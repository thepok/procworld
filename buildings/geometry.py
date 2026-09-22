"""Backend-neutral building geometry that preserves semantic polygon footprints."""
import math
from ..core.domain import AreaDomain,PrismDomain
from ..representation.provider import RepresentationProvider
from ..representation.geometry import GeometryBundle,Mesh,box_instance,extrude_polygon


def _area(node,z=None):
    if isinstance(node.domain,PrismDomain):
        z=node.domain.minimum_z if z is None else z
        return AreaDomain(tuple((p[0],p[1],z) for p in node.domain.area.vertices))
    b=node.domain.bounds; z=b.minimum[2] if z is None else z
    return AreaDomain.rectangle(b.minimum[0],b.minimum[1],b.maximum[0],b.maximum[1],z)


def _edge_box(a,b,z,height,thickness,material,depth_offset=0.):
    dx,dy=b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dy)
    if length<1e-7: return None
    nx,ny=dy/length,-dx/length
    cx=(a[0]+b[0])/2+nx*depth_offset; cy=(a[1]+b[1])/2+ny*depth_offset
    return box_instance((cx,cy,z+height/2),(length,thickness,height),material,math.atan2(dy,dx))


def _facade_instances(area,state,base,body_top):
    vertices=area.vertices; edges=list(zip(vertices,vertices[1:]+vertices[:1]))
    sh=state['storey_height']; floors=state['floor_count']; bay=max(1.8,state.get('facade_bay',3.2))
    ww=max(.6,state.get('window_width',1.2)); wh=max(.8,state.get('window_height',1.45))
    out=[]
    door_edge=min(range(len(edges)),key=lambda i:(edges[i][0][1]+edges[i][1][1])/2)
    for floor in range(floors):
        wz=base+sh*(floor+.56)
        if wz+wh/2>body_top: continue
        for edge_i,(a,b) in enumerate(edges):
            dx,dy=b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dy)
            if length<1.4: continue
            count=max(1,min(16,int(length/bay)))
            angle=math.atan2(dy,dx); nx,ny=dy/length,-dx/length
            for k in range(count):
                t=(k+.5)/count
                if floor==0 and edge_i==door_edge and abs(t-.5)<.18: continue
                x=a[0]+dx*t+nx*.035; y=a[1]+dy*t+ny*.035
                out.append(box_instance((x,y,wz),(min(ww,length/count*.58),.07,wh),'window',angle))
    a,b=edges[door_edge]; dx,dy=b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dy)
    if length>1.2:
        angle=math.atan2(dy,dx); nx,ny=dy/length,-dx/length
        out.append(box_instance(((a[0]+b[0])/2+nx*.04,(a[1]+b[1])/2+ny*.04,base+1.1),
                                (min(1.6,length*.35),.09,2.2),'door',angle))
    return out


def _gable_roof(area,body_top,top,material):
    v=area.vertices
    if len(v)!=4: return None
    xs={round(p[0],8) for p in v}; ys={round(p[1],8) for p in v}
    if len(xs)!=2 or len(ys)!=2: return None
    x0,x1=min(xs),max(xs); y0,y1=min(ys),max(ys); ridge=(x0+x1)/2
    rv=((x0,y0,body_top),(x1,y0,body_top),(x1,y1,body_top),(x0,y1,body_top),
        (ridge,y0,top),(ridge,y1,top))
    rf=((0,1,4),(3,5,2),(0,4,5,3),(1,2,5,4))
    return Mesh(rv,rf,material,'gable_roof')


class BuildingProvider(RepresentationProvider):
    refinement_gain=2.5
    key='building.exterior'; version='2.0.0'; supported_types=('Building',); max_level=2
    def realize(self,node,detail_request,context):
        b=node.domain.bounds; base=b.minimum[2]; top=b.maximum[2]
        state=node.semantic_state; roof=max(.05,state.get('roof_height',.35)); body_top=max(base,top-roof)
        area=_area(node,base); facade=state.get('facade_material',state.get('usage','residential'))
        roof_material=state.get('roof_material','roof')
        if detail_request==0:
            # Even the cheapest massing follows the semantic polygon. The AABB
            # remains only an acceleration/fallback envelope.
            return GeometryBundle(meshes=(extrude_polygon(area.vertices,base,top,facade,'building_massing'),))
        meshes=[extrude_polygon(area.vertices,base,body_top,facade,'building_shell')]
        gable=_gable_roof(area,body_top,top,roof_material) if state.get('roof_form')=='gable' else None
        if gable is not None:
            meshes.append(gable)
        else:
            meshes.append(extrude_polygon(area.vertices,body_top,top,roof_material,'roof_cap'))
        instances=[]
        if detail_request>=2:
            instances.extend(_facade_instances(area,state,base,body_top))
        if context.include_interiors and node.child_ids:
            # Deliberate deterministic cutaway: retain only alternating exterior
            # wall segments rather than restoring a rectangular shell.
            meshes=[]
            edges=list(zip(area.vertices,area.vertices[1:]+area.vertices[:1]))
            wall_height=max(.2,body_top-base)
            for i,(a,c) in enumerate(edges):
                if i%2:
                    wall=_edge_box(a,c,base,wall_height,.22,facade)
                    if wall: instances.append(wall)
        return GeometryBundle(tuple(meshes),tuple(instances))


class InteriorProvider(RepresentationProvider):
    key='building.interior_proxies'; version='2.0.0'
    supported_types=('Floor','Room','Corridor','VerticalCore','FurnitureProxy'); max_level=0
    def realize(self,node,detail_request,context):
        b=node.domain.bounds; center=b.center; size=b.size
        if node.type_id=='Floor':
            area=_area(node,b.minimum[2])
            top=min(b.maximum[2],b.minimum[2]+.16)
            return GeometryBundle(meshes=(extrude_polygon(area.vertices,b.minimum[2],top,'floor','floor_slab'),))
        if node.type_id in {'Room','Corridor'}:
            area=_area(node,b.minimum[2]); height=min(1.,b.maximum[2]-b.minimum[2]); walls=[]
            material='room'
            for a,c in zip(area.vertices,area.vertices[1:]+area.vertices[:1]):
                wall=_edge_box(a,c,b.minimum[2],height,.10,material)
                if wall: walls.append(wall)
            return GeometryBundle(instances=tuple(walls))
        if node.type_id=='VerticalCore':
            area=_area(node,b.minimum[2])
            return GeometryBundle(meshes=(extrude_polygon(area.vertices,b.minimum[2],b.maximum[2],'concrete','vertical_core'),))
        return GeometryBundle(instances=(box_instance(center,size,'furniture'),))


class SettlementMassProvider(RepresentationProvider):
    key='settlement.mass'; supported_types=('City',); max_level=0
    def realize(self,node,detail_request,context):
        # Used only when the region's finer semantic events are not materialized.
        b=node.domain.bounds; x,y=b.center[:2]; w,d=b.size[:2]
        z=context.environment.height(x,y)
        return GeometryBundle(instances=(box_instance((x,y,z+4),(w*.45,d*.45,8),'residential'),))
