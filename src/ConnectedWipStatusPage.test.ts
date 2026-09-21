import { describe, expect, it } from 'vitest'
import { parseWipResponse } from './ConnectedWipStatusPage'

import { wipFixture } from '../tests/fixtures/productionRecovery'

describe('WIP facts must remain unknown when the response is malformed', () => {
  it('accepts real zero quantities and legacy nullable Pattern/distribution', () => {
    expect(parseWipResponse(wipFixture()).rows[0].sewn_qty_pcs).toBe(0)
  })
  it.each(['not-a-number', null, undefined, '', true, -1, 1.5, Number.MAX_SAFE_INTEGER + 1])('rejects invalid COUNT %s', (value) => {
    const fixture = wipFixture()
    Object.assign(fixture.rows[0], { unfinished_sewing_qty_pcs: value })
    expect(() => parseWipResponse(fixture)).toThrow()
  })
  it.each(['row_version', 'open_flags', 'updated_at', 'distribution'])('rejects missing required field %s', (field) => {
    const fixture = wipFixture()
    Reflect.deleteProperty(fixture.rows[0], field)
    expect(() => parseWipResponse(fixture)).toThrow()
  })
  it('rejects flags inconsistent with their count', () => {
    const fixture = wipFixture()
    fixture.rows[0].open_flag_count = 1
    expect(() => parseWipResponse(fixture)).toThrow()
  })
})
