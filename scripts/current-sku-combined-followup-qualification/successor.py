"""Writer-only exact transition961 ->21c; no qualification result is created.

The fixed path and digest table was reviewed once against the published UTC
candidate. The binder never fills it from current filesystem contents.
"""
from hashlib import sha256
from pathlib import Path
import gzip
import json

PRIOR = '961c22f8d3fa6fd2c16a8932a23b6d3a347d0c98'
BASE = '21c69cf25defcee854beb08e998062d7e883d968'
TREE = 'a0d2c0da83bf5dc29f2c6b2e02abe6d7ed68f89e'
REVIEWED = {
    '.github/workflows/cp7-sku-pair-native.yml': ('19c87d15d533b9886125f5e98874ca86d5422111eed3e8ce7684ba8431797d56', '995de2a59f91c77471e193d5a7d48f4b0e05c089d1a0fc560c45ffb4cce11cbd'),
    'scripts/cp7_sku_pair_conversion/UTC_FINGERPRINT_REPAIR_LOCAL.json': (None, 'f79a8435dac41a36fcd1fe5d8d865ced7783dab6d2769d9c460147e2dfd01366'),
    'scripts/cp7_sku_pair_conversion/conversion.sql': ('71211f85eae538e96886bc401e4357dc54259f4783c938d3fa4ab4b1c66deff5', '4b26a65beae5defc877589dae756ce2adc9ecb19b3b9a3b68c86765a4c434961'),
    'scripts/current-sku-pair-conversion-qualification/cases.py': ('d6ce9825ce9a60715cce7a1667d5c09a3c65b328c8cadac7dd219f6a81f464f6', '5a2e70eb96edc54318cf331c4583af48abdf63f783da19a1974725be0414f4e9'),
    'scripts/current-sku-pair-native-adapter/CONFIG.json': ('4f258dbede795eb8e1ba004ded5fbd69d8f7466e411ab60736c6a6264445a7b4', 'ae26caea82d3bd65cf555078291d711240fb5a30905febd8974b208a44eaa039'),
    'scripts/current-sku-pair-native-adapter/README.md': ('fe04b9761d9d4ed7e5e1073efab31db3417313d7c6388b0592146efc6db88d45', 'fa41531dddc9eafc7aec1da2bf83729411ceb7ee6bc222b9b306ca5ada2e4ecf'),
    'scripts/current-sku-pair-native-adapter/SOURCE.json': ('af049d8a42d5a03aafd781e6e7cbd7f9a74dd05b1b90cc04b01f9b2abedb77de', '55578488fee984b1eba421d7a58ad9d3ee825bbedc2c53d0e3090676883b41e7'),
    'scripts/current-sku-pair-native-adapter/retained961/CP7_SKU_PAIR_CONVERSION_NATIVE.json.gz': (None, 'e8467ae86927411b3ee8ec08646ebc7e6002e0ee4d4518effd4a7a918f71b231'),
    'scripts/current-sku-pair-native-adapter/retained961/CP7_SKU_PAIR_CONVERSION_NATIVE7.json.gz': (None, '34c3c12b3d99d8111c4dff9c4a6d728a85db04086a92ec6967e7b1903309a60e'),
    'scripts/current-sku-pair-native-adapter/retained961/LOCAL_CANONICAL_FIRST_FAILURE.log': (None, 'a36b590ca0fd33c44117da3e85ff11fd8ad9aa4bcb86bad3a9e6d3b5eddce904'),
    'scripts/current-sku-pair-native-adapter/retained961/LOCAL_SQL15_VM30.json': (None, 'ea36524e82ee40416d690c4f5546e7b157ee15bb450ab80c31bcb6ad0a3e5deb'),
    'scripts/current-sku-pair-native-adapter/retained961/LOCAL_VM_DEFAULT_HOOK_FAILURE.json': (None, '937c0f88d55798d434c18b15d32a368ce1db32f90133e3b36ec7710d3b4737ee'),
    'scripts/current-sku-pair-native-adapter/retained961/RECEIPT.json': (None, 'b8ef73037dbfd8ad8dfb11f23d01e8f66ba82d1c3963372caaf77d350f414ec0'),
    'scripts/current-sku-pair-native-adapter/retained961/T3_BACKUP_RESTORE_DRILL.json.gz': (None, '229b1ccc5f22693fe9e1fbbacaa2df1deee0a246713cb87a3bdca3e6dec39891'),
    'scripts/current-sku-pair-native-adapter/retained961/T3_PACKAGE_FILES_INSTALL.json.gz': (None, 'a1c8a1ca1ae654997ead274c2d51fa04a6b55916b9b23f4339741c81760083e7'),
    'scripts/current-sku-pair-native-adapter/retained961/T3_PACKAGE_INSTALL.json.gz': (None, 'c6f351f055908f0c1439c6172bd68377416f5de4ab4115b613b8fe29811cd1e7'),
    'scripts/current-sku-pair-native-adapter/test_workflow.py': ('f0dcf317616cba4af01fed41dc6f5509dc37c4f223c207149a0e15406e1c9bb8', 'e5456ec2d34cd9319b409a5f93b80b4d7ed6a33eb555f007e13b35eac4b499e6'),
    'tests/cp7/families/sku-pair-conversion.test.ts': ('005774633d7be69ebf2e3918865bc51a97e08bc53805d1f83877fe70b86e5db1', 'c9e11478ecdd1669de2aec8df42c660807b566a29913da8278a0fe6cbfba4240'),
}


