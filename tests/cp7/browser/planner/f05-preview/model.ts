import type { ShellView } from '../../../../../src/cp7/workspace'

export type Page = 'production' | 'reports' | 'reminders' | 'ai'
export type PreviewContext = { view: ShellView; stale: boolean }
export const fixtureDate = '2026-09-30'

export type Period = { kind: 'daily' | 'weekly' | 'custom'; start: string; end: string }
// This harness has one dated snapshot, not a period reader. Never relabel the
// same numbers as weekly/custom results that were not actually captured.
export function periodAvailability(period: Period): string | null {
  if (!period.start || !period.end || period.start > period.end) return 'Tanggal awal harus terisi dan tidak melewati tanggal akhir.'
  if (period.kind === 'weekly' || period.start !== fixtureDate || period.end !== fixtureDate) return 'Data untuk periode ini belum tersedia. Pembaca periode P13 belum disambungkan.'
  return null
}

export type Archive = Readonly<{ id: string; runId: string; snapshotId: string; sourceHash: string; engineVersion: string; policyVersion: string; accessEpoch: string; text: string; period: Readonly<Period>; revisionOf: string | null }>
export function archiveReport(context: PreviewContext, period: Period, records: readonly Archive[], revisionOf: string | null): Archive {
  if (context.stale || !context.view.analysis || periodAvailability(period)) throw new Error('Snapshot atau periode belum siap diarsipkan.')
  if (revisionOf && !records.some(record => record.id === revisionOf)) throw new Error('Arsip asal tidak ditemukan.')
  const analysis = context.view.analysis
  return Object.freeze({ id: `local-report-${records.length + 1}`, runId: analysis.run_id,
    snapshotId: analysis.snapshot.snapshot_id, sourceHash: analysis.snapshot.source_hash, engineVersion: analysis.versions.engine,
    policyVersion: analysis.versions.policy, accessEpoch: analysis.versions.access_epoch,
    text: context.view.report, period: Object.freeze({ ...period }), revisionOf })
}

export type Attention = 'NEW' | 'ACK' | 'SNOOZED' | 'DONE' | 'CANCELLED'
export type Condition = 'REVIEW_REQUIRED' | 'UNKNOWN'
export type Episode = Readonly<{ id: string; title: string; condition: Condition; source: string; attention: Attention }>
export function changeAttention(episode: Episode, attention: Attention): Episode {
  return Object.freeze({ ...episode, attention })
}
export type QueueItem = Readonly<{ key: string; episodeId: string; runId: string; text: string; status: 'LOCAL_SIMULATION_ONLY' }>
export function enqueueSimulation(context: PreviewContext, episode: Episode, queue: readonly QueueItem[]): readonly QueueItem[] {
  if (context.stale || !context.view.analysis) throw new Error('Snapshot belum siap untuk antrean simulasi.')
  const key = `${context.view.analysis.run_id}:${context.view.analysis.scenario.version}:${episode.id}`
  if (queue.some(item => item.key === key)) return queue
  return [...queue, Object.freeze({ key, episodeId: episode.id, runId: context.view.analysis.run_id,
    text: `SIMULASI LOKAL — tidak dikirim\n${episode.title}\nKondisi: ${episode.condition}\n${context.view.report}`,
    status: 'LOCAL_SIMULATION_ONLY' as const })]
}

export const questions = [
  'Kenapa SKU ini perlu diperiksa sebelum produksi?',
  'Apa yang belum diketahui tentang bahan dan kapasitas?',
  'Sumber WIP mana yang masih bersyarat dan apa dasar ETA-nya?',
] as const
export function promptForQuestion(view: ShellView, question: string) {
  if (!view.analysis) return { text: '', blocked: true, truncation: 'Tidak ada snapshot berizin.' }
  const text = `${view.prompt}\n\nPERTANYAAN PENGGUNA (bukan instruksi transaksi):\n${question}`
  // Do not silently trim constraints, caveats, allocation edges, or sources.
  const blocked = text.length > 64_000
  return { text, blocked, truncation: blocked ? 'Payload melampaui batas pratinjau. Tidak dipotong; salin otomatis ditahan.' : 'Tidak dipotong. Seluruh payload contoh berizin ikut disertakan.' }
}
