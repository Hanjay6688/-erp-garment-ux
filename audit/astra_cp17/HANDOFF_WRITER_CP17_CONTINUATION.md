# Kotak serah-terima penulis — hasil Astra CP1–CP7 dan lanjutan

Kandidat yang dinilai: `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`.

**Vonis: TAHAN penerimaan penuh.** Baca `AUDIT_ASTRA_CP17_CONTINUATION_0b7049d9.md` bersama laporan pertama yang terkunci pada `f70361d551d9dbc9931e330216901a8b702feab5`. Laporan pertama dan ledger hasil merah tidak ditimpa. Produk dan cabang penulis tidak diubah auditor.

## 1. Perbaikan produk yang sudah terbukti: FIN01

Pembayaran payroll biasa (penuh, cicilan final, dan sebagian) dapat mendahului akrual utangnya. Saksi terbaru: akrual 13 Oktober, bayar 375,25 tanggal 12 Oktober diterima; payable kontraktor cutoff −375,25, liabilities laporan 1759 → 1383,75, balance_difference tetap 0. Seluruh 135 baris detector integrity/v267/v268 tetap nol. Report confidence sudah BLOCKED sebelum/sesudah karena delapan masalah seed lain yang sama; Astra tidak mengklaim semua UI diam atau laporan READY palsu.

Perbaiki pada batas native pemilik pembayaran, bukan UI saja. Pembayaran biasa hanya melunasi utang yang tersedia pada tanggal itu. Advance/kasbon harus sumber eksplisit. Jaga current authority, lock, version, UUID replay, akrual dan tanggal ekonomi/pengakuan buku. Gunakan forward correction; jangan ubah migrasi historis.

Sumber utama: `scripts/cp7-src/payroll/settlement-write.sql`, `scripts/cp7-src/payroll/installments.sql`, `scripts/cp7_installment_bundle.py`, dan effective native payment/accrual dalam FULL composition. Detail pertama: `FINDING_FIN01_PAYROLL_DATE.md`; observasi tambahan: `FIN01_FULL_OBSERVATION.json` dan Original run `38559168896`, job `115835678985`, artifact `11891897967`.

Bukti penerimaan kandidat baru:

| Wajib | Expected |
|---|---|
| PAY04 full, PAY05 final, PAY06 partial dan FIN07 | Tanggal sebelum sumber akrual ditolak atomik; laporan cutoff tidak berubah; tidak ada sisa request/context/row. |
| Same-day/later, sumber campuran, partial→final | Jalur sah selesai; hanya sumber yang tersedia pada tanggal bayar dilunasi, jumlah/akun/pihak tepat. |
| Replay, lost reply, reversal/reopened liability, periode tertutup | Tidak menggandakan kas/settlement; history dan kontrak D01 dipertahankan. |
| Detector | Sebelum/saat/setelah lengkap, positive/negative control, payable bertanggal tidak lolos diam-diam. |
| Browser payroll desktop/HP + server/report reread | Pesan tanggal salah jelas; jalur tanggal sah tetap selesai dan angka server cocok. |

Berikan diff produk, commit/tree baru, manifest sebelum eksekusi, case ID/oracle/source hash, run/job/artifact, bukti sebelum/sesudah dan restoration/ACL/session gates. Auditor akan memeriksa kandidat baru secara independen. Semua hasil gagal kandidat lama disimpan.

## 2. CP2 tetap bukti historis yang kurang

Receipt `docs/cp7/evidence/writer-resume-20261005/CP2_ENCRYPTED_RECOVERY.json` menunjukkan pembukaan arsip 149 anggota; itu belum restore database yang diverifikasi auditor. Pemegang arsip/kunci menyiapkan restore disposable dengan identitas ciphertext, recipe/engine, schema-owner-ACL, data/control totals, invariant dan cleanup. Secret tetap di lingkungan pemegangnya; jangan kirim kunci ke auditor.

Jika tidak tersedia, laporkan ketidaktersediaannya. Rekomendasi Astra: bukti restore diperlukan sebelum klaim penuh CP1–CP7; pengecualian scope hanya keputusan owner eksplisit, bukan mengubah CP2 menjadi PASS. P21 modern tidak menggantikan CP2.

## 3. Materi Fable baru: rekap, bukan tuduhan yang otomatis sah

Snapshot Fable `1826aec19595c0e78f7a26107d77e0c445c94408` masih draft. Seluruh 31 butir R1/R3/R4 direkap di `FABLE_CONTINUATION_REVIEW.md`, dengan tiga Original runtime dibaca langsung. R1-05 satu akar dengan FIN01. R1-03 ditolak oleh guard pada probe Astra. R1-01 belum ditutup untuk varian dua Mandor/periode berbeda.

Prioritas pembuktian tambahan: R3-01 all-BS rework/payroll; R3-08 reopen→re-POST tanggal lama; R1-02 policy denominator; R3-03 klaim dengan fixture sah. Ketiganya/varian lain tidak dianggap bug terbukti hanya dari static review. Khusus R3-03, PASS pada chain4 berasal dari penolakan karena BS=0, sehingga belum menguji tanggal settlement. Jangan gunakan hasil itu untuk menutup dugaan.

Catatan dokumentasi AC/release manifest disertakan, tanpa permintaan mengedit migrasi historis atau melonggarkan guard. Tindak lanjut statis dibedakan dari wajib perbaikan FIN01; jangan membangun aturan bisnis baru tanpa kontrak/keputusan owner.

## 4. Keputusan dan batas yang tetap

- A2 tetap OPEN, diterima non-blocker oleh D13-10. Penyebab dua run lama belum diketahui; log aslinya tetap disimpan.
- A6 dan F-OPS-05/ASR-OPS yang sudah diterima tidak dibuka lagi. Dua selector SALES_MANUAL_13 usang tetap dicatat merah dengan bukti pengganti P11 kandidat sama.
- CP7C/Drive tetap HOLD, `production_go:false`.
- Matriks 271 requirement + 84 charter + 10 kebutuhan owner adalah review cakupan beserta bukti/batas, bukan klaim semua klausul lulus atau semua hipotesis baru selesai.

Dokumen ini siap diteruskan oleh owner. Astra tidak mengirim pesan langsung kepada penulis/Fable dan tidak memberi izin produksi.
