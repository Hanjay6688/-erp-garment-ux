"""Verify the successor on the same Global as its parent, including Astra's unchanged 16 scenarios."""
import hashlib
import importlib.util
import json
import os
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
import subprocess
from threading import Thread

import psycopg
import cp7_r3_reminders_cases as rem
import install as upgrade

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ['GITHUB_WORKSPACE'])
OUT = Path(os.environ['WRITER_RESULTS'])
RELEASE = json.loads((HERE / 'candidate.json').read_text())
OLD = HERE.parent / 'cp75-reminders'
spec = importlib.util.spec_from_file_location('parent_fixture', OLD / 'check.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
SQL = 'scripts/cp7-src/manual-reminders/facade.sql'


def versioned_install():
    assert fixture.RELEASE['product'] == RELEASE['parent'] and fixture.RELEASE['tree'] == RELEASE['parent_tree']
    fixture.install()
    (OUT / 'installation.json').rename(OUT / 'parent-installation.json')
    for p in ['install.py', 'workspace.patch']:
        assert fixture.git_blob(HERE / p) == RELEASE['files']['scripts/cp7_global_reminder_order/' + p]['after']
    for files, directory, patch in [([p for p in RELEASE['files'] if p.startswith('src/')], fixture.APP, 'ui.patch'),
                                    ([SQL], ROOT / 'fixtures', 'factory.patch')]:
        for side in ['before', 'after']:
            if side == 'after':
                subprocess.run(['git', 'apply', '--no-index', str(HERE / patch)], cwd=directory, check=True)
            assert all(fixture.git_blob(directory / p) == RELEASE['files'][p][side] for p in files)
    before = fixture.seal()
    assert before['sha256'] == RELEASE['parent_catalogue'] and before['groups'] == 25
    steps = []
    for direction, changed in [('up', True), ('up', False), ('down', True), ('down', False), ('up', True)]:
        with psycopg.connect(**fixture.DB) as conn:
            result = upgrade.apply(conn, direction)
        assert result['changed'] is changed
        fingerprint = fixture.seal()
        assert fingerprint['counts'] == before['counts'] and fingerprint['groups'] == 25
        if direction == 'down':
            assert fingerprint == before
        elif steps:
            assert fingerprint['sha256'] == steps[0]['catalogue']
        else:
            assert fingerprint['sha256'] != before['sha256']
        steps.append({**result, 'catalogue': fingerprint['sha256']})
        fixture.store('installation', dict(release=RELEASE, parent=before['sha256'], steps=steps))
    source = (ROOT / 'fixtures' / SQL).read_text().split('create function cp7_reminders.workspace(', 1)[1].split('as $$', 1)[1].split('$$;', 1)[0]
    with psycopg.connect(**fixture.DB) as conn:
        actual = conn.execute("select prosrc from pg_proc where oid='cp7_reminders.workspace(jsonb)'::regprocedure").fetchone()[0]
    assert source == actual and upgrade.sha(actual) == upgrade.AFTER
    fixture.store('installation', dict(release=RELEASE, parent=before['sha256'], steps=steps, factory_equals_upgrade=True))


def sql_controls():
    query = dict(filter='OPEN', limit=25, offset=0, include_order=True)
    with psycopg.connect(**fixture.DB) as c, c.cursor() as q:
        actor, other = rem.owner(q), rem.owner(q)
        empty = rem.get(q, other, query)['order_token']
        assert empty == hashlib.sha256(b'').hexdigest()
        start = datetime(2038, 3, 1, tzinfo=timezone.utc)
        for i in range(201):
            rem.save(q, actor, 'SAVE', rem.body((start + timedelta(minutes=i)).isoformat(), title='Control ' + str(i)))
        original_order = rem.order_of(q, actor, 'OPEN')
        assert len(original_order) == 201

        def token_ids(order):
            expected = hashlib.sha256(','.join(order[:200]).encode()).hexdigest()
            for offset in [0, 25, 100, 175]:
                page = rem.get(q, actor, {**query, 'offset': offset})
                assert page['order_token'] == expected and page['page']['beyond_window'] == 1
                assert [r['id'] for r in page['items']] == order[offset:offset+25]
            return expected

        def update(index, due, note):
            row = rem.row(q, original_order[index])
            rem.save(q, actor, 'SAVE', rem.body(due, title=row['title'], note=note, rid=row['id']), expected=row['row_version'])

        first = token_ids(original_order)
        update(0, start.isoformat(), 'Only the note changed')
        update(200, '2040-01-01T00:00:00Z', 'Still outside the window')
        assert first == token_ids(rem.order_of(q, actor, 'OPEN'))
        update(0, '2042-01-01T00:00:00Z', 'Moved to last')
        update(200, '2020-01-01T00:00:00Z', 'Moved to first')
        after = rem.order_of(q, actor, 'OPEN')
        assert after == [original_order[-1], *original_order[1:-1], original_order[0]]
        second = token_ids(after)
        assert second != first and rem.get(q, other, query)['order_token'] == empty
        for legacy in [dict(filter='OPEN'), dict(filter='OPEN', include_order=False)]:
            response = rem.get(q, actor, legacy)
            assert 'order_token' not in response and response['items'][0]['id'] == after[0]
        bad = rem.refused(q, lambda: rem.get(q, actor, {**query, 'include_order': 'true'}), 'CP7_REMINDERS_QUERY')
        denied = rem.refused(q, lambda: rem.as_actor(q, dict(role='authenticated'), "select public.erp_cp7_get_reminders_v1('{ \"include_order\": true }'::jsonb)"), 'CP7_REMINDERS_DENIED')
        fixture.store('sql-controls', dict(window=200, actual=201, offsets=[0,25,100,175], original=first, swapped=second,
                      note_and_outside_window_stable=True, other_actor_stable=True, legacy_shapes=2, invalid_option=bad, denied=denied))
        c.rollback()


def chromium():
    subprocess.run(['npm', 'ci', '--no-audit', '--no-fund'], cwd=fixture.APP, check=True)
    out_file = '--outputFile=' + str(OUT / 'vitest.json')
    subprocess.run(['node',str(fixture.APP / 'node_modules/vitest/vitest.mjs'),'run','src/ConnectedRemindersPage.dom.test.tsx',
                    'src/ConnectedRemindersWa.dom.test.tsx','src/cp6BusinessTime.test.ts','--reporter=json',out_file], cwd=fixture.APP, check=True)
    original = ROOT / 'oracle/qualification/astra-public/global-final/verify_reminder_browser.json'
    prefix = (OLD / 'browser.cjs').read_text().split('  const browser=await chromium.launch', 1)[0]
    with ThreadingHTTPServer(('127.0.0.1', 0), fixture.Adapter) as http:
        thread = Thread(target=http.serve_forever, daemon=True)
        thread.start()
        try:
            for name, body in [('astra',json.loads(original.read_text())), ('writer',(HERE / 'ids.cjs').read_text())]:
                driver = OUT / (name + '.cjs')
                driver.write_text(prefix + body)
                subprocess.run(['node',str(driver),str(fixture.APP),str(OUT),'http://127.0.0.1:'+str(http.server_port)], check=True)
                data = json.loads((OUT / 'browser.json').read_text())
                if name == 'astra':
                    (OUT / 'browser.json').rename(OUT / 'astra-cases.json')
                    assert len(data) == len({v['id'] for v in data}) == 16 and all(v['outcome']=='PASS' for v in data), [(v['id'], v.get('error')) for v in data if v['outcome']!='PASS']
        finally:
            http.shutdown()
            thread.join()


if __name__ == '__main__':
    versioned_install()
    sql_controls()
    chromium()
