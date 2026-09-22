"""Persistent downhill drainage. Coarse local sinks are lakes, not fake outlets.

Each source is owned by a canonical region. Paths may cross region boundaries;
no path is clipped/reseeded at a requested scene boundary. This is not a global
flow-accumulation or physically complete hydrology solver.
"""
import math
from ..core.seed import RandomStream


def drainage_path(fields,region_coord,region_size,seed,max_steps=42,step=72.):
    cx,cy=(c*region_size for c in region_coord)
    rng=RandomStream(seed,'drainage',region_coord)
    candidates=[(cx+rng.uniform(-region_size*.4,region_size*.4,'x',i),
                 cy+rng.uniform(-region_size*.4,region_size*.4,'y',i)) for i in range(7)]
    x,y=max(candidates,key=lambda p:(fields.height(*p),p))
    z=fields.height(x,y)
    if z<fields.sea_level+18: return (),False
    points=[(x,y,z+.18)]; seen=set()
    for _ in range(max_steps):
        choices=[]
        for dx,dy in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
            nx,ny=x+dx*step,y+dy*step; nz=fields.height(nx,ny)
            slope=(z-nz)/(step*math.hypot(dx,dy))
            if nz<z-.05 and (round(nx,5),round(ny,5)) not in seen:
                choices.append((slope,-nz,nx,ny,nz))
        if not choices: return tuple(points),True
        _,_,x,y,z=max(choices)
        seen.add((round(x,5),round(y,5)))
        points.append((x,y,max(z+.18,fields.sea_level+.03)))
        if z<=fields.sea_level: return tuple(points),False
    return tuple(points),False
