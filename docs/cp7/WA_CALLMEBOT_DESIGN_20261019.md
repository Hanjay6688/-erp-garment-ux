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

Supaya "semua yang masuk Pengingat" benar-benar satu tempat, menu **Reminder** mendapat bagian baru **Pengingat sistem**: stok
di bawah minimum, tagihan dan piutang jatuh tempo, kekurangan kain/aksesori untuk PO dan target produksi. Sekarang hal-hal
itu tersebar di Ringkasan Gudang dan panel analisis. Pengingat pribadi yang diketik manual tetap di tempatnya. Setiap baris baru
di Pengingat sistem (dan pengingat pribadi Bos yang waktunya tiba) langsung diteruskan ke WA.

**Yang diteruskan:**

| Yang muncul di Pengingat | Kapan masuk WA |
|---|---|
| Kekurangan kain/aksesori untuk PO, target produksi kurang | Beberapa detik sesudah analisis selesai. Analisis dijalankan otomatis tiap 60 menit di jam kerja (bisa diubah, paling cepat 15 menit), dan juga setiap kali seseorang menjalankannya di aplikasi |
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

Versi kedua (sesudah pemetaan modul pengingat): penerusan WA dan daftar Pengingat sistem dibuat sebagai modul sendiri. Modul
pengingat yang sudah ada (`scripts/cp7-src/reminders/`) tidak diubah. Alasannya:

- Pengingat di modul lama dihitung saat seseorang membuka panel. Tidak ada aliran kejadian otomatis.
- Klaim WA di tabel klaim lama akan muncul di panel lama dan ditolak oleh layarnya.
- Pemeriksa bundle lama mengunci jumlah fungsi, trigger dan hak baca tabel `erp` peran `cp7_reminder`.

### Bagian

| Bagian | Isi |
|---|---|
| Skema `cp7_alert_native`, peran `cp7_alert` (nologin, noinherit) | Pemilik semua tabel dan fungsi baru. Hak baca hanya yang dipakai pengumpul (dicek bundle seperti `cp7_reminder`) |
| `alerts` | Satu baris per kejadian Pengingat sistem: `id`, `kind` (`FABRIC_BELOW_MINIMUM`, `STOCK_AT_REORDER_POINT`, `AR_DUE`, `AP_DUE`, `FABRIC_NEED`, `ACCESSORY_NEED`, `PRODUCTION_GAP`), `subject_key`, `episode` (naik bila muncul lagi sesudah beres), `title`, `detail` jsonb (angka dari sumber, tanpa hitungan baru), `party_names` jsonb (dipisah agar Ringkas bisa menyembunyikan), `source_hash`, `opened_at`, `resolved_at`, `state` (`OPEN`/`RESOLVED`). Satu `OPEN` per `kind+subject_key` (unique index parsial). Append-only kecuali penutupan |
| `alert_settings` | Revisi append-only: `enabled`, `phone_e164`, `detail` (`SUMMARY` bawaan / `DETAILED`), `digest_times`, `kinds`, `repeat_minutes` (1.440), `burst_after_per_day` (30), `burst_merge_minutes` (30), `max_items` (10), `quiet` (21:00–06:00), `analysis_every_minutes` (60, minimal 15, `0` = mati), `analysis_hours` (07:00–20:00), `actor` (owner yang mengaktifkan) |
| Vault secret `cp7_callmebot_apikey` | Ditulis lewat `erp_cp7_set_wa_key_v1` (khusus owner). Tidak ada RPC yang membacanya kembali |
| `wa_outbox` | Diisi trigger `AFTER INSERT` pada `alerts` (kejadian baru) dan oleh tick untuk pengingat pribadi owner yang jatuh waktu dan untuk ulangan. Kolom: `source` (`ALERT`, `MANUAL_REMINDER`, `REPEAT`), `source_id`, `seen_at`, `dispatch_id`, `outcome` |
| `wa_dispatches` | Satu baris per pesan (`INSTANT`, `DIGEST`, `TEST`), `body`, `body_sha256`, `net_request_id`, `status`, `http_status`, `provider_text`, waktu |
| `cp7_alert_native.collect()` | Pengumpul. Sumber dibaca sebagai owner lewat pembaca yang sudah ada (pola K4: `request.jwt.claims` owner, akses dicek ulang tiap langkah, klaim dipulihkan sesudahnya). Membuka `alerts` baru dan menutup yang sudah beres |
| `cp7_alert_native.wa_send()` / `wa_reconcile()` | Menggabung outbox, cek ulang, kirim lewat pg_net sesudah commit; membaca jawaban |
| Jadwal (`cp7_ops.schedules()`, dipasang `scripts/cp7_schedule.py` bersama jadwal CP7 lain) | `cp7-alert-collect` tiap menit, `cp7-wa-send` tiap menit, `cp7-alert-analysis` sesuai `analysis_every_minutes`. Daftar jadwal di kasus K3/K4/K6 ditambah secara terdeklarasi |
| RPC publik (`erp_cp7_*`, owner `cp7_alert`, `authenticated` saja) | `erp_cp7_get_alerts_v1` (daftar Pengingat sistem; izin baca per jenis), `erp_cp7_get_wa_settings_v1`, `erp_cp7_save_wa_settings_v1`, `erp_cp7_set_wa_key_v1`, `erp_cp7_send_wa_test_v1`, `erp_cp7_resolve_wa_dispatch_v1` (tandai "masuk"/"tidak masuk" untuk `UNKNOWN`) |
| Layar | Menu Reminder: bagian Pengingat sistem (semua peran yang berhak melihat) dan tab "Sambungan WhatsApp" (khusus owner) |

