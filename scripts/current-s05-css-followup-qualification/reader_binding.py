"""One current reader CSS pin, preserving all historical manifests and SQL.

The active composed reader's source guard must see the exact reviewed CSS.
Its historical predecessor manifests are evidence and remain byte-identical.
All41 actual reader inputs are checked before importing the ERP graph.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='50c77207e088af16988d7d91a5b06f72e8e30ecc'
PATH='scripts/cp7_s05_s03_sku_composition/SOURCE.json'
CSS='src/accessory-standard-report.css'
ORIGINAL=dict(bytes=5351,sha256='344d0248e341826978e4aad76bb1c3311bba2e69ac87cb1ad07785c06df7c237')
BEFORE='a9d62618178521d25fa392e6497e24ebc1e8146277b9cda33a9d76e7ea76d16a'
AFTER='0ca870ad603a4654d44b4f9b8905f4e91c47d26ff45947d8017d17a1b8b3bcdf'

def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())

def derive(raw):
    if pin(raw)!=ORIGINAL:raise ValueError('FOCUSED_EXACT_ORIGINAL_CURRENT_READER_MANIFEST_REQUIRED')
    before=json.loads(raw)
    if len(before['files'])!=41 or before['files'].get(CSS)!=BEFORE:
        raise ValueError('FOCUSED_EXACT_CURRENT_READER_CSS_PIN_REQUIRED')
    a=json.dumps(CSS)+': '+json.dumps(BEFORE);b=json.dumps(CSS)+': '+json.dumps(AFTER)
    text=raw.decode()
    if text.count(a)!=1 or b in text:raise ValueError('FOCUSED_ONE_CURRENT_READER_CSS_PIN_ANCHOR_REQUIRED')
    text=text.replace(a,b,1)
    if text.count(b)!=1 or text.replace(b,a,1).encode()!=raw:
        raise ValueError('FOCUSED_CURRENT_READER_MANIFEST_EXACT_INVERSE_REQUIRED')
    after=json.loads(text)
    if {k:v for k,v in before.items()if k!='files'}!={k:v for k,v in after.items()if k!='files'}:
        raise ValueError('FOCUSED_READER_CONTRACT_METADATA_MUST_NOT_CHANGE')
    if {k:v for k,v in before['files'].items()if k!=CSS}!={k:v for k,v in after['files'].items()if k!=CSS}:
        raise ValueError('FOCUSED_ALL_OTHER_FORTY_READER_PINS_UNCHANGED')
    return text.encode(),dict(path=PATH,original=ORIGINAL,derived=pin(text.encode()),counted_changes=1,
        current_CSS_path=CSS,current_CSS_sha256=AFTER,other_reader_source_pins_unchanged=40,
        complete_original_recovered=True,historical_manifests_changed=False,reader_SQL_or_Native_changes=False)

def check_files(raw,read):
    pins=json.loads(raw)
    if pins['contract']!='cp7.s05-s03-sku-normal-app.v1'or len(pins['files'])!=41:
        raise ValueError('FOCUSED_EXACT_CURRENT_S05_READER_CONTRACT_REQUIRED')
    for name,digest in pins['files'].items():
        if sha256(read(name)).hexdigest()!=digest:raise ValueError('S05_SOURCE_CHANGED: '+name)
    return dict(actual_reader_inputs_checked=41,all_current_reader_source_pins_match=True)

def preflight():
    original=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',BASE+':'+PATH])
    expected,proof=derive(original)
    if (ROOT/PATH).read_bytes()!=expected:raise ValueError('FOCUSED_EXACT_REVIEWED_READER_MANIFEST_REQUIRED')
    checked=check_files(expected,lambda name:(ROOT/name).read_bytes())
    # Load only the original stdlib-only reader declaration, not its parent.
    path=ROOT/'scripts/cp7_s05_s03_sku_composition/stage.py'
    spec=importlib.util.spec_from_file_location('focused_actual_reader_function_declarations',path)
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    if len(reader.function_sources())!=5:raise ValueError('FOCUSED_EXACT_FIVE_READER_FUNCTION_SOURCES_REQUIRED')
    return dict(status='EXACT_CURRENT_READER_CSS_BINDING_AND_ALL41_INPUTS',**proof,**checked,
        reader_function_sources=5,actual_case_credit=0)
