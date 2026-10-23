"""Retain Native25 exactly and add four checked-save races/two browser journeys.

This is a separate immutable case budget. Native25's retained OW10 controls
are never relabelled as checked-save controls.
"""
import cp7_ow13c_checked_cases as base
import cp7_ow13c_checked_race_cases as concurrent

CONTRACT = 'cp7.ow13c.checked-save-journeys.v1'
IDS = {k: list(v) for k, v in base.IDS.items()}
IDS['races'] += concurrent.IDS
IDS['browser'] += ['OW13C_BROWSER_DESKTOP_EDIT_AND_STALE_REFUSAL',
                   'OW13C_BROWSER_MOBILE_LOST_REPLY_ORDINARY_PLAN_REOPEN']
REQUIRED = {k: len(v) for k, v in IDS.items()}
EXPECTED = DECLARED = sum(REQUIRED.values())
assert REQUIRED == dict(native=15, races=8, http=4, browser=4) and EXPECTED == 31
FUNCTIONS, SCHEDULES = base.FUNCTIONS, base.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE = {}, {}, {}


def cases(cur, today):
    base.INSTALL_STATES, base.REORDER_STATES, base.CHECKED_STATE = INSTALL_STATES, REORDER_STATES, CHECKED_STATE
    return base.cases(cur, today)


def races(tools, today):
    return base.races(tools, today)+concurrent.races(tools, today)


def http_cases(http, today):
    return base.http_cases(http, today)
