# Review daftar keputusan owner — 25 September 2026

Sumber kontrak lokal dibaca ulang dan hash diverifikasi:
- M: f21ac70360915a1f1021b42a3918e862ca7d11cf88c1b90c5627b4490c69af07.
- P:92966cd6ed27e64123be6c52e2263bfbdb3db91c97f2e441c3bdc98589397676.
- BR:4566ab6f1c8e53bc21c70c0c777f780b526305815e04d5913a5c858dfaa85886.

Sumber gabungan terbaru44cc69d8f9c5f26aa5d50103a2fb827de0b0f01f sudah berisi lanjutan Fable; jangan mengembalikan repo ke46ee4c2. Branch auditor lama c96c014c928d4ff81b4c49d030c9aef80718493a mengarahkan penerus ke branch gabungan. Writer saat pembacaan:d284e9b4f4e9e6bede36b4fa0dd7966ce785fa8c.

Catatan pembacaan:
1. Kontrak M1022–1025 dan marker arsip1053: ALL sudah diputuskan; M1072 bukan status aktif yang membatalkannya. M3817 secara eksplisit mengizinkan edit prepared draft dan mewajibkan stale detection. M6667 meminta mencari keputusan terbaru dan tidak membebani owner dengan persoalan teknis.
2. M629–646,3816–3825,6008–6021,6148–6162: pisahkan existing invoice-date/prefix/immutable rules dari klarifikasi aplikasi tanggal pada advance/refund dan downstream recost.
3. M1691–1699,1753–1757,4448–4479: owner boleh menentukan penempatan CR, tetapi kewajiban CP6 dan fitur yang sudah masuk kandidat tidak otomatis dapat dikecualikan.
4. AUDIT_PROGRESS/INDEX/HANDOFF pada44cc dibaca. CP6-19 masih memiliki ordinary-route caveat; itu masalah pembuktian teknis, bukan perlu izin owner untuk mengedit draft. CP6-18 masih mempunyai oracle optional-binding terbuka.
5. audit/out/T2_classification.md dan DATE_family_results.md pada c96c dibaca sebagai klasifikasi auditor, bukan hasil native yang baru diverifikasi GPT. Dekomposisi25=8AS+12kalender+4AO+1adjustment. Klasifikasi awal literal invoice-date perlu dibaca bersama catatan keluarga tanggal yang lebih baru; jangan memilih aturan hanya untuk menyesuaikan hasil kandidat.
6. docs/cp6-ao-ap-owner-decisions.md pada d284 dibaca hanya sebagai corroboration; kontrak M1024 sendiri cukup untuk approvalALL. scripts/cp6_t2_regression.py:11–52 dan scripts/cp6_ay_probe.py:1–22 memuat kutipan keputusan24Sep yang akan diperjelas. Kutipan writer belum otomatis menjadi kontrak.
7. docs/cp6-aw-design.md:135–143 dibaca: P-03 memblokir semua tanggal untuk banyak check current-state; per-date scoping memerlukan bukti dan pilihan kebijakan. scripts/cp6_ax_probe.py:1–9,181–202 memuat profil AX (non-PO, valuation reference/owner, OTHER_INCOME); detail itu belum otomatis menjadi oracle kontrak.
8. out/fable_native15_xaudit5_results.md dan out/fable_tool_review_d284e9b.md dibaca. Menurut catatan Fable, native15 run36065350201/job107853710984 dan xaudit5 run36065517737/job107854232896 sudah dijalankan pada d284; ini bukan NOT_RUN lagi. Tugas ini tidak membaca ulang log Actions dan tidak mengklaim mengeksekusi atau memverifikasi ulang seluruh hasil tersebut.
9. Draft owner disiapkan di OWNER_DECISIONS_CP6_DRAFT.md: enam pilihan, rekomendasi, alternatif, contoh dan dampak oracle. Semua masih USULAN. Tidak ada kontrak, produk, verdict temuan atau hasil native yang diubah oleh tugas ini.

Ruang lingkup akhir: penyusunan keputusan owner, bukan re-audit seluruh daftar bug/PASS yang disalin ke chat. Tidak ada alasan untuk menyebut CP6 aman atau production_go=true hanya setelah tiga P1 diperbaiki. MaterialP2, cakupan browser/inverse dan gate lain masih mengikuti kontrak.

LANGKAH BERIKUTNYA: owner memilih klausul; baru catat addendum resmi dengan rujukan kontrak. Writer/auditor lanjut tugas teknis yang tidak menunggu pilihan. Pertahankan seluruh pembaruan Fable pada branch gabungan dan lakukan update fast-forward.
