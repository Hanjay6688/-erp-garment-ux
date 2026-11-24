export const STOCK_FORMULA_VERSION = 'stock-health.v1' as const

export enum StockHealthStatus {
  BELUM_CUKUP_DATA = 'BELUM_CUKUP_DATA',
  AMAN = 'AMAN',
  RENDAH = 'RENDAH',
  PERLU_PESAN = 'PERLU_PESAN',
  PERLU_PRODUKSI = 'PERLU_PRODUKSI',
  KRITIS = 'KRITIS',
}

export enum StockCalculationBasis {
  BELUM_DIATUR = 'BELUM_DIATUR',
  MANUAL = 'MANUAL',
  REKOMENDASI_SISTEM = 'REKOMENDASI_SISTEM',
}

export type StockItemKind = 'FG' | 'ACCESSORY' | 'FABRIC'
export type StockDataState = 'BACKEND' | 'SIMULATED'
export type StockConfidence = 'TIDAK_TERSEDIA' | 'RENDAH' | 'SEDANG' | 'TINGGI'

export type StockHealthInput = {
  itemKind: StockItemKind
  uom: string
  physicalStock: number | null
  reservedStock: number | null
  confirmedIncoming: number | null
  averageDailyDemand: number | null
  leadTimeDays: number | null
  safetyStock: number | null
  targetStock: number | null
  reorderPointOverride?: number | null
  basis: StockCalculationBasis
  historyDays: number | null
  availableDays: number | null
  stockoutDays: number | null
  minimumSampleDays: number
  sizeRangeApplicable: boolean
  requiredSizes?: readonly string[] | null
  projectedStockBySize?: Readonly<Record<string, number>> | null
  dataState: StockDataState
  sourceSystem: string
  asOf: string | null
  calculatedAt: string | null
  formulaVersion?: string
}

export type StockHealthResult = {
  healthStatus: StockHealthStatus
  basis: StockCalculationBasis
  uom: string
  physicalStock: number | null
  reservedStock: number | null
  availableStock: number | null
  confirmedIncoming: number | null
  projectedStock: number | null
  averageDailyDemand: number | null
  leadTimeDays: number | null
  leadTimeDemand: number | null
  safetyStock: number | null
  reorderPoint: number | null
  targetStock: number | null
  recommendedQty: number | null
  historyDays: number | null
  availableDays: number | null
  stockoutDays: number | null
  minimumSampleDays: number
  brokenRequiredSizes: string[] | null
  confidence: StockConfidence
  dataState: StockDataState
  sourceSystem: string
  asOf: string | null
  calculatedAt: string | null
  formulaVersion: string
  missingFields: string[]
  validationIssues: string[]
  invariants: {
    reserveSubtractedExactlyOnce: boolean | null
    incomingAddedExactlyOnce: boolean | null
  }
}

export type EffectiveStockPolicy = {
  id: string
  effectiveFrom: string
  effectiveTo: string | null
  basis: StockCalculationBasis
  targetStock: number | null
  reorderPoint: number | null
}

export type UomConversion = {
  code: string
  baseCode: string
  factorToBase: number
}

const numericOrNull = (value: number | null, field: string, validationIssues: string[]) => {
  if (value === null) return null
  if (!Number.isFinite(value) || value < 0) {
    validationIssues.push(`${field} harus angka non-negatif`)
    return null
  }
  return value
}

const hasValue = (value: number | null): value is number => value !== null

const actionStatusFor = (itemKind: StockItemKind) =>
  itemKind === 'FG' ? StockHealthStatus.PERLU_PRODUKSI : StockHealthStatus.PERLU_PESAN

