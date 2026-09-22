# Hierarchical Procedural World

A runnable, dependency-free Python reference implementation of the attached
**Hierarchical Procedural World System** specification, with a Blender add-on.
The semantic core does not import Blender. Version: **1.0.0**.

This is an extensible first implementation, not a production photorealistic
city simulator or a claim that every future capability in the specification is
complete. See [implementation status](docs/IMPLEMENTATION_STATUS.md) for the
explicit boundaries, including the plant bridge and Blender runtime status.

## Start without Blender

Extract the ZIP. From the directory **containing** the `procedural_world` folder:

```bash
python -m procedural_world generate --seed 12 --year 2025 --out world_output
```

Python **3.10 or newer** is required. No third-party runtime packages are needed.
The command writes `world.json` (semantic state, events, constraints, versions),
`world.obj` and `world.mtl` (portable geometry), `map.svg` (top-down semantic debug
map), and `snapshot.json` (camera, budget report, omissions and errors).
Open the SVG in a browser or import the OBJ into a 3D application. The OBJ exporter
expands instances; Blender can retain them through Geometry Nodes.

For a smaller initial request:

```bash
python -m procedural_world generate --radius 350 --halo 1 --max-refinements 80 --out small_world
```

An editable installation and `worldgen` command are also supported:

```bash
python -m pip install -e ./procedural_world
worldgen generate --seed 12 --year 1930 --quality DRAFT --out world_1930
```

The repository intentionally is the add-on package itself; `pyproject.toml`
contains an explicit package-directory mapping for that layout.

## Start in Blender

The **same delivered ZIP** has `procedural_world/__init__.py` at its top package
level and is intended for Blender's legacy add-on **Install from Disk** workflow.
Install the ZIP, enable **Hierarchical Procedural World**, then open the 3D
Viewport sidebar (`N`) and select **World Gen**. Add a WorldRoot, select a seed,
year, camera and budget, then choose **Generate Snapshot**.

Target API: **Blender 4.2+**. The Python sources were compiled and the independent
core was tested, but Blender was **not installed in the authoring environment**.
Blender registration, Geometry Nodes evaluation, UI interaction and rendering
therefore require runtime verification on your installation. A supplied smoke
test exercises generation, evaluated instances and safe replacement:

```bash
blender --background --factory-startup --python procedural_world/examples/blender_smoke_test.py
```

See [Blender usage and troubleshooting](docs/BLENDER.md). The adapter does not
clear your scene, change your render engine, or create one object per semantic
node. Terrain and other meshes are batched by category/material. Repeated
geometry uses Geometry Nodes point instancing; a failed instancing setup falls
back to mesh batches. Generated content is owner-tagged and replaced only after
a new scene realization succeeds. Keep a normal backup of `.blend` files.

## API example

```python
from procedural_world import World, WorldSettings, Camera, Budget, RefinementState

world = World(WorldSettings(seed=12, world_time=2025))
snapshot = world.snapshot(
    time=1930,
    camera=Camera((650, -900, 650), (0, 0, 40)),
    center=(0, 0),
    radius=600,
    halo=2,
    budget=Budget.preset("DRAFT"),
    request=RefinementState(structural=1, geometric=2, temporal=1, behavioral=1),
)
world.save("world.json")
```

`World` is the camera-independent semantic root. `Snapshot` is a bounded view
and realization of it. Coordinates are meters, XY is the ground plane, and Z is
up. Years are floating-point values; Thing lifetimes are half-open intervals
`[created_at, destroyed_at)`. Events are applied at `event.time <= snapshot.time`.

The default seed 12 has land near the origin. Seed 42 has ocean near the origin;
that is intentional, not a failed city generator. Geography is never changed
just to force a settlement into the requested scene.

## Independent refinement controls

| Control | Initial application capabilities |
|---|---|
| Structural 0–3 | 0: proxies; 1: building floors and individual vegetation; 2: rooms and circulation; 3: furniture proxies |
| Geometric 0–3 | 0: coarse representation; buildings add roofs at 1 and windows/doors at 2; terrain supports three grid upgrades |
| Temporal 0–1 | Per-node views of explicit source events; the core also validates aggregate event refinement |
| Behavioral 0–1 | Resolves a coarse urban-process policy into explicit rule descriptors, without rewriting committed history |

These are **independent request axes**, not a global LOD. Structural request
numbers denote available capabilities down the ownership hierarchy. A Building
advances its own structural state once when it creates Floors; those Floors
advance their own states when creating Rooms. They do not all share a universal
"LOD 3" interpretation. Geometric capabilities are provider-specific.

