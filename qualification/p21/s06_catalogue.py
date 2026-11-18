"""Bind the three S06 function bodies before Global captures its final seal."""

from hashlib import sha256
from contextlib import contextmanager
import re

from .s06_source import confirm_source, require, PRODUCT, TREE, PARENT, FILES


@contextmanager
def phase(name):
    """Retain a bounded installer error in the public terminal receipt."""
    print(f'GLOBAL_ORDINARY_PHASE P21_S06_{name} STARTED', flush=True)
    try:
        yield
    except Exception as error:
        kind = type(error).__name__.upper()
        kind = kind if re.fullmatch(r'[A-Z0-9_]{1,48}', kind) else 'ERROR'
        state = getattr(error, 'sqlstate', None)
        state = state if isinstance(state, str) and re.fullmatch(r'[0-9A-Z]{5}', state) else 'NONE'
        print(f'GLOBAL_ORDINARY_PHASE P21_S06_{name} FAILED', flush=True)
        raise ValueError(f'CP7_S06_{name}_{kind}_SQLSTATE_{state}') from error
    else:
        print(f'GLOBAL_ORDINARY_PHASE P21_S06_{name} COMPLETED', flush=True)


def project_functions(catalogue, original, installed):
    rows = dict(catalogue['functions'])
    require(all(rows.get(name) == body for name, body in installed.items()),
            'CP7_S06_INSTALLED_FUNCTION_DRIFT')
    return dict(catalogue, functions=[[name, original.get(name, body)]
                                     for name, body in catalogue['functions']])


def bind(provider, product, predecessor_receipt):
    from global_owning import owning

    confirm_source(product)
    change = owning.load('cp7_exact_s06_install', product / 'scripts/cp7_s06_reminder_forward.py')
    expected = change.expected_bodies()
    repair = provider._repair_readers_preseal
    predecessor = provider._repair_predecessor_image
    restore = provider._repair_restore_unused
    original = installed = install_receipt = None

    def install_layer(cur):
        nonlocal original, installed, install_receipt
        repairs = repair(cur)
        before = provider.capture(cur)
        # The retained full install grants cp7_alert to Supabase Admin.
        # Reuse that existing installer authority; postgres cannot replace it.
        with phase('INSTALL'), provider.as_role(cur, 'supabase_admin'), provider.metadata_context(cur):
            install_receipt = change.install(cur)
            require(install_receipt['status'] == 'INSTALLED', 'CP7_S06_FRESH_INSTALL_REQUIRED')
            require(change.install(cur)['status'] == 'ALREADY_INSTALLED', 'CP7_S06_INSTALL_REPLAY_FAILED')
        after = provider.capture(cur)
        original = {name: row for name, row in before['functions'] if name in expected}
        installed = {name: row for name, row in after['functions'] if name in expected}
        require(set(original) == set(installed) == set(expected)
                and all(original[name][1:] == installed[name][1:] for name in expected)
                and project_functions(after, original, installed) == before,
                'CP7_S06_UNDECLARED_CATALOGUE_CHANGE')
        return repairs

    def project(before, after):
        return predecessor(before, project_functions(after, original, installed))

    def remove_layer(cur, state):
        current = provider.capture(cur)
        project_functions(current, original, installed)
        with phase('UNUSED_INVERSE'), provider.as_role(cur, 'supabase_admin'), provider.metadata_context(cur):
            for name in expected:
                cur.execute(original[name][0], prepare=False)
        require(provider.capture(cur) == project_functions(current, original, installed),
                'CP7_S06_UNUSED_INVERSE_INCOMPLETE')
        restore(cur, state)

    provider._repair_readers_preseal = install_layer
    provider._repair_predecessor_image = project
    provider._repair_restore_unused = remove_layer

    def receipt(state):
        detail = dict(install_receipt, product=PRODUCT, tree=TREE, parent=PARENT,
                      changed_paths=sorted(FILES), install_replay=True,
                      changed_function_count=len(installed),
                      installed_definition_sha256={name: sha256(row[0].encode()).hexdigest()
                                                   for name, row in installed.items()})
        return dict(predecessor_receipt(state), s06=detail)

    return receipt
