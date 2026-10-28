// Focused SQL execution against PGlite + explicit Native test doubles.
// Not a real Auth/Native/concurrency/installation qualification.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { randomUUID } from 'node:crypto'
import { execFileSync } from 'node:child_process'
const { PGlite } = await import(process.env.CP7_SQL_TEST_PGLITE_URL || '@electric-sql/pglite')
const here = new URL('.', import.meta.url), repo = fileURLToPath(new URL('../../', here))
const source = name => readFileSync(new URL(name, here), 'utf8')
const derived = JSON.parse(execFileSync('python3', ['-B', '-c',
 `import json,sys;sys.path.insert(0,'scripts');from cp7_vendor_receivable.test_derivation import originals;from cp7_vendor_receivable.native_delta import patched;print(json.dumps(patched(originals())))`], { cwd: repo, encoding: 'utf8' }))
const policy = readFileSync(new URL('../cp6_bd_objects_policy.sql', here), 'utf8')
const credit = readFileSync(new URL('../cp6_bd_objects_claimcredit.sql', here), 'utf8')
const extract = (text, name) => {
 const start = text.indexOf('CREATE OR REPLACE FUNCTION erp.' + name + '(')
 assert.ok(start >= 0, name)
 return text.slice(start, text.indexOf('$function$;', text.indexOf('$function$', start) + 10) + 11)
}
const db = new PGlite()
await db.exec(source('local_fixture.sql'))
await db.exec(extract(policy, 'bd_amount_v1') + extract(policy, 'bd_uuid_v1'))
await db.exec(source('receivable.sql'))
await db.exec(derived['erp.bd_claim_credit_applied_v1(text,uuid)'])
await db.exec(extract(credit, 'bd_vendor_invoice_paid_v1'))
await db.exec(derived['erp.bd_apply_vendor_credit_v1(text,uuid,text,uuid,numeric,date,text,uuid)'])
await db.exec(derived['erp.save_laundry_bd_action_v1(text,jsonb,uuid)'])
const q = async (sql, params = []) => (await db.query(sql, params)).rows
const one = async (sql, params = []) => Object.values((await q(sql, params))[0])[0]
const vendor = randomUUID(), ar = randomUUID(), cash = randomUUID(), cashCoa = randomUUID(), ap = randomUUID(), cost = randomUUID(), actor = randomUUID()
await q(`select set_config('app.actor',$1,false),set_config('app.allowed','true',false)`, [actor])
for (const [id, code] of [[ar, 'ARV'], [cashCoa, 'BANK'], [ap, 'AP'], [cost, 'COST']]) {
 await q(`insert into erp.chart_accounts(id,account_code,account_name,account_type,normal_balance)values($1,$2,$2,'ASSET','DEBIT')`, [id, code])
}
await q(`insert into erp.cash_accounts values($1,$2,'BANK','Bank',true)`, [cash, cashCoa])
await q(`insert into erp.accounting_account_mappings values('AP_VENDOR',$1),('WIP',$2)`, [ap, cost])
const createSource = async amount => {
 const id = randomUUID()
 await q(`insert into erp.bd_laundry_invoices_v1 values($1,$2,'DRAFT',-$3::numeric,$4,current_date-5,$5,null,null)`, [id, vendor, amount, randomUUID(), 'COR-' + id])
 const line = await one(`select cp7_vendor_receivable.register_v1($1,$2)`, [id, ar])
 const jid = await one(`select erp.post_journal('BD_LAUNDRY_CORRECTION_CREDIT',$1,current_date-5,'fixture',$2)`, [id, JSON.stringify([line, { account_id: cost, debit: 0, credit: amount, vendor_id: vendor }])])
 await q(`update erp.bd_laundry_invoices_v1 set status='POSTED',journal_id=$2 where id=$1`, [id, jid])
 return id
}
const date = await one(`select current_date::text`)
const refundPayload = (id, amount = '20.00') => ({ source_id: id, amount, date, cash_account_id: cash, reason: 'Vendor mengembalikan ke bank' })
const command = (action, payload, id = randomUUID()) => one(`select erp.save_laundry_bd_action_v1($1,$2,$3)`, [action, JSON.stringify(payload), id])
const consumed = id => one(`select erp.bd_claim_credit_applied_v1('INVOICE_CORRECTION',$1)::text`, [id])
const isolated = async fn => { await db.exec('begin'); try { await fn() } finally { await db.exec('rollback') } }
const refused = async (fn, pattern) => {
 await db.exec('savepoint expected_refusal')
 try { await assert.rejects(fn(), pattern) } finally { await db.exec('rollback to expected_refusal;release expected_refusal') }
}