### Sumber pengumpul (dibaca sebagai owner, tanpa hitungan baru)

| Jenis | Pembaca yang sudah ada |
|---|---|
| `FABRIC_BELOW_MINIMUM` | `low`/`low_hit` di `scripts/cp7-src/warehouse-summary/summary.sql` dipindah ke satu fungsi baca bersama (`cp7_warehouse_summary.fabric_below_minimum()`); Ringkasan Gudang dan pengumpul memakai fungsi yang sama. Uji gudang lama tetap harus lulus tanpa diubah |
| `STOCK_AT_REORDER_POINT` | `erp.stock_policy_versions` yang berlaku (basis `MANUAL`) dibanding saldo stok Native per lokasi lewat pembaca kartu stok CP7 yang sudah ada. Diperiksa saat pembuatan: kalau tidak ada pembaca tanpa hitungan baru, jenis ini ditunda dan ditulis di "belum" |
| `AR_DUE`, `AP_DUE` | `cp7_reminder_native.receivable_source()` / `payable_source()` (tidak butuh run analisis; izin `finance.ar.view` / `finance.ap.view`), aturan jatuh tempo yang sama dengan pengingat aturan |
| `FABRIC_NEED`, `ACCESSORY_NEED`, `PRODUCTION_GAP` | Set kondisi staged `DONE` terbaru (milik siapa pun yang berhak; label "data analisis per <waktu>"), dicek ulang langsung lewat `staged_recheck` sebelum dibuka sebagai alert |
| Pengingat pribadi owner | `erp.manual_reminders` milik owner, `status='OPEN'`, `due_at` tiba |

Analisis otomatis: `cp7-alert-analysis` memulai satu analisis staged sebagai owner lewat RPC mulai yang sudah ada bila tidak ada
analisis owner yang sedang berjalan; penjalan server K4 menyelesaikannya. Batas 8 detik per langkah dan semua pemeriksaan
sumber/otoritas/hash tetap.

### Alur kirim (tiap menit)

1. Lock advisory per tugas (`CP7:ALERT:COLLECT`, `CP7:WA:SEND`); tick kedua yang bersamaan langsung selesai.
2. Settings mati atau kunci tidak ada → outbox ditandai `DISABLED`; tidak ada permintaan.
3. Ambil outbox yang menunggu. Cek ulang tiap baris ke sumbernya sekarang (alert masih `OPEN` dan sumbernya masih terbuka;
   pengingat pribadi masih `OPEN`). Yang sudah beres → `RESOLVED_BEFORE_SEND` dengan alasan.
4. Jam tenang → `HELD_QUIET`, diproses lagi sesudah jam tenang dengan cek ulang.
5. Gabung yang lolos jadi satu pesan, per jenis, paling banyak `max_items` baris lalu "dan N lainnya", maksimal 1.000 karakter.
   Sesudah `burst_after_per_day` pesan, gabung per `burst_merge_minutes`. Tidak ada yang dibuang.
6. Kirim satu pesan per tick: `net.http_get('https://api.callmebot.com/whatsapp.php', phone, text, apikey)`. Kunci dibaca dari
   Vault di dalam fungsi `security definer` milik `cp7_alert`; tidak pernah ditulis ke tabel ERP atau log. pg_net mengirim
   sesudah transaksi commit, jadi transaksi yang batal tidak mengirim apa pun.
7. `wa_reconcile`: HTTP 200 → `PROVIDER_ACCEPTED`; HTTP lain → `PROVIDER_REFUSED`, outbox menunggu lagi; tidak ada jawaban
   sesudah 10 menit → `UNKNOWN`, tidak dikirim ulang otomatis, owner menandai di layar.
8. Ulangan: alert yang masih `OPEN` dan sudah dikirim masuk outbox lagi bila `repeat_minutes` lewat.

Ringkasan: per slot `digest_times`, semua alert `OPEN` dan pengingat pribadi owner yang terbuka; tidak memakan jeda ulang;
`NOTHING_DUE` tanpa pesan.

Pesan uji: `erp_cp7_send_wa_test_v1`, satu pesan tetap, paling banyak 3 per jam.

### Keamanan dan izin

- RPC pengaturan, kunci dan uji hanya owner (`erp.require_owner_admin()` plus peran OWNER). `erp_cp7_get_alerts_v1` mengikuti
  izin baca per jenis (gudang/bahan untuk stok, `finance.ar.view`/`finance.ap.view`, izin analisis untuk kebutuhan produksi).
