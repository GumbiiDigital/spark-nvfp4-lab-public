# Rebuild only the vLLM extension in the exact production image. The running
# service is not used as a build environment and remains untouched.
ARG BASE_IMAGE=ghcr.io/ciprianveg/gb10-glm-5.2@sha256:61ae08ffe856ed639adf6ce36eb8d7d8284d8ab0e4fbbf015a2a672751504721
FROM ${BASE_IMAGE} AS builder

USER root
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG BUILD_JOBS=4
ENV MAX_JOBS=${BUILD_JOBS} \
    VLLM_MAX_JOBS=${BUILD_JOBS} \
    CMAKE_BUILD_PARALLEL_LEVEL=${BUILD_JOBS} \
    NVCC_THREADS=1 \
    TORCH_CUDA_ARCH_LIST=12.1a \
    VLLM_TARGET_DEVICE=cuda \
    VLLM_VERSION_OVERRIDE=0.11.2.dev280+gilded.gnosis.v18.vllm264bce1.b12xbc85ef3.fi801d57a.cu132.20260718 \
    UV_LINK_MODE=copy

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    install -m 0755 /root/.local/bin/uv /usr/local/bin/uv && \
    uv --version

RUN cp -a /opt/vllm /work-vllm && rm -rf /work-vllm/build
COPY CMakeLists.sm121-nvfp4.patch /tmp/CMakeLists.sm121-nvfp4.patch
RUN patch -d /work-vllm -p1 --forward < /tmp/CMakeLists.sm121-nvfp4.patch && \
    grep -F 'CUDA_SUPPORTED_ARCHS "7.5;8.0;8.6;8.7;8.9;9.0;10.0;11.0;12.0;12.1"' /work-vllm/CMakeLists.txt && \
    grep -F 'FP4_SM120_ARCHS "12.0f"' /work-vllm/CMakeLists.txt

RUN uv pip install \
      --python /opt/venv/bin/python \
      --no-build-isolation \
      --no-deps \
      --reinstall \
      --verbose \
      /work-vllm

RUN set -eu; \
    artifact_so="$(find /opt/venv/lib/python3.12/site-packages/vllm -maxdepth 1 -type f -name '_C_stable_libtorch*.so' -print -quit)"; \
    test -n "${artifact_so}"; \
    mkdir -p /artifact; \
    cp -a "${artifact_so}" /artifact/; \
    cp /work-vllm/CMakeLists.txt /artifact/CMakeLists.patched.txt; \
    cp /tmp/CMakeLists.sm121-nvfp4.patch /artifact/; \
    sha256sum /artifact/_C_stable_libtorch*.so > /artifact/SHA256SUMS; \
    cuobjdump --list-elf /artifact/_C_stable_libtorch*.so > /artifact/cuobjdump-list-elf.txt; \
    grep -q 'sm_121' /artifact/cuobjdump-list-elf.txt

FROM scratch AS artifact
COPY --from=builder /artifact/ /artifact/
