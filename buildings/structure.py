"""Refine polygonal building envelopes into floors, circulation, rooms and furniture."""
from ..core.node import Thing,Dimension
from ..core.domain import AreaDomain,Bounds,PrismDomain,VolumeDomain
from ..core.constraints import Commitment
from ..core.seed import RandomStream,derive_seed,stable_id
from ..refinement.refiner import Refiner,RefinementResult
from ..refinement.budget import Cost
from .archetypes import room_program
from .footprint import polygon_centroid


def _child(parent,type_id,key,domain,state):
    return Thing(stable_id(parent.id,type_id,key),type_id,derive_seed(parent.seed,type_id,key),domain,state,
                 (parent.id,),created_at=parent.created_at,destroyed_at=parent.destroyed_at,
                 provenance={'generator':'building.structure','version':'2.0.0'},
                 commitments=tuple(Commitment(k,v) for k,v in state.items()))


def _footprint(node,z=None):
    if isinstance(node.domain,PrismDomain):
        z=node.domain.minimum_z if z is None else z
        return AreaDomain(tuple((p[0],p[1],z) for p in node.domain.area.vertices))
    b=node.domain.bounds; z=b.minimum[2] if z is None else z
    return AreaDomain.rectangle(b.minimum[0],b.minimum[1],b.maximum[0],b.maximum[1],z)


def _interior_rectangle(area,width,height,z,preferred=None):
    b=area.bounds; x0,y0=b.minimum[:2]; x1,y1=b.maximum[:2]
    width=min(width,(x1-x0)*.8); height=min(height,(y1-y0)*.8)
    if width<=.4 or height<=.4: return None
    cx,cy=preferred or polygon_centroid(tuple((p[0],p[1]) for p in area.vertices))
    candidates=[(cx,cy),((x0+x1)/2,(y0+y1)/2)]
    for iy in range(1,5):
        for ix in range(1,5):
            candidates.append((x0+(x1-x0)*ix/5,y0+(y1-y0)*iy/5))
    for cx,cy in candidates:
        try:
            rect=AreaDomain.rectangle(cx-width/2,cy-height/2,cx+width/2,cy+height/2,z)
        except ValueError:
            continue
        if area.contains_domain(rect): return rect
    return None


def _room_cells(area,z0,z1):
    b=area.bounds; x0,y0=b.minimum[:2]; x1,y1=b.maximum[:2]
    w,h=x1-x0,y1-y0
    nx=max(2,min(4,int(w/5.5)))
    ny=max(2,min(4,int(h/5.5)))
    margin=min(.22,max(.08,min(w/max(nx,1),h/max(ny,1))*.035))
    cells=[]
    for iy in range(ny):
        ay=y0+h*iy/ny+margin; by=y0+h*(iy+1)/ny-margin
        for ix in range(nx):
            ax=x0+w*ix/nx+margin; bx=x0+w*(ix+1)/nx-margin
            if bx-ax<1 or by-ay<1: continue
            rect=AreaDomain.rectangle(ax,ay,bx,by,z0)
            if area.contains_domain(rect):
                cells.append((ix,iy,PrismDomain(rect,z0,z1)))
    return cells


class BuildingFloorsRefiner(Refiner):
    key='building.floors'; version='2.0.0'; supported_types=('Building',); capability='polygon-preserving floors and core'
    def estimate_cost(self,node,context):
        n=node.semantic_state['floor_count']; return Cost(nodes=n+1,memory_bytes=(n+1)*1600)
    def refine(self,node,context):
        b=node.domain.bounds; n=node.semantic_state['floor_count']; h=node.semantic_state['storey_height']
        base=b.minimum[2]; body_top=min(b.maximum[2],base+n*h)
        children=[]
        for i in range(n):
            z=base+h*i; top=min(z+h,body_top)
            area=_footprint(node,z)
            d=PrismDomain(area,z,top)
            children.append(_child(node,'Floor',i,d,{
                'floor_index':i,'usage':node.semantic_state['usage'],'floor_area':area.area,
                'archetype':node.semantic_state.get('archetype','generic')}))
        area=_footprint(node,base)
        core_area=_interior_rectangle(area,min(3.2,b.size[0]*.18),min(4.2,b.size[1]*.22),base)
        if core_area is not None and body_top>base:
            children.append(_child(node,'VerticalCore','core',PrismDomain(core_area,base,body_top),{
                'circulation':True,'serves_floor_count':n,'core_type':'stair_elevator' if n>=4 else 'stair'}))
        return RefinementResult(Dimension.STRUCTURAL,1,{
            'materialized_floor_count':n,'vertical_core_count':int(core_area is not None)},tuple(children))


