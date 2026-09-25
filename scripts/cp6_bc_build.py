#!/usr/bin/env python3
"""Build the BC T1 family install: the accessory service, return and inspection workflow (ACC-04b), the accessory policy
settings (ACC-DEC01, ACC-DEC03..07, ERP-DEC02) and the opening accessory states ALL-C02/C03 (owner decision 25 Sep 2026:
every CR and every ALL state built and tested in CP6; policy rows are application settings with a fail-closed default).

New objects come from scripts/cp6_bc_objects_{policy,service,note,import,router}.sql; every existing function is taken from
the definition the chain currently runs (fixture, migrations, the BA and BB T1 files) with checked substitutions only:
  N1 erp.post_material_adjustment (fixture + v2.6.20u edit) and erp._cp6_material_adjustment_revaluation_state (v2.6.20t):
     the expense (outbound) and income (inbound) account of an adjustment posted by BC is its purpose account
     (erp.bc_adjustment_account_v1: internal use by purpose, ACC-DEC04; recovery valuation, ACC-DEC03); every other
     adjustment keeps OTHER_EXPENSE/OTHER_INCOME.
  N2 erp._recalculate_material_cost_core (v2.6.20ao) and erp.sync_material_cost_revaluation (BA): a credited mandor note
     return (source BC_NOTE_RETURN_CREDIT) comes back into stock at its note line's issue cost, like a cutting return at
     its issue cost, and is revalued with that issue against ACCESSORY_RECOVERY_COGS; a reversed BC write-off between its
     day and its reversal's day is revalued against its own purpose account.
  N3 erp.populate_payroll_draft (AC), erp.validate_material_kasbon_deduction and erp.refresh_contractor_issue_payroll_status
     (fixture), erp.run_integrity_checks (AC): payroll collects, caps and settles a note line on its collectible amount
     (erp.bc_note_item_collectible_v1: the original receivable less credited unpaid parts plus a rounding line; exactly
     total_receivable without BC activity).
  N4 erp.approve_payroll (BB): a carried return credit (BC_RETURN_CARRY) was recognized as CONTRACTOR_PAYABLE at the
     credit; approval does not accrue it again.
  N5 erp.save_accessory_issue_action_v1 and erp.get_accessory_issue_workspace_v1 (AP): mode FREE for a category on the
     owner's Special free list (ERP-DEC02) at price 0 with its policy version, checked again at posting; zones are not
     offered as a note location; a note shows its collectible amount, free lines and rounding.
  N6 erp.bb_opening_credit_lines_v1 and erp.bb_opening_credit_account_v1 (BB): an opening note return credit
     (ACCESSORY_NOTE_RETURN) is a non-cash settlement MATERIAL_RECOVERY / CONTRACTOR_RECEIVABLE of the imported document.
  N7 import pipeline (BB texts of erp.stage_migration_row, erp._validate_migration_batch_base, erp.finalize_migration_batch,
     erp.save_initial_import_action_v1, erp.get_initial_import_workspace_v1, erp.initial_import_revision_v1): the files
     OPENING_ACCESSORY_NOTE_LINE (ALL-C02) and OPENING_ACCESSORY_CUSTODY (ALL-C03) are validated and applied after BB's.
  N8 erp.assert_new_stock_cutoff_coverage_v1 (BB): the customer garment custody product reference is classified.
  N9 erp.run_v265_gudang_write_integrity_checks (fixture): contractor_issue_price_provenance_gap accepts the owner-decided
     manual retail price (ACC-DEC02, M:1066) as a note line's price provenance; before, every manual-price note (AP) was a
     CRITICAL finding (reproduced without BC). A line with neither a price version nor a typed price is still flagged. A
     manual price of 0 is refused (M:5023): free is only the ERP-DEC02 FREE mode.
Label T1_FAMILY: development install on the disposable chain AN -> AU -> AV -> AW..BA -> BB, not a release package.

Usage: python3 scripts/cp6_bc_build.py            # writes supabase/dev/cp6_bc_t1_family.sql
       python3 scripts/cp6_bc_build.py --check
"""
from pathlib import Path
import gzip,hashlib,json,re,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import cp6_bb_build as bb

