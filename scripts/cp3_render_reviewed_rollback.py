#!/usr/bin/env python3
"""Render a rollback-only CP3 SQL fixture from exact reviewed bytes.

This utility is deliberately fail-closed. It accepts an input only when:
- the SHA-256 matches the caller-supplied reviewed digest;
- UTF-8 and SQL lexical structure are valid;
- exactly one top-level BEGIN and one top-level COMMIT exist;
- no top-level ROLLBACK already exists;
- BEGIN is the first SQL statement;
- COMMIT is the final SQL statement; and
- the final statement is exactly ``COMMIT;``.

Quoted strings, quoted identifiers, nested block comments, line comments, and
PostgreSQL dollar-quoted bodies are lexically ignored, so text such as COMMIT
inside a function body cannot be mistaken for the terminal transaction marker.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

RENDERER_VERSION = "CP3_REVIEWED_ROLLBACK_V1"
_IDENTIFIER_START = re.compile(r"[A-Za-z_]" )
_IDENTIFIER_PART = re.compile(r"[A-Za-z0-9_$]")
_DOLLAR_TAG = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$")


class RenderError(ValueError):
    """Raised when exact-byte or SQL transaction guards fail."""


@dataclass(frozen=True)
class Token:
    value: str
    start: int
    end: int


@dataclass(frozen=True)
class RenderMetadata:
    renderer_version: str
    input_sha256: str
    output_sha256: str
    input_bytes: int
    output_bytes: int
    begin_token_count: int
    commit_token_count: int
    rollback_token_count: int
    begin_char_offset: int
    commit_char_offset: int
    terminal_semicolon_char_offset: int
    replacement: str


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _blank(masked: list[str], start: int, end: int) -> None:
    for index in range(start, end):
        if masked[index] not in "\r\n":
            masked[index] = " "


def mask_non_code(text: str) -> str:
    """Return text with comments and quoted regions replaced by spaces.

    Newlines and all character positions are preserved. Unterminated lexical
    regions are rejected instead of guessed.
    """

    masked = list(text)
    length = len(text)
    index = 0

    while index < length:
        char = text[index]
        nxt = text[index + 1] if index + 1 < length else ""

        if char == "-" and nxt == "-":
            start = index
            index += 2
            while index < length and text[index] not in "\r\n":
                index += 1
            _blank(masked, start, index)
            continue

        if char == "/" and nxt == "*":
            start = index
            depth = 1
            index += 2
            while index < length and depth:
                current = text[index]
                following = text[index + 1] if index + 1 < length else ""
                if current == "/" and following == "*":
                    depth += 1
                    index += 2
                elif current == "*" and following == "/":
                    depth -= 1
                    index += 2
                else:
                    index += 1
            if depth:
                raise RenderError("unterminated block comment")
            _blank(masked, start, index)
            continue

        if char == "'":
            start = index
            index += 1
            while index < length:
                if text[index] == "'":
                    if index + 1 < length and text[index + 1] == "'":
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            else:
                raise RenderError("unterminated single-quoted string")
            _blank(masked, start, index)
            continue

        if char == '"':
            start = index
            index += 1
            while index < length:
                if text[index] == '"':
                    if index + 1 < length and text[index + 1] == '"':
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            else:
                raise RenderError("unterminated double-quoted identifier")
            _blank(masked, start, index)
            continue

        if char == "$":
            match = _DOLLAR_TAG.match(text, index)
            if match:
                tag = match.group(0)
                start = index
                body_start = match.end()
                close = text.find(tag, body_start)
                if close < 0:
                    raise RenderError(f"unterminated dollar-quoted body {tag}")
                index = close + len(tag)
                _blank(masked, start, index)
                continue

        index += 1

    return "".join(masked)


def tokenize_code(masked: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0
    while index < len(masked):
        char = masked[index]
        if _IDENTIFIER_START.fullmatch(char):
            start = index
            index += 1
            while index < len(masked) and _IDENTIFIER_PART.fullmatch(masked[index]):
                index += 1
            tokens.append(Token(masked[start:index].upper(), start, index))
            continue
        if char == ";":
            tokens.append(Token(";", index, index + 1))
        index += 1
    return tokens


def split_statements(tokens: Iterable[Token]) -> list[list[Token]]:
    statements: list[list[Token]] = []
    current: list[Token] = []
    for token in tokens:
        current.append(token)
        if token.value == ";":
            statements.append(current)
            current = []
    if current:
        statements.append(current)
    return statements


def _statement_words(statement: list[Token]) -> list[str]:
    return [token.value for token in statement if token.value != ";"]


def render_reviewed_rollback(input_bytes: bytes, expected_sha256: str) -> tuple[bytes, RenderMetadata]:
    expected = expected_sha256.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise RenderError("expected SHA-256 must be exactly 64 lowercase/uppercase hex characters")

    actual = sha256_hex(input_bytes)
    if actual != expected:
        raise RenderError(f"input SHA-256 mismatch: expected {expected}, observed {actual}")

    if input_bytes.startswith(b"\xef\xbb\xbf"):
        raise RenderError("UTF-8 BOM is not accepted; review exact BOM-free bytes")
    try:
        text = input_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise RenderError(f"input is not strict UTF-8: {error}") from error

    masked = mask_non_code(text)
    tokens = tokenize_code(masked)
    statements = split_statements(tokens)
    if not statements:
        raise RenderError("input contains no SQL statement")
    if statements[-1][-1].value != ";":
        raise RenderError("final SQL statement is not semicolon-terminated")

    begin_tokens = [token for token in tokens if token.value == "BEGIN"]
    commit_tokens = [token for token in tokens if token.value == "COMMIT"]
    rollback_tokens = [token for token in tokens if token.value == "ROLLBACK"]

    if len(begin_tokens) != 1:
        raise RenderError(f"expected exactly one top-level BEGIN, observed {len(begin_tokens)}")
    if len(commit_tokens) != 1:
        raise RenderError(f"expected exactly one top-level COMMIT, observed {len(commit_tokens)}")
    if rollback_tokens:
        raise RenderError(f"input already contains {len(rollback_tokens)} top-level ROLLBACK token(s)")

    if _statement_words(statements[0]) != ["BEGIN"]:
        raise RenderError("BEGIN must be the first SQL statement and must be exactly BEGIN;")
    if _statement_words(statements[-1]) != ["COMMIT"]:
        raise RenderError("terminal SQL statement must be exactly COMMIT;")

    commit_token = commit_tokens[0]
    terminal_statement = statements[-1]
    if commit_token not in terminal_statement:
        raise RenderError("the sole COMMIT token is not in the terminal statement")
    terminal_semicolon = terminal_statement[-1]

    # masked text after the final semicolon must contain only whitespace because
    # comments/quoted regions are already blanked. This rejects trailing SQL.
    if masked[terminal_semicolon.end :].strip():
        raise RenderError("non-comment SQL exists after terminal COMMIT;")

    rendered_text = text[: commit_token.start] + "ROLLBACK" + text[commit_token.end :]
    rendered_bytes = rendered_text.encode("utf-8")
    rendered_masked = mask_non_code(rendered_text)
    rendered_tokens = tokenize_code(rendered_masked)
    if sum(token.value == "COMMIT" for token in rendered_tokens) != 0:
        raise RenderError("post-render verification found a top-level COMMIT")
    if sum(token.value == "ROLLBACK" for token in rendered_tokens) != 1:
        raise RenderError("post-render verification did not find exactly one top-level ROLLBACK")

    metadata = RenderMetadata(
        renderer_version=RENDERER_VERSION,
        input_sha256=actual,
        output_sha256=sha256_hex(rendered_bytes),
        input_bytes=len(input_bytes),
        output_bytes=len(rendered_bytes),
        begin_token_count=1,
        commit_token_count=1,
        rollback_token_count=0,
        begin_char_offset=begin_tokens[0].start,
        commit_char_offset=commit_token.start,
        terminal_semicolon_char_offset=terminal_semicolon.start,
        replacement="COMMIT->ROLLBACK",
    )
    return rendered_bytes, metadata


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        input_bytes = args.input.read_bytes()
        rendered, metadata = render_reviewed_rollback(input_bytes, args.expected_sha256)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.metadata.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(rendered)
        args.metadata.write_text(json.dumps(asdict(metadata), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, RenderError) as error:
        print(f"CP3 rollback render rejected: {error}", file=sys.stderr)
        return 2

    print(json.dumps(asdict(metadata), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
