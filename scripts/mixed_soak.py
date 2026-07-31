#!/usr/bin/env python3
"""Sixty-minute mixed short load with six semantic deep-context injections."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request

from transformers import PreTrainedTokenizerFast

from needle_matrix import build_prompt


INJECTION_DEPTHS = (50_000, 200_000, 500_000, 50_000, 200_000, 500_000)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--tokenizer-file", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--duration", type=int, default=3600)
    parser.add_argument("--short-concurrency", type=int, default=2)
    parser.add_argument("--short-pacing", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--run-salt", default="default")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    progress = args.output_dir / "mixed-soak-progress.jsonl"
    tokenizer = PreTrainedTokenizerFast(tokenizer_file=args.tokenizer_file)
    lock = threading.Lock()
    started = time.monotonic()
    stop_at = started + args.duration
    short_counter = 0
    short_rows: list[dict] = []
    injection_rows: list[dict] = []

    def append(kind: str, row: dict) -> None:
        encoded = json.dumps({"kind": kind, **row}, sort_keys=True)
        with lock:
            with progress.open("a", encoding="utf-8") as stream:
                stream.write(encoded + "\n")
                stream.flush()

    def post(payload: dict, timeout: float) -> tuple[int | None, dict | None, str | None, float]:
        request = urllib.request.Request(
            f"{args.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        request_started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, json.loads(response.read()), None, time.perf_counter() - request_started
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return None, None, f"{type(exc).__name__}: {exc}", time.perf_counter() - request_started

    def short_worker(worker_id: int) -> None:
        nonlocal short_counter
        while time.monotonic() < stop_at:
            with lock:
                request_id = short_counter
                short_counter += 1
            expected = f"SOAK-{worker_id}-{request_id}"
            payload = {
                "model": args.model,
                "messages": [{"role": "user", "content": (
                    f"Cache salt short-{worker_id}-{request_id}. Reply with exactly {expected}."
                )}],
                "temperature": 0,
                "max_tokens": 64,
                "chat_template_kwargs": {
                    "clear_thinking": True,
                    "enable_thinking": False,
                },
            }
            status, body, error, latency = post(payload, 900)
            message = (((body or {}).get("choices") or [{}])[0].get("message") or {})
            answer = (message.get("content") or "").strip()
            row = {
                "worker": worker_id,
                "request_id": request_id,
                "elapsed_s": time.monotonic() - started,
                "status": status,
                "error": error,
                "latency_s": latency,
                "usage": (body or {}).get("usage"),
                "expected": expected,
                "answer": answer[:160],
                "pass": status == 200 and error is None and answer == expected,
            }
            short_rows.append(row)
            append("short", row)
            remaining = args.short_pacing - latency
            if remaining > 0:
                time.sleep(remaining)

    def injection(index: int, depth: int, content: str, local_tokens: int, key: str) -> dict:
        payload = {
            "model": args.model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "max_tokens": 64,
            "chat_template_kwargs": {
                "clear_thinking": True,
                "enable_thinking": False,
            },
        }
        status, body, error, latency = post(payload, args.timeout)
        message = (((body or {}).get("choices") or [{}])[0].get("message") or {})
        answer = (message.get("content") or "").strip()
        usage = (body or {}).get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens")
        prompt_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        key_occurrences = content.count(key)
        prompt_tokens_verified = bool(
            isinstance(prompt_tokens, int)
            and local_tokens <= prompt_tokens <= local_tokens + 512
            and abs(prompt_tokens - depth) <= 512
        )
        row = {
            "index": index,
            "depth": depth,
            "scheduled_s": index * (args.duration / len(INJECTION_DEPTHS)),
            "finished_elapsed_s": time.monotonic() - started,
            "status": status,
            "error": error,
            "latency_s": latency,
            "local_content_tokens": local_tokens,
            "prompt_utf8_sha256": prompt_sha256,
            "verification_key_occurrences": key_occurrences,
            "usage": usage,
            "prompt_tokens_verified": prompt_tokens_verified,
            "expected": key,
            "answer": answer,
            "response_body": body,
            "pass": (
                status == 200
                and error is None
                and answer == key
                and prompt_tokens_verified
                and key_occurrences == 1
            ),
        }
        injection_rows.append(row)
        append("injection", row)
        return row

    injection_futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.short_concurrency + 6) as pool:
        short_futures = [pool.submit(short_worker, i) for i in range(args.short_concurrency)]
        for index, depth in enumerate(INJECTION_DEPTHS):
            scheduled = started + index * (args.duration / len(INJECTION_DEPTHS))
            while time.monotonic() < scheduled:
                time.sleep(min(1.0, scheduled - time.monotonic()))
            salt = (
                f"mixed-soak-injection-{index}-{depth}-"
                f"20260730-natural-hidden-key-{args.run_salt}"
            )
            key = f"SOAK-ORCHID-{index}-{depth // 1000}K"
            content, local_tokens = build_prompt(tokenizer, depth, "middle", salt, key)
            injection_futures.append(pool.submit(injection, index, depth, content, local_tokens, key))
        for future in short_futures:
            future.result()
        for future in injection_futures:
            future.result()

    short_rows.sort(key=lambda row: row["request_id"])
    injection_rows.sort(key=lambda row: row["index"])
    result = {
        "requested_duration_s": args.duration,
        "actual_duration_s": time.monotonic() - started,
        "short_concurrency": args.short_concurrency,
        "short_pacing_s": args.short_pacing,
        "run_salt": args.run_salt,
        "short": {
            "requests": len(short_rows),
            "passes": sum(1 for row in short_rows if row["pass"]),
            "failures": sum(1 for row in short_rows if not row["pass"]),
        },
        "injections": injection_rows,
        "pass": all(row["pass"] for row in short_rows) and len(injection_rows) == 6 and all(row["pass"] for row in injection_rows),
    }
    (args.output_dir / "mixed-soak-result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
