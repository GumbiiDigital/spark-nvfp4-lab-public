# Spark NVFP4 Lab

I maintain this as a local experiment record for NVFP4 quantization and inference workflows. The private source baseline is d1f5bf0. It contains the SOP, shell pipeline, evaluation/performance/quantization helpers, release fixtures, security notes, and tests.

## What I built

1. Provenance-first quantization and serving workflow.
2. Separate scripts for quantization, performance, evaluation, serving, and pipeline orchestration.
3. Release fixtures for BF16 and NVFP4 evaluation, performance, and quantization manifests.
4. A rendered experiment card and shell test for repeatable reporting.
5. Security guidance and outside-review hooks.
6. A methodology treating memory, speed, quality, and reliability as separate gates.

## Recorded results

| Observation | Source evidence | Status |
|---|---|---|
| Baseline d1f5bf0 | private HEAD | Historical |
| BF16 and NVFP4 result records exist as release fixtures | tests/fixtures/release-sample | Structural fixture |
| Quantization, performance, evaluation, serving, and pipeline scripts are tracked | scripts/ | Historical inventory |
| SOP records unified-memory accounting and release planning lessons | source SOP history | Historical |
| Report rendering and release fixture tests are tracked | tests and CI | Source-backed check |

Fixtures establish record shape; they are not presented as live benchmark claims.

## Why it matters

A smaller artifact is not automatically better. Quantization can change memory, throughput, quality, startup, and reliability in different directions.

## Engineering approach

Runs start with provenance and controlled intent, separate warmup from measurement, compare baseline and candidate, record quality and reliability, and publish limitations. Unknown remains valid.

## Sanitized architecture boundary

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Repository map

- [docs/CASE-STUDY.md](docs/CASE-STUDY.md)
- [docs/NVFP4-EXPERIMENT-RECORD.md](docs/NVFP4-EXPERIMENT-RECORD.md)
- [docs/PUBLICATION-SAFETY.md](docs/PUBLICATION-SAFETY.md)
- [examples/synthetic-benchmark-record.json](examples/synthetic-benchmark-record.json)

## Evidence rules and limits

Statements above are historical or structural. This public interface ships no model, quantized artifact, private path, live benchmark, or deployment status. Current performance requires a fresh, provenance-backed run.