AP=ROOT/'supabase/migrations/20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql'
AC=ROOT/'supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql'
AO=ROOT/'supabase/migrations/20260922135612_erp_v2_6_20ao_cp6_invoice_retail.sql'
T20=ROOT/'supabase/migrations/20260912171034_erp_v2_6_20t_cp6_material_adjustment_revaluation.sql'
BA=ROOT/'supabase/dev/cp6_ba_t1_family.sql'
BB=ROOT/'supabase/dev/cp6_bb_t1_family.sql'
FIXTURE=ROOT/'supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz'
CATALOG_BC=ROOT/'src/initialImportCatalogBC.json'
OBJECTS=[ROOT/f'scripts/cp6_bc_objects_{p}.sql' for p in ('policy','service','note','import','router')]
OUT=ROOT/'supabase/dev/cp6_bc_t1_family.sql'
VERSION='v2.6.20bc'
NEW_ENTITIES=['OPENING_ACCESSORY_NOTE_LINE','OPENING_ACCESSORY_CUSTODY']


def last_definition(path,name,end='$function$;',text=None):
    """The last CREATE OR REPLACE FUNCTION erp.<name>( ... <end> of a file."""
    text=text if text is not None else path.read_text()
    heads=[m.start() for m in re.finditer(r'(?i)create or replace function erp\.'+re.escape(name)+r'\(',text)]
    assert heads,('BC_SOURCE_MISSING',path.name,name)
    start=heads[-1];stop=text.index(end,start)+len(end)
    return text[start:stop]


def substitute(body,subs,label):
    for old,new in subs:
        assert body.count(old)==1,(label,old[:80],body.count(old))
        body=body.replace(old,new)
    return body


def fixture(name,subs,edits=()):
    text=gzip.open(FIXTURE,'rt').read()
    body=last_definition(None,name,text=text)
    for old,new,count in edits:
        assert body.count(old)==count,(name,'EDIT',old,body.count(old))
        body=body.replace(old,new)
    return substitute(body,subs,name)


# ---------------------------------------------------------------- N1 adjustment accounts
ADJ_SUBS=[("jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',round(-v_value,2),'credit',0)",
           "jsonb_build_object('account_id',erp.bc_adjustment_account_v1(h.id,'OTHER_EXPENSE'),'debit',round(-v_value,2),'credit',0)"),
          ("jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',round(v_value,2))",
           "jsonb_build_object('account_id',erp.bc_adjustment_account_v1(h.id,'OTHER_INCOME'),'debit',0,'credit',round(v_value,2))")]
ADJ_EDITS=[('h.physical_at::date','erp._cp3_business_date(h.physical_at)',2)]   # v2.6.20u, in place


def adjustment_state():
    text=T20.read_text()
    head='create function erp._cp6_material_adjustment_revaluation_state(p_adjustment uuid)'
    assert text.count(head)==1
    start=text.index(head);stop=text.index('$$;',start)+3
    body='CREATE OR REPLACE FUNCTION'+text[start+len('create function'):stop]
    return substitute(body,[
        ("  select erp.account_id(mapping) account_id,sum(amount) amount",
         "  -- BC: the purpose account of an adjustment posted by BC (erp.bc_adjustment_account_v1), else OTHER_EXPENSE/OTHER_INCOME.\n"
         "  select case when mapping='MATERIAL_INVENTORY' then erp.account_id(mapping) else erp.bc_adjustment_account_v1(p_adjustment,mapping) end account_id,sum(amount) amount"),
        ("  group by erp.account_id(mapping) having sum(amount)<>0","  group by 1 having sum(amount)<>0")],'adjustment state')


# ---------------------------------------------------------------- N2 note return cost
CORE_HEAD='CREATE OR REPLACE FUNCTION erp._recalculate_material_cost_core(p_material_id uuid, p_recalc_from timestamp with time zone, p_allow_checkpoint boolean)'
CORE_OLD="      elsif r.movement_type='CUTTING_RETURN' and r.source_type='CUTTING_GROUP_RETURN' then\n"
CORE_NEW=("      elsif r.source_type='BC_NOTE_RETURN_CREDIT' then\n"
          "        -- BC: a credited mandor note return comes back at the issue cost of its note line (like a cutting return).\n"
          "        select x.unit_cost_snapshot into v_cost from erp.material_stock_movements x where x.id=erp.bc_note_return_issue_movement_v1(r.source_id);\n"
          "        v_cost:=coalesce(v_cost,r.input_unit_cost,r.unit_cost_snapshot,v_avg);\n")+CORE_OLD