export function calculateStockHealth(input: StockHealthInput): StockHealthResult {
  const validationIssues: string[] = []
  const uom = input.uom.trim()
  const sourceSystem = input.sourceSystem.trim()
  const formulaVersion = (input.formulaVersion ?? STOCK_FORMULA_VERSION).trim()
  const asOfIsValid = input.asOf !== null && Number.isFinite(Date.parse(input.asOf))
  const calculatedAtIsValid = input.calculatedAt !== null && Number.isFinite(Date.parse(input.calculatedAt))
  if (!uom) validationIssues.push('uom wajib diisi')
  if (input.asOf !== null && !asOfIsValid) validationIssues.push('asOf harus tanggal/waktu yang valid')
  if (input.calculatedAt !== null && !calculatedAtIsValid) validationIssues.push('calculatedAt harus tanggal/waktu yang valid')
  if (!formulaVersion) validationIssues.push('formulaVersion wajib diisi')
  const physicalStock = numericOrNull(input.physicalStock, 'physicalStock', validationIssues)
  const reservedStock = numericOrNull(input.reservedStock, 'reservedStock', validationIssues)
  const confirmedIncoming = numericOrNull(input.confirmedIncoming, 'confirmedIncoming', validationIssues)
  const averageDailyDemand = numericOrNull(input.averageDailyDemand, 'averageDailyDemand', validationIssues)
  const leadTimeDays = numericOrNull(input.leadTimeDays, 'leadTimeDays', validationIssues)
  const safetyStock = numericOrNull(input.safetyStock, 'safetyStock', validationIssues)
  const requestedTargetStock = numericOrNull(input.targetStock, 'targetStock', validationIssues)
  const reorderPointOverride = numericOrNull(input.reorderPointOverride ?? null, 'reorderPointOverride', validationIssues)
  const historyDays = numericOrNull(input.historyDays, 'historyDays', validationIssues)
  const availableDays = numericOrNull(input.availableDays, 'availableDays', validationIssues)
  const stockoutDays = numericOrNull(input.stockoutDays, 'stockoutDays', validationIssues)
  const rawMinimumSampleDays = numericOrNull(input.minimumSampleDays, 'minimumSampleDays', validationIssues)
  const minimumSampleDays = rawMinimumSampleDays !== null && Number.isInteger(rawMinimumSampleDays) && rawMinimumSampleDays > 0 ? rawMinimumSampleDays : 30
  if (rawMinimumSampleDays !== null && (!Number.isInteger(rawMinimumSampleDays) || rawMinimumSampleDays <= 0)) {
    validationIssues.push('minimumSampleDays harus bilangan bulat positif')
  }
  if (hasValue(historyDays) && hasValue(availableDays) && hasValue(stockoutDays) && availableDays + stockoutDays > historyDays) {
    validationIssues.push('availableDays + stockoutDays tidak boleh melebihi historyDays')
  }
  const sizeRangeInputsReady = !input.sizeRangeApplicable || (input.requiredSizes !== null && input.requiredSizes !== undefined && input.projectedStockBySize !== null && input.projectedStockBySize !== undefined)
  if (input.requiredSizes && input.projectedStockBySize) {
    for (const size of input.requiredSizes) {
      const balance = input.projectedStockBySize[size]
      if (balance !== undefined && (!Number.isFinite(balance) || balance < 0)) {
        validationIssues.push(`projectedStockBySize.${size} harus angka non-negatif`)
      }
    }
  }
  const brokenRequiredSizes = !input.sizeRangeApplicable || !sizeRangeInputsReady
    ? null
    : findBrokenSizeRange(input.requiredSizes ?? [], input.projectedStockBySize ?? {})

  // There is intentionally no available-stock input: reserve can only be subtracted here.
  const availableStock = hasValue(physicalStock) && hasValue(reservedStock)
    ? physicalStock - reservedStock
    : null
  if (hasValue(physicalStock) && hasValue(reservedStock) && reservedStock > physicalStock) {
    validationIssues.push('reservedStock tidak boleh melebihi physicalStock')
  }
  const projectedStock = hasValue(availableStock) && hasValue(confirmedIncoming)
    ? availableStock + confirmedIncoming
    : null
  const leadTimeDemand = hasValue(averageDailyDemand) && hasValue(leadTimeDays)
    ? averageDailyDemand * leadTimeDays
    : null

  const historyIsSufficient = hasValue(historyDays) && historyDays >= minimumSampleDays
  const availableSampleIsSufficient = hasValue(availableDays) && availableDays >= minimumSampleDays
  const systemFormulaReady = input.basis === StockCalculationBasis.REKOMENDASI_SISTEM
    && historyIsSufficient
    && availableSampleIsSufficient
    && hasValue(leadTimeDemand)
    && hasValue(safetyStock)
  const manualFormulaReady = input.basis === StockCalculationBasis.MANUAL
    && (hasValue(reorderPointOverride) || hasValue(requestedTargetStock))

  const reorderPoint = systemFormulaReady
    ? leadTimeDemand + safetyStock
    : manualFormulaReady
      ? reorderPointOverride ?? requestedTargetStock
      : null
  const targetStock = systemFormulaReady
    ? requestedTargetStock ?? reorderPoint
    : manualFormulaReady
      ? requestedTargetStock ?? reorderPoint
      : null
  if (hasValue(reorderPoint) && hasValue(targetStock) && targetStock < reorderPoint) {
    validationIssues.push('targetStock tidak boleh lebih kecil dari reorderPoint')
  }
  const formulaReady = hasValue(projectedStock)
    && hasValue(reorderPoint)
    && hasValue(targetStock)
    && input.dataState === 'BACKEND'
    && sourceSystem.length > 0
    && asOfIsValid
    && calculatedAtIsValid
    && formulaVersion.length > 0
    && (input.itemKind !== 'FG' || sizeRangeInputsReady)
    && validationIssues.length === 0
  const sizeRangeIsBroken = input.itemKind === 'FG' && (brokenRequiredSizes?.length ?? 0) > 0
  const recommendedQty = formulaReady && !sizeRangeIsBroken ? Math.max(0, targetStock - projectedStock) : null

  let healthStatus = StockHealthStatus.BELUM_CUKUP_DATA
  if (formulaReady) {
    if (sizeRangeIsBroken) healthStatus = StockHealthStatus.PERLU_PRODUKSI
    else if (projectedStock <= 0 && (reorderPoint > 0 || targetStock > 0)) healthStatus = StockHealthStatus.KRITIS
    else if (projectedStock < reorderPoint) healthStatus = actionStatusFor(input.itemKind)
    else if (projectedStock < targetStock) healthStatus = StockHealthStatus.RENDAH
    else healthStatus = StockHealthStatus.AMAN
  }

  const missingFields: string[] = []
  if (!hasValue(physicalStock)) missingFields.push('physicalStock')
  if (!hasValue(reservedStock)) missingFields.push('reservedStock')
  if (!hasValue(confirmedIncoming)) missingFields.push('confirmedIncoming')
  if (input.basis === StockCalculationBasis.BELUM_DIATUR) missingFields.push('calculationBasis')
  if (input.basis === StockCalculationBasis.MANUAL && !manualFormulaReady) missingFields.push('manualThreshold')
  if (input.basis === StockCalculationBasis.REKOMENDASI_SISTEM) {
    if (!historyIsSufficient) missingFields.push('minimumHistorySample')
    if (!availableSampleIsSufficient) missingFields.push('minimumAvailableDaySample')
    if (!hasValue(averageDailyDemand)) missingFields.push('averageDailyDemand')
    if (!hasValue(leadTimeDays)) missingFields.push('leadTimeDays')
    if (!hasValue(safetyStock)) missingFields.push('safetyStock')
  }
  if (sizeRangeIsBroken) missingFields.push('sizeRangeTargetBySize')
  if (input.itemKind === 'FG' && !sizeRangeInputsReady) missingFields.push('projectedStockByRequiredSize')
  if (input.dataState === 'SIMULATED') missingFields.push('backendSourceOfTruth')
  if (input.dataState === 'BACKEND' && !sourceSystem) missingFields.push('sourceSystem')
  if (input.dataState === 'BACKEND' && !asOfIsValid) missingFields.push('asOf')
  if (input.dataState === 'BACKEND' && !calculatedAtIsValid) missingFields.push('calculatedAt')
  if (!formulaVersion) missingFields.push('formulaVersion')

  const confidence: StockConfidence = input.dataState === 'SIMULATED' || !formulaReady
    ? 'TIDAK_TERSEDIA'
    : input.basis === StockCalculationBasis.MANUAL
      ? 'SEDANG'
      : hasValue(availableDays) && availableDays >= minimumSampleDays * 2 && hasValue(historyDays) && hasValue(stockoutDays) && stockoutDays <= historyDays * 0.1
        ? 'TINGGI'
        : historyIsSufficient
          ? 'SEDANG'
          : 'RENDAH'

  return {
    healthStatus,
    basis: input.basis,
    uom,
    physicalStock,
    reservedStock,
    availableStock,
    confirmedIncoming,
    projectedStock,
    averageDailyDemand,
    leadTimeDays,
    leadTimeDemand,
    safetyStock,
    reorderPoint,
    targetStock,
    recommendedQty,
    historyDays,
    availableDays,
    stockoutDays,
    minimumSampleDays,
    brokenRequiredSizes,
    confidence,
    dataState: input.dataState,
    sourceSystem,
    asOf: input.asOf,
    calculatedAt: input.calculatedAt,
    formulaVersion,
    missingFields: [...new Set(missingFields)],
    validationIssues,
    invariants: {
      reserveSubtractedExactlyOnce: hasValue(physicalStock) && hasValue(reservedStock) && hasValue(availableStock)
        ? availableStock === physicalStock - reservedStock
        : null,
      incomingAddedExactlyOnce: hasValue(availableStock) && hasValue(confirmedIncoming) && hasValue(projectedStock)
        ? projectedStock === availableStock + confirmedIncoming
        : null,
    },
  }
}

