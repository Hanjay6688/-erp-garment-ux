export type QtyTuple = number[]

export type SizeTuple = string[]

export type ProductionPatternSnapshot = Readonly<{
  id: string
  code: string
  revision: string
  name: string
}>

export const simulationPatternSnapshots = {
  lucyRegular: { id: 'b4500000-0000-0000-0000-000000000042', code: 'LCY-REG', revision: 'R1', name: 'Kulot Lucy Regular' },
  nevadaLoose: { id: 'b4500000-0000-0000-0000-000000000043', code: 'NVD-LOOSE', revision: 'R2', name: 'Nevada Loose' },
  malibuRegular: { id: 'b4500000-0000-0000-0000-000000000041', code: 'MLB-REG', revision: 'R1', name: 'Malibu Regular' },
  zodiakJumbo: { id: 'b4500000-0000-0000-0000-000000000039', code: 'ZDK-JUMBO', revision: 'R3', name: 'Zodiak Jumbo' },
} satisfies Record<string, ProductionPatternSnapshot>

export const patternSnapshotLabel = (pattern: ProductionPatternSnapshot | null) => pattern
  ? `${pattern.code} · ${pattern.revision} · ${pattern.name}`
  : 'Histori lama · Pola belum tercatat'
