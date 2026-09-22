"""Transactional scene realization, material batches, and Geometry Nodes instances.

Only generated, owner-tagged objects are replaced. User objects are never purged.
No collection or Blender object is required for every semantic node.
"""
from __future__ import annotations
from collections import defaultdict
import json
import math
import uuid
from ..representation.geometry import GeometryScene,PROTOTYPES
from .materials import material

OWNER='pw_generated_owner'


def _remove_object(obj):
    import bpy
    data=obj.data
    groups=[m.node_group for m in obj.modifiers if m.type=='NODES' and m.node_group]
    bpy.data.objects.remove(obj,do_unlink=True)
    if data is not None and data.users==0 and isinstance(data,bpy.types.Mesh): bpy.data.meshes.remove(data)
    for group in groups:
        if group.users==0 and group.get(OWNER): bpy.data.node_groups.remove(group)


def remove_generated(collection,owner,scene):
    """Preserve unrelated objects even if a user linked them into an output collection."""
    import bpy
    for child in list(collection.children):
        if child.get(OWNER)==owner:
            remove_generated(child,owner,scene)
        else:
            if child.name not in scene.collection.children: scene.collection.children.link(child)
            collection.children.unlink(child)
    for obj in list(collection.objects):
        if obj.get(OWNER)==owner:
            _remove_object(obj)
        else:
            if obj.name not in scene.collection.objects: scene.collection.objects.link(obj)
            collection.objects.unlink(obj)
    bpy.data.collections.remove(collection)


def _new_mesh_object(name,vertices,faces,collection,root,owner,material_name,ids,face_ids=None):
    import bpy
    data=bpy.data.meshes.new(name+'_Mesh'); data[OWNER]=owner
    data.from_pydata(vertices,[],faces); data.update()
    data.materials.append(material(material_name))
    if face_ids:
        attribute=data.attributes.new('pw_semantic_index','INT','FACE')
        attribute.data.foreach_set('value',face_ids)
    obj=bpy.data.objects.new(name,data); obj[OWNER]=owner; obj['pw_semantic_ids']=json.dumps(ids)
    collection.objects.link(obj)
    if root is not None: obj.parent=root
    return obj


def _instance_batch(name,instances,prototype,material_name,collection,prototypes_collection,root,owner):
    import bpy
    obj=None; group=None; source=None; group_name=None
    try:
        source=_new_mesh_object(name+'_Prototype',prototype.vertices,prototype.faces,prototypes_collection,
                                None,owner,material_name,[])
        source.hide_render=True; source.hide_set(True)
        positions=[i.transform.translation for _,i in instances]
        obj=_new_mesh_object(name,positions,[],collection,root,owner,material_name,
                             [nid for nid,_ in instances])
        for attr_name,values in (
            ('pw_scale',[v for _,i in instances for v in i.transform.scale]),
            ('pw_rotation',[v for _,i in instances for v in (0.,0.,i.transform.rotation_z)])):
            attr=obj.data.attributes.new(attr_name,'FLOAT_VECTOR','POINT')
            attr.data.foreach_set('vector',values)
        attribute=obj.data.attributes.new('pw_semantic_index','INT','POINT')
        attribute.data.foreach_set('value',list(range(len(instances))))
        group=bpy.data.node_groups.new(name+'_Instances','GeometryNodeTree'); group[OWNER]=owner; group_name=group.name
        group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
        group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
        n=group.nodes; links=group.links
        inp=n.new('NodeGroupInput'); out=n.new('NodeGroupOutput'); out.is_active_output=True
        info=n.new('GeometryNodeObjectInfo'); info.inputs['Object'].default_value=source
        info.transform_space='ORIGINAL'
        if 'As Instance' in info.inputs: info.inputs['As Instance'].default_value=False
        inst=n.new('GeometryNodeInstanceOnPoints')
        scale=n.new('GeometryNodeInputNamedAttribute'); scale.data_type='FLOAT_VECTOR'; scale.inputs['Name'].default_value='pw_scale'
        rotation=n.new('GeometryNodeInputNamedAttribute'); rotation.data_type='FLOAT_VECTOR'; rotation.inputs['Name'].default_value='pw_rotation'
        links.new(inp.outputs['Geometry'],inst.inputs['Points'])
        links.new(info.outputs['Geometry'],inst.inputs['Instance'])
        links.new(scale.outputs['Attribute'],inst.inputs['Scale'])
        links.new(rotation.outputs['Attribute'],inst.inputs['Rotation'])
        links.new(inst.outputs['Instances'],out.inputs['Geometry'])
        modifier=obj.modifiers.new('Procedural World Instances','NODES'); modifier.node_group=group
        obj['pw_representation']='instanced_points'
        return obj
    except Exception:
        if obj is not None: _remove_object(obj)
        remaining=bpy.data.node_groups.get(group_name) if group_name else None
        if remaining is not None and remaining.users==0: bpy.data.node_groups.remove(remaining)
        if source is not None and source.name in bpy.data.objects: _remove_object(source)
        raise


