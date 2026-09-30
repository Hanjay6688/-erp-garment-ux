# Paket writer analyzer

Mulai dari `docs/cp7/f04/YIELD_ANALYZER_HANDOFF.md` pada repo atau salinan di ZIP. Source teruji `ddfb9d7a030457d712c666e3b6d5517a77fa3671`, PR #38, stacked pada PR #37. ZIP adalah snapshot handoff/sumber patch/bukti; bukan instalasi ERP mandiri.

F04 memiliki satu mesin/kontrak; F05 memanggil dan menampilkan. Lebar kosong tetap sah. Semua data uji sintetis; reader asli, model terkalibrasi dan runtime cutting belum terhubung.

`SOURCE_MANIFEST.json` mengikat setiap berkas yang diuji ke source. Commit lokal tes berbeda dari commit GitHub hanya pada metadata commit, dengan git tree identik dan SHA256 setiap source telah dicocokkan. Receipt asli tetap utuh. `SHA256SUMS.txt` mengikat isi snapshot ZIP; `PACKAGE_SHA256.txt` mengikat arsip itu sendiri.
