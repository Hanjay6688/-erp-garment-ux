#!/usr/bin/env python3
"""Build the AZ T1 family install: material recost corrections dated from the physical movement (owner, 24 Sep 2026).

Owner decisions (quoted): "WIP: setujui prinsip max(tanggal ekonomi invoice, tanggal fisik potong) saat tanggal ekonomi
masih terbuka. WIP belum ada pada 1-2 Sep, jadi koreksi -Rp10 tidak boleh membuat saldo WIP negatif di dua hari itu."
and, for the AS fixture that cuts on 22 Sep, "Ikut prinsip WIP" (the material-to-WIP revaluation follows the cutting
day, the invoice journal stays on the invoice date). Same family as AY (a value correction must not precede the
physical fact it corrects), so every branch of the material recost is dated the same way.

Finding: the supplier invoice journal (MATERIAL_SUPPLIER_INVOICE, date E) corrects MATERIAL_INVENTORY for the whole
received quantity; then erp.sync_material_cost_revaluation moves the correction of every consuming movement out of
MATERIAL_INVENTORY (to WIP for cutting, cutting returns and contractor issues, to ACCESSORY_RECOVERY_COGS for issued
accessories, to MATERIAL_PURCHASE_VARIANCE for supplier returns), and erp._cp6_sync_material_adjustment_revaluation does
the same for material adjustment documents, both on E. When the movement happened after E, WIP (or the other account)
receives the correction before the material was there and MATERIAL_INVENTORY loses it while the material is still in
stock: with a lower invoice price WIP is negative between E and the cutting day.

AZ changes only the date of those two postings (and, as their consequence, of the finished-PO residual WIP close below): D = greatest(E, business date of the movement's physical_at) (for an
adjustment document, of the document's physical_at) when E is open; when E is already closed every posting stays on E
exactly as before (one journal with economic date E that post_journal posts on the recognition day, the rule AY rev3
keeps). A physical date after today (the product allows a few minutes of clock skew) is capped at today. Amounts,
accounts, state and events are unchanged. Outside an invoice E is today and nothing moves; the residual close below is
changed on the invoice path only (independent review 24 Sep: its other callers pass other dates).
Label T1_FAMILY: development install on the disposable chain AN -> AU -> AV -> AW -> AX -> AY, not a release package.

Usage: python3 scripts/cp6_az_build.py            # writes supabase/dev/cp6_az_t1_family.sql
       python3 scripts/cp6_az_build.py --check
"""
from pathlib import Path
import hashlib,sys

ROOT=Path(__file__).resolve().parents[1]
AS=ROOT/'supabase/migrations/20260922210815_erp_v2_6_20as_cp6_event_dates_product_identity.sql'
AO=ROOT/'supabase/migrations/20260922135612_erp_v2_6_20ao_cp6_invoice_retail.sql'
OUT=ROOT/'supabase/dev/cp6_az_t1_family.sql'
VERSION='v2.6.20az'

E_EXPR='coalesce(erp.invoice_recost_economic_date_v1(),erp._cp3_business_date(statement_timestamp()))'
CLOSED="""exists(select 1 from erp.accounting_period_control c
            where c.singleton_id=1 and c.closed_through is not null and v_e<=c.closed_through)"""

# ---------------------------------------------------------------- erp.sync_material_cost_revaluation (AS)
REVAL_HEAD='CREATE OR REPLACE FUNCTION erp.sync_material_cost_revaluation(p_material_id uuid)'
REVAL_DECLARE_OLD="""  v_journal uuid;
begin
  perform erp.require_internal();
"""
REVAL_DECLARE_NEW="""  v_journal uuid;
  v_e date;
  v_closed boolean;
  v_date date;
begin
  perform erp.require_internal();
  -- AZ (owner, 24 Sep 2026): a correction is dated from the physical movement it corrects when the recost date E is
  -- open, D = greatest(E, business date of the movement); a closed E keeps every posting on E (post_journal posts it
  -- on the recognition day with economic date E), as before.
  v_e:="""+E_EXPR+""";
  v_closed:="""+CLOSED+""";
"""
REVAL_DIFF_OLD="""    if abs(v_diff)>0.005 then
      if v_diff>0 then"""
REVAL_DIFF_NEW="""    if abs(v_diff)>0.005 then
      v_date:=case when v_closed then v_e
        else least(greatest(v_e,erp._cp3_business_date(r.physical_at)),erp._cp3_business_date(statement_timestamp())) end;
      if v_diff>0 then"""
REVAL_EVENT_OLD="values(p_material_id,r.id,"+E_EXPR+",v_old,v_target,v_diff,v_counterpart,v_po,v_contractor)"
REVAL_EVENT_NEW="values(p_material_id,r.id,v_date,v_old,v_target,v_diff,v_counterpart,v_po,v_contractor)"
REVAL_JOURNAL_OLD="v_journal:=erp.post_journal('MATERIAL_COST_REVALUATION',v_event,"+E_EXPR+","
REVAL_JOURNAL_NEW="v_journal:=erp.post_journal('MATERIAL_COST_REVALUATION',v_event,v_date,"

