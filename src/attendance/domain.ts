export type ISODate = string

export type Contractor = {
  id: string
  name: string
  attendanceRequired: boolean
  attendancePolicyReason?: string
}

export type Worker = {
  id: string
  contractorId: string
  name: string
  jobDescription: string
  employmentPeriods: WorkerEmploymentPeriod[]
  notes: string
}

export type WorkerEmploymentPeriod = {
  id: string
  workerId: string
  effectiveFrom: ISODate
  effectiveTo: ISODate | null
  reason: string
  changedBy: string
  changedAt: string
  endReason?: string
  endedBy?: string
  endedAt?: string
}

export type WorkerRateVersion = {
  id: string
  workerId: string
  dailyRate: number
  effectiveFrom: ISODate
  effectiveTo: ISODate | null
  reason: string
  changedBy: string
  changedAt: string
}

export type AttendanceMark = 'PRESENT' | 'ABSENT'
export type AttendanceEntry = {
  workerId: string
  workDate: ISODate
  mark: AttendanceMark
  rateSnapshot?: number
}
export type AttendanceBook = Record<string, AttendanceEntry>
export type AttendancePeriodStatus = 'DRAFT' | 'POSTED' | 'CORRECTED' | 'REVERSED'
export type BulkAttendanceAction = 'MARK_ALL_PRESENT' | 'CLEAR' | 'COPY_PREVIOUS_WEEK'

export type BulkMutation = {
  key: string
  workerId: string
  workDate: ISODate
  before?: AttendanceEntry
  after?: AttendanceEntry
}

export type BulkAttendancePreview = {
  action: BulkAttendanceAction
  mutations: BulkMutation[]
  affectedCells: number
  missingSourceCells: number
  nominalBefore: number
  nominalAfter: number
  nominalDelta: number
}

const DAY_IN_MS = 86_400_000

const parseUTCDate = (value: ISODate) => new Date(`${value}T00:00:00.000Z`)

export const attendanceKey = (workerId: string, workDate: ISODate) => `${workerId}::${workDate}`

