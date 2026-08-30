// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import OperationsAdminPages, { type OperationsAdminView } from './OperationsAdminPages'

let container: HTMLDivElement
let root: Root

const renderView = (view: OperationsAdminView) => {
  act(() => root.render(<OperationsAdminPages view={view} onNavigate={vi.fn()}/>))
}

beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
})

afterEach(() => {
  act(() => root.unmount())
  container.remove()
})

describe('Operations admin fixture disclosure', () => {
  it('marks settings versions, policies, numbering, and roles as examples', () => {
    renderView('admin-settings')

    expect(container.querySelector('[role="note"]')?.textContent).toContain('DATA CONTOH · UX SIMULASI')
    expect(container.textContent).toContain('Fixture v12 · efektif 29 Agu')
    expect(container.textContent).toContain('belum membaca atau menulis kebijakan Supabase')
    expect(container.textContent).toContain('Contoh format')
    expect(container.textContent).toContain('Contoh scope')
    expect([...container.querySelectorAll('.policy-switch span')].every((item) => item.textContent?.startsWith('CONTOH ·'))).toBe(true)
  })

  it('marks period status, checks, dates, and previous close as a fixture', () => {
    renderView('admin-period-close')

    expect(container.querySelector('[role="note"]')?.textContent).toContain('tidak ada query close-gate')
    expect(container.textContent).toContain('FIXTURE · OPEN · 2 BLOCKER')
    expect(container.textContent).toContain('6 pemeriksaan fixture lintas modul')
    expect([...container.querySelectorAll('.close-checks article > b')]).toHaveLength(6)
    expect([...container.querySelectorAll('.close-checks article > b')].every((item) => item.textContent?.startsWith('CONTOH ·'))).toBe(true)
    expect(container.textContent).toContain('Bukan hasil close live')
    expect(container.textContent).not.toContain('Terverifikasi sebagai input')
  })

  it('marks audit metrics and every event as examples without claiming a live backend guard', () => {
    renderView('admin-audit')

    expect(container.querySelector('[role="note"]')?.textContent).toContain('bukan bukti guard backend berjalan')
    expect(container.textContent).not.toContain('Guard backend bekerja')
    expect(container.textContent).toContain('2 event contoh')
    expect(container.textContent).toContain('6 / 6 contoh')
    expect([...container.querySelectorAll('.audit-action small')]).toHaveLength(6)
    expect([...container.querySelectorAll('.audit-action small')].every((item) => item.textContent?.startsWith('EVENT CONTOH ·'))).toBe(true)
  })
})
