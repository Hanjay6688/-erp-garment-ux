# Writer checkpoint OW04 — Native44, Auth HTTP8 dan race/pemulihan6

Ini pemeriksaan internal writer, bukan audit independen eksternal. OW04 tetap
BELUM SELESAI; feature_complete:false, audit_complete:false,
production_go:false. Root adalah satu penulis/integrator; pembantu melakukan
counter terbatas tanpa mengedit produk bersama.

## Kandidat dan identitas bukti

| Lingkup | Kandidat | Bukti |
|---|---|---|
| Backend Native44 | ef98e6e65c13322bf08e6f704e511bdbb03a07a8 | run39489386389/job118858149684,44 PASS |
| HTTP8 + race6 baru, backend persis sama | 6f318261ab585ad7a8378d6041839dc1a549fa87 | run39497414236/job118885938105,8+6 PASS |
| Snapshot frontend parser terhadap keluaran Native44 lama | parser proposal tidak berubah | ui-wire-native44/RESULT.json,12 pasangan/72 assertion PASS; bukan browser/runtime baru |

Tree kandidat HTTP/race: d13e185c229cab3011ca4112decd4c9df80ba733.
Tree backend ef98:7f4b094916bd27c4b6f8a6978b6dacd570ff121a.
Backend directory tree07064b179f82e6827020074d0dc9707fbe5bd76e;
Native probe blobb82ad1f28fcb8b19db2a2892960151bba01df56c.
QUALIFIED_CORE.json menolak perubahan dependensi produk sebelum koneksi
database dan mengikat receipt44/hash yang sudah lulus. Native44 tidak
dijalankan ulang pada run HTTP/race; jangan menyebutnya58 kasus runtime baru.

Kedua kelompok baru memiliki tepat ID yang dideklarasikan sebelumnya,
pemulihan CP6/advisor lulus, tidak meninggalkan sesi/database kasus, dan
pembersihan Auth kembali ke semula. Kedua paket luar lulus kelima gerbang:
installed, primary_unchanged, backup_restore_drill, security_advisors,
writer_runtime. Kedua outcome langkah GitHub benar-benar success, bukan
conclusion yang dimask oleh continue-on-error.

Sumber bukti: CI_EF98_NATIVE44_PASS.json dan log lengkapnya;
CI_6F31_HTTP_RACE14_PASS.json dan CI_6F31_HTTP_RACE14_RUNTIME.log.gz.
Receipt terakhir mencatat14 keluaran kasus, ketiga ringkasan, identitas kedua
paket, kandidat, run/job dan SHA256 log mentah serta gzip. Log lengkap baru
356939 byte; gzip55197 byte. Raw SHA256:
1bd6e6b8f65c1c8d2ab2df64079edb713d51aa0737bdaf9e38b617f5207d0cdf.
Gzip SHA256:
80f9679997903541f69f323f4f0e8a7ca1f4498c9e4a271e9757bc0f5db870cc.

## Perubahan dan kontrak yang telah dibuktikan

Source-completion PAYMENT, PAYMENT_REVERSE dan RETURN_REVERSE ditempatkan
setelah pembaruan status header, HPP dan audit Native. Perhitungan E tetap
sebelum guard uang/status asli. Pernyataan Native, guard asli dan pemeriksaan
penutupan fakta akhir tetap dipertahankan. N10 mencakup OWNER dan UID manusia
kosong, pembayaran setelah retur, inverse PAID menjadi PARTIAL, GL netral
serta stok fisik10. Seluruh44 ID dan expected uang/tanggal tetap.

Native44 terdiri dari12 settlement awal CREDIT/REFUND,20 kontrol lama dan12
Native EMPTY. Ini membuktikan registrasi target kosong dan inverse yang
dideklarasikan, bukan semua keluarga terkoreksi atau pemakai kredit.
P tetap pembayaran/uang muka asli, U APPLY masuk, I pengakuan bertanda yang
dipertahankan; E=P+U−I. Riwayat pembayaran asli tidak ditulis ulang.

