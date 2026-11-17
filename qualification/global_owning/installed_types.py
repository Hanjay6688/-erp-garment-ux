"""Public type intake and rolled-back fabric preview on the disposable installation."""

from contextlib import contextmanager
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import re


GENERATOR = 'cp7_export_disposable_types.py'
GENERATOR_SHA = '6affa65b293293c814e37f049441a50225fa5b006b4d9405ce750dc3d788f6ee'
INVENTORY = 'cp7_install_legacy_inventory.py'
INVENTORY_SHA = 'e5c44eb8c741f6aca67c0d842ac56dd841bc5ea45eae0030e845edae4f8f49b7'
TYPE_FILE = 'database.current-disposable.generated.ts'
RPC = re.compile(r'(?m)^      (erp_[A-Za-z0-9_]+):')
REFERENCES = ('erp.materials', 'erp.fabric_master_profiles')


def require(value, message):
    if not value:
        raise ValueError(message)


def load_exact(candidate, name, digest):
    path = candidate / 'scripts' / name
    require(path.is_file() and path.resolve() == path and sha256(path.read_bytes()).hexdigest() == digest,
            'CP7_INSTALLED_TYPES_EXACT_RETAINED_HELPER_REQUIRED')
    spec = spec_from_file_location('cp7_installed_' + path.stem, path)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def public_erp_names(raw):
    text = raw.decode('utf-8')
    functions = text.split('\n    Functions: {\n', 1)
    require(len(functions) == 2, 'CP7_INSTALLED_TYPES_PUBLIC_FUNCTION_SECTION_REQUIRED')
    block = functions[1].split('\n    Enums: {', 1)
    require(len(block) == 2, 'CP7_INSTALLED_TYPES_PUBLIC_ENUM_BOUNDARY_REQUIRED')
    return set(RPC.findall(block[0]))


@contextmanager
def consistent_read(conn, cur):
    idle = conn.info.transaction_status.name == 'IDLE'
    require(cur.connection is conn and idle and not conn.autocommit, 'CP7_INSTALLED_TYPES_IDLE_OBSERVER_REQUIRED')
    try:
        cur.execute('set transaction isolation level repeatable read read only')
        yield
    finally:
        conn.rollback()


def verify_inventory(conn, cur, inventory):
    require(cur.connection is conn and conn.info.transaction_status.name == 'IDLE'
            and not conn.autocommit,
            'CP7_INSTALLED_TYPES_IDLE_INVENTORY_OBSERVER_REQUIRED')
    try:
        cur.execute("set local statement_timeout='180s';set local lock_timeout='8s'")
        before = inventory.capture(cur)
        evidence = inventory.preview_active_rules(cur, before)
        require(inventory.assert_preserved(cur, before) == before
                and evidence['inventory_sha256'] == before['rows_sha256']
                and evidence['read_only_preview'] is True and evidence['selection_made'] is False,
                'CP7_INSTALLED_TYPES_LEGACY_INVENTORY_CHANGED')
        return dict(status='PASS', source_sha256=inventory.source_hash(),
                    fabric_rows=before['count'], active_fabric_rows=len(evidence['rows']),
                    recorded_minimum_rows=sum(row['minimum_stock_qty'] is not None for row in before['rows']),
                    references_and_preview_cache_equal=True, persisted_policy_changes=False)
    finally:
        conn.rollback()


def collect(conn, cur, *, package, lifecycle, state, preseal_census, candidate, output):
    generator = load_exact(candidate, GENERATOR, GENERATOR_SHA)
    inventory = load_exact(candidate, INVENTORY, INVENTORY_SHA)
    provider = lifecycle.provider
    target = output / TYPE_FILE
    require(not target.exists(), 'CP7_INSTALLED_TYPES_ONE_CAPTURE_REQUIRED')

    with consistent_read(conn, cur):
        lifecycle.verify(cur, state)
        initial = provider.capture(cur)
        data = provider._timezone_snapshot(cur, lock=False)
        require(all(name in preseal_census and name in data and preseal_census[name] == data[name]
                    for name in REFERENCES), 'CP7_INSTALLED_TYPES_PRESEAL_FABRIC_REFERENCES_CHANGED')
        expected = {row[0] for row in cur.execute("""select distinct p.proname
            from pg_proc p join pg_namespace n on p.pronamespace=n.oid
            where n.nspname='public' and p.prokind='f' and left(p.proname,4)='erp_'""").fetchall()}
        require(expected, 'CP7_INSTALLED_TYPES_INSTALLED_PUBLIC_RPC_REQUIRED')
    inventory_record = verify_inventory(conn, cur, inventory)
    inventory_record['preseal_reference_tables_equal'] = True
    record = generator.generate(package.boundary.PG, target)
    generated = public_erp_names(target.read_bytes())
    require(generated == expected, 'CP7_INSTALLED_TYPES_PUBLIC_RPC_INVENTORY_MISMATCH')
    # A fresh snapshot would expose an unexpected committed DML or DDL effect
    # from the CLI connection that the first read-only snapshot could hide.
    with consistent_read(conn, cur):
        require(len(initial) == 25 and provider.capture(cur) == initial
                and provider._timezone_snapshot(cur, lock=False) == data,
                'CP7_INSTALLED_TYPES_CATALOG_OR_DATA_CHANGED')
        lifecycle.verify(cur, state)
        receipt = dict(status='PASS', generated=record, installed_legacy_inventory=inventory_record,
                       public_erp_names=len(expected),
                       catalogue_groups=len(initial), source_catalogue_equal=True,
                       all_rows_and_sequences_equal=True, production_go=False, independent_acceptance=False)

    with (output / 'CP7_INSTALLED_TYPES.json').open('x', encoding='ascii') as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return receipt
