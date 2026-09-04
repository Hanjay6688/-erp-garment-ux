import { describe, expect, it } from 'vitest'
import { CP6_BUSINESS_TIME_LABEL, cp6WibPhysicalTimeToIso, formatCp6WibDateTime } from './cp6BusinessTime'

describe('CP6 business time', () => {
  it('serializes an operator-entered wall clock as Asia/Jakarta regardless of device timezone', () => {
    expect(CP6_BUSINESS_TIME_LABEL).toBe('WIB (Asia/Jakarta)')
    expect(cp6WibPhysicalTimeToIso('2026-09-04T08:15')).toBe('2026-09-04T01:15:00.000Z')
    expect(cp6WibPhysicalTimeToIso('2026-09-04T08:15:42')).toBe('2026-09-04T01:15:42.000Z')
    expect(formatCp6WibDateTime('2026-09-04T01:15:00.000Z')).toContain('08.15')
  })

  it('never invents a physical time for blank or invalid operator input', () => {
    expect(cp6WibPhysicalTimeToIso('')).toBeNull()
    expect(cp6WibPhysicalTimeToIso('2026-02-30T08:00')).toBeNull()
    expect(cp6WibPhysicalTimeToIso('2026-09-04')).toBeNull()
  })
})
