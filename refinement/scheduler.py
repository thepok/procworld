"""Best-first, deterministic, four-axis refinement with atomic budget checks."""
from __future__ import annotations
from dataclasses import replace
import heapq
import math
from ..core.graph import SemanticGraph
from ..core.node import Dimension,RefinementState
from ..core.domain import UnboundedDomain
from ..core.seed import canonical
from .budget import Cost
from .overrides import NodeOverride
from ..representation.provider import realize
from ..representation.fallback import fallback


INTERIOR_TYPES={'Floor','Room','Corridor','FurnitureProxy','Stairwell','ElevatorShaft'}


def renderable(node,graph,context):
    if node.category!='thing' or isinstance(node.domain,UnboundedDomain): return False
    if node.type_id in INTERIOR_TYPES and not context.include_interiors: return False
    if context.registry.is_container(node.type_id):
        return not any(graph.is_active(cid,context.time) for cid in node.child_ids)
    return True


def node_memory(node):
    # A deterministic payload estimate. Python/container overhead varies by runtime.
    return len(canonical(node.to_data()).encode('utf8'))+512


class Scheduler:
    def __init__(self):
        self.errors=[]; self.skipped=[]; self.records=[]; self.attempts=0
    def run(self,graph,scene,context,ledger,center,radius,overrides=None):
        overrides=overrides or {}; heap=[]; queued=set(); sequence=0
        def effective(node):
            override=overrides.get(node.id,NodeOverride())
            request=RefinementState(**{d.value:override.target(d,context.request.get(d)) for d in Dimension})
            constraints=[]; stack=list(node.parent_ids); seen=set()
            while stack:
                pid=stack.pop()
                if pid in seen: continue
                seen.add(pid); p=graph[pid]; constraints.extend(p.commitments); stack.extend(p.parent_ids)
            return replace(context,request=request,ancestor_commitments=tuple(constraints)),override
        def enqueue(node):
            nonlocal sequence
            if not graph.is_active(node.id,context.time): return
            ctx,override=effective(node)
            if override.never_refine: return
            if isinstance(node.domain,UnboundedDomain): return
            pixels,visible=context.camera.projected_importance(node.domain.bounds)
            d=math.hypot(node.anchor[0]-center[0],node.anchor[1]-center[1])
            falloff=1/(1+(d/max(radius,1))**4)
            for refiner in sorted(context.registry.refiners.values(),key=lambda r:r.key):
                token=(node.id,refiner.key,node.version,node.refinement_state.get(refiner.dimension))
                if token in queued: continue
                try:
                    if not refiner.can_refine(node.copy(),ctx): continue
                    forced=override.forced(refiner.dimension,node.refinement_state.get(refiner.dimension))
                    if refiner.dimension==Dimension.GEOMETRIC and node.id not in scene.bundles: continue
                    if not forced:
                        if not visible or pixels<4: continue
                        if refiner.dimension==Dimension.STRUCTURAL and d>radius*1.15: continue
                    cost=refiner.estimate_cost(node.copy(),ctx)
                    gain=float(refiner.estimate_gain(node.copy(),ctx))
                    if not math.isfinite(gain) or gain<=0: continue
                    expense=1+cost.nodes*10+cost.triangles*.015+cost.memory_bytes/10000
                    semantic=float(node.semantic_state.get('semantic_importance',1.))
                    score=gain*max(1,pixels)**1.25*falloff*max(.01,semantic)/expense
                    if forced: score+=1e15
                    heapq.heappush(heap,(-score,node.id,refiner.key,node.version,sequence)); sequence+=1
                    queued.add(token)
                except Exception as exc:
                    self.errors.append({'node_id':node.id,'refiner':refiner.key,'error':f'{type(exc).__name__}: {exc}'})
        for node in graph.active(context.time): enqueue(node)
        while heap and ledger.refinements<ledger.budget.max_refinements and not ledger.time_exhausted:
            _,node_id,key,version,_=heapq.heappop(heap)
            node=graph[node_id]
            if node.version!=version: continue
            refiner=context.registry.refiners[key]; ctx,override=effective(node)
            if not refiner.can_refine(node.copy(),ctx): continue
            self.attempts+=1
            try:
                result=refiner.refine(node.copy(),ctx)
                if result.dimension!=refiner.dimension or result.level!=node.refinement_state.get(refiner.dimension)+1:
                    raise ValueError('A refiner must advance its declared dimension by one level')
                trial=SemanticGraph(); trial.nodes=dict(graph.nodes)
                trial.refine(node_id,result.dimension,result.level,result.facts,result.children)
                updated=trial[node_id]
                staged={}; replace_cost=Cost()
                additional=sum(node_memory(trial[c.id]) for c in result.children)
                additional+=max(0,node_memory(updated)-node_memory(node))
                new_cost=Cost(nodes=len(result.children),memory_bytes=additional)
                if node_id in scene.bundles:
                    previous=scene.bundles[node_id]; replace_cost=previous.cost()
                    if result.geometry is not None:
                        bundle=result.geometry
                    elif result.dimension==Dimension.STRUCTURAL:
                        bundle=realize(updated,updated.refinement_state.geometric,ctx)
                    else:
                        bundle=previous
                    staged[node_id]=bundle; new_cost=new_cost+bundle.cost()
                elif result.geometry is not None:
                    raise ValueError('Cannot refine unmaterialized geometry')
                for child in result.children:
                    current=trial[child.id]
                    if renderable(current,trial,ctx):
                        try: bundle=realize(current,0,ctx)
                        except Exception as exc:
                            self.errors.append({'node_id':child.id,'refiner':'fallback','error':str(exc)})
                            bundle=fallback(current)
                        staged[child.id]=bundle; new_cost=new_cost+bundle.cost()
                if any(bundle.prototypes for bundle in staged.values()):
                    prototypes=scene.prototypes()
                    for bundle in staged.values():
                        for name,mesh in bundle.prototypes:
                            if name in prototypes and prototypes[name]!=mesh:
                                raise ValueError(f'Conflicting shared prototype {name}')
                            prototypes[name]=mesh
                if not ledger.reserve(new_cost,replace_cost):
                    self.skipped.append({'node_id':node_id,'refiner':key,'reason':'budget'})
                    continue
                graph.nodes=trial.nodes
                for nid,bundle in staged.items():
                    scene.bundles[nid]=bundle
                    scene.categories[nid]=context.registry.category_for(graph[nid].type_id)
                ledger.refinements+=1
                if result.dimension in (Dimension.STRUCTURAL,Dimension.BEHAVIORAL):
                    self.records.append({'parent_id':node_id,'dimension':result.dimension.value,'level':result.level,
                                         'facts':result.facts,'children':[c.to_data() for c in result.children],
                                         'generator':key,'generator_version':refiner.version})
                enqueue(graph[node_id])
                for child in result.children: enqueue(graph[child.id])
            except Exception as exc:
                # The graph and previous representation survive a failed provider.
                self.errors.append({'node_id':node_id,'refiner':key,'error':f'{type(exc).__name__}: {exc}'})
        unmet=[]
        for nid,override in sorted(overrides.items()):
            for name,level in override.minimum.items():
                if nid not in graph.nodes or graph[nid].refinement_state.get(Dimension(name))<level:
                    unmet.append({'node_id':nid,'dimension':name,'minimum':level})
        return {'attempts':self.attempts,'errors':self.errors,'budget_skips':self.skipped,
                'unmet_forced_minimums':unmet,'queued_remaining':len(heap)}