REVAL_SUBS=[
    ("      and msm.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN','CONTRACTOR_MATERIAL_ISSUE_ITEM','MATERIAL_SUPPLIER_RETURN_ITEM')",
     "      and msm.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN','CONTRACTOR_MATERIAL_ISSUE_ITEM','MATERIAL_SUPPLIER_RETURN_ITEM','BC_NOTE_RETURN_CREDIT')"),
    ("    elsif r.source_type='MATERIAL_SUPPLIER_RETURN_ITEM' then\n      v_counterpart:='MATERIAL_PURCHASE_VARIANCE';\n    end if;",
     "    elsif r.source_type='MATERIAL_SUPPLIER_RETURN_ITEM' then\n      v_counterpart:='MATERIAL_PURCHASE_VARIANCE';\n"
     "    elsif r.source_type='BC_NOTE_RETURN_CREDIT' then\n"
     "      -- BC: a credited note return is revalued with its note line's issue, against the accessory recovery cost.\n"
     "      select cmi.po_id,cmi.contractor_id into v_po,v_contractor from erp.bc_lot_events_v1 e join erp.bc_return_lots_v1 l on l.id=e.lot_id\n"
     "        join erp.contractor_material_issue_items ii on ii.id=l.note_item_id join erp.contractor_material_issues cmi on cmi.id=ii.issue_id\n"
     "        where e.id=r.source_id;\n"
     "      v_counterpart:='ACCESSORY_RECOVERY_COGS';\n    end if;"),
    ("        when r.source_type='CUTTING_GROUP_RETURN' then (select case",
     "        when r.source_type='BC_NOTE_RETURN_CREDIT' then (select x.unit_cost_snapshot from erp.material_stock_movements x\n"
     "            where x.id=erp.bc_note_return_issue_movement_v1(r.source_id))\n"
     "        when r.source_type='CUTTING_GROUP_RETURN' then (select case"),
    ("  for r in select msm.*,rv.id rv_id,rv.physical_at rv_at","  for r in select msm.*,rv.id rv_id,rv.physical_at rv_at,i.adjustment_id adj_id"),
    ("            jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',0,'credit',q.amt))",
     "            jsonb_build_object('account_id',erp.bc_adjustment_account_v1(r.adj_id,'OTHER_EXPENSE'),'debit',0,'credit',q.amt))"),
    ("            jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',abs(q.amt),'credit',0),",
     "            jsonb_build_object('account_id',erp.bc_adjustment_account_v1(r.adj_id,'OTHER_EXPENSE'),'debit',abs(q.amt),'credit',0),")]

# ---------------------------------------------------------------- N3 collectible
POPULATE_SUBS=[("      cmii.total_receivable - coalesce((","      erp.bc_note_item_collectible_v1(cmii.id) - coalesce((")]
KASBON_SUBS=[("select cmi.contractor_id,coalesce(cmii.total_receivable,0) into v_issue_contractor,v_total",
              "select cmi.contractor_id,erp.bc_note_item_collectible_v1(cmii.id) into v_issue_contractor,v_total")]
REFRESH_SUBS=[("  SELECT COALESCE(total_receivable,0) INTO v_total\n","  SELECT erp.bc_note_item_collectible_v1(id) INTO v_total\n")]
CHECKS_SUBS=[("HAVING COALESCE(SUM(CASE WHEN ps.id IS NOT NULL THEN pd.amount ELSE 0 END),0)>COALESCE(cmii.total_receivable,0)+0.01",
              "HAVING COALESCE(SUM(CASE WHEN ps.id IS NOT NULL THEN pd.amount ELSE 0 END),0)>erp.bc_note_item_collectible_v1(cmii.id)+0.01"),
             ("SELECT cmii.id,cmii.payroll_status,COALESCE(cmii.total_receivable,0) total_receivable,",
              "SELECT cmii.id,cmii.payroll_status,erp.bc_note_item_collectible_v1(cmii.id) total_receivable,")]

# ---------------------------------------------------------------- N4 carry accrual
APPROVE_SUBS=[("  where payroll_id=p.id and source_type not in('ACCESSORY_BOM','OPENING_PAYABLE');",
               "  -- BC: a carried note return credit was recognized as CONTRACTOR_PAYABLE at the credit.\n"
               "  where payroll_id=p.id and source_type not in('ACCESSORY_BOM','OPENING_PAYABLE','BC_RETURN_CARRY');")]

