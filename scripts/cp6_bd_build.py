#!/usr/bin/env python3
"""Build the BD T1 family install: priced laundry deliveries (LAU-05b: package, components with partial coverage, lump sum per
batch, minimum charge, scoped rates per model/size/colour) and the laundry policy settings LAU-DEC01..06 (owner decision
25 Sep 2026: every CR and every ALL state built and tested in CP6; policy rows are application settings with a fail-closed
default).

New objects come from scripts/cp6_bd_objects_{policy,master,pricing,router}.sql; every existing function is taken from the
definition the chain currently runs (AC/20 migrations, the AW, AY and BA T1 files) with checked substitutions only:
  L1 erp.save_laundry_qc_action_v1 (BA):
     POST_DELIVERY  inside the BD facade (context POST_PRICED_DELIVERY) the line takes the priced average rate (NULL while a
                    component price is unknown, status PENDING) and the priced charge lines are attached after the size lines;
                    outside it, a vendor/process that needs BD pricing is refused (BD_PRICING_REQUIRED) instead of being
                    priced at the base rate.
     POST_RECEIPT   a BD-priced delivery is received with the process it was priced for (BD_PROCESS_CHANGED otherwise) and
                    each size takes its exact share of the estimate (erp.bd_allocate_receipt_v1; the last return of a size
                    takes the residual).
  L2 erp.post_laundry_delivery (AC): a BD line with an unknown price keeps its NULL rate (no base-rate fill).
  L3 erp.desired_laundry_accrual (20) and erp.rebuild_po_hpp (AY): the uncosted part of a BD line is its estimate less the
     shares already taken by posted receipts (erp.bd_uncosted_estimate_v1; exactly the old formula for any other line); a BD
     line with an unknown price keeps the PO's HPP pending; a lot sourced from a BD receipt size takes that size's own amount.
  L4 erp.period_blockers_v1 (AW): BD_LAUNDRY_COMPONENT_PRICE_UNKNOWN blocks close while a BD component price is unknown and
     the old LAUNDRY_PRICE_UNKNOWN does not already report the line.
  L5 erp.set_laundry_rate_owner_estimate_v1 (AW): refused for a BD line (its price is set per charge, SET_CHARGE_PRICE).
  L6 erp.validate_laundry_receipt_line (20): a receipt line of a priced delivery costs the sum of its exact size shares
     (ESTIMATED, the known part while a component price is unknown); the old qty x rate rule stays for every other line.
Label T1_FAMILY: development install on the disposable chain AN -> AU -> AV -> AW..BA -> BB -> BC, not a release package.

Usage: python3 scripts/cp6_bd_build.py            # writes supabase/dev/cp6_bd_t1_family.sql
       python3 scripts/cp6_bd_build.py --check
"""
from pathlib import Path
import hashlib,re,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from cp6_bc_build import last_definition,substitute

M20=ROOT/'supabase/migrations/20260904111157_erp_v2_6_20_cp6_laundry_qc_fg_authoritative.sql'
AC=ROOT/'supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql'
AW=ROOT/'supabase/dev/cp6_aw_t1_family.sql'
AY=ROOT/'supabase/dev/cp6_ay_t1_family.sql'
BA=ROOT/'supabase/dev/cp6_ba_t1_family.sql'
OBJECTS=[ROOT/f'scripts/cp6_bd_objects_{p}.sql' for p in ('policy','master','pricing','router')]
OUT=ROOT/'supabase/dev/cp6_bd_t1_family.sql'
VERSION='v2.6.20bd'

