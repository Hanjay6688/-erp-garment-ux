"""Read the archived FFDA's 25 catalogue groups and compare their object identities after the BF installation."""
import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re


def digest(value):
    encoded=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def capture_details(cur, values, folder):
    """Preserve per-field evidence and independently check the installation-local guard literal."""
    guard_name="cp7_credit.assert_source_native_trigger_census_v1()"
    row=dict(values["functions"])[guard_name]
    pattern=re.compile(r"(if actual_sha256 is distinct from ')([a-f0-9]{64})('then)")
    matches=list(pattern.finditer(row[0]))
    if len(matches)!=1:
        raise ValueError("The installed native guard must have exactly one source-bound comparison")
    capture=Path(os.environ["GITHUB_WORKSPACE"])/"auditor/scripts/cp7_customer_credit/integration/source_triggers/capture.sql"
    if hashlib.sha256(capture.read_bytes()).hexdigest()!="0ec6af17788d09a3f30ffc2adffa2f6a8e46dae8d1879664669f91995fe91f38":
        raise ValueError("The native trigger census source has changed")
    with cur.connection.transaction(force_rollback=True):
        cur.execute("set local search_path=''; set local timezone='UTC'")
        source=capture.read_text().strip().removesuffix(";")
        captured,live=cur.execute("select q.value,cp7_credit.pg_jsonb_sha256(q.value) from ("+source+") q(value)").fetchone()
    token=matches[0]
    checked=row[0][:token.start(2)]+"<LOCAL_CENSUS_SHA256>"+row[0][token.end(2):]
    receipt={"name":guard_name,"literal":token.group(2),"measured_local_census":live,
             "verified_local_literal":token.group(2)==live,"body_with_only_literal_replaced":digest(checked),
             "remaining_function_fields":digest(row[1:]),"scope_counts":{k:len(v) for k,v in captured.items()},
             "foreign_key_semantics":digest(sorted(digest(item["semantic"]) for item in captured["foreign_keys"])),
             "ordinary_attachments":sum(not item["internal"] for item in captured["triggers"]),
             "internal_attachments":sum(item["internal"] for item in captured["triggers"]),
             "production_go":False}
    (folder/"native-credit-proof.json").write_text(json.dumps(receipt,indent=2)+"\n")
    # Hash each field. Values such as function bodies and privilege-bearing text stay in PostgreSQL.
    with gzip.open(folder/"catalogue-fields.json.gz","xt",encoding="utf-8") as out:
        json.dump({g:[[k,[digest(x) for x in (v if isinstance(v,list) else [v])]] for k,v in entries]
                   for g,entries in values.items()},out,separators=(",",":"))


def capture_original(output):
    import psycopg
    from psycopg.types.json import Jsonb
    workspace=Path(os.environ["GITHUB_WORKSPACE"])
    path=workspace/"auditor/scripts/cp7_global_nonpo_envelope/catalogue_profile.py"
    raw=path.read_bytes()
    assert hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()=="00a6cb8e5f7115c0af192dce64c6b316147c6446"
    spec=importlib.util.spec_from_file_location("cp75_original_catalogue_profile",path)
    profile=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(profile)
    expected=json.loads((workspace/"source/qualification/cp75-factory-global/ffda-catalogue.json").read_text())
    with psycopg.connect(host=os.environ["PGHOST"],user="supabase_admin",dbname="cp6_rollback") as conn,conn.cursor() as cur:
        cur.execute("set transaction isolation level repeatable read read only")
        cur.execute("set local search_path=''; set local timezone='UTC'")
        official=cur.execute("select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()").fetchone()[0]
        assert official==expected["server"]
        values={}
        for group,query in sorted(profile.queries().items()):
            ordered="select k,v from("+query+')q(k,v) order by k collate "C",v::text collate "C"'
            values[group]=[list(pair) for pair in cur.execute(ordered).fetchall()]
        persisted=cur.execute("select encode(sha256(convert_to(%s::jsonb::text,'UTF8')),'hex')",(Jsonb(values),)).fetchone()[0]
        assert persisted==official["sha256"] and digest(values)==expected["full25_sha256"]
        try:
            capture_details(cur,values,output.parent)
        except Exception as exc:
            (output.parent/"catalogue-detail-error.json").write_text(json.dumps({"type":type(exc).__name__,"detail":str(exc)[:240]})+"\n")
    rows={g:[[key,digest(value)] for key,value in entries] for g,entries in values.items()}
    with gzip.open(output,"xt",encoding="utf-8") as dest:
        json.dump({"origin_run":expected["origin_run"],"server":official,"capture_sha256":digest(values),
                   "groups":{g:digest(v) for g,v in values.items()},"objects":rows},dest,separators=(",",":"))
    print("CP75_ORIGINAL_RAW_SOURCE_CONFIRMED",expected["full25_sha256"],flush=True)


def compare(original,rebuilt,measurement,out):
    with gzip.open(original,"rt",encoding="utf-8") as f:
        source=json.load(f)
    with gzip.open(rebuilt,"rt",encoding="utf-8") as f:
        local=json.load(f)
    with measurement.open() as f:
        receipt=json.load(f)
    if set(source["objects"])!=set(local) or set(source["groups"])!=set(receipt["group_hashes"]):
        raise ValueError("Full25 groups do not match")
    delta={}
    for name in sorted(local):
        ref=source["objects"][name]
        candidate=local[name]
        counts=Counter(key for key,_ in ref)
        has_duplicates=len(candidate)!=receipt["server"]["counts"][name] or any(n!=1 for n in counts.values())
        data={"raw_group_equal":source["groups"][name]==receipt["group_hashes"][name],
              "archived_count":source["server"]["counts"][name],"candidate_count":receipt["server"]["counts"][name],
              "object_hashes_complete":not has_duplicates}
        if not has_duplicates:
            indexed=dict(ref)
            all_keys=sorted(indexed.keys()|candidate.keys())
            data["different"]=[{"name":key,"archived":indexed.get(key),"reconstructed":candidate.get(key)}
                               for key in all_keys if indexed.get(key)!=candidate.get(key)]
            if data["raw_group_equal"] and data["different"]:
                raise ValueError("Equal group digest conflicts with the per-object comparison")
        delta[name]=data
    result={"origin_run":source["origin_run"],"archived_seal":source["server"]["sha256"],"local_seal":receipt["server"]["sha256"],
            "groups":delta,"changed_groups":[g for g,item in delta.items() if not item["raw_group_equal"]],
            "production_go":False}
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("CP75_CATALOGUE_GROUP_DIFF",json.dumps(result["changed_groups"]),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="operation",required=True)
    sub.add_parser("capture").add_argument("destination",type=Path)
    both=sub.add_parser("compare")
    for key in ("original","rebuilt","measurement","out"):
        both.add_argument(key,type=Path)
    args=p.parse_args()
    if args.operation=="capture":
        capture_original(args.destination)
    else:
        compare(args.original,args.rebuilt,args.measurement,args.out)
