import unittest
from types import SimpleNamespace

from procedural_world.core.node import Thing
from procedural_world.core.domain import AreaDomain,Bounds,VolumeDomain
from procedural_world.buildings.archetypes import architectural_profile,era_for
from procedural_world.buildings.lifecycle import building_for_parcel
from procedural_world.buildings.geometry import BuildingProvider,BuildingCoreProvider
from procedural_world.buildings.structure import BuildingCoreRefiner,FloorRoomsRefiner,RoomFurnitureRefiner
from procedural_world.world.world import World


class BuildingArchetypeTests(unittest.TestCase):
    def test_era_boundaries(self):
        self.assertEqual(era_for(1779),'preindustrial')
        self.assertEqual(era_for(1900),'historicist')
        self.assertEqual(era_for(1960),'postwar')
        self.assertEqual(era_for(2025),'contemporary')

    def test_architectural_profile_is_deterministic(self):
        a=architectural_profile('residential',1905,12345,5,22,30)
        b=architectural_profile('residential',1905,12345,5,22,30)
        self.assertEqual(a,b)
        self.assertIn(a['roof_type'],{'gable','hip','flat','shed'})
        self.assertGreater(a['window_width'],0)

    def test_usage_changes_program(self):
        residential=architectural_profile('residential',2020,5,7,22,30)
        industrial=architectural_profile('industrial',2020,5,2,22,30)
        commercial=architectural_profile('commercial',2020,5,7,22,30)
        self.assertNotEqual(residential['archetype'],industrial['archetype'])
        self.assertEqual(commercial['ground_floor_mode'],'storefront')
        self.assertEqual(industrial['ground_floor_mode'],'loading')


class BuildingGenerationTests(unittest.TestCase):
    def setUp(self):
        self.world=World()
        self.parcel=Thing('parcel','Parcel',77,AreaDomain.rectangle(-20,-25,20,25),
                          {'land_use':'residential'},(self.world.id,),created_at=1800)
        self.building=building_for_parcel(self.parcel,0,2008,self.world.environment)

    def test_style_is_semantic_state(self):
        state=self.building.semantic_state
        for key in ('archetype','style_era','roof_type','facade_material','window_width','has_elevator'):
            self.assertIn(key,state)
        committed={c.path for c in self.building.commitments}
        self.assertIn('archetype',committed)
        self.assertIn('roof_type',committed)

    def test_exterior_detail_is_progressive(self):
        provider=BuildingProvider(); context=SimpleNamespace(include_interiors=False)
        bundles=[provider.realize(self.building,level,context) for level in range(5)]
        costs=[b.cost() for b in bundles]
        self.assertGreater(costs[1].triangles,costs[0].triangles)
        self.assertGreater(costs[2].instances,costs[1].instances)
        self.assertGreater(costs[3].instances,costs[2].instances)
        self.assertGreater(costs[4].instances,costs[3].instances)

    def test_vertical_core_stays_inside_envelope(self):
        node=self.building.copy(); node.refinement_state.structural=1
        node.semantic_state['has_elevator']=True
        result=BuildingCoreRefiner().refine(node,None)
        self.assertEqual(result.level,2)
        self.assertTrue(result.children)
        for child in result.children:
            self.assertTrue(node.domain.contains_domain(child.domain))

    def test_core_geometry_can_refine(self):
        node=self.building.copy(); node.refinement_state.structural=1
        core=BuildingCoreRefiner().refine(node,None).children[0]
        provider=BuildingCoreProvider(); context=SimpleNamespace(include_interiors=True)
        coarse=provider.realize(core,0,context); detailed=provider.realize(core,1,context)
        self.assertGreater(detailed.cost().instances,coarse.cost().instances)


class InteriorProgramTests(unittest.TestCase):
    def _floor(self,usage):
        return Thing('floor-'+usage,'Floor',8,VolumeDomain(Bounds((0,0,0),(20,24,3.2))),
                     {'floor_index':0,'floor_count':4,'usage':usage,'archetype':'test','floor_area':480,'ground_floor':True},
                     created_at=1900)

    def test_room_program_depends_on_use(self):
        residential=FloorRoomsRefiner().refine(self._floor('residential'),None)
        commercial=FloorRoomsRefiner().refine(self._floor('commercial'),None)
        r={n.semantic_state.get('use') for n in residential.children if n.type_id=='Room'}
        c={n.semantic_state.get('use') for n in commercial.children if n.type_id=='Room'}
        self.assertIn('bedroom',r)
        self.assertIn('kitchen',r)
        self.assertIn('retail',c)
        self.assertNotEqual(r,c)

    def test_furniture_matches_room_program_and_stays_inside(self):
        room=Thing('room','Room',9,VolumeDomain(Bounds((0,0,0),(8,7,3))),
                   {'use':'bedroom','floor_area':56},created_at=1900)
        result=RoomFurnitureRefiner().refine(room,None)
        kinds={n.semantic_state['furniture_type'] for n in result.children}
        self.assertIn('Bed',kinds)
        self.assertIn('Wardrobe',kinds)
        for child in result.children:
            self.assertTrue(room.domain.contains_domain(child.domain))


if __name__=='__main__':
    unittest.main()
