"""Bound provisional pricing to exact Native automatic rework ownership."""
from hashlib import sha256
from pathlib import Path
import re
from cp7_sku_cost_components.valuation_delta import Derivation
from cp7_sku_pending_accounting.derivation import derive as accounting

HERE=Path(__file__).resolve().parent
PINS={
 'cp7_sku_conversion.pool_quote_v2':'615677c139c85c1292af5012148e27708bcadabb8f767fbb70d4ac2107367518',
 'cp7_sku_conversion.pool_cost_components_v3':'9048b5789ff4384637de31f38a0247d68b37b41d4baa4b71a81c120754cba37e',
 'cp7_sku_conversion.post_conversion_money_v3':'c2b45cd411043a619274c30d368425b8e1c0674b7be98f808907ddb540220c5f',
 'erp.be_conversion_preview_v1':'c58f30fe9be8538f792f882d6d92485c98997ffea31f794c3a48de213922a8bc',
 'erp.be_post_conversion_v1':'1f6d5a08fc69f62bde7ef7bb4caa93df9c018dcb26bc4004611fa0ecf189e900',
 'erp.be_reverse_conversion_v1':'b3651bdb846656556dcd7f5778f8b4c5f8f91a8bd945171544d9550aea7d4efc',
 'erp.be_complete_rework_target_v1':'16de46828fc0ed3c54467985403f43ea9e341dceac1859eccdeaa5d55f420e41',
 'erp.be_reverse_rework_target_v1':'3dd30156e24e23cfee1834286dd4f20771b7ff3907f1431611d9f00c6bfcd340',
}


