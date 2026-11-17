"""Verify the installed SKU parent on a disposable database for Global."""

import argparse
from contextlib import contextmanager
from datetime import date
from hashlib import file_digest, sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from zipfile import ZipFile

from realtime_comparator import prepare as prepare_catalogue_check
from snapshot_prerequisites import observe as observe_prerequisites
from sku_inputs import HEAD, TREE, git
from sku_progress import before_mandor, observe as stage, runtime_with_progress
from p21 import mode as p21_mode


REPO = p21_mode.REPOSITORY
FOCUSED_BRANCH = 'cp7/focused-b-browser'
ORIGINAL = 'Hanjay6688/-erp-garment-ux'
ARTIFACT = 14011544457
RUN = 43347020525
ARCHIVE_PIN = (166093725, 'de951319b2e9a31c490e2a2dc75a4985561e381256085c10d162264576e54c27')
CATALOGUE = 'SKU_GLOBAL_PARENT_ACTUAL_FULL25.json'
CATALOGUE_PIN = dict(bytes=16051957, sha256='ecf858d67f43c0967cfe6f38c51338dea64331ef6c0d1264786a8967f856e2a4')
QUALIFICATION = 'CP7_SKU_CURRENT_PARENT_MONEY_AUTOMATIC_QUALIFICATION.json'
QUALIFICATION_PIN = (8962731, '21199c40956e85b00b219548114741730f0e4f6a7109c7a30c70f763e0d17b75')
SKU = 'scripts/current-sku-automatic-composite-preparation'
FENCE = 'scripts/current-sku-managed-recovery-native27-qualification/source_context.py'
COMPARATOR_SHA = '44d6c946a6a3b9364ff4bd71e434fd8d0bf0d07787649d207a88bed021400ba3'
SKU_ENTRY_SHA = 'fb1dd131c0853b4feb80506d914b0984bac1a8babf53fdf5350eec0f84327a15'


def require(value, reason):
    if not value:
        raise ValueError(reason)


def check_context(action):
    """Admit only source preparation in the exact E22 workflow."""
    p21_mode.public_identity(os.environ.get('GITHUB_SHA', ''))
    require(sys.flags.optimize == 0 and action in ('retrieve', 'source'),
            'P21_PUBLIC_SOURCE_PREPARATION_ONLY')

def pin(raw):
    return len(raw), sha256(raw).hexdigest()


def retrieve(path):
    api = ('gh', 'api', f'repos/{ORIGINAL}/actions/artifacts/{ARTIFACT}')
    metadata = json.loads(subprocess.check_output(api, stderr=subprocess.PIPE, timeout=45))
    require(metadata['id'] == ARTIFACT and metadata['workflow_run']['id'] == RUN
            and metadata['workflow_run']['head_sha'] == HEAD and not metadata['expired']
            and (metadata['size_in_bytes'], metadata['digest']) == (ARCHIVE_PIN[0], 'sha256:' + ARCHIVE_PIN[1]),
            'PRIVATE_GLOBAL_EXACT_SKU_ARTIFACT_REQUIRED')
    with path.open('xb') as output:
        subprocess.run((*api[:-1], api[-1] + '/zip'), stdout=output, stderr=subprocess.PIPE, timeout=240, check=True)


def retained(path):
    with path.open('rb') as stream:
        require((path.stat().st_size, file_digest(stream, 'sha256').hexdigest()) == ARCHIVE_PIN,
                'PRIVATE_GLOBAL_EXACT_SKU_ARCHIVE_REQUIRED')
    with ZipFile(path) as archive:
        catalogue = archive.read(CATALOGUE)
        qualification = archive.read(QUALIFICATION)
    require(pin(catalogue) == (CATALOGUE_PIN['bytes'], CATALOGUE_PIN['sha256'])
            and pin(qualification) == QUALIFICATION_PIN, 'PRIVATE_GLOBAL_EXACT_SKU_REPORT_MEMBERS_REQUIRED')
    report = json.loads(qualification)
    require(report['qualification_commit'] == HEAD and report['status'] == 'PASS'
            and report['actual_Native_cases'] == 25 and report['actual_browser_cases'] == 2
            and report['cp6_restored'] is True and report['advisor_gate'] is True
            and report['production_go'] is False, 'PRIVATE_GLOBAL_SUCCESSFUL_SKU_REPORT_REQUIRED')
    case, = report['committed'].values()
    original = case['Global_parent_catalogue']
    require((original['head'], original['run_id'], original['attempt']) == (HEAD, str(RUN), 1)
            and {k: original['original'][k] for k in CATALOGUE_PIN} == CATALOGUE_PIN
            and original['fingerprint']['groups'] == 25, 'PRIVATE_GLOBAL_EXACT_SAME_RUN_FULL25_REQUIRED')
    return catalogue, original['fingerprint'], report['source_declaration']['complete_combined_sources']


