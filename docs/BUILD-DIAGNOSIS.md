# Build Diagnosis

## Pinned environment

| Component | Value |
| --- | --- |
| Hardware target | NVIDIA GB10, SM121, aarch64 |
| CUDA | 13.2.1 |
| Driver | 580.159.03 |
| vLLM | `264bce1da81e27d638e7cf265b4cbd125d023c38` |
| Build target | `TORCH_CUDA_ARCH_LIST=12.1a` |
| Base image | pinned v18-vision digest in `reproduction/Dockerfile` |

## Blocker 1: CUDA 13 support list

The CUDA 13 branch declared:

```cmake
set(CUDA_SUPPORTED_ARCHS "7.5;8.0;8.6;8.7;8.9;9.0;10.0;11.0;12.0")
```

The CUDA 12.8/12.9 branch already included `12.1`. The CUDA 13 branch did not.
The requested `12.1a` target was therefore clamped during the supported-target
intersection.

The tested correction appends `12.1`.

## Blocker 2: impossible FP4 family guard

The pinned image used:

```cmake
cuda_archs_loose_intersection(FP4_SM120_ARCHS "99.0f" "${CUDA_ARCHS}")
```

`99.0f` cannot match a real target, so the entire SM12x FP4 block is skipped.
The tested correction restores `12.0f`.

The `f` suffix is a family target. Once the requested architecture survives
the supported-architecture intersection, `12.0f` can resolve the SM12x family
to `12.1a`.

## Exact patch

See [the tested CMake patch](../reproduction/CMakeLists.sm121-nvfp4.patch).

The build gates the output with:

```text
candidate SHA-256  7a64f63055f1dc7f33fd83682ae6183d403e24567dad5d9177a23c594c9a5536
sm_121a entries    63
sm_120 entries     0
```

That proves native candidate inventory. It does not by itself prove request
correctness; the semantic gates are separate.

## Vision/MTP path

The composite target used the public QuantTrio text checkpoint and Baseten
vision tower. In the pinned loader, the text checkpoint exposes
`num_nextn_predict_layers` at the expected config level, while the vision
checkpoint nests it under `text_config`.

Using the vision checkpoint as the speculative-model path failed before weight
loading. The accepted configuration kept the vision target and supplied the
matching text checkpoint to speculative decoding. This was a configuration
schema issue, not an NVFP4 kernel failure.

## Upstream context

vLLM PR [#38126](https://github.com/vllm-project/vllm/pull/38126) fixed SM121
guard and loose-intersection handling upstream. The remaining gap in this
pinned downstream image was the CUDA 13 supported list plus its deliberate
`99.0f` rewrite.

The public [ciprianveg v18.1-vision path](https://github.com/ciprianveg/gb10-glm-5.2/tree/master/v18-vision)
now implements the same Light Foundry approach and preserves the vision
overlay while replacing rebuilt extensions.

## What this diagnosis does not claim

- It does not claim every vLLM revision needs this patch.
- It does not claim `12.1` alone is sufficient in a fork that still uses
  `99.0f`.
- It does not resolve whether an older `sm_120`-only build used compatible
  SASS or PTX JIT on GB10.
- It does not modify CUDA or NVIDIA libraries.
