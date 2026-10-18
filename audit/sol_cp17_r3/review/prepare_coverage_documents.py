"""Prepare coverage documents from the sealed r2 record and already-read r3 results.

No product/test imports, database calls, network calls, or probe execution.
Witness matching is an index for the manually stated scope, not an automatic
inference that every matching ID proves every word of an invariant.
"""
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
PRIOR = "841fce45c58b7c004d1dea2f293f57e4b1fa5ba0"
PIN = "b53b5acdf260b03ebac3474e9ae837fcef6f6eb1"


def old(name):
    return json.loads(subprocess.check_output(["git", "show", PRIOR + ":audit/sol_cp17_r2/" + name], cwd=REPO))


def witnesses(ledger, pattern):
    found, seen = [], set()
    for r in ledger:
        if r["category"] in {"AUXILIARY_SMOKE", "SOURCE_ADMISSION_NO_PRODUCT_CREDIT", "DIAGNOSTIC_LEGACY", "DIAGNOSTIC_ONLY_RUN"} or r["report"] == "CP7_P19_SCALE.json":
            continue
        if not re.search(pattern, r["id"] + " " + r["report"], re.I):
            continue
        key = (r["run_id"], r["id"], r["category"])
        if key in seen:
            continue
        seen.add(key)
        found.append({k: r.get(k) for k in ["run_id", "artifact_id", "report", "group", "id", "status", "category", "internal_second_attempt"]})
    return dict(pattern=pattern, matching_occurrences=len(found), status_counts=dict(collections.Counter(r["status"] for r in found)), examples=found[:12])


