# Hierarchical Procedural World System

## 1. Objective

Create an extensible procedural world-generation framework capable of generating large, coherent, historically evolved static scenes.

The first major application is urban environments, but the framework must not be city-specific.

The system must support:

- terrain
- oceans, lakes and rivers
- settlements and cities
- roads and infrastructure
- districts
- parcels
- buildings
- interiors
- furniture
- vegetation
- procedural plants
- future procedural systems that do not yet exist

The fundamental architectural requirement is:

> Everything may initially exist only as a crude abstraction and may later be refined into increasingly detailed structure without invalidating the abstractions already generated.

The same principle applies to:

- spatial structure
- geometry
- historical development
- behavior and simulation rules

The framework should remain usable at every stage of development.

If only terrain and primitive building blocks exist, it should already generate complete scenes.

When better road generators, building systems, interiors, furniture, vegetation, economics or historical models are later implemented, existing worlds should be capable of being regenerated with the increased sophistication.

---

# 2. Fundamental Concept

The system represents the world as a recursively refinable graph.

The conceptual root is:

```text
ProceduralNode

```

Two fundamental categories specialize it:

```text
ProceduralNode
├── Thing
└── Process

```

A `Thing` describes something that exists.

Examples:

```text
World
Terrain
Ocean
River
Settlement
City
District
Road
Block
Parcel
Building
Floor
Room
Furniture
Park
Forest
Tree
Plant

```

A `Process` describes how Things change over time.

Examples:

```text
TerrainEvolution
SettlementGrowth
RoadDevelopment
ParcelSubdivision
BuildingLifecycle
Demolition
Construction
UrbanExpansion
VegetationSuccession
PlantGrowth

```

Both Things and Processes must themselves be refinable.

---

# 3. Central Design Principle

No subsystem may require all lower-level subsystems to exist.

For example:

Version 1:

```text
Building
→ rectangular box

```

Later:

```text
Building
→ exterior shell
→ floors

```

Later:

```text
Building
→ floors
→ rooms

```

Later:

```text
Room
→ furniture proxy boxes

```

Later:

```text
Room
→ real furniture generator

```

The existence of the later systems must not require rewriting the earlier architecture.

Every procedural object therefore needs a valid fallback representation.

---

# 4. Structural Refinement vs Specialization

These concepts must remain separate.

## Specialization

Specialization determines what something is.

Example:

```text
Thing
→ Structure
→ Building
→ ResidentialBuilding
→ ApartmentBuilding

```

This is semantic specialization.

## Refinement

Refinement determines what something consists of.

Example:

```text
ApartmentBuilding
→ floors
→ apartments
→ rooms
→ furniture

```

A Thing can become semantically specialized without exposing its internal structure.

A Thing can also expose more internal structure without changing its semantic identity.

---

# 5. Four Independent Refinement Dimensions

Do not represent detail using one universal LOD number.

Each node has at least four independent refinement dimensions.

## 5.1 Structural Refinement

How deeply has the internal composition been generated?

Example:

```text
Building
→ Floors
→ Rooms
→ Furniture

```

## 5.2 Geometric Refinement

How accurate is the visual representation?

Example:

```text
Bounding box
→ Massing mesh
→ Exterior shell
→ Facade
→ Windows
→ Detailed architecture

```

## 5.3 Temporal Refinement

How detailed is the object's history?

Example:

```text
Building existed in 1950

```

becomes:

```text
constructed 1921
renovated 1964
extended 1982
roof replaced 2007

```

## 5.4 Behavioral Refinement

How sophisticated are the rules governing change?

Example:

```text
random demolition

```

becomes:

```text
age-dependent demolition

```

then:

```text
condition + land value + demand + regulations

```

These four dimensions must remain independently controllable.

---

# 6. The World Is Conceptually Unbounded

Do not treat the generated scene boundary as the boundary of the world.

The world exists conceptually over unlimited coordinates.

Only the required portion is instantiated.

Large-scale world properties should be deterministic functions of absolute world coordinates.

Conceptually:

```text
elevation(seed, x, y)
geology(seed, x, y)
temperature(seed, x, y)
moisture(seed, x, y)
water_table(seed, x, y)
biome(seed, x, y)
fertility(seed, x, y)
settlement_suitability(seed, x, y)

```

This means that generating a 10 km region and later increasing it to 30 km must not alter the original 10 km.

Only new surrounding world state is revealed.

Never derive fundamental geography from the dimensions of the current requested region.

---

# 7. World Root

The user creates one root object:

```text
WorldRoot

```

The WorldRoot defines:

```text
seed
world_time
environment parameters
generation budget
camera
optional constraints
optional overrides

```

The user should not be required to manually specify a city boundary.

