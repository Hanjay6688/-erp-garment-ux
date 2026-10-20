# Checkpoint proposal writer setelah WA99

`proposals.tar.gz` menyimpan492 berkas sumber/usulan, uji, hasil, kegagalan
awal, bantahan dan patch UI. Seluruh isi dibaca ulang dan dicocokkan dengan
`MANIFEST.json`; digest arsip ada di `RECEIPT.json`. Ini arsip inert, bukan
perintah pemasangan. Folder kerja tiruan yang dapat dibentuk ulang dikecualikan;
patch lengkap, sumber asli, konfigurasi dan tanda terima tetap disimpan.

Sumber integrasi root yang dipakai kualifikasi ada di
`scripts/cp7_customer_credit/` dan `scripts/cp7_ow04_probe.py` pada commit ini.
Sumber aktif itu lebih baru daripada salinan usulan root di dalam arsip,
termasuk penyesuaian lokasi, canonical view PostgreSQL, serta pemeriksaan
declaration/config facade. Jangan menimpa versi repo dengan usulan arsip.

Paket parent UI ada di `ui-parent/ui-parent-integration.patch` dan prasyarat
empat modulnya. Hasil167 uji lokal dan TypeScript bukan bukti Native/browser
nyata. Belum diterapkan ke alur produk karena backend belum dikualifikasi.

Counter yang dipertahankan: tinjauan akun sama/hash berbeda, urutan hash refund,
fastpath yang melewati pemeriksaan kredit, UTC/Jakarta, dan canonical view.
Hipotesis batched input parent tidak menghasilkan kegagalan pada reproduksi
independen; jangan dilaporkan sebagai cacat yang diperbaiki.

Ikuti `../NATIVE_QUALIFICATION_LIMITS.md` dan declaration32 kasus. Registrasi
EMPTY Native langsung serta rekonsiliasi koreksi tetap terbuka. Tidak ada
klaim `feature_complete`, audit independen, pemasangan atau izin produksi.
