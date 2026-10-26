// A integration projection for D17-18. No work is scheduled or advanced here.
// Accept only the existing, strictly validated source-bound server reply.
import {parseStagedJob, type StagedRequest} from '../cp7_current_frozen_finance_ui/vendor/src/nativeStagedJob'
import {planInstantMicros} from '../cp7_current_frozen_finance_ui/vendor/src/nativePlanInstant'

export const PROGRESS_POLICY = 'D17-18-20261026' as const
export type PhaseState = 'PREPARING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'BLOCKED' | 'ACCESS_REVOKED' | 'NOT_REQUESTED'
export type PhaseProgress = {state: PhaseState; done: number | null; total: number | null; percent: number | null; label: string; failureCode: string | null}
export type CombinedProgress = {
  policy: typeof PROGRESS_POLICY; requestId: string; state: PhaseState | 'EXPIRED'; complete: boolean
  operational: PhaseProgress; finance: PhaseProgress; overallPercent: null
  capturedAt: string; operationalLastProgressAt: string; financeLastProgressAt: null
  elapsedSinceCaptureMs: number | null; elapsedClock: 'CLIENT_OBSERVATION'; terminalDurationMs: null
  clockBeforeCapture: boolean; queuePosition: null; workerState: 'NOT_EXPOSED'
  recovery: 'SAME_REQUEST_STATUS' | 'NEW_REQUEST_AFTER_SOURCE_CHECK' | 'RESTORE_ACCESS' | 'NONE'
  message: string
}
const phase = (state: PhaseState, done: number | null, total: number | null, label: string, failureCode: string | null = null): PhaseProgress => ({
  state, done, total, percent: done !== null && total !== null && total > 0 ? Number(BigInt(done) * 10000n / BigInt(total)) / 100 : null, label, failureCode,
})

export function projectCombinedProgress(raw: unknown, request: StagedRequest, observedAt: string): CombinedProgress {
  const job = parseStagedJob(raw, request.id, request)
  const elapsedMicros = planInstantMicros(observedAt) - planInstantMicros(job.reference.capturedAt)
  const elapsedMs = elapsedMicros < 0n ? null : Number(elapsedMicros / 1000n)
  if (elapsedMs !== null && !Number.isSafeInteger(elapsedMs)) throw Error('Jam pengamatan tidak dapat dipakai.')
  const operational = phase(job.state === 'DONE' ? 'COMPLETED' : job.state === 'FAILED' ? 'FAILED' : job.planFinal ? 'RUNNING' : 'PREPARING',
    job.unitsDone, job.planFinal ? job.unitCount : null,
    job.state === 'DONE' ? 'Perhitungan produksi selesai' : job.state === 'FAILED' ? 'Perhitungan produksi gagal' : job.planFinal ? `Tahap produksi ${job.stageIndex} dari ${job.stageCount}` : 'Menyiapkan data produksi',
    job.failure?.code ?? null)
  const f = job.financeCapture
  let finance: PhaseProgress
  if (!f) finance = phase('NOT_REQUESTED', null, null, 'Angka keuangan tidak diminta')
  else if (f.state === 'ACCESS_REVOKED') finance = phase('ACCESS_REVOKED', null, null, 'Hak membaca angka keuangan tidak tersedia')
  else {
    const c = f.capture!
    const state = f.state === 'FAILED' ? 'FAILED' : f.state === 'READY' ? f.result?.readiness === 'READY' ? 'COMPLETED' : 'BLOCKED' : c.unitsTotal === null ? 'PREPARING' : 'RUNNING'
    finance = phase(state, c.unitsDone, c.unitsTotal,
      state === 'COMPLETED' ? 'Laporan keuangan resmi selesai' : state === 'BLOCKED' ? 'Perhitungan laporan selesai; data atau HPP belum lengkap' : state === 'FAILED' ? 'Perhitungan laporan resmi gagal' : state === 'PREPARING' ? 'Menyiapkan laporan resmi; jumlah langkah belum diketahui' : 'Memeriksa sumber laporan resmi', c.failureCode)
  }
  // Operational and financial units are different work. Adding/averaging their
  // percentages would invent an overall denominator. Do not publish one.
  const state = job.retention?.state === 'EXPIRED' ? 'EXPIRED' : finance.state === 'ACCESS_REVOKED' ? 'ACCESS_REVOKED'
    : operational.state === 'FAILED' || finance.state === 'FAILED' ? 'FAILED'
    : finance.state === 'BLOCKED' ? 'BLOCKED'
    : operational.state === 'COMPLETED' && ['COMPLETED', 'NOT_REQUESTED'].includes(finance.state) ? 'COMPLETED'
    : operational.state === 'PREPARING' && ['PREPARING', 'NOT_REQUESTED'].includes(finance.state) ? 'PREPARING' : 'RUNNING'
  const message = state === 'EXPIRED' ? 'Hasil melewati masa simpan. Buat analisis baru dengan sumber terkini.'
    : state === 'ACCESS_REVOKED' ? 'Bagian keuangan tidak dapat dibaca dengan hak saat ini.'
    : state === 'FAILED' ? 'Analisis belum lengkap. Periksa penyebab gagal sebelum memulai perhitungan baru.'
    : state === 'BLOCKED' ? 'Analisis gabungan belum lengkap karena data laporan atau HPP masih tertahan; angka yang belum diketahui bukan nol.'
    : state === 'COMPLETED' ? f ? 'Produksi dan laporan keuangan resmi selesai.' : 'Perhitungan produksi selesai; angka keuangan tidak termasuk.'
    : operational.state === 'COMPLETED' ? 'Produksi selesai. Analisis gabungan masih menunggu laporan keuangan resmi.'
    : 'Analisis belum selesai. Kemajuan setiap bagian ditampilkan terpisah.'
  return {policy: PROGRESS_POLICY, requestId: job.requestId, state, complete: state === 'COMPLETED', operational, finance,
    overallPercent: null, capturedAt: job.reference.capturedAt, operationalLastProgressAt: job.lastProgressAt,
    financeLastProgressAt: null, elapsedSinceCaptureMs: elapsedMs, elapsedClock: 'CLIENT_OBSERVATION', terminalDurationMs: null,
    clockBeforeCapture: elapsedMicros < 0n, queuePosition: null, workerState: 'NOT_EXPOSED',
    recovery: state === 'ACCESS_REVOKED' ? 'RESTORE_ACCESS' : ['EXPIRED', 'FAILED', 'BLOCKED'].includes(state) ? 'NEW_REQUEST_AFTER_SOURCE_CHECK' : state === 'COMPLETED' ? 'NONE' : 'SAME_REQUEST_STATUS', message}
}
