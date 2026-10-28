"""Bind only after both exact raw prerequisites have been intaken and preserved."""
from hashlib import sha256
from pathlib import Path
import argparse
import importlib.util
import json
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def bind(args):
    assert not(HERE/'SOURCE.json').exists(),'SOURCE_ALREADY_BOUND'
    sys.path.insert(0,str(REPO/'scripts'))
    rows=json.loads(Path(args.bindings).read_bytes());proofs={};actuals={}
    for variable,row in rows.items():
        proof=json.loads(Path(row['proof']).read_bytes());raw=Path(row['original']).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        proofs[variable]=proof;actuals[variable]=json.loads(raw)
    evidence=load('public_native_binding_evidence',HERE/'evidence.py')
    for variable,path in((evidence.PRIVATE_VARIABLE,args.private_native_intake),(evidence.B_VARIABLE,args.B_facade_intake)):
        receipt=json.loads(Path(path).read_bytes());proof=proofs[variable]
        assert all(receipt.get(key)==value for key,value in proof.items())
        assert receipt['status']=='PASS'and receipt['cp6_restored']and receipt['advisor_gate']
        assert receipt['package_gate']==dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=True)
        assert receipt['production_go']is receipt['independent_acceptance']is False
        if variable==evidence.PRIVATE_VARIABLE:
            assert receipt['counts']=={'PASS':45}and receipt['source_pins_verified']==3644
            assert receipt['full22_all_rows_all_sequences_restored']
        else:
            assert receipt['counts']==dict(native=3,races=3,http=2)and receipt['source_pins_verified']==90
            assert receipt['B_delegate_sha256']=='cbfb6ee4cbe165221c3bcab18750547f0b4952224e5ed7e5e0f2cbcd42ebd7c4'
            assert receipt['full_boundary_and_sessions_restored']and receipt['B_actual_Auth_HTTP_credit']
            assert receipt['new_A_Auth_HTTP_credit']is False
    sys.argv=sys.argv[:1];sys.path[:0]=[str(HERE),str(REPO/'scripts')]
    native=load('public_native_binding_real_graph',HERE/'probe.py')
    verified=evidence.validate(REPO,HERE,proofs,actuals,native.product)
    native.business.source_binding()
    old_path=REPO/'scripts/current-frozen-finance-native-qualification/SOURCE.json'
    old=json.loads(old_path.read_bytes());files=dict(old['files'])
    for path,digest in files.items():assert sha256((REPO/path).read_bytes()).hexdigest()==digest,path
    added=[old_path,REPO/'scripts/cp7_current_frozen_public_installation.py',
        REPO/'scripts/cp7_current_frozen_public_source_check.py',REPO/'.github/workflows/cp7-current-frozen-public-native.yml']
    for directory in(REPO/'scripts/cp7_current_frozen_public',HERE,
            REPO/'docs/cp7/d17-14/ow15/frozen-public-integration'):
        added.extend(path for path in directory.iterdir()if path.is_file()and path.name!='SOURCE.json')
    for path in added:files[str(path.relative_to(REPO))]=sha256(path.read_bytes()).hexdigest()
    pins=dict(contract='cp7.current-frozen-public-finance-native52-qualification.v1',
        files=dict(sorted(files.items())),case_ids=list(native.IDS),
        retained_declaration_sha256=sha256(old_path.read_bytes()).hexdigest(),
        actual_qualification_originals=proofs,production_go=False,independent_acceptance=False)
    with(HERE/'SOURCE.json').open('x')as out:out.write(json.dumps(pins,indent=2)+'\n')
    print(json.dumps(dict(status='SOURCE_BOUND_ACTUAL_PRIVATE45_AND_B_FACADE8',source_pins=len(files),
        actual_prerequisites=len(verified),case_count=52,production_go=False)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in('bindings','private-native-intake','B-facade-intake'):parser.add_argument('--'+name,required=True)
    bind(parser.parse_args())
