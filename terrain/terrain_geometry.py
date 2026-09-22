from ..representation.provider import RepresentationProvider
from ..representation.geometry import Mesh,GeometryBundle,ribbon


class TerrainProvider(RepresentationProvider):
    key='terrain.heightfield'; version='1.0.0'; supported_types=('Terrain',); max_level=3
    def realize(self,node,detail_request,context):
        # Canonical grids share exact absolute-coordinate samples at equal detail.
        n=(8,16,32,64)[min(detail_request,3)]
        b=node.domain.bounds; x0,y0=b.minimum[:2]; w,h=b.size[:2]
        verts=tuple((x0+w*i/n,y0+h*j/n,context.environment.height(x0+w*i/n,y0+h*j/n))
                    for j in range(n+1) for i in range(n+1))
        faces=[]
        for j in range(n):
            for i in range(n):
                a=j*(n+1)+i; faces.extend(((a,a+1,a+n+2),(a,a+n+2,a+n+1)))
        # Boundary skirts hide cracks between differently tessellated neighboring tiles.
        border=(list(range(n+1))+[j*(n+1)+n for j in range(1,n+1)]
                +[n*(n+1)+i for i in range(n-1,-1,-1)]+[j*(n+1) for j in range(n-1,0,-1)])
        vv=list(verts)
        for a,c in zip(border,border[1:]+border[:1]):
            k=len(vv); va,vc=verts[a],verts[c]
            vv.extend(((va[0],va[1],va[2]-35),(vc[0],vc[1],vc[2]-35)))
            faces.append((a,k,k+1,c))
        return GeometryBundle(meshes=(Mesh(tuple(vv),tuple(faces),'terrain','terrain'),))


class WaterProvider(RepresentationProvider):
    key='water.primitive'; version='1.0.0'; supported_types=('Water',); max_level=0
    def realize(self,node,detail_request,context):
        from ..representation.fallback import fallback
        if hasattr(node.domain,'points'):
            return GeometryBundle(meshes=(ribbon(node.domain.points,node.domain.width,'water','river'),))
        return fallback(node,'water')


class RoadProvider(RepresentationProvider):
    refinement_gain=.055
    key='road.ribbon'; version='1.0.0'; supported_types=('Road',); max_level=1
    def realize(self,node,detail_request,context):
        d=node.domain
        meshes=[ribbon(d.points,d.width,'road','road')]
        if detail_request:
            # A narrow center stripe is a cheap optional road refinement.
            points=tuple((x,y,z+.018) for x,y,z in d.points)
            meshes.append(ribbon(points,.13,'path','road_center'))
        return GeometryBundle(meshes=tuple(meshes))
