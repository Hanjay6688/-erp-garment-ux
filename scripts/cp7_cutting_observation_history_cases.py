"""Every predecessor34 plus ten actual observation cases =44."""
import cp7_cutting_input_history_cases as previous
import cp7_cutting_observation_cases as observations
import json
from pathlib import Path
MANIFEST=json.loads((Path(__file__).resolve().parents[1]/'docs/cp7/f04/native_cutting_observation_native44_manifest.json').read_text())
EXPECTED=MANIFEST['expected_case_count']
REQUIRED=MANIFEST['required_case_counts']
assert EXPECTED==44==sum(REQUIRED.values())
def cases(cur,today):return previous.cases(cur,today)+observations.cases(cur,today)
def races(tools,today):return previous.races(tools,today)+observations.races(tools,today)
def http_cases(http,today):return previous.http_cases(http,today)+observations.http_cases(http,today)
