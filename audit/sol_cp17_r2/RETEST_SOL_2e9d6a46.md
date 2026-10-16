# Audit ulang Sol — CP1–7 r2

Kandidat: **`2e9d6a468c110684c278d585418eb404250d1150`**. Tree: **`5e50d224f8e74fa3bca83b599fb606739435b598`**.
Auditor: **Sol**, independen, tanpa subagen dan tanpa membaca hasil peserta lain pada putaran ini.
Jendela uji: 16–17 Oktober 2026 WIB. Sumber handoff writer dibaca pada `b388a4b7d4b0291de81b68d1e624a062eda5edd1`;
delapan berkas setelah kandidat hanya dokumen. Guide Pro Max SHA-256
`5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639` cocok dengan acuan putaran sebelumnya.

**Vonis kandidat integrasi: HOLD. Pekerjaan audit putaran ini selesai; `production_go=false`, `audit_complete=false`.**
Tidak ada kode produk diperbaiki, SQL hosted dijalankan, deployment dilakukan, atau perubahan ke cabang writer/main.
Penerimaan CP6 sebelumnya dipertahankan sesuai kontraknya; laporan ini menilai kandidat integrasi r2 dan syarat penutupnya.

## Ringkasan

Temuan produk baru: **S0 0, S1 0, S2 1, S3 0**. Selain itu ada dua item yang sudah diungkap writer dan tetap terbuka:
siklus layar pool HPP absensi (S1, fungsi belum tersedia) dan paginasi alat receipt (S3).
Kelima temuan Sol putaran `dfab13bf` tertutup dalam cakupan yang diuji. Tiga akar bersama yang sebelumnya dicatat Sol
(angka contoh UAT, master harian, jahit wave BF) juga telah diuji ulang dan tertutup dalam batas keputusan D15.

Matriks 82 invarian: **73 PASS dalam cakupan bukti, 9 INCOMPLETE**. Tidak ada klaim bahwa 73 baris itu mencakup setiap
permutasi atau data produksi. Sembilan INCOMPLETE adalah kekurangan bukti penerimaan yang dirinci, bukan sembilan bug baru.
Bug nomor PO melanggar fungsi D15-6 dan sasaran waktu simpan; penjaga atomicity justru tetap bekerja pada contoh gagal itu.

Semua **10 run, 21 job** auditor terminal: **8 run sukses, 2 run gagal; 18 job sukses, 3 job gagal**.
Satu job gagal adalah contoh produk baru; dua lainnya masalah alat auditor yang dikualifikasi secara terbuka.
Tidak ada hasil gagal yang diganti menjadi PASS. Tidak ada rerun job GitHub untuk mencoba keberuntungan.

## Lingkungan dan perintah

CI Ubuntu 24.04, PostgreSQL image `17.6.1.165`, Supabase CLI `2.116.0`, Python 3.12,
`psycopg[binary] 3.2.10`, Node 22, Chromium dari Playwright `1.62.1` sesuai lockfile kandidat.
Semua basis data pengujian sekali pakai. Auth HTTP/browser memakai GoTrue dan PostgREST lokal nyata kecuali
inventaris UI yang ditandai MOCK. Akun owner non-superuser dipakai pada uji pemasang 58 berkas.

Perintah utama yang benar-benar dijalankan, melalui workflow cabang auditor dengan checkout kandidat pada SHA penuh:

```text
python ../sol/audit/sol_cp17_r2/retest_probe.py
CP7_F03_BUCKET=<8 bucket> python ../auditor/scripts/cp7_f03_full_probe.py
python ../sol/audit/sol_cp17_r2/owner_baseline.py
python ../auditor/scripts/cp6_readiness_owner_test.py
python ../sol/audit/sol_cp17_r2/new_probe.py
python ../sol/audit/sol_cp17_r2/uat_probe.py
CP7_F03_BUCKET=prefreeze_ui python ../auditor/scripts/cp7_f03_full_probe.py
python ../auditor/scripts/cp7_cutting_model_probe.py
node ../sol/audit/sol_cp17_r2/menu_inventory.mjs
node ../sol/audit/sol_cp17_r2/menu_inventory_qualified.mjs
npm test
npm run test:security
CodeQL security-extended: javascript-typescript, actions; zero-results gate
python scripts/cp6_readiness_owner_drain_test.py
python scripts/cp6_auditor_public_state_test.py
```

