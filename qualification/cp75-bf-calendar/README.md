# Pemeriksaan singkat kalender BF asli

Workflow `cp75-bf-calendar.yml` membuka satu salinan BF dari run Astra `44800849536` pada klaster tanpa jaringan. Di dalam transaksi baca-saja, PostgreSQL mengembalikan waktu mulai UTC, semua tabel anak `realtime.messages`, batas setiap partisi dan tabel harian yang terlepas. Berkas `bf-calendar.json` menyandingkan hasilnya dengan lima tanggal menurut proses pemulihan dan lima tanggal menurut waktu pemasangan sumber. Hari sumber berasal dari langkah menyalakan database pada job `136512294676`.

## Akses Astra

Pakai `request.json` dari artefak `cp75-request-<run>`. Cocokkan ID run serta SHA commit dengan halaman Actions. Dengan pemeriksa `qualification/cp75-original-access/access.py` pada commit itu, jalankan perintah pemulihan biasa dengan tambahan `--clean-only`. Terbitkan respons terbungkus ke cabang `writer-a/cp75-baseline-public` pada `qualification/cp75-grants/<run>.json`. Respons terikat pada penerima sekali pakai run itu dan hanya membuka BF. Arsip Global historis sudah memiliki bukti pemulihan di run `44867955170`.

## Hasil untuk pemasang

Artefak `cp75-original-bf-calendar-<run>` menyimpan tanda terima pembukaan, waktu startup sumber dan hasil SQL. Hasil SQL ikut disimpan jika kalender berbeda dari yang diperkirakan. Pemeriksaan ini tidak membukukan transaksi ERP. Putusan CP7.5 berada di Astra. `production_go=false`.
