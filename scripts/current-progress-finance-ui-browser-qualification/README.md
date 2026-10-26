# D17-18 — persiapan uji layar progres dan keuangan

VENI. VIDI. VICI. ERP. Reliable data adalah dewa.
Keuangan termasuk laporan, stok, dan HPP adalah raja.

Status: **belum terikat bukti Native6 dan belum dijalankan di browser asli**.
`CONFIG.json.choice_head=null` menolak binding; tidak ada `SOURCE.json`.
Hanya setelah Original Native6 yang tepat lulus, sumber backend disalin persis,
head hasilnya dicatat, lalu binder dan admission lengkap dijalankan.

Host A terdiri atas 112 berkas persis dari `0f818812`, termasuk 90 berkas B
tanpa perubahan. Fixture browser persis dari kandidat `389326f6` yang sebelumnya
lulus dua kasus layar. Pemeriksaan lama atas 24 angka laporan, UNKNOWN,
kehilangan respons, UUID tersimpan, hak akses, sumber tersegel, stok/uang/HPP,
kontras, lebar HP, dua salinan database, Auth asli, dan pemulihan tetap wajib.
Hasil uji lama bukan bukti bahwa layar progres baru ini sudah lulus.

Tambahan kasus membandingkan jumlah pekerjaan dan batang kemajuan layar dengan
respons RPC progres asli. Produksi selesai/keuangan berjalan, laporan READY,
laporan tertahan, buka ulang pekerjaan, dan pencabutan akses dibedakan. Jam
server diperiksa; total yang belum diketahui tidak diberi batang persentase.
Tidak ada batang kemajuan keseluruhan. Akun lain dan anonim ditolak oleh RPC.
Pengujian keuangan tetap memajukan pekerja melalui SQL fixture terpisah dan
tidak mengklaim cron sungguhan. Uji ini juga belum meliputi penerapan pembanding,
potong, skala seluruh pabrik, atau pemasangan bawaan aplikasi.

Cabang pelaksanaan tersendiri ada pada workflow. Cabang persiapan tidak memicu
uji database. Source guard memastikan host/B asli, penjaga bisnis lama, serta
dua salinan penuh dan pemulihannya. Lima uji terkendali memeriksa ketegasan
pembanding progres; ini bukan bukti produk berjalan di server.

`production_go=false`; `independent_acceptance=false`; formal 5/16 tetap terbuka.
