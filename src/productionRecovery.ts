import type { Json } from './types/database.preconnect'

export const productionDomains = ['BS', 'LAUNDRY_QC', 'CUTTING', 'PICKUP', 'WIP', 'INITIAL_IMPORT', 'POCKET_FABRIC'] as const
export type ProductionDomain = typeof productionDomains[number]
export type ProductionEnvelope = {
  action: string; payload: Json; expectedVersion: number | null
  fingerprint: string; id: string; createdAt: string
}
export const domainLabels: Record<ProductionDomain, string> = {
  POCKET_FABRIC: 'Kain kantong', BS: 'Barang BS & Rework', LAUNDRY_QC: 'Laundry / QC', CUTTING: 'Buat Potongan',
  PICKUP: 'Bagi Potongan', WIP: 'Status WIP', INITIAL_IMPORT: 'Impor data awal',
}
const actions: Record<ProductionDomain, readonly string[]> = {
  BS: ['CREATE_MANUAL_BS', 'CLASSIFY_BS', 'SAVE_REWORK', 'COMPLETE_REWORK', 'DISPOSE_BS',
    'HOLD_BS', 'RELEASE_HOLD', 'REVERSE_DISPOSITION', 'REVERSE_REWORK_COMPLETION',
    'SAVE_CLAIM', 'RESOLVE_CLAIM', 'REVERSE_CLAIM_RESOLUTION'],
  LAUNDRY_QC: ['POST_DELIVERY', 'POST_RECEIPT', 'POST_FAILED_WASH', 'REVERSE_DELIVERY',
    'REVERSE_RECEIPT', 'POST_FINAL_SKU', 'REVERSE_FINAL_SKU'],
  CUTTING: ['SAVE_DRAFT', 'POST', 'DELETE'], PICKUP: ['SAVE_DRAFT', 'POST', 'DELETE'], WIP: ['OPEN', 'RESOLVED'],
  POCKET_FABRIC: ['REGISTER', 'POST', 'REVERSE'],
  INITIAL_IMPORT: ['CREATE', 'SAVE_FILE', 'VALIDATE', 'FINALIZE', 'ALLOCATE_CASH_ADVANCE', 'PREPAYMENT'],
}
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const changeEvent = 'erp:production-recovery-changed'

export function productionKey(scope: string, domain: ProductionDomain) {
  // Preserve the admitted CP5/CP6 envelopes across upgrades. Never migrate by
  // deleting an old key: corrupted and inaccessible are not the empty state.
  const prefix = domain === 'BS' ? 'erp.cp5' : domain === 'LAUNDRY_QC' ? 'erp.cp6' : `erp.production.${domain}`
  return `${prefix}.pending-mutation.v1:${scope}`
}
function revisionKey(scope: string) { return `erp.production.revision.v1:${scope}` }
export function productionLockName(scope: string) { return `erp.production.exclusive-writer.v1:${scope}` }
export function productionLockManager() {
  try { return typeof globalThis.navigator?.locks?.request === 'function' ? globalThis.navigator.locks : null }
  catch { return null }
}

export function parseProductionEnvelope(raw: string, domain: ProductionDomain): ProductionEnvelope {
  const value = JSON.parse(raw) as Partial<ProductionEnvelope> | null
  if (!value || typeof value !== 'object' || Array.isArray(value)
    || typeof value.action !== 'string' || !actions[domain].includes(value.action)
    || !value.payload || typeof value.payload !== 'object' || Array.isArray(value.payload)
    || !(value.expectedVersion === null || typeof value.expectedVersion === 'number'
      && Number.isSafeInteger(value.expectedVersion) && value.expectedVersion >= 0)
    || typeof value.id !== 'string' || !uuid.test(value.id)
    || typeof value.createdAt !== 'string' || !Number.isFinite(Date.parse(value.createdAt))
    || value.fingerprint !== JSON.stringify({ action: value.action, payload: value.payload, expectedVersion: value.expectedVersion })) {
    throw new Error('Recovery envelope rusak; jangan hapus UUID atau payload lama.')
  }
  return value as ProductionEnvelope
}

