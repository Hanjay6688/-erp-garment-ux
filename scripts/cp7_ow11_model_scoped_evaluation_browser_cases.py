"""Two actual Auth/browser scoped-model journeys; Native6 is separate evidence."""
from hashlib import sha256
from pathlib import Path
import cp7_ow11_model_scoped_evaluation_cases as native

CONTRACT = 'cp7.ow11.model-scoped-evaluation-browser.v1'
IDS = dict(browser=['OW11_SCOPED_MODEL_BROWSER_MOBILE_HISTORY_MODEL_EXACT_RECOVERY',
                    'OW11_SCOPED_MODEL_BROWSER_DESKTOP_BOUNDED_ENTRY_SOURCE_ACCESS'])
REQUIRED = dict(browser=2)
EXPECTED = DECLARED = 2
FUNCTIONS, SCHEDULES, stage = native.FUNCTIONS, native.SCHEDULES, native.stage
INSTALL_STATES, REORDER_STATES, CHECKED_STATE, SCHEDULE_STATE, BOUNDED_STATE, REFERENCE_STATE, STAGE_STATE = {}, {}, {}, {}, {}, {}, {}
PARENT_CHECKER = None


def sources():
    root = Path(__file__).resolve().parents[1]
    paths = [Path(__file__), Path(native.__file__), Path(native.parent.__file__)]
    paths += [Path(__file__).with_name('cp7_ow11_model_scoped_evaluation_browser' + suffix)
              for suffix in ('.mjs', '_probe.py', '_fixture.py')]
    paths += [root / 'src' / name for name in ('nativeScopedModel.ts', 'NativeScopedModelPanel.tsx',
              'NativeAnalysisPanel.tsx', 'NativeStagedAnalysisView.tsx')]
    return {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest() for p in paths}
