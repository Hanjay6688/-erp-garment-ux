-- Use the request identity carried by existing authenticated warehouse, journal and finance calls.
do $warehouse_finance_identity$
declare
    item_ record;
    r_ name;
    f_ record;
    accessor_ record;
    changed_ text;
    roles_ constant name[]:=array['cp7_fg_read','cp7_fg_write','cp7_finance_read','cp7_journal_read','cp7_material_read','cp7_material_write','cp7_misc_read','cp7_misc_write','cp7_recost_read','cp7_recost_write','cp7_return_read','cp7_return_write']::name[];
    memberships_ jsonb;
    owners_ jsonb;
begin
    if session_user <> 'postgres' or current_user <> 'postgres' or current_setting('is_superuser') <> 'off' then
        raise exception 'Expected the managed Enteng Uji installer';
    end if;
    foreach r_ in array roles_ loop
        if pg_has_role('postgres',r_,'SET') or pg_has_role('postgres',r_,'USAGE') or
            not exists(select from pg_roles where rolname=r_ and not (rolcanlogin or rolsuper or rolcreaterole or rolcreatedb) and rolbypassrls=(r_ in ('cp7_fg_read','cp7_finance_read','cp7_journal_read','cp7_material_read','cp7_misc_read','cp7_recost_read','cp7_return_read')))
            or exists(select from unnest(array['anon','authenticated','service_role']) a where pg_has_role(a,r_,'SET')) then
            raise exception 'Expected a qualified private ERP role';
        end if;
    end loop;
    for accessor_ in select * from (values
        ('uid','uuid','9ab5ea099e74ec09e83b1505c51a3647791195aed7c742dcc3f257dfc7d2f300'),
        ('jwt','jsonb','fed2a8ac0349ffaba807c1b574698bfb1348825b8ef5163ad72d8408386f5e3e')
    ) v(method,returns,pin) loop
        if not exists(select from pg_proc p where p.oid=to_regprocedure('cp7_request_context.'||accessor_.method||'()')
            and p.proowner='postgres'::regrole and not p.prosecdef and p.provolatile='s'
            and p.pronargs=0 and p.prorettype::regtype::text=accessor_.returns and p.proconfig=array['search_path=""']::text[]
            and encode(sha256(convert_to(p.prosrc,'UTF8')),'hex')=accessor_.pin
            and not exists(select from unnest(array['anon','authenticated','service_role']) a
               where has_schema_privilege(a,'cp7_request_context','USAGE') or has_function_privilege(a,p.oid,'EXECUTE'))) then
            raise exception 'Unexpected operator identity reader';
        end if;
    end loop;
    select jsonb_agg(to_jsonb(m) order by m.roleid,m.grantor) into memberships_ from pg_auth_members m
        where m.member='postgres'::regrole and (m.roleid::regrole::text)::name=any(roles_);
    select jsonb_object_agg(nspname,jsonb_build_array(nspowner,nspacl::text)) into owners_ from pg_namespace
        where nspname=any(array['cp7_fg','cp7_finance','cp7_journal','cp7_material','cp7_misc_correction','cp7_recost','cp7_supplier_return']);
    grant cp7_fg_read,cp7_fg_write,cp7_finance_read,cp7_journal_read,cp7_material_read,cp7_material_write,cp7_misc_read,cp7_misc_write,cp7_recost_read,cp7_recost_write,cp7_return_read,cp7_return_write to postgres with inherit false, set true granted by postgres;
    grant usage on schema cp7_request_context to cp7_fg_read,cp7_fg_write,cp7_finance_read,cp7_journal_read,cp7_material_read,cp7_material_write,cp7_misc_write,cp7_recost_read,cp7_recost_write,cp7_return_read,cp7_return_write;
    grant execute on function cp7_request_context.uid() to cp7_fg_read,cp7_fg_write,cp7_finance_read,cp7_journal_read,cp7_material_read,cp7_material_write,cp7_misc_write,cp7_recost_read,cp7_recost_write,cp7_return_read,cp7_return_write;
    grant execute on function cp7_request_context.jwt() to cp7_fg_read,cp7_fg_write,cp7_finance_read,cp7_journal_read,cp7_material_read,cp7_material_write,cp7_recost_read,cp7_recost_write,cp7_return_read,cp7_return_write;
    for item_ in select * from (values
      ('cp7_fg.access_now(text)','cp7_fg_read','cp7_fg_read',3,'fcefa59812bbb2336eabfde1539fe6d706b73b840f50e402725cd3d839d05e78'),
      ('cp7_fg.adjust_command(text,jsonb,uuid,text)','cp7_fg_write','cp7_fg_read',3,'a9c8eff61b572d0c10b542f542d76c28e6bfd88fe3ad83ed1d07af388bdb8ccf'),
      ('cp7_fg.book_command(text,jsonb,uuid)','cp7_fg_write','cp7_fg_read',3,'53165eaa1b4a3efe57f7593b4279916a32763b7758feb3257d74b5d54c8a6462'),
      ('cp7_finance.access_now()','cp7_finance_read','cp7_finance_read',2,'f21a53171786463987bbeee55039d4b4c0b909bd633734dff4781bfa2ccd4a17'),
      ('cp7_journal.access_now()','cp7_journal_read','cp7_journal_read',2,'979e1fa9e37c452a871f3adb99e694738ecc1ae6e574dd5086a68961bc261b20'),
      ('cp7_material.access_now()','cp7_material_read','cp7_material_read',3,'48795f9a5fb83a7f71fc0640f11f8692b1e52f08c38cecb5825e648ed57fc017'),
      ('cp7_material.command(text,jsonb,uuid,text)','cp7_material_write','cp7_material_read',5,'85c6bdb4a9a65fbb4401a8c3884e0c9bbe63a16fe02d9418eb07ef30dfff31b4'),
      ('cp7_material.count_command(text,jsonb,uuid,text)','cp7_material_write','cp7_material_read',5,'8cc33089ad51c81b974b359d4d84df74558666c18432f80c29e8f98d3ddf61fc'),
      ('cp7_misc_correction.command(jsonb,uuid)','cp7_misc_write','cp7_misc_read',4,'1ba1bbcea8f18571a2352648c47be0b51b631899660b998f2b58502a339da33e'),
      ('cp7_recost.access_now(boolean)','cp7_recost_read','cp7_recost_read',2,'857e2940bd94806a824b9c9558f835abd12cce0f10bf46dc720d2acfe27f0d51'),
      ('cp7_recost.command(jsonb,uuid)','cp7_recost_write','cp7_recost_read',1,'4147eca1d8416b10d27caf084e54027e9bcd6f0bd64649f192f488ad2102c8a9'),
      ('cp7_supplier_return.access_now()','cp7_return_read','cp7_return_read',3,'12e31bf33469378d61332a4a125a2b7a7109dceba36fc83b0565d23f08fcfa7b'),
      ('cp7_supplier_return.command(text,jsonb,uuid,text)','cp7_return_write','cp7_return_read',4,'27d215d56ad7c1feb9a3f851d143a49bc61d2d5803e032ead875cbacb3f0989a'),
      ('cp7_supplier_return.document_command(text,jsonb,uuid,text)','cp7_return_write','cp7_return_read',4,'cce877f979176a81dbb3df6c3df80d6dda39efd111c1e0a26bb33b0e9a83b885')
    ) v(signature,owner_role,schema_owner,calls,pin) loop
        select p.oid,p.prosrc body,to_jsonb(p)-'prosrc' metadata,pg_get_functiondef(p.oid) ddl,
            n.nspname schema_name,has_schema_privilege(p.proowner,n.oid,'CREATE') can_create into strict f_
            from pg_proc p join pg_namespace n on n.oid=p.pronamespace
            where p.oid=to_regprocedure(item_.signature) and pg_get_userbyid(p.proowner)=item_.owner_role
              and pg_get_userbyid(n.nspowner)=item_.schema_owner and not p.prosecdef
              and encode(sha256(convert_to(p.prosrc,'UTF8')),'hex')=item_.pin;
        if regexp_count(f_.body,'\mauth\.(uid|jwt)\(\)',1,'i')<>item_.calls or position('cp7_request_context.' in f_.body)>0
            or exists(select from unnest(array['anon','authenticated','service_role']) a
              where has_schema_privilege(a,f_.schema_name,'USAGE') and has_function_privilege(a,f_.oid,'EXECUTE')) then
            raise exception 'Warehouse or finance operator route changed for %',item_.signature;
        end if;
        changed_:=regexp_replace(f_.body,'\mauth\.(uid|jwt)\(\)','cp7_request_context.\1()','gi');
        if not f_.can_create then
            execute format('set local role %I',item_.schema_owner);
            execute format('grant create on schema %I to %I',f_.schema_name,item_.owner_role);
        end if;
        execute format('set local role %I',item_.owner_role);
        execute replace(f_.ddl,f_.body,changed_);
        if not f_.can_create then
            execute format('set local role %I',item_.schema_owner);
            execute format('revoke create on schema %I from %I',f_.schema_name,item_.owner_role);
        end if;
        execute 'reset role';
        if not exists(select from pg_proc p where p.oid=f_.oid and p.prosrc=changed_ and to_jsonb(p)-'prosrc'=f_.metadata) then
            raise exception 'Warehouse or finance operator routine metadata changed';
        end if;
    end loop;
    revoke cp7_fg_read,cp7_fg_write,cp7_finance_read,cp7_journal_read,cp7_material_read,cp7_material_write,cp7_misc_read,cp7_misc_write,cp7_recost_read,cp7_recost_write,cp7_return_read,cp7_return_write from postgres granted by postgres restrict;
    if memberships_ is distinct from (select jsonb_agg(to_jsonb(m) order by m.roleid,m.grantor) from pg_auth_members m
        where m.member='postgres'::regrole and (m.roleid::regrole::text)::name=any(roles_))
       or owners_ is distinct from (select jsonb_object_agg(nspname,jsonb_build_array(nspowner,nspacl::text)) from pg_namespace
        where nspname=any(array['cp7_fg','cp7_finance','cp7_journal','cp7_material','cp7_misc_correction','cp7_recost','cp7_supplier_return'])) then
        raise exception 'Warehouse or finance operator release changed an existing schema or left installer rights open';
    end if;
end $warehouse_finance_identity$;
