import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { functionBlocks } from './schedule-scenario-fixture.mjs'
// PL-8 part 2: the global supply source before (git, renamed *_0) and after
// (working tree) on the real CP7 capture readers (wip/source.sql,
// wip/other-source.sql) and WIP kernel, over SYNTHETIC erp stand-ins that hold
// exactly the columns those readers select (plus FK-style indexes). Rows come
// from the f04 lifecycle generator (loaded column by column) or from labelled
// administrative clones of spent groups. Only the baseline source/build and the
// schedule selection are stubs; supply, schedule-scenario and netting are real.
export const supplyBase = '2c746deaa005313756b451947bb941cc5eed5c6f'
const git = path => execFileSync('git', ['show', `${supplyBase}:${path}`], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 })
const now = path => readFileSync(path, 'utf8')
const pick = (text, ...names) => { const all = functionBlocks(text); return names.map(n => { if (!all.has(n)) throw new Error(n); return all.get(n) }).join('\n') }
export const AT = '2026-10-07T03:00:00+00:00'
export const MODEL = '6d0e1c1e-0000-4000-8000-0000000000a1'
export const SIZES = Array.from({ length: 5 }, (_, i) => `00000000-0000-4000-8000-00000000000${i + 1}`)

const STUBS = `
create schema erp;
create table erp.production_orders(id uuid primary key,model_id uuid);
create table erp.products(id uuid primary key,size_id uuid,identity_root_id uuid,model_id uuid,brand_id uuid,color_name text,
 effective_from timestamptz default '2026-01-01T00:00:00Z',effective_to timestamptz,created_at timestamptz default '2026-01-01T00:00:00Z');
create table erp.cutting_groups(id uuid primary key,po_id uuid,row_version bigint,status text,pattern_id uuid,pattern_revision_snapshot int,
 cut_at timestamptz,picked_up_at timestamptz,material_issue_posted boolean);
create table erp.cutting_group_rolls(id uuid primary key,cutting_group_id uuid);
create table erp.cutting_group_size_slots(id uuid primary key,size_id uuid);
create table erp.cutting_roll_yields(id uuid primary key,cutting_group_roll_id uuid,size_slot_id uuid,qty_pcs numeric);
create table erp.cutting_pickups(id uuid primary key,cutting_group_id uuid,status text,picked_up_at timestamptz,row_version bigint);
create table erp.cutting_distribution_batches(id uuid primary key,pickup_id uuid);
create table erp.cutting_distribution_allocations(id uuid primary key,batch_id uuid,cutting_roll_yield_id uuid,qty_pcs numeric);
create table erp.laundry_deliveries(id uuid primary key,status text,physical_at timestamptz,row_version bigint,target_wash_process_id uuid,target_dyeing_color text);
create table erp.laundry_delivery_lines(id uuid primary key,cutting_group_id uuid,delivery_id uuid,qty_sent_pcs numeric);
create table erp.laundry_delivery_batch_size_lines(id uuid primary key,delivery_line_id uuid,distribution_batch_id uuid,size_id uuid,qty_sent_pcs numeric);
create table erp.laundry_receipts(id uuid primary key,status text,physical_at timestamptz,row_version bigint);
create table erp.laundry_receipt_lines(id uuid primary key,delivery_line_id uuid,receipt_id uuid,qty_good_received numeric,qty_bs_laundry numeric,qty_missing numeric,qty_stuck numeric);
create table erp.laundry_receipt_batch_size_lines(id uuid primary key,receipt_line_id uuid,delivery_batch_size_line_id uuid,size_id uuid,qty_good_received numeric,qty_bs_laundry numeric);
create table erp.qc_inspections(id uuid primary key,status text,physical_at timestamptz,row_version bigint);
create table erp.qc_inspection_items(id uuid primary key,cutting_group_id uuid,inspection_id uuid,source_laundry_receipt_line_id uuid,
 source_laundry_receipt_batch_size_line_id uuid,final_product_id uuid,qty_good_pcs numeric,qty_bs_pcs numeric);
create table erp.bs_cases(id uuid primary key,cutting_group_id uuid,qc_item_id uuid,product_id uuid,source_laundry_receipt_line_id uuid,source_laundry_bs_allocation_id uuid,
 qty_pcs numeric,status text,detected_at_stage text,physical_at timestamptz,row_version bigint,po_id uuid,untracked_type text);
create table erp.rework_orders(id uuid primary key,bs_case_id uuid,qty_sent numeric,qty_good_returned numeric,qty_bs_returned numeric,physical_sent_at timestamptz,
 completed_at timestamptz,status text,row_version bigint,good_fg_lot_id uuid,cost_posted boolean);
create table erp.bs_resolutions(id uuid primary key,bs_case_id uuid,resolution_type text,qty_pcs numeric,source_rework_order_id uuid,physical_at timestamptz);
create table erp.bs_case_hold_events(id uuid primary key,bs_case_id uuid,action text,resulting_status text,physical_at timestamptz,created_at timestamptz);
create table erp.fg_unsourced_receipts_v1(id uuid primary key,bs_case_id uuid,bs_resolution_id uuid,qty_pcs numeric,status text,lot_id uuid,quality_grade text,physical_at timestamptz);
create table erp.laundry_failed_wash_attempts(id uuid primary key,receipt_line_id uuid,delivery_id uuid,custody_outcome text,qty_attempted_pcs numeric);
create table erp.laundry_failed_wash_batch_size_lines(id uuid primary key,attempt_id uuid,delivery_batch_size_line_id uuid,size_id uuid,qty_attempted_pcs numeric);
create table erp.laundry_redispatch_participant_events(id uuid primary key,event_type text,source_delivery_batch_size_line_id uuid,successor_delivery_batch_size_line_id uuid,
 qty_pcs numeric,source_offset_pcs bigint,successor_offset_pcs bigint,releases_allocation_event_id uuid,released_delivery_id uuid,created_at timestamptz);
create table erp.laundry_claims(id uuid primary key,delivery_id uuid,receipt_line_id uuid,claim_type text,qty_claimed numeric,status text,opened_at timestamptz,resolved_at timestamptz,row_version bigint);
create table erp.sewing_terminal_events(id uuid primary key,cutting_group_id uuid,qty_signed numeric,event_kind text,reversal_of_id uuid,physical_at timestamptz,row_version bigint);
create table erp.wip_control_flags(id uuid primary key,cutting_group_id uuid,flag_type text,status text,row_version bigint,created_at timestamptz,resolved_at timestamptz);
create table erp.migration_batches(id uuid primary key,status text);
create table erp.opening_balance_headers(id uuid primary key,status text,opening_date date);
create table erp.opening_balance_items(id uuid primary key,opening_id uuid,balance_type text,qty numeric,product_id uuid,model_id uuid,customer_id uuid,vendor_id uuid,contractor_id uuid);
create table erp.initial_import_production_sources(opening_item_id uuid,source_row_id uuid,batch_id uuid,po_id uuid,size_id uuid,stage text,qty_pcs numeric,bs_case_id uuid);
create table erp.bb_wip_pickups_v1(id uuid primary key,opening_item_id uuid,physical_at timestamptz,reversed_at timestamptz);
create table erp.fg_lots(id uuid primary key,product_id uuid);
create table erp.initial_import_wip_outputs(id uuid primary key,opening_item_id uuid,lot_id uuid,qty_pcs numeric,physical_at timestamptz);
create table erp.initial_import_wip_output_reversals(output_id uuid,physical_at timestamptz);
create table erp.bb_wip_bs_splits_v1(id uuid primary key,opening_item_id uuid,bs_case_id uuid,product_id uuid,qty_pcs numeric,physical_at timestamptz,reversed_at timestamptz);
create table erp.bd_opening_laundry_claims_v1(id uuid primary key,opening_item_id uuid,claim_type text,qty_claimed numeric,claim_date date,cancelled_at timestamptz,row_version bigint);
create table erp.bd_opening_laundry_claim_events_v1(id uuid primary key,claim_id uuid,event_kind text,qty numeric,resolution text,event_date date,reversed_at timestamptz);
create index on erp.cutting_groups(material_issue_posted,cut_at,id);
create index on erp.cutting_group_rolls(cutting_group_id);create index on erp.cutting_roll_yields(cutting_group_roll_id);
create index on erp.cutting_pickups(cutting_group_id);create index on erp.cutting_distribution_batches(pickup_id);
create index on erp.cutting_distribution_allocations(batch_id);create index on erp.laundry_delivery_lines(cutting_group_id);
create index on erp.laundry_delivery_lines(delivery_id);create index on erp.laundry_delivery_batch_size_lines(delivery_line_id);
create index on erp.laundry_receipt_lines(delivery_line_id);create index on erp.laundry_receipt_batch_size_lines(receipt_line_id);
create index on erp.qc_inspection_items(cutting_group_id);create index on erp.bs_cases(cutting_group_id);create index on erp.rework_orders(bs_case_id);
create index on erp.bs_resolutions(bs_case_id);create index on erp.bs_case_hold_events(bs_case_id);create index on erp.fg_unsourced_receipts_v1(bs_case_id);
create index on erp.laundry_failed_wash_attempts(receipt_line_id);create index on erp.laundry_failed_wash_batch_size_lines(attempt_id);
create index on erp.laundry_redispatch_participant_events(source_delivery_batch_size_line_id);
create index on erp.laundry_redispatch_participant_events(successor_delivery_batch_size_line_id);
create index on erp.laundry_claims(delivery_id);create index on erp.sewing_terminal_events(cutting_group_id);
create index on erp.wip_control_flags(cutting_group_id,status);`

