"""Explicit immutable prerequisite bytes; null pin refuses before any GET."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import io
import json
import os
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    spec = importlib.util.spec_from_file_location('continuation_terminal_fetch_gate',HERE/'gate.py')
    gate = importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)
    config = json.loads((HERE/'CONFIG.json').read_bytes()); pin = gate.selected(config)

    def get(path):
        return subprocess.check_output(['gh','api','repos/Hanjay6688/-erp-garment-ux/'+path])

    run = json.loads(get('actions/runs/'+str(pin['run_id'])))
    if (run['status'],run['conclusion'],run['head_sha'],run['path']) != ('completed','success',pin['head'],config['required_parent_workflow']):
        raise ValueError('D1_CONT_EXACT_TERMINAL_SUCCESSFUL_PARENT_WORKFLOW_REQUIRED')
    job = json.loads(get('actions/jobs/'+str(pin['job_id'])))
    if (job['run_id'],job['status'],job['conclusion']) != (pin['run_id'],'completed','success'):
        raise ValueError('D1_CONT_EXACT_TERMINAL_SUCCESSFUL_PARENT_JOB_REQUIRED')
    artifact = json.loads(get('actions/artifacts/'+str(pin['artifact_id'])))
    if artifact['workflow_run']['id'] != pin['run_id']or artifact['expired']is not False:
        raise ValueError('D1_CONT_EXACT_PARENT_ARTIFACT_REQUIRED')
    rawzip = get('actions/artifacts/'+str(pin['artifact_id'])+'/zip')
    if (len(rawzip) != pin['zip_bytes']or len(rawzip) != artifact['size_in_bytes']
            or sha256(rawzip).hexdigest() != pin['zip_sha256']or artifact['digest'] != 'sha256:'+pin['zip_sha256']):
        raise ValueError('D1_CONT_EXACT_PARENT_ZIP_BYTES_REQUIRED')
    out = ROOT/'cp6-proof/t3/RETAINED_D1_CONT_PARENT'; out.mkdir(parents=True,exist_ok=True)
    with(out/'ORIGINAL.zip').open('xb')as stream:
        stream.write(rawzip)
    with zipfile.ZipFile(io.BytesIO(rawzip))as archive:
        if archive.testzip()is not None:
            raise ValueError('D1_CONT_PARENT_ZIP_CORRUPT')
        for key in gate.ORIGINALS:
            item = pin[key]; names = [name for name in archive.namelist()if Path(name).name == item['name']]
            if len(names) != 1:
                raise ValueError('D1_CONT_UNIQUE_EXACT_PARENT_RAW_ORIGINAL_REQUIRED:'+key)
            raw = archive.read(names[0])
            with(out/item['name']).open('xb')as stream:
                stream.write(raw)
            if len(raw) != item['bytes']or sha256(raw).hexdigest() != item['sha256']:
                raise ValueError('D1_CONT_PARENT_ORIGINAL_BYTES_CHANGED:'+key)
    (out/'FETCH_RECEIPT.json').write_text(json.dumps(dict(status='EXACT_TERMINAL_RAW_PARENT_ACQUIRED_FULL_SOURCE_ADMISSION_STILL_REQUIRED',
        parent_head=pin['head'],run_id=pin['run_id'],job_id=pin['job_id'],artifact_id=pin['artifact_id'],raw_pins=pin,
        fresh_continuation_case_credit=0,production_go=False),indent=2)+'\n')
    with open(os.environ['GITHUB_ENV'],'a')as env:
        env.write('CP7_D1_CONT_NATIVE13_ORIGINALS='+str(out)+'\n')


if __name__ == '__main__':
    main()
