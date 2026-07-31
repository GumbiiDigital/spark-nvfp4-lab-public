# Publication Safety

## The corrected rule

Measured results are allowed in this repository.

The previous blanket prohibition was a temporary restriction from the first
synthetic portfolio version. It was not a GitHub rule, an NVFP4 rule, or a
requirement from the private source repository.

The replacement rule is narrower and useful: publish sanitized measurements
when they are backed by retained receipts and when the public record states the
method, evidence tier, and limitations.

## Allowed

- Aggregate performance, capacity, duration, pass/fail, and count results.
- Exact software revisions and public artifact hashes.
- Sanitized benchmark prompts, rate definitions, and validation harnesses.
- Build patches against public upstream source.
- Failures and corrections that explain the accepted result.
- Hashes of retained private evidence archives.
- Public hardware class and cluster size when they are essential to the claim.

## Kept private

- Credentials, keys, cookies, tokens, and account internals.
- Live addresses, hostnames, remote-access paths, and physical topology.
- Hardware identifiers, boot identifiers, exact service inventory, and
  controller state.
- Local user paths and private repository URLs.
- Raw logs, raw telemetry, screenshots, and per-host receipts.
- Model files, compiled extensions, container layers, and third-party binaries.

## Evidence contract

Every measured claim must identify:

1. whether it is measured, observed, or inferred;
2. the frozen workload shape and rate definition;
3. the accepted pass/fail gate;
4. the limitation that prevents a broader claim;
5. the retained evidence hash that can be checked privately.

An interrupted, contaminated, or partial attempt cannot be merged into the
accepted campaign. Startup, correctness, capacity, performance, stability, and
rollback remain separate proof states.

## Automated gate

The checker scans Markdown, JSON, source, workflow, and text files for private
network ranges, local user paths, account identifiers, secrets, hardware IDs,
private-source links, and unreviewed images. It accepts both explicitly
synthetic examples and the single reviewed measured-summary schema.

The publication manifest covers every configured public file except itself.
