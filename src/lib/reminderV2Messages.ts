// Reminders v2 (reminders from a staged run's dated snapshot): refusals of a
// request in words. A condition that changed since it was read is 40001 and is
// never retried on its own; the screen asks to read it again first.
export function reminderV2Message(message: unknown): string | null {
  if (typeof message !== 'string') return null
  switch (message.trim().toUpperCase()) {
    case 'CP7_REMINDER_V2_CONDITIONS_NOT_READY': return 'Daftar pengingat dari analisis ini belum selesai disiapkan. Siapkan dulu daftarnya.'
    case 'CP7_REMINDER_V2_CONDITION_CHANGED': return 'Kondisi ini sudah berubah sejak terakhir dibaca (misalnya ada pembayaran). Baca ulang, lalu coba lagi.'
    case 'CP7_REMINDER_V2_NOT_ACTIVE_IN_SNAPSHOT': return 'Menurut analisis per waktu itu, kondisi ini tidak perlu ditangani. Tidak ada pratinjau yang dibuat.'
    case 'CP7_REMINDER_V2_IDENTITY_CHANGED': return 'Analisis bertahap di layar tidak sama dengan yang tersimpan di server. Muat ulang analisisnya.'
    case 'CP7_REMINDER_V2_SNAPSHOT_INDEX_MISSING': return 'Analisis ini dibuat sebelum indeks per target tersedia. Jalankan analisis baru.'
    case 'CP7_REMINDER_V2_PAYLOAD': return 'Isian pengingat tidak sah. Muat ulang daftarnya.'
    case 'CP7_LOCAL_COOLDOWN_OR_QUIET': return 'Pengaturan pengingat belum mengizinkan pratinjau sekarang (belum diatur, dimatikan, waktu tenang, atau masih jeda).'
    case 'CP7_LOCAL_BINDING_UNAVAILABLE': return 'Tujuan pratinjau lokal berubah atau dimatikan. Muat ulang pengaturannya.'
    case 'CP7_LOCAL_BINDING_STALE': return 'Tujuan pratinjau lokal sudah diubah dari sesi lain. Muat ulang pengaturannya.'
    case 'CP7_LOCAL_AMBIGUOUS_EPISODE_NO_NEW_OCCURRENCE': return 'Masih ada pratinjau lokal yang hasilnya belum pasti untuk kondisi ini. Pastikan dulu hasilnya.'
    case 'CP7_LOCAL_UNKNOWN_REQUIRED': return 'Hanya pratinjau yang hasilnya belum pasti yang bisa dipastikan.'
    case 'CP7_LOCAL_ALREADY_RESOLVED': return 'Hasil pratinjau ini sudah dipastikan sebelumnya.'
    case 'CP7_RULE_POLICY_STALE_REVISION': return 'Pengaturan pengingat sudah diubah dari sesi lain. Muat ulang pengaturannya.'
    case 'CP7_RULE_POLICY_CONFIG': return 'Isian pengaturan pengingat tidak sah (batas, satuan, jeda, atau waktu tenang).'
    case 'CP7_REMINDER_REQUEST_CHANGED': return 'Permintaan ini sudah dipakai dengan isi lain. Buat permintaan baru.'
    default: return null
  }
}
