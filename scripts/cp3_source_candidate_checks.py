#!/usr/bin/env python3
"""Fail-closed static/provenance checks for the CP3 source candidate.

This script proves source shape only. It never labels SQL compile, runtime,
concurrency, UAT, or production as PASS.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from cp3_render_reviewed_rollback import mask_non_code, tokenize_code

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "migration_policy_sewing": ROOT / "supabase/migrations/20260901023000_erp_v2_6_14a_attendance_hpp_policy_and_sewing_terminal.sql",
    "migration_pool_intents": ROOT / "supabase/migrations/20260901023100_erp_v2_6_14b_attendance_hpp_pool_intents.sql",
    "source_contract": ROOT / "supabase/tests/attendance_hpp_cp3_source_contract.sql",
    "concurrency_harness": ROOT / "supabase/tests/attendance_hpp_cp3_concurrency.py",
    "concurrency_fixture_example": ROOT / "supabase/tests/attendance_hpp_cp3_concurrency.fixture.example.json",
    "rollback_renderer": ROOT / "scripts/cp3_render_reviewed_rollback.py",
    "rollback_renderer_tests": ROOT / "scripts/test_cp3_render_reviewed_rollback.py",
}


class CheckFailure(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailure(message)


def top_level_words(text: str) -> list[str]:
    return [token.value for token in tokenize_code(mask_non_code(text))]


def strip_sql_comments(text: str) -> str:
    """Remove line/nested block comments while preserving quoted bodies."""
    output: list[str] = []
    index = 0
    depth = 0
    state = "code"
    dollar_tag = ""
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if state == "line":
            if char in "\r\n":
                state = "code"
                output.append(char)
            else:
                output.append(" ")
            index += 1
            continue
        if state == "block":
            if char == "/" and nxt == "*":
                depth += 1
                output.extend("  ")
                index += 2
            elif char == "*" and nxt == "/":
                depth -= 1
                output.extend("  ")
                index += 2
                if depth == 0:
                    state = "code"
            else:
                output.append("\n" if char == "\n" else " ")
                index += 1
            continue
        if state == "single":
            output.append(char)
            if char == "'":
                if nxt == "'":
                    output.append(nxt)
                    index += 2
                    continue
                state = "code"
            index += 1
            continue
        if state == "double":
            output.append(char)
            if char == '"':
                if nxt == '"':
                    output.append(nxt)
                    index += 2
                    continue
                state = "code"
            index += 1
            continue
        if state == "dollar":
            if text.startswith(dollar_tag, index):
                output.append(dollar_tag)
                index += len(dollar_tag)
                state = "code"
            else:
                output.append(char)
                index += 1
            continue

        if char == "-" and nxt == "-":
            state = "line"
            output.extend("  ")
            index += 2
        elif char == "/" and nxt == "*":
            state = "block"
            depth = 1
            output.extend("  ")
            index += 2
        elif char == "'":
            state = "single"
            output.append(char)
            index += 1
        elif char == '"':
            state = "double"
            output.append(char)
            index += 1
        elif char == "$":
            match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", text[index:])
            if match:
                dollar_tag = match.group(0)
                state = "dollar"
                output.append(dollar_tag)
                index += len(dollar_tag)
            else:
                output.append(char)
                index += 1
        else:
            output.append(char)
            index += 1
    require(state == "code", f"unterminated SQL lexical state {state}")
    return "".join(output)


def check_transaction_shape(path: Path, terminal: str) -> dict:
    text = path.read_text(encoding="utf-8")
    words = top_level_words(text)
    begin_count = words.count("BEGIN")
    commit_count = words.count("COMMIT")
    rollback_count = words.count("ROLLBACK")
    require(begin_count == 1, f"{path}: expected one top-level BEGIN, observed {begin_count}")
    if terminal == "COMMIT":
        require(commit_count == 1 and rollback_count == 0, f"{path}: migration must end in one COMMIT and no ROLLBACK")
    else:
        require(rollback_count == 1 and commit_count == 0, f"{path}: acceptance must end in one ROLLBACK and no COMMIT")
    require(words[0] == "BEGIN", f"{path}: BEGIN is not the first SQL statement")
    require(words[-2:] == [terminal, ";"], f"{path}: terminal statement is not exact {terminal};")
    return {"begin": begin_count, "commit": commit_count, "rollback": rollback_count, "terminal": terminal}


def main() -> int:
    try:
        for label, path in FILES.items():
            require(path.is_file(), f"missing required candidate file: {label} -> {path}")
            require(path.stat().st_size > 100, f"candidate file is suspiciously small: {path}")
            require(path.read_text(encoding="utf-8").strip() != "PLACEHOLDER", f"placeholder survived: {path}")

        tx = {
            "migration_policy_sewing": check_transaction_shape(FILES["migration_policy_sewing"], "COMMIT"),
            "migration_pool_intents": check_transaction_shape(FILES["migration_pool_intents"], "COMMIT"),
            "source_contract": check_transaction_shape(FILES["source_contract"], "ROLLBACK"),
        }

        migration_a = FILES["migration_policy_sewing"].read_text(encoding="utf-8")
        migration_b = FILES["migration_pool_intents"].read_text(encoding="utf-8")
        executable = strip_sql_comments(migration_a + "\n" + migration_b)
        lower = executable.lower()

        require("selesai_dijahit" in lower, "explicit SELESAI_DIJAHIT contract is missing")
        require("contractor_hpp_policy_versions" in lower, "explicit Special/attendance policy table is missing")
        require("original_journal_line_id" in lower, "original debit-line identity is missing")
        require("cancel_attendance_hpp_pool_v1" in lower, "ACTIVE pool cancel orchestration is missing")
        require("cp3_assert_typed_operation_manifest_v1" in lower, "typed operation isolation helper is missing")
        require("cp3_validate_pool_v1" in lower, "bounded set-based pool validator is missing")
        require("post_journal(" not in lower, "CP3 foundation must not post the general ledger")
        require("create or replace function public." not in lower, "CP3 candidate must not create public facades")
        require(not re.search(r"grant\s+execute[\s\S]{0,180}\bto\s+authenticated\b", lower),
                "CP3 candidate must not grant execution to authenticated")

        prepare_match = re.search(
            r"create\s+or\s+replace\s+function\s+erp\.prepare_attendance_hpp_pool_v1\b([\s\S]*?)\n\$function\$;",
            executable,
            re.IGNORECASE,
        )
        require(prepare_match is not None, "prepare_attendance_hpp_pool_v1 definition was not found")
        prepare = prepare_match.group(0).lower()
        require("v_attendance_hpp_active_sewing_events_v1" in prepare,
                "pool denominator is not bound to the active sewing-event view")
        for stale in ("fg_lots", "initial_qty_pcs", "qc_good", "good_qty"):
            require(stale not in prepare, f"stale QC/FG denominator token found in prepare function: {stale}")

        contract = FILES["source_contract"].read_text(encoding="utf-8").lower()
        for case in (
            "missing required key",
            "explicit null",
            "wrong type",
            "extra key",
            "nested required key",
            "transfer",
            "carry_forward",
            "movement",
            "asia/jakarta",
        ):
            require(case in contract, f"source-contract negative case missing: {case}")

        renderer_tests = FILES["rollback_renderer_tests"].read_text(encoding="utf-8")
        test_count = len(re.findall(r"^\s+def test_", renderer_tests, re.MULTILINE))
        require(test_count >= 15, f"rollback renderer adversarial corpus too small: {test_count}")

        concurrency = FILES["concurrency_harness"].read_text(encoding="utf-8")
        for marker in (
            "threading.Barrier",
            "ThreadPoolExecutor",
            "cancel_vs_finalize",
            "same_key_different_payload",
            "LOCAL_HOSTS",
            "CP3_DISPOSABLE_CONFIRM",
        ):
            require(marker in concurrency, f"real concurrency/safety marker missing: {marker}")

        entries = []
        for label, path in FILES.items():
            entries.append({
                "label": label,
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
        entries.sort(key=lambda item: item["path"])

        report = {
            "status": "PASS_SOURCE_SHAPE_ONLY",
            "truth_boundary": {
                "sql_compile": "NOT_EXECUTED",
                "runtime": "NOT_EXECUTED",
                "real_concurrency": "HARNESS_PRESENT_NOT_EXECUTED",
                "uat_applied": False,
                "live_deployed": False,
                "backend_connected": False,
                "production_go": False,
            },
            "transaction_shape": tx,
            "rollback_renderer_test_count": test_count,
            "files": entries,
        }
        output = ROOT / "cp3-source-candidate-check-report.json"
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        checksum = ROOT / "cp3-source-candidate-SHA256SUMS.txt"
        checksum.write_text("".join(f"{item['sha256']}  {item['path']}\n" for item in entries), encoding="utf-8")
        print(json.dumps(report, sort_keys=True))
        return 0
    except (CheckFailure, OSError, UnicodeError) as error:
        print(f"CP3 source candidate check FAILED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
