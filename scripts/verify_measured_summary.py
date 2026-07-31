#!/usr/bin/env python3
"""Verify the frozen public GLM-5.2 NVFP4 aggregate result."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "examples" / "glm52-nvfp4-measured-summary.json"


def main() -> int:
    data = json.loads(RESULT.read_text(encoding="utf-8"))
    assert data["record_type"] == "measured_summary"
    assert data["public_safe"] is True
    assert data["historical"] is True

    build = data["build"]
    assert build["candidate_extension_sha256"] == (
        "7a64f63055f1dc7f33fd83682ae6183d403e24567dad5d9177a23c594c9a5536"
    )
    assert build["sm_121a_entries"] == 63
    assert build["sm_120_entries"] == 0

    profile = data["profile"]
    assert profile["text_checkpoint"] == "QuantTrio/GLM-5.2-Int4-Int8Mix"
    assert profile["vision_checkpoint"] == "baseten/GLM-5.2-Vision-NVFP4"
    assert profile["speculative_checkpoint_class"] == "matching text checkpoint"
    assert profile["kv_cache_dtype"] == "nvfp4_ds_mla"
    assert profile["kv_gmem_stride_bytes"] == 432
    assert profile["kv_cache_bytes_per_rank"] == 46_817_928_192
    assert profile["kv_pool_tokens"] == 1_264_256
    assert profile["max_model_len"] == 1_000_000
    assert profile["nominal_concurrency_at_max_length"] == 1.26

    correctness = data["correctness"]
    assert correctness["deterministic_text"] == {"passed": 4, "attempted": 4}
    assert correctness["needle_matrix"]["passed"] == 9
    assert correctness["needle_matrix"]["attempted"] == 9
    assert correctness["near_one_million"]["prompt_tokens"] == 999_913
    assert correctness["near_one_million"]["exact_answer_pass"] is True
    assert correctness["vision_coordinate"]["bimodality_disclosed"] is True

    performance = data["performance"]
    assert performance["source_prompt_known"] is False
    assert performance["aggregate_c1_tokens_per_second"] == 45.982288710620395
    assert performance["aggregate_c8_tokens_per_second"] == 115.75003783669834

    stability = data["stability"]
    assert stability["actual_duration_seconds"] >= 3_600
    assert stability["short_requests"] == 1_484
    assert stability["short_passes"] == 1_484
    assert stability["short_failures"] == 0
    assert stability["deep_injections_passed"] == 6
    assert stability["deep_injections_attempted"] == 6
    assert stability["runtime_guard_triggered"] is False
    assert stability["fatal_guard_triggered"] is False

    evidence = data["evidence"]
    assert evidence["private_archive_manifest_sha256"] == (
        "c36955af2c89c3864dda247966bfd9d2f3190ad88a7379d8b33c3dd3242eea16"
    )
    assert evidence["raw_evidence_published"] is False
    assert evidence["aggregate_derivative_only"] is True
    assert len(data["limitations"]) >= 3

    print("measured summary: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
