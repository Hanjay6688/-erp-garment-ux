"""First execution of previously unexecuted modes-module native factories on frozen CP7 FULL.

Only installation, output location and observation adapters are composed here.
Original fixtures, case operations, expectations and status vocabulary stay intact.
No business-case retry. BB/BC/BD readers are captured with their native adapters.
"""
from pathlib import Path
from contextlib import contextmanager
import hashlib, importlib, json, sys, traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import full_stack
import cp6_auditor_runner as native
from cp7_catalog_state import exact_public_catalog

TAG = sys.argv[1].lower()
assert TAG in ('bd-range',)
native.r1.OUT = full_stack.OUT

@contextmanager
def reader_capture(module):
    changes = []
    if TAG in ('bb','bc','bd'):
        directory = full_stack.OUT / ('WORKSPACE_' + TAG.upper())
        directory.mkdir(parents=True, exist_ok=True)
        module.OUT = full_stack.OUT
        module.WS['dir'] = directory
        pairs = [(module.api, 'read', module.recording_read)]
        if TAG == 'bc':
            pairs += [(module, 'ws', module.recording_ws),
                      (module, 'note_read', module.recording_note_read)]
        if TAG == 'bd':
            pairs += [(module, 'bd_ws', module.recording_bd_ws)]
        for obj, name, replacement in pairs:
            changes.append((obj, name, getattr(obj, name)))
            setattr(obj, name, replacement)
    try:
        yield
    finally:
        for obj, name, original in reversed(changes):
            setattr(obj, name, original)

def run():
    label = 'ASTRA_CP17_NATIVE_MODES_' + TAG.upper().replace('-','_')
    report = dict(label=label, status='INCOMPLETE', production_go=False,
                  evidence_origin='ASTRA_FIRST_EXECUTION_ON_CP7_FULL',
                  oracle_origin='INHERITED_UNCHANGED_FACTORY', retry=False)
    module = importlib.import_module('cp6_bd_revision_modes')
    source = Path(module.__file__)
    report['factory_source'] = str(source)
    report['factory_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    try:
        with full_stack.installed(report) as verify:
            with exact_public_catalog(native, retain_raw=True, retain_locations=True) as catalog:
                with reader_capture(module):
                    def factory(cur, today):
                        all_cases = module.cases(cur, today)
                        cases = [(key, op) for key, op in all_cases if key.startswith('RANGE:')]
                        assert len(cases) == 2, 'RANGE_FACTORY_BUDGET_CHANGED'
                        full_stack.save(label + '_PREEXECUTION_PLAN', dict(
                            case_ids=[key for key, _ in cases], business_day=str(today),
                            source_sha256=report['factory_sha256'], **full_stack.identity()))
                        return cases
                    report['group'] = native._strict_group_once(label + '_CASES', factory, verify)
                if TAG in ('bb','bc','bd'):
                    report['workspace_parse'] = module.workspace_parse('after')
                report['catalog_adapter'] = catalog
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    good = not report.get('error') and report.get('group', {}).get('status') == 'PASS'
    if TAG in ('bb','bc','bd'):
        good = good and report.get('workspace_parse', {}).get('status') == 'PASS'
    report['status'] = 'PASS' if good and report.get('cp6_restored') and report.get('advisor_gate') else 'INCOMPLETE'
    full_stack.save(label, report)
    print(json.dumps({k:report.get(k) for k in ('label','status','error','cp6_restored','advisor_gate')}, default=str), flush=True)
    return dict(status=report['status'], production_go=False)

if __name__ == '__main__':
    full_stack.package._writer_runtime = lambda browser_mode=False:run()
    full_stack.package.run('install')
