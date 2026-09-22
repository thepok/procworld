from __future__ import annotations
from .fallback import fallback


class RepresentationProvider:
    key='representation'
    version='1'
    priority=10
    supported_types=()
    max_level=0
    time_dependent=False
    def supports(self,thing,registry):
        return any(registry.is_a(thing.type_id,t) for t in self.supported_types)
    def realize(self,thing,detail_request,context):
        return fallback(thing)


def realize(node,level,context):
    provider=context.registry.provider_for(node)
    if provider is None: return fallback(node)
    key=context.cache.key(node,provider,context.time,{'level':level,'interiors':context.include_interiors,
        'vegetation_adapter':getattr(context.vegetation_adapter,'version',None)},context.constraints)
    cached=context.cache.get(key)
    if cached is not None: return cached
    # Providers receive an isolated semantic copy, not the authoritative node.
    result=provider.realize(node.copy(),level,context)
    result.cost()  # Validate declared geometry and prototype references before caching.
    dependencies=[f'node:{node.id}',f'generator:{provider.key}','world:seed','world:constraints']
    if provider.time_dependent: dependencies.append('world:time')
    context.cache.put(key,result,dependencies)
    return result