export type ProductionRecoveryState = {
  signature: string | null; corrupted: boolean
  pending: Partial<Record<ProductionDomain, ProductionEnvelope>>
}
export function readProductionRecovery(scope: string): ProductionRecoveryState {
  const pending: ProductionRecoveryState['pending'] = {}
  try {
    const storage = globalThis.localStorage
    if (!storage) throw new Error('Storage tidak tersedia')
    const revision = storage.getItem(revisionKey(scope))
    if (revision !== null && !uuid.test(revision)) throw new Error('Revision rusak')
    const parts = [revision]
    for (const domain of productionDomains) {
      const raw = storage.getItem(productionKey(scope, domain))
      parts.push(raw)
      if (raw !== null) pending[domain] = parseProductionEnvelope(raw, domain)
    }
    return { signature: JSON.stringify(parts), pending, corrupted: false }
  } catch { return { signature: null, pending, corrupted: true } }
}
export function hasProductionPending(state: ProductionRecoveryState) { return Object.keys(state.pending).length > 0 }

function publish(scope: string) {
  globalThis.dispatchEvent(new CustomEvent(changeEvent, { detail: scope }))
}
export function persistProductionEnvelope(scope: string, domain: ProductionDomain, envelope: ProductionEnvelope) {
  try {
    const state = readProductionRecovery(scope)
    if (state.corrupted || hasProductionPending(state)) return false
    const raw = JSON.stringify(envelope)
    parseProductionEnvelope(raw, domain)
    globalThis.localStorage.setItem(productionKey(scope, domain), raw)
    if (globalThis.localStorage.getItem(productionKey(scope, domain)) !== raw) return false
    // A completed mutation must invalidate a tab that missed both storage
    // events. Empty -> envelope -> empty alone would otherwise be an ABA race.
    const revision = globalThis.crypto.randomUUID()
    globalThis.localStorage.setItem(revisionKey(scope), revision)
    return globalThis.localStorage.getItem(revisionKey(scope)) === revision
  } catch { return false }
  finally { publish(scope) }
}
export function clearProductionEnvelope(scope: string, domain: ProductionDomain, envelope: ProductionEnvelope) {
  try {
    const observed = readProductionRecovery(scope)
    const current = observed.pending[domain]
    if (observed.corrupted || current?.id !== envelope.id || current.fingerprint !== envelope.fingerprint) return false
    globalThis.localStorage.removeItem(productionKey(scope, domain))
    return globalThis.localStorage.getItem(productionKey(scope, domain)) === null
  } catch { return false }
  finally { publish(scope) }
}
export function observeProductionRecovery(scope: string, listener: () => void) {
  const local = (event: Event) => { if ((event as CustomEvent).detail === scope) listener() }
  const storage = (event: StorageEvent) => {
    if (event.key === null || event.key === revisionKey(scope)
      || productionDomains.some((domain) => event.key === productionKey(scope, domain))) listener()
  }
  globalThis.addEventListener(changeEvent, local)
  globalThis.addEventListener('storage', storage)
  return () => { globalThis.removeEventListener(changeEvent, local); globalThis.removeEventListener('storage', storage) }
}

export function isDefiniteInitialRejection(error: unknown) {
  if (!error || typeof error !== 'object') return false
  const { code, status } = error as { code?: unknown; status?: unknown }
  if (typeof code !== 'string' || typeof status === 'number' && [408, 425, 429, 502, 503, 504].includes(status)) return false
  // HTTP status alone is not a database rollback receipt. Use the known
  // PostgreSQL statement-rejection families; connection/resource/shutdown and
  // PostgREST/proxy failures retain the envelope conservatively.
  // https://docs.postgrest.org/en/stable/references/errors.html
  return /^(?:22[0-9A-Z]{3}|23[0-9A-Z]{3}|40[0-9A-Z]{3}|42501|P0001)$/.test(code)
}