# ---------------------------------------------------------------- N5 note facade
ISSUE_SUBS=[
    ("declare v_action text:=upper(btrim(p_action));v_cached jsonb;v_result jsonb;v_native jsonb;v_line jsonb;v_quote jsonb;",
     "declare v_action text:=upper(btrim(p_action));v_cached jsonb;v_result jsonb;v_native jsonb;v_line jsonb;v_quote jsonb;v_free jsonb;"),
    ("array['material_id','qty','mode','manual_price','price_version_id','factor'],'accessory issue line');",
     "array['material_id','qty','mode','manual_price','price_version_id','factor','free_policy_version'],'accessory issue line');"),
    ("   else raise exception 'Pilih harga master atau eceran per pcs';end if;",
     "   elsif v_line->>'mode'='FREE' then\n"
     "    -- BC (ERP-DEC02): only a category on the owner's Special free list, for a Special contractor at the physical time.\n"
     "    if v_line ? 'manual_price' or v_line ? 'price_version_id' or v_line ? 'factor' then raise exception 'Pilih satu dasar harga';end if;\n"
     "    perform 1 from erp.bc_policy_settings_v1 where policy_key='ERP_DEC02' for share;\n"
     "    v_free:=erp.bc_free_basis_v1((v_line->>'material_id')::uuid,v_contractor,v_at);\n"
     "    if v_free is null then raise exception 'BC_FREE_NOT_ALLOWED: aksesori ini tidak gratis untuk mandor pada tanggal nota (ERP-DEC02 belum ditetapkan atau kategori/mandor tidak termasuk)';end if;\n"
     "    if v_line->>'free_policy_version' is distinct from v_free->>'policy_version' then raise exception 'STALE_PRICE: daftar kategori gratis berubah, muat ulang';end if;\n"
     "    v_items:=v_items||jsonb_build_array(jsonb_build_object('material_id',v_line->>'material_id','qty',v_line->>'qty','manual_retail_unit_price','0'));\n"
     "   else raise exception 'Pilih harga master, eceran per pcs, atau gratis Special';end if;"),
    ("   raise exception 'STALE_PRICE: harga master berubah, muat ulang';end if;\n",
     "   raise exception 'STALE_PRICE: harga master berubah, muat ulang';end if;\n"
     "  -- BC (ERP-DEC02): the free lines of this note with the policy version they used.\n"
     "  delete from erp.bc_free_issue_lines_v1 where issue_id=v_id;\n"
     "  insert into erp.bc_free_issue_lines_v1(issue_id,material_id,category_id,policy_version)\n"
     "  select v_id,m.id,m.accessory_category_id,(x->>'free_policy_version')::bigint from jsonb_array_elements(p_payload->'items') x\n"
     "   join erp.materials m on m.id=(x->>'material_id')::uuid where x->>'mode'='FREE';\n")]
ISSUE_SUBS.append((
    "then raise exception 'Harga eceran wajib nominal nonnegatif, maksimal dua desimal';end if;\n",
    "then raise exception 'Harga eceran wajib nominal nonnegatif, maksimal dua desimal';end if;\n"
    "    -- BC (M:5023, ERP-DEC02): a price of 0 is free; free is never a way around the note price, only an owner-listed Special category.\n"
    "    if (v_line->>'manual_price')::numeric=0 then raise exception 'BC_FREE_REQUIRES_POLICY: harga eceran 0 hanya lewat gratis Special yang ditetapkan owner (ERP-DEC02)';end if;\n"))
WORKSPACE_SUBS=[
    ("from erp.locations where is_active and location_type='RAW_MATERIAL_WAREHOUSE'),'[]'::jsonb),",
     "from erp.locations where is_active and location_type='RAW_MATERIAL_WAREHOUSE'\n"
     "    and not exists(select 1 from erp.bc_accessory_zones_v1 z where z.location_id=locations.id)),'[]'::jsonb),"),
    ("'materials',coalesce((select jsonb_agg(quote||jsonb_build_object('stock',stock) order by quote->>'name',id) from selected),'[]'::jsonb),",
     "'materials',coalesce((select jsonb_agg(quote||jsonb_build_object('stock',stock,'free',erp.bc_free_basis_v1(id,v_contractor,v_at)) order by quote->>'name',id) from selected),'[]'::jsonb),"),
    ("'amount',i.total_receivable::numeric(24,6)::text,'payroll_status',i.payroll_status) order by i.id)",
     "'amount',i.total_receivable::numeric(24,6)::text,'payroll_status',i.payroll_status,\n"
     "     'free',exists(select 1 from erp.bc_free_issue_lines_v1 f where f.issue_id=i.issue_id and f.material_id=i.material_id),\n"
     "     'collectible',round(erp.bc_note_item_collectible_v1(i.id),2)::text) order by i.id)"),
    ("   'payroll_locked',exists(",
     "   'rounding',(select jsonb_build_object('document_id',r.id,'amount',r.amount::text,'row_version',d.row_version::text)\n"
     "     from erp.bc_note_roundings_v1 r join erp.bc_documents_v1 d on d.id=r.id where r.issue_id=h.id and d.status='POSTED'),\n"
     "   'payroll_locked',exists(")]

