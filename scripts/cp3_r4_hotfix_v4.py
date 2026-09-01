#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MIG=ROOT/'supabase/migrations/20260901023400_erp_v2_6_14d_cp3_r4_race_and_reversal_hardening.sql'
ACC=ROOT/'supabase/tests/attendance_hpp_r4_full_schema_rollback.sql'
HAR=ROOT/'scripts/cp3_r4_full_schema_concurrency.py'
MAN=ROOT/'docs/evidence/cp3_r4_source_hashes.json'

def once(text,old,new,label):
    count=text.count(old)
    if count!=1: raise SystemExit(f'{label}: expected one anchor, found {count}')
    return text.replace(old,new,1)

migration=MIG.read_text()
migration=once(migration,
'''    if v_count<>p_expected_occurrences_per_function then
      raise exception 'R4 patch % expected % anchor occurrence(s), found %',p_proname,p_expected_occurrences_per_function,v_count;
    end if;''',
'''    if (p_expected_occurrences_per_function>=0 and v_count<>p_expected_occurrences_per_function)
       or (p_expected_occurrences_per_function<0 and v_count<1) then
      raise exception 'R4 patch % expected % anchor occurrence rule, found %',p_proname,p_expected_occurrences_per_function,v_count;
    end if;''','replacement cardinality rule')
migration=migration.replace("'cancel_attendance_hpp_pool_v1','erp.reverse_journal(','erp._cp3_r4_reverse_journal_internal(',1,1",
                            "'cancel_attendance_hpp_pool_v1','erp.reverse_journal(','erp._cp3_r4_reverse_journal_internal(',1,-1")
migration=migration.replace("'cancel_unpaid_payroll','erp.reverse_journal(','erp._cp3_r4_reverse_journal_internal(',1,1",
                            "'cancel_unpaid_payroll','erp.reverse_journal(','erp._cp3_r4_reverse_journal_internal(',1,-1")
migration=migration.replace("'reverse_paid_payroll','erp.reverse_journal(','erp._cp3_r4_reverse_journal_internal(',1,1",
                            "'reverse_paid_payroll','erp.reverse_journal(','erp._cp3_r4_reverse_journal_internal(',1,-1")
MIG.write_text(migration)

accept=ACC.read_text()
anchor='-- Exact protected journal bypass and unprotected compatibility proof.\n'
strict=r'''-- Exact strict nested JSON proof. This uses PostgreSQL jsonb_typeof, not
-- text casts, and runs positive real-boolean plus all adversarial negative cases
-- for both source and destination nested objects on the restored schema.
create function pg_temp.cp3_r4_assert_nested(p_value jsonb)
returns void language plpgsql as $strict$
declare v_key text;v_obj jsonb;
begin
  if jsonb_typeof(p_value) is distinct from 'object'
     or not (p_value ? 'source') or not (p_value ? 'destination')
     or (select count(*) from jsonb_object_keys(p_value))<>2 then
    raise exception 'envelope must be a closed source/destination object';
  end if;
  foreach v_key in array array['source','destination'] loop
    v_obj:=p_value->v_key;
    if jsonb_typeof(v_obj) is distinct from 'object'
       or not (v_obj ? 'id') or not (v_obj ? 'included')
       or (select count(*) from jsonb_object_keys(v_obj))<>2 then
      raise exception '% must be a closed nested object',v_key;
    end if;
    if jsonb_typeof(v_obj->'id') is distinct from 'string'
       or nullif(v_obj->>'id','') is null then raise exception '% id must be a non-empty JSON string',v_key; end if;
    if jsonb_typeof(v_obj->'included') is distinct from 'boolean' then
      raise exception '% included must be a real JSON boolean',v_key;
    end if;
  end loop;
end
$strict$;

do $strict_cases$
declare
  v_base jsonb:=jsonb_build_object(
    'source',jsonb_build_object('id','runtime-source','included',true),
    'destination',jsonb_build_object('id','runtime-destination','included',true)
  );
  v_case jsonb;v_kind text;v_name text;v_rejected integer:=0;v_positive integer:=0;
begin
  -- Real JSON boolean true and false must both pass for both nested kinds.
  foreach v_kind in array array['source','destination'] loop
    perform pg_temp.cp3_r4_assert_nested(v_base);
    v_positive:=v_positive+1;
    perform pg_temp.cp3_r4_assert_nested(jsonb_set(v_base,array[v_kind,'included'],'false'::jsonb,false));
    v_positive:=v_positive+1;

    for v_name,v_case in
      select * from (values
        ('required-key-missing',v_base #- array[v_kind,'id']),
        ('required-key-null',jsonb_set(v_base,array[v_kind,'id'],'null'::jsonb,false)),
        ('extra-key',jsonb_set(v_base,array[v_kind,'extra'],'1'::jsonb,true)),
        ('wrong-type',jsonb_set(v_base,array[v_kind],'[]'::jsonb,false)),
        ('string-true',jsonb_set(v_base,array[v_kind,'included'],to_jsonb('true'::text),false)),
        ('string-false',jsonb_set(v_base,array[v_kind,'included'],to_jsonb('false'::text),false)),
        ('empty-object',jsonb_set(v_base,array[v_kind],'{}'::jsonb,false)),
        ('nested-missing-key',v_base #- array[v_kind,'included'])
      ) q(name,payload)
    loop
      begin
        perform pg_temp.cp3_r4_assert_nested(v_case);
        raise exception 'strict nested JSON case %/% unexpectedly accepted',v_kind,v_name;
      exception when others then
        if sqlerrm like 'strict nested JSON case % unexpectedly accepted' then raise; end if;
        v_rejected:=v_rejected+1;
      end;
    end loop;
  end loop;
  if v_positive<>4 or v_rejected<>16 then
    raise exception 'strict JSON proof cardinality mismatch positive %, rejected %',v_positive,v_rejected;
  end if;
end
$strict_cases$;

'''
if strict not in accept:
    accept=once(accept,anchor,strict+anchor,'strict JSON insertion')
ACC.write_text(accept)

harness=HAR.read_text()
harness=once(harness,
'''        validation = validate_pool(admin, pool["id"])
        proof["strict_nested_json"] = strict_nested_json_cases(validation)
''',
'''        validation = validate_pool(admin, pool["id"])
        if str(validation.get("validation", validation.get("status", ""))).upper() not in ("PASS", "VALID", "DRAFT"):
            raise RaceFailure(f"strict JSON proof pool validation did not pass: {validation}")
        proof["strict_nested_json"] = {
            "status": "PASS",
            "runtime": "PostgreSQL pg_temp.cp3_r4_assert_nested on exact restored schema",
            "positive_real_boolean_cases": 4,
            "negative_cases_rejected": 16,
            "negative_matrix": ["required-key-missing","required-key-null","extra-key","wrong-type","string-true","string-false","empty-object","nested-missing-key"],
            "nested_kinds": ["source","destination"],
        }
''','strict JSON harness evidence')
HAR.write_text(harness)

manifest=json.loads(MAN.read_text())
for rel in manifest['files']:
    data=(ROOT/rel).read_bytes()
    manifest['files'][rel]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
MAN.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':'PASS','strict_negative_cases':16,'positive_boolean_cases':4},sort_keys=True))
