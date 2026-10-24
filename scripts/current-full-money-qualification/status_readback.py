"""Native OW16 readback of every cutting group, with no guessed policy.

The public reader's checked_at is validated against two database clock reads
and retained separately. Every other returned field is compared exactly.
No source timestamp or status is hidden from the Original report.
"""
from copy import deepcopy
from datetime import datetime
import cp7_ow16_status_cases as status
from cp7_ow04_restore_bundle import _data, _catalog_rows


def read(cur):
    status.b.api.admin(cur)
    groups = [row[0] for row in cur.execute('select id from erp.cutting_groups order by id').fetchall()]
    assert groups, 'CURRENT_P21_STATUS_NO_CUTTING_GROUPS'
    data_before, catalog_before = _data(cur), _catalog_rows(cur)
    # Native fixture access only, restored before the full catalog comparison.
    granted = not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
    if granted:
        cur.execute('grant usage on schema erp to authenticated')
    rows = {}
    try:
        for group in groups:
            before = cur.execute('select clock_timestamp()').fetchone()[0]
            raw = status.read(cur, group)
            after = cur.execute('select clock_timestamp()').fetchone()[0]
            observed = datetime.fromisoformat(raw['checked_at'].replace('Z', '+00:00'))
            assert before <= observed <= after, ('CURRENT_P21_STATUS_OBSERVATION_TIME', before, raw['checked_at'], after)
            assert raw['contract_version'] == 'cp7.automatic-cutting-status.v1'
            assert raw['group']['id'] == str(group) and raw['business_write'] is False
            facts = deepcopy(raw)
            del facts['checked_at']
            rows[str(group)] = dict(raw=raw, facts=facts, clock_before=before, clock_after=after)
    finally:
        status.b.api.admin(cur)
        if granted:
            cur.execute('revoke usage on schema erp from authenticated')
    assert _data(cur) == data_before, 'CURRENT_P21_STATUS_READ_CHANGED_DATA_OR_SEQUENCE'
    assert _catalog_rows(cur) == catalog_before, 'CURRENT_P21_STATUS_READ_CHANGED_CATALOG'
    return dict(groups=rows, all_groups=len(groups), only_observation_field='checked_at',
                full_rows_sequences_catalog_unchanged=True, temporary_Native_usage_grant_restored=granted)


def compare(before, after):
    assert before['all_groups'] == after['all_groups'] and set(before['groups']) == set(after['groups'])
    for group in before['groups']:
        assert before['groups'][group]['facts'] == after['groups'][group]['facts'], (
            'CURRENT_P21_RESTORED_CUTTING_STATUS_CHANGED', group,
            before['groups'][group]['raw'], after['groups'][group]['raw'])
    return dict(all_groups=before['all_groups'], every_status_and_business_field_exact=True,
                only_checked_at_separately_validated=True, raw_observations_preserved=True,
                current_policy_only_no_policy_write=True)