The default workflow should be:

```text
place WorldRoot
choose seed
choose time
choose camera
generate

```

The system generates appropriate terrain, water, vegetation and settlement automatically.

---

# 8. Spatial Domains

Every Thing has both:

```text
anchor
domain

```

The domain describes the spatial region it occupies or controls.

Supported domain types should include:

```text
PointDomain
CurveDomain
AreaDomain
SurfaceDomain
VolumeDomain
NetworkDomain

```

Examples:

Tree:

```text
PointDomain

```

Road:

```text
CurveDomain / NetworkDomain

```

Park:

```text
AreaDomain

```

Building:

```text
AreaDomain + VolumeDomain

```

Room:

```text
VolumeDomain

```

River:

```text
CurveDomain + AreaDomain

```

City:

```text
AreaDomain

```

The procedural framework must operate on domains generically rather than assuming every generator works on points or polygons.

---

# 9. Scope

Introduce a core structure called `Scope`.

A Scope contains the context in which a generator operates.

Conceptually:

```python
Scope:
    transform
    domain
    world_seed
    local_seed

    current_time
    historical_interval

    parent_constraints
    environment

    semantic_context

    refinement_request
    generation_budget

```

A generator consumes a Scope and may produce child Scopes.

Example:

```text
BuildingGenerator
    ↓
FloorScopes
FacadeScopes
RoofScope

```

Then:

```text
FloorGenerator
    ↓
RoomScopes
CorridorScopes

```

Then:

```text
RoomGenerator
    ↓
FurnitureScopes

```

The same mechanism must work for:

```text
World → regions
City → districts
District → blocks
Block → parcels
Park → vegetation zones
Forest → trees
Plant → branches

```

---

# 10. Semantic State and Geometry Must Be Separate

Never make generated geometry the authoritative representation of the world.

A Thing has semantic state independent from geometry.

For example:

```text
BuildingThing
    footprint
    construction_time
    height
    floors
    use
    style
    condition

```

Geometry may currently only be:

```text
box

```

The building nevertheless semantically exists as a full building.

Later geometry may become:

```text
facade
roof
windows
interior

```

without changing the semantic identity.

This separation is mandatory.

---

# 11. Stable Identity

Every semantic Thing receives a deterministic persistent ID.

Example:

```text
World
└── City_41
    └── District_18
        └── Block_702
            └── Parcel_191
                ├── Building_993 [1902–1974]
                └── Building_1882 [1976–present]

```

Objects can disappear historically while parent objects persist.

A Thing should therefore support:

```text
created_at
destroyed_at

```

or more generally:

```text
valid_time_interval

```

Identity must not be derived from transient geometry.

---

# 12. Determinism

Generation must be deterministic.

Conceptually:

```text
World = F(seed, rules, time, constraints)

```

Use hierarchical deterministic seeds.

Example:

```text
world seed
→ region seed
→ city seed
→ district seed
→ block seed
→ parcel seed
→ building seed
→ room seed
→ furniture seed

```

Do not use uncontrolled global random state.

Different subsystems should derive named deterministic sub-seeds.

For example:

```text
building_seed("structure")
building_seed("facade")
building_seed("interior")

```

Improving the furniture generator must not randomly alter the building facade.

---

# 13. Dependency Isolation

Sub-generator randomness must be isolated.

For example:

Changing:

```text
flower generator

```

must not alter:

```text
road network
building locations
terrain

```

Changing:

```text
furniture refinement

```

must not alter:

```text
building footprints

```

This requires deterministic sub-seeds and explicit subsystem boundaries.

---

# 14. Processes

Processes are first-class procedural objects.

A Process receives world state and produces Events.

A Process should generally not directly modify visual geometry.

Conceptually:

```python
Process.evaluate(
    world_state,
    time_interval,
    context
) -> list[Event]

```

Examples:

```text
UrbanGrowthProcess
RoadDevelopmentProcess
BuildingLifecycleProcess
VegetationGrowthProcess

```

---

# 15. Events

Changes occur through semantic Events.

Examples:

```text
CreateSettlement
ExtendRoad
UpgradeRoad
SplitParcel
MergeParcel
ConstructBuilding
ExtendBuilding
RenovateBuilding
DemolishBuilding
ChangeLandUse
CreatePark
PlantTree
TreeDies
FloodArea

```

Example:

```text
ConstructBuildingEvent

time = 1924.3
target = Parcel_181
building_type = residential
floors = 4
footprint = ...
seed = ...

```

The event history is independent of rendering.

---

# 16. Event Refinement

Events themselves must be hierarchically refinable.

A coarse simulation might initially create:

```text
ResidentialExpansion
time = 1920–1940
region = A
floor_area_added = 180000

```