class FloorRoomsRefiner(Refiner):
    key='floor.rooms'; version='2.0.0'; supported_types=('Floor',); required_request=2; capability='polygon-aware room program and circulation'
    def estimate_cost(self,node,context): return Cost(nodes=12,memory_bytes=17000)
    def refine(self,node,context):
        b=node.domain.bounds; z=b.minimum[2]+.18; top=b.maximum[2]-.18
        if top-z<1.: return RefinementResult(Dimension.STRUCTURAL,1,{'room_generation':'insufficient_height'})
        area=_footprint(node,z)
        cells=_room_cells(area,z,top)
        if not cells:
            # The exact polygon remains useful even when it is too small/narrow
            # for the cheap grid planner.
            room=PrismDomain(area,z,top)
            child=_child(node,'Room','whole_floor',room,{'use':'multi_use','floor_area':area.area})
            return RefinementResult(Dimension.STRUCTURAL,1,{'room_count':1,'has_circulation':False},(child,))
        center=area.bounds.center
        corridor_i=min(range(len(cells)),key=lambda i:(cells[i][2].bounds.center[0]-center[0])**2+
                         (cells[i][2].bounds.center[1]-center[1])**2)
        rng=RandomStream(node.seed,'rooms')
        program=room_program(node.semantic_state.get('usage','residential'))
        children=[]; room_count=0
        for i,(ix,iy,domain) in enumerate(cells):
            if i==corridor_i:
                children.append(_child(node,'Corridor','circulation',domain,{
                    'circulation':True,'floor_area':domain.area.area}))
                continue
            use=rng.choice(program,'program',ix,iy)
            children.append(_child(node,'Room',(ix,iy),domain,{'use':use,'floor_area':domain.area.area}))
            room_count+=1
        return RefinementResult(Dimension.STRUCTURAL,1,{
            'room_count':room_count,'has_circulation':True,'planning_method':'contained_grid'},tuple(children))


class RoomFurnitureRefiner(Refiner):
    key='room.furniture_proxy'; version='2.0.0'; supported_types=('Room',); required_request=3; capability='usage-aware proxy furniture'
    def estimate_cost(self,node,context): return Cost(nodes=4,memory_bytes=5600)
    def refine(self,node,context):
        b=node.domain.bounds; x,y,z=b.minimum; w,h,depth=b.size
        use=node.semantic_state.get('use','generic')
        if use in {'bedroom','living'}:
            specs=(('Bed' if use=='bedroom' else 'Sofa',.28,.28,.32,.30,.65),('Table',.66,.42,.22,.20,.75),('Shelf',.86,.55,.10,.55,1.65))
        elif use in {'office','study','meeting','reception'}:
            specs=(('Desk',.28,.28,.28,.22,.78),('Chair',.28,.54,.14,.14,.85),('Shelf',.86,.55,.10,.55,1.65))
        elif use in {'production','storage','service'}:
            specs=(('WorkBench',.30,.30,.34,.22,.95),('Storage',.78,.56,.24,.44,1.8))
        else:
            specs=(('Table',.32,.30,.25,.22,.78),('Chair',.32,.56,.14,.14,.85),('Shelf',.86,.55,.10,.55,1.65))
        children=[]
        for name,fx,fy,fw,fh,vertical in specs:
            height=min(vertical,depth*.8); cx=x+w*fx; cy=y+h*fy
            d=VolumeDomain(Bounds((cx-w*fw/2,cy-h*fh/2,z),(cx+w*fw/2,cy+h*fh/2,z+height)))
            if node.domain.contains_domain(d):
                children.append(_child(node,'FurnitureProxy',name,d,{'furniture_type':name,'room_use':use}))
        return RefinementResult(Dimension.STRUCTURAL,1,{'furniture_proxy_count':len(children)},tuple(children))
