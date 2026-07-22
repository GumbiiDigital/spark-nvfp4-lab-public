# Case Study: A Benchmark Is a Comparison Contract

## Context

Quantization experiments are easy to overstate. A single speed or memory result can hide changes in quality, reliability, startup, or workload shape.

## Problem

Results become hard to compare when provenance, controls, warmup, workload, retries, and quality checks are implicit.

## What I built

The public experiment contract separates:

- source artifact provenance;
- quantization method and intent;
- baseline and candidate identity;
- controlled variables;
- warmup from measurement;
- memory, speed, quality, and reliability comparisons;
- failure handling; and
- publication limitations.

## Engineering decisions

- Provenance is required before comparison.
- Baseline and candidate share the same declared workload class.
- Quality is a gate, not an afterthought.
- Reliability includes failures and retries, not only successful samples.
- Qualitative values are used in the public example to avoid publishing private measurements.
- Unknown remains an allowed result.

## Representative artifact

The synthetic benchmark record is an original, fictional comparison record. It contains provenance class, controlled variables, qualitative outcomes, quality gates, and limitations without asserting that a benchmark ran.

## Evidence available here

- The example parses as JSON.
- The record identifies itself as synthetic.
- Provenance and all comparison dimensions are explicit.
- The publication checker rejects common private-data patterns.
- CI runs the same checker.

## Lessons

The number is not the experiment. The experiment is the contract that makes the number interpretable and repeatable.

## Limitations

No model, quantized artifact, private path, benchmark output, or live measurement is included. Compatibility and performance remain unproven by this public example.
