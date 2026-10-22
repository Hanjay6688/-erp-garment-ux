"""Fetch the exact positive OW06 Native10 original; no DB or product execution."""
from hashlib import sha256
from pathlib import Path
import json
import os
import subprocess
import zipfile

REPO=Path(__file__).resolve().parents[1]
RECEIPT=REPO/'docs/cp7/d17-14/ow06/CHECKPOINT.json'


def main():
    proof=json.loads(RECEIPT.read_bytes())
    assert proof['classification']=='BOUNDED_OW06_NATIVE_BACKEND_CHECKPOINT_NOT_FULL_FEATURE_OR_INDEPENDENT_AUDIT'
    assert proof['status']=='PASS'and proof['counts']=={'PASS':10}and proof['cp6_restored']and proof['advisor_gate']
    artifact=proof['artifact'];original=proof['original_report']
    assert type(artifact['id'])is int and artifact['id']>0
    root=Path(os.environ['RUNNER_TEMP']);archive=root/'ow06-qualified-native10.zip'
    with archive.open('wb')as output:
        subprocess.run(['gh','api',f"repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{artifact['id']}/zip"],stdout=output,check=True)
    packed=archive.read_bytes()
    assert len(packed)==artifact['zip_bytes']and sha256(packed).hexdigest()==artifact['zip_sha256']
    with zipfile.ZipFile(archive)as z:
        assert z.namelist().count(original['name'])==1
        raw=z.read(original['name'])
    assert len(raw)==original['bytes']and sha256(raw).hexdigest()==original['sha256']
    actual=json.loads(raw)
    assert actual['status']=='PASS'and actual['native']['counts']=={'PASS':10}
    assert actual['cp6_restored']and actual['advisor_gate']and actual['required_case_ids_pass']
    declared=json.loads((REPO/'scripts/cp7_supplier_transfer/SOURCE.json').read_bytes())
    assert actual['source_declaration']['OW06_declared_source']==declared
    for path,digest in declared['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('QUALIFIED_OW06_SOURCE_CHANGED',path)
    out=root/'OW06_NATIVE10_ORIGINAL.json';out.write_bytes(raw)
    with open(os.environ['GITHUB_ENV'],'a')as env:
        env.write('OW06_NATIVE10_ORIGINAL_REPORT='+str(out)+'\n')
    print('ACTUAL_OW06_NATIVE10_ORIGINAL_BYTES_AND_FULL_DECLARED_SOURCE_VERIFIED_NO_PRODUCT_EXECUTION',flush=True)


if __name__=='__main__':main()
