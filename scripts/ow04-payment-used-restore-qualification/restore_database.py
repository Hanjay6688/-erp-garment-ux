"""Fixed disposable full-database restore helpers from the qualified old drill.

Database owner, ACL, settings and platform schema authority are reproduced
physically. No ignored metadata group, public grant or runtime bypass.
"""
import psycopg
from psycopg import sql
import cp6_t3_backup_restore_drill as drill

SOURCE='cp6_rollback'
RESTORED='ow04_payment_restore'
PLATFORM_SCHEMAS=('graphql','graphql_public')
core=None

def _platform_schema_authority(cur):
    """Exact source grants for two extension-created platform schemas."""
    result={}
    for name,owner in cur.execute('select nspname,pg_get_userbyid(nspowner)from pg_namespace '
            'where nspname=any(%s::text[])order by nspname',(list(PLATFORM_SCHEMAS),)).fetchall():
        grants=cur.execute("select case when a.grantee=0 then'PUBLIC'else pg_get_userbyid(a.grantee)end,"
            'a.privilege_type,a.is_grantable,pg_get_userbyid(a.grantor)from pg_namespace n '
            "cross join lateral aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner)))a "
            'where n.nspname=%s order by 1,2,3,4',(name,)).fetchall()
        result[name]=dict(owner=owner,grants=grants)
    return result

def _database_profile(db):
    with psycopg.connect(drill.url(db))as conn,conn.cursor()as cur:
        owner,encoding,collate,ctype,limit=cur.execute('select pg_get_userbyid(datdba),pg_encoding_to_char(encoding),'
            'datcollate,datctype,datconnlimit from pg_database where datname=current_database()').fetchone()
        grants=cur.execute("select case when x.grantee=0 then'PUBLIC'else pg_get_userbyid(x.grantee)end,"
            'x.privilege_type,x.is_grantable,pg_get_userbyid(x.grantor)from pg_database d '
            "cross join lateral aclexplode(coalesce(d.datacl,acldefault('d',d.datdba)))x "
            'where d.datname=current_database()order by 1,2,3,4').fetchall()
        settings=cur.execute("select case when s.setrole=0 then null else pg_get_userbyid(s.setrole)end,s.setconfig "
            'from pg_db_role_setting s join pg_database d on d.oid=s.setdatabase '
            'where d.datname=current_database()order by 1 nulls first').fetchall()
        assert owner=='postgres'and all(row[3]==owner for row in grants),'USED_RESTORE_SOURCE_DATABASE_AUTHORITY_CHANGED'
        return dict(owner=owner,encoding=encoding,collate=collate,ctype=ctype,limit=limit,
            grants=grants,settings=settings,platform_schemas=_platform_schema_authority(cur))

