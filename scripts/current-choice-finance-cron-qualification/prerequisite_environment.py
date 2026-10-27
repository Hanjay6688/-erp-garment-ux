"""Bind the shared Native6 Original to the UI admission without another fetch."""
from pathlib import Path
from hashlib import sha256
import json


def bindings(repo, environment):
    scripts = Path(repo) / 'scripts'
    ui = scripts / 'current-progress-finance-ui-browser-qualification'
    transport = scripts / 'current-choice-preparation-transport-qualification'
    ui_config = json.loads((ui / 'CONFIG.json').read_bytes())
    transport_config = json.loads((transport / 'CONFIG.json').read_bytes())
    ui_proof = json.loads((ui / 'SOURCE.json').read_bytes())['actual_predecessor']
    transport_proof = json.loads((transport / 'SOURCE.json').read_bytes())['actual_predecessor']
    assert ui_proof == transport_proof, 'NATIVE6_PREREQUISITE_MISMATCH'
    source = Path(environment[transport_config['choice_variable']])
    raw = source.read_bytes()
    assert len(raw) == ui_proof['bytes'], 'NATIVE6_ORIGINAL_LENGTH_CHANGED'
    assert sha256(raw).hexdigest() == ui_proof['sha256'], 'NATIVE6_ORIGINAL_HASH_CHANGED'
    target = ui_config['choice_variable']
    if target in environment:
        assert Path(environment[target]).read_bytes() == raw, 'UI_NATIVE6_ALREADY_BOUND_TO_DIFFERENT_BYTES'
    return {target: str(source)}