THEMES = {
    "U": (r"CASH|PAYMENT|PAYROLL|P18_FULL_CYCLE|P13_FINANCE|RECEIPT_CORRECTION|MISC_CORRECTION|NOTE_CORRECTION|EXACT|REPLAY",
        "Buku/jurnal, kas dua dasar tanggal, pembayaran dan inverse pada fixture yang disaksikan. Hitungan P18, P13, receipt dan CP17 diperiksa lagi di NUMERIC_DOCUMENT_REVIEW.md."),
    "S": (r"P09_|P10_|CUTTING|E01_|E03_|REOPEN|QC_FINAL|SG02|SG01|WAVE|YEAR_364",
        "Konservasi dan prefix stok, identitas roll, satuan, WIP/FG dan active-use blockers pada keluarga yang diuji; tidak menyamakan seluruh permutasi dengan satu fixture."),
    "H": (r"COST|E06|RECEIPT_CORRECTION|HPP|P18_FULL_CYCLE|QC_FINAL|RATE_CHOICE|R3_09",
        "Biaya bahan→WIP→FG→COGS, recost ekonomi/pengakuan, unknown dan revisi upah. Perubahan Native snapshot lewat bundle tarif masuk lingkup; supabase/ yang tetap bukan alasan menganggap Native tetap."),
    "P": (r"PAYMENT|RETURN|CREDIT|P11_|P13_|P18_FULL_CYCLE|HISTORY_",
        "Sisa per dokumen, kredit/uang muka, retur dan aging diperiksa dalam jalur yang dideklarasikan, bukan seluruh data aktual."),
    "T": (r"PERIOD|CLOSED|E06|YEAR_364|DATE|CUTOVER|R3_04|FIN02",
        "Tanggal WIB dan ekonomi/pengakuan, filing tertutup, cutover-floor sintetis. Rollover alat dicatat; tidak dianggap otomatis bug tanggal produk."),
    "L": (r"ANALYSIS|FINANCE_READ|HISTORY|AUDIT_|WAREHOUSE|REPORT|P19_|P18_FULL_CYCLE",
        "Pembaca publik/arsip, confidence/unknown dan proyeksi yang diuji. Snapshot/revisi tidak dianggap arbitrary as-known atau bukti seluruh permukaan kebocoran."),
    "R": (r"F04_|F05_|P05_|P06_|P14_|P15_|P19_|PLANNER|FABRIC_RULE",
        "Kernel Native/model/netting/material/supply dan aplikasi sah pada suite F04/F05/P19. Model privat positif terpisah dari promosi histori operasional nyata."),
    "K": (r"CORRECTION|REVERSE|REVERS|IMMUTABLE|APPEND|LINEAGE|YEAR_364|RESTORE|TYPO",
        "Koreksi Native dan lineage, inverse/replace atomik, waktu ekonomi, dokumen posted tetap serta refusal sesuai fixture. Tidak memakai temuan cash lama yang sudah CLOSED."),
    "C": (r"REPLAY|UUID|RACE|STALE|TOKEN|FAILURE|ATOMIC|RECOVERY|LOST|CURRENT|BOUNDARY",
        "UUID, token, dua sesi, kegagalan terakhir, lost answer dan cleanup yang tercatat. Race memakai test claims sesuai label; HTTP/browser memakai real Auth; keduanya tidak disamakan."),
    "A": (r"ACCESS|AUTH|PERMISSION|ROLE|REVOK|DENIED|PRIVATE|FACADE|GUARDS|CURRENT",
        "Bukti akses yang sudah dijalankan dan kontrak sumber diwarisi; tambahan probe keamanan tidak dibuat/dijalankan setelah pembatasan sesi. Pengecualian privat D14-9 tetap berlabel sendiri."),
    "UI": (r"BROWSER|RECOVERY|LOST|LARGE|EXACT|HISTORY|WAREHOUSE|REMINDERS|ERP_SETTINGS",
        "Browser disposable dan Enteng-build yang diintersep lokal. Ordinary CP17 21 INCOMPLETE tetap terlihat; sensus demo bukan verifikasi semua layar connected atau perangkat fisik."),
    "POL": (r"POLICY|PENDING|UNKNOWN|WAIVED|FREE|R3_09|MODE|ERP_SETTINGS|HPP_POOL",
        "Keputusan D14–D16 dibaca; pending bukan nol. Tarif pilihan dan mode baru hanya Owner/Admin; perubahan snapshot Native dideklarasikan dan diuji."),
    "M": (r"CUTOVER|IMPORT|OPENING|P21|REHEARSAL|INSTALL|ROLLBACK",
        "Import/opening sintetis, rehearsals dan baseline konstruksi terpisah dari cutover serta pemasangan hosted nyata."),
    "N": (r"RULE|REMINDER|ALERT|ACK|SNOOZE|EPISODE",
        "Episode/rule, ACK/snooze dan manual reminders pada transport lokal; tidak ada pengiriman ke penerima nyata atau penerimaan delivery live."),
    "D": (r"DETECTOR|INTEGRITY|CHECKS|HPP|COST|FULL_CYCLE",
        "Hasil detektor yang dilaporkan dan asal seal lama dicatat; nol akhir tidak mengganti exact 0 → +1 → 0 setiap detektor atau before/after setiap skenario."),
}

INCOMPLETE = {
    "INV-T02": "Fasad pool baru menolak periode tertutup. Sumber CP4 dan observasi grant efektif pada run Sol mengonfirmasi empat wrapper public lama tetap executable oleh authenticated, tanpa melalui guard fasad baru. Dampak mutasi periode tertutup lintas-entrypoint belum diuji; cakupan periode global belum ditutup, bukan product FAIL mutasi terbukti.",
    "INV-T04": "Arsip immutable/revisi diuji; arbitrary as-known untuk seluruh fakta terlambat belum dibuktikan.",
    "INV-L07": "Bukti izin pada jalur yang diuji tersedia, tetapi semua alternatif API/cache/prompt dan tambahan probe yang ditahan belum ditutup.",
    "INV-UI04": "Desktop/phone sintetis ada, tetapi ordinary CP17 21 INCOMPLETE dan perangkat fisik/iPad serta seluruh loaded state tidak dikualifikasi lengkap.",
    "INV-POL03": "Sisa teks cash SOL-R1-001 lama dikoreksi: CLOSED menurut RETEST_DISPOSITIONS r2 dan kontrol current. Satu sumber aturan secara global serta seam pembungkus pool publik belum dibuktikan; tidak membuka ulang cash yang sudah sembuh.",
    "INV-M01": "Saldo awal nyata dan satu periode shadow/cutover tidak dijalankan; fixture sintetis tidak menggantinya.",
    "INV-M03": "Tidak ada cutover nyata, sehingga pemeriksaan sesudah cutover nyata tidak diberi PASS.",
    "INV-M04": "Baseline hosted nyata yang fresh dan pemasangan CP7C tidak disentuh. Rehearsal konstruksi dan restore-drill diberi batas terpisah.",
    "INV-D01": "Tidak setiap detektor mendapat exact 0 → +1 → 0 pada run ini; tambahan probe tidak dijalankan. Kontrol terbatas dari seal lama dipertahankan asalnya.",
    "INV-D04": "Belum ada inventaris before/after seluruh detektor untuk masing-masing 29 skenario; nol akhir suite tidak cukup.",
}

