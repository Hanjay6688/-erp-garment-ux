// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import MasterDataPages from './MasterDataPages'

describe('Master Produk human-facing identity', () => {
  let container: HTMLDivElement
  let root: Root

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

  it('shows and edits Merek -> Nomor SKU -> Model without a Pattern field', () => {
    act(() => root.render(<MasterDataPages view="master-products"/>))
    expect(container.textContent).toContain('Vivo · 73001 · Classic')

    const add = [...container.querySelectorAll('button')]
      .find((button) => button.textContent?.trim() === 'Tambah produk')
    expect(add).toBeDefined()
    act(() => add?.click())

    const fieldLabels = [...container.querySelectorAll('.md-editor-grid > label > span:first-child, .md-editor-grid > .md-size-field > span:first-child')]
      .map((node) => node.textContent?.trim())
    expect(fieldLabels.slice(0, 4)).toEqual([
      'MEREK', 'NOMOR SKU', 'MODEL', 'NAMA PRODUK / DESKRIPSI',
    ])
    expect(fieldLabels).not.toContain('POLA')
  })
})
