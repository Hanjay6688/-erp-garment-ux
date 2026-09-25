# CP6-05/06 — hasil browser dan kontrol fixture, 25 September 2026

Kandidat: tool `9dd7bc2b9309d008e8a2e50d81876d831f3e5ea7`, produk `a095a9d804d29643721e18635c2c3e26adcd56ea`. **Pembuktian kasus browser di bawah selesai; audit seluruh CP6 belum selesai. CP6 HOLD, audit_complete=false, production_go=false.**

## Hasil yang berlaku

| Kasus | Run / job | Hasil dan batas |
|---|---|---|
| CP6-05 / W10: Pola dan duplikasi role | 36102303107 /107967209608 | 2COUNTEREXAMPLE: server benar-benar commit HTTP200, balasan diputus; klik ulang mengubah UUID (role juga kodeCUSTOM), ditolak409; satu row tetap. M1679/3819 mengharuskan envelope dipertahankan dan hasil lama direkonsiliasi. Bukan duplikasi data/eskalasi hak/kerugian finansial. P2 GPT vs P3 Fable dicatat. |
| Laundry healthy control rev5 | 36106291785 /107979461548, baris2126 | PASS: Auth RPC200, parser asli menerima, browser menampilkan20, tidak ada ID seed bermasalah dalam respons. |
| Laundry initial unknown rev5 | run/job sama, baris2127 | COUNTEREXAMPLE M3825: read gagal → empat KPI0, banner error dan write lock. Gangguan dilepas → HTTP200/parser/UI20, error hilang. Kontrol refetch PASS; tidak terbukti bug refetch. |
| QC healthy control rev6 | 36106777202 /107980988537, baris2126 | PASS: Auth RPC200, parser asli menerima, browser menampilkan10, ID seed bermasalah tidak muncul. |
| QC initial unknown rev6 | run/job sama, baris2127 | COUNTEREXAMPLE M3825: read gagal → empat KPI0 + error/write lock; refetch pulih ke10. Kontrol refetch PASS. |

**CP6-06/W13 P2 dikonfirmasi pada Laundry dan QC.** Oracle hanya menerima representasi unknown saat data tidak diketahui; angka0 tetap sah untuk bacaan berhasil yang benar-benar nol. Tidak ada bypass mutasi atau laporan finansial final palsu yang dibuktikan oleh kasus ini. Perilaku refetch pada fixture valid yang diuji bekerja.

Run QC berwarna hijau dan berlabel RUN_COMPLETE, tetapi berisi1PASS+1COUNTEREXAMPLE. RUN_COMPLETE berarti hasil kasus lengkap, **bukan penerimaan produk**. Laundry dan QC diambil dari run yang berbeda; tidak mengklaim satu run4/4PASS.

## Penyebab INCOMPLETE lama dan perbaikan fixture

Diagnosis GPT rev3 dan sumber Fable sejalan: fixture warisan `a1000000-0000-0000-0000-000000000001` (mandor) dan `a2000000-0000-0000-0000-000000000001` (model) diterima PostgreSQL tetapi tidak cocok regex UUID versi/varian frontend. Parser asli menolak **ID Mandor bukan UUID valid.** / **ID model QC bukan UUID valid.** Source `src/laundryQcModel.ts:123,149–153`, SHA256 `f217cd5a2be8dd42262063733b47626cee841bad75391271b402ed6add167ccb`. Hook `useLaundryQcWorkspace.ts:37–50` mengirim exception ke fallback `src/lib/clientError.ts:35–71`, sehingga respons200 tampak sebagai kegagalan koneksi.

Fixture baru:
- Model/mandor/produk dibuat melalui public initial-import CREATE/SAVE_FILE/VALIDATE/FINALIZE; UUIDv4 diverifikasi. Pola/Potongan melalui RPC publik. Kebijakan mandor melalui `public.erp_set_contractor_hpp_policy_v1`, bukan grant fungsi private.
- Hanya dalam salinan browser: satu produk seed dengan model a200… disisihkan melalui flag `is_portal_visible=false`. Seluruh row FG movement dibandingkan sebelum/sesudah flag dan tetap sama. Tidak menghapus transaksi, mengubah qty posted, atau mengganti UUID lama.
- Asosiasi model/ukuran serta ordinary work drafts dari recipe fixture dicatat terbuka. Browser memakai **pencarian UI asli dengan kode model baru** untuk membatasi transaksi; kontrol berlaku pada workspace dengan filter tersebut, bukan penerimaan seluruh data seed tanpa filter.
- Tidak mengubah source parser/DDL/SQL produk, tidak menulis ulang respons HTTP, dan tidak menambah EXECUTE privilege. Schema USAGE fixture dikembalikan sebelum aktor browser.
- Nama merek dibuat unik lewat SAVE_FILE supaya tidak bertabrakan antarfixture. Expected20/10 dan oracle tidak diubah.

