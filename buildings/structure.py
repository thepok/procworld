"""Building structural refinement: floors, cores, rooms, and furniture proxies."""
from ..core.node import Thing,Dimension
from ..core.domain import Bounds,VolumeDomain
from ..core.constraints import Commitment
from ..core.seed import derive_seed,stable_id
from ..refinement.refiner import Refiner,RefinementResult
from ..refinement.budget import Cost


def _child(parent,type_id,key,domain,state):
    return Thing(stable_id(parent.id,type_id,key),type_id,derive_seed(parent.seed,type_id,key),domain,state,
                 (parent.id,),created_at=parent.created_at,destroyed_at=parent.destroyed_at,
                 provenance={'generator':'building.structure','version':'2.0.0'},
                 commitments=tuple(Commitment(k,v) for k,v in state.items()))


class BuildingFloorsRefiner(Refiner):
    key='building.floors'; version='2.0.0'; supported_types=('Building',); capability='floors'
    def estimate_cost(self,node,context):
        n=node.semantic_state['floor_count']; return Cost(nodes=n,memory_bytes=n*1700)
    def refine(self,node,context):
        b=node.domain.bounds; n=node.semantic_state['floor_count']; h=node.semantic_state['storey_height']
        children=[]
        for i in range(n):
            z=b.minimum[2]+h*i
            d=VolumeDomain(Bounds((*b.minimum[:2],z),(*b.maximum[:2],min(z+h,b.maximum[2]))))
            state={'floor_index':i,'floor_count':n,'usage':node.semantic_state['usage'],
                   'archetype':node.semantic_state.get('archetype','generic'),
                   'floor_area':b.size[0]*b.size[1],
                   'ground_floor':i==0}
            children.append(_child(node,'Floor',i,d,state))
        return RefinementResult(Dimension.STRUCTURAL,1,{'materialized_floor_count':n},tuple(children))


class BuildingCoreRefiner(Refiner):
    """Add persistent vertical-circulation volumes after floor materialization."""
    key='building.vertical_core'; version='1.0.0'; supported_types=('Building',)
    required_request=2; max_level=2; capability='stairs and elevator core'
    def estimate_cost(self,node,context):
        return Cost(nodes=2 if node.semantic_state.get('has_elevator') else 1,memory_bytes=3600)
    def estimate_gain(self,node,context): return 1.35
    def can_refine(self,node,context):
        return node.refinement_state.structural==1 and super().can_refine(node,context)
    def refine(self,node,context):
        b=node.domain.bounds; x,y,z=b.minimum; X,Y,Z=b.maximum; w,d,_=b.size
        if w<3.0 or d<3.0:
            return RefinementResult(Dimension.STRUCTURAL,2,{'vertical_core':'omitted_tight_envelope'})
        core_w=min(max(1.8,w*.16),3.2)
        core_d=min(max(2.6,d*.22),5.2)
        cx=(x+X)/2
        cy=Y-core_d/2-max(.35,d*.04)
        stair=VolumeDomain(Bounds((cx-core_w/2,cy-core_d/2,z),(cx+core_w/2,cy+core_d/2,Z)))
        children=[_child(node,'Stairwell','main',stair,{'core_type':'stair','serves_floors':node.semantic_state['floor_count']})]
        if node.semantic_state.get('has_elevator') and w>=6.0:
            ew=min(2.1,max(1.5,w*.1)); ed=min(2.1,max(1.5,d*.1))
            ex=min(X-ew/2-.35,cx+core_w/2+ew/2+.35)
            elev=VolumeDomain(Bounds((ex-ew/2,cy-ed/2,z),(ex+ew/2,cy+ed/2,Z)))
            if b.contains(elev.bounds):
                children.append(_child(node,'ElevatorShaft','main',elev,
                                       {'core_type':'elevator','serves_floors':node.semantic_state['floor_count']}))
        return RefinementResult(Dimension.STRUCTURAL,2,
                                {'vertical_core':'materialized','vertical_core_count':len(children)},tuple(children))


def _room_uses(usage,ground_floor):
    if usage=='commercial':
        return ('retail' if ground_floor else 'office','office','meeting','service')
    if usage=='industrial':
        return ('production','production','storage','service')
    return ('living','bedroom','kitchen','bathroom')