`WorldSettings.behavioral_level` chooses among the initial growth policies
(0: coarse, 1: slope-aware, 2: additional fertility/elevation costs). That is a
world rule input. Increasing the behavioral *refinement request* exposes the
already-selected rule model; it does not silently change the past.

Interior generation is independent of exterior geometry. `--structure 3
--interiors` requests a deliberate cutaway and interior proxies. It is not an
automatic window-visibility or occlusion solver. Forced node overrides can
prioritize specific buildings, but numerical budgets always win.

## Budgets, failures, and reproducibility

PREVIEW, DRAFT, HIGH and FINAL specify numerical node, realization-instance,
triangle and refinement limits. You can override them:

```bash
python -m procedural_world generate --quality DRAFT --max-nodes 20000 --max-triangles 300000 --max-refinements 500
```

The scheduler reserves actual generated geometry cost before committing a
proposal. Failed refiners leave the previous graph and representation intact.
Unknown Thing types receive domain-based fallback geometry. Too-small budgets
may produce coarse region masses or omit representations; every omission is
reported rather than hidden. Memory is a deterministic payload estimate, **not
a process-RSS hard limit**. Optional `--max-seconds` is a cooperative cutoff
between work units, not preemptive cancellation; it can overrun during one unit
and makes selected detail timing-dependent. Budgets unable to hold even their
selected semantic base fail with an explicit error.

Fresh worlds with identical seed, rules, constraints, time, camera, deterministic
budget and generator versions produce identical content fingerprints. Wall-clock
durations and cache hit counters are intentionally excluded. Refinement is
incremental: a World remembers committed structural detail. Repeated snapshots
may resolve additional information within a new per-run refinement allowance;
previously committed structure is not erased to satisfy a lower request. A
loaded world therefore includes its persisted commitments as part of its input.
Use fresh worlds for strict same-input benchmark comparisons.

Changing a camera does not rewrite events. Changing the year does not change
absolute-coordinate terrain. Named random streams isolate facades, interiors,
vegetation, region geography and lifecycle decisions. Generator version checks
are strict on load by default. Saved files use JSON and a content hash, never
executable pickle data. The hash detects accidental changes; it is not a digital
signature or an authentication mechanism.

## Constraints and extensions

The initial growth policy consumes NoBuildArea, ProtectedArea, ParkConstraint,
GrowthAttractor and GrowthRepulsor influences. AABB intersection/falloff is a
conservative first spatial policy, not exact polygon clipping. Constraint inputs
are immutable for an existing historical world: changing them constructs a new
world/rule realization rather than retroactively patching committed facts.

```bash
python -m procedural_world generate --constraints procedural_world/examples/constraints.json --out directed_world
```

Registries accept new semantic types, processes, event handlers, refiners and
representation providers. Domain serialization and generic fallbacks have
separate extension registries. See [the extension guide](docs/EXTENDING.md) and
`examples/custom_extension.py`, which adds a statue, plinth refinement,
weathering process, semantic event and representation without modifying the core.

The **Morpho Plants adapter is an injection boundary only**. No existing plant
implementation or documented API was supplied. `MorphoPlantsAdapter` accepts a
caller-provided function returning `GeometryBundle`; it does not pretend to
import or integrate unavailable software. `examples/plant_bridge.py` demonstrates
the contract with a bounded demo plant. Built-in trees remain usable without it.

## Tests and examples

From the directory containing `procedural_world`:

```bash
python -m unittest discover -s procedural_world/tests -v
python procedural_world/examples/generate_world.py
python procedural_world/examples/historical_comparison.py
python procedural_world/examples/custom_extension.py
```

The delivered test report records the actual executed results. Tests cover
seed isolation, all domain encodings, concave containment, transactional
refinement, event aggregate commitments, historical replacement, expansion,
serialization, forced interiors, graceful plugin failures, budget accounting,
cache isolation, exports and backend independence.

## Documentation map

- [Architecture and invariants](docs/ARCHITECTURE.md)
- [Implementation status and limitations](docs/IMPLEMENTATION_STATUS.md)
- [Extension contracts](docs/EXTENDING.md)
- [Blender workflow](docs/BLENDER.md)
- [Original supplied specification](docs/SPECIFICATION.md)
- [References and verification](docs/REFERENCES.md)

Code license: MIT. The supplied specification is preserved as user-provided
source material; the code license does not assert ownership over that document.