Workflow pemicu hidup pada cabang audit. Checkout produk selalu `ref: 2e9d6a46…`; writer/base/harness serta action
yang dipakai dipin. `IDENTITY_SOURCE.json`, identitas CI, hash bundle dan manifest provider mengikat bukti ke produk.
SQL release/dev/migrations di `supabase/` **tidak berubah** terhadap `dfab13bf`; perubahan CP7 dan pembacanya tetap
diaudit. Terdapat 133 berkas berubah termasuk dokumen, 112 di luar `docs/`; hitungan tersebut bukan jumlah fitur.

## Hasil per kelompok

| Kelompok | Hasil | Makna bukti |
|---|---|---|
| F03 delapan bucket | 447 kasus + 3 smoke PASS | Gabungan Native/race/HTTP/browser; seluruh komposisi r2, 41 peran privat; bukan 447 Native saja. |
| CP17 | 145/145 PASS | 80 Native, 18 race, 14 real Auth HTTP, 33 browser. Manifest dan ID kasus diperiksa. |
| Literal Sol lama | 7/7 Native PASS | Angka dan expected lama dipertahankan, termasuk pemasukan terpakai dan pembatalan jahit parsial. |
| HTTP koreksi Sol | 4/4 PASS | Login nyata, pembaca ruang koreksi publik, inverse+replacement serta kontrol penolakan negatif. |
| Batas/dimensi tambahan Sol | 2 PASS, 1 COUNTEREXAMPLE → FAIL | Nomor999 PASS; nomor1000 gagal; SKU5/2/9 reverse/repost PASS, netWIP356. |
| Owner install | 10/10 guard dan 58/58 berkas PASS | Helper stop-before-U tanpa monkeypatch; owner non-superuser, Native BF verify, admission/reopen. |
| Build UAT + Native disposable | 3/3 PASS | Auth asli, hidden-menu census HP, customer lifecycle desktop, PO otomatis HP. Transport diarahkan lokal; hosted belum diuji. |
| Regresi UI lama di final CP7 | 31/31 PASS | BD/BE/BF/readiness; dua tes demo penjualan yang resmi pensiun diganti dua tes draft tersambung yang dideklarasikan provider. |
| F04 model/consumer | 57/57 PASS | 34 Native, 8 race, 5 HTTP, 10 browser; termasuk existing-PO POST/recovery/current-access. |
| Inventaris UI | 288 pengamatan PASS | 48 menu×3 mode×2 viewport. Auth/access MOCK, business reads 403; rute, label, lebar, refusal saja. |
| Unit/DOM | 1.794/1.794 PASS | 215 berkas, full Git history; tidak ada kasus diskip pada hasil yang dikualifikasi. |
| Gerbang keamanan sumber | PASS | `npm run test:security`; cek statis tidak dihitung sebagai kasus Native yang tercetak pada metadata gate. |
| CodeQL | Dua bahasa selesai, 0 findings | JavaScript/TypeScript dan Actions, setiap invocation sukses; sumber kandidat persis. |
| Drain dan comparator | PASS, kontrol terpisah | Dipisahkan dari 145 CP17; comparator sensitif pada definisi/anggota/owner/ACL, bukan pemulihan sebab dua A2 lama. |

