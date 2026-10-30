"""Explicit historical-source endpoints and actual public recovery product."""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import gzip
import importlib.util
import json
import subprocess
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
NS='scripts/current-sku-managed-recovery-native27-qualification'
BASE=PRODUCT_HEAD='f3d014648d12279dfa89ca8593f25585430a5efe'
TREE=PRODUCT_TREE='b1c316d6e853805f933a6665a81edf9332d12a36'
BRANCH='astra-a/sku-managed-recovery-native27-20261030'
WORKFLOW='.github/workflows/cp7-sku-managed-recovery-native27.yml'
SQL='scripts/cp7_sku_pair_conversion/conversion.sql'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

@contextmanager
def scoped_argv():
    prior=sys.argv;contents=list(prior);sys.argv=prior[:1]
    try:yield
    finally:prior[:]=contents;sys.argv=prior

def current_files():
    value=json.loads((ROOT/'scripts/current-sku-recovery-material-lock/evidence/UNPROJECTED_CURRENT_RUNTIME.json').read_bytes())
    assert value['status']=='PASS'and len(value['sku_business_leaves'])==10
    assert value['projected_sources']is False and value['forbidden_DB_network_attempts']==[]
    return value['sku_business_leaves']

def old_files():
    return json.loads((ROOT/'scripts/current-sku-pair-native-adapter/CONFIG.json').read_bytes())['runtime_files']

def historical_transition(name):
    return json.loads((HERE/'HISTORICAL_TRANSITIONS.json').read_bytes()).get(name)

def pin_for(name,pin):
    transition=historical_transition(name)
    if transition is None:return pin
    expected=pin['sha256']if isinstance(pin,dict)else pin
    assert expected==transition['old']['sha256'],('SKU27_UNREVIEWED_HISTORICAL_PRODUCT_PIN',name)
    digest=transition['current']['sha256']
    if isinstance(pin,dict):
        # Historical bytes are verified against the exact retained21 commit.
        old=subprocess.check_output(['git','-C',str(ROOT),'show','21c69cf25defcee854beb08e998062d7e883d968:'+name])
        assert len(old)==pin['bytes']and sha256(old).hexdigest()==expected
        return dict(pin,bytes=transition['current']['bytes'],sha256=digest)
    return digest

def verify_pin(root,name,pin):
    value=pin_for(name,pin);raw=(root/name).read_bytes()
    return(len(raw)==value['bytes']and sha256(raw).hexdigest()==value['sha256'])if isinstance(value,dict)else sha256(raw).hexdigest()==value

def historical_path(root,name,head):
    old=subprocess.check_output(['git','-C',str(root),'show',head+':'+name])
    transition=historical_transition(name)
    if transition is not None:
        assert sha256(old).hexdigest()==transition['old']['sha256'],('SKU27_HISTORICAL_PRODUCT_BYTES_CHANGED',name)
        return verify_pin(root,name,transition['old']['sha256'])
    return(root/name).read_bytes()==old

def runtime_files(prior):
    assert prior==old_files(),'SKU27_EXACT_RETAINED21_PRODUCT_SOURCE_REQUIRED'
    return current_files()

def historical_sources(product):
    raw=gzip.decompress((ROOT/'scripts/current-sku-combined-followup-qualification/retained21/CP7_SKU_PAIR_CONVERSION_NATIVE.json.gz').read_bytes())
    prior=json.loads(raw)['source_declaration']['current_installation'];assert prior['files']==old_files()
    actual=product.sources();expected=dict(prior,predecessor=product.parent().sources(),files=current_files())
    assert prior['predecessor']==actual['predecessor']==expected['predecessor'],'SKU27_PARENT_SOURCE_CHANGED'
    assert actual==expected,'SKU27_ACTUAL_PRODUCT_EXCEEDS_FROZEN_RECOVERY_SCOPE'
    assert len(product.CAPTURE_SIGNATURES)==8 and len(product.FUNCTIONS)==19 and len(product.TABLES)==5
    return prior  # Authentic old declaration for the unchanged old prerequisite only.

def source_receipt():
    return dict(product_source_commit=PRODUCT_HEAD,product_source_tree=PRODUCT_TREE,
      added_Native_captures=2,total_Native_captures=8,private_functions=19,private_tables=5,
      current_sources_are_actual=True,historical21_only_uses_authentic_retained_source=True,
      historical_preflight_source_pins=43,material_lock_transition_source_pins=20,
      exact_material_SQL_hunks=1,actual_successor_cases=0,group_recovery_supported=False)

def fresh_native7_sha(first):
    name='CP7_SKU_PAIR_CONVERSION_NATIVE7.json';raw=(ROOT/'cp6-proof/t3'/name).read_bytes();digest=sha256(raw).hexdigest()
    assert[p for p in first['strict_group_originals']if p['name']==name]==[dict(name=name,bytes=len(raw),sha256=digest)]
    assert json.loads(raw)==first['native'];return digest

def bc_at(fixture,seconds):
    return load('sku27_native_BC_clock',HERE/'recovery_cases.py').bc_at(fixture,seconds)

def native_admission(raw):
    return load('sku27_native_private_derivation',HERE/'derive.py').derive('native_admission',raw)
