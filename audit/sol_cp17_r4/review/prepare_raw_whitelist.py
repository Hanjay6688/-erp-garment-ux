"""Hash a finite textual evidence list. Final reports/ZIP receipt stay outside it."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import argparse
import json
import subprocess

A = Path(__file__).resolve().parents[1]
REPO = A.parents[1]
IMAGE_ORIGINAL = 'ci_receipts/sol_artifacts/12158565737/files/cp45-browser-original/results.json'
DERIVATIVE = 'ci_receipts/derived/BUILD_cp45_browser_original_TEXT_ONLY.json'

def main():
    p = argparse.ArgumentParser(); p.add_argument('--final', action='store_true'); args = p.parse_args()
    receipt = json.loads((A / 'ci_receipts/OWN_CI_RECEIPT_FINAL.json').read_text())
    register = json.loads((A / 'ci_receipts/ROOT_RUN_REGISTER.json').read_text())
    if args.final:
        assert receipt['registered_run_count'] == receipt['terminal_run_count'] == len(register)
        assert receipt['provider_run_id_set_equal'] is True and receipt['all_selected_text_bytes_hash_verified'] is True
        assert (A / 'PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json').exists(), 'LAST_DISPUTE_ORIGINAL_NOT_REVIEWED'
        assert json.loads((A / 'PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json').read_text())['state'].startswith('READ_')
    build = json.loads((A / 'BUILD_RESULT_REVIEW.json').read_text())['image_derivatives'][0]
    assert build['path'] == DERIVATIVE and build['source_path'] == IMAGE_ORIGINAL and build['removed_image_attachment_count'] == 8
    assert sha256((A / IMAGE_ORIGINAL).read_bytes()).hexdigest() == build['source_sha256']
    assert sha256((A / DERIVATIVE).read_bytes()).hexdigest() == build['sha256']
    allowed = {'.json', '.jsonl', '.md', '.txt', '.csv', '.sarif', '.log', '.py', '.mjs', '.yml', '.yaml', '.patch'}
    paths = {}
    for file in (A / 'ci_receipts').rglob('*'):
        if not file.is_file() or file.suffix.lower() not in allowed or '__pycache__' in file.parts:
            continue
        rel = str(file.relative_to(A))
        if rel == IMAGE_ORIGINAL:
            continue
        if rel.startswith('ci_receipts/sol_artifacts/') and '/files/' in rel:
            category = 'OWN_ORIGINAL_SELECTED_TEXT'
        elif rel.startswith('ci_receipts/own_job_logs/'):
            category = 'OWN_EXACT_DECODED_LOG'
        elif 'writer_' in rel:
            category = 'WRITER_REUSED_RAW_OR_CAPTURE_METADATA'
        elif 'retained_r3/' in rel:
            category = 'RETAINED_SOL_R3_REFERENCE_ZERO_R4_RUNTIME'
        elif rel == DERIVATIVE:
            category = 'TEXT_ONLY_DERIVATIVE_EIGHT_PNG_PAYLOADS_REMOVED'
        elif file.name == 'REPRODUCTION_SOURCE_SNAPSHOT.json':
            category = 'EXACT_GIT_REPRODUCTION_SOURCE_SNAPSHOT_NOT_RUNTIME_PROOF'
        elif file.name.startswith('STATIC_'):
            category = 'STATIC_SOURCE_NAVIGATION_ZERO_RUNTIME_CREDIT'
        elif file.name.startswith('SOL_') and file.suffix == '.jsonl':
            category = 'REVIEWED_CASE_LEDGER_WITH_ORACLE_AND_FIXTURE_ORIGINS'
        else:
            category = 'RAW_RECEIPT_METADATA_OR_EXACT_CAPTURE'
        paths[rel] = category
    tracked = subprocess.check_output(['git', 'ls-files', '--', 'audit/sol_cp17_r4/*.json'], cwd=REPO, text=True).splitlines()
    markers = ('PREEXECUTION', 'PREREQUISITE', 'VALIDATION', 'PROVENANCE', 'SOURCE_FREEZE')
    extra_names = {'Q1_QUALIFICATION_NEED.json', 'SCREEN_PREEXECUTION_INVENTORY.json', 'STATIC_GUARD_DEPENDENCY_MAP.json'}
    for path in tracked:
        file = REPO / path
        if any(marker in file.name for marker in markers) or file.name in extra_names:
            paths[str(file.relative_to(A))] = 'PUBLISHED_PREEXECUTION_EXPECTED_SOURCE_OR_VALIDATION'
    paths['PLAN_DISPOSITIONS.json'] = 'DECLARED_PLAN_WITHDRAWAL_AND_EXECUTED_COMPONENT_DISTINCTION'
    entries = []
    for rel, category in sorted(paths.items()):
        data = (A / rel).read_bytes()
        # Originals may be large, but every selected deliverable must be UTF-8 text.
        data.decode('utf-8')
        assert b'iVBORw0KGgo' not in data and b'data:image/png;base64' not in data and b'data:image/jpeg;base64' not in data, rel
        entries.append(dict(path='audit/sol_cp17_r4/' + rel, bytes=len(data), sha256=sha256(data).hexdigest(), category=category))
    result = dict(state='FINAL' if args.final else 'DRAFT_AWAITING_LAST_QUALIFICATION_AND_RECONCILIATION',
                  candidate_sha='663f6faefcbb9c70f0f99bbc7e78164e03521329', candidate_tree='023f3554432f80f994439f5d0b8cc164846a2041',
                  root='repository', files=len(entries), total_bytes=sum(r['bytes'] for r in entries),
                  registered_runs=len(register), reconciled_terminal_runs=receipt['terminal_run_count'],
                  category_counts=dict(Counter(r['category'] for r in entries)), entries=entries,
                  exclusions=[dict(path='audit/sol_cp17_r4/' + IMAGE_ORIGINAL, reason='Eight embedded PNG payloads; unchanged Original remains in scratch, text-only derivative and attachment hash metadata are selected.', source_sha256=build['source_sha256'], derivative='audit/sol_cp17_r4/' + DERIVATIVE, derivative_sha256=build['sha256']),
                              dict(artifact_id=12158226655, name='audit-r4-Sol-663f6fae-build-ux-erp-ux-dist', reason='Built application distribution, deliberately not downloaded as textual audit evidence.'),
                              dict(paths=['.github/workflows/audit-sol-r4-matching-pipeline.yml', 'audit/sol_cp17_r4/matching_pipeline_qualification.py', 'audit/sol_cp17_r4/MATCHING_PIPELINE_PREEXECUTION_MANIFEST.json', 'audit/sol_cp17_r4/MATCHING_PIPELINE_PREEXECUTION_VALIDATION.json'], reason='Unpublished withdrawn standalone plan. Executed matching_pipeline_case.py is separately retained via finite qualification/source snapshot.'),
                              dict(path='audit/sol_cp17_r4/WRITER_FAILURE_REVIEW_DRAFT.json', reason='Obsolete heuristic review; not accepted evidence.'),
                              dict(paths=['Final main report', 'FINDINGS.json', 'WRITER_HANDOFF.md', 'coverage matrices', 'SEAL_MANIFEST.json', 'RAW_EVIDENCE_ARCHIVE_RECEIPT.json'], reason='Small Git seal after ZIP receipt; kept outside this ZIP to avoid self-referential hashes.'),
                              dict(types=['screenshots', 'image payloads', 'binaries', 'runtime SQL dumps', 'temporary files', 'whole repository backup'], reason='Outside the selected textual audit-evidence package.')],
                  capture_limits=['Decoded log hashes identify stored exact connector text, not remote provider ZIP-log bytes. Writer22log capture LF disclosure remains in LOG_CAPTURE_FORMAT.json.',
                                  'Static/source snapshots do not create execution credit. Source snapshot includes available published audit tools, not a claim that every available file executed.',
                                  'Eight attachments are preserved only as count/hash metadata in the derivative; no visual acceptance is inferred from payloads.'])
    (A / 'RAW_EVIDENCE_WHITELIST.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['state', 'files', 'total_bytes', 'registered_runs', 'reconciled_terminal_runs']}))

if __name__ == '__main__': main()
