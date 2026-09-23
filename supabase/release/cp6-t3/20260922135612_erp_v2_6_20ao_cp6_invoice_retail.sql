-- CP6 AO: source-bound permanent package. Closed, drained maintenance required.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';set local search_path='';
set local role postgres;
do $closed_admission$
begin
 if session_user not in('postgres','supabase_admin')
  or (select datallowconn from pg_database where datname=current_database())
  or exists(select 1 from pg_stat_activity where datname=current_database() and pid<>pg_backend_pid()) then
  raise exception 'PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE';
 end if;
end $closed_admission$;
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;
do $lock_business$
declare n text;
begin
 for n in select c.relname from pg_class c join pg_namespace s on s.oid=c.relnamespace where s.nspname='erp' and c.relkind in('r','p') order by 1 loop
  execute format('lock table erp.%I in share row exclusive mode',n);
 end loop;
end $lock_business$;
do $predecessor$
begin
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20an')
  or exists(select 1 from erp.schema_migrations where version='v2.6.20ao') or to_regclass('erp.cp6_v2620ao_rollback_capsule') is not null
  or (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20an_cp6_cutting_selectors')<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version='20260921223438' and name='erp_v2_6_20an_cp6_cutting_selectors'
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='4df51d65fdb9a644fe2eeba92af23446e0c0389a1ebf9f336a0a396c144d7b71')
  or exists(select 1 from supabase_migrations.schema_migrations where version>'20260921223438') then raise exception 'AO_EXACT_PREDECESSOR_REQUIRED';end if;
end $predecessor$;
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule')
), objects as (
 select 'FUNCTION:'||format('%I.%I(%s)',n.nspname,p.proname,replace(oidvectortypes(p.proargtypes),', ',',')) k,
 jsonb_build_array(pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl)a order by a::text) end) v
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p')
 union all
 select 'RELATION:'||format('%I.%I',nspname,relname),jsonb_build_array(relkind,pg_get_userbyid(relowner),
  case when relacl is null then null else array(select a::text from unnest(relacl)a order by a::text) end,
  relrowsecurity,relforcerowsecurity,relreplident,relpersistence,relispartition,reloptions)
 from relations
 union all
 select 'COLUMN:'||format('%I.%I.%I',r.nspname,r.relname,a.attname),
 jsonb_build_array((select count(*) from pg_attribute visible where visible.attrelid=a.attrelid and visible.attnum>0 and not visible.attisdropped and visible.attnum<=a.attnum),format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,
  pg_get_expr(d.adbin,d.adrelid),a.attcollation::regcollation::text,
  case when a.attacl is null then null else array(select x::text from unnest(a.attacl)x order by x::text) end)
 from relations r join pg_attribute a on a.attrelid=r.oid and a.attnum>0 and not a.attisdropped
 left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum
 union all
 select 'CONSTRAINT:'||format('%I.%I.%I',r.nspname,r.relname,c.conname),
 jsonb_build_array(c.contype,pg_get_constraintdef(c.oid),c.condeferrable,c.condeferred,c.convalidated,c.conislocal,c.connoinherit)
 from relations r join pg_constraint c on c.conrelid=r.oid
 union all
 select 'INDEX:'||format('%I.%I',r.nspname,c.relname),
 jsonb_build_array(pg_get_indexdef(i.indexrelid),i.indisunique,i.indisprimary,i.indisexclusion,i.indisvalid,i.indisready,i.indisclustered,i.indisreplident,c.reloptions)
 from relations r join pg_index i on i.indrelid=r.oid join pg_class c on c.oid=i.indexrelid
 union all
 select 'TRIGGER:'||format('%I.%I.%I',r.nspname,r.relname,t.tgname),jsonb_build_array(pg_get_triggerdef(t.oid),t.tgenabled)
 from relations r join pg_trigger t on t.tgrelid=r.oid and not t.tgisinternal
 union all
 select 'POLICY:'||format('%I.%I.%I',r.nspname,r.relname,p.polname),jsonb_build_array(p.polcmd,p.polpermissive,
  array(select case when x=0 then 'PUBLIC' else pg_get_userbyid(x) end from unnest(p.polroles)x order by 1),
  pg_get_expr(p.polqual,p.polrelid),pg_get_expr(p.polwithcheck,p.polrelid))
 from relations r join pg_policy p on p.polrelid=r.oid
 union all
 select 'VIEW:'||format('%I.%I',nspname,relname),to_jsonb(pg_get_viewdef(oid,false)) from relations where relkind in('v','m')
 union all
 select 'SEQUENCE:'||format('%I.%I',r.nspname,r.relname),jsonb_build_array(format_type(s.seqtypid,null),s.seqstart,s.seqincrement,s.seqmax,s.seqmin,s.seqcache,s.seqcycle)
 from relations r join pg_sequence s on s.seqrelid=r.oid
 union all
 select 'SCHEMA:'||nspname,jsonb_build_array(pg_get_userbyid(nspowner),
  case when nspacl is null then null else array(select a::text from unnest(nspacl)a order by a::text) end)
 from pg_namespace where nspname in('erp','public')
 union all
 select 'DEFAULT_ACL:'||pg_get_userbyid(d.defaclrole)||':'||coalesce(n.nspname,'GLOBAL')||':'||d.defaclobjtype::text,
 to_jsonb(array(select a::text from unnest(d.defaclacl)a order by a::text))
 from pg_default_acl d left join pg_namespace n on n.oid=d.defaclnamespace
 where n.nspname in('erp','public') or d.defaclnamespace=0
 union all
 select 'ENUM:'||format('%I.%I',n.nspname,t.typname),jsonb_build_array(pg_get_userbyid(t.typowner),
  (select jsonb_agg(e.enumlabel order by e.enumsortorder) from pg_enum e where e.enumtypid=t.oid))
 from pg_type t join pg_namespace n on n.oid=t.typnamespace where n.nspname in('erp','public') and t.typtype='e'
)
select coalesce(jsonb_object_agg(k,encode(extensions.digest(convert_to(v::text,'UTF8'),'sha256'),'hex')),'{}'::jsonb) from objects
) catalog;
 select count(*),encode(extensions.digest(convert_to(coalesce(string_agg(length(key)::text||':'||key||':'||value,E'\n' order by key collate "C"),''),'UTF8'),'sha256'),'hex') into object_count,fingerprint from jsonb_each_text(actual);
 if object_count<>6628 or fingerprint is distinct from 'de36bdd5b6a1b2d2e5d21214fc722cfbba6e6489b3af8adfde29ac8d58d7f9e9' then
  raise exception 'AO_PREDECESSOR_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
