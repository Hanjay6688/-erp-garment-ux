# Serah-terima penulis — audit penuh CP1–CP7 putaran 1

**Status: TAHAN penerimaan penuh.** Audit putaran 1 telah dikunci; selanjutnya perlu kandidat perbaikan dari penulis. Dokumen ini merangkum tindakan, tidak mengubah laporan/bukti putaran 1.

## Identitas dan bahan yang harus dibaca

- Kandidat yang diuji: `0b7049d9203bac52b47a4c89f3e0d75646067a8f`.
- Laporan dan ledger terkunci pada commit auditor `f70361d551d9dbc9931e330216901a8b702feab5`.
- [Laporan lengkap](https://github.com/Hanjay6688/-erp-garment-ux/blob/f70361d551d9dbc9931e330216901a8b702feab5/audit/astra_cp17/AUDIT_ASTRA_CP17_0b7049d9.md).
- [Temuan FIN-01 dan langkah reproduksi](https://github.com/Hanjay6688/-erp-garment-ux/blob/f70361d551d9dbc9931e330216901a8b702feab5/audit/astra_cp17/FINDING_FIN01_PAYROLL_DATE.md).
- [Status CP1 dan CP2](https://github.com/Hanjay6688/-erp-garment-ux/blob/f70361d551d9dbc9931e330216901a8b702feab5/audit/astra_cp17/CP1_CP2_EVIDENCE_REVIEW.md).
- Bukti asli, indeks arsip, manifest, sumber kasus, seluruh disposisi non-PASS dan batas pemeriksaan berada di direktori `audit/astra_cp17/` pada commit tersebut.

## 1. Perbaikan produk wajib — ASTRA-CP17-FIN-01

Pembayaran payroll biasa dapat bertanggal sebelum utang terkait diakui. Ketiga jalur yang terbukti adalah pembayaran penuh, cicilan final, dan cicilan sebagian. Saksi paling jelas: absensi1000 baru diakui13Okt, tetapi cicilan375,25 pada12Okt diterima, membuat utang kontraktor pada12Okt menjadi−375,25. Laporan tetap seimbang dan pemeriksaan integritas inti yang diuji tidak memberi alarm.

Perbaiki pemeriksaan ketersediaan utang pada tanggal pembayaran di batas native pemilik pembayaran. Pembayaran biasa hanya boleh melunasi sumber utang yang sudah tersedia pada tanggal itu. Jika proses kasbon diperlukan, gunakan sumber advance yang eksplisit dan klasifikasi akun yang benar. Jaga permission, version, lock, idempotency, tanggal ekonomi dan aturan periode tertutup. Gunakan forward correction; migrasi historis tidak diubah.

Sumber yang perlu ditelusuri: `scripts/cp7-src/payroll/settlement-write.sql`, `scripts/cp7-src/payroll/installments.sql`, `scripts/cp7_installment_bundle.py`, dan effective native payment/accrual yang dipasang oleh FULL composition. Jangan memperbaiki UI saja atau menggeser tanggal akrual diam-diam.

### Bukti penerimaan kandidat baru

| Kasus | Hasil yang harus diperlihatkan |
|---|---|
| PAY-04-EARLY-FULL |Pembayaran penuh yang melunasi akrual masa depan ditolak atomik |
| PAY-05-EARLY-INSTALLMENT |Cicilan final sebelum utang tersedia ditolak atomik |
| PAY-06-DATED-PARTIAL |Cicilan sebagian sebelum utang tersedia ditolak atomik; saldo dan laporan cutoff tidak berubah |
| PAY-01-CONTROL dan kontrol baru same-day/later |Pembayaran sah tetap berhasil tepat sekali |
| Partial/final, replay, reversal, reopened liability, closed period |Jumlah, sumber, tanggal, riwayat dan akun kontrol tetap benar; request/context/row tidak tertinggal pada refusal |
| Browser payroll desktop/HP dan pembacaan server/laporan |Penolakan tanggal salah jelas bagi pengguna; tanggal sah bisa disimpan dan hasil server/laporan sesuai |

Simpan hasil gagal asli putaran1. Uji kandidat perbaikan diberi identitas/manifest baru; jangan mengganti expected lama untuk sekadar menghasilkan hijau. Lakukan regresi yang terdampak dan pembuktian before/after. Auditor akan memeriksa perbaikan secara independen pada kandidat baru.

**Batas severity yang perlu dijaga:** S0 pada laporan didasarkan pada perubahan kewajiban/laporan dan tidak adanya alarm integritas inti yang diuji. Seluruh detector finansial lain serta seluruh banner UI belum diukur pada PAY-06. Sertakan hasil detector/report-confidence yang relevan pada kandidat baru; jangan menyatakan bahwa laporan Astra telah membuktikan semuanya diam.

## 2. Bukti historis CP2

Receipt writer `docs/cp7/evidence/writer-resume-20261005/CP2_ENCRYPTED_RECOVERY.json` membuktikan klaim pembukaan arsip149 anggota, bukan restore database yang telah diverifikasi Astra.

Pemegang arsip/kunci menyiapkan bukti restore disposable: identitas ciphertext, recipe dan engine, inventaris database/schema/owner/ACL, data dan control totals, invariant bisnis, kegagalan asli bila ada, serta cleanup. Secret tetap di lingkungan pemegangnya; jangan mengirim kunci kepada auditor. Restore sintetis CP7 modern tidak menggantikan CP2 historis. Jika bahan tidak tersedia, laporkan ketidaktersediaannya; status CP2 tidak diubah menjadi PASS.

## 3. Keputusan yang sudah ada dan rekap Fable

- A2 tetap OPEN dan diterima owner sebagai non-blocker melalui D13-10; dua log gagal asli dan batasnya tetap disimpan.
- A6 serta perbaikan backup F-OPS-05/ASR-OPS yang sudah diterima tidak dibuka kembali.
- CP7C/Drive tetap HOLD; `production_go:false`.
- Petunjuk Fable tentang tanggal payroll sudah terbukti dengan probe Astra. Dugaan absensi melalui Nota kedua ditolak pada dua jalur yang diuji; sumber HPP identik melalui kolam overlap ditolak pada saksi Astra. Tidak diklaim membebaskan semua kemungkinan jalur.
- Sembilan dugaan Fable lain belum tersedia rinciannya. Jangan mengarang, menutup, atau menandainya lulus.

## 4. Paket balasan yang diperlukan dari penulis

Berikan commit/tree kandidat baru, diff produk terpisah dari perubahan alat uji, pemetaan FIN-01 ke perbaikannya, manifest dan bukti tiap kasus, run/job/artifact beserta hash, restoration/owner/ACL/session gates, serta daftar risiko yang masih terbuka. CP2 dapat disertakan sebagai paket bukti historis terpisah.

Pemeriksaan lanjutan 14 Oktober 2026: cabang penulis masih `00b0eb24b2f014d102f0082111d13ee3be429cf2`; Fable masih `31cf30090b712897714f35c5a507cd1cd48c5d04`; cabang auditor tetap memiliki laporan terkunci tersebut. Belum ada kandidat revisi untuk dinilai. Dokumen ini disiapkan untuk diteruskan oleh owner; tidak ada pesan dikirim kepada penulis/Fable.