@contextmanager
def source_engine(workspace, expected_sources, *, full_check, use_reviewed_digest=False):
    root = workspace / 'auditor'
    require((git(root, 'rev-parse', 'HEAD'), git(root, 'rev-parse', 'HEAD^{tree}')) == (HEAD, TREE)
            and not git(root, 'status', '--porcelain', '--untracked-files=no'), 'PRIVATE_GLOBAL_EXACT_SKU_SOURCE_REQUIRED')
    os.chdir(workspace / 'writer')
    path = root / SKU / 'qualification.py'
    require(pin(path.read_bytes())[1] == SKU_ENTRY_SHA, 'PRIVATE_GLOBAL_EXACT_SKU_DIAGNOSTIC_ENTRY_REQUIRED')
    spec = spec_from_file_location('global_retained_sku_owner', path)
    entry = module_from_spec(spec)
    spec.loader.exec_module(entry)
    sys.path[:0] = [str(path.parent)]
    fence = entry.load('global_retained_sku_source_fence', entry.FROZEN_AFUI / FENCE)
    with entry.inherited_scope():
        with fence.fenced_source_read() as observations:
            engine = (entry.runtime() if full_check else
                      runtime_with_progress(entry, use_reviewed_digest=use_reviewed_digest))
            with engine.inherited_admission.parent_scope():
                source = engine.admitted()['complete_combined_sources'] if full_check else engine.product.sources()
                require(source == expected_sources, 'PRIVATE_GLOBAL_EXACT_QUALIFIED_SKU_INSTALL_GRAPH_REQUIRED')
        require(not observations['attempts'] and not observations['network_nonGit_attempts'],
                'PRIVATE_GLOBAL_SOURCE_FENCE_REQUIRED')
        with engine.inherited_admission.parent_scope():
            yield entry, engine