do $historical_capsules$
declare r record;actual text;
begin
 for r in select * from jsonb_each_text('{"bs_resolution_v2619_rollback_capsule":"28ab388833da7da87384766ecaedadc66b4d048c303ee91e16f3939e34afdc39","bs_resolution_v2619a_rollback_capsule":"de8dfaab7b63b8742d383a089cdb05e73b629aad9f4df149e6a3c9fb590ef560","bs_resolution_v2619b_rollback_capsule":"d6d4f7457743d51679b5d25bf166ed69ca4b4f098cf5902ff985937531c2505d","bs_resolution_v2619c_rollback_capsule":"0207ba4f2ffba8ed61584709bbd884f1d2ee1a5981194fd7189a45afe8b3cbe1","cp3_r4_rollback_capsule":"7c01add62e66a4e2774a7199c2e77a04cca5e5942dbbba54d22cef720f82bc1d","cp45_v2617_rollback_capsule":"b9a43ce463de9905e94dd6538fd2a4952b0586a78c145f6f9d88aab7d6da3d80","cp45_v2617a_rollback_capsule":"b065dbcfdf1b59cb799e9f58caf6dd5ca7686e9f70826fce6a1ba8f140610022","cp4_v2616_rollback_capsule":"dde0a005dbe7cc93709bdfc6b961f4b9a76bf4db06fd7177d21dc79048af4d2f","cp6_v2620_rollback_capsule":"01f1e4e23211cff3c399d2d768a41be57980bfab00790715aa759b00a515e032","cp6_v2620a_rollback_capsule":"67befaaf327d2591e1ca1d654132ee483eba39b6cbb4f891c4719d817155d448","cp6_v2620aa_rollback_capsule":"eb0d6fb4fcac2ac06929d577101e604428e9a04821813c342e5b831147dc8948","cp6_v2620ab_rollback_capsule":"3be9a9166e3a607962be819fbe23d38fe455290a7a970dc2aad068079bf30785","cp6_v2620ac_relation_rollback_capsule":"63c595c956e25135e1e032613831f5a08a734ba1f5c4746c46483c84517ad5ea","cp6_v2620ac_rollback_capsule":"51a8b08c9d96e66f03c2c8ba94ed3ed8fb15b26d1a2e4c65c58c614442dfa969","cp6_v2620ad_rollback_capsule":"5c3588109395b32ed743e0f4f5d789a3c59e3fffbab7469138f1f423c877ea9d","cp6_v2620ae_rollback_capsule":"6a75e02bf7b90c542fd9f2ac9534a2de066b047f5ffea65bffb1f83fa63c17f0","cp6_v2620af_rollback_capsule":"bfa89fc0e94d34b29405acedf551935f024942835f31cdc98f0f0983a9550288","cp6_v2620ag_rollback_capsule":"7ddfe6181f0c1c7439faf8a8150c542e958b3bafd8d18b5b2d1eb454fd7a85b7","cp6_v2620ah_rollback_capsule":"361be9321e5f4dadc7c7ec0e99ed746a98e7a4150178fc8355d23707c1507a93","cp6_v2620ai_rollback_capsule":"f2428dd712aa763b1379a4ae5b1a1e1e6ee175b355d8769b854a28f1355181c8","cp6_v2620aj_rollback_capsule":"8e24026dc90a2a92292c2cc6c8faa5fc3de991a19f326db494e0af2a518436f1","cp6_v2620ak_rollback_capsule":"dc7bfce7b9ee6a42e33cdf03cabd99d64435a4615245b2037fd6e4ee399aef10","cp6_v2620al_rollback_capsule":"c9e9aca042674efa5c6fa283e4b9ee47f3353ee9ee95b34e14ef1fd6b09bfde9","cp6_v2620am_rollback_capsule":"e781e631d06c6894c20b1fe6f9c65779f461d19c405c8ae74f28ed7d83ae6a26","cp6_v2620an_rollback_capsule":"ebfa8a281a32fe54babbdc209264ab422fde27f344d48561b90d2af022fe75b3","cp6_v2620b_rollback_capsule":"f9bf784bff0c54e647f491e257a9649fd0c3e6f10c39ddfc0944c961b9dd7601","cp6_v2620c_rollback_capsule":"f88b1f5890ee8e7041758971bf9c9a3ce2bd0a7be6989fb95332c2dd7fa139aa","cp6_v2620d_rollback_capsule":"fa300c5554da4bb6812c61d726fd64f66329c97b085fa7d6ad5d0d8e5ae31235","cp6_v2620e_rollback_capsule":"143cd291cf4c12e78ab61e74e02ed03b08a48832a5064671868ff2bd2e3e1da7","cp6_v2620f_rollback_capsule":"076133b098e821fc2713af559618adf8aa3e204908f810af440fda355fc7a57f","cp6_v2620g_rollback_capsule":"ed9f4cacb47bd026ad6bdea373d1aa87044ed12aa60323cea453e3187dc488c4","cp6_v2620h_rollback_capsule":"4c25a060a2df3c22cd6fa9ff0b297163e223118a0d930b97bf1282b4756d909d","cp6_v2620i_rollback_capsule":"051203d95c44968abd8594f5bd48e289c4ac9a6c9fa49a89eee1086ad6b2c166","cp6_v2620j_rollback_capsule":"1393a8085d0f58717b13048c9cc3f7e9969ac86c351d6dfefdd2d4f43a735bd2","cp6_v2620k_rollback_capsule":"55aa71061f616ea11b361f0fabee2fd892f6438cc3f567cb9c135552ade42409","cp6_v2620l_rollback_capsule":"b4278768fce4ef307795953c14f607278c43bf474d76d3362e477280be08eb39","cp6_v2620m_rollback_capsule":"4b5f89d7bc4557f92b47716fe15640ab244c424fc1279433eb806d9d91d234e9","cp6_v2620n_rollback_capsule":"46e5ea4524613bb7a386551ada9e06888ea35eb987f9f5b864457fdd18bc3bc1","cp6_v2620o_rollback_capsule":"044e6b1a050df7e2a1d36082b0451877bda01116c08f611dfceb7a666bdf03c8","cp6_v2620p_rollback_capsule":"b656abaf23276984567c6c8d87b311427463c008b5ecd762fbdd0c2df13795df","cp6_v2620q_rollback_capsule":"ab6c992fbaa87f19a4eba696a57a3972f98504a354d9b5fc3be660939f8ea20f","cp6_v2620r_rollback_capsule":"8eb5e0a38284c5f8e3fee56618893ba72feaae9d26605c9ca3874dae25045297","cp6_v2620s_rollback_capsule":"fb57810a75f8829a038ed61b3a1cabde33dccf1e384661bc6723c51e28b3e132","cp6_v2620t_rollback_capsule":"348db4650d788750da243500b49e23c1130fdb70bc4a6d1fdf136bf68aa21f30","cp6_v2620u_rollback_capsule":"720eb1984548a3c381387fbe4d34e3c6f00334c8a4549eab7e398b827dcb7dd4","cp6_v2620v_rollback_capsule":"573ef5842eefadf1c32469514f4c8498667c99aec20ef20651406e4f419f5f60","cp6_v2620w_rollback_capsule":"f4e2ca1d577dd9f2724cc90693e8ee8bff36365c696575b69c6463f3e8ca0324","cp6_v2620x_rollback_capsule":"064db1068b56daa69e409ae582cd8a99490cea75d269154baa4217f90d3ca0d1","cp6_v2620y_rollback_capsule":"e3b23429a7f002c85ca8de1f8c632df13a4a2fc4e4654c12e2431c212772841d","cp6_v2620z_rollback_capsule":"ad0436a1480af43070e9861cb7e28d4cf55c435edbffb5fe368ca7babb7863ef","cutting_bridge_v2618_rollback_capsule":"535d1abd25668bc5bee79d82a602afe5efe4e8ce313bf1fb5170ae2004e3cb2d","cutting_bridge_v2618a_rollback_capsule":"db0608e690b3d936fa20b62cc4cfb9b1f9e86718212526eb6131562578b8bf60"}'::jsonb) loop
  execute format($caps$select encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to((to_jsonb(t)-array['captured_at','boundary_snapshot'])::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$caps$,r.key) into actual;
  if actual is distinct from r.value then raise exception 'AO_HISTORICAL_CAPSULE_DRIFT: %',r.key;end if;
 end loop;
end $historical_capsules$;
create table erp.cp6_v2620ao_rollback_capsule(like erp.cp6_v2620an_rollback_capsule including all);
alter table erp.cp6_v2620ao_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620ao_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620ao_rollback_capsule(object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
 format('%I.%I(%s)',n.nspname,p.proname,replace(oidvectortypes(p.proargtypes),', ',',')),pg_get_functiondef(p.oid),
 encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
 array(select a::text from unnest(p.proacl)a order by a::text),pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.oid in('erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)'::regprocedure,'erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)'::regprocedure,'erp.normalize_contractor_issue_item_uom_price()'::regprocedure,'erp.post_material_purchase_cost_correction(uuid)'::regprocedure,'erp.post_material_supplier_invoice(uuid)'::regprocedure,'erp.reverse_material_purchase_cost_correction(uuid,text)'::regprocedure,'erp.reverse_material_supplier_invoice(uuid,text)'::regprocedure,'erp.save_contractor_material_issue_draft_v2(jsonb,uuid,bigint)'::regprocedure,'erp.sync_material_cost_revaluation(uuid)'::regprocedure,'erp.sync_po_hpp_to_gl(uuid,date)'::regprocedure);
do $before_data$
declare v_table text;v_hash jsonb;v_before jsonb;
begin
 v_before:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620ao_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_before:=v_before||jsonb_build_object(v_table,v_hash);
 end loop;

 update erp.cp6_v2620ao_rollback_capsule set boundary_snapshot=jsonb_build_object('before',v_before,'platform_before',(select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations t where not(false)),'markers_before',(select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from erp.schema_migrations t where not(false)));
end $before_data$;

create table erp.invoice_recost_execution_context(
 transaction_id bigint primary key,invoice_date date not null,source_id uuid not null
);
alter table erp.invoice_recost_execution_context enable row level security;
revoke all on erp.invoice_recost_execution_context from public,anon,authenticated,service_role;
alter table erp.contractor_material_issue_items add column manual_retail_unit_price numeric;

CREATE OR REPLACE FUNCTION erp.invoice_recost_economic_date_v1()
RETURNS date LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' AS $function$
 select invoice_date from erp.invoice_recost_execution_context where transaction_id=txid_current();
$function$;
revoke all on function erp.invoice_recost_economic_date_v1() from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp._cp6_sync_material_adjustment_revaluation(p_adjustment uuid, p_material uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'pg_catalog', 'pg_temp'
AS $function$
declare s jsonb;v_delta jsonb;v_lines jsonb;v_event uuid;v_journal uuid;v_date date;
begin
 perform erp.require_internal();
 if not exists(select 1 from erp.material_adjustment_items where adjustment_id=p_adjustment and material_id=p_material) then
  raise exception 'T_MATERIAL_ADJUSTMENT_SOURCE_MISMATCH';
 end if;
 -- The material writer already owns its material/movement locks. Serialize the
 -- shared document without taking another material or document-row lock.
 perform pg_advisory_xact_lock(hashtextextended('MATERIAL_ADJUSTMENT_REVALUE|'||p_adjustment::text,0));
 s:=erp._cp6_material_adjustment_revaluation_state(p_adjustment);
 if (s->>'incomplete_cost')::bigint>0 then
  if exists(select 1 from erp.material_adjustments where id=p_adjustment and status in('POSTED','REVERSED')) then
   raise exception 'T_MATERIAL_ADJUSTMENT_COST_SNAPSHOT_MISSING';
  end if;
  return;
 end if;
 select coalesce(jsonb_object_agg(k,amount),'{}'::jsonb) into v_delta from(
  select coalesce(t.key,b.key) k,coalesce(t.value::numeric,0)-coalesce(b.value::numeric,0) amount
  from jsonb_each_text(s->'target') t full join jsonb_each_text(s->'book') b using(key)
 ) d where amount<>0;
 if v_delta='{}'::jsonb then return;end if;
 select jsonb_agg(jsonb_build_object('account_id',key::uuid,
  'debit',greatest(value::numeric,0),'credit',greatest(-value::numeric,0)) order by key)
 into v_lines from jsonb_each_text(v_delta);
 v_event:=gen_random_uuid();v_date:=coalesce(erp.invoice_recost_economic_date_v1(),erp._cp3_business_date(statement_timestamp()));
 v_journal:=erp.post_journal('MATERIAL_ADJUSTMENT_REVALUATION',v_event,v_date,
  'Document cumulative material adjustment recost: '||p_adjustment::text,v_lines);
 insert into erp.material_adjustment_revaluation_facts(
  id,adjustment_id,triggering_material_id,effective_date,prior_ledger,target_ledger,ledger_delta,journal_entry_id
 ) values(v_event,p_adjustment,p_material,v_date,s->'book',s->'target',v_delta,v_journal);
 if erp._cp6_supplier_cent_ledger(array[v_journal]) is distinct from v_delta
    or erp._cp6_material_adjustment_revaluation_state(p_adjustment)->'book' is distinct from s->'target' then
  raise exception 'T_MATERIAL_ADJUSTMENT_REVALUATION_POSTCONDITION';
 end if;
end
$function$;
CREATE OR REPLACE FUNCTION erp._recalculate_material_cost_core(p_material_id uuid, p_recalc_from timestamp with time zone, p_allow_checkpoint boolean)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  r erp.material_stock_movements%rowtype;
  rr record;
  v_stock numeric(18,6):=0;
  v_avg numeric(18,6):=0;
  v_stock_before numeric(18,6);
  v_avg_before numeric(18,6);
  v_cost numeric(18,6);
  v_new_stock numeric(18,6);
  v_new_avg numeric(18,6);
  v_closed date;
  v_cp erp.material_cost_checkpoints%rowtype;
  v_use_checkpoint boolean:=false;
  v_cutoff timestamptz;
  v_transfer_pairs jsonb;
  v_transfer_rows bigint;
  v_transfer_pair_count bigint;
  v_location_minimum numeric;
  v_invoice_date date;
  v_queue record;
begin
  perform erp.require_internal();
  select closed_through into v_closed from erp.accounting_period_control where singleton_id=1 for share;
  perform 1 from erp.materials where id=p_material_id for update;
  if not found then raise exception 'Material not found'; end if;

  with active as (
    select m.*,row_number() over(partition by m.source_id,m.roll_id,m.physical_at,
        abs(m.qty_signed),m.movement_type order by m.system_created_at,m.id) ordinal
    from erp.material_stock_movements m
    where m.material_id=p_material_id and m.source_type='MATERIAL_TRANSFER'
      and m.reversal_of_id is null
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
  ), pairs as (
    select i.id incoming,o.id outgoing
    from active i join active o on o.source_id=i.source_id
      and o.roll_id is not distinct from i.roll_id and o.physical_at=i.physical_at
      and o.qty_signed=-i.qty_signed and o.ordinal=i.ordinal
      and o.movement_type='TRANSFER_OUT' and o.qty_signed<0
    where i.movement_type='TRANSFER_IN' and i.qty_signed>0
      and (o.physical_at,o.system_created_at,o.id)<(i.physical_at,i.system_created_at,i.id)
      and o.location_id<>i.location_id
  )
  select coalesce((select jsonb_object_agg(incoming::text,outgoing::text) from pairs),'{}'::jsonb),
    (select count(*) from active),(select count(*) from pairs)
  into v_transfer_pairs,v_transfer_rows,v_transfer_pair_count;
  if v_transfer_rows<>2*v_transfer_pair_count then
    raise exception 'AM_TRANSFER_PAIR_LINEAGE_UNPROVEN for material %',p_material_id;
  end if;

  -- The cost engine excludes a source and its linked inverse together. Apply
  -- the identical effective-history rule at each physical location/roll too;
  -- this preserves atomic receipt replacement and existing cancellation rules.
  select min(prefix) into v_location_minimum from (
    select sum(m.qty_signed) over(partition by m.location_id,m.roll_id
      order by m.physical_at,coalesce(o.system_created_at,m.system_created_at),
        coalesce(o.id,m.id),(o.id is not null) rows unbounded preceding) prefix
    from erp.material_stock_movements m
    left join erp.material_stock_movements o on o.id=(v_transfer_pairs->>m.id::text)::uuid
    where m.material_id=p_material_id and m.reversal_of_id is null
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
  ) effective_history;
  if v_location_minimum<0 then
    raise exception 'AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY for material %',p_material_id;
  end if;

  if p_allow_checkpoint and p_recalc_from is not null and v_closed is not null then
    select * into v_cp from erp.material_cost_checkpoints where material_id=p_material_id;
    if v_cp.material_id is not null
       and v_cp.checkpoint_date<=v_closed
       and erp._cp3_business_date(p_recalc_from)>v_cp.checkpoint_date then
      v_cutoff:=((v_cp.checkpoint_date+1)::timestamp at time zone 'Asia/Jakarta');

  if exists(
    with history as (
      select msm.id,msm.qty_signed,msm.unit_cost_snapshot,msm.movement_type,msm.source_type,
        h.movement_id,h.stock_before,h.stock_after,h.average_before,h.average_after,
        h.movement_qty,h.movement_unit_cost,paired_out.unit_cost_snapshot paired_cost,
        sum(msm.qty_signed) over w expected_stock,
        lag(h.average_after,1,0::numeric) over w previous_average
      from erp.material_stock_movements msm
      left join erp.material_cost_history h on h.movement_id=msm.id and h.material_id=msm.material_id
      left join erp.material_stock_movements paired_out on paired_out.id=(v_transfer_pairs->>msm.id::text)::uuid
      where msm.material_id=p_material_id and msm.physical_at<v_cutoff
        and msm.reversal_of_id is null
        and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id)
      window w as(order by msm.physical_at,coalesce(paired_out.system_created_at,msm.system_created_at),
        coalesce(paired_out.id,msm.id),(paired_out.id is not null) rows unbounded preceding)
    )
    select 1 from history where movement_id is null
      or movement_qty is distinct from qty_signed
      or movement_unit_cost is distinct from unit_cost_snapshot
      or stock_before is distinct from expected_stock-qty_signed
      or stock_after is distinct from expected_stock
      or average_before is distinct from previous_average
      or (qty_signed<0 and movement_unit_cost is distinct from average_before)
      or (movement_type='TRANSFER_IN' and source_type='MATERIAL_TRANSFER'
          and movement_unit_cost is distinct from paired_cost)
      or average_after is distinct from case
        when stock_after=0 then 0
        when qty_signed<0 then average_before
        else round((stock_before*average_before+qty_signed*movement_unit_cost)/nullif(stock_after,0),6)
      end
  ) then
    raise exception 'AM_LEGACY_COST_CHECKPOINT_REQUIRES_HISTORY_REVIEW for material %',p_material_id;
  end if;

      v_use_checkpoint:=true;
      v_stock:=v_cp.stock_qty;
      v_avg:=v_cp.moving_average_cost;
    end if;
  end if;

  if v_use_checkpoint then
    if v_cp.last_movement_id is null then
      delete from erp.material_cost_history where material_id=p_material_id;
    else
      delete from erp.material_cost_history h
      using erp.material_stock_movements msm
      where h.material_id=p_material_id and h.movement_id=msm.id
        and erp._cp3_business_date(msm.physical_at)>v_cp.checkpoint_date;
    end if;
  else
    delete from erp.material_cost_history where material_id=p_material_id;
  end if;

  for r in
    select msm.* from erp.material_stock_movements msm
  left join erp.material_stock_movements paired_out
    on paired_out.id=(v_transfer_pairs->>msm.id::text)::uuid
    where msm.material_id=p_material_id
      and msm.reversal_of_id is null
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id)
      and (
        not v_use_checkpoint
        or v_cp.last_movement_id is null
        or erp._cp3_business_date(msm.physical_at)>v_cp.checkpoint_date
      )
    order by msm.physical_at,coalesce(paired_out.system_created_at,msm.system_created_at),
      coalesce(paired_out.id,msm.id),(paired_out.id is not null)
    for update of msm
  loop
    v_stock_before:=v_stock;
    v_avg_before:=v_avg;
    if r.qty_signed>0 then
      if r.movement_type='TRANSFER_IN' and r.source_type='MATERIAL_TRANSFER' then
        -- The paired OUT must already have been replayed (or retained by the
        -- closed-period checkpoint). Its historical cost is the incoming cost,
        -- including a transfer of the entire balance that temporarily hits 0.
        select o.unit_cost_snapshot into v_cost
        from erp.material_stock_movements o
        join erp.material_cost_history h on h.movement_id=o.id and h.material_id=o.material_id
        where o.id=(v_transfer_pairs->>r.id::text)::uuid and o.material_id=p_material_id
          and o.is_cost_recalculated;
        if not found or v_cost is null then
          raise exception 'AM_TRANSFER_OUT_COST_NOT_REPLAYED for movement %',r.id;
        end if;
      elsif r.movement_type='REVERSAL' and r.reversal_of_id is not null then
        select x.unit_cost_snapshot into v_cost from erp.material_stock_movements x where x.id=r.reversal_of_id;
        v_cost:=coalesce(v_cost,r.input_unit_cost,r.unit_cost_snapshot,v_avg);
      elsif r.movement_type='CUTTING_RETURN' and r.source_type='CUTTING_GROUP_RETURN' then
        select x.unit_cost_snapshot into v_cost
        from erp.material_stock_movements x
        where x.material_id=r.material_id
          and x.source_type='CUTTING_GROUP' and x.source_id=r.source_id
          and x.movement_type='CUTTING_ISSUE'
          and x.roll_id is not distinct from r.roll_id
        order by x.physical_at desc,x.system_created_at desc,x.id desc limit 1;
        v_cost:=coalesce(v_cost,r.input_unit_cost,r.unit_cost_snapshot,v_avg);
      else
        v_cost:=coalesce(r.input_unit_cost,r.unit_cost_snapshot,v_avg);
      end if;
      v_new_stock:=v_stock+r.qty_signed;
      if v_new_stock>0 then
        v_new_avg:=((v_stock*v_avg)+(r.qty_signed*v_cost))/v_new_stock;
      else
        v_new_avg:=0;
      end if;
    else
      v_new_stock:=v_stock+r.qty_signed;
      if v_new_stock<0 then
        raise exception 'Backdate/correction would create negative material stock for material %, movement %',p_material_id,r.id;
      end if;
      v_cost:=v_avg;
      v_new_avg:=case when v_new_stock=0 then 0 else v_avg end;
    end if;

    update erp.material_stock_movements
    set original_unit_cost_snapshot=coalesce(original_unit_cost_snapshot,v_cost),
        unit_cost_snapshot=v_cost,
        is_cost_recalculated=true
    where id=r.id;

    insert into erp.material_cost_history(material_id,movement_id,physical_at,stock_before,average_before,movement_qty,movement_unit_cost,stock_after,average_after)
    values(p_material_id,r.id,r.physical_at,v_stock_before,v_avg_before,r.qty_signed,v_cost,v_new_stock,v_new_avg);
    v_stock:=v_new_stock;
    v_avg:=v_new_avg;
  end loop;

  for rr in
    select mr.id as roll_id,coalesce(sum(msm.qty_signed),0)::numeric as roll_qty
    from erp.material_rolls mr
    left join erp.material_stock_movements msm on msm.roll_id=mr.id
    where mr.material_id=p_material_id
    group by mr.id
  loop
    if rr.roll_qty<0 then raise exception 'Correction would create negative roll stock for roll %',rr.roll_id; end if;
    update erp.material_rolls
    set cached_qty=rr.roll_qty,
        status=case when rr.roll_qty=0 then 'EXHAUSTED' when rr.roll_qty<original_qty then 'HALF_USED' else 'AVAILABLE' end,
        updated_at=statement_timestamp()
    where id=rr.roll_id and status<>'RETURNED_SUPPLIER';
  end loop;

  update erp.cutting_group_rolls cgr
  set unit_cost_snapshot=(
    select msm.unit_cost_snapshot
    from erp.material_stock_movements msm
    where msm.material_id=p_material_id and msm.source_type='CUTTING_GROUP'
      and msm.source_id=cgr.cutting_group_id and msm.movement_type='CUTTING_ISSUE'
      and msm.roll_id is not distinct from cgr.roll_id
    order by msm.physical_at desc,msm.system_created_at desc,msm.id desc limit 1
  )
  where exists(
    select 1 from erp.material_stock_movements msm
    where msm.material_id=p_material_id and msm.source_type='CUTTING_GROUP'
      and msm.source_id=cgr.cutting_group_id and msm.movement_type='CUTTING_ISSUE'
      and msm.roll_id is not distinct from cgr.roll_id
  );

  update erp.contractor_material_issue_items ii
  set unit_cost_snapshot=(
    select msm.unit_cost_snapshot from erp.material_stock_movements msm
    where msm.material_id=p_material_id and msm.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM'
      and msm.source_id=ii.id and msm.movement_type='CONTRACTOR_ISSUE'
    order by msm.physical_at desc,msm.system_created_at desc,msm.id desc limit 1
  )
  where ii.material_id=p_material_id and exists(
    select 1 from erp.material_stock_movements msm
    where msm.material_id=p_material_id and msm.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM'
      and msm.source_id=ii.id and msm.movement_type='CONTRACTOR_ISSUE'
  );

  update erp.materials set cached_stock_qty=v_stock,moving_average_cost=v_avg,updated_at=statement_timestamp() where id=p_material_id;

  perform erp.sync_material_cost_revaluation(p_material_id);

  insert into erp.cost_recalc_queue(entity_type,entity_id,recalc_from,reason)
  select distinct 'PO',cg.po_id,min(msm.physical_at),'Material moving-average/backdate recalculation'
  from erp.material_stock_movements msm
  join erp.cutting_groups cg on msm.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') and msm.source_id=cg.id
  where msm.material_id=p_material_id
    and exists(select 1 from erp.fg_lots fl where fl.po_id=cg.po_id)
    and not exists(select 1 from erp.cost_recalc_queue q where q.entity_type='PO' and q.entity_id=cg.po_id and (q.status in('PENDING','RUNNING') or (q.status='FAILED' and q.attempt_count<3)))
  group by cg.po_id;

  insert into erp.cost_recalc_queue(entity_type,entity_id,recalc_from,reason)
  select distinct 'PO',cmi.po_id,min(msm.physical_at),'Contractor material moving-average/backdate recalculation'
  from erp.material_stock_movements msm
  join erp.contractor_material_issue_items ii on msm.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and msm.source_id=ii.id
  join erp.contractor_material_issues cmi on cmi.id=ii.issue_id
  where msm.material_id=p_material_id and cmi.po_id is not null
    and exists(select 1 from erp.fg_lots fl where fl.po_id=cmi.po_id)
    and not exists(select 1 from erp.cost_recalc_queue q where q.entity_type='PO' and q.entity_id=cmi.po_id and (q.status in('PENDING','RUNNING') or (q.status='FAILED' and q.attempt_count<3)))
  group by cmi.po_id;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('materials',p_material_id,'RECALCULATE',jsonb_build_object('cached_stock_qty',v_stock,'moving_average_cost',v_avg,'original_movement_snapshots_preserved',true,'gl_revaluation_synced',true,'checkpoint_used',v_use_checkpoint,'recalc_from',p_recalc_from),erp.current_app_user_id(),'Material chronological moving-average recalculation');

  perform erp.refresh_accessory_hpp_after_material_recost(p_material_id,'Material chronological moving-average recalculation');

  v_invoice_date:=erp.invoice_recost_economic_date_v1();
  if v_invoice_date is not null then
    for v_queue in
      select q.* from erp.cost_recalc_queue q where q.entity_type='PO'
        and q.status in('PENDING','FAILED')
        and q.entity_id in(
          select cg.po_id from erp.cutting_groups cg join erp.material_stock_movements m
            on m.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') and m.source_id=cg.id where m.material_id=p_material_id
          union select i.po_id from erp.contractor_material_issues i join erp.contractor_material_issue_items l on l.issue_id=i.id
            where l.material_id=p_material_id and i.po_id is not null
        ) order by q.entity_id,q.queued_at,q.id for update
    loop
      perform erp.rebuild_po_hpp(v_queue.entity_id,v_queue.reason);
      perform erp.propagate_conversion_hpp_for_po(v_queue.entity_id);
      perform erp.sync_po_hpp_to_gl(v_queue.entity_id,v_invoice_date);
      if exists(select 1 from erp.production_orders where id=v_queue.entity_id and status='FINISHED') then
        perform erp.sync_finished_po_wip_residual(v_queue.entity_id,v_invoice_date,'Invoice-date material correction');
      end if;
      update erp.cost_recalc_queue set status='DONE',started_at=statement_timestamp(),completed_at=statement_timestamp(),
        last_attempt_at=statement_timestamp(),attempt_count=attempt_count+1,error_message=null,next_attempt_at=null where id=v_queue.id;
    end loop;
  end if;

  if not v_use_checkpoint and v_closed is not null then
    perform erp.refresh_material_cost_checkpoint(p_material_id,v_closed);
  end if;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.normalize_contractor_issue_item_uom_price()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_type varchar(20);
  v_base_uom varchar(20);
  v_category uuid;
  v_contractor uuid;
  v_at timestamptz;
  v_price record;
  v_factor numeric(18,6);
  v_dimension varchar(20);
begin
  select material_type,unit_code,accessory_category_id
    into v_type,v_base_uom,v_category
  from erp.materials where id=new.material_id;
  if v_type is null then raise exception 'Material not found'; end if;

  select contractor_id,physical_at into v_contractor,v_at
  from erp.contractor_material_issues where id=new.issue_id;
  if v_contractor is null or v_at is null then
    raise exception 'Contractor issue header must exist before adding lines';
  end if;

  if v_type='ACCESSORY' then
    if v_category is null then
      raise exception 'Accessory material % must be assigned to an accessory category before issue',new.material_id;
    end if;

    if new.manual_retail_unit_price is not null then
      if new.manual_retail_unit_price::text in('NaN','Infinity','-Infinity')
        or new.manual_retail_unit_price<0 or new.manual_retail_unit_price<>round(new.manual_retail_unit_price,2) then
        raise exception 'Harga eceran wajib nominal valid dengan paling banyak dua angka desimal'; end if;
      select u.dimension into v_dimension from erp.uom_definitions u where u.unit_code=v_base_uom;
      if v_dimension is distinct from 'COUNT' or new.qty is null or new.qty<=0
        or new.qty::text in('NaN','Infinity','-Infinity') or new.qty<>trunc(new.qty) then
        raise exception 'Eceran memerlukan jumlah fisik utuh dalam satuan dasar hitung'; end if;
      if new.transaction_qty is not null and new.transaction_qty<>new.qty then
        raise exception 'Jumlah eceran harus sama dengan jumlah fisik'; end if;
      new.transaction_qty:=new.qty;new.transaction_uom_code:=v_base_uom;new.base_qty_per_transaction_uom:=1;
      new.unit_sale_price_snapshot:=new.manual_retail_unit_price;
      new.accessory_price_version_id:=null;new.material_price_version_id:=null;
      return new;
    end if;

    perform pg_advisory_xact_lock(hashtextextended('CAPRICE:'||v_contractor::text||':'||v_category::text,0));
    select x.* into v_price
    from erp.contractor_accessory_price_versions x
    where x.category_id=v_category
      and x.contractor_id is not distinct from v_contractor
      and x.effective_from<=v_at
      and (x.effective_to is null or x.effective_to>v_at)
    order by x.effective_from desc limit 1;

    if v_price.id is null then
      perform pg_advisory_xact_lock(hashtextextended('CAPRICE:GLOBAL:'||v_category::text,0));
      select x.* into v_price
      from erp.contractor_accessory_price_versions x
      where x.category_id=v_category
        and x.contractor_id is null
        and x.effective_from<=v_at
        and (x.effective_to is null or x.effective_to>v_at)
      order by x.effective_from desc limit 1;
    end if;

    if v_price.id is null then
      raise exception 'No active mandor selling price for accessory category % at %',v_category,v_at;
    end if;

    v_factor:=erp.accessory_uom_factor(v_category,v_price.selling_uom_code,v_at);
    if new.transaction_qty is null then
      if new.qty is null then raise exception 'Accessory issue requires transaction quantity'; end if;
      if (new.qty/v_factor)::numeric(18,6)*v_factor<>new.qty then
        raise exception 'Jumlah PCS ini memerlukan harga eceran manual; pecahan lusin/gross tidak dibulatkan'; end if;
      new.transaction_qty:=new.qty/v_factor;
    end if;
    if new.transaction_qty<=0 then raise exception 'Transaction quantity must be positive'; end if;
    new.transaction_uom_code:=v_price.selling_uom_code;
    new.base_qty_per_transaction_uom:=v_factor;
    new.qty:=new.transaction_qty*v_factor;

    select u.dimension into v_dimension
    from erp.accessory_categories ac
    join erp.uom_definitions u on u.unit_code=ac.base_uom_code
    where ac.id=v_category;
    if v_dimension='COUNT' and abs(new.qty-round(new.qty))>0.000001 then
      raise exception 'Count-based accessory issue must convert to a whole base-unit quantity; calculated %',new.qty;
    end if;

    new.unit_sale_price_snapshot:=v_price.selling_price;
    new.accessory_price_version_id:=v_price.id;
    new.material_price_version_id:=null;
  else
    if new.manual_retail_unit_price is not null then raise exception 'Harga eceran manual hanya untuk aksesori hitung'; end if;
    if new.qty is null or new.qty<=0 then raise exception 'Issue base quantity must be positive'; end if;

    perform pg_advisory_xact_lock(hashtextextended('CMPRICE:'||v_contractor::text||':'||new.material_id::text,0));
    select x.* into v_price
    from erp.contractor_material_price_versions x
    where x.material_id=new.material_id
      and x.contractor_id is not distinct from v_contractor
      and x.effective_from<=v_at
      and (x.effective_to is null or x.effective_to>v_at)
    order by x.effective_from desc limit 1;

    if v_price.id is null then
      perform pg_advisory_xact_lock(hashtextextended('CMPRICE:GLOBAL:'||new.material_id::text,0));
      select x.* into v_price
      from erp.contractor_material_price_versions x
      where x.material_id=new.material_id
        and x.contractor_id is null
        and x.effective_from<=v_at
        and (x.effective_to is null or x.effective_to>v_at)
      order by x.effective_from desc limit 1;
    end if;

    if v_price.id is null then
      raise exception 'Harga jual material ke mandor belum diset untuk material % pada tanggal/jam %. Set harga material mandor dulu sebelum posting.',new.material_id,v_at;
    end if;

    new.transaction_qty:=coalesce(new.transaction_qty,new.qty);
    new.transaction_uom_code:=coalesce(new.transaction_uom_code,v_base_uom);
    new.base_qty_per_transaction_uom:=coalesce(new.base_qty_per_transaction_uom,1);
    if abs(new.qty-(new.transaction_qty*new.base_qty_per_transaction_uom))>0.000001 then
      raise exception 'Issue transaction UOM quantity does not reconcile to base quantity';
    end if;

    new.unit_sale_price_snapshot:=v_price.selling_price;
    new.material_price_version_id:=v_price.id;
    new.accessory_price_version_id:=null;
  end if;

  if new.unit_sale_price_snapshot is null or new.unit_sale_price_snapshot<0 then
    raise exception 'Issue selling price snapshot is required and cannot be negative';
  end if;
  return new;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.post_material_purchase_cost_correction(p_correction_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_n_before jsonb;v_n_purchases uuid[];
  h erp.material_purchase_cost_corrections%rowtype;
  p erp.material_purchase_headers%rowtype;
  m record;
  r record;
  v_delta_payable numeric(24,6);
  v_old_cost numeric(18,6);
  v_current_payable numeric(24,6);
  v_proposed_payable numeric(24,6);
  v_paid numeric(24,6);
  v_post_seq bigint;
begin
  perform erp.require_owner_admin();
  select * into h from erp.material_purchase_cost_corrections where id=p_correction_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Material purchase cost correction must be DRAFT'; end if;
  insert into erp.invoice_recost_execution_context(transaction_id,invoice_date,source_id) values(txid_current(),h.invoice_date,h.id);
  select * into p from erp.material_purchase_headers where id=h.purchase_id for update;
  if p.id is null or p.status<>'POSTED' then raise exception 'Source material purchase must be POSTED'; end if;
  v_n_purchases:=array[p.id];v_n_before:=erp._cp6_supplier_cent_state(v_n_purchases);
  if not exists(select 1 from erp.material_purchase_cost_correction_items where correction_id=h.id) then raise exception 'Cost correction has no lines'; end if;

  select coalesce(max(c.post_seq),0)+1 into v_post_seq
  from erp.material_purchase_cost_corrections c
  where c.purchase_id=p.id and c.post_seq is not null;

  select erp.material_purchase_payable_total(p.id) into v_current_payable;
  select coalesce(sum(mpi.qty*(ci.new_unit_price-erp.material_purchase_current_unit_cost(mpi.id))),0)
  into v_delta_payable
  from erp.material_purchase_cost_correction_items ci
  join erp.material_purchase_items mpi on mpi.id=ci.purchase_item_id
  where ci.correction_id=h.id;
  v_proposed_payable:=v_current_payable+v_delta_payable;
  select coalesce(sum(sp.amount),0) into v_paid from erp.supplier_payments sp where sp.purchase_id=p.id and sp.status='POSTED';
  if round(v_proposed_payable,2)<0 then raise exception 'Corrected purchase payable cannot become negative'; end if;
  if v_paid>round(v_proposed_payable,2) then raise exception 'Cost correction would make supplier payments exceed corrected payable. Use supplier credit/receivable correction flow'; end if;

  for m in
    select distinct mpi.material_id
    from erp.material_purchase_cost_correction_items ci join erp.material_purchase_items mpi on mpi.id=ci.purchase_item_id
    where ci.correction_id=h.id
  loop
    for r in
      select ci.id as correction_item_id,ci.purchase_item_id,ci.new_unit_price,mpi.qty,mpi.material_id
      from erp.material_purchase_cost_correction_items ci
      join erp.material_purchase_items mpi on mpi.id=ci.purchase_item_id
      where ci.correction_id=h.id and mpi.material_id=m.material_id
      order by ci.id
    loop
      v_old_cost:=erp.material_purchase_current_unit_cost(r.purchase_item_id);
      update erp.material_purchase_cost_correction_items
      set old_unit_cost_snapshot=v_old_cost,qty_basis=r.qty,delta_amount=r.qty*(r.new_unit_price-v_old_cost)
      where id=r.correction_item_id;
      update erp.material_stock_movements msm
      set input_unit_cost=r.new_unit_price
      where msm.movement_type='PURCHASE' and msm.qty_signed>0 and (
        (msm.source_type='MATERIAL_PURCHASE_ITEM' and msm.source_id=r.purchase_item_id)
        or (msm.source_type='MATERIAL_PURCHASE_ROLL' and msm.source_id in(select mr.id from erp.material_rolls mr where mr.purchase_item_id=r.purchase_item_id))
      );
      if not found then raise exception 'Original purchase stock movement not found for purchase item %',r.purchase_item_id; end if;
    end loop;

    perform erp.recalculate_material_cost(m.material_id,p.physical_at);

  end loop;

  update erp.material_purchase_cost_corrections
  set status='POSTED',posted_at=clock_timestamp(),post_seq=v_post_seq
  where id=h.id;
  select erp.material_purchase_payable_total(p.id) into v_proposed_payable;
  select coalesce(sum(sp.amount),0) into v_paid from erp.supplier_payments sp where sp.purchase_id=p.id and sp.status='POSTED';
  update erp.material_purchase_headers set payment_status=case when v_paid=round(v_proposed_payable,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end where id=p.id;
  perform erp._cp6_apply_supplier_cent_event('MATERIAL_PURCHASE_COST_CORRECTION',h.id,h.invoice_date,'Supplier document cents '||h.id::text,v_n_before,false);
  delete from erp.invoice_recost_execution_context where transaction_id=txid_current();
end;
$function$;
CREATE OR REPLACE FUNCTION erp.post_material_supplier_invoice(p_invoice_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_n_before jsonb;v_n_purchases uuid[];
  h erp.material_supplier_invoices%rowtype;
  r record;
  v_capacity numeric;
  v_matched numeric;
  v_old_cost numeric;
  v_new_cost numeric;
  v_basis_qty numeric;
  v_delta_before numeric;
  v_delta_after numeric;
  v_inventory_delta numeric;
  v_liability_delta numeric;
  v_bridge numeric;
  v_purchase uuid;
  v_paid numeric;
  v_payable numeric;
begin
  perform erp.require_owner_admin();
  select * into h from erp.material_supplier_invoices where id=p_invoice_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Material supplier invoice must be DRAFT'; end if;
  insert into erp.invoice_recost_execution_context(transaction_id,invoice_date,source_id) values(txid_current(),h.invoice_date,h.id);
  if h.invoice_date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date then raise exception 'Supplier invoice date cannot be in the future'; end if;
  if (h.received_at AT TIME ZONE 'Asia/Jakarta')::date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date then raise exception 'Supplier invoice received_at cannot be in the future'; end if;
  if not exists(select 1 from erp.material_supplier_invoice_lines where invoice_id=h.id) then
    raise exception 'Material supplier invoice has no lines';
  end if;

  -- Deterministic lock order protects concurrent invoice/payment/return clicks.
  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.purchase_id
  loop
    perform 1 from erp.material_purchase_headers where id=v_purchase for update;
  end loop;
  select array_agg(distinct i.purchase_id order by i.purchase_id) into v_n_purchases
  from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=h.id;
  perform 1 from erp.material_purchase_headers where id=any(v_n_purchases) order by id for update;
  v_n_before:=erp._cp6_supplier_cent_state(v_n_purchases);
  for r in
    select distinct i.id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.id
  loop
    perform 1 from erp.material_purchase_items where id=r.id for update;
  end loop;

  for r in
    select l.*,i.qty as receipt_qty,i.unit_price as estimate_unit_cost,
           i.material_id,i.purchase_id,i.invoice_match_state,
           ph.supplier_id,ph.physical_at
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    join erp.material_purchase_headers ph on ph.id=i.purchase_id
    where l.invoice_id=h.id order by i.id
  loop
    if r.supplier_id is distinct from h.supplier_id then
      raise exception 'Invoice supplier does not match receipt supplier for item %',r.purchase_item_id;
    end if;
    if r.invoice_match_state='DIRECT_FINAL' then
      raise exception 'Receipt item % was already final-invoiced at physical receipt',r.purchase_item_id;
    end if;
    v_capacity:=erp.material_purchase_invoice_capacity(r.purchase_item_id);
    v_matched:=erp.material_purchase_posted_invoice_qty(r.purchase_item_id);
    if v_matched+r.qty_invoiced>v_capacity then
      raise exception 'Invoice quantity exceeds unmatched receipt quantity for item %. Capacity %, already matched %, requested %',
        r.purchase_item_id,v_capacity,v_matched,r.qty_invoiced;
    end if;

    v_old_cost:=erp.material_purchase_current_unit_cost(r.purchase_item_id);
    v_basis_qty:=v_capacity;
    select coalesce(sum(x.net_amount-(x.qty_invoiced*r.estimate_unit_cost)),0)
    into v_delta_before
    from erp.material_supplier_invoice_lines x
    join erp.material_supplier_invoices xh on xh.id=x.invoice_id
    where x.purchase_item_id=r.purchase_item_id and xh.status='POSTED';
    v_delta_after:=v_delta_before+(r.net_amount-(r.qty_invoiced*r.estimate_unit_cost));
    v_new_cost:=greatest(((v_basis_qty*r.estimate_unit_cost)+v_delta_after)/v_basis_qty,0);
    v_inventory_delta:=r.receipt_qty*(v_new_cost-v_old_cost);
    v_liability_delta:=r.net_amount-(r.qty_invoiced*r.estimate_unit_cost);
    v_bridge:=v_inventory_delta-v_liability_delta;

    update erp.material_supplier_invoice_lines
    set receipt_estimate_unit_cost_snapshot=r.estimate_unit_cost,
        prior_blended_unit_cost_snapshot=v_old_cost,
        posted_blended_unit_cost_snapshot=v_new_cost,
        grni_clear_amount_snapshot=r.qty_invoiced*r.estimate_unit_cost,
        ap_create_amount_snapshot=r.net_amount,
        inventory_revaluation_snapshot=v_inventory_delta,
        bridge_variance_snapshot=v_bridge
    where id=r.id;

  end loop;

  update erp.material_supplier_invoices
  set status='POSTED',posted_at=clock_timestamp(),posting_reason=coalesce(posting_reason,'Supplier invoice posted')
  where id=h.id;

  for r in
    select distinct l.purchase_item_id
    from erp.material_supplier_invoice_lines l
    where l.invoice_id=h.id order by l.purchase_item_id
  loop
    perform erp.refresh_material_purchase_item_cost(r.purchase_item_id);
    perform erp.refresh_material_purchase_item_match_state(r.purchase_item_id);
  end loop;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.purchase_id
  loop
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0)
    into v_payable,v_paid;
    update erp.material_purchase_headers
    set supplier_invoice_number=h.invoice_number,
        due_date=coalesce(h.due_date,due_date),
        payment_status=case when v_paid=round(v_payable,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end
    where id=v_purchase;
  end loop;
  perform erp._cp6_apply_supplier_cent_event('MATERIAL_SUPPLIER_INVOICE',h.id,h.invoice_date,'Supplier document cents '||h.id::text,v_n_before,false);
  delete from erp.invoice_recost_execution_context where transaction_id=txid_current();
end;
$function$;
CREATE OR REPLACE FUNCTION erp.reverse_material_purchase_cost_correction(p_correction_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_n_before jsonb;v_n_purchases uuid[];
  h erp.material_purchase_cost_corrections%rowtype;
  p erp.material_purchase_headers%rowtype;
  r record;
  m uuid;
  v_journal uuid;
  v_current_payable numeric(24,6);
  v_delta numeric(24,6);
  v_projected numeric(24,6);
  v_paid numeric(24,6);
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal koreksi harga pembelian wajib diisi'; end if;
  select * into h from erp.material_purchase_cost_corrections where id=p_correction_id for update;
  if h.id is null then raise exception 'Koreksi harga pembelian tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya koreksi harga pembelian POSTED yang dapat direverse'; end if;
  insert into erp.invoice_recost_execution_context(transaction_id,invoice_date,source_id) values(txid_current(),erp._cp3_business_date(statement_timestamp()),h.id);
  if h.post_seq is null then raise exception 'Urutan posting koreksi harga pembelian tidak ditemukan; reversal dibatalkan'; end if;
  select * into p from erp.material_purchase_headers where id=h.purchase_id for update;
  if p.id is null or p.status<>'POSTED' then raise exception 'Pembelian sumber harus masih POSTED'; end if;
  v_n_purchases:=array[p.id];v_n_before:=erp._cp6_supplier_cent_state(v_n_purchases);

  if exists(
    select 1
    from erp.material_purchase_cost_correction_items ci
    join erp.material_purchase_cost_correction_items ci2 on ci2.purchase_item_id=ci.purchase_item_id
    join erp.material_purchase_cost_corrections c2 on c2.id=ci2.correction_id
    where ci.correction_id=h.id and c2.status='POSTED' and c2.id<>h.id
      and c2.post_seq>h.post_seq
  ) then
    raise exception 'Ada koreksi harga yang lebih baru pada item pembelian ini. Reverse koreksi terbaru terlebih dahulu.';
  end if;

  select erp.material_purchase_payable_total(p.id) into v_current_payable;
  select coalesce(sum(delta_amount),0) into v_delta
  from erp.material_purchase_cost_correction_items where correction_id=h.id;
  v_projected:=v_current_payable-v_delta;
  select coalesce(sum(amount),0) into v_paid from erp.supplier_payments where purchase_id=p.id and status='POSTED';
  if v_paid>round(v_projected,2) then
    raise exception 'Reversal koreksi harga membuat pembayaran supplier melebihi hutang tersisa. Reverse/koreksi pembayaran supplier terlebih dahulu.';
  end if;

  for r in
    select ci.*,mpi.material_id
    from erp.material_purchase_cost_correction_items ci
    join erp.material_purchase_items mpi on mpi.id=ci.purchase_item_id
    where ci.correction_id=h.id order by ci.id
  loop
    if r.old_unit_cost_snapshot is null then
      raise exception 'Snapshot harga sebelum koreksi tidak ditemukan untuk item %; reversal dibatalkan',r.purchase_item_id;
    end if;
    update erp.material_stock_movements msm
    set input_unit_cost=r.old_unit_cost_snapshot
    where msm.movement_type='PURCHASE' and msm.qty_signed>0 and (
      (msm.source_type='MATERIAL_PURCHASE_ITEM' and msm.source_id=r.purchase_item_id)
      or (msm.source_type='MATERIAL_PURCHASE_ROLL' and msm.source_id in (select mr.id from erp.material_rolls mr where mr.purchase_item_id=r.purchase_item_id))
    );
  end loop;

  update erp.material_purchase_cost_corrections set status='REVERSED' where id=h.id;
  for m in
    select distinct mpi.material_id from erp.material_purchase_cost_correction_items ci
    join erp.material_purchase_items mpi on mpi.id=ci.purchase_item_id where ci.correction_id=h.id
  loop
    perform erp.recalculate_material_cost(m,p.physical_at);
  end loop;

  select id into v_journal from erp.journal_entries
  where source_type='MATERIAL_PURCHASE_COST_CORRECTION' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if abs(v_delta)>0.005 and v_journal is null and not exists(select 1 from erp.supplier_cent_posting_facts where source_type='MATERIAL_PURCHASE_COST_CORRECTION' and source_id=h.id and phase='POST') then
    raise exception 'Jurnal koreksi harga pembelian tidak ditemukan; reversal dibatalkan agar inventory/AP tidak rusak';
  end if;


  select erp.material_purchase_payable_total(p.id) into v_projected;
  select coalesce(sum(amount),0) into v_paid from erp.supplier_payments where purchase_id=p.id and status='POSTED';
  update erp.material_purchase_headers set payment_status=case when v_paid=round(v_projected,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end where id=p.id;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('material_purchase_cost_corrections',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
  perform erp._cp6_apply_supplier_cent_event('MATERIAL_PURCHASE_COST_CORRECTION',h.id,erp._cp3_business_date(statement_timestamp()),p_reason,v_n_before,true);
  delete from erp.invoice_recost_execution_context where transaction_id=txid_current();
end;
$function$;
CREATE OR REPLACE FUNCTION erp.reverse_material_supplier_invoice(p_invoice_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_n_before jsonb;v_n_purchases uuid[];
  h erp.material_supplier_invoices%rowtype;
  r record;
  v_purchase uuid;
  v_current_ap numeric;
  v_invoice_ap numeric;
  v_paid numeric;
  v_journal uuid;
  v_latest record;
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_reason),'') is null then raise exception 'Supplier invoice reversal reason is required'; end if;
  select * into h from erp.material_supplier_invoices where id=p_invoice_id for update;
  if h.id is null then raise exception 'Material supplier invoice not found'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Only a POSTED supplier invoice may be reversed'; end if;
  insert into erp.invoice_recost_execution_context(transaction_id,invoice_date,source_id) values(txid_current(),erp._cp3_business_date(statement_timestamp()),h.id);

  select array_agg(distinct i.purchase_id order by i.purchase_id) into v_n_purchases
  from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=h.id;
  perform 1 from erp.material_purchase_headers where id=any(v_n_purchases) order by id for update;
  v_n_before:=erp._cp6_supplier_cent_state(v_n_purchases);
  if exists(
    select 1
    from erp.material_supplier_invoice_lines l
    join erp.material_supplier_return_items ri on ri.purchase_item_id=l.purchase_item_id
    join erp.material_supplier_returns rh on rh.id=ri.return_id
    where l.invoice_id=h.id and rh.status='POSTED'
      and coalesce(ri.ap_relief_qty_snapshot,0)>0
  ) then
    raise exception 'Reverse AP-backed supplier returns before reversing this invoice';
  end if;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.purchase_id
  loop
    perform 1 from erp.material_purchase_headers where id=v_purchase for update;
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce(sum(l.net_amount),0),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0)
    into v_current_ap,v_invoice_ap,v_paid
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id and i.purchase_id=v_purchase;
    if v_paid>round(v_current_ap-v_invoice_ap,2) then
      raise exception 'Reverse supplier payments first: payment % would exceed projected final AP %',
        v_paid,v_current_ap-v_invoice_ap;
    end if;
  end loop;

  select id into v_journal from erp.journal_entries
  where source_type='MATERIAL_SUPPLIER_INVOICE' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if exists(
    select 1 from erp.material_supplier_invoice_lines
    where invoice_id=h.id and(
      coalesce(grni_clear_amount_snapshot,0)<>0
      or coalesce(ap_create_amount_snapshot,0)<>0
      or coalesce(inventory_revaluation_snapshot,0)<>0
    )
  ) and v_journal is null and not exists(select 1 from erp.supplier_cent_posting_facts where source_type='MATERIAL_SUPPLIER_INVOICE' and source_id=h.id and phase='POST') then
    raise exception 'Supplier invoice journal is missing; reversal aborted to protect AP/GRNI/HPP';
  end if;

  update erp.material_supplier_invoices
  set status='REVERSED',reversed_at=clock_timestamp(),reversal_reason=btrim(p_reason)
  where id=h.id;


  for r in
    select distinct l.purchase_item_id
    from erp.material_supplier_invoice_lines l
    where l.invoice_id=h.id order by l.purchase_item_id
  loop
    perform erp.refresh_material_purchase_item_cost(r.purchase_item_id);
    perform erp.refresh_material_purchase_item_match_state(r.purchase_item_id);
  end loop;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.purchase_id
  loop
    select ih.invoice_number,ih.due_date into v_latest
    from erp.material_supplier_invoices ih
    join erp.material_supplier_invoice_lines il on il.invoice_id=ih.id
    join erp.material_purchase_items pi on pi.id=il.purchase_item_id
    where pi.purchase_id=v_purchase and ih.status='POSTED'
    order by ih.posted_at desc,ih.id desc limit 1;
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0)
    into v_current_ap,v_paid;
    update erp.material_purchase_headers
    set supplier_invoice_number=v_latest.invoice_number,
        due_date=v_latest.due_date,
        payment_status=case when v_paid=round(v_current_ap,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end
    where id=v_purchase;
  end loop;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('material_supplier_invoices',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
  perform erp._cp6_apply_supplier_cent_event('MATERIAL_SUPPLIER_INVOICE',h.id,erp._cp3_business_date(statement_timestamp()),p_reason,v_n_before,true);
  delete from erp.invoice_recost_execution_context where transaction_id=txid_current();
end;
$function$;
CREATE OR REPLACE FUNCTION erp.save_contractor_material_issue_draft_v2(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_id uuid:=nullif(p_payload->>'id','')::uuid;
  v_action text:=upper(coalesce(nullif(btrim(p_payload->>'action'),''),'SAVE'));
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  h erp.contractor_material_issues%rowtype;v_line jsonb;v_type text;v_roll uuid;v_qty numeric;
begin
  perform erp.require_internal();
  if v_reason is null then raise exception 'change_reason is required'; end if;
  if v_action not in('SAVE','DELETE') then raise exception 'action must be SAVE or DELETE'; end if;
  if v_action='SAVE' and coalesce(jsonb_typeof(p_payload->'items'),'null')<>'array' then raise exception 'items must be a JSON array'; end if;
  v_hash:=erp._request_hash(jsonb_build_object('payload',p_payload,'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('save_contractor_material_issue_draft_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);
  if v_id is null then
    if v_action='DELETE' then raise exception 'Issue id is required for DELETE'; end if;
    if p_expected_version is not null then raise exception 'expected_version must be null on create'; end if;
    insert into erp.contractor_material_issues(
      issue_number,contractor_id,po_id,physical_at,status,notes,created_by,location_id
    ) values(
      btrim(p_payload->>'issue_number'),(p_payload->>'contractor_id')::uuid,
      nullif(p_payload->>'po_id','')::uuid,(p_payload->>'physical_at')::timestamptz,
      'DRAFT',nullif(btrim(p_payload->>'notes'),''),erp.current_app_user_id(),
      (p_payload->>'location_id')::uuid
    ) returning * into h;v_id:=h.id;
  else
    if p_expected_version is null then raise exception 'expected_version is required'; end if;
    select * into h from erp.contractor_material_issues where id=v_id for update;
    if h.id is null then raise exception 'Contractor material issue not found'; end if;
    if h.row_version<>p_expected_version then raise exception 'STALE_VERSION expected %, current %',p_expected_version,h.row_version; end if;
    if h.status<>'DRAFT' then raise exception 'Only DRAFT contractor issue can be saved/deleted'; end if;
    if v_action='DELETE' then
      delete from erp.contractor_material_issues where id=v_id;
      v_response:=jsonb_build_object('contractor_material_issue_id',v_id,'status','DELETED');
      return erp._idempotency_complete('save_contractor_material_issue_draft_v2',p_client_request_id,v_response);
    end if;
    update erp.contractor_material_issues
    set issue_number=coalesce(nullif(btrim(p_payload->>'issue_number'),''),h.issue_number),
        contractor_id=case when p_payload?'contractor_id' then (p_payload->>'contractor_id')::uuid else h.contractor_id end,
        po_id=case when p_payload?'po_id' then nullif(p_payload->>'po_id','')::uuid else h.po_id end,
        physical_at=coalesce(nullif(p_payload->>'physical_at','')::timestamptz,h.physical_at),
        location_id=case when p_payload?'location_id' then (p_payload->>'location_id')::uuid else h.location_id end,
        notes=case when p_payload?'notes' then nullif(btrim(p_payload->>'notes'),'') else h.notes end
    where id=v_id returning * into h;
  end if;
  if jsonb_array_length(p_payload->'items')=0 then raise exception 'At least one contractor issue line is required'; end if;
  if not exists(select 1 from erp.locations l where l.id=h.location_id and l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE') then
    raise exception 'Contractor issue location must be an active raw-material warehouse';
  end if;
  delete from erp.contractor_material_issue_items where issue_id=v_id;
  for v_line in select value from jsonb_array_elements(p_payload->'items') loop
    select material_type into v_type from erp.materials
    where id=(v_line->>'material_id')::uuid and is_active;
    if v_type is null then raise exception 'Active material is required'; end if;
    v_roll:=nullif(v_line->>'roll_id','')::uuid;
    if v_type='FABRIC' and v_roll is null then raise exception 'FABRIC contractor issue requires roll_id'; end if;
    if v_type<>'FABRIC' and v_roll is not null then raise exception 'Only FABRIC may use roll_id'; end if;
    v_qty:=coalesce(nullif(v_line->>'qty','')::numeric,nullif(v_line->>'transaction_qty','')::numeric);
    if nullif(v_line->>'manual_retail_unit_price','') is not null then
      if v_qty is null or v_qty::text in('NaN','Infinity','-Infinity') or v_qty<=0 or v_qty<>trunc(v_qty)
        or (nullif(v_line->>'transaction_qty','') is not null and (v_line->>'transaction_qty')::numeric<>v_qty) then
        raise exception 'Jumlah eceran harus PCS utuh dan konsisten sebelum penyimpanan'; end if;
    end if;
    -- Explicit manual retail price is a separate base-PCS price. Configured
    -- dozen/gross prices remain versioned and are never overwritten.
    insert into erp.contractor_material_issue_items(
      id,issue_id,material_id,roll_id,qty,unit_sale_price_snapshot,
      notes,transaction_qty,manual_retail_unit_price
    ) values(
      coalesce(nullif(v_line->>'id','')::uuid,gen_random_uuid()),v_id,
      (v_line->>'material_id')::uuid,v_roll,v_qty,0,
      nullif(btrim(v_line->>'notes'),''),nullif(v_line->>'transaction_qty','')::numeric,nullif(v_line->>'manual_retail_unit_price','')::numeric
    );
  end loop;
  select * into h from erp.contractor_material_issues where id=v_id;
  v_response:=jsonb_build_object(
    'contractor_material_issue_id',h.id,'status',h.status,'row_version',h.row_version,
    'item_count',(select count(*) from erp.contractor_material_issue_items i where i.issue_id=v_id),
    'base_qty_total',(select sum(i.qty) from erp.contractor_material_issue_items i where i.issue_id=v_id),
    'receivable_total',(select sum(i.total_receivable) from erp.contractor_material_issue_items i where i.issue_id=v_id)
  );
  return erp._idempotency_complete('save_contractor_material_issue_draft_v2',p_client_request_id,v_response);
end;
$function$;
CREATE OR REPLACE FUNCTION erp.sync_material_cost_revaluation(p_material_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  r record;
  v_target numeric(24,2);
  v_old numeric(24,2);
  v_diff numeric(24,2);
  v_counterpart text;
  v_po uuid;
  v_contractor uuid;
  v_material_type text;
  v_lines jsonb;
  v_event uuid;
  v_journal uuid;
begin
  perform erp.require_internal();

  for r in
    select msm.*
    from erp.material_stock_movements msm
    where msm.material_id=p_material_id
      and msm.movement_type<>'REVERSAL'
      and msm.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN','CONTRACTOR_MATERIAL_ISSUE_ITEM','MATERIAL_SUPPLIER_RETURN_ITEM')
    order by msm.physical_at,msm.system_created_at,msm.id
    for update
  loop
    v_counterpart:=null; v_po:=null; v_contractor:=null; v_material_type:=null;

    if r.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN') then
      v_counterpart:='WIP';
      select cg.po_id into v_po from erp.cutting_groups cg where cg.id=r.source_id;
    elsif r.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' then
      select cmi.po_id,cmi.contractor_id,m.material_type
      into v_po,v_contractor,v_material_type
      from erp.contractor_material_issue_items ii
      join erp.contractor_material_issues cmi on cmi.id=ii.issue_id
      join erp.materials m on m.id=ii.material_id
      where ii.id=r.source_id;
      v_counterpart:=case when v_material_type='ACCESSORY' then 'ACCESSORY_RECOVERY_COGS' else 'WIP' end;
    elsif r.source_type='MATERIAL_SUPPLIER_RETURN_ITEM' then
      v_counterpart:='MATERIAL_PURCHASE_VARIANCE';
    end if;

    if v_counterpart is null then continue; end if;

    if exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=r.id) then
      v_target:=0;
    else
      v_target:=round((r.qty_signed*(r.unit_cost_snapshot-coalesce(r.original_unit_cost_snapshot,r.unit_cost_snapshot)))::numeric,2);
    end if;

    select s.applied_inventory_delta into v_old
    from erp.material_cost_revaluation_state s where s.movement_id=r.id for update;
    v_old:=coalesce(v_old,0);
    v_diff:=round(v_target-v_old,2);

    if abs(v_diff)>0.005 then
      if v_diff>0 then
        v_lines:=jsonb_build_array(
          jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',v_diff,'credit',0,'po_id',v_po,'contractor_id',v_contractor),
          jsonb_build_object('mapping_key',v_counterpart,'debit',0,'credit',v_diff,'po_id',v_po,'contractor_id',v_contractor)
        );
      else
        v_lines:=jsonb_build_array(
          jsonb_build_object('mapping_key',v_counterpart,'debit',abs(v_diff),'credit',0,'po_id',v_po,'contractor_id',v_contractor),
          jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',0,'credit',abs(v_diff),'po_id',v_po,'contractor_id',v_contractor)
        );
      end if;

      insert into erp.material_cost_revaluation_events(material_id,movement_id,effective_date,old_inventory_delta,new_inventory_delta,delta_amount,counterpart_mapping_key,po_id,contractor_id)
      values(p_material_id,r.id,coalesce(erp.invoice_recost_economic_date_v1(),erp._cp3_business_date(statement_timestamp())),v_old,v_target,v_diff,v_counterpart,v_po,v_contractor)
      returning id into v_event;

      v_journal:=erp.post_journal('MATERIAL_COST_REVALUATION',v_event,coalesce(erp.invoice_recost_economic_date_v1(),erp._cp3_business_date(statement_timestamp())),
        'Automatic material moving-average recost: '||r.source_type,v_lines);
      update erp.material_cost_revaluation_events set journal_entry_id=v_journal where id=v_event;
    end if;

    insert into erp.material_cost_revaluation_state(movement_id,applied_inventory_delta,updated_at)
    values(r.id,v_target,statement_timestamp())
    on conflict(movement_id) do update set applied_inventory_delta=excluded.applied_inventory_delta,updated_at=statement_timestamp();
  end loop;
  for r in select distinct i.adjustment_id
    from erp.material_adjustment_items i
    join erp.material_stock_movements m on m.source_type='MATERIAL_ADJUSTMENT_ITEM'
      and m.source_id=i.id and m.reversal_of_id is null
    where m.material_id=p_material_id order by i.adjustment_id
  loop
    perform erp._cp6_sync_material_adjustment_revaluation(r.adjustment_id,p_material_id);
  end loop;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.sync_po_hpp_to_gl(p_po_id uuid, p_effective_date date DEFAULT ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  t record;
  s erp.po_hpp_gl_state%rowtype;
  v_target_qty integer:=0;
  v_target_hpp numeric(24,6):=0;
  v_target_fg numeric(24,6):=0;
  v_target_cogs numeric(24,6):=0;
  v_target_other numeric(24,6):=0;
  v_df numeric(24,6);v_dc numeric(24,6);v_do numeric(24,6);v_sum numeric(24,6);
  v_lines jsonb:='[]'::jsonb;v_event uuid;v_journal uuid;v_documented_gain numeric(24,6):=0;
begin
  perform erp.require_internal();
  p_effective_date:=coalesce(erp.invoice_recost_economic_date_v1(),p_effective_date);
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into t from erp.compute_po_hpp_gl_targets_v2620d(p_po_id);
  select * into s from erp.po_hpp_gl_state where po_id=p_po_id for update;

  if coalesce(t.base_output_qty,0)>0 then
    v_target_qty:=t.base_output_qty;
    -- Cumulative targets, deltas, journal lines, and saved state all use the
    -- same minor-unit values. The balancing bucket receives the deterministic remainder.
    v_target_hpp:=round(coalesce(t.hpp_total_cost,0),2);
    v_target_fg:=round(coalesce(t.fg_value,0),2);
    v_target_cogs:=round(coalesce(t.cogs_value,0),2);
    v_target_other:=v_target_hpp-v_target_fg-v_target_cogs;

    with lot_hpp as(
      select fl.id lot_id,case when coalesce(hv.qty_basis_pcs,0)>0
        then hv.total_cost/hv.qty_basis_pcs else 0 end::numeric hpp_per_pcs
      from erp.fg_lots fl left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current=true
      where fl.po_id=p_po_id and fl.lot_origin<>'VOIDED_PRODUCTION'
    ), adj_net as(
      select fm.lot_id,sum(fm.qty_signed)::numeric qty
      from erp.fg_stock_movements fm join erp.fg_lots fl on fl.id=fm.lot_id
      where fl.po_id=p_po_id and fl.lot_origin<>'VOIDED_PRODUCTION'
        and((fm.movement_type='ADJUSTMENT' and fm.source_type='FG_ADJUSTMENT_ITEM')
          or(fm.movement_type='REVERSAL' and exists(
            select 1 from erp.fg_stock_movements orig where orig.id=fm.reversal_of_id
              and orig.movement_type='ADJUSTMENT' and orig.source_type='FG_ADJUSTMENT_ITEM')))
      group by fm.lot_id
    )
    select coalesce(sum(greatest(a.qty,0)*lh.hpp_per_pcs),0) into v_documented_gain
    from adj_net a join lot_hpp lh on lh.lot_id=a.lot_id;
    if v_target_other < -v_documented_gain-0.01 then
      raise exception 'PO HPP allocation inconsistent: financial FG + net sold exceeds production output without a matching documented positive FG adjustment';
    end if;
  else
    v_target_qty:=0;v_target_hpp:=0;v_target_fg:=0;v_target_cogs:=0;v_target_other:=0;
    if s.po_id is null then return; end if;
  end if;

  v_df:=v_target_fg-round(coalesce(s.fg_value,0),2);
  v_dc:=v_target_cogs-round(coalesce(s.cogs_value,0),2);
  v_do:=v_target_other-round(coalesce(s.other_out_value,0),2);
  v_sum:=v_df+v_dc+v_do;

  if abs(v_df)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_df>0
    then jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_df,'credit',0,'po_id',p_po_id)
    else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',abs(v_df),'po_id',p_po_id) end); end if;
  if abs(v_dc)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_dc>0
    then jsonb_build_object('mapping_key','COGS','debit',v_dc,'credit',0,'po_id',p_po_id)
    else jsonb_build_object('mapping_key','COGS','debit',0,'credit',abs(v_dc),'po_id',p_po_id) end); end if;
  if abs(v_do)>0.005 then
    if v_do>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','OTHER_EXPENSE','debit',v_do,'credit',0,'po_id',p_po_id));
    else v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','OTHER_INCOME','debit',0,'credit',abs(v_do),'po_id',p_po_id)); end if;
  end if;
  if abs(v_sum)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_sum>0
    then jsonb_build_object('mapping_key','WIP','debit',0,'credit',v_sum,'po_id',p_po_id)
    else jsonb_build_object('mapping_key','WIP','debit',abs(v_sum),'credit',0,'po_id',p_po_id) end); end if;

  if jsonb_array_length(v_lines)>=2 then
    insert into erp.po_hpp_gl_events(po_id,effective_date,old_hpp_total,new_hpp_total,fg_delta,cogs_delta,other_delta)
    values(p_po_id,p_effective_date,round(coalesce(s.hpp_total_cost,0),2),v_target_hpp,v_df,v_dc,v_do)
    returning id into v_event;
    v_journal:=erp.post_journal('PO_HPP_GL_SYNC',v_event,p_effective_date,
      'Latest corrected HPP allocation · exact minor-unit targets',v_lines);
    update erp.po_hpp_gl_events set journal_entry_id=v_journal where id=v_event;
  end if;

  insert into erp.po_hpp_gl_state(po_id,base_output_qty,hpp_total_cost,fg_value,cogs_value,other_out_value,updated_at)
  values(p_po_id,v_target_qty,v_target_hpp,v_target_fg,v_target_cogs,v_target_other,statement_timestamp())
  on conflict(po_id) do update set base_output_qty=excluded.base_output_qty,
    hpp_total_cost=excluded.hpp_total_cost,fg_value=excluded.fg_value,
    cogs_value=excluded.cogs_value,other_out_value=excluded.other_out_value,updated_at=statement_timestamp();
end
$function$;

do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule')
), objects as (
 select 'FUNCTION:'||format('%I.%I(%s)',n.nspname,p.proname,replace(oidvectortypes(p.proargtypes),', ',',')) k,
 jsonb_build_array(pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl)a order by a::text) end) v
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p')
 union all
 select 'RELATION:'||format('%I.%I',nspname,relname),jsonb_build_array(relkind,pg_get_userbyid(relowner),
  case when relacl is null then null else array(select a::text from unnest(relacl)a order by a::text) end,
  relrowsecurity,relforcerowsecurity,relreplident,relpersistence,relispartition,reloptions)
 from relations
 union all
 select 'COLUMN:'||format('%I.%I.%I',r.nspname,r.relname,a.attname),
 jsonb_build_array((select count(*) from pg_attribute visible where visible.attrelid=a.attrelid and visible.attnum>0 and not visible.attisdropped and visible.attnum<=a.attnum),format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,
  pg_get_expr(d.adbin,d.adrelid),a.attcollation::regcollation::text,
  case when a.attacl is null then null else array(select x::text from unnest(a.attacl)x order by x::text) end)
 from relations r join pg_attribute a on a.attrelid=r.oid and a.attnum>0 and not a.attisdropped
 left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum
 union all
 select 'CONSTRAINT:'||format('%I.%I.%I',r.nspname,r.relname,c.conname),
 jsonb_build_array(c.contype,pg_get_constraintdef(c.oid),c.condeferrable,c.condeferred,c.convalidated,c.conislocal,c.connoinherit)
 from relations r join pg_constraint c on c.conrelid=r.oid
 union all
 select 'INDEX:'||format('%I.%I',r.nspname,c.relname),
 jsonb_build_array(pg_get_indexdef(i.indexrelid),i.indisunique,i.indisprimary,i.indisexclusion,i.indisvalid,i.indisready,i.indisclustered,i.indisreplident,c.reloptions)
 from relations r join pg_index i on i.indrelid=r.oid join pg_class c on c.oid=i.indexrelid
 union all
 select 'TRIGGER:'||format('%I.%I.%I',r.nspname,r.relname,t.tgname),jsonb_build_array(pg_get_triggerdef(t.oid),t.tgenabled)
 from relations r join pg_trigger t on t.tgrelid=r.oid and not t.tgisinternal
 union all
 select 'POLICY:'||format('%I.%I.%I',r.nspname,r.relname,p.polname),jsonb_build_array(p.polcmd,p.polpermissive,
  array(select case when x=0 then 'PUBLIC' else pg_get_userbyid(x) end from unnest(p.polroles)x order by 1),
  pg_get_expr(p.polqual,p.polrelid),pg_get_expr(p.polwithcheck,p.polrelid))
 from relations r join pg_policy p on p.polrelid=r.oid
 union all
 select 'VIEW:'||format('%I.%I',nspname,relname),to_jsonb(pg_get_viewdef(oid,false)) from relations where relkind in('v','m')
 union all
 select 'SEQUENCE:'||format('%I.%I',r.nspname,r.relname),jsonb_build_array(format_type(s.seqtypid,null),s.seqstart,s.seqincrement,s.seqmax,s.seqmin,s.seqcache,s.seqcycle)
 from relations r join pg_sequence s on s.seqrelid=r.oid
 union all
 select 'SCHEMA:'||nspname,jsonb_build_array(pg_get_userbyid(nspowner),
  case when nspacl is null then null else array(select a::text from unnest(nspacl)a order by a::text) end)
 from pg_namespace where nspname in('erp','public')
 union all
 select 'DEFAULT_ACL:'||pg_get_userbyid(d.defaclrole)||':'||coalesce(n.nspname,'GLOBAL')||':'||d.defaclobjtype::text,
 to_jsonb(array(select a::text from unnest(d.defaclacl)a order by a::text))
 from pg_default_acl d left join pg_namespace n on n.oid=d.defaclnamespace
 where n.nspname in('erp','public') or d.defaclnamespace=0
 union all
 select 'ENUM:'||format('%I.%I',n.nspname,t.typname),jsonb_build_array(pg_get_userbyid(t.typowner),
  (select jsonb_agg(e.enumlabel order by e.enumsortorder) from pg_enum e where e.enumtypid=t.oid))
 from pg_type t join pg_namespace n on n.oid=t.typnamespace where n.nspname in('erp','public') and t.typtype='e'
)
select coalesce(jsonb_object_agg(k,encode(extensions.digest(convert_to(v::text,'UTF8'),'sha256'),'hex')),'{}'::jsonb) from objects
) catalog;
 select count(*),encode(extensions.digest(convert_to(coalesce(string_agg(length(key)::text||':'||key||':'||value,E'\n' order by key collate "C"),''),'UTF8'),'sha256'),'hex') into object_count,fingerprint from jsonb_each_text(actual);
 if object_count<>6636 or fingerprint is distinct from 'd4928be2a2744508d8b7acaabd0227538cc6245d73d6f34e3134b240a50d5fa0' then
  raise exception 'AO_INSTALLED_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
update erp.cp6_v2620ao_rollback_capsule c set installed_definition_sha256=encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'),'sha256'),'hex');
do $after_data$
declare v_table text;v_hash jsonb;v_after jsonb;v_preserved jsonb;
begin
 v_after:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620ao_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_after:=v_after||jsonb_build_object(v_table,v_hash);
 end loop;

 v_preserved:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620ao_rollback_capsule','invoice_recost_execution_context']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t)-case %L when 'contractor_material_issue_items' then array['manual_retail_unit_price']::text[] else array[]::text[] end)::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table,v_table) into v_hash;
  v_preserved:=v_preserved||jsonb_build_object(v_table,v_hash);
 end loop;

 if v_preserved is distinct from (select boundary_snapshot->'before' from erp.cp6_v2620ao_rollback_capsule limit 1)
  or exists(select 1 from jsonb_each(v_after) where key=any(array['invoice_recost_execution_context']::text[]) and (value->>'count')::bigint<>0)
  then raise exception 'AO_INSTALL_CHANGED_BUSINESS_DATA';end if;
 update erp.cp6_v2620ao_rollback_capsule set boundary_snapshot=boundary_snapshot||jsonb_build_object('after',v_after);
end $after_data$;
insert into erp.schema_migrations(version,description) values('v2.6.20ao','CP6 AO source-bound connected import, inventory and financial lifecycle package');
do $capsule_guard$
declare r record;c record;e jsonb;boundary jsonb;actual jsonb;expected jsonb;
begin
 if not exists(select 1 from pg_class where oid='erp.cp6_v2620ao_rollback_capsule'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
  or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='erp.cp6_v2620ao_rollback_capsule'::regclass and a.grantee<>p.relowner)
  or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='erp.cp6_v2620ao_rollback_capsule'::regclass and a.grantee<>'postgres'::regrole)
  or exists(select 1 from pg_policy where polrelid='erp.cp6_v2620ao_rollback_capsule'::regclass)
  or exists(select 1 from pg_trigger where tgrelid='erp.cp6_v2620ao_rollback_capsule'::regclass and not tgisinternal)
  or (select count(*) from erp.cp6_v2620ao_rollback_capsule)<>10 then raise exception 'AO_CAPSULE_SECURITY_OR_COUNT';end if;
 -- Match the complete visible column/constraint/index shape to the source-pinned
 -- AN template. Names of generated capsule indexes are intentionally immaterial.
 for r in select unnest(array['erp.cp6_v2620ao_rollback_capsule','erp.cp6_v2620an_rollback_capsule']) as rel loop
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel::regclass)) into actual;
  if expected is null then expected:=actual;elsif actual is distinct from expected then raise exception 'AO_CAPSULE_SHAPE_DRIFT';end if;
 end loop;
 select boundary_snapshot into boundary from erp.cp6_v2620ao_rollback_capsule limit 1;
 if boundary is null or exists(select 1 from erp.cp6_v2620ao_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before']) then raise exception 'AO_CAPSULE_BOUNDARY';end if;
 for r in select * from jsonb_each('{"erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)":{"acl":["postgres=X/postgres"],"identity":"erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)","installed_sha256":"b6b5fdae99e0dd5c263c2d76c4bf9e4e087db014bf22ca78fef226dd6ee3fe9f","owner":"postgres","predecessor_sha256":"4b7dfd039b49e56082d0dd0a63613cfdaf7483af244627109dd1c2ed230e9804"},"erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)":{"acl":["postgres=X/postgres"],"identity":"erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)","installed_sha256":"88f9326b1ba192f7f42fa9d3d849c9927ebbafd71bc358ca8efabb37cdd88c99","owner":"postgres","predecessor_sha256":"2069e292b0c43850a19469ae20af36616e396840619e72c43d204e209154987d"},"erp.normalize_contractor_issue_item_uom_price()":{"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.normalize_contractor_issue_item_uom_price()","installed_sha256":"1f513cd5017be61bb974f877100568ad856250eadb977d28ebb5ac9222664816","owner":"postgres","predecessor_sha256":"d83bccf28a18c5af10e5c7bf206be85d33fe4ee9890253c24c5b6e331508b045"},"erp.post_material_purchase_cost_correction(uuid)":{"acl":["authenticated=X/postgres","postgres=X/postgres"],"identity":"erp.post_material_purchase_cost_correction(uuid)","installed_sha256":"a60812fb34ddae1660ff68a4df0af3c29a87201a71f0a4e769904972d4800903","owner":"postgres","predecessor_sha256":"5839dee0ab9db69ebabf5f08894b5c6603c851c1d55aa9eff30a12dd0331dff9"},"erp.post_material_supplier_invoice(uuid)":{"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.post_material_supplier_invoice(uuid)","installed_sha256":"7f7c0df785f1ad715052746d2614d78c3992c018fc8f24abad5f36b6928af2ea","owner":"postgres","predecessor_sha256":"5b455191508e0945c388f804e189055a435b8a56faab9213a01e812420784c0a"},"erp.reverse_material_purchase_cost_correction(uuid,text)":{"acl":["authenticated=X/postgres","postgres=X/postgres"],"identity":"erp.reverse_material_purchase_cost_correction(uuid,text)","installed_sha256":"6aa31b5acdb31d654b1a5389a6fd8282c78d7088b3840a5493d89c5ba806bba7","owner":"postgres","predecessor_sha256":"9913ee82901495aa850712c29d21ab8a8b96a5d71c29fca20fb0844b1af1dddd"},"erp.reverse_material_supplier_invoice(uuid,text)":{"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.reverse_material_supplier_invoice(uuid,text)","installed_sha256":"c4a3194b4be9107102961fd3fe1c00127c278e3e33048fe2d10871cc7407d1b8","owner":"postgres","predecessor_sha256":"b4b10a9021e4360a25327656217fac0ed8a171748c215af2291ed00539684cb2"},"erp.save_contractor_material_issue_draft_v2(jsonb,uuid,bigint)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.save_contractor_material_issue_draft_v2(jsonb,uuid,bigint)","installed_sha256":"d770d21f6bdb3962818fa4c677367ec15998420e5e92c195e1feb538a2227e20","owner":"postgres","predecessor_sha256":"59395cfcdb7e13f47ac083b48921dbaddb97db2c09f17cf9e22b383fd97cfa3f"},"erp.sync_material_cost_revaluation(uuid)":{"acl":["postgres=X/postgres"],"identity":"erp.sync_material_cost_revaluation(uuid)","installed_sha256":"ae4ad29be5dbba3db18da7da9256723c86b3388d0f0d6293db6271170f078461","owner":"postgres","predecessor_sha256":"7710e4d4f7b5179ec6539a1aa3957cde32c470a8a768eb417850be07bf0fbeda"},"erp.sync_po_hpp_to_gl(uuid,date)":{"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.sync_po_hpp_to_gl(uuid,date)","installed_sha256":"0f460c85c5c7d6cbd0ddf30dfa78336b8016c6a83d39f5dc9caf3ac2ca6a4418","owner":"postgres","predecessor_sha256":"a444bcb1e18ede1b5b9cb300b43ba99565c073d1050a06270046bbb2ecc666e2"}}'::jsonb) loop
  select * into c from erp.cp6_v2620ao_rollback_capsule where object_regidentity=r.key;e:=r.value;
  if c.object_regidentity is null or c.definition_sha256 is distinct from e->>'predecessor_sha256'
   or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex') is distinct from e->>'predecessor_sha256'
   or c.installed_definition_sha256 is distinct from e->>'installed_sha256'
   or c.owner_snapshot is distinct from e->>'owner' or to_jsonb(c.acl_snapshot) is distinct from e->'acl' then
   raise exception 'AO_CAPSULE_SOURCE_DRIFT: %',r.key;
  end if;
 end loop;
end $capsule_guard$;
commit;