W11 P3 UX tetap: bedakan respons data tidak valid dari kegagalan jaringan; pertahankan validasi dan write lock. W12 pertanyaan kualitas seed/kompatibilitas data tetap untuk writer pada drill/artifact yang diizinkan. **Audit ini tidak memeriksa hosted/legacy/production.** Keberhasilan kontrol baru menyelesaikan hambatan fixture untuk dua kasus, tidak membuktikan seluruh data produksi bebas UUID demikian.

## Riwayat tidak dilabel ulang

| Run / job | Status raw / alasan |
|---|---|
| 36101907250 /107966011162 | NOT_RUN/INCOMPLETE: path browser salah di workflow audit. |
| 36102303107 /107967209608 | 2CE CP6-05 +2INCOMPLETE Laundry/QC (diagnostik kontrol belum lengkap). |
| 36102938451 /107969167045 | 2INCOMPLETE: respons200 tetapi belum bisa dirender. |
| 36103599807 /107971184469 | 2INCOMPLETE: parser kandidat menetapkan kegagalan UUID fixture. |
| 36105734698 /107977705679 | 4INCOMPLETE: setup memanggil fungsi policy private yang EXECUTE-nya ditolak; seluruh setup rollback; browser users0. |
| 36106291785 /107979461548 | 1PASS+1CE Laundry;2INCOMPLETE QC karena nama merek helper sama. |
| 36106777202 /107980988537 | 1PASS+1CE QC; RUN_COMPLETE, tidak adaINCOMPLETE. |

Ledger per run di `out/gpt_recovery_run_<run>.json` (dua pertama) atau `out/gpt_unknown_run_<run>.json` (sisanya). Seluruh run selesai. Rev5/6 masing-masing2Authusers dibersihkan; counts[0,0,0,0] pulih, console0, browserDB0, clone0, primary_unchanged=true. Factory ordinary kosong bukan kasus bisnis PASS.

LOG SHA256 rev5 `c671cb4ee423900d2f4fb58679850ad756eda9d7b1eb463d584d32142bf99304`; rev6 `02e9cf2969ab5958d325bb969364b4e73148065fac8f4a94676c33b7dcb01707`. Hash lain dan JSON per-case tetap di ledger.

## Skenario yang dapat diulang

| Berkas | SHA256 |
|---|---|
| `audit/scenarios/recovery_round8/gpt_recovery_browser.mjs` | `015097817df43ea4719c827e919c5cb7ae5814a5d19444231e8b434e7f067d79` |
| `audit/scenarios/unknown_round8/gpt_unknown_fixture_rev5.py` | `401e32610062b8c737307d58603b89823669d38c33a3296354cc837e6a36f729` |
| `audit/scenarios/unknown_round8/gpt_unknown_browser_rev5.mjs` | `fb071a8cb557bdea113a3e3e2f4137d0e561a08c91956f35c4e1617ace4a5a42` |
| `audit/scenarios/unknown_round8/gpt_unknown_fixture_rev6.py` | `b85b0ddda85380f3afe59896c11e0685ef3b141506ac2fe79198a01b09322bce` |
| `audit/scenarios/unknown_round8/gpt_unknown_browser_rev6.mjs` | `77044ff34ecd361e8cf18cef24db3ed7a7bd0c83379f73a758d6580e569813bb` |

Manifest_rev3/4/5/6 dan oracle awal tetap utuh. Untuk rerun Laundry setelah perbaikan, pakai setup merek unik rev6 dengan pasangan kasus Laundry yang sama; simpan sebagai revisi baru sebelum dispatch. Jangan menyalin setup rev5 apa adanya ke beberapa scope yang berbagi DB lalu mengulangi benturan nama.

## LANGKAH BERIKUTNYA

Writer W10 memperbaiki envelope Pola/Role; W13 membuat unknown berbeda dari0; W11 memperjelas kategori error. Auditor review successor, rerun kasus yang terdampak beserta healthy/refetch controls, mempertahankan semua hasil lama. Tidak perlu run diagnostik tambahan pada kandidat yang sama. Tugas W8 sen, W7 integritas grup, W1/C6→D06, W9 marker, W2 integrasi oracle, dan cakupan ALL/izin/payroll/HPP yang belum diuji tetap terbuka.
