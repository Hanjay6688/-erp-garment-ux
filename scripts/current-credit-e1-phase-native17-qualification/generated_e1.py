"""Exact qualified D1 download outputs and unchanged D1/E client reports only."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json

HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('e_phase_generated_safe_types',HERE/'generated_later.py')
g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
PREFIX='cp6-proof/t3/'


def streamed_pin(root,name):
    path=g.safe_file(root,name)
    assert path.stat().st_size<=512*1024*1024,'E_GENERATED_FILE_SIZE_BOUND'
    digest=sha256()
    with path.open('rb')as stream:
        for chunk in iter(lambda:stream.read(65536),b''):digest.update(chunk)
    return dict(bytes=path.stat().st_size,sha256=digest.hexdigest())


def admit(root,here,names):
    root,here,names=Path(root),Path(here),set(names)
    contract=json.loads((here/'E1_GENERATED_RECEIPTS.json').read_bytes(),object_pairs_hook=g._object)
    assert contract['version']=='CLOSED_E1_GENERATED_NON_SOURCE_V1'
    for name,pin in contract['producer_files'].items():
        assert g.same(streamed_pin(root,name),pin),'E_GENERATED_PRODUCER_CHANGED:'+name
    cfg=json.loads((here/'CONFIG.json').read_bytes(),object_pairs_hook=g._object)
    parent=cfg['accepted_D1']
    expected={parent[key]['name']:dict(bytes=parent[key]['bytes'],sha256=parent[key]['sha256'])for key in contract['retained_parent_keys']}
    expected['ORIGINAL.zip']=dict(bytes=parent['zip_bytes'],sha256=parent['zip_sha256'])
    fetch=(json.dumps(dict(status='EXACT_TERMINAL_PARENT_RAW_BYTES_ACQUIRED_FULL_SOURCE_ADMISSION_STILL_REQUIRED',
        parent_head=parent['head'],run_id=parent['run_id'],job_id=parent['job_id'],artifact_id=parent['artifact_id'],raw_pins=parent,
        fresh_E_case_credit=0,production_go=False),indent=2)+'\n').encode()
    expected['FETCH_RECEIPT.json']=dict(bytes=len(fetch),sha256=sha256(fetch).hexdigest())
    accepted={};retained=PREFIX+'RETAINED_E1_D1/'
    selected={name for name in names if name.startswith(retained)}
    if selected:
        assert selected=={retained+name for name in expected},'E_GENERATED_PARENT_OUTPUT_SET'
        for name,pin in expected.items():
            observed=streamed_pin(root,retained+name)
            assert g.same(observed,pin),'E_GENERATED_PARENT_RAW_BYTES_CHANGED:'+name
            accepted[retained+name]=observed
    for basename,client in contract['clients'].items():
        relative=PREFIX+basename
        if relative not in names:continue
        value=g.json_file(root,relative)
        assert set(value)==set(client['top_keys']),'E_GENERATED_CLIENT_KEYS'
        assert type(value['startTime'])is int and value['startTime']>0,'E_GENERATED_CLIENT_TIME'
        for key,expected in client['fixed'].items():
            assert g.same(value[key],expected),'E_GENERATED_CLIENT_SUMMARY_CHANGED:'+key
        rows=value['testResults'];assert type(rows)is list and len(rows)==len(client['files'])
        observed={}
        for row in rows:
            name=row['name'];assert type(name)is str and '..'not in Path(name).parts
            matches=[path for path in client['files']if name==path or name.endswith('/'+path)]
            assert len(matches)==1 and matches[0]not in observed,'E_GENERATED_CLIENT_SOURCE_SET'
            path=matches[0];assert row['status']=='passed'and row.get('message','')==''
            cases=row['assertionResults'];assert len(cases)==len(client['files'][path])
            actual=[]
            for case in cases:
                assert case['status']=='passed'and case.get('failureMessages')==[],'E_GENERATED_CLIENT_CASE_FAILURE'
                actual.append({key:case[key]for key in ('fullName','title','ancestorTitles')})
            assert g.same(actual,client['files'][path]),'E_GENERATED_CLIENT_ASSERTION_SET_CHANGED'
            observed[path]=actual
        assert set(observed)==set(client['files'])
        accepted[relative]=streamed_pin(root,relative)
    return accepted,dict(classification='E1_SOURCE_BOUND_GENERATED_OUTPUTS_ONLY',accepted=len(accepted),
        retained_parent_raw_count=5,unchanged_client_cases={'D1':20,'E1':111},Native_credit=0)
