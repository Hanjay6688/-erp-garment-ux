# Pemeriksaan singkat kalender BF asli

Workflow `cp75-bf-calendar.yml` membuka satu salinan BF dari run Astra `44800849536` pada klaster tanpa jaringan. Di dalam transaksi baca-saja, PostgreSQL mengembalikan waktu mulai UTC, semua tabel anak `realtime.messages`, batas setiap partisi dan tabel harian yang terlepas. Berkas `bf-calendar.json` menyandingkan hasilnya dengan lima tanggal menurut proses pemulihan dan lima tanggal menurut waktu pemasangan sumber. Hari sumber berasal dari langkah menyalakan database pada job `136512294676`.

## Akses Astra

Pakai `request.json` dari artefak `cp75-request-<run>`. Cocokkan ID run serta SHA commit dengan halaman Actions. Dengan pemeriksa `qualification/cp75-original-access/access.py` pada commit itu, jalankan perintah pemulihan biasa dengan tambahan `--clean-only`. Terbitkan respons terbungkus ke cabang `writer-a/cp75-baseline-public` pada `qualification/cp75-grants/<run>.json`. Respons terikat pada penerima sekali pakai run itu dan hanya membuka BF. Arsip Global historis sudah memiliki bukti pemulihan di run `44867955170`.

## Hasil untuk pemasang

Artefak `cp75-original-bf-calendar-<run>` menyimpan tanda terima pembukaan, waktu startup sumber dan hasil SQL. Hasil SQL ikut disimpan jika kalender berbeda dari yang diperkirakan. Pemeriksaan ini tidak membukukan transaksi ERP. Putusan CP7.5 berada di Astra. `production_go=false`.

## Kandidat pemasang untuk uji ulang

Pada pemulihan BF, pemasang membaca hasil SQL dari klaster yang baru dibuka dan mencocokkan sumbernya dengan arsip BF yang disahkan Astra. Pemasang menerima hari sumber hanya apabila nama kelima tabel, batas harian, hubungan ke induk, dan asal arsip cocok. Perbandingan 25 kelompok katalog, indeks, izin, serta pemeriksaan kredit bawaan tetap berjalan. Pemasangan baru menggunakan tanggal mulai PostgreSQL pada instalasi tersebut.

Workflow jalur asli memulai pemeriksaan kalender sebelum pemasangan. Bila kalender cocok, workflow membaca ulang bukti upgrade asli dari run `44867955170`, memeriksa sidik artefak serta sumber skenario, kemudian menjalankan pemasangan bersih dan dua pemulihan. Run kontrol singkat menggunakan katalog SKU yang disegel, PostgreSQL sintetis terpisah dan bukti pemulihan historis Astra.

Produk yang diperiksa tetap `48858590`. Paket ini merupakan calon perbaikan alat pemasangan. Putusan CP7.5 dicatat oleh Astra sesudah jalur asli selesai.