HTTP8 membuat pengguna Auth sungguhan, login password grant, memanggil RPC
publik lewat PostgREST, COMMIT nyata, kemudian memakai koneksi baru untuk
oracle uang/jurnal/pasangan tanggal/stok/HPP yang tidak diubah. Replay dan
penolakan membandingkan semua tabel privat, materialisasi, completion,
request/scope serta batas ERP/platform. Seluruh schema privat wajib ada;
schema yang hanya berisi fungsi boleh tidak memiliki tabel.

Kasus STAFF mengaktifkan role Legacy STAFF hanya di salinan uji, mempertahankan
identitas/flag sistem, dan memakai fine permissions OWNER yang asli tanpa
mengubah guard owner/admin Native. CREDIT quote pengguna yang sama wajib
berhasil terlebih dahulu; kedua panggilan REFUND kemudian ditolak dengan
pesan Native400/P0001 yang persis. Run akhir mencatat prior_active:false dan
explicitly_activated:true. Anonymous, digest rusak, reserved plan, payload
request berubah dan replay setelah keanggotaan dicabut juga ditolak atomik.

Race6 memakai fixture SQL terautentikasi, bukan Auth sungguhan. Hubungan
blocking holder/worker dibuktikan dengan PID yang persis, bukan waktu tunggu
semata. Cakupannya: request berbeda berebut satu settlement, UUID yang sama,
payload berubah, izin dicabut oleh sesi ketiga setelah worker menunggu FG,
rollback holder sesudah badan transaksi penuh, dan penghentian backend
holder yang diketahui pada database sekali pakai sebelum COMMIT. Worker
yang sah berakhir dengan satu receipt luar/dalam, angka/jurnal/stok/HPP
persis, pembayaran asli tetap, tanpa retur/cohort transaksi yang dibatalkan.

Request berbeda setelah cohort pertama masih ditolak sebagai keluarga belum
didukung; itu membuktikan penolakan atomik, bukan dukungan beberapa cohort.
Putus backend sebelum COMMIT bukan bukti pemulihan server penuh atau respons
HTTP sukses yang hilang sesudah COMMIT.

## Kegagalan awal dan counter internal

- 80b97175 Native44:42 PASS/2 INCOMPLETE. Penutupan fakta menolak header
  Native inverse yang belum diperbarui; urutan source hook dibetulkan.
  CI_80B9_FIRST_FAILURE dan SOURCE_COMPLETION_FAILURE_DISPOSITION.md tetap ada.
- f3437108, run39492199058/job118867983298: HTTP7 PASS/1 INCOMPLETE.
  Lookup STAFF yang menyaring active menghasilkan kosong; penulis semula
  salah menyimpulkan role tidak ada. Kasus berhenti sebelum login/refund STAFF.
- 2f6c28ec, run39494596197/job118876226645: HTTP7 PASS/1 INCOMPLETE,
  race6 SKIPPED. Role STAFF ternyata ada tetapi sengaja inactive pada Legacy.
  Perbaikan pertama hanya membuat role bila tidak ada, sehingga belum cukup.
  Kedua receipt/log lengkap dipertahankan. Fixture akhir mengaktifkan role
  pada salinan sekali pakai secara eksplisit; produk dan EXPECTED8 tidak berubah.
  HTTP_STAFF_FIXTURE_FAILURE_DISPOSITION.md mencatat koreksi diagnosis ini.
- Counter HTTP membetulkan expected reserved-field/role error sesuai guard
  asli, memperluas snapshot dari sembilan tabel ke semua tabel privat,
  membedakan keberadaan schema dan tabel, serta mengikat hash implementasi.
  Penilaian awal, sebelum/perbaikan dan hasil recheck tetap di http-check/.
- Counter race menemukan wrapper paket selalu menghapus cp6_rollback.
  Workflow menyimpan seluruh pohon bukti HTTP tanpa menimpa, clone AB baru
  lewat alat yang sudah diizinkan, lalu menjalankan race6. Kedua pohon bukti
  diunggah. Workflow dan reproduksi awal tetap di race-check/.
- Counter gerbang akhir menghasilkan dua false-green sintetis saat gerbang
  hanya memeriksa hasil dalam. Perbaikannya mewajibkan kedua outcome GitHub
  yang asli serta kelima gerbang kedua paket luar. Reproduksi dan kode awal
  tetap; final recheck dan24 kontrol sintetis (1 positif/23 negatif) lulus.
  Kontrol sintetis bukan bukti runtime/Auth/Native.
