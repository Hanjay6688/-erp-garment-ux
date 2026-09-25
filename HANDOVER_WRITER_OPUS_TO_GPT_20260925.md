# Serah terima writer Opus → GPT (bila owner memutuskan), 25 Sep 2026 — catatan auditor
Syarat auditor (bukan cara kerja writer): (1) GPT berhenti mengaudit selama menjadi writer; hasilnya tetap harus lulus run auditor sendiri; (2) kerja hanya di cabang
`claude/new-session-deapao`; tidak menyentuh main/kompetisi/hosted/production; (3) tulis §32 di `docs/cp6-au-r1-handoff.md` dengan head + nomor run per gate, ikuti
pola §30–§31; (4) pakai workflow CI yang ada (probe family, auditor scenario, T2, T3, rollback, CodeQL); (5) tabel kasus per family memetakan kasus → ID C6/ALL → oracle
pra-kode auditor; (6) jangan mengecualikan detektor diam-diam (lihat D07).
Bacaan wajib writer baru: §30–§31, `docs/cp6-bc-case-table.md`, `AUDIT_WRITER_HANDOFF_CP6.md`, `WRITER_HANDOFF_R12_PASTE_20260925.md`, `OWNER_DECISIONS_CP6_DRAFT.md`.
Yang menunggu writer: D07 (spesifikasi paste R12 §2.1), F3 (keputusan owner/writer), kasus pengganti `ACCESSORY_CONNECTED_ZERO`, BD (dimulai di 40d6906/b9f5ab1/caeff6f), BE, uji gabungan.
