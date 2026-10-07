# Paket sumber writer ERP — kandidat staged 5.000 target

Sumber produk/alat bukti: `59d63e46ea5b109101a4e0a2eff7d27a8f3541f8`,
tree `2ac496cbacca2fe9ed1a924d0ffcc93bdb2b8844`. Status penutupan:
**kualifikasi writer 15/15 workflow dan 35/35 job sukses pada satu source**.
Ini bahan review writer; P20
independen dan penerimaan pemasangan P21 belum diberikan.

`SOURCE_MANIFEST.json` memuat setiap berkas dalam cakupan sumber yang
ditetapkan: frontend ERP, kontrak, SQL/skrip CP6/CP7, seluruh uji dan fixture
browser/kernel, workflow, aset/config
runtime, framework lengkap, seluruh direktori Supabase, serta acuan keputusan
owner dan penerimaan CP6. Inventaris diperluas menjadi 2.098 berkas.
Setiap berkas mempunyai ukuran, SHA-256 dan Git blob/mode. Hash Git lokal
dan tree GitHub identik. Manifest bukan klaim bahwa seluruh requirement
framework yang tercatat NOT_RUN sudah menerima bukti runtime.

## Jalur baca seluruh ERP

Master asli yang dirujuk framework juga ditemukan dan dipulihkan lengkap
untuk konteks writer: `ERP_V3_2_Master_Pulih_20260923.md` (681.195 byte,
7.236 baris, SHA-256
`f21ac70360915a1f1021b42a3918e862ca7d11cf88c1b90c5627b4490c69af07`)
dan `ERP_V3_2_Perubahan_Pulih_20260923.md` (131.244 byte,
SHA-256 `92966cd6ed27e64123be6c52e2263bfbdb3db91c97f2e441c3bdc98589397676`).
Sumber itu mempertahankan UX32, BR V3.1, reminder V2, aksesori/laundry,
33 AUD-ID dan kontrak CP7 rev3. Status AQ/CP6 HOLD/CP7 belum dimulai di
bagian awal master adalah sejarah September; penerimaan dan checkpoint
lebih baru dibaca dari keputusan owner serta receipt yang tepat.

"Lengkap" untuk pemulihan master berarti byte sumber yang tersedia,
bukan klaim bahwa seluruh percakapan dari semua chat/akun telah diperoleh.
Ringkasan writer tidak mengganti master, addendum atau receipt asli.

1. Urutan otoritas dan keputusan owner: framework `01_KONTRAK_DAN_INTEGRASI.md`,
   `06_RUSUK_KEBUTUHAN_OWNER.md`, `docs/AUDIT_PANDUAN_PRO_MAX.md`, serta
   `docs/cp6-d11-kebijakan-dan-gbd03.md`. Keputusan yang sudah disahkan tetap.
2. Framework lengkap: `docs/cp7/framework-v2/00_MULAI_DI_SINI.md` dan seluruh
   bab/kontrak/registri yang diindeks manifest. Paket framework historis
   berstatus persiapan; status implementasi saat ini berasal dari bukti writer.
3. Penerimaan CP6: `docs/cp7/acceptance/HANDOFF.md`; batas HOLD operasional,
   audit CP7 dan izin produksi dibaca terpisah.
4. Konteks produk dan pengambilalihan writer:
   `docs/cp7/handoff/GPT_WRITER_STAGED_5000_20261008.md`.
5. Rumus, perbaikan nyata dan temuan terbuka:
   `docs/cp7/SELF_CHECK_FORMULAS_20261006.md`.
6. Analisis staged: kontrak §10 `p19/P19_STAGED_5000_20261007.md`, deklarasi
   kasus `P19_STAGED.json`, `P19_SCALE.json`, sumber dan uji produk dalam manifest.
7. Bukti exact source/run/Original/gate:
   `docs/cp7/evidence/gpt-staged-5000-20261008/README.md` dan receipt di sana.

