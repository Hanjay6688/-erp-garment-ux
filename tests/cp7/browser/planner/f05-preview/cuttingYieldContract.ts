// Private F05 proposal. The shared AnalysisResult and F04 kernels are unchanged.
// Prediction, range fitting and classification belong to the producer, not JSX.
export type YieldInput = Readonly<{
  rollId: string; rollRevision: string; materialId: string; patternId: string; patternRevision: string;
  consumed: Readonly<{ value: string; unit: 'M' }>;
  usableWidthCm: string | null; markerRevision: string | null;
  sizeSlots: readonly string[]; observedCutPcs: string | null; outputComplete: boolean;
  materialFamily: Readonly<{ brandId: string; millId: string; behaviourBasis: 'FIXTURE_MATERIAL_HISTORY_NOT_VERIFIED' }>;
  measurements: Readonly<{ issuedDeclaredM: string; issuedMeasuredM: string | null; remainingMeasuredM: string | null;
    familyWidthCm: string; evidence: 'FIXTURE_ONLY' | 'UNVERIFIED'; refs: readonly string[] }>;
}>
export type YieldContext = Readonly<{ runId: string; actorScope: string; accessEpoch: string }>
export type YieldPeer = Readonly<{ rollId: string; sourceRevision: string }>
export type YieldUnavailable = 'INSUFFICIENT' | 'INCOMPLETE' | 'UNSEEN_COMBINATION' | 'STALE' | 'ERROR'
export type YieldReview = Readonly<{
  contract: 'f05.cutting-yield-preview.v1'; fixtureKind: 'SYNTHETIC_ONLY'; inputKey: string;
  context: YieldContext; modelVersion: string; policyVersion: string;
}> & (Readonly<{
  status: 'READY'; assessment: 'NORMAL' | 'LOW' | 'HIGH';
  interval: Readonly<{ lower: string; upper: string; unit: 'PCS'; kind: 'PREDICTION'; basis: 'WITHOUT_WIDTH' | 'WITH_RECORDED_WIDTH'; qualification: 'FIXTURE_ONLY_NOT_CALIBRATED' }>;
  peers: readonly YieldPeer[]; periodStart: string; periodEnd: string;
  reasons: readonly string[]; checks: readonly string[]; findings: readonly string[];
}> | Readonly<{ status: YieldUnavailable; reason: string }>)

// Repeated sizes retain multiplicity. Slot ordering alone does not define a
// new mix; a known marker/layout revision remains a separate identity.
export function sizeMixKey(slots: readonly string[]) { return JSON.stringify([...slots].sort()) }
export function sizeMixLabel(slots: readonly string[]) {
  const counts = new Map<string, number>()
  for (const size of slots) counts.set(size, (counts.get(size) ?? 0) + 1)
  return [...counts].sort(([a], [b]) => a.localeCompare(b)).map(([size, count]) => `${size}×${count}`).join(' · ')
}
export function yieldInputKey(input: YieldInput) {
  return JSON.stringify([input.rollId, input.rollRevision, input.materialId, input.patternId, input.patternRevision,
    input.consumed.value, input.consumed.unit, input.usableWidthCm, input.markerRevision,
    sizeMixKey(input.sizeSlots), input.observedCutPcs, input.outputComplete, input.materialFamily, input.measurements])
}

export function guardYieldReview(result: YieldReview, input: YieldInput, context: YieldContext): YieldReview {
  if (result.contract !== 'f05.cutting-yield-preview.v1' || result.fixtureKind !== 'SYNTHETIC_ONLY'
    || result.inputKey !== yieldInputKey(input) || result.context.runId !== context.runId
    || result.context.actorScope !== context.actorScope || result.context.accessEpoch !== context.accessEpoch) throw new Error('Konteks hasil analyzer tidak cocok. Hasil lama ditahan.')
  if (result.status === 'READY') {
    if (!input.outputComplete || !input.observedCutPcs || !/^\d+$/.test(input.observedCutPcs)
      || input.sizeSlots.length === 0) throw new Error('Input atau hasil per roll belum lengkap.')
    if (result.interval.basis !== (input.usableWidthCm === null ? 'WITHOUT_WIDTH' : 'WITH_RECORDED_WIDTH')) throw new Error('Basis lebar tidak sesuai. Lebar kosong tidak boleh diimputasi diam-diam.')
    const { lower, upper, unit, kind, qualification } = result.interval
    if (!/^\d+$/.test(lower) || !/^\d+$/.test(upper) || BigInt(lower) > BigInt(upper)
      || unit !== 'PCS' || kind !== 'PREDICTION' || qualification !== 'FIXTURE_ONLY_NOT_CALIBRATED'
      || result.peers.length === 0 || new Set(result.peers.map(peer => peer.rollId)).size !== result.peers.length
      || result.peers.some(peer => peer.rollId === input.rollId || !peer.sourceRevision)) throw new Error('Rentang atau sumber pembanding tidak valid.')
    // Consistency check on a supplied classification; never fit a range here.
    const actual = BigInt(input.observedCutPcs)
    if ((result.assessment === 'LOW' && actual >= BigInt(lower))
      || (result.assessment === 'HIGH' && actual <= BigInt(upper))
      || (result.assessment === 'NORMAL' && (actual < BigInt(lower) || actual > BigInt(upper)))) throw new Error('Status tidak sesuai dengan hasil dan rentang yang diberikan.')
  }
  return result
}
