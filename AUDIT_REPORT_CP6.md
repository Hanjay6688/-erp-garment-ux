# CP6 audit — checkpoint putaran9 dan arsip historis

## Checkpoint audit independen putaran 9 — 25 September 2026

**T2 native SELESAI, belum acceptance:** [run 36125151913](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36125151913) audit head d1bc8ad, AR job `108039445366` 174/174 PASS, temporal job `108039445443` 41/41 PASS, regresi job `108039445222` status asli `DISPOSITION_REQUIRED` (BUSINESS 179 PASS+39 CONTROL_PASS+12 HOLD kalender; IMPORTS31 PASS, VALUES65 PASS; NEW_CASES 25 PASS+8 COUNTEREXAMPLE+1 INCOMPLETE; tambahan C0 25/25 PASS). `T2_IDENTITY` memastikan 12 HOLD historis tidak bergeser. `primary_unchanged=true`, clones0, tiga job SUCCESS. Peta persis 600 kasus `out/gpt_r9_t2_cases.json` dan ledger `out/gpt_r9_t2_run.md`; status keseluruhan tetap HOLD, production_go=false. Berikutnya jalankan T3 package satu workflow fase sendiri, kemudian rollback setelah T3 selesai.

T2 regresi kasus lama yang bukan PASS: 12 `DATE_POLICY_REVIEW_REQUIRED`, 8 `COUNTEREXAMPLE` tanggal, 1 `INCOMPLETE` adjustment; AO trial 4 `INCOMPLETE`. Semua ID dan original status dapat ditelusuri di `out/gpt_r9_t2_cases.json`. Tiga job Actions hijau artinya eksekusi tuntas, sedangkan verdict bisnis tetap `DISPOSITION_REQUIRED`. BA C6 75 dan ALL22 belum diuji terhadap BB–BE.

**CP6 HOLD · audit_complete=false · production_go=false.** Head writer yang dibekukan untuk bukti ini `d1bc8adff3ba1a2a7001ef39e4819d0c3813d00b`, produk BA `b6d81f93a1e244178193178aec765facfd1b5488`. Compare e10260b..d1bc8ad hanya mengubah lampiran C6 rev3. Semua bukti di bagian ini adalah `AUDITOR_SCENARIO`, bukan bukti rilis atau penerimaan global. Bagian round8 di bawah adalah **riwayat kandidat a095a9d**, bukan status produk BA terbaru.

| Area / oracle | Bukti audit sendiri pada d1bc8ad | Status gate saat ini |
|---|---|---|
| W8 / CP6-03, M:3818/3820 | Run 36122470639 job 108030928495: direct/invoice × naik/turun, 4/4 PASS, bahan habis 0/0,00 dan sen dokumen teralokasi persis. Baseline tanpa BA pernah PASS; kasus regresi BA awal tidak boleh dilekatkan ke baseline. | Kasus sasaran terverifikasi; acceptance CP6 keseluruhan HOLD |
| W9 / C0 D01 §3.4 | Run sama: koreksi terlambat membuat `changed_since_filing=true` tanpa mengubah filed values/ID; kontrol tanpa koreksi false, 2/2 PASS. | Kasus sasaran terverifikasi; gate laporan belum lengkap |
| LAU-T14 / M:4474 | Run sama: tarif saat kirim 7, tarif baru 9, terima 10PCS tetap 7,00/70,00; kontrol tarif tetap sama, 2/2 PASS. | Kasus sasaran terverifikasi; laundry36 UNVERIFIED |
| W7 / tool fail closed | Run sama jobs 108030928804/108030928817 intentionally red: status asing menjadi INCOMPLETE, ID ganda race/HTTP ditolak; primary/Auth bersih. | Tes penolakan alat PASS; bukan klaim produk |
| W10 / CP6-05, M:1679/3819 | [Run 36124300108](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36124300108) job 108036762501: pola dan role, real Auth/browser/HTTP, respons committed dijatuhkan, retry UUID/payload identik, replay respons sama, tepat satu baris; 2/2 PASS. | Kasus sasaran terverifikasi; gate global HOLD |
| W13 / CP6-06, M:3825 | Run sama jobs 108036762474/108036762544: kontrol sehat Laundry20/QC10, saat read gagal UI `—, belum diketahui`, tulis terkunci, HTTP200/refetch memulihkan 20/10; 4/4 PASS. | Kasus sasaran terverifikasi; gate global HOLD |
| W11, beda error parser/jaringan | Run sama job 108036762327: seed UUID tidak valid disengaja pada clone; abort menunjukkan pesan jaringan, HTTP200/parser menunjukkan `ID Mandor bukan UUID valid.`; PASS. | Perbaikan pesan terverifikasi untuk jalur ini |
| C6: 39 ACC + 36 LAU; ALL22 | Oracle dari tiga kontrak di `out/r9_acc_oracle.md`, `out/r9_lau_oracle.md`, `out/r9_all_oracle.md`, masing-masing SHA pada AUDIT_PROGRESS. ID case crosswalk 75/75 cocok M, register ALL22 22/22 cocok writer §29.6. | **75+22 UNVERIFIED/HOLD** hingga family BB–BE diuji; peta bukan hasil |
| D06 / LAU-04 | Owner jelas meminta seluruh22 dan CR di CP6. Namun `D06` tanpa namespace ambigu, lampiran rev3 belum sah; M:1757 bukan sumber kebijakan setting; M:4475 melarang final sales/close baru saat harga laundry UNKNOWN tanpa policy. | **HOLD**, cek `post_sale_v2` dan klarifikasi dokumen sebelum ACCEPT |

Run browser rev1 `36123487209` tetap tercatat **INCOMPLETE** untuk W10 dan salah klasifikasi W13 karena dua cacat skenario sendiri; rincian dan kontrol di `out/gpt_r9_browser_rev1_run.md`. Rev2 memakai hash baru dan **7/7 PASS**, tidak menulis ulang label lama. Perinciannya `out/gpt_r9_browser_rev2_run.md`; tes bisnis/tool `out/gpt_r9_business_tool_run.md`. Empat catatan oracle dikunci dan di-push sebelum pemeriksaan kode BB–BE. Semua uji disposable tanpa menulis ke hosted/legacy/main/competition.

**Langkah audit berikut:** writer BB→BC→BD→BE belum tersedia pada freeze ini. Saat tiap head muncul, review diff, ikat 75+22 oracle untuk ID/adapter/kebijakan, buat skenario kasus sah dan refusal/race/rollback/UI, lalu run native dengan hash baru. Pertahankan CP6 HOLD dan `production_go=false` sampai seluruh gate kontrak, laporan C6/D06, dan bukti independen lengkap.

---

<!-- GPT_R8_CURRENT_REPORT_BEGIN -->
## Putusan terkini — audit silang putaran 8, 25 September 2026

**CP6 HOLD · audit_complete=false · production_go=false.** Produk yang dinilai: `a095a9d804d29643721e18635c2c3e26adcd56ea`; alat: `9dd7bc2b9309d008e8a2e50d81876d831f3e5ea7`. Bagian ini menggantikan status sementara putaran 8 di bawah; hasil kandidat lama tetap historis. Audit seluruh CP6 belum selesai.

### Hasil yang sudah ditutup dan yang masih terbuka

