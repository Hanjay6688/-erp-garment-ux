#!/usr/bin/env python3
"""Fail-closed renderer for exact reviewed CP3 SQL bytes.

The renderer never discovers or repairs SQL. It accepts one operation only,
binds the manifest to the renderer bytes and source bytes, requires one exact
operation marker plus one terminal top-level COMMIT, and verifies the expected
statement count, terminal position, rendered byte count, and rendered digest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

ALLOWED_TOP_KEYS = {
    "manifest_version",
    "candidate",
    "source_path",
    "source_sha256",
    "source_bytes",
    "renderer_sha256",
    "expected_top_level_statement_count",
    "expected_terminal_commit_start",
    "expected_rendered_sha256",
    "expected_rendered_bytes",
    "operations",
}
ALLOWED_OPERATION_KEYS = {"domain", "operation_type", "source_path"}
ALLOWED_OPERATIONS = {
    "ATTENDANCE_HPP": {"ATTENDANCE_HPP_FOUNDATION"},
    "LAUNDRY_CLAIM": {"LAUNDRY_CLAIM_SETTLEMENT", "LAUNDRY_CLAIM_REVERSAL"},
}
FORBIDDEN_CLAIM_TOKENS = ("transfer", "carry", "movement")
MARKER_RE = re.compile(
    r"(?m)^\s*--\s*CP3_OPERATION:\s*DOMAIN=([A-Z_]+)\s+TYPE=([A-Z_]+)\s*$"
)


class RenderError(RuntimeError):
    pass


@dataclass(frozen=True)
class Statement:
    raw: str
    start: int
    end: int
    normalized: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_manifest(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise RenderError("manifest must be a JSON object")
    missing = sorted(ALLOWED_TOP_KEYS - payload.keys())
    extra = sorted(payload.keys() - ALLOWED_TOP_KEYS)
    if missing:
        raise RenderError(f"manifest missing keys: {', '.join(missing)}")
    if extra:
        raise RenderError(f"manifest unexpected keys: {', '.join(extra)}")
    if payload["manifest_version"] != "CP3_REVIEWED_SQL_V1":
        raise RenderError("unsupported manifest_version")
    if not isinstance(payload["operations"], list) or len(payload["operations"]) != 1:
        raise RenderError("operations must contain exactly one isolated operation")
    operation = payload["operations"][0]
    if not isinstance(operation, dict):
        raise RenderError("operation[0] must be an object")
    missing_op = sorted(ALLOWED_OPERATION_KEYS - operation.keys())
    extra_op = sorted(operation.keys() - ALLOWED_OPERATION_KEYS)
    if missing_op:
        raise RenderError(f"operation[0] missing keys: {', '.join(missing_op)}")
    if extra_op:
        raise RenderError(f"operation[0] unexpected keys: {', '.join(extra_op)}")
    domain = operation["domain"]
    operation_type = operation["operation_type"]
    if domain not in ALLOWED_OPERATIONS:
        raise RenderError(f"operation[0] unknown domain {domain!r}")
    if operation_type not in ALLOWED_OPERATIONS[domain]:
        raise RenderError(f"operation[0] {operation_type!r} is not allowed for domain {domain!r}")
    if operation["source_path"] != payload["source_path"]:
        raise RenderError("operation source_path must equal top-level source_path")
    for key in ("source_sha256", "renderer_sha256", "expected_rendered_sha256"):
        if not isinstance(payload[key], str) or re.fullmatch(r"[0-9a-f]{64}", payload[key]) is None:
            raise RenderError(f"{key} must be a lowercase SHA-256 hex digest")
    for key in (
        "source_bytes",
        "expected_top_level_statement_count",
        "expected_terminal_commit_start",
        "expected_rendered_bytes",
    ):
        if not isinstance(payload[key], int) or payload[key] <= 0:
            raise RenderError(f"{key} must be a positive integer")
    return operation


def _dollar_tag_at(text: str, index: int) -> str | None:
    match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", text[index:])
    return match.group(0) if match else None


def split_top_level_statements(text: str) -> list[Statement]:
    statements: list[Statement] = []
    state = "normal"
    dollar_tag: str | None = None
    block_depth = 0
    statement_start = 0
    clean: list[str] = []
    i = 0

    def finish(end: int) -> None:
        nonlocal statement_start, clean
        raw = text[statement_start:end]
        normalized = " ".join("".join(clean).split()).strip().lower()
        if normalized:
            statements.append(Statement(raw=raw, start=statement_start, end=end, normalized=normalized))
        statement_start = end
        clean = []

    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if state == "normal":
            if ch == "-" and nxt == "-":
                state = "line_comment"; clean.append(" "); i += 2; continue
            if ch == "/" and nxt == "*":
                state = "block_comment"; block_depth = 1; clean.append(" "); i += 2; continue
            if ch == "'":
                state = "single"; clean.append("''"); i += 1; continue
            if ch == '"':
                state = "double"; clean.append('""'); i += 1; continue
            if ch == "$":
                tag = _dollar_tag_at(text, i)
                if tag:
                    state = "dollar"; dollar_tag = tag; clean.append("$body$"); i += len(tag); continue
            if ch == ";":
                clean.append(";"); finish(i + 1); i += 1; continue
            clean.append(ch); i += 1; continue
        if state == "line_comment":
            if ch == "\n": state = "normal"; clean.append("\n")
            i += 1; continue
        if state == "block_comment":
            if ch == "/" and nxt == "*": block_depth += 1; i += 2; continue
            if ch == "*" and nxt == "/":
                block_depth -= 1; i += 2
                if block_depth == 0: state = "normal"; clean.append(" ")
                continue
            i += 1; continue
        if state == "single":
            if ch == "'" and nxt == "'": i += 2; continue
            if ch == "'": state = "normal"
            i += 1; continue
        if state == "double":
            if ch == '"' and nxt == '"': i += 2; continue
            if ch == '"': state = "normal"
            i += 1; continue
        if state == "dollar":
            assert dollar_tag is not None
            if text.startswith(dollar_tag, i):
                i += len(dollar_tag); state = "normal"; dollar_tag = None; continue
            i += 1; continue
    if state not in {"normal", "line_comment"}:
        raise RenderError(f"unterminated SQL lexical state: {state}")
    finish(len(text))
    return statements


def strip_terminal_semicolon(normalized: str) -> str:
    return normalized[:-1].strip() if normalized.endswith(";") else normalized.strip()


def analyze_source(source_bytes: bytes) -> dict:
    text = source_bytes.decode("utf-8")
    statements = split_top_level_statements(text)
    if len(statements) < 3:
        raise RenderError("reviewed SQL must contain BEGIN, body, and terminal COMMIT")
    first = strip_terminal_semicolon(statements[0].normalized)
    last = strip_terminal_semicolon(statements[-1].normalized)
    if first not in {"begin", "begin transaction"}:
        raise RenderError(f"first top-level statement must be BEGIN, got {first!r}")
    if last not in {"commit", "commit transaction"}:
        raise RenderError(f"last top-level statement must be COMMIT, got {last!r}")
    commits = [s for s in statements if strip_terminal_semicolon(s.normalized) in {"commit", "commit transaction"}]
    if len(commits) != 1 or commits[0] is not statements[-1]:
        raise RenderError("reviewed SQL must have exactly one final top-level COMMIT")
    body = "".join(statement.raw for statement in statements[1:-1]).lstrip()
    source_sha = sha256_bytes(source_bytes)
    header = (
        "-- GENERATED FROM EXACT REVIEWED BYTES; DO NOT EDIT.\n"
        f"-- source_sha256={source_sha}\n"
        f"-- source_bytes={len(source_bytes)}\n"
        f"-- top_level_statement_count={len(statements)}\n"
        f"-- terminal_commit_start={statements[-1].start}\n"
    )
    rendered = (header + body.rstrip() + "\n").encode("utf-8")
    return {
        "text": text,
        "statements": statements,
        "rendered": rendered,
        "source_sha256": source_sha,
        "source_bytes": len(source_bytes),
        "top_level_statement_count": len(statements),
        "terminal_commit_start": statements[-1].start,
        "terminal_commit_end": statements[-1].end,
        "rendered_sha256": sha256_bytes(rendered),
        "rendered_bytes": len(rendered),
    }


def render(manifest_path: Path, output_sql: Path, output_metadata: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    operation = validate_manifest(manifest)
    renderer_sha = sha256_bytes(Path(__file__).resolve().read_bytes())
    if renderer_sha != manifest["renderer_sha256"]:
        raise RenderError(f"renderer SHA-256 mismatch: expected {manifest['renderer_sha256']}, got {renderer_sha}")
    source_path = (manifest_path.parent.parent.parent / manifest["source_path"]).resolve()
    source_bytes = source_path.read_bytes()
    analysis = analyze_source(source_bytes)
    if analysis["source_sha256"] != manifest["source_sha256"]:
        raise RenderError("source SHA-256 mismatch")
    if analysis["source_bytes"] != manifest["source_bytes"]:
        raise RenderError("source byte count mismatch")

    markers = MARKER_RE.findall(analysis["text"])
    expected_marker = (operation["domain"], operation["operation_type"])
    if markers != [expected_marker]:
        raise RenderError(f"exact operation marker mismatch: expected {[expected_marker]}, got {markers}")

    semantic_sql = " ".join(statement.normalized for statement in analysis["statements"])
    if operation["domain"] == "LAUNDRY_CLAIM":
        hit = [token for token in FORBIDDEN_CLAIM_TOKENS if token in semantic_sql]
        if hit:
            raise RenderError("LAUNDRY_CLAIM operation contains forbidden transfer/carry/movement semantics: " + ", ".join(hit))

    expected = {
        "top_level_statement_count": manifest["expected_top_level_statement_count"],
        "terminal_commit_start": manifest["expected_terminal_commit_start"],
        "rendered_sha256": manifest["expected_rendered_sha256"],
        "rendered_bytes": manifest["expected_rendered_bytes"],
    }
    for key, value in expected.items():
        if analysis[key] != value:
            raise RenderError(f"{key} mismatch: expected {value}, got {analysis[key]}")

    output_sql.parent.mkdir(parents=True, exist_ok=True)
    output_sql.write_bytes(analysis["rendered"])
    metadata = {
        "status": "PASS",
        "manifest_path": str(manifest_path),
        "renderer_sha256": renderer_sha,
        "source_path": str(source_path),
        "source_sha256": analysis["source_sha256"],
        "source_bytes": analysis["source_bytes"],
        "top_level_statement_count": analysis["top_level_statement_count"],
        "terminal_commit_start": analysis["terminal_commit_start"],
        "terminal_commit_end": analysis["terminal_commit_end"],
        "rendered_sha256": analysis["rendered_sha256"],
        "rendered_bytes": analysis["rendered_bytes"],
        "operation": operation,
    }
    output_metadata.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output_sql", type=Path)
    parser.add_argument("output_metadata", type=Path)
    args = parser.parse_args()
    metadata = render(args.manifest.resolve(), args.output_sql.resolve(), args.output_metadata.resolve())
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
