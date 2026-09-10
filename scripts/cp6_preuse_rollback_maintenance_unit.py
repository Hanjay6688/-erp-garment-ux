#!/usr/bin/env python3
"""Pure endpoint-allowlist tests for the CP6 maintenance executor."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import cp6_preuse_rollback_maintenance as maintenance


REPORT = Path('cp6-proof/CP6_PREUSE_ROLLBACK_MAINTENANCE_UNIT.json')
TARGET = 'postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'
CONTROL = (
    'postgresql://cp6_maintenance_admission:maintenance-only@127.0.0.1:54322/template1'
)


def run() -> dict[str, Any]:
    result: dict[str, Any] = {
        'classification': 'PURE_MAINTENANCE_ENDPOINT_ALLOWLIST_UNIT',
        'production_go': False,
        'expected_case_count': 23,
        'cases': [],
    }

    def case(
        name: str,
        target: str = TARGET,
        control: str = CONTROL,
        *,
        confirmation: str = 'cp6_rollback',
        allow_postgres: bool = False,
        accepted: bool = False,
    ) -> None:
        old_confirm = os.environ.get('CP6_MAINTENANCE_CONFIRM_DATABASE')
        old_system = os.environ.get('CP6_MAINTENANCE_ALLOW_SYSTEM_DATABASE')
        os.environ['CP6_MAINTENANCE_CONFIRM_DATABASE'] = confirmation
        if allow_postgres:
            os.environ['CP6_MAINTENANCE_ALLOW_SYSTEM_DATABASE'] = 'postgres'
        else:
            os.environ.pop('CP6_MAINTENANCE_ALLOW_SYSTEM_DATABASE', None)
        try:
            observed = maintenance._validate_connections(target, control)
            if not accepted:
                raise AssertionError('endpoint unexpectedly accepted')
            result['cases'].append(
                {'case': name, 'status': 'PASS', 'accepted': True, 'observed': observed}
            )
        except Exception as exc:
            if accepted:
                raise
            result['cases'].append(
                {'case': name, 'status': 'PASS', 'accepted': False, 'rejection': str(exc)}
            )
        finally:
            if old_confirm is None:
                os.environ.pop('CP6_MAINTENANCE_CONFIRM_DATABASE', None)
            else:
                os.environ['CP6_MAINTENANCE_CONFIRM_DATABASE'] = old_confirm
            if old_system is None:
                os.environ.pop('CP6_MAINTENANCE_ALLOW_SYSTEM_DATABASE', None)
            else:
                os.environ['CP6_MAINTENANCE_ALLOW_SYSTEM_DATABASE'] = old_system

    case('exact_disposable_clone', accepted=True)
    case(
        'explicit_local_postgres',
        TARGET.replace('/cp6_rollback', '/postgres'),
        confirmation='postgres',
        allow_postgres=True,
        accepted=True,
    )
    case(
        'postgres_without_explicit_opt_in',
        TARGET.replace('/cp6_rollback', '/postgres'),
        confirmation='postgres',
    )
    case('external_target_host', TARGET.replace('127.0.0.1', 'db.example.invalid'))
    case('wrong_target_port', TARGET.replace('54322', '5432'))
    case('wrong_target_user', TARGET.replace('postgres:postgres', 'owner:postgres'))
    case('wrong_target_database', TARGET.replace('/cp6_rollback', '/uat'))
    case('missing_target_host', 'dbname=cp6_rollback user=postgres port=54322 password=postgres')
    case('non_loopback_target_hostaddr', TARGET + '?hostaddr=192.0.2.8')
    case('target_options_override', TARGET + '?options=-csearch_path%3Dpublic')
    case('target_service_override', TARGET + '?service=untrusted')
    case('target_application_name_override', TARGET + '?application_name=untrusted')
    case('target_without_password', TARGET.replace('postgres:postgres@', 'postgres@'))
    case('external_control_host', control=CONTROL.replace('127.0.0.1', 'db.example.invalid'))
    case('wrong_control_port', control=CONTROL.replace('54322', '5432'))
    case(
        'wrong_control_user',
        control=CONTROL.replace('cp6_maintenance_admission', 'postgres'),
    )
    case('wrong_control_database', control=CONTROL.replace('/template1', '/postgres'))
    case(
        'missing_control_host',
        control='dbname=template1 user=cp6_maintenance_admission port=54322 password=x',
    )
    case('non_loopback_control_hostaddr', control=CONTROL + '?hostaddr=192.0.2.8')
    case('control_options_override', control=CONTROL + '?options=-csearch_path%3Dpublic')
    case('control_service_override', control=CONTROL + '?service=untrusted')
    case(
        'control_without_password',
        control=CONTROL.replace(
            'cp6_maintenance_admission:maintenance-only@',
            'cp6_maintenance_admission@',
        ),
    )
    case('confirmation_mismatch', confirmation='postgres')

    result['completed_case_count'] = len(result['cases'])
    result['status'] = (
        'PASS'
        if result['completed_case_count'] == result['expected_case_count']
        and all(item['status'] == 'PASS' for item in result['cases'])
        else 'FAIL'
    )
    return result


def main() -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = run()
    except Exception as exc:
        result = {'status': 'FAIL', 'error': str(exc), 'production_go': False}
    REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps(result, sort_keys=True, default=str))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
