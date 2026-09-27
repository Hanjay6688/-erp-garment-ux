# BE — handoff writer, 27–28 September 2026 WIB

Status: **implementasi dan verifikasi writer selesai; siap audit independen dengan disposisi T2 yang tercatat.** Verifikasi terakhir dibaca pada 28 September 2026 sekitar00.09 WIB. **CP6 HOLD, audit_complete=false, production_go=false, release_evidence=false.** Hasil writer tidak menggantikan penerimaan auditor independen.

Bukti terstruktur: [writer_verification.json](evidence/cp6-be-20260927/writer_verification.json). Log keamanan lokal: [security.log](evidence/cp6-be-20260927/security.log). Riwayat kegagalan dan perbaikan dipertahankan di [progres writer](cp6-writer-gpt-progress.md).

## Mandat dan batas

Hansen mengizinkan GPT mengambil estafet pada 27 September 22.47 WIB bila tidak ada push writer lama; BD diaudit terpisah dan temuannya ditangani menyusul. Interupsi alat berikutnya adalah `aborted by user`, bukan bukti writer lama. Owner meminta penjelasan dan kelanjutan pada 23.25 WIB. Setiap perubahan tak dikenal pada writer branch harus menghentikan penulisan dan dilaporkan.

- Repository: `Hanjay6688/-erp-garment-ux`; satu writer pada `claude/new-session-deapao`.
- Baseline estafet: `08065a3b4da71c51ffbbab77f0a6b1ac7e6638ec`.
- Sumber produk terbaru: `73dc4055685e3f6bbefcd4c61bce1e60dcce26e3` (BE-23).
- `main` tetap `557005e6674058f1e5e966b350cba05501e06182`; competition tetap `ca7f09556397801c50a2277bdb65b1bf019f9a05`.
- Semua database eksekusi berupa salinan disposable; hosted/UAT/legacy tidak dimutasi. Tidak merge, deploy, atau mengubah keputusan bisnis.
- Pengecekan remote hanya melihat push yang tersedia. Ia tidak membuktikan bahwa editor lokal pada chat lain berhenti. Tidak ada janji pemantauan setelah sesi berakhir.

## Konteks kerja yang tetap berlaku

Prioritas owner: reliable data; stok, HPP, dan keuangan harus sesuai kejadian nyata. Instruksi owner terbaru mengalahkan proposal writer; kontrak M/P, addendum keputusan CP6, C6 rev4 yang disahkan, serta errata ALL-C04 menjadi acuan. Nominal fixture bukan tarif/kebijakan produksi.

Framework existing: React/TypeScript/Vite, backend Supabase/PostgreSQL dengan facade RPC sempit, pengujian native Python/SQL serta browser Playwright. Tidak ada upgrade dependency. CI memakai Supabase CLI `2.116.0` dan PostgreSQL `17.6.1.165`; runtime lokal tidak mempunyai Docker/PostgreSQL siap, sehingga hasil native diambil dari CI tersebut.

Sumber konteks lanjutan: `docs/cp6-au-r1-handoff.md` (riwayat Claude/GPT sampai BD), `docs/cp6-writer-gpt-progress.md` (BE dan estafet), `docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25.md`, serta lampiran C6 pada direktori yang sama. Handoff pemulihan konteks menyimpan kontrak M/P/BR, kebutuhan pabrik, framework, reliability, dan keputusan lama; bagian prep-only pada handoff itu sudah dilampaui izin estafet 22.47 WIB.

## Empat alur BE

| Alur | Perilaku yang dibangun | Batas yang harus tetap dijaga |
|---|---|---|
| Ganti merek FG | Pilih lot sumber tepat, pindah jumlah/nilai atomik ke SKU tujuan, biaya aksesori/jasa dan bongkaran tertaut, recost ke turunan terjual/retur/konversi | Model konstruksi dan ukuran harus sesuai; tidak mengambil lot FIFO lain; opening/non-PO hanya lewat sumber nilai yang admitted |
| Rework ke SKU baru | Partial disimpan; COMPLETE menghasilkan GOOD native dan mengonversi lot itu dalam satu transaksi | Partial tidak membuat FG/payable; GOOD+BS=sent; tidak menggandakan hasil; inverse tertaut |
| Celup ulang | Target SKU, sumber jasa vendor nyata, harga unknown tetap pending, invoice BD meneruskan selisih biaya ke FG/COGS | Rework laundry gratis existing tetap gratis; unknown bukan nol; tarif per PCS per sumber sesuai D10, bukan per ukuran |
| Kain kantong / ALL-C04 | Impor pengeluaran historis dan hasil jahit, gabung denominator historis/native termasuk Afui, alokasi expense ke WIP/FG/COGS, koreksi/inverse tanpa stok keluar kedua | Histori ALLOCATED hanya referensi; provenance dan total kontrol wajib; tidak membuat hasil jahit/gerakan stok historis palsu |

