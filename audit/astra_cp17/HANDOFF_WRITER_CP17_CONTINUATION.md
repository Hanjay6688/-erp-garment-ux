# Kotak serah-terima penulis — hasil Astra CP1–CP7 dan lanjutan

Kandidat yang dinilai: `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`.

**Vonis: TAHAN penerimaan penuh.** Baca `AUDIT_ASTRA_CP17_CONTINUATION_0b7049d9.md` bersama laporan pertama yang terkunci pada `f70361d551d9dbc9931e330216901a8b702feab5`. Laporan pertama dan ledger hasil merah tidak ditimpa. Produk dan cabang penulis tidak diubah auditor.

## 1. Perbaikan produk yang sudah terbukti: FIN01, RWK01, STK01, FIN02, HPP01

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

### RWK01 — hak upah rework sesudah SCRAP

Dua komponen ×30 sudah mengakui utang60. Setelah hasil all-BS lalu SCRAP, view eligible dan kartu Nota kosong; kontrol hasil GOOD berhasil masuk Nota60. Selaraskan reader, validator dan allocation dengan hak kerja yang benar-benar terjadi. Saksi asli harus bisa menjadi Nota dan dilunasi tepat sekali; uji mixed/partial, WRITE_OFF/HOLD sesuai kontrak, duplicate source, reversal dan browser. Baca `FINDING_RWK01_REWORK_ENTITLEMENT.md`.

### STK01 — kartu stok historis sesudah posting ulang potongan

Beli10, potong10, REOPEN, lalu POST10 lagi dengan tanggal potong lama diterima. Kartu CURRENT_RESTATED memberi prefix−10, saldo sekarang0. Selaraskan proyeksi effective history/writer pengganti/cost/readers sambil menjaga audit trail dan current-clock inverse yang diterima. Jangan menghapus riwayat atau menganggap larangan semua koreksi sebagai fitur selesai. Uji sampai re-POST, variasi qty/tanggal/periode, replay/dependency, seluruh baris GL dan laporan cutoff; tambah detector dan browser. Baca `FINDING_STK01_CUTTING_HISTORY.md`. Tidak diklaim seluruh HPP/GL salah dari bukti header saja.

### FIN02 — settlement klaim laundry sebelum sumber

Vendor baru punya invoice80 dan klaim MISSING1 pada9Okt. ACCEPTED20/SETTLED pada8Okt diterima: datedAP0→−20, liabilities1859→1839, laba0→20. Seluruh135detector tetap0; confidence/preflight BLOCKED oleh delapan seed lama yang sama. Kontrol9Okt PASS. Perbaiki native settlement capacity menurut tanggal/sumber tanpa melarang D12 kredit lintas tagihan yang sudah disetujui. Uji MISSING/STUCK/DAMAGE sah, same-day/later, replay/race/reversal/closed-period, detector dan browser. Baca `FINDING_FIN02_LAUNDRY_CLAIM_DATE.md`.

### HPP01 — pool aktif menjadi stale sesudah policy baru

Pool1000/10=100 sudah ACTIVE; penambahan policy retroaktif untuk Mandor C yang sebelumnya excluded diterima. Native validator langsung menyatakan STALE_POOL_INPUT, tetapi status ACTIVE dan alokasinya tetap,135detector tetap0. Perbaiki dependency eligibility yang belum tercatat pada child pool, dengan penolakan atomik atau alur cancel/koreksi sah. Uji kasus asli, irrelevant policy, effective-date boundary, cancellation→replacement, race, detector dan HPP hilir/browser. Jangan mengklaim angka laporan hilir yang belum diukur. Detail `FINDING_HPP01_ACTIVE_POOL_POLICY.md`.

### Alur yang belum lengkap dari penelusuran sumber

