import type { UxTampilan } from './uxTampilan'

export function UxTampilanToggle({ value, onChange, placement = 'topbar' }: { value: UxTampilan; onChange: (value: UxTampilan) => void; placement?: 'topbar' | 'sidebar' }) {
  return <div className={`ux-tampilan-toggle ${placement === 'sidebar' ? 'in-sidebar' : ''}`} role="group" aria-label={placement === 'sidebar' ? 'Pilih tampilan (menu)' : 'Pilih tampilan'} title="Tampilan lama tetap tersedia kalau tampilan baru kurang cocok">
    <button type="button" aria-label="Tampilan baru" aria-pressed={value==='baru'} className={value==='baru'?'active':''} onClick={()=>onChange('baru')}><span className="ux-tampilan-prefix">Tampilan </span>baru</button>
    <button type="button" aria-label="Tampilan lama" aria-pressed={value==='lama'} className={value==='lama'?'active':''} onClick={()=>onChange('lama')}><span className="ux-tampilan-prefix">Tampilan </span>lama</button>
  </div>
}
