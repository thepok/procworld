# Sources and verification

## User-provided design basis

`SPECIFICATION.md` is a verbatim copy of the supplied **Hierarchical Procedural
World System**, sections 1–78. It is the design basis, including its distinction
between initial implementations and future modules. No external city dataset,
existing plant code or pre-existing repository was attached.

## External API references

The Blender legacy installation workflow was checked against the official manual:

- https://docs.blender.org/manual/en/latest/editors/preferences/addons.html
- https://docs.blender.org/manual/en/latest/advanced/scripting/addon_tutorial.html

Relevant official API references for local runtime verification:

- https://docs.blender.org/api/current/bpy.types.Mesh.html
- https://docs.blender.org/api/current/bpy.types.Object.html
- https://docs.blender.org/api/current/bpy.props.html
- https://docs.blender.org/api/current/bpy.types.NodeTreeInterface.html

Direct retrieval of some current API pages failed in the authoring environment.
No third-party Blender implementation was copied, and no claim is made that the
adapter was runtime-tested. Its target interfaces are isolated from the tested
standard-library core, and `examples/blender_smoke_test.py` provides a concrete
acceptance test for a Blender installation.

## Reproducibility record

See `TEST_REPORT.md` for the actual commands, Python version, tests and smoke
runs executed before packaging. Test timing is machine-dependent and is not a
performance guarantee. The code uses no network services, API keys, telemetry,
downloaded assets or third-party runtime libraries.
