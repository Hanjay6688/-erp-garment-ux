"""Six focused transport cases; no mutation of B's fixture or accepted routes."""
from pathlib import Path
import importlib.util
import cp7_current_choice_preparation.installation as product

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


common = load('choice_transport_common', HERE / 'common.py')
http = load('choice_transport_http', HERE / 'http_cases.py')
race = load('choice_transport_races', HERE / 'race_cases.py')
http.C = race.C = common
race.PRODUCT = product
IDS = common.IDS
GROUPS = {'choice_http': IDS['http'], 'choice_races': IDS['races']}
installed = common.installed
http_cases, races = http.http_cases, race.races
