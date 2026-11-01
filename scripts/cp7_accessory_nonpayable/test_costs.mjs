// Isolated function/accounting model. Native bodies are exact counted copies;
// the surrounding small schema/guards/valuation sources are labelled stubs.
// This is not an ERP installation, Native business journey, or browser test.
import assert from 'node:assert/strict'
import {readFileSync,writeFileSync,mkdtempSync,unlinkSync,rmdirSync,existsSync} from 'node:fs'
import {dirname,resolve,join} from 'node:path'
import {tmpdir} from 'node:os'
import {fileURLToPath,pathToFileURL} from 'node:url'
import {execFileSync} from 'node:child_process'
import {createHash,randomUUID} from 'node:crypto'
const here=dirname(fileURLToPath(import.meta.url)),root=resolve(here,'../..')
assert(process.env.PGLITE_MODULE)
const {PGlite}=await import(pathToFileURL(resolve(process.env.PGLITE_MODULE)).href)
const db=new PGlite(),q=(sql,args=[])=>db.query(sql,args)
const val=async(sql,args=[])=>Object.values((await q(sql,args)).rows[0])[0]
const id=n=>`00000000-0000-4000-8000-${String(n).padStart(12,'0')}`
const C={owner:id(1),special:id(2),ordinary:id(3),catA:id(4),catB:id(5),event:id(6),polA:id(7),polB:id(8),
  productA:id(9),productB:id(10),bomA:id(11),bomB:id(12),itemA:id(13),itemB:id(14),material:id(15)}
const files=['policy.sql','basis.sql','native_derivation.py','native-before/ensure_snapshot.sql','native-before/initial_accrual.sql','native-before/recost.sql','native-before/reverse_qc.sql','native-before/reverse_rework.sql','native-before/rework_target.sql']
const hashes=Object.fromEntries(files.map(f=>[f,createHash('sha256').update(readFileSync(resolve(here,f))).digest('hex')]))
const derived=execFileSync('python',['-B',resolve(here,'native_derivation.py'),'--sql'],{cwd:root,encoding:'utf8',maxBuffer:1024*1024})
const scratch=mkdtempSync(join(tmpdir(),'cp7-afui-native-')),derivedFile=join(scratch,'derived.sql')
let clashes
try {
  writeFileSync(derivedFile,derived)
  clashes=execFileSync('python',['-B',resolve(root,'scripts/cp7_plpgsql_clash_check.py'),derivedFile],{encoding:'utf8'})
}finally{if(existsSync(derivedFile))unlinkSync(derivedFile);rmdirSync(scratch)}
assert(clashes.trim().split('\n').every(line=>/^functions \d+$/.test(line)), 'DERIVED_NATIVE_ALIAS_CLASH:'+clashes)
const checks=[]
const test=async(name,fn)=>{await fn();checks.push({name,status:'PASS'})}
const counts=async()=>val(`select jsonb_build_object('basis',(select count(*)from cp7_accessory_nonpayable.good_bases_v1),
 'snapshots',(select count(*)from erp.fg_accessory_cost_snapshots),'journals',(select count(*)from erp.journal_entries),
 'entitlements',(select count(*)from erp.contractor_accessory_reimbursement_entitlements))`)
const ledger=(po,key)=>val(`select coalesce(sum(jl.debit-jl.credit),0)::text from erp.journal_lines jl
 join erp.journal_entries je on je.id=jl.journal_entry_id where jl.po_id=$1 and jl.account_id=erp.account_id($2)
 and je.status in('POSTED','REVERSED')`,[po,key])