SPECIFIC = {
    "INV-U01": r"FULL_CYCLE|E06_|HPP_POOL_CREATE_ACTIVATE|RF_PRICE_AFTER",
    "INV-U02": r"REPLAY|SAME_UUID|ONCE|EXACT_ZERO",
    "INV-U03": r"INVERSE|CANCEL_NEW_RATE|REVERSE|REVERSAL|CANCEL_RETURN",
    "INV-U04": r"FULL_CYCLE|FINANCE_LIFECYCLE|HISTORY_EVENTS_AND_BALANCES|NEW_RATE_WAGE_TO_PAYROLL",
    "INV-U05": r"^CP17_CASH_|R2_CASH_BOOK_DATE|SPENT_INCOME|CASH_PREFIX",
    "INV-U06": r"EXACT|CENT|LARGE|ROUND",
    "INV-U07": r"OVERPAY|OVER_PAYMENT|PAID_EXCEEDS|CREDIT|PAYMENT_LIMIT",
    "INV-U08": r"PAYMENT|PAYROLL|NEW_RATE_WAGE_TO_PAYROLL",
    "INV-S02": r"BACKDATE|PREFIX|BEFORE_USE|BELOW_USE|CHRONO|REOPEN_REPOST_CARD",
    "INV-S03": r"TRANSFER|WRONG_MATERIAL|MATERIAL_CROSS",
    "INV-S04": r"ROLL_NUMBER|DUPLICATE_LINES_KEEP_LOT|ROLL_COUNT|MATERIAL_NAME_TYPO",
    "INV-S05": r"UOM|DOZEN|GROSS|UNIT|SERIES",
    "INV-S06": r"ASTRA_G1_G2|WAVE|UNSEWN|UNSENT|WIP|SEWING_RECORD",
    "INV-S07": r"QC_FINAL|RETURN_STOCK|FG_ADJUST|P10_|SG02",
    "INV-H01": r"FULL_CYCLE|RF_PRICE|E06_|HPP_POOL_CREATE|QC_FINAL",
    "INV-H02": r"FULL_CYCLE|COST_CONTINUATION|RECEIPT_CORRECTION|NEW_RATE_WAGE",
    "INV-H03": r"E06_|ECONOMIC|BOOK_DATE|YEAR_END|INVOICE_PRICE_AFTER|LATE",
    "INV-H04": r"GRNI|FINAL_INVOICE|INVOICED|INVOICE_PRICE|LATE",
    "INV-H05": r"RF_PRICE_AFTER_SALE_AND_RETURN|COST_CONTINUATION|FULL_CYCLE|E06_",
    "INV-H06": r"PENDING|UNKNOWN|NONFINAL|FREE|WAIVED|LAUNDRY",
    "INV-P01": r"HISTORY_EVENTS_AND_BALANCES|FULL_CYCLE|CREDIT|PAYMENT|REFUND",
    "INV-P02": r"ADVANCE|CREDIT|FIN02_CLAIM_BEFORE|SOURCE_DATE",
    "INV-P03": r"AGING|DUE|REVERSALS_LISTED|HISTORY|OBLIGATION",
    "INV-T01": r"E06_|UTC|TIMEZONE|WIB|MICROSECOND|DATE_BOUNDARY",
    "INV-T02": r"CLOSED|PERIOD|ECONOMIC|REOPEN|HPP_POOL",
    "INV-T03": r"FUTURE|ARRIVAL_DATE|BEFORE_SOURCE|BEFORE_CUT",
    "INV-L02": r"ARCHIVE|REVISION|IMMUTABLE|AS_KNOWN|FILING",
    "INV-L03": r"UNKNOWN|PENDING|NULL|NO_DATA|NOT_ZERO",
    "INV-L04": r"CONFIDENCE|READY|UNKNOWN|NONFINAL|PENDING|CLOSE",
    "INV-L05": r"PERIOD_COMPAR|COMPARISON|DAY_FULL|YEAR|TZ",
    "INV-L06": r"READ_ONLY|READONLY|BOUNDARY|UNCHANGED|CAPTURE|PUBLIC_READ",
    "INV-R01": r"UNKNOWN|STALE|SOURCE_CHANGED|PENDING|BASELINE|HISTORY",
    "INV-R02": r"ACTION|CARD|DEADLINE|EXPLAIN|SOURCE|PLAN",
    "INV-R03": r"PRIORITY|GAP|RANK|DEADLINE|STABLE",
    "INV-R04": r"NETTING|DRAFT|RESERVATION|DOUBLE|SURPLUS",
    "INV-R05": r"SUPPLY|DELAY|SCHEDULE|ARRIVAL",
    "INV-R06": r"MODEL|PROMOT|SELECTOR|HOLDOUT|FOLD|SES",
    "INV-R07": r"AI|PROMPT|PROJECTION|QUESTION",
    "INV-R08": r"APPLY|READ_ONLY|CAPTURE|SOURCE_CHANGED|NETTING",
    "INV-R09": r"CUTTING_MODEL|YIELD|FABRIC_NEED|FABRIC_RULE|RECIPE",
    "INV-K01": r"CORRECTION|IMMUTABLE|SOURCE_UNCHANGED|RESTORE",
    "INV-K02": r"ECONOMIC|E06_|YEAR_|BOOK_DATE|DATE_MOVE|CLOSED_PERIOD_CORRECTION",
    "INV-K03": r"DUPLICATE|LINEAGE|TWO_ALLOCATIONS|SAME_LINE|ROLL_NUMBER",
    "INV-K04": r"DECLARED|IMMUTABLE_HISTORY|LINEAGE|NATIVE_DELTAS",
    "INV-K05": r"DRAFT.*BLOCK|BLOCK.*DRAFT|ACTIVE_USE|INVOICE_INCOMPLETE|DOWNSTREAM",
    "INV-K06": r"REPEATED|REVISION|ONE_CARD|MICROSECONDS|ONE_TRANSACTION",
    "INV-K07": r"APPEND|IMMUTABLE|REVISIONS_IMMUTABLE|POSTED_EDIT",
    "INV-C01": r"UUID|REPLAY|SAME_REQUEST",
    "INV-C02": r"STALE|REVIEW|TOKEN|VERSION",
    "INV-C03": r"RACE|SIMULTANEOUS|CONCURRENT",
    "INV-C04": r"FAILURE|ATOMIC|MIDWAY|FINAL_POST",
    "INV-C05": r"LOST|RECOVERY|RESEND|RECOVER|SAME_REQUEST",
    "INV-A01": r"CURRENT|REVOK|PERMISSION_REMOVED|AUTHORITY",
    "INV-A02": r"INACTIVE|DEACTIVAT|ROLE|DENIED|ANONYMOUS",
    "INV-POL01": r"PENDING|POLICY|ERP_SETTINGS",
    "INV-POL02": r"PENDING|UNCONFIGURED|UNKNOWN|SHARED_SPLIT",
    "INV-POL04": r"FREE|WAIVED|LAUNDRY|POLICY",
    "INV-M02": r"IMPORT|CUTOVER.*FAILURE|CUTOVER.*UUID|OPENING",
    "INV-N01": r"EPISODE|ALERT|RULE|REMINDER|NO_CURRENT_GAP",
    "INV-N02": r"ACK|SNOOZE|RULE|REMINDER|NATIVE_BUSINESS_UNCHANGED",
}