| Lingkup | Kesimpulan pada kandidat ini | Bukti dan batas |
|---|---|---|
| CP6-01 / A2, waktu WIB | **VERIFIED_INDEPENDENT**, 12/12 kasus browser | Tiga halaman Potongan, Bagi Potongan, BS × Jakarta/UTC/GMT−12/Kiritimati. Login form nyata, simpan melalui HTTP, baca kembali database. Run36099496005 memberi8PASS dan4INCOMPLETE locator; run36100064157 menutup4pickup dengan locator yang benar. Nilai00:30WIB menjadi17:30Z hari sebelumnya di semua zona. |
| CP6-02/A3, CP6-07/A9, CP6-09/A1, CP6-18/A10 | **VERIFIED_INDEPENDENT untuk kasus yang tercatat** | GPT menguji penolakan bertanggal/identitas/impor ganda dan kontrol positif. Fable menambah jenis impor, bypass dan race impor. Ini bukan penerimaan seluruh ALL, semua jenis saldo, atau seluruh jalur payroll. |
| CP6-03 / A4 | **HOLD, P2 produk: residu multi-penerimaan masih terbukti** | Empat kasus GPT, dua arah × koreksi langsung/invoice. Saat qty0: UP persediaan0,01/WIP20,01, expected0/20,02; DOWN persediaan−0,01/WIP20,01, expected0/20,00. Kasus satu penerimaan PASS tidak menutup kasus ini. Satu ID temuan tetap CP6-03. |
| CP6-04 / A5 | **VERIFIED_INDEPENDENT untuk dua selector lama** | GPT impor51PASS; log Fable selector101 dibaca langsung:102 sumber claimable muncul, sumber lama tetap selectable. Bukan bukti seluruh UX pencarian/paging. |
| CP6-24 / A6, close tanggal sama | **VERIFIED_INDEPENDENT untuk race yang diuji** | Dua sesi, tepat satu filing; kontrol close sesudah reopen ada pada run Fable. |
| CP6-10 / B1, alias R8-B1-01 | **HOLD, P2 alat: race/HTTP belum ketat** | Ordinary self-test lulus. Pada race dan HTTP, ID ganda menimpa INCOMPLETE dengan PASS; status tidak dikenal diterima; job tetap RUN_COMPLETE. Perlu strict group di kedua mode. |
| CP6-05 / W10, identitas request setelah commit ambigu | **CONFIRMED_NATIVE_BROWSER_SCOPED**, P2 GPT / P3 Fable | Pola dan duplikasi Role: first save benar-benar commit HTTP200, hanya balasan diputus. Klik ulang membuat UUID baru (Role juga kodeCUSTOM), ditolak409; database tetap satu row. Dua COUNTEREXAMPLE M:1679/3819, bukan duplikasi data atau eskalasi hak. |
| CP6-06 / W13, KPI saat data unknown | **HOLD, P2 produk; Laundry dan QC terkonfirmasi native** | Laundry rev5 healthy20/refetch20 PASS; QC rev6 healthy10/refetch10 PASS. Read awal gagal menampilkan empat KPI0 disertai banner error dan write lock. Dua COUNTEREXAMPLE M:3825. Tidak ada bug refetch yang terbukti pada fixture valid ini. |
| W11 / W12, diagnosis fixture dan pesan error | **P3 UX / pertanyaan kualitas data** | Parser asli menolak UUID seed versi0, lalu exception diberi pesan seolah jaringan gagal. Kontrol baru memakai API UUIDv4 dan isolasi seed hanya pada salinan. Hambatan kontrol selesai; W12 bukan izin auditor memeriksa hosted/legacy. |
| C0 D01, 25 oracle uang/tanggal baru | **25/25 PASS**, terpisah dari hasil beku | AS8 + kalender12 + AO4 pada36098555186; ADJUSTMENT_DATE pada36099496005. Membandingkan jurnal, saldo per prefix, tanggal dan laporan. Retry adjustment hanya memulihkan schema USAGE alat setelah helper mencabutnya. Tidak mengubah produk atau oracle. |
| HTTP dengan Auth sungguhan | **PASS dalam matriks tercatat** | Matriks argumen valid18cek, pencabutan user OWNER, dan jangkauan helper prepare. Kasus dummy-argument lama ditarik sebagai kesalahan probe. Helper prepare private tidak terjangkau HTTP publik pada runtime ini; bukan bukti seluruh jalur legacy aman. |
| CP6-11/B2, CP6-12/B3, T3 | **Subgate teknis T3_PREP diterima dengan batas yang dinyatakan** | Log install25/pins/gate/restore/browser dan rollback127check dibaca; comparator rollback direview. Kekurangan lama rollback AC..AV NOT_BUILT sudah teratasi. Ini bukan izin rilis. |
| C6 / D06 / GATE-16 | **HOLD** | Usulan split ACC-04/LAU-05 sudah disepakati dalam audit silang. Crosswalk75ID asli selesai sebagai daftar cakupan, bukan75PASS. Inventaris implementasi CR, revisi lampiran dan ratifikasi D06 masih diperlukan. |
| C0 §3.4, penanda laporan | **UNVERIFIED, pertanyaan semantik W9** | Dua kasus AO tertutup: filing tetap, uang/tanggal benar, tetapi `changed_since_filing=false`. Implementasi hanya memeriksa readiness. Klausa addendum perlu dicocokkan terhadap maksud penanda; belum diklaim sebagai kerugian finansial atau P2 baru. |

CP6-03 penting karena nominal dokumen yang sah tidak habis teralokasi setelah bahan fisik habis; toleransi0,01 per penerimaan belum disahkan kontrak. Oracle M:835,3818–3820,6625,6632 memakai jumlah sen masing-masing dokumen, bukan pembulatan ulang total gabungan. R8-B1-01 penting bagi keutuhan bukti: hasil yang belum lengkap dapat hilang dan memberi kesan run selesai. Ini tidak membatalkan hasil bisnis dengan ID unik/status sah yang sudah diperiksa satu per satu.

### Buku run dan asal bukti

| Run / job | Asal dan hasil yang diperiksa |
|---|---|
| 36097284096 / 107952094985 | Skenario GPT: ordinary28PASS/4COUNTEREXAMPLE/1INCOMPLETE; race2PASS; HTTP lama2PASS/1counterexample argumen salah. Ledger `out/gpt_round8_run_36097284096.json`. |
| 36097284096 / 107952095105,107952095197 | Self-test ordinary SELFTEST_PASS; sentinel race/HTTP menunjukkan R8-B1-01. Sentinel hijau bukan PASS oracle auditor. |
| 36098555186 / 107955933618 | Oracle C0 baru24PASS/1INCOMPLETE helper; ledger `out/gpt_c0_run_36098555186.json`. |
| 36099496005 / 107958771209 | Adjustment retry1PASS; HTTP3PASS; browser8PASS/4INCOMPLETE locator; ledger `out/gpt_browser_run_36099496005.json`. |
| 36100064157 / 107960458342 | Pickup browser4PASS; ledger `out/gpt_pickup_run_36100064157.json`. Semua12 browser memakai Auth nyata; Auth pulih, console0, salinan dibuang, primary tidak berubah. |
| 36101907250 / 107966011162 | Run recovery awal NOT_RUN/INCOMPLETE akibat path browser workflow audit; hasil tetap. Ledger `out/gpt_recovery_run_36101907250.json`. |
| 36102303107 / 107967209608 | Browser recovery Pola/Role2COUNTEREXAMPLE; Laundry/QC2INCOMPLETE sebelum diagnosis fixture. Ledger `out/gpt_recovery_run_36102303107.json`. |
| 36102938451 / 107969167045; 36103599807 / 107971184469 | Masing-masing2INCOMPLETE. Rev3 parser kandidat tanpa perubahan source membuktikan penolakan UUID seed mandor/model. Ledger `out/gpt_unknown_run_<run>.json`. |
| 36105734698 / 107977705679 | Rev4 setup memanggil fungsi policy private yang EXECUTE-nya ditolak;4INCOMPLETE, fixture rollback dan browser users0. Kesalahan setup auditor, bukan temuan produk. |
| 36106291785 / 107979461548 | Rev5 Laundry1PASS healthy+1COUNTEREXAMPLE unknown, refetchPASS; QC2INCOMPLETE karena nama merek helper bertabrakan. Ledger `out/gpt_unknown_run_36106291785.json`. |
| 36106777202 / 107980988537 | Rev6 QC1PASS healthy+1COUNTEREXAMPLE unknown, refetchPASS. RUN_COMPLETE/job hijau berarti hasil lengkap, bukan produkPASS. Ledger `out/gpt_unknown_run_36106777202.json`. |
| 36095707100 / 107947426273,107947426182,107947426290 | Run Fable atas harness writer, log direview GPT: identitas230/31/65 tetap; historicalHOLD12 tetap; AR146sequential+28race, AT16+4, AU15+6. QUIETED/PAYROLL_APPROVED tercatat; hasil ini tidak menerima semua cek negatif readiness. |
| 36096194323 / 107948864042 | Log skenario Fable: selector101PASS (102 sumber), koreksi invoiceUP/DOWN dan kontrol AV PASS. Dipakai ulang dengan asal bukti tetap jelas. |
| 36095715362 / 107947449272,107947449368,107947449378 | Run Fable T3, direview GPT:25file, pin cocok, restore RESTORED_SAME_MEANING, browser10PASS. Data320tabel/1657baris sama;19error pg_cron dengan0job sumber, normalisasi katalog terbatas. Bukan byte-identical restore. Advisor mentah REVIEW_REQUIRED; tambahan hanya INFO internalERP. |
| 36095723676 / 107947475610 | Run Fable rollback, direview GPT:127/127PASS, dua siklus BA→AC→AB,25post-use refusal. Setiap keluarga memakai satu transaksi saldo awal AR17,25; guard membandingkan seluruh dataERP, tetapi tidak menguji setiap bentuk transaksi. |
| 36090824553 / 107932695282,107932695376,107932695412,107932695437 | CodeQL writer pada d113bed:0hasil tiap bahasa, log dibaca GPT. Sesudah scan hanya satu perubahan kode alat: port preview4177→4176 pada origin dan process args. Diff direview dan browser diuji; jangan menyebut scan dijalankan pada9dd7bc2 atau sebagai bukti SQL/bisnis aman. |

Bukti silang lengkap: `out/gpt_round8_t3_crossreview.json` dan `out/gpt_round8_final_crossreview.json`. Semua bukti di atas berasal dari LOG Actions, bukan isi `docs/evidence/`. Tidak ada run baru yang diklaim untuk pekerjaan Fable/writer. Semua label tetap AUDITOR_SCENARIO, T2_REGRESSION atau T3_PREP; tidak ada bukti produksi/rilis.

### Kontrak, oracle dan scope C6

