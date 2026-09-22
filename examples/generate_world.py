"""Run from any directory: python /path/to/procedural_world/examples/generate_world.py."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from procedural_world import World,WorldSettings,Budget,RefinementState
from procedural_world.representation.export import export_obj,export_svg


def main():
    world=World(WorldSettings(seed=12,world_time=2025))
    snapshot=world.snapshot(radius=350,halo=1,budget=Budget.preset('DRAFT'),request=RefinementState(1,2,1,1))
    out=Path('example_world'); out.mkdir(exist_ok=True)
    export_obj(snapshot.scene,out/'scene.obj'); export_svg(snapshot,out/'map.svg'); world.save(out/'world.json')
    print(f'Created {len(snapshot.scene.bundles)} representations in {out.resolve()}')
    print(snapshot.report['budget'])


if __name__=='__main__': main()
