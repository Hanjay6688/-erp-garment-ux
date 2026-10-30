"""Pure qualification binding gate before any ERP import, GET or database."""
from hashlib import sha256
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-attendance-choice-reader-native14-qualification'
BASE='9ac9c8bd1bfb7d64a1e735067083c68acbff02ef'
TREE='49591433899ef13c70e3cd94fc0c43894ea182df'


def selected(cfg):
    if (cfg.get('qualification_contract')!='cp7.s03.lawful-fixture-successor-native14.v1'
            or cfg.get('source_base')!=BASE or cfg.get('source_base_tree')!=TREE
            or cfg.get('source_base_is_runtime_prerequisite')is not False
            or cfg.get('failed9ac_partial8PASS_is_prerequisite')is not False
            or cfg.get('fresh_groups')!=[11,3] or cfg.get('expected_captures')!=15
            or cfg.get('expected_clones')!=2 or cfg.get('runtime_files_changed')is not False
            or type(cfg.get('actual_Native_cases'))is not int or cfg.get('actual_Native_cases')!=0 or cfg.get('Native_executed')is not False
            or cfg.get('production_go')is not False or cfg.get('independent_acceptance')is not False):
        raise ValueError('S03_LAWFUL_CLOSED_SOURCE15_SAME_RUNTIME_FRESH11_THEN3_REQUIRED')
    pin=cfg.get('inherited_CONFIG')
    if not isinstance(pin,dict) or set(pin)!={'bytes','sha256'}:
        raise ValueError('S03_LAWFUL_EXACT_INHERITED_CONFIG_REQUIRED')
    return cfg


def current():
    cfg=selected(json.loads((HERE/'CONFIG.json').read_bytes()))
    raw=(PARENT/'CONFIG.json').read_bytes()
    if dict(bytes=len(raw),sha256=sha256(raw).hexdigest())!=cfg['inherited_CONFIG']:
        raise ValueError('S03_LAWFUL_FROZEN_PARENT_CONFIG_CHANGED')
    return cfg
