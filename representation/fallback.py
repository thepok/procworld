"""A missing specialized generator is normal, not a rendering failure."""
from ..core.domain import (UnboundedDomain,PointDomain,CurveDomain,AreaDomain,VolumeDomain,
                           SurfaceDomain,PrismDomain,NetworkDomain)
from ..core.scope import Transform
from .geometry import GeometryBundle,Instance,Mesh,box_instance,ribbon,triangulate_polygon,tube,extrude_polygon


FALLBACKS={}


def register_fallback(domain_class,provider):
    if domain_class in FALLBACKS: raise ValueError('Fallback already registered')
    FALLBACKS[domain_class]=provider


def fallback(node,material='generic'):
    d=node.domain
    provider=next((FALLBACKS[c] for c in type(d).__mro__ if c in FALLBACKS),None)
    if provider: return provider(d,material)
    b=d.bounds
    return GeometryBundle(instances=(box_instance(b.center,b.size,material),))


register_fallback(UnboundedDomain,lambda d,m:GeometryBundle())
register_fallback(PointDomain,lambda d,m:GeometryBundle(instances=(
    Instance('canopy',Transform(d.position,(max(.3,d.radius*2),)*3),m),)))
register_fallback(CurveDomain,lambda d,m:GeometryBundle(meshes=(tube(d.points,max(.1,d.width),m),)))
register_fallback(AreaDomain,lambda d,m:GeometryBundle(meshes=(Mesh(d.vertices,triangulate_polygon(d.vertices),m),)))
register_fallback(VolumeDomain,lambda d,m:GeometryBundle(instances=(box_instance(d.bounds.center,d.bounds.size,m),)))
register_fallback(SurfaceDomain,lambda d,m:GeometryBundle(meshes=(Mesh(
    tuple((p[0],p[1],d.minimum_z) for p in d.area.vertices),
    triangulate_polygon(d.area.vertices),m),)))
register_fallback(PrismDomain,lambda d,m:GeometryBundle(meshes=(
    extrude_polygon(d.area.vertices,d.minimum_z,d.maximum_z,m,'prism_fallback'),)))
register_fallback(NetworkDomain,lambda d,m:GeometryBundle(meshes=tuple(
    tube((d.vertices[a],d.vertices[b]),max(.1,d.width),m) for a,b in d.edges)))



def _curve_fallback(domain,material):
    mesh=tube(domain.points,max(.1,domain.width),material)
    if mesh.faces: return GeometryBundle(meshes=(mesh,))
    return GeometryBundle(instances=(Instance('canopy',Transform(domain.anchor,(max(.3,domain.width),)*3),material),))


def _network_fallback(domain,material):
    meshes=tuple(tube((domain.vertices[a],domain.vertices[b]),max(.1,domain.width),material)
                 for a,b in domain.edges if domain.vertices[a]!=domain.vertices[b])
    if meshes: return GeometryBundle(meshes=meshes)
    return GeometryBundle(instances=tuple(Instance('canopy',Transform(p,(max(.3,domain.width),)*3),material)
                                         for p in domain.vertices))


FALLBACKS[CurveDomain]=_curve_fallback
FALLBACKS[NetworkDomain]=_network_fallback
