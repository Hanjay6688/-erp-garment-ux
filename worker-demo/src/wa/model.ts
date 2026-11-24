// WA-4 (owner D17-3..D17-6): closed parsers for the public RPCs of scripts/cp7-src/alerts/alerts.sql (alerts_read,
// wa_settings_read, wa_settings_save, wa_key_set, wa_test, wa_resolve, settings_json, defaults, analysis_status). Every
// shape below is the server's own; an unknown key, a missing key or a fact the server never writes is refused with
// "Respons ... tidak cocok". The settings predicates mirror wa_settings_save (best practice D13) except the digest/quiet
// hours rule, which only the server decides (CP7_WA_DIGEST_IN_QUIET_HOURS is shown in plain words). The CallMeBot key is
// never parsed, kept or returned here: no reply carries it.
// SS-1 (owner D17-8, D17-9) adds FG_AT_REORDER_POINT: a finished good at or under its reorder point (cp7_stock_formula);
// SS-2/SS-3 add ACCESSORY_AT_REORDER_POINT (materials.sql, material_alert_row). Owner D17-10: a fabric on the formula is a row
// of FABRIC_BELOW_MINIMUM (one title, "Stok kain di bawah minimum"; no separate fabric kind), and an accessory is reminded
// only by its minimum, never the formula: typed (MANUAL) or worked out from the owner's numbers (ESTIMATE, D17-12).
export const obligationKinds = ['OPENING_AR', 'OPENING_AP', 'PAYROLL_AP', 'ACCESSORY_AP', 'LAUNDRY_AP', 'LAUNDRY_RECEIPT', 'LAUNDRY_OPENING_UNINVOICED'] as const
export type ObligationKind = typeof obligationKinds[number]
export const isObligationKind = (kind: string): kind is ObligationKind => obligationKinds.some(k => k === kind)
export const alertKinds = ['FABRIC_BELOW_MINIMUM', 'ACCESSORY_AT_REORDER_POINT', 'FG_AT_REORDER_POINT', 'AR_DUE', 'AP_DUE',
  'PRODUCTION_GAP', 'FABRIC_NEED', 'ACCESSORY_NEED', ...obligationKinds, 'RECOST_PENDING'] as const
export type AlertKind = typeof alertKinds[number]

/** The order of cp7_alert_native.defaults(). */
export const waKinds = ['MANUAL_REMINDER', 'FABRIC_BELOW_MINIMUM', 'ACCESSORY_AT_REORDER_POINT', 'FG_AT_REORDER_POINT', 'AR_DUE', 'AP_DUE',
  'PRODUCTION_GAP', 'FABRIC_NEED', 'ACCESSORY_NEED', ...obligationKinds, 'RECOST_PENDING'] as const
export type WaKind = typeof waKinds[number]

/** The order of the groups on the Pengingat sistem screen (the order of the WhatsApp message, render() in alerts.sql). */
export const alertKindOrder: readonly AlertKind[] = ['FABRIC_BELOW_MINIMUM', 'ACCESSORY_AT_REORDER_POINT', 'FG_AT_REORDER_POINT',
  'FABRIC_NEED', 'ACCESSORY_NEED', 'PRODUCTION_GAP', 'AP_DUE', 'AR_DUE', ...obligationKinds]
