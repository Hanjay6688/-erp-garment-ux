Auditor (Fable; hasil konvergen dengan GPT) → Writer, CP6 putaran 11 (25 Sep 2026, 16:10 WIB)
Head diaudit: BB final 4c61acad2270e11a2aca762237790a68cf36278a (handoff writer §30). CP6 HOLD, audit_complete=false, production_go=false.
Rincian: out/fable_r11_results.md §1–§8, out/gpt_bb_round10_result.md, daftar tugas berlaku AUDIT_WRITER_HANDOFF_CP6.md.

1. KEPUTUSAN OWNER (langsung ke auditor, teks verbatim di OWNER_DECISIONS_CP6_DRAFT.md):
   a. D06 DISAHKAN: Lampiran C6 rev4 pada 4c61acad (sha256 42e04815…) termasuk scope ACC-04b, LAU-05b, LAU-06b, ALL 22.
      PENDING_POLICY_VALUE tetap pending sampai owner menyetujui angkanya. Pengesahan ≠ penerimaan uji.
      → Writer: catat D06 di addendum induk bagian 9 (tanggal, commit, sha), ubah status lampiran dari "OWNER_ACK_REQUIRED" ke "DISAHKAN (D06)".
   b. T3 = OPSI A: rata-rata bergerak untuk bahan sejenis yang bercampur; selisih pembulatan beberapa nota boleh terkumpul di satu PO
      (contoh teruji 10,05 vs 10,01). JANGAN tulis batas tetap "paling banyak 1 sen per PO". Wajib tetap cocok dan diuji: total nilai,
      nilai per tanggal, stok habis = nilai 0, jejak sumber dan penyesuaian. Penilaian per roll = CR terpisah.
      → Writer: perbaiki kalimat di docs/cp6-t3-cent-per-po-and-t5-advisor-note.md (§T3 "Permintaan keputusan owner") sesuai teks di atas;
        tambahkan probe BA yang mengunci empat kewajiban itu pada n nota bertumpuk (n ≥ 3, termasuk 10) — bukan per-PO = nota.

2. HASIL BB PADA 4c61acad (semua bukti run auditor sendiri):
   - Probe before/after: 57/57 PASS after (52 writer + 5 Fable); before 52 NO_ROUTE + 2 COUNTEREXAMPLE + 3 PASS; parser halaman berjalan.
   - Runtime auditor: race 8/8, HTTP 3/3, browser 3/3. T2 identik (holds 12/12, C0 25/25). Paket T3 26/26 (advisor +75 INFO, drill OK,
     UUID CLEAN 855 kolom, alias NONE). Rollback 131/131. T4 dokumen dua bahan PASS (pembulatan per dokumen). Regresi BA 7 skenario bersih.
   - GPT: S02 dua draf berbagi stok PASS; pool 10 nota PASS (total 100,10, stok 0).
   - TIDAK ADA CACAT PRODUK BB yang ditemukan kedua auditor pada head ini. Tiga cacat yang writer temukan dan perbaiki sendiri
     (format uang 2 desimal 5959854, urutan drop rollback 797fadd, S02 tanpa family e648711) sudah terverifikasi lewat run di atas.

3. CATATAN BB YANG MASIH HARUS DIBERESKAN WRITER (bukan blocker, tapi sebelum BC diklaim):
   a. Label: W05 di BB = PARTIAL (finansial saja) — sudah di rev4; pastikan tabel kasus dan §29.6 memakai label yang sama.
   b. Rute 6 keadaan era-BA (P01, A01, A02, W01, W03, C01) masih "inventaris writer, belum diverifikasi SQL oleh auditor".
      Sertakan satu probe impor→lanjutan→inverse per keadaan itu (boleh di BB atau family sendiri) agar 22/22 punya bukti run, bukan inventaris.
   c. Advisor: +75 INFO rls_enabled_no_policy (termasuk 19 tabel bb_* dan capsule BB) — catat di paket rilis sebagai disengaja (T5 sudah, perbarui angkanya 56 → 75).
   d. T6 drill data hosted (UUID, alias CASH_BANK, ukuran DB) = tugas operator; auditor tidak menyentuh hosted.
   e. T7 opsional (W3 cabut grant helper prepare, W5 pesan STALE_VERSION) tetap terbuka.

4. BERIKUTNYA: BC (ACC-04b, ACC-DEC/ERP-DEC02 sebagai pengaturan dengan default tolak/pending, ALL C02/C03). Kirim head BC FINAL + tabel kasus →
   ID (75 C6 / 22 ALL) → oracle pra-kode (Fable out/fable_c6_75_oracles_pre_code.md; GPT out/r9_acc_oracle.md), dengan T1 before/after,
   race dua sesi, HTTP Auth, browser, T2, paket T3 berkas ke-27 + rollback. Nilai kebijakan aksesori tetap PENDING_POLICY_VALUE (tolak/pending),
   jangan isi angka.

5. Tata kerja cabang audit: log progres kini per auditor (AUDIT_PROGRESS_FABLE.md, AUDIT_PROGRESS_GPT.md); AUDIT_PROGRESS.md dibekukan sebagai riwayat.
   Daftar tugas tetap satu: AUDIT_WRITER_HANDOFF_CP6.md. Batas auditor tidak berubah (baca saja; tanpa push ke cabang writer; tanpa hosted).
