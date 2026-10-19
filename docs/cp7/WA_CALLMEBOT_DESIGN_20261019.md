# Desain: pengingat ERP ke WhatsApp owner lewat CallMeBot (D17-3, D17-4)

Status: **desain**. Belum dibuat, belum dipasang.

Keputusan owner (19 Okt 2026), dikutip persis:
- D17-3: "yaudah desain callmebot buat gw"
- D17-4: "gw maunya tiap kena safety stock dll auto kirim terus, yg sehari 2kali itu juga mau kan ringkasan"

## Untuk owner (ringkas)

Ada dua jenis pesan ke WhatsApp Bos.

**1. Pesan langsung, tiap kali kena.** Aplikasi memeriksa tiap 5 menit. Begitu sesuatu baru kena, pesan langsung
dikirim, tanpa ada yang menekan tombol. Contoh:

```
⚠ ERP Enteng · 20 Okt 10.35
Stok kain di bawah minimum: Katun Combed 30s Hitam
Sisa 42 kg, minimum 60 kg
Buka ERP > Bahan & Roll
```

Yang dianggap "kena" (masing-masing bisa dinyalakan atau dimatikan di aplikasi):

| Pemicu | Dari mana |
|---|---|
| Stok kain di bawah stok minimum | Stok minimum yang diisi di data Kain (sudah dipakai di Ringkasan Gudang) |
| Stok barang jadi / bahan sampai titik pesan ulang | Kebijakan stok yang sudah diatur per barang |
| Kain atau aksesori kurang untuk PO | Hasil analisis produksi terakhir |
| Target produksi kurang | Hasil analisis produksi terakhir |
| Tagihan supplier jatuh tempo | Data utang langsung |
| Piutang pelanggan jatuh tempo | Data piutang langsung |

**2. Ringkasan dua kali sehari** (bawaan jam 08.00 dan 15.00 WIB, bisa diubah), berisi semua yang masih terbuka:

```
ERP Enteng · Ringkasan 20 Okt 08.00
• 2 kain di bawah stok minimum
• 3 tagihan supplier jatuh tempo ≤ 3 hari: Rp 12.450.000
• 1 piutang pelanggan lewat jatuh tempo: Rp 4.200.000
• 2 PO kekurangan kain
Rincian: buka ERP > Pengingat
```

**Cara membaca "auto kirim terus":** setiap kali kena, pesannya langsung terkirim otomatis. Selama urusannya belum beres,
ia ikut di setiap ringkasan. Pesan langsungnya diulang paling cepat tiap 24 jam (bawaan) sampai beres. Jedanya bisa
diubah di aplikasi, misalnya jadi tiap 4 jam atau tidak diulang.

**Pengaman:**
- Tepat sebelum dikirim, tiap pengingat dicek ulang ke data terbaru. Yang sudah beres tidak dikirim (aturan Bos 8 Okt).
- Satu kejadian tidak dikirim dobel.
- Kalau banyak yang kena bersamaan, misalnya 10 kain sekaligus, semuanya digabung jadi satu pesan, bukan 10 pesan.
- Bawaannya paling banyak 12 pesan langsung per hari, supaya CallMeBot tidak memblokir. Kalau lewat batas, sisanya masuk
  ringkasan berikutnya. Batas ini bisa diubah.
- Jam tenang bawaannya 21.00–06.00. Yang kena di jam itu dikirim jam 06.00. Bisa dimatikan.
- Satu tombol untuk mematikan semua pengiriman, di layar "Sambungan WhatsApp".
- Hanya ke nomor Bos sendiri.
- Isi pesan lewat server CallMeBot (pihak ketiga). Bawaannya **Ringkas**: nama kain/barang tetap tampil (supaya pesan stok
  berguna), tetapi nama supplier, pelanggan dan mandor tidak; tagihan hanya jumlah dan total. Bisa diganti ke **Rinci** di
  aplikasi.
- Kalau CallMeBot sedang mati, pengingat tetap ada di ERP dan layar menulis "WA gagal terkirim jam …".
- Situs CallMeBot menulis API gratisnya "hanya untuk pemakaian pribadi". Kalau suatu hari tidak bisa dipakai, bagian
  pengirimnya bisa diganti (misalnya Telegram) dengan alur yang sama.

**Cara pasang nanti (saat CP7C dibuka):**
1. Dari WA Bos: kirim kalimat persetujuan ke nomor CallMeBot (nomor dan kalimatnya dicek di situs CallMeBot saat itu),
   tunggu balasan berisi kunci.
2. Di ERP, layar "Sambungan WhatsApp": isi nomor WA Bos dan kuncinya. Kunci diketik di layar, tidak pernah lewat chat.
3. Tekan **Kirim pesan uji**. Kalau masuk, tekan **Aktifkan**.

## Desain teknis