Seluruh posting tetap atomik dan immutable; koreksi append-only; permission diperiksa sebelum cache replay; request hash, stale version, recovery fence, kapasitas, tanggal ekonomi/fisik, serta detector tetap berlaku. D01 mempertahankan tanggal ekonomi, memakai tanggal barang untuk koreksi terkait tahap dan tanggal pengakuan yang sah saat periode tutup. D06 tetap mencakup seluruh ALL22/ACC39/LAU36 dan tambahan BE dalam CP6.

## Perbaikan selama estafet

1. Invoice kain kantong dengan selisih uang nol tetap menyegarkan kepastian HPP. Tidak membuat event/jurnal uang nol buatan.
2. Preview konversi dapat mengambil row lock melalui PostgREST; reader dengan hak view melihat preview tanpa biaya dan tetap tidak dapat posting. Validator mutasi native tetap berlaku saat posting.
3. Koreksi opening yang telah dijual, diretur, atau dikonversi menyiapkan propagasi nilai turunan sebelum pemeriksaan exact source delta. Guard konversi non-PO tanpa sumber tidak dihapus.
4. Allowlist keamanan mencatat tepat enam pasangan RPC BE existing; larangan RPC dinamis/akses tabel bebas/unsafe HTML tetap. CodeQL mengikuti perubahan scripts/src/workflows.
5. Ditambah kontrol mixed historis/native dengan Afui, as-of periode tutup, inverse setelah sale-return-conversion, dan browser unggah kedua CSV BE.
6. Alat browser membandingkan uang negatif dengan tanda pada seluruh angka exact BigInt; assertion jurnal impor tetap -91.25. Locator mobile ditautkan ke dokumen fixture. Fixture tanggal tutup dan lokasi kolom attendance diperbaiki; expected bisnis tidak diubah.
7. Regresi BE-21 menemukan adapter impor mengambil pocket lock pada batch tanpa baris pocket. BE-23 membatasi lock pada batch yang memiliki baris pocket belum diterapkan. Frozen `REQUEST_CONCURRENT_ACTION` beserta jadwal/assertion-nya tetap utuh dan wajib lulus ulang.

## Angka kain kantong yang dikunci

- Denominator10 PCS: WIP5, FG3, terjual2. Biaya11.25 dialokasikan 5.62 / 3.38 / 2.25; koreksi15.00 menjadi7.50 / 4.50 / 3.00. Pembulatan mengikuti urutan native agar seluruh sen tetap terjelaskan.
- Mixed10 PCS historis +10 native termasuk Afui: sumber22.50; WIP11.24, FG6.76, COGS4.50, expense-22.50. Pembulatan per sumber dipertahankan.
- Impor CSV melalui UI: draft tidak membukukan fakta; VALIDATE lalu FINALIZE memberi WIP50, FG30, expense11.25, opening equity-91.25; satu sumber5 unit dan denominator10; tidak ada material movement atau sewing completion palsu.

## Bukti final

Runtime SQL, frontend dan scripts tidak berubah sejak product head73dc405. Paket dipin pada `e09b0207f08b7736fad79e82fd81f1bf5dc1a85d`; rollback disesuaikan pada `bfeca3e9ff33d3c342fef931dac79f7e6a2c3279`. Commit dokumentasi berikutnya tidak mengubah sumber yang diuji. Bukti sebelum BE-23 dicatat di progres dengan identitas aslinya dan tidak dipindahkan ke source baru.

