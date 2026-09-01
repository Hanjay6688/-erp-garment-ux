#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/cp3-r4-full-schema-validation.yml'
MANIFEST = ROOT / 'docs/evidence/cp3_r4_source_hashes.json'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected one anchor, found {count}')
    return text.replace(old, new, 1)


workflow = WORKFLOW.read_text(encoding='utf-8')

# Exact least privilege needed only to publish/update the draft review boundary.
if re.search(r'^permissions:\s*$', workflow, flags=re.M):
    block = re.search(r'^permissions:\s*$\n(?:^[ ]{2}[^\n]+\n)+', workflow, flags=re.M)
    if block is None:
        raise SystemExit('R4 publisher could not parse the permissions block')
    replacement = 'permissions:\n  contents: read\n  pull-requests: write\n'
    workflow = workflow[:block.start()] + replacement + workflow[block.end():]
else:
    workflow = replace_once(
        workflow,
        '\njobs:\n',
        '\npermissions:\n  contents: read\n  pull-requests: write\n\njobs:\n',
        'R4 workflow jobs anchor',
    )

# Bind the artifact metadata outputs to a stable step id.
if 'id: cp3_r4_proof_upload' not in workflow:
    pattern = re.compile(
        r'(?P<indent>^[ ]+)- name: (?P<name>[^\n]*Upload[^\n]*CP3 R4[^\n]*proof[^\n]*)\n'
        r'(?P<body>(?:^(?P=indent)[ ]+[^\n]*\n)*?)'
        r'^(?P=indent)[ ]+uses: actions/upload-artifact@v4\n',
        flags=re.M | re.I,
    )
    match = pattern.search(workflow)
    if match is None:
        # Generated workflow can retain the R3 wording while already using the R4 artifact name.
        artifact_name_pos = workflow.find('name: cp3-r4-full-schema-proof')
        if artifact_name_pos < 0:
            raise SystemExit('R4 publisher could not find the proof artifact step')
        step_start = workflow.rfind('\n      - name:', 0, artifact_name_pos)
        uses_pos = workflow.find('\n        uses: actions/upload-artifact@v4', step_start, artifact_name_pos + 200)
        if step_start < 0 or uses_pos < 0:
            raise SystemExit('R4 publisher could not locate the proof upload action')
        insert_at = uses_pos + 1
        workflow = workflow[:insert_at] + '        id: cp3_r4_proof_upload\n' + workflow[insert_at:]
    else:
        uses_start = match.end() - len('        uses: actions/upload-artifact@v4\n')
        indent = match.group('indent') + '  '
        workflow = workflow[:uses_start] + f'{indent}id: cp3_r4_proof_upload\n' + workflow[uses_start:]

