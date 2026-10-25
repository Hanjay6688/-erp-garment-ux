# Estafet Writer A — 26 Oktober 2026 WIB

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa.
Keuangan—termasuk laporan—stok, dan HPP adalah raja.

Owner meminta sesi ini menggantikan chat Writer A yang penuh, memulihkan konteks
ERP dan meneruskan A/integrasi. B boleh dibaca tetapi scope tidak ditukar. Ini
penulis A, bukan auditor independen. Tidak ada subagent baru.

## Kebutuhan yang dibawa

Garment/manufaktur dan grosir; toko adalah customer eksternal dengan akses
terbatas. Rantai bahan/roll–potong–mandor–laundry–QC–FG–jual/retur tersambung ke
stok, upah, AR/AP, GRNI, HPP dan jurnal. Epi/Selo/Afat/Afui tetap empat mandor;
aturan khusus Afui dan tarif mengikuti kontrak/master. Invoice laundry terlambat
berbulan-bulan bagian alur normal. Skala ±1.200 SKU, rata-rata tiga ukuran;
keanggotaan SKU tidak dipaksa selalu tiga. Lusin/PCS/box/pack eksplisit.

Satu sumber resmi untuk laporan dan analisis. Posted immutable; koreksi inverse
dan successor bertaut, latest corrected wins pada tampilan, snapshot laporan
terbit tetap dipertahankan. Waktu fisik/ekonomi/buku/pencatatan dibedakan, WIB;
periode tertutup tidak otomatis dibuka. Uang/stok/HPP/upah/lineage atomik.
Idempotensi UUID+payload; jawaban hilang bukan izin membuat transaksi baru.
Hak terkini diperiksa sesudah menunggu lock dan pada replay. UNKNOWN/PENDING/
INCOMPLETE bukan nol/gratis. Draft non-authoritative. FG/WIP/kredit/BS/good/
pembayaran/upah tidak dihitung dua kali. Sen tepat dan PCS bulat.

Satu transfer supplier multi-tagihan berarti satu kas keluar, alokasi partial
dan sisa utang jelas. Invoice harian toko, partial AR dan retur lunas refund/
kredit tetap dituju. Moving average, biaya aksesoris/BOM dan harga jual mandor
dipisahkan. Invoice terlambat/recost mengikuti raw/WIP/FG/COGS dan tanggal sah.
Rework membayar komponen sah tanpa pengulangan saat penutupan.

CP7 memakai satu mesin Stok/Planner/saran potong/Business Report/Reminder/Tanya
AI V1. WIP dialokasikan global; rekomendasi punya jumlah, kapan, alasan, sumber,
waktu dan ketidakpastian. Operasional boleh muncul lebih dulu; kesimpulan laba
menunggu angka resmi. Backtest membuktikan metode kompleks; data kurang menahan
aktivasi, bukan menghapus fitur. Analog dikonfirmasi pengguna; SAVE memeriksa
kelayakan ulang. Status potong menilai total PCS menurut bahan+pola+rentang
ukuran dari riwayat pabrik, tidak ke WA. Minimum lama referensi, satu aturan aktif.

UI hitam/biru, HP390 nyaman, search-first, filter gabungan, pilihan lintas
halaman, total/saldo seluruh hasil; ledger/lusin/sebelum-sesudah jelas. Angka
utama kontras4,5:1 dan tanpa luapan yang disembunyikan. Fitur akhir tersambung
di mode nyata. Biaya tambahan Rp0; produksi/hosted/WA nyata belum diotorisasi.

## Scope dan aturan penerimaan

Versi2/D17-17 berlaku. A: OW04/05/06/07/08/09/12a, langkah pemasangan OW14b dan
OW15; A satu-satunya integrator untuk installer/bundle/types/registry/migrasi/
paket audit. B: OW10/11/12b/13/14 tampilan-aturan/16. Adopsi B harus versi tepat
dan Original aktual; PASS komponen bukan PASS gabungan. Shared memakai commit
[bersama] terpisah, baris scope lain tidak diubah. Tanpa force-push/rebase.

