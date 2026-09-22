"""Deterministic building birth/renovation/replacement schedules."""
from ..core.node import Thing
from ..core.domain import VolumeDomain,Bounds
from ..core.constraints import Commitment
from ..core.event import Event,create_event
from ..core.seed import RandomStream,derive_seed,stable_id
from .archetypes import architectural_profile


def building_for_parcel(parcel,generation,birth,environment):
    rng=RandomStream(parcel.seed,'building',generation)
    b=parcel.domain.bounds; x,y=b.minimum[:2]; w,h=b.size[:2]
    inset=rng.uniform(2.5,5.0,'setback')
    # Keep a valid envelope even for manually authored small parcels.
    inset=min(inset,max(.5,min(w,h)*.28))
    x0,y0,x1,y1=x+inset,y+inset,x+w-inset,y+h-inset
    base=max(environment.height(px,py) for px in (x0,(x0+x1)/2,x1) for py in (y0,(y0+y1)/2,y1))+.2
    usage=parcel.semantic_state['land_use']
    floors=rng.integer(1,3,'floors')+max(0,int((birth-1850)//75))
    if usage=='commercial': floors+=2
    if usage=='industrial': floors=min(3,floors)
    floors=min(12,floors); storey=3.2
    style_seed=derive_seed(parcel.seed,'style',generation)
    profile=architectural_profile(usage,birth,style_seed,floors,x1-x0,y1-y0)
    roof={'flat':.55,'shed':1.15,'gable':1.8,'hip':1.65}.get(profile['roof_type'],1.2)
    height=floors*storey+roof
    floorplate=(x1-x0)*(y1-y0)
    state={'footprint':[x0,y0,x1,y1],'height':height,'floor_count':floors,'storey_height':storey,
           'roof_height':roof,'usage':usage,'construction_time':birth,'condition':1.,
           'last_renovation':birth,'condition_decay':.006,'style_seed':style_seed,
           'floor_area':floorplate*floors,'floorplate_area':floorplate,'generation':generation,
           'setback':inset,**profile}
    commitments=tuple(Commitment(k,state[k]) for k in
                      ('footprint','height','floor_count','usage','construction_time','floor_area','archetype','roof_type'))
    return Thing(stable_id(parcel.id,'Building',generation),'Building',derive_seed(parcel.seed,'building',generation),
                 VolumeDomain(Bounds((x0,y0,base),(x1,y1,base+height))),state,(parcel.id,),created_at=birth,
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
                                {'facts':{'condition':1.,'last_renovation':renovation,'renovated':True}},process_id,priority=40))
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
