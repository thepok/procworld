"""Blender 4.2+ integration. Imported only when the add-on is enabled."""
# Do not enable postponed annotations here: Blender properties must be evaluated.
import json
import math
import uuid
from dataclasses import asdict,replace
import bpy
from bpy.props import (StringProperty,IntProperty,FloatProperty,BoolProperty,EnumProperty,PointerProperty)
from bpy.types import Operator,Panel,PropertyGroup
from mathutils import Vector
from .. import World,WorldSettings,RefinementState,Budget,Camera
from ..core.constraints import InfluenceField
from ..core.domain import AreaDomain
from ..core.seed import digest
from ..core.serialization import world_to_data,world_from_data
from ..refinement.overrides import NodeOverride
from .geometry_backend import realize_snapshot,remove_generated
from .debug_draw import debug_scene

_RUNTIME={}
_SNAPSHOTS={}


def _root_poll(_self,obj): return obj is not None and bool(obj.get('pw_root_id'))
def _camera_poll(_self,obj): return obj is not None and obj.type=='CAMERA'


def find_root(context):
    obj=context.active_object
    while obj:
        if obj.get('pw_root_id'): return obj
        obj=obj.parent
    root=getattr(context.scene,'pw_active_root',None)
    if root and root.name in context.scene.objects: return root
    return next((o for o in context.scene.objects if o.get('pw_root_id')),None)


def _text_json(name,default):
    if not name: return default
    text=bpy.data.texts.get(name)
    if text is None: raise ValueError(f'Blender text block does not exist: {name}')
    return json.loads(text.as_string())


def _write_owned_text(root,key,suffix,payload):
    owner=root['pw_root_id']; old_name=root.get(key,''); text=bpy.data.texts.get(old_name)
    if text is None or text.get('pw_owner')!=owner:
        text=bpy.data.texts.new(f'PW_{owner[:8]}_{suffix}.json'); text['pw_owner']=owner
    text.clear(); text.write(json.dumps(payload,sort_keys=True,allow_nan=False,separators=(',',':')))
    root[key]=text.name
    return text


def _constraints(root,context):
    settings=root.pw_settings
    constraints=[InfluenceField.from_data(c) for c in _text_json(settings.constraints_text,[])]
    inverse=root.matrix_world.inverted()
    for obj in context.scene.objects:
        if obj.get('pw_constraint_owner')!=root['pw_root_id']: continue
        if obj.type=='EMPTY':
            size=obj.empty_display_size
            points=[inverse @ (obj.matrix_world @ Vector((x*size,y*size,0))) for x in (-1,1) for y in (-1,1)]
        else:
            points=[inverse @ (obj.matrix_world @ Vector(p)) for p in obj.bound_box]
        x0=min(p.x for p in points); x1=max(p.x for p in points)
        y0=min(p.y for p in points); y1=max(p.y for p in points)
        if x1-x0<.01 or y1-y0<.01: continue
        until=float(obj.get('pw_active_until',0.))
        constraints.append(InfluenceField(obj.get('pw_constraint_id',obj.name),obj.get('pw_constraint_kind','NoBuildArea'),
            AreaDomain.rectangle(x0,y0,x1,y1),float(obj.get('pw_strength',1.)),float(obj.get('pw_falloff',0.)),
            float(obj.get('pw_active_from',-1000000.)),until if until else None))
    return tuple(constraints)


def _world(root,context):
    s=root.pw_settings; constraints=_constraints(root,context)
    signature=digest(int(s.seed),s.sea_level,s.behavioral_policy,[c.to_data() for c in constraints])
    owner=root['pw_root_id']; cached=_RUNTIME.get(owner)
    if cached and cached[0]==signature:
        world=cached[1]
    elif root.get('pw_world_signature')==signature and root.get('pw_world_text'):
        world=world_from_data(_text_json(root['pw_world_text'],{}))
    else:
        world=World(WorldSettings(seed=int(s.seed),world_time=s.year,sea_level=s.sea_level,
                                  behavioral_level=s.behavioral_policy),constraints=constraints)
    world.settings=replace(world.settings,world_time=s.year)
    explicit=_text_json(s.overrides_text,{})
    world.overrides.update({k:NodeOverride(**v) for k,v in explicit.items()})
    _RUNTIME[owner]=(signature,world)
    return world,signature