export const shiftDate = (value: ISODate, days: number): ISODate => {
  const date = parseUTCDate(value)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

export const datesBetween = (startDate: ISODate, endDate: ISODate): ISODate[] => {
  const start = parseUTCDate(startDate).getTime()
  const end = parseUTCDate(endDate).getTime()
  if (!Number.isFinite(start) || !Number.isFinite(end) || start > end) return []
  const dates: ISODate[] = []
  for (let cursor = start; cursor <= end; cursor += DAY_IN_MS) {
    dates.push(new Date(cursor).toISOString().slice(0, 10))
  }
  return dates
}

export const indonesianDayDate = (value: ISODate) => new Intl.DateTimeFormat('id-ID', {
  weekday: 'long',
  day: 'numeric',
  month: 'short',
  timeZone: 'UTC',
}).format(parseUTCDate(value))

const orderedEmploymentPeriods = (worker: Worker) => worker.employmentPeriods
  .slice()
  .sort((left, right) => left.effectiveFrom.localeCompare(right.effectiveFrom))

export const employmentPeriodForDate = (
  worker: Worker,
  workDate: ISODate,
): WorkerEmploymentPeriod | undefined => orderedEmploymentPeriods(worker).find((period) => (
  period.effectiveFrom <= workDate
    && (period.effectiveTo === null || period.effectiveTo >= workDate)
))

export const workerIsActive = (worker: Worker) => worker.employmentPeriods.some(
  (period) => period.effectiveTo === null,
)

export const workerEmploymentStatusOn = (worker: Worker, workDate: ISODate) => {
  if (employmentPeriodForDate(worker, workDate)) return 'ELIGIBLE' as const
  const periods = orderedEmploymentPeriods(worker)
  if (periods.length === 0 || workDate < periods[0].effectiveFrom) return 'NOT_STARTED' as const
  const last = periods[periods.length - 1]
  if (last.effectiveTo !== null && workDate > last.effectiveTo) return 'STOPPED' as const
  return 'EMPLOYMENT_GAP' as const
}

const assertEmploymentPeriodDoesNotOverlap = (
  periods: WorkerEmploymentPeriod[],
  next: WorkerEmploymentPeriod,
) => {
  const overlaps = periods.some((period) => (
    (period.effectiveTo === null || period.effectiveTo >= next.effectiveFrom)
      && (next.effectiveTo === null || next.effectiveTo >= period.effectiveFrom)
  ))
  if (overlaps) throw new Error('Masa kerja baru bertumpuk dengan histori masa kerja yang sudah ada.')
}

export const reactivateWorker = (
  worker: Worker,
  next: Omit<WorkerEmploymentPeriod, 'workerId' | 'effectiveTo'>,
): Worker => {
  if (workerIsActive(worker)) throw new Error('Pekerja masih aktif dan tidak dapat diaktifkan ulang.')
  if (!next.reason.trim()) throw new Error('Alasan aktif kembali wajib diisi.')
  const period: WorkerEmploymentPeriod = {...next, workerId: worker.id, effectiveTo: null}
  assertEmploymentPeriodDoesNotOverlap(worker.employmentPeriods, period)
  return {...worker, employmentPeriods: [...worker.employmentPeriods, period]}
}

export const deactivateWorker = (
  worker: Worker,
  change: Pick<WorkerEmploymentPeriod, 'effectiveTo' | 'reason' | 'changedBy' | 'changedAt'>,
): Worker => {
  if (!change.reason.trim()) throw new Error('Alasan nonaktif wajib diisi.')
  const openPeriods = worker.employmentPeriods.filter((period) => period.effectiveTo === null)
  if (openPeriods.length !== 1) throw new Error('Pekerja tidak mempunyai tepat satu masa kerja aktif.')
  const openPeriod = openPeriods[0]
  if (!change.effectiveTo || change.effectiveTo < openPeriod.effectiveFrom) {
    throw new Error('Tanggal berhenti tidak boleh sebelum tanggal mulai masa kerja aktif.')
  }
  return {
    ...worker,
    employmentPeriods: worker.employmentPeriods.map((period) => period.id === openPeriod.id ? {
      ...period,
      effectiveTo: change.effectiveTo,
      endReason: change.reason,
      endedBy: change.changedBy,
      endedAt: change.changedAt,
    } : period),
  }
}

export const workerIsEligibleOn = (
  worker: Worker,
  contractor: Contractor | undefined,
  workDate: ISODate,
) => {
  if (!contractor || !contractor.attendanceRequired) return false
  return Boolean(employmentPeriodForDate(worker, workDate))
}

export const defaultRoster = (workers: Worker[], contractorId: string) => workers.filter(
  (worker) => worker.contractorId === contractorId && workerIsActive(worker),
)

export const initialRateCoversEmploymentStart = (
  effectiveFrom: ISODate,
  employmentStart: ISODate,
) => Boolean(effectiveFrom && employmentStart && effectiveFrom <= employmentStart)

export const rateForDate = (
  workerId: string,
  workDate: ISODate,
  versions: WorkerRateVersion[],
): WorkerRateVersion | undefined => versions
  .filter((version) => version.workerId === workerId
    && version.effectiveFrom <= workDate
    && (version.effectiveTo === null || version.effectiveTo >= workDate))
  .sort((left, right) => right.effectiveFrom.localeCompare(left.effectiveFrom))[0]

export const addRateVersion = (
  versions: WorkerRateVersion[],
  next: Omit<WorkerRateVersion, 'effectiveTo'>,
): WorkerRateVersion[] => {
  if (!Number.isFinite(next.dailyRate) || next.dailyRate <= 0) {
    throw new Error('Rate harian harus lebih besar dari nol.')
  }
  if (!next.reason.trim()) throw new Error('Alasan perubahan rate wajib diisi.')
  if (versions.some((version) => version.workerId === next.workerId && version.effectiveFrom === next.effectiveFrom)) {
    throw new Error('Sudah ada versi rate pada tanggal efektif tersebut.')
  }

  const workerVersions = versions
    .filter((version) => version.workerId === next.workerId)
    .concat({...next, effectiveTo: null})
    .sort((left, right) => left.effectiveFrom.localeCompare(right.effectiveFrom))
    .map((version, index, ordered) => ({
      ...version,
      effectiveTo: ordered[index + 1] ? shiftDate(ordered[index + 1].effectiveFrom, -1) : null,
    }))

  return versions
    .filter((version) => version.workerId !== next.workerId)
    .concat(workerVersions)
}

export const insertAttendance = (book: AttendanceBook, entry: AttendanceEntry): AttendanceBook => {
  const key = attendanceKey(entry.workerId, entry.workDate)
  if (book[key]) throw new Error('Absensi pekerja pada tanggal ini sudah tercatat.')
  return {...book, [key]: entry}
}

export const canMutateAttendance = (status: AttendancePeriodStatus) => status === 'DRAFT'

export const attendanceEntryAmount = (
  entry: AttendanceEntry | undefined,
  versions: WorkerRateVersion[],
) => entry?.mark === 'PRESENT'
  ? entry.rateSnapshot ?? rateForDate(entry.workerId, entry.workDate, versions)?.dailyRate ?? 0
  : 0

export const snapshotAttendanceRates = (
  book: AttendanceBook,
  versions: WorkerRateVersion[],
  keys?: Iterable<string>,
): AttendanceBook => {
  const includedKeys = keys ? new Set(keys) : null
  return Object.fromEntries(Object.entries(book).map(([key, entry]) => {
    if (includedKeys && !includedKeys.has(key)) return [key, entry]
    const applicableRate = rateForDate(entry.workerId, entry.workDate, versions)
    if (!applicableRate) {
      throw new Error(`Rate pekerja ${entry.workerId} pada ${entry.workDate} belum tersedia.`)
    }
    return [key, {...entry, rateSnapshot: applicableRate.dailyRate}]
  }))
}

export const previewBulkAttendance = ({
  action,
  workers,
  contractors,
  workDates,
  rates,
  book,
  excludedBulkDates = [],
}: {
  action: BulkAttendanceAction
  workers: Worker[]
  contractors: Contractor[]
  workDates: ISODate[]
  rates: WorkerRateVersion[]
  book: AttendanceBook
  excludedBulkDates?: ISODate[]
}): BulkAttendancePreview => {
  const contractorById = new Map(contractors.map((contractor) => [contractor.id, contractor]))
  const excluded = new Set(excludedBulkDates)
  const mutations: BulkMutation[] = []
  let missingSourceCells = 0

  for (const worker of workers) {
    const contractor = contractorById.get(worker.contractorId)
    for (const workDate of workDates) {
      if (excluded.has(workDate) || !workerIsEligibleOn(worker, contractor, workDate)) continue
      const key = attendanceKey(worker.id, workDate)
      const before = book[key]
      let after: AttendanceEntry | undefined

      if (action === 'MARK_ALL_PRESENT') {
        after = {workerId: worker.id, workDate, mark: 'PRESENT'}
      } else if (action === 'COPY_PREVIOUS_WEEK') {
        const source = book[attendanceKey(worker.id, shiftDate(workDate, -7))]
        if (!source) {
          missingSourceCells += 1
          continue
        }
        after = {workerId: worker.id, workDate, mark: source.mark}
      }

      if (before?.mark === after?.mark) continue
      mutations.push({key, workerId: worker.id, workDate, before, after})
    }
  }

  const nominalBefore = mutations.reduce((sum, mutation) => sum + attendanceEntryAmount(mutation.before, rates), 0)
  const nominalAfter = mutations.reduce((sum, mutation) => sum + attendanceEntryAmount(mutation.after, rates), 0)
  return {
    action,
    mutations,
    affectedCells: mutations.length,
    missingSourceCells,
    nominalBefore,
    nominalAfter,
    nominalDelta: nominalAfter - nominalBefore,
  }
}

export const applyBulkAttendance = (
  book: AttendanceBook,
  preview: BulkAttendancePreview,
): AttendanceBook => {
  const next = {...book}
  for (const mutation of preview.mutations) {
    if (mutation.after) next[mutation.key] = mutation.after
    else delete next[mutation.key]
  }
  return next
}
