"""Exercise the actual F05 group selector before a disposable database is built."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'scripts/cp7_f05_analysis_probe.py'
tree = ast.parse(source.read_text())
selector = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'bounded_group_names')
run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
assignment = next(n for n in run.body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'bounded_groups' for t in n.targets))
env = {}
exec(compile(ast.Module(body=[selector], type_ignores=[]), str(source), 'exec'), env)
route = compile(ast.Expression(body=assignment.value), str(source), 'eval')
decl = json.loads((ROOT / 'docs/cp7/d17-14/ow11/MODEL_SCOPED_EVALUATION_TRANSPORT_CONTRACT.json').read_text())
budget = decl['required_case_counts']
assert budget == {'native': 1, 'races': 4, 'http': 2}
flags = {a.arg: ast.literal_eval(d) for a, d in zip(run.args.args, run.args.defaults)}
flags.update(ow13c_bounded_stage=True, ow11_model_history_runtime=True,
             ow11_model_scoped_evaluation=True, ow11_model_scoped_transport=True)


def select(required=budget, **changes):
    return eval(route, env, dict(flags, case_provider=SimpleNamespace(REQUIRED=required), **changes))


assert select() == ('native', 'races', 'http')
denied = 0
for required, changes in [
    ({'native': 1, 'races': 3, 'http': 2}, {}),
    ({'native': 1, 'races': 4, 'http': 1}, {}),
    ({'native': 1, 'races': 4, 'http': 2, 'browser': 1}, {}),
    (budget, {'ow11_model_scoped_transport': False}),
    (budget, {'ow11_model_history_transport': True}),
    (budget, {'ow11_model_target_transport': True}),
    (budget, {'ow11_model_target_transport_part': 'A'}),
]:
    try:
        select(required, **changes)
    except ValueError:
        denied += 1
    else:
        raise AssertionError(('UNEXPECTED_ROUTING_ADMISSION', required, changes))
assert denied == 7
# Existing history7 and retained Native6 still retain their own selector.
assert select(budget, ow11_model_scoped_transport=False, ow11_model_history_transport=True) == ('native', 'races', 'http')
assert select({'native': 6}, ow11_model_scoped_transport=False) == ('native',)
print(json.dumps({'status': 'PASS', 'actual_run_selector': True, 'negative_controls': denied,
                  'unchanged_history7_and_native6': True, 'actual_Auth_HTTP_credit': False}))
