"""Fetch the exact positive OW-08b wash chain Native11 original (wash over OW07, OW-15 step 11); no DB or product execution.

scripts/cp7_credit_followups/SOURCE.json names the chain receipt docs/cp7/d17-14/ow08/wash-native11-<head8>-chain-pass.json
(native_original_run) and the report's raw size and SHA-256 (native_original); receipt and pins must agree, and the
downloaded report must be exactly those bytes. The report must be the PASS 11/11 wash report whose declared source equals
the wash source pinned in this tree. Until the receipt exists the PENDING_* pins refuse.
"""
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import subprocess
import zipfile

REPO=Path(__file__).resolve().parents[1]
LABEL='CP7_OW08B_LAUNDRY_UNKNOWN_WASH_NATIVE11'
REPORT=LABEL+'.json'


def main():
    pins=json.loads((REPO/'scripts/cp7_credit_followups/SOURCE.json').read_bytes())
    pin,run=pins['native_original'],pins['native_original_run']
    head=re.fullmatch(r'docs/cp7/d17-14/ow08/wash-native11-([0-9a-f]{8})-chain-pass\.json',run['receipt'])
    assert head and head.group(1)==run['head'],('WASH_CHAIN_RECEIPT_PIN_PENDING_OR_CHANGED',run['receipt'],run['head'])
    proof=json.loads((REPO/run['receipt']).read_bytes())
    assert proof['label']==LABEL and proof['status']=='PASS'and proof['expected_case_count']==proof['observed_case_count']==11
    assert len(proof['cases'])==11 and set(proof['cases'].values())=={'PASS'}
    assert proof['cp6_restored']and proof['advisor_gate']and all(proof['package_gate'].values())
    assert proof['run']==run['run']and proof['head']==run['head']and proof['qualification_commit'].startswith(run['head'])
    artifact=int(re.fullmatch(r'cp7-ow08b-laundry-unknown-wash-native11 \((\d+)\)',proof['artifact']).group(1));original=proof['report']
    assert artifact==run['artifact']
    assert original['name']==REPORT==pin['name']and original['raw_bytes']==pin['bytes']and original['raw_sha256']==pin['sha256']
    root=Path(os.environ['RUNNER_TEMP']);archive=root/'wash-chain-qualified-native11.zip'
    with archive.open('wb')as output:
        subprocess.run(['gh','api',f"repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{artifact}/zip"],stdout=output,check=True)
    with zipfile.ZipFile(archive)as z:
        assert z.namelist().count(REPORT)==1
        raw=z.read(REPORT)
    assert len(raw)==pin['bytes']and sha256(raw).hexdigest()==pin['sha256']
    actual=json.loads(raw)
    assert actual['label']==LABEL and actual['status']=='PASS'and actual['native']['counts']=={'PASS':11}
    assert actual['cp6_restored']and actual['advisor_gate']and actual['required_case_ids_pass']
    assert actual['qualification_commit']==proof['qualification_commit']
    declared=json.loads((REPO/'scripts/cp7_laundry_unknown_wash/SOURCE.json').read_bytes())
    assert actual['source_declaration']['OW08b_wash_declared_source']==declared
    for path,digest in declared['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('QUALIFIED_WASH_SOURCE_CHANGED',path)
    out=root/'OW08B_WASH_NATIVE11_ORIGINAL.json';out.write_bytes(raw)
    with open(os.environ['GITHUB_ENV'],'a')as env:
        env.write('OW08B_WASH_NATIVE11_ORIGINAL_REPORT='+str(out)+'\n')
    print('ACTUAL_OW08B_WASH_NATIVE11_ORIGINAL_BYTES_AND_FULL_DECLARED_SOURCE_VERIFIED_NO_PRODUCT_EXECUTION',flush=True)


if __name__=='__main__':main()
