#!/usr/bin/env python3
"""A bounded frontend writer successor; never an independent/global PASS."""
from pathlib import Path
import hashlib
import json
import subprocess
import re

BASE = '9f884fbb27bdb92d6ee63f60333e007dc36f3f1c'
BASE_TREE = 'b4cf1e5d6c8aff531470af01dcdb4d146b4fca7f'
BACKEND = '25fa4736329e5148dfdb3572bc169952cba23251'
BACKEND_TREE = 'a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d'
PIN_FILE = 'docs/evidence/cp6-disposable-ui-source-pins.json'
DOC = 'docs/cp6-disposable-ui-audit.md'
AUDIT_DOC = 'docs/cp6-final-successor-independent.md'
AK_DOC = 'docs/cp6-ak-import-repair.md'
AK_INDEPENDENT_DOC = 'docs/cp6-ak-independent-audit.md'
AL_DOC = 'docs/cp6-al-opening-values.md'
FRONTEND_DOC = 'docs/cp6-frontend-recovery.md'
PATHS = '''.github/workflows/cp6-ac-independent-audit.yml
.github/workflows/cp6-ad-roll-opening-check.yml
.github/workflows/cp6-ag-sale-reservation.yml
.github/workflows/cp6-ah-return-allocation.yml
.github/workflows/cp6-ai-work-source.yml
.github/workflows/cp6-final-boundary-audit.yml
.github/workflows/cp6-full-schema-validation.yml
docs/evidence/cp6-aj-ai-catalog-pins.json
docs/evidence/cp6-aj-predecessor-functions.json
docs/evidence/cp6-aj-runtime-pins.json
docs/evidence/cp6-ak-aj-catalog-pins.json
docs/evidence/cp6-ak-predecessor-functions.json
docs/evidence/cp6-ak-runtime-pins.json
docs/evidence/cp6-al-ak-catalog-pins.json
docs/evidence/cp6-al-predecessor-functions.json
docs/evidence/cp6-al-runtime-pins.json
docs/evidence/cp6-am-al-catalog-pins.json
docs/evidence/cp6-am-cli-provenance.json
docs/evidence/cp6-am-predecessor-functions.json
docs/evidence/cp6-am-runtime-pins.json
docs/evidence/cp6-claim-money-original-dom.json
docs/evidence/cp6-frontend-original-counterexamples.json
package.json
scripts/assert-cp6-disposable-env.mjs
scripts/build-preflight.mjs
scripts/check-access-catalog.mjs
scripts/check-cp5-boundary.mjs
scripts/check-cp6-boundary.mjs
scripts/check-cp6-deep-business-repair.mjs
scripts/check-cp6-expanded-audit-closure.mjs
scripts/check-production-recovery.mjs
scripts/cp6_disposable_ui_e2e.mjs
scripts/cp6_disposable_ui_scope.py
scripts/cp6_final_ak_independent.py
scripts/cp6_final_gap_midnight.py
scripts/cp6_final_gap_native.py
scripts/cp6_final_gap_ui.mjs
scripts/cp6_final_independent_acceptance.py
scripts/cp6_final_money_independent.mjs
scripts/cp6_foundation_qualification.py
scripts/cp6_frontend_recovery_fixture.py
scripts/cp6_frontend_recovery_ui.mjs
scripts/cp6_preuse_rollback_maintenance.py
scripts/cp6_v2620aj_build_sql.py
scripts/cp6_v2620aj_maintenance_schedules.py
scripts/cp6_v2620aj_review.py
scripts/cp6_v2620aj_runtime.py
scripts/cp6_v2620ak_advisors.py
scripts/cp6_v2620ak_build_sql.py
scripts/cp6_v2620ak_followup.py
scripts/cp6_v2620ak_import_concurrency.py
scripts/cp6_v2620ak_import_review.py
scripts/cp6_v2620ak_maintenance_schedules.py
scripts/cp6_v2620ak_review.py
scripts/cp6_v2620ak_runtime.py
scripts/cp6_v2620al_advisors.py
scripts/cp6_v2620al_build_sql.py
scripts/cp6_v2620al_direct_concurrency.py
scripts/cp6_v2620al_import_concurrency.py
scripts/cp6_v2620al_import_review.py
scripts/cp6_v2620al_maintenance_schedules.py
scripts/cp6_v2620al_review.py
scripts/cp6_v2620al_runtime.py
scripts/cp6_v2620al_value_review.py
scripts/cp6_v2620am_build_sql.py
scripts/cp6_v2620am_definitions.py
scripts/cp6_v2620am_runtime.py
scripts/cp6_v2620am_sql_trial.py
scripts/cp6_v2620am_review.py
scripts/cp6_v2620am_followup.py
scripts/cp6_v2620am_transfer_crossflow.py
scripts/cp6_v2620am_concurrency.py
scripts/cp6_v2620am_advisors.py
scripts/cp6_v2620am_maintenance_schedules.py
docs/evidence/cp6-am-regression-oracle-pins.json
src/AccessControlPage.tsx
src/ConnectedBsResolutionPage.dom.test.tsx
src/ConnectedBsResolutionPage.tsx
src/ConnectedCuttingPage.tsx
src/ConnectedLaundryPage.tsx
src/ConnectedLaundryQcSelectors.dom.test.tsx
src/ConnectedPatternFilter.tsx
src/ConnectedPickupPage.tsx
src/ConnectedProductionRecovery.dom.test.tsx
src/ConnectedQcFinalPage.tsx
src/ConnectedWipStatusPage.test.ts
src/ConnectedWipStatusPage.tsx
src/CuttingPatternPicker.tsx
src/PatternPage.tsx
src/ProductionRecoveryNotice.tsx
src/accessProductionControl.test.ts
src/auth/AuthGate.tsx
src/auth/AuthProvider.tsx
src/bsResolutionModel.test.ts
src/bsResolutionModel.ts
src/components/RuntimeIdentity.tsx
src/config/runtime.test.ts
src/config/runtime.ts
src/cuttingPersistence.ts
src/laundryQcModel.test.ts
src/laundryQcModel.ts
src/lib/clientError.test.ts
src/lib/clientError.ts
src/lib/supabase.ts
src/main.tsx
src/productionRecovery.test.ts
src/productionRecovery.ts
src/quantityInput.test.ts
src/quantityInput.ts
src/useLaundryQcWorkspace.ts
src/useProductionMutation.ts
src/vite-env.d.ts
supabase/migrations/20260916202400_erp_v2_6_20aj_cp6_rework_output_lineage.sql
supabase/migrations/20260917033516_erp_v2_6_20ak_cp6_import_reference_preview.sql
supabase/migrations/20260917054049_erp_v2_6_20al_cp6_opening_value_validation.sql
supabase/migrations/20260921214120_erp_v2_6_20am_cp6_transfer_integrity.sql
supabase/rollbacks/20260916202400_erp_v2_6_20aj_cp6_rework_output_lineage.rollback.sql
supabase/rollbacks/20260917033516_erp_v2_6_20ak_cp6_import_reference_preview.rollback.sql
supabase/rollbacks/20260917054049_erp_v2_6_20al_cp6_opening_value_validation.rollback.sql
supabase/rollbacks/20260921214120_erp_v2_6_20am_cp6_transfer_integrity.rollback.sql
tests/browser/cp5-bs-resolution.spec.ts
tests/browser/cp6-laundry-qc.spec.ts
tests/fixtures/productionRecovery.ts
docs/evidence/cp6-an-am-catalog-pins.json
docs/evidence/cp6-an-cli-provenance.json
docs/evidence/cp6-an-predecessor-functions.json
docs/evidence/cp6-an-runtime-pins.json
scripts/check-source-ownership.mjs
scripts/cp6_v2620an_advisors.py
scripts/cp6_v2620an_build_sql.py
scripts/cp6_v2620an_definitions.py
scripts/cp6_v2620an_gate.py
scripts/cp6_v2620an_maintenance_schedules.py
scripts/cp6_v2620an_review.py
scripts/cp6_v2620an_runtime.py
scripts/cp6_v2620an_selectors.py
scripts/cp6_v2620an_selectors_ui.mjs
scripts/cp6_v2620an_ui_fixture.py
src/cuttingSelectors.test.ts
src/cuttingSelectors.ts
src/types/database.preconnect.ts
supabase/migrations/20260921223438_erp_v2_6_20an_cp6_cutting_selectors.sql
supabase/rollbacks/20260921223438_erp_v2_6_20an_cp6_cutting_selectors.rollback.sql'''.splitlines()


