# Desain: semua pengingat ERP diteruskan ke WhatsApp owner lewat CallMeBot (D17-3..D17-5)

Status: **desain**. Belum dibuat, belum dipasang.

Keputusan owner (19 Okt 2026), dikutip persis:
- D17-3: "yaudah desain callmebot buat gw"
- D17-4: "gw maunya tiap kena safety stock dll auto kirim terus, yg sehari 2kali itu juga mau kan ringkasan"
- D17-5: "bukan cuma itu, semua hal yg masuk ke reminder harus langsung forward wa biar realtime
  triger lu pasti lebih gampang kan"

## Untuk owner (ringkas)

**Aturannya:** apa pun yang muncul di Pengingat ERP langsung diteruskan ke WhatsApp Bos, otomatis, tanpa ada yang menekan
tombol. Ditambah ringkasan jam 08.00 dan 15.00 (jamnya bisa diubah) berisi semua yang masih belum beres.

**Yang diteruskan:**

| Yang muncul di Pengingat | Kapan masuk WA |
|---|---|
| Hal "Perlu perhatian" baru dari analisis (kekurangan kain/aksesori untuk PO, target produksi kurang, dan lainnya) | Beberapa detik sesudah muncul |
| Pengingat aturan yang baru kena (tagihan supplier, piutang pelanggan, kewajiban lain) | Beberapa detik sesudah tercatat |
| Pengingat pribadi Bos sendiri (yang dibuat di menu Reminder) | Saat waktunya tiba (paling lambat ±1 menit) |
| Jatuh tempo yang tiba karena tanggal berganti | Paling lambat ±1 menit sesudah lewat |
| Stok kain di bawah stok minimum, stok sampai titik pesan ulang | Paling lambat ±1 menit sesudah transaksi gudang yang menyebabkannya |

Contoh:

```
⚠ ERP Enteng · 20 Okt 10.35
Stok kain di bawah minimum: Katun Combed 30s Hitam
Sisa 42 kg, minimum 60 kg
Buka ERP > Bahan & Roll
```

**Soal trigger:** betul, untuk yang tercatat sebagai baris baru di Pengingat, trigger yang dipakai, dan masuk WA dalam hitungan
detik. Ada dua hal yang tidak bisa dengan trigger:
- **Jatuh tempo dan pengingat pribadi** muncul karena waktu berjalan, bukan karena ada data baru. Jadi dicek tiap menit.
- **Stok** juga dicek tiap menit, tidak pakai trigger di tabel transaksi gudang. Trigger di sana ikut berjalan di setiap
  transaksi gudang; kalau bermasalah, transaksi gudangnya bisa ikut gagal. Untuk Bos hasilnya sama: masuk WA paling lambat
  ±1 menit.

Kalau transaksinya batal, pesannya tidak terkirim.

**Selama belum beres:** ikut di setiap ringkasan. Pesan langsung diulang paling cepat tiap 24 jam (bisa diubah di aplikasi,
atau dimatikan).

**Supaya tidak kebanjiran dan nomor tidak diblokir CallMeBot:**
- Yang muncul dalam menit yang sama digabung jadi satu pesan.
- Paling banyak satu pesan per menit.
- Sesudah 30 pesan dalam sehari (bisa diubah), pesan berikutnya digabung jadi satu tiap 30 menit.
- **Tidak ada yang dibuang**, hanya digabung.
- Jam tenang 21.00–06.00 (bisa dimatikan): yang muncul di jam itu dikirim jam 06.00.
- Satu tombol untuk mematikan semua, di layar "Sambungan WhatsApp".

**Pengaman lain:**
- Tepat sebelum dikirim, tiap pengingat dicek ulang ke data terbaru. Yang sudah beres tidak dikirim (aturan Bos 8 Okt).
- Satu kejadian tidak dikirim dobel.
- Hanya ke nomor Bos sendiri. Pengingat pribadi milik staf tidak diteruskan, karena itu catatan pribadi mereka.
- Isi pesan lewat server CallMeBot (pihak ketiga). Bawaannya **Ringkas**: nama kain/barang tampil, nama supplier, pelanggan
  dan mandor tidak; tagihan hanya jumlah dan total. Bisa diganti ke **Rinci** di aplikasi.
- Kalau CallMeBot sedang mati, pengingat tetap ada di ERP dan layar menulis "WA gagal terkirim jam …".
- Situs CallMeBot menulis API gratisnya "hanya untuk pemakaian pribadi". Kalau suatu hari tidak bisa dipakai, bagian
  pengirimnya bisa diganti (misalnya Telegram) dengan alur yang sama.

