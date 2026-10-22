const messages: Record<string, string> = {
  CP7_MANDOR_CORRECTION_STALE_REVIEW: 'Dokumen PO atau data mandor berubah. Periksa ulang dokumen pengunci dan pilih mandor lagi.',
  CP7_MANDOR_CORRECTION_REQUEST_CHANGED: 'Isi koreksi berbeda dari permintaan yang sudah tersimpan. Periksa hasil permintaan lama sebelum membuat koreksi lain.',
  CP7_MANDOR_CORRECTION_DEPENDENCIES: 'Masih ada dokumen yang mengunci mandor. Periksa ulang daftar pengunci dan balik dokumen asal sesuai urutannya.',
  CP7_MANDOR_CORRECTION_TARGET: 'Pilih mandor aktif yang berbeda dari mandor PO saat ini.',
  CP7_MANDOR_CORRECTION_NOT_FOUND: 'PO koreksi tidak ditemukan. Muat ulang WIP & Jahit.',
  CP7_MANDOR_CORRECTION_PICKUP_SOURCE: 'Riwayat pembagian PO belum cocok. Periksa seluruh pembagian sebelum mengoreksi mandor.',
  CP7_MANDOR_CORRECTION_FIELDS: 'Periksa PO, mandor pengganti dan alasan koreksi, lalu periksa ulang dokumennya.',
  CP7_MANDOR_CORRECTION_INCOMPLETE: 'Koreksi belum memenuhi pemeriksaan akhir dan seluruh perubahannya dibatalkan. Muat ulang dan periksa dokumen asal.',
}
export function mandorCorrectionMessage(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const code = value.match(/^CP7_MANDOR_CORRECTION_[A-Z_]+/)?.[0]
  return code ? messages[code] ?? null : null
}