# ---------------------------------------------------------------- L1 laundry facade (BA)
DELIVERY_RATE_OLD='''    select count(*)::integer,min(r.rate_per_pcs) into v_rate_count,v_rate
    from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at);
    if v_rate_count<>1 then
      raise exception 'Exactly one authoritative Laundry rate must be effective for this vendor/process/time; found %',v_rate_count;
    end if;
'''
DELIVERY_RATE_NEW='''    if coalesce((erp.bd_context_v1()).action,'')='POST_PRICED_DELIVERY' then
      -- BD (LAU-05b): the BD facade priced this delivery; the line keeps the exact average rate when every price is known and
      -- NULL while a component price is unknown (the charge lines are attached below).
      v_rate:=((erp.bd_context_v1()).pricing->>'avg_rate')::numeric;v_rate_count:=1;
    elsif erp.bd_vendor_needs_pricing_v1(v_vendor_id,v_process_id) then
      raise exception 'BD_PRICING_REQUIRED: vendor ini memakai harga paket/komponen/borongan/minimum/tarif khusus; kirim lewat halaman harga laundry (POST_PRICED_DELIVERY)';
    else
'''+'\n'.join('  '+l if l else l for l in DELIVERY_RATE_OLD.rstrip('\n').split('\n'))+'''
    end if;
'''
DELIVERY_STATUS_OLD="      v_delivery_line_id,v_delivery_id,v_group.id,v_total,v_rate,'ESTIMATED',\n"
DELIVERY_STATUS_NEW="      v_delivery_line_id,v_delivery_id,v_group.id,v_total,v_rate,case when v_rate is null then 'PENDING' else 'ESTIMATED' end,\n"
DELIVERY_ATTACH_OLD='''    ) select v_delivery_line_id,v_batch_id,x.size_id,x.qty_sent_pcs,v_actor
      from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer);
'''
DELIVERY_ATTACH_NEW=DELIVERY_ATTACH_OLD+'''    -- BD: the priced charge lines and per-size estimates of this delivery (only inside the BD facade's context).
    perform erp.bd_attach_delivery_pricing_v1(v_delivery_line_id);
'''
RECEIPT_RATE_OLD='''    select count(*)::integer,min(r.rate_per_pcs) into v_rate_count,v_rate
    from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_delivery.physical_at
      and(r.effective_to is null or r.effective_to>v_delivery.physical_at);
    if v_rate_count<>1 then
      raise exception 'Exactly one authoritative actual Laundry rate must be effective for this vendor/process/time; found % (rate of the send time)',v_rate_count;
    end if;
'''
RECEIPT_RATE_NEW='''    if exists(select 1 from erp.bd_laundry_priced_lines_v1 bp where bp.delivery_id=v_delivery.id) then
      -- BD (LAU-05b): a priced delivery is received at its own exact estimate (erp.bd_allocate_receipt_v1 below), with the
      -- process it was priced for; its rate snapshot is the priced average (NULL while a component price is unknown).
      if v_process_id is distinct from v_delivery.target_wash_process_id then
        raise exception 'BD_PROCESS_CHANGED: kiriman dengan harga paket/komponen/borongan hanya diterima dengan proses yang dihargai saat kirim';
      end if;
      select dl.estimated_rate_snapshot into v_rate from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery.id;
      v_rate_count:=1;
    else
'''+'\n'.join('  '+l if l else l for l in RECEIPT_RATE_OLD.rstrip('\n').split('\n'))+'''
    end if;
'''
RECEIPT_ALLOC_OLD='''    insert into erp.laundry_receipt_bs_product_allocations(
      receipt_line_id,product_id,qty_bs,notes,created_by
    ) select v_receipt_line_id,x.bs_product_id,sum(x.qty_bs_laundry)::integer,
        'CP6 immutable Laundry-BS product/size declaration',v_actor
'''
RECEIPT_ALLOC_NEW='''    -- BD: each size of a priced delivery takes its exact share of the estimate; the receipt line's cost is their sum.
    perform erp.bd_allocate_receipt_v1(v_receipt_line_id);
'''+RECEIPT_ALLOC_OLD
RECEIPT_RESPONSE_OLD="      'rate_per_pcs',v_rate,'actual_cost',round(v_total*v_rate,2),\n      'cost_status','ESTIMATED_UNBILLED','accrual_effect'"
RECEIPT_RESPONSE_NEW=("      'rate_per_pcs',v_rate,'actual_cost',coalesce((select sum(ba.amount) from erp.bd_laundry_receipt_allocations_v1 ba\n"
                      "        where ba.receipt_line_id=v_receipt_line_id),round(v_total*v_rate,2)),\n      'cost_status','ESTIMATED_UNBILLED','accrual_effect'")
