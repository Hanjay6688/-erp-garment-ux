"""28 unchanged retained return controls plus four explicit delta controls.

Historical four changed-refusal-text controls remain INCOMPLETE. Their exact
successor mapping is declared; no frozen expected value or case is rewritten.
"""
from datetime import timedelta
from pathlib import Path
import importlib.util
REPO=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('draft_return_regression_core',REPO/'scripts/draft-return-isolation-qualification/cases.py')
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
PATCHED=False
USED_GUARD=None
FIXTURES=core.FIXTURES
COUNTEREXAMPLES=core.COUNTEREXAMPLES
RETAINED_IDS=('RETURN_SAME_GRADE_A', 'RETURN_SAME_GRADE_B', 'RETURN_SAME_HOLD', 'RETURN_OTHER_GRADE_A', 'RETURN_OTHER_GRADE_B', 'RETURN_OTHER_HOLD', 'ALLOCATION_LIMIT', 'SPLIT_DESTINATION', 'AH_AG_RETURN_SAME_GRADE_A', 'AH_AG_RETURN_SAME_GRADE_B', 'AH_AG_RETURN_SAME_HOLD', 'AH_AG_RETURN_OTHER_GRADE_A', 'AH_AG_RETURN_OTHER_GRADE_B', 'AH_AG_RETURN_OTHER_HOLD', 'AH_AG_RETURN_OVER_QTY', 'AH_AG_RETURN_REPEAT_POST', 'AH_AG_RETURN_REVERSE', 'AH_AG_RETURN_ALLOCATION_ONE_DOCUMENT', 'AH_ORDINARY_SAME_GRADE_A', 'AH_ORDINARY_SAME_GRADE_B', 'AH_ORDINARY_SAME_HOLD', 'AH_ORDINARY_OTHER_GRADE_A', 'AH_ORDINARY_OTHER_GRADE_B', 'AH_ORDINARY_OTHER_HOLD', 'AH_ALLOCATION_LIMIT', 'AH_SPLIT_DESTINATION', 'AH_SOURCE_DRAFT', 'AH_SOURCE_REVERSED')
SUCCESSOR_MAP={'SOURCE_REBIND': 'RETAINED_SOURCE_REBIND_REFUSAL', 'AH_SOURCE_REBIND': 'RETAINED_SOURCE_REBIND_REFUSAL', 'AH_AG_RETURN_SPLIT': 'RETAINED_THREE_PIECE_ALLOCATION_LIMIT', 'AH_AG_RETURN_REBIND_CUSTOMER': 'VALID_RETURN_WITH_BAD_CUSTOMER_SIBLING_DRAFT'}
IDS=core.IDS+RETAINED_IDS

def cases(cur,today):
    core.PATCHED=PATCHED;core.USED_GUARD=USED_GUARD
    result=core.cases(cur,today)
    found=core.old.ai.phase_cases('focused')
    selected=[(n,fn)for n,fn in found if n in RETAINED_IDS]
    assert tuple(n for n,_ in selected)==RETAINED_IDS
    day=today-timedelta(days=3)
    for name,fn in selected:
        def run(n=name,operation=fn):
            row=operation(cur,day)
            return dict(status=row.get('status'),original_result=row,retained_case_id=n,
                original_body_and_oracle_unchanged=True,delta_installed=PATCHED)
        result.append((name,run))
    return result
