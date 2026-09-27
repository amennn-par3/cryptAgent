# Schema validation scope

Schemas declare JSON Schema draft 2020-12 and use a small subset implemented by
tools/schema_check.py. The bundled validator has no third-party dependency. It is
not a general JSON Schema implementation; unsupported keywords are rejected.

Specification validation fixes the baseline scheme, profile and limits. Extensions
require a new schema/profile version. Request schema describes the initial assessment
envelope. Only assess mode is implemented by demo_backend.py; generate and repair are
reserved for later integration and are explicitly rejected by this demo.

Paths are package-relative. The demo resolves and bounds them before reading. A report
is structurally valid only after schema validation; a future policy engine must also
enforce exactly one row per requirement, evidence provenance and verdict consistency.
Do not treat JSON shape validation as evidence that security claims are true.
