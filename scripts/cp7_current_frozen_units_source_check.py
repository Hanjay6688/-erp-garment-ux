"""Local adversarial source/catalog checks; never opens a database connection."""
from contextlib import ExitStack, nullcontext
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import ast
import importlib.util
import json
import shutil
import sys


def run(repo):
    import psycopg
    def forbidden(*args, **kwargs):
        raise AssertionError('SOURCE_CHECK_MUST_NOT_CONNECT_DATABASE')
    with patch.object(psycopg, 'connect', forbidden):
        sys.path.insert(0, str(repo/'scripts'))
        path = repo/'scripts/current-versioned-performance-native-qualification/probe.py'
        spec = importlib.util.spec_from_file_location('frozen_source_runtime_graph', path)
        graph = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(graph)
        import cp7_current_frozen_units as inputs
        from cp7_current_frozen_units import binary
        import cp7_current_frozen_units_installation as product
        admitted = inputs.sources()
        def definitions(path):
            return {n.name: ast.dump(n, include_attributes=False)
                    for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef)}
        original = definitions(repo/'scripts/cp7_history_reference_binary_v2/__init__.py')
        adapted = definitions(repo/'scripts/cp7_current_frozen_units/binary.py')
        database_functions = sorted(set(original)-{'sources', 'verify_sources'})
        assert all(original[k] == adapted[k] for k in database_functions)
        refused = []
        manifest = json.loads((inputs.ROOT/'BOUND_B_SOURCES.json').read_bytes())
        source_cases = [
            ('retained_v1_changed', 'cp7_history_reference/digest.sql', '\n-- changed\n'),
            ('qualified_render_input_changed', 'cp7_current_frozen_units/qualified-B-v1-render-input.sql', '\n-- changed\n'),
            ('binary_SQL_changed', 'cp7_history_reference_binary_v2/digest.sql', '\n-- changed\n'),
            ('binary_manifest_changed', 'cp7_history_reference_binary_v2/MANIFEST.json', '\n'),
            ('capsule_SQL_changed', 'cp7_frozen_analysis_v2/capsule.sql', '\n-- changed\n'),
            ('units_SQL_changed', 'cp7_frozen_analysis_units_v2/hooks.prepared.sql', '\n-- changed\n'),
            ('undeclared_B_file', 'cp7_frozen_analysis_units_v2/unqualified.sql', 'select 1;\n'),
            ('qualified_receipt_declaration_changed', 'cp7_current_frozen_units/BOUND_B_SOURCES.json', '\n'),
        ]
        with TemporaryDirectory(prefix='cp7-frozen-source-') as temporary:
            destination = Path(temporary)
            scripts = destination/'scripts'
            paths = set(manifest['files']) | {
                'scripts/cp7_history_reference/digest.sql',
                *('scripts/cp7_current_frozen_units/'+p.name for p in inputs.ROOT.iterdir() if p.is_file()),
            }
            for relative in paths:
                target = destination/relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(repo/relative, target)
            with patch.multiple(inputs, ROOT=scripts/'cp7_current_frozen_units', REPO=destination), \
                 patch.multiple(binary, ROOT=scripts/'cp7_history_reference_binary_v2', ADAPTER_ROOT=scripts/'cp7_current_frozen_units'):
                binary.verify_sources()
                for label, path, suffix in source_cases:
                    target = scripts/path
                    before = target.read_bytes() if target.exists() else None
                    try:
                        target.write_bytes((before or b'')+suffix.encode())
                        try:
                            binary.verify_sources()
                        except ValueError:
                            refused.append(label)
                        else:
                            raise AssertionError('UNQUALIFIED_SOURCE_ACCEPTED:'+label)
                    finally:
                        if before is None:
                            target.unlink()
                        else:
                            target.write_bytes(before)
                binary.verify_sources()

        # Exercise the complete transition validator against changed authority,
        # undeclared objects and missing replacements, using source-derived keys.
        originals = product.units.render.originals()
        new_functions = product.units.FUNCTIONS
        before = {k:{} for k in ('schemas', 'functions', *('group'+str(i) for i in range(20)))}
        after = deepcopy(before)
        state = dict(old_rows={}, new_rows={}, catalog=deepcopy(before))
        for signature in originals:
            old = ['retained:'+signature, 'old-body', 'cp7_capture', False]
            new = ['qualified:'+signature, 'new-body', 'cp7_capture', False]
            state['old_rows'][signature] = old
            state['new_rows'][signature] = new
            before['functions'][signature] = [old[0], 'unchanged-owner-ACL-settings']
            after['functions'][signature] = [new[0], 'unchanged-owner-ACL-settings']
        for signature in new_functions:
            state['new_rows'][signature] = ['private:'+signature, 'body', 'cp7_capture', False]
            after['functions'][signature] = ['private:'+signature, 'private-authority']
        after['schemas'][product.units.SCHEMA] = ['cp7_capture', 'private-ACL']
        state['catalog'] = deepcopy(after)
        product._admit_units(before, after, state)
        def reject_transition(label, change):
            b, a, s = deepcopy(before), deepcopy(after), deepcopy(state)
            change(b, a, s)
            try:
                product._admit_units(b, a, s)
            except ValueError:
                refused.append(label)
            else:
                raise AssertionError('UNQUALIFIED_TRANSITION_ACCEPTED:'+label)
        first = next(iter(originals))
        def authority(b, a, s):
            a['functions'][first][1] = 'public-execute-granted'
            s['catalog'] = deepcopy(a)
        reject_transition('existing_function_authority_changed', authority)
        reject_transition('unrelated_object_changed', lambda b,a,s: a['group0'].update(unrelated=['changed']))
        reject_transition('missing_replacement', lambda b,a,s: a['functions'].__setitem__(first,b['functions'][first]))
        reject_transition('missing_private_function_state', lambda b,a,s: s['new_rows'].pop(next(iter(new_functions))))

        # The real inverse entry point must refuse both data and sequence drift
        # before it invokes any component inverse. This is a local guard test.
        inverse_calls = []
        for name, actual in [('row_drift', {'rows':'changed','sequence:one':1}),
                             ('sequence_drift', {'rows':'same','sequence:one':2})]:
            with ExitStack() as stack:
                stack.enter_context(patch.object(product, 'atomic', lambda cur:nullcontext()))
                stack.enter_context(patch.object(product, '_locks', lambda cur:None))
                stack.enter_context(patch.object(product, 'verify', lambda cur,state:None))
                stack.enter_context(patch.object(product.catalog, '_data', lambda cur:actual))
                for module in (product.units, product.capsule, product.binary, product.predecessor):
                    stack.enter_context(patch.object(module, 'rollback_preuse', lambda *a:inverse_calls.append('inverse')))
                try:
                    product.rollback_preuse(object(), {'preuse_data_and_sequences':{'rows':'same','sequence:one':1}})
                except ValueError as error:
                    assert str(error) == product.USED_ERROR
                    refused.append(name+'_before_inverse')
                else:
                    raise AssertionError('USED_INVERSE_ACCEPTED:'+name)
        assert not inverse_calls
        product_source = repo/'scripts/cp7_current_frozen_units_installation.py'
        ast.parse(product_source.read_bytes())
        return dict(status='LOCAL_SOURCE_AND_GUARD_PASS', exact_B_files=20,
                    qualified_B_head=admitted['bound']['B_head'],
                    unchanged_B_database_functions=database_functions,
                    negative_controls=refused, negative_control_count=len(refused),
                    global_used_guard_no_inverse_calls=True,
                    entrypoint_sha256=sha256(product_source.read_bytes()).hexdigest(),
                    local_mock_guard_test_only=True, database_executed=False,
                    A_runtime_qualified=False, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(run(root), indent=2))
