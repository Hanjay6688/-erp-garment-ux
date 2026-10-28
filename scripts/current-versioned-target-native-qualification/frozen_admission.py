"""Run the complete Native30 source gate in its exact immutable checkout."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess,sys

FROZEN_HEAD='ffa0b63dbb6f0b7888eeaec59d0f39347cd58e0e'
GATE='scripts/current-scoped-model-native-qualification/probe.py'


def invoke():
    root=Path(os.environ['CURRENT_SCOPED_MODEL_FROZEN_SOURCE_ROOT']).resolve()
    assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==FROZEN_HEAD
    assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=no'],text=True).strip()
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    env['PYTHONPATH']=str(root/'scripts')+os.pathsep+os.pathsep.join(p for p in env.get('PYTHONPATH','').split(os.pathsep)if p and not p.endswith('/scripts'))
    raw=subprocess.check_output([sys.executable,str(Path(__file__).resolve()),'--frozen-child',str(root)],env=env,cwd=root.parent/'writer')
    return json.loads(raw)


def child(root):
    sys.argv=sys.argv[:1];sys.path.insert(0,str(root/'scripts'))
    spec=importlib.util.spec_from_file_location('immutable_current_scoped_model_native30_gate',root/GATE)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=module.admitted();raw=json.dumps(result,sort_keys=True,default=str,separators=(',',':')).encode()
    print(json.dumps(dict(frozen_head=FROZEN_HEAD,admitted=True,
        source_manifest_sha256=sha256((root/GATE).with_name('SOURCE.json').read_bytes()).hexdigest(),
        complete_admission_receipt_sha256=sha256(raw).hexdigest(),
        current_installation=module.product.sources(),qualification=result['qualification'],
        originals=result['actual_originals_verified']),default=str))


if __name__=='__main__':
    assert len(sys.argv)==3 and sys.argv[1]=='--frozen-child'
    child(Path(sys.argv[2]).resolve())
