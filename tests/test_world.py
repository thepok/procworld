from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest
from procedural_world import World,WorldSettings,RefinementState,Budget,Camera,Thing,Dimension
from procedural_world.core.constraints import InfluenceField,CommitmentViolation
from procedural_world.core.domain import AreaDomain
from procedural_world.core.serialization import world_to_data,world_from_data
from procedural_world.core.seed import stable_id,canonical
from procedural_world.refinement.budget import Cost,BudgetLedger
from procedural_world.refinement.cache import ResultCache
from procedural_world.refinement.dependency import DependencyGraph
from procedural_world.refinement.overrides import NodeOverride
from procedural_world.refinement.refiner import Refiner,RefinementResult
from procedural_world.buildings.lifecycle import building_for_parcel
from procedural_world.world.fields import WorldFields
from procedural_world.representation.geometry import GeometryBundle,Mesh
from procedural_world.representation.export import export_obj,export_svg


class FieldTests(unittest.TestCase):
    def test_field_repeatability(self):
        a=WorldFields(12); b=WorldFields(12)
        for x,y in ((0,0),(-100,-200),(1536,768),(1000000,-3000000)):
            self.assertEqual(a.sample(x,y),b.sample(x,y))
    def test_expansion_cannot_change_fields(self):
        f=WorldFields(12); small={(x,y):f.height(x,y) for x in range(-50,51,25) for y in range(-50,51,25)}
        for x in range(-1000,1001,100): f.sample(x,x)
        self.assertEqual(small,{p:f.height(*p) for p in small})
    def test_negative_coordinate_continuity(self):
        f=WorldFields(12)
        self.assertLess(abs(f.height(-1e-5,0)-f.height(1e-5,0)),.001)
    def test_normal_is_unit(self):
        n=WorldFields(12).normal(100,200)
        self.assertAlmostEqual(sum(v*v for v in n),1)
    def test_ocean_is_not_forced_to_be_a_city(self):
        w=World(WorldSettings(seed=42)); w.ensure_region((0,0),2025)
        self.assertFalse(any(n.type_id=='City' for n in w.graph().nodes.values()))


class WorldHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world=World(); cls.world.ensure_region((0,0),2025)
    def test_settlement_and_roads_exist(self):
        types={n.type_id for n in self.world.graph().active(2025)}
        self.assertTrue({'City','District','Road','Block','Parcel','Building','Park'}<=types)
    def test_prefix_history_is_stable(self):
        old=World(); old.ensure_region((0,0),1800)
        a={e.id:e.to_data() for e in old.events.ordered(1800)}
        b={e.id:e.to_data() for e in self.world.events.ordered(1800)}
        self.assertEqual(a,b)
    def test_historical_replay_matches_fresh_world(self):
        old=World(); old.ensure_region((0,0),1800)
        self.assertEqual(old.graph(1800).fingerprint(),self.world.graph(1800).fingerprint())
    def test_replacement_keeps_parcel_identity(self):
        graph=self.world.graph(); parcels={}
        for n in graph.nodes.values():
            if n.type_id=='Building': parcels.setdefault(n.parent_ids[0],[]).append(n)
        replaced=[v for v in parcels.values() if len(v)>1]
        self.assertTrue(replaced)
        for lineage in replaced:
            lineage.sort(key=lambda n:n.created_at)
            for a,b in zip(lineage,lineage[1:]):
                self.assertNotEqual(a.id,b.id); self.assertEqual(a.parent_ids,b.parent_ids)
                self.assertLessEqual(a.destroyed_at,b.created_at)
    def test_active_buildings_respect_lifetimes(self):
        for year in (1750,1800,1850,1900,1950,2025):
            for n in self.world.graph(year).active(year):
                self.assertLessEqual(n.created_at,year)
                self.assertTrue(n.destroyed_at is None or year<n.destroyed_at)
    def test_parent_domains_contain_generated_children(self):
        graph=self.world.graph()
        for n in graph.nodes.values():
            if n.provenance.get('crosses_parent_boundary'): continue
            for pid in n.parent_ids: self.assertTrue(graph[pid].domain.contains_domain(n.domain),(pid,n.id))
    def test_region_expansion_preserves_existing_events(self):
        w=World(); w.ensure_region((0,0),2025); before={k:e.to_data() for k,e in w.events.events.items()}
        w.ensure_region((1,0),2025)
        self.assertTrue(all(w.events.events[k].to_data()==v for k,v in before.items()))
    def test_no_build_constraint(self):
        constraint=InfluenceField('reserve','NoBuildArea',AreaDomain.rectangle(-760,-760,760,760))
        w=World(constraints=(constraint,)); w.ensure_region((0,0),2025)
        self.assertFalse(any(n.type_id=='Building' for n in w.graph().nodes.values()))
    def test_event_aggregate_matches_initial_construction(self):
        for parent in self.world.events.events.values():
            if parent.type_id!='UrbanExpansion': continue
            children=[e for e in self.world.events.events.values() if e.parent_id==parent.id]
            self.assertAlmostEqual(sum(e.payload.get('floor_area_added',0) for e in children),parent.payload['floor_area_added'])
            self.assertTrue(all(parent.time<=e.time<=parent.interval_end for e in children))
    def test_road_topology_has_persistent_endpoints(self):
        graph=self.world.graph()
        roads=[n for n in graph.nodes.values() if n.type_id=='Road']
        self.assertTrue(all(len(n.semantic_state['junction_ids'])==2 for n in roads))
        counts={}
        for n in roads:
            for key in n.semantic_state['junction_ids']: counts[key]=counts.get(key,0)+1
        self.assertGreater(max(counts.values()),2)


