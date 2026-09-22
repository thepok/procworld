from dataclasses import dataclass
import math


@dataclass(frozen=True,slots=True)
class WorldSettings:
    seed: int = 12
    world_time: float = 2025.
    sea_level: float = 0.
    region_size: float = 1536.
    settlement_probability: float = .88
    initial_year: float = 1680.
    maximum_year: float = 2500.
    growth_rings: int = 3
    block_size: float = 100.
    behavioral_level: int = 1
    def __post_init__(self):
        if type(self.seed) is not int: raise ValueError('World seed must be an integer')
        if not all(math.isfinite(v) for v in (self.world_time,self.sea_level,self.region_size,
                    self.initial_year,self.maximum_year,self.block_size,self.settlement_probability)):
            raise ValueError('World settings must be finite')
        if self.region_size<512 or self.block_size<30 or not 0<=self.settlement_probability<=1:
            raise ValueError('Invalid spatial or settlement settings')
        if type(self.growth_rings) is not int or not 0<=self.growth_rings<=8:
            raise ValueError('growth_rings must be in [0,8]')
        if (self.growth_rings+1)*self.block_size+140>self.region_size/2:
            raise ValueError('The canonical settlement layout does not fit its owner region')
        if not self.initial_year<=self.world_time<=self.maximum_year or self.initial_year>=self.maximum_year:
            raise ValueError('World time must lie in the configured historical interval')
        if self.behavioral_level not in (0,1,2): raise ValueError('behavioral_level must be 0, 1, or 2')
