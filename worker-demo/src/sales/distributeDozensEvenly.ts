export function distributeDozensEvenly(dozens: number, sizeCount = 3): number[] | null {
  if (!Number.isFinite(dozens) || dozens < 0 || !Number.isSafeInteger(sizeCount) || sizeCount < 1) return null

  const exactPieces = dozens * 12
  const roundedPieces = Math.round(exactPieces)
  if (Math.abs(exactPieces - roundedPieces) > Number.EPSILON * Math.max(1, Math.abs(exactPieces)) * 4) return null
  if (!Number.isSafeInteger(roundedPieces)) return null
  if (roundedPieces % sizeCount !== 0) return null

  const perSize = roundedPieces / sizeCount
  if (!Number.isSafeInteger(perSize)) return null
  return Array.from({ length: sizeCount }, () => perSize)
}