def _restore(path,db,profile):
    assert db in(SOURCE,RESTORED)and profile['owner']=='postgres'
    drill.docker('dropdb','-U','supabase_admin','--if-exists','--force',db,check=False)
    drill.docker('createdb','-U','supabase_admin','--maintenance-db=template1','-T','template0',
        '--owner=postgres','--encoding='+profile['encoding'],'--lc-collate='+profile['collate'],
        '--lc-ctype='+profile['ctype'],db)
    result=drill.docker('pg_restore','-U','supabase_admin','-d',db,'--no-password',path,check=False)
    errors=[line for line in result.stderr.splitlines()if line.startswith('pg_restore: error:')]
    unexplained=[line for line in errors if not drill.CRON_ERROR.match(line)]
    with psycopg.connect(drill.url(db))as conn,conn.cursor()as cur:
        actual=_database_profile(db)
        for grantee in sorted({'PUBLIC'}|{v[0]for v in actual['grants']}):
            principal=sql.SQL('public')if grantee=='PUBLIC'else sql.Identifier(grantee)
            cur.execute(sql.SQL('revoke all privileges on database {} from {}').format(sql.Identifier(db),principal))
        for grantee,privilege,grantable,grantor in profile['grants']:
            assert privilege in('CONNECT','CREATE','TEMPORARY')and grantor=='postgres'
            principal=sql.SQL('public')if grantee=='PUBLIC'else sql.Identifier(grantee)
            cur.execute(sql.SQL('grant {} on database {} to {}{}').format(sql.SQL(privilege),sql.Identifier(db),principal,
                sql.SQL(' with grant option'if grantable else'')))
        cur.execute(sql.SQL('alter database {} connection limit {}').format(sql.Identifier(db),sql.Literal(profile['limit'])))
        for role,settings in profile['settings']:
            for setting in settings:
                key,separator,value=setting.partition('=');assert separator
                if role is None:
                    command=sql.SQL('alter database {} set {} to {}').format(sql.Identifier(db),sql.Identifier(key),sql.Literal(value))
                else:
                    command=sql.SQL('alter role {} in database {} set {} to {}').format(sql.Identifier(role),sql.Identifier(db),sql.Identifier(key),sql.Literal(value))
                cur.execute(command)
        # pg_graphql creates these schemas during CREATE EXTENSION. Replay the
        # source backup's exact owner/grants; do not treat privilege drift as
        # portable equality. This is an explicit caller restore step, before
        # the product API attests metadata and changes its sole OID seal.
        original_user=cur.execute('select current_user').fetchone()[0]
        for name,wanted in profile['platform_schemas'].items():
            assert name in PLATFORM_SCHEMAS and all(g[3]==wanted['owner']for g in wanted['grants'])
            current=actual['platform_schemas'][name]
            cur.execute(sql.SQL('alter schema {} owner to {}').format(sql.Identifier(name),sql.Identifier(wanted['owner'])))
            cur.execute(sql.SQL('set local role {}').format(sql.Identifier(wanted['owner'])))
            for grantee in sorted({'PUBLIC',current['owner'],wanted['owner']}|{g[0]for g in current['grants']}):
                principal=sql.SQL('public')if grantee=='PUBLIC'else sql.Identifier(grantee)
                cur.execute(sql.SQL('revoke all privileges on schema {} from {} cascade').format(sql.Identifier(name),principal))
            for grantee,privilege,grantable,grantor in wanted['grants']:
                assert privilege in('CREATE','USAGE')and grantor==wanted['owner']
                principal=sql.SQL('public')if grantee=='PUBLIC'else sql.Identifier(grantee)
                cur.execute(sql.SQL('grant {} on schema {} to {}{}').format(sql.SQL(privilege),sql.Identifier(name),principal,
                    sql.SQL(' with grant option'if grantable else'')))
            cur.execute(sql.SQL('set local role {}').format(sql.Identifier(original_user)))
        conn.commit()
    assert _database_profile(db)==profile,'USED_RESTORE_DATABASE_OWNER_ACL_OR_SETTINGS_CHANGED'
    return dict(exit=result.returncode,error_count=len(errors),unexplained=unexplained[:40],
        only_pg_cron_errors=not unexplained,database_owner_acl_and_settings_preserved=True,
        platform_schema_authority_restored=sorted(profile['platform_schemas']))

def _roles(cur):
    return {r[0] for r in cur.execute("select rolname from pg_roles where rolname like 'cp7_%'").fetchall()}

def _foundation(cur):
    granted=not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
    if granted:cur.execute('grant usage on schema erp to authenticated')
    seeded=not cur.execute('select count(*)from erp.app_users').fetchone()[0]
    if seeded:core.native.api.seed(cur)
    # Native's retained fixture and the Data API use UTC sessions. Review
    # tokens include jsonb timestamp text, so both sides of a restore must use
    # the same session zone. Business/economic dates are explicitly WIB.
    cur.execute("set local timezone='UTC';set local statement_timeout='240s';set local lock_timeout='8s'")
    return granted,seeded
