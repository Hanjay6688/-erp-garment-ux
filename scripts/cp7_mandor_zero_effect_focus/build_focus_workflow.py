#!/usr/bin/env python3
"""Derive one-case Mandor diagnostic from the exact Mandor17 setup prefix."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re

from focus_identity import FOCUS_DIR, PRODUCT_HEAD


SOURCE_BYTES = 38453
SOURCE_GIT_BLOB = "4c4b75527eee2f88d06708da762890932f3cdc05"
RUNTIME_ANCHOR = "    - name: Run current Mandor17 once and retain complete Originals during owning\n"
JOBS_ANCHOR = "jobs:\n"
APPROVED_BRANCH = "__APPROVED_DISPOSABLE_BRANCH__"
EARLY_WINDOW = "    - name: Require genuine six-hour WIB window before current Mandor setup\n"
QUALIFICATION_ADMISSION = "    - name: Admit genuine Afui15 and whole current Mandor graph under database network\n"
BROWSER_SETUP = "    - name: Install pinned browser dependencies in both actual checkout roots\n"
START_DATABASE = "    - name: Start disposable database\n"
AUDITOR_CHECKOUT = """    - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
      with:
        path: auditor
        fetch-depth: 0
        persist-credentials: 'false'
"""


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def derive(raw: bytes, approved_branch: str = APPROVED_BRANCH) -> bytes:
    if len(raw) != SOURCE_BYTES or git_blob(raw) != SOURCE_GIT_BLOB:
        raise ValueError("CP7_FOCUS_EXACT_MANDOR17_WORKFLOW_REQUIRED")
    text = raw.decode()
    if approved_branch != APPROVED_BRANCH and not re.fullmatch(
            r"astra-a/mandor-zero-effect-focus-[0-9]{8}", approved_branch):
        raise ValueError("CP7_FOCUS_LITERAL_WRITER_A_BRANCH_REQUIRED")
    if text.count(JOBS_ANCHOR) != 1 or text.count(RUNTIME_ANCHOR) != 1:
        raise ValueError("CP7_FOCUS_ONE_SETUP_PREFIX_REQUIRED")
    body = JOBS_ANCHOR + text.split(JOBS_ANCHOR, 1)[1].split(RUNTIME_ANCHOR, 1)[0]
    if any(body.count(x) != 1 for x in
           (EARLY_WINDOW, QUALIFICATION_ADMISSION, BROWSER_SETUP, START_DATABASE)):
        raise ValueError("CP7_FOCUS_EXACT_REMOVAL_ANCHORS_REQUIRED")
    if body.count(AUDITOR_CHECKOUT) != 1:
        raise ValueError("CP7_FOCUS_EXACT_AUDITOR_CHECKOUT_REQUIRED")
    product_checkout = AUDITOR_CHECKOUT.replace(
        "        path: auditor\n", f"        ref: {PRODUCT_HEAD}\n        path: auditor\n", 1)
    tools_checkout = AUDITOR_CHECKOUT.replace(
        "        path: auditor\n", "        path: focus-tools\n", 1).replace(
            "fetch-depth: 0", "fetch-depth: 4", 1)
    body = body.replace(AUDITOR_CHECKOUT, tools_checkout + product_checkout, 1)
    window = """    - name: Require bounded four-hour WIB focus window plus setup reserve
      working-directory: auditor
      run: |
        python - <<'PY'
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        zone = ZoneInfo('Asia/Jakarta')
        now = datetime.now(zone)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        remaining = int((midnight - now).total_seconds())
        required = 14400 + 900
        if remaining < required:
            raise SystemExit(f'CP7_FOCUS_WIB_WINDOW_REQUIRED:{remaining}:{required}')
        print({'status':'FOCUS_WINDOW_PASS','remaining_seconds':remaining,'required_seconds':required})
        PY
"""
    first = body.index(EARLY_WINDOW)
    end = body.index("    - name: Select exact qualified prerequisite heads", first)
    body = body[:first] + window + body[end:]
    admission = f"""    - name: Admit exact focused source with database and network fenced
      working-directory: writer
      env:
        CP7_FOCUS_APPROVED_REF: refs/heads/{approved_branch}
      run: python -B ../focus-tools/{FOCUS_DIR}/focus_preflight.py
"""
    first = body.index(QUALIFICATION_ADMISSION)
    end = body.index(BROWSER_SETUP, first)
    body = body[:first] + admission + body[end:]
    first = body.index(BROWSER_SETUP)
    end = body.index(START_DATABASE, first)
    body = body[:first] + body[end:]
    body = body.replace(
        "    name: Current Mandor17 with complete Originals and owning restoration\n",
        "    name: Focused Mandor correction with exact rollback\n", 1)
    body = body.replace("    timeout-minutes: 360\n", "    timeout-minutes: 240\n", 1)
    header = f"""name: CP7 Mandor focused correction diagnostic
'on':
  push:
    branches:
    - {approved_branch}
    paths:
    - .github/workflows/cp7-mandor-zero-effect-focus.yml
    - {FOCUS_DIR}/**
permissions:
  contents: read
  actions: read
concurrency:
  group: cp7-mandor-zero-effect-focus-single
  cancel-in-progress: false
"""
    suffix = f"""    - name: Run one exact correction case and prove database recovery
      working-directory: writer
      env:
        CP7_FOCUS_APPROVED_REF: refs/heads/{approved_branch}
        CP6_FIXTURE_SCHEMA_PROFILE: HOSTED_USAGE
      run: >-
        python -B ../focus-tools/{FOCUS_DIR}/focus_transaction.py
        --output ../focus-proof/MANDOR_ZERO_EFFECT_FOCUS.json
        --case-original ../focus-proof/MANDOR_ZERO_EFFECT_CASE_ORIGINAL.json.gz
    - name: Remove disposable database
      if: always()
      working-directory: base
      run: |
        if command -v supabase >/dev/null 2>&1 && test -d cp5-local; then
          supabase stop --workdir cp5-local --no-backup
        fi
    - uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
      if: always() && hashFiles('focus-proof/**') != ''
      with:
        name: cp7-mandor-zero-effect-focus-${{{{ github.run_attempt }}}}
        path: focus-proof
        retention-days: 30
        if-no-files-found: error
"""
    output = (header + body + suffix).encode()
    forbidden = (
        RUNTIME_ANCHOR.encode(), b"workflow_dispatch", b"Install pinned browser dependencies",
        b"Open actual desktop and mobile browsers", b"Confirm actual Mandor Original upload",
        b"Run current Mandor17 once",
    )
    if any(x in output for x in forbidden) or b"Focused Mandor correction with exact rollback" not in output:
        raise ValueError("CP7_FOCUS_FULL_RUNTIME_OR_SETUP_IDENTITY_LEAK")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--approved-branch", default=APPROVED_BRANCH)
    args = parser.parse_args()
    result = derive(args.source.read_bytes(), args.approved_branch)
    args.output.write_bytes(result)
    print({"status": "DERIVED", "bytes": len(result), "sha256": hashlib.sha256(result).hexdigest(),
           "approved_branch": args.approved_branch})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
