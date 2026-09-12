#!/usr/bin/env python3
"""Fixture orchestration regressions; database boundaries are mocked, not native proof."""
from __future__ import annotations

import json
import os
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import cp6_v2620h_maintenance_rollback_matrix as matrix
import cp6_v2620j_rollback_guards as jguards


REPORT = Path('cp6-proof/CP6_ROLLBACK_SETUP_UNIT.json')
GENERATIONS = tuple(matrix.TARGETS)
SOURCE_GENERATIONS = ('I', 'J', 'K', 'L', 'M', 'N', 'O', 'P')
PLANS = {
    (source, target): tuple(reversed(
        GENERATIONS[GENERATIONS.index(target):GENERATIONS.index(source) + 1]
    ))
    for source in SOURCE_GENERATIONS
    for target in GENERATIONS[:GENERATIONS.index(source) + 1]
}


def exercise_prepare(source: str, target: str, *, fault: str | None = None) -> None:
    conn, cur = MagicMock(), MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cur
    rows = [matrix.TARGETS[source][:2]] + [
        (int(generation <= source), generation <= source)
        for generation in matrix.TARGETS
    ]
    if fault == 'wrong_platform':
        rows[0] = ('99999999999999', 'unknown_successor')
    elif fault == 'missing_marker':
        rows[4] = (0, True)
    elif fault == 'missing_capsule':
        rows[4] = (1, False)
    elif fault == 'unexpected_j_capsule':
        rows[5] = (0, True)
    elif fault == 'missing_l_capsule':
        rows[1+tuple(matrix.TARGETS).index('L')] = (1, False)
    elif fault == 'missing_m_capsule':
        rows[1+tuple(matrix.TARGETS).index('M')] = (1, False)
    cur.fetchone.side_effect = rows
    capsule = [{} for _ in range(matrix.TARGETS[target][4])]
    with ExitStack() as stack:
        command = stack.enter_context(patch.object(matrix, 'command'))
        strip = stack.enter_context(patch.object(matrix, 'maintenance_strip'))
        stack.enter_context(patch.object(matrix.legacy, 'connect', return_value=conn))
        seed = stack.enter_context(patch.object(matrix.legacy, 'seed', return_value={'fixture': True}))
        stack.enter_context(patch.object(matrix.legacy, 'capture_capsule', return_value=capsule))
        verify = stack.enter_context(patch.object(matrix.legacy, 'verify_functions'))
        rejection = None
        try:
            observed = matrix.prepare(target, 'REPORT', Path('cp6-proof/unit-only'), source_generation=source)
        except AssertionError as exc:
            rejection = exc
        if fault is not None:
            if rejection is None:
                raise AssertionError('Invalid source generation was accepted')
            strip.assert_not_called()
            seed.assert_not_called()
            verify.assert_not_called()
            # Only the physical clone is allowed before source verification.
            assert command.call_count == 1
        else:
            if rejection is not None:
                raise rejection
            assert tuple(call.args[0] for call in strip.call_args_list) == PLANS[source, target]
            assert observed == ({'fixture': True}, capsule)
            assert command.call_count == 2
            seed.assert_called_once_with(cur, 'REPORT')
            verify.assert_called_once_with(capsule, True)


def invalid_request(source: str, target: str) -> None:
    with patch.object(matrix, 'command') as command, patch.object(matrix, 'maintenance_strip') as strip:
        try:
            matrix.prepare(target, 'REPORT', Path('cp6-proof/unit-only'), source_generation=source)
        except AssertionError:
            pass
        else:
            raise AssertionError('Unsupported fixture request was accepted')
        command.assert_not_called()
        strip.assert_not_called()


def structural_restore_summary() -> None:
    conn, cur = MagicMock(), MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchone.return_value = (True,)
    database_value = 'DATABASE_VALUE_MUST_NOT_BE_SERIALIZED'
    with patch.object(jguards.psycopg, 'connect', return_value=conn), patch.object(
        jguards.maintenance, '_function_snapshot', return_value=[database_value] * 3,
    ) as snapshot:
        observed = jguards.verify_exact_i_restore('unit-conninfo-never-connected')
    snapshot.assert_called_once_with(conn, jguards.maintenance.TRUSTED_FUNCTIONS['J'])
    assert observed == {
        'generation': 'I', 'restored_function_count': 3,
        'owner_acl_exact': True, 'metadata_schema_residue': 0,
    }
    assert database_value not in json.dumps(observed)


