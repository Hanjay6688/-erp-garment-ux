# BF: skenario tarif yang berlaku

Paket uji FREE lama menaruh tarif laundry di `settings.laundry_rates` milik SKU. Itu sudah tidak sesuai kontrak Native saat ini. Tarif berasal dari **vendor, proses/paket/komponen**, dan versi tarif yang berlaku saat kiriman dicatat. SKU tetap membawa array `laundry_rates: []`; menulis override tarif SKU melalui fasad harus ditolak.

| Entrypoint lama yang dipertahankan namanya | Perilaku setelah diperbaiki |
|---|---|
| `scripts/cp6_bf_free_probe.py` | Membuat tarif vendor melalui `SAVE_COMPONENT_RATE`, memeriksa FREE/WAIVED/UNKNOWN/KNOWN, sembilan penolakan atomik dan 16 PCS fisik dengan HPP yang dihitung terpisah |
| `scripts/cp6_bf_free_modes.py` | Memakai skenario vendor di atas serta regresi/race Native saat ini; Auth HTTP memakai role GUDANG yang tersedia untuk penolakan akses |
| `scripts/cp6_bf_free_browser_fixture.py` | Menyiapkan tarif vendor Native pada database browser sekali pakai, tanpa tarif pada SKU |
| `scripts/cp6_bf_free_browser.mjs` | Memastikan form SKU tidak menawarkan tarif laundry, lalu menyimpan dan memuat ulang FREE/WAIVED pada halaman harga vendor |
| `scripts/cp6_bf_vendor_probe.py` | Regresi yang sengaja menyuntikkan override SKU salah tetap merupakan uji penolakan/ketahanan data, bukan contoh pengaturan yang boleh dipakai |

FREE dan WAIVED bernilai nol **secara eksplisit**. UNKNOWN tetap belum diketahui, bukan nol. Tarif KNOWN harus mengikuti aturan Native untuk nilai positif. Perubahan harga vendor atau harga jual SKU di masa depan tidak menulis ulang biaya kiriman yang sudah tercatat.

Contoh aritmetika uji: 16 PCS berukuran 5/8/3, biaya kain 100.00 dan kerja 127.19 per PCS, laundry FREE/WAIVED nol. Total HPP 2135.04, alokasi ukuran 667.20/1067.52/400.32, dan HPP per PCS 133.44. Angka itu fixture uji, bukan tarif vendor nyata.

Dokumen handoff, screenshot dan receipt lama tetap historis. Verdict lama tidak diubah menjadi PASS. Saat menilai aturan yang berlaku, gunakan source dan receipt baru pada `docs/cp6-readiness/`, beserta hash paket SQL yang tetap sama dengan CP6 diterima.
