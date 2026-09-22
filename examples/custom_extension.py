"""A new Thing, Process, Event, Refiner and Representation, without core edits."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from procedural_world import World,WorldSettings,Thing,Process,Dimension,RefinementState
from procedural_world.core.domain import Bounds,VolumeDomain
from procedural_world.core.event import Event,handle_update
from procedural_world.core.scope import Scope,TimeInterval
from procedural_world.core.seed import stable_id,derive_seed
from procedural_world.world.bootstrap import default_registry
from procedural_world.refinement.refiner import Refiner,RefinementResult
from procedural_world.refinement.overrides import NodeOverride
from procedural_world.representation.provider import RepresentationProvider
from procedural_world.representation.geometry import GeometryBundle,box_instance
from procedural_world.representation.export import export_obj


class StatuePlinthRefiner(Refiner):
    key='example.statue.plinth'; supported_types=('StoneStatue',); capability='plinth composition'
    def refine(self,node,context):
        b=node.domain.bounds
        domain=VolumeDomain(Bounds(b.minimum,(*b.maximum[:2],b.minimum[2]+1)))
        plinth=Thing(stable_id(node.id,'Plinth','base'),'Plinth',derive_seed(node.seed,'plinth'),domain,
                     {'material':'stone'},(node.id,),created_at=node.created_at)
        return RefinementResult(Dimension.STRUCTURAL,1,{'has_plinth':True},(plinth,))


class StatueProvider(RepresentationProvider):
    key='example.statue.geometry'; supported_types=('StoneStatue',); max_level=1
    def realize(self,node,detail_request,context):
        b=node.domain.bounds; x,y,z=b.center; w,d,h=b.size
        if not detail_request: return GeometryBundle(instances=(box_instance(b.center,b.size,'generic'),))
        return GeometryBundle(instances=(box_instance((x,y,z+.5),(w*.45,d*.45,h-1),'generic'),))


class WeatheringProcess(Process):
    def evaluate(self,world_state,time_interval,context):
        statue_id=self.semantic_state['statue_id']; time=1950.
        if not time_interval.contains(time): return []
        return [Event(stable_id(statue_id,'Event','patina'),'WeatherStatue',time,statue_id,
                      {'facts':{'patina':'aged_stone'}},self.id,priority=40)]


def main():
    registry=default_registry()
    registry.register_type('StoneStatue','Thing',category='Props')
    registry.register_type('Plinth','Thing',category='Props')
    registry.register_type('WeatheringProcess','Process',category='Debug')
    registry.register_refiner(StatuePlinthRefiner()); registry.register_representation(StatueProvider())
    registry.register('events','WeatherStatue',handle_update,'1.0.0')
    registry.register('processes','WeatheringProcess',WeatheringProcess,'1.0.0')
    world=World(WorldSettings(settlement_probability=0),registry=registry)
    ground=world.environment.height(0,0)
    statue=Thing('example_statue','StoneStatue',77,VolumeDomain(Bounds((-2,-2,ground),(2,2,ground+8))),
                 {'material':'stone'},(world.id,),created_at=1900)
    world.add_thing(statue)
    process=WeatheringProcess('weathering','WeatheringProcess',88,statue.domain,{'statue_id':statue.id},
                             (world.id,),created_at=1900)
    world.add_thing(process)
    interval=TimeInterval(1900,2025)
    scope=Scope(statue.domain,world.settings.seed,process.seed,2025,interval,environment=world.environment)
    world.events.extend(process.evaluate(world.graph(),interval,scope))
    snapshot=world.snapshot(radius=50,halo=1,request=RefinementState(1,1,0,0),
                           overrides={statue.id:NodeOverride(always_refine=True)})
    assert snapshot.graph[statue.id].semantic_state['patina']=='aged_stone'
    assert snapshot.graph[statue.id].semantic_state['has_plinth']
    export_obj(snapshot.scene,'extension_output/statue.obj')
    world.save('extension_output/world.json')
    print('Custom extension generated. Re-register these types/providers before loading its saved world.')


if __name__=='__main__': main()
