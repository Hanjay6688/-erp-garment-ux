"""Replay the published SKU comparator over its pinned data with controlled SQL replies."""
from datetime import date, timedelta
from hashlib import sha256
import argparse
import gzip
import tempfile
import copy
import importlib.util
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--catalogue", type=Path, required=True)
parser.add_argument("--prior-release", type=Path, required=True, help="Pinned f8520a7 qualification directory")
parser.add_argument("--candidate-release", type=Path, required=True, help="Candidate qualification directory")
args = parser.parse_args()

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name,path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

sys.path.insert(0, str(args.prior_release))
import daily_partitions as daily
old_path = args.prior_release / "realtime_comparator.py"
assert sha256(old_path.read_bytes()).hexdigest() == "e58d24c8c60d1ccff9a1f4376475c1f59332f52095476bc2a750fa7ac83e2a7c"
previous_prepare = load_module("prior_calendar",old_path).prepare
changed = load_module("writer_calendar",args.candidate_release / "realtime_comparator.py")

# Read the exact comparator from the published source patch used by the original installer.
patch = (args.prior_release/"global-preseal/global-combined.patch.gz").read_bytes()
assert sha256(patch).hexdigest() == "25930a5519c806ec439dda4c06fe5cab869896d6b78dbb461a47cd0c6b369489"
name = "scripts/current-global-sku-automatic-preparation/parent_catalogue.py"
section, = (block for block in gzip.decompress(patch).decode().split("diff --git ")
            if block.startswith(f"a/{name} b/{name}\n"))
code = "".join(line[1:] for line in section.splitlines(keepends=True)
               if line.startswith("+") and not line.startswith("+++"))
assert sha256(code.encode()).hexdigest() == "44d6c946a6a3b9364ff4bd71e434fd8d0bf0d07787649d207a88bed021400ba3"
with tempfile.TemporaryDirectory() as temp:
    path = Path(temp)/"parent_catalogue.py"
    path.write_text(code)
    original = load_module("original_parent_catalogue",path)
raw = args.catalogue.read_bytes()
pin = {"bytes": 16051957, "sha256": "ecf858d67f43c0967cfe6f38c51338dea64331ef6c0d1264786a8967f856e2a4"}
assert original.pin(raw) == pin
archive = json.loads(raw)
source, bf_day, restart = date(2026,11,13), date(2026,11,20), date(2026,11,21)

def shift_catalogue():
    shifts = {daily.partition_name(source + timedelta(days=i)).split('.')[1]:
              daily.partition_name(bf_day + timedelta(days=i)).split('.')[1] for i in range(-1,4)}
    # Change only the five reviewed table families and their registered date ranges.
    result = copy.deepcopy(archive)
    for i in range(-1,4):
        before, after = source + timedelta(days=i), bf_day + timedelta(days=i)
        name = daily.partition_name(before)
        for group, keys in daily.expected_objects(name).items():
            selected = set(keys)
            for j, (key, row) in enumerate(result[group]):
                if key not in selected: continue
                if group == 'relations' and key == name:
                    assert row[11] == daily.expected_range(before)
                    row[11] = daily.expected_range(after)
                line = json.dumps([key,row], ensure_ascii=False)
                result[group][j] = json.loads(daily.DAY_TOKEN.sub(lambda m: shifts[m[0]], line))
    for rows in result.values(): rows.sort(key=lambda e:e[0])
    return result

stored = shift_catalogue()
fp = {"contract": "cp75-offline-control", "groups":25, "counts":{k:len(v) for k,v in archive.items()}}
args = {"parent_catalogue_fingerprint":fp,"parent_catalogue_equivalence":original.reviewed_fields(raw,pin)}
params = {"archived_startup_day":source}

class ReplayCursor:
    def __init__(self, value, day, fail_guard=False):
        self.definition = dict(value['functions'])[original.CENSUS][0]
        self.day, self.fail_guard = day, fail_guard
        self.guard_calls = 0

    def execute(self, sql, params=None):
        if sql == changed.UTC_POSTMASTER_START_DAY: self.result = self.day
        elif sql == 'select pg_get_functiondef(%s::regprocedure)' and params == (original.CENSUS,):
            self.result = self.definition
        elif sql == 'select cp7_credit.assert_source_native_trigger_census_v1()':
            self.guard_calls += 1
            if self.fail_guard: raise ValueError('CONTROL_NATIVE_CENSUS_REJECTED')
            self.result = None
        else: raise AssertionError(sql)
        return self

    def fetchone(self): return (self.result,)

