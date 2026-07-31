# X Post Source

## Main post

Got the full GLM-5.2-Vision NVFP4 result reproduced on my eight GB10 cluster.

Final result:

- 1M context
- 1,264,256-token KV pool
- 45.98 tok/s at c1
- 115.75 tok/s aggregate at c8
- 1,484/1,484 short requests during a fresh 63.6-minute soak
- 6/6 deep 50K/200K/500K injections

Native SM121 was real: 63 `sm_121a` cubins, zero `sm_120`.

The build gap was exactly where Light Foundry described it. CUDA 13 did not
include `12.1` in the supported list, and the pinned image used the impossible
`99.0f` family guard to skip the FP4 block. Restoring `12.0f`, adding `12.1`,
and rebuilding for `12.1a` opened the native NVFP4 path.

I also tried hard to make it fail.

Deterministic text passed 4/4. Needle retrieval passed 9/9 through 500K. A
999,913-token request returned the exact key. The fresh mixed soak completed
without a request failure, rank stall, NCCL wait, Xid, or OOM kill.

Two caveats:

1. The original benchmark prompt was not published, so the throughput match is
   comparable, not byte-identical.
2. The vision coordinate fixture was bimodal across retries. The vision path
   worked, but I am not calling the coordinates deterministic.

Full write-up, exact patch, measured summary, methodology, failures, and
sanitized harnesses:

https://github.com/GumbiiDigital/spark-nvfp4-lab-public

Credit to Light Foundry for the original diagnosis and target, and to ciprian
for the v18-vision base and the new public v18.1-vision path.

## Original sources

- Light Foundry: https://x.com/light_foundry/status/2082302264480579891
- ciprianveg: https://github.com/ciprianveg/gb10-glm-5.2
- vLLM SM121 fix: https://github.com/vllm-project/vllm/pull/38126
- vLLM stability issue: https://github.com/vllm-project/vllm/issues/43562