Later a more sophisticated refiner may expand it into:

```text
ResidentialExpansion
├── ExtendRoad 1922
├── SplitParcels 1923
├── ConstructBuilding 1924
├── ConstructBuilding 1926
├── ConstructBuilding 1928
├── ...
└── ConstructBuilding 1939

```

The child events must satisfy the coarse parent event.

This allows historical resolution to improve without rewriting established history.

---

# 17. Coarse Facts Become Commitments

Once coarse generation establishes a fact, later refinement must respect it.

Example:

```text
District population in 1950 ≈ 12,000

```

A later household generator should produce approximately that population.

Example:

```text
Road exists by 1880

```

Later historical refinement cannot construct it in 1920.

Example:

```text
Building footprint reserved here

```

Interior generation must remain inside it.

This rule is fundamental:

> Refinement may add information but must not contradict already committed higher-level information.

---

# 18. Constraint Propagation

Constraints flow downward.

Conceptually:

```text
World
↓
Region
↓
City
↓
District
↓
Block
↓
Parcel
↓
Building
↓
Floor
↓
Room
↓
Furniture

```

Examples:

Building constrains Floors.

Floor constrains Rooms.

Room constrains Furniture.

Park constrains Plants.

Terrain constrains Roads.

Parent constraints should be accessible through Scope.

---

# 19. Growth Rather Than Placement

Cities must evolve.

Do not generate a final street layout and decorate it.

The world at time `t` should be the consequence of development over time.

Conceptually:

```text
World(t)
=
initial_state
+
events occurring before t

```

Urban development should initially support at least:

```text
settlement establishment
road extension
parcel subdivision
building construction
building replacement
urban expansion
park creation
vegetation maturation

```

---

# 20. Extendable Growth Rules

Growth rules must themselves support behavioral refinement.

Example road development:

Level 0:

```text
extend toward undeveloped land

```

Level 1:

```text
extend toward development pressure

```

Level 2:

```text
development pressure
+ terrain cost
+ connectivity

```

Level 3:

```text
traffic demand
+ construction cost
+ land acquisition
+ topology optimization

```

All levels implement the same Process contract.

---

# 21. Aggregate Models Before Agent Models

Do not initially simulate individual citizens.

Begin with aggregate fields.

Potential fields:

```text
population_density
employment_density
land_value
accessibility
development_pressure
traffic_pressure
building_condition
green_space_demand
industrial_pressure

```

These fields influence Processes.

Example:

```text
population pressure
+
accessible land
+
suitable zoning
→ development opportunity

```

Only introduce detailed agents later if they materially improve results.

---

# 22. Feedback Loops

Processes may influence one another.

Example:

```text
new road
→ accessibility rises
→ land value changes
→ development pressure rises
→ buildings appear
→ population/jobs increase
→ traffic rises
→ road pressure rises

```

These feedback systems should operate through semantic state and fields rather than direct geometry manipulation.

---

# 23. Terrain Generation

Terrain itself follows the same hierarchical architecture.

Minimum semantic terrain model:

```text
TerrainThing

```

Possible representations:

Far:

```text
coarse heightfield

```

Mid:

```text
erosion-scale terrain

```

Near:

```text
river banks
cliffs
drainage features

```

Very near:

```text
rocks
soil detail
grass
small vegetation

```

Do not require all levels initially.

---

# 24. Water

Water bodies should be semantic entities.

Types may include:

```text
Ocean
Lake
River
Wetland

```

At minimum:

```text
Ocean → plane / surface
Lake → plane
River → ribbon

```

Later refinement may add:

```text
shore geometry
beaches
cliffs
river banks
tributaries
wetlands

```

Hydrological structure should be determined from persistent world fields and terrain rather than invented independently at the visible scene boundary.

---

# 25. Sensible World Beyond the Detailed Area

There must never be an obvious artificial city boundary.

Around the highly refined area, generate progressively cheaper context.

Conceptually:

```text
Detailed Region
↓
Context Region
↓
Raw Context / Horizon

```

Detailed region:

```text
roads
buildings
parks
trees
interiors if visible

```

Context region:

```text
major roads
building masses
forest proxies
fields
water
terrain

```

Raw horizon:

```text
terrain
water
vegetation masses
settlement masses
major infrastructure

```

The transition should be gradual.

---

# 26. Context Halo

Each major generation request may define:

```text
Core Domain
Context Halo

```

The Core receives high refinement.

The Halo receives progressively cheaper representations.

Beyond the Halo, the world remains latent but deterministic.

The halo should be camera-aware.

For example, visible mountains may require terrain generation much farther away than geometry behind the camera.

---

# 27. Camera-Aware Generation

The target use case is static rendering.

