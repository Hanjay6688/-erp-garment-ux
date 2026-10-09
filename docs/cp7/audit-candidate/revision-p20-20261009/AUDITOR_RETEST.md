# Uji ulang P20 — kandidat revisi `870d4f79` (sesi auditor terpisah)

Dokumen ini untuk **auditor di sesi terpisah**, bukan writer. Audit P20 atas `2e605bb7` memberi putusan **HOLD**
(`audit/astra-p20-2e605bb7-20261009`, `audit/astra_p20/REPORT.md` dan `WRITER_HANDOFF.md`). Handoff auditor meminta:
"Saat kandidat revisi diserahkan, retest F01–F05 dan bagian yang mungkin terdampak perubahan. Tidak perlu mengulang
seluruh kasus yang aman tanpa alasan." Perbaikan writer adalah kandidat baru; hasil writer di paket ini bukan
penerimaan.

## Paste block untuk membuka sesi auditor

> Kamu auditor independen untuk uji ulang P20 CP7 ERP Garment (repo `Hanjay6688/-erp-garment-ux`, cabang
> `claude/new-session-deapao`). Kandidat revisi adalah commit sumber `870d4f791bc72159f07ed7bd6a17275c19c5ddc7`
> (tree `2248685e0b4e65dac26db7aacc808f2c6da9c51d`), tercatat di
> `docs/cp7/audit-candidate/revision-p20-20261009/CI_RECEIPT.json`. Uji commit itu, bukan HEAD lain; commit sesudahnya
> hanya dokumen — buktikan sendiri dengan `git diff --name-only 870d4f79 HEAD` (semua harus di bawah `docs/`). Baca
> `docs/AUDIT_PANDUAN_PRO_MAX.md`, laporan dan handoff audit P20 di cabang `audit/astra-p20-2e605bb7-20261009`
> (`audit/astra_p20/REPORT.md`, `WRITER_HANDOFF.md`), lalu `README.md` dan `AUDITOR_RETEST.md` di folder paket revisi.
> Uji ulang F01–F05 dengan kriteria retest di handoff itu memakai oracle auditor sendiri, ditambah regresi area yang
> disentuh perubahan (daftar di `AUDITOR_RETEST.md`). Selisih sumber dari `2e605bb7` ada di `SOURCE_DELTA.json`.
> Batas: jangan mengubah `main`, deployment Cloudflare, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy
> ERP-Garment (`vlxdhpkjeevubjxexnfo`, read-only) atau produksi; jangan push ke `claude/new-session-deapao`,
> `cp7/integration` atau cabang audit P20 lama (pakai cabang audit baru); jangan memasang jadwal pg_cron atau backup
> malam di database mana pun selain salinan sekali pakai; jangan mengirim pesan ke orang lain; jangan meminta
> password/token/kunci; jangan melonggarkan oracle/guard; simpan log gagal pertama. Keputusan owner yang sudah
> disahkan tidak dibuka ulang. Area optimasi timeline PR44 tidak boleh diterima oleh auditor yang menulisnya.
> `production_go:false` tetap.

## Yang diuji ulang

