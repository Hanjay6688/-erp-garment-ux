# Disposisi counter browser sebelum CI

Ini review internal writer, bukan audit independen. COUNTER_INITIAL.json
mengunci penilaian kontrak sebelum implementasi/kesimpulan pemeriksa lain;
COUNTER_IMPLEMENTATION_INITIAL.json kemudian mencatat tiga celah alat uji.
Semua sumber awal, reproduksi sintetis dan keluaran pertama dipertahankan
byte-identik; COUNTER_PRESERVATION.json mencatat hash setiap salinan.

1. Reload setelah COMMIT bisa belum mengirim request ketika fault dilepas.
   Uji kini menunggu actual requestfailed, jumlah abort handler positif,
   pesan kegagalan refresh yang sudah settled, envelope bersih dan lock
   sebelum fault dilepas. Setelah itu menunggu respons200 pembacaan sumber
   yang segar dengan sale/version/E/AR yang tepat sebelum writer terbuka.
2. Toleransi satu piksel dihapus. Predicate kembali scrollWidth<=innerWidth.
3. Uji tidak lagi hanya melihat respons backend dan visibilitas panel:
   delapan pasang total before/after, hak kredit, tanggal retur/pengakuan,
   label review dan refund Rp100 dengan dua sumbu tanggal diperiksa di layar
   sebelum checkbox konfirmasi. Oracle berasal dari fixture/golden yang lama.

COUNTER_IMPLEMENTATION_FINAL.json mengikat hash sumber akhir dan menutup
ketiga celah di lingkupnya. Skrip portable:
`node docs/cp7/d17-14/ow04/browser-check/read_fault_schedule_recheck.mjs scripts/ow04-qualification/browser_cases.mjs /tmp/ow04-browser-counter.json`.
Ia menolak jadwal deferred read yang belum terkena fault, menolak event gagal
tanpa handler abort, menerima kontrol valid, dan menolak overflow391/390.
Itu simulasi klausul alat uji, bukan bukti browser/HTTP/database/Native.

Sesudah replay403, baseline penuh diambil setelah perubahan administratif;
sesudah restore, metadata keanggotaan yang sah tidak dihapus demi equality.
Ledger privat tetap sama, lalu seluruh keadaan dibandingkan terhadap baseline
post-restore pada replay berikutnya. Byte fixture tersimpan wajib cocok SHA
yang diterima Node saat persiapan dan golden wajib sama expected asli.

Belum ada hasil browser baru saat disposisi ini dibuat. Tetap wajib seluruh
empat kasus runtime, source restore, Auth cleanup, CP6/advisor dan kelima
gerbang paket luar. Dukungan keluarga terkoreksi/beberapa cohort/APPLY/undo,
UI produk default dan penerimaan independen tetap belum selesai.