Therefore the camera should strongly influence geometric refinement.

Estimate projected screen importance.

Possible inputs:

```text
distance
projected pixel size
visibility
occlusion
camera framing
depth of field
semantic importance
reflection visibility
shadow contribution

```

Example:

A 2 km distant skyscraper may deserve more geometry than a 5 m distant bottle if it occupies more screen space.

---

# 28. Refinement Priority

Implement a generic scheduler.

A candidate refinement receives a score.

Conceptually:

```text
score =
    visual_gain
    × semantic_importance
    × interaction_or_composition_importance
    × uncertainty
    × refinement_gain
    / computational_cost

```

Exact formula may evolve.

The scheduler repeatedly selects the most valuable unresolved refinement until budget is exhausted.

---

# 29. Budget-Based Generation

Do not rely only on fixed LOD distances.

Support explicit budgets such as:

```text
PREVIEW
DRAFT
HIGH
FINAL

```

and ideally numerical limits:

```text
max_generation_time
max_nodes
max_instances
max_triangles
memory_budget

```

For static renders, the system may use seconds or minutes to improve the scene.

This is an advantage over realtime systems.

---

# 30. Simulation LOD

Not only geometry should have LOD.

Simulation itself should support multiple levels.

Example:

Far-away region:

```text
statistical settlement model

```

Nearby city:

```text
district model

```

Foreground district:

```text
parcel-level development

```

Important building:

```text
individual building lifecycle

```

This allows large worlds without requiring detailed simulation everywhere.

---

# 31. Temporal LOD

History also has levels.

Coarse:

```text
1800
1900
2000

```

Medium:

```text
decades

```

Fine:

```text
individual construction and demolition events

```

Very fine:

```text
repairs
extensions
renovations

```

Historical refinement should be generated only where required.

---

# 32. Historical Time Control

The WorldRoot exposes a world time.

Example:

```text
World Year = 2025

```

Changing the year produces a deterministic historical snapshot.

Examples:

```text
1800 → small settlement
1870 → larger road network
1930 → industrial expansion
1970 → redevelopment
2025 → modern city

```

The same camera and seed should allow rendering consistent historical comparisons.

---

# 33. Lifecycle Model

Things may own lifecycle Processes.

Examples:

```text
BuildingThing
→ BuildingLifecycleProcess

RoadThing
→ RoadLifecycleProcess

PlantThing
→ PlantLifecycleProcess

DistrictThing
→ DistrictLifecycleProcess

```

A lifecycle may emit events affecting itself or other Things.

---

# 34. Building Replacement

Replacement is event-driven.

Example:

```text
Parcel_22

Building_A
valid 1901–1974

DemolishBuilding 1974

Building_B
valid 1976–present

```

At 1950:

```text
Building_A exists

```

At 2025:

```text
Building_B exists

```

The parcel identity remains stable.

---

# 35. Reusable Subsystems

Generators must be compositional.

Example ParkGenerator:

```text
ParkGenerator
├── TerrainAdapter
├── PathGenerator
├── BenchGenerator
├── LampGenerator
└── VegetationGenerator

```

Example BuildingGenerator:

```text
BuildingGenerator
├── StructureGenerator
├── FacadeGenerator
├── WindowGenerator
├── InteriorGenerator
└── PlantGenerator

```

Do not duplicate procedural systems.

---

# 36. Integration of the Existing Plant System

The existing procedural plant generator should become one implementation behind a generic vegetation interface.

Example:

```text
VegetationThing
→ TreeThing
→ PlantGenerator

```

Far away:

```text
TreeThing
→ coarse canopy/trunk proxy

```

Midground:

```text
TreeThing
→ simplified tree

```

Foreground:

```text
TreeThing
→ full Morpho Plants generator

```

The city or park generator should not know how plant geometry works.

It requests:

```text
species/genome characteristics
position
age
environment
detail requirement
seed

```

and receives the appropriate representation.

---

# 37. Forest Refinement

Forest:

Far:

```text
forest mass

```

Medium:

```text
canopy clusters

```

Near:

```text
individual tree proxies

```

Very near:

```text
individual full plant generators

```

Same semantic forest, increasingly refined.

---

# 38. Generic Fallback Representation

Every Thing must be renderable even if no specialized geometry implementation exists.

Generic fallback:

```text
PointDomain → marker / sphere
CurveDomain → line / tube
AreaDomain → flat polygon
VolumeDomain → bounding box
NetworkDomain → line network

```

This guarantees that missing generators never make the world impossible to visualize.

---

# 39. Missing Specialized Systems

Suppose no furniture generator exists.

Room refinement may currently output:

```text
FurnitureProxyThing

```

represented as boxes.

Later:

