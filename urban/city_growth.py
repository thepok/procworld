"""Incremental, terrain-aware grid growth via semantic Processes and Events.

The initial policy is intentionally modest: connected grid frontiers, four-lot
blocks, broad land use, parks, and event-driven replacement. It does not claim
realistic street topology, traffic, agents, or economic equilibrium.
"""
from __future__ import annotations
from dataclasses import replace
import math
from ..core.node import Thing,Process
from ..core.domain import AreaDomain,CurveDomain
from ..core.event import Event,create_event
from ..core.constraints import Commitment
from ..core.seed import RandomStream,stable_id,derive_seed
from .parcels import subdivide_rectangular_block
from .urban_fields import DevelopmentPolicy
from ..buildings.lifecycle import lifecycle_events,building_for_parcel


class CityGrowthProcess(Process):
    def evaluate(self,world_state,time_interval,context):
        settings=context.semantic_context['settings']
        rid=context.semantic_context['region_id']
        coord=tuple(self.semantic_state['region_coordinate'])
        fields=context.environment; rng=RandomStream(context.world_seed,'settlement',coord)
        if rng.unit('exists')>settings.settlement_probability: return []
        ox,oy=(c*settings.region_size for c in coord)
        candidates=[(ox+rng.uniform(-100,100,'site_x',i),oy+rng.uniform(-100,100,'site_y',i)) for i in range(9)]
        cx,cy=max(candidates,key=lambda p:(fields.settlement_suitability(*p),p))
        if fields.settlement_suitability(cx,cy)<.14: return []
        founding=settings.initial_year+rng.uniform(0,48,'founding')
        if founding>time_interval.end: return []
        r=settings.growth_rings; s=settings.block_size; half=(r+1)*s
        city_area=AreaDomain.rectangle(cx-half-8,cy-half-8,cx+half+8,cy+half+8)
        city_id=stable_id(rid,'City','settlement')
        city=Thing(city_id,'City',derive_seed(self.seed,'city'),city_area,
                   {'name':f'Settlement {coord[0]},{coord[1]}','founding_year':founding,
                    'growth_policy':'connected_frontier_grid','behavioral_level':settings.behavioral_level},
                   (rid,),created_at=founding)
        events=[create_event(city,'CreateSettlement',self.id,6)]
        district_ids={}
        for sx in (-1,1):
            for sy in (-1,1):
                x0,x1=(cx-half,cx) if sx<0 else (cx,cx+half)
                y0,y1=(cy-half,cy) if sy<0 else (cy,cy+half)
                d=Thing(stable_id(city_id,'District',(sx,sy)),'District',derive_seed(city.seed,'district',sx,sy),
                        AreaDomain.rectangle(x0,y0,x1,y1),{'quadrant':[sx,sy]},(city_id,),created_at=founding)
                district_ids[sx,sy]=d.id; events.append(create_event(d,'CreateDistrict',self.id,7))
        policy=DevelopmentPolicy(); planned=[]
        for i in range(-r-1,r+1):
            for j in range(-r-1,r+1):
                x,y=cx+(i+.5)*s,cy+(j+.5)*s
                ring=max(abs(i+.5),abs(j+.5))-.5
                pf=policy.score(fields,x,y,(cx,cy),founding,settings.behavioral_level,context.parent_constraints)
                birth=founding+ring*29+rng.uniform(3,16,'block_birth',i,j)+max(0,1-pf['development_pressure'])*5
                area=AreaDomain.rectangle(cx+i*s+5,cy+j*s+5,cx+(i+1)*s-5,cy+(j+1)*s-5)
                corners=area.vertices+(area.anchor,)
                if min(fields.height(*p[:2]) for p in corners)<=fields.sea_level+2: continue
                if settings.behavioral_level and max(fields.slope(*p[:2]) for p in corners)>.34: continue
                if any(c.kind in {'NoBuildArea','ProtectedArea'} and c.blocks(area,birth) for c in context.parent_constraints): continue
                planned.append((birth,i,j,area,pf,ring))
        accepted=[]; indices=set()
        for spec in sorted(planned,key=lambda v:(v[5],v[0],v[1],v[2])):
            birth,i,j,area,pf,ring=spec
            if ring and not any((i+di,j+dj) in indices for di,dj in ((-1,0),(1,0),(0,-1),(0,1))): continue
            indices.add((i,j)); accepted.append(spec)
        roads={}
        for birth,i,j,area,pf,ring in accepted:
            for a,b in (((i,j),(i+1,j)),((i+1,j),(i+1,j+1)),((i,j+1),(i+1,j+1)),((i,j),(i,j+1))):
                key=tuple(sorted((a,b)))
                roads[key]=min(roads.get(key,1e10),birth-1)
        for (a,b),birth in sorted(roads.items()):
            if birth>time_interval.end: continue
            points=[]
            for k in range(9):
                t=k/8; x=cx+(a[0]+(b[0]-a[0])*t)*s; y=cy+(a[1]+(b[1]-a[1])*t)*s
                points.append((x,y,max(fields.height(x,y)+.22,fields.sea_level+.8)))
            arterial=(a[0]==b[0]==0 or a[1]==b[1]==0)
            width=8. if arterial else 6.
            junctions=[stable_id(city_id,'Junction',a),stable_id(city_id,'Junction',b)]
            road=Thing(stable_id(city_id,'Road',(a,b)),'Road',derive_seed(city.seed,'road',a,b),CurveDomain(tuple(points),width),
                       {'hierarchy':'arterial' if arterial else 'local','width':width,'junction_ids':junctions},
                       (city_id,),created_at=birth,commitments=(Commitment('width',width),Commitment('junction_ids',junctions)))
            events.append(create_event(road,'ExtendRoad',self.id,10))
        for birth,i,j,area,pf,ring in accepted:
            if birth>time_interval.end: continue
            bid=stable_id(city_id,'Block',(i,j)); bseed=derive_seed(city.seed,'block',i,j)
            district=district_ids[-1 if i<0 else 1,-1 if j<0 else 1]
            block=Thing(bid,'Block',bseed,area,{'grid_index':[i,j],'capacity_parcels':4,**pf},
                        (district,),created_at=birth,commitments=(Commitment('capacity_parcels',4),))
            events.append(create_event(block,'CreateBlock',self.id,15))
            park=rng.unit('park',i,j)<.11 or any(c.kind=='ParkConstraint' and c.blocks(area,birth) for c in context.parent_constraints)
            if park:
                thing=Thing(stable_id(bid,'Park','park'),'Park',derive_seed(bseed,'park'),area,
                            {'tree_count':12,'species':'broadleaf','maximum_height':12.,'public':True},
                            (bid,),created_at=birth+.1)
                if thing.created_at<=time_interval.end: events.append(create_event(thing,'CreatePark',self.id,20))
                continue
            parcels=[]; floor_area=0; expansion=stable_id(bid,'Event','initial_expansion')
            for px,py,parcel_area in subdivide_rectangular_block(area):
                pseed=derive_seed(bseed,'parcel',px,py)
                land=rng.unit('land_use',i,j,px,py)
                usage='commercial' if land<.18 and ring<2 else ('industrial' if land>.91 else 'residential')
                parcel=Thing(stable_id(bid,'Parcel',(px,py)),'Parcel',pseed,parcel_area,{'land_use':usage},
                             (bid,),created_at=birth+.2)
                first_birth=birth+2+RandomStream(pseed).uniform(0,9,'first_construction')
                parcels.append((parcel,first_birth))
                if not any(c.blocks(parcel_area,first_birth) for c in context.parent_constraints):
                    floor_area+=building_for_parcel(parcel,0,first_birth,fields).semantic_state['floor_area']
            events.append(Event(expansion,'UrbanExpansion',birth,bid,{'floor_area_added':floor_area},self.id,
                                interval_end=birth+12,priority=16))
            for parcel,first_birth in parcels:
                if parcel.created_at<=time_interval.end:
                    events.append(create_event(parcel,'SplitParcel',self.id,20))
                events.extend(lifecycle_events(parcel,first_birth,context,self.id,expansion))
        return [e for e in events if time_interval.contains(e.time)]