QUALIFIED = {
    "INV-U05": "Kas diuji pada tanggal ekonomi dan buku sesuai D15-1, pada keadaan akhir command. Keterangan r2 'POSTED0→−1' adalah sejarah SOL-001 yang sudah CLOSED, bukan current failure; kontrol cash current juga PASS.",
    "INV-H06": "Owner D11 LAU-DEC04 ALLOW_PENDING mengatasi contoh lama panduan: penjualan dapat sah dengan HPP belum final; label nonfinal tetap, tutup buku diblokir, dan recost diuji. Bukan memaksa semua penjualan pending ditolak.",
    "INV-A03": "Build/run client-artifact scan dan source-contract checks current lulus. CodeQL awal selesai dengan 0 results tetapi binding gate FAIL karena metadata alat Sol. Q1 terpisah memvalidasi pin b53/tree dan workflow SHA, seluruh manifest/SARIF lulus. Hasil awal tetap utuh; seluruh permukaan akses tidak diklaim sudah habis diuji.",
    "INV-A04": "Advisor delta current dicatat dan gate whitelist lulus pada Original yang dibaca; INFO RLS-no-policy pada tabel privat deny-all bukan otomatis akses publik. Tambahan probe keamanan tidak dijalankan.",
    "INV-A05": "Exact private grant/body/exposure checks yang sudah berjalan ditelaah sesuai D14-9. Tidak memperluas penerimaan 82 writer erp privat ke pembungkus publik pool; batas itu dicatat pada INV-T02/POL03.",
    "INV-C06": "Indeks memeriksa flag full_boundary_restored/public_schema_unchanged dan session_leaks per baris yang menyediakannya; hasil struktural dirujuk dari RESULT_DOCUMENT_REVIEW_PARTIAL.json. Mode copy-per-race/HTTP/browser punya cleanup terpisah, tidak diklaim sebagai savepoint Native yang sama.",
    "INV-M05": "Refusal guards terdahulu dipertahankan asalnya; pemasangan/rehearsal disposable current ditelaah terpisah. Riwayat penyebab kegagalan AZ pertama yang belum diketahui tidak dihapus atau dianggap current positive install failure.",
    "INV-POL05": "COUNTEREXAMPLE yang diterima owner tetap COUNTEREXAMPLE dalam Original/seal asalnya. Tidak direlabel PASS untuk menyamakan warna job; current reproduksi yang tidak tersedia diberi batas retained-only.",
}