| Area | Fokus reviewer |
|---|---|
| Akses/pemulihan | Hak setelah lock, UUID lintas tab/rute, kegagalan refetch, satu transaksi koreksi/inverse. |
| Keuangan/laporan | Decimal eksak, retur/HPP/beban, jurnal/neraca/subledger, UNKNOWN dan tanggal ekonomi/WIB. |
| AP/pembelian/bahan | GRNI/invoice terlambat/kredit/retur/pembayaran, konservasi stok dan propagasi biaya. |
| AR/penjualan | Cadangan draf sekali, posting/retur parsial/realokasi, guard koreksi harga barang diretur. |
| Payroll | Kode pekerja, absensi versus upah, BS/sisa/kompensasi, cicilan/saldo negatif dan aturan Afui. |
| Produksi/laundry/SKU | Root fisik versus SKU komersial, lineage QC/ukuran, yield ditinjau, status produksi terpisah dari jual FG. |
| Perencanaan/model | Cutoff as-known, baseline/netting/jadwal/kain/aksesori, kapasitas dan konfigurasi yang diketahui. |
| Analisis/pengingat/AI | Acuan immutable, hasil penuh/halaman, sumber basi, keuangan DEFERRED, downstream staged belum tersedia. |
| UI/operasional | 48 rute, 111 izin, mode demo/terhubung, pesan penolakan, pemulihan dan pengukuran data siap digunakan. |

## P21: isi kompilasi dan cakupan latihan nyata

Ada dua kompilasi SQL deterministik, disimpan gzip tanpa kehilangan byte:

- `F03_REHEARSAL.sql.gz`: keluaran `cp7_f03_bundle.bundle()` yang benar-benar
  dipakai latihan P21 saat ini. Hash/ukuran ada di manifest.
- `FULL_RULE_SOURCE_WITH_STAGED.sql.gz`: keluaran
  `cp7_rule_source_bundle.bundle()`, termasuk seluruh rantai F03, perencanaan,
  analisis staged dan pengingat/local sink. Ini kompilasi untuk review calon
  paket gabungan; belum merupakan receipt rilis atau pemasangan hosted.

**Batas penting:** P21 hijau saat ini menguji komposisi F03. SQL F03 tersebut
tidak memuat `cp7_analysis_stage`. Native staged/analysis menguji instalasi
keluarganya sendiri; hasil itu tidak dipindahkan menjadi latihan P21 untuk
paket gabungan penuh. P21 USE juga ditahan dalam transaksi lalu di-rollback,
sesuai field Original `HELD_OPEN_THEN_ROLLED_BACK`; bukan bukti pemulihan
instalasi penuh yang sudah dipakai dan di-commit.

Kompilasi bergantung pada basis CP6 yang representatif, definisi pendahulu
yang dipin, grant eksplisit dan verifikasi installer. SQL ini tidak mengganti
admission/backup/restore harness. P21 rilis membutuhkan kandidat diterima P20,
uji T2 atas hasil pemasangan, pins/advisor/CodeQL, guard rollback sesudah
pemakaian dan pemulihan paket gabungan pada lingkungan sekali pakai.

## Status dan batas penerimaan

- Fitur staged yang dikualifikasi: request/step/status/page set/page/source
  check, acuan tunggal, paritas, hak, UUID, pause/resume dan buka ulang DONE.
  Tangga aplikasi Native/Auth/browser membuktikan seluruh 5.000 target
  pada 1/30/100 hari, semua 26 halaman dan hash/kontrak diperiksa. Receipt
  eksak ada di `59d63e46-scale5-retained/RECEIPT.json` dan
  `59d63e46-full-app-observations.json` dalam direktori bukti.
- Tiga detik adalah sasaran optimasi owner. Waktu hitung penuh, capture,
  acknowledgement, klik halaman dan membuka hasil selesai dicatat terpisah.
  Untuk 5.000 target: buka DONE 1,003–1,074 dtk; 75 klik halaman lanjutan
  0,554–0,723 dtk; hitung baru sampai halaman pertama 83,030–110,541 dtk.
  Pengukuran Chromium loopback sekali per vektor bukan SLA pabrik atau hosted.
- Nilai owner tetap terbuka: PL-5 B, konfigurasi nyata CP6, retensi staged,
  driver server, prioritas downstream staged, pilihan capture dan runner PL-8.
- Penggabungan `cp7/integration`, P20 independen dan P21 rilis belum terjadi.
  `independent_acceptance=false`, `installed_P21_acceptance=false`,
  `production_go=false`.

Kandidat sumber ini tetap dapat dibaca ulang pada SHA di atas apabila commit
dokumentasi/bukti berikutnya berbeda. Kelulusan CI selalu diikat ke SHA yang
benar-benar dijalankan, bukan otomatis ke HEAD terbaru.
