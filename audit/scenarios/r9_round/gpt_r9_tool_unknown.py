"""Independent W7 probe: unknown status must make race and HTTP groups INCOMPLETE.

The frozen duplicate-ID scenario is a separate job because a correct early
group refusal prevents later status cases from executing in the same group.
"""


def cases(cur, today):
    return [("G9_TOOL:REGISTRATION_CONTROL", lambda: {"status": "PASS"})]


def races(tools, today):
    return [("G9_TOOL:RACE_UNKNOWN_STATUS", lambda: {"status": "UNRECOGNISED", "sentinel": "must_be_incomplete"})]


def http_cases(http, today):
    return [("G9_TOOL:HTTP_UNKNOWN_STATUS", lambda: {"status": "UNRECOGNISED", "sentinel": "must_be_incomplete"})]
