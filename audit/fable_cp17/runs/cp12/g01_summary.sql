
with ext as (
  select objid,classid from pg_depend where deptype='e'
), nsp as (
  select oid,nspname from pg_namespace where nspname in ('erp','public')
), fn as (
  select n.nspname||'.'||p.proname||'('||pg_get_function_identity_arguments(p.oid)||')' k,p.*
  from pg_proc p join nsp n on n.oid=p.pronamespace
  where not exists(select 1 from ext e where e.classid='pg_proc'::regclass and e.objid=p.oid)
), rel as (
  select n.nspname||'.'||c.relname k,c.*
  from pg_class c join nsp n on n.oid=c.relnamespace
  where c.relkind in ('r','p','v','m','S','f')
    and not exists(select 1 from ext e where e.classid='pg_class'::regclass and e.objid=c.oid)
), o(kind,k,h) as (
  -- function bodies (pg_get_functiondef includes language, volatility, security, search_path)
  select 'function',k,md5(pg_get_functiondef(oid)) from fn where prokind<>'a'
  union all
  select 'function_owner_acl',k,md5(pg_get_userbyid(proowner)||'|'||coalesce((
    select string_agg(v,',' order by v) from (select case a.grantee when 0 then 'PUBLIC' else pg_get_userbyid(a.grantee)::text end
      ||':'||a.privilege_type||':'||a.is_grantable v
    from aclexplode(coalesce(proacl,acldefault('f',proowner))) a) z),'')) from fn
  union all
  select 'relation',k,md5(relkind::text||'|'||relpersistence::text||'|'||relrowsecurity||'|'||relforcerowsecurity
    ||'|'||coalesce(array_to_string(reloptions,','),'')||'|'||coalesce((
    select string_agg(a.attname||' '||format_type(a.atttypid,a.atttypmod)||' '||a.attnotnull
      ||' '||coalesce(pg_get_expr(d.adbin,d.adrelid),'')||' '||a.attidentity::text||' '||a.attgenerated::text
      ||' '||coalesce(co.collname,''),',' order by a.attnum)
    from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum
    left join pg_collation co on co.oid=a.attcollation and a.attcollation<>0
      and co.collname<>'default'
    where a.attrelid=rel.oid and a.attnum>0 and not a.attisdropped),'')) from rel
  union all
  select 'relation_owner_acl',k,md5(pg_get_userbyid(relowner)||'|'||coalesce((
    select string_agg(v,',' order by v) from (select case a.grantee when 0 then 'PUBLIC' else pg_get_userbyid(a.grantee)::text end
      ||':'||a.privilege_type||':'||a.is_grantable v
    from aclexplode(coalesce(relacl,acldefault((case when relkind='S' then 's' else 'r' end)::"char",relowner))) a) z),'')
    ||'|'||coalesce((select string_agg(x.attname||'='||x.attacl::text,',' order by x.attname)
      from pg_attribute x where x.attrelid=rel.oid and x.attacl is not null and not x.attisdropped),'')) from rel
  union all
  select 'view',k,md5(pg_get_viewdef(oid)) from rel where relkind in ('v','m')
  union all
  select 'sequence',r.k,md5(format_type(s.seqtypid,null)||'|'||s.seqstart||'|'||s.seqincrement||'|'||s.seqmax
    ||'|'||s.seqmin||'|'||s.seqcache||'|'||s.seqcycle||'|'||coalesce((
      select dc.relname||'.'||da.attname from pg_depend d join pg_class dc on dc.oid=d.refobjid
      join pg_attribute da on da.attrelid=d.refobjid and da.attnum=d.refobjsubid
      where d.classid='pg_class'::regclass and d.objid=r.oid and d.deptype in ('a','i') limit 1),''))
  from rel r join pg_sequence s on s.seqrelid=r.oid
  union all
  select 'constraint',r.k||'.'||co.conname,md5(co.contype::text||'|'||pg_get_constraintdef(co.oid)||'|'||co.convalidated)
  from pg_constraint co join rel r on r.oid=co.conrelid
  union all
  select 'index',n.nspname||'.'||ic.relname,md5(pg_get_indexdef(i.indexrelid))
  from pg_index i join pg_class ic on ic.oid=i.indexrelid join nsp n on n.oid=ic.relnamespace
  where not exists(select 1 from ext e where e.classid='pg_class'::regclass and e.objid=i.indrelid)
  union all
  select 'trigger',tn.nspname||'.'||c.relname||'.'||t.tgname,md5(pg_get_triggerdef(t.oid)||'|'||t.tgenabled::text)
  from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace tn on tn.oid=c.relnamespace
  join pg_proc p on p.oid=t.tgfoid join pg_namespace fn on fn.oid=p.pronamespace
  where not t.tgisinternal and (tn.nspname in ('erp','public') or fn.nspname in ('erp','public'))
    and not exists(select 1 from ext e where e.classid='pg_class'::regclass and e.objid=c.oid)
  union all
  select 'policy',r.k||'.'||p.polname,md5(p.polcmd::text||'|'||p.polpermissive||'|'||coalesce((
      select string_agg(v,',' order by v) from (select case x when 0 then 'PUBLIC' else pg_get_userbyid(x)::text end v
      from unnest(p.polroles) x) z),'')||'|'||coalesce(pg_get_expr(p.polqual,p.polrelid),'')
    ||'|'||coalesce(pg_get_expr(p.polwithcheck,p.polrelid),''))
  from pg_policy p join rel r on r.oid=p.polrelid
  union all
  select 'type',n.nspname||'.'||t.typname,md5(t.typtype::text||'|'||coalesce(format_type(t.typbasetype,t.typtypmod),'')
    ||'|'||coalesce((select string_agg(e.enumlabel,',' order by e.enumsortorder) from pg_enum e where e.enumtypid=t.oid),'')
    ||'|'||coalesce((select string_agg(pg_get_constraintdef(c.oid),',' order by c.conname) from pg_constraint c where c.contypid=t.oid),''))
  from pg_type t join nsp n on n.oid=t.typnamespace
  where t.typtype in ('e','d','c','r','m') and (t.typtype<>'c' or (select relkind from pg_class where oid=t.typrelid)='c')
    and not exists(select 1 from ext e where e.classid='pg_type'::regclass and e.objid=t.oid)
  union all
  select 'schema',n.nspname,md5(pg_get_userbyid(s.nspowner)||'|'||coalesce((
    select string_agg(v,',' order by v) from (select case a.grantee when 0 then 'PUBLIC' else pg_get_userbyid(a.grantee)::text end
      ||':'||a.privilege_type||':'||a.is_grantable v
    from aclexplode(coalesce(s.nspacl,acldefault('n',s.nspowner))) a) z),''))
  from nsp n join pg_namespace s on s.oid=n.oid
  union all
  select 'default_acl',pg_get_userbyid(d.defaclrole)||'.'||coalesce(n.nspname,'*')||'.'||d.defaclobjtype::text,
    md5(coalesce((select string_agg(v,',' order by v) from (select case a.grantee when 0 then 'PUBLIC' else pg_get_userbyid(a.grantee)::text end
      ||':'||a.privilege_type||':'||a.is_grantable v from aclexplode(d.defaclacl) a) z),''))
  from pg_default_acl d left join pg_namespace n on n.oid=d.defaclnamespace
  where d.defaclnamespace=0 or n.nspname in ('erp','public')
  union all
  select 'extension',x.extname,md5(x.extversion||'|'||xn.nspname)
  from pg_extension x join pg_namespace xn on xn.oid=x.extnamespace
  union all
  select 'app_ledger',m.version::text,md5(m.description) from erp.schema_migrations m
  union all
  select 'platform_ledger',lpad(row_number() over (order by m.version)::text,3,'0')||' '||m.version||' '||coalesce(m.name,''),
    md5(coalesce(array_length(m.statements,1),0)||'|'||coalesce(array_to_string(m.statements,chr(10)),''))
  from supabase_migrations.schema_migrations m
  union all
  select 'config_hash','erp.'||t.name,t.h from (
    select 'app_roles' name,(select count(*)||':'||md5(coalesce(string_agg(j::text,'|' order by j::text),'')) from (select to_jsonb(x)-'{id,created_at,updated_at,created_by,updated_by}'::text[] j from erp.app_roles x) z) h
    union all select 'app_permissions',(select count(*)||':'||md5(coalesce(string_agg(j::text,'|' order by j::text),'')) from (select to_jsonb(x)-'{id,created_at,updated_at,created_by,updated_by}'::text[] j from erp.app_permissions x) z)
    union all select 'app_role_permissions',(select count(*)||':'||md5(coalesce(string_agg(j::text,'|' order by j::text),'')) from (select to_jsonb(x)-'{id,created_at,updated_at,created_by,updated_by}'::text[] j from erp.app_role_permissions x) z)
    union all select 'chart_accounts',(select count(*)||':'||md5(coalesce(string_agg(j::text,'|' order by j::text),'')) from (select to_jsonb(x)-'{id,created_at,updated_at,created_by,updated_by}'::text[] j from erp.chart_accounts x) z)
    union all select 'accounting_account_mappings',(select count(*)||':'||md5(coalesce(string_agg(j::text,'|' order by j::text),'')) from (select to_jsonb(x)-'{id,created_at,updated_at,created_by,updated_by}'::text[] j from erp.accounting_account_mappings x) z)
    union all select 'uom_definitions',(select count(*)||':'||md5(coalesce(string_agg(j::text,'|' order by j::text),'')) from (select to_jsonb(x)-'{id,created_at,updated_at,created_by,updated_by}'::text[] j from erp.uom_definitions x) z)
  ) t
)
select jsonb_object_agg(kind,jsonb_build_object('n',n,'md5',h) order by kind) as fingerprint
from (select kind,count(*) n,md5(string_agg(k||'='||h,chr(10) order by k)) h from o group by kind) s
