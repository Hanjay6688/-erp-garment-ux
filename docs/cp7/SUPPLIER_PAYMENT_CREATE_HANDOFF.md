# Bayar supplier dari aplikasi — perintah owning baru

Status: kandidat penulis di cabang `claude/new-session-deapao`. Bukan audit independen, bukan pemasangan, bukan GO. `independent_acceptance=false`, `production_go=false`.

## Kenapa perlu

P18 siklus penuh (`p18/P18_FULL_CYCLE.md`) menemukan bahwa CP7 hanya bisa melihat, membetulkan, dan membatalkan pembayaran supplier. Mencatat pembayaran baru tidak bisa. Akibatnya hutang bahan tidak pernah bisa dilunasi dari ERP, sehingga hutang dan kas pasti salah. Pembayaran vendor laundry (BD) dan upah mandor (CP7 payroll) sudah punya penulis aplikasi, jadi celah ini hanya untuk supplier bahan.

## Desain

| Bagian | Isi |
|---|---|
| SQL | `scripts/cp7-src/invoices/payment-create.sql`. Dipasang lewat bundel P09 (`cp7_procurement_bundle.py`), sesudah `payment-correction.sql`. Skema privat `cp7_supplier_payment_create` hanya berisi `requests` dan `context`, keduanya RLS + kebijakan `false`. |
| RPC publik | `erp_cp7_get_supplier_payment_create_v1(p_query)` untuk ruang kerja (sisa hutang Native, token tinjauan, rekening aktif 25 per halaman) dan `erp_cp7_create_supplier_payment_v1(p_payload,p_request)` untuk perintah. Keduanya hanya bisa dipanggil `authenticated`. |
| Hak | Sama dengan membetulkan atau membatalkan pembayaran: OWNER/ADMIN dengan `finance.ap.pay`, ditambah `warehouse.procurement.view` dan `finance.ap.view`. Hak dicek tiga kali: sebelum kunci, sesudah kunci, dan sesudah posting. Bila hak berubah di tengah, perintah ditolak. |
| Token tinjauan | MD5 atas baris penerimaan, jawaban hutang Native (`cp7_invoice.payment_ap`), dan semua baris pembayaran penerimaan itu, dalam zona UTC. Bila sejak ditinjau ada pembayaran, pembatalan, kredit, atau perubahan penerimaan, perintah ditolak `CP7_SUPPLIER_PAYMENT_STALE_REVIEW`. Dua tab tidak bisa membayar dua kali dari tinjauan yang sama. |
| Penulisan | Baris DRAFT, lalu Native `erp.post_supplier_payment` yang tidak diubah. Native tetap satu-satunya penentu kapasitas hutang, akun, dan jurnal (Dr AP_SUPPLIER, Cr akun kas). Peran App tidak diberi hak DML ERP. Penulisnya fungsi definer milik `postgres` yang sempit. |
| Tolakan tambahan | Nominal di atas sisa hutang (`EXCEEDS_REMAINING`), tanggal di masa depan (`DATE_FUTURE`), tanggal sebelum barang datang (`BEFORE_RECEIPT`; uang muka adalah dokumen lain), rekening tidak aktif, penerimaan yang tidak ada atau sudah lunas (`NOTHING_PAYABLE`), dan isian yang tidak lengkap atau berlebih. |
| Idempoten | Satu `(actor, request UUID)` memberi satu hasil. Payload berbeda dengan UUID yang sama ditolak `CP7_SUPPLIER_PAYMENT_REQUEST_CHANGED`. |
| UI | Tombol "Bayar supplier …" di panel Pembayaran supplier (halaman Pembelian & Penerimaan). Formulir berisi nominal, waktu WIB, rekening (bisa dicari), keterangan, dan centang pemeriksaan. Sisa hutang sesudah bayar tampil sebelum disahkan. Bila balasan hilang sesudah commit, envelope yang sama dipulihkan sesudah reload lewat "Periksa status …". |

## Uji yang dinyatakan

Suite Native `CP7 Supplier Payment Create` (workflow `claude-supplier-payment-create.yml`) berisi 10 kasus.

**Native (4):**
- **Bayar persis:**
  - bayar 400 lalu 600 dari hutang 1.000;
  - jurnal tepat;
  - kas −400 lalu −1.000;
  - status PAID;
  - pengulangan UUID tanpa efek kedua;
  - payload berubah ditolak;
  - token basi ditolak;
  - hutang lunas ditolak.
- **Tolakan tanpa efek:** sembilan tolakan dengan pembayaran, jurnal, request, kas, dan stok/HPP tidak berubah.
- **Hak terkini:**
  - ADMIN tanpa hak bayar bisa membaca tetapi tidak bisa membayar;
  - JWT `service_role` ditolak;
  - fungsi privat tidak bisa dieksekusi;
  - tulis langsung ke tabel ditolak;
  - ADMIN dengan hak bayar berhasil.