```text
FurnitureProxyThing
→ FurnitureThing
→ Chair / Desk / Bed / Shelf

```

Likewise:

```text
UnknownStatueThing
→ bounding box

```

until a StatueGenerator is implemented.

Fallbacks are first-class, not error cases.

---

# 40. Refinement Providers

Avoid hard-wiring every possible refinement into the Thing classes.

Use pluggable refiners.

Conceptually:

```python
class Refiner:
    supported_node_type
    refinement_dimension
    capability
    cost_estimate

    def can_refine(node, context):
        ...

    def estimate_gain(node, context):
        ...

    def refine(node, context):
        ...

```

Multiple refiners may support the same Thing.

Example:

```text
BuildingMassingRefiner
BuildingFacadeRefiner
BuildingInteriorRefiner
BuildingHistoricalRefiner
BuildingLifecycleRefiner

```

This makes future extensions modular.

---

# 41. Registry

Use a registry system for:

```text
Thing types
Process types
Refiners
Representations
Event types
Domain types

```

New modules should register themselves rather than requiring edits to one enormous switch statement.

Avoid:

```python
if thing.type == BUILDING:
...
elif thing.type == ROAD:
...

```

throughout the architecture.

---

# 42. Data-Oriented Semantic Graph

The semantic graph should remain relatively lightweight.

Do not require a full Blender object for every semantic node.

Potential semantic node:

```python
Node:
    id
    type_id
    parent_ids
    child_ids

    semantic_state
    domain

    seed

    temporal_state

    committed_constraints

    refinement_state

```

Geometry should be generated separately.

This allows millions of coarse semantic nodes without millions of scene objects.

---

# 43. Lazy Materialization

Do not fully instantiate every child immediately.

Example:

```text
CityThing

```

may know that it contains:

```text
district summaries

```

without generating every block.

A District may know aggregate:

```text
population
density
road length
building floor area

```

without explicitly creating every parcel.

Only materialize children when refinement requires them.

---

# 44. Caching

Refinement results should be cacheable.

Cache key should include relevant inputs such as:

```text
node identity
node version
seed
world time
generator version
constraints
refinement parameters

```

Avoid regenerating unaffected parts of the world unnecessarily.

---

# 45. Invalidation

When something changes, invalidate only dependent results.

Example:

Changing:

```text
camera

```

should alter geometric refinement decisions but not world history.

Changing:

```text
world year

```

may alter active buildings and vegetation ages but should not regenerate terrain.

Changing:

```text
terrain seed

```

may invalidate almost everything spatially dependent on terrain.

Dependency tracking should make these relationships explicit.

---

# 46. Versioning

Refiners should expose implementation versions.

Example:

```text
RoadGrowthRefiner v1
BuildingGenerator v3
PlantGenerator v2

```

World metadata should record generator versions.

This helps reproduce old results and diagnose changes after algorithms improve.

---

# 47. Manual Constraints and Artistic Direction

Default behavior should require minimal manual input.

However users must be able to constrain the world.

Potential constraint nodes:

```text
FixedRoad
FixedBuilding
FixedLandmark
ProtectedArea
NoBuildArea
HistoricCenter
CommercialCenter
IndustrialAttractor
TransportHub
GrowthAttractor
GrowthRepulsor
ParkConstraint
WaterConstraint

```

Constraints have:

```text
domain
strength
falloff
active time range
parameters

```

---

# 48. Influence Fields

Generic influences should be supported.

Conceptually:

```text
InfluenceField:
    domain
    value
    falloff
    active_time

```

Examples:

```text
development attraction
commercial attraction
land value modifier
traffic attraction
vegetation suppression
historic preservation

```

Processes sample these fields.

---

# 49. Environment

The World exposes environmental information generically.

Possible fields:

```text
terrain height
terrain normal
slope
water proximity
soil
moisture
temperature
sun exposure
wind
biome

```

Sub-generators may use the subset they understand.

Example:

RoadGenerator:

```text
slope
water
terrain cost

```

PlantGenerator:

```text
moisture
light
temperature
space

```

---

# 50. Initial City Growth Model

The first implementation should remain deliberately simple.

Minimum viable urban growth:

1. Determine settlement-suitable regions.
2. Seed one or more settlements.
3. Create primitive early road structure.
4. Expand roads toward development pressure.
5. Produce blocks.
6. Divide blocks into parcels.
7. Assign broad land use.
8. Construct buildings.
9. Age buildings.
10. Occasionally renovate, extend, demolish or replace them.
11. Create parks/open land where appropriate.
12. Continue until target world time.

This model does not need realistic economics initially.

It must, however, use the generic Process/Event architecture.

---

# 51. Initial Terrain Model

Minimum implementation:

