"""Render the existing coverage dispositions for human review."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


for stem, title, key, need in (
    ("INVARIANT_MATRIX", "82 invarian", "invariant", "requirement"),
    ("SCENARIO_MATRIX", "29 skenario", "id", "requirement"),
    ("CHAIN_MATRIX", "20 sambungan", "id", "chain"),
):
    x = json.loads((ROOT / (stem + ".json")).read_text())
    text = ["# Disposisi Sol r3 — " + title, "", "Kandidat `" + x["candidate_sha"] + "`. Hasil penilaian dengan batas yang tertulis; `audit_complete=false`.", "",
            "Seluruh baris mempunyai disposisi; itu berbeda dari seluruh baris PASS. " + x["qualification"], "",
            "Asal retained adalah seal Sol r2 `" + x["prior_seal"] + "`. Bukti current berasal dari eksekusi Sol atas oracle writer/warisan, lalu pembacaan Original. Contoh ID di bawah hanya indeks untuk lingkup yang dijelaskan, bukan bukti otomatis seluruh kalimat kebutuhan. Smoke, source-admission kredit nol, dan diagnosis tidak dipakai sebagai saksi produk.", "",
            "Jumlah: " + ", ".join(f"{n} {status}" for status, n in x["status_counts"].items()) + ". Tidak menjadi persentase ERP.", "",
            "| ID / kebutuhan | Disposisi | Lingkup dan batas | Contoh bukti current |",
            "|---|---|---|---|"]
    for row in x["rows"]:
        witness = row["r3_document_witnesses"]
        examples = witness["examples"][:3]
        example = "; ".join("`" + r["id"] + "` (" + r["status"] + ", run `" + str(r["run_id"]) + "`)" for r in examples)
        if not example:
            example = "Retained scope; tidak ada saksi current yang cocok pada indeks ini."
        scope = row.get("qualification", row.get("scope", ""))
        if "current_scope" in row:
            scope = row["current_scope"] + " " + scope
        text.append("| " + cell(row[key] + " — " + row[need]) + " | " + row["status"] + " dalam batas tertulis | " + cell(scope) + " | " + cell(example) + " |")
    text += ["", "Ledger rinci dan seluruh first-attempt/raw non-PASS dipertahankan dalam paket bukti; JSON matriks memuat record retained asli serta indeks saksi yang lebih lengkap. Berkas main report/handoff menjelaskan gap alat tanggal, batas pool public, backup, dan gate penerimaan.", ""]
    (ROOT / (stem + ".md")).write_text("\n".join(text))
    print(stem, len(x["rows"]))
