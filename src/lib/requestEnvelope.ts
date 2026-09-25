import { isUnansweredFailure } from './clientError'

// W10 / CP6-05 (independent audit round 9; M:1679, M:3819): a master-data write keeps its request identity until the
// server has answered. The envelope (request UUID, RPC and the exact arguments) is stored before sending; a repeat of the
// same change after a lost answer replays it with the same UUID, so the server replays the stored result instead of
// taking a new request. A different change is held back until the unknown one is settled. Same idea as the envelopes of
// the connected production pages (src/productionRecovery.ts), for the Pola and Hak Akses pages.
export type RequestEnvelope = {
  id: string; rpc: string; args: Record<string, unknown>; fingerprint: string; createdAt: string
}
export type PendingRead = { envelope: RequestEnvelope | null; corrupted: boolean }
export type SendOutcome =
  | { ok: true }
  | { ok: false; state: 'UNKNOWN'; error: unknown }
  | { ok: false; state: 'REFUSED'; error: unknown }
  | { ok: false; state: 'BLOCKED'; pending: RequestEnvelope | null }
// The page sends with a literal RPC name per call site (source ownership check); the envelope only carries the name.
export type Send = (rpc: string, args: Record<string, unknown>) => PromiseLike<{ error: unknown }>

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const memory = new Map<string, string>()

export function requestEnvelopeKey(scope: string) { return `erp.master.pending-request.v1:${scope}` }

function storage() {
  try { return globalThis.localStorage ?? null } catch { return null }
}
function getRaw(scope: string) {
  const store = storage()
  if (!store) return memory.get(requestEnvelopeKey(scope)) ?? null
  return store.getItem(requestEnvelopeKey(scope))
}
function setRaw(scope: string, value: string | null) {
  const key = requestEnvelopeKey(scope)
  const store = storage()
  if (value === null) { memory.delete(key); store?.removeItem(key); return }
  memory.set(key, value)
  store?.setItem(key, value)
}
function fingerprintOf(rpc: string, args: Record<string, unknown>) { return JSON.stringify({ rpc, args }) }

export function readPendingRequest(scope: string): PendingRead {
  let raw: string | null
  try { raw = getRaw(scope) } catch { return { envelope: null, corrupted: true } }
  if (raw === null) return { envelope: null, corrupted: false }
  try {
    const value = JSON.parse(raw) as Partial<RequestEnvelope> | null
    if (!value || typeof value.id !== 'string' || !uuid.test(value.id) || typeof value.rpc !== 'string'
      || !value.args || typeof value.args !== 'object' || Array.isArray(value.args)
      || value.fingerprint !== fingerprintOf(value.rpc, value.args) || typeof value.createdAt !== 'string') {
      return { envelope: null, corrupted: true }
    }
    return { envelope: value as RequestEnvelope, corrupted: false }
  } catch { return { envelope: null, corrupted: true } }
}

async function deliver(scope: string, envelope: RequestEnvelope, send: Send): Promise<SendOutcome> {
  let error: unknown = null
  try { ({ error } = await send(envelope.rpc, { ...envelope.args, p_client_request_id: envelope.id })) }
  catch (thrown) { error = thrown }
  if (!error) { setRaw(scope, null); return { ok: true } }
  if (isUnansweredFailure(error)) return { ok: false, state: 'UNKNOWN', error }
  setRaw(scope, null)
  return { ok: false, state: 'REFUSED', error }
}

/** Sends one change. The same change after an unknown outcome reuses its UUID; another change waits (BLOCKED). */
export async function sendOnce(scope: string, rpc: string, args: Record<string, unknown>, send: Send): Promise<SendOutcome> {
  const { envelope, corrupted } = readPendingRequest(scope)
  if (corrupted) return { ok: false, state: 'BLOCKED', pending: null }
  const fingerprint = fingerprintOf(rpc, args)
  if (envelope && envelope.fingerprint !== fingerprint) return { ok: false, state: 'BLOCKED', pending: envelope }
  const current = envelope ?? { id: globalThis.crypto.randomUUID(), rpc, args, fingerprint, createdAt: new Date().toISOString() }
  if (!envelope) setRaw(scope, JSON.stringify(current))
  return deliver(scope, current, send)
}

/** Replays the stored change exactly (same UUID, same arguments) to learn its outcome. */
export async function replayPendingRequest(scope: string, send: Send): Promise<SendOutcome> {
  const { envelope, corrupted } = readPendingRequest(scope)
  if (corrupted || !envelope) return { ok: false, state: 'BLOCKED', pending: envelope }
  return deliver(scope, envelope, send)
}

export const PENDING_UNKNOWN_MESSAGE = 'Hasil perubahan belum diketahui (balasan server tidak diterima). Tekan Simpan lagi tanpa mengubah isi, atau "Kirim ulang perubahan tertunda": identitas permintaannya sama, jadi server tidak mencatatnya dua kali.'
export const PENDING_BLOCKED_MESSAGE = 'Ada perubahan sebelumnya yang hasilnya belum diketahui. Kirim ulang perubahan tertunda itu dulu sebelum mengirim perubahan lain.'
export const PENDING_CORRUPTED_MESSAGE = 'Catatan permintaan tertunda di browser ini rusak. Jangan dihapus; muat ulang halaman dan periksa data sebelum mengubah apa pun.'

