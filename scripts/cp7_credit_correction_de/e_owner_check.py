"""E public-owner adapter control with declared catalog cursor doubles only."""
import json
from . import e_composition as product
from .local_owner_check import Cursor


def main():
    checks=[]
    assert set(product.PUBLIC_OWNERS.values())=={'cp7_sales_write'}
    for signature in product.PUBLIC_OWNERS:
        captured={'functions':{signature:['original','cp7_sales_write']},'schemas':{'public':['postgres','explicit-acl']}}
        for create in(False,True):
            cursor=Cursor('cp7_sales_write',create)
            with product.public_function_ddl(cursor,signature,captured):cursor.execute('DECLARED_REPLACEMENT')
            sql=[v['sql']for v in cursor.trace]
            assert 'set local role "cp7_sales_write"'in sql
            assert sum('grant create on schema'in q for q in sql)==int(not create)
            assert sum('revoke create on schema'in q for q in sql)==int(not create)
            assert any(v['sql']=="select set_config('role',%s,true)"and v['params']==('none',)for v in cursor.trace)
            checks.append(signature+':'+('EXISTING_CREATE'if create else'TEMPORARY_CREATE_RESTORED'))
        for owner,acl,expected in(('cp7_sales_read','explicit-acl','OWNER_CHANGED'),('cp7_sales_write',None,'NULL_SCHEMA_ACL')):
            cursor=Cursor(owner,False,acl)
            try:
                with product.public_function_ddl(cursor,signature,captured):raise AssertionError('E_UNSAFE_DDL_ADMITTED')
            except ValueError as error:assert expected in str(error)
            assert not any('grant 'in v['sql']or'set local role'in v['sql']for v in cursor.trace)
            checks.append(signature+':'+expected+'_REFUSED_BEFORE_DDL')
    source=(product.HERE/'e_composition.py').read_text()
    assert 'with public_function_ddl(cur,signature,before):cur.execute(definitions[signature],prepare=False)'in source
    assert "with public_function_ddl(cur,signature,state['before']):cur.execute(state['originals'][signature],prepare=False)"in source
    checks.append('INSTALL_AND_PREUSE_INVERSE_SYMMETRIC')
    return dict(status='PASS',scope='E_METADATA_CURSOR_DOUBLE_ONLY',checks=checks,Native_execution=False)

if __name__=='__main__':print(json.dumps(main(),indent=2))