# ---------------------------------------------------------------- erp._cp6_sync_material_adjustment_revaluation (AO)
ADJ_HEAD='CREATE OR REPLACE FUNCTION erp._cp6_sync_material_adjustment_revaluation(p_adjustment uuid, p_material uuid)'
ADJ_DECLARE_OLD="declare s jsonb;v_delta jsonb;v_lines jsonb;v_event uuid;v_journal uuid;v_date date;\nbegin"
ADJ_DECLARE_NEW="declare s jsonb;v_delta jsonb;v_lines jsonb;v_event uuid;v_journal uuid;v_date date;v_e date;\nbegin"
ADJ_DATE_OLD=" v_event:=gen_random_uuid();v_date:="+E_EXPR+";"
ADJ_DATE_NEW=""" v_event:=gen_random_uuid();
 -- AZ: dated from the adjustment document's physical day when the recost date E is open; a closed E stays on E.
 v_e:="""+E_EXPR+""";
 v_date:=case when """+CLOSED+""" then v_e
   else least(greatest(v_e,(select erp._cp3_business_date(a.physical_at) from erp.material_adjustments a where a.id=p_adjustment)),
              erp._cp3_business_date(statement_timestamp())) end;"""


# ---------------------------------------------------------------- erp.sync_finished_po_wip_residual (AC)
# A consequence of AZ (and AY) the writer found before T2: the invoice path closes a FINISHED PO's residual WIP on E; with
# the revaluation on the cutting day and the HPP legs on the goods/sale days, a close on an earlier open E would leave the
# PO's WIP non-zero between E and those days. The close is therefore not dated before the PO's last WIP posting when the
# date is open; a closed date stays (post_journal posts it on the recognition day, as before).
RESIDUAL_AC=ROOT/'supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql'
RESIDUAL_HEAD="CREATE OR REPLACE FUNCTION erp.sync_finished_po_wip_residual(p_po_id uuid, p_effective_date date DEFAULT ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date, p_reason text DEFAULT 'Finished PO residual WIP close'::text)"
RESIDUAL_OLD='''  if abs(v_residual)<=0.005 then return; end if;
  insert into erp.po_wip_close_events'''
RESIDUAL_NEW='''  if abs(v_residual)<=0.005 then return; end if;
  -- AZ: on the invoice path only (a late supplier invoice), not before the PO's last WIP posting while the date is open,
  -- never after today; a closed date and every other caller (finish, laundry estimate, pocket) stay as before.
  if erp.invoice_recost_economic_date_v1() is not null and not exists(select 1 from erp.accounting_period_control c
                where c.singleton_id=1 and c.closed_through is not null and p_effective_date<=c.closed_through) then
    select least(greatest(p_effective_date,coalesce(max(je.transaction_date),p_effective_date)),erp._cp3_business_date(statement_timestamp()))
      into p_effective_date
    from erp.journal_lines jl
    join erp.journal_entries je on je.id=jl.journal_entry_id
    where je.status in ('POSTED','REVERSED')
      and jl.po_id=p_po_id and jl.account_id=v_wip_account;
  end if;
  insert into erp.po_wip_close_events'''


def function(path,head,subs,once=True):
    text=path.read_text()
    assert text.count(head)==1,(path.name,head)
    start=text.index(head);end=text.index('$function$;',start)+len('$function$;')
    body=text[start:end]
    for old,new in subs:
        assert body.count(old)==1,(head,old[:60])
        body=body.replace(old,new)
    if once:assert 'invoice_recost_economic_date_v1()' in body and body.count(E_EXPR)==1,(head,'E computed once')
    return body


def build():
    reval=function(AS,REVAL_HEAD,[(REVAL_DECLARE_OLD,REVAL_DECLARE_NEW),(REVAL_DIFF_OLD,REVAL_DIFF_NEW),
                                  (REVAL_EVENT_OLD,REVAL_EVENT_NEW),(REVAL_JOURNAL_OLD,REVAL_JOURNAL_NEW)])
    adj=function(AO,ADJ_HEAD,[(ADJ_DECLARE_OLD,ADJ_DECLARE_NEW),(ADJ_DATE_OLD,ADJ_DATE_NEW)])
    residual=function(RESIDUAL_AC,RESIDUAL_HEAD,[(RESIDUAL_OLD,RESIDUAL_NEW)],once=False)
    parts=['-- CP6 AZ material recost corrections dated from the physical movement: T1_FAMILY development install (NOT a release package).',
           '-- Generated by scripts/cp6_az_build.py from the AS/AO definitions; do not edit by hand.',
           'begin;',"set local lock_timeout='10s';set local statement_timeout='240s';set local search_path='';",
           'do $t1_guard$','begin',
           " if (select count(*) from erp.schema_migrations where version in('v2.6.20av','v2.6.20aw','v2.6.20ax','v2.6.20ay'))<>4 then raise exception 'AZ_T1_REQUIRES_AV_AW_AX_AY'; end if;",
           f" if exists(select 1 from erp.schema_migrations where version='{VERSION}') then raise exception 'AZ_T1_ALREADY_INSTALLED'; end if;",
           'end $t1_guard$;',reval,adj,residual,
           f"insert into erp.schema_migrations(version,description) values('{VERSION}',"
           "'T1_FAMILY development install of AZ (material recost corrections dated from the physical movement); not a release package');",'commit;','']
    return '\n'.join(parts)


if __name__=='__main__':
    text=build()
    if '--check' in sys.argv:
        assert OUT.read_text()==text,'supabase/dev/cp6_az_t1_family.sql is stale; rerun scripts/cp6_az_build.py'
        print('fresh',hashlib.sha256(text.encode()).hexdigest())
    else:
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(text)
        print(OUT.relative_to(ROOT),len(text),hashlib.sha256(text.encode()).hexdigest())
