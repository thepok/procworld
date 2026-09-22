from dataclasses import dataclass,field
from ..core.node import Dimension,RefinementState


@dataclass(frozen=True,slots=True)
class NodeOverride:
    never_refine: bool = False
    always_refine: bool = False
    minimum: dict[str,int] = field(default_factory=dict)
    maximum: dict[str,int] = field(default_factory=dict)
    def __post_init__(self):
        if self.never_refine and self.always_refine:
            raise ValueError('Never and always refine are mutually exclusive')
        for values in (self.minimum,self.maximum):
            for key,value in values.items():
                Dimension(key)
                if type(value) is not int or value<0: raise ValueError('Invalid override level')
        for key,value in self.minimum.items():
            if key in self.maximum and value>self.maximum[key]:
                raise ValueError('Forced minimum exceeds forced maximum')
        if self.never_refine and any(self.minimum.values()):
            raise ValueError('Never-refine contradicts a forced minimum')
    def target(self,dimension:Dimension,requested:int) -> int:
        key=dimension.value
        if self.never_refine: return 0
        return min(max(requested,self.minimum.get(key,0)),self.maximum.get(key,10**6))
    def forced(self,dimension,current):
        return self.always_refine or current<self.minimum.get(dimension.value,0)
