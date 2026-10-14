# Audit Astra CP1–CP7 — IN PROGRESS

Kandidat `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`.
Paket owner `00b0eb24b2f014d102f0082111d13ee3be429cf2`; Panduan Pro Max dibaca utuh dan hash-nya cocok.
Cabang audit baru `audit/astra-cp1-7-0b7049d9-20261014`.

Gelombang native pertama menjalankan 31 suite dengan probe dan oracle kandidat. Rancangan oracle writer diberi label
tersendiri; ini belum menggantikan kasus kontrak independen Astra yang disiapkan berikutnya.
Regresi baseline CP3–CP5 dan sambungan CP1–CP7 mendapat gelombang serta manifest sendiri sebelum dijalankan.
Kasus helper P11, prefreeze, K3 dan supplier-create pada kandidat yang sama sudah memiliki bukti Astra terkunci
di `57ac8aab`; sumber dan batas buktinya dicocokkan dan hitungannya tidak ditambahkan sebagai eksekusi baru.

Adaptasi harness yang dinyatakan sejak awal: pengulangan grup otomatis saat pergantian hari dinonaktifkan untuk
mematuhi Pro Max §1.9. Guard tanggal, expected, dan status pertama tetap asli. Kegagalan tidak dicari ulang supaya hijau.
CP1/CP2 historis, data cutover asli, shadow run dan baseline hosted terbaru tidak diklaim telah diverifikasi.
Alat CP7C tetap di luar cakupan. `audit_complete:false`, `production_go:false`.

Laporan Fable dari putaran CP1–CP7 ini belum dibaca. Yang boleh dibaca hanya laporan lama pada commit yang disebut handoff.