| Bukti | Run / job | Hasil yang dibaca dari log |
|---|---|---|
| Native sebelum/sesudah BE | 36334558778 / 108662809909,108662810136 | Sebelum16 NO_ROUTE sesuai rencana; sesudah16/16 PASS,34 snapshot parser diterima,mismatch kosong |
| Race / HTTP / browser BE | 36334558752 / 108662810029 | Race9/9,HTTP2/2,browser6/6 PASS,console_errors0,Auth dibersihkan,primary tidak berubah,clone0 |
| CodeQL security-extended | 36334558739 / 108662809937,108662810067,108662810095,108662810118 | Actions,JS/TS,C/C++,Python PASS; masing-masing result_count0; SARIF artifact, bukan upload Code Scanning |
| T2 temporal | 36334558842 / 108663058400 | AT16+4 race,AU15+6 race semuanya PASS |
| T2 AR | 36334558842 / 108663058476 | 145 sequential PASS +1 superseded INCOMPLETE; pengganti BC PASS;28/28 race PASS,termasuk ACTION yang diperbaiki |
| T2 regresi | 36334558842 / 108663058496 | 422 status per kasus sama dengan run sebelum koreksi lock; BUSINESS230/IMPORTS31/VALUES65 sama dengan AU; disposisi historis tetap, C0 25/25 PASS |
| Paket install/compare/restore | 36334904571 / 108663778946,108663778791 | 29/29,ALL_STAGES_INSTALLED; pins_reproduced equal=true,differ=[]; keempat gate true |
| Browser paket | 36334904571 / 108663779050 | 10/10 PASS,console_errors0; login asli,anonymous refusal,lost reply+replay,stok/HPP per brand,inverse |
| Rollback final | 36335243724 / 108664744431 | 143/143 PASS: dua cycle29 keluarga, reinstall identik, urutan/admission ditolak,29 post-use refusal; primary tidak berubah |
| Security lokal | npm run test:security pada e09b020 | Exit0; ownership/akses/CP5/CP6/predecessor,build-secret canary,UAT Auth boundaries |

TypeScript `tsc -b` dan50 file/558 Vitest telah PASS pada estafet BE-18; tidak ada perubahan frontend sesudahnya. Ini dicatat sebagai bukti frontend yang sama, bukan run ulang pada commit dokumentasi akhir.

Identitas SHA-256:

| Artefak | SHA-256 |
|---|---|
| `supabase/dev/cp6_be_t1_family.sql` | `a540f9a99ba9cb3f8bc99e95cde45a0c31bd1c1468a9f1a50e233f2fc4552384` |
| BE release SQL | `80cfbc8877cf5605d0f7ac147d9cd437f0caea1fa9ab177ce664fb14c33633fe` |
| Release MANIFEST | `1bd374834e0a425e5191bf3b71397ace5fbe49b65a52b5a4dba1a813950544ec` |
| Pin `be_pins_36334558775.json` | `64f99a9d4104207ecf68c64e7b5f0b9aa37eab8e39284cde45aace76b81f3ef5` |
| Canonical rollback capture | `ae704f42e6d56fd8d5c8ea2b4a60aeb69aa319f50555d0cfe439408366d0ec61` |
| BE rollback SQL | `71c2368dd40bb990569a48923e328e6d85cd29e9f55ad329260977bf592d49fb` |
| Browser BE script | `c64245bbac78abd6744f3754f8b2983ed09ed2e73e33173ed9fc19ae8138ab52` |

Advisor raw verdict tetap REVIEW_REQUIRED:73 baseline menjadi205,132 tambahan seluruhnya INFO `rls_enabled_no_policy` pada tabel private/capsule,tidak ada penghapusan. Gate khusus menerima jenis ini; bukan klaim zero-advisory. Restore `RESTORED_SAME_MEANING`:data identik dan engine sama; exit1 berisi19 galat pg_cron saja karena clone bukan database `postgres`,unexplained=[]; catalog difference seluruhnya diklasifikasi. Tidak ada job cron sumber. Restore cron produksi tidak diklaim.

## Peta berkas implementasi