Angka di atas adalah **eksekusi dengan konteks sumber**, dapat memakai oracle yang sama pada lapisan berbeda.
Tidak dijumlahkan menjadi “sekian ribu bug-proof unik”. Ledger juga mempertahankan dua diagnosis INCOMPLETE pada
baseline CP6 sebelum CP7 dipasang; keduanya mendapat nol kredit penerimaan. `CASE_LEDGER.json` dan `SUITE_RESULTS.json`
mencatat lapisan dan asal per baris, bukan sekadar warna job.

## Temuan baru: SOL-R2-001 — penomoran PO ke-1.000 tidak selesai

- **S2, NATIVE_QUALIFIED, INDEPENDENT_NATIVE_RERUN.** Kebutuhan: D15-6 dan sasaran waktu simpan owner.
- Lokasi: `scripts/cp7-src/cutting-correction/auto-po.sql:212–217`.
- Rantai dampak: Buat Potongan → nomor/PO baru → posting material dan WIP → pickup/tahap produksi berikutnya tidak dimulai.
  Tidak ditemukan saldo/stok rusak pada kasus ini; command batal sepenuhnya.
- Fixture: 999 PO `DRAFT/CUTTING` sintetis, bernomor 001–999 pada satu tanggal, tanpa stok/jurnal.
  Roll sah berisi 10; permintaan lewat public facade sebagai OWNER.
- Expected: nomor berikutnya `PO-261014-1000`, satu PO dan satu potongan sah dalam waktu terbatas.
- Actual: timeout uji 3,003 detik, SQLSTATE57014; konteks tepat pada `WHILE ... lpad(v_n::text,3,'0')`.
  `lpad('1000',3,'0')` menghasilkan `100`; seluruh nomor yang diperiksa sudah ada. Kontrol998→999 selesai 0,040 detik.
- Sesudah gagal: roll tetap10, seluruh boundary dipulihkan, public schema tidak berubah, advisory/session leak0.
  Penundaan permintaan lain karena kunci harian merupakan telusur sumber, belum klaim race teruji di batas1.000.
- Bukti: **run38934111700 / job117085146759 / artifact12059209949 / SOL_R2_NEW_RESULT.json**.
  Nama kasus persis dan output asli terdapat pada `FINDINGS.json` serta arsip Native.
- Perbaikan yang disarankan: panjang tiga menjadi minimum, tetap unik dan terkunci per tanggal; pertahankan UUID dan
  transaksi atomik. Uji999/1000/1001,9999/10000, dua sesi, replay, kegagalan di tengah dan draf. Jangan menyelesaikan
  dengan menambah batas waktu.

## Uji ulang dan item yang sudah diketahui

`RETEST_DISPOSITIONS.json` mencatat seluruh penutupan lima temuan Sol lama, tiga akar bersama, serta cakupan lama
SOL-001/002/003. Contoh uang lama tidak diganti: pemasukan30,01, pengeluaran20, koreksi25,01 menghasilkan5,01;
koreksi catatan saja menghasilkan10,01; pengganti15,01 ditolak karena akan menghasilkan−4,99. Fakta awal tetap.
Lebar QC/HPP demo sekarang390 pada viewport390, dari669/627 sebelumnya.

**Pool HPP absensi belum memiliki siklus layar** — item writer R2-07 yang dikonfirmasi dengan telusur sumber,
bukan penemuan baru Sol. Native preview/create/activate/cancel ada; pemanggilnya tidak ada pada `src`/facade CP7.
Pengaman meminta pool dibatalkan sebelum koreksi sumber tertentu, sementara jalur layar itu belum tersedia.
Pemenuhan D15-2 tidak menghapus kebutuhan pool. SQL HPP01 PASS tidak menjadi bukti ketersediaan UI.

**Receipt hanya halaman pertama** — skrip kandidat `scripts/cp7_ci_receipt.py:28/31` belum memaginasi run/job.
Writer sudah mengungkapnya dan membuat receipt dengan salinan lain. Auditor membaca halaman1+2 dari metadata final:
116run/115workflow,94sukses22gagal, attempt1, cocok pada SHA kandidat. Angka179job/157sukses berasal dari receipt writer;
seluruh22 job gagal dibaca lognya, bukan klaim setiap job sukses writer telah diuji ulang auditor.

