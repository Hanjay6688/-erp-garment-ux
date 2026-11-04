"""Prepare exact new observation types and metadata controls without ERP."""
from copy import deepcopy
from pathlib import Path
import argparse
import importlib.util
import json
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('global_automatic_current_source_routes', HERE / 'routes.py')
routes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routes)
base = routes.base
MONEY_INPUT = dict(bytes=453690, sha256='a6db2fb74b510c0edad3bbc57a0ee238e57492f6b1905a6e79a6243b8d2bd23a')


def prepare(money_input_path):
    raw = Path(money_input_path).read_bytes()
    base.require(base.pin(raw) == MONEY_INPUT, 'GLOBAL_AUTOMATIC_EXACT_RETAINED_MONEY_MODEL_INPUT_REQUIRED')
    money = json.loads(raw)
    helpers, proof = routes.derive()
    prior_helpers, _ = routes.prior.derive()
    base.require(money['helpers'] == prior_helpers and len(money['columns']) == 80
                 and sum(map(len, money['columns'].values())) == 813,
                 'GLOBAL_AUTOMATIC_REUSE_REQUIRES_EXACT_PARENT_HELPERS_AND_TYPES')
    profile, reference = routes.sources()
    columns = dict(money['columns'])
    for name in routes.TABLES:
        table = 'cp7_sku_conversion.' + name
        rows = [row for key, row in profile['groups']['columns'].items() if key.startswith(table + ':')]
        base.require(table not in columns and rows, 'GLOBAL_AUTOMATIC_NEW_EXACT_TABLE_COLUMNS_REQUIRED:' + table)
        columns[table] = sorted(rows, key=lambda row: row[1])
    base.require(len(columns) == 82 and sum(map(len, columns.values())) == 835,
                 'GLOBAL_AUTOMATIC_EXACT_COMBINED_EIGHTY_TWO_TABLE_TYPES_REQUIRED')
    from cp7_global_nonpo_envelope import admission, catalogue_profile
    gates = ('PARENT_HEAD', 'PARENT_TREE', 'PARENT_ROOT_RECEIPT', 'PARENT_RUN', 'PARENT_JOB',
             'PARENT_ROOT_CONTRACT', 'INPUT_PROFILE_PIN', 'RUNTIME_ENTRY')
    base.require(all(getattr(admission, name) is None for name in gates), 'GLOBAL_AUTOMATIC_ALL_EIGHT_GATES_MUST_REMAIN_CLOSED')
    expected, *_ = routes.prior.expected_authority()
    groups = set(catalogue_profile.queries()) - set(catalogue_profile.EXTRA)
    candidate = {group: {} for group in groups}
    candidate['functions'] = deepcopy(expected)
    _, _, authority = base.expected_authority()
    candidate['relations']['erp.v_current_hpp'] = authority['actual_source_profile']['view_relation']
    for group, rows in profile['groups'].items():
        candidate[group].update(deepcopy(rows))
    candidate['functions'].update(deepcopy(profile['replacement_functions']))
    routes.current_reference(candidate)
    controls = []

    def refused(label, changed):
        try:
            routes.check_profile(changed, profile)
        except ValueError as error:
            controls.append(dict(label=label, result='REFUSED_AS_REQUIRED', error=str(error)))
        else:
            raise ValueError('GLOBAL_AUTOMATIC_METADATA_CONTROL_DID_NOT_REFUSE:' + label)

    for signature, row in (profile['groups']['functions'] | profile['replacement_functions']).items():
        for index in range(19):
            changed = dict(candidate, functions=dict(candidate['functions']))
            changed['functions'][signature] = list(row)
            changed['functions'][signature][index] = dict(unreviewed=index)
            refused(signature + ': attribute ' + str(index), changed)
    for group, rows in profile['groups'].items():
        if group == 'functions':
            continue
        for name in rows:
            changed = dict(candidate)
            changed[group] = dict(candidate[group])
            changed[group].pop(name)
            refused(group + ': missing ' + name, changed)
    additions = (HERE / 'automatic_edges.sql').read_text() + '\n'.join(route['after'][len(route['before']):]
        for route in proof['exact_routes'] if route['helper'] == 'capture')
    code = re.sub(r"'(?:[^']|'')*'", 'STRING_LITERAL', additions)
    code = re.sub(r'/\*[\s\S]*?\*/|--[^\n]*', '', code)
    base.require(not re.search(r'(?i)\b(?:insert\s+into|delete\s+from|update\s+[a-z]|lock\s+table|for\s+(?:update|share))\b|\b(?:nextval|gen_random_uuid|pg_advisory\w*|set_config)\s*\(', code),
                 'GLOBAL_AUTOMATIC_OBSERVATION_ADDITIONS_MUST_BE_READ_ONLY')
    report = dict(status='GLOBAL_AUTOMATIC_SOURCE_AND_FULL_METADATA_CONTROLS_PASS_NOT_RUNTIME',
                  source=reference, retained_money_input=MONEY_INPUT, derived_helpers=proof['derived_helpers'],
                  negative_controls=controls, exact_current_functions=19, checked_function_attributes=361,
                  typed_tables=len(columns), typed_columns=sum(map(len, columns.values())),
                  new_full_rowsets=2, new_identity_edges=8, all_eight_Global_gates_unset=True,
                  complete_actual_combined_input_profile=False, actual_ERP_cases=0, runtime_admission=False,
                  production_go=False, independent_acceptance=False)
    inputs = dict(classification='MODELED_AUTOMATIC_GLOBAL_OBSERVATION_NOT_ERP', helpers=helpers,
                  parent_helpers=prior_helpers, proof=proof, columns=columns, automatic_tables=routes.TABLES,
                  automatic_columns={name: columns['cp7_sku_conversion.' + name] for name in routes.TABLES},
                  modeled_callbacks=money['modeled_callbacks'], actual_ERP_cases=0,
                  constraints_owners_RLS_Native_callbacks_and_business_transactions_are_not_tested=True)
    return report, inputs


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--money-input', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--model-input', required=True)
    args = parser.parse_args()
    report, inputs = prepare(args.money_input)
    Path(args.report).write_text(json.dumps(report, indent=2) + '\n')
    Path(args.model_input).write_text(json.dumps(inputs, sort_keys=True) + '\n')
    print(json.dumps({key: report[key] for key in ('status', 'typed_tables', 'typed_columns', 'checked_function_attributes', 'actual_ERP_cases')}))