- **Batas privat:** konteks kosong sesudah commit, dan tidak ada hak skema privat atau DML ERP untuk role App.

**Race nyata (3):**
- UUID sama dari dua sesi menghasilkan satu pembayaran.
- Dua request baru dengan tinjauan yang sama: satu berhasil, yang lain `STALE_REVIEW`.
- Tunggu kunci nyata, lalu hak ADMIN dicabut: tolak sebelum ada efek.

**Auth/HTTP nyata (1):** ruang kerja, bayar, replay identik, anonim ditolak, lalu hak dicabut sehingga replay mendapat 403.

**Browser (2):**
- Desktop: OWNER membayar 250 dari 1.000, balasan hilang sesudah commit, reload, lalu UUID yang sama dipulihkan.
- Mobile: alur biasa.

Kedua browser memastikan sisa hutang 750, kas −250, dan catatan tersimpan, serta tidak ada geser horizontal.

**Shell:**
- 6 kontrol DOM baru di `src/SupplierPaymentCreatePanel.dom.test.tsx`;
- 13 kontrol panel lama tetap lulus;
- `check:source` dan `check:access` lulus dengan 2 batas RPC baru;
- `tsc -b` bersih.

**P18:** `cp7_p18_full_cycle_cases.py` kini membayar supplier lewat perintah ini. Hasil run pertama yang memakai posting Native tetap tercatat.

## Hasil (dibaca dari log job CI asli; LOCAL_PG16_DEV tidak dihitung)

| Sumber | Run / job | Hasil |
|---|---|---|
| 4042235f | 37490924137 / 112363127748 | 7 PASS, 1 INCOMPLETE (sub-kontrol baru `CURRENT_ACCESS` salah anggapan, lihat di bawah). Kegagalan pertama disimpan di `evidence/supplier-payment-create/first-4042235f/`. |
| f999b502 | 37491709756 / 112365828821 | 9 PASS, 1 INCOMPLETE (sub-kontrol yang sama). Browser desktop PASS (balasan hilang sesudah commit → reload → UUID sama) dan browser mobile PASS; console 0. Disimpan di `browser-f999b502/`. |
| **917ff2b7** | **37492084385 / 112367128931** | **10/10 PASS**: Native 4, race 3, HTTP 1, browser 2. `cp6_restored=true`, `advisor_gate=true`. Disimpan di `qualified-917ff2b7/`. |

Shell di 4042235f (run 37490924114) lulus, termasuk kontrol DOM baru. Build UX dan CodeQL juga lulus.

**Kenapa run pertama INCOMPLETE.** Sub-kontrol baru menganggap role `authenticated` tidak bisa INSERT ke `erp.supplier_payments`. Di klon setara hosted, INSERT itu bisa, karena G-01 mempertahankan USAGE `erp` untuk `authenticated`. Sub-kontrol itu sekarang hanya mencatat pengamatan di dalam savepoint yang di-rollback. Kontrol perintah baru tidak dilonggarkan.

## Temuan bawaan hosted (perlu keputusan GPT/owner)

Pengamatan di 917ff2b7, dengan aktor ADMIN tanpa `finance.ap.pay`:
- INSERT DRAFT langsung ke `erp.supplier_payments`: **ALLOWED**.
- Native `erp.post_supplier_payment` atas baris itu: **POSTED**. Fungsi ini bisa dieksekusi `authenticated`, dan pengamannya `require_internal` hanya memeriksa peran OWNER/ADMIN/STAFF.

Jalur ini tidak bisa dicapai dari aplikasi, karena PostgREST hanya membuka skema `public`. Jalur ini baru bisa dipakai dengan koneksi database langsung sebagai `authenticated`, atau bila skema `erp` kelak dibuka ke API.

Penutupnya ada dua kemungkinan:
- mencabut INSERT/EXECUTE dari `authenticated` pada objek Native ini;
- menambah pemeriksaan `finance.ap.pay` di Native.

Keduanya mengubah Native atau ACL hosted, jadi tidak dilakukan writer tanpa keputusan.

## Batasan

- Belum ada pembayaran gabungan banyak penerimaan dalam satu transfer. Satu pembayaran berlaku untuk satu penerimaan.
- Belum ada referensi bank terpisah dari keterangan.
- Kas boleh minus karena Native tidak memeriksa saldo kas. Ini kebijakan owner yang belum diputuskan dan tidak dikarang.
- Uang muka sebelum barang datang tetap lewat alur uang muka yang ada.