Kedua item beserta arah perbaikan ada di `WRITER_HANDOFF.md` dan `FINDINGS.json` bagian `known_open_items`.

## Hasil merah yang bukan temuan produk baru

| Sumber | Hasil asli | Klasifikasi dan tindakan |
|---|---|---|
| Own run38934111778, job117085147935 | UI UAT69PASS/27INCOMPLETE | Alat observasi menekan tombol pembuka yang tertutup sidebar yang masih terbuka setelah mencatat menu hidden. Perbaikan keadaan menu saja; expected lebar/angka/ID tetap. Run38937763036 job117097460133:96PASS. |
| Own run38934111778, job117085148136 | Unit1766PASS/19FAIL/9SKIP; dua suite gagal dikoleksi | Checkout auditor dangkal, objek predecessor untuk perbandingan tidak tersedia. Full history dipenuhi tanpa mengubah uji/expected: run38937763036 job117097460517,1794PASS. Demo96 pengamatan sudah PASS pada job pertama. |
| `ROUND_MANIFEST` F03 field `expected_native` | Label keliru, nilai447 | Itu447 lintas lapisan, ditambah3smoke; anggaran/ID/provider tidak berubah. Koreksi label pelaporan terbuka di TOOL_QUALIFICATION.json. |
| Additional install reports `SOL_R2_NEW_INSTALLATION` / `SOL_R2_UAT_INSTALLATION` | Provider ringkasan CP17 INCOMPLETE | Wrapper sengaja menjalankan hanya3 kasus tambahan dan tidak mengulang145 provider. Hasil3 kasus dinilai oleh report Sol tersendiri; restore/advisor tetap wajib. Tidak dihitung sebagai dua kegagalan145 CP17. |
| Prefreeze diagnosis CP6-only | Dua READINESS INCOMPLETE | RPC CP7 recost belum ada pada baseline sebelum instalasiCP7. Setelah stackCP7 dipasang,31 kasus yang berlaku PASS. Diagnosis dipertahankan, tidak direlabel PASS. |
| Writer116run | 22run gagal |20jalur lama terhenti di cakupan historis,1AF membutuhkan artifact kedaluwarsa,1scenario lengkap berisi4INCOMPLETE. Log dibaca sebagai REUSED_WRITER_EVIDENCE, bukan penutup audit. Tidak dihapus dari hitungan CI. |
| Writer AT predecessor observations |2COUNTEREXAMPLE,39CONTROL_PASS,12DATE_POLICY_REVIEW_REQUIRED | `cp6_as_trial.qualify` secara eksplisit menjalankan AR_EXTRA_PROBES pada stageAR sebelum kualifikasiAS. Label dan fase dipertahankan; bukan bukti regresi stack final. CONTROL_PASS tidak dihitung sebagai kegagalan. |
| Backup/restore lokal |19 galat pg_cron yang dijelaskan | Drill meluluskan kesetaraan data/katalog bisnis dan keluaran mesin, dengan pengecualian ekstensi cron pada database selainpostgres. Tidak diklaim sebagai restore jadwal produksi. |

Log gagal pertama dan sumber kualifikasi tidak dihapus. `TOOL_QUALIFICATION.json`, `WRITER_FAILURE_CONTEXT.json`,
run register dan arsip menyimpan pemisahan tersebut. Sebab kegagalan AZ historis dan dua A2 lama tetap belum diketahui;
lulusnya pemasang/comparator sekarang tidak membuktikan penyebab kegagalan yang catatannya dulu tidak tersedia.

## Cakupan CP1–7 dan sambungan

