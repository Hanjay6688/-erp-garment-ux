#!/usr/bin/env python3
"""Build the AY T1 family install: PO HPP corrections dated from the physical date of the goods (owner, 24 Sep 2026).

Owner decision (quoted): "Saya pilih Geser tanggal recost. Jangan catat penurunan nilai barang jadi pada 23 Agustus
ketika barang jadinya baru ada 24 Agustus. Alokasikan koreksi ke barang jadi sejak tanggal fisiknya dan ke HPP untuk
bagian yang terjual, dengan tanggal jurnal mengikuti aturan periode terbuka/tertutup yang sudah diputuskan. Pertahankan
pemeriksaan saldo negatif per tanggal."

Finding (T2 run 5/6): erp.sync_po_hpp_to_gl posts one journal per PO at the recost date, which on the invoice path is the
invoice date (often the material receipt day). A late invoice that lowers the price therefore credits FG_INVENTORY on a
day before the FG lot existed, the daily FG balance is negative that day and the AW engine holds every later close.

AY keeps the PO targets, the state and the per-PO deltas of the current function (AS) exactly and replaces only how the
delta is posted:
  Outside a late supplier invoice (erp.invoice_recost_economic_date_v1() is null) the posting is exactly the AS posting:
  one journal on the caller's date (rev5; independent review 24 Sep, M1: callers such as FG adjustment, QC and laundry
  receipt pass a physical date, and a write-off must stay on that date).
  On the invoice path (rev5) each piece's correction follows the piece, per lot, with the lot's own HPP change since the
  last sync (erp.rebuild_po_hpp allocates material per cutting-group lineage; rev3 split the PO change by pieces and put a
  later cut's correction on an earlier lot, rev4 counted current pieces only and left WIP negative when pieces had been
  written off or converted, independent review 24 Sep, B1):
  Leg A  production in (QC_GOOD, REWORK_IN, OPENING movements, reversals as their original) moves WIP -> FG on the
         movement's physical date (not before the lot date, not before E).
  Leg C  ADJUSTMENT, BS_OUT, REBRAND_OUT/IN move FG <-> the other bucket on their physical dates.
  Leg B  sales (allocations of posted sales) move FG -> COGS on the sale date, posted returns back on the return date.
  Remainders (rounding, anything the legs do not explain) go to the latest date of the legs. The previous HPP of a lot is
  the one the function last posted (new table erp.po_hpp_gl_lot_state_v1, empty at install; used only when written with
  or after the PO state) or else the HPP version current at the last sync (calculated_at <= state updated_at).
  E is the recost date as before (invoice date on the invoice path, the caller's date otherwise). When E is already
  closed, every leg stays on E (the physical dates are capped at E): one journal with economic date E that post_journal
  posts on the recognition day of the decided period rule (erp.resolve_accounting_transaction_date), exactly as before AY,
  so no earlier report changes and the economic date is kept. T2 run 8 (35950787577) showed the first AY text dating part
  of such a correction on an open FG day before the invoice; T2 run 9 (35952233525) showed rev2 (v_from = the resolved
  date) losing the economic date E that the AR oracles require (economic E, transaction on the recognition day). Only an
  open E moves forward to the goods. Allocations are in cents with the remainder on the last bucket, so every account's
  total equals the previous single journal. Each requested date gets its own event and journal (one POSTED journal per
  source); post_journal still moves any closed date into the open period (AW B04, P07).
The function text is taken from its current definition (AS) and changed only by the checked substitutions below.
Label T1_FAMILY: development install on the disposable chain AN -> AU -> AV -> AW -> AX, not a release package.

Usage: python3 scripts/cp6_ay_build.py            # writes supabase/dev/cp6_ay_t1_family.sql
       python3 scripts/cp6_ay_build.py --check
"""
from pathlib import Path
import hashlib,sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'supabase/dev/cp6_ay_t1_family.sql'
AS=next((ROOT/'supabase/migrations').glob('*_erp_v2_6_20as_*.sql'))
VERSION='v2.6.20ay'
HEAD='CREATE OR REPLACE FUNCTION erp.sync_po_hpp_to_gl(p_po_id uuid, p_effective_date date DEFAULT ((statement_timestamp() AT TIME ZONE \'Asia/Jakarta\'::text))::date)'

DECLARE_OLD="""  v_lines jsonb:='[]'::jsonb;v_event uuid;v_journal uuid;v_documented_gain numeric(24,6):=0;
begin"""
DECLARE_NEW="""  v_lines jsonb:='[]'::jsonb;v_event uuid;v_journal uuid;v_documented_gain numeric(24,6):=0;
  v_acc jsonb:='{}'::jsonb;v_f numeric(24,6);v_c numeric(24,6);v_o numeric(24,6);v_wip numeric(24,6);r record;
  v_cap date;v_lots jsonb;v_end date;v_sf numeric(24,6):=0;v_sc numeric(24,6):=0;v_so numeric(24,6):=0;
begin"""