def _camera(root,context):
    s=root.pw_settings; camera=s.camera or context.scene.camera
    if camera is None: return None,(0.,0.)
    inverse=root.matrix_world.inverted()
    local=inverse @ camera.matrix_world
    position=local.translation
    forward=local.to_3x3() @ Vector((0,0,-1)); up=local.to_3x3() @ Vector((0,1,0))
    forward.normalize(); up.normalize()
    # Approximate focus on the ground; an explicit core center can override this.
    distance=-position.z/forward.z if abs(forward.z)>.01 else s.radius
    distance=max(s.radius*.3,min(s.radius*5,distance))
    target=position+forward*distance
    center=(target.x,target.y) if s.follow_camera else (s.center_x,s.center_y)
    scale=camera.data.ortho_scale if camera.data.type=='ORTHO' else None
    resolution=context.scene.render
    return Camera(tuple(position),tuple(target),tuple(up),math.degrees(camera.data.angle_y),
                  max(1,resolution.resolution_x),max(1,resolution.resolution_y),
                  max(.01,camera.data.clip_start),max(camera.data.clip_end,10.),scale),center


class PWSettings(PropertyGroup):
    seed: StringProperty(name='Seed',default='12')
    year: FloatProperty(name='World Year',default=2025,min=1680,max=2500,precision=1)
    sea_level: FloatProperty(name='Sea Level',default=0.)
    quality: EnumProperty(name='Budget',items=[(q,q,'') for q in ('PREVIEW','DRAFT','HIGH','FINAL')],default='PREVIEW')
    camera: PointerProperty(name='Camera',type=bpy.types.Object,poll=_camera_poll)
    radius: FloatProperty(name='Core Radius',default=600.,min=30.,max=20000.,subtype='DISTANCE')
    halo: FloatProperty(name='Context Halo',default=2.,min=1.,max=5.)
    follow_camera: BoolProperty(name='Center Core on Camera Focus',default=False)
    center_x: FloatProperty(name='Core X',default=0.)
    center_y: FloatProperty(name='Core Y',default=0.)
    structural: IntProperty(name='Structure',default=1,min=0,max=3)
    geometric: IntProperty(name='Geometry',default=2,min=0,max=3)
    temporal: IntProperty(name='History',default=0,min=0,max=1)
    behavioral: IntProperty(name='Rule Resolution',default=0,min=0,max=1)
    behavioral_policy: IntProperty(name='Growth Policy',default=1,min=0,max=2)
    include_interiors: BoolProperty(name='Interior Cutaway',default=False)
    use_instances: BoolProperty(name='Geometry Nodes Instances',default=True)
    embed_world: BoolProperty(name='Store Semantic World in .blend',default=True)
    constraints_text: StringProperty(name='Constraint JSON Text')
    overrides_text: StringProperty(name='Override JSON Text')
    save_path: StringProperty(name='World JSON',subtype='FILE_PATH',default='//procedural_world.json')
    debug: EnumProperty(name='Debug Overlay',items=[(v,v.title(),'') for v in ('NONE','DOMAINS','AGE','PRESSURE','TYPE')],default='NONE')
    inspect_id: StringProperty(name='Semantic ID')


class PW_OT_add_root(Operator):
    bl_idname='pw.add_root'; bl_label='Add WorldRoot'; bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        root=bpy.data.objects.new('WorldRoot',None); root.empty_display_type='PLAIN_AXES'; root.empty_display_size=20
        root.location=context.scene.cursor.location; root['pw_root_id']=uuid.uuid4().hex
        context.scene.collection.objects.link(root)
        for obj in context.selected_objects: obj.select_set(False)
        root.select_set(True); context.view_layer.objects.active=root; context.scene.pw_active_root=root
        root.pw_settings.camera=context.scene.camera
        return {'FINISHED'}