- C0 SHA256 `e83d56e66812011c9a7a4057bf29987d0bcf62aabc17ad23ab422170abb00c99`. Bagian1–8 sama persis dengan versi disahkan di5d54472, SHA256 seluruh versi tersebut `d39762da0520f30268a73244e7471b7d990138e3cbe36475d639c7cfca8e926d`. D01–D05 sah menurut handoff owner dan konfirmasi owner-ke-auditor yang dicatat Fable; tidak diminta lagi.
- D03§5.3: WIP tanpa produk/atribut lengkap boleh diposting dengan provenance unknown. ModelPO/ukuran dan atribut yang terisi tetap mengikat; unknown tidak dianggap cocok. Bukti harus mempertahankan alasan penetapan produk hasil.
- Oracle baru dibekukan di `out/gpt_c0_oracle_freeze.md`. Hasil beku12HOLD dan25kasus terkait tetap historis; 25PASS baru adalah bukti terpisah. Integrasi oracle ke harness berulang adalah pekerjaan W2, bukan alasan mengulang pertanyaan kebijakan D01.
- C6 SHA256 `72621c8a978573506b8c829a2a8790de948f6cb10e83ecd14dfddf35d495bc0d`. M:1691–1699 dan1753–1757 mengizinkan penundaan fitur baru yang disahkan owner, tetapi tidak penundaan cacat/perilaku lama. M:4448–4479 tidak membuka lagi persetujuan master vendor yang sudah diberikan.
- `out/gpt_c6_scope_amendment.md` memisahkan baseline dari perluasan baru. `out/gpt_c6_75_case_crosswalk.{md,json}` memetakan39ACC +36LAU ke klausul/oracle asli. Semua baris full-case masih UNVERIFIED sampai punya bukti yang sesuai; satu uji7PCS atau browserWIP bukan bukti semua baris.

### Batas pembuktian browser recovery/unknown

Kontrol Laundry/QC memakai identitas UUIDv4 dari API dan pencarian UI asli berdasarkan model baru. Satu produk seed tidak valid disisihkan dengan flag visibility hanya di salinan; ledger FG sebelum/sesudah flag sama. Parser dan respons HTTP tidak diubah. Jadi kontrol menerima workspace yang difilter ini, bukan seluruh data seed tanpa filter. Kedua run memulihkan Auth counts, membuang browser DB/clone, dan membuktikan primary tidak berubah. Tidak ada pemeriksaan hosted/legacy/production. W11 membedakan error data/parser dari error jaringan; W12 adalah tindak lanjut writer pada drill/artifact yang diizinkan.

### Yang belum selesai

CP6-03, B1, CP6-05 dan CP6-06 tetap terbuka untuk perbaikan. CP6-05 kini terbukti native pada Pola/Role; CP6-06 terbukti native pada Laundry/QC dengan healthy dan refetch controls PASS. Rincian oracle, setup, hash, raw results dan batas klaim ada di `out/gpt_recovery_unknown_final.md`. Run lama tetap INCOMPLETE; hasil baru tidak melabel ulang sejarah.

Cakupan ALL22state/6keluarga, matriks izin/lokasi dan jalur sumber–HPP/payroll belum selesai. `out/gpt_all_round8_binding.md` mengikat9blob sumber pada kandidat; kesamaan source tidak menerima seluruh runtime karena BA dapat mengganti fungsi. Hipotesis BS/payroll CP6-08 serta COUNT pecahan CP6-20 belum menjadi bug terbukti.

A7/CP6-25 opsional P3: refusal aman, pesan terlalu umum. A8/CP6-19 tidak terbukti sebagai stale post pada jalur aplikasi sah; ordinary edit PASS, prepare langsung lalu edit ditolak, helper private HTTP404. Hardening grant dapat dikerjakan writer, tetapi bukan alasan menghidupkan ulang klaim bypass browser. Editabilitas jalur prepared legacy yang diwajibkan M:1025/3817 tetap memerlukan route yang sah jika masih didukung.

Lanjut melalui tugas aktif di `AUDIT_WRITER_HANDOFF_CP6.md`, cakupan di `AUDIT_HANDOFF_CP6.md`, serta status terstruktur `audit/CP6_COMBINED_INDEX.json`. Tutup hanya kasus/gate yang benar-benar terbukti; rerun hanya bukti yang terdampak successor.


Handoff ringkas Fable untuk successor: `WRITER_HANDOFF_R9_20260925.md`. Penomoran W10/W11/W12/W13 dipakai bersama; tidak ada duplikasi temuan CP6-05/06. Perbedaan prioritas W10 P2 GPT/P3 Fable tetap terbuka dan fakta runtime sama.
<!-- GPT_R8_CURRENT_REPORT_END -->

---

## Arsip checkpoint sebelumnya

Catatan di bawah mempertahankan status saat dicatat. Instruksi pending dan penilaian lama yang bertentangan dengan bagian aktif di atas sudah digantikan; hasil run beku tidak dilabel ulang.

## Rev5: CP6-06 Laundry terkonfirmasi native; QC perlu fixture tanpa benturan nama

Run **36106291785/job107979461548**, audit **a4b65b9**, LOG SHA256**c671cb4ee423900d2f4fb58679850ad756eda9d7b1eb463d584d32142bf99304**. Hasil **1PASS +1COUNTEREXAMPLE +2INCOMPLETE**.
- Laundry healthy: RPC Auth200, parser asli menerima, browser menampilkan**20**. Produk seed yang disisihkan1; ID seed tidak ada pada respons yang dinilai.
- Laundry unknown: read awal diputus → empat KPI**0**, banner error dan write lock terlihat; gangguan dilepas → HTTP200/parser menerima/UI**20**, error hilang. **CP6-06 native confirmed pada Laundry (M3825)**, tidak ada bug refetch/false-finality/bypass yang diklaim.
- QC belum masuk browser: nama merek bawaan helper `Cutover brand` bertabrakan dengan fixture Laundry pada database yang sama. Guard unique menolak setup; paired unknown tetapINCOMPLETE.
- Cleanup:Auth2user/counts pulih, console0, browserDB0, clone0, primary unchanged. Raw status tersimpan utuh di `out/gpt_unknown_run_36106291785.json`.

Rev6 hanya dua kasus QC. Nama merek dibuat unik lewat `SAVE_FILE` sebelum FINALIZE, tanpa mengubah identitas/angka/oracle atau menurunkan unique guard. Laundry tidak diulang. Manifest_rev6; fixtureb85b0ddda85380f3afe59896c11e0685ef3b141506ac2fe79198a01b09322bce; browser77044ff34ecd361e8cf18cef24db3ed7a7bd0c83379f73a758d6580e569813bb.
LANGKAH BERIKUTNYA: catat run/job QC rev6 dan hasil healthy10→unknown→refetch10; kemudian konsolidasikan CP6-05/06, W11/W12 dan ALL ke laporan/handoff. CP6 HOLD · audit_complete=false · production_go=false.



## Native CP6-05 confirmed; CP6-06 probe still incomplete

Run **36102303107/job107967209608**, audit6156adb, exact9dd7bc2/a095a9d. Browser recovery Pattern and role duplicate: **2COUNTEREXAMPLE**. Each first save truly committed with HTTP200, then only its reply was dropped. Retrying unchanged form generated a different UUID; role duplicate also generated a different CUSTOM code. Both retries returned409 uniqueness errors; database retained exactly one row. **No duplicate row, privilege escalation or financial corruption claimed.** CP6-05 remains P2, now native browser confirmed under M1679/M3819 (retain exact envelope/replay). Writer action W10: preserve pending UUID/payload/expected-version through ambiguity and reconcile the original result.

Laundry/QC: **2INCOMPLETE**, positive Auth RPCs observed nonzero20/10, but successful-render/refetch assertion remained0 and threw before recording error details. These are not promoted to CP6-06 native proof yet. Add diagnostics preserving the initial UI, response metadata and post-refetch error before evaluating the positive control. Keep oracle fixed; test only these two cases next.

Cleanup:4browser users, Auth counts restored[0,0,0,0], console errors0, browser database0, clone0, primary unchanged. Ledger `out/gpt_recovery_run_36102303107.json`, log SHA2565eef7922fa41727ab263d962731792c3d19542dc6c0963f751743166d860fba4. Previous36101907250 NOT_RUN path failure preserved. LANGKAH BERIKUTNYA: diagnostic-only unknown2retry; then update reports/index without duplicate findings. CP6 HOLD.

## GPT round8 — independent native results (25 September 2026)
**CP6 HOLD · audit_complete=false · production_go=false.** Candidate tool `9dd7bc2`, product `a095a9d`. Historical 12 HOLD unchanged. This section supersedes the earlier IN_FLIGHT entry for run 36097284096 only; it does not relabel old candidates.

Run [36097284096](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36097284096), audit commit `f28a871d`. Full per-case JSON, job IDs, source log line numbers and SHA256: `out/gpt_round8_run_36097284096.json`. Scenario hashes remain in `audit/scenarios/round8/MANIFEST.json`.