def structural_capsule_summary() -> None:
    conn, cur = MagicMock(), MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchone.return_value = (1,)
    database_value = 'DATABASE_VALUE_MUST_NOT_BE_SERIALIZED'
    with ExitStack() as stack:
        stack.enter_context(patch.object(jguards, 'CLONE_ROOT', MagicMock()))
        stack.enter_context(patch.object(matrix, 'prepare'))
        stack.enter_context(patch.object(jguards, 'coherent_capsule_fault', return_value=(database_value,) * 3))
        stack.enter_context(patch.object(jguards.psycopg, 'connect', return_value=conn))
        stack.enter_context(patch.object(matrix, 'read_json_if_present', return_value={
            'admission_closed': False, 'rollback_started': False,
        }))
        stack.enter_context(patch.object(jguards.maintenance, 'run_maintenance_rollback', side_effect=
            jguards.maintenance.MaintenanceRollbackError('TRUSTED_PREDECESSOR_PIN_MISMATCH')))
        stack.enter_context(patch.object(matrix, 'reopen_clone'))
        stack.enter_context(patch.object(matrix.legacy, 'drop_clone'))
        observed = jguards.verify_j_capsule_fault()
    assert set(observed) == {
        'target', 'status', 'coherent_checksum_changed', 'trusted_pin_rejected',
        'admission_closed', 'rollback_started', 'installed_generation_preserved',
    }
    assert observed['status'] == 'PASS' and observed['trusted_pin_rejected'] is True
    assert database_value not in json.dumps(observed)


def run() -> dict:
    cases = []
    for source, target in PLANS:
        exercise_prepare(source, target)
        cases.append({'case': f'{source}_SOURCE_FOR_{target}', 'status': 'PASS'})
    for source, target in (('I', 'J'), ('H', 'F'), ('N', 'O'), ('O', 'P'), ('J', 'K'), ('K', 'L'), ('L', 'M'), ('M', 'N')):
        invalid_request(source, target)
        cases.append({'case': f'REJECT_{source}_SOURCE_FOR_{target}', 'status': 'PASS'})
    for fault in ('wrong_platform', 'missing_marker', 'missing_capsule', 'unexpected_j_capsule'):
        exercise_prepare('I', 'F', fault=fault)
        cases.append({'case': fault, 'status': 'PASS'})
    exercise_prepare('L', 'F', fault='missing_l_capsule')
    cases.append({'case': 'MISSING_L_CAPSULE', 'status': 'PASS'})
    exercise_prepare('M', 'F', fault='missing_m_capsule')
    cases.append({'case': 'MISSING_M_CAPSULE', 'status': 'PASS'})
    structural_restore_summary()
    cases.append({'case': 'STRUCTURAL_RESTORE_SUMMARY', 'status': 'PASS'})
    structural_capsule_summary()
    cases.append({'case': 'STRUCTURAL_CAPSULE_SUMMARY', 'status': 'PASS'})

    # Reintroduce the actual #120 defect. This oracle must reject it even
    # when every mocked maintenance operation itself returns successfully.
    with patch.object(matrix, 'setup_rollback_plan', return_value=('J', 'I', 'H', 'G', 'F')):
        try:
            exercise_prepare('I', 'F')
        except AssertionError:
            pass
        else:
            raise AssertionError('Unconditional-J negative control unexpectedly passed')
    # Source verification may not silently accept a missing successor capsule.
    with patch.object(matrix, 'verify_setup_source'):
        try:
            exercise_prepare('I', 'F', fault='unexpected_j_capsule')
        except AssertionError:
            pass
        else:
            raise AssertionError('Permissive-source negative control unexpectedly passed')
    assert len(cases) == 76
    return {
        'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
        'classification': 'MOCKED_FIXTURE_ORCHESTRATION_NOT_NATIVE_DATABASE_PROOF',
        'status': 'PASS', 'expected_case_count': 76, 'completed_case_count': len(cases),
        'cases': cases,
        'unconditional_j_negative_control_rejected': True,
        'permissive_source_negative_control_rejected': True,
        'production_go': False,
    }


if __name__ == '__main__':
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    result = run()
    REPORT.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))
