"""Actual Auth v2 browser proof; no fabricated historical model winner."""
import cp7_ow11_model_evaluation_v2_cases as native
CONTRACT='cp7.ow11.model-evaluation-v2-browser.v1'
IDS=dict(browser=['OW11_MODEL_V2_BROWSER_MOBILE_EXACT_RECOVERY_POLICY_SOURCE',
 'OW11_MODEL_V2_BROWSER_DESKTOP_BASELINE_CURRENT_ACCESS'])
REQUIRED=dict(browser=2)
EXPECTED=DECLARED=2
FUNCTIONS,SCHEDULES=native.FUNCTIONS,native.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None
stage=native.stage
