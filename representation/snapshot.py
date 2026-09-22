from __future__ import annotations
from dataclasses import dataclass,asdict
import math
import copy
from ..core.node import RefinementState
from ..core.domain import Bounds,UnboundedDomain
from ..core.seed import digest
from ..refinement.budget import Budget,BudgetLedger,Cost
from ..refinement.refiner import RefinementContext
from ..refinement.scheduler import Scheduler,renderable,node_memory
from .camera import Camera
from .geometry import GeometryScene
from .provider import realize
from .fallback import fallback


@dataclass(slots=True)
class Snapshot:
    seed: int
    time: float
    camera: Camera
    center: tuple[float,float]
    radius: float
    halo: float
    graph: object
    scene: GeometryScene
    report: dict
    generator_versions: dict
    def to_data(self,include_graph=False,include_geometry=True):
        data={'schema_version':1,'seed':self.seed,'time':self.time,'camera':asdict(self.camera),
              'center':self.center,'radius':self.radius,'halo':self.halo,'report':self.report,
              'generator_versions':self.generator_versions}
        if include_graph: data['semantic_graph']=self.graph.to_data()
        if include_geometry: data['geometry']=self.scene.to_data()
        return data
    def fingerprint(self):
        # Timing and cache hit rates are operational, not reproducible world content.
        return digest(self.seed,self.time,asdict(self.camera),self.graph.to_data(),self.scene.to_data())


def build_snapshot(world,time=None,camera=None,center=(0.,0.),radius=600.,halo=2.,
                   budget=None,request=None,overrides=None,include_interiors=False):
    time=world.settings.world_time if time is None else float(time)
    if not world.settings.initial_year<=time<=world.settings.maximum_year:
        raise ValueError('Snapshot year is outside the configured historical interval')
    center=tuple(float(v) for v in center)
    if len(center)!=2 or not all(math.isfinite(v) for v in center): raise ValueError('Invalid snapshot center')
    if not math.isfinite(radius+halo) or radius<=0 or not 1<=halo<=10: raise ValueError('Invalid core radius or halo')
    budget=budget or Budget.preset('PREVIEW'); request=request or RefinementState(1,2,0,0)
    camera=camera or Camera((center[0]+600,center[1]-850,700),(center[0],center[1],30))
    ledger=BudgetLedger(budget)
    selected,materialization=world.materialize(center,radius*halo,time,budget,ledger)
    graph=world.graph(time,event_ids=selected,max_nodes=budget.max_nodes)
    semantic_cost=Cost(nodes=len(graph),memory_bytes=sum(node_memory(n) for n in graph.nodes.values()))
    if not ledger.reserve(semantic_cost):
        raise ValueError('Budget cannot hold the selected semantic graph; increase max_nodes/memory or time limit')
    scene=GeometryScene()
    context=RefinementContext(world.settings.seed,time,world.environment,world.registry,world.cache,camera,
                              request,budget,world.constraints,tuple(copy.deepcopy(world.events.ordered(time))),include_interiors,
                              vegetation_adapter=world.vegetation_adapter)
    extent=Bounds((center[0]-radius*halo,center[1]-radius*halo,-1e6),
                  (center[0]+radius*halo,center[1]+radius*halo,1e6))
    active=graph.active(time)
    candidates=[]
    for node in active:
        if not renderable(node,graph,context) or not node.domain.bounds.intersects(extent,True): continue
        pixels,visible=camera.projected_importance(node.domain.bounds)
        # Terrain and water keep the context complete before decorative detail.
        base_priority=1e10 if node.type_id in {'Terrain','Ocean','River','Lake'} else 0
        candidates.append((-(base_priority+pixels*(1 if visible else .05)),node.id))
    failures=[]; omitted=[]
    for _,node_id in sorted(candidates):
        node=graph[node_id]
        try:
            bundle=realize(node,0,context)
            scene.validate_bundle(bundle)
        except Exception as exc:
            failures.append({'node_id':node_id,'error':str(exc)}); bundle=fallback(node)
        if not ledger.reserve(bundle.cost()):
            omitted.append(node_id); continue
        scene.bundles[node_id]=bundle; scene.categories[node_id]=world.registry.category_for(node.type_id)
    scheduler=Scheduler()
    overrides={**world.overrides,**(overrides or {})}
    scheduling=scheduler.run(graph,scene,context,ledger,center,radius,overrides)
    world.commit_refinements(scheduler.records)
    geometry_cost=scene.cost()
    report={'budget':ledger.report(),'materialization':materialization,'scheduler':scheduling,
            'fallback_errors':failures,'omitted_representations':omitted,
            'active_nodes':len(graph.active(time)),'represented_nodes':len(scene.bundles),
            'geometry_triangles':geometry_cost.triangles,'geometry_instances':geometry_cost.instances,
            'cache':{'hits':world.cache.hits,'misses':world.cache.misses},
            'visibility':'Bounding-sphere/frustum approximation; no occlusion, reflections, or depth-of-field solver'}
    return Snapshot(world.settings.seed,time,camera,center,radius,halo,graph,scene,report,dict(world.registry.versions))
