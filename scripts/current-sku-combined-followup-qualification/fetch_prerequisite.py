"""Acquire exact terminal proof bytes only after root fills the closed pin."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import io
import json
import os
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]


def main():
    spec = importlib.util.spec_from_file_location('sku_terminal_prerequisite_gate', HERE / 'gate.py')
    gate = importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)
    cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
    pin = gate.selected(cfg)  # No GET, secret, runtime import or DB before this.
    def get(path):
        return subprocess.check_output(['gh', 'api', 'repos/Hanjay6688/-erp-garment-ux/' + path])
    run = json.loads(get('actions/runs/' + str(pin['run_id'])))
    assert run['status'] == 'completed' and run['conclusion'] == 'success' and run['head_sha'] == gate.BASE
    assert run['path'] == '.github/workflows/cp7-sku-pair-native.yml'
    artifact = json.loads(get('actions/artifacts/' + str(pin['artifact_id'])))
    assert artifact['workflow_run']['id'] == pin['run_id'] and artifact['expired'] is False
    rawzip = get('actions/artifacts/' + str(pin['artifact_id']) + '/zip')
    out = ROOT / 'cp6-proof/t3/RETAINED_SKU21C'; out.mkdir(parents=True, exist_ok=True)
    (out / 'ORIGINAL.zip').write_bytes(rawzip)
    assert len(rawzip) == pin['zip_bytes'] == artifact['size_in_bytes']
    assert sha256(rawzip).hexdigest() == pin['zip_sha256'] and artifact['digest'] == 'sha256:' + pin['zip_sha256']
    with zipfile.ZipFile(io.BytesIO(rawzip)) as z:
        assert z.testzip() is None
        for key in ('original', 'package'):
            item = pin[key]; names = [n for n in z.namelist() if Path(n).name == item['name']]
            assert len(names) == 1
            raw = z.read(names[0]); (out / item['name']).write_bytes(raw)
            assert len(raw) == item['bytes'] and sha256(raw).hexdigest() == item['sha256']
    actual = json.loads((out / pin['original']['name']).read_bytes())
    assert actual['status'] == 'PASS' and actual['qualification_commit'] == gate.BASE
    (out / 'FETCH_RECEIPT.json').write_text(json.dumps(dict(status='EXACT_TERMINAL_RAW_BYTES_ACQUIRED_SOURCE_ADMISSION_STILL_REQUIRED',
         run_id=pin['run_id'], artifact_id=pin['artifact_id'], raw_pins=pin, actual_new_cases=0), indent=2) + '\n')
    with open(os.environ['GITHUB_ENV'], 'a') as env:
        env.write('CP7_SKU_NATIVE7_ORIGINALS=' + str(out) + '\n')


if __name__ == '__main__': main()