// One generated cutting capture (f04 lifecycle generator) written column by
// column into the stand-ins the capture readers select from. Each QC/BS row
// gets its own product of its exact size (the generator shares one product
// id across sizes; a Native product has one size).
const LOADER = `
create function public.sx_load(f jsonb)returns void language plpgsql as $$
begin
 insert into erp.production_orders(id,model_id)select distinct on(x.po_id)x.po_id,x.model_id from jsonb_to_recordset(f->'groups')x(po_id uuid,model_id uuid)
  where x.po_id is not null on conflict do nothing;
 insert into erp.cutting_groups(id,po_id,row_version,status,pattern_id,pattern_revision_snapshot,cut_at,picked_up_at,material_issue_posted)
  select id,po_id,revision::bigint,status,pattern_id,pattern_revision_snapshot,cut_at,picked_up_at,material_issue_posted
  from jsonb_to_recordset(f->'groups')x(id uuid,po_id uuid,revision text,status text,pattern_id uuid,pattern_revision_snapshot int,cut_at timestamptz,picked_up_at timestamptz,material_issue_posted boolean);
 insert into erp.cutting_group_rolls select md5('roll'||id)::uuid,group_id from jsonb_to_recordset(f->'yields')x(id uuid,group_id uuid);
 insert into erp.cutting_group_size_slots select md5('slot'||id)::uuid,size_id from jsonb_to_recordset(f->'yields')x(id uuid,size_id uuid);
 insert into erp.cutting_roll_yields select id,md5('roll'||id)::uuid,md5('slot'||id)::uuid,qty_pcs::numeric from jsonb_to_recordset(f->'yields')x(id uuid,qty_pcs text);
 insert into erp.cutting_pickups select distinct on(pickup_id)pickup_id,group_id,status,picked_up_at,revision::bigint
  from jsonb_to_recordset(f->'batches')x(pickup_id uuid,group_id uuid,status text,picked_up_at timestamptz,revision text)on conflict do nothing;
 insert into erp.cutting_distribution_batches select distinct on(batch_id)batch_id,pickup_id from jsonb_to_recordset(f->'batches')x(batch_id uuid,pickup_id uuid)on conflict do nothing;
 insert into erp.cutting_distribution_allocations select id,batch_id,yield_id,qty_pcs::numeric from jsonb_to_recordset(f->'batches')x(id uuid,batch_id uuid,yield_id uuid,qty_pcs text);
 insert into erp.laundry_deliveries select distinct on(delivery_id)delivery_id,status,physical_at,revision::bigint,target_wash_process_id,target_dyeing_color
  from jsonb_to_recordset(f->'deliveries')x(delivery_id uuid,status text,physical_at timestamptz,revision text,target_wash_process_id uuid,target_dyeing_color text)on conflict do nothing;
 insert into erp.laundry_delivery_lines select id,group_id,delivery_id,qty_pcs::numeric from jsonb_to_recordset(f->'deliveries')x(id uuid,group_id uuid,delivery_id uuid,qty_pcs text);
 insert into erp.laundry_delivery_batch_size_lines select id,delivery_line_id,batch_id,size_id,qty_pcs::numeric
  from jsonb_to_recordset(f->'delivery_sizes')x(id uuid,delivery_line_id uuid,batch_id uuid,size_id uuid,qty_pcs text);
 insert into erp.laundry_receipts select distinct on(receipt_id)receipt_id,status,physical_at,revision::bigint
  from jsonb_to_recordset(f->'receipts')x(receipt_id uuid,status text,physical_at timestamptz,revision text)on conflict do nothing;
 insert into erp.laundry_receipt_lines select id,delivery_line_id,receipt_id,good_pcs::numeric,bs_pcs::numeric,missing_pcs::numeric,stuck_pcs::numeric
  from jsonb_to_recordset(f->'receipts')x(id uuid,delivery_line_id uuid,receipt_id uuid,good_pcs text,bs_pcs text,missing_pcs text,stuck_pcs text);
 insert into erp.laundry_receipt_batch_size_lines select id,receipt_line_id,delivery_size_id,size_id,good_pcs::numeric,bs_pcs::numeric
  from jsonb_to_recordset(f->'receipt_sizes')x(id uuid,receipt_line_id uuid,delivery_size_id uuid,size_id uuid,good_pcs text,bs_pcs text);
 insert into erp.products(id,size_id,identity_root_id,model_id)select distinct md5('q'||final_product_id||size_id)::uuid,size_id,product_root,null::uuid
  from jsonb_to_recordset(f->'qc')x(final_product_id uuid,size_id uuid,product_root uuid)on conflict do nothing;
 insert into erp.qc_inspections select distinct on(inspection_id)inspection_id,status,physical_at,revision::bigint
  from jsonb_to_recordset(f->'qc')x(inspection_id uuid,status text,physical_at timestamptz,revision text)on conflict do nothing;
 insert into erp.qc_inspection_items select id,group_id,inspection_id,receipt_line_id,receipt_size_id,md5('q'||final_product_id||size_id)::uuid,good_pcs::numeric,bs_pcs::numeric
  from jsonb_to_recordset(f->'qc')x(id uuid,group_id uuid,inspection_id uuid,receipt_line_id uuid,receipt_size_id uuid,final_product_id uuid,size_id uuid,good_pcs text,bs_pcs text);
 insert into erp.products(id,size_id)select distinct md5('b'||product_id||coalesce(size_id::text,'-'))::uuid,size_id
  from jsonb_to_recordset(f->'bs')x(product_id uuid,size_id uuid)where product_id is not null on conflict do nothing;
 insert into erp.bs_cases(id,cutting_group_id,qc_item_id,product_id,source_laundry_receipt_line_id,source_laundry_bs_allocation_id,qty_pcs,status,detected_at_stage,physical_at,row_version)
  select id,group_id,qc_item_id,md5('b'||product_id||coalesce(size_id::text,'-'))::uuid,receipt_line_id,receipt_size_id,qty_pcs::numeric,status,detected_at_stage,physical_at,revision::bigint
  from jsonb_to_recordset(f->'bs')x(id uuid,group_id uuid,qc_item_id uuid,product_id uuid,size_id uuid,receipt_line_id uuid,receipt_size_id uuid,qty_pcs text,status text,detected_at_stage text,physical_at timestamptz,revision text);
 insert into erp.rework_orders select id,bs_case_id,sent_pcs::numeric,good_pcs::numeric,bs_pcs::numeric,physical_sent_at,completed_at,status,revision::bigint,good_fg_lot_id,completion_posted
  from jsonb_to_recordset(f->'reworks')x(id uuid,bs_case_id uuid,sent_pcs text,good_pcs text,bs_pcs text,physical_sent_at timestamptz,completed_at timestamptz,status text,revision text,good_fg_lot_id uuid,completion_posted boolean);
 insert into erp.bs_resolutions select id,bs_case_id,resolution_type,qty_pcs::numeric,source_rework_order_id,physical_at
  from jsonb_to_recordset(f->'resolutions')x(id uuid,bs_case_id uuid,resolution_type text,qty_pcs text,source_rework_order_id uuid,physical_at timestamptz);
 insert into erp.bs_case_hold_events select id,bs_case_id,action,resulting_status,physical_at,created_at
  from jsonb_to_recordset(f->'holds')x(id uuid,bs_case_id uuid,action text,resulting_status text,physical_at timestamptz,created_at timestamptz);
 insert into erp.fg_unsourced_receipts_v1 select id,bs_case_id,bs_resolution_id,qty_pcs::numeric,status,lot_id,quality_grade,physical_at
  from jsonb_to_recordset(f->'bs_fg')x(id uuid,bs_case_id uuid,bs_resolution_id uuid,qty_pcs text,status text,lot_id uuid,quality_grade text,physical_at timestamptz);
 insert into erp.laundry_failed_wash_attempts select id,receipt_line_id,delivery_id,custody_outcome,qty_pcs::numeric
  from jsonb_to_recordset(f->'failed')x(id uuid,receipt_line_id uuid,delivery_id uuid,custody_outcome text,qty_pcs text);
 insert into erp.laundry_failed_wash_batch_size_lines select id,attempt_id,delivery_size_id,size_id,qty_pcs::numeric
  from jsonb_to_recordset(f->'failed_sizes')x(id uuid,attempt_id uuid,delivery_size_id uuid,size_id uuid,qty_pcs text);
 insert into erp.laundry_redispatch_participant_events select id,event_type,source_id,successor_id,qty_pcs::numeric,source_offset_pcs,successor_offset_pcs,
  releases_allocation_event_id,released_delivery_id,timestamptz '2026-08-01T00:00:00Z'+o*interval '1 second'
  from rows from(jsonb_to_recordset(f->'redispatch')as(id uuid,event_type text,source_id uuid,successor_id uuid,qty_pcs text,source_offset_pcs bigint,
   successor_offset_pcs bigint,releases_allocation_event_id uuid,released_delivery_id uuid))with ordinality x(id,event_type,source_id,successor_id,qty_pcs,
   source_offset_pcs,successor_offset_pcs,releases_allocation_event_id,released_delivery_id,o);
 insert into erp.laundry_claims select id,delivery_id,receipt_line_id,claim_type,qty_pcs::numeric,status,opened_at,resolved_at,revision::bigint
  from jsonb_to_recordset(f->'claims')x(id uuid,delivery_id uuid,receipt_line_id uuid,claim_type text,qty_pcs text,status text,opened_at timestamptz,resolved_at timestamptz,revision text);
 insert into erp.sewing_terminal_events select id,group_id,qty_signed::numeric,event_kind,reversal_of_id,physical_at,revision::bigint
  from jsonb_to_recordset(f->'sewing')x(id uuid,group_id uuid,qty_signed text,event_kind text,reversal_of_id uuid,physical_at timestamptz,revision text);
 insert into erp.wip_control_flags select id,group_id,flag_type,status,revision::bigint,created_at,resolved_at
  from jsonb_to_recordset(f->'flags')x(id uuid,group_id uuid,flag_type text,status text,revision text,created_at timestamptz,resolved_at timestamptz);
end $$;
-- SYNTHETIC administrative clones of historical groups, labelled as such; they
-- never stand in for an ordinary Native posting. kind: direct (cut -> QC FG,
-- 2 positions per size), laundry (cut -> pickup -> delivery -> receipt -> QC FG,
-- 4 per size), bs_scrap (QC BS scrapped: EXIT), rework_fg (QC BS reworked to FG),
-- open (cut only), partial (QC leaves one piece), flag (spent + OPEN flag),
-- failed (spent + an earlier failed RETURN_UNPROCESSED attempt), hold (BS on
-- hold), rework_open (BS sent to rework, IN_PROGRESS), claim_other (spent +
-- OPEN OTHER claim), unposted (material issue not posted).
create function public.sx_seed(kind text,n integer,sizes integer default 1,q integer default 3,at timestamptz default '2026-09-01T00:00:00Z')returns uuid[]
language plpgsql as $$
declare out uuid[]:='{}';g uuid;r uuid;s uuid;y uuid;pk uuid;b uuid;d uuid;l uuid;ds uuid;rc uuid;rl uuid;rs uuid;insp uuid;item uuid;bc uuid;rw uuid;
 prod uuid;size uuid;z integer;po uuid:=md5('sx-po')::uuid;spent boolean:=kind not in('open','partial','unposted');bsq integer;
 laundry boolean:=kind in('laundry','failed','claim_other');
begin
 insert into erp.production_orders values(po,'${MODEL}')on conflict do nothing;
 for i in 1..n loop
  g:=gen_random_uuid();out:=array_append(out,g);
  insert into erp.cutting_groups values(g,po,1,'POSTED',null,null,at,case when laundry then at+interval '1 hour' end,kind<>'unposted');
  r:=gen_random_uuid();insert into erp.cutting_group_rolls values(r,g);
  if laundry then pk:=gen_random_uuid();b:=gen_random_uuid();
   insert into erp.cutting_pickups values(pk,g,'POSTED',at+interval '1 hour',1);insert into erp.cutting_distribution_batches values(b,pk);end if;
  for z in 1..sizes loop
   size:=('00000000-0000-4000-8000-00000000000'||z)::uuid;prod:=md5('sx-product-'||z)::uuid;
   insert into erp.products(id,size_id,identity_root_id,model_id)values(prod,size,md5('sx-root')::uuid,'${MODEL}')on conflict do nothing;
   s:=gen_random_uuid();y:=gen_random_uuid();
   insert into erp.cutting_group_size_slots values(s,size);insert into erp.cutting_roll_yields values(y,r,s,q);
   if kind in('open','unposted')then continue;end if;
   insp:=gen_random_uuid();item:=gen_random_uuid();rl:=null;rs:=null;
   if laundry then
    insert into erp.cutting_distribution_allocations values(gen_random_uuid(),b,y,q);
    d:=gen_random_uuid();l:=gen_random_uuid();ds:=gen_random_uuid();rc:=gen_random_uuid();rl:=gen_random_uuid();rs:=gen_random_uuid();
    insert into erp.laundry_deliveries values(d,'POSTED',at+interval '2 hour',1,null,'BLUE');
    insert into erp.laundry_delivery_lines values(l,g,d,q);
    insert into erp.laundry_delivery_batch_size_lines values(ds,l,b,size,q);
    insert into erp.laundry_receipts values(rc,'POSTED',at+interval '3 hour',1);
    insert into erp.laundry_receipt_lines values(rl,l,rc,q,0,0,0);
    insert into erp.laundry_receipt_batch_size_lines values(rs,rl,ds,size,q,0);
    if kind='claim_other'then insert into erp.laundry_claims values(gen_random_uuid(),d,null,'OTHER',1,'OPEN',at+interval '4 hour',null,1);end if;
    if kind='failed'then
     d:=gen_random_uuid();l:=gen_random_uuid();rc:=gen_random_uuid();
     insert into erp.laundry_deliveries values(d,'REVERSED',at+interval '90 minutes',1,null,'BLUE');
     insert into erp.laundry_delivery_lines values(l,g,d,q);
     insert into erp.laundry_receipts values(rc,'POSTED',at+interval '100 minutes',1);
     insert into erp.laundry_receipt_lines values(gen_random_uuid(),l,rc,0,0,0,0);
     insert into erp.laundry_failed_wash_attempts select gen_random_uuid(),x.id,d,'RETURN_UNPROCESSED',q from erp.laundry_receipt_lines x where x.delivery_line_id=l;
    end if;
   end if;
   bsq:=case when kind in('bs_scrap','rework_fg','hold','rework_open')then 1 else 0 end;
   insert into erp.qc_inspections values(insp,'POSTED',at+interval '4 hour',1);
   insert into erp.qc_inspection_items values(item,g,insp,rl,rs,prod,case when kind='partial'then q-1 else q-bsq end,bsq);
   if bsq>0 then
    bc:=gen_random_uuid();
    insert into erp.bs_cases(id,cutting_group_id,qc_item_id,product_id,qty_pcs,status,detected_at_stage,physical_at,row_version)
     values(bc,g,item,prod,1,case kind when 'hold'then 'ON_HOLD'when 'rework_open'then 'IN_REWORK'else 'RESOLVED'end,'QC',at+interval '4 hour',1);
    if kind='bs_scrap'then insert into erp.bs_resolutions values(gen_random_uuid(),bc,'SCRAP',1,null,at+interval '5 hour');end if;
    if kind in('rework_fg','rework_open')then rw:=gen_random_uuid();
     insert into erp.rework_orders values(rw,bc,1,case when kind='rework_fg'then 1 end,case when kind='rework_fg'then 0 end,at+interval '5 hour',
      case when kind='rework_fg'then at+interval '6 hour'end,case when kind='rework_fg'then 'COMPLETED'else 'IN_PROGRESS'end,1,null,kind='rework_fg');
     if kind='rework_fg'then insert into erp.bs_resolutions values(gen_random_uuid(),bc,'REWORK_SEWING',1,rw,at+interval '6 hour');end if;
    end if;
    if kind='hold'then insert into erp.bs_case_hold_events values(gen_random_uuid(),bc,'HOLD','ON_HOLD',at+interval '5 hour',at+interval '5 hour');end if;
   end if;
  end loop;
  if kind='flag'then insert into erp.wip_control_flags values(gen_random_uuid(),g,'PENDING_CORRECTION','OPEN',1,at+interval '5 hour',null);end if;
 end loop;
 return out;
end $$;
create function public.sx_reset()returns void language plpgsql as $$
begin
 execute(select 'truncate '||string_agg(format('%I.%I',schemaname,tablename),',')from pg_tables where schemaname='erp');
end $$;`

