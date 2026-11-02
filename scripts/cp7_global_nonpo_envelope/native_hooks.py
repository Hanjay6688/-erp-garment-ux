"""Counted source-only adapters over exact actual DE30 owning definitions.

No SQL executor, installer, connection or runtime admission is provided.
"""
from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent
NS='cp7_global_nonpo_envelope.'
D1='cp7_credit_correction_de.'
E='cp7_credit_note_carry_de.'
SOURCE='cp7_credit.'


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def originals():
    ref=json.loads((HERE/'NATIVE_OWNING_REFERENCE.json').read_bytes())
    if(ref['head']!='6e61506c10a18541c104b981bd438e78b175b5d1'
        or ref['functions_unchanged_after_committed_E']is not True
        or len(ref['functions'])!=8):raise ValueError('GLOBAL_EXACT_ACTUAL_EIGHT_OWNERS_REQUIRED')
    return ref['functions']


def changes():
    lock=" perform "+NS+"lock_v1("+NS+"selected_profile_v1());\n"
    def bind(op,table,root):
        return(" perform "+NS+"bind_v1('"+op+"',(select operation_id from "+table+
            " where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()),\n"
            "  "+NS+"selected_profile_v1(),("+NS+"review_v1(array["+root+"])->>'basis_sha256'));\n")
    end='end $function$\n'
    quote=D1+'quote_v1(jsonb)';basis=E+'basis_v1(uuid)'
    return{
      quote:[
       ("declare sale uuid:=(p->>'sale_id')::uuid;","declare global_envelope_ jsonb;sale uuid:=(p->>'sale_id')::uuid;"),
       (" if exists(select 1 from erp.fg_lots l where l.id=any(cp7_credit.source_hpp_lot_ids_v1(sale))and(l.po_id is not null or l.lot_origin='CONVERSION'))",
        " global_envelope_:="+NS+"review_v1(array[sale]);\n if exists(select 1 from erp.fg_lots l where l.id=any(cp7_credit.source_hpp_lot_ids_v1(sale))and(l.po_id is not null or l.lot_origin='CONVERSION'))"),
       ("or exists(select 1 from erp.be_conversion_sources_v1 s join erp.fg_lots l on l.id=s.source_lot_id where l.po_id is null)then",
        "or(global_envelope_->>'status')is distinct from'OBSERVED_QUIESCENT_SOURCE_ONLY'then"),
       ("'refund_product_cap_basis',cap_products,'profile',profile,","'refund_product_cap_basis',cap_products,'global_envelope',global_envelope_,'profile',profile,")],
      D1+'prepare_v1(jsonb,uuid,text,jsonb)':[
       (" src:=ow04_source_proposal.locked_source_family((p->>'sale_id')::uuid);",lock+" src:=ow04_source_proposal.locked_source_family((p->>'sale_id')::uuid);"),
       (end,bind('D1',D1+'work_v1',"(p->>'sale_id')::uuid")+end)],
      D1+'finish_v1(jsonb)':[
       (' insert into '+D1+'operations_v1('," perform "+NS+"finish_v1('D1',w.operation_id);\n insert into "+D1+'operations_v1(')],
      basis:[
       ('declare authority jsonb;','declare global_envelope_ jsonb;authority jsonb;'),
       (' lots:=cp7_credit.source_hpp_lot_ids_v1(p_sale);',' global_envelope_:='+NS+'review_v1(array[p_sale]);\n lots:=cp7_credit.source_hpp_lot_ids_v1(p_sale);'),
       ("or exists(select 1 from erp.be_conversion_sources_v1 c join erp.fg_lots l on l.id=c.source_lot_id where l.po_id is null)then",
        "or(global_envelope_->>'status')is distinct from'OBSERVED_QUIESCENT_SOURCE_ONLY'then"),
       ("'connected_sources',sources,'authority',authority,","'connected_sources',sources,'global_envelope',global_envelope_,'authority',authority,")],
      E+'prepare_v1(jsonb,uuid,text,uuid,jsonb)':[
       (" graph:=cp7_credit.consumer_joined_graph_v1((p->>'sale_id')::uuid,null);",lock+" graph:=cp7_credit.consumer_joined_graph_v1((p->>'sale_id')::uuid,null);"),
       (end,bind('E',E+'work_v1',"(p->>'sale_id')::uuid")+end)],
      E+'finish_v1(jsonb)':[
       (' insert into '+E+'operations_v1('," perform "+NS+"finish_v1('E',w.operation_id);\n insert into "+E+'operations_v1(')],
      SOURCE+'source_request_enter_v1(text,jsonb,uuid,text)':[
       (' perform cp7_credit.assert_only_own_sales_source_context_v1(sale,p_action);',
        ' perform cp7_credit.assert_only_own_sales_source_context_v1(sale,p_action);\n'+lock.rstrip()),
       (" if exists(select 1 from erp.be_conversion_sources_v1 s\n  join erp.fg_lots l on l.id=s.source_lot_id where l.po_id is null)then\n  raise exception 'CP7_CREDIT_SOURCE_GLOBAL_HPP_GRAPH_UNQUALIFIED';end if;",
        " if("+NS+"review_v1(array[sale])->>'status')is distinct from'OBSERVED_QUIESCENT_SOURCE_ONLY'then\n  raise exception 'CP7_CREDIT_SOURCE_GLOBAL_HPP_GRAPH_UNQUALIFIED';end if;"),
       (end," perform "+NS+"bind_v1('SOURCE',op,"+NS+"selected_profile_v1(),null);\n"+end)],
      SOURCE+'source_request_finish_v1(uuid)':[
       (' delete from cp7_credit.source_operation_work_v1 where operation_id=w.operation_id;',
        " perform "+NS+"finish_v1('SOURCE',w.operation_id);\n delete from cp7_credit.source_operation_work_v1 where operation_id=w.operation_id;")],
    }


