# Pilihan cara kirim pengingat ke WhatsApp (19 Okt 2026)

Owner: "pikirin ya aplikasi buat kirim ke wanya ya". Dokumen ini membandingkan pilihan; belum ada yang dipasang.

## Keadaan sekarang di aplikasi

Mesin pengingat sudah ada: memilih pengingat yang jatuh tempo, menyusun teksnya, dan memeriksa ulang kondisi sebelum
"dikirim". Pengirimannya masih **pratinjau lokal** ("PRATINJAU LOKAL · TIDAK DIKIRIM"); tombol "Kirim WhatsApp" sengaja
mati (`src/cp7/notification.ts`). Tidak ada sambungan ke layanan WhatsApp, nomor penerima, jadwal kirim otomatis atau
bukti terkirim. Rancangan sambungan lengkap ada sejak permintaan owner 28 Sep (`docs/cp7/framework-v2/06_RUSUK_KEBUTUHAN_OWNER.md`
bagian 8, `registries/owner_delta.json` OWN28-08); pengiriman nyata dijadwalkan di CP7C.

## Pilihan

Asumsi: 5–20 penerima (owner, admin, mandor, gudang), 10–100 pesan per hari (sekitar 300–3.000 per bulan).

| Pilihan | Biaya | Resmi | Otomatis | Yang perlu disiapkan | Risiko |
|---|---|---|---|---|---|
| A. Tombol "Kirim lewat WhatsApp" (tautan wa.me) | Rp0 | Ya (fitur "click to chat" WhatsApp) | Tidak: WhatsApp terbuka dengan pesan sudah terisi, orangnya tekan Kirim | Tidak ada; aplikasi hanya membuat tautan | Harus ada orang yang menekan kirim; terkirim dari HP yang dipakai |
| B. Bot Telegram | Rp0 | Ya | Ya, penuh | Tiap penerima pasang Telegram dan menekan Start sekali; pengirim di server (Supabase Edge Function atau Cloudflare Worker, paket gratis) | Bukan WhatsApp |
| C. WhatsApp resmi (Meta Cloud API), pesan dari bisnis | Sekitar Rp357 per pesan utilitas di Indonesia, jadi sekitar Rp107 rb–1,07 jt per bulan; PPN belum pasti | Ya | Ya, penuh | Akun Meta Business, nomor khusus, template pesan disetujui Meta, kartu pembayaran | Berbayar |
| D. WhatsApp resmi, hanya membalas orang yang chat dulu | Rp0 untuk 1.000 pesan pertama per bulan, lalu sekitar Rp357 per pesan | Ya | Hanya dalam 24 jam sesudah penerima chat ke nomor bisnis | Sama dengan C | Penerima harus chat ke nomor bisnis tiap hari; 100 pesan/hari melewati 1.000/bulan |
| E. Gateway tidak resmi (Fonnte, Wablas, Woowa, Watzap) | Fonnte ada paket gratis 1.000 pesan/bulan (teks saja); lainnya sekitar Rp25 rb–197 rb/bulan | Tidak | Ya | Menautkan nomor WhatsApp biasa lewat kode QR | Melanggar aturan WhatsApp (pesan otomatis lewat aplikasi tidak resmi); nomor bisa diblokir |
| F. Program sendiri (Baileys, whatsapp-web.js, WAHA) | Program Rp0 | Tidak | Ya | Server yang menyala terus (bukan Supabase/Cloudflare); server gratis tidak andal | Sama dengan E, ditambah server |

Server: pengiriman otomatis (B, C, D) cukup satu panggilan web dari Supabase Edge Function (paket gratis 500 rb
panggilan/bulan) atau Cloudflare Worker (paket gratis 100 rb permintaan/hari), dijadwalkan dengan pg_cron atau Cloudflare
Cron. Tidak perlu server tambahan.

## Kalau pengingat cukup dikirim ke HP owner sendiri

Owner: "ada app lain yg ngirim ke diri sendiri". Semua di bawah gratis dan otomatis; semuanya butuh pengirim terjadwal di
server (Supabase Edge Function + pg_cron, paket gratis), yang termasuk pekerjaan CP7C (ditahan, D13-9a).