POST_START="""  if abs(v_df)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_df>0"""
POST_END="""  insert into erp.po_hpp_gl_state(po_id,base_output_qty,hpp_total_cost,fg_value,cogs_value,other_out_value,updated_at)"""
POST_NEW_HEAD="""  -- AY (owner, 24 Sep 2026): on the late supplier invoice path the correction reaches FG from the physical date of the
  -- goods and COGS from the sale date, never before the goods existed, with the decided closed/open period rule. Totals
  -- per account are exactly the previous single journal (cents; remainders on the latest date of the legs).
  -- The period rule is applied as before AY when the effective date E is already closed: every leg stays on E, so the
  -- correction is one journal with economic date E that post_journal (erp.resolve_accounting_transaction_date) posts on
  -- the recognition day; no report before that day changes and the economic date is kept. Only an open E moves forward
  -- to the goods (v_cap caps the physical dates at E when E is closed; every date after an open E is open as well; an
  -- open E caps them at today, since the product allows a physical time a few minutes ahead of the clock).
  v_cap:=erp._cp3_business_date(statement_timestamp());
  if exists(select 1 from erp.accounting_period_control c
            where c.singleton_id=1 and c.closed_through is not null and p_effective_date<=c.closed_through) then
    v_cap:=p_effective_date;
  end if;
  -- Per lot: its date, its current HPP per piece and its HPP change since the last sync. The previous HPP is the one this
  -- function last posted for the lot (erp.po_hpp_gl_lot_state_v1, when written together with or after the PO state) or
  -- else the lot's HPP version current at the last sync (calculated_at <= the state's updated_at); a lot never synced
  -- counts from zero (erp.rebuild_po_hpp allocates material per cutting-group lineage, so lots of one PO change by
  -- different amounts per piece; rev3 split the PO change by pieces, AZ T1 run 35968507694).
  select coalesce(jsonb_object_agg(x.id::text,jsonb_build_object('d',x.d,'h',x.h,'dh',x.h-x.o)),'{}'::jsonb)
  into v_lots
  from(
    select fl.id,greatest(p_effective_date,least(v_cap,erp._cp3_business_date(fl.produced_at))) d,
      coalesce((select case when coalesce(hv.qty_basis_pcs,0)>0 then hv.total_cost/hv.qty_basis_pcs else 0 end
                from erp.hpp_versions hv where hv.lot_id=fl.id and hv.is_current),0)::numeric h,
      coalesce((select ls.hpp_per_pcs from erp.po_hpp_gl_lot_state_v1 ls where ls.lot_id=fl.id and ls.updated_at>=s.updated_at),
               (select case when coalesce(ov.qty_basis_pcs,0)>0 then ov.total_cost/ov.qty_basis_pcs else 0 end
                from erp.hpp_versions ov where ov.lot_id=fl.id and ov.calculated_at<=s.updated_at
                order by ov.calculated_at desc,ov.version_no desc limit 1),0)::numeric o
    from erp.fg_lots fl where fl.po_id=p_po_id and fl.lot_origin in('PRODUCTION','CONVERSION')
  ) x;
  if erp.invoice_recost_economic_date_v1() is null then
  -- Independent review 24 Sep (M1): outside a late supplier invoice the posting is exactly the AS posting (one journal on
  -- the caller's date); several callers pass a physical date (FG adjustment, QC, laundry receipt, ...), whose write-off
  -- must stay on that date.
"""

