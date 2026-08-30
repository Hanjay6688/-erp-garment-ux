import { describe, expect, it } from 'vitest'
import {
  addRateVersion,
  applyBulkAttendance,
  attendanceEntryAmount,
  attendanceKey,
  canMutateAttendance,
  deactivateWorker,
  defaultRoster,
  indonesianDayDate,
  initialRateCoversEmploymentStart,
  insertAttendance,
  previewBulkAttendance,
  rateForDate,
  reactivateWorker,
  snapshotAttendanceRates,
  workerIsActive,
  workerIsEligibleOn,
  type AttendanceBook,
  type Contractor,
  type Worker,
  type WorkerRateVersion,
} from './domain'

const normal: Contractor = {id: 'mandor-normal', name: 'Mandor Normal', attendanceRequired: true}
const exempt: Contractor = {id: 'mandor-exempt', name: 'Mandor Exempt', attendanceRequired: false}
const worker: Worker = {
  id: 'wrk-stable-001',
  contractorId: normal.id,
  name: 'Nama Lama',
  jobDescription: 'Jahit',
  employmentPeriods: [{
    id: 'employment-1',
    workerId: 'wrk-stable-001',
    effectiveFrom: '2026-08-26',
    effectiveTo: '2026-08-29',
    reason: 'Masuk awal',
    changedBy: 'Owner',
    changedAt: '2026-08-26T00:00:00Z',
  }],
  notes: '',
}
const rates: WorkerRateVersion[] = [
  {id: 'rate-1', workerId: worker.id, dailyRate: 100_000, effectiveFrom: '2026-08-01', effectiveTo: '2026-08-27', reason: 'Rate awal', changedBy: 'Owner', changedAt: '2026-08-01T00:00:00Z'},
  {id: 'rate-2', workerId: worker.id, dailyRate: 125_000, effectiveFrom: '2026-08-28', effectiveTo: null, reason: 'Rate baru', changedBy: 'Owner', changedAt: '2026-08-28T00:00:00Z'},
]

