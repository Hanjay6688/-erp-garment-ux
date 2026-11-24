import { useRef, useState } from 'react'
import JSZip from 'jszip'
import { Download, FileSpreadsheet, Upload } from 'lucide-react'
import { convertWorkbook, pack, type WorkbookResult } from './migrationWorkbook.mjs'
import tabNames from './migrationTabNames.json'

const folder = '/migrasi/'
const example = 'Contoh_Migrasi_Sintetis.xlsx'

export default function MigrationWorkbook() {
  const current = useRef(0)
  const [result, setResult] = useState<WorkbookResult | null>(null)
  const [message, setMessage] = useState('')
  const [packing, setPacking] = useState(false)

  async function inspect(file?: File) {
    const ticket = ++current.current
    setResult(null)
    setPacking(false)
    setMessage('Memeriksa ' + (file?.name ?? 'contoh sintetis') + '…')
    try {
      let source: Blob
      if (file) source = file
      else {
        const response = await fetch(folder + example)
        if (!response.ok) throw new Error('Contoh belum tersedia.')
        source = await response.blob()
      }
      if (source.size > 40 * 1024 * 1024) throw new Error('File melebihi 40 MiB. Pilih workbook yang hanya berisi data sumber.')
      const data = await convertWorkbook(await source.arrayBuffer(), tabNames, JSZip)
      if (ticket !== current.current) return
      setResult(data)
      const rows = data.files.reduce((sum, item) => sum + item.rows, 0)
      setMessage(data.errorCount ? `${data.errorCount} temuan perlu diperbaiki.` : rows ? `${rows.toLocaleString('id-ID')} baris dalam ${data.files.length} tab siap dibuat CSV.` : 'Template masih kosong. Isi satu tab atau coba data contoh.')
    } catch (error) {
      if (ticket === current.current) setMessage(error instanceof Error ? error.message : 'File tidak terbaca.')
    }
  }

  async function download() {
    if (!result?.files.length || packing) return
    const ticket = current.current
    setPacking(true)
    try {
      const bytes = await pack(result, JSZip)
      if (current.current !== ticket) return
      const link = document.createElement('a')
      const url = URL.createObjectURL(new Blob([bytes], { type: 'application/zip' }))
      link.href = url
      link.download = 'CSV_Migrasi_ERP.zip'
      document.body.append(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch {
      if (current.current === ticket) setMessage('Paket CSV belum berhasil dibuat. Coba lagi.')
    } finally {
      if (current.current === ticket) setPacking(false)
    }
  }

  return <section className="wb-import" aria-labelledby="wb-title">
    <div className="hero-copy"><h1 id="wb-title">Impor data awal</h1><p>Siapkan Excel dari data lama. Pemeriksaan berlangsung di perangkat ini.</p></div>
    <div className="panel wb-panel"><header><FileSpreadsheet aria-hidden="true"/><h2>Persiapan Excel</h2></header>
      <div className="wb-actions">
        <a className="soft-btn" href={folder + 'Template_Migrasi_ERP_CP8.xlsx'} download><Download size={17}/>Unduh template Excel</a>
        <button type="button" className="soft-btn" onClick={() => void inspect()}>Coba data contoh</button>
        <label className="primary-btn wb-file"><Upload size={17}/>Pilih file Excel<input aria-label="Pilih file Excel" type="file" accept=".xlsx" onChange={event => { const file = event.currentTarget.files?.[0]; event.currentTarget.value = ''; if (file) void inspect(file) }}/></label>
      </div>
      <p role="status" aria-live="polite">{message}</p>
      {Boolean(result?.errorCount) && <ul>{result!.errors.map((error, index) => <li key={index}>{error}</li>)}</ul>}
      {Boolean(result?.files.length) && <><table className="wb-table"><thead><tr><th scope="col">Tab Excel</th><th scope="col">Baris</th></tr></thead><tbody>{result!.files.map(item => <tr key={item.key}><th scope="row">{item.name}</th><td>{item.rows.toLocaleString('id-ID')}</td></tr>)}</tbody></table>
        <button className="primary-btn" type="button" onClick={() => void download()} disabled={packing}><Download size={17}/>Unduh paket CSV</button></>}
    </div>
  </section>
}