**Cara pasang nanti (saat CP7C dibuka):**
1. Dari WA Bos: kirim kalimat persetujuan ke nomor CallMeBot (nomor dan kalimatnya dicek di situs CallMeBot saat itu), lalu
   tunggu balasan berisi kunci.
2. Di ERP, layar "Sambungan WhatsApp": isi nomor WA Bos dan kuncinya. Kunci diketik di layar, tidak pernah lewat chat.
3. Tekan **Kirim pesan uji**. Kalau masuk, tekan **Aktifkan**.

## Desain teknis

### Prinsip

- Satu kotak keluar (outbox) untuk semua sumber pengingat. Sumber hanya menaruh "sesuatu baru muncul"; satu pengirim
  memeriksa ulang, menggabung, dan mengirim.
- Mesin pengingat yang sudah ada (`scripts/cp7-src/reminders/`) tidak diubah perilakunya: kondisi, episode, kebijakan
  (`cooldown_minutes`, `quiet`) dan pemeriksaan ulang dipakai apa adanya. Lingkungan klaim baru `CALLMEBOT_WA_SELF` di
  samping `LOCAL_TEST_SINK`.
- Semuanya di database: trigger dan pg_cron (tiap menit) mengisi outbox, pg_net mengirim permintaan web **sesudah transaksi
  commit** (transaksi batal = tidak ada pesan), Supabase Vault menyimpan kunci. Tidak perlu Edge Function atau server
  tambahan. Biaya Rp0.
- Tidak ada trigger di tabel bisnis Native (stok, jurnal, penjualan). Trigger hanya di tabel milik `cp7_reminder_native`.
- Paling banyak satu kali kirim per kejadian (at-most-once). Kiriman yang hasilnya tidak diketahui tidak dikirim ulang
  otomatis.
- Pengirim tidak menghitung angka bisnis; ia hanya membaca kondisi yang lolos pemeriksaan ulang.

### Sumber dan cara masuk outbox

| Sumber (tabel/rule yang sudah ada) | Dianggap "masuk" saat | Cara masuk outbox |
|---|---|---|
| `cp7_reminder_native.attention` (Perlu perhatian dari analisis) | baris baru `state='NEW'`, atau `SNOOZED` yang `resume_at`-nya tiba | Trigger `AFTER INSERT`; snooze lewat tick menit |
| `cp7_reminder_native.rule_episodes`, `staged_episodes` (PRODUCTION_GAP, ACCESSORY_NEED, FABRIC_NEED, AR_DUE, AP_DUE) | episode baru `state='ACTIVE'` | Trigger `AFTER INSERT` |
| `cp7_reminder_native.obligation_episodes` (AR, MATERIAL_AP, kewajiban lain bila sudah dipasang) | episode baru `state='ACTIVE'` | Trigger `AFTER INSERT` |
| `erp.manual_reminders` milik owner (`owner_user_id` = owner, `status='OPEN'`) | `due_at` tiba | Tick menit (dibaca saja; tidak ada trigger di tabel Native ini) |
| Jatuh tempo AR/AP yang tiba karena tanggal | tanggal WIB berganti / jam tertentu | Tick menit menjalankan pembaca langsung yang sudah ada; episode baru lalu masuk lewat trigger di atas |
| Stok: `FABRIC_BELOW_MINIMUM`, `STOCK_AT_REORDER_POINT` (rule baru, di bawah) | kondisi baru terbuka | Tick menit; episode baru lalu masuk lewat trigger di atas |

`attention` ditulis ulang per run analisis dan per pengguna (`actor`, `run_id`, `action_key`). Pengirim mengenali hal yang sama
lewat `semantic_hash`: hal yang sama dari run analisis berikutnya (atau dari analisis staf) tidak dikirim lagi selama masih
dalam jeda ulang; hanya `semantic_hash` yang belum pernah diteruskan atau yang muncul lagi sesudah beres yang dihitung baru.

Trigger hanya menyisipkan satu baris kecil ke `wa_self_outbox` (`source`, `source_id`, `condition_key`, `seen_at`) dan tidak
pernah gagal karena isi (tanpa validasi rumit, tanpa panggilan luar). Kalau settings mati, trigger tidak menulis apa pun.

### Rule baru untuk stok