```text
multi-scale deterministic height field
sea level
basic drainage
basic rivers
basic biome classification

```

It should already produce:

```text
ocean
coasts
plains
hills
mountains
rivers

```

Later improved erosion/hydrology can replace or refine these processes.

---

# 52. Initial Road Model

Minimum:

```text
road nodes
road edges
road hierarchy

```

Roads should grow incrementally.

Initial road extension may consider:

```text
development pressure
terrain slope
water crossing penalty
existing connectivity

```

Roads must be persistent semantic entities.

---

# 53. Initial Parcel Model

Road geometry creates blocks.

Blocks are subdivided into parcels.

Initial parcel subdivision may use simple heuristics:

```text
target frontage
target parcel depth
minimum area

```

Later systems may improve historical subdivision behavior.

---

# 54. Initial Building Model

Minimum building semantic parameters:

```text
footprint
height
floor_count
usage
construction_time
condition
style seed

```

Geometry levels:

```text
LOD 0: bounding block
LOD 1: massing
LOD 2: roof + facade
LOD 3: windows/doors
LOD 4: floor structure
LOD 5: rooms
LOD 6: furniture

```

These are capabilities rather than one global integer.

---

# 55. Building Interior Development

Interior generation must consume the existing building constraints.

Example:

```text
Building
→ Floors
→ circulation
→ Rooms

```

Initially:

```text
rooms represented as colored volumes

```

Later:

```text
walls
doors
stairs

```

Later:

```text
furniture proxies

```

Later:

```text
real furniture generators

```

Do not make interior availability necessary for exterior generation.

---

# 56. Static Render Workflow

The primary use case is generating static scenes.

Suggested workflow:

```text
1. Add WorldRoot
2. Set seed
3. Set year
4. Set camera
5. Optionally add constraints
6. Select generation quality/budget
7. Generate snapshot
8. Inspect
9. Force/refuse refinement on selected areas if desired
10. Generate final

```

---

# 57. Forced Refinement Controls

Users must be able to override automatic refinement.

Per node:

```text
Auto
Forced Minimum Detail
Forced Maximum Detail
Never Refine
Always Refine

```

Examples:

A visible building through a window:

```text
minimum structural refinement = interior

```

Background district:

```text
maximum geometric refinement = massing

```

---

# 58. Camera-Specific Scene Realization

Semantic world state should be reusable across different cameras.

Camera A may request:

```text
detailed downtown
coarse suburbs

```

Camera B may request:

```text
detailed suburbs
coarse downtown

```

Both derive from the same semantic world.

Do not bake camera-specific geometry decisions into semantic history.

---

# 59. Snapshot Concept

The final output is a Snapshot:

```text
Snapshot(
    world,
    time,
    camera,
    refinement_budget
)

```

A Snapshot materializes the subset of semantic world state needed for a render.

The same World may produce many Snapshots.

---

# 60. Geometry Backend Separation

The procedural core should not depend strongly on Blender.

Preferred layers:

```text
Core Semantic System
↓
Procedural Generators
↓
Geometry Description Layer
↓
Blender Adapter

```

This allows core logic to be unit-tested without Blender.

The Blender adapter creates:

```text
Meshes
Curves
Instances
Collections
Materials
Geometry Nodes setups

```

---

# 61. Blender Representation

Suggested Blender organization:

```text
WorldRoot

Generated_World/
    Terrain/
    Water/
    Roads/
    Buildings/
    Vegetation/
    Props/
    Debug/

```

Do not create one Blender Collection for every semantic node.

Use batching and instancing where appropriate.

---

# 62. Instancing

Strongly prefer instancing for:

```text
windows
street lamps
trees
cars if ever implemented
chairs
repeating facade modules
rocks
vegetation

```

Semantic identity may remain distinct even if geometry is shared.

---

# 63. Geometry Nodes

Geometry Nodes may be useful for high-volume repeated geometry.

However:

- Semantic structure must not live exclusively inside opaque Geometry Nodes graphs.
- Important procedural decisions should remain accessible to the semantic system.
- Geometry Nodes should primarily act as efficient realization mechanisms.

---

# 64. Debug Visualization

Implement strong debugging tools from the beginning.

Possible overlays:

```text
domains
scopes
road graph
parcel boundaries
development pressure
land value
population density
refinement level
node IDs
historical age
event locations
generation costs

```

Without these, procedural failures will become extremely difficult to diagnose.

---

# 65. Inspection UI

Selecting a generated object should expose:

```text
semantic ID
semantic type
parent
creation time
destruction time
seed
generator
generator version
refinement state
constraints
event history

```

Allow navigating:

```text
parent
children
source event
source process

```

---

# 66. Serialization

World state should be serializable separately from Blender geometry.

