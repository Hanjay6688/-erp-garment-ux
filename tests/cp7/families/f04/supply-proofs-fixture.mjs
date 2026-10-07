import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { functionBlocks } from './schedule-scenario-fixture.mjs'
import { MODEL, installSupplyControls } from './supply-exhausted-fixture.mjs'
// PL-8 part 3: stored exhaustion proofs. The predecessor is cb201edf's global
// supply source (git, renamed *_1), which classifies every posted group with
// normalize_cutting on every request; the working tree reuses a stored proof
// for a group whose captured rows hash to it. Same SYNTHETIC erp stand-ins,
// capture readers and WIP kernel as f04-supply-exhausted (installed by it).
export const proofBase = 'cb201edf39e65ab88ed54f4daa5b501ed774957f'
const git = path => execFileSync('git', ['show', `${proofBase}:${path}`], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 })
const now = path => readFileSync(path, 'utf8')
const pick = (text, ...names) => { const all = functionBlocks(text); return names.map(n => { if (!all.has(n)) throw new Error(n); return all.get(n) }).join('\n') }
export const TREE = 'scripts/cp7-src/planning/supply-source.sql'

// Fact arrays whose change alone can turn a proven group's verdict, each with
// the stored-row change that does it on a SYNTHETIC spent group (sp_mutate).
// groups, sewing and failed_sizes are hashed too: a groups-row change that
// matters removes the group from the posted set, sewing is not read by the
// kernel, and a failed_sizes row needs a failed attempt, which opens the group.
export const ARRAY_MUTATIONS = {
  yields: 'yields', batches: 'batches', deliveries: 'deliveries', delivery_sizes: 'delivery_sizes', receipts: 'receipts',
  receipt_sizes: 'receipt_sizes', qc: 'qc', bs: 'bs', reworks: 'reworks', resolutions: 'resolutions', holds: 'holds', bs_fg: 'bs_fg',
  failed: 'failed', redispatch: 'redispatch', claims: 'claims', flags: 'flags',
}
// Seed kinds (sx_seed) that carry rows of each mutated array.
export const SEED_FOR = {
  yields: 'direct', batches: 'laundry', deliveries: 'laundry', delivery_sizes: 'laundry', receipts: 'laundry', receipt_sizes: 'laundry', qc: 'direct',
  bs: 'bs_scrap', reworks: 'rework_fg', resolutions: 'bs_scrap', holds: 'bs_scrap', bs_fg: 'bs_scrap', failed: 'laundry', redispatch: 'laundry',
  claims: 'laundry', flags: 'direct',
}
export const MUTATIONS = [...Object.values(ARRAY_MUTATIONS), 'delivery_reversal', 'receipt_reversal', 'qc_reversal', 'qc_backdated', 'rework_late', 'groups', 'sewing', 'unpost']

