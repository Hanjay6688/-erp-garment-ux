import { describe, expect, it } from 'vitest'
import { pickupFixture } from '../tests/fixtures/productionRecovery'
import { parsePickupQueue } from './cuttingPersistence'
import { cuttingSourceRow } from './cuttingSource'
import { parseTransactionSource, type TransactionDocument } from './transactionSource'

const group = '11111111-1111-4111-8111-111111111111', po = '22222222-2222-4222-8222-222222222222'
const actor = '33333333-3333-4333-8333-333333333333'
const doc = (): TransactionDocument => ({domain:'CUTTING',route:'mandor-wip',id:group,number:'CUT-EXACT',status:'CUT',revision:'2',focus:{kind:'CUTTING_GROUP',id:group,parent_id:po,page_offset:100}})
const queue = () => {
  const q = pickupFixture()
  q.filter = 'ALL'; q.offset = 100; q.total = 102
  q.rows[0].cutting_group_id = group; q.rows[0].po_id = po; q.rows[0].group_number = 'CUT-EXACT'
  return parsePickupQueue(q)
}
const envelope = () => ({contract_version:'cp7.transaction-source.v1',actor_scope_id:actor,source:{source_type:'CUTTING_GROUP',source_id:group},status:'AVAILABLE',document:doc(),read_at:'2026-10-03T04:00:00.123456Z',business_DML:false})

describe('posted cutting source keeps the Native group, PO and exact page', () => {
  it('opens the target on page 100 instead of the first adjacent group', () => {
    const q = queue(), adjacent = {...q.rows[0],cutting_group_id:actor,group_number:'OTHER'}
    q.rows.unshift(adjacent)
    expect(cuttingSourceRow(q,doc()).cutting_group_id).toBe(group)
    expect(parseTransactionSource(envelope(),envelope().source,actor).document).toEqual(doc())
  })
  it.each(['missing','po','version','status','page','filter','query'])('refuses %s instead of choosing another row', kind => {
    const q = queue()
    if(kind==='missing')q.rows[0].cutting_group_id=actor
    if(kind==='po')q.rows[0].po_id=actor
    if(kind==='version')q.rows[0].row_version=3
    if(kind==='status')q.rows[0].status='SEWING'
    if(kind==='page')q.offset=0
    if(kind==='filter')q.filter='WAITING'
    if(kind==='query')q.query='CUT'
    expect(()=>cuttingSourceRow(q,doc())).toThrow('Potongan asal berubah')
  })
  it('refuses a lossy Native version rather than claiming it equals the large source version', () => {
    const q=queue(),d=doc();q.rows[0].row_version=9007199254740992;d.revision='9007199254740993'
    expect(()=>cuttingSourceRow(q,d)).toThrow()
  })
  it.each(['parent','id','offset','route','null','extra'])('refuses malformed closed focus: %s', kind => {
    const e=envelope(),focus=e.document.focus as {kind:string;id:string;parent_id:string;page_offset:number;extra?:boolean}
    if(kind==='parent')focus.parent_id='po-number'
    if(kind==='id')focus.id=actor
    if(kind==='offset')focus.page_offset=25
    if(kind==='route')e.document.route='procurement'
    if(kind==='null')e.document.focus=null
    if(kind==='extra')focus.extra=true
    expect(()=>parseTransactionSource(e,e.source,actor)).toThrow()
  })
})