export function createUnconfiguredPrototypeStock(input: {
  itemKind: StockItemKind
  uom: string
  physicalStock: number
  sourceSystem: string
}): StockHealthInput {
  return {
    ...input,
    reservedStock: null,
    confirmedIncoming: null,
    averageDailyDemand: null,
    leadTimeDays: null,
    safetyStock: null,
    targetStock: null,
    reorderPointOverride: null,
    basis: StockCalculationBasis.BELUM_DIATUR,
    historyDays: null,
    availableDays: null,
    stockoutDays: null,
    minimumSampleDays: 30,
    sizeRangeApplicable: input.itemKind === 'FG',
    requiredSizes: null,
    projectedStockBySize: null,
    dataState: 'SIMULATED',
    asOf: null,
    calculatedAt: null,
  }
}

export function calculateAvailabilityAdjustedDemand(soldQuantity: number, availableDays: number): number | null {
  if (!Number.isFinite(soldQuantity) || soldQuantity < 0 || !Number.isFinite(availableDays) || availableDays <= 0) return null
  return soldQuantity / availableDays
}

export function findBrokenSizeRange(requiredSizes: readonly string[], stockBySize: Readonly<Record<string, number>>) {
  return requiredSizes.filter((size) => (stockBySize[size] ?? 0) <= 0)
}