# ---------------------------------------------------------------- N6 opening note credit
CREDIT_LINES_SUBS=[("  if c.credit_kind in('CUSTOMER_ALLOWANCE','CUSTOMER_CREDIT_APPLY') then",
                    "  -- BC (ALL-C02): a note return credited on the imported mandor receivable.\n"
                    "  if c.credit_kind='ACCESSORY_NOTE_RETURN' then return erp.bc_opening_note_credit_lines_v1(p_settlement_id);end if;\n"
                    "  if c.credit_kind in('CUSTOMER_ALLOWANCE','CUSTOMER_CREDIT_APPLY') then")]
CREDIT_ACCOUNT_SUBS=[("  select case c.credit_kind when 'CUSTOMER_ALLOWANCE' then erp.account_id('SALES_REVENUE')",
                      "  select case c.credit_kind when 'ACCESSORY_NOTE_RETURN' then erp.account_id('MATERIAL_RECOVERY') when 'CUSTOMER_ALLOWANCE' then erp.account_id('SALES_REVENUE')")]

# ---------------------------------------------------------------- N7 import pipeline (BB texts)
def entities(extra):
    return ','.join("'%s'"%e for e in extra)
STAGE_SUBS=[("'OPEN_SALES_DRAFT') then\n    raise exception 'Unsupported migration entity_type %'",
             "'OPEN_SALES_DRAFT',"+entities(NEW_ENTITIES)+") then\n    raise exception 'Unsupported migration entity_type %'")]
BASE_SUBS=[("'OPEN_SALES_DRAFT')","'OPEN_SALES_DRAFT',"+entities(NEW_ENTITIES)+")")]
FINAL_SUBS=[("'OPEN_SALES_DRAFT') and posted_entity_id is null)","'OPEN_SALES_DRAFT',"+entities(NEW_ENTITIES)+") and posted_entity_id is null)")]
ROUTER_SUBS=[("     perform erp.bb_validate_sales_imports_v1(b.id);\n",
              "     perform erp.bb_validate_sales_imports_v1(b.id);\n     perform erp.bc_validate_imports_v1(b.id);\n"),
             ("       perform erp.bb_apply_sales_imports_v1(b.id);\n",
              "       perform erp.bb_apply_sales_imports_v1(b.id);\n       perform erp.bc_apply_imports_v1(b.id);\n")]
WS_SUBS=[("||erp.bb_sales_workspace_v1(b.id);","||erp.bb_sales_workspace_v1(b.id)||erp.bc_import_workspace_v1(b.id);")]
REV_SUBS=[("   'bb_production',erp.bb_production_revision_part_v1(p_batch_id)\n )::text",
           "   'bb_production',erp.bb_production_revision_part_v1(p_batch_id),\n   'bc',erp.bc_import_revision_part_v1(p_batch_id)\n )::text")]

# ---------------------------------------------------------------- N8 coverage
COVER_OLD='''"erp.bb_open_sales_draft_lines_v1.product_id":{"class":"DERIVED","reason":"Provenance of a sales draft open at cutover; the sale is its native sales_items line (reservation of existing stock)"},'''
COVER_NEW=COVER_OLD+'''"erp.bc_customer_custody_v1.product_id":{"class":"SOURCE_DOCUMENT","reason":"A customer-owned garment in service (ACC-C10); never company stock, no stock fact"},'''

# ---------------------------------------------------------------- N9 provenance detector (fixture v2.6.5)
# Found while testing BC (reproduced on the BB chain without BC): a note line with the owner-decided manual retail price
# (ACC-DEC02, M:1066) has no price version by design and tripped CRITICAL contractor_issue_price_provenance_gap. The
# detector keeps flagging a line with neither a price version nor a typed retail price.
PROVENANCE_SUBS=[("  where (m.material_type='ACCESSORY' and i.accessory_price_version_id is null)",
                  "  where (m.material_type='ACCESSORY' and i.accessory_price_version_id is null and i.manual_retail_unit_price is null)")]

