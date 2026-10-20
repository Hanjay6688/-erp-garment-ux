# Counter-review internal writer — 20 Oktober 2026

**Ini bukan audit independen atau izin produksi.** Satu penulis/integrator: sesi Codex utama,
cabang `astra/d17-14-20261020`. Kandidat audit `55c885d1` tidak diubah.

## Sumber dan kepemilikan

Repo diperbarui dari remote: Claude `41b5b0eb0d3a0dd0640005b88698c35b2eb3611d`;
sesudah serah-terima `5fd5d38e` hanya dua dokumen keputusan/scope yang berubah.
Cabang writer remote cocok `0bde7153` sebelum publikasi checkpoint ini. Tidak ditemukan perubahan
produk baru dari writer lain pada scope tersebut; ini observasi repo, bukan jaminan visibilitas semua sesi.
Mandat owner terbaru menetapkan sesi utama sebagai satu-satunya penulis/integrator.
Tidak ditemukan AGENTS.md di repo/ancestor yang diperiksa; CLAUDE.md tetap berlaku.

Sumber dibaca ulang: CLAUDE.md, AUDIT_PANDUAN_PRO_MAX.md, ERP_BEST_PRACTICES.md,
erp-reliability-invariants.md, OWNER_DECISIONS_20261008.md sampai D17-15,
OPEN_WORK_D17_14_20261020.md dan HANDOFF_ASTRA_WRITER_D17_14_20261020.md.
Lingkup kini **16 butir**: 15 D17-14 ditambah OW-16 D17-15, sebelum paket OW-15.
OW-16 menilai total PCS menurut bahan + pola + rentang ukuran, bukan vektor hasil per ukuran;
tanpa WA/Pengingat, minimum riwayat dan lebar rentang tidak dikarang.

Laporan Astra r5 dibaca dari commit terkunci `ff9fc3dab59641b15348eb316eb8a30269ad6fc4`:
RETEST_ASTRA_17fa2507.md, FINDINGS.json, REPORT_LOCK.json. Bukti 396 slot / dua INCOMPLETE alat
yang mempunyai kualifikasi tetap bukti kandidat `17fa2507`; bukan bukti runtime perubahan writer ini.
Kecepatan 100 target finansial 1,88–2,19 detik / 300 target 6,57–7,75 detik tetap historis.

## Konfigurasi dan metode

Owner akhirnya memilih empat pembantu **GPT-6.1 Sol, reasoning max**.
Empat pemanggilan spawn menerima konfigurasi tersebut: max_contract_ui, max_sql_counter,
max_finance_hpp, max_stock_corrections. Konfigurasi Ultra sebelumnya dihentikan setelah koreksi owner.
Tidak ada klaim kesamaan kemampuan, harga, jumlah token, atau konfigurasi komputasi tersembunyi.
Semua pembantu dilarang membuat agen dan mengedit file produk. Tidak ada patch produk dari pembantu.

Penilaian awal memakai commit lokal sama `5e4554247b5e0a8c6d71d6687d6e77e6c79989b2`,
tree seluruh repo `d102d7fa59860f5d1bdda6e5b993551b004736bf`, serta sumber kontrak yang sama.
Kesimpulan pemeriksa lain baru dibagikan setelah penilaian awal masing-masing tercatat di pesan sesi.
Pasangan counter: UI ↔ SQL dan uang/HPP ↔ stok/koreksi. Seluruh hasil berlabel
**INTERNAL_WRITER_SOURCE_REVIEW**; persetujuan pemeriksa tidak dihitung runtime PASS.

## Temuan, tantangan dan disposisi

