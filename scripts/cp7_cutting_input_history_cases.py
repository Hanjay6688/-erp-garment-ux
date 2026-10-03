"""All predecessor23 plus eleven actual prospective-input cases =34."""
import cp7_cutting_yield_history_cases as previous
import cp7_cutting_input_cases as inputs
EXPECTED=34
def cases(cur,today):return previous.cases(cur,today)+inputs.cases(cur,today)
def races(tools,today):return previous.races(tools,today)+inputs.races(tools,today)
def http_cases(http,today):return previous.http_cases(http,today)+inputs.http_cases(http,today)
