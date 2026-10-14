# Empat program CP5 historis — eksekusi identik dan disposisi

Run `38572768164`, job `115881983961`, control `0d7f3dcc72e1fbee19883c1056361c54527f6885`, kandidat FULL `0b7049d9`. Artifact `11898319571`, SHA256 `0d2a143067b6e1465246b942b79932fb6cc1b314e71f59cf43be1d59a28347bc`. Program asli dijalankan sekali tanpa mengganti sumber, fixture, expected atau melewati dispatcher historis. Setiap program memakai clone tersendiri. Ini **4 eksekusi program: 1 PASS, 3 INCOMPLETE**, tidak ditambahkan sebagai empat kasus bisnis atau sejumlah assertion yang ditebak.

| Program | Hasil asli | Disposisi |
|---|---|---|
| cutting_bridge_persistence_pickup_wip_rollback.sql | Exit 3, INCOMPLETE | Berhenti pada assertion gabungan akhir `Cutting Bridge facade/private-table/CP4 owner boundary regressed`. **GUARD_BY_DESIGN / hash predecessor historis**: minimal operand hash owner-admin pasti gagal karena delta CP7 yang dideklarasikan dan diperiksa FULL. Hasil mentah tetap INCOMPLETE. |
| cp5_bs_resolution_recovery_rollback.sql | Exit 3, INCOMPLETE | Fixture rework non-PO ditolak `BE_NONPO_REWORK_UNSUPPORTED`; kontrak current mengarahkannya ke AX. Bagian setelah kegagalan belum dijalankan. GUARD_BY_DESIGN pada prasyarat fixture ini; bukan seluruh suite PASS. |
| cp5_rework_accessory_lineage_rollback.sql | Exit 0, PASS | Program utuh mencapai DO/ROLLBACK. Kredit satu program, bukan setiap assertion sebagai kasus baru. |
| cp5_bs_resolution_concurrency.py | Exit 1, INCOMPLETE; Original race FAIL | Fase receipt-reversal-wins berhenti karena fixture posted receipt tidak mempunyai lineage WIP CP6. Pembalikan gagal; claim kemudian OPEN bukan bukti claim mengalahkan pembalikan yang sukses. AUDITOR_TOOL/LEGACY_FIXTURE_GAP. Fase akhir STUCK belum tercapai. |

## Batas assertion cutting bridge

Assertion akhir menggabungkan grant anon/private authenticated, hak tabel, execution-context kosong, RLS dua rollback capsule, substring body `require_internal`, substring guard pada recost, dan hash `require_owner_admin`. Log tidak merinci seluruh operand. Penelusuran effective source menemukan satu operand yang **pasti tidak cocok pada FULL yang sah**: SQL lama mengharuskan MD5 CP4 `965de305e5a381cfdf5588f2b9d4babc`, sedangkan CP7 sengaja menambahkan konteks settlement privat melalui `cp7_settlement_bundle.patched_owner`.

Definisi FULL yang diharapkan mempunyai MD5 `ec31bbfd0fba3e18a66f7f3ea33473e8`, SHA256 `57efdfe8af1a3dddba35332e81f00a27c7e2fcf9c0708e31c53a3eb74766fcdf`. `cp7_p21_full_rehearsal_probe.install` membandingkan definisi hasil pemasangan persis dengan hasil patched_owner, sekaligus menjaga owner dan ACL, sebelum mengembalikan runtime FULL. Original job melewati pemasangan, runtime_before dan runtime_after. Program SQL historis tidak mengganti fungsi owner-admin itu.

Jadi error gabungan sudah mempunyai sebab konkret: oracle byte-hash predecessor bertentangan dengan delta CP7 yang sah. Ini **bukan bukti seluruh operand lain sudah ditangkap nilainya**, bukan semua private-boundary otomatis PASS, dan bukan alasan menghapus guard. Kelas GUARD_BY_DESIGN/historical-oracle; raw INCOMPLETE disimpan. Pada kandidat perbaikan gunakan matriks predecessor vs delta current beserta kontrol izin, tanpa mengedit migrasi atau mengganti expected diam-diam. Hash sumber diagnosis ada di `CP5_EXACT_OBSERVATION.json`.

## Race dan pemulihan

Original race menyimpan empat kelompok sebelum kegagalan: disposition_vs_disposition, claim_reversal_vs_bs_cash_compensation, damage_claim_vs_capacity, damage_claim_wins_vs_receipt_reversal. Hasil masing-masing tetap tersedia; bukan sertifikasi seluruh race. Pembalikan gagal dengan `Laundry receipt reversal refused: posted WIP source history is missing or duplicated` pada `append_cp6_laundry_wip_reversal_v2620`. Setup historis memasukkan receipt POSTED langsung, tanpa event WIP yang dituntut mesin current. Fase `stuck_claim_vs_physical_return` tidak berjalan.

Seluruh 19 field residue race bernilai 0. Keempat clone tersisa 0; restoration dan advisor gate outer true. Field `remaining_sessions` setiap program mencakup satu koneksi verifikasi auditor yang sedang dibuka; jangan menyebut daftar itu kosong atau setara strict per-case gate. Setelah disposal tidak ada database clone. `CP5_EXACT_OBSERVATION.json` menyimpan hash sumber, exit, tail error, cleanup dan hash Original; stdout lengkap serta race Original berada di arsip.

Keempat job desc kini telah dieksekusi dan didisposisikan. Ketidaklengkapan exact-suite tetap batas penerimaan, terpisah dari lima cacat runtime yang dibuktikan dengan kasus Astra.
