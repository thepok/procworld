"""Small deterministic building archetype library.

Archetypes describe semantic tendencies. They never directly create geometry,
which keeps them replaceable by more sophisticated architectural generators.
"""
from __future__ import annotations


def choose_archetype(usage, birth, rng):
    if usage=='industrial':
        names=('workshop','warehouse','factory') if birth<1970 else ('warehouse','factory','logistics')
    elif usage=='commercial':
        names=('shop_house','office','civic') if birth<1945 else ('office','retail','mixed_commercial')
    else:
        if birth<1850: names=('townhouse','tenement','courtyard_house')
        elif birth<1945: names=('townhouse','tenement','apartment_block')
        elif birth<1990: names=('apartment_block','slab','tower_podium')
        else: names=('apartment_block','mixed_residential','terraced_block')
    name=rng.choice(names,'archetype')
    return name, style_for(name,birth,rng)


def style_for(name,birth,rng):
    historic=birth<1918
    midcentury=1945<=birth<1980
    if name in {'factory','warehouse','workshop','logistics'}:
        facade=rng.choice(('brick','concrete','metal'),'facade')
        roof=rng.choice(('flat','shed'),'roof')
        bay=rng.uniform(3.2,5.5,'bay')
    elif name in {'office','retail','mixed_commercial','tower_podium','civic'}:
        facade=rng.choice(('stone','stucco','glass','concrete'),'facade')
        roof='flat' if not historic else rng.choice(('gable','hip'),'roof')
        bay=rng.uniform(2.4,4.0,'bay')
    else:
        facade=rng.choice(('brick','stucco','stone') if historic else ('brick','stucco','concrete'),'facade')
        roof=rng.choice(('gable','hip','flat'),'roof') if not midcentury else rng.choice(('flat','gable'),'roof')
        bay=rng.uniform(2.5,3.8,'bay')
    return {
        'facade_material':facade,
        'roof_form':roof,
        'roof_material':'tile_roof' if roof in {'gable','hip'} and historic else ('metal' if roof=='shed' else 'roof'),
        'facade_bay':bay,
        'window_width':min(1.8,max(.8,bay*rng.uniform(.34,.52,'window_width'))),
        'window_height':rng.uniform(1.25,1.75,'window_height'),
    }


def room_program(usage):
    if usage=='commercial':
        return ('office','meeting','service','storage','reception')
    if usage=='industrial':
        return ('production','storage','service','office')
    return ('living','bedroom','kitchen','bathroom','study','storage')
