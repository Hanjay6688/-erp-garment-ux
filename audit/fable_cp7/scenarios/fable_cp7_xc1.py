"""Fable cross-check round 1 (candidate ae0214ad, tool scripts/cp7_nightly_backup.py after Astra ASR-OPS-01 fix 85e17168).
Own oracles. Invariant under test: the nightly backup never drops, and never leaves unverified-as-verified, a database it
did not create in THIS attempt; a database that takes a name the tool is using must survive, and the night must then be
recorded unverified. Administrator DDL is injected after the tool's real steps (monkeypatched Tools methods), as Astra
and the writer did, but with Fable's own expectations and its own foreign-database canaries.
Native (savepoint group):
  XC1:NO_NAME_BASED_DROP_OR_CREATE_IN_TOOL   source-level oracle at runtime: Tools.drop/Tools.create gone; drop_owned/create_attempt/leftovers present.
Races (fresh copy each):
  XC1:LEFTOVER_REPLACED_AFTER_DUMP_KEPT      Astra's sequence (marked leftover under --scratch, replaced by a foreign database after pg_dump).
  XC1:ATTEMPT_SWAPPED_BEFORE_RESTORE_KEPT    writer's stated operating boundary: the attempt's random-named database swapped for a foreign one before pg_restore.
  XC1:COPIED_OID_MARK_ON_FOREIGN_KEPT        foreign <scratch>_<hex> databases: unmarked, and marked with a copied mark naming another OID.
  XC1:PLAIN_MARK_COPIED_ONTO_FOREIGN         foreign database under --scratch carrying a copy of the tool's PLAIN (legacy, OID-less) mark.
"""
import hashlib,inspect,os,re,secrets,tempfile,uuid
from pathlib import Path
import psycopg
from psycopg import sql
import cp7_nightly_backup as nightly
import cp7_p19_staged_cases as staged
b=staged.b

def cases(cur,today):
    def no_name_based_paths():
        src=Path(inspect.getsourcefile(nightly)).read_bytes();text=src.decode()
        has=lambda n:hasattr(nightly,n)
        tool_cls=nightly.Tools
        gone=not hasattr(tool_cls,'drop') and not hasattr(tool_cls,'create')
        present=all(has(n) for n in ('drop_owned','create_attempt','leftovers','is_mark','identity'))
        dropdb_calls=len(re.findall(r"'dropdb'",text));drop_by_name=len(re.findall(r'drop database \{\}',text))
        ok=gone and present and dropdb_calls==0
        return dict(status='PASS' if ok else 'FAIL',sha256=hashlib.sha256(src).hexdigest(),tools_drop_create_removed=gone,oid_functions_present=present,
                    dropdb_string_occurrences=dropdb_calls,drop_database_identifier_sites=drop_by_name,note='drop sites must be inside drop_owned only (checked by reading the file in the report)')
    return [('XC1:NO_NAME_BASED_DROP_OR_CREATE_IN_TOOL',no_name_based_paths)]

