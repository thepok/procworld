"""Deterministic building birth/renovation/replacement schedules."""
from ..core.node import Thing
from ..core.domain import AreaDomain,PrismDomain
from ..core.constraints import Commitment
from ..core.event import Event,create_event
from ..core.seed import RandomStream,derive_seed,stable_id
from .footprint import footprint_for_parcel,polygon_centroid
from .archetypes import choose_archetype


def building_for_parcel(parcel,generation,birth,environment):
    rng=RandomStream(parcel.seed,'building',generation)
    usage=parcel.semantic_state['land_use']
    footprint_kind,xy,setback=footprint_for_parcel(parcel,rng,usage,birth)
    cx,cy=polygon_centroid(xy)
    samples=xy+((cx,cy),)
    base=max(environment.height(px,py) for px,py in samples)+.2
    area=AreaDomain(tuple((px,py,base) for px,py in xy))
    floors=rng.integer(1,3,'floors')+max(0,int((birth-1850)//75))
    if usage=='commercial': floors+=2
    if usage=='industrial': floors=min(3,floors)
    floors=min(12,floors)
    storey=3.2 if usage!='industrial' else rng.uniform(3.6,5.2,'industrial_storey')
    archetype,style=choose_archetype(usage,birth,rng)
    roof=0.35 if style['roof_form']=='flat' else rng.uniform(1.2,2.4,'roof_height')
    height=floors*storey+roof
    footprint_area=area.area
    state={
        'footprint':[[float(x),float(y)] for x,y in xy],
        'footprint_kind':footprint_kind,
        'footprint_area':footprint_area,
        'setback':setback,
        'height':height,
        'floor_count':floors,
        'storey_height':storey,
        'roof_height':roof,
        'usage':usage,
        'archetype':archetype,
        **style,
        'construction_time':birth,
        'condition':1.,
        'last_renovation':birth,
        'condition_decay':.006,
        'style_seed':derive_seed(parcel.seed,'style',generation),
        'floor_area':footprint_area*floors,
        'generation':generation,
    }
    commitments=tuple(Commitment(k,state[k]) for k in (
        'footprint','footprint_kind','footprint_area','height','floor_count','usage','construction_time','floor_area'))
    return Thing(stable_id(parcel.id,'Building',generation),'Building',derive_seed(parcel.seed,'building',generation),
                 PrismDomain(area,base,base+height),state,(parcel.id,),created_at=birth,
                 commitments=commitments,provenance={'generator':'building.lifecycle','version':'2.0.0'})


def lifecycle_events(parcel,first_birth,context,process_id,expansion_id=None):
    events=[]; birth=first_birth; generation=0; end=context.current_time
    while birth<=end:
        if any(c.blocks(parcel.domain,birth) for c in context.parent_constraints): break
        building=building_for_parcel(parcel,generation,birth,context.environment)
        parent=expansion_id if generation==0 else None
        event=create_event(building,'ConstructBuilding',process_id,30,parent)
        if generation==0:
            event=Event(**{**event.to_data(),'payload':{**event.payload,'floor_area_added':building.semantic_state['floor_area']}})
        events.append(event)
        rng=RandomStream(parcel.seed,'lifecycle',generation)
        death=birth+rng.uniform(80,125,'lifespan')
        renovation=birth+rng.uniform(28,40,'renovation')
        if renovation<=end:
            events.append(Event(stable_id(building.id,'Event','renovate'),'RenovateBuilding',renovation,building.id,
                                {'facts':{'condition':1.,'last_renovation':renovation}},process_id,priority=40))
        protected=any(c.kind=='ProtectedArea' and c.active(death) and
                      c.domain.bounds.intersects(parcel.domain.bounds,True) for c in context.parent_constraints)
        if protected: break
        if death<=end:
            events.append(Event(stable_id(building.id,'Event','demolish'),'DemolishBuilding',death,building.id,
                                {},process_id,priority=45))
        birth=death+rng.uniform(2,5,'replacement_delay'); generation+=1
        if generation>32: raise RuntimeError('Lifecycle safety bound exceeded')
    return events


def condition_at(node,time):
    return max(.05,min(1.,node.semantic_state.get('condition',1.)-
        max(0,time-node.semantic_state.get('last_renovation',node.created_at))*node.semantic_state.get('condition_decay',.006)))
