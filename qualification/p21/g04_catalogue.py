"""Install the pinned Switch Roll layer before the final Global seal."""

from hashlib import sha256

from .g04_invoice import confirm_source, require


SCHEMA = 'cp7_switch_roll'
CORRECTIONS = f'{SCHEMA}.corrections'
SOURCE_SHA = 'dac3f026f2b2b7d891fc0106fd1960f55c39959aa6756611f45c8179df8e1422'
COUNTS = dict(schemas=1, functions=13, relations=4, columns=14, constraints=4,
              indexes=3, triggers=9, policies=1, types=2, type_implementation=2)
REFERENCES = {'corrections_issue_id_fkey': 'erp.material_stock_movements',
              'corrections_purchase_id_fkey': 'erp.material_purchase_headers'}


def split_catalogue(catalogue, signatures):
    """Separate only this extension's rows for the retained transition check."""
    def included(group, name, row):
        if group == 'schemas':
            return name == SCHEMA
        if group == 'functions':
            return name in signatures
        if group == 'triggers' and row[0] is True:
            target = REFERENCES.get(row[12])
            return (target is not None and row[15] == CORRECTIONS
                    and name.split(':', 1)[0] in (CORRECTIONS, target))
        return group in COUNTS and name.startswith(f'{SCHEMA}.')

    retained, added = {}, {}
    for group, rows in catalogue.items():
        retained[group] = []
        for name, row in rows:
            target = added.setdefault(group, []) if included(group, name, row) else retained[group]
            target.append([name, row])
    require({group: len(rows) for group, rows in added.items()} == COUNTS
            and {name for name, _ in added['functions']} == signatures,
            'CP7_P21_G04_SWITCH_ROLL_CATALOGUE_SHAPE')
    return retained, added


def bind_switch_roll(provider, product):
    """Extend the already bound P20 preseal and unused inverse in this run."""
    from global_owning import owning

    confirm_source(product)
    roll = owning.load('cp7_g04_exact_switch_roll', product / 'scripts/cp7_switch_roll_install.py')
    require(sha256(roll.SQL.read_bytes()).hexdigest() == SOURCE_SHA,
            'CP7_P21_G04_SWITCH_ROLL_INSTALL_SOURCE')
    signatures = set(roll.PUBLIC) | {f'{SCHEMA}.{name}' for name in roll.PRIVATE}
    repair = provider._repair_readers_preseal
    predecessor = provider._repair_predecessor_image
    restore = provider._repair_restore_unused
    verify_inverse = provider._timezone_verify_inverse
    addition = installed = None

    def install_layer(cur):
        nonlocal addition, installed
        repairs = repair(cur)
        before = provider.capture(cur)
        # P21 installed this layer through the existing Supabase Admin connection.
        # PostgreSQL's postgres role cannot transfer ownership to cp7_procure_write.
        with provider.as_role(cur, 'supabase_admin'):
            installed = roll.install(cur)
        projected, addition = split_catalogue(provider.capture(cur), signatures)
        require(projected == before and installed['source_sha256'] == SOURCE_SHA
                and installed['public_rpc_count'] == len(roll.PUBLIC)
                and installed['predecessor_public_functions_preserved'] is True
                and installed['browser_capabilities_scoped'] is True,
                'CP7_P21_G04_SWITCH_ROLL_UNDECLARED_CATALOGUE_CHANGE')
        return repairs

    def project(before, after):
        after, observed = split_catalogue(after, signatures)
        require(observed == addition, 'CP7_P21_G04_SWITCH_ROLL_PRESEAL_DRIFT')
        return predecessor(before, after)

    def remove_layer(cur, state):
        with provider.as_role(cur, 'supabase_admin'):
            roll.remove_preuse(cur)
        restore(cur, state)

    def verify_removed(cur, state):
        # The retained inverse already compared all rows and sequences before DDL.
        retained = dict(state['preuse_data_and_sequences'])
        del retained[CORRECTIONS]
        verify_inverse(cur, dict(state, preuse_data_and_sequences=retained))

    provider._repair_readers_preseal = install_layer
    provider._repair_predecessor_image = project
    provider._repair_restore_unused = remove_layer
    provider._timezone_verify_inverse = verify_removed

    def receipt(state):
        return dict(installed, catalogue_additions=COUNTS,
                    sealed_fingerprint=state['sealed']['actual_parent_root_receipt']['catalogue_fingerprint'])

    return receipt
