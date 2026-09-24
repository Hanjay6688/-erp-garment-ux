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
  On the invoice path (rev6/rev7, independent reviews 24 Sep of rev4, rev5 and rev6) the correction follows each piece
  by daily balances: for every date of a physical fact (an FG movement of the PO's lots, reversals and voided lots
  included; a material fact behind the PO's HPP; the cutting day of a group in a cutting batch) the correction held in
  FG, COGS and other is each lot's per-piece correction as of that date times its pieces in FG, sold (sales, returns and
  their reversals) and out otherwise (adjustment, BS, relabel and their reversals); each date posts the change of these
  balances, WIP balancing, and the last date takes the exact remainder to the targets. History: rev3 split the PO
  change by pieces (a later cut's correction on an earlier lot); rev4 counted current pieces only (write-offs and
  conversions left WIP negative); rev5 followed movements but ignored reversed sales (FG negative), voided lots, cutting
  batches pooled across days (proven natively, WIP -2.29) and relabelled lots without a sync of their own; rev6 still
  dated a material fact after the lot (a cutting return, a later contractor issue, a PO-wide pool) on the lot's day
  (WIP -3.50 in the review harness), swung a reversed relabel through the other account and joined dates x movements.
  Per-piece correction of a lot: its HPP now minus the HPP last posted (erp.po_hpp_gl_lot_state_v1 when written with or
  after the PO state; else the version current at the last sync; else the lot's first version; else zero), less, as of
  each date, the part of its material correction whose fact is not there yet: erp.rebuild_po_hpp pools cutting
  material per cutting batch (over the batch's effective pieces; groups of other POs included), else per lineage group,
  else per PO, and shares non-accessory contractor material over the PO's source quantity; every such fact (cutting
  issue or return, contractor issue item) keeps its value at the last sync in erp.po_hpp_gl_material_state_v1 and its
  change is dated on the day AZ dates its WIP revaluation (a batch divides by the pieces of the groups cut by then).
  The state is written only by a sync whose HPP was rebuilt in the same statement, with a 'SYNC' marker; a fact created
  after the marker is in no posted HPP (old value zero). rev7.1 (independent review of rev7): for a PO without material
  state (produced before AY; F1) the old value of a fact comes from the HPP last rebuilt (tp): zero when the fact came
  later, else its value less the revaluations of its movement since tp (the release installs its new tables empty, so
  the state is not seeded); the function runs with jit off (F2: planner misestimate, JIT compile under the global lock);
  a relabelled lot follows its root lot through any chain of relabels (F3). A voided lot takes the correction of the
  live lots of its cutting group.
  rev7.2 (round seven, writer): the part of a fact's change explained by its revaluations since the HPP posted last
  (erp.material_cost_revaluation_events) is dated on each revaluation's own day (a non-invoice recost still queued at the
  invoice enters WIP on its day, not the fact's); a batch diluted by a group new since the last sync gets that dilution on
  the new group's cut day (review of rev7, F4); the lot state is used as the last sync wrote it (F9: the baseline refresh
  moves the PO state clock without an HPP change); the pocket-fabric part of a lot's HPP change is dated no earlier than
  the PO's pocket allocation (period end), as the pocket recost journal (AZ rev2).
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

