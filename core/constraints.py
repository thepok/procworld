"""Hard refinement commitments and time-dependent artistic influence fields."""
from __future__ import annotations
from dataclasses import dataclass, field
import math
import copy
from .domain import Domain, Vec3, domain_from_data
from .seed import canonical


class CommitmentViolation(ValueError):
    pass


def lookup(state: dict, path: str):
    value = state
    for part in path.split('.'):
        value = value[part]
    return value


@dataclass(frozen=True, slots=True)
class Commitment:
    path: str
    value: object
    tolerance: float = 0.
    def __post_init__(self):
        if self.tolerance < 0 or not math.isfinite(self.tolerance):
            raise ValueError('Invalid commitment tolerance')
        canonical(self.value)
        object.__setattr__(self,'value',copy.deepcopy(self.value))
    def validate(self, state: dict):
        try:
            actual = lookup(state,self.path)
        except (KeyError,TypeError) as exc:
            raise CommitmentViolation(f'Missing committed fact {self.path}') from exc
        if self.tolerance and isinstance(actual,(int,float)) and isinstance(self.value,(int,float)):
            okay = math.isfinite(actual) and abs(actual-self.value) <= self.tolerance
        else:
            okay = canonical(actual) == canonical(self.value)
        if not okay:
            raise CommitmentViolation(f'{self.path}: {actual!r} contradicts {self.value!r}')
    def to_data(self):
        return {'path':self.path,'value':self.value,'tolerance':self.tolerance}


@dataclass(frozen=True, slots=True)
class InfluenceField:
    id: str
    kind: str
    domain: Domain
    strength: float = 1.
    falloff: float = 0.
    active_from: float = -1e9
    active_until: float | None = None
    parameters: dict = field(default_factory=dict)
    def __post_init__(self):
        if self.falloff < 0 or not all(math.isfinite(v) for v in
                                     (self.strength,self.falloff,self.active_from)):
            raise ValueError('Invalid influence parameters')
        if self.active_until is not None and (not math.isfinite(self.active_until)
                                              or self.active_until <= self.active_from):
            raise ValueError('Invalid influence interval')
        canonical(self.parameters)
    def active(self,time:float) -> bool:
        return self.active_from <= time and (self.active_until is None or time < self.active_until)
    def sample(self, p: Vec3, time: float) -> float:
        if not self.active(time):
            return 0.
        if self.domain.contains_point(p):
            return self.strength
        if not self.falloff:
            return 0.
        b = self.domain.bounds
        # AABB distance is an intentionally inexpensive influence approximation.
        d = math.sqrt(sum(max(a-v,0,v-z)**2 for a,z,v in zip(b.minimum,b.maximum,p)))
        t = max(0.,1-d/self.falloff)
        return self.strength*t*t*(3-2*t)
    def blocks(self, domain: Domain, time: float) -> bool:
        return (self.kind in {'NoBuildArea','ProtectedArea','ParkConstraint'} and
                self.strength > 0 and self.active(time) and
                self.domain.bounds.intersects(domain.bounds,xy_only=True))
    def to_data(self):
        return {'id':self.id,'kind':self.kind,'domain':self.domain.to_data(),
                'strength':self.strength,'falloff':self.falloff,
                'active_from':self.active_from,'active_until':self.active_until,
                'parameters':self.parameters}
    @classmethod
    def from_data(cls,d):
        return cls(**{**d,'domain':domain_from_data(d['domain'])})
