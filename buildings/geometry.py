from ..representation.provider import RepresentationProvider
from ..representation.geometry import GeometryBundle,Mesh,box_instance
from .lifecycle import condition_at


class BuildingProvider(RepresentationProvider):
    refinement_gain=2.
    key='building.exterior'; version='1.0.0'; supported_types=('Building',); max_level=2
    def realize(self,node,detail_request,context):
        b=node.domain.bounds; x,y,z=b.minimum; X,Y,Z=b.maximum; w,d,h=b.size
        state=node.semantic_state; material=state['usage']; roof=state['roof_height']
        body=h-roof
        if context.include_interiors and node.child_ids:
            # A deliberate cutaway, not automatic occlusion-based interior visibility.
            walls=(box_instance((x+.13,(y+Y)/2,z+body/2),(.26,d,body),material),
                   box_instance(((x+X)/2,Y-.13,z+body/2),(w,.26,body),material))
            return GeometryBundle(instances=walls)
        if detail_request==0:
            return GeometryBundle(instances=(box_instance(b.center,b.size,material),))
        instances=[box_instance(((x+X)/2,(y+Y)/2,z+body/2),(w,d,body),material)]
        rv=((x,y,z+body),(X,y,z+body),(X,Y,z+body),(x,Y,z+body),
            ((x+X)/2,y,Z),((x+X)/2,Y,Z))
        rf=((0,1,4),(3,5,2),(0,4,5,3),(1,2,5,4))
        meshes=(Mesh(rv,rf,'roof','gable_roof'),)
        if detail_request>=2:
            floor_count=state['floor_count']; sh=state['storey_height']
            nx=max(1,min(10,int(w/4.2))); ny=max(1,min(10,int(d/4.2)))
            for floor in range(floor_count):
                wz=z+sh*(floor+.56)
                for side in (0,1):
                    yy=y+.025 if side==0 else Y-.025
                    for k in range(nx):
                        xx=x+(k+.5)*w/nx
                        instances.append(box_instance((xx,yy,wz),(min(1.4,w/nx*.55),.055,1.45),'window'))
                    xx=x+.025 if side==0 else X-.025
                    for k in range(ny):
                        yy=y+(k+.5)*d/ny
                        instances.append(box_instance((xx,yy,wz),(.055,min(1.4,d/ny*.55),1.45),'window'))
            instances.append(box_instance(((x+X)/2,y+.04,z+1.1),(1.6,.08,2.2),'door'))
        return GeometryBundle(meshes,tuple(instances))


class InteriorProvider(RepresentationProvider):
    key='building.interior_proxies'; supported_types=('Floor','Room','Corridor','FurnitureProxy'); max_level=0
    def realize(self,node,detail_request,context):
        b=node.domain.bounds; center=b.center; size=b.size
        if node.type_id=='Floor':
            return GeometryBundle(instances=(box_instance((center[0],center[1],b.minimum[2]+.08),(size[0],size[1],.16),'floor'),))
        if node.type_id in {'Room','Corridor'}:
            # Low room boundary walls leave the cutaway legible.
            x,y,z=b.minimum; X,Y,Z=b.maximum; height=min(1.,Z-z)
            walls=(box_instance(((x+X)/2,y+.05,z+height/2),(X-x,.1,height),'room'),
                   box_instance((x+.05,(y+Y)/2,z+height/2),(.1,Y-y,height),'room'))
            return GeometryBundle(instances=walls)
        return GeometryBundle(instances=(box_instance(center,size,'furniture'),))


class SettlementMassProvider(RepresentationProvider):
    key='settlement.mass'; supported_types=('City',); max_level=0
    def realize(self,node,detail_request,context):
        # Used only when the region's finer semantic events are not materialized.
        b=node.domain.bounds; x,y=b.center[:2]; w,d=b.size[:2]
        z=context.environment.height(x,y)
        return GeometryBundle(instances=(box_instance((x,y,z+4),(w*.45,d*.45,8),'residential'),))
