"""Two real Auth/browser confirmation journeys; independent component budget."""
import cp7_ow11_analog_browser_cases as advisory
import cp7_ow11_analog_choice_cases as native
CONTRACT='cp7.ow11.analog-choice-browser.v1'
IDS=dict(browser=['OW11_CHOICE_BROWSER_MOBILE_LOSS_RELOAD_REPLAY_CLEAR',
                  'OW11_CHOICE_BROWSER_DESKTOP_DENSE_STALE_AND_REVOKED'])
REQUIRED=dict(browser=2)
EXPECTED=DECLARED=2
FUNCTIONS=tuple(dict.fromkeys((*advisory.FUNCTIONS,*native.FUNCTIONS)))
SCHEDULES=native.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None
stage=native.stage
