# Putaran silang 2 CP7 — daftar butir

Dasar: keputusan owner D13-10..D13-13 (13 Okt 2026), disalin verbatim ke `../../OWNER_DECISIONS_20261008.md` dari
register Fable (`audit/fable_cp7/OWNER_DECISIONS_TO_AUDITOR_20261013.md`, commit `9fc44978`). Laporan yang dijawab:
Fable v1.1 (`audit/fable_cp7/AUDIT_FABLE_XC1_ae0214ad_v1.1.md`, commit `6e3a8983`). Laporan putaran 1 Astra belum masuk
saat kandidat ini dibuat.

Kandidat: **`0b7049d9203bac52b47a4c89f3e0d75646067a8f`**, tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`. Sama untuk Astra
dan Fable (D13-13). Kode produk (`supabase/`, `src/`, `scripts/cp7-src/`) identik dengan `ae0214ad` dan `7a0b4a90`.

| ID | Butir | Asal | Yang dikerjakan penulis | Bukti | Untuk Astra | Untuk Fable |
|---|---|---|---|---|---|---|
| R2-A6 | Cakupan pengganti `SALES_MANUAL_13`: kasus browser sungguhan P11 desktop dan HP yang menekan "Terapkan lusin baris N" | Fable v1.1 A6 TIDAK LENGKAP; owner D13-12(1), D13-9c | Dua kasus pengganti yang sudah terdaftar (`P11_DRAFT_BROWSER_DESKTOP`, `P11_DRAFT_BROWSER_MOBILE_RECOVERY`, `scripts/cp7_p11_drafts_browser.mjs`, fungsi `dozenHelper`) sekarang: menolak isian tidak sah tanpa mengubah qty (kosong, 1,1, 1.1, sisa 12, 0+0); qty tetap 13 sebelum tombol; 2 lusin + 1 = 25 dengan baris 2 tidak berubah dan total Rp520; tanpa geser horizontal di HP; kembali ke 13 lewat helper; simpan; baca ulang dari server `[2,13]`, stok `[17,28]`; form edit membaca 13 dari server. Produk tidak diubah. Harapan lama kasus tidak diubah. | Run `CP7 Pre-freeze UI Regression` dan `CP7 F03 Full Retained Components` di kandidat; tangkapan layar `P11_DOZEN_HELPER_{DESKTOP,MOBILE}.png` | **Silang:** jalankan ulang atau baca log per kasus; nyatakan LENGKAP / TIDAK LENGKAP. | Nyatakan LENGKAP / TIDAK LENGKAP (D13-12). |
| R2-F05 | F-OPS-05: tanda polos masih dihormati | Fable v1.1 A1.3; owner D13-12(2) | `scripts/cp7_nightly_backup.py`: `is_mark` hanya menerima tanda percobaan yang menyebut OID database itu sendiri; cabang tanda polos dihapus. `mark_scratch` wajib token 16 hex dan OID. Kasus baru `K3C_RACE_BACKUP_PLAIN_MARK_COPIED_ONTO_FOREIGN_KEPT` (k3-cleanup-25). Dua kasus lama yang memakai tanda polos sebagai "milik alat" diganti ke tanda ber-OID; harapannya tidak berubah (lihat catatan di bawah). | Run `CP7 P19 Analysis Job Transport` job `k3-cleanup-25` | **Silang:** urutan ASR-OPS-01-mu (situasi A–D) tetap tertutup dengan aturan tanda baru? | `XC1:PLAIN_MARK_COPIED_ONTO_FOREIGN` tanpa mengubah oracle harus PASS; 4 kasus XC1 lain dan 2 kasus backup core tetap PASS. |
| R2-REG | Register D13-10..D13-13 | Fable (catatan untuk penulis) | Disalin verbatim ke register kanonik sebelum kandidat dibuat. | `docs/cp7/OWNER_DECISIONS_20261008.md` | Untuk diketahui. | Cocokkan kata per kata dengan registermu. |
| R2-D11 | Pembanding terurut sebagai pelengkap diagnosis A2 | Owner D13-11 (izin) | **Tidak dipakai di putaran ini.** `state_difference` yang sudah terpasang sudah membedakan ORDER_ONLY dari CONTENT setiap kali grup gagal. Menambah pembanding di `cp6_auditor_runner.py` menyentuh semua workflow. `cp6_auditor_runner.py` dan `cp6_auditor_difference.py` tidak berubah sejak `ae0214ad`. | `git diff ae0214ad 0b7049d9 -- scripts/cp6_auditor_runner.py scripts/cp6_auditor_difference.py` kosong | Untuk diketahui. | Untuk diketahui. |
| A2 | Selisih akhir grup bayar supplier | Owner D13-10 | Keterbatasan terbuka yang tercantum, bukan syarat pembekuan. Diagnosis tetap terpasang. Dua kegagalan lama dan log aslinya tetap disimpan. | `CP7 Supplier Payment Create` di kandidat | Untuk diketahui. | Untuk diketahui. |

## Catatan F-OPS-05: dua kasus lama yang tandanya diganti

Keduanya dulu memakai tanda polos untuk mewakili "database sisa milik alat". Sesuai D13-12, tanda polos tidak lagi milik
alat, jadi bentuk tandanya diganti ke tanda percobaan dengan OID database itu sendiri. Harapan kasus tidak berubah dan
tidak ada yang dilonggarkan:

- `K3C_RACE_BACKUP_SCRATCH_NEVER_DROPS_ANOTHER_DATABASE`, bagian "sisa milik alat dipakai ulang lalu dihapus": tetap
  `scratch_before == OURS`, malam terverifikasi, `scratch_after == ABSENT`.
- `K3C_RACE_BACKUP_SCRATCH_OWNERSHIP_BY_OID` situasi A (urutan Astra): tetap `scratch_before == OURS`, pengganti
  tetap ada, `BACKUP_SCRATCH_REPLACED`, tidak ada yang diverifikasi atau dipangkas.

Perilaku tanda polos sekarang diuji terpisah di kasus baru, dengan harapan yang lebih ketat (database tetap utuh).

## Di luar kualifikasi (CP7C, ditahan D13-9a)

Sejak `ae0214ad`, cabang juga memuat alat backup CP7C yang ditahan: `scripts/cp7_offsite_backup*.py`,
`scripts/cp7_supabase_restore_drill.py`, `ops/backup-repo/*`, dan workflow `cp7-offsite-backup.yml`,
`cp7-backup-kit-check.yml`, `cp7-supabase-restore-drill.yml`. Tidak ada workflow kualifikasi yang memakainya. Push
kandidat ikut menjalankan `CP7 Offsite Backup` dan `CP7 Backup Kit Check`; hasilnya dicatat di `CI_RECEIPT.json` hanya
untuk diketahui. Alat offsite memakai aturan tanda yang sama, jadi paket CP7C perlu dikualifikasi ulang saat CP7C dibuka.

## Hasil auditor

| Auditor | Commit laporan | R2-A6 | R2-F05 | A2 | Catatan |
|---|---|---|---|---|---|
| Astra | `57ac8aab` (laporan terkunci), `fb24bd92` (pemeriksaan paket final) | **LENGKAP** | **DITUTUP** | MASIH TERBUKA, bukan penghalang (D13-10) | A1, A3, A8 DITUTUP; 141 eksekusi CI / 139 ID unik + 1 DOM; koreksi kalimat pergantian hari (92 eksekusi ulang, 41 ditandai rollover) sudah dimasukkan ke README. |
| Fable | `46fe722c` (v1.2 final), `c17a53b2`, `319e6624` (koreksi) | **LENGKAP** | **DITUTUP** | MASIH TERBUKA, bukan penghalang (D13-10) | R2-REG cocok kata per kata; tidak ada temuan baru; tidak ada bantahan terhadap Astra. Run pertama kasus Fable merah karena fixture Fable sendiri memakai tanda polos; fixture dibetulkan tanpa mengubah oracle, 5/5 PASS; kedua log disimpan. |

**Kedua auditor menutup R2-A6 dan F-OPS-05. CP7 dibekukan final pada `0b7049d9` (D13-13): `../../FREEZE_CP7_FINAL_20261014.md`.**