JIT_OLD=""" SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$"""
JIT_NEW=""" SECURITY DEFINER
 SET search_path TO 'erp', 'public'
 SET jit TO 'off'
AS $function$"""

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
  -- rev6/rev7 (independent reviews 24 Sep of rev4, rev5 and rev6): daily balances. For every date D of a physical fact
  -- (an FG movement of the PO's lots, including reversals and voided lots; a material fact behind the PO's HPP; the
  -- cutting day of a group in a cutting batch) the correction held in FG, COGS and other is each lot's per-piece
  -- correction as of D times its pieces in FG, sold (sales and returns and their reversals) and out otherwise
  -- (adjustment, BS, relabel, and their reversals) as of D; each date posts the change of those balances (cents), WIP
  -- balancing, and the last date the exact remainder to the targets. Per-piece correction of a lot: its HPP now minus
  -- the HPP last posted (erp.po_hpp_gl_lot_state_v1 when written with or after the PO state; else the version current
  -- at the last sync; else the lot's first version, for a lot made by a flow that does not sync, e.g. a relabel; else
  -- zero), less the part of its material correction whose fact (erp.po_hpp_gl_material_state_v1) is dated after D.
  v_end:=p_effective_date;
  for r in
    with recursive lot0 as(
      select fl.id,fl.lot_origin,coalesce(fl.cutting_group_id,qi.cutting_group_id) grp,
        coalesce((select max(case when coalesce(hv.qty_basis_pcs,0)>0 then hv.total_cost/hv.qty_basis_pcs else 0 end)
                  from erp.hpp_versions hv where hv.lot_id=fl.id and hv.is_current),0)::numeric h,
        coalesce((select ls.hpp_per_pcs from erp.po_hpp_gl_lot_state_v1 ls where ls.lot_id=fl.id),
                 (select case when coalesce(ov.qty_basis_pcs,0)>0 then ov.total_cost/ov.qty_basis_pcs else 0 end
                  from erp.hpp_versions ov where ov.lot_id=fl.id and ov.calculated_at<=s.updated_at
                  order by ov.calculated_at desc,ov.version_no desc limit 1),
                 (select case when coalesce(fv.qty_basis_pcs,0)>0 then fv.total_cost/fv.qty_basis_pcs else 0 end
                  from erp.hpp_versions fv where fv.lot_id=fl.id order by fv.version_no,fv.calculated_at limit 1),0)::numeric o,
        (select pa.source_lot_id from erp.product_conversion_allocations pa where pa.destination_lot_id=fl.id order by pa.id limit 1) src,
        (select pc.status from erp.product_conversion_allocations pa join erp.product_conversions pc on pc.id=pa.conversion_id
          where pa.destination_lot_id=fl.id order by pa.id limit 1) cst,
        -- The pocket-fabric part of the lot HPP (erp.rebuild_po_hpp: component from POCKET_PERIOD_ALLOCATION) changed in this
        -- statement, per piece: now less the version before this statement.
        coalesce((select (coalesce((select sum(c.total_cost) from erp.hpp_version_components c
                    where c.hpp_version_id=hv.id and c.source_type='POCKET_PERIOD_ALLOCATION'),0)
                  -coalesce((select sum(c.total_cost) from erp.hpp_version_components c
                    where c.hpp_version_id=(select pv.id from erp.hpp_versions pv where pv.lot_id=fl.id and pv.calculated_at<statement_timestamp()
                                             order by pv.calculated_at desc,pv.version_no desc limit 1)
                      and c.source_type='POCKET_PERIOD_ALLOCATION'),0))/nullif(hv.qty_basis_pcs,0)
          from erp.hpp_versions hv where hv.lot_id=fl.id and hv.is_current and hv.calculated_at>=statement_timestamp()),0)::numeric dp
      from erp.fg_lots fl left join erp.qc_inspection_items qi on qi.id=fl.qc_item_id
      where fl.po_id=p_po_id and fl.lot_origin in('PRODUCTION','CONVERSION','VOIDED_PRODUCTION')
    ), grp as(
      -- The PO's cutting groups and every group of their cutting batches (a batch may hold groups of other POs; its
      -- material is pooled over all of them): pieces and the day the group was first cut.
      select g.id,g.po_id,g.cutting_batch_id batch,
        coalesce((select gt.total_pcs from erp.v_cutting_group_totals gt where gt.cutting_group_id=g.id),0)::numeric pcs,
        greatest(p_effective_date,least(v_cap,coalesce((select min(erp._cp3_business_date(mm.physical_at)) from erp.material_stock_movements mm
          where mm.source_id=g.id and mm.source_type='CUTTING_GROUP'),erp._cp3_business_date(g.cut_at)))) cd
      from erp.cutting_groups g
      where g.po_id=p_po_id or g.cutting_batch_id in(select g0.cutting_batch_id from erp.cutting_groups g0
                                                     where g0.po_id=p_po_id and g0.cutting_batch_id is not null)
    ), bt as(
      -- Each batch: pieces of its groups and the effective pieces erp.rebuild_po_hpp divides its material by.
      select gr.batch,sum(gr.pcs) spcs,
        coalesce((select vb.effective_pcs from erp.v_cutting_batch_totals vb where vb.cutting_batch_id=gr.batch),0)::numeric eff
      from grp gr where gr.batch is not null group by gr.batch
    ), mk as(
      -- When the material state was last written (a sync right after erp.rebuild_po_hpp), and tp, when the HPP posted
      -- last was rebuilt (the latest version of the PO's lots before this statement).
      select (select ms.updated_at from erp.po_hpp_gl_material_state_v1 ms where ms.po_id=p_po_id and ms.source_key='SYNC') ts,
        (select max(hv.calculated_at) from erp.hpp_versions hv join erp.fg_lots fl on fl.id=hv.lot_id
          where fl.po_id=p_po_id and hv.calculated_at<statement_timestamp()) tp
    ), fct as(
      -- Every material fact behind the PO's HPP (erp.rebuild_po_hpp): cutting issues and returns of each group (pooled per
      -- cutting batch when the group is in one; the PO-wide pool takes the PO's own groups) and non-accessory contractor
      -- issues (PO-wide over the source quantity), on the physical day erp.sync_material_cost_revaluation dates its WIP
      -- revaluation (AZ), with its value now (cur) and its value in the HPP last posted (ov): its state; else zero for a
      -- fact created after the state was written (no posted HPP has it); else, for a PO without material state
      -- (produced before AY; independent review of rev7, F1), zero for a fact created after tp and, for one created by
      -- tp, its value less the revaluations of its movement since tp (the inventory delta of a movement moves opposite
      -- to its value in the HPP); else unknown (null: the pool keeps the constant correction). anc: the revaluations of
      -- its movement after this instant are part of the change.
      select case when gr.batch is not null then 'B:'||gr.batch::text else 'G:'||gr.id::text end pool,gr.po_id=p_po_id own,
        greatest(p_effective_date,least(v_cap,erp._cp3_business_date(mm.physical_at))) d,-mm.qty_signed*mm.unit_cost_snapshot cur,
        gr.id gid,ms.material_value is null and mm.system_created_at>coalesce(mk.ts,mk.tp) fresh,mm.id fid,array[mm.id] mids,
        case when ms.material_value is not null then ms.material_value
             when mk.ts is not null then case when mm.system_created_at>mk.ts then 0 end
             when mm.system_created_at>mk.tp then 0
             when mm.system_created_at<=mk.tp then -mm.qty_signed*mm.unit_cost_snapshot+coalesce((select sum(e.delta_amount)
               from erp.material_cost_revaluation_events e where e.movement_id=mm.id and e.created_at>mk.tp),0) end ov,
        case when ms.material_value is not null then ms.updated_at
             when mm.system_created_at>coalesce(mk.ts,mk.tp) then '-infinity'::timestamptz else mk.tp end anc
      from erp.material_stock_movements mm join grp gr on gr.id=mm.source_id cross join mk
      left join erp.po_hpp_gl_material_state_v1 ms on ms.po_id=p_po_id and ms.source_key='M:'||mm.id::text
      where mm.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN')
      union all
      select 'CONTRACTOR',false,greatest(p_effective_date,least(v_cap,erp._cp3_business_date(coalesce(cv.pa,cm.physical_at)))),
        ci.qty*ci.unit_cost_snapshot,null::uuid,false,ci.id,cv.ids,
        case when ms.material_value is not null then ms.material_value
             when mk.ts is not null then case when cv.ca>mk.ts then 0 end
             when cv.ca>mk.tp then 0
             when cv.ca<=mk.tp then ci.qty*ci.unit_cost_snapshot+coalesce((select sum(e.delta_amount)
               from erp.material_cost_revaluation_events e where e.movement_id=any(cv.ids) and e.created_at>mk.tp),0) end,
        case when ms.material_value is not null then ms.updated_at
             when cv.ca>coalesce(mk.ts,mk.tp) then '-infinity'::timestamptz else mk.tp end
      from erp.contractor_material_issue_items ci join erp.contractor_material_issues cm on cm.id=ci.issue_id
      join erp.materials mt on mt.id=ci.material_id cross join mk
      cross join lateral(select min(cm2.physical_at) pa,min(cm2.system_created_at) ca,array_agg(cm2.id) ids
        from erp.material_stock_movements cm2
        where cm2.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and cm2.source_id=ci.id) cv
      left join erp.po_hpp_gl_material_state_v1 ms on ms.po_id=p_po_id and ms.source_key='C:'||ci.id::text
      where cm.po_id=p_po_id and cm.status='POSTED' and mt.material_type<>'ACCESSORY'
    ), fev as(
      -- The revaluations (erp.material_cost_revaluation_events) of each fact's movement inside its change, each on the
      -- day it moved the value into WIP (AZ: the movement day of an invoice recost, today for any other recost). A
      -- correction then leaves WIP no earlier than it entered it, also for a non-invoice recost still queued when the
      -- invoice is processed (independent review of rev7, residual risk).
      select f.fid,f.pool,f.own,greatest(p_effective_date,least(v_cap,coalesce(e.effective_date,f.d))) d,-e.delta_amount dv
      from fct f join erp.material_cost_revaluation_events e on e.movement_id=any(f.mids) and e.created_at>f.anc
      where f.ov is not null
    ), mat as(
      -- Each fact's change: its revaluations on their own days, the rest (a new fact's value, anything the revaluations
      -- do not explain) on its physical day; cur, gid and fresh only on the fact row.
      select f.pool,f.own,f.d,f.cur,f.gid,f.fresh,
        f.cur-f.ov-coalesce((select sum(v.dv) from fev v where v.fid=f.fid),0) dv
      from fct f
      union all
      select v.pool,v.own,v.d,0,null::uuid,null::boolean,v.dv from fev v
    ), matp as(
      select pool,d,cur,dv from mat union all select 'PO',d,cur,dv from mat where own
    ), pools as(
      -- Each pool: all its facts known (ok), its material correction (dvf) and its material now (mnow).
      select pool,bool_and(dv is not null) ok,coalesce(sum(dv),0) dvf,coalesce(sum(cur),0) mnow from matp group by pool
    ), lot as(
      -- The material pool of each lot as erp.rebuild_po_hpp allocates it (its cutting batch over the batch's effective
      -- pieces, else its lineage group over the group's pieces, else the PO over the PO's production pieces) and qf, the
      -- pieces behind that pool now.
      select l.*,gr.batch,
        case when gr.batch is not null then case when b.eff>0 then 'B:'||gr.batch::text else 'PO' end
             when gr.pcs>0 then 'G:'||gr.id::text else 'PO' end pool,
        case when gr.batch is not null and b.eff>0 then b.eff
             when gr.batch is null and gr.pcs>0 then gr.pcs
             else nullif((select sum(f2.initial_qty_pcs) from erp.fg_lots f2 where f2.po_id=p_po_id and f2.lot_origin='PRODUCTION'),0) end qf
      from lot0 l left join grp gr on gr.id=l.grp left join bt b on b.batch=gr.batch
    ), srcq as(
      select nullif(erp.cp6_po_source_qty_v2620c(p_po_id),0)::numeric q
    ), lotd as(
      select l.id,l.pool,l.qf,l.batch,l.src,l.cst,case when l.lot_origin='VOIDED_PRODUCTION' then 0 else l.dp end dp,case when l.lot_origin='VOIDED_PRODUCTION'
          then coalesce((select avg(l2.h-l2.o) from lot0 l2 where l2.grp=l.grp and l2.lot_origin='PRODUCTION'),
                        coalesce((select p.dvf/l.qf from pools p where p.pool=l.pool and p.ok),0)
                        +coalesce((select p.dvf/(select q from srcq) from pools p where p.pool='CONTRACTOR' and p.ok),0))
          else l.h-l.o end dh
      from lot l
    ), ev as(
      select m.lot_id,greatest(p_effective_date,least(v_cap,erp._cp3_business_date(m.physical_at))) d,
        coalesce(o.movement_type,m.movement_type) k,m.qty_signed::numeric q
      from erp.fg_stock_movements m join lotd l on l.id=m.lot_id
      left join erp.fg_stock_movements o on m.movement_type='REVERSAL' and o.id=m.reversal_of_id
      where coalesce(o.movement_type,m.movement_type) in('QC_GOOD','REWORK_IN','OPENING','SALE','SALE_RETURN',
                                                         'ADJUSTMENT','BS_OUT','REBRAND_OUT','REBRAND_IN')
    ), pk as(
      -- The pocket-fabric allocation of the PO is posted at the end of its period (erp.save_pocket_period_action_v1); a change
      -- of its pocket-fabric part is dated no earlier (the recost journal too, AZ).
      select greatest(p_effective_date,least(v_cap,max(pp.period_end))) d from erp.pocket_period_destinations pd
      join erp.pocket_periods pp on pp.id=pd.pool_id where pd.po_id=p_po_id
    ), dates as(
      select d from ev union select m.d from matp m join pools p on p.pool=m.pool and p.ok
      union select gr.cd from grp gr where gr.batch is not null
      union select pk.d from pk where pk.d is not null and exists(select 1 from lot0 where dp<>0)
    ), daily as(
      select lot_id,d,
        sum(case when k in('QC_GOOD','REWORK_IN','OPENING') then q else 0 end) p,
        sum(case when k in('SALE','SALE_RETURN') then -q else 0 end) sd,
        sum(case when k in('ADJUSTMENT','BS_OUT','REBRAND_OUT','REBRAND_IN') then -q else 0 end) ot
      from ev group by 1,2
    ), cumq as(
      -- Pieces of each lot in FG / sold / out otherwise as of each date: running sums (independent review of rev6, M-4:
      -- no dates x movements join).
      select g.lot_id,g.d,
        sum(coalesce(dy.p,0)) over w p,sum(coalesce(dy.sd,0)) over w sd,sum(coalesce(dy.ot,0)) over w ot
      from (select l.id lot_id,dt.d from lotd l cross join dates dt) g
      left join daily dy on dy.lot_id=g.lot_id and dy.d=g.d
      window w as(partition by g.lot_id order by g.d rows unbounded preceding)
    ), pday as(
      select pool,d,sum(dv) dv from matp group by 1,2
    ), pcum as(
      -- Each pool's material correction as of each date (running sum).
      select p.pool,dt.d,sum(coalesce(pd.dv,0)) over(partition by p.pool order by dt.d rows unbounded preceding) dv
      from pools p cross join dates dt left join pday pd on pd.pool=p.pool and pd.d=dt.d where p.ok
    ), bcum as(
      -- Each batch's pieces cut by each date, scaled to its effective pieces.
      select b.batch,dt.d,
        case when b.spcs>0 then b.eff*sum(coalesce(bd.pcs,0)) over(partition by b.batch order by dt.d rows unbounded preceding)/b.spcs
             else b.eff end pcs
      from bt b cross join dates dt
      left join (select gr.batch,gr.cd,sum(gr.pcs) pcs from grp gr where gr.batch is not null group by 1,2) bd on bd.batch=b.batch and bd.cd=dt.d
    ), newg as(
      -- Groups the HPP posted last did not have (every cutting fact of the group is new).
      select m.gid from mat m where m.gid is not null group by m.gid having bool_and(m.fresh)
    ), bnew as(
      -- Effective pieces of each batch's new groups: cut by each date, and in total.
      select b.batch,dt.d,
        case when b.spcs>0 then b.eff*sum(coalesce(nd.pcs,0)) over(partition by b.batch order by dt.d rows unbounded preceding)/b.spcs else 0 end pcs,
        case when b.spcs>0 then b.eff*coalesce((select sum(g.pcs) from grp g join newg n on n.gid=g.id where g.batch=b.batch),0)/b.spcs else 0 end tot
      from bt b cross join dates dt
      left join (select gr.batch,gr.cd,sum(gr.pcs) pcs from grp gr join newg n on n.gid=gr.id where gr.batch is not null group by 1,2) nd
        on nd.batch=b.batch and nd.cd=dt.d
    ), cl as(
      -- Per-piece correction of each lot as of each date: its correction now, less the part of its pool's (and the PO's
      -- contractor) material correction whose fact is not there yet on that date. A batch divides by the (effective)
      -- pieces of the groups cut by then. A batch that got a new group since the HPP posted last also spreads its old
      -- material over the new pieces; that dilution (old material x (1/pieces by D - 1/pieces now), pieces by D counting the
      -- new groups cut by D) is dated on the new group's cut day (independent review of rev7, F4).
      select c.lot_id,c.d,c.p,c.sd,c.ot,
        l.dh+coalesce(pc.dv/nullif(case when l.pool like 'B:%' then bc.pcs else l.qf end,0),0)-coalesce(pp.dvf/l.qf,0)
          +coalesce(case when l.pool like 'B:%' and bn.tot>0
                         then (pp.mnow-pp.dvf)*(1/nullif(l.qf-bn.tot+bn.pcs,0)-1/l.qf) end,0)
          +coalesce((cc.dv-cp.dvf)/(select q from srcq),0)
          -case when l.dp<>0 and c.d<(select pk.d from pk) then l.dp else 0 end cv
      from cumq c join lotd l on l.id=c.lot_id
      left join pools pp on pp.pool=l.pool and pp.ok
      left join pcum pc on pc.pool=l.pool and pc.d=c.d
      left join bcum bc on bc.batch=l.batch and bc.d=c.d
      left join bnew bn on bn.batch=l.batch and bn.d=c.d
      left join pools cp on cp.pool='CONTRACTOR' and cp.ok
      left join pcum cc on cc.pool='CONTRACTOR' and cc.d=c.d
    ), chain as(
      -- Relabel lineage: every lot of the PO with its root lot (a lot not relabelled from a lot of this PO) and the sum of
      -- the own differences of its posted relabels (a reversed relabel adds none).
      select l.id,l.id root,0::numeric off,0 depth from lotd l where l.src is null or not exists(select 1 from lotd px where px.id=l.src)
      union all
      select l.id,c.root,c.off+case when l.cst='POSTED' then l.dh-px.dh else 0 end,c.depth+1
      from chain c join lotd l on l.src=c.id join lotd px on px.id=c.id where c.depth<100
    ), cl2 as(
      -- A relabelled lot follows its root lot (independent reviews of rev6, F6, and rev7, F3: a relabel, reversed or in a
      -- chain, moves pieces at the same correction, so nothing swings through the other account).
      select c.d,c.p,c.sd,c.ot,coalesce(cr.cv+ch.off,c.cv) cv
      from cl c left join chain ch on ch.id=c.lot_id and ch.root<>c.lot_id
      left join cl cr on cr.lot_id=ch.root and cr.d=c.d
    )
    select d,sum(cv*(p-sd-ot)) f,sum(cv*sd) c,sum(cv*ot) o from cl2 group by d order by d
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
  -- The HPP this sync posted for each lot and the value of each material fact it saw: the bases of the next sync.
  insert into erp.po_hpp_gl_lot_state_v1(lot_id,po_id,hpp_per_pcs,updated_at)
  select fl.id,p_po_id,coalesce((select max(case when coalesce(hv.qty_basis_pcs,0)>0 then hv.total_cost/hv.qty_basis_pcs else 0 end)
    from erp.hpp_versions hv where hv.lot_id=fl.id and hv.is_current),0),statement_timestamp()
  from erp.fg_lots fl where fl.po_id=p_po_id and fl.lot_origin in('PRODUCTION','CONVERSION','VOIDED_PRODUCTION')
  on conflict(lot_id) do update set po_id=excluded.po_id,hpp_per_pcs=excluded.hpp_per_pcs,updated_at=excluded.updated_at;
  -- The material state is the value of each fact inside the HPP just posted, so it is written only when that HPP was
  -- rebuilt in this statement (every erp.rebuild_po_hpp caller syncs right after it; a sync without a rebuild, e.g. FG
  -- adjustment or a sale reversal, posts the HPP of the last rebuild, which the kept state still describes).
  if exists(select 1 from erp.hpp_versions hv join erp.fg_lots fl on fl.id=hv.lot_id
            where fl.po_id=p_po_id and hv.is_current and hv.calculated_at>=statement_timestamp()) then
    insert into erp.po_hpp_gl_material_state_v1(po_id,source_key,material_value,updated_at)
    select p_po_id,'M:'||mm.id::text,-mm.qty_signed*mm.unit_cost_snapshot,statement_timestamp()
    from erp.material_stock_movements mm join erp.cutting_groups g on g.id=mm.source_id
    where mm.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN')
      and (g.po_id=p_po_id or g.cutting_batch_id in(select g0.cutting_batch_id from erp.cutting_groups g0
                                                    where g0.po_id=p_po_id and g0.cutting_batch_id is not null))
    union all
    select p_po_id,'C:'||ci.id::text,ci.qty*ci.unit_cost_snapshot,statement_timestamp()
    from erp.contractor_material_issue_items ci join erp.contractor_material_issues cm on cm.id=ci.issue_id
    where cm.po_id=p_po_id and cm.status='POSTED'
    union all
    select p_po_id,'SYNC',0,statement_timestamp()
    on conflict(po_id,source_key) do update set material_value=excluded.material_value,updated_at=excluded.updated_at;
  end if;

