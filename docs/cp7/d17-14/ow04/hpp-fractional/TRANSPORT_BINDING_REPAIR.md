# Pengikatan ulang bukti Native58

Kandidat `3a667e938bb1485a0f4206483d107b6ac76e347d`, tree
`a48bb1ebed975ef297fdc41aec2f712d9aebc5b8`, benar-benar lulus58 Native pada
run39532484310/job119001397111. Receipt `../CI_3A667_NATIVE58_PASS.json`
menautkan58 batas pemulihan kasus,5 gerbang paket, artefak dan laporan/log
lengkap. Kegagalan produk761362 tetap disimpan dan tidak diganti labelnya.

HTTP8, race6 dan browser4 kandidat lama tetap bukti lama. QUALIFIED_CORE
sekarang menunjuk receipt Native58 sebenarnya; produk/installer/caller yang
berbeda dari tree/blobs kandidat tersebut tetap ditolak sebelum membuka DB.
Perubahan di direktori qualification boleh berjalan terpisah. Native58 tidak
dijalankan ulang oleh entry HTTP/browser; itu dinyatakan sebagai bukti reused.

Dua celah pemeriksa akhir ditemukan pemeriksa internal dengan menjalankan
fungsi asli terhadap berkas sintetis: status/count binding yang tidak cocok
dan hash deklarasi laporan yang salah masih diterima. Reproduksi pertama
disimpan dalam `TRANSPORT_FINAL_GATE_COUNTEREXAMPLES.json`. Pemeriksa akhir
kini menolak binding selain PASS44/58, mewajibkan seluruh binding+SHA yang sama
pada masing-masing laporan HTTP/race, dan membandingkan hash deklarasi asli.
Nama laporan generik `reused_native_binding` menggantikan nama khusus44.

Perintah kontrol sebelum CI transport baru:

```
python -B scripts/ow04-qualification/native_binding_recheck.py
python -B scripts/ow04-qualification/final_binding_recheck.py
ERP_REPO=. PYTHONPATH=scripts:scripts/ow04-qualification python -B -c \
 'import transport_probe as t; assert t.qualified_core()["native_case_count"] == 58'
```

Kontrol sintetis21+5 lulus; preflight membaca receipt runtime nyata yang sudah
diverifikasi dan lulus tanpa membuka DB. Tidak ada expected kasus HTTP8,
race6 atau browser4 yang diubah. Hasil CI transport/browser pada backend baru
masih diperlukan. Ini review internal writer, bukan penerimaan auditor.
OW04 serta backlog D17-14 tetap terbuka; `production_go:false`.
