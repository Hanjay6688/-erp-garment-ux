"""Run every predecessor gate in its immutable source checkout, in a fresh process.

Old UI pins are never repinned. The caller separately verifies every current
file and exact product-source equality before running the new six UI cases.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess,sys

FROZEN_HEAD='469ed1e8b2edf80f7988feba38162a5be7251b8c'
GATES=('current-return-browser-bounded-qualification','current-analog-native-fixture-qualification')


def invoke():
    root=Path(os.environ['CURRENT_ANALOG_FROZEN_SOURCE_ROOT']).resolve()
    assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==FROZEN_HEAD
    assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=no'],text=True).strip()
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    # Replace the current source import path. The interpreter's installed
    # dependency location and immutable writer cwd retain their usual roles.
    env['PYTHONPATH']=str(root/'scripts')+os.pathsep+os.pathsep.join(
        p for p in env.get('PYTHONPATH','').split(os.pathsep)if p and not p.endswith('/scripts'))
    raw=subprocess.check_output([sys.executable,str(Path(__file__).resolve()),'--frozen-child',str(root)],env=env,cwd=root.parent/'writer')
    return json.loads(raw)


def child(root):
    # The recovery modules own an empty CLI contract. These child-process
    # routing arguments belong to this adapter only, never to those modules.
    sys.argv=sys.argv[:1]
    sys.path.insert(0,str(root/'scripts'))
    receipts={}
    for index,folder in enumerate(GATES):
        path=root/'scripts'/folder/'probe.py'
        spec=importlib.util.spec_from_file_location('frozen_predecessor_gate_'+str(index),path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        result=module.admitted()
        raw=json.dumps(result,sort_keys=True,default=str,separators=(',',':')).encode()
        pins=json.loads((path.parent/'SOURCE.json').read_bytes())
        receipts[folder]=dict(admitted=True,source_manifest_sha256=sha256((path.parent/'SOURCE.json').read_bytes()).hexdigest(),
            complete_admission_receipt_sha256=sha256(raw).hexdigest(),pin_count=len(pins['files']))
    import cp7_current_analog_installation as product
    print(json.dumps(dict(frozen_head=FROZEN_HEAD,gates=receipts,current_installation=product.sources()),default=str))


if __name__=='__main__':
    assert len(sys.argv)==3 and sys.argv[1]=='--frozen-child'
    child(Path(sys.argv[2]).resolve())
