/** Align quantities by physical size, even when shipments have different subsets/order. */
export function alignSizeQuantities(sourceSizes: string[], quantities: number[], targetSizes: string[]): number[] {
  if (sourceSizes.length !== quantities.length || new Set(sourceSizes).size !== sourceSizes.length
    || new Set(targetSizes).size !== targetSizes.length || quantities.some(q => !Number.isSafeInteger(q) || q < 0)
    || sourceSizes.some((size, i) => quantities[i] > 0 && !targetSizes.includes(size))) {
    throw new Error('Jumlah dan ukuran fisik tidak cocok.')
  }
  const values = new Map(sourceSizes.map((size, i) => [size, quantities[i]]))
  return targetSizes.map(size => values.get(size) ?? 0)
}
