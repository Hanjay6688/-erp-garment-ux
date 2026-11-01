// @vitest-environment jsdom
import { act, StrictMode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import GoodPolicyDatesPanel from './GoodPolicyDatesPanel'
import wire from '../scripts/cp7_accessory_nonpayable/LOCAL_SETTINGS_CONTROLS.json'
import { goodPolicyDateRequestKey, parseGoodPolicyDates, persistGoodDateRequest,
  prepareGoodPolicyDate, readGoodDateRequest, type GoodDatePayload } from './nativeGoodPolicyDates'

const sample = wire.contract_samples, actor = sample.workspace.actor, scope = 'model:good-policy-date-panel'
const rpc = vi.fn(), client = { rpc }, lost = vi.fn(), locked = vi.fn()
let root: Root, container: HTMLDivElement
const tick = () => new Promise<void>(resolve => setTimeout(resolve, 0))
const held = () => readGoodDateRequest(scope, actor)
const command = () => prepareGoodPolicyDate(parseGoodPolicyDates(sample.workspace, actor), sample.workspace.current_source.id,
  sample.command.payload.effective_from, sample.command.payload.reason, true, sample.command.requestId)
const outcome = (args: Record<string, unknown>, status = 'SAVED') => {
  const p = args.p_payload as GoodDatePayload
  return { ...sample.outcome, request_id: args.p_request, actor: p.actor, effective_from: p.effective_from,
    source_event_id: p.source_event_id, reason: p.reason, status,
    id: status === 'SAVED' ? sample.outcome.id : null, source_version: status === 'SAVED' ? sample.outcome.source_version : null }
}
const render = (manage = true) => <GoodPolicyDatesPanel client={client} scope={scope} actor={actor} canManage={manage} onAccessLost={lost} onLockChange={locked}/>
const mount = async (manage = true, strict = false) => act(async () => { root.render(strict ? <StrictMode>{render(manage)}</StrictMode> : render(manage)); await tick() })
const button = (text: string) => {
  const found = [...container.querySelectorAll('button')].find(button => button.textContent === text)
  if (!found) throw Error('MISSING_BUTTON:' + text)
  return found
}
const click = async (text: string) => act(async () => { button(text).click(); await tick() })
const edit = async (element: HTMLInputElement | HTMLTextAreaElement, value: string) => act(async () => {
  Object.getOwnPropertyDescriptor(element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype, 'value')!.set!.call(element, value)
  element.dispatchEvent(new Event('input', { bubbles: true })); element.dispatchEvent(new Event('change', { bubbles: true })); await tick()
})
const review = async () => act(async () => { container.querySelector<HTMLInputElement>('input[type=checkbox]')!.click(); await tick() })
const fill = async () => { await edit(container.querySelector('input[type=date]')!, sample.command.payload.effective_from); await edit(container.querySelector('textarea')!, sample.command.payload.reason); await review() }
const writes = () => rpc.mock.calls.filter(([name]) => name === 'erp_cp7_save_good_policy_date_v1')
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true }); localStorage.clear(); rpc.mockReset(); lost.mockReset(); locked.mockReset()
  Object.defineProperty(navigator, 'locks', { configurable: true, value: { request: async (_name: string, _options: unknown, fn: (lock: object) => unknown) => fn({}) } })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
  rpc.mockImplementation(async (name: string) => name === 'erp_cp7_get_good_policy_dates_v1'
    ? { data: sample.workspace, error: null } : { data: null, error: new TypeError('reply lost') })
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); localStorage.clear(); vi.restoreAllMocks(); Reflect.deleteProperty(navigator, 'locks') })

