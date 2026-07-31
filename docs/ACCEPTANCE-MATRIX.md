# Acceptance Matrix

| Claim | Evidence tier | Result | Limitation |
| --- | --- | --- | --- |
| Native SM121 build | exact compiled artifact inventory | Pass: 63 `sm_121a`, zero `sm_120` | one pinned vLLM/image revision |
| NVFP4 MLA geometry | live all-rank startup receipt | Pass: stride 432 | B12X `nvfp4_ds_mla`, not generic `nvfp4` |
| 1,264,256-token KV pool | live server receipt | Pass | capacity ratio is not throughput |
| 1M configured length | live args plus semantic request | Pass | semantic request reported 999,913 prompt tokens |
| Deterministic text | four cache-distinct requests | Pass: 4/4 | one exact-output task |
| Vision path | generated coordinate fixture | Pass with caveat | coordinate output was bimodal across retries |
| Retrieval through 500K | nine semantic requests | Pass: 9/9 | one tokenizer and one filler generator |
| Near-1M correctness | streamed semantic request | Pass | one hidden-key workload |
| c1 performance band | frozen aggregate benchmark | Pass: 45.9823 tok/s | original source prompt unknown |
| c8 performance band | synchronized aggregate benchmark | Pass: 115.7500 tok/s | one prompt class and software stack |
| MTP acceptance range | vLLM counter delta | Pass: 3.9485 mean length | content dependent |
| 60-minute stability | fresh mixed-load soak | Pass: 1,484/1,484 plus 6/6 deep | not an indefinite production burn-in |
| vLLM #43562 first-request crash | repeated NVFP4 read-path requests | Not reproduced | different SM121/B12X/software path from issue reporter |
| Deterministic vision coordinates | repeated unchanged fixture | Fail | five accepted rows, three vertical misses |
| Fleet restoration | independent post-rollback audit | Pass | current live health is time-sensitive and not published as a guarantee |

## Verdict

The original report's geometry, text capacity, comparable c1/c8 performance,
and one-hour mixed-load stability are reproduced.

The exact source benchmark prompt remains unknown, and the vision coordinate
fixture remains nondeterministic. Those limits stay attached to every public
summary.
