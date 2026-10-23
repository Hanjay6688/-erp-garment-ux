"""Fetch the exact positive OW-12a chain Native7 original (OW12a over OW08a); no DB or product execution."""
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import subprocess
import zipfile

REPO=Path(__file__).resolve().parents[1]
RECEIPT=REPO/'docs/cp7/d17-14/ow12/native7-646a52e0-chain-pass.json'
LABEL='CP7_OW12A_FINANCE_CAPTURE_NATIVE7'


def main():
    proof=json.loads(RECEIPT.read_bytes())
    assert proof['label']==LABEL and proof['status']=='PASS'and proof['expected_case_count']==proof['observed_case_count']==7
    assert len(proof['cases'])==7 and set(proof['cases'].values())=={'PASS'}
    assert proof['cp6_restored']and proof['advisor_gate']and all(proof['package_gate'].values())
    artifact=int(re.fullmatch(r'cp7-ow12a-finance-capture-native7 \((\d+)\)',proof['artifact']).group(1));original=proof['report']
    root=Path(os.environ['RUNNER_TEMP']);archive=root/'ow12a-chain-qualified-native7.zip'
    with archive.open('wb')as output:
        subprocess.run(['gh','api',f"repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{artifact}/zip"],stdout=output,check=True)
    with zipfile.ZipFile(archive)as z:
        assert z.namelist().count(original['name'])==1
        raw=z.read(original['name'])
    assert len(raw)==original['raw_bytes']and sha256(raw).hexdigest()==original['raw_sha256']
    actual=json.loads(raw)
    assert actual['label']==LABEL and actual['status']=='PASS'and actual['native']['counts']=={'PASS':7}
    assert actual['cp6_restored']and actual['advisor_gate']and actual['required_case_ids_pass']
    assert actual['qualification_commit']==proof['qualification_commit']
    declared=json.loads((REPO/'scripts/cp7_finance_capture/SOURCE.json').read_bytes())
    assert actual['source_declaration']['OW12a_declared_source']==declared
    for path,digest in declared['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('QUALIFIED_OW12A_SOURCE_CHANGED',path)
    out=root/'OW12A_NATIVE7_ORIGINAL.json';out.write_bytes(raw)
    with open(os.environ['GITHUB_ENV'],'a')as env:
        env.write('OW12A_NATIVE7_ORIGINAL_REPORT='+str(out)+'\n')
    print('ACTUAL_OW12A_NATIVE7_ORIGINAL_BYTES_AND_FULL_DECLARED_SOURCE_VERIFIED_NO_PRODUCT_EXECUTION',flush=True)


if __name__=='__main__':main()
