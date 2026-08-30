import { useMemo, useState, type FormEvent } from 'react'
import {
  AlertTriangle,
  Banknote,
  CalendarDays,
  Check,
  CheckCircle2,
  ClipboardCheck,
  Copy,
  History,
  LockKeyhole,
  Pencil,
  Plus,
  RefreshCcw,
  Save,
  ShieldCheck,
  Undo2,
  UserRound,
  UsersRound,
  X,
  XCircle,
} from 'lucide-react'
import { cleanMoneyInput, formatMoneyInput } from '../moneyInput'
import {
  addRateVersion,
  applyBulkAttendance,
  attendanceEntryAmount,
  attendanceKey,
  canMutateAttendance,
  datesBetween,
  deactivateWorker,
  indonesianDayDate,
  initialRateCoversEmploymentStart,
  previewBulkAttendance,
  rateForDate,
  reactivateWorker,
  shiftDate,
  snapshotAttendanceRates,
  workerEmploymentStatusOn,
  workerIsActive,
  workerIsEligibleOn,
  type AttendanceBook,
  type AttendanceMark,
  type AttendancePeriodStatus,
  type BulkAttendanceAction,
  type BulkAttendancePreview,
  type Contractor,
  type Worker,
  type WorkerEmploymentPeriod,
  type WorkerRateVersion,
} from './domain'

type AttendancePageProps = {
  onNavigate: (view: 'admin-period-close') => void
}

type WorkerEditor = {
  workerId: string | null
  name: string
  jobDescription: string
  dailyRate: string
  effectiveFrom: string
  startDate: string
  endDate: string
  notes: string
  changeReason: string
}

type RateEditor = {
  workerId: string
  dailyRate: string
  effectiveFrom: string
  reason: string
}

type EmploymentEditor = {
  workerId: string
  action: 'DEACTIVATE' | 'REACTIVATE'
  effectiveDate: string
  reason: string
}

const CONTRACTORS: Contractor[] = [
  {id: 'epi', name: 'Epi', attendanceRequired: true},
  {id: 'selo', name: 'Selo', attendanceRequired: true},
  {id: 'afat', name: 'Afat', attendanceRequired: true},
  {
    id: 'afui',
    name: 'Afui',
    attendanceRequired: false,
    attendancePolicyReason: 'Contoh data canonical: attendance_required=false. Status/rate Special adalah aturan terpisah.',
  },
]

const employment = (
  id: string,
  workerId: string,
  effectiveFrom: string,
  effectiveTo: string | null,
  reason = 'Masuk roster awal · simulasi',
  endReason?: string,
): WorkerEmploymentPeriod => ({
  id,
  workerId,
  effectiveFrom,
  effectiveTo,
  reason,
  changedBy: 'Owner · simulasi',
  changedAt: `${effectiveFrom}T00:00:00Z`,
  endReason,
  endedBy: endReason ? 'Owner · simulasi' : undefined,
  endedAt: endReason && effectiveTo ? `${effectiveTo}T00:00:00Z` : undefined,
})

const INITIAL_WORKERS: Worker[] = [
  {id: 'wrk-epi-001', contractorId: 'epi', name: 'Dedi', jobDescription: 'Jahit badan', employmentPeriods: [employment('emp-epi-001-a', 'wrk-epi-001', '2026-02-10', null)], notes: 'Tim utama'},
  {id: 'wrk-epi-002', contractorId: 'epi', name: 'Rian', jobDescription: 'Pasang pinggang', employmentPeriods: [
    employment('emp-epi-002-a', 'wrk-epi-002', '2026-06-01', '2026-08-20', 'Masuk roster awal · simulasi', 'Sempat berhenti'),
    employment('emp-epi-002-b', 'wrk-epi-002', '2026-08-26', null, 'Aktif kembali hari Rabu · simulasi'),
  ], notes: 'Aktif kembali hari Rabu; gap lama tetap tersimpan'},
  {id: 'wrk-epi-003', contractorId: 'epi', name: 'Maman', jobDescription: 'Finishing jahit', employmentPeriods: [employment('emp-epi-003-a', 'wrk-epi-003', '2026-05-03', '2026-08-28', 'Masuk roster awal · simulasi', 'Berhenti dari tim')], notes: 'Sudah berhenti'},
  {id: 'wrk-selo-001', contractorId: 'selo', name: 'Asep', jobDescription: 'Jahit badan', employmentPeriods: [employment('emp-selo-001-a', 'wrk-selo-001', '2026-01-18', null)], notes: ''},
  {id: 'wrk-selo-002', contractorId: 'selo', name: 'Nia', jobDescription: 'Lubang kancing', employmentPeriods: [employment('emp-selo-002-a', 'wrk-selo-002', '2026-04-12', null)], notes: ''},
  {id: 'wrk-afat-001', contractorId: 'afat', name: 'Ujang', jobDescription: 'Obras', employmentPeriods: [employment('emp-afat-001-a', 'wrk-afat-001', '2026-03-07', null)], notes: ''},
  {id: 'wrk-afat-002', contractorId: 'afat', name: 'Yani', jobDescription: 'Quality helper', employmentPeriods: [employment('emp-afat-002-a', 'wrk-afat-002', '2026-07-11', null)], notes: ''},
]

const rate = (
  id: string,
  workerId: string,
  dailyRate: number,
  effectiveFrom: string,
  effectiveTo: string | null,
  reason = 'Rate awal roster simulasi',
): WorkerRateVersion => ({
  id,
  workerId,
  dailyRate,
  effectiveFrom,
  effectiveTo,
  reason,
  changedBy: 'Owner · simulasi',
  changedAt: `${effectiveFrom}T00:00:00Z`,
})