### Prinsip

- Ini tujuan baru untuk mesin pengingat yang sudah ada (`scripts/cp7-src/reminders/`): kondisi, episode, kebijakan (ambang,
  jeda `cooldown_minutes`, jam tenang `quiet`) dan pemeriksaan ulang dipakai apa adanya. Lingkungan klaim baru
  `CALLMEBOT_WA_SELF` di samping `LOCAL_TEST_SINK`.
- Semuanya di database: pg_cron menjadwalkan, pg_net mengirim permintaan web, Supabase Vault menyimpan kunci. Tidak perlu
  Edge Function atau server tambahan. Biaya Rp0.
- Paling banyak satu kali kirim per kejadian (at-most-once). Kiriman yang hasilnya tidak diketahui tidak dikirim ulang
  otomatis.
- Pengirim tidak menghitung angka bisnis. Ia hanya membaca kondisi yang sudah lolos pemeriksaan ulang.

### Aturan (rule) baru untuk pemicu stok

Aturan yang sudah ada: `PRODUCTION_GAP`, `ACCESSORY_NEED`, `FABRIC_NEED` (dari analysis staged), `AR_DUE`, `AP_DUE`
(pembaca langsung v1). Tambahan, keduanya dibaca langsung dari data sekarang (live) dan murah:

| Rule | Kondisi terbuka | Sumber | Kunci kondisi |
|---|---|---|---|
| `FABRIC_BELOW_MINIMUM` | qty kain aktif di semua lokasi < `fabric_master_profiles.minimum_stock_qty` (> 0) | Rumus yang sama dengan `low_hit` di `scripts/cp7-src/warehouse-summary/summary.sql`, dipindah ke satu fungsi baca bersama supaya layar Gudang dan pengingat tidak bisa berbeda | `FABRIC_BELOW_MINIMUM:<material_id>` |
| `STOCK_AT_REORDER_POINT` | qty FG/bahan per lokasi ≤ `manual_reorder_point_qty` dari `erp.stock_policy_versions` yang berlaku (basis `MANUAL`) | Saldo stok Native per lokasi | `STOCK_AT_REORDER_POINT:<subject>:<id>:<location>` |

`rule_policies.rule_id` dan `policy_validate` menerima kedua rule ini (bawaan: aktif, cooldown 1.440 menit, jam tenang
21:00–06:00 WIB). Episode, observasi dan `recheck` mengikuti pola `AR_DUE`/`AP_DUE` (live). Barang tanpa stok minimum atau
titik pesan ulang tidak memicu apa pun.

### Komponen

| Komponen | Isi |
|---|---|
| `cp7_reminder_native.wa_self_settings` (revisi append-only, pola `rule_policies`) | `enabled`, `phone_e164`, `detail` (`SUMMARY` bawaan / `DETAILED`), `digest_times` (bawaan `08:00`,`15:00` WIB), `instant_enabled` (bawaan true), `instant_rules` (bawaan semua tujuh rule), `instant_max_per_day` (bawaan 12), `max_items` (bawaan 10), `actor` (owner yang mengaktifkan), `reason`, `created_at` |
| Vault secret `cp7_callmebot_apikey` | Ditulis lewat `erp_cp7_set_wa_self_key_v1` (khusus owner). Tidak ada RPC yang membacanya kembali; layar hanya menampilkan "kunci terpasang, diganti <tanggal>" |
| `cp7_reminder_native.wa_self_dispatches` | Satu baris per pesan: `kind` (`INSTANT`, `DIGEST`, `TEST`), `slot` (untuk DIGEST: tanggal+jam WIB, unik; untuk INSTANT: id tick), `claim_ids[]`, `body`, `body_sha256`, `net_request_id`, `status` (`QUEUED`, `PROVIDER_ACCEPTED`, `PROVIDER_REFUSED`, `UNKNOWN`, `NOTHING_DUE`, `SKIPPED_DISABLED`, `SKIPPED_LIMIT`, `HELD_QUIET`), `http_status`, `provider_text` (dipotong, tanpa kunci), `created_at`, `finished_at`. Append-only kecuali transisi status yang dijaga trigger |
| `cp7_reminder_native.wa_self_tick()` (pg_cron tiap 5 menit) | Menjalankan mode langsung tiap tick, dan ringkasan bila slotnya jatuh waktu |
| `cp7_reminder_native.wa_self_reconcile()` (pg_cron tiap menit) | Membaca `net._http_response` untuk dispatch `QUEUED` |
| Layar "Sambungan WhatsApp" (halaman yang sudah ada di `src/cp7/Cp7Shell.tsx`) | Aktif/mati; nomor (disamarkan); kunci terpasang ya/tidak; pesan langsung aktif/mati + daftar pemicu; jeda ulang; batas per hari; jam tenang; Rinci/Ringkas; jam ringkasan; **Kirim pesan uji**; riwayat 30 kiriman terakhir dengan status |

