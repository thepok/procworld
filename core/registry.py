"""Explicit extension points instead of global type switches."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True,slots=True)
class TypeDefinition:
    name: str
    parent: str|None = None
    container: bool = False
    category: str = 'Generic'


class Registry:
    def __init__(self):
        self.types: dict[str,TypeDefinition]={}
        self.processes: dict[str,object]={}
        self.refiners: dict[str,object]={}
        self.representations: dict[str,object]={}
        self.events: dict[str,object]={}
        self.versions: dict[str,str]={}
    def register_type(self,name:str,parent:str|None=None,container=False,category='Generic'):
        if name in self.types: raise ValueError(f'Type already registered: {name}')
        if parent is not None and parent not in self.types: raise ValueError(f'Unknown base type {parent}')
        self.types[name]=TypeDefinition(name,parent,container,category)
    def is_a(self,name:str,parent:str) -> bool:
        seen=set()
        while name and name not in seen:
            if name==parent: return True
            seen.add(name)
            definition=self.types.get(name)
            name=definition.parent if definition else None
        return False
    def register(self,category:str,key:str,value,version:str='1'):
        if category not in {'processes','refiners','representations','events'}:
            raise ValueError(f'Unknown registry category {category}')
        bucket=getattr(self,category)
        if key in bucket: raise ValueError(f'Duplicate {category} registration: {key}')
        bucket[key]=value; self.versions[f'{category}:{key}']=str(version)
    def register_refiner(self,refiner):
        self.register('refiners',refiner.key,refiner,refiner.version)
    def register_representation(self,provider):
        self.register('representations',provider.key,provider,provider.version)
    def provider_for(self,node):
        providers=[p for p in self.representations.values() if p.supports(node,self)]
        return max(providers,key=lambda p:(p.priority,p.key)) if providers else None
    def category_for(self,type_id):
        return self.types.get(type_id,TypeDefinition(type_id)).category
    def is_container(self,type_id):
        return self.types.get(type_id,TypeDefinition(type_id)).container
