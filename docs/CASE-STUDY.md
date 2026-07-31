# Case Study: Reproducing the 1M-Context NVFP4 Result

## The target

Light Foundry reported GLM-5.2-Vision serving on eight GB10 systems with a
1,000,000-token context window, a 1,264,256-token NVFP4 KV pool, about 44 tok/s
single-stream throughput, and 118 tok/s aggregate at eight concurrent
requests.

I wanted to know whether the result was repeatable on my cluster, why several
DGX Spark builds had deliberately disabled the FP4 path, and whether the
quantized KV read path remained semantically correct under long context.

## Why startup was not enough

The build could succeed while the relevant source block was skipped. The
packing kernel could exist while the attention read path failed. A server
could return HTTP 200 while the cache produced the wrong answer.

I split the work into separate gates:

1. native build inventory;
2. exact startup geometry;
3. deterministic text;
4. programmatically asserted vision;
5. front/middle/end retrieval through 500K;
6. a separate near-1M semantic request;
7. frozen performance measurement;
8. a fresh 60-minute mixed-load soak;
9. rollback and baseline restoration.

No later gate was inferred from an earlier one.

## Build diagnosis

The pinned CUDA 13 build contained two independent blockers.

The supported-architecture list contained `12.0` but not `12.1`. That meant a
requested `12.1a` target was intersected before the downstream FP4 family
guard had a chance to match it.

The image also replaced the normal `12.0f` FP4 family guard with `99.0f`.
Because that architecture does not exist, the FP4 SM12x block was skipped.

The working candidate changed both values and built with
`TORCH_CUDA_ARCH_LIST=12.1a`. `cuobjdump --list-elf` then reported 63
`sm_121a` entries and zero `sm_120` entries.

I applied the two corrections together. This record therefore does not claim
that changing the supported-architecture list alone fixes every downstream
fork.

## Early failures

The first exact-profile startup reached the expected pool but emitted NVIDIA
memory-allocation events before any request. The frozen safety contract treated
those events as fatal, so that attempt rolled back without claiming semantic
or performance success.

A matched FP8 control later produced the same loading-time driver signature.
That weakened the hypothesis that the event was specific to NVFP4 attention.
The final contract separated startup-only advisories from any event occurring
after engine readiness, while retaining an independent runtime memory floor.

Other failed attempts exposed different problems:

- duplicate long-context traffic contaminated a performance run and triggered
  the memory guard;
- an over-conservative 3.5% admission floor rejected an otherwise exact
  profile near 3.44%;
- the vision coordinate response alternated between an accepted row and a
  vertically displaced row under the same fixture;
- one ownership collision was rejected before validation traffic instead of
  being blended into the campaign.

Each invalid run was frozen and archived. None contributed results to the
accepted run.

## Exact capacity

The accepted server reserved 46,817,928,192 KV bytes on every rank and
reported:

```text
GPU KV cache size: 1,264,256 tokens
Maximum concurrency for 1,000,000 tokens per request: 1.26x
```

That concurrency number is the pool divided by maximum sequence length. It is
not a throughput result.

The near-edge request contained 999,913 server-counted prompt tokens and
returned the exact hidden key after 1,863.24 seconds. That is the semantic
capacity receipt.

## Performance

Prompt content changed MTP acceptance enough to move decode performance. I
measured candidate prompts first, selected the orchid continuation shape, then
froze it.

The accepted benchmark used one warmup, three standalone single-stream trials,
and a synchronized c1-c8 sweep. Every request used a unique repeated salt and
generated exactly 1,500 tokens.

The c1 aggregate result was 45.9823 tok/s. The c8 aggregate result was 115.7500
tok/s. Both land in the original report's band.

The exact source prompt from the original report is unknown. That limitation
stays attached to the result.

## Fresh stability run

The final run began with fresh deterministic text and hash-verified the
same-profile capacity, needle, vision, and performance receipts. It then ran a
new 3,600-second mixed workload.

Two short-request workers completed 1,484 requests without failure. Six deep
requests were injected at 50K, 200K, and 500K twice. Every deep request
returned the exact expected key and verified its server prompt-token count.

The final 500K request completed after the nominal hour boundary, so the actual
run lasted 3,814.93 seconds.

No permanent rank stall, NCCL wait, request failure, CUDA event, Linux OOM
kill, cache-drop event, or runtime guard occurred in the accepted soak.

## Rollback

The campaign ended through the same controller that launched it. The cluster
returned to the pinned FP8 baseline, the protected supporting services were
restored, and every pre-maintenance orchestration-service state matched its
post-rollback state.

The full private archive was made read-only and checksum-verified. The public
record retains its manifest hash without publishing operational identities or
raw logs.

## Result

The geometry, capacity, semantic text path, c1/c8 performance band, and fresh
60-minute stability result were reproduced.

The first-request crash from vLLM issue #43562 was not reproduced on this
pinned B12X MLA path. The vision path operated, but its coordinate output was
bimodal and is not presented as deterministic.
