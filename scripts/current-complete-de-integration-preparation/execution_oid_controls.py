"""Pure and cursor-protocol controls against the saved disposable PG17 model."""
from pathlib import Path
from types import SimpleNamespace
from copy import deepcopy
from hashlib import sha256
import argparse
import importlib.util
import json

HERE = Path(__file__).resolve().parent


def controls(path):
    spec=importlib.util.spec_from_file_location('DE_exact_execution_ids',HERE/'execution_oids.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    raw=Path(path).read_bytes();model=json.loads(raw)
    declaration_raw=(HERE/'EXECUTION_OID_QUERIES.json').read_bytes();declaration=json.loads(declaration_raw)
    assert model['declaration_sha256']==sha256(declaration_raw).hexdigest()
    assert model['classification']=='DISPOSABLE_POSTGRESQL17_METADATA_MODEL_NOT_ERP'
    assert model['provider_functions_invoked']==model['actual_ERP_calls']==model['actual_Native_case_credit']==0
    assert model['version'].startswith('17.')
    schema=declaration['groups'];groups=model['groups'];original=model['original_groups']
    counts=module.validate(groups,schema,original)
    negatives=[]

    def refusal(label,changed,base=original):
        try:module.validate(changed,schema,base)
        except (ValueError,KeyError,TypeError):negatives.append(label)
        else:raise AssertionError('MODEL_NOT_REFUSED:'+label)

    for name in schema:
        changed=deepcopy(groups);changed.pop(name);refusal('missing:'+name,changed)
    changed=deepcopy(groups);changed['unexpected']=[];refusal('additional-group',changed)
    for value in (1,True,-1,'01','-1','١','4294967296','not-an-oid'):
        changed=deepcopy(groups);changed['operator_routine_oids'][0]['oprcode']=value
        refusal('noncanonical:'+repr(value),changed)
    for label,change in (
        ('duplicate',lambda rows:rows.append(dict(rows[0]))),
        ('missing-original-member',lambda rows:rows.pop()),
        ('unknown-routine',lambda rows:rows[0].update(oprcode='4294967295')),
        ('extra-column',lambda rows:rows[0].update(not_a_column='1'))):
        changed=deepcopy(groups);change(changed['operator_routine_oids']);refusal(label,changed)
    for value in ('0','4294967295'):
        changed=deepcopy(groups);changed['range_execution_oids'][0]['rngsubtype']=value
        refusal('invalid-range-type:'+value,changed)
    changed=deepcopy(groups);changed['transform_execution_oids']=[dict(
        oid='4294967295',trftype=str(original['types']['rows'][0]['oid']),
        trflang='4294967295',trffromsql='0',trftosql='0')]
    refusal('unknown-transform-language',changed)
    badbase=deepcopy(original);badbase['routines']['rows'].append(badbase['routines']['rows'][0])
    refusal('duplicate-original-routine',groups,badbase)

    base=dict(classification='ACTUAL_READ_ONLY_ALL_NAMESPACE_SYSTEM_CRON_METADATA_NOT_WRITER_CLOSURE',
        database='cp6_rollback',current_role='postgres',session_role='postgres',snapshot='1:2:',groups=original)
    snapshot=('cp6_rollback','postgres','postgres','on','repeatable read','1:2:','pg_catalog')
    query_names={row['query']:name for name,row in schema.items()}
    class Cursor:
        def __init__(self,fail_at=None):
            self.connection=SimpleNamespace(autocommit=False,info=SimpleNamespace(host='127.0.0.1',port=54322))
            self.fail_at=fail_at;self.snapshots=0;self.reads=[]
        def execute(self,sql):
            if sql in query_names:
                self.reads.append(query_names[sql]);self.row=(groups[query_names[sql]],)
            else:
                self.snapshots+=1;self.row=snapshot
                if self.snapshots==self.fail_at:self.row=tuple('changed' if i==5 else x for i,x in enumerate(snapshot))
            return self
        def fetchone(self):return self.row
    before=deepcopy(base);cursor=Cursor();observed=module.capture(cursor,base)
    assert cursor.reads==list(schema) and observed['same_original_readonly_snapshot']is True and base==before
    for fail_at in (1,2):
        cursor=Cursor(fail_at)
        try:module.capture(cursor,base)
        except ValueError as error:assert 'SNAPSHOT_CHANGED'in str(error)
        else:raise AssertionError('changed snapshot accepted')
        assert len(cursor.reads)==(0 if fail_at==1 else 4)
    return dict(status='PASS_PG17_EXACT_OIDS_AND_CLOSED_CURSOR_PROTOCOL_MODELS',
        input_model=dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),query_counts=counts,
        actual_model_queries=4,provider_functions_invoked=0,positive_model=1,
        negative_models=negatives,snapshot_protocol_controls=3,
        original_27_groups_rewritten=False,actual_ERP_calls=0,actual_Native_case_credit=0,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=controls(args.model);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],positive_model=result['positive_model'],
        negative_models=len(result['negative_models']),snapshot_protocol_controls=3,actual_ERP_calls=0)))