it('requires an explicit date and review, labels all inputs and reads once in StrictMode', async () => {
  await mount(true, true)
  expect(container.querySelector<HTMLInputElement>('input[type=date]')!.value).toBe('')
  expect(container.querySelector<HTMLTextAreaElement>('textarea')!.value).toBe('')
  expect(button('Simpan tanggal berlaku yang ditinjau').disabled).toBe(true)
  expect(container.textContent).toContain('HPP barang tetap dicatat')
  for (const element of container.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input,select,textarea')) expect(element.labels?.length).toBe(1)
  expect(rpc).toHaveBeenCalledTimes(1); expect(writes()).toHaveLength(0)
})
it('persists before send and retries the same request after a lost reply and remount', async () => {
  let first: Record<string, unknown> | null = null
  rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => {
    if (name === 'erp_cp7_get_good_policy_dates_v1') return { data: sample.workspace, error: null }
    expect(held().pending?.requestId).toBe(args.p_request)
    if (!first) { first = structuredClone(args); return { data: null, error: new TypeError('reply lost') } }
    expect(args).toEqual(first); return { data: outcome(args), error: null }
  })
  await mount(); await fill(); await click('Simpan tanggal berlaku yang ditinjau')
  expect(held().pending).not.toBeNull(); expect(container.querySelector('fieldset')!.disabled).toBe(true)
  expect(locked).toHaveBeenLastCalledWith(true)
  await act(async () => root.unmount()); root = createRoot(container); await mount(); await click('Periksa hasil tanggal yang sama')
  expect(held().pending).toBeNull(); expect(writes()).toHaveLength(2); expect(container.textContent).toContain('versi kategori 35 tersimpan')
})
it('cancels an unresolved request with the original payload and displays cancellation without a saved date', async () => {
  persistGoodDateRequest(scope, command())
  rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => name === 'erp_cp7_get_good_policy_dates_v1'
    ? { data: sample.workspace, error: null } : { data: outcome(args, 'CANCELLED'), error: null })
  await mount(); await click('Batalkan permintaan jika belum tersimpan')
  expect(writes()[0][1]).toEqual({ p_payload: command().payload, p_request: command().requestId, p_cancel: true })
  expect(held().pending).toBeNull(); expect(container.textContent).toContain('Tidak ada tanggal berlaku baru dari permintaan ini')
})
it('reports an already saved result when cancellation arrives after commit', async () => {
  persistGoodDateRequest(scope, command())
  rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => name === 'erp_cp7_get_good_policy_dates_v1'
    ? { data: sample.workspace, error: null } : { data: outcome(args), error: null })
  await mount(); await click('Batalkan permintaan jika belum tersimpan')
  expect(container.textContent).toContain('sudah tersimpan sebelum pembatalan'); expect(held().pending).toBeNull()
})
it('clears review after editing and refuses to write without storage or a browser lock', async () => {
  await mount(); await fill(); expect(button('Simpan tanggal berlaku yang ditinjau').disabled).toBe(false)
  await edit(container.querySelector('textarea')!, 'SYNTHETIC CHANGED REASON')
  expect(button('Simpan tanggal berlaku yang ditinjau').disabled).toBe(true); await review()
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw Error('storage unavailable') })
  await click('Simpan tanggal berlaku yang ditinjau'); expect(writes()).toHaveLength(0)
  vi.restoreAllMocks(); Object.defineProperty(navigator, 'locks', { configurable: true, value: undefined })
  await click('Simpan tanggal berlaku yang ditinjau'); expect(writes()).toHaveLength(0)
})
it('retains a mismatched success receipt and an uncertain replay after access loss', async () => {
  rpc.mockImplementation(async (name: string, args: Record<string, unknown>) => name === 'erp_cp7_get_good_policy_dates_v1'
    ? { data: sample.workspace, error: null } : { data: { ...outcome(args), effective_from: '2026-12-01' }, error: null })
  await mount(); await fill(); await click('Simpan tanggal berlaku yang ditinjau')
  expect(held().pending).not.toBeNull(); expect(container.textContent).not.toContain('versi kategori 35 tersimpan')
  rpc.mockImplementation(async (name: string) => name === 'erp_cp7_get_good_policy_dates_v1' ? { data: sample.workspace, error: null }
    : { data: null, error: { code: '42501', status: 403, message: 'NONPAYABLE_OWNER_DATE_REQUIRED' } })
  await click('Periksa hasil tanggal yang sama'); expect(held().pending).not.toBeNull(); expect(lost).toHaveBeenCalledOnce()
})
it('releases only a definite initial refusal and requires a new read', async () => {
  rpc.mockImplementation(async (name: string) => name === 'erp_cp7_get_good_policy_dates_v1' ? { data: sample.workspace, error: null }
    : { data: null, error: { code: 'P0001', message: 'NONPAYABLE_POSTED_GOOD_POLICY_REVIEW_REQUIRED' } })
  await mount(); await fill(); await click('Simpan tanggal berlaku yang ditinjau')
  expect(held().pending).toBeNull(); expect(container.textContent).toContain('Koreksi atau balik hasil terkait')
  expect(container.querySelector('fieldset')).toBeNull()
})
it('ignores late success after another tab changes the held request', async () => {
  let release: (reply: unknown) => void = () => {}
  rpc.mockImplementation(async (name: string) => name === 'erp_cp7_get_good_policy_dates_v1' ? { data: sample.workspace, error: null }
    : new Promise(resolve => { release = resolve }))
  await mount(); await fill(); await click('Simpan tanggal berlaku yang ditinjau')
  const original = held().pending!, changed = { ...original, requestId: crypto.randomUUID() }
  await act(async () => {
    localStorage.setItem(goodPolicyDateRequestKey(scope), JSON.stringify(changed))
    dispatchEvent(new StorageEvent('storage', { key: goodPolicyDateRequestKey(scope) })); await tick()
  })
  await act(async () => { release({ data: outcome({ p_payload: original.payload, p_request: original.requestId }), error: null }); await tick() })
  expect(held().pending).toEqual(changed); expect(container.textContent).not.toContain('versi kategori 35 tersimpan')
})
it('keeps admin read-only and corrupted recovery closed', async () => {
  localStorage.setItem(goodPolicyDateRequestKey(scope), 'broken')
  await mount(false); expect(container.querySelector('fieldset')!.disabled).toBe(true)
  expect(container.textContent).toContain('Admin dapat membaca riwayat'); expect(writes()).toHaveLength(0)
})
