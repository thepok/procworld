"""Backend-neutral building representations with progressive architectural detail."""
from __future__ import annotations
from ..representation.provider import RepresentationProvider
from ..representation.geometry import GeometryBundle,Mesh,box_instance
from ..core.seed import RandomStream
from .archetypes import profile_from_state


def _gable_roof(b,body_height,roof_height,material='roof'):
    x,y,z=b.minimum; X,Y,_=b.maximum; e=z+body_height; top=e+roof_height
    v=((x,y,e),(X,y,e),(X,Y,e),(x,Y,e),((x+X)/2,y,top),((x+X)/2,Y,top))
    f=((0,1,4),(3,5,2),(0,4,5,3),(1,2,5,4))
    return Mesh(v,f,material,'gable_roof')


def _hip_roof(b,body_height,roof_height,material='roof'):
    x,y,z=b.minimum; X,Y,_=b.maximum; e=z+body_height; top=e+roof_height
    w,d=X-x,Y-y
    if w>=d:
        inset=min(w*.28,d*.36)
        a=((x+inset,(y+Y)/2,top),(X-inset,(y+Y)/2,top))
    else:
        inset=min(d*.28,w*.36)
        a=(((x+X)/2,y+inset,top),((x+X)/2,Y-inset,top))
    v=((x,y,e),(X,y,e),(X,Y,e),(x,Y,e),a[0],a[1])
    if w>=d:
        f=((0,1,5,4),(1,2,5),(2,3,4,5),(3,0,4))
    else:
        f=((0,1,4),(1,2,5,4),(2,3,5),(3,0,4,5))
    return Mesh(v,f,material,'hip_roof')


def _shed_roof(b,body_height,roof_height,material='roof'):
    x,y,z=b.minimum; X,Y,_=b.maximum; e=z+body_height; top=e+roof_height
    v=((x,y,e),(X,y,e),(X,Y,e),(x,Y,e),(x,y,top),(X,y,top))
    f=((0,1,5,4),(0,4,3),(1,2,5),(3,4,5,2))
    return Mesh(v,f,material,'shed_roof')


def _bay_count(length,target):
    return max(1,min(18,int(round(length/max(2.2,float(target))))))


def _window_material(profile):
    return 'glass' if profile.get('ground_floor_mode')=='storefront' else 'window'


def _add_windows(instances,b,state,profile,detail):
    x,y,z=b.minimum; X,Y,_=b.maximum; w,d,_=b.size
    floors=max(1,int(state.get('floor_count',1))); sh=float(state.get('storey_height',3.2))
    nx=_bay_count(w,profile['facade_bay_target']); ny=_bay_count(d,profile['facade_bay_target'])
    ww=min(float(profile['window_width']),w/max(nx,1)*.62)
    wh=min(float(profile['window_height']),sh*.60)
    mat=_window_material(profile)
    for floor in range(floors):
        wz=z+sh*(floor+.56)
        front_store=profile.get('ground_floor_mode')=='storefront' and floor==0
        fh=min(sh*.70,2.35) if front_store else wh
        fw=min(max(ww,2.15),w/max(nx,1)*.78) if front_store else ww
        for k in range(nx):
            xx=x+(k+.5)*w/nx
            instances.append(box_instance((xx,y+.03,wz),(fw,.06,fh),mat))
            instances.append(box_instance((xx,Y-.03,wz),(ww,.06,wh),'window'))
            if detail>=3 and not front_store:
                instances.append(box_instance((xx,y-.025,wz-fh/2-.06),(min(fw*1.12,w/nx*.84),.11,.10),'trim'))
        for k in range(ny):
            yy=y+(k+.5)*d/ny
            instances.append(box_instance((x+.03,yy,wz),(.06,min(ww,d/ny*.62),wh),'window'))
            instances.append(box_instance((X-.03,yy,wz),(.06,min(ww,d/ny*.62),wh),'window'))
    entrance=min(float(profile.get('entrance_width',1.7)),max(.9,w*.22))
    instances.append(box_instance(((x+X)/2,y+.045,z+min(1.15,sh*.36)),(entrance,.09,min(2.3,sh*.72)),'door'))


