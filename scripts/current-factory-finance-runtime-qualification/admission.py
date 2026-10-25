"""Require actual current Native20 and current-chain minute cron before factory use."""
from pathlib import Path
from hashlib import sha256
import json
import os
import subprocess


PROOF_NAMES = {'ALIGNED_CHAIN.json', 'CLONE_install.clone-erp.sql',
    'CLONE_install.connection-fence.txt', 'CLONE_install.database-identity.txt',
    'CLONE_install.source-erp.sql', 'CLONE_install.txt',
    'T3_PACKAGE_FILES_INSTALL.json', 'T3_PACKAGE_INSTALL.json',
    'T3_BACKUP_RESTORE_DRILL.json', 'CP7_CURRENT_FACTORY_FINANCE1.json'}


def source_worktree(repo):
    changed = subprocess.check_output(['git', '-C', str(repo), 'diff', 'HEAD', '--name-only'], text=True).splitlines()
    assert not changed, ('FACTORY_TRACKED_SOURCE_CHANGED', changed)
    untracked = subprocess.check_output(['git', '-C', str(repo), 'ls-files', '--others', '--exclude-standard', '-z'], text=True).split('\0')
    untracked = [p for p in untracked if p]
    allowed = {'cp6-proof/t3/' + name for name in PROOF_NAMES}
    refused = sorted(set(untracked) - allowed)
    assert not refused, ('FACTORY_UNDECLARED_UNTRACKED_PATH', refused)
    return dict(tracked_sources_clean=True, declared_untracked_proof_paths=sorted(untracked),
                source_hashes_checked_separately=True)


def admitted(repo, here, ids, product, native):
    predecessor = native.admitted()
    assert predecessor['current_installation'] == product.sources()
    pins = json.loads((here / 'SOURCE.json').read_bytes())
    assert pins['case_ids'] == list(ids) and len(ids) == 1
    for path, digest in pins['files'].items():
        assert sha256((repo / path).read_bytes()).hexdigest() == digest, path
    worktree = source_worktree(repo)
    proofs = pins['actual_qualification_originals']
    assert set(proofs) == {'CURRENT_MODEL_TARGET_ORIGINAL_REPORT', 'CURRENT_MODEL_TARGET_CRON_ORIGINAL_REPORT'}
    verified = {}
    for variable, proof in proofs.items():
        raw = Path(os.environ[variable]).read_bytes()
        assert len(raw) == proof['bytes'] and sha256(raw).hexdigest() == proof['sha256']
        actual = json.loads(raw)
        assert actual['status'] == proof['status'] == 'PASS'
        assert actual['cp6_restored'] and actual['advisor_gate'] and actual['required_case_ids_pass']
        assert actual['baseline_full22_all_rows_all_sequences_equal'] and actual['baseline_advisors_equal']
        assert actual['source_declaration']['current_installation'] == product.sources()
        if variable == 'CURRENT_MODEL_TARGET_ORIGINAL_REPORT':
            assert actual['native']['counts'] == {'PASS': 20} and actual['observed_case_count'] == 20
            assert actual['required_case_ids'] == predecessor['qualification']['case_ids']
        else:
            case_id = 'CURRENT_FINANCE_MODEL_ACTUAL_MINUTE_CRON_BOUNDED_READY_AND_DEFERRED'
            assert actual['required_case_ids'] == [case_id] and actual['observed_case_count'] == 1
            assert actual['actual_cron_claim'] and actual['manual_steps'] == 0 and not actual['changed_schedule']
            assert actual['scheduler_quiet_before_baseline_restore'] and actual['used_guard_refused_before_DDL']
            case = actual['committed'][case_id]
            assert case['status'] == 'PASS' and case['official_sections_and_metrics_exact']
            assert case['independent_book_signature'] and case['metric_count'] == 24
            assert case['unknown_never_zero'] and case['unchanged_production_minute_schedule']
            runner = 'scripts/current-model-target-cron-qualification/runner.py'
            assert actual['source_declaration']['qualification']['files'][runner] == sha256((repo / runner).read_bytes()).hexdigest()
        verified[variable] = dict(proof, observed_status='PASS')
    return dict(qualified_current_model_target=predecessor, current_installation=product.sources(),
                qualification=pins, actual_originals_verified=verified, source_worktree=worktree,
                synthetic_factory_scope=dict(commercial_skus=1200, sizes_per_sku=3, variants=3600),
                independent_acceptance=False, production_go=False)
