"""Built-ins register here; applications can pass an independently extended Registry."""
from ..core.registry import Registry
from ..core.event import register_events


def default_registry():
    r=Registry()
    r.register_type('ProceduralNode')
    r.register_type('Thing','ProceduralNode')
    r.register_type('Process','ProceduralNode')
    for name,parent,container,category in (
        ('World','Thing',True,'Debug'),('Region','Thing',True,'Debug'),
        ('Terrain','Thing',False,'Terrain'),('Water','Thing',False,'Water'),
        ('Ocean','Water',False,'Water'),('Lake','Water',False,'Water'),('River','Water',False,'Water'),
        ('Wetland','Water',False,'Water'),('Settlement','Thing',True,'Buildings'),
        ('City','Settlement',True,'Buildings'),('District','Thing',True,'Debug'),
        ('Road','Thing',False,'Roads'),('Block','Thing',True,'Debug'),('Parcel','Thing',True,'Debug'),
        ('Building','Thing',False,'Buildings'),('Floor','Thing',False,'Props'),
        ('Room','Thing',False,'Props'),('Corridor','Thing',False,'Props'),('VerticalCore','Thing',False,'Props'),
        ('Furniture','Thing',False,'Props'),('FurnitureProxy','Furniture',False,'Props'),
        ('Vegetation','Thing',False,'Vegetation'),('Forest','Vegetation',False,'Vegetation'),
        ('Park','Vegetation',False,'Vegetation'),('Tree','Vegetation',False,'Vegetation'),
        ('UrbanGrowthProcess','Process',False,'Debug')):
        r.register_type(name,parent,container,category)
    register_events(r)
    from ..urban.city_growth import CityGrowthProcess
    r.register('processes','UrbanGrowthProcess',CityGrowthProcess,'1.0.0')
    from ..refinement.refiner import GeometricRefiner,HistoricalRefiner,UrbanBehaviorRefiner
    from ..buildings.structure import BuildingFloorsRefiner,FloorRoomsRefiner,RoomFurnitureRefiner
    from ..vegetation.vegetation import VegetationRefiner,VegetationAreaProvider,TreeProvider
    from ..terrain.terrain_geometry import TerrainProvider,WaterProvider,RoadProvider
    from ..buildings.geometry import BuildingProvider,InteriorProvider,SettlementMassProvider
    for refiner in (GeometricRefiner(),HistoricalRefiner(),UrbanBehaviorRefiner(),BuildingFloorsRefiner(),
                    FloorRoomsRefiner(),RoomFurnitureRefiner(),VegetationRefiner()):
        r.register_refiner(refiner)
    for provider in (TerrainProvider(),WaterProvider(),RoadProvider(),BuildingProvider(),InteriorProvider(),
                     SettlementMassProvider(),VegetationAreaProvider(),TreeProvider()):
        r.register_representation(provider)
    r.versions.update({'core':'1.1.0','fields':'1.0.0','settlement_policy':'1.0.0','hydrology':'1.0.0',
                       'building_lifecycle':'2.0.0'})
    return r