POST_NEW_TAIL="""  else
  -- Invoice path: each piece's correction follows the piece. For every FG movement of a lot, on its physical date
  -- (not before the lot's date): production in (QC_GOOD, REWORK_IN, OPENING) moves the lot's HPP change x pieces from WIP
  -- to FG; ADJUSTMENT, BS_OUT and REBRAND_OUT/IN move it between FG and the other bucket (independent review 24 Sep, B1:
  -- rev4 counted current pieces only, so a write-off or conversion left WIP negative between the lot and its date).
  -- A reversal counts as its original's kind. Sales move FG -> COGS on the sale (or return) date (allocations, as the
  -- target counts them). What rounding or an unexplained difference leaves goes to the latest date of the legs.
  v_end:=p_effective_date;
  for r in select x.d,sum(x.a) a,sum(x.c) c from(
      select greatest((l.value->>'d')::date,least(v_cap,erp._cp3_business_date(m.physical_at))) d,
        case when coalesce(o.movement_type,m.movement_type) in('QC_GOOD','REWORK_IN','OPENING')
          then m.qty_signed*(l.value->>'dh')::numeric else 0 end a,
        case when coalesce(o.movement_type,m.movement_type) in('ADJUSTMENT','BS_OUT','REBRAND_OUT','REBRAND_IN')
          then m.qty_signed*(l.value->>'dh')::numeric else 0 end c
      from erp.fg_stock_movements m join jsonb_each(v_lots) l on l.key=m.lot_id::text
      left join erp.fg_stock_movements o on m.movement_type='REVERSAL' and o.id=m.reversal_of_id
      where coalesce(o.movement_type,m.movement_type) in('QC_GOOD','REWORK_IN','OPENING','ADJUSTMENT','BS_OUT','REBRAND_OUT','REBRAND_IN')) x
    group by x.d order by x.d
  loop
    v_acc:=erp.po_hpp_gl_leg_add_v1(v_acc,r.d,round(r.a,2)+round(r.c,2),0,-round(r.c,2));
    v_sf:=v_sf+round(r.a,2)+round(r.c,2);v_so:=v_so-round(r.c,2);v_end:=greatest(v_end,r.d);
  end loop;
  for r in select f.d,sum(f.a) a from(
      select greatest((l.value->>'d')::date,least(v_cap,erp._cp3_business_date(h.sale_date))) d,
             a.qty_pcs::numeric*(l.value->>'dh')::numeric a
      from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
      join erp.sales_headers h on h.id=i.sale_id join jsonb_each(v_lots) l on l.key=a.lot_id::text
      where h.status in('POSTED','PARTIAL_PAID','PAID')
      union all
      select greatest((l.value->>'d')::date,least(v_cap,erp._cp3_business_date(h.physical_at))),
             -ri.qty_pcs::numeric*(l.value->>'dh')::numeric
      from erp.sales_return_items ri join erp.sales_returns h on h.id=ri.return_id join jsonb_each(v_lots) l on l.key=ri.lot_id::text
      where h.status='POSTED') f
    group by f.d order by f.d
  loop
    v_acc:=erp.po_hpp_gl_leg_add_v1(v_acc,r.d,-round(r.a,2),round(r.a,2),0);
    v_sf:=v_sf-round(r.a,2);v_sc:=v_sc+round(r.a,2);v_end:=greatest(v_end,r.d);
  end loop;
  select greatest(v_end,coalesce(max((value->>'d')::date),v_end)) into v_end from jsonb_each(v_lots);
  -- Remainders on the latest date: COGS (FG -> COGS), other (WIP balances), FG (WIP balances); totals equal v_df/v_dc/v_do.
  v_acc:=erp.po_hpp_gl_leg_add_v1(v_acc,v_end,-(v_dc-v_sc),v_dc-v_sc,0);
  v_sf:=v_sf-(v_dc-v_sc);
  v_acc:=erp.po_hpp_gl_leg_add_v1(v_acc,v_end,v_df-v_sf,0,v_do-v_so);
  -- One event and one journal per requested date; WIP balances each date.
  for r in select key::date d,value v from jsonb_each(v_acc) order by 1 loop
    v_f:=(r.v->>'fg')::numeric;v_c:=(r.v->>'cogs')::numeric;v_o:=(r.v->>'other')::numeric;v_wip:=-(v_f+v_c+v_o);
    v_lines:='[]'::jsonb;
    if abs(v_f)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_f>0
      then jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_f,'credit',0,'po_id',p_po_id)
      else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',abs(v_f),'po_id',p_po_id) end); end if;
    if abs(v_c)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_c>0
      then jsonb_build_object('mapping_key','COGS','debit',v_c,'credit',0,'po_id',p_po_id)
      else jsonb_build_object('mapping_key','COGS','debit',0,'credit',abs(v_c),'po_id',p_po_id) end); end if;
    if abs(v_o)>0.005 then
      if v_o>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
        'mapping_key','OTHER_EXPENSE','debit',v_o,'credit',0,'po_id',p_po_id));
      else v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
        'mapping_key','OTHER_INCOME','debit',0,'credit',abs(v_o),'po_id',p_po_id)); end if;
    end if;
    if abs(v_wip)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_wip>0
      then jsonb_build_object('mapping_key','WIP','debit',v_wip,'credit',0,'po_id',p_po_id)
      else jsonb_build_object('mapping_key','WIP','debit',0,'credit',abs(v_wip),'po_id',p_po_id) end); end if;
    if jsonb_array_length(v_lines)>=2 then
      insert into erp.po_hpp_gl_events(po_id,effective_date,old_hpp_total,new_hpp_total,fg_delta,cogs_delta,other_delta)
      values(p_po_id,r.d,round(coalesce(s.hpp_total_cost,0),2),v_target_hpp,v_f,v_c,v_o)
      returning id into v_event;
      v_journal:=erp.post_journal('PO_HPP_GL_SYNC',v_event,r.d,
        'Latest corrected HPP allocation · exact minor-unit targets · dated from the goods',v_lines);
      update erp.po_hpp_gl_events set journal_entry_id=v_journal,
        effective_date=(select transaction_date from erp.journal_entries where id=v_journal) where id=v_event;
    end if;
  end loop;
  end if;
  -- The HPP this sync posted for each lot, the base of the next sync's per-lot change.
  insert into erp.po_hpp_gl_lot_state_v1(lot_id,po_id,hpp_per_pcs,updated_at)
  select key::uuid,p_po_id,(value->>'h')::numeric,statement_timestamp() from jsonb_each(v_lots)
  on conflict(lot_id) do update set po_id=excluded.po_id,hpp_per_pcs=excluded.hpp_per_pcs,updated_at=excluded.updated_at;

"""

