import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import { financialRecoveryBlocked, useFinancialRecoveryGate } from './useFinancialRecoveryGate'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import MandorShopCards from './MandorShopCards'
import { parseMandorShopAllocationOutcome, parseMandorShopWorkspace, type MandorShopAction, type MandorShopAllocation, type MandorShopCard, type MandorShopWorkspace } from './mandorShopContract'
import type { Json } from './types/database.preconnect'

type Target = { payroll: string; contractor: string; number: string; name: string }
type Intent = { document: { [key: string]: Json | undefined }; target: Target }
type Props = {
  payrollId: string | null; contractorId: string | null; payrollNumber: string; contractorName: string
  parentReady: boolean; readRevision: number; onReload: () => Promise<boolean>
  onTarget: (payroll: string) => void; onRetire: () => void
}
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
function intent(value: Json): Intent {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Catatan pemasangan tagihan perlu diperiksa.')
  const d = value.document, t = value.target
  if (!d || typeof d !== 'object' || Array.isArray(d) || !t || typeof t !== 'object' || Array.isArray(t)
    || typeof d.payroll_id !== 'string' || !uuid.test(d.payroll_id) || typeof d.sale_id !== 'string' || !uuid.test(d.sale_id)
    || t.payroll !== d.payroll_id || typeof t.contractor !== 'string' || !uuid.test(t.contractor)
    || typeof t.number !== 'string' || typeof t.name !== 'string') throw Error('Catatan pemasangan tagihan perlu diperiksa.')
  return { document: d, target: { payroll: d.payroll_id, contractor: t.contractor, number: t.number, name: t.name } }
}
function action(value: string): MandorShopAction {
  if (value !== 'RESERVE' && value !== 'RELEASE') throw Error('Tindakan tagihan tidak dikenal. Catatan lama tetap disimpan.')
  return value
}
function message(failure: unknown): string {
  const raw = normalizeClientError(failure).message
  if (/CP7_MANDOR_SHOP_(REVIEW_CHANGED|SOURCE_BUSY_REVIEW_AGAIN|REQUEST_BUSY)/i.test(raw)) return 'Tagihan, alokasi, atau payroll berubah atau sedang diproses. Muat ulang lalu periksa lagi.'
  if (/CP7_MANDOR_SHOP_INVOICE_CAPACITY_CHANGED/i.test(raw)) return 'Nominal melebihi sisa tagihan yang belum dipasang. Muat ulang tagihan.'
  if (/CP7_MANDOR_SHOP_PAYROLL_CAPACITY_CHANGED/i.test(raw)) return 'Nominal melebihi kapasitas payroll saat ini. Muat ulang payroll.'
  if (/CP7_MANDOR_SHOP_WRONG_MANDOR/i.test(raw)) return 'Nota bukan milik mandor pada payroll ini. Muat ulang dan pilih nota yang benar.'
  if (/CP7_MANDOR_SHOP_(ACCESS_DENIED|ACCESS_CHANGED)/i.test(raw)) return 'Hak akses berubah. Periksa sesi dan muat ulang sumber.'
  return raw
}