export function convertToBaseUom(quantity: number, conversion: UomConversion): number | null {
  if (!Number.isFinite(quantity) || quantity < 0 || !Number.isFinite(conversion.factorToBase) || conversion.factorToBase <= 0) return null
  return quantity * conversion.factorToBase
}

export function selectEffectiveStockPolicy(policies: readonly EffectiveStockPolicy[], effectiveDate: string) {
  const isoDate = /^\d{4}-\d{2}-\d{2}$/
  if (!isoDate.test(effectiveDate) || !Number.isFinite(Date.parse(`${effectiveDate}T00:00:00Z`))) return null
  const candidates = policies.filter((policy) => {
    if (!isoDate.test(policy.effectiveFrom) || !Number.isFinite(Date.parse(`${policy.effectiveFrom}T00:00:00Z`))) return false
    if (policy.effectiveTo !== null && (!isoDate.test(policy.effectiveTo)
      || !Number.isFinite(Date.parse(`${policy.effectiveTo}T00:00:00Z`))
      || policy.effectiveTo < policy.effectiveFrom)) return false
    return policy.effectiveFrom <= effectiveDate && (policy.effectiveTo === null || effectiveDate <= policy.effectiveTo)
  })
  // Overlap means policy history is corrupt or ambiguous; never choose silently.
  return candidates.length === 1 ? candidates[0] : null
}
