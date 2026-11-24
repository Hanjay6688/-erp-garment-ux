// "Tampilan baru" (UX rapih layer) vs "Tampilan lama" (previous look).
// The new layer lives in src/ux-rapih.css and only applies while <html> has
// the `ux-rapih` class, so the previous look is always one click away.

export type UxTampilan = 'baru' | 'lama'

export const UX_TAMPILAN_STORAGE_KEY = 'erp-ux-tampilan'
export const UX_RAPIH_CLASS = 'ux-rapih'

export function readUxTampilan(storage: Pick<Storage, 'getItem'> | undefined = safeStorage()): UxTampilan {
  try {
    return storage?.getItem(UX_TAMPILAN_STORAGE_KEY) === 'lama' ? 'lama' : 'baru'
  } catch {
    return 'baru'
  }
}

export function saveUxTampilan(value: UxTampilan, storage: Pick<Storage, 'setItem'> | undefined = safeStorage()) {
  try {
    storage?.setItem(UX_TAMPILAN_STORAGE_KEY, value)
  } catch {
    // Private mode / blocked storage: the choice simply lasts for this session.
  }
}

export function applyUxTampilan(value: UxTampilan, root: Pick<Element, 'classList'> | undefined = globalThis.document?.documentElement) {
  root?.classList.toggle(UX_RAPIH_CLASS, value === 'baru')
}

function safeStorage(): Storage | undefined {
  try {
    return globalThis.localStorage
  } catch {
    return undefined
  }
}
