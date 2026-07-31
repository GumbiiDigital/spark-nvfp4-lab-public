# QA Evidence

## Public artifact hashes

| Artifact | SHA-256 |
| --- | --- |
| Tested vLLM extension | `7a64f63055f1dc7f33fd83682ae6183d403e24567dad5d9177a23c594c9a5536` |
| Retained private evidence archive manifest | `c36955af2c89c3864dda247966bfd9d2f3190ad88a7379d8b33c3dd3242eea16` |
| Local final reproduction report | `23d2cff9607a7bad5d169c659769f2fb38d3bf517a40bba9eaa455c0b7d298e7` |

The compiled extension and raw archive are not distributed by this repository.
The hashes bind this public record to the privately retained tested bytes.

## Accepted counts

| Evidence | Count |
| --- | ---: |
| Candidate ranks with matching extension hash and arguments | 8/8 |
| Deterministic text passes | 4/4 |
| Needle passes | 9/9 |
| Near-1M prompt tokens | 999,913 |
| Short soak requests | 1,484/1,484 |
| Deep soak injections | 6/6 |
| Accepted archive files | 296 |
| Writable files in sealed archive | 0 |
| Post-rollback orchestration-state rows matching baseline | 16/16 |

## Public validation gates

Before publication, the repository must pass:

1. JSON parsing and measured-summary schema validation;
2. Python syntax compilation for every published harness;
3. privacy and secret-pattern scanning;
4. exact-case local Markdown-link validation;
5. external source-link validation;
6. publication-manifest verification;
7. Git diff whitespace validation;
8. a clean staged-file review;
9. live default-branch and raw-file verification after merge.

## Evidence separation

The public measured JSON is an aggregate derivative. It is not a raw log. The
private archive contains per-rank receipts, request results, controller logs,
guards, and rollback evidence under its own immutable manifest.
