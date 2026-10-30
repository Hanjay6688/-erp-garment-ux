"""Local authoring only: count reversible changes within the allocated child files."""
from pathlib import Path
from hashlib import sha256
import difflib
import json
import os

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-attendance-choice-browser4-qualification'
NAMES=('backend_runtime.py','bind_source.py','component.py','derive.py','fixture.py',
    'output_admission.py','probe.py','proof_binder.py','result_gate.py','source_guard.py',
    'source_inventory.py','test_contract.py','test_outputs.py','workflow.py','cases.mjs',
    'evidence.mjs','test_oracles.mjs','CONFIG.json','PREPARED_BACKEND.json',
    'PREPARED_AUTHOR_BINDING.json','RUNTIME_SOURCE.json','BUILD_OUTPUT_CONTRACT.json',
    'retained-preparation/CONFIG.json','retained-source-metadata/PREPARED_NATIVE14_CONFIG.json',
    'retained-source-metadata/PREPARED_NATIVE14_SOURCE.json',
    *( 'inherited-output-validation/'+name for name in ('generated_receipts.py','generated_later.py',
        'GENERATED_RECEIPTS.json','LATER_GENERATED_RECEIPTS.json','DERIVATION.json',
        'parent/GENERATED_RECEIPTS.json','parent/LATER_GENERATED_RECEIPTS.json')))

def main():
    if os.environ.get('CI'):raise ValueError('S03_BROWSER_LAWFUL_SEAL_IN_CI_FORBIDDEN')
    frozen=json.loads((HERE/'FROZEN_BROWSER_PARENT.json').read_bytes())
    for name,pin in frozen['files'].items():
        raw=(ROOT/name).read_bytes()
        if len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']:
            raise ValueError('S03_BROWSER_LAWFUL_NO_PARENT_REPIN:'+name)
    rows=[]
    pairs=[(PARENT/name,HERE/name)for name in NAMES]
    pairs.append((ROOT/'.github/workflows/cp7-current-s03-browser4.yml',ROOT/'.github/workflows/cp7-current-s03-browser4-lawful.yml'))
    for old,new in pairs:
        before,after=old.read_bytes(),new.read_bytes();a,b=before.decode().splitlines(keepends=True),after.decode().splitlines(keepends=True)
        changes=[]
        for group in difflib.SequenceMatcher(None,a,b,autojunk=False).get_grouped_opcodes(3):
            start,stop=group[0],group[-1]
            changes.append(dict(before=''.join(a[start[1]:stop[2]]),after=''.join(b[start[3]:stop[4]]),count=1))
        rows.append(dict(parent=str(old.relative_to(ROOT)),derived=str(new.relative_to(ROOT)),parent_bytes=len(before),
            parent_sha256=sha256(before).hexdigest(),derived_sha256=sha256(after).hexdigest(),changes=changes))
    value=dict(contract='cp7.s03.browser-lawful-reversible-source.v1',parent_public_commit=frozen['commit'],
        parent_tree=frozen['tree'],files=rows,counted_changes=sum(len(row['changes'])for row in rows),
        source_derivation_only=True,Native_SQL_changed=False,actual_Native_Auth_browser_credit=0)
    (HERE/'ADAPTATIONS.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(dict(files=len(rows),counted_changes=value['counted_changes'],Native_Auth_browser_credit=0)))

if __name__=='__main__':main()
