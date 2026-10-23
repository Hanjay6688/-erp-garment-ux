"""Fetch the exact positive OW-04b slice B Native6+Race1 original; no DB or product execution."""
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import subprocess
import zipfile

REPO=Path(__file__).resolve().parents[1]
RECEIPT=REPO/'docs/cp7/d17-14/ow04/ow04b-slice-b-native6-race1-33760a52-pass.json'
LABEL='CP7_OW04BB_MULTI_RETURN_NATIVE6_RACE1'


def main():
    proof=json.loads(RECEIPT.read_bytes())
    assert proof['label']==LABEL and proof['status']=='PASS'and proof['expected_case_count']==proof['observed_case_count']==6
    assert proof['observed_race_count']==1 and set(proof['cases'].values())=={'PASS'}and set(proof['races'].values())=={'PASS'}
    assert proof['cp6_restored']and proof['advisor_gate']and all(proof['package_gate'].values())
    artifact=int(re.fullmatch(r'cp7-ow04b-multi-return-native6-race1 \((\d+)\)',proof['artifact']).group(1));original=proof['report']
    root=Path(os.environ['RUNNER_TEMP']);archive=root/'ow04bb-qualified-native6-race1.zip'
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
