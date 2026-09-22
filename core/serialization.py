"""Versioned JSON persistence, atomic file replacement, no executable pickle data."""
from __future__ import annotations
from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
import warnings
from .event import EventLog
from .graph import SemanticGraph
from .constraints import InfluenceField
from .seed import canonical,digest

SCHEMA_VERSION=1


def world_to_data(world):
    payload={'schema_version':SCHEMA_VERSION,'settings':asdict(world.settings),
             'constraints':[c.to_data() for c in world.constraints],
             'generator_versions':dict(sorted(world.registry.versions.items())),
             'base_graph':world.base.to_data(),'event_log':world.events.to_data(),
             'regions':world.regions,'refinement_records':world.refinement_records,
             'overrides':{k:asdict(v) for k,v in sorted(world.overrides.items())}}
    payload['content_hash']=digest(payload)
    return payload


def save_world(world,path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    data=world_to_data(world)
    fd,temp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf8') as f:
            json.dump(data,f,sort_keys=True,indent=2,allow_nan=False)
            f.flush(); os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp): os.unlink(temp)
    return path


def world_from_data(data,registry=None,strict_versions=True,vegetation_adapter=None):
    from ..world.world import World
    from ..world.config import WorldSettings
    from ..refinement.overrides import NodeOverride
    data=dict(data)
    if data.get('schema_version')!=SCHEMA_VERSION: raise ValueError('Unsupported world schema version')
    expected=data.pop('content_hash',None)
    if expected is None or digest(data)!=expected: raise ValueError('World content hash mismatch')
    world=World(WorldSettings(**data['settings']),constraints=tuple(InfluenceField.from_data(c) for c in data['constraints']),
                registry=registry,vegetation_adapter=vegetation_adapter)
    saved=data['generator_versions']; current=world.registry.versions
    mismatches={k:(v,current.get(k)) for k,v in saved.items() if current.get(k)!=v}
    if mismatches:
        message=f'Generator version mismatch: {mismatches}'
        if strict_versions: raise ValueError(message)
        warnings.warn(message+'; reproducibility is not guaranteed',RuntimeWarning)
    world.base=SemanticGraph.from_data(data['base_graph'])
    if world.id not in world.base.nodes: raise ValueError('World root identity does not match settings')
    world.events=EventLog.from_data(data['event_log'])
    world.regions=data['regions']; world.refinement_records=data['refinement_records']
    world.overrides={k:NodeOverride(**v) for k,v in data.get('overrides',{}).items()}
    for record in world.regions.values():
        if any(eid not in world.events.events for eid in record['events']+record['coarse_events']):
            raise ValueError('Region references an absent event')
    # Validate semantic history and stored refinement constraints once on load.
    world.graph(max((r['until'] for r in world.regions.values()),default=world.settings.world_time))
    return world


def load_world(path,**kwargs):
    with Path(path).open('r',encoding='utf8') as f:
        data=json.load(f,parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f'Invalid JSON number {x}')))
    return world_from_data(data,**kwargs)
