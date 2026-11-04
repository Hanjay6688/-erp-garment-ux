"""Bind real browser prerequisites to the complete current product, unarmed.

Every Root/source/plan gate precedes Git, frozen sources and runtime imports.
The construction and full source admission run inside the retained DB/network
fence. Only an explicit fixture operation may subsequently open its fixed
disposable browser copy through the unchanged Native fixture main function.
"""
from contextlib import contextmanager
from pathlib import Path
from types import CodeType, ModuleType
import importlib.util
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


entry = load('current_browser_actual_owning_entry', HERE / 'qualification.py')
preflight = load('current_browser_complete_source_prerequisites', HERE / 'browser_preflight.py')
observer = load('current_browser_complete_economic_observer', HERE / 'browser_observer.py')
AFUI_HEAD = '92a376091a1d1ea9901648e614f3e5212677a81f'
AFUI_TREE = 'ef194e421402ae1e45625e2d57f58c848ef9e08f'


def require(value, message):
    if not value:
        raise ValueError(message)


@contextmanager
def scope():
    entry.actual_inputs()  # First action; no caller/source/Git inspection.
    require(os.environ.get('GITHUB_REF') == entry.BRANCH, 'CURRENT_SKU_BROWSER_SINGLE_OWNING_BRANCH_REQUIRED')
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    require(head == os.environ.get('GITHUB_SHA'), 'CURRENT_SKU_BROWSER_EXACT_OWNING_HEAD_REQUIRED')
    entry.frozen(entry.FROZEN_AFUI, AFUI_HEAD, AFUI_TREE)
    fence = entry.load('current_browser_original_source_DB_network_fence',
                       entry.FROZEN_AFUI / 'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    with entry.inherited_scope():
        with fence.fenced_source_read() as guard:
            engine = entry.runtime()
            with engine.inherited_admission.parent_scope():
                source = engine.admitted()
                current_fixture, fixture_proof = fixture(engine.product)
        require(not guard['attempts'] and not guard['network_nonGit_attempts'],
                'CURRENT_SKU_BROWSER_SOURCE_ATTEMPTED_DATABASE_OR_NETWORK')
        with engine.inherited_admission.parent_scope():
            yield engine, dict(status='COMPLETE_CURRENT_PRODUCT_SOURCE_ADMITTED_NOT_BROWSER_OR_FINANCIAL_ACCEPTANCE',
                               qualification_commit=head, complete_current_source_admission=source,
                               source_database_network_guard=guard, source_projected=False,
                               current_browser_fixture_binding=fixture_proof,
                               actual_ERP_cases=0, actual_Auth_HTTP_cases=0, actual_browser_cases=0), current_fixture


def derive_fixture(raw):
    require(entry.admission.pin(raw) == preflight.PINS['browser_fixture'], 'CURRENT_SKU_EXACT_COMPLETE_BROWSER_FIXTURE_REQUIRED')
    text = raw.decode()
    routes = (
        ("    blob=(json.dumps(raw,indent=2,sort_keys=True,default=str)+'\\n').encode()\n"
         "    output=Path('cp6-proof/t3')/(label+'_FULL_CURRENT_STATE.json');output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(blob)",
         "    output=Path('cp6-proof/t3')/(label+'_FULL_CURRENT_STATE.json');output.parent.mkdir(parents=True,exist_ok=True)\n"
         "    saved=_COMPLETE_IO.save_sorted(output.absolute(),raw,'CURRENT_SKU_COMPLETE_BROWSER_CENSUS_CONFLICT')"),
        ("raw_evidence=dict(path=str(output),bytes=len(blob),sha256=sha256(blob).hexdigest())",
         "raw_evidence=dict(path=str(output),bytes=saved['bytes'],sha256=saved['sha256'])"),
    )
    for before, after in routes:
        require(text.count(before) == 1 and after not in text, 'CURRENT_SKU_ONE_COMPLETE_CENSUS_OUTPUT_ROUTE_REQUIRED')
        text = text.replace(before, after, 1)
    recovered = text
    for before, after in reversed(routes):
        recovered = recovered.replace(after, before, 1)
    require(recovered.encode() == raw, 'CURRENT_SKU_COMPLETE_BROWSER_FIXTURE_NOT_RECOVERED')
    compile(text, 'current_complete_browser_fixture', 'exec', dont_inherit=True)
    return text, dict(retained=entry.admission.pin(raw), derived=entry.admission.pin(text.encode()),
                      complete_original_recovered=True, output_expression_routes=2,
                      Native_commands_and_all22_data_and_sequences_assertions_unchanged=True,
                      actual_browser_cases=0)


def pretty_originals(original):
    # The complete IO primitive normally uses compact sorted JSON. This old
    # browser census used indent=2; preserve that exact encoder contract while
    # retaining the original streamed writer, hashes and exclusive publication.
    def encoded(value):
        for part in json.JSONEncoder(indent=2, sort_keys=True, default=str).iterencode(value):
            yield part.encode('utf-8')
        yield b'\n'
    return entry.money_binding.private_module(original, dict(encoded=encoded))


def fixture(product):
    entry.actual_inputs()
    require(Path(product.__file__).resolve() == entry.assembly.FROZEN_AUTO / 'scripts/cp7_sku_automatic_pending/composition.py',
            'CURRENT_SKU_BROWSER_ACTUAL_COMPLETE_AUTOMATIC_PRODUCT_REQUIRED')
    deriver = load('current_browser_exact_frozen_fixture_deriver',
                   entry.FROZEN_SKU / 'scripts/current-sku-managed-recovery-native27-qualification/derive.py')
    raw, _ = deriver.derive('browser_fixture')
    text, proof = derive_fixture(raw.encode())
    module = ModuleType('current_SKU_complete_Native_browser_fixture')
    module.__file__ = str(entry.FROZEN_SKU / 'scripts/current-sku-managed-recovery-native27-qualification/browser_fixture.py')
    module._COMPLETE_IO = pretty_originals(entry.report_io.complete_originals())
    previous_path = list(sys.path)
    try:
        with arguments([]):
            exec(compile(text, module.__file__ + '::complete-current-census', 'exec', dont_inherit=True), module.__dict__)
    finally:
        sys.path[:] = previous_path
    native_text, _ = deriver.derive('fixture')
    require(entry.admission.pin(native_text.encode()) == preflight.PINS['fixture'], 'CURRENT_SKU_EXACT_REAL_NATIVE_FIXTURE_REQUIRED')
    filename = str(entry.FROZEN_SKU / deriver.SOURCES['fixture'][0])
    functions = {code.co_name: code for code in compile(native_text, filename, 'exec', dont_inherit=True).co_consts
                 if isinstance(code, CodeType)}
    for name, expected in functions.items():
        actual = getattr(module.f, name, None)
        require(callable(actual) and actual.__code__ == expected and actual.__globals__ is module.f.__dict__,
                'CURRENT_SKU_ACTUAL_UNCHANGED_NATIVE_FIXTURE_FUNCTION_REQUIRED:' + name)
    for name in ('be', 'bf'):
        helper = getattr(module.f, name)
        path = Path(helper.__file__).resolve()
        allowed = [root / 'scripts' / ('cp6_' + name + '_probe.py') for root in
                   (entry.FROZEN_AFUI, entry.FROZEN_PARENT, entry.FROZEN_SKU)]
        require(path in allowed and not any(part.is_symlink() for part in (path, *path.parents)),
                'CURRENT_SKU_REAL_FROZEN_NATIVE_HELPER_REQUIRED:' + name)
        require(path.read_bytes() == (entry.FROZEN_SKU / 'scripts' / path.name).read_bytes(),
                'CURRENT_SKU_NATIVE_HELPER_SOURCE_CHANGED:' + name)
    current = entry.money_binding.private_module(module, dict(product=product))
    original = current.observe
    current.observe = lambda cur, value, label: observer.observe(original, cur, value, label)
    require(current.main.__globals__ is current.__dict__ and current.census.__globals__ is current.__dict__,
            'CURRENT_SKU_BROWSER_MAIN_AND_FULL_CENSUS_CURRENT_PRODUCT_BINDING_REQUIRED')
    return current, dict(proof, actual_native_constructor=preflight.PINS['fixture'],
                         actual_Native_function_code_identities_checked=len(functions),
                         actual_current_product_bound=True, original_Native_helper_sources_checked=2,
                         import_path_and_operation_arguments_preserved=True,
                         sorted_pretty_complete_original_bytes_preserved=True)


@contextmanager
def arguments(values):
    original, contents = sys.argv, list(sys.argv)
    sys.argv = original[:1] + list(values)
    try:
        yield
    finally:
        original[:] = contents
        sys.argv = original
