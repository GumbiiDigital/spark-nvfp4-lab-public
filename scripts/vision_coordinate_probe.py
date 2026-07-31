#!/usr/bin/env python3
"""Programmatically assert a vision model's pixel-coordinate answer."""

from __future__ import annotations

import argparse
import base64
import io
import json
from pathlib import Path
import re
import time
import urllib.request

from PIL import Image, ImageDraw


WIDTH, HEIGHT = 800, 500
MARKER_BOX = (590, 105, 670, 185)
EXPECTED = ((MARKER_BOX[0] + MARKER_BOX[2]) // 2, (MARKER_BOX[1] + MARKER_BOX[3]) // 2)
TOLERANCE = 35


def parse_coordinates(text: str) -> tuple[int, int] | None:
    candidates = [text]
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        candidates.insert(0, match.group(0))
    for candidate in candidates:
        try:
            data = json.loads(candidate)
            return int(data["x"]), int(data["y"])
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            continue
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (WIDTH, HEIGHT), "#102a43")
    draw = ImageDraw.Draw(image)
    for x, y in ((80, 80), (220, 330), (430, 250)):
        draw.rectangle((x, y, x + 60, y + 60), fill="#e53935")
    draw.rectangle(MARKER_BOX, fill="#00ff66")
    draw.line((0, HEIGHT // 2, WIDTH, HEIGHT // 2), fill="#ffffff", width=2)
    draw.line((WIDTH // 2, 0, WIDTH // 2, HEIGHT), fill="#ffffff", width=2)
    fixture = args.output_dir / "vision-coordinate-fixture.png"
    image.save(fixture)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode()
    prompt = (
        f"This image is exactly {WIDTH} pixels wide and {HEIGHT} pixels high. "
        "Using origin (0,0) at the top-left, report the pixel coordinates of "
        "the CENTER of the single bright-green square. Return only compact JSON "
        'with integer keys x and y, for example {"x":1,"y":2}.'
    )
    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
        ]}],
        "temperature": 0,
        "max_tokens": 128,
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
    answer = (message.get("content") or "").strip()
    parsed = parse_coordinates(answer)
    passed = bool(
        status == 200
        and parsed is not None
        and abs(parsed[0] - EXPECTED[0]) <= TOLERANCE
        and abs(parsed[1] - EXPECTED[1]) <= TOLERANCE
    )
    result = {
        "status": status,
        "image_size": [WIDTH, HEIGHT],
        "marker_box": list(MARKER_BOX),
        "expected_center": list(EXPECTED),
        "tolerance_px": TOLERANCE,
        "parsed_center": None if parsed is None else list(parsed),
        "answer": answer,
        "usage": body.get("usage"),
        "latency_s": time.perf_counter() - started,
        "pass": passed,
    }
    (args.output_dir / "vision-coordinate-result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
