# Spark NVFP4 Lab Public

I built this repository to document a reproducible method for NVFP4 experimentation without publishing private artifacts or pretending that one benchmark answers every deployment question. The method tracks provenance, quantization intent, benchmark controls, quality, speed, memory, and reliability as separate evidence.

## What I built

The public framework covers:

- source artifact provenance;
- explicit quantization configuration;
- immutable experiment intent;
- warmup and measurement separation;
- baseline and candidate comparison;
- memory, speed, quality, and reliability dimensions;
- failure and retry accounting; and
- result publication with known limits.

## Why it matters

A smaller or faster artifact is not automatically better. Quantization can change memory use, startup behavior, throughput, output quality, numerical stability, and operational reliability in different ways.

I want every comparison to state what was held constant and what remains unproven.

## Engineering approach

Each experiment record includes provenance class, synthetic artifact identity, method intent, workload class, controlled variables, qualitative comparison fields, quality gates, reliability observations, and limitations.

The public example uses qualitative outcomes instead of private operational measurements. It is a schema demonstration, not a benchmark claim.

## Synthetic public-safe architecture

The diagram shows the experiment pipeline from provenance through review using only synthetic artifacts.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Representative work and artifacts

- [Case study](docs/CASE-STUDY.md) - designing a comparison that does not hide tradeoffs.
- [Synthetic benchmark record](examples/synthetic-benchmark-record.json) - a provenance and comparison schema.
- [Publication safety](docs/PUBLICATION-SAFETY.md) - artifact and result boundary.
- [Share copy](docs/SHARE.md) - concise public narrative.
- [Safety checker](scripts/check_publication_safety.py) - repository privacy gate.

## Evidence and lessons

The public evidence is structural: original methodology, valid synthetic JSON, explicit comparison dimensions, a synthetic diagram, and automated privacy checks. No performance or quality result is claimed.

The central lesson is that benchmark reproducibility depends on provenance and controls as much as it depends on the measured value.

## Repository map

| Path | Purpose |
|---|---|
| README.md | Experiment framework and limits |
| docs/CASE-STUDY.md | Comparison-method case study |
| docs/ARCHITECTURE.md | Synthetic Mermaid experiment flow |
| docs/PUBLICATION-SAFETY.md | Publication rules |
| docs/SHARE.md | Share-ready copy |
| examples/ | Synthetic benchmark JSON |
| scripts/check_publication_safety.py | Privacy and structure checker |
| .github/workflows/publication-safety.yml | CI gate |

## Publication boundary

This is a public project interface, not an operational benchmark repository. I exclude live addresses, hostnames, hardware identities, accounts, local paths, credentials, model locations, raw telemetry, private artifacts, service inventories, private topology, equipment maps, and operational commands. Examples are synthetic and do not reproduce a live environment.

## Limitations

This repository does not ship models, quantized artifacts, benchmark outputs, private measurements, or deployment status. The example does not prove NVFP4 compatibility, speed, memory savings, quality, or reliability on a particular system.
