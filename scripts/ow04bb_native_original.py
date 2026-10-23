"""Fetch the exact positive OW-04b slice B chain Native6+Race1 original (slice B over slice A over followups, OW-15 step 14).

No DB or product execution. scripts/cp7_credit_incoming/SOURCE.json names the chain receipt
docs/cp7/d17-14/ow04/ow04b-slice-b-native6-race1-<head8>-chain-pass.json (native_original_run) and the report's raw
size, SHA-256, artifact and qualification commit (native_original); receipt and pins must agree. Until the receipt
exists the PENDING_* pins refuse. The earlier pass 33760a52 (over OW05) stays in docs as history.
"""
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import subprocess
import zipfile

REPO=Path(__file__).resolve().parents[1]
LABEL='CP7_OW04BB_MULTI_RETURN_NATIVE6_RACE1'


def main():
    pins=json.loads((REPO/'scripts/cp7_credit_incoming/SOURCE.json').read_bytes())
    pin,run=pins['native_original'],pins['native_original_run']
    head=re.fullmatch(r'docs/cp7/d17-14/ow04/ow04b-slice-b-native6-race1-([0-9a-f]{8})-chain-pass\.json',run['receipt'])
    assert head and head.group(1)==run['head'],('OW04BB_CHAIN_RECEIPT_PIN_PENDING_OR_CHANGED',run['receipt'],run['head'])
    proof=json.loads((REPO/run['receipt']).read_bytes())
    assert proof['label']==LABEL and proof['status']=='PASS'and proof['expected_case_count']==proof['observed_case_count']==6
    assert proof['observed_race_count']==1 and set(proof['cases'].values())=={'PASS'}and set(proof['races'].values())=={'PASS'}
    assert proof['cp6_restored']and proof['advisor_gate']and all(proof['package_gate'].values())
    assert proof['run']==run['run']and proof['qualification_commit']==pin['qualification_commit']and pin['qualification_commit'].startswith(run['head'])
    artifact=int(re.fullmatch(r'cp7-ow04b-multi-return-native6-race1 \((\d+)\)',proof['artifact']).group(1));original=proof['report']
    assert artifact==run['artifact']and proof['artifact']==pin['artifact']
    assert original['name']==pin['name']and original['raw_bytes']==pin['bytes']and original['raw_sha256']==pin['sha256']
    root=Path(os.environ['RUNNER_TEMP']);archive=root/'ow04bb-chain-qualified-native6-race1.zip'
    with archive.open('wb')as output:
        subprocess.run(['gh','api',f"repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{artifact}/zip"],stdout=output,check=True)
    with zipfile.ZipFile(archive)as z:
        names=[name for name in z.namelist()if Path(name).name==original['name']]
        assert len(names)==1,names
        raw=z.read(names[0])
    assert len(raw)==original['raw_bytes']and sha256(raw).hexdigest()==original['raw_sha256']
    actual=json.loads(raw)
    assert actual['label']==LABEL and actual['status']=='PASS'and actual['native']['counts']=={'PASS':6}
    assert actual['races']['counts']=={'PASS':1}and actual['cp6_restored']and actual['advisor_gate']and actual['required_case_ids_pass']
    assert actual['qualification_commit']==proof['qualification_commit']
    declared=json.loads((REPO/'scripts/cp7_credit_multi/SOURCE.json').read_bytes())
    assert actual['source_declaration']['OW04BB_declared_source']==declared
    for path,digest in declared['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('QUALIFIED_OW04BB_SOURCE_CHANGED',path)
    out=root/'OW04BB_NATIVE6_RACE1_ORIGINAL.json';out.write_bytes(raw)
    with open(os.environ['GITHUB_ENV'],'a')as env:
        env.write('OW04BB_NATIVE6_ORIGINAL_REPORT='+str(out)+'\n')
    print('ACTUAL_OW04BB_NATIVE6_RACE1_ORIGINAL_BYTES_AND_FULL_DECLARED_SOURCE_VERIFIED_NO_PRODUCT_EXECUTION',flush=True)


if __name__=='__main__':main()
