# Case study: a benchmark is a comparison contract

## Actual problem

The private lab had scripts for quantization, evaluation, performance, serving, and pipeline orchestration. Without a common record, a fast result could hide a quality regression, memory-accounting error, or unreliable startup.

## Source-backed sequence

1. The SOP established a local-first reproducible method.
2. Memory accounting was corrected for unified memory rather than relying on an unsupported field.
3. Release planning and card rendering were added around BF16/NVFP4 fixtures.
4. CI and shell tests check the reporting path.
5. The lab remains experimental; a fixture is not a measured claim.

## Failed hypotheses

- One throughput number answers suitability: false.
- Free-memory reporting can be assumed portable: false.
- A quantized artifact is successful without provenance and quality checks: false.

## Bounded tests and acceptance gates

The source defines provenance, controlled variables, warmup/measurement separation, quality, reliability, and publication limits. Public validation checks only public JSON, Markdown, and privacy boundaries.

## Result

The durable result is a repeatable comparison contract with explicit unknowns. Performance and quality remain workload-specific.
