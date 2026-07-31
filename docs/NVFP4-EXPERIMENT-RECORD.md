# NVFP4 Experiment Record

## Target

- Eight NVIDIA GB10 systems.
- Tensor parallel size 8.
- Text weights: `QuantTrio/GLM-5.2-Int4-Int8Mix`.
- Vision tower: `baseten/GLM-5.2-Vision-NVFP4`.
- B12X sparse MLA attention.
- MTP enabled.
- `nvfp4_ds_mla` KV cache.
- 1,000,000 maximum model length.
- 46,817,928,192 KV bytes per rank.
- Maximum sequences 8.
- Maximum batched tokens 2,048.
- CUDA graph capture sizes 1, 2, 4, and 8.

The composite vision target was served with the matching text checkpoint in
the speculative configuration. The vision config nests its MTP layer count
under `text_config`; the text config exposes it at the level expected by the
pinned speculative loader.

## Build receipt

| Field | Measured value |
| --- | --- |
| vLLM source | `264bce1da81e27d638e7cf265b4cbd125d023c38` |
| CUDA | 13.2.1 |
| Driver | 580.159.03 |
| Candidate extension SHA-256 | `7a64f63055f1dc7f33fd83682ae6183d403e24567dad5d9177a23c594c9a5536` |
| `sm_121a` cubins | 63 |
| `sm_120` cubins | 0 |
| KV dtype | `nvfp4_ds_mla` |
| KV record stride | 432 bytes |
| KV pool | 1,264,256 tokens |
| Nominal 1M concurrency | 1.26x |

## Correctness receipt

| Test | Result |
| --- | --- |
| Deterministic exact text | 4/4 |
| 50K needles | 3/3 |
| 200K needles | 3/3 |
| 500K needles | 3/3 |
| Near-1M semantic request | 999,913 prompt tokens, exact key |
| Vision coordinate | accepted result `(600,125)` against `(630,145)`, 35-pixel tolerance |

The vision fixture is not described as deterministic. Across unchanged
historical retries, five requests returned `(600,125)` and three returned
`(600,250)`.

## Performance receipt

The benchmark used a 2,048-token prompt including chat overhead, 1,500 forced
output tokens, a unique cache salt per request, one excluded warmup, three
single-stream measurements, and a synchronized c1-c8 sweep.

| Measurement | Result |
| --- | ---: |
| Single-stream decode trials | 48.6099, 51.4122, 53.7813 tok/s |
| Single-stream median | 51.4122 tok/s |
| Single-stream spread | 10.0870% |
| c1 aggregate client-wall rate | 45.9823 tok/s |
| c8 aggregate client-wall rate | 115.7500 tok/s |
| Orchid acceptance length, including target token | 3.9485 |

The c1 aggregate rate includes request wall time. The standalone decode trials
start timing at the first nonempty streamed token. Those are different rate
definitions and are intentionally kept separate.

## Stability receipt

- Requested duration: 3,600 seconds.
- Actual duration: 3,814.93 seconds.
- Short-request concurrency: 2.
- Short requests: 1,484/1,484 passed.
- Deep injections: 6/6 passed.
- Injection order: 50K, 200K, 500K, 50K, 200K, 500K.
- Prompt tokens: 49,912; 199,912; 499,912; 49,912; 199,912; 499,912.
- Runtime request failures: zero.
- Runtime fatal-guard events: zero.

## Evidence boundary

The accepted receipts came from unchanged exact-profile attempts using the
same container family, candidate extension hash, model geometry, and NVFP4
path. Correctness/capacity, performance, and the final fresh soak were
collected in separate bounded maintenance windows. They are same-profile
immutable receipts, not one uninterrupted server lifetime.

The retained private archive manifest SHA-256 is
`c36955af2c89c3864dda247966bfd9d2f3190ad88a7379d8b33c3dd3242eea16`.