class PW_OT_generate(Operator):
    bl_idname='pw.generate'; bl_label='Generate Snapshot'; bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        root=find_root(context)
        if root is None:
            self.report({'ERROR'},'Add a WorldRoot first'); return {'CANCELLED'}
        try:
            world,signature=_world(root,context); s=root.pw_settings; camera,center=_camera(root,context)
            snapshot=world.snapshot(time=s.year,camera=camera,center=center,radius=s.radius,halo=s.halo,
                budget=Budget.preset(s.quality),request=RefinementState(s.structural,s.geometric,s.temporal,s.behavioral),
                include_interiors=s.include_interiors)
            debug=debug_scene(snapshot,s.debug) if s.debug!='NONE' else None
            collection,warnings=realize_snapshot(snapshot,root,context.scene,use_instances=s.use_instances,debug=debug)
            _SNAPSHOTS[root['pw_root_id']]=snapshot
            root['pw_world_signature']=signature
            root['pw_summary']=f'{snapshot.report["active_nodes"]} active nodes | {snapshot.scene.cost().triangles:,} triangles'
            root['pw_last_report']=json.dumps(snapshot.report)
            if s.embed_world: _write_owned_text(root,'pw_world_text','world',world_to_data(world))
            _write_owned_text(root,'pw_report_text','report',snapshot.report)
            if warnings or snapshot.report['scheduler']['errors']:
                self.report({'WARNING'},'Snapshot generated with fallbacks; see the report text block')
            else: self.report({'INFO'},root['pw_summary'])
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'},f'{type(exc).__name__}: {exc}'); return {'CANCELLED'}


class PW_OT_save_world(Operator):
    bl_idname='pw.save_world'; bl_label='Save Semantic World'
    def execute(self,context):
        root=find_root(context)
        if root is None: return {'CANCELLED'}
        try:
            world,signature=_world(root,context)
            path=bpy.path.abspath(root.pw_settings.save_path); world.save(path)
            self.report({'INFO'},f'Saved semantic world: {path}'); return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class PW_OT_load_world(Operator):
    bl_idname='pw.load_world'; bl_label='Load Semantic World'; bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        root=find_root(context)
        if root is None: return {'CANCELLED'}
        try:
            world=World.load(bpy.path.abspath(root.pw_settings.save_path)); s=root.pw_settings
            s.seed=str(world.settings.seed); s.year=world.settings.world_time; s.sea_level=world.settings.sea_level
            s.behavioral_policy=world.settings.behavioral_level
            text=_write_owned_text(root,'pw_constraints_text','constraints',[c.to_data() for c in world.constraints])
            s.constraints_text=text.name
            text=_write_owned_text(root,'pw_overrides_text','overrides',{k:asdict(v) for k,v in world.overrides.items()})
            s.overrides_text=text.name
            # Existing constraint objects must not be applied twice to a loaded world.
            for obj in context.scene.objects:
                if obj.get('pw_constraint_owner')==root['pw_root_id']:
                    obj['pw_constraint_owner']=''
            signature=digest(world.settings.seed,s.sea_level,s.behavioral_policy,[c.to_data() for c in world.constraints])
            root['pw_world_signature']=signature; _RUNTIME[root['pw_root_id']]=(signature,world)
            _write_owned_text(root,'pw_world_text','world',world_to_data(world))
            self.report({'INFO'},'World loaded; generate a snapshot to realize it'); return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class PW_OT_add_constraint(Operator):
    bl_idname='pw.add_constraint'; bl_label='Add Constraint'; bl_options={'REGISTER','UNDO'}
    kind: EnumProperty(items=[(v,v,'') for v in ('NoBuildArea','ProtectedArea','ParkConstraint','GrowthAttractor','GrowthRepulsor')])
    def execute(self,context):
        root=find_root(context)
        if root is None: return {'CANCELLED'}
        obj=bpy.data.objects.new(self.kind,None); obj.empty_display_type='CUBE'; obj.empty_display_size=50
        obj.location=context.scene.cursor.location; obj['pw_constraint_owner']=root['pw_root_id']
        obj['pw_constraint_id']=uuid.uuid4().hex; obj['pw_constraint_kind']=self.kind
        obj['pw_strength']=1.; obj['pw_falloff']=0.; obj['pw_active_from']=-1000000.; obj['pw_active_until']=0.
        context.scene.collection.objects.link(obj)
        for other in context.selected_objects: other.select_set(False)
        obj.select_set(True); context.view_layer.objects.active=obj
        self.report({'INFO'},'Move/scale this constraint; regenerate after editing'); return {'FINISHED'}