const CHECKS = `
-- Predecessor and working tree at one clock, byte for byte (or the same
-- refusal). census: how many groups this clock reads from a stored proof, how
-- many batches mix proven and classified groups and how many batches with
-- proofs still prove nothing (test bookkeeping only).
create function public.sp_cmp(p_at timestamptz,census boolean default false)returns jsonb language plpgsql as $$
declare o jsonb;n jsonb;so text:='NO_ERROR';sn text:='NO_ERROR';ids uuid[];i integer:=1;k integer;part jsonb;kernel text;r jsonb;h integer;
 hit integer:=0;mixed integer:=0;whole integer:=0;refused integer:=0;before bigint;
begin
 select count(*)into before from cp7_supply_native.exhaustion_proofs;
 begin o:=cp7_supply_native.wip_source_at_1(p_at);exception when others then so:=sqlstate||':'||sqlerrm;end;
 begin n:=cp7_supply_native.wip_source_at(p_at);exception when others then sn:=sqlstate||':'||sqlerrm;end;
 if census then
  kernel:=cp7_supply_native.proof_kernel();
  select coalesce(array_agg(id order by id),'{}')into ids from erp.cutting_groups where material_issue_posted and cut_at<=p_at;
  k:=cardinality(ids);
  while i<=k and k<=20000 loop
   part:=cp7_wip.capture_cutting_sources(ids[i:least(i+49,k)],p_at);
   if part->>'status'='COMPLETE'then
    r:=cp7_supply_native.batch_reuse(part,kernel);h:=jsonb_array_length(r->'hit');hit:=hit+h;
    if h=least(i+49,k)-i+1 then whole:=whole+1;elsif h>0 then mixed:=mixed+1;end if;
    if h>0 and cp7_supply_native.batch_verdict(part,kernel)->'spent'='[]'then refused:=refused+1;end if;
   end if;
   i:=i+50;
  end loop;
 end if;
 return jsonb_build_object('old',so,'new',sn,'same',so=sn and o::text is not distinct from n::text,
  'exhausted',jsonb_array_length(n->'scope'->'exhausted_cutting_groups'),'kept',jsonb_array_length(n->'scope'->'cutting_groups'),
  'reused',hit,'mixed_batches',mixed,'reused_batches',whole,'refused_batches_with_proofs',refused,'reader_wrote',(select count(*)from cp7_supply_native.exhaustion_proofs)<>before);
end $$;
-- The supply build on both sources (baseline stub plus each production
-- source), byte for byte, or the same refusal.
create function public.sp_build_same(p_at timestamptz)returns boolean language plpgsql as $$
declare c jsonb:=cp7_baseline_native.source();a text;b text;
begin
 begin a:=cp7_supply_native.build(c||jsonb_build_object('production_sources',cp7_supply_native.wip_source_at_1(p_at)),'{}')::text;
 exception when others then a:=sqlstate||':'||sqlerrm;end;
 begin b:=cp7_supply_native.build(c||jsonb_build_object('production_sources',cp7_supply_native.wip_source_at(p_at)),'{}')::text;
 exception when others then b:=sqlstate||':'||sqlerrm;end;
 return a=b;
end $$;
-- Stores proofs in windows of p_window groups (not the source's batching);
-- p_max stops after that many groups for a partially proven history.
create function public.sp_prove(p_at timestamptz,p_window integer,p_max integer default null)returns integer language plpgsql as $$
declare after uuid;r jsonb;made integer:=0;seen integer:=0;
begin
 loop
  r:=cp7_supply_native.prove_exhausted(p_at,after,p_window);made:=made+(r->>'proofs_added')::integer;seen:=seen+(r->>'scanned')::integer;
  exit when(r->>'done')::boolean or seen>=coalesce(p_max,2147483647);after:=(r->>'next_after')::uuid;
 end loop;
 return made;
end $$;
-- One correction, cancellation/reversal or backdated row on group g, applied
-- after proofs were stored. Backdated rows carry a physical time one day
-- before the clock. Returns whether a row changed.
create function public.sp_mutate(kind text,g uuid,p_at timestamptz)returns boolean language plpgsql as $$
declare b timestamptz:=p_at-interval '1 day';n integer;
begin
 case kind
 when 'yields'then update erp.cutting_roll_yields set qty_pcs=qty_pcs+1 where id=(select y.id from erp.cutting_group_rolls r
  join erp.cutting_roll_yields y on y.cutting_group_roll_id=r.id where r.cutting_group_id=g order by y.id limit 1);
 when 'batches'then update erp.cutting_pickups set status='CANCELLED',row_version=row_version+1 where cutting_group_id=g;
 when 'deliveries'then update erp.laundry_delivery_lines set qty_sent_pcs=qty_sent_pcs+1
  where id=(select id from erp.laundry_delivery_lines where cutting_group_id=g order by id limit 1);
 when 'delivery_reversal'then update erp.laundry_deliveries set status='REVERSED',row_version=row_version+1
  where id in(select delivery_id from erp.laundry_delivery_lines where cutting_group_id=g)and status='POSTED';
 when 'delivery_sizes'then update erp.laundry_delivery_batch_size_lines set qty_sent_pcs=qty_sent_pcs+1 where id=(select s.id
  from erp.laundry_delivery_lines l join erp.laundry_delivery_batch_size_lines s on s.delivery_line_id=l.id where l.cutting_group_id=g order by s.id limit 1);
 when 'receipts'then update erp.laundry_receipt_lines set qty_good_received=qty_good_received+1 where id=(select r.id
  from erp.laundry_delivery_lines l join erp.laundry_receipt_lines r on r.delivery_line_id=l.id where l.cutting_group_id=g order by r.id limit 1);
 when 'receipt_reversal'then update erp.laundry_receipts set status='REVERSED',row_version=row_version+1 where status='POSTED'and id in(
  select r.receipt_id from erp.laundry_delivery_lines l join erp.laundry_receipt_lines r on r.delivery_line_id=l.id where l.cutting_group_id=g);
 when 'receipt_sizes'then update erp.laundry_receipt_batch_size_lines set qty_good_received=qty_good_received+1 where id=(select s.id
  from erp.laundry_delivery_lines l join erp.laundry_receipt_lines r on r.delivery_line_id=l.id
  join erp.laundry_receipt_batch_size_lines s on s.receipt_line_id=r.id where l.cutting_group_id=g order by s.id limit 1);
 when 'qc'then update erp.qc_inspection_items set qty_good_pcs=qty_good_pcs-1
  where id=(select id from erp.qc_inspection_items where cutting_group_id=g and qty_good_pcs>0 order by id limit 1);
 when 'qc_reversal'then update erp.qc_inspections set status='REVERSED',row_version=row_version+1 where id=(select q.id
  from erp.qc_inspection_items i join erp.qc_inspections q on q.id=i.inspection_id where i.cutting_group_id=g and q.status='POSTED'order by q.id limit 1);
 when 'qc_backdated'then
  insert into erp.products(id,size_id)select distinct md5('sp-q'||s.size_id)::uuid,s.size_id from erp.cutting_group_rolls r
   join erp.cutting_roll_yields y on y.cutting_group_roll_id=r.id join erp.cutting_group_size_slots s on s.id=y.size_slot_id
   where r.cutting_group_id=g on conflict do nothing;
  insert into erp.qc_inspections values(md5('sp-i'||g||b)::uuid,'POSTED',b,1);
  insert into erp.qc_inspection_items select gen_random_uuid(),g,md5('sp-i'||g||b)::uuid,null,null,md5('sp-q'||s.size_id)::uuid,1,0
   from erp.cutting_group_rolls r join erp.cutting_roll_yields y on y.cutting_group_roll_id=r.id
   join erp.cutting_group_size_slots s on s.id=y.size_slot_id where r.cutting_group_id=g order by y.id limit 1;
 when 'bs'then update erp.bs_cases set status='ON_HOLD',row_version=row_version+1
  where id=(select id from erp.bs_cases where cutting_group_id=g and status<>'CANCELLED'order by id limit 1);
 when 'reworks'then update erp.rework_orders set status='IN_PROGRESS',row_version=row_version+1 where id=(select w.id
  from erp.bs_cases c join erp.rework_orders w on w.bs_case_id=c.id where c.cutting_group_id=g and w.status='COMPLETED'order by w.id limit 1);
 when 'rework_late'then update erp.rework_orders set completed_at=p_at+interval '1 hour',row_version=row_version+1 where id=(select w.id
  from erp.bs_cases c join erp.rework_orders w on w.bs_case_id=c.id where c.cutting_group_id=g and w.status='COMPLETED'order by w.id limit 1);
 when 'resolutions'then update erp.bs_resolutions set qty_pcs=qty_pcs+1 where id=(select d.id
  from erp.bs_cases c join erp.bs_resolutions d on d.bs_case_id=c.id where c.cutting_group_id=g order by d.id limit 1);
 when 'holds'then insert into erp.bs_case_hold_events select gen_random_uuid(),c.id,'HOLD','ON_HOLD',b,b
  from erp.bs_cases c where c.cutting_group_id=g and c.status<>'CANCELLED'order by c.id limit 1;
 when 'bs_fg'then insert into erp.fg_unsourced_receipts_v1 select gen_random_uuid(),c.id,d.id,d.qty_pcs+1,'POSTED',null,'B',b
  from erp.bs_cases c join erp.bs_resolutions d on d.bs_case_id=c.id where c.cutting_group_id=g and d.source_rework_order_id is null order by d.id limit 1;
 when 'failed'then insert into erp.laundry_failed_wash_attempts select gen_random_uuid(),r.id,l.delivery_id,'RETRY_AT_VENDOR',1
  from erp.laundry_delivery_lines l join erp.laundry_receipt_lines r on r.delivery_line_id=l.id where l.cutting_group_id=g order by r.id limit 1;
 when 'redispatch'then insert into erp.laundry_redispatch_participant_events select gen_random_uuid(),'ALLOCATE',s.id,s.id,1,0,0,null,null,b
  from erp.laundry_delivery_lines l join erp.laundry_delivery_batch_size_lines s on s.delivery_line_id=l.id where l.cutting_group_id=g order by s.id limit 1;
 when 'claims'then insert into erp.laundry_claims select gen_random_uuid(),l.delivery_id,null,'OTHER',1,'OPEN',b,null,1
  from erp.laundry_delivery_lines l where l.cutting_group_id=g order by l.id limit 1;
 when 'flags'then insert into erp.wip_control_flags values(gen_random_uuid(),g,'PENDING_CORRECTION','OPEN',1,b,null);
 when 'groups'then update erp.cutting_groups set row_version=row_version+1 where id=g;
 when 'sewing'then insert into erp.sewing_terminal_events values(gen_random_uuid(),g,1,'COMPLETE',null,b,1);
 when 'unpost'then update erp.cutting_groups set material_issue_posted=false where id=g;
 else raise exception 'sp_mutate %',kind;
 end case;
 get diagnostics n=row_count;
 return n>0;
end $$;
-- One round of mutations: kind i goes to the first group of its pool (the
-- proven groups for the first p_proven kinds, then any posted group), in an
-- order fixed by p_salt, that the kind changes. Returns the kinds applied.
create function public.sp_mutate_round(p_kinds text[],p_proven integer,p_salt integer,p_at timestamptz)returns jsonb language plpgsql as $$
declare done jsonb:='[]';g uuid;i integer;
begin
 for i in 1..cardinality(p_kinds) loop
  for g in select x from unnest(case when i<=p_proven then array(select distinct group_id from cp7_supply_native.exhaustion_proofs)
    else array(select id from erp.cutting_groups where material_issue_posted)end)x order by md5(x::text||p_salt||':'||i) loop
   if public.sp_mutate(p_kinds[i],g,p_at)then done:=done||to_jsonb(p_kinds[i]);exit;end if;
  end loop;
 end loop;
 return done;
end $$;
-- Moves group g's rows to id x (controls which capture batch it lands in).
create function public.sp_rekey(g uuid,x uuid)returns void language plpgsql as $$
begin
 update erp.cutting_groups set id=x where id=g;update erp.cutting_group_rolls set cutting_group_id=x where cutting_group_id=g;
 update erp.cutting_pickups set cutting_group_id=x where cutting_group_id=g;update erp.laundry_delivery_lines set cutting_group_id=x where cutting_group_id=g;
 update erp.qc_inspection_items set cutting_group_id=x where cutting_group_id=g;update erp.bs_cases set cutting_group_id=x where cutting_group_id=g;
 update erp.sewing_terminal_events set cutting_group_id=x where cutting_group_id=g;update erp.wip_control_flags set cutting_group_id=x where cutting_group_id=g;
end $$;
-- Group b's first delivery line moves onto group a's delivery header, so one
-- delivery (and every claim on it) belongs to both groups.
create function public.sp_share(a uuid,b uuid)returns boolean language plpgsql as $$
declare n integer;
begin
 update erp.laundry_delivery_lines set delivery_id=(select delivery_id from erp.laundry_delivery_lines where cutting_group_id=a order by id limit 1)
  where id=(select id from erp.laundry_delivery_lines where cutting_group_id=b order by id limit 1)
   and exists(select 1 from erp.laundry_delivery_lines where cutting_group_id=a);
 get diagnostics n=row_count;return n>0;
end $$;
-- SYNTHETIC spent groups with many sizes (direct QC to FG, 2 pieces a size).
create function public.sp_seed_wide(n integer,sizes integer,at timestamptz)returns uuid[]language plpgsql as $$
declare out uuid[]:='{}';g uuid;r uuid;s uuid;y uuid;size uuid;insp uuid;po uuid:=md5('sx-po')::uuid;
begin
 insert into erp.production_orders values(po,'${MODEL}')on conflict do nothing;
 for i in 1..n loop
  g:=gen_random_uuid();out:=out||g;insp:=gen_random_uuid();r:=gen_random_uuid();
  insert into erp.cutting_groups values(g,po,1,'POSTED',null,null,at,null,true);insert into erp.cutting_group_rolls values(r,g);
  insert into erp.qc_inspections values(insp,'POSTED',at+interval '4 hour',1);
  for z in 1..sizes loop
   size:=('00000000-0000-4000-8000-'||lpad(z::text,12,'0'))::uuid;s:=gen_random_uuid();y:=gen_random_uuid();
   insert into erp.products(id,size_id)values(md5('sp-w'||z)::uuid,size)on conflict do nothing;
   insert into erp.cutting_group_size_slots values(s,size);insert into erp.cutting_roll_yields values(y,r,s,2);
   insert into erp.qc_inspection_items values(gen_random_uuid(),g,insp,null,null,md5('sp-w'||z)::uuid,2,0);
  end loop;
 end loop;
 return out;
end $$;`

