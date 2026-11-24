import { useSyncExternalStore } from 'react'
import { emptySession, type Session } from './model'

const key = 'atelier.planner.nov24.1'
const changed = 'atelier-planner-example-updated'
function read() { return window.sessionStorage.getItem(key) ?? '' }
function parse(value: string): Session {
  if (!value) return emptySession
  try {
    const data = JSON.parse(value)
    return Array.isArray(data.cuts) && Array.isArray(data.pickups) ? {...data, confirmed:Array.isArray(data.confirmed)?data.confirmed:[],elsewhere:Array.isArray(data.elsewhere)?data.elsewhere:[]} : emptySession
  } catch { return emptySession }
}
export const readPlannerSession = () => typeof window === 'undefined' ? emptySession : parse(read())
function subscribe(update: () => void) {
  window.addEventListener(changed, update)
  return () => window.removeEventListener(changed, update)
}
export function usePlannerSession() {
  return parse(useSyncExternalStore(subscribe, read, () => ''))
}
export function changeSession(edit: (current: Session) => Session) {
  const next = edit(parse(read()))
  window.sessionStorage.setItem(key, JSON.stringify(next))
  window.dispatchEvent(new Event(changed))
  return next
}
