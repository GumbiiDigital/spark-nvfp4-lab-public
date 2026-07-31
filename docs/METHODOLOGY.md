# Methodology

## Evidence states

I treated the campaign as nine separate proof states:

1. source and build intent;
2. native cubin inventory;
3. all-rank startup geometry;
4. deterministic and vision semantics;
5. long-context retrieval;
6. near-edge capacity;
7. content-selected performance;
8. fresh mixed-load stability;
9. rollback and restoration.

An earlier state never substituted for a later one.

## Deterministic text

Four requests used different repeated cache salts, temperature zero, thinking
disabled, and an exact expected answer. Acceptance required four exact outputs.

## Vision

The harness generates an 800x500 PNG with one bright-green square centered at
`(630,145)`. It asks for compact JSON coordinates and asserts both axes within
35 pixels.

The fixture and prompt are generated in code. No human visual judgment is used
for the pass/fail result.

## Needle matrix

The matrix constructs deterministic natural filler at three context depths:
50K, 200K, and 500K. The unique hidden key appears at the front, middle, or
end, producing nine cases.

Each request must:

- contain the key exactly once in the prompt;
- return HTTP 200;
- report the expected server prompt-token count;
- return the exact key with no extra text.

## Near-1M capacity

The capacity request targets the configured one-million-token edge with a
middle-position key and a unique repeated cache salt. The accepted server
receipt contained 999,913 prompt tokens.

The difference from exactly one million is chat-template overhead and the
required generation budget. The request was inside the configured 1M sequence
limit and exercised virtually the full prompt capacity.

## Performance

### Workload

- prompt: 2,048 tokens including chat overhead;
- generation: exactly 1,500 output tokens;
- temperature: zero;
- EOS: ignored;
- cache control: unique repeated salt per request;
- prompt mode: orchid continuation;
- warmup: one excluded request;
- single stream: three measured requests;
- concurrency: synchronized groups c1 through c8.

### Rates

Standalone decode rate:

```text
output tokens / (stream completion time - first nonempty token time)
```

Aggregate concurrency rate:

```text
sum of output tokens / client wall time for the synchronized group
```

The two rates answer different questions and are not interchanged.

### MTP acceptance

The harness snapshots vLLM speculative counters before and after the accepted
benchmark. Mean acceptance length is:

```text
1 + accepted draft tokens / draft cycles
```

The accepted orchid scout measured 3.9485 tokens including the target token.

## Stability

The soak runs two short-request workers for 3,600 seconds. It schedules deep
semantic requests at 0, 600, 1,200, 1,800, 2,400, and 3,000 seconds with
depths 50K, 200K, 500K, 50K, 200K, and 500K.

The run remains active until every scheduled deep request finishes. That is why
the accepted campaign lasted longer than one hour.

Acceptance requires:

- zero short-request failures;
- six exact deep answers;
- verified prompt-token counts;
- exactly one key occurrence per deep prompt;
- no runtime guard or fatal guard;
- no unrecovered queued traffic after the final injection.

## Campaign integrity

- One owner controls each attempt.
- Duplicate owners are rejected before traffic.
- Every prompt is cache-distinct.
- Imported same-profile receipts are hash-verified.
- Contaminated or interrupted runs are archived separately.
- Rollback remains part of completion, not an afterthought.
