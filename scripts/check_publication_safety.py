#!/usr/bin/env python3
"""Fail closed when public repository text contains likely private data."""

from __future__ import annotations

import ipaddress
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = Path("scripts/check_publication_safety.py")
FENCE = chr(96) * 3
REQUIRED_FILES = {
    Path("README.md"),
    Path("LICENSE"),
    Path("docs/CASE-STUDY.md"),
    Path("docs/BUILD-DIAGNOSIS.md"),
    Path("docs/METHODOLOGY.md"),
    Path("docs/ACCEPTANCE-MATRIX.md"),
    Path("docs/QA-EVIDENCE.md"),
    Path("docs/ARCHITECTURE.md"),
    Path("docs/PUBLICATION-SAFETY.md"),
    Path("docs/SHARE.md"),
    Path("docs/X-POST.md"),
    Path("examples/glm52-nvfp4-measured-summary.json"),
    Path("reproduction/Dockerfile"),
    Path("reproduction/CMakeLists.sm121-nvfp4.patch"),
    Path("publication-policy.json"),
    Path(".github/workflows/publication-safety.yml"),
    SELF,
}
TEXT_SUFFIXES = {
    ".md",
    ".json",
    ".py",
    ".yml",
    ".yaml",
    ".txt",
    ".toml",
    ".patch",
    ".sh",
    ".cmake",
}
TEXT_NAMES = {"Dockerfile", "NOTICE"}
FORBIDDEN_NETWORKS = tuple(
    ipaddress.ip_network(value)
    for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10")
)
ALLOWED_DOCUMENTATION_NETWORKS = tuple(
    ipaddress.ip_network(value)
    for value in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
)
IPV4 = re.compile(r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])")
PATTERNS = {
    "private_key_block": re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+)\b"),
    "cloud_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]+\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "mac_address": re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"),
    "uuid": re.compile(r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\b"),
    "serial_like": re.compile(r"\b(?=[A-Z0-9]*[A-Z])(?=[A-Z0-9]*[0-9])[A-Z0-9]{10,}\b"),
    "multicast_local_hostname": re.compile(r"\b[A-Za-z0-9-]+[.]local\b", re.IGNORECASE),
    "mac_home_path": re.compile(r"/Users/[A-Za-z0-9._-]+"),
    "posix_home_path": re.compile(r"/home/[A-Za-z0-9._-]+"),
    "windows_home_path": re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+"),
    "secret_assignment": re.compile(
        r"""(?i)\b(?:api[_-]?key|password|secret|access[_-]?token)\b\s*[:=]\s*["'][^"']+["']"""
    ),
    "sensitive_mapping_field": re.compile(
        r"""(?i)["']?(?:device_id|hardware_id|serial_number|mac_address|outlet_map|controller_map|live_topology|service_inventory)["']?\s*[:=]"""
    ),
    "private_source_link": re.compile(r"https://github[.]com/GumbiiDigital/(?![A-Za-z0-9._-]+-public(?:\b|/))"),
    "private_fleet_name": re.compile(r"\b(?:wg-spark[0-9]+|sonicforge|spark-[0-9a-f]{4})\b", re.IGNORECASE),
    "private_service_name": re.compile(r"\b(?:gumbii-registry|compose-arangodb|cliproxyapi)\b", re.IGNORECASE),
    "markdown_image": re.compile(r"!\[[^]]*\]\([^)]+\)"),
}
LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")


def repository_files() -> list[Path]:
    files: list[Path] = []
    excluded_parts = {".git", ".venv", "__pycache__", "candidate-artifact", "node_modules"}
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in excluded_parts for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"symlink is not allowed: {relative}")
        if path.is_file():
            files.append(relative)
    return sorted(files)


