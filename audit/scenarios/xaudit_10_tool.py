"""AUDITOR SCENARIO xaudit_10_tool (Fable, round 9 W7 B1 tool probe, independent of GPT's): deliberately invalid outputs.
Expected (tool oracle, handoff §29.2 W7): a status outside PASS/FAIL/COUNTEREXAMPLE/INCOMPLETE becomes INCOMPLETE with the
original value kept; a non-dict result becomes INCOMPLETE; a raised exception becomes INCOMPLETE with the message; the group
prints planned/final/missing; an ID that never produced a row is 'missing'. No duplicate IDs here (covered separately), so the
whole group executes. No business RPC is called. A RUN_COMPLETE with these cases would be a TOOL counterexample."""
def cases(cur,today):
    return [('F10_TOOL:CASES_CONTROL',lambda:dict(status='PASS',scope='registration control only')),
            ('F10_TOOL:CASES_WEIRD_STATUS',lambda:dict(status='MAYBE',sentinel='MUST_BE_INCOMPLETE_KEEP_ORIGINAL')),
            ('F10_TOOL:CASES_NOT_A_DICT',lambda:['not','a','dict']),
            ('F10_TOOL:CASES_RAISES',lambda:(_ for _ in ()).throw(RuntimeError('deliberate exception must be INCOMPLETE')))]
def races(tools,today):
    return [('F10_TOOL:RACE_CONTROL',lambda:dict(status='PASS')),
            ('F10_TOOL:RACE_WEIRD_STATUS',lambda:dict(status='SUCCESS',sentinel='MUST_BE_INCOMPLETE')),
            ('F10_TOOL:RACE_NONE_STATUS',lambda:dict(status=None)),
            ('F10_TOOL:RACE_NOT_A_DICT',lambda:'PASS')]
def http_cases(http,today):
    return [('F10_TOOL:HTTP_CONTROL',lambda:dict(status='PASS')),
            ('F10_TOOL:HTTP_WEIRD_STATUS',lambda:dict(status='pass',sentinel='lowercase must not count as PASS')),
            ('F10_TOOL:HTTP_MISSING_STATUS',lambda:dict(note='no status key')),
            ('F10_TOOL:HTTP_NOT_A_DICT',lambda:None)]
