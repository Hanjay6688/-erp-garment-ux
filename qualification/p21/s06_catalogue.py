"""Bind the three S06 function bodies before Global captures its final seal."""

from hashlib import sha256

from .s06_source import confirm_source, require, PRODUCT, TREE, PARENT, FILES


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
        with provider.as_role(cur, 'postgres'), provider.metadata_context(cur):
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
        with provider.as_role(cur, 'postgres'), provider.metadata_context(cur):
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