def scan_text(relative: Path, text: str, failures: list[str]) -> None:
    for name, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            if name == "serial_like" and match.group(0) == "SHA256SUMS":
                continue
            line = text.count("\n", 0, match.start()) + 1
            failures.append(f"{relative}:{line}: prohibited pattern {name}")

    for match in IPV4.finditer(text):
        value = match.group(0)
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            failures.append(f"{relative}: invalid IPv4-like value {value}")
            continue
        if any(address in network for network in FORBIDDEN_NETWORKS):
            failures.append(f"{relative}: private or CGNAT address {value}")
        elif not any(address in network for network in ALLOWED_DOCUMENTATION_NETWORKS):
            failures.append(f"{relative}: non-documentation address {value}")

    if relative.suffix == ".md":
        if text.count(FENCE) % 2:
            failures.append(f"{relative}: unbalanced Markdown code fence")
        first = next((line for line in text.splitlines() if line.strip()), "")
        if relative == Path("docs/ARCHITECTURE.md"):
            lines = [line for line in text.splitlines() if line.strip()]
            fence_lines = [line for line in lines if line.startswith(FENCE)]
            if not lines or lines[0] != f"{FENCE}mermaid" or lines[-1] != FENCE or len(fence_lines) != 2:
                failures.append(f"{relative}: architecture must contain one Mermaid fence and no prose")
        elif not first.startswith("#"):
            failures.append(f"{relative}: first non-empty line must be a heading")

        for target in LINK.findall(text):
            if target.startswith("#") or "://" in target:
                continue
            clean = target.split("#", 1)[0]
            resolved = (ROOT / relative.parent / clean).resolve()
            if clean and not resolved.is_relative_to(ROOT.resolve()):
                failures.append(f"{relative}: link escapes repository: {target}")
            elif clean and not resolved.exists():
                failures.append(f"{relative}: broken relative link: {target}")


def main() -> int:
    failures: list[str] = []
    try:
        files = repository_files()
    except ValueError as exc:
        print(f"publication safety: FAIL\n{exc}")
        return 1

    present = set(files)
    missing = sorted(REQUIRED_FILES - present)
    failures.extend(f"missing required file: {path}" for path in missing)

    image_suffixes = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
    failures.extend(f"image asset is not authorized: {path}" for path in files if path.suffix.lower() in image_suffixes)

    json_files = [path for path in files if path.suffix == ".json"]
    json_examples = [path for path in json_files if path.parts and path.parts[0] == "examples"]
    if not json_examples:
        failures.append("at least one JSON example is required")

    scanned = 0
    for relative in files:
        if relative == SELF or (
            relative.suffix not in TEXT_SUFFIXES and relative.name not in TEXT_NAMES
        ):
            continue
        path = ROOT / relative
        try:
            text = path.read_text(encoding="utf-8")
            text.encode("ascii")
        except (UnicodeDecodeError, UnicodeEncodeError):
            failures.append(f"{relative}: file must be ASCII text")
            continue
        scanned += 1
        if relative != Path("publication-policy.json"):
            scan_text(relative, text, failures)
        if relative.suffix == ".json":
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                failures.append(f"{relative}: invalid JSON: {exc}")
                continue
            if relative == Path("publication-policy.json"):
                if not isinstance(payload, dict) or payload.get("schema_version") != 1:
                    failures.append(f"{relative}: publication policy schema must be version 1")
                continue
            if not isinstance(payload, dict):
                failures.append(f"{relative}: JSON publication must be an object")
                continue
            if payload.get("synthetic") is True:
                continue
            if payload.get("record_type") == "measured_summary":
                evidence = payload.get("evidence") or {}
                limitations = payload.get("limitations") or []
                if payload.get("public_safe") is not True:
                    failures.append(f"{relative}: measured summary must declare public_safe true")
                if payload.get("historical") is not True:
                    failures.append(f"{relative}: measured summary must declare historical true")
                if evidence.get("raw_evidence_published") is not False:
                    failures.append(f"{relative}: measured summary must exclude raw evidence")
                if evidence.get("aggregate_derivative_only") is not True:
                    failures.append(f"{relative}: measured summary must declare aggregate derivative only")
                if len(limitations) < 3:
                    failures.append(f"{relative}: measured summary must preserve at least three limitations")
                continue
            failures.append(
                f"{relative}: JSON must be an explicit synthetic example or reviewed measured_summary"
            )

    if failures:
        print("publication safety: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    measured = sum(
        1
        for path in json_examples
        if json.loads((ROOT / path).read_text(encoding="utf-8")).get("record_type") == "measured_summary"
    )
    print(
        "publication safety: PASS "
        f"({scanned} text files, {len(json_examples)} JSON examples, {measured} measured summaries)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
