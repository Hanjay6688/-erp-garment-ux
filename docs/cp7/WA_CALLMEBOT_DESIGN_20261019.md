# Desain: pengingat ERP ke WhatsApp owner lewat CallMeBot (D17-3)

Status: **desain**. Belum dibuat, belum dipasang. Keputusan owner D17-3 (19 Okt 2026): "yaudah desain callmebot buat gw".

## Untuk owner (ringkas)

**Hasilnya:** dua kali sehari (bawaan jam 08.00 dan 15.00 WIB, bisa diubah di aplikasi) WhatsApp Bos menerima satu pesan
ringkasan dari nomor CallMeBot, misalnya:

```
ERP Enteng · Pengingat 20 Okt 08.00
• 3 tagihan supplier jatuh tempo ≤ 3 hari: Rp 12.450.000
• 1 piutang pelanggan lewat jatuh tempo: Rp 4.200.000
• 2 PO kekurangan kain
• 1 PO kekurangan aksesori
Rincian: buka ERP > Pengingat
```

- **Gratis.** CallMeBot gratis, dan pengirim jalan di Supabase yang sudah dipakai.
- **Yang sudah selesai tidak ditagih.** Tiap pengingat diperiksa ulang ke data terbaru tepat sebelum dikirim, seperti aturan
  Bos 8 Okt.
- **Tidak dobel.** Satu kejadian hanya masuk satu kali. Yang masih terbuka muncul lagi di ringkasan berikutnya sesuai
  aturan jeda yang sudah ada.
- **Bisa dimatikan** kapan saja dari layar "Sambungan WhatsApp" (satu tombol).
- **Hanya ke nomor Bos sendiri.** CallMeBot memang hanya mengirim ke nomor yang mendaftar.

**Yang perlu diketahui:**

- Isi pesan lewat server CallMeBot (pihak ketiga). Karena itu bawaannya **Ringkas**: hanya jumlah dan total, tanpa nama
  supplier, pelanggan atau mandor. Bisa diganti ke **Rinci** di aplikasi.
- Situs CallMeBot menulis API gratisnya "hanya untuk pemakaian pribadi" dan tidak menjanjikan layanan selalu jalan. Kalau
  CallMeBot mati, pengingat tetap ada di ERP dan layar menulis "WA gagal terkirim jam …". Penggantinya nanti (misalnya
  Telegram) memakai alur yang sama; hanya bagian pengirimnya yang diganti.
- Kunci CallMeBot diketik Bos sendiri di layar ERP saat pemasangan. Tidak pernah dikirim lewat chat dan tidak tersimpan di
  kode.

**Cara pasang nanti (saat CP7C dibuka):**

1. Di HP Bos: simpan nomor CallMeBot (nomornya dicek di situs CallMeBot saat itu karena bisa berganti), kirim kalimat
   persetujuan yang ditulis di situsnya, lalu tunggu balasan berisi kunci (API key).
2. Di ERP, layar "Sambungan WhatsApp": isi nomor WA Bos dan kunci tadi, tekan **Kirim pesan uji**. Kalau pesan uji masuk,
   tekan **Aktifkan**.

## Desain teknis

### Prinsip

- Sambungan ini adalah tujuan baru untuk mesin pengingat yang sudah ada (`scripts/cp7-src/reminders/`). Kondisi, episode,
  kebijakan (ambang, jeda, jam tenang) dan pemeriksaan ulang tidak diubah. Tujuan baru ini menggantikan `LOCAL_TEST_SINK`.
- Semuanya di database: pg_cron menjadwalkan, pg_net mengirim permintaan web, Supabase Vault menyimpan kunci. Tidak perlu
  Edge Function atau server tambahan.
- Paling banyak satu kali kirim per kejadian (at-most-once). Kirim yang hasilnya tidak diketahui tidak dikirim ulang otomatis.
- Tidak ada angka yang dihitung oleh pengirim. Pengirim hanya membaca kondisi yang sudah lolos pemeriksaan ulang.

### Komponen

