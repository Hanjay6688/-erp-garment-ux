import {useEffect,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {hasPermission} from './auth/accessCatalog'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatReceiptDecimal as numberText} from './procurementContract'
import TransactionSourceLink from './TransactionSourceNavigation'
import {parseSalesCreditDependencies,type CreditDependencySource,type SalesCreditDependencies as Dependencies} from './salesCreditDependenciesContract'

export default function SalesCreditDependencies({source,current,locked}:{source:CreditDependencySource;current:boolean;locked:boolean}) {
  const {runtime,identity} = useAuth(), access = identity.status === 'AUTHORIZED' ? identity : null
  const permitted = current && hasPermission(access,'sales.invoice.view') && hasPermission(access,'sales.return.view') && hasPermission(access,'finance.ar.view')
  const readable = permitted && !locked && Boolean(source.review_token)
  const scope = JSON.stringify([isConnectedRuntime(runtime) ? runtime.projectRef : null,access?.profile.authUserId,access?.profile.id,
    access?.profile.rowVersion,access?.profile.roleRowVersion,access?.permissions,source,readable])
  const active = useRef(scope), serial = useRef(0); active.current = scope
  const [capture,setCapture] = useState<{scope:string;data:Dependencies}|null>(null)
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState<{scope:string;message:string}|null>(null)
  useEffect(()=>{++serial.current;setCapture(null);setBusy(false);setError(null);return()=>{++serial.current}},[scope])
  const data = readable && capture?.scope === scope ? capture.data : null
  const problem = readable && error?.scope === scope ? error.message : ''
  const load = async(offset=0)=>{
    if (!readable || busy || !isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') return
    const wanted=scope,ticket=++serial.current
    setCapture(null);setError(null);setBusy(true)
    try {
      const result=await getUatSupabaseClient(runtime).rpc('erp_cp7_get_sales_credit_dependencies_v1',{p_query:{
        sale_id:source.id,expected_version:source.row_version,review_token:source.review_token!,offset,limit:25,
      }})
      if (active.current !== wanted || serial.current !== ticket) return
      if (result.error) throw result.error
      const parsed=parseSalesCreditDependencies(result.data,source,identity.profile.authUserId,offset)
      setCapture({scope:wanted,data:parsed})
    } catch(failure) {
      if (active.current === wanted && serial.current === ticket) setError({scope:wanted,message:normalizeClientError(failure).message})
    } finally {
      if (active.current === wanted && serial.current === ticket) setBusy(false)
    }
  }
  if (!permitted) return null
  return <section aria-label={`Penggunaan saldo kredit ${source.number}`}>
    <h4>Saldo kredit yang sudah digunakan</h4>
    <p>Pengembalian uang atau pemakaian saldo kredit yang masih aktif dapat menahan pembatalan dokumen asal. Periksa dokumen berikut dahulu, lalu muat ulang invoice.</p>
    <button type="button" disabled={!readable || busy} onClick={()=>void load()}>{busy ? 'Memeriksa penggunaan saldo kredit…' : 'Lihat penggunaan saldo kredit'}</button>
    {!data && !busy && !problem ? <p>Penggunaan saldo kredit belum diperiksa.</p> : null}
    {busy ? <p role="status">Rincian sedang dimuat; penggunaan saldo kredit belum dipastikan.</p> : null}
    {problem ? <p role="alert">{problem} Penggunaan saldo kredit belum dapat dipastikan.</p> : null}
    {data ? <>
      <p>{data.page.total} penggunaan saldo kredit aktif.</p>
      {data.page.total !== '0' ? <ol aria-label="Langkah membatalkan penggunaan saldo kredit">
        <li>Buka retur asal pada daftar berikut, lalu buka Saldo kredit pelanggan pada invoice asal.</li>
        <li>Pilih Periksa riwayat kredit, lalu Periksa pembatalan pada pemakaian saldo atau pengembalian uang yang terkait.</li>
        <li>Isi waktu transaksi WIB dan alasan, periksa pembatalan penuh, lalu simpan. Nilai dan rekening mengikuti transaksi asli.</li>
        <li>Muat ulang invoice dan periksa penggunaan saldo kredit lagi sebelum membatalkan retur atau pembayaran asal.</li>
      </ol> : null}
      {data.dependencies.map(row=><article className="cproc-item" key={row.event_id} data-credit-dependency-id={row.event_id}>
        <strong>{row.kind === 'REFUND' ? 'Pengembalian uang' : 'Pemakaian saldo kredit'} · Rp{numberText(row.amount)}</strong>
        <p>Retur {row.source_return_number} · invoice asal {row.source_sale_number}</p>
        <p>Tanggal transaksi {row.economic_date} · tanggal buku {row.book_date}</p>
        <TransactionSourceLink sourceType="SALES_RETURN" sourceId={row.source_return_id} disabled={!readable || busy} label={`Buka retur asal ${row.source_return_number}`}/>
        {row.target_sale ? <><p>Dipakai pada invoice {row.target_sale.number}.</p><TransactionSourceLink sourceType="SALE" sourceId={row.target_sale.id} disabled={!readable || busy} label={`Buka invoice pemakaian ${row.target_sale.number}`}/></> : null}
      </article>)}
      {data.page.total === '0' ? <p>Tidak ada penggunaan saldo kredit aktif pada invoice ini.</p> : data.dependencies.length === 0 ? <p>Halaman ini tidak menampilkan penggunaan aktif. Periksa halaman sebelumnya.</p> : null}
      <div className="cproc-pagination">
        <button type="button" disabled={busy || !readable || data.page.offset === 0} onClick={()=>void load(Math.max(0,data.page.offset-25))}>Penggunaan kredit sebelumnya</button>
        <button type="button" disabled={busy || !readable || data.page.next_offset === null} onClick={()=>void load(data.page.next_offset??0)}>Penggunaan kredit berikutnya</button>
      </div>
    </> : null}
  </section>
}
