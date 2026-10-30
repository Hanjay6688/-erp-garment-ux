/** Typed schema/history sensitivity fixtures, never Native business commands. */
import {uuid} from './model.mjs';
export async function mixedJournal(db,{product=21,reversal=false,sourceType='LOCAL_STRUCTURAL_MIXED',sourceId=null}={}){
 await db.exec(`insert into erp.journal_entries(id,status,source_type,source_id)values('${uuid(610)}','POSTED','${sourceType}',${sourceId?`'${uuid(sourceId)}'`:'null'});
 insert into erp.journal_lines(id,journal_entry_id,account_id,debit,credit,product_id)values
 ('${uuid(710)}','${uuid(610)}','${uuid(501)}',0,1,null),
 ('${uuid(711)}','${uuid(610)}','${uuid(501)}',1,0,${product?`'${uuid(product)}'`:'null'});`);
 if(reversal)await db.exec(`update erp.journal_lines set product_id=null where journal_entry_id='${uuid(610)}';
  insert into erp.journal_entries(id,status,source_type,reversal_of_id)values('${uuid(611)}','POSTED','JOURNAL_REVERSAL','${uuid(610)}');
  insert into erp.journal_lines(id,journal_entry_id,account_id,debit,credit,product_id)values
  ('${uuid(712)}','${uuid(611)}','${uuid(501)}',1,0,'${uuid(21)}'),('${uuid(713)}','${uuid(611)}','${uuid(501)}',0,1,null)`);
}
export async function cost(db,{product=21,reversal=false}={}){
 await mixedJournal(db,{product,reversal});
 await db.exec(`insert into erp.bc_documents_v1(id,status)values('${uuid(901)}','POSTED');
  insert into erp.material_adjustments(id,amount)values('${uuid(902)}',0);
  insert into erp.be_conversion_cost_sources_v1(document_id,conversion_id,kind)values('${uuid(901)}','${uuid(201)}','USAGE');
  insert into erp.be_conversion_cost_events_v1(id,document_id,adjustment_id,previous_amount,target_amount,journal_id,economic_date)
  values('${uuid(903)}','${uuid(901)}','${uuid(902)}',1,1,'${uuid(610)}','2026-10-20');`);
}
export async function secondConversion(db){
 await db.exec(`insert into erp.product_conversions(id,from_product_id,to_product_id,status,physical_at,qty_pcs)
  values('${uuid(202)}','${uuid(21)}','${uuid(24)}','REVERSED','2026-10-20T03:00Z',1)`);
}
export async function returns(db,{sharedDocument=true}={}){
 await secondConversion(db);
 await db.exec(`insert into erp.bc_documents_v1(id,status)values('${uuid(901)}','POSTED'),('${uuid(904)}','POSTED');
  insert into erp.bc_outstanding_returns_v1(id,status,qty_expected)values('${uuid(906)}','OPEN',5),('${uuid(907)}','OPEN',5);
  insert into erp.be_conversion_returns_v1(outstanding_id,conversion_id,line_no)values('${uuid(906)}','${uuid(201)}',1),('${uuid(907)}','${uuid(202)}',1);
  insert into erp.bc_return_lots_v1(id,outstanding_id,document_id,qty_received,value_mode)values
  ('${uuid(908)}','${uuid(906)}','${uuid(901)}',1,'PENDING'),
  ('${uuid(909)}','${uuid(907)}','${uuid(sharedDocument?901:904)}',1,'PENDING');`);
}
export async function rich(db){
 await cost(db);
 await db.exec(`insert into erp.be_nonpo_transfer_events_v1(id,conversion_id,previous_value,target_value,journal_id,economic_date)
  values('${uuid(920)}','${uuid(201)}',20,20,'${uuid(610)}','2026-10-20');
  insert into erp.bc_documents_v1(id,status)values('${uuid(904)}','REVERSED');
  insert into erp.bc_document_links_v1 values('${uuid(901)}','JOURNAL','${uuid(610)}'),('${uuid(904)}','TRANSFER','${uuid(990)}');
  insert into erp.bc_adjustment_purposes_v1 values('${uuid(902)}','${uuid(901)}','FACTORY_USE','${uuid(501)}','LOCAL_POLICY',1);
  insert into erp.bc_outstanding_returns_v1(id,status,qty_expected,document_id)values('${uuid(906)}','OPEN',5,'${uuid(901)}');
  insert into erp.be_conversion_returns_v1 values('${uuid(906)}','${uuid(201)}',1);
  insert into erp.bc_return_lots_v1(id,outstanding_id,document_id,qty_received,value_mode)values('${uuid(908)}','${uuid(906)}','${uuid(901)}',1,'PENDING');
  insert into erp.bc_lot_events_v1(id,document_id,lot_id,event_kind,qty,qty_usable,qty_damaged)
  values('${uuid(910)}','${uuid(904)}','${uuid(908)}','VALUE',1,0,0);
  insert into erp.non_po_hpp_gl_sync_events_v2620f(id,product_id,journal_entry_id)values('${uuid(930)}','${uuid(23)}','${uuid(610)}');`);
}