export default function MandorShopPayrollPanel(props: Props) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw Error('Sesi payroll belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const mutation = useProductionMutation('MANDOR_SHOP_ALLOCATION'), { beginRead, finishRead, isReadCurrent, invalidate, run, reconcile } = mutation
  const [open, setOpen] = useState(false), [data, setData] = useState<MandorShopWorkspace | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const seq = useRef(0), cursor = useRef<string | null>(null), wanted = useRef<Target | null>(null)
  const latestRead = useRef<Promise<boolean>>(Promise.resolve(false))
  const view = identity.permissions.includes('finance.payroll.view') && identity.permissions.includes('finance.ar.view')
  const approve = identity.permissions.includes('finance.payroll.approve')
  if (props.payrollId && props.contractorId) wanted.current = { payroll: props.payrollId, contractor: props.contractorId, number: props.payrollNumber, name: props.contractorName }
  const retire = useCallback(() => { ++seq.current; setData(null); setBusy(false) }, [])
  const blocked = useFinancialRecoveryGate(mutation.scope, retire)
  const read = useCallback(async () => {
    retire(); setError('')
    const target = wanted.current, after = cursor.current
    if (!target || !view || financialRecoveryBlocked(mutation.scope)) return false
    const generation = ++seq.current, ticket = beginRead(); setBusy(true)
    try {
      const result = await client.rpc('erp_cp7_get_mandor_shop_payroll_v1', { p_payroll: target.payroll, p_after: after })
      if (generation !== seq.current || !isReadCurrent(ticket) || financialRecoveryBlocked(mutation.scope)) return false
      if (result.error) throw result.error
      const next = parseMandorShopWorkspace(result.data, target.payroll, target.contractor)
      if (next.can_change !== (approve && ['DRAFT', 'CALCULATED', 'REVIEW'].includes(next.status))) throw Error('Hak mengubah potongan berubah. Muat ulang payroll.')
      if (!finishRead(ticket)) return false
      setData(next); return true
    } catch (failure) {
      if (generation === seq.current && isReadCurrent(ticket)) setError(message(failure))
      return false
    } finally { if (generation === seq.current) setBusy(false) }
  }, [approve, beginRead, client, finishRead, isReadCurrent, mutation.scope, retire, view])
  const load = useCallback(() => { const pending = read(); latestRead.current = pending; return pending }, [read])
  useEffect(() => { setOpen(false); cursor.current = null; retire(); invalidate() }, [props.payrollId, retire, invalidate])
  useEffect(() => {
    if (open && props.parentReady && props.payrollId && props.contractorId) void load()
    else { retire(); invalidate() }
    return () => { ++seq.current }
  }, [load, open, props.parentReady, props.payrollId, props.contractorId, props.readRevision, retire, invalidate])
  const handlers: ProductionMutationHandlers = {
    send: envelope => { const old = intent(envelope.payload); return client.rpc('erp_cp7_save_mandor_shop_allocation_v1', {
      p_action: action(envelope.action), p_payload: old.document, p_request: envelope.id,
    }) },
    validate: (value, envelope) => { const old = intent(envelope.payload)
      parseMandorShopAllocationOutcome(value, envelope.id, action(envelope.action), String(old.document.payroll_id), String(old.document.sale_id)) },
    retire: (_value, envelope) => {
      const old = intent(envelope.payload); wanted.current = old.target; cursor.current = null
      retire(); props.onTarget(old.target.payroll); props.onRetire()
    },
    reload: async () => {
      const before = latestRead.current
      if (!await props.onReload()) { retire(); invalidate(); return false }
      let current = latestRead.current !== before ? latestRead.current : load(), ok = await current
      while (!ok && latestRead.current !== current) { current = latestRead.current; ok = await current }
      return ok
    },
  }
  const write = async (kind: MandorShopAction, card: MandorShopCard, value: string | MandorShopAllocation) => {
    if (!data || mutation.writerLocked || !props.parentReady || !data.can_change || data.payroll_id !== props.payrollId
      || data.contractor_id !== props.contractorId || !data.cards.some(c => c.sale_id === card.sale_id && c.review_token === card.review_token)) return false
    const document: Json = { contract_version: 'cp7.mandor-shop-allocation-command.v1', payroll_id: data.payroll_id,
      sale_id: card.sale_id, review_token: card.review_token, ...(kind === 'RESERVE' ? { amount: String(value) } : { allocation_id: (value as MandorShopAllocation).id }) }
    const target: Target = { payroll: data.payroll_id, contractor: data.contractor_id, number: props.payrollNumber, name: props.contractorName }
    retire()
    return run(kind, { document, target }, null, handlers)
  }
  const visible = props.parentReady && !blocked && !mutation.workspaceStale && data?.payroll_id === props.payrollId && data.contractor_id === props.contractorId ? data : null
  if (!view && !mutation.pending && !mutation.corruptedEnvelope) return null
  return <section className="panel cpay-detail" aria-label="Tagihan belanja mandor">
    <header className="cpay-actions"><h2>Tagihan belanja mandor</h2><button type="button" disabled={!view || !props.parentReady || !props.payrollId || !props.contractorId || busy || mutation.busy || blocked}
      onClick={() => { cursor.current = null; setOpen(true) }}>Pasang tagihan belanja</button></header>
    <ProductionRecoveryNotice recovery={mutation} className="cpay-action" onReconcile={() => reconcile(handlers)}
      messageText={mutation.pending && !mutation.corruptedEnvelope ? 'Status pemasangan tagihan belum pasti. Periksa permintaan yang sama sebelum tindakan baru.' : mutation.error ? message({ message: mutation.error }) : undefined}
      noticeText="Pilihan tagihan tersimpan. Payroll dan saldo tagihan terbaru sudah dimuat." reconcileLabel="Periksa status pemasangan tagihan"/>
    <MandorShopCards open={open} payrollId={props.payrollId ?? ''} payrollNumber={props.payrollNumber} contractorId={props.contractorId ?? ''} contractorName={props.contractorName}
      workspace={visible} ready={Boolean(visible)} busy={busy || mutation.busy} writeLocked={mutation.writerLocked} error={error}
      onClose={() => setOpen(false)} onReload={async () => { cursor.current = null; return handlers.reload() }}
      onNext={async after => { cursor.current = after; return load() }}
      onReserve={(card, amount) => write('RESERVE', card, amount)} onRelease={(card, allocation) => write('RELEASE', card, allocation)}/>
  </section>
}
