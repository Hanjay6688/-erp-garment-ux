"""Prepare isolated typed reader controls from the retained exact model input."""
from hashlib import sha256
from pathlib import Path
import json,re,sys
from .derivation import derive,ROOT,PARENT


def prepare(source,destination):
    raw=Path(source).read_bytes()
    if sha256(raw).hexdigest()!='90ccf2bdfbf0e123d525dacdb2d6237706b4348bec41486a0ce203716f4c217c':
        raise ValueError('PENDING_ACCOUNTING_EXACT_RETAINED_MODEL_INPUT_REQUIRED')
    old=json.loads(raw);product=derive()
    old_scope=re.findall(r'(?ms)^create (?:or replace )?function cp7_sku_conversion\.cost_scope_value_v3\([\s\S]*?\$\$;\n',old['cost_ddl'])
    if not old_scope or old_scope[-1]!=product['old_scope']:
        raise ValueError('PENDING_ACCOUNTING_EXISTING_MONEY_SCOPE_NOT_EXACT')
    valuation=(ROOT/'scripts/cp7_sku_moving_average/valuation.sql').read_text()
    costs=(PARENT/'costs.sql').read_text();money=(PARENT/'money.sql').read_text()
    table_names=['sale_allocation_values_v2','sales_return_values_v2','cost_events_v3',
        'sale_cost_components_v3','return_cost_components_v3','cost_money_events_v3']
    tables=[]
    for name in table_names:
        matches=re.findall(r'(?ms)^create table cp7_sku_conversion\.'+name+r'\([\s\S]*?^\);\n',valuation+'\n'+costs+'\n'+money)
        if len(matches)!=1:raise ValueError('PENDING_ACCOUNTING_EXACT_TYPED_PRIVATE_TABLE_REQUIRED:'+name)
        tables.append(matches[0])
    cells=re.findall(r'(?ms)^create function cp7_sku_conversion\.cost_money_cells_v3\([\s\S]*?\$\$;\n',money)
    if len(cells)!=1:raise ValueError('PENDING_ACCOUNTING_EXACT_CENT_CUSTODY_REQUIRED')
    result=dict(classification='TYPED_READER_MODEL_NOT_NATIVE_ERP',columns=old['columns'],tables=tables,
        original_root=product['parent_root'],original_unit=product['parent_unit'],original_scope=product['old_scope'],
        cells=cells[0],extra={k:old['cost_functions'][k]for k in('erp.be_conversion_extra_v1(uuid)','erp.be_allocation_extra_v1(uuid)')},
        product=product,actual_ERP_cases=0,actual_Auth_cases=0,production_go=False)
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    target=destination/'INPUT.json';target.write_text(json.dumps(result,sort_keys=True)+'\n')
    return dict(path=str(target),bytes=target.stat().st_size,sha256=sha256(target.read_bytes()).hexdigest())


if __name__=='__main__':print(json.dumps(prepare(*sys.argv[1:])))
