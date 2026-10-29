"""Literal IDs/categories; never an executed-case result."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[2]


def ids(relative, name='IDS'):
    nodes = ast.parse((ROOT / relative).read_text()).body
    return next(ast.literal_eval(n.value) for n in nodes if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))


NATIVE_IDS = ids('scripts/current-sku-pair-conversion-qualification/cases.py')
COST_IDS = ids('scripts/current-sku-group-cost-qualification/cases.py')
RACE_IDS = ids('scripts/current-sku-pair-conversion-qualification/races.py')
WAIT_IDS = ids('scripts/current-sku-pair-conversion-qualification/auth_waits.py')
BROWSER_IDS = (
    'SKU29_BROWSER_DESKTOP_REAL_AUTH_PAIR_FIFO_RECOVERY_INVERSE',
    'SKU29_BROWSER_MOBILE390_REAL_AUTH_PAIR_FIFO_GUARDS_INVERSE',
    'A_STAGED_AI_BROWSER_DESKTOP_MANUAL_AND_RETIRED_RESPONSES',
    'A_STAGED_AI_BROWSER_MOBILE_MANUAL_AND_RETIRED_RESPONSES',
)
assert tuple(map(len, (NATIVE_IDS, COST_IDS, RACE_IDS, WAIT_IDS, BROWSER_IDS))) == (7, 3, 3, 6, 4)
assert len(set(NATIVE_IDS + COST_IDS + RACE_IDS + WAIT_IDS + BROWSER_IDS)) == 23