class PW_OT_inspect(Operator):
    bl_idname='pw.inspect'; bl_label='Inspect Semantic Node'
    node_id: StringProperty(default='')
    def execute(self,context):
        root=find_root(context)
        if root is None: return {'CANCELLED'}
        try:
            world,_=_world(root,context)
            graph=_SNAPSHOTS[root['pw_root_id']].graph if root['pw_root_id'] in _SNAPSHOTS else world.graph(root.pw_settings.year)
            node_id=self.node_id or root.pw_settings.inspect_id
            obj=context.active_object
            if not self.node_id and obj and obj.get('pw_semantic_ids'):
                ids=json.loads(obj['pw_semantic_ids']); index=0
                if obj.type=='MESH':
                    obj.update_from_editmode(); attr=obj.data.attributes.get('pw_semantic_index')
                    if attr:
                        if attr.domain=='FACE':
                            selected=next((p.index for p in obj.data.polygons if p.select),0)
                            if len(attr.data): index=attr.data[selected].value
                        elif attr.domain=='POINT':
                            index=next((v.index for v in obj.data.vertices if v.select),0)
                if ids: node_id=ids[min(index,len(ids)-1)]
            if node_id not in graph.nodes: raise ValueError('Enter a materialized semantic ID or select a generated face/instance point')
            root.pw_settings.inspect_id=node_id; node=graph[node_id]
            payload={'node':node.to_data(),'events':[e.to_data() for e in world.events.for_target(node_id)]}
            _write_owned_text(root,'pw_inspection_text','inspection',payload)
            root['pw_inspection_summary']=json.dumps({'type':node.type_id,'created_at':node.created_at,
                'destroyed_at':node.destroyed_at,'seed':str(node.seed),'parent_ids':node.parent_ids,'child_ids':node.child_ids,
                'refinement':node.refinement_state.to_data()})
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class PW_OT_set_override(Operator):
    bl_idname='pw.set_override'; bl_label='Set Node Override'
    mode: EnumProperty(items=[(v,v,'') for v in ('AUTO','NEVER','DETAILED')])
    def execute(self,context):
        root=find_root(context)
        if root is None or not root.pw_settings.inspect_id: return {'CANCELLED'}
        try:
            world,_=_world(root,context); nid=root.pw_settings.inspect_id
            if self.mode=='AUTO': world.overrides.pop(nid,None)
            elif self.mode=='NEVER': world.overrides[nid]=NodeOverride(never_refine=True)
            else: world.overrides[nid]=NodeOverride(always_refine=True,minimum={'structural':1,'geometric':2})
            text=_write_owned_text(root,'pw_overrides_text','overrides',{k:asdict(v) for k,v in world.overrides.items()})
            root.pw_settings.overrides_text=text.name
            self.report({'INFO'},'Override stored; numerical budgets still apply'); return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class PW_PT_main(Panel):
    bl_label='Procedural World'; bl_idname='PW_PT_main'; bl_space_type='VIEW_3D'; bl_region_type='UI'; bl_category='World Gen'
    def draw(self,context):
        layout=self.layout; layout.operator('pw.add_root',icon='WORLD')
        layout.prop(context.scene,'pw_active_root',text='Active Root')
        root=find_root(context)
        if root is None: return
        s=root.pw_settings; layout.label(text=root.name)
        row=layout.row(align=True); row.prop(s,'seed'); row.prop(s,'year')
        layout.prop(s,'quality'); layout.prop(s,'camera'); layout.prop(s,'radius'); layout.prop(s,'halo')
        layout.prop(s,'follow_camera')
        if not s.follow_camera:
            row=layout.row(align=True); row.prop(s,'center_x'); row.prop(s,'center_y')
        box=layout.box(); box.label(text='Independent Refinement Axes')
        for p in ('structural','geometric','temporal','behavioral'): box.prop(s,p)
        box.prop(s,'include_interiors'); layout.prop(s,'use_instances'); layout.prop(s,'debug')
        layout.operator('pw.generate',icon='FILE_REFRESH')
        if root.get('pw_summary'): layout.label(text=root['pw_summary'])
        box=layout.box(); box.label(text='Artistic Constraints')
        box.operator_menu_enum('pw.add_constraint','kind')
        obj=context.active_object
        if obj and obj.get('pw_constraint_owner')==root['pw_root_id']:
            box.label(text=obj.get('pw_constraint_kind','Constraint'))
            for key in ('pw_strength','pw_falloff','pw_active_from','pw_active_until'): box.prop(obj,f'["{key}"]')
        box.prop(s,'constraints_text'); box.prop(s,'overrides_text')
        box.prop(s,'sea_level'); box.prop(s,'behavioral_policy')
        box=layout.box(); box.label(text='Persistence'); box.prop(s,'embed_world'); box.prop(s,'save_path')
        row=box.row(align=True); row.operator('pw.save_world'); row.operator('pw.load_world')