`SOURCE_GAPS_CP5.md`: SG-01 koreksi POSTED pickup (S1); SG-02 input→writer pengembalian sisa kain fisik (S1); SG-03 tagihan rewash berbayar same-SKU (S2, kontrak/rute). Ini kelas bukti STATIC, terpisah dari lima akar cacat runtime. Dua alur pertama perlu diselesaikan sesuai arahan koreksi/stock owner. Jangan memakai inverse pickup saldo awal untuk mengklaim pickup produksi tertangani, dan jangan menyamakan reported remaining dengan physical return. Untuk rewash, rekomendasi: sumber biaya jasa tersendiri saat berbayar, FREE/WAIVED eksplisit saat gratis.

## 2. CP2 tetap bukti historis yang kurang

Receipt `docs/cp7/evidence/writer-resume-20261005/CP2_ENCRYPTED_RECOVERY.json` menunjukkan pembukaan arsip 149 anggota; itu belum restore database yang diverifikasi auditor. Pemegang arsip/kunci menyiapkan restore disposable dengan identitas ciphertext, recipe/engine, schema-owner-ACL, data/control totals, invariant dan cleanup. Secret tetap di lingkungan pemegangnya; jangan kirim kunci ke auditor.

Jika tidak tersedia, laporkan ketidaktersediaannya. Rekomendasi Astra: bukti restore diperlukan sebelum klaim penuh CP1–CP7; pengecualian scope hanya keputusan owner eksplisit, bukan mengubah CP2 menjadi PASS. P21 modern tidak menggantikan CP2.

## 3. Materi Fable baru: rekap, bukan tuduhan yang otomatis sah

Snapshot Fable `1826aec19595c0e78f7a26107d77e0c445c94408` masih draft. Seluruh 31 butir R1/R3/R4 direkap di `FABLE_CONTINUATION_REVIEW.md`, dengan tiga Original runtime dibaca langsung. R1-05 satu akar dengan FIN01. R1-03 ditolak oleh guard pada probe Astra. R1-01 varian dua Mandor/periode berbeda sudah diuji: jumlah2000 tetap teralokasi2000, sumber payroll masing-masing sekali; overlap tujuan bukan dengan sendirinya duplikasi biaya.

R3-01/R3-08/R3-03 sudah dibuktikan lewat probe Astra dan menjadi RWK01/STK01/FIN02. R1-02 menjadi HPP01. Empat program CP5 lama telah dijalankan identik,1PASS/3INCOMPLETE. `CP5_EXACT_REVIEW.md` mempertahankan assertion cutting yang operand gagalnya belum diketahui dan dua ketidakcocokan fixture current; pada kandidat perbaikan, petakan predecessor dan delta current serta tampilkan operand guard tanpa menghapus pemeriksaan izin. Hasil merah asli tidak diganti. Jangan memakai PASS fixture Fable yang belum mencapai writer sebagai bukti tanggal benar. Setiap dugaan lain memiliki disposisi terpisah; bukti statis tidak menggantikan gate runtime.

Catatan dokumentasi AC/release manifest disertakan, tanpa permintaan mengedit migrasi historis atau melonggarkan guard. Tindak lanjut statis dibedakan dari lima akar cacat runtime; jangan membangun aturan bisnis baru tanpa kontrak/keputusan owner.

## 4. Keputusan dan batas yang tetap

- A2 tetap OPEN, diterima non-blocker oleh D13-10. Penyebab dua run lama belum diketahui; log aslinya tetap disimpan.
- A6 dan F-OPS-05/ASR-OPS yang sudah diterima tidak dibuka lagi. Dua selector SALES_MANUAL_13 usang tetap dicatat merah dengan bukti pengganti P11 kandidat sama.
- CP7C/Drive tetap HOLD, `production_go:false`.
- Matriks 271 requirement + 84 charter + 10 kebutuhan owner adalah review cakupan beserta bukti/batas, bukan klaim semua klausul lulus atau semua hipotesis baru selesai.

Dokumen ini siap diteruskan oleh owner. Astra tidak mengirim pesan langsung kepada penulis/Fable dan tidak memberi izin produksi.
