#!/usr/bin/env python3
"""Four cache-distinct exact-output probes for deterministic text correctness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    expected = "NVFP4-ORCHID-47"
    rows = []
    for attempt in range(4):
        salt = f"deterministic-20260729-{attempt}"
        payload = {
            "model": args.model,
            "messages": [{
                "role": "user",
                "content": (
                    f"Private cache salt: {salt}. Reply with exactly {expected}. "
                    "Do not add punctuation, explanation, or whitespace."
                ),
            }],
            "temperature": 0,
            "max_tokens": 64,
            # This deployed GLM template emits an opening <think> unless
            # enable_thinking is explicitly false.  A 64-token correctness
            # probe must spend its budget on the asserted answer, not hidden
            # reasoning_content.
            "chat_template_kwargs": {
                "clear_thinking": True,
                "enable_thinking": False,
            },
        }
        request = urllib.request.Request(
            f"{args.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        started = time.perf_counter()
        with urllib.request.urlopen(request, timeout=900) as response:
            body = json.loads(response.read())
            status = response.status
        message = ((body.get("choices") or [{}])[0].get("message") or {})
        content = (message.get("content") or "").strip()
        reasoning = (
            message.get("reasoning_content")
            or message.get("reasoning")
            or ""
        ).strip()
        rows.append({
            "attempt": attempt,
            "salt": salt,
            "status": status,
            "content": content,
            "reasoning_preview": reasoning[:240],
            "usage": body.get("usage"),
            "latency_s": time.perf_counter() - started,
            "pass": status == 200 and content == expected,
        })
    result = {"expected": expected, "runs": rows, "pass": all(r["pass"] for r in rows)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
