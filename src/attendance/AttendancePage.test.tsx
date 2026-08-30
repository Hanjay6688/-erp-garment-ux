// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AttendancePage from './AttendancePage'

let container: HTMLDivElement
let root: Root

const buttonContaining = (text: string) => {
  const button = [...container.querySelectorAll('button')].find((candidate) => candidate.textContent?.includes(text))
  if (!button) throw new Error(`Button not found: ${text}`)
  return button as HTMLButtonElement
}

const click = async (element: HTMLElement) => {
  await act(async () => { element.click() })
}

const changeInput = async (element: HTMLInputElement, value: string) => {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
  await act(async () => {
    setter?.call(element, value)
    element.dispatchEvent(new Event('input', {bubbles: true}))
    element.dispatchEvent(new Event('change', {bubbles: true}))
  })
}

beforeEach(async () => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
  await act(async () => { root.render(<AttendancePage onNavigate={vi.fn()}/>) })
})

afterEach(async () => {
  await act(async () => { root.unmount() })
  container.remove()
})

describe('AttendancePage guarded interactions', () => {
  it('shows count and nominal preview before applying a bulk attendance action', async () => {
    expect(container.querySelectorAll('.attendance2-present')).toHaveLength(0)

    await click(buttonContaining('Tandai semua hadir'))

    expect(container.textContent).toContain('PREVIEW AKSI MASSAL')
    expect(container.textContent).toContain('Belum diterapkan dan belum menulis backend.')
    expect(container.querySelectorAll('.attendance2-present')).toHaveLength(0)

    await click(buttonContaining('Terapkan ke Draft'))

    expect(container.querySelectorAll('.attendance2-present').length).toBeGreaterThan(0)
    expect(container.textContent).not.toContain('PREVIEW AKSI MASSAL')
    expect(container.textContent).toContain('Masih Draft lokal; backend belum berubah.')
  })

  it('locks direct edits after posting and exposes a reasoned correction flow', async () => {
    const showInactive = container.querySelector('.attendance2-roster>header input[type="checkbox"]')
    expect(showInactive).toBeInstanceOf(HTMLInputElement)
    await click(showInactive as HTMLInputElement)

    await click(buttonContaining('Tandai semua hadir'))
    await click(buttonContaining('Terapkan ke Draft'))

    const explicitAbsentButtons = [...container.querySelectorAll('button')]
      .filter((button) => button.textContent?.includes('Set absen')) as HTMLButtonElement[]
    expect(explicitAbsentButtons).toHaveLength(2)
    for (const button of explicitAbsentButtons) await click(button)

    const postButton = buttonContaining('Simulasikan posting')
    expect(postButton.disabled).toBe(false)
    await click(postButton)

    const attendanceChecks = [...container.querySelectorAll('.attendance2-matrix input[type="checkbox"]')] as HTMLInputElement[]
    expect(attendanceChecks.length).toBeGreaterThan(0)
    expect(attendanceChecks.every((checkbox) => checkbox.disabled)).toBe(true)
    expect(container.textContent).toContain('POSTED')

    await click(buttonContaining('Buat koreksi'))
    expect(container.textContent).toContain('POSTED TETAP IMMUTABLE')
    expect(container.textContent).toContain('Buat dokumen koreksi baru')
    expect(buttonContaining('Siapkan request').disabled).toBe(true)
  })

  it('keeps attendance and lifecycle isolated per Mandor and period identity', async () => {
    const showInactive = container.querySelector('.attendance2-roster>header input[type="checkbox"]') as HTMLInputElement
    await click(showInactive)
    await click(buttonContaining('Tandai semua hadir'))
    await click(buttonContaining('Terapkan ke Draft'))
    for (const button of [...container.querySelectorAll('button')].filter((candidate) => candidate.textContent?.includes('Set absen'))) {
      await click(button as HTMLButtonElement)
    }
    await click(buttonContaining('Simulasikan posting'))
    expect(container.textContent).toContain('POSTED')

    const contractor = container.querySelector<HTMLSelectElement>('.attendance2-controls select')
    expect(contractor).not.toBeNull()
    await act(async () => {
      if (contractor) contractor.value = 'selo'
      contractor?.dispatchEvent(new Event('change', {bubbles: true}))
    })

    expect(container.textContent).toContain('DRAFT')
    expect(container.querySelectorAll('.attendance2-present')).toHaveLength(0)
  })

  it('keeps the same attendance draft when only the pay date changes', async () => {
    await click(buttonContaining('Tandai semua hadir'))
    await click(buttonContaining('Terapkan ke Draft'))
    const recordedBefore = container.querySelectorAll('.attendance2-present').length
    expect(recordedBefore).toBeGreaterThan(0)

    const dateInputs = [...container.querySelectorAll<HTMLInputElement>('.attendance2-controls input[type="date"]')]
    expect(dateInputs).toHaveLength(3)
    await changeInput(dateInputs[2], '2026-09-01')

    expect(container.querySelectorAll('.attendance2-present')).toHaveLength(recordedBefore)
    expect(container.textContent).toContain('Tanggal gajian 1 Sep 2026')
  })

  it('reactivates an inactive worker with the same stable ID and a preserved employment gap', async () => {
    const showInactive = container.querySelector('.attendance2-roster>header input[type="checkbox"]') as HTMLInputElement
    await click(showInactive)
    const mamanCard = [...container.querySelectorAll<HTMLElement>('.attendance2-roster-list>article')]
      .find((card) => card.textContent?.includes('wrk-epi-003'))
    expect(mamanCard).toBeDefined()
    const reactivate = [...(mamanCard?.querySelectorAll('button') ?? [])]
      .find((button) => button.textContent?.includes('Aktifkan kembali')) as HTMLButtonElement
    await click(reactivate)

    const form = container.querySelector<HTMLFormElement>('.attendance2-employment-editor')
    expect(form?.textContent).toContain('AKTIFKAN KEMBALI')
    const effectiveDate = form?.querySelector<HTMLInputElement>('input[type="date"]')
    const reason = form?.querySelector<HTMLInputElement>('input:not([type="date"])')
    expect(effectiveDate).not.toBeNull()
    expect(reason).not.toBeNull()
    await changeInput(effectiveDate as HTMLInputElement, '2026-08-30')
    await changeInput(reason as HTMLInputElement, 'Kembali membantu tim')
    await click(buttonContaining('Simpan status simulasi'))

    const updatedCard = [...container.querySelectorAll<HTMLElement>('.attendance2-roster-list>article')]
      .find((card) => card.textContent?.includes('wrk-epi-003'))
    expect(updatedCard?.textContent).toContain('Status aktif · 2 periode kerja')
    expect(container.textContent).toContain('stable ID wrk-epi-003')
    expect(container.textContent).toContain('Jeda masa kerja')
  })

  it('shows uncovered effective-rate cells and blocks posting instead of snapshotting zero', async () => {
    const dateInputs = [...container.querySelectorAll<HTMLInputElement>('.attendance2-controls input[type="date"]')]
    await changeInput(dateInputs[0], '2026-08-19')
    await changeInput(dateInputs[1], '2026-08-20')

    expect(container.textContent).toContain('2 tanggal eligible belum punya rate')
    expect(buttonContaining('Simulasikan posting').disabled).toBe(true)
  })

  it('keeps posted eligibility stable when a later employment end is added', async () => {
    const showInactive = container.querySelector('.attendance2-roster>header input[type="checkbox"]') as HTMLInputElement
    await click(showInactive)
    await click(buttonContaining('Tandai semua hadir'))
    await click(buttonContaining('Terapkan ke Draft'))
    for (const button of [...container.querySelectorAll('button')].filter((candidate) => candidate.textContent?.includes('Set absen'))) {
      await click(button as HTMLButtonElement)
    }
    await click(buttonContaining('Simulasikan posting'))
    const totalsBefore = [...container.querySelectorAll('.attendance2-metrics article')].map((card) => card.textContent)

    const dediCard = [...container.querySelectorAll<HTMLElement>('.attendance2-roster-list>article')]
      .find((card) => card.textContent?.includes('wrk-epi-001'))
    const deactivate = [...(dediCard?.querySelectorAll('button') ?? [])]
      .find((button) => button.textContent?.includes('Nonaktifkan')) as HTMLButtonElement
    await click(deactivate)
    const reason = container.querySelector<HTMLInputElement>('.attendance2-employment-editor input:not([type="date"])')
    await changeInput(reason as HTMLInputElement, 'Berhenti setelah periode posted')
    await click(buttonContaining('Simpan status simulasi'))

    expect([...container.querySelectorAll('.attendance2-metrics article')].map((card) => card.textContent)).toEqual(totalsBefore)
    expect(container.textContent).toContain('POSTED')
  })
})
