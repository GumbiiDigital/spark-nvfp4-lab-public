#!/usr/bin/env python3
"""One cache-salted semantic request at the configured one-million-token edge."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import requests
from transformers import PreTrainedTokenizerFast

from needle_matrix import build_prompt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--tokenizer-file", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=7200)
    args = parser.parse_args()
    tokenizer = PreTrainedTokenizerFast(tokenizer_file=args.tokenizer_file)
    key = "ONE-MILLION-ORCHID-47"
    content, local_tokens = build_prompt(
        tokenizer,
        1_000_000,
        "middle",
        "one-million-capacity-20260730-natural-hidden-key",
        key,
    )
    prompt_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    key_occurrences = content.count(key)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "status": "request-prepared",
        "expected": key,
        "local_content_tokens": local_tokens,
        "prompt_utf8_sha256": prompt_sha256,
        "verification_key_occurrences": key_occurrences,
        "cache_control": "unique salt repeated throughout the full prefix",
        "complete": False,
        "pass": False,
    }, indent=2) + "\n", encoding="utf-8")
    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0,
        "max_tokens": 64,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {
            "clear_thinking": True,
            "enable_thinking": False,
        },
    }
    started = time.perf_counter()
    first = None
    output_parts = []
    reasoning_parts = []
    usage = None
    stream_events = []
    response_id = None
    finish_reason = None
    with requests.post(
        f"{args.base_url.rstrip('/')}/chat/completions",
        json=payload,
        stream=True,
        timeout=(30, args.timeout),
    ) as response:
        status = response.status_code
        response.raise_for_status()
        for raw in response.iter_lines(decode_unicode=True):
            if not raw or not raw.startswith("data: "):
                continue
            body = raw[6:]
            if body == "[DONE]":
                break
            event = json.loads(body)
            stream_events.append(event)
            response_id = event.get("id") or response_id
            if event.get("usage"):
                usage = event["usage"]
            choices = event.get("choices") or []
            if choices:
                finish_reason = choices[0].get("finish_reason") or finish_reason
                delta = choices[0].get("delta") or {}
                content_delta = delta.get("content") or ""
                reasoning_delta = delta.get("reasoning") or delta.get("reasoning_content") or ""
                if content_delta or reasoning_delta:
                    first = first or time.perf_counter()
                    output_parts.append(content_delta)
                    reasoning_parts.append(reasoning_delta)
    ended = time.perf_counter()
    answer = "".join(output_parts).strip()
    usage = usage or {}
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    passed = bool(
        status == 200
        and answer == key
        and local_tokens <= prompt_tokens <= local_tokens + 512
        and 999_000 <= prompt_tokens <= 999_936
        and prompt_tokens + completion_tokens <= 1_000_000
        and key_occurrences == 1
    )
    result = {
        "status": status,
        "expected": key,
        "answer": answer,
        "local_content_tokens": local_tokens,
        "prompt_utf8_sha256": prompt_sha256,
        "verification_key_occurrences": key_occurrences,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "ttft_s": None if first is None else first - started,
        "latency_s": ended - started,
        "prefill_tok_s": None if first is None else prompt_tokens / (first - started),
        "reasoning": "".join(reasoning_parts),
        "response_id": response_id,
        "finish_reason": finish_reason,
        "stream_events": stream_events,
        "cache_control": "unique salt repeated throughout the full prefix",
        "complete": True,
        "pass": passed,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
