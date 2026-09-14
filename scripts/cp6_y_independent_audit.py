#!/usr/bin/env python3
"""Independent Y audit. Real authenticated SQL; no hosted database or HTTP claim.
Exit 1: qualified counterexample. Exit 2: incomplete proof/fixture. No business SQL edits.
"""
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import uuid
import zipfile
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path, PurePosixPath
from zoneinfo import ZoneInfo

HEAD_Y = 'bde9da786e3cde94cdb96e953310e5fac46f8574'
TREE_Y = '81f5d1c57622c59d36409e70032a632ae9af0157'
OUT = Path('cp6-proof/independent-y')
REPORT = OUT / 'Y_INDEPENDENT_AUDIT.json'
ZONES = ('Asia/Jakarta', 'UTC', 'Pacific/Kiritimati', 'Etc/GMT+12')
OLD_ARTIFACT = 10335276559
OLD_DIGEST = '88c66cf64909e246fe41b8b71cd03631d4eba10bf7451c69186e95c79fc2b871'


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def save(name, result):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(result, indent=2, default=str) + '\n')


def incoming():
    """Independent byte/source binder, with expected digest from the GitHub API."""
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise AssertionError('INCOMING_REQUIRES_DISPOSABLE_ACTIONS_RUN')
    api = json.loads(subprocess.check_output([
        'gh', 'api', 'repos/Hanjay6688/-erp-garment-ux/actions/artifacts/' + str(OLD_ARTIFACT)
    ], text=True))
    if (api['id'], api['digest'], api['expired'], api['workflow_run']['head_sha']) != (
            OLD_ARTIFACT, 'sha256:' + OLD_DIGEST, False, HEAD_Y):
        raise AssertionError('INCOMING_API_IDENTITY_OR_DIGEST_MISMATCH')
    save('Y_INCOMING_ARTIFACT_API.json', api)
    with tempfile.TemporaryDirectory(prefix='independent-y-incoming-') as d:
        archive = Path(d) / 'incoming.zip'
        with archive.open('wb') as stream:
            subprocess.run(['gh', 'api', 'repos/Hanjay6688/-erp-garment-ux/actions/artifacts/'
                            + str(OLD_ARTIFACT) + '/zip'], stdout=stream, check=True)
        actual = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
        if actual != OLD_DIGEST or archive.stat().st_size != api['size_in_bytes']:
            raise AssertionError('INCOMING_ARCHIVE_BYTES_MISMATCH')
        with zipfile.ZipFile(archive) as z:
            if len(z.infolist()) != 2 or set(z.namelist()) != {
                    'CP6_NATIVE_TRANSFER.json', 'CP6_NATIVE_PROOF.tar.xz'}:
                raise AssertionError('INCOMING_TRANSPORT_MEMBERS')
            transfer = json.loads(z.read('CP6_NATIVE_TRANSFER.json'))
            compressed = z.read('CP6_NATIVE_PROOF.tar.xz')
        if (len(compressed), hashlib.sha256(compressed).hexdigest()) != (
                transfer['archive']['bytes'], transfer['archive']['sha256']):
            raise AssertionError('INCOMING_COMPRESSED_BYTES')
        payload_path = Path(d) / 'payload.tar.xz'
        payload_path.write_bytes(compressed)
        observed = {}
        manifest = None
        selected = {}
        with tarfile.open(payload_path, 'r:xz') as tar:
            for member in tar:
                p = PurePosixPath(member.name)
                if not member.isfile() or p.is_absolute() or '..' in p.parts or '\\' in member.name or member.name in observed:
                    raise AssertionError('INCOMING_UNSAFE_OR_DUPLICATE_MEMBER:' + member.name)
                data = tar.extractfile(member).read()
                observed[member.name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
                if member.name == 'CP6_V2620Y_RUNTIME_MANIFEST.json':
                    manifest = json.loads(data)
                if member.name in ('H_MAINTENANCE_ROLLBACK/manifest.json',
                                   'cp6-auth-permission-e2e.json',
                                   'CP6_V2620Y_CASH_BUSINESS_DATE_REGRESSION.json',
                                   'FINAL_RECONCILIATION.json'):
                    selected[member.name] = json.loads(data)
        if manifest is None:
            raise AssertionError('INCOMING_MANIFEST_ABSENT')
        identity = manifest['identity']
        if (identity['head_sha'], identity['head_tree'], identity['run_id'], identity['run_attempt']) != (
                HEAD_Y, TREE_Y, 34809413932, 1):
            raise AssertionError('INCOMING_NATIVE_IDENTITY')
        if git('rev-parse', HEAD_Y + '^{tree}') != TREE_Y:
            raise AssertionError('INCOMING_GIT_TREE')
        if manifest['status'] != 'PASS_EXACT_LOCAL_DISPOSABLE_CI' or manifest['production_go'] is not False:
            raise AssertionError('INCOMING_STATUS')
        manifest_bytes = observed.pop('CP6_V2620Y_RUNTIME_MANIFEST.json')
        if manifest_bytes['sha256'] != transfer['runtime_manifest']['sha256']:
            raise AssertionError('INCOMING_MANIFEST_HASH')
        if set(observed) != set(manifest['proof_files']):
            raise AssertionError('INCOMING_PAYLOAD_SET')
        for name, info in observed.items():
            expected = manifest['proof_files'][name]
            if any(info[k] != expected[k] for k in ('bytes', 'sha256')):
                raise AssertionError('INCOMING_PAYLOAD_PIN:' + name)
        for name, expected in manifest['sources'].items():
            p = PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name:
                raise AssertionError('INCOMING_SOURCE_PATH')
            data = subprocess.check_output(['git', 'show', HEAD_Y + ':' + name])
            if (len(data), hashlib.sha256(data).hexdigest()) != (expected['bytes'], expected['sha256']):
                raise AssertionError('INCOMING_SOURCE_PIN:' + name)
            if 'platform_ledger_sha256' in expected and hashlib.sha256(data[:-1]).hexdigest() != expected['platform_ledger_sha256']:
                raise AssertionError('INCOMING_PLATFORM_PIN:' + name)
        if len(observed) != 10579 or len(manifest['sources']) != 195:
            raise AssertionError('INCOMING_COUNTS')
        result = dict(status='PASS_BYTE_AND_SOURCE_INTEGRITY', head=HEAD_Y, tree=TREE_Y,
                      artifact_id=OLD_ARTIFACT, artifact_sha256=actual,
                      payload_count=len(observed), source_count=len(manifest['sources']),
                      maintenance_case_count=len(selected['H_MAINTENANCE_ROLLBACK/manifest.json']['cases']),
                      auth_case_count=len(selected['cp6-auth-permission-e2e.json']['cases']),
                      y_writer_case_count=len(selected['CP6_V2620Y_CASH_BUSINESS_DATE_REGRESSION.json']['cases']),
                      independent_business_audit=False, production_go=False)
    save('Y_INCOMING_INTEGRITY.json', result)
    print(json.dumps(result), flush=True)
    return 0


def audit():
    import psycopg
    from psycopg.conninfo import conninfo_to_dict
    import cp6_x_independent_audit as prior
    import cp6_v2620y_runtime as runtime
    from cp6_v2620n_rollback_guards import function_catalog

    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    if params != dict(user='postgres', password='postgres', host='127.0.0.1', port='54322', dbname='postgres'):
        raise AssertionError('Y_AUDIT_EXACT_DISPOSABLE_ENDPOINT_REQUIRED')
    if os.environ.get('CP6_Y_INDEPENDENT_CONFIRM') != 'postgres':
        raise AssertionError('Y_AUDIT_DISPOSABLE_CONFIRMATION_REQUIRED')
    if git('diff', '--name-only', HEAD_Y, 'HEAD', '--', 'supabase/migrations', 'supabase/rollbacks'):
        raise AssertionError('Y_AUDIT_REQUIRES_UNCHANGED_Y_BUSINESS_SQL')
    if os.environ.get('GITHUB_SHA') != git('rev-parse', 'HEAD'):
        raise AssertionError('Y_AUDIT_EXACT_CHECKOUT')
    result = dict(format='CP6_Y_INDEPENDENT_AUDIT_V1', status='INCOMPLETE',
                  head=git('rev-parse', 'HEAD'), tree=git('rev-parse', 'HEAD^{tree}'),
                  parents=git('show', '-s', '--format=%P', 'HEAD').split(),
                  audited_business_head=HEAD_Y, audited_business_tree=TREE_Y,
                  run_id=os.environ.get('GITHUB_RUN_ID'), run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),
                  source_sql_unchanged=True, production_go=False,
                  real_authenticated_session=True, synthetic_jwt_context=True,
                  http_ui_reachability_proven=False, cases={})
    save(REPORT.name, result)

    def capture(cur, query, args=()):
        cur.execute('savepoint y_audit_call')
        try:
            cur.execute(query, args)
            value = cur.fetchall() if cur.description else []
            state = prior.one(cur, 'select to_jsonb(a) from erp.accounting_period_control a where singleton_id=1')
            return dict(ok=True, value=value, period_state=state)
        except psycopg.Error as exc:
            return dict(ok=False, sqlstate=exc.sqlstate, error=str(exc))
        finally:
            cur.execute('rollback to savepoint y_audit_call;release savepoint y_audit_call')

    def close_case(cur, zone, offset):
        prior.owner(cur)
        prior.zone(cur, 'Asia/Jakarta')
        instant = prior.one(cur, 'select current_timestamp')
        today = instant.astimezone(ZoneInfo('Asia/Jakarta')).date()
        target = today + timedelta(days=offset)
        baseline = capture(cur, 'select erp.close_accounting_through(%s,%s)', (target, 'Y independent date boundary'))
        prior.zone(cur, zone)
        observed = capture(cur, 'select erp.close_accounting_through(%s,%s)', (target, 'Y independent date boundary'))
        expected_ok = target < today
        evidence = dict(zone=zone, target=str(target), jakarta_today=str(today),
                        expected_accept=expected_ok, jakarta_control=baseline, actual=observed,
                        caller_today=str(instant.astimezone(ZoneInfo(zone)).date()),
                        source='erp.close_accounting_through(date,text)',
                        classification='CONTROL', status='CONTROL_PASS')
        if baseline['ok'] != expected_ok:
            evidence.update(status='INCOMPLETE', classification='CLOSE_CONTROL_PRECONDITION_NOT_QUALIFIED')
        elif observed['ok'] != baseline['ok']:
            evidence.update(status='NEW_Y_BUG_REPRODUCED', severity='P2',
                            classification='PREMATURE_PERIOD_CLOSE' if observed['ok'] else 'LAWFUL_PRIOR_DAY_CLOSE_FALSE_REFUSAL')
        return evidence

    def cash_default(cur, cash, zone):
        prior.owner(cur)
        prior.zone(cur, 'Asia/Jakarta')
        instant = prior.one(cur, 'select current_timestamp')
        today = instant.astimezone(ZoneInfo('Asia/Jakarta')).date()
        physical = datetime.combine(today, time(0, 0), tzinfo=ZoneInfo('Asia/Jakarta'))
        balance = prior.opening(cur, 'CUSTOMER_RECEIVABLE')
        ident = uuid.uuid4()
        before = prior.scrap.reports(cur, (str(today - timedelta(days=1)), str(today)))
        cur.execute('insert into erp.opening_subledger_settlements'
                    '(id,balance_id,settlement_number,physical_at,amount,cash_account_id,status) '
                    "values(%s,%s,%s,%s,.03,%s,'DRAFT')",
                    (ident, balance, 'YAUD-' + str(ident), physical, cash))
        cur.execute('select erp.post_opening_subledger_settlement(%s)', (ident,))
        after = prior.scrap.reports(cur, tuple(before))
        for day in before:
            want = Decimal('.03') if day == str(today) else Decimal(0)
            got = Decimal(str(after[day]['financial_position']['cash'])) - Decimal(str(before[day]['financial_position']['cash']))
            if got != want or after[day]['data_confidence']['status'] != 'READY':
                raise AssertionError('Y_DEFAULT_CASH_FIXTURE_CASH_OR_REPORT_NOT_QUALIFIED')
        prior.zone(cur, zone)
        cur.execute('select * from erp.report_cash_balance(%s)', (today,))
        explicit = cur.fetchall()
        cur.execute('select * from erp.report_cash_balance()')
        default = cur.fetchall()
        caller_day = instant.astimezone(ZoneInfo(zone)).date()
        cur.execute('select * from erp.report_cash_balance(%s)', (caller_day,))
        caller_explicit = cur.fetchall()
        prior.admin(cur)
        cur.execute("select economic_date,transaction_date from erp.journal_entries "
                    "where source_type='OPENING_SUBLEDGER_SETTLEMENT' and source_id=%s", (ident,))
        journals = cur.fetchall()
        if journals != [(today, today)]:
            raise AssertionError('Y_DEFAULT_CASH_SOURCE_POSTING_NOT_QUALIFIED')
        mismatch = default != explicit
        qualified = mismatch and default == caller_explicit and explicit != caller_explicit
        if mismatch and not qualified:
            raise AssertionError('Y_DEFAULT_CASH_DIFFERENCE_NOT_ATTRIBUTABLE_TO_CALLER_DATE')
        return dict(status='NEW_Y_BUG_REPRODUCED' if qualified else 'CONTROL_PASS',
                    severity='P2' if qualified else None,
                    classification='DIRECT_CASH_DEFAULT_WRONG_BUSINESS_DAY' if qualified else 'CONTROL',
                    zone=zone, expected_as_of=str(today), caller_as_of=str(caller_day),
                    explicit_today=explicit, default_actual=default, explicit_caller_day=caller_explicit,
                    source_journals=journals, amount='0.03', settlement_id=str(ident),
                    owner_reports_before=before, owner_reports_after=after,
                    source_posting_correct=True, source='erp.report_cash_balance(date)')

    with psycopg.connect(**dict(params, user='supabase_admin'), autocommit=False) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='180s';set local lock_timeout='8s'")
        baseline = prior.boundary(cur)
        result['runtime_before'] = baseline
        result['engine'] = prior.one(cur, 'select version()')
        if len(runtime.verified_successor(cur)) != 6:
            raise AssertionError('Y_AUDIT_VERIFIED_RUNTIME_REQUIRED')
        catalog = function_catalog(cur)
        save('Y_FULL_FUNCTION_CATALOG.json', catalog)
        target_names = ('report_cash_balance', 'close_accounting_through', 'finish_production_order',
                        '_post_cutting_qty_correction', '_recalculate_material_cost_core',
                        '_cp3_r4_reverse_journal_internal', 'resolve_accounting_transaction_date',
                        'reverse_sales_payment', 'reverse_vendor_payment', 'reverse_opening_subledger_settlement')
        selected = [r for r in catalog if r[0].split('(')[0].split('.')[-1] in target_names]
        save('Y_TARGET_FUNCTIONS.json', selected)
        for row in selected:
            print('Y_AUDIT_TARGET_SOURCE ' + json.dumps(row, default=str), flush=True)
        usage = prior.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
        if not usage:
            cur.execute('grant usage on schema erp to authenticated')
        prior.actors.claims(cur, dict(sub=prior.base.OPERATOR_AUTH, role='authenticated'))
        cur.execute("select set_config('app.change_reason','Independent Y disposable audit',true)")
        prior.base.load_fixture_foundation(cur)
        cash = prior.one(cur, 'select id from erp.cash_accounts where is_active order by id limit 1')
        cases = [('CLOSE:' + z + ':' + str(d), lambda zone=z, offset=d: close_case(cur, zone, offset))
                 for z in ZONES for d in (-2, -1, 0, 1)]
        cases += [('CASH_DEFAULT:' + z, lambda zone=z: cash_default(cur, cash, zone)) for z in ZONES]
        result['expected_case_count'] = len(cases)
        for name, operation in cases:
            cur.execute('savepoint independent_y_case')
            before = prior.boundary(cur)
            try:
                evidence = operation()
            except Exception as exc:
                evidence = dict(status='INCOMPLETE', classification='FIXTURE_OR_ORACLE_ERROR',
                                error=str(exc), sqlstate=getattr(exc, 'sqlstate', None))
            finally:
                cur.execute('rollback to savepoint independent_y_case')
                prior.admin(cur)
                cur.execute('release savepoint independent_y_case')
            evidence['full_boundary_restored'] = prior.boundary(cur) == before
            result['cases'][name] = evidence
            save(REPORT.name, result)
            print('Y_AUDIT_CASE ' + json.dumps(dict(name=name, **evidence), default=str), flush=True)
            if not evidence['full_boundary_restored']:
                raise AssertionError('Y_AUDIT_CASE_RESIDUE:' + name)
        conn.rollback()
        result['runtime_after'] = prior.boundary(cur)
        result['entire_unseeded_runtime_restored'] = result['runtime_after'] == baseline
        result['schema_usage_restored'] = prior.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')") == usage
        conn.rollback()
    result['qualified_counterexamples'] = sum(c['status'] == 'NEW_Y_BUG_REPRODUCED' for c in result['cases'].values())
    result['controls_passed'] = sum(c['status'] == 'CONTROL_PASS' for c in result['cases'].values())
    result['incomplete_cases'] = sum(c['status'] == 'INCOMPLETE' for c in result['cases'].values())
    complete = (len(result['cases']) == result['expected_case_count'] and result['incomplete_cases'] == 0
                and result['entire_unseeded_runtime_restored'] and result['schema_usage_restored'])
    result['status'] = ('FAIL_NEW_COUNTEREXAMPLE' if result['qualified_counterexamples'] else 'PASS_BOUNDED_AUDIT') if complete else 'INCOMPLETE'
    for name in ('scripts/cp6_y_independent_audit.py', '.github/workflows/cp6-full-schema-validation.yml'):
        data = Path(name).read_bytes()
        result.setdefault('sources', {})[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    save(REPORT.name, result)
    print('Y_AUDIT_SUMMARY ' + json.dumps({k: v for k, v in result.items() if k not in (
        'cases', 'runtime_before', 'runtime_after')}, default=str), flush=True)
    return 0 if result['status'] == 'PASS_BOUNDED_AUDIT' else 1 if result['status'] == 'FAIL_NEW_COUNTEREXAMPLE' else 2


if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['--verify-incoming']:
            status = incoming()
        elif not sys.argv[1:]:
            status = audit()
        else:
            raise AssertionError('UNKNOWN_AUDIT_ARGUMENT')
    except Exception as exc:
        previous = json.loads(REPORT.read_text()) if REPORT.exists() else {}
        previous.update(status='INCOMPLETE', error=str(exc), production_go=False)
        save(REPORT.name, previous)
        print('Y_AUDIT_FATAL ' + json.dumps(dict(status='INCOMPLETE', error=str(exc))), flush=True)
        status = 2
    raise SystemExit(status)