class BudgetCacheTests(unittest.TestCase):
    def test_budget_reservations(self):
        ledger=BudgetLedger(Budget(max_nodes=3,max_instances=2,max_triangles=10))
        self.assertTrue(ledger.reserve(Cost(nodes=2,triangles=8)))
        self.assertFalse(ledger.reserve(Cost(nodes=2)))
        self.assertEqual(ledger.used.nodes,2)
        self.assertTrue(ledger.reserve(Cost(triangles=4),Cost(triangles=8)))
        self.assertEqual(ledger.used.triangles,4)
    def test_invalid_costs_rejected(self):
        with self.assertRaises(ValueError): Cost(nodes=-1)
        with self.assertRaises(ValueError): Budget(max_nodes=-1)
        with self.assertRaises(ValueError): Budget(max_generation_time=0)
    def test_dependency_transitive_invalidation(self):
        d=DependencyGraph(); d.record('terrain',('seed',)); d.record('road',('terrain',)); d.record('chair',('room',))
        self.assertEqual(d.affected('seed'),{'seed','terrain','road'})
    def test_cache_mutation_isolation(self):
        c=ResultCache(); c.put('a',{'nested':[]},('seed',)); data=c.get('a'); data['nested'].append(1)
        self.assertEqual(c.get('a'),{'nested':[]})
        c.invalidate('seed'); self.assertIsNone(c.get('a'))
    def test_lru_is_bounded(self):
        c=ResultCache(2)
        for i in range(3): c.put(str(i),i)
        self.assertIsNone(c.get('0')); self.assertEqual(len(c.entries),2)
    def test_overrides_validate_conflicts(self):
        with self.assertRaises(ValueError): NodeOverride(minimum={'structural':2},maximum={'structural':1})
        with self.assertRaises(ValueError): NodeOverride(never_refine=True,always_refine=True)


