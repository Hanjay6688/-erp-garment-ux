"""Source-bound AN/AO/AP catalogs, functions, capsules and platform ledgers."""
from pathlib import Path
import json
from cp6_ao_ap_inventory import inventory,function_pins,history_capsules,sha
from cp6_ao_ap_build import capsule_guard
import cp6_v2620an_build_sql as an

ROOT=Path(__file__).resolve().parents[1]
PINS=ROOT/'docs/evidence/cp6-ao-ap-package-pins.json'
CATALOG=ROOT/'docs/evidence/cp6-ao-ap-catalog.json'
EXPECTED_PINS_SHA256='542c2a3e6909d930a52a184afdede38d3ff3948d46f772dd5c71345297d944dd'

def pins():
    assert sha(PINS.read_bytes())==EXPECTED_PINS_SHA256,'PACKAGE_SOURCE_PINS_DRIFT'
    p=json.loads(PINS.read_text())
    assert sha(CATALOG.read_bytes())==p['capture_sha256'],'PACKAGE_CATALOG_SOURCE_DRIFT'
    for path,key in [('scripts/cp6_ao_ap_inventory.py','inventory_sha256'),('scripts/cp6_ao_ap_build.py','builder_sha256')]:
        assert sha((ROOT/path).read_bytes())==p[key],path
    for f in p['families'].values():
        for key in ('migration','rollback'):
            assert sha((ROOT/f[key]).read_bytes())==f[key+'_sha256'],'PACKAGE_SQL_SOURCE_DRIFT:'+f[key]
    return p

def verified(cur,stage,pre_admission=False):
    p=pins();capture=json.loads(CATALOG.read_text());expected=capture['stages'][stage]
    cur.execute("set local search_path='';set local timezone='UTC'")
    actual=function_pins(cur)
    assert actual==expected['functions'], 'PACKAGE_FUNCTION_OWNER_ACL_DRIFT:'+str(next((k for k in sorted(set(actual)|set(expected['functions'])) if actual.get(k)!=expected['functions'].get(k)),None))
    assert history_capsules(cur)==capture['history_capsules'],'PACKAGE_HISTORICAL_CAPSULE_DRIFT'
    families=[] if stage=='AN' else ['AO'] if stage=='AO' else ['AO','AP']
    for f in ('AO','AP'):
        pin=p['families'][f]
        if f in families:
            cur.execute(capsule_guard(f,pin),prepare=False)
            assert cur.execute('select count(*) from erp.schema_migrations where version=%s',(pin['version'],)).fetchone()==(1,),'PACKAGE_MARKER_DRIFT:'+f
            assert cur.execute('select version,name,statements from supabase_migrations.schema_migrations where version=%s or name=%s',(pin['stamp'],pin['name'])).fetchall()==[(pin['stamp'],pin['name'],[(ROOT/pin['migration']).read_text()])],'PACKAGE_PLATFORM_SOURCE_DRIFT:'+f
        else:
            assert cur.execute('select to_regclass(%s)',(pin['capsule'],)).fetchone()==(None,),'PACKAGE_SUCCESSOR_CAPSULE:'+f
            assert not cur.execute('select 1 from erp.schema_migrations where version=%s',(pin['version'],)).fetchone(),'PACKAGE_SUCCESSOR_MARKER:'+f
    assert cur.execute('select version,name,statements from supabase_migrations.schema_migrations where version=%s or name=%s',(an.STAMP,an.NAME)).fetchall()==[(an.STAMP,an.NAME,[(ROOT/an.MIGRATION).read_text()])],'PACKAGE_AN_PLATFORM_DRIFT'
    stamp=an.STAMP if stage=='AN' else p['families'][stage]['stamp']
    assert not cur.execute('select 1 from supabase_migrations.schema_migrations where version>%s',(stamp,)).fetchone(),'PACKAGE_SUCCESSOR_PLATFORM_RESIDUE'
    if not pre_admission:
        objects=inventory(cur)
        assert objects==expected['objects'],'PACKAGE_CATALOG_DRIFT:'+str(next((k for k in sorted(set(objects)|set(expected['objects'])) if objects.get(k)!=expected['objects'].get(k)),None))
    return dict(stage=stage,function_count=len(actual),object_count=len(expected['objects']),full_catalog_verified=not pre_admission)

def sql_body(source):
    """Only unwrap the reviewed top-level transaction; never alter SQL guards."""
    lines=source.splitlines(keepends=True)
    assert lines[0].startswith('-- CP6 ') and lines[1]=='begin;\n' and lines[-1]=='commit;\n'
    return ''.join(lines[2:-1])
