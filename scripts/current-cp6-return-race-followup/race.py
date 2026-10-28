"""One explicit successor guard; every original lock/state/report assertion retained."""
from hashlib import sha256
import ast,inspect
OLD="'Original sale must be active/posted'"
NEW="'CP7_NATIVE_EMPTY_ACTIVE_SOURCE_REQUIRED'"
IDS=('SALE_REVERSE_COMMIT','SALE_REVERSE_ABORT')
def derive(original):
    assert original.count(OLD)==1 and NEW not in original,'EXACT_LEGACY_GUARD_ANCHOR_REQUIRED'
    tree=ast.parse(original);assert len(tree.body)==1 and isinstance(tree.body[0],ast.FunctionDef)and tree.body[0].name=='run_case'
    revised=original.replace(OLD,NEW,1)
    # Reverse the single literal change: all control flow, locks, final state,
    # physical quantities, report readiness and assertions must be byte equal.
    assert revised.replace(NEW,OLD,1)==original
    assert sum(isinstance(n,ast.Assert)for n in ast.walk(tree))==sum(isinstance(n,ast.Assert)for n in ast.walk(ast.parse(revised)))
    return revised

def execute(legacy,operation,case_id,tools,product,state,control):
    assert case_id in IDS
    original=legacy.ah.run_case;source=inspect.getsource(original);namespace=dict(vars(legacy.ah))
    exec(compile(derive(source),'<current-return-reverse-guard-successor>','exec'),namespace)
    candidate=namespace['run_case'];prior_current=legacy.CURRENT
    try:
        legacy.ah.run_case=candidate;legacy.CURRENT=True
        row=operation()
    finally:
        assert legacy.ah.run_case is candidate
        legacy.ah.run_case=original;legacy.CURRENT=prior_current
    assert row['status']=='PASS',row
    actual=row['original_result'];assert actual['mode']==case_id
    response=actual['second']
    if case_id=='SALE_REVERSE_COMMIT':
        assert response['committed']is False and response['sqlstate']=='P0001'
        assert response['error'].splitlines()[0]=='CP7_NATIVE_EMPTY_ACTIVE_SOURCE_REQUIRED'
        assert actual['final_state']==('REVERSED',0,0)
    else:
        assert response['committed']is True and actual['final_state']==('POSTED',2,1)
    # The real Native use must refuse inverse on this exact disposable copy.
    # The test-only ERP USAGE is isolated by the unchanged catalog context.
    with tools.connect()as conn,conn.cursor()as cur:
        with control.product_catalog(cur):
            _,_,_,_,catalog=product.runtime();before=catalog._catalog_rows(cur);data=catalog._data(cur)
            try:product.rollback_preuse(cur,state)
            except (AssertionError,ValueError)as error:assert str(error)==product.USED_ERROR,str(error)
            else:raise AssertionError('USED_RETURN_RACE_INVERSE_NOT_REFUSED')
            assert catalog._catalog_rows(cur)==before and catalog._data(cur)==data
        conn.rollback()
    return dict(row,explicit_successor=True,legacy_id=case_id,old_message=OLD[1:-1],current_message=NEW[1:-1],
        original_race_source_sha256=sha256(source.encode()).hexdigest(),only_expected_guard_literal_changed=True,
        used_guard_refused_before_DDL=True,raw_response_preserved=True,legacy_result_relabelled=False)
