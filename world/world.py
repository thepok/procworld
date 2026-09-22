"""Persistent, camera-independent world history with lazy canonical-region materialization."""
from __future__ import annotations
from dataclasses import fields
import copy
import math
from ..core.node import Thing,Dimension,node_from_data
from ..core.domain import UnboundedDomain
from ..core.graph import SemanticGraph
from ..core.event import EventLog
from ..core.scope import Scope,TimeInterval
from ..core.seed import stable_id,canonical
from ..core.constraints import CommitmentViolation
from ..refinement.cache import ResultCache
from .fields import WorldFields
from .config import WorldSettings
from .regions import region_coordinates,static_region_events,EPOCH
from .bootstrap import default_registry


class World:
    def __init__(self,settings:WorldSettings|None=None,*,constraints=(),registry=None,vegetation_adapter=None):
        self.settings=settings or WorldSettings()
        self.registry=registry or default_registry()
        self.constraints=tuple(copy.deepcopy(constraints))
        self.environment=WorldFields(self.settings.seed,self.settings.sea_level)
        self.vegetation_adapter=vegetation_adapter
        if vegetation_adapter:
            self.registry.versions['vegetation_adapter']=vegetation_adapter.version
        self.id=stable_id('procedural_universe','World',self.settings.seed)
        self.base=SemanticGraph()
        self.base.add(Thing(self.id,'World',self.settings.seed,UnboundedDomain(),
                            {'seed':self.settings.seed,'sea_level':self.settings.sea_level}))
        self.events=EventLog(); self.regions={}; self.refinement_records=[]; self.overrides={}
        self.cache=ResultCache(1536)
    def add_thing(self,thing):
        """Add a manually authored semantic Thing; all graph invariants still apply."""
        self.base.add(thing)
    @staticmethod
    def _region_key(coord): return f'{coord[0]},{coord[1]}'
    def ensure_region(self,coord,until):
        key=self._region_key(coord); previous=self.regions.get(key)
        if previous and previous['until']>=until: return previous
        until=max(until,previous['until'] if previous else until)
        rid,process,static=static_region_events(self.id,self.settings,self.environment,coord)
        evaluator=self.registry.processes.get(process.type_id)
        urban=[]
        if evaluator is not None:
            process=evaluator(**{f.name:copy.deepcopy(getattr(process,f.name)) for f in fields(process)})
            interval=TimeInterval(EPOCH,until)
            scope=Scope(process.domain,self.settings.seed,process.seed,until,interval,
                        parent_constraints=self.constraints,environment=self.environment,
                        semantic_context={'settings':self.settings,'region_id':rid})
            urban=process.evaluate(None,interval,scope)
        all_events=static+urban
        # Append is all-or-nothing and detects accidental changes to an existing prefix.
        self.events.extend(all_events)
        coarse=[e.id for e in static]+[e.id for e in urban if e.type_id=='CreateSettlement']
        record={'coordinate':list(coord),'until':until,'events':sorted(e.id for e in all_events),
                'coarse_events':sorted(coarse),'node_count':sum('node' in e.payload for e in all_events),
                'coarse_node_count':sum('node' in self.events.events[eid].payload for eid in coarse)}
        self.regions[key]=record
        return record
    def materialize(self,center,radius,time,budget,ledger=None):
        regional_ids={eid for r in self.regions.values() for eid in r['events']}
        selected=set(self.events.events)-regional_ids
        count=len(self.base)+sum('node' in self.events.events[eid].payload and self.events.events[eid].time<=time for eid in selected)
        report={'full_regions':[],'coarse_regions':[],'omitted_regions':[]}
        coordinates=region_coordinates(center,radius,self.settings.region_size)
        if count>budget.max_nodes: raise ValueError('The world root/manual graph exceeds max_nodes')
        for coord in coordinates:
            if ledger is not None and ledger.time_exhausted:
                report['omitted_regions'].append(list(coord)); continue
            record=self.ensure_region(coord,time)
            # Leave 5% headroom for initial structural detail where feasible.
            full_limit=max(1,min(int(budget.max_nodes*.95),budget.memory_budget//2200))
            node_count=sum('node' in self.events.events[eid].payload and self.events.events[eid].time<=time for eid in record['events'])
            coarse_count=sum('node' in self.events.events[eid].payload and self.events.events[eid].time<=time for eid in record['coarse_events'])
            if count+node_count<=full_limit:
                selected.update(record['events']); count+=node_count; report['full_regions'].append(list(coord))
            elif count+coarse_count<=min(budget.max_nodes,max(1,budget.memory_budget//2200)):
                selected.update(record['coarse_events']); count+=coarse_count; report['coarse_regions'].append(list(coord))
            else:
                report['omitted_regions'].append(list(coord))
        return selected,report
    def graph(self,time=None,*,event_ids=None,max_nodes=None):
        time=self.settings.world_time if time is None else time
        if event_ids is None:
            log=self.events
        else:
            log=EventLog(); log.events={k:self.events.events[k] for k in event_ids}
        graph=log.replay(self.base,time,self.registry)
        for record in self.refinement_records:
            pid=record['parent_id']; dim=Dimension(record['dimension'])
            if pid not in graph.nodes: continue
            if graph[pid].refinement_state.get(dim)>=record['level']: continue
            children=tuple(node_from_data(d) for d in record['children'])
            if max_nodes is not None and len(graph)+len(children)>max_nodes: continue
            graph.refine(pid,dim,record['level'],record['facts'],children)
        return graph
    def commit_refinements(self,records):
        by_key={(r['parent_id'],r['dimension'],r['level']):r for r in self.refinement_records}
        additions=[]
        for record in records:
            key=(record['parent_id'],record['dimension'],record['level'])
            if key in by_key:
                # Implementation versions may differ, but committed child facts may not.
                old=by_key[key]
                if canonical((old['facts'],old['children']))!=canonical((record['facts'],record['children'])):
                    raise CommitmentViolation('A refiner contradicted committed structural detail')
            else:
                additions.append(copy.deepcopy(record)); by_key[key]=record
        self.refinement_records.extend(additions)
    def snapshot(self,**kwargs):
        from ..representation.snapshot import build_snapshot
        return build_snapshot(self,**kwargs)
    def save(self,path):
        from ..core.serialization import save_world
        return save_world(self,path)
    @classmethod
    def load(cls,path,**kwargs):
        from ..core.serialization import load_world
        return load_world(path,**kwargs)
    def invalidate(self,token):
        return self.cache.invalidate(token)
