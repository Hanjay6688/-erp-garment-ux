"""Qualification-only preservation of exact authority on two fixed local copies."""
import psycopg

COPY_ADMISSIONS=[]
ORIGINAL_COPY_DATABASE=None
PRODUCT=None
STATE=None


def copy_database(name):
    # Qualifier setup only, on the one declared local disposable HTTP copy.
    # Reproduce the source database authority, then run the unchanged complete
    # verifier. No catalog projection, dropped group, or product grant.
    from urllib.parse import urlparse
    from psycopg import sql
    assert name in('cp6_auditor_browser','cp6_auditor_http')
    url=ORIGINAL_COPY_DATABASE(name)
    parsed=urlparse(url)
    assert parsed.hostname in('127.0.0.1','localhost')and parsed.path=='/'+name
    with psycopg.connect(url)as conn,conn.cursor()as cur:
        assert cur.execute('select current_database()').fetchone()[0]==name
        before=PRODUCT.catalog._catalog_rows(cur)
        expected=STATE['installed_catalog']
        changes={group:sorted(key for key in set(before[group])|set(expected[group])
            if before[group].get(key)!=expected[group].get(key))
            for group in expected if before[group]!=expected[group]}
        record=dict(classification='LOCAL_BROWSER_RACE_TEMPLATE_COPY_AUTHORITY_PRESERVATION',
            before_changed_catalog_members=changes,source_database_authority=expected['database_authority'],
            actual_copy_before_authority=before['database_authority'],
            full22_after_must_equal_original_install=True,product_state_modified=False,
            Native_or_schema_or_RPC_permissions_changed=False)
        COPY_ADMISSIONS.append(record)
        assert changes=={'database_authority':['CURRENT']},('UNDECLARED_HTTP_COPY_CATALOG_CHANGE',changes)
        source=expected['database_authority']['CURRENT']
        assert source[0]=='postgres'and source[8]is None
        # The actual generic createdb template copy has the admin owner and
        # default database ACL/settings; every other observed object is exact.
        acl=PRODUCT.catalog._acl('null::aclitem[]','r.oid','d')
        query="select jsonb_build_array(pg_get_userbyid(r.oid),%s::text,%s::text,%s::text,-1,false,true,"+acl+",null)from pg_roles r where r.rolname='supabase_admin'"
        fresh=cur.execute(query,tuple(source[1:4])).fetchone()[0]
        assert before['database_authority']=={'CURRENT':fresh},'HTTP_COPY_IS_NOT_EXACT_FRESH_CREATEDB_AUTHORITY'
        cur.execute(sql.SQL('alter database {} owner to postgres').format(sql.Identifier(name)))
        cur.execute('set local role postgres')
        with PRODUCT.catalog._catalog(cur):
            current=cur.execute(PRODUCT.catalog.QUERIES['database_authority']).fetchone()[1]
        if current[7]!=source[7]:
            assert all(row[1]=='postgres'and row[2]in('CONNECT','CREATE','TEMPORARY')for row in source[7])
            for principal in sorted({row[0]for row in current[7]}):
                who=sql.SQL('PUBLIC')if principal=='PUBLIC'else sql.Identifier(principal)
                cur.execute(sql.SQL('revoke all privileges on database {} from {}').format(sql.Identifier(name),who))
            for principal,grantor,privilege,grantable in source[7]:
                who=sql.SQL('PUBLIC')if principal=='PUBLIC'else sql.Identifier(principal)
                cur.execute(sql.SQL('grant {} on database {} to {}{}').format(sql.SQL(privilege),
                    sql.Identifier(name),who,sql.SQL(' with grant option')if grantable else sql.SQL('')))
        cur.execute('reset role')
        after=PRODUCT.catalog._catalog_rows(cur)
        assert after==expected,'HTTP_TEMPLATE_COPY_COMPLETE22_NOT_IDENTICAL_AFTER_AUTHORITY_PRESERVATION'
        record.update(actual_copy_after_authority=after['database_authority'],
            all22_groups_equal_original_install=True,exact_catalog_sha256=PRODUCT.catalog.digest(after))
        PRODUCT.verify(cur,STATE)
        conn.commit()
    return url
