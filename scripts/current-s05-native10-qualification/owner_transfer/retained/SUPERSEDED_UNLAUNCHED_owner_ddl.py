"""Bounded installer capability for this new role only; no connection/commit.

The caller MUST enclose the whole stage in the inherited atomic savepoint.
The administrative caller remains a superuser; the DDL executes as the exact
postgres owner, which may be a non-superuser CREATEROLE. No existing role,
schema ACL, membership, or GUC is normalized to fit this supported profile.
"""
ROLE = 'cp7_accessory_standard_read'
CREATOR = 'postgres'
ROLE_DDL = ('create role '+ROLE+' nologin noinherit nosuperuser nocreatedb '
            'nocreaterole noreplication nobypassrls;')
IDENTITY_SQL = ("select current_user::text,session_user::text,rolsuper,rolcreaterole,"
                "current_setting('createrole_self_grant'),"
                "(select rolsuper from pg_roles where rolname=session_user) "
                "from pg_roles where rolname=current_user")
PUBLIC_SQL = "select pg_get_userbyid(nspowner)::text,nspacl::text from pg_namespace where nspname='public'"
MEMBERS_SQL = ("select pg_get_userbyid(roleid)::text,pg_get_userbyid(member)::text,"
               "pg_get_userbyid(grantor)::text,admin_option,inherit_option,set_option "
               "from pg_auth_members where roleid=%s::regrole or member=%s::regrole "
               "order by roleid,member,grantor")


def ident(value):
    if not isinstance(value, str) or not value or '\0' in value:
        raise ValueError('S05_INVALID_ROLE_IDENTIFIER')
    return '"'+value.replace('"', '""')+'"'


def identity(cur):
    row = cur.execute(IDENTITY_SQL).fetchone()
    if row is None:
        raise ValueError('S05_CURRENT_ROLE_MISSING')
    return tuple(row)


def members(cur):
    return [tuple(row) for row in cur.execute(MEMBERS_SQL, (ROLE, ROLE))]


def expected_auto_members(creator, superuser, bootstrap):
    if superuser:
        return []
    if creator == bootstrap:
        return [(ROLE, creator, bootstrap, True, True, True)]
    return sorted([(ROLE, creator, bootstrap, True, False, False),
                   (ROLE, creator, creator, False, True, True)])


def checked_outer(cur):
    outer = identity(cur)
    if not outer[2]:
        raise ValueError('S05_ADMINISTRATIVE_SUPERUSER_CALLER_REQUIRED')
    return outer


def assert_restored(cur, outer, public):
    if identity(cur) != outer:
        raise ValueError('S05_INSTALLER_ROLE_OR_GUC_NOT_RESTORED')
    if tuple(cur.execute(PUBLIC_SQL).fetchone()) != public:
        raise ValueError('S05_RAW_PUBLIC_OWNER_OR_ACL_NOT_RESTORED')