# ---------------------------------------------------------------- F4 opening settlement read (BB text)
# Found while testing BC (the ALL-A01 continuation, reproduced on the BB chain without BC): an opening balance paid from an
# imported advance has a settlement without cash account and without credit row; its 'reversible' flag evaluated
# false OR NULL = NULL, and the import page (which refuses a flag that is not a boolean) hid the whole batch. The flag is
# false there: such a settlement is reversed through the advance (PREPAYMENT REVERSE_PAYMENT), not the settlement facade.
FINANCIAL_WS_SUBS=[("            'reversible',s.status='POSTED' and c.credit_kind is distinct from 'CUSTOMER_CREDIT_APPLY' and s.cash_account_id is not null or\n"
                    "              (s.status='POSTED' and c.credit_kind in('CUSTOMER_ALLOWANCE','SUPPLIER_ALLOWANCE','VENDOR_ALLOWANCE')))",
                    "            'reversible',coalesce(s.status='POSTED' and c.credit_kind is distinct from 'CUSTOMER_CREDIT_APPLY' and s.cash_account_id is not null or\n"
                    "              (s.status='POSTED' and c.credit_kind in('CUSTOMER_ALLOWANCE','SUPPLIER_ALLOWANCE','VENDOR_ALLOWANCE')),false))")]

REPLACED=['erp.post_material_adjustment(uuid)','erp._cp6_material_adjustment_revaluation_state(uuid)',
          'erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','erp.sync_material_cost_revaluation(uuid)',
          'erp.populate_payroll_draft(uuid)','erp.validate_material_kasbon_deduction()','erp.refresh_contractor_issue_payroll_status(uuid)',
          'erp.run_integrity_checks()','erp.approve_payroll(uuid)','erp.save_accessory_issue_action_v1(text,jsonb,uuid)',
          'erp.get_accessory_issue_workspace_v1(jsonb)','erp.bb_opening_credit_lines_v1(uuid)','erp.bb_opening_credit_account_v1(uuid)',
          'erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)','erp._validate_migration_batch_base(uuid)',
          'erp.finalize_migration_batch(uuid)','erp.save_initial_import_action_v1(text,jsonb,uuid)',
          'erp.get_initial_import_workspace_v1(uuid)','erp.initial_import_revision_v1(uuid)','erp.assert_new_stock_cutoff_coverage_v1()',
          'erp.run_v265_gudang_write_integrity_checks()','erp.bb_financial_workspace_v1(uuid)']
NEW_TABLES=['bc_policy_settings_v1','bc_policy_setting_events_v1','bc_accessory_zones_v1','bc_execution_context_v1',
            'bc_documents_v1','bc_document_links_v1','bc_adjustment_purposes_v1','bc_internal_use_lines_v1','bc_outstanding_returns_v1',
            'bc_customer_custody_v1','bc_return_lots_v1','bc_lot_events_v1','bc_count_variances_v1','bc_opening_note_lines_v1',
            'bc_note_roundings_v1','bc_free_issue_lines_v1']


def objects():
    return '\n'.join(p.read_text().rstrip('\n') for p in OBJECTS)


def new_functions():
    text=objects();found=[]
    for m in re.finditer(r'(?i)create or replace function ((?:erp|public)\.[a-z0-9_]+)\(',text):found.append(m.group(1))
    return found


def catalog():
    base=bb.catalog();extra=json.loads(CATALOG_BC.read_text())
    assert not set(base)&set(extra),'BC_CATALOG_OVERLAP'
    for e in NEW_ENTITIES:assert e in extra,('BC_CATALOG_ENTITY_MISSING',e)
    return {**base,**extra}


def router():
    body=substitute(last_definition(BB,'save_initial_import_action_v1'),ROUTER_SUBS,'router')
    old=re.search(r"v_catalog constant jsonb:=('.*?')::jsonb;",body,re.S)
    assert old and body.count(old.group(0))==1
    return body.replace(old.group(0),'v_catalog constant jsonb:='+"'"+json.dumps(catalog(),ensure_ascii=False).replace("'","''")+"'"+'::jsonb;')


