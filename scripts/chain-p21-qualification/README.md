# P21 rantai — uji pasang, copot, pakai, cadangkan dan pulihkan ujung rantai OW-15

Uji P21 untuk seluruh rantai tahap (OW05, OW06, kasbon, fgqc, OW05b, OW08a, OW12a, OW-09, OW07, wash, OW-04b followups,
irisan A, B, C) di salinan database sekali pakai. Tidak menyentuh database hosted atau produksi.

- Probe: `scripts/cp7_p21_current_chain_rehearsal_probe.py` (salinan probe P21 OW05).
- Adaptor: `scripts/cp7_p21_chain_adapter.py`; pemulihan: `scripts/cp7_chain_restore.py`.
- Workflow: `.github/workflows/cp7-chain-p21.yml`.
- `SOURCE.json`: sidik jari berkas dan laporan asli irisan C (masih `PENDING_OW04BC_*` sampai irisan C lulus; sampai itu
  workflow berhenti di langkah ambil laporan, sebelum database dinyalakan).
- `EXPECTED_CHAIN_STEPS.json`: langkah rantai dari rencana bagian 4. Langkah bertanda `TODO` belum ditulis; selama masih
  ada, laporan tidak boleh PASS. Setiap langkah memakai panggilan dan pemeriksaan dari berkas kasus tahapnya sendiri, dan
  berjalan sesudah cek "sudah dipakai" ditolak, sebelum database dicadangkan (lalu dicek lagi di database hasil pulih).
- Catatan lingkup (`scope_notes`): pembacaan status tahap B **belum** jadi langkah wajib, karena B belum di rantai;
  ditambah saat tahap B masuk. Catatan ini ikut tercetak di setiap laporan.

Yang diperketat dibanding P21 OW05: cek piutang lama dan `CP7_CUSTOMER_CREDIT_REPORT_UNPROVEN` harus semuanya
`('CRITICAL',0)`. Batas lama 2/3/1 tetap tersimpan sebagai riwayat di
`docs/cp7/d17-14/ow04/p21-36a6b880-readiness-boundary.json`. Cek READY E01 tidak diubah; periode absensi lama dibagi ke pool
lewat facade Native dengan alasan berlabel fixture sebelum E01 (temuan 3). Berkas EXPECTED lama di
`scripts/ow05-p21-qualification` tidak diubah dan dipakai apa adanya.
