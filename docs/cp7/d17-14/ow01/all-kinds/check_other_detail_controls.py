"""SYNTHETIC_ORACLE_CONTROL_SOURCE_ONLY_NOT_NATIVE.

Retain the nine isolated assertion controls used in independent review.
Only _other_detail and _assert_alerts are extracted from the pinned proposal;
database, RPC, fixture, transport and provider operations are never executed.
The stub objects below are synthetic assertion inputs, not Native evidence.
"""
import argparse
import ast
import copy
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace


SCOPE = 'SYNTHETIC_ORACLE_CONTROL_SOURCE_ONLY_NOT_NATIVE'
PINNED_MODULE_SHA256 = '29b45d3ca5c4dba23ba0a931e26bcdde1ce6964467eee5e921df941bbe7fd945'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module', type=Path,
                        default=Path(__file__).with_name('cp7_wa_all_kinds_transport_cases.py'))
    parser.add_argument('--result', type=Path,
                        default=Path(__file__).with_name('OTHER_DETAIL_CONTROLS.json'))
    args = parser.parse_args()
    p = args.module.resolve()
    module_sha = hashlib.sha256(p.read_bytes()).hexdigest()
    assert module_sha == PINNED_MODULE_SHA256, ('PINNED_MODULE_CHANGED', module_sha)
    t = ast.parse(p.read_text())
    ns = {
        'D': Decimal,
        'OTHER': frozenset(('OPENING_AR', 'OPENING_AP', 'PAYROLL_AP', 'ACCESSORY_AP',
                            'LAUNDRY_AP', 'LAUNDRY_RECEIPT', 'LAUNDRY_OPENING_UNINVOICED')),
        'ANALYSIS': frozenset(('PRODUCTION_GAP', 'FABRIC_NEED')),
    }
    nodes = [n for n in t.body if isinstance(n, ast.FunctionDef)
             and n.name in ('_other_detail', '_assert_alerts')]
    assert {n.name for n in nodes} == {'_other_detail', '_assert_alerts'}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(p), 'exec'), ns)

    source_id = '00000000-0000-0000-0000-000000000001'
    subject = 'AP_DUE:PAYROLL_AP:' + source_id
    src = {
        'domain': 'PAYROLL_AP', 'source_id': source_id, 'label': 'E05-target',
        'state': 'DATA_REVIEW', 'reason': 'MISSING_RECORDED_DUE_DATE',
        'economic_state': 'OPEN', 'source_hash': 'a' * 64, 'as_of': '2026-10-20',
        'financial_source': {
            'remaining': {'state': 'KNOWN', 'value': '400'}, 'recorded_due_date': None,
        },
    }

    def invoke(source, patch=None):
        d = ns['_other_detail'](source)
        d.update(patch or {})
        a = {
            'id': '00000000-0000-0000-0000-000000000002', 'episode': 1,
            'title': 'Perlu diperiksa: E05-target', 'detail': d, 'party_names': [],
        }
        wa = SimpleNamespace(
            alerts=lambda cur, kind: {subject: a},
            rpc=lambda cur, *rpc_args: {'rows': [dict(
                a, kind=source['domain'], subject_key=subject, state='OPEN')]},
        )
        x = {
            'kind': source['domain'], 'owner': 'actor', 'subjects': [subject],
            'source_state': 'DATA_REVIEW',
            'amount': '400' if source['financial_source']['remaining']['state'] == 'KNOWN' else None,
        }
        return ns['_assert_alerts'](None, wa, x, {subject: source})

    checks = []
    invoke(src)
    checks.append({'case': 'VALID_KNOWN', 'expected': 'ACCEPT', 'observed': 'ACCEPT', 'status': 'PASS'})
    for patch in (
        {'reason': 'SOURCE_REVIEW'}, {'economic_state': 'SETTLED'},
        {'remaining': '399'}, {'due_date': '2026-10-19'},
        {'label': 'another document'}, {'source_hash': 'b' * 64}, {'as_of': '2026-10-19'},
    ):
        try:
            invoke(src, patch)
        except AssertionError:
            checks.append({'case': 'MALFORMED_' + next(iter(patch)).upper(),
                           'expected': 'REJECT', 'observed': 'REJECT', 'status': 'PASS'})
        else:
            raise AssertionError(('MALFORMED_PROJECTION_ACCEPTED', patch))

    unknown = copy.deepcopy(src)
    unknown['financial_source']['remaining'] = {'state': 'UNKNOWN'}
    unknown['domain'] = 'ACCESSORY_AP'
    unknown['reason'] = 'ALLOCATION_NOT_SETTLEMENT'
    unknown['economic_state'] = 'UNKNOWN'
    invoke(unknown)
    checks.append({'case': 'VALID_UNKNOWN_WITHOUT_VALUE_KEY', 'expected': 'ACCEPT',
                   'observed': 'ACCEPT', 'status': 'PASS'})
    assert len(checks) == 9
    result = {
        'scope': SCOPE, 'status': 'PASS', 'checks_count': len(checks), 'checks': checks,
        'module': str(p), 'module_sha256': module_sha,
        'control_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'database_executed': False, 'Native_executed': False, 'provider_executed': False,
    }
    args.result.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
