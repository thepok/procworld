import copy
import json
import math
import os
import subprocess
import sys
import unittest
from procedural_world.core.seed import RandomStream,derive_seed,stable_id,canonical
from procedural_world.core.domain import *
from procedural_world.core.node import Thing,Process,Dimension,RefinementState
from procedural_world.core.graph import SemanticGraph
from procedural_world.core.constraints import Commitment,CommitmentViolation,InfluenceField
from procedural_world.core.scope import Scope,TimeInterval
from procedural_world.core.event import Event,EventLog,create_event,AggregateRequirement,register_events
from procedural_world.core.registry import Registry
from procedural_world.representation.fallback import fallback
from procedural_world.representation.geometry import GeometryBundle,Mesh,triangulate_polygon


class SeedTests(unittest.TestCase):
    def test_repeatability(self):
        self.assertEqual(derive_seed(17,'facade',5),derive_seed(17,'facade',5))
    def test_namespaces_are_isolated(self):
        a=RandomStream(12); before=a.unit('facade')
        for i in range(100): a.unit('furniture',i)
        self.assertEqual(before,a.unit('facade'))
        self.assertNotEqual(a.unit('facade'),a.unit('structure'))
    def test_identity_is_not_geometry(self):
        self.assertEqual(stable_id('parcel','Building',1),stable_id('parcel','Building',1))
        self.assertNotEqual(stable_id('parcel','Building',1),stable_id('parcel','Building',2))
    def test_canonical_mapping_order(self):
        self.assertEqual(canonical({'b':1,'a':2}),canonical({'a':2,'b':1}))
    def test_nan_is_rejected(self):
        with self.assertRaises(ValueError): canonical({'x':float('nan')})
    def test_random_bounds(self):
        r=RandomStream(5)
        for i in range(100):
            self.assertTrue(0<=r.unit(i)<1); self.assertTrue(2<=r.integer(2,5,i)<=5)
        with self.assertRaises(ValueError): r.choice([])