| Skenario dan expected | Observed awal | Penyelesaian / batas bukti |
|---|---|---|
| Laporan/pengingat ditolak 42501 atau jaringan tidak pasti: fakta lama harus hilang (INV-UI02/L07) | catch hanya menulis pesan, fakta/preview dan kontrol masih ada | 4 kasus merah di 5e455424; perbaikan 155d9dc7 memberi 14/14 DOM. UUID yang belum pasti tetap disimpan. |
| StorageEvent recovery saat pembacaan lama tertahan: fakta tidak boleh hidup lagi | listener hanya memuat UUID, tidak membatalkan generasi baca | Dua kasus merah di 155d9dc7; reset fakta + generasi; balasan lama tetap diabaikan. |
| Pengingat semula DONE, workspace baru RUNNING/FAILED/tidak ada | halaman DONE lama masih terlihat | Tiga kasus merah; halaman/check/preview/live dikosongkan untuk keadaan belum siap. |
| Revisi A lalu buka publikasi B: konfirmasi/seri A tidak boleh dipakai | base A dan reviewed bertahan | Satu kasus merah; membuka publikasi membatalkan base dan konfirmasi. Total putaran kedua 6 merah→20/20 DOM. |
| Buka ulang tidak membuat pekerjaan baru; hasil sama | observer dipasang sesudah mount; laporan hanya cek id, analisis hanya elemen terlihat | Observer sebelum navigasi; cek run/identity/hash/ringkasan dan run/hash/semua target. Browser baru belum lulus CI saat dokumen dibuat. |
| Dispatcher menjaga pelaku, akses akhir, kunci, rollback, JWT dan private grants | Tidak ditemukan kontra-contoh SQL dari telusur kedua pemeriksa | Bukan bukti runtime. Tambah dua kasus timeout tabel asli dan asersi ketiga JWT sebelum commit pada balapan. Manifest 32 tepat. |
| Dugaan WAITING tidak terambil karena started_at kosong | SQL menetapkan NOT NULL dan mengisinya | Hipotesis ditolak dari definisi sumber, tidak diubah produk. |
| WA run terbaru harus menguji SQL 0bde7153, bukan label product_ref lama | Metadata legacy menulis 39212271 | Rekonstruksi 58 modul/186 pembacaan sumber menghasilkan 2.903.090 byte dan hash sama dengan CI; SQL392 berbeda. Batas metadata dicatat di receipt WA. |

Putaran kedua sempat menghasilkan dua kegagalan prasyarat karena pembersihan halaman DONE terlalu luas;
log percobaan tetap disimpan. Koreksi mempertahankan expected, membatasi pembersihan pada perubahan keadaan/hak.
Semua log merah/hijau dan cara reproduksi ada di `ow02/README.md`.

## Temuan uang/HPP untuk implementasi berikutnya — belum diperbaiki

- **OW-07:** aktivasi dan pembatalan pool absen yang aktif memanggil rebuild/propagasi/GL,
  tanpa residual FINISHED yang dipakai pool kain kantong. Prediksi 10 PCS dijahit, 8 Good + 2 BS,
  pool Rp1.000: Rp800 FG dan Rp200 residual WIP. Ini **prediksi belum dijalankan**, bukan S0 runtime terbukti.
  Perlu dua delta Native terdaftar dan fixture aktivasi/cancel terpisah, WIP per PO + jurnal + detektor tepat.
- **OW-07:** rantai close→readiness→BF period_blockers tidak mempunyai pemeriksaan sumber absen/kain kantong
  belum dialokasikan. Detektor yang ada memeriksa sumber alokasi yang sudah ada, bukan sumber yang terlewat.
  Perlu kontrol sumber sebenarnya, termasuk kebijakan HPP yang kosong, dan uji close tertahan→alokasi→boleh.
- **OW-04:** retur invoice lunas belum punya penyelesaian uang kembali/kredit pelanggan untuk penjualan Native.
  Guard overpayment sah untuk pembukuan AR-only; jangan dihapus atau memakai kredit migrasi BB palsu.
  Kredit/refund, status, detektor, pembatalan dan koreksi pembayaran memerlukan satu sumber saldo yang konsisten.
