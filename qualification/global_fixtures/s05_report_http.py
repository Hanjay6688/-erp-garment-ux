"""Compare ordinary authenticated S05 reads with the owning Native oracle."""

from hashlib import sha256
from types import SimpleNamespace
import json
import re


CASE = 'GLOBAL_AUTH_S05_ORDINARY_ACCESS'
REPORT = 'erp_cp7_get_accessory_standard_report_v1'
SIGNATURE = '(date,date,uuid,uuid,text,integer,integer)'
CONTRACT = 'cp7.accessory-standard-report.v1'
ACL_REFUSAL = 'permission denied for function ' + REPORT
ROLE_REFUSAL = 'CP7_ACCESSORY_REPORT_DENIED'
REPORT_SQL = 'scripts/cp7_accessory_standard_report/report.sql'
READER_IMAGES = 'scripts/current-global-first-snapshot-preparation/REVIEWED_READER_IMAGES.json'
PINS = {
    REPORT_SQL: '216f34d1225171543a743d272a2a9a15aeeda50658a32b53b0ea7ccc64b3702a',
    READER_IMAGES: 'ea51351de5f00b7e28107e177800edcbc34a4e7f68644d2b23c49d442b71ad19',
}


def need(value, reason):
    if not value:
        raise ValueError('GLOBAL_AUTH_S05_' + reason)


def check_sources(candidate, plan):
    files = {name: (candidate / name).read_bytes() for name in PINS}
    need(all(sha256(raw).hexdigest() == PINS[name] for name, raw in files.items()), 'EXACT_REPORT_SOURCES_REQUIRED')
    sql = files[REPORT_SQL].decode()
    public = 'function public.' + REPORT + SIGNATURE
    need(f'revoke all on {public}from public,anon,service_role,cp7_capture,postgres;' in sql
         and f'grant execute on {public}to authenticated;' in sql
         and "not in('OWNER','ADMIN')" in sql and plan.S05_REVIEW_RPC == REPORT and plan.HTTP_CASE_IDS[-1] == CASE,
         'EXACT_REPORT_AUTHORITY_REQUIRED')
    images = json.loads(files[READER_IMAGES])
    workspace = images['new_rows']['cp7_accessory_standard_report.workspace' + SIGNATURE][0]
    access = 'cp7_accessory_standard_report.access_now()'
    data = 'cp7_accessory_standard_report.workspace_data_v1('
    need(workspace.count(access) == 2 and workspace.index(access) < workspace.index(data) < workspace.rindex(access),
         'EXACT_ORDINARY_REPORT_AND_ACCESS_READS_REQUIRED')


def report_body(body):
    need(type(body) is dict and body.get('business_DML') is False and body.get('contract_version') == CONTRACT
         and type(body.get('captured_at')) is str
         and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z', body['captured_at']) is not None,
         'EXACT_READ_ONLY_REPORT_REQUIRED')
    return {key: value for key, value in body.items() if key != 'captured_at'}


def prepared_query(native):
    expected = report_body(native['reads']['selected_PO'])
    query, report = expected['query'], expected['report']
    need(query.keys() == {'period_start', 'period_end', 'contractor_id', 'po_id', 'q', 'offset', 'limit'}
         and query['period_start'] == query['period_end'] and query['offset'] == 0 and query['limit'] == 30
         and report['contractor_id'] == query['contractor_id'] == expected['selected_contractor']['id']
         and report['po_filter'] == query['po_id'] == expected['po_options'][0]['id']
         and report['status'] == 'KNOWN' and report['business_timezone'] == 'Asia/Jakarta'
         and len(report['rows']) == len(report['standard_sources']) == len(report['lot_sources']) == 1,
         'NATIVE_SELECTED_PO_ORACLE_REQUIRED')
    keys = ('period_start', 'period_end', 'contractor_id', 'po_id', 'q', 'offset', 'limit')
    rpc = ('p_start', 'p_end', 'p_contractor', 'p_po', 'p_query', 'p_offset', 'p_limit')
    return dict(zip(rpc, (query[key] for key in keys), strict=True)), expected


def bind(candidate, plan):
    check_sources(candidate, plan)

    def start(attempt, *, owner, admin, finance, native, observe, require_quiet, retain):
        """Read before the shared permission window, inside it, and after restoration."""
        need((owner.role, admin.role, finance.role) == ('OWNER', 'ADMIN', 'KEUANGAN'), 'EXACT_ACTOR_ROLES_REQUIRED')
        query, expected = prepared_query(native)
        measurements = {}

        def measured(label, operation, *, status, message=None):
            require_quiet()
            before = observe()
            require_quiet()
            response = operation(REPORT, dict(query))
            body = response.get('body') if type(response) is dict else None
            observed_status = response.get('status') if type(response) is dict else None
            code = body.get('code') if type(body) is dict else None
            record = dict(http_status=observed_status if type(observed_status) is int else None,
                          sqlstate=code if type(code) is str and re.fullmatch('[0-9A-Z]{5}', code) else None)
            measurements[label] = record
            require_quiet()
            record['same_native_state'] = observe() == before
            require_quiet()
            need(observed_status == status and record['same_native_state'], 'RESPONSE_OR_READ_ONLY_STATE_CHANGED:' + label)
            if message is None:
                need(report_body(body) == expected, 'NATIVE_AND_HTTP_REPORT_DIFFER:' + label)
                record['same_native_report'] = True
            else:
                need(type(body) is dict and set(body) <= {'code', 'message', 'hint', 'details'} and code == '42501'
                     and type(body.get('message')) is str
                     and (body['message'] == message or body['message'].startswith(message + ':')),
                     'EXACT_AUTHORITY_DENIAL_REQUIRED:' + label)
                record['denial'] = message
            return record

        def run(label, operation, *, status, message=None):
            try:
                return measured(label, operation, status=status, message=message)
            except Exception:
                retain(CASE + '_FIRST_FAILURE', dict(phase=label, measurements=measurements))
                raise

        access = {actor.role: plan.observe_access(attempt, actor) for actor in (owner, admin, finance)}
        for evidence in access.values():
            plan.require_permissions(evidence, plan.S05_PERMISSIONS)
        run('owner', owner.rpc, status=200)
        run('admin', admin.rpc, status=200)
        run('finance', finance.rpc, status=403, message=ROLE_REFUSAL)
        run('anon', attempt.anon_rpc, status=401, message=ACL_REFUSAL)
        run('service', attempt.service_rpc, status=403, message=ACL_REFUSAL)

        def during_revocation(actor, revoked_access):
            need(actor is admin and 'admin_revoked' not in measurements, 'ONE_SAME_ADMIN_PERMISSION_WINDOW_REQUIRED')
            plan.compare_access(access['ADMIN'], revoked_access, lost=(plan.REVOKED_PERMISSION,))
            return run('admin_revoked', admin.rpc, status=403, message=ROLE_REFUSAL)

        def finish():
            need('admin_revoked' in measurements and 'admin_restored' not in measurements,
                 'EXACT_REVOCATION_AND_RESTORATION_ORDER_REQUIRED')
            plan.compare_access(access['ADMIN'], plan.observe_access(attempt, admin))
            run('admin_restored', admin.rpc, status=200)
            return dict(status='PASS', access=access, observations=measurements,
                        original=retain(CASE, dict(case=CASE, query=query, native=expected, access=access,
                                                   observations=measurements)))

        return SimpleNamespace(during_revocation=during_revocation, finish=finish)

    return start