FACADE_SUBS=[(DELIVERY_RATE_OLD,DELIVERY_RATE_NEW),(DELIVERY_STATUS_OLD,DELIVERY_STATUS_NEW),(DELIVERY_ATTACH_OLD,DELIVERY_ATTACH_NEW),
             (RECEIPT_RATE_OLD,RECEIPT_RATE_NEW),(RECEIPT_ALLOC_OLD,RECEIPT_ALLOC_NEW),(RECEIPT_RESPONSE_OLD,RECEIPT_RESPONSE_NEW)]

# ---------------------------------------------------------------- L2 delivery posting (AC)
POST_DELIVERY_SUBS=[("    if v_rate is null and h.target_wash_process_id is not null then\n",
                     "    -- BD: a priced line with an unknown component price keeps its NULL rate (never the base rate).\n"
                     "    if v_rate is null and h.target_wash_process_id is not null\n"
                     "       and not exists(select 1 from erp.bd_laundry_priced_lines_v1 bp where bp.delivery_line_id=r.id) then\n")]

# ---------------------------------------------------------------- L3 accrual and HPP
ACCRUAL_SUBS=[("    select\n      ldl.qty_sent_pcs,\n      ldl.estimated_rate_snapshot,","    select\n      ldl.id,\n      ldl.qty_sent_pcs,\n      ldl.estimated_rate_snapshot,"),
              ("      +greatest(qty_sent_pcs-costed_qty,0)*coalesce(estimated_rate_snapshot,0)\n",
               "      -- BD: a priced line's estimate less the shares taken by posted receipts; the old formula for any other line.\n"
               "      +erp.bd_uncosted_estimate_v1(id,qty_sent_pcs,costed_qty,estimated_rate_snapshot)\n")]
REBUILD_SUBS=[
    ("  select coalesce(sum(actual_cost+greatest(qty_sent_pcs-qty_costed_actual,0)*coalesce(estimated_rate_snapshot,0)),0),\n"
     "         coalesce(bool_or(has_pending_receipt or qty_sent_pcs>qty_costed_actual),false)\n",
     "  -- BD: uncosted part of a priced line by its exact shares; an unknown component price keeps the HPP pending.\n"
     "  select coalesce(sum(actual_cost+erp.bd_uncosted_estimate_v1(id,qty_sent_pcs,qty_costed_actual,estimated_rate_snapshot)),0),\n"
     "         coalesce(bool_or(has_pending_receipt or qty_sent_pcs>qty_costed_actual or not erp.bd_line_complete_v1(id)),false)\n"),
    ("      select coalesce(sum(actual_cost+greatest(qty_sent_pcs-qty_costed_actual,0)*coalesce(estimated_rate_snapshot,0)),0)\n"
     "      into v_group_laundry from dl;\n",
     "      select coalesce(sum(actual_cost+erp.bd_uncosted_estimate_v1(id,qty_sent_pcs,qty_costed_actual,estimated_rate_snapshot)),0)\n"
     "      into v_group_laundry from dl;\n"),
    ("            then rl.actual_cost/nullif(rl.qty_good_received+rl.qty_bs_laundry,0)\n",
     "            -- BD: a lot from a priced receipt size takes that size's own amount (sizes may be priced differently).\n"
     "            then coalesce((select ba.amount/nullif(ba.qty,0) from erp.bd_laundry_receipt_allocations_v1 ba where ba.receipt_batch_size_line_id=rx.id),\n"
     "              rl.actual_cost/nullif(rl.qty_good_received+rl.qty_bs_laundry,0))\n")]