- **OW-05:** histori work/sewing/WIP/pool yang sudah dibalik masih menghalangi pickup; memperbaiki filter saja
  tidak menyelesaikan Native pickup POST, snapshot tarif, lock payroll dan tanggal pembalik.
  Perlu generasi koreksi ber-lineage dan urutan buka PO/undo dependensi yang ditinjau, tanpa menghapus histori.

Rincian source/fixture disimpan di `NEXT_MONEY_WORK_SOURCE_REVIEW.md`. Tidak ada temuan uang di atas
yang ditutup lewat voting. Belum ada sengketa kebenaran yang diputuskan tanpa sumber/pengujian;
kekurangan bukti Native tetap eksplisit.

`feature_complete:false`, `audit_complete:false`, `production_go:false`.

## Lanjutan saat writer aktif kembali — OW-02/03

Empat pembantu baru GPT-6.1 Sol Max (fork kosong, dilarang membuat anak atau
mengubah produk): `max_ow02_failure`, `max_ow03_sql`, `max_ow03_ui`,
`max_ow03_native`. Semua mendapat base333005ed dan patch sama
`fa614dcdf21a74fd7c0f85e79d6ee1f48e624c7d8e309b0962208545b7a27476`.
Sesudah penilaian awal dikunci, UI/SQL serta Native/SQL saling menantang
kontrak dan fixture. Review final dibatasi pada patch
`8b65c8871ee322272eccd23f44f1f645b27461c851b6a9a769be1f5c8e3e2157`.

| Skenario / expected | Observed dan bukti | Disposisi |
|---|---|---|
| Hasil pengingat server dan halaman sama untuk satu referensi | CI28/32; satu perbandingan gagal karena waktu baca publik memang berbeda, meski hash/total sama | Stored rows seluruh kolom harus persis sama; setiap clock harus cocok read_at halaman dan berada dalam batas clock DB. Semua field publik lain tetap persis dibandingkan, dengan diagnosis selisih. Native ulang menunggu. |
| Actor dicabut sebelum/di tengah pekerjaan, tanpa output parsial | Tiga fixture mencoba mencabut OWNER terakhir, ditolak sebelum penjalan diuji | OWNER kedua administratif dibuat sebelum capture; actor, pencabutan, guard dan expected semula tetap. Pemeriksa scoped final tidak menemukan pelemahan; runtime menunggu. |
| Kelipatan opsional: legacy/replay, exact PCS, ASSUMED refs, gap dan bahan tetap | Tidak ditemukan cacat aritmetika/kontrak pada patch; bukti aktual analisis awal belum ada karena F04 hanya baseline | Tambah Native complete same-reference parity dua root, BOM186, clear/arsip dan dua publikasi; browser langsung/bertahap96+3. Runtime belum diklaim. |
| Sesi RPC401 harus menghapus fakta, walau identitas provider belum berubah | Tiga catch bertahap hanya menghapus FORBIDDEN; ketiga DOM baru gagal | Reset state bertahap untuk AUTH_REQUIRED dan FORBIDDEN, termasuk generasi baca;17/17 DOM lulus. |
| Produk acak boleh muncul pada halaman mana pun | Browser baru berasumsi halaman0 | Tiga pemeriksa menemukan risiko yang sama secara terpisah. Writer menelusuri rentang sampai produk ditemukan dan kembali ke halaman0 untuk kontrol lama; tidak mengubah pemeriksaan kuantitas. |

Pemeriksa SQL melaporkan eksekusi sintetis tambahan (helper, compiler, laporan,
upgrade/profile/ACL). Harness terpisahnya tidak diarsipkan di sini; laporan
itu tidak digunakan sebagai bukti kualifikasi Native. Bukti lokal writer
yang dapat dijalankan ulang, kegagalan awal, dan batas ada pada `ow03/README.md`.
Belum ada perselisihan kebenaran terbuka; kekurangan runtime tetap terbuka.
Risiko reuse alat browser lama: tombol jeda berganti nama saat penjalan aktif,
dan status progres dapat berlalu cepat. Suite staged mandiri tidak memasang
penjalan; bukti gabungan tidak diklaim dari suite tersebut.
