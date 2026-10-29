/** Focused SQL execution: actual D quote and retained collectors/kernel, structural/factual doubles elsewhere. */
import {readFile} from 'node:fs/promises'
import {execFileSync} from 'node:child_process'
import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE||'@electric-sql/pglite')
const here=new URL('../cp7_credit_correction_de/',import.meta.url),db=new PGlite(),id=n=>`00000000-0000-4000-8000-${String(n).padStart(12,'0')}`
const [sale,ret,customer,ar,cohort,family,allocation,location,part,component,plan,consumer,target]=Array.from({length:13},(_,i)=>id(i+1))
const statement=async(file,name)=>{const text=await readFile(new URL(file,here),'utf8'),start=text.indexOf('create function '+name+'(');assert(start>=0);const tail=text.slice(start),end=tail.indexOf('$$;',tail.indexOf('$$')+2);return tail.slice(0,end+3)}
try{
 await db.exec(await readFile(new URL('schema-double.sql',import.meta.url),'utf8'))
 for(const file of ['../cp7_customer_credit/kernel/kernel.sql','../cp7_customer_credit/ordinal-wrapper/wrapper.sql','review.sql','facts.sql','owning.sql','proof.sql','posting.sql','materialize.sql','closure.sql'])await db.exec(await readFile(new URL(file,here),'utf8'))
 await db.exec(`create schema cp7_note;create table cp7_note.revisions(root_sale_id uuid,previous_sale_id uuid,replacement_sale_id uuid);create schema cp7_credit_incoming;
 create or replace function auth.uid()returns uuid language sql stable as $$select '${customer}'::uuid$$;
 create function cp7_sales_return_correction.access_now()returns jsonb language sql volatile as $$select '{"declared_authority_double":true}'::jsonb$$;
 create function cp7_sales_return_correction.validate(jsonb)returns void language plpgsql as $$begin null;end$$;
 create function cp7_credit.assert_current_materialized_profile(uuid,uuid,uuid)returns void language plpgsql stable as $$begin null;end$$;
 create function cp7_credit.inspect_current_materialized_profile(uuid,uuid,uuid)returns jsonb language sql stable as $$select '{"I":"200.00","actual_objects":[]}'::jsonb$$;
 create function cp7_credit.source_native_snapshot_v1(uuid)returns jsonb language sql stable as $$select '{"declared_source_double":true}'::jsonb$$;
 create function cp7_credit.source_hpp_lot_ids_v1(uuid)returns uuid[]language sql stable as $$select '{}'::uuid[]$$;
 create function cp7_credit.consumer_event_data_v1(uuid)returns jsonb language sql stable as $$select '{"declared_consumer_provenance_double":true}'::jsonb$$;
 create or replace function ow04_source_proposal.sha(jsonb)returns text language sql immutable as $$select encode(sha256(convert_to($1::text,'UTF8')),'hex')$$;
 create function cp7_credit_incoming.incoming_applied_v1(uuid)returns numeric language sql stable as $$select 0::numeric$$;
 create function erp.resolve_accounting_transaction_date(date)returns date language sql stable as $$select $1$$;
 create or replace function cp7_credit.account_by_mapping_v1(text)returns uuid language sql stable as $$select '${ar}'::uuid$$;
 `)
 if(!(await db.query("select to_regclass('erp.be_conversion_sources_v1')x")).rows[0].x)await db.exec('create table erp.be_conversion_sources_v1(source_lot_id uuid)')
 await db.exec(await statement('../cp7_customer_credit/ledger/01_immutable_facts.proposal.sql','cp7_credit.pg_jsonb_sha256'))
 await db.exec(await statement('../cp7_customer_credit/coordinator/01_coordinator_facts.sql','cp7_credit.initial_base_events_v1'))
 await db.exec(await statement('../cp7_customer_credit/coordinator/05_factual_profile.sql','cp7_credit.initial_ordinal_input_v1'))
 const active=await statement('../cp7_customer_credit/consumer/05_consumer_data.sql','cp7_credit.consumer_active_events_v1').catch(async()=>{
  const files=execFileSync('rg',['--files',new URL('../cp7_customer_credit/consumer/',here).pathname],{encoding:'utf8'}).trim().split('\n');
  for(const file of files)if(file.endsWith('.sql')&&(await readFile(file,'utf8')).includes('create function cp7_credit.consumer_active_events_v1('))return statement(file,'cp7_credit.consumer_active_events_v1');throw Error('active reader missing')
 })
 await db.exec(active.replace('create function ','create or replace function '))
 await db.query('insert into erp.sales_headers(id,customer_id,status)values($1,$2,\'PAID\')',[sale,customer])
 await db.query('insert into erp.sales_returns(id,sale_id,customer_id,status,physical_at)values($1,$2,$3,\'POSTED\',\'2026-10-02T05:00:00Z\')',[ret,sale,customer])
 await db.query('insert into erp.sales_return_items(id,return_id,sale_stock_allocation_id,location_id,qty_pcs,quality_grade,refund_amount)values($1,$2,$3,$4,2,\'GRADE_A\',200)',[id(41),ret,allocation,location])
 await db.query('insert into erp.accounting_account_mappings(mapping_key,account_id)values(\'AR_CUSTOMER\',$1)',[ar])
 for(const [n,type,source,debit,credit,date]of [[21,'SALE',sale,1000,0,'2026-10-01'],[22,'SALES_PAYMENT',id(43),0,1000,'2026-10-01'],[23,'SALES_RETURN',ret,0,200,'2026-10-02']]){
  await db.query('insert into erp.journal_entries(id,source_type,source_id,status,economic_date,transaction_date)values($1,$2,$3,\'POSTED\',$4,$4)',[id(n),type,source,date])
  await db.query('insert into erp.journal_lines(id,journal_entry_id,account_id,debit,credit)values($1,$2,$3,$4,$5)',[id(n+100),id(n),ar,debit,credit])
 }
 await db.query('insert into erp.sales_payments(id,sale_id,status,amount)values($1,$2,\'POSTED\',1000)',[id(43),sale])
 await db.query("insert into cp7_credit.return_families(id,family_root_sale_id,family_ordinal,first_return_id,source_sha256)values($1,$2,1,$3,repeat('a',64))",[family,sale,ret])
 await db.query('insert into cp7_credit.return_family_members(family_id,return_id)values($1,$2)',[family,ret])
 await db.query('insert into cp7_credit.cohorts(id,family_id,source_sale_id,source_return_id)values($1,$2,$3,$4)',[cohort,family,sale,ret])
 await db.query('insert into cp7_credit.recognition_plans(id,cohort_id)values($1,$2)',[plan,cohort])
 await db.query('insert into cp7_credit.recognition_components(id,plan_id)values($1,$2)',[component,plan])
 await db.query('insert into cp7_credit.component_parts(id,component_id,amount)values($1,$2,200)',[part,component])
 await db.query("insert into cp7_credit.component_journals(part_id,journal_id,economic_date,transaction_date)values($1,$2,'2026-10-02','2026-10-02')",[part,id(44)])
 const p={sale_id:sale,return_id:ret,review_token:'a'.repeat(32),return_review_token:'b'.repeat(32),change_reason:'Nilai kredit ditinjau',replacement:{physical_at:'2026-10-02T05:00:00Z',notes:null,items:[{allocation_id:allocation,location_id:location,qty_pcs:'2',quality_grade:'GRADE_A',refund_amount:'250.00',notes:null}]}}
 const quote=async(payload)=>(await db.query('select cp7_credit_correction_de.quote_v1($1::jsonb)q',[payload])).rows[0].q

 // All rows below are declared LOCAL structural/source doubles. They are not
 // posted Native documents. The unchanged Native normalizer is executed only
 // for its per-item cap; stock, cost, journal and full transaction proof are absent.
 await db.query('insert into erp.sales_items(id,sale_id,product_id,qty_pcs,unit_price_snapshot,discount_amount,line_total)values($1,$2,$3,5,200,0,1000)',[id(80),sale,id(82)])
 await db.query('insert into erp.sale_stock_allocations(id,sale_item_id,qty_pcs,lot_id,unit_hpp_snapshot)values($1,$2,5,$3,10)',[allocation,id(80),id(81)])
 await db.query("insert into erp.locations(id,is_active,location_type)values($1,true,'FG_WAREHOUSE')",[location])
 await db.exec(`create table cap_source_override(snapshot jsonb);
 create or replace function cp7_credit.source_native_snapshot_v1(p_sale uuid)returns jsonb language sql stable as $$
 select coalesce((select snapshot from public.cap_source_override),jsonb_build_object('declared_cap_source_double',true,
 'sale',(select to_jsonb(h)from erp.sales_headers h where h.id=p_sale),
 'items',(select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]')from erp.sales_items i where i.sale_id=p_sale),
 'allocations',(select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')from erp.sale_stock_allocations a)))$$;
 create view erp.v_current_hpp as select '${id(81)}'::uuid lot_id,10::numeric hpp_per_pcs;`)
 const normalizer=await readFile(new URL('retained/normalizer.sql',import.meta.url),'utf8')
 const normalizerSHA=createHash('sha256').update(normalizer).digest('hex');assert.equal(normalizerSHA,'1ca83d0e1728833c1fff2d3a285b142f8b1064e85afd3560573f885fedfd92bc')
 await db.exec(normalizer)
 await db.exec('create trigger local_cap_only before insert on erp.sales_return_items for each row execute function erp.normalize_sales_return_item_from_allocation()')
 // Additional rows are LOCAL structural/source doubles, not posted documents.
 const productA=id(82),productB=id(96),peer=id(200),draft=id(300)
 await db.query('update erp.sales_return_items set product_id=$1,lot_id=$2 where return_id=$3',[productA,id(81),ret])
 await db.query('update erp.sale_stock_allocations set location_id=$1 where id=$2',[location,allocation])
 await db.query('insert into erp.fg_lots(id,product_id)values($1,$2)',[id(81),productA])
 await db.query('insert into erp.sales_items(id,sale_id,product_id,qty_pcs,line_total)values($1,$2,$3,1,1000)',[id(95),sale,productB])
 await db.query('update erp.journal_lines set debit=2000 where journal_entry_id=$1',[id(21)])
 await db.query('update erp.journal_lines set credit=2000 where journal_entry_id=$1',[id(22)])
 await db.query('update erp.sales_payments set amount=2000 where sale_id=$1',[sale])
 await db.query("insert into erp.sales_returns(id,sale_id,customer_id,status,physical_at)values($1,$2,$3,'POSTED','2026-10-02T05:01:00Z')",[peer,sale,customer])
 await db.query("insert into erp.sales_return_items(id,return_id,sale_stock_allocation_id,location_id,qty_pcs,quality_grade,refund_amount)values($1,$2,$3,$4,3,'GRADE_A',600)",[id(210),peer,allocation,location])
 await db.query("insert into erp.journal_entries(id,source_type,source_id,status,economic_date,transaction_date)values($1,'SALES_RETURN',$2,'POSTED','2026-10-02','2026-10-02')",[id(205),peer])
 await db.query('insert into erp.journal_lines(id,journal_entry_id,account_id,debit,credit)values($1,$2,$3,0,600)',[id(207),id(205),ar])
 await db.query("insert into cp7_credit.return_families(id,family_root_sale_id,family_ordinal,first_return_id,source_sha256)values($1,$2,2,$3,repeat('b',64))",[id(201),sale,peer])
 await db.query('insert into cp7_credit.return_family_members(family_id,return_id)values($1,$2)',[id(201),peer])
 await db.query('insert into cp7_credit.cohorts(id,family_id,source_sale_id,source_return_id)values($1,$2,$3,$4)',[id(202),id(201),sale,peer])
 await db.query('insert into cp7_credit.recognition_plans(id,cohort_id)values($1,$2)',[id(203),id(202)])
 await db.query('insert into cp7_credit.recognition_components(id,plan_id)values($1,$2)',[id(204),id(203)])
 await db.query('insert into cp7_credit.component_parts(id,component_id,amount)values($1,$2,600)',[id(208),id(204)])
 await db.query("insert into cp7_credit.component_journals(part_id,journal_id,economic_date,transaction_date)values($1,$2,'2026-10-02','2026-10-02')",[id(208),id(206)])
 await db.exec(`create or replace function cp7_credit.source_native_snapshot_v1(p_sale uuid)returns jsonb language sql stable as $$
 select coalesce((select snapshot from public.cap_source_override),jsonb_build_object('declared_cap_source_double',true,
 'sale',(select to_jsonb(h)from erp.sales_headers h where h.id=p_sale),
 'items',(select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]')from erp.sales_items i where i.sale_id=p_sale),
 'allocations',(select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=p_sale),
 'returns',(select coalesce(jsonb_agg(to_jsonb(h)order by h.id),'[]')from erp.sales_returns h where h.sale_id=p_sale),
 'return_items',(select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]')from erp.sales_return_items i join erp.sales_returns h on h.id=i.return_id where h.sale_id=p_sale)))$$;
 create function erp.require_internal()returns void language plpgsql as $$begin null;end$$;
 create function erp.assert_non_po_product_hpp_target_book_v2620f(uuid)returns void language plpgsql as $$begin null;end$$;
 create function erp.lock_current_hpp_per_pcs(uuid)returns numeric language sql as $$select 10::numeric$$;
 create function erp.post_fg_movement(uuid,uuid,uuid,text,text,integer,numeric,uuid,text,uuid,timestamptz,text,boolean)returns void language plpgsql as $$begin raise exception 'LOCAL_NATIVE_AGGREGATE_PASSED_STOP_BEFORE_STOCK_WRITE';end$$;
 create unique index local_only_native_probe_balance on erp.fg_inventory_balances(product_id,location_id,quality_grade);`)
 const nativeSQL=await readFile(new URL('retained/post_sales_return.sql',import.meta.url),'utf8')
 assert.equal(createHash('sha256').update(nativeSQL).digest('hex'),'5f974ad9b9fff9ec9fef3018153683d35b79a9a5e8bd4c60e9a4a17b97622cdc')
 await db.exec(nativeSQL)
 const proposed=structuredClone(p);proposed.replacement.items[0].refund_amount='400.01'
 const reviewed=await quote(proposed)
 assert.equal(reviewed.state,'READY');assert.deepEqual(reviewed.issues,[])
 let refusal
 await db.exec('begin')
 try{
  await db.query("update erp.sales_returns set status='REVERSED'where id=$1",[ret])
  await db.query("insert into erp.sales_returns(id,sale_id,customer_id,status,physical_at)values($1,$2,$3,'DRAFT','2026-10-02T05:00:00Z')",[draft,sale,customer])
  await db.query("insert into erp.sales_return_items(id,return_id,sale_stock_allocation_id,location_id,qty_pcs,quality_grade,refund_amount)values($1,$2,$3,$4,2,'GRADE_A',400.01)",[id(301),draft,allocation,location])
  await db.query('select erp.post_sales_return($1)',[draft])
 }catch(e){refusal={sqlstate:e.code,message:e.message,where:e.where}}
 finally{await db.exec('rollback')}
 assert.equal(refusal?.sqlstate,'P0001');assert.match(refusal.message,/Refund exceeds original net sale value for product/)
 console.log(JSON.stringify({status:'CONFIRMED_LOCAL_QUOTE_READY_NATIVE_AGGREGATE_REFUSAL',classification:'LOCAL_SQL_ACTUAL_QUOTE_KERNEL_AND_UNCHANGED_NATIVE_PREDICATE_WITH_STRUCTURAL_SOURCE_AUTH_HPP_DOUBLES',reviewed,refusal,math:{productA_sale:'1000.00',peerPOSTED:'600.00',replacement:'400.01',perLineMax:'400.00',lineTolerance:'0.01',aggregate:'1000.01',productAggregateTolerance:'0.00',invoiceSale:'2000.00',payment:'2000.00',physicalA:'2 replacement +3 peer =5 sold'},Native_financial_execution:false,actual_Native_cases:0,stock_or_journal_writer_called:false},null,2))
}catch(error){console.error(JSON.stringify({status:'FAIL_LOCAL_REPRO',message:error.message,sqlstate:error.code,where:error.where,stack:error.stack,Native_financial_execution:false},null,2));process.exitCode=1}finally{await db.close()}
