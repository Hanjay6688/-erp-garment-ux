# Handoff gabungan audit CP6 — mulai di sini

Tanggal: 24 September 2026 UTC. Kandidat produk: `9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc`; tree: `5d5f833b2e75e23184c643d5ac469781f1c3ce5e`.
Cabang audit: `audit/cp6-final-20260924-gpt-a0bcadf`.

**CP6 HOLD · audit_complete=false · production_go=false.** Kelompok gate GPT: **6 HOLD, 4 UNVERIFIED, 0 ACCEPT keseluruhan gate**.

Owner: **Hansen**. Writer yang disebut owner: **Claude Opus Max**. Auditor: **GPT dan Claude Fable Ultracode**. Nama “Claude” dalam laporan sumber merujuk audit Fable, kecuali dinyatakan writer.

## Pembagian kerja terbaru: writer dapat mulai, auditor tetap lanjut

Owner menyampaikan proposal writer untuk rollback dan dua perbaikan runtime. **Rekomendasi GPT: owner dapat memberi “gas” sekarang untuk tiga pekerjaan terbatas di bawah; tidak perlu menunggu seluruh audit CP6 selesai.** Proposal tersebut belum diperlakukan sebagai implementasi, run baru, atau PASS. GPT tidak mengirim instruksi/pesan ke writer dan tidak memutasi cabang writer.

| Pekerjaan writer Opus | Batas implementasi | Verifikasi GPT/Fable |
|---|---|---|
| Rollback AW..AZ dan mode T3 | Urutan AZ→AW; pre-use saja; setelah ada transaksi harus menolak tanpa perubahan; katalog kembali persis. | Review diff dan pins; install→rollback→install ulang, refusal setelah use, katalog/data/owner/ACL/trigger/riwayat migrasi serta cleanup. |
| Runtime dua sesi | Rantai dan fixture committed dalam database salinan disposable; tiap koneksi menyiapkan identitas sendiri. | Actor/role/JWT/grant preflight pada dua koneksi, pekerja benar-benar berjalan, jadwal overlap, exact refusal, satu efek domain, sumber/primary tetap. |
| Runtime Auth/HTTP | Login Auth sungguhan pada stack disposable, kemudian PostgREST; gunakan dasar T3 existing. | Skenario/oracle milik auditor, identitas dan izin nyata, status+pesan penolakan, state tidak berubah, cleanup. Sertakan jalur UI browser→HTTP→runtime. |

Writer menyatakan **migrasi, paket dev, frontend, dan 24 file SQL paket rilis tidak berubah**. Ini klaim rencana yang harus diperiksa lewat diff terhadap9add57e ketika commit baru tersedia. Tidak ada diff implementasi baru yang sudah diperiksa dalam handoff ini.

Catatan batas yang wajib dipertahankan:
- AZ→AW membuktikan kembali ke **AV**. Itu belum membuktikan rollback seluruh AC..AZ ke **AB**, dan tidak otomatis menyelesaikan guard digest AC varian rilis.
- Auth login→PostgREST membuktikan jalur Auth/HTTP; kontrak browser→HTTP→runtime tetap memerlukan kasus UI nyata.
- Saat alat/rollback berubah, catat **commit produk acuan** dan **commit alat yang dijalankan** secara terpisah. Jangan memberi label head9add pada job yang checkout commit baru.
- Jangan selidiki ulang absennya rollback AW..AZ sekarang. Gap itu sudah jelas HOLD; tunggu artifact/diff writer untuk direview.
- Auditor tetap menyusun oracle dari kontrak dan menilai alat writer. Hasil writer bukan independent PASS; jangan melonggarkan guard atau menyesuaikan expected agar hijau.

## Cara melanjutkan

