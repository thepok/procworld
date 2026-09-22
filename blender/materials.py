"""Blender materials are created only by the optional backend."""
from ..representation.geometry import MATERIALS


def material(name):
    import bpy
    full='PW_Material_'+name
    existing=bpy.data.materials.get(full)
    if existing is not None and existing.get('pw_material')==name: return existing
    result=bpy.data.materials.new(full); result['pw_material']=name
    color=MATERIALS.get(name,MATERIALS['generic'])
    result.diffuse_color=color; result.use_nodes=True
    bsdf=result.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value=color
        bsdf.inputs['Roughness'].default_value=.25 if name in {'water','window','glass'} else (.42 if name=='metal' else .82)
        if 'Metallic' in bsdf.inputs: bsdf.inputs['Metallic'].default_value=.65 if name=='metal' else (.15 if name in {'window','glass'} else 0.)
    return result
