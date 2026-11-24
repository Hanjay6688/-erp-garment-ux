import type { SkuMasterWorkspace, SkuSettings } from './skuMaster'
export default function SkuSettingsFields({ value, lookups, change }: { value: SkuSettings; lookups: NonNullable<SkuMasterWorkspace['lookups']>; change: (s: SkuSettings) => void }) {
  const patch = (p: Partial<SkuSettings>) => change({ ...value, ...p })
  return <>
    <label>Harga jual per PCS untuk seluruh ukuran<input inputMode="decimal" value={value.price ?? ''} placeholder="Belum ditentukan" onChange={e => patch({ price: e.target.value === '' ? null : e.target.value })}/></label>
    <h3>Resep aksesori per PCS bagus</h3><p>Biaya aksesori = jumlah resep × harga per satuan. Pilih rata-rata kategori dari stok, atau harga standar resep. Penggantian biaya mandor dicatat terpisah.</p>
    <label>Status resep<select aria-label="Status resep" value={value.bom === null ? 'PENDING' : 'SET'} onChange={e => patch({ bom: e.target.value === 'PENDING' ? null : [] })}><option value="PENDING">Belum ditentukan</option><option value="SET">Sudah ditentukan</option></select></label>
    {value.bom !== null && <>{value.bom.length === 0 && <p>Tanpa aksesori: resep sudah ditentukan dengan 0 komponen.</p>}{value.bom.map((b, i) => {
      const category = lookups.accessories.find(a => a.id === b.category_id)
      const set = (p: Partial<typeof b>) => patch({ bom: value.bom!.map((x, j) => j === i ? { ...x, ...p } : x) })
      return <fieldset key={i}><legend>Aksesori {i + 1}</legend><label>Kategori<select value={b.category_id} onChange={e => { const a = lookups.accessories.find(x => x.id === e.target.value); set({ category_id: e.target.value, hpp_uom_code: a?.unit ?? '', reimbursement_uom_code: a?.unit ?? '' }) }}><option value="">Pilih aksesori</option>{lookups.accessories.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label>
        <label>Jumlah {category?.unit} per PCS<input inputMode="decimal" value={b.qty_per_good_fg_base} onChange={e => set({ qty_per_good_fg_base: e.target.value })}/></label>
        <label>Sumber harga HPP<select value={b.hpp_method} onChange={e => set({ hpp_method: e.target.value })}><option value="CATEGORY_MOVING_AVG">Rata-rata kategori stok</option><option value="BOM_STANDARD">Harga standar resep</option></select></label>
        {b.hpp_method === 'BOM_STANDARD' && <label>Harga standar per {b.hpp_uom_code}<input inputMode="decimal" value={b.hpp_standard_rate ?? ''} onChange={e => set({ hpp_standard_rate: e.target.value })}/></label>}
        <label>Penggantian mandor per {b.reimbursement_uom_code}<input inputMode="decimal" value={b.reimbursement_rate} onChange={e => set({ reimbursement_rate: e.target.value })}/></label><button type="button" onClick={() => patch({ bom: value.bom!.filter((_, j) => i !== j) })}>Hapus aksesori</button>
      </fieldset>
    })}<button type="button" onClick={() => patch({ bom: [...value.bom!, { category_id: '', qty_per_good_fg_base: '', hpp_method: 'CATEGORY_MOVING_AVG', reimbursement_rate: '0', reimbursement_uom_code: '' }] })}>Tambah aksesori</button></>}
    <h3>Tarif pekerjaan per SKU</h3><p>Satu tarif per PCS untuk semua ukuran anggota. Kolom Special hanya berlaku pada mandor yang berstatus Special saat pekerjaan.</p>
    {value.work_rates.map((r, i) => { const set = (p: Partial<typeof r>) => patch({ work_rates: value.work_rates.map((x, j) => j === i ? { ...x, ...p } : x) }); return <fieldset key={i}><legend>Pekerjaan {i + 1}</legend>
      <label>Komponen<select value={r.work_component_id} onChange={e => set({ work_component_id: e.target.value })}><option value="">Pilih pekerjaan</option>{lookups.work.map(x => <option key={x.id} value={x.id}>{x.name} · {x.category}</option>)}</select></label>
      <label>Mandor<select value={r.contractor_id ?? ''} onChange={e => set({ contractor_id: e.target.value || null })}><option value="">Semua mandor</option>{lookups.contractors.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
      <label><input type="checkbox" checked={r.special ?? false} onChange={e => set({ special: e.target.checked })}/>Khusus mandor Special</label>
      <label>Tarif per PCS<input inputMode="decimal" value={r.rate} onChange={e => set({ rate: e.target.value })}/></label><button type="button" onClick={() => patch({ work_rates: value.work_rates.filter((_, j) => j !== i) })}>Hapus tarif pekerjaan</button>
    </fieldset> })}<button type="button" onClick={() => patch({ work_rates: [...value.work_rates, { work_component_id: '', rate: '', contractor_id: null, special: false }] })}>Tambah tarif pekerjaan</button>
    <h3>Referensi laundry</h3><p>Pilih kombinasi atau komponen di kiriman laundry. Tarif berasal dari master vendor; riwayat SKU membantu memilih jasa dan membandingkan biaya sebelumnya.</p>
    {value.laundry_rates.length > 0 && <p>Pengaturan lama memuat tarif laundry SKU. Tarif itu tidak dipakai untuk kiriman baru; revisi ini memakai sumber tarif vendor.</p>}
  </>
}
