"""Every original17 plus3 Native source cases,1 real Auth/HTTP and2 actual UI cases."""
import cp7_planning_history_cases as original
import cp7_cutting_yield_cases as cutting
EXPECTED=23
def cases(cur,today):return original.cases(cur,today)+cutting.cases(cur,today)
def races(tools,today):return original.races(tools,today)
def http_cases(http,today):return original.http_cases(http,today)+cutting.http_cases(http,today)
