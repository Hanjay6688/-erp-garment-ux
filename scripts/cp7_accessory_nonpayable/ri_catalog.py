"""Exact FK edges and the one declared Native policy-use trigger."""
SCHEMA = 'cp7_accessory_nonpayable'
EDGES = (
    ('category_versions_v1', 'source_event_id', 'erp.bc_policy_setting_events_v1'),
    ('good_bases_v1', 'snapshot_id', 'erp.fg_accessory_cost_snapshots'),
    ('good_bases_v1', 'lot_id', 'erp.fg_lots'),
    ('good_bases_v1', 'contractor_id', 'erp.contractors'),
    ('good_bases_v1', 'category_policy_id', SCHEMA + '.category_versions_v1'),
    ('good_bases_v1', 'special_policy_id', 'erp.contractor_hpp_policy_versions'),
)
SPECIAL_TRIGGER = 'erp.contractor_hpp_policy_versions:nonpayable_special_used_guard_v1'


def expected_constraints():
    result = {}
    for table, column, parent in EDGES:
        child = SCHEMA + '.' + table
        constraint = table + '_' + column + '_fkey'
        result[child + ':' + constraint] = ['f', False, False, True, True, 0, True, None,
            parent + '_pkey', child, 'FOREIGN KEY (' + column + ') REFERENCES ' + parent + '(id)']
    return result


def expected_external_triggers(constraints):
    for key, value in expected_constraints().items():
        if constraints.get(key) != value:
            raise ValueError('NONPAYABLE_EXACT_FOREIGN_KEY_EDGE_REQUIRED:' + key)
    result = {}
    for table, column, parent in EDGES:
        if parent.startswith(SCHEMA + '.'):
            continue
        child = SCHEMA + '.' + table
        constraint = table + '_' + column + '_fkey'
        for function, kind in (('"RI_FKey_noaction_del"()', 9), ('"RI_FKey_noaction_upd"()', 17)):
            key = parent + ':' + child + ':' + constraint + ':' + function + ':' + str(kind)
            result[key] = [True, 'O', kind, 0, '', [], False, False, function,
                None, None, None, constraint, child, None, child]
    definition = ('CREATE TRIGGER nonpayable_special_used_guard_v1 BEFORE INSERT OR DELETE OR UPDATE '
        'ON erp.contractor_hpp_policy_versions FOR EACH ROW EXECUTE FUNCTION '
        + SCHEMA + '.guard_special_change_v1()')
    result[SPECIAL_TRIGGER] = [False, 'O', 31, 0, '', [], False, False,
        SCHEMA + '.guard_special_change_v1()', definition, None, None, None, None, None, None]
    return result
