import type { LucideIcon } from 'lucide-react'
import './workspaceFigures.css'

type Figure = {
  label: string
  value: string | number
  icon: LucideIcon
  tone: 'blue' | 'green' | 'amber' | 'red'
}

export function WorkspaceFigures({ label, figures }: { label: string; figures: Figure[] }) {
  return <dl className="workspace-figures" aria-label={label}>
    {figures.map(({ label, value, icon: Icon, tone }) => <div key={label} data-tone={tone}>
      <dt><Icon aria-hidden="true"/>{label}</dt><dd>{value}</dd>
    </div>)}
  </dl>
}
