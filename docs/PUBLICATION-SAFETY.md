# Publication Safety

## Purpose

I publish the NVFP4 experiment method, not private artifacts, measurements, or deployment details.

## Allowed

- Synthetic artifact provenance.
- Original benchmark and comparison schemas.
- Qualitative outcomes.
- General controls, quality gates, and reliability fields.
- Clear unknowns and limitations.

## Excluded

- Model files, quantized artifacts, private paths, endpoints, accounts, or credentials.
- Raw telemetry, logs, benchmark outputs, and identifying measurements.
- Hardware identity, private topology, and service inventory.
- Claims that a synthetic benchmark ran.
- Third-party content copied without permission.

## Project-specific review

Every record must separate provenance, baseline, candidate, controlled variables, warmup, measurement, quality, reliability, and limitations. A speed or memory claim cannot stand in for the complete comparison.

## Gate

The checker validates JSON, required files, Mermaid-only architecture, and common private-data patterns. CI runs the same check. Technical review is required before any future result claim.