class SnapshotTests(unittest.TestCase):
    def options(self):
        return dict(radius=250,halo=1,budget=replace(Budget.preset('PREVIEW'),max_refinements=24),request=RefinementState(0,2,0,0))
    def test_fresh_world_determinism(self):
        a=World().snapshot(**self.options()); b=World().snapshot(**self.options())
        self.assertEqual(a.fingerprint(),b.fingerprint())
    def test_camera_does_not_change_history(self):
        w=World(); w.snapshot(**self.options()); before=w.events.fingerprint()
        w.snapshot(**{**self.options(),'camera':Camera((-600,850,700),(0,0,30))})
        self.assertEqual(before,w.events.fingerprint())
    def test_geometry_budget_is_never_exceeded(self):
        b=replace(Budget.preset('PREVIEW'),max_triangles=1200,max_instances=200,max_refinements=20)
        s=World().snapshot(radius=350,halo=1,budget=b)
        self.assertLessEqual(s.scene.cost().triangles,b.max_triangles)
        self.assertLessEqual(s.scene.cost().instances,b.max_instances)
        self.assertTrue(s.report['omitted_representations'])
    def test_tiny_node_budget_degrades_to_context(self):
        s=World().snapshot(radius=100,halo=1,budget=Budget(max_nodes=20,max_refinements=0))
        self.assertLessEqual(len(s.graph),20)
        self.assertTrue(s.report['materialization']['coarse_regions'])
    def test_terrain_cache_survives_year_change(self):
        w=World(); options={**self.options(),'request':RefinementState(),'budget':replace(Budget.preset('PREVIEW'),max_refinements=0)}
        w.snapshot(time=1900,**options); hits=w.cache.hits; w.snapshot(time=2025,**options)
        self.assertGreater(w.cache.hits,hits)
    def test_missing_provider_still_renders(self):
        w=World(WorldSettings(seed=42,settlement_probability=0))
        from procedural_world.core.domain import PointDomain
        node=Thing('alien','AlienMonument',17,PointDomain((0,0,50),2),parent_ids=(w.id,),created_at=1800)
        w.add_thing(node); s=w.snapshot(radius=50,halo=1,request=RefinementState())
        self.assertIn('alien',s.scene.bundles)
    def test_failing_refiner_cannot_mutate_authoritative_node(self):
        class Bad(Refiner):
            key='bad.plugin'; supported_types=('Building',)
            def estimate_gain(self,n,c): return 1e20
            def refine(self,n,c):
                n.semantic_state['height']=-100
                raise RuntimeError('deliberate provider failure')
        w=World(); w.registry.register_refiner(Bad())
        s=w.snapshot(radius=250,halo=1,budget=replace(Budget.preset('PREVIEW'),max_refinements=2))
        self.assertTrue(any(e['refiner']=='bad.plugin' for e in s.report['scheduler']['errors']))
        self.assertTrue(all(n.semantic_state['height']>0 for n in s.graph.nodes.values() if n.type_id=='Building'))
    def test_interior_refinement_and_serialization(self):
        w=World(WorldSettings(settlement_probability=0))
        parcel=Thing('manual_parcel','Parcel',15,AreaDomain.rectangle(-15,-15,15,15),{'land_use':'residential'},(w.id,),created_at=1800)
        w.add_thing(parcel); building=building_for_parcel(parcel,0,1850,w.environment); w.add_thing(building)
        s=w.snapshot(radius=60,halo=1,request=RefinementState(3,0,0,0),include_interiors=True,
                     budget=replace(Budget.preset('DRAFT'),max_refinements=100),
                     overrides={building.id:NodeOverride(always_refine=True,minimum={'structural':1})})
        types={n.type_id for n in s.graph.nodes.values()}
        self.assertTrue({'Floor','Room','Corridor','FurnitureProxy'}<=types)
        self.assertFalse(s.report['scheduler']['errors'])
        for n in s.graph.nodes.values():
            if n.type_id in {'Floor','Room','FurnitureProxy'}:
                for pid in n.parent_ids: self.assertTrue(s.graph[pid].domain.contains_domain(n.domain))
        loaded=world_from_data(json.loads(json.dumps(world_to_data(w))))
        self.assertEqual(w.graph().fingerprint(),loaded.graph().fingerprint())
    def test_exports_are_real_files(self):
        s=World().snapshot(**self.options())
        with tempfile.TemporaryDirectory() as d:
            obj=export_obj(s.scene,Path(d)/'scene.obj'); svg=export_svg(s,Path(d)/'map.svg')
            self.assertTrue(obj.read_text().startswith('# Hierarchical'))
            self.assertIn('v ',obj.read_text()); self.assertIn('<svg',svg.read_text())
            self.assertTrue(obj.with_suffix('.mtl').exists())

    def test_global_manual_events_are_included_in_snapshots(self):
        from procedural_world.core.event import Event
        from procedural_world.core.domain import PointDomain
        w=World(WorldSettings(seed=42,settlement_probability=0))
        node=Thing('manual','Monument',3,PointDomain((0,0,60),2),{'patina':'new'},(w.id,),created_at=1800)
        w.add_thing(node)
        w.events.append(Event('manual_update','ChangeLandUse',1900,node.id,{'facts':{'patina':'aged'}}))
        s=w.snapshot(radius=50,halo=1,request=RefinementState())
        self.assertEqual(s.graph[node.id].semantic_state['patina'],'aged')
    def test_future_history_does_not_consume_past_semantic_budget(self):
        budget=Budget(max_nodes=550,max_refinements=0)
        old=World(); old.ensure_region((0,0),2025)
        a=old.snapshot(time=1800,radius=150,halo=1,budget=budget,request=RefinementState())
        b=World().snapshot(time=1800,radius=150,halo=1,budget=budget,request=RefinementState())
        self.assertEqual(a.fingerprint(),b.fingerprint())
    def test_external_plant_envelope_failure_retains_previous_geometry(self):
        from procedural_world.vegetation.morpho_adapter import MorphoPlantsAdapter
        from procedural_world.representation.geometry import box_instance
        from procedural_world.core.domain import VolumeDomain,Bounds
        adapter=MorphoPlantsAdapter(lambda req:GeometryBundle(instances=(box_instance((1000,1000,1000),(10,10,10)),)),'bad-demo-1')
        w=World(WorldSettings(seed=42,settlement_probability=0),vegetation_adapter=adapter)
        tree=Thing('manual_tree','Tree',4,VolumeDomain(Bounds((-3,-3,50),(3,3,60))),
            {'position':[0,0,50],'maximum_height':10.,'maximum_radius':3.,'maturity_age':30.,'species':'demo'},
            (w.id,),created_at=1800)
        w.add_thing(tree)
        s=w.snapshot(radius=50,halo=1,request=RefinementState(0,2,0,0),
            overrides={tree.id:NodeOverride(always_refine=True,minimum={'geometric':2})})
        self.assertEqual(s.graph[tree.id].refinement_state.geometric,1)
        self.assertTrue(any('committed tree domain' in e['error'] for e in s.report['scheduler']['errors']))
        self.assertIn(tree.id,s.scene.bundles)

    def test_core_has_no_blender_dependency(self):
        self.assertNotIn('bpy',sys.modules)


class SerializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world=World(); cls.world.ensure_region((0,0),1900)
    def test_roundtrip(self):
        data=world_to_data(self.world); loaded=world_from_data(json.loads(json.dumps(data)))
        self.assertEqual(self.world.graph(1900).fingerprint(),loaded.graph(1900).fingerprint())
        self.assertEqual(self.world.events.fingerprint(),loaded.events.fingerprint())
    def test_atomic_file_save_load(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'world.json'; self.world.save(path); loaded=World.load(path)
            self.assertEqual(loaded.events.fingerprint(),self.world.events.fingerprint())
            self.assertFalse(list(Path(d).glob('*.tmp')))
    def test_tampering_rejected(self):
        d=world_to_data(self.world); d['settings']['seed']=999
        with self.assertRaises(ValueError): world_from_data(d)
    def test_generator_version_mismatch(self):
        from procedural_world.world.bootstrap import default_registry
        r=default_registry(); r.versions['fields']='changed'
        with self.assertRaises(ValueError): world_from_data(world_to_data(self.world),registry=r)
    def test_geometry_is_not_persisted(self):
        data=world_to_data(self.world)
        self.assertNotIn('geometry',data); self.assertNotIn('camera',data)


if __name__=='__main__': unittest.main()