| Rule | Kondisi terbuka | Sumber | Kunci kondisi |
|---|---|---|---|
| `FABRIC_BELOW_MINIMUM` | qty kain aktif di semua lokasi < `fabric_master_profiles.minimum_stock_qty` (> 0) | Rumus `low_hit` di `scripts/cp7-src/warehouse-summary/summary.sql`, dipindah ke satu fungsi baca bersama supaya layar Gudang dan pengingat tidak bisa berbeda | `FABRIC_BELOW_MINIMUM:<material_id>` |
| `STOCK_AT_REORDER_POINT` | qty FG/bahan per lokasi ≤ `manual_reorder_point_qty` dari `erp.stock_policy_versions` yang berlaku (basis `MANUAL`) | Saldo stok Native per lokasi | `STOCK_AT_REORDER_POINT:<subject>:<id>:<location>` |

`rule_policies` dan `policy_validate` menerima kedua rule (bawaan: aktif, cooldown 1.440 menit, jam tenang 21:00–06:00 WIB).
Episode dan `recheck` mengikuti pola `AR_DUE`/`AP_DUE`. Tick menit hanya membaca bahan dengan stok minimum/titik pesan ulang
(himpunan kecil), jadi murah.

### Komponen

| Komponen | Isi |
|---|---|
| `cp7_reminder_native.wa_self_settings` (revisi append-only, pola `rule_policies`) | `enabled`, `phone_e164`, `detail` (`SUMMARY` bawaan / `DETAILED`), `digest_times` (bawaan `08:00`,`15:00` WIB), `instant_enabled` (bawaan true), `sources` (bawaan semua), `repeat_minutes` (bawaan 1.440; 0 = tidak diulang), `burst_after_per_day` (bawaan 30), `burst_merge_minutes` (bawaan 30), `max_items` (bawaan 10), `quiet` (bawaan 21:00–06:00), `actor` (owner), `reason`, `created_at` |
| Vault secret `cp7_callmebot_apikey` | Ditulis lewat `erp_cp7_set_wa_self_key_v1` (khusus owner). Tidak ada RPC yang membacanya kembali |
| `cp7_reminder_native.wa_self_outbox` | Baris "muncul" dari trigger/tick: `id`, `source`, `source_id`, `condition_key`, `seen_at`, `dispatch_id` (null sampai dikirim/diputuskan), `outcome` (`SENT`, `RESOLVED_BEFORE_SEND`, `MERGED`, `HELD_QUIET`, `DISABLED`) |
| `cp7_reminder_native.wa_self_dispatches` | Satu baris per pesan: `kind` (`INSTANT`, `DIGEST`, `TEST`), `slot`, `claim_ids[]`, `outbox_ids[]`, `body`, `body_sha256`, `net_request_id`, `status` (`QUEUED`, `PROVIDER_ACCEPTED`, `PROVIDER_REFUSED`, `UNKNOWN`, `NOTHING_DUE`, `HELD_QUIET`), `http_status`, `provider_text` (dipotong, tanpa kunci), `created_at`, `finished_at` |
| `cp7_reminder_native.wa_self_tick()` (pg_cron tiap menit) | Isi outbox dari sumber berbasis waktu dan stok; kirim outbox yang menunggu; ringkasan bila slotnya tiba |
| `cp7_reminder_native.wa_self_reconcile()` (pg_cron tiap menit) | Membaca `net._http_response` untuk dispatch `QUEUED` |
| Layar "Sambungan WhatsApp" (halaman yang sudah ada di `src/cp7/Cp7Shell.tsx`) | Aktif/mati; nomor (disamarkan); kunci terpasang ya/tidak; sumber yang diteruskan; ulang tiap; batas gabung; jam tenang; Ringkas/Rinci; jam ringkasan; **Kirim pesan uji**; riwayat 30 kiriman terakhir dengan status |

Identitas: tick berjalan sebagai peran `cp7_reminder` dengan identitas owner dari settings (pola penjalan server K4: akses
dicek ulang tiap unit). Pengingat yang owner tidak berhak lihat tidak diteruskan.

### Alur kirim (tiap tick)

