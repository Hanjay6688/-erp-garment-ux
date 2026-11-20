"""Read the archived FFDA's 25 catalogue groups and compare their object identities after the BF installation."""
import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path


def digest(value):
    encoded=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


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
