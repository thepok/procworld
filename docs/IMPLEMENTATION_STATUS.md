# Implementation status

This is a complete runnable **first-version reference package**, not an assertion
that every long-term feature in the supplied specification is already finished.
The original source distinguishes initial systems from future refinement systems.
The following matrix makes the implementation boundaries explicit.

| Specification areas | Delivered behavior | Boundary / future work |
|---|---|---|
| 1–13, 18, 42 | Generic Thing/Process graph; semantic specialization; four refinement axes; eight finite/unbounded domain forms; Scope; named seeds; deterministic IDs; additive transactions | Data records are Python objects, not a packed million-node store |
| 14–17, 19–22 | Process evaluation; registered Event handlers; deterministic replay; interval/aggregate event-refinement validation; initial development pressure/accessibility fields | Urban policy is a simple connected grid frontier; no realistic economics, agents, traffic equilibrium or coupled infrastructure simulator |
| 23–26, 49, 51 | Multi-scale height, climate/moisture/geology/biome/suitability fields; ocean surfaces; downhill rivers and coarse sink lakes; canonical cells; context halo | No erosion, global watershed/flow accumulation, coastline triangulation, river-bed carving or physical lake flooding; owner-source rivers can be incomplete beyond a not-yet-materialized owner region |
| 27–31, 57–59 | Projected camera importance; best-first scheduler; explicit budgets; cheap context masses; four independent requests; forced controls; reusable snapshots | Frustum/bounding-sphere approximation only; no true occlusion, reflection, shadow or depth-of-field solver; repeated snapshots can incrementally add committed structure |
| 32–34, 50, 52–54 | Historical establishment, roads, blocks, parcel subdivision, broad land use, construction, aging calculation, renovation, demolition/replacement, parks | Building extensions, parcel merges/resubdivision, sophisticated street topology and explicit engineering are not implemented |
| 35–39, 55 | Compositional building/forest refiners; polygon-prism building footprints; L/T/U/stepped/chamfered massing; edge-based facade openings; Floors, Rooms, Corridor, VerticalCore, FurnitureProxy; forest mass -> trees; bounded demo plants | No fully engineered architecture, stairs/doors-between-every-room connectivity, furnished production assets or photoreal materials |
| 36, 37, 73 phase 10 | MorphoPlantsAdapter callback contract, environment/age/seed requests, envelope validation, failure fallback | **Actual Morpho Plants integration is not present** because no existing implementation/API was attached |
| 40–46, 72 | Refiner/provider registries, process/event registries, domain readers/fallback registry, bounded cache, transitive dependency tags, implementation versions | No automatic code-change dependency analysis or disk geometry-cache database |
| 47–48 | Active-time influence fields; NoBuild/Protected/Park constraints; growth attraction/repulsion; manual semantic Things | Exact polygon clipping, automatic landmark ingestion and every suggested constraint specialization are not implemented |
| 60–65 | Backend-neutral Mesh/Instance layer; OBJ/MTL/SVG/JSON exports; optional Blender WorldRoot/UI; category/material batching; Geometry Nodes instancing with mesh fallback; owner-safe replacement; basic overlays/inspection/navigation | **Blender runtime was not available for authoring tests.** Supplied add-on is compile-checked and includes a Blender smoke test, but installation, UI, node evaluation and rendering need runtime verification |
| 66–70 | Atomic versioned JSON save/load, content hash, persisted events/settings/constraints/committed structure/overrides, deterministic tests, failure injection tests | Hash is an integrity checksum, not authentication. Strict migration across changed generator versions is not implemented |
| 71–78 | Modular architecture, executable extension example, documentation, valid fallback-first output and honest feature boundaries | Large production scenes, full historical behavioral refinement, physically plausible hydrology and full plant software are future providers |

## Important operational distinctions

**Historical correctness here means internal consistency**, not a simulation of a
specific real city or evidence-based reconstruction. Construction events generate
the visible state; the resulting grid still is deliberately simplistic.

**Historical event refinement is a validated API**, while the initial city
process emits detailed construction events directly. The temporal refiner exposes
those events per node. A fully lazy coarse-to-fine historical simulator is future
work, not silently claimed by this package.

**Behavioral refinement currently resolves policy detail**, while the
`behavioral_level` setting selects the initial evaluator's policy. New future
behavior may be supplied through a registered Process/refiner, but changing a
past world's policy is not a license to contradict committed events.

**Canonical field sampling is expansion-consistent.** Different geometric detail
levels approximate that same field differently. Terrain skirts hide coarse/fine
boundary cracks; they do not make different tessellations mathematically
identical between samples.

**The renderer and semantic graph have separate budgets.** Node accounting covers
the instantiated snapshot graph, including historical records in that view.
Derived event logs and caches consume additional host memory. Triangle accounting
includes the expanded cost of instances, not merely each prototype once.

**A missing generator is not fatal; insufficient resources can still omit output.**
Failure reports make both situations explicit. Source completeness means the
package contains its implemented modules and executable examples; it does not
mean all future phases of the supplied roadmap have been achieved.
