"""Prepared accounting readers; strict price admission remains unchanged.

A real PO can have a current numeric valuation while its completion/laundry
status remains pending. Accounting reads those facts; manual price admission
continues to require the unchanged final-cost root.
"""
from hashlib import sha256
from pathlib import Path
import re
from cp7_sku_cost_components.valuation_delta import Derivation

ROOT=Path(__file__).resolve().parents[2]
PARENT=ROOT/'scripts/cp7_sku_cost_components'
PARENT_FILES={'costs.sql':'999ce0516366efb0a2cdc59e0c90b7edf99717dc387fa51f972934e287c1e6c1',
    'money.sql':'58ea892a29077535cbb417a3aac750a3b35996027d8d6b10851aa5030b92cc69'}
PINS={'cost_root_v3':'6daa8decc76b48009d037bf15c9c12fc00e37a55889d75afd8af8ba69d818c05',
      'cost_current_unit_v3':'1a8b1eb926cda146402da8c32b195d362b3847c1872f22ef06c50fb4e1f28d5e'}


def original(file,name):
    raw=(PARENT/file).read_text()
    matches=re.findall(r'(?ms)^create function cp7_sku_conversion\.'+name+r'\([\s\S]*?\$\$;\n',raw)
    if len(matches)!=1 or sha256(matches[0].encode()).hexdigest()!=PINS[name]:
        raise ValueError('PENDING_ACCOUNTING_EXACT_PARENT_REQUIRED:'+name)
    return matches[0]


def derive():
    for name,digest in PARENT_FILES.items():
        if sha256((PARENT/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('PENDING_ACCOUNTING_WHOLE_PARENT_FILE_CHANGED:'+name)
    root=original('costs.sql','cost_root_v3')
    unit=original('money.sql','cost_current_unit_v3')
    scopes=re.findall(r'(?ms)^create function cp7_sku_conversion\.cost_scope_value_v3\([\s\S]*?\$\$;\n',
        (PARENT/'costs.sql').read_text())
    if len(scopes)!=1:raise ValueError('PENDING_ACCOUNTING_EXACT_SCOPE_REQUIRED')
    previous=Derivation(scopes[0])
    previous.once('sum(t.units*r.unit_value)',
        'sum(t.units*cp7_sku_conversion.cost_current_unit_v3(t.root_lot_id,p_product))',
        'reconstruct the exact existing monetary scope reader')
    scope=previous.source.replace('create function ','create or replace function ',1)
    result={};routes={}
    def finish(name,d,source):
        if d.inverse()!=source:raise ValueError('PENDING_ACCOUNTING_ORIGINAL_NOT_RECOVERED:'+name)
        result[name]=d.source;routes[name]=[x[2]for x in d.routes]

    d=Derivation(root)
    d.once('cost_root_v3(p_lot uuid)','cost_accounting_root_v5(p_lot uuid)',
        'separate private accounting identity from unchanged strict price identity')
    d.once('h.id version_id,h.cost_state,','h.id version_id,h.cost_state,h.hpp_per_pcs present_native_hpp,',
        'require a present Native numeric HPP instead of inventing a missing valuation')
    d.once('if r.qty_pcs<=0 or r.extra is null',
        'if r.qty_pcs is null or r.qty_pcs<=0 or r.extra is null',
        'an accounting unit requires an actual positive allocation quantity')
    before="""  or r.version_id is null or r.cost_state='ESTIMATED' or r.conversion_status not in('POSTED','REVERSED')
  or erp.bd_lot_laundry_unknown_v1(p_lot)
  or(r.po_id is not null and not exists(select 1 from erp.get_hpp_completeness(r.po_id)c where c.pending_reason_count=0))then"""
    after="""  or r.version_id is null or r.conversion_status not in('POSTED','REVERSED')
  or(r.po_id is not null and(not exists(select 1 from erp.production_orders p where p.id=r.po_id)
    or r.present_native_hpp is null
    or r.present_native_hpp::text in('NaN','Infinity','-Infinity')))
  or(r.po_id is null and(r.cost_state='ESTIMATED' or erp.bd_lot_laundry_unknown_v1(p_lot)))then"""
    d.once(before,after,'only genuine PO accounting may read present provisional amounts; non-PO admission stays strict')
    d.once("jsonb_build_object('allocation',to_jsonb(r)",
        """jsonb_build_object('accounting_only',true,'final_cost_ready',coalesce(r.cost_state<>'ESTIMATED'
   and not erp.bd_lot_laundry_unknown_v1(p_lot)
   and(r.po_id is null or exists(select 1 from erp.get_hpp_completeness(r.po_id)c where c.pending_reason_count=0)),false),
   'allocation',to_jsonb(r)""",'retain an honest pending/final label with the complete Native source proof')
    finish('cp7_sku_conversion.cost_accounting_root_v5(uuid)',d,root)

    d=Derivation(unit)
    d.once('-- Keep current HPP completeness and real PO attribution from the Native root.',
        '-- Accounting keeps present numeric PO facts; strict price admission stays in the original reader.',
        'describe the accounting reader without claiming pending cost is final')
    d.once('cost_current_unit_v3(p_root uuid,p_product uuid)',
        'cost_accounting_unit_v5(p_root uuid,p_product uuid)','separate accounting units from strict pool units')
    d.once('cost_root_v3(p_root)','cost_accounting_root_v5(p_root)',
        'retain all exact non-PO cent custody guards and real PO attribution')
    finish('cp7_sku_conversion.cost_accounting_unit_v5(uuid,uuid)',d,unit)

    d=Derivation(scope)
    d.once('cost_current_unit_v3(t.root_lot_id,p_product)',
        'cost_accounting_unit_v5(t.root_lot_id,p_product)','the accounting scope consumes present source amounts')
    d.once('cost_root_v3(t.root_lot_id)','cost_accounting_root_v5(t.root_lot_id)',
        'accounting scope no longer confuses PO cost readiness with numeric source availability')
    finish('cp7_sku_conversion.cost_scope_value_v3(uuid,uuid,text)',d,scope)
    ddl='\n'.join(result.values())+"""
revoke all on function cp7_sku_conversion.cost_accounting_root_v5(uuid),
 cp7_sku_conversion.cost_accounting_unit_v5(uuid,uuid)from public,anon,authenticated,service_role;
"""
    return dict(ddl=ddl,definitions=result,derivations=routes,old_scope=scope,
        parent_root=root,parent_unit=unit,parent_scope_sha256=sha256(scope.encode()).hexdigest(),
        actual_Native_cases=0,production_go=False,independent_acceptance=False)
