"""Backend-neutral meshes and instances. Semantic records never contain these."""
from __future__ import annotations
from dataclasses import dataclass,field
import math
from ..core.domain import Vec3,point
from ..core.scope import Transform
from ..refinement.budget import Cost


@dataclass(frozen=True,slots=True)
class Mesh:
    vertices: tuple[Vec3,...]
    faces: tuple[tuple[int,...],...]
    material: str = 'generic'
    name: str = 'mesh'
    def __post_init__(self):
        object.__setattr__(self,'vertices',tuple(point(v) for v in self.vertices))
        object.__setattr__(self,'faces',tuple(tuple(f) for f in self.faces))
        if any(len(f)<3 or any(type(i) is not int or i<0 or i>=len(self.vertices) for i in f) for f in self.faces):
            raise ValueError('Invalid mesh indices')
    @property
    def triangle_count(self): return sum(len(f)-2 for f in self.faces)
    def transformed(self,transform:Transform,material:str|None=None):
        return Mesh(tuple(transform.apply(v) for v in self.vertices),self.faces,material or self.material,self.name)
    def to_data(self):
        return {'name':self.name,'vertices':self.vertices,'faces':self.faces,'material':self.material}


@dataclass(frozen=True,slots=True)
class Instance:
    prototype: str
    transform: Transform = field(default_factory=Transform)
    material: str = 'generic'
    def to_data(self):
        return {'prototype':self.prototype,'translation':self.transform.translation,
                'scale':self.transform.scale,'rotation_z':self.transform.rotation_z,'material':self.material}


@dataclass(frozen=True,slots=True)
class GeometryBundle:
    meshes: tuple[Mesh,...] = ()
    instances: tuple[Instance,...] = ()
    prototypes: tuple[tuple[str,Mesh],...] = ()
    def __post_init__(self):
        names=[name for name,_ in self.prototypes]
        if len(names)!=len(set(names)): raise ValueError('Duplicate prototype name')
        for name,mesh in self.prototypes:
            if name in PROTOTYPES and PROTOTYPES[name]!=mesh:
                raise ValueError(f'Cannot replace built-in prototype {name}')
        available=set(PROTOTYPES)|set(names)
        if any(i.prototype not in available for i in self.instances):
            raise ValueError('Unresolved instance prototype')
    def cost(self):
        prototypes={**PROTOTYPES,**dict(self.prototypes)}
        triangles=sum(m.triangle_count for m in self.meshes)+sum(prototypes[i.prototype].triangle_count for i in self.instances)
        memory=sum(len(m.vertices)*24+sum(len(f) for f in m.faces)*8 for m in self.meshes)+len(self.instances)*160
        memory+=sum(len(m.vertices)*24+sum(len(f) for f in m.faces)*8 for _,m in self.prototypes)
        return Cost(instances=len(self.meshes)+len(self.instances),triangles=triangles,memory_bytes=memory)
    def to_data(self):
        return {'meshes':[m.to_data() for m in self.meshes],
                'instances':[i.to_data() for i in self.instances],
                'prototypes':{k:v.to_data() for k,v in self.prototypes}}
    @classmethod
    def from_data(cls,d):
        meshes=tuple(Mesh(**m) for m in d.get('meshes',()))
        instances=tuple(Instance(i['prototype'],Transform(i['translation'],i['scale'],i.get('rotation_z',0)),i['material'])
                        for i in d.get('instances',()))
        prototypes=tuple((k,Mesh(**m)) for k,m in d.get('prototypes',{}).items())
        return cls(meshes,instances,prototypes)


def box_instance(center:Vec3,size:Vec3,material='generic',rotation=0):
    # Degenerate domain fallbacks still receive a visible, finite representation.
    return Instance('unit_box',Transform(center,tuple(max(.02,float(s)) for s in size),rotation),material)


