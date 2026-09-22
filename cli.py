"""Command-line entry point; only the Python standard library is required."""
from __future__ import annotations
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
from . import World,WorldSettings,RefinementState,Budget,Camera,__version__
from .core.constraints import InfluenceField
from .refinement.overrides import NodeOverride
from .representation.export import export_obj,export_svg,export_snapshot


def _parser():
    parser=argparse.ArgumentParser(prog='worldgen',description='Deterministic hierarchical procedural worlds')
    parser.add_argument('--version',action='version',version=__version__)
    sub=parser.add_subparsers(dest='command',required=True)
    g=sub.add_parser('generate',help='Generate a snapshot, semantic world JSON, OBJ, and SVG debug map')
    g.add_argument('--seed',type=int,default=12); g.add_argument('--year',type=float,default=2025)
    g.add_argument('--out',type=Path,default=Path('world_output'))
    g.add_argument('--world',type=Path,help='Load an existing serialized world instead of creating one')
    g.add_argument('--center',nargs=2,type=float,default=(0.,0.),metavar=('X','Y'))
    g.add_argument('--radius',type=float,default=600.); g.add_argument('--halo',type=float,default=2.)
    g.add_argument('--quality',choices=('PREVIEW','DRAFT','HIGH','FINAL'),default='PREVIEW')
    g.add_argument('--structure',type=int,choices=range(4),default=1)
    g.add_argument('--geometry',type=int,choices=range(4),default=2)
    g.add_argument('--temporal',type=int,choices=range(2),default=0)
    g.add_argument('--behavior',type=int,choices=range(2),default=0)
    g.add_argument('--interiors',action='store_true',help='Use a cutaway and realize available interior proxies')
    g.add_argument('--camera',nargs=6,type=float,metavar=('X','Y','Z','TX','TY','TZ'))
    g.add_argument('--constraints',type=Path,help='JSON array of InfluenceField records')
    g.add_argument('--overrides',type=Path,help='JSON object mapping node IDs to NodeOverride settings')
    g.add_argument('--geometry-json',action='store_true',help='Also export the full backend-neutral geometry JSON')
    g.add_argument('--no-obj',action='store_true'); g.add_argument('--no-svg',action='store_true')
    for flag in ('max-nodes','max-instances','max-triangles','max-refinements'):
        g.add_argument('--'+flag,type=int)
    g.add_argument('--max-seconds',type=float,help='Cooperative wall-time cutoff; makes the selected detail timing-dependent')
    i=sub.add_parser('inspect',help='Inspect a saved semantic node and its source history')
    i.add_argument('--world',type=Path,required=True); i.add_argument('--id',required=True); i.add_argument('--year',type=float)
    v=sub.add_parser('validate',help='Validate and summarize a serialized world')
    v.add_argument('world',type=Path)
    return parser


def main(argv=None):
    parser=_parser(); args=parser.parse_args(argv)
    try:
        if args.command=='generate':
            if args.world and args.constraints:
                raise ValueError('Constraints are immutable world inputs; do not override them when loading a world')
            if args.world:
                world=World.load(args.world)
            else:
                constraints=()
                if args.constraints:
                    constraints=tuple(InfluenceField.from_data(c) for c in json.loads(args.constraints.read_text()))
                world=World(WorldSettings(seed=args.seed,world_time=args.year),constraints=constraints)
            budget=Budget.preset(args.quality)
            changes={key:getattr(args,key) for key in ('max_nodes','max_instances','max_triangles','max_refinements')
                     if getattr(args,key) is not None}
            if args.max_seconds is not None: changes['max_generation_time']=args.max_seconds
            budget=replace(budget,**changes)
            overrides={}
            if args.overrides:
                overrides={k:NodeOverride(**v) for k,v in json.loads(args.overrides.read_text()).items()}
                world.overrides.update(overrides)
            camera=Camera(tuple(args.camera[:3]),tuple(args.camera[3:])) if args.camera else None
            snapshot=world.snapshot(time=args.year,center=tuple(args.center),radius=args.radius,halo=args.halo,budget=budget,
                request=RefinementState(args.structure,args.geometry,args.temporal,args.behavior),camera=camera,
                overrides=overrides,include_interiors=args.interiors)
            args.out.mkdir(parents=True,exist_ok=True)
            world.save(args.out/'world.json')
            if not args.no_obj: export_obj(snapshot.scene,args.out/'world.obj')
            if not args.no_svg: export_svg(snapshot,args.out/'map.svg')
            data=snapshot.to_data(include_geometry=False)
            (args.out/'snapshot.json').write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False),encoding='utf8')
            if args.geometry_json: export_snapshot(snapshot,args.out/'geometry.json')
            summary={'output':str(args.out.resolve()),'snapshot_fingerprint':snapshot.fingerprint(),
                     'nodes':len(snapshot.graph),'active_nodes':snapshot.report['active_nodes'],
                     'represented_nodes':len(snapshot.scene.bundles),'triangles':snapshot.scene.cost().triangles,
                     'refinements':snapshot.report['budget']['refinements'],
                     'refinement_errors':len(snapshot.report['scheduler']['errors']),
                     'omitted_representations':len(snapshot.report['omitted_representations'])}
            print(json.dumps(summary,indent=2)); return 0
        world=World.load(args.world)
        if args.command=='inspect':
            year=world.settings.world_time if args.year is None else args.year
            graph=world.graph(year)
            if args.id not in graph.nodes: raise ValueError(f'Node not materialized: {args.id}')
            print(json.dumps({'node':graph[args.id].to_data(),'active':graph.is_active(args.id,year),
                              'history':[e.to_data() for e in world.events.for_target(args.id)]},indent=2)); return 0
        graph=world.graph()
        print(json.dumps({'valid':True,'nodes':len(graph),'events':len(world.events.events),
                          'regions':len(world.regions),'semantic_fingerprint':graph.fingerprint()},indent=2)); return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f'worldgen: {exc}',file=sys.stderr); return 2


if __name__=='__main__':
    raise SystemExit(main())
