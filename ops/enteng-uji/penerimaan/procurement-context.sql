-- Keep the four purchasing functions bound to the operator of the active request.
do $procurement$
declare
    read_role_ constant text := 'cp7_procure_read';
    write_role_ constant text := 'cp7_procure_write';
    item_ record;
    obj_ record;
    role_ text;
    context_ text;
    clauses_ text;
    memberships_ jsonb;
    schema_acl_ text;
    meta_ jsonb;
begin
    if current_user <> 'postgres' or session_user <> 'postgres' or current_setting('is_superuser') <> 'off' then
        raise exception 'The managed postgres installer is required';
    end if;
    if (select nspowner from pg_namespace where nspname='cp7_procurement') is distinct from read_role_::regrole then
        raise exception 'The procurement schema owner changed';
    end if;
    select nspacl::text into strict schema_acl_ from pg_namespace where nspname='cp7_procurement';
    foreach role_ in array array[read_role_,write_role_] loop
        if not exists (select from pg_roles where rolname=role_ and not rolcanlogin and not rolsuper and not rolcreaterole and not rolcreatedb)
           or pg_has_role('postgres',role_,'USAGE') or pg_has_role('postgres',role_,'SET')
           or exists(select from unnest(array['anon','authenticated','service_role']) a where pg_has_role(a,role_,'SET')) then
            raise exception 'Procurement role authority changed for %',role_;
        end if;
    end loop;
    for item_ in select * from (values
        ('uid','uuid','9ab5ea099e74ec09e83b1505c51a3647791195aed7c742dcc3f257dfc7d2f300'),
        ('jwt','jsonb','fed2a8ac0349ffaba807c1b574698bfb1348825b8ef5163ad72d8408386f5e3e')
    ) q(accessor,returns,source_hash) loop
        context_ := 'cp7_request_context.'||item_.accessor||'()';
        if not exists (select from pg_proc where oid=to_regprocedure(context_) and proowner='postgres'::regrole and not prosecdef and provolatile='s'
          and pronargs=0 and prorettype::regtype::text=item_.returns and proconfig=array['search_path=""']::text[]
          and encode(sha256(convert_to(prosrc,'UTF8')),'hex')=item_.source_hash)
          or exists (select from unnest(array['anon','authenticated','service_role']) a
            where has_schema_privilege(a,'cp7_request_context','USAGE') or has_function_privilege(a,context_,'EXECUTE')) then
            raise exception 'The private operator reader changed';
        end if;
    end loop;
    select coalesce(jsonb_agg(to_jsonb(m) order by roleid,granted_by),'[]') into memberships_
      from (select m.*,m.grantor as granted_by from pg_auth_members m where m.roleid in (read_role_::regrole,write_role_::regrole)
            and m.member='postgres'::regrole) m;
    execute 'grant cp7_procure_read, cp7_procure_write to postgres with inherit false, set true granted by postgres';
    foreach role_ in array array[read_role_,write_role_] loop
        execute format('grant usage on schema cp7_request_context to %I',role_);
        execute format('grant execute on function cp7_request_context.uid(), cp7_request_context.jwt() to %I',role_);
    end loop;
    for item_ in select * from (values
      ('cp7_procurement.access_now()',read_role_,3,'884ee0fe806db2f2c3cb46933491afff2a74fde88da2b358f9d7786b51b0dcb0'),
      ('cp7_procurement.command(text,jsonb,uuid,text)',write_role_,2,'b5dd84953e12afde2f6a8adeefb05a087fa0a474adb8e486cab48470e1706615'),
      ('cp7_procurement.reverse_request(jsonb,uuid,text)',write_role_,3,'e3db8ffeaf9e32ee92be919957e68e27c1b46e2e7c8284bb576cd9b7e27c6794'),
      ('cp7_procurement.save_draft_request(jsonb,uuid,text)',write_role_,3,'272c396524af740a33421b31f1e70e30ea1c0c52359774663080a54e9d8d8fa0')
    ) q(signature,owner_role,calls,source_hash) loop
        select p.prosrc as body,pg_get_functiondef(p.oid) as ddl,p.oid,
               to_jsonb(p)-'prosrc' as metadata,has_schema_privilege(p.proowner,p.pronamespace,'CREATE') as can_create
        into strict obj_ from pg_proc p where p.oid=to_regprocedure(item_.signature)
            and p.proowner=item_.owner_role::regrole and not p.prosecdef
            and encode(sha256(convert_to(p.prosrc,'UTF8')),'hex')=item_.source_hash;
        if regexp_count(obj_.body,'\mauth\.(uid|jwt)\(\)',1,'i')<>item_.calls or
           position('cp7_request_context.' in obj_.body)>0 or
           exists(select from unnest(array['anon','authenticated','service_role']) a where
              has_schema_privilege(a,'cp7_procurement','USAGE') and has_function_privilege(a,obj_.oid,'EXECUTE')) then
            raise exception 'The procurement identity route changed for %',item_.signature;
        end if;
        clauses_:=regexp_replace(obj_.body,'\mauth\.(uid|jwt)\(\)','cp7_request_context.\1()','gi');
        if not obj_.can_create then
            execute format('set local role %I',read_role_);
            execute format('grant create on schema cp7_procurement to %I',item_.owner_role);
        end if;
        execute format('set local role %I',item_.owner_role);
        execute replace(obj_.ddl,obj_.body,clauses_);
        if not obj_.can_create then
            execute format('set local role %I',read_role_);
            execute format('revoke create on schema cp7_procurement from %I',item_.owner_role);
        end if;
        execute 'reset role';
        select to_jsonb(p)-'prosrc' into strict meta_ from pg_proc p where p.oid=obj_.oid and p.prosrc=clauses_;
        if meta_ is distinct from obj_.metadata then
            raise exception 'Owner, grants or routine identity changed for %',item_.signature;
        end if;
    end loop;
    execute 'revoke cp7_procure_read, cp7_procure_write from postgres granted by postgres restrict';
    if schema_acl_ is distinct from (select nspacl::text from pg_namespace where nspname='cp7_procurement')
      or memberships_ is distinct from (select coalesce(jsonb_agg(to_jsonb(m) order by roleid,granted_by),'[]')
          from (select m.*,m.grantor as granted_by from pg_auth_members m where m.roleid in (read_role_::regrole,write_role_::regrole)
                and m.member='postgres'::regrole) m) then
        raise exception 'Temporary installation rights were not restored';
    end if;
end $procurement$;