export async function installProofControls(db) {
  await installSupplyControls(db)
  const old = pick(git(TREE), 'cp7_supply_native.exhausted_groups', 'cp7_supply_native.wip_source_at')
    .replace('create function cp7_supply_native.exhausted_groups(', 'create function cp7_supply_native.exhausted_groups_1(')
    .replace('create function cp7_supply_native.wip_source_at(', 'create function cp7_supply_native.wip_source_at_1(')
    .replace('proved:=cp7_supply_native.exhausted_groups(part)', 'proved:=cp7_supply_native.exhausted_groups_1(part)')
  if (!old.includes('exhausted_groups_1(part)') || old.includes('exhaustion_proofs') || !old.includes("cp7_wip.normalize_cutting(capture)")) throw new Error('predecessor is not the cb201edf classifier')
  if (!now(TREE).includes('cp7_supply_native.exhaustion_proofs')) throw new Error('working tree stores no proofs')
  await db.execute(`${old}\n${CHECKS}`)
}

// The supply run writer (working tree serve/capture and runs table) over stubs
// of the access check and query reader it calls: one actor, query as given.
export async function installCaptureStubs(db) {
  const tree = now(TREE), start = tree.indexOf('create table cp7_supply_native.runs('), trigger = tree.indexOf('create trigger immutable_supply_run')
  if (start < 0 || trigger < start) throw new Error('working tree has no supply runs table')
  await db.execute(`create function cp7_private.access_now()returns jsonb language sql stable as $$select '{"actor":"5e1f0000-0000-4000-8000-000000000001"}'::jsonb$$;
   create function cp7_planning.history_query(q jsonb)returns jsonb language sql immutable as $$select q$$;
   ${tree.slice(start, tree.indexOf(';', trigger) + 1)}
   ${pick(tree, 'cp7_supply_native.serve', 'cp7_supply_native.capture')}`)
}