SQL_REPLACEMENTS = (
    ("create function cp7_sku_conversion.revision_v1(p_source uuid,p_target uuid,p_location uuid)returns text\n"
     "language sql stable security definer set search_path=''as $$",
     "-- Timestamp-bearing facts must have the same canonical serialization for a\n"
     "-- preview caller and the UTC posting coordinator. No field is excluded.\n"
     "create function cp7_sku_conversion.revision_v1(p_source uuid,p_target uuid,p_location uuid)returns text\n"
     "language sql stable security definer set search_path=''set timezone='UTC'as $$"),
    ("create function cp7_sku_conversion.preview_v1(p_payload jsonb)returns jsonb\n"
     "language plpgsql volatile security definer set search_path=''as $$",
     "create function cp7_sku_conversion.preview_v1(p_payload jsonb)returns jsonb\n"
     "language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$"),
)

MIXED_INSERT = """    # A production fixture may leave WIB as caller timezone while the posting
    # coordinator runs in UTC. Compare the same untouched source in all five
    # retained business-day zones; a timezone change must never fake staleness.
    zones=('Asia/Jakarta','UTC','Asia/Tokyo','Pacific/Kiritimati','Etc/GMT+12')
    reviewed=[];ledger_before=f.native_ledgers(cur)
    for zone in zones:
        cur.execute("select set_config('TimeZone',%s,true)",(zone,))
        frozen,v=f.review(cur,p);reviewed.append(v)
        assert f.one(cur,"select current_setting('TimeZone')")==zone
        assert f.native_ledgers(cur)==ledger_before
    assert all(row==reviewed[0]for row in reviewed),reviewed
    cur.execute("set local timezone='Asia/Jakarta'")
"""
MIXED_RETURN = (
    "      quantity_and_exact_lot_value_conserved=True,Native_financial_detectors_unchanged=True)",
    "      quantity_and_exact_lot_value_conserved=True,Native_financial_detectors_unchanged=True,\n"
    "      preview_caller_zones_checked=list(zones),all_preview_fields_equal_across_zones=True,\n"
    "      preview_caller_setting_restored=True,posting_function_timezone='UTC')",
)


def replacements(raw, pairs):
    result = raw.decode()
    for before, after in pairs:
        assert result.count(before) == 1, 'SKU_COMBINED_REVIEWED_TRANSITION_ANCHOR_CHANGED'
        result = result.replace(before, after, 1)
    return result.encode()


def admit_transition(git):
    """Check exact eighteen-path transition and retain the real six-pass failure."""
    paths = git('diff', '--name-only', PRIOR, BASE).decode().splitlines()
    assert set(paths) == set(REVIEWED), 'SKU_COMBINED_UNREVIEWED_NATIVE_BASE_CHANGE'
    assert git('rev-parse', BASE + '^{tree}').decode().strip() == TREE
    for name, (old, new) in REVIEWED.items():
        if old is not None:
            assert sha256(git('show', PRIOR + ':' + name)).hexdigest() == old, name
        assert sha256(git('show', BASE + ':' + name)).hexdigest() == new, name
    sql = 'scripts/cp7_sku_pair_conversion/conversion.sql'
    assert replacements(git('show', PRIOR + ':' + sql), SQL_REPLACEMENTS) == git('show', BASE + ':' + sql)
    cases = 'scripts/current-sku-pair-conversion-qualification/cases.py'
    anchor = "    frozen,v=f.review(cur,p);made=f.action(cur,'POST',frozen);rows=f.allocations(cur,made)"
    assert replacements(git('show', PRIOR + ':' + cases), ((anchor, MIXED_INSERT + anchor), MIXED_RETURN)) == git('show', BASE + ':' + cases)
    prefix = 'scripts/current-sku-pair-native-adapter/retained961/'
    receipt = json.loads(git('show', BASE + ':' + prefix + 'RECEIPT.json'))
    assert receipt['head'] == PRIOR and receipt['status'] == 'INCOMPLETE'
    assert receipt['case_counts'] == {'PASS': 6, 'INCOMPLETE': 1}
    assert receipt['writer_runtime'] is False and receipt['used_inverse_guard_NOT_observed'] is True
    for name, pin in receipt['files'].items():
        raw = gzip.decompress(git('show', BASE + ':' + prefix + name + '.gz'))
        assert len(raw) == pin['raw_bytes'] and sha256(raw).hexdigest() == pin['raw_sha256'], name
    return dict(prior_head=PRIOR, head=BASE, tree=TREE, reviewed_paths={
        name: dict(prior_sha256=old, successor_sha256=new) for name, (old, new) in REVIEWED.items()},
        product_change='ONLY_TWO_UTC_FUNCTION_ATTRIBUTES_AND_EXPLANATORY_COMMENT',
        Native_case_change='SAME_MIXED_CASE_FIVE_CALLER_ZONES_ALL_FIELDS_EQUAL',
        financial_quantity_value_inverse_oracles_changed=False,
        retained961_status='INCOMPLETE', retained961_counts={'PASS': 6, 'INCOMPLETE': 1},
        retained961_usable_prerequisite=False, actual_successor_execution=False)