- Satu preflight awal memakai CWD keliru untuk import bukti lama; kegagalan
  lingkungan disimpan, diperbaiki lewat CWD tanpa koneksi DB/perubahan expected.

Tidak ada bantahan yang belum diselesaikan di lingkup source review akhir
yang terbatas tersebut. Kesepakatan pemeriksa internal bukan bukti bahwa
keseluruhan ERP benar; audit independen dan batas bukti tetap terpisah.

## Reproduksi

Gunakan workflow .github/workflows/cp7-ow04-http.yml dari kandidat6f318261
dengan lima checkout terkunci, versi Supabase/runtime, align AB, otoritas
rollback salinan dan guard yang sama. Entry menolak argumen/override otoritas.
Perintah dijalankan dari direktori writer yang dipersiapkan workflow:

```sh
python ../auditor/scripts/ow04-qualification/transport_probe.py
# Simpan seluruh bukti HTTP dan clone AB baru persis seperti workflow.
python ../auditor/scripts/ow04-qualification/race_probe.py
OW04_HTTP_STEP_OUTCOME=success OW04_RACE_STEP_OUTCOME=success \
  python ../auditor/scripts/ow04-qualification/qualification_gate.py \
  ../auditor/cp6-proof/t3
```

Variabel outcome di atas hanya reproduksi lokal setelah langkah sebenarnya
berhasil; di CI nilainya berasal dari steps.*.outcome, bukan diisi manual.
Workflow asli tetap sumber konfigurasi otoritatif. Raw log dapat dibaca dengan
gzip -dc; verifikasi hash terhadap receipt sebelum menafsirkan hasil.

Pemeriksaan wire tanpa database/jaringan:

```sh
node --experimental-strip-types docs/cp7/d17-14/ow04/ui-wire-native44/check.mjs
```

ui-parent-escrow/ menyimpan dua patch UI yang belum dipasang serta semua53
berkas proposal/hasil terdahulu secara lossless dan terikat hash. Empat
prasyarat root yang sudah untracked tetap dipertahankan, tidak ditimpa atau
diaktifkan. Enam sumber dasar masih cocok BASE_MANIFEST dan parent patch
lulus git apply --check. Hasil167 uji mocked DOM/type adalah bukti historis
dengan SDK stand-ins, bukan hasil browser/backend baru.

## Pekerjaan berikutnya dan batas penyerahan

Lanjut OW04 pada cabang astra/d17-14-20261020; kandidat auditor
55c885d1a12336905e433e05852b99be4d933f74 tetap beku. Masih perlu:
rekonsiliasi keluarga terkoreksi/beberapa cohort, APPLY/konsumsi refund serta
compound undo, komposisi installer produk atomik, UI aktif dan browser nyata,
respons sukses hilang/reload/writer-lock, batas akun/kas/tanggal tambahan yang
relevan, serta kualifikasi produk terpadu. UI dan pembaca E harus dipasang
bersama backend baru; jangan memasang frontend parsial ke installer lama.

Default installer/frontend produk belum berubah. Pelunasan efektif invoice
harus berarti E=P+U−I; tabel riwayat pembayaran tetap P. Fail-closed untuk
jalur yang belum didukung bukan pemenuhan seluruh syarat OW04.

Backlog owner tetap OPEN_WORK_D17_14_20261020.md:3 selesai,13 terbuka dari16.
Setelah OW04, urutannya OW05 mandor sesudah jahit; OW06 bayar supplier lintas
penerimaan; OW07 guard pool/HPP/WIP; OW08 koreksi uang/HPP; OW09 filter global;
OW10–14 perencanaan/model/keuangan skala pabrik/rumus bahan; OW16 status potong
tambahan D17-15; terakhir OW15 paket auditor. Nilai kebijakan tidak dikarang.

Tidak ada pengukuran browser/latensi baru. Bukti P19 lama dan audit Astra r5
tetap terikat kandidatnya sendiri. Tidak ada perubahan Enteng, kirim WhatsApp
nyata, Drive, merge main atau deploy produksi pada checkpoint ini.

