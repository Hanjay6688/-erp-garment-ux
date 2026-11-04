"""Check the whole retained browser/fixture sources before runtime adoption."""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import argparse
import importlib.util
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PINS = {
    'fixture': dict(bytes=8281, sha256='9d7cfae86d679c7803514db886fc69c8cdc1c8eac2fcda5a3a298927227803b7'),
    'browser_fixture': dict(bytes=7848, sha256='c0d7c52948e92ee55ab324844d2b71a5d0f32b605665837665dfa17c56ba3022'),
    'browser': dict(bytes=22853, sha256='7a1cb2ea0d5b4bed519f45d07ed95b381fae3e01cfa31c6835c30317765c9537'),
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


assembly = load('current_browser_closed_source_assembly', HERE / 'assembly.py')


def check(*, runtime=False):
    if runtime:
        assembly.admission.require_ready()
    else:
        assembly.require(all(getattr(assembly.admission, name) is None for name in assembly.admission.GATES),
                         'CURRENT_SKU_BROWSER_PREPARATION_MUST_KEEP_ALL_GATES_CLOSED')
    own = assembly.source_manifest()
    reference = assembly.prepared_sources()[0]
    deriver = load('current_browser_exact_retained_Native27_sources',
                   ROOT / 'scripts/current-sku-managed-recovery-native27-qualification/derive.py')
    sources = {}
    for name, expected in PINS.items():
        text, proof = deriver.derive(name)
        assembly.require(assembly.admission.pin(text.encode()) == expected, 'CURRENT_SKU_EXACT_BROWSER_SOURCE_REQUIRED:' + name)
        sources[name] = dict(source=expected, complete_retained_derivation=proof)
    tree = reference['automatic_source']['tree']
    native = load('current_browser_original_public_facade_shapes', ROOT / 'scripts/cp7_sku_pair_conversion/native_delta.py')
    signatures = list(native.SIGNATURES[:4])
    assembly.require(len(set(signatures)) == 4 and all(name.startswith('public.') for name in signatures),
                     'CURRENT_SKU_FOUR_REAL_PUBLIC_FACADES_REQUIRED')
    permissions = set()
    for file in ('pairs.sql', 'conversion.sql'):
        raw = assembly.git('show', tree + ':scripts/cp7_sku_pair_conversion/' + file)
        permissions.update(re.findall(r"erp\.(?:require_permission|has_permission)\('([^']+)'\)", raw.decode()))
    private = assembly.git('show', tree + ':scripts/cp7_sku_moving_average/private_delta.py')
    assembly.require(all(token in private for token in (b'pool_quote_v2', b'native_physical_value',
        b'SKU_LOCATION_GRADE_MOVING_AVERAGE_V2', b'source_value_pool', b'target_value_pool')),
        'CURRENT_SKU_REAL_MOVING_AVERAGE_PREVIEW_CONTRACT_REQUIRED')
    source = Decimal(3) * Decimal('10.01') + Decimal(7) * Decimal('20.02')
    target = Decimal(4) * Decimal('30.03')
    raw_transfer = Decimal(4) * source / Decimal(10)
    booked = raw_transfer.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    physical = Decimal(2) * Decimal('10.01') + Decimal(2) * Decimal('20.02')
    ui_path = ROOT / 'src/HppPage.tsx'
    stale_cogs_text = 'Saat penjualan, COGS tetap mengambil HPP lot sesuai FIFO.'
    return dict(classification='CURRENT_BROWSER_SOURCE_AND_ORACLES_PREPARED_NOT_ACTUAL_AUTH_OR_BROWSER',
                owning_source=own, retained_full_sources=sources, actual_public_facades=signatures,
                declared_source_permissions=sorted(permissions), permissions_not_checked_on_actual_actors=True,
                exact_current_preview_deriver=assembly.admission.pin(private),
                independent_fixture_oracle=dict(source_qty='10', source_value=str(source), source_reserved='1',
                    target_qty='4', target_value=str(target), conversion_qty='4',
                    native_physical_value=str(physical), raw_economic_transfer=str(raw_transfer),
                    booked_moving_average_transfer=str(booked), source_after_raw=str(source-raw_transfer),
                    target_after_raw=str(target+raw_transfer), global_value=str(source+target)),
                old_browser_FIFO_accounting_expectation_must_not_be_reused=True,
                historical_cogs_help_text_still_needs_current_integration=stale_cogs_text in ui_path.read_text(),
                exact_fixture_current_product_binding_and_real_copy_runtime_still_pending=True,
                Native25_runtime_still_excludes_these_new_browser_cases=True,
                actual_browser_cases=0, actual_Auth_HTTP_cases=0, actual_ERP_cases=0,
                production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--runtime', action='store_true');args = parser.parse_args()
    print(json.dumps(check(runtime=args.runtime), sort_keys=True))
