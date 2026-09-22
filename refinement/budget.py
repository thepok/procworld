"""Numerical budgets with transactional reservations and explicit stop reasons."""
from __future__ import annotations
from dataclasses import dataclass,asdict
import math
import time


@dataclass(frozen=True,slots=True)
class Cost:
    nodes: int = 0
    instances: int = 0
    triangles: int = 0
    memory_bytes: int = 0
    def __post_init__(self):
        if any(type(v) is not int or v<0 for v in asdict(self).values()):
            raise ValueError('Costs must be nonnegative integers')
    def __add__(self,other):
        return Cost(*(getattr(self,k)+getattr(other,k) for k in asdict(self)))


@dataclass(frozen=True,slots=True)
class Budget:
    max_nodes: int = 18000
    max_instances: int = 12000
    max_triangles: int = 250000
    memory_budget: int = 256*1024*1024
    max_refinements: int = 450
    max_generation_time: float|None = None
    def __post_init__(self):
        for key in ('max_nodes','max_instances','max_triangles','memory_budget','max_refinements'):
            v=getattr(self,key)
            if type(v) is not int or v<0: raise ValueError(f'{key} must be a nonnegative integer')
        if self.max_generation_time is not None and (not math.isfinite(self.max_generation_time)
                                                       or self.max_generation_time<=0):
            raise ValueError('Time budget must be positive or None')
    @classmethod
    def preset(cls,name:str) -> 'Budget':
        presets={
            'PREVIEW':dict(max_nodes=18000,max_instances=10000,max_triangles=180000,max_refinements=120),
            'DRAFT':dict(max_nodes=32000,max_instances=24000,max_triangles=600000,max_refinements=600),
            'HIGH':dict(max_nodes=80000,max_instances=70000,max_triangles=2200000,max_refinements=2200),
            'FINAL':dict(max_nodes=180000,max_instances=180000,max_triangles=6500000,max_refinements=7000),
        }
        try: return cls(**presets[name.upper()])
        except KeyError as exc: raise ValueError(f'Unknown budget preset: {name}') from exc


class BudgetLedger:
    def __init__(self,budget:Budget):
        self.budget=budget; self.used=Cost(); self.started=time.monotonic(); self.refinements=0
    @property
    def elapsed(self): return time.monotonic()-self.started
    @property
    def time_exhausted(self):
        return self.budget.max_generation_time is not None and self.elapsed>=self.budget.max_generation_time
    def allows(self,cost:Cost,replace:Cost=Cost()) -> bool:
        b=self.budget
        values=[getattr(self.used,k)-getattr(replace,k)+getattr(cost,k) for k in asdict(cost)]
        return (not self.time_exhausted and all(v>=0 for v in values) and
                all(v<=limit for v,limit in zip(values,(b.max_nodes,b.max_instances,b.max_triangles,b.memory_budget))))
    def reserve(self,cost:Cost,replace:Cost=Cost()) -> bool:
        if not self.allows(cost,replace): return False
        self.used=Cost(*(getattr(self.used,k)-getattr(replace,k)+getattr(cost,k) for k in asdict(cost)))
        return True
    def report(self):
        return {'limits':asdict(self.budget),'used':asdict(self.used),'refinements':self.refinements,
                'elapsed_seconds':round(self.elapsed,6),'time_exhausted':self.time_exhausted,
                'memory_accounting':'Estimated semantic and geometry payloads; not process RSS'}