def races(tools,today):
    container=os.environ.get('CP6_DATABASE_CONTAINER','supabase_db_cp5-local')
    def pg():return psycopg.connect(nightly.db_url(tools.admin,'postgres'),autocommit=True)
    def mk(name,row,comment=None):
        with pg() as c:
            c.execute(sql.SQL('create database {} template template0').format(sql.Identifier(name)))
            if comment is not None:c.execute(sql.SQL('comment on database {} is {}').format(sql.Identifier(name),sql.Literal(comment)))
        with psycopg.connect(nightly.db_url(tools.admin,name),autocommit=True) as c:
            c.execute('create table fable_canary(v text not null)');c.execute('insert into fable_canary values(%s)',(row,))
    def state(name):
        with pg() as c:
            r=c.execute("select oid,shobj_description(oid,'pg_database') from pg_database where datname=%s",(name,)).fetchone()
        if r is None:return None
        with psycopg.connect(nightly.db_url(tools.admin,name)) as c:
            rows=c.execute('select v from fable_canary').fetchall() if c.execute("select 1 from pg_tables where tablename='fable_canary'").fetchone() else []
            foreign_tables=c.execute("select count(*) from pg_tables where schemaname not in('pg_catalog','information_schema') and tablename<>'fable_canary'").fetchone()[0]
        return dict(oid=r[0],comment=r[1],canary=[x[0] for x in rows],other_tables=foreign_tables)
    def drop(name):
        with pg() as c:c.execute(sql.SQL('drop database if exists {} with (force)').format(sql.Identifier(name)))
    def attempts(scratch):
        with pg() as c:return [r[0] for r in c.execute('select datname from pg_database where datname ~ %s',('^'+re.escape(scratch)+'_[0-9a-f]{16}$',)).fetchall()]
    def role():
        with pg() as c:
            r=c.execute("select current_user,rolsuper,rolcreatedb,version() from pg_roles where rolname=current_user").fetchone()
        return dict(user=r[0],superuser=r[1],createdb=r[2],server=r[3][:40])
    def night(source,scratch):
        with tempfile.TemporaryDirectory(prefix='fable-xc1-') as dest:
            return nightly.backup(tools.admin,source,scratch,dest,keep=14,container=container)
    def source_db():
        return os.path.basename(tools.admin.rsplit('/',1)[-1].split('?')[0])
    def fresh(tag):
        s=os.environ.get('PGURL','');src=source_db() or 'cp6_auditor_race'
        return src,'fable_xc1_'+tag
    def leftover_replaced():
        src,scratch=fresh(uuid.uuid4().hex[:8]);made=[scratch]
        mk(scratch,'OLD_OURS')  # a leftover the tool itself marked on an earlier night: since 0b7049d9 the tool's own mark is OID-bound,
        with pg() as c:          # so the fixture writes exactly what the tool writes (token + this database's OID); the oracle is unchanged
            old_oid=c.execute('select oid from pg_database where datname=%s',(scratch,)).fetchone()[0]
            c.execute(sql.SQL('comment on database {} is {}').format(sql.Identifier(scratch),sql.Literal('%s attempt=%s oid=%d'%(nightly.SCRATCH_MARK,'e'*16,old_oid))))
        real=nightly.Tools.dump
        def dump_then_replace(self,s,target,snapshot):
            r=real(self,s,target,snapshot);drop(scratch);mk(scratch,'FOREIGN_AFTER_DUMP');return r
        nightly.Tools.dump=dump_then_replace
        try:rec=night(src,scratch)
        finally:nightly.Tools.dump=real
        try:
            after=state(scratch);left=attempts(scratch)
            kept=after is not None and after['canary']==['FOREIGN_AFTER_DUMP'] and after['comment'] is None and after['other_tables']==0
            ok=kept and rec.get('restore_verified') is False and 'BACKUP_SCRATCH_REPLACED' in str(rec.get('error')) and left==[]
            return dict(status='PASS' if ok else ('COUNTEREXAMPLE' if not kept else 'FAIL'),foreign_kept=kept,foreign_state=after,restore_verified=rec.get('restore_verified'),
                        error=str(rec.get('error'))[:200],scratch_before=rec.get('scratch_before'),leftovers=rec.get('leftovers'),attempt_dbs_left=left,role=role())
        finally:
            for n in made+attempts(scratch):drop(n)
    def attempt_swapped():
        src,scratch=fresh(uuid.uuid4().hex[:8]);moved=scratch+'_moved';made=[moved];swapped={}
        real=nightly.Tools.restore
        def swap_then_restore(self,name,file):
            with pg() as c:c.execute(sql.SQL('alter database {} rename to {}').format(sql.Identifier(name),sql.Identifier(moved)))
            mk(name,'FOREIGN_SWAPPED_IN');swapped['name']=name;made.append(name);return real(self,name,file)
        nightly.Tools.restore=swap_then_restore
        try:rec=night(src,scratch)
        finally:nightly.Tools.restore=real
        try:
            name=swapped.get('name');after=state(name) if name else None;moved_after=state(moved)
            kept=after is not None and 'FOREIGN_SWAPPED_IN' in after['canary']
            own_gone=moved_after is None
            ok=kept and own_gone and rec.get('restore_verified') is False and 'BACKUP_SCRATCH_REPLACED' in str(rec.get('error'))
            return dict(status='PASS' if ok else ('COUNTEREXAMPLE' if not kept else 'FAIL'),foreign_kept=kept,foreign_received_restored_tables=(after or {}).get('other_tables'),
                        own_attempt_dropped_by_oid=own_gone,drop_record=(rec.get('scratch_attempt')or{}).get('drop'),restore_verified=rec.get('restore_verified'),error=str(rec.get('error'))[:200],
                        boundary='writer-stated: tables may be restored into the replacement; it is never dropped and the night is unverified')
        finally:
            for n in made+attempts(scratch):drop(n)
    def copied_oid_mark():
        src,scratch=fresh(uuid.uuid4().hex[:8]);unmarked='%s_%s'%(scratch,secrets.token_hex(8));copied='%s_%s'%(scratch,secrets.token_hex(8));made=[unmarked,copied]
        mk(unmarked,'FOREIGN_UNMARKED')
        with pg() as c:other_oid=c.execute("select oid from pg_database where datname='postgres'").fetchone()[0]
        mk(copied,'FOREIGN_COPIED_MARK','%s attempt=%s oid=%d'%(nightly.SCRATCH_MARK,'f'*16,other_oid))
        rec=night(src,scratch)
        try:
            a,bb=state(unmarked),state(copied);left=attempts(scratch)
            kept=a is not None and a['canary']==['FOREIGN_UNMARKED'] and bb is not None and bb['canary']==['FOREIGN_COPIED_MARK']
            ok=kept and rec.get('restore_verified') is True and sorted(left)==sorted([unmarked,copied])
            return dict(status='PASS' if ok else ('COUNTEREXAMPLE' if not kept else 'FAIL'),unmarked_kept=a is not None,copied_mark_kept=bb is not None,restore_verified=rec.get('restore_verified'),
                        leftovers=rec.get('leftovers'),error=str(rec.get('error'))[:200] if rec.get('error') else None)
        finally:
            for n in made+attempts(scratch):drop(n)
    def plain_mark_copied():
        src,scratch=fresh(uuid.uuid4().hex[:8]);made=[scratch]
        mk(scratch,'FOREIGN_WITH_COPIED_PLAIN_MARK',nightly.SCRATCH_MARK)  # not created by the tool; an administrator copied the legacy mark text
        rec=night(src,scratch)
        try:
            after=state(scratch);kept=after is not None and after['canary']==['FOREIGN_WITH_COPIED_PLAIN_MARK']
            return dict(status='PASS' if kept else 'COUNTEREXAMPLE',foreign_kept=kept,foreign_state=after,scratch_before=rec.get('scratch_before'),leftovers=rec.get('leftovers'),
                        restore_verified=rec.get('restore_verified'),error=str(rec.get('error'))[:200] if rec.get('error') else None,
                        note='Fable oracle: a database the tool did not create must survive even if it carries a copy of the plain mark; the OID-bound mark makes the plain mark unnecessary since no night ever ran outside CI')
        finally:
            for n in made+attempts(scratch):drop(n)
    return [('XC1:LEFTOVER_REPLACED_AFTER_DUMP_KEPT',leftover_replaced),('XC1:ATTEMPT_SWAPPED_BEFORE_RESTORE_KEPT',attempt_swapped),
            ('XC1:COPIED_OID_MARK_ON_FOREIGN_KEPT',copied_oid_mark),('XC1:PLAIN_MARK_COPIED_ONTO_FOREIGN',plain_mark_copied)]
