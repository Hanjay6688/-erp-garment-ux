"""Validate saved actual catalog-query model; never repeat SQL or ERP cases."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import argparse,importlib.util,json

HERE=Path(__file__).resolve().parent


def check(model_path):
    raw=model_path.read_bytes();model=json.loads(raw)
    spec=importlib.util.spec_from_file_location('owning_P0_privilege_target',HERE/'p0_privileges.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    declaration=json.loads((HERE/'P0_PRIVILEGE_QUERIES.json').read_bytes())
    assert model['declaration_sha256']==sha256((HERE/'P0_PRIVILEGE_QUERIES.json').read_bytes()).hexdigest()
    assert model['provider_functions_invoked']==0 and model['actual_ERP_calls']==0
    base=model['base'];selected=model['selected'];groups=model['groups']
    counts=m.validate(groups,declaration,base,selected);negative=[]
    def refusal(label,change):
        g,b,s=deepcopy((groups,base,selected));change(g,b,s)
        try:m.validate(g,declaration,b,s)
        except (ValueError,KeyError,TypeError):negative.append(label)
        else:raise AssertionError('P0_PRIVILEGE_INVALID_FACT_ACCEPTED:'+label)
    refusal('missing-group',lambda g,b,s:g.pop('tables'))
    refusal('missing-role-function',lambda g,b,s:g['functions'].pop())
    refusal('missing-role-table',lambda g,b,s:g['tables'].pop())
    refusal('missing-column-privilege',lambda g,b,s:g['column_privileges'].pop())
    refusal('omitted-physical-column',lambda g,b,s:g['columns'].pop())
    refusal('duplicate-function',lambda g,b,s:g['functions'].append(deepcopy(g['functions'][0])))
    refusal('duplicate-column',lambda g,b,s:g['columns'].append(deepcopy(g['columns'][0])))
    refusal('integer-boolean',lambda g,b,s:g['functions'][0].update(execute=1))
    refusal('unknown-field',lambda g,b,s:g['tables'][0].update(assumed_allowed=True))
    refusal('bad-oid',lambda g,b,s:g['functions'][0].update(function_oid='01'))
    refusal('wrong-schema-oid',lambda g,b,s:g['tables'][0].update(schema_oid='999999'))
    refusal('unknown-role-oid',lambda g,b,s:g['functions'][0].update(role_oid='999999'))
    refusal('boolean-attnum',lambda g,b,s:g['columns'][0].update(attnum=True))
    refusal('string-acl',lambda g,b,s:g['columns'][0].update(attacl='{}'))
    refusal('missing-base-role',lambda g,b,s:b['groups']['roles']['rows'].pop())
    refusal('duplicate-base-role',lambda g,b,s:b['groups']['roles']['rows'].append(deepcopy(b['groups']['roles']['rows'][0])))
    refusal('missing-base-schema',lambda g,b,s:b['groups']['schemas']['rows'].clear())
    refusal('missing-selected-function',lambda g,b,s:s['functions'].pop(next(iter(s['functions']))))
    refusal('wrong-database',lambda g,b,s:b.update(database='postgres'))
    refusal('primary-marker',lambda g,b,s:b.update(primary_scheduler_database=True))
    refusal('unsupported-major-version',lambda g,b,s:b.update(server_version_num='160000'))
    base=deepcopy(base);base['P0_dependency_supplement']={'selected':selected}
    identity=(base['database'],base['current_role'],base['session_role'],'on','repeatable read',base['snapshot'],'pg_catalog')
    params={'roles':sorted((str(r['oid'])for r in base['groups']['roles']['rows']),key=int),
        'functions':sorted((str(r['oid'])for r in selected['functions'].values()),key=int),
        'relations':sorted((str(r['oid'])for r in selected['relations'].values()),key=int)}
    class Cursor:
        def __init__(self,changed=None):
            self.connection=SimpleNamespace(autocommit=False,info=SimpleNamespace(host='localhost',port=54322))
            self.identities=0;self.queries=[];self.changed=changed
        def execute(self,sql,args=None):
            if args is None:
                self.identities+=1;row=identity
                if self.identities==self.changed:row=identity[:-2]+('changed:','pg_catalog')
            else:
                name=next(k for k,v in declaration['groups'].items()if v['query']==sql)
                assert args==tuple(params[k]for k in declaration['groups'][name]['parameters'])
                self.queries.append(name);row=(groups[name],)
            return SimpleNamespace(fetchone=lambda:row)
    cursor=Cursor();observed=m.capture(cursor,base)
    assert observed['groups']==groups and observed['group_counts']==counts
    assert cursor.queries==list(declaration['groups']) and cursor.identities==2
    snapshot_controls=[]
    for boundary in (1,2):
        cursor=Cursor(boundary)
        try:m.capture(cursor,base)
        except ValueError as error:
            assert str(error)=='P0_PRIVILEGE_SNAPSHOT_CHANGED_'+('BEFORE_READ'if boundary==1 else'AFTER_READ')
            assert len(cursor.queries)==(0 if boundary==1 else 4)
            snapshot_controls.append(str(error))
        else:raise AssertionError('SNAPSHOT_CHANGE_ACCEPTED')
    cursor=Cursor();cursor.connection.autocommit=True
    try:m.capture(cursor,base)
    except ValueError as error:
        assert str(error)=='P0_PRIVILEGE_EXISTING_LOCAL_READONLY_CURSOR_REQUIRED'and not cursor.queries
        snapshot_controls.append(str(error))
    else:raise AssertionError('AUTOCOMMIT_ACCEPTED')
    return dict(status='PASS_P0_PRIVILEGE_FACTS_NOT_AUTHORITY_CLOSURE',
        model=dict(bytes=len(raw),sha256=sha256(raw).hexdigest(),version=model['version'],
            assertions=model['assertions'],provider_functions_invoked=0),
        positive_controls=2,negative_controls=negative,snapshot_controls=snapshot_controls,
        group_counts=counts,actual_SQL_executed_this_control=0,actual_ERP_calls=0,
        actual_Native_case_credit=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=check(a.model);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],positive=result['positive_controls'],
        negative=len(result['negative_controls']),snapshot=len(result['snapshot_controls']),counts=result['group_counts'])))
