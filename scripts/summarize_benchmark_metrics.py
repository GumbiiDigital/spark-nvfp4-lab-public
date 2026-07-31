#!/usr/bin/env python3
"""Summarize speculative counter deltas and the c1/c8 benchmark endpoints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


BASES = (
    "vllm:spec_decode_num_drafts_total",
    "vllm:spec_decode_num_draft_tokens_total",
    "vllm:spec_decode_num_accepted_tokens_total",
)


def parse_metrics(path: Path) -> dict[str, float]:
    values: dict[str, float] = {name: 0.0 for name in BASES}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        name, value = line.rsplit(" ", 1)
        base = name.split("{", 1)[0]
        if base in values:
            values[base] += float(value)
        if base == "vllm:spec_decode_num_accepted_tokens_per_pos_total":
            position = name.split('position="', 1)[1].split('"', 1)[0]
            key = f"accepted_position_{position}"
            values[key] = values.get(key, 0.0) + float(value)
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    before = parse_metrics(args.before)
    after = parse_metrics(args.after)
    delta = {
        key: after.get(key, 0.0) - before.get(key, 0.0)
        for key in sorted(set(before) | set(after))
    }
    benchmark = json.loads(args.benchmark.read_text(encoding="utf-8"))
    assert benchmark.get("complete") is True and benchmark.get("pass") is True
    assert benchmark["definition"]["prompt_mode"] == "orchid_continuation"
    sweep = {row["concurrency"]: row for row in benchmark["concurrency_sweep"]}
    drafts = delta["vllm:spec_decode_num_drafts_total"]
    accepted = delta["vllm:spec_decode_num_accepted_tokens_total"]
    draft_tokens = delta["vllm:spec_decode_num_draft_tokens_total"]
    result = {
        "prompt_mode": "orchid_continuation",
        "source_post_prompt_known": False,
        "single_stream_rates_tok_s": benchmark["single_summary"]["rates"],
        "single_stream_median_tok_s": benchmark["single_summary"]["median"],
        "single_stream_spread_pct": benchmark["single_summary"]["spread_pct"],
        "aggregate_c1_tok_s": sweep[1]["aggregate_output_tok_s"],
        "aggregate_c8_tok_s": sweep[8]["aggregate_output_tok_s"],
        "speculative_metrics_delta": delta,
        "accepted_draft_tokens_per_draft": accepted / drafts if drafts else None,
        "mean_acceptance_length_including_target_token": (
            1.0 + accepted / drafts if drafts else None
        ),
        "draft_token_acceptance_rate": accepted / draft_tokens if draft_tokens else None,
        "complete": True,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
