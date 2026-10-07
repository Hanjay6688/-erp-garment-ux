import { describe, expect, it } from 'vitest'
import { UX_RAPIH_CLASS, UX_TAMPILAN_STORAGE_KEY, applyUxTampilan, readUxTampilan, saveUxTampilan } from './uxTampilan'

describe('Tampilan baru / lama switch', () => {
  it('defaults to the new look and remembers "lama"', () => {
    const values = new Map<string, string>()
    const storage = { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => { values.set(key, value) } }
    expect(readUxTampilan(storage)).toBe('baru')
    saveUxTampilan('lama', storage)
    expect(values.get(UX_TAMPILAN_STORAGE_KEY)).toBe('lama')
    expect(readUxTampilan(storage)).toBe('lama')
    saveUxTampilan('baru', storage)
    expect(readUxTampilan(storage)).toBe('baru')
  })

  it('survives blocked storage', () => {
    const blocked = { getItem: () => { throw new Error('blocked') }, setItem: () => { throw new Error('blocked') } }
    expect(readUxTampilan(blocked)).toBe('baru')
    expect(() => saveUxTampilan('lama', blocked)).not.toThrow()
    expect(readUxTampilan(undefined)).toBe('baru')
  })

  it('toggles the scoping class that carries the whole new layer', () => {
    const classes = new Set<string>()
    const root = { classList: { toggle: (name: string, force?: boolean) => { if (force) classes.add(name); else classes.delete(name); return Boolean(force) } } } as unknown as Element
    applyUxTampilan('baru', root)
    expect(classes.has(UX_RAPIH_CLASS)).toBe(true)
    applyUxTampilan('lama', root)
    expect(classes.has(UX_RAPIH_CLASS)).toBe(false)
  })
})
