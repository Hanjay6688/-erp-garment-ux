"""Bind the exact closed money bridge privately to a genuine Mandor Root.

The retained ten gates and preparation manifest remain unchanged. Their
admission functions execute with a private globals dictionary; the source
manifest provider independently verifies the original closed source plus the
actual pinned Root/source bytes. No transaction, SQL or inverse is rewritten.
"""
from pathlib import Path
from types import CellType, FunctionType, ModuleType
import ast
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
cumulative_parent = load('automatic_cumulative_parent_source', HERE / 'cumulative_parent.py')
RETAINED_ADMISSION_PIN = dict(bytes=5388, sha256='ebd1c9eeda7c37012191468c841ffe1d4d162f7ef659bf11fbbc3359819d6d82')


def private_module(original, replacements):
    """Keep code/metadata; rebind source globals and decorated function cells."""
    private = ModuleType(original.__name__ + '_private_actual_parent')
    private.__dict__.update(original.__dict__)
    def clone(value, namespace, closure):
        copied = FunctionType(value.__code__, namespace, value.__name__, value.__defaults__, closure)
        copied.__kwdefaults__ = value.__kwdefaults__
        copied.__annotations__ = dict(value.__annotations__)
        copied.__dict__.update(value.__dict__)
        copied.__qualname__ = value.__qualname__
        copied.__module__ = value.__module__
        copied.__doc__ = value.__doc__
        return copied

    for name, value in original.__dict__.items():
        if name in replacements or not isinstance(value, FunctionType):
            continue
        if value.__globals__ is original.__dict__:
            private.__dict__[name] = clone(value, private.__dict__, value.__closure__)
            continue
        wrapped = getattr(value, '__wrapped__', None)
        if isinstance(wrapped, FunctionType) and wrapped.__globals__ is original.__dict__:
            # contextmanager's wrapper lives in contextlib; its sole function
            # cell must follow the rebound generator, rather than old globals.
            rebound = clone(wrapped, private.__dict__, wrapped.__closure__)
            cells = tuple(CellType(rebound) if cell.cell_contents is wrapped else cell
                          for cell in value.__closure__ or ())
            if not any(cell.cell_contents is wrapped for cell in value.__closure__ or ()):
                raise ValueError('PRIVATE_MODULE_DECORATOR_FUNCTION_CELL_REQUIRED')
            copied = clone(value, value.__globals__, cells)
            copied.__wrapped__ = rebound
            private.__dict__[name] = copied
    private.__dict__.update(replacements)
    return private


def exact_inputs(parent_raw, money_raw, plan_raw):
    admission.require_ready()  # Before reading any caller, file, Git or ERP.
    assembly.require(admission.OWNING_RUNTIME_ENTRY == ENTRY, 'SKU_AUTOMATIC_EXACT_OWNING_ENTRY_REQUIRED')
    return admission.inputs(parent_raw, money_raw, plan_raw)


def _private_admission(original, bindings, parent_raw, *, cumulative_source_only):
    gates = private_module(original, bindings)
    if not cumulative_source_only:
        return gates

    root = cumulative_parent.verify(parent_raw)
    path = Path(original.__file__)
    raw = path.read_bytes()
    assembly.require(admission.pin(raw) == RETAINED_ADMISSION_PIN,
                     'SKU_AUTOMATIC_EXACT_RETAINED_ADMISSION_FOR_CUMULATIVE_SOURCE_REQUIRED')
    # Replace just the parent contract in the private copy of the pinned
    # function. Money, file pins and source fence still use the retained checks.
    function = next(node for node in ast.parse(raw).body
                    if isinstance(node, ast.FunctionDef) and node.name == 'admitted')
    assignment, = [node for node in function.body if isinstance(node, ast.Assign)
                   and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                   and node.targets[0].id == 'expected_parent']
    assignment.value = ast.Name(id='_reviewed_cumulative_parent_fields', ctx=ast.Load())
    gates._reviewed_cumulative_parent_fields = cumulative_parent.expected_parent(root)
    isolated = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    exec(compile(isolated, str(path) + '::cumulative_source_only', 'exec'), gates.__dict__)
    return gates


def _private_bridge(parent_raw, money_raw, unchanged, *, cumulative_source_only=False):
    # The financial entry supplies its complete five-gate validation. The
    # source-only observer instead supplies its exact, separately reviewed
    # Root/source pins while its database/network fence is already active.
    unchanged()
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
    gates = _private_admission(original.admission, bindings, parent_raw,
                               cumulative_source_only=cumulative_source_only)
    admitted = gates.admitted(parent_raw, money_raw, reference['native_case_ids'])

    def source_manifest():
        # Verify the old manifest as the closed preparation it actually is.
        # The separate actual binding never changes the historical manifest.
        retained = original.source_manifest()
        unchanged()
        assembly.require(gates.admitted(parent_raw, money_raw, reference['native_case_ids']) == admitted,
                         'SKU_AUTOMATIC_ACTUAL_PRIVATE_PARENT_BINDING_CHANGED')
        return admission.pin(admission.canonical(dict(retained_closed_preparation=retained,
                    private_actual_parent_bindings=bindings, actual_parent_admission=admitted)))

    bridge = private_module(original, dict(admission=gates, source_manifest=source_manifest))
    proof = dict(classification='EXACT_PRIVATE_SOURCE_BINDING_NOT_FINANCIAL_ACCEPTANCE',
                 retained_closed_source=original.source_manifest(), private_bound_source=source_manifest(),
                 private_gate_names=list(original.admission.GATES),
                 complete_original_function_code_preserved=not cumulative_source_only,
                 retained_module_globals_unchanged=True,
                 actual_ERP_cases=0, production_go=False)
    return bridge, proof


def bind(parent_raw, money_raw, plan_raw):
    receipt = exact_inputs(parent_raw, money_raw, plan_raw)
    cumulative = json.loads(parent_raw).get('status') == cumulative_parent.STATUS
    reviewed = None
    if cumulative:
        adopter = load('automatic_cumulative_actual_adoption', HERE / 'cumulative_runtime.py')
        reviewed = adopter.validate_actual(admission, parent_raw, money_raw, plan_raw)

    def unchanged():
        assembly.require(exact_inputs(parent_raw, money_raw, plan_raw) == receipt,
                         'SKU_AUTOMATIC_ACTUAL_PRIVATE_INPUTS_CHANGED')
        if cumulative:
            assembly.require(adopter.validate_actual(admission, parent_raw, money_raw, plan_raw) == reviewed,
                             'SKU_CUMULATIVE_QUALIFICATION_DECISION_CHANGED')

    # The private money source graph preserves the historical source-only
    # parent contract. Only the separately replayed owning decision permits
    # this financial entry; the historical Root alone still cannot do so.
    bridge, proof = _private_bridge(parent_raw, money_raw, unchanged,
                                    cumulative_source_only=cumulative)
    if cumulative:
        proof['owning_cumulative_qualification_decision'] = reviewed
    return bridge, proof
