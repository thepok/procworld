# Architecture and invariants

## Data flow

`WorldSettings + constraints -> coordinate fields + canonical-region Processes
-> immutable semantic Events -> replayed SemanticGraph -> independent refiners
-> camera/budget-specific Snapshot -> GeometryScene -> export or Blender`.

The `World` object itself is the WorldRoot application object. Its base graph
contains a root `Thing` with an `UnboundedDomain`. The finite region size is a
world-rule input describing canonical ownership cells; it is not derived from
the requested scene dimensions. A requested radius and halo choose which cells
are materialized. Already-owned coordinates and IDs do not move when the request
expands. Region generation is lazy; building interiors and individual forest
vegetation are further lazy structural applications.

## Modules

`core` contains spatial domains, lightweight Things and Processes, Scopes,
registries, named randomness, commitments, graph transactions, event history and
JSON persistence. It has no Blender dependencies.

`world` contains immutable settings, absolute-coordinate environmental fields,
canonical owner regions, built-in registration and the persistent World API.
`terrain` provides coarse downhill drainage and heightfield/water representations.
`urban` emits development events and incremental road topology. `buildings`
provides lifecycles, structure and exteriors. `vegetation` provides area proxies,
lazy trees and the plant-adapter boundary.

`refinement` contains the four-axis contract, deterministic best-first scheduler,
resource ledger, overrides, bounded cache and transitive dependency invalidation.
`representation` contains camera projection, meshes, prototypes, instances,
fallbacks, snapshot assembly and OBJ/SVG/JSON exports. `blender` is the optional
realization/UI layer.

## Identity and randomness

IDs use BLAKE2b over canonical JSON tuples of parent identity, semantic type and
stable ownership key. Seeds derive from named paths rather than Python's salted
`hash()` or a global RNG. A random sample is keyed, for example,
`RandomStream(parcel_seed, "building", generation).uniform(..., "setback")`.
Adding a furniture draw cannot advance the facade's random sequence. Geometry,
iteration order and current camera are never identity inputs.

Specialization uses a semantic type registry. `graph.specialize()` requires a
registered subtype and preserves the persistent ID and composition. Refinement
creates child nodes or additive facts; it does not change semantic identity.

## Spatial commitments

All node domains are in absolute world coordinates. A Scope also provides a
Transform for local representation work, but generators do not implicitly
reinterpret semantic coordinates through that transform. Child generation must
satisfy parent-domain containment and lifetime constraints.

Area domains constrain XY footprints, not altitude. Volume domains constrain XYZ.
Surface domains have polygonal XY support and a finite height interval. Curves
and networks conservatively test child AABBs against individual segment capsules;
this can reject a valid but complicated child rather than accept an escaping one.
Concave area containment checks boundary-intersection intervals, not merely
corner membership. Generic concave area geometry uses ear-clipping triangulation
and expects simple, non-self-intersecting polygons.

A river may cross its owner region boundary through an explicit provenance
permission. Such exceptions are not inferred automatically for every child.
The finite world's conceptual root is represented by UnboundedDomain without
serializing infinities or pretending the visible rectangle is the whole world.

## Atomic refinement

A Refiner receives an isolated node copy and a context without a mutable graph.
It returns a `RefinementResult` declaring exactly one dimension advance, additive
facts, child nodes and/or replacement geometry. A staged graph validates IDs,
parents, domains, lifetimes and committed values before publishing. Resource
cost is reserved before graph or geometry state is committed. A failing provider
therefore retains the previous representation. External plant geometry is also
checked against the committed tree envelope.

Structural and behavioral refinement records are persisted as additive
commitments. Snapshot-specific geometric state is not persisted as authoritative
world data. Temporal event views are derived per snapshot; the authoritative
history remains the event log. Committed structural children remain valid when
a parent is later demolished because replay intersects their lifetimes with the
parent and active traversal also checks ancestors.

## History

Initial geographic entities are timeless relative to the supported historical
interval. Urban growth establishes settlements and districts, grows connected
road frontiers, creates road-enclosed rectangular blocks, subdivides parcels,
constructs buildings, renovates and replaces them, and reserves parks. A road is
created before its adjacent block. Parcel identity survives each replacement.
Historical dates and initial building properties are derived from birth events,
not from the camera or the requested snapshot year.

EventLog replay sorts by time, explicit priority and persistent ID. Its creation,
update and destruction handlers operate on semantics only. Registration controls
which event types can execute; unknown event types raise an error rather than
silently disappear. Aggregate events are containers and commitments, not a
second state mutation on top of their children. `EventLog.refine()` validates
parent intervals, parent IDs and supplied aggregate requirements transactionally.

The initial urban evaluator resolves a full finite region's history when that
region is first requested. Context views can instantiate only region/settlement
summaries, but deriving those summaries currently still evaluates that finite
region. This is **not** a million-node hierarchical aggregate simulator. Future
regional summary providers should avoid that work at source; they can do so
without changing the graph, Process, Event or Snapshot contracts.

## Selection and budgets

Camera importance estimates projected bounding-sphere size and frustum overlap.
A large object can outrank a smaller nearby one. Semantic importance, provider
gain, distance-to-core falloff, estimated cost and manual overrides affect the
best-first queue. Stable identity/key tie-breakers remove traversal-order
randomness. Reflection, shadow, depth-of-field and occlusion contributions are
not solved by this first camera model.

Base terrain and water are represented before optional detail. A specialized
representation missing or failing at baseline uses the generic domain fallback.
Numerical budgets can still omit objects: no finite budget can guarantee all
proxies for an arbitrarily large requested world. Reports expose coarse regions,
omitted regions, omitted representations, skipped refiners, errors and unmet
forced minima. Force controls never override numerical ceilings.

Memory accounting estimates JSON semantic payloads and mesh/instance arrays,
not every Python object, cached result, event record, Blender datablock or RSS
allocation. Event planning is bounded per owner region but not preemptive. The
wall-clock deadline is checked between tasks; it is not a hard real-time limit.

## Cache and invalidation

Result keys include semantic identity/version/state, seed, type, domain,
implementation/version, requested detail, constraints, cutaway state and adapter
version. Time is included only for a time-dependent provider. Camera selection
is outside geometry cache keys. Dependency tags identify nodes, generators,
world seed, constraints and time; `ResultCache.invalidate()` follows reverse
transitive dependencies. Cache values are copied at the boundary to prevent a
consumer from mutating stored results. The cache is bounded and ephemeral.

Changing immutable geography/rule settings requires a new World. Camera changes
reuse history and cached geometry; time changes replay history and retain
terrain cache entries. Versioned JSON contains no geometry unless explicitly
exported as a separate Snapshot representation.