SCENARIO_PATTERNS = {
    1:"YEAR_364|YEAR_HISTORY|YEAR_FINAL|364", 2:"LATE|INVOICE|COST|RECEIPT_CORRECTION|E06",
    3:"CLOSED|PERIOD|REOPEN",4:"PAYMENT|REFUND|ADVANCE|CREDIT",5:"RETURN|REFUND",
    6:"DUPLICATE|IDENTICAL|LINEAGE",7:"EXACT|CENT|LARGE|ROUND",8:"NULL|UNKNOWN|ZERO|NEGATIVE|INVALID|REFUS",
    9:"DATE|E06|YEAR|ROLLOVER|CASH",10:"RACE|UUID|REPLAY",11:"CURRENT|AUTH|RECOVERY|LOST|REVOK|INACTIVE",
    12:"DRAFT|POST|REVERSE|REVISION|REPEATED",13:"BACKDATE|PREFIX|CHRONO|STOCK",14:"SCOPE|SUPPLIER|VENDOR|MANDOR|WAREHOUSE",
    15:"TYPO|MATERIAL|WAREHOUSE|SUPPLIER|DATE",16:"CUTOVER|IMPORT|OPENING",17:"UNKNOWN|PENDING|YIELD|SUPPLY|F04|F05",
    18:"REPORT|READ|RACE|IMMUTABLE",19:"DETECTOR|APPEND|INTEGRITY",20:"RANGE|SKU|MEMBER|IDENTITY",
    21:"REHEARSAL|INSTALL|ROLLBACK",22:"FULL_CYCLE|CHAIN|OPENING|E01",23:"REGRESSION|BASELINE|BRIDGE",
    24:"PLANNER|MATCH|ALLOC|NETTING|MATERIAL_APPLY",25:"WAIVED|FREE",26:"LARGE|PAGE|PAGING|LIMIT|1000|10000|EXACT",
    27:"CORRECTION|REVERSE|REPLAY|DRAFT",28:"IDENTITY|SKU|MEMBER|REVERSED|WAVE|SNAPSHOT",29:"BROWSER|AI|PROMPT|RULE|REMINDER|AUTH",
}