Identitas: tick berjalan sebagai peran `cp7_reminder` dengan identitas owner dari settings (pola penjalan server K4: akses
dicek ulang tiap unit). Kalau owner kehilangan izin baca (misalnya `finance.ap.view`), rule itu berhenti dikirim.

### Alur mode langsung (tiap tick)

1. Lock advisory `CP7:WA_SELF:TICK`; tick kedua yang bersamaan langsung selesai.
2. Settings mati, kunci tidak ada, atau `instant_enabled=false` → selesai tanpa baris.
3. Evaluasi rule live (`FABRIC_BELOW_MINIMUM`, `STOCK_AT_REORDER_POINT`, `AR_DUE`, `AP_DUE`), dan rule staged bila ada set
   kondisi `DONE` baru sejak tick sebelumnya (analisis yang dijalankan siapa pun atau dijadwalkan).
4. Calon kirim: kondisi yang **baru membuka episode** sejak tick sebelumnya, ditambah kondisi yang masih terbuka dan
   jedanya (`cooldown_minutes`) sudah lewat.
5. Klaim tiap calon lewat jalur klaim yang sudah ada dengan lingkungan `CALLMEBOT_WA_SELF`. Pemeriksaan ulang ke data
   sekarang berjalan di sini; yang bukan `STILL_OPEN` dicatat alasannya dan tidak dikirim. `occurrence_key` mencegah dobel.
6. Jam tenang → dispatch `HELD_QUIET`; klaim tetap dan dikirim di tick pertama sesudah jam tenang, dengan pemeriksaan ulang
   lagi.
7. Batas harian tercapai → `SKIPPED_LIMIT`; klaim dilepas (`SUPPRESSED` dengan alasan `DAILY_LIMIT`) dan kondisinya muncul di
   ringkasan berikutnya.
