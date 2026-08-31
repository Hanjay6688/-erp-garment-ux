// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { InviteAcceptanceAttempt, InviteStepResult } from './InviteAcceptance'
import { InviteAcceptancePage } from './InviteAcceptance'

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((resolver) => { resolve = resolver })
  return { promise, resolve }
}

function inputValue(input: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
  if (!setter) throw new Error('Input value setter unavailable.')
  setter.call(input, value)
  input.dispatchEvent(new Event('input', { bubbles: true }))
}

async function settle() {
  await act(async () => { await new Promise((resolve) => globalThis.setTimeout(resolve, 0)) })
}

let container: HTMLDivElement
let root: Root

beforeEach(() => {
  ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
})

afterEach(async () => {
  await act(async () => { root.unmount() })
  container.remove()
  vi.restoreAllMocks()
})

async function render(attempt: InviteAcceptanceAttempt, onComplete = vi.fn(), onExit = vi.fn()) {
  await act(async () => { root.render(<InviteAcceptancePage attempt={attempt} onComplete={onComplete} onExit={onExit} />) })
  return { onComplete, onExit }
}

function button(label: string) {
  return [...container.querySelectorAll('button')].find((candidate) => candidate.textContent === label)
}

describe('invite acceptance DOM flow', () => {
  it('waits for explicit consent, exposes accessible loading, validates strength, and guards double submit', async () => {
    const verification = deferred<InviteStepResult>()
    const update = deferred<InviteStepResult>()
    const attempt: InviteAcceptanceAttempt = {
      hasValidRequest: true,
      verify: vi.fn(() => verification.promise),
      setPassword: vi.fn(() => update.promise),
      abandon: vi.fn(async () => undefined),
    }
    await render(attempt)
    expect(attempt.verify).not.toHaveBeenCalled()
    expect(container.textContent).toContain('Tautan sensitif sudah dibersihkan')

    await act(async () => { button('Verifikasi undangan')!.dispatchEvent(new MouseEvent('click', { bubbles: true })) })
    expect(attempt.verify).toHaveBeenCalledTimes(1)
    expect(container.querySelector('[role="status"]')?.getAttribute('aria-label')).toBe('Memverifikasi undangan')
    await act(async () => { verification.resolve({ ok: true }) })
    await settle()

    const inputs = container.querySelectorAll('input')
    expect(document.activeElement).toBe(inputs[0])
    await act(async () => {
      inputValue(inputs[0] as HTMLInputElement, 'weak')
      inputValue(inputs[1] as HTMLInputElement, 'weak')
      container.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    })
    expect(container.querySelector('[role="alert"]')?.textContent).toContain('minimal 12')
    expect(attempt.setPassword).not.toHaveBeenCalled()

    await act(async () => {
      inputValue(inputs[0] as HTMLInputElement, 'StrongPassword!42')
      inputValue(inputs[1] as HTMLInputElement, 'StrongPassword!42')
      const form = container.querySelector('form')!
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    })
    expect(attempt.setPassword).toHaveBeenCalledExactlyOnceWith('StrongPassword!42')
    expect((button('Menyimpan…') as HTMLButtonElement).disabled).toBe(true)

    await act(async () => { update.resolve({ ok: true }) })
    await settle()
    expect(container.querySelector('[role="status"]')?.textContent).toContain('berhasil disimpan')
    expect(container.querySelectorAll('input')).toHaveLength(0)
  })

  it('signs out safely before leaving an abandoned flow', async () => {
    const abandoned = deferred<void>()
    const onExit = vi.fn()
    const attempt: InviteAcceptanceAttempt = {
      hasValidRequest: true,
      verify: vi.fn(async (): Promise<InviteStepResult> => ({ ok: true })),
      setPassword: vi.fn(async (): Promise<InviteStepResult> => ({ ok: true })),
      abandon: vi.fn(() => abandoned.promise),
    }
    await render(attempt, vi.fn(), onExit)

    await act(async () => { button('Batalkan dan keluar')!.dispatchEvent(new MouseEvent('click', { bubbles: true })) })
    expect(attempt.abandon).toHaveBeenCalledTimes(1)
    expect(onExit).not.toHaveBeenCalled()
    expect((button('Mengakhiri sesi…') as HTMLButtonElement).disabled).toBe(true)

    await act(async () => { abandoned.resolve() })
    await settle()
    expect(onExit).toHaveBeenCalledTimes(1)
  })

  it('renders invalid-link failure as an accessible alert without a password form', async () => {
    const attempt: InviteAcceptanceAttempt = {
      hasValidRequest: false,
      verify: vi.fn(async () => ({ ok: false, message: 'Tautan undangan tidak valid atau sudah kedaluwarsa.' })),
      setPassword: vi.fn(async () => ({ ok: false, message: 'blocked' })),
      abandon: vi.fn(async () => undefined),
    }
    await render(attempt)
    await settle()
    expect(container.querySelector('[role="alert"]')?.textContent).toContain('tidak valid')
    expect(container.querySelector('form')).toBeNull()
    expect(container.querySelector('input')).toBeNull()
  })
})
