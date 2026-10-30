"""Writer-only new seal; no old source manifest is regenerated."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import os
import yaml

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def load(name,file):
    s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def write():
    if os.environ.get('CI')or os.environ.get('GITHUB_ACTIONS')=='true':raise ValueError('DE_SKU_CI_CANNOT_RESEAL_SOURCE')
    a=load('de_sku_freeze_admission','admission.py');w=load('de_sku_freeze_workflow','workflow.py')
    if yaml.safe_load((ROOT/w.NEW).read_bytes())!=w.derive(yaml.safe_load((ROOT/w.OLD).read_bytes())):
        raise ValueError('DE_SKU_WORKFLOW_NOT_EXACT_TRANSITION')
    imports=a.imported();a.immutable_parent(imports);wf=a.pin((ROOT/w.NEW).read_bytes())
    for name in('GENERATED_RECEIPTS.json','LATER_GENERATED_RECEIPTS.json','SKU_GENERATED_RECEIPTS.json'):
        p=HERE/name;cfg=a.document(p.read_bytes());cfg['producer_files'][w.NEW]=wf
        if name=='LATER_GENERATED_RECEIPTS.json':cfg['package_workflow_name']=w.NAME
        p.write_text(json.dumps(cfg,indent=2)+'\n')
    paths={str(p.relative_to(ROOT))for p in HERE.rglob('*')if p.is_file()and p.name!='SOURCE.json'}|set(imports)|{w.NEW}
    files={}
    for name in sorted(paths):
        if '__pycache__'in name or name.endswith('.pyc'):raise ValueError('DE_SKU_BYTECODE_FREEZE_FORBIDDEN')
        p=a.regular(name);files[name]=dict(a.pin(p.read_bytes()),mode='100755'if p.stat().st_mode&0o111 else'100644')
    value=dict(base=a.BASE,classification='ACTUAL_PARENT_CATALOGUE_INSTALL_ONLY_PREPARATION',
        exact_public_import_head=a.IMPORTED,business_runtime_entry=None,actual_business_cases=0,
        actual_Native_cases=0,production_go=False,independent_acceptance=False,files=files,
        complete_engine_derivation=load('de_sku_freeze_deriver','derive.py').derive()[1])
    (HERE/'SOURCE.json').write_text(json.dumps(value,indent=2)+'\n')
    return a.preflight(require_clean=False)


if __name__=='__main__':print(json.dumps(write(),sort_keys=True))