original_checker = previous_prepare(original, raw, pin, **params)
fresh_checker = changed.prepare(original, raw, pin, **params)
restore_checker = changed.prepare(original, raw, pin, restored_source_day=bf_day, **params)
checks = []
def check(label, checker, rows, clock, error=None, fail_guard=False):
    cur = ReplayCursor(rows, clock, fail_guard)
    def fingerprint(cursor, value):
        assert cursor is cur and value is rows
        return fp
    try:
        res=checker(cur,rows,args,fingerprint)
        if error or cur.guard_calls != 1: raise AssertionError(label)
        checks.append([label, res['status']])
        return res
    except ValueError as ex:
        if str(ex) != error: raise
        checks.append([label, str(ex)])

check("previous checker on the source date",original_checker,stored,bf_day)
check("previous checker after restart",original_checker,stored,restart,"GLOBAL_REALTIME_EXACT_FIVE_DAILY_PARTITIONS_REQUIRED")
check("fresh installation on its own day",fresh_checker,stored,bf_day)
check("fresh installation with wrong day",fresh_checker,stored,restart,"GLOBAL_REALTIME_EXACT_FIVE_DAILY_PARTITIONS_REQUIRED")
res=check("restored copy after a restart",restore_checker,stored,restart)
dates=res['realtime_daily_partitions']
assert dates['restored_source_utc_day']==str(bf_day) and dates['current_postmaster_utc_day']==str(restart)
check("restored copy a month later",restore_checker,stored,date(2026,12,21))
check("archive does not match admitted source day",restore_checker,archive,restart,"GLOBAL_REALTIME_EXACT_FIVE_DAILY_PARTITIONS_REQUIRED")
check("native guard still called",restore_checker,stored,restart,"CONTROL_NATIVE_CENSUS_REJECTED",fail_guard=True)
first = daily.partition_name(bf_day-timedelta(days=1))
for label,group,selector,mutation,error in [
    ('missing day','relations',first,None,'GLOBAL_REALTIME_EXACT_FIVE_DAILY_PARTITIONS_REQUIRED'),
    ('wrong midnight bound','relations',first,(11,'DEFAULT'),'GLOBAL_REALTIME_EXACT_DAILY_PARTITION_REQUIRED'),
    ('wrong owner','relations',first,(0,'postgres'),'GLOBAL_REALTIME_EXACT_DAILY_PARTITION_REQUIRED'),
    ('wrong parent','inheritance',first+':1','public.unrelated','GLOBAL_REALTIME_EXACT_ATTACHED_TABLE_AND_INDEXES_REQUIRED'),
    ('index removed','indexes',first+'_pkey',None,'GLOBAL_REALTIME_INCOMPLETE_DAILY_PARTITION_FOOTPRINT'),
    ('unrelated ERP change','relations',next(k for k,v in stored['relations'] if k.startswith('erp.') and v[1]=='r'),
     (0,'fake_owner'),'GLOBAL_CURRENT_PARENT_CATALOGUE_OUTSIDE_REVIEWED_SCOPE'),
]:
    values = dict(stored)
    entries = [[k,r] for k,r in stored[group]]
    j=next(i for i,(k,r) in enumerate(entries) if k==selector)
    if mutation is None: del entries[j]
    elif isinstance(mutation,str): entries[j][1]=mutation
    else:
        value=list(entries[j][1]);value[mutation[0]]=mutation[1];entries[j][1]=value
    values[group]=entries
    check(label,restore_checker,values,restart,error)

print(json.dumps({"sku_catalogue_sha256":pin["sha256"],"sku_groups":len(archive),"sku_objects":sum(map(len,archive.values())),
                  "sql_replies":"controlled for comparator replay","checks":checks,
                  "raw_original_bf_sql_read":False,"production_go":False},indent=2))