1. Lock advisory `CP7:WA_SELF:TICK`; tick kedua yang bersamaan langsung selesai.
2. Settings mati atau kunci tidak ada → outbox yang menunggu ditandai `DISABLED`; selesai.
3. Isi outbox dari sumber berbasis waktu dan stok (tabel di atas).
4. Ambil outbox yang menunggu. Untuk tiap baris, klaim lewat jalur klaim yang sudah ada dengan lingkungan `CALLMEBOT_WA_SELF`.
   Pemeriksaan ulang ke data sekarang berjalan di sini. Yang bukan `STILL_OPEN` ditandai `RESOLVED_BEFORE_SEND` dengan
   alasannya. `occurrence_key` mencegah dobel. Pengingat pribadi dan hal Perlu perhatian diperiksa masih `OPEN`/`NEW`.
5. Jam tenang → `HELD_QUIET`; diproses lagi (dengan cek ulang) di tick pertama sesudah jam tenang.
6. Gabung semua yang lolos jadi satu pesan, dikelompokkan per jenis, paling banyak `max_items` baris lalu "dan N lainnya",
   maksimal 1.000 karakter. Kalau jumlah pesan hari ini ≥ `burst_after_per_day`, tahan dan gabung sampai
   `burst_merge_minutes` lewat sejak pesan terakhir.
7. Kirim (paling banyak satu pesan per tick): `net.http_get('https://api.callmebot.com/whatsapp.php', phone, text, apikey)`.
   Kunci dibaca dari Vault di dalam fungsi `security definer` milik `cp7_reminder`, tidak pernah ditulis ke tabel ERP atau
   log. Dispatch `QUEUED`.
8. Ulangan: kondisi yang masih terbuka dan sudah dikirim masuk outbox lagi bila `repeat_minutes` lewat.

Ringkasan (slot `digest_times`): lock per slot; semua yang masih terbuka dari semua sumber; klaim dengan `occurrence_key`
milik slot (tidak memakan jeda pesan langsung); cek ulang; tidak ada yang terbuka → `NOTHING_DUE` tanpa pesan.

Hasil (`wa_self_reconcile`):
- HTTP 200 → `PROVIDER_ACCEPTED`; klaim selesai (status klaim baru `PROVIDER_ACCEPTED`).
- HTTP lain → `PROVIDER_REFUSED`; klaim `SUPPRESSED` dengan alasan; outbox kembali menunggu (belum pernah terkirim).
- Tidak ada jawaban sesudah 10 menit → `UNKNOWN`; tidak dikirim ulang otomatis; layar meminta owner menandai "masuk"/"tidak
  masuk" (tabel resolusi yang sudah ada).
- Tiga kegagalan berturut-turut → peringatan di layar Sambungan WhatsApp dan halaman Pengingat; pengiriman tetap dicoba.

Pesan uji: `erp_cp7_send_wa_self_test_v1`, satu pesan tetap ("ERP Enteng: pesan uji <jam>"), dispatch `TEST`, paling banyak
3 per jam.

### Keamanan dan izin

- Semua RPC baru hanya owner (`erp.require_owner_admin()`) dan mengikuti fasad CP7: `authenticated` hanya memanggil RPC
  publik `erp_cp7_*`; fungsi dan tabel di `cp7_reminder_native` tidak bisa dipakai peran browser (FABLE-012 tetap berlaku).
- Kunci: Vault, tulis-saja. Tidak ada di repo, chat, artifact CI, outbox atau dispatch. Uji mencari nilai kunci di semua tabel
  `cp7_*`/`erp` dan log job: harus nol.
- `net.http_request_queue` menyimpan URL berisi kunci sampai permintaan diproses, dan hanya bisa dibaca superuser/peran
  Supabase. Batas ini diterima dan dicatat; alternatifnya Edge Function dengan secret, kalau auditor menolak.
- `SUMMARY` memuat nama kain/barang tetapi tidak memuat nama supplier, pelanggan, mandor, nomor HP atau alamat.
- Pengingat pribadi staf tidak pernah dibaca pengirim (filter `owner_user_id` = owner di settings).

### Uji (sebelum pemasangan; tidak ada pesan sungguhan)

CI memakai server CallMeBot palsu (HTTP lokal di runner) yang mencatat permintaan dan bisa menjawab 200, 500 atau diam.
pg_net diarahkan ke alamat palsu lewat setting uji; alamat asli hanya di pemasangan.

