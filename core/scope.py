from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import math
from .domain import Domain, Vec3, point
from .seed import derive_seed
from .node import RefinementState


@dataclass(frozen=True,slots=True)
class Transform:
    translation: Vec3 = (0.,0.,0.)
    scale: Vec3 = (1.,1.,1.)
    rotation_z: float = 0.
    def __post_init__(self):
        object.__setattr__(self,'translation',point(self.translation))
        object.__setattr__(self,'scale',point(self.scale))
        if not math.isfinite(self.rotation_z) or any(v<=0 for v in self.scale):
            raise ValueError('Transform requires finite rotation and positive scales')
    def apply(self,p:Vec3) -> Vec3:
        x,y,z=(p[i]*self.scale[i] for i in range(3))
        c,s=math.cos(self.rotation_z),math.sin(self.rotation_z)
        return (x*c-y*s+self.translation[0],x*s+y*c+self.translation[1],z+self.translation[2])


@dataclass(frozen=True,slots=True)
class TimeInterval:
    start: float
    end: float
    def __post_init__(self):
        if not math.isfinite(self.start+self.end) or self.end<self.start:
            raise ValueError('Invalid time interval')
    def contains(self,time:float) -> bool:
        return self.start <= time <= self.end


@dataclass(frozen=True,slots=True)
class Scope:
    domain: Domain
    world_seed: int
    local_seed: int
    current_time: float
    historical_interval: TimeInterval
    transform: Transform = field(default_factory=Transform)
    parent_constraints: tuple = ()
    environment: Any = None
    semantic_context: dict = field(default_factory=dict)
    refinement_request: RefinementState = field(default_factory=RefinementState)
    generation_budget: Any = None
    def child(self,key:str,domain:Domain,**semantic_context) -> 'Scope':
        if not self.domain.contains_domain(domain):
            raise ValueError('Child scope escapes its parent domain')
        return Scope(domain,self.world_seed,derive_seed(self.local_seed,key),self.current_time,
                     self.historical_interval,self.transform,self.parent_constraints,self.environment,
                     {**self.semantic_context,**semantic_context},self.refinement_request,self.generation_budget)
