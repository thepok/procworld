"""Spatial domains in absolute world coordinates (XY ground plane, Z up)."""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import ClassVar, Callable

Vec3 = tuple[float, float, float]
EPS = 1e-7


def point(value) -> Vec3:
    out = tuple(float(v) for v in value)
    if len(out) != 3 or not all(math.isfinite(v) for v in out):
        raise ValueError('Expected a finite 3D point')
    return out


@dataclass(frozen=True, slots=True)
class Bounds:
    minimum: Vec3
    maximum: Vec3

    def __post_init__(self):
        object.__setattr__(self, 'minimum', point(self.minimum))
        object.__setattr__(self, 'maximum', point(self.maximum))
        if any(a > b for a, b in zip(self.minimum, self.maximum)):
            raise ValueError('Inverted bounds')

    @property
    def center(self) -> Vec3:
        return tuple((a+b)/2 for a, b in zip(self.minimum, self.maximum))

    @property
    def size(self) -> Vec3:
        return tuple(b-a for a, b in zip(self.minimum, self.maximum))

    @property
    def corners(self) -> tuple[Vec3, ...]:
        a, b = self.minimum, self.maximum
        return tuple((x, y, z) for x in (a[0], b[0])
                     for y in (a[1], b[1]) for z in (a[2], b[2]))

    def contains_point(self, p: Vec3, epsilon: float = EPS) -> bool:
        return all(a-epsilon <= v <= b+epsilon
                   for a, b, v in zip(self.minimum, self.maximum, p))

    def contains(self, other: 'Bounds') -> bool:
        return self.contains_point(other.minimum) and self.contains_point(other.maximum)

    def intersects(self, other: 'Bounds', xy_only: bool = False) -> bool:
        n = 2 if xy_only else 3
        return all(self.minimum[i] <= other.maximum[i]+EPS and
                   self.maximum[i]+EPS >= other.minimum[i] for i in range(n))

    def expanded(self, amount: float) -> 'Bounds':
        if amount < 0:
            raise ValueError('Expansion must be nonnegative')
        return Bounds(tuple(v-amount for v in self.minimum),
                      tuple(v+amount for v in self.maximum))


def _bounds(points: tuple[Vec3, ...], padding: float = 0) -> Bounds:
    if not points:
        raise ValueError('A finite domain needs at least one point')
    return Bounds(tuple(min(p[i] for p in points)-padding for i in range(3)),
                  tuple(max(p[i] for p in points)+padding for i in range(3)))


def segment_distance(p: Vec3, a: Vec3, b: Vec3, xy_only: bool = False) -> float:
    n = 2 if xy_only else 3
    d = [b[i]-a[i] for i in range(n)]
    den = sum(x*x for x in d)
    t = max(0., min(1., sum((p[i]-a[i])*d[i] for i in range(n))/den)) if den else 0.
    return math.sqrt(sum((p[i]-a[i]-t*d[i])**2 for i in range(n)))


def polygon_contains(vertices: tuple[Vec3, ...], p: Vec3) -> bool:
    inside = False
    x, y = p[:2]
    for a, b in zip(vertices, vertices[1:]+vertices[:1]):
        if segment_distance(p, a, b, True) <= EPS:
            return True
        if (a[1] > y) != (b[1] > y):
            cross = (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]
            if x < cross:
                inside = not inside
    return inside


def _segment_inside_polygon(vertices, a, b) -> bool:
    """Test all intervals split by boundary intersections, not just endpoints."""
    if not polygon_contains(vertices, a) or not polygon_contains(vertices, b):
        return False
    ts = [0., 1.]
    dx, dy = b[0]-a[0], b[1]-a[1]
    for c, d in zip(vertices, vertices[1:]+vertices[:1]):
        ex, ey = d[0]-c[0], d[1]-c[1]
        det = dx*ey-dy*ex
        if abs(det) > EPS:
            t = ((c[0]-a[0])*ey-(c[1]-a[1])*ex)/det
            u = ((c[0]-a[0])*dy-(c[1]-a[1])*dx)/det
            if 0 < t < 1 and -EPS <= u <= 1+EPS:
                ts.append(t)
    ts.sort()
    return all(polygon_contains(vertices, (a[0]+dx*(s+t)/2,
                                            a[1]+dy*(s+t)/2, a[2]))
               for s, t in zip(ts, ts[1:]))