def verify():
    git = lambda *args: subprocess.check_output(['git', *args], text=True).strip()
    assert git('rev-parse', BASE+'^{tree}') == BASE_TREE
    assert git('rev-parse', BACKEND+'^{tree}') == BACKEND_TREE
    assert git('merge-base', BASE, 'HEAD') == BASE
    assert not git('rev-list', '--merges', BASE+'..HEAD')
    assert not git('diff', '--name-only', 'HEAD'), 'Uncommitted tracked changes'
    changed = set(git('diff', '--name-only', BASE, 'HEAD').splitlines())
    assert changed == set(PATHS) | {PIN_FILE, DOC, AUDIT_DOC, AK_DOC, AK_INDEPENDENT_DOC, AL_DOC, FRONTEND_DOC}, sorted(changed)
    pins = json.loads(Path(PIN_FILE).read_text())
    assert pins['base'] == BASE and pins['backend'] == BACKEND
    assert set(pins['sha256']) == set(PATHS)
    for path, expected in pins['sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, path
    expected_sql = {
        'supabase/migrations/20260921223438_erp_v2_6_20an_cp6_cutting_selectors.sql',
        'supabase/rollbacks/20260921223438_erp_v2_6_20an_cp6_cutting_selectors.rollback.sql',
        'supabase/migrations/20260921214120_erp_v2_6_20am_cp6_transfer_integrity.sql',
        'supabase/rollbacks/20260921214120_erp_v2_6_20am_cp6_transfer_integrity.rollback.sql',
        'supabase/migrations/20260917054049_erp_v2_6_20al_cp6_opening_value_validation.sql',
        'supabase/rollbacks/20260917054049_erp_v2_6_20al_cp6_opening_value_validation.rollback.sql',
        'supabase/migrations/20260917033516_erp_v2_6_20ak_cp6_import_reference_preview.sql',
        'supabase/rollbacks/20260917033516_erp_v2_6_20ak_cp6_import_reference_preview.rollback.sql',

        'supabase/migrations/20260916202400_erp_v2_6_20aj_cp6_rework_output_lineage.sql',
        'supabase/rollbacks/20260916202400_erp_v2_6_20aj_cp6_rework_output_lineage.rollback.sql',
    }
    assert set(git('diff', '--name-only', BACKEND, 'HEAD', '--', 'supabase').splitlines()) == expected_sql
    assert not git('diff', '--name-only', '--diff-filter=MDRTCUXB', BACKEND, 'HEAD', '--', 'supabase')
    aj = json.loads(Path('docs/evidence/cp6-aj-runtime-pins.json').read_text())
    assert aj['predecessor_head'] == BACKEND and len(aj['functions']) == 6
    for path, expected in aj['source_pins'].items():
        raw = Path(path).read_bytes()
        assert len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256'], path
    # No admitted migration/rollback or original AK oracle can drift in AL.
    predecessor = '8c1a22b8fba26c1ee820645cf5793f19353522b8'
    assert not git('diff', '--name-only', '--diff-filter=MDRTCUXB', predecessor, 'HEAD', '--', 'supabase')
    original_oracle = 'scripts/cp6_final_ak_independent.py'
    assert Path(original_oracle).read_bytes() == subprocess.check_output(['git', 'show', predecessor+':'+original_oracle])
    al = json.loads(Path('docs/evidence/cp6-al-runtime-pins.json').read_text())
    assert al['predecessor_head'] == '684b708dee785934fe5fe4fe567c454cba873ea9' and len(al['functions']) == 2
    for path, expected in al['source_pins'].items():
        raw = Path(path).read_bytes()
        assert len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256'], path
    am=json.loads(Path('docs/evidence/cp6-am-runtime-pins.json').read_text())
    assert am['predecessor_head']=='4e74e25270c6a062d98e1adaa58cf50ea22e2e8c' and len(am['functions'])==6
    for path,expected in am['source_pins'].items():
        raw=Path(path).read_bytes()
        assert len(raw)==expected['bytes'] and hashlib.sha256(raw).hexdigest()==expected['sha256'],path
    an=json.loads(Path('docs/evidence/cp6-an-runtime-pins.json').read_text())
    assert an['predecessor_head']=='bf05659d4f8e99d0332215772d658417e4233cc8' and len(an['new_functions'])==2
    assert len(an['functions'])==1 and an['functions'][0]['predecessor_sha256']==an['functions'][0]['installed_sha256']
    for path,expected in an['source_pins'].items():
        raw=Path(path).read_bytes()
        assert len(raw)==expected['bytes'] and hashlib.sha256(raw).hexdigest()==expected['sha256'],path
    # Preserve the validation bodies; only routing to the dedicated combined gate changes.
    full = '.github/workflows/cp6-full-schema-validation.yml'
    route = '''          if python scripts/cp6_disposable_ui_scope.py; then
            echo 'full=false' >> "$GITHUB_OUTPUT"
          else
            python scripts/cp6_ai_audit_router.py
          fi
'''
    text = Path(full).read_text()
    assert text.count(route) == 1
    assert text.replace(route, '          python scripts/cp6_ai_audit_router.py\n') == subprocess.check_output(['git','show',BASE+':'+full],text=True)
    ad = '.github/workflows/cp6-ad-roll-opening-check.yml'
    route = ' || python scripts/cp6_disposable_ui_scope.py; then\n'
    text = Path(ad).read_text()
    assert text.count(route) == 1
    assert text.replace(route, '; then\n') == subprocess.check_output(['git','show',BASE+':'+ad],text=True)
    for name in ('cp6-ac-independent-audit.yml', 'cp6-ai-work-source.yml', 'cp6-ag-sale-reservation.yml', 'cp6-ah-return-allocation.yml'):
        path = '.github/workflows/' + name
        text = Path(path).read_text()
        if name in ('cp6-ag-sale-reservation.yml', 'cp6-ah-return-allocation.yml'):
            text = text.replace(' || python scripts/cp6_disposable_ui_scope.py; then', '; then')
        else:
            text, count = re.subn(r'(?m)^([ ]*)# BEGIN AJ QUALIFIED ROUTE\n.*?^[ ]*# END AJ QUALIFIED ROUTE\n', '', text, flags=re.S)
            assert count == 1
            if name == 'cp6-ai-work-source.yml':
                text = text.replace("    needs: review-scope\n    if: needs.review-scope.outputs.aj != 'true'\n", '')
        assert text == subprocess.check_output(['git','show',BASE+':'+path],text=True), path
    return dict(status='ROUTED_TO_EXPLICIT_AM_OR_AN_FAMILY_GATE',base_backend_head=BACKEND,
                base_backend_tree=BACKEND_TREE,backend_generation='AN_CANDIDATE',backend_head=git('rev-parse','HEAD'),frontend_head=git('rev-parse','HEAD'),
                frontend_tree=git('rev-parse','HEAD^{tree}'),
                historical_460_matrix_reexecuted=False,independent_acceptance=False,
                production_go=False)


if __name__ == '__main__':
    print(json.dumps(verify()))