class DomainTests(unittest.TestCase):
    def domains(self):
        area=AreaDomain.rectangle(0,0,10,10)
        return [UnboundedDomain(),PointDomain((1,2,3),.5),CurveDomain(((0,0,0),(5,5,1)),2),area,
                VolumeDomain(Bounds((0,0,0),(10,10,10))),SurfaceDomain(area,-2,3),
                NetworkDomain(((0,0,0),(1,0,0)),((0,1),),1)]
    def test_roundtrip_every_domain(self):
        for d in self.domains():
            with self.subTest(type=d.type_id):
                self.assertEqual(d,domain_from_data(json.loads(canonical(d.to_data()))))
    def test_all_domains_have_fallback(self):
        for i,d in enumerate(self.domains()):
            geometry=fallback(Thing(str(i),'Unknown',i,d))
            self.assertIsInstance(geometry,GeometryBundle)
            if not isinstance(d,UnboundedDomain): self.assertGreater(geometry.cost().triangles,0)
    def test_vertical_curve_fallback(self):
        n=Thing('v','Cable',1,CurveDomain(((0,0,0),(0,0,10)),.2))
        self.assertGreater(fallback(n).cost().triangles,0)
    def test_concave_containment_rejects_crossing_edge(self):
        # A U shape: endpoints can be inside while the connecting edge escapes.
        u=AreaDomain(((0,0,0),(6,0,0),(6,6,0),(4,6,0),(4,2,0),(2,2,0),(2,6,0),(0,6,0)))
        child=AreaDomain.rectangle(1,3,5,4)
        self.assertTrue(u.contains_point((1,3,0))); self.assertTrue(u.contains_point((5,3,0)))
        self.assertFalse(u.contains_domain(child))
    def test_concave_triangulation_preserves_area(self):
        v=((0,0,0),(4,0,0),(4,1,0),(1,1,0),(1,4,0),(0,4,0))
        triangles=triangulate_polygon(v)
        area=sum(abs((v[b][0]-v[a][0])*(v[c][1]-v[a][1])-(v[c][0]-v[a][0])*(v[b][1]-v[a][1]))/2 for a,b,c in triangles)
        self.assertAlmostEqual(area,7.)
    def test_invalid_shapes_rejected(self):
        with self.assertRaises(ValueError): Bounds((1,0,0),(0,1,1))
        with self.assertRaises(ValueError): CurveDomain(((0,0,0),))
        with self.assertRaises(ValueError): PointDomain((math.nan,0,0))
        with self.assertRaises(ValueError): NetworkDomain(((0,0,0),),((0,1),))

    def test_commitment_does_not_alias_source_value(self):
        value=[1,2]; c=Commitment('footprint',value); value.append(3)
        self.assertEqual(c.value,[1,2])
    def test_degenerate_network_still_renders(self):
        n=Thing('dot','NetworkMarker',1,NetworkDomain(((0,0,0),),()))
        self.assertGreater(fallback(n).cost().triangles,0)
    def test_conflicting_builtin_prototype_is_rejected(self):
        from procedural_world.representation.geometry import PROTOTYPES
        mesh=Mesh(((0,0,0),(1,0,0),(0,1,0)),((0,1,2),))
        with self.assertRaises(ValueError): GeometryBundle(prototypes=(('unit_box',mesh),))

    def test_volume_contains(self):
        p=VolumeDomain(Bounds((0,0,0),(10,10,10)))
        self.assertTrue(p.contains_domain(VolumeDomain(Bounds((1,1,1),(9,9,9)))))
        self.assertFalse(p.contains_domain(VolumeDomain(Bounds((1,1,1),(11,9,9)))))


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.graph=SemanticGraph()
        self.parent=Thing('p','Building',1,VolumeDomain(Bounds((0,0,0),(10,10,10))),
                          {'height':10},created_at=1800,commitments=(Commitment('height',10),))
        self.graph.add(self.parent)
    def child(self):
        return Thing('c','Floor',2,VolumeDomain(Bounds((1,1,1),(9,9,3))),{},('p',),created_at=1800)
    def test_four_independent_dimensions(self):
        self.graph.refine('p',Dimension.GEOMETRIC,1)
        s=self.graph['p'].refinement_state
        self.assertEqual(s.to_data(),{'structural':0,'geometric':1,'temporal':0,'behavioral':0})
    def test_refinement_is_additive(self):
        self.graph.refine('p',Dimension.STRUCTURAL,1,{'extra':'fact'},(self.child(),))
        self.assertEqual(self.graph['p'].semantic_state['height'],10)
        self.assertEqual(self.graph['p'].child_ids,('c',))
    def test_conflicting_refinement_is_atomic(self):
        before=self.graph.fingerprint()
        with self.assertRaises(CommitmentViolation): self.graph.refine('p',Dimension.STRUCTURAL,1,{'height':11},(self.child(),))
        self.assertEqual(self.graph.fingerprint(),before)
    def test_escaping_child_is_atomic(self):
        c=self.child(); c.domain=VolumeDomain(Bounds((0,0,0),(20,20,20))); before=self.graph.fingerprint()
        with self.assertRaises(CommitmentViolation): self.graph.refine('p',Dimension.STRUCTURAL,1,{},(c,))
        self.assertEqual(self.graph.fingerprint(),before)
    def test_commitments_apply_to_events(self):
        with self.assertRaises(CommitmentViolation): self.graph.update('p',{'height':20})
        self.assertEqual(self.graph['p'].semantic_state['height'],10)
    def test_destruction_cascades(self):
        self.graph.add(self.child()); self.graph.destroy('p',1900)
        self.assertTrue(self.graph.is_active('c',1899)); self.assertFalse(self.graph.is_active('c',1900))
        self.assertEqual(self.graph['c'].destroyed_at,1900)
    def test_child_cannot_predate_parent(self):
        c=self.child(); c.created_at=1799
        with self.assertRaises(CommitmentViolation): self.graph.add(c)
    def test_specialization_does_not_create_structure(self):
        r=Registry(); r.register_type('Building'); r.register_type('House','Building')
        self.graph.specialize('p','House',r)
        self.assertEqual(self.graph['p'].id,'p'); self.assertEqual(self.graph['p'].child_ids,())
        self.assertEqual(self.graph['p'].refinement_state.structural,0)
    def test_graph_roundtrip(self):
        self.graph.add(self.child())
        loaded=SemanticGraph.from_data(json.loads(canonical(self.graph.to_data())))
        self.assertEqual(loaded.fingerprint(),self.graph.fingerprint())
    def test_cycles_rejected_on_load(self):
        data=self.graph.to_data(); data[0]['parent_ids']=['missing']
        with self.assertRaises(ValueError): SemanticGraph.from_data(data)
    def test_scope_constraints_and_seed_propagate(self):
        scope=Scope(self.parent.domain,12,4,1900,TimeInterval(1800,1900),parent_constraints=self.parent.commitments)
        child=scope.child('floor',self.child().domain)
        self.assertEqual(child.parent_constraints,scope.parent_constraints)
        self.assertNotEqual(child.local_seed,scope.local_seed)


