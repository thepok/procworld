# Executed verification report

Date: 2026-09-22

Environment: CPython 3.13.5, Linux x86_64.
The tests and command-line application use the Python standard library only.

## Unit and integration tests

Command, executed from the directory containing the package:

```bash
python -m unittest discover -s procedural_world/tests -v
```

**Result: 74 tests passed, 0 failures, 0 errors.**
Recorded duration in this environment: 15.144 seconds. This is not a timing
promise for other machines. The raw test output is included below.

## Additional executed checks

- All package Python files compile successfully with `compileall`.
- `python -m procedural_world generate --out full_smoke` completed with the
  default settings: 7,135 snapshot semantic records, 4,451 active nodes,
  564 represented nodes, 16,740 triangles, 120 successful refinements,
  no refinement errors and no omitted representations.
- `examples/generate_world.py` completed: 257 represented nodes, 176,024 triangles,
  600 refinements, within its DRAFT budget.
- `examples/historical_comparison.py` completed for 1780, 1850, 1930 and 2025.
- `examples/custom_extension.py` completed and asserted that its registered
  semantic event and plinth refinement were present in the snapshot.
- A wheel built and installed using the delivered `pyproject.toml` with
  `pip install --no-deps --no-build-isolation --target <temporary-directory>`.
  Importing the installed package outside the source tree and running
  `python -m procedural_world --version` returned `1.0.0`.
- The delivered archive excludes bytecode, build directories, wheel/install
  products, generated demo output, virtual environments and external assets.

## Not executed / not claimed

No Blender executable was installed in the authoring environment. Blender UI
registration, Geometry Nodes evaluation, scene rendering and the supplied
`examples/blender_smoke_test.py` were **not** runtime-tested. The Blender Python
source was compile-checked only.

No existing Morpho Plants source/API was supplied. The delivered plant bridge
is an explicit callback integration contract and demo, not a completed external
software integration. Envelope validation and failure fallback are tested with
a deliberately invalid adapter.

No benchmark of millions of nodes, hard process-RSS limit, real city dataset,
photorealistic renderer or physically accurate hydrology was performed.

## Raw test output

