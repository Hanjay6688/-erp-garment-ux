"""Bind Native45 only after the actual full Native40 Original was intaken PASS."""
from hashlib import sha256
from pathlib import Path
import argparse
import importlib.util
import json
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
PARENT='8de2ae694c6eda60a6724415eb60772c4f7a20b2'
VARIABLE='CURRENT_FROZEN_UNITS_NATIVE_ORIGINAL_REPORT'


def bind(args):
    original=Path(args.original).read_bytes()
    proof=json.loads(Path(args.proof).read_bytes())
    intake=json.loads(Path(args.intake).read_bytes())
    assert len(original)==proof['bytes']and sha256(original).hexdigest()==proof['sha256']
    assert all(intake.get(k)==v for k,v in proof.items())
    assert intake['status']==proof['status']=='PASS'and proof['head']==PARENT
    assert intake['counts']=={'PASS':40}and intake['source_pins_verified']==3618
    assert intake['actual_prerequisites_verified']==4
    assert intake['cp6_restored']and intake['advisor_gate']and intake['full22_all_rows_all_sequences_restored']
    assert intake['package_gate']==dict(installed=True,primary_unchanged=True,
        backup_restore_drill=True,security_advisors=True,writer_runtime=True)
    assert intake['production_go']is intake['independent_acceptance']is False
    actual=json.loads(original)
    assert actual['label']=='CP7_CURRENT_FROZEN_UNITS_NATIVE40'
    assert actual['qualification_commit']==PARENT and actual['status']=='PASS'
    assert actual['required_case_ids_pass']and actual['native']['counts']=={'PASS':40}
    old_path=REPO/'scripts/current-frozen-units-native-qualification/SOURCE.json'
    old=json.loads(old_path.read_bytes())
    assert actual['source_declaration']['qualification']==old
    assert actual['required_case_ids']==old['case_ids']
    assert set(actual['native']['cases'])==set(old['case_ids'])
    for row in actual['native']['cases'].values():
        assert row['status']=='PASS'and row['full_boundary_restored']and row['public_schema_unchanged']
    # Import the complete real module graph without executing any case or DB.
    sys.argv=sys.argv[:1];sys.path.insert(0,str(REPO/'scripts'))
    spec=importlib.util.spec_from_file_location('frozen_finance_binding_graph',HERE/'probe.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert actual['source_declaration']['current_installation']==module.product.predecessor.sources()
    module.business.source_binding()
    files=dict(old['files'])
    for path,digest in files.items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,path
    added=[old_path,REPO/'scripts/cp7_current_frozen_finance_installation.py',
        REPO/'scripts/cp7_current_frozen_finance_source_check.py',
        REPO/'.github/workflows/cp7-current-frozen-finance-native.yml']
    for directory in(REPO/'scripts/cp7_current_frozen_finance',HERE,
                     REPO/'docs/cp7/d17-14/ow15/frozen-finance-integration'):
        added.extend(p for p in directory.iterdir()if p.is_file()and p.name!='SOURCE.json')
    for path in added:
        files[str(path.relative_to(REPO))]=sha256(path.read_bytes()).hexdigest()
    pins=dict(contract='cp7.current-frozen-finance-native45-qualification.v1',
        files=dict(sorted(files.items())),case_ids=list(module.IDS),
        retained_declaration_sha256=sha256(old_path.read_bytes()).hexdigest(),
        actual_qualification_originals={VARIABLE:proof},production_go=False,independent_acceptance=False)
    with(HERE/'SOURCE.json').open('x')as output:
        output.write(json.dumps(pins,indent=2)+'\n')
    print(json.dumps(dict(status='BOUND_ACTUAL_NATIVE40_ONLY',source_pins=len(files),
        case_count=45,prerequisite_head=PARENT,actual_run=proof['run_id'],production_go=False)))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in('original','proof','intake'):parser.add_argument('--'+name,required=True)
    bind(parser.parse_args())