# ---------------------------------------------------------------- L4 close blocker
BLOCKER_ANCHOR="  -- LAUNDRY: a delivery rate that is not a finite non-negative number is not a known price (P-02).\n"
BLOCKER_NEW='''  -- BD (LAU-05b, LAU-T12): a component price of a priced delivery still unknown on or before the date, reported here when
  -- LAUNDRY_PRICE_UNKNOWN does not (every piece already returned and costed at the known part only).
  return query
  select 'LAUNDRY'::text,'BD_LAUNDRY_COMPONENT_PRICE_UNKNOWN'::text,'POLICY'::text,'AS_OF'::text,
    erp._cp3_business_date(ld.physical_at),
    jsonb_build_object('delivery_id',ld.id,'delivery_number',ld.delivery_number,'delivery_line_id',bp.delivery_line_id,'po_id',ld.po_id,
      'unknown_charges',(select count(*) from erp.bd_laundry_charge_lines_v1 c where c.delivery_line_id=bp.delivery_line_id and c.rate_status='UNKNOWN')),
    format('Harga komponen laundry kiriman %s belum diketahui; isi harga komponen di halaman harga laundry.',ld.delivery_number)
  from erp.bd_laundry_priced_lines_v1 bp
  join erp.laundry_delivery_lines ldl on ldl.id=bp.delivery_line_id
  join erp.laundry_deliveries ld on ld.id=bp.delivery_id
  left join lateral (select sum(lrl.qty_good_received+lrl.qty_bs_laundry) costed_qty
    from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where lrl.delivery_line_id=ldl.id and lr.status='POSTED' and lrl.actual_cost_status in('ESTIMATED','FINAL')) rc on true
  where not bp.total_complete and ld.status not in('DRAFT','REVERSED') and ld.physical_at<v_end
    and not(ldl.estimated_rate_snapshot is null and ldl.qty_sent_pcs-coalesce(rc.costed_qty,0)>0);

'''+BLOCKER_ANCHOR
BLOCKER_SUBS=[(BLOCKER_ANCHOR,BLOCKER_NEW)]

# ---------------------------------------------------------------- L5 owner estimate
ESTIMATE_SUBS=[("  if v_line.estimated_rate_snapshot is not null then raise exception 'LAUNDRY_ESTIMATE_RATE_ALREADY_KNOWN'; end if;\n",
                "  if v_line.estimated_rate_snapshot is not null then raise exception 'LAUNDRY_ESTIMATE_RATE_ALREADY_KNOWN'; end if;\n"
                "  -- BD: a priced delivery's unknown price is set per charge line (SET_CHARGE_PRICE), never as one flat rate.\n"
                "  if exists(select 1 from erp.bd_laundry_priced_lines_v1 bp where bp.delivery_line_id=v_line.id) then\n"
                "    raise exception 'BD_USE_CHARGE_PRICE: kiriman ini dihargai per komponen; isi harga komponen yang belum diketahui di halaman harga laundry';\n"
                "  end if;\n")]

# ---------------------------------------------------------------- L6 receipt line cost
RECEIPT_LINE_OLD='''  if new.actual_cost_status='FINAL' and new.actual_cost is not null then
    return new;
  end if;
'''
RECEIPT_LINE_NEW=RECEIPT_LINE_OLD+'''  -- BD: a receipt line of a priced delivery costs the exact shares of its sizes (erp.bd_allocate_receipt_v1), not qty x rate.
  if exists(select 1 from erp.bd_laundry_receipt_allocations_v1 a where a.receipt_line_id=new.id) then
    new.actual_cost:=(select sum(a.amount) from erp.bd_laundry_receipt_allocations_v1 a where a.receipt_line_id=new.id);
    new.actual_cost_status:='ESTIMATED';
    return new;
  end if;
'''
RECEIPT_LINE_SUBS=[(RECEIPT_LINE_OLD,RECEIPT_LINE_NEW)]

