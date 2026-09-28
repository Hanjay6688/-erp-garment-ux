# Putusan akhir CP6 setelah verifikasi cakupan G04 — 29 September 2026 WIB

**CP6: CLOSED — INDEPENDENTLY ACCEPTED FOR CONTRACT SCOPE.**
**R10 / AUD-G04: OPEN pada CP7 full dummy sales flow.**
**`production_go=false`; tidak ada merge, deploy, atau penulisan ke production.**

Putusan ini menyelaraskan penerimaan revisi yang sudah selesai dengan master kontrak asli. R10 tidak menjadi syarat tambahan penutupan CP6 karena kontrak menempatkan UI penjualan/pembayaran/retur/refund pada CP7. Ini tidak menyatakan UI tersebut sudah berfungsi, tidak memberi PASS/N/A pada R10, dan tidak memindahkan bug backend CP6 ke tahap lain.

## Kandidat dan perubahan yang diperiksa

- Writer terbaru: `10a834712e515af86c6d8baa89bbe40cff9793e3`.
- Kandidat penerimaan sebelumnya: `fab23e77669f899594f983b41a6301c32246958b`.
- Fingerprint produk/paket yang diuji: `434b18215f57dd7a361ca621341488d3c31e9703`.
- BF release SHA-256: `9bf4b5642c9d6af3369f98ad265bd802ee993fac7e1d8d290412184588392643`.

Diff `fab23e7..10a8347` hanya lima dokumen handoff/bukti. `src`, `supabase`, `scripts`, dan `.github` identik; tidak ada perubahan produk, paket, rollback, workflow atau oracle. Bukti runtime pada byte produk yang sama tetap berlaku. Putaran ini melakukan pembacaan kontrak, pemeriksaan hash, dan rekonsiliasi cakupan; tidak mengaku menjalankan tes runtime baru.

## Verifikasi kontrak oleh auditor

Auditor mengambil berkas **master asli**, menghitung hash dari seluruh byte, dan membaca konteks klausulnya. Tidak hanya menerima kutipan di handoff writer.

| Sumber | Hasil |
|---|---|
| `ERP_V3_2_Master_Pulih_20260923.md` | 681195 byte |
| SHA-256 yang dihitung auditor | `f21ac70360915a1f1021b42a3918e862ca7d11cf88c1b90c5627b4490c69af07` |
| Pin M, bagian 1 addendum keputusan owner | Identik |

