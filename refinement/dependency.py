"""Transitive invalidation using named input and result dependency tokens."""
from collections import defaultdict


class DependencyGraph:
    def __init__(self):
        self.dependencies=defaultdict(set)
        self.dependents=defaultdict(set)
    def record(self,result:str,inputs):
        self.remove(result)
        for token in inputs:
            if token==result: raise ValueError('A result cannot depend on itself')
            self.dependencies[result].add(token); self.dependents[token].add(result)
    def remove(self,result:str):
        for token in self.dependencies.pop(result,set()):
            self.dependents[token].discard(result)
    def affected(self,token:str):
        seen=set(); stack=[token]
        while stack:
            item=stack.pop()
            if item in seen: continue
            seen.add(item); stack.extend(self.dependents.get(item,()))
        return seen