Recommended format:

```text
JSON or MessagePack for early versions

```

Possibly later a custom binary format.

Persist:

```text
World seed
World settings
Constraints
Committed semantic state
Events
Generator versions
Manual overrides

```

Derived geometry should not need to be stored unless intentionally cached.

---

# 67. Reproducibility

A serialized world plus matching generator versions should recreate the same semantic world.

A Snapshot additionally requires:

```text
camera
time
budget
render settings

```

---

# 68. Performance Philosophy

Optimize first around semantic scalability.

Millions of semantic abstractions should be cheaper than millions of Blender objects.

Only refine and realize things that matter.

Broad priority:

```text
semantic graph
→ lazy structural generation
→ camera-aware selection
→ geometry realization

```

Do not generate enormous detailed cities and then hide them.

---

# 69. Error Handling

Generator failure must degrade gracefully.

If a specialized refiner fails:

```text
fallback to previous refinement level

```

Example:

```text
FurnitureGenerator fails
→ use furniture proxy

```

If detailed facade generation fails:

```text
use building massing

```

A single unsupported specialization must never prevent the world from rendering.

---

# 70. Testing Strategy

The core system should have extensive deterministic unit tests.

Test categories:

## Determinism

Same inputs → same outputs.

## Seed isolation

Changing one subsystem does not alter unrelated systems.

## Constraint preservation

Child refinement satisfies parent commitments.

## Spatial consistency

Children remain inside parent domains unless explicitly allowed.

## Temporal consistency

Objects do not exist outside validity intervals.

## Historical consistency

Refined events preserve parent event totals and intervals.

## Expansion consistency

Generating a larger world does not alter already generated coordinates.

## Refinement monotonicity

Higher refinement adds information without unexpectedly removing committed facts.

## Serialization

Save/load preserves semantic state.

## Backend independence

Core tests run without Blender.

---

# 71. Suggested Module Architecture

A possible code organization:

```text
procedural_world/
│
├── core/
│   ├── node.py
│   ├── thing.py
│   ├── process.py
│   ├── domain.py
│   ├── scope.py
│   ├── event.py
│   ├── constraints.py
│   ├── seed.py
│   ├── registry.py
│   └── serialization.py
│
├── refinement/
│   ├── refiner.py
│   ├── scheduler.py
│   ├── budget.py
│   ├── dependency.py
│   └── cache.py
│
├── world/
│   ├── world.py
│   ├── fields.py
│   ├── climate.py
│   └── regions.py
│
├── terrain/
│   ├── terrain.py
│   ├── hydrology.py
│   └── terrain_geometry.py
│
├── urban/
│   ├── settlement.py
│   ├── city_growth.py
│   ├── roads.py
│   ├── blocks.py
│   ├── parcels.py
│   ├── land_use.py
│   └── urban_fields.py
│
├── buildings/
│   ├── building.py
│   ├── lifecycle.py
│   ├── massing.py
│   ├── facade.py
│   ├── floors.py
│   └── interiors.py
│
├── vegetation/
│   ├── vegetation.py
│   ├── forests.py
│   └── morpho_adapter.py
│
├── representation/
│   ├── geometry.py
│   ├── fallback.py
│   └── snapshot.py
│
└── blender/
    ├── addon.py
    ├── world_root.py
    ├── operators.py
    ├── ui.py
    ├── geometry_backend.py
    ├── materials.py
    └── debug_draw.py

```

This is illustrative, not mandatory.

---

# 72. Initial Core Interfaces

Conceptually:

```python
class ProceduralNode:
    id
    type_id
    seed
    domain
    semantic_state
    refinement_state
    constraints

```

```python
class Thing(ProceduralNode):
    valid_time_interval

```

```python
class Process(ProceduralNode):

    def evaluate(
        self,
        world,
        time_interval,
        context
    ) -> list[Event]:
        ...

```

```python
class Refiner:

    def supports(self, node, dimension) -> bool:
        ...

    def estimate_cost(self, node, context):
        ...

    def estimate_gain(self, node, context):
        ...

    def refine(self, node, context):
        ...

```

```python
class RepresentationProvider:

    def supports(self, thing):
        ...

    def realize(self, thing, detail_request, backend):
        ...

```

---

# 73. Development Phases

## Phase 1 — Generic Core

Implement:

```text
ProceduralNode
Thing
Process
Domain
Scope
Event
Constraints
Seed derivation
Registry
Serialization

```

No city yet.

Test heavily.

---

## Phase 2 — Refinement Infrastructure

Implement:

```text
Refiner registry
four refinement dimensions
budget
scheduler
lazy child generation
fallback representation
dependency tracking

```

Create trivial synthetic Things to test recursion.

