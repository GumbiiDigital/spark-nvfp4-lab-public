# GLM-5.2-Vision NVFP4 on Eight DGX Sparks

I reproduced Light Foundry's 1M-context GLM-5.2-Vision NVFP4 result on my
eight-system NVIDIA GB10 cluster.

The final profile reached the exact KV geometry from the original report:

- `1,000,000` maximum context;
- `1,264,256` KV-cache tokens;
- `1.26x` nominal concurrency for a 1M-token request;
- `kv_gmem_stride=432` with `nvfp4_ds_mla`;
- 63 native `sm_121a` cubins and zero `sm_120` cubins;
- `45.98 tok/s` at concurrency 1;
- `115.75 tok/s` aggregate at concurrency 8;
- a fresh 63.6-minute mixed-load stability run with no request failures.

The measurements and engineering conclusions are real. Raw fleet logs,
hostnames, addresses, service inventory, boot identifiers, controller state,
and operational paths remain private.

The composite serving stack used
[QuantTrio/GLM-5.2-Int4-Int8Mix](https://huggingface.co/QuantTrio/GLM-5.2-Int4-Int8Mix)
for the text weights and
[baseten/GLM-5.2-Vision-NVFP4](https://huggingface.co/baseten/GLM-5.2-Vision-NVFP4)
for the vision tower.

## Final result

| Measurement | Light Foundry report | My measured result |
| --- | ---: | ---: |
| Maximum context | 1,000,000 | 1,000,000 |
| KV pool | 1,264,256 tokens | 1,264,256 tokens |
| Nominal 1M concurrency | 1.26x | 1.26x |
| KV record stride | 432 bytes | 432 bytes |
| Concurrency 1 | about 44 tok/s | 45.9823 tok/s |
| Concurrency 8 | 118 tok/s | 115.7500 tok/s |

The c1 result is 4.5% above the reported band and the c8 result is 1.9%
below it. That is a match inside the original report's warning that
single-run comparisons within roughly 10% are mostly MTP-acceptance noise.

The original benchmark prompt and exact rate formula were not published. My
throughput comparison uses a frozen 2,048-token orchid-continuation prompt,
1,500 forced output tokens, unique salts, one excluded warmup, and client-wall
aggregate throughput. This is a comparable reproduction, not a byte-identical
benchmark replay.

## Correctness and stability

| Gate | Result |
| --- | --- |
| Deterministic text | 4/4 exact outputs |
| Needle retrieval | 9/9 at 50K, 200K, and 500K; front, middle, and end |
| Near-1M semantic request | 999,913 prompt tokens; exact hidden key returned |
| Vision coordinate request | Passed within 35 pixels, with bimodality disclosed below |
| Fresh mixed-load soak | 3,814.93 seconds |
| Short requests during soak | 1,484/1,484 passed |
| Deep injections during soak | 6/6 at 50K, 200K, and 500K |
| Runtime failures | zero request, CUDA, NCCL, Xid, OOM-kill, or rank-stall failures |

The long soak used two continuously paced short-request workers and six
scheduled semantic injections. Every deep request returned its exact key,
reported the expected server-side prompt-token count, and contained the key
exactly once.

## What was actually broken

This was a build-configuration problem in the pinned image, not a missing
SM121 kernel-family concept.

Two gates disabled the native path:

1. the CUDA 13 supported-architecture list ended at `12.0`, so a requested
   `12.1a` target was clamped before the family match could run;
2. the image changed `FP4_SM120_ARCHS` from `12.0f` to the impossible value
   `99.0f`, which skipped the FP4 SM12x block.

I restored `12.0f`, added `12.1`, and rebuilt with
`TORCH_CUDA_ARCH_LIST=12.1a`. The resulting extension contained 63
`sm_121a` entries and no `sm_120` entries.

The exact tested patch and build are in [reproduction/](reproduction/).
Ciprian's upstream repository now ships a native-SM121 `v18.1-vision` path
that follows the same Light Foundry fix.

## The vision/MTP configuration gotcha

The text checkpoint exposes `num_nextn_predict_layers` at its top level. The
vision checkpoint nests that field under `text_config`. Supplying the vision
checkpoint as the speculative model produced an unsupported-MTP error before
weights loaded.

The accepted server loaded the composite vision target while pointing the
speculative configuration at the matching text checkpoint. The public model
identifiers are listed above; no private model path is required to understand
the correction.

## What NVFP4 buys

The density improvement is about `1.52x`, not 2x:

```text
FP8 stride    656 bytes
NVFP4 stride  432 bytes
656 / 432     1.5185x
```

The BF16 RoPE block remains uncompressed. Halving only the quantized portion
does not halve the complete KV record.

For this exact profile, reserving `46,817,928,192` KV bytes per rank produced
the measured 1,264,256-token pool.

## The stability concern was real

vLLM issue
[#43562](https://github.com/vllm-project/vllm/issues/43562) documented an
SM120 first-request failure in the NVFP4 attention read path. Compiling the
packing kernel would not have been enough; every accepted campaign had to
exercise the read path and prove semantic output.

I did not reproduce that first-request failure on this pinned B12X MLA path.
I did encounter other failures that mattered:

- startup-only NVIDIA memory-allocation advisories appeared during model
  loading, including under the FP8 control. They did not recur after readiness
  in the accepted run;
- one earlier run was contaminated by a duplicate long-context workload and
  correctly terminated through the memory guard;
- a 3.5% admission-memory floor was too strict for the exact 1.26M pool and
  caused false starts; 3.3% admitted the known-good profile while the 1.0%
  runtime guard remained intact;
- the unchanged vision coordinate fixture was bimodal. Five historical runs
  returned `(600,125)` and three returned `(600,250)`. The vision path worked,
  but I do not claim deterministic coordinate output.

Failures are part of this record. They are not blended into the accepted run
or removed to make the final number look cleaner.

## Repository map

| Path | Contents |
| --- | --- |
| [docs/CASE-STUDY.md](docs/CASE-STUDY.md) | Full engineering sequence, failed hypotheses, and corrections |
| [docs/BUILD-DIAGNOSIS.md](docs/BUILD-DIAGNOSIS.md) | CUDA 13 and SM121 build diagnosis |
| [docs/METHODOLOGY.md](docs/METHODOLOGY.md) | Frozen prompts, rates, correctness gates, and soak design |
| [docs/ACCEPTANCE-MATRIX.md](docs/ACCEPTANCE-MATRIX.md) | Claim-by-claim verdict and evidence tier |
| [docs/QA-EVIDENCE.md](docs/QA-EVIDENCE.md) | Public hashes, counts, and accepted receipts |
| [docs/NVFP4-EXPERIMENT-RECORD.md](docs/NVFP4-EXPERIMENT-RECORD.md) | Concise measured record |
| [examples/glm52-nvfp4-measured-summary.json](examples/glm52-nvfp4-measured-summary.json) | Machine-readable public result |
| [reproduction/](reproduction/) | Exact tested Dockerfile and CMake patch |
| [scripts/](scripts/) | Sanitized correctness, capacity, throughput, and soak harnesses |
| [docs/X-POST.md](docs/X-POST.md) | X-ready source copy with credits and caveats |

## How I treat evidence

- Startup geometry is not semantic correctness.
- An HTTP 200 is not a correct long-context answer.
- A successful write kernel is not proof that the KV read path works.
- A one-off throughput result is not a stable hardware constant.
- Capacity and performance remain separate evidence tracks.
- An interrupted or contaminated attempt never becomes part of the accepted
  campaign.
- Unknown remains unknown.

## Publication boundary

Measured results are allowed here. The old repository rule that prohibited
measurements was a temporary portfolio-safety restriction, not a GitHub or
project requirement. It has been removed.

Public measurements must still be aggregate, receipt-backed, historically
labeled, and stripped of operational identity. The private evidence archive
retains the full logs and per-host receipts under an immutable checksum
manifest. This public repository publishes the result, method, exact build
delta, sanitized harnesses, and source-archive hashes.

See [Publication Safety](docs/PUBLICATION-SAFETY.md) for the enforced boundary.

## Credits and scope

- [Light Foundry's original post](https://x.com/light_foundry/status/2082302264480579891)
  established the target and build diagnosis I independently tested.
- [ciprianveg/gb10-glm-5.2](https://github.com/ciprianveg/gb10-glm-5.2)
  supplied the v18-vision base and now includes a public native-SM121 NVFP4
  path.
- [vLLM PR #38126](https://github.com/vllm-project/vllm/pull/38126)
  fixed the upstream SM121 guard/intersection logic.
- [QuantTrio/GLM-5.2-Int4-Int8Mix](https://huggingface.co/QuantTrio/GLM-5.2-Int4-Int8Mix)
  and [baseten/GLM-5.2-Vision-NVFP4](https://huggingface.co/baseten/GLM-5.2-Vision-NVFP4)
  are external checkpoints and are not redistributed here.

This is an independently maintained Gumbii Digital engineering record. It is
not an NVIDIA, Z.ai, vLLM, Light Foundry, or ciprianveg endorsement.

No model weights, CUDA libraries, NVIDIA libraries, compiled extensions, or
container images are redistributed here.

## License

Gumbii Digital's original code, documentation, examples, data, diagrams, and
media are available under the [MIT License](LICENSE). Third-party components,
assets, product names, and trademarks retain their respective terms; see
[COPYRIGHT.md](COPYRIGHT.md) for scope.
