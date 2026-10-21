-- Proposal only; this helper has NOT executed this SQL.
-- Execute with search_path='' in the caller's existing catalog_path context.
-- Capture ALL triggers, including disabled triggers and RI internals.
with scope as (
 select c.oid,n.nspname||'.'||c.relname as relation,
  pg_get_userbyid(c.relowner) as owner,c.relkind::text as kind,
  c.relispartition,c.relhasrules
 from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname='erp'and c.relname=any(array[
  'sales_headers','sales_payments','sales_returns',
  'fg_stock_movements','journal_entries','hpp_versions'])
), fk as (
 select k.oid,k.conname,k.conrelid,k.confrelid,
  jsonb_build_object(
   'relation',cn.nspname||'.'||cc.relname,
   'columns',(select jsonb_agg(a.attname order by x.ord)
    from unnest(k.conkey)with ordinality x(attnum,ord)
    join pg_attribute a on a.attrelid=k.conrelid and a.attnum=x.attnum),
   'parent',pn.nspname||'.'||pc.relname,
   'parent_columns',(select jsonb_agg(a.attname order by x.ord)
    from unnest(k.confkey)with ordinality x(attnum,ord)
    join pg_attribute a on a.attrelid=k.confrelid and a.attnum=x.attnum),
   'update_action',k.confupdtype::text,'delete_action',k.confdeltype::text,
   'match_type',k.confmatchtype::text,'deferrable',k.condeferrable,
   'initially_deferred',k.condeferred,'validated',k.convalidated)as semantic,
  pg_get_constraintdef(k.oid,false)as definition
 from pg_constraint k
 join pg_class cc on cc.oid=k.conrelid join pg_namespace cn on cn.oid=cc.relnamespace
 join pg_class pc on pc.oid=k.confrelid join pg_namespace pn on pn.oid=pc.relnamespace
 where k.contype='f'and(k.conrelid in(select oid from scope)or k.confrelid in(select oid from scope))
), tr as (
 select t.oid,t.tgfoid,jsonb_build_object(
  'trigger_oid',t.oid,'function_oid',t.tgfoid,
  'relation',s.relation,'relation_owner',s.owner,
  'name',t.tgname,'enabled',t.tgenabled::text,'internal',t.tgisinternal,
  'function',fn.nspname||'.'||p.proname||'('||pg_get_function_identity_arguments(p.oid)||')',
  'trigger_type',t.tgtype,'argument_count',t.tgnargs,
  'args_hex',encode(t.tgargs,'hex'),
  'columns',coalesce((select jsonb_agg(a.attname order by x.ord)
   from unnest(t.tgattr::smallint[])with ordinality x(attnum,ord)
   join pg_attribute a on a.attrelid=t.tgrelid and a.attnum=x.attnum),'[]'::jsonb),
  'deferrable',t.tgdeferrable,'initially_deferred',t.tginitdeferred,
  'condition',pg_get_expr(t.tgqual,t.tgrelid,false),
  'old_table',t.tgoldtable,'new_table',t.tgnewtable,
  'parent_trigger',case when t.tgparentid=0 then null else jsonb_build_array(
    ptn.nspname,ptc.relname,pt.tgname)end,
  'referenced_relation',case when t.tgconstrrelid=0 then null else crn.nspname||'.'||cr.relname end,
  'constraint',case when t.tgconstraint=0 then null else jsonb_build_object(
    'oid',k.oid,'name',k.conname,'type',k.contype::text,
    'semantic',f.semantic,'definition',pg_get_constraintdef(k.oid,false))end,
  'definition',pg_get_triggerdef(t.oid,false),
  'definition_sha256',encode(sha256(convert_to(pg_get_triggerdef(t.oid,false),'UTF8')),'hex'))as row
 from scope s join pg_trigger t on t.tgrelid=s.oid
 join pg_proc p on p.oid=t.tgfoid join pg_namespace fn on fn.oid=p.pronamespace
 left join pg_trigger pt on pt.oid=t.tgparentid
 left join pg_class ptc on ptc.oid=pt.tgrelid left join pg_namespace ptn on ptn.oid=ptc.relnamespace
 left join pg_class cr on cr.oid=t.tgconstrrelid left join pg_namespace crn on crn.oid=cr.relnamespace
 left join pg_constraint k on k.oid=t.tgconstraint left join fk f on f.oid=k.oid
), funcs as (
 select p.oid,fn.nspname||'.'||p.proname||'('||pg_get_function_identity_arguments(p.oid)||')'as identity,
  jsonb_build_object(
   'function_oid',p.oid,'identity',fn.nspname||'.'||p.proname||'('||pg_get_function_identity_arguments(p.oid)||')',
   'owner',pg_get_userbyid(p.proowner),'language',l.lanname,
   'security_definer',p.prosecdef,'volatility',p.provolatile::text,
   'config',coalesce(to_jsonb(p.proconfig),'[]'::jsonb),
   'acl',(select coalesce(jsonb_agg(jsonb_build_object(
     'grantee',case when a.grantee=0 then 'PUBLIC'else pg_get_userbyid(a.grantee)end,
     'privilege',a.privilege_type,'grantable',a.is_grantable)
     order by case when a.grantee=0 then 'PUBLIC'else pg_get_userbyid(a.grantee)end,a.privilege_type,a.is_grantable),'[]'::jsonb)
    from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner)))a),
   'result',pg_get_function_result(p.oid),'input_arguments',pg_get_function_identity_arguments(p.oid),
   'body',p.prosrc,'body_sha256',encode(sha256(convert_to(p.prosrc,'UTF8')),'hex'),
   'definition',pg_get_functiondef(p.oid),
   'definition_sha256',encode(sha256(convert_to(pg_get_functiondef(p.oid),'UTF8')),'hex'),
   'proc_raw',to_jsonb(p),'owner_oid',p.proowner,'language_oid',p.prolang)as row
 from pg_proc p join pg_namespace fn on fn.oid=p.pronamespace join pg_language l on l.oid=p.prolang
 where p.oid in(select tgfoid from tr)
)
select jsonb_build_object(
 'relations',(select coalesce(jsonb_agg(to_jsonb(s)order by s.relation),'[]'::jsonb)from scope s),
 'triggers',(select coalesce(jsonb_agg(row order by oid),'[]'::jsonb)from tr),
 'functions',(select coalesce(jsonb_agg(row order by identity),'[]'::jsonb)from funcs),
 'foreign_keys',(select coalesce(jsonb_agg(jsonb_build_object('oid',oid,'name',conname,
   'semantic',semantic,'definition',definition)order by oid),'[]'::jsonb)from fk)
);
