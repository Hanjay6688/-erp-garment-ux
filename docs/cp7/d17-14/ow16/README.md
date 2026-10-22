# OW16 — status hasil potong otomatis

23 Oktober2026 WIB. **Implementasi tersedia di cabang produksi; belum ditutup sebagai selesai.**
Status keseluruhan tetap5/16. Pemasang bawaan, kualifikasi Native/HTTP/browser dan pemulihan gabungan masih perlu
diselesaikan. Tidak ada penulisan Enteng/hosted/produksi, WA atau cabang integrasi.

Update23 Oktober: kualifikasi writer Native/HTTP/browser/pemulihan sekarang **16/16 PASS** pada
`3f0e545cc6d6948ac5d0f1052bb55cc971ab530a`, run39832859589/job120013305810.
Native10, dua pengguna2, HTTP2, browser desktop/HP2; CP6/advisor dipulihkan. Receipt `3f0e545-pass.json` memuat
hash Original dan hasil browser. Kegagalan boot pertama0 kasus tetap disimpan. Pemasang bawaan/registrasi oleh A,
pengisian angka produksi oleh owner, penggabungan dan audit tetap terbuka. Bagian bukti implementasi awal di bawah
adalah catatan historis, digantikan hasil server ini untuk kandidat yang disebut; bukan klaim semua head berikutnya lulus.

`automatic-status.sql` menyediakan pembacaan otomatis setelah potong disahkan dan kebijakan pabrik yang hanya dapat
disimpan OWNER dengan hak kelola produk. Riwayat semua akun dibandingkan per material Native, pola/revisi snapshot,
dan set ukuran yang sama. Yang dinilai total PCS menurut kain yang benar-benar dipakai; bukan sisa potong hitungan,
hasil laundry, atau klaim penyebab selisih. Tanggal fisik sama memakai waktu pencatatan yang lebih awal sebagai
pembeda; kelompok yang dibuat kemudian tidak menjadi riwayat sebelumnya pada tanggal/jam fisik sama.

Rentang empiris memakai kuantil diskret pusat dari rasio PCS/kain, lalu dihitung ke jumlah kain potongan sekarang;
batas PCS dibulatkan ke dalam (ceil bawah, floor atas). Tidak ada interval integer yang layak berarti data belum lengkap.
Jumlah kelompok menghitung satu kejadian per jenis bahan, bukan satu baris per roll. Kebijakan cakupan/minimum riwayat
tidak mempunyai angka bawaan aktif. OWNER mengisi, meninjau dan menyimpan alasannya dalam aplikasi; nilai fixture
uji bukan keputusan atau konfigurasi produksi. Kebijakan baru tidak mengubah sejarah transaksi.

Keadaan berbeda tetap terlihat: belum disahkan/dibatalkan, aturan belum ditetapkan, dijeda, riwayat belum cukup,
data belum lengkap, wajar, lebih sedikit, atau lebih banyak. Status produksi berikutnya membaca tahap Native;
posting potong tidak dianggap selesai seluruh produksi. Tidak ada langkah capture/pemeriksaan manual untuk memperoleh
status awal; panel learning prospektif lama tetap eksperimen terpisah.

## Kontrak dan pengamanan

- `public.erp_cp7_get_cutting_status_v1(p_group uuid)` → `cp7.automatic-cutting-status.v1`.
- `public.erp_cp7_save_cutting_status_policy_v1(p_payload jsonb,p_request uuid)` dan lookup dengan argumen identik
  `public.erp_cp7_get_cutting_status_policy_request_v1` → `cp7.automatic-cutting-policy-result.v1`.
- Payload tertutup: expected_revision, state, coverage, min_groups, reason, explicit_review. Coverage dikirim sebagai
  pecahan desimal tepat, isian pengguna dalam persen; PCS/revisi/jumlah kelompok tetap string integer.
- Satu kebijakan pabrik, versi immutable; kunci request lalu kunci kebijakan, pemeriksaan hak baru setelah masing-masing
  tunggu dan saat replay/lookup. UUID sama berisi lain ditolak, versi lama ditolak. Lookup negatif menyegel UUID supaya
  balasan hilang tidak menyebabkan penulisan baru tanpa kepastian.
- Metadata privat RLS, izin baca hanya untuk principal pembaca internal; pengguna tidak mendapat akses tabel/schema
  privat. Definer privat access hanya mendelegasikan pemeriksaan identitas yang sama kepada principal konfigurasi.
  Tidak ada grant penulis bisnis ERP. Uji lokal mencakup tidak ada hak DML ERP, direct private access, ADMIN/anon/STAFF.
- UI membuang hasil lama saat dokumen, sumber atau hak berubah.401/403 menghentikan pembacaan otomatis sampai sesi baru
  atau percobaan eksplisit. Setiap UUID tertunda disimpan pada key sendiri: dua tab tidak menimpa catatan balasan hilang.

## Bukti saat commit implementasi pertama

- `local-first-failure.json` dipertahankan: principal pembaca mendapat SELECT tetapi policy RLS privat belum membolehkan
  pembacaan kebijakan. Ditambah satu policy SELECT hanya untuk `cp7_capture`; tidak membuka akses pengguna.
- `local-after.json`:11/11 PASS, SQL produk yang sebenarnya di fixture relasional terkontrol; identitas adalah adapter
  fixture, **belum** bukti transaksi Native/HTTP. Termasuk504 kelompok historis, dimensi pembanding, waktu fisik sama,
  bayangan masa depan, LOW/HIGH, kuantitas kain, replay, pembatalan lookup dan metadata immutable.
-34/34 unit/DOM PASS pada lima berkas terkait status, potongan/PO otomatis dan learning lama. Termasuk kirim kebijakan
  lewat form, balasan hilang, lookup UUID yang sama, respons terlambat dan hak dicabut. Ini belum browser nyata.
- TypeScript dan CSS ownership PASS. `npm run build` tertahan registri RPC: tiga entri status baru perlu integrator,
  dan tiga entri MandorCorrection sudah hilang pada baseline sebelum OW16. `SHARED_INTEGRATION.patch` berisi usulan
  penambahan nama yang tepat; penjaga tidak dilemahkan dan berkas bersama belum diubah oleh B.

Permintaan pemasangan/registrasi rinci ada di `../KOORDINASI.md`. Setelah penggabungan, uji sumber dan pasang/pulih
harus memakai kode yang sama dengan kode teruji; jangan menyebut status lokal ini sebagai production_go atau audit.