const INITIAL_RATES: WorkerRateVersion[] = [
  rate('rate-epi-001-a', 'wrk-epi-001', 125_000, '2026-02-10', null),
  rate('rate-epi-002-a', 'wrk-epi-002', 100_000, '2026-08-26', '2026-08-27'),
  rate('rate-epi-002-b', 'wrk-epi-002', 115_000, '2026-08-28', null, 'Perubahan rate efektif di tengah periode'),
  rate('rate-epi-003-a', 'wrk-epi-003', 110_000, '2026-05-03', null),
  rate('rate-selo-001-a', 'wrk-selo-001', 135_000, '2026-01-18', null),
  rate('rate-selo-002-a', 'wrk-selo-002', 120_000, '2026-04-12', null),
  rate('rate-afat-001-a', 'wrk-afat-001', 150_000, '2026-03-07', null),
  rate('rate-afat-002-a', 'wrk-afat-002', 105_000, '2026-07-11', null),
]

const HOLIDAYS: Record<string, string> = {
  '2026-08-30': 'Libur mingguan · contoh kebijakan',
}

const money = (value: number) => new Intl.NumberFormat('id-ID', {
  style: 'currency',
  currency: 'IDR',
  maximumFractionDigits: 0,
}).format(value)

const shortDate = (value: string) => {
  const date = new Date(`${value}T00:00:00Z`)
  if (Number.isNaN(date.getTime())) return 'Belum dipilih'
  return new Intl.DateTimeFormat('id-ID', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(date)
}

const emptyWorkerEditor = (startDate: string): WorkerEditor => ({
  workerId: null,
  name: '',
  jobDescription: '',
  dailyRate: '',
  effectiveFrom: startDate,
  startDate,
  endDate: '',
  notes: '',
  changeReason: '',
})

const bulkLabel: Record<BulkAttendanceAction, string> = {
  MARK_ALL_PRESENT: 'Tandai semua hadir',
  CLEAR: 'Kosongkan isian',
  COPY_PREVIOUS_WEEK: 'Salin minggu sebelumnya',
}

export default function AttendancePage({onNavigate}: AttendancePageProps) {
  const [contractors] = useState<Contractor[]>(CONTRACTORS)
  const [workers, setWorkers] = useState<Worker[]>(() => INITIAL_WORKERS)
  const [rates, setRates] = useState<WorkerRateVersion[]>(() => INITIAL_RATES)
  const [books, setBooks] = useState<Record<string, AttendanceBook>>({})
  const [selectedContractorId, setSelectedContractorId] = useState('epi')
  const [periodStart, setPeriodStart] = useState('2026-08-24')
  const [periodEnd, setPeriodEnd] = useState('2026-08-30')
  const [periodPayDates, setPeriodPayDates] = useState<Record<string, string>>({})
  const [periodStatuses, setPeriodStatuses] = useState<Record<string, AttendancePeriodStatus>>({})
  const [showInactive, setShowInactive] = useState(false)
  const [bulkPreview, setBulkPreview] = useState<BulkAttendancePreview | null>(null)
  const [workerEditor, setWorkerEditor] = useState<WorkerEditor | null>(null)
  const [rateEditor, setRateEditor] = useState<RateEditor | null>(null)
  const [employmentEditor, setEmploymentEditor] = useState<EmploymentEditor | null>(null)
  const [amendment, setAmendment] = useState<{kind: 'CORRECTION' | 'REVERSAL'; reason: string} | null>(null)
  const [notice, setNotice] = useState('')
  const [formError, setFormError] = useState('')
  const [workerSequence, setWorkerSequence] = useState(8)

  const selectedContractor = contractors.find((contractor) => contractor.id === selectedContractorId) ?? contractors[0]
  const periodKey = `${selectedContractorId}::${periodStart}::${periodEnd}`
  const payDate = periodPayDates[periodKey] ?? '2026-08-31'
  const periodStatus: AttendancePeriodStatus = periodStatuses[periodKey] ?? 'DRAFT'
  const book = books[periodKey] ?? {}
  const workDates = useMemo(() => datesBetween(periodStart, periodEnd), [periodEnd, periodStart])
  const contractorWorkers = useMemo(
    () => workers.filter((worker) => worker.contractorId === selectedContractorId),
    [selectedContractorId, workers],
  )
  const visibleWorkers = useMemo(
    () => contractorWorkers.filter((worker) => showInactive || workerIsActive(worker)),
    [contractorWorkers, showInactive],
  )
  const mutable = canMutateAttendance(periodStatus)
  const holidayDates = workDates.filter((date) => Boolean(HOLIDAYS[date]))
  const latestLockedPeriodEnd = useMemo(() => Object.entries(periodStatuses)
    .filter(([key, status]) => key.startsWith(`${selectedContractorId}::`) && status !== 'DRAFT')
    .map(([key]) => key.split('::')[2])
    .filter(Boolean)
    .sort()
    .at(-1), [periodStatuses, selectedContractorId])

  const periodTotals = useMemo(() => {
    let eligibleCells = 0
    let recordedCells = 0
    let presentDays = 0
    let nominal = 0
    let uncoveredRateCells = 0
    for (const worker of contractorWorkers) {
      for (const workDate of workDates) {
        if (!workerIsEligibleOn(worker, selectedContractor, workDate)) continue
        eligibleCells += 1
        if (!rateForDate(worker.id, workDate, rates)) uncoveredRateCells += 1
        const entry = book[attendanceKey(worker.id, workDate)]
        if (!entry) continue
        recordedCells += 1
        if (entry.mark === 'PRESENT') presentDays += 1
        nominal += attendanceEntryAmount(entry, rates)
      }
    }
    return {eligibleCells, recordedCells, presentDays, nominal, uncoveredRateCells, missingCells: eligibleCells - recordedCells}
  }, [book, contractorWorkers, rates, selectedContractor, workDates])

  const setAttendance = (worker: Worker, workDate: string, mark?: AttendanceMark) => {
    if (!mutable || !workerIsEligibleOn(worker, selectedContractor, workDate)) return
    const key = attendanceKey(worker.id, workDate)
    setBooks((allBooks) => {
      const current = allBooks[periodKey] ?? {}
      const next = {...current}
      if (mark) next[key] = {workerId: worker.id, workDate, mark}
      else delete next[key]
      return {...allBooks, [periodKey]: next}
    })
    setBulkPreview(null)
  }

  const prepareBulk = (action: BulkAttendanceAction) => {
    if (!mutable || !selectedContractor.attendanceRequired) return
    setBulkPreview(previewBulkAttendance({
      action,
      workers: visibleWorkers,
      contractors,
      workDates,
      rates,
      book,
      excludedBulkDates: action === 'MARK_ALL_PRESENT' ? holidayDates : [],
    }))
  }

  const confirmBulk = () => {
    if (!bulkPreview || !mutable) return
    setBooks((allBooks) => ({
      ...allBooks,
      [periodKey]: applyBulkAttendance(allBooks[periodKey] ?? {}, bulkPreview),
    }))
    setNotice(`${bulkLabel[bulkPreview.action]} diterapkan ke ${bulkPreview.affectedCells} isian. Masih Draft lokal; backend belum berubah.`)
    setBulkPreview(null)
  }

  const openAddWorker = () => {
    setWorkerEditor(emptyWorkerEditor(periodStart))
    setRateEditor(null)
    setEmploymentEditor(null)
    setFormError('')
  }

  const openEditWorker = (worker: Worker) => {
    setWorkerEditor({
      workerId: worker.id,
      name: worker.name,
      jobDescription: worker.jobDescription,
      dailyRate: '',
      effectiveFrom: periodStart,
      startDate: '',
      endDate: '',
      notes: worker.notes,
      changeReason: '',
    })
    setRateEditor(null)
    setEmploymentEditor(null)
    setFormError('')
  }

  const saveWorker = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!workerEditor) return
    const name = workerEditor.name.trim()
    const jobDescription = workerEditor.jobDescription.trim()
    const reason = workerEditor.changeReason.trim()
    if (!name || !jobDescription || !reason || (!workerEditor.workerId && !workerEditor.startDate)) {
      setFormError('Nama, pekerjaan, alasan, dan tanggal mulai untuk pekerja baru wajib diisi.')
      return
    }
    if (!workerEditor.workerId && workerEditor.endDate && workerEditor.endDate < workerEditor.startDate) {
      setFormError('Tanggal berhenti tidak boleh sebelum tanggal mulai.')
      return
    }

    if (workerEditor.workerId) {
      setWorkers((current) => current.map((worker) => worker.id === workerEditor.workerId ? {
        ...worker,
        name,
        jobDescription,
        notes: workerEditor.notes.trim(),
      } : worker))
      setNotice(`Profil ${name} diperbarui dengan alasan “${reason}”. Stable ID dan seluruh histori masa kerja/absensi tidak berubah. Simulasi browser saja.`)
    } else {
      const dailyRate = Number(cleanMoneyInput(workerEditor.dailyRate))
      if (dailyRate <= 0 || !workerEditor.effectiveFrom) {
        setFormError('Rate awal dan tanggal efektif rate wajib diisi.')
        return
      }
      if (!initialRateCoversEmploymentStart(workerEditor.effectiveFrom, workerEditor.startDate)) {
        setFormError('Rate awal harus berlaku paling lambat pada tanggal mulai agar coverage payroll tidak bolong.')
        return
      }
      const workerId = `wrk-${selectedContractorId}-${String(workerSequence).padStart(3, '0')}`
      const newWorker: Worker = {
        id: workerId,
        contractorId: selectedContractorId,
        name,
        jobDescription,
        employmentPeriods: [employment(
          `employment-${workerId}-001`,
          workerId,
          workerEditor.startDate,
          workerEditor.endDate || null,
          reason,
          workerEditor.endDate ? reason : undefined,
        )],
        notes: workerEditor.notes.trim(),
      }
      setWorkers((current) => [...current, newWorker])
      setRates((current) => addRateVersion(current, {
        id: `rate-${workerId}-${workerEditor.effectiveFrom}`,
        workerId,
        dailyRate,
        effectiveFrom: workerEditor.effectiveFrom,
        reason,
        changedBy: 'Owner · simulasi',
        changedAt: new Date().toISOString(),
      }))
      setWorkerSequence((current) => current + 1)
      setNotice(`${name} ditambahkan ke roster ${selectedContractor.name} dengan stable ID ${workerId}. Simulasi browser saja.`)
    }
    setWorkerEditor(null)
    setFormError('')
  }

  const openRateEditor = (worker: Worker) => {
    const currentRate = rateForDate(worker.id, periodEnd, rates)?.dailyRate ?? 0
    setRateEditor({workerId: worker.id, dailyRate: String(currentRate), effectiveFrom: periodEnd, reason: ''})
    setWorkerEditor(null)
    setEmploymentEditor(null)
    setFormError('')
  }

  const openEmploymentEditor = (worker: Worker) => {
    const action: EmploymentEditor['action'] = workerIsActive(worker) ? 'DEACTIVATE' : 'REACTIVATE'
    const orderedPeriods = worker.employmentPeriods.slice().sort((left, right) => left.effectiveFrom.localeCompare(right.effectiveFrom))
    const latestPeriod = orderedPeriods.at(-1)
    const minimumByHistory = action === 'REACTIVATE' && latestPeriod?.effectiveTo
      ? shiftDate(latestPeriod.effectiveTo, 1)
      : latestPeriod?.effectiveFrom ?? periodStart
    const minimumByLock = latestLockedPeriodEnd ? shiftDate(latestLockedPeriodEnd, 1) : minimumByHistory
    const minimumDate = [minimumByHistory, minimumByLock].sort().at(-1) ?? periodStart
    const preferredDate = action === 'DEACTIVATE' ? periodEnd : periodStart
    setEmploymentEditor({workerId: worker.id, action, effectiveDate: [preferredDate, minimumDate].sort().at(-1) ?? minimumDate, reason: ''})
    setWorkerEditor(null)
    setRateEditor(null)
    setFormError('')
  }

  const saveEmployment = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!employmentEditor) return
    const reason = employmentEditor.reason.trim()
    if (!employmentEditor.effectiveDate || !reason) {
      setFormError('Tanggal efektif dan alasan wajib diisi.')
      return
    }
    if (latestLockedPeriodEnd && employmentEditor.effectiveDate <= latestLockedPeriodEnd) {
      setFormError(`Tanggal efektif harus setelah periode terkunci ${shortDate(latestLockedPeriodEnd)} agar eligibility historis tidak berubah.`)
      return
    }
    const target = workers.find((worker) => worker.id === employmentEditor.workerId)
    if (!target) return
    if (employmentEditor.action === 'DEACTIVATE') {
      const conflictingDraftEntries = Object.values(books)
        .flatMap((attendanceBook) => Object.values(attendanceBook))
        .filter((entry) => entry.workerId === target.id && entry.workDate > employmentEditor.effectiveDate)
      if (conflictingDraftEntries.length > 0) {
        setFormError(`Masih ada ${conflictingDraftEntries.length} isian absensi setelah tanggal berhenti. Kosongkan/koreksi isian tersebut dulu; sistem tidak menghapusnya diam-diam.`)
        return
      }
    }
    try {
      const changedAt = new Date().toISOString()
      const nextWorker = employmentEditor.action === 'REACTIVATE'
        ? reactivateWorker(target, {
          id: `employment-${target.id}-${employmentEditor.effectiveDate}`,
          effectiveFrom: employmentEditor.effectiveDate,
          reason,
          changedBy: 'Owner · simulasi',
          changedAt,
        })
        : deactivateWorker(target, {
          effectiveTo: employmentEditor.effectiveDate,
          reason,
          changedBy: 'Owner · simulasi',
          changedAt,
        })
      setWorkers((current) => current.map((worker) => worker.id === target.id ? nextWorker : worker))
      setNotice(employmentEditor.action === 'REACTIVATE'
        ? `${target.name} aktif kembali mulai ${shortDate(employmentEditor.effectiveDate)} dengan stable ID ${target.id}. Gap masa kerja lama tetap tersimpan. Simulasi browser saja.`
        : `${target.name} nonaktif setelah ${shortDate(employmentEditor.effectiveDate)}. Histori sebelum tanggal itu tetap tersimpan. Simulasi browser saja.`)
      setEmploymentEditor(null)
      setFormError('')
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Perubahan status masa kerja tidak dapat disimpan.')
    }
  }

  const saveRate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!rateEditor) return
    try {
      const dailyRate = Number(cleanMoneyInput(rateEditor.dailyRate))
      const nextRates = addRateVersion(rates, {
        id: `rate-${rateEditor.workerId}-${rateEditor.effectiveFrom}`,
        workerId: rateEditor.workerId,
        dailyRate,
        effectiveFrom: rateEditor.effectiveFrom,
        reason: rateEditor.reason,
        changedBy: 'Owner · simulasi',
        changedAt: new Date().toISOString(),
      })
      setRates(nextRates)
      const worker = workers.find((item) => item.id === rateEditor.workerId)
      setNotice(`Versi rate baru ${worker?.name ?? rateEditor.workerId} berlaku ${shortDate(rateEditor.effectiveFrom)}. Rate lama tetap tersimpan. Simulasi browser saja.`)
      setRateEditor(null)
      setFormError('')
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Rate tidak dapat disimpan.')
    }
  }

  const postPeriod = () => {
    if (!mutable || periodTotals.missingCells > 0 || periodTotals.uncoveredRateCells > 0 || periodTotals.eligibleCells === 0) return
    const periodEntryKeys = contractorWorkers.flatMap((worker) => workDates
      .filter((workDate) => workerIsEligibleOn(worker, selectedContractor, workDate))
      .map((workDate) => attendanceKey(worker.id, workDate)))
    try {
      const postedBook = snapshotAttendanceRates(book, rates, periodEntryKeys)
      setBooks((allBooks) => ({...allBooks, [periodKey]: postedBook}))
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Rate snapshot tidak lengkap; posting dibatalkan.')
      return
    }
    setPeriodStatuses((current) => ({...current, [periodKey]: 'POSTED'}))
    setBulkPreview(null)
    setNotice('Posting disimulasikan di browser: periode kini immutable dan rate tersnapshot. Tidak ada payroll, kas, stok, atau HPP backend yang berubah.')
  }

  const submitAmendment = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!amendment?.reason.trim()) return
    setNotice(`Rancangan ${amendment.kind === 'CORRECTION' ? 'correction' : 'reversal'} dicatat dengan alasan “${amendment.reason.trim()}”. Snapshot posted tetap utuh; request belum dikirim karena endpoint backend belum tersambung.`)
    setAmendment(null)
  }

  return <div className="attendance2-page">
    <section className="ops-hero attendance2-hero">
      <div>
        <span>PAYROLL · ABSENSI PER PEKERJA</span>
        <h1>Roster ringan per Mandor</h1>
        <p>Kelola pekerja keluar-masuk, rate efektif, dan absensi per tanggal tanpa membuat HR master yang berat. Relasi tetap memakai stable worker ID.</p>
      </div>
      <aside className={!selectedContractor.attendanceRequired ? 'attendance2-exempt' : 'attendance-rule'}>
        <UsersRound/>
        <div>
          <small>MANDOR TERPILIH</small>
          <strong>{selectedContractor.name}</strong>
          <em>{!selectedContractor.attendanceRequired ? 'attendance_required=false · absensi anak buah tidak diwajibkan' : `${contractorWorkers.filter(workerIsActive).length} pekerja aktif`}</em>
        </div>
      </aside>
    </section>

    <div className="attendance2-disclosure" role="status">
      <AlertTriangle/>
      <span><strong>UX SIMULASI · FRONTEND BELUM TERHUBUNG BACKEND.</strong> Roster dan isian di halaman ini hanya hidup di browser. Tidak ada payroll, kas, stok, atau HPP yang diposting.</span>
    </div>

    <section className="ops-metrics attendance2-metrics">
      <article className="panel"><span>STATUS PERIODE</span><strong className={mutable ? 'warn-text' : 'good-text'}>{periodStatus}</strong><small>{mutable ? 'Boleh diedit sebelum posting' : 'Snapshot posted tidak dapat diedit'}</small></article>
      <article className="panel"><span>ISIAN TERCATAT</span><strong>{periodTotals.recordedCells} / {periodTotals.eligibleCells}</strong><small>{periodTotals.missingCells} tanggal pekerja belum diisi</small></article>
      <article className="panel"><span>HARI HADIR</span><strong>{periodTotals.presentDays}</strong><small>Tidak menyimpulkan kotak kosong sebagai absen</small></article>
      <article className="panel"><span>PREVIEW NOMINAL</span><strong>{money(periodTotals.nominal)}</strong><small>{periodTotals.uncoveredRateCells > 0 ? `${periodTotals.uncoveredRateCells} tanggal eligible belum punya rate` : 'Rate efektif × hari hadir · belum diposting'}</small></article>
    </section>

    <section className="panel attendance2-workspace">
      <header className="attendance2-toolbar">
        <div>
          <span>PERIODE ABSENSI</span>
          <strong>{workDates.length > 0 ? `${shortDate(periodStart)} — ${shortDate(periodEnd)}` : 'Tanggal periode tidak valid'}</strong>
          <small>Tanggal gajian {shortDate(payDate)} · hari libur ditandai pada kolom.</small>
        </div>
        <div className="attendance2-controls">
          <label><span>MANDOR</span><select value={selectedContractorId} onChange={(event) => {setSelectedContractorId(event.target.value); setBulkPreview(null); setWorkerEditor(null); setRateEditor(null); setEmploymentEditor(null)}}>{contractors.map((contractor) => <option key={contractor.id} value={contractor.id}>{contractor.name}{!contractor.attendanceRequired ? ' · absensi tidak wajib' : ''}</option>)}</select></label>
          <label><span>AWAL PERIODE</span><input type="date" value={periodStart} onChange={(event) => {setPeriodStart(event.target.value); setBulkPreview(null)}}/></label>
          <label><span>AKHIR PERIODE</span><input type="date" value={periodEnd} onChange={(event) => {setPeriodEnd(event.target.value); setBulkPreview(null)}}/></label>
          <label><span>TANGGAL GAJIAN</span><input type="date" value={payDate} disabled={!mutable} onChange={(event) => setPeriodPayDates((current) => ({...current, [periodKey]: event.target.value}))}/></label>
        </div>
      </header>

      {!selectedContractor.attendanceRequired ? <div className="attendance2-exempt-card">
        <ShieldCheck/>
        <div><strong>Absensi tidak diwajibkan oleh kebijakan Mandor</strong><p>{selectedContractor.attendancePolicyReason ?? 'Alasan pengecualian harus berasal dari konfigurasi backend.'}</p><small>Logika membaca <code>contractors.attendance_required=false</code>; nama dan status Special tidak dipakai sebagai aturan.</small></div>
      </div> : <>
        <div className="attendance2-bulkbar">
          <div><ClipboardCheck/><span><strong>Aksi cepat selalu pakai preview</strong><small>Tandai semua tidak mengisi tanggal libur; copy hanya memakai record sumber yang benar-benar ada.</small></span></div>
          <div>
            <button className="soft-btn" disabled={!mutable || visibleWorkers.length === 0} onClick={() => prepareBulk('MARK_ALL_PRESENT')}><Check/> Tandai semua hadir</button>
            <button className="soft-btn" disabled={!mutable || visibleWorkers.length === 0} onClick={() => prepareBulk('CLEAR')}><X/> Kosongkan</button>
            <button className="soft-btn" disabled={!mutable || visibleWorkers.length === 0} onClick={() => prepareBulk('COPY_PREVIOUS_WEEK')}><Copy/> Salin minggu sebelumnya</button>
          </div>
        </div>

        {bulkPreview ? <section className="attendance2-preview" aria-live="polite">
          <div><span>PREVIEW AKSI MASSAL</span><strong>{bulkLabel[bulkPreview.action]}</strong><small>Belum diterapkan dan belum menulis backend.</small></div>
          <p><b>{bulkPreview.affectedCells}</b><span>isian berubah</span></p>
          <p><b>{money(bulkPreview.nominalDelta)}</b><span>perubahan nominal preview</span></p>
          {bulkPreview.action === 'COPY_PREVIOUS_WEEK' ? <p><b>{bulkPreview.missingSourceCells}</b><span>sumber kosong dilewati</span></p> : null}
          <div className="attendance2-preview-actions"><button className="soft-btn" onClick={() => setBulkPreview(null)}>Batal</button><button className="primary-btn" disabled={bulkPreview.affectedCells === 0} onClick={confirmBulk}><Check/> Terapkan ke Draft</button></div>
        </section> : null}

        <div className="attendance2-matrix-wrap">
          <table className="attendance2-matrix">
            <thead><tr><th>Pekerja</th>{workDates.map((workDate) => <th key={workDate}><span>{indonesianDayDate(workDate)}</span>{HOLIDAYS[workDate] ? <small>{HOLIDAYS[workDate]}</small> : <small>Hari kerja</small>}</th>)}</tr></thead>
            <tbody>{visibleWorkers.map((worker) => <tr key={worker.id}>
              <th><span className="attendance2-worker-name"><UserRound/><span><strong>{worker.name}</strong><small>{worker.jobDescription}</small><code>{worker.id}</code></span></span><em>{worker.employmentPeriods.length} periode kerja tersimpan</em><em>{workerIsActive(worker) ? 'Status roster aktif' : 'Status roster nonaktif'}</em></th>
              {workDates.map((workDate) => {
                const eligible = workerIsEligibleOn(worker, selectedContractor, workDate)
                const key = attendanceKey(worker.id, workDate)
                const entry = book[key]
                const effectiveRate = entry?.rateSnapshot ?? rateForDate(worker.id, workDate, rates)?.dailyRate
                const employmentStatus = workerEmploymentStatusOn(worker, workDate)
                const outsideReason = employmentStatus === 'NOT_STARTED' ? 'Belum mulai' : employmentStatus === 'STOPPED' ? 'Sudah berhenti' : employmentStatus === 'EMPLOYMENT_GAP' ? 'Jeda masa kerja' : 'Tidak eligible'
                return <td key={key} className={!eligible ? 'attendance2-ineligible' : entry?.mark === 'PRESENT' ? 'attendance2-present' : entry?.mark === 'ABSENT' ? 'attendance2-absent' : ''}>
                  {eligible ? <>
                    <label className="attendance2-check"><input type="checkbox" checked={entry?.mark === 'PRESENT'} disabled={!mutable} onChange={(event) => setAttendance(worker, workDate, event.target.checked ? 'PRESENT' : 'ABSENT')}/><span aria-hidden="true"><Check/></span></label>
                    <strong>{entry?.mark === 'PRESENT' ? 'Hadir' : entry?.mark === 'ABSENT' ? 'Absen' : 'Belum diisi'}</strong>
                    <small>{effectiveRate ? money(effectiveRate) : 'Rate belum ada'}</small>
                    {entry ? <button aria-label={`Kosongkan ${worker.name} ${workDate}`} disabled={!mutable} onClick={() => setAttendance(worker, workDate)}><X/></button> : <button disabled={!mutable} onClick={() => setAttendance(worker, workDate, 'ABSENT')}>Set absen</button>}
                  </> : <><LockKeyhole/><strong>{outsideReason}</strong><small>Tidak dapat dicentang</small></>}
                </td>
              })}
            </tr>)}</tbody>
          </table>
          {visibleWorkers.length === 0 ? <div className="attendance2-empty"><UsersRound/><strong>Belum ada pekerja aktif</strong><small>Nyalakan “Tampilkan nonaktif” atau tambah pekerja untuk Mandor ini.</small></div> : null}
        </div>
      </>}

      <footer className="attendance2-footer">
        <div className={periodTotals.missingCells > 0 || periodTotals.uncoveredRateCells > 0 ? 'warn' : ''}>{periodTotals.missingCells > 0 || periodTotals.uncoveredRateCells > 0 ? <AlertTriangle/> : <CheckCircle2/>}<span><strong>{periodTotals.missingCells > 0 ? `${periodTotals.missingCells} isian eligible belum dicatat` : periodTotals.uncoveredRateCells > 0 ? `${periodTotals.uncoveredRateCells} tanggal eligible belum punya rate` : 'Semua tanggal eligible dan rate sudah lengkap'}</strong><small>Kotak kosong tidak otomatis dianggap absen; posting tanpa rate ditolak.</small></span></div>
        <div>
          {!mutable ? <><button className="soft-btn" onClick={() => setAmendment({kind: 'CORRECTION', reason: ''})}><RefreshCcw/> Buat koreksi</button><button className="soft-btn" onClick={() => setAmendment({kind: 'REVERSAL', reason: ''})}><Undo2/> Buat reversal</button></> : <button className="soft-btn" onClick={() => setNotice('Draft tersimpan hanya di state browser. Endpoint penyimpanan backend belum tersambung.')}><Save/> Simpan Draft</button>}
          <button className="primary-btn" disabled={!mutable || periodTotals.missingCells > 0 || periodTotals.uncoveredRateCells > 0 || periodTotals.eligibleCells === 0} onClick={postPeriod}><LockKeyhole/> {mutable ? 'Simulasikan posting' : 'Posted · terkunci'}</button>
        </div>
      </footer>

      {amendment ? <form className="attendance2-amendment" onSubmit={submitAmendment}>
        <div><span>POSTED TETAP IMMUTABLE</span><strong>{amendment.kind === 'CORRECTION' ? 'Buat dokumen koreksi baru' : 'Buat event reversal baru'}</strong><small>Dokumen sumber tidak dibuka untuk edit dan tidak dihapus.</small></div>
        <label><span>ALASAN · WAJIB</span><textarea value={amendment.reason} onChange={(event) => setAmendment({...amendment, reason: event.target.value})} placeholder="Jelaskan salah input dan dampaknya..."/></label>
        <div><button type="button" className="soft-btn" onClick={() => setAmendment(null)}>Batal</button><button className="primary-btn" disabled={!amendment.reason.trim()}><ShieldCheck/> Siapkan request</button></div>
      </form> : null}
      {notice ? <div className="ops-notice" aria-live="polite"><CheckCircle2/><span>{notice}</span><button aria-label="Tutup pemberitahuan" onClick={() => setNotice('')}><XCircle/></button></div> : null}
    </section>

    <section className="panel attendance2-roster">
      <header>
        <div><span>ROSTER PEKERJA · {selectedContractor.name.toUpperCase()}</span><strong>Tambah dan edit langsung dari Absensi</strong><small>Nonaktifkan pekerja lama; jangan hard-delete histori.</small></div>
        <div><label><input type="checkbox" checked={showInactive} onChange={(event) => setShowInactive(event.target.checked)}/> Tampilkan nonaktif</label><button className="primary-btn" onClick={openAddWorker}><Plus/> Tambah pekerja</button></div>
      </header>

      <div className="attendance2-roster-list">{visibleWorkers.map((worker) => {
        const currentRate = rateForDate(worker.id, periodEnd, rates)
        const workerRates = rates.filter((version) => version.workerId === worker.id).sort((left, right) => right.effectiveFrom.localeCompare(left.effectiveFrom))
        const workerEmploymentPeriods = worker.employmentPeriods.slice().sort((left, right) => right.effectiveFrom.localeCompare(left.effectiveFrom))
        const latestEmployment = workerEmploymentPeriods[0]
        const isActive = workerIsActive(worker)
        return <article key={worker.id} className={isActive ? '' : 'inactive'}>
          <div className="attendance2-roster-id"><UserRound/><span><strong>{worker.name}</strong><code>{worker.id}</code><small>{worker.jobDescription}</small></span></div>
          <div><span>MASA KERJA TERBARU</span><strong>{latestEmployment ? `${shortDate(latestEmployment.effectiveFrom)} — ${latestEmployment.effectiveTo ? shortDate(latestEmployment.effectiveTo) : 'Aktif'}` : 'Belum ada masa kerja'}</strong><small>{isActive ? `Status aktif · ${workerEmploymentPeriods.length} periode kerja` : `Status nonaktif · ${workerEmploymentPeriods.length} periode kerja tetap ada`}</small><details><summary><History/> Lihat histori masa kerja</summary><div>{workerEmploymentPeriods.map((period) => <p key={period.id}><span><b>{shortDate(period.effectiveFrom)} — {period.effectiveTo ? shortDate(period.effectiveTo) : 'aktif'}</b><small>{period.id}</small></span><em>{period.endReason ? `${period.reason} · Berhenti: ${period.endReason}` : period.reason}</em></p>)}</div></details></div>
          <div><span>RATE BERLAKU</span><strong>{currentRate ? `${money(currentRate.dailyRate)} / hari` : 'Belum ada rate'}</strong><small>{currentRate ? `Mulai ${shortDate(currentRate.effectiveFrom)}` : 'Lengkapi rate history'}</small></div>
          <details><summary><History/> {workerRates.length} versi rate</summary><div>{workerRates.map((version) => <p key={version.id}><span><b>{money(version.dailyRate)}</b><small>{shortDate(version.effectiveFrom)} — {version.effectiveTo ? shortDate(version.effectiveTo) : 'seterusnya'}</small></span><em>{version.reason}</em></p>)}</div></details>
          <div className="attendance2-roster-actions"><button className="soft-btn" onClick={() => openEditWorker(worker)}><Pencil/> Edit</button><button className="soft-btn" onClick={() => openRateEditor(worker)}><Banknote/> Ubah rate</button><button className="soft-btn" onClick={() => openEmploymentEditor(worker)}>{isActive ? <XCircle/> : <RefreshCcw/>} {isActive ? 'Nonaktifkan' : 'Aktifkan kembali'}</button></div>
          {worker.notes ? <p className="attendance2-worker-note">{worker.notes}</p> : null}
        </article>
      })}</div>

      {workerEditor ? <form className="attendance2-editor" onSubmit={saveWorker}>
        <header><div><span>{workerEditor.workerId ? 'EDIT PEKERJA' : 'PEKERJA BARU'}</span><strong>{workerEditor.workerId ?? 'Stable ID dibuat saat simpan'}</strong></div><button type="button" aria-label="Tutup form" onClick={() => {setWorkerEditor(null); setFormError('')}}><X/></button></header>
        <div className="attendance2-editor-grid">
          <label><span>NAMA / PANGGILAN</span><input value={workerEditor.name} onChange={(event) => setWorkerEditor({...workerEditor, name: event.target.value})}/></label>
          <label><span>JENIS PEKERJAAN</span><input value={workerEditor.jobDescription} onChange={(event) => setWorkerEditor({...workerEditor, jobDescription: event.target.value})} placeholder="Contoh: Jahit badan"/></label>
          {!workerEditor.workerId ? <><label><span>TANGGAL MULAI</span><input type="date" value={workerEditor.startDate} onChange={(event) => setWorkerEditor({...workerEditor, startDate: event.target.value})}/></label><label><span>TANGGAL BERHENTI · OPSIONAL</span><input type="date" value={workerEditor.endDate} onChange={(event) => setWorkerEditor({...workerEditor, endDate: event.target.value})}/></label><label><span>RATE HARIAN AWAL</span><input inputMode="numeric" value={formatMoneyInput(workerEditor.dailyRate)} onChange={(event) => setWorkerEditor({...workerEditor, dailyRate: cleanMoneyInput(event.target.value)})} placeholder="125.000"/></label><label><span>RATE BERLAKU MULAI</span><input type="date" value={workerEditor.effectiveFrom} onChange={(event) => setWorkerEditor({...workerEditor, effectiveFrom: event.target.value})}/></label></> : null}
          <label className="wide"><span>CATATAN OPSIONAL</span><input value={workerEditor.notes} onChange={(event) => setWorkerEditor({...workerEditor, notes: event.target.value})}/></label>
          <label className="wide"><span>ALASAN PERUBAHAN · WAJIB</span><input value={workerEditor.changeReason} onChange={(event) => setWorkerEditor({...workerEditor, changeReason: event.target.value})} placeholder="Contoh: pekerja baru / berhenti / koreksi nama..."/></label>
        </div>
        {formError ? <p className="attendance2-form-error"><AlertTriangle/>{formError}</p> : null}
        <footer><small>Perubahan di layar ini belum menulis backend atau audit trail produksi.</small><button className="primary-btn"><Save/> Simpan simulasi</button></footer>
      </form> : null}

      {rateEditor ? <form className="attendance2-editor attendance2-rate-editor" onSubmit={saveRate}>
        <header><div><span>VERSI RATE BARU</span><strong>{workers.find((worker) => worker.id === rateEditor.workerId)?.name} · {rateEditor.workerId}</strong></div><button type="button" aria-label="Tutup form" onClick={() => {setRateEditor(null); setFormError('')}}><X/></button></header>
        <div className="attendance2-editor-grid">
          <label><span>RATE HARIAN BARU</span><input inputMode="numeric" value={formatMoneyInput(rateEditor.dailyRate)} onChange={(event) => setRateEditor({...rateEditor, dailyRate: cleanMoneyInput(event.target.value)})}/></label>
          <label><span>BERLAKU MULAI</span><input type="date" value={rateEditor.effectiveFrom} onChange={(event) => setRateEditor({...rateEditor, effectiveFrom: event.target.value})}/></label>
          <label className="wide"><span>ALASAN · WAJIB</span><input value={rateEditor.reason} onChange={(event) => setRateEditor({...rateEditor, reason: event.target.value})} placeholder="Rate lama tidak akan ditimpa"/></label>
        </div>
        {formError ? <p className="attendance2-form-error"><AlertTriangle/>{formError}</p> : null}
        <footer><small>Rate posted memakai snapshot; versi master baru tidak menulis ulang payroll lama.</small><button className="primary-btn"><Save/> Tambah versi rate</button></footer>
      </form> : null}

      {employmentEditor ? <form className="attendance2-editor attendance2-employment-editor" onSubmit={saveEmployment}>
        <header><div><span>{employmentEditor.action === 'REACTIVATE' ? 'AKTIFKAN KEMBALI' : 'NONAKTIFKAN PEKERJA'}</span><strong>{workers.find((worker) => worker.id === employmentEditor.workerId)?.name} · {employmentEditor.workerId}</strong></div><button type="button" aria-label="Tutup form" onClick={() => {setEmploymentEditor(null); setFormError('')}}><X/></button></header>
        <div className="attendance2-editor-grid">
          <label><span>{employmentEditor.action === 'REACTIVATE' ? 'AKTIF MULAI' : 'HARI KERJA TERAKHIR'}</span><input type="date" value={employmentEditor.effectiveDate} onChange={(event) => setEmploymentEditor({...employmentEditor, effectiveDate: event.target.value})}/></label>
          <label className="wide"><span>ALASAN · WAJIB</span><input value={employmentEditor.reason} onChange={(event) => setEmploymentEditor({...employmentEditor, reason: event.target.value})} placeholder={employmentEditor.action === 'REACTIVATE' ? 'Contoh: kembali ke tim setelah jeda' : 'Contoh: berhenti dari tim'}/></label>
        </div>
        {formError ? <p className="attendance2-form-error"><AlertTriangle/>{formError}</p> : null}
        <footer><small>{employmentEditor.action === 'REACTIVATE' ? 'Membuat periode kerja baru dengan stable worker ID yang sama; gap lama tidak dihapus.' : 'Menutup periode kerja aktif; histori lama tidak ditimpa.'} Frontend simulasi, backend belum berubah.</small><button className="primary-btn"><Save/> Simpan status simulasi</button></footer>
      </form> : null}
    </section>

    <section className="attendance2-notes">
      <article className="panel"><ShieldCheck/><div><span>GUARDRAIL HISTORI</span><strong>Posted hanya correction / reversal</strong><p>Stable ID menjaga histori saat nama berubah. Rate dan masa kerja memakai effective date; aktif kembali membuat periode baru sehingga gap lama tidak terhapus.</p></div></article>
      <article className="panel"><CalendarDays/><div><span>BATAS IMPLEMENTASI SEKARANG</span><strong>Attendance → payroll ada; lineage HPP belum diklaim</strong><p>Absensi memang input payroll sesuai rule existing. Yang belum terverifikasi adalah formula dan lineage alokasi biaya absensi ke HPP PO/SKU, jadi halaman ini tidak membuat angka HPP rekaan.</p><button className="soft-btn" onClick={() => onNavigate('admin-period-close')}>Lihat kontrol periode</button></div></article>
    </section>
  </div>
}
