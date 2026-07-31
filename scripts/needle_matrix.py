#!/usr/bin/env python3
"""Cache-salted front/middle/end needle retrieval at exact context depths."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request

from transformers import PreTrainedTokenizerFast


DEPTHS = (50_000, 200_000, 500_000)
POSITIONS = ("front", "middle", "end")


def token_count(tokenizer: PreTrainedTokenizerFast, text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))


def exact_filler(tokenizer: PreTrainedTokenizerFast, target: int, unit: str) -> str:
    unit_ids = tokenizer.encode(unit, add_special_tokens=False)
    if not unit_ids:
        raise RuntimeError("filler unit tokenized to zero tokens")
    repeats, remainder = divmod(target, len(unit_ids))
    text = unit * repeats
    if remainder:
        text += tokenizer.decode(unit_ids[:remainder], skip_special_tokens=True)
    # Tokenizer decode/encode boundaries can shift a few tokens. Converge with
    # a stable single-token pad while never exceeding the requested target.
    pad = " x"
    for _ in range(32):
        count = token_count(tokenizer, text)
        if count == target:
            return text
        if count < target:
            text += pad * (target - count)
        else:
            text = tokenizer.decode(
                tokenizer.encode(text, add_special_tokens=False)[:target],
                skip_special_tokens=True,
            )
    count = token_count(tokenizer, text)
    if count != target:
        raise RuntimeError(f"could not construct exact filler: target={target} got={count}")
    return text


def natural_filler(
    tokenizer: PreTrainedTokenizerFast,
    target: int,
    salt: str,
) -> str:
    """Build varied, deterministic prose instead of one repeated token pattern."""
    places = (
        "harbor",
        "orchard",
        "observatory",
        "library",
        "station",
        "workshop",
        "valley",
        "laboratory",
    )
    objects = (
        "copper dial",
        "weather ledger",
        "blue lantern",
        "map case",
        "ceramic gauge",
        "field notebook",
        "signal mast",
        "water clock",
    )
    actions = (
        "was inspected",
        "was catalogued",
        "was recalibrated",
        "was photographed",
        "was transferred",
        "was compared",
        "was sealed",
        "was indexed",
    )
    notes = (
        "under clear skies",
        "before the evening shift",
        "after routine maintenance",
        "during a quiet interval",
        "with no anomaly recorded",
        "beside the eastern window",
        "following the standard checklist",
        "while the archive remained open",
    )
    chunks: list[str] = []
    chars = 0
    index = 0
    char_target = max(4096, target * 5)
    while chars < char_target:
        sentence = (
            f" Record {index} for {salt}: the {objects[index % len(objects)]} at the "
            f"{places[(index * 3) % len(places)]} {actions[(index * 5) % len(actions)]} "
            f"{notes[(index * 7) % len(notes)]}."
        )
        chunks.append(sentence)
        chars += len(sentence)
        index += 1
    return exact_filler(tokenizer, target, "".join(chunks))


def build_prompt(
    tokenizer: PreTrainedTokenizerFast,
    depth: int,
    position: str,
    salt: str,
    key: str,
) -> tuple[str, int]:
    needle = f"\nAUTHORITATIVE RECORD: the verification key is {key}.\n"
    question = (
        "\nQuestion: What is the verification key in the authoritative record? "
        "Reply with only that key."
    )
    salt_line = f"Cache salt {salt}. The remaining text is archival filler.\n"
    fixed = token_count(tokenizer, salt_line + needle + question)
    target_content = depth - 96
    filler_tokens = target_content - fixed
    if filler_tokens <= 0:
        raise ValueError("depth too small")
    filler = natural_filler(tokenizer, filler_tokens, salt)
    if position == "front":
        content = salt_line + needle + filler + question
    elif position == "middle":
        ids = tokenizer.encode(filler, add_special_tokens=False)
        pivot = len(ids) // 2
        left = tokenizer.decode(ids[:pivot], skip_special_tokens=True)
        right = tokenizer.decode(ids[pivot:], skip_special_tokens=True)
        content = salt_line + left + needle + right + question
    elif position == "end":
        content = salt_line + filler + needle + question
    else:
        raise ValueError(position)
    return content, token_count(tokenizer, content)


def send(base_url: str, model: str, content: str, timeout: float) -> tuple[int, dict, float]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0,
        "max_tokens": 64,
        "min_tokens": 1,
        "chat_template_kwargs": {
            "clear_thinking": True,
            "enable_thinking": False,
        },
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read())
        return response.status, body, time.perf_counter() - started


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--tokenizer-file", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=1800)
    args = parser.parse_args()
    tokenizer = PreTrainedTokenizerFast(tokenizer_file=args.tokenizer_file)
    rows = []
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def write_checkpoint(complete: bool) -> None:
        result = {
            "cache_control": "request-distinct salt embedded in deterministic varied prose",
            "runs": rows,
            "complete": complete,
            "pass": complete and all(row["pass"] for row in rows),
        }
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    for depth in DEPTHS:
        for position in POSITIONS:
            salt = f"nvfp4-{depth}-{position}-20260730-natural-hidden-key"
            key = f"ORCHID-{depth // 1000}-{position.upper()}"
            content, local_tokens = build_prompt(tokenizer, depth, position, salt, key)
            prompt_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
            key_occurrences = content.count(key)
            status, body, latency = send(args.base_url, args.model, content, args.timeout)
            choice = (body.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            answer = (message.get("content") or "").strip()
            usage = body.get("usage") or {}
            prompt_tokens = usage.get("prompt_tokens")
            prompt_tokens_verified = bool(
                isinstance(prompt_tokens, int)
                and local_tokens <= prompt_tokens <= local_tokens + 512
                and abs(prompt_tokens - depth) <= 512
            )
            rows.append({
                "depth": depth,
                "position": position,
                "salt": salt,
                "expected": key,
                "status": status,
                "local_content_tokens": local_tokens,
                "prompt_utf8_sha256": prompt_sha256,
                "verification_key_occurrences": key_occurrences,
                "prompt_tokens": prompt_tokens,
                "prompt_tokens_verified": prompt_tokens_verified,
                "completion_tokens": usage.get("completion_tokens"),
                "latency_s": latency,
                "answer": answer,
                "message": message,
                "finish_reason": choice.get("finish_reason"),
                "response_id": body.get("id"),
                "response_model": body.get("model"),
                "response_body": body,
                "pass": (
                    status == 200
                    and answer == key
                    and prompt_tokens_verified
                    and key_occurrences == 1
                ),
            })
            write_checkpoint(complete=False)
            if not rows[-1]["pass"]:
                print(json.dumps(rows[-1], indent=2))
                return 2
    result = {
        "cache_control": "request-distinct salt embedded in deterministic varied prose",
        "runs": rows,
        "complete": True,
        "pass": all(row["pass"] for row in rows),
    }
    write_checkpoint(complete=True)
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
