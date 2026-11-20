# Global uji ffda5cfc untuk auditor

Produk `ffda5cfceb7ebc196656baa650dffd18dd425047`, tree `760f38cc80ee9ca15e62a86ba358dfd8e858d895`. Gunakan tanda `INSTALLED_AND_PRESERVED` di `writer-global-terminal-<run>` dan `COMMITTED` di `writer-global-catalogue-<run>/installed.json`. `preseal.json` sendiri belum membuktikan commit. Rekam ID run asal, SHA runner, fingerprint 25 kelompok dan SHA arsip dalam bukti independen.

Lingkungan dibangun dari delapan tree yang diperiksa terhadap sumber auditor. Pemasang menggunakan database `cp6_rollback` dari rantai SKU dan Global. Tiga fungsi S06 dipasang dari pendahulu yang tersertifikasi. Perubahan SQL kandidat diterapkan dalam transaksi Global sebelum segel akhir. Salinan fisik diambil dari cluster sesudah commit. Pada salinan terisolasi, pemasang mendaftarkan tiga jadwal ERP sebagai nonaktif dan memeriksa fingerprint Global sekali lagi. `pg_verifybackup` memeriksa manifest fisik. Berkas data dan konfigurasi Vault dienkripsi bersama. Tidak ada pengujian empat klausul bisnis dalam langkah pemasangan.

## Membuka lingkungan yang disimpan

Unduh `installed.json` dan `global-ffda.cp7` dari dua artefak pada run yang sama. Paket frontend tersedia di artefak `writer-global-auditor-ui-<run>`. Paket ini mengambil sumber aplikasi, dependensi terkunci dan konfigurasi Vite langsung dari tree kandidat. Cocokkan SHA-256 masing-masing ZIP dengan metadata GitHub Actions dan jalankan `unzip -t` sebelum ekstraksi. Ambil kunci sekali pakai dari handoff pribadi Writer A. Tetapkan `PYTHONPATH` ke direktori `qualification` di checkout runner.

```sh
python -m close11.resume --installed installed.json --checkpoint global-ffda.cp7 \
  --key /jalur-pribadi/CP7_GLOBAL_FFDA_AUDITOR_RECOVERY.pem \
  --network internal --container-file container.txt
```

Perintah memakai Docker dan Python 3 dengan paket `cryptography`. Ia memeriksa autentikasi arsip, SHA plaintext, manifest PostgreSQL dan sidik jari katalog yang dilaporkan oleh Global. Ia membuat volume data dan konfigurasi dari checkpoint yang sama. Jaringan Docker internal memungkinkan Auth, PostgREST dan browser uji terhubung melalui jaringan audit. Koneksi WhatsApp keluar tetap terisolasi. Untuk cabang pemulihan BR-T39, salin juga volume konfigurasi. `--socket-dir "$RUNNER_TEMP/pg-socket-auditor"` membuat soket lokal untuk klien Python dan layanan auditor pada runner yang sama. Pasang layanan audit di jaringan yang ditampilkan oleh `docker inspect` untuk kontainer tersebut. Jalankan perintah SQL dari kontainer dengan `docker exec -i -u postgres "$(cat container.txt)" psql -U supabase_admin -d cp6_rollback`.

## Memakai runner publik tanpa mempublikasikan kunci auditor

Auditor dapat membuka checkpoint pada satu job GitHub Actions publik miliknya di cabang `audit/` repo ini. Simpan kunci sementara job dengan mode 0600 di `RUNNER_TEMP`. Jalankan urutan berikut di job yang sama.

1. Unduh dua artefak run pemasangan, periksa SHA arsip dan CRC, lalu ekstrak. Checkout helper Writer A pada SHA yang diberikan dalam handoff.
2. Jalankan `python -m close11.audit_access challenge --installed installed.json --archive global-ffda.cp7 --request request.json --private "$RUNNER_TEMP/audit-receiver.pem"`. Publikasikan hanya `request.json` sebagai artefak GitHub.
3. Dari ruang kerja privat auditor, ambil `request.json`. Cocokkan ID dan SHA job terhadap GitHub Actions. Jalankan perintah di bawah. Untuk checkpoint yang diterbitkan tanpa `envelope_sha256`, sertakan `--source-archive global-ffda.cp7`. Kembalikan hanya `reply.json` kepada job yang sama. Berkas balasan terikat pada ID run, SHA commit, nonce dan kunci publik sementara.
4. Di job auditor, jalankan `python -m close11.resume --installed installed.json --checkpoint global-ffda.cp7 --receiver-key "$RUNNER_TEMP/audit-receiver.pem" --request request.json --reply reply.json --network internal --container-file container.txt`. Salin checkpoint hanya sekali. Jalankan **AUD-G01, AUD-G02, AUD-G14 dan BR-T39** pada lingkungan yang sudah dibuka, lalu simpan bukti masing-masing sebelum membersihkannya. Writer A tidak mengisi hasil atau putusan audit.

```sh
python -m close11.audit_access grant --installed installed.json --request request.json \
  --key /jalur-pribadi/CP7_GLOBAL_FFDA_AUDITOR_RECOVERY.pem \
  --audit-run "$AUDIT_RUN" --audit-head "$AUDIT_COMMIT" --reply reply.json
```

Untuk selesai, hapus kontainer dan kedua volume sementara sesuai nama yang dicetak helper. Jika memilih jaringan internal, lepaskan layanan audit kemudian hapus jaringan itu. GitHub menyimpan artefak asal selama 30 hari. `production_go=false`.

### Langkah GitHub Actions siap pakai

Sebelum empat langkah uji independen, panggil `Hanjay6688/-erp-garment-ux/qualification/close11/open@<SHA-runner>` dengan argumen `origin-run` dan `origin-runner`. Job memerlukan izin baca `actions` dan `contents`. Tiga outputnya adalah `container`, `socket` dan `application`. Pengujian dapat mengakses basis `cp6_rollback` pada soket tersebut dan menjalankan aplikasi dari direktori `application`. Job menunggu balasan auditor hingga 20 menit. Setelah memeriksa ID dan SHA job, terbitkan hasil `grant` di `qualification/astra-public/close11-key-grants/<ID-run-auditor>.json` pada cabang auditor `audit/astra-cp7-public-ffda`. Balasan hanya dapat dipakai satu job itu. Pertahankan kontainer sampai keempat uji dan pengarsipan hasil selesai.
