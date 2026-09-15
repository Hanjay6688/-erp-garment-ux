#!/usr/bin/env python3
"""Exact AD source/capsule verification; AC's 272 runtime objects stay intact."""
from pathlib import Path
import hashlib,json,os,subprocess
import cp6_v2620ac_runtime as ac

STAMP='20260915113627'
NAME='erp_v2_6_20ad_cp6_opening_material_business_day'
VERSION='v2.6.20ad'
MIGRATION=Path(f'supabase/migrations/{STAMP}_{NAME}.sql')
ROLLBACK=Path(f'supabase/rollbacks/{STAMP}_{NAME}.rollback.sql')
PINS=Path('docs/evidence/cp6-ad-runtime-pins.json')
CAPSULE='erp.cp6_v2620ad_rollback_capsule'
AC_HEAD='1bdca3766f7c9800d68295ff5122798060b8a05d'
AC_TREE='334629c626257b8b713826f491cdf62385d5299b'
PINS_SHA256='077e0dfde7c56ce9b37add1c18683ce8cf6ae8a3433adf29e8c2320cd8a6bd18'

def pins():
    data=PINS.read_bytes()
    if hashlib.sha256(data).hexdigest()!=PINS_SHA256:raise AssertionError('AD_TRUSTED_PINS_CHANGED')
    return json.loads(data)

def verify_source_files():
    payload=pins();ac.verify_source_files()
    for path,pin in payload['source_pins'].items():
        b=Path(path).read_bytes()
        if len(b)!=pin['bytes'] or hashlib.sha256(b).hexdigest()!=pin['sha256']:
            raise AssertionError('AD_SOURCE_BYTES_MISMATCH:'+path)
    if len(payload['functions'])!=2 or set(f['identity'] for f in payload['functions']) & set(f['identity'] for f in ac.pins()['functions']):
        raise AssertionError('AD_REQUIRES_TWO_FUNCTIONS_OUTSIDE_AC_CAPSULE')
    return payload

def verify_audit_source():
    verify_source_files()
    git=lambda *a:subprocess.check_output(['git',*a],text=True).strip()
    if git('rev-parse',AC_HEAD+'^{tree}')!=AC_TREE or git('merge-base',AC_HEAD,'HEAD')!=AC_HEAD:
        raise AssertionError('AD_REQUIRES_FROZEN_AC_ANCESTRY')
    if git('rev-list','--merges',AC_HEAD+'..HEAD'):raise AssertionError('AD_LINEAR_SUCCESSOR_REQUIRED')
    changed=set(git('diff','--name-only',AC_HEAD,'HEAD','--','supabase/migrations','supabase/rollbacks').splitlines())
    if changed!={str(MIGRATION),str(ROLLBACK)}:raise AssertionError('AD_ONLY_NEW_AD_SQL_EDGE_ALLOWED')
    if git('diff','--name-only','--diff-filter=MDRTCUXB',AC_HEAD,'HEAD','--','supabase/migrations','supabase/rollbacks'):
        raise AssertionError('AD_ADMITTED_SQL_CHANGED')
    head=git('rev-parse','HEAD')
    if os.environ.get('GITHUB_SHA')!=head:raise AssertionError('AD_EXACT_NATIVE_HEAD_REQUIRED')
    return head,git('rev-parse','HEAD^{tree}')

def verify_ac_pre_admission(cur):
    verify_source_files()
    objects=ac.verified_pre_admission_successor(cur)
    if len(objects)!=115:raise AssertionError('AD_REQUIRES_AC_FUNCTION_CAPSULE')
    return objects

def verify_predecessor(cur):
    payload=verify_source_files()
    if len(ac.verified_successor(cur))!=272:raise AssertionError('AD_REQUIRES_EXACT_AC')
    if cur.execute("select to_regclass(%s) is not null or exists(select 1 from erp.schema_migrations where version=%s) or exists(select 1 from supabase_migrations.schema_migrations where name=%s)",(CAPSULE,VERSION,NAME)).fetchone()[0]:
        raise AssertionError('AD_PREDECESSOR_HAS_SUCCESSOR_RESIDUE')
    for f in payload['functions']:
        row=cur.execute("""select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
          pg_get_userbyid(p.proowner),array(select a::text from unnest(p.proacl) a order by a::text)
          from pg_proc p where p.oid=to_regprocedure(%s)""",(f['identity'],)).fetchone()
        if row!=(f['predecessor_sha256'],f['owner'],f['acl']):raise AssertionError('AD_PREDECESSOR_FUNCTION_DRIFT:'+f['identity'])
    return payload

def verified_successor(cur):
    payload=verify_source_files()
    cur.execute("""select exists(select 1 from erp.schema_migrations where version=%s),to_regclass(%s) is not null,
      (select count(*) from supabase_migrations.schema_migrations where name=%s)""",(VERSION,CAPSULE,NAME))
    if cur.fetchone()!=(True,True,1):raise AssertionError('AD_MARKER_CAPSULE_PLATFORM_MISMATCH')
    row=cur.execute("""select version,encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')
      from supabase_migrations.schema_migrations where name=%s""",(NAME,)).fetchone()
    if row!=(STAMP,payload['source_pins'][str(MIGRATION)]['sha256']):raise AssertionError('AD_PLATFORM_SOURCE_MISMATCH')
    ac._capsule_security(cur,CAPSULE)
    from cp6_preuse_rollback_maintenance import _capsule_snapshot,TARGETS
    own=_capsule_snapshot(cur.connection,'AD',TARGETS['AD'])
    inherited=ac.verified_successor(cur)
    if len(own)!=2 or len(inherited)!=272:raise AssertionError('AD_RUNTIME_CARDINALITY')
    boundaries=cur.execute(f'select boundary_snapshot from {CAPSULE}').fetchall()
    if len(boundaries)!=2 or any(len(row[0])!=216 for row in boundaries) or boundaries[0]!=boundaries[1]:
        raise AssertionError('AD_BOUNDARY_CAPSULE_MISMATCH')
    result=dict(inherited)
    result.update({f['identity']:{**f,'kind':'FUNCTION'} for f in own})
    return result
