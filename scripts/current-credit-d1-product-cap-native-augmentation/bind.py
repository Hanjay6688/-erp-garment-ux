"""Writer-only metadata freeze. No DB, Native, remote or original-file edits."""
from pathlib import Path
from hashlib import sha256
import ast
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def bind():
    api=json.loads((HERE/'API.json').read_bytes())
    case_text=(ROOT/api['modules']['retained']['path']).read_text()
    nodes=ast.parse(case_text).body
    ids=next(ast.literal_eval(n.value)for n in nodes if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name)and t.id=='IDS'for t in n.targets))
    assert len(ids)==len(set(ids))==13
    owning=ROOT/'scripts/cp7_credit_correction_de/owning.sql';text=owning.read_text()
    start=text.index('create function cp7_credit_correction_de.quote_v1(')
    tail=text[start:];body=tail[tail.index('$$')+2:tail.index('$$;',tail.index('$$')+2)]
    assert 'refund_product_cap_basis' in body
    files={pin['path']for pin in api['modules'].values()}
    files.add(str(owning.relative_to(ROOT)))
    # Directly used immutable journal/read-data definitions, not another
    # product installer or an exception to the outer source/census gate.
    files.add('scripts/cp7_customer_credit/readers/02_materialized_profile.proposal.sql')
    files.update(str(p.relative_to(ROOT))for p in HERE.rglob('*')if p.is_file()
        and p.name!='SOURCE.json'and '__pycache__'not in p.parts and p.suffix!='.pyc')
    pins={}
    for name in sorted(files):
        raw=(ROOT/name).read_bytes();pins[name]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    value=dict(status='PREPARED_NATIVE_AUGMENTATION_NOT_EXECUTED',
        contract='cp7.credit-d1-product-cap-native-augmentation.v1',
        original_Native13_ids=list(ids),augmented_id='D_MULTIFAMILY_ORDINAL',
        original_callback_sha256=api['modules']['retained']['sha256'],
        files=pins,required_quote_body_sha256=sha256(body.encode()).hexdigest(),
        entrypoint='scripts/current-credit-d1-product-cap-native-augmentation/factory.py::business(retained_business_module)',
        private_proxy_overrides=['cases'],old_function_bodies_changed=0,old_assertions_removed=0,
        other12_callback_identities_preserved=True,Native_executed=False,
        outer_combined_product_source_and_full13_strict_group_and_package_gates_required=True,
        independent_acceptance=False,production_go=False)
    (HERE/'SOURCE.json').write_text(json.dumps(value,indent=2)+'\n')
    return dict(status=value['status'],files=len(pins),api_modules=len(api['modules']),api_function_bodies=len(api['functions']))


if __name__=='__main__':
    assert sys.argv[1:]==['--writer-freeze'],'D1_CAP_NATIVE_BINDER_NOT_RUNTIME'
    print(json.dumps(bind()))
