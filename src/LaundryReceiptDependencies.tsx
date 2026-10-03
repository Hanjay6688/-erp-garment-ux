import { useEffect, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import TransactionSourceLink from './TransactionSourceNavigation'
import { parseTransactionDependencies, type TransactionDependencies } from './transactionDependencies'

export default function LaundryReceiptDependencies({ receiptId, receiptNumber, receiptRevision, current }: {
  receiptId: string; receiptNumber: string; receiptRevision: number; current: boolean
}) {
  const { runtime, identity } = useAuth(), access = identity.status === 'AUTHORIZED' ? identity : null
  const permitted = current && hasPermission(access, 'production.laundry.view') && hasPermission(access, 'production.final_sku.view')
  const scope = JSON.stringify([isConnectedRuntime(runtime) ? runtime.projectRef : null, access?.profile.authUserId,
    access?.profile.id, access?.profile.rowVersion, access?.profile.roleRowVersion, access?.permissions,
    receiptId, receiptNumber, receiptRevision, permitted])
  const active = useRef(scope), serial = useRef(0)
  active.current = scope
  const [capture, setCapture] = useState<{ scope: string; value: TransactionDependencies } | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  useEffect(() => { ++serial.current; setCapture(null); setBusy(false); setError(''); return () => { ++serial.current } }, [scope])
  const value = permitted && capture?.scope === scope ? capture.value : null
  const load = async (offset: number) => {
    if (!permitted || busy || !isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') return
    const ticket = ++serial.current, wanted = scope, source = { source_type: 'LAUNDRY_RECEIPT', source_id: receiptId }
    setCapture(null); setBusy(true); setError('')
    try {
      const r = await getUatSupabaseClient(runtime).rpc('erp_cp7_get_transaction_dependencies_v1', { p_source: source, p_offset: offset })
      if (ticket !== serial.current || active.current !== wanted) return
      if (r.error) throw r.error
      const result = parseTransactionDependencies(r.data, source, identity.profile.authUserId, offset)
      if (result.parent.number !== receiptNumber || result.parent.revision !== String(receiptRevision) || result.parent.status !== 'POSTED') {
        throw Error('Penerimaan berubah sejak halaman dibuka. Muat ulang data Laundry sebelum memeriksa QC terkait.')
      }
      setCapture({ scope: wanted, value: result })
    } catch (failure) {
      if (ticket === serial.current && active.current === wanted) setError(normalizeClientError(failure).message)
    } finally { if (ticket === serial.current && active.current === wanted) setBusy(false) }
  }
  return <section className="clq-dependencies" aria-label={`QC terkait ${receiptNumber}`}>
    <button type="button" disabled={!permitted || busy} onClick={() => void load(0)}>{busy ? 'Memeriksa QC terkait…' : 'Lihat QC terkait'}</button>
    {!hasPermission(access, 'production.final_sku.view') ? <small>Izin lihat QC diperlukan untuk membuka transaksi terkait.</small> : null}
    {error ? <small role="alert">{error}</small> : null}
    {value ? <>
      <p>{value.page.total ? `${value.page.total} QC aktif memakai penerimaan ini.` : 'Tidak ada QC aktif yang memakai penerimaan ini.'}</p>
      <ul>{value.dependencies.map(row => <li key={row.source_id} data-laundry-qc-dependency-id={row.source_id}>
        <strong>{row.number}</strong><TransactionSourceLink sourceType={row.source_type} sourceId={row.source_id} disabled={!permitted || busy} label="Buka QC terkait"/>
      </li>)}</ul>
      {value.page.total > 25 ? <div className="clq-dependency-pages">
        <span>{value.page.offset + 1}–{value.page.offset + value.dependencies.length} dari {value.page.total}</span>
        <button type="button" disabled={!permitted || busy || value.page.offset === 0} onClick={() => void load(Math.max(0, value.page.offset - 25))}>QC sebelumnya</button>
        <button type="button" disabled={!permitted || busy || !value.page.has_more || value.page.offset >= 1000000} onClick={() => void load(value.page.offset + 25)}>QC berikutnya</button>
      </div> : null}
      <small>Periksa QC terkait dahulu, lalu muat ulang Laundry. Penghalang lain tetap diperiksa saat pembatalan penerimaan dikirim.</small>
    </> : null}
  </section>
}
