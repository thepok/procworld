"""Projected bounding-sphere importance, with perspective and orthographic cameras."""
from dataclasses import dataclass
import math
from ..core.domain import Bounds,Vec3,point


def _dot(a,b): return sum(x*y for x,y in zip(a,b))
def _sub(a,b): return tuple(x-y for x,y in zip(a,b))
def _cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def _normal(v):
    length=math.sqrt(_dot(v,v))
    if length<1e-12: raise ValueError('Degenerate camera orientation')
    return tuple(x/length for x in v)


@dataclass(frozen=True,slots=True)
class Camera:
    position: Vec3 = (600.,-850.,700.)
    target: Vec3 = (0.,0.,30.)
    up: Vec3 = (0.,0.,1.)
    vertical_fov: float = 50.
    width: int = 1920
    height: int = 1080
    near: float = .1
    far: float = 20000.
    orthographic_scale: float|None = None
    def __post_init__(self):
        for k in ('position','target','up'): object.__setattr__(self,k,point(getattr(self,k)))
        if not 1<self.vertical_fov<179 or self.width<=0 or self.height<=0 or self.near<=0 or self.far<=self.near:
            raise ValueError('Invalid camera projection')
        if self.orthographic_scale is not None and self.orthographic_scale<=0:
            raise ValueError('Invalid orthographic scale')
        forward=_normal(_sub(self.target,self.position)); _normal(_cross(forward,self.up))
    def projected_importance(self,bounds:Bounds) -> tuple[float,bool]:
        center=bounds.center; radius=max(.2,math.sqrt(sum(s*s for s in bounds.size))/2)
        forward=_normal(_sub(self.target,self.position))
        right=_normal(_cross(forward,self.up)); up=_cross(right,forward)
        delta=_sub(center,self.position); depth=_dot(delta,forward)
        aspect=self.width/self.height
        if self.orthographic_scale is not None:
            half_y=self.orthographic_scale/2; pixels=2*radius*self.height/self.orthographic_scale
        else:
            half_y=max(self.near,depth)*math.tan(math.radians(self.vertical_fov)/2)
            pixels=radius*self.height/max(half_y,self.near)
        visible=(depth+radius>=self.near and depth-radius<=self.far and
                 abs(_dot(delta,right))<=half_y*aspect+radius and abs(_dot(delta,up))<=half_y+radius)
        return min(pixels,max(self.width,self.height)*4),visible
