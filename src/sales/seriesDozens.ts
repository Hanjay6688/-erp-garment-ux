// Owner D14-5 (15 Oct 2026): "auto bagi kalo lusin ... gw jual itu biasa satu seri. berjalan 2 arah juga misal gw
// ketik 4/5/4 tulisannya jadi 1 lusin 1 potong". A series is every size line of one commercial SKU in the draft.
// Dozens typed for a series are split evenly over its sizes; per-size pieces read back as "x lusin y potong".
// An uneven split is refused with a plain sentence, never rounded (as the single-line helper refuses fractions).

const WHOLE = /^[0-9]{1,7}$/

export function dozensText(totalPcs: bigint): string {
  if (totalPcs < 0n) return ''
  const dozens = totalPcs / 12n, pieces = totalPcs % 12n
  if (dozens === 0n) return `${pieces} potong`
  return pieces === 0n ? `${dozens} lusin` : `${dozens} lusin ${pieces} potong`
}

/** Sum of the series lines' typed pieces, or null while any line is empty or not a whole number. */
export function seriesTotal(qtys: string[]): bigint | null {
  if (qtys.length === 0 || qtys.some((q) => !WHOLE.test(q.trim()))) return null
  return qtys.reduce((sum, q) => sum + BigInt(q.trim()), 0n)
}

export type SeriesSplit = { ok: true; perSize: string; total: bigint } | { ok: false; message: string }

export function splitSeriesDozens(dozens: string, pieces: string, sizeCount: number): SeriesSplit {
  const d = dozens.trim(), p = pieces.trim() === '' ? '0' : pieces.trim()
  if (!WHOLE.test(d) || !/^[0-9]{1,2}$/.test(p) || Number(p) > 11) {
    return { ok: false, message: 'Isi lusin dengan angka bulat dan sisa potong 0 sampai 11.' }
  }
  if (!Number.isSafeInteger(sizeCount) || sizeCount < 1) return { ok: false, message: 'Seri ini belum mempunyai ukuran.' }
  const total = BigInt(d) * 12n + BigInt(p)
  if (total === 0n) return { ok: false, message: 'Jumlah lusin masih nol.' }
  if (total % BigInt(sizeCount) !== 0n) {
    return { ok: false, message: `${dozensText(total)} (${total} PCS) tidak bisa dibagi rata ke ${sizeCount} ukuran. Isi per ukuran, atau ubah jumlahnya.` }
  }
  return { ok: true, perSize: String(total / BigInt(sizeCount)), total }
}
