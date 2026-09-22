"""Injection boundary for a plant generator supplied by an application.

No Morpho Plants source/API was included in the specification. This bridge
accepts an explicit callable rather than guessing an undocumented module/API.
"""
from dataclasses import dataclass
from typing import Callable
from ..representation.geometry import GeometryBundle


@dataclass(frozen=True,slots=True)
class PlantRequest:
    semantic_id: str
    seed: int
    species: str
    age: float
    position: tuple[float,float,float]
    maximum_height: float
    maximum_radius: float
    environment: dict
    detail_requirement: int


class MorphoPlantsAdapter:
    def __init__(self,generate:Callable[[PlantRequest],GeometryBundle],version:str):
        if not callable(generate) or not version:
            raise ValueError('Supply a generation callable and an implementation version')
        self.generate=generate; self.version=str(version)
    def realize(self,request:PlantRequest) -> GeometryBundle:
        geometry=self.generate(request)
        if not isinstance(geometry,GeometryBundle):
            raise TypeError('A plant adapter must return a GeometryBundle')
        geometry.cost()
        return geometry
