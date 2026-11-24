/** Compact catalogue membership, including discontinuous series and explicit single sizes. */
export function sizeRangeLabel(values: readonly string[]): string {
  const labels = [...new Set(values.map(value => value.trim()).filter(Boolean))]
  if (!labels.length) return ''
  const apparel = ['XXXS', 'XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']
  const numeric = labels.every(label => /^(0|[1-9]\d*)$/.test(label) && Number.isSafeInteger(Number(label)))
  const ordinal = (label: string) => numeric ? Number(label) : apparel.indexOf(label.toUpperCase())
  if (!numeric && labels.some(label => ordinal(label) < 0)) return labels.join(', ')
  labels.sort((left, right) => ordinal(left) - ordinal(right))
  const ranges: string[] = []
  let start = labels[0], end = start
  const finish = () => ranges.push(start === end ? start : start + '–' + end)
  for (const label of labels.slice(1)) {
    if (ordinal(label) !== ordinal(end) + 1) { finish(); start = label }
    end = label
  }
  finish()
  return ranges.join(', ')
}
