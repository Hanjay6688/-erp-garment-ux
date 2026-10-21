"""Recheck preserved final-gate counterexamples; synthetic files, zero DB calls."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / 'scripts/ow04-qualification/qualification_gate.py'
NODE = next(n for n in ast.parse(SOURCE.read_text()).body
            if isinstance(n, ast.FunctionDef) and n.name == 'require')
CODE = compile(ast.Module(body=[NODE], type_ignores=[]), str(SOURCE), 'exec')
GATES = ('installed', 'primary_unchanged', 'backup_restore_drill',
         'security_advisors', 'writer_runtime')


def exercise(mutation):
    with tempfile.TemporaryDirectory(prefix='SYNTHETIC-ow04-final-gate-') as folder:
        base = Path(folder)
        expected = base / 'scripts/ow04-qualification'
        proof = base / 'proof/t3'
        old_package = proof.parent / 'ow04-http-completed'
        for directory in (expected, proof, old_package):
            directory.mkdir(parents=True, exist_ok=True)
        candidate = 'a' * 40
        binding = dict(status='PASS', native_case_count=58, candidate='b' * 40,
                       core_directory_tree='c' * 40, native_probe_blob='d' * 40)
        if mutation == 'binding_incomplete':
            binding['status'] = 'INCOMPLETE'
        if mutation == 'binding_unsupported32':
            binding['native_case_count'] = 32
        binding_bytes = (json.dumps(binding) + '\n').encode()
        (expected / 'QUALIFIED_CORE.json').write_bytes(binding_bytes)
        for label, filename, group, declaration, count in (
            ('HTTP', 'CP7_OW04_HTTP.json', 'http', 'EXPECTED.json', 8),
            ('RACES', 'CP7_OW04_RACES.json', 'races', 'RACE_EXPECTED.json', 6),
        ):
            raw = (SOURCE.parent / declaration).read_bytes()
            (expected / declaration).write_bytes(raw)
            ids = [r['id'] for r in json.loads(raw)['cases']]
            reused = dict(**copy.deepcopy(binding),
                          binding_sha256=hashlib.sha256(binding_bytes).hexdigest())
            report = dict(candidate_commit=candidate,
                          core_directory_tree=binding['core_directory_tree'],
                          native_probe_blob=binding['native_probe_blob'],
                          status='PASS', expected_case_count=count,
                          observed_case_count=count, cp6_restored=True,
                          advisor_gate=True, reused_native_binding=reused,
                          predeclared_case_sha256=hashlib.sha256(raw).hexdigest())
            report[group] = dict(status='PASS', counts={'PASS': count},
                                 database_remaining=0, auth_counts={'restored': True},
                                 cleanup_failures=[])
            report[group]['cases' if label == 'HTTP' else 'races'] = {
                ident: {'status': 'PASS'} for ident in ids}
            if mutation == 'reports_reused44_current_binding58':
                report['reused_native_binding']['native_case_count'] = 44
            if mutation == 'report_declaration_hash_wrong':
                report['predeclared_case_sha256'] = '0' * 64
            (proof / filename).write_text(json.dumps(report))
            package = dict(mode='install', status='ALL_STAGES_INSTALLED',
                           gate={key: True for key in GATES})
            package_path = (old_package if label == 'HTTP' else proof)
            (package_path / 'T3_PACKAGE_INSTALL.json').write_text(json.dumps(package))
        namespace = dict(Path=Path, json=json, hashlib=hashlib,
                         __file__=str(expected / 'qualification_gate.py'))
        exec(CODE, namespace)
        try:
            result = namespace['require'](proof, candidate,
                                           {'HTTP': 'success', 'RACES': 'success'})
            return dict(id=mutation, accepted=True, answer=result)
        except Exception as error:
            return dict(id=mutation, accepted=False, error=str(error))


if __name__ == '__main__':
    rows = [exercise(name) for name in (
        'valid', 'binding_incomplete', 'binding_unsupported32',
        'reports_reused44_current_binding58', 'report_declaration_hash_wrong')]
    assert rows[0]['accepted'] is True and all(row['accepted'] is False for row in rows[1:]), rows
    print(json.dumps(dict(classification='SYNTHETIC_ACTUAL_FUNCTION_NOT_RUNTIME',
                          status='PASS', gate_source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                          database_calls=0, rows=rows), indent=2))
