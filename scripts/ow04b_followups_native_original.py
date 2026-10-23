"""Fetch the exact positive OW-04b followups chain Native9+Race3 original (followups over wash, OW-15 step 12).

No DB or product execution. scripts/cp7_credit_remaining/SOURCE.json names the chain receipt
docs/cp7/d17-14/ow04/ow04b-native9-race3-<head8>-chain-pass.json (native_original_run) and the report's raw size and
SHA-256 (native_original); receipt and pins must agree, and the downloaded report must be exactly those bytes. The report
must be the PASS 9/9 + 3/3 races followups report whose declared source equals the followups source pinned in this tree.
Until the receipt exists the PENDING_* pins refuse.
"""
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import subprocess
import zipfile

REPO=Path(__file__).resolve().parents[1]
LABEL='CP7_OW04B_CREDIT_FOLLOWUPS_NATIVE9_RACE3'
REPORT=LABEL+'.json'


def main():
    pins=json.loads((REPO/'scripts/cp7_credit_remaining/SOURCE.json').read_bytes())
    pin,run=pins['native_original'],pins['native_original_run']
    head=re.fullmatch(r'docs/cp7/d17-14/ow04/ow04b-native9-race3-([0-9a-f]{8})-chain-pass\.json',run['receipt'])
    assert head and head.group(1)==run['head'],('OW04B_CHAIN_RECEIPT_PIN_PENDING_OR_CHANGED',run['receipt'],run['head'])
    proof=json.loads((REPO/run['receipt']).read_bytes())
    assert proof['label']==LABEL and proof['status']=='PASS'and proof['expected_case_count']==proof['observed_case_count']==9
    assert proof['observed_race_count']==3 and len(proof['cases'])==9 and len(proof['races'])==3
    assert set(proof['cases'].values())=={'PASS'}and set(proof['races'].values())=={'PASS'}
    assert proof['cp6_restored']and proof['advisor_gate']and all(proof['package_gate'].values())
    assert proof['run']==run['run']and proof['qualification_commit'].startswith(run['head'])
    artifact=int(re.fullmatch(r'cp7-ow04b-credit-followups-native9-race3 \((\d+)\)',proof['artifact']).group(1));original=proof['report']
    assert artifact==run['artifact']
    assert original['name']==REPORT==pin['name']and original['raw_bytes']==pin['bytes']and original['raw_sha256']==pin['sha256']
    root=Path(os.environ['RUNNER_TEMP']);archive=root/'ow04b-chain-qualified-native9-race3.zip'
    with archive.open('wb')as output:
        subprocess.run(['gh','api',f"repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{artifact}/zip"],stdout=output,check=True)
    with zipfile.ZipFile(archive)as z:
        names=[name for name in z.namelist()if Path(name).name==REPORT]
        assert len(names)==1,names
        raw=z.read(names[0])
    assert len(raw)==pin['bytes']and sha256(raw).hexdigest()==pin['sha256']
    actual=json.loads(raw)
    assert actual['label']==LABEL and actual['status']=='PASS'and actual['native']['counts']=={'PASS':9}
    assert actual['races']['counts']=={'PASS':3}and actual['required_case_ids_pass']and actual['required_race_ids_pass']
    assert actual['cp6_restored']and actual['advisor_gate']and actual['qualification_commit']==proof['qualification_commit']
    declared=json.loads((REPO/'scripts/cp7_credit_followups/SOURCE.json').read_bytes())
    assert actual['source_declaration']['OW04B_declared_source']==declared
    for path,digest in declared['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('QUALIFIED_OW04B_SOURCE_CHANGED',path)
    out=root/'OW04B_NATIVE9_RACE3_ORIGINAL.json';out.write_bytes(raw)
    with open(os.environ['GITHUB_ENV'],'a')as env:
        env.write('OW04B_NATIVE9_RACE3_ORIGINAL_REPORT='+str(out)+'\n')
    print('ACTUAL_OW04B_NATIVE9_RACE3_ORIGINAL_BYTES_AND_FULL_DECLARED_SOURCE_VERIFIED_NO_PRODUCT_EXECUTION',flush=True)


if __name__=='__main__':main()
