"""Small bounded LRU of isolated results, keyed by actual generation inputs."""
from collections import OrderedDict
import copy
from .dependency import DependencyGraph
from ..core.seed import digest


class ResultCache:
    def __init__(self,capacity:int=1024):
        if capacity<0: raise ValueError('Invalid cache capacity')
        self.capacity=capacity; self.entries=OrderedDict(); self.dependencies=DependencyGraph()
        self.hits=0; self.misses=0
    @staticmethod
    def key(node,provider,time,parameters,constraints=()):
        return digest(node.id,node.version,node.seed,node.type_id,node.domain.to_data(),
                      node.semantic_state,time if provider.time_dependent else None,
                      provider.key,provider.version,parameters,
                      [c.to_data() for c in constraints])
    def get(self,key):
        if key not in self.entries:
            self.misses+=1; return None
        self.hits+=1; self.entries.move_to_end(key)
        return copy.deepcopy(self.entries[key])
    def put(self,key,value,dependencies=()):
        if not self.capacity: return
        self.entries[key]=copy.deepcopy(value); self.entries.move_to_end(key)
        self.dependencies.record(key,dependencies)
        while len(self.entries)>self.capacity:
            old,_=self.entries.popitem(last=False); self.dependencies.remove(old)
    def invalidate(self,token):
        keys=self.dependencies.affected(token)
        for key in keys:
            self.entries.pop(key,None); self.dependencies.remove(key)
        return keys
    def clear(self):
        self.entries.clear(); self.dependencies=DependencyGraph()
