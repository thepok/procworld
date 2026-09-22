"""Lightweight semantic records; no geometry or Blender imports."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import copy
import math
from .domain import Domain, UnboundedDomain, domain_from_data
from .constraints import Commitment, CommitmentViolation
from .seed import canonical


class Dimension(str,Enum):
    STRUCTURAL='structural'
    GEOMETRIC='geometric'
    TEMPORAL='temporal'
    BEHAVIORAL='behavioral'


@dataclass(slots=True)
class RefinementState:
    structural: int = 0
    geometric: int = 0
    temporal: int = 0
    behavioral: int = 0
    def __post_init__(self):
        if any(type(getattr(self,d.value)) is not int or getattr(self,d.value)<0 for d in Dimension):
            raise ValueError('Refinement levels must be nonnegative integers')
    def get(self, dimension: Dimension) -> int:
        return getattr(self,Dimension(dimension).value)
    def advance(self, dimension: Dimension, level: int):
        if type(level) is not int or level <= self.get(dimension):
            raise CommitmentViolation('Refinement must advance monotonically')
        setattr(self,Dimension(dimension).value,level)
    def to_data(self):
        return {d.value:self.get(d) for d in Dimension}


@dataclass(slots=True)
class ProceduralNode:
    id: str
    type_id: str
    seed: int
    domain: Domain = field(default_factory=UnboundedDomain)
    semantic_state: dict = field(default_factory=dict)
    parent_ids: tuple[str,...] = ()
    child_ids: tuple[str,...] = ()
    created_at: float = -1e9
    destroyed_at: float | None = None
    commitments: tuple[Commitment,...] = ()
    refinement_state: RefinementState = field(default_factory=RefinementState)
    version: int = 0
    provenance: dict = field(default_factory=dict)
    category: str = 'node'
    def __post_init__(self):
        self.parent_ids=tuple(self.parent_ids); self.child_ids=tuple(self.child_ids)
        self.commitments=tuple(self.commitments)
        if not self.id or not self.type_id or type(self.seed) is not int:
            raise ValueError('Node identity, type, and integer seed are required')
        if not math.isfinite(self.created_at) or (self.destroyed_at is not None and
           (not math.isfinite(self.destroyed_at) or self.destroyed_at < self.created_at)):
            raise ValueError('Invalid half-open lifetime interval')
        if self.id in self.parent_ids or len(set(self.parent_ids)) != len(self.parent_ids):
            raise ValueError('Invalid parents')
        canonical(self.semantic_state)
        self.validate()
    @property
    def anchor(self):
        return self.domain.anchor
    def exists_at(self,time:float) -> bool:
        return self.created_at <= time and (self.destroyed_at is None or time < self.destroyed_at)
    def validate(self):
        for commitment in self.commitments:
            commitment.validate(self.semantic_state)
    def copy(self):
        return copy.deepcopy(self)
    def to_data(self):
        return {'id':self.id,'type_id':self.type_id,'seed':self.seed,'domain':self.domain.to_data(),
                'semantic_state':copy.deepcopy(self.semantic_state),'parent_ids':self.parent_ids,
                'child_ids':self.child_ids,'created_at':self.created_at,'destroyed_at':self.destroyed_at,
                'commitments':[c.to_data() for c in self.commitments],
                'refinement_state':self.refinement_state.to_data(),'version':self.version,
                'provenance':copy.deepcopy(self.provenance),'category':self.category}


@dataclass(slots=True)
class Thing(ProceduralNode):
    category: str = 'thing'


@dataclass(slots=True)
class Process(ProceduralNode):
    category: str = 'process'
    def evaluate(self,world_state,time_interval,context):
        raise NotImplementedError('Register a Process evaluator for this process type')


def node_from_data(data:dict) -> ProceduralNode:
    values=copy.deepcopy(data)
    values['domain']=domain_from_data(values['domain'])
    values['commitments']=tuple(Commitment(**c) for c in values.get('commitments',()))
    values['refinement_state']=RefinementState(**values.get('refinement_state',{}))
    cls={'thing':Thing,'process':Process}.get(values.get('category'),ProceduralNode)
    return cls(**values)