| CP | Yang diperiksa | Batas penerimaan |
|---|---|---|
| CP1 | Hash/tree produk, guide, jalur baselineG01, ledger/schema dan batas Native sepanjang install/recovery. | Identitas hosted saat ini tidak dibaca; acuan hosted tercatat lama, bukan preflight baru. |
| CP2 | Backup/restore bisnis pada database disposable dan perubahan primary yang harus nol; arsip bukti asli dipertahankan. | Original CP2 functional restore/kunci/data nyata di CP7C; restore cron produksi tidak diklaim. |
| CP3 | Auth nyata, RBAC/current-access, role/grant/owner/catalog, revocation dan larangan akses API `erp`. | Revoke82writer tetap ditunda sesuaiD14-9; kanal/API/cache/prompt di luar permukaan uji bukan PASS menyeluruh. |
| CP4 | Pola/master/SKU/range/BOM/tarif/snapshot, stock-to-cost/GL, finish/reopen/HPP dan seluruh instalasi pendahulu. | Kombinasi dan data nyata tidak disamakan dengan fixture; pool HPP belum punya UI lifecycle. |
| CP5 | PO/potong/pickup/BS/sewing, kegagalan atomik, replay, dua tab, existingPO UI recovery dan pencabutan izin. | Nomor PO1000 gagal; satu rangkaian layar seluruh tahap dan setiap cabang tidak diklaim. |
| CP6 | Release58berkas tidak berubah, ownerinstall/restore, BD/BE/BF/range/vendor/claim dan31browser di stackCP7akhir. | Penerimaan lama tetap; sebab AZ/A2 historis bukan otomatis tertutup, dan CP7C hosted belum dilakukan. |
| CP7 | F03/P09–P13, CP17/D15, master baru, autoPO, wave, koreksi, reports/period, F04consumer, modeUI, dua chain browser baru; mesin P19 lama ditelusuri perubahan sumbernya. | P19 skala besar/K2–K6/AI/WA memakai bukti independen lama pada sumber tak berubah, bukan uji Native/live baru putaran ini. |

`CHAIN_MATRIX.json` memberi disposisi **20/20** sambungan B1–B13/S1–S7; `SCENARIO_MATRIX.json` memberi disposisi29skenario,
dan `IMPACT_MATRIX.json` mengikuti setiap akar r2 sampai stok, biaya/upah, HPP, GL, pembayaran, laporan dan layar.
Jumlah baris ditinjau tidak berarti20 perjalanan layar penuh telah lulus. Dua chain baru yang benar-benar dijalankan:
imporWIP→FG→ganti merek→tutup buku→jual→bayar→kas→reopen, dan BS→rework→Nota→payroll→bayar dengan komponen/recipe dari layar.

## Yang belum terbukti dan tidak diberi PASS

- Data cutover nyata per baris dan shadow minimal satu periode; seluruh cek integritas pascacutover nyata.
- Original CP2 functional restore, preflight hosted baru, instalasi CP7/maintenance/rollback hosted; tahapan owner tetapCP7C.
- Semua detektor memiliki kontrol0→tepat+1→0, dan semua detektor bernilai nol sebelum/sesudah **setiap** skenario.
  Kontrol subset lama dan detector kas baru tidak menutup seluruh katalog.
- Angka pada perangkat fisik HP/iPad serta semua layar dalam keadaan data positif/bermuatan; yang diuji adalah Chromium1440/390.
- Seluruh kanal di luar API/role/capture/AI/cache yang tercakup kasus; non-leakage as-known semua kombinasi waktu.
- Satu perjalanan layar seluruh13tahap dan7cabang sekaligus, serta UI lifecycle poolHPP.
- Sebab AZ pertama dan dua A2 historis yang bukti diagnosis aslinya tidak lengkap.

Ini daftar konkret batas bukti, bukan daftar tambahan bug yang diasumsikan. Rincian9invarian INCOMPLETE beserta
syaratnya ada di `INVARIANT_MATRIX.json`; persyaratan rilis tidak dihapus agar status terlihat selesai.

## Label asal bukti