def build():
    adjustment=fixture('post_material_adjustment',ADJ_SUBS,edits=ADJ_EDITS)
    state=adjustment_state()
    core=substitute(bb.function(AO,CORE_HEAD,[]),[(CORE_OLD,CORE_NEW)],'core')
    reval=substitute(last_definition(BA,'sync_material_cost_revaluation'),REVAL_SUBS,'revaluation')
    populate=substitute(last_definition(AC,'populate_payroll_draft'),POPULATE_SUBS,'populate')
    kasbon=fixture('validate_material_kasbon_deduction',KASBON_SUBS)
    refresh=fixture('refresh_contractor_issue_payroll_status',REFRESH_SUBS)
    checks=substitute(last_definition(AC,'run_integrity_checks'),CHECKS_SUBS,'integrity checks')
    approve=substitute(last_definition(BB,'approve_payroll'),APPROVE_SUBS,'approve')
    issue=substitute(last_definition(AP,'save_accessory_issue_action_v1'),ISSUE_SUBS,'note facade')
    workspace=substitute(last_definition(AP,'get_accessory_issue_workspace_v1'),WORKSPACE_SUBS,'note workspace')
    credit_lines=substitute(last_definition(BB,'bb_opening_credit_lines_v1'),CREDIT_LINES_SUBS,'credit lines')
    credit_account=substitute(last_definition(BB,'bb_opening_credit_account_v1'),CREDIT_ACCOUNT_SUBS,'credit account')
    stage=substitute(last_definition(BB,'stage_migration_row'),STAGE_SUBS,'stage')
    base=substitute(last_definition(BB,'_validate_migration_batch_base'),BASE_SUBS,'base')
    final=substitute(last_definition(BB,'finalize_migration_batch'),FINAL_SUBS,'finalize')
    ws=substitute(last_definition(BB,'get_initial_import_workspace_v1'),WS_SUBS,'import workspace')
    rev=substitute(last_definition(BB,'initial_import_revision_v1'),REV_SUBS,'revision')
    cover=substitute(last_definition(BB,'assert_new_stock_cutoff_coverage_v1'),[(COVER_OLD,COVER_NEW)],'coverage')
    provenance=fixture('run_v265_gudang_write_integrity_checks',PROVENANCE_SUBS)
    financial_ws=substitute(last_definition(BB,'bb_financial_workspace_v1'),FINANCIAL_WS_SUBS,'financial workspace')
    parts=['-- CP6 BC accessory service/return workflow, accessory policy settings and ALL-C02/C03 (owner decision 25 Sep 2026): T1_FAMILY development install (NOT a release package).',
           '-- Generated by scripts/cp6_bc_build.py from scripts/cp6_bc_objects_*.sql, the fixture, the AC/AO/AP/20t migrations and the BA/BB T1 files; do not edit by hand.',
           'begin;',"set local lock_timeout='10s';set local statement_timeout='240s';set local search_path='';",
           'do $t1_guard$','begin',
           " if not exists(select 1 from erp.schema_migrations where version='v2.6.20bb') then raise exception 'BC_T1_REQUIRES_BB'; end if;",
           f" if exists(select 1 from erp.schema_migrations where version='{VERSION}') or to_regclass('erp.bc_documents_v1') is not null then raise exception 'BC_T1_ALREADY_INSTALLED'; end if;",
           'end $t1_guard$;',objects(),adjustment,state,core,reval,populate,kasbon,refresh,checks,approve,issue,workspace,
           credit_lines,credit_account,stage,base,final,router(),ws,rev,cover,provenance,financial_ws,
           'do $coverage$ begin perform erp.assert_new_stock_cutoff_coverage_v1(); end $coverage$;',
           f"insert into erp.schema_migrations(version,description) values('{VERSION}',"
           "'T1_FAMILY development install of BC (accessory service post, internal use by purpose, return receipt and inspection, custody with pending value, note return credit, whole-rupiah rounding, Special free lines, policy settings ACC-DEC01/03..07 and ERP-DEC02, ALL-C02/C03 import); not a release package');",
           'commit;','']
    return '\n'.join(parts)


if __name__=='__main__':
    text=build()
    if '--check' in sys.argv:
        assert OUT.read_text()==text,'supabase/dev/cp6_bc_t1_family.sql is stale; rerun scripts/cp6_bc_build.py'
        print('fresh',hashlib.sha256(text.encode()).hexdigest())
    else:
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(text)
        print(OUT.relative_to(ROOT),len(text),hashlib.sha256(text.encode()).hexdigest())
