import { useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Check, CheckCircle2, ChevronDown,
  ChevronRight, ClipboardCheck, Clock3, Copy, FileClock, FileSearch, Filter,
  History, KeyRound, LockKeyhole, Plus, RefreshCcw, Save, Search, Settings2,
  ShieldAlert, ShieldCheck, SlidersHorizontal, Trash2, UserRoundCog, UsersRound,
  WalletCards, XCircle,
} from 'lucide-react'
import { cleanMoneyInput, formatMoneyInput } from './moneyInput'
import './operations-admin.css'

export type OperationsAdminView = 'operations-attendance' | 'admin-settings' | 'admin-period-close' | 'admin-audit'

type OperationsAdminProps = {
  view: OperationsAdminView
  onNavigate: (view: OperationsAdminView) => void
}

type AttendanceStatus = 'DRAFT' | 'POSTED'
type RateSource = 'DEFAULT' | 'OVERRIDE' | 'COPIED'
type AttendanceLine = {
  id: string
  contractor: 'Epi' | 'Selo' | 'Afat' | 'Afui'
  group: string
  special: boolean
  crew: number
  present: number
  half: number
  rate: number
  source: RateSource
  split?: boolean
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

const previousDate = (value: string) => {
  const date = new Date(`${value}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() - 1)
  return date.toISOString().slice(0, 10)
}

const baseAttendance = (): AttendanceLine[] => [
  { id:'epi-main', contractor:'Epi', group:'Rate utama', special:false, crew:12, present:11, half:1, rate:125_000, source:'DEFAULT' },
  { id:'selo-main', contractor:'Selo', group:'Rate utama', special:false, crew:14, present:13, half:0, rate:135_000, source:'DEFAULT' },
  { id:'afat-main', contractor:'Afat', group:'Rate utama', special:false, crew:18, present:17, half:1, rate:150_000, source:'DEFAULT' },
  { id:'afui-special', contractor:'Afui', group:'Mandor Special', special:true, crew:1, present:0, half:0, rate:0, source:'DEFAULT' },
]

const attendanceAmount = (line: AttendanceLine) => line.special ? 0 : Math.round((line.present + line.half * .5) * line.rate)
const absentCount = (line: AttendanceLine) => Math.max(0, line.crew - line.present - line.half)

const auditEvents: AuditEvent[] = [
  {id:'AUD-26882',priority:'P1',module:'Payroll',action:'Rate harian diubah',reference:'ABS-260829-AFAT',actor:'Owner',role:'Administrator',happenedAt:'29 Agu 2026 · 07:42',result:'BERHASIL',reason:'Tambahan rate untuk pekerjaan urgent hari ini.',impact:'Payroll harian +Rp85.000; snapshot tanggal sebelumnya tidak berubah.',before:'Afat · Rp150.000 / orang / hari',after:'Afat · Rp155.000 / orang / hari',sourceTime:'Tanggal kerja 29 Agu 2026 · Posting 29 Agu 2026 07:42'},
  {id:'AUD-26879',priority:'P1',module:'Master Data',action:'Flag Mandor Special aktif',reference:'MDR-AFUI',actor:'Owner',role:'Administrator',happenedAt:'28 Agu 2026 · 18:16',result:'BERHASIL',reason:'Afui tidak memakai absensi anak buah dan memakai harga special.',impact:'Afui dikecualikan dari pool absensi; harga SKU dan aksesori memakai kolom Special.',before:'Regular · absensi wajib',after:'Special · absensi dikecualikan',sourceTime:'Efektif 29 Agu 2026 · Dicatat 28 Agu 2026 18:16'},
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

function AttendancePage({onNavigate}:{onNavigate:OperationsAdminProps['onNavigate']}) {
  const [workDate,setWorkDate] = useState('2026-08-29')
  const [records,setRecords] = useState<Record<string,AttendanceLine[]>>({'2026-08-29':baseAttendance()})
  const [postedDates,setPostedDates] = useState<string[]>([])
  const [contractor,setContractor] = useState('Semua mandor')
  const [selected,setSelected] = useState<string[]>([])
  const [bulkRate,setBulkRate] = useState('')
  const [notice,setNotice] = useState('')
  const [splitSequence,setSplitSequence] = useState(1)
  const dayStatus: AttendanceStatus = postedDates.includes(workDate) ? 'POSTED' : 'DRAFT'
  const dayLines = records[workDate] ?? baseAttendance()
  const visibleLines = dayLines.filter((line)=>contractor==='Semua mandor'||line.contractor===contractor)
  const regularVisible = visibleLines.filter((line)=>!line.special)
  const selectedRegular = regularVisible.filter((line)=>selected.includes(line.id))
  const allVisibleSelected = regularVisible.length>0 && regularVisible.every((line)=>selected.includes(line.id))
  const dayTotal = dayLines.reduce((sum,line)=>sum+attendanceAmount(line),0)
  const paidUnits = dayLines.reduce((sum,line)=>sum+(line.special?0:line.present+line.half*.5),0)
  const missing = dayLines.filter((line)=>!line.special&&line.present+line.half+absentCount(line)!==line.crew).length
  const periodAttendance = 37_950_000
  const regularProduction = 7_240
  const attendanceHpp = Math.round(periodAttendance/regularProduction)
  const locked = dayStatus==='POSTED'

  const updateLines = (updater:(current:AttendanceLine[])=>AttendanceLine[]) => {
    if(locked)return
    setRecords((current)=>({...current,[workDate]:updater(current[workDate]??baseAttendance())}))
  }

  const updateLine = (id:string,patch:Partial<AttendanceLine>) => updateLines((current)=>current.map((line)=>line.id===id?{...line,...patch}:line))

  const changeCount = (line:AttendanceLine,key:'present'|'half',value:string) => {
    const next=Math.min(line.crew,Math.max(0,Math.round(Number(value)||0)))
    const other=key==='present'?line.half:line.present
    updateLine(line.id,{[key]:Math.min(next,Math.max(0,line.crew-other))} as Partial<AttendanceLine>)
  }

  const toggleAll = () => {
    if(allVisibleSelected)setSelected((current)=>current.filter((id)=>!regularVisible.some((line)=>line.id===id)))
    else setSelected((current)=>[...new Set([...current,...regularVisible.map((line)=>line.id)])])
  }

  const applyBulkRate = () => {
    const rate=Number(cleanMoneyInput(bulkRate))
    if(rate<=0||selectedRegular.length===0)return
    updateLines((current)=>current.map((line)=>selected.includes(line.id)&&!line.special?{...line,rate,source:'OVERRIDE'}:line))
    setNotice(`Rate ${money(rate)} diterapkan ke ${selectedRegular.length} baris pada ${dateLabel(workDate)}. Masih Draft.`)
    setBulkRate('')
  }

  const copyPreviousDay = () => {
    if(locked)return
    const sourceDate=previousDate(workDate)
    const source=(records[sourceDate]??baseAttendance()).map((line)=>({...line,source:line.special?'DEFAULT':'COPIED' as RateSource}))
    setRecords((current)=>({...current,[workDate]:source}))
    setSelected([])
    setNotice(`Absensi dan rate disalin dari ${dateLabel(sourceDate)}. Cek ulang lalu simpan Draft.`)
  }

  const splitRate = (line:AttendanceLine) => {
    if(locked||line.special||line.crew<=1)return
    const newId=`${line.contractor.toLowerCase()}-split-${splitSequence}`
    const newPresent=line.present>0?1:0
    const newHalf=newPresent===0&&line.half>0?1:0
    updateLines((current)=>current.flatMap((item)=>item.id!==line.id?[item]:[
      {...item,crew:item.crew-1,present:Math.max(0,item.present-newPresent),half:Math.max(0,item.half-newHalf)},
      {...item,id:newId,group:`Rate tambahan ${splitSequence}`,crew:1,present:newPresent,half:newHalf,source:'OVERRIDE',split:true},
    ]))
    setSplitSequence((value)=>value+1)
    setNotice(`Satu orang dipisah dari ${line.contractor}. Isi rate khusus tanpa mengubah anggota lain.`)
  }

  const removeSplit = (line:AttendanceLine) => {
    if(!line.split||locked)return
    updateLines((current)=>{
      const target=current.find((item)=>item.contractor===line.contractor&&!item.split)
      return current.filter((item)=>item.id!==line.id).map((item)=>item.id===target?.id?{
        ...item,crew:item.crew+line.crew,present:item.present+line.present,half:item.half+line.half,
      }:item)
    })
    setSelected((current)=>current.filter((id)=>id!==line.id))
  }

  const postDay = () => {
    setPostedDates((current)=>[...new Set([...current,workDate])])
    setSelected([])
    setNotice(`${dateLabel(workDate)} diposting dalam simulasi. Rate menjadi snapshot Payroll; koreksi berikutnya wajib adjustment/reversal.`)
  }

  return <>
    <AdminHero eyebrow="PAYROLL · ABSENSI & RATE HARIAN" title="Absensi harian tanpa bongkar Payroll" description="Catat kehadiran dan rate efektif pada tanggal kerja. Rate boleh berbeda tiap hari atau per orang, lalu dikunci sebagai snapshot saat diposting." icon={UsersRound}>
      <aside className="attendance-rule"><UsersRound/><div><small>MANDOR REGULAR</small><strong>Epi · Selo · Afat</strong><em>Afui / Special otomatis dikecualikan.</em></div></aside>
    </AdminHero>

    <section className="ops-metrics attendance-metrics">
      <article className="panel"><span>STATUS HARI INI</span><strong className={locked?'good-text':'warn-text'}>{dayStatus}</strong><small>{locked?'Snapshot payroll terkunci':'Boleh diedit sebelum posting'}</small></article>
      <article className="panel"><span>UNIT DIBAYAR</span><strong>{paidUnits.toLocaleString('id-ID')} hari</strong><small>Hadir + ½ hari × 0,5</small></article>
      <article className="panel"><span>NOMINAL HARI INI</span><strong>{money(dayTotal)}</strong><small>Belum mengubah kas</small></article>
      <article className="panel"><span>MANDOR SPECIAL</span><strong>Afui · Rp0</strong><small>Tidak ikut pool absensi</small></article>
    </section>

    <section className="panel attendance-workspace">
      <header className="attendance-toolbar">
        <div><span>INPUT PER TANGGAL</span><strong>{dateLabel(workDate)}</strong><small>Ubah rate di baris atau pilih beberapa baris sekaligus.</small></div>
        <div className="attendance-controls">
          <label><span>TANGGAL KERJA</span><input type="date" value={workDate} onChange={(event)=>{setWorkDate(event.target.value);setSelected([]);setNotice('')}}/></label>
          <label><span>MANDOR</span><select value={contractor} onChange={(event)=>{setContractor(event.target.value);setSelected([])}}><option>Semua mandor</option><option>Epi</option><option>Selo</option><option>Afat</option><option>Afui</option></select></label>
          <button className="soft-btn" disabled={locked} onClick={copyPreviousDay}><Copy/> Salin hari kemarin</button>
        </div>
      </header>

      <div className={`attendance-bulk ${selectedRegular.length>0?'active':''}`}>
        <label className="check-all"><input type="checkbox" checked={allVisibleSelected} onChange={toggleAll} disabled={locked||regularVisible.length===0}/><span><strong>{selectedRegular.length>0?`${selectedRegular.length} baris dipilih`:'Pilih semua yang tampil'}</strong><small>Boleh uncheck baris yang rate-nya tidak berubah.</small></span></label>
        <label className="bulk-money"><span>RATE BARU</span><div><b>Rp</b><input inputMode="numeric" value={formatMoneyInput(bulkRate)} onChange={(event)=>setBulkRate(cleanMoneyInput(event.target.value))} placeholder="150.000" disabled={locked}/></div></label>
        <button className="primary-btn" disabled={locked||selectedRegular.length===0||Number(cleanMoneyInput(bulkRate))<=0} onClick={applyBulkRate}><SlidersHorizontal/> Terapkan rate</button>
      </div>

      <div className="attendance-table-wrap">
        <table className="attendance-table">
          <thead><tr><th aria-label="Pilih"/><th>Mandor / kelompok rate</th><th>Anggota</th><th>Hadir</th><th>½ hari</th><th>Absen</th><th>Rate / orang / hari</th><th>Nominal</th><th/></tr></thead>
          <tbody>{visibleLines.map((line)=><tr key={line.id} className={`${line.special?'special':''} ${selected.includes(line.id)?'selected':''}`}>
            <td><input type="checkbox" checked={selected.includes(line.id)} disabled={locked||line.special} onChange={()=>setSelected((current)=>current.includes(line.id)?current.filter((id)=>id!==line.id):[...current,line.id])}/></td>
            <td><div className="attendance-identity"><span>{line.contractor.slice(0,2).toUpperCase()}</span><div><strong>Mandor {line.contractor}</strong><small>{line.group}</small></div>{line.special&&<em>SPECIAL</em>}</div></td>
            <td><strong className="tabular">{line.crew}</strong><small>orang</small></td>
            <td>{line.special?<span className="excluded-cell">—</span>:<input className="count-input" type="number" min="0" max={line.crew-line.half} value={line.present} disabled={locked} onChange={(event)=>changeCount(line,'present',event.target.value)}/>}</td>
            <td>{line.special?<span className="excluded-cell">—</span>:<input className="count-input" type="number" min="0" max={line.crew-line.present} value={line.half} disabled={locked} onChange={(event)=>changeCount(line,'half',event.target.value)}/>}</td>
            <td><strong className="tabular muted-number">{line.special?'—':absentCount(line)}</strong></td>
            <td>{line.special?<div className="special-rate"><strong>Rp0</strong><small>Tidak pakai absensi</small></div>:<div className="rate-input"><span>Rp</span><input inputMode="numeric" value={formatMoneyInput(line.rate)} disabled={locked} onChange={(event)=>updateLine(line.id,{rate:Number(cleanMoneyInput(event.target.value)),source:'OVERRIDE'})}/><em className={line.source.toLowerCase()}>{line.source==='DEFAULT'?'Master':line.source==='COPIED'?'Disalin':'Override'}</em></div>}</td>
            <td><strong className="line-total">{money(attendanceAmount(line))}</strong><small>{line.special?'Dikecualikan':`${line.present+line.half*.5} unit dibayar`}</small></td>
            <td>{!line.special&&(line.split?<button className="icon-action danger" aria-label="Hapus rate tambahan" disabled={locked} onClick={()=>removeSplit(line)}><Trash2/></button>:<button className="split-rate" disabled={locked||line.crew<=1} onClick={()=>splitRate(line)}><Plus/> Pecah rate</button>)}</td>
          </tr>)}</tbody>
        </table>
      </div>

      <footer className="attendance-footer">
        <div className={missing>0?'warn':''}>{missing>0?<AlertTriangle/>:<CheckCircle2/>}<span><strong>{missing>0?`${missing} kelompok belum seimbang`:'Jumlah orang sudah seimbang'}</strong><small>Hadir + ½ hari + absen harus sama dengan anggota.</small></span></div>
        <div className="attendance-actions">
          {locked?<button className="soft-btn" onClick={()=>setNotice('Buat Attendance Adjustment dengan alasan; snapshot posted tidak dibuka untuk edit langsung.')}><RefreshCcw/> Buat koreksi</button>:<button className="soft-btn" onClick={()=>setNotice(`Draft ${dateLabel(workDate)} tersimpan di browser. Backend belum berubah.`)}><Save/> Simpan Draft</button>}
          <button className="primary-btn" disabled={locked||missing>0} onClick={postDay}><LockKeyhole/> {locked?'Sudah diposting':'Post ke Payroll'}</button>
        </div>
      </footer>
      {notice&&<div className="ops-notice"><CheckCircle2/><span>{notice}</span><button aria-label="Tutup pemberitahuan" onClick={()=>setNotice('')}><XCircle/></button></div>}
    </section>

    <section className="attendance-lower-grid">
      <article className="panel allocation-preview">
        <header><div><span>PREVIEW ALOKASI HPP · AGUSTUS 2026</span><strong>Absensi regular dibagi ke produksi regular</strong></div><WalletCards/></header>
        <div className="allocation-formula"><span><small>POOL ABSENSI</small><strong>{money(periodAttendance)}</strong><em>Epi + Selo + Afat</em></span><b>÷</b><span><small>PRODUKSI ELIGIBLE</small><strong>{regularProduction.toLocaleString('id-ID')} pcs</strong><em>Afui tidak masuk pembagi</em></span><b>=</b><span className="result"><small>BIAYA ABSENSI / PCS</small><strong>{money(attendanceHpp)}</strong><em>Masuk versi HPP saat close</em></span></div>
        <p><ShieldCheck/> Komisi Special Afui sudah menempel di SKU, jadi tidak ditambah absensi lagi. Rate harian dan jumlah produksi disnapshot per periode.</p>
      </article>
      <article className="panel attendance-rules">
        <header><div><span>GUARDRAIL</span><strong>Supaya edit gampang tanpa merusak histori</strong></div><ShieldCheck/></header>
        <div><p><Check/> Draft bebas diedit sepanjang belum diposting.</p><p><Check/> Posting mengunci rate efektif per tanggal.</p><p><Check/> Salah posted dibuat adjustment/reversal dengan alasan.</p><p><Check/> Late input masuk periode terbuka atau explicit reopen.</p></div>
        <button className="soft-btn" onClick={()=>onNavigate('admin-period-close')}>Lihat Tutup Periode <ArrowRight/></button>
      </article>
    </section>
  </>
}

function SettingsPage({onNavigate}:{onNavigate:OperationsAdminProps['onNavigate']}) {
  const [editing,setEditing]=useState(false)
  const [effectiveDate,setEffectiveDate]=useState('2026-09-01')
  const [reason,setReason]=useState('')
  const [notice,setNotice]=useState('')
  const [settings,setSettings]=useState({reserveDraft:true,excludeSpecial:true,postedReversal:true,negativeCarry:true,halfDay:'0,5',closeCadence:'Bulanan · akhir bulan',timezone:'Asia/Jakarta'})
  const changePolicy=(key:'reserveDraft'|'excludeSpecial'|'postedReversal'|'negativeCarry')=>setSettings((current)=>({...current,[key]:!current[key]}))
  const saveVersion=()=>{
    if(!reason.trim())return
    setEditing(false);setNotice(`Versi pengaturan baru dijadwalkan efektif ${dateLabel(effectiveDate)}. Simulasi ini belum menulis backend.`);setReason('')
  }
  return <>
    <AdminHero eyebrow="PENGATURAN & AUDIT · SYSTEM POLICY" title="Pengaturan ERP yang bisa dipertanggungjawabkan" description="Atur kebijakan operasional, nomor dokumen, dan akses. Setiap perubahan membuat versi baru; transaksi posted dan snapshot lama tidak ikut ditulis ulang." icon={Settings2}>
      <aside><Settings2/><div><small>SETTING VERSION</small><strong>v12 · efektif 29 Agu</strong><em>Perubahan berikutnya wajib alasan.</em></div></aside>
    </AdminHero>
    <section className="ops-admin-tabs panel"><button className="active"><Settings2/> Pengaturan ERP</button><button onClick={()=>onNavigate('admin-period-close')}><LockKeyhole/> Tutup Periode</button><button onClick={()=>onNavigate('admin-audit')}><History/> Audit Trail</button></section>
    <section className="settings-layout">
      <main className="panel settings-main">
        <header><div><span>KEBIJAKAN INTI</span><strong>Aturan yang berdampak ke stok, payroll, dan histori</strong><small>Toggle hanya dapat diubah dalam mode Edit dan tetap memerlukan effective date.</small></div><button className="soft-btn" onClick={()=>{setEditing((value)=>!value);setNotice('')}}>{editing?<XCircle/>:<SlidersHorizontal/>} {editing?'Batalkan':'Edit kebijakan'}</button></header>
        <div className="policy-list">
          <PolicyToggle title="Invoice Draft langsung reserve stok" description="Available-to-sell turun real time; batal Draft melepas reserve. Posting baru membentuk sale/AR." checked={settings.reserveDraft} disabled={!editing} onChange={()=>changePolicy('reserveDraft')} tone="stock"/>
          <PolicyToggle title="Mandor Special tidak ikut absensi" description="Afui dan Mandor lain yang dicentang Special memakai harga SKU/aksesori Special, tanpa pool attendance." checked={settings.excludeSpecial} disabled={!editing} onChange={()=>changePolicy('excludeSpecial')} tone="payroll"/>
          <PolicyToggle title="Posted hanya lewat reversal / correction" description="Tidak ada edit atau delete langsung untuk stock, invoice, payroll, jurnal, dan period close." checked={settings.postedReversal} disabled={!editing} onChange={()=>changePolicy('postedReversal')} tone="audit"/>
          <PolicyToggle title="Net payroll negatif dibawa ke depan" description="Kasbon dan potongan yang melebihi upah menjadi saldo Mandor, bukan dipaksa nol." checked={settings.negativeCarry} disabled={!editing} onChange={()=>changePolicy('negativeCarry')} tone="money"/>
        </div>
        <div className="settings-fields">
          <label><span>TIMEZONE BISNIS</span><select value={settings.timezone} disabled={!editing} onChange={(event)=>setSettings((current)=>({...current,timezone:event.target.value}))}><option>Asia/Jakarta</option></select><small>Tanggal fisik dan waktu sistem tetap disimpan terpisah.</small></label>
          <label><span>FAKTOR ½ HARI</span><input value={settings.halfDay} disabled={!editing} onChange={(event)=>setSettings((current)=>({...current,halfDay:event.target.value}))}/><small>1 hari + ½ hari = 1,5 unit bayar.</small></label>
          <label><span>RITME TUTUP BUKU</span><select value={settings.closeCadence} disabled={!editing} onChange={(event)=>setSettings((current)=>({...current,closeCadence:event.target.value}))}><option>Bulanan · akhir bulan</option><option>Custom fiscal period</option></select><small>Laporan harian tetap tersedia sebelum close.</small></label>
        </div>
        {editing&&<section className="settings-version-form"><label><span>BERLAKU MULAI</span><input type="date" value={effectiveDate} onChange={(event)=>setEffectiveDate(event.target.value)}/></label><label className="reason"><span>ALASAN PERUBAHAN · WAJIB</span><input value={reason} onChange={(event)=>setReason(event.target.value)} placeholder="Contoh: kebijakan operasional September..."/></label><button className="primary-btn" disabled={!reason.trim()} onClick={saveVersion}><Save/> Simpan versi baru</button></section>}
        {notice&&<div className="ops-notice inline"><CheckCircle2/><span>{notice}</span></div>}
      </main>
      <aside className="settings-side">
        <section className="panel document-numbering"><header><div><span>NOMOR DOKUMEN</span><strong>Format aktif</strong></div><FileClock/></header><div><p><span>Invoice</span><strong>INV-YYMMDD-SEQ</strong></p><p><span>Nota FG</span><strong>NFG-YYMMDD-SEQ</strong></p><p><span>Payroll</span><strong>PAY-YYMM-SEQ</strong></p><p><span>Adjustment</span><strong>ADJ-YYMMDD-SEQ</strong></p></div><small>Nomor dibuat backend saat posting agar tidak dobel akibat klik ulang.</small></section>
        <section className="panel role-summary"><header><div><span>ROLE & AKSES</span><strong>Scope aktif</strong></div><KeyRound/></header><div><p><b>Owner / Admin</b><span>Approve, reversal, reopen, setting</span></p><p><b>Keuangan</b><span>AP, AR, payroll, close preview</span></p><p><b>Gudang</b><span>Receipt, issue, stock count</span></p><p><b>Toko</b><span>Invoice Draft, reserve, payment</span></p><p><b>QC</b><span>QC, BS, rework, FG handoff</span></p></div><button className="soft-btn" onClick={()=>setNotice('Detail Role & Akses siap dijadikan writer setelah Auth/RLS backend disambungkan.')}>Review akses</button></section>
      </aside>
    </section>
  </>
}

function PolicyToggle({title,description,checked,disabled,onChange,tone}:{title:string;description:string;checked:boolean;disabled:boolean;onChange:()=>void;tone:string}) {
  return <article className={tone}><span className="policy-icon">{tone==='stock'?<ClipboardCheck/>:tone==='payroll'?<UsersRound/>:tone==='audit'?<ShieldCheck/>:<WalletCards/>}</span><div><strong>{title}</strong><small>{description}</small></div><label className="policy-switch"><input type="checkbox" checked={checked} disabled={disabled} onChange={onChange}/><i/><span>{checked?'AKTIF':'NONAKTIF'}</span></label></article>
}

function PeriodClosePage({onNavigate}:{onNavigate:OperationsAdminProps['onNavigate']}) {
  const [notice,setNotice]=useState('')
  const checks=[
    {tone:'block',title:'Absensi belum lengkap',detail:'2 tanggal Draft belum diposting · Epi / Selo / Afat',owner:'Payroll'},
    {tone:'block',title:'Antrean HPP recalc aktif',detail:'1 invoice supplier terlambat memengaruhi RM → WIP → FG → COGS',owner:'Keuangan'},
    {tone:'warn',title:'Stock adjustment masih Draft',detail:'3 dokumen belum diposting atau dibatalkan',owner:'Gudang'},
    {tone:'warn',title:'GRNI belum menjadi invoice',detail:'3 receipt memakai harga estimate / benchmark',owner:'AP'},
    {tone:'clear',title:'Invoice penjualan sudah sinkron',detail:'Reserved, posted sale, retur, dan AR cocok',owner:'Toko'},
    {tone:'clear',title:'Payroll paid sudah rekonsiliasi',detail:'Reversal dan carry-forward tidak menggantung',owner:'Payroll'},
  ]
  return <>
    <AdminHero eyebrow="PENGATURAN & AUDIT · PERIOD CONTROL" title="Tutup Periode Agustus 2026" description="Close dilakukan bulanan setelah absensi, stok, HPP, AP/AR, dan payroll lolos validasi. Preview tidak mengubah transaksi." icon={LockKeyhole}>
      <aside className="close-status"><ShieldAlert/><div><small>STATUS PERIODE</small><strong>OPEN · 2 BLOCKER</strong><em>Belum aman untuk ditutup.</em></div></aside>
    </AdminHero>
    <section className="ops-admin-tabs panel"><button onClick={()=>onNavigate('admin-settings')}><Settings2/> Pengaturan ERP</button><button className="active"><LockKeyhole/> Tutup Periode</button><button onClick={()=>onNavigate('admin-audit')}><History/> Audit Trail</button></section>
    <section className="close-overview">
      <main className="panel close-checks"><header><div><span>CLOSE GATE</span><strong>6 pemeriksaan lintas modul</strong><small>Blocker wajib nol. Warning boleh lanjut hanya dengan alasan dan approval Owner.</small></div><button className="soft-btn" onClick={()=>setNotice('Preview dijalankan ulang 29 Agu 2026 · 08:12. Simulasi tidak mengubah data.')}><RefreshCcw/> Jalankan ulang</button></header><div>{checks.map((item)=><article className={item.tone} key={item.title}><i>{item.tone==='clear'?<Check/>:item.tone==='block'?<XCircle/>:<AlertTriangle/>}</i><span><strong>{item.title}</strong><small>{item.detail}</small></span><b>{item.owner}</b></article>)}</div><footer><div><ShieldAlert/><span><strong>Periode belum bisa ditutup</strong><small>Selesaikan 2 blocker lalu jalankan preview ulang.</small></span></div><button className="primary-btn" disabled><LockKeyhole/> Tutup Agustus 2026</button></footer>{notice&&<div className="ops-notice inline"><CheckCircle2/><span>{notice}</span></div>}</main>
      <aside className="close-side">
        <section className="panel close-allocation"><header><div><span>ATTENDANCE → HPP</span><strong>Preview alokasi regular</strong></div><WalletCards/></header><div><p><span>Pool absensi</span><b>{money(37_950_000)}</b></p><p><span>Produksi Epi + Selo + Afat</span><b>7.240 pcs</b></p><p><span>Afui / Special</span><b>Dikecualikan</b></p></div><footer><span>BIAYA ABSENSI / PCS</span><strong>{money(Math.round(37_950_000/7_240))}</strong><small>Membentuk versi HPP baru saat close.</small></footer></section>
        <section className="panel late-document"><header><div><span>TAGIHAN TERLAMBAT</span><strong>Sesudah periode ditutup</strong></div><FileSearch/></header><p>Tanggal ekonomi asli tetap disimpan. Jurnal masuk ke hari pertama yang masih open; kalau angka closed harus direvisi, hanya Owner yang dapat explicit reopen dengan alasan.</p><div><Check/> Tidak mengubah histori diam-diam</div><div><Check/> Recalc RM → WIP → FG → COGS tetap terlacak</div></section>
        <section className="panel previous-close"><header><div><span>PERIODE SEBELUMNYA</span><strong>Juli 2026 · CLOSED</strong></div><LockKeyhole/></header><p>Ditutup 2 Agu 2026 · 21:14 oleh Owner</p><button className="soft-btn" onClick={()=>setNotice('Permintaan reopen wajib alasan, impact preview, expected row_version, dan approval Owner kedua.')}>Lihat aturan reopen</button></section>
      </aside>
    </section>
  </>
}

function AuditTrailPage({onNavigate}:{onNavigate:OperationsAdminProps['onNavigate']}) {
  const [query,setQuery]=useState('')
  const [module,setModule]=useState('Semua modul')
  const [priority,setPriority]=useState('Semua prioritas')
  const [expanded,setExpanded]=useState<string[]>([auditEvents[0].id])
  const [notice,setNotice]=useState('')
  const visible=useMemo(()=>auditEvents.filter((event)=>{
    const haystack=`${event.id} ${event.module} ${event.action} ${event.reference} ${event.actor} ${event.reason}`.toLowerCase()
    return haystack.includes(query.toLowerCase())&&(module==='Semua modul'||event.module===module)&&(priority==='Semua prioritas'||event.priority===priority)
  }),[module,priority,query])
  const p0=auditEvents.filter((event)=>event.priority==='P0').length
  const blocked=auditEvents.filter((event)=>event.result==='DIBLOKIR').length
  return <>
    <AdminHero eyebrow="PENGATURAN & AUDIT · IMMUTABLE EVENT LOG" title="Audit Trail untuk uang, stok, dan HPP" description="Telusuri siapa melakukan apa, kapan, alasan, nilai sebelum–sesudah, dan apakah backend menerima, menolak, atau membalikkan transaksi." icon={History}>
      <aside className="audit-immutable"><ShieldCheck/><div><small>APPEND ONLY</small><strong>Jejak tidak dapat diedit</strong><em>Koreksi menjadi event baru yang tertaut.</em></div></aside>
    </AdminHero>
    <section className="ops-admin-tabs panel"><button onClick={()=>onNavigate('admin-settings')}><Settings2/> Pengaturan ERP</button><button onClick={()=>onNavigate('admin-period-close')}><LockKeyhole/> Tutup Periode</button><button className="active"><History/> Audit Trail</button></section>
    <section className="ops-metrics audit-metrics"><article className="panel danger"><span>P0 · UANG / STOK</span><strong>{p0} event</strong><small>Butuh review Owner</small></article><article className="panel warn"><span>WRITE DIBLOKIR</span><strong>{blocked}</strong><small>Guard backend bekerja</small></article><article className="panel"><span>REVERSAL</span><strong>1</strong><small>Dokumen asal tetap utuh</small></article><article className="panel good"><span>JEJAK LENGKAP</span><strong>6 / 6</strong><small>Actor, waktu, alasan, impact</small></article></section>
    <section className="panel audit-browser">
      <header className="audit-toolbar"><label className="audit-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari nomor dokumen, user, aksi, alasan..."/></label><label><Filter/><select value={module} onChange={(event)=>setModule(event.target.value)}><option>Semua modul</option>{[...new Set(auditEvents.map((event)=>event.module))].map((item)=><option key={item}>{item}</option>)}</select></label><label><ShieldAlert/><select value={priority} onChange={(event)=>setPriority(event.target.value)}><option>Semua prioritas</option><option>P0</option><option>P1</option><option>P2</option><option>TUNING</option></select></label><button className="soft-btn" onClick={()=>setNotice('Export audit disiapkan dari backend dengan filter aktif; file belum dibuat pada UX simulasi.')}><FileSearch/> Export</button></header>
      <div className="audit-priority-legend"><span><b>P0</b> uang, stok, HPP, AR/AP</span><span><b>P1</b> kontrol operasional</span><span><b>P2</b> kelengkapan proses</span><span><b>TUNING</b> kenyamanan UX</span></div>
      <div className="audit-list">{visible.map((event)=>{
        const open=expanded.includes(event.id)
        return <article key={event.id} className={`audit-event ${open?'open':''}`}>
          <button className="audit-event-head" onClick={()=>setExpanded((current)=>current.includes(event.id)?current.filter((id)=>id!==event.id):[...current,event.id])}>
            <span className={`audit-priority ${event.priority.toLowerCase()}`}>{event.priority}</span>
            <span className="audit-time"><Clock3/><span><strong>{event.happenedAt}</strong><small>{event.id}</small></span></span>
            <span className="audit-action"><small>{event.module}</small><strong>{event.action}</strong><em>{event.reference}</em></span>
            <span className="audit-actor"><UserRoundCog/><span><strong>{event.actor}</strong><small>{event.role}</small></span></span>
            <span className={`audit-result ${event.result.toLowerCase()}`}>{event.result}</span>
            {open?<ChevronDown/>:<ChevronRight/>}
          </button>
          {open&&<div className="audit-event-detail">
            <div className="audit-change"><article><span>SEBELUM</span><strong>{event.before}</strong></article><ArrowRight/><article><span>SESUDAH</span><strong>{event.after}</strong></article></div>
            <div className="audit-context"><article><span>ALASAN</span><p>{event.reason}</p></article><article><span>IMPACT</span><p>{event.impact}</p></article><article><span>TANGGAL & WAKTU</span><p>{event.sourceTime}</p></article></div>
          </div>}
        </article>
      })}{visible.length===0&&<div className="audit-empty"><Search/><strong>Event tidak ditemukan</strong><small>Ubah pencarian atau filter.</small></div>}</div>
      {notice&&<div className="ops-notice inline"><CheckCircle2/><span>{notice}</span><button onClick={()=>setNotice('')}><XCircle/></button></div>}
    </section>
  </>
}
