# OW10 — proyeksi suplai global, kontrak sebelum pemanggil

23 Oktober2026 WIB. `cp7_reorder_supply.project(jsonb)` adalah helper privat
murni. Ia membaca **satu** hasil alokasi global; tidak mengambil WIP model dan
tidak mengalokasikan ulang. Ini tahap kernel, **belum mengganti pemanggil ROP**.
OW10 tetap OPEN sampai sumber/periode/lead, caller dan Native terbukti.

Input tertutup `cp7.reorder-supply-input.v1`: snapshot_id, scope_id
GLOBAL_NATIVE_PLANNING, scenario_id, captured_at, checked_at, source_hash,
current_source_hash, source_state CURRENT/ARCHIVED_STALE/UNKNOWN, complete_scope,
wip_status COMPLETE/UNKNOWN, allocation_status SCENARIO/UNKNOWN, query,
expected_query, budgets, targets, refs. Query kanonik punya from_date,
through_date, group_mode AS_SOLD/RESTATED. Batas teknis:5000 target,1000 posisi,
10000 entri suplai seluruh scope; bukan nilai kebijakan produksi.

Budget per **physical_key + size_id** berasal dari proyeksi barang baik dan ETA
global yang sama: physical_key, snapshot_id, size_id, projected_good_pcs, eta,
eligible. Bukan potongan mentah, bukan hitungan ulang yield. Target memegang
target_key, size_id, reorder_point_pcs, target_pcs, available_fg_pcs,
lead_deadline, deadline, supplies, refs. Supplies memakai kontrak netting lama.
Angka PCS teks integer; stok tersedia boleh negatif. Unknown tetap null.

- Seluruh kredit atas satu physical_key wajib konservatif terhadap budget yang
  sama. DIRECTED hanya untuk satu target; tidak boleh bercampur candidate.
  Candidate boleh terbagi ke beberapa target, tetapi jumlahnya tidak melewati
  budget. Duplikat persis pada target sama dihitung sekali seperti kernel lama;
  identitas, ukuran, ETA, snapshot atau jumlah bertentangan ditolak.
- DIRECTED/INCOMING yang tepat waktu masuk posisi dasar; ALLOCATED_CANDIDATE
  hanya posisi bersyarat dan perlu allocation_status SCENARIO. Jumlah tetap
  dihitung oleh `cp7_baseline.net(v2)` untuk L dan L+R, tanpa rumus kedua.
  Input WIP ini menolak INCOMING: pesanan masuk bukan posisi WIP yang ditangkap
  adapter ini dan harus memakai sumber resmi tersendiri bila ditambahkan.
- Suplai terlambat, tidak eligible, yield/ETA unknown tidak dijadikan stok
  tersedia. Kandidat tidak menyembunyikan kebutuhan produksi dasar.
- Sumber/kueri berubah, scope parsial atau WIP belum lengkap menghasilkan
  unknown untuk semua posisi; tidak memakai snapshot lama sebagai angka kini.
  Fingerprint caller wajib memakai sumber operasi/engine/kalender yang sama;
  helper murni ini tidak membuktikan kebenaran hash yang diberikan caller.
- Alokasi kandidat UNKNOWN dengan suplai terarah yang terbukti menghasilkan
  PARTIAL: posisi dasar tetap terbaca, seluruh jumlah/posisi bersyarat null dan
  status bersyarat UNKNOWN, bukan kandidat0 yang dikira sudah terbukti.
- Deadline target yang belum diketahui hanya boleh bersama supplies kosong;
  hasilnya unknown. Target hilang, key ganda, field tambahan atau null palsu
  bukan jalan pintas menjadi0.

Caller berikutnya harus mempertahankan budget posisi saat ANA_META sebelum
K3 membersihkan intermediate, memilih job DONE/kept dengan scope/kueri/hash
segar, dan memeriksa kesamaan profil/lead/target/stok dengan ROP. Ia harus
menampilkan waktu dan sifat proyeksi serta kandidat terpisah. Tanpa job cocok,
jelaskan unknown dan jalan memperbarui analisis; jangan kembali ke WIP mentah.
Pemasang, bundle dan registry A tidak diubah oleh tahap kernel ini.
