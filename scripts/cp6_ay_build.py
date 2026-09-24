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
  Leg A  per lot date D = greatest(E, business date of the lot) of the PO's PRODUCTION/CONVERSION lots: FG takes each
         lot's own change (its HPP change since the last sync times FG owned + net sold pieces; rev4, see below), WIP
         balances; the change of the other bucket (write-offs, BS) goes with the latest lot date.
  Leg B  per sale or return date (greatest(lot date, business date of the sale or return)): each lot's HPP change times
         the pieces sold on that date (a posted return is negative) moves FG -> COGS.
  rev4 (independent review 24 Sep, proven natively by AZ T1 run 35968507694, AZ:MULTI_CUT_*): rev3 weighted both legs by
  pieces, but erp.rebuild_po_hpp allocates material to a lot by its cutting-group lineage; with two cuts of different
  yields and a lot between them the earlier lot took part of the later cut's correction (PO WIP -2.29 on the day between
  the cuts for a higher price, FG +5.09 instead of +2.80). The previous HPP of a lot is the one this function last posted
  (new table erp.po_hpp_gl_lot_state_v1, empty at install) or, for a lot last synced before it existed, the HPP version
  current at the last sync (calculated_at <= state updated_at); a lot never synced counts from zero.
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
  v_acc jsonb:='{}'::jsonb;v_t numeric(24,6);v_q numeric;v_w numeric;v_n integer;v_i integer;v_left numeric(24,6);
  v_amt numeric(24,6);v_last date;v_f numeric(24,6);v_c numeric(24,6);v_o numeric(24,6);v_wip numeric(24,6);r record;
  v_cap date;v_lots jsonb;