```text
test_all_domains_have_fallback (test_core.DomainTests.test_all_domains_have_fallback) ... ok
test_commitment_does_not_alias_source_value (test_core.DomainTests.test_commitment_does_not_alias_source_value) ... ok
test_concave_containment_rejects_crossing_edge (test_core.DomainTests.test_concave_containment_rejects_crossing_edge) ... ok
test_concave_triangulation_preserves_area (test_core.DomainTests.test_concave_triangulation_preserves_area) ... ok
test_conflicting_builtin_prototype_is_rejected (test_core.DomainTests.test_conflicting_builtin_prototype_is_rejected) ... ok
test_degenerate_network_still_renders (test_core.DomainTests.test_degenerate_network_still_renders) ... ok
test_invalid_shapes_rejected (test_core.DomainTests.test_invalid_shapes_rejected) ... ok
test_roundtrip_every_domain (test_core.DomainTests.test_roundtrip_every_domain) ... ok
test_vertical_curve_fallback (test_core.DomainTests.test_vertical_curve_fallback) ... ok
test_volume_contains (test_core.DomainTests.test_volume_contains) ... ok
test_bad_aggregate_rejected (test_core.EventTests.test_bad_aggregate_rejected) ... ok
test_before_birth_is_absent (test_core.EventTests.test_before_birth_is_absent) ... ok
test_coarse_event_totals_preserved (test_core.EventTests.test_coarse_event_totals_preserved) ... ok
test_collision_batch_is_atomic (test_core.EventTests.test_collision_batch_is_atomic) ... ok
test_event_idempotence (test_core.EventTests.test_event_idempotence) ... ok
test_refined_event_stays_inside_interval (test_core.EventTests.test_refined_event_stays_inside_interval) ... ok
test_replay_order_independent (test_core.EventTests.test_replay_order_independent) ... ok
test_unknown_event_is_not_silently_lost (test_core.EventTests.test_unknown_event_is_not_silently_lost) ... ok
test_child_cannot_predate_parent (test_core.GraphTests.test_child_cannot_predate_parent) ... ok
test_commitments_apply_to_events (test_core.GraphTests.test_commitments_apply_to_events) ... ok
test_conflicting_refinement_is_atomic (test_core.GraphTests.test_conflicting_refinement_is_atomic) ... ok
test_cycles_rejected_on_load (test_core.GraphTests.test_cycles_rejected_on_load) ... ok
test_destruction_cascades (test_core.GraphTests.test_destruction_cascades) ... ok
test_escaping_child_is_atomic (test_core.GraphTests.test_escaping_child_is_atomic) ... ok
test_four_independent_dimensions (test_core.GraphTests.test_four_independent_dimensions) ... ok
test_graph_roundtrip (test_core.GraphTests.test_graph_roundtrip) ... ok
test_refinement_is_additive (test_core.GraphTests.test_refinement_is_additive) ... ok
test_scope_constraints_and_seed_propagate (test_core.GraphTests.test_scope_constraints_and_seed_propagate) ... ok
test_specialization_does_not_create_structure (test_core.GraphTests.test_specialization_does_not_create_structure) ... ok
test_canonical_mapping_order (test_core.SeedTests.test_canonical_mapping_order) ... ok
test_identity_is_not_geometry (test_core.SeedTests.test_identity_is_not_geometry) ... ok
test_namespaces_are_isolated (test_core.SeedTests.test_namespaces_are_isolated) ... ok
test_nan_is_rejected (test_core.SeedTests.test_nan_is_rejected) ... ok
test_random_bounds (test_core.SeedTests.test_random_bounds) ... ok
test_repeatability (test_core.SeedTests.test_repeatability) ... ok
test_budget_reservations (test_world.BudgetCacheTests.test_budget_reservations) ... ok
test_cache_mutation_isolation (test_world.BudgetCacheTests.test_cache_mutation_isolation) ... ok
test_dependency_transitive_invalidation (test_world.BudgetCacheTests.test_dependency_transitive_invalidation) ... ok
test_invalid_costs_rejected (test_world.BudgetCacheTests.test_invalid_costs_rejected) ... ok
test_lru_is_bounded (test_world.BudgetCacheTests.test_lru_is_bounded) ... ok
test_overrides_validate_conflicts (test_world.BudgetCacheTests.test_overrides_validate_conflicts) ... ok
test_expansion_cannot_change_fields (test_world.FieldTests.test_expansion_cannot_change_fields) ... ok
test_field_repeatability (test_world.FieldTests.test_field_repeatability) ... ok
test_negative_coordinate_continuity (test_world.FieldTests.test_negative_coordinate_continuity) ... ok
test_normal_is_unit (test_world.FieldTests.test_normal_is_unit) ... ok
test_ocean_is_not_forced_to_be_a_city (test_world.FieldTests.test_ocean_is_not_forced_to_be_a_city) ... ok
test_atomic_file_save_load (test_world.SerializationTests.test_atomic_file_save_load) ... ok
test_generator_version_mismatch (test_world.SerializationTests.test_generator_version_mismatch) ... ok
test_geometry_is_not_persisted (test_world.SerializationTests.test_geometry_is_not_persisted) ... ok
test_roundtrip (test_world.SerializationTests.test_roundtrip) ... ok
test_tampering_rejected (test_world.SerializationTests.test_tampering_rejected) ... ok
test_camera_does_not_change_history (test_world.SnapshotTests.test_camera_does_not_change_history) ... ok
test_core_has_no_blender_dependency (test_world.SnapshotTests.test_core_has_no_blender_dependency) ... ok
test_exports_are_real_files (test_world.SnapshotTests.test_exports_are_real_files) ... ok
test_external_plant_envelope_failure_retains_previous_geometry (test_world.SnapshotTests.test_external_plant_envelope_failure_retains_previous_geometry) ... ok
test_failing_refiner_cannot_mutate_authoritative_node (test_world.SnapshotTests.test_failing_refiner_cannot_mutate_authoritative_node) ... ok
test_fresh_world_determinism (test_world.SnapshotTests.test_fresh_world_determinism) ... ok
test_future_history_does_not_consume_past_semantic_budget (test_world.SnapshotTests.test_future_history_does_not_consume_past_semantic_budget) ... ok
test_geometry_budget_is_never_exceeded (test_world.SnapshotTests.test_geometry_budget_is_never_exceeded) ... ok
test_global_manual_events_are_included_in_snapshots (test_world.SnapshotTests.test_global_manual_events_are_included_in_snapshots) ... ok
test_interior_refinement_and_serialization (test_world.SnapshotTests.test_interior_refinement_and_serialization) ... ok
test_missing_provider_still_renders (test_world.SnapshotTests.test_missing_provider_still_renders) ... ok
test_terrain_cache_survives_year_change (test_world.SnapshotTests.test_terrain_cache_survives_year_change) ... ok
test_tiny_node_budget_degrades_to_context (test_world.SnapshotTests.test_tiny_node_budget_degrades_to_context) ... ok
test_active_buildings_respect_lifetimes (test_world.WorldHistoryTests.test_active_buildings_respect_lifetimes) ... ok
test_event_aggregate_matches_initial_construction (test_world.WorldHistoryTests.test_event_aggregate_matches_initial_construction) ... ok
test_historical_replay_matches_fresh_world (test_world.WorldHistoryTests.test_historical_replay_matches_fresh_world) ... ok
test_no_build_constraint (test_world.WorldHistoryTests.test_no_build_constraint) ... ok
test_parent_domains_contain_generated_children (test_world.WorldHistoryTests.test_parent_domains_contain_generated_children) ... ok
test_prefix_history_is_stable (test_world.WorldHistoryTests.test_prefix_history_is_stable) ... ok
test_region_expansion_preserves_existing_events (test_world.WorldHistoryTests.test_region_expansion_preserves_existing_events) ... ok
test_replacement_keeps_parcel_identity (test_world.WorldHistoryTests.test_replacement_keeps_parcel_identity) ... ok
test_road_topology_has_persistent_endpoints (test_world.WorldHistoryTests.test_road_topology_has_persistent_endpoints) ... ok
test_settlement_and_roads_exist (test_world.WorldHistoryTests.test_settlement_and_roads_exist) ... ok

----------------------------------------------------------------------
Ran 74 tests in 15.144s

OK
```
