# BE — handoff writer, 27 September 2026

Status: verifikasi sumber BE-23 berjalan. **CP6 HOLD, audit_complete=false, production_go=false, release_evidence=false.** Hasil writer tidak menggantikan penerimaan auditor independen. Status final dan identitas bukti akan diisi setelah seluruh run dibaca.

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

PENDING: native16, race9, HTTP2, browser6, paket29 terpin, rollback143 checks, T2 dan CodeQL pada source BE-23. Bukti sebelum BE-23 dicatat di progres dengan identitas aslinya dan tidak dipindahkan ke source baru.

## Disposisi T2 yang tidak boleh disamarkan menjadi PASS

Oracle beku dipertahankan. Pada run sebelum BE-23, BUSINESS230/IMPORTS31/VALUES65 mempunyai identitas/status sama dengan AU; BUSINESS mencakup179 PASS,39 CONTROL_PASS,12 DATE_POLICY_REVIEW_REQUIRED. NEW_CASES34:25 PASS,8 COUNTEREXAMPLE tanggal AS,1 INCOMPLETE ADJUSTMENT_DATE. Trial AO:8 PASS dan4 INCOMPLETE tanggal invoice. Kedua belas HOLD tetap HOLD.

Oracle tanggal yang disetujui owner memiliki grup terpisah: AS8/8 MATCH, oracle B5/5 PASS ditambah kalender12 MATCH, serta C0 auditor25/25 PASS. Persetujuan, penjelasan pembaca tanggal dan sumber oracle ada di handoff Claude/GPT §23.5–23.6 dan dalam `scripts/cp6_t2_regression.py`. Tidak mengganti hasil kasus beku.

Kasus AR lama `ACCESSORY_CONNECTED_ZERO` tetap INCOMPLETE karena harga nota manual nol ditolak `BC_FREE_REQUIRES_POLICY`. Pengganti `ACCESSORY_CONNECTED_ZERO_REFUSED_BC_FREE_POLICY` harus PASS, berdasarkan ERP-DEC02. Ini berbeda dari race ACTION BE-21 yang merupakan regresi produk dan telah diperbaiki, bukan diterima sebagai disposisi.

## Yang masih menjadi tanggung jawab penerimaan independen

- Audit BE terhadap kontrak, antarmuka, lifecycle, permission, race, recost dan seluruh sumber biaya; hasil writer bukan self-acceptance.
- Terima dan tindak lanjuti audit BD terpisah sesuai arahan owner; tidak mengklaim audit itu selesai.
- Tinjau disposisi T2 historis tanpa mengubah frozen result.
- Tinjau batas advisor/restore: tambahan INFO RLS tanpa policy pada tabel private/capsule; restore clone hanya menerima pengecualian pg_cron yang terjelaskan. Ini tidak berarti zero-advisory atau restore cron produksi telah diuji.
- Selesaikan gate gabungan CP6 dan persetujuan sebelum hosted migration/deploy/production. Manifest builder tetap T3_PREP; bukti eksekusi dibaca terpisah dari metadata generasi.

Sebelum penulisan berikutnya: baca head remote dan hasil audit yang relevan, pastikan single writer, pertahankan predecessor dan frozen oracle, lalu ubah hanya sumber yang perlu. Bila writer lain muncul, berhenti dan beri tahu Hansen.
