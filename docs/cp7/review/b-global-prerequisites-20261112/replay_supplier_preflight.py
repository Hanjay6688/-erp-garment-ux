"""Replay existing preflight code with the retained SQL protocol model, no DB.

Run against exact E4EA first, then against the proposed adapter. This proves
preflight behavior only, not PostgreSQL, actors, ledger effects or Global.
"""
import argparse
import ast
from copy import deepcopy
from datetime import date, datetime
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

NS = 'scripts/current-sku-automatic-composite-preparation'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def run(source_root, retained_root):
    current = load('b_supplier_preflight_subject', source_root / NS / 'native_preflight.py')
    retained = load('b_supplier_retained', retained_root / 'native_preflight.py')
    model = load('b_retained_model', retained_root / 'test_native_preflight.py')
    money_gate = load('b_money_gate', retained_root / 'money_gate_support.py')
    permission_keys = dict(retained.PERMISSIONS, **current.ACTOR_PERMISSIONS)

    class Cursor(model.CursorModel):
        def __init__(self, rows):
            super().__init__()
            self.now = datetime(2026, 11, 12, 10, tzinfo=ZoneInfo('Asia/Jakarta'))
            self.accounts['5100'] = [(True, True, 'EXPENSE')]
            self.functions.update(current.FUNCTIONS)
            self.database_roles.update({k: ('authenticated', 'authenticated') for k in current.ACTOR_FUNCTIONS})
            self.mappings['AP_SUPPLIER'] = rows
            self.fail_supplier_read = False

        def execute(self, query, params=()):
            normalized = ' '.join(query.split())
            if normalized == 'select public.erp_get_my_access_v1()':
                self.seen.append((self.actor, normalized, params))
                if self.actor == self.fail_actor:
                    self.aborted = True
                    raise model.ModeledSQLFailure('explicit modeled public access refusal')
                self.rows = [(dict(allowed=True, profile=dict(role_code='OWNER', is_active=True),
                    permissions=[k for k in permission_keys[self.actor] if (self.actor, k) not in self.permissions]),)]
                return self
            if 'from erp.accounting_account_mappings m' in normalized and params == ('AP_SUPPLIER',) and self.fail_supplier_read:
                raise model.ModeledSQLFailure('explicit modeled account read failure')
            return super().execute(query, params)

    def prerequisites(rows, *, permission_denied=False, actor_error=False, read_error=False, changed_census=False):
        cur = Cursor(rows)
        if permission_denied:
            cur.permissions.add(('accessory_operator', 'warehouse.accessory.view'))
        if actor_error:
            cur.fail_actor = 'conversion_and_owner_native'
        cur.fail_supplier_read = read_error
        business, selected, captures = model.business(cur, changed_census=changed_census)

        def actor(name):
            def choose(cursor, *_):
                assert cursor is cur
                cursor.actor = name
            return choose

        modules = SimpleNamespace(
            bd=SimpleNamespace(chain=SimpleNamespace(production=SimpleNamespace(owner=actor('upstream_completion_owner')))),
            invoice=SimpleNamespace(auth=SimpleNamespace(actor=actor('supplier_invoice_owner'))))
        # Administrative bindings are explicit doubles; no business result is invented.
        native = SimpleNamespace(context=lambda _: (None, modules),
            source_contract=lambda *_: dict(status='NATIVE_AUTOMATIC_CALLER_APIS_BOUND_NOT_EXECUTED', calls=6,
                original_AFUI_physical_constructor=True, actual_ERP_cases=0))
        invoices = SimpleNamespace(source_contract=lambda _: dict(original_invoice_helper_shapes=4, actual_ERP_cases=0))
        product = SimpleNamespace(sources=lambda: dict(classification='EXPLICIT_PROTOCOL_REPLAY_NOT_ERP'))
        proof = current.check(cur, date(2026, 11, 12), business, retained, product, native, invoices)
        assert cur.actor == 'admin' and not cur.savepoints and not cur.aborted
        assert selected == list(retained.ACTOR_FUNCTIONS)
        assert len(captures) == 4
        writes = [q for _, q, _ in cur.seen if not q.startswith(('select ', 'savepoint ', 'rollback to savepoint ', 'release savepoint '))]
        assert writes == [], writes
        return proof, cur

    gate_tree = ast.parse((source_root / NS / 'final_gate.py').read_bytes())
    gate_node = next(n for n in gate_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'validate_preflight')
    env = dict(money_gate=money_gate, prerequisites=current)
    exec(compile(ast.Module(body=[gate_node], type_ignores=[]), 'exact_validate_preflight_function', 'exec'), env)

    class Protocol:
        @staticmethod
        def exact(a, b, code):
            if a != b:
                raise ValueError(code)

        @classmethod
        def fields(cls, a, b, code):
            for key, value in b.items():
                cls.exact(a.get(key), value, code + ':' + key)

    def final_gate(proof):
        value = json.loads(json.dumps(proof, default=str))
        env['validate_preflight'](Protocol, dict(native_prerequisites=deepcopy(value)), value)

    cases = []
    for name, rows in (
        ('missing', []), ('inactive', [(False, True)]),
        ('nonpostable', [(True, False)]), ('dangling', [(None, None)]),
        ('duplicate', [(True, True), (True, True)]), ('valid', [(True, True)]),
    ):
        proof, cur = prerequisites(rows)
        expected = 'PASS' if name == 'valid' else 'REFUSED'
        checked = any(params == ('AP_SUPPLIER',) and 'from erp.accounting_account_mappings m' in sql for _, sql, params in cur.seen)
        cases.append(dict(id=name, expected=expected, actual=proof['status'], errors=proof['errors'],
                          mapping_read=checked, read_only_protocol=True, all_five_actor_checks_preserved=True,
                          status='PASS' if proof['status'] == expected else 'FAIL'))
        if name == 'valid':
            valid = proof
            final_gate(proof)

    # Preserve existing authority, failed-session recovery and all-row census refusals.
    for name, kwargs in [('permission', dict(permission_denied=True)), ('actor_error', dict(actor_error=True)),
                         ('census_change', dict(changed_census=True))]:
        proof, _ = prerequisites([(True, True)], **kwargs)
        cases.append(dict(id=name, expected='REFUSED', actual=proof['status'], errors=proof['errors'],
                          status='PASS' if proof['status'] == 'REFUSED' else 'FAIL'))

    try:
        proof, _ = prerequisites([(True, True)], read_error=True)
    except model.ModeledSQLFailure:
        actual = 'PROPAGATED'
    else:
        actual = proof['status']
    cases.append(dict(id='unexpected_account_read_error', expected='PROPAGATED', actual=actual,
                      status='PASS' if actual == 'PROPAGATED' else 'FAIL'))

    for name, mutation in (
        ('omitted', lambda p: p.pop('supplier_account_mappings', None)),
        ('empty', lambda p: p.update(supplier_account_mappings={})),
        ('false', lambda p: p.update(supplier_account_mappings={'AP_SUPPLIER': [[False, True]]})),
        ('extra', lambda p: p.update(supplier_account_mappings={'AP_SUPPLIER': [[True, True]], 'UNREVIEWED': [[True, True]]})),
    ):
        changed = deepcopy(valid)
        mutation(changed)
        try:
            final_gate(changed)
        except (KeyError, ValueError):
            actual = 'REFUSED'
        else:
            actual = 'ACCEPTED'
        cases.append(dict(id='final_gate_' + name, expected='REFUSED', actual=actual,
                          status='PASS' if actual == 'REFUSED' else 'FAIL'))

    return dict(classification='EXISTING_PYTHON_PREFLIGHT_SQL_PROTOCOL_REPLAY_NOT_DATABASE',
        status='PASS' if all(c['status'] == 'PASS' for c in cases) else 'FAIL', cases=cases,
        source={name: pin(source_root / NS / name) for name in ('native_preflight.py', 'final_gate.py')},
        retained={name: pin(retained_root / name) for name in ('native_preflight.py', 'test_native_preflight.py', 'money_gate_support.py')},
        actual_SQL_executed=0, actual_ERP_cases=0, actual_Auth_HTTP_cases=0,
        database_changes=0, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_root', type=Path)
    parser.add_argument('retained_root', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = run(args.source_root, args.retained_root)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(status=result['status'], cases=len(result['cases']),
        failed=[c['id'] for c in result['cases'] if c['status'] == 'FAIL'], actual_ERP_cases=0)))
    raise SystemExit(int(result['status'] != 'PASS'))