| Scope | Evidence | Gate disposition |
|---|---|---|
| A1 duplicates, A3 dated WIP and positive dates, A9 three-party dated capacities + controls, A10 WIP identity + positive controls | 28/33 ordinary cases PASS across these and four single-receipt cent cases, import-51 selector, ordinary edit and replay | ACCEPT for the explicitly listed cases only; complete business gates not closed |
| CP6-03 / A4, multiple receipts, direct + invoice, UP + DOWN | Four COUNTEREXAMPLE, job107952094985 lines1888–1891 | HOLD; existing P2 finding remains open, not a duplicate new finding |
| A6 close race, WIP race quantity safety | 2 PASS, job107952094985 lines1894–1895 | ACCEPT for safety cases; A7 message specificity remains optional P3 |
| A8 prepared edit | Ordinary validate→edit→finalize PASS. Exposed prepare→edit explicitly refused: INCOMPLETE for draft editability | UNVERIFIED reachability/editability; no stale successful post proved via this legitimate edit |
| B1 savepoint strictness | Writer selftest independently executed: SELFTEST_PASS, job107952095105 | ACCEPT for duplicate/status/isolation checks in ordinary mode |
| B1 race and HTTP strictness, R8-B1-01 | Both duplicate IDs erase earlier INCOMPLETE; unknown statuses accepted; job107952095197 still RUN_COMPLETE | HOLD, P2 tool/evidence integrity |
| Real Auth HTTP | Revoked and unmapped users PASS; old H1 dummy arguments produce business validation errors | H1 UNVERIFIED, not a promoted product finding; fix arguments before rerun |
| C6 / GATE-16 | Eleven-row review in out/gpt_round8_c6_review.md; source policy crosswalk incomplete | HOLD; D06 remains unratified |

### Verified residual CP6-03 (P2)
Two separately rounded one-unit receipts of the same material, both fully consumed; physical stock = 0. UP correction 10.00→10.005 makes two document totals 10.01+10.01=20.02. Actual inventory 0.01 and WIP20.01; required inventory0/WIP20.02. DOWN 10.01→10.004 makes totals10.00+10.00=20.00. Actual inventory−0.01 and WIP20.01; required inventory0/WIP20.00. Reproduced through direct correction and supplier invoice. No return or tolerance-policy ambiguity in these fixtures. Writer's disclosed per-receipt limit describes the remaining defect; it does not authorize closing the contract gate. Oracle: Master Pulih M:835 (cent reconciliation principle), M:3818–3820, M:6625/M:6632 (GRNI/AP/stock/HPP reconciliation, sold-out cents, total/per-date value). Likely mechanism: `supabase/dev/cp6_ba_t1_family.sql:670–684` uses rounded aggregate stock endpoints, losing the sum of individually posted receipt cents.

### R8-B1-01 (P2 tool; extension of existing runner-integrity finding)
`gpt_tool_modes.py` returns INCOMPLETE then PASS for the same ID, plus NOT_A_VALID_STATUS, independently in race and HTTP. Both first results disappear from final counts; final RUN_COMPLETE/job success. Source `scripts/cp6_auditor_modes.py:99–126,237–267`: dictionaries overwrite and finish checks only INCOMPLETE/cleanup, not uniqueness/status vocabulary. This does not turn our unique-ID business results into failures; it invalidates a claim that all modes enforce B1. Required oracle: each planned case retained once, duplicate IDs rejected, unknown vocabulary→INCOMPLETE, incomplete cannot become complete by overwrite (Master M:1699/M:4324).
All three jobs: primary unchanged, clones removed; HTTP Auth counts restored. No hosted access.

### HTTP and prepared-draft qualification
H1 OWNER import read uses a random nonexistent batch; viewer accessory write uses an unknown action. Errors therefore cannot establish either access failure or access success for valid actions. Keep raw COUNTEREXAMPLE for provenance, classify the audit conclusion UNVERIFIED and rerun valid calls. A8 explicitly refused edit establishes no stale post, but does not establish editable prepared drafts required by M:1025/M:3817. Review real public reachability before deciding necessity/severity; retain old P3 distinction.

### LANGKAH BERIKUTNYA
1. Write/freeze 25 fresh T2 oracles from C0 D01 (8 AS +12 calendar+4 AO+1 adjustment); preserve historical statuses. Assert amounts and dates by prefix, not only current totals or equality to writer output.
2. Resolve Fable oracle differences explicitly: calendar WIP82.37/FG49.43/COGS32.95 after first partial invoice; inventory remains at E before cutting G; open adjustment recost dated max(E,A), not an early expense at E.
3. Run the next audit-only workflow phase pinned to the same candidate: C0 cases, valid real-Auth HTTP, and browser timezone/actions. Changing the current workflow and new scenario together avoids rerunning the completed business phase.
4. Cross-review T3/rollback/CodeQL actual Actions logs with provenance; finish C6 source crosswalk and A7/A8 recommendation. Commit each run/finding, then update combined report and writer handoff without duplicating CP6-03.


---

# Laporan audit CP6 — checkpoint pemulihan

Tanggal: 24 September 2026 UTC.
Kandidat: `9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc`.
Tree kandidat: `5d5f833b2e75e23184c643d5ac469781f1c3ce5e`.
Baseline pembanding: `ca7f09556397801c50a2277bdb65b1bf019f9a05`.
Cabang audit: `audit/cp6-final-20260924-gpt-a0bcadf`.

## Putusan

**HOLD; production_go=false; audit_complete=false.**

Audit yang diminta mencakup seluruh CP6. Laporan pertama berhenti terlalu dini; laporan itu tetap berstatus checkpoint parsial. Dokumen ini memperluas cakupan dan menyimpan hasil lanjutan, tetapi belum menutup seluruh kewajiban audit.

Dari sepuluh kelompok gate auditor, enam HOLD dan empat UNVERIFIED; belum ada ACCEPT untuk keseluruhan gate. Tidak ada P0 yang dibuktikan. U02/U03 telah dikonfirmasi melalui review independen atas log native Claude, berlabel REUSED_EVIDENCE; kasus original kami tetap NOT_RUN. Handoff gabungan tanpa duplikasi tersedia di AUDIT_HANDOFF_CP6.md; batas oracle dan koreksi laporan Claude ada di AUDIT_CLAUDE_CROSS_REVIEW.md.

HOLD berarti bukti dan pemenuhan kontrak belum cukup untuk menyetujui kandidat. Dokumen ini tidak menyatakan telah terjadi kehilangan uang atau insiden produksi.

## Pembaruan6140edb: sebagian bukti rollback tersedia

Run36063754595/job107848561550, attempt1/head6140edb1acd182efc84a4c85879860785335e688, telah diverifikasi dari log Actions: **22 pemeriksaan writer PASS**, mencakup dua siklus rollback AW..AZ dan pasang ulang serta empat refusal tanpa perubahan state pembanding. EmpatSQLrollback dan builder cocok hash manifest; capture18380bytes direkonstruksi dari log, SHA25662bb0e2a9a0bb69106538d32569239bf67bb8c79e05325808f837ad6f8450cf6. Produk forward tetap9add; tidak ada diff pada migrations/dev/release/cp6-t3/src.

**C6-10 tetap HOLD:** AW..AZ sudah tersedia dan diuji writer, sementara AC..AV versi release NOT_BUILT. AZ→AW kembali ke AV. Batas bukti: normalisasi capsule pada siklus2/reinstall mengecualikan captured_at dan boundary_snapshot; post-usefixture memakai satu INSERTaudit_logs. Review independen SQL/helper dan kecukupan oracle belum selesai. [Ledger](out/writer_6140edb_run_ledger.json) dan [catatan](out/writer_6140edb_review.md) menyimpan detail. Ini REUSED_WRITER_EVIDENCE; native15 tetap NOT_RUN.

## Dasar dan batas otoritas

Gate dan oracle berasal hanya dari tiga kontrak yang diserahkan pengguna:

- M: `ERP_V3_2_Master_Pulih_20260923.md`.
- P: `ERP_V3_2_Perubahan_Pulih_20260923.md`.
- BR: `ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md`, untuk batas tahap CP6/CP7.

SHA256 ketiganya tercatat dalam [AUDIT_PROGRESS.md](AUDIT_PROGRESS.md). Berkas latar ERP, komentar implementasi, status PASS writer, klaim auditor lain, serta ingatan audit lama tidak dijadikan oracle. Nomor baris M/P/BR mengacu pada berkas kontrak asli, bukan nomor baris laporan.

C6-01 sampai C6-10 adalah pengelompokan auditor. Satu operasi yang lolos pemeriksaan tidak menerima seluruh gate.

