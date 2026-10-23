"""Fetch the exact positive OW07 Native7 chain original (OW07 over OW-09, OW-15 step 10); no DB or product execution.

SOURCE.json ow07_native_original names the chain receipt docs/cp7/d17-14/ow07/native7-<head8>-chain-pass.json and repeats
its head, run, artifact and the report's raw size and SHA-256; receipt and pin must agree, and the downloaded report must
be exactly those bytes. The report itself must be the PASS 7/7 OW07 report whose declared source equals the OW07 source
pinned in this tree (which names cp7_ow09_lists as its predecessor). Until the receipt exists the PENDING_* pin refuses.
"""
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import subprocess
import zipfile

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
LABEL='CP7_OW07_HPP_CLOSE_NATIVE7'
REPORT='CP7_OW07_HPP_CLOSE_NATIVE7.json'


def main():
    pin=json.loads((HERE/'SOURCE.json').read_bytes())['ow07_native_original']
    head=re.fullmatch(r'docs/cp7/d17-14/ow07/native7-([0-9a-f]{8})-chain-pass\.json',pin['receipt'])
    assert head and head.group(1)==pin['head'],('OW07_CHAIN_RECEIPT_PIN_PENDING_OR_CHANGED',pin['receipt'],pin['head'])
    proof=json.loads((REPO/pin['receipt']).read_bytes())
    assert proof['label']==LABEL and proof['status']=='PASS'and proof['expected_case_count']==proof['observed_case_count']==7
    assert len(proof['cases'])==7 and set(proof['cases'].values())=={'PASS'}
    assert proof['cp6_restored']and proof['advisor_gate']and all(proof['package_gate'].values())
    assert proof['run']==pin['run']and proof['head']==pin['head']and proof['qualification_commit'].startswith(pin['head'])
    artifact=int(re.fullmatch(r'cp7-ow07-hpp-close-native7 \((\d+)\)',proof['artifact']).group(1));original=proof['report']
    assert artifact==pin['artifact']and pin['artifact_name']=='cp7-ow07-hpp-close-native7'
    assert original['name']==REPORT and original['raw_bytes']==pin['bytes']and original['raw_sha256']==pin['sha256']
    root=Path(os.environ['RUNNER_TEMP']);archive=root/'ow07-chain-qualified-native7.zip'
    with archive.open('wb')as output:
        subprocess.run(['gh','api',f"repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{artifact}/zip"],stdout=output,check=True)
    with zipfile.ZipFile(archive)as z:
        assert z.namelist().count(REPORT)==1
        raw=z.read(REPORT)
    assert len(raw)==pin['bytes']and sha256(raw).hexdigest()==pin['sha256']
    actual=json.loads(raw)
    assert actual['label']==LABEL and actual['status']=='PASS'and actual['native']['counts']=={'PASS':7}
    assert actual['cp6_restored']and actual['advisor_gate']and actual['required_case_ids_pass']
    assert actual['qualification_commit']==proof['qualification_commit']
    declared=json.loads((REPO/'scripts/cp7_hpp_close/SOURCE.json').read_bytes())
    assert actual['source_declaration']['OW07_declared_source']==declared
    for path,digest in declared['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('QUALIFIED_OW07_SOURCE_CHANGED',path)
    out=root/'OW07_NATIVE7_ORIGINAL.json';out.write_bytes(raw)
    with open(os.environ['GITHUB_ENV'],'a')as env:
        env.write('OW07_NATIVE7_ORIGINAL_REPORT='+str(out)+'\n')
    print('ACTUAL_OW07_NATIVE7_ORIGINAL_BYTES_AND_FULL_DECLARED_SOURCE_VERIFIED_NO_PRODUCT_EXECUTION',flush=True)


if __name__=='__main__':main()
