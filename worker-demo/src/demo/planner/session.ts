import { useSyncExternalStore } from 'react'
import { emptySession, type Session } from './model'
import type { LaundryDelivery } from '../laundryModel'
import { invoiceKey, readSaleReturns } from '../saleReturnJournal'

const key = 'atelier.planner.nov24.1'
const changed = 'atelier-planner-example-updated'
export const laundryBookKey = 'erp.demo.laundry.book.v1'
const readLaundry = () => window.sessionStorage.getItem(laundryBookKey) ?? ''

function withLaundry(session: Session, raw: string): Session {
  if (!raw) return session
  try {
    const data = JSON.parse(raw) as { deliveries?: LaundryDelivery[] }
    return Array.isArray(data.deliveries) ? { ...session, laundry: data.deliveries } : session
  } catch { return session }
}

export function refreshPlanner() {
  window.dispatchEvent(new Event(changed))
}
function read() { return window.sessionStorage.getItem(key) ?? '' }
function parse(value: string): Session {
  if (!value) return emptySession
  try {
    const data = JSON.parse(value)
    return Array.isArray(data.cuts) && Array.isArray(data.pickups) ? {...data, confirmed:Array.isArray(data.confirmed)?data.confirmed:[],elsewhere:Array.isArray(data.elsewhere)?data.elsewhere:[]} : emptySession
  } catch { return emptySession }
}
export const readPlannerSession = () => typeof window === 'undefined' ? emptySession : { ...withLaundry(parse(read()), readLaundry()), saleReturns:readSaleReturns() }
function subscribe(update: () => void) {
  window.addEventListener(changed, update)
  return () => window.removeEventListener(changed, update)
}
export function usePlannerSession() {
  const main = useSyncExternalStore(subscribe, read, () => '')
  const laundry = useSyncExternalStore(subscribe, readLaundry, () => '')
  useSyncExternalStore(subscribe, () => window.sessionStorage.getItem(invoiceKey), () => null)
  return { ...withLaundry(parse(main), laundry), saleReturns:readSaleReturns() }
}
export function changeSession(edit: (current: Session) => Session) {
  const next = edit(readPlannerSession())
  window.sessionStorage.setItem(key, JSON.stringify({ ...next, laundry: undefined, saleReturns: undefined }))
  refreshPlanner()
  return next
}
