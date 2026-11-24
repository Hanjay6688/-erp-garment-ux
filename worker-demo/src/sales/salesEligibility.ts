import type { Product } from '../productCatalog'

export function isSellableGoodAtLocation(
  product: Pick<Product, 'location' | 'grade'>,
  selectedLocation: string,
) {
  return product.location === selectedLocation
    && product.grade.trim().toUpperCase() === 'GOOD'
}

export function parseManualPieceQuantity(value: string): number | null {
  const normalized = value.trim()
  if (normalized === '') return 0
  if (!/^\d+$/.test(normalized)) return null
  const parsed = Number(normalized)
  return Number.isSafeInteger(parsed) && parsed >= 0 ? parsed : null
}
