"""Closed actual Auth cutting browser provider; default app remains unchanged."""
from hashlib import sha256
from pathlib import Path
import cp7_ow12b_frozen_cutting_cases as native
CONTRACT='cp7.ow12b.frozen-cutting-auth-browser2.v2'
IDS=dict(browser=['OW12B_FROZEN_CUTTING_AUTH_BROWSER_DESKTOP_SAVE_LOST_REPLY_REPLAY',
 'OW12B_FROZEN_CUTTING_AUTH_BROWSER_MOBILE_CURRENT_ACCESS_RETAINS_COMMAND'])
REQUIRED=dict(browser=2);EXPECTED=DECLARED=2
FUNCTIONS,SCHEDULES=native.FUNCTIONS,native.SCHEDULES
stage=native.facade.stage
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None
RUNTIME_PATHS=('scripts/cp7_frozen_quantity_ui/client/NativeFrozenProgress.tsx', 'scripts/cp7_frozen_quantity_ui/client/nativeFrozenProgress.ts', 'scripts/cp7_frozen_analysis_choice_v2/client/nativeFrozenChoice.ts', 'scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis.ts', 'scripts/cp7_frozen_analysis_readers_v2/client/nativeFrozenAnalog.ts', 'scripts/cp7_frozen_choice_ui/client/NativeFrozenAnalogPanel.tsx', 'scripts/cp7_frozen_choice_ui/client/NativeFrozenChoicePanel.tsx', 'scripts/cp7_frozen_choice_ui/client/frozen-choice.css', 'scripts/cp7_frozen_cutting_ui/client/NativeFrozenCuttingPanel.tsx', 'scripts/cp7_frozen_cutting_ui/client/frozen-cutting.css', 'scripts/cp7_frozen_quantity_ui/client/NativeFrozenQuantityPanel.tsx', 'scripts/cp7_frozen_quantity_ui/client/nativeFrozenQuantity.ts', 'src/NativePlanDraftPanel.tsx', 'src/ProductionRecoveryNotice.tsx', 'src/TargetDemandDetails.tsx', 'src/auth/AuthGate.tsx', 'src/auth/AuthProvider.tsx', 'src/auth/auth.css', 'src/auth/authPolicy.ts', 'src/config/runtime.ts', 'src/cp6BusinessTime.ts', 'src/cp7/fixture.ts', 'src/cp7/native-analysis.schema.json', 'src/cp7/reasons.json', 'src/cp7/workspace.ts', 'src/cuttingPersistence.ts', 'src/financeReportContract.ts', 'src/lib/analysisRetentionMessages.ts', 'src/lib/clientError.ts', 'src/lib/mandorCorrectionMessages.ts', 'src/lib/masterMessages.ts', 'src/lib/planV2Messages.ts', 'src/lib/receiptCorrectionMessages.ts', 'src/lib/reminderV2Messages.ts', 'src/lib/reportV2Messages.ts', 'src/lib/supabase.ts', 'src/native-bounded-quantity.css', 'src/native-plan-draft.css', 'src/native-production-planning.css', 'src/nativeAnalysis.ts', 'src/nativeAnalysisFinanceSidecar.ts', 'src/nativeAnalysisPages.ts', 'src/nativeAnalysisTransport.ts', 'src/nativeBoundedAnalysis.ts', 'src/nativeBoundedQuantity.ts', 'src/nativeCuttingSuggestion.ts', 'src/nativeHistoryYieldPolicy.ts', 'src/nativeModelPolicy.ts', 'src/nativeModelTarget.ts', 'src/nativePlanActual.ts', 'src/nativePlanDraft.ts', 'src/nativePlanInstant.ts', 'src/nativeProductAnalog.ts', 'src/nativeStagedJob.ts', 'src/nativeStagedPlan.ts', 'src/nativeTargetDemand.ts', 'src/procurementContract.ts', 'src/productionRecovery.ts', 'src/quantityInput.ts', 'src/styles.css', 'src/useProductionMutation.ts')

def sources():
 root=Path(__file__).resolve().parents[1]
 helpers=tuple('scripts/cp7_ow12b_frozen_cutting_auth_'+s for s in('cases.py','browser.mjs','build.mjs','fixture.py','probe.py','preflight.py'))
 host=('scripts/cp6_auditor_browser_host.mjs','scripts/cp6_auditor_modes.py','scripts/cp6_bb_probe.py','scripts/cp7_planning_schedule_cases.py','scripts/cp7_plan_native_cases.py')
 return {**native.sources(),**{p:sha256((root/p).read_bytes()).hexdigest()for p in(*helpers,*host,*RUNTIME_PATHS)}}