export const waKindLabel: Record<WaKind, string> = {
  MANUAL_REMINDER: 'Pengingat pribadi Bos',
  FABRIC_BELOW_MINIMUM: 'Stok kain di bawah minimum',
  ACCESSORY_AT_REORDER_POINT: 'Stok aksesori menipis',
  FG_AT_REORDER_POINT: 'Stok barang jadi menipis',
  AR_DUE: 'Piutang pelanggan jatuh tempo',
  AP_DUE: 'Tagihan supplier jatuh tempo',
  PRODUCTION_GAP: 'Kekurangan produksi (dari analisis)',
  FABRIC_NEED: 'Kain perlu dibeli (dari analisis)',
  ACCESSORY_NEED: 'Kebutuhan aksesori perlu diperiksa (dari analisis)',
  OPENING_AR: 'Piutang saldo awal',
  OPENING_AP: 'Utang saldo awal',
  PAYROLL_AP: 'Tagihan gaji',
  ACCESSORY_AP: 'Kredit retur aksesori mandor',
  LAUNDRY_AP: 'Tagihan laundry',
  LAUNDRY_RECEIPT: 'Penerimaan laundry perlu diperiksa',
  RECOST_PENDING: 'Hitung ulang HPP',
  LAUNDRY_OPENING_UNINVOICED: 'Laundry awal belum ditagih',
}
export const isAnalysisKind = (kind: AlertKind) => kind === 'PRODUCTION_GAP' || kind === 'FABRIC_NEED' || kind === 'ACCESSORY_NEED'

/** The kinds whose every row comes from cp7_stock_formula: no party names, keyed by the item or material. FABRIC_BELOW_MINIMUM
 * also has rows from the formula (FabricFormulaDetail); those are checked by their detail. */
export const isReorderKind = (kind: AlertKind) => kind === 'FG_AT_REORDER_POINT' || kind === 'ACCESSORY_AT_REORDER_POINT'
export const outboxStates = ['PENDING', 'HELD_QUIET', 'DISPATCHED', 'ACCEPTED', 'UNKNOWN', 'RESOLVED_BEFORE_SEND', 'DISABLED', 'KIND_OFF'] as const
export type OutboxState = typeof outboxStates[number]
export const dispatchStatuses = ['QUEUED', 'PROVIDER_ACCEPTED', 'PROVIDER_REFUSED', 'TRANSPORT_FAILED', 'UNKNOWN', 'NOTHING_DUE'] as const
export type DispatchStatus = typeof dispatchStatuses[number]
export const dispatchKinds = ['INSTANT', 'DIGEST', 'TEST'] as const
export type DispatchKind = typeof dispatchKinds[number]
export type DispatchOutcome = 'DELIVERED' | 'NOT_DELIVERED'
export type WaDetailMode = 'SUMMARY' | 'DETAILED'
export const waTickJobs = ['COLLECT', 'SEND', 'ANALYSIS'] as const
export type WaTickJob = typeof waTickJobs[number]

/** The key rule of vault_key_write; the key itself never leaves the input that holds it. */
export const waKeyPattern = /^[A-Za-z0-9_-]{4,64}$/
export const waPhonePattern = /^\+[1-9][0-9]{7,14}$/
export const ALERTS_RESOLVED_DAYS = 7
export const WA_DIGEST_SLOTS = 4
export type Tick = { at: string; outcome: string | null }
export type AnalysisRun = {
  runId: string; dataAsOf: string; phase: 'SET' | 'CHECK' | 'DONE' | 'FAILED'; rule: 'PRODUCTION_GAP' | 'FABRIC_NEED' | 'ACCESSORY_NEED'; nextOffset: number
  checked: number; stillOpen: number; closed: number; ruleOff: number; error: string | null; startedAt: string; updatedAt: string; finishedAt: string | null
}
export type AnalysisRequest = {
  requestId: string; state: 'PENDING' | 'REQUESTED' | 'FAILED' | 'SKIPPED_NO_CHANGE'
  query: { fromDate: string | null; throughDate: string | null; groupMode: string | null } | null
  freshness: string; createdAt: string; requestedAt: string | null; error: string | null
}
export type AnalysisStatus = { run: AnalysisRun | null; request: AnalysisRequest | null; tick: Tick | null }
export type AlertSource = { kind: AlertKind; lastTryAt: string | null; lastOkAt: string | null; lastError: string | null; openCount: number | null }
export type AlertWa = { state: OutboxState; round: number; reason: string | null; dispatchId: number | null; dispatchStatus: DispatchStatus | null; settledAt: string | null }

