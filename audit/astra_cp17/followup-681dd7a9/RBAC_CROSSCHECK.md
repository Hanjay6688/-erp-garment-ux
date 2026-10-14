# FABLE-012 — hak katalog, pemeriksaan peran, dan jangkauan API

**Disposisi: hak katalog terkonfirmasi; bypass pengguna biasa ditolak untuk dua fungsi yang diuji; jangkauan hosted belum diverifikasi.** Temuan tetap bahan pengerasan S2/permintaan bukti konfigurasi, bukan108 exploit terbukti atau otomatis S1 karena suatu schema diekspos.

## Original Fable dibaca

|Run / job|Artifact / SHA256|Hasil mentah|
|---|---|---|
|38571378585 /115877180312|11897878192 /`3eb22a20ba8e11d4d140b338c08eceef68660ce651ba58521ac6b2d4fcab8962`|2 PASS, 1 INCOMPLETE karena placeholder pola LIKE.|
|38572386253 /115880664623|11898249509 /`a6ebaeb2d3647bea26dd118dc1d70589b74f9c037968c016c9ca72ba6040c6de`|1 PASS untuk facade; run pertama tidak dihapus.|

Kedua ZIP asli dan log job lengkap disimpan dalam `preserved/`, dengan indeks/hash `FABLE_RUNTIME_ARCHIVES.json`. Source kasus pertama disimpan terpisah `fable_cp17_rbac.run1.py`, SHA256 `789fd3f50b5b3bd987c91727cf6ab67e167dc8bd1ead40be9cbf6db8dd035481`, sesuai Original pertama; source setelah perbaikan placeholder tidak dipakai untuk mengaku sebagai source run pertama.

Fable menghitung940 fungsi erp; authenticated punya EXECUTE 160,108 nama cocok regex “writer”. Angka 108 mencakup 28 fungsi berawalan `run_` pemeriksa integrity/security, satu fungsi trigger, dan helper `set_change_reason`. Jadi nama “writer-like” adalah klasifikasi awal, **bukan pembuktian108aksi perubahan bisnis yang dapat dieksploitasi**. Anon tidak punya USAGE erp;266 facade public berstatus SECURITY DEFINER dengan search_path terpasang dan tidak bisa EXECUTE oleh anon.

## Uji independen Astra, upaya pertama

- Kandidat/tree:`0b7049d9203bac52b47a4c89f3e0d75646067a8f` /`ce6aed0a0af920e8aa80248f3cabcd293688df18`.
- Control prapelaksanaan:`aa25e5ee06e58e218e8318bb0cf8d10e8eeff382`; manifest `../RBAC_FOLLOWUP_MANIFEST.json`; source cases SHA256 `ada0413cf02823ba1291871a61f3dc53d6d0786d8c1b72696c08820556bc0918`.
- Run38593568808, job115954406369, attempt 1; artifact 11908777291, SHA256 `fbd29da1bc65c6f2d0c08e530186130eadc3ac361fb28f0cacb301c1636c43ed`.
- Dua caseID di bawah didaftarkan sebelum operasi. Manifest di artifact cocok byte dengan manifest yang dikomit sebelum run.

|Kasus|Hasil dan batas|
|---|---|
|CP17-ASTRA-RBAC-01-CATALOG|PASS.940 fungsi erp,160authenticated EXECUTE,108writer-like/107non-trigger; nol tabel erp tanpa RLS;266 facade public tidak anon dan definer search_path terpasang. Membaca katalog, bukan menguji semua940 fungsi bisnis.|
|CP17-ASTRA-RBAC-02-ROLE-BOUNDARY|PASS. Role kustom dengan permission finance payroll approve/pay, OWNER nonaktif, dan subject tidak terdaftar masing-masing mencoba `erp.close_accounting_through` serta `erp.reopen_accounting_through`: keenamnya ditolak P0001 `OWNER or ADMIN access required`. Owner aktif benar-benar mengubah closed-through12 Okt→11 Okt dan membuat satu audit row, lalu rollback mengembalikan semua.|

Semua panggilan yang diuji memakai `current_user=session_user=authenticated` dan subject yang benar; tidak menjalankan aksi sebagai superuser. Admin hanya menyiapkan fixture identitas dan period-control pada database disposable, membaca observasi, dan mengembalikan transaksi. Tidak mengubah function body, ACL/grant, schema exposure atau guard produk.

Batas asli SQL ini tetap dicatat: **bukan login Auth/HTTP dan bukan browser/hosted**, hanya dua entry point native. `RBAC_OBSERVATION.json` memuat enam penolakan, satu kontrol positif, before/after dan sumber lengkap. Setiap case memiliki `full_boundary_restored:true`, `public_schema_unchanged:true`, nol advisory lock/session bocor. FULL sebelum/sesudah diverifikasi, CP6 dipulihkan, advisor gate lulus, primary unchanged dan auth_users_after0; database CI dibersihkan. Ada advisory lock fixture pada awal group; semua nol pada pemeriksaan akhir setiap kasus, bukan klaim awalnya kosong.

## Makna dan tindak lanjut

Bukti ini membantah penyederhanaan “authenticated EXECUTE berarti sembarang pengguna login bisa buka buku”. Ia **tidak membantah** fakta bahwa OWNER yang sah mempunyai jalur SQL native di luar facade, atau menutup semua fungsi/guard/context yang lain. Bila Data API tidak mengekspos erp, jalur SQL tersebut belum tentu tersedia untuk klien HTTP; konfigurasi hosted masih belum dibaca. Dokumentasi resmi mengenai exposed schemas dan hak SQL dicatat di `PRIMARY_REFERENCES.json`.

Penulis perlu mencatat konfigurasi schema API pada bukti rilis dan daftar entry point native yang memang diizinkan. Jika kontrak mengharuskan private erp tidak dipanggil pengguna, rapikan grant lewat forward change yang mempunyai inventaris caller/role/dependency dan uji Auth/HTTP positif-negatif. Jangan menerapkan blanket REVOKE seluruh fungsi/schema hanya dari hitungan nama; helper RLS/invoker/legacy yang sah juga perlu dinilai. Penerimaan perubahan nanti harus membuktikan direct call yang dilarang ditolak, public facade sah tetap berjalan, user nonaktif/revoked tetap ditahan dan rollback/ACL tepat.

## Q18 — label provenance bawaan runner

Envelope `ASTRA_CP17_OWN_INTEGRATION.json` masih membawa string generik runner `oracle_origin:ASTRA_FROZEN_CONTRACT_E800E016`. **Itu bukan commit sumber dua oracle baru ini.** Sumber dan oracle sebenarnya adalah file/hash/controlSHA aa25e5ee di atas, ditulis sesudah paparan FABLE-012 yang diizinkan owner. Manifest dan preexecution plan mencatat keadaan sebenarnya; tidak ada klaim penemuan blind atau oracle dari E800E016. Original tidak diubah; pembaca menggunakan pin sumber prapelaksanaan.
