"""Root-bound immutable parent proof. Null/known incomplete pin refuses before GET."""
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
    spec = importlib.util.spec_from_file_location('e1_terminal_parent_fetch_gate', HERE/'gate.py')
    gate = importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)
    config = json.loads((HERE/'CONFIG.json').read_bytes())
    pin = gate.selected(config)  # Before GET, runtime import, token access or DB.

    def get(path):
        return subprocess.check_output(['gh', 'api', 'repos/Hanjay6688/-erp-garment-ux/'+path])

    run = json.loads(get('actions/runs/'+str(pin['run_id'])))
    if (run['status'], run['conclusion'], run['head_sha'], run['path']) != (
            'completed', 'success', pin['head'], config['required_parent_workflow']):
        raise ValueError('E1_EXACT_TERMINAL_SUCCESSFUL_PARENT_WORKFLOW_REQUIRED')
    job = json.loads(get('actions/jobs/'+str(pin['job_id'])))
    if (job['run_id'], job['status'], job['conclusion']) != (pin['run_id'], 'completed', 'success'):
        raise ValueError('E1_EXACT_TERMINAL_SUCCESSFUL_PARENT_JOB_REQUIRED')
    artifact = json.loads(get('actions/artifacts/'+str(pin['artifact_id'])))
    if artifact['workflow_run']['id'] != pin['run_id'] or artifact['expired'] is not False:
        raise ValueError('E1_EXACT_PARENT_ARTIFACT_REQUIRED')
    rawzip = get('actions/artifacts/'+str(pin['artifact_id'])+'/zip')
    if (len(rawzip) != pin['zip_bytes'] or len(rawzip) != artifact['size_in_bytes'] or
            sha256(rawzip).hexdigest() != pin['zip_sha256'] or artifact['digest'] != 'sha256:'+pin['zip_sha256']):
        raise ValueError('E1_EXACT_PARENT_ZIP_BYTES_REQUIRED')
    out = ROOT/'cp6-proof/t3/RETAINED_E1_D1'; out.mkdir(parents=True, exist_ok=True)
    (out/'ORIGINAL.zip').write_bytes(rawzip)
    with zipfile.ZipFile(io.BytesIO(rawzip)) as archive:
        if archive.testzip() is not None:
            raise ValueError('E1_PARENT_ZIP_CORRUPT')
        for key in ('original', 'native_group', 'package'):
            item = pin[key]
            names = [name for name in archive.namelist() if Path(name).name == item['name']]
            if len(names) != 1:
                raise ValueError('E1_EXACT_UNIQUE_PARENT_ORIGINAL_REQUIRED:'+key)
            raw = archive.read(names[0]); (out/item['name']).write_bytes(raw)
            if len(raw) != item['bytes'] or sha256(raw).hexdigest() != item['sha256']:
                raise ValueError('E1_PARENT_ORIGINAL_BYTES_CHANGED:'+key)
    (out/'FETCH_RECEIPT.json').write_text(json.dumps(dict(status='EXACT_TERMINAL_PARENT_RAW_BYTES_ACQUIRED_FULL_SOURCE_ADMISSION_STILL_REQUIRED',
        parent_head=pin['head'], run_id=pin['run_id'], job_id=pin['job_id'], artifact_id=pin['artifact_id'], raw_pins=pin,
        fresh_E_case_credit=0, production_go=False), indent=2)+'\n')
    with open(os.environ['GITHUB_ENV'], 'a') as env:
        env.write('CP7_E1_D1_ORIGINALS='+str(out)+'\n')


if __name__ == '__main__':
    main()