// The isolation rules of batch_reuse (which rows belong to a group, which
// columns link two groups, which clock read the hash carries) were derived
// from these kernel functions as of proofBase. A function whose text differs
// from proofBase is listed: re-check those rules, then move proofBase.
export const ANALYSED_KERNEL = {
  'scripts/cp7-src/wip/source.sql': ['cp7_wip.capture_cutting_sources'],
  'scripts/cp7-src/wip/normalize.sql': ['cp7_wip.transition', 'cp7_wip.ref', 'cp7_wip.normalize_cutting'],
  'scripts/cp7-src/wip/bs.sql': ['cp7_wip.settle_bs'], 'scripts/cp7-src/wip/rewash.sql': ['cp7_wip.redispatch_valid'],
  'scripts/cp7-src/wip/graph.sql': ['cp7_wip.reconcile'], 'scripts/cp7-src/wip/bootstrap.sql': ['cp7_wip.fields', 'cp7_wip.key', 'cp7_wip.pcs', 'cp7_wip.refs'],
}
export function kernelDrift() {
  const drift = []
  for (const [path, names] of Object.entries(ANALYSED_KERNEL)) {
    const before = functionBlocks(git(path)), after = functionBlocks(now(path))
    for (const n of names) if (!after.has(n) || before.get(n) !== after.get(n)) drift.push(n)
  }
  return drift
}

// A working-tree function with one fragment replaced (a weaker design), or as
// shipped. The fragment must occur exactly once.
export function variant(name, from = null, to = null) {
  const block = pick(now(TREE), name).replace(/^create function /, 'create or replace function ')
  if (from === null) return block
  if (block.split(from).length !== 2) throw new Error(`${name}: fragment not unique: ${from}`)
  return block.replace(from, to)
}
export const NORMALIZE = () => pick(now('scripts/cp7-src/wip/normalize.sql'), 'cp7_wip.normalize_cutting').replace(/^create function /, 'create or replace function ')
