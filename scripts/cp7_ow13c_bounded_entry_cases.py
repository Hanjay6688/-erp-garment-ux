"""Two actual bounded-entry browser journeys; Native6 remains separate proof."""
import cp7_ow13c_bounded_stage_cases as bounded
CONTRACT='cp7.ow13c.bounded-staged-entry.v1'
IDS=dict(browser=['OW13C_BOUNDED_ENTRY_DESKTOP_STALE_DIRTY','OW13C_BOUNDED_ENTRY_MOBILE_LOST_REPLY'])
REQUIRED=dict(browser=2)
EXPECTED=DECLARED=2
FUNCTIONS,SCHEDULES=bounded.FUNCTIONS,bounded.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
