"""T3 browser precondition: the clone runs the committed combined release package plus the AW/AX T1 files.

The AU browser fixture checks `cp6_au_runtime.verified`, which pins the AU catalog; AV..AX change that catalog on
purpose, so on the combined candidate the fixture checks this instead (set CP6_T3_BROWSER=1): every package file is in
the platform ledger with exactly the statements of supabase/release/cp6-t3 (sha256 from MANIFEST.json), nothing else
was applied after AB, AW/AX T1 verify (function texts and the AV coverage registry), and the whole erp/public catalog
equals the installed pin of the last package file. The browser cases and their oracles are unchanged. Label: T3_PREP.
"""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'supabase/release/cp6-t3/MANIFEST.json'
AB_STAMP='20260914190500'


def verified(cur):
    manifest=json.loads(MANIFEST.read_text())
    expected={f['stamp']:f['package_sha256'] for f in manifest['files']}
    live=dict(cur.execute("""select version,encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')
        from supabase_migrations.schema_migrations where version>%s""",(AB_STAMP,)).fetchall())
    assert live==expected,('T3_BROWSER_PACKAGE_LEDGER_DRIFT',sorted(set(live)^set(expected)),
                           sorted(k for k in expected if live.get(k)!=expected[k]))
    import cp6_az_probe as azp
    ax=azp.az_verified(cur)
    # The whole erp/public catalog (definitions, owners, ACLs) equals the installed pin of the last package file (AZ),
    # read on a separate read-only connection so the caller's session settings are untouched.
    import psycopg
    import cp6_t3_release_package as package
    last=manifest['files'][-1]
    block=package.catalog_blocks((ROOT/last['file']).read_text())[1]
    with psycopg.connect(package.CLONE) as conn,conn.cursor() as check:
        conn.read_only=True
        live=package.live_catalog(check,block);conn.rollback()
    assert live==(block['count'],block['fingerprint']),('T3_BROWSER_CATALOG_DRIFT',last['key'],live)
    return dict(stage='T3_PACKAGE_PLUS_AW_AX_AY_AZ_T1',package_files=len(expected),aw_ax_ay_az=ax['stage'],ax_sql_sha256=ax['ax_sql_sha256'],
                ay_sql_sha256=ax['ay_sql_sha256'],az_sql_sha256=ax['az_sql_sha256'],
                catalog=dict(file=last['key'],object_count=live[0],fingerprint=live[1]))
