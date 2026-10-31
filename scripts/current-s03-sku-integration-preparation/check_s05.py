"""Source binding and pure transition refusal controls; no install or SQL."""
from hashlib import sha256
from pathlib import Path
import argparse,ast,importlib,importlib.util,json,sys,zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
STAGE=ROOT/'scripts/cp7_s05_s03_sku_composition'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def check(archive):
    pins=json.loads((STAGE/'SOURCE.json').read_bytes())
    if(pins['contract']!='cp7.s05-s03-sku-normal-app.v1'
       or pins['actual_current_composite_cases']!=0
       or pins['production_go']is not False or pins['independent_acceptance']is not False):
        raise ValueError('JOIN_S05_PREPARATION_ONLY_REQUIRED')
    for name,digest in pins['files'].items():
        path=ROOT/name
        if path.is_symlink()or not path.resolve().is_relative_to(ROOT)or sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('JOIN_S05_SOURCE_CHANGED: '+name)
    delta=json.loads((STAGE/'SOURCE_TRANSITION.json').read_bytes())
    old=(ROOT/delta['original_path']).read_bytes();new=(STAGE/'stage.py').read_bytes()
    if sha256(old).hexdigest()!=delta['original_sha256']or sha256(new).hexdigest()!=delta['derived_sha256']:
        raise ValueError('JOIN_S05_DERIVATION_SOURCE_CHANGED')
    derived=old.decode()
    for row in delta['changes']:
        if row['count']!=1 or derived.count(row['before'])!=1:raise ValueError('JOIN_S05_EXACT_ANCHOR_REQUIRED')
        derived=derived.replace(row['before'],row['after'],1)
    if derived.encode()!=new:raise ValueError('JOIN_S05_UNDECLARED_STAGE_CHANGE')
    for row in reversed(delta['changes']):
        if derived.count(row['after'])!=1:raise ValueError('JOIN_S05_EXACT_REVERSE_REQUIRED')
        derived=derived.replace(row['after'],row['before'],1)
    if derived.encode()!=old:raise ValueError('JOIN_S05_REVERSE_MUST_RECOVER_ORIGINAL')
    functions=lambda raw:{n.name:ast.dump(n)for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    before,after=functions(old),functions(new)
    if before.keys()!=after.keys()or{k for k in before if before[k]!=after[k]}!={'parent','sources','verify'}:
        raise ValueError('JOIN_S05_UNDECLARED_FUNCTION_BODY_CHANGE')
    # Reading a failed Original supplies a real old catalog as a negative-
    # control input. Additions below are explicitly synthetic unit fixtures;
    # they are never emitted as an installed catalog or runtime proof.
    raw=archive.read_bytes()
    if len(raw)!=94787144 or sha256(raw).hexdigest()!='06d8605b40b05c62b6a9cc7115444560f403d6c1844aa114e901e76a26ac9ac0':
        raise ValueError('JOIN_S05_EXACT_RECORDED_PARENT_ORIGINAL_REQUIRED')
    del raw
    with zipfile.ZipFile(archive)as z:main=json.loads(z.read('CP7_SKU_MANAGED_RECOVERY_NATIVE27.json'))
    if main['status']!='INCOMPLETE':raise ValueError('JOIN_S05_FAILED_PARENT_MUST_REMAIN_FAILED')
    catalog=next(iter(main['committed'].values()))['Native_to_copy_handoff']['raw_current_catalog']
    guard_module=load('join_s05_source_fence',ROOT/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    saved=sys.argv
    try:
        sys.argv=sys.argv[:1];sys.path.insert(0,str(ROOT/'scripts'))
        with guard_module.fenced_source_read()as guard:
            reader=importlib.import_module('cp7_s05_s03_sku_composition.stage')
            product=importlib.import_module('cp7_s03_sku_composition.composition')
            sku=importlib.import_module('cp7_sku_pair_conversion.composition')
            if reader.parent()is not product or product.parent()is not sku:
                raise ValueError('JOIN_S05_NATURAL_S03_SKU_IMPORT_CHAIN_REQUIRED')
            if len(reader.function_sources())!=5:raise ValueError('JOIN_S05_EXACT_UNCHANGED_REPORT_SQL_REQUIRED')
            added={group:dict(rows)for group,rows in catalog.items()}
            marker={'source_control_only_not_installed':True}
            if reader.SCHEMA in added['schemas']or reader.ROLE in added['roles']or set(reader.FUNCTIONS)&set(added['functions']):
                raise ValueError('JOIN_S05_RECORDED_CONTROL_PARENT_ALREADY_HAS_READER')
            added['schemas'][reader.SCHEMA]=marker;added['roles'][reader.ROLE]=marker
            added['functions'].update({name:marker for name in reader.FUNCTIONS})
            reader.transition(catalog,added)
            denied=[]
            def refusal(name,changed):
                try:reader.transition(catalog,changed)
                except ValueError as error:
                    if not str(error).startswith(('S05_UNDECLARED_CATALOG_DELTA:','S05_EXACT_FUNCTION_SET_REQUIRED','S05_ALL22_REQUIRED')):raise
                    denied.append(name)
                else:raise ValueError('JOIN_S05_TRANSITION_CONTROL_DID_NOT_REFUSE: '+name)
            for name in (*product.native_delta.SIGNATURES,*sku.CAPTURE_SIGNATURES):
                changed={group:dict(rows)for group,rows in added.items()}
                changed['functions'][name]=marker
                refusal('changed_parent_function:'+name,changed)
            for label,group,key,value in (
                ('removed_existing_function','functions',product.native_delta.SIGNATURES[0],None),
                ('extra_private_function','functions','cp7_accessory_standard_report.extra()',marker),
                ('extra_parent_role','roles','cp7_unreviewed_writer',marker),
                ('extra_table','relations','erp.unreviewed_business_table',marker),
                ('extra_trigger','triggers','erp.unreviewed_business_table:unreviewed',marker),
                ('missing_report_function','functions',reader.PUBLIC,None),
            ):
                changed={name:dict(rows)for name,rows in added.items()}
                if value is None:del changed[group][key]
                else:changed[group][key]=value
                refusal(label,changed)
            missing=dict(added);del missing['functions'];refusal('missing_catalog_group',missing)
    finally:sys.argv=saved
    return dict(status='S05_ON_S03_SKU_SOURCE_AND_PURE_TRANSITION_CONTROLS_PASS_NOT_RUNTIME',
        pinned_source_files=len(pins['files']),reversible_stage_changes=4,
        unchanged_complete_stage_functions=len(before)-3,unchanged_report_SQL_functions=5,
        source_import_chain=['cp7_s05_s03_sku_composition','cp7_s03_sku_composition','cp7_sku_pair_conversion'],
        transition_unit_fixture_admitted=True,transition_unit_fixture_is_actual_installation=False,
        transition_negative_controls=denied,negative_controls_passed=len(denied),source_DB_guard=guard,
        complete_product_sources_evaluated=False,actual_Native_cases=0,actual_browser_cases=0,
        actual_composite_install_qualified=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--sku-archive',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(check(args.sku_archive),indent=2))