// Old/new results kept server side; node only sees compact verdicts.
const CHECKS = `
create table public.sx_out(name text primary key,state text not null,v jsonb);
create function public.sx_run(p_name text,p_sql text)returns text language plpgsql as $$
declare r jsonb;s text:='NO_ERROR';
begin
 begin execute p_sql into r;exception when others then s:=sqlstate||':'||sqlerrm;r:=null;end;
 insert into public.sx_out values(p_name,s,r)on conflict(name)do update set state=excluded.state,v=excluded.v;
 return s;
end $$;
create function public.sx_get(p_name text)returns jsonb language sql stable as $$select v from public.sx_out where name=p_name$$;
create function public.sx_state(p_name text)returns text language sql stable as $$select state from public.sx_out where name=p_name$$;
-- Group id of a pool or position key ('CUT:<group>:<size>').
create function public.sx_gid(k text)returns text language sql immutable as $$select case when split_part(k,':',1)='CUT'then split_part(k,':',2)end$$;
-- Old vs new source at one clock, both normalized by the unchanged kernel.
create function public.sx_parity(p_at timestamptz)returns jsonb language plpgsql as $$
declare o jsonb;n jsonb;wo jsonb;wn jsonb;s0 text;s1 text;w0 text:='NO_ERROR';w1 text:='NO_ERROR';ex jsonb;r jsonb;exs text[];
begin
 perform public.sx_run('old_source',format('select cp7_supply_native.wip_source_at_0(%L::timestamptz)',p_at));
 perform public.sx_run('new_source',format('select cp7_supply_native.wip_source_at(%L::timestamptz)',p_at));
 s0:=public.sx_state('old_source');s1:=public.sx_state('new_source');o:=public.sx_get('old_source');n:=public.sx_get('new_source');
 r:=jsonb_build_object('old_source',s0,'new_source',s1);
 if s1<>'NO_ERROR'then return r;end if;
 ex:=n->'scope'->'exhausted_cutting_groups';exs:=array(select jsonb_array_elements_text(ex));
 r:=r||jsonb_build_object('posted',jsonb_array_length(n->'scope'->'cutting_groups')+jsonb_array_length(ex),'kept',jsonb_array_length(n->'scope'->'cutting_groups'),
  'exhausted',jsonb_array_length(ex),
  'exhausted_sorted',ex=(select coalesce(jsonb_agg(x order by x::uuid),'[]')from jsonb_array_elements_text(ex)x),
  'scope_keys',(select jsonb_agg(k order by k)from jsonb_object_keys(n->'scope')k),
  'disjoint',not exists(select 1 from jsonb_array_elements_text(n->'scope'->'cutting_groups')x where x=any(exs)),
  'no_pruned_fact',not exists(select 1 from jsonb_each(n->'facts'->'cutting')c,jsonb_array_elements(case when jsonb_typeof(c.value)='array'then c.value else '[]'end)x
   where x->>'group_id'=any(exs)or(c.key='groups'and x->>'id'=any(exs))));
 perform public.sx_run('new_wip',format('select cp7_wip.normalize_production(%L::jsonb)',n));
 w1:=public.sx_state('new_wip');wn:=public.sx_get('new_wip');
 r:=r||jsonb_build_object('new_wip',w1,'new_status',wn->>'status','new_reason',wn->>'reason','new_positions',jsonb_array_length(wn->'positions'));
 if s0<>'NO_ERROR'then return r;end if;
 perform public.sx_run('old_wip',format('select cp7_wip.normalize_production(%L::jsonb)',o));
 w0:=public.sx_state('old_wip');wo:=public.sx_get('old_wip');
 r:=r||jsonb_build_object('old_wip',w0,'old_status',wo->>'status','old_reason',wo->>'reason','old_positions',jsonb_array_length(wo->'positions'),
  'same_scope_union',(select coalesce(jsonb_agg(x order by x::uuid),'[]')from(select jsonb_array_elements_text(n->'scope'->'cutting_groups')x union all select unnest(exs))u)=o->'scope'->'cutting_groups',
  'same_other_scope',(n->'scope')-'cutting_groups'-'exhausted_cutting_groups'=(o->'scope')-'cutting_groups',
  'same_other_facts',n->'facts'->'other'=o->'facts'->'other',
  -- Nothing pruned: the source is the predecessor's plus an empty list, byte for byte.
  'identical_when_none_pruned',case when jsonb_array_length(ex)=0 then n::text=jsonb_set(o,'{scope,exhausted_cutting_groups}','[]')::text end);
 if w0<>'NO_ERROR'or w1<>'NO_ERROR'or wo->>'status'<>'COMPLETE'or wn->>'status'<>'COMPLETE'then
  return r||jsonb_build_object('same_outcome',w0=w1 and wo->>'status' is not distinct from wn->>'status' and wo->>'reason' is not distinct from wn->>'reason'
   and wo->>'pool_key' is not distinct from wn->>'pool_key' and wo->>'source_id' is not distinct from wn->>'source_id');
 end if;
 return r||jsonb_build_object('same_outcome',true,
  'kept_positions_identical',wn->'positions'=(select coalesce(jsonb_agg(x order by k),'[]')from jsonb_array_elements(wo->'positions')with ordinality a(x,k)
   where coalesce(public.sx_gid(x->>'pool_key')<>all(exs),true)),
  'kept_totals_identical',wn->'totals'=(select coalesce(jsonb_agg(x order by k),'[]')from jsonb_array_elements(wo->'totals')with ordinality a(x,k)
   where coalesce(public.sx_gid(x->>'pool_key')<>all(exs),true)),
  'pruned_pools',(select count(*)from jsonb_array_elements(wo->'totals')x where public.sx_gid(x->>'pool_key')=any(exs)),
  'pruned_all_fg_or_exit',not exists(select 1 from jsonb_array_elements(wo->'totals')x where public.sx_gid(x->>'pool_key')=any(exs)
   and((x->>'wip_pcs')::numeric<>0 or(x->>'bs_pcs')::numeric<>0 or(x->>'withheld_pcs')::numeric<>0
    or(x->>'fg_pcs')::numeric+(x->>'exited_pcs')::numeric<>(x->>'input_pcs')::numeric)),
  'every_pruned_has_pools',(select count(distinct public.sx_gid(x->>'pool_key'))from jsonb_array_elements(wo->'totals')x where public.sx_gid(x->>'pool_key')=any(exs))=cardinality(exs),
  -- Independent restatement of the open signals over the predecessor's facts.
  'pruned_without_open_signal',not exists(
   select 1 from jsonb_array_elements(o->'facts'->'cutting'->'flags')x where x->>'group_id'=any(exs)and x->>'status'is distinct from 'RESOLVED'
   union all select 1 from jsonb_array_elements(o->'facts'->'cutting'->'failed')a join jsonb_array_elements(o->'facts'->'cutting'->'receipts')x
    on x->>'id'=a->>'receipt_line_id' where x->>'group_id'=any(exs)
   union all select 1 from jsonb_array_elements(o->'facts'->'cutting'->'bs')x where x->>'group_id'=any(exs)and x->>'status'='ON_HOLD'
   union all select 1 from jsonb_array_elements(o->'facts'->'cutting'->'reworks')w join jsonb_array_elements(o->'facts'->'cutting'->'bs')x
    on x->>'id'=w->>'bs_case_id' where x->>'group_id'=any(exs)and w->>'status'not in('COMPLETED','CANCELLED')
   union all select 1 from jsonb_array_elements(o->'facts'->'cutting'->'claims')c join jsonb_array_elements(o->'facts'->'cutting'->'deliveries')x
    on x->>'delivery_id'=c->>'delivery_id' where x->>'group_id'=any(exs)and c->>'status'not in('REJECTED','SETTLED','WRITTEN_OFF')),
  'same_signals',wn->'attention'=wo->'attention'and wn->'allocation_review_required'=wo->'allocation_review_required'
   and wn->'rewash_review_required'=wo->'rewash_review_required');
end $$;
-- Two stored netting results compared byte for byte once the three source
-- hashes of the second are read as the first's and the evidence list emptied.
create function public.sx_same_net(p_a text,p_b text)returns jsonb language plpgsql as $$
declare a jsonb:=public.sx_get(p_a);b jsonb:=public.sx_get(p_b);ha text[];hb text[];p text[]:='{schedule_run_result,supply_run_result,production_scope,exhausted_cutting_groups}';
 ta text;tb text;
begin
 ha:=array[a->>'source_hash',a#>>'{schedule_run_result,source_hash}',a#>>'{schedule_run_result,supply_run_result,source_hash}'];
 hb:=array[b->>'source_hash',b#>>'{schedule_run_result,source_hash}',b#>>'{schedule_run_result,supply_run_result,source_hash}'];
 ta:=jsonb_set(a,p,'[]')::text;tb:=replace(replace(replace(jsonb_set(b,p,'[]')::text,hb[1],ha[1]),hb[2],ha[2]),hb[3],ha[3]);
 return jsonb_build_object('identical',ta=tb,'rows_identical',tb::jsonb->'rows'=ta::jsonb->'rows','match_results_identical',b->'match_results'=a->'match_results',
  'wip_identical',b#>'{schedule_run_result,wip}'=a#>'{schedule_run_result,wip}','listed',jsonb_array_length(b#>p),'hashes_differ',ha<>hb,
  'status',b->>'status','allocation',b#>>'{allocation,status}','positions',jsonb_array_length(b#>'{schedule_run_result,wip,positions}'),
  'needs_check',(select count(*)from jsonb_array_elements(b->'match_results')x where x->'result'->>'match'in('NEEDS_CHECK','UNKNOWN')));
end $$;
-- Supply build before and after on the two sources: everything but the
-- declared contract fields is the same when nothing was pruned.
create function public.sx_build_parity()returns jsonb language plpgsql as $$
declare c0 jsonb;c1 jsonb;b0 jsonb;b1 jsonb;drop_keys text[]:=array['contract_version','production_scope','production_scope_basis','source_hash'];
begin
 c0:=cp7_baseline_native.source()||jsonb_build_object('production_sources',public.sx_get('old_source'));
 c1:=cp7_baseline_native.source()||jsonb_build_object('production_sources',public.sx_get('new_source'));
 b0:=cp7_supply_native.build_0(c0,'{}');b1:=cp7_supply_native.build(c1,'{}');
 return jsonb_build_object('old_contract',b0->>'contract_version','new_contract',b1->>'contract_version','new_basis',b1->>'production_scope_basis',
  'rest_identical',(b1-drop_keys)::text=(b0-drop_keys)::text,'wip_identical',(b1->'wip')::text=(b0->'wip')::text,
  'scope_is_old_plus_empty_list',b1->'production_scope'=(b0->'production_scope')||'{"exhausted_cutting_groups":[]}',
  'hash_changed',b1->>'source_hash'<>b0->>'source_hash',
  'old_path_absent',not(b1?'exhausted_cutting_groups'),'new_path',b1#>'{production_scope,exhausted_cutting_groups}');
end $$;`

