"""Add floors, circulation, rooms, then furniture without changing the envelope."""
from ..core.node import Thing,Dimension
from ..core.domain import Bounds,VolumeDomain
from ..core.constraints import Commitment
from ..core.seed import derive_seed,stable_id
from ..refinement.refiner import Refiner,RefinementResult
from ..refinement.budget import Cost


def _child(parent,type_id,key,domain,state):
    return Thing(stable_id(parent.id,type_id,key),type_id,derive_seed(parent.seed,type_id,key),domain,state,
                 (parent.id,),created_at=parent.created_at,destroyed_at=parent.destroyed_at,
                 provenance={'generator':'building.structure','version':'1.0.0'},
                 commitments=tuple(Commitment(k,v) for k,v in state.items()))


class BuildingFloorsRefiner(Refiner):
    key='building.floors'; supported_types=('Building',); capability='floors'
    def estimate_cost(self,node,context):
        n=node.semantic_state['floor_count']; return Cost(nodes=n,memory_bytes=n*1400)
    def refine(self,node,context):
        b=node.domain.bounds; n=node.semantic_state['floor_count']; h=node.semantic_state['storey_height']
        children=[]
        for i in range(n):
            z=b.minimum[2]+h*i
            d=VolumeDomain(Bounds((*b.minimum[:2],z),(*b.maximum[:2],z+h)))
            children.append(_child(node,'Floor',i,d,{'floor_index':i,'usage':node.semantic_state['usage'],
                                                   'floor_area':b.size[0]*b.size[1]}))
        return RefinementResult(Dimension.STRUCTURAL,1,{'materialized_floor_count':n},tuple(children))


class FloorRoomsRefiner(Refiner):
    key='floor.rooms'; supported_types=('Floor',); required_request=2; capability='rooms and circulation'
    def estimate_cost(self,node,context): return Cost(nodes=5,memory_bytes=7000)
    def refine(self,node,context):
        b=node.domain.bounds; x,y,z=b.minimum; X,Y,Z=b.maximum
        margin=.25; mid=(x+X)/2; corridor_width=min(2.,(X-x)/5)
        if X-x<4 or Y-y<4: return RefinementResult(Dimension.STRUCTURAL,1,{'room_generation':'insufficient_space'})
        corridor=VolumeDomain(Bounds((mid-corridor_width/2,y+margin,z+.18),(mid+corridor_width/2,Y-margin,Z-.18)))
        children=[_child(node,'Corridor','circulation',corridor,{'circulation':True})]
        for side,(x0,x1) in enumerate(((x+margin,mid-corridor_width/2-margin),(mid+corridor_width/2+margin,X-margin))):
            for row,(y0,y1) in enumerate(((y+margin,(y+Y)/2-margin),((y+Y)/2+margin,Y-margin))):
                domain=VolumeDomain(Bounds((x0,y0,z+.18),(x1,y1,Z-.18)))
                children.append(_child(node,'Room',(side,row),domain,{'use':'living' if row else 'work',
                                                                   'floor_area':(x1-x0)*(y1-y0)}))
        return RefinementResult(Dimension.STRUCTURAL,1,{'room_count':4,'has_circulation':True},tuple(children))


class RoomFurnitureRefiner(Refiner):
    key='room.furniture_proxy'; supported_types=('Room',); required_request=3; capability='proxy furniture'
    def estimate_cost(self,node,context): return Cost(nodes=3,memory_bytes=4200)
    def refine(self,node,context):
        b=node.domain.bounds; x,y,z=b.minimum; w,h,depth=b.size
        children=[]
        # Normalized, non-overlapping footprints, all inside the committed room.
        specs=(('Desk',.2,.2,.28,.22,.78),('Chair',.2,.5,.14,.14,.85),('Shelf',.83,.5,.12,.6,1.65))
        for name,fx,fy,fw,fh,vertical in specs:
            height=min(vertical,depth*.8); cx=x+w*fx; cy=y+h*fy
            d=VolumeDomain(Bounds((cx-w*fw/2,cy-h*fh/2,z),(cx+w*fw/2,cy+h*fh/2,z+height)))
            children.append(_child(node,'FurnitureProxy',name,d,{'furniture_type':name}))
        return RefinementResult(Dimension.STRUCTURAL,1,{'furniture_proxy_count':len(children)},tuple(children))