- Kunci: Vault, tulis-saja; tidak ada di repo, chat, artifact CI, outbox atau dispatch. Uji mencari nilai kunci di semua tabel
  `cp7_*`/`erp` dan log job.
- `net.http_request_queue` menyimpan URL berisi kunci sampai permintaan diproses; hanya superuser/peran Supabase yang bisa
  membacanya. Batas ini dicatat; alternatifnya Edge Function dengan secret bila auditor menolak.
- `SUMMARY` menyembunyikan `party_names` (supplier, pelanggan, mandor); nama kain/barang tetap.
- Pengingat pribadi staf tidak pernah dibaca.
- Tidak ada trigger di tabel bisnis Native. Satu-satunya trigger baru ada di `cp7_alert_native.alerts`.

### Uji (sebelum pemasangan; tidak ada pesan sungguhan)

Server CallMeBot palsu berjalan sebagai kontainer di jaringan docker stack Supabase CI. Uji kelayakan WA-0 (workflow "CP7 WA
Forward") memastikan dulu bahwa pg_net dan Vault tersedia dan pg_net bisa melayani database salinan uji.

| Uji | Yang dibuktikan |
|---|---|
| Native per jenis sumber | Muncul di `alerts`, masuk WA; isi sama dengan layar asalnya (Ringkasan Gudang, AR/AP, analisis) |
| Native: pengingat pribadi owner jatuh waktu; milik staf | Terkirim; milik staf tidak pernah masuk outbox |
| Native: transaksi yang membuka alert lalu batal | Tidak ada outbox, tidak ada permintaan |
| Native: beres sebelum kirim | `RESOLVED_BEFORE_SEND` dengan alasan |
| Native: muncul lagi sesudah beres | Episode baru, terkirim lagi |
| Native: ulang belum lewat / sudah lewat | Tidak dobel / sekali |
| Native: banyak dalam satu menit; lewat 30 pesan sehari | Satu pesan; digabung tiap 30 menit; jumlah outbox = terkirim + tergabung + beres |
| Native: jam tenang; ringkasan | `HELD_QUIET` lalu kirim 06:00; ringkasan memuat semua yang terbuka |
| Native: 200 / 500 / diam | `PROVIDER_ACCEPTED` / `PROVIDER_REFUSED` lalu kirim lagi / `UNKNOWN` tanpa kirim ulang |
| Native: mati, tanpa kunci | Tidak ada permintaan |
| Native: kunci | Tidak terbaca lewat RPC mana pun; tidak ada di tabel, outbox, dispatch, log |
| Native: privasi dan izin | `SUMMARY` tanpa nama pihak; non-owner ditolak di RPC pengaturan; daftar Pengingat sistem mengikuti izin baca |
| Native: Ringkasan Gudang | Uji gudang lama lulus tanpa diubah sesudah `low_hit` dipindah ke fungsi bersama |
| Race | Dua tick bersamaan; ringkasan dan tick; alert dibuka saat tick berjalan; stok diterima saat tick: satu dispatch, tidak dobel, tidak ada outbox yatim |
| HTTP Auth nyata | Owner set kunci/aktifkan/kirim uji; staf ditolak 42501; daftar Pengingat sistem per peran |
| Browser desktop + HP | Menu Reminder: Pengingat sistem; tab Sambungan WhatsApp: isi kunci, kirim uji (server palsu), atur, riwayat, matikan |
| Pasang/copot | Bundle terpasang di atas tumpukan CP7 lengkap; pencopotan memulihkan katalog, jadwal dan isi `cp7_*` lain persis |

### Pemasangan

Ikut CP7C (ditahan, D13-9a): pg_cron, pg_net dan Vault aktif di Enteng (dicek saat preflight); pemasangan sesudah backup awal
terverifikasi. Pesan sungguhan pertama hanya **pesan uji** yang ditekan owner sendiri. Penulis tidak mengirim pesan apa pun.

### Belum pasti (dicek saat pembuatan atau pemasangan)

- Format dan metode API CallMeBot (GET dengan `phone`, `text`, `apikey` menurut tutorial; sumber lain menyebut POST) serta
  teks jawaban suksesnya. Desain ini hanya memakai HTTP 200 sebagai tanda diterima.
- Batas kirim CallMeBot (tidak ditemukan angka resmi). Bawaan: satu pesan per menit, digabung tiap 30 menit sesudah 30
  pesan sehari.
- Apakah "pemakaian pribadi" mencakup pengingat usaha ke nomor owner sendiri. Owner memilih CallMeBot dengan catatan ini.
- `STOCK_AT_REORDER_POINT`: ada atau tidaknya pembaca saldo per lokasi tanpa hitungan baru (lihat tabel sumber).
- Kewajiban lain (`other-obligation-source.sql`) masih draf; ditambahkan sebagai jenis alert begitu sumbernya dipasang.

Sumber: https://www.callmebot.com/blog/free-api-whatsapp-messages/ ; https://www.callmebot.com/tag/free/ (lewat pencarian,
19 Okt 2026). Perbandingan pilihan: `WA_PILIHAN_PENGIRIMAN_20261019.md`.