def derive(actual):
    expected=originals()
    if actual!=expected:raise ValueError('GLOBAL_EXACT_CURRENT_ACTUAL_OWNER_BODIES_AND_AUTHORITY_REQUIRED')
    routes=changes()
    if set(routes)!=set(expected):raise ValueError('GLOBAL_EXACT_EIGHT_OWNER_ROUTE_NAMES_REQUIRED')
    result={};proof={};count=0
    for signature,row in expected.items():
        raw=row[0];text=raw
        for before,after in routes[signature]:
            if text.count(before)!=1 or after in text:raise ValueError('GLOBAL_EXACT_ONE_OWNER_ANCHOR:'+signature)
            text=text.replace(before,after,1);count+=1
        recovered=text
        for before,after in reversed(routes[signature]):
            if recovered.count(after)!=1:raise ValueError('GLOBAL_EXACT_OWNER_ROUTE_REVERSE:'+signature)
            recovered=recovered.replace(after,before,1)
        if recovered!=raw:raise ValueError('GLOBAL_COMPLETE_ORIGINAL_OWNER_NOT_RECOVERED:'+signature)
        result[signature]=text
        proof[signature]=dict(before=pin(raw.encode()),after=pin(text.encode()),
            routes=[dict(before=a,after=b,count=1)for a,b in routes[signature]],
            unchanged_owner_and_ACL_and_all_metadata=row[1:])
    if count!=18:raise ValueError('GLOBAL_EXACT_EIGHTEEN_OWNER_ROUTES_REQUIRED')
    return result,dict(status='GLOBAL_EIGHT_NATIVE_OWNING_SOURCE_ADAPTERS_NOT_APPLIED',
        functions=proof,owning_functions=8,source_routes=count,global_guard_sites=3,
        complete_original_definitions_recovered=True,Native_propagation_transfer_sync_FIFO_HPP_journal_stock_engines_changed=0,
        public_fields_or_permissions_changed=0,final_actual_parent_review_still_required=True,
        actual_SQL_executed=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)
