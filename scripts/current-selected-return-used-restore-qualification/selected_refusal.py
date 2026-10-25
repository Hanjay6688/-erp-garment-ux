"""Exact retained refusal checks with the qualified selected-customer error."""
import ast,inspect,textwrap


def customer_refusal(business,cur,rid):
    old=business.old
    before=old.data(cur);catalog=old.product.catalog._catalog_rows(cur)
    result=old.peer.operation(cur,'select erp.post_sales_return(%s)',(rid,))
    code='OW04_SOURCE_CUSTOMER_MISMATCH'
    assert result['refused']and result['error']['sqlstate']=='P0001'and result['error']['message'].splitlines()[0]==code,result
    assert old.data(cur)==before and old.product.catalog._catalog_rows(cur)==catalog
    return dict(result=result,all_data_and_sequences_unchanged=True,full22_unchanged=True)


def source_binding(business):
    expected=ast.parse(textwrap.dedent(inspect.getsource(business.customer_refusal)))
    function=expected.body[0];function.args.args.insert(0,ast.arg(arg='business'))
    function.body.insert(0,ast.parse('old=business.old').body[0])
    changes=0
    for row in function.body:
        if isinstance(row,ast.Assign)and len(row.targets)==1 and isinstance(row.targets[0],ast.Name)and row.targets[0].id=='code':
            assert ast.dump(row.value,include_attributes=False)==ast.dump(ast.parse("'CP7_NATIVE_EMPTY_ACTIVE_SOURCE_REQUIRED'if PATCHED else'OW04_SOURCE_CUSTOMER_MISMATCH'",mode='eval').body,include_attributes=False)
            row.value=ast.Constant(value='OW04_SOURCE_CUSTOMER_MISMATCH');changes+=1
    actual=ast.parse(textwrap.dedent(inspect.getsource(customer_refusal)))
    assert changes==1 and ast.dump(actual,include_attributes=False)==ast.dump(expected,include_attributes=False),'SELECTED_RETURN_RESTORE_REFUSAL_ORACLE_CHANGED'
    return dict(exact_retained_business_assertions=True,only_expected_selected_customer_code_changed=True,
        original_helper_unchanged=True,expected_sqlstate='P0001',expected_error='OW04_SOURCE_CUSTOMER_MISMATCH',
        all_rows_sequences_and_full22_checks_retained=True)
