"""Pure refiner proposals; only the scheduler may commit their results."""
from __future__ import annotations
from dataclasses import dataclass,field
from typing import Any
from ..core.node import Dimension,ProceduralNode,RefinementState
from ..core.scope import Scope,TimeInterval
from .budget import Cost


@dataclass(frozen=True,slots=True)
class RefinementContext:
    world_seed: int
    time: float
    environment: Any
    registry: Any
    cache: Any
    camera: Any
    request: RefinementState
    budget: Any
    constraints: tuple = ()
    events: tuple = ()
    include_interiors: bool = False
    ancestor_commitments: tuple = ()
    vegetation_adapter: Any = None
    def scope_for(self,node):
        return Scope(node.domain,self.world_seed,node.seed,self.time,
                     TimeInterval(node.created_at,self.time),
                     parent_constraints=self.constraints+self.ancestor_commitments+node.commitments,
                     environment=self.environment,semantic_context={'semantic_id':node.id,'type_id':node.type_id},
                     refinement_request=self.request,generation_budget=self.budget)


@dataclass(frozen=True,slots=True)
class RefinementResult:
    dimension: Dimension
    level: int
    facts: dict = field(default_factory=dict)
    children: tuple[ProceduralNode,...] = ()
    geometry: Any = None


class Refiner:
    key='base.refiner'
    version='1.0.0'
    dimension=Dimension.STRUCTURAL
    supported_types=()
    capability='unspecified'
    required_request=1
    max_level=1
    def supports(self,node,dimension,registry):
        return dimension==self.dimension and any(registry.is_a(node.type_id,t) for t in self.supported_types)
    def can_refine(self,node,context):
        return (self.supports(node,self.dimension,context.registry) and
                context.request.get(self.dimension)>=self.required_request and
                node.refinement_state.get(self.dimension)<self.max_level)
    def estimate_cost(self,node,context): return Cost(nodes=1,memory_bytes=1024)
    def estimate_gain(self,node,context): return 1.
    def refine(self,node,context): raise NotImplementedError


class GeometricRefiner(Refiner):
    key='geometry.provider'; dimension=Dimension.GEOMETRIC; capability='provider geometry'
    def supports(self,node,dimension,registry):
        p=registry.provider_for(node)
        return node.category=='thing' and dimension==self.dimension and p is not None and p.max_level>0
    def can_refine(self,node,context):
        p=context.registry.provider_for(node)
        return (p is not None and node.category=='thing' and
                node.refinement_state.geometric<min(context.request.geometric,p.max_level))
    def estimate_cost(self,node,context):
        return Cost(triangles=64*(node.refinement_state.geometric+1),memory_bytes=2048)
    def estimate_gain(self,node,context):
        provider=context.registry.provider_for(node)
        return getattr(provider,'refinement_gain',1.)/(1+node.refinement_state.geometric)
    def refine(self,node,context):
        from ..representation.provider import realize
        level=node.refinement_state.geometric+1
        return RefinementResult(self.dimension,level,geometry=realize(node,level,context))


class HistoricalRefiner(Refiner):
    key='history.event_view'; dimension=Dimension.TEMPORAL; supported_types=('Building','Road','Block')
    capability='explicit event history'
    def estimate_cost(self,node,context): return Cost(memory_bytes=768)
    def estimate_gain(self,node,context): return .12
    def refine(self,node,context):
        events=[{'id':e.id,'type':e.type_id,'time':e.time,'source_process':e.process_id,'parent_event':e.parent_id}
                for e in context.events if e.target_id==node.id and e.time<=context.time]
        return RefinementResult(self.dimension,1,{f'history_at_{context.time:g}':events})


class UrbanBehaviorRefiner(Refiner):
    """Resolve the coarse process policy to explicit rule descriptors.

    The descriptors explain the policy used by the initial evaluator. They do
    not retroactively rerun or change committed historical events.
    """
    key='urban.policy_resolution'; dimension=Dimension.BEHAVIORAL
    supported_types=('UrbanGrowthProcess',); capability='resolved aggregate policy'
    def estimate_cost(self,node,context): return Cost(memory_bytes=512)
    def estimate_gain(self,node,context): return .15
    def refine(self,node,context):
        level=node.semantic_state.get('behavioral_level',0)
        return RefinementResult(self.dimension,1,{'resolved_policy':{
            'frontier':'connected ring growth','accessibility_weight':.5,'suitability_weight':.5,
            'slope_penalty':.8 if level>=1 else 0.,'fertility_weight':.15 if level>=2 else 0.,
            'maximum_buildable_slope':.34 if level>=1 else None,
            'construction_water_clearance':2.,'agents':False}})
