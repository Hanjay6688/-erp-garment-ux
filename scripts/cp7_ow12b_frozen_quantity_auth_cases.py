"""Two real Auth/browser journeys of the explicit prepared frozen quantity UI."""
from hashlib import sha256
from pathlib import Path
import cp7_ow12b_frozen_choice_cases as native
import cp7_ow12b_frozen_facade_cases as facade
CONTRACT='cp7.ow12b.frozen-quantity-auth-browser2.v2'
IDS=dict(browser=['OW12B_FROZEN_QUANTITY_AUTH_BROWSER_DESKTOP_DONE_RECOVERY_ANALOG','OW12B_FROZEN_QUANTITY_AUTH_BROWSER_MOBILE_STALE_CURRENT_ACCESS'])
REQUIRED=dict(browser=2);EXPECTED=DECLARED=2
FUNCTIONS=(*native.FUNCTIONS,facade.REQUEST)
SCHEDULES,stage=native.SCHEDULES,native.stage
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None

def sources():
 root=Path(__file__).resolve().parents[1]
 paths=[root/'scripts'/('cp7_ow12b_frozen_quantity_auth_'+suffix)for suffix in('cases.py','browser.mjs','build.mjs','fixture.py','probe.py','preflight.py')]
 paths+=list((root/'scripts/cp7_frozen_choice_ui/client').glob('*.tsx'))
 paths+=list((root/'scripts/cp7_frozen_quantity_ui/client').glob('*.tsx'))
 paths+=list((root/'scripts/cp7_frozen_quantity_ui/client').glob('*.ts'))
 paths+=[root/'scripts/cp7_frozen_quantity_ui/client/nativeFrozenQuantity.ts',root/'src/native-bounded-quantity.css']
 paths+=[root/p for p in ('scripts/cp6_auditor_browser_host.mjs','scripts/cp6_auditor_modes.py','scripts/cp7_frozen_analysis_choice_v2/client/nativeFrozenChoice.ts','scripts/cp7_frozen_choice_ui/client/frozen-choice.css','scripts/cp6_bb_probe.py','scripts/cp7_planning_schedule_cases.py','scripts/cp7_plan_native_cases.py','scripts/cp7_frozen_analysis_facade_v2/client/nativeFrozenAnalysis.ts','scripts/cp7_frozen_analysis_readers_v2/client/nativeFrozenAnalog.ts','src/auth/AuthProvider.tsx','src/auth/AuthGate.tsx','src/auth/authPolicy.ts','src/auth/auth.css','src/lib/supabase.ts','src/config/runtime.ts','src/styles.css','src/native-production-planning.css','src/nativeProductionPlanning.ts','src/lib/clientError.ts')]
 return {**native.sources(),**facade.sources(),**{str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest()for p in paths}}
