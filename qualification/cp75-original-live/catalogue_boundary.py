"""Compare the full live catalogue with the signed Global, allowing one verified cluster-bound constant."""
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path

from psycopg.types.json import Jsonb

FUNCTION = "cp7_credit.assert_source_native_trigger_census_v1()"
PATTERN = re.compile(r"(if actual_sha256 is distinct from ')([a-f0-9]{64})('then)")
REFERENCE_TOKEN = "9c3033ea96385e5ba29b2aed974f0cac5dc5d90940f64d863bf9a965ca8a1032"
STAGES = {
    "ffda": "a3da0ecf21909731ab8474c54a7c91afb75bb58dd8b6042cc82314b20808dbd7",
    "hpp": "da0b424f305f0b423808d445034ff8a166e32a8d9d13f811078daf2c864b012b",
    "current": "deb596acb49e10ac66e0a1616a582ff74889146c0b59ee0d81ac7c2818397821",
}


def guard(cur, stage, out):
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    original = Path(os.environ["RUNNER_TEMP"]) / "cp75-original-observations"
    clean = json.loads((original/"clean-opened.json").read_text())
    ref = json.loads((original/"upgrade-opened.json").read_text())
    native = json.loads((original/"native-credit-proof.json").read_text())
    if (os.environ.get("CP75_BINDING_AUDIT") != "1" or cur.connection.info.dbname != "cp6_rollback"
            or clean["origin_run"] != 44800849536 or clean["catalogue"] != "b036261ee8902fc3be5307d54cf2b021dd2e2b419e24100655a7a338b70bad0a"
            or ref["origin_run"] != 44671146483 or ref["catalogue"] != STAGES["ffda"]
            or not native["verified_local_literal"] or native["literal"] != native["measured_local_census"]
            or native["literal"] != REFERENCE_TOKEN or native["name"] != FUNCTION):
        raise ValueError("Original archive or native census evidence does not match the independent reference")
    query_source = workspace/"auditor/scripts/cp7_customer_credit/integration/source_triggers/capture.sql"
    if hashlib.sha256(query_source.read_bytes()).hexdigest() != "0ec6af17788d09a3f30ffc2adffa2f6a8e46dae8d1879664669f91995fe91f38":
        raise ValueError("Incorrect native census reader")
    catalogue = workspace/"auditor/scripts/cp7_global_nonpo_envelope/catalogue_profile.py"
    source = catalogue.read_bytes()
    if hashlib.sha1(b"blob "+str(len(source)).encode()+b"\0"+source).hexdigest() != "00a6cb8e5f7115c0af192dce64c6b316147c6446":
        raise ValueError("Incorrect complete catalogue reader")
    spec=importlib.util.spec_from_file_location("cp75_full_catalogue_reader",catalogue)
    profile=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(profile)
    with cur.connection.transaction(force_rollback=True):
        cur.execute("set local search_path=''; set local timezone='UTC'")
        official=cur.execute("select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()").fetchone()[0]
        values={}
        for group,query in sorted(profile.queries().items()):
            ordered="select k,v from("+query+')q(k,v) order by k collate "C",v::text collate "C"'
            values[group]=[list(row) for row in cur.execute(ordered).fetchall()]
        def full_seal():
            return cur.execute("select encode(sha256(convert_to(%s::jsonb::text,'UTF8')),'hex')",
                               (Jsonb(values),)).fetchone()[0]
        if len(values)!=25 or {g:len(v) for g,v in values.items()}!=official["counts"] or full_seal()!=official["sha256"]:
            raise ValueError("The independent capture does not reproduce the unmodified PostgreSQL fingerprint")
        fn,=[value for key,value in values["functions"] if key==FUNCTION]
        match,=PATTERN.finditer(fn[0])
        raw_literal=match.group(2)
        census=query_source.read_text().strip().removesuffix(";")
        own=cur.execute("select cp7_credit.pg_jsonb_sha256(q.value) from ("+census+") q(value)").fetchone()[0]
        if raw_literal!=own:
            raise ValueError("The installed credit guard does not enforce its own raw census")
        # Only the in-memory copy used for comparison changes. The live guard, all
        # permissions, function metadata, constraints and other objects stay byte-exact.
        fn[0]=fn[0][:match.start(2)]+REFERENCE_TOKEN+fn[0][match.end(2):]
        translated=full_seal()
    receipt={"stage":stage,"raw":official["sha256"],"archived":STAGES[stage],"projected":translated,
             "raw_equal":official["sha256"]==STAGES[stage],"verified":translated==STAGES[stage],
             "object":FUNCTION,"native_literal":raw_literal,"measured_local_census":own,
             "archived_literal":REFERENCE_TOKEN,"groups":len(values),"entries":sum(official["counts"].values()),
             "production_go":False}
    out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    if not receipt["verified"]:
        raise ValueError("Other Full25 object or field differences remain at "+stage)
    return receipt["raw"]