def derive(parent_definitions):
    originals={}
    for name in PINS:
        values=[v for k,v in parent_definitions.items()if k.split('(')[0]==name]
        if len(values)!=1 or sha256(values[0].encode()).hexdigest()!=PINS[name]:
            raise ValueError('AUTOMATIC_PENDING_EXACT_PARENT_BODY_REQUIRED:'+name)
        originals[name]=values[0]
    result={};routes={}
    def save(name,d):
        if d.inverse()!=originals[name]:raise ValueError('AUTOMATIC_PENDING_ORIGINAL_RECOVERY_REQUIRED:'+name)
        result[name]=re.sub(r'(?i)^create function ','create or replace function ',d.source,count=1)
        routes[name]=[v[2]for v in d.routes]

    name='cp7_sku_conversion.pool_quote_v2';d=Derivation(originals[name])
    d.once('v_unknown boolean;v_revision text;',
        'v_unknown boolean;v_revision text;v_automatic boolean;v_cost_pending boolean;',
        'retain explicit provisional state separately from numeric value')
    token=' with components as materialized('
    d.once(token," v_automatic:=cp7_sku_conversion.automatic_scope_v5(p_product,p_location,p_grade);\n"+token,
        'only current exact Native automatic source and target scopes receive provisional admission')
    token=" if v_unknown then raise exception 'CP7_SKU_POOL_HPP_UNKNOWN: seluruh komponen ekonomi termasuk reservasi harus diketahui';end if;"
    replacement=""" if v_automatic and exists(
  select 1 from cp7_sku_conversion.pool_components_v2(p_product,p_location,p_grade)c
  join erp.fg_lots l on l.id=c.root_lot_id left join erp.hpp_versions h on h.id=c.hpp_version_id
  where c.component_units< -0.000000000001 or c.hpp_version_id is null or c.unit_value is null
   or c.unit_value::text in('NaN','Infinity','-Infinity')
   or(l.po_id is not null and not exists(select 1 from erp.production_orders p where p.id=l.po_id))
   or(l.po_id is null and(h.cost_state='ESTIMATED'or erp.bd_lot_laundry_unknown_v1(l.id)))
 )then raise exception 'CP7_SKU_AUTOMATIC_PRESENT_NUMERIC_PO_COMPONENTS_REQUIRED';end if;
 if v_unknown and not v_automatic then raise exception 'CP7_SKU_POOL_HPP_UNKNOWN: seluruh komponen ekonomi termasuk reservasi harus diketahui';end if;"""
    d.once(token,replacement,'keep manual finality refusal; automatic PO values must actually exist and non-PO costs remain final')
    token=' v_value:=round(v_base+v_adjust,6);'
    d.once(token,token+"""
 if v_automatic then
  select coalesce(bool_or((c.source_revision->>'accounting_only')::boolean is true
   and(c.source_revision->>'final_cost_ready')::boolean is not true),false)
  into v_cost_pending from cp7_sku_conversion.pool_cost_components_v3(p_product,p_location,p_grade)c;
  v_unknown:=v_unknown or v_cost_pending;
 end if;""",'pending added-cost roots also preserve the provisional label')
    d.once("case when v_qty=0 then 'EMPTY' else 'KNOWN'end",
        "case when v_qty=0 then 'EMPTY'when v_unknown then 'PROVISIONAL'else 'KNOWN'end",
        'never describe a provisional numeric value as final known cost')
    d.once("'revision',v_revision);",
        "'revision',v_revision)||case when v_automatic then jsonb_build_object('final_cost_ready',not v_unknown)else '{}'::jsonb end;",
        'private automatic reads expose honest readiness; ordinary pool replies retain their exact shape')
    save(name,d)

    name='cp7_sku_conversion.pool_cost_components_v3';d=Derivation(originals[name])
    d.once('cp7_sku_conversion.cost_root_v3(a.root_lot_id)',
        'cp7_sku_conversion.automatic_cost_root_v5(a.root_lot_id,p_product,p_location,p_grade)',
        'only an economically owned PO root in the active automatic scope may use accounting facts')
    d.many('cp7_sku_conversion.cost_current_unit_v3(a.root_lot_id,p_product)',
        'cp7_sku_conversion.automatic_cost_unit_v5(a.root_lot_id,p_product,p_location,p_grade)',2,
        'private automatic reads keep all other strict root and cent custody checks')
    save(name,d)

    name='cp7_sku_conversion.post_conversion_money_v3';d=Derivation(originals[name])
    for side in('source','target'):
        d.once('cp7_sku_conversion.cost_current_unit_v3(c.root_lot_id,q.'+side+'_product_id)',
            'cp7_sku_conversion.automatic_cost_unit_v5(c.root_lot_id,q.'+side+'_product_id,q.location_id,q.quality_grade)',
            'validate '+side+' current owned money under the same automatic frame')
    save(name,d)

    name='erp.be_conversion_preview_v1';d=Derivation(originals[name])
    token="'source_value_revision',v_source_pool->>'revision','target_value_revision',v_target_pool->>'revision')end;"
    d.once(token,"""'source_value_revision',v_source_pool->>'revision','target_value_revision',v_target_pool->>'revision')
   ||case when cp7_sku_conversion.automatic_scope_v5(s.id,v_location,'GRADE_A')then jsonb_build_object(
    'source_value_state',v_source_pool->>'state','target_value_state',v_target_pool->>'state',
    'valuation_provisional',v_source_pool->>'state'='PROVISIONAL'or v_target_pool->>'state'='PROVISIONAL')else '{}'::jsonb end
  end;""",'retain provisional state in the private automatic preview and preserve ordinary manual reply fields')
    save(name,d)

    name='erp.be_post_conversion_v1';d=Derivation(originals[name])
    token=' v:=erp.be_conversion_preview_v1(p_payload);'
    d.once(token,' perform cp7_sku_conversion.automatic_assert_native_v5(p_request,p_origin,p_rework,p_payload);\n'+token,
        'after all original permission and source locks bind the exact server-generated automatic child')
    save(name,d)

    name='erp.be_reverse_conversion_v1';d=Derivation(originals[name])
    token=' perform erp.reverse_product_conversion(p_conversion,p_reason);'
    d.once(token,' perform cp7_sku_conversion.automatic_assert_native_v5(p_conversion,null,null,null);\n'+token,
        'retain all original inverse guards and require the exact owning automatic child when a frame exists')
    save(name,d)

    name='erp.be_complete_rework_target_v1';d=Derivation(originals[name])
    d.once('v_result jsonb;','v_result jsonb;v_automatic_request uuid;',
        'reserve the existing one random Native child before computing its opaque expected revision')
    token=' v_result:=erp.be_post_conversion_v1('
    d.once(token,""" v_automatic_request:=gen_random_uuid();
 perform cp7_sku_conversion.automatic_enter_v5(p_rework,'POST',v_automatic_request);
"""+token,'establish exact completed PO GOOD ownership before source revision and preview admission')
    d.once(')),gen_random_uuid(),',')),v_automatic_request,',
        'use that same single server-generated Native child identity')
    token=' if v_own then delete from erp.be_execution_context_v1'
    d.once(token," perform cp7_sku_conversion.automatic_leave_v5(p_rework,'POST',v_automatic_request);\n"+token,
        'retain successful Native/economic provenance then release only the owning temporary frame')
    save(name,d)

    name='erp.be_reverse_rework_target_v1';d=Derivation(originals[name])
    token='   perform erp.be_reverse_conversion_v1(v,p_reason);'
    d.once(token,"""   perform cp7_sku_conversion.automatic_enter_v5(p_rework,'REVERSE',v);
"""+token+"\n   perform cp7_sku_conversion.automatic_leave_v5(p_rework,'REVERSE',v);",
        'each exact posted automatic child owns its private inverse frame inside the unchanged Native loop')
    save(name,d)
    return dict(ddl=accounting()['ddl']+'\n'+(HERE/'context.sql').read_text(),definitions=result,
        derivations=routes,parent_source_sha256=PINS,actual_ERP_cases=0,production_go=False,independent_acceptance=False)