await test('local SQL contract with Native test doubles', async t => {
 await t.test('dedicated AR required; mapped and cash accounts refused', () => isolated(async () => {
  assert.equal(await one('select cp7_vendor_receivable.eligible_v1($1)', [ar]), true)
  assert.equal(await one('select cp7_vendor_receivable.eligible_v1($1)', [cashCoa]), false)
  assert.equal(await one('select cp7_vendor_receivable.eligible_v1($1)', [ap]), false)
 }))
 await t.test('refund enters cash and consumes credit once; same UUID replays', () => isolated(async () => {
  const id = await createSource('100.01'), key = randomUUID(), payload = refundPayload(id, '20.01')
  const first = await command('RECEIVE_VENDOR_REFUND', payload, key)
  assert.equal(first.remaining, '80.00')
  assert.equal((await command('RECEIVE_VENDOR_REFUND', payload, key)).replayed, true)
  assert.equal(await consumed(id), '20.01')
  assert.equal(await one('select count(*)::integer from cp7_vendor_receivable.refunds_v1'), 1)
  assert.equal(await one('select sum(debit-credit)::text from erp.journal_lines where account_id=$1', [cashCoa]), '20.01')
 }))
 await t.test('real BD application code uses AR credit and reduces available refund', () => isolated(async () => {
  const id = await createSource('100.00'), invoice = randomUUID(), key = randomUUID()
  await q(`insert into erp.vendor_invoices values($1,$2,'POSTED',60,current_date-1,'NEXT',now())`, [invoice, vendor])
  await one(`select erp.bd_apply_vendor_credit_v1('INVOICE_CORRECTION',$1,'VENDOR_INVOICE',$2,60,current_date,'tagihan berikut',$3)`, [id, invoice, key])
  assert.equal(await consumed(id), '60.00')
  assert.equal(await one(`select sum(credit-debit)::text from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.source_id=$1 and l.account_id=$2`, [key, ar]), '60.00')
  assert.equal((await command('RECEIVE_VENDOR_REFUND', refundPayload(id, '40.00'))).remaining, '0.00')
 }))
 await t.test('refund inverse returns source balance with retained original receipt', () => isolated(async () => {
  const id = await createSource('100.00'), refund = await command('RECEIVE_VENDOR_REFUND', refundPayload(id))
  await command('REVERSE_VENDOR_REFUND', { refund_id: refund.refund_id, reason: 'Pembatalan bukti salah rekening' })
  assert.equal(await consumed(id), '0.00')
  assert.equal(await one('select count(*)::integer from cp7_vendor_receivable.refunds_v1'), 1)
  assert.equal(await one('select count(*)::integer from cp7_vendor_receivable.reversals_v1'), 1)
 }))
 await t.test('permission revoked before replay refuses cached financial response', () => isolated(async () => {
  const id = await createSource('100.00'), key = randomUUID(), payload = refundPayload(id)
  await command('RECEIVE_VENDOR_REFUND', payload, key)
  await q(`select set_config('app.allowed','false',true)`)
  await assert.rejects(command('RECEIVE_VENDOR_REFUND', payload, key), /TEST_ACCESS_DENIED/)
 }))
 await t.test('refund over source balance and malformed money are refused', () => isolated(async () => {
  const id = await createSource('10.00')
  await refused(() => command('RECEIVE_VENDOR_REFUND', refundPayload(id, '10.01')), /EXCEEDS_AVAILABLE/)
  await refused(() => command('RECEIVE_VENDOR_REFUND', refundPayload(id, '1.001')), /BD_AMOUNT_INVALID/)
  await refused(() => command('RECEIVE_VENDOR_REFUND', { ...refundPayload(id), amount: 1 }), /BD_AMOUNT_INVALID/)
  assert.equal(await consumed(id), '0.00')
  assert.equal(await one('select count(*)::integer from cp7_vendor_receivable.refunds_v1'), 0)
 }))
 await t.test('changed payload cannot reuse UUID; original record stays immutable', () => isolated(async () => {
  const id = await createSource('100.00'), key = randomUUID(), payload = refundPayload(id)
  await command('RECEIVE_VENDOR_REFUND', payload, key)
  await refused(() => command('RECEIVE_VENDOR_REFUND', { ...payload, amount: '21.00' }, key), /BD_REQUEST_REUSED/)
  await refused(() => q('update cp7_vendor_receivable.refunds_v1 set amount=1 where id=$1', [key]), /APPEND_ONLY/)
  assert.equal(await consumed(id), '20.00')
 }))
 await t.test('refund date cannot precede correction; dated AR floor rejects earlier depletion', () => isolated(async () => {
  const id = await createSource('100.00')
  await refused(() => command('RECEIVE_VENDOR_REFUND', { ...refundPayload(id), date: '2000-01-01' }), /BEFORE_APPROVAL/)
  const sourceJournal = await one('select journal_id from erp.bd_laundry_invoices_v1 where id=$1', [id])
  await q(`update erp.journal_entries set transaction_date=current_date+1 where id=$1`, [sourceJournal])
  await refused(() => command('RECEIVE_VENDOR_REFUND', refundPayload(id)), /NEGATIVE_DATED/)
 }))
 await t.test('unrelated offsetting journal lines cannot hide behind equal AR totals', () => isolated(async () => {
  await createSource('100.00')
  const id = randomUUID()
  await q(`insert into erp.journal_entries values($1,'UNLINKED',$2,'POSTED',current_date,current_date,null)`, [id, randomUUID()])
  await q(`insert into erp.journal_lines(journal_entry_id,account_id,vendor_id,debit,credit)values($1,$2,$3,1,0),($1,$2,$3,0,1)`, [id, ar, vendor])
  await assert.rejects(one('select cp7_vendor_receivable.prove_v1($1)', [vendor]), /MATERIALIZATION_UNPROVEN/)
 }))
})
await db.close()