// PL-8 part 3: the working tree's exhaustion-proof table (with the CP7
// immutability trigger) precedes the functions that read it.
export function proofStore(text) {
  const start = text.indexOf('create table cp7_supply_native.exhaustion_proofs('), trigger = text.indexOf('create trigger immutable_exhaustion_proof')
  if (start < 0 || trigger < start) throw new Error('working tree has no exhaustion proof store')
  return `create schema if not exists cp7_private;
   ${pick(now('scripts/cp7-src/snapshot/bootstrap.sql'), 'cp7_private.immutable_run')}
   ${text.slice(start, text.indexOf(';', trigger) + 1)}`
}

export async function installSupplyControls(db) {
  const head = git('scripts/cp7-src/planning/supply-source.sql'), tree = now('scripts/cp7-src/planning/supply-source.sql')
  const old = pick(head, 'cp7_supply_native.wip_source_at', 'cp7_supply_native.build')
    .replace('create function cp7_supply_native.wip_source_at(', 'create function cp7_supply_native.wip_source_at_0(')
    .replace('create function cp7_supply_native.build(', 'create function cp7_supply_native.build_0(')
  if (!old.includes("'cp7.native-supply.v1'") || old.includes('exhausted')) throw new Error('predecessor supply source is not the pre-PL-8 one')
  const fresh = [...functionBlocks(tree).keys()].filter(n => n.startsWith('cp7_supply_native.') && !/\.(serve|capture)$/.test(n))
  if (!fresh.includes('cp7_supply_native.exhausted_groups')) throw new Error('working tree has no PL-8 classifier')
  const schedule = now('scripts/cp7-src/planning/schedule-scenario.sql'), netting = now('scripts/cp7-src/planning/netting.sql')
  await db.execute(`create schema if not exists extensions;create extension if not exists pgcrypto schema extensions;
   ${STUBS}
   ${now('scripts/cp7-src/wip/graph.sql')}
   ${now('scripts/cp7-src/wip/normalize.sql')}
   ${now('scripts/cp7-src/wip/bs.sql')}
   ${now('scripts/cp7-src/wip/rewash.sql')}
   ${now('scripts/cp7-src/wip/other-normalize.sql')}
   ${now('scripts/cp7-src/wip/yield.sql')}
   ${pick(now('scripts/cp7-src/wip/production.sql'), 'cp7_wip.normalize_production')}
   ${now('scripts/cp7-src/wip/source.sql')}
   ${now('scripts/cp7-src/wip/other-source.sql')}
   create schema cp7_planning;
   ${pick(now('scripts/cp7-src/planning/bootstrap.sql'), 'cp7_planning.utc')}
   -- Stubs: the baseline source/build (products, review rows) and the schedule selection.
   create schema cp7_baseline_native;create schema cp7_supply_native;create schema cp7_schedule_native;create schema cp7_netting_native;
   create table public.sx_baseline(c jsonb not null);
   create function cp7_baseline_native.source()returns jsonb language sql stable as $$select c from public.sx_baseline$$;
   create function cp7_baseline_native.build(c jsonb,q jsonb)returns jsonb language sql immutable as $$
    select jsonb_build_object('captured_at',c->>'captured_at','rows',c->'stub_rows')$$;
   create function cp7_schedule_native.source_at(p_at timestamptz)returns jsonb language sql stable as $$select 'null'::jsonb$$;
   ${proofStore(tree)}
   ${pick(tree, ...fresh)}
   ${old}
   ${pick(now('scripts/cp7-src/planning/schedule.sql'), 'cp7_schedule_native.route', 'cp7_schedule_native.position_model')}
   ${pick(schedule, 'cp7_schedule_native.source', 'cp7_schedule_native.fingerprint', 'cp7_schedule_native.build')}
   ${pick(netting, 'cp7_netting_native.source', 'cp7_netting_native.fingerprint', 'cp7_netting_native.bound_product', 'cp7_netting_native.matching_models_within', 'cp7_netting_native.matching_models',
     'cp7_netting_native.matching', 'cp7_netting_native.matches', 'cp7_netting_native.timeline', 'cp7_netting_native.build')}
   ${LOADER}
   ${CHECKS}`)
}

