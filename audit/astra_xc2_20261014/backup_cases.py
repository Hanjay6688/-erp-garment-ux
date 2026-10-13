"""Astra's backup contract cases. All databases are synthetic and disposable.

The five legacy oracles are preserved. Only their owned-leftover fixture is
updated to the required token/OID API, with the exact one-line diff archived.
New barriers run after real dump/hash operations, never replace verdicts.
"""
from pathlib import Path
from urllib.parse import urlparse
import json, os, uuid
import psycopg
from psycopg import sql
import cp7_nightly_backup as backup
import cp6_auditor_runner as native
import legacy_cases_current_fixture as legacy


def races(tools, today):
    assert urlparse(tools.admin).hostname in ('127.0.0.1', 'localhost', '::1')

    def legacy_checked(case_id, case):
        result = case()
        expected = [(1, 'SOURCE_ORIGINAL')]
        if case_id.endswith('LIVE_WRITE'):
            expected.append((2, 'AFTER_EXPORTED_SNAPSHOT'))
        assert result['source_rows'] == expected, result
        result['additional_source_integrity_assertion'] = True
        return result

    cases = [(case_id, lambda case_id=case_id, case=case: legacy_checked(case_id, case))
             for case_id, case in legacy.races(tools, today)[:5]]

    def scenario(kind):
        tag = uuid.uuid4().hex[:10]
        source, scratch, moved = ['ax2_' + part + '_' + tag for part in ('src', 'scr', 'moved')]
        patterned = scratch + '_' + 'a' * 16
        admin = backup.db_url(tools.admin, 'postgres')
        names = set()
        observed = {}
        dest = Path(native.r1.AUDITOR) / 'cp6-proof/t3' / ('AX2_BACKUP_' + kind)
        dest.mkdir(parents=True, exist_ok=True)
        # A dated verified canary proves refusal cannot prune an older backup.
        oldfile = dest / 'old-verified.dump'
        oldfile.write_bytes(b'ASTRA_SYNTHETIC_RETENTION_CANARY')
        (dest / 'old-verified.dump.receipt.json').write_text(json.dumps(dict(
            contract=backup.CONTRACT, file=oldfile.name, restore_verified=True,
            started_at_utc='2020-01-01T00:00:00+00:00')))

        def pg():
            return psycopg.connect(admin, autocommit=True)

        def create(name, text):
            with pg() as conn:
                conn.execute(sql.SQL('create database {} template template0').format(sql.Identifier(name)))
            names.add(name)
            with psycopg.connect(backup.db_url(admin, name)) as conn:
                conn.execute('create table public.astra_xc2_canary(v text not null)')
                conn.execute('insert into public.astra_xc2_canary values(%s)', (text,))
                conn.commit()

        def comment(name, value):
            with pg() as conn:
                conn.execute(sql.SQL('comment on database {} is {}').format(sql.Identifier(name), sql.Literal(value)))

        def state(name):
            identity = backup.identity(admin, name)
            if identity is None:
                return None
            with psycopg.connect(backup.db_url(admin, name)) as conn:
                rows = conn.execute('select v from public.astra_xc2_canary order by v').fetchall()
            return dict(oid=identity[0], comment=identity[1], rows=rows)

        real_hashes, real_mark = backup.data_hashes, backup.mark_scratch
        try:
            create(source, 'SOURCE_UNCHANGED')
            source_before = state(source)
            if kind in ('PLAIN_CONFIG', 'PLAIN_PATTERN'):
                foreign = scratch if kind == 'PLAIN_CONFIG' else patterned
                create(foreign, 'FOREIGN_MUST_SURVIVE')
                comment(foreign, backup.SCRATCH_MARK)
                observed['foreign_before'] = state(foreign)

            if kind in ('FINALLY_REPLACED_AFTER_HASH', 'FINALLY_MARK_REPLACED'):
                def hashes_then_admin_action(url, expected_oid=None):
                    result = real_hashes(url, expected_oid)
                    if expected_oid is not None:
                        name = urlparse(url).path.lstrip('/')
                        names.add(name)
                        observed['barrier'] = dict(point='AFTER_REAL_HASH_BEFORE_FINAL_DROP', oid=expected_oid, name=name)
                        if kind == 'FINALLY_REPLACED_AFTER_HASH':
                            with pg() as conn:
                                conn.execute(sql.SQL('alter database {} rename to {}').format(sql.Identifier(name), sql.Identifier(moved)))
                            names.add(moved)
                            create(name, 'FOREIGN_AFTER_HASH')
                        else:
                            comment(name, backup.SCRATCH_MARK)
                        observed['protected_before_finally'] = state(name)
                    return result
                backup.data_hashes = hashes_then_admin_action

            if kind == 'FINALLY_BEFORE_MARK_THROW':
                def mark_throws(admin_url, name, token, oid):
                    names.add(name)
                    observed['barrier'] = dict(point='CREATED_BEFORE_MARK', oid=oid, name=name)
                    assert backup.identity(admin_url, name) == (oid, None)
                    raise RuntimeError('ASTRA_INJECTED_PRE_MARK_FAILURE')
                backup.mark_scratch = mark_throws

            result = backup.backup(admin, source, scratch, dest, keep=1,
                                   container=os.environ['CP6_DATABASE_CONTAINER'])
            observed['receipt'] = result
            assert state(source) == source_before, (source_before, state(source))
            observed['source_unchanged'] = True
            if kind in ('PLAIN_CONFIG', 'PLAIN_PATTERN'):
                assert state(foreign) == observed['foreign_before']
                observed['foreign_after'] = state(foreign)
                if kind == 'PLAIN_CONFIG':
                    assert result['restore_verified'] is False and 'BACKUP_SCRATCH_EXISTS_NOT_OURS' in result.get('error', '')
                    assert result['scratch_before'] == 'FOREIGN' and result['scratch_attempt']['drop']['result'] == 'NOT_CREATED'
                else:
                    assert result['restore_verified'] is True and result['leftovers'] == []
                    assert result['scratch_attempt']['drop']['result'] == 'DROPPED'
            elif kind == 'FINALLY_REPLACED_AFTER_HASH':
                name = observed['barrier']['name']
                assert state(name) == observed['protected_before_finally']
                assert result['restore_verified'] is True and backup.identity(admin, moved) is None
                assert result['scratch_attempt']['drop']['name'] == moved and result['scratch_attempt']['drop']['result'] == 'DROPPED'
            elif kind == 'FINALLY_MARK_REPLACED':
                name = observed['barrier']['name']
                assert state(name) == observed['protected_before_finally']
                assert result['restore_verified'] is False and result['scratch_attempt']['drop']['result'] == 'NOT_OURS'
                assert 'BACKUP_SCRATCH_REPLACED' in result.get('error', '')
            elif kind == 'FINALLY_BEFORE_MARK_THROW':
                assert result['restore_verified'] is False and 'ASTRA_INJECTED_PRE_MARK_FAILURE' in result.get('error', '')
                assert result['scratch_attempt']['drop']['result'] == 'DROPPED'
                assert backup.identity(admin, observed['barrier']['name']) is None
            if not result['restore_verified']:
                assert result['retention']['removed'] == [] and oldfile.read_bytes() == b'ASTRA_SYNTHETIC_RETENTION_CANARY'
                observed['old_verified_backup_preserved'] = True
            observed['status'] = 'PASS'
            return observed
        finally:
            backup.data_hashes, backup.mark_scratch = real_hashes, real_mark
            # Cleanup belongs to the auditor, after every survival assertion.
            with pg() as conn:
                names.update(r[0] for r in conn.execute('select datname from pg_database where datname like %s', (scratch + '%',)))
                for name in sorted(names):
                    assert name.startswith('ax2_')
                    conn.execute(sql.SQL('drop database if exists {} with(force)').format(sql.Identifier(name)))

    def grammar():
        oid, token = 2000000001, '0123456789abcdef'
        good = backup.SCRATCH_MARK + ' attempt=' + token + ' oid=' + str(oid)
        observations = [backup.is_mark(c, oid) for c in [None, '', backup.SCRATCH_MARK, good + ' suffix', good.replace(token, 'x' * 16), good.replace(str(oid), '2000000002')]]
        assert observations == [False] * 6
        assert backup.is_mark(good, oid) and backup.is_mark(good, oid, token)
        assert not backup.is_mark(good, oid, 'f' * 16)
        return dict(status='PASS', invalid_marks_rejected=6, exact_oid_and_token_required=True)

    cases += [('AX2-M01-MARK-GRAMMAR', grammar)]
    cases += [('AX2-B%02d-%s' % (i + 6, kind), lambda kind=kind: scenario(kind)) for i, kind in enumerate([
        'PLAIN_CONFIG', 'PLAIN_PATTERN', 'FINALLY_REPLACED_AFTER_HASH', 'FINALLY_MARK_REPLACED', 'FINALLY_BEFORE_MARK_THROW'])]
    return cases
