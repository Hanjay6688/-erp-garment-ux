"""Fresh browser2 copies inside the same owning Native25 recovery lifecycle."""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import json
import os

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('current_browser_copy_owning_entry', HERE / 'qualification.py')
entry = importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
IDS = ('SKU_CURRENT_MOVAVG_DESKTOP_REAL_AUTH_PAIR_VALUE_RECOVERY_INVERSE',
       'SKU_CURRENT_MOVAVG_MOBILE390_REAL_AUTH_PAIR_VALUE_GUARDS_INVERSE')
LABEL = 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_BROWSER2'


def require(value, message):
    if not value:
        raise ValueError(message)


def actual_inputs():
    originals = entry.actual_inputs()
    plan = json.loads(originals[2])
    require(plan.get('required_browser_case_ids') == list(IDS) and plan.get('fresh_real_Auth_browser_required') is True,
            'CURRENT_SKU_BROWSER_EXPLICIT_COMPLETE_PLAN_ADOPTION_REQUIRED')
    require(os.environ.get('GITHUB_REF') == entry.BRANCH, 'CURRENT_SKU_BROWSER_SINGLE_OWNING_BRANCH_REQUIRED')
    return originals


@contextmanager
def copy_scope(modes, product, state):
    originals = actual_inputs()
    require(Path(product.__file__).resolve() == entry.assembly.FROZEN_AUTO / 'scripts/cp7_sku_automatic_pending/composition.py',
            'CURRENT_SKU_BROWSER_COMPLETE_CURRENT_PRODUCT_REQUIRED')
    with entry.inherited_scope():
        parent = entry.load('current_browser_unchanged_accepted_Mandor_copy_authority',
                            entry.FROZEN_PARENT / 'scripts/current-mandor-shop-native-qualification/access_runtime.py')
        original = entry.FROZEN_PARENT / 'scripts/current-mandor-shop-native-qualification/AFUI15_PARENT_ROOT_ACTUAL_INTAKE.json'
        require(original.is_file() and not any(part.is_symlink() for part in (original, *original.parents)),
                'CURRENT_SKU_BROWSER_GENUINE_UPSTREAM_AFUI_ROOT_REQUIRED')
        afui_raw = original.read_bytes()
        parent.admission.parent(afui_raw)
        # The retained scope needs a genuine Afui Root for eligibility plus
        # runtime()/verify(). Preserve those exact interfaces honestly: it
        # verifies the complete current product and original current state.
        facade = SimpleNamespace(parent_raw=afui_raw, runtime=product.runtime, verify=product.verify)
        with parent.copy_scope(modes, facade, state) as copies:
            yield copies
        require(actual_inputs() == originals, 'CURRENT_SKU_BROWSER_ACTUAL_INPUTS_CHANGED')


def run(product, state, verify, report):
    actual_inputs()
    source = entry.load('current_browser_complete_journey_derivation', HERE / 'browser_prepare.py')
    text, proof = source.derive()
    require((HERE / 'browser.mjs').read_bytes() == text.encode(), 'CURRENT_SKU_EXACT_REAL_BROWSER_JOURNEYS_REQUIRED')
    modes = entry.load('current_browser_original_full_App_copy_host',
                       entry.FROZEN_AFUI / 'scripts/current-s03-sku-s05-composite-qualification/modes.py')
    require(modes.AUDITOR == entry.FROZEN_AFUI, 'CURRENT_SKU_BROWSER_EXACT_UNCHANGED_HOST_ROOT_REQUIRED')
    host = 'scripts/current-s03-sku-s05-composite-qualification/host.mjs'
    require((ROOT / host).read_bytes() == (entry.FROZEN_AFUI / host).read_bytes(),
            'CURRENT_SKU_BROWSER_NORMAL_FULL_APP_HOST_MUST_REMAIN_UNCHANGED')
    modes.AUDITOR = ROOT
    browser_gate = entry.load('current_browser_complete_current_original_gate', HERE / 'browser_gate.py')
    case_output = entry.complete_case_output()
    with copy_scope(modes, product, state) as copies, case_output.scope(modes, 'copies'):
        report['current_browser_copy_authority'] = copies
        report['current_browser_journey_derivation'] = proof
        actual = modes.run_browser(HERE / 'browser.mjs', verify, 'sku_current_money_automatic_browser2')
    helper = entry.report_io.complete_originals()
    target = ROOT / 'cp6-proof/t3' / (LABEL + '.json');target.parent.mkdir(parents=True, exist_ok=True)
    retained = helper.save_sorted(target, actual, 'CURRENT_SKU_FIRST_COMPLETE_BROWSER_ORIGINAL_CONFLICT')
    report['current_browser_original'] = retained
    gate = browser_gate.typed()[0](actual, IDS, mode='BROWSER')
    report['current_browser_gate'] = gate
    require(len(copies['actual_copy_admissions']) == 1 and all(
        row.get('all22_groups_equal_original_install') is True
        and row.get('product_state_modified') is False
        and row.get('Native_or_schema_or_RPC_permissions_changed') is False
        for row in copies['actual_copy_admissions']), 'CURRENT_SKU_ONE_REAL_BROWSER_COPY_WITH_UNCHANGED_CURRENT_AUTHORITY')
    reader = entry.load('current_browser_exact_original_protocol_reader',
                        ROOT / 'scripts/current-s03-sku-s05-composite-qualification/parents.py')
    source = actual['cases'][IDS[0]]['source_pins']['entire_current_source_admission']['complete_current_source_admission']
    report['current_browser_complete_evidence_gate'] = browser_gate.gate(
        reader, target.parent, actual, report, os.environ['GITHUB_SHA'], source)
    report.update(actual_browser_cases=2, real_Auth_browser_claim=True)
    return dict(original=actual, original_file=retained, gate=gate, copy_authority=copies)
