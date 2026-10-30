"""Offline source/permission/read-only declaration checks; never Native PASS."""
import ast
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sql_functions(source):
    return re.findall(r'create function\s+(.+?)returns\s+[^\n]+\n(language\s+\w+[^$]+)\$\$(.*?)\$\$;', source, re.I | re.S)


def assert_read_only(source):
    functions = sql_functions(source)
    assert len(functions) == 5, ('FUNCTION_COUNT', len(functions))
    for signature, options, body in functions:
        no_comments = re.sub(r'--[^\n]*', '', body)
        assert not re.search(r'\b(insert\s+into|update\s+[\w."]+\s+set|delete\s+from|merge\s+into|truncate|nextval|setval|execute\s+|for\s+(update|share)|pg_advisory|ensure_\w+\s*\(|commit_accessory|post_\w+\s*\(|recalculate_\w+\s*\()\b', no_comments, re.I), signature
        assert "search_path=''" in options
    assert 'create or replace' not in source.lower()
    assert not re.search(r'create\s+(table|trigger|policy)|grant\s+.+\s+on\s+(erp\.|schema erp)', source, re.I)
    assert "l.lot_origin='PRODUCTION'" in source
    assert "h.status='POSTED'" in source
    assert source.count("at time zone 'Asia/Jakarta'") == 4
    assert "c.updated_at<=sn.snapshotted_at" not in source
    assert "a.action='INSERT'and a.new_data->>'base_uom_code'=c.base_uom_code" in source
    assert "a.old_data->>'base_uom_code'is distinct from a.new_data->>'base_uom_code'" in source
    assert "sn.total_reimbursement=0 or" in source
    assert "case when ro.id is not null then d.reimbursement_contractor_id else po.contractor_id end" in source
    assert "coalesce(d.reimbursement_contractor_id" not in source
    assert "snapshot_count=0 and commitment_id is not null" in source
    assert "decision_state='NONE'" in source
    assert source.count('cp7_accessory_standard_report.access_now()') == 4  # declaration, two calls, ALTER owner
    return len(functions)


def check():
    pins = json.loads((HERE/'SOURCE.json').read_bytes())
    assert pins['contract'] == 'cp7.accessory-standard-report.stage.v1'
    assert pins['production_go'] is pins['independent_acceptance'] is False
    for path, digest in pins['files'].items():
        assert sha256((ROOT/path).read_bytes()).hexdigest() == digest, path
    policy = pins['policy']
    original = subprocess.run(['git', 'show', policy['commit']+':'+policy['path']], cwd=ROOT, capture_output=True, check=True, text=True).stdout
    section = '## '+policy['section']+original.split('## '+policy['section'], 1)[1]
    assert sha256(section.encode()).hexdigest() == policy['section_sha256'], 'OWNER_POLICY_CHANGED'
    for path in HERE.glob('*.py'):
        ast.parse(path.read_text(), filename=str(path))
    source = (HERE/'report.sql').read_text()
    functions = assert_read_only(source)
    # Each forbidden mutation is a negative scanner control, not runtime proof.
    negative_controls = 0
    for statement in ('insert into erp.audit_logs values(1);', 'update erp.fg_lots set cached_qty_pcs=0;',
                      "select nextval('erp.audit_logs_id_seq');", 'perform erp.ensure_fg_accessory_cost_snapshot(null);'):
        mutant = source.replace(" select to_char(p_at", ' '+statement+'\n select to_char(p_at', 1)
        try:
            assert_read_only(mutant)
        except AssertionError:
            negative_controls += 1
        else:
            raise AssertionError('MUTATION_CONTROL_NOT_REJECTED')
    tree = ast.parse((HERE/'cases.py').read_text())
    ids = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'IDS' for t in n.targets))
    assert list(ids) == pins['Native_case_ids'] and len(ids) == len(set(ids)) == 10
    # The catalog admission matcher is pure: adversarial before/after fixtures
    # do not import a product runtime or connect to any database.
    spec = importlib.util.spec_from_file_location('s05_offline_stage', HERE/'stage.py')
    stage = importlib.util.module_from_spec(spec); spec.loader.exec_module(stage)
    assert len(stage.function_sources()) == 5
    names = ('schemas','roles','functions')+tuple('unchanged_'+str(i) for i in range(19))
    before = {name: {} for name in names}
    after = {name: dict(rows) for name, rows in before.items()}
    after['schemas'][stage.SCHEMA] = ['reader schema']; after['roles'][stage.ROLE] = ['nonlogin']
    after['functions'] = {signature: ['new exact reader'] for signature in stage.FUNCTIONS}
    stage.transition(before, after)
    rejected = 0
    for group, key in (('functions', 'erp.post_journal()'), ('roles', 'authenticated'), ('schemas', 'erp'), ('unchanged_0', 'business')):
        bad = {name: dict(rows) for name, rows in after.items()}; bad[group][key] = ['UNDECLARED']
        try:
            stage.transition(before, bad)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError('CATALOG_CONTROL_NOT_REJECTED')
    return dict(status='PASS_OFFLINE_SOURCE_ONLY', files=len(pins['files']), read_functions=functions,
                mutation_controls=negative_controls, catalog_delta_controls=rejected, prepared_Native_cases=list(ids),
                Native_executions=0, database_calls=0, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
