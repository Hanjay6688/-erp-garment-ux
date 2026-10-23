"""Fetch the exact positive OW-05b chain Native6 original (OW05b over fgqc); no DB or product execution."""
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import subprocess
import zipfile

REPO=Path(__file__).resolve().parents[1]
RECEIPT=REPO/'docs/cp7/d17-14/ow05/native6-197fb3fc-chain-pass.json'
LABEL='CP7_OW05B_MANDOR_GUIDANCE_NATIVE6'


def main():
    proof=json.loads(RECEIPT.read_bytes())
    assert proof['label']==LABEL and proof['status']=='PASS'and proof['expected_case_count']==proof['observed_case_count']==6
    assert len(proof['cases'])==6 and set(proof['cases'].values())=={'PASS'}
    assert proof['cp6_restored']and proof['advisor_gate']and all(proof['package_gate'].values())
    artifact=int(re.fullmatch(r'cp7-ow05b-mandor-guidance-native6 \((\d+)\)',proof['artifact']).group(1));original=proof['report']
    root=Path(os.environ['RUNNER_TEMP']);archive=root/'ow05b-chain-qualified-native6.zip'
    with archive.open('wb')as output:
        subprocess.run(['gh','api',f"repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{artifact}/zip"],stdout=output,check=True)
    with zipfile.ZipFile(archive)as z:
        assert z.namelist().count(original['name'])==1
        raw=z.read(original['name'])
    assert len(raw)==original['raw_bytes']and sha256(raw).hexdigest()==original['raw_sha256']
    actual=json.loads(raw)
    assert actual['label']==LABEL and actual['status']=='PASS'and actual['native']['counts']=={'PASS':6}
    assert actual['cp6_restored']and actual['advisor_gate']and actual['required_case_ids_pass']
    assert actual['qualification_commit']==proof['qualification_commit']
    declared=json.loads((REPO/'scripts/cp7_contractor_guidance/SOURCE.json').read_bytes())
    assert actual['source_declaration']['OW05b_declared_source']==declared
    for path,digest in declared['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('QUALIFIED_OW05B_SOURCE_CHANGED',path)
    out=root/'OW05B_NATIVE6_ORIGINAL.json';out.write_bytes(raw)
    with open(os.environ['GITHUB_ENV'],'a')as env:
        env.write('OW05B_NATIVE6_ORIGINAL_REPORT='+str(out)+'\n')
    print('ACTUAL_OW05B_NATIVE6_ORIGINAL_BYTES_AND_FULL_DECLARED_SOURCE_VERIFIED_NO_PRODUCT_EXECUTION',flush=True)


if __name__=='__main__':main()