| Klaim | Asal |
|---|---|
| Runtime r2, counterexample, restore/admission, Auth, race dan transaksi browser | INDEPENDENT_NATIVE_RERUN, run/job/artifact per CASE_LEDGER. |
| Lebar/label/rute/penolakan pada inventaris288 | INDEPENDENT_NATIVE_RERUN pada subjek UI Chromium CI; sublabel INDEPENDENT_UI_MOCK_RERUN. Auth dan business-response tiruan; tidak menutup klaim transaksi Native. |
| Identitas, ketiadaan route pool, dampak sumber dan paginasi receipt | INDEPENDENT_SOURCE_REVIEW pada kandidat dan input writer yang dipin. |
| CodeQL | INDEPENDENT_NATIVE_RERUN untuk eksekusi pemindai statis CI, sumber kandidat persis; bukan pengganti pengujian izin SQL. |
| Angka hasil writer dan22 log gagal writer | REUSED_WRITER_EVIDENCE; bukan penutup runtime audit. |
| Sumber tak berubah yang tidak diulang | Bukti Sol lama terkunci pada seal278a95ce dan sebelumnya; tanggal/SHA lama tetap, tidak disebut fresh rerun. |
| Kebijakan tanggal/cutover/PO/menu/penundaan | Keputusan owner tertulis D15 dan register sebelumnya; otorisasi, bukan bukti runtime. |

## Pertanyaan owner

Tidak ada pertanyaan baru yang belum dijawab register. D15-1 s.d. D15-6 sudah dipakai: kas dua tanggal, hide UAT,
master/rates, reopenPO, cutover resmi, PO otomatis A. Status produksi tetap menunggu tahapan yang telah diputuskan;
auditor tidak meminta ulang izin atau mengarang tanggal/nilai kebijakan.

## Fokus tambahan

Batas penomoran menunjukkan kebutuhan uji tepat di perubahan panjang angka, di luar fixture nomor001/002.
Koreksi majemuk diuji dari keadaan akhir yang sah, sambil tetap menjaga setiap prefix harian pada dua dasar tanggal.
Sambungan per SKU dinilai secara dimensional: ukuran, SKU, komponen, tarif, upah, persediaan siap kirim dan pembalik.
Mode UAT dibuktikan terpisah dari mode disposable; bukti rute tiruan tetap diberi batasnya.

## Ringkasan owner

Audit ulang r2 sudah selesai dan semua job telah berakhir.
Lima temuan Sol sebelumnya sudah lolos uji ulang dalam cakupan yang dicatat.
Ada satu bug baru: pembuatan PO ke-1.000 pada tanggal yang sama tidak selesai.
Saat kasus itu dihentikan, stok dan data tetap utuh.
Siklus layar pool HPP absensi masih belum tersedia dan sudah diakui writer sebelumnya.
Perbaikannya serta contoh uji yang perlu dipertahankan tersedia dalam handoff.
Bukti rilis nyata yang belum lengkap tetap disebut terang, sehingga kandidat gabungan masih HOLD.
Tidak ada database online atau aplikasi produksi diubah.

## Segel dan arsip

Cabang auditor: `audit/sol-cp1-7-r2-2e9d6a46-20261016`. Daftar berkas dan hash terdapat pada `SEAL_MANIFEST.json`.
Arsip Original146berkas: `SOL_CP17_r2_2e9d6a46_20261017_EVIDENCE.zip`,9.061.841byte, SHA-256
`aee8e8002b6c090701ec384c79cdc3208bd9d889ce8e73949ae8f92c45e65864`. Penunjuk tersimpan di `PROOF_ARCHIVE_POINTER.json`.
Screenshot, SQLdump dan kode repository tidak diduplikasi ke arsip. Byte setiap laporan asli diperiksa dengan CRC ZIP
dan SHA-256; manifest membedakan anggota yang diambil dari metadata anggota ZIP yang sengaja tidak diunduh.