def ribbon(points,width,material='road',name='ribbon') -> Mesh:
    verts=[]; faces=[]
    for a,b in zip(points,points[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dy)
        if length<1e-9: continue
        nx,ny=-dy/length*width/2,dx/length*width/2
        k=len(verts)
        verts.extend(((a[0]+nx,a[1]+ny,a[2]),(a[0]-nx,a[1]-ny,a[2]),
                      (b[0]-nx,b[1]-ny,b[2]),(b[0]+nx,b[1]+ny,b[2])))
        faces.append((k,k+1,k+2,k+3))
    return Mesh(tuple(verts),tuple(faces),material,name)


def _unit_box():
    v=((-0.5,-0.5,-0.5),(0.5,-0.5,-0.5),(0.5,0.5,-0.5),(-0.5,0.5,-0.5),
       (-0.5,-0.5,0.5),(0.5,-0.5,0.5),(0.5,0.5,0.5),(-0.5,0.5,0.5))
    return Mesh(v,((0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)),name='unit_box')


def _canopy():
    v=((0,0,.5),(0,0,-.5),(.5,0,0),(0,.5,0),(-.5,0,0),(0,-.5,0))
    f=((0,2,3),(0,3,4),(0,4,5),(0,5,2),(1,3,2),(1,4,3),(1,5,4),(1,2,5))
    return Mesh(v,f,name='canopy')


PROTOTYPES={'unit_box':_unit_box(),'canopy':_canopy()}
MATERIALS={
    'generic':(.6,.55,.68,1),'terrain':(.32,.41,.23,1),'water':(.12,.36,.50,1),
    'road':(.16,.17,.18,1),'path':(.57,.52,.40,1),'residential':(.65,.53,.39,1),
    'commercial':(.52,.57,.60,1),'industrial':(.42,.44,.44,1),'roof':(.27,.18,.14,1),
    'brick':(.46,.24,.17,1),'stucco':(.72,.68,.58,1),'stone':(.55,.54,.50,1),
    'concrete':(.48,.49,.47,1),'glass':(.25,.42,.48,1),'metal':(.38,.40,.42,1),
    'tile_roof':(.38,.16,.10,1),
    'window':(.20,.36,.45,1),'door':(.23,.16,.10,1),'bark':(.27,.18,.10,1),
    'foliage':(.18,.34,.13,1),'park':(.31,.46,.22,1),'floor':(.66,.61,.49,1),
    'room':(.64,.65,.71,1),'furniture':(.48,.30,.16,1),'debug':(1.,.35,.08,1),
}


@dataclass(slots=True)
class GeometryScene:
    bundles: dict[str,GeometryBundle] = field(default_factory=dict)
    categories: dict[str,str] = field(default_factory=dict)
    def prototypes(self):
        result=dict(PROTOTYPES)
        for bundle in self.bundles.values():
            for name,mesh in bundle.prototypes:
                if name in result and result[name]!=mesh:
                    raise ValueError(f'Conflicting shared prototype {name}')
                result[name]=mesh
        return result
    def validate_bundle(self,bundle):
        if not bundle.prototypes: return
        existing=self.prototypes()
        for name,mesh in bundle.prototypes:
            if name in existing and existing[name]!=mesh:
                raise ValueError(f'Conflicting shared prototype {name}')
    def expanded_meshes(self):
        prototypes=self.prototypes()
        for node_id,bundle in sorted(self.bundles.items()):
            yield from ((node_id,m) for m in bundle.meshes)
            yield from ((node_id,prototypes[i.prototype].transformed(i.transform,i.material)) for i in bundle.instances)
    def to_data(self):
        return {'bundles':{k:b.to_data() for k,b in sorted(self.bundles.items())},'categories':self.categories}
    def cost(self):
        total=Cost()
        for bundle in self.bundles.values(): total=total+bundle.cost()
        return total



def triangulate_polygon(vertices):
    """Ear-clipping triangulation of a simple XY polygon, in either winding."""
    if len(vertices)<3: raise ValueError('Polygon needs at least three vertices')
    signed=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(vertices,vertices[1:]+vertices[:1]))
    indices=list(range(len(vertices)))
    if signed<0: indices.reverse()
    def cross(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def inside(p,a,b,c):
        return cross(a,b,p)>=-1e-9 and cross(b,c,p)>=-1e-9 and cross(c,a,p)>=-1e-9
    triangles=[]
    while len(indices)>3:
        found=False
        for k,b in enumerate(indices):
            a=indices[k-1]; c=indices[(k+1)%len(indices)]
            if cross(vertices[a],vertices[b],vertices[c])<=1e-10: continue
            if any(inside(vertices[i],vertices[a],vertices[b],vertices[c]) for i in indices if i not in (a,b,c)): continue
            triangles.append((a,b,c)); indices.pop(k); found=True; break
        if not found: raise ValueError('Polygon is self-intersecting or numerically degenerate')
    triangles.append(tuple(indices))
    return tuple(triangles)


def extrude_polygon(vertices,bottom_z,top_z,material='generic',name='prism') -> Mesh:
    """Extrude a simple XY polygon between two Z planes.

    ``vertices`` may carry arbitrary Z values; only XY is used for the footprint.
    Concave polygons are supported through the existing ear-clipping triangulator.
    """
    footprint=tuple((float(p[0]),float(p[1]),float(bottom_z)) for p in vertices)
    if len(footprint)<3 or top_z < bottom_z:
        raise ValueError('Invalid polygon extrusion')
    cap=triangulate_polygon(footprint)
    n=len(footprint)
    verts=footprint+tuple((p[0],p[1],float(top_z)) for p in footprint)
    faces=[tuple(reversed(t)) for t in cap]
    faces.extend(tuple(i+n for i in t) for t in cap)
    for i in range(n):
        j=(i+1)%n
        faces.append((i,j,j+n,i+n))
    return Mesh(verts,tuple(faces),material,name)


def tube(points,width,material='generic',sides=6):
    """A capped 3D tube for arbitrary curve/network-domain fallback geometry."""
    vertices=[]; faces=[]; radius=max(.05,width/2)
    for a,b in zip(points,points[1:]):
        d=tuple(b[i]-a[i] for i in range(3)); length=math.sqrt(sum(v*v for v in d))
        if length<1e-9: continue
        d=tuple(v/length for v in d); helper=(0,0,1) if abs(d[2])<.9 else (0,1,0)
        u=(d[1]*helper[2]-d[2]*helper[1],d[2]*helper[0]-d[0]*helper[2],d[0]*helper[1]-d[1]*helper[0])
        norm=math.sqrt(sum(v*v for v in u)); u=tuple(v/norm for v in u)
        v=(d[1]*u[2]-d[2]*u[1],d[2]*u[0]-d[0]*u[2],d[0]*u[1]-d[1]*u[0])
        offset=len(vertices)
        for p in (a,b):
            for k in range(sides):
                angle=2*math.pi*k/sides
                vertices.append(tuple(p[i]+radius*(math.cos(angle)*u[i]+math.sin(angle)*v[i]) for i in range(3)))
        faces.extend((tuple(offset+k for k in range(sides-1,-1,-1)),tuple(offset+sides+k for k in range(sides))))
        for k in range(sides):
            j=(k+1)%sides
            faces.append((offset+k,offset+j,offset+sides+j,offset+sides+k))
    return Mesh(tuple(vertices),tuple(faces),material,'tube')