def realize_snapshot(snapshot,root,scene,*,use_instances=True,debug=None):
    import bpy
    owner=root.get('pw_root_id')
    if not owner: raise ValueError('The Blender root is missing pw_root_id')
    old=[c for c in list(scene.collection.children) if c.get('pw_snapshot_owner')==owner]
    stage=bpy.data.collections.new('PW_Staging_'+uuid.uuid4().hex[:8]); stage[OWNER]=owner
    stage['pw_snapshot_owner']=owner; scene.collection.children.link(stage)
    categories={}; warnings=[]
    def category(name):
        if name not in categories:
            c=bpy.data.collections.new(name); c[OWNER]=owner; stage.children.link(c); categories[name]=c
        return categories[name]
    meshes=defaultdict(list); instances=defaultdict(list); prototypes=snapshot.scene.prototypes()
    scenes=[snapshot.scene]+([debug] if debug else [])
    for source in scenes:
        prototypes.update(source.prototypes())
        for node_id,bundle in sorted(source.bundles.items()):
            cat=source.categories.get(node_id,'Props')
            for mesh in bundle.meshes: meshes[cat,mesh.material].append((node_id,mesh))
            for instance in bundle.instances: instances[cat,instance.prototype,instance.material].append((node_id,instance))
    try:
        for (cat,prototype_name,mat),batch in sorted(instances.items()):
            prototype=prototypes[prototype_name]
            if use_instances:
                try:
                    _instance_batch(f'PW_{cat}_{prototype_name}_{mat}',batch,prototype,mat,
                                    category(cat),category('Prototypes'),root,owner)
                    continue
                except Exception as exc:
                    warnings.append(f'Instancing fell back to mesh batching: {exc}')
            for node_id,instance in batch:
                meshes[cat,mat].append((node_id,prototype.transformed(instance.transform,mat)))
        for (cat,mat),batch in sorted(meshes.items()):
            vertices=[]; faces=[]; face_ids=[]; ids=[]; id_index={}
            # Limit individual mesh sizes; there is still no object-per-semantic-node requirement.
            chunk=0
            def flush():
                nonlocal vertices,faces,face_ids,ids,id_index,chunk
                if not faces: return
                obj=_new_mesh_object(f'PW_{cat}_{mat}_{chunk}',vertices,faces,category(cat),root,owner,mat,ids,face_ids)
                obj['pw_representation']='batched_mesh'; chunk+=1
                vertices=[]; faces=[]; face_ids=[]; ids=[]; id_index={}
            for node_id,mesh in batch:
                if len(vertices)+len(mesh.vertices)>200000: flush()
                semantic=node_id[6:] if node_id.startswith('Debug:') else node_id
                if semantic not in id_index: id_index[semantic]=len(ids); ids.append(semantic)
                index=id_index[semantic]; offset=len(vertices)
                vertices.extend(mesh.vertices); faces.extend(tuple(i+offset for i in f) for f in mesh.faces)
                face_ids.extend([index]*len(mesh.faces))
            flush()
        stage.name='Generated_World_'+owner[:8]
        stage['pw_snapshot_year']=snapshot.time
        stage['pw_snapshot_fingerprint']=snapshot.fingerprint()
        stage['pw_backend_warnings']=json.dumps(warnings)
    except Exception:
        remove_generated(stage,owner,scene)
        raise
    # Commit the replacement only after every new batch has been constructed.
    for collection in old: remove_generated(collection,owner,scene)
    return stage,warnings
