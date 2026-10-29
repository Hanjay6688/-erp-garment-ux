"""Only pinned Native21 downloads and exact72 client output; no Native credit."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('sku_generated_common_safety',HERE/'generated_later.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
PREFIX='cp6-proof/t3/'


def admit(root,here,names):
    root,here,names=Path(root),Path(here),set(names)
    contract=json.loads((here/'SKU_GENERATED_RECEIPTS.json').read_bytes(),object_pairs_hook=g._object)
    assert contract['version']=='CLOSED_SKU_GENERATED_NON_SOURCE_V1'
    for name,pin in contract['producer_files'].items():
        raw=g.safe_file(root,name).read_bytes()
        assert len(raw)==pin['bytes']and sha256(raw).hexdigest()==pin['sha256'],'SKU_GENERATED_PRODUCER_CHANGED:'+name
    parent=json.loads((root/'scripts/current-sku-combined-followup-qualification/CONFIG.json').read_bytes())['accepted_native7']
    expected={parent[key]['name']:dict(bytes=parent[key]['bytes'],sha256=parent[key]['sha256'])for key in ('original','package')}
    expected['ORIGINAL.zip']=dict(bytes=parent['zip_bytes'],sha256=parent['zip_sha256'])
    fetch=(json.dumps(dict(status='EXACT_TERMINAL_RAW_BYTES_ACQUIRED_SOURCE_ADMISSION_STILL_REQUIRED',
        run_id=parent['run_id'],artifact_id=parent['artifact_id'],raw_pins=parent,actual_new_cases=0),indent=2)+'\n').encode()
    expected['FETCH_RECEIPT.json']=dict(bytes=len(fetch),sha256=sha256(fetch).hexdigest())
    assert g.same(contract['retained21_files'],expected),'SKU_GENERATED_NATIVE21_CONTRACT_DIFFERS_FROM_FROZEN_READER'
    accepted={}
    retained=PREFIX+'RETAINED_SKU21C/'
    selected={name for name in names if name.startswith(retained)}
    if selected:
        expected={retained+name for name in contract['retained21_files']}
        assert selected==expected,'SKU_GENERATED_NATIVE21_OUTPUT_SET'
        for name,pin in contract['retained21_files'].items():
            raw=g.raw_file(root,retained+name)
            assert len(raw)==pin['bytes']and sha256(raw).hexdigest()==pin['sha256'],'SKU_GENERATED_NATIVE21_BYTES_CHANGED:'+name
            accepted[retained+name]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    client=PREFIX+'SKU_TARGETED_CLIENT.json'
    if client in names:
        value=g.json_file(root,client)
        assert set(value)==set(contract['client_top_keys'])
        for key,expected in contract['client_fixed'].items():
            assert g.same(value[key],expected),'SKU_GENERATED_CLIENT_SUMMARY_CHANGED:'+key
        rows=value['testResults'];assert isinstance(rows,list)and len(rows)==8
        observed={}
        for row in rows:
            name=row['name'];assert isinstance(name,str)and '..'not in Path(name).parts
            matches=[path for path in contract['client_files']if name==path or name.endswith('/'+path)]
            assert len(matches)==1 and matches[0]not in observed,'SKU_GENERATED_CLIENT_PATH_SET'
            path=matches[0];assert row['status']=='passed'and row.get('message','')==''
            cases=row['assertionResults'];assert len(cases)==len(contract['client_files'][path])
            fixed=[]
            for case in cases:
                assert case['status']=='passed'and case.get('failureMessages')==[]
                fixed.append({key:case[key]for key in ('fullName','title','ancestorTitles')})
            assert g.same(fixed,contract['client_files'][path]),'SKU_GENERATED_CLIENT_ASSERTION_SET_CHANGED:'+path
            observed[path]=fixed
        assert set(observed)==set(contract['client_files'])
        raw=g.raw_file(root,client);accepted[client]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    return accepted,dict(classification='SKU_GENERATED_NON_SOURCE_OUTPUTS_ONLY',accepted=len(accepted),
        authoritative_Native21_reader_unchanged=True,client_scope='EXACT_ORIGINAL8_SRC_FILES_72_CASES',Native_credit=0)
