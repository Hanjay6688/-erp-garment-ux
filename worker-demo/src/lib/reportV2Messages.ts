// Business Report v2 (a report of a staged run's dated snapshot): refusals of
// a request in words. A revision that lost to another one is 40001 and is
// never retried on its own; the screen asks to open the latest version.
export function reportV2Message(message: unknown): string | null {
  if (typeof message !== 'string') return null
  switch (message.trim().toUpperCase()) {
    case 'CP7_REPORT_REVISION_CHANGED': return 'Seri laporan ini sudah direvisi dari permintaan lain. Buka versi terbaru, lalu buat revisi dari sana.'
    case 'CP7_REPORT_SERIES_SCOPE_CHANGED': return 'Revisi harus memakai jenis dan periode yang sama dengan seri laporannya.'
    case 'CP7_REPORT_V2_IDENTITY_CHANGED': return 'Analisis bertahap di layar tidak sama dengan yang tersimpan di server. Muat ulang analisisnya.'
    case 'CP7_REPORT_REQUEST_CHANGED': return 'Permintaan laporan ini sudah dipakai dengan isi lain. Buat permintaan laporan baru.'
    case 'CP7_REPORT_REVIEW': return 'Isi jenis, judul dan alasan laporan, lalu konfirmasi peninjauan.'
    case 'CP7_REPORT_REVISION': return 'Versi laporan yang direvisi tidak sah. Buka laporannya lagi sebelum membuat revisi.'
    case 'CP7_REPORT_V2_SECTION_UNAVAILABLE': return 'Bagian laporan ini tidak ada. Buka laporannya lagi.'
    default: return null
  }
}