| Area | Berkas utama |
|---|---|
| SQL | `scripts/cp6_be_objects_{conversion,cost,nonpo,rework,redye,pocket}.sql`; builder `cp6_be_build.py`,`cp6_be_pocket_build.py`,`cp6_be_redye_build.py`; hasil `supabase/dev/cp6_be_t1_family.sql` |
| Ganti merek | `src/ConnectedProductConversionPage.tsx`,`src/productConversion.ts` |
| Rework/celup | `src/ConnectedBsResolutionPage.tsx`,`src/ConnectedLaundryPage.tsx`,`src/LaundryBdPanel.tsx` |
| Kain kantong/impor | `src/ConnectedPocketFabricPage.tsx`,`src/BePocketHistory.tsx`,`src/ConnectedInitialImportPage.tsx`,`src/initialImportCatalogBE.json` |
| Pembuktian | `scripts/cp6_be_probe.py`,`cp6_be_cost_probe.py`,`cp6_be_pocket_probe.py`,`cp6_be_modes.py`,`cp6_be_browser.mjs`,`cp6_be_browser_fixture.py`; T2 `cp6_t2_regression.py` |
| Rilis/pemulihan | `supabase/release/cp6-t3-src`,`cp6-t3`,`cp6-t3-rollbacks`; capture dan pins di `docs/evidence/cp6-t3` |

## Disposisi T2 yang tidak boleh disamarkan menjadi PASS

Oracle beku dipertahankan. Pada run final `36334558842`, BUSINESS230/IMPORTS31/VALUES65 mempunyai identitas/status sama dengan AU; BUSINESS mencakup179 PASS,39 CONTROL_PASS,12 DATE_POLICY_REVIEW_REQUIRED. NEW_CASES34:25 PASS,8 COUNTEREXAMPLE tanggal AS,1 INCOMPLETE ADJUSTMENT_DATE. Trial AO:8 PASS dan4 INCOMPLETE tanggal invoice. Kedua belas HOLD tetap HOLD. Seluruh422 status unik yang dicatat job regresi sama dengan run `36333723666`: tidak ada kasus ditambah,dihapus,atau bergeser akibat perbaikan scope lock BE.

Oracle tanggal yang disetujui owner memiliki grup terpisah: AS8/8 MATCH, oracle B5/5 PASS ditambah kalender12 MATCH, serta C0 auditor25/25 PASS. Persetujuan, penjelasan pembaca tanggal dan sumber oracle ada di handoff Claude/GPT §23.5–23.6 dan dalam `scripts/cp6_t2_regression.py`. Tidak mengganti hasil kasus beku.

Kasus AR lama `ACCESSORY_CONNECTED_ZERO` tetap INCOMPLETE karena harga nota manual nol ditolak `BC_FREE_REQUIRES_POLICY`. Pengganti `ACCESSORY_CONNECTED_ZERO_REFUSED_BC_FREE_POLICY` PASS, berdasarkan ERP-DEC02. Ini berbeda dari race ACTION BE-21 yang merupakan regresi produk dan telah diperbaiki: run final mengamati blocking nyata, menolak key sama dengan action berbeda sesudah pemenang commit, dan membuktikan perubahan stok/jurnal tepat sekali.

## Yang masih menjadi tanggung jawab penerimaan independen

- Audit BE terhadap kontrak, antarmuka, lifecycle, permission, race, recost dan seluruh sumber biaya; hasil writer bukan self-acceptance.
- Terima dan tindak lanjuti audit BD terpisah sesuai arahan owner; tidak mengklaim audit itu selesai.
- Tinjau disposisi T2 historis tanpa mengubah frozen result.
- Tinjau batas advisor/restore: tambahan INFO RLS tanpa policy pada tabel private/capsule; restore clone hanya menerima pengecualian pg_cron yang terjelaskan. Ini tidak berarti zero-advisory atau restore cron produksi telah diuji.
- Selesaikan gate gabungan CP6 dan persetujuan sebelum hosted migration/deploy/production. Manifest builder tetap T3_PREP; bukti eksekusi dibaca terpisah dari metadata generasi.

Sebelum penulisan berikutnya: baca head remote dan hasil audit yang relevan, pastikan single writer, pertahankan predecessor dan frozen oracle, lalu ubah hanya sumber yang perlu. Bila writer lain muncul, berhenti dan beri tahu Hansen.