/** FABRIC_BELOW_MINIMUM of a fabric with a minimum in Kain & Benchmark (fabric_source, the Ringkasan Gudang rule). */
export type FabricDetail = { kind: 'FABRIC_BELOW_MINIMUM'; materialId: string; materialSku: string | null; materialName: string; unitCode: string | null; qty: string; minimumQty: string }
type DueFields = {
  documentId: string | null; number: string | null; amount: string | null; dueDate: string | null
  state: 'OVERDUE' | 'DUE_TODAY'; asOf: string | null; invoiceNumbers: string | null
}
export type DueDetail = ({ kind: 'AR_DUE' } & DueFields) | ({ kind: 'AP_DUE' } & DueFields)
export type ObligationDetail = {
  kind: ObligationKind; documentId: string; label: string; amount: string | null; amountState: 'KNOWN' | 'UNKNOWN'
  dueDate: string | null; state: 'ACTIVE' | 'DATA_REVIEW'; reason: string; economicState: 'OPEN' | 'UNKNOWN'
  asOf: string; sourceHash: string
}
type AnalysisFields = {
  runId: string; dataAsOf: string; checkedAt: string | null; label: string | null; targetKey: string | null
  needSnapshotPcs: string | null; needNowPcs: string | null; increasePcs: string | null; materialId: string | null; materialName: string | null
  value: string | null; unit: string | null; threshold: string | null; reason: string | null
}
export type AnalysisDetail = ({ kind: 'PRODUCTION_GAP' } & AnalysisFields) | ({ kind: 'FABRIC_NEED' } & AnalysisFields)
export type AccessoryNeedDetail = {
  kind: 'ACCESSORY_NEED'; runId: string; dataAsOf: string; checkedAt: string; label: string; targetKey: string
  categoryKey: string; categoryName: string | null; state: 'DATA_REVIEW'; verdict: 'REVIEW_REQUIRED_NOW'
  grossState: 'KNOWN' | 'ASSUMED' | 'UNKNOWN'; grossQty: string | null; unit: string
  installedState: 'UNKNOWN'; installedProven: null; unusedAllocatedState: 'UNKNOWN'; unusedAllocatedProven: null
  additionalExternalState: 'UNKNOWN'; additionalExternal: null; thresholdStatus: 'NOT_EVALUATED_UNKNOWN'
  reason: 'INSTALLATION_AND_ELIGIBLE_UNUSED_SUPPLY_NOT_PROVEN' | 'BOM_NOT_RECORDED' | 'BOM_AMBIGUOUS' | 'CATEGORY_UNAVAILABLE'
}

/** cp7_stock_formula.alert_row: the numbers only, quantities as decimal text. */
export type FgReorderDetail = {
  kind: 'FG_AT_REORDER_POINT'; rootId: string; sizeId: string; sku: string; productName: string; sizeCode: string | null
  freePcs: string; wipPcs: string | null; wipStatus: 'COMPLETE' | 'UNKNOWN' | 'NOT_READ'; positionPcs: string | null; reorderPointPcs: string
  basis: 'MANUAL' | 'FORMULA'; dailyMean: string | null; leadDays: string | null; leadBasis: string | null; bufferMode: string | null
  safetyPcs: string | null; serviceLevel: string | null
  projection?: { analysisAt: string | null; candidatePcs: string | null; conditionalPositionPcs: string | null
    thresholdSource: 'PLANNING_PROFILE' | 'NATIVE_HISTORY_WITH_EXISTING_DEFAULTS' | 'PROFILE_UNAVAILABLE' }
}

/** cp7_stock_formula.material_alert_row: a fabric or accessory at or under its number, quantities as decimal text. */
export type MaterialReorderFields = {
  materialId: string; sku: string; name: string; unitCode: string | null; freeQty: string; onOrderQty: string; reorderPointQty: string
  dailyMean: string | null; leadDays: string | null; safetyQty: string | null; serviceLevel: string | null
}

/** D17-10: a fabric without a minimum, on the formula, is a row of FABRIC_BELOW_MINIMUM with the material shape. */
export type FabricFormulaDetail = { kind: 'FABRIC_BELOW_MINIMUM'; materialType: 'FABRIC'; basis: 'FORMULA' } & MaterialReorderFields

