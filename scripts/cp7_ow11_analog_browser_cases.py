"""Two actual browser/Auth flows; Native4 remains separate proof."""
import cp7_ow11_analog_reader_cases as reader
CONTRACT='cp7.ow11.analog-browser.v1'
IDS=dict(browser=['OW11_ANALOG_BROWSER_MOBILE_AVAILABLE_ZERO_SIZE_ACCESS',
                  'OW11_ANALOG_BROWSER_DESKTOP_DENSE_PAGES_RELOAD_K2'])
REQUIRED=dict(browser=2)
EXPECTED=DECLARED=2
FUNCTIONS=tuple(dict.fromkeys((*reader.FUNCTIONS,'erp_cp7_read_staged_analysis_pages_v1',
                              'erp_cp7_read_staged_analysis_page_v1','erp_cp7_check_staged_analysis_source_v1')))
SCHEDULES=reader.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE,ANALOG_STATE={},{},{},{},{},{},{},{}
