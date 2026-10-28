"""Two actual Auth/browser journeys under the versioned target overlay."""
from hashlib import sha256
from pathlib import Path
import cp7_ow11_model_target_consumer_v2_cases as native
CONTRACT='cp7.ow11.model-target-browser.v2'
IDS=dict(browser=['OW11_MODEL_TARGET_V2_BROWSER_MOBILE_UNKNOWN_ANALOG_CLEAR',
 'OW11_MODEL_TARGET_V2_BROWSER_DESKTOP_DENSE_PROVENANCE_RELOAD'])
REQUIRED=dict(browser=2)
EXPECTED=DECLARED=2
FUNCTIONS,SCHEDULES,stage=native.FUNCTIONS,native.SCHEDULES,native.stage
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None

def sources():
 root=Path(__file__).resolve().parents[1]
 paths=[Path(__file__),Path(__file__).with_name('cp7_ow11_model_target_v2_browser.mjs'),
  Path(__file__).with_name('cp7_ow11_model_target_v2_browser_probe.py')]
 paths += [root/'scripts'/name for name in ('cp7_ow11_consumer_browser_fixture.py',
  'cp7_ow11_analog_browser_fixture.py','cp7_ow11_model_scoped_evaluation_browser_fixture.py',
  'cp7_ow11_analog_browser.mjs')]
 paths += [root/'src'/name for name in ('nativeModelTarget.ts','nativeTargetDemand.ts',
  'TargetDemandDetails.tsx','nativeScopedModel.ts','NativeScopedModelPanel.tsx',
  'NativeProductAnalogPanel.tsx','NativeProductAnalogChoicePanel.tsx',
  'NativeBoundedQuantityPanel.tsx','NativeStagedAnalysisView.tsx','NativeAnalysisPanel.tsx')]
 return dict(native.sources(),**{str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest()for p in paths})