/** D17-10/D17-12: an accessory at or under its minimum (reorderPointQty), typed (MANUAL) or worked out from the owner's numbers
 * (ESTIMATE, with its lama kirim); never the formula, so no cadangan or tingkat layanan. */
export type AccessoryMinimumDetail = { kind: 'ACCESSORY_AT_REORDER_POINT'; materialType: 'ACCESSORY'; basis: 'MANUAL' | 'ESTIMATE' } & MaterialReorderFields
export type MaterialReorderDetail = FabricFormulaDetail | AccessoryMinimumDetail
export type RecalculateCostDetail = { kind: 'RECOST_PENDING'; queueId:string; entityId:string; entityType:string; poNumber:string|null; status:'PENDING'|'RUNNING'|'FAILED' }
export type AlertDetail = RecalculateCostDetail | FabricDetail | MaterialReorderDetail | FgReorderDetail | DueDetail | AnalysisDetail | AccessoryNeedDetail | ObligationDetail
export const isObligationDetail = (d: AlertDetail): d is ObligationDetail => obligationKinds.some(k => k === d.kind)

/** A detail with the material shape (a fabric on the formula, or an accessory), not the fabric minimum's. */
export const isMaterialReorderDetail = (d: AlertDetail): d is MaterialReorderDetail =>
  d.kind === 'ACCESSORY_AT_REORDER_POINT' || (d.kind === 'FABRIC_BELOW_MINIMUM' && 'materialType' in d)
export type SystemAlert = {
  id: string; kind: AlertKind; subjectKey: string; episode: number; title: string; detail: AlertDetail; partyNames: string[]
  state: 'OPEN' | 'RESOLVED'; openedAt: string; refreshedAt: string; resolvedAt: string | null; resolution: string | null; wa: AlertWa | null
}
export type SystemAlerts = { readAt: string; configured: boolean; collector: Tick | null; analysis: AnalysisStatus | null; kinds: AlertSource[]; rows: SystemAlert[] }
export type WaSettings = {
  revision: number; enabled: boolean; phone: string | null; detail: WaDetailMode; digestTimes: string[]; kinds: WaKind[]
  repeatMinutes: number; burstAfterPerDay: number; burstMergeMinutes: number; maxItems: number
  quietEnabled: boolean; quietStart: string; quietEnd: string; analysisEveryMinutes: number; analysisStart: string; analysisEnd: string
  savedAt: string | null
}
export type WaDispatch = {
  id: number; kind: DispatchKind; status: DispatchStatus; queuedAt: string; answeredAt: string | null; httpStatus: number | null
  providerText: string | null; body: string | null; digestSlot: string | null; resolvedOutcome: DispatchOutcome | null; resolvedAt: string | null; items: number
}
export type WaWorkspace = {
  readAt: string; settings: WaSettings; defaults: WaSettings; keyPresent: boolean; keySetAt: string | null; transportIsCallmebot: boolean
  quietNow: boolean; analysis: AnalysisStatus; ticks: Partial<Record<WaTickJob, Tick>>; outbox: Partial<Record<OutboxState, number>>; dispatches: WaDispatch[]
}
export type WaDraft = {
  enabled: boolean; phone: string; detail: WaDetailMode; digestTimes: string[]; kinds: WaKind[]
  repeatMinutes: string; burstAfterPerDay: string; burstMergeMinutes: string; maxItems: string
  quietEnabled: boolean; quietStart: string; quietEnd: string; analysisEveryMinutes: string; analysisStart: string; analysisEnd: string
}
export type WaSaveResult = { replay: boolean; settings: WaSettings }
export type WaKeyResult = { replay: boolean; keyPresent: boolean; keySetAt: string }
export type WaTestResult = { replay: boolean; dispatchId: number; status: DispatchStatus }
export type WaResolveResult = { replay: boolean; dispatchId: number; outcome: DispatchOutcome }

export class WaResponseError extends Error {}
