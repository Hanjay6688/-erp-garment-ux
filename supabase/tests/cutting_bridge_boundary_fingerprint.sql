\set ON_ERROR_STOP on

select jsonb_build_object(
  'functions',(
    select jsonb_agg(jsonb_build_object(
      'identity',format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
      'definition_sha256',encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
      'owner',pg_get_userbyid(p.proowner),
      'acl',(
        select coalesce(jsonb_agg(jsonb_build_object(
          'grantor',pg_get_userbyid(a.grantor),
          'grantee',case when a.grantee=0 then 'PUBLIC' else pg_get_userbyid(a.grantee) end,
          'privilege',a.privilege_type,
          'grantable',a.is_grantable
        ) order by a.grantor,a.grantee,a.privilege_type,a.is_grantable),'[]'::jsonb)
        from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
      )
    ) order by n.nspname,p.proname,pg_get_function_identity_arguments(p.oid))
    from pg_proc p
    join pg_namespace n on n.oid=p.pronamespace
    where p.oid in(
      'erp.save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)'::regprocedure,
      'erp.post_cutting_material_issue(uuid,uuid)'::regprocedure,
      'erp.get_wip_control_v1(text,uuid,text,text)'::regprocedure,
      'erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)'::regprocedure,
      'erp.sync_material_cost_revaluation(uuid)'::regprocedure,
      'erp.post_journal(text,uuid,date,text,jsonb)'::regprocedure,
      'erp.refresh_accessory_hpp_after_material_recost(uuid,text)'::regprocedure,
      'erp.refresh_material_cost_checkpoint(uuid,date)'::regprocedure
    )
  ),
  'relations',(
    select jsonb_agg(jsonb_build_object(
      'identity',format('%I.%I',n.nspname,c.relname),
      'owner',pg_get_userbyid(c.relowner),
      'acl',(
        select coalesce(jsonb_agg(jsonb_build_object(
          'grantor',pg_get_userbyid(a.grantor),
          'grantee',case when a.grantee=0 then 'PUBLIC' else pg_get_userbyid(a.grantee) end,
          'privilege',a.privilege_type,
          'grantable',a.is_grantable
        ) order by a.grantor,a.grantee,a.privilege_type,a.is_grantable),'[]'::jsonb)
        from aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a
      )
    ) order by n.nspname,c.relname)
    from pg_class c
    join pg_namespace n on n.oid=c.relnamespace
    where c.oid in(
      'erp.cutting_groups'::regclass,
      'erp.cutting_group_size_slots'::regclass,
      'erp.cutting_group_rolls'::regclass,
      'erp.cutting_roll_yields'::regclass,
      'erp.material_rolls'::regclass,
      'erp.material_stock_movements'::regclass,
      'erp.production_orders'::regclass,
      'erp.sizes'::regclass,
      'erp.locations'::regclass
    )
  ),
  'external_application_triggers',(
    select jsonb_agg(jsonb_build_object(
      'table',format('%I.%I',tn.nspname,c.relname),
      'trigger',t.tgname,
      'function',format('%I.%I',fn.nspname,p.proname),
      'definition_sha256',encode(extensions.digest(convert_to(pg_get_triggerdef(t.oid,true),'UTF8'),'sha256'),'hex'),
      'enabled',t.tgenabled
    ) order by tn.nspname,c.relname,t.tgname)
    from pg_trigger t
    join pg_class c on c.oid=t.tgrelid
    join pg_namespace tn on tn.oid=c.relnamespace
    join pg_proc p on p.oid=t.tgfoid
    join pg_namespace fn on fn.oid=p.pronamespace
    where not t.tgisinternal
      and tn.nspname<>'erp'
      and fn.nspname='erp'
  )
);
