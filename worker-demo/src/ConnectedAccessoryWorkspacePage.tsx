import { lazy, Suspense, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { useTransactionSource } from './TransactionSourceNavigation'
import ConnectedAccessoryIssuePage from './ConnectedAccessoryIssuePage'
import './accessory-workspace.css'

const Report = lazy(() => import('./ConnectedAccessoryStandardReportPage'))

export default function ConnectedAccessoryWorkspacePage() {
  const { runtime, identity } = useAuth()
  const source = useTransactionSource('ACCESSORY_ISSUE')
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') return <ConnectedAccessoryIssuePage/>
  const canReport = ['OWNER', 'ADMIN'].includes(identity.profile.role)
    && identity.permissions.includes('finance.contractor_accessory.view')
    && identity.permissions.includes('finance.hpp.view')
  const scope = JSON.stringify([runtime.projectRef, identity.profile.id, identity.profile.authUserId,
    identity.profile.rowVersion, identity.profile.roleRowVersion, identity.profile.role,
    identity.permissions, source?.key ?? null])
  // A source-link navigation or access change retires the report immediately
  // and opens the existing note page with its own source/recovery handling.
  return <Workspace key={scope} canReport={canReport}/>
}

function Workspace({ canReport }: { canReport: boolean }) {
  const [report, setReport] = useState(false)
  return <>
    {canReport && <div className="panel asw-tabs" role="group" aria-label="Tampilan aksesori mandor">
      <button type="button" aria-pressed={!report} onClick={() => setReport(false)}>Nota ambil aksesori</button>
      <button type="button" aria-pressed={report} onClick={() => setReport(true)}>Diambil vs standar GOOD</button>
    </div>}
    {canReport && report
      ? <Suspense fallback={<p role="status">Membuka laporan aksesori…</p>}><Report/></Suspense>
      : <ConnectedAccessoryIssuePage/>}
  </>
}
