"""Deterministic polygonal building footprints.

The building footprint is semantic state, not a by-product of mesh generation.
This module deliberately generates simple polygons without holes so they can be
represented by the core AreaDomain/PrismDomain types and refined safely later.
"""
from __future__ import annotations
from ..core.domain import AreaDomain, EPS


def _xy_polygon(kind, x0, y0, x1, y1, rng):
    w=x1-x0; h=y1-y0; cx=(x0+x1)/2
    if kind=='rectangle':
        return ((x0,y0),(x1,y0),(x1,y1),(x0,y1))
    if kind=='l_shape':
        xm=x0+w*rng.uniform(.46,.72,'l','x')
        ym=y0+h*rng.uniform(.38,.66,'l','y')
        return ((x0,y0),(x1,y0),(x1,ym),(xm,ym),(xm,y1),(x0,y1))
    if kind=='t_shape':
        bar=y0+h*rng.uniform(.30,.48,'t','bar')
        stem=w*rng.uniform(.30,.48,'t','stem')
        return ((x0,y0),(x1,y0),(x1,bar),(cx+stem/2,bar),(cx+stem/2,y1),
                (cx-stem/2,y1),(cx-stem/2,bar),(x0,bar))
    if kind=='u_shape':
        tx=w*rng.uniform(.20,.30,'u','tx')
        ty=h*rng.uniform(.20,.32,'u','ty')
        return ((x0,y0),(x1,y0),(x1,y1),(x1-tx,y1),(x1-tx,y0+ty),
                (x0+tx,y0+ty),(x0+tx,y1),(x0,y1))
    if kind=='stepped':
        xm=x0+w*rng.uniform(.55,.78,'step','x')
        ym=y0+h*rng.uniform(.42,.68,'step','y')
        return ((x0,y0),(x1,y0),(x1,ym),(xm,ym),(xm,y1),(x0,y1))
    if kind=='chamfered':
        c=min(w,h)*rng.uniform(.08,.18,'chamfer','amount')
        # Unequal corner cuts keep the silhouette from degenerating into a
        # symmetric octagon while remaining convex and easy to subdivide.
        a=(.75,.95,1.1,.85)
        return ((x0+c*a[0],y0),(x1-c*a[1],y0),(x1,y0+c*a[1]),
                (x1,y1-c*a[2]),(x1-c*a[2],y1),(x0+c*a[3],y1),
                (x0,y1-c*a[3]),(x0,y0+c*a[0]))
    raise ValueError(f'Unknown footprint kind: {kind}')


def _candidate_kinds(usage, birth, minimum_span):
    if minimum_span < 9:
        return ('rectangle','chamfered')
    if usage=='industrial':
        return ('rectangle','rectangle','stepped','chamfered')
    if birth < 1850:
        return ('rectangle','rectangle','l_shape','chamfered')
    if birth < 1945:
        return ('rectangle','l_shape','l_shape','u_shape','stepped','chamfered')
    if usage=='commercial':
        return ('rectangle','t_shape','l_shape','stepped','chamfered','chamfered')
    return ('rectangle','l_shape','t_shape','u_shape','stepped','chamfered')


def polygon_centroid(vertices):
    """Centroid of a non-self-intersecting XY polygon."""
    area2=0.; xsum=0.; ysum=0.
    for a,b in zip(vertices,vertices[1:]+vertices[:1]):
        cross=a[0]*b[1]-b[0]*a[1]
        area2+=cross; xsum+=(a[0]+b[0])*cross; ysum+=(a[1]+b[1])*cross
    if abs(area2)<EPS:
        return (sum(p[0] for p in vertices)/len(vertices),sum(p[1] for p in vertices)/len(vertices))
    return (xsum/(3*area2),ysum/(3*area2))


def footprint_for_parcel(parcel, rng, usage, birth):
    """Return ``(kind, xy_vertices, setback)`` inside *parcel*.

    AABB geometry is used only to propose candidates.  The parcel domain makes
    the final acceptance decision, so the returned polygon remains a true
    child of the semantic parcel.
    """
    b=parcel.domain.bounds; x0,y0=b.minimum[:2]; x1,y1=b.maximum[:2]
    w=x1-x0; h=y1-y0
    max_setback=max(.35,min(5.,min(w,h)*.22))
    setback=min(max_setback,rng.uniform(.8,max_setback,'setback'))
    kinds=_candidate_kinds(usage,birth,min(w,h))
    preferred=rng.choice(kinds,'footprint_kind')
    ordered=(preferred,)+tuple(k for k in kinds if k!=preferred)+('rectangle',)
    seen=set()
    for scale in (1.,.90,.80,.68,.55):
        inset=setback+(1-scale)*min(w,h)*.25
        ax0,ay0,ax1,ay1=x0+inset,y0+inset,x1-inset,y1-inset
        if ax1-ax0<2 or ay1-ay0<2: continue
        for kind in ordered:
            if kind in seen and scale==1.: continue
            try:
                xy=_xy_polygon(kind,ax0,ay0,ax1,ay1,rng)
                area=AreaDomain(tuple((x,y,0.) for x,y in xy))
            except ValueError:
                continue
            if parcel.domain.contains_domain(area):
                return kind,xy,inset
            seen.add(kind)
    # Irregular authored parcels may have no useful axis-aligned inscribed
    # rectangle.  In that case, using their own polygon is still better than
    # lying about the building with an AABB.
    parcel_area=getattr(parcel.domain,'area',None)
    if isinstance(parcel.domain,AreaDomain): parcel_area=parcel.domain
    if isinstance(parcel_area,AreaDomain):
        return 'parcel_fill',tuple((p[0],p[1]) for p in parcel_area.vertices),0.
    raise ValueError('Parcel has no usable polygonal building footprint')