begin"""

POST_START="""  if abs(v_df)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_df>0"""
POST_END="""  insert into erp.po_hpp_gl_state(po_id,base_output_qty,hpp_total_cost,fg_value,cogs_value,other_out_value,updated_at)"""
POST_NEW="""  -- AY (owner, 24 Sep 2026): the correction reaches FG from the physical date of the goods and COGS from the sale date,
  -- never before the goods existed, with the decided closed/open period rule. Totals per account are exactly the
  -- previous single journal (cents, remainder on the last bucket).
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
  v_t:=v_df+v_dc;
  -- AY rev4 (independent review 24 Sep; T1 AZ:MULTI_CUT_* run 35968507694): erp.rebuild_po_hpp allocates material to a
  -- lot by its cutting-group lineage, so lots of one PO change by different amounts per piece; rev3 split the PO change
  -- over the lot dates by pieces and put a later cut's correction on an earlier lot (PO WIP -2.29 on the day between the
  -- cuts). The change of each lot is now its own HPP change since the last sync times its quantity (FG owned + net sold,
  -- as erp.compute_po_hpp_gl_targets_v2620d counts it). The previous HPP is the one this function last posted for the lot
  -- (erp.po_hpp_gl_lot_state_v1) or, for a lot last synced before that table existed, its HPP version current at the
  -- last sync (calculated_at <= the state's updated_at, both statement timestamps); a lot never synced counts from zero.
  select coalesce(jsonb_object_agg(x.id::text,jsonb_build_object('d',x.d,'h',x.h,'dh',x.h-x.o,'q',x.q)),'{}'::jsonb),max(x.d)
  into v_lots,v_last
  from(
    select fl.id,greatest(p_effective_date,least(v_cap,erp._cp3_business_date(fl.produced_at))) d,
      coalesce((select case when coalesce(hv.qty_basis_pcs,0)>0 then hv.total_cost/hv.qty_basis_pcs else 0 end
                from erp.hpp_versions hv where hv.lot_id=fl.id and hv.is_current),0)::numeric h,
      coalesce((select ls.hpp_per_pcs from erp.po_hpp_gl_lot_state_v1 ls where ls.lot_id=fl.id),
               (select case when coalesce(ov.qty_basis_pcs,0)>0 then ov.total_cost/ov.qty_basis_pcs else 0 end
                from erp.hpp_versions ov where ov.lot_id=fl.id and ov.calculated_at<=s.updated_at
                order by ov.calculated_at desc,ov.version_no desc limit 1),0)::numeric o,
      (greatest(coalesce((select sum(fm.qty_signed) from erp.fg_stock_movements fm where fm.lot_id=fl.id),0)
          +coalesce((select sum(abs(fm.qty_signed)) from erp.fg_stock_movements fm where fm.lot_id=fl.id
                     and fm.movement_type='SALE_RESERVE' and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id)),0),0)
       +greatest(coalesce((select sum(a.qty_pcs) from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
                     join erp.sales_headers h on h.id=i.sale_id where a.lot_id=fl.id and h.status in('POSTED','PARTIAL_PAID','PAID')),0)
          -coalesce((select sum(ri.qty_pcs) from erp.sales_return_items ri join erp.sales_returns h on h.id=ri.return_id
                     where ri.lot_id=fl.id and h.status='POSTED'),0),0))::numeric q
    from erp.fg_lots fl where fl.po_id=p_po_id and fl.lot_origin in('PRODUCTION','CONVERSION')
  ) x;
  v_last:=coalesce(v_last,p_effective_date);
  -- Leg A: FG (and the sold part, moved on in leg B) take each lot's own change on the lot's date; WIP balances each date.
  select count(distinct value->>'d') into v_n from jsonb_each(v_lots);
  if v_n>0 then
    v_i:=0;v_left:=v_t;
    for r in select (value->>'d')::date d,sum((value->>'dh')::numeric*(value->>'q')::numeric) a
      from jsonb_each(v_lots) group by 1 order by 1
    loop
      v_i:=v_i+1;
      v_amt:=case when v_i=v_n then v_left else round(r.a,2) end;
      v_left:=v_left-v_amt;
      v_acc:=erp.po_hpp_gl_leg_add_v1(v_acc,r.d,v_amt,0,0);
    end loop;
  else
    v_acc:=erp.po_hpp_gl_leg_add_v1(v_acc,p_effective_date,v_t,0,0);
  end if;
  v_acc:=erp.po_hpp_gl_leg_add_v1(v_acc,v_last,0,0,v_do);
  -- Leg B: the sold change moves FG -> COGS on the sale (or return) date: each lot's HPP change times the pieces sold
  -- (a posted return is negative) on that date.
  select count(distinct f.d) into v_n from(
    select greatest((l.value->>'d')::date,least(v_cap,erp._cp3_business_date(h.sale_date))) d
    from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
    join erp.sales_headers h on h.id=i.sale_id join jsonb_each(v_lots) l on l.key=a.lot_id::text
    where h.status in('POSTED','PARTIAL_PAID','PAID')
    union all
    select greatest((l.value->>'d')::date,least(v_cap,erp._cp3_business_date(h.physical_at)))
    from erp.sales_return_items ri join erp.sales_returns h on h.id=ri.return_id join jsonb_each(v_lots) l on l.key=ri.lot_id::text
    where h.status='POSTED') f;
  if v_n>0 then
    v_i:=0;v_left:=v_dc;
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
      v_i:=v_i+1;
      v_amt:=case when v_i=v_n then v_left else round(r.a,2) end;
      v_left:=v_left-v_amt;
      v_acc:=erp.po_hpp_gl_leg_add_v1(v_acc,r.d,-v_amt,v_amt,0);
    end loop;
  elsif abs(v_dc)>0.005 then
    v_acc:=erp.po_hpp_gl_leg_add_v1(v_acc,v_last,-v_dc,v_dc,0);
  end if;
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
  -- AY rev4: the HPP this sync posted for each lot, the base of the next sync's per-lot change.
  insert into erp.po_hpp_gl_lot_state_v1(lot_id,po_id,hpp_per_pcs,updated_at)
  select key::uuid,p_po_id,(value->>'h')::numeric,statement_timestamp() from jsonb_each(v_lots)
  on conflict(lot_id) do update set po_id=excluded.po_id,hpp_per_pcs=excluded.hpp_per_pcs,updated_at=excluded.updated_at;

"""

TABLE="""create table erp.po_hpp_gl_lot_state_v1(
  lot_id uuid primary key,
  po_id uuid not null,
  hpp_per_pcs numeric not null,
  updated_at timestamptz not null default statement_timestamp());
comment on table erp.po_hpp_gl_lot_state_v1 is 'AY rev4: HPP per piece of each lot as erp.sync_po_hpp_to_gl last posted it (base of the per-lot change of the next sync).';
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
    return body[:a].replace(DECLARE_OLD,DECLARE_NEW)+POST_NEW+body[b:]


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
