import { lowercaseHex64, uuidText as uuid } from '../lib/contractPatterns'
import { WaResponseError } from './model'
import type { Tick } from './model'

export function fail(what: string): never { throw new WaResponseError(`Respons sambungan WhatsApp tidak cocok (${what}).`) }
export type Obj = Record<string, unknown>
export const obj = (v: unknown, what: string): Obj => Boolean(v) && typeof v === 'object' && !Array.isArray(v) ? v as Obj : fail(what)
export const arr = (v: unknown, what: string): unknown[] => Array.isArray(v) ? v : fail(what)
export const str = (v: unknown, what: string) => typeof v === 'string' ? v : fail(what)
export const maybeStr = (v: unknown, what: string) => v === null ? null : str(v, what)
export const bool = (v: unknown, what: string) => typeof v === 'boolean' ? v : fail(what)
export const instant = (v: unknown, what: string) => typeof v === 'string' && Number.isFinite(Date.parse(v)) ? v : fail(what)
export const maybeInstant = (v: unknown, what: string) => v === null ? null : instant(v, what)
export const count = (v: unknown, what: string) => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 ? v : fail(what)
export const maybeCount = (v: unknown, what: string) => v === null ? null : count(v, what)
export const positive = (v: unknown, what: string) => typeof v === 'number' && Number.isSafeInteger(v) && v >= 1 ? v : fail(what)
export const maybePositive = (v: unknown, what: string) => v === null ? null : positive(v, what)
export const uuidText = (v: unknown, what: string) => typeof v === 'string' && uuid.test(v) ? v : fail(what)
export const hash = (v: unknown, what: string) => typeof v === 'string' && lowercaseHex64.test(v) ? v : fail(what)
export const maybeUuid = (v: unknown, what: string) => v === null ? null : uuidText(v, what)
export const decimalText = /^-?\d+(\.\d+)?$/

// Numbers come from the sources as text (numeric::text) or, inside the analysis numbers, as JSON numbers.
export const decimal = (v: unknown, what: string) => typeof v === 'number' && Number.isFinite(v) ? String(v)
  : typeof v === 'string' && decimalText.test(v) ? v : fail(what)
export const maybeDecimal = (v: unknown, what: string) => v === null ? null : decimal(v, what)
export const clock = /^([01][0-9]|2[0-3]):[0-5][0-9]$/

export function oneOf<T extends string>(v: unknown, values: readonly T[], what: string): T {
  return typeof v === 'string' && (values as readonly string[]).includes(v) ? v as T : fail(what)
}

export function keys(o: Obj, expected: readonly string[], what: string) {
  const got = Object.keys(o).sort(), want = [...expected].sort()
  if (got.length !== want.length || got.some((k, i) => k !== want[i])) fail(what)
}

// Keys a row must have, and the only other keys it may have.
export function keysWithin(o: Obj, required: readonly string[], allowed: readonly string[], what: string) {
  const got = Object.keys(o)
  if (required.some(k => !got.includes(k)) || got.some(k => !allowed.includes(k))) fail(what)
}

export function tick(v: unknown, what: string): Tick {
  const o = obj(v, what); keys(o, ['at', 'outcome'], what)
  return { at: instant(o.at, what), outcome: maybeStr(o.outcome, what) }
}
export const maybeTick = (v: unknown, what: string) => v === null ? null : tick(v, what)

export function within(v: unknown, lo: number, hi: number, what: string, orZero = false) {
  const n = count(v, what)
  return (orZero && n === 0) || (n >= lo && n <= hi) ? n : fail(what)
}
