"""Verify the byte-exact OW04 input previously accepted before the SKU install."""
from hashlib import file_digest, sha256
from pathlib import Path
from zipfile import ZipFile
import json
import sys

ARTIFACT = 12407224140
ZIP_SIZE = 2460112
ZIP_SHA = "46db3ad31ef447a073a24630a7af5a87c667b545d797ef612b0a1b4598f2e100"
MEMBER = "CP7_OW04_CONSUMER_CLOSURE_NATIVE32.json"
REPORT_SIZE = 8166263
REPORT_SHA = "9a66b07743087e107e3d7d9298d9e517b786077f848cee79ffc326a8246c3a50"
CANDIDATE = "8c437dbe0d6e62e246b2cf0cda75fb6c19330357"


def verify(path):
    with path.open("rb") as f:
        if path.stat().st_size != ZIP_SIZE or file_digest(f, "sha256").hexdigest() != ZIP_SHA:
            raise ValueError("The complete Native32 archive differs from the released SKU input")
    with ZipFile(path) as z:
        matches = [r for r in z.infolist() if Path(r.filename).name == MEMBER]
        if len(matches) != 1 or matches[0].file_size != REPORT_SIZE:
            raise ValueError("Native32 has a missing or ambiguous original report")
        raw = z.read(matches[0])
    if sha256(raw).hexdigest() != REPORT_SHA:
        raise ValueError("The Native32 report differs from the original")
    obj = json.loads(raw)
    if (obj["candidate_commit"],obj["status"],obj["observed_case_count"],obj["hosted"],
        obj["production_go"]) != (CANDIDATE, "PASS", 32, False, False):
        raise ValueError("Unexpected Native32 acceptance or environment")
    return {"original_artifact": ARTIFACT, "archive_bytes": ZIP_SIZE, "archive_sha256": ZIP_SHA,
            "member":MEMBER, "report_bytes": REPORT_SIZE,"report_sha256": REPORT_SHA,
            "native32_source": CANDIDATE, "retained_cases":32, "actual_cases_rerun":0, "production_go":False}


if __name__ == "__main__":
    print(json.dumps(verify(Path(sys.argv[1])), indent=2))
