"""Prepare the exact automatic installer over the full current money product.

An actual current Mandor Root, unchanged money source admission and complete
new Native case plan must be bound before this loader inspects any caller.
This preparation neither opens those gates nor provides an active workflow.
"""
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN_AUTO = ROOT.parent / 'qualified-sku-automatic'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


admission = load('current_automatic_closed_admission', HERE / 'admission.py')
derivation = load('current_automatic_exact_interface_derivation', HERE / 'derive.py')


def require(value, message):
    if not value:
        raise ValueError(message)


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def prepared_sources():
    ref = json.loads((HERE / 'SOURCE_REFERENCE.json').read_bytes())
    require(ref['classification'] == 'EXACT_PREPARED_AUTOMATIC_SOURCE_NOT_ERP_ACCEPTANCE'
            and ref['actual_ERP_cases'] == 0 and ref['production_go'] is False,
            'SKU_AUTOMATIC_SOURCE_REFERENCE_IS_NOT_ACCEPTANCE')
    tree = ref['automatic_source']['tree']
    require(len(ref['automatic_files']) == 20 and len(ref['unchanged_money_product']['files']) == 44,
            'SKU_AUTOMATIC_COMPLETE_SOURCE_FILE_SETS_REQUIRED')
    for name, blob in ref['unchanged_money_product']['files'].items():
        require(git('rev-parse', tree + ':' + name).decode().strip() == blob,
                'SKU_AUTOMATIC_ORIGINAL_MONEY_PRODUCT_CHANGED:' + name)
    for name, expected in ref['automatic_files'].items():
        raw = git('show', tree + ':' + name)
        require(admission.pin(raw) == {k: expected[k] for k in ('bytes', 'sha256')}
                and git('rev-parse', tree + ':' + name).decode().strip() == expected['blob'],
                'SKU_AUTOMATIC_EXACT_REVIEWED_ADDITION_REQUIRED:' + name)
    raw = git('show', tree + ':scripts/cp7_sku_automatic_pending/composition.py')
    text, proof = derivation.derive(raw)
    return ref, text, proof


def source_manifest():
    raw = (HERE / 'SOURCE.json').read_bytes()
    value = json.loads(raw)
    require(value['contract'] == 'cp7.current-automatic-product-bridge-preparation.v1'
            and value['actual_ERP_cases'] == 0 and value['production_go'] is False,
            'SKU_AUTOMATIC_EXACT_PREPARATION_MANIFEST_REQUIRED')
    closed = [getattr(admission, name) is None for name in admission.GATES]
    require(all(closed) or not any(closed), 'SKU_AUTOMATIC_NO_PARTIAL_RUNTIME_ADMISSION')
    require(value['all_admission_values_unset'] is all(closed)
            and value.get('actual_parent_adopted', False) is (not any(closed)),
            'SKU_AUTOMATIC_SOURCE_AND_ACTUAL_GATE_STATE_REQUIRED')
    for name, expected in value['files'].items():
        path = HERE / name
        require(path.is_file() and not path.is_symlink() and admission.pin(path.read_bytes()) == expected,
                'SKU_AUTOMATIC_PREPARATION_SOURCE_CHANGED:' + name)
    require(value['derivation'] == prepared_sources()[2], 'SKU_AUTOMATIC_DECLARED_DERIVATION_CHANGED')
    return admission.pin(raw)


def load_prepared(bridge, parent, money_module, automatic_module, parent_raw, money_raw, plan_raw):
    admission.require_ready()  # Before caller/module/receipt/file/Git/ERP inspection.
    receipt = admission.inputs(parent_raw, money_raw, plan_raw)
    own = source_manifest()
    ref, text, proof = prepared_sources()
    require(Path(bridge.__file__).resolve() == ROOT / 'scripts/current-sku-money-composite-preparation/assembly.py',
            'SKU_AUTOMATIC_EXACT_CURRENT_MONEY_BRIDGE_REQUIRED')
    # The retained bridge admits the actual complete Mandor17 parent and the
    # unqualified money candidate. It does not require a duplicate money19 run.
    money = bridge.load_prepared(parent, money_module, parent_raw, money_raw)
    expected = FROZEN_AUTO / 'scripts/cp7_sku_automatic_pending'
    require(Path(automatic_module.__file__).resolve() == expected / 'composition.py',
            'SKU_AUTOMATIC_EXACT_FROZEN_INSTALLER_MODULE_REQUIRED')
    for name in ('catalog_additions', 'installation_product'):
        require(Path(getattr(automatic_module, name).__file__).resolve() == expected / (name + '.py'),
                'SKU_AUTOMATIC_EXACT_FROZEN_DEPENDENCY_REQUIRED:' + name)
    require(automatic_module.parent() is money_module, 'SKU_AUTOMATIC_ORIGINAL_MONEY_MODULE_CONTEXT_REQUIRED')

    def frozen():
        require(subprocess.check_output(['git', '-C', str(FROZEN_AUTO), 'rev-parse', 'HEAD']).decode().strip()
                == ref['automatic_source']['public_head'], 'SKU_AUTOMATIC_FROZEN_HEAD_CHANGED')
        require(subprocess.check_output(['git', '-C', str(FROZEN_AUTO), 'rev-parse', 'HEAD^{tree}']).decode().strip()
                == ref['automatic_source']['tree'], 'SKU_AUTOMATIC_FROZEN_TREE_CHANGED')
        require(not subprocess.check_output(['git', '-C', str(FROZEN_AUTO), 'status', '--porcelain', '--untracked-files=no']).strip(),
                'SKU_AUTOMATIC_FROZEN_SOURCE_DIRTY')

    def bridge_sources():
        require(admission.inputs(parent_raw, money_raw, plan_raw) == receipt and source_manifest() == own,
                'SKU_AUTOMATIC_PARENT_SOURCE_OR_PLAN_CHANGED')
        frozen()
        require(admission.pin(admission.canonical(money.sources())) == admission.CURRENT_MONEY_GRAPH_PIN,
                'SKU_AUTOMATIC_COMPLETE_CURRENT_MONEY_GRAPH_CHANGED')
        return dict(receipt=receipt, preparation_source=own, derivation=proof,
                    complete_current_parent_state_bound=True, actual_ERP_cases=0, production_go=False)

    bridge_sources()
    product = ModuleType('automatic_on_current_mandor_money')
    product.__file__ = str(expected / 'composition.py')
    product.__package__ = automatic_module.__package__
    product.__dict__.update(_CURRENT_MONEY_PARENT=money, _BRIDGE_SOURCES=bridge_sources)
    exec(compile(text, product.__file__ + '::current_money_parent', 'exec'), product.__dict__)
    return product
