# Exact Tested Build Delta

This directory preserves the exact historical candidate build used for the
measured reproduction.

## Files

- `Dockerfile`: rebuilds the pinned vLLM extension from the exact v18-vision
  base-image digest.
- `CMakeLists.sm121-nvfp4.patch`: adds CUDA 13 `12.1` support and restores the
  `12.0f` SM12x FP4 family guard.

## Build

```bash
docker buildx build \
  --platform linux/arm64 \
  --target artifact \
  --output type=local,dest=./candidate-artifact \
  -f reproduction/Dockerfile \
  reproduction
```

The expected historical extension hash is:

```text
7a64f63055f1dc7f33fd83682ae6183d403e24567dad5d9177a23c594c9a5536
```

The artifact must contain native `sm_121` entries. A matching build is still
only a build receipt; run the semantic validation before trusting NVFP4 KV
output.

## Current upstream path

For a maintained public image and recipe, use
[ciprianveg/gb10-glm-5.2 v18.1-vision](https://github.com/ciprianveg/gb10-glm-5.2/tree/master/v18-vision).

This historical Dockerfile is retained to make the measured candidate
auditable, not to replace the upstream production path.
