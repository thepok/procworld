"""Deterministic architectural profiles derived from semantic building facts.

The profile is deliberately backend-neutral.  It describes architectural intent
that geometry providers may realize at different levels of detail without making
meshes authoritative world state.
"""
from __future__ import annotations
from ..core.seed import RandomStream


def era_for(year: float) -> str:
    if year < 1780:
        return 'preindustrial'
    if year < 1880:
        return 'industrializing'
    if year < 1919:
        return 'historicist'
    if year < 1946:
        return 'interwar'
    if year < 1980:
        return 'postwar'
    if year < 2005:
        return 'late_modern'
    return 'contemporary'


def _material_palette(era: str, usage: str) -> tuple[str, ...]:
    if usage == 'industrial':
        return ('brick', 'concrete', 'metal') if era in {'historicist', 'industrializing'} else ('concrete', 'metal')
    if usage == 'commercial':
        if era in {'late_modern', 'contemporary'}:
            return ('glass', 'stone', 'concrete')
        return ('stone', 'brick', 'stucco')
    if era in {'preindustrial', 'industrializing', 'historicist'}:
        return ('brick', 'stucco', 'stone')
    if era in {'interwar', 'postwar'}:
        return ('stucco', 'brick', 'concrete')
    return ('stucco', 'brick', 'concrete', 'stone')


def architectural_profile(usage: str, construction_time: float, style_seed: int,
                          floor_count: int, width: float, depth: float) -> dict:
    """Return deterministic architectural intent for a building.

    Named random draws keep facade choices isolated from unrelated generators.
    The returned mapping is JSON-serializable and suitable for semantic state.
    """
    usage = usage if usage in {'residential', 'commercial', 'industrial'} else 'residential'
    era = era_for(construction_time)
    rng = RandomStream(style_seed, 'architecture')
    aspect = max(width, depth) / max(.01, min(width, depth))

    if usage == 'industrial':
        archetype = 'industrial_hall' if floor_count <= 2 else 'industrial_loft'
        roof_type = rng.choice(('gable', 'shed', 'flat'), 'roof')
        ground_floor = 'loading'
    elif usage == 'commercial':
        if era in {'preindustrial', 'industrializing', 'historicist'}:
            archetype = 'merchant_block'
            roof_type = rng.choice(('gable', 'hip'), 'roof')
        elif era in {'interwar', 'postwar'}:
            archetype = 'office_block'
            roof_type = 'flat'
        else:
            archetype = 'commercial_slab' if floor_count >= 6 else 'mixed_use_block'
            roof_type = 'flat'
        ground_floor = 'storefront'
    else:
        if floor_count <= 2 and era in {'preindustrial', 'industrializing'}:
            archetype = 'urban_house'
            roof_type = rng.choice(('gable', 'hip'), 'roof')
        elif era in {'historicist', 'interwar'}:
            archetype = 'perimeter_apartment'
            roof_type = rng.choice(('gable', 'hip'), 'roof')
        elif era == 'postwar':
            archetype = 'residential_slab'
            roof_type = 'flat'
        else:
            archetype = 'apartment_block'
            roof_type = rng.choice(('flat', 'gable'), 'roof') if floor_count < 5 else 'flat'
        ground_floor = 'residential_entry'

    material = rng.choice(_material_palette(era, usage), 'facade_material')
    regularity = .78 + rng.uniform(-.08, .12, 'regularity')
    window_width = rng.uniform(1.05, 1.55, 'window_width')
    window_height = rng.uniform(1.25, 1.75, 'window_height')
    if usage == 'industrial':
        window_width *= 1.35
        window_height *= 1.25
    if usage == 'commercial':
        window_width *= 1.12

    balcony_rate = 0.
    if usage == 'residential' and floor_count >= 2 and era not in {'preindustrial', 'industrializing'}:
        balcony_rate = rng.uniform(.22, .58, 'balcony_rate')

    has_elevator = floor_count >= (4 if construction_time >= 1960 else 6)
    if construction_time < 1890:
        has_elevator = False

    return {
        'style_era': era,
        'archetype': archetype,
        'roof_type': roof_type,
        'facade_material': material,
        'ground_floor_mode': ground_floor,
        'window_regularity': round(regularity, 6),
        'window_width': round(window_width, 6),
        'window_height': round(window_height, 6),
        'balcony_rate': round(balcony_rate, 6),
        'has_elevator': bool(has_elevator),
        'entrance_width': round(rng.uniform(1.35, 2.25, 'entrance_width'), 6),
        'cornice_depth': round(rng.uniform(.12, .38, 'cornice_depth') if era in {'industrializing','historicist','interwar'} else .08, 6),
        'plinth_height': round(rng.uniform(.25, .65, 'plinth_height'), 6),
        'facade_bay_target': round(rng.uniform(3.1, 4.6, 'facade_bay_target'), 6),
        'aspect_ratio': round(aspect, 6),
    }


def profile_from_state(state: dict, width: float, depth: float) -> dict:
    """Read committed profile facts, deriving defaults for legacy worlds."""
    seed = int(state.get('style_seed', 0))
    derived = architectural_profile(state.get('usage', 'residential'),
                                    float(state.get('construction_time', 2000.)), seed,
                                    int(state.get('floor_count', 1)), width, depth)
    for key in tuple(derived):
        if key in state:
            derived[key] = state[key]
    return derived