| Gate | Status | Contract file/lines | Current basis |
|---|---|---|---|
|C6-01 evidence identity/completeness|HOLD|M1624–1626,1693,1762–1767,4391–4393,4521–4525|Exact SHA/jobs bound; runner duplicate-ID loss; T2 disposition and missing independent cases remain.|
|C6-02 atomicity/immutable facts/exact state|HOLD|M3816–3826,5048–5052|U02/U03 corroborated from independently reviewed external native logs: historical WIP prefix and zero-qty inventory value counterexamples. REUSED_EVIDENCE; full lifecycle acceptance absent.|
|C6-03 recovery/input/unknown/selectors|HOLD|M1678–1679,1691,3817–3820,3825–3826,3939|Wrong WIB payloads, unstable request recovery and failed-read zero display reproduced locally; selector tails source-supported.|
|C6-04 ALL initial import|UNVERIFIED|M44–45,359–365,749–755,829–843,934–938,1024–1025,1691; P966–967|22-state semantic crosswalk persisted; native continuation and unmapped adapter obligations remain.|
|C6-05 dates/recost/HPP/journals/reports|HOLD|M375,377,837,1022,1059–1065,1666,1691,3816,3820,3825|F01 wrong WIB payload; U02/U03 native WIP/cent counterexamples corroborated via REUSED_EVIDENCE. Full dated financial acceptance absent.|
|C6-06 production/AP/AR/payroll/advances|HOLD|M359–379,629–648,749–757,3822–3824|U02 WIP counterexample corroborated via REUSED_EVIDENCE. Advance and payroll/BS attribution hypotheses still NOT_RUN; broader lifecycle coverage absent.|
|C6-07 accepted accessories/pocket|UNVERIFIED|M44–48,466–472,495,557–561,1023,3900–3902,3951,5192–5199|Positive local controls and source mechanisms; whole lifecycle/races not independently accepted; expanded CR scope separate.|
|C6-08 Auth/permissions/connected UI|UNVERIFIED|M1691,4486,5046–5052,5209,5213–5224|27 public RPCs traced;10 browser cases rerun; full real Auth/action/location/revocation matrix absent.|
|C6-09 concurrency/stale state|UNVERIFIED|M751–755,1025,4165,4486,5048–5052|Existing AR/AT/AU races rerun;20 AR observations independently checked narrowly; own full schedules absent.|
|C6-10 install/compatibility/rollback/cleanup|HOLD|M1767,3826,4306–4314,4486,5192–5209|Install/backup restore scoped positive;6140edb AW..AZ writercycle22PASS; AC..AV releaseNOT_BUILT and full rollback qualification remain open.|

## Cakupan yang telah dicatat

Matriks kewajiban yang terakhir disimpan di workspace memuat132 baris dalam27 keluarga:80 inti CP6,32 ekstensi CP6 yang diterima,13 baris bergantung pemilihan CR, dan7 batas tahap berikutnya/opsional.105 ID uji stabil dalam kontrak telah disilangkan. Angka itu bukan132 uji yang sudah dieksekusi.

Distribusi penilaian terakhir:96 UNVERIFIED,7 UNVERIFIED_SOURCE_RISK,5 HOLD_SOURCE_REPRO,2 PARTIALLY_VERIFIED,1 HOLD_QUALIFICATION,1 HOLD_EVIDENCE_PRODUCER,13 SCOPE_UNRESOLVED,7 DEFERRED. Baris yang belum dikerjakan tidak dihitung sebagai PASS.

Berkas matriks final belum berhasil dipulihkan byte-nya setelah workspace terputus. Receipt terakhir:
- `continuation/coverage_matrix.json`: `e5fdcc9fc6fdd165ee701094e2c60e8639b87673ec73bc9b1554c4c11491fd1d`.
- `continuation/coverage_completion.md`: `c5bb9160e0f6005e8d530a826504b0a61348d1bc8ba081278b70182e4c973394`.

Jangan menganggap kedua berkas itu sudah ada di cabang pemulihan ini. Versi checkpoint sebelumnya tersedia terpisah; pengganti byte tidak dibuat dengan mengklaim hash lama.

Hasil yang sekarang tersimpan langsung di cabang ini:

- [Ledger native per kasus](out/native_case_ledger.json): hasil terstruktur dan lokasi baris log dari sembilan job auditor yang sudah selesai, termasuk tahap install dan observasi restore.
- [Pemetaan semantik ALL](out/all_open_documents.md) dan [JSON](out/all_open_documents.json): enam keluarga dan22 keadaan dokumen cutover.
- [Pemeriksaan sumber payroll](out/payroll_source_followup.md): eligibility, snapshot/rate, kapasitas komponen, BS dan rework beserta batasnya.
- [Checkpoint dan langkah lanjut](AUDIT_PROGRESS.md).

## Bukti runtime yang benar-benar tersedia

Sembilan job di bawah merupakan eksekusi terpilih yang benar-benar baru pada saat dijalankan. Pengambilan ulang log dalam pemulihan ini bukan run baru. ID job warisan pada attempt berikutnya tidak dihitung sebagai eksekusi tambahan.

| Run ID | Job ID | Actual start UTC | Observed scope/result |
|---|---|---|---|
|36037873682|107772639059|18:23:54|Original326:314 PASS/control,12 date-policy HOLD; NEW34:25PASS/8COUNTEREXAMPLE/1INCOMPLETE; AO12:8PASS/4INCOMPLETE. DISPOSITION_REQUIRED, primary unchanged,clone0. Log2198–2199.|
|36037876338|107772603343|18:23:48|24install stages; restored same meaning318tables/1647rows,5checks; Auth0→0/primary unchanged.54advisorINFO reviewed, not assumed security exposure. Log1301–1330.|
|36037878419|107772676223|18:24:00|CodeQL JavaScript/TypeScript PASS,result_count0. Log2415.|
|36037873682|107792476681|19:15:14|AR146sequential+28race writerPASS. Independent raw-observation checker20scopedPASS/5INCOMPLETE/3UNVERIFIED.|
|36037876338|107792486765|19:15:17|Browser10PASS,console0,REST stopped,Auth0→0,primary unchanged. Opening WIP_OUTPUT flow only. Log1608–1609.|
|36037878419|107792495809|19:15:18|CodeQL Actions PASS,result_count0. Log1331.|
|36037878419|107794260297|19:19:58|CodeQL Python PASS,result_count0. Log1811.|
|36037873682|107795483321|19:23:12|AT16+AU15sequential and4+6races writerPASS. Raw worker results retained; boolean invariants not promoted to full independent proof. Log1739.|
|36037878419|107795615827|19:23:33|CodeQL C++ PASS,result_count0. Log1772.|

Semua terikat kandidat9add57e. Job pin T3 `107772660584`, baris1340, equal:true merupakan bukti existing yang dibaca, bukan rerun auditor baru.

Ledger menyimpan status output asli writer. Itu memungkinkan pemeriksaan ulang setiap kasus, tetapi PASS-only tanpa observasi bisnis rinci tetap terbatas. Seed/fixture diagnostics dikeluarkan dari jumlah kasus. Duplikasi pasangan group/case tidak ditemukan dalam catatan kasus native yang dipulihkan.

Tiga hash log fase1 cocok kembali setelah mempertahankan konvensi berkas lokal sebelumnya: UTF-8 hasil fetch ditambah satu LF. Ledger mencatat kedua hash, yaitu teks sebagaimana diambil dan varian dengan tambahan satu LF; tidak menyamarkan perbedaan encoding sebagai perubahan hasil.

### Interpretasi T2

BUSINESS230 terdiri dari179 PASS,39 CONTROL_PASS dan12 DATE_POLICY_REVIEW_REQUIRED; IMPORT31 dan VALUES65 PASS. Jadi326 kasus historis menghasilkan314 PASS/control dan12 HOLD kebijakan tanggal.

NEW34 tetap25 PASS,8 COUNTEREXAMPLE dan1 INCOMPLETE; AO12 tetap8 PASS dan4 INCOMPLETE. Overlay8 tanggal,5 tambahan dan12 calendar-policy disimpan terpisah. MATCH pada overlay writer tidak otomatis mengganti status mentah atau membuktikan oracle kontrak. Dua belas analisis calendar-policy merujuk keluarga kasus HOLD lama; tidak dihitung sebagai12 cacat tambahan.

Untuk AR, pemeriksaan auditor terhadap observasi mentah menghasilkan20 pemeriksaan sempit yang sesuai,5 INCOMPLETE karena rincian penolakan kurang, dan3 UNVERIFIED karena bukti hanya boolean writer. Pemeriksaan sempit mencakup satu header POSTED, satu efek kuantitas/nilai, debit-kredit agregat, dan beberapa penolakan yang teramati. Belum membuktikan semua akun, dimensi, lineage, prefix tanggal, baseline rollback, atau kesamaan respons replay.

AT/AU mempunyai hasil worker native, tetapi sejumlah invariant tetap hanya boolean writer. Menemukan mekanisme lock di source atau melihat status race PASS belum menerima seluruh C6-09.

### Interpretasi T3 dan CodeQL

Install24 tahap dan restore snapshot setelah install memberi bukti positif terbatas. Drill restore membandingkan318 tabel/1.647 baris dan lima pemeriksaan. Exit restore1 memuat19 error pg_cron yang diklasifikasikan; sumber memiliki0 cron jobs, data dibandingkan identik, dan engine dibandingkan sama. Ini belum membuktikan downgrade kandidat ke baseline.

