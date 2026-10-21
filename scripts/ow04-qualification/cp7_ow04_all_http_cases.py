"""Exact real HTTP qualification: preserved initial8 plus new source6."""
import cp7_ow04_http_cases as initial_http
import cp7_ow04_source_http_cases as source_http

INITIAL_IDS = initial_http.IDS
SOURCE_IDS = source_http.IDS
IDS = INITIAL_IDS + SOURCE_IDS
assert len(INITIAL_IDS) == 8 and len(SOURCE_IDS) == 6
assert len(IDS) == len(set(IDS)) == 14


def http_cases(http, today):
    planned = initial_http.http_cases(http, today) + source_http.http_cases(http, today)
    assert tuple(ident for ident, _ in planned) == IDS
    return planned