8. Semua calon satu tick digabung jadi satu pesan (dikelompokkan per rule, paling banyak `max_items` baris lalu "dan N
   lainnya"; maksimal 1.000 karakter) → kirim (lihat "Kirim dan hasil").

### Alur ringkasan (slot 08:00 / 15:00)

1. Lock advisory per slot `CP7:WA_SELF:DIGEST:<slot>`; satu dispatch per slot.
2. Kumpulkan semua kondisi yang masih terbuka dari tujuh rule. Klaim dengan `occurrence_key` milik slot itu (bukan kejadian
   langsung), jadi ringkasan tidak memakan jatah jeda pesan langsung.
3. Pemeriksaan ulang seperti di atas; tidak ada yang terbuka → `NOTHING_DUE` tanpa pesan.
4. Susun per kelompok (jumlah dan total rupiah; `DETAILED` menambah nama) → kirim.

### Kirim dan hasil

- `net.http_get('https://api.callmebot.com/whatsapp.php', phone, text, apikey)`. Kunci dibaca dari Vault di dalam fungsi
  `security definer` milik `cp7_reminder`, tidak pernah ditulis ke tabel ERP atau log. Dispatch `QUEUED` dengan
  `net_request_id`; klaim tetap `CLAIMED` dan terikat ke dispatch.
- `wa_self_reconcile`:
  - HTTP 200 → dispatch `PROVIDER_ACCEPTED`, klaim selesai (status klaim baru `PROVIDER_ACCEPTED`).
  - HTTP lain → dispatch `PROVIDER_REFUSED`, klaim `SUPPRESSED` dengan alasan; kondisinya boleh ikut tick atau slot
    berikutnya karena belum pernah terkirim.
  - Tidak ada jawaban sesudah 10 menit → `UNKNOWN`, klaim `UNKNOWN`. Tidak dikirim ulang otomatis; layar meminta owner
    menandai "masuk"/"tidak masuk" (tabel resolusi yang sudah ada).
- Antar dua permintaan ke CallMeBot paling sedikit 60 detik (antrian di tick).
- Tiga kegagalan berturut-turut → peringatan di layar Sambungan WhatsApp dan halaman Pengingat; pengiriman tetap dicoba.

Pesan uji: `erp_cp7_send_wa_self_test_v1`, satu pesan tetap ("ERP Enteng: pesan uji <jam>"), dispatch `TEST`, paling banyak
3 per jam.

### Keamanan dan izin

- Semua RPC baru hanya owner (`erp.require_owner_admin()`) dan mengikuti fasad CP7: `authenticated` hanya memanggil RPC
  publik `erp_cp7_*`; fungsi di `cp7_reminder_native` tidak bisa dipanggil peran browser (FABLE-012 tetap berlaku).
- Kunci: Vault, tulis-saja. Tidak ada di repo, chat, artifact CI, atau `wa_self_dispatches`. Uji mencari nilai kunci di
  semua tabel `cp7_*`/`erp` dan log job: harus nol.
- `net.http_request_queue` menyimpan URL berisi kunci sampai permintaan diproses, dan hanya bisa dibaca superuser/peran
  Supabase. Batas ini diterima dan dicatat; alternatifnya Edge Function dengan secret, kalau auditor menolak.
- `SUMMARY` memuat nama kain/barang tetapi tidak memuat nama supplier, pelanggan, mandor, nomor HP atau alamat.
- Izin baca per rule mengikuti `rule-policy.sql` (AR_DUE butuh `finance.ar.view`, AP_DUE `finance.ap.view`); rule stok
  butuh izin lihat gudang yang sama dengan Ringkasan Gudang.

### Uji (sebelum pemasangan; tidak ada pesan sungguhan)

CI memakai server CallMeBot palsu (HTTP lokal di runner) yang mencatat permintaan dan bisa menjawab 200, 500 atau diam.
pg_net diarahkan ke alamat palsu lewat setting uji; alamat asli hanya di pemasangan.

| Uji | Yang dibuktikan |
|---|---|
| Native: kain turun di bawah minimum lewat pemakaian kain | Satu pesan langsung di tick berikutnya; isinya sama dengan daftar "di bawah minimum" di Ringkasan Gudang |
| Native: stok naik lagi sebelum tick | Tidak dikirim; alasan `RESOLVED_NOW` |
| Native: masih di bawah minimum, jeda belum lewat / sudah lewat | Tidak dobel / dikirim ulang sekali |
| Native: 10 kain kena dalam satu tick | Satu pesan berisi 10 baris (atau 10 baris pertama + "dan N lainnya") |
| Native: batas harian, jam tenang | `SKIPPED_LIMIT` lalu masuk ringkasan / `HELD_QUIET` lalu dikirim 06:00 dengan cek ulang |
| Native: ringkasan | Semua kondisi terbuka masuk; tidak memakan jeda pesan langsung; `NOTHING_DUE` tanpa pesan |
| Native: 200 / 500 / diam | `PROVIDER_ACCEPTED` / `PROVIDER_REFUSED` lalu ikut berikutnya / `UNKNOWN` tanpa kirim ulang |
| Native: mati, tanpa kunci | Tidak ada permintaan ke server palsu |
| Native: kunci | Tidak terbaca lewat RPC mana pun; tidak ada di tabel ERP, dispatch atau log |
| Native: `SUMMARY` | Memuat nama kain/barang; tidak memuat nama supplier/pelanggan/mandor dari fixture |
| Native: izin | Non-owner ditolak di semua RPC baru; rule mengikuti izin baca owner |
| Race: dua tick bersamaan; ringkasan dan tick bersamaan | Satu dispatch per tick/slot, satu permintaan per dispatch, tidak ada klaim yatim |
| Race: kain diterima saat tick berjalan | Dikirim hanya kalau masih di bawah minimum saat diklaim |
| HTTP Auth nyata | Owner bisa set kunci/aktifkan/kirim uji; staf ditolak 42501 |
| Browser desktop + HP | Layar Sambungan WhatsApp: isi kunci, kirim uji (server palsu), atur pemicu dan jeda, riwayat, matikan |

### Pemasangan

Ikut CP7C (ditahan, D13-9a): butuh pg_cron, pg_net dan Vault aktif di Enteng (dicek saat preflight), dan pemasangan sesudah
backup awal terverifikasi. Pesan sungguhan pertama hanya **pesan uji** yang ditekan owner sendiri. Penulis tidak mengirim
pesan apa pun.

### Belum pasti (dicek saat pembuatan atau pemasangan)

- Format dan metode API CallMeBot (GET dengan `phone`, `text`, `apikey` menurut tutorial; sumber lain menyebut POST) serta
  teks jawaban suksesnya. Desain ini hanya memakai HTTP 200 sebagai tanda diterima.
- Batas kirim CallMeBot (tidak ditemukan angka resmi). Bawaan desain: 12 pesan langsung + 2 ringkasan per hari, jarak antar
  kirim minimal 60 detik.
- Apakah "pemakaian pribadi" mencakup pengingat usaha ke nomor owner sendiri. Owner memilih CallMeBot dengan catatan ini.
- `STOCK_AT_REORDER_POINT` hanya berguna bila titik pesan ulang sudah diatur di Kebijakan stok; layar CP7 untuk mengaturnya
  diperiksa saat pembuatan (yang pasti ada: stok minimum kain di data Kain).

Sumber: https://www.callmebot.com/blog/free-api-whatsapp-messages/ ; https://www.callmebot.com/tag/free/ (lewat pencarian,
19 Okt 2026). Perbandingan pilihan: `WA_PILIHAN_PENGIRIMAN_20261019.md`.
