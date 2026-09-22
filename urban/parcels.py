from ..core.domain import AreaDomain


def subdivide_rectangular_block(domain:AreaDomain,columns=2,rows=2,gap=1.):
    if columns<=0 or rows<=0 or gap<0: raise ValueError('Invalid subdivision parameters')
    b=domain.bounds; x,y=b.minimum[:2]; w,h=b.size[:2]
    if w/columns<=2*gap or h/rows<=2*gap: raise ValueError('Block is too small for requested parcels')
    return tuple((i,j,AreaDomain.rectangle(x+i*w/columns+gap,y+j*h/rows+gap,
                                          x+(i+1)*w/columns-gap,y+(j+1)*h/rows-gap))
                 for j in range(rows) for i in range(columns))
