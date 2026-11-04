"""Bind the exact closed money bridge privately to a genuine Mandor Root.

The retained ten gates and preparation manifest remain unchanged. Their
admission functions execute with a private globals dictionary; the source
manifest provider independently verifies the original closed source plus the
actual pinned Root/source bytes. No transaction, SQL or inverse is rewritten.
"""
from pathlib import Path
from types import FunctionType, ModuleType
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ENTRY = 'scripts/current-sku-automatic-composite-preparation/qualification.py'
PRIOR = ROOT / 'scripts/current-sku-money-composite-preparation/assembly.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


assembly = load('automatic_private_money_binding_source', HERE / 'assembly.py')
admission = assembly.admission


def private_module(original, replacements):
    """Keep complete code objects, defaults, closures and source filenames."""
    private = ModuleType(original.__name__ + '_private_actual_parent')
    private.__dict__.update(original.__dict__)
    for name, value in original.__dict__.items():
        if name in replacements or not isinstance(value, FunctionType) or value.__globals__ is not original.__dict__:
            continue
        cloned = FunctionType(value.__code__, private.__dict__, value.__name__, value.__defaults__, value.__closure__)
        cloned.__kwdefaults__ = value.__kwdefaults__
        cloned.__annotations__ = dict(value.__annotations__)
        cloned.__dict__.update(value.__dict__)
        private.__dict__[name] = cloned
    private.__dict__.update(replacements)
    return private


def exact_inputs(parent_raw, money_raw, plan_raw):
    admission.require_ready()  # Before reading any caller, file, Git or ERP.
    assembly.require(admission.OWNING_RUNTIME_ENTRY == ENTRY, 'SKU_AUTOMATIC_EXACT_OWNING_ENTRY_REQUIRED')
    return admission.inputs(parent_raw, money_raw, plan_raw)


def bind(parent_raw, money_raw, plan_raw):
    receipt = exact_inputs(parent_raw, money_raw, plan_raw)
    original = load('automatic_exact_unchanged_money_bridge', PRIOR)
    original.source_manifest()
    assembly.require(all(getattr(original.admission, name) is None for name in original.admission.GATES),
                     'SKU_AUTOMATIC_RETAINED_MONEY_GATES_MUST_REMAIN_CLOSED')
    root, source = json.loads(parent_raw), json.loads(money_raw)
    reference, *_ = original.prepared_sources()
    bindings = dict(PARENT_HEAD=root['head'], PARENT_TREE=root['tree'],
                    PARENT_ROOT_PIN=admission.pin(parent_raw),
                    PARENT_SOURCE_PIN=admission.pin(admission.canonical(root['qualified_current_Mandor_sources'])),
                    PARENT_MODULE_PIN=root['assembly_source'], SKU_HEAD=reference['candidate_head'],
                    SKU_TREE=reference['candidate_tree'], SKU_SOURCE_PREFLIGHT_PIN=admission.pin(money_raw),
                    SKU_SOURCE_PIN=admission.pin(admission.canonical(source['complete_candidate_source_admission']['current_installation'])),
                    RUNTIME_ENTRY=ENTRY)
    assembly.require(set(bindings) == set(original.admission.GATES), 'SKU_AUTOMATIC_EXACT_TEN_PRIVATE_BINDINGS')
    gates = private_module(original.admission, bindings)
    admitted = gates.admitted(parent_raw, money_raw, reference['native_case_ids'])

    def source_manifest():
        # Verify the old manifest as the closed preparation it actually is.
        # The separate actual binding never changes the historical manifest.
        retained = original.source_manifest()
        assembly.require(exact_inputs(parent_raw, money_raw, plan_raw) == receipt
                         and gates.admitted(parent_raw, money_raw, reference['native_case_ids']) == admitted,
                         'SKU_AUTOMATIC_ACTUAL_PRIVATE_PARENT_BINDING_CHANGED')
        return admission.pin(admission.canonical(dict(retained_closed_preparation=retained,
                    private_actual_parent_bindings=bindings, actual_parent_admission=admitted)))

    bridge = private_module(original, dict(admission=gates, source_manifest=source_manifest))
    proof = dict(classification='EXACT_PRIVATE_SOURCE_BINDING_NOT_FINANCIAL_ACCEPTANCE',
                 retained_closed_source=original.source_manifest(), private_bound_source=source_manifest(),
                 private_gate_names=list(original.admission.GATES),
                 complete_original_function_code_preserved=True, retained_module_globals_unchanged=True,
                 actual_ERP_cases=0, production_go=False)
    return bridge, proof
