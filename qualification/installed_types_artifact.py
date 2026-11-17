"""Select only the public type export from a successful disposable Global run."""

from hashlib import sha256
import json
from pathlib import Path
import sys

from global_owning.installed_types import INVENTORY_SHA, TYPE_FILE, public_erp_names, require
from global_owning import installed_types_only


def select(scratch, output):
    focused = installed_types_only.enabled()
    receipt_name = 'CP7_GLOBAL_INSTALLED_FINAL.json' if focused else 'GLOBAL_ORDINARY_FINAL.json'
    result = json.loads((scratch / receipt_name).read_bytes())
    require(result['status'] == 'PASS' and len(result['checks']) == (12 if focused else 16)
            and all(result['checks'].values()) and result['actual_Global_cases'] == (0 if focused else 23)
            and all(v == 'success' for v in result['workflow'].values())
            and result['production_go'] is result['independent_acceptance'] is False,
            'CP7_INSTALLED_TYPES_GLOBAL_PACKAGE_RECEIPT_REQUIRED')
    receipt_raw = (output / 'CP7_INSTALLED_TYPES.json').read_bytes()
    if focused:
        require(result['contract'] == 'cp7.global.installed-observation.v1'
                and result['scope'] == installed_types_only.SCOPE
                and result['schema_receipt'] == dict(bytes=len(receipt_raw), sha256=sha256(receipt_raw).hexdigest()),
                'CP7_INSTALLED_TYPES_EXACT_FOCUSED_RECEIPT_REQUIRED')
    receipt = json.loads(receipt_raw)
    path = output / TYPE_FILE
    raw = path.read_bytes()
    expected = receipt['generated']
    inventory = receipt['installed_legacy_inventory']
    counts = tuple(inventory[key] for key in ('fabric_rows', 'active_fabric_rows', 'recorded_minimum_rows'))
    require(inventory['status'] == 'PASS' and inventory['source_sha256'] == INVENTORY_SHA
            and all(type(count) is int and count >= 0 for count in counts)
            and counts[1] <= counts[0] and counts[2] <= counts[0]
            and inventory['references_and_preview_cache_equal'] is True
            and inventory['preseal_reference_tables_equal'] is True
            and inventory['persisted_policy_changes'] is False,
            'CP7_INSTALLED_TYPES_LEGACY_INVENTORY_RECEIPT_REQUIRED')
    require(receipt['status'] == expected['status'] == 'PASS'
            and receipt['source_catalogue_equal'] is receipt['all_rows_and_sequences_equal'] is True
            and receipt['catalogue_groups'] == 25 and receipt['public_erp_names'] == len(public_erp_names(raw))
            and expected['raw_sha256'] == sha256(raw).hexdigest() and expected['raw_bytes'] == len(raw)
            and expected['schema'] == 'public' and expected['hosted'] is False
            and expected['cli_version'] == '2.116.0' and expected['raw_name'] == TYPE_FILE
            and len(raw) < 1_000_000, 'CP7_INSTALLED_TYPES_VALIDATED_PUBLIC_EXPORT_REQUIRED')
    target = scratch / 'installed-public-types'
    target.mkdir(mode=0o700)
    (target / TYPE_FILE).write_bytes(raw)
    (target / 'CP7_INSTALLED_TYPES.json').write_bytes(receipt_raw)


if __name__ == '__main__':
    require(len(sys.argv) == 3, 'CP7_INSTALLED_TYPES_FIXED_ARTIFACT_DIRS_REQUIRED')
    select(Path(sys.argv[1]), Path(sys.argv[2]))