async function fixture({special=true,cost='10',rework=false}={}) {
  const po=randomUUID(),lot=randomUUID(),group=randomUUID(),qc=randomUUID(),qcItem=randomUUID(),bs=randomUUID(),rw=randomUUID()
  const category=special?C.catA:C.catB,product=special?C.productA:C.productB,contractor=special?C.special:C.ordinary
  await q('update erp.control_avg set cost=$1 where category_id=$2',[cost,category])
  await q("insert into erp.production_orders values($1,$2,'SYNTHETIC','QC','QC')",[po,contractor])
  await q("insert into erp.fg_lots values($1,'PRODUCTION',$2,$3,'2026-10-15T03:00:00Z',1,$4,true)",[lot,po,product,rework?null:qcItem])
  if(rework) {
    await q("insert into erp.bs_cases values($1,$2,1,'IN_REWORK',null,null,null)",[bs,po])
    await q("insert into erp.rework_orders values($1,$2,$3,'COMPLETED',true,'INTERNAL',$4,null,null)",[rw,lot,bs,po])
    await q('insert into erp.rework_accessory_decisions values($1,$2,$3,$4,1)',[randomUUID(),rw,special?C.bomA:C.bomB,contractor])
    const decision=await val('select id from erp.rework_accessory_decisions where rework_order_id=$1',[rw])
    await q("insert into erp.rework_accessory_selection_lines values($1,$2,$3,$4,1,'CATEGORY_MOVING_AVG',0,3)",[randomUUID(),decision,special?C.itemA:C.itemB,category])
    await q("insert into erp.po_accessory_bom_commitments values($1,$2,$3,'2026-10-15T03:00:00Z')",[po,product,special?C.bomA:C.bomB])
  } else {
    await q("insert into erp.qc_inspections values($1,$2,'POSTED',null)",[qc,po])
    await q('insert into erp.qc_inspection_items values($1,$2)',[qcItem,qc])
  }
  await q("insert into erp.fg_stock_movements values($1,$2,$3,$4,$5,null,1)",
    [randomUUID(),lot,rework?'REWORK_IN':'QC_GOOD',rework?'REWORK_ORDER':'QC_ITEM',rework?rw:qcItem])
  return {po,lot,rw,qc,category,contractor}
}
const accrue=f=>q('select erp.post_accessory_reimbursement_accrual($1)',[f.lot])
async function recost(cost) {await q('update erp.control_avg set cost=$1 where category_id=$2',[cost,C.catA]);await q('select erp.refresh_accessory_hpp_after_material_recost($1,$2)',[C.material,'SYNTHETIC REVISED COST'])}
try {
  await db.exec(`
    create role anon nologin;create role authenticated nologin;create role service_role nologin;create schema erp;
    create function erp.require_internal()returns void language plpgsql as $$begin end;$$;
    create function erp.require_owner_admin()returns void language plpgsql as $$begin end;$$;
    create function erp.current_app_user_id()returns uuid language sql as $$select '${C.owner}'::uuid$$;
    create table erp.bc_policy_settings_v1(policy_key text primary key,status text,value jsonb,version bigint);
    create table erp.bc_policy_setting_events_v1(id uuid primary key,policy_key text,version bigint,status text,value jsonb);
    create table erp.accessory_categories(id uuid primary key,is_active boolean,category_code text,base_uom_code text);
    create table erp.contractors(id uuid primary key,contractor_type text);
    create table erp.contractor_hpp_policy_versions(id uuid primary key,contractor_id uuid,effective_from date,effective_to date,is_special boolean,row_version bigint);
    create table erp.production_orders(id uuid primary key,contractor_id uuid,po_number text,status text,current_stage text,updated_at timestamptz);
    create table erp.fg_lots(id uuid primary key,lot_origin text,po_id uuid,product_id uuid,produced_at timestamptz,initial_qty_pcs integer,qc_item_id uuid,is_open boolean);
    create table erp.rework_orders(id uuid primary key,good_fg_lot_id uuid,bs_case_id uuid,status text,cost_posted boolean,destination_type text,po_id uuid,notes text,updated_at timestamptz);
    create table erp.rework_accessory_decisions(id uuid primary key,rework_order_id uuid,bom_version_id uuid,reimbursement_contractor_id uuid,selected_item_count integer);
    create table erp.rework_accessory_selection_lines(id uuid,decision_id uuid,bom_item_id uuid,category_id uuid,qty_per_good_fg_base_snapshot numeric,
      hpp_method_snapshot text,hpp_standard_unit_cost_base_snapshot numeric,reimbursement_unit_rate_base_snapshot numeric);
    create table erp.po_accessory_bom_commitments(po_id uuid,product_id uuid,bom_version_id uuid,committed_at timestamptz,primary key(po_id,product_id));
    create table erp.initial_import_wip_outputs(lot_id uuid,opening_item_id uuid);
    create table erp.initial_import_production_sources(opening_item_id uuid,accessory_cost_included boolean);
    create table erp.accessory_bom_items(id uuid,bom_version_id uuid,category_id uuid,hpp_method text,hpp_uom_code text,hpp_standard_rate numeric,
      reimbursement_uom_code text,reimbursement_rate numeric,qty_per_good_fg_base numeric);
    create table erp.control_bom(product_id uuid primary key,bom_version_id uuid);
    create table erp.control_avg(category_id uuid primary key,cost numeric);
    create table erp.fg_accessory_cost_snapshots(id uuid primary key default gen_random_uuid(),lot_id uuid,po_id uuid,product_id uuid,bom_version_id uuid,
      bom_item_id uuid,category_id uuid,good_qty_pcs integer,qty_per_good_fg_base numeric(18,6),hpp_method text,
      category_avg_cost_base_snapshot numeric(18,6),hpp_unit_cost_base_snapshot numeric(18,6),reimbursement_unit_rate_base_snapshot numeric(18,6),
      costing_basis_at timestamptz,costing_basis_source text,
      total_hpp_cost numeric generated always as(good_qty_pcs*qty_per_good_fg_base*hpp_unit_cost_base_snapshot)stored,
      total_reimbursement numeric generated always as(good_qty_pcs*qty_per_good_fg_base*reimbursement_unit_rate_base_snapshot)stored,
      unique(lot_id,bom_item_id));
    create table erp.contractor_accessory_reimbursement_entitlements(snapshot_id uuid,contractor_id uuid,po_id uuid,lot_id uuid,product_id uuid,category_id uuid,
      physical_at timestamptz,amount numeric,payroll_status text default 'UNALLOCATED');
    create table erp.fg_accessory_cost_revisions(id uuid primary key default gen_random_uuid(),snapshot_id uuid,material_id uuid,old_category_avg_cost numeric,
      new_category_avg_cost numeric,old_hpp_unit_cost numeric,new_hpp_unit_cost numeric,reason text,changed_by uuid);
    create table erp.materials(id uuid,material_type text,accessory_category_id uuid);
    create table erp.journal_entries(id uuid primary key default gen_random_uuid(),source_type text,source_id uuid,status text,posting_at timestamptz default statement_timestamp());
    create table erp.journal_lines(journal_entry_id uuid,account_id uuid,debit numeric,credit numeric,contractor_id uuid,po_id uuid,product_id uuid);
    create table erp.accounting_period_control(singleton_id integer,closed_through date);
    create table erp.bs_cases(id uuid primary key,po_id uuid,qty_pcs integer,status text,qc_item_id uuid,notes text,updated_at timestamptz);
    create table erp.bs_resolutions(bs_case_id uuid,qty_pcs integer,source_rework_order_id uuid);
    create table erp.rework_component_lines(id uuid,rework_order_id uuid,amount_payable numeric);
    create table erp.payroll_work_items(source_type text,source_id uuid,payroll_id uuid);
    create table erp.payroll_settlements(id uuid,status text);
    create table erp.qc_inspections(id uuid primary key,po_id uuid,status text,updated_at timestamptz,inspection_number text default 'SYNTHETIC');
    create table erp.qc_inspection_items(id uuid primary key,inspection_id uuid);
    create table erp.laundry_receipts(delivery_id uuid,status text);
    create table erp.laundry_deliveries(id uuid,po_id uuid,status text);
    create table erp.cutting_groups(po_id uuid,picked_up_at timestamptz);
    create table erp.fg_stock_movements(id uuid primary key,lot_id uuid,movement_type text,source_type text,source_id uuid,reversal_of_id uuid,qty_signed numeric);
    create table erp.audit_logs(entity_type text,entity_id uuid,action text,changed_by uuid,change_reason text);
    create table erp.be_rework_targets_v1(rework_id uuid);
    create function erp.accessory_category_weighted_avg_cost_at(uuid,timestamptz)returns numeric language sql stable as $$select cost from erp.control_avg where category_id=$1$$;
    create function erp.accessory_uom_factor(uuid,text,timestamptz)returns numeric language sql stable as $$select 1::numeric$$;
    create function erp.commit_accessory_bom_for_lot(p_lot uuid)returns uuid language plpgsql as $$declare chosen uuid;l erp.fg_lots%rowtype;begin
      select * into l from erp.fg_lots where id=p_lot;select bom_version_id into chosen from erp.control_bom where product_id=l.product_id;
      insert into erp.po_accessory_bom_commitments values(l.po_id,l.product_id,chosen,l.produced_at)on conflict do nothing;return chosen;end;$$;
    create function erp.account_id(text)returns uuid language sql stable as $$select case $1 when 'WIP' then '${id(900)}'::uuid
      when 'ACCESSORY_REIMBURSE_VARIANCE' then '${id(901)}'::uuid when 'CONTRACTOR_PAYABLE' then '${id(902)}'::uuid else null end$$;
    create function erp.post_journal(p_type text,p_source uuid,p_date date,p_memo text,p_lines jsonb)returns uuid language plpgsql as $$
    declare chosen uuid;line jsonb;dr numeric;cr numeric;begin
      select sum((x->>'debit')::numeric),sum((x->>'credit')::numeric)into dr,cr from jsonb_array_elements(p_lines)x;
      if dr<>cr or dr<=0 or jsonb_array_length(p_lines)<2 then raise exception 'MODEL_UNBALANCED_OR_ZERO_JOURNAL';end if;
      if exists(select 1 from erp.journal_entries where source_type=p_type and source_id=p_source and status='POSTED')then raise exception 'MODEL_DUPLICATE_JOURNAL';end if;
      insert into erp.journal_entries(source_type,source_id,status)values(p_type,p_source,'POSTED')returning id into chosen;
      for line in select value from jsonb_array_elements(p_lines)loop
        insert into erp.journal_lines values(chosen,erp.account_id(line->>'mapping_key'),(line->>'debit')::numeric,(line->>'credit')::numeric,
          (line->>'contractor_id')::uuid,(line->>'po_id')::uuid,(line->>'product_id')::uuid);
      end loop;return chosen;end;$$;
    create function erp.reverse_journal(p_original uuid,p_reason text)returns uuid language plpgsql as $$declare made uuid;begin
      insert into erp.journal_entries(source_type,source_id,status)values('REVERSAL',p_original,'POSTED')returning id into made;
      insert into erp.journal_lines select made,account_id,credit,debit,contractor_id,po_id,product_id from erp.journal_lines where journal_entry_id=p_original;
      update erp.journal_entries set status='REVERSED' where id=p_original;return made;end;$$;
    create function erp._cp3_business_date(timestamptz)returns date language sql stable as $$select($1 at time zone 'Asia/Jakarta')::date$$;
    create function erp.invoice_recost_economic_date_v1()returns date language sql stable as $$select date'2026-10-01'$$;
    create function erp.rebuild_po_hpp(uuid,text)returns void language plpgsql as $$begin end;$$;
    create function erp.propagate_conversion_hpp_for_po(uuid)returns void language plpgsql as $$begin end;$$;
    create function erp.sync_po_hpp_to_gl(uuid,date)returns void language plpgsql as $$begin end;$$;
    create function erp.sync_laundry_accrual(uuid,date)returns void language plpgsql as $$begin end;$$;
    create function erp.fg_lot_has_active_downstream(uuid,text,text,uuid)returns boolean language sql as $$select false$$;
    create function erp.reverse_fg_movement(p_id uuid,p_reason text)returns void language sql as $$
      insert into erp.fg_stock_movements select gen_random_uuid(),lot_id,'REVERSAL',source_type,source_id,id,-qty_signed from erp.fg_stock_movements where id=p_id$$;
  `)
  await q('insert into erp.contractors values($1,\'MANDOR\'),($2,\'MANDOR\')',[C.special,C.ordinary])
  await q("insert into erp.accessory_categories values($1,true,'A','PCS'),($2,true,'B','PCS')",[C.catA,C.catB])
  await q("insert into erp.contractor_hpp_policy_versions values($1,$2,'2026-10-01',null,true,1),($3,$4,'2026-10-01',null,false,1)",[C.polA,C.special,C.polB,C.ordinary])
  const config=JSON.stringify({special_free_category_ids:[C.catA]})
  await q("insert into erp.bc_policy_settings_v1 values('ERP_DEC02','SET',$1::jsonb,2)",[config])
  await q("insert into erp.bc_policy_setting_events_v1 values($1,'ERP_DEC02',2,'SET',$2::jsonb)",[C.event,config])
  await q('insert into erp.control_bom values($1,$2),($3,$4)',[C.productA,C.bomA,C.productB,C.bomB])
  await q('insert into erp.control_avg values($1,10),($2,10)',[C.catA,C.catB])
  await q("insert into erp.materials values($1,'ACCESSORY',$2)",[C.material,C.catA])
  await q("insert into erp.accessory_bom_items values($1,$2,$3,'CATEGORY_MOVING_AVG','PCS',0,'PCS',3,1),($4,$5,$6,'CATEGORY_MOVING_AVG','PCS',0,'PCS',3,1)",[C.itemA,C.bomA,C.catA,C.itemB,C.bomB,C.catB])
  await db.exec(readFileSync(resolve(here,'policy.sql'),'utf8'))
  await db.exec(readFileSync(resolve(here,'basis.sql'),'utf8'))
  const seen=await val('select cp7_accessory_nonpayable.timeline_token_v1()')
  await q("select cp7_accessory_nonpayable.record_version_v1('2026-10-01',$1,$2,$3,'SYNTHETIC GOOD-DATE POLICY')",[C.event,randomUUID(),seen])
  await db.exec(derived)
  // The unchanged actual BE helper exits on the real no-target predicate.
  // Converted rework targets remain outside this isolated model's claims.
  await db.exec(readFileSync(resolve(here,'native-before/rework_target.sql'),'utf8'))
  await db.exec(readFileSync(resolve(here,'native-before/reverse_qc.sql'),'utf8'))
  const special=await fixture()
  await db.exec(readFileSync(resolve(here,'native-before/initial_accrual.sql'),'utf8'))
  await test('ORIGINAL_NATIVE_REPRODUCES_POSITIVE_HPP_ZERO_REIMBURSE_REFUSAL',async()=>{const before=await counts();await assert.rejects(()=>accrue(special),/HPP snapshot has cost but zero Mandor reimbursement/);assert.deepEqual(await counts(),before)})
  await db.exec(derived)
  await test('INITIAL_GOOD_HPP10_REIMBURSE0',async()=>{await accrue(special);assert.equal(await ledger(special.po,'WIP'),'10.00');assert.equal(await ledger(special.po,'ACCESSORY_REIMBURSE_VARIANCE'),'-10.00');assert.equal(await ledger(special.po,'CONTRACTOR_PAYABLE'),'0')})
  await test('FROZEN_ORIGINAL_BOM_RATE_AND_CONTRACTOR',async()=>{const b=await val('select basis from cp7_accessory_nonpayable.good_bases_v1 where lot_id=$1',[special.lot]);assert.equal(b.contractor_id,C.special);assert.equal(b.nonpayable,true);assert.equal(await val('select original_reimbursement_rate::text from cp7_accessory_nonpayable.good_bases_v1 where lot_id=$1',[special.lot]),'3.000000')})
  await test('FREE_GOOD_HAS_NO_PAYABLE_ENTITLEMENT',async()=>assert.equal(await val('select count(*)::integer from erp.contractor_accessory_reimbursement_entitlements where lot_id=$1',[special.lot]),0))
  await test('REPEATED_INITIAL_COMMAND_CHANGES_NOTHING',async()=>{const before=await counts();await accrue(special);assert.deepEqual(await counts(),before)})
  const ordinary=await fixture({special:false})
  await test('ORDINARY_CONTRACTOR_BOM_REIMBURSEMENT_PRESERVED',async()=>{await accrue(ordinary);assert.equal(await ledger(ordinary.po,'WIP'),'10.00');assert.equal(await ledger(ordinary.po,'CONTRACTOR_PAYABLE'),'-3.00');assert.equal(await val('select sum(amount)::text from erp.contractor_accessory_reimbursement_entitlements where lot_id=$1',[ordinary.lot]),'3.000000000000')})
  await q('update erp.accessory_bom_items set reimbursement_rate=0 where id=$1',[C.itemB])
  const unproven=await fixture({special:false})
  await test('UNPROVEN_POSITIVE_HPP_ZERO_REIMBURSE_STILL_REFUSED',async()=>{const before=await counts();await assert.rejects(()=>accrue(unproven),/HPP snapshot has cost but zero Mandor reimbursement/);assert.deepEqual(await counts(),before)})
  await q('update erp.accessory_bom_items set reimbursement_rate=3 where id=$1',[C.itemB])
  await test('BACKDATED_CATEGORY_POLICY_CANNOT_REWRITE_ACTIVE_GOOD',async()=>{const token=await val('select cp7_accessory_nonpayable.timeline_token_v1()');await assert.rejects(()=>q("select cp7_accessory_nonpayable.record_version_v1('2026-10-10',$1,$2,$3,'SYNTHETIC BACKDATE')",[C.event,randomUUID(),token]),/POSTED_GOOD_POLICY_REVIEW_REQUIRED/)})
  await test('SPECIAL_POLICY_CANNOT_REWRITE_ACTIVE_GOOD',async()=>await assert.rejects(()=>q('update erp.contractor_hpp_policy_versions set is_special=false where id=$1',[C.polA]),/POSTED_GOOD_SPECIAL_POLICY_USED/))
  const boundary=await fixture({cost:'0.005'})
  await test('HALF_CENT_INITIAL_RECOGNIZES_ONE_BALANCED_CENT',async()=>{await accrue(boundary);assert.equal(await ledger(boundary.po,'WIP'),'0.01');assert.equal(await ledger(boundary.po,'ACCESSORY_REIMBURSE_VARIANCE'),'-0.01')})
  const tiny=await fixture({cost:'0.004'})
  await test('SUBCENT_INITIAL_HAS_NO_ZERO_JOURNAL',async()=>{await accrue(tiny);assert.equal(await ledger(tiny.po,'WIP'),'0');assert.equal(await val("select count(*)::integer from erp.journal_entries where source_type='ACCESSORY_REIMBURSE_ACCRUAL' and source_id=$1",[tiny.lot]),0)})
  for(const [cost,expected]of[['0.006','0.01'],['0.014','0.01'],['0.016','0.02'],['0','0.00']]) {
    await test('CUMULATIVE_RECOST_FROM_SUBCENT:'+cost,async()=>{await recost(cost);assert.equal(await ledger(tiny.po,'WIP'),expected);assert.equal(await ledger(tiny.po,'CONTRACTOR_PAYABLE'),'0')})
    await test('NO_DOUBLE_INITIAL_AFTER_RECOST:'+cost,async()=>{const before=await counts();await accrue(tiny);assert.deepEqual(await counts(),before)})
  }
  const rw=await fixture({cost:'0',rework:true})
  await test('REWORK_ZERO_START_NO_FAKE_COMPANION',async()=>{await accrue(rw);assert.equal(await ledger(rw.po,'WIP'),'0');assert.equal(await val('select count(*)::integer from erp.rework_component_lines where rework_order_id=$1',[rw.rw]),0)})
  await recost('2')
  await test('ZERO_START_RECOST_RECOGNIZES_HPP_WITHOUT_PAYABLE',async()=>{assert.equal(await ledger(rw.po,'WIP'),'2.00');assert.equal(await ledger(rw.po,'ACCESSORY_REIMBURSE_VARIANCE'),'-2.00');assert.equal(await ledger(rw.po,'CONTRACTOR_PAYABLE'),'0')})
  await test('REWORK_INVERSE_REVERSES_NONPAYABLE_RECOST',async()=>{await q('select erp.reverse_rework_completion($1,$2)',[rw.rw,'SYNTHETIC INVERSE']);assert.equal(await ledger(rw.po,'WIP'),'0.00');assert.equal(await ledger(rw.po,'ACCESSORY_REIMBURSE_VARIANCE'),'0.00');assert.equal(await val('select lot_origin from erp.fg_lots where id=$1',[rw.lot]),'VOIDED_PRODUCTION')})
  await test('QC_INVERSE_REVERSES_INITIAL_AND_RECOST',async()=>{await q('select erp.reverse_qc($1,$2)',[special.qc,'SYNTHETIC INVERSE']);assert.equal(await ledger(special.po,'WIP'),'0.00');assert.equal(await ledger(special.po,'ACCESSORY_REIMBURSE_VARIANCE'),'0.00')})
  await test('HALF_CENT_AND_ZERO_START_QC_INVERSES',async()=>{for(const f of[boundary,tiny]){await q('select erp.reverse_qc($1,$2)',[f.qc,'SYNTHETIC INVERSE']);assert.equal(await ledger(f.po,'WIP'),'0.00')}})
  await test('POLICY_USE_RELEASED_AFTER_LAWFUL_GOOD_INVERSE',async()=>{const seen=await val('select cp7_accessory_nonpayable.timeline_token_v1()');await q("select cp7_accessory_nonpayable.record_version_v1('2026-10-10',$1,$2,$3,'SYNTHETIC REVIEW AFTER INVERSE')",[C.event,randomUUID(),seen])})
  const result={status:'ISOLATED_POSTGRES_NONPAYABLE_NATIVE_FUNCTION_MODEL_PASS',engine:await val('select version()'),checks,source_sha256:hashes,
    actual_ERP_Native_cases:0,actual_Auth_cases:0,actual_browser_cases:0,installed_on_candidate:false,
    full_stock_HPP_sales_pipeline_qualified:false,real_two_session_qualified:false,production_go:false,independent_acceptance:false}
  if(process.argv[2])writeFileSync(resolve(process.argv[2]),JSON.stringify(result,null,2)+'\n')
  console.log(JSON.stringify({...result,checks:{PASS:checks.length}}))
}catch(error){
  const result={status:'ISOLATED_MODEL_FIRST_FAILURE',error:String(error.stack||error),completed_checks:checks,source_sha256:hashes,actual_ERP_Native_cases:0,production_go:false}
  if(process.argv[2])writeFileSync(resolve(process.argv[2]),JSON.stringify(result,null,2)+'\n')
  throw error
}finally{await db.close()}
