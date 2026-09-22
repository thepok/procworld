"""Immutable event records and deterministic, idempotent historical replay."""
from __future__ import annotations
from dataclasses import dataclass,field
import copy
import math
from .node import node_from_data
from .graph import SemanticGraph
from .constraints import CommitmentViolation
from .seed import canonical,digest,stable_id


@dataclass(frozen=True,slots=True)
class Event:
    id: str
    type_id: str
    time: float
    target_id: str
    payload: dict = field(default_factory=dict)
    process_id: str|None = None
    parent_id: str|None = None
    interval_end: float|None = None
    priority: int = 20
    def __post_init__(self):
        if not math.isfinite(self.time) or (self.interval_end is not None and
           (not math.isfinite(self.interval_end) or self.interval_end < self.time)):
            raise ValueError('Invalid event time interval')
        canonical(self.payload)
    def to_data(self):
        return {'id':self.id,'type_id':self.type_id,'time':self.time,'target_id':self.target_id,
                'payload':copy.deepcopy(self.payload),'process_id':self.process_id,'parent_id':self.parent_id,
                'interval_end':self.interval_end,'priority':self.priority}
    @classmethod
    def from_data(cls,data):
        return cls(**copy.deepcopy(data))


def create_event(node,type_id='CreateThing',process_id=None,priority=20,parent_id=None):
    return Event(stable_id(node.id,'Event',type_id),type_id,node.created_at,node.id,
                 {'node':node.to_data()},process_id,parent_id,priority=priority)


@dataclass(frozen=True,slots=True)
class AggregateRequirement:
    parent_key: str
    child_key: str
    tolerance: float = 1e-6
    def validate(self,parent:Event,children:tuple[Event,...]):
        if self.tolerance<0: raise ValueError('Negative aggregate tolerance')
        total=sum(float(c.payload.get(self.child_key,0)) for c in children)
        target=float(parent.payload[self.parent_key])
        if not math.isfinite(total+target) or abs(total-target)>self.tolerance:
            raise CommitmentViolation(f'Event total {total} does not preserve {target}')


class EventLog:
    def __init__(self):
        self.events:dict[str,Event]={}
        self.refinements:dict[str,tuple[str,...]]={}
    def append(self,event:Event):
        old=self.events.get(event.id)
        if old is not None and canonical(old.to_data())!=canonical(event.to_data()):
            raise CommitmentViolation(f'Conflicting historical event {event.id}')
        self.events[event.id]=copy.deepcopy(event)
    def extend(self,events):
        events=list(events); staged=dict(self.events)
        for event in events:
            old=staged.get(event.id)
            if old and canonical(old.to_data())!=canonical(event.to_data()):
                raise CommitmentViolation(f'Conflicting historical event {event.id}')
            staged[event.id]=copy.deepcopy(event)
        self.events=staged
    def refine(self,parent_id:str,children:tuple[Event,...],requirements=()):
        parent=self.events[parent_id]
        if parent.interval_end is None: raise CommitmentViolation('A coarse event needs an interval')
        if not children: raise CommitmentViolation('Event refinement cannot be empty')
        if len({c.id for c in children})!=len(children): raise CommitmentViolation('Duplicate child events')
        for c in children:
            if c.parent_id!=parent_id or c.id==parent_id:
                raise CommitmentViolation('Invalid event parent')
            if c.time<parent.time or (c.interval_end or c.time)>parent.interval_end:
                raise CommitmentViolation('Child event escapes parent interval')
            p=parent
            while p.parent_id:
                if p.parent_id==c.id: raise CommitmentViolation('Event cycle')
                p=self.events[p.parent_id]
        for rule in requirements: rule.validate(parent,children)
        ids=tuple(sorted(c.id for c in children))
        if parent_id in self.refinements and self.refinements[parent_id]!=ids:
            raise CommitmentViolation('Previously refined history is committed')
        self.extend(children); self.refinements[parent_id]=ids
    def ordered(self,time:float|None=None):
        return sorted((e for e in self.events.values() if time is None or e.time<=time),
                      key=lambda e:(e.time,e.priority,e.id))
    def replay(self,initial:SemanticGraph,time:float,registry) -> SemanticGraph:
        graph=initial.copy()
        for event in self.ordered(time):
            handler=registry.events.get(event.type_id)
            if handler is None:
                raise ValueError(f'Unregistered event type: {event.type_id}')
            handler(graph,event)
        return graph
    def for_target(self,node_id):
        return tuple(e for e in self.ordered() if e.target_id==node_id)
    def to_data(self):
        return {'events':[e.to_data() for e in self.ordered()],
                'refinements':{k:list(v) for k,v in sorted(self.refinements.items())}}
    @classmethod
    def from_data(cls,data):
        log=cls(); log.extend(Event.from_data(d) for d in data['events'])
        log.refinements={k:tuple(v) for k,v in data.get('refinements',{}).items()}
        for parent,children in log.refinements.items():
            if parent not in log.events or any(c not in log.events or log.events[c].parent_id!=parent for c in children):
                raise ValueError('Broken serialized event refinement')
        return log
    def fingerprint(self):
        return digest(self.to_data())


def handle_create(graph,event):
    node=node_from_data(event.payload['node'])
    if node.id!=event.target_id or node.created_at!=event.time:
        raise CommitmentViolation('Creation event disagrees with its semantic node')
    graph.add(node,check_domain=not node.provenance.get('crosses_parent_boundary',False))


def handle_update(graph,event):
    if not graph.is_active(event.target_id,event.time):
        raise CommitmentViolation('An update targets an inactive Thing')
    graph.update(event.target_id,event.payload['facts'])


def handle_destroy(graph,event):
    graph.destroy(event.target_id,event.time)


def handle_aggregate(graph,event):
    # Aggregate events are commitments/containers, never double-applied mutations.
    return None


def register_events(registry):
    for name in ('CreateThing','CreateRegion','CreateSettlement','CreateDistrict','ExtendRoad',
                 'CreateBlock','SplitParcel','ConstructBuilding','CreatePark','CreateForest','PlantTree'):
        registry.register('events',name,handle_create)
    for name in ('RenovateBuilding','ChangeLandUse','UpgradeRoad'):
        registry.register('events',name,handle_update)
    for name in ('DemolishBuilding','TreeDies'):
        registry.register('events',name,handle_destroy)
    for name in ('UrbanExpansion','ResidentialExpansion','LifecycleSummary'):
        registry.register('events',name,handle_aggregate)