REPLACED=['erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)','erp.post_laundry_delivery(uuid)','erp.desired_laundry_accrual(uuid)',
          'erp.rebuild_po_hpp(uuid,text)','erp.period_blockers_v1(date,date)','erp.set_laundry_rate_owner_estimate_v1(uuid,numeric,text)',
          'erp.validate_laundry_receipt_line()']
NEW_TABLES=['bd_policy_settings_v1','bd_policy_setting_events_v1','bd_execution_context_v1','bd_laundry_vendor_terms_v1','bd_laundry_components_v1',
            'bd_laundry_component_rates_v1','bd_laundry_packages_v1','bd_laundry_package_components_v1','bd_laundry_package_rates_v1',
            'bd_laundry_scoped_rates_v1','bd_requests_v1','bd_laundry_priced_lines_v1','bd_laundry_charge_lines_v1','bd_laundry_charge_shares_v1',
            'bd_laundry_size_estimates_v1','bd_laundry_receipt_allocations_v1']


def objects():
    return '\n'.join(p.read_text().rstrip('\n') for p in OBJECTS)


def new_functions():
    return [m.group(1) for m in re.finditer(r'(?i)create or replace function ((?:erp|public)\.[a-z0-9_]+)\(',objects())]


def build():
    facade=substitute(last_definition(BA,'save_laundry_qc_action_v1'),FACADE_SUBS,'laundry facade')
    post_delivery=substitute(last_definition(AC,'post_laundry_delivery'),POST_DELIVERY_SUBS,'post delivery')
    accrual=substitute(last_definition(M20,'desired_laundry_accrual'),ACCRUAL_SUBS,'accrual')
    rebuild=substitute(last_definition(AY,'rebuild_po_hpp'),REBUILD_SUBS,'rebuild')
    blockers=substitute(last_definition(AW,'period_blockers_v1'),BLOCKER_SUBS,'blockers')
    estimate=substitute(last_definition(AW,'set_laundry_rate_owner_estimate_v1'),ESTIMATE_SUBS,'owner estimate')
    receipt_line=substitute(last_definition(M20,'validate_laundry_receipt_line'),RECEIPT_LINE_SUBS,'receipt line')
    parts=['-- CP6 BD priced laundry deliveries (LAU-05b) and laundry policy settings LAU-DEC01..06 (owner decision 25 Sep 2026): T1_FAMILY development install (NOT a release package).',
           '-- Generated by scripts/cp6_bd_build.py from scripts/cp6_bd_objects_*.sql, the 20/AC migrations and the AW/AY/BA T1 files; do not edit by hand.',
           'begin;',"set local lock_timeout='10s';set local statement_timeout='240s';set local search_path='';",
           'do $t1_guard$','begin',
           " if not exists(select 1 from erp.schema_migrations where version='v2.6.20bc') then raise exception 'BD_T1_REQUIRES_BC'; end if;",
           f" if exists(select 1 from erp.schema_migrations where version='{VERSION}') or to_regclass('erp.bd_laundry_priced_lines_v1') is not null then raise exception 'BD_T1_ALREADY_INSTALLED'; end if;",
           'end $t1_guard$;',objects(),facade,post_delivery,accrual,rebuild,blockers,estimate,receipt_line,
           f"insert into erp.schema_migrations(version,description) values('{VERSION}',"
           "'T1_FAMILY development install of BD (priced laundry deliveries: package, components with partial coverage, lump sum per batch, minimum charge, scoped rates; exact per-size receipt shares; policy settings LAU-DEC01..06); not a release package');",
           'commit;','']
    return '\n'.join(parts)


if __name__=='__main__':
    text=build()
    if '--check' in sys.argv:
        assert OUT.read_text()==text,'supabase/dev/cp6_bd_t1_family.sql is stale; rerun scripts/cp6_bd_build.py'
        print('fresh',hashlib.sha256(text.encode()).hexdigest())
    else:
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(text)
        print(OUT.relative_to(ROOT),len(text),hashlib.sha256(text.encode()).hexdigest())