describe('attendance roster domain', () => {
  it('uses real Indonesian weekday labels without local timezone drift', () => {
    expect(indonesianDayDate('2026-08-26')).toMatch(/^Rabu, 26 Agu/)
  })

  it('blocks dates before a Wednesday start and after a mid-period end', () => {
    expect(workerIsEligibleOn(worker, normal, '2026-08-25')).toBe(false)
    expect(workerIsEligibleOn(worker, normal, '2026-08-26')).toBe(true)
    expect(workerIsEligibleOn(worker, normal, '2026-08-29')).toBe(true)
    expect(workerIsEligibleOn(worker, normal, '2026-08-30')).toBe(false)
  })

  it('uses the effective-dated rate and preserves the older numeric rate', () => {
    expect(rateForDate(worker.id, '2026-08-27', rates)?.dailyRate).toBe(100_000)
    expect(rateForDate(worker.id, '2026-08-28', rates)?.dailyRate).toBe(125_000)
    expect(rates[0].dailyRate).toBe(100_000)
  })

  it('adds a rate version by closing the previous interval, not replacing history', () => {
    const result = addRateVersion(rates.slice(0, 1), {
      id: 'rate-next', workerId: worker.id, dailyRate: 120_000,
      effectiveFrom: '2026-08-20', reason: 'Penyesuaian', changedBy: 'Owner', changedAt: '2026-08-19T00:00:00Z',
    })
    expect(result).toHaveLength(2)
    expect(result.find((rate) => rate.id === 'rate-1')).toMatchObject({dailyRate: 100_000, effectiveTo: '2026-08-19'})
    expect(result.find((rate) => rate.id === 'rate-next')).toMatchObject({dailyRate: 120_000, effectiveTo: null})
  })

  it('keeps attendance attached to stable ID after a name edit', () => {
    const book = insertAttendance({}, {workerId: worker.id, workDate: '2026-08-28', mark: 'PRESENT'})
    const renamed = {...worker, name: 'Nama Baru'}
    expect(book[attendanceKey(renamed.id, '2026-08-28')].mark).toBe('PRESENT')
  })

  it('hides inactive workers from the default roster', () => {
    expect(defaultRoster([worker], normal.id)).toEqual([])
  })

  it('reactivates with the same stable ID while preserving the historic employment gap', () => {
    const reactivated = reactivateWorker(worker, {
      id: 'employment-2',
      effectiveFrom: '2026-09-03',
      reason: 'Kembali ke tim',
      changedBy: 'Owner',
      changedAt: '2026-09-02T10:00:00Z',
    })

    expect(reactivated.id).toBe(worker.id)
    expect(reactivated.employmentPeriods).toHaveLength(2)
    expect(workerIsEligibleOn(reactivated, normal, '2026-08-28')).toBe(true)
    expect(workerIsEligibleOn(reactivated, normal, '2026-08-31')).toBe(false)
    expect(workerIsEligibleOn(reactivated, normal, '2026-09-03')).toBe(true)
    expect(workerIsActive(reactivated)).toBe(true)
  })

  it('rejects overlapping reactivation instead of erasing the previous stop boundary', () => {
    expect(() => reactivateWorker(worker, {
      id: 'employment-overlap',
      effectiveFrom: '2026-08-29',
      reason: 'Tanggal salah',
      changedBy: 'Owner',
      changedAt: '2026-08-29T10:00:00Z',
    })).toThrow(/bertumpuk/i)
    expect(worker.employmentPeriods[0].effectiveTo).toBe('2026-08-29')
  })

  it('closes only the active employment period and preserves its opening audit', () => {
    const activeWorker = reactivateWorker(worker, {
      id: 'employment-2',
      effectiveFrom: '2026-09-03',
      reason: 'Kembali ke tim',
      changedBy: 'Owner A',
      changedAt: '2026-09-02T10:00:00Z',
    })
    const deactivated = deactivateWorker(activeWorker, {
      effectiveTo: '2026-09-20',
      reason: 'Berhenti lagi',
      changedBy: 'Owner B',
      changedAt: '2026-09-20T10:00:00Z',
    })
    const closed = deactivated.employmentPeriods.find((period) => period.id === 'employment-2')

    expect(closed).toMatchObject({
      effectiveFrom: '2026-09-03',
      effectiveTo: '2026-09-20',
      reason: 'Kembali ke tim',
      changedBy: 'Owner A',
      endReason: 'Berhenti lagi',
      endedBy: 'Owner B',
    })
    expect(deactivated.employmentPeriods[0]).toEqual(worker.employmentPeriods[0])
    expect(workerIsActive(deactivated)).toBe(false)
  })

  it('rejects a duplicate attendance insert for the same worker and date', () => {
    const first = insertAttendance({}, {workerId: worker.id, workDate: '2026-08-28', mark: 'PRESENT'})
    expect(() => insertAttendance(first, {workerId: worker.id, workDate: '2026-08-28', mark: 'ABSENT'})).toThrow(/sudah tercatat/i)
  })

  it('previews bulk count and nominal before applying it', () => {
    const preview = previewBulkAttendance({
      action: 'MARK_ALL_PRESENT', workers: [worker], contractors: [normal],
      workDates: ['2026-08-27', '2026-08-28'], rates, book: {},
    })
    expect(preview.affectedCells).toBe(2)
    expect(preview.nominalAfter).toBe(225_000)
    expect(Object.keys(applyBulkAttendance({}, preview))).toHaveLength(2)
  })

  it('does not invent attendance when the previous week has no source record', () => {
    const preview = previewBulkAttendance({
      action: 'COPY_PREVIOUS_WEEK', workers: [worker], contractors: [normal],
      workDates: ['2026-08-28'], rates, book: {},
    })
    expect(preview.affectedCells).toBe(0)
    expect(preview.missingSourceCells).toBe(1)
  })

  it('treats attendance-exempt as data and never requires its roster', () => {
    expect(workerIsEligibleOn({...worker, contractorId: exempt.id}, exempt, '2026-08-28')).toBe(false)
  })

  it('keeps posted, corrected, and reversed periods immutable', () => {
    expect(canMutateAttendance('DRAFT')).toBe(true)
    expect(canMutateAttendance('POSTED')).toBe(false)
    expect(canMutateAttendance('CORRECTED')).toBe(false)
    expect(canMutateAttendance('REVERSED')).toBe(false)
  })

  it('keeps posted payroll nominal unchanged after the master rate changes', () => {
    const book = insertAttendance({}, {workerId: worker.id, workDate: '2026-08-28', mark: 'PRESENT'})
    const postedBook = snapshotAttendanceRates(book, rates)
    const changedMasterRates = rates.map((rate) => ({...rate, dailyRate: 999_000}))
    expect(attendanceEntryAmount(postedBook[attendanceKey(worker.id, '2026-08-28')], changedMasterRates)).toBe(125_000)
  })

  it('fails closed when posting tries to snapshot an attendance date without rate coverage', () => {
    const book = insertAttendance({}, {workerId: worker.id, workDate: '2026-08-28', mark: 'PRESENT'})
    expect(() => snapshotAttendanceRates(book, [])).toThrow(/rate pekerja.*belum tersedia/i)
    expect(book[attendanceKey(worker.id, '2026-08-28')].rateSnapshot).toBeUndefined()
  })

  it('requires the initial rate to cover the first employment date', () => {
    expect(initialRateCoversEmploymentStart('2026-08-26', '2026-08-26')).toBe(true)
    expect(initialRateCoversEmploymentStart('2026-08-20', '2026-08-26')).toBe(true)
    expect(initialRateCoversEmploymentStart('2026-08-27', '2026-08-26')).toBe(false)
  })

  it('clears only recorded cells through an explicit preview', () => {
    const book: AttendanceBook = {
      [attendanceKey(worker.id, '2026-08-28')]: {workerId: worker.id, workDate: '2026-08-28', mark: 'PRESENT'},
    }
    const preview = previewBulkAttendance({
      action: 'CLEAR', workers: [worker], contractors: [normal],
      workDates: ['2026-08-28', '2026-08-29'], rates, book,
    })
    expect(preview.affectedCells).toBe(1)
    expect(preview.nominalDelta).toBe(-125_000)
    expect(applyBulkAttendance(book, preview)).toEqual({})
  })
})
