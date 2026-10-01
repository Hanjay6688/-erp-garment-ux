"""Select the retained combined-ledger and private-context controls only."""
import cp7_f03_cases as retained

def cases(cur, today):
    names = {'F03_COMBINED_LEDGER', 'F03_PRIVATE_CONTEXT_ISOLATION'}
    result = [(name, case) for name, case in retained.cases(cur, today) if name in names]
    assert {name for name, _ in result} == names
    return result
