# cp17 — penyelidikan satu job merah: `cp6-t3-aligned-install` (run 38522071779, job 115713835290)

Label: INDEPENDENT_SOURCE_REVIEW + FABLE (log dibaca per baris, bukan warna job). Kandidat beku 0b7049d9 / tree ce6aed0a. Ref yang didispatch: `claude/new-session-deapao` @ 00b0eb24 (workflow identik dengan kandidat beku untuk file ini).

## 1. Apa yang terjadi

Langkah "Rebuild to v2.6.20, align with hosted, continue the frozen path to AC" menjalankan `scripts/cp6_t3_aligned_chain.py`. Laporan `ALIGNED_CHAIN.json` menyatakan:

- `status = REFUSED_AT_STEP`
- `refused_step = "Apply exact AC temporal surface closure and verify 272 runtime objects"`
- pesan: `AC_VIEW_PREDECESSOR_MISMATCH: erp.v_payroll_nota_browser`
- detail: `source=t body=f owner=t acl=t options=t rls=t` (ACL expected = live = `{authenticated=r/postgres,postgres=arwdDxtm/postgres}`)

Artinya: migrasi AC (`supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql`, pemeriksaan predecessor di baris 1144–1151) menolak karena **sha256 badan view `erp.v_payroll_nota_browser` yang hidup** di basis "hosted-faithful" (dibangun ulang ke v2.6.20 lalu diselaraskan dengan metadata hosted G-01) **berbeda dari sha yang diharapkan** migrasi; sumber, owner, ACL, options, dan RLS cocok. Guard bekerja sesuai desain: migrasi menolak berjalan di atas predecessor yang tidak persis.

## 2. Fakta pendukung (diverifikasi dari pohon beku)

| Fakta | Nilai |
|---|---|
| Baris komentar penulis, `scripts/cp6_t3_aligned_chain.py:20` | "The frozen AC refuses on the aligned chain (run 35911530080); the T3 release package starts after AB." |
| Docstring skrip yang sama | "Label: T3_PREP (not release evidence)" ; "records PASS or the exact refusal. No guard is changed." |
| Workflow mem-pin lima checkout | writer ca7f0955, harness c6b0e4fb, candidate 25fa4736, base 1bdca376 (assert HEAD + tree 334629c6), auditor = ref yang didispatch |
| Artifact penulis yang diunduh | `actions/artifacts/10392910720` (AC native 200) |
| Salinan AC di `supabase/migrations/` | sha256 7b5690a2eddf6188… ; terakhir diubah f455f612 "normalize effective view ACLs", sebelumnya fde6c6a7, a5a76171, a46c5139 |
| Salinan AC di paket rilis `supabase/release/cp6-t3/` | sha256 871fb32b1d4a1e7f… (berbeda; teks badan view `v_payroll_nota_browser` dan hash-nya berbeda) |
| Paket rilis T3 (`cp6-t3-release-package.yml`) | memasang dari `supabase/release/cp6-t3/` (30 file AC..BF) **mulai setelah AB**, bukan lewat jalur aligned-install |
| Riwayat run workflow ini | tidak pernah sukses sejak dibuat 23 Sep 2026 (semua gagal/dibatalkan) — konsisten dengan komentar baris 20 |

## 3. Klasifikasi

**BUKAN temuan produk CP7, dan bukan penghalang.** Alasan:

1. Jalur `cp6-t3-aligned-install` adalah alat **persiapan T3 (T3_PREP)** era CP6 yang oleh penulis sendiri dicatat menolak di langkah AC sejak run 35911530080, dan jalur rilis sesungguhnya (paket `supabase/release/cp6-t3/`) **tidak** memakai jalur ini.
2. Penolakan berasal dari guard predecessor yang bekerja sesuai desain (GUARD_BY_DESIGN); tidak ada data yang berubah di luar basis sekali pakai.
3. Workflow ini di-pin ke lima commit historis; menjalankannya di kandidat 0b7049d9 tidak menguji 0b7049d9 (sama seperti pin identitas lain di RED_CLASSIFICATION).

**Yang tetap saya catat sebagai temuan dokumentasi/bukti (kandidat S3, bukan penghalang):**

- Repo memuat **dua salinan migrasi AC yang berbeda** (migrations vs release package). Pemasangan baru dari `supabase/migrations/` dan dari `supabase/release/cp6-t3/` menghasilkan definisi `erp.v_payroll_nota_browser` yang berbeda (teks badan dan sha). Paket rilis dibekukan (ae29390e/decafe62) **sebelum** migrations AC diubah oleh f455f612. Tidak ada dokumen di pohon beku yang menyatakan mana yang kanonik untuk pemasangan baru. Ini relevan untuk CP7C/VPS nanti (pemasangan baru). Ditriase sebagai FABLE-xxx S3 di laporan utama; rekomendasi: penulis menyatakan satu sumber kanonik dan menambah pemeriksaan kesamaan (atau mencatat alasan perbedaan) — tanpa melonggarkan guard.
- Workflow yang **tidak pernah hijau** sejak dibuat masih ada di pohon beku tanpa penanda "diketahui menolak" selain komentar di skrip. Rekomendasi: beri label eksplisit di nama workflow/README (dokumentasi, S3).

## 4. Dampak pada vonis

- CP6: tidak mengubah vonis (jalur rilis T3 yang sesungguhnya dinilai dari `cp6-t3-release-package` + `cp6-t3-rollback`, lihat REGISTER_RUNS).
- CP7: tidak terkait.
- Tidak ada rerun: job menolak di badan kasus (bukan mati sebelum kasus), jadi rerun tidak diizinkan dan tidak diperlukan.

Bukti: `RED_CLASSIFICATION.md` (entri aligned-install → DISELIDIKI → SELESAI, rujuk dokumen ini); log job tersimpan di sesi auditor (tool-results get_job_logs job 115713835290, 2026-10-14T06:42:25Z).