SCENARIO_OVERRIDES = {
    7:("INCOMPLETE","Bukti sen ganjil/angka besar retained dan current tersedia, tetapi semua jalur 1/3 dan ekstrem belum ditelusuri. Oracle AR 22,65 mandiri tambahan belum dieksekusi."),
    9:("INCOMPLETE","Bukti WIB/timezone tersedia, tetapi 60 hasil pertama tetap INCOMPLETE: 21 ordinary CP17 serta 39 dalam lima kelompok internal. Belum ada penerimaan endurance tengah malam penuh yang bersih."),
    16:("INCOMPLETE","OWNER_DEFERRED: cutover dan satu periode shadow nyata di luar pelaksanaan putaran ini; impor sintetis dipisahkan."),
    19:("INCOMPLETE","Sensitivitas tepat +1 belum dibuktikan pada setiap detektor; probe terkendali tambahan tidak dijalankan."),
    21:("INCOMPLETE","OWNER_DEFERRED: pemasangan dari fresh baseline hosted sebenarnya tidak dilakukan. Restore/rehearsal disposable konstruksi dicatat terpisah."),
    22:("INCOMPLETE","Teks cash FAIL lama sudah basi: disposisi r2 CLOSED dan kontrol koreksi current PASS. Beberapa rantai layar konkret PASS, tetapi seluruh rantai CP1–7 beserta koreksi/laporan/rekomendasi dan setiap oracle integritas belum dibuktikan sebagai satu inventaris."),
    24:("INCOMPLETE","Kernel/matcher/netting dan jalur apply publik tertentu diuji; tidak ada klaim seluruh varian matcher → allocator → command sudah tertutup."),
    26:("INCOMPLETE","PO 1000/1001/10000 serta kontrol source/pages/uang besar diuji. P19 lima kasus adalah pengukuran 48 sampel dengan cap/refusal; 18 sampel direct/finance tanpa pengecualian melewati sasaran berat 3 detik, sehingga bukan penerimaan kinerja. Semua cast, skala, writer, pagination dan export belum ditelusuri; tidak ada N/A 32-bit secara global."),
    27:("INCOMPLETE","Koreksi spent-income lama sudah CLOSED; receipt/nota/retur/pembayaran current berhasil. Inventaris setiap transaksi melalui create → edit draft → post → koreksi sah → seluruh pembaca hilir masih terbatas."),
    29:("INCOMPLETE","Jalur real Auth RPC/browser/report/AI/rule terpilih diuji. Kelengkapan alternatif API/cache/prompt, perangkat fisik dan pengiriman nyata belum terbukti; probe akses tambahan ditahan."),
}

