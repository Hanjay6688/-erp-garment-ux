export type ThreeSizeQuantity = [number, number, number]

export function distributeDozensEvenly(dozens: number): ThreeSizeQuantity | null {
  if (!Number.isFinite(dozens) || dozens < 0) return null

  const exactPieces = dozens * 12
  const roundedPieces = Math.round(exactPieces)
  if (Math.abs(exactPieces - roundedPieces) > Number.EPSILON * Math.max(1, Math.abs(exactPieces)) * 4) return null
  if (!Number.isSafeInteger(roundedPieces)) return null
  if (roundedPieces % 3 !== 0) return null

  const perSize = roundedPieces / 3
  if (!Number.isSafeInteger(perSize)) return null
  return [perSize, perSize, perSize]
}
