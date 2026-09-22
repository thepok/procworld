"""Hierarchical Procedural World — pure Python core with an optional Blender adapter."""
__version__='1.0.0'
bl_info={
    'name':'Hierarchical Procedural World',
    'author':'Procedural World contributors',
    'version':(1,0,0),
    'blender':(4,2,0),
    'location':'3D Viewport > Sidebar > World Gen',
    'description':'Deterministic historical worlds, independent refinement axes, terrain and settlements',
    'category':'Object',
}
from .world.world import World
from .world.config import WorldSettings
from .core.node import Thing,Process,ProceduralNode,Dimension,RefinementState
from .refinement.budget import Budget
from .representation.camera import Camera


def register():
    from .blender.addon import register as register_addon
    register_addon()


def unregister():
    from .blender.addon import unregister as unregister_addon
    unregister_addon()


__all__=['World','WorldSettings','Thing','Process','ProceduralNode','Dimension','RefinementState','Budget','Camera']
