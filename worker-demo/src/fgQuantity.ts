// Inventory stays in integer pieces, including signed movements. Convert once after summing pieces.
export function dozenPieces(pieces: number | bigint | string) {
  const value = BigInt(pieces)
  const amount = value < 0n ? -value : value
  const dozens = (amount / 12n).toLocaleString('id-ID')
  return (value < 0n ? '−' : '') + dozens + ' lusin ' + amount % 12n + ' potong'
}
export function fgQuantity(pieces: number | bigint | string) {
  return dozenPieces(pieces) + ' (' + BigInt(pieces).toLocaleString('id-ID') + ' pcs)'
}
