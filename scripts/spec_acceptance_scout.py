#!/usr/bin/env python3
"""Measure content-dependent MTP acceptance and decode rate on one exact server."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import requests
from transformers import PreTrainedTokenizerFast


METRICS = (
    "vllm:spec_decode_num_drafts_total",
    "vllm:spec_decode_num_draft_tokens_total",
    "vllm:spec_decode_num_accepted_tokens_total",
)


def count_tokens(tokenizer: PreTrainedTokenizerFast, text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))


def fit_prompt(
    tokenizer: PreTrainedTokenizerFast, prefix_unit: str, instruction: str, target: int
) -> str:
    prompt = instruction
    while count_tokens(tokenizer, prefix_unit + prompt) <= target:
        prompt = prefix_unit + prompt
    while count_tokens(tokenizer, prompt) < target:
        prompt = " x" + prompt
    while count_tokens(tokenizer, prompt) > target:
        prompt = prompt[len(prefix_unit) :] if prompt.startswith(prefix_unit) else prompt[1:]
    assert count_tokens(tokenizer, prompt) == target
    return prompt


def prompts(tokenizer: PreTrainedTokenizerFast, target: int) -> dict[str, str]:
    return {
        "technical_survey": fit_prompt(
            tokenizer,
            " [SCOUT-TECH] evidence-backed systems observation.",
            "\nWrite a detailed technical survey of distributed inference. "
            "Continue until the server token limit; do not stop early.",
            target,
        ),
        "orchid_continuation": fit_prompt(
            tokenizer,
            " ORCHID-47",
            "\nContinue the exact preceding pattern only. Output ORCHID-47 followed "
            "by a space repeatedly. Do not add commentary.",
            target,
        ),
        "alphabet_cycle": fit_prompt(
            tokenizer,
            " ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "\nContinue the exact uppercase alphabet cycle with spaces between cycles. "
            "Do not add commentary.",
            target,
        ),
        "jsonl_counter": fit_prompt(
            tokenizer,
            '{"ok":true,"value":47}\n',
            "\nContinue with exactly the same minified JSON object, one object per line. "
            "Do not use a code fence or commentary.",
            target,
        ),
        "number_cycle": fit_prompt(
            tokenizer,
            " 1 2 3 4 5 6 7 8 9 10",
            "\nContinue the exact 1-through-10 number cycle separated by spaces. "
            "Do not add commentary.",
            target,
        ),
    }


def metric_snapshot(url: str) -> tuple[dict[str, float], str]:
    response = requests.get(url, timeout=(10, 30))
    response.raise_for_status()
    text = response.text
    values: dict[str, float] = {name: 0.0 for name in METRICS}
    position_values: dict[str, float] = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        name, value = line.rsplit(" ", 1)
        base = name.split("{", 1)[0]
        if base in values:
            values[base] += float(value)
        if base == "vllm:spec_decode_num_accepted_tokens_per_pos_total":
            marker = 'position="'
            position = name.split(marker, 1)[1].split('"', 1)[0]
            position_values[position] = position_values.get(position, 0.0) + float(value)
    values.update({f"accepted_position_{key}": value for key, value in position_values.items()})
    return values, text


def run_request(
    base_url: str,
    model: str,
    tokenizer: PreTrainedTokenizerFast,
    prompt: str,
    max_tokens: int,
    timeout: float,
) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "min_tokens": max_tokens,
        "ignore_eos": True,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {"clear_thinking": True, "enable_thinking": False},
    }
    started = time.perf_counter()
    first = None
    usage = None
    output_parts: list[str] = []
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
                text = (
                    delta.get("content")
                    or delta.get("reasoning")
                    or delta.get("reasoning_content")
                    or ""
                )
                if text:
                    first = first or time.perf_counter()
                    output_parts.append(text)
    ended = time.perf_counter()
    output = "".join(output_parts)
    local_prompt_tokens = count_tokens(tokenizer, prompt)
    reported_prompt_tokens = int((usage or {}).get("prompt_tokens") or 0)
    output_tokens = int((usage or {}).get("completion_tokens") or 0)
    elapsed = None if first is None else max(ended - first, 1e-9)
    return {
        "status": status,
        "prompt_tokens": reported_prompt_tokens,
        "output_tokens": output_tokens,
        "ttft_s": None if first is None else first - started,
        "latency_s": ended - started,
        "decode_elapsed_s": elapsed,
        "decode_tok_s": None if elapsed is None else output_tokens / elapsed,
        "output_utf8_sha256": hashlib.sha256(output.encode()).hexdigest(),
        "output_prefix": output[:160],
        "output_suffix": output[-160:],
        "pass": (
            status == 200
            and output_tokens == max_tokens
            and local_prompt_tokens <= reported_prompt_tokens <= local_prompt_tokens + 512
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--tokenizer-file", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prompt-content-tokens", type=int, default=2041)
    parser.add_argument("--max-tokens", type=int, default=384)
    parser.add_argument("--timeout", type=float, default=900)
    args = parser.parse_args()
    tokenizer = PreTrainedTokenizerFast(tokenizer_file=args.tokenizer_file)
    metrics_url = args.base_url.removesuffix("/v1") + "/metrics"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for name, prompt in prompts(tokenizer, args.prompt_content_tokens).items():
        before, _ = metric_snapshot(metrics_url)
        request = run_request(
            args.base_url, args.model, tokenizer, prompt, args.max_tokens, args.timeout
        )
        time.sleep(1)
        after, _ = metric_snapshot(metrics_url)
        keys = set(before) | set(after)
        delta = {key: after.get(key, 0.0) - before.get(key, 0.0) for key in sorted(keys)}
        drafts = delta.get("vllm:spec_decode_num_drafts_total", 0.0)
        accepted = delta.get("vllm:spec_decode_num_accepted_tokens_total", 0.0)
        draft_tokens = delta.get("vllm:spec_decode_num_draft_tokens_total", 0.0)
        request.update(
            {
                "name": name,
                "local_content_tokens": count_tokens(tokenizer, prompt),
                "prompt_utf8_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "metrics_delta": delta,
                "accepted_draft_tokens_per_draft": accepted / drafts if drafts else None,
                "mean_acceptance_length_including_target_token": (
                    1.0 + accepted / drafts if drafts else None
                ),
                "draft_token_acceptance_rate": accepted / draft_tokens if draft_tokens else None,
            }
        )
        rows.append(request)
        args.output.write_text(
            json.dumps(
                {
                    "definition": {
                        "source_post_prompt_known": False,
                        "purpose": "content-dependent MTP acceptance scout",
                        "prompt_shape": "2048 tokens including chat overhead",
                        "generation_shape": args.max_tokens,
                    },
                    "rows": rows,
                    "complete": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    result = {
        "definition": {
            "source_post_prompt_known": False,
            "purpose": "content-dependent MTP acceptance scout",
            "prompt_shape": "2048 tokens including chat overhead",
            "generation_shape": args.max_tokens,
        },
        "rows": rows,
        "complete": True,
        "pass": all(row["pass"] for row in rows),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
