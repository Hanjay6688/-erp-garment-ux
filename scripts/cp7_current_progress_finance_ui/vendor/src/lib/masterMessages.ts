// Indonesian text for the named refusals of the master-data and work-rate screens (schema cp7_master, owner D15-3) and of
// the cutover date (schema cp7_cutover, owner D15-5).
// The only caller is normalizeClientError, so every page shows one translation; 42501 keeps the generic access text.
const changed = 'Data ini baru saja diubah di layar lain. Muat ulang lalu periksa lagi.'
const messages: Record<string, string> = {
  CP7_MASTER_REVIEW_CHANGED: changed,
  CP7_WORK_RATE_REVIEW_CHANGED: 'Tarif atau komponen kerja ini baru saja diubah di layar lain. Muat ulang lalu periksa lagi.',
  CP7_MASTER_REQUEST_CHANGED: 'Permintaan berubah. Periksa hasil permintaan sebelumnya sebelum mengirim lagi.',
  CP7_MASTER_DUPLICATE_CODE: 'Kode itu sudah dipakai data lain. Pakai kode lain.',
  CP7_MASTER_CODE_IN_USE: 'Kode tidak bisa diganti karena data ini sudah dipakai transaksi. Nama dan kontak tetap bisa dibetulkan.',
  CP7_MASTER_NO_CHANGE: 'Tidak ada yang berubah.',
  CP7_MASTER_POLICY_DATE: 'Isi tanggal mulai berlaku untuk perubahan "Wajib absensi" atau "Mandor Special".',
  CP7_MASTER_POLICY_SAME_DAY: 'Sudah ada aturan absensi/Special yang mulai tanggal itu. Pilih tanggal lain.',
  CP7_MASTER_USE_RENAME: 'Nama dan kode bahan dibetulkan lewat bagian "Benerin nama bahan" di halaman ini.',
  CP7_MASTER_LOCATION_TYPE: 'Jenis lokasi itu dipakai sistem produksi dan tidak dibuat atau diubah dari sini.',
  CP7_MASTER_TYPE_IN_USE: 'Jenis lokasi tidak bisa diganti karena lokasi ini sudah punya mutasi stok (atau dipakai zona aksesori). Buat lokasi baru.',
  CP7_MASTER_UNIT_IN_USE: 'Satuan tidak bisa diganti karena kain ini sudah diterima atau dipakai.',
  CP7_MASTER_UOM_IN_USE: 'Satuan dasar tidak bisa diganti karena kategori ini sudah dipakai.',
  CP7_MASTER_UOM: 'Satuan itu belum terdaftar.',
  CP7_MASTER_UOM_CONVERSION: 'Satuan itu belum punya konversi ke satuan dasar kategori pada tanggal tersebut.',
  CP7_MASTER_CATEGORY_IN_USE: 'Kategori tidak bisa diganti karena varian ini sudah punya mutasi stok.',
  CP7_MASTER_CATEGORY_INACTIVE: 'Kategorinya tidak aktif. Aktifkan kategori dulu.',
  CP7_MASTER_SUPPLIER_INACTIVE: 'Supplier yang dipilih tidak aktif.',
  CP7_MASTER_MANDOR_INACTIVE: 'Mandor yang dipilih tidak aktif.',
  CP7_MASTER_BENCHMARK_DATE: 'Harga acuan baru harus mulai sesudah tanggal harga acuan terakhir.',
  CP7_MASTER_PRICE_DATE: 'Sudah ada harga yang mulai tanggal itu. Pilih tanggal lain.',
  CP7_MASTER_PRICE_USED_UNTIL: 'Harga lama sudah dipakai nota sampai tanggal itu; harga baru harus mulai sesudahnya.',
  CP7_MASTER_BLOCKED: 'Belum bisa dinonaktifkan. Lihat alasannya di layar.',
  CP7_MASTER_ALREADY_ACTIVE: 'Data ini sudah aktif.',
  CP7_MASTER_ALREADY_INACTIVE: 'Data ini sudah nonaktif.',
  CP7_MASTER_NOT_FOUND: 'Data tidak ditemukan. Muat ulang daftar.',
  CP7_MASTER_FIELDS: 'Isian belum lengkap atau formatnya belum sesuai.',
  CP7_MASTER_QUERY: 'Pencarian tidak valid.',
  CP7_WORK_RATE_FIELDS: 'Isian tarif belum lengkap atau formatnya belum sesuai.',
  CP7_WORK_RATE_LATER_VERSION: 'Sudah ada tarif yang mulai lebih lambat. Tarif baru harus mulai sesudah tarif terakhir.',
  CP7_WORK_RATE_USED_UNTIL: 'Tarif lama sudah dipakai upah sampai tanggal itu; tarif baru (atau penghentian) harus mulai sesudahnya.',
  CP7_WORK_RATE_USED: 'Tarif pada tanggal itu sudah dipakai upah dan tidak bisa diubah. Buat tarif baru dari tanggal sesudahnya.',
  CP7_WORK_RATE_NOTHING_TO_STOP: 'Tidak ada tarif yang berlaku pada tanggal itu.',
  CP7_WORK_RATE_COMPONENT: 'Komponen kerja itu tidak ada di daftar komponen kerja model ini. Tambahkan ke model dulu.',
  CP7_WORK_RATE_MODEL_INACTIVE: 'Model atau komponen kerjanya tidak aktif.',
  CP7_WORK_RATE_MANDOR_INACTIVE: 'Mandor ini tidak aktif. Aktifkan dulu sebelum mengisi tarif.',
  CP7_WORK_RATE_NOT_FOUND: 'Mandor, model, atau komponen tidak ditemukan. Muat ulang.',
  CP7_WORK_RATE_BOM_DATE: 'Komponen kerja model sudah dipakai upah; perubahan harus mulai sesudah pemakaian terakhir dan sebelum versi itu berakhir.',
  CP7_WORK_RATE_BOM_INACTIVE: 'Daftar komponen kerja model ini sudah dinonaktifkan dan tidak diubah dari sini.',
  CP7_WORK_RATE_QUERY: 'Pencarian tidak valid.',
  // Owner D15-5: the official cutover date (the refusals that carry their own sentence are passed through by clientError).
  CP7_CUTOVER_STALE: 'Tanggal mulai pakai aplikasi baru saja diubah di layar lain. Muat ulang lalu periksa lagi.',
  CP7_CUTOVER_NO_CHANGE: 'Tanggal itu sudah berlaku.',
  CP7_CUTOVER_DATE: 'Tanggal mulai pakai aplikasi harus antara 1 Januari 2000 dan satu tahun dari hari ini.',
  CP7_CUTOVER_REQUEST_CHANGED: 'Permintaan berubah. Periksa hasil permintaan sebelumnya sebelum mengirim lagi.',
  CP7_CUTOVER_FIELDS: 'Isian tanggal mulai pakai aplikasi belum lengkap atau formatnya belum sesuai.',
}
export function masterMessage(message: unknown): string | null {
  if (typeof message !== 'string') return null
  const upper = message.toUpperCase()
  const key = Object.keys(messages).sort((a, b) => b.length - a.length).find(k => upper.includes(k))
  if (!key) return null
  const date = /(\d{4}-\d{2}-\d{2})/.exec(message)?.[1]
  return date && (key.endsWith('_USED_UNTIL') || key === 'CP7_WORK_RATE_BOM_DATE') ? `${messages[key]} (Tanggal: ${date}.)` : messages[key]
}