# Insert after the proof upload block, before teardown/cleanup. The step only runs
# on the normal success path and therefore cannot publish a failed candidate.
if 'Publish exact frozen R4 writer-proof boundary' not in workflow:
    artifact_name_pos = workflow.find('name: cp3-r4-full-schema-proof')
    step_start = workflow.rfind('\n      - name:', 0, artifact_name_pos)
    next_step = workflow.find('\n      - name:', artifact_name_pos)
    if artifact_name_pos < 0 or step_start < 0 or next_step < 0:
        raise SystemExit('R4 publisher could not find proof upload step boundaries')

    publisher = r'''
      - name: Publish exact frozen R4 writer-proof boundary
        shell: bash
        env:
          GH_TOKEN: ${{ github.token }}
          PROOF_ARTIFACT_ID: ${{ steps.cp3_r4_proof_upload.outputs.artifact-id }}
          PROOF_ARTIFACT_DIGEST: ${{ steps.cp3_r4_proof_upload.outputs.artifact-digest }}
        run: |
          set -euo pipefail
          test -n "$PROOF_ARTIFACT_ID"
          test -n "$PROOF_ARTIFACT_DIGEST"
          test "$GITHUB_REF_NAME" = "cp3/hpp-attendance-sewing-terminal-r4-20260901"
          test "$(git rev-parse HEAD)" = "$GITHUB_SHA"

          JOB_ID="$(gh api "repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/jobs?per_page=100" \
            --jq '.jobs[] | select(.name=="validate-full-schema") | .id' | head -n1)"
          test -n "$JOB_ID"

          cat > /tmp/cp3-r4-pr-body.md <<EOF
          ## FROZEN REVIEW BOUNDARY — DRAFT ONLY

          **DO NOT MERGE. DO NOT APPLY TO ERP ENTENG UAT. DO NOT MUTATE ERP GARMENT LEGACY.**

          ### Exact identity

          - base branch: `main`
          - exact base SHA: `bf3ce8e2821f120d8abd8788daf07f6da7c15459`
          - head branch: `cp3/hpp-attendance-sewing-terminal-r4-20260901`
          - **exact frozen head SHA: `${GITHUB_SHA}`**
          - reviewed R3 parent SHA: `366a4b2fb6f6daa0ef1d9d47a78c7b83a8c89ceb`
          - schema fingerprint: `a0c59b96b3879edd28f3d8c57d0894a3`

          Any head movement invalidates this boundary. Emit `CONCURRENT_WRITER_DETECTED` and stop if the observed head differs.

          ### R4 writer proof

          - workflow: `CP3 R4 Full-Schema Validation`
          - run: `${GITHUB_RUN_ID}`
          - job: `${JOB_ID}`
          - result before this success-gated publisher: **SUCCESS**
          - artifact: `cp3-r4-full-schema-proof`
          - artifact ID: `${PROOF_ARTIFACT_ID}`
          - artifact digest: `${PROOF_ARTIFACT_DIGEST}`

          The workflow reached this publisher only after exact CP2 restore, source hash verification, R3 regressions, v2.6.14d apply, strict nested JSON runtime matrix, 2,000-destination benchmark, real two-session R4 races, accounting reconciliation, reviewed rollback, byte-equivalent function/ACL restoration, and zero-residue gates completed successfully.

          ### R4 findings addressed

          1. APPROVE payroll versus ACTIVE pool lock/guard in both orders.
          2. Policy update versus ACTIVE pool lock/overlap guard in both orders; non-overlapping future policy remains allowed.
          3. Owning work-completion reversal cannot bypass unreversed `SELESAI_DIJAHIT`; shared Asia/Jakarta business-date lock is used.
          4. Generic/service-role journal reversal cannot reverse `ATTENDANCE_HPP_POOL` or `PAYROLL_ATTENDANCE_ACCRUAL`; owning cancellation/reversal remains compatible through a private primitive.
          5. Exact restored-schema source/destination JSON proof covers missing/null/extra/wrong-type/string-boolean/empty/nested-missing cases.

          ### Truth boundary

          - SOURCE: writer full-schema/runtime proof **PASS; independent audit pending**
          - ERP Enteng UAT: **UNCHANGED / NOT APPLIED**
          - ERP Garment legacy: **UNCHANGED / READ-ONLY**
          - main: **UNCHANGED**
          - Auth/RLS browser E2E: **NOT RUN / OUTSIDE CP3**
          - backend-connected frontend: **NO**
          - production go: **NO**

          Only Work Sol Max may issue `CP3 SOURCE CANDIDATE: PASS FOR CP4 UAT APPLICATION`.
          Chat Sol Pro is parked during the independent re-audit.
          EOF

          EXISTING="$(gh api "repos/${GITHUB_REPOSITORY}/pulls?state=open&head=${GITHUB_REPOSITORY_OWNER}:cp3/hpp-attendance-sewing-terminal-r4-20260901&base=main&per_page=10" --jq '.[0].number // empty')"
          if [ -z "$EXISTING" ]; then
            PR_NUMBER="$(gh api "repos/${GITHUB_REPOSITORY}/pulls" \
              --method POST \
              -f title='CP3 R4 race-safe attendance HPP candidate for independent re-audit' \
              -f head='cp3/hpp-attendance-sewing-terminal-r4-20260901' \
              -f base='main' \
              -F draft=true \
              --raw-field body="$(cat /tmp/cp3-r4-pr-body.md)" \
              --jq '.number')"
          else
            PR_NUMBER="$EXISTING"
            gh api "repos/${GITHUB_REPOSITORY}/pulls/${PR_NUMBER}" \
              --method PATCH \
              -f title='CP3 R4 race-safe attendance HPP candidate for independent re-audit' \
              --raw-field body="$(cat /tmp/cp3-r4-pr-body.md)" >/dev/null
          fi
          echo "CP3_R4_FROZEN_PR=${PR_NUMBER}"

          if gh api "repos/${GITHUB_REPOSITORY}/pulls/16" --jq '.state' 2>/dev/null | grep -qx open; then
            gh api "repos/${GITHUB_REPOSITORY}/pulls/16" --method PATCH \
              -f state=closed \
              -f title='[SUPERSEDED BY R4] CP3 R3 target-faithful attendance HPP candidate' \
              --raw-field body="Superseded without merge by draft R4 PR #${PR_NUMBER} at exact frozen head `${GITHUB_SHA}` after independent review returned five P1 findings. Do not review, merge, or apply PR #16. ERP Enteng UAT and ERP Garment legacy remain unchanged." >/dev/null
          fi
'''
    workflow = workflow[:next_step] + publisher + workflow[next_step:]

WORKFLOW.write_text(workflow, encoding='utf-8')

manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
for rel in manifest['files']:
    data = (ROOT / rel).read_bytes()
    manifest['files'][rel] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps({'status': 'PASS', 'success_gated_pr_publisher': True, 'hashed_files': len(manifest['files'])}, sort_keys=True))
