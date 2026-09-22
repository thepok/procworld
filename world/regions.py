"""Canonical ownership cells are independent of the requested visible region."""
from __future__ import annotations
import math
from ..core.domain import Bounds,AreaDomain,VolumeDomain,SurfaceDomain,CurveDomain
from ..core.node import Thing,Process
from ..core.event import create_event
from ..core.seed import stable_id,derive_seed,RandomStream
from ..terrain.hydrology import drainage_path

EPOCH=-1000000.


def region_coordinates(center,radius,size):
    if radius<0 or not math.isfinite(radius): raise ValueError('Invalid region radius')
    x,y=center; half=size/2
    x0=math.floor((x-radius+half)/size); x1=math.floor((x+radius+half)/size)
    y0=math.floor((y-radius+half)/size); y1=math.floor((y+radius+half)/size)
    if (x1-x0+1)*(y1-y0+1)>10000:
        raise ValueError('Request exceeds 10,000 owner regions; use tiled offline requests')
    return sorted(((i,j) for i in range(x0,x1+1) for j in range(y0,y1+1)),
                  key=lambda c:((c[0]*size-x)**2+(c[1]*size-y)**2,c))


def region_domain(coord,size):
    cx,cy=(c*size for c in coord); half=size/2
    return VolumeDomain(Bounds((cx-half,cy-half,-2000),(cx+half,cy+half,5000)))


def static_region_events(world_id,settings,fields,coord):
    seed=derive_seed(settings.seed,'region',coord)
    rid=stable_id(world_id,'Region',coord); domain=region_domain(coord,settings.region_size)
    region=Thing(rid,'Region',seed,domain,{'coordinate':list(coord)},(world_id,),created_at=EPOCH)
    events=[create_event(region,'CreateRegion',priority=0)]
    area=AreaDomain.rectangle(*domain.bounds.minimum[:2],*domain.bounds.maximum[:2])
    terrain=Thing(stable_id(rid,'Terrain','surface'),'Terrain',derive_seed(seed,'terrain'),
                  SurfaceDomain(area,settings.sea_level-250,settings.sea_level+350),
                  {'field_version':fields.version},(rid,),created_at=EPOCH)
    events.append(create_event(terrain,priority=2))
    ocean=Thing(stable_id(rid,'Ocean','sea'),'Ocean',derive_seed(seed,'water'),
                AreaDomain.rectangle(*domain.bounds.minimum[:2],*domain.bounds.maximum[:2],settings.sea_level),
                {'water_level':settings.sea_level},(rid,),created_at=EPOCH)
    events.append(create_event(ocean,priority=2))
    points,sink=drainage_path(fields,coord,settings.region_size,settings.seed)
    if len(points)>2:
        river=Thing(stable_id(rid,'River','drainage'),'River',derive_seed(seed,'river'),CurveDomain(points,5.),
                    {'source_owner':list(coord),'drains_to_sink':sink},(rid,),created_at=EPOCH,
                    provenance={'crosses_parent_boundary':True,'generator':'downhill_drainage','version':'1.0.0'})
        events.append(create_event(river,priority=2))
        if sink:
            x,y,z=points[-1]; half=12
            lake=Thing(stable_id(river.id,'Lake','sink'),'Lake',derive_seed(seed,'lake'),
                       AreaDomain.rectangle(x-half,y-half,x+half,y+half,z),{'water_level':z},(rid,),
                       created_at=EPOCH,provenance={'crosses_parent_boundary':True})
            events.append(create_event(lake,priority=2))
    cx,cy=domain.anchor[:2]; rng=RandomStream(seed,'forest')
    for k,(sx,sy) in enumerate(((-1,-1),(-1,1),(1,-1),(1,1))):
        x=cx+sx*settings.region_size*.35; y=cy+sy*settings.region_size*.35
        if fields.height(x,y)<=settings.sea_level+1: continue
        half=settings.region_size*.09
        forest_area=AreaDomain.rectangle(x-half,y-half,x+half,y+half)
        forest=Thing(stable_id(rid,'Forest',k),'Forest',derive_seed(seed,'forest',k),forest_area,
                     {'tree_count':24,'species':'broadleaf','maximum_height':18.,'biome':fields.biome(x,y)},
                     (rid,),created_at=settings.initial_year-100)
        events.append(create_event(forest,'CreateForest',priority=5))
    process=Process(stable_id(rid,'UrbanGrowthProcess','growth'),'UrbanGrowthProcess',derive_seed(seed,'urban_process'),
                    domain,{'region_coordinate':list(coord),'behavioral_level':settings.behavioral_level},
                    (rid,),created_at=EPOCH)
    events.append(create_event(process,priority=1))
    return rid,process,events
