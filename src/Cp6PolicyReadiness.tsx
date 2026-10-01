import { POLICY_EFFECT, policyStatus, type PolicyState } from './cp6Readiness'

export default function Cp6PolicyReadiness({ policies }: { policies: readonly PolicyState[] }) {
  const pending = policies.filter(p => p.status !== 'SET' && p.key !== 'LAU-DEC05')
  return <aside className="panel" aria-label="Kesiapan pengaturan transaksi">
    <p role="status">{pending.length ? `${pending.length} pengaturan belum diterapkan. Beberapa transaksi menunggu isian owner.` : 'Pengaturan pada halaman ini sudah diterapkan.'}</p>
    {pending.length > 0 && <details><summary>Lihat transaksi yang menunggu pengaturan</summary>
      <ul>{pending.map(p => <li key={p.key}><strong>{p.key} · {policyStatus(p)}.</strong> {POLICY_EFFECT[p.key]}</li>)}</ul>
    </details>}
    {policies.some(p => p.key === 'LAU-DEC05' && p.status !== 'SET') && <p>Tarif khusus sengaja tidak diaktifkan sesuai keputusan owner. Tarif vendor, proses, dan paket biasa tetap berjalan.</p>}
  </aside>
}
