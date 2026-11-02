from pathlib import Path
import ast

HERE=Path(__file__).resolve().parent
source=(HERE/'qualification_cases.py').read_text()
tree=ast.parse(source)
ids=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)
         and any(isinstance(t,ast.Name)and t.id=='IDS'for t in n.targets))
assert len(ids)==5 and len(set(ids))==5
for name in ('canonical_forward_back','exact_group_reverse','root_recost','sale_partial_return_reverse','reservation_location_isolation'):
    assert any(isinstance(n,ast.FunctionDef)and n.name==name for n in tree.body)
for token in ('20.00','35.00','95.00','130.00','150.00','post_opening_hpp_correction',
              'component_events_v2','valuation_events_v2','SKU_MOVING_AVERAGE'):
    assert token in source,token
assert 'actual native pass' not in source.lower()
for token in ('sale_allocation_values_v2','sales_return_values_v2','sales_returns.inverse','sales_returns.reverse_sale',
              'active_reservation_included_in_pool','other_location_unchanged'):
    assert token in source,token
print({'status':'SKU_MOVAVG_FIVE_INTENDED_NATIVE_CASES_SOURCE_PASS','actual_Native_cases':0,
       'production_go':False})