Sepuluh kasus browser mencakup login nyata, penolakan anonymous, dua fixture identitas PRODUCT yang ambigu dalam WIP_OUTPUT, satu balasan hilang/remount/replay, stock/HPP dan inverse terkait. Kasus itu belum meliputi seluruh halaman, zona waktu perangkat, hak akses, lokasi atau pemulihan setiap command.

Empat CodeQL menghasilkan result_count0. Itu tidak menguji kebenaran bisnis SQL.54 INFO RLS-without-policy pada advisor mempunyai REVOKE eksplisit pada sumber yang ditinjau; jumlah INFO tidak dijadikan bukti otomatis kebocoran data.

## Temuan, oracle dan tingkat bukti

Prioritas adalah dampak potensial bila jalur dan kondisi yang dijelaskan terpenuhi, bukan pernyataan bahwa dampak produksi telah terjadi.

| ID | Priority/status | Independent oracle and evidence |
|---|---|---|
|F01|P1/local confirmed|M3820 WIB input2026-09-20T00:30 must serializeSep19T17:30Z on every device. Active Cutting/Pickup/BS serialize via device timezone.34exact-source checks28PASS/6FAIL; actual persisted ledger impact not native-tested.|
|U01|P2/source CONFIRMED,native corroboration limited|M1691 complete selectors. Claude XA2 returned100 recent eligible delivery rows while omitting oldqty10. Fixture uses privileged cloning; full legal producer/claim/UI sequence unverified. REUSED_EVIDENCE run36051514868/job107807966805.|
|U02|P1/CONFIRMED via REUSED_EVIDENCE|M3816,3820–3823. Claude XA1 on9add: second completion POSTED, stageprefix−8 and WIPGLPO−20. Run36048357523/job107797410652. Our original SI02 file remains NOT_RUN; reviewed equivalent native case is separately attributed.|
|U03|P2/CONFIRMED via REUSED_EVIDENCE|M1022,3818,3820. Claude XA1/XA2 correction+invoice paths endrawqty0 with inventory−0.01/up or+0.01/down. Up WIP10.02 vs10.01. Down half-tie oracle qualified; residual still confirmed. Jobs107797410652/107807966805. Our four original cases remain NOT_RUN.|
|R01|P2/local confirmed|M1767,4391–4393 traceable evidence. Duplicate IDs overwrite earlier INCOMPLETE in actual unchanged runner AST with I/O doubles. Raw logs retain both. Current indexed native cases had no duplicate group/ID.|
|R02|P2/qualification gap|M3826,4306–4314,5198–5209. At9add AW–AZ rollback absent. At6140edb four artifacts and22writercyclechecks PASS; AC..AV releaseNOT_BUILT, full inverse qualification open. Forward MANIFEST remainsNOT_TESTED; product unchanged.|
|C-AUTH-01|P2/local confirmed,post-lock|M1679,3819 retain exact request envelope. Pattern/Access retries regenerate UUID; quick-create can reuse UUID with changed payload.7local checks4PASS/3FAIL. Server uniqueness/version protections acknowledged; no committed duplicate/data-corruption claim.|
|C-SEL-01|P2/source confirmed,nativeUNVERIFIED|M1691,3826,4486;M495 for pocket cancel. Initial-import latest50 and pocket-period latest50 are sole action selectors; payroll/prepayment targets cap100. One public51draft scenario prepared; other valid fixtures unwritten.|
|C-UNK-01|P2/local confirmed,post-lock|M3825 unknown is not zero. Failed initial Laundry/QC workspace read leaves null but unconditional KPI expressions render0.4local checks2PASS/2FAIL. Error banners and writer locks remain; no financial finality or mutation bypass claim.|
|C-BIZ-01|candidateP1/nativeUNVERIFIED|M629–646 and3816–3820. Opening67.25D−8,correctionto100D−2,refund100D−4 predicts normal advance prefix−32.75 for supplier/vendor/customer while current0. Public route source traced; six cases NOT_RUN. Applying dated-prefix rule to advance monetary capacity is stated inference.|
|C-BIZ-02|unpromoted reachability lead|COUNT transfer/adjustment may admit0.5; no independent ordinary route proof. Runner conditionally grants schemaUSAGE. Four cases excluded from default batch; optional execution remains INCOMPLETE with privilege qualification.|

### Dampak dan batas temuan utama

**F01 — tanggal WIB bergantung zona perangkat.** Input2026-09-20T00:30 WIB harus menjadi2026-09-19T17:30Z. Callback aktif Cutting/Pickup/BS menggunakan `new Date(datetime-local).toISOString()`: pada perangkat UTC menghasilkan2026-09-20T00:30Z; pada Kiritimati menghasilkan2026-09-19T10:30Z. Ini dapat mengubah tanggal kejadian, urutan dan periode akuntansi yang diminta pengguna. Oracle M3820 dan34 pemeriksaan source lokal mendukung cacat payload; posting ledger pada browser nyata untuk fixture ini belum dijalankan. Locator: `src/ConnectedCuttingPage.tsx:272`, `src/ConnectedPickupPage.tsx:200`, `src/ConnectedBsResolutionPage.tsx:40` serta pemanggilnya. Laundry/QC dengan helper waktu bisnis menjadi kontrol positif.

**R01 — kehilangan kasus dalam ringkasan runner.** AST runner kandidat yang tidak diubah, dijalankan dengan I/O doubles, menimpa hasil pertama ketika ID kasus sama; ringkasan akhir dapat PASS walau kasus pertama INCOMPLETE. Log mentah tetap menyimpan keduanya. Ini kelemahan produsen bukti, bukan bukti transaksi ERP salah atau kasus T2 aktual hilang.

**C-AUTH-01 — identitas permintaan saat balasan tidak diketahui.** Retry save Pattern/Access membuat UUID baru; quick-create dapat mempertahankan UUID sambil mengubah payload dan kehilangan UUID ketika remount. Respons server setelah commit yang hilang belum direproduksi native. Unique/version guards mengurangi sebagian duplikasi, tetapi tidak memulihkan envelope permintaan semula. Dampak yang dibuktikan terbatas pada perilaku callback pemulihan, bukan committed double-write.

**C-UNK-01 — gagal membaca menjadi angka nol.** Awal workspace Laundry/QC yang gagal dibaca tetap null, sementara ekspresi KPI menampilkan0. M3825 membedakan data unknown dan zero. Error banner dan penguncian write masih ada; tidak diklaim sebagai bypass posting atau laporan keuangan final yang palsu.

**C-SEL-01/U01 — sumber valid di luar batas daftar.** Daftar import/pocket50 dan payroll/prepayment100 tidak memiliki kelanjutan pada pemilih tindakan yang diperiksa. Reader BS membatasi100 sebelum filter claimable. Ini berpotensi membuat tindakan terhadap sumber lama tak terjangkau dari UI. Satu skenario51 draft import telah disiapkan, belum dijalankan; fixture pocket/payroll/prepayment/BS lengkap masih harus ditulis.

**C-BIZ-01 — kapasitas advance pada tanggal historis.** Sumber67,25 padaD−8, koreksi menjadi100 padaD−2, refund100 padaD−4 diprediksi menghasilkan saldo normal−32,75 padaD−4 meskipun saldo sekarang0. Berlaku tanda aset untuk supplier/vendor dan tanda kewajiban untuk customer. Public dispatcher, state reducer dan period guard telah ditelusuri; koreksi dan refund memakai kapasitas kini. Enam skenario termasuk kontrol urutan disiapkan. Penerapan aturan dated-prefix M3816–3820 ke kapasitas uang muka dinyatakan sebagai inferensi auditor bersama M629–646; belum ada hasil native.

**U02/U03 — prefix WIP dan satu sen recost.** Oracle fase1 kami sekarang mendapat corroboration native dari kasus Claude pada exact kandidat. U02 menghasilkan stageprefix−8/WIPGLPO−20; U03 meninggalkan nilai persediaan±0.01 saat qty0 pada correction dan invoice. Ini REUSED_EVIDENCE yang diperiksa dari log asli, bukan run baru kami. Oracle half-even pada arah turun tidak dipakai untuk mengklaim WIP10.00 sendiri salah. Detail fixture, hash dan batas dampak ada di AUDIT_CLAUDE_CROSS_REVIEW.md.

**R02 — kualifikasi rollback seluruh paket belum lengkap.** Writer menambah empat rollback AW–AZ pada6140edb; dua siklus dan refusal tercatat PASS dalam22check native writer. Ini kembali ke AV; AC..AV versi paket rilis masihNOT_BUILT. OriginalAV teramati menolak releasechain tanpa perubahan state. GuarddigestAC tetap tidak boleh dilemahkan. Auditor perlu menilai generatedSQL/helper, normalisasi capsule dan cakupan oracle. Bukti AW..AZ ini dicatat sebagai kemajuan yang terbatas, dengan C6-10 tetapHOLD.