1. Checkout cabang audit ini dan baca [AUDIT_PROGRESS.md](AUDIT_PROGRESS.md).
2. Gunakan tiga kontrak dengan hash yang tercatat. Lock fase1 GPT tetapcbca0c6c…; pembacaan laporan Fable dilakukan post-lock atas instruksi owner.
3. Mulai dari ID gabungan di bawah. Alias lama tetap dipertahankan; temuan yang sama tidak dihitung dua kali.
4. Pakai [indeks terstruktur](audit/CP6_COMBINED_INDEX.json) untuk oracle berkas/baris, bukti, batas dan next action tiap isu.
5. Simpan kasus, SHA256, run/job/attempt/head, expected/actual serta cleanup ke repo. Kasus gagal tidak dihapus. Jika memakai agen, catatan out/ ditulis bertahap dan dicheckpoint sesudah batch.

Sumber yang dibekukan: [GPT sebelum cross-review](https://github.com/Hanjay6688/-erp-garment-ux/blob/19117b17be65c1ffc1d19593ee04a43103d7e860/AUDIT_REPORT_CP6.md), [laporan Fable cf301a6](https://github.com/Hanjay6688/-erp-garment-ux/blob/cf301a6f0c128ac8c221ab11e22c95db0ce1c896/AUDIT_REPORT_CP6.md).
Dokumen aktif: [laporan CP6](AUDIT_REPORT_CP6.md) dan [hasil verifikasi silang](AUDIT_CLAUDE_CROSS_REVIEW.md).

## Register gabungan tanpa duplikasi

Kolom alias memakai ID GPT dan/atau Fable. CONFIRMED source/lokal berbeda dari native; hipotesis bukan bug terkonfirmasi.

| ID | Alias asal | Isu | Status terkini |
|---|---|---|---|
|CP6-01|F01 / F1-14|Waktu WIB mengikuti zona perangkat|P1; source/lokal terkonfirmasi|
|CP6-02|U02 / F1-16|Completion WIP backdate merusak prefix|P1; native Claude dikonfirmasi ulang|
|CP6-03|U03 / F1-17|Nilai bahan tersisa pada qty nol|P2; native Claude dikonfirmasi ulang|
|CP6-04|U01, C-SEL-01 / F1-15|Selector BS/import/pocket/payroll/prepayment terpotong|P2; source pasti, native BS terbatas|
|CP6-05|C-AUTH-01|UUID/payload retry tidak stabil|P2; lokal, native belum|
|CP6-06|C-UNK-01|Failed read ditampilkan sebagai KPI nol|P2; lokal, browser belum|
|CP6-07|C-BIZ-01|Refund backdate memakai kapasitas advance masa depan|Kandidat P1; 6 kasus NOT_RUN|
|CP6-08|payroll_source_followup|Atribusi baseline BS terhadap upah rework|Hipotesis; belum dipromosikan|
|CP6-09|F1-12|Identitas sumber opening lintas batch|Angka posting terbukti; oracle duplikasi bersyarat|
|CP6-10|R01 / F1-04|Integritas hasil dan isolasi runner|P2 alat; subklaim dibedakan|
|CP6-11|O01 / F1-18|Assertion T3 melewatkan hasil restore/cleanup|P2 alat; source terkonfirmasi|
|CP6-12|R02 / F1-05, F1-11|Rollback rilis belum terkualifikasi, termasuk AV|HOLD; implementasi diarahkan ke writer|
|CP6-13|T2 disposition / F1-01|Oracle tanggal dan disposition T2|HOLD; bukan otomatis 25 bug|
|CP6-14|F1-03|Fixture QUIETED/PAYROLL_APPROVED pada T2|Bukti bersyarat; review fixture|
|CP6-15|advisor54_review / F1-06|Disposition 54 advisor INFO|P3 review; bukan bukti exposure|
|CP6-16|F1-07|Toleransi kesetaraan backup/restore|P3 bukti; berbeda dari rollback migrasi|
|CP6-17|C6-04 / F1-02|ALL disetujui, implementasi belum lengkap|Konflik approval dibantah; coverage tetap terbuka|
|CP6-18|H01, SI-01 / H01|Pengikatan produk opsional pada WIP|Hipotesis; oracle dan native terbuka|
|CP6-19|H02, SI-04 / H02|Finalisasi sesudah prepared draft diedit|Hipotesis; native belum|
|CP6-20|C-BIZ-02|COUNT pecahan pada transfer/adjustment|Ditahan; ordinary-route reachability belum|
|CP6-21|F1-08, F1-10|Urutan helper sys.path|INFO; belum ada dampak terbukti|
|CP6-22|F1-09|Cutting sebelum penerimaan|Ditarik oleh Claude setelah native refusal|
|CP6-23|F1-13|Viewer membaca aksesori sesuai izin view|Ditarik: oracle all-denied salah|

Bukti native yang ditinjau ulang berlabel **REUSED_EVIDENCE**, bukan run baru GPT. [Ledger cross-review](out/claude_cross_review_native_ledger.json) menyimpan20baris kasus dari5run, metadata, SHA dan baris log. [Ledger sebelumnya](out/native_case_ledger.json) menyimpan observasi T2/T3/CodeQL. Label asli COUNTEREXAMPLE tidak otomatis berarti oracle auditor sudah benar.

## Empat hambatan yang dikirim owner

| ID | Keadaan kini | Langkah berikutnya |
|---|---|---|
| BLOCKER-01 — race | Run36051535647/job107808033765 dan36052066150/job107809808216 gagal saat setup, sebelum race. Identitas/grant belum terlihat dari koneksi kedua. | Writer Opus menyediakan runtime salinan committed. Spec: [race review](out/race_blocker_review.md). Jangan retry skrip lama tanpa dukungan tersebut. |
| BLOCKER-02 — HTTP/JWT | xaudit_4 mengekstrak signing secret dan membuat token sendiri. Kejadian classifier hanya laporan eksternal; skrip juga tidak membuktikan login Auth. | Writer Opus memakai Auth nyata dari T3; auditor menyusun matrix role/action dan browser. Spec: [HTTP review](out/http_blocker_review.md). Tidak ada jaminan classifier akan menyetujui; jangan mengakali penolakan. |
| BLOCKER-03 — rollback | AW..AZ absent, manifestNOT_TESTED, mode T3 rollback absent. HOLD sudah tercatat. | **Hentikan penyelidikan ulang gap lama.** Tunggu implementasi writer, lalu review artifact dan native qualification. Batas AV vs seluruh paket tetap berlaku. |
| BLOCKER-04 — agen | Reset kuota Claude22:20/trigger22:26 tidak diverifikasi di sini. Dua agen GPT sudah menyelesaikan review race/HTTP dan temuan ekonomi. | Review dapat dilanjutkan dari repo; tidak perlu menunggu kuota Claude untuk pekerjaan GPT. Native gate tetap terbuka. |

Rincian gabungan: [blocker_and_recovery_assessment.md](out/blocker_and_recovery_assessment.md). Empat catatan agen tersimpan di out/. Tidak ada kontak hosted/legacy/production atau pesan ke pihak lain.

## Perbedaan penilaian yang jangan hilang saat digabung

- **ALL sudah disetujui:** M1024 menggantikan M1072–1078 historis. Cakupan implementasinya masih perlu dibuktikan; tidak perlu menanyakan scope yang sama lagi.
- **Opening lintas batch:** tambahan15,75 terbukti. Identitas sumber fisik yang sama belum terbukti. Perlu negative same-source dan positive distinct-source/partial-import.
- **Pembulatan turun:** jangan menganggap half-even Python otomatis aturan ERP. Residu inventory±0,01 valid; WIP10,00 sendiri belum dinilai salah tanpa canonical rounding.
- **Selector BS:** cap100 source terkonfirmasi. Fixture101delivery dibuat dengan SQL cloning; lifecycle producer, net claimability dan actual UI claim perlu diperkuat.
- **Race rev2:** hash benar5d640e42…;3915e006… milik rev1. Kedua run tetap INCOMPLETE.
- **T2:**25hasil menunggu disposition, bukan25bug otomatis. MATCH terhadap oracle writer bukan acceptance kontrak.
- **Cakupan GPT dalam laporan Fable:** snapshot lama. Checkpoint19117b17 telah mencatat9job terpilih dan4bahasa CodeQL; tidak perlu rerun hanya untuk memperbaiki narasi.
- **AV:** addendumXA2 memuat2kontrol identitas. Jangan menyebut tidak diuji sama sekali; tetap belum full lifecycle/rollback.

## Lima belas kasus original GPT yang belum dijalankan

| Kelompok | Jumlah | Keadaan sumber |
|---|---:|---|
| Stock/import: SI01identity, SI02datedcapacity, SI03retry, SI04prepare-edit |4| [stock_import_scenario.py](audit/scenarios/stock_import_scenario.py), exact hashff92e8d9… dipulihkan |
| Money: DIRECT/INVOICE × UP/DOWN |4| [money_dates_scenario.py](audit/scenarios/money_dates_scenario.py), exact hashcfa1157b… dipulihkan |
| Advance: supplier/customer/vendor × ordered/backdated |6| [business_scenarios_reconstructed.py](audit/scenarios/business_scenarios_reconstructed.py), hash90625484… baru. Original44b075c7… tidak dipalsukan sebagai pulih; COUNT tetap dikecualikan. |
| Selector:51draft import |1| [import_selector_reconstructed.py](audit/scenarios/import_selector_reconstructed.py), hash66d0524c… baru. UI discovery; known-UUID reader positif. Berbeda dari BS101 Fable. |

**Sumber15kasus kini lengkap:**8exact frozen+7rekonstruksi. [Payload gabungan](audit/scenarios/combined_native15_reconstructed.py) SHA256`cec2ad521835476cf702119486e637d3eff4b62d8f72197a9ca2c2d50cf1fadb`,47183bytes; [manifest](audit/scenarios/native15_manifest.json) berisi15ID unik dan hash tiap member. Status tetap **NOT_RUN, run_id=null, job_id=null**. Pemeriksaan lokal hanya sintaks/registrasi/hash. Payload lama968cac54… belum pulih byte-identik; versi baru tidak memakai hash lama. Hasil Fable tidak mengganti status eksekusi batch ini.

Dispatch custom sudah diizinkan handoff. Connector sesi GPT hanya menyediakan GET dan rerun job existing, belum POST dispatch baru. Jangan meminta password/token/kunci. Ketika executor yang berwenang tersedia, kirim byte file langsung dan cocokkan hash/planned IDs dalam log.

## Urutan audit selanjutnya

1. Writer dapat mengerjakan tiga alat/artifact di atas setelah instruksi owner. Auditor memanfaatkan waktu untuk menajamkan oracle dan fixture; kedua kegiatan dapat berjalan tanpa dua writer produk.
2. Review diff writer terhadap9add, pastikan lingkup file tidak melebar, lalu verifikasi mode runtime/rollback baru dengan kontrol kegagalan.
3. Review7rekonstruksi dan8sumber frozen yang kini tersimpan, termasuk batas oracle SI01/moneyDOWN/advance. Jalankan payload15melalui executor disposable yang berwenang; tidak perlu merekonstruksi ulang file yang sudah selesai.
4. Prioritaskan WIP prefix, recost dan WIB UI; lanjut advance/payroll, selector, recovery dan unknown sampai konsumen/inverse/report.
5. Lengkapi ALL22state/6family, Auth/action/location/revocation, browser, race, transitive HPP/producers dan adapter residual. Crosswalk ALL/payroll ada di out/.
6. Perbarui putusan tiap gate pada exact source yang diuji. Penyelesaian handoff ini tidak menyelesaikan audit seluruh CP6 atau mengizinkan produksi.
