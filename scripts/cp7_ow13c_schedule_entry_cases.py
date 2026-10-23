"""Two real browser journeys for direct work entry; no repeated race/Auth group."""
import cp7_ow13c_schedule_transport_cases as transport
CONTRACT = 'cp7.ow13c.staged-schedule-direct-entry.v1'
IDS = dict(browser=['OW13C_SCHEDULE_ENTRY_DESKTOP_STALE_DIRTY', 'OW13C_SCHEDULE_ENTRY_MOBILE_LOST_REPLY'])
REQUIRED = dict(browser=2)
EXPECTED = DECLARED = 2
FUNCTIONS, SCHEDULES = transport.FUNCTIONS, transport.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE, SCHEDULE_STATE = {}, {}, {}, {}
