// A KPI tile of the connected CP6 pages. CP6-06 (M:3825): a value the page has not read is unknown, never 0, so it is shown
// as "—" with "belum diketahui" until the server answers; a real 0 from the server is still shown as 0.
export function Cp6Kpi({ label, value, note }: { label: string; value: number | null | undefined; note: string }) {
  const unknown = value === null || value === undefined
  return <article data-kpi-state={unknown ? 'UNKNOWN' : 'KNOWN'}>
    <span>{label}</span>
    <strong aria-label={unknown ? `${label}: belum diketahui` : undefined}>{unknown ? '—' : value}</strong>
    <small>{unknown ? 'belum diketahui · data belum termuat' : note}</small>
  </article>
}