| Komponen | Isi |
|---|---|
| `cp7_reminder_native.wa_self_settings` (revisi, append-only, seperti `rule_policies`) | `enabled`, `phone_e164` (nomor owner), `detail` (`SUMMARY`/`DETAILED`), `schedule` (jam kirim WIB, bawaan `08:00`,`15:00`), `max_items` (bawaan 10), `max_per_day` (bawaan 4), `actor` (auth id owner yang mengaktifkan), `reason`, `created_at` |
| Vault secret `cp7_callmebot_apikey` | Kunci CallMeBot. Ditulis lewat RPC khusus owner (`erp_cp7_set_wa_self_key_v1`). Tidak ada RPC yang membacanya kembali; layar hanya menampilkan "kunci terpasang, diganti <tanggal>" dan 2 karakter terakhir |
| Lingkungan klaim baru `CALLMEBOT_WA_SELF` | `staged_claims.environment` dan `local_claims.environment` menerima `LOCAL_TEST_SINK` atau `CALLMEBOT_WA_SELF`. Binding baru dengan lingkungan ini hanya bisa dibuat owner dan hanya satu yang aktif |
| `cp7_reminder_native.wa_self_dispatches` | Satu baris per pesan: `id`, `slot` (tanggal + jam jadwal WIB, unik), `claim_ids[]`, `body`, `body_sha256`, `net_request_id`, `status` (`QUEUED`, `PROVIDER_ACCEPTED`, `PROVIDER_REFUSED`, `UNKNOWN`, `NOTHING_DUE`, `SKIPPED_DISABLED`, `SKIPPED_LIMIT`), `http_status`, `provider_text` (dipotong, tanpa kunci), `created_at`, `finished_at`. Append-only kecuali transisi status yang dijaga trigger |
| `cp7_reminder_native.wa_self_tick()` (pg_cron, tiap 5 menit) | Lihat alur. Berjalan sebagai peran `cp7_reminder` dengan identitas owner dari settings (pola penjalan server K4: akses dicek ulang tiap unit) |
| `cp7_reminder_native.wa_self_reconcile()` (pg_cron, tiap menit) | Membaca `net._http_response` untuk `net_request_id` yang masih `QUEUED` |
| Layar "Sambungan WhatsApp" (`src/cp7/Cp7Shell.tsx`, halaman yang sudah ada) | Aktif/mati, nomor (disamarkan), kunci terpasang ya/tidak, Ringkas/Rinci, jam kirim, **Kirim pesan uji**, riwayat 20 kiriman terakhir dengan status |

### Alur satu slot (misalnya 20 Okt 08:00 WIB)

1. `wa_self_tick` melihat slot yang jatuh waktunya dan belum punya baris di `wa_self_dispatches`. Lock advisory per slot
   (`CP7:WA_SELF:<slot>`); dua tick bersamaan menghasilkan satu baris.
2. Kalau settings mati, kunci tidak ada atau batas harian tercapai: tulis `SKIPPED_*`, selesai.
3. Kumpulkan kondisi terbuka: AR_DUE/AP_DUE dari pembaca langsung v1 (`receivable-source.sql`, `payable-source.sql`), serta
   PRODUCTION_GAP/FABRIC_NEED/ACCESSORY_NEED dari set kondisi staged terakhir yang `DONE` milik owner. Kondisi staged tetap
   memakai label "data analisis per <waktu>".
4. Klaim tiap kondisi lewat jalur klaim yang sudah ada dengan lingkungan `CALLMEBOT_WA_SELF`. Di sini pemeriksaan ulang ke
   data sekarang berjalan (`staged_recheck` / `recheck`). Yang hasilnya bukan `STILL_OPEN` tidak masuk pesan dan dicatat
   alasannya. Kebijakan jeda dan jam tenang berlaku seperti sekarang. Kunci kejadian (`occurrence_key`) mencegah dobel.
5. Kalau tidak ada yang lolos: `NOTHING_DUE`, tanpa pesan.
6. Susun satu pesan: kelompokkan per jenis. `SUMMARY` hanya jumlah dan total rupiah; `DETAILED` menambah nama dan nomor
   dokumen, paling banyak `max_items` baris lalu "dan N lainnya". Maksimal 1.000 karakter.
7. Kirim: `net.http_get('https://api.callmebot.com/whatsapp.php', params := phone, text, apikey)`. Kunci dibaca dari Vault di
   dalam fungsi `security definer` milik `cp7_reminder`, tidak pernah ditulis ke tabel ERP atau log. Baris dispatch menjadi
   `QUEUED` dengan `net_request_id`. Klaim tetap `CLAIMED` dan terikat ke dispatch.
8. `wa_self_reconcile`:
   - HTTP 200 → `PROVIDER_ACCEPTED`, klaim selesai (status klaim baru `PROVIDER_ACCEPTED`).
   - HTTP lain → `PROVIDER_REFUSED`, klaim `SUPPRESSED` dengan alasan. Kondisinya bisa ikut slot berikutnya karena belum
     pernah terkirim.
   - Tidak ada jawaban sesudah 10 menit → `UNKNOWN`, klaim `UNKNOWN`. Tidak dikirim ulang otomatis. Layar meminta owner
     menandai "masuk"/"tidak masuk" (memakai tabel resolusi yang sudah ada).