Formal5/16, production_go=false, independent_acceptance=false; bukan persentase
teknis. Kebijakan belum diputus (absen tanpa jahitan, laundry overpay/piutang,
bagian kredit yang belum ditetapkan, batas koreksi HPP bila dikehendaki) tidak
dikarang. Lanjut bagian independen. Bukti CP6 lengkap,12 batas arsip,
Native286/currentB,21 gagal+4browser pembanding dan paket satu kandidat tetap
terbuka. Writer PASS tidak memberi izin produksi atau audit independen.

Sumber dibaca: AGENTS/CLAUDE, ERP_BEST_PRACTICES, pembagian versi2, keputusan
D17-14–17, OPEN_WORK, WRITER_A_SCOPE/ACTIVE/KOORDINASI, konteks A versi100 dan
bagian terbaru konteks writer versi60. Konteks domain/roadmap dari dasar handoff
A dipulihkan; bukan klaim seluruh transkrip setiap chat tersedia. Kontrak
domain tetap dibaca sebelum domain diubah.

## Posisi aktual yang melampaui handoff versi100

- Native45 a3088e21/run40222596942/art12611956497 PASS45;3644pin,24metrik,
  seluruh3602target,full22/rows/sequence dan lima gate. Bukan factory/Auth/default.
- Performance factory c17b56ed/run40227300626/art12613688822 INCOMPLETE:
  BF_HISTORY saat membuat membership10hari lalu. Pemulihan lulus; Original utuh.
- Public52 6dceb3d3/run40234978669/job121294499742 berjalan; privatefactory
  778ac17e/run40234971454/job121294477378 antre pada pengamatan estafet.
- B terakhir dibaca714766d1, koreksi cutting ee1ebfd1 dan handoff B208.
  A belum mengadopsi seluruh B terbaru; cabang/file B tidak diubah.

## Perbaikan yang telah diteruskan

Commit daab8075 menyimpan dua fixture. Yang benar-benar dijalankan adalah
scripts/current-factory-finance-runtime-qualification/fixture.py dengan
SHA256193197b3c288b382970250f2f3db4c38ea21e3fd45bb1729fe25f94ecbe5e3bd.
Original membuktikan fixture PASS1200×3 dan sembilan tabel posted persis;
run daab berhenti belakangan pada timeout analisis. Generator selanjutnya
menyalin sibling lama sha6dceb87... dan salah menyebutnya date-corrected.

Kandidat5bf4e03a37418545655f07a52582103348b17cd4/tree1bcf55aa menggunakan byte
fixture runtime daab persis: penjualan historis dahulu, membership sekarang
via Native per batch. Runner/probe privat persis; tidak mengubah produk/jam/
angka/guard/ACL/timeout/jadwal.65assert menjaga sejarah dan keuangan.12kontrol
negatif menolak salah sibling/pin palsu/sejarah berubah/guard dilonggarkan;
43shellsteps parse. Fulladmission3668pin/9Original PASS, receipt3211958byte
SHAf5c4c8b034c59c4ba7f197d480be47064ad884eddce8ca1324c3036812f1ce70.
Cabang eksekusi astra-a/d17-14-frozen-finance-factory2-20261026 telah dikirim: run40236661942/job121299590702 in_progress.
Belum runtimePASS. Versi lama/failure tidak diganti atau diulang tanpa perubahan.

## Lanjut

Pantau tiga run tepat; ambil Original lengkap, cek source/head/bytes/gates/
restoration dan arsipkan sekali. Pemeriksa factorydate2 harus memeriksa
current_native_membership_verified dan sembilan tabel posted; jangan memakai
field lama membership_effective_before_sales. Public52 tetap memerlukan
Auth/race/browser/cron/usedrestore tersendiri. Sesudah bukti aktual, lanjut
adopsi B bertahap, sisa A, kualifikasi terpadu dan paket auditor satu versi.
Checkpoint menyimpan kemajuan, bukan menyatakan seluruh scope selesai.
