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
  On the invoice path (rev6, independent reviews 24 Sep of rev4 and rev5) the correction follows each piece by daily
  balances: for every date of a physical fact (an FG movement of the PO's lots, reversals and voided lots included; the
  cutting day of a group in a cutting batch) the correction held in FG, COGS and other is each lot's per-piece correction
  as of that date times its pieces in FG, sold (sales, returns and their reversals) and out otherwise (adjustment, BS,
  relabel and their reversals); each date posts the change of these balances, WIP balancing, and the last date takes the
  exact remainder to the targets. History: rev3 split the PO change by pieces (a later cut's correction on an earlier
  lot); rev4 counted current pieces only (write-offs and conversions left WIP negative); rev5 followed movements but
  ignored reversed sales (FG negative), voided lots, cutting batches pooled across days (proven natively, WIP -2.29) and
  relabelled lots without a sync of their own. Per-piece correction of a lot: its HPP now minus the HPP last posted
  (erp.po_hpp_gl_lot_state_v1 when written with or after the PO state; else the version current at the last sync; else
  the lot's first version; else zero); a voided lot takes the correction of the live lots of its cutting group; a lot of
  a cutting batch takes, as of each date, the batch material correction of the groups cut by then over their pieces
  (erp.po_hpp_gl_group_state_v1 keeps each group's material value at the last sync) plus its own non-material part.
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
  v_cap date;v_end date;v_sf numeric(24,6):=0;v_sc numeric(24,6):=0;v_so numeric(24,6):=0;
begin"""

POST_START="""  if abs(v_df)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_df>0"""
POST_END="""  insert into erp.po_hpp_gl_state(po_id,base_output_qty,hpp_total_cost,fg_value,cogs_value,other_out_value,updated_at)"""
POST_NEW_HEAD="""  -- AY (owner, 24 Sep 2026): on the late supplier invoice path the correction of each piece is dated from the physical
  -- facts of that piece: WIP -> FG when it enters FG, FG -> COGS when it is sold (back when returned or when the sale is
  -- reversed), FG -> other when it is written off, BS'd or relabelled; never before the piece was there. Per-account
  -- totals equal the previous single journal (the last date takes the exact remainder).
  -- The period rule is applied as before AY when the effective date E is already closed: every date is capped at E,
  -- so the correction is one journal with economic date E that post_journal (erp.resolve_accounting_transaction_date)
  -- posts on the recognition day; no report before that day changes and the economic date is kept. Only an open E
  -- moves forward to the goods (an open E caps the physical dates at today: the product allows a physical time a few
  -- minutes ahead of the clock).
  v_cap:=erp._cp3_business_date(statement_timestamp());
  if exists(select 1 from erp.accounting_period_control c
            where c.singleton_id=1 and c.closed_through is not null and p_effective_date<=c.closed_through) then
    v_cap:=p_effective_date;
  end if;
  if erp.invoice_recost_economic_date_v1() is null then
  -- Independent review 24 Sep (M1): outside a late supplier invoice the posting is exactly the AS posting (one journal on
  -- the caller's date); several callers pass a physical date (FG adjustment, QC, laundry receipt, ...), whose write-off
  -- must stay on that date.
"""

POST_NEW_TAIL="""  else
  -- rev6 (independent reviews 24 Sep of rev4 and rev5): daily balances. For every date D of a physical fact (an FG
  -- movement of the PO's lots, including reversals and voided lots; the cutting day of a group in a cutting batch) the
  -- correction held in FG, COGS and other is each lot's per-piece correction as of D times its pieces in FG, sold
  -- (sales and returns and their reversals) and out otherwise (adjustment, BS, relabel, and their reversals) as of D;
  -- each date posts the change of those balances (cents), WIP balancing, and the last date the exact remainder to the
  -- targets. Per-piece correction of a lot: its HPP now minus the HPP last posted (erp.po_hpp_gl_lot_state_v1 when
  -- written with or after the PO state; else the version current at the last sync; else the lot's first version, for a
  -- lot made by a flow that does not sync, e.g. a relabel; else zero). A voided lot takes the correction of the live
  -- lots of its cutting group. A lot of a cutting batch (erp.rebuild_po_hpp pools material over the batch) takes, as of
  -- D, the batch's material correction of the groups cut by D over their pieces, plus its own non-material part; the
  -- group corrections come from erp.po_hpp_gl_group_state_v1 (material value at the last sync); a batch without fresh
  -- group state falls back to the lot's constant correction.
  v_end:=p_effective_date;
  for r in
    with lot as(
      select fl.id,fl.lot_origin,coalesce(fl.cutting_group_id,qi.cutting_group_id) grp,cg.cutting_batch_id pool,
        coalesce((select max(case when coalesce(hv.qty_basis_pcs,0)>0 then hv.total_cost/hv.qty_basis_pcs else 0 end)
                  from erp.hpp_versions hv where hv.lot_id=fl.id and hv.is_current),0)::numeric h,
        coalesce((select ls.hpp_per_pcs from erp.po_hpp_gl_lot_state_v1 ls where ls.lot_id=fl.id and ls.updated_at>=s.updated_at),
                 (select case when coalesce(ov.qty_basis_pcs,0)>0 then ov.total_cost/ov.qty_basis_pcs else 0 end
                  from erp.hpp_versions ov where ov.lot_id=fl.id and ov.calculated_at<=s.updated_at
                  order by ov.calculated_at desc,ov.version_no desc limit 1),
                 (select case when coalesce(fv.qty_basis_pcs,0)>0 then fv.total_cost/fv.qty_basis_pcs else 0 end
                  from erp.hpp_versions fv where fv.lot_id=fl.id order by fv.version_no,fv.calculated_at limit 1),0)::numeric o
      from erp.fg_lots fl left join erp.qc_inspection_items qi on qi.id=fl.qc_item_id
      left join erp.cutting_groups cg on cg.id=coalesce(fl.cutting_group_id,qi.cutting_group_id)
      where fl.po_id=p_po_id and fl.lot_origin in('PRODUCTION','CONVERSION','VOIDED_PRODUCTION')
    ), gd as(
      -- Material correction per piece of each cutting group of the PO since the last sync (group state).
      select g.id,(coalesce((select sum(-mm.qty_signed*mm.unit_cost_snapshot) from erp.material_stock_movements mm
          where mm.source_id=g.id and mm.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN')),0)
          -gs.material_value)/nullif((select gt.total_pcs from erp.v_cutting_group_totals gt where gt.cutting_group_id=g.id),0) dm
      from erp.cutting_groups g join erp.po_hpp_gl_group_state_v1 gs on gs.cutting_group_id=g.id where g.po_id=p_po_id
    ), lotd as(
      select l.id,l.pool,case when l.lot_origin='VOIDED_PRODUCTION'
          then coalesce((select avg(l2.h-l2.o) from lot l2 where l2.grp=l.grp and l2.lot_origin='PRODUCTION'),
                        (select gd.dm from gd where gd.id=l.grp),0)
          else l.h-l.o end dh
      from lot l
    ), pg as(
      select g.id,g.cutting_batch_id pool,
        greatest(p_effective_date,least(v_cap,coalesce((select min(erp._cp3_business_date(mm.physical_at)) from erp.material_stock_movements mm
          where mm.source_id=g.id and mm.source_type='CUTTING_GROUP'),erp._cp3_business_date(g.cut_at)))) cd,
        coalesce((select gt.total_pcs from erp.v_cutting_group_totals gt where gt.cutting_group_id=g.id),0)::numeric pcs,
        coalesce((select sum(-mm.qty_signed*mm.unit_cost_snapshot) from erp.material_stock_movements mm
          where mm.source_id=g.id and mm.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN')),0)::numeric mv,
        (select gs.material_value from erp.po_hpp_gl_group_state_v1 gs where gs.cutting_group_id=g.id) mv_old
      from erp.cutting_groups g where g.cutting_batch_id in(select l.pool from lotd l where l.pool is not null)
    ), pool_ok as(
      select pool,sum(mv-mv_old)/sum(pcs) dm_final from pg group by pool having bool_and(mv_old is not null) and sum(pcs)>0
    ), ev as(
      select m.lot_id,greatest(p_effective_date,least(v_cap,erp._cp3_business_date(m.physical_at))) d,
        coalesce(o.movement_type,m.movement_type) k,m.qty_signed::numeric q
      from erp.fg_stock_movements m join lotd l on l.id=m.lot_id
      left join erp.fg_stock_movements o on m.movement_type='REVERSAL' and o.id=m.reversal_of_id
      where coalesce(o.movement_type,m.movement_type) in('QC_GOOD','REWORK_IN','OPENING','SALE','SALE_RETURN',
                                                         'ADJUSTMENT','BS_OUT','REBRAND_OUT','REBRAND_IN')
    ), dates as(
      select d from ev union select pg.cd from pg join pool_ok k on k.pool=pg.pool
    ), cum as(
      select dt.d,e.lot_id,
        sum(case when e.k in('QC_GOOD','REWORK_IN','OPENING') then e.q else 0 end) p,
        sum(case when e.k in('SALE','SALE_RETURN') then -e.q else 0 end) sd,
        sum(case when e.k in('ADJUSTMENT','BS_OUT','REBRAND_OUT','REBRAND_IN') then -e.q else 0 end) ot
      from dates dt join ev e on e.d<=dt.d group by dt.d,e.lot_id
    ), cval as(
      select c.d,c.p,c.sd,c.ot,
        case when k.pool is null then l.dh
          else coalesce((select sum(g.mv-g.mv_old)/nullif(sum(g.pcs),0) from pg g where g.pool=k.pool and g.cd<=c.d),0)+(l.dh-k.dm_final)
        end cv
      from cum c join lotd l on l.id=c.lot_id left join pool_ok k on k.pool=l.pool
    )
    select d,sum(cv*(p-sd-ot)) f,sum(cv*sd) c,sum(cv*ot) o from cval group by d order by d
  loop
    -- The change of the rounded balances since the previous date; the total is rounded once and FG takes the rest, so a
    -- pure sale day (FG -> COGS) moves no cent through WIP (independent review of rev6, m-1).
    v_f:=round(r.f+r.c+r.o,2)-round(r.c,2)-round(r.o,2);
    v_acc:=erp.po_hpp_gl_leg_add_v1(v_acc,r.d,v_f-v_sf,round(r.c,2)-v_sc,round(r.o,2)-v_so);
    v_sf:=v_f;v_sc:=round(r.c,2);v_so:=round(r.o,2);v_end:=greatest(v_end,r.d);
  end loop;
  -- The last date takes the exact remainder to the targets (rounding, or anything the balances do not explain).
  v_acc:=erp.po_hpp_gl_leg_add_v1(v_acc,v_end,v_df-v_sf,v_dc-v_sc,v_do-v_so);
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
    -- The other bucket stays on one account, the one the AS journal would use for the PO's total other change, so each
    -- account's total equals the AS journal (independent review of rev6, M-3/F5).
    if abs(v_o)>0.005 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key',case when v_do>=0 then 'OTHER_EXPENSE' else 'OTHER_INCOME' end,
      'debit',greatest(v_o,0),'credit',greatest(-v_o,0),'po_id',p_po_id)); end if;
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
  -- The HPP this sync posted for each lot and the material value of each cutting group: the bases of the next sync.
  insert into erp.po_hpp_gl_lot_state_v1(lot_id,po_id,hpp_per_pcs,updated_at)
  select fl.id,p_po_id,coalesce((select max(case when coalesce(hv.qty_basis_pcs,0)>0 then hv.total_cost/hv.qty_basis_pcs else 0 end)
    from erp.hpp_versions hv where hv.lot_id=fl.id and hv.is_current),0),statement_timestamp()
  from erp.fg_lots fl where fl.po_id=p_po_id and fl.lot_origin in('PRODUCTION','CONVERSION','VOIDED_PRODUCTION')
  on conflict(lot_id) do update set po_id=excluded.po_id,hpp_per_pcs=excluded.hpp_per_pcs,updated_at=excluded.updated_at;
  insert into erp.po_hpp_gl_group_state_v1(cutting_group_id,po_id,material_value,updated_at)
  select g.id,p_po_id,coalesce((select sum(-mm.qty_signed*mm.unit_cost_snapshot) from erp.material_stock_movements mm
    where mm.source_id=g.id and mm.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN')),0),statement_timestamp()
  from erp.cutting_groups g where g.po_id=p_po_id
  on conflict(cutting_group_id) do update set po_id=excluded.po_id,material_value=excluded.material_value,updated_at=excluded.updated_at;

"""

TABLE="""create table erp.po_hpp_gl_lot_state_v1(
  lot_id uuid primary key,
  po_id uuid not null,
  hpp_per_pcs numeric not null,
  updated_at timestamptz not null default statement_timestamp());
comment on table erp.po_hpp_gl_lot_state_v1 is 'AY: HPP per piece of each lot as erp.sync_po_hpp_to_gl last posted it (base of the per-lot correction of the next sync).';
alter table erp.po_hpp_gl_lot_state_v1 enable row level security;
revoke all on erp.po_hpp_gl_lot_state_v1 from public,anon,authenticated,service_role;
create table erp.po_hpp_gl_group_state_v1(
  cutting_group_id uuid primary key,
  po_id uuid not null,
  material_value numeric not null,
  updated_at timestamptz not null default statement_timestamp());
comment on table erp.po_hpp_gl_group_state_v1 is 'AY rev6: material value of each cutting group at the last erp.sync_po_hpp_to_gl (base of the batch-pool correction by cutting day).';
alter table erp.po_hpp_gl_group_state_v1 enable row level security;
revoke all on erp.po_hpp_gl_group_state_v1 from public,anon,authenticated,service_role;"""

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
           f" if exists(select 1 from erp.schema_migrations where version='{VERSION}') or to_regprocedure('erp.po_hpp_gl_leg_add_v1(jsonb,date,numeric,numeric,numeric)') is not null or to_regclass('erp.po_hpp_gl_lot_state_v1') is not null or to_regclass('erp.po_hpp_gl_group_state_v1') is not null then raise exception 'AY_T1_ALREADY_INSTALLED'; end if;",
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
