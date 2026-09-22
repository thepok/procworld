import unittest
from types import SimpleNamespace

from procedural_world.core.domain import AreaDomain,PrismDomain,domain_from_data
from procedural_world.core.node import Thing
from procedural_world.buildings.lifecycle import building_for_parcel
from procedural_world.buildings.structure import BuildingFloorsRefiner,FloorRoomsRefiner
from procedural_world.buildings.geometry import BuildingProvider
from procedural_world.world.fields import WorldFields


class PolygonBuildingTests(unittest.TestCase):
    def parcel(self,seed=1,usage='residential'):
        return Thing(f'parcel-{seed}','Parcel',seed,AreaDomain.rectangle(0,0,42,32),
                     {'land_use':usage},created_at=1800)

    def irregular_building(self):
        environment=WorldFields(123)
        for seed in range(1,80):
            building=building_for_parcel(self.parcel(seed),0,1910,environment)
            if len(building.semantic_state['footprint'])>4:
                return building
        self.fail('Expected at least one deterministic irregular footprint')

    def test_generated_buildings_are_not_forced_to_rectangles(self):
        environment=WorldFields(123)
        kinds=set(); vertex_counts=set()
        for seed in range(1,50):
            b=building_for_parcel(self.parcel(seed),0,1910,environment)
            kinds.add(b.semantic_state['footprint_kind'])
            vertex_counts.add(len(b.semantic_state['footprint']))
            self.assertIsInstance(b.domain,PrismDomain)
            self.assertTrue(self.parcel(seed).domain.contains_domain(b.domain))
        self.assertTrue(kinds-{'rectangle'})
        self.assertTrue(any(n>4 for n in vertex_counts))

    def test_footprint_generation_is_deterministic(self):
        environment=WorldFields(123); parcel=self.parcel(17)
        a=building_for_parcel(parcel,0,1910,environment)
        b=building_for_parcel(parcel,0,1910,environment)
        self.assertEqual(a.to_data(),b.to_data())

    def test_prism_domain_roundtrip_preserves_concavity(self):
        area=AreaDomain(((0,0,0),(10,0,0),(10,4,0),(4,4,0),(4,10,0),(0,10,0)))
        domain=PrismDomain(area,2,14)
        loaded=domain_from_data(domain.to_data())
        self.assertEqual(domain,loaded)
        self.assertFalse(domain.contains_point((8,8,5)))
        self.assertTrue(domain.contains_point((2,8,5)))

    def test_floor_refinement_keeps_exact_polygon(self):
        building=self.irregular_building()
        result=BuildingFloorsRefiner().refine(building,None)
        floors=[c for c in result.children if c.type_id=='Floor']
        self.assertEqual(len(floors),building.semantic_state['floor_count'])
        parent_xy=tuple((p[0],p[1]) for p in building.domain.area.vertices)
        for floor in floors:
            self.assertIsInstance(floor.domain,PrismDomain)
            self.assertEqual(parent_xy,tuple((p[0],p[1]) for p in floor.domain.area.vertices))
            self.assertTrue(building.domain.contains_domain(floor.domain))

    def test_room_planner_never_escapes_concave_floor(self):
        building=self.irregular_building()
        floors=[c for c in BuildingFloorsRefiner().refine(building,None).children if c.type_id=='Floor']
        result=FloorRoomsRefiner().refine(floors[0],None)
        self.assertTrue(result.children)
        for child in result.children:
            self.assertTrue(floors[0].domain.contains_domain(child.domain))

    def test_coarse_geometry_uses_polygon_not_aabb_box(self):
        building=self.irregular_building()
        bundle=BuildingProvider().realize(building,0,SimpleNamespace(include_interiors=False))
        self.assertEqual(len(bundle.instances),0)
        self.assertEqual(len(bundle.meshes),1)
        mesh=bundle.meshes[0]
        footprint_vertices=len(building.domain.area.vertices)
        self.assertEqual(len(mesh.vertices),footprint_vertices*2)
        self.assertGreater(mesh.triangle_count,12)


if __name__=='__main__':
    unittest.main()
