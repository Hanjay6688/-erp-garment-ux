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
PAIR_CENSUS_TABLES = tuple('cp7_sku_conversion.' + name for name in
                          ('pairs_v1', 'pair_events_v1', 'groups_v1', 'members_v1', 'execution_v1'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


entry = load('current_browser_actual_owning_entry', HERE / 'qualification.py')
preflight = load('current_browser_complete_source_prerequisites', HERE / 'browser_preflight.py')
observer = load('current_browser_complete_economic_observer', HERE / 'browser_observer.py')


def require(value, message):
    if not value:
        raise ValueError(message)


@contextmanager
def scope():
    entry.actual_inputs()  # First action; no caller/source/Git inspection.
    require(os.environ.get('GITHUB_REF') == entry.BRANCH, 'CURRENT_SKU_BROWSER_SINGLE_OWNING_BRANCH_REQUIRED')
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    require(head == os.environ.get('GITHUB_SHA'), 'CURRENT_SKU_BROWSER_EXACT_OWNING_HEAD_REQUIRED')
    entry.frozen_afui()
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
         "    output=Path('cp6-proof/t3')/(label+'_FULL_CURRENT_STATE.json')\n"
         "    target=_BROWSER_PROOF_ROOT/output;target.parent.mkdir(parents=True,exist_ok=True)\n"
         "    saved=_COMPLETE_IO.save_sorted(target,raw,'CURRENT_SKU_COMPLETE_BROWSER_CENSUS_CONFLICT')"),
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


def derive_census(text):
    before = "    assert len(rows)==22 and all(table in data for table in product.TABLES),'SKU29_FULL_CURRENT_CENSUS_REQUIRED'"
    after = '    _BROWSER_REQUIRE_COMPLETE_CENSUS(rows, data)'
    require(text.count(before) == 1 and after not in text, 'CURRENT_SKU_EXACT_CENSUS_PRODUCT_TABLES_ROUTE_REQUIRED')
    revised = text.replace(before, after, 1)
    require(revised.count(after) == 1 and revised.replace(after, before, 1) == text,
            'CURRENT_SKU_EXACT_CENSUS_ASSERTION_INVERSE_REQUIRED')
    compile(revised, 'current_complete_browser_census', 'exec', dont_inherit=True)
    return revised, dict(retained=entry.admission.pin(text.encode()), derived=entry.admission.pin(revised.encode()),
                         exact_assertion_routes=1, previous_source_recovered=True,
                         pair_product_table_scope=PAIR_CENSUS_TABLES,
                         current_data_and_sequences_closed_over_actual_catalogue=True)


def require_complete_census(rows, data, pair_tables):
    require(len(rows) == 22 and type(rows.get('relations')) is dict,
            'SKU29_FULL_CURRENT_CENSUS_REQUIRED')
    relations = rows['relations']
    tables = {name for name, row in relations.items() if row[1] in ('r', 'p', 'm')}
    sequences = {'sequence:' + name for name, row in relations.items() if row[1] == 'S'}
    require(tuple(pair_tables) == PAIR_CENSUS_TABLES and set(pair_tables) <= tables
            and set(data) == tables | sequences, 'SKU29_FULL_CURRENT_CENSUS_REQUIRED')


def pretty_originals(original):
    # The complete IO primitive normally uses compact sorted JSON. This old
    # browser census used indent=2; preserve that exact encoder contract while
    # retaining the original streamed writer, hashes and exclusive publication.
    def encoded(value):
        for part in json.JSONEncoder(indent=2, sort_keys=True, default=str).iterencode(value):
            yield part.encode('utf-8')
        yield b'\n'
    return entry.money_binding.private_module(original, dict(encoded=encoded))


def fixture_sources():
    # The browser contract pins the unchanged one-location Native constructor.
    # The money checkout has a different, location-aware constructor for its
    # own cases. Keep that source intact and use the exact browser donor tree.
    root = entry.FROZEN_PARENT
    deriver = load('current_browser_exact_frozen_fixture_deriver',
                   root / 'scripts/current-sku-managed-recovery-native27-qualification/derive.py')
    raw, _ = deriver.derive('browser_fixture')
    native_text, _ = deriver.derive('fixture')
    require(entry.admission.pin(raw.encode()) == preflight.PINS['browser_fixture'],
            'CURRENT_SKU_EXACT_COMPLETE_BROWSER_FIXTURE_REQUIRED')
    require(entry.admission.pin(native_text.encode()) == preflight.PINS['fixture'],
            'CURRENT_SKU_EXACT_REAL_NATIVE_FIXTURE_REQUIRED')
    return root, deriver, raw, native_text


def native_helper_origin(helper, name):
    require(name in ('be', 'bf'), 'CURRENT_SKU_EXACT_NATIVE_HELPER_NAME_REQUIRED')
    path = Path(helper.__file__).resolve()
    legacy = ROOT.parent / 'qualified-sku090b'
    allowed = [root / 'scripts' / ('cp6_' + name + '_probe.py') for root in
               (entry.FROZEN_AFUI, entry.FROZEN_PARENT, entry.FROZEN_SKU, legacy)]
    require(path in allowed and not any(part.is_symlink() for part in (path, *path.parents)),
            'CURRENT_SKU_REAL_FROZEN_NATIVE_HELPER_REQUIRED:' + name + ':' + str(path))
    legacy_proof = None
    if path == legacy / 'scripts' / path.name:
        # Full product import legitimately loads these shared helpers from the
        # already-qualified SKU090b ancestor. Recheck that exact ancestor with
        # its retained physical guard, rather than replacing a live module.
        original = entry.load('current_browser_exact_qualified_SKU_ancestor',
                              entry.FROZEN_AFUI / 'scripts/current-final-s03-sku-s05-preparation/frozen_parent.py')
        legacy_proof = original.admitted()
        require(Path(legacy_proof['path']) == legacy, 'CURRENT_SKU_EXACT_HELPER_ANCESTOR_REQUIRED')
    require(path.read_bytes() == (entry.FROZEN_SKU / 'scripts' / path.name).read_bytes(),
            'CURRENT_SKU_NATIVE_HELPER_SOURCE_CHANGED:' + name)
    return dict(path=str(path), identical_current_money_helper=True,
                actual_qualified_ancestor=legacy_proof)


def fixture(product):
    entry.actual_inputs()
    require(Path(product.__file__).resolve() == entry.assembly.FROZEN_AUTO / 'scripts/cp7_sku_automatic_pending/composition.py',
            'CURRENT_SKU_BROWSER_ACTUAL_COMPLETE_AUTOMATIC_PRODUCT_REQUIRED')
    root, deriver, raw, native_text = fixture_sources()
    text, proof = derive_fixture(raw.encode())
    text, census_proof = derive_census(text)
    module = ModuleType('current_SKU_complete_Native_browser_fixture')
    module.__file__ = str(root / 'scripts/current-sku-managed-recovery-native27-qualification/browser_fixture.py')
    module._COMPLETE_IO = pretty_originals(entry.report_io.complete_originals())
    previous_path = list(sys.path)
    try:
        with arguments([]):
            exec(compile(text, module.__file__ + '::complete-current-census', 'exec', dont_inherit=True), module.__dict__)
    finally:
        sys.path[:] = previous_path
    filename = str(root / deriver.SOURCES['fixture'][0])
    functions = {code.co_name: code for code in compile(native_text, filename, 'exec', dont_inherit=True).co_consts
                 if isinstance(code, CodeType)}
    for name, expected in functions.items():
        actual = getattr(module.f, name, None)
        require(callable(actual) and actual.__code__ == expected and actual.__globals__ is module.f.__dict__,
                'CURRENT_SKU_ACTUAL_UNCHANGED_NATIVE_FIXTURE_FUNCTION_REQUIRED:' + name)
    helpers = {name: native_helper_origin(getattr(module.f, name), name) for name in ('be', 'bf')}
    pair_tables = module.product.TABLES
    require(type(pair_tables) is tuple and pair_tables == PAIR_CENSUS_TABLES,
            'CURRENT_SKU_EXACT_RETAINED_PAIR_CENSUS_TABLES_REQUIRED')
    # The complete current product supplies the readers. The original pair
    # product supplies its table contract, including execution history.
    def require_census(rows, data):
        require_complete_census(rows, data, pair_tables)
    # The fixture process runs from writer, but the browser gate and upload own auditor's proof directory.
    current = entry.money_binding.private_module(module, dict(product=product, _BROWSER_PROOF_ROOT=ROOT,
                                                              _BROWSER_REQUIRE_COMPLETE_CENSUS=require_census))
    original = current.observe
    current.observe = lambda cur, value, label: observer.observe(original, cur, value, label)
    require(current.main.__globals__ is current.__dict__ and current.census.__globals__ is current.__dict__,
            'CURRENT_SKU_BROWSER_MAIN_AND_FULL_CENSUS_CURRENT_PRODUCT_BINDING_REQUIRED')
    return current, dict(proof, complete_current_census_route=census_proof, actual_native_constructor=preflight.PINS['fixture'],
                         exact_browser_constructor_checkout='qualified-mandor-parent',
                         money_location_aware_constructor_unchanged=True,
                         actual_Native_function_code_identities_checked=len(functions),
                         actual_current_product_bound=True, original_Native_helper_sources_checked=2,
                         actual_Native_helper_origins=helpers,
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
