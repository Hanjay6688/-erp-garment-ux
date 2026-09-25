"""Independent B1 mode-level probes, deliberately invalid outputs.

Expected: reject duplicate IDs before any operation; unknown status becomes
INCOMPLETE. If the runner reports RUN_COMPLETE or loses the first sentinel,
that is a TOOL counterexample, never a product PASS. No business RPC is called.
Separate from the business scenario so it cannot contaminate business results.
"""
def cases(cur,today):
    return [('G8_TOOL:CONTROL',lambda:dict(status='PASS',scope='registration control only'))]

def races(tools,today):
    return [('G8_TOOL:RACE_DUP',lambda:dict(status='INCOMPLETE',sentinel='FIRST_MUST_NOT_BE_LOST')),
            ('G8_TOOL:RACE_DUP',lambda:dict(status='PASS',sentinel='SECOND_MUST_NOT_OVERWRITE')),
            ('G8_TOOL:RACE_UNKNOWN',lambda:dict(status='NOT_A_VALID_STATUS',sentinel='MUST_BE_INCOMPLETE'))]

def http_cases(http,today):
    return [('G8_TOOL:HTTP_DUP',lambda:dict(status='INCOMPLETE',sentinel='FIRST_MUST_NOT_BE_LOST')),
            ('G8_TOOL:HTTP_DUP',lambda:dict(status='PASS',sentinel='SECOND_MUST_NOT_OVERWRITE')),
            ('G8_TOOL:HTTP_UNKNOWN',lambda:dict(status='NOT_A_VALID_STATUS',sentinel='MUST_BE_INCOMPLETE'))]