---

## Phase 3 — Infinite World Fields

Implement:

```text
deterministic coordinate fields
terrain height
sea level
basic biome
basic water

```

Verify world expansion consistency.

---

## Phase 4 — Blender WorldRoot

Implement:

```text
WorldRoot object
basic UI
camera reference
time
seed
generation budget
Generate Snapshot

```

Render terrain and water.

---

## Phase 5 — Primitive Settlements

Implement:

```text
settlement suitability
settlement seed
very simple roads
building proxies

```

Result should already visually resemble a crude settlement.

---

## Phase 6 — Historical Growth

Implement:

```text
time
events
road extension
new construction
building aging
demolition/replacement

```

Verify historical snapshots.

---

## Phase 7 — Blocks and Parcels

Add:

```text
road-enclosed blocks
parcel subdivision
land use

```

Buildings now arise from parcels.

---

## Phase 8 — Building Refinement

Implement:

```text
massing
roofs
facades
windows
basic floors

```

No interiors required yet.

---

## Phase 9 — Camera-Aware Scheduler

Implement:

```text
projected screen importance
visibility approximation
geometric budget
context halo

```

Far regions use proxies automatically.

---

## Phase 10 — Vegetation Integration

Integrate Morpho Plants.

Implement:

```text
vegetation areas
forest proxies
individual nearby trees
full detailed foreground plants

```

---

## Phase 11 — Interiors

Implement:

```text
floors
rooms
circulation
proxy furniture

```

---

## Phase 12 — Generic Extension API

Document how a developer adds:

```text
new Thing
new Process
new Refiner
new Event
new Representation

```

At this point the framework must be usable by future procedural subsystems without editing the core.

---

# 74. Non-Goals for the First Version

Do not initially attempt:

```text
full realistic economics
individual human simulation
real traffic simulation
complete architectural engineering
accurate sewage/water infrastructure
fully realistic erosion
perfect hydrology
photorealistic materials
fully furnished interiors

```

These belong to later refinement modules.

The architecture must support their future addition without requiring them now.

---

# 75. Critical Anti-Patterns

Do not implement separate monolithic generators such as:

```text
GenerateCity()
GenerateVillage()
GenerateForest()

```

that directly create final geometry.

Do not build:

```text
if LOD == 0
...
elif LOD == 1
...

```

as the fundamental architecture.

Do not tie semantic state to Blender objects.

Do not rely on scene boundaries for world generation.

Do not generate every detail and merely hide distant geometry.

Do not let detailed generation contradict previously committed coarse state.

Do not let improvements in one subsystem reshuffle unrelated random results.

Do not make absent lower-level generators fatal.

---

# 76. Desired Emergent Behavior

Eventually, with only:

```text
WorldRoot
Seed
Year
Camera

```

the system should be capable of producing something conceptually like:

```text
World
├── terrain
│   ├── mountains
│   ├── valleys
│   └── coast
│
├── hydrology
│   ├── ocean
│   └── river
│
├── settlement
│   └── city
│       ├── historic core
│       ├── later districts
│       ├── roads
│       ├── blocks
│       ├── parcels
│       ├── parks
│       │   └── vegetation
│       │       └── Morpho Plants
│       │
│       └── buildings
│           ├── exterior
│           ├── floors
│           └── visible interiors
│               └── furniture
│
└── surrounding context
    ├── villages
    ├── farmland
    ├── forests
    └── raw terrain

```

All of this represents one deterministic semantic world.

Only the amount of instantiated detail varies with:

```text
camera
time
available refiners
generation budget
manual constraints

```

---

# 77. Ultimate Architectural Rule

The most important invariant of the entire system is:

> A coarse world must always remain valid when the system learns how to generate more detail.

A newly implemented subsystem should normally add one of:

```text
new specialization
new structural refinement
new geometric refinement
new temporal refinement
new behavioral refinement

```

rather than requiring old systems to be rewritten.

A procedural city is therefore not a finished model.

It is a partially resolved description of a world whose unresolved parts can always be expanded later.

---

# 78. Final Mental Model

The framework can be summarized as:

```text
WORLD SEED
    ↓
latent deterministic world
    ↓
semantic Things
+
Processes
+
Events
+
Constraints
    ↓
recursive refinement
    ↓
camera/time/budget-dependent Snapshot
    ↓
geometry backend
    ↓
Blender scene

```

Or more compactly:

```text
World
=
Things
+
Processes
+
History
+
Constraints
+
Refinement

```

The city, buildings, interiors, furniture, terrain and plants are all applications of the same underlying recursive procedural system.

The user should be able to start with a nearly empty WorldRoot today and continuously gain more realistic and more detailed output as new refiners are implemented in the future.