| Temuan | Kriteria retest dari handoff auditor | Yang berubah di `870d4f79` | Titik awal (bukan bukti lulus) |
|---|---|---|---|
| F01 BLOCKER kapasitas lintas versi | v1/v2 dan v2/v1 yang tumpang tindih tidak dapat commit total >60; v2/v2 tetap lulus; 59+1 kontrol sah; rollback pemenang pertama membolehkan kapasitas dipakai kembali; bukan sekadar peringatan | `scripts/cp7-src/plan-native/commands.sql` (`cp7_plan_native.apply`): kunci `CP7:PLAN_CAPACITY` sesudah kunci roll, izin diperiksa ulang sesudah kunci, kapasitas sisa dihitung sebelum dan sesudah penulis Native, lebih → 40001 `CP7_PLAN_CAPACITY_USED`; `staged.sql` hanya komentar; pesan layar `src/lib/planV2Messages.ts` | `scripts/cp7_p19_plan_v2_cases.py` (`P19P_V1_V2_SHARED_CAPACITY`, `P19P_RACE_V1_HOLDS_V2_REFUSED`, `P19P_RACE_V2_HOLDS_V1_REFUSED`, `P19P_RACE_V1_ROLLBACK_FREES_CAPACITY`); probe auditor `astra-p20-plan-race.yml` / `AS20-32` |
| F02 MAJOR bersyarat cron dua database | Pemasangan B tidak mengubah A; pemasangan ulang idempoten; uninstall hanya menghapus job target | `scripts/cp7_schedule.py`: nama job `<jadwal>@<database>`, job bernama sama milik database lain ditolak sebelum perubahan | `K3C_RACE_CRON_TWO_DATABASES`; probe auditor `AS20-43` |
| F03 MINOR receipt backup tertimpa | Benturan ditolak sebelum menimpa, atau setiap percobaan bernama unik; percobaan gagal mempertahankan dump **dan** receipt valid lama; 15 restore nyata → 14 malam disimpan, malam gagal tidak memangkas | `scripts/cp7_nightly_backup.py`: nama = detik WIB + token acak, nama yang ada ditolak, receipt diklaim eksklusif | `K3C_RACE_BACKUP_RETRY_SAME_SECOND`, `K3C_RACE_NIGHTLY_BACKUP_VERIFIED`; probe auditor `AS20-45` |
| F04 MINOR batas detektor | Jangan menyebut verifikasi membuktikan seluruh isi indeks semantik; immutable guard tidak dilemahkan | Hanya deklarasi `docs/cp7/k3/K3_CLEANUP.json` (`not_rederived_before_removal`); perilaku tidak berubah | Probe auditor `AS20-39` dengan dan tanpa trigger immutable |
| F05 MINOR gate bukti | `cp7_probe_evidence_test.py` menjalankan seluruh kontrol negatif asli; metadata expected cocok dengan jumlah kasus sebenarnya tanpa mengurangi uji | `scripts/cp7_probe_evidence_test.py`, `.github/workflows/claude-p08-shell.yml`, `scripts/cp7_f04_schedule_probe.py` (70 → 71), `scripts/cp7_p18_full_cycle_probe.py` (`cases.EXPECTED`) | Workflow `CP7 Shell S0 (Claude branch)` di receipt |

## Regresi yang mungkin terdampak

- **Rencana v1 lama** (`plan39`, suite PL Native Planning): apply v1 sekarang menunggu kunci kapasitas bersama dan bisa
  menolak 40001. Periksa replay (UUID sama → hasil sama), larangan dua rencana atas potongan yang sama, izin dicabut
  sesudah kunci, dan v2/v2 tetap seperti sebelumnya. Periksa juga apakah urutan kunci (permintaan → roll → kapasitas →
  target → versi) bisa membuat deadlock dengan jalur lain yang mengambil kunci yang sama.
- **Hitungan "rencana lain"**: v1 menghitung potongan semua rencana lain yang grup Native-nya belum `material_issue_posted`;
  v2 menghitung intent lain menurut aturan snapshot-nya. Periksa bahwa grup yang bahannya sudah dikeluarkan tidak
  dihitung dua kali (sudah tercermin di kapasitas Original) dan grup draf Native yang sudah dihapus tidak menahan
  kapasitas (kedua versi menggabungkan intent dengan `erp.cutting_groups` yang masih ada).
- **Jadwal**: `K3C_RACE_PG_CRON_FIRES` (job sungguhan berjalan lalu dicopot) dengan nama job baru; `install` tetap
  menolak tanpa `--installation-approved`.
- **Backup**: rotasi 14 malam terverifikasi memakai nama berkas baru; malam gagal tidak memangkas.
- **Pesan layar**: kalimat penolakan kapasitas v1 sama dengan v2 (`src/lib/clientError.test.ts`).
- Area lain yang tidak disentuh `SOURCE_DELTA.json` boleh tidak diulang; tulis BELUM DIULANG, bukan LULUS.

## Bukti writer (untuk diuji ulang, bukan diterima begitu saja)

- `CI_RECEIPT.json`: 15/15 workflow dan 43/43 job pada `870d4f79`.
- `SOURCE_DELTA.json`: 28 berkas berubah dari `2e605bb7` (15 bukan dokumen).
- `../../evidence/p20-audit-20261009/README.md`: run auditor yang menjadi kegagalan pertama F01–F05.
- Ketiga balapan F01 gagal pada apply v1 lama ketika dicoba writer di salinan lokal; itu bukan bukti CI dan perlu
  dibuktikan sendiri bila dipakai.

## Hasil yang diminta

1. Per temuan F01–F05: DITUTUP / MASIH TERBUKA, dengan run, kasus dan oracle auditor.
2. Regresi di atas: LULUS / GAGAL / BELUM DIULANG, dengan alasan.
3. Temuan baru bila ada (ID, keparahan, reproduksi, bukti, dampak).
4. Vonis kandidat revisi dan syarat sebelum owner memberi izin memasang jadwal pembersihan dan backup malam. Penerimaan
   area PR44 tetap memerlukan auditor lain.
