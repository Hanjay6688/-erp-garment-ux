export type WipControlStatus = 'ACTIVE' | 'COMPLETED'
export type WipControlFilter = WipControlStatus | 'ALL'

export type WipChildControlFacts = {
  finalSkuComplete: boolean
  unfinishedSewing: boolean
  unsentReady: boolean
  laundryDraft: boolean
  laundryInTransit: boolean
  unresolvedLaundryIssue: boolean
  pendingFinalSkuHandoff: boolean
  openDependency: boolean
  operatorActionRequired: boolean
}

export function deriveWipControlStatus(children: readonly WipChildControlFacts[]): WipControlStatus {
  if (children.length === 0) return 'ACTIVE'
  return children.every((child) => child.finalSkuComplete
    && !child.unfinishedSewing
    && !child.unsentReady
    && !child.laundryDraft
    && !child.laundryInTransit
    && !child.unresolvedLaundryIssue
    && !child.pendingFinalSkuHandoff
    && !child.openDependency
    && !child.operatorActionRequired)
    ? 'COMPLETED'
    : 'ACTIVE'
}

export function filterByWipControlStatus<T extends { controlStatus: WipControlStatus }>(
  rows: readonly T[],
  filter: WipControlFilter,
) {
  return filter === 'ALL' ? [...rows] : rows.filter((row) => row.controlStatus === filter)
}