class Domain:
    type_id: ClassVar[str] = 'domain'
    @property
    def bounds(self) -> Bounds:
        raise NotImplementedError
    @property
    def anchor(self) -> Vec3:
        return self.bounds.center
    def contains_point(self, p: Vec3) -> bool:
        return self.bounds.contains_point(p)
    def contains_domain(self, child: 'Domain') -> bool:
        return self.bounds.contains(child.bounds)
    def to_data(self) -> dict:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class UnboundedDomain(Domain):
    type_id: ClassVar[str] = 'unbounded'
    @property
    def bounds(self):
        # A root has no finite bounds; callers must explicitly handle it.
        raise ValueError('The world root has no finite spatial boundary')
    @property
    def anchor(self):
        return (0., 0., 0.)
    def contains_point(self, p):
        return True
    def contains_domain(self, child):
        return True
    def to_data(self):
        return {'type': self.type_id}


@dataclass(frozen=True, slots=True)
class PointDomain(Domain):
    position: Vec3
    radius: float = 0.
    type_id: ClassVar[str] = 'point'
    def __post_init__(self):
        object.__setattr__(self, 'position', point(self.position))
        if self.radius < 0 or not math.isfinite(self.radius):
            raise ValueError('Invalid point radius')
    @property
    def bounds(self):
        return _bounds((self.position,), self.radius)
    def contains_point(self, p):
        return math.dist(self.position, p) <= self.radius+EPS
    def contains_domain(self, child):
        return all(self.contains_point(p) for p in child.bounds.corners)
    def to_data(self):
        return {'type': self.type_id, 'position': self.position, 'radius': self.radius}


@dataclass(frozen=True, slots=True)
class CurveDomain(Domain):
    points: tuple[Vec3, ...]
    width: float = 0.
    type_id: ClassVar[str] = 'curve'
    def __post_init__(self):
        object.__setattr__(self, 'points', tuple(point(p) for p in self.points))
        if len(self.points) < 2 or self.width < 0 or not math.isfinite(self.width):
            raise ValueError('A curve needs >=2 points and a nonnegative width')
    @property
    def bounds(self):
        return _bounds(self.points, self.width/2)
    def contains_point(self, p):
        return any(segment_distance(p,a,b) <= self.width/2+EPS
                   for a,b in zip(self.points,self.points[1:]))
    def contains_domain(self, child):
        # Conservative: a child's whole AABB must fit in ONE convex capsule.
        return any(all(segment_distance(p,a,b) <= self.width/2+EPS
                       for p in child.bounds.corners)
                   for a,b in zip(self.points,self.points[1:]))
    def to_data(self):
        return {'type':self.type_id, 'points':self.points, 'width':self.width}


@dataclass(frozen=True, slots=True)
class AreaDomain(Domain):
    vertices: tuple[Vec3, ...]
    type_id: ClassVar[str] = 'area'
    def __post_init__(self):
        object.__setattr__(self, 'vertices', tuple(point(p) for p in self.vertices))
        if len(self.vertices) < 3 or abs(self.signed_area) < EPS:
            raise ValueError('An area needs a nondegenerate polygon')
    @classmethod
    def rectangle(cls, x0, y0, x1, y1, z=0):
        if x1 <= x0 or y1 <= y0:
            raise ValueError('Empty rectangle')
        return cls(((x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z)))
    @property
    def signed_area(self):
        return sum(a[0]*b[1]-b[0]*a[1] for a,b in
                   zip(self.vertices,self.vertices[1:]+self.vertices[:1]))/2
    @property
    def area(self):
        return abs(self.signed_area)
    @property
    def bounds(self):
        return _bounds(self.vertices)
    def contains_point(self, p):
        # Area domains constrain the footprint, not altitude.
        return polygon_contains(self.vertices,p)
    def contains_domain(self, child):
        b = child.bounds
        a = self.bounds
        if not (a.minimum[0]-EPS <= b.minimum[0] and a.maximum[0]+EPS >= b.maximum[0]
                and a.minimum[1]-EPS <= b.minimum[1] and a.maximum[1]+EPS >= b.maximum[1]):
            return False
        if isinstance(child, AreaDomain):
            outline = child.vertices
        else:
            x,y,_ = b.minimum; X,Y,_ = b.maximum
            outline = ((x,y,0),(X,y,0),(X,Y,0),(x,Y,0))
        return all(_segment_inside_polygon(self.vertices,p,q)
                   for p,q in zip(outline,outline[1:]+outline[:1]))
    def to_data(self):
        return {'type':self.type_id,'vertices':self.vertices}


