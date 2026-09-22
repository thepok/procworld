# Blender workflow

## Installation

The archive is a legacy add-on layout with one top-level `procedural_world`
package. In Blender, open **Edit → Preferences → Add-ons**, use **Install from
Disk**, select the delivered ZIP, and enable **Hierarchical Procedural World**.
This is not a hosted Blender Extensions manifest/package.

The code targets the Blender 4.2+ Python API. No Blender executable was available
in the authoring environment, so runtime compatibility is not claimed as tested.
The ordinary Python package and tests do not require Blender. The supplied
`examples/blender_smoke_test.py` is the executable runtime verification path.

## Basic scene

Open the 3D Viewport sidebar with `N`, then **World Gen**. Choose **Add WorldRoot**.
The root is placed at the 3D cursor. Generated objects are parented to it; absolute
semantic coordinates are local to that world placement. Unit scale and an
unrotated root are the simplest setup. A copied WorldRoot must have a distinct
root identifier before independent regeneration; use **Add WorldRoot** for
multiple worlds instead of duplicating its custom ID properties.

Choose a seed, year and budget. Seed 12 demonstrates a settlement near the local
origin. An ocean seed is allowed to remain ocean. Choose a camera or leave it
unset for the core's default camera importance estimate. Camera framing,
lighting, world background and the render engine remain yours to configure.
The smoke test includes an example camera and sun.

Core radius/halo choose the materialized domain. "Center Core on Camera Focus"
approximates a ground intersection from the selected camera; otherwise Core X/Y
are explicit local world coordinates. Requested region dimensions do not alter
the latent geography.

Generate a snapshot. The owner-tagged output collection contains category
collections for terrain, water, roads, buildings, vegetation, props and optional
debug geometry. A failed regeneration should retain the previous output because
the adapter builds a staging collection first. Unrelated user objects are not
purged; when found in an output collection being replaced, they are relinked to
the scene. Intentional edits to generated meshes will be replaced on regeneration.

## Geometry and interiors

"Geometry Nodes Instances" batches repeated prototypes on point geometry with
per-point scale/rotation and semantic-ID metadata. If constructing a node setup
fails, that batch is expanded into mesh geometry and a warning is stored.
Uncheck this option to use mesh batching directly while diagnosing node issues.
This fallback covers construction exceptions, not every possible silent runtime
node-evaluation problem; use the supplied smoke test and inspect the viewport.

Structure and geometry requests are independent. Structure 1 can create floors
while exterior geometry remains a mass. Structure 2 allows rooms/circulation,
and 3 allows furniture proxies. "Interior Cutaway" realizes the generated
interiors and omits the obstructing exterior mass where floors are available.
It is a diagnostic cutaway, not engineered architecture or automatic window
visibility. Budget priorities may leave a building unrefined; force its semantic
ID or use a more generous budget to expose it.

## Constraints

The constraint menu creates an editable Empty for NoBuildArea, ProtectedArea,
ParkConstraint, GrowthAttractor or GrowthRepulsor. Move/scale it and edit strength,
falloff and active interval in the panel. End year 0 means no end. Constraint
objects are separate from the generated output and survive regeneration.
The current implementation uses a conservative XY bounding box for object
constraints. Non-axis-aligned/concave clipping is not performed.

Constraint JSON Text and Override JSON Text refer to **Blender Text Editor block
names**, not filesystem paths. Example records are in `examples/constraints.json`.
Changing the terrain/rule/constraint input creates a new semantic world
realization; it does not rewrite previously committed history in place.

## Semantic inspection

The backend retains face-domain or point-domain `pw_semantic_index` attributes
and a per-batch semantic-ID table. Select a generated batch, select a face or an
instance point in Edit Mode, then inspect. The inspector also accepts IDs and
provides parent/child navigation. A complete JSON inspection text block includes
semantic state, provenance, commitments, refinement state and source events.
Point-instance picking is deliberately simple: clicking an evaluated visible
instance is not guaranteed to resolve its exact source point. Use point selection
or a known semantic ID for unambiguous inspection.

Auto/Never/Detailed controls write node overrides. A generic Detailed override
can ask for a capability a particular type does not have; this appears as an
unmet minimum in the report rather than bypassing budgets or inventing geometry.
Never-refine does not erase already committed structure.

Debug modes provide domain outlines, age, development-pressure or semantic-type
color overlays, capped by remaining triangle/instance allowance. They are basic
inspection aids, not every overlay suggested in the roadmap. Overlay geometry
is auxiliary; its use is not included in the semantic scheduler's reported
refinement count.

## Persistence

"Store Semantic World in .blend" writes versioned world JSON to an owner-tagged
Text block. This is separate from generated meshes. Save/load buttons work with
the World JSON filesystem path, including Blender's `//` relative path syntax.
A snapshot report is always written to a Text block. Event history is reusable
across cameras and years; the runtime cache is not required for persistence.

Loading an external world restores its constraint and override text records.
Existing constraint objects for that root are detached from its active constraint
set so they are not accidentally applied twice. They are not deleted.

## Troubleshooting and acceptance

Run the Blender smoke test in a disposable file. Confirm add-on registration,
visible terrain/buildings, evaluated instances, regeneration safety and the saved
`.blend` file. The headless test package's pass count does not substitute for
these Blender checks.

For an empty ocean viewport, try seed 12, a camera looking toward the root, and a
reasonable far clipping plane. For missing near detail, check the numerical
budget report, force the appropriate semantic ID, and distinguish Structure from
Geometry. For external plant problems, the stock proxies work without a plugin.
For version mismatch errors, register matching providers or start a new WorldRoot
instead of silently discarding old commitments.
