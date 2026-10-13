# Bukti Astra 7a0b4a90

Mulai dari [REPORT.md](REPORT.md) dan [WRITER_HANDOFF.md](WRITER_HANDOFF.md). [FINAL_CI_RECEIPT.json](FINAL_CI_RECEIPT.json) mencatat enam run Astra; semua selesai. Dua run merah asli tetap merah: kesalahan klasifikasi alat auditor dan counterexample backup. Koreksi klasifikasi memakai Original yang sama, bukan pengulangan transaksi.

[FINAL_ORIGINALS.tar.xz](FINAL_ORIGINALS.tar.xz) berisi **341 berkas / 280.760.601 byte sebelum kompresi**, termasuk seluruh JSON Original per job, pengamatan batas supplier lengkap, log gagal pertama, diagnosis CP6 lama, SARIF dan screenshot mandiri. Tidak ada JSON yang dipangkas untuk mengecilkan arsip. Traces/screenshot raw besar yang tidak dimasukkan tetap tersedia pada artefak run; indeks ZIP dan hash unduhannya ikut disimpan. Manifest tiap anggota: [ORIGINALS_MANIFEST.json](ORIGINALS_MANIFEST.json).

SHA-256 arsip: `d1a31774c60bf36671addfe96f51c02fc6af21ea7805d4eb07d4d741a4f4dcb1`.

Ekstraksi dari folder laporan:

```sh
tar -xJf FINAL_ORIGINALS.tar.xz
```

Verifikasi tanpa mengekstrak atau menulis file:

```python
import hashlib, json, tarfile
with tarfile.open('FINAL_ORIGINALS.tar.xz', 'r:xz') as archive:
    manifest = json.load(archive.extractfile('ORIGINALS_MANIFEST.json'))
    for row in manifest['files']:
        body = archive.extractfile(row['path']).read()
        assert len(body) == row['bytes']
        assert hashlib.sha256(body).hexdigest() == row['sha256'], row['path']
print('341 complete Originals verified')
```

`REGRESSION_RESULTS.json` adalah indeks turunan, bukan pengganti Original. Penghitung lokal sempat menolak bentuk dua laporan: source admission attention bernilai nol kredit keluarga, dan payroll mendeklarasikan inventaris per kelompok tanpa total agregat. Penghitung disesuaikan untuk mempertahankan inventaris tersebut, memeriksa setiap ID terencana, status, pemulihan, jumlah kasus, serta kebocoran sesi; tidak ada uji produk diulang untuk itu.

Fixture/oracle writer tetap disebut `WRITER_UNCHANGED` meskipun eksekusinya dijalankan Astra. Kasus mandiri dan kode workflow berada di folder ini dan `.github/workflows/audit-astra-retest-*.yml`. SHA kode uji yang benar untuk setiap run terdapat pada receipt; jangan memakai HEAD bergerak sebagai pengganti. Retest pada kandidat berikutnya harus membekukan SHA baru dan mengikat checkout serta receipt baru secara eksplisit, sambil mempertahankan hasil pertama ini.

PR44 bukan penerimaan independen Astra. Tambahan writer sampai `5e96cbcf` hanya mendapat pemeriksaan delta sumber yang dijelaskan di laporan, bukan PASS runtime baru. `production_go:false`.