H01 identitas optional WIP, H02 perubahan alternate-route item draft, nullable expected_version pada deactivation, COUNT pecahan, dan kebijakan GRNI_ESTIMATE_OPEN tetap lead/kesenjangan yang belum dipromosikan.

## Lanjutan ALL dan payroll

Pemetaan [ALL](out/all_open_documents.md) mengikat kewajiban kontrak ke representasi yang diterima serta state yang diperlukan command berikutnya:

| Keluarga | Bukti sumber positif | Masih harus dibuktikan |
|---|---|---|
| Purchase/receipt/invoice | Uninvoiced receipt menjadi purchase item native; supplier debt lama menjadi opening subledger yang dapat diselesaikan. | Split receipt sebagian diinvoicing, hak retur lama, public cash-settlement chain dan procurement draft. |
| Sales/reservation/returns | AR lama bernomor dapat menjadi opening receivable. | Reservasi draft lama, alokasi lot untuk retur lama, credit/refund yang masih terbuka. |
| Payroll/attendance/reimburse | Kewajiban mandor yang sudah diakui dapat dibawa sebagai opening payable. | Kerja belum disetujui, attendance/carry, entitlement BOM dan pencegahan accrual kedua. |
| Advances/settlements | Sisa advance dan alokasi cash advance ke payroll baru mempunyai command lanjutan. | Prefix waktu, pemakaian bersamaan, pemilihan target lengkap, pemisahan utang aksesori dari cash advance. |
| Production/WIP/BS/laundry/rework | PO header, WIP SEWING/LAUNDRY, output terattestasi dan valued BS terpetakan. | Cut-but-unpicked, laundry delivery/claim lama dan rework yang sudah berjalan saat cutover. |
| Accessory/pocket custody | Stok awal dan tindakan issue/withdrawal baru terpetakan. | Hak retur nota lama, custody/condition/recovery bila CR dipilih, serta pool pocket lintas cutover. |

M930–938 mengizinkan provenance keuangan tanpa mengarang nota lama; M369–379 membatasi rekonstruksi sejarah WIP. Karena itu sumber yang belum terpetakan dicatat sebagai UNMAPPED, bukan otomatis cacat. Enam keluarga/22 keadaan juga bukan penerimaan ALL.

Pemeriksaan [payroll](out/payroll_source_followup.md) menolak dua dugaan dalam source: regular wages tidak diskalakan GOOD/laundry return, dan duplicate component rows tidak melewati cap melalui snapshot berbeda pada jalur yang diperiksa. Konservasi alokasi payroll, snapshot first-use, rate efektif, freeze rate yang sudah dipakai dan source lock telah ditelusuri. Installed definitions, lawful entry route dan native lifecycle tetap belum dibuktikan lengkap.

Satu risiko BS baru belum dipromosikan: group10 dengan komponenB selesai pada GOOD8 tetapi belum dikerjakan padaBS2 dapat mendapat baseline otomatis `min(2,8)=2`. Rework kemudian menghitung entitlement baru0, sementara fakta contoh mengharuskan2×25=50. Koreksi CLASSIFY_BS tersedia sebelum rework dan menjadi kontrol penting. Pemeriksaan dispatcher, save caller dan trigger menemukan koreksi itu opsional pada jalur source yang diperiksa; baseline tidak dikoreksi otomatis. Namun belum dibuktikan secara native bahwa fixture sah pada instalasi kandidat menyebabkan kehilangan entitlement. Tidak ada skenario executable/native untuk risiko ini.

Kepatuhan Special belum dapat dinilai normatif pada lanjutan ini karena bagian kontrak presisinya belum dibaca ulang. Source policy flags bukan pengganti oracle kontrak.

## Protokol buta dan rekonsiliasi

Lock fase1:
- `PHASE1_FINDINGS_LOCK.md`: `cbca0c6cb3150f0005bbea877d1a6b0371afa6103d9907c21899b1e235e46156`.
- `PHASE1_SHA256SUMS`: `50ba9228c863d4c483404bd425d8d64aac3073c3cd6726e35d9ca840d653438a`.

Writer evidence terpilih dibaca pada fase2 setelah lock. Recheck lokal terakhir menunjukkan kedua lock tidak berubah. Temuan C-* dan pemeriksaan ALL/payroll lanjutan dinyatakan post-lock.

Paparan sebelum lock tetap diungkap: ingatan audit sebelumnya, nama berkas terlarang/satu snippet judul commit, dan bocoran auditor lain. Semuanya dikecualikan sebagai oracle. R01 sudah direproduksi independen sebelum bocoran duplicate-ID. Klaim advisory lock dan second-connection commit tidak dinyatakan sebagai hasil native kita.

Rekonsiliasi mempertahankan batas klaim: install PASS tidak menerima rollback, browser10 tidak menerima semua flow/Auth, MATCH writer tidak mengganti status raw T2, INFO advisor bukan exposure otomatis, dan source/release40 body-match bukan bukti lengkap katalog terpasang. Tidak ada temuan native baru hanya karena dokumen writer menyebutnya.

Instruksi owner terbaru mengubah urutan: laporan Claude diminta diperiksa sekarang dan hasilnya digabung ke repo. Review dilakukan post-lock pada snapshotcf301a6, dengan kontrak/source/log Actions sebagai pembanding. Race36051535647/36052066150 terverifikasi gagal sebelum balapan; sumber xaudit_4 dibaca, tetapi kejadian classifier sendiri tetap laporan eksternal. Tidak ada upaya melewati penolakan izin atau mengambil credential. Lihat AUDIT_HANDOFF_CP6.md dan AUDIT_CLAUDE_CROSS_REVIEW.md.

## Skenario yang disiapkan

Default combined batch:15 cases, native **NOT_RUN**, run_id:null,job_id:null.
- combined_scenarios.py SHA256 `968cac54ac7fa7fe4e3fc1d666e257b04944faf1beec1f45a209274db00869d1`;25248bytes;33664base64chars.
- work/stock_import_scenario.py:4cases; SHA256 ff92e8d973ebb75c05ba8ac6b47da96565c9b50760c91b247f331a765d18df81.
- work/money_dates_scenario.py:4cases; SHA256 cfa1157b7ea39e6f5162d85a540ed5e22c30d8fef9ddfe840b5a9bf2f631d9ef.
- continuation/business/business_scenarios.py:6default advance cases,4held COUNT cases; SHA256 44b075c763a5d6962322d51e4b4ed0b75360b6e0135575420208ac39152b342b.
- continuation/auth_selector_scenarios.py:1case; SHA256 2276140a28ce27e9cd8e18b03285bdeee9aa33aee4118fe701eca20442bc3bd4.
Syntax, embedded-byte/hash equality, JSON roundtrip and unique factory IDs were checked. Factory enumeration used inert runtime imports. No case lambda/SQL executed.

Pembaruan recovery: exact stock_import_scenario.py dan money_dates_scenario.py (8kasus) telah dipulihkan dan disalin ke audit/scenarios/ dengan hash di atas. Byte final lama gabungan15/business6/selector1 tidak pulih utuh. Kini business6+selector1 telah direkonstruksi dengan hash baru dan digabung bersama8kasus exact menjadi payload15baru; native tetap NOT_RUN. Matrix lama tetap berbeda hash dari versi final.

Empat kasus COUNT yang membutuhkan kualifikasi privilege dikeluarkan dari batch default. Runner yang disetujui mempunyai conditional schema USAGE grant; keberhasilan di bawah grant tersebut tidak membuktikan ordinary reachability pada ACL kandidat yang belum diubah.

## Pekerjaan tersisa dan hambatan konkret

| Jenis | Keadaan aktual | Syarat lanjut |
|---|---|---|
| Workspace | Sudah online lagi; folder lama hilang. Penyebab platform dari409 terdahulu tidak teramati. | Kontrak, lock fase1 dan8kasus exact sudah pulih. Rekonstruksi hanya revisi yang hilang dengan hash baru; jangan mengaku sebagai byte lama. |
| Dispatch | Tool sesi ini dapat rerun job existing; tidak menyediakan custom workflow-dispatch POST atau DB lokal. | Jalankan payload yang sudah disiapkan melalui endpoint disposable yang disetujui dari lingkungan berkemampuan dispatch. Jangan ubah workflow atau produk untuk melewati batas. |
| Oracle Special/rate | Bagian kontrak rinci tidak tersedia untuk dibaca ulang pada fallback ini. | Pulihkan kontrak asli dan verifikasi hash/baris sebelum putusan normatif. |
| Rollback | Jalur AW–AZ lengkap belum tersedia/terkualifikasi. | Writer menyediakan downgrade atau demonstrasi refusal aman yang memenuhi kontrak; auditor memverifikasi native. |
| Pekerjaan audit belum dilakukan | Native15, fixture selector lain, browser timezone/unknown/recovery, Auth/action/location, jadwal concurrency sendiri, transitive HPP/source producers dan sejumlah adapter ALL. | Siapkan fixture sah dan oracle independen, jalankan serta catat dampak, replay/inverse, rollback/cleanup. Ini bukan semuanya hambatan alat. |
| Laporan auditor lain | Owner terbaru meminta review sekarang dan penggabungan repo. | Cross-review selesai untuk temuan/hambatan prioritas; hasil deduplikasi dan queue lanjut ada di AUDIT_HANDOFF_CP6.md. Seluruh CP6 tetap belum selesai. |

