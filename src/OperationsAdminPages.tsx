import { useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Check, CheckCircle2, ChevronDown,
  ChevronRight, ClipboardCheck, Clock3, FileClock, FileSearch, Filter,
  History, KeyRound, LockKeyhole, RefreshCcw, Save, Search, Settings2,
  ShieldAlert, ShieldCheck, SlidersHorizontal, UserRoundCog, UsersRound,
  WalletCards, XCircle,
} from 'lucide-react'
import AttendancePage from './attendance/AttendancePage'
import './operations-admin.css'

export type OperationsAdminView = 'operations-attendance' | 'admin-settings' | 'admin-period-close' | 'admin-audit'

type OperationsAdminProps = {
  view: OperationsAdminView
  onNavigate: (view: OperationsAdminView) => void
}

type AuditPriority = 'P0' | 'P1' | 'P2' | 'TUNING'
type AuditEvent = {
  id: string
  priority: AuditPriority
  module: string
  action: string
  reference: string
  actor: string
  role: string
  happenedAt: string
  result: 'BERHASIL' | 'DIBLOKIR' | 'DIBALIKKAN'
  reason: string
  impact: string
  before: string
  after: string
  sourceTime: string
}

const money = (value: number) => new Intl.NumberFormat('id-ID', {
  style: 'currency', currency: 'IDR', maximumFractionDigits: 0,
}).format(value)

const dateLabel = (value: string) => new Intl.DateTimeFormat('id-ID', {
  weekday: 'long', day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC',
}).format(new Date(`${value}T00:00:00Z`))

const auditExampleEvents: AuditEvent[] = [
  {id:'AUD-26882',priority:'P1',module:'Payroll',action:'Rate harian diubah',reference:'ABS-260829-AFAT',actor:'Owner',role:'Administrator',happenedAt:'29 Agu 2026 · 07:42',result:'BERHASIL',reason:'Tambahan rate untuk pekerjaan urgent hari ini.',impact:'Payroll harian +Rp85.000; snapshot tanggal sebelumnya tidak berubah.',before:'Afat · Rp150.000 / orang / hari',after:'Afat · Rp155.000 / orang / hari',sourceTime:'Tanggal kerja 29 Agu 2026 · Posting 29 Agu 2026 07:42'},
  {id:'AUD-26879',priority:'P1',module:'Master Data',action:'Kewajiban absensi Mandor diubah',reference:'MDR-AFUI',actor:'Owner',role:'Administrator',happenedAt:'28 Agu 2026 · 18:16',result:'BERHASIL',reason:'Afui tidak diwajibkan memakai absensi anak buah.',impact:'attendance_required diubah menjadi false; status dan rate Special tetap merupakan aturan terpisah.',before:'attendance_required = true',after:'attendance_required = false',sourceTime:'Efektif 29 Agu 2026 · Dicatat 28 Agu 2026 18:16'},
  {id:'AUD-26874',priority:'P1',module:'Penjualan',action:'Invoice draft mereservasi stok',reference:'INV-260828-031',actor:'Nina',role:'Toko',happenedAt:'28 Agu 2026 · 16:05',result:'BERHASIL',reason:'Barang sudah diambil untuk invoice yang tetap terbuka sampai toko tutup.',impact:'Available-to-sell turun 24 pcs; stok fisik tidak diposting sebagai penjualan.',before:'Available 108 pcs',after:'Available 84 pcs · Reserved 24 pcs',sourceTime:'Tanggal fisik 28 Agu 2026 · Sistem 28 Agu 2026 16:05'},
  {id:'AUD-26870',priority:'P0',module:'Gudang',action:'Stock adjustment ditolak',reference:'ADJ-260828-009',actor:'Sistem',role:'Concurrency guard',happenedAt:'28 Agu 2026 · 15:51',result:'DIBLOKIR',reason:'expected row_version 18, data terbaru sudah version 19.',impact:'Tidak ada mutasi stok atau jurnal yang terbentuk.',before:'Request −12 pcs · row_version 18',after:'Diblokir · saldo tetap 96 pcs',sourceTime:'Request 28 Agu 2026 15:51 · Reject 28 Agu 2026 15:51'},
  {id:'AUD-26861',priority:'P0',module:'Payroll',action:'Pembayaran dibalik',reference:'PAY-260828-004',actor:'Owner',role:'Administrator',happenedAt:'28 Agu 2026 · 13:20',result:'DIBALIKKAN',reason:'Rekening pembayaran salah; akan dibayar ulang ke rekening Mandor.',impact:'Kas dikembalikan dan payroll payable dibuka lagi. Nota sumber tetap utuh.',before:'PAID · Mandiri Payroll −Rp18.740.000',after:'APPROVED · payable Rp18.740.000',sourceTime:'Tanggal bayar 28 Agu 2026 · Reversal 28 Agu 2026 13:20'},
  {id:'AUD-26844',priority:'P2',module:'Tutup Periode',action:'Preview close dijalankan',reference:'CLOSE-2026-08',actor:'Rina',role:'Keuangan',happenedAt:'28 Agu 2026 · 10:08',result:'DIBLOKIR',reason:'Validasi akhir bulan sebelum close.',impact:'Periode tetap OPEN; absensi belum lengkap dan antrean recost masih aktif.',before:'OPEN · 2 blocker',after:'OPEN · tidak ada transaksi berubah',sourceTime:'Periode ekonomi Agu 2026 · Preview 28 Agu 2026 10:08'},
]

