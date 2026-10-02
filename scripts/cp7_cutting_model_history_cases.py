"""Every predecessor53 plus four ordinary connected consumer journeys =57."""
import cp7_cutting_observation_history_cases as previous
import cp7_cutting_model_cases as model
import json
from pathlib import Path
MANIFEST=json.loads((Path(__file__).resolve().parents[1]/'docs/cp7/f04/native_cutting_learning_native57_manifest.json').read_text())
EXPECTED=MANIFEST['expected_case_count']
REQUIRED=MANIFEST['required_case_counts']
assert EXPECTED==57==sum(REQUIRED.values())
def cases(cur,today):return previous.cases(cur,today)+model.cases(cur,today)
def races(tools,today):return previous.races(tools,today)+model.races(tools,today)
def http_cases(http,today):return previous.http_cases(http,today)+model.http_cases(http,today)
