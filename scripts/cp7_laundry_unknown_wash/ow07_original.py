"""Fetch the exact positive OW07 Native7 original report (run 39828046424); no DB or product execution.

docs/cp7/d17-14/ow07/PROGRESS.md records one size and SHA-256 for artifact cp7-ow07-hpp-close-native7 of that run without
saying whether they are those of the downloaded archive or of the report inside it. Both are bindings to the same run's
bytes, so the recorded pair must equal one of them exactly (the one that matched is printed); a different pair refuses.
The report itself must be the PASS 7/7 OW07 report whose declared source equals the OW07 source pinned in this tree.
"""
from hashlib import sha256
from pathlib import Path
import json
import os
import subprocess
import zipfile

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
REPORT='CP7_OW07_HPP_CLOSE_NATIVE7.json'


def main():
    proof=json.loads((HERE/'SOURCE.json').read_bytes())['ow07_native_original']
    listing=json.loads(subprocess.run(['gh','api',f"repos/Hanjay6688/-erp-garment-ux/actions/runs/{proof['run_id']}/artifacts?per_page=100"],
        stdout=subprocess.PIPE,check=True).stdout)
    found=[a for a in listing['artifacts']if a['name']==proof['artifact_name']]
    assert len(found)==1 and not found[0]['expired'],('OW07_ARTIFACT_NOT_UNIQUE_OR_EXPIRED',[(a['id'],a['expired'])for a in found])
    root=Path(os.environ['RUNNER_TEMP']);archive=root/'ow07-qualified-native7.zip'
    with archive.open('wb')as output:
        subprocess.run(['gh','api',f"repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{found[0]['id']}/zip"],stdout=output,check=True)
    packed=archive.read_bytes()
    with zipfile.ZipFile(archive)as z:
        names=[n for n in z.namelist()if Path(n).name==REPORT]
        assert len(names)==1,names
        raw=z.read(names[0])
    pairs={'archive':(len(packed),sha256(packed).hexdigest()),'report':(len(raw),sha256(raw).hexdigest())}
    matched=[k for k,v in pairs.items()if v==(proof['bytes'],proof['sha256'])]
    assert len(matched)==1,('OW07_RECORDED_DIGEST_MISMATCH',pairs)
    actual=json.loads(raw)
    assert actual['label']=='CP7_OW07_HPP_CLOSE_NATIVE7' and actual['status']=='PASS' and actual['native']['counts']=={'PASS':7}
    assert actual['cp6_restored']and actual['advisor_gate']and actual['required_case_ids_pass']
    declared=json.loads((REPO/'scripts/cp7_hpp_close/SOURCE.json').read_bytes())
    assert actual['source_declaration']['OW07_declared_source']==declared
    for path,digest in declared['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('QUALIFIED_OW07_SOURCE_CHANGED',path)
    out=root/'OW07_NATIVE7_ORIGINAL.json';out.write_bytes(raw)
    with open(os.environ['GITHUB_ENV'],'a')as env:
        env.write('OW07_NATIVE7_ORIGINAL_REPORT='+str(out)+'\n')
    print(json.dumps(dict(ow07_native7_original=True,artifact_id=found[0]['id'],recorded_pair_is=matched[0],
        archive=pairs['archive'],report=pairs['report'])),flush=True)
    print('ACTUAL_OW07_NATIVE7_ORIGINAL_BYTES_AND_FULL_DECLARED_SOURCE_VERIFIED_NO_PRODUCT_EXECUTION',flush=True)


if __name__=='__main__':main()
