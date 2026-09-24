"""T3 browser precondition: the clone runs the committed combined release package plus the AW/AX T1 files.

The AU browser fixture checks `cp6_au_runtime.verified`, which pins the AU catalog; AV..AX change that catalog on
purpose, so on the combined candidate the fixture checks this instead (set CP6_T3_BROWSER=1): every package file is in
the platform ledger with exactly the statements of supabase/release/cp6-t3 (sha256 from MANIFEST.json), nothing else
was applied after AB, and AW/AX T1 verify (function texts and the AV coverage registry). The browser cases and their
oracles are unchanged. Label: T3_PREP.
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
    import cp6_ax_probe as axp
    ax=axp.ax_verified(cur)
    return dict(stage='T3_PACKAGE_PLUS_AW_AX_T1',package_files=len(expected),aw_ax=ax['stage'],ax_sql_sha256=ax['ax_sql_sha256'])
