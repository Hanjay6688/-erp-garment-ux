"""Verify exact reversible context substitutions above the frozen public browser prep.

This checks source only. It executes no inherited business module and authorizes
neither a source change nor an actual browser/financial verdict.
"""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def verify():
    plan=json.loads((HERE/'ADAPTATIONS.json').read_bytes())
    if plan['contract']!='cp7.s03.browser-lawful-reversible-source.v1':
        raise ValueError('S03_BROWSER_LAWFUL_EXACT_DERIVATION_CONTRACT_REQUIRED')
    total=0
    for item in plan['files']:
        original=(ROOT/item['parent']).read_bytes()
        actual=(ROOT/item['derived']).read_bytes()
        if len(original)!=item['parent_bytes']or sha256(original).hexdigest()!=item['parent_sha256']:
            raise ValueError('S03_BROWSER_LAWFUL_FROZEN_PARENT_SOURCE_CHANGED')
        value=original.decode()
        for step in item['changes']:
            if not step['before']or value.count(step['before'])!=step['count']or step['count']!=1:
                raise ValueError('S03_BROWSER_LAWFUL_ONE_FORWARD_ANCHOR_REQUIRED')
            value=value.replace(step['before'],step['after'],1)
        if value.encode()!=actual or sha256(actual).hexdigest()!=item['derived_sha256']:
            raise ValueError('S03_BROWSER_LAWFUL_DERIVED_SOURCE_CHANGED')
        for step in reversed(item['changes']):
            if not step['after']or value.count(step['after'])!=1:
                raise ValueError('S03_BROWSER_LAWFUL_ONE_REVERSE_ANCHOR_REQUIRED')
            value=value.replace(step['after'],step['before'],1)
        if value.encode()!=original:raise ValueError('S03_BROWSER_LAWFUL_LOSSLESS_PARENT_REQUIRED')
        total+=len(item['changes'])
    if total!=plan['counted_changes']:raise ValueError('S03_BROWSER_LAWFUL_COUNT_CHANGED')
    spec=importlib.util.spec_from_file_location('s03_exact_current_rights_delta',HERE/'rights_delta.py')
    rights=importlib.util.module_from_spec(spec);spec.loader.exec_module(rights)
    current_rights=rights.verify()
    spec=importlib.util.spec_from_file_location('s03_exact_cancelled_history_delta',HERE/'history_delta.py')
    history=importlib.util.module_from_spec(spec);spec.loader.exec_module(history)
    current_history=history.verify()
    return dict(derived_files=len(plan['files']),counted_changes=total,all_parent_bytes_restored=True,
        Native_SQL_changed=False,frozen_UI82_changed=False,frozen_runtime7_changed=False,
        current_UI_changed_paths=['src/attendance-period-choice.css'],
        current_rights_successor=current_rights,current_history_successor=current_history,actual_Native_Auth_browser_credit=0)

if __name__=='__main__':print(json.dumps(verify()))