class EventTests(unittest.TestCase):
    def setUp(self):
        self.registry=Registry(); register_events(self.registry)
        self.initial=SemanticGraph(); self.initial.add(Thing('root','World',1))
    def test_replay_order_independent(self):
        p=Thing('a','Parcel',2,parent_ids=('root',),created_at=1800)
        b=Thing('b','Building',3,parent_ids=('a',),created_at=1810)
        events=[create_event(p),create_event(b)]
        a=EventLog(); a.extend(events); c=EventLog(); c.extend(reversed(events))
        self.assertEqual(a.replay(self.initial,1850,self.registry).fingerprint(),c.replay(self.initial,1850,self.registry).fingerprint())
    def test_event_idempotence(self):
        e=Event('e','UrbanExpansion',1800,'root',{},interval_end=1900)
        log=EventLog(); log.append(e); log.append(e); self.assertEqual(len(log.events),1)
    def test_collision_batch_is_atomic(self):
        log=EventLog(); log.append(Event('e','UrbanExpansion',1800,'root'))
        with self.assertRaises(CommitmentViolation):
            log.extend([Event('f','UrbanExpansion',1800,'root'),Event('e','UrbanExpansion',1801,'root')])
        self.assertNotIn('f',log.events)
    def test_coarse_event_totals_preserved(self):
        log=EventLog(); log.append(Event('p','ResidentialExpansion',1800,'root',{'total':10},interval_end=1820))
        children=(Event('a','UrbanExpansion',1802,'root',{'area':4},parent_id='p'),
                  Event('b','UrbanExpansion',1815,'root',{'area':6},parent_id='p'))
        log.refine('p',children,(AggregateRequirement('total','area'),))
        self.assertEqual(log.refinements['p'],('a','b'))
    def test_bad_aggregate_rejected(self):
        log=EventLog(); log.append(Event('p','UrbanExpansion',1800,'root',{'total':10},interval_end=1820))
        child=Event('a','UrbanExpansion',1810,'root',{'area':9},parent_id='p')
        with self.assertRaises(CommitmentViolation): log.refine('p',(child,),(AggregateRequirement('total','area'),))
        self.assertNotIn('a',log.events)
    def test_refined_event_stays_inside_interval(self):
        log=EventLog(); log.append(Event('p','UrbanExpansion',1800,'root',{},interval_end=1820))
        with self.assertRaises(CommitmentViolation):
            log.refine('p',(Event('a','UrbanExpansion',1821,'root',{},parent_id='p'),))
    def test_before_birth_is_absent(self):
        log=EventLog(); log.append(create_event(Thing('b','Building',2,parent_ids=('root',),created_at=1850)))
        self.assertNotIn('b',log.replay(self.initial,1849,self.registry).nodes)
    def test_unknown_event_is_not_silently_lost(self):
        log=EventLog(); log.append(Event('x','AlienEvent',1800,'root'))
        with self.assertRaises(ValueError): log.replay(self.initial,1900,self.registry)


if __name__=='__main__': unittest.main()