| Uji | Yang dibuktikan |
|---|---|
| Native: tiap sumber (attention baru, episode aturan baru, episode kewajiban baru, pengingat pribadi owner jatuh waktu, jatuh tempo karena tanggal, kain di bawah minimum, titik pesan ulang) | Masuk outbox dan terkirim; waktu dari muncul sampai permintaan tercatat (target: trigger < 1 tick, waktu/stok ≤ 2 tick) |
| Native: transaksi yang membuat episode lalu batal (rollback) | Tidak ada outbox, tidak ada permintaan |
| Native: analisis dijalankan dua kali (owner, lalu staf) dengan hal Perlu perhatian yang sama | Satu kiriman; analisis kedua tidak mengirim ulang |
| Native: kondisi beres sebelum tick | Tidak dikirim; `RESOLVED_BEFORE_SEND` dengan alasan |
| Native: masih terbuka, ulang belum lewat / sudah lewat | Tidak dobel / dikirim ulang sekali |
| Native: 10 hal muncul di menit yang sama | Satu pesan |
| Native: lewat 30 pesan sehari | Pesan berikutnya digabung tiap 30 menit; tidak ada yang hilang (jumlah outbox = jumlah yang terkirim/tergabung/beres) |
| Native: jam tenang | `HELD_QUIET` lalu dikirim 06:00 dengan cek ulang |
| Native: ringkasan | Semua yang terbuka masuk; tidak memakan jeda pesan langsung; `NOTHING_DUE` tanpa pesan |
| Native: 200 / 500 / diam | `PROVIDER_ACCEPTED` / `PROVIDER_REFUSED` lalu kirim lagi / `UNKNOWN` tanpa kirim ulang |
| Native: mati, tanpa kunci | Tidak ada permintaan ke server palsu; trigger tidak menulis |
| Native: trigger tidak mengganggu | Transaksi yang membuat episode/attention tetap berhasil dengan outbox penuh atau settings rusak |
| Native: kunci | Tidak terbaca lewat RPC mana pun; tidak ada di tabel ERP, outbox, dispatch atau log |
| Native: privasi | `SUMMARY` tanpa nama supplier/pelanggan/mandor; pengingat pribadi staf tidak pernah masuk outbox |
| Native: izin | Non-owner ditolak di semua RPC baru; pengingat yang owner tidak berhak lihat tidak diteruskan |
| Race: dua tick bersamaan; ringkasan dan tick bersamaan; episode dibuat saat tick berjalan | Satu dispatch per tick/slot; tidak ada kiriman dobel atau outbox yatim |
| Race: kain diterima saat tick berjalan | Dikirim hanya kalau masih di bawah minimum saat diklaim |
| HTTP Auth nyata | Owner bisa set kunci/aktifkan/kirim uji; staf ditolak 42501 |
| Browser desktop + HP | Layar Sambungan WhatsApp: isi kunci, kirim uji (server palsu), atur sumber/ulang/gabung, riwayat, matikan |

### Pemasangan

Ikut CP7C (ditahan, D13-9a): butuh pg_cron (jadwal tiap menit), pg_net dan Vault aktif di Enteng (dicek saat preflight), dan
pemasangan sesudah backup awal terverifikasi. Pesan sungguhan pertama hanya **pesan uji** yang ditekan owner sendiri.
Penulis tidak mengirim pesan apa pun.

### Belum pasti (dicek saat pembuatan atau pemasangan)

- Format dan metode API CallMeBot (GET dengan `phone`, `text`, `apikey` menurut tutorial; sumber lain menyebut POST) serta
  teks jawaban suksesnya. Desain ini hanya memakai HTTP 200 sebagai tanda diterima.
- Batas kirim CallMeBot (tidak ditemukan angka resmi). Bawaan desain: maksimal satu pesan per menit, digabung tiap 30 menit
  sesudah 30 pesan sehari; angkanya bisa diubah di aplikasi.
- Apakah "pemakaian pribadi" mencakup pengingat usaha ke nomor owner sendiri. Owner memilih CallMeBot dengan catatan ini.
- `STOCK_AT_REORDER_POINT` hanya berguna bila titik pesan ulang sudah diatur di Kebijakan stok; layar CP7 untuk mengaturnya
  diperiksa saat pembuatan (yang pasti ada: stok minimum kain di data Kain).
- Kewajiban lain (`other-obligation-source.sql`) masih draf; diteruskan begitu sumbernya dipasang.

Sumber: https://www.callmebot.com/blog/free-api-whatsapp-messages/ ; https://www.callmebot.com/tag/free/ (lewat pencarian,
19 Okt 2026). Perbandingan pilihan: `WA_PILIHAN_PENGIRIMAN_20261019.md`.
