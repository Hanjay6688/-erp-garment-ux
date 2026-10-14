# Handoff uji ulang perbaikan CP1–CP7 r1 — untuk Sol

Owner menyalin **seluruh isi kotak di bawah** ke sesi Sol. Kandidatnya sama untuk Fable, Astra dan Sol. Rincian:
`README.md` dan `FINDINGS_TRACKER.md` di folder ini.

````text
Kamu Sol, auditor independen. Ini UJI ULANG perbaikan penulis atas temuanmu di audit penuh CP1–CP7
(audit/sol_cp1_7/AUDIT_REPORT.md, FINDINGS.json, WRITER_HANDOFF.md, 10bfe397, cabang
audit/sol-cp1-7-0b7049d9-20261014). Repo Hanjay6688/-erp-garment-ux. Fable dan Astra menguji ulang kandidat yang sama
secara terpisah.

KANDIDAT
- Commit <KANDIDAT>, tree <TREE>, cabang writer claude/new-session-deapao. Basis auditmu: 0b7049d9 (tree ce6aed0a).
- supabase/ tidak berubah sejak 0b7049d9 (buktikan: git diff --name-only 0b7049d9 <KANDIDAT> -- supabase kosong).
  Perubahan produk ada di scripts/cp7-src/ (lapisan CP7 + delta Native yang dideklarasikan) dan src/.
- Bukti penulis: docs/cp7/audit-candidate/cp1-7-fix-r1-20261015/README.md (per temuan), FINDINGS_TRACKER.md
  (bagian G), CI_RECEIPT.json (semua workflow dan job pada kandidat), docs/cp7/cp17/CP17_FIXES.json (40 kasus yang
  dideklarasikan sebelum dijalankan; workflow "CP7 CP17 Fixes").

YANG DIUJI ULANG (temuanmu → klaim penulis)
- SOL-001 bank saldo 0 bisa bayar supplier → D14-3: kas/bank tidak boleh minus pada tanggal mana pun, satu penjaga
  per rekening untuk semua pengeluaran, termasuk pembayaran bertanggal mundur dan dua pembayaran bersamaan.
  Kasus CP17_CASH_* (6), CP17_RACE_TWO_PAYMENTS_ONE_BANK, CP17_HTTP_CASH_EMPTY_BANK_REFUSED. Fixture yang membayar
  memakai modal owner lewat jurnal Native (scripts/cp7_cash_funding.py); kasus bank kosong tetap kosong.
- SOL-002 artefak BE 4/16 → folder keluaran tidak lagi dipindah saat impor AV; gerbang unggah memeriksa himpunan ID,
  status dan hasil akhir (scripts/cp6_av_probe.py, scripts/cp6_be_probe.py). Workflow "CP6 BE T1 Family Probe".
- SOL-003 + OPEN-AZ-FIRST → diagnosis PostgreSQL disimpan di berkas terpisah 0600 di sebelah laporan (juga proses
  lain di database saat gagal: jenis dan status saja). Catatan jujur: di CI berkas itu ikut artifact run (repo privat,
  data sekali pakai). Penyebab paling mungkin kegagalan pertama di AZ: autovacuum masuk ke database yang sudah
  ditutup dan blok pertama AZ menolak; log run pertamamu tidak menyebut blok mana, jadi ini belum terbukti. Pemasang
  owner sekarang menunggu proses lain keluar sebelum tiap berkas dan hanya mengulang penolakan
  PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE (transaksi berkas itu sudah batal); teks pengaman tidak berubah.
  scripts/cp6_readiness_owner_install.py, scripts/cp6_readiness_owner_drain_test.py (6 kasus; jalan di workflow CP17).
  Workflow readiness milik penulis terikat cabang cp6/release-readiness dan menolak cabang ini; jalankan pemasangan
  owner 58 berkas lewat workflow milikmu seperti sebelumnya, sebaiknya beberapa kali.
Juga periksa regresi di sekitar perubahan kas: upah, vendor laundry, kasbon (D14-6), dan pembalikan.

ATURAN PUTARAN
- Tanpa saling intip (Pro Max §2.2, §16.7): jangan membaca laporan, cabang, run, artifact atau komentar auditor lain
  dari putaran uji ulang ini sampai laporanmu dikunci dengan commit. Laporan yang sudah terkunci sebelum putaran ini
  (ketiga audit penuh atas 0b7049d9 dan addendumnya) boleh dibaca.
- Label asal-bukti per klaim (§2.9). Baca status per kasus dari log atau artifact, bukan warna job (§2.10). Rerun
  paling banyak sekali dan hanya bila job mati sebelum kasus berjalan (§1.9).
- Dispatch workflow writer hanya dengan ref claude/new-session-deapao dan catat head_sha yang terpakai; bila head
  sudah bergeser, buktikan tree produk sama sebelum memakai hasilnya (§1.7, §2.8, §16.1).
- Jangan percaya klaim penulis begitu saja: susun oracle sendiri dari kontrak dan keputusan owner (D14-2..D14-7).
  Keputusan owner yang sudah disahkan tidak dibuka ulang; pertanyaan yang sudah dijawab tidak ditulis ulang sebagai
  terbuka (§2.12).
- Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only), production. Jangan meminta password, token atau kunci di chat.
- Panduan: docs/AUDIT_PANDUAN_PRO_MAX.md (SHA-256 5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639,
  sama dengan saat audit penuh). Bila ada beda, berkas di repo yang berlaku.

LAPORAN
- Cabang audit baru, usul: audit/sol-cp1-7-retest-<KANDIDAT8>-20261015, berkas audit/sol_cp1_7_retest/RETEST_REPORT.md
  dan FINDINGS.json. Per temuan: DITUTUP / MASIH TERBUKA / BARU, dengan bukti.
- Ringkasan untuk owner dalam bahasa sehari-hari, pendek. Owner bukan programmer.
````
