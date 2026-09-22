# Building System

The building subsystem turns a committed parcel-level building into progressively richer architectural structure and geometry without changing its identity, footprint, lifetime, or other committed facts.

## Semantic building state

A building is created by `buildings.lifecycle.building_for_parcel`. The lifecycle generator commits the coarse facts that later detail must respect: footprint, total height, floor count, use, construction time, floor area, architectural archetype, and roof type.

Architecture is deterministic. `buildings.archetypes.architectural_profile` derives a style profile from the building's use, construction year, style seed, storey count, and proportions. The profile includes:

- architectural era and archetype;
- roof form;
- facade material intent;
- facade bay and window proportions;
- ground-floor treatment;
- balcony propensity;
- entrance width, cornice, and plinth dimensions;
- whether the building has an elevator.

These are semantic facts. Geometry reads them; geometry does not invent a second building definition.

## Geometric refinement

`BuildingProvider` exposes four progressive exterior refinements above the fallback block:

| Level | Representation |
| --- | --- |
| 0 | committed building envelope block |
| 1 | massing plus roof form |
| 2 | deterministic windows, entrances, and commercial storefront treatment |
| 3 | facade articulation: plinth, cornice, floor bands, window trim, and selected balconies |
| 4 | rooftop detail such as parapets, chimneys, and mechanical equipment |

The levels are additive. A more detailed realization preserves the same semantic building and does not modify historical state.

The current roof implementations support flat, gable, hip, and shed forms. Facade rhythm is driven by a target bay width instead of hard-coded window counts, allowing differently sized buildings to retain plausible proportions.

## Structural refinement

Structural refinement is independent from exterior geometric detail.

### Building -> floors

`BuildingFloorsRefiner` materializes one `Floor` semantic node per committed storey. Every floor remains inside the committed building volume and inherits use and archetype context.

### Building -> vertical core

`BuildingCoreRefiner` adds a persistent `Stairwell` and, where the semantic building profile requires one, an `ElevatorShaft`. These volumes span the building and are constrained by its envelope.

The core is generated after floor materialization and advances the building structural refinement from level 1 to level 2.

### Floor -> rooms and circulation

`FloorRoomsRefiner` produces a corridor plus rooms. Room program depends on building use:

- residential: living, bedroom, kitchen, bathroom;
- commercial: retail/office, office, meeting, service;
- industrial: production, storage, service.

The initial layout remains intentionally simple and rectangular. It is a semantic scaffold for later plan solvers, not a claim of architectural realism.

### Room -> furniture proxies

`RoomFurnitureRefiner` places deterministic proxy objects appropriate to the room's program. Bedrooms receive beds and wardrobes; offices receive desks; industrial rooms receive machines or racks; and so on. These remain `FurnitureProxy` nodes so a future furniture system can replace their representation without changing the room or building.

## Interior visualization

When `include_interiors=True`, the building exterior switches to a simple cutaway and structural children become renderable. `BuildingCoreProvider` can then refine stairwells from a core proxy into explicit stair-step geometry. Elevator shafts remain lightweight but gain floor door markers at higher detail.

## Extension points

The current system is intentionally a scaffold. Useful next refinements can be added without replacing the lifecycle model:

- polygonal/non-rectangular footprints;
- facade-side semantic nodes and facade grammar modules;
- apartment/unit subdivision between floors and rooms;
- doors and connectivity graphs;
- stair flights that satisfy exact building-code constraints;
- roof dormers and more roof families;
- historical facade renovations;
- structural grids and columns;
- material aging and damage;
- detailed windows, frames, balconies, railings, and shop fronts;
- apartment and office layout optimization;
- visibility-aware interior generation.

Any such extension should preserve the core invariant: new detail may resolve an existing building more precisely, but must not contradict its committed higher-level state.
