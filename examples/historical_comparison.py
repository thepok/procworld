"""The same seed and camera, four historical snapshots, stable parcel identities."""
from pathlib import Path
import sys
from dataclasses import replace
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from procedural_world import World,Budget,RefinementState,Camera
from procedural_world.representation.export import export_obj,export_svg


def main():
    world=World(); camera=Camera((650,-900,650),(0,0,40)); out=Path('history_output')
    out.mkdir(exist_ok=True)
    for year in (1780,1850,1930,2025):
        snapshot=world.snapshot(time=year,camera=camera,radius=350,halo=1,
            budget=replace(Budget.preset('PREVIEW'),max_refinements=80),request=RefinementState(0,2,1,0))
        export_obj(snapshot.scene,out/f'world_{year}.obj'); export_svg(snapshot,out/f'map_{year}.svg')
        print(year, snapshot.report['active_nodes'],snapshot.fingerprint())
    world.save(out/'shared_world.json')


if __name__=='__main__': main()