def install(cur, as_owner, report_sql):
    """Capture and remove only the new role's exact automatic creator edges."""
    outer = checked_outer(cur)
    public = tuple(cur.execute(PUBLIC_SQL).fetchone())
    # GRANT/REVOKE materializes NULL to a non-NULL default ACL. A fresh role
    # cannot already have a direct CREATE grant. Refuse before any role/DDL;
    # neither resetting the catalog nor changing the declared baseline is safe.
    if public[1] is None:
        raise ValueError('S05_NULL_PUBLIC_ACL_PROFILE_UNSUPPORTED_BEFORE_DDL')
    if cur.execute('select exists(select 1 from pg_roles where rolname=%s)', (ROLE,)).fetchone()[0]:
        raise ValueError('S05_READER_ROLE_ALREADY_EXISTS')
    if report_sql.count(ROLE_DDL) != 1:
        raise ValueError('S05_EXACT_NEW_ROLE_DDL_REQUIRED')
    before_role, body = report_sql.split(ROLE_DDL)
    if any(line.strip() and not line.lstrip().startswith('--') for line in before_role.splitlines()):
        raise ValueError('S05_UNEXPECTED_DDL_BEFORE_NEW_ROLE')
    bootstrap = cur.execute('select rolname::text from pg_roles where oid=10').fetchone()[0]
    with as_owner(cur, CREATOR):
        creator = identity(cur)
        if creator[0] != CREATOR or not (creator[2] or creator[3]):
            raise ValueError('S05_EXACT_POSTGRES_CREATOR_REQUIRED')
        if not cur.execute("select has_schema_privilege(current_user,'public','CREATE WITH GRANT OPTION')").fetchone()[0]:
            raise ValueError('S05_POSTGRES_PUBLIC_CREATE_GRANT_OPTION_REQUIRED')
        cur.execute("select set_config('createrole_self_grant',%s,true)", ('set, inherit',))
        cur.execute(ROLE_DDL, prepare=False)
        # Restore before creating the schema/functions, even on the success path.
        # An SQL failure is restored by the encompassing atomic savepoint.
        cur.execute("select set_config('createrole_self_grant',%s,true)", (creator[4],))
        automatic = members(cur)
        if sorted(automatic) != expected_auto_members(CREATOR, creator[2], bootstrap):
            raise ValueError('S05_UNEXPECTED_NEW_ROLE_CREATOR_MEMBERSHIP')
        cur.execute(body, prepare=False)
        if members(cur) != automatic or identity(cur) != creator:
            raise ValueError('S05_NEW_ROLE_DDL_CHANGED_MEMBERSHIP_OR_GUC')
    if identity(cur) != outer:
        raise ValueError('S05_ADMINISTRATIVE_CALLER_NOT_RESTORED')
    # The creator's self-grant depends on its bootstrap ADMIN edge: remove the
    # dependent self-grant first, then only that exact bootstrap grantor edge.
    for role, member, grantor, *_ in sorted(automatic, key=lambda row: row[2] == bootstrap):
        cur.execute('revoke '+ident(role)+' from '+ident(member)+' granted by '+ident(grantor))
    if members(cur):
        raise ValueError('S05_TEMPORARY_CREATOR_MEMBERSHIP_REMAINS')
    assert_restored(cur, outer, public)
    return dict(status='S05_NEW_READER_OWNER_CAPABILITIES_EXACTLY_RESTORED',
                outer_role=outer[0], session_role=outer[1], creator=creator[0],
                outer_current_superuser=outer[2], session_superuser=outer[5],
                actual_outer_identity=list(outer), actual_creator_identity=list(creator),
                creator_superuser=creator[2], original_createrole_self_grant=creator[4],
                automatic_new_role_memberships=[list(row) for row in automatic],
                membership_rows_after=0, raw_public_owner=public[0], raw_public_acl=public[1],
                raw_NULL_public_ACL_supported=False, persistent_authority_change=False)


def uninstall(cur, as_owner):
    """Drop only the verified new role's objects, with a bounded SET handover."""
    outer = checked_outer(cur)
    public = tuple(cur.execute(PUBLIC_SQL).fetchone())
    if members(cur):
        raise ValueError('S05_UNEXPECTED_EXISTING_READER_MEMBERSHIP')
    # No old membership is overwritten. Stage.verify has already checked the
    # role, all objects, permissions, functions and exact whole22/data baseline.
    cur.execute('grant '+ident(ROLE)+' to '+ident(CREATOR)+
                ' with admin false,inherit true,set true granted by '+ident(outer[0]))
    handover = members(cur)
    if handover != [(ROLE, CREATOR, outer[0], False, True, True)]:
        raise ValueError('S05_UNEXPECTED_UNINSTALL_HANDOVER')
    with as_owner(cur, CREATOR):
        cur.execute('drop owned by '+ident(ROLE)+' cascade', prepare=False)
    # Removing this new role also removes exactly its new handover edge.
    cur.execute('drop role '+ident(ROLE), prepare=False)
    assert_restored(cur, outer, public)
    return dict(status='S05_NEW_READER_ONLY_REMOVED',
                temporary_memberships=[list(row) for row in handover], persistent_authority_change=False)
