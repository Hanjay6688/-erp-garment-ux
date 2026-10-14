#!/usr/bin/env python3
"""FABLE-002: the two copies of AC..AV are not two truths. Read-only check, no database.

supabase/migrations/*_20ac..20av_* are the original files as they were written; they are never edited (a changed
migration would no longer match the ledger of installs made from it). supabase/release/cp6-t3/* is the package a new
install uses: the same files with the reviewed guard pins re-taken on the hosted-faithful chain (owner decision G-01
option (b), cp6_t3_release_package.py). AW..BF exist only in the package (their sources are in
supabase/release/cp6-t3-src).

This check rebuilds every package file in memory from its source and the committed pins, with the builder's own
derivation, and requires:
  * every source still has the sha256 the manifest recorded (no drift in the original files);
  * every rebuilt file is byte-identical to the committed package file and to the manifest's package_sha256;
  * the only differences between a source and its package file are the substitutions the manifest lists (each kind
    is one the builder reviews: AC_VIEW, LEDGER, CATALOG, CAPSULE), and every changed line is a guard pin line.
Nothing is written. Exit 1 on any mismatch.
"""
from pathlib import Path
import difflib, json, sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cp6_t3_release_package as r  # noqa: E402



def check():
    manifest = json.loads((r.RELEASE / 'MANIFEST.json').read_text())
    pins = json.loads((r.ROOT / manifest['pins']['file']).read_text())
    blob = json.dumps(pins, separators=(',', ':'))
    assert r.sha(blob) == manifest['pins']['blob_sha256'], ('PINS_BLOB_SHA256', r.sha(blob))
    rows = {x['key']: x for x in r.package()}
    assert [f['key'] for f in pins['files']] == list(rows) == [f['key'] for f in manifest['files']], 'PACKAGE_KEYS'
    report, renamed = [], []
    for f, m in zip(pins['files'], manifest['files']):
        row = rows[f['key']]
        text = (r.ROOT / row['path']).read_text()
        assert row['path'] == m['source'] and r.sha(text) == m['source_sha256'] == f['source_sha256'], ('SOURCE_DRIFT', f['key'])
        assert [s for s in f['subs'] if s['kind'] == 'LEDGER'] == r.ledger_subs(text, renamed), ('LEDGER_CASCADE', f['key'])
        if f['key'] == 'AC':
            assert [s for s in f['subs'] if s['kind'] == 'AC_VIEW'] == r.ac_view_subs(text), 'AC_VIEW'
        final = r.check_subs(row, text, f['subs'])
        committed = (r.ROOT / m['file']).read_text()
        assert final == committed and r.sha(committed) == m['package_sha256'], ('PACKAGE_NOT_REPRODUCED', f['key'])
        kinds = sorted({s['kind'] for s in f['subs']})
        assert set(kinds) <= {'AC_VIEW', 'LEDGER', 'CATALOG', 'CAPSULE'}, ('UNREVIEWED_KIND', f['key'], kinds)
        assert [dict(kind=s['kind'], what=s['what'], count=s['count']) for s in f['subs']] == m['substitutions'], ('MANIFEST_SUBS', f['key'])
        changed = [line for line in difflib.unified_diff(text.splitlines(), final.splitlines(), lineterm='', n=0)
                   if line[:1] in '+-' and not line.startswith(('+++', '---'))]
        if final != text:
            renamed.append(dict(key=f['key'], old=f['source_sha256'], new=f['package_sha256']))
        report.append(dict(key=f['key'], source=row['path'], package=m['file'], identical=final == text,
                           changed_lines=len(changed), substitution_kinds=kinds))
    return dict(check='CP7_RELEASE_COPY_CHECK', files=len(report), only_in_package=[x['key'] for x in report if 'release/cp6-t3-src' in x['source']],
                differing_copies=[x['key'] for x in report if not x['identical'] and 'supabase/migrations' in x['source']],
                status='PASS', rows=report)


if __name__ == '__main__':
    try:
        out = check()
    except AssertionError as exc:
        print(json.dumps(dict(check='CP7_RELEASE_COPY_CHECK', status='FAIL', error=repr(exc.args)), indent=1))
        raise SystemExit(1)
    print(json.dumps({k: v for k, v in out.items() if k != 'rows'}, indent=1))
    for row in out['rows']:
        print(row['key'], 'identical' if row['identical'] else 'pins re-taken (%s): %d changed lines' % (','.join(row['substitution_kinds']), row['changed_lines']))