9. Tiga slot berturut-turut gagal: layar dan halaman Pengingat menampilkan peringatan; pengiriman tetap dicoba di slot
   berikutnya.

Pesan uji: tombol owner memanggil `erp_cp7_send_wa_self_test_v1`, satu pesan tetap ("ERP Enteng: pesan uji <jam>"), dicatat
sebagai dispatch jenis `TEST`, paling banyak 3 per jam.

### Keamanan dan izin

- Semua RPC baru hanya owner (`erp.require_owner_admin()`) dan mengikuti fasad CP7: `authenticated` hanya memanggil RPC
  publik `erp_cp7_*`, fungsi di `cp7_reminder_native` tidak bisa dipanggil peran browser (FABLE-012 tetap berlaku).
- Kunci: Vault, tulis-saja. Tidak ada di repo, di chat, di artifact CI, atau di `wa_self_dispatches`. Pemeriksa di uji mencari
  nilai kunci di semua tabel `cp7_*`/`erp` dan log job: harus nol.
- `net.http_request_queue` menyimpan URL berisi kunci sampai permintaan diproses, dan hanya bisa dibaca superuser/peran
  Supabase. Ini batas yang diterima dan dicatat. Alternatifnya Edge Function dengan secret, kalau auditor menolak batas ini.
- Isi `SUMMARY` tidak memuat nama orang/usaha, nomor HP atau alamat.
- Izin baca per jenis tetap: AR_DUE hanya kalau owner punya `finance.ar.view`, AP_DUE `finance.ap.view` (sama dengan
  `rule-policy.sql`).

### Uji (sebelum pemasangan; tidak ada pesan sungguhan)

CI memakai server CallMeBot palsu (HTTP lokal di runner) yang mencatat permintaan dan bisa menjawab 200, 500, atau diam.
pg_net diarahkan ke alamat palsu itu lewat setting uji; alamat asli hanya di pemasangan.

| Uji | Yang dibuktikan |
|---|---|
| Native: kondisi selesai sebelum slot | Tidak masuk pesan; alasan `RESOLVED_NOW` tercatat |
| Native: dua slot berturutan | Kondisi yang sama tidak dobel dalam jeda; muncul lagi sesudah jeda |
| Native: 200 / 500 / diam | `PROVIDER_ACCEPTED` / `PROVIDER_REFUSED` lalu ikut slot berikut / `UNKNOWN` tanpa kirim ulang |
| Native: mati, tanpa kunci, batas harian, jam tenang | Tidak ada permintaan ke server palsu |
| Native: kunci | Tidak terbaca lewat RPC mana pun; tidak ada di tabel ERP, dispatch atau log |
| Native: `SUMMARY` | Pesan tidak memuat nama supplier/pelanggan/mandor dari fixture |
| Native: izin | Non-owner ditolak di semua RPC baru; AR/AP mengikuti izin baca |
| Race: dua tick bersamaan | Satu dispatch per slot, satu permintaan |
| Race: kondisi dibayar saat tick berjalan | Ikut kirim hanya kalau masih terbuka saat diklaim; tidak ada klaim yatim |
| HTTP Auth nyata | Owner bisa set kunci/aktifkan/kirim uji; staf ditolak 42501 |
| Browser desktop + HP | Layar Sambungan WhatsApp: isi kunci, kirim uji (ke server palsu), riwayat, matikan |

### Pemasangan

Ikut CP7C (ditahan, D13-9a): butuh pg_cron, pg_net dan Vault aktif di Enteng (dicek saat preflight), dan pemasangan sesudah
backup awal terverifikasi. Pesan sungguhan pertama hanya **pesan uji** yang ditekan owner sendiri di layar. Penulis tidak
mengirim pesan apa pun.

### Belum pasti (dicek saat pembuatan atau pemasangan)

- Format dan metode API CallMeBot (GET dengan `phone`, `text`, `apikey` menurut tutorial; sumber lain menyebut POST) serta
  teks jawaban suksesnya. Dicek di situs CallMeBot saat pembuatan; status sukses di desain ini hanya HTTP 200.
- Batas kirim CallMeBot (tidak ditemukan angka resmi). Bawaan desain: paling banyak 4 pesan per hari.
- Apakah "pemakaian pribadi" mencakup pengingat usaha ke nomor owner sendiri. Owner memilih CallMeBot dengan catatan ini.

Sumber: https://www.callmebot.com/blog/free-api-whatsapp-messages/ ; https://www.callmebot.com/tag/free/ (lewat pencarian,
19 Okt 2026). Pilihan lain dan perbandingannya: `WA_PILIHAN_PENGIRIMAN_20261019.md`.
