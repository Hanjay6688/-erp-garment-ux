export type NotaSizeValues = [number, number, number]
export type NotaSizeLabels = [string, string, string]

export type ReadyFgNotaComponent = {
  id: string
  name: string
  rate: number
}

export type ReadyFgNotaCard = {
  id: string
  kind: 'REWORK_RELEASE' | 'STUCK_RELEASE'
  caseId: string
  originId?: string
  sourceLabel: string
  label: string
  brand: string
  sku: string
  material: string
  mandor: string
  sizes: NotaSizeLabels
  qtyBySize: NotaSizeValues
  qty: number
  components: ReadyFgNotaComponent[]
  unitRate: number
  subtotal: number
  createdAt: string
}

export type RegularFgNotaSnapshot = {
  cardId: string
  fullRate: number
  sewingRate: number
  commissionRate: number
  bomRate: number
  bsComponents: ReadyFgNotaComponent[]
  stuckComponents: ReadyFgNotaComponent[]
}

export type RegularFgNotaSource = {
  parentId: string
  batchId: string
  completionCount: number
}

export const regularFgNotaCardId = (source: Pick<RegularFgNotaSource, 'parentId' | 'batchId'>) =>
  `qc-${source.parentId}-${source.batchId}`

export function selectRegularFgNotaSources<T extends RegularFgNotaSource>(sources: readonly T[]) {
  const earliestBySewingSource = new Map<string, T>()
  sources.forEach((source) => {
    const id = regularFgNotaCardId(source)
    const current = earliestBySewingSource.get(id)
    if (!current || source.completionCount < current.completionCount) earliestBySewingSource.set(id, source)
  })
  return Array.from(earliestBySewingSource.values())
}