@dataclass(frozen=True, slots=True)
class VolumeDomain(Domain):
    box: Bounds
    type_id: ClassVar[str] = 'volume'
    @property
    def bounds(self):
        return self.box
    def to_data(self):
        return {'type':self.type_id,'minimum':self.box.minimum,'maximum':self.box.maximum}


@dataclass(frozen=True, slots=True)
class SurfaceDomain(Domain):
    area: AreaDomain
    minimum_z: float
    maximum_z: float
    type_id: ClassVar[str] = 'surface'
    def __post_init__(self):
        if not math.isfinite(self.minimum_z+self.maximum_z) or self.minimum_z > self.maximum_z:
            raise ValueError('Invalid surface height range')
    @property
    def bounds(self):
        b = self.area.bounds
        return Bounds((*b.minimum[:2],self.minimum_z),(*b.maximum[:2],self.maximum_z))
    def contains_point(self, p):
        return self.minimum_z-EPS <= p[2] <= self.maximum_z+EPS and self.area.contains_point(p)
    def contains_domain(self, child):
        return self.bounds.contains(child.bounds) and self.area.contains_domain(child)
    def to_data(self):
        return {'type':self.type_id,'area':self.area.to_data(),
                'minimum_z':self.minimum_z,'maximum_z':self.maximum_z}


@dataclass(frozen=True, slots=True)
class NetworkDomain(Domain):
    vertices: tuple[Vec3, ...]
    edges: tuple[tuple[int,int], ...]
    width: float = 0.
    type_id: ClassVar[str] = 'network'
    def __post_init__(self):
        object.__setattr__(self,'vertices',tuple(point(p) for p in self.vertices))
        object.__setattr__(self,'edges',tuple(tuple(e) for e in self.edges))
        if not self.vertices or self.width < 0 or not math.isfinite(self.width):
            raise ValueError('Invalid network')
        if any(len(e)!=2 or min(e)<0 or max(e)>=len(self.vertices) for e in self.edges):
            raise ValueError('Invalid network edge')
    @property
    def bounds(self):
        return _bounds(self.vertices,self.width/2)
    def contains_point(self,p):
        return any(segment_distance(p,self.vertices[a],self.vertices[b]) <= self.width/2+EPS
                   for a,b in self.edges)
    def contains_domain(self,child):
        return any(all(segment_distance(p,self.vertices[a],self.vertices[b]) <= self.width/2+EPS
                       for p in child.bounds.corners) for a,b in self.edges)
    def to_data(self):
        return {'type':self.type_id,'vertices':self.vertices,'edges':self.edges,'width':self.width}


DOMAIN_READERS: dict[str, Callable[[dict], Domain]] = {
    'unbounded': lambda d: UnboundedDomain(),
    'point': lambda d: PointDomain(d['position'],d.get('radius',0)),
    'curve': lambda d: CurveDomain(tuple(d['points']),d.get('width',0)),
    'area': lambda d: AreaDomain(tuple(d['vertices'])),
    'volume': lambda d: VolumeDomain(Bounds(d['minimum'],d['maximum'])),
    'surface': lambda d: SurfaceDomain(domain_from_data(d['area']),d['minimum_z'],d['maximum_z']),
    'network': lambda d: NetworkDomain(tuple(d['vertices']),tuple(d['edges']),d.get('width',0)),
}


def register_domain(type_id: str, reader: Callable[[dict], Domain]):
    if type_id in DOMAIN_READERS:
        raise ValueError(f'Domain already registered: {type_id}')
    DOMAIN_READERS[type_id] = reader


def domain_from_data(data: dict) -> Domain:
    try:
        reader = DOMAIN_READERS[data['type']]
    except KeyError as exc:
        raise ValueError(f"Unknown domain type: {data.get('type')}") from exc
    return reader(data)