export default function OperationsAdminPages({view,onNavigate}: OperationsAdminProps) {
  if (view === 'operations-attendance') return <AttendancePage onNavigate={onNavigate}/>
  if (view === 'admin-settings') return <SettingsPage onNavigate={onNavigate}/>
  if (view === 'admin-period-close') return <PeriodClosePage onNavigate={onNavigate}/>
  return <AuditTrailPage onNavigate={onNavigate}/>
}

function AdminHero({eyebrow,title,description,icon:Glyph,children}:{eyebrow:string;title:string;description:string;icon:typeof Settings2;children?:React.ReactNode}) {
  return <section className="ops-hero">
    <div><span>{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>
    {children ?? <aside><Glyph/><div><small>ERP CONTROL</small><strong>Versi & jejak perubahan</strong><em>Perubahan berisiko selalu butuh alasan.</em></div></aside>}
  </section>
}

function FixtureDisclosure({children}:{children:React.ReactNode}) {
  return <section className="admin-fixture-disclosure" role="note">
    <AlertTriangle/>
    <div><strong>DATA CONTOH · UX SIMULASI</strong><span>{children}</span></div>
  </section>
}

function SettingsPage({onNavigate}:{onNavigate:OperationsAdminProps['onNavigate']}) {
  const [editing,setEditing]=useState(false)
  const [effectiveDate,setEffectiveDate]=useState('2026-09-01')
  const [reason,setReason]=useState('')
  const [notice,setNotice]=useState('')
  const [settings,setSettings]=useState({reserveDraft:true,postedReversal:true,negativeCarry:true,halfDay:'0,5',closeCadence:'Bulanan · akhir bulan',timezone:'Asia/Jakarta'})
  const changePolicy=(key:'reserveDraft'|'postedReversal'|'negativeCarry')=>setSettings((current)=>({...current,[key]:!current[key]}))
  const saveVersion=()=>{
    if(!reason.trim())return
    setEditing(false);setNotice(`Versi pengaturan baru dijadwalkan efektif ${dateLabel(effectiveDate)}. Simulasi ini belum menulis backend.`);setReason('')
  }
  return <>
    <AdminHero eyebrow="PENGATURAN & AUDIT · SYSTEM POLICY" title="Pengaturan ERP yang bisa dipertanggungjawabkan" description="Rancang kebijakan operasional, nomor dokumen, dan akses dengan versi efektif. Nilai contoh di layar ini belum menjadi kebijakan aktif sampai adapter backend tersambung." icon={Settings2}>
      <aside><Settings2/><div><small>CONTOH SETTING VERSION</small><strong>Fixture v12 · efektif 29 Agu</strong><em>Bukan versi pengaturan dari backend.</em></div></aside>
    </AdminHero>
    <section className="ops-admin-tabs panel"><button className="active"><Settings2/> Pengaturan ERP</button><button onClick={()=>onNavigate('admin-period-close')}><LockKeyhole/> Tutup Periode</button><button onClick={()=>onNavigate('admin-audit')}><History/> Audit Trail</button></section>
    <FixtureDisclosure>Toggle, versi, effective date, format nomor, dan scope role di bawah adalah fixture untuk menguji alur. Halaman ini belum membaca atau menulis kebijakan Supabase; jangan gunakan nilainya sebagai konfigurasi aktif.</FixtureDisclosure>
    <section className="settings-layout">
      <main className="panel settings-main">
        <header><div><span>CONTOH KEBIJAKAN INTI</span><strong>Fixture aturan yang berdampak ke stok, payroll, dan histori</strong><small>Interaksi berikut hanya mengubah state lokal untuk mengecek UX effective-dated.</small></div><button className="soft-btn" onClick={()=>{setEditing((value)=>!value);setNotice('')}}>{editing?<XCircle/>:<SlidersHorizontal/>} {editing?'Batalkan':'Edit contoh'}</button></header>
        <div className="policy-list">
          <PolicyToggle title="Invoice Draft langsung reserve stok" description="Available-to-sell turun real time; batal Draft melepas reserve. Posting baru membentuk sale/AR." checked={settings.reserveDraft} disabled={!editing} onChange={()=>changePolicy('reserveDraft')} tone="stock"/>
          <PolicyToggle title="Kewajiban absensi mengikuti profil Mandor" description="contractors.attendance_required menentukan kewajiban absensi. Status dan rate Special tidak otomatis memberi pengecualian." checked disabled onChange={()=>undefined} tone="payroll"/>
          <PolicyToggle title="Posted hanya lewat reversal / correction" description="Tidak ada edit atau delete langsung untuk stock, invoice, payroll, jurnal, dan period close." checked={settings.postedReversal} disabled={!editing} onChange={()=>changePolicy('postedReversal')} tone="audit"/>
          <PolicyToggle title="Net payroll negatif dibawa ke depan" description="Kasbon dan potongan yang melebihi upah menjadi saldo Mandor, bukan dipaksa nol." checked={settings.negativeCarry} disabled={!editing} onChange={()=>changePolicy('negativeCarry')} tone="money"/>
        </div>
        <div className="settings-fields">
          <label><span>TIMEZONE BISNIS</span><select value={settings.timezone} disabled={!editing} onChange={(event)=>setSettings((current)=>({...current,timezone:event.target.value}))}><option>Asia/Jakarta</option></select><small>Tanggal fisik dan waktu sistem tetap disimpan terpisah.</small></label>
          <label><span>FAKTOR ½ HARI</span><input value={settings.halfDay} disabled={!editing} onChange={(event)=>setSettings((current)=>({...current,halfDay:event.target.value}))}/><small>1 hari + ½ hari = 1,5 unit bayar.</small></label>
          <label><span>RITME TUTUP BUKU</span><select value={settings.closeCadence} disabled={!editing} onChange={(event)=>setSettings((current)=>({...current,closeCadence:event.target.value}))}><option>Bulanan · akhir bulan</option><option>Custom fiscal period</option></select><small>Laporan harian tetap tersedia sebelum close.</small></label>
        </div>
        {editing&&<section className="settings-version-form"><label><span>BERLAKU MULAI</span><input type="date" value={effectiveDate} onChange={(event)=>setEffectiveDate(event.target.value)}/></label><label className="reason"><span>ALASAN PERUBAHAN · WAJIB</span><input value={reason} onChange={(event)=>setReason(event.target.value)} placeholder="Contoh: kebijakan operasional September..."/></label><button className="primary-btn" disabled={!reason.trim()} onClick={saveVersion}><Save/> Simpan contoh versi</button></section>}
        {notice&&<div className="ops-notice inline"><CheckCircle2/><span>{notice}</span></div>}
      </main>
      <aside className="settings-side">
        <section className="panel document-numbering"><header><div><span>NOMOR DOKUMEN · CONTOH</span><strong>Contoh format</strong></div><FileClock/></header><div><p><span>Invoice</span><strong>INV-YYMMDD-SEQ</strong></p><p><span>Nota FG</span><strong>NFG-YYMMDD-SEQ</strong></p><p><span>Payroll</span><strong>PAY-YYMM-SEQ</strong></p><p><span>Adjustment</span><strong>ADJ-YYMMDD-SEQ</strong></p></div><small>Target implementasi: backend membuat nomor saat posting agar idempotent. Format ini belum dibaca dari sumber live.</small></section>
        <section className="panel role-summary"><header><div><span>ROLE & AKSES · CONTOH</span><strong>Contoh scope</strong></div><KeyRound/></header><div><p><b>Owner / Admin</b><span>Approve, reversal, reopen, setting</span></p><p><b>Keuangan</b><span>AP, AR, payroll, close preview</span></p><p><b>Gudang</b><span>Receipt, issue, stock count</span></p><p><b>Toko</b><span>Invoice Draft, reserve, payment</span></p><p><b>QC</b><span>QC, BS, rework, FG handoff</span></p></div><button className="soft-btn" onClick={()=>setNotice('Ini preview scope role. Auth/RLS backend belum disambungkan dan belum ada akses live yang berubah.')}>Review contoh akses</button></section>
      </aside>
    </section>
  </>
}

function PolicyToggle({title,description,checked,disabled,onChange,tone}:{title:string;description:string;checked:boolean;disabled:boolean;onChange:()=>void;tone:string}) {
  return <article className={tone}><span className="policy-icon">{tone==='stock'?<ClipboardCheck/>:tone==='payroll'?<UsersRound/>:tone==='audit'?<ShieldCheck/>:<WalletCards/>}</span><div><strong>{title}</strong><small>{description}</small></div><label className="policy-switch"><input type="checkbox" checked={checked} disabled={disabled} onChange={onChange}/><i/><span>CONTOH · {checked?'AKTIF':'NONAKTIF'}</span></label></article>
}

function PeriodClosePage({onNavigate}:{onNavigate:OperationsAdminProps['onNavigate']}) {
  const [notice,setNotice]=useState('')
  const fixtureChecks=[
    {tone:'block',title:'Absensi belum lengkap',detail:'2 tanggal Draft belum diposting · Epi / Selo / Afat',owner:'Payroll'},
    {tone:'block',title:'Antrean HPP recalc aktif',detail:'1 invoice supplier terlambat memengaruhi RM → WIP → FG → COGS',owner:'Keuangan'},
    {tone:'warn',title:'Stock adjustment masih Draft',detail:'3 dokumen belum diposting atau dibatalkan',owner:'Gudang'},
    {tone:'warn',title:'GRNI belum menjadi invoice',detail:'3 receipt memakai harga estimate / benchmark',owner:'AP'},
    {tone:'clear',title:'Invoice penjualan sudah sinkron',detail:'Reserved, posted sale, retur, dan AR cocok',owner:'Toko'},
    {tone:'clear',title:'Payroll paid sudah rekonsiliasi',detail:'Reversal dan carry-forward tidak menggantung',owner:'Payroll'},
  ]
  return <>
    <AdminHero eyebrow="PENGATURAN & AUDIT · PERIOD CONTROL" title="Tutup Periode · contoh Agustus 2026" description="Prototype close bulanan setelah absensi, stok, HPP, AP/AR, dan payroll lolos validasi. Status dan pemeriksaan di layar ini belum berasal dari period-close backend." icon={LockKeyhole}>
      <aside className="close-status"><ShieldAlert/><div><small>STATUS CONTOH</small><strong>FIXTURE · OPEN · 2 BLOCKER</strong><em>Bukan status periode live.</em></div></aside>
    </AdminHero>
    <section className="ops-admin-tabs panel"><button onClick={()=>onNavigate('admin-settings')}><Settings2/> Pengaturan ERP</button><button className="active"><LockKeyhole/> Tutup Periode</button><button onClick={()=>onNavigate('admin-audit')}><History/> Audit Trail</button></section>
    <FixtureDisclosure>Periode Agustus 2026, enam pemeriksaan, dua blocker, nama dokumen, dan close sebelumnya adalah skenario contoh. Tombol hanya mendemokan UX; tidak ada query close-gate, posting, atau reopen ke backend.</FixtureDisclosure>
    <section className="close-overview">
      <main className="panel close-checks"><header><div><span>CLOSE GATE · CONTOH</span><strong>6 pemeriksaan fixture lintas modul</strong><small>UX target: blocker wajib nol; warning perlu alasan dan approval Owner.</small></div><button className="soft-btn" onClick={()=>setNotice('Preview contoh dijalankan ulang secara lokal. Tidak ada query atau transaksi backend.')}><RefreshCcw/> Jalankan ulang contoh</button></header><div>{fixtureChecks.map((item)=><article className={item.tone} key={item.title}><i>{item.tone==='clear'?<Check/>:item.tone==='block'?<XCircle/>:<AlertTriangle/>}</i><span><strong>{item.title}</strong><small>{item.detail}</small></span><b>CONTOH · {item.owner}</b></article>)}</div><footer><div><ShieldAlert/><span><strong>Contoh periode belum bisa ditutup</strong><small>Skenario fixture masih mempunyai 2 blocker.</small></span></div><button className="primary-btn" disabled><LockKeyhole/> Tutup contoh Agustus 2026</button></footer>{notice&&<div className="ops-notice inline"><CheckCircle2/><span>{notice}</span></div>}</main>
      <aside className="close-side">
        <section className="panel close-allocation"><header><div><span>CATATAN AUDIT · ATTENDANCE → HPP</span><strong>Bukan hasil close live</strong></div><WalletCards/></header><div><p><span>Attendance → payroll</span><b>Ditemukan pada audit skema</b></p><p><span>Alokasi biaya ke PO / SKU</span><b>Belum terverifikasi</b></p><p><span>Angka preview</span><b>Tidak dihitung</b></p></div><footer><span>STATUS HPP ABSENSI</span><strong>BELUM TERSEDIA</strong><small>Jangan close berdasarkan formula atau angka simulasi.</small></footer></section>
        <section className="panel late-document"><header><div><span>ATURAN TARGET · TAGIHAN TERLAMBAT</span><strong>Sesudah periode ditutup</strong></div><FileSearch/></header><p>Target flow: tanggal ekonomi asli tetap disimpan. Jurnal masuk ke hari pertama yang masih open; revisi angka closed hanya melalui explicit reopen dengan alasan.</p><div><Check/> Target: histori tidak berubah diam-diam</div><div><Check/> Target: recalc RM → WIP → FG → COGS terlacak</div></section>
        <section className="panel previous-close"><header><div><span>CONTOH PERIODE SEBELUMNYA</span><strong>Fixture · Juli 2026 · CLOSED</strong></div><LockKeyhole/></header><p>Contoh: ditutup 2 Agu 2026 · 21:14 oleh Owner</p><button className="soft-btn" onClick={()=>setNotice('Simulasi aturan reopen: alasan, impact preview, expected row_version, dan approval Owner kedua. Backend belum dipanggil.')}>Lihat contoh aturan reopen</button></section>
      </aside>
    </section>
  </>
}

function AuditTrailPage({onNavigate}:{onNavigate:OperationsAdminProps['onNavigate']}) {
  const [query,setQuery]=useState('')
  const [module,setModule]=useState('Semua modul')
  const [priority,setPriority]=useState('Semua prioritas')
  const [expanded,setExpanded]=useState<string[]>([auditExampleEvents[0].id])
  const [notice,setNotice]=useState('')
  const visible=useMemo(()=>auditExampleEvents.filter((event)=>{
    const haystack=`${event.id} ${event.module} ${event.action} ${event.reference} ${event.actor} ${event.reason}`.toLowerCase()
    return haystack.includes(query.toLowerCase())&&(module==='Semua modul'||event.module===module)&&(priority==='Semua prioritas'||event.priority===priority)
  }),[module,priority,query])
  const p0=auditExampleEvents.filter((event)=>event.priority==='P0').length
  const blocked=auditExampleEvents.filter((event)=>event.result==='DIBLOKIR').length
  return <>
    <AdminHero eyebrow="PENGATURAN & AUDIT · CONTOH EVENT LOG" title="Audit Trail untuk uang, stok, dan HPP" description="Prototype untuk menilai penelusuran actor, waktu, alasan, nilai sebelum–sesudah, dan hasil transaksi. Event di halaman ini bukan event backend aktual." icon={History}>
      <aside className="audit-immutable"><ShieldCheck/><div><small>TARGET · APPEND ONLY</small><strong>Contoh jejak immutable</strong><em>Belum dibaca dari audit log backend.</em></div></aside>
    </AdminHero>
    <section className="ops-admin-tabs panel"><button onClick={()=>onNavigate('admin-settings')}><Settings2/> Pengaturan ERP</button><button onClick={()=>onNavigate('admin-period-close')}><LockKeyhole/> Tutup Periode</button><button className="active"><History/> Audit Trail</button></section>
    <FixtureDisclosure>Enam event, ID dokumen, actor, timestamp, nilai uang/stok, hasil, dan seluruh metrik adalah fixture. Belum ada pembacaan audit table; status BERHASIL atau DIBLOKIR di sini bukan bukti guard backend berjalan.</FixtureDisclosure>
    <section className="ops-metrics audit-metrics"><article className="panel danger"><span>CONTOH P0 · UANG / STOK</span><strong>{p0} event contoh</strong><small>Skenario review Owner</small></article><article className="panel warn"><span>CONTOH WRITE DIBLOKIR</span><strong>{blocked} fixture</strong><small>Skenario guard, bukan bukti backend</small></article><article className="panel"><span>CONTOH REVERSAL</span><strong>1 fixture</strong><small>Target: dokumen asal tetap utuh</small></article><article className="panel good"><span>KELENGKAPAN FIXTURE</span><strong>6 / 6 contoh</strong><small>Actor, waktu, alasan, impact</small></article></section>
    <section className="panel audit-browser">
      <header className="audit-toolbar"><label className="audit-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari event contoh, user, aksi, alasan..."/></label><label><Filter/><select value={module} onChange={(event)=>setModule(event.target.value)}><option>Semua modul</option>{[...new Set(auditExampleEvents.map((event)=>event.module))].map((item)=><option key={item}>{item}</option>)}</select></label><label><ShieldAlert/><select value={priority} onChange={(event)=>setPriority(event.target.value)}><option>Semua prioritas</option><option>P0</option><option>P1</option><option>P2</option><option>TUNING</option></select></label><button className="soft-btn" onClick={()=>setNotice('Export belum tersedia: daftar ini fixture UX dan belum tersambung ke sumber audit backend.')}><FileSearch/> Export contoh</button></header>
      <div className="audit-priority-legend"><span><b>LEGENDA CONTOH</b></span><span><b>P0</b> uang, stok, HPP, AR/AP</span><span><b>P1</b> kontrol operasional</span><span><b>P2</b> kelengkapan proses</span><span><b>TUNING</b> kenyamanan UX</span></div>
      <div className="audit-list">{visible.map((event)=>{
        const open=expanded.includes(event.id)
        return <article key={event.id} className={`audit-event ${open?'open':''}`}>
          <button className="audit-event-head" onClick={()=>setExpanded((current)=>current.includes(event.id)?current.filter((id)=>id!==event.id):[...current,event.id])}>
            <span className={`audit-priority ${event.priority.toLowerCase()}`}>{event.priority}</span>
            <span className="audit-time"><Clock3/><span><strong>{event.happenedAt}</strong><small>{event.id}</small></span></span>
            <span className="audit-action"><small>EVENT CONTOH · {event.module}</small><strong>{event.action}</strong><em>{event.reference}</em></span>
            <span className="audit-actor"><UserRoundCog/><span><strong>{event.actor}</strong><small>{event.role}</small></span></span>
            <span className={`audit-result ${event.result.toLowerCase()}`}>{event.result}</span>
            {open?<ChevronDown/>:<ChevronRight/>}
          </button>
          {open&&<div className="audit-event-detail">
            <div className="audit-change"><article><span>SEBELUM</span><strong>{event.before}</strong></article><ArrowRight/><article><span>SESUDAH</span><strong>{event.after}</strong></article></div>
            <div className="audit-context"><article><span>ALASAN</span><p>{event.reason}</p></article><article><span>IMPACT</span><p>{event.impact}</p></article><article><span>TANGGAL & WAKTU</span><p>{event.sourceTime}</p></article></div>
          </div>}
        </article>
      })}{visible.length===0&&<div className="audit-empty"><Search/><strong>Event contoh tidak ditemukan</strong><small>Ubah pencarian atau filter fixture.</small></div>}</div>
      {notice&&<div className="ops-notice inline"><CheckCircle2/><span>{notice}</span><button onClick={()=>setNotice('')}><XCircle/></button></div>}
    </section>
  </>
}
