"""Saved PG17 dispatch identities and same-snapshot cursor controls; no ERP."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import argparse,importlib.util,json

HERE=Path(__file__).resolve().parent


def check(path):
    spec=importlib.util.spec_from_file_location('DE_dispatch_oid_controls_target',HERE/'dispatch_oids.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    raw=path.read_bytes();model=json.loads(raw)
    declaration_raw=(HERE/'DISPATCH_OID_QUERIES.json').read_bytes();declaration=json.loads(declaration_raw)
    assert model['classification']=='DISPOSABLE_POSTGRESQL17_DISPATCH_MODEL_NOT_ERP'
    assert model['version'].startswith('17.')
    assert model['declaration_sha256']==sha256(declaration_raw).hexdigest()
    assert model['actual_ERP_calls']==model['actual_Native_case_credit']==model['provider_functions_invoked']==0
    groups=model['groups'];schema=declaration['groups'];original=model['original_groups'];execution=model['execution_groups']
    counts=module.validate(groups,schema,original,execution);negative=[]
    def refuses(label,change):
        data=deepcopy(dict(groups=groups,original=original,execution=execution));change(data)
        try:module.validate(data['groups'],schema,data['original'],data['execution'])
        except (ValueError,KeyError,TypeError):negative.append(label)
        else:raise AssertionError('INVALID_DISPATCH_METADATA_ACCEPTED:'+label)
    for name in schema:refuses('missing:'+name,lambda d,n=name:d['groups'].pop(n))
    refuses('extra-group',lambda d:d['groups'].update(unexpected=[]))
    for value in(1,True,'01','-1','١','4294967296','public.metadata_probe_transition'):
        refuses('noncanonical:'+repr(value),lambda d,v=value:d['groups']['aggregate_support_oids'][0].update(aggtransfn=v))
    for value in(False,0,-1,32768,'1'):
        refuses('invalid-support-number:'+repr(value),lambda d,v=value:d['groups']['family_support_oids'][0].update(amprocnum=v))
    refuses('duplicate-row',lambda d:d['groups']['access_method_oids'].append(deepcopy(d['groups']['access_method_oids'][0])))
    refuses('unknown-handler',lambda d:d['groups']['access_method_oids'][0].update(amhandler='4294967295'))
    refuses('invalid-method-type',lambda d:d['groups']['access_method_oids'][0].update(amtype='x'))
    refuses('missing-original-routine',lambda d:d['groups']['routine_support_oids'].pop())
    refuses('missing-original-aggregate',lambda d:d['groups']['aggregate_support_oids'].pop())
    refuses('range-class-missing',lambda d:d['execution']['range_execution_oids'][0].update(rngsubopc='4294967295'))
    refuses('relation-method-missing',lambda d:d['original']['relations']['rows'][0].update(relam=4294967295))
    refuses('unknown-operator',lambda d:d['groups']['family_operator_oids'][0].update(amopopr='4294967295'))
    def wrong_method(data):
        row=data['groups']['operator_class_oids'][0]
        row['opcmethod']=next(r['oid']for r in data['groups']['access_method_oids']if r['oid']!=row['opcmethod'])
    refuses('operator-class-family-method-mismatch',wrong_method)
    base=dict(classification='ACTUAL_READ_ONLY_ALL_NAMESPACE_SYSTEM_CRON_METADATA_NOT_WRITER_CLOSURE',
        database='cp6_rollback',current_role='postgres',session_role='postgres',snapshot='1:2:',
        groups=original,execution_oid_supplement=dict(groups=execution))
    identity=('cp6_rollback','postgres','postgres','on','repeatable read','1:2:','pg_catalog')
    query_names={row['query']:name for name,row in schema.items()}
    class Cursor:
        def __init__(self,fail_at=None):
            self.connection=SimpleNamespace(autocommit=False,info=SimpleNamespace(host='127.0.0.1',port=54322))
            self.fail_at=fail_at;self.snapshots=0;self.reads=[]
        def execute(self,sql):
            if sql in query_names:
                self.reads.append(query_names[sql]);self.row=(groups[query_names[sql]],)
            else:
                self.snapshots+=1;self.row=identity
                if self.snapshots==self.fail_at:self.row=tuple('changed'if i==5 else x for i,x in enumerate(identity))
            return self
        def fetchone(self):return self.row
    before=deepcopy(base);cursor=Cursor();observed=module.capture(cursor,base)
    assert cursor.reads==list(schema)and observed['same_original_readonly_snapshot']is True and base==before
    for fail_at in(1,2):
        cursor=Cursor(fail_at)
        try:module.capture(cursor,base)
        except ValueError as error:assert 'SNAPSHOT_CHANGED'in str(error)
        else:raise AssertionError('DISPATCH_CHANGED_SNAPSHOT_ACCEPTED')
        assert len(cursor.reads)==(0 if fail_at==1 else 7)
    return dict(status='PASS_PG17_DISPATCH_OIDS_AND_CLOSED_CURSOR_PROTOCOL_MODELS',
        input_model=dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),query_counts=counts,
        actual_model_queries=7,positive_saved_model=1,negative_controls=negative,snapshot_protocol_controls=3,
        model_counterexample=model['counterexample'],provider_functions_invoked=0,
        original_27_queries_rewritten=False,original_four_execution_queries_rewritten=False,
        actual_ERP_calls=0,actual_Native_case_credit=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=check(a.model)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],positive=1,negative=len(result['negative_controls']),
        snapshots=3,actual_ERP_calls=0)))
