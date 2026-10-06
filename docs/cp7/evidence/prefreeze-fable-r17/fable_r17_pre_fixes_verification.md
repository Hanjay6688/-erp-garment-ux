# Fable — Putaran 17 (PRA_PEMBEKUAN): verifikasi perbaikan PRE-02/03/04 pada `cp7/integration` ac714a5b

Tanggal: 2026-10-06. Head yang diuji: `ac714a5b8d371f3adecaf53ba7c9b7643ce5046d` (merge perbaikan Claude 92f30e42 + d82fa583; GPT e76bf721/56c75586). Runtime auditor dan workflow T3 identik dengan 095b33b0. Produk berubah vs 095b33b0 hanya `src/LaundryBdPanel.tsx` (+10: setiap hasil BD pasti menyegarkan bacaan Laundry) + satu uji DOM baru; `supabase/` tidak berubah.

## Tinjauan sumber perbaikan (INDEPENDENT_SOURCE_REVIEW)
| Commit | Isi | Penilaian |
|---|---|---|
| 92f30e42 (tests only) | `cp6_au_browser_ui.mjs`: assertion "field merek disabled" → "tidak ada field merek yang bisa diedit **dan** tidak ada tombol Sahkan yang aktif, sampai Reconcile selesai, termasuk setelah reload"; uji dulu memastikan keduanya ada & aktif (count 1) sebelum menuntut nol | **setara/lebih ketat**, bukan pelonggaran; catatan UX: CP7 menyembunyikan field alih-alih menonaktifkan (keputusan layar, bukan angka) |
| 92f30e42 / d82fa583 (tests only) | `cp6_be_browser.mjs`: selector ke form "Cari BS atau claim" + "Cari kasus"; langkah reverse mengikuti layar baru "Periksa pembatalan hasil" → review menyebut nomor & "2 Good dan 2 BS" → "Sahkan" | assertion qty=0 dan REVERSED tetap, **ditambah** pemeriksaan isi review; kegagalan pertama disimpan |
| 56c75586 (produk, GPT) | `LaundryBdPanel.tsx` reload menyegarkan Laundry setelah hasil BD pasti | menjelaskan PRE-02; tidak menyentuh writer Native |

## Run ulang auditor (INDEPENDENT_NATIVE_RERUN)
| Run | Suite | Hasil | Sebelumnya (r16) |
|---|---|---|---|
| 37455461404 | `cp6_be_modes.py` + `cp6_be_browser.mjs` | **17/17 PASS** | 15 + 2 INCOMPLETE |
| 37455472929 | `cp6_bd_modes.py` + `cp6_bd_browser.mjs` | **20/20 PASS** (LAU_T36 PASS) | 19 + 1 INCOMPLETE |
| 37455505705 | T3 paket 30 berkas + browser | install/advisor/restore/pins PASS; **AT flow 10/10 PASS**; browser 27 PASS + **4 INCOMPLETE** (`READINESS_BROWSER:*FINANCE_NOTE` ×2 = PRE-01; `BF_BROWSER:SALES_MANUAL_13_*` ×2 = PRE-05) | 23 + 8 |

Angka penulis (AT 10/10, skenario 17/17, REDYE PASS) **cocok** dengan bacaan saya.

## Disposisi
| ID | Status | Dasar |
|---|---|---|
| PRE-02 | **CLOSED** | LAU_T36 + FREE/WAIVED (BD_REV_BROWSER) PASS di modes BD dan T3 browser |
| PRE-03 | **CLOSED** | AT flow 10/10; assertion pengganti dinilai setara/lebih ketat |
| PRE-04 | **CLOSED** | BE 17/17; REDYE/REWORK PASS di T3 browser |
| PRE-01 | OPEN (GPT) | 2 alert di Keuangan masih; teks alert masih belum tertangkap |
| PRE-05 | OPEN (GPT) | uji halaman simulasi penjualan belum di-retire |
| PRE-06, PRE-07 | OPEN (GPT) | belum ada perubahan di head ini |

Catatan asal-bukti: PRE-03/04 ditulis Claude (penulis), diverifikasi Fable lewat run auditor; Fable tidak menulis kode apa pun untuk item ini.
