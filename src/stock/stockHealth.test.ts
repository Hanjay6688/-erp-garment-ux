import { describe, expect, it } from 'vitest'
import {
  StockCalculationBasis,
  StockHealthStatus,
  calculateAvailabilityAdjustedDemand,
  calculateStockHealth,
  convertToBaseUom,
  findBrokenSizeRange,
  selectEffectiveStockPolicy,
  type StockHealthInput,
} from './stockHealth'

const input = (overrides: Partial<StockHealthInput> = {}): StockHealthInput => ({
  itemKind: 'ACCESSORY',
  uom: 'pcs',
  physicalStock: 100,
  reservedStock: 20,
  confirmedIncoming: 10,
  averageDailyDemand: 10,
  leadTimeDays: 5,
  safetyStock: 20,
  targetStock: 100,
  basis: StockCalculationBasis.REKOMENDASI_SISTEM,
  historyDays: 60,
  availableDays: 50,
  stockoutDays: 10,
  minimumSampleDays: 30,
  sizeRangeApplicable: false,
  dataState: 'BACKEND',
  sourceSystem: 'test fixture',
  asOf: '2026-08-30',
  calculatedAt: '2026-08-30T10:00:00Z',
  ...overrides,
})

describe('calculateStockHealth', () => {
  it('keeps missing history and an unset policy honest without a recommendation', () => {
    const result = calculateStockHealth(input({
      basis: StockCalculationBasis.BELUM_DIATUR,
      reservedStock: null,
      confirmedIncoming: null,
      averageDailyDemand: null,
      leadTimeDays: null,
      safetyStock: null,
      targetStock: null,
      historyDays: null,
    }))

    expect(result.healthStatus).toBe(StockHealthStatus.BELUM_CUKUP_DATA)
    expect(result.basis).toBe(StockCalculationBasis.BELUM_DIATUR)
    expect(result.availableStock).toBeNull()
    expect(result.recommendedQty).toBeNull()
  })

  it('subtracts reserve exactly once and adds only confirmed incoming once', () => {
    const result = calculateStockHealth(input())

    expect(result.availableStock).toBe(80)
    expect(result.projectedStock).toBe(90)
    expect(result.invariants).toEqual({
      reserveSubtractedExactlyOnce: true,
      incomingAddedExactlyOnce: true,
    })
  })

  it('treats on-hand fully consumed by reservations as critical', () => {
    const result = calculateStockHealth(input({
      basis: StockCalculationBasis.MANUAL,
      physicalStock: 10,
      reservedStock: 10,
      confirmedIncoming: 0,
      reorderPointOverride: 10,
      targetStock: 20,
      averageDailyDemand: null,
      leadTimeDays: null,
      safetyStock: null,
      historyDays: null,
    }))

    expect(result.projectedStock).toBe(0)
    expect(result.healthStatus).toBe(StockHealthStatus.KRITIS)
    expect(result.recommendedQty).toBe(20)
  })

  it('does not activate a system recommendation before the minimum sample', () => {
    const result = calculateStockHealth(input({ historyDays: 14, availableDays: 10, stockoutDays: 4, minimumSampleDays: 30 }))

    expect(result.healthStatus).toBe(StockHealthStatus.BELUM_CUKUP_DATA)
    expect(result.reorderPoint).toBeNull()
    expect(result.recommendedQty).toBeNull()
    expect(result.validationIssues).toEqual([])
  })

  it('requires enough in-stock days, not merely a long calendar period', () => {
    const result = calculateStockHealth(input({ historyDays: 60, availableDays: 1, minimumSampleDays: 30 }))

    expect(result.healthStatus).toBe(StockHealthStatus.BELUM_CUKUP_DATA)
    expect(result.recommendedQty).toBeNull()
    expect(result.missingFields).toContain('minimumAvailableDaySample')
  })

  it('rejects a zero minimum sample instead of activating an empty history', () => {
    const result = calculateStockHealth(input({ historyDays:0, availableDays:0, stockoutDays:0, minimumSampleDays:0 }))

    expect(result.healthStatus).toBe(StockHealthStatus.BELUM_CUKUP_DATA)
    expect(result.recommendedQty).toBeNull()
    expect(result.validationIssues).toContain('minimumSampleDays harus bilangan bulat positif')
  })

  it('maps a shortage to ordering for accessories and production for FG', () => {
    const accessory = calculateStockHealth(input({ physicalStock: 50, reservedStock: 10, confirmedIncoming: 0 }))
    const fg = calculateStockHealth(input({ itemKind: 'FG', physicalStock: 50, reservedStock: 10, confirmedIncoming: 0, sizeRangeApplicable:false }))

    expect(accessory.healthStatus).toBe(StockHealthStatus.PERLU_PESAN)
    expect(fg.healthStatus).toBe(StockHealthStatus.PERLU_PRODUKSI)
    expect(fg.recommendedQty).toBe(60)
  })

  it('projects only the confirmed-incoming operand supplied by the backend adapter', () => {
    const result = calculateStockHealth(input({ physicalStock: 40, reservedStock: 0, confirmedIncoming: 0 }))

    expect(result.projectedStock).toBe(40)
    expect(result.healthStatus).toBe(StockHealthStatus.PERLU_PESAN)
  })

  it('distinguishes low stock from a safe projected balance', () => {
    const low = calculateStockHealth(input({ physicalStock: 75, reservedStock: 0, confirmedIncoming: 0 }))
    const safe = calculateStockHealth(input({ physicalStock: 110, reservedStock: 0, confirmedIncoming: 0 }))

    expect(low.reorderPoint).toBe(70)
    expect(low.healthStatus).toBe(StockHealthStatus.RENDAH)
    expect(safe.healthStatus).toBe(StockHealthStatus.AMAN)
    expect(safe.recommendedQty).toBe(0)
  })

  it('marks a broken required FG size range without inventing an aggregate quantity', () => {
    const result = calculateStockHealth(input({
      itemKind: 'FG',
      sizeRangeApplicable: true,
      physicalStock: 200,
      reservedStock: 0,
      confirmedIncoming: 0,
      requiredSizes: ['28', '29', '30'],
      projectedStockBySize: { '28':100, '30':100 },
    }))

    expect(result.healthStatus).toBe(StockHealthStatus.PERLU_PRODUKSI)
    expect(result.brokenRequiredSizes).toEqual(['29'])
    expect(result.recommendedQty).toBeNull()
    expect(result.missingFields).toContain('sizeRangeTargetBySize')
  })

  it('fails closed when an FG range applies but per-size projected balances are absent', () => {
    const result = calculateStockHealth(input({ itemKind:'FG', sizeRangeApplicable:true }))

    expect(result.healthStatus).toBe(StockHealthStatus.BELUM_CUKUP_DATA)
    expect(result.recommendedQty).toBeNull()
    expect(result.missingFields).toContain('projectedStockByRequiredSize')
  })

  it('rejects non-finite per-size projected balances', () => {
    const result = calculateStockHealth(input({
      itemKind:'FG',
      sizeRangeApplicable:true,
      requiredSizes:['28', '29', '30'],
      projectedStockBySize:{ '28':10, '29':Number.NaN, '30':10 },
    }))

    expect(result.healthStatus).toBe(StockHealthStatus.BELUM_CUKUP_DATA)
    expect(result.recommendedQty).toBeNull()
    expect(result.validationIssues).toContain('projectedStockBySize.29 harus angka non-negatif')
  })

  it('treats an explicit manual zero policy as safe at zero instead of falsely critical', () => {
    const result = calculateStockHealth(input({
      basis: StockCalculationBasis.MANUAL,
      physicalStock: 0,
      reservedStock: 0,
      confirmedIncoming: 0,
      reorderPointOverride: 0,
      targetStock: 0,
      averageDailyDemand: null,
      leadTimeDays: null,
      safetyStock: null,
      historyDays: null,
    }))

    expect(result.healthStatus).toBe(StockHealthStatus.AMAN)
    expect(result.recommendedQty).toBe(0)
  })

  it('never emits an actionable recommendation from simulated operands', () => {
    const result = calculateStockHealth(input({ dataState:'SIMULATED' }))

    expect(result.healthStatus).toBe(StockHealthStatus.BELUM_CUKUP_DATA)
    expect(result.recommendedQty).toBeNull()
    expect(result.missingFields).toContain('backendSourceOfTruth')
  })

  it('returns the same pure calculation for the same normalized inputs', () => {
    const first = calculateStockHealth(input())
    const second = calculateStockHealth(input())

    expect(second).toEqual(first)
  })

  it('rejects invalid negative components instead of hiding them in a recommendation', () => {
    const result = calculateStockHealth(input({ reservedStock: -1 }))

    expect(result.availableStock).toBeNull()
    expect(result.recommendedQty).toBeNull()
    expect(result.validationIssues).toContain('reservedStock harus angka non-negatif')
  })

  it('fails closed when reservations exceed physical stock', () => {
    const result = calculateStockHealth(input({ physicalStock: 10, reservedStock: 11 }))

    expect(result.healthStatus).toBe(StockHealthStatus.BELUM_CUKUP_DATA)
    expect(result.recommendedQty).toBeNull()
    expect(result.validationIssues).toContain('reservedStock tidak boleh melebihi physicalStock')
  })

  it('requires backend provenance and calculation timestamps before a status is actionable', () => {
    const result = calculateStockHealth(input({ sourceSystem: ' ', asOf: null, calculatedAt: 'not-a-date' }))

    expect(result.healthStatus).toBe(StockHealthStatus.BELUM_CUKUP_DATA)
    expect(result.recommendedQty).toBeNull()
    expect(result.missingFields).toEqual(expect.arrayContaining(['sourceSystem', 'asOf', 'calculatedAt']))
    expect(result.validationIssues).toContain('calculatedAt harus tanggal/waktu yang valid')
  })

  it('rejects a target below reorder point instead of understating the shortage', () => {
    const result = calculateStockHealth(input({ targetStock: 50 }))

    expect(result.healthStatus).toBe(StockHealthStatus.BELUM_CUKUP_DATA)
    expect(result.recommendedQty).toBeNull()
    expect(result.validationIssues).toContain('targetStock tidak boleh lebih kecil dari reorderPoint')
  })
})