def _add_articulation(instances,b,state,profile):
    x,y,z=b.minimum; X,Y,_=b.maximum; w,d,h=b.size
    floors=max(1,int(state.get('floor_count',1))); sh=float(state.get('storey_height',3.2))
    body=min(h,float(state.get('floor_count',1))*sh)
    plinth=min(float(profile.get('plinth_height',.35)),sh*.25)
    instances.append(box_instance(((x+X)/2,y-.035,z+plinth/2),(w+.12,.07,plinth),'trim'))
    instances.append(box_instance(((x+X)/2,Y+.035,z+plinth/2),(w+.12,.07,plinth),'trim'))
    cornice=max(.05,float(profile.get('cornice_depth',.08)))
    if body>.5:
        instances.append(box_instance(((x+X)/2,(y+Y)/2,z+body-.11),(w+cornice*2,d+cornice*2,.22),'trim'))
    # Shallow floor bands make storey scale legible without creating semantic geometry.
    if floors<=8:
        for floor in range(1,floors):
            zz=z+floor*sh
            instances.append(box_instance(((x+X)/2,y-.018,zz),(w,.045,.075),'trim'))
            instances.append(box_instance(((x+X)/2,Y+.018,zz),(w,.045,.075),'trim'))
    rate=float(profile.get('balcony_rate',0.))
    if rate>0 and w>=5:
        rng=RandomStream(int(state.get('style_seed',0)),'balconies')
        nx=_bay_count(w,profile['facade_bay_target'])
        for floor in range(1,min(floors,8)):
            for k in range(nx):
                if rng.unit(floor,k)>rate: continue
                xx=x+(k+.5)*w/nx
                bw=min(2.2,w/nx*.72)
                zz=z+floor*sh+.12
                instances.append(box_instance((xx,y-.38,zz),(bw,.72,.12),'balcony'))
                instances.append(box_instance((xx,y-.70,zz+.55),(bw,.05,1.0),'metal'))


def _add_rooftop_details(instances,b,state,profile):
    x,y,z=b.minimum; X,Y,Z=b.maximum; w,d,_=b.size
    rng=RandomStream(int(state.get('style_seed',0)),'roof_details')
    roof_type=profile.get('roof_type','gable')
    if roof_type=='flat':
        parapet=.45
        instances.extend((
            box_instance(((x+X)/2,y+.09,Z-parapet/2),(w,.18,parapet),'roof'),
            box_instance(((x+X)/2,Y-.09,Z-parapet/2),(w,.18,parapet),'roof'),
            box_instance((x+.09,(y+Y)/2,Z-parapet/2),(.18,d,parapet),'roof'),
            box_instance((X-.09,(y+Y)/2,Z-parapet/2),(.18,d,parapet),'roof')))
    equipment=2 if state.get('usage') in {'commercial','industrial'} else 1
    for i in range(equipment):
        ew=min(2.8,max(1.0,w*.10)); ed=min(2.4,max(.9,d*.10)); eh=rng.uniform(.7,1.4,'hvac_h',i)
        cx=x+w*rng.uniform(.32,.68,'hvac_x',i); cy=y+d*rng.uniform(.34,.70,'hvac_y',i)
        instances.append(box_instance((cx,cy,Z+eh/2),(ew,ed,eh),'metal'))
    if profile.get('style_era') in {'preindustrial','industrializing','historicist','interwar'}:
        count=1 if w<15 else 2
        for i in range(count):
            cx=x+w*(.3+.4*i/max(1,count-1)) if count>1 else x+w*.34
            instances.append(box_instance((cx,Y-d*.18,Z+.65),(.55,.55,1.3),'brick'))


