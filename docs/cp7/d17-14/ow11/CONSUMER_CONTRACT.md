# Private consumer prototype

Lima fungsi privat, tanpa RPC, table baru, penggantian fungsi existing atau installer.
Tidak terhubung pada layar/forecast. Sumber dependency dan dua SQL dipin dalam
MANIFEST; sumber qualified lama tidak diedit.

- capture memakai source_at existing pada captured_at; baris pilihan immutable,
  termasuk CLEAR, tidak memuat clock penangkapan baru yang bergerak.
- prepare menuntut semua produk, semua histori dan semua pilihan pada capture yang
  sama; tanggal query tertutup, scope/duplikasi/recorded clock diperiksa.
- resolve memakai total PCS AVAILABLE dan jumlah hari pada query baru. Bukti lama
  adalah identitas asumsi, bukan total penjualan untuk dipakai selamanya. Skala
  positif eksplisit; ukuran/versi produk/profil berubah atau histori kurang gagal
  tertutup. UTC timestamp source_at +00:00 diterima melalui normalisasi suffix ke Z
  tanpa mengubah nilai sumber atau memotong mikrodetik.
- baseline_rows berasal dari baseline qualified yang dipin, tetap memakai
  cp7_demand.estimate dan cp7_baseline.target existing. Manual dan own cukup tetap
  prioritas. Tanpa pilihan, hasil JSON sama persis pada fixture yang sama.
- Numerator exact total*scale dan denominator hari dijaga sampai ceil terakhir.
  Statistik memakai stddev_samp sumber yang sama*scale, minimum14 existing; buffer
  hanya satu. Ref deduplicated, batas1000 tidak dipotong. Alasan1000 karakter
  disimpan utuh di provenance; input kernel menunjuk choice UUID.

Uji lokal actual SQL20 kasus PASS: prioritas, parity JSON, pembanding di luar chunk,
current query mengganti total999 pada bukti lama, zero AVAILABLE, UNKNOWN/stockout,
CLEAR dan recorded clock, perubahan produk/profil, PCS di atas integer aman JS,
statistical oracle Decimal80 digit, metadata keliru, batas refs dan2000 produk
terkendali dengan pembanding di posisi terakhir. Ini bukan Native capture2000,
Auth, installer/inverse22, SLA, fullAchain, penerimaan OW11 atau production_go.

Dua kegagalan lokal dipertahankan: format recorded UTC dari source_at dan operator
JSONB concat/arrow tanpa kurung yang menghasilkan refs kosong. Oracle diperbaiki
menuntut refusal spesifik sehingga kegagalan validator lain tidak dihitung lulus.

Penyambungan berikut mengikuti CONSUMER_INTEGRATION_MAP.md: full source/engine
fingerprints, seluruh history sebelum baseline lintas chunk, direct/staged/bounded/
reorder memakai satu adapter, dan choice writer memeriksa tepat delta tulisannya
sendiri pada pemeriksaan source kedua. Semua itu masih OPEN. Model kompleks tetap
memerlukan kebijakan aktivasi berversi dan backtest yang sah.
