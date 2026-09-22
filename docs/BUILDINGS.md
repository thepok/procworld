# Building subsystem

The building system treats a building as a persistent semantic object whose geometry can be refined without changing its identity or historical commitments.

## Footprints are polygons, not boxes

A building's authoritative footprint is stored as a polygon and its spatial domain is a `PrismDomain`: an `AreaDomain` extruded between two Z elevations. The axis-aligned bounds are only an acceleration and fallback envelope.

The built-in lifecycle generator can currently produce deterministic:

- rectangles
- L-shaped footprints
- T-shaped footprints
- U-shaped / open-courtyard footprints
- stepped footprints
- chamfered footprints
- parcel-fill polygons for authored irregular parcels when no useful inscribed rectangle is available

Manually authored buildings are not restricted to these templates. Any valid simple polygon can be used as the footprint of a `PrismDomain`.

## Semantic state

Generated buildings commit facts such as:

- polygon footprint and footprint area
- footprint family
- construction time
- use
- height and floor count
- storey height
- archetype
- roof form
- facade material and bay spacing
- deterministic style seed

These facts exist independently of the Blender or mesh representation.

## Structural refinement

Structural refinement preserves the real footprint:

```text
Building prism
├── Floor prisms using the same polygon
├── Vertical circulation core
└── Floor
    ├── Corridor
    └── Rooms
        └── FurnitureProxy
```

The inexpensive room planner subdivides the floor's bounding region into candidate cells, but only commits cells fully contained by the floor polygon. It therefore cannot create a room in the missing corner of an L-shaped building or across the void of a U-shaped building.

This room planner is intentionally simple. A later architectural solver can replace it while retaining the same building/floor commitments.

## Geometric refinement

Building geometry follows the semantic polygon at every level:

- coarse massing: direct polygon extrusion
- shell: polygon extrusion plus roof
- facade: windows and doors distributed along actual polygon edges
- interiors: polygon floor slabs, room/corridor boundaries and a vertical core

Rectangular buildings may receive a simple gable roof. Irregular footprints currently fall back to a footprint-following roof cap rather than inventing unsupported compound roof topology.

## Extension direction

Useful next refinements include footprint orientation from road frontage, party walls, setbacks from individual parcel edges, wings and courtyards with holes, facade grammar by edge, structural grids, stair/elevator connectivity, apartment/unit subdivision and roof graphs for compound footprints.

The key invariant is that these improvements must refine the committed polygonal building rather than replacing it with a contradictory shape.