class FloorRoomsRefiner(Refiner):
    key='floor.rooms'; version='2.0.0'; supported_types=('Floor',); required_request=2; capability='rooms and circulation'
    def estimate_cost(self,node,context): return Cost(nodes=5,memory_bytes=8500)
    def refine(self,node,context):
        b=node.domain.bounds; x,y,z=b.minimum; X,Y,Z=b.maximum
        margin=.25; mid=(x+X)/2; corridor_width=min(2.,max(1.15,(X-x)/5))
        if X-x<4 or Y-y<4:
            return RefinementResult(Dimension.STRUCTURAL,1,{'room_generation':'insufficient_space'})
        corridor=VolumeDomain(Bounds((mid-corridor_width/2,y+margin,z+.18),(mid+corridor_width/2,Y-margin,Z-.18)))
        children=[_child(node,'Corridor','circulation',corridor,{'circulation':True,'floor_index':node.semantic_state.get('floor_index',0)})]
        uses=_room_uses(node.semantic_state.get('usage','residential'),node.semantic_state.get('ground_floor',False))
        index=0
        for side,(x0,x1) in enumerate(((x+margin,mid-corridor_width/2-margin),(mid+corridor_width/2+margin,X-margin))):
            for row,(y0,y1) in enumerate(((y+margin,(y+Y)/2-margin),((y+Y)/2+margin,Y-margin))):
                if x1<=x0 or y1<=y0: continue
                domain=VolumeDomain(Bounds((x0,y0,z+.18),(x1,y1,Z-.18)))
                use=uses[index % len(uses)]; index+=1
                children.append(_child(node,'Room',(side,row),domain,
                    {'use':use,'floor_area':(x1-x0)*(y1-y0),'daylight_side':'west' if side==0 else 'east'}))
        return RefinementResult(Dimension.STRUCTURAL,1,
                                {'room_count':len(children)-1,'has_circulation':True,'program':node.semantic_state.get('usage','residential')},
                                tuple(children))


_FURNITURE={
    'living':(('Sofa',.30,.24,.34,.18,.82),('Table',.58,.42,.22,.20,.72),('Shelf',.84,.52,.10,.62,1.7)),
    'bedroom':(('Bed',.34,.33,.48,.34,.62),('Wardrobe',.84,.53,.11,.55,1.9),('Desk',.30,.76,.26,.16,.78)),
    'kitchen':(('Counter',.18,.50,.16,.70,.92),('Table',.58,.48,.28,.24,.76),('Cabinet',.84,.50,.11,.64,1.9)),
    'bathroom':(('Vanity',.22,.30,.24,.18,.88),('Bath',.60,.32,.34,.22,.58),('Cabinet',.82,.72,.12,.18,1.55)),
    'office':(('Desk',.30,.28,.30,.20,.78),('Desk',.66,.28,.30,.20,.78),('Shelf',.84,.68,.10,.48,1.7)),
    'meeting':(('Table',.50,.48,.48,.28,.76),('Chair',.20,.50,.12,.14,.85),('Shelf',.84,.55,.10,.50,1.7)),
    'retail':(('Counter',.24,.68,.36,.16,.95),('Display',.60,.35,.22,.22,1.35),('Shelf',.84,.50,.10,.70,1.8)),
    'service':(('Counter',.24,.28,.30,.18,.92),('Shelf',.84,.48,.10,.62,1.7),('Cabinet',.56,.76,.24,.16,1.7)),
    'production':(('Machine',.30,.32,.28,.26,1.25),('Machine',.68,.32,.28,.26,1.25),('Rack',.82,.72,.12,.42,1.8)),
    'storage':(('Rack',.22,.48,.16,.68,1.9),('Rack',.52,.48,.16,.68,1.9),('Rack',.82,.48,.16,.68,1.9)),
}


class RoomFurnitureRefiner(Refiner):
    key='room.furniture_proxy'; version='2.0.0'; supported_types=('Room',); required_request=3; capability='program-aware proxy furniture'
    def estimate_cost(self,node,context): return Cost(nodes=3,memory_bytes=5200)
    def refine(self,node,context):
        b=node.domain.bounds; x,y,z=b.minimum; w,h,depth=b.size
        children=[]; use=node.semantic_state.get('use','living')
        specs=_FURNITURE.get(use,_FURNITURE['living'])
        for i,(name,fx,fy,fw,fh,vertical) in enumerate(specs):
            height=min(vertical,depth*.8); cx=x+w*fx; cy=y+h*fy
            x0=max(x+.05,cx-w*fw/2); x1=min(x+w-.05,cx+w*fw/2)
            y0=max(y+.05,cy-h*fh/2); y1=min(y+h-.05,cy+h*fh/2)
            if x1<=x0 or y1<=y0: continue
            d=VolumeDomain(Bounds((x0,y0,z),(x1,y1,z+height)))
            children.append(_child(node,'FurnitureProxy',(name,i),d,{'furniture_type':name,'room_use':use}))
        return RefinementResult(Dimension.STRUCTURAL,1,{'furniture_proxy_count':len(children)},tuple(children))
