# Full owning transport — sedang disiapkan, belum diterima runtime

Native bb3e4f64 lulus73/73,113 UI/DOM dan build. Bukti asli lengkap pada
docs/cp7/d17-14/ow04/dependency-bb3e4f64-native73-pass/.
Native diulang pada73 hanya karena readonly reader baru; selanjutnya Native73
dipakai ulang dengan tree/probe/full-installer, receipt/declaration dan64
retained case IDs yang diikat persis. Tidak mengubah oracle lama.

Commit persiapan ini menghubungkan HTTP/race/browser ke owning installer
produk penuh melalui full_backend.py, termasuk verifikasi dan pengaman
rollback sebelum dipakai. HTTP menjadi8 initial+6 source+4 readonly=18.
Races tetap6 retained+2 source. Browser masih4 pada titik ini; case kelima
untuk dokumen REFUND dan manifest UI18 file belum dipasang.

qualified_core mempertahankan kontrol historis44/58/63 dan menambah73;
entry runtime penuh mewajibkan73 sebelum membuka koneksi.
42 kontrol Native binding (28 lama+14 baru) serta final gate yang mendukung
63/HTTP14 historis dan73/HTTP18 baru disiapkan. Counterexample final gate
50 (35 lama+15 baru). Semuanya masih perlu CI pada commit transport aktual;
hasil sintetis tidak menjadi proof Native/HTTP/browser.

Langkah berikut:
1. Lengkapi browser5, ACTIVE_UI_SOURCE18, browser probe expectation/hash.
2. Aktifkan workflow HTTP/browser hanya pada branch feature ini, perbarui
   preflight73/18 dan emit laporan JSON asli gzip seperti Native73.
3. Jalankan preflight/pure controls sebelum DB rebuild; jangan melemahkan
   predicate bila ada kegagalan. Pertahankan kegagalan pertama.
4. Tunggu HTTP18/race8/browser5, full owning restore/advisor/package gates,
   actual Auth cleanup dan clean UI binding. Baru integrasikan writer branch.

Executor lokal masih environment_offline409; source diselamatkan dan
pekerjaan diteruskan via GitHub API/CI. Tidak memakai subagent.
production_go=false; feature_complete=false; audit_complete=false.
