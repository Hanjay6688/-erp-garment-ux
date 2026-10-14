# Serah-terima penulis — addendum silang CP1–CP7

Kandidat tetap `0b7049d9203bac52b47a4c89f3e0d75646067a8f`. **TAHAN penerimaan penuh tetap berlaku.** Lima akar runtime Astra FIN01/RWK01/STK01/FIN02/HPP01 belum mempunyai kandidat perbaikan pada pemeriksaan cabang penulis terakhir; daftar perbaikan dan expected pada `../HANDOFF_WRITER_CP17_CONTINUATION.md` tetap berlaku.

Yang diperbarui dari handoff lama:

1. Fable kini **laporan final**, bukan draft. Semua 12 temuan dipetakan di `FABLE_FINAL_DISPOSITIONS.md`;31 dugaan terdahulu tetap punya disposisi masing-masing. Dugaan duplicate attendance bukan bug terbukti pada rute yang ditolak probe Astra; overlap tujuan dua pool juga bukan otomatis double-cost. Jangan mengerjakan dugaan tersebut seolah sudah terkonfirmasi.
2. CP1 mendapat bukti hosted Fable16/16 cocok baseline. CP2 kini punya laporan restore PG16 lokal; jangan lagi tulis “tidak ada restore”. Namun tidak ada bukti kesetaraan lengkap definisi/owner/ACL, layanan Supabase asli atau round-trip Storage. Field `postgres_image` pada verifier adalah konstanta. Lihat `CP1_CP2_CROSSCHECK.md`; penerimaan CP2 penuh masih kurang bukti tersebut.
3. FABLE-012: dua uji Astra PASS. Enam percobaan non-owner/nonaktif ditolak; owner sah bisa melakukan reopen native dalam kontrol transaksi. Catat exposed schemas dan kebijakan native entry point saat rilis; pengerasan grant harus menjaga caller/helper sah. Bukan108 exploit terkonfirmasi, bukan alasan otomatis menaikkan S1. Detail dan Original ada pada `RBAC_CROSSCHECK.md`.
4. Indeks39 ACC + 36 LAU + 22 ALL selesai: `C6_75_ALL22_CROSSWALK.json`/`.md`.40 baris punya kasus bernama;57berbasis profil review. Semua 97mempunyai disposisi, tetapi bukan97 klaim lulus semua klausul. Gunakan gap/oracle per baris saat menyiapkan kandidat perbaikan.
5. Koreksi kalimat handoff CP5 lama: operand hash guard cutting sudah diketahui berbeda karena delta owner P12/P13 yang sah. `CP5_EXACT_REVIEW.md` adalah penjelasan final; raw program tetap INCOMPLETE. Jangan revert guard produk untuk menyamakan pin predecessor. Kesalahan manifest artifact final-gaps dan label provenance runner juga diungkap dalam addendum; tidak ada Original/hasil merah yang ditimpa.

Insiden Fable yang perlu diteruskan kepada pemegang backup: sebagian passphrase CP2 disebut tercetak di log sesi Fable. Anggap kunci tersebut terpapar; jangan pakai ulang untuk backup baru. Tidak ada nilai kunci dalam paket ini dan Astra tidak mengambil kunci/Drive.

Untuk kandidat revisi: berikan commit/tree, diff produk, expected sumber/role/tanggal/lineage, kasus asal yang tetap dipertahankan, kontrol positif-negatif dan bukti full restoration. **Lima akar runtime dan tiga gap alur tetap mengikuti handoff utama.** CP7C tetap HOLD; A2 diterima OPEN non-blocker D13-10; A6/P11 dan F-OPS-05 yang sudah selesai tidak dibuka ulang. Laporan ini tidak memberi izin produksi.

Siap diteruskan owner; auditor tidak mengirim pesan kepada penulis/Fable.
