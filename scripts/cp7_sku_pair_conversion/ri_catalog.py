"""Exact parent-side RI edges created by this delta's three declared ERP FKs.

Catalog22 keys internal triggers by the referencing constraint, not the
opaque RI_ConstraintTrigger OID name. No other ERP trigger is admitted.
"""
EDGES=(
 ('cp7_sku_conversion.pairs_v1','pairs_v1_left_id_fkey','erp.bf_skus_v1','left_id','erp.bf_skus_v1_pkey'),
 ('cp7_sku_conversion.pairs_v1','pairs_v1_right_id_fkey','erp.bf_skus_v1','right_id','erp.bf_skus_v1_pkey'),
 ('cp7_sku_conversion.members_v1','members_v1_conversion_id_fkey','erp.product_conversions','conversion_id','erp.product_conversions_pkey'),
)

def expected_constraints():
    return {child+':'+constraint:['f',False,False,True,True,0,True,None,index,child,
      'FOREIGN KEY ('+column+') REFERENCES '+parent+'(id)']for child,constraint,parent,column,index in EDGES}

def expected_parent_triggers(constraints):
    expected=expected_constraints()
    for key,row in expected.items():
        if constraints.get(key)!=row:raise ValueError('SKU_PAIR_CONVERSION_FOREIGN_KEY_EDGE_CHANGED:'+key)
    triggers={}
    for child,constraint,parent,_,_ in EDGES:
        for function,kind in(('"RI_FKey_noaction_del"()',9),('"RI_FKey_noaction_upd"()',17)):
            key=parent+':'+child+':'+constraint+':'+function+':'+str(kind)
            triggers[key]=[True,'O',kind,0,'',[],False,False,function,None,None,None,constraint,child,None,child]
    return triggers

def permitted_parent_trigger(key,row,expected):return key in expected and row==expected[key]
