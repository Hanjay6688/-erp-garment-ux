"""Actual Auth/browser target provenance under the model-aware overlay."""
import cp7_ow11_model_target_consumer_cases as native
CONTRACT='cp7.ow11.model-target-browser.v1'
IDS=dict(browser=['OW11_MODEL_TARGET_BROWSER_MOBILE_UNKNOWN_ANALOG_CLEAR',
 'OW11_MODEL_TARGET_BROWSER_DESKTOP_DENSE_PROVENANCE_RELOAD'])
REQUIRED=dict(browser=2)
EXPECTED=DECLARED=2
FUNCTIONS=native.FUNCTIONS
SCHEDULES=native.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None
stage=native.stage
