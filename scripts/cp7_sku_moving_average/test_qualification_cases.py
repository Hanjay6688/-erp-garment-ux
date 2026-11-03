from pathlib import Path
import ast

HERE=Path(__file__).resolve().parent
source=(HERE/'qualification_cases.py').read_text()
tree=ast.parse(source)
ids=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)
         and any(isinstance(t,ast.Name)and t.id=='IDS'for t in n.targets))
assert len(ids)==6 and len(set(ids))==6
for name in ('canonical_forward_back','exact_group_reverse','root_recost','sale_partial_return_reverse','reservation_location_isolation','fractional_return_scope'):
    assert any(isinstance(n,ast.FunctionDef)and n.name==name for n in tree.body)
for token in ('20.00','35.00','95.00','130.00','150.00','post_opening_hpp_correction',
              'component_events_v2','valuation_events_v2','SKU_MOVING_AVERAGE'):
    assert token in source,token
assert 'actual native pass' not in source.lower()
for token in ('sale_allocation_values_v2','sales_return_values_v2','sales_returns.inverse','sales_returns.reverse_sale',
              'active_reservation_included_in_pool','other_location_unchanged'):
    assert token in source,token
print({'status':'SKU_MOVAVG_SIX_INTENDED_NATIVE_CASES_SOURCE_PASS','actual_Native_cases':0,
       'production_go':False})

# Three independent fixture trials; preserve every original business statement.
from hashlib import sha256
from copy import deepcopy
fractional=deepcopy(next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='fractional_return_scope'))
blocks=[n for n in fractional.body if isinstance(n,ast.With)]
assert len(blocks)==3
assert [ast.literal_eval(next(k.value for k in n.items[0].context_expr.keywords if k.arg=='savepoint_name'))for n in blocks]==['sku_cent_split','sku_cent_batch','sku_cent_recost']
for n in blocks:
    call=n.items[0].context_expr
    assert ast.unparse(call.func)=='cur.connection.transaction' and not call.args
    assert set(k.arg for k in call.keywords)=={'savepoint_name','force_rollback'}
    assert next(k.value.value for k in call.keywords if k.arg=='force_rollback')is True
restored=[]
for n in fractional.body:restored.extend(n.body if isinstance(n,ast.With)else[n])
fractional.body=restored
assert sha256(ast.dump(fractional,include_attributes=False).encode()).hexdigest()=='8c283a1f06735a023acf3119405f9056e88c5aa1151e9317e1bc16b8428f9e82'
print({'status':'THREE_ISOLATED_FIXTURE_TRIALS_ALL_FEA758_BUSINESS_ORACLES_IDENTICAL','actual_Native_cases':0})
