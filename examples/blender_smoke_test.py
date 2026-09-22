"""Run with Blender, not ordinary Python.

blender --background --factory-startup --python procedural_world/examples/blender_smoke_test.py

The authoring environment did not contain Blender; this script is provided for
runtime verification on your Blender installation.
"""
from pathlib import Path
import sys
import json
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import bpy
from mathutils import Vector
import procedural_world

procedural_world.register()
try:
    bpy.ops.pw.add_root()
    root=bpy.context.active_object
    root.pw_settings.radius=200; root.pw_settings.halo=1
    root.pw_settings.structural=1; root.pw_settings.geometric=1
    data=bpy.data.cameras.new('DemoCamera'); camera=bpy.data.objects.new('DemoCamera',data)
    bpy.context.scene.collection.objects.link(camera); camera.location=(500,-650,420)
    camera.rotation_euler=(Vector((0,0,40))-camera.location).to_track_quat('-Z','Y').to_euler()
    data.clip_end=10000; bpy.context.scene.camera=camera; root.pw_settings.camera=camera
    sun_data=bpy.data.lights.new('DemoSun','SUN'); sun_data.energy=2.5
    sun=bpy.data.objects.new('DemoSun',sun_data); bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler=(.45,-.6,-.2)
    result=bpy.ops.pw.generate()
    assert result=={'FINISHED'},result
    bpy.context.view_layer.update()
    generated=[c for c in bpy.context.scene.collection.children if c.get('pw_snapshot_owner')==root['pw_root_id']]
    assert len(generated)==1
    assert any(obj.type=='MESH' and len(obj.data.polygons)>0 for obj in generated[0].all_objects)
    depsgraph=bpy.context.evaluated_depsgraph_get()
    instance_count=sum(1 for obj in depsgraph.object_instances if obj.is_instance)
    print(json.dumps({'blender_version':bpy.app.version_string,'generated_objects':len(generated[0].all_objects),
                      'evaluated_instances':instance_count,'summary':root['pw_summary']}))
    # Verify replacement doesn't remove an unrelated user object.
    marker=bpy.data.objects.new('UserObjectMustSurvive',None); bpy.context.scene.collection.objects.link(marker)
    assert bpy.ops.pw.generate()=={'FINISHED'}
    assert marker.name in bpy.data.objects
    bpy.ops.wm.save_as_mainfile(filepath=str(Path('procedural_world_demo.blend').resolve()))
finally:
    procedural_world.unregister()
