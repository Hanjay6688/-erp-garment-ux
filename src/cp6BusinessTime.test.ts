import { describe, expect, it } from 'vitest'
import { CP6_BUSINESS_TIME_LABEL, cp6WibDateTimeInput, cp6WibPhysicalTimeToIso, formatCp6WibDateTime } from './cp6BusinessTime'

// Node's process.env.TZ sets the timezone Date uses; typed here because the app tsconfig has no Node types.
const nodeEnv = (globalThis as unknown as { process: { env: Record<string, string | undefined> } }).process.env

describe('CP6 business time', () => {
  it('serializes an operator-entered wall clock as Asia/Jakarta regardless of device timezone', () => {
    expect(CP6_BUSINESS_TIME_LABEL).toBe('WIB (Asia/Jakarta)')
    expect(cp6WibPhysicalTimeToIso('2026-09-04T08:15')).toBe('2026-09-04T01:15:00.000Z')
    expect(cp6WibPhysicalTimeToIso('2026-09-04T08:15:42')).toBe('2026-09-04T01:15:42.000Z')
    expect(formatCp6WibDateTime('2026-09-04T01:15:00.000Z')).toContain('08.15')
  })

  it('rejects impossible or ambiguous wall-clock values instead of inventing physical time', () => {
    expect(cp6WibPhysicalTimeToIso('')).toBeNull()
    expect(cp6WibPhysicalTimeToIso('2026-02-30T08:00')).toBeNull()
    expect(cp6WibPhysicalTimeToIso('2026-09-04')).toBeNull()
  })

  // CP6-01 (audit 25 Sep 2026): the cutting, pickup and BS pages used new Date(value).toISOString(), which reads the
  // wall clock in the device timezone. The helpers must give the same instant and input on every device.
  const zones = ['Asia/Jakarta', 'Asia/Makassar', 'UTC', 'Pacific/Kiritimati', 'America/Los_Angeles']
  it.each(zones)('keeps WIB wall clock and instant identical on a device in %s', (zone) => {
    const previous = nodeEnv.TZ
    nodeEnv.TZ = zone
    try {
      expect(cp6WibPhysicalTimeToIso('2026-09-20T00:30')).toBe('2026-09-19T17:30:00.000Z')
      expect(cp6WibDateTimeInput('2026-09-19T17:30:00.000Z')).toBe('2026-09-20T00:30')
      expect(cp6WibDateTimeInput(new Date('2026-09-19T17:30:00.000Z'))).toBe('2026-09-20T00:30')
      // The replaced page expression agrees only on a device already set to WIB, so this matrix fails on the old code.
      expect(new Date('2026-09-20T00:30').toISOString() === '2026-09-19T17:30:00.000Z').toBe(zone === 'Asia/Jakarta')
    } finally {
      if (previous === undefined) delete nodeEnv.TZ
      else nodeEnv.TZ = previous
    }
  })

  it('gives an empty input instead of an invented time for an invalid instant', () => {
    expect(cp6WibDateTimeInput('not a time')).toBe('')
    expect(cp6WibDateTimeInput('2026-09-19T17:30:00.000Z')).toBe('2026-09-20T00:30')
  })
})
