// @vitest-environment jsdom
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from './App'
import MobilePrimaryNavigation from './MobilePrimaryNavigation'
import { recoveryRuntime } from '../tests/fixtures/productionRecovery'

const state = vi.hoisted(() => ({ auth: null as unknown }))
vi.mock('./auth/AuthProvider', () => ({ useAuth: () => state.auth }))
let root: Root, container: HTMLDivElement
const runtime = { ...recoveryRuntime, projectRef: 'cp6-disposable', mode: 'DISPOSABLE_TEST' }
function identity(permissions: string[]) {
  state.auth = { runtime, signingOut: false, signOutError: null, signOut: vi.fn(), identity: {
    status: 'AUTHORIZED', profile: { id: 'ui-actor', fullName: 'Penguji UI', roleName: 'Terbatas',
      rowVersion: 1, roleRowVersion: 1 }, permissions,
  } }
}
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
  identity(['dashboard.view'])
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); vi.restoreAllMocks() })
const labels = () => Array.from(container.querySelectorAll('.mobile-primary-nav button')).map(b => b.textContent)

it('admits only current permitted routes and retains the complete-menu entry for a restricted user', async () => {
  await act(async () => root.render(<App/>))
  expect(labels()).toEqual(['Dashboard', 'Lainnya'])
  expect(container.querySelector('.kpi-grid')).toBeNull()
  expect(container.querySelector('.dashboard-unlinked')).not.toBeNull()
})

it('withdraws mobile destinations immediately when the current role loses permissions', async () => {
  identity(['dashboard.view', 'sales.invoice.view', 'warehouse.fg.view', 'finance.payroll.view'])
  await act(async () => root.render(<App/>))
  expect(labels()).toEqual(['Dashboard', 'Penjualan', 'Stok FG', 'Payroll', 'Lainnya'])
  identity(['dashboard.view']); await act(async () => root.render(<App/>))
  expect(labels()).toEqual(['Dashboard', 'Lainnya'])
  expect(container.querySelectorAll('.mobile-primary-nav [aria-current=page]')).toHaveLength(1)
})

it('keeps the current workspace mounted on repeated selection and delegates other routes and More once', async () => {
  const navigate = vi.fn(), more = vi.fn()
  await act(async () => root.render(<MobilePrimaryNavigation
    items={[{ id: 'current', label: 'Saat ini', icon: null }, { id: 'next', label: 'Berikut', icon: null }]}
    current="current" menuOpen={false} onNavigate={navigate} onMore={more}/>))
  const buttons = container.querySelectorAll('button')
  await act(async () => { buttons[0].click(); buttons[0].click() })
  expect(navigate).not.toHaveBeenCalled()
  await act(async () => { buttons[1].click(); buttons[2].click() })
  expect(navigate).toHaveBeenCalledExactlyOnceWith('next'); expect(more).toHaveBeenCalledOnce()
  expect(buttons[2].getAttribute('aria-expanded')).toBe('false')
})