// Products of one root and model (the clones' model) per size, with reviewed
// SCENARIO rows: the per-target numbers netting computes from the WIP.
export async function setBaseline(db, at = AT) {
  const root = 'a0000000-0000-4000-8000-0000000000a0', brand = 'b0000000-0000-4000-8000-0000000000b0'
  const products = SIZES.slice(0, 3).map((size, i) => ({ id: `c0000000-0000-4000-8000-00000000000${i + 1}`, root_id: root, model_id: MODEL, size_id: size, name: `PL8 synthetic ${i + 1}` }))
  const rows = products.map((p, i) => ({ target_key: `${root}:${p.size_id}`, size_id: p.size_id, target: { status: 'SCENARIO', target_pcs: String(30 + 7 * i) },
    available_fg_pcs: String(4 + i), profile: { config: { lead_days: '3', review_days: '2' } }, production_policy: { policy: { state: 'ACTIVE' } },
    demand_estimate: { daily_pcs: String(2 + i) }, refs: [{ kind: 'PRODUCT_TARGET', id: `${root}:${p.size_id}`, revision: '1' }] }))
  const c = { captured_at: at, status: 'COMPLETE', facts: { products }, profiles: [], production_policies: { rows: [] }, stub_rows: rows }
  const literal = v => `'${JSON.stringify(v).replaceAll("'", "''")}'::jsonb`
  await db.execute(`truncate public.sx_baseline;insert into public.sx_baseline values(${literal(c)});
   insert into erp.products(id,size_id,identity_root_id,model_id,brand_id,color_name)
   select (x->>'id')::uuid,(x->>'size_id')::uuid,(x->>'root_id')::uuid,(x->>'model_id')::uuid,'${brand}','BLUE' from jsonb_array_elements(${literal(products)})x on conflict do nothing;`)
}
// Defects of the f04 generator that can exist as stored rows (no duplicate
// keys, non-arrays, uncastable text or capture-level flags).
export const LOADABLE_DEFECTS = [null, null, null, null, null, null, 'NO_YIELDS', 'NEGATIVE_QC', 'FRACTION_QC', 'OVER_QC', 'DELIVERY_TOTAL', 'BATCH_LINEAGE',
  'LEGACY_MULTI_SIZE', 'RECEIPT_TOTAL', 'RECEIPT_LINEAGE', 'RECEIPT_MISSING', 'FAILED_PHYSICAL', 'CLAIM_RECEIPT', 'QC_LINEAGE', 'QC_PARENT', 'CANCELLED_SOURCE',
  'BS_LINEAGE', 'BS_SIZE', 'REWORK_SOURCE', 'REWORK_UNPOSTED', 'REWORK_MISMATCH', 'RESOLUTION_SOURCE', 'RESOLUTION_LINEAGE', 'RESOLUTION_TYPE', 'DUPLICATE_BS_FG',
  'BS_FG_MISMATCH', 'HOLD_STATE', 'HOLD_ZERO', 'REDISPATCH_OVERLAP', 'LEGACY_RECEIPT_MULTI_SIZE', 'NULL_REVISION']
// The PL-7 preflight predicate (an intent that is still open for its target),
// read from the working tree so the test follows the shipped path names.
export function intentPredicate() {
  const text = now('scripts/cp7-src/plan-native/preflight.sql')
  const start = text.indexOf(' if exists(select 1 from cp7_plan_native.intents i join erp.cutting_groups g on g.id=i.cutting_group_id where i.target_key=target')
  const end = text.indexOf('\n  or exists(select 1 from cp7_plan_native.intents i join erp.cutting_groups g on g.id=i.cutting_group_id where i.target_key=target and i.core_hash')
  if (start < 0 || end < 0) throw new Error('PL-7 predicate moved')
  return `create schema if not exists cp7_plan_native;
   create table if not exists cp7_plan_native.intents(target_key text not null,cutting_group_id uuid not null,core_hash text);
   create or replace function cp7_plan_native.sx_open_intent(target text,s jsonb)returns boolean language plpgsql stable set search_path='' as $f$
   begin return ${text.slice(start + ' if '.length, end)};end $f$;`
}
