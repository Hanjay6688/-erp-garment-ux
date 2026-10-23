"""Two actual UI cases for the bounded paged quantity driver; no new race credit."""
import cp7_ow13c_bounded_stage_cases as bounded
CONTRACT='cp7.ow13c.bounded-quantity-browser.v1'
IDS=dict(browser=['OW13C_QUANTITY_MOBILE_CHECKED_SAVE_REPLY_RECOVERY','OW13C_QUANTITY_DESKTOP_DENSE2000_PAGED_FRESHNESS'])
REQUIRED=dict(browser=2)
EXPECTED=DECLARED=2
FUNCTIONS=tuple(dict.fromkeys((*bounded.FUNCTIONS,'erp_cp7_read_staged_analysis_pages_v1','erp_cp7_read_staged_analysis_page_v1',
                             'erp_cp7_check_staged_analysis_source_v1','erp_cp7_get_plan_options_v2','erp_cp7_read_plan_draft_v2')))
SCHEDULES=bounded.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