"""

TABLE="""create table erp.po_hpp_gl_lot_state_v1(
  lot_id uuid primary key,
  po_id uuid not null,
  hpp_per_pcs numeric not null,
  updated_at timestamptz not null default statement_timestamp());
comment on table erp.po_hpp_gl_lot_state_v1 is 'AY: HPP per piece of each lot as erp.sync_po_hpp_to_gl last posted it (base of the per-lot correction of the next sync).';
alter table erp.po_hpp_gl_lot_state_v1 enable row level security;
revoke all on erp.po_hpp_gl_lot_state_v1 from public,anon,authenticated,service_role;
create table erp.po_hpp_gl_material_state_v1(
  po_id uuid not null,
  source_key text not null,
  material_value numeric not null,
  updated_at timestamptz not null default statement_timestamp(),
  primary key(po_id,source_key));
comment on table erp.po_hpp_gl_material_state_v1 is 'AY rev7: value of each material fact behind a PO HPP (cutting issue/return M:<movement>, also of other POs'' groups in the same cutting batch; contractor issue C:<item>) as that PO''s last erp.sync_po_hpp_to_gl saw it; base of the per-fact correction dated on its own day.';
alter table erp.po_hpp_gl_material_state_v1 enable row level security;
revoke all on erp.po_hpp_gl_material_state_v1 from public,anon,authenticated,service_role;"""

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
    # Independent review of rev7 (F2): the planner estimates the daily-balance query far too high and JIT-compiles it (about
    # 4 s at 300 lots under the global FG_HPP_SALES_V2620C lock); the function runs with jit off.
    assert body.count(JIT_OLD)==1
    return body[:a].replace(DECLARE_OLD,DECLARE_NEW).replace(JIT_OLD,JIT_NEW)+POST_NEW_HEAD+body[a:b]+POST_NEW_TAIL+body[b:]


def alias_collisions(fn):
    """Table aliases of the invoice-path query that shadow a plpgsql variable of the function (rev6 CI error: alias t
    against record t; rev7.1 harness: alias s against record s). Such a name resolves to the variable at run time."""
    import re
    decl=fn[fn.index('declare'):fn.index('\nbegin')]
    names=set(re.findall(r'^\s*([a-z_][a-z0-9_]*)\s',decl,re.M))|set(re.findall(r';\s*([a-z_][a-z0-9_]*)\s',decl))
    q=POST_NEW_TAIL[POST_NEW_TAIL.index('with recursive'):POST_NEW_TAIL.index('select d,sum(cv*(p-sd-ot))')]
    aliases=set(re.findall(r'\b(?:from|join)\s+(?:erp\.)?[a-z_0-9]+\s+([a-z][a-z0-9_]*)\b',q))
    aliases|=set(re.findall(r'\)\s+([a-z][a-z0-9_]*)\s+(?:on|where|left|join|cross|window)',q))
    return sorted((aliases-{'on','where','left','join','cross','window','union','group','lateral'})&(names-{'declare'}))


def assert_no_alias_collision(fn):
    bad=alias_collisions(fn)
    assert not bad,('AY_BUILD_ALIAS_SHADOWS_PLPGSQL_VARIABLE',bad)


def build():
    parts=['-- CP6 AY PO HPP corrections dated from the goods: T1_FAMILY development install (NOT a release package).',
           '-- Generated by scripts/cp6_ay_build.py from the AS definition of erp.sync_po_hpp_to_gl; do not edit by hand.',
           'begin;',"set local lock_timeout='10s';set local statement_timeout='240s';set local search_path='';",
           'do $t1_guard$','begin',
           " if (select count(*) from erp.schema_migrations where version in('v2.6.20av','v2.6.20aw','v2.6.20ax'))<>3 then raise exception 'AY_T1_REQUIRES_AV_AW_AX'; end if;",
           f" if exists(select 1 from erp.schema_migrations where version='{VERSION}') or to_regprocedure('erp.po_hpp_gl_leg_add_v1(jsonb,date,numeric,numeric,numeric)') is not null or to_regclass('erp.po_hpp_gl_lot_state_v1') is not null or to_regclass('erp.po_hpp_gl_material_state_v1') is not null then raise exception 'AY_T1_ALREADY_INSTALLED'; end if;",
           'end $t1_guard$;',TABLE,HELPER,
           'revoke all on function erp.po_hpp_gl_leg_add_v1(jsonb,date,numeric,numeric,numeric) from public,anon,authenticated,service_role;',
           (lambda fn:(fn,assert_no_alias_collision(fn))[0])(sync_function()),
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
