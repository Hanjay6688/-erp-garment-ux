"""Keep the complete Native cost command and add bounded source redistribution."""
from hashlib import sha256
from valuation_delta import Derivation

SIGNATURE='erp.be_reconcile_cost_document_v1(uuid,date)'
ORIGINAL_SHA256='fdaf4b1384fa7a4840359cbc7c1e94b588979e2cd364a2b2e9da9f03662492ad'


def derive(original):
    if sha256(original.encode()).hexdigest()!=ORIGINAL_SHA256:raise ValueError('SKU_COST_NATIVE_RECONCILE_CHANGED')
    d=Derivation(original)
    d.once('r record;v_target numeric;v_before numeric;v_delta numeric;v_journal uuid;v_own boolean;v_event uuid;',
        'r record;v_target numeric;v_before numeric;v_delta numeric;v_journal uuid;v_own boolean;v_event uuid;\n v_sku_before jsonb;v_sku_delta numeric:=0;',
        'bounded per-document source proof and exact delta')
    d.once("if c.status<>'POSTED' then raise exception 'BE_COST_SOURCE_NOT_POSTED';end if;",
        "if c.status<>'POSTED' then raise exception 'BE_COST_SOURCE_NOT_POSTED';end if;\n if l.po_id is null then v_sku_before:=cp7_sku_conversion.capture_cost_source_v3(p_document);end if;",
        'every affected source book exact before any new journal or event')
    d.once('values(v_event,p_document,r.adjustment_id,v_before,v_target,v_journal,p_date,erp.current_app_user_id());',
        'values(v_event,p_document,r.adjustment_id,v_before,v_target,v_journal,p_date,erp.current_app_user_id());\n     v_sku_delta:=v_sku_delta+v_delta;',
        'legitimate delta comes from exact retained Native cost event')
    d.once("if l.po_id is null then\n   perform erp.be_nonpo_sync_all_v1",
        "if l.po_id is null then\n   perform cp7_sku_conversion.rebalance_cost_source_v3(p_document,p_date,v_sku_before,v_sku_delta);\n   perform erp.be_nonpo_sync_all_v1",
        'bounded balanced source transfer before unchanged Native FG COGS sync')
    if d.inverse()!=original:raise ValueError('SKU_COST_NATIVE_DERIVATION_NOT_REVERSIBLE')
    return d.source,[r[2]for r in d.routes]
