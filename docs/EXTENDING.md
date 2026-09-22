# Extension contracts

The executable example `examples/custom_extension.py` adds all five major
extension types without modifying built-ins. Import and register an extension
before loading a world that records its generator versions.

## Semantic types and manual Things

Create a fresh default registry, then register a type with a semantic parent:

```python
from procedural_world.world.bootstrap import default_registry
registry = default_registry()
registry.register_type("StoneStatue", "Thing", category="Props")
```

Create a `Thing` with a persistent ID, seed, domain, JSON-compatible semantic
state, parent IDs and lifetime. `World.add_thing()` adds a manually authored node
to the base semantic graph. It still enforces the same graph/domain invariants.
Semantic type inheritance is independent of composition: a StoneStatue can have
no generated child structure while still being a StoneStatue.

## Processes and Events

Subclass `Process.evaluate(world_state, time_interval, context)` and return
Events. Do not create Blender objects or meshes from a Process. A registered
handler applies the event to a SemanticGraph. Creation/update/destruction helper
handlers are available, and custom semantic handlers may be registered. Unknown
event types fail on replay rather than being ignored.

The initial region application invokes the registered UrbanGrowthProcess. A
custom application explicitly invokes its additional processes, as shown in the
example. Registering a Process does **not** automatically choose when to run it.
Manually emitted global events operating on manually authored/base-graph objects
are included in snapshots. Region-owned extensions should arrange their event
ownership and dependency materialization in their application; a global event
must not require an omitted, unmaterialized regional target.

An event ID must be stable across evaluation calls. Appending the same event is
idempotent; reusing its ID for different payload/time is rejected. Use explicit
priorities when equal-time creation events have parent-child dependencies.
Lifetimes use `[start, end)`, replay uses `event.time <= snapshot.time`, and coarse
event refinement intervals are inclusive when validating child event dates.

Coarse aggregate example:

```python
log.refine(parent_id, child_events, requirements=(
    AggregateRequirement("floor_area_added", "floor_area_added", tolerance=0.01),
))
```

The parent must already exist and provide an interval. Child events must cite
that parent, remain in the interval and preserve all supplied aggregate totals.
Aggregate handlers should not double-apply child mutations.

## Refiners

Subclass `Refiner` and define `key`, `version`, `dimension`, supported types and a
capability. Implement `refine(node, context)` and return `RefinementResult`.

A proposal must advance exactly one dimension by one local state level. It can
add previously absent facts, generate children inside the parent, or replace
geometry. It cannot overwrite a committed fact, change identity or create an
orphan. Nodes passed to plugins are isolated copies. Context supplies environment,
time, registered providers, cache, camera, global constraints, inherited
commitments and an optional plant adapter, but not a mutable authoritative graph.
`context.scope_for(node)` creates a Scope with named seed and inherited context.

Declare deterministic cost and positive gain estimates for scheduling. The
actual proposed geometry/child cost is checked before commit; estimates never
permit overspending. A provider exception or invalid proposal leaves previous
state intact and is recorded in the snapshot report. Do not perform irreversible
external side effects inside a refiner; the transaction only protects internal
semantic and geometry state.

## Representation providers

Subclass `RepresentationProvider`; define supported semantic types, priority,
implementation version, maximum local geometric level, optional refinement gain,
and whether output depends on world time. Return `GeometryBundle` containing
backend-neutral meshes and/or instances. Do not import `bpy` here.

A Mesh has finite world-space vertices, polygon index tuples and a material key.
An Instance cites a shared prototype and a Transform (translation, positive
scale, Z rotation). Bundles may introduce named prototypes; names should include
your extension/version or a deterministic shape key to avoid collisions.
`GeometryScene` expands instances for OBJ export or leaves them shared for Blender.
Normals/material textures and arbitrary affine rotations are intentionally not
part of this minimal geometry layer; extend it explicitly when needed.

A provider's `time_dependent` flag must be true for age-dependent geometry.
Implementation/version, input state, world seed, relevant time, constraints,
cutaway flag and adapter version participate in cache keys. Changing code without
updating its version undermines reproducibility.

## Domains and fallbacks

Implement a `Domain` with bounds, anchor, containment and `to_data()` methods.
Register its JSON reader with `register_domain(type_id, reader)`. Register a
geometry fallback with `register_fallback(DomainSubclass, provider)` or accept
the generic bounding-box fallback. Use an explicit domain containment rule; do
not silently accept children just because their anchors lie inside a parent.

## Plant bridge

`MorphoPlantsAdapter(generate_callable, version)` invokes an application-supplied
callable with a `PlantRequest`: semantic ID, seed, species, age, position,
maximum envelope, environment and detail requirement. That callable must return
`GeometryBundle` in world coordinates. Geometry exceeding the committed Tree
domain is rejected, and the previous proxy is retained. Implement translation
to the actual external plant API in your own integration function; no external
package names or API signatures are guessed here.

## Versioned save/load

Register the same required extension versions before `World.load(path,
registry=registry)`. An additional new provider is allowed; a missing or changed
recorded version fails by default. `strict_versions=False` emits a warning rather
than pretending the regenerated output is reproducible. There is no automatic
migration mechanism for incompatible changes to old committed facts.
