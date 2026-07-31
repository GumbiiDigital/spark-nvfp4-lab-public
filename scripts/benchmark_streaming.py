#!/usr/bin/env python3
"""Cache-distinct pp2048/tg1500 single and concurrency streaming benchmark."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import statistics
import threading
import time

import requests
from transformers import PreTrainedTokenizerFast


def content_tokens(tokenizer: PreTrainedTokenizerFast, text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))


def build_prompt(
    tokenizer: PreTrainedTokenizerFast,
    salt: str,
    target: int = 2041,
    mode: str = "technical_survey",
) -> str:
    if mode == "technical_survey":
        suffix = (
            "\nWrite a detailed technical survey of distributed inference. Continue "
            "until the server's token limit; do not stop early."
        )
        unit = f" [{salt}] evidence-backed systems observation."
    elif mode == "orchid_continuation":
        suffix = (
            f"\nUnique request salt: {salt}. Continue the demonstrated pattern. "
            "Output ORCHID-47 followed by a space repeatedly. Do not add commentary. "
            "Continue until the server's token limit."
        )
        unit = f" ORCHID-47 [{salt}]"
    else:
        raise ValueError(f"unsupported prompt mode: {mode}")
    unit_ids = tokenizer.encode(unit, add_special_tokens=False)
    repeats = max(1, (target - content_tokens(tokenizer, suffix)) // len(unit_ids))
    prompt = unit * repeats + suffix
    while content_tokens(tokenizer, prompt) < target:
        prompt = " x" + prompt
    return prompt


def one_request(
    base_url: str,
    model: str,
    tokenizer: PreTrainedTokenizerFast,
    salt: str,
    max_tokens: int,
    timeout: float,
    prompt_mode: str,
) -> dict:
    prompt = build_prompt(tokenizer, salt, mode=prompt_mode)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "min_tokens": max_tokens,
        "ignore_eos": True,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {
            "clear_thinking": True,
            "enable_thinking": False,
        },
    }
    started = time.perf_counter()
    first = None
    last = None
    usage = None
    pieces = 0
    with requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        json=payload,
        stream=True,
        timeout=(30, timeout),
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
            if event.get("usage"):
                usage = event["usage"]
            choices = event.get("choices") or []
            if choices:
                delta = choices[0].get("delta") or {}
                if delta.get("content") or delta.get("reasoning") or delta.get("reasoning_content"):
                    now = time.perf_counter()
                    first = first or now
                    last = now
                    pieces += 1
    ended = time.perf_counter()
    prompt_tokens = int((usage or {}).get("prompt_tokens") or 0)
    output_tokens = int((usage or {}).get("completion_tokens") or 0)
    local_tokens = content_tokens(tokenizer, prompt)
    decode_elapsed = None if first is None else max(ended - first, 1e-9)
    return {
        "salt": salt,
        "status": status,
        "local_content_tokens": local_tokens,
        "prompt_utf8_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "stream_events_with_text": pieces,
        "ttft_s": None if first is None else first - started,
        "latency_s": ended - started,
        "decode_elapsed_s": decode_elapsed,
        "decode_tok_s": None if decode_elapsed is None else output_tokens / decode_elapsed,
        "pass": (
            status == 200
            and output_tokens == max_tokens
            and local_tokens <= prompt_tokens <= local_tokens + 512
        ),
    }


def run_group(args, tokenizer, concurrency: int, label: str) -> dict:
    barrier = threading.Barrier(concurrency)

    def worker(index: int) -> dict:
        barrier.wait()
        return one_request(
            args.base_url,
            args.model,
            tokenizer,
            f"{label}-c{concurrency}-r{index}",
            args.max_tokens,
            args.timeout,
            args.prompt_mode,
        )

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        rows = list(pool.map(worker, range(concurrency)))
    elapsed = time.perf_counter() - started
    total_output = sum(row["output_tokens"] for row in rows)
    return {
        "concurrency": concurrency,
        "wall_s": elapsed,
        "total_output_tokens": total_output,
        "aggregate_output_tok_s": total_output / elapsed,
        "requests": rows,
        "pass": all(row["pass"] for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--tokenizer-file", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-tokens", type=int, default=1500)
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument(
        "--prompt-mode",
        choices=("technical_survey", "orchid_continuation"),
        default="technical_survey",
    )
    args = parser.parse_args()
    tokenizer = PreTrainedTokenizerFast(tokenizer_file=args.tokenizer_file)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    definition = {
        "prompt_shape": "approximately 2,048 tokens including chat overhead",
        "generation_shape": args.max_tokens,
        "single_rate": "completion_tokens / (stream completion - first nonempty token)",
        "aggregate_rate": "sum(completion_tokens) / client wall time for synchronized group",
        "cache_control": "unique salt repeated throughout every prompt",
        "source_post_shape_known": False,
        "prompt_mode": args.prompt_mode,
    }

    def write_checkpoint(warmup: dict, singles: list[dict], sweep: list[dict], complete: bool) -> dict:
        rates = [row["decode_tok_s"] for row in singles if row["decode_tok_s"] is not None]
        result = {
            "definition": definition,
            "warmup_excluded": warmup,
            "single_measured": singles,
            "single_summary": {
                "rates": rates,
                "mean": statistics.mean(rates) if rates else None,
                "median": statistics.median(rates) if rates else None,
                "min": min(rates) if rates else None,
                "max": max(rates) if rates else None,
                "spread_pct": ((max(rates) - min(rates)) / statistics.mean(rates) * 100) if rates else None,
            },
            "concurrency_sweep": sweep,
            "complete": complete,
        }
        result["pass"] = bool(
            complete
            and warmup["pass"]
            and all(row["pass"] for row in singles)
            and all(group["pass"] for group in sweep)
        )
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return result

    warmup = one_request(
        args.base_url,
        args.model,
        tokenizer,
        "warmup-pp2048-tg1500",
        args.max_tokens,
        args.timeout,
        args.prompt_mode,
    )
    singles = []
    sweep = []
    write_checkpoint(warmup, singles, sweep, complete=False)
    for i in range(3):
        singles.append(one_request(
            args.base_url,
            args.model,
            tokenizer,
            f"single-measured-{i}",
            args.max_tokens,
            args.timeout,
            args.prompt_mode,
        ))
        write_checkpoint(warmup, singles, sweep, complete=False)
    for concurrency in range(1, 9):
        sweep.append(run_group(args, tokenizer, concurrency, "sweep"))
        write_checkpoint(warmup, singles, sweep, complete=False)
    result = write_checkpoint(warmup, singles, sweep, complete=True)
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