def probe(workspace, catalogue, fingerprint, expected_sources, output, *, browser=None, dated_preseal=False,
          expanded_review=None):
    require(expanded_review is None or (dated_preseal and browser is None), 'PRIVATE_GLOBAL_EXPANDED_RELATION_PRESEAL_ONLY')
    comparator_source = Path(__file__).with_name('parent_catalogue.py')
    require(pin(comparator_source.read_bytes())[1] == COMPARATOR_SHA, 'PRIVATE_GLOBAL_REVIEWED_COMPARATOR_CHANGED')
    with source_engine(workspace, expected_sources, full_check=False,
                       use_reviewed_digest=browser is not None or dated_preseal) as (entry, engine):
        # Import the released package from the frozen harness. Use the same
        # package files, boundary lock, role authority and SKU installers.
        import psycopg

        package = engine.package
        admin = package.boundary.ADMIN
        with psycopg.connect(admin) as conn, conn.cursor() as cur:
            require((conn.info.host, conn.info.port, conn.info.dbname) == ('127.0.0.1', 54322, 'cp6_rollback')
                    and cur.execute('show server_version_num').fetchone() == ('170006',),
                    'PRIVATE_GLOBAL_EXACT_LOCAL_DISPOSABLE_DB_REQUIRED')
        require(package.ledger(admin)['app'][-1] == 'v2.6.20ab' and package.capsule_compare(admin)['equal'] is True,
                'PRIVATE_GLOBAL_EXACT_ALIGNED_AB_CLONE_REQUIRED')
        result = package.package.install(output / 'T3_PACKAGE_FILES_INSTALL.json')
        require(result['status'] == 'ALL_FILES_INSTALLED' and len(result['files']) == 30,
                'PRIVATE_GLOBAL_AC_TO_BF_PACKAGE_INSTALL_REQUIRED')
        require(package.verify_awx()['stage'] == 'BE_PLUS_BF_T1', 'PRIVATE_GLOBAL_EXACT_BF_REQUIRED')
        print('GLOBAL_PARENT_T3_BF_VERIFIED stages=30', flush=True)
        capture, live_fingerprint, groups = entry.load('global_exact_retained_catalogue',
            workspace / 'auditor' / SKU / 'global_parent_catalogue.py').exact_readers()
        comparator = entry.load('global_exact_retained_comparator', comparator_source)
        reviewed = comparator.reviewed_fields(catalogue, CATALOGUE_PIN)
        compare = prepare_catalogue_check(comparator, catalogue, CATALOGUE_PIN, archived_startup_day=date(2026, 11, 13))
        inputs = dict(parent_catalogue_fingerprint=fingerprint, parent_catalogue_equivalence=reviewed)
        from sku_credit_seal import prepare as prepare_credit_seal

        credit = prepare_credit_seal(entry)
        baseline_catalogue = engine.predecessor.catalog
        with psycopg.connect(admin) as conn, conn.cursor() as cur:
            before = capture(cur)
            data = baseline_catalogue._data(cur)
        data_hashes = engine.drill.data_hashes('cp6_rollback')
        if browser is not None:
            profile = engine.database._database_profile('cp6_rollback')
            dump = '/tmp/cp7_focused_b_bf_pre.dump'
            with stage('BF_BACKUP'):
                engine.dump.dump('cp6_rollback', dump)
        os.environ['CP6_FIXTURE_SCHEMA_PROFILE'] = 'HOSTED_USAGE'
        committed = False
        failure = None
        try:
            if browser is not None or dated_preseal:
                engine.runner.scheduler_quiet(admin)
            with engine.trusted_installer_connection() as conn, conn.cursor() as cur:
                try:
                    engine.current_native.acquire_boundary(cur)
                    print('GLOBAL_PARENT_INSTALL_SKU_PREDECESSORS', flush=True)
                    with before_mandor(lambda: credit.record_baseline(cur)):
                        prior = engine._sku_install_parent(cur)
                    print('GLOBAL_PARENT_INSTALL_SKU_DELTA', flush=True)
                    with stage('SKU_AUTOMATIC_DELTA'):
                        state = engine._sku_install_delta(cur, prior)
                    with stage('SKU_AUTOMATIC_VERIFY'):
                        engine._sku_verify_installed(cur, state)
                    with stage('SKU_CREDIT_RESEAL'):
                        current_data = baseline_catalogue._data(cur)
                        credit.install_final(cur)
                        require(baseline_catalogue._data(cur) == current_data,
                                'PRIVATE_GLOBAL_CREDIT_RESEAL_CHANGED_ROWS_OR_SEQUENCES')
                    with stage('SKU_FULL25_COMPARE'):
                        current = capture(cur)
                        require(set(current) == groups, 'PRIVATE_GLOBAL_FULL25_REQUIRED')
                        with credit.owning._postgres_reader(cur):
                            proof = compare(cur, current, inputs, live_fingerprint)
                        require(proof['status'] == 'GLOBAL_ACTUAL_PARENT_CATALOGUE_AND_CENSUS_VERIFIED',
                                'PRIVATE_GLOBAL_LIVE_SKU_CATALOGUE_REQUIRED')
                    prerequisites = observe_prerequisites(cur)
                    require(prerequisites['status'] == 'PASS', 'PRIVATE_GLOBAL_LIVE_ACCOUNT_RPC_PREREQUISITES_REQUIRED')
                    print('GLOBAL_PARENT_LIVE_SKU_VERIFIED groups=25 account_mappings=4 public_rpcs=10', flush=True)
                    if browser is not None or dated_preseal:
                        from global_preseal import ScopeRefused

                        from dated_global_preseal import prepare, reviewed_relations

                        sku_data = baseline_catalogue._data(cur)
                        scope_refused = None
                        try:
                            with cur.connection.transaction(force_rollback=True), stage('GLOBAL_PRESEAL'):
                                with prepare(workspace / 'global-candidate', catalogue, fingerprint, output,
                                             verify_as=credit.owning._postgres_reader, expanded_review=expanded_review) as observe:
                                    observation = observe(cur)
                                require(observation.get('preseal_savepoint_restored') is True
                                        and observation.get('sealed_profile_rows') == 0,
                                        'PRIVATE_GLOBAL_DATED_PRESEAL_EXACT_INVERSE_REQUIRED')
                                if expanded_review is not None:
                                    require([r['qualified_name'] for r in observation['observed']['relations']]
                                            == reviewed_relations(expanded_review),
                                            'PRIVATE_GLOBAL_EXACT_EXPANDED_RELATION_OBSERVATION_REQUIRED')
                        except ScopeRefused as error:
                            require(error.report.get('owning_transaction_still_open') is True
                                    and error.report.get('preseal_savepoint_restored') is True,
                                    'PRIVATE_GLOBAL_PRESEAL_RESTORE_REQUIRED_BEFORE_BROWSER')
                            print_failure('GLOBAL_PARENT_PRESEAL_SCOPE_REFUSED', error)
                            scope_refused = error
                        except Exception as error:
                            print_failure('GLOBAL_PARENT_PRESEAL_FIRST_FAILURE', error)
                            if browser is None:
                                raise
                        require(capture(cur) == current and baseline_catalogue._data(cur) == sku_data,
                                'PRIVATE_GLOBAL_PRESEAL_RESTORE_REQUIRED_BEFORE_BROWSER')
                        credit.verify_live(cur)
                        print('GLOBAL_PARENT_SKU_RESTORED_AFTER_PRESEAL', flush=True)
                        if scope_refused is not None and expanded_review is not None:
                            raise scope_refused
                    if browser is not None:
                        committed = True
                        conn.commit()
                finally:
                    conn.rollback()
            if browser is not None:
                with stage('B_BROWSER'):
                    browser.run(workspace, output, capture, current, baseline_catalogue, engine.drill,
                                verify_credit_copy=credit.verify_copy)
        except Exception as error:
            failure = error
            print_failure('GLOBAL_LIVE_PARENT_FIRST_FAILURE', error)
            raise
        finally:
            try:
                if committed:
                    with stage('BF_RESTORE'):
                        restored = engine.database._restore(dump, 'cp6_rollback', profile)
                    require(restored['only_pg_cron_errors'], 'PRIVATE_GLOBAL_FOCUSED_B_FULL_BF_RESTORE_REQUIRED')
                with psycopg.connect(admin) as conn, conn.cursor() as cur:
                    if committed:
                        roles_before = {name for name, _ in before['roles'] if name.startswith('cp7_')}
                        roles_created = {name for name, _ in current['roles'] if name.startswith('cp7_')} - roles_before
                        engine.role_cleanup.restore_roles(cur, roles_before, roles_created, engine.database._roles)
                        conn.commit()
                    restored_catalogue = capture(cur)
                    if committed:
                        # Restore allocates new OIDs. Use the owning engine's exact portable
                        # projection, retaining the three additional dispatch catalogue groups.
                        extra = {'operators', 'casts', 'languages'}
                        for group in extra:
                            require(restored_catalogue[group] == before[group], 'PRIVATE_GLOBAL_FOCUSED_B_DISPATCH_CHANGED')
                        def portable(value):
                            return baseline_catalogue._portable({k: dict(v) for k, v in value.items() if k not in extra})
                        same_catalogue = portable(restored_catalogue) == portable(before)
                    else:
                        same_catalogue = restored_catalogue == before
                    require(same_catalogue and baseline_catalogue._data(cur) == data,
                            'PRIVATE_GLOBAL_BF_ROLLBACK_CATALOGUE_ROWS_SEQUENCES_CHANGED')
                require(engine.drill.data_hashes('cp6_rollback') == data_hashes,
                        'PRIVATE_GLOBAL_BF_ROLLBACK_DATABASE_ROWS_CHANGED')
                print('GLOBAL_PARENT_BF_RESTORE_VERIFIED catalogue=true rows=true sequences=true' if committed else
                      'GLOBAL_PARENT_BF_ROLLBACK_VERIFIED catalogue=true rows=true sequences=true', flush=True)
                if browser is not None:
                    browser.bf_restored(output)
            except Exception as error:
                print_failure('GLOBAL_LIVE_PARENT_RESTORE_FAILURE', error)
                if failure is None:
                    raise
            finally:
                if browser is not None:
                    engine.drill.docker('rm', '-f', dump, check=False)
    print(json.dumps(dict(status='GLOBAL_LIVE_SKU_PARENT_VERIFIED', original_sku_run=RUN, parent_tree=TREE,
                          actual_sku_cases=0, actual_global_cases=0, production_go=False)), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('retrieve', 'source', 'preseal-source', 'dated-preseal-source',
                                          'probe', 'focused-b', 'dated-preseal'))
    parser.add_argument('--expanded-relations', action='store_true')
    args = parser.parse_args()
    check_context(args.action)
    branch = os.environ['GITHUB_REF_NAME']
    expanded_review = None
    if args.expanded_relations:
        require(branch == 'cp7/global-inputs' and args.action in ('dated-preseal-source', 'dated-preseal'),
                'PRIVATE_GLOBAL_EXPANDED_RELATION_PRESEAL_ONLY')
        from dated_global_preseal import EXPANDED_REVIEW_NAME
        from global_preseal import INPUTS

        expanded_review = INPUTS / EXPANDED_REVIEW_NAME
    if args.action in ('probe', 'focused-b'):
        require((args.action == 'focused-b') == (branch == FOCUSED_BRANCH), 'PRIVATE_GLOBAL_EXACT_LANE_REQUIRED')
    if args.action in ('preseal-source', 'dated-preseal-source', 'dated-preseal'):
        require(branch == FOCUSED_BRANCH or expanded_review is not None, 'PRIVATE_GLOBAL_EXACT_LANE_REQUIRED')
    workspace = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    output = Path(os.environ['RUNNER_TEMP']).resolve() / 'cp7-live-parent'
    output.mkdir(mode=0o700, exist_ok=True)
    archive = output / 'sku-original.zip'
    if args.action == 'retrieve':
        retrieve(archive)
        retained(archive)
        print('GLOBAL_PARENT_EXACT_SKU_ORIGINAL_VERIFIED', flush=True)
        return
    catalogue, fingerprint, sources = retained(archive)
    comparator = Path(__file__).with_name('parent_catalogue.py')
    require(pin(comparator.read_bytes())[1] == COMPARATOR_SHA, 'PRIVATE_GLOBAL_REVIEWED_COMPARATOR_CHANGED')
    retained_settings = json.loads((output / 'sku-settings.json').read_bytes())
    require(not any(key.startswith('GITHUB_') or key == 'GH_TOKEN' for key in retained_settings),
            'PRIVATE_GLOBAL_INHERITED_INPUTS_CANNOT_CHANGE_JOB_IDENTITY')
    os.environ.update(retained_settings)
    if args.action == 'source':
        from sku_credit_seal import prepare as prepare_credit_seal
        from sku_digest_binding import bind as prepare_digest

        with source_engine(workspace, sources, full_check=True) as (entry, _):
            prepare_credit_seal(entry)
            prepare_digest(entry)
            print('GLOBAL_PARENT_EXACT_SKU_INSTALL_GRAPH_VERIFIED', flush=True)
        return
    if args.action in ('preseal-source', 'dated-preseal-source'):
        if args.action == 'dated-preseal-source':
            from dated_global_preseal import prepare
        else:
            from global_preseal import prepare

        kwargs = {} if expanded_review is None else {'expanded_review': expanded_review}
        with prepare(workspace / 'global-candidate', catalogue, fingerprint, output, **kwargs):
            return
    browser = None
    if args.action == 'focused-b':
        import b_focused_browser as browser
    probe(workspace, catalogue, fingerprint, sources, output, browser=browser,
          dated_preseal=args.action == 'dated-preseal', expanded_review=expanded_review)


def print_failure(label, error):
    # Keep SQL, fixture rows, paths and authentication material out of job logs.
    message = str(error)
    safe = re.match(r'^(?:[A-Z][A-Z0-9_]{7,110})\b', message)
    code = getattr(error, 'sqlstate', '') or ''
    print(label, type(error).__name__, safe[0] if safe else '', code, flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print_failure('GLOBAL_LIVE_PARENT_FAILURE', error)
        filename = getattr(error, 'filename', None)
        if isinstance(error, FileNotFoundError) and filename:
            path = Path(filename)
            for base in ('GITHUB_WORKSPACE', 'RUNNER_TEMP'):
                root = Path(os.environ[base])
                if path.is_relative_to(root):
                    name = path.relative_to(root).as_posix()
                    if re.fullmatch(r'[A-Za-z0-9./_-]{1,220}', name):
                        print('GLOBAL_LIVE_PARENT_FAILURE missing', name, flush=True)
                    break
        raise SystemExit(1) from None

