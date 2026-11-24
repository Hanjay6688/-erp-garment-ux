// Owner decisions 8 Oct 2026, in words: a staged analysis is kept 7 days after
// it finished (then expired, never served again), and the history yield policy
// is saved by an owner or admin as a new version with a reason.
export function analysisRetentionMessage(message: unknown): string | null {
  if (typeof message !== 'string') return null
  switch (message.trim().toUpperCase()) {
    case 'CP7_ANALYSIS_RESULT_EXPIRED': return 'Hasil analisis ini sudah kedaluwarsa: hasil disimpan 7 hari sesudah selesai. Buat analisis baru.'
    case 'CP7_YIELD_POLICY_REVISION_CHANGED': return 'Kebijakan yield histori sudah diubah dari tempat lain. Muat ulang kebijakannya sebelum menyimpan lagi.'
    case 'CP7_YIELD_POLICY_REQUEST_CHANGED': return 'Permintaan simpan ini sudah dipakai dengan isi lain. Simpan sebagai permintaan baru.'
    case 'CP7_YIELD_POLICY_VALUES': return 'Isi jendela (1–3660 hari), minimal grup (1–1000) dan minimal PCS potong (1–1.000.000) sebagai bilangan bulat.'
    case 'CP7_YIELD_POLICY_CONFIDENCE_FIXED': return 'Tingkat keyakinan tetap 90% sesuai keputusan owner.'
    case 'CP7_YIELD_POLICY_REVIEW': return 'Pilih status dan isi alasan kebijakan.'
    default: return null
  }
}