Pin diperiksa pada [addendum di commit writer terbaru](https://github.com/Hanjay6688/-erp-garment-ux/blob/10a834712e515af86c6d8baa89bbe40cff9793e3/docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25.md). Kutipan dan hash yang dihitung sendiri disimpan dalam [scope-evidence.json](scope-evidence.json).

Klausul yang menentukan:

- **R1.3, baris 1699:** kasus material yang belum selesai dalam scope CP6 tidak boleh diberi label lock; item CP7 dan tahap berikutnya tetap terbuka pada tahapnya. Penutupan CP6 tidak mensyaratkan penyelesaian seluruh roadmap.
- **R1.4, baris 1728:** AUD-G04, UI sales/payment/return/refund, berada pada **CP7 full dummy sales**. Dependensi backend tetap diuji di CP6/CR bila nilai atau sumber terdampak.
- **G04, baris 6289:** cakupan Sales, AR, COGS; gate **CP7 full dummy sales flow**.
- **G04, baris 6291–6305:** bukti native tidak membuktikan seluruh tombol UI terhubung; fitur tetap belum selesai. Acceptance UI mencakup draft, edit, post, pembayaran sebagian, retur, refund, reversal, stale data, klik ganda, respons hilang, hak endpoint, dan rekonsiliasi.

Review lama `docs/reviews/ERP_CP6_Audit_757b79a_20260923.md` bagian 10 juga menempatkan modul penjualan pada CP7. Berkas `03_SCOPE_CP6.md` tidak digunakan sebagai sumber karena belum diperoleh. Master asli yang hash-nya cocok sudah memberikan dasar langsung; tidak diperlukan keputusan kebijakan baru untuk menciptakan pemetaan ini.

## Bukti penerimaan yang tetap berlaku

| Kelompok | Bukti dan asal |
|---|---|
| Retest auditor ini | [36466041148](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36466041148): CP6 8 native + 4 race PASS; CP7 10 fokus + 6 browser PASS. Asal probe sendiri, probe auditor lain, dan skenario writer yang dijalankan ulang dipisahkan dalam laporan sebelumnya. |
| Retest auditor PR32 | [36467230838](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36467230838): 5/5 native PASS, 30/30 pemasangan; log aslinya telah diperiksa auditor ini pada putaran sebelumnya. |
| Cross-check writer | CP6 97 native, 26 race, 8 Auth/HTTP, 37 browser; rollback147. CP7 619 tes + 6 browser. Log telah diperiksa, tidak dihitung sebagai seluruh tes yang dijalankan auditor ini. |
| Regresi yang diterima sebelumnya | Tetap mengikuti SHA, ruang lingkup dan disposisi historisnya; tidak dibuka ulang karena perubahan dokumentasi. Angka mentah historis tidak diubah menjadi PASS atau dihitung sebagai tes baru. |

CP6-FINAL-01 dan CP7-DELTA-01 tetap **CLOSED/FIX VERIFIED**. R14 laporan Grade B berisi sudah dieksekusi auditor ini, termasuk nilai, lot asal, pembagian grade dan inverse. Empat jadwal race konversi/master juga telah dijalankan auditor ini. Fakta bahwa lima probe PR32 tidak mencakup dua kelompok terakhir tidak menghapus bukti terpisah tersebut.

### Rekonsiliasi keluarga gate CP6

Pemetaan berikut menggabungkan bukti yang telah diterima dan bukti perubahan terbaru. Ini bukan klaim seluruh matriks dieksekusi baru pada putaran dokumentasi ini. Register lama `AUDIT_PROGRESS_GPT.md` di `9aa7c76` merekam checkpoint pra-BD/BE; status historisnya tidak diubah. Handoff gabungan pada commit tersebut juga sudah menerima W2/C0 25 kasus oleh kedua auditor, recovery terpilih, HTTP, T2/T3 dan rollback pada versi saat itu. Perubahan BD/BE/BF kemudian mempunyai bukti penerus yang dijelaskan dalam laporan delta dan retest terbaru.

| Gate | Dasar putusan gabungan dalam cakupan CP6 |
|---|---|
| C6-01 — identitas/cukup bukti | Kandidat produk, byte paket, sumber kontrak, oracle, run, dan asal skenario terikat; perubahan terakhir hanya dokumen. ACCEPT. |
| C6-02 — atomik/fakta posted | Bukti transaksi dan inverse terdahulu dipertahankan; retest BF menolak edit historis secara atomik serta menjaga replay dan pembalikan. ACCEPT. |
| C6-03 — recovery/input/selector | Penerimaan recovery terdahulu dan revisi BD/BE tetap berlaku; browser paket BF/AU 37 kasus terverifikasi pada log. Tidak ada perubahan UI dalam perbaikan terakhir. ACCEPT. |
| C6-04 — saldo awal ALL | Bukti BB/BC/BD/BE dan disposisi keluarga saldo awal diteruskan pada jalur produk yang tidak berubah; tidak menggunakan keberhasilan lima probe konversi sebagai pengganti matriks ALL. ACCEPT sesuai kasus dan disposisi yang telah diaudit. |
| C6-05 — tanggal/HPP/jurnal/laporan | Oracle C0 yang disahkan dan diterima kedua auditor dipertahankan; HPP/invoice/inverse pada audit delta serta riwayat konversi pada retest terbaru lulus. Hasil raw kalender lama tidak dilabel ulang. ACCEPT sesuai oracle yang berlaku. |
| C6-06 — produksi/AR/AP/payroll/uang muka | Bukti BB dan keluarga transaksi sebelumnya tetap; retest kredit supplier, pemakaian/replay/inverse, rework/range dan invoice susulan melengkapi perubahan yang berdampak. ACCEPT dalam scope CP6. |
| C6-07 — aksesori/pocket/laundry | Bukti BC/BD/BE terdahulu, cross-check regresi BC45/BD41, serta audit delta FREE/WAIVED/UNKNOWN, biaya dan kredit dipertahankan. Tarif/kebijakan owner tidak dibuka ulang. ACCEPT dalam scope yang disepakati. |
| C6-08 — akses/UI | Bukti Auth dan browser terdahulu, 8 Auth/HTTP paket dan uji akses independen terpilih dipertahankan. G04 UI sales tetap OPEN_CP7 menurut kontrak; bukan PASS UI CP6. ACCEPT untuk batas akses/UI CP6. |
| C6-09 — concurrency/stale | Bukti race sebelumnya dan paket26, ditambah 4 jadwal konversi/master yang dieksekusi auditor. Tidak ada perubahan produk sejak run. ACCEPT. |
| C6-10 — pemasangan/pemulihan/rollback | Install 30 berkas dan backup/restore pada database sementara dieksekusi auditor; rollback147 cross-check writer pada byte paket yang sama. Fresh cutover/data produksi tetap tahap rilis berikut sesuai kontrak. ACCEPT untuk gate paket CP6. |

Rujukan riwayat: [handoff gabungan auditor](https://github.com/Hanjay6688/-erp-garment-ux/blob/9aa7c766ac0d23f403fc458ce513193716c6bd1e/AUDIT_WRITER_HANDOFF_CP6.md), [handoff audit delta CP6/CP7](https://github.com/Hanjay6688/-erp-garment-ux/blob/c2728c7e28ed674e680590b6f3db56478b1388b5/audits/independent_delta_20260929/reports/CP6_CP7_HANDOFF_WRITER_20260929.md), serta [hasil retest](RESULT.md). Penerimaan checkpoint ini tidak mengubah semua label mentah historis menjadi PASS; sumber, cakupan, dan disposisi masing-masing tetap dipertahankan.

Pembaruan PR32 yang dibaca pada putaran ini telah menarik R10 sebagai alasan HOLD dan menutup cakupan audit PR32. Putusan gabungan di dokumen ini melengkapi penerimaan tersebut. Tidak ada blocker CP6 aktif yang diidentifikasi dalam rekonsiliasi keluarga dan perubahan yang diperiksa; tidak ada klaim seluruh variasi bisnis atau integrasi CP7 sudah diuji.

## Handoff akhir untuk writer

1. Catat checkpoint **CP6 CLOSED / diterima independen sesuai scope kontrak**, dengan kandidat dan fingerprint di atas. HOLD administratif untuk penyelarasan R10 selesai melalui putusan ini.
2. Pertahankan **R10 / AUD-G04 OPEN_CP7**, lengkap dengan acceptance berikut: browser → facade → database → refetch; draft → edit → post → bayar sebagian → retur → refund → reversal; exact size dan lot/alokasi asal; reservasi sekali; stale state, submit ganda, respons hilang, hak akses terkini; rekonsiliasi stok/AR/COGS/jurnal per dokumen dan agregat; readback setelah reload.
3. Pertahankan R03, yaitu wave fisik terpisah untuk referensi pekerjaan berbeda pada ukuran sama. R14 yang diterima tetap terbatas pada rute Grade B yang diuji.
4. Perubahan produk atau integrasi CP7 berikutnya memerlukan pemeriksaan dampak dan tes pada kandidat baru. Penerimaan cangkang sintetis tidak menjadi bukti sambungan backend atau seluruh integrasi CP7 sudah lulus.
5. `production_go=false` tetap. Penutupan tahap CP6 tidak memberi izin deploy, penggunaan production, ataupun menyatakan seluruh ERP selesai. Izin cangkang CP7 yang sudah ada tetap berlaku; dokumen ini tidak mengeksekusi atau mengaktifkan konektivitas operasional.

Tidak ada pekerjaan perbaikan CP6 tambahan untuk writer dari penyelarasan ini. [RESULT.md](RESULT.md) tetap menyimpan asal tes dan batasnya; [HANDOFF.md](HANDOFF.md) diperbarui untuk merujuk putusan akhir ini. Catatan sebelumnya yang menyatakan pemetaan R10 belum pasti digantikan oleh hasil verifikasi kontrak di sini.