class PW_PT_inspector(Panel):
    bl_label='Semantic Inspector'; bl_idname='PW_PT_inspector'; bl_space_type='VIEW_3D'; bl_region_type='UI'; bl_category='World Gen'
    def draw(self,context):
        root=find_root(context)
        if root is None: return
        layout=self.layout; layout.prop(root.pw_settings,'inspect_id'); layout.operator('pw.inspect')
        raw=root.get('pw_inspection_summary')
        if not raw: return
        data=json.loads(raw)
        layout.label(text=f'Type: {data["type"]}'); layout.label(text=f'Created: {data["created_at"]:.1f}')
        layout.label(text=f'Destroyed: {data["destroyed_at"]}'); layout.label(text=f'Seed: {data["seed"]}')
        layout.label(text='Refinement: '+str(data['refinement']))
        for pid in data['parent_ids'][:3]: layout.operator('pw.inspect',text='Parent: '+pid[:24]).node_id=pid
        for cid in data['child_ids'][:6]: layout.operator('pw.inspect',text='Child: '+cid[:24]).node_id=cid
        if len(data['child_ids'])>6: layout.label(text=f'+ {len(data["child_ids"])-6} more in inspection JSON')
        row=layout.row(align=True)
        for mode in ('AUTO','NEVER','DETAILED'): row.operator('pw.set_override',text=mode.title()).mode=mode
        layout.label(text='Full state, constraints, and events:')
        layout.label(text=root.get('pw_inspection_text',''))


_CLASSES=(PWSettings,PW_OT_add_root,PW_OT_generate,PW_OT_save_world,PW_OT_load_world,
          PW_OT_add_constraint,PW_OT_inspect,PW_OT_set_override,PW_PT_main,PW_PT_inspector)


def register():
    for cls in _CLASSES: bpy.utils.register_class(cls)
    bpy.types.Object.pw_settings=PointerProperty(type=PWSettings)
    bpy.types.Scene.pw_active_root=PointerProperty(type=bpy.types.Object,poll=_root_poll)


def unregister():
    _RUNTIME.clear(); _SNAPSHOTS.clear()
    if hasattr(bpy.types.Scene,'pw_active_root'): del bpy.types.Scene.pw_active_root
    if hasattr(bpy.types.Object,'pw_settings'): del bpy.types.Object.pw_settings
    for cls in reversed(_CLASSES): bpy.utils.unregister_class(cls)