| Pilihan | Resmi | Catatan |
|---|---|---|
| CallMeBot (WhatsApp ke nomor sendiri) | Bukan layanan WhatsApp/Meta; pihak ketiga | Daftar dengan mengirim satu kalimat persetujuan ke nomor CallMeBot, lalu dapat kunci; aplikasi mengirim lewat satu alamat web. Situsnya menulis API gratis ini "hanya untuk pemakaian pribadi" (belum jelas apakah pengingat usaha termasuk). Isi pesan (utang, stok) lewat server pihak ketiga. Kadang kunci baru keluar sesudah 24 jam. Tidak ada jaminan layanan |
| Bot Telegram ke diri sendiri | Ya | Owner pasang Telegram dan menekan Start pada bot sekali. Gratis penuh, tanpa pihak ketiga selain Telegram |
| ntfy (aplikasi notifikasi HP) | Proyek sumber terbuka | Pasang aplikasi ntfy, langganan satu "topik" rahasia. Server umum gratis tanpa daftar; siapa pun yang menebak nama topik bisa membaca, jadi nama topik harus rahasia |

Sumber (lewat pencarian, 19 Okt 2026; halaman tidak bisa dibuka langsung dari lingkungan ini):
https://www.callmebot.com/blog/free-api-whatsapp-messages/ ; https://www.callmebot.com/tag/free/ ;
https://docs.ntfy.sh/terms/ ; https://core.telegram.org/bots/faq

## Saran penulis

Dengan aturan owner "gamau keluarin duit 1000 pun":

1. **Sekarang: A (tombol wa.me).** Gratis, resmi, tanpa risiko nomor diblokir, tanpa server baru. Aplikasi menyiapkan
   daftar pengingat dan isi pesannya; admin atau owner menekan satu tombol per orang, WhatsApp terbuka, lalu tekan Kirim.
   Pemeriksaan ulang sebelum kirim tetap berjalan. Bisa dibuat dan diuji sebelum CP7C karena tidak menyambung ke layanan
   luar mana pun.
2. **Kalau harus otomatis dan tetap gratis: B (Telegram).** Resmi dan gratis penuh, tetapi bukan WhatsApp. Pengirim
   terjadwal di server masuk pekerjaan CP7C (ditahan, D13-9a).
3. **Kalau harus WhatsApp otomatis: C (resmi, berbayar).** Biayanya sekitar Rp357 per pesan.
4. **Tidak disarankan: E dan F.** Murah atau gratis, tetapi melanggar aturan WhatsApp; nomor usaha bisa diblokir.

## Batas riset

Fakta di atas diambil dari ringkasan mesin pencari atas halaman yang disebut di bawah; alat pembuka halaman gagal di
lingkungan ini, jadi tidak ada halaman yang dibuka langsung. Kurs: Rp17.950 per US$1 (JISDOR 15 Okt 2026, menurut berita).
Belum pasti: PPN 11% atas harga Meta; apakah nomor uji gratis Meta boleh dipakai sungguhan (Meta menyebutnya untuk
pengembangan); tanda "sent via fonnte" pada paket gratis Fonnte (sumbernya bertentangan); harga Wablas/Watzap dan reseller
berbeda antar sumber; satu tabel vendor masih menyebut template utilitas di dalam jendela 24 jam gratis, sedangkan halaman
Meta (lewat pencarian) menyebutnya berbayar sejak 1 Okt 2026. Harga harus dicek ulang di halaman resmi sebelum memilih C atau D.

## Sumber (diakses lewat pencarian, 19 Okt 2026)

- Harga Meta: https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing ;
  https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/non-template-messages
- Tarif Indonesia: https://www.gupshup.ai/resources/wp-content/uploads/2025/12/IDR_Jan2026.pdf ;
  https://chatmaxima.com/whatsapp-api-pricing/indonesia/ ;
  https://help-center.qontak.com/hc/en-us/articles/48430892733465-Latest-WhatsApp-Message-Prices-October-2026
- Mulai dan nomor uji: https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started
- Click to chat: https://faq.whatsapp.com/general/chats/how-to-use-click-to-chat/
- Aturan WhatsApp: https://www.whatsapp.com/legal/messaging-guidelines ; https://business.whatsapp.com/policy
- Gateway: https://fonnte.com/ ; https://docs.fonnte.com/language/en/ ; https://wablas.id/ ; https://woo-wa.com/ ;
  https://watzap.id/harga
- Telegram: https://core.telegram.org/bots/faq
- Jadwal dan batas gratis: https://supabase.com/docs/guides/functions/schedule-functions ;
  https://supabase.com/docs/guides/platform/manage-your-usage/edge-function-invocations ;
  https://developers.cloudflare.com/workers/platform/limits/