CHAIN_UPDATES = {
    "B1":("PASS","P09 Native/HTTP/browser pada kandidat current; master supplier/bahan harian juga dilalui CP17 Enteng.","P09_|MASTER_SUPPLIER|MASTER_FABRIC"),
    "B2":("PASS","Nomor PO 1000/1001/10000 dan atomisitas auto-PO menutup SOL-R2-001 dalam lingkup uji; bukan klaim semua ukuran integer.","AUTO_PO|CUTTING|E01"),
    "B3":("PASS","Master baru/Mandor/tarif → pickup → sewing serta pickup inverse; bukan seluruh 13 tahap browser sekaligus.","MASTER_WORKFORCE|D15_3|PICKUP|SG01"),
    "B4":("PASS","Sewing dasar dan per-SKU/pilihan tarif Native serta Enteng PASS; dua kasus ordinary pilihan tarif tetap INCOMPLETE karena rollover.","SEWING|R3_09|WAVE"),
    "B5":("INCOMPLETE","Regresi komponen Laundry dipisahkan dari satu perjalanan pengguna sewing → kirim → terima → QC tanpa putus.","LAU_|LAUNDRY|SG03|FIN02"),
    "B6":("INCOMPLETE","Komponen vendor/AP/kas serta jalur sah/refusal belum membuktikan seluruh sambungan browser invoice Laundry → AP → pembayaran sebagai satu perjalanan.","VENDOR|LAUNDRY|FIN02|CASH"),
    "B7":("PASS","QC final SKU Enteng desktop/HP mem-post 10 GOOD, nilai 120, satu jurnal, tanpa WIP event tambahan. Sumber Laundry adalah fixture sah, bukan demonstrasi penerimaan lewat layar.","QC_FINAL|P10_|FG_"),
    "B8":("PASS","Finish/reopen dengan active-use blockers dan HPP tetap; biaya sumber/status ready terjaga dalam fixture.","FINISH|REOPEN|HPP"),
    "B9":("PASS","Buku FG, adjustment dan konversi merek pada stack akhir; bukan semua permutasi atau satu rantai penuh 13 tahap.","P10_|BOOK|BRAND|CONVERSION"),
    "B10":("PASS","P11 sales/draft/reservasi/series-lusin serta rantai Enteng FG → penjualan → AR nol.","P11_|SERIES_DOZENS|CHAIN_FG"),
    "B11":("PASS","Teks cash FAIL r2 yang basi dikoreksi. Kontrol spent-income P11/CP17 current serta invoice 30000 / pembayaran 30000 / AR 0 pada rantai Enteng berhasil.","PAYMENT|CHAIN_FG_TO_AR|SPENT_INCOME|P11_"),
    "B12":("PASS","Retur/koreksi/refund current mempunyai bukti; hasil HTTP rollover pertama disimpan terpisah dari eksekusi kedua.","RETURN|REFUND"),
    "B13":("PASS","Rantai konkret sewing → nota → payroll → kas → laporan/tutup/buka serta rekonsiliasi P13. Bukan satu rantai seluruh 13 tahap; cash FAIL lama yang basi dihapus dari putusan current.","CHAIN_SEWING|P13_|FULL_CYCLE|CASH|JOURNAL"),
    "S1":("PASS","Settlement/koreksi/AP/kas supplier dan guard tanggal kas current; cash lama yang sudah CLOSED tidak dibuka ulang.","SUPPLIER_PAYMENT|SUPPLIER_CREDIT|CASH"),
    "S2":("PASS","Komponen retur/kredit supplier dengan lineage, tanggal dan nilai yang tetap dapat ditelusuri; bukan semua permutasi produksi.","P09_RETURN|CREDIT|SUPPLIER"),
    "S3":("PASS","Lifecycle/replacement pool HPP Enteng serta work/rework/nota/payroll menutup gap UI. Ordinary pool browser INCOMPLETE dan batas wrapper publik lama tetap eksplisit.","HPP_POOL|PAYROLL|KASBON|BS_REWORK"),
    "S4":("PASS","Enteng nota POST → REVERSE → POST → payroll PREPARE → APPROVE → PAY: 6000 − 2100 = 3900; nota dibatalkan 1500 tidak dipotong. Assertion tanggal ordinary browser INCOMPLETE.","ACCESSORY_NOTE_TO_PAYROLL|E24_|NOTE_"),
    "S5":("PASS","Rantai positif BS/rework/nota/payroll dan aturan rewash produk sama; bukan setiap permutasi partial/QC dalam satu perjalanan layar.","BS_REWORK|REWORK|REDYE|SG03"),
    "S6":("PASS","Komponen opname FG/bahan dan inverse GL. Material count pertama 14 PASS + 3 INCOMPLETE dipisahkan dari kedua 17 PASS; tidak otomatis dihijaukan.","COUNT_|ADJUST|P10_"),
    "S7":("PASS","Opening/impor sintetis → WIP/merek/penjualan/pembayaran serta kelanjutan BS/rework. Cutover/hosted/shadow nyata tetap ditunda.","IMPORT_WIP|CUTOVER|OPENING|E01_BRIDGE"),
}


