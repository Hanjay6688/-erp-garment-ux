# CP7 — tahap cangkang, 28 September 2026

Mandat owner dalam sesi 28 September 2026 membuka implementasi **cangkang terpisah**
sambil CP6 diselesaikan. Contoh sintetis diizinkan; data, aturan, dan kelulusan
yang belum ada tidak boleh dikarang. Ini delta atas gerbang urutan pada framework
v2, bukan pernyataan CP6 lulus dan bukan izin produksi.

## Dua gerbang

| Gerbang | Status | Bukti yang diperlukan |
|---|---|---|
| S0: cangkang terisolasi | Dimandatkan owner | Kontrak v2, contoh berlabel, batas tanpa transaksi, UI dan tes lokal |
| S1: integrasi operasional | BLOCKED_UPSTREAM | P00 accepted CP6 SHA/tree/schema, BD/BE/BF + release/last-check dan impact map; P01 final contract/permission; native snapshot/engine/command tests |

Source referensi UI: `da20943c25cafe887d96943428fc157f80839e24` pada
`claude/new-session-deapao`. Branch kerja: `cp7/empty-body-20260928`.
Accepted execution base tetap **null**. Main/branch CP6/DB tidak menjadi target tulis.
Writer CP6 boleh bergerak pada branch terpisah sesuai mandat paralel owner.
Perubahan tak terduga pada branch CP7 sendiri tetap menghentikan penulisan.

## Implementasi S0

- Route `/cp7-preview` hanya untuk runtime demo, default tanpa data. Route
  connected ditolak; kegagalan sumber tidak pernah memuat fixture otomatis.
- Kontrak `AnalysisResult v2` dan notification disalin dari paket yang dibaca,
  beserta schema/contoh/reasons dan hash sumber. Salinan ini proposed boundary,
  belum parser RPC produksi atau finalisasi P01.
- Stok/SKU exact size, prioritas produksi, panel Potongan, Business Report,
  Reminder dan Tanya AI memakai satu hasil. Presenter hanya memformat hasil;
  tidak ada mesin stok, forecast, HPP atau utang kedua di browser.
- Contoh numerik O02 asli: FG18, target48, gap dasar18, gap bersyarat8.
  Bahan/kapasitas/HPP tetap UNKNOWN sesuai contoh. Ini hasil oracle fixture,
  bukan kalkulasi terhadap CP6. Semua asumsi dan sumber tetap terbaca.
- State kosong, contoh, partial, stale, gagal baca, serta hak contoh
  ditampilkan berbeda. Hak contoh bukan bukti RLS/izin server.
- Tanya AI V1 berisi teks yang dapat disalin manual; sukses clipboard hanya
  setelah write berhasil. Buka ChatGPT dilakukan terpisah tanpa payload URL.
- WA hanya render lokal; tidak ada provider, nomor, jadwal aktif atau send.

## Tunda dengan alasan konkret

| Bagian | Yang disiapkan | Yang menunggu |
|---|---|---|
| P00–P02 | Port baca, state dan DTO | Accepted base, parser endpoint, snapshot coherent dan izin server |
| P03–P08 | Exact-size/membership display, sumber/alokasi dan alasan | Normalisasi lineage, histori range, demand/backtest, forecast, global allocation dan apply atomik |
| P09–P13 | Tempat status bahan/kapasitas/keuangan | Koneksi sales/retur/payment/payroll/HPP; invoice UNKNOWN/FREE/WAIVED dan lintas credit dari CP6 accepted |
| P14/P15 | Consumer, template lokal, detail sumber | Laporan publish/arsip immutable dan perbandingan periode dari server |
| P16 | Kategori produksi/aksesori/AR/AP, state unknown | Invoice allocation/due reader, episode persistent, policy threshold, ACK/snooze server |
| P17 | Prompt dari hasil contoh yang diproyeksikan | Authorized snapshot nyata, volume/truncation dan revocation server |
| P16 WA / CP7C | Notification contract dan preview lokal | Recipient/provider/schedule/outbox/worker/reconcile/delivery nyata |
| P18–P21 | Bukti S0 terbatas | Full-flow, scale, independent acceptance dan release |

Tidak ada parameter layanan, throughput, tarif, due date, size-membership,
policy atau identitas produk operasional yang disimpulkan dari contoh. Label
range hanya tampilan; exact size tidak dipecah dari string dan tidak digabung
menjadi lot baru. Readiness cangkang tidak menutup satu pun 84 case ERP dalam
framework. Bukti S0 dicatat terpisah dalam checkpoint.

## Pemilik path dan sambungan berikutnya

S0 memiliki `src/cp7/**`, `docs/cp7/**`, tes/workflow CP7 baru, serta dua sambungan
App (lazy route dan tautan demo). Tidak mengubah RPC allowlist, permission
catalog, runtime modes, migrations, lockfile, fixture CP6 atau test oracle CP6.
Panel Potongan diuji dalam pratinjau; pemasangan ke form connected ditunda
hingga source/context/dirty-form contracts disahkan.

Langkah integrasi: impor accepted receipts → diff dari reference SHA → finalkan
P01/parser/projection → ganti port unavailable dengan facade yang sah → uji
stock/HPP/AR/AP, exact size, permission, replay dan two-writer domain →
independent acceptance. Fixture adapter tetap hanya demo.