class BuildingProvider(RepresentationProvider):
    refinement_gain=2.4
    key='building.exterior'; version='2.0.0'; supported_types=('Building',); max_level=4
    def realize(self,node,detail_request,context):
        b=node.domain.bounds; x,y,z=b.minimum; X,Y,Z=b.maximum; w,d,h=b.size
        state=node.semantic_state; profile=profile_from_state(state,w,d)
        roof=min(float(state.get('roof_height',1.2)),h*.45); body=max(.2,h-roof)
        material=profile.get('facade_material') or state.get('usage','generic')
        if context.include_interiors and node.child_ids:
            # Camera-independent cutaway: retain two envelope walls and let structural children show through.
            wall=.22
            walls=(box_instance((x+wall/2,(y+Y)/2,z+body/2),(wall,d,body),material),
                   box_instance(((x+X)/2,Y-wall/2,z+body/2),(w,wall,body),material))
            return GeometryBundle(instances=walls)
        if detail_request<=0:
            return GeometryBundle(instances=(box_instance(b.center,b.size,material),))

        instances=[box_instance(((x+X)/2,(y+Y)/2,z+body/2),(w,d,body),material)]
        meshes=[]
        roof_type=profile.get('roof_type','gable')
        if roof_type=='flat':
            instances.append(box_instance(((x+X)/2,(y+Y)/2,z+body+roof/2),(w,d,max(.18,roof)),'roof'))
        elif roof_type=='hip':
            meshes.append(_hip_roof(b,body,roof))
        elif roof_type=='shed':
            meshes.append(_shed_roof(b,body,roof))
        else:
            meshes.append(_gable_roof(b,body,roof))

        if detail_request>=2:
            _add_windows(instances,b,state,profile,detail_request)
        if detail_request>=3:
            _add_articulation(instances,b,state,profile)
        if detail_request>=4:
            _add_rooftop_details(instances,b,state,profile)
        return GeometryBundle(tuple(meshes),tuple(instances))


class InteriorProvider(RepresentationProvider):
    key='building.interior_proxies'; version='2.0.0'; supported_types=('Floor','Room','Corridor','FurnitureProxy'); max_level=0
    def realize(self,node,detail_request,context):
        b=node.domain.bounds; center=b.center; size=b.size
        if node.type_id=='Floor':
            return GeometryBundle(instances=(box_instance((center[0],center[1],b.minimum[2]+.08),(size[0],size[1],.16),'floor'),))
        if node.type_id in {'Room','Corridor'}:
            x,y,z=b.minimum; X,Y,Z=b.maximum; height=min(1.,Z-z)
            walls=(box_instance(((x+X)/2,y+.05,z+height/2),(X-x,.1,height),'room'),
                   box_instance((x+.05,(y+Y)/2,z+height/2),(.1,Y-y,height),'room'))
            return GeometryBundle(instances=walls)
        material='furniture'
        if node.semantic_state.get('furniture_type') in {'Machine','Rack'}: material='metal'
        return GeometryBundle(instances=(box_instance(center,size,material),))


class BuildingCoreProvider(RepresentationProvider):
    key='building.vertical_core_geometry'; version='1.0.0'; supported_types=('Stairwell','ElevatorShaft'); max_level=1
    refinement_gain=.7
    def realize(self,node,detail_request,context):
        if not context.include_interiors:
            return GeometryBundle()
        b=node.domain.bounds; x,y,z=b.minimum; X,Y,Z=b.maximum; w,d,h=b.size
        if node.type_id=='ElevatorShaft':
            instances=[box_instance(b.center,b.size,'concrete')]
            if detail_request>=1:
                floors=max(1,int(node.semantic_state.get('serves_floors',1))); sh=h/floors
                for floor in range(floors):
                    instances.append(box_instance(((x+X)/2,y-.025,z+(floor+.45)*sh),(min(1.15,w*.7),.055,min(2.1,sh*.65)),'metal'))
            return GeometryBundle(instances=tuple(instances))
        if detail_request<=0:
            return GeometryBundle(instances=(box_instance(b.center,b.size,'room'),))
        floors=max(1,int(node.semantic_state.get('serves_floors',1))); sh=h/floors
        instances=[]; steps=8
        step_w=max(.6,w*.78); step_d=max(.12,d/(steps+2)); step_h=sh/(steps*2)
        for floor in range(floors):
            base=z+floor*sh
            for i in range(steps):
                instances.append(box_instance(((x+X)/2,y+(i+.5)*step_d,base+(i+.5)*step_h),
                                              (step_w,step_d*.92,step_h),'concrete'))
            landing_z=base+steps*step_h
            instances.append(box_instance(((x+X)/2,(y+Y)/2,landing_z),(step_w,d*.32,.12),'concrete'))
        return GeometryBundle(instances=tuple(instances))


class SettlementMassProvider(RepresentationProvider):
    key='settlement.mass'; supported_types=('City',); max_level=0
    def realize(self,node,detail_request,context):
        b=node.domain.bounds; x,y=b.center[:2]; w,d=b.size[:2]
        z=context.environment.height(x,y)
        return GeometryBundle(instances=(box_instance((x,y,z+4),(w*.45,d*.45,8),'residential'),))