Tidak ada produk, main, cabang kompetisi/writer, hosted/legacy/production database atau deployment yang diubah oleh pekerjaan pemulihan. Cabang ini berisi artefak audit. Laporan dan log di sini memungkinkan sesi berikut melanjutkan tanpa mengulang fase1 atau mengandalkan chat sebagai satu-satunya checkpoint.


## Pembaruan integrasi audit silang — 24 September2026

Owner meminta audit GPT dan Claude digabung tanpa mengulang temuan yang sama. [AUDIT_HANDOFF_CP6.md](AUDIT_HANDOFF_CP6.md) menjadi pintu masuk lanjut: satu ID gabungan per isu, alias kedua audit, tingkat bukti, status disagreement,4hambatan runtime dan next actions. [AUDIT_CLAUDE_CROSS_REVIEW.md](AUDIT_CLAUDE_CROSS_REVIEW.md) menjelaskan verifikasi dan batas tiap klaim. Laporan asli/hasil gagal tetap dipertahankan melalui referensi commit.

Koreksi penting: ALL sudah disetujui menurutM1024; F1-02 bukan konflik keputusan aktif. F1-12 numeriknya terbukti tetapi identitas sumber fisik lintas batch belum ditentukan. Run race rev2 memakaiSHA5d640e42..., bukanSHA3915e006... milikrev1. Hasil tersebut belum menjadi penerimaan seluruh gate. Tidak ada custom native run baru selama recovery/cross-review.


## Sumber native15 siap, eksekusi belum berjalan

Payload audit/scenarios/combined_native15_reconstructed.py mempunyai SHA256`cec2ad521835476cf702119486e637d3eff4b62d8f72197a9ca2c2d50cf1fadb`,47183bytes dan15caseID unik. Manifest audit/scenarios/native15_manifest.json mengikat8kasus frozen exact dan7rekonstruksi post-lock. Sintaks, registrasi tanpa DB, source embedding dan hash sudah diperiksa; **belum ada native run atau hasil bisnis**. RunID/jobIDnull. BatasoracleSI01, moneyDOWN, advance danUIselector dicatat pada manifest. Ini tidak mengubah HOLD atau audit_complete=false.

## Addendum Fable — hasil native lanjutan (24 Sep 2026, run 36065350201 & 36065517737 pada head alat d284e9b, produk 9add57e)
Rincian expected/actual per kasus: `out/fable_native15_xaudit5_results.md`; register diperbarui di `audit/CP6_COMBINED_INDEX.json`.
- native15 (skenario GPT, oracle direview Fable): SI-01 COUNTEREXAMPLE (WIP teridentifikasi diselesaikan sebagai produk/brand/warna lain; CP6-18), SI-02 COUNTEREXAMPLE (prefix WIP −8; CP6-02), SI-03 PASS, SI-04 COUNTEREXAMPLE (draf prepared diedit lalu POSTED tanpa rekonsiliasi; CP6-19, caveat reachability), MONEY 4× COUNTEREXAMPLE (CP6-03), ADVANCE ORDERED 3× PASS, ADVANCE DATED_CAPACITY 3× COUNTEREXAMPLE (**CP6-07 P1**: uang muka −32,75 pada prefix), SELECTOR-51 INCOMPLETE (fixture GPT; rerun run 36066079063).
- xaudit_5 (oracle Fable pada mode dua sesi + Auth/HTTP nyata writer): R1 CP6-09 terbukti di bawah dua sesi (kunci ada, guard tidak); **R2 baru CP6-24 (P2)**: close tanggal yang sama diulang → dua filing; R3 aman (penolakan POCKET_PERIOD_BUSY, tidak ada output ganda; pesan ≠ STALE_VERSION); H1 matriks fail-closed anon/GUDANG/viewer(M:281)/OWNER lulus substansi (2 cek gagal = artefak argumen dummy probe); H2 revocation PASS; H3 unmapped PASS. Browser→HTTP→runtime UI belum.
- Verdict tetap: CP6 HOLD, audit_complete=false, production_go=false.

## Addendum Fable — CP6-19 lewat jalur aplikasi yang sah (25 Sep 2026, xaudit_6 rev3, run 36081137254, head alat d284e9b, produk 9add57e)
- Permintaan owner: uji CP6-19 lewat jalur aplikasi yang sah karena M:1025/M:3817 mengizinkan draf prepared diedit.
- rev1 (run 36080176237) dan rev2 (run 36080510340) INCOMPLETE: file hasil edit ditolak validasi impor produk (asal biaya > nilai; qty penerimaan ≠ sisa bahan + asal biaya). Bukan bukti produk.
- rev3 (2/2 PASS, `primary_unchanged=true`): edit konsisten neraca setelah VALIDATE → FINALIZE memposting isi terakhir (item WIP 4/20.00, sumber 4, stage events 4, satu baris WIP). Setelah prepare lewat RPC yang di-grant ke `authenticated`, SAVE_FILE ditolak eksplisit ("Batch ini sudah menerapkan master melalui jalur lama").
- Kesimpulan: **CP6-19 REFUTED pada jalur aplikasi yang sah**. SI-04 (COUNTEREXAMPLE beku, run 36065350201) tetap tercatat sebagai edit SQL langsung pada `erp.opening_balance_items`; residu P3 opsional: grant `authenticated` pada `erp.prepare_migration_opening_balance` dan tidak adanya cek ulang item-vs-staging (`…20ap….sql:2283`). Bukan penahan gate.
- Verdict tetap: CP6 HOLD, audit_complete=false, production_go=false (P1 CP6-09, CP6-01, CP6-02; rollback AC..AV NOT_BUILT; D01–D06 belum diputuskan).

## Addendum Fable — keputusan owner D01–D06 disahkan (25 Sep 2026)
- Owner mengonfirmasi langsung di sesi audit: pilihan A untuk D01–D06, termasuk akun lawan AX = pendapatan lain-lain. Label OWNER_CONFIRMED_CHAT; tiga kontrak belum berubah, addendum bernomor masih harus ditulis writer dan disahkan tertulis (handoff C0).
- Dampak register: CP6-07 → P1 wajib (kapasitas per tanggal, handoff A9/C2); CP6-18 → P2 wajib (produk WIP awal mengikat, A10/C3); 25 kasus T2 beku mendapat oracle baru setelah addendum ada (C1); GATE-16 menunggu daftar acceptance ID (C6).
- Verdict tetap: CP6 HOLD, audit_complete=false, production_go=false.

## Addendum Fable — putaran 8 (25 Sep 2026, head 9dd7bc2, produk a095a9d)
Rincian di `out/fable_r8_results.md`. Rerun auditor pada kandidat baru a095a9d: A1/CP6-09, A3/CP6-02, A4/CP6-03 (satu penerimaan), A5/CP6-04, A6/CP6-24, A9/CP6-07, A10/CP6-18 **tertutup** dengan skenario auditor sendiri (open_1 13/13, open_2 4/4, xaudit_1_rev2 4/4, xaudit_2_rev2 5/5, selector-51 PASS, xaudit_7 12/12 termasuk kontrol positif dan upaya bypass; R2 dua sesi satu filing). A2/CP6-01 tertutup lewat review sumber. Dua COUNTEREXAMPLE rev1 (arah DOWN) ditarik sebagai kesalahan oracle auditor (HALF_EVEN vs half-up; M:485).
T3 package (36095715362): 25 berkas terpasang, gate {installed, primary_unchanged, drill, advisors} true, browser 10/10, label T3_PREP. T3 rollback AC..BA cycle 127/127 (36095723676). T2 (36095707100): identitas identik dengan referensi; 25 beku tetap HOLD (M:1769); oracle pasca-addendum ditulis (`out/fable_t2_oracles_post_addendum.md`, 24/25 PASS di bawah D01, ADJUSTMENT_DATE INCOMPLETE fixture).
Dokumen: hash addendum C0 dan bagian 1–8 (d39762da…) serta lampiran C6 cocok; kutipan bagian 9 = chat writer (UNVERIFIED_OWNER_DECISION sampai owner mengonfirmasi ke auditor). Lampiran C6: 9/11 cocok, ACC-04 dan LAU-05 salah label CR-TUNDA (M:1668 "tetap dibutuhkan"), 7 sub-keputusan tanpa baris → D06 belum bisa disahkan.
A7 tidak perlu; A8 direkomendasikan sebelum rilis (tidak menahan). B1 terbukti (ID ganda menolak grup; bocor → INCOMPLETE).
- Verdict tetap: CP6 HOLD, audit_complete=false, production_go=false. Penahan tersisa: 25 T2 beku menunggu run dengan oracle baru, D06/GATE-16, cakupan ALL, browser auditor, konfirmasi owner atas teks addendum.