def write(name, x):
    (ROOT/name).write_text(json.dumps(x,indent=2,ensure_ascii=False)+"\n")


def main():
    ledger=json.loads((ROOT/"CASE_LEDGER_PARTIAL.json").read_text())
    registry=json.loads((ROOT/"CI_RUN_DISPOSITIONS.json").read_text())
    assert registry["original_status_counts"]=={"failure":3,"success":78}
    common=dict(candidate_sha=PIN,report_state="FINAL_LIMITED_SCOPE_ASSESSMENT",audit_complete=False,
        prior_seal=PRIOR,evidence_ledger="CASE_LEDGER_PARTIAL.json",evidence_ledger_sha256=hashlib.sha256((ROOT/"CASE_LEDGER_PARTIAL.json").read_bytes()).hexdigest(),
        evidence_origins=["RETAINED_SOL_R2_SEAL","INDEPENDENT_SOL_EXECUTION_OF_WRITER_OR_INHERITED_ORACLES_DOCUMENT_REVIEW"],
        qualification="PASS hanya untuk lingkup yang disaksikan/retained pada tiap baris, bukan penerimaan ERP penuh. Probe tambahan baru belum dieksekusi. Pencocokan ID adalah indeks tinjauan, bukan bukti otomatis.")
    invariants=[]
    for r in old("INVARIANT_MATRIX.json"):
        family=re.match(r"INV-([A-Z]+)",r["invariant"])[1]
        pattern,basis=THEMES[family]
        pattern=SPECIFIC.get(r["invariant"],pattern)
        status="INCOMPLETE" if r["invariant"] in INCOMPLETE else "PASS"
        invariants.append(dict(invariant=r["invariant"],requirement=r["requirement"],status=status,
            current_scope=basis,qualification=INCOMPLETE.get(r["invariant"],QUALIFIED.get(r["invariant"],"Lingkup bukti terkualifikasi; tidak melampaui cakupan seal lama serta hasil current spesifik yang dirujuk.")),
            retained_prior_record=r,r3_document_witnesses=witnesses(ledger,pattern)))
    write("INVARIANT_MATRIX.json",dict(common,denominator=82,status_counts=dict(collections.Counter(r["status"]for r in invariants)),rows=invariants))
    guide=(REPO/"docs/AUDIT_PANDUAN_PRO_MAX.md").read_text()
    requirements=dict(re.findall(r"- \*\*(SKN-\d+)\*\* ([^\n]+)",guide))
    scenarios=[]
    for r in old("SCENARIO_MATRIX.json"):
        n=int(r["id"].split("-")[1]);override=SCENARIO_OVERRIDES.get(n)
        status=override[0] if override else "PASS"
        scenarios.append(dict(id=r["id"],requirement=requirements[r["id"]],status=status,
            qualification=override[1] if override else "Eksekusi current atas oracle writer/warisan ditambah cakupan lama yang dipertahankan secara eksplisit. Tidak menjadi persentase ERP keseluruhan.",
            retained_prior_record=r,r3_document_witnesses=witnesses(ledger,SCENARIO_PATTERNS[n])))
    write("SCENARIO_MATRIX.json",dict(common,denominator=29,status_counts=dict(collections.Counter(r["status"]for r in scenarios)),rows=scenarios))
    chains=[]
    for r in old("CHAIN_MATRIX.json")["rows"]:
        status,boundary,pattern=CHAIN_UPDATES[r["id"]]
        chains.append(dict(id=r["id"],chain=r["chain"],status=status,scope=boundary,application_pages=r["application_pages"],
            retained_prior_record=r,r3_document_witnesses=witnesses(ledger,pattern)))
    write("CHAIN_MATRIX.json",dict(common,denominator=20,reviewed=20,all_20_one_browser_chain_proven=False,
        status_counts=dict(collections.Counter(r["status"]for r in chains)),rows=chains))
    print("FINAL_LIMITED_SCOPE", "invariants",dict(collections.Counter(r["status"]for r in invariants)),"scenarios",dict(collections.Counter(r["status"]for r in scenarios)),"chains",dict(collections.Counter(r["status"]for r in chains)))


if __name__ == "__main__":
    main()