TABLE="""create table erp.po_hpp_gl_lot_state_v1(
  lot_id uuid primary key,
  po_id uuid not null,
  hpp_per_pcs numeric not null,
  updated_at timestamptz not null default statement_timestamp());
comment on table erp.po_hpp_gl_lot_state_v1 is 'AY: HPP per piece of each lot as erp.sync_po_hpp_to_gl last posted it (base of the per-lot change of the next sync).';
alter table erp.po_hpp_gl_lot_state_v1 enable row level security;
revoke all on erp.po_hpp_gl_lot_state_v1 from public,anon,authenticated,service_role;"""

HELPER="""CREATE OR REPLACE FUNCTION erp.po_hpp_gl_leg_add_v1(p_acc jsonb, p_day date, p_fg numeric, p_cogs numeric, p_other numeric)
 RETURNS jsonb
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO ''
AS $function$
-- AY: add one dated leg (FG, COGS, other) to the per-date accumulator of erp.sync_po_hpp_to_gl.
select coalesce(p_acc,'{}'::jsonb)||jsonb_build_object(p_day::text,jsonb_build_object(
  'fg',coalesce((p_acc->(p_day::text)->>'fg')::numeric,0)+coalesce(p_fg,0),
  'cogs',coalesce((p_acc->(p_day::text)->>'cogs')::numeric,0)+coalesce(p_cogs,0),
  'other',coalesce((p_acc->(p_day::text)->>'other')::numeric,0)+coalesce(p_other,0)))
$function$;"""


def sync_function():
    text=AS.read_text()
    assert text.count(HEAD)==1
    start=text.index(HEAD);end=text.index('$function$;',start)+len('$function$;')
    body=text[start:end]
    assert body.count(DECLARE_OLD)==1 and body.count(POST_START)==1 and body.count(POST_END)==1
    a=body.index(POST_START);b=body.index(POST_END)
    return body[:a].replace(DECLARE_OLD,DECLARE_NEW)+POST_NEW_HEAD+body[a:b]+POST_NEW_TAIL+body[b:]


def build():
    parts=['-- CP6 AY PO HPP corrections dated from the goods: T1_FAMILY development install (NOT a release package).',
           '-- Generated by scripts/cp6_ay_build.py from the AS definition of erp.sync_po_hpp_to_gl; do not edit by hand.',
           'begin;',"set local lock_timeout='10s';set local statement_timeout='240s';set local search_path='';",
           'do $t1_guard$','begin',
           " if (select count(*) from erp.schema_migrations where version in('v2.6.20av','v2.6.20aw','v2.6.20ax'))<>3 then raise exception 'AY_T1_REQUIRES_AV_AW_AX'; end if;",
           f" if exists(select 1 from erp.schema_migrations where version='{VERSION}') or to_regprocedure('erp.po_hpp_gl_leg_add_v1(jsonb,date,numeric,numeric,numeric)') is not null or to_regclass('erp.po_hpp_gl_lot_state_v1') is not null then raise exception 'AY_T1_ALREADY_INSTALLED'; end if;",
           'end $t1_guard$;',TABLE,HELPER,
           'revoke all on function erp.po_hpp_gl_leg_add_v1(jsonb,date,numeric,numeric,numeric) from public,anon,authenticated,service_role;',
           sync_function(),
           f"insert into erp.schema_migrations(version,description) values('{VERSION}',"
           "'T1_FAMILY development install of AY (PO HPP corrections dated from the goods); not a release package');",'commit;','']
    return '\n'.join(parts)


if __name__=='__main__':
    text=build()
    if '--check' in sys.argv:
        assert OUT.read_text()==text,'supabase/dev/cp6_ay_t1_family.sql is stale; rerun scripts/cp6_ay_build.py'
        print('fresh',hashlib.sha256(text.encode()).hexdigest())
    else:
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(text)
        print(OUT.relative_to(ROOT),len(text),hashlib.sha256(text.encode()).hexdigest())
