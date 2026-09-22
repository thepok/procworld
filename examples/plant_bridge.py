"""An executable adapter contract demonstration, NOT a Morpho Plants integration.

Replace bounded_demo_plant with a callable translating PlantRequest into your
actual plant generator's documented API, and translate its mesh/instances back
into GeometryBundle. The scheduler retains proxy geometry if that callable fails.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from procedural_world.vegetation.morpho_adapter import MorphoPlantsAdapter,PlantRequest
from procedural_world.representation.geometry import GeometryBundle,Instance,box_instance
from procedural_world.core.scope import Transform


def bounded_demo_plant(request:PlantRequest) -> GeometryBundle:
    x,y,z=request.position; h=request.maximum_height; r=request.maximum_radius
    return GeometryBundle(instances=(
        box_instance((x,y,z+h*.3),(r*.16,r*.16,h*.6),'bark'),
        Instance('canopy',Transform((x,y,z+h*.7),(r*1.8,r*1.8,h*.6)),'foliage')))


adapter=MorphoPlantsAdapter(bounded_demo_plant,version='demo-bounded-plant-1')
# Usage: World(vegetation_adapter=adapter).snapshot(...)


if __name__=='__main__':
    request=PlantRequest('demo',12,'broadleaf',30,(0,0,0),12,3,{'moisture':.5},2)
    print(adapter.realize(request).to_data())