describe('stock calculation helpers', () => {
  it('uses available days rather than all calendar days for demand', () => {
    expect(calculateAvailabilityAdjustedDemand(90, 9)).toBe(10)
    expect(calculateAvailabilityAdjustedDemand(90, 0)).toBeNull()
  })

  it('finds a broken required size range', () => {
    expect(findBrokenSizeRange(['28', '29', '30'], { '28': 10, '29': 0, '30': 4 })).toEqual(['29'])
  })

  it('converts accessory UOM with an explicit factor', () => {
    expect(convertToBaseUom(2, { code: 'LUSIN', baseCode: 'PCS', factorToBase: 12 })).toBe(24)
    expect(convertToBaseUom(1, { code: 'BOX', baseCode: 'PCS', factorToBase: 0 })).toBeNull()
  })

  it('selects the effective policy without rewriting historical policy', () => {
    const policies = [
      { id: 'old', effectiveFrom: '2026-01-01', effectiveTo: '2026-06-30', basis: StockCalculationBasis.MANUAL, targetStock: 80, reorderPoint: 50 },
      { id: 'new', effectiveFrom: '2026-07-01', effectiveTo: null, basis: StockCalculationBasis.MANUAL, targetStock: 120, reorderPoint: 75 },
    ]

    expect(selectEffectiveStockPolicy(policies, '2026-03-01')?.id).toBe('old')
    expect(selectEffectiveStockPolicy(policies, '2026-08-01')?.id).toBe('new')
  })

  it('fails closed for overlapping or invalid effective policy history', () => {
    const overlapping = [
      { id: 'a', effectiveFrom: '2026-01-01', effectiveTo: null, basis: StockCalculationBasis.MANUAL, targetStock: 80, reorderPoint: 50 },
      { id: 'b', effectiveFrom: '2026-07-01', effectiveTo: null, basis: StockCalculationBasis.MANUAL, targetStock: 120, reorderPoint: 75 },
    ]

    expect(selectEffectiveStockPolicy(overlapping, '2026-08-01')).toBeNull()
    expect(selectEffectiveStockPolicy(overlapping, 'not-a-date')).toBeNull()
  })
})
