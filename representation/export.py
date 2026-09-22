"""Portable, dependency-free exports for inspection without Blender."""
from __future__ import annotations
import json
from pathlib import Path
from html import escape
from .geometry import MATERIALS
from ..core.seed import canonical


def export_obj(scene,path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    mtl=path.with_suffix('.mtl')
    materials={m.material for _,m in scene.expanded_meshes()}
    with mtl.open('w',encoding='utf8') as f:
        for name in sorted(materials):
            color=MATERIALS.get(name,MATERIALS['generic'])
            f.write(f'newmtl {name}\nKd {color[0]} {color[1]} {color[2]}\nKa 0.05 0.05 0.05\nd {color[3]}\n\n')
    offset=1
    with path.open('w',encoding='utf8') as f:
        f.write(f'# Hierarchical Procedural World; Z up; meters\nmtllib {mtl.name}\n')
        for node_id,mesh in scene.expanded_meshes():
            f.write(f'g {node_id.replace(":","_")}\nusemtl {mesh.material}\n')
            for x,y,z in mesh.vertices: f.write(f'v {x:.6f} {y:.6f} {z:.6f}\n')
            for face in mesh.faces: f.write('f '+' '.join(str(i+offset) for i in face)+'\n')
            offset+=len(mesh.vertices)
    return path


def export_svg(snapshot,path,size=1200):
    """Top-down semantic debug map, not a 3D renderer."""
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    cx,cy=snapshot.center; radius=snapshot.radius*snapshot.halo
    scale=size/(2*radius)
    def xy(p): return ((p[0]-cx+radius)*scale,(cy+radius-p[1])*scale)
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">',
           '<rect width="100%" height="100%" fill="#d4d9c3"/>']
    draw_order={'Terrain':0,'Water':1,'Vegetation':2,'Roads':3,'Buildings':4,'Props':5}
    nodes=sorted(snapshot.graph.active(snapshot.time),key=lambda n:(draw_order.get(snapshot.scene.categories.get(n.id,''),0),n.id))
    for n in nodes:
        if n.id not in snapshot.scene.bundles: continue
        category=snapshot.scene.categories.get(n.id,'Generic')
        if category=='Terrain': continue
        color={'Water':'#659faf','Vegetation':'#769052','Roads':'#595b58','Buildings':'#ae8566','Props':'#82694f'}.get(category,'#ad9eb6')
        title=escape(f'{n.type_id} {n.id}\ncreated: {n.created_at:.1f}')
        if hasattr(n.domain,'points'):
            coords=' '.join(f'{x:.2f},{y:.2f}' for x,y in map(xy,n.domain.points))
            width=max(1,getattr(n.domain,'width',1)*scale)
            lines.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width:.2f}"><title>{title}</title></polyline>')
        else:
            b=n.domain.bounds; x,y=xy((b.minimum[0],b.maximum[1],0)); w,h=b.size[:2]
            lines.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(1,w*scale):.2f}" height="{max(1,h*scale):.2f}" fill="{color}" stroke="#eee9da" stroke-width="0.3"><title>{title}</title></rect>')
    lines.extend((f'<text x="20" y="32" font-family="sans-serif" font-size="20">World year {snapshot.time:g} · seed {escape(str(snapshot.seed))}</text>','</svg>'))
    path.write_text('\n'.join(lines),encoding='utf8'); return path


def export_snapshot(snapshot,path,include_graph=False):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    data=snapshot.to_data(include_graph=include_graph)
    path.write_text(json.dumps(data,sort_keys=True,indent=2,allow_nan=False),encoding='utf8')
    return path
