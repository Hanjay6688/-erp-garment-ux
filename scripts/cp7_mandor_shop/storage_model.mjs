// Isolated PostgreSQL/WASM storage controls, not an ERP/Auth/payment test.
// Only the referenced Native column types are modeled. No Native body runs.
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const [runtime, nativeInputPath, output] = process.argv.slice(2);
assert(runtime && nativeInputPath && output, 'Explicit isolated runtime, Native input proof, and output required');
const { PGlite } = await import(pathToFileURL(runtime).href);
const here = fileURLToPath(new URL('.', import.meta.url));
const sha = value => createHash('sha256').update(value).digest('hex');
const inputRaw = await readFile(nativeInputPath);
const input = JSON.parse(inputRaw);
for (const table of ['erp.contractors','erp.customers','erp.sales_headers','erp.payroll_settlements','erp.payroll_deductions','erp.journal_entries']) {
  assert.equal(input.columns[table][table + ':id'][2], 'uuid');
}
const id = n => '00000000-0000-4000-8000-' + String(n).padStart(12, '0');
const actor = id(9001), contractorA = id(1), contractorB = id(2);
const customerA = id(101), customerB = id(102), saleA = id(201), saleB = id(202);
const payrollA = id(301), payrollB = id(302), allocationA = id(501), allocationB = id(502);
const event1 = id(601), event2 = id(602), event3 = id(603), event4 = id(604), event5 = id(605);
const journal1 = id(701), journal2 = id(702), journal3 = id(703), journal4 = id(704);
const settlement1 = id(801), settlement2 = id(802), reversal1 = id(901), reversal2 = id(902);
const results = [];
let request = 10000;
const db = new PGlite();
async function within(action, body) {
  const req = id(++request);
  await db.exec('BEGIN');
  try {
    await db.query("SELECT set_config('cp7_model.actor',$1,true)", [actor]);
    await db.query("INSERT INTO cp7_mandor_shop.requests(actor,request_id,action,payload,payload_sha256,response) VALUES($1,$2,$3,'{}',$4,'{}')", [actor,req,action,'a'.repeat(64)]);
    await db.query('INSERT INTO cp7_mandor_shop.command_context VALUES(pg_backend_pid(),txid_current(),$1,$2,$3,$4)', [actor,req,action,'a'.repeat(64)]);
    const value = await body(req);
    await db.exec('DELETE FROM cp7_mandor_shop.command_context WHERE backend_pid=pg_backend_pid() AND transaction_id=txid_current()');
    await db.exec('COMMIT');
    return value;
  } catch (error) {
    await db.exec('ROLLBACK');
    throw error;
  }
}
async function rejected(label, action, body, code, messagePart) {
  let error;
  try { await within(action, body); } catch (caught) { error = caught; }
  assert(error, label + ': rejection required');
  assert.equal(error.code, code, label + ': SQLSTATE');
  if (messagePart) assert(error.message.includes(messagePart), label + ': exact rejection');
  results.push({ label, result:'REFUSED_AS_REQUIRED', SQLSTATE:error.code });
}
async function state(allocation, expected, ordinal) {
  const row = (await db.query('SELECT state,last_ordinal FROM cp7_mandor_shop.allocation_states WHERE allocation_id=$1', [allocation])).rows[0];
  assert.deepEqual(row, {state:expected,last_ordinal:ordinal});
}
async function append(req, event, allocation, ordinal, predecessor, kind, settlement = null, reversal = null) {
  await db.query('INSERT INTO cp7_mandor_shop.allocation_events(id,allocation_id,ordinal,predecessor_id,kind,settlement_id,reversal_id,actor,request_id) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)', [event,allocation,ordinal,predecessor,kind,settlement,reversal,actor,req]);
}
try {
  await db.exec(`
    CREATE ROLE anon; CREATE ROLE authenticated; CREATE ROLE service_role;
    CREATE SCHEMA erp; CREATE SCHEMA auth;
    CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$
      SELECT nullif(current_setting('cp7_model.actor',true),'')::uuid
    $$;
    CREATE TABLE erp.contractors(id uuid PRIMARY KEY,is_active boolean NOT NULL);
    CREATE TABLE erp.customers(id uuid PRIMARY KEY,is_active boolean NOT NULL);
    CREATE TABLE erp.sales_headers(id uuid PRIMARY KEY,customer_id uuid NOT NULL,status varchar(30) NOT NULL);
    CREATE TABLE erp.payroll_settlements(id uuid PRIMARY KEY,contractor_id uuid NOT NULL,status varchar(30) NOT NULL);
    CREATE TABLE erp.payroll_deductions(id uuid PRIMARY KEY,payroll_id uuid NOT NULL,deduction_type varchar(30) NOT NULL,amount numeric(20,2) NOT NULL,contractor_issue_item_id uuid,bs_resolution_id uuid,opening_cash_advance_balance_id uuid);
    CREATE TABLE erp.journal_entries(id uuid PRIMARY KEY,source_type varchar(100),source_id uuid,status varchar(30),economic_date date,transaction_date date,reversal_of_id uuid);
    INSERT INTO erp.contractors VALUES('${contractorA}',true),('${contractorB}',true);
    INSERT INTO erp.customers VALUES('${customerA}',true),('${customerB}',true);
    INSERT INTO erp.sales_headers VALUES('${saleA}','${customerA}','POSTED'),('${saleB}','${customerB}','POSTED');
    INSERT INTO erp.payroll_settlements VALUES('${payrollA}','${contractorA}','DRAFT'),('${payrollB}','${contractorB}','DRAFT');
  `);
  const schema = await readFile(here + 'schema.sql');
  const events = await readFile(here + 'events.sql');
  await db.exec(schema.toString());
  await db.exec(events.toString());
  await db.query('INSERT INTO cp7_mandor_shop.contractor_accounts(contractor_id,customer_id,created_by) VALUES($1,$2,$5),($3,$4,$5)', [contractorA,customerA,contractorB,customerB,actor]);
  await within('POST_SALE', async () => {
    await db.query("INSERT INTO cp7_mandor_shop.sales(sale_id,contractor_id,customer_id,contractor_name_at_post,posted_by) VALUES($1,$2,$3,'A',$7),($4,$5,$6,'B',$7)", [saleA,contractorA,customerA,saleB,contractorB,customerB,actor]);
  });
  await within('RESERVE', async () => {
    await db.query('INSERT INTO cp7_mandor_shop.payroll_identities(payroll_id,contractor_id,created_by) VALUES($1,$2,$5),($3,$4,$5)', [payrollA,contractorA,payrollB,contractorB,actor]);
  });
  await rejected('Wrong mandor across invoice and selected payroll', 'RESERVE', req => db.query('INSERT INTO cp7_mandor_shop.allocations VALUES($1,$2,$3,$4,300000,$5,$6,statement_timestamp())', [id(599),saleA,payrollB,contractorA,actor,req]), '23503');
  await rejected('Fractional cents are rejected before storage rounding', 'RESERVE', req => db.query('INSERT INTO cp7_mandor_shop.allocations VALUES($1,$2,$3,$4,1.005,$5,$6,statement_timestamp())', [id(598),saleA,payrollA,contractorA,actor,req]), '23514');
  await within('RESERVE', async req => {
    await db.query('INSERT INTO cp7_mandor_shop.allocations VALUES($1,$2,$3,$4,300000,$5,$6,statement_timestamp())', [allocationA,saleA,payrollA,contractorA,actor,req]);
    await append(req,event1,allocationA,1,null,'RESERVE');
  });
  await state(allocationA,'RESERVED',1);
  results.push({label:'Initial reservation creates exactly one current projection',result:'PASS'});
  await rejected('Duplicate active card for same invoice and payroll', 'RESERVE', async req => {
    await db.query('INSERT INTO cp7_mandor_shop.allocations VALUES($1,$2,$3,$4,1,$5,$6,statement_timestamp())', [id(597),saleA,payrollA,contractorA,actor,req]);
    await append(req,id(699),id(597),1,null,'RESERVE');
  },'23505');
  await rejected('A second initial event cannot restart the same allocation', 'RESERVE', req => append(req,id(698),allocationA,1,null,'RESERVE'),'23505');
  await rejected('Fact amount cannot be edited', 'RESERVE', () => db.query('UPDATE cp7_mandor_shop.allocations SET amount=1 WHERE id=$1',[allocationA]), 'P0001','IMMUTABLE');
  await rejected('Native deduction amount must equal its immutable allocation', 'RESERVE', async () => {
    await db.query("INSERT INTO erp.payroll_deductions(id,payroll_id,deduction_type,amount) VALUES($1,$2,'OTHER',299999)",[id(999),payrollA]);
    await db.query('INSERT INTO cp7_mandor_shop.deduction_links VALUES($1,$2,$3,$4,299999,$5)',[allocationA,saleA,payrollA,contractorA,id(999)]);
  },'23503');
  await rejected('A stale predecessor cannot release a current reservation', 'RELEASE', req => append(req,id(697),allocationA,2,null,'RELEASE'),'23514');
  await db.query("UPDATE erp.payroll_settlements SET status='PAID' WHERE id=$1",[payrollA]);
  await db.query("INSERT INTO erp.journal_entries VALUES($1,'FG_MANDOR_PAYROLL_OFFSET',$2,'POSTED','2026-11-02','2026-11-02',NULL)",[journal1,settlement1]);
  await within('SETTLE',async req => {
    await db.query("INSERT INTO cp7_mandor_shop.settlements(id,payroll_id,contractor_id,journal_id,total_amount,economic_date,book_date,actor,request_id) VALUES($1,$2,$3,$4,300000,'2026-11-02','2026-11-02',$5,$6)",[settlement1,payrollA,contractorA,journal1,actor,req]);
    await db.query('INSERT INTO cp7_mandor_shop.settlement_lines VALUES($1,$2,$3,$4,$5,300000)',[settlement1,allocationA,saleA,payrollA,contractorA]);
    await append(req,event2,allocationA,2,event1,'SETTLE',settlement1);
  });
  await state(allocationA,'SETTLED',2);
  results.push({label:'One exact linked settlement advances the reservation',result:'PASS'});
  await rejected('A paid allocation cannot settle twice', 'SETTLE', req => append(req,id(696),allocationA,3,event2,'SETTLE',settlement1),'P0001','SETTLE_EXACT_RESERVED_LINE_ONLY');
  await rejected('A paid allocation cannot be released without reversal', 'RELEASE', req => append(req,id(695),allocationA,3,event2,'RELEASE'),'P0001','RELEASE_RESERVED_ONLY');
  await db.query("UPDATE erp.journal_entries SET status='REVERSED' WHERE id=$1",[journal1]);
  await db.query("INSERT INTO erp.journal_entries VALUES($1,'REVERSAL',$2,'POSTED','2026-11-02','2026-11-02',$3)",[journal2,reversal1,journal1]);
  await within('REOPEN',async req => {
    await db.query("INSERT INTO cp7_mandor_shop.settlement_reversals(id,settlement_id,reversal_journal_id,reason,actor,request_id) VALUES($1,$2,$3,'model only',$4,$5)",[reversal1,settlement1,journal2,actor,req]);
    await append(req,event3,allocationA,3,event2,'REOPEN',settlement1,reversal1);
  });
  await state(allocationA,'RESERVED',3);
  results.push({label:'Linked reversal and reopening retains the reservation',result:'PASS'});
  await db.query("INSERT INTO erp.journal_entries VALUES($1,'FG_MANDOR_PAYROLL_OFFSET',$2,'POSTED','2026-11-02','2026-11-02',NULL)",[journal3,settlement2]);
  await within('SETTLE',async req => {
    await db.query("INSERT INTO cp7_mandor_shop.settlements(id,payroll_id,contractor_id,journal_id,total_amount,economic_date,book_date,actor,request_id) VALUES($1,$2,$3,$4,300000,'2026-11-02','2026-11-02',$5,$6)",[settlement2,payrollA,contractorA,journal3,actor,req]);
    await db.query('INSERT INTO cp7_mandor_shop.settlement_lines VALUES($1,$2,$3,$4,$5,300000)',[settlement2,allocationA,saleA,payrollA,contractorA]);
    await append(req,event4,allocationA,4,event3,'SETTLE',settlement2);
  });
  await db.query("UPDATE erp.journal_entries SET status='REVERSED' WHERE id=$1",[journal3]);
  await db.query("INSERT INTO erp.journal_entries VALUES($1,'REVERSAL',$2,'POSTED','2026-11-02','2026-11-02',$3)",[journal4,reversal2,journal3]);
  await within('REVERSE',async req => {
    await db.query("INSERT INTO cp7_mandor_shop.settlement_reversals(id,settlement_id,reversal_journal_id,reason,actor,request_id) VALUES($1,$2,$3,'model full reverse',$4,$5)",[reversal2,settlement2,journal4,actor,req]);
    await append(req,event5,allocationA,5,event4,'REVERSE',settlement2,reversal2);
  });
  await state(allocationA,'RELEASED',5);
  results.push({label:'Full settlement reversal releases the reservation',result:'PASS'});
  await within('RESERVE',async req => {
    await db.query('INSERT INTO cp7_mandor_shop.allocations VALUES($1,$2,$3,$4,100000,$5,$6,statement_timestamp())',[allocationB,saleB,payrollB,contractorB,actor,req]);
    await append(req,id(606),allocationB,1,null,'RESERVE');
  });
  await within('CANCEL',req => append(req,id(607),allocationB,2,id(606),'RELEASE'));
  await state(allocationB,'RELEASED',2);
  results.push({label:'Cancellation releases an unpaid reservation through a new event',result:'PASS'});
  let denied;
  await db.exec('SET ROLE authenticated');
  try { await db.query('SELECT * FROM cp7_mandor_shop.allocations'); } catch (error) { denied=error; }
  await db.exec('RESET ROLE');
  assert.equal(denied?.code,'42501');
  results.push({label:'Authenticated browser role cannot read private facts directly',result:'REFUSED_AS_REQUIRED',SQLSTATE:'42501'});
  assert.equal((await db.query('SELECT count(*)::int AS n FROM cp7_mandor_shop.command_context')).rows[0].n,0);
  const version=(await db.query('SELECT version() AS v')).rows[0].v;
  const report={status:'FG_MANDOR_ISOLATED_STORAGE_MODEL_CONTROLS_PASS_NOT_NATIVE',PostgreSQL_model:version,
    source_files:{'schema.sql':{bytes:schema.length,sha256:sha(schema)},'events.sql':{bytes:events.length,sha256:sha(events)}},
    Native_reference_input:{bytes:inputRaw.length,sha256:sha(inputRaw)},results,
    modeled_Native_tables:6,only_referenced_Native_columns_modeled:true,synthetic_fixture_values:true,
    SQL_executed_on_isolated_model:true,actual_ERP_calls:0,actual_Native_cases:0,actual_Auth_HTTP_cases:0,
    actual_two_session_races:0,actual_browser_cases:0,public_commands_or_Native_payment_hooks_implemented:false,
    invoice_balance_and_payroll_capacity_and_cash_accounting_not_qualified:true,
    workflow_activated:false,production_go:false,independent_acceptance:false};
  await writeFile(output,JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({status:report.status,storage_controls:results.length,actual_Native_cases:0}));
} finally { await db.close(); }
