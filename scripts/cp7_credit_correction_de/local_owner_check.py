"""Directed DDL-helper control double; no Native/financial/source proof.

The cursor models only the verified predecessor's owner/schema metadata. The
emitted statements are also executed by local_owner_check.mjs under real local
Postgres roles, with a NONSUPERUSER business-executor stand-in.
"""
from types import SimpleNamespace
import json
from psycopg.pq import TransactionStatus
from cp7_credit_correction_de import composition as product


class Cursor:
    def __init__(self,owner,allowed=False,acl='original-explicit-acl'):
        self.owner=owner;self.allowed=allowed;self.acl=acl;self.rows=[];self.trace=[]
        self.connection=SimpleNamespace(info=SimpleNamespace(transaction_status=TransactionStatus.INTRANS))

    def execute(self,query,params=None,prepare=None):
        statement=query if isinstance(query,str)else query.as_string(None)
        self.trace.append(dict(sql=statement,params=params))
        if statement=='show role':self.rows=[('none',)]
        elif 'join pg_namespace' in statement:self.rows=[(self.owner,'public','postgres',self.acl,self.allowed)]
        elif 'select nspacl::text' in statement:self.rows=[(self.acl,)]
        else:self.rows=[]
        return self

    def fetchone(self):return self.rows[0]


def main():
    traces={};checks=[]
    for signature,owner in ((product.native_delta.PUBLIC_COMMAND,'cp7_sales_write'),(product.native_delta.PUBLIC_WORKSPACE,'cp7_sales_read')):
        captured={'functions':{signature:['original',owner]},'schemas':{'public':['postgres','original-explicit-acl']}}
        for allowed in(False,True):
            cursor=Cursor(owner,allowed)
            with product.public_function_ddl(cursor,signature,captured):
                cursor.execute('DECLARED_REPLACEMENT',prepare=False)
            statements=[x['sql']for x in cursor.trace]
            assert any('set local role "'+owner+'"'==q for q in statements)
            assert sum('grant create on schema' in q for q in statements)==int(not allowed)
            assert sum('revoke create on schema' in q for q in statements)==int(not allowed)
            assert any(q=="select set_config('role',%s,true)"and x['params']==('none',)for x in cursor.trace for q in[x['sql']])
            assert not any('alter function' in q.lower()or'grant execute' in q.lower()for q in statements)
            traces[owner+':'+str(allowed)]=cursor.trace;checks.append(owner+('_EXISTING_CREATE'if allowed else'_TEMPORARY_CREATE_RESTORED'))
        for bad in('postgres','cp7_invoice_write'):
            cursor=Cursor(bad)
            try:
                with product.public_function_ddl(cursor,signature,captured):raise AssertionError('BAD_OWNER_ADMITTED')
            except ValueError as error:assert 'OWNER_CHANGED' in str(error)
            assert not any('grant 'in x['sql']or'set local role'in x['sql']for x in cursor.trace)
            checks.append('WRONG_OWNER_'+bad+'_REFUSED')
        cursor=Cursor(owner,False,None)
        try:
            with product.public_function_ddl(cursor,signature,captured):raise AssertionError('NULL_ACL_NORMALIZED')
        except ValueError as error:assert 'NULL_SCHEMA_ACL' in str(error)
        assert not any('grant 'in x['sql']or'set local role'in x['sql']for x in cursor.trace)
        checks.append(owner+'_NULL_SCHEMA_ACL_REFUSED_BEFORE_DDL')
    source=product.HERE.joinpath('composition.py').read_text()
    assert 'with public_function_ddl(cur,signature,before):cur.execute(definitions[signature],prepare=False)' in source
    assert "with public_function_ddl(cur,signature,state['before']):cur.execute(state['originals'][signature],prepare=False)" in source
    checks.append('INSTALL_AND_PREUSE_ROLLBACK_USE_SAME_EXACT_OWNER_ADAPTER')
    return dict(status='PASS',scope='DIRECTED_METADATA_CURSOR_DOUBLE',checks=checks,traces=traces,Native_execution=False)

if __name__=='__main__':print(json.dumps(main(),indent=2))
