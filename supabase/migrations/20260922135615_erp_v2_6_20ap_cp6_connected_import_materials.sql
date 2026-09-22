-- CP6 AP: source-bound permanent package. Closed, drained maintenance required.
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
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20ao')
  or exists(select 1 from erp.schema_migrations where version='v2.6.20ap') or to_regclass('erp.cp6_v2620ap_rollback_capsule') is not null
  or (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20ao_cp6_invoice_retail')<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version='20260922135612' and name='erp_v2_6_20ao_cp6_invoice_retail'
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='5687bb0236528d7e485e738ee2f96c2be0f4bde7e0d41c16bacee3a58183bdbb')
  or exists(select 1 from supabase_migrations.schema_migrations where version>'20260922135612') then raise exception 'AP_EXACT_PREDECESSOR_REQUIRED';end if;
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
 if object_count<>6646 or fingerprint is distinct from '9577907de2a00601ebb22a6f59178db499970d61d058c44d83edcd7f67576ebe' then
  raise exception 'AP_PREDECESSOR_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
do $historical_capsules$
declare r record;actual text;
begin
 for r in select * from jsonb_each_text('{"bs_resolution_v2619_rollback_capsule":"28ab388833da7da87384766ecaedadc66b4d048c303ee91e16f3939e34afdc39","bs_resolution_v2619a_rollback_capsule":"de8dfaab7b63b8742d383a089cdb05e73b629aad9f4df149e6a3c9fb590ef560","bs_resolution_v2619b_rollback_capsule":"d6d4f7457743d51679b5d25bf166ed69ca4b4f098cf5902ff985937531c2505d","bs_resolution_v2619c_rollback_capsule":"0207ba4f2ffba8ed61584709bbd884f1d2ee1a5981194fd7189a45afe8b3cbe1","cp3_r4_rollback_capsule":"7c01add62e66a4e2774a7199c2e77a04cca5e5942dbbba54d22cef720f82bc1d","cp45_v2617_rollback_capsule":"b9a43ce463de9905e94dd6538fd2a4952b0586a78c145f6f9d88aab7d6da3d80","cp45_v2617a_rollback_capsule":"b065dbcfdf1b59cb799e9f58caf6dd5ca7686e9f70826fce6a1ba8f140610022","cp4_v2616_rollback_capsule":"dde0a005dbe7cc93709bdfc6b961f4b9a76bf4db06fd7177d21dc79048af4d2f","cp6_v2620_rollback_capsule":"01f1e4e23211cff3c399d2d768a41be57980bfab00790715aa759b00a515e032","cp6_v2620a_rollback_capsule":"67befaaf327d2591e1ca1d654132ee483eba39b6cbb4f891c4719d817155d448","cp6_v2620aa_rollback_capsule":"eb0d6fb4fcac2ac06929d577101e604428e9a04821813c342e5b831147dc8948","cp6_v2620ab_rollback_capsule":"3be9a9166e3a607962be819fbe23d38fe455290a7a970dc2aad068079bf30785","cp6_v2620ac_relation_rollback_capsule":"2be5cbb62d1147e1e0d053dc4e447fe1d1258439352c297814c981c985959838","cp6_v2620ac_rollback_capsule":"51a8b08c9d96e66f03c2c8ba94ed3ed8fb15b26d1a2e4c65c58c614442dfa969","cp6_v2620ad_rollback_capsule":"5c3588109395b32ed743e0f4f5d789a3c59e3fffbab7469138f1f423c877ea9d","cp6_v2620ae_rollback_capsule":"6a75e02bf7b90c542fd9f2ac9534a2de066b047f5ffea65bffb1f83fa63c17f0","cp6_v2620af_rollback_capsule":"bfa89fc0e94d34b29405acedf551935f024942835f31cdc98f0f0983a9550288","cp6_v2620ag_rollback_capsule":"7ddfe6181f0c1c7439faf8a8150c542e958b3bafd8d18b5b2d1eb454fd7a85b7","cp6_v2620ah_rollback_capsule":"361be9321e5f4dadc7c7ec0e99ed746a98e7a4150178fc8355d23707c1507a93","cp6_v2620ai_rollback_capsule":"f2428dd712aa763b1379a4ae5b1a1e1e6ee175b355d8769b854a28f1355181c8","cp6_v2620aj_rollback_capsule":"8e24026dc90a2a92292c2cc6c8faa5fc3de991a19f326db494e0af2a518436f1","cp6_v2620ak_rollback_capsule":"dc7bfce7b9ee6a42e33cdf03cabd99d64435a4615245b2037fd6e4ee399aef10","cp6_v2620al_rollback_capsule":"c9e9aca042674efa5c6fa283e4b9ee47f3353ee9ee95b34e14ef1fd6b09bfde9","cp6_v2620am_rollback_capsule":"e781e631d06c6894c20b1fe6f9c65779f461d19c405c8ae74f28ed7d83ae6a26","cp6_v2620an_rollback_capsule":"ebfa8a281a32fe54babbdc209264ab422fde27f344d48561b90d2af022fe75b3","cp6_v2620b_rollback_capsule":"f9bf784bff0c54e647f491e257a9649fd0c3e6f10c39ddfc0944c961b9dd7601","cp6_v2620c_rollback_capsule":"f88b1f5890ee8e7041758971bf9c9a3ce2bd0a7be6989fb95332c2dd7fa139aa","cp6_v2620d_rollback_capsule":"fa300c5554da4bb6812c61d726fd64f66329c97b085fa7d6ad5d0d8e5ae31235","cp6_v2620e_rollback_capsule":"143cd291cf4c12e78ab61e74e02ed03b08a48832a5064671868ff2bd2e3e1da7","cp6_v2620f_rollback_capsule":"076133b098e821fc2713af559618adf8aa3e204908f810af440fda355fc7a57f","cp6_v2620g_rollback_capsule":"ed9f4cacb47bd026ad6bdea373d1aa87044ed12aa60323cea453e3187dc488c4","cp6_v2620h_rollback_capsule":"4c25a060a2df3c22cd6fa9ff0b297163e223118a0d930b97bf1282b4756d909d","cp6_v2620i_rollback_capsule":"051203d95c44968abd8594f5bd48e289c4ac9a6c9fa49a89eee1086ad6b2c166","cp6_v2620j_rollback_capsule":"1393a8085d0f58717b13048c9cc3f7e9969ac86c351d6dfefdd2d4f43a735bd2","cp6_v2620k_rollback_capsule":"55aa71061f616ea11b361f0fabee2fd892f6438cc3f567cb9c135552ade42409","cp6_v2620l_rollback_capsule":"b4278768fce4ef307795953c14f607278c43bf474d76d3362e477280be08eb39","cp6_v2620m_rollback_capsule":"4b5f89d7bc4557f92b47716fe15640ab244c424fc1279433eb806d9d91d234e9","cp6_v2620n_rollback_capsule":"46e5ea4524613bb7a386551ada9e06888ea35eb987f9f5b864457fdd18bc3bc1","cp6_v2620o_rollback_capsule":"044e6b1a050df7e2a1d36082b0451877bda01116c08f611dfceb7a666bdf03c8","cp6_v2620p_rollback_capsule":"b656abaf23276984567c6c8d87b311427463c008b5ecd762fbdd0c2df13795df","cp6_v2620q_rollback_capsule":"ab6c992fbaa87f19a4eba696a57a3972f98504a354d9b5fc3be660939f8ea20f","cp6_v2620r_rollback_capsule":"8eb5e0a38284c5f8e3fee56618893ba72feaae9d26605c9ca3874dae25045297","cp6_v2620s_rollback_capsule":"fb57810a75f8829a038ed61b3a1cabde33dccf1e384661bc6723c51e28b3e132","cp6_v2620t_rollback_capsule":"348db4650d788750da243500b49e23c1130fdb70bc4a6d1fdf136bf68aa21f30","cp6_v2620u_rollback_capsule":"720eb1984548a3c381387fbe4d34e3c6f00334c8a4549eab7e398b827dcb7dd4","cp6_v2620v_rollback_capsule":"573ef5842eefadf1c32469514f4c8498667c99aec20ef20651406e4f419f5f60","cp6_v2620w_rollback_capsule":"f4e2ca1d577dd9f2724cc90693e8ee8bff36365c696575b69c6463f3e8ca0324","cp6_v2620x_rollback_capsule":"064db1068b56daa69e409ae582cd8a99490cea75d269154baa4217f90d3ca0d1","cp6_v2620y_rollback_capsule":"e3b23429a7f002c85ca8de1f8c632df13a4a2fc4e4654c12e2431c212772841d","cp6_v2620z_rollback_capsule":"ad0436a1480af43070e9861cb7e28d4cf55c435edbffb5fe368ca7babb7863ef","cutting_bridge_v2618_rollback_capsule":"535d1abd25668bc5bee79d82a602afe5efe4e8ce313bf1fb5170ae2004e3cb2d","cutting_bridge_v2618a_rollback_capsule":"db0608e690b3d936fa20b62cc4cfb9b1f9e86718212526eb6131562578b8bf60"}'::jsonb) loop
  execute format($caps$select encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to((to_jsonb(t)-array['captured_at','boundary_snapshot'])::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$caps$,r.key) into actual;
  if actual is distinct from r.value then raise exception 'AP_HISTORICAL_CAPSULE_DRIFT: %',r.key;end if;
 end loop;
end $historical_capsules$;
create table erp.cp6_v2620ap_rollback_capsule(like erp.cp6_v2620an_rollback_capsule including all);
alter table erp.cp6_v2620ap_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620ap_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620ap_rollback_capsule(object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
 format('%I.%I(%s)',n.nspname,p.proname,replace(oidvectortypes(p.proargtypes),', ',',')),pg_get_functiondef(p.oid),
 encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
 array(select a::text from unnest(p.proacl)a order by a::text),pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.oid in('erp._validate_migration_batch_base(uuid)'::regprocedure,'erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)'::regprocedure,'erp.apply_migration_master_rows(uuid)'::regprocedure,'erp.prepare_migration_opening_balance(uuid,text)'::regprocedure,'erp.refresh_material_purchase_item_cost(uuid)'::regprocedure,'erp.run_v267_financial_truth_checks()'::regprocedure,'erp.validate_material_supplier_invoice_line()'::regprocedure,'erp.validate_supplier_return_source()'::regprocedure,'erp.sync_material_purchase_grni_on_status()'::regprocedure,'erp.finalize_migration_batch(uuid)'::regprocedure,'erp._cp6_supplier_cent_state(uuid[])'::regprocedure,'erp.run_v268_financial_report_checks()'::regprocedure,'erp.approve_payroll(uuid)'::regprocedure,'erp.post_opening_subledger_settlement(uuid)'::regprocedure,'erp.post_payroll_payment(uuid)'::regprocedure,'erp.reverse_paid_payroll(uuid,text)'::regprocedure,'erp.post_sales_payment(uuid)'::regprocedure,'erp.post_supplier_payment(uuid)'::regprocedure,'erp.post_vendor_payment(uuid)'::regprocedure,'erp.reverse_journal(uuid,text)'::regprocedure,'erp.reverse_sales_payment(uuid,text)'::regprocedure,'erp.reverse_supplier_payment(uuid,text)'::regprocedure,'erp.reverse_vendor_payment(uuid,text)'::regprocedure,'erp.reverse_opening_subledger_settlement(uuid,text)'::regprocedure,'erp.rebuild_po_hpp(uuid,text)'::regprocedure,'erp.ensure_fg_accessory_cost_snapshot(uuid)'::regprocedure,'erp.get_wip_control_v1(text,uuid,text,text)'::regprocedure,'erp.sync_opening_lot_hpp_to_gl(uuid,date)'::regprocedure,'erp.post_opening_balance(uuid)'::regprocedure,'erp.compute_po_hpp_gl_book_v2620e(uuid)'::regprocedure);
do $before_data$
declare v_table text;v_hash jsonb;v_before jsonb;
begin
 v_before:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620ap_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_before:=v_before||jsonb_build_object(v_table,v_hash);
 end loop;

 update erp.cp6_v2620ap_rollback_capsule set boundary_snapshot=jsonb_build_object('before',v_before,'platform_before',(select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations t where not(false)),'markers_before',(select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from erp.schema_migrations t where not(false)));
end $before_data$;

create table erp.initial_import_financial_sources(
 id uuid primary key default gen_random_uuid(),
 batch_id uuid not null references erp.migration_batches(id),
 source_row_id uuid not null unique references erp.migration_staging_rows(id) on delete cascade,
 opening_item_id uuid not null unique references erp.opening_balance_items(id) on delete cascade,
 balance_type text not null check(balance_type in('CUSTOMER_RECEIVABLE','SUPPLIER_PAYABLE','VENDOR_PAYABLE','CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE')),
 party_id uuid not null,cutover_date date not null,
 source_mode text not null check(source_mode in('SUMMARY','DOCUMENT')),
 document_number text,document_date date,due_date date,
 original_amount numeric(20,2) not null,settled_before_cutover numeric(20,2) not null,
 outstanding_amount numeric(20,2) not null,
 created_at timestamptz not null default statement_timestamp(),
 check(original_amount>0 and settled_before_cutover>=0 and outstanding_amount>0
   and original_amount-settled_before_cutover=outstanding_amount),
 check((source_mode='SUMMARY' and document_number is null and document_date is null and due_date is null and settled_before_cutover=0)
   or (source_mode='DOCUMENT' and nullif(btrim(document_number),'') is not null and document_date is not null
     and document_date<=cutover_date and (due_date is null or due_date>=document_date)))
);
create unique index initial_import_financial_document_key on erp.initial_import_financial_sources
 (balance_type,party_id,lower(btrim(document_number))) where source_mode='DOCUMENT';
create unique index initial_import_financial_summary_key on erp.initial_import_financial_sources
 (balance_type,party_id) where source_mode='SUMMARY';
create index initial_import_financial_party on erp.initial_import_financial_sources(balance_type,party_id);
alter table erp.initial_import_financial_sources enable row level security;
revoke all on erp.initial_import_financial_sources from public,anon,authenticated,service_role;

create table erp.initial_import_opening_stock_sources(
 source_row_id uuid primary key references erp.migration_staging_rows(id) on delete cascade,
 batch_id uuid not null references erp.migration_batches(id),
 source_key text not null,
 opening_item_id uuid not null unique references erp.opening_balance_items(id) on delete cascade,
 unique(batch_id,source_key)
);
create table erp.initial_import_receipt_headers(
 purchase_id uuid primary key references erp.material_purchase_headers(id),
 batch_id uuid not null references erp.migration_batches(id),
 supplier_id uuid not null references erp.suppliers(id),
 receipt_number text not null check(length(btrim(receipt_number)) between 1 and 120),
 receipt_date date not null,cutover_date date not null,
 check(receipt_date<=cutover_date)
);
create unique index initial_import_receipt_identity on erp.initial_import_receipt_headers(supplier_id,lower(btrim(receipt_number)));
create index initial_import_receipt_batch on erp.initial_import_receipt_headers(batch_id);
create table erp.initial_import_receipt_lines(
 purchase_item_id uuid primary key references erp.material_purchase_items(id),
 purchase_id uuid not null references erp.initial_import_receipt_headers(purchase_id),
 source_row_id uuid not null unique references erp.migration_staging_rows(id),
 opening_item_id uuid not null unique references erp.opening_balance_items(id),
 receipt_line_number text not null check(length(btrim(receipt_line_number)) between 1 and 60)
);
create unique index initial_import_receipt_line_identity on erp.initial_import_receipt_lines(purchase_id,lower(btrim(receipt_line_number)));
alter table erp.initial_import_opening_stock_sources enable row level security;
alter table erp.initial_import_receipt_headers enable row level security;
alter table erp.initial_import_receipt_lines enable row level security;
revoke all on erp.initial_import_opening_stock_sources,erp.initial_import_receipt_headers,erp.initial_import_receipt_lines from public,anon,authenticated,service_role;

alter table erp.initial_import_financial_sources add column source_kind text not null default 'BALANCE'
 check(source_kind in('BALANCE','CONTRACTOR_CASH_ADVANCE'));
alter table erp.initial_import_financial_sources add constraint initial_import_cash_advance_source
 check(source_kind='BALANCE' or (balance_type='CONTRACTOR_RECEIVABLE' and source_mode='DOCUMENT'));
alter table erp.payroll_deductions add column opening_cash_advance_balance_id uuid
 references erp.opening_subledger_balances(id);
alter table erp.payroll_deductions drop constraint payroll_deductions_deduction_type_check;
alter table erp.payroll_deductions add constraint payroll_deductions_deduction_type_check
 check(deduction_type in('MATERIAL_KASBON','BS_COMPENSATION','PENALTY','OTHER','CASH_ADVANCE'));
alter table erp.payroll_deductions add constraint payroll_cash_advance_source_check check(
 (deduction_type='CASH_ADVANCE' and opening_cash_advance_balance_id is not null
   and contractor_issue_item_id is null and bs_resolution_id is null)
 or (deduction_type<>'CASH_ADVANCE' and opening_cash_advance_balance_id is null));
create index payroll_cash_advance_balance on erp.payroll_deductions(opening_cash_advance_balance_id,payroll_id)
 where opening_cash_advance_balance_id is not null;
create unique index payroll_cash_advance_once on erp.payroll_deductions(payroll_id,opening_cash_advance_balance_id)
 where opening_cash_advance_balance_id is not null;

create table erp.initial_import_prepayments(
 id uuid primary key default gen_random_uuid(),batch_id uuid not null references erp.migration_batches(id),
 source_row_id uuid not null unique references erp.migration_staging_rows(id),
 party_type text not null check(party_type in('SUPPLIER','CUSTOMER','VENDOR')),party_id uuid not null,
 supplier_id uuid references erp.suppliers(id),customer_id uuid references erp.customers(id),vendor_id uuid references erp.laundry_vendors(id),
 coa_account_id uuid not null references erp.chart_accounts(id),
 document_number text not null check(length(btrim(document_number)) between 1 and 120),
 document_date date not null,cutover_date date not null check(document_date<=cutover_date),
 original_amount numeric(20,2) not null,settled_before_cutover numeric(20,2) not null,amount numeric(20,2) not null,
 created_at timestamptz not null default statement_timestamp(),
 check(original_amount>0 and settled_before_cutover>=0 and amount>0 and original_amount-settled_before_cutover=amount),
 check(num_nonnulls(supplier_id,customer_id,vendor_id)=1 and party_id=coalesce(supplier_id,customer_id,vendor_id)
   and ((party_type='SUPPLIER' and supplier_id is not null) or (party_type='CUSTOMER' and customer_id is not null) or (party_type='VENDOR' and vendor_id is not null)))
);
create unique index initial_import_prepayment_document on erp.initial_import_prepayments(party_type,party_id,lower(btrim(document_number)));
create index initial_import_prepayment_batch on erp.initial_import_prepayments(batch_id);
create index initial_import_prepayment_account on erp.initial_import_prepayments(coa_account_id);
create table erp.initial_import_prepayment_payments(
 payment_id uuid primary key,advance_id uuid not null references erp.initial_import_prepayments(id),
 supplier_payment_id uuid unique references erp.supplier_payments(id),
 sales_payment_id uuid unique references erp.sales_payments(id),
 vendor_payment_id uuid unique references erp.vendor_payments(id),
 opening_settlement_id uuid unique references erp.opening_subledger_settlements(id),
 payment_snapshot jsonb not null,created_at timestamptz not null default statement_timestamp(),
 check(num_nonnulls(supplier_payment_id,sales_payment_id,vendor_payment_id,opening_settlement_id)=1
   and payment_id=coalesce(supplier_payment_id,sales_payment_id,vendor_payment_id,opening_settlement_id))
);
create index initial_import_prepayment_payment_source on erp.initial_import_prepayment_payments(advance_id);
create table erp.initial_import_prepayment_events(
 id uuid primary key default gen_random_uuid(),advance_id uuid not null references erp.initial_import_prepayments(id),
 event_type text not null check(event_type in('CORRECTION','REFUND','REVERSAL')),
 component text not null check(component in('CORRECTION','REFUND')),delta numeric(20,2) not null check(delta<>0),
 effective_date date not null,reason text not null check(length(btrim(reason))>0),
 cash_account_id uuid references erp.cash_accounts(id),
 reverses_event_id uuid unique references erp.initial_import_prepayment_events(id),
 journal_entry_id uuid not null unique references erp.journal_entries(id),
 created_by uuid not null references erp.app_users(id),created_at timestamptz not null default statement_timestamp(),
 check((event_type='REVERSAL' and reverses_event_id is not null) or
   (event_type=component and reverses_event_id is null and (component<>'REFUND' or delta<0))),
 check((component='REFUND' and cash_account_id is not null) or (component='CORRECTION' and cash_account_id is null))
);
create index initial_import_prepayment_event_source on erp.initial_import_prepayment_events(advance_id);
alter table erp.initial_import_prepayments enable row level security;
alter table erp.initial_import_prepayment_payments enable row level security;
alter table erp.initial_import_prepayment_events enable row level security;
revoke all on erp.initial_import_prepayments,erp.initial_import_prepayment_payments,erp.initial_import_prepayment_events from public,anon,authenticated,service_role;
alter table erp.supplier_payments alter column cash_account_id drop not null;
alter table erp.opening_subledger_settlements alter column cash_account_id drop not null;
alter table erp.supplier_payments add constraint supplier_prepayment_funding_check
 check(cash_account_id is not null or payment_method is not distinct from 'OPENING_ADVANCE');
alter table erp.sales_payment_posting_facts alter column cash_account_id drop not null;
alter table erp.sales_payment_posting_facts add constraint sales_prepayment_fact_funding_check
 check(cash_account_id is not null or payment_snapshot->>'payment_method' is not distinct from 'OPENING_ADVANCE');

create table erp.pocket_fabric_materials(
 material_id uuid primary key references erp.materials(id),
 created_by uuid references erp.app_users(id),created_at timestamptz not null default clock_timestamp()
);
create table erp.pocket_fabric_usage(
 adjustment_id uuid primary key references erp.material_adjustments(id),
 material_id uuid not null references erp.pocket_fabric_materials(material_id),
 roll_id uuid not null references erp.material_rolls(id),location_id uuid not null references erp.locations(id),
 input_mode text not null check(input_mode in('USED','REMAINING')),
 input_quantity numeric(20,6) not null check(input_quantity>=0),
 stock_before numeric(20,6) not null check(stock_before>0),
 issued_quantity numeric(20,6) not null check(issued_quantity>0 and issued_quantity<=stock_before),
 stock_revision text not null,posted_header jsonb not null,posted_item jsonb not null,
 cost_policy text not null default 'PERIOD_EXPENSE' check(cost_policy='PERIOD_EXPENSE'),
 created_by uuid references erp.app_users(id),created_at timestamptz not null default clock_timestamp(),
 check(issued_quantity=case input_mode when 'USED' then input_quantity else stock_before-input_quantity end)
);
create index pocket_fabric_usage_roll on erp.pocket_fabric_usage(roll_id);
create index pocket_fabric_usage_material on erp.pocket_fabric_usage(material_id);
create index pocket_fabric_usage_location on erp.pocket_fabric_usage(location_id);
create table erp.pocket_fabric_execution_context(
 backend_pid integer not null,transaction_id bigint not null,actor_key text not null,
 adjustment_id uuid not null references erp.pocket_fabric_usage(adjustment_id),
 primary key(backend_pid,transaction_id,adjustment_id)
);
alter table erp.pocket_fabric_materials enable row level security;
alter table erp.pocket_fabric_usage enable row level security;
alter table erp.pocket_fabric_execution_context enable row level security;
revoke all on erp.pocket_fabric_materials,erp.pocket_fabric_usage,erp.pocket_fabric_execution_context from public,anon,authenticated,service_role;

create table erp.pocket_periods(
 id uuid primary key default gen_random_uuid(),period_start date not null,period_end date not null,
 manifest jsonb not null,denominator bigint not null check(denominator>0),original_amount numeric(20,2) not null check(original_amount>0),
 reason text not null,created_by uuid not null references erp.app_users(id),created_at timestamptz not null default clock_timestamp(),
 check(period_end>=period_start and period_end-period_start<=366)
);
create table erp.pocket_period_sources(
 pool_id uuid not null references erp.pocket_periods(id),adjustment_id uuid not null references erp.pocket_fabric_usage(adjustment_id),
 original_amount numeric(20,2) not null check(original_amount>=0),primary key(pool_id,adjustment_id)
);
create index pocket_period_source_document on erp.pocket_period_sources(adjustment_id);
create table erp.pocket_period_destinations(
 pool_id uuid not null references erp.pocket_periods(id),event_id uuid not null references erp.sewing_terminal_events(id),
 po_id uuid not null references erp.production_orders(id),contractor_id uuid not null references erp.contractors(id),
 cutting_group_id uuid references erp.cutting_groups(id),sewing_qty bigint not null check(sewing_qty>0),
 preceding_qty bigint not null check(preceding_qty>=0),source_snapshot jsonb not null,primary key(pool_id,event_id)
);
create index pocket_period_destination_event on erp.pocket_period_destinations(event_id);
create index pocket_period_destination_po on erp.pocket_period_destinations(po_id);
create index pocket_period_destination_contractor on erp.pocket_period_destinations(contractor_id);
create index pocket_period_destination_group on erp.pocket_period_destinations(cutting_group_id);
create table erp.pocket_period_events(
 id uuid primary key,pool_id uuid not null references erp.pocket_periods(id),kind text not null check(kind in('POST','RECOST','CANCEL')),
 economic_date date not null,prior_ledger jsonb not null,target_ledger jsonb not null,ledger_delta jsonb not null,
 journal_entry_id uuid unique references erp.journal_entries(id),reason text not null,
 created_by uuid not null references erp.app_users(id),created_at timestamptz not null default clock_timestamp()
);
create index pocket_period_event_pool on erp.pocket_period_events(pool_id);
create unique index pocket_period_one_post on erp.pocket_period_events(pool_id) where kind='POST';
create unique index pocket_period_one_cancel on erp.pocket_period_events(pool_id) where kind='CANCEL';
alter table erp.pocket_periods enable row level security;
alter table erp.pocket_period_sources enable row level security;
alter table erp.pocket_period_destinations enable row level security;
alter table erp.pocket_period_events enable row level security;
revoke all on erp.pocket_periods,erp.pocket_period_sources,erp.pocket_period_destinations,erp.pocket_period_events from public,anon,authenticated,service_role;

create table erp.initial_import_production_sources(
 opening_item_id uuid primary key references erp.opening_balance_items(id) on delete cascade,
 source_row_id uuid not null unique references erp.migration_staging_rows(id),
 batch_id uuid not null references erp.migration_batches(id),
 po_id uuid not null references erp.production_orders(id),size_id uuid not null references erp.sizes(id),
 stage text not null check(stage in('SEWING','LAUNDRY','QC')),
 qty_pcs integer not null check(qty_pcs>0),original_amount numeric(20,2) not null check(original_amount>=0),
 accessory_cost_included boolean not null,bs_case_id uuid unique references erp.bs_cases(id)
);
create index initial_import_production_po on erp.initial_import_production_sources(po_id);
create table erp.initial_import_cost_origins(
 source_row_id uuid primary key references erp.migration_staging_rows(id),
 purchase_item_id uuid not null references erp.material_purchase_items(id),
 opening_item_id uuid not null references erp.opening_balance_items(id),
 material_qty numeric(18,6) not null check(material_qty>0),unit_cost_snapshot numeric(18,6) not null check(unit_cost_snapshot>=0),
 unique(purchase_item_id,opening_item_id)
);
create index initial_import_cost_origin_target on erp.initial_import_cost_origins(opening_item_id);
create table erp.initial_import_origin_cost_events(
 id uuid primary key default gen_random_uuid(),opening_item_id uuid not null references erp.opening_balance_items(id),
 previous_delta numeric(20,2) not null,new_delta numeric(20,2) not null,economic_date date not null,
 journal_entry_id uuid references erp.journal_entries(id),created_at timestamptz not null default clock_timestamp(),
 created_by uuid not null references erp.app_users(id)
);
create index initial_import_origin_cost_event_target on erp.initial_import_origin_cost_events(opening_item_id,created_at,id);
create table erp.initial_import_wip_outputs(
 id uuid primary key default gen_random_uuid(),opening_item_id uuid not null references erp.initial_import_production_sources(opening_item_id),
 lot_id uuid not null unique references erp.fg_lots(id),qty_pcs integer not null check(qty_pcs>0),
 physical_at timestamptz not null,reason text not null,created_at timestamptz not null default clock_timestamp(),
 created_by uuid not null references erp.app_users(id)
);
create index initial_import_wip_output_source on erp.initial_import_wip_outputs(opening_item_id);
create table erp.initial_import_bs_value_events(
 id uuid primary key default gen_random_uuid(),opening_item_id uuid not null references erp.initial_import_production_sources(opening_item_id),
 disposed_qty integer not null check(disposed_qty>=0),previous_amount numeric(20,2) not null,target_amount numeric(20,2) not null,
 economic_date date not null,journal_entry_id uuid references erp.journal_entries(id),
 created_at timestamptz not null default clock_timestamp(),created_by uuid not null references erp.app_users(id)
);
create index initial_import_bs_value_target on erp.initial_import_bs_value_events(opening_item_id,created_at,id);
alter table erp.initial_import_receipt_lines alter column opening_item_id drop not null;
alter table erp.initial_import_production_sources enable row level security;
alter table erp.initial_import_cost_origins enable row level security;
alter table erp.initial_import_origin_cost_events enable row level security;
alter table erp.initial_import_wip_outputs enable row level security;
alter table erp.initial_import_bs_value_events enable row level security;
revoke all on erp.initial_import_production_sources,erp.initial_import_cost_origins,erp.initial_import_origin_cost_events,
 erp.initial_import_wip_outputs,erp.initial_import_bs_value_events from public,anon,authenticated,service_role;

create table erp.initial_import_wip_output_reversals(
 output_id uuid primary key references erp.initial_import_wip_outputs(id),reason text not null,
 physical_at timestamptz not null,created_at timestamptz not null default clock_timestamp(),
 created_by uuid not null references erp.app_users(id)
);
alter table erp.initial_import_wip_output_reversals enable row level security;
revoke all on erp.initial_import_wip_output_reversals from public,anon,authenticated,service_role;

create or replace function erp.accessory_issue_quote_v1(p_material uuid,p_contractor uuid,p_at timestamptz)
returns jsonb language plpgsql stable security definer set search_path='' as $function$
declare m record;p erp.contractor_accessory_price_versions%rowtype;v_factor numeric;
begin
 select x.id,x.material_sku,x.material_name,x.unit_code,c.id category_id,c.category_name
 into m from erp.materials x join erp.accessory_categories c on c.id=x.accessory_category_id
 join erp.uom_definitions u on u.unit_code=x.unit_code
 where x.id=p_material and x.is_active and x.material_type='ACCESSORY' and c.is_active
  and u.is_active and u.dimension='COUNT' and upper(x.unit_code)='PCS' and c.base_uom_code=x.unit_code;
 if m.id is null then return null;end if;
 select * into p from erp.contractor_accessory_price_versions v
 where v.category_id=m.category_id and (v.contractor_id=p_contractor or v.contractor_id is null)
  and v.effective_from<=p_at and (v.effective_to is null or v.effective_to>p_at)
 order by (v.contractor_id is not null) desc,v.effective_from desc,v.id limit 1;
 -- Read the same effective conversion as the native writer without invoking
 -- its internal-only transaction helper from an authorized view-only reader.
 -- The native save still locks and verifies the actual price/factor at write.
 if p.id is not null then
  if upper(p.selling_uom_code)=upper(m.unit_code) then v_factor:=1;
  else
   select base_qty_per_uom into v_factor from erp.accessory_category_uom_conversions
   where category_id=m.category_id and upper(uom_code)=upper(p.selling_uom_code)
    and effective_from<=p_at and (effective_to is null or effective_to>p_at)
   order by effective_from desc limit 1;
   if v_factor is null then raise exception 'No active UOM conversion for category %, UOM %, at %',m.category_id,p.selling_uom_code,p_at;end if;
  end if;
 end if;
 return jsonb_build_object('id',m.id,'sku',m.material_sku,'name',m.material_name,'unit',m.unit_code,
  'category',m.category_name,'price_version_id',p.id,'master_price',p.selling_price::numeric(24,6)::text,
  'price_unit',p.selling_uom_code,'factor',v_factor::numeric(24,6)::text);
end;$function$;
revoke all on function erp.accessory_issue_quote_v1(uuid,uuid,timestamp with time zone) from public,anon,authenticated,service_role;
create or replace function erp.get_accessory_issue_workspace_v1(p_filters jsonb default '{}'::jsonb)
returns jsonb language plpgsql security definer set search_path='' set TimeZone='UTC' as $function$
declare v_contractor uuid:=nullif(p_filters->>'contractor_id','')::uuid;v_location uuid:=nullif(p_filters->>'location_id','')::uuid;
 v_id uuid:=nullif(p_filters->>'id','')::uuid;v_at timestamptz:=coalesce(nullif(p_filters->>'physical_at','')::timestamptz,statement_timestamp());
 v_query text:=lower(btrim(coalesce(p_filters->>'query','')));v_material_query text:=lower(btrim(coalesce(p_filters->>'material_query','')));
 v_result jsonb;v_document jsonb;v_material_ids jsonb:=coalesce(p_filters->'material_ids','[]'::jsonb);
begin
 perform erp.require_permission('finance.contractor_accessory.view');
 perform erp._cp3_assert_closed_json_object(p_filters,array[]::text[],array['contractor_id','location_id','physical_at','id','query','material_query','material_ids'],'accessory workspace filters');
 if length(v_query)>120 or length(v_material_query)>120 then raise exception 'Pencarian terlalu panjang';end if;
 if p_filters?'material_ids' and (jsonb_typeof(p_filters->'material_ids')<>'array' or jsonb_array_length(p_filters->'material_ids')>100) then raise exception 'Daftar aksesori tidak valid';end if;
 if v_id is not null then
  if not exists(select 1 from erp.contractor_material_issues where id=v_id) then raise exception 'Nota tidak ditemukan';end if;
  if not(p_filters?'contractor_id') then select contractor_id into v_contractor from erp.contractor_material_issues where id=v_id;end if;
  if not(p_filters?'location_id') then select location_id into v_location from erp.contractor_material_issues where id=v_id;end if;
  if not(p_filters?'physical_at') then select physical_at into v_at from erp.contractor_material_issues where id=v_id;end if;
  select jsonb_build_object('id',h.id,'number',h.issue_number,'contractor_id',h.contractor_id,'location_id',h.location_id,'po_id',h.po_id,
   'physical_local',to_char(h.physical_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),
   'status',h.status,'row_version',h.row_version::text,'notes',coalesce(h.notes,''),
   'total',coalesce((select sum(i.total_receivable) from erp.contractor_material_issue_items i where i.issue_id=h.id),0)::numeric(24,2)::text,
   'payroll_locked',exists(select 1 from erp.payroll_deductions d join erp.payroll_settlements s on s.id=d.payroll_id
     join erp.contractor_material_issue_items i on i.id=d.contractor_issue_item_id where i.issue_id=h.id and s.status<>'REVERSED'),
   'items',coalesce((select jsonb_agg(jsonb_build_object('id',i.id,'material_id',i.material_id,'sku',m.material_sku,'name',m.material_name,
     'unit',m.unit_code,'qty',i.qty::numeric(24,6)::text,'manual_price',i.manual_retail_unit_price::numeric(24,2)::text,
     'price',i.unit_sale_price_snapshot::numeric(24,6)::text,'factor',i.base_qty_per_transaction_uom::numeric(24,6)::text,
     'price_unit',i.transaction_uom_code,'price_version_id',i.accessory_price_version_id,
     'amount',i.total_receivable::numeric(24,6)::text,'payroll_status',i.payroll_status) order by i.id)
     from erp.contractor_material_issue_items i join erp.materials m on m.id=i.material_id where i.issue_id=h.id),'[]'::jsonb))
  into v_document from erp.contractor_material_issues h where h.id=v_id;
  if not(p_filters?'material_ids') then select coalesce(jsonb_agg(material_id),'[]'::jsonb) into v_material_ids from erp.contractor_material_issue_items where issue_id=v_id;end if;
 end if;
 with history as (
  select h.id,h.issue_number number,c.contractor_name contractor,h.status,h.row_version::text row_version,
   erp._cp3_business_date(h.physical_at) date,
   coalesce((select sum(i.total_receivable) from erp.contractor_material_issue_items i where i.issue_id=h.id),0)::numeric(24,2)::text total
  from erp.contractor_material_issues h join erp.contractors c on c.id=h.contractor_id
  where (v_query='' or strpos(lower(concat_ws(' ',h.issue_number,c.contractor_name)),v_query)>0)
   and not exists(select 1 from erp.contractor_material_issue_items i join erp.materials m on m.id=i.material_id
    join erp.uom_definitions u on u.unit_code=m.unit_code where i.issue_id=h.id and (m.material_type<>'ACCESSORY' or u.dimension<>'COUNT'))
 ), choices as (
  select m.id from erp.materials m join erp.accessory_categories c on c.id=m.accessory_category_id
  join erp.uom_definitions u on u.unit_code=m.unit_code
  where m.material_type='ACCESSORY' and m.is_active and c.is_active and u.is_active and u.dimension='COUNT' and upper(m.unit_code)='PCS' and m.unit_code=c.base_uom_code
   and ((v_material_query='' or strpos(lower(concat_ws(' ',m.material_sku,m.material_name,c.category_name)),v_material_query)>0)
    or m.id::text in(select jsonb_array_elements_text(v_material_ids)))
 ), selected as (
  select x.id,erp.accessory_issue_quote_v1(x.id,v_contractor,v_at) quote,
   coalesce((select sum(s.qty_signed) from erp.material_stock_movements s where s.material_id=x.id and s.location_id=v_location),0)::numeric(24,6)::text stock
  from choices x order by (x.id::text in(select jsonb_array_elements_text(v_material_ids))) desc,x.id limit 100
 ) select jsonb_build_object(
  'contractor_id',v_contractor,'location_id',v_location,
  'physical_local',to_char(v_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),
  'filters',p_filters,'document',v_document,'history_count',(select count(*) from history),'material_count',(select count(*) from choices),
  'history',coalesce((select jsonb_agg(to_jsonb(x) order by x.date desc,x.id) from(select * from history order by date desc,id limit 50)x),'[]'::jsonb),
  'materials',coalesce((select jsonb_agg(quote||jsonb_build_object('stock',stock) order by quote->>'name',id) from selected),'[]'::jsonb),
  'contractors',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',contractor_name) order by contractor_name,id) from erp.contractors where is_active and contractor_type='MANDOR'),'[]'::jsonb),
  'locations',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',location_name) order by location_name,id) from erp.locations where is_active and location_type='RAW_MATERIAL_WAREHOUSE'),'[]'::jsonb),
  'orders',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',po_number) order by po_number,id) from erp.production_orders where contractor_id=v_contractor and status not in('FINISHED','CANCELLED')),'[]'::jsonb)
 ) into v_result;
 return v_result;
end;$function$;
revoke all on function erp.get_accessory_issue_workspace_v1(jsonb) from public,anon,authenticated,service_role;
create or replace function erp.save_accessory_issue_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
returns jsonb language plpgsql security definer set search_path='' set TimeZone='UTC' as $function$
declare v_action text:=upper(btrim(p_action));v_cached jsonb;v_result jsonb;v_native jsonb;v_line jsonb;v_quote jsonb;
 v_id uuid;v_version bigint;v_contractor uuid;v_location uuid;v_po uuid;v_at timestamptz;v_reason text;v_items jsonb:='[]'::jsonb;
 h erp.contractor_material_issues%rowtype;
begin
 perform erp.require_permission('finance.contractor_accessory.view');
 if v_action not in('SAVE_DRAFT','POST','DELETE','REVERSE') or v_action is null then raise exception 'Tindakan nota tidak dikenal';end if;
 if v_action in('SAVE_DRAFT','POST','DELETE') then perform erp.require_permission('finance.contractor_accessory.create');end if;
 if v_action='POST' then perform erp.require_permission('finance.contractor_accessory.post');end if;
 if v_action='REVERSE' then perform erp.require_owner_admin();perform erp.require_permission('finance.contractor_accessory.reverse');end if;
 perform erp.require_internal();
 perform erp._cp3_assert_closed_json_object(p_payload,array['reason'],array['id','expected_version','number','contractor_id','location_id','po_id','physical_at','notes','items','reason'],'accessory issue payload');
 if jsonb_typeof(p_payload->'reason')<>'string' or nullif(btrim(p_payload->>'reason'),'') is null or length(p_payload->>'reason')>1000 then raise exception 'Alasan nota wajib diisi';end if;
 v_reason:=btrim(p_payload->>'reason');v_id:=nullif(p_payload->>'id','')::uuid;
 if p_payload->>'expected_version' is not null and (jsonb_typeof(p_payload->'expected_version')<>'string' or (p_payload->>'expected_version')!~'^[1-9][0-9]{0,18}$') then raise exception 'Versi nota wajib berupa teks bilangan bulat';end if;
 v_version:=(p_payload->>'expected_version')::bigint;
 v_cached:=erp._idempotency_begin('save_accessory_issue_action_v1',p_client_request_id,erp._request_hash(jsonb_build_object('action',v_action,'payload',p_payload)));
 if v_cached is not null then return v_cached;end if;
 if v_id is not null then
  select * into h from erp.contractor_material_issues where id=v_id for update;
  if h.id is null then raise exception 'Nota tidak ditemukan';end if;
  if v_version is null or h.row_version<>v_version then raise exception 'STALE_VERSION: nota berubah, muat ulang';end if;
  if exists(select 1 from erp.contractor_material_issue_items i join erp.materials m on m.id=i.material_id
   join erp.uom_definitions u on u.unit_code=m.unit_code where i.issue_id=v_id and (m.material_type<>'ACCESSORY' or u.dimension<>'COUNT')) then raise exception 'Form ini hanya untuk nota aksesori hitung';end if;
 elsif v_version is not null or v_action in('DELETE','REVERSE') then raise exception 'Identitas dan versi nota tidak cocok';end if;
 if v_action in('SAVE_DRAFT','POST') then
  if v_id is not null and h.status<>'DRAFT' then raise exception 'Nota disahkan tidak dapat diedit';end if;
  if jsonb_typeof(p_payload->'number') is distinct from 'string' or nullif(btrim(p_payload->>'number'),'') is null or length(p_payload->>'number')>60 then raise exception 'Nomor nota wajib diisi';end if;
  if jsonb_typeof(p_payload->'physical_at') is distinct from 'string' or (p_payload->>'physical_at')!~'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+07:00$' then raise exception 'Waktu pengambilan wajib memakai tanggal dan jam WIB';end if;
  v_at:=(p_payload->>'physical_at')::timestamptz;
  if (to_char(v_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')||'+07:00')<>(p_payload->>'physical_at')
   or erp._cp3_business_date(v_at)>erp._cp3_business_date(statement_timestamp()) then raise exception 'Tanggal pengambilan tidak valid atau di masa depan';end if;
  v_contractor:=(p_payload->>'contractor_id')::uuid;v_location:=(p_payload->>'location_id')::uuid;v_po:=nullif(p_payload->>'po_id','')::uuid;
  if not exists(select 1 from erp.contractors where id=v_contractor and is_active and contractor_type='MANDOR') then raise exception 'Pilih mandor aktif';end if;
  if not exists(select 1 from erp.locations where id=v_location and is_active and location_type='RAW_MATERIAL_WAREHOUSE') then raise exception 'Pilih gudang bahan aktif';end if;
  if v_po is not null then
   perform 1 from erp.production_orders where id=v_po and contractor_id=v_contractor and status not in('FINISHED','CANCELLED') for update;
   if not found then raise exception 'PO harus aktif dan milik mandor yang sama';end if;
  end if;
  if jsonb_typeof(p_payload->'items') is distinct from 'array' then raise exception 'Rincian aksesori wajib diisi';end if;
  if jsonb_array_length(p_payload->'items') not between 1 and 100 then raise exception 'Isi 1 sampai 100 aksesori';end if;
  if exists(select 1 from jsonb_array_elements(p_payload->'items') x group by x->>'material_id' having count(*)>1) then raise exception 'Aksesori yang sama tidak boleh dua baris';end if;
  for v_line in select value from jsonb_array_elements(p_payload->'items') loop
   perform erp._cp3_assert_closed_json_object(v_line,array['material_id','qty','mode'],array['material_id','qty','mode','manual_price','price_version_id','factor'],'accessory issue line');
   if jsonb_typeof(v_line->'qty') is distinct from 'string' or (v_line->>'qty')!~'^[1-9][0-9]{0,11}$' then raise exception 'Jumlah aksesori harus PCS utuh positif';end if;
   v_quote:=erp.accessory_issue_quote_v1((v_line->>'material_id')::uuid,v_contractor,v_at);
   if v_quote is null then raise exception 'Aksesori hitung aktif tidak ditemukan';end if;
   if v_line->>'mode'='MANUAL' then
    if jsonb_typeof(v_line->'manual_price') is distinct from 'string' or (v_line->>'manual_price')!~'^[0-9]{1,12}(\.[0-9]{1,2})?$' then raise exception 'Harga eceran wajib nominal nonnegatif, maksimal dua desimal';end if;
    v_items:=v_items||jsonb_build_array(jsonb_build_object('material_id',v_line->>'material_id','qty',v_line->>'qty','manual_retail_unit_price',v_line->>'manual_price'));
   elsif v_line->>'mode'='MASTER' then
    if v_line->>'manual_price' is not null then raise exception 'Pilih satu dasar harga';end if;
    if v_quote->>'price_version_id' is null or v_line->>'price_version_id' is distinct from v_quote->>'price_version_id'
     or v_line->>'factor' is distinct from v_quote->>'factor' then raise exception 'STALE_PRICE: harga master berubah atau belum tersedia, muat ulang';end if;
    v_items:=v_items||jsonb_build_array(jsonb_build_object('material_id',v_line->>'material_id','qty',v_line->>'qty'));
   else raise exception 'Pilih harga master atau eceran per pcs';end if;
  end loop;
  v_native:=erp.save_contractor_material_issue_draft_v2(jsonb_build_object('id',v_id,'issue_number',btrim(p_payload->>'number'),
   'contractor_id',v_contractor,'location_id',v_location,'po_id',v_po,'physical_at',v_at,'notes',p_payload->>'notes','change_reason',v_reason,'items',v_items),p_client_request_id,v_version);
  v_id:=(v_native->>'contractor_material_issue_id')::uuid;
  -- Native save takes the configured-price locks. Verify the actually selected
  -- versions there, so a concurrent tariff/conversion edit cannot pass preview.
  if exists(select 1 from jsonb_array_elements(p_payload->'items') x
   join erp.contractor_material_issue_items i on i.issue_id=v_id and i.material_id=(x->>'material_id')::uuid
   where x->>'mode'='MASTER' and (i.accessory_price_version_id::text is distinct from x->>'price_version_id'
    or i.base_qty_per_transaction_uom is distinct from (x->>'factor')::numeric)) then
   raise exception 'STALE_PRICE: harga master berubah, muat ulang';end if;
  if v_action='POST' then v_native:=erp.post_contractor_material_issue_v2(v_id,p_client_request_id,(v_native->>'row_version')::bigint,v_reason);end if;
 elsif v_action='DELETE' then
  v_native:=erp.save_contractor_material_issue_draft_v2(jsonb_build_object('id',v_id,'action','DELETE','change_reason',v_reason),p_client_request_id,v_version);
 else v_native:=erp.reverse_contractor_material_issue_v2(v_id,v_reason,p_client_request_id,v_version);
 end if;
 select * into h from erp.contractor_material_issues where id=v_id;
 v_result:=jsonb_build_object('id',v_id,'action',v_action,'request_id',p_client_request_id,'status',case when v_action='DELETE' then 'DELETED' else h.status end,'row_version',h.row_version::text);
 return erp._idempotency_complete('save_accessory_issue_action_v1',p_client_request_id,v_result);
end;$function$;
revoke all on function erp.save_accessory_issue_action_v1(text,jsonb,uuid) from public,anon,authenticated,service_role;
create or replace function public.erp_get_accessory_issue_workspace_v1(p_filters jsonb default '{}'::jsonb) returns jsonb language sql security definer set search_path='' as $function$ select erp.get_accessory_issue_workspace_v1(p_filters);$function$;
revoke all on function public.erp_get_accessory_issue_workspace_v1(jsonb) from public,anon,authenticated,service_role;
grant execute on function public.erp_get_accessory_issue_workspace_v1(jsonb) to authenticated,service_role;
create or replace function public.erp_save_accessory_issue_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid) returns jsonb language sql security definer set search_path='' as $function$ select erp.save_accessory_issue_action_v1(p_action,p_payload,p_client_request_id);$function$;
revoke all on function public.erp_save_accessory_issue_action_v1(text,jsonb,uuid) from public,anon,authenticated,service_role;
grant execute on function public.erp_save_accessory_issue_action_v1(text,jsonb,uuid) to authenticated,service_role;
create or replace function erp.pocket_period_lock_v1() returns void
language plpgsql security definer set search_path='' as $function$
begin
 if not pg_try_advisory_xact_lock(hashtextextended('POCKET_HPP_PERIOD_V1',0)) then
  raise exception 'POCKET_PERIOD_BUSY: alokasi kain kantong sedang berubah. Coba kembali dengan data terbaru';end if;
end;$function$;
revoke all on function erp.pocket_period_lock_v1() from public,anon,authenticated,service_role;
create or replace function erp.pocket_period_active_v1(p_pool uuid) returns boolean
language sql stable security definer set search_path='' as $function$
 select exists(select 1 from erp.pocket_periods p where p.id=p_pool)
 and not exists(select 1 from erp.pocket_period_events e where e.pool_id=p_pool and e.kind='CANCEL');
$function$;
revoke all on function erp.pocket_period_active_v1(uuid) from public,anon,authenticated,service_role;
create or replace function erp.pocket_period_total_v1(p_pool uuid) returns numeric
language sql stable security definer set search_path='' as $function$
 select coalesce(sum(-((erp._cp6_material_adjustment_revaluation_state(s.adjustment_id)->>'current_value')::numeric)),0)::numeric(20,2)
 from erp.pocket_period_sources s where s.pool_id=p_pool;
$function$;
revoke all on function erp.pocket_period_total_v1(uuid) from public,anon,authenticated,service_role;
create or replace function erp.pocket_period_amount_v1(p_pool uuid,p_before bigint,p_qty bigint) returns numeric
language sql stable security definer set search_path='' as $function$
 select case when erp.pocket_period_active_v1(p_pool) then
 round(erp.pocket_period_total_v1(p_pool)*(p_before+p_qty)/p.denominator,2)
 -round(erp.pocket_period_total_v1(p_pool)*p_before/p.denominator,2) else 0 end
 from erp.pocket_periods p where p.id=p_pool;
$function$;
revoke all on function erp.pocket_period_amount_v1(uuid,bigint,bigint) from public,anon,authenticated,service_role;
create or replace function erp.pocket_period_manifest_v1(p_start date,p_end date) returns jsonb
language sql stable security definer set search_path='' set TimeZone='UTC' as $function$
 with sources as(
  select u.adjustment_id,h.row_version::text version,erp._cp3_business_date(h.physical_at) date,
   u.material_id,u.roll_id,u.issued_quantity::text quantity,
   (-((erp._cp6_material_adjustment_revaluation_state(h.id)->>'current_value')::numeric))::numeric(20,2)::text amount
  from erp.pocket_fabric_usage u join erp.material_adjustments h on h.id=u.adjustment_id
  where h.status='POSTED' and erp._cp3_business_date(h.physical_at) between p_start and p_end
 ), destinations as(
  select e.id event_id,e.po_id,e.contractor_id,e.cutting_group_id,e.qty_signed::bigint sewing_qty,
   coalesce(sum(e.qty_signed) over(order by e.physical_at,e.id rows between unbounded preceding and 1 preceding),0)::bigint preceding_qty,
   to_jsonb(e) source_snapshot
  from erp.sewing_terminal_events e join erp.work_completion_events w on w.id=e.source_work_completion_id
  where e.event_kind='SELESAI_DIJAHIT' and e.qty_signed>0 and w.status='POSTED'
   and erp._cp3_business_date(e.physical_at) between p_start and p_end
   and not exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=e.id)
 ) select jsonb_build_object('period_start',p_start,'period_end',p_end,
  'sources',coalesce((select jsonb_agg(to_jsonb(s) order by adjustment_id) from sources s),'[]'::jsonb),
  'destinations',coalesce((select jsonb_agg(to_jsonb(d) order by preceding_qty,event_id) from destinations d),'[]'::jsonb),
  'amount',coalesce((select sum(amount::numeric) from sources),0)::numeric(20,2)::text,
  'quantity',coalesce((select sum(sewing_qty) from destinations),0)::bigint::text,
  'blocked_by',coalesce((select jsonb_agg(p.id order by p.id) from erp.pocket_periods p
   where erp.pocket_period_active_v1(p.id) and p.period_start<=p_end and p.period_end>=p_start),'[]'::jsonb));
$function$;
revoke all on function erp.pocket_period_manifest_v1(date,date) from public,anon,authenticated,service_role;
create or replace function erp.pocket_period_state_v1(p_pool uuid) returns jsonb
language sql stable security definer set search_path='' set TimeZone='UTC' as $function$
 select jsonb_build_object('id',p.id,'period_start',p.period_start,'period_end',p.period_end,'reason',p.reason,
  'status',case when erp.pocket_period_active_v1(p.id) then 'ACTIVE' else 'CANCELLED' end,
  'quantity',p.denominator::text,'original_amount',p.original_amount::text,
  'current_amount',(case when erp.pocket_period_active_v1(p.id) then erp.pocket_period_total_v1(p.id) else 0 end)::numeric(20,2)::text,
  'per_piece',(case when erp.pocket_period_active_v1(p.id) then erp.pocket_period_total_v1(p.id)/p.denominator else 0 end)::numeric(24,6)::text,
  'revision',encode(extensions.digest(convert_to(jsonb_build_object('pool',to_jsonb(p),'events',
   (select jsonb_agg(to_jsonb(e) order by e.created_at,e.id) from erp.pocket_period_events e where e.pool_id=p.id),
   'value',erp.pocket_period_total_v1(p.id))::text,'UTF8'),'sha256'),'hex'))
 from erp.pocket_periods p where p.id=p_pool;
$function$;
revoke all on function erp.pocket_period_state_v1(uuid) from public,anon,authenticated,service_role;
create or replace function erp.pocket_period_target_v1(p_pool uuid,p_cancel boolean default false) returns jsonb
language sql stable security definer set search_path='' as $function$
 with values_by_key as(
  select 'WIP|'||d.po_id::text key,sum(erp.pocket_period_amount_v1(d.pool_id,d.preceding_qty,d.sewing_qty)) amount
  from erp.pocket_period_destinations d where d.pool_id=p_pool group by d.po_id
  union all select 'OTHER_EXPENSE',-erp.pocket_period_total_v1(p_pool)
 ) select case when p_cancel or not erp.pocket_period_active_v1(p_pool) then '{}'::jsonb else
 coalesce((select jsonb_object_agg(key,amount) from values_by_key where amount<>0),'{}'::jsonb) end;
$function$;
revoke all on function erp.pocket_period_target_v1(uuid,boolean) from public,anon,authenticated,service_role;
create or replace function erp.pocket_period_book_v1(p_pool uuid) returns jsonb
language sql stable security definer set search_path='' as $function$
 with sums as(
  select case when l.account_id=erp.account_id('WIP') and l.po_id is not null then 'WIP|'||l.po_id::text
   when l.account_id=erp.account_id('OTHER_EXPENSE') and l.po_id is null then 'OTHER_EXPENSE'
   else 'INVALID|'||l.account_id::text||'|'||coalesce(l.po_id::text,'') end key,sum(l.debit-l.credit) amount
  from erp.pocket_period_events e join erp.journal_entries j on j.id=e.journal_entry_id
   join erp.journal_lines l on l.journal_entry_id=j.id where e.pool_id=p_pool group by 1
 ) select coalesce(jsonb_object_agg(key,amount) filter(where amount<>0),'{}'::jsonb) from sums;
$function$;
revoke all on function erp.pocket_period_book_v1(uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.pocket_lot_cost_v1(p_lot_id uuid)
 RETURNS numeric
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
with target as(
  select fl.id,fl.po_id,coalesce(fl.cutting_group_id,qi.cutting_group_id) group_id,
    fl.initial_qty_pcs::numeric lot_qty,fl.produced_at
  from erp.fg_lots fl
  left join erp.qc_inspection_items qi on qi.id=fl.qc_item_id
  where fl.id=p_lot_id and fl.lot_origin='PRODUCTION'
), position as(
  select t.*,
    coalesce((select sum(x.initial_qty_pcs)::numeric from erp.fg_lots x
      left join erp.qc_inspection_items xqi on xqi.id=x.qc_item_id
      where x.po_id=t.po_id and x.lot_origin='PRODUCTION'
        and coalesce(x.cutting_group_id,xqi.cutting_group_id)=t.group_id
        and (x.produced_at,x.id)<(t.produced_at,t.id)),0) group_start,
    coalesce((select sum(x.initial_qty_pcs)::numeric from erp.fg_lots x
      where x.po_id=t.po_id and x.lot_origin='PRODUCTION'
        and (x.produced_at,x.id)<(t.produced_at,t.id)),0) po_start
  from target t
), terminal as(
  select e.id,e.po_id,e.cutting_group_id,e.qty_signed::numeric event_qty,
    coalesce(sum(e.qty_signed) over(
      partition by e.po_id,e.cutting_group_id
      order by e.physical_at,e.id rows between unbounded preceding and 1 preceding
    ),0)::numeric group_start,
    coalesce(sum(e.qty_signed) over(
      partition by e.po_id
      order by e.physical_at,e.id rows between unbounded preceding and 1 preceding
    ),0)::numeric po_start
  from erp.sewing_terminal_events e join position p on p.po_id=e.po_id
  where e.event_kind='SELESAI_DIJAHIT' and e.qty_signed>0
    and not exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=e.id)
), alloc as(
  select a.cutting_group_id,a.sewing_qty::numeric source_qty,erp.pocket_period_amount_v1(a.pool_id,a.preceding_qty,a.sewing_qty)::numeric source_cost,
    case when a.cutting_group_id is null then t.po_start else t.group_start end source_start
  from position p
  join erp.pocket_period_destinations a on a.po_id=p.po_id
    and (a.cutting_group_id=p.group_id or a.cutting_group_id is null)
  join erp.pocket_periods hp on hp.id=a.pool_id and erp.pocket_period_active_v1(hp.id)
  join terminal t on t.id=a.event_id
)
select coalesce(sum(
  greatest(least(
    case when a.cutting_group_id is null then p.po_start+p.lot_qty else p.group_start+p.lot_qty end,
    a.source_start+a.source_qty
  )-greatest(
    case when a.cutting_group_id is null then p.po_start else p.group_start end,
    a.source_start
  ),0)*a.source_cost/nullif(a.source_qty,0)
),0)::numeric
from position p left join alloc a on true
$function$;
revoke all on function erp.pocket_lot_cost_v1(uuid) from public,anon,authenticated,service_role;
create or replace function erp.preview_pocket_period_v1(p_start date,p_end date) returns jsonb
language plpgsql stable security definer set search_path='' set TimeZone='UTC' as $function$
declare m jsonb;q numeric;v numeric;
begin
 perform erp.require_owner_admin();perform erp.require_permission('warehouse.stock.adjust');perform erp.require_permission('finance.hpp.manage');
 if p_start is null or p_end is null or p_end<p_start or p_end-p_start>366
  or p_end>erp._cp3_business_date(statement_timestamp()) then raise exception 'Pilih periode yang valid, maksimal 367 hari sampai hari ini';end if;
 m:=erp.pocket_period_manifest_v1(p_start,p_end);q:=(m->>'quantity')::numeric;v:=(m->>'amount')::numeric;
 return jsonb_build_object('period_start',p_start,'period_end',p_end,'amount',m->>'amount','quantity',m->>'quantity',
  'source_count',jsonb_array_length(m->'sources'),'per_piece',(case when q>0 then v/q else 0 end)::numeric(24,6)::text,
  'blocked',jsonb_array_length(m->'blocked_by')>0,'can_post',q>0 and v>0 and jsonb_array_length(m->'blocked_by')=0,
  'revision',encode(extensions.digest(convert_to(m::text,'UTF8'),'sha256'),'hex'));
end;$function$;
revoke all on function erp.preview_pocket_period_v1(date,date) from public,anon,authenticated,service_role;
create or replace function erp.sync_pocket_period_v1(p_pool uuid,p_date date,p_kind text,p_reason text) returns void
language plpgsql security definer set search_path='' as $function$
declare target jsonb;book jsonb;delta jsonb;lines jsonb;ident uuid:=gen_random_uuid();journal uuid;v_po uuid;v_book_date date;
begin
 perform erp.require_internal();perform erp.pocket_period_lock_v1();
 if p_kind not in('POST','RECOST','CANCEL') or p_date is null or nullif(btrim(p_reason),'') is null then raise exception 'Invalid pocket allocation sync';end if;
 if not erp.pocket_period_active_v1(p_pool) then raise exception 'Alokasi periode sudah dibatalkan';end if;
 target:=erp.pocket_period_target_v1(p_pool,p_kind='CANCEL');book:=erp.pocket_period_book_v1(p_pool);
 select coalesce(jsonb_object_agg(k,amount),'{}'::jsonb) into delta from(
  select coalesce(t.key,b.key) k,coalesce(t.value::numeric,0)-coalesce(b.value::numeric,0) amount
  from jsonb_each_text(target) t full join jsonb_each_text(book) b using(key)) x where amount<>0;
 if delta='{}'::jsonb and p_kind='RECOST' then return;end if;
 if delta<>'{}'::jsonb then
  select jsonb_agg(jsonb_build_object('mapping_key',split_part(key,'|',1),
   'po_id',nullif(split_part(key,'|',2),''),'debit',greatest(value::numeric,0),'credit',greatest(-value::numeric,0)) order by key)
  into lines from jsonb_each_text(delta);
  journal:=erp.post_journal('POCKET_HPP_PERIOD',ident,p_date,p_reason,lines);
  select transaction_date into v_book_date from erp.journal_entries where id=journal;
 end if;
 insert into erp.pocket_period_events(id,pool_id,kind,economic_date,prior_ledger,target_ledger,ledger_delta,journal_entry_id,reason,created_by)
 values(ident,p_pool,p_kind,p_date,book,target,delta,journal,p_reason,erp.current_app_user_id());
 for v_po in select distinct po_id from erp.pocket_period_destinations where pool_id=p_pool order by po_id loop
  perform erp.rebuild_po_hpp(v_po,p_reason);perform erp.propagate_conversion_hpp_for_po(v_po);
  perform erp.sync_po_hpp_to_gl(v_po,p_date);
  if exists(select 1 from erp.production_orders where id=v_po and status='FINISHED') then
   perform erp.sync_finished_po_wip_residual(v_po,coalesce(v_book_date,p_date),p_reason);end if;
 end loop;
 if erp.pocket_period_book_v1(p_pool) is distinct from target then raise exception 'Pocket allocation ledger mismatch';end if;
end;$function$;
revoke all on function erp.sync_pocket_period_v1(uuid,date,text,text) from public,anon,authenticated,service_role;
create or replace function erp.save_pocket_period_action_v1(p_action text,p_payload jsonb,p_request uuid) returns jsonb
language plpgsql security definer set search_path='' set TimeZone='UTC' set DateStyle='ISO, YMD' as $function$
declare cached jsonb;m jsonb;v jsonb;r jsonb;ident uuid;start_day date;end_day date;reason text;
begin
 perform erp.require_owner_admin();perform erp.require_permission('warehouse.stock.adjust');perform erp.require_permission('finance.hpp.manage');
 if p_action not in('POST_PERIOD','CANCEL_PERIOD') or jsonb_typeof(p_payload) is distinct from 'object'
  or octet_length(p_payload::text)>10000 then raise exception 'Data alokasi periode tidak valid';end if;
 reason:=nullif(btrim(p_payload->>'reason'),'');if reason is null or length(reason)>1000 then raise exception 'Alasan wajib diisi, maksimal 1000 karakter';end if;
 cached:=erp._idempotency_begin('save_pocket_fabric_action_v1',p_request,erp._request_hash(jsonb_build_object('action',p_action,'payload',p_payload)));
 if cached is not null then return cached;end if;
 perform erp.pocket_period_lock_v1();perform set_config('app.change_reason',reason,true);
 if p_action='POST_PERIOD' then
  if coalesce(p_payload->>'period_start','') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
   or coalesce(p_payload->>'period_end','') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'Tanggal periode wajib YYYY-MM-DD';end if;
  start_day:=(p_payload->>'period_start')::date;end_day:=(p_payload->>'period_end')::date;
  v:=erp.preview_pocket_period_v1(start_day,end_day);
  if not (v->>'can_post')::boolean then raise exception 'Periode memerlukan biaya dan hasil jahit positif serta tidak boleh tumpang tindih';end if;
  if v->>'revision' is distinct from p_payload->>'expected_revision' then raise exception 'STALE_VERSION: sumber biaya atau hasil jahit berubah; lihat pembagian terbaru';end if;
  perform erp._cp3_lock_business_period(start_day,end_day);
  m:=erp.pocket_period_manifest_v1(start_day,end_day);ident:=gen_random_uuid();
  insert into erp.pocket_periods(id,period_start,period_end,manifest,denominator,original_amount,reason,created_by)
  values(ident,start_day,end_day,m,(m->>'quantity')::bigint,(m->>'amount')::numeric,reason,erp.current_app_user_id());
  insert into erp.pocket_period_sources(pool_id,adjustment_id,original_amount)
  select ident,(x->>'adjustment_id')::uuid,(x->>'amount')::numeric from jsonb_array_elements(m->'sources') x;
  insert into erp.pocket_period_destinations(pool_id,event_id,po_id,contractor_id,cutting_group_id,sewing_qty,preceding_qty,source_snapshot)
  select ident,(x->>'event_id')::uuid,(x->>'po_id')::uuid,(x->>'contractor_id')::uuid,(x->>'cutting_group_id')::uuid,
   (x->>'sewing_qty')::bigint,(x->>'preceding_qty')::bigint,x->'source_snapshot' from jsonb_array_elements(m->'destinations') x;
  perform erp.sync_pocket_period_v1(ident,end_day,'POST',reason);
 else
  ident:=(p_payload->>'id')::uuid;v:=erp.pocket_period_state_v1(ident);
  if v is null or v->>'status'<>'ACTIVE' then raise exception 'Pilih alokasi periode yang aktif';end if;
  if v->>'revision' is distinct from p_payload->>'expected_revision' then raise exception 'STALE_VERSION: alokasi periode berubah';end if;
  perform erp.sync_pocket_period_v1(ident,erp._cp3_business_date(statement_timestamp()),'CANCEL',reason);
 end if;
 insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
 values('pocket_periods',ident,case when p_action='POST_PERIOD' then 'POST' else 'REVERSE' end,erp.current_app_user_id(),reason);
 r:=jsonb_build_object('request_id',p_request,'action',p_action,'id',ident,'status',case when p_action='POST_PERIOD' then 'ACTIVE' else 'CANCELLED' end);
 return erp._idempotency_complete('save_pocket_fabric_action_v1',p_request,r);
end;$function$;
revoke all on function erp.save_pocket_period_action_v1(text,jsonb,uuid) from public,anon,authenticated,service_role;
create or replace function erp.guard_pocket_period_v1() returns trigger
language plpgsql security definer set search_path='' as $function$
declare v_pool uuid;v_date date;v_po uuid;v_prior uuid;
begin
 if tg_table_name in('pocket_periods','pocket_period_sources','pocket_period_destinations','pocket_period_events') then
  raise exception 'Riwayat alokasi periode tetap; gunakan pembatalan tertaut';end if;
 if tg_table_name='material_stock_movements' then
 if new.reversal_of_id is null or not exists(
  select 1 from erp.material_stock_movements m join erp.material_adjustment_items i on i.id=m.source_id and m.source_type='MATERIAL_ADJUSTMENT_ITEM'
  join erp.pocket_fabric_usage u on u.adjustment_id=i.adjustment_id where m.id=new.reversal_of_id) then return new;end if;
 elsif tg_table_name='material_adjustment_revaluation_facts' then
  if not exists(select 1 from erp.pocket_fabric_usage where adjustment_id=new.adjustment_id) then return new;end if;
 elsif tg_table_name='work_completion_events' then
  if old.status<>'POSTED' or new.status='POSTED' then return new;end if;
 end if;
 perform erp.pocket_period_lock_v1();
 if tg_table_name='material_adjustment_revaluation_facts' then
  for v_pool in select s.pool_id from erp.pocket_period_sources s where s.adjustment_id=new.adjustment_id and erp.pocket_period_active_v1(s.pool_id) order by s.pool_id loop
   perform erp.sync_pocket_period_v1(v_pool,new.effective_date,'RECOST','Koreksi harga kain kantong');end loop;
 elsif tg_table_name='pocket_fabric_usage' then
  select erp._cp3_business_date(physical_at) into v_date from erp.material_adjustments where id=new.adjustment_id;
  if exists(select 1 from erp.pocket_periods p where erp.pocket_period_active_v1(p.id) and v_date between p.period_start and p.period_end) then
   raise exception 'Batalkan alokasi periode sebelum menambah pengeluaran di periode itu';end if;
 elsif tg_table_name='material_stock_movements' then
  if new.reversal_of_id is not null and exists(select 1 from erp.material_stock_movements m
   join erp.material_adjustment_items i on i.id=m.source_id and m.source_type='MATERIAL_ADJUSTMENT_ITEM'
   join erp.pocket_period_sources s on s.adjustment_id=i.adjustment_id
   where m.id=new.reversal_of_id and erp.pocket_period_active_v1(s.pool_id)) then
   raise exception 'Batalkan alokasi periode sebelum membatalkan pengeluaran kain kantong';end if;
 elsif tg_table_name in('sewing_terminal_events','work_completion_events') then
  if tg_table_name='work_completion_events' then
   if old.status<>'POSTED' or new.status='POSTED' then return new;end if;
   v_date:=erp._cp3_business_date(old.physical_at);v_po:=old.po_id;
  else
   v_date:=erp._cp3_business_date(new.physical_at);v_po:=new.po_id;v_prior:=new.reversal_of_id;
   if v_prior is not null then select erp._cp3_business_date(physical_at) into v_date from erp.sewing_terminal_events where id=v_prior;end if;
  end if;
  if exists(select 1 from erp.pocket_periods p where erp.pocket_period_active_v1(p.id) and
   (v_date between p.period_start and p.period_end or exists(select 1 from erp.pocket_period_destinations d
    join erp.sewing_terminal_events e on e.id=d.event_id where d.pool_id=p.id and d.po_id=v_po and erp._cp3_business_date(e.physical_at)>=v_date))) then
   raise exception 'Batalkan alokasi kain kantong terkait sebelum mengoreksi hasil jahit';end if;
 end if;
 return new;
end;$function$;
revoke all on function erp.guard_pocket_period_v1() from public,anon,authenticated,service_role;
create or replace function erp.pocket_period_checks_v1()
returns table(check_name text,severity text,issue_count bigint,details text)
language sql stable security definer set search_path='' set TimeZone='UTC' as $function$
 select 'AP_PERIOD_POCKET_LEDGER'::text,'CRITICAL'::text,count(*),'Period funding matches current source value and cancellation'::text
 from erp.pocket_periods p where erp.pocket_period_book_v1(p.id) is distinct from erp.pocket_period_target_v1(p.id,false)
 union all select 'AP_PERIOD_POCKET_SOURCES','CRITICAL',count(*),'Source membership and original snapshots remain conserved'
 from erp.pocket_periods p where (select sum(s.original_amount) from erp.pocket_period_sources s where s.pool_id=p.id) is distinct from p.original_amount
  or (select count(*) from erp.pocket_period_sources where pool_id=p.id)<>jsonb_array_length(p.manifest->'sources')
  or (select sum(d.sewing_qty) from erp.pocket_period_destinations d where d.pool_id=p.id) is distinct from p.denominator
  or (select count(*) from erp.pocket_period_destinations where pool_id=p.id)<>jsonb_array_length(p.manifest->'destinations')
  or exists(select 1 from erp.pocket_period_destinations d join erp.sewing_terminal_events e on e.id=d.event_id
    where d.pool_id=p.id and (to_jsonb(e)<>d.source_snapshot or (erp.pocket_period_active_v1(p.id) and
     exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=e.id))))
 union all select 'AP_PERIOD_POCKET_OVERLAP','CRITICAL',count(*),'Active allocation periods never overlap'
 from erp.pocket_periods p join erp.pocket_periods q on p.id<q.id and p.period_start<=q.period_end and p.period_end>=q.period_start
 where erp.pocket_period_active_v1(p.id) and erp.pocket_period_active_v1(q.id)
 union all select 'AP_PERIOD_POCKET_HPP','CRITICAL',count(*),'Current lot HPP includes the exact period source share'
 from erp.fg_lots l join erp.hpp_versions h on h.lot_id=l.id and h.is_current
 where l.lot_origin='PRODUCTION' and exists(select 1 from erp.pocket_period_destinations d where d.po_id=l.po_id)
 and abs(erp.pocket_lot_cost_v1(l.id)-coalesce((select sum(c.total_cost) from erp.hpp_version_components c
  where c.hpp_version_id=h.id and c.source_type='POCKET_PERIOD_ALLOCATION'),0))>0.000001;
$function$;
revoke all on function erp.pocket_period_checks_v1() from public,anon,authenticated,service_role;
create or replace function public.erp_preview_pocket_fabric_period_v1(p_period_start date,p_period_end date) returns jsonb language sql stable security definer set search_path='' as $function$ select erp.preview_pocket_period_v1(p_period_start,p_period_end);$function$;
revoke all on function public.erp_preview_pocket_fabric_period_v1(date,date) from public,anon,authenticated,service_role;
grant execute on function public.erp_preview_pocket_fabric_period_v1(date,date) to authenticated,service_role;
create or replace function erp.pocket_fabric_roll_revision_v1(p_roll uuid)
returns text language sql stable security definer set search_path='' set TimeZone='UTC' as $function$
 select encode(extensions.digest(convert_to(jsonb_build_object(
 'roll',(select to_jsonb(r) from erp.material_rolls r where id=p_roll),
 'movements',(select jsonb_agg(to_jsonb(m) order by m.id) from erp.material_stock_movements m where roll_id=p_roll)
 )::text,'UTF8'),'sha256'),'hex');
$function$;
revoke all on function erp.pocket_fabric_roll_revision_v1(uuid) from public,anon,authenticated,service_role;
create or replace function erp.guard_pocket_fabric_v1()
returns trigger language plpgsql security definer set search_path='' as $function$
declare v_material uuid;v_adjustment uuid;
begin
 if tg_table_name in('pocket_fabric_materials','pocket_fabric_usage') then
  raise exception 'Riwayat kain kantong tetap; gunakan pembatalan tertaut';
 elsif tg_table_name='cutting_group_rolls' then
  select material_id into v_material from erp.material_rolls where id=new.roll_id;
  perform 1 from erp.materials where id=v_material for update;
  if exists(select 1 from erp.pocket_fabric_materials where material_id=v_material) then
   raise exception 'Kain kantong memakai pengurangan stok tanpa hasil ukuran atau HPP produk';end if;
 elsif tg_table_name='material_stock_movements' then
  if new.reversal_of_id is not null then
   select u.adjustment_id into v_adjustment from erp.pocket_fabric_usage u
    join erp.material_adjustment_items i on i.adjustment_id=u.adjustment_id
    join erp.material_stock_movements m on m.source_id=i.id and m.source_type='MATERIAL_ADJUSTMENT_ITEM'
    where m.id=new.reversal_of_id;
   if v_adjustment is not null and not exists(select 1 from erp.pocket_fabric_execution_context c
     where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()
      and c.actor_key=erp._idempotency_actor_key() and c.adjustment_id=v_adjustment) then
    raise exception 'Batalkan pengurangan kain kantong melalui dokumen asal';end if;
  end if;
 end if;
 return new;
end;$function$;
revoke all on function erp.guard_pocket_fabric_v1() from public,anon,authenticated,service_role;
create or replace function erp.get_pocket_fabric_workspace_v1(p_query text default '')
returns jsonb language plpgsql security definer set search_path='' set TimeZone='UTC' as $function$
declare v_query text:=lower(btrim(coalesce(p_query,'')));v_result jsonb;
begin
 perform erp.require_owner_admin();perform erp.require_permission('warehouse.stock.adjust');
 if length(v_query)>120 then raise exception 'Pencarian terlalu panjang';end if;
 with balances as (
  select m.roll_id,m.location_id,sum(m.qty_signed)::numeric(20,6) qty
  from erp.material_stock_movements m join erp.pocket_fabric_materials p on p.material_id=m.material_id
  where m.roll_id is not null group by m.roll_id,m.location_id having sum(m.qty_signed)>0
 ), choices as (
  select r.id,r.material_id,r.roll_number,m.material_name,m.unit_code,b.location_id,l.location_name,b.qty::text qty,
   erp.pocket_fabric_roll_revision_v1(r.id) revision
  from balances b join erp.material_rolls r on r.id=b.roll_id join erp.materials m on m.id=r.material_id
  join erp.locations l on l.id=b.location_id
  where m.is_active and l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
   and (v_query='' or strpos(lower(concat_ws(' ',r.roll_number,m.material_sku,m.material_name,l.location_name)),v_query)>0)
 ), recent as (
  select h.id,h.adjustment_number number,h.status,h.row_version::text row_version,
   erp._cp3_business_date(h.physical_at) date,h.notes reason,u.roll_id,r.roll_number,m.material_name,m.unit_code,
   u.input_mode,u.input_quantity::text input_quantity,u.stock_before::text stock_before,u.issued_quantity::text issued_quantity,
   u.cost_policy,(-((erp._cp6_material_adjustment_revaluation_state(h.id)->>'current_value')::numeric))::numeric(20,2)::text current_cost
  from erp.pocket_fabric_usage u join erp.material_adjustments h on h.id=u.adjustment_id
  join erp.material_rolls r on r.id=u.roll_id join erp.materials m on m.id=u.material_id
  where v_query='' or strpos(lower(concat_ws(' ',h.adjustment_number,r.roll_number,m.material_sku,m.material_name)),v_query)>0
  order by h.created_at desc,h.id limit 50
 ) select jsonb_build_object(
  'rolls',coalesce((select jsonb_agg(to_jsonb(x) order by x.roll_number,x.id,x.location_id) from (select * from choices order by roll_number,id,location_id limit 100) x),'[]'::jsonb),
  'roll_count',(select count(*) from choices),
  'materials',coalesce((select jsonb_agg(to_jsonb(x) order by x.name,x.id) from (
    select m.id,m.material_sku sku,m.material_name name from erp.materials m
    where m.is_active and m.material_type='FABRIC' and not exists(select 1 from erp.pocket_fabric_materials where material_id=m.id)
     and (v_query='' or strpos(lower(concat_ws(' ',m.material_sku,m.material_name)),v_query)>0)
     and not exists(select 1 from erp.cutting_group_rolls c join erp.material_rolls r on r.id=c.roll_id where r.material_id=m.id)
    order by m.material_name,m.id limit 50) x),'[]'::jsonb),
  'periods',coalesce((select jsonb_agg(erp.pocket_period_state_v1(p.id) order by p.created_at desc,p.id) from (select * from erp.pocket_periods order by created_at desc,id limit 50) p),'[]'::jsonb),
  'history',coalesce((select jsonb_agg(to_jsonb(x) order by x.date desc,x.id) from recent x),'[]'::jsonb)
 ) into v_result;
 return v_result;
end;$function$;
revoke all on function erp.get_pocket_fabric_workspace_v1(text) from public,anon,authenticated,service_role;
create or replace function erp.save_pocket_fabric_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
returns jsonb language plpgsql security definer set search_path='' set TimeZone='UTC' set DateStyle='ISO, YMD' as $function$
declare v_action text:=upper(btrim(p_action));v_cached jsonb;v_result jsonb;v_reason text;v_mode text;
 v_material uuid;v_roll uuid;v_location uuid;v_id uuid;v_stock numeric;v_input numeric;v_qty numeric;v_date date;
 v_revision text;v_native jsonb;h erp.material_adjustments%rowtype;u erp.pocket_fabric_usage%rowtype;
begin
 perform erp.require_owner_admin();perform erp.require_permission('warehouse.stock.adjust');
 if v_action in('POST_PERIOD','CANCEL_PERIOD') then return erp.save_pocket_period_action_v1(v_action,p_payload,p_client_request_id);end if;
 perform erp.pocket_period_lock_v1();
 if v_action is null or v_action not in('REGISTER','POST','REVERSE') then raise exception 'Aksi kain kantong tidak dikenal';end if;
 if jsonb_typeof(p_payload) is distinct from 'object' or octet_length(p_payload::text)>10000 then raise exception 'Data kain kantong tidak valid';end if;
 v_reason:=nullif(btrim(p_payload->>'reason'),'');
 if v_reason is null or length(v_reason)>1000 then raise exception 'Alasan wajib diisi, maksimal 1000 karakter';end if;
 v_cached:=erp._idempotency_begin('save_pocket_fabric_action_v1',p_client_request_id,
  erp._request_hash(jsonb_build_object('action',v_action,'payload',p_payload)));
 if v_cached is not null then return v_cached;end if;
 perform set_config('app.change_reason',v_reason,true);
 if v_action='REGISTER' then
  v_material:=(p_payload->>'material_id')::uuid;
  perform 1 from erp.materials where id=v_material and is_active and material_type='FABRIC' for update;
  if not found then raise exception 'Pilih bahan kain yang aktif';end if;
  if exists(select 1 from erp.cutting_group_rolls c join erp.material_rolls r on r.id=c.roll_id where r.material_id=v_material) then
   raise exception 'Bahan sudah dipakai pada potongan; gunakan master kain kantong tersendiri';end if;
  insert into erp.pocket_fabric_materials(material_id,created_by) values(v_material,erp.current_app_user_id());
  v_id:=v_material;
 elsif v_action='POST' then
  v_roll:=(p_payload->>'roll_id')::uuid;v_location:=(p_payload->>'location_id')::uuid;
  select material_id into v_material from erp.material_rolls where id=v_roll;
  perform 1 from erp.materials where id=v_material and is_active for update;
  if not found or not exists(select 1 from erp.pocket_fabric_materials where material_id=v_material) then raise exception 'Roll belum ditetapkan sebagai kain kantong';end if;
  perform 1 from erp.material_rolls where id=v_roll for update;
  v_revision:=erp.pocket_fabric_roll_revision_v1(v_roll);
  if nullif(p_payload->>'expected_revision','') is null or p_payload->>'expected_revision'<>v_revision then
   raise exception 'STALE_VERSION: stok roll berubah. Muat ulang dan periksa angkanya';end if;
  if coalesce(p_payload->>'date','') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'Tanggal wajib YYYY-MM-DD';end if;
  v_date:=(p_payload->>'date')::date;
  if v_date::text<>p_payload->>'date' or v_date>erp._cp3_business_date(statement_timestamp()) then raise exception 'Tanggal pengurangan tidak valid';end if;
  v_mode:=p_payload->>'mode';
  if v_mode is null or v_mode not in('USED','REMAINING') or jsonb_typeof(p_payload->'quantity') is distinct from 'string'
   or coalesce(p_payload->>'quantity','') !~ '^[0-9]{1,14}([.,][0-9]{1,6})?$' then raise exception 'Jumlah harus angka teks, maksimal enam desimal';end if;
  v_input:=replace(p_payload->>'quantity',',','.')::numeric;
  select coalesce(sum(qty_signed),0) into v_stock from erp.material_stock_movements where roll_id=v_roll and location_id=v_location;
  v_qty:=case v_mode when 'USED' then v_input else v_stock-v_input end;
  if v_qty<=0 or v_qty>v_stock then raise exception 'Pengurangan harus positif dan tidak melebihi stok roll di gudang';end if;
  if v_mode='REMAINING' and exists(select 1 from erp.material_stock_movements where roll_id=v_roll and erp._cp3_business_date(physical_at)>v_date) then
   raise exception 'Hitung sisa tidak boleh mendahului pergerakan stok berikutnya; gunakan jumlah keluar bila mencatat mundur';end if;
  v_native:=erp.save_material_adjustment_draft_v2(jsonb_build_object(
   'adjustment_number','KKT-'||p_client_request_id::text,'reason_code','INTERNAL_FACTORY_USE',
   'physical_at',v_date::text||'T12:00:00+07:00','location_id',v_location,'change_reason',v_reason,
   'notes',v_reason,'items',jsonb_build_array(jsonb_build_object('material_id',v_material,'roll_id',v_roll,'qty_signed',(-v_qty)::text))
  ),gen_random_uuid(),null);
  v_id:=(v_native->>'material_adjustment_id')::uuid;
  perform erp.post_material_adjustment_v2(v_id,gen_random_uuid(),(v_native->>'row_version')::bigint,v_reason);
  insert into erp.pocket_fabric_usage(adjustment_id,material_id,roll_id,location_id,input_mode,input_quantity,
   stock_before,issued_quantity,stock_revision,posted_header,posted_item,created_by)
  select v_id,v_material,v_roll,v_location,v_mode,v_input,v_stock,v_qty,v_revision,
   to_jsonb(a)-'status'-'row_version'-'updated_at',to_jsonb(i),erp.current_app_user_id()
  from erp.material_adjustments a join erp.material_adjustment_items i on i.adjustment_id=a.id where a.id=v_id;
 else
  v_id:=(p_payload->>'id')::uuid;
  select * into h from erp.material_adjustments where id=v_id for update;
  select * into u from erp.pocket_fabric_usage where adjustment_id=v_id;
  if u.adjustment_id is null or h.status<>'POSTED' then raise exception 'Pilih pengurangan kain kantong yang masih disahkan';end if;
  if jsonb_typeof(p_payload->'expected_version') is distinct from 'string' or h.row_version::text is distinct from p_payload->>'expected_version' then
   raise exception 'STALE_VERSION: dokumen berubah';end if;
  perform 1 from erp.materials where id=u.material_id for update;
  perform 1 from erp.material_rolls where id=u.roll_id for update;
  insert into erp.pocket_fabric_execution_context values(pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_id);
  perform erp.reverse_material_adjustment_v2(v_id,v_reason,gen_random_uuid(),h.row_version);
  delete from erp.pocket_fabric_execution_context where backend_pid=pg_backend_pid() and transaction_id=txid_current() and adjustment_id=v_id;
 end if;
 insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
 values(case when v_action='REGISTER' then 'pocket_fabric_materials' else 'pocket_fabric_usage' end,v_id,
  case when v_action='REGISTER' then 'INSERT' when v_action='POST' then 'POST' else 'REVERSE' end,erp.current_app_user_id(),v_reason);
 v_result:=jsonb_build_object('request_id',p_client_request_id,'action',v_action,'id',v_id,
  'status',case when v_action='REGISTER' then 'REGISTERED' else (select status from erp.material_adjustments where id=v_id) end);
 return erp._idempotency_complete('save_pocket_fabric_action_v1',p_client_request_id,v_result);
end;$function$;
revoke all on function erp.save_pocket_fabric_action_v1(text,jsonb,uuid) from public,anon,authenticated,service_role;
create or replace function erp.pocket_fabric_checks_v1()
returns table(check_name text,severity text,issue_count bigint,details text) language sql stable security definer set search_path='' set TimeZone='UTC' as $function$
 with docs as (
  select u.*,h.status,h.physical_at,h.reason_code,to_jsonb(h)-'status'-'row_version'-'updated_at' header,
   (erp._cp6_material_adjustment_revaluation_state(h.id)->>'current_value')::numeric signed_value
  from erp.pocket_fabric_usage u join erp.material_adjustments h on h.id=u.adjustment_id
 ), original_journals as (
  select u.adjustment_id,j.id from docs u join erp.journal_entries j on j.source_type='MATERIAL_ADJUSTMENT' and j.source_id=u.adjustment_id
  union select u.adjustment_id,f.journal_entry_id from docs u join erp.material_adjustment_revaluation_facts f on f.adjustment_id=u.adjustment_id
 ), all_journals as (
  select * from original_journals union select o.adjustment_id,j.id from original_journals o join erp.journal_entries j on j.reversal_of_id=o.id
 )
 select 'AP_POCKET_SOURCE'::text,'CRITICAL'::text,count(*),'Pocket outflow preserves the original roll, quantity and posted source'::text from docs u where u.header<>u.posted_header or u.reason_code<>'INTERNAL_FACTORY_USE'
  or u.status not in('POSTED','REVERSED') or (select count(*) from erp.material_adjustment_items where adjustment_id=u.adjustment_id)<>1
  or not exists(select 1 from erp.material_adjustment_items i where i.adjustment_id=u.adjustment_id and to_jsonb(i)=u.posted_item
    and i.material_id=u.material_id and i.roll_id=u.roll_id and i.qty_signed=-u.issued_quantity)
 union all select 'AP_POCKET_EXPENSE_LEDGER','CRITICAL',count(*),'Current outflow value reconciles to inventory and period expense including corrections and inverses' from docs u where
  erp._cp6_supplier_cent_ledger((select array_agg(j.id) from all_journals j where j.adjustment_id=u.adjustment_id))
  is distinct from case when u.signed_value=0 then '{}'::jsonb else jsonb_build_object(
   erp.account_id('MATERIAL_INVENTORY')::text,u.signed_value,erp.account_id('OTHER_EXPENSE')::text,-u.signed_value) end
 union all select 'AP_POCKET_NO_CUTTING','CRITICAL',count(*),'Pocket fabric does not create sized cutting output' from erp.cutting_group_rolls c join erp.material_rolls r on r.id=c.roll_id
  join erp.pocket_fabric_materials p on p.material_id=r.material_id;
$function$;
revoke all on function erp.pocket_fabric_checks_v1() from public,anon,authenticated,service_role;
create or replace function public.erp_get_pocket_fabric_workspace_v1(p_query text default '') returns jsonb language sql security definer set search_path='' as $function$ select erp.get_pocket_fabric_workspace_v1(p_query);$function$;
revoke all on function public.erp_get_pocket_fabric_workspace_v1(text) from public,anon,authenticated,service_role;
grant execute on function public.erp_get_pocket_fabric_workspace_v1(text) to authenticated,service_role;
create or replace function public.erp_save_pocket_fabric_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid) returns jsonb language sql security definer set search_path='' as $function$ select erp.save_pocket_fabric_action_v1(p_action,p_payload,p_client_request_id);$function$;
revoke all on function public.erp_save_pocket_fabric_action_v1(text,jsonb,uuid) from public,anon,authenticated,service_role;
grant execute on function public.erp_save_pocket_fabric_action_v1(text,jsonb,uuid) to authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.initial_prepayment_payments_v1(p_advance_id uuid)
RETURNS TABLE(payment_id uuid,target_id uuid,party_id uuid,party_type text,number text,status text,amount numeric,
 payment_date timestamptz,cash_account_id uuid,source_type text,payment_snapshot jsonb)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' SET TimeZone TO 'UTC' AS $function$
 select p.id,p.purchase_id,h.supplier_id,'SUPPLIER'::text,p.payment_number::text,p.status::text,p.amount,p.payment_date,p.cash_account_id,'SUPPLIER_PAYMENT'::text,to_jsonb(p)-'status'
 from erp.initial_import_prepayment_payments l join erp.supplier_payments p on p.id=l.supplier_payment_id
 join erp.material_purchase_headers h on h.id=p.purchase_id where l.advance_id=p_advance_id
 union all
 select p.id,p.sale_id,h.customer_id,'CUSTOMER',p.payment_number::text,p.status::text,p.amount,p.payment_date,p.cash_account_id,'SALES_PAYMENT',to_jsonb(p)-'status'
 from erp.initial_import_prepayment_payments l join erp.sales_payments p on p.id=l.sales_payment_id
 join erp.sales_headers h on h.id=p.sale_id where l.advance_id=p_advance_id
 union all
 select p.id,p.vendor_invoice_id,h.vendor_id,'VENDOR',p.payment_number::text,p.status::text,p.amount,p.payment_date,p.cash_account_id,'VENDOR_PAYMENT',to_jsonb(p)-'status'
 from erp.initial_import_prepayment_payments l join erp.vendor_payments p on p.id=l.vendor_payment_id
 join erp.vendor_invoices h on h.id=p.vendor_invoice_id where l.advance_id=p_advance_id
 union all
 select p.id,p.balance_id,coalesce(h.supplier_id,h.customer_id,h.vendor_id),h.party_type::text,p.settlement_number::text,p.status::text,p.amount,p.physical_at,p.cash_account_id,
   'OPENING_SUBLEDGER_SETTLEMENT',(to_jsonb(p)-'status'-'updated_at')||jsonb_build_object('payment_method','OPENING_ADVANCE')
 from erp.initial_import_prepayment_payments l join erp.opening_subledger_settlements p on p.id=l.opening_settlement_id
 join erp.opening_subledger_balances h on h.id=p.balance_id where l.advance_id=p_advance_id;
$function$;
revoke all on function erp.initial_prepayment_payments_v1(uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.initial_prepayment_state_v1(p_advance_id uuid)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' AS $function$
 select jsonb_build_object('id',a.id,'party_type',a.party_type,'party_id',a.party_id,'document_number',a.document_number,
   'document_date',a.document_date,'cutover_date',a.cutover_date,'original_amount',a.original_amount::text,
   'settled_before_cutover',a.settled_before_cutover::text,'opening_amount',(a.amount+e.corrected)::numeric(20,2)::text,
   'applied_amount',p.applied::numeric(20,2)::text,'refunded_amount',(-e.refunded)::numeric(20,2)::text,
   'remaining_amount',(a.amount+e.corrected+e.refunded-p.applied)::numeric(20,2)::text)
 from erp.initial_import_prepayments a
 cross join lateral(select coalesce(sum(delta) filter(where component='CORRECTION'),0) corrected,
   coalesce(sum(delta) filter(where component='REFUND'),0) refunded from erp.initial_import_prepayment_events where advance_id=a.id) e
 cross join lateral(select coalesce(sum(amount),0) applied from erp.initial_prepayment_payments_v1(a.id) where status='POSTED') p
 where a.id=p_advance_id;
$function$;
revoke all on function erp.initial_prepayment_state_v1(uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.initial_prepayment_account_v1(p_payment_id uuid)
RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' AS $function$
 select a.coa_account_id from erp.initial_import_prepayment_payments l join erp.initial_import_prepayments a on a.id=l.advance_id where l.payment_id=p_payment_id;
$function$;
revoke all on function erp.initial_prepayment_account_v1(uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.initial_prepayment_targets_v1(p_advance_id uuid)
RETURNS TABLE(id uuid,number text,party_id uuid,party_type text,remaining_amount text,target_date date,target_kind text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' AS $function$
 select h.id,h.purchase_number::text,h.supplier_id,'SUPPLIER'::text,
   (erp.material_purchase_payable_total(h.id)-coalesce((select sum(amount) from erp.supplier_payments where purchase_id=h.id and status='POSTED'),0))::numeric(20,2)::text,
   greatest(erp._cp3_business_date(h.physical_at),(select max(i.invoice_date) from erp.material_supplier_invoices i
     join erp.material_supplier_invoice_lines l on l.invoice_id=i.id join erp.material_purchase_items pi on pi.id=l.purchase_item_id where pi.purchase_id=h.id and i.status='POSTED')),'DOCUMENT'::text
 from erp.material_purchase_headers h join erp.initial_import_prepayments a on a.id=p_advance_id and a.party_type='SUPPLIER' and a.party_id=h.supplier_id
 where h.status='POSTED'
 union all
 select h.id,h.sale_number::text,h.customer_id,'CUSTOMER',
   (round(erp.sale_net_total(h.id),2)-coalesce((select sum(amount) from erp.sales_payments where sale_id=h.id and status='POSTED'),0))::numeric(20,2)::text,
   erp._cp3_business_date(h.sale_date),'DOCUMENT'
 from erp.sales_headers h join erp.initial_import_prepayments a on a.id=p_advance_id and a.party_type='CUSTOMER' and a.party_id=h.customer_id
 where h.status in('POSTED','PARTIAL_PAID','PAID')
 union all
 select h.id,h.invoice_number::text,h.vendor_id,'VENDOR',
   (h.total_amount-coalesce((select sum(amount) from erp.vendor_payments where vendor_invoice_id=h.id and status='POSTED'),0))::numeric(20,2)::text,h.invoice_date,'DOCUMENT'
 from erp.vendor_invoices h join erp.initial_import_prepayments a on a.id=p_advance_id and a.party_type='VENDOR' and a.party_id=h.vendor_id
 where h.status in('POSTED','PARTIAL_PAID','PAID')
 union all
 select b.id,coalesce(s.document_number,h.opening_number)||' · saldo awal',a.party_id,a.party_type,
   (b.original_amount-b.settled_amount)::numeric(20,2)::text,h.opening_date,'OPENING'
 from erp.initial_import_prepayments a join erp.opening_subledger_balances b on b.party_type=a.party_type
   and coalesce(b.supplier_id,b.customer_id,b.vendor_id)=a.party_id
 join erp.opening_balance_items oi on oi.id=b.opening_item_id
 join erp.opening_balance_headers h on h.id=oi.opening_id and h.status='POSTED'
 left join erp.initial_import_financial_sources s on s.opening_item_id=b.opening_item_id
 where a.id=p_advance_id and b.direction=case when a.party_type='CUSTOMER' then 'RECEIVABLE' else 'PAYABLE' end;
$function$;
revoke all on function erp.initial_prepayment_targets_v1(uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.initial_prepayment_funding_v1(
 p_payment_id uuid,p_kind text,p_party uuid,p_amount numeric,p_date date,p_target_date date)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare a erp.initial_import_prepayments%rowtype;l erp.initial_import_prepayment_payments%rowtype;c erp.chart_accounts%rowtype;p record;
begin
 perform erp.require_internal();
 select * into l from erp.initial_import_prepayment_payments where payment_id=p_payment_id;
 if l.payment_id is null then return null;end if;
 select * into a from erp.initial_import_prepayments where id=l.advance_id for update;
 select * into p from erp.initial_prepayment_payments_v1(a.id) where payment_id=p_payment_id;
 if a.id is null or a.party_type<>p_kind or a.party_id<>p_party or p.party_type<>a.party_type or p.party_id<>a.party_id
   or p.amount<>p_amount or p.status<>'DRAFT' or p.cash_account_id is not null
   or p.payment_snapshot is distinct from l.payment_snapshot or p.payment_snapshot->>'payment_method' is distinct from 'OPENING_ADVANCE'
   or not exists(select 1 from erp.migration_batches where id=a.batch_id and status='POSTED') then
   raise exception 'Sumber uang muka tidak cocok dengan pihak dan pembayaran tagihan';end if;
 if p_date is null or p_target_date is null or p_date<greatest(a.cutover_date,p_target_date)
   or p_date>erp._cp3_business_date(statement_timestamp()) then raise exception 'Tanggal pemakaian uang muka harus sejak saldo awal dan tagihan, sampai hari ini';end if;
 if p_amount<=0 or p_amount>(erp.initial_prepayment_state_v1(a.id)->>'remaining_amount')::numeric then
   raise exception 'Pemakaian melebihi sisa uang muka';end if;
 select * into c from erp.chart_accounts where id=a.coa_account_id;
 if not(c.is_active and c.is_postable) or c.account_type<>(case when a.party_type='CUSTOMER' then 'LIABILITY' else 'ASSET' end)
   or c.normal_balance<>(case when a.party_type='CUSTOMER' then 'CREDIT' else 'DEBIT' end)
   or exists(select 1 from erp.cash_accounts where coa_account_id=c.id)
   or exists(select 1 from erp.accounting_account_mappings where account_id=c.id) then raise exception 'Akun uang muka harus akun khusus aktif sesuai jenis pihak';end if;
 return a.coa_account_id;
end;$function$;
revoke all on function erp.initial_prepayment_funding_v1(uuid,text,uuid,numeric,date,date) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.guard_initial_prepayment_immutable_v1()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path TO '' AS $function$
begin raise exception 'Riwayat uang muka tetap; gunakan koreksi atau pembatalan tertaut';end;$function$;
revoke all on function erp.guard_initial_prepayment_immutable_v1() from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.guard_initial_prepayment_account_v1()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
begin
 if TG_TABLE_NAME='chart_accounts' then
   if exists(select 1 from erp.initial_import_prepayments where coa_account_id=old.id) then
     if TG_OP='DELETE' then raise exception 'Akun sumber uang muka tidak dapat dihapus';end if;
     if new.account_type<>old.account_type or new.normal_balance<>old.normal_balance or new.report_group<>old.report_group
       or not new.is_active or not new.is_postable then raise exception 'Sifat akun uang muka yang sudah dipakai harus tetap agar saldo dan laporan konsisten';end if;
   end if;
 elsif TG_TABLE_NAME='cash_accounts' then
   if exists(select 1 from erp.initial_import_prepayments where coa_account_id=new.coa_account_id) then raise exception 'Akun uang muka tidak boleh dijadikan rekening kas/bank';end if;
 else
   if exists(select 1 from erp.initial_import_prepayments where coa_account_id=new.account_id) then raise exception 'Akun uang muka tidak boleh dijadikan mapping akun utama';end if;
 end if;
 if TG_OP='DELETE' then return old;end if;return new;
end;$function$;
revoke all on function erp.guard_initial_prepayment_account_v1() from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.guard_initial_prepayment_payment_v1()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path TO '' AS $function$
begin
 if TG_TABLE_NAME='opening_subledger_settlements' then
   if TG_OP='DELETE' then
     if old.cash_account_id is null then raise exception 'Pemakaian uang muka tetap; gunakan pembatalan tertaut';end if;return old;
   end if;
   if new.cash_account_id is not null and (TG_OP='INSERT' or old.cash_account_id is not null) then return new;end if;
   if current_user<>'postgres' or new.cash_account_id is not null or
     (TG_OP='UPDATE' and to_jsonb(new)-'status'-'updated_at' is distinct from to_jsonb(old)-'status'-'updated_at') then
     raise exception 'Pelunasan saldo awal dari uang muka harus melalui command resmi dan identitasnya tetap';end if;
   return new;
 end if;
 if TG_OP='DELETE' then
   if old.payment_method='OPENING_ADVANCE' then raise exception 'Riwayat pemakaian uang muka tidak dapat dihapus';end if;return old;
 end if;
 if new.payment_method is distinct from 'OPENING_ADVANCE' and (TG_OP='INSERT' or old.payment_method is distinct from 'OPENING_ADVANCE') then return new;end if;
 if current_user<>'postgres' then raise exception 'Uang muka harus melalui command resmi';end if;
 if new.payment_method is distinct from 'OPENING_ADVANCE' or new.cash_account_id is not null
   or (TG_OP='UPDATE' and to_jsonb(new)-'status' is distinct from to_jsonb(old)-'status') then
   raise exception 'Identitas pembayaran uang muka bersifat tetap';end if;
 if TG_OP='INSERT' and new.status<>'DRAFT' then raise exception 'Pembayaran uang muka dibuat draft sebelum diposting';end if;
 if TG_OP='UPDATE' and not((old.status='DRAFT' and new.status='POSTED') or (old.status='POSTED' and new.status='REVERSED') or old.status=new.status) then
   raise exception 'Status pembayaran uang muka tidak sah';end if;
 return new;
end;$function$;
revoke all on function erp.guard_initial_prepayment_payment_v1() from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.check_initial_prepayment_v1(p_batch_id uuid,p_row_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD' AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;c jsonb;v_cutover date;v_party uuid;v_account uuid;
 v_table text;v_code text;v_entity text;k text;v_number text;v_value numeric;
begin
 perform erp.require_owner_admin();
 select * into r from erp.migration_staging_rows where id=p_row_id and batch_id=p_batch_id and entity_type='OPENING_ADVANCE';
 if r.id is null then raise exception 'Baris uang muka tidak ditemukan';end if;j:=r.normalized_payload;
 foreach k in array array['party_type','party_code','coa_account_code','document_number','document_date','original_amount','settled_before_cutover','amount','control_key'] loop
   if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk uang muka',k;end if;
 end loop;
 if j->>'party_type' not in('SUPPLIER','CUSTOMER','VENDOR') then raise exception 'party_type: gunakan SUPPLIER, CUSTOMER, atau VENDOR';end if;
 v_number:=btrim(j->>'document_number');if length(v_number)>120 then raise exception 'document_number: maksimal 120 karakter';end if;
 select (cutover_at at time zone 'Asia/Jakarta')::date into v_cutover from erp.migration_batches where id=p_batch_id;
 if j->>'document_date' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' or (j->>'document_date')::date::text<>j->>'document_date'
   or (j->>'document_date')::date>v_cutover then raise exception 'document_date: tanggal valid tidak boleh melewati saldo awal';end if;
 foreach k in array array['original_amount','settled_before_cutover','amount'] loop
   v_value:=(j->>k)::numeric;
   if v_value::text in('NaN','Infinity','-Infinity') or v_value<0 or v_value<>round(v_value,2) then raise exception '%: nominal harus tepat dua desimal dan nonnegatif',k;end if;
   perform v_value::numeric(20,2);
 end loop;
 if (j->>'amount')::numeric<=0 or (j->>'original_amount')::numeric-(j->>'settled_before_cutover')::numeric<>(j->>'amount')::numeric then
   raise exception 'amount: sisa positif harus sama dengan uang muka asal dikurangi pemakaian/pengembalian lama';end if;
 v_table:=case j->>'party_type' when 'SUPPLIER' then 'suppliers' when 'CUSTOMER' then 'customers' else 'laundry_vendors' end;
 v_code:=case j->>'party_type' when 'SUPPLIER' then 'supplier_code' when 'CUSTOMER' then 'customer_code' else 'vendor_code' end;
 v_entity:=case j->>'party_type' when 'VENDOR' then 'LAUNDRY_VENDOR' else j->>'party_type' end;
 execute format('select id from erp.%I where %I=$1 and is_active',v_table,v_code) into v_party using j->>'party_code';
 if v_party is null and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type=v_entity
   and validation_status='VALID' and normalized_payload->>v_code=j->>'party_code'
   and coalesce(nullif(normalized_payload->>'is_active','')::boolean,true)) then raise exception 'party_code: pihak aktif tidak ditemukan';end if;
 select id,to_jsonb(a) into v_account,c from erp.chart_accounts a where account_code=j->>'coa_account_code';
 if v_account is null then
   select normalized_payload into c from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='CHART_ACCOUNT'
     and validation_status='VALID' and normalized_payload->>'account_code'=j->>'coa_account_code';
 end if;
 if c is null or c->>'account_type' is distinct from (case when j->>'party_type'='CUSTOMER' then 'LIABILITY' else 'ASSET' end)
   or c->>'normal_balance' is distinct from (case when j->>'party_type'='CUSTOMER' then 'CREDIT' else 'DEBIT' end)
   or not coalesce(nullif(c->>'is_active','')::boolean,true) or not coalesce(nullif(c->>'is_postable','')::boolean,true)
   or exists(select 1 from erp.cash_accounts where coa_account_id=v_account)
   or exists(select 1 from erp.accounting_account_mappings where account_id=v_account)
   or exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='CASH_ACCOUNT'
     and normalized_payload->>'coa_account_code'=j->>'coa_account_code') then
   raise exception 'coa_account_code: gunakan akun khusus uang muka aktif, aset untuk supplier/vendor atau kewajiban untuk pelanggan';end if;
 if v_account is not null and not exists(select 1 from erp.initial_import_prepayments where coa_account_id=v_account)
   and exists(select 1 from erp.journal_lines where account_id=v_account) then
   raise exception 'coa_account_code: akun ini sudah memiliki saldo tanpa sumber uang muka; rekonsiliasi dahulu';end if;
 if exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='OPENING_ADVANCE' and s.id<>r.id
   and s.normalized_payload->>'party_type'=j->>'party_type' and s.normalized_payload->>'party_code'=j->>'party_code'
   and lower(btrim(s.normalized_payload->>'document_number'))=lower(v_number))
   or exists(select 1 from erp.initial_import_prepayments where party_type=j->>'party_type' and party_id=v_party
     and lower(btrim(document_number))=lower(v_number) and source_row_id<>r.id) then raise exception 'document_number: uang muka sudah dicatat';end if;
 return jsonb_build_object('party_id',v_party,'coa_account_id',v_account,'cutover_date',v_cutover);
end;$function$;
revoke all on function erp.check_initial_prepayment_v1(uuid,uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.validate_initial_prepayments_v1(p_batch_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare r record;
begin
 perform erp.require_owner_admin();
 for r in select id from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='OPENING_ADVANCE' order by source_row_no loop
   begin
     perform erp.check_initial_prepayment_v1(p_batch_id,r.id);
     update erp.migration_staging_rows set validation_status='VALID',validation_errors='[]' where id=r.id;
   exception when others then
     update erp.migration_staging_rows set validation_status='ERROR',validation_errors=jsonb_build_array(sqlerrm) where id=r.id;
   end;
 end loop;
end;$function$;
revoke all on function erp.validate_initial_prepayments_v1(uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.apply_initial_prepayments_v1(p_batch_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare r record;j jsonb;c jsonb;v_id uuid;v_amount numeric;v_customer uuid;v_vendor uuid;
begin
 perform erp.require_owner_admin();
 for r in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='OPENING_ADVANCE'
   and posted_entity_id is null order by source_row_no loop
   if r.validation_status<>'VALID' then raise exception 'Uang muka belum lolos pemeriksaan';end if;j:=r.normalized_payload;
   -- Lock normalized source identity before revalidation, including other batches.
   perform pg_advisory_xact_lock(hashtextextended('INITIAL_PREPAYMENT:'||(j->>'party_type')||':'||(j->>'party_code')||':'||lower(btrim(j->>'document_number')),0));
   c:=erp.check_initial_prepayment_v1(p_batch_id,r.id);
   if c->>'party_id' is null or c->>'coa_account_id' is null then raise exception 'Master uang muka belum tersedia';end if;
   insert into erp.initial_import_prepayments(batch_id,source_row_id,party_type,party_id,supplier_id,customer_id,vendor_id,coa_account_id,document_number,document_date,cutover_date,original_amount,settled_before_cutover,amount)
   values(p_batch_id,r.id,j->>'party_type',(c->>'party_id')::uuid,
     case when j->>'party_type'='SUPPLIER' then (c->>'party_id')::uuid end,
     case when j->>'party_type'='CUSTOMER' then (c->>'party_id')::uuid end,
     case when j->>'party_type'='VENDOR' then (c->>'party_id')::uuid end,
     (c->>'coa_account_id')::uuid,btrim(j->>'document_number'),
     (j->>'document_date')::date,(c->>'cutover_date')::date,(j->>'original_amount')::numeric,(j->>'settled_before_cutover')::numeric,(j->>'amount')::numeric)
   returning id into v_id;
   v_amount:=(j->>'amount')::numeric;
   v_customer:=case when j->>'party_type'='CUSTOMER' then (c->>'party_id')::uuid end;
   v_vendor:=case when j->>'party_type'='VENDOR' then (c->>'party_id')::uuid end;
   perform erp.post_journal('OPENING_PREPAYMENT',v_id,(c->>'cutover_date')::date,'Uang muka tersisa sebelum ERP',jsonb_build_array(
     jsonb_build_object('account_id',c->>'coa_account_id','debit',case when v_customer is null then v_amount else 0 end,
       'credit',case when v_customer is null then 0 else v_amount end,'customer_id',v_customer,'vendor_id',v_vendor),
     jsonb_build_object('mapping_key','OPENING_EQUITY','debit',case when v_customer is null then 0 else v_amount end,
       'credit',case when v_customer is null then v_amount else 0 end,'customer_id',v_customer,'vendor_id',v_vendor)));
   update erp.migration_staging_rows set posted_entity_id=v_id,posted_entity_type='OPENING_ADVANCE' where id=r.id;
 end loop;
end;$function$;
revoke all on function erp.apply_initial_prepayments_v1(uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.manage_initial_prepayment_v1(p_payload jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD' SET TimeZone TO 'UTC' AS $function$
declare a erp.initial_import_prepayments%rowtype;e erp.initial_import_prepayment_events%rowtype;
 v_op text:=p_payload->>'operation';v_table text;v_parent text;v_fk text;v_link text;v_rpc text;
 v_payment uuid;v_target uuid;v_id uuid;v_journal uuid;v_cash uuid;v_cash_coa uuid;v_locked uuid;
 v_amount numeric;v_delta numeric;v_debit numeric;v_date date;v_reason text;v_customer uuid;v_vendor uuid;
 v_snapshot jsonb;v_state jsonb;v_target_state record;v_payment_at timestamptz;
begin
 perform erp.require_owner_admin();
 if v_op is null or v_op not in('APPLY','REVERSE_PAYMENT','REFUND','CORRECT','REVERSE_EVENT') then raise exception 'Operasi uang muka tidak dikenal';end if;
 v_reason:=nullif(btrim(p_payload->>'reason'),'');if v_reason is null then raise exception 'Alasan pemakaian/perubahan uang muka wajib diisi';end if;
 select * into a from erp.initial_import_prepayments where id=(p_payload->>'advance_id')::uuid and batch_id=(p_payload->>'batch_id')::uuid;
 if a.id is null then raise exception 'Uang muka bukan milik batch ini';end if;
 v_table:=case a.party_type when 'SUPPLIER' then 'supplier_payments' when 'CUSTOMER' then 'sales_payments' else 'vendor_payments' end;
 v_parent:=case a.party_type when 'SUPPLIER' then 'material_purchase_headers' when 'CUSTOMER' then 'sales_headers' else 'vendor_invoices' end;
 v_fk:=case a.party_type when 'SUPPLIER' then 'purchase_id' when 'CUSTOMER' then 'sale_id' else 'vendor_invoice_id' end;
 v_link:=case a.party_type when 'SUPPLIER' then 'supplier_payment_id' when 'CUSTOMER' then 'sales_payment_id' else 'vendor_payment_id' end;
 v_rpc:=case a.party_type when 'SUPPLIER' then 'supplier_payment' when 'CUSTOMER' then 'sales_payment' else 'vendor_payment' end;
 -- Match native lock order: payment (when existing), document, then funding.
 if v_op='REVERSE_PAYMENT' then
   v_payment:=(p_payload->>'payment_id')::uuid;
   if not exists(select 1 from erp.initial_import_prepayment_payments where payment_id=v_payment and advance_id=a.id) then raise exception 'Pembayaran bukan pemakaian uang muka ini';end if;
   if exists(select 1 from erp.initial_import_prepayment_payments where payment_id=v_payment and opening_settlement_id is not null) then
     v_table:='opening_subledger_settlements';v_parent:='opening_subledger_balances';v_fk:='balance_id';v_link:='opening_settlement_id';v_rpc:='opening_subledger_settlement';end if;
   execute format('select to_jsonb(p) from erp.%I p where id=$1 for update',v_table) into v_snapshot using v_payment;
   v_target:=(v_snapshot->>v_fk)::uuid;
 elsif v_op='APPLY' then
   v_target:=(p_payload->>'target_id')::uuid;
   select * into v_target_state from erp.initial_prepayment_targets_v1(a.id) where id=v_target;
   if v_target_state.id is null then raise exception 'Tagihan pihak ini tidak ditemukan';end if;
   if v_target_state.target_kind='OPENING' then
     v_table:='opening_subledger_settlements';v_parent:='opening_subledger_balances';v_fk:='balance_id';v_link:='opening_settlement_id';v_rpc:='opening_subledger_settlement';end if;
 end if;
 if v_target is not null then execute format('select id from erp.%I where id=$1 for update',v_parent) into v_locked using v_target;
   if v_locked is null then raise exception 'Tagihan tujuan tidak ditemukan';end if;
 end if;
 select * into a from erp.initial_import_prepayments where id=a.id for update;
 if p_payload->>'expected_revision' is distinct from erp.initial_import_revision_v1(a.batch_id) then raise exception 'STALE_VERSION: saldo atau tagihan berubah; muat ulang';end if;
 v_state:=erp.initial_prepayment_state_v1(a.id);
 if v_op in('APPLY','REFUND','CORRECT') then
   if coalesce(p_payload->>'amount','') !~ '^[0-9]+([.,][0-9]{1,2})?$' then raise exception 'amount: isi nominal tepat dua desimal tanpa pemisah ribuan';end if;
   v_amount:=replace(p_payload->>'amount',',','.')::numeric;perform v_amount::numeric(20,2);
   if v_amount<=0 and v_op<>'CORRECT' then raise exception 'Nominal harus positif';end if;
   if coalesce(p_payload->>'effective_date','') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'Tanggal wajib YYYY-MM-DD';end if;
   v_date:=(p_payload->>'effective_date')::date;
   if v_date::text<>p_payload->>'effective_date' or v_date<a.cutover_date or v_date>erp._cp3_business_date(statement_timestamp()) then raise exception 'Tanggal harus sejak saldo awal sampai hari ini';end if;
 end if;
 if v_op='APPLY' then
   select * into v_target_state from erp.initial_prepayment_targets_v1(a.id) where id=v_target;
   if v_target_state.id is null or v_amount>(v_target_state.remaining_amount)::numeric then raise exception 'Tagihan pihak yang sama harus memiliki sisa mencukupi';end if;
   if v_date<v_target_state.target_date then raise exception 'Pemakaian uang muka tidak boleh mendahului tagihan';end if;
   if v_amount>(v_state->>'remaining_amount')::numeric then raise exception 'Pemakaian melebihi sisa uang muka';end if;
   v_payment:=gen_random_uuid();v_payment_at:=(v_date::timestamp+interval '12 hours') at time zone 'Asia/Jakarta';
   if v_link='opening_settlement_id' then
     insert into erp.opening_subledger_settlements(id,balance_id,settlement_number,physical_at,amount,cash_account_id,notes,created_by)
     values(v_payment,v_target,'ADV-'||v_payment::text,v_payment_at,v_amount,null,v_reason,erp.current_app_user_id())
     returning (to_jsonb(opening_subledger_settlements)-'status'-'updated_at')||jsonb_build_object('payment_method','OPENING_ADVANCE') into v_snapshot;
   else
     execute format('insert into erp.%I(id,%I,payment_number,payment_date,amount,cash_account_id,payment_method,notes,created_by) values($1,$2,$3,$4,$5,null,''OPENING_ADVANCE'',$6,erp.current_app_user_id()) returning to_jsonb(%I)-''status''',v_table,v_fk,v_table)
       into v_snapshot using v_payment,v_target,'ADV-'||v_payment::text,v_payment_at,v_amount,v_reason;
   end if;
   execute format('insert into erp.initial_import_prepayment_payments(payment_id,advance_id,%I,payment_snapshot) values($1,$2,$1,$3)',v_link)
     using v_payment,a.id,v_snapshot;
   execute format('select erp.%I($1)','post_'||v_rpc) using v_payment;
 elsif v_op='REVERSE_PAYMENT' then
   execute format('select erp.%I($1,$2)','reverse_'||v_rpc) using v_payment,v_reason;
 else
   v_id:=gen_random_uuid();
   v_customer:=case when a.party_type='CUSTOMER' then a.party_id end;v_vendor:=case when a.party_type='VENDOR' then a.party_id end;
   if v_op='REVERSE_EVENT' then
     select * into e from erp.initial_import_prepayment_events where id=(p_payload->>'event_id')::uuid and advance_id=a.id;
     if e.id is null or e.event_type='REVERSAL' or exists(select 1 from erp.initial_import_prepayment_events where reverses_event_id=e.id) then raise exception 'Perubahan tidak ditemukan atau sudah dibatalkan';end if;
     v_delta:=-e.delta;
     if (v_state->>'remaining_amount')::numeric+v_delta<0 then raise exception 'Pembatalan mengurangi uang muka di bawah pemakaian; batalkan pemakaiannya dahulu';end if;
     v_journal:=erp._cp3_r4_reverse_journal_internal(e.journal_entry_id,v_reason);
     select economic_date into v_date from erp.journal_entries where id=v_journal;
     insert into erp.initial_import_prepayment_events(id,advance_id,event_type,component,delta,effective_date,reason,cash_account_id,reverses_event_id,journal_entry_id,created_by)
       values(v_id,a.id,'REVERSAL',e.component,v_delta,v_date,v_reason,e.cash_account_id,e.id,v_journal,erp.current_app_user_id());
   else
     v_delta:=case when v_op='CORRECT' then v_amount-(v_state->>'opening_amount')::numeric else -v_amount end;
     if v_delta=0 then raise exception 'Nilai koreksi sama dengan saldo awal saat ini';end if;
     if (v_state->>'remaining_amount')::numeric+v_delta<0 then raise exception 'Perubahan melebihi sisa uang muka; batalkan pemakaian dahulu';end if;
     if v_op='REFUND' then
       v_cash:=(p_payload->>'cash_account_id')::uuid;
       select coa_account_id into v_cash_coa from erp.cash_accounts where id=v_cash and is_active;
       if v_cash_coa is null then raise exception 'Pilih rekening kas/bank aktif';end if;
     else v_cash_coa:=erp.account_id('OPENING_EQUITY');end if;
     v_debit:=case when a.party_type='CUSTOMER' then -v_delta else v_delta end;
     v_journal:=erp.post_journal('PREPAYMENT_EVENT',v_id,v_date,v_reason,jsonb_build_array(
       jsonb_build_object('account_id',a.coa_account_id,'debit',greatest(v_debit,0),'credit',greatest(-v_debit,0),'customer_id',v_customer,'vendor_id',v_vendor),
       jsonb_build_object('account_id',v_cash_coa,'debit',greatest(-v_debit,0),'credit',greatest(v_debit,0),'customer_id',v_customer,'vendor_id',v_vendor)));
     insert into erp.initial_import_prepayment_events(id,advance_id,event_type,component,delta,effective_date,reason,cash_account_id,journal_entry_id,created_by)
       values(v_id,a.id,case when v_op='CORRECT' then 'CORRECTION' else 'REFUND' end,
         case when v_op='CORRECT' then 'CORRECTION' else 'REFUND' end,v_delta,v_date,v_reason,v_cash,v_journal,erp.current_app_user_id());
   end if;
 end if;
 insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
   values('initial_import_prepayments',a.id,'UPDATE',jsonb_build_object('operation',v_op,'payment_id',v_payment,'event_id',v_id),erp.current_app_user_id(),v_reason);
end;$function$;
revoke all on function erp.manage_initial_prepayment_v1(jsonb) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.initial_prepayment_checks_v1()
RETURNS TABLE(check_name text,severity text,issue_count bigint,details text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' AS $function$
 select 'AP_PREPAYMENT_CAPACITY','CRITICAL',count(*)::bigint,'Current opening minus refunds and native posted applications must remain nonnegative'
 from erp.initial_import_prepayments a cross join lateral(select erp.initial_prepayment_state_v1(a.id) s) v
 where (s->>'remaining_amount')::numeric<0 or (s->>'opening_amount')::numeric<0 or (s->>'refunded_amount')::numeric<0
 union all
 select 'AP_PREPAYMENT_PAYMENT_SOURCE','CRITICAL',count(*)::bigint,'Every application retains its source, exact payment snapshot, and party; cash is absent'
 from erp.initial_import_prepayments a cross join lateral erp.initial_prepayment_payments_v1(a.id) p
 join erp.initial_import_prepayment_payments l on l.payment_id=p.payment_id
 where p.party_id<>a.party_id or p.party_type<>a.party_type or p.amount<=0 or p.cash_account_id is not null
   or p.payment_snapshot is distinct from l.payment_snapshot or p.payment_snapshot->>'payment_method' is distinct from 'OPENING_ADVANCE'
   or erp._cp3_business_date(p.payment_date)<a.cutover_date
 union all
 select 'AP_PREPAYMENT_PAYMENT_JOURNAL','CRITICAL',count(*)::bigint,'Applied advances retain exact native liability/receivable journals and their linked inverses'
 from erp.initial_import_prepayments a cross join lateral erp.initial_prepayment_payments_v1(a.id) p
 cross join lateral(select case a.party_type when 'SUPPLIER' then erp.account_id('AP_SUPPLIER') when 'CUSTOMER' then erp.account_id('AR_CUSTOMER') else erp.account_id('AP_VENDOR') end account_id,
   case when a.party_type='CUSTOMER' then 1 else -1 end sign) k
 where (p.status='DRAFT' and exists(select 1 from erp.journal_entries where source_type=p.source_type and source_id=p.payment_id))
   or(p.status in('POSTED','REVERSED') and (
     (select count(*) from erp.journal_entries where source_type=p.source_type and source_id=p.payment_id)<>1
     or not exists(select 1 from erp.journal_entries j where j.source_type=p.source_type and j.source_id=p.payment_id
       and j.status=p.status and j.economic_date=erp._cp3_business_date(p.payment_date)
       and (select count(*) from erp.journal_lines where journal_entry_id=j.id)=2
       and erp._cp6_supplier_cent_ledger(array[j.id])=jsonb_build_object(a.coa_account_id::text,p.amount*k.sign,k.account_id::text,-p.amount*k.sign)
       and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and
         (l.customer_id is distinct from a.customer_id or l.vendor_id is distinct from a.vendor_id or l.contractor_id is not null))
       and (select count(*) from erp.journal_entries where reversal_of_id=j.id)=case when p.status='REVERSED' then 1 else 0 end
       and (p.status<>'REVERSED' or exists(select 1 from erp.journal_entries x where x.reversal_of_id=j.id and x.status='POSTED'
         and erp._cp6_supplier_cent_ledger(array[j.id,x.id])='{}'::jsonb)))))
 union all
 select 'AP_PREPAYMENT_OPENING_JOURNAL','CRITICAL',count(*)::bigint,'Opening prepayment posts only the carried balance once at cutover, without historical cash'
 from erp.initial_import_prepayments a
 where (select count(*) from erp.journal_entries where source_type='OPENING_PREPAYMENT' and source_id=a.id)<>1
   or not exists(select 1 from erp.journal_entries j where j.source_type='OPENING_PREPAYMENT' and j.source_id=a.id
     and j.status='POSTED' and j.economic_date=a.cutover_date
     and (select count(*) from erp.journal_lines where journal_entry_id=j.id)=2
     and erp._cp6_supplier_cent_ledger(array[j.id])=jsonb_build_object(
       a.coa_account_id::text,case when a.party_type='CUSTOMER' then -a.amount else a.amount end,
       erp.account_id('OPENING_EQUITY')::text,case when a.party_type='CUSTOMER' then a.amount else -a.amount end)
     and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id
       and (l.customer_id is distinct from a.customer_id or l.vendor_id is distinct from a.vendor_id or l.contractor_id is not null)))
 union all
 select 'AP_PREPAYMENT_EVENT_JOURNAL','CRITICAL',count(*)::bigint,'Corrections, cash refunds, and append-only reversals retain exact money and economic dates'
 from erp.initial_import_prepayment_events e join erp.initial_import_prepayments a on a.id=e.advance_id
 left join erp.initial_import_prepayment_events prior on prior.id=e.reverses_event_id
 left join erp.journal_entries j on j.id=e.journal_entry_id
 cross join lateral(select case when a.party_type='CUSTOMER' then -e.delta else e.delta end amount,
   case when e.component='CORRECTION' then erp.account_id('OPENING_EQUITY') else (select coa_account_id from erp.cash_accounts where id=e.cash_account_id) end account_id) k
 where j.id is null or j.economic_date<>e.effective_date or e.effective_date<a.cutover_date
   or j.source_type<>case when e.event_type='REVERSAL' then 'JOURNAL_REVERSAL' else 'PREPAYMENT_EVENT' end
   or (e.event_type<>'REVERSAL' and j.source_id<>e.id)
   or (e.event_type='REVERSAL' and (prior.advance_id is distinct from e.advance_id or prior.event_type='REVERSAL'
     or e.delta<>-prior.delta or e.component<>prior.component or j.reversal_of_id is distinct from prior.journal_entry_id))
   or j.status<>case when exists(select 1 from erp.initial_import_prepayment_events x where x.reverses_event_id=e.id) then 'REVERSED' else 'POSTED' end
   or (select count(*) from erp.journal_lines where journal_entry_id=j.id)<>2
   or erp._cp6_supplier_cent_ledger(array[j.id]) is distinct from jsonb_build_object(a.coa_account_id::text,k.amount,k.account_id::text,-k.amount)
   or exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id
     and (l.customer_id is distinct from a.customer_id or l.vendor_id is distinct from a.vendor_id or l.contractor_id is not null))
 union all
 select 'AP_PREPAYMENT_GL_SUBLEDGER','CRITICAL',count(*)::bigint,'Each dedicated advance account equals current remaining balances across all sources'
 from (select a.coa_account_id,sum((erp.initial_prepayment_state_v1(a.id)->>'remaining_amount')::numeric
   *case when a.party_type='CUSTOMER' then -1 else 1 end) expected from erp.initial_import_prepayments a group by a.coa_account_id) x
 where x.expected is distinct from (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
   join erp.journal_entries j on j.id=l.journal_entry_id where l.account_id=x.coa_account_id and j.status in('POSTED','REVERSED'));
$function$;
revoke all on function erp.initial_prepayment_checks_v1() from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.opening_cash_advance_state_v1(p_balance_id uuid)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' AS $function$
 select jsonb_build_object('balance_id',b.id,'contractor_id',b.contractor_id,
   'document_number',s.document_number,'document_date',s.document_date,'cutover_date',s.cutover_date,
   'original_amount',s.original_amount::text,'settled_before_cutover',s.settled_before_cutover::text,
   'opening_amount',b.original_amount::text,'settled_amount',b.settled_amount::text,
   'remaining_amount',(b.original_amount-b.settled_amount)::text,
   'reserved_amount',x.reserved::numeric(20,2)::text,
   'available_amount',(b.original_amount-b.settled_amount-x.reserved)::numeric(20,2)::text,
   'status',b.status)
 from erp.opening_subledger_balances b
 join erp.initial_import_financial_sources s on s.opening_item_id=b.opening_item_id
   and s.source_kind='CONTRACTOR_CASH_ADVANCE'
 cross join lateral(select coalesce(sum(d.amount),0) reserved
   from erp.payroll_deductions d join erp.payroll_settlements p on p.id=d.payroll_id
   where d.opening_cash_advance_balance_id=b.id and p.status not in('PAID','REVERSED')) x
 where b.id=p_balance_id;
$function$;
revoke all on function erp.opening_cash_advance_state_v1(uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.initial_import_revision_v1(p_batch_id uuid)
RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' SET TimeZone TO 'UTC' AS $function$
 select encode(extensions.digest(convert_to(jsonb_build_object(
   'batch',(select to_jsonb(b) from erp.migration_batches b where id=p_batch_id),
   'rows',coalesce((select jsonb_agg(to_jsonb(s) order by s.entity_type,s.source_row_no)
     from erp.migration_staging_rows s where s.batch_id=p_batch_id),'[]'::jsonb),
   'opening',coalesce((select jsonb_agg(to_jsonb(h) order by h.id)
     from erp.opening_balance_headers h where h.migration_batch_id=p_batch_id),'[]'::jsonb),
   'advance_balances',coalesce((select jsonb_agg(to_jsonb(bs) order by bs.id)
     from erp.opening_subledger_balances bs join erp.initial_import_financial_sources s on s.opening_item_id=bs.opening_item_id
     where s.batch_id=p_batch_id and s.source_kind='CONTRACTOR_CASH_ADVANCE'),'[]'::jsonb),
   'advance_deductions',coalesce((select jsonb_agg(to_jsonb(d) order by d.id)
     from erp.payroll_deductions d join erp.opening_subledger_balances bs on bs.id=d.opening_cash_advance_balance_id
     join erp.initial_import_financial_sources s on s.opening_item_id=bs.opening_item_id where s.batch_id=p_batch_id),'[]'::jsonb),
   'advance_payrolls',coalesce((select jsonb_agg(to_jsonb(p) order by p.id) from erp.payroll_settlements p
     where exists(select 1 from erp.initial_import_financial_sources s where s.batch_id=p_batch_id
       and s.source_kind='CONTRACTOR_CASH_ADVANCE' and s.party_id=p.contractor_id)),'[]'::jsonb),
   'prepayments',coalesce((select jsonb_agg(to_jsonb(a)||jsonb_build_object(
     'events',(select jsonb_agg(to_jsonb(e) order by e.id) from erp.initial_import_prepayment_events e where e.advance_id=a.id),
     'payments',(select jsonb_agg(to_jsonb(p) order by p.payment_id) from erp.initial_prepayment_payments_v1(a.id) p),
     'targets',(select jsonb_agg(to_jsonb(t) order by t.id) from erp.initial_prepayment_targets_v1(a.id) t)
   ) order by a.id) from erp.initial_import_prepayments a where a.batch_id=p_batch_id),'[]'::jsonb),
   'items',coalesce((select jsonb_agg(to_jsonb(i) order by i.id)
     from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id
     where h.migration_batch_id=p_batch_id),'[]'::jsonb)
 )::text,'UTF8'),'sha256'),'hex');
$function$;
revoke all on function erp.initial_import_revision_v1(uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.get_initial_import_workspace_v1(p_batch_id uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare b erp.migration_batches%rowtype; v_batch jsonb;
begin
 perform erp.require_owner_admin();
 perform erp.require_permission('settings.erp.view');
 if p_batch_id is not null then
   select * into b from erp.migration_batches where id=p_batch_id for share;
   if b.id is null then raise exception 'Batch impor tidak ditemukan'; end if;
   select jsonb_build_object('id',b.id,'code',b.batch_code,'status',b.status,
     'cutover_at',b.cutover_at,'notes',b.notes,'revision',erp.initial_import_revision_v1(b.id),
     'rows',coalesce((select jsonb_agg(jsonb_build_object(
       'id',s.id,'entity',s.entity_type,'source_row_no',s.source_row_no,
       'payload',s.normalized_payload,'validation_status',s.validation_status,
       'errors',s.validation_errors,'applied',s.posted_entity_id is not null
     ) order by s.entity_type,s.source_row_no) from erp.migration_staging_rows s where s.batch_id=b.id),'[]'::jsonb),
     'uninvoiced_receipts',coalesce((select jsonb_agg(jsonb_build_object(
       'receipt_number',rh.receipt_number,'receipt_line_number',rl.receipt_line_number,'receipt_date',rh.receipt_date,
       'cutover_date',rh.cutover_date,'purchase_id',rh.purchase_id,'purchase_item_id',rl.purchase_item_id,
       'supplier_id',rh.supplier_id,'opening_item_id',rl.opening_item_id,
       'qty',pi.qty,'on_hand_at_cutover',coalesce((select qty from erp.opening_balance_items where id=rl.opening_item_id),0),
       'consumed_before_cutover',coalesce((select sum(material_qty) from erp.initial_import_cost_origins where purchase_item_id=pi.id),0),'unmatched_qty',erp.material_purchase_invoice_capacity(pi.id)-erp.material_purchase_posted_invoice_qty(pi.id),
       'invoice_match_state',pi.invoice_match_state) order by rh.receipt_number,rl.receipt_line_number)
       from erp.initial_import_receipt_headers rh join erp.initial_import_receipt_lines rl on rl.purchase_id=rh.purchase_id
       join erp.material_purchase_items pi on pi.id=rl.purchase_item_id where rh.batch_id=b.id),'[]'::jsonb),
     'cash_advances',coalesce((select jsonb_agg(erp.opening_cash_advance_state_v1(bs.id)||jsonb_build_object(
       'contractor_code',c.contractor_code,'contractor_name',c.contractor_name,
       'allocations',coalesce((select jsonb_agg(jsonb_build_object('payroll_id',p.id,'payroll_number',p.payroll_number,
         'status',p.status,'row_version',p.row_version::text,'amount',d.amount::text) order by p.period_end,p.id)
         from erp.payroll_deductions d join erp.payroll_settlements p on p.id=d.payroll_id
         where d.opening_cash_advance_balance_id=bs.id and p.status<>'REVERSED'),'[]'::jsonb)) order by s.document_number,bs.id)
       from erp.initial_import_financial_sources s join erp.opening_subledger_balances bs on bs.opening_item_id=s.opening_item_id
       join erp.contractors c on c.id=bs.contractor_id where s.batch_id=b.id and s.source_kind='CONTRACTOR_CASH_ADVANCE'),'[]'::jsonb),
     'advance_payrolls',coalesce((select jsonb_agg(to_jsonb(x) order by x.period_end,x.id) from(
       select p.id,p.payroll_number,p.contractor_id,p.period_end,p.row_version::text,p.net_payable::text
       from erp.payroll_settlements p where p.status in('DRAFT','CALCULATED','REVIEW') and exists(
         select 1 from erp.initial_import_financial_sources s where s.batch_id=b.id
           and s.source_kind='CONTRACTOR_CASH_ADVANCE' and s.party_id=p.contractor_id)
       order by p.period_end,p.id limit 100) x),'[]'::jsonb),
     'prepayments',coalesce((select jsonb_agg(erp.initial_prepayment_state_v1(a.id)||jsonb_build_object(
       'party_name',case a.party_type when 'SUPPLIER' then (select supplier_name from erp.suppliers where id=a.party_id)
         when 'CUSTOMER' then (select customer_name from erp.customers where id=a.party_id) else (select vendor_name from erp.laundry_vendors where id=a.party_id) end,
       'targets',coalesce((select jsonb_agg(to_jsonb(t) order by t.target_date,t.id) from (
         select * from erp.initial_prepayment_targets_v1(a.id) where remaining_amount::numeric>0 order by target_date,id limit 100) t),'[]'::jsonb),
       'payments',coalesce((select jsonb_agg(jsonb_build_object('id',p.payment_id,'number',p.number,'status',p.status,'amount',p.amount::numeric(20,2)::text) order by p.payment_date,p.payment_id)
         from erp.initial_prepayment_payments_v1(a.id) p),'[]'::jsonb),
       'events',coalesce((select jsonb_agg(jsonb_build_object('id',e.id,'kind',e.event_type,'delta',e.delta::text,'date',e.effective_date,'reason',e.reason,
         'reversed',exists(select 1 from erp.initial_import_prepayment_events x where x.reverses_event_id=e.id)) order by e.created_at,e.id)
         from erp.initial_import_prepayment_events e where e.advance_id=a.id),'[]'::jsonb)) order by a.document_number,a.id)
       from erp.initial_import_prepayments a where a.batch_id=b.id),'[]'::jsonb),
     'prepayment_cash_accounts',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',cash_account_name) order by cash_account_code)
       from erp.cash_accounts where is_active),'[]'::jsonb),
     'production_sources',erp.initial_import_production_rows_v1(b.id),
     'opening_id',(select h.id from erp.opening_balance_headers h where h.migration_batch_id=b.id order by h.created_at limit 1)
   ) into v_batch;
 end if;
 return jsonb_build_object('batch',v_batch,'recent',coalesce((select jsonb_agg(x order by x.created_at desc,x.id)
   from (select id,batch_code,status,cutover_at,created_at from erp.migration_batches
     order by created_at desc,id limit 50) x),'[]'::jsonb));
end;$function$;
revoke all on function erp.get_initial_import_workspace_v1(uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.save_initial_import_action_v1(
 p_action text,p_payload jsonb,p_client_request_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare
 v_action text:=upper(btrim(p_action)); v_batch uuid; v_type text;
 b erp.migration_batches%rowtype; v_cached jsonb; v_result jsonb; v_row jsonb; v_normal jsonb;
 v_field text; v_text text; v_number numeric; v_line integer; v_seen integer[]:='{}';
 v_total bigint; v_valid bigint; v_errors bigint; v_opening uuid; v_date date;
 v_catalog constant jsonb:='{"LAUNDRY_VENDOR": {"label": "Vendor laundry", "required": ["vendor_code", "vendor_name"], "fields": {"vendor_code": "Kode laundry", "vendor_name": "Nama laundry", "phone": "Telepon", "is_active": "Aktif", "notes": "Catatan"}}, "LOCATION": {"label": "Lokasi dan gudang", "required": ["location_code", "location_name", "location_type"], "fields": {"location_code": "Kode lokasi", "location_name": "Nama lokasi", "location_type": "Jenis lokasi", "is_active": "Aktif"}}, "CHART_ACCOUNT": {"label": "Akun buku besar", "required": ["account_code", "account_name", "account_type", "report_group", "normal_balance"], "fields": {"account_code": "Kode akun", "account_name": "Nama akun", "account_type": "Jenis akun", "report_group": "Kelompok laporan", "normal_balance": "Saldo normal", "parent_account_code": "Kode akun induk", "is_postable": "Boleh dipakai jurnal", "is_active": "Aktif"}}, "CASH_ACCOUNT": {"label": "Rekening kas dan bank", "required": ["cash_account_code", "cash_account_name", "coa_account_code", "account_kind"], "fields": {"cash_account_code": "Kode kas bank", "cash_account_name": "Nama kas bank", "coa_account_code": "Kode akun buku besar", "account_kind": "Jenis rekening", "is_active": "Aktif"}}, "BRAND": {"label": "Merek", "required": ["brand_code", "brand_name"], "fields": {"brand_code": "Kode merek", "brand_name": "Nama merek", "is_active": "Aktif"}}, "SIZE": {"label": "Ukuran", "required": ["size_code"], "fields": {"size_code": "Kode ukuran", "sort_order": "Urutan", "is_active": "Aktif"}}, "MODEL": {"label": "Model produk", "required": ["model_code", "model_name"], "fields": {"model_code": "Kode model", "model_name": "Nama model", "description": "Keterangan", "is_active": "Aktif"}}, "PRODUCT": {"label": "Produk per ukuran", "required": ["sku", "product_name", "model_code", "brand_code", "color_name", "size_code"], "fields": {"sku": "Kode produk", "product_name": "Nama produk", "model_code": "Kode model", "brand_code": "Kode merek", "color_name": "Warna", "size_code": "Kode ukuran", "is_active": "Aktif"}}, "CUSTOMER": {"label": "Pelanggan", "required": ["customer_code", "customer_name"], "fields": {"customer_code": "Kode pelanggan", "customer_name": "Nama pelanggan", "phone": "Telepon", "address": "Alamat", "is_active": "Aktif"}}, "SUPPLIER": {"label": "Supplier", "required": ["supplier_code", "supplier_name"], "fields": {"supplier_code": "Kode supplier", "supplier_name": "Nama supplier", "supplier_type": "Jenis supplier", "phone": "Telepon", "address": "Alamat", "is_active": "Aktif"}}, "CONTRACTOR": {"label": "Mandor", "required": ["contractor_code", "contractor_name"], "fields": {"contractor_code": "Kode mandor", "contractor_name": "Nama mandor", "contractor_type": "Jenis mandor", "attendance_required": "Wajib absensi", "is_active": "Aktif", "notes": "Catatan"}}, "ACCESSORY_CATEGORY": {"label": "Kategori aksesori", "required": ["category_code", "category_name", "base_uom_code"], "fields": {"category_code": "Kode kategori", "category_name": "Nama kategori", "base_uom_code": "Satuan dasar", "is_active": "Aktif", "notes": "Catatan"}}, "MATERIAL": {"label": "Bahan dan aksesori", "required": ["material_sku", "material_name", "material_type", "unit_code"], "fields": {"material_sku": "Kode bahan", "material_name": "Nama bahan", "material_type": "Jenis bahan", "unit_code": "Satuan dasar", "accessory_category_code": "Kode kategori aksesori", "is_active": "Aktif"}}, "MATERIAL_ROLL": {"label": "Stok awal kain per roll", "required": ["material_sku", "roll_number", "opening_qty", "unit_cost", "location_code", "control_key"], "fields": {"material_sku": "Kode bahan", "roll_number": "Nomor roll", "opening_qty": "Jumlah awal", "unit_cost": "Biaya per satuan", "location_code": "Kode gudang", "supplier_code": "Kode supplier", "notes": "Catatan", "control_key": "Kode total pembanding", "opening_source_key": "Kode rincian stok asal"}}, "OPENING_BALANCE_ITEM": {"label": "Stok dan saldo awal", "required": ["balance_type", "control_key"], "fields": {"balance_type": "Jenis saldo", "material_sku": "Kode bahan", "product_sku": "Kode produk", "brand_code": "Kode merek", "model_code": "Kode model", "color_name": "Warna", "size_code": "Kode ukuran", "location_code": "Kode gudang", "contractor_code": "Kode mandor", "customer_code": "Kode pelanggan", "supplier_code": "Kode supplier", "vendor_code": "Kode laundry", "cash_account_code": "Kode kas bank", "stage": "Tahap produksi", "qty": "Jumlah", "unit_cost": "Biaya per satuan", "amount": "Nominal", "quality_grade": "Kualitas", "hpp_input_method": "Cara isi HPP", "hpp_percent_of_price": "Persentase HPP", "notes": "Catatan", "control_key": "Kode total pembanding", "document_number": "Nomor dokumen asal", "document_date": "Tanggal dokumen asal", "due_date": "Tanggal jatuh tempo", "original_amount": "Nominal dokumen awal", "settled_before_cutover": "Sudah dibayar sebelum saldo awal", "opening_source_key": "Kode rincian stok asal", "source_kind": "Jenis sumber saldo", "po_number": "Nomor PO saldo fisik", "accessory_cost_included": "Biaya aksesoris sudah termasuk (true/false)"}}, "OPEN_PO": {"label": "Pesanan produksi berjalan", "required": ["po_number", "model_code", "status", "current_stage"], "fields": {"po_number": "Nomor pesanan", "model_code": "Kode model", "contractor_code": "Kode mandor", "target_qty_pcs": "Target buah", "target_dozens": "Target lusin", "status": "Status", "current_stage": "Tahap produksi", "physical_start_at": "Waktu mulai fisik", "notes": "Catatan"}}, "OPENING_CONTROL": {"label": "Total pembanding saldo awal", "required": ["control_key", "balance_type", "amount"], "fields": {"control_key": "Kode total pembanding", "balance_type": "Jenis saldo", "qty": "Total jumlah", "amount": "Total nominal", "notes": "Catatan"}}, "UNINVOICED_RECEIPT": {"label": "Penerimaan belum ditagih — sisa bahan dan asal biaya", "required": ["receipt_number", "receipt_line_number", "receipt_date", "supplier_code", "material_sku", "location_code", "qty", "unit_cost", "control_key"], "fields": {"receipt_number": "Nomor penerimaan asal", "receipt_line_number": "Nomor baris penerimaan", "receipt_date": "Tanggal penerimaan asal", "supplier_code": "Kode supplier", "material_sku": "Kode bahan", "location_code": "Kode gudang", "qty": "Jumlah belum ditagih", "unit_cost": "Biaya estimasi per satuan", "opening_source_key": "Kode rincian stok asal", "control_key": "Kode total pembanding", "notes": "Catatan"}}, "OPENING_ADVANCE": {"label": "Uang muka tersisa", "required": ["party_type", "party_code", "coa_account_code", "document_number", "document_date", "original_amount", "settled_before_cutover", "amount", "control_key"], "fields": {"party_type": "Jenis pihak", "party_code": "Kode pihak", "coa_account_code": "Kode akun uang muka", "document_number": "Nomor bukti uang muka", "document_date": "Tanggal uang muka", "original_amount": "Nominal asal", "settled_before_cutover": "Terpakai atau kembali sebelum saldo awal", "amount": "Sisa uang muka", "control_key": "Kode total pembanding"}}, "OPENING_COST_ORIGIN": {"label": "Asal biaya yang sudah terpakai sebelum cutover", "fields": {"supplier_code": "Kode supplier", "receipt_number": "Nomor penerimaan asal", "receipt_line_number": "Nomor baris penerimaan", "target_source_key": "Kode rincian WIP/BS/FG tujuan", "qty": "Jumlah bahan yang sudah terpakai", "notes": "Catatan"}, "required": ["supplier_code", "receipt_number", "receipt_line_number", "target_source_key", "qty"]}}'::jsonb;
begin
 perform erp.require_owner_admin();
 perform erp.require_permission('settings.erp.view');
 if v_action is null or v_action not in('CREATE','SAVE_FILE','VALIDATE','FINALIZE','ALLOCATE_CASH_ADVANCE','PREPAYMENT','WIP_OUTPUT') then raise exception 'Aksi impor tidak dikenal'; end if;
 if p_payload is null or jsonb_typeof(p_payload)<>'object' or octet_length(p_payload::text)>5242880 then
   raise exception 'Isi impor harus berupa objek dan maksimal 5 MB'; end if;
 v_cached:=erp._idempotency_begin('save_initial_import_action_v1',p_client_request_id,
   erp._request_hash(jsonb_build_object('action',v_action,'payload',p_payload)));
 if v_cached is not null then return v_cached; end if;
 perform set_config('app.change_reason','Impor awal: '||v_action,true);
 if v_action='CREATE' then
   if p_payload->>'cutover_date' is null or p_payload->>'cutover_date' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then
     raise exception 'Tanggal saldo awal wajib memakai YYYY-MM-DD'; end if;
   v_date:=(p_payload->>'cutover_date')::date;
   if v_date::text<>p_payload->>'cutover_date' or v_date>(statement_timestamp() at time zone 'Asia/Jakarta')::date then
     raise exception 'Tanggal saldo awal tidak valid atau berada di masa depan'; end if;
   v_batch:=erp.create_migration_batch(p_payload->>'batch_code',v_date::timestamp at time zone 'Asia/Jakarta',
     'CSV UTF-8',p_payload->>'notes');
 elsif v_action='WIP_OUTPUT' then
   v_batch:=(p_payload->>'batch_id')::uuid;
   v_result:=erp.complete_initial_import_wip_v1(p_payload);
   v_result:=v_result||jsonb_build_object('request_id',p_client_request_id,'action',v_action,'batch_id',v_batch,'status','POSTED');
   return erp._idempotency_complete('save_initial_import_action_v1',p_client_request_id,v_result);
 elsif v_action='PREPAYMENT' then
   v_batch:=(p_payload->>'batch_id')::uuid;
   select * into b from erp.migration_batches where id=v_batch for update;
   if b.id is null or b.status<>'POSTED' then raise exception 'Uang muka harus berasal dari impor yang sudah disahkan';end if;
   perform erp.manage_initial_prepayment_v1(p_payload);
 elsif v_action='ALLOCATE_CASH_ADVANCE' then
   v_batch:=nullif(p_payload->>'batch_id','')::uuid;
   select * into b from erp.migration_batches where id=v_batch for update;
   if b.id is null or b.status<>'POSTED' then raise exception 'Kasbon harus berasal dari impor yang sudah disahkan';end if;
   perform 1 from erp.payroll_settlements where id=(p_payload->>'payroll_id')::uuid for update;
   perform 1 from erp.opening_subledger_balances where id=(p_payload->>'balance_id')::uuid for update;
   if p_payload->>'expected_revision' is distinct from erp.initial_import_revision_v1(b.id) then
     raise exception 'STALE_VERSION: saldo atau payroll berubah; muat ulang sebelum mengalokasikan';end if;
   if not exists(select 1 from erp.initial_import_financial_sources s join erp.opening_subledger_balances bs on bs.opening_item_id=s.opening_item_id
     where s.batch_id=b.id and s.source_kind='CONTRACTOR_CASH_ADVANCE' and bs.id=(p_payload->>'balance_id')::uuid) then
     raise exception 'Saldo kasbon bukan milik batch ini';end if;
   if coalesce(p_payload->>'amount','') !~ '^[0-9]+([.,][0-9]{1,2})?$' then
     raise exception 'amount: gunakan nominal positif tepat dua desimal atau nol untuk melepas alokasi';end if;
   perform erp.set_opening_cash_advance_payroll_v1((p_payload->>'balance_id')::uuid,
     (p_payload->>'payroll_id')::uuid,replace(p_payload->>'amount',',','.')::numeric,
     (p_payload->>'expected_payroll_version')::bigint);
 else
   v_batch:=nullif(p_payload->>'batch_id','')::uuid;
   select * into b from erp.migration_batches where id=v_batch for update;
   if b.id is null then raise exception 'Batch impor tidak ditemukan'; end if;
   if b.status not in('DRAFT','READY','VALIDATING','POSTING') or exists(
     select 1 from erp.opening_balance_headers where migration_batch_id=b.id and status<>'DRAFT') then
     raise exception 'Impor yang sudah disahkan tidak dapat diedit atau disahkan ulang dengan permintaan baru'; end if;
   if nullif(p_payload->>'expected_revision','') is null
     or p_payload->>'expected_revision'<>erp.initial_import_revision_v1(b.id) then
     raise exception 'STALE_VERSION: isi impor berubah. Muat ulang sebelum melanjutkan'; end if;
   if v_action='SAVE_FILE' then
     v_type:=p_payload->>'entity';
     if v_type is null or not v_catalog ? v_type then raise exception 'Jenis file impor tidak didukung'; end if;
     if jsonb_typeof(p_payload->'rows') is distinct from 'array'
       or jsonb_array_length(p_payload->'rows')>5000 then raise exception 'Maksimal 5000 baris per file'; end if;
     if (select count(*) from erp.migration_staging_rows where batch_id=b.id and entity_type<>v_type)
       +jsonb_array_length(p_payload->'rows')>5000 then raise exception 'Maksimal 5000 baris per batch; pecah menjadi batch terpisah'; end if;
     if exists(select 1 from erp.migration_staging_rows where batch_id=b.id
       and posted_entity_id is not null and entity_type<>'OPENING_BALANCE_ITEM') then
       raise exception 'Batch ini sudah menerapkan master melalui jalur lama; selesaikan di jalur asal'; end if;
     perform 1 from erp.opening_balance_headers where migration_batch_id=b.id order by id for update;
     delete from erp.opening_balance_items i using erp.opening_balance_headers h
       where i.opening_id=h.id and h.migration_batch_id=b.id and h.status='DRAFT';
     update erp.migration_staging_rows set posted_entity_type=null,posted_entity_id=null,posted_at=null
       where batch_id=b.id and entity_type='OPENING_BALANCE_ITEM';
     delete from erp.migration_staging_rows where batch_id=b.id and entity_type=v_type;
     for v_row in select value from jsonb_array_elements(p_payload->'rows') loop
       if jsonb_typeof(v_row)<>'object' or jsonb_typeof(v_row->'payload') is distinct from 'object'
         or coalesce(v_row->>'source_row_no','') !~ '^[1-9][0-9]{0,6}$' then raise exception 'Identitas baris impor tidak valid'; end if;
       v_line:=(v_row->>'source_row_no')::integer;
       if v_line=any(v_seen) then raise exception 'Baris sumber % ditulis dua kali',v_line; end if;
       v_seen:=array_append(v_seen,v_line);v_normal:='{}'::jsonb;
       for v_field,v_text in select key,value #>> '{}' from jsonb_each(v_row->'payload') loop
         if not (v_catalog->v_type->'fields') ? v_field or jsonb_typeof(v_row->'payload'->v_field)<>'string' then
           raise exception 'Baris %, kolom %: nama kolom atau tipe data tidak valid',v_line,v_field; end if;
         v_text:=btrim(v_text);
         if length(v_text)>20000 then raise exception 'Baris %, kolom % terlalu panjang',v_line,v_field; end if;
         if v_field in('qty','opening_qty','unit_cost','amount','original_amount','settled_before_cutover','hpp_percent_of_price','target_dozens','target_qty_pcs','sort_order') and v_text<>'' then
           if v_text !~ '^-?[0-9]+([.,][0-9]+)?$' then
             raise exception 'Baris %, kolom %: isi angka tanpa pemisah ribuan',v_line,v_field; end if;
           v_text:=replace(v_text,',','.');v_number:=v_text::numeric;
           if (v_field in('amount','original_amount','settled_before_cutover') and v_number<>round(v_number,2))
             or (v_field in('qty','opening_qty','unit_cost','target_dozens') and v_number<>round(v_number,6))
             or (v_field='hpp_percent_of_price' and v_number<>round(v_number,4))
             or (v_field in('target_qty_pcs','sort_order') and v_number<>trunc(v_number)) then
             raise exception 'Baris %, kolom %: ketelitian angka melebihi kolom tujuan; angka tidak dibulatkan otomatis',v_line,v_field; end if;
         end if;
         v_normal:=v_normal||jsonb_build_object(v_field,v_text);
       end loop;
       perform erp.stage_migration_row(b.id,v_type,v_line,null,
         (v_row->'payload')||jsonb_build_object('_filename',left(coalesce(p_payload->>'filename',''),255)),v_normal);
     end loop;
     update erp.migration_batches set status='DRAFT',validated_at=null,error_message=null where id=b.id;
   else
     if not exists(select 1 from erp.migration_staging_rows where batch_id=b.id) then raise exception 'Unggah data sebelum memeriksa atau mengesahkan'; end if;
     select * into v_total,v_valid,v_errors from erp.validate_migration_batch(b.id);
     perform erp.validate_initial_import_financial_sources_v1(b.id);
     perform erp.validate_initial_import_production_v1(b.id);
     perform erp.validate_initial_import_cost_origins_v1(b.id);
     perform erp.validate_initial_import_receipts_v1(b.id);
     perform erp.validate_initial_prepayments_v1(b.id);
     perform erp.validate_initial_import_totals_v1(b.id);
     select count(*),count(*) filter(where validation_status='VALID'),count(*) filter(where validation_status='ERROR')
       into v_total,v_valid,v_errors from erp.migration_staging_rows where batch_id=b.id;
     if v_action='FINALIZE' and v_errors=0 then
       -- Domain writers execute inside this same transaction. A refusal in any
       -- consumer rolls back masters, opening stock, journals, and application.
       perform erp.apply_migration_master_rows(b.id);
       perform erp.apply_migration_open_pos(b.id);
       if exists(select 1 from erp.migration_staging_rows where batch_id=b.id
         and entity_type in('OPENING_BALANCE_ITEM','MATERIAL_ROLL')) then
         v_opening:=erp.prepare_migration_opening_balance(b.id,null);
         perform erp.post_opening_balance(v_opening);
       end if;
       perform erp.apply_initial_import_receipts_v1(b.id);
       perform erp.apply_initial_prepayments_v1(b.id);
       perform erp.finalize_migration_batch(b.id);
     end if;
   end if;
 end if;
 v_result:=jsonb_build_object('request_id',p_client_request_id,'action',v_action,'batch_id',v_batch,
   'status',(select status from erp.migration_batches where id=v_batch),'total_rows',v_total,
   'valid_rows',v_valid,'error_rows',v_errors,'revision',erp.initial_import_revision_v1(v_batch));
 return erp._idempotency_complete('save_initial_import_action_v1',p_client_request_id,v_result);
end;$function$;
revoke all on function erp.save_initial_import_action_v1(text,jsonb,uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION public.erp_get_initial_import_workspace_v1(p_batch_id uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path TO '' AS $function$
 select erp.get_initial_import_workspace_v1(p_batch_id);
$function$;
revoke all on function public.erp_get_initial_import_workspace_v1(uuid) from public,anon,authenticated,service_role;
grant execute on function public.erp_get_initial_import_workspace_v1(uuid) to authenticated,service_role;
CREATE OR REPLACE FUNCTION public.erp_save_initial_import_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path TO '' AS $function$
 select erp.save_initial_import_action_v1(p_action,p_payload,p_client_request_id);
$function$;
revoke all on function public.erp_save_initial_import_action_v1(text,jsonb,uuid) from public,anon,authenticated,service_role;
grant execute on function public.erp_save_initial_import_action_v1(text,jsonb,uuid) to authenticated,service_role;
CREATE OR REPLACE FUNCTION erp._validate_migration_batch_base(p_batch_id uuid)
 RETURNS TABLE(total_rows bigint, valid_rows bigint, error_rows bigint)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare r record;e jsonb;v_required text[];k text;v_total bigint;v_valid bigint;v_error bigint;v_bt text;v_material_type text;v_number numeric;v_status text;v_cutover timestamptz;ref record;v_code text;v_exists boolean;v_typed jsonb;
begin
  perform erp.require_owner_admin();
  select status into v_status from erp.migration_batches where id=p_batch_id for update;
  if v_status is null then raise exception 'Migration batch not found'; end if;
  if v_status not in('DRAFT','VALIDATING','READY','POSTING')
     or exists(select 1 from erp.opening_balance_headers where migration_batch_id=p_batch_id and status<>'DRAFT') then
    raise exception 'AK_MIGRATION_PREVIEW_AFTER_POSTING_REFUSED';
  end if;
  select cutover_at into v_cutover from erp.migration_batches where id=p_batch_id;
  update erp.migration_batches set status='VALIDATING',error_message=null where id=p_batch_id;
  update erp.migration_staging_rows set validation_status='PENDING',validation_errors='[]'::jsonb,updated_at=statement_timestamp() where batch_id=p_batch_id;
  update erp.migration_staging_rows s set validation_status='ERROR',validation_errors=jsonb_build_array('Duplicate legacy_key inside entity type'),updated_at=statement_timestamp()
  where s.batch_id=p_batch_id and s.legacy_key is not null and exists(select 1 from erp.migration_staging_rows d where d.batch_id=s.batch_id and d.entity_type=s.entity_type and d.legacy_key=s.legacy_key and d.id<>s.id);

  with keys as (
    select id,entity_type,case entity_type
      when 'PRODUCT' then jsonb_build_array(normalized_payload->>'brand_code',lower(btrim(normalized_payload->>'sku')),normalized_payload->>'size_code')
      else jsonb_build_array(normalized_payload->>case entity_type
        when 'LAUNDRY_VENDOR' then 'vendor_code' when 'LOCATION' then 'location_code' when 'CHART_ACCOUNT' then 'account_code' when 'CASH_ACCOUNT' then 'cash_account_code' when 'BRAND' then 'brand_code' when 'SIZE' then 'size_code' when 'MODEL' then 'model_code'
        when 'CUSTOMER' then 'customer_code' when 'SUPPLIER' then 'supplier_code' when 'CONTRACTOR' then 'contractor_code'
        when 'ACCESSORY_CATEGORY' then 'category_code' when 'MATERIAL' then 'material_sku' when 'OPEN_PO' then 'po_number' end) end business_key
    from erp.migration_staging_rows where batch_id=p_batch_id and entity_type not in('MATERIAL_ROLL','OPENING_BALANCE_ITEM','OPENING_CONTROL','OPENING_COST_ORIGIN','UNINVOICED_RECEIPT','OPENING_ADVANCE')
  ) update erp.migration_staging_rows s set validation_status='ERROR',
      validation_errors=s.validation_errors||jsonb_build_array('Duplicate master/PO identity inside migration batch')
    where s.id in(select k.id from keys k where exists(select 1 from keys d
      where d.id<>k.id and d.entity_type=k.entity_type and d.business_key=k.business_key));

  for r in select * from erp.migration_staging_rows where batch_id=p_batch_id order by case entity_type
      when 'LAUNDRY_VENDOR' then 1 when 'LOCATION' then 2 when 'CHART_ACCOUNT' then 3 when 'CASH_ACCOUNT' then 4 when 'BRAND' then 10 when 'SIZE' then 20 when 'MODEL' then 30
      when 'CUSTOMER' then 40 when 'SUPPLIER' then 50 when 'CONTRACTOR' then 60
      when 'ACCESSORY_CATEGORY' then 70 when 'MATERIAL' then 80 when 'MATERIAL_ROLL' then 85
      when 'PRODUCT' then 90 when 'OPEN_PO' then 100 else 110 end,source_row_no loop
    e:='[]'::jsonb;
    begin
      -- A malformed input is a row error. It must not roll back diagnostics
      -- for the entire batch or be accepted as NaN/infinite business quantity.
      foreach k in array array['qty','opening_qty','unit_cost','amount',
        'hpp_percent_of_price','target_qty_pcs','target_dozens'] loop
        if nullif(btrim(r.normalized_payload->>k),'') is not null then
          v_number:=(r.normalized_payload->>k)::numeric;
          if v_number::text in('NaN','Infinity','-Infinity') then
            e:=e||jsonb_build_array('Field must be a finite number: '||k);
          end if;
        end if;
      end loop;
    if jsonb_typeof(r.normalized_payload)<>'object' then e:=e||jsonb_build_array('normalized_payload must be a JSON object'); end if;
    v_required:=case r.entity_type
      when 'LAUNDRY_VENDOR' then array['vendor_code','vendor_name']
      when 'LOCATION' then array['location_code','location_name','location_type']
      when 'CHART_ACCOUNT' then array['account_code','account_name','account_type','report_group','normal_balance']
      when 'CASH_ACCOUNT' then array['cash_account_code','cash_account_name','coa_account_code','account_kind']
      when 'BRAND' then array['brand_code','brand_name']
      when 'SIZE' then array['size_code']
      when 'MODEL' then array['model_code','model_name']
      when 'PRODUCT' then array['sku','product_name','model_code','brand_code','color_name','size_code']
      when 'CUSTOMER' then array['customer_code','customer_name']
      when 'SUPPLIER' then array['supplier_code','supplier_name']
      when 'CONTRACTOR' then array['contractor_code','contractor_name']
      when 'ACCESSORY_CATEGORY' then array['category_code','category_name','base_uom_code']
      when 'MATERIAL' then array['material_sku','material_name','material_type','unit_code']
      when 'MATERIAL_ROLL' then array['material_sku','roll_number','opening_qty','unit_cost','location_code']
      when 'OPENING_BALANCE_ITEM' then array['balance_type']
      when 'OPEN_PO' then array['po_number','model_code','status','current_stage']
      else array[]::text[] end;
    foreach k in array v_required loop
      if nullif(trim(coalesce(r.normalized_payload->>k,'')),'') is null then e:=e||jsonb_build_array('Missing required field: '||k); end if;
    end loop;

    -- Validate only fields consumed by the matching writer. Composite casts
    -- enforce the actual column types/widths without inserting any master.
    -- Empty optional values retain the writers' existing default semantics.
    for ref in select * from(values
      ('LAUNDRY_VENDOR','laundry_vendors',array['vendor_code','vendor_name','phone','is_active','notes']),
      ('LOCATION','locations',array['location_code','location_name','location_type','is_active']),
      ('CHART_ACCOUNT','chart_accounts',array['account_code','account_name','account_type','report_group','normal_balance','is_postable','is_active']),
      ('CASH_ACCOUNT','cash_accounts',array['cash_account_code','cash_account_name','account_kind','is_active']),
      ('BRAND','brands',array['brand_code','brand_name','is_active']),
      ('SIZE','sizes',array['size_code','sort_order','is_active']),
      ('MODEL','product_models',array['model_code','model_name','description','is_active']),
      ('PRODUCT','products',array['sku','product_name','color_name','is_active','is_portal_visible']),
      ('CUSTOMER','customers',array['customer_code','customer_name','phone','address','is_active']),
      ('SUPPLIER','suppliers',array['supplier_code','supplier_name','supplier_type','phone','address','is_active']),
      ('CONTRACTOR','contractors',array['contractor_code','contractor_name','contractor_type','attendance_required','is_active','notes']),
      ('ACCESSORY_CATEGORY','accessory_categories',array['category_code','category_name','base_uom_code','is_active','notes']),
      ('MATERIAL','materials',array['material_sku','material_name','material_type','unit_code','is_active']),
      ('MATERIAL_ROLL','material_rolls',array['roll_number','notes']),
      ('OPEN_PO','production_orders',array['po_number','target_qty_pcs','target_dozens','status','current_stage','physical_start_at','notes']),
      ('OPENING_BALANCE_ITEM','opening_balance_items',array['balance_type','qty','amount','stage','quality_grade','notes','hpp_input_method','hpp_percent_of_price'])
    ) fields(entity,relation_name,field_names) where fields.entity=r.entity_type loop
      select coalesce(jsonb_object_agg(field,r.normalized_payload->field),'{}'::jsonb)
        into v_typed from unnest(ref.field_names) field
        where nullif(r.normalized_payload->>field,'') is not null;
      begin
        execute format('select jsonb_populate_record(null::erp.%I,$1)',ref.relation_name) using v_typed;
      exception when data_exception then
        -- Retain the fast whole-row cast for valid imports. On a bad value,
        -- identify its field so the persisted row error tells the user what
        -- to repair; keep the original SQLSTATE and refusal semantics.
        for k in select jsonb_object_keys(v_typed) loop
          begin
            execute format('select jsonb_populate_record(null::erp.%I,$1)',ref.relation_name)
              using jsonb_build_object(k,v_typed->k);
          exception when data_exception then
            raise exception using errcode=sqlstate,message=format('%s: %s',k,sqlerrm);
          end;
        end loop;
        raise;
      end;
    end loop;
    perform erp.validate_initial_import_master_row_v1(p_batch_id,r.entity_type,r.normalized_payload);
    if r.entity_type='SUPPLIER' and coalesce(nullif(upper(r.normalized_payload->>'supplier_type'),''),'MATERIAL')
      not in('MATERIAL','ACCESSORY','OTHER') then raise exception 'supplier_type must be MATERIAL, ACCESSORY or OTHER'; end if;
    if r.entity_type='OPEN_PO' then
      if nullif(r.normalized_payload->>'target_qty_pcs','') is not null
         and (r.normalized_payload->>'target_qty_pcs')::integer<=0 then raise exception 'target_qty_pcs must be positive'; end if;
      if nullif(r.normalized_payload->>'target_dozens','') is not null
         and (r.normalized_payload->>'target_dozens')::numeric<=0 then raise exception 'target_dozens must be positive'; end if;
    end if;
    if r.entity_type='MATERIAL_ROLL' then
      perform (r.normalized_payload->>'opening_qty')::numeric(18,6);
      perform (r.normalized_payload->>'unit_cost')::numeric(18,6);
    end if;
    if r.entity_type='OPENING_BALANCE_ITEM' then
      if nullif(r.normalized_payload->>'unit_cost','') is not null then
        perform (r.normalized_payload->>'unit_cost')::numeric(18,6);
      end if;
      if upper(r.normalized_payload->>'balance_type')='BS' then
        v_number:=nullif(r.normalized_payload->>'qty','')::numeric;
        if v_number is null or v_number<=0 or v_number<>trunc(v_number) or v_number>2147483647 then
          raise exception 'AL_BS_REQUIRES_POSITIVE_WHOLE_PCS';
        end if;
      end if;
      if upper(r.normalized_payload->>'balance_type')='WIP' then
        if nullif(r.normalized_payload->>'amount','') is null and
           (nullif(r.normalized_payload->>'qty','') is null or nullif(r.normalized_payload->>'unit_cost','') is null) then
          raise exception 'AL_WIP_REQUIRES_AMOUNT_OR_QTY_AND_COST';
        end if;
        foreach k in array array['qty','amount','unit_cost'] loop
          if nullif(r.normalized_payload->>k,'') is not null and (r.normalized_payload->>k)::numeric<0 then
            raise exception 'AL_WIP_VALUE_MUST_BE_NONNEGATIVE: %',k;
          end if;
        end loop;
      end if;
    end if;
    if r.entity_type='ACCESSORY_CATEGORY' and not exists(select 1 from erp.uom_definitions where unit_code=upper(r.normalized_payload->>'base_uom_code')) then e:=e||jsonb_build_array('Unknown base_uom_code'); end if;
    if r.entity_type='MATERIAL' then
      if upper(coalesce(r.normalized_payload->>'material_type','')) not in('FABRIC','ACCESSORY','OTHER') then e:=e||jsonb_build_array('material_type must be FABRIC, ACCESSORY or OTHER'); end if;
      if upper(coalesce(r.normalized_payload->>'material_type',''))='ACCESSORY' and nullif(trim(coalesce(r.normalized_payload->>'accessory_category_code','')),'') is null then e:=e||jsonb_build_array('ACCESSORY material requires accessory_category_code'); end if;
    end if;
    if r.entity_type='MATERIAL_ROLL' then
      if coalesce(nullif(r.normalized_payload->>'opening_qty','')::numeric,0)<=0 then e:=e||jsonb_build_array('MATERIAL_ROLL opening_qty must be positive'); end if;
      if coalesce(nullif(r.normalized_payload->>'unit_cost','')::numeric,-1)<0 then e:=e||jsonb_build_array('MATERIAL_ROLL unit_cost must be zero or positive'); end if;
      select material_type into v_material_type from erp.materials where material_sku=r.normalized_payload->>'material_sku';
      if v_material_type is null then
        select upper(s.normalized_payload->>'material_type') into v_material_type from erp.migration_staging_rows s
        where s.batch_id=p_batch_id and s.entity_type='MATERIAL' and s.normalized_payload->>'material_sku'=r.normalized_payload->>'material_sku' limit 1;
      end if;
      if coalesce(v_material_type,'')<>'FABRIC' then e:=e||jsonb_build_array('MATERIAL_ROLL requires a FABRIC material'); end if;
      if not exists(select 1 from erp.locations where location_code=r.normalized_payload->>'location_code' and location_type='RAW_MATERIAL_WAREHOUSE' and is_active=true)
        and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='LOCATION'
          and s.validation_status='VALID' and s.normalized_payload->>'location_code'=r.normalized_payload->>'location_code'
          and upper(s.normalized_payload->>'location_type')='RAW_MATERIAL_WAREHOUSE'
          and coalesce(nullif(s.normalized_payload->>'is_active','')::boolean,true)) then e:=e||jsonb_build_array('MATERIAL_ROLL location_code must be an active raw-material warehouse'); end if;
      if nullif(trim(coalesce(r.normalized_payload->>'supplier_code','')),'') is not null
         and not exists(select 1 from erp.suppliers where supplier_code=r.normalized_payload->>'supplier_code')
         and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='SUPPLIER' and s.normalized_payload->>'supplier_code'=r.normalized_payload->>'supplier_code') then
        e:=e||jsonb_build_array('Unknown MATERIAL_ROLL supplier_code');
      end if;
      if exists(select 1 from erp.migration_staging_rows d where d.batch_id=p_batch_id and d.entity_type='MATERIAL_ROLL' and d.id<>r.id
                and d.normalized_payload->>'material_sku'=r.normalized_payload->>'material_sku' and d.normalized_payload->>'roll_number'=r.normalized_payload->>'roll_number') then
        e:=e||jsonb_build_array('Duplicate roll_number for material inside migration batch');
      end if;
      if exists(select 1 from erp.material_rolls mr join erp.materials m on m.id=mr.material_id where m.material_sku=r.normalized_payload->>'material_sku' and mr.roll_number=r.normalized_payload->>'roll_number' and mr.id is distinct from r.posted_entity_id) then
        e:=e||jsonb_build_array('MATERIAL_ROLL conflicts with an existing roll number');
      end if;
    end if;

    if r.entity_type='OPENING_BALANCE_ITEM' then
      v_bt:=upper(coalesce(r.normalized_payload->>'balance_type',''));
      if v_bt not in('MATERIAL','FINISHED_GOODS','WIP','BS','CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE','CUSTOMER_RECEIVABLE','VENDOR_PAYABLE','SUPPLIER_PAYABLE','CASH_BANK') then e:=e||jsonb_build_array('Unsupported opening balance_type for migration framework'); end if;
      if v_bt='MATERIAL' and(nullif(r.normalized_payload->>'material_sku','') is null or nullif(r.normalized_payload->>'location_code','') is null or coalesce(nullif(r.normalized_payload->>'qty','')::numeric,0)<=0) then e:=e||jsonb_build_array('MATERIAL opening needs material_sku, location_code and positive qty'); end if;
      if v_bt='MATERIAL' and exists(select 1 from erp.materials m where m.material_sku=r.normalized_payload->>'material_sku' and m.material_type='FABRIC') then e:=e||jsonb_build_array('FABRIC opening stock must use MATERIAL_ROLL rows, not anonymous MATERIAL opening'); end if;
      if v_bt='FINISHED_GOODS' and(nullif(r.normalized_payload->>'product_sku','') is null or coalesce(nullif(r.normalized_payload->>'qty','')::numeric,0)<=0) then e:=e||jsonb_build_array('FINISHED_GOODS opening needs product_sku and positive qty'); end if;
      if v_bt in('CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE') and(nullif(r.normalized_payload->>'contractor_code','') is null or coalesce(nullif(r.normalized_payload->>'amount','')::numeric,0)<=0) then e:=e||jsonb_build_array('Contractor opening balance needs contractor_code and positive amount'); end if;
      if v_bt='CUSTOMER_RECEIVABLE' and(nullif(r.normalized_payload->>'customer_code','') is null or coalesce(nullif(r.normalized_payload->>'amount','')::numeric,0)<=0) then e:=e||jsonb_build_array('Customer receivable opening needs customer_code and positive amount'); end if;
      if v_bt='SUPPLIER_PAYABLE' and(nullif(r.normalized_payload->>'supplier_code','') is null or coalesce(nullif(r.normalized_payload->>'amount','')::numeric,0)<=0) then e:=e||jsonb_build_array('Supplier payable opening needs supplier_code and positive amount'); end if;
      if v_bt='VENDOR_PAYABLE' and(nullif(r.normalized_payload->>'vendor_code','') is null or coalesce(nullif(r.normalized_payload->>'amount','')::numeric,0)<=0) then e:=e||jsonb_build_array('Vendor payable opening needs vendor_code and positive amount'); end if;
      if v_bt='CASH_BANK' and(nullif(r.normalized_payload->>'cash_account_code','') is null or coalesce(nullif(r.normalized_payload->>'amount','')::numeric,0)<=0) then e:=e||jsonb_build_array('CASH_BANK opening needs cash_account_code and positive amount'); end if;
    end if;
    if r.entity_type='OPEN_PO' then
      if upper(coalesce(r.normalized_payload->>'status','')) not in('DRAFT','CUTTING','SEWING','LAUNDRY','QC','FINISHED','ON_HOLD','CANCELLED') then e:=e||jsonb_build_array('Invalid PO status'); end if;
      if upper(coalesce(r.normalized_payload->>'current_stage','')) not in('CUTTING','SEWING','LAUNDRY','QC','FINISHED','ON_HOLD') then e:=e||jsonb_build_array('Invalid PO current_stage'); end if;
    end if;
    -- Topological order matches apply_migration_master_rows. A staged parent
    -- must itself be VALID; presence alone never proves a usable reference.
    for ref in select * from(values
      ('material_sku','materials','material_sku','MATERIAL',array['MATERIAL_ROLL','OPENING_BALANCE_ITEM']),
      ('model_code','product_models','model_code','MODEL',array['PRODUCT','OPEN_PO','OPENING_BALANCE_ITEM']),
      ('brand_code','brands','brand_code','BRAND',array['PRODUCT']),
      ('size_code','sizes','size_code','SIZE',array['PRODUCT']),
      ('accessory_category_code','accessory_categories','category_code','ACCESSORY_CATEGORY',array['MATERIAL']),
      ('unit_code','uom_definitions','unit_code',null,array['MATERIAL']),
      ('contractor_code','contractors','contractor_code','CONTRACTOR',array['OPEN_PO','OPENING_BALANCE_ITEM']),
      ('customer_code','customers','customer_code','CUSTOMER',array['OPENING_BALANCE_ITEM']),
      ('supplier_code','suppliers','supplier_code','SUPPLIER',array['MATERIAL_ROLL','OPENING_BALANCE_ITEM']),
      ('location_code','locations','location_code','LOCATION',array['MATERIAL_ROLL','OPENING_BALANCE_ITEM']),
      ('vendor_code','laundry_vendors','vendor_code','LAUNDRY_VENDOR',array['OPENING_BALANCE_ITEM']),
      ('cash_account_code','cash_accounts','cash_account_code','CASH_ACCOUNT',array['OPENING_BALANCE_ITEM'])
    ) refs(field,relation_name,code_field,staged_type,consumers)
    where r.entity_type=any(refs.consumers) loop
      v_code:=r.normalized_payload->>ref.field;
      if nullif(btrim(v_code),'') is null then continue; end if;
      if ref.field='unit_code' then v_code:=upper(v_code); end if;
      -- Identifiers are selected only from the constant allowlist above.
      execute format('select exists(select 1 from erp.%I where %I=$1)',ref.relation_name,ref.code_field)
        into v_exists using v_code;
      if not v_exists and not exists(select 1 from erp.migration_staging_rows s
        where s.batch_id=p_batch_id and s.entity_type=ref.staged_type
          and s.validation_status='VALID' and s.normalized_payload->>ref.code_field=v_code) then
        e:=e||jsonb_build_array('Unknown or invalid staged reference: '||ref.field||' = '||v_code);
      end if;
    end loop;
    if r.entity_type='OPENING_BALANCE_ITEM' and v_bt='MATERIAL'
       and exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id
         and s.entity_type='MATERIAL' and s.validation_status='VALID'
         and s.normalized_payload->>'material_sku'=r.normalized_payload->>'material_sku'
         and upper(s.normalized_payload->>'material_type')='FABRIC') then
      e:=e||jsonb_build_array('FABRIC opening stock must use MATERIAL_ROLL rows');
    end if;
    if r.entity_type='PRODUCT' then
      -- Import may maintain display data, never rewrite identity/history.
      if exists(select 1 from erp.products p join erp.brands b on b.id=p.brand_id
        join erp.sizes sz on sz.id=p.size_id join erp.product_models m on m.id=p.model_id
        where b.brand_code=r.normalized_payload->>'brand_code'
          and sz.size_code=r.normalized_payload->>'size_code'
          and lower(btrim(p.sku))=lower(btrim(r.normalized_payload->>'sku'))
      ) and not exists(select 1 from erp.products p join erp.brands b on b.id=p.brand_id
        join erp.sizes sz on sz.id=p.size_id join erp.product_models m on m.id=p.model_id
        where b.brand_code=r.normalized_payload->>'brand_code'
          and sz.size_code=r.normalized_payload->>'size_code'
          and lower(btrim(p.sku))=lower(btrim(r.normalized_payload->>'sku'))
          and p.effective_from<=v_cutover and (p.effective_to is null or p.effective_to>v_cutover)
          and m.model_code=r.normalized_payload->>'model_code'
          and lower(btrim(p.color_name))=lower(btrim(r.normalized_payload->>'color_name'))) then
        e:=e||jsonb_build_array('PRODUCT identity/history conflicts at migration cutover');
      end if;
    end if;
    exception when others then
      e:=e||jsonb_build_array('Invalid row value: '||sqlerrm);
    end;
    if r.validation_status='ERROR' and jsonb_array_length(r.validation_errors)>0 then e:=r.validation_errors||e; end if;
    update erp.migration_staging_rows set validation_status=case when jsonb_array_length(e)=0 then 'VALID' else 'ERROR' end,validation_errors=e,updated_at=statement_timestamp() where id=r.id;
  end loop;
  select count(*),count(*) filter(where validation_status='VALID'),count(*) filter(where validation_status='ERROR') into v_total,v_valid,v_error from erp.migration_staging_rows where batch_id=p_batch_id;
  update erp.migration_batches set status=case when v_error=0 then 'READY' else 'DRAFT' end,validated_at=statement_timestamp(),error_message=case when v_error=0 then null else v_error||' staging row(s) failed validation' end where id=p_batch_id;
  return query select v_total,v_valid,v_error;
end;$function$;
CREATE OR REPLACE FUNCTION erp.stage_migration_row(p_batch_id uuid, p_entity_type text, p_source_row_no integer, p_legacy_key text, p_source_payload jsonb, p_normalized_payload jsonb)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare v_status text; v_id uuid; v_type text:=upper(trim(p_entity_type));
begin
  perform erp.require_owner_admin();
  select status into v_status from erp.migration_batches where id=p_batch_id for update;
  if v_status is null then raise exception 'Migration batch not found'; end if;
  if v_status not in ('DRAFT','VALIDATING','READY','POSTING') then raise exception 'Migration batch % cannot be staged while status is %',p_batch_id,v_status; end if;
  -- Lock order is batch -> opening in both the editor and posting consumer.
  perform 1 from erp.opening_balance_headers where migration_batch_id=p_batch_id order by id for update;
  if exists(select 1 from erp.opening_balance_headers where migration_batch_id=p_batch_id and status<>'DRAFT') then
    raise exception 'AK_MIGRATION_STAGE_AFTER_POSTING_REFUSED';
  end if;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type=v_type
    and source_row_no=p_source_row_no and posted_entity_id is not null and entity_type<>'OPENING_BALANCE_ITEM') then
    raise exception 'AK_APPLIED_MASTER_ROW_EDIT_REQUIRES_MASTER_CORRECTION';
  end if;
  if p_source_row_no is null or p_source_row_no<=0 then raise exception 'source_row_no must be positive'; end if;
  if v_type not in ('BRAND','SIZE','MODEL','PRODUCT','CUSTOMER','SUPPLIER','CONTRACTOR','ACCESSORY_CATEGORY','MATERIAL','MATERIAL_ROLL','OPENING_BALANCE_ITEM','OPEN_PO','OPENING_CONTROL','OPENING_ADVANCE','OPENING_COST_ORIGIN','UNINVOICED_RECEIPT','LAUNDRY_VENDOR','LOCATION','CHART_ACCOUNT','CASH_ACCOUNT') then
    raise exception 'Unsupported migration entity_type %',v_type;
  end if;
  insert into erp.migration_staging_rows(batch_id,entity_type,source_row_no,legacy_key,source_payload,normalized_payload,validation_status,validation_errors,updated_at)
  values (p_batch_id,v_type,p_source_row_no,nullif(trim(p_legacy_key),''),coalesce(p_source_payload,'{}'::jsonb),coalesce(p_normalized_payload,'{}'::jsonb),'PENDING','[]'::jsonb,statement_timestamp())
  on conflict (batch_id,entity_type,source_row_no) do update set
    legacy_key=excluded.legacy_key,source_payload=excluded.source_payload,normalized_payload=excluded.normalized_payload,
    validation_status='PENDING',validation_errors='[]'::jsonb,posted_entity_type=null,posted_entity_id=null,posted_at=null,updated_at=statement_timestamp()
  returning id into v_id;
  -- Prepared opening is still a draft: edits remain allowed. Invalidate only
  -- its unposted lines, keep the header identity, and require fresh prepare.
  delete from erp.opening_balance_items i using erp.opening_balance_headers h
    where i.opening_id=h.id and h.migration_batch_id=p_batch_id and h.status='DRAFT';
  update erp.migration_staging_rows set posted_entity_type=null,posted_entity_id=null,posted_at=null
    where batch_id=p_batch_id and entity_type='OPENING_BALANCE_ITEM';
  update erp.migration_batches set status='DRAFT',validated_at=null,error_message=null where id=p_batch_id;
  return v_id;
end;$function$;
CREATE OR REPLACE FUNCTION erp.apply_migration_master_rows(p_batch_id uuid)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  r record;
  j jsonb;
  v_id uuid;
  v_model uuid;
  v_brand uuid;
  v_size uuid;
  v_category uuid;
  v_material uuid;
  v_supplier uuid;
  v_cutover timestamptz;
  v_count integer:=0;
  v_existing record;
begin
  perform erp.require_owner_admin();
  perform 1 from erp.migration_batches where id=p_batch_id for update;
  if not found then raise exception 'Migration batch not found'; end if;
  if (select status from erp.migration_batches where id=p_batch_id) not in('READY','POSTING') then
    raise exception 'Migration batch must be READY';
  end if;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and validation_status<>'VALID') then
    raise exception 'Migration batch contains unvalidated/error rows';
  end if;
  select cutover_at into v_cutover from erp.migration_batches where id=p_batch_id;
  update erp.migration_batches set status='POSTING',error_message=null where id=p_batch_id;

  for r in
    select * from erp.migration_staging_rows
    where batch_id=p_batch_id and validation_status='VALID' and posted_entity_id is null
      and entity_type in(
        'LAUNDRY_VENDOR','LOCATION','CHART_ACCOUNT','CASH_ACCOUNT','BRAND','SIZE','MODEL','CUSTOMER','SUPPLIER','CONTRACTOR',
        'ACCESSORY_CATEGORY','MATERIAL','MATERIAL_ROLL','PRODUCT'
      )
    order by case entity_type
      when 'LAUNDRY_VENDOR' then 1 when 'LOCATION' then 2 when 'CHART_ACCOUNT' then 3 when 'CASH_ACCOUNT' then 4 when 'BRAND' then 10 when 'SIZE' then 20 when 'MODEL' then 30
      when 'CUSTOMER' then 40 when 'SUPPLIER' then 50 when 'CONTRACTOR' then 60
      when 'ACCESSORY_CATEGORY' then 70 when 'MATERIAL' then 80
      when 'MATERIAL_ROLL' then 85 when 'PRODUCT' then 90 else 999 end,
      source_row_no
  loop
    j:=r.normalized_payload;
    v_id:=null;
    perform erp.validate_initial_import_master_row_v1(p_batch_id,r.entity_type,j);
    case r.entity_type
      when 'LAUNDRY_VENDOR' then
        insert into erp.laundry_vendors(vendor_code,vendor_name,phone,is_active,notes)
        values(j->>'vendor_code',j->>'vendor_name',nullif(j->>'phone',''),coalesce(nullif(j->>'is_active','')::boolean,true),j->>'notes')
        on conflict(vendor_code) do update set vendor_name=excluded.vendor_name,phone=excluded.phone,
          is_active=excluded.is_active,notes=excluded.notes,updated_at=statement_timestamp() returning id into v_id;
      when 'LOCATION' then
        insert into erp.locations(location_code,location_name,location_type,is_active)
        values(j->>'location_code',j->>'location_name',upper(j->>'location_type'),coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(location_code) do update set location_name=excluded.location_name,is_active=excluded.is_active
          where locations.location_type=excluded.location_type returning id into v_id;
        if v_id is null then raise exception 'location_type: identitas lokasi berubah saat impor'; end if;
      when 'CHART_ACCOUNT' then
        -- Parent links are attached after every code exists, in this transaction.
        -- Existing semantic fields remain unchanged and were checked above.
        insert into erp.chart_accounts(account_code,account_name,account_type,report_group,normal_balance,is_postable,is_active)
        values(j->>'account_code',j->>'account_name',upper(j->>'account_type'),j->>'report_group',upper(j->>'normal_balance'),
          coalesce(nullif(j->>'is_postable','')::boolean,true),coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(account_code) do update set account_name=excluded.account_name
          where chart_accounts.account_type=excluded.account_type and chart_accounts.report_group=excluded.report_group
            and chart_accounts.normal_balance=excluded.normal_balance and chart_accounts.is_postable=excluded.is_postable
            and chart_accounts.is_active=excluded.is_active
            and (select p.account_code from erp.chart_accounts p where p.id=chart_accounts.parent_account_id)
              is not distinct from nullif(btrim(j->>'parent_account_code'),'') returning id into v_id;
        if v_id is null then raise exception 'account_code: arti akun berubah saat impor'; end if;
      when 'CASH_ACCOUNT' then
        select id into v_category from erp.chart_accounts where account_code=j->>'coa_account_code';
        if v_category is null then raise exception 'coa_account_code: akun belum diterapkan'; end if;
        insert into erp.cash_accounts(cash_account_code,cash_account_name,coa_account_id,account_kind,is_active)
        values(j->>'cash_account_code',j->>'cash_account_name',v_category,upper(j->>'account_kind'),coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(cash_account_code) do update set cash_account_name=excluded.cash_account_name,is_active=excluded.is_active
          where cash_accounts.coa_account_id=excluded.coa_account_id and cash_accounts.account_kind=excluded.account_kind returning id into v_id;
        if v_id is null then raise exception 'coa_account_code: rekening berubah saat impor'; end if;
      when 'BRAND' then
        insert into erp.brands(brand_code,brand_name,is_active)
        values(j->>'brand_code',j->>'brand_name',coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(brand_code) do update set
          brand_name=excluded.brand_name,is_active=excluded.is_active,updated_at=statement_timestamp()
        returning id into v_id;
      when 'SIZE' then
        insert into erp.sizes(size_code,sort_order,is_active)
        values(j->>'size_code',coalesce(nullif(j->>'sort_order','')::integer,0),
          coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(size_code) do update set
          sort_order=excluded.sort_order,is_active=excluded.is_active
        returning id into v_id;
      when 'MODEL' then
        insert into erp.product_models(model_code,model_name,description,is_active)
        values(j->>'model_code',j->>'model_name',j->>'description',
          coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(model_code) do update set
          model_name=excluded.model_name,description=excluded.description,
          is_active=excluded.is_active,updated_at=statement_timestamp()
        returning id into v_id;
      when 'CUSTOMER' then
        insert into erp.customers(customer_code,customer_name,phone,address,is_active)
        values(j->>'customer_code',j->>'customer_name',j->>'phone',j->>'address',
          coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(customer_code) do update set
          customer_name=excluded.customer_name,phone=excluded.phone,address=excluded.address,
          is_active=excluded.is_active,updated_at=statement_timestamp()
        returning id into v_id;
      when 'SUPPLIER' then
        insert into erp.suppliers(
          supplier_code,supplier_name,supplier_type,phone,address,is_active
        ) values(
          j->>'supplier_code',j->>'supplier_name',
          coalesce(nullif(upper(j->>'supplier_type'),''),'MATERIAL'),
          j->>'phone',j->>'address',coalesce(nullif(j->>'is_active','')::boolean,true)
        )
        on conflict(supplier_code) do update set
          supplier_name=excluded.supplier_name,supplier_type=excluded.supplier_type,
          phone=excluded.phone,address=excluded.address,is_active=excluded.is_active
        returning id into v_id;
      when 'CONTRACTOR' then
        insert into erp.contractors(
          contractor_code,contractor_name,contractor_type,attendance_required,is_active,notes
        ) values(
          j->>'contractor_code',j->>'contractor_name',
          coalesce(nullif(upper(j->>'contractor_type'),''),'MANDOR'),
          coalesce(nullif(j->>'attendance_required','')::boolean,true),
          coalesce(nullif(j->>'is_active','')::boolean,true),j->>'notes'
        )
        on conflict(contractor_code) do update set
          contractor_name=excluded.contractor_name,contractor_type=excluded.contractor_type,
          attendance_required=excluded.attendance_required,is_active=excluded.is_active,
          notes=excluded.notes,updated_at=statement_timestamp()
        returning id into v_id;
      when 'ACCESSORY_CATEGORY' then
        insert into erp.accessory_categories(
          category_code,category_name,base_uom_code,is_active,notes
        ) values(
          j->>'category_code',j->>'category_name',upper(j->>'base_uom_code'),
          coalesce(nullif(j->>'is_active','')::boolean,true),j->>'notes'
        )
        on conflict(category_code) do update set
          category_name=excluded.category_name,is_active=excluded.is_active,
          notes=excluded.notes,updated_at=statement_timestamp()
        returning id into v_id;
      when 'MATERIAL' then
        v_category:=null;
        if nullif(btrim(coalesce(j->>'accessory_category_code','')),'') is not null then
          select id into v_category from erp.accessory_categories
          where category_code=j->>'accessory_category_code';
          if v_category is null then
            raise exception 'Unknown accessory category % for material %',
              j->>'accessory_category_code',j->>'material_sku';
          end if;
        end if;
        insert into erp.materials(
          material_sku,material_name,material_type,unit_code,accessory_category_id,is_active
        ) values(
          j->>'material_sku',j->>'material_name',upper(j->>'material_type'),
          upper(j->>'unit_code'),v_category,
          coalesce(nullif(j->>'is_active','')::boolean,true)
        )
        on conflict(material_sku) do update set
          material_name=excluded.material_name,
          accessory_category_id=excluded.accessory_category_id,
          is_active=excluded.is_active,updated_at=statement_timestamp()
        returning id into v_id;
      when 'MATERIAL_ROLL' then
        select id into v_material from erp.materials
        where material_sku=j->>'material_sku' and material_type='FABRIC';
        if v_material is null then
          raise exception 'MATERIAL_ROLL material % is not a FABRIC material',j->>'material_sku';
        end if;
        v_supplier:=null;
        if nullif(btrim(coalesce(j->>'supplier_code','')),'') is not null then
          select id into v_supplier from erp.suppliers where supplier_code=j->>'supplier_code';
          if v_supplier is null then
            raise exception 'Unknown supplier % for roll %',j->>'supplier_code',j->>'roll_number';
          end if;
        end if;
        if exists(select 1 from erp.material_rolls
          where material_id=v_material and roll_number=j->>'roll_number') then
          raise exception 'Migration roll already exists for material %, roll %',
            j->>'material_sku',j->>'roll_number';
        end if;
        insert into erp.material_rolls(
          material_id,purchase_item_id,supplier_id,roll_number,original_qty,
          cached_qty,status,received_at,notes
        ) values(
          v_material,null,v_supplier,j->>'roll_number',(j->>'opening_qty')::numeric,
          0,'AVAILABLE',v_cutover,coalesce(j->>'notes','Legacy roll at migration cutover')
        ) returning id into v_id;
      when 'PRODUCT' then
        select id into v_model from erp.product_models where model_code=j->>'model_code';
        select id into v_brand from erp.brands where brand_code=j->>'brand_code';
        select id into v_size from erp.sizes where size_code=j->>'size_code';
        if v_model is null or v_brand is null or v_size is null then
          raise exception 'Product % has unresolved model/brand/size mapping',j->>'sku';
        end if;
        insert into erp.product_model_sizes(model_id,size_id)
        values(v_model,v_size) on conflict(model_id,size_id) do nothing;

        select p.* into v_existing
        from erp.products p
        where p.brand_id=v_brand
          and lower(btrim(p.sku))=lower(btrim(j->>'sku'))
          and p.size_id=v_size
          and p.effective_from<=v_cutover
          and(p.effective_to is null or p.effective_to>v_cutover)
        order by p.effective_from desc,p.id desc limit 1;

        if v_existing.id is null then
          if exists(
            select 1 from erp.products p
            where p.brand_id=v_brand
              and lower(btrim(p.sku))=lower(btrim(j->>'sku'))
              and p.size_id=v_size
          ) then
            raise exception 'Migration product % already has identity history for brand % / size % but no version valid at cutover %. Do not guess a historical version; fix migration mapping/effective dates first.',
              j->>'sku',j->>'brand_code',j->>'size_code',v_cutover;
          end if;
          insert into erp.products(
            sku,model_id,brand_id,color_name,size_id,product_name,
            is_portal_visible,is_active,effective_from
          ) values(
            j->>'sku',v_model,v_brand,j->>'color_name',v_size,j->>'product_name',
            coalesce(nullif(j->>'is_portal_visible','')::boolean,true),
            coalesce(nullif(j->>'is_active','')::boolean,true),v_cutover
          ) returning id into v_id;
        else
          if v_existing.model_id is distinct from v_model
             or v_existing.brand_id is distinct from v_brand
             or lower(btrim(v_existing.color_name)) is distinct from lower(btrim(j->>'color_name'))
             or v_existing.size_id is distinct from v_size then
            raise exception 'Migration product % identity differs from the brand + SKU version already valid at cutover. Use controlled identity-version mapping instead of overwriting history.',j->>'sku';
          end if;
          v_id:=v_existing.id;
          update erp.products set
            product_name=j->>'product_name',
            is_portal_visible=coalesce(nullif(j->>'is_portal_visible','')::boolean,true),
            is_active=coalesce(nullif(j->>'is_active','')::boolean,true),updated_at=statement_timestamp()
          where id=v_id;
        end if;
    end case;
    update erp.migration_staging_rows set
      posted_entity_type=r.entity_type,posted_entity_id=v_id,
      posted_at=statement_timestamp(),updated_at=statement_timestamp()
    where id=r.id;
    v_count:=v_count+1;
  end loop;
  update erp.chart_accounts a set parent_account_id=p.id
    from erp.migration_staging_rows s join erp.chart_accounts p on p.account_code=s.normalized_payload->>'parent_account_code'
    where s.batch_id=p_batch_id and s.entity_type='CHART_ACCOUNT' and s.posted_entity_id=a.id
      and a.parent_account_id is distinct from p.id;
  return v_count;
end
$function$;
CREATE OR REPLACE FUNCTION erp.prepare_migration_opening_balance(p_batch_id uuid, p_opening_number text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare b erp.migration_batches%rowtype;r record;j jsonb;v_header uuid;v_material uuid;v_roll uuid;v_product uuid;v_model uuid;v_contractor uuid;v_customer uuid;v_location uuid;v_supplier uuid;v_vendor uuid;v_cash uuid;v_type text;v_number text;v_hpp_method text;v_hpp_pct numeric;v_opening_item uuid;
begin
  perform erp.require_owner_admin();select * into b from erp.migration_batches where id=p_batch_id for update;if b.id is null then raise exception 'Migration batch not found';end if;if b.status not in('READY','POSTING') then raise exception 'Migration batch must be READY/POSTING';end if;if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and validation_status<>'VALID') then raise exception 'Migration batch contains unvalidated/error rows';end if;
  if exists(select 1 from erp.opening_balance_headers where migration_batch_id=p_batch_id) then select id into v_header from erp.opening_balance_headers where migration_batch_id=p_batch_id order by created_at limit 1;
    perform 1 from erp.opening_balance_headers where id=v_header for update;
    if exists(select 1 from erp.opening_balance_items where opening_id=v_header) then return v_header;end if;
    if (select status from erp.opening_balance_headers where id=v_header)<>'DRAFT' then raise exception 'AK_POSTED_OPENING_REBUILD_REFUSED';end if;
  end if;
  v_number:=coalesce(nullif(trim(p_opening_number),''),'MIG-'||b.batch_code);if v_header is null then insert into erp.opening_balance_headers(opening_number,opening_date,status,notes,created_by,migration_batch_id) values(v_number,(b.cutover_at AT TIME ZONE 'Asia/Jakarta')::date,'DRAFT','Prepared from migration batch '||b.batch_code,erp.current_app_user_id(),b.id) returning id into v_header;end if;
  for r in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='MATERIAL_ROLL' and validation_status='VALID' order by source_row_no loop
    j:=r.normalized_payload;select m.id,mr.id into v_material,v_roll from erp.materials m join erp.material_rolls mr on mr.material_id=m.id where m.material_sku=j->>'material_sku' and mr.roll_number=j->>'roll_number';select id into v_location from erp.locations where location_code=j->>'location_code' and location_type='RAW_MATERIAL_WAREHOUSE' and is_active=true;if v_material is null or v_roll is null or v_location is null then raise exception 'MATERIAL_ROLL row % was not applied/resolved safely',r.source_row_no;end if;
    insert into erp.opening_balance_items(opening_id,balance_type,material_id,roll_id,location_id,qty,unit_cost_snapshot,notes) values(v_header,'MATERIAL',v_material,v_roll,v_location,(j->>'opening_qty')::numeric,(j->>'unit_cost')::numeric,coalesce(j->>'notes','Legacy roll opening row '||r.source_row_no)) returning id into v_opening_item;
    perform erp.link_initial_import_stock_source_v1(b.id,r.id,v_opening_item);
    perform erp.link_initial_import_production_v1(b.id,r.id,v_opening_item);
  end loop;
  for r in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='OPENING_BALANCE_ITEM' and validation_status='VALID' order by source_row_no loop
    j:=r.normalized_payload;v_type:=upper(j->>'balance_type');v_material:=null;v_product:=null;v_model:=null;v_contractor:=null;v_customer:=null;v_location:=null;v_supplier:=null;v_vendor:=null;v_cash:=null;v_hpp_method:=coalesce(nullif(upper(j->>'hpp_input_method'),''),'MANUAL');v_hpp_pct:=nullif(j->>'hpp_percent_of_price','')::numeric;
    if nullif(trim(coalesce(j->>'material_sku','')),'') is not null then select id into v_material from erp.materials where material_sku=j->>'material_sku';if v_material is null then raise exception 'Opening row %: unknown material_sku %',r.source_row_no,j->>'material_sku';end if;end if;
    if nullif(trim(coalesce(j->>'product_sku','')),'') is not null then
      v_product:=erp.resolve_opening_product_identity(j->>'product_sku',b.cutover_at,j->>'color_name',j->>'size_code',j->>'model_code',j->>'brand_code');
    end if;
    if nullif(trim(coalesce(j->>'model_code','')),'') is not null then select id into v_model from erp.product_models where model_code=j->>'model_code';if v_model is null then raise exception 'Opening row %: unknown model_code %',r.source_row_no,j->>'model_code';end if;end if;
    if nullif(trim(coalesce(j->>'contractor_code','')),'') is not null then select id into v_contractor from erp.contractors where contractor_code=j->>'contractor_code';if v_contractor is null then raise exception 'Opening row %: unknown contractor_code %',r.source_row_no,j->>'contractor_code';end if;end if;
    if nullif(trim(coalesce(j->>'customer_code','')),'') is not null then select id into v_customer from erp.customers where customer_code=j->>'customer_code';if v_customer is null then raise exception 'Opening row %: unknown customer_code %',r.source_row_no,j->>'customer_code';end if;end if;
    if nullif(trim(coalesce(j->>'location_code','')),'') is not null then select id into v_location from erp.locations where location_code=j->>'location_code';if v_location is null then raise exception 'Opening row %: unknown location_code %',r.source_row_no,j->>'location_code';end if;end if;
    if nullif(trim(coalesce(j->>'supplier_code','')),'') is not null then select id into v_supplier from erp.suppliers where supplier_code=j->>'supplier_code';if v_supplier is null then raise exception 'Opening row %: unknown supplier_code %',r.source_row_no,j->>'supplier_code';end if;end if;
    if nullif(trim(coalesce(j->>'vendor_code','')),'') is not null then select id into v_vendor from erp.laundry_vendors where vendor_code=j->>'vendor_code';if v_vendor is null then raise exception 'Opening row %: unknown vendor_code %',r.source_row_no,j->>'vendor_code';end if;end if;
    if nullif(trim(coalesce(j->>'cash_account_code','')),'') is not null then select id into v_cash from erp.cash_accounts where cash_account_code=j->>'cash_account_code';if v_cash is null then raise exception 'Opening row %: unknown cash_account_code %',r.source_row_no,j->>'cash_account_code';end if;end if;
    insert into erp.opening_balance_items(opening_id,balance_type,material_id,product_id,model_id,contractor_id,customer_id,location_id,supplier_id,vendor_id,cash_account_id,stage,qty,amount,unit_cost_snapshot,quality_grade,notes,hpp_input_method,hpp_percent_of_price)
    values(v_header,v_type,v_material,v_product,v_model,v_contractor,v_customer,v_location,v_supplier,v_vendor,v_cash,nullif(j->>'stage',''),nullif(j->>'qty','')::numeric,nullif(j->>'amount','')::numeric,nullif(j->>'unit_cost','')::numeric,nullif(j->>'quality_grade',''),coalesce(j->>'notes','Legacy migration row '||r.source_row_no),case when v_type='FINISHED_GOODS' then v_hpp_method else 'MANUAL' end,case when v_type='FINISHED_GOODS' and v_hpp_method='PRICE_PERCENT' then v_hpp_pct else null end) returning id into v_opening_item;
    perform erp.check_initial_import_financial_source_v1(b.id,r.id,v_opening_item);
    perform erp.link_initial_import_stock_source_v1(b.id,r.id,v_opening_item);
    perform erp.link_initial_import_production_v1(b.id,r.id,v_opening_item);
    update erp.migration_staging_rows set posted_entity_type='OPENING_BALANCE_HEADER',posted_entity_id=v_header,posted_at=statement_timestamp(),updated_at=statement_timestamp() where id=r.id;
  end loop;return v_header;
end$function$;
CREATE OR REPLACE FUNCTION erp.validate_initial_import_totals_v1(p_batch_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare r record; c record; j jsonb; v_key text; v_type text; v_qty numeric; v_amount numeric;
 v_totals jsonb:='{}'; v_entry jsonb; v_product uuid; v_cutover timestamptz; v_cost numeric;
begin
 perform erp.require_owner_admin();
 select cutover_at into v_cutover from erp.migration_batches where id=p_batch_id for update;
 if v_cutover is null then raise exception 'Batch tidak ditemukan'; end if;
 for r in select * from erp.migration_staging_rows where batch_id=p_batch_id
   and entity_type in('MATERIAL_ROLL','OPENING_BALANCE_ITEM','UNINVOICED_RECEIPT','OPENING_ADVANCE') order by entity_type,source_row_no loop
  begin
   j:=r.normalized_payload;v_key:=nullif(btrim(j->>'control_key'),'');
   if v_key is null then raise exception 'control_key: rincian wajib terhubung ke total pembanding'; end if;
   if (select count(*) from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='OPENING_CONTROL'
      and normalized_payload->>'control_key'=v_key)<>1 then
     raise exception 'control_key %: harus punya tepat satu total pembanding',v_key; end if;
   if r.validation_status<>'VALID' then continue; end if;
   v_type:=case when r.entity_type='MATERIAL_ROLL' then 'MATERIAL' when r.entity_type='UNINVOICED_RECEIPT' then 'GRNI_MATERIAL' when r.entity_type='OPENING_ADVANCE' then (j->>'party_type')||'_ADVANCE' else upper(j->>'balance_type') end;
   v_qty:=coalesce(nullif(j->>case when r.entity_type='MATERIAL_ROLL' then 'opening_qty' else 'qty' end,'')::numeric,0);
   v_cost:=nullif(j->>'unit_cost','')::numeric;
   if v_type='FINISHED_GOODS' and upper(j->>'hpp_input_method')='PRICE_PERCENT' then
     v_product:=erp.resolve_opening_product_identity(j->>'product_sku',v_cutover,j->>'color_name',j->>'size_code',j->>'model_code',j->>'brand_code');
     v_cost:=round(erp.resolve_product_price_at(v_product,erp.product_opening_physical_at(v_product,(v_cutover at time zone 'Asia/Jakarta')::date))*(j->>'hpp_percent_of_price')::numeric/100,6);
   end if;
   v_amount:=case when v_type in('MATERIAL','FINISHED_GOODS','GRNI_MATERIAL') then round(v_qty*v_cost,2)
     when v_type='BS' then case when nullif(j->>'po_number','') is not null then round(coalesce(nullif(j->>'amount','')::numeric,v_qty*v_cost),2) else 0 end else round(coalesce(nullif(j->>'amount','')::numeric,v_qty*v_cost),2) end;
   if r.entity_type='UNINVOICED_RECEIPT' then
     -- GRNI is rounded once per receipt document, exactly as its subledger.
     -- Physical opening value retains its existing per-stock-line rounding.
     if r.source_row_no=(select min(s.source_row_no) from erp.migration_staging_rows s where s.batch_id=p_batch_id
       and s.entity_type='UNINVOICED_RECEIPT' and s.normalized_payload->>'supplier_code'=j->>'supplier_code'
       and lower(btrim(s.normalized_payload->>'receipt_number'))=lower(btrim(j->>'receipt_number'))) then
       select round(sum((s.normalized_payload->>'qty')::numeric*(s.normalized_payload->>'unit_cost')::numeric),2) into v_amount
       from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='UNINVOICED_RECEIPT'
         and s.normalized_payload->>'supplier_code'=j->>'supplier_code'
         and lower(btrim(s.normalized_payload->>'receipt_number'))=lower(btrim(j->>'receipt_number'));
     else v_amount:=0;end if;
   end if;
   if v_amount is null then raise exception 'amount: nilai rincian belum lengkap'; end if;
   if v_type='WIP' and nullif(j->>'amount','') is not null and v_cost is not null and nullif(j->>'qty','') is not null
     and round((j->>'amount')::numeric,2)<>round(v_qty*v_cost,2) then raise exception 'amount: nilai WIP tidak sama dengan jumlah x biaya'; end if;
   if v_type in('MATERIAL','FINISHED_GOODS','BS') and nullif(j->>'amount','') is not null and (j->>'amount')::numeric<>v_amount then
     raise exception 'amount: nominal rincian tidak sama dengan nilai yang akan dibukukan'; end if;
   v_entry:=v_totals->v_key;
   if v_entry is not null and v_entry->>'type'<>v_type then raise exception 'control_key: satu total tidak boleh mencampur jenis saldo'; end if;
   v_totals:=v_totals||jsonb_build_object(v_key,jsonb_build_object('type',v_type,
     'qty',coalesce((v_entry->>'qty')::numeric,0)+v_qty,'amount',coalesce((v_entry->>'amount')::numeric,0)+v_amount));
  exception when others then
   update erp.migration_staging_rows set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array(sqlerrm) where id=r.id;
  end;
 end loop;
 for c in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='OPENING_CONTROL' order by source_row_no loop
  begin
   j:=c.normalized_payload;v_key:=nullif(btrim(j->>'control_key'),'');v_entry:=v_totals->v_key;
   if v_key is null then raise exception 'control_key: kode total wajib diisi'; end if;
   if (select count(*) from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='OPENING_CONTROL'
     and normalized_payload->>'control_key'=v_key)<>1 then raise exception 'control_key: total ditulis lebih dari sekali'; end if;
   if v_entry is null then raise exception 'control_key: total tidak memiliki rincian yang valid'; end if;
   if upper(j->>'balance_type') is distinct from v_entry->>'type' then raise exception 'balance_type: total dan rincian berbeda'; end if;
   if nullif(j->>'amount','') is null or (j->>'amount')::numeric is distinct from (v_entry->>'amount')::numeric then
     raise exception 'amount: total pembanding %, jumlah rincian %',j->>'amount',v_entry->>'amount'; end if;
   if v_entry->>'type'='WIP' and nullif(j->>'qty','') is null and exists(
      select 1 from erp.migration_staging_rows x where x.batch_id=p_batch_id and x.entity_type='OPENING_BALANCE_ITEM'
      and x.normalized_payload->>'control_key'=v_key and nullif(x.normalized_payload->>'po_number','') is not null) then
     raise exception 'qty: total pembanding WIP fisik wajib berisi jumlah pcs';end if;
   if (v_entry->>'type' in('MATERIAL','FINISHED_GOODS','BS','GRNI_MATERIAL') or nullif(j->>'qty','') is not null)
      and (nullif(j->>'qty','')::numeric is distinct from (v_entry->>'qty')::numeric) then
     raise exception 'qty: total pembanding %, jumlah rincian %',j->>'qty',v_entry->>'qty'; end if;
  exception when others then
   update erp.migration_staging_rows set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array(sqlerrm) where id=c.id;
  end;
 end loop;
 update erp.migration_batches set status=case when exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id
   and validation_status<>'VALID') then 'DRAFT' else 'READY' end where id=p_batch_id;
end;$function$;
revoke all on function erp.validate_initial_import_totals_v1(uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.validate_initial_import_master_row_v1(
 p_batch_id uuid,p_entity text,j jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare old_row record; parent_code text; coa record; v_cycle boolean; v_missing boolean;
begin
 perform erp.require_owner_admin();
 if p_entity='LOCATION' then
   if upper(j->>'location_type') not in('RAW_MATERIAL_WAREHOUSE','CUTTING_WIP','CONTRACTOR_WIP',
     'LAUNDRY_WIP','QC_WIP','FG_WAREHOUSE','SCRAP_AREA','OTHER') then
     raise exception 'location_type: jenis lokasi tidak dikenal'; end if;
   select * into old_row from erp.locations where location_code=j->>'location_code' for share;
   if old_row.id is not null and old_row.location_type is distinct from upper(j->>'location_type') then
     raise exception 'location_type: impor tidak boleh mengganti jenis lokasi existing'; end if;
   if old_row.id is not null and not coalesce(nullif(j->>'is_active','')::boolean,true)
     and (coalesce((select sum(qty_signed) from erp.material_stock_movements where location_id=old_row.id),0)<>0
       or coalesce((select sum(qty_signed) from erp.fg_stock_movements where location_id=old_row.id),0)<>0) then
     raise exception 'is_active: lokasi masih memiliki stok'; end if;
 elsif p_entity='CHART_ACCOUNT' then
   if upper(j->>'account_type') not in('ASSET','LIABILITY','EQUITY','REVENUE','EXPENSE') then
     raise exception 'account_type: jenis akun tidak dikenal'; end if;
   if upper(j->>'normal_balance') not in('DEBIT','CREDIT') then
     raise exception 'normal_balance: gunakan DEBIT atau CREDIT'; end if;
   select a.*,p.account_code parent_code into old_row from erp.chart_accounts a
     left join erp.chart_accounts p on p.id=a.parent_account_id where a.account_code=j->>'account_code' for share of a;
   parent_code:=nullif(btrim(j->>'parent_account_code'),'');
   if old_row.id is not null and (
     old_row.account_type is distinct from upper(j->>'account_type')
     or old_row.report_group is distinct from j->>'report_group'
     or old_row.normal_balance is distinct from upper(j->>'normal_balance')
     or old_row.parent_code is distinct from parent_code
     or old_row.is_postable is distinct from coalesce(nullif(j->>'is_postable','')::boolean,true)
     or old_row.is_active is distinct from coalesce(nullif(j->>'is_active','')::boolean,true)) then
     raise exception 'account_code: impor tidak boleh mengubah arti, induk, atau status akun existing'; end if;
   -- Staged definitions replace the same code only in this read-only graph.
   -- Reversed CSV order works; self-links, long cycles and missing ancestors fail.
   with recursive staged as(
     select distinct on(normalized_payload->>'account_code') normalized_payload->>'account_code' code,
       nullif(btrim(normalized_payload->>'parent_account_code'),'') parent
     from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='CHART_ACCOUNT'
     order by normalized_payload->>'account_code',source_row_no,id
   ), graph as(
     select a.account_code code,p.account_code parent from erp.chart_accounts a
       left join erp.chart_accounts p on p.id=a.parent_account_id
       where not exists(select 1 from staged s where s.code=a.account_code)
     union all select code,parent from staged
   ), walk(code,parent,path,cycle,missing) as(
     select g.code,g.parent,array[g.code]::text[],false,false from graph g where g.code=j->>'account_code'
     union all
     select coalesce(g.code,w.parent),g.parent,w.path||w.parent,w.parent=any(w.path),g.code is null
       from walk w left join graph g on g.code=w.parent
       where w.parent is not null and not w.cycle and not w.missing
   ) select coalesce(bool_or(cycle),false),coalesce(bool_or(missing),false) into v_cycle,v_missing from walk;
   if v_cycle then raise exception 'parent_account_code: hubungan induk akun membentuk lingkaran'; end if;
   if v_missing then raise exception 'parent_account_code: akun induk tidak ditemukan'; end if;
 elsif p_entity='CASH_ACCOUNT' then
   if upper(j->>'account_kind') not in('CASH','BANK','EWALLET','OTHER') then
     raise exception 'account_kind: jenis rekening tidak dikenal'; end if;
   select a.id,a.account_code,a.account_type,a.is_active,a.is_postable into coa
     from erp.chart_accounts a where a.account_code=j->>'coa_account_code' for share;
   if exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='CHART_ACCOUNT'
      and s.normalized_payload->>'account_code'=j->>'coa_account_code') then
     select null::uuid id,s.normalized_payload->>'account_code' account_code,
       upper(s.normalized_payload->>'account_type') account_type,
       coalesce(nullif(s.normalized_payload->>'is_active','')::boolean,true) is_active,
       coalesce(nullif(s.normalized_payload->>'is_postable','')::boolean,true) is_postable into coa
       from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='CHART_ACCOUNT'
       and s.normalized_payload->>'account_code'=j->>'coa_account_code' and s.validation_status='VALID' limit 1;
   end if;
   if coa.account_code is null or coa.account_type is distinct from 'ASSET' or not coa.is_active or not coa.is_postable then
     raise exception 'coa_account_code: rekening memerlukan akun ASSET aktif yang boleh dipakai jurnal'; end if;
   select c.*,a.account_code into old_row from erp.cash_accounts c join erp.chart_accounts a on a.id=c.coa_account_id
     where c.cash_account_code=j->>'cash_account_code' for share of c;
   if old_row.id is not null and (old_row.account_code is distinct from j->>'coa_account_code'
      or old_row.account_kind is distinct from upper(j->>'account_kind')) then
     raise exception 'coa_account_code/account_kind: impor tidak boleh memindahkan rekening existing'; end if;
 end if;
end;$function$;
revoke all on function erp.validate_initial_import_master_row_v1(uuid,text,jsonb) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.check_initial_import_financial_source_v1(
 p_batch_id uuid,p_row_id uuid,p_opening_item_id uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD' AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;v_cutover date;v_type text;v_mode text;
 v_code_field text;v_id_field text;v_table text;v_party uuid;v_number text;v_date date;v_due date;
 v_original numeric;v_paid numeric;v_amount numeric;v_field text;v_value numeric;v_result jsonb;
begin
 perform erp.require_owner_admin();
 select * into r from erp.migration_staging_rows where id=p_row_id and batch_id=p_batch_id;
 if r.id is null or r.entity_type<>'OPENING_BALANCE_ITEM' then raise exception 'Baris saldo awal tidak ditemukan'; end if;
 j:=r.normalized_payload;v_type:=upper(j->>'balance_type');
 if coalesce(nullif(j->>'source_kind',''),'BALANCE') not in('BALANCE','CONTRACTOR_CASH_ADVANCE') then
   raise exception 'source_kind: gunakan BALANCE atau CONTRACTOR_CASH_ADVANCE';end if;
 if j->>'source_kind'='CONTRACTOR_CASH_ADVANCE' and (v_type is distinct from 'CONTRACTOR_RECEIVABLE'
   or nullif(btrim(j->>'document_number'),'') is null) then
   raise exception 'source_kind: kasbon tunai wajib rincian dokumen CONTRACTOR_RECEIVABLE';end if;

 if v_type not in('CUSTOMER_RECEIVABLE','SUPPLIER_PAYABLE','VENDOR_PAYABLE','CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE') then
   if exists(select 1 from unnest(array['document_number','document_date','due_date','original_amount','settled_before_cutover']) f
       where nullif(btrim(j->>f),'') is not null) then
     raise exception 'document_number: metadata dokumen ini hanya untuk piutang/utang awal'; end if;
   return null;
 end if;
 select (cutover_at at time zone 'Asia/Jakarta')::date into v_cutover from erp.migration_batches where id=p_batch_id;
 v_code_field:=case when v_type like 'CONTRACTOR_%' then 'contractor_code'
   when v_type='CUSTOMER_RECEIVABLE' then 'customer_code' when v_type='SUPPLIER_PAYABLE' then 'supplier_code' else 'vendor_code' end;
 v_id_field:=replace(v_code_field,'_code','_id');
 v_table:=case when v_type like 'CONTRACTOR_%' then 'contractors'
   when v_type='CUSTOMER_RECEIVABLE' then 'customers' when v_type='SUPPLIER_PAYABLE' then 'suppliers' else 'laundry_vendors' end;
 execute format('select id from erp.%I where %I=$1',v_table,v_code_field) into v_party using j->>v_code_field;
 v_number:=nullif(btrim(j->>'document_number'),'');v_mode:=case when v_number is null then 'SUMMARY' else 'DOCUMENT' end;
 v_amount:=nullif(j->>'amount','')::numeric;
 if v_amount is null or v_amount::text in('NaN','Infinity','-Infinity') or v_amount<=0 or v_amount<>round(v_amount,2) then
   raise exception 'amount: saldo tersisa harus uang positif dengan paling banyak dua desimal'; end if;
 if v_mode='SUMMARY' then
   if exists(select 1 from unnest(array['document_date','due_date','original_amount','settled_before_cutover']) f
       where nullif(btrim(j->>f),'') is not null) then
     raise exception 'document_number: isi nomor dokumen untuk rincian nilai awal dan pembayaran lama'; end if;
   v_original:=v_amount;v_paid:=0;
 else
   if length(v_number)>120 then raise exception 'document_number: maksimal 120 karakter'; end if;
   foreach v_field in array array['original_amount','settled_before_cutover'] loop
     v_value:=nullif(j->>v_field,'')::numeric;
     if v_value is null or v_value::text in('NaN','Infinity','-Infinity') or v_value<0 or v_value<>round(v_value,2) then
       raise exception '%: wajib nominal valid dengan paling banyak dua desimal',v_field; end if;
     perform v_value::numeric(20,2);
   end loop;
   v_original:=(j->>'original_amount')::numeric;v_paid:=(j->>'settled_before_cutover')::numeric;
   if v_original-v_paid<>v_amount then raise exception 'amount: nominal awal dikurangi pembayaran lama harus sama dengan saldo tersisa'; end if;
   foreach v_field in array array['document_date','due_date'] loop
     if v_field='due_date' and nullif(j->>v_field,'') is null then continue; end if;
     if coalesce(j->>v_field,'') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
       or (j->>v_field)::date::text<>j->>v_field then raise exception '%: gunakan tanggal YYYY-MM-DD yang valid',v_field; end if;
   end loop;
   v_date:=(j->>'document_date')::date;v_due:=nullif(j->>'due_date','')::date;
   if v_date>v_cutover then raise exception 'document_date: dokumen melewati tanggal saldo awal'; end if;
   if v_due<v_date then raise exception 'due_date: jatuh tempo mendahului tanggal dokumen'; end if;
 end if;
 -- The same party/balance may be represented by one summary or by documents.
 -- Even a mathematically matching control must not admit both representations.
 if exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.id<>r.id
   and s.entity_type='OPENING_BALANCE_ITEM' and upper(s.normalized_payload->>'balance_type')=v_type
   and s.normalized_payload->>v_code_field=j->>v_code_field
   and (v_mode='SUMMARY' or nullif(btrim(s.normalized_payload->>'document_number'),'') is null)) then
   raise exception 'document_number: jangan campur ringkasan saldo dan rincian dokumen pihak yang sama, atau ulangi ringkasannya'; end if;
 if v_mode='DOCUMENT' and exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.id<>r.id
   and s.entity_type='OPENING_BALANCE_ITEM' and upper(s.normalized_payload->>'balance_type')=v_type
   and s.normalized_payload->>v_code_field=j->>v_code_field
   and lower(btrim(s.normalized_payload->>'document_number'))=lower(v_number)) then
   raise exception 'document_number: dokumen yang sama muncul dua kali dalam batch'; end if;
 if p_opening_item_id is not null then
   if v_party is null or not exists(select 1 from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id
     where i.id=p_opening_item_id and h.migration_batch_id=p_batch_id and h.status='DRAFT'
       and i.balance_type=v_type and (to_jsonb(i)->>v_id_field)::uuid=v_party and i.amount=v_amount) then
     raise exception 'Dokumen asal tidak cocok dengan rincian saldo yang akan dibukukan'; end if;
   perform pg_advisory_xact_lock(hashtextextended('INITIAL_OPENING_FINANCIAL:'||v_type||':'||v_party::text,0));
 end if;
 if v_party is not null then
   if exists(select 1 from erp.initial_import_financial_sources s where s.balance_type=v_type and s.party_id=v_party
     and s.source_row_id<>r.id and (s.source_mode='SUMMARY' or v_mode='SUMMARY')) then
     raise exception 'document_number: saldo pihak ini sudah diimpor; ringkasan dan rincian tidak boleh dibukukan ulang lintas batch'; end if;
   if v_mode='DOCUMENT' and exists(select 1 from erp.initial_import_financial_sources s where s.balance_type=v_type and s.party_id=v_party
     and s.source_row_id<>r.id and lower(btrim(s.document_number))=lower(v_number)) then
     raise exception 'document_number: dokumen ini sudah diimpor pada batch lain'; end if;
   if exists(select 1 from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id
     where h.status='POSTED' and i.balance_type=v_type and (to_jsonb(i)->>v_id_field)::uuid=v_party
       and not exists(select 1 from erp.initial_import_financial_sources s where s.opening_item_id=i.id)) then
     raise exception 'document_number: saldo pihak ini sudah dibukukan melalui jalur lama; rekonsiliasi sumbernya sebelum impor tambahan'; end if;
 end if;
 if v_type='SUPPLIER_PAYABLE' and (
   exists(select 1 from erp.initial_import_receipt_headers h where h.supplier_id=v_party
     and (v_mode='SUMMARY' or lower(btrim(h.receipt_number))=lower(v_number)))
   or exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='UNINVOICED_RECEIPT'
     and s.normalized_payload->>'supplier_code'=j->>'supplier_code'
     and (v_mode='SUMMARY' or lower(btrim(s.normalized_payload->>'receipt_number'))=lower(v_number)))
 ) then raise exception 'document_number: utang awal tumpang tindih dengan penerimaan belum ditagih';end if;
 v_result:=jsonb_build_object('source_mode',v_mode,'document_number',v_number,'document_date',v_date,'due_date',v_due,
   'original_amount',v_original,'settled_before_cutover',v_paid,'outstanding_amount',v_amount);
 if p_opening_item_id is not null then
   insert into erp.initial_import_financial_sources(batch_id,source_row_id,opening_item_id,balance_type,party_id,cutover_date,
     source_mode,document_number,document_date,due_date,original_amount,settled_before_cutover,outstanding_amount,source_kind)
   values(p_batch_id,r.id,p_opening_item_id,v_type,v_party,v_cutover,v_mode,v_number,v_date,v_due,v_original,v_paid,v_amount,coalesce(nullif(j->>'source_kind',''),'BALANCE'));
 end if;
 return v_result;
end;$function$;
revoke all on function erp.check_initial_import_financial_source_v1(uuid,uuid,uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.validate_initial_import_financial_sources_v1(p_batch_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare r record;
begin
 perform erp.require_owner_admin();
 for r in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='OPENING_BALANCE_ITEM'
   and validation_status='VALID' order by source_row_no loop
   begin
     perform erp.check_initial_import_financial_source_v1(p_batch_id,r.id,null);
   exception when others then
     update erp.migration_staging_rows set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array(sqlerrm) where id=r.id;
   end;
 end loop;
end;$function$;
revoke all on function erp.validate_initial_import_financial_sources_v1(uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.refresh_material_purchase_item_cost(p_purchase_item_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  i erp.material_purchase_items%rowtype;
  h erp.material_purchase_headers%rowtype;
  v_cost numeric;
begin
  perform erp.require_internal();
  select * into i from erp.material_purchase_items where id=p_purchase_item_id for update;
  if i.id is null then raise exception 'Material purchase item not found'; end if;
  select * into h from erp.material_purchase_headers where id=i.purchase_id for update;
  if h.id is null or h.status<>'POSTED' then raise exception 'Source purchase must be POSTED'; end if;
  v_cost:=erp.material_purchase_current_unit_cost(i.id);

  if exists(select 1 from erp.initial_import_receipt_lines where purchase_item_id=i.id) then
    update erp.material_stock_movements m set input_unit_cost=v_cost
    from erp.initial_import_receipt_lines l
    where l.purchase_item_id=i.id and m.source_type='OPENING_BALANCE_ITEM' and m.source_id=l.opening_item_id
      and m.movement_type='OPENING' and m.qty_signed=(select oi.qty from erp.opening_balance_items oi where oi.id=l.opening_item_id);
    if not found and exists(select 1 from erp.initial_import_receipt_lines where purchase_item_id=i.id and opening_item_id is not null) then raise exception 'Opening source movement missing for imported receipt %',i.id;end if;
    if exists(select 1 from erp.initial_import_receipt_lines where purchase_item_id=i.id and opening_item_id is not null) then perform erp.recalculate_material_cost(i.material_id,h.physical_at);end if;
    perform erp.recost_initial_import_origins_v1(i.id);
    return;
  end if;

  update erp.material_stock_movements msm
  set input_unit_cost=v_cost
  where msm.movement_type='PURCHASE' and msm.qty_signed>0 and(
    (msm.source_type='MATERIAL_PURCHASE_ITEM' and msm.source_id=i.id)
    or
    (msm.source_type='MATERIAL_PURCHASE_ROLL' and msm.source_id in(
      select mr.id from erp.material_rolls mr where mr.purchase_item_id=i.id
    ))
  );
  if not found then raise exception 'Original purchase stock movement not found for item %',i.id; end if;
  perform erp.recalculate_material_cost(i.material_id,h.physical_at);
end;
$function$;
CREATE OR REPLACE FUNCTION erp.run_v267_financial_truth_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_catalog', 'information_schema', 'pg_temp'
AS $function$
  select 'V267_GRNI_MAPPING_INVALID','CRITICAL',count(*)::bigint,
         'GRNI_MATERIAL must map to an active CREDIT liability account'
  from erp.accounting_account_mappings m
  join erp.chart_accounts a on a.id=m.account_id
  where m.mapping_key='GRNI_MATERIAL'
    and not(a.account_type='LIABILITY' and a.normal_balance='CREDIT' and a.is_active and a.is_postable)

  union all
  select 'V267_MISSING_GRNI_MAPPING','CRITICAL',case when exists(
    select 1 from erp.accounting_account_mappings where mapping_key='GRNI_MATERIAL'
  ) then 0 else 1 end::bigint,'GRNI mapping is required'

  union all
  select 'V267_ESTIMATED_RECEIPT_MISSING_GRNI_RECLASS','CRITICAL',count(*)::bigint,
         'Posted estimated receipts require an AP-to-GRNI reclassification journal'
  from erp.material_purchase_headers h
  where h.status='POSTED' and erp.material_purchase_grni_total(h.id)>0.005
    and not exists(
      select 1 from erp.journal_entries j
      where (j.source_type='MATERIAL_PURCHASE_GRNI_RECLASS' or (
        j.source_type='OPENING_UNINVOICED_RECEIPT' and exists(select 1 from erp.initial_import_receipt_headers r where r.purchase_id=h.id))) and j.source_id=h.id
        and j.status in('POSTED','REVERSED')
    )

  union all
  select 'V267_POSTED_INVOICE_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
         'Every non-zero posted supplier invoice requires an AP/GRNI journal'
  from erp.material_supplier_invoices h
  where h.status='POSTED'
    and exists(select 1 from erp.material_supplier_invoice_lines l where l.invoice_id=h.id and(l.net_amount<>0 or l.grni_clear_amount_snapshot<>0))
    and not exists(
      select 1 from erp.journal_entries j
      where j.source_type='MATERIAL_SUPPLIER_INVOICE' and j.source_id=h.id and j.status='POSTED'
    )

  union all
  select 'V267_INVOICE_MATCH_OVER_RECEIPT','CRITICAL',count(*)::bigint,
         'Posted supplier-invoice quantity exceeds receipt quantity net of GRNI-backed returns'
  from erp.material_purchase_items i
  where erp.material_purchase_posted_invoice_qty(i.id)>erp.material_purchase_invoice_capacity(i.id)

  union all
  select 'V267_PAYMENT_EXCEEDS_FINAL_AP','CRITICAL',count(*)::bigint,
         'Supplier payment must never consume GRNI or exceed final AP'
  from erp.material_purchase_headers h
  where coalesce((select sum(p.amount) from erp.supplier_payments p where p.purchase_id=h.id and p.status='POSTED'),0)
        >round(erp.material_purchase_final_ap_total(h.id),2)

  union all
  select 'V267_LEGACY_CORRECTION_ON_GRNI','CRITICAL',count(*)::bigint,
         'Legacy price corrections may only touch DIRECT_FINAL receipt items'
  from erp.material_purchase_cost_correction_items ci
  join erp.material_purchase_cost_corrections c on c.id=ci.correction_id
  join erp.material_purchase_items i on i.id=ci.purchase_item_id
  where c.status='POSTED' and i.invoice_match_state<>'DIRECT_FINAL'

  union all
  select 'V267_POSTED_RETURN_MISSING_LIABILITY_SNAPSHOT','CRITICAL',count(*)::bigint,
         'Posted supplier returns require AP/GRNI quantity and amount snapshots'
  from erp.material_supplier_return_items ri
  join erp.material_supplier_returns rh on rh.id=ri.return_id
  where rh.status='POSTED' and(
    ri.ap_relief_qty_snapshot is null or ri.grni_relief_qty_snapshot is null
    or ri.ap_relief_amount_snapshot is null or ri.grni_relief_amount_snapshot is null
  )

  union all
  select 'V267_GRNI_GL_SUBLEDGER_MISMATCH','CRITICAL',case when abs(
    coalesce((select sum(a.credit_total-a.debit_total)
      from erp.account_daily_balances a
      where a.account_id=erp.account_id('GRNI_MATERIAL')),0)
    -coalesce((select sum(round(erp.material_purchase_grni_total(h.id),2))
      from erp.material_purchase_headers h where h.status='POSTED'),0)
  )<>0 then 1 else 0 end::bigint,
  'GRNI general ledger must equal estimated unmatched receipt liability'

  union all
  select 'V267_AP_GL_SUBLEDGER_MISMATCH','CRITICAL',case when abs(
    coalesce((select sum(a.credit_total-a.debit_total)
      from erp.account_daily_balances a
      where a.account_id=erp.account_id('AP_SUPPLIER')),0)
    -coalesce((select sum(greatest(
      round(erp.material_purchase_final_ap_total(h.id),2)
      -coalesce((select sum(p.amount) from erp.supplier_payments p where p.purchase_id=h.id and p.status='POSTED'),0),0
    )) from erp.material_purchase_headers h where h.status='POSTED'),0)
    -coalesce((select sum(b.original_amount-b.settled_amount)
      from erp.opening_subledger_balances b
      join erp.opening_balance_items i on i.id=b.opening_item_id
      join erp.opening_balance_headers oh on oh.id=i.opening_id and oh.status='POSTED'
      where b.party_type='SUPPLIER' and b.direction='PAYABLE'),0)
  )<>0 then 1 else 0 end::bigint,
  'Supplier AP general ledger must equal final-invoice subledger net of payment/returns'

  union all
  select 'V267_BROWSER_ROLE_DIRECT_INVOICE_WRITE','CRITICAL',count(*)::bigint,
         'Supplier invoice aggregate must be writable only through v2 RPCs'
  from information_schema.role_table_grants g
  where g.table_schema='erp' and g.table_name in('material_supplier_invoices','material_supplier_invoice_lines')
    and g.grantee in('PUBLIC','anon','authenticated')
    and g.privilege_type in('INSERT','UPDATE','DELETE')
  union all
  select 'V2620M_SUPPLIER_PAYMENT_EXACT_STATUS','CRITICAL',count(*)::bigint,
    'Supplier payment status and capacity must equal the rounded final liability of each purchase'
  from erp.material_purchase_headers h
  cross join lateral(select round(erp.material_purchase_final_ap_total(h.id),2) payable,
    coalesce((select sum(p.amount) from erp.supplier_payments p
      where p.purchase_id=h.id and p.status='POSTED'),0) paid) x
  where h.status='POSTED' and(
    x.paid<0 or x.paid>x.payable
    or x.paid::text in('NaN','Infinity','-Infinity')
    or x.payable::text in('NaN','Infinity','-Infinity')
    or(h.payment_status='PAID' and x.paid<>x.payable)
    or(h.payment_status='PARTIAL' and not(x.paid>0 and x.paid<x.payable))
    or(h.payment_status='UNPAID' and x.paid<>0))

  union all
  select 'V2620M_OPENING_SUBLEDGER_STATE','CRITICAL',count(*)::bigint,
    'Every posted financial opening requires one source-matched balance, exact settlements, and exact status'
  from erp.opening_balance_items i
  join erp.opening_balance_headers h on h.id=i.opening_id and h.status='POSTED'
  left join erp.opening_subledger_balances b on b.opening_item_id=i.id
  cross join lateral(select coalesce((select c.corrected_amount
      from erp.opening_financial_corrections c where c.opening_item_id=i.id and c.status='POSTED'
      order by c.correction_seq desc limit 1),i.amount) original,
    coalesce((select sum(s.amount) from erp.opening_subledger_settlements s
      where s.balance_id=b.id and s.status='POSTED'),0)
    +coalesce((select sum(d.amount) from erp.payroll_deductions d join erp.payroll_settlements p on p.id=d.payroll_id
      where d.opening_cash_advance_balance_id=b.id and p.status='PAID'),0) paid) x
  where i.balance_type in('CUSTOMER_RECEIVABLE','SUPPLIER_PAYABLE','VENDOR_PAYABLE',
    'CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE') and(
    b.id is null or (select count(*) from erp.opening_subledger_balances bx where bx.opening_item_id=i.id)<>1
    or b.original_amount is distinct from x.original
    or b.settled_amount is distinct from x.paid
    or b.original_amount::text in('NaN','Infinity','-Infinity')
    or b.settled_amount::text in('NaN','Infinity','-Infinity')
    or b.original_amount<0 or b.settled_amount<0 or b.settled_amount>b.original_amount
    or b.status is distinct from case when x.paid=x.original then 'SETTLED'
      when x.paid>0 then 'PARTIAL' else 'OPEN' end
    or b.party_type is distinct from split_part(i.balance_type,'_',1)
    or b.direction is distinct from split_part(i.balance_type,'_',2)
    or b.customer_id is distinct from i.customer_id
    or b.supplier_id is distinct from i.supplier_id
    or b.vendor_id is distinct from i.vendor_id
    or b.contractor_id is distinct from i.contractor_id)

  union all
  select 'V2620M_PAYMENT_SOURCE_JOURNAL_MISMATCH','CRITICAL',count(*)::bigint,
    'Each supplier or opening settlement must match its own original and inverse money, accounts, party, and lifecycle'
  from(
    select p.id,p.status,p.amount,p.cash_account_id,'SUPPLIER_PAYMENT'::text source_type,
      erp.account_id('AP_SUPPLIER') balance_account,false incoming,
      null::uuid customer_id,null::uuid vendor_id,null::uuid contractor_id
    from erp.supplier_payments p
    union all
    select s.id,s.status,s.amount,s.cash_account_id,'OPENING_SUBLEDGER_SETTLEMENT',
      erp.account_id(case when b.party_type='CUSTOMER' then 'AR_CUSTOMER'
        when b.party_type='SUPPLIER' then 'AP_SUPPLIER'
        when b.party_type='VENDOR' then 'AP_VENDOR'
        when b.direction='RECEIVABLE' then 'CONTRACTOR_RECEIVABLE' else 'CONTRACTOR_PAYABLE' end),
      b.direction='RECEIVABLE',b.customer_id,b.vendor_id,b.contractor_id
    from erp.opening_subledger_settlements s
    join erp.opening_subledger_balances b on b.id=s.balance_id
  ) x
  left join erp.cash_accounts ca on ca.id=x.cash_account_id
  where x.amount<=0 or x.amount::text in('NaN','Infinity','-Infinity') or (ca.id is null and erp.initial_prepayment_account_v1(x.id) is null)
    or (select count(*) from erp.journal_entries j
      where j.source_type=x.source_type and j.source_id=x.id and j.status in('POSTED','REVERSED'))
      <>case when x.status='DRAFT' then 0 else 1 end
    or exists(
      select 1 from erp.journal_entries j
      where j.source_type=x.source_type and j.source_id=x.id and j.status in('POSTED','REVERSED') and(
        j.status is distinct from x.status
        or (select count(*) from erp.journal_lines l where l.journal_entry_id=j.id)<>2
        or exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and(
          l.customer_id is distinct from x.customer_id or l.vendor_id is distinct from x.vendor_id
          or l.contractor_id is distinct from x.contractor_id
          or not((l.account_id=coalesce(erp.initial_prepayment_account_v1(x.id),ca.coa_account_id) and
                l.debit=case when x.incoming then x.amount else 0 end and
                l.credit=case when x.incoming then 0 else x.amount end)
            or (l.account_id=x.balance_account and
                l.debit=case when x.incoming then 0 else x.amount end and
                l.credit=case when x.incoming then x.amount else 0 end))))
        or (select count(*) from erp.journal_entries inv where inv.reversal_of_id=j.id)
          <>case when x.status='REVERSED' then 1 else 0 end
        or exists(select 1 from erp.journal_entries inv where inv.reversal_of_id=j.id and(
          inv.source_type<>'JOURNAL_REVERSAL' or inv.status<>'POSTED'
          or (select count(*) from erp.journal_lines l where l.journal_entry_id=inv.id)<>2
          or exists(select 1 from erp.journal_lines l where l.journal_entry_id=inv.id and(
            l.customer_id is distinct from x.customer_id or l.vendor_id is distinct from x.vendor_id
            or l.contractor_id is distinct from x.contractor_id
            or not((l.account_id=coalesce(erp.initial_prepayment_account_v1(x.id),ca.coa_account_id) and
                  l.credit=case when x.incoming then x.amount else 0 end and
                  l.debit=case when x.incoming then 0 else x.amount end)
              or (l.account_id=x.balance_account and
                  l.credit=case when x.incoming then 0 else x.amount end and
                  l.debit=case when x.incoming then x.amount else 0 end))))))
      ))

  union all
  select 'V2620M_ORPHAN_PAYMENT_JOURNAL','CRITICAL',count(*)::bigint,
    'A supplier payment or opening settlement journal must retain its business source'
  from erp.journal_entries j
  where j.status in('POSTED','REVERSED') and(
    (j.source_type='SUPPLIER_PAYMENT' and not exists(select 1 from erp.supplier_payments p where p.id=j.source_id))
    or(j.source_type='OPENING_SUBLEDGER_SETTLEMENT' and not exists(
      select 1 from erp.opening_subledger_settlements s where s.id=j.source_id)))

  union all
  select 'V2620P_SUPPLIER_RETURN_MATCH_STATE','CRITICAL',count(*)::bigint,
    'Supplier invoice match and price states must equal posted invoice quantity against current return-adjusted capacity'
  from erp.material_purchase_items i
  cross join lateral(select erp.material_purchase_invoice_capacity(i.id) capacity,
    erp.material_purchase_posted_invoice_qty(i.id) matched) x
  where i.invoice_match_state<>'DIRECT_FINAL' and(
    i.invoice_match_state is distinct from case when x.matched<=0 then 'UNMATCHED'
      when x.matched<x.capacity then 'PARTIAL' else 'MATCHED' end
    or i.price_state is distinct from case when x.matched<=0 then 'ESTIMATED'
      when x.matched<x.capacity then 'PARTIAL' else 'FINAL' end)

  union all
  select 'V2620O_SUPPLIER_RETURN_ALLOCATION','CRITICAL',count(*)::bigint,
    'Posted supplier-return AP/GRNI snapshots must partition each line and AP relief must not exceed invoiced quantity'
  from erp.material_purchase_items i
  where exists(
    select 1
    from erp.material_supplier_return_items ri
    join erp.material_supplier_returns rh on rh.id=ri.return_id
    where ri.purchase_item_id=i.id and rh.status='POSTED' and(
      ri.ap_relief_qty_snapshot is null or ri.grni_relief_qty_snapshot is null
      or ri.ap_relief_amount_snapshot is null or ri.grni_relief_amount_snapshot is null
      or ri.ap_relief_qty_snapshot<0 or ri.grni_relief_qty_snapshot<0
      or ri.ap_relief_qty_snapshot::text in('NaN','Infinity','-Infinity')
      or ri.grni_relief_qty_snapshot::text in('NaN','Infinity','-Infinity')
      or ri.ap_relief_amount_snapshot::text in('NaN','Infinity','-Infinity')
      or ri.grni_relief_amount_snapshot::text in('NaN','Infinity','-Infinity')
      or abs(ri.ap_relief_qty_snapshot+ri.grni_relief_qty_snapshot-ri.qty)>0.000001
      or abs(ri.ap_relief_amount_snapshot
        -ri.ap_relief_qty_snapshot*ri.supplier_credit_unit_price)>0.000001
      or abs(ri.grni_relief_amount_snapshot
        -ri.grni_relief_qty_snapshot*i.unit_price)>0.000001
    )
  ) or coalesce((
    select sum(ri.ap_relief_qty_snapshot)
    from erp.material_supplier_return_items ri
    join erp.material_supplier_returns rh on rh.id=ri.return_id
    where ri.purchase_item_id=i.id and rh.status='POSTED'
  ),0)>case when i.invoice_match_state='DIRECT_FINAL' then i.qty
    else erp.material_purchase_posted_invoice_qty(i.id) end+0.000001
  or i.id in(
    with legacy_capacity as(
      select pi.id purchase_item_id,
        case when pi.invoice_match_state='DIRECT_FINAL' then pi.qty else
          coalesce((
            select sum(il.qty_invoiced)
            from erp.material_supplier_invoice_lines il
            join erp.material_supplier_invoices ih on ih.id=il.invoice_id
            where il.purchase_item_id=pi.id and ih.status='POSTED'
              and not exists(
                select 1 from erp.supplier_cent_posting_facts f
                where f.source_type='MATERIAL_SUPPLIER_INVOICE'
                  and f.source_id=ih.id and f.phase='POST'
              )
          ),0)
        end-coalesce((
          select sum(ri.ap_relief_qty_snapshot)
          from erp.material_supplier_return_items ri
          join erp.material_supplier_returns rh on rh.id=ri.return_id
          where ri.purchase_item_id=pi.id and rh.status='POSTED'
            and not exists(
              select 1 from erp.supplier_cent_posting_facts f
              where f.source_type='MATERIAL_SUPPLIER_RETURN'
                and f.source_id=rh.id and f.phase='POST'
            )
        ),0) opening_capacity
      from erp.material_purchase_items pi
    ), allocation_events as(
      select il.purchase_item_id,f.recorded_at,f.source_id,
        0 event_order,sum(il.qty_invoiced)::numeric delta,'INVOICE'::text event_kind
      from erp.supplier_cent_posting_facts f
      join erp.material_supplier_invoices ih
        on ih.id=f.source_id and ih.status='POSTED'
      join erp.material_supplier_invoice_lines il on il.invoice_id=ih.id
      join erp.material_purchase_items pi on pi.id=il.purchase_item_id
      where f.source_type='MATERIAL_SUPPLIER_INVOICE' and f.phase='POST'
        and pi.invoice_match_state<>'DIRECT_FINAL'
      group by il.purchase_item_id,f.recorded_at,f.source_id
      union all
      select ri.purchase_item_id,f.recorded_at,f.source_id,
        1 event_order,-sum(ri.ap_relief_qty_snapshot)::numeric,'RETURN'::text
      from erp.supplier_cent_posting_facts f
      join erp.material_supplier_returns rh
        on rh.id=f.source_id and rh.status='POSTED'
      join erp.material_supplier_return_items ri on ri.return_id=rh.id
      where f.source_type='MATERIAL_SUPPLIER_RETURN' and f.phase='POST'
      group by ri.purchase_item_id,f.recorded_at,f.source_id
    ), running_capacity as(
      select e.purchase_item_id,e.event_kind,l.opening_capacity+
        sum(e.delta) over(
          partition by e.purchase_item_id
          order by e.recorded_at,e.event_order,e.source_id
          rows between unbounded preceding and current row
        ) capacity_after
      from allocation_events e
      join legacy_capacity l using(purchase_item_id)
    )
    select purchase_item_id from running_capacity
    where event_kind='RETURN' and capacity_after < -0.000001
  )

  union all
  select 'V2620R_SUPPLIER_INVOICE_SOURCE_STATE','CRITICAL',count(*)::bigint,
    'Every posted supplier invoice must reference only posted material receipts'
  from erp.material_supplier_invoices ih
  where ih.status='POSTED' and exists(
    select 1 from erp.material_supplier_invoice_lines il
    join erp.material_purchase_items pi on pi.id=il.purchase_item_id
    join erp.material_purchase_headers ph on ph.id=pi.purchase_id
    where il.invoice_id=ih.id and ph.status<>'POSTED'
  )

  union all
  select 'V2620Y_OPENING_SETTLEMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Opening settlement cash and subledger dates must follow the Jakarta physical event'
  from erp.journal_entries j
    join erp.opening_subledger_settlements h on h.id=j.source_id
    where j.source_type='OPENING_SUBLEDGER_SETTLEMENT'
      and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
      and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620Y_VENDOR_PAYMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Vendor payment cash and AP dates must follow the Jakarta payment event'
  from erp.journal_entries j
    join erp.vendor_payments h on h.id=j.source_id
    where j.source_type='VENDOR_PAYMENT'
      and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
      and j.economic_date is distinct from erp._cp3_business_date(h.payment_date)

  union all
  select 'V2620Y_SALES_PAYMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Original customer payment cash, AR and immutable fact dates must follow the Jakarta payment event'
  from erp.journal_entries j
    join erp.sales_payments h on h.id=j.source_id
    join erp.sales_payment_posting_facts f on f.payment_id=h.id
    where j.source_type='SALES_PAYMENT'
      and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
      and f.replaces_payment_id is null
      and (j.economic_date is distinct from erp._cp3_business_date(f.payment_date)
        or f.journal_economic_date is distinct from erp._cp3_business_date(f.payment_date))

  union all
  select 'V2620W_SCRAP_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Paid scrap economic dates must match the canonical Jakarta physical business date'
  from erp.journal_entries j
  join erp.scrap_sales h on h.id=j.source_id
  where j.source_type='SCRAP_SALE' and j.status in('POSTED','REVERSED')
    and h.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620V_MISC_FINANCE_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Misc finance economic dates must match the canonical Jakarta physical business date'
  from erp.journal_entries j
  join erp.misc_finance_transactions h on h.id=j.source_id
  where j.source_type='MISC_FINANCE' and j.status in('POSTED','REVERSED')
    and h.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620U_MATERIAL_ADJUSTMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Material adjustment journals must use the canonical Jakarta date of physical_at'
  from erp.journal_entries j
  join erp.material_adjustments h on h.id=j.source_id
  where j.source_type='MATERIAL_ADJUSTMENT' and j.status in('POSTED','REVERSED')
    and h.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620U_JOURNAL_REVERSAL_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Generic journal reversals must use the canonical Jakarta date of posting_at'
  from erp.journal_entries j
  where j.source_type='JOURNAL_REVERSAL' and j.status='POSTED'
    and j.economic_date is distinct from erp._cp3_business_date(j.posting_at)

  union all
  select 'V2620U_MATERIAL_RECEIPT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Material receipt and GRNI journals must use the canonical Jakarta date of physical_at'
  from erp.journal_entries j
  join erp.material_purchase_headers h on h.id=j.source_id
  where j.source_type in('MATERIAL_PURCHASE','MATERIAL_PURCHASE_GRNI_RECLASS')
    and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620T_JOURNAL_FUTURE_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Journal economic dates may not exceed the canonical Jakarta day of the recorded posting instant'
  from erp.journal_entries j
  where j.status in('POSTED','REVERSED')
    and j.economic_date>erp._cp3_business_date(j.posting_at)

  union all
  select 'V2620T_MATERIAL_ADJUSTMENT_REVALUATION','CRITICAL',count(*)::bigint,
    'Material adjustment revaluation must conserve document cents at original and corrected valuation endpoints'
  from erp.material_adjustments h
  cross join lateral(select erp._cp6_material_adjustment_revaluation_state(h.id) s) x
  where h.status in('POSTED','REVERSED')
    and (x.s->'target' is distinct from x.s->'book' or (x.s->>'incomplete_cost')::bigint>0)

  union all
  select 'V2620T_MATERIAL_ADJUSTMENT_FACT_LEDGER','CRITICAL',count(*)::bigint,
    'Append-only material adjustment revaluation facts must match their protected original journal'
  from erp.material_adjustment_revaluation_facts f
  left join erp.journal_entries j on j.id=f.journal_entry_id
  where j.id is null or j.status<>'POSTED' or j.source_type<>'MATERIAL_ADJUSTMENT_REVALUATION'
    or j.source_id is distinct from f.id or j.economic_date is distinct from f.effective_date
    or erp._cp6_supplier_cent_ledger(array[f.journal_entry_id]) is distinct from f.ledger_delta

  union all
  select 'V2620S_SUPPLIER_PAYMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Supplier payment original journals must retain the canonical Jakarta business date in every lifecycle state'
  from erp.supplier_payments p
  join erp.journal_entries j on j.source_type='SUPPLIER_PAYMENT' and j.source_id=p.id
    and j.status in('POSTED','REVERSED')
  where p.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(p.payment_date)

  union all
  select 'V2620N_SUPPLIER_CENT_FACT_LEDGER','CRITICAL',count(*)::bigint,
    'Supplier cent posting and linked inverse must retain their exact source and ledger vector'
  from erp.supplier_cent_posting_facts f
  where f.ledger_delta is distinct from erp._cp6_supplier_cent_ledger(array[f.journal_entry_id,f.adjustment_journal_entry_id])
    or(f.phase='POST' and f.adjustment_journal_entry_id is not null)
    or not exists(select 1 from(
      select 'MATERIAL_PURCHASE_COST_CORRECTION'::text source_type,id,status from erp.material_purchase_cost_corrections
      union all select 'MATERIAL_SUPPLIER_INVOICE',id,status from erp.material_supplier_invoices
      union all select 'MATERIAL_SUPPLIER_RETURN',id,status from erp.material_supplier_returns
    ) s where s.source_type=f.source_type and s.id=f.source_id
      and s.status=case when exists(select 1 from erp.supplier_cent_posting_facts r
        where r.source_type=f.source_type and r.source_id=f.source_id and r.phase='REVERSE') then 'REVERSED' else 'POSTED' end)
    or(f.journal_entry_id is not null and not exists(select 1 from erp.journal_entries j
      where j.id=f.journal_entry_id and(
        (f.phase='POST' and j.source_type=f.source_type and j.source_id=f.source_id)
        or(f.phase='REVERSE' and j.source_type='JOURNAL_REVERSAL' and exists(select 1
          from erp.journal_entries original where original.id=j.reversal_of_id
            and original.source_type=f.source_type and original.source_id=f.source_id)))))
    or(f.adjustment_journal_entry_id is not null and not exists(select 1 from erp.journal_entries j
      where j.id=f.adjustment_journal_entry_id and j.source_type='CENT_INVERSE:'||f.source_type
        and j.source_id=f.source_id))

  union all
  select 'AP_OPENING_RECEIPT_SOURCE_DRIFT','CRITICAL',count(*)::bigint,
    'Imported receipts require an exact posted opening layer and no additional purchase movement'
  from erp.initial_import_receipt_headers rh join erp.material_purchase_headers h on h.id=rh.purchase_id
  where h.status<>'POSTED' or h.supplier_id<>rh.supplier_id or erp._cp3_business_date(h.physical_at)<>rh.cutover_date
    or not exists(select 1 from erp.initial_import_receipt_lines l where l.purchase_id=h.id)
    or exists(select 1 from erp.material_purchase_items pi left join erp.initial_import_receipt_lines l on l.purchase_item_id=pi.id
      left join erp.opening_balance_items oi on oi.id=l.opening_item_id left join erp.opening_balance_headers oh on oh.id=oi.opening_id
      where pi.purchase_id=h.id and (l.purchase_id is distinct from h.id or (l.opening_item_id is not null and oh.status is distinct from 'POSTED')
        or (l.opening_item_id is not null and oi.balance_type is distinct from 'MATERIAL')
        or pi.qty is distinct from coalesce(oi.qty,0)+coalesce((select sum(material_qty) from erp.initial_import_cost_origins where purchase_item_id=pi.id),0)
        or (l.opening_item_id is not null and (pi.material_id is distinct from oi.material_id or pi.unit_price is distinct from oi.unit_cost_snapshot
        or oi.location_id is distinct from h.location_id))
        or (l.opening_item_id is not null and (select count(*) from erp.material_stock_movements m where m.source_type='OPENING_BALANCE_ITEM'
          and m.source_id=oi.id and m.movement_type='OPENING' and m.qty_signed=oi.qty)<>1)
        or exists(select 1 from erp.material_stock_movements m where m.source_type='MATERIAL_PURCHASE_ITEM' and m.source_id=pi.id)))
  union all
  select 'AP_OPENING_RECEIPT_JOURNAL_DRIFT','CRITICAL',count(*)::bigint,
    'Imported GRNI opening has exact value, opening equity offset, and cutover date'
  from erp.initial_import_receipt_headers rh
  cross join lateral(select round(sum(qty*unit_price),2) value from erp.material_purchase_items where purchase_id=rh.purchase_id) v
  where (v.value>0 and not exists(select 1 from erp.journal_entries j where j.source_type='OPENING_UNINVOICED_RECEIPT'
    and j.source_id=rh.purchase_id and j.status='POSTED' and j.economic_date=rh.cutover_date
    and erp._cp6_supplier_cent_ledger(array[j.id])=jsonb_build_object(erp.account_id('OPENING_EQUITY')::text,v.value,erp.account_id('GRNI_MATERIAL')::text,-v.value)))
    or exists(select 1 from erp.journal_entries j where j.source_id=rh.purchase_id and j.source_type in('MATERIAL_PURCHASE','MATERIAL_PURCHASE_GRNI_RECLASS'))

  union all
  select 'AP_CASH_ADVANCE_CAPACITY','CRITICAL',count(*)::bigint,
    'Cash advance settlements plus unpaid payroll reservations must not exceed the current opening source'
  from erp.opening_subledger_balances b cross join lateral(select erp.opening_cash_advance_state_v1(b.id) s) x
  where x.s is not null and (x.s->>'available_amount')::numeric<0
  union all
  select 'AP_CASH_ADVANCE_SOURCE','CRITICAL',count(*)::bigint,
    'Cash payroll deductions must reference a posted cash advance belonging to the same contractor'
  from erp.payroll_deductions d join erp.payroll_settlements p on p.id=d.payroll_id
  left join erp.opening_subledger_balances b on b.id=d.opening_cash_advance_balance_id
  left join erp.initial_import_financial_sources s on s.opening_item_id=b.opening_item_id
  where d.deduction_type='CASH_ADVANCE' and (s.source_kind is distinct from 'CONTRACTOR_CASH_ADVANCE'
    or s.party_id is distinct from p.contractor_id or b.contractor_id is distinct from p.contractor_id
    or (p.status='PAID' and p.payment_date<s.cutover_date))
  union all
  select 'AP_CASH_ADVANCE_PAYROLL_JOURNAL','CRITICAL',count(*)::bigint,
    'Cash advance payroll settles receivable/payable once, with exact date and contractor dimensions'
  from erp.payroll_settlements p
  cross join lateral(select coalesce(sum(amount),0) amount from erp.payroll_deductions
    where payroll_id=p.id and deduction_type='CASH_ADVANCE') d
  where (d.amount>0 and p.status='PAID' and not exists(select 1 from erp.journal_entries j
    where j.source_type='PAYROLL_CASH_ADVANCE_DEDUCTION' and j.source_id=p.id and j.status='POSTED'
      and j.economic_date=p.payment_date
      and erp._cp6_supplier_cent_ledger(array[j.id])=jsonb_build_object(
        erp.account_id('CONTRACTOR_PAYABLE')::text,d.amount,erp.account_id('CONTRACTOR_RECEIVABLE')::text,-d.amount)
      and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and l.contractor_id is distinct from p.contractor_id)))
    or((p.status<>'PAID' or d.amount=0) and exists(select 1 from erp.journal_entries j where j.source_type='PAYROLL_CASH_ADVANCE_DEDUCTION'
      and j.source_id=p.id and j.status='POSTED'))

 union all select * from erp.initial_prepayment_checks_v1()
UNION ALL SELECT * FROM erp.pocket_period_checks_v1()
 UNION ALL SELECT * FROM erp.pocket_fabric_checks_v1();

$function$;
CREATE OR REPLACE FUNCTION erp.validate_material_supplier_invoice_line()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare v_invoice_supplier uuid;v_purchase_supplier uuid;v_status text;
begin
  select supplier_id,status into v_invoice_supplier,v_status
  from erp.material_supplier_invoices where id=new.invoice_id;
  if v_status is null then raise exception 'Supplier invoice header not found'; end if;
  if v_status<>'DRAFT' then raise exception 'Supplier invoice lines may only change while DRAFT'; end if;

  select h.supplier_id into v_purchase_supplier
  from erp.material_purchase_items i
  join erp.material_purchase_headers h on h.id=i.purchase_id
  where i.id=new.purchase_item_id and h.status='POSTED';
  if v_purchase_supplier is null then raise exception 'Invoice line must reference a POSTED material receipt'; end if;
  if v_purchase_supplier is distinct from v_invoice_supplier then
    raise exception 'Invoice supplier does not match receipt supplier';
  end if;
  if exists(select 1 from erp.initial_import_receipt_lines l
    join erp.initial_import_receipt_headers r on r.purchase_id=l.purchase_id
    join erp.material_supplier_invoices h on h.id=new.invoice_id
    where l.purchase_item_id=new.purchase_item_id and h.invoice_date<r.cutover_date) then
    raise exception 'Invoice penerimaan awal tidak boleh mendahului cutover; rekonsiliasi dokumen lama terlebih dahulu';end if;
  return new;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.validate_supplier_return_source()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_header_supplier uuid;
  v_purchase_supplier uuid;
  v_purchase_material uuid;
  v_purchase_qty numeric(18,6);
  v_purchase_price numeric(18,6);
  v_roll_purchase_item uuid;
  v_prior numeric(18,6);
  v_current numeric(18,6);
begin
  select supplier_id into v_header_supplier from erp.material_supplier_returns where id=new.return_id;
  if v_header_supplier is null then raise exception 'Supplier return header not found'; end if;
  if new.roll_id is not null then
    select purchase_item_id into v_roll_purchase_item from erp.material_rolls where id=new.roll_id;
    if v_roll_purchase_item is null then
      select l.purchase_item_id into v_roll_purchase_item from erp.initial_import_receipt_lines l
      join erp.opening_balance_items i on i.id=l.opening_item_id where i.roll_id=new.roll_id;
    end if;
    if v_roll_purchase_item is null then raise exception 'Returned roll has no source purchase item'; end if;
    if new.purchase_item_id is not null and new.purchase_item_id is distinct from v_roll_purchase_item then raise exception 'Return purchase item does not match roll source purchase'; end if;
    new.purchase_item_id:=v_roll_purchase_item;
  end if;
  if new.purchase_item_id is null then raise exception 'Supplier return line must reference the source purchase item'; end if;
  select mph.supplier_id,mpi.material_id,mpi.qty into v_purchase_supplier,v_purchase_material,v_purchase_qty
  from erp.material_purchase_items mpi join erp.material_purchase_headers mph on mph.id=mpi.purchase_id
  where mpi.id=new.purchase_item_id and mph.status='POSTED';
  if v_purchase_material is null then raise exception 'Source purchase item must belong to a POSTED purchase'; end if;
  if v_purchase_supplier is distinct from v_header_supplier then raise exception 'Supplier return source purchase belongs to a different supplier'; end if;
  if v_purchase_material is distinct from new.material_id then raise exception 'Supplier return material does not match source purchase item'; end if;
  if exists(select 1 from erp.initial_import_receipt_lines l join erp.opening_balance_items i on i.id=l.opening_item_id
    where l.purchase_item_id=new.purchase_item_id and i.roll_id is distinct from new.roll_id) then
    raise exception 'Return roll does not match imported opening source';end if;
  v_purchase_price:=erp.material_purchase_current_unit_cost(new.purchase_item_id);
  new.supplier_credit_unit_price:=coalesce(new.supplier_credit_unit_price,v_purchase_price);
  select coalesce(sum(msri.qty),0) into v_prior from erp.material_supplier_return_items msri join erp.material_supplier_returns msr on msr.id=msri.return_id
  where msri.purchase_item_id=new.purchase_item_id and msri.id<>new.id and msr.status='POSTED';
  select coalesce(sum(msri.qty),0) into v_current from erp.material_supplier_return_items msri
  where msri.return_id=new.return_id and msri.purchase_item_id=new.purchase_item_id and msri.id<>new.id;
  if exists(select 1 from erp.initial_import_receipt_lines where purchase_item_id=new.purchase_item_id)
    and v_prior+v_current+new.qty>coalesce((select oi.qty from erp.initial_import_receipt_lines l join erp.opening_balance_items oi on oi.id=l.opening_item_id where l.purchase_item_id=new.purchase_item_id),0) then
    raise exception 'Supplier return cannot use quantities already consumed before cutover';end if;
  if v_prior+v_current+new.qty>v_purchase_qty+0.000001 then raise exception 'Supplier return exceeds quantity from source purchase item. Purchased %, prior returned %, current draft incl line %',v_purchase_qty,v_prior,v_current+new.qty; end if;
  return new;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.sync_material_purchase_grni_on_status()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare v_estimated numeric(24,6);v_journal uuid;v_reason text;
begin
  if old.status='DRAFT' and new.status='POSTED' then
    if exists(select 1 from erp.initial_import_receipt_headers where purchase_id=new.id) then
      select round(sum(qty*unit_price),2) into v_estimated from erp.material_purchase_items where purchase_id=new.id;
      if v_estimated>0 then
        perform erp.post_journal('OPENING_UNINVOICED_RECEIPT',new.id,erp._cp3_business_date(new.physical_at),
          'Opening receipt liability; physical stock already in opening balance',jsonb_build_array(
            jsonb_build_object('mapping_key','OPENING_EQUITY','debit',v_estimated,'credit',0),
            jsonb_build_object('mapping_key','GRNI_MATERIAL','debit',0,'credit',v_estimated)));
      end if;
      return new;
    end if;

    select coalesce(sum(i.line_total),0) into v_estimated
    from erp.material_purchase_items i
    where i.purchase_id=new.id and i.invoice_match_state<>'DIRECT_FINAL';
    if v_estimated>0.005 then
      perform erp.post_journal(
        'MATERIAL_PURCHASE_GRNI_RECLASS',new.id,erp._cp3_business_date(new.physical_at),
        'Receipt without final supplier invoice: AP reclassified to GRNI',
        jsonb_build_array(
          jsonb_build_object('mapping_key','AP_SUPPLIER','debit',round(v_estimated,2),'credit',0),
          jsonb_build_object('mapping_key','GRNI_MATERIAL','debit',0,'credit',round(v_estimated,2))
        )
      );
    end if;
  elsif old.status='POSTED' and new.status='REVERSED' then
    select id into v_journal from erp.journal_entries
    where source_type='MATERIAL_PURCHASE_GRNI_RECLASS' and source_id=new.id and status='POSTED'
    order by posting_at desc,id desc limit 1;
    if v_journal is not null then
      v_reason:=coalesce(nullif(current_setting('app.change_reason',true),''),'Material purchase reversal');
      perform erp.reverse_journal(v_journal,v_reason);
    end if;
  end if;
  return new;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.finalize_migration_batch(p_batch_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare v_opening uuid;v_status text;
begin
  perform erp.require_owner_admin();select status into v_status from erp.migration_batches where id=p_batch_id for update;if v_status is null then raise exception 'Migration batch not found';end if;if v_status='POSTED' then return;end if;if v_status not in('READY','POSTING') then raise exception 'Migration batch must be READY/POSTING';end if;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and validation_status<>'VALID') then raise exception 'Migration batch has validation errors';end if;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type in('BRAND','SIZE','MODEL','PRODUCT','CUSTOMER','SUPPLIER','CONTRACTOR','ACCESSORY_CATEGORY','MATERIAL','MATERIAL_ROLL','OPEN_PO','LAUNDRY_VENDOR','LOCATION','CHART_ACCOUNT','CASH_ACCOUNT','OPENING_COST_ORIGIN','UNINVOICED_RECEIPT','OPENING_ADVANCE') and posted_entity_id is null) then raise exception 'Migration batch still has unapplied master/roll/open-PO rows';end if;
  select id into v_opening from erp.opening_balance_headers where migration_batch_id=p_batch_id order by created_at limit 1;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type in('OPENING_BALANCE_ITEM','MATERIAL_ROLL')) then
    if v_opening is null then raise exception 'Opening stock/balance rows exist but opening document was not prepared';end if;
    if (select status from erp.opening_balance_headers where id=v_opening)<>'POSTED' then raise exception 'Migration opening balance must be POSTED before finalizing batch';end if;
  end if;
  update erp.migration_batches set status='POSTED',posted_at=statement_timestamp(),error_message=null where id=p_batch_id;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason) values('migration_batches',p_batch_id,'POST',jsonb_build_object('status','POSTED'),erp.current_app_user_id(),'Finalize migration batch');
end;$function$;
CREATE OR REPLACE FUNCTION erp._cp6_supplier_cent_state(p_purchases uuid[])
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'pg_catalog', 'pg_temp'
AS $function$
 select coalesce(jsonb_object_agg(h.id::text,jsonb_build_object(
  'ap',round(erp.material_purchase_final_ap_total(h.id),2),
  'grni',round(erp.material_purchase_grni_total(h.id),2),
  'inventory',round(coalesce((select sum(case when exists(select 1 from erp.initial_import_receipt_lines origin where origin.purchase_item_id=i.id)
      then coalesce((select round(oi.qty*erp.material_purchase_current_unit_cost(i.id),2) from erp.initial_import_receipt_lines l join erp.opening_balance_items oi on oi.id=l.opening_item_id where l.purchase_item_id=i.id),0)
       +coalesce((select sum(round(o.material_qty*erp.material_purchase_current_unit_cost(i.id),2)) from erp.initial_import_cost_origins o where o.purchase_item_id=i.id),0)
      else i.qty*erp.material_purchase_current_unit_cost(i.id) end)
    from erp.material_purchase_items i where i.purchase_id=h.id),0)
   -coalesce((select sum(-m.qty_signed*coalesce(m.original_unit_cost_snapshot,m.unit_cost_snapshot))
    from erp.material_supplier_return_items ri
    join erp.material_supplier_returns r on r.id=ri.return_id and r.status='POSTED'
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    join erp.material_stock_movements m on m.source_type='MATERIAL_SUPPLIER_RETURN_ITEM'
      and m.source_id=ri.id and m.movement_type='SUPPLIER_RETURN'
    where i.purchase_id=h.id),0),2))), '{}')
 from erp.material_purchase_headers h where h.id=any(p_purchases) and h.status='POSTED'
$function$;
CREATE OR REPLACE FUNCTION erp.run_v268_financial_report_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_catalog', 'information_schema', 'pg_temp'
 SET "TimeZone" TO 'UTC'
AS $function$
begin
  perform erp.require_owner_admin();
  return query
  select r.check_name,r.severity,r.issue_count,r.details
  from erp._v268_financial_report_checks_pre_scope() r
  where r.check_name not in(
    'V268_BROWSER_DIRECT_FINANCIAL_WRITE',
    'V268_BROWSER_DIRECT_LEDGER_OR_INVOICE_WRITE',
    'V268_ACTIVE_SALE_MISSING_JOURNAL',
    'V268_POSTED_SALES_RETURN_MISSING_JOURNAL'
  )

  union all
  select 'V268_BROWSER_DIRECT_LEDGER_OR_INVOICE_WRITE','CRITICAL',count(*)::bigint,
    'Browser roles must not directly mutate ledger or supplier-invoice aggregates'
  from information_schema.role_table_grants g
  where g.table_schema='erp'
    and g.table_name in('journal_entries','journal_lines','account_daily_balances',
      'material_supplier_invoices','material_supplier_invoice_lines')
    and g.grantee in('PUBLIC','anon','authenticated')
    and g.privilege_type in('INSERT','UPDATE','DELETE')

  union all
  select 'V2620C_PO_HPP_TARGET_STATE_MISMATCH','CRITICAL',count(*)::bigint,
    'Saved PO HPP/FG/COGS/other state must equal independently recomputed current minor-unit targets'
  from erp.po_hpp_gl_state s
  cross join lateral erp.compute_po_hpp_gl_targets_v2620d(s.po_id) t
  where s.base_output_qty is distinct from coalesce(t.base_output_qty,0)
     or s.hpp_total_cost is distinct from round(coalesce(t.hpp_total_cost,0),2)
     or s.fg_value is distinct from round(coalesce(t.fg_value,0),2)
     or s.cogs_value is distinct from round(coalesce(t.cogs_value,0),2)
     or s.other_out_value is distinct from(
       round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)-round(coalesce(t.cogs_value,0),2))

  union all
  select 'V2620C_HPP_COMPONENT_SUM_MISMATCH','CRITICAL',count(*)::bigint,
    'Every current production HPP version must equal the exact sum of its traceable production components'
  from erp.hpp_versions h
  join erp.fg_lots fl on fl.id=h.lot_id and fl.lot_origin='PRODUCTION'
  where h.is_current and abs(h.total_cost-coalesce((
    select sum(c.total_cost) from erp.hpp_version_components c where c.hpp_version_id=h.id
  ),0))>0.000001

  union all
  select 'V2620C_PO_HPP_BOOK_MISMATCH','CRITICAL',count(*)::bigint,
    'Per-PO FG, COGS, and HPP-disposition books must equal the saved minor-unit state after every post, recost, cancellation, return, and reversal'
  from erp.po_hpp_gl_state s
  cross join lateral erp.compute_po_hpp_gl_book_v2620e(s.po_id) b
  where abs(b.fg_value-s.fg_value)>0.005
     or abs(b.cogs_value-s.cogs_value)>0.005
     or abs(b.other_out_value-s.other_out_value)>0.005

  union all
  select 'V2620C_WIP_SOURCE_CONSERVATION_MISMATCH','CRITICAL',count(*)::bigint,
    'Per-PO WIP book must equal independently sourced manufacturing cost not yet transferred into current HPP, net of an active final residual close'
  from erp.po_hpp_gl_state s
  cross join lateral(
    select (
      coalesce((
        select sum(-m.qty_signed*m.unit_cost_snapshot)
        from erp.material_stock_movements m
        where (m.source_type='CUTTING_GROUP' and m.source_id in(
          select g.id from erp.cutting_groups g where g.po_id=s.po_id
        )) or (m.source_type='CUTTING_GROUP_RETURN' and m.source_id in(
          select g.id from erp.cutting_groups g where g.po_id=s.po_id
        ))
      ),0)
      +coalesce((
        select sum(i.qty*i.unit_cost_snapshot)
        from erp.contractor_material_issue_items i
        join erp.contractor_material_issues h on h.id=i.issue_id and h.status='POSTED'
        join erp.materials m on m.id=i.material_id and m.material_type<>'ACCESSORY'
        where h.po_id=s.po_id
      ),0)
      +coalesce((
        select sum(l.amount_payable)
        from erp.work_completion_lines l
        join erp.work_completion_events h on h.id=l.completion_id and h.status='POSTED'
        where h.po_id=s.po_id
      ),0)
      +coalesce((
        select sum(a.allocated_amount)
        from erp.attendance_hpp_pool_allocations a
        join erp.attendance_hpp_pools h on h.id=a.pool_id and h.status='ACTIVE'
        where a.po_id=s.po_id
      ),0)
      +coalesce((
        with delivery_cost as(
          select dl.id,dl.qty_sent_pcs,dl.estimated_rate_snapshot,
            coalesce(sum(case when rh.status='POSTED'
              and rl.actual_cost_status in('ESTIMATED','FINAL')
              then rl.qty_good_received+rl.qty_bs_laundry else 0 end),0) qty_costed,
            coalesce(sum(case when rh.status='POSTED'
              and rl.actual_cost_status in('ESTIMATED','FINAL')
              then coalesce(rl.actual_cost,0) else 0 end),0) actual_cost
          from erp.laundry_delivery_lines dl
          join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
          left join erp.laundry_receipt_lines rl on rl.delivery_line_id=dl.id
          left join erp.laundry_receipts rh on rh.id=rl.receipt_id
          where d.po_id=s.po_id
          group by dl.id,dl.qty_sent_pcs,dl.estimated_rate_snapshot
        )
        select sum(actual_cost+greatest(qty_sent_pcs-qty_costed,0)
          *coalesce(estimated_rate_snapshot,0)) from delivery_cost
      ),0)
      +coalesce((
        select sum(rl.actual_cost)
        from erp.laundry_failed_wash_attempts a
        join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
          and rl.actual_cost_status in('ESTIMATED','FINAL')
        join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
        join erp.laundry_deliveries d on d.id=a.delivery_id and d.status='REVERSED'
        where d.po_id=s.po_id
      ),0)
      +coalesce((
        select sum(l.amount_payable)
        from erp.rework_component_lines l
        join erp.rework_orders r on r.id=l.rework_order_id
          and r.status<>'CANCELLED' and r.cost_posted=true
        join erp.bs_cases b on b.id=r.bs_case_id
        where b.po_id=s.po_id
      ),0)
      +coalesce((
        select sum(a.adjustment_amount) from erp.cost_adjustments a
        where a.po_id=s.po_id and a.component_type='OTHER'
      ),0)
      +coalesce((
        select sum(a.total_hpp_cost)
        from erp.fg_accessory_cost_snapshots a
        join erp.fg_lots fl on fl.id=a.lot_id
          and fl.lot_origin='PRODUCTION'
        where fl.po_id=s.po_id
      ),0)
      +coalesce((select sum(erp.initial_import_source_value_v1(ps.opening_item_id)) from erp.initial_import_production_sources ps where ps.po_id=s.po_id),0)
      -coalesce((select sum(e.target_amount-e.previous_amount) from erp.initial_import_bs_value_events e join erp.initial_import_production_sources ps on ps.opening_item_id=e.opening_item_id where ps.po_id=s.po_id),0)
      +coalesce((select sum(erp.pocket_period_amount_v1(d.pool_id,d.preceding_qty,d.sewing_qty)) from erp.pocket_period_destinations d where d.po_id=s.po_id),0)
    )::numeric source_cost
  ) truth
  cross join lateral(
    select coalesce(sum(jl.debit-jl.credit),0)::numeric wip_book
    from erp.journal_lines jl
    join erp.journal_entries je on je.id=jl.journal_entry_id
      and je.status in('POSTED','REVERSED')
    where jl.po_id=s.po_id and jl.account_id=erp.account_id('WIP')
  ) w
  cross join lateral(
    select coalesce(sum(e.residual_amount),0)::numeric active_wip_close
    from erp.po_wip_close_events e
    join erp.journal_entries je on je.id=e.journal_entry_id
      and je.source_type='PO_WIP_RESIDUAL_CLOSE' and je.status='POSTED'
    where e.po_id=s.po_id
  ) c
  where abs(w.wip_book-(round(truth.source_cost,2)-s.hpp_total_cost-c.active_wip_close))>0.005

  union all
  select 'V2620C_SALE_REVENUE_REPORT_INPUT_MISMATCH','CRITICAL',count(*)::bigint,
    'Each sale lifecycle must contribute its exact line total to SALES_REVENUE while active and zero after cancellation/reversal'
  from(
    select h.id,h.status,
      case when h.status in('POSTED','PARTIAL_PAID','PAID')
        then coalesce((select sum(i.line_total) from erp.sales_items i where i.sale_id=h.id),0)
        else 0 end::numeric expected_revenue,
      coalesce(sum(jl.credit-jl.debit),0)::numeric booked_revenue
    from erp.sales_headers h
    left join erp.journal_entries origin on origin.source_type='SALE' and origin.source_id=h.id
      and origin.status in('POSTED','REVERSED')
    left join erp.journal_entries je on je.id=origin.id
      or (je.source_type='JOURNAL_REVERSAL' and je.reversal_of_id=origin.id
          and je.status in('POSTED','REVERSED'))
    left join erp.journal_lines jl on jl.journal_entry_id=je.id
      and jl.account_id=erp.account_id('SALES_REVENUE')
    group by h.id,h.status
  ) x
  where abs(x.booked_revenue-x.expected_revenue)>0.005

  union all
  select 'V2620C_SALES_RETURN_REPORT_INPUT_MISMATCH','CRITICAL',count(*)::bigint,
    'Each sales-return lifecycle must reduce SALES_REVENUE by its exact refund while active and contribute zero after reversal'
  from(
    select h.id,h.status,
      case when h.status='POSTED'
        then -coalesce((select sum(i.refund_amount) from erp.sales_return_items i where i.return_id=h.id),0)
        else 0 end::numeric expected_revenue,
      coalesce(sum(jl.credit-jl.debit),0)::numeric booked_revenue
    from erp.sales_returns h
    left join erp.journal_entries origin on origin.source_type='SALES_RETURN' and origin.source_id=h.id
      and origin.status in('POSTED','REVERSED')
    left join erp.journal_entries je on je.id=origin.id
      or (je.source_type='JOURNAL_REVERSAL' and je.reversal_of_id=origin.id
          and je.status in('POSTED','REVERSED'))
    left join erp.journal_lines jl on jl.journal_entry_id=je.id
      and jl.account_id=erp.account_id('SALES_REVENUE')
    group by h.id,h.status
  ) x
  where abs(x.booked_revenue-x.expected_revenue)>0.005

  union all
  select 'V2620C_DRAFT_SALE_VALUE_LEAK','CRITICAL',count(*)::bigint,
    'An active Draft reservation may reduce sellable quantity but may not classify current HPP as COGS/other expense'
  from(
    select distinct fl.po_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.sales_headers h on h.id=i.sale_id and h.status='DRAFT'
    join erp.fg_lots fl on fl.id=a.lot_id and fl.po_id is not null
  ) d
  cross join lateral erp.compute_po_hpp_gl_targets_v2620d(d.po_id) t
  where abs(coalesce(t.other_out_value,0))>0.005

  union all
  select 'V2620C_VENDOR_PAYMENT_EXACT_STATUS_MISMATCH','CRITICAL',count(*)::bigint,
    'Vendor invoice PAID/PARTIAL status must match the exact two-decimal payment subledger'
  from erp.vendor_invoices h
  cross join lateral(
    select coalesce(sum(p.amount),0)::numeric(20,2) paid
    from erp.vendor_payments p where p.vendor_invoice_id=h.id and p.status='POSTED'
  ) x
  where (h.status='PAID' and x.paid<>h.total_amount)
     or (h.status='PARTIAL_PAID' and not(x.paid>0 and x.paid<h.total_amount))
     or (h.status='POSTED' and x.paid<>0)

  union all
  select 'V2620C_HPP_STATE_HAS_SUBCENT','CRITICAL',count(*)::bigint,
    'Cumulative PO HPP GL state must contain exactly the minor-unit amounts that were journaled'
  from erp.po_hpp_gl_state s
  where s.hpp_total_cost<>round(s.hpp_total_cost,2)
     or s.fg_value<>round(s.fg_value,2)
     or s.cogs_value<>round(s.cogs_value,2)
     or s.other_out_value<>round(s.other_out_value,2)

  union all
  select 'V2620D_REDISPATCH_PARTICIPANT_LINEAGE_MISMATCH','CRITICAL',count(*)::bigint,
    'Every carried participant interval must be contiguous, bounded, acyclic, same-source, and descend from a prior immutable full return'
  from(
    select a.id issue_id
    from erp.laundry_redispatch_participant_allocations a
    join erp.laundry_delivery_batch_size_lines sx
      on sx.id=a.source_delivery_batch_size_line_id
    join erp.laundry_delivery_lines sdl on sdl.id=sx.delivery_line_id
    join erp.laundry_deliveries sd on sd.id=sdl.delivery_id
    join erp.laundry_delivery_batch_size_lines dx
      on dx.id=a.successor_delivery_batch_size_line_id
    join erp.laundry_delivery_lines ddl on ddl.id=dx.delivery_line_id
    join erp.laundry_deliveries dd on dd.id=ddl.delivery_id
    where sx.distribution_batch_id<>dx.distribution_batch_id
       or sx.size_id<>dx.size_id or sdl.cutting_group_id<>ddl.cutting_group_id
       or sd.status<>'REVERSED'
       or (sd.physical_at,sd.created_at,sd.id)>=(dd.physical_at,dd.created_at,dd.id)
       or a.source_offset_pcs+a.qty_pcs>sx.qty_sent_pcs
       or a.successor_offset_pcs+a.qty_pcs>dx.qty_sent_pcs
       or not exists(
         select 1 from erp.laundry_failed_wash_attempts f
         join erp.laundry_failed_wash_batch_size_lines fx
           on fx.attempt_id=f.id and fx.delivery_batch_size_line_id=sx.id
          and fx.qty_attempted_pcs=sx.qty_sent_pcs
         join erp.laundry_receipts fr on fr.id=f.receipt_id
           and fr.status in('POSTED','REVERSED')
         join erp.wip_stage_events rv on rv.id=f.return_wip_event_id
           and rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
           and rv.stage_from='LAUNDRY' and rv.stage_to='SEWING'
           and rv.qty_pcs=f.qty_attempted_pcs
         join erp.wip_stage_events src on src.id=rv.source_id
           and src.source_type='LAUNDRY_DELIVERY_LINE'
           and src.source_id=sx.delivery_line_id
         join erp.laundry_delivery_lines fdl on fdl.id=src.source_id
           and fdl.delivery_id=f.delivery_id
           and rv.po_id=sd.po_id
           and rv.cutting_group_id=fdl.cutting_group_id
         where f.delivery_id=sd.id and f.custody_outcome='RETURN_UNPROCESSED'
           and fr.physical_at<=dd.physical_at and rv.physical_at<=dd.physical_at
       )
    union all
    select min(a.id::text)::uuid
    from erp.laundry_redispatch_participant_allocations a
    group by a.source_delivery_batch_size_line_id
    having min(a.source_offset_pcs)<>0
       or max(a.source_offset_pcs+a.qty_pcs)<>sum(a.qty_pcs)
    union all
    select min(a.id::text)::uuid
    from erp.laundry_redispatch_participant_allocations a
    group by a.successor_delivery_batch_size_line_id
    having min(a.successor_offset_pcs)<>0
       or max(a.successor_offset_pcs+a.qty_pcs)<>sum(a.qty_pcs)
  ) bad_lineage

  union all
  select 'V268_ACTIVE_SALE_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
    'Every active Sale with a monetary or rounded non-PO HPP effect requires its SALE journal'
  from erp.sales_headers h
  where h.status in('POSTED','PARTIAL_PAID','PAID')
    and round(coalesce((select sum(i.line_total) from erp.sales_items i
          where i.sale_id=h.id),0),2)>0.005
    and not exists(select 1 from erp.journal_entries j
      where j.source_type='SALE' and j.source_id=h.id and j.status='POSTED')

  union all
  select 'V268_POSTED_SALES_RETURN_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
    'Every posted return with a monetary or rounded non-PO HPP effect requires its SALES_RETURN journal'
  from erp.sales_returns h
  where h.status='POSTED'
    and round(coalesce((select sum(i.refund_amount)
          from erp.sales_return_items i where i.return_id=h.id),0),2)>0.005
    and not exists(select 1 from erp.journal_entries j
      where j.source_type='SALES_RETURN' and j.source_id=h.id and j.status='POSTED')

  union all
  select 'V2620F_NON_PO_PRODUCT_HPP_BOOK_MISMATCH','CRITICAL',count(*)::bigint,
    'Each non-PO product book must equal cumulative per-lot minor-unit HPP targets across every active Sale, return, correction, and reversal'
  from(
    select distinct fl.product_id
    from erp.fg_lots fl
    where fl.po_id is null
      and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
  ) p
  cross join lateral erp.compute_non_po_product_hpp_targets_v2620f(p.product_id) t
  cross join lateral erp.compute_non_po_product_hpp_book_v2620f(p.product_id) b
  where abs(t.hpp_total_cost-b.hpp_total_cost)>0.005
     or abs(t.fg_value-b.fg_value)>0.005
     or abs(t.cogs_value-b.cogs_value)>0.005
     or abs(t.other_out_value-b.other_out_value)>0.005

  union all
  select 'V2620E_SALES_RETURN_VALUE_EXCEEDS_SALE','CRITICAL',count(*)::bigint,
    'Posted cumulative product refund may never exceed the exact original product sale value'
  from(
    select sr.sale_id,i.product_id,sum(i.refund_amount)::numeric refund,
      coalesce((select sum(si.line_total) from erp.sales_items si
        where si.sale_id=sr.sale_id and si.product_id=i.product_id),0)::numeric sold
    from erp.sales_returns sr join erp.sales_return_items i on i.return_id=sr.id
    where sr.status='POSTED'
    group by sr.sale_id,i.product_id
  ) refund where refund.refund>refund.sold

  union all
  select 'V2620E_OPENING_HPP_LINEAGE_MISMATCH','CRITICAL',count(*)::bigint,
    'Opening FG HPP must follow its opening source or latest active correction and must not pretend to have production components'
  from erp.fg_lots fl
  left join lateral(
    select count(*)::integer movement_count,min(m.id::text)::uuid movement_id,
      min(m.source_id::text)::uuid source_id,min(m.qty_signed)::integer qty_signed,
      min(m.unit_hpp_snapshot)::numeric unit_hpp
    from erp.fg_stock_movements m
    where m.lot_id=fl.id and m.movement_type='OPENING'
  ) om on true
  left join erp.opening_balance_items oi on oi.id=om.source_id
  left join erp.opening_balance_headers oh on oh.id=oi.opening_id
  left join lateral(
    select count(*)::integer current_count,min(h.id::text)::uuid current_id,
      min(h.qty_basis_pcs)::integer qty_basis,min(h.total_cost)::numeric total_cost
    from erp.hpp_versions h where h.lot_id=fl.id and h.is_current
  ) ch on true
  left join lateral(
    select h.total_cost,h.qty_basis_pcs
    from erp.hpp_versions h where h.lot_id=fl.id
    order by h.version_no,h.id limit 1
  ) first_hpp on true
  left join lateral(
    select c.corrected_hpp
    from erp.opening_hpp_corrections c
    join erp.hpp_versions h on h.id=c.hpp_version_id
    where c.lot_id=fl.id and c.status='POSTED'
    order by h.version_no desc,h.id desc limit 1
  ) correction on true
  where fl.lot_origin='OPENING' and(
    om.movement_count<>1 or ch.current_count<>1
    or oi.id is null or oi.balance_type<>'FINISHED_GOODS'
    or oh.status<>'POSTED' or oi.product_id is distinct from fl.product_id
    or om.qty_signed is distinct from fl.initial_qty_pcs
    or ch.qty_basis is distinct from fl.initial_qty_pcs
    or abs(first_hpp.total_cost-fl.initial_qty_pcs*om.unit_hpp)>0.000001
    or abs(om.unit_hpp-erp.resolve_opening_fg_unit_hpp(oi.id,oh.opening_date))>0.000001
    or abs(ch.total_cost-fl.initial_qty_pcs
      *coalesce(correction.corrected_hpp,om.unit_hpp))>0.000001
    or fl.cached_qty_pcs is distinct from coalesce((
      select sum(m.qty_signed)::integer from erp.fg_stock_movements m
      where m.lot_id=fl.id
    ),0)
    or exists(select 1 from erp.hpp_version_components c
      join erp.hpp_versions h on h.id=c.hpp_version_id where h.lot_id=fl.id)
  )

  union all
  select 'V2620E_OPENING_FG_GL_MISMATCH','CRITICAL',count(*)::bigint,
    'Each posted opening document FG journal must equal its immutable opening FG movement value'
  from erp.opening_balance_headers h
  cross join lateral(
    select coalesce(sum(round(m.qty_signed*m.unit_hpp_snapshot,2)),0)::numeric expected_fg
    from erp.opening_balance_items i
    join erp.fg_stock_movements m
      on m.source_type='OPENING_BALANCE_ITEM' and m.source_id=i.id
     and m.movement_type='OPENING'
    where i.opening_id=h.id and i.balance_type='FINISHED_GOODS'
  ) expected
  cross join lateral(
    select coalesce(sum(l.debit-l.credit),0)::numeric actual_fg
    from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
    where j.source_type='OPENING_BALANCE' and j.source_id=h.id
      and j.status='POSTED' and l.account_id=erp.account_id('FG_INVENTORY')
  ) actual
  where h.status='POSTED' and abs(expected.expected_fg-actual.actual_fg)>0.005

  union all
  select 'V2620I_SALES_PAYMENT_JOURNAL_LINEAGE_MISMATCH','CRITICAL',count(*)::bigint,
    'Each customer payment must own exactly one exact cash/AR journal and, when reversed, exactly one exact inverse'
  from(
    select p.id
    from erp.sales_payments p
    join erp.sales_headers h on h.id=p.sale_id
    where
      (p.status='DRAFT' and exists(
        select 1 from erp.journal_entries o
        where o.source_type='SALES_PAYMENT' and o.source_id=p.id
      ))
      or
      (p.status in('POSTED','REVERSED') and(
        (select count(*) from erp.journal_entries o
         where o.source_type='SALES_PAYMENT' and o.source_id=p.id)<>1
        or not exists(
          select 1
          from erp.journal_entries o
          where o.source_type='SALES_PAYMENT' and o.source_id=p.id
            and o.status=case when p.status='POSTED' then 'POSTED' else 'REVERSED' end
            and o.economic_date=case when p.replaces_payment_id is null
          then erp._cp3_business_date(p.payment_date) else (select pr.reversal_economic_date
            from erp.sales_payment_reversal_facts pr
            where pr.payment_id=p.replaces_payment_id) end
            and (select count(*) from erp.journal_lines l where l.journal_entry_id=o.id)=2
            and (select coalesce(sum(l.debit),0) from erp.journal_lines l where l.journal_entry_id=o.id)=p.amount
            and (select coalesce(sum(l.credit),0) from erp.journal_lines l where l.journal_entry_id=o.id)=p.amount
            and (select count(*) from erp.journal_lines l
                 left join erp.cash_accounts ca on ca.id=p.cash_account_id
                 where l.account_id=coalesce(erp.initial_prepayment_account_v1(p.id),ca.coa_account_id) and l.journal_entry_id=o.id and l.debit=p.amount and l.credit=0
                   and l.customer_id=h.customer_id and l.vendor_id is null
                   and l.contractor_id is null and l.po_id is null and l.product_id is null)=1
            and (select count(*) from erp.journal_lines l
                 where l.journal_entry_id=o.id and l.account_id=erp.account_id('AR_CUSTOMER')
                   and l.debit=0 and l.credit=p.amount and l.customer_id=h.customer_id
                   and l.vendor_id is null and l.contractor_id is null
                   and l.po_id is null and l.product_id is null)=1
            and (
              (p.status='POSTED' and not exists(
                select 1 from erp.journal_entries r
                where r.source_type='JOURNAL_REVERSAL'
                  and (r.source_id=o.id or r.reversal_of_id=o.id)
              ))
              or
              (p.status='REVERSED'
                and (select count(*) from erp.journal_entries r
                     where r.source_type='JOURNAL_REVERSAL'
                       and (r.source_id=o.id or r.reversal_of_id=o.id))=1
                and exists(
                  select 1 from erp.journal_entries r
                  where r.source_type='JOURNAL_REVERSAL' and r.source_id=o.id
                    and r.reversal_of_id=o.id and r.status='POSTED'
                    and (select count(*) from erp.journal_lines x where x.journal_entry_id=r.id)=2
                    and not exists(
                      select 1 from erp.journal_lines ol
                      where ol.journal_entry_id=o.id and not exists(
                        select 1 from erp.journal_lines rl
                        where rl.journal_entry_id=r.id
                          and rl.account_id=ol.account_id
                          and rl.debit=ol.credit and rl.credit=ol.debit
                          and rl.customer_id is not distinct from ol.customer_id
                          and rl.vendor_id is not distinct from ol.vendor_id
                          and rl.contractor_id is not distinct from ol.contractor_id
                          and rl.po_id is not distinct from ol.po_id
                          and rl.product_id is not distinct from ol.product_id
                      )
                    )
                    and not exists(
                      select 1 from erp.journal_lines rl
                      where rl.journal_entry_id=r.id and not exists(
                        select 1 from erp.journal_lines ol
                        where ol.journal_entry_id=o.id
                          and ol.account_id=rl.account_id
                          and ol.debit=rl.credit and ol.credit=rl.debit
                          and ol.customer_id is not distinct from rl.customer_id
                          and ol.vendor_id is not distinct from rl.vendor_id
                          and ol.contractor_id is not distinct from rl.contractor_id
                          and ol.po_id is not distinct from rl.po_id
                          and ol.product_id is not distinct from rl.product_id
                      )
                    )
                )
              )
            )
        )
      ))
    union all
    select o.id
    from erp.journal_entries o
    where o.source_type='SALES_PAYMENT'
      and not exists(select 1 from erp.sales_payments p where p.id=o.source_id)
  ) payment_lineage_faults

  union all
  select 'V2620K_PAYMENT_ALLOCATION_DATE_MISMATCH','CRITICAL',count(*)::bigint,
    'Allocation replacement must conserve cash and customer AR on each economic and GL date'
  from erp.sales_payment_posting_facts f
  left join erp.sales_payment_reversal_facts pr on pr.payment_id=f.replaces_payment_id
  where f.replaces_payment_id is not null and(
    pr.payment_id is null
    or f.journal_economic_date is distinct from pr.reversal_economic_date
    or f.journal_transaction_date is distinct from pr.reversal_transaction_date
    or f.journal_posting_at<pr.reversal_posting_at)

  union all
  select 'V2620J_SALES_PAYMENT_IMMUTABLE_FACT_MISMATCH','CRITICAL',count(*)::bigint,
    'Posted payment invoice/cash identity and reversal dates must match append-only facts; correction requires one linked replacement'
  from(
    select p.id
    from erp.sales_payments p
    left join erp.sales_headers h on h.id=p.sale_id
    left join erp.sales_payment_posting_facts f on f.payment_id=p.id
    left join erp.journal_entries o on o.id=f.original_journal_entry_id
    left join erp.sales_payment_reversal_facts rf on rf.payment_id=p.id
    left join erp.journal_entries r on r.id=rf.reversal_journal_entry_id
    left join erp.sales_payment_posting_facts pf on pf.payment_id=f.replaces_payment_id
    left join erp.sales_payment_reversal_facts prf on prf.payment_id=f.replaces_payment_id
    where
      (p.status='DRAFT' and(f.payment_id is not null or rf.payment_id is not null))
      or
      (p.status in('POSTED','REVERSED') and(
        f.payment_id is null or h.id is null
        or f.sale_id is distinct from p.sale_id
        or f.customer_id is distinct from h.customer_id
        or f.payment_number is distinct from p.payment_number
        or f.payment_date is distinct from p.payment_date
        or f.amount is distinct from p.amount
        or f.cash_account_id is distinct from p.cash_account_id
        or f.replaces_payment_id is distinct from p.replaces_payment_id
        or f.payment_snapshot is distinct from to_jsonb(p)-'status'
        or f.lineage_sha256 is distinct from encode(extensions.digest(convert_to(jsonb_build_array(
          f.payment_id,f.sale_id,f.customer_id,f.payment_number,f.payment_date,f.amount,
          f.cash_account_id,f.original_journal_entry_id,f.journal_economic_date,
          f.journal_transaction_date,f.journal_posting_at,f.replaces_payment_id,
          f.predecessor_reversal_journal_id,f.payment_snapshot
        )::text,'UTF8'),'sha256'),'hex')
        or o.id is null or o.source_type<>'SALES_PAYMENT' or o.source_id is distinct from p.id
        or o.status is distinct from case when p.status='POSTED' then 'POSTED' else 'REVERSED' end
        or o.economic_date is distinct from f.journal_economic_date
        or o.transaction_date is distinct from f.journal_transaction_date
        or o.posting_at is distinct from f.journal_posting_at
        or ((f.replaces_payment_id is null)<>(f.predecessor_reversal_journal_id is null))
        or (f.replaces_payment_id is not null and(
          pf.payment_id is null or prf.payment_id is null
          or f.predecessor_reversal_journal_id is distinct from prf.reversal_journal_entry_id
          or pf.sale_id=f.sale_id or pf.customer_id is distinct from f.customer_id
          or pf.amount is distinct from f.amount
          or pf.cash_account_id is distinct from f.cash_account_id
          or pf.payment_date is distinct from f.payment_date
        ))
        or (p.status='POSTED' and(
          rf.payment_id is not null or exists(
            select 1 from erp.journal_entries x where x.source_type='JOURNAL_REVERSAL'
              and(x.source_id=o.id or x.reversal_of_id=o.id)
          )
        ))
        or (p.status='REVERSED' and(
          rf.payment_id is null or r.id is null
          or rf.original_journal_entry_id is distinct from o.id
          or r.source_type<>'JOURNAL_REVERSAL' or r.source_id is distinct from o.id
          or r.reversal_of_id is distinct from o.id or r.status<>'POSTED'
          or r.economic_date is distinct from rf.reversal_economic_date
          or r.transaction_date is distinct from rf.reversal_transaction_date
          or r.posting_at is distinct from rf.reversal_posting_at
          or rf.reversal_economic_date<f.journal_economic_date
          or rf.reversal_posting_at<f.journal_posting_at
          or rf.lineage_sha256 is distinct from encode(extensions.digest(convert_to(jsonb_build_array(
            rf.payment_id,rf.original_journal_entry_id,rf.reversal_journal_entry_id,
            rf.reversal_economic_date,rf.reversal_transaction_date,rf.reversal_posting_at
          )::text,'UTF8'),'sha256'),'hex')
        ))
      ))
    union all
    select f.payment_id from erp.sales_payment_posting_facts f
    left join erp.sales_payments p on p.id=f.payment_id where p.id is null
    union all
    select r.payment_id from erp.sales_payment_reversal_facts r
    left join erp.sales_payments p on p.id=r.payment_id
    left join erp.sales_payment_posting_facts f on f.payment_id=r.payment_id
    where p.id is null or f.payment_id is null or p.status<>'REVERSED'
  ) payment_fact_faults

  union all
  select 'V2620H_FAILED_WASH_RETURN_TIME_MISMATCH','CRITICAL',count(*)::bigint,
    'RETURN_UNPROCESSED inverse WIP time must equal its authoritative physical receipt time'
  from erp.laundry_failed_wash_attempts a
  left join erp.laundry_receipts rh on rh.id=a.receipt_id
  left join erp.wip_stage_events rv on rv.id=a.return_wip_event_id
  where a.custody_outcome='RETURN_UNPROCESSED' and(
    rh.id is null or rv.id is null
    or rv.source_type<>'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
    or rv.physical_at is distinct from rh.physical_at
  )

  union all
  select 'V2620H_CUSTOMER_AR_STATUS_MISMATCH','CRITICAL',count(*)::bigint,
    'Sale PAID/PARTIAL/POSTED status must equal the exact two-decimal payment subledger and overpayment is unsupported'
  from erp.sales_headers h
  cross join lateral(
    select round(erp.sale_net_total(h.id),2)::numeric(20,2) total,
      round(coalesce(sum(round(p.amount,2)),0),2)::numeric(20,2) paid
    from erp.sales_payments p where p.sale_id=h.id and p.status='POSTED'
  ) x
  where h.status in('POSTED','PARTIAL_PAID','PAID') and(
    x.paid>x.total
    or (h.status='PAID' and x.paid<>x.total)
    or (h.status='PARTIAL_PAID' and not(x.paid>0 and x.paid<x.total))
    or (h.status='POSTED' and x.paid<>0)
  )

  union all
  select 'V2620H_CUSTOMER_AR_BY_CUSTOMER_MISMATCH','CRITICAL',count(*)::bigint,
    'Each customer signed AR general-ledger balance must equal active net sales less posted payments'
  from(
    select coalesce(g.customer_id,s.customer_id) customer_id,
      coalesce(g.amount,0)::numeric gl_amount,coalesce(s.amount,0)::numeric subledger_amount
    from(
      select jl.customer_id,sum(jl.debit-jl.credit)::numeric amount
      from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
      where je.status in('POSTED','REVERSED') and jl.account_id=erp.account_id('AR_CUSTOMER')
        and jl.customer_id is not null
      group by jl.customer_id
    ) g
    full join(
      select x.customer_id,sum(x.amount)::numeric amount from(
        select h.customer_id,round(erp.sale_net_total(h.id),2)-coalesce((
          select sum(round(p.amount,2)) from erp.sales_payments p
          where p.sale_id=h.id and p.status='POSTED'),0) amount
        from erp.sales_headers h where h.status in('POSTED','PARTIAL_PAID','PAID')
        union all
        select ob.customer_id,ob.original_amount-ob.settled_amount
        from erp.opening_subledger_balances ob
        join erp.opening_balance_items oi on oi.id=ob.opening_item_id
        join erp.opening_balance_headers oh on oh.id=oi.opening_id and oh.status='POSTED'
        where ob.party_type='CUSTOMER' and ob.direction='RECEIVABLE'
      ) x group by x.customer_id
    ) s on s.customer_id=g.customer_id
  ) ar where round(ar.gl_amount,2) is distinct from round(ar.subledger_amount,2)

  union all
  select 'V2620G_LAUNDRY_WIP_CUSTODY_MISMATCH','CRITICAL',count(*)::bigint,
    'Laundry source and inverse events must match authoritative delivery quantity, dimensions, direction, chronology and net physical custody'
  from(
    select dl.id
    from erp.laundry_delivery_lines dl
    join erp.laundry_deliveries d on d.id=dl.delivery_id
    join erp.production_orders po on po.id=d.po_id
    left join lateral(
      select count(*) total_sources,
        count(*) filter(where s.po_id=d.po_id
          and s.cutting_group_id is not distinct from dl.cutting_group_id
          and s.contractor_id is not distinct from po.contractor_id
          and s.stage_from='SEWING' and s.stage_to='LAUNDRY'
          and s.qty_pcs=dl.qty_sent_pcs and s.physical_at=d.physical_at) valid_sources,
        coalesce(sum(s.qty_pcs),0) source_qty
      from erp.wip_stage_events s
      where s.source_type='LAUNDRY_DELIVERY_LINE' and s.source_id=dl.id
    ) source on true
    left join lateral(
      select count(*) total_inverses,
        count(*) filter(where r.po_id=s.po_id
          and r.cutting_group_id is not distinct from s.cutting_group_id
          and r.contractor_id is not distinct from s.contractor_id
          and r.stage_from='LAUNDRY' and r.stage_to='SEWING'
          and r.qty_pcs=dl.qty_sent_pcs and r.qty_pcs=s.qty_pcs
          and r.physical_at>=s.physical_at) valid_inverses,
        coalesce(sum(r.qty_pcs),0) inverse_qty
      from erp.wip_stage_events s
      join erp.wip_stage_events r on r.source_id=s.id
        and r.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
      where s.source_type='LAUNDRY_DELIVERY_LINE' and s.source_id=dl.id
    ) inverse on true
    where d.status<>'DRAFT' and(
      source.total_sources<>1 or source.valid_sources<>1
      or inverse.total_inverses<>case when d.status='REVERSED' then 1 else 0 end
      or inverse.valid_inverses<>inverse.total_inverses
      or source.source_qty-inverse.inverse_qty<>
        case when d.status='REVERSED' then 0 else dl.qty_sent_pcs end
    )
    union all
    select s.id from erp.wip_stage_events s
    left join erp.laundry_delivery_lines dl on dl.id=s.source_id
    left join erp.laundry_deliveries d on d.id=dl.delivery_id
    where s.source_type='LAUNDRY_DELIVERY_LINE'
      and(dl.id is null or d.id is null or d.status='DRAFT')
    union all
    select r.id from erp.wip_stage_events r
    left join erp.wip_stage_events s on s.id=r.source_id
      and s.source_type='LAUNDRY_DELIVERY_LINE'
    where r.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL' and s.id is null
  ) bad_custody

  union all
  select 'V2620E_REDISPATCH_EVENT_MISMATCH','CRITICAL',count(*)::bigint,
    'Effective redispatch allocation/release events must be bounded, non-overlapping, chronological, and backed by exact custody facts'
  from(
    select a.id
    from erp.laundry_redispatch_participant_events a
    join erp.laundry_delivery_batch_size_lines sx
      on sx.id=a.source_delivery_batch_size_line_id
    join erp.laundry_delivery_lines sl on sl.id=sx.delivery_line_id
    join erp.laundry_deliveries sd on sd.id=sl.delivery_id
    join erp.laundry_delivery_batch_size_lines dx
      on dx.id=a.successor_delivery_batch_size_line_id
    join erp.laundry_delivery_lines dl on dl.id=dx.delivery_line_id
    join erp.laundry_deliveries dd on dd.id=dl.delivery_id
    where a.event_type='ALLOCATE' and(
      sx.distribution_batch_id<>dx.distribution_batch_id or sx.size_id<>dx.size_id
      or sl.cutting_group_id<>dl.cutting_group_id or sd.status<>'REVERSED'
      or (sd.physical_at,sd.created_at,sd.id)>=(dd.physical_at,dd.created_at,dd.id)
      or a.source_offset_pcs+a.qty_pcs>sx.qty_sent_pcs
      or a.successor_offset_pcs+a.qty_pcs>dx.qty_sent_pcs
      or not exists(
        select 1 from erp.laundry_failed_wash_attempts f
        join erp.laundry_failed_wash_batch_size_lines fx
          on fx.attempt_id=f.id and fx.delivery_batch_size_line_id=sx.id
         and fx.qty_attempted_pcs=sx.qty_sent_pcs
        join erp.laundry_receipts fr on fr.id=f.receipt_id
           and fr.status in('POSTED','REVERSED')
         join erp.wip_stage_events rv on rv.id=f.return_wip_event_id
           and rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
           and rv.stage_from='LAUNDRY' and rv.stage_to='SEWING'
           and rv.qty_pcs=f.qty_attempted_pcs
         join erp.wip_stage_events src on src.id=rv.source_id
           and src.source_type='LAUNDRY_DELIVERY_LINE'
           and src.source_id=sx.delivery_line_id
         join erp.laundry_delivery_lines fdl on fdl.id=src.source_id
           and fdl.delivery_id=f.delivery_id
           and rv.po_id=sd.po_id
           and rv.cutting_group_id=fdl.cutting_group_id
        where f.delivery_id=sd.id and f.custody_outcome='RETURN_UNPROCESSED'
          and fr.physical_at<=dd.physical_at and rv.physical_at<=dd.physical_at)
      or (not exists(select 1 from erp.laundry_redispatch_participant_events x
            where x.event_type='RELEASE' and x.releases_allocation_event_id=a.id)
          and dd.status='REVERSED'
          and not exists(select 1 from erp.laundry_receipts r where r.delivery_id=dd.id))
    )
    union all
    select a.id
    from erp.laundry_redispatch_participant_events a
    where a.event_type='ALLOCATE'
      and not exists(select 1 from erp.laundry_redispatch_participant_events x
        where x.event_type='RELEASE' and x.releases_allocation_event_id=a.id)
      and exists(
        select 1 from erp.laundry_redispatch_participant_events b
        where b.event_type='ALLOCATE' and b.id>a.id
          and not exists(select 1 from erp.laundry_redispatch_participant_events x
            where x.event_type='RELEASE' and x.releases_allocation_event_id=b.id)
          and ((b.source_delivery_batch_size_line_id=a.source_delivery_batch_size_line_id
              and int4range(b.source_offset_pcs,b.source_offset_pcs+b.qty_pcs,'[)')
                && int4range(a.source_offset_pcs,a.source_offset_pcs+a.qty_pcs,'[)'))
            or (b.successor_delivery_batch_size_line_id=a.successor_delivery_batch_size_line_id
              and int4range(b.successor_offset_pcs,b.successor_offset_pcs+b.qty_pcs,'[)')
                && int4range(a.successor_offset_pcs,a.successor_offset_pcs+a.qty_pcs,'[)')))
      )
    union all
    select x.id
    from erp.laundry_redispatch_participant_events x
    join erp.laundry_redispatch_participant_events a
      on a.id=x.releases_allocation_event_id and a.event_type='ALLOCATE'
    join erp.laundry_delivery_batch_size_lines sx
      on sx.id=a.successor_delivery_batch_size_line_id
    join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
    join erp.laundry_deliveries d on d.id=dl.delivery_id
    where x.event_type='RELEASE' and(
      x.released_delivery_id<>d.id or d.status<>'REVERSED'
      or exists(select 1 from erp.laundry_receipts r where r.delivery_id=d.id)
    )
  ) bad_events

  union all
  select 'V2620F_CONVERSION_VALUE_LINEAGE_MISMATCH','CRITICAL',count(*)::bigint,
    'Every posted conversion must be PO-sourced, value-preserving, rooted, and represented by exact OUT/IN facts with current descendant HPP'
  from erp.product_conversion_allocations a
  join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
  join erp.fg_lots s on s.id=a.source_lot_id
  left join erp.fg_lots d on d.id=a.destination_lot_id
  left join erp.v_current_hpp sh on sh.lot_id=s.id
  left join erp.v_current_hpp dh on dh.lot_id=d.id
  where s.po_id is null or d.id is null or d.po_id is distinct from s.po_id
     or d.lot_origin<>'CONVERSION' or d.source_lot_id is distinct from s.id
     or d.initial_qty_pcs is distinct from a.qty_pcs or a.qty_pcs<=0
     or sh.hpp_per_pcs is null or dh.hpp_per_pcs is null
     or abs(dh.hpp_per_pcs-(sh.hpp_per_pcs
       +a.conversion_cost_allocated/nullif(a.qty_pcs,0)))>0.000001
     or (select count(*) from erp.fg_stock_movements m
         where m.source_type='PRODUCT_CONVERSION' and m.source_id=c.id
           and m.lot_id=s.id and m.movement_type='REBRAND_OUT'
           and m.qty_signed=-a.qty_pcs)<>1
     or (select count(*) from erp.fg_stock_movements m
         where m.source_type='PRODUCT_CONVERSION' and m.source_id=c.id
           and m.lot_id=d.id and m.movement_type='REBRAND_IN'
           and m.qty_signed=a.qty_pcs)<>1

  union all
  select 'V2620D_SALE_LIFECYCLE_HPP_DIMENSION_MISMATCH','CRITICAL',count(*)::bigint,
    'Every Sale lifecycle journal must conserve FG/COGS/disposition independently inside each PO or non-PO dimension'
  from erp.journal_entries e
  left join erp.journal_entries o on o.id=e.reversal_of_id
  cross join lateral(
    select coalesce(sum(l.debit-l.credit) filter(where l.account_id in(
      erp.account_id('COGS'),erp.account_id('FG_INVENTORY'),
      erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
    )),0) hpp_net
    from erp.journal_lines l where l.journal_entry_id=e.id
  ) b
  where e.status in('POSTED','REVERSED') and(
    e.source_type in('SALE','SALES_RETURN')
    or(e.source_type='JOURNAL_REVERSAL' and o.source_type in('SALE','SALES_RETURN'))
  ) and(
    abs(b.hpp_net)>0.005
    or exists(
      select 1 from erp.journal_lines l
      where l.journal_entry_id=e.id
        and l.account_id in(
          erp.account_id('COGS'),erp.account_id('FG_INVENTORY'),
          erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
        )
      group by l.po_id
      having abs(sum(l.debit-l.credit))>0.005
    )
  );
  return query
  select 'V2620AD_OPENING_MATERIAL_TIMELINE_MISMATCH'::text,'CRITICAL'::text,
    (select count(*)::bigint
    from erp.opening_balance_items i
    join erp.opening_balance_headers h on h.id=i.opening_id
    where h.status='POSTED' and i.balance_type='MATERIAL' and (
      (select count(*) from erp.material_stock_movements m
       where m.source_type='OPENING_BALANCE_ITEM' and m.source_id=i.id)<>1
      or not exists(select 1 from erp.material_stock_movements m
        where m.source_type='OPENING_BALANCE_ITEM' and m.source_id=i.id
          and m.movement_type='OPENING' and m.material_id=i.material_id
          and m.location_id=i.location_id and m.roll_id is not distinct from i.roll_id
          and m.physical_at=(h.opening_date::timestamp at time zone 'Asia/Jakarta'))
    )),
    'Every posted material opening line must own one movement at the start of its Jakarta document date'::text;

  return query
  select 'V2620AE_OPENING_MATERIAL_ROLL_INTEGRITY'::text,'CRITICAL'::text,
    (select count(*)::bigint
    from erp.opening_balance_items i
    join erp.opening_balance_headers h on h.id=i.opening_id and h.status='POSTED'
    left join erp.materials material on material.id=i.material_id
    left join erp.material_rolls roll on roll.id=i.roll_id
    where (i.roll_id is not null and i.balance_type<>'MATERIAL')
      or (i.balance_type='MATERIAL' and (
      (material.material_type='FABRIC' and i.roll_id is null)
      or (i.roll_id is not null and (
        material.material_type is distinct from 'FABRIC'
        or
        roll.material_id is distinct from i.material_id
        or roll.purchase_item_id is not null
        or i.qty>roll.original_qty
        or (select count(*) from erp.opening_balance_items other_i
            join erp.opening_balance_headers other_h on other_h.id=other_i.opening_id
            where other_h.status='POSTED' and other_i.balance_type='MATERIAL'
              and other_i.roll_id=i.roll_id)<>1
        or (select count(*) from erp.material_stock_movements opening_m
            where opening_m.roll_id=i.roll_id and opening_m.movement_type='OPENING'
              and opening_m.reversal_of_id is null)<>1
        or exists(select 1 from erp.material_stock_movements purchase_m
            where purchase_m.roll_id=i.roll_id and purchase_m.movement_type='PURCHASE'
              and purchase_m.reversal_of_id is null)
      ))
    ))),
    'Each posted opening roll must belong to one fabric line, enter once, and stay within original quantity'::text;

  return query
  select 'V2620AF_OPENING_SOURCE_LINEAGE_MISMATCH'::text,'CRITICAL'::text,
    (select count(*)::bigint from (
    select m.id
    from erp.material_stock_movements m
    left join erp.opening_balance_items i on i.id=m.source_id
    left join erp.opening_balance_headers h on h.id=i.opening_id
    where m.source_type='OPENING_BALANCE_ITEM' and m.movement_type='OPENING'
      and m.reversal_of_id is null and (
        h.status is distinct from 'POSTED' or i.balance_type is distinct from 'MATERIAL'
        or m.material_id is distinct from i.material_id
        or m.roll_id is distinct from i.roll_id or m.location_id is distinct from i.location_id
        or m.qty_signed is distinct from i.qty
        or m.input_unit_cost is distinct from coalesce((
          select erp.material_purchase_current_unit_cost(origin.purchase_item_id)::numeric(18,6)
          from erp.initial_import_receipt_lines origin where origin.opening_item_id=i.id),i.unit_cost_snapshot)
        or (exists(select 1 from erp.initial_import_receipt_lines origin where origin.opening_item_id=i.id)
          and coalesce(m.original_unit_cost_snapshot,m.unit_cost_snapshot) is distinct from i.unit_cost_snapshot))
    union all
    select m.id
    from erp.fg_stock_movements m
    left join erp.opening_balance_items i on i.id=m.source_id
    left join erp.opening_balance_headers h on h.id=i.opening_id
    where m.source_type='OPENING_BALANCE_ITEM' and m.movement_type='OPENING'
      and m.reversal_of_id is null and (
        h.status is distinct from 'POSTED' or i.balance_type is distinct from 'FINISHED_GOODS'
        or m.product_id is distinct from i.product_id or m.qty_signed is distinct from i.qty
        or (i.location_id is not null and m.location_id is distinct from i.location_id))
    union all
    select s.id
    from erp.opening_subledger_balances s
    left join erp.opening_balance_items i on i.id=s.opening_item_id
    left join erp.opening_balance_headers h on h.id=i.opening_id
    where h.status is distinct from 'POSTED'
      or i.balance_type is distinct from (s.party_type||'_'||s.direction)
      -- original_amount is the CURRENT corrected balance (numeric(20,2)),
      -- despite its legacy column name. The immutable opening line remains
      -- unchanged; posted linked correction deltas determine its effective sum.
      or s.original_amount is distinct from (round(i.amount,2)+coalesce((
        select sum(c.delta_amount) from erp.opening_financial_corrections c
        where c.opening_item_id=i.id and c.status='POSTED'),0))
    union all
    select h.id from erp.opening_balance_headers h
    where h.status='POSTED'
      and not exists(select 1 from erp.opening_balance_items i where i.opening_id=h.id)
    union all
    select e.id from erp.journal_entries e
    left join erp.opening_balance_headers h on h.id=e.source_id
    where e.source_type='OPENING_BALANCE' and e.reversal_of_id is null
      and h.status is distinct from 'POSTED'
    union all
    select h.id from erp.opening_balance_headers h
    cross join lateral (
      select coalesce(sum(greatest(coalesce(round(case
        when i.balance_type in('MATERIAL','FINISHED_GOODS') then i.qty*i.unit_cost_snapshot
        when i.balance_type='BS' and exists(select 1 from erp.initial_import_production_sources ps where ps.opening_item_id=i.id) then coalesce(i.amount,i.qty*i.unit_cost_snapshot)
        when i.balance_type='WIP' then coalesce(i.amount,coalesce(i.qty,0)*coalesce(i.unit_cost_snapshot,0))
        when i.balance_type in('CONTRACTOR_RECEIVABLE','CUSTOMER_RECEIVABLE','CASH_BANK') then i.amount
        else 0 end,2),0),0)),0) debits,
        coalesce(sum(greatest(coalesce(round(case
        when i.balance_type in('CONTRACTOR_PAYABLE','VENDOR_PAYABLE','SUPPLIER_PAYABLE') then i.amount
        else 0 end,2),0),0)),0) credits
      from erp.opening_balance_items i where i.opening_id=h.id
    ) expected
    cross join lateral (
      select coalesce(sum(l.debit),0) debits,coalesce(sum(l.credit),0) credits
      from erp.journal_entries e join erp.journal_lines l on l.journal_entry_id=e.id
      where e.source_type='OPENING_BALANCE' and e.source_id=h.id and e.reversal_of_id is null
    ) actual
    where h.status='POSTED' and (
      actual.debits<>greatest(expected.debits,expected.credits)
      or actual.credits<>greatest(expected.debits,expected.credits))
  ) broken_opening_lineage),
    'Opening stock and subledger facts require their original posted source with conserved quantity and input value'::text;

  return query select 'V2620AG_SALE_RESERVATION_LINEAGE_MISMATCH'::text,'CRITICAL'::text,(with active as (
  select m.* from erp.fg_stock_movements m
  where m.source_type='SALE_ITEM' and m.movement_type in('SALE_RESERVE','SALE')
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)
), allocations as (
  select a.sale_item_id,a.lot_id,a.location_id,sum(a.qty_pcs)::bigint qty
  from erp.sale_stock_allocations a group by a.sale_item_id,a.lot_id,a.location_id
), movements as (
  select m.source_id sale_item_id,m.lot_id,m.location_id,sum(-m.qty_signed)::bigint qty
  from active m group by m.source_id,m.lot_id,m.location_id
)
select count(*)::bigint from (
  select m.id,sh_lineage.id sale_id from active m
  left join erp.sales_items i on i.id=m.source_id
  left join erp.sales_headers sh_lineage on sh_lineage.id=i.sale_id
  left join erp.fg_lots l on l.id=m.lot_id
  where sh_lineage.status is null or sh_lineage.status not in('DRAFT','POSTED','PARTIAL_PAID','PAID')
    or m.movement_type is distinct from case when sh_lineage.status='DRAFT' then 'SALE_RESERVE' else 'SALE' end
    or m.product_id is distinct from i.product_id or l.product_id is distinct from i.product_id
    or m.location_id is distinct from sh_lineage.source_location_id
    or m.customer_id is distinct from sh_lineage.customer_id or m.physical_at is distinct from sh_lineage.sale_date
    or m.quality_grade is distinct from 'GRADE_A' or m.qty_signed>=0
  union all
  select a.id,sh_lineage.id from erp.sale_stock_allocations a
  left join erp.sales_items i on i.id=a.sale_item_id
  left join erp.sales_headers sh_lineage on sh_lineage.id=i.sale_id
  left join erp.fg_lots l on l.id=a.lot_id
  where sh_lineage.status is null or sh_lineage.status not in('DRAFT','POSTED','PARTIAL_PAID','PAID','REVERSED')
    or l.product_id is distinct from i.product_id
    or a.location_id is distinct from sh_lineage.source_location_id or a.qty_pcs<=0
  union all
  select i.id,sh_lineage.id from allocations a full join movements m using(sale_item_id,lot_id,location_id)
  join erp.sales_items i on i.id=coalesce(a.sale_item_id,m.sale_item_id)
  join erp.sales_headers sh_lineage on sh_lineage.id=i.sale_id
  where sh_lineage.status in('DRAFT','POSTED','PARTIAL_PAID','PAID') and a.qty is distinct from m.qty
  union all
  select i.id,sh_lineage.id from erp.sales_items i join erp.sales_headers sh_lineage on sh_lineage.id=i.sale_id
  where (sh_lineage.status in('POSTED','PARTIAL_PAID','PAID') or
    (sh_lineage.status='DRAFT' and (exists(select 1 from erp.sale_stock_allocations a
       join erp.sales_items sibling on sibling.id=a.sale_item_id where sibling.sale_id=sh_lineage.id)
      or exists(select 1 from active m join erp.sales_items sibling on sibling.id=m.source_id where sibling.sale_id=sh_lineage.id))))
    and (i.qty_pcs is distinct from (select coalesce(sum(a.qty_pcs),0) from erp.sale_stock_allocations a where a.sale_item_id=i.id)
      or i.qty_pcs is distinct from (select coalesce(sum(-m.qty_signed),0) from active m where m.source_id=i.id))
  union all
  select sh_lineage.id,sh_lineage.id from erp.sales_headers sh_lineage where sh_lineage.status in('POSTED','PARTIAL_PAID','PAID')
    and not exists(select 1 from erp.sales_items i where i.sale_id=sh_lineage.id)
) broken where /*SCOPE*/true),'Sale source and reserved or posted stock must agree on item, lot, quantity, location, customer and physical time'::text;
  return query select 'V2620AH_RETURN_ALLOCATION_LINEAGE_MISMATCH'::text,'CRITICAL'::text,(with active_return as (
  select ah_line.*,ah_return.sale_id,ah_return.customer_id,ah_return.physical_at
  from erp.sales_return_items ah_line join erp.sales_returns ah_return on ah_return.id=ah_line.return_id
  where ah_return.status='POSTED'
), live_movement as (
  select ah_movement.* from erp.fg_stock_movements ah_movement
  where ah_movement.source_type='SALES_RETURN_ITEM' and ah_movement.movement_type='SALE_RETURN'
    and not exists(select 1 from erp.fg_stock_movements ah_reversal where ah_reversal.reversal_of_id=ah_movement.id)
)
select count(*)::bigint from (
  select ah_line.id from active_return ah_line
  left join erp.sale_stock_allocations ah_allocation on ah_allocation.id=ah_line.sale_stock_allocation_id
  left join erp.sales_items ah_sale_line on ah_sale_line.id=ah_allocation.sale_item_id
  left join erp.sales_headers ah_sale on ah_sale.id=ah_sale_line.sale_id
  where ah_allocation.id is null or ah_sale.status is null or ah_sale.status not in('POSTED','PARTIAL_PAID','PAID')
    or ah_line.sale_id is distinct from ah_sale.id or ah_line.customer_id is distinct from ah_sale.customer_id
    or ah_line.product_id is distinct from ah_sale_line.product_id or ah_line.lot_id is distinct from ah_allocation.lot_id
    or ah_line.physical_at<ah_sale.sale_date
  union all
  select ah_allocation.id from erp.sale_stock_allocations ah_allocation join active_return ah_line on ah_line.sale_stock_allocation_id=ah_allocation.id
  group by ah_allocation.id,ah_allocation.qty_pcs having sum(ah_line.qty_pcs)>ah_allocation.qty_pcs
  union all
  select ah_movement.id from live_movement ah_movement left join active_return ah_line on ah_line.id=ah_movement.source_id
  where ah_line.id is null or ah_movement.product_id is distinct from ah_line.product_id or ah_movement.lot_id is distinct from ah_line.lot_id
    or ah_movement.location_id is distinct from ah_line.location_id or ah_movement.quality_grade is distinct from ah_line.quality_grade
    or ah_movement.customer_id is distinct from ah_line.customer_id or ah_movement.physical_at is distinct from ah_line.physical_at
    or ah_movement.qty_signed is distinct from ah_line.qty_pcs
  union all
  select ah_line.id from active_return ah_line left join live_movement ah_movement on ah_movement.source_id=ah_line.id
  group by ah_line.id,ah_line.qty_pcs having count(ah_movement.id)<>1 or sum(ah_movement.qty_signed) is distinct from ah_line.qty_pcs::bigint
  union all
  select ah_return.id from erp.sales_returns ah_return where ah_return.status='POSTED'
    and not exists(select 1 from erp.sales_return_items ah_line where ah_line.return_id=ah_return.id)
) broken),'Active return quantities and receipt facts must match their selected original sale allocation and chosen destination'::text;
  return query select 'V2620AI_WORK_SOURCE_LINEAGE_MISMATCH'::text,'CRITICAL'::text,(select count(*)::bigint from (
 select ai_line.id
 from erp.work_completion_lines ai_line
 join erp.work_completion_events ai_event on ai_event.id=ai_line.completion_id and ai_event.status='POSTED'
 left join erp.po_work_component_snapshots ai_snapshot on ai_snapshot.id=ai_line.po_component_snapshot_id
 left join erp.production_orders ai_po on ai_po.id=ai_event.po_id
 left join erp.cutting_groups ai_group on ai_group.id=ai_event.cutting_group_id
 where ai_snapshot.id is null or ai_po.id is null or ai_group.id is null
   or ai_snapshot.po_id is distinct from ai_event.po_id
   or ai_snapshot.work_component_id is distinct from ai_line.work_component_id
   or ai_snapshot.rate_per_pcs_snapshot is distinct from ai_line.rate_snapshot
   or ai_group.po_id is distinct from ai_event.po_id
   or ai_po.contractor_id is distinct from ai_event.contractor_id
 union all
 select ai_event.id from erp.work_completion_events ai_event
 where ai_event.status='POSTED' and not exists(select 1 from erp.work_completion_lines ai_line where ai_line.completion_id=ai_event.id)
) ai_broken),'Posted work must retain the selected PO, contractor, component and committed rate snapshot'::text;
end
$function$;
CREATE OR REPLACE FUNCTION erp.check_initial_import_receipt_v1(p_batch_id uuid,p_row_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD' AS $function$
declare r erp.migration_staging_rows%rowtype;s erp.migration_staging_rows%rowtype;
 j jsonb;v_cutover date;v_party uuid;v_key text;v_number text;v_line text;v_date date;v_qty numeric;v_cost numeric;k text;
begin
 perform erp.require_owner_admin();
 select * into r from erp.migration_staging_rows where id=p_row_id and batch_id=p_batch_id and entity_type='UNINVOICED_RECEIPT';
 if r.id is null then raise exception 'Baris penerimaan tidak ditemukan'; end if;
 j:=r.normalized_payload;
 foreach k in array array['receipt_number','receipt_line_number','receipt_date','supplier_code','material_sku','location_code','qty','unit_cost','control_key'] loop
   if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi',k;end if;
 end loop;
 v_number:=btrim(j->>'receipt_number');v_line:=btrim(j->>'receipt_line_number');v_key:=nullif(btrim(j->>'opening_source_key'),'');
 if length(v_number)>120 or length(v_line)>60 or length(v_key)>120 then raise exception 'receipt_number: identitas sumber terlalu panjang';end if;
 if j->>'receipt_date' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' or (j->>'receipt_date')::date::text<>j->>'receipt_date' then
   raise exception 'receipt_date: gunakan YYYY-MM-DD';end if;
 v_date:=(j->>'receipt_date')::date;
 select (cutover_at at time zone 'Asia/Jakarta')::date into v_cutover from erp.migration_batches where id=p_batch_id;
 if v_date>v_cutover then raise exception 'receipt_date: penerimaan melewati cutover';end if;
 v_qty:=(j->>'qty')::numeric;v_cost:=(j->>'unit_cost')::numeric;
 if v_qty::text in('NaN','Infinity','-Infinity') or v_cost::text in('NaN','Infinity','-Infinity')
   or v_qty<=0 or v_cost<0 or v_qty<>round(v_qty,6) or v_cost<>round(v_cost,6) then
   raise exception 'qty: jumlah positif dan biaya nonnegatif harus tepat, maksimal enam desimal';end if;
 perform v_qty::numeric(18,6);perform v_cost::numeric(18,6);

 if v_key is not null then
  if (select count(*) from erp.migration_staging_rows where batch_id=p_batch_id
   and entity_type in('MATERIAL_ROLL','OPENING_BALANCE_ITEM') and normalized_payload->>'opening_source_key'=v_key)<>1 then
   raise exception 'opening_source_key: harus menunjuk tepat satu rincian stok dalam batch ini';end if;
  select * into s from erp.migration_staging_rows where batch_id=p_batch_id
   and entity_type in('MATERIAL_ROLL','OPENING_BALANCE_ITEM') and normalized_payload->>'opening_source_key'=v_key;
  if s.validation_status<>'VALID' or (s.entity_type='OPENING_BALANCE_ITEM' and upper(s.normalized_payload->>'balance_type')<>'MATERIAL') then
   raise exception 'opening_source_key: sumber harus rincian stok bahan yang valid';end if;
  if s.normalized_payload->>'material_sku' is distinct from j->>'material_sku'
   or s.normalized_payload->>'location_code' is distinct from j->>'location_code'
   or (s.normalized_payload->>'unit_cost')::numeric is distinct from v_cost then
   raise exception 'opening_source_key: bahan, gudang, dan biaya harus sama dengan stok awal';end if;
  if nullif(s.normalized_payload->>'supplier_code','') is not null and s.normalized_payload->>'supplier_code'<>j->>'supplier_code' then
   raise exception 'supplier_code: supplier berbeda dengan stok asal';end if;
 end if;
 if v_qty is distinct from coalesce((s.normalized_payload->>case when s.entity_type='MATERIAL_ROLL' then 'opening_qty' else 'qty' end)::numeric,0)
   +coalesce((select sum((x.normalized_payload->>'qty')::numeric) from erp.migration_staging_rows x where x.batch_id=p_batch_id
     and x.entity_type='OPENING_COST_ORIGIN' and x.validation_status='VALID'
     and x.normalized_payload->>'supplier_code'=j->>'supplier_code'
     and lower(btrim(x.normalized_payload->>'receipt_number'))=lower(v_number)
     and lower(btrim(x.normalized_payload->>'receipt_line_number'))=lower(v_line)),0) then
  raise exception 'opening_source_key: jumlah belum ditagih harus tepat sama dengan sisa bahan + seluruh asal biaya yang sudah terpakai';end if;
 if not exists(select 1 from erp.materials where material_sku=j->>'material_sku' and is_active)
   and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='MATERIAL' and validation_status='VALID' and normalized_payload->>'material_sku'=j->>'material_sku') then
  raise exception 'material_sku: bahan aktif tidak ditemukan';end if;
 if not exists(select 1 from erp.locations where location_code=j->>'location_code' and is_active and location_type='RAW_MATERIAL_WAREHOUSE')
   and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='LOCATION' and validation_status='VALID' and normalized_payload->>'location_code'=j->>'location_code' and normalized_payload->>'location_type'='RAW_MATERIAL_WAREHOUSE') then
  raise exception 'location_code: gudang bahan aktif tidak ditemukan';end if;
 select id into v_party from erp.suppliers where supplier_code=j->>'supplier_code' and is_active;
 if v_party is null and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='SUPPLIER'
   and validation_status='VALID' and normalized_payload->>'supplier_code'=j->>'supplier_code'
   and coalesce(nullif(normalized_payload->>'is_active','')::boolean,true)) then raise exception 'supplier_code: supplier aktif tidak ditemukan';end if;
 if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch_id and x.entity_type='UNINVOICED_RECEIPT' and x.id<>r.id
   and (x.normalized_payload->>'opening_source_key'=v_key or (
     x.normalized_payload->>'supplier_code'=j->>'supplier_code' and lower(btrim(x.normalized_payload->>'receipt_number'))=lower(v_number)
     and (lower(btrim(x.normalized_payload->>'receipt_line_number'))=lower(v_line)
       or x.normalized_payload->>'receipt_date'<>j->>'receipt_date' or x.normalized_payload->>'location_code'<>j->>'location_code'
       or x.normalized_payload->>'control_key'<>j->>'control_key')))) then
   raise exception 'receipt_number: sumber ganda atau rincian dokumen tidak konsisten';end if;
 if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch_id and x.entity_type='OPENING_BALANCE_ITEM'
   and upper(x.normalized_payload->>'balance_type')='SUPPLIER_PAYABLE' and x.normalized_payload->>'supplier_code'=j->>'supplier_code'
   and (nullif(btrim(x.normalized_payload->>'document_number'),'') is null or lower(btrim(x.normalized_payload->>'document_number'))=lower(v_number))) then
   raise exception 'receipt_number: jangan campur kewajiban belum ditagih dengan ringkasan utang atau dokumen asal yang sama';end if;
 if v_party is not null then
   if exists(select 1 from erp.initial_import_receipt_headers where supplier_id=v_party and lower(btrim(receipt_number))=lower(v_number))
      or exists(select 1 from erp.material_purchase_headers where supplier_id=v_party and lower(btrim(purchase_number))=lower(v_number)) then
     raise exception 'receipt_number: penerimaan sudah tercatat, termasuk pada jalur pembelian';end if;
   if exists(select 1 from erp.initial_import_financial_sources where balance_type='SUPPLIER_PAYABLE' and party_id=v_party
     and (source_mode='SUMMARY' or lower(btrim(document_number))=lower(v_number)))
     or exists(select 1 from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id
       where i.balance_type='SUPPLIER_PAYABLE' and i.supplier_id=v_party and h.status='POSTED'
       and not exists(select 1 from erp.initial_import_financial_sources f where f.opening_item_id=i.id)) then
     raise exception 'receipt_number: kewajiban supplier sudah memiliki opening yang tumpang tindih atau belum terurai';end if;
 end if;
end;$function$;
revoke all on function erp.check_initial_import_receipt_v1(uuid,uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.validate_initial_import_receipts_v1(p_batch_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare r record;
begin
 perform erp.require_owner_admin();
 for r in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type in('MATERIAL_ROLL','OPENING_BALANCE_ITEM')
   and nullif(btrim(normalized_payload->>'opening_source_key'),'') is not null loop
   if length(r.normalized_payload->>'opening_source_key')>120
     or (r.entity_type='OPENING_BALANCE_ITEM' and upper(r.normalized_payload->>'balance_type') not in('MATERIAL','FINISHED_GOODS','WIP','BS'))
     or exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.id<>r.id
       and s.entity_type in('MATERIAL_ROLL','OPENING_BALANCE_ITEM')
       and s.normalized_payload->>'opening_source_key'=r.normalized_payload->>'opening_source_key') then
     update erp.migration_staging_rows set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array('opening_source_key: kode unik maksimal 120 karakter hanya untuk stok/WIP/BS') where id=r.id;
   end if;
 end loop;
 for r in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='UNINVOICED_RECEIPT' order by source_row_no loop
   begin perform erp.check_initial_import_receipt_v1(p_batch_id,r.id);
   exception when others then update erp.migration_staging_rows set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array(sqlerrm) where id=r.id;
   end;
 end loop;
end;$function$;
revoke all on function erp.validate_initial_import_receipts_v1(uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.link_initial_import_stock_source_v1(p_batch_id uuid,p_row_id uuid,p_item_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare v_key text;
begin
 perform erp.require_owner_admin();
 select nullif(btrim(normalized_payload->>'opening_source_key'),'') into v_key from erp.migration_staging_rows where id=p_row_id and batch_id=p_batch_id;
 if v_key is null then return;end if;
 if not exists(select 1 from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id
   where i.id=p_item_id and i.balance_type in('MATERIAL','FINISHED_GOODS','WIP','BS') and h.status='DRAFT' and h.migration_batch_id=p_batch_id) then
   raise exception 'opening_source_key hanya untuk rincian stok/WIP/BS';end if;
 insert into erp.initial_import_opening_stock_sources(source_row_id,batch_id,source_key,opening_item_id) values(p_row_id,p_batch_id,v_key,p_item_id);
end;$function$;
revoke all on function erp.link_initial_import_stock_source_v1(uuid,uuid,uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.apply_initial_import_receipts_v1(p_batch_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare b erp.migration_batches%rowtype;r record;j jsonb;v_supplier uuid;v_purchase uuid;v_item uuid;
 v_opening erp.opening_balance_items%rowtype;v_cutover date;v_material uuid;v_location uuid;v_origin record;v_target uuid;
begin
 perform erp.require_owner_admin();
 select * into b from erp.migration_batches where id=p_batch_id for update;
 if b.status not in('READY','POSTING') or exists(select 1 from erp.migration_staging_rows where batch_id=b.id and validation_status<>'VALID') then
   raise exception 'Penerimaan awal memerlukan batch valid terbaru';end if;
 v_cutover:=(b.cutover_at at time zone 'Asia/Jakarta')::date;
 -- Same lock as financial opening preparation, plus normalized receipt identity.
 for r in select distinct s.id supplier_id from erp.migration_staging_rows x join erp.suppliers s on s.supplier_code=x.normalized_payload->>'supplier_code'
   where x.batch_id=b.id and x.entity_type='UNINVOICED_RECEIPT' order by s.id loop
   perform pg_advisory_xact_lock(hashtextextended('INITIAL_OPENING_FINANCIAL:SUPPLIER_PAYABLE:'||r.supplier_id::text,0));
 end loop;
 for r in select x.*,s.id supplier_id from erp.migration_staging_rows x join erp.suppliers s on s.supplier_code=x.normalized_payload->>'supplier_code'
   where x.batch_id=b.id and x.entity_type='UNINVOICED_RECEIPT' order by s.id,lower(btrim(x.normalized_payload->>'receipt_number')),x.source_row_no loop
   perform pg_advisory_xact_lock(hashtextextended('INITIAL_RECEIPT:'||r.supplier_id::text||':'||lower(btrim(r.normalized_payload->>'receipt_number')),0));
   perform erp.check_initial_import_receipt_v1(b.id,r.id);
 end loop;
 for r in select * from erp.migration_staging_rows where batch_id=b.id and entity_type='UNINVOICED_RECEIPT' order by source_row_no loop
   j:=r.normalized_payload;
   select id into strict v_supplier from erp.suppliers where supplier_code=j->>'supplier_code' and is_active;
   select i.* into v_opening from erp.initial_import_opening_stock_sources s
     join erp.opening_balance_items i on i.id=s.opening_item_id join erp.opening_balance_headers h on h.id=i.opening_id
     where s.batch_id=b.id and s.source_key=j->>'opening_source_key' and h.status='POSTED' for update of i;
   if v_opening.id is not null and (v_opening.unit_cost_snapshot<>(j->>'unit_cost')::numeric
     or not exists(select 1 from erp.material_stock_movements m where m.source_type='OPENING_BALANCE_ITEM' and m.source_id=v_opening.id
       and m.movement_type='OPENING' and m.qty_signed=v_opening.qty and m.material_id=v_opening.material_id
       and m.location_id=v_opening.location_id and m.roll_id is not distinct from v_opening.roll_id)) then
     raise exception 'Asal fisik penerimaan tidak cocok dengan stok awal yang dibukukan';end if;
   select id into strict v_material from erp.materials where material_sku=j->>'material_sku' and is_active;
   select id into strict v_location from erp.locations where location_code=j->>'location_code' and is_active and location_type='RAW_MATERIAL_WAREHOUSE';
   select purchase_id into v_purchase from erp.initial_import_receipt_headers where batch_id=b.id and supplier_id=v_supplier
     and lower(btrim(receipt_number))=lower(btrim(j->>'receipt_number'));
   if v_purchase is null then
     v_purchase:=gen_random_uuid();
     insert into erp.material_purchase_headers(id,purchase_number,supplier_id,physical_at,location_id,notes,created_by)
       values(v_purchase,'OPEN-'||v_purchase::text,v_supplier,b.cutover_at,v_location,
         'Saldo awal penerimaan '||(j->>'receipt_number')||' tanggal '||(j->>'receipt_date'),erp.current_app_user_id());
     insert into erp.initial_import_receipt_headers(purchase_id,batch_id,supplier_id,receipt_number,receipt_date,cutover_date)
       values(v_purchase,b.id,v_supplier,j->>'receipt_number',(j->>'receipt_date')::date,v_cutover);
   end if;
   insert into erp.material_purchase_items(purchase_id,material_id,qty,unit_price,price_state,price_source,notes)
     values(v_purchase,v_material,(j->>'qty')::numeric,(j->>'unit_cost')::numeric,'ESTIMATED','MANUAL_ESTIMATE',j->>'notes') returning id into v_item;
   insert into erp.initial_import_receipt_lines(purchase_item_id,purchase_id,source_row_id,opening_item_id,receipt_line_number)
     values(v_item,v_purchase,r.id,v_opening.id,j->>'receipt_line_number');

   for v_origin in select * from erp.migration_staging_rows x where x.batch_id=b.id and x.entity_type='OPENING_COST_ORIGIN'
     and x.normalized_payload->>'supplier_code'=j->>'supplier_code'
     and lower(btrim(x.normalized_payload->>'receipt_number'))=lower(btrim(j->>'receipt_number'))
     and lower(btrim(x.normalized_payload->>'receipt_line_number'))=lower(btrim(j->>'receipt_line_number')) loop
    select opening_item_id into strict v_target from erp.initial_import_opening_stock_sources where batch_id=b.id and source_key=v_origin.normalized_payload->>'target_source_key';
    insert into erp.initial_import_cost_origins(source_row_id,purchase_item_id,opening_item_id,material_qty,unit_cost_snapshot)
     values(v_origin.id,v_item,v_target,(v_origin.normalized_payload->>'qty')::numeric,(j->>'unit_cost')::numeric);
    update erp.migration_staging_rows set posted_entity_type='OPENING_COST_ORIGIN',posted_entity_id=v_origin.id,posted_at=statement_timestamp(),updated_at=statement_timestamp() where id=v_origin.id;
   end loop;
   update erp.migration_staging_rows set posted_entity_type='OPENING_UNINVOICED_RECEIPT_ITEM',posted_entity_id=v_item,
     posted_at=statement_timestamp(),updated_at=statement_timestamp() where id=r.id;
 end loop;
 for r in select purchase_id from erp.initial_import_receipt_headers where batch_id=b.id order by purchase_id loop
   update erp.material_purchase_headers set status='POSTED' where id=r.purchase_id;
 end loop;
end;$function$;
revoke all on function erp.apply_initial_import_receipts_v1(uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.guard_initial_import_receipt_header_v1()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
begin
 if tg_op<>'INSERT' and exists(select 1 from erp.initial_import_receipt_headers where purchase_id=old.id) then
   if tg_op='DELETE' then raise exception 'Penerimaan saldo awal bersifat tetap; gunakan koreksi tertaut';end if;
   if old.status='POSTED' and (new.status<>old.status or new.supplier_id is distinct from old.supplier_id
     or new.physical_at<>old.physical_at or new.location_id is distinct from old.location_id or new.purchase_number<>old.purchase_number) then
     raise exception 'Penerimaan saldo awal bersifat tetap; gunakan koreksi tertaut';end if;
 elsif tg_op<>'DELETE' and new.supplier_id is not null then
   perform pg_advisory_xact_lock(hashtextextended('INITIAL_RECEIPT:'||new.supplier_id::text||':'||lower(btrim(new.purchase_number)),0));
   if exists(select 1 from erp.initial_import_receipt_headers where supplier_id=new.supplier_id
     and lower(btrim(receipt_number))=lower(btrim(new.purchase_number))) then
     raise exception 'receipt_number: penerimaan ini sudah diimpor sebagai stok awal';end if;
 end if;
 if tg_op='DELETE' then return old;end if;return new;
end;$function$;
revoke all on function erp.guard_initial_import_receipt_header_v1() from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.approve_payroll(p_payroll_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  p erp.payroll_settlements%rowtype;
  v_manual_reimburse numeric(20,2) := 0;
  v_extra_accrual numeric(20,2) := 0;
  v_negative_manual numeric(20,2) := 0;
  v_attendance numeric(20,2) := 0;
begin
  perform erp.require_owner_admin();
  perform erp.recalculate_payroll(p_payroll_id);
  select * into p from erp.payroll_settlements where id=p_payroll_id for update;
  if p.id is null or p.status not in ('CALCULATED','REVIEW') then
    raise exception 'Payroll must be CALCULATED/REVIEW before approval, current status %',p.status;
  end if;

  perform erp.check_opening_cash_advance_payroll_v1(p.id);
  perform erp._cp3_lock_business_period(p.period_start,p.period_end);
  if exists(
    select 1 from erp.attendance_hpp_pools hp
    where hp.status='ACTIVE'
      and hp.period_start=p.period_start
      and hp.period_end=p.period_end
  ) then
    raise exception 'Attendance HPP pool for payroll period % through % is already ACTIVE. Cancel the ACTIVE pool first before approving this payroll.',p.period_start,p.period_end;
  end if;
  if exists (
    select 1 from erp.journal_entries je
    where je.source_id=p.id
      and je.source_type in ('PAYROLL_ATTENDANCE_ACCRUAL','PAYROLL_EXTRA_ACCRUAL','PAYROLL_MANUAL_REDUCTION')
      and je.status='POSTED'
  ) then
    raise exception 'Payroll approval accrual already exists; inspect duplicate/ambiguous approval state';
  end if;

  select coalesce(sum(amount),0) into v_manual_reimburse
  from erp.payroll_reimbursements
  where payroll_id=p.id and source_type<>'ACCESSORY_BOM';
  v_attendance:=round(coalesce(p.attendance_total,0),2);
  v_extra_accrual:=round(v_manual_reimburse+greatest(p.manual_adjustment,0),2);
  v_negative_manual:=round(greatest(-p.manual_adjustment,0),2);

  update erp.payroll_settlements set status='APPROVED',updated_at=statement_timestamp() where id=p.id;

  if v_attendance>0 then
    perform erp.post_journal(
      'PAYROLL_ATTENDANCE_ACCRUAL',p.id,p.period_end,
      'Attendance payroll approved into unassigned WIP',
      jsonb_build_array(
        jsonb_build_object('mapping_key','WIP','debit',v_attendance,'credit',0,'contractor_id',p.contractor_id,
                           'description','Approved attendance cost awaiting SELESAI_DIJAHIT allocation'),
        jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',v_attendance,'contractor_id',p.contractor_id,
                           'description','Approved attendance payable')
      )
    );
  end if;
  if v_extra_accrual>0 then
    perform erp.post_journal(
      'PAYROLL_EXTRA_ACCRUAL',p.id,p.period_end,
      'Approved manual reimbursement/manual payroll accrual',
      jsonb_build_array(
        jsonb_build_object('mapping_key','LABOR_COST','debit',v_extra_accrual,'credit',0,'contractor_id',p.contractor_id),
        jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',v_extra_accrual,'contractor_id',p.contractor_id)
      )
    );
  end if;
  if v_negative_manual>0 then
    perform erp.post_journal(
      'PAYROLL_MANUAL_REDUCTION',p.id,p.period_end,
      'Approved negative manual payroll adjustment',
      jsonb_build_array(
        jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',v_negative_manual,'credit',0,'contractor_id',p.contractor_id),
        jsonb_build_object('mapping_key','LABOR_COST','debit',0,'credit',v_negative_manual,'contractor_id',p.contractor_id)
      )
    );
  end if;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values(
    'payroll_settlements',p.id,'POST',
    jsonb_build_object('lifecycle_action','APPROVE','attendance_accrual',v_attendance,
                       'extra_accrual',v_extra_accrual,'manual_reduction',v_negative_manual),
    erp.current_app_user_id(),'Payroll approved; cost recognition completed before payment'
  );
end;
$function$;
CREATE OR REPLACE FUNCTION erp.post_opening_subledger_settlement(p_settlement_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
DECLARE s erp.opening_subledger_settlements%ROWTYPE;b erp.opening_subledger_balances%ROWTYPE;v_cash uuid;v_remaining numeric(20,2);v_lines jsonb;
BEGIN PERFORM erp.require_owner_admin();SELECT * INTO s FROM erp.opening_subledger_settlements WHERE id=p_settlement_id FOR UPDATE;IF s.id IS NULL OR s.status<>'DRAFT' THEN RAISE EXCEPTION 'Opening subledger settlement must be DRAFT';END IF;SELECT * INTO b FROM erp.opening_subledger_balances WHERE id=s.balance_id FOR UPDATE;IF b.id IS NULL OR b.status='SETTLED' THEN RAISE EXCEPTION 'Opening subledger balance is not open';END IF;v_remaining:=b.original_amount-b.settled_amount;
IF erp.opening_cash_advance_state_v1(b.id) IS NOT NULL THEN
 IF erp._cp3_business_date(s.physical_at)<(erp.opening_cash_advance_state_v1(b.id)->>'cutover_date')::date THEN
   RAISE EXCEPTION 'Pengembalian kasbon harus sejak tanggal saldo awal';END IF;
 v_remaining:=(erp.opening_cash_advance_state_v1(b.id)->>'available_amount')::numeric;
END IF;IF s.amount>v_remaining THEN RAISE EXCEPTION 'Settlement exceeds opening outstanding. Remaining %, requested %',v_remaining,s.amount;END IF;v_cash:=erp.initial_prepayment_funding_v1(s.id,b.party_type,coalesce(b.supplier_id,b.customer_id,b.vendor_id),s.amount,erp._cp3_business_date(s.physical_at),
      (select h.opening_date from erp.opening_balance_items oi join erp.opening_balance_headers h on h.id=oi.opening_id where oi.id=b.opening_item_id));
IF v_cash IS NULL THEN SELECT coa_account_id INTO v_cash FROM erp.cash_accounts WHERE id=s.cash_account_id AND is_active=true;END IF;IF v_cash IS NULL THEN RAISE EXCEPTION 'Active cash/bank account is required';END IF;
IF b.direction='RECEIVABLE' AND b.party_type='CUSTOMER' THEN v_lines:=jsonb_build_array(jsonb_build_object('account_id',v_cash,'debit',s.amount,'credit',0,'customer_id',b.customer_id),jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',s.amount,'customer_id',b.customer_id));ELSIF b.direction='RECEIVABLE' AND b.party_type='CONTRACTOR' THEN v_lines:=jsonb_build_array(jsonb_build_object('account_id',v_cash,'debit',s.amount,'credit',0,'contractor_id',b.contractor_id),jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',0,'credit',s.amount,'contractor_id',b.contractor_id));ELSIF b.direction='PAYABLE' AND b.party_type='SUPPLIER' THEN v_lines:=jsonb_build_array(jsonb_build_object('mapping_key','AP_SUPPLIER','debit',s.amount,'credit',0),jsonb_build_object('account_id',v_cash,'debit',0,'credit',s.amount));ELSIF b.direction='PAYABLE' AND b.party_type='VENDOR' THEN v_lines:=jsonb_build_array(jsonb_build_object('mapping_key','AP_VENDOR','debit',s.amount,'credit',0,'vendor_id',b.vendor_id),jsonb_build_object('account_id',v_cash,'debit',0,'credit',s.amount,'vendor_id',b.vendor_id));ELSIF b.direction='PAYABLE' AND b.party_type='CONTRACTOR' THEN v_lines:=jsonb_build_array(jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',s.amount,'credit',0,'contractor_id',b.contractor_id),jsonb_build_object('account_id',v_cash,'debit',0,'credit',s.amount,'contractor_id',b.contractor_id));ELSE RAISE EXCEPTION 'Unsupported opening subledger direction/party combination';END IF;
PERFORM erp.post_journal('OPENING_SUBLEDGER_SETTLEMENT',s.id,erp._cp3_business_date(s.physical_at),'Opening subledger settlement '||s.settlement_number,v_lines);UPDATE erp.opening_subledger_settlements SET status='POSTED',updated_at=statement_timestamp() WHERE id=s.id;UPDATE erp.opening_subledger_balances SET settled_amount=settled_amount+s.amount,status=CASE WHEN settled_amount+s.amount=original_amount THEN 'SETTLED' ELSE 'PARTIAL' END,updated_at=statement_timestamp() WHERE id=b.id;END;$function$;
CREATE OR REPLACE FUNCTION erp.post_payroll_payment(p_payroll_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  p erp.payroll_settlements%rowtype;
  v_cash uuid;
  v_material_deduction numeric(20,2):=0;
  v_other_deduction numeric(20,2):=0;v_cash_advance numeric(20,2):=0;
  v_expected_attendance numeric(20,2):=0;
  v_actual_attendance numeric(20,2):=0;
  v_attendance_journal_count bigint:=0;
  r record;
begin
  perform erp.require_internal();
  select * into p from erp.payroll_settlements where id=p_payroll_id for update;
  if p.id is null or p.status<>'APPROVED' then raise exception 'Payroll must be APPROVED'; end if;
  perform erp.check_opening_cash_advance_payroll_v1(p.id);
  perform erp._cp3_lock_business_period(p.period_start,p.period_end);
  if p.net_payable<0 then raise exception 'Payroll net payable cannot be negative; carry deductions forward instead'; end if;
  if p.payment_date is null then raise exception 'Payroll payment date is required'; end if;
  if p.payment_date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date then raise exception 'Tanggal pembayaran payroll berada di masa depan'; end if;
  if p.net_payable>0 then
    select coa_account_id into v_cash from erp.cash_accounts where id=p.payment_cash_account_id and is_active=true;
    if v_cash is null then raise exception 'Active payroll cash/bank account is required when cash payment is positive'; end if;
  end if;

  v_expected_attendance:=round(coalesce(p.attendance_total,0),2);
  select count(distinct je.id),coalesce(sum(jl.debit),0)
    into v_attendance_journal_count,v_actual_attendance
  from erp.journal_entries je
  join erp.journal_lines jl on jl.journal_entry_id=je.id
  where je.source_type='PAYROLL_ATTENDANCE_ACCRUAL' and je.source_id=p.id and je.status='POSTED'
    and jl.account_id=erp.account_id('WIP') and jl.debit>0;
  if (v_expected_attendance=0 and v_attendance_journal_count<>0)
     or (v_expected_attendance>0 and (v_attendance_journal_count<>1 or round(v_actual_attendance,2) is distinct from v_expected_attendance)) then
    raise exception 'PAYROLL_APPROVAL_ACCRUAL_MISSING_OR_MISMATCH: expected attendance %, journal count %, WIP debit %',
      v_expected_attendance,v_attendance_journal_count,round(v_actual_attendance,2);
  end if;

  select coalesce(sum(amount),0) into v_material_deduction
  from erp.payroll_deductions where payroll_id=p.id and deduction_type='MATERIAL_KASBON';
  select coalesce(sum(amount),0) into v_other_deduction
  from erp.payroll_deductions where payroll_id=p.id and deduction_type not in('MATERIAL_KASBON','CASH_ADVANCE');
  if v_material_deduction>0 then
    perform erp.post_journal('PAYROLL_MATERIAL_DEDUCTION',p.id,p.payment_date,
      'Physical material/accessory purchase deduction',jsonb_build_array(
        jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',v_material_deduction,'credit',0,'contractor_id',p.contractor_id),
        jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',0,'credit',v_material_deduction,'contractor_id',p.contractor_id)));
  end if;
  select coalesce(sum(amount),0) into v_cash_advance from erp.payroll_deductions
    where payroll_id=p.id and deduction_type='CASH_ADVANCE';
  if v_cash_advance>0 then
    perform erp.post_journal('PAYROLL_CASH_ADVANCE_DEDUCTION',p.id,p.payment_date,'Pelunasan kasbon tunai melalui payroll',jsonb_build_array(
      jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',v_cash_advance,'credit',0,'contractor_id',p.contractor_id),
      jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',0,'credit',v_cash_advance,'contractor_id',p.contractor_id)));
  end if;
  if v_other_deduction>0 then
    perform erp.post_journal('PAYROLL_OTHER_DEDUCTION',p.id,p.payment_date,
      'BS/penalty/other payroll deduction',jsonb_build_array(
        jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',v_other_deduction,'credit',0,'contractor_id',p.contractor_id),
        jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',v_other_deduction,'contractor_id',p.contractor_id)));
  end if;
  if p.net_payable>0 then
    perform erp.post_journal('PAYROLL_PAYMENT',p.id,p.payment_date,'Mandor payroll payment',jsonb_build_array(
      jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',p.net_payable,'credit',0,'contractor_id',p.contractor_id),
      jsonb_build_object('account_id',v_cash,'debit',0,'credit',p.net_payable,'contractor_id',p.contractor_id)));
  end if;

  update erp.payroll_settlements set status='PAID',settled_at=statement_timestamp(),updated_at=statement_timestamp() where id=p.id;
  update erp.opening_subledger_balances b set settled_amount=b.settled_amount+x.amount,
    status=case when b.settled_amount+x.amount=b.original_amount then 'SETTLED' else 'PARTIAL' end,updated_at=statement_timestamp()
  from(select opening_cash_advance_balance_id id,sum(amount) amount from erp.payroll_deductions
    where payroll_id=p.id and deduction_type='CASH_ADVANCE' group by opening_cash_advance_balance_id) x where b.id=x.id;

  for r in select distinct pd.contractor_issue_item_id id from erp.payroll_deductions pd
           where pd.payroll_id=p.id and pd.contractor_issue_item_id is not null
  loop perform erp.refresh_contractor_issue_payroll_status(r.id); end loop;
  update erp.contractor_accessory_reimbursement_entitlements e set payroll_status='SETTLED'
  where e.id in(select pr.source_id from erp.payroll_reimbursements pr
                where pr.payroll_id=p.id and pr.source_type='ACCESSORY_BOM' and pr.source_id is not null);
  for r in
    select distinct bc.id as bs_case_id from erp.bs_cases bc
    where exists(select 1 from erp.payroll_work_items pwi where pwi.payroll_id=p.id and pwi.po_id=bc.po_id)
       or exists(select 1 from erp.payroll_work_items pwi join erp.rework_component_lines rcl on rcl.id=pwi.source_id
                 join erp.bs_case_components bcc on bcc.id=rcl.bs_case_component_id
                 where pwi.payroll_id=p.id and bcc.bs_case_id=bc.id)
  loop perform erp.rebuild_bs_component_counters(r.bs_case_id); end loop;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('payroll_settlements',p.id,'POST',
    jsonb_build_object('lifecycle_action','PAY','payment_settlement_only',true,'attendance_accrual_created_at_payment',false),
    erp.current_app_user_id(),'Payroll payment settled approved payable without recognizing attendance cost again');
end;
$function$;
CREATE OR REPLACE FUNCTION erp.reverse_paid_payroll(p_payroll_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  p erp.payroll_settlements%rowtype;
  r record;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Payroll reversal reason is required'; end if;
  select * into p from erp.payroll_settlements where id=p_payroll_id for update;
  if p.id is null then raise exception 'Payroll not found'; end if;
  if p.status='REVERSED' then return; end if;
  if p.status<>'PAID' then raise exception 'Only PAID payroll uses reverse_paid_payroll; unpaid payroll uses cancel_unpaid_payroll'; end if;
  perform 1 from erp.opening_subledger_balances b where exists(select 1 from erp.payroll_deductions d
    where d.payroll_id=p.id and d.opening_cash_advance_balance_id=b.id) order by b.id for update;
  perform erp._cp3_lock_business_period(p.period_start,p.period_end);
  if exists(
    select 1 from erp.attendance_hpp_pool_sources s
    join erp.attendance_hpp_pools hp on hp.id=s.pool_id
    where s.payroll_id=p.id and hp.status='ACTIVE'
  ) then
    raise exception 'PAYROLL_CONSUMED_BY_ACTIVE_HPP_POOL: cancel the active attendance HPP pool first';
  end if;

  for r in
    select je.id from erp.journal_entries je
    where je.source_id=p.id
      and je.source_type in ('PAYROLL_ATTENDANCE_ACCRUAL','PAYROLL_EXTRA_ACCRUAL','PAYROLL_MANUAL_REDUCTION',
                             'PAYROLL_MATERIAL_DEDUCTION','PAYROLL_OTHER_DEDUCTION','PAYROLL_PAYMENT','PAYROLL_CASH_ADVANCE_DEDUCTION')
      and je.status='POSTED'
    order by je.posting_at desc,je.id desc
  loop perform erp._cp3_r4_reverse_journal_internal(r.id,p_reason); end loop;

  update erp.payroll_settlements set status='REVERSED',settled_at=null,updated_at=statement_timestamp() where id=p.id;
  update erp.opening_subledger_balances b set settled_amount=b.settled_amount-x.amount,
    status=case when b.settled_amount-x.amount=b.original_amount then 'SETTLED' when b.settled_amount-x.amount>0 then 'PARTIAL' else 'OPEN' end,
    updated_at=statement_timestamp()
  from(select opening_cash_advance_balance_id id,sum(amount) amount from erp.payroll_deductions
    where payroll_id=p.id and deduction_type='CASH_ADVANCE' group by opening_cash_advance_balance_id) x where b.id=x.id;

  for r in select distinct pd.contractor_issue_item_id id from erp.payroll_deductions pd
           where pd.payroll_id=p.id and pd.contractor_issue_item_id is not null
  loop perform erp.refresh_contractor_issue_payroll_status(r.id); end loop;
  for r in select distinct pr.source_id id from erp.payroll_reimbursements pr
           where pr.payroll_id=p.id and pr.source_type='ACCESSORY_BOM' and pr.source_id is not null
  loop
    update erp.contractor_accessory_reimbursement_entitlements e
    set payroll_status=case
      when exists(select 1 from erp.payroll_reimbursements pr2 join erp.payroll_settlements ps2 on ps2.id=pr2.payroll_id
                  where pr2.source_type='ACCESSORY_BOM' and pr2.source_id=e.id and ps2.status='PAID') then 'SETTLED'
      when exists(select 1 from erp.payroll_reimbursements pr2 join erp.payroll_settlements ps2 on ps2.id=pr2.payroll_id
                  where pr2.source_type='ACCESSORY_BOM' and pr2.source_id=e.id and ps2.status<>'REVERSED') then 'ALLOCATED'
      else 'UNALLOCATED' end
    where e.id=r.id;
  end loop;
  for r in
    select distinct bc.id as bs_case_id from erp.bs_cases bc
    where exists(select 1 from erp.payroll_work_items pwi where pwi.payroll_id=p.id and pwi.po_id=bc.po_id)
       or exists(select 1 from erp.payroll_work_items pwi join erp.rework_component_lines rcl on rcl.id=pwi.source_id
                 join erp.bs_case_components bcc on bcc.id=rcl.bs_case_component_id
                 where pwi.payroll_id=p.id and bcc.bs_case_id=bc.id)
  loop perform erp.rebuild_bs_component_counters(r.bs_case_id); end loop;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('payroll_settlements',p.id,'REVERSE_PAID',jsonb_build_object('previous_status','PAID'),erp.current_app_user_id(),p_reason);
end;
$function$;
CREATE OR REPLACE FUNCTION erp.guard_opening_cash_advance_deduction_v1()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path TO '' AS $function$
declare p erp.payroll_settlements%rowtype;b erp.opening_subledger_balances%rowtype;
 v_reserved numeric;v_earnings numeric;v_deductions numeric;v_id uuid;v_date date;
begin
 if TG_OP='DELETE' then
   if old.opening_cash_advance_balance_id is null then return old;end if;
   v_id:=old.payroll_id;
 else
   if new.opening_cash_advance_balance_id is null and new.deduction_type<>'CASH_ADVANCE'
     and (TG_OP='INSERT' or old.opening_cash_advance_balance_id is null) then return new;end if;
   v_id:=new.payroll_id;
 end if;
 -- Only the controlled writer may reach the typed numeric column. Direct DML
 -- would coerce excess precision before this trigger could inspect the input.
 if current_user<>'postgres' then raise exception 'Alokasi kasbon tunai harus melalui command resmi';end if;
 perform erp.require_internal();
 if TG_OP='UPDATE' and (new.payroll_id<>old.payroll_id
   or new.opening_cash_advance_balance_id is distinct from old.opening_cash_advance_balance_id
   or new.deduction_type is distinct from old.deduction_type) then
   raise exception 'Sumber kasbon payroll tidak dapat dipindah; hapus alokasi draft lalu pilih sumber yang benar';end if;
 select * into p from erp.payroll_settlements where id=v_id for update;
 if p.id is null or p.status not in('DRAFT','CALCULATED','REVIEW') then
   raise exception 'Alokasi kasbon hanya boleh diedit pada payroll draft';end if;
 if TG_OP='DELETE' then
   perform 1 from erp.opening_subledger_balances where id=old.opening_cash_advance_balance_id for update;
   return old;
 end if;
 if new.deduction_type<>'CASH_ADVANCE' or new.opening_cash_advance_balance_id is null
   or new.contractor_issue_item_id is not null or new.bs_resolution_id is not null
   or new.amount is null or new.amount::text in('NaN','Infinity','-Infinity')
   or new.amount<=0 or new.amount<>round(new.amount,2) then
   raise exception 'Alokasi kasbon memerlukan sumber tunai dan nominal positif tepat dua desimal';end if;
 select * into b from erp.opening_subledger_balances where id=new.opening_cash_advance_balance_id for update;
 select s.cutover_date into v_date from erp.initial_import_financial_sources s
   join erp.opening_balance_headers h on h.migration_batch_id=s.batch_id and h.status='POSTED'
   where s.opening_item_id=b.opening_item_id and s.source_kind='CONTRACTOR_CASH_ADVANCE';
 if b.id is null or v_date is null or b.party_type<>'CONTRACTOR' or b.direction<>'RECEIVABLE'
   or b.contractor_id is distinct from p.contractor_id then
   raise exception 'Kasbon tunai harus berasal dari saldo awal sah milik mandor payroll ini';end if;
 select coalesce(sum(d.amount),0) into v_reserved from erp.payroll_deductions d
   join erp.payroll_settlements ps on ps.id=d.payroll_id
   where d.opening_cash_advance_balance_id=b.id and d.id<>new.id and ps.status not in('PAID','REVERSED');
 if new.amount>b.original_amount-b.settled_amount-v_reserved then
   raise exception 'Alokasi melebihi sisa kasbon yang belum dipakai payroll lain';end if;
 select coalesce((select sum(amount) from erp.payroll_work_items where payroll_id=p.id),0)
   +case when c.attendance_required then coalesce((select sum(amount) from erp.payroll_attendance_items where payroll_id=p.id),0) else 0 end
   +coalesce((select sum(amount) from erp.payroll_reimbursements where payroll_id=p.id),0)
   +p.manual_adjustment into v_earnings from erp.contractors c where c.id=p.contractor_id;
 select coalesce(sum(amount),0) into v_deductions from erp.payroll_deductions where payroll_id=p.id and id<>new.id;
 if new.amount>greatest(v_earnings-v_deductions,0) then
   raise exception 'Potongan kasbon melebihi pendapatan payroll; sisanya dibawa ke periode berikutnya';end if;
 return new;
end;$function$;
revoke all on function erp.guard_opening_cash_advance_deduction_v1() from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.check_opening_cash_advance_payroll_v1(p_payroll_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare p erp.payroll_settlements%rowtype;r record;v_reserved numeric;v_cash numeric;v_all numeric;
begin
 perform erp.require_internal();
 select * into p from erp.payroll_settlements where id=p_payroll_id for update;
 if p.id is null then raise exception 'Payroll tidak ditemukan';end if;
 select coalesce(sum(amount),0) into v_cash from erp.payroll_deductions
   where payroll_id=p.id and deduction_type='CASH_ADVANCE';
 if v_cash=0 then return;end if;
 select coalesce(sum(amount),0) into v_all from erp.payroll_deductions where payroll_id=p.id;
 if p.deduction_total<>v_all or p.net_payable<0 then
   raise exception 'Hitung ulang payroll: total potongan harus cocok dan tidak boleh melebihi pendapatan';end if;
 for r in select b.*,s.cutover_date,s.source_kind,s.party_id,
     (select sum(d.amount) from erp.payroll_deductions d where d.payroll_id=p.id and d.opening_cash_advance_balance_id=b.id) amount
   from erp.opening_subledger_balances b left join erp.initial_import_financial_sources s on s.opening_item_id=b.opening_item_id
   where exists(select 1 from erp.payroll_deductions d where d.payroll_id=p.id and d.opening_cash_advance_balance_id=b.id)
   order by b.id for update of b loop
   if r.source_kind is distinct from 'CONTRACTOR_CASH_ADVANCE' or r.contractor_id is distinct from p.contractor_id
     or r.party_id is distinct from p.contractor_id or r.party_type<>'CONTRACTOR' or r.direction<>'RECEIVABLE'
     or p.payment_date<r.cutover_date then raise exception 'Sumber mandor/tanggal pembayaran kasbon tidak cocok';end if;
   select coalesce(sum(d.amount),0) into v_reserved from erp.payroll_deductions d
     join erp.payroll_settlements ps on ps.id=d.payroll_id
     where d.opening_cash_advance_balance_id=r.id and d.payroll_id<>p.id and ps.status not in('PAID','REVERSED');
   if r.amount>r.original_amount-r.settled_amount-v_reserved then
     raise exception 'Saldo kasbon berubah atau sudah dialokasikan pada payroll lain';end if;
 end loop;
end;$function$;
revoke all on function erp.check_opening_cash_advance_payroll_v1(uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.guard_opening_cash_advance_balance_v1()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare v_reserved numeric;
begin
 if not exists(select 1 from erp.initial_import_financial_sources s
   where s.opening_item_id=new.opening_item_id and s.source_kind='CONTRACTOR_CASH_ADVANCE') then return new;end if;
 select coalesce(sum(d.amount),0) into v_reserved from erp.payroll_deductions d
   join erp.payroll_settlements p on p.id=d.payroll_id
   where d.opening_cash_advance_balance_id=new.id and p.status not in('PAID','REVERSED');
 if new.original_amount<new.settled_amount+v_reserved then
   raise exception 'Saldo kasbon tidak cukup setelah pembayaran dan alokasi payroll; lepaskan alokasi terlebih dahulu';end if;
 return new;
end;$function$;
revoke all on function erp.guard_opening_cash_advance_balance_v1() from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.set_opening_cash_advance_payroll_v1(
 p_balance_id uuid,p_payroll_id uuid,p_amount numeric,p_expected_version bigint)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare p erp.payroll_settlements%rowtype;v_id uuid;
begin
 perform erp.require_owner_admin();
 if p_amount is null or p_amount::text in('NaN','Infinity','-Infinity') or p_amount<0 or p_amount<>round(p_amount,2) then
   raise exception 'Nominal alokasi harus tepat dua desimal; gunakan nol untuk melepaskan alokasi';end if;
 select * into p from erp.payroll_settlements where id=p_payroll_id for update;
 if p.id is null or p.status not in('DRAFT','CALCULATED','REVIEW') then raise exception 'Payroll harus draft';end if;
 if p_expected_version is null or p.row_version<>p_expected_version then raise exception 'STALE_VERSION: payroll berubah';end if;
 if erp.opening_cash_advance_state_v1(p_balance_id) is null then raise exception 'Saldo kasbon tunai tidak ditemukan';end if;
 select id into v_id from erp.payroll_deductions where payroll_id=p.id and opening_cash_advance_balance_id=p_balance_id;
 if p_amount=0 then
   if v_id is null then raise exception 'Alokasi yang akan dilepas tidak ditemukan';end if;
   delete from erp.payroll_deductions where id=v_id;
 elsif v_id is null then
   insert into erp.payroll_deductions(payroll_id,deduction_type,opening_cash_advance_balance_id,amount,notes)
     values(p.id,'CASH_ADVANCE',p_balance_id,p_amount,'Alokasi kasbon tunai saldo awal') returning id into v_id;
 else update erp.payroll_deductions set amount=p_amount where id=v_id;
 end if;
 perform erp.recalculate_payroll(p.id);
 return v_id;
end;$function$;
revoke all on function erp.set_opening_cash_advance_payroll_v1(uuid,uuid,numeric,bigint) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.post_sales_payment(p_payment_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
 SET "TimeZone" TO 'UTC'
AS $function$
declare
  p erp.sales_payments%rowtype;
  h erp.sales_headers%rowtype;
  prior_payment erp.sales_payments%rowtype;
  prior_fact erp.sales_payment_posting_facts%rowtype;
  prior_reversal erp.sales_payment_reversal_facts%rowtype;
  j erp.journal_entries%rowtype;
  v_cash uuid;
  v_paid numeric(20,2);
  v_total numeric(20,2);
  v_amount numeric(20,2);
  v_journal uuid;
  v_snapshot jsonb;
  v_digest text;
begin
  perform erp.require_internal();
  select * into p from erp.sales_payments where id=p_payment_id for update;
  if p.id is null or p.status<>'DRAFT' then raise exception 'Sales payment must be DRAFT'; end if;
  v_amount:=round(p.amount,2)::numeric(20,2);
  if p.amount is distinct from v_amount or v_amount<=0 then
    raise exception 'Customer payment must be a positive exact two-decimal amount';
  end if;
  if erp._cp3_business_date(p.payment_date)>erp._cp3_business_date(statement_timestamp()) then
    raise exception 'Customer payment business date cannot be in the future';
  end if;
  select * into h from erp.sales_headers where id=p.sale_id for update;
  if h.status not in('POSTED','PARTIAL_PAID') then
    raise exception 'Sale must be posted and still unpaid before payment';
  end if;
  if p.replaces_payment_id is not null then
    if p.replaces_payment_id=p.id then raise exception 'Payment cannot replace itself'; end if;
    perform pg_advisory_xact_lock(hashtextextended('SALES_PAYMENT_REPLACEMENT|'||p.replaces_payment_id::text,0));
    select * into prior_payment from erp.sales_payments
    where id=p.replaces_payment_id for update;
    select * into prior_fact from erp.sales_payment_posting_facts
    where payment_id=p.replaces_payment_id;
    select * into prior_reversal from erp.sales_payment_reversal_facts
    where payment_id=p.replaces_payment_id;
    if prior_payment.id is null or prior_payment.status<>'REVERSED'
       or prior_fact.payment_id is null or prior_reversal.payment_id is null then
      raise exception 'Replacement requires one fully reversed posted payment';
    end if;
    if erp.initial_prepayment_account_v1(p.id) is not null or erp.initial_prepayment_account_v1(prior_payment.id) is not null then
      raise exception 'Uang muka dipindah melalui pembatalan lalu pemakaian baru dari workspace impor';end if;
    if prior_fact.customer_id is distinct from h.customer_id
       or prior_fact.sale_id=p.sale_id
       or prior_fact.amount is distinct from v_amount
       or prior_fact.cash_account_id is distinct from p.cash_account_id
       or prior_fact.payment_date is distinct from p.payment_date then
      raise exception 'Allocation replacement must preserve customer, amount, cash account and original payment clock while changing invoice';
    end if;
    if exists(select 1 from erp.sales_payment_posting_facts f
      where f.replaces_payment_id=p.replaces_payment_id) then
      raise exception 'Reversed payment already owns a linked replacement';
    end if;
  end if;
  select round(erp.sale_net_total(h.id),2)::numeric(20,2) into v_total;
  select round(coalesce(sum(round(sp.amount,2)),0),2)::numeric(20,2) into v_paid
  from erp.sales_payments sp where sp.sale_id=h.id and sp.status='POSTED';
  if v_paid>=v_total then
    raise exception 'Sale has no remaining receivable after returns/credits. Net sale %, already paid %',v_total,v_paid;
  end if;
  if v_paid+v_amount>v_total then
    raise exception 'Customer payment exceeds exact remaining receivable. Net sale %, already paid %, requested %',v_total,v_paid,v_amount;
  end if;
  v_cash:=erp.initial_prepayment_funding_v1(p.id,'CUSTOMER',h.customer_id,p.amount,erp._cp3_business_date(p.payment_date),erp._cp3_business_date(h.sale_date));
  if v_cash is null then
  select coa_account_id into v_cash from erp.cash_accounts where id=p.cash_account_id and is_active=true;
  end if;
  if v_cash is null then raise exception 'Active cash/bank account is required'; end if;
  v_journal:=erp.post_journal('SALES_PAYMENT',p_payment_id,
    case when p.replaces_payment_id is null then erp._cp3_business_date(p.payment_date)
      else prior_reversal.reversal_economic_date end,'Customer payment',jsonb_build_array(
    jsonb_build_object('account_id',v_cash,'debit',v_amount,'credit',0,'customer_id',h.customer_id),
    jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',v_amount,'customer_id',h.customer_id)));
  select * into strict j from erp.journal_entries where id=v_journal;
  if p.replaces_payment_id is not null and(
    j.economic_date is distinct from prior_reversal.reversal_economic_date
    or j.transaction_date is distinct from prior_reversal.reversal_transaction_date
    or j.posting_at<prior_reversal.reversal_posting_at) then
    raise exception 'PAYMENT_REPLACEMENT_DATE_CONSERVATION_REQUIRED';
  end if;
  v_snapshot:=to_jsonb(p)-'status';
  v_digest:=encode(extensions.digest(convert_to(jsonb_build_array(
    p.id,p.sale_id,h.customer_id,p.payment_number,p.payment_date,v_amount,
    p.cash_account_id,j.id,j.economic_date,j.transaction_date,j.posting_at,
    p.replaces_payment_id,prior_reversal.reversal_journal_entry_id,v_snapshot
  )::text,'UTF8'),'sha256'),'hex');
  insert into erp.sales_payment_posting_facts(
    payment_id,sale_id,customer_id,payment_number,payment_date,amount,cash_account_id,
    original_journal_entry_id,journal_economic_date,journal_transaction_date,
    journal_posting_at,replaces_payment_id,predecessor_reversal_journal_id,
    payment_snapshot,lineage_sha256,recorded_by
  ) values(
    p.id,p.sale_id,h.customer_id,p.payment_number,p.payment_date,v_amount,p.cash_account_id,
    j.id,j.economic_date,j.transaction_date,j.posting_at,p.replaces_payment_id,
    prior_reversal.reversal_journal_entry_id,v_snapshot,v_digest,erp.current_app_user_id()
  );
  update erp.sales_payments set status='POSTED' where id=p_payment_id;
  v_paid:=v_paid+v_amount;
  update erp.sales_headers
  set status=case when v_paid=v_total then 'PAID' else 'PARTIAL_PAID' end
  where id=h.id;
end
$function$;
CREATE OR REPLACE FUNCTION erp.post_supplier_payment(p_payment_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare p erp.supplier_payments%rowtype;h erp.material_purchase_headers%rowtype;v_cash uuid;v_paid numeric(20,2);v_total numeric(20,2);
begin
  perform erp.require_internal();select * into p from erp.supplier_payments where id=p_payment_id for update;
  if p.id is null or p.status<>'DRAFT' then raise exception 'Supplier payment must be DRAFT'; end if;
  select * into h from erp.material_purchase_headers where id=p.purchase_id for update;
  if h.id is null or h.status<>'POSTED' then raise exception 'Material purchase must be POSTED before payment'; end if;
  select erp.material_purchase_payable_total(h.id)::numeric(20,2) into v_total;
  select coalesce(sum(amount),0)::numeric(20,2) into v_paid from erp.supplier_payments where purchase_id=h.id and status='POSTED';
  if v_paid+p.amount>v_total then raise exception 'Supplier payment exceeds remaining payable. Net payable %, already paid %, requested %',v_total,v_paid,p.amount; end if;
  v_cash:=erp.initial_prepayment_funding_v1(p.id,'SUPPLIER',h.supplier_id,p.amount,erp._cp3_business_date(p.payment_date),greatest(erp._cp3_business_date(h.physical_at),(select max(i.invoice_date) from erp.material_supplier_invoices i join erp.material_supplier_invoice_lines l on l.invoice_id=i.id join erp.material_purchase_items pi on pi.id=l.purchase_item_id where pi.purchase_id=h.id and i.status='POSTED')));
  if v_cash is null then
  select coa_account_id into v_cash from erp.cash_accounts where id=p.cash_account_id and is_active=true;
  end if;
  if v_cash is null then raise exception 'Active cash/bank account is required'; end if;
  perform erp.post_journal('SUPPLIER_PAYMENT',p.id,erp._cp3_business_date(p.payment_date),'Material supplier payment',jsonb_build_array(
    jsonb_build_object('mapping_key','AP_SUPPLIER','debit',p.amount,'credit',0),jsonb_build_object('account_id',v_cash,'debit',0,'credit',p.amount)));
  update erp.supplier_payments set status='POSTED' where id=p.id;v_paid:=v_paid+p.amount;
  update erp.material_purchase_headers set payment_status=case when v_paid=round(v_total,2) then 'PAID' else 'PARTIAL' end where id=h.id;
end;$function$;
CREATE OR REPLACE FUNCTION erp.post_vendor_payment(p_payment_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  p erp.vendor_payments%rowtype;h erp.vendor_invoices%rowtype;
  v_cash uuid;v_paid numeric(20,2);
begin
  perform erp.require_internal();
  select * into p from erp.vendor_payments where id=p_payment_id for update;
  if p.id is null or p.status<>'DRAFT' then raise exception 'Vendor payment must be DRAFT'; end if;
  select * into h from erp.vendor_invoices where id=p.vendor_invoice_id for update;
  if h.status not in('POSTED','PARTIAL_PAID') then
    raise exception 'Vendor invoice must be posted and still unpaid';
  end if;
  select coalesce(sum(amount),0)::numeric(20,2) into v_paid
  from erp.vendor_payments where vendor_invoice_id=h.id and status='POSTED';
  if v_paid+p.amount>h.total_amount then
    raise exception 'Vendor payment exceeds exact remaining payable. Invoice total %, already paid %, requested %',
      h.total_amount,v_paid,p.amount;
  end if;
  v_cash:=erp.initial_prepayment_funding_v1(p.id,'VENDOR',h.vendor_id,p.amount,erp._cp3_business_date(p.payment_date),h.invoice_date);
  if v_cash is null then
  select coa_account_id into v_cash from erp.cash_accounts
  where id=p.cash_account_id and is_active=true;
  end if;
  if v_cash is null then raise exception 'Active cash/bank account is required'; end if;
  perform erp.post_journal('VENDOR_PAYMENT',p.id,erp._cp3_business_date(p.payment_date),'Laundry vendor payment',jsonb_build_array(
    jsonb_build_object('mapping_key','AP_VENDOR','debit',p.amount,'credit',0,'vendor_id',h.vendor_id),
    jsonb_build_object('account_id',v_cash,'debit',0,'credit',p.amount,'vendor_id',h.vendor_id)));
  update erp.vendor_payments set status='POSTED' where id=p.id;
  v_paid:=v_paid+p.amount;
  update erp.vendor_invoices set status=case when v_paid=total_amount then 'PAID' else 'PARTIAL_PAID' end
  where id=h.id;
end
$function$;
CREATE OR REPLACE FUNCTION erp.reverse_journal(p_journal_entry_id uuid, p_reason text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare v_source_type text;
begin
  perform erp.require_internal();
  if nullif(btrim(p_reason),'') is null then raise exception 'Journal reversal reason is required'; end if;
  select source_type into v_source_type
  from erp.journal_entries where id=p_journal_entry_id for update;
  if v_source_type is null then raise exception 'Journal entry not found'; end if;
  if v_source_type='POCKET_HPP_PERIOD' then raise exception 'Batalkan alokasi kain kantong melalui periode asal';end if;
  if v_source_type='MATERIAL_ADJUSTMENT' and exists(select 1 from erp.pocket_fabric_usage u join erp.journal_entries j on j.source_id=u.adjustment_id where j.id=p_journal_entry_id)
    and not exists(select 1 from erp.pocket_fabric_execution_context c join erp.journal_entries j on j.source_id=c.adjustment_id
      where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()
      and c.actor_key=erp._idempotency_actor_key() and j.id=p_journal_entry_id) then
    raise exception 'Batalkan pengurangan kain kantong melalui dokumen asal';end if;
  if v_source_type in('OPENING_PREPAYMENT','PREPAYMENT_EVENT') or (v_source_type in('SUPPLIER_PAYMENT','SALES_PAYMENT','VENDOR_PAYMENT','OPENING_SUBLEDGER_SETTLEMENT')
    and exists(select 1 from erp.initial_import_prepayment_payments l join erp.journal_entries j on j.source_id=l.payment_id where j.id=p_journal_entry_id)) then
    raise exception 'Pembatalan uang muka harus melalui sumber pembayaran atau perubahan tertaut';end if;
  if v_source_type='MATERIAL_ADJUSTMENT_REVALUATION' then
    raise exception 'T_PROTECTED_REVALUATION_JOURNAL_USE_SOURCE_WORKFLOW';
  end if;
  if v_source_type in ('ATTENDANCE_HPP_POOL','PAYROLL_ATTENDANCE_ACCRUAL') then
    raise exception 'Protected journal source type % cannot be reversed through generic reverse_journal. Use the owning attendance HPP pool or payroll cancellation/reversal flow.',v_source_type;
  end if;
  return erp._cp3_r4_reverse_journal_internal(p_journal_entry_id,p_reason);
end
$function$;
CREATE OR REPLACE FUNCTION erp.reverse_sales_payment(p_payment_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
 SET "TimeZone" TO 'UTC'
AS $function$
declare
  p erp.sales_payments%rowtype;
  h erp.sales_headers%rowtype;
  f erp.sales_payment_posting_facts%rowtype;
  j erp.journal_entries%rowtype;
  r erp.journal_entries%rowtype;
  v_journal uuid;
  v_reversal_journal uuid;
  v_paid numeric(20,2);
  v_total numeric(20,2);
  v_digest text;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal pembayaran customer wajib diisi'; end if;
  select * into p from erp.sales_payments where id=p_payment_id for update;
  if p.id is null then raise exception 'Pembayaran customer tidak ditemukan'; end if;
  if p.status='REVERSED' then return; end if;
  if p.status<>'POSTED' then raise exception 'Hanya pembayaran customer yang sudah POSTED yang dapat direverse'; end if;
  select * into h from erp.sales_headers where id=p.sale_id for update;
  perform 1 from erp.initial_import_prepayments a join erp.initial_import_prepayment_payments l on l.advance_id=a.id where l.payment_id=p.id for update of a;
  if h.id is null then raise exception 'Penjualan sumber pembayaran tidak ditemukan'; end if;
  select * into f from erp.sales_payment_posting_facts where payment_id=p.id;
  if f.payment_id is null or f.payment_snapshot is distinct from to_jsonb(p)-'status'
     or f.sale_id is distinct from p.sale_id or f.customer_id is distinct from h.customer_id
     or f.amount is distinct from p.amount or f.payment_date is distinct from p.payment_date
     or f.cash_account_id is distinct from p.cash_account_id then
    raise exception 'Immutable payment posting fact is missing or inconsistent; reversal stopped';
  end if;
  v_journal:=f.original_journal_entry_id;
  select * into j from erp.journal_entries where id=v_journal for update;
  if j.id is null or j.source_type<>'SALES_PAYMENT' or j.source_id<>p.id
     or j.status<>'POSTED' or j.economic_date<>f.journal_economic_date
     or j.transaction_date<>f.journal_transaction_date or j.posting_at<>f.journal_posting_at then
    raise exception 'Jurnal pembayaran customer tidak cocok dengan immutable fact; reversal dibatalkan';
  end if;
  v_reversal_journal:=case when erp.initial_prepayment_account_v1(p.id) is not null then erp._cp3_r4_reverse_journal_internal(v_journal,p_reason) else erp.reverse_journal(v_journal,p_reason) end;
  select * into strict r from erp.journal_entries where id=v_reversal_journal;
  if r.economic_date<f.journal_economic_date or r.posting_at<f.journal_posting_at then
    raise exception 'Payment reversal chronology cannot precede original posting';
  end if;
  v_digest:=encode(extensions.digest(convert_to(jsonb_build_array(
    p.id,j.id,r.id,r.economic_date,r.transaction_date,r.posting_at
  )::text,'UTF8'),'sha256'),'hex');
  insert into erp.sales_payment_reversal_facts(
    payment_id,original_journal_entry_id,reversal_journal_entry_id,
    reversal_economic_date,reversal_transaction_date,reversal_posting_at,
    lineage_sha256,recorded_by
  ) values(
    p.id,j.id,r.id,r.economic_date,r.transaction_date,r.posting_at,
    v_digest,erp.current_app_user_id()
  );
  update erp.sales_payments set status='REVERSED' where id=p.id;

  select round(erp.sale_net_total(h.id),2)::numeric(20,2) into v_total;
  select round(coalesce(sum(round(amount,2)),0),2)::numeric(20,2) into v_paid
  from erp.sales_payments where sale_id=h.id and status='POSTED';
  if v_paid>v_total then
    raise exception 'Payment reversal exposed an unsupported customer overpayment. Net sale %, still paid %',v_total,v_paid;
  end if;
  update erp.sales_headers
  set status=case when v_paid=v_total and v_total>=0 then 'PAID'
    when v_paid>0 and v_paid<v_total then 'PARTIAL_PAID' else 'POSTED' end
  where id=h.id;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values ('sales_payments',p.id,'REVERSE',erp.current_app_user_id(),p_reason);
end
$function$;
CREATE OR REPLACE FUNCTION erp.reverse_supplier_payment(p_payment_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  p erp.supplier_payments%rowtype;
  h erp.material_purchase_headers%rowtype;
  v_journal uuid;
  v_paid numeric(20,2);
  v_total numeric(20,2);
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal pembayaran supplier wajib diisi'; end if;
  select * into p from erp.supplier_payments where id=p_payment_id for update;
  if p.id is null then raise exception 'Pembayaran supplier tidak ditemukan'; end if;
  if p.status='REVERSED' then return; end if;
  if p.status<>'POSTED' then raise exception 'Hanya pembayaran supplier yang sudah POSTED yang dapat direverse'; end if;
  select * into h from erp.material_purchase_headers where id=p.purchase_id for update;
  perform 1 from erp.initial_import_prepayments a join erp.initial_import_prepayment_payments l on l.advance_id=a.id where l.payment_id=p.id for update of a;
  if h.id is null then raise exception 'Pembelian sumber pembayaran tidak ditemukan'; end if;

  select id into v_journal from erp.journal_entries
  where source_type='SUPPLIER_PAYMENT' and source_id=p.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if v_journal is null then raise exception 'Jurnal pembayaran supplier tidak ditemukan; reversal dibatalkan agar kas/hutang tidak rusak'; end if;

  if erp.initial_prepayment_account_v1(p.id) is not null then perform erp._cp3_r4_reverse_journal_internal(v_journal,p_reason);else perform erp.reverse_journal(v_journal,p_reason);end if;
  update erp.supplier_payments set status='REVERSED' where id=p.id;

  select erp.material_purchase_payable_total(h.id)::numeric(20,2) into v_total;
  select coalesce(sum(amount),0)::numeric(20,2) into v_paid from erp.supplier_payments where purchase_id=h.id and status='POSTED';
  update erp.material_purchase_headers set payment_status=case when v_paid=round(v_total,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end where id=h.id;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values ('supplier_payments',p.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;
CREATE OR REPLACE FUNCTION erp.reverse_vendor_payment(p_payment_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  p erp.vendor_payments%rowtype;h erp.vendor_invoices%rowtype;
  v_journal uuid;v_paid numeric(20,2);
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then
    raise exception 'Alasan reversal pembayaran vendor laundry wajib diisi';
  end if;
  select * into p from erp.vendor_payments where id=p_payment_id for update;
  if p.id is null then raise exception 'Pembayaran vendor laundry tidak ditemukan'; end if;
  if p.status='REVERSED' then return; end if;
  if p.status<>'POSTED' then
    raise exception 'Hanya pembayaran vendor laundry yang sudah POSTED yang dapat direverse';
  end if;
  select * into h from erp.vendor_invoices where id=p.vendor_invoice_id for update;
  perform 1 from erp.initial_import_prepayments a join erp.initial_import_prepayment_payments l on l.advance_id=a.id where l.payment_id=p.id for update of a;
  if h.id is null then raise exception 'Invoice vendor laundry sumber pembayaran tidak ditemukan'; end if;
  select id into v_journal from erp.journal_entries
  where source_type='VENDOR_PAYMENT' and source_id=p.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if v_journal is null then
    raise exception 'Jurnal pembayaran vendor laundry tidak ditemukan; reversal dibatalkan agar kas/hutang tidak rusak';
  end if;
  if erp.initial_prepayment_account_v1(p.id) is not null then perform erp._cp3_r4_reverse_journal_internal(v_journal,p_reason);else perform erp.reverse_journal(v_journal,p_reason);end if;
  update erp.vendor_payments set status='REVERSED' where id=p.id;
  select coalesce(sum(amount),0)::numeric(20,2) into v_paid
  from erp.vendor_payments where vendor_invoice_id=h.id and status='POSTED';
  update erp.vendor_invoices set status=case
    when v_paid=h.total_amount then 'PAID'
    when v_paid>0 then 'PARTIAL_PAID' else 'POSTED' end where id=h.id;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('vendor_payments',p.id,'REVERSE',erp.current_app_user_id(),p_reason);
end
$function$;
CREATE OR REPLACE FUNCTION erp.reverse_opening_subledger_settlement(p_settlement_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
DECLARE s erp.opening_subledger_settlements%ROWTYPE;b erp.opening_subledger_balances%ROWTYPE;v_journal uuid;
BEGIN PERFORM erp.require_owner_admin();SELECT * INTO s FROM erp.opening_subledger_settlements WHERE id=p_settlement_id FOR UPDATE;IF s.id IS NULL OR s.status<>'POSTED' THEN RAISE EXCEPTION 'Only POSTED opening settlement can be reversed';END IF;SELECT * INTO b FROM erp.opening_subledger_balances WHERE id=s.balance_id FOR UPDATE;PERFORM 1 FROM erp.initial_import_prepayments a JOIN erp.initial_import_prepayment_payments l ON l.advance_id=a.id WHERE l.payment_id=s.id FOR UPDATE OF a;SELECT id INTO v_journal FROM erp.journal_entries WHERE source_type='OPENING_SUBLEDGER_SETTLEMENT' AND source_id=s.id AND status='POSTED' ORDER BY posting_at DESC LIMIT 1;IF v_journal IS NULL THEN RAISE EXCEPTION 'Opening settlement journal not found';END IF;IF erp.initial_prepayment_account_v1(s.id) IS NOT NULL THEN PERFORM erp._cp3_r4_reverse_journal_internal(v_journal,p_reason);ELSE PERFORM erp.reverse_journal(v_journal,COALESCE(NULLIF(trim(p_reason),''),'Opening settlement reversal'));END IF;UPDATE erp.opening_subledger_settlements SET status='REVERSED',updated_at=statement_timestamp() WHERE id=s.id;UPDATE erp.opening_subledger_balances SET settled_amount=GREATEST(settled_amount-s.amount,0),status=CASE WHEN GREATEST(settled_amount-s.amount,0)=0 THEN 'OPEN' WHEN GREATEST(settled_amount-s.amount,0)=original_amount THEN 'SETTLED' ELSE 'PARTIAL' END,updated_at=statement_timestamp() WHERE id=b.id;END;$function$;
CREATE OR REPLACE FUNCTION erp.rebuild_po_hpp(p_po_id uuid, p_reason text DEFAULT 'Recalculate HPP'::text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_material numeric(24,6):=0;v_opening_cost numeric(24,6):=0;
  v_material_allocated numeric(24,6):=0;
  v_contractor_material numeric(24,6):=0;
  v_accessory numeric(24,6):=0;
  v_labor numeric(24,6):=0;
  v_commission numeric(24,6):=0;
  v_laundry numeric(24,6):=0;
  v_rework numeric(24,6):=0;
  v_other numeric(24,6):=0;
  v_pocket numeric(24,6):=0;v_pocket_allocated numeric(24,6):=0;v_lot_pocket numeric(24,6):=0;
  v_attendance_hpp numeric(24,6):=0;
  v_shared_attendance_hpp numeric(24,6):=0;
  v_shared_labor numeric(24,6):=0;
  v_shared_commission numeric(24,6):=0;
  v_shared_rework numeric(24,6):=0;
  v_shared_other numeric(24,6):=0;
  v_total_current numeric(24,6):=0;
  v_total_qty integer:=0;
  v_pending boolean:=false;
  r record;
  c record;
  v_old_id uuid;
  v_new_id uuid;
  v_version integer;
  v_lot_accessory numeric(24,6);
  v_lot_cost numeric(24,6);
  v_lot_material numeric(24,6);
  v_pool_material numeric(24,6);
  v_pool_qty numeric(24,6);
  v_batch_id uuid;
  v_state varchar(20);
  v_group_fg_qty numeric(24,6);
  v_group_labor numeric(24,6);
  v_group_commission numeric(24,6);
  v_group_laundry numeric(24,6);
  v_group_rework numeric(24,6);
  v_group_attendance_hpp numeric(24,6);
  v_lot_attendance_hpp numeric(24,6);
  v_lot_labor numeric(24,6);
  v_lot_commission numeric(24,6);
  v_lot_laundry numeric(24,6);
  v_lot_rework numeric(24,6);
  v_lot_other numeric(24,6);
  v_cp6_lineage boolean:=false;
  v_lot_cp6_receipt_laundry numeric(24,6):=0;
  v_lot_cp6_attempt_laundry numeric(24,6):=0;
  v_laundry_allocated numeric(24,6):=0;
  v_labor_allocated numeric(24,6):=0;
  v_commission_allocated numeric(24,6):=0;
  v_rework_allocated numeric(24,6):=0;
  v_attendance_allocated numeric(24,6):=0;
  v_po_source_qty numeric(24,6):=0;
begin
  perform erp.require_internal();
  perform erp.pocket_period_lock_v1();
  select coalesce(sum(erp.pocket_period_amount_v1(d.pool_id,d.preceding_qty,d.sewing_qty)),0) into v_pocket from erp.pocket_period_destinations d where d.po_id=p_po_id;
  -- One lock order covers Draft reservation, post/reversal, late recost, and GL sync.
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  perform pg_advisory_xact_lock(hashtextextended('PO_HPP:'||p_po_id::text,0));

  select coalesce(sum(-msm.qty_signed*msm.unit_cost_snapshot),0) into v_material
  from erp.material_stock_movements msm
  where (msm.source_type='CUTTING_GROUP' and msm.source_id in (select id from erp.cutting_groups where po_id=p_po_id))
     or (msm.source_type='CUTTING_GROUP_RETURN' and msm.source_id in (select id from erp.cutting_groups where po_id=p_po_id));

  select coalesce(sum(cmii.qty*cmii.unit_cost_snapshot),0) into v_contractor_material
  from erp.contractor_material_issue_items cmii
  join erp.contractor_material_issues cmi on cmi.id=cmii.issue_id
  join erp.materials m on m.id=cmii.material_id
  where cmi.po_id=p_po_id and cmi.status='POSTED' and m.material_type<>'ACCESSORY';

  select
    coalesce(sum(case when wc.component_category='COMMISSION' then wcl.amount_payable else 0 end),0),
    coalesce(sum(case when wc.component_category<>'COMMISSION' then wcl.amount_payable else 0 end),0),
    coalesce(sum(case when wce.cutting_group_id is null and wc.component_category='COMMISSION' then wcl.amount_payable else 0 end),0),
    coalesce(sum(case when wce.cutting_group_id is null and wc.component_category<>'COMMISSION' then wcl.amount_payable else 0 end),0)
  into v_commission,v_labor,v_shared_commission,v_shared_labor
  from erp.work_completion_lines wcl
  join erp.work_completion_events wce on wce.id=wcl.completion_id
  join erp.work_components wc on wc.id=wcl.work_component_id
  where wce.po_id=p_po_id and wce.status='POSTED';

  with dl as (
    select ldl.id,ldl.cutting_group_id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot,
           coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then lrl.qty_good_received+lrl.qty_bs_laundry else 0 end),0) as qty_costed_actual,
           coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then coalesce(lrl.actual_cost,0) else 0 end),0) as actual_cost,
           bool_or(lr.status='POSTED' and lrl.actual_cost_status in('PENDING','ESTIMATED')) as has_pending_receipt
    from erp.laundry_delivery_lines ldl
    join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
    left join erp.laundry_receipt_lines lrl on lrl.delivery_line_id=ldl.id
    left join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where ld.po_id=p_po_id and ld.status<>'REVERSED'
    group by ldl.id,ldl.cutting_group_id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot
  )
  select coalesce(sum(actual_cost+greatest(qty_sent_pcs-qty_costed_actual,0)*coalesce(estimated_rate_snapshot,0)),0),
         coalesce(bool_or(has_pending_receipt or qty_sent_pcs>qty_costed_actual),false)
  into v_laundry,v_pending from dl;

  select v_laundry+coalesce(sum(rl.actual_cost),0)
    into v_laundry
  from erp.laundry_failed_wash_attempts a
  join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
  join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
  join erp.laundry_deliveries ld on ld.id=a.delivery_id and ld.status='REVERSED'
  where ld.po_id=p_po_id and rl.actual_cost_status in('ESTIMATED','FINAL');

  v_pending:=v_pending or exists(
    select 1
    from erp.laundry_failed_wash_attempts a
    join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
    join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
    join erp.laundry_deliveries ld on ld.id=a.delivery_id
    where ld.po_id=p_po_id and rl.actual_cost_status='ESTIMATED'
  );


  select coalesce(sum(rcl.amount_payable),0),
         coalesce(sum(case when bc.cutting_group_id is null then rcl.amount_payable else 0 end),0)
  into v_rework,v_shared_rework
  from erp.rework_component_lines rcl
  join erp.rework_orders ro on ro.id=rcl.rework_order_id
  join erp.bs_cases bc on bc.id=ro.bs_case_id
  where bc.po_id=p_po_id and ro.status<>'CANCELLED' and coalesce(ro.cost_posted,false)=true;

  select coalesce(sum(adjustment_amount),0),coalesce(sum(case when lot_id is null then adjustment_amount else 0 end),0)
  into v_other,v_shared_other
  from erp.cost_adjustments
  where po_id=p_po_id and component_type='OTHER';

  select
    coalesce(sum(a.allocated_amount),0),
    coalesce(sum(case when a.cutting_group_id is null then a.allocated_amount else 0 end),0)
  into v_attendance_hpp,v_shared_attendance_hpp
  from erp.attendance_hpp_pool_allocations a
  join erp.attendance_hpp_pools hp on hp.id=a.pool_id and hp.status='ACTIVE'
  where a.po_id=p_po_id;

  select coalesce(sum(initial_qty_pcs),0) into v_total_qty
  from erp.fg_lots where po_id=p_po_id and lot_origin='PRODUCTION';
  if v_total_qty<=0 then return; end if;
  v_po_source_qty:=erp.cp6_po_source_qty_v2620c(p_po_id);
  if coalesce(v_po_source_qty,0)<=0 then
    raise exception 'PO source quantity is required before HPP can be allocated';
  end if;

  for r in select id from erp.fg_lots where po_id=p_po_id and lot_origin='PRODUCTION' order by produced_at,id
  loop perform erp.ensure_fg_accessory_cost_snapshot(r.id); end loop;

  select coalesce(sum(facs.total_hpp_cost),0) into v_accessory
  from erp.fg_accessory_cost_snapshots facs join erp.fg_lots fl on fl.id=facs.lot_id
  where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION';

  v_pending:=v_pending or exists(select 1 from erp.initial_import_production_sources s
    join erp.initial_import_cost_origins o on o.opening_item_id=s.opening_item_id where s.po_id=p_po_id
    and erp.material_purchase_invoice_capacity(o.purchase_item_id)>erp.material_purchase_posted_invoice_qty(o.purchase_item_id));
  v_state:=case when v_pending then 'ESTIMATED' when exists (select 1 from erp.cost_adjustments where po_id=p_po_id) then 'ADJUSTED' else 'ACTUAL' end;

  for r in
    select fl.*,coalesce(fl.qc_item_id,(
      select bc.qc_item_id from erp.rework_orders ro
      join erp.bs_cases bc on bc.id=ro.bs_case_id
      where ro.good_fg_lot_id=fl.id
    )) as source_qc_item_id,
      coalesce(fl.cutting_group_id,qi.cutting_group_id) as lineage_group_id
    from erp.fg_lots fl left join erp.qc_inspection_items qi on qi.id=fl.qc_item_id
    where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION'
    order by fl.produced_at,fl.id
  loop
    v_lot_material:=0;v_pool_material:=0;v_pool_qty:=0;v_batch_id:=null;
    v_group_fg_qty:=0;v_group_labor:=0;v_group_commission:=0;v_group_laundry:=0;v_group_rework:=0;v_group_attendance_hpp:=0;
    v_cp6_lineage:=false;v_lot_cp6_receipt_laundry:=0;v_lot_cp6_attempt_laundry:=0;

    if r.lineage_group_id is not null then
      select cutting_batch_id into v_batch_id from erp.cutting_groups where id=r.lineage_group_id;
      if v_batch_id is not null then
        select coalesce(sum(-msm.qty_signed*msm.unit_cost_snapshot),0) into v_pool_material
        from erp.material_stock_movements msm
        where (msm.source_type='CUTTING_GROUP' and msm.source_id in (select id from erp.cutting_groups where cutting_batch_id=v_batch_id))
           or (msm.source_type='CUTTING_GROUP_RETURN' and msm.source_id in (select id from erp.cutting_groups where cutting_batch_id=v_batch_id));
        select effective_pcs::numeric into v_pool_qty from erp.v_cutting_batch_totals where cutting_batch_id=v_batch_id;
      else
        select coalesce(sum(-msm.qty_signed*msm.unit_cost_snapshot),0) into v_pool_material
        from erp.material_stock_movements msm
        where msm.source_id=r.lineage_group_id and msm.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN');
        select total_pcs::numeric into v_pool_qty from erp.v_cutting_group_totals where cutting_group_id=r.lineage_group_id;
      end if;

      select coalesce(sum(fl2.initial_qty_pcs),0)::numeric into v_group_fg_qty
      from erp.fg_lots fl2 where fl2.po_id=p_po_id and fl2.lot_origin='PRODUCTION' and fl2.cutting_group_id=r.lineage_group_id;

      select
        coalesce(sum(case when wc.component_category<>'COMMISSION' then wcl.amount_payable else 0 end),0),
        coalesce(sum(case when wc.component_category='COMMISSION' then wcl.amount_payable else 0 end),0)
      into v_group_labor,v_group_commission
      from erp.work_completion_lines wcl
      join erp.work_completion_events wce on wce.id=wcl.completion_id
      join erp.work_components wc on wc.id=wcl.work_component_id
      where wce.po_id=p_po_id and wce.status='POSTED' and wce.cutting_group_id=r.lineage_group_id;

      with dl as (
        select ldl.id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot,
               coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then lrl.qty_good_received+lrl.qty_bs_laundry else 0 end),0) as qty_costed_actual,
               coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then coalesce(lrl.actual_cost,0) else 0 end),0) as actual_cost
        from erp.laundry_delivery_lines ldl
        join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
        left join erp.laundry_receipt_lines lrl on lrl.delivery_line_id=ldl.id
        left join erp.laundry_receipts lr on lr.id=lrl.receipt_id
        where ld.po_id=p_po_id and ld.status<>'REVERSED' and ldl.cutting_group_id=r.lineage_group_id
        group by ldl.id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot
      )
      select coalesce(sum(actual_cost+greatest(qty_sent_pcs-qty_costed_actual,0)*coalesce(estimated_rate_snapshot,0)),0)
      into v_group_laundry from dl;

      select v_group_laundry+coalesce(sum(rl.actual_cost),0)
        into v_group_laundry
      from erp.laundry_failed_wash_attempts a
      join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
      join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
      join erp.laundry_deliveries ld on ld.id=a.delivery_id and ld.status='REVERSED'
      join erp.laundry_delivery_lines ldl on ldl.delivery_id=ld.id
      where ld.po_id=p_po_id and ldl.cutting_group_id=r.lineage_group_id
        and rl.actual_cost_status in('ESTIMATED','FINAL');


      select coalesce(sum(rcl.amount_payable),0) into v_group_rework
      from erp.rework_component_lines rcl
      join erp.rework_orders ro on ro.id=rcl.rework_order_id
      join erp.bs_cases bc on bc.id=ro.bs_case_id
      where bc.po_id=p_po_id and bc.cutting_group_id=r.lineage_group_id and ro.status<>'CANCELLED' and coalesce(ro.cost_posted,false)=true;

      select coalesce(sum(a.allocated_amount),0) into v_group_attendance_hpp
      from erp.attendance_hpp_pool_allocations a
      join erp.attendance_hpp_pools hp on hp.id=a.pool_id and hp.status='ACTIVE'
      where a.po_id=p_po_id and a.cutting_group_id=r.lineage_group_id;
    end if;

    select exists(
      select 1
      from erp.qc_inspection_items qi
      join erp.laundry_receipt_batch_size_lines rx
        on rx.id=qi.source_laundry_receipt_batch_size_line_id
      where qi.id=r.source_qc_item_id
    ) into v_cp6_lineage;

    if v_cp6_lineage then
      select coalesce((case
          when rl.actual_cost_status in('ESTIMATED','FINAL') and rl.actual_cost is not null
            then rl.actual_cost/nullif(rl.qty_good_received+rl.qty_bs_laundry,0)
          else coalesce(rl.actual_rate_snapshot,dl.estimated_rate_snapshot,0)
        end)*r.initial_qty_pcs,0)
      into v_lot_cp6_receipt_laundry
      from erp.qc_inspection_items qi
      join erp.laundry_receipt_batch_size_lines rx
        on rx.id=qi.source_laundry_receipt_batch_size_line_id
      join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
        and rl.id=qi.source_laundry_receipt_line_id
      join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
      join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
      join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
      left join erp.laundry_failed_wash_attempts fa on fa.receipt_line_id=rl.id
      where qi.id=r.source_qc_item_id and fa.id is null;
      v_lot_cp6_receipt_laundry:=coalesce(v_lot_cp6_receipt_laundry,0);

      select erp.cp6_lot_failed_wash_cost_v2620e(r.id)
      into v_lot_cp6_attempt_laundry;
    end if;

    if coalesce(v_pool_qty,0)>0 then v_lot_material:=v_pool_material*(r.initial_qty_pcs::numeric/v_pool_qty);
    else v_lot_material:=v_material*(r.initial_qty_pcs::numeric/v_total_qty::numeric); end if;
    v_lot_material:=v_lot_material+v_contractor_material*(r.initial_qty_pcs::numeric/v_po_source_qty);
    v_material_allocated:=v_material_allocated+v_lot_material;

    v_lot_labor:=erp.cp6_lot_work_cost_v2620c(r.id,'LABOR');
    v_lot_commission:=erp.cp6_lot_work_cost_v2620c(r.id,'COMMISSION');
    v_lot_laundry:=case when v_cp6_lineage
      then v_lot_cp6_receipt_laundry+v_lot_cp6_attempt_laundry
      when r.lineage_group_id is not null then v_group_laundry*(r.initial_qty_pcs::numeric/nullif(
        coalesce(nullif((select total_pcs::numeric from erp.v_cutting_group_totals
          where cutting_group_id=r.lineage_group_id),0),v_po_source_qty),0))
      else v_laundry*(r.initial_qty_pcs::numeric/v_po_source_qty) end;
    v_lot_rework:=erp.cp6_lot_rework_cost_v2620c(r.id);
    v_lot_attendance_hpp:=erp.cp6_lot_attendance_cost_v2620c(r.id);
    v_lot_pocket:=erp.pocket_lot_cost_v1(r.id);v_pocket_allocated:=v_pocket_allocated+v_lot_pocket;

    select coalesce(sum(total_hpp_cost),0) into v_lot_accessory from erp.fg_accessory_cost_snapshots where lot_id=r.id;
    select coalesce(sum(adjustment_amount),0) into v_lot_other from erp.cost_adjustments where lot_id=r.id and component_type='OTHER';
    v_lot_other:=v_lot_other+v_shared_other*(r.initial_qty_pcs::numeric/v_po_source_qty);
    v_laundry_allocated:=v_laundry_allocated+v_lot_laundry;
    v_labor_allocated:=v_labor_allocated+v_lot_labor;
    v_commission_allocated:=v_commission_allocated+v_lot_commission;
    v_rework_allocated:=v_rework_allocated+v_lot_rework;
    v_attendance_allocated:=v_attendance_allocated+v_lot_attendance_hpp;
    v_opening_cost:=erp.initial_import_lot_cost_v1(r.id);
    v_lot_cost:=v_opening_cost+v_lot_material+v_lot_labor+v_lot_commission+v_lot_laundry+v_lot_rework+v_lot_attendance_hpp+v_lot_other+v_lot_accessory+v_lot_pocket;
    v_total_current:=v_total_current+v_lot_cost;

    select id into v_old_id from erp.hpp_versions where lot_id=r.id and is_current=true order by version_no desc limit 1;
    select coalesce(max(version_no),0)+1 into v_version from erp.hpp_versions where lot_id=r.id;
    if v_old_id is not null then update erp.hpp_versions set is_current=false where id=v_old_id; end if;

    insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,supersedes_id,calculation_reason,created_by)
    values (r.id,v_version,v_state,r.initial_qty_pcs,v_lot_cost,true,v_old_id,p_reason,erp.current_app_user_id()) returning id into v_new_id;

    insert into erp.hpp_version_components(hpp_version_id,component_type,description,total_cost,source_type,source_id)
    values
      (v_new_id,'MATERIAL',case when v_batch_id is not null then 'Cutting material by effective batch yield + PO-shared non-accessory contractor material' else 'Cutting/legacy material pool + PO-shared non-accessory contractor material' end,v_lot_material,case when v_batch_id is not null then 'CUTTING_BATCH' else 'PO' end,coalesce(v_batch_id,p_po_id)),
      (v_new_id,'LABOR','Labor allocation: immutable component completion intervals; unfinished remains WIP',v_lot_labor,case when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'COMMISSION','Commission allocation: immutable component completion intervals; unfinished remains WIP',v_lot_commission,case when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'LAUNDRY',case when v_cp6_lineage
        then 'CP6 exact receipt/batch-size service lineage; unfinished cost remains WIP'
        else 'Legacy Laundry allocation from same cutting group; PENDING uses estimate' end,
        v_lot_laundry,case when v_cp6_lineage then 'QC_ITEM'
          when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,
        case when v_cp6_lineage then r.source_qc_item_id else coalesce(r.lineage_group_id,p_po_id) end),
      (v_new_id,'REWORK','Rework allocation: exact good rework lot and qty-sent source',v_lot_rework,case when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'LABOR','Attendance HPP: ACTIVE source sewing intervals; unfinished remains WIP',v_lot_attendance_hpp,'ATTENDANCE_HPP_ACTIVE_ALLOCATION',coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'OTHER','Kain kantong: pembagian periode selesai dijahit',v_lot_pocket,'POCKET_PERIOD_ALLOCATION',p_po_id),
      (v_new_id,'OTHER','Other/adjustment allocation',v_lot_other,'PO',p_po_id),
      (v_new_id,'OTHER','Saldo fisik sebelum cutover',v_opening_cost,'INITIAL_IMPORT_PRODUCTION',r.id);

    for c in
      select facs.id,facs.total_hpp_cost,ac.category_name,facs.hpp_method
      from erp.fg_accessory_cost_snapshots facs join erp.accessory_categories ac on ac.id=facs.category_id
      where facs.lot_id=r.id order by ac.category_code
    loop
      insert into erp.hpp_version_components(hpp_version_id,component_type,description,total_cost,source_type,source_id)
      values (v_new_id,'ACCESSORY','Accessory category: '||c.category_name||' ['||c.hpp_method||']',c.total_hpp_cost,'FG_ACCESSORY_SNAPSHOT',c.id);
    end loop;

    update erp.fg_stock_movements set unit_hpp_snapshot=(select hpp_per_pcs from erp.hpp_versions where id=v_new_id)
    where lot_id=r.id and movement_type in ('QC_GOOD','REWORK_IN');
  end loop;

  if v_pocket_allocated < -0.005 or v_pocket_allocated>v_pocket+0.005 then raise exception 'Pocket HPP cost conservation failed';end if;
  if v_labor_allocated < -0.005 or v_labor_allocated > v_labor+0.005
     or v_commission_allocated < -0.005 or v_commission_allocated > v_commission+0.005
     or v_rework_allocated < -0.005 or v_rework_allocated > v_rework+0.005
     or v_attendance_allocated < -0.005 or v_attendance_allocated > v_attendance_hpp+0.005 then
    raise exception 'CP6 source-owned HPP allocation violates cost conservation: labor %/%, commission %/%, rework %/%, attendance %/%',
      v_labor_allocated,v_labor,v_commission_allocated,v_commission,
      v_rework_allocated,v_rework,v_attendance_allocated,v_attendance_hpp;
  end if;

  if v_laundry_allocated < -0.005 or v_laundry_allocated > v_laundry+0.005 then
    raise exception 'CP6 Laundry HPP allocation violates cost conservation: accrued %, FG allocated %',
      v_laundry,v_laundry_allocated;
  end if;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values ('production_orders',p_po_id,'RECALCULATE',jsonb_build_object(
    'material_total_issued',v_material+v_contractor_material,'cutting_material_total',v_material,'contractor_nonaccessory_material_total',v_contractor_material,'material_allocated_to_current_fg',v_material_allocated,'material_basis','CUTTING_BATCH_EFFECTIVE_YIELD_PLUS_PO_SHARED_CONTRACTOR_MATERIAL',
    'pocket_fabric',v_pocket,'pocket_allocated_to_fg',v_pocket_allocated,'pocket_remaining_in_wip',v_pocket-v_pocket_allocated,
    'accessory',v_accessory,'labor',v_labor,'attendance_hpp',v_attendance_hpp,'commission',v_commission,'laundry',v_laundry,'rework',v_rework,'other',v_other,
    'laundry_allocated_to_current_fg',v_laundry_allocated,
    'laundry_remaining_in_wip',v_laundry-v_laundry_allocated,
    'labor_allocated_to_fg',v_labor_allocated,'labor_remaining_in_wip',v_labor-v_labor_allocated,
    'commission_allocated_to_fg',v_commission_allocated,'commission_remaining_in_wip',v_commission-v_commission_allocated,
    'rework_allocated_to_fg',v_rework_allocated,'rework_remaining_in_wip',v_rework-v_rework_allocated,
    'attendance_allocated_to_fg',v_attendance_allocated,'attendance_remaining_in_wip',v_attendance_hpp-v_attendance_allocated,
    'po_physical_source_qty',v_po_source_qty,
    'laundry_basis','CP6_EXACT_DELIVERY_SIZE_CUSTODY_INTERVAL_V2620C',
    'total_current_fg_cost',v_total_current,'cost_state',v_state,'nonmaterial_basis','CUTTING_GROUP_LINEAGE_WITH_PO_SHARED_FALLBACK','accessory_basis','GOOD_FG_X_CATEGORY_BOM'),
    erp.current_app_user_id(),p_reason);
end;
$function$;
CREATE OR REPLACE FUNCTION erp.ensure_fg_accessory_cost_snapshot(p_lot_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  l erp.fg_lots%rowtype;
  p erp.production_orders%rowtype;
  v_bom uuid;
  r record;
  v_category_avg numeric(18,6);
  v_hpp_factor numeric(18,6);
  v_reimburse_factor numeric(18,6);
  v_hpp_base numeric(18,6);
  v_reimburse_base numeric(18,6);
  v_snapshot uuid;
  v_commit_at timestamptz;
  v_rework uuid;
  v_decision uuid;
  v_recipient uuid;
  v_selected_count integer;
  v_snapshot_count integer;
begin
  perform erp.require_internal();
  select * into l from erp.fg_lots where id=p_lot_id for update;
  if l.id is null or l.lot_origin<>'PRODUCTION' then return; end if;
  select * into p from erp.production_orders where id=l.po_id;
  if p.id is null then return; end if;

  select ro.id,d.id,d.bom_version_id,d.reimbursement_contractor_id,d.selected_item_count
  into v_rework,v_decision,v_bom,v_recipient,v_selected_count
  from erp.rework_orders ro
  join erp.rework_accessory_decisions d on d.rework_order_id=ro.id
  where ro.good_fg_lot_id=l.id;

  if v_rework is not null then
    select count(*) into v_snapshot_count
    from erp.fg_accessory_cost_snapshots s where s.lot_id=l.id;
    if v_snapshot_count>0 then
      if v_snapshot_count<>v_selected_count
         or exists(
           select 1 from erp.fg_accessory_cost_snapshots s
           left join erp.rework_accessory_selection_lines sl
             on sl.decision_id=v_decision and sl.bom_item_id=s.bom_item_id
           where s.lot_id=l.id and sl.id is null
         ) then
        raise exception 'Rework accessory snapshot set diverges from immutable selection lineage';
      end if;
      return;
    end if;
    if v_selected_count=0 then return; end if;
    if v_bom is null then raise exception 'Selected rework accessory lineage has no BOM version'; end if;
    if not exists(
      select 1 from erp.po_accessory_bom_commitments c
      where c.po_id=l.po_id and c.product_id=l.product_id and c.bom_version_id=v_bom
    ) then raise exception 'Rework accessory BOM commitment is missing or changed'; end if;

    for r in
      select sl.*,c.category_code
      from erp.rework_accessory_selection_lines sl
      join erp.accessory_categories c on c.id=sl.category_id
      where sl.decision_id=v_decision
      order by c.category_code,sl.id
    loop
      v_category_avg:=erp.accessory_category_weighted_avg_cost_at(r.category_id,l.produced_at);
      if r.hpp_method_snapshot='CATEGORY_MOVING_AVG' then
        if v_category_avg is null then
          raise exception 'Cannot snapshot HPP: accessory category % has no moving-average valuation history at %',r.category_id,l.produced_at;
        end if;
        v_hpp_base:=v_category_avg;
      else
        v_hpp_base:=r.hpp_standard_unit_cost_base_snapshot;
      end if;
      v_reimburse_base:=r.reimbursement_unit_rate_base_snapshot;
      insert into erp.fg_accessory_cost_snapshots(
        lot_id,po_id,product_id,bom_version_id,bom_item_id,category_id,
        good_qty_pcs,qty_per_good_fg_base,hpp_method,
        category_avg_cost_base_snapshot,hpp_unit_cost_base_snapshot,
        reimbursement_unit_rate_base_snapshot,costing_basis_at,costing_basis_source
      ) values(
        l.id,l.po_id,l.product_id,v_bom,r.bom_item_id,r.category_id,
        l.initial_qty_pcs,r.qty_per_good_fg_base_snapshot,r.hpp_method_snapshot,
        v_category_avg,v_hpp_base,v_reimburse_base,l.produced_at,'FG_ACCEPTANCE'
      ) returning id into v_snapshot;
      if v_recipient is null and v_reimburse_base>0 then
        raise exception 'Selected rework accessory reimbursement has no authoritative Mandor';
      end if;
      if v_recipient is not null and v_reimburse_base>0 then
        insert into erp.contractor_accessory_reimbursement_entitlements(
          snapshot_id,contractor_id,po_id,lot_id,product_id,category_id,physical_at,amount
        ) select
          v_snapshot,v_recipient,l.po_id,l.id,l.product_id,r.category_id,
          l.produced_at,total_reimbursement
        from erp.fg_accessory_cost_snapshots where id=v_snapshot;
      end if;
    end loop;
    return;
  end if;

  if exists(select 1 from erp.initial_import_wip_outputs o join erp.initial_import_production_sources s on s.opening_item_id=o.opening_item_id where o.lot_id=l.id and s.accessory_cost_included) then return;end if;
  if exists(select 1 from erp.fg_accessory_cost_snapshots where lot_id=l.id) then return; end if;
  v_bom:=erp.commit_accessory_bom_for_lot(l.id);
  if v_bom is null then return; end if;
  select committed_at into v_commit_at
  from erp.po_accessory_bom_commitments
  where po_id=l.po_id and product_id=l.product_id;
  for r in
    select i.*,c.base_uom_code
    from erp.accessory_bom_items i
    join erp.accessory_categories c on c.id=i.category_id
    where i.bom_version_id=v_bom order by c.category_code
  loop
    v_category_avg:=erp.accessory_category_weighted_avg_cost_at(r.category_id,l.produced_at);
    if r.hpp_method='CATEGORY_MOVING_AVG' then
      if v_category_avg is null then
        raise exception 'Cannot snapshot HPP: accessory category % has no moving-average valuation history at %',r.category_id,l.produced_at;
      end if;
      v_hpp_base:=v_category_avg;
    else
      v_hpp_factor:=erp.accessory_uom_factor(r.category_id,r.hpp_uom_code,l.produced_at);
      v_hpp_base:=r.hpp_standard_rate/v_hpp_factor;
    end if;
    v_reimburse_factor:=erp.accessory_uom_factor(
      r.category_id,r.reimbursement_uom_code,l.produced_at
    );
    v_reimburse_base:=r.reimbursement_rate/v_reimburse_factor;
    insert into erp.fg_accessory_cost_snapshots(
      lot_id,po_id,product_id,bom_version_id,bom_item_id,category_id,
      good_qty_pcs,qty_per_good_fg_base,hpp_method,
      category_avg_cost_base_snapshot,hpp_unit_cost_base_snapshot,
      reimbursement_unit_rate_base_snapshot,costing_basis_at,costing_basis_source
    ) values(
      l.id,l.po_id,l.product_id,v_bom,r.id,r.category_id,l.initial_qty_pcs,
      r.qty_per_good_fg_base,r.hpp_method,v_category_avg,v_hpp_base,
      v_reimburse_base,l.produced_at,
      case when v_commit_at=l.produced_at then 'FIRST_FINANCIAL_USE' else 'FG_ACCEPTANCE' end
    ) returning id into v_snapshot;
    if p.contractor_id is null and v_reimburse_base>0 then
      raise exception 'PO % has accessory reimbursement BOM but no mandor/contractor',p.po_number;
    end if;
    if p.contractor_id is not null and v_reimburse_base>0 then
      insert into erp.contractor_accessory_reimbursement_entitlements(
        snapshot_id,contractor_id,po_id,lot_id,product_id,category_id,physical_at,amount
      ) select
        v_snapshot,p.contractor_id,l.po_id,l.id,l.product_id,r.category_id,
        l.produced_at,total_reimbursement
      from erp.fg_accessory_cost_snapshots where id=v_snapshot;
    end if;
  end loop;
end
$function$;
CREATE OR REPLACE FUNCTION erp.get_wip_control_v1(p_filter text DEFAULT 'ACTIVE'::text, p_pattern_id uuid DEFAULT NULL::uuid, p_sort text DEFAULT 'PATTERN'::text, p_query text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_filter text:=upper(coalesce(nullif(btrim(p_filter),''),'ACTIVE'));
  v_sort text:=upper(coalesce(nullif(btrim(p_sort),''),'PATTERN'));
  v_query text:=lower(nullif(btrim(p_query),''));
begin
  perform erp.require_permission('production.wip.view');
  if v_filter not in ('ACTIVE','COMPLETED','ALL') then raise exception 'filter must be ACTIVE, COMPLETED, or ALL'; end if;
  if v_sort not in ('PATTERN','PRODUCTION','UPDATED') then raise exception 'sort must be PATTERN, PRODUCTION, or UPDATED'; end if;
  return jsonb_build_object(
    'filter',v_filter,'sort',v_sort,'pattern_id',p_pattern_id,
    'opening_rows',coalesce((select jsonb_agg(x-'original_amount'-'current_amount'-'accessory_cost_included')
     from jsonb_array_elements(erp.initial_import_production_rows_v1(null)) x
     where p_pattern_id is null and (v_filter='ALL' or ((x->>'remaining_qty_pcs')::integer>0)=(v_filter='ACTIVE'))
       and (v_query is null or lower(concat_ws(' ',x->>'po_number',x->>'source_key',x->>'size_code',x->>'contractor_name',x->>'vendor_name')) like '%'||v_query||'%')),'[]'::jsonb),'rows',coalesce((
      select jsonb_agg(
        to_jsonb(w)||jsonb_build_object(
          'distribution',(
            select jsonb_build_object(
              'pickup_id',p.id,'contractor_id',p.contractor_id,'contractor_name',c.contractor_name,
              'picked_up_at',p.picked_up_at,'allocation_mode',p.allocation_mode,
              'batches',coalesce((
                select jsonb_agg(jsonb_build_object(
                  'id',b.id,'batch_no',b.batch_no,'notes',b.notes,
                  'qty_pcs',coalesce((select sum(a.qty_pcs) from erp.cutting_distribution_allocations a where a.batch_id=b.id),0),
                  'sizes',coalesce((
                    select jsonb_agg(jsonb_build_object('size_code',z.size_code,'qty_pcs',z.qty_pcs)
                      order by z.sort_order,z.size_code)
                    from (
                      select sz.size_code,sz.sort_order,sum(a.qty_pcs)::bigint qty_pcs
                      from erp.cutting_distribution_allocations a
                      join erp.cutting_roll_yields y on y.id=a.cutting_roll_yield_id
                      join erp.cutting_group_size_slots ss on ss.id=y.size_slot_id
                      join erp.sizes sz on sz.id=ss.size_id
                      where a.batch_id=b.id group by sz.id,sz.size_code,sz.sort_order
                    ) z
                  ),'[]'::jsonb)
                ) order by b.batch_no,b.id)
                from erp.cutting_distribution_batches b where b.pickup_id=p.id
              ),'[]'::jsonb)
            )
            from erp.cutting_pickups p join erp.contractors c on c.id=p.contractor_id
            where p.cutting_group_id=w.cutting_group_id and p.status='POSTED'
            order by p.posted_at desc,p.id desc limit 1
          )
        ) order by
          case when v_sort='PATTERN' then coalesce(w.pattern_sort_order,2147483647) end,
          case when v_sort='PATTERN' then coalesce(w.pattern_code,'~') end,
          case when v_sort='UPDATED' then w.updated_at end desc,
          w.po_number,w.group_number,w.cutting_group_id
      )
      from erp.v_wip_control_status_v1 w
      where (v_filter='ALL' or w.control_status=v_filter)
        and (p_pattern_id is null or w.pattern_id=p_pattern_id)
        and (v_query is null or lower(concat_ws(' ',w.po_number,w.group_number,w.model_code,w.model_name,
          w.pattern_code,w.pattern_name,w.executor_name,w.group_status,w.notes)) like '%'||v_query||'%')
    ),'[]'::jsonb)
  );
end
$function$;
CREATE OR REPLACE FUNCTION erp.sync_opening_lot_hpp_to_gl(p_lot_id uuid, p_effective_date date DEFAULT ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  l erp.fg_lots%rowtype; s erp.opening_lot_hpp_gl_state%rowtype;
  h erp.hpp_versions%rowtype; v_baseline numeric; v_source_delta numeric;
  v_expected_delta numeric; v_current_qty numeric; v_base_fg numeric;
  v_net_sold_qty numeric; v_actual_cogs numeric; v_expense numeric; v_income numeric;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into l from erp.fg_lots where id=p_lot_id for update;
  if l.id is null or l.lot_origin<>'OPENING' then return; end if;
  select * into h from erp.hpp_versions where lot_id=l.id and is_current;
  if h.id is null then raise exception 'Opening current HPP is missing'; end if;
  select fm.unit_hpp_snapshot into v_baseline from erp.fg_stock_movements fm
  where fm.lot_id=l.id and fm.movement_type='OPENING'
  order by fm.physical_at,fm.system_created_at,fm.id limit 1;
  if v_baseline is null then raise exception 'Opening lot % has no source movement',l.lot_number; end if;
  if exists(select 1 from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id
    where a.source_lot_id=l.id and c.status='POSTED') then
    raise exception 'Opening HPP conversion requires a sourced descendant correction workflow';
  end if;
  select * into s from erp.opening_lot_hpp_gl_state where lot_id=l.id for update;
  v_expected_delta:=round(h.total_cost,2)
    -round(l.initial_qty_pcs*coalesce(s.current_hpp,v_baseline),2);
  select t.hpp_total_cost-b.hpp_total_cost into v_source_delta
  from erp.compute_non_po_product_hpp_targets_v2620f(l.product_id) t
  cross join lateral erp.compute_non_po_product_hpp_book_v2620f(l.product_id) b;
  if v_source_delta is distinct from v_expected_delta then
    raise exception 'OPENING_SOURCE_CHANGE_NOT_EXACT: product %, pending lot basis %, target/book source delta %',
      l.product_id,v_expected_delta,v_source_delta;
  end if;
  if v_source_delta<>0 then
    perform erp.post_journal('OPENING_HPP_SOURCE_V2620G',h.id,p_effective_date,
      'Source lot basis correction for '||l.lot_number||' / HPP version '||h.id,
      jsonb_build_array(
        jsonb_build_object('mapping_key','FG_INVENTORY',
          'debit',greatest(v_source_delta,0),'credit',greatest(-v_source_delta,0),'product_id',l.product_id),
        jsonb_build_object('mapping_key','OPENING_EQUITY',
          'debit',greatest(-v_source_delta,0),'credit',greatest(v_source_delta,0))
      ));
  end if;
  perform erp.sync_non_po_product_hpp_to_gl_v2620f(l.product_id,p_effective_date,
    'OPENING_HPP_LIFECYCLE_V2620G',h.id,'Exact rounded opening source and cumulative physical lifecycle');
  perform erp.assert_non_po_product_hpp_target_book_v2620f(l.product_id);

  -- Preserve the historical raw revaluation diagnostics and trigger-activation
  -- contract. These projections are not used as monetary posting authority:
  -- actual journals and F's cumulative source/target/book checks are.
  -- DRAFT reservations reduce sellable qty, not company ownership.
  select coalesce(sum(fm.qty_signed),0),coalesce(sum(fm.qty_signed*fm.unit_hpp_snapshot),0)
    into v_current_qty,v_base_fg from erp.fg_stock_movements fm where fm.lot_id=l.id;
  select v_current_qty+coalesce(sum(abs(fm.qty_signed)),0),
    v_base_fg+coalesce(sum(abs(fm.qty_signed)*fm.unit_hpp_snapshot),0)
    into v_current_qty,v_base_fg from erp.fg_stock_movements fm
    where fm.lot_id=l.id and fm.movement_type='SALE_RESERVE'
      and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id);
  select coalesce(sum(a.qty_pcs),0),coalesce(sum(a.qty_pcs*a.unit_hpp_snapshot),0)
    into v_net_sold_qty,v_actual_cogs from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id join erp.sales_headers sh on sh.id=i.sale_id
    where a.lot_id=l.id and sh.status in('POSTED','PARTIAL_PAID','PAID');
  select v_net_sold_qty-coalesce(sum(i.qty_pcs),0),v_actual_cogs-coalesce(sum(i.qty_pcs*i.unit_hpp_snapshot),0)
    into v_net_sold_qty,v_actual_cogs from erp.sales_return_items i
    join erp.sales_returns rh on rh.id=i.return_id where i.lot_id=l.id and rh.status='POSTED';
  select coalesce(sum(case when i.qty_signed<0 then -i.qty_signed*(h.hpp_per_pcs-i.unit_hpp_snapshot) else 0 end),0),
    coalesce(sum(case when i.qty_signed>0 then i.qty_signed*(h.hpp_per_pcs-i.unit_hpp_snapshot) else 0 end),0)
    into v_expense,v_income from erp.fg_adjustment_items i
    join erp.fg_adjustments a on a.id=i.adjustment_id where i.lot_id=l.id and a.status='POSTED';
  insert into erp.opening_lot_hpp_gl_state(lot_id,current_hpp,fg_revaluation,cogs_revaluation,
    expense_revaluation,income_revaluation,equity_revaluation,updated_at)
  values(l.id,h.hpp_per_pcs,v_current_qty*h.hpp_per_pcs-v_base_fg,
    v_net_sold_qty*h.hpp_per_pcs-v_actual_cogs,v_expense,v_income,
    l.initial_qty_pcs*(h.hpp_per_pcs-v_baseline),statement_timestamp())
  on conflict(lot_id) do update set current_hpp=excluded.current_hpp,
    fg_revaluation=excluded.fg_revaluation,cogs_revaluation=excluded.cogs_revaluation,
    expense_revaluation=excluded.expense_revaluation,income_revaluation=excluded.income_revaluation,
    equity_revaluation=excluded.equity_revaluation,updated_at=statement_timestamp();
end
$function$;
CREATE OR REPLACE FUNCTION erp.post_opening_balance(p_opening_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.opening_balance_headers%rowtype; r record; v_lot uuid; v_lot_no text; v_value numeric(24,6); v_unit_hpp numeric(20,6);
  v_debits numeric(24,6):=0; v_credits numeric(24,6):=0; v_lines jsonb:='[]'::jsonb; v_default_fg_location uuid; v_fg_count integer;
  v_product_at timestamptz;v_source erp.initial_import_production_sources%rowtype;v_bs uuid;
begin
  perform erp.require_owner_admin();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  -- Serialize with staging before taking the header lock. A revalidated
  -- preview alone cannot revive the obsolete prepared lines removed by edit.
  perform 1 from erp.migration_batches b where b.id=(select migration_batch_id
    from erp.opening_balance_headers where id=p_opening_id) for update;
  if exists(select 1 from erp.migration_batches b join erp.opening_balance_headers opening_header on opening_header.migration_batch_id=b.id
    where opening_header.id=p_opening_id and (b.status not in('READY','POSTING') or exists(
      select 1 from erp.migration_staging_rows s where s.batch_id=b.id and s.validation_status<>'VALID'))) then
    raise exception 'AK_OPENING_REQUIRES_CURRENT_VALIDATED_BATCH';
  end if;
  select * into h from erp.opening_balance_headers where id=p_opening_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Opening balance must be DRAFT'; end if;
  if not exists(select 1 from erp.opening_balance_items where opening_id=h.id) then raise exception 'Opening balance has no lines'; end if;

  perform i.id from erp.opening_balance_items i
  where i.opening_id=h.id order by i.id for update;

  -- Ordinary opening items remain editable while DRAFT. Validate the latest
  -- locked rows before any stock, BS, subledger or journal side effect.
  for r in select * from erp.opening_balance_items where opening_id=h.id order by id loop
    if r.qty::text in('NaN','Infinity','-Infinity')
       or r.amount::text in('NaN','Infinity','-Infinity')
       or r.unit_cost_snapshot::text in('NaN','Infinity','-Infinity')
       or r.hpp_percent_of_price::text in('NaN','Infinity','-Infinity')
       or r.reference_sell_price_snapshot::text in('NaN','Infinity','-Infinity') then
      raise exception 'AL_OPENING_VALUES_MUST_BE_FINITE';
    end if;
    if r.balance_type='BS' and
       (r.qty is null or r.qty<=0 or r.qty<>trunc(r.qty) or r.qty>2147483647) then
      raise exception 'AL_BS_REQUIRES_POSITIVE_WHOLE_PCS';
    end if;
    if r.balance_type='WIP' then
      if r.amount is null and (r.qty is null or r.unit_cost_snapshot is null) then
        raise exception 'AL_WIP_REQUIRES_AMOUNT_OR_QTY_AND_COST';
      end if;
      if r.amount<0 or r.qty<0 or r.unit_cost_snapshot<0 then
        raise exception 'AL_WIP_VALUE_MUST_BE_NONNEGATIVE';
      end if;
    end if;
  end loop;
  if exists(
    select 1 from erp.opening_balance_items i
    where i.opening_id=h.id and i.roll_id is not null
      and i.balance_type<>'MATERIAL'
  ) then
    raise exception 'AE_OPENING_ROLL_ONLY_ALLOWED_FOR_MATERIAL';
  end if;
  if exists(
    select 1 from erp.opening_balance_items i
    where i.opening_id=h.id and i.balance_type='MATERIAL'
      and i.roll_id is not null
    group by i.roll_id having count(*)>1
  ) then
    raise exception 'AE_OPENING_ROLL_DUPLICATE_IN_DOCUMENT';
  end if;
  perform mr.id from erp.material_rolls mr
  where mr.id in(
    select i.roll_id from erp.opening_balance_items i
    where i.opening_id=h.id and i.roll_id is not null
  ) order by mr.id for update;
  for r in
    select i.*,m.material_type,
      mr.material_id as roll_material_id,
      mr.original_qty as roll_original_qty,
      mr.cached_qty as roll_cached_qty,
      mr.purchase_item_id as roll_purchase_item_id,
      mr.status as roll_status
    from erp.opening_balance_items i
    left join erp.materials m on m.id=i.material_id
    left join erp.material_rolls mr on mr.id=i.roll_id
    where i.opening_id=h.id and i.balance_type='MATERIAL'
    order by i.id
  loop
    if r.material_type='FABRIC' and r.roll_id is null then
      raise exception 'AE_FABRIC_OPENING_REQUIRES_ROLL';
    end if;
    if r.roll_id is not null then
      if r.material_type is distinct from 'FABRIC' then
        raise exception 'AE_OPENING_ROLL_REQUIRES_FABRIC';
      end if;
      if r.roll_material_id is distinct from r.material_id then
        raise exception 'AE_OPENING_ROLL_MATERIAL_MISMATCH';
      end if;
      if r.roll_status is distinct from 'AVAILABLE' then
        raise exception 'AE_OPENING_ROLL_NOT_AVAILABLE';
      end if;
      if r.roll_purchase_item_id is not null then
        raise exception 'AE_PURCHASE_ROLL_CANNOT_BE_OPENING_BALANCE';
      end if;
      if coalesce(r.qty,0)>r.roll_original_qty then
        raise exception 'AE_OPENING_QTY_EXCEEDS_ROLL_ORIGINAL';
      end if;
      if exists(
        select 1 from erp.opening_balance_items prior
        join erp.opening_balance_headers prior_h on prior_h.id=prior.opening_id
        where prior.roll_id=r.roll_id and prior_h.status='POSTED'
      ) then
        raise exception 'AE_OPENING_ROLL_ALREADY_POSTED';
      end if;
      if exists(select 1 from erp.material_stock_movements prior_m where prior_m.roll_id=r.roll_id)
         or coalesce(r.roll_cached_qty,0)<>0 then
        raise exception 'AE_OPENING_ROLL_HAS_EXISTING_STOCK_HISTORY';
      end if;
    end if;
  end loop;

  select count(*),(array_agg(id order by id))[1] into v_fg_count,v_default_fg_location from erp.locations where location_type='FG_WAREHOUSE' and is_active=true;
  for r in select * from erp.opening_balance_items where opening_id=h.id order by id loop
    select * into v_source from erp.initial_import_production_sources where opening_item_id=r.id;
    if r.balance_type='MATERIAL' then
      if r.material_id is null or r.location_id is null or coalesce(r.qty,0)<=0 then raise exception 'Opening material needs material, location and positive qty'; end if;
      if r.unit_cost_snapshot is null or r.unit_cost_snapshot<0 then raise exception 'Opening material unit cost wajib diisi (0 boleh jika memang nilainya nol)'; end if;
      v_value:=r.qty*r.unit_cost_snapshot;
      insert into erp.material_stock_movements(material_id,roll_id,location_id,movement_type,qty_signed,input_unit_cost,unit_cost_snapshot,source_type,source_id,physical_at,created_by)
      values(r.material_id,r.roll_id,r.location_id,'OPENING',r.qty,r.unit_cost_snapshot,r.unit_cost_snapshot,'OPENING_BALANCE_ITEM',r.id,(h.opening_date::timestamp at time zone 'Asia/Jakarta'),erp.current_app_user_id());
      perform erp.recalculate_material_cost(r.material_id);
      if round(v_value,2)>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',round(v_value,2),'credit',0));v_debits:=v_debits+round(v_value,2);end if;
    elsif r.balance_type='FINISHED_GOODS' then
      if r.product_id is null or coalesce(r.qty,0)<=0 or trunc(r.qty)<>r.qty then raise exception 'Opening FG needs product and whole positive pcs qty'; end if;
      if r.location_id is null and v_fg_count<>1 then raise exception 'Opening FG requires location when active FG warehouse count is not exactly one'; end if;
      if r.hpp_input_method='MANUAL' and (r.unit_cost_snapshot is null or r.unit_cost_snapshot<0) then raise exception 'Opening FG HPP manual wajib diisi (0 boleh jika memang HPP nol), atau pilih %% dari harga jual'; end if;
      v_product_at:=erp.product_opening_physical_at(r.product_id,h.opening_date);
      v_unit_hpp:=erp.resolve_opening_fg_unit_hpp(r.id,h.opening_date);v_value:=r.qty*v_unit_hpp;
      v_lot_no:='OPEN-'||h.opening_number||'-'||substr(r.id::text,1,8);
      insert into erp.fg_lots(lot_number,po_id,qc_item_id,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,is_open,lot_origin)
      values(v_lot_no,null,null,r.product_id,r.qty::integer,0,v_product_at,true,'OPENING') returning id into v_lot;
      insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,calculation_reason,created_by)
      values(v_lot,1,case when exists(
        select 1 from erp.initial_import_opening_stock_sources k join erp.migration_staging_rows o
          on o.batch_id=k.batch_id and o.entity_type='OPENING_COST_ORIGIN' and o.normalized_payload->>'target_source_key'=k.source_key
        where k.opening_item_id=r.id) then 'ESTIMATED' else 'ACTUAL' end,r.qty::integer,v_value,true,case when r.hpp_input_method='PRICE_PERCENT' then 'Opening FG HPP from selling price percentage snapshot' else 'Opening FG HPP' end,erp.current_app_user_id());
      perform erp.post_fg_movement(r.product_id,v_lot,coalesce(r.location_id,v_default_fg_location),coalesce(r.quality_grade,'GRADE_A'),'OPENING',r.qty::integer,v_unit_hpp,null,'OPENING_BALANCE_ITEM',r.id,v_product_at,'Opening finished goods',false);
      if round(v_value,2)>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','FG_INVENTORY','debit',round(v_value,2),'credit',0,'product_id',r.product_id));v_debits:=v_debits+round(v_value,2);end if;
    elsif r.balance_type='WIP' then v_value:=coalesce(r.amount,coalesce(r.qty,0)*coalesce(r.unit_cost_snapshot,0));if round(v_value,2)>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','WIP','debit',round(v_value,2),'credit',0,'po_id',v_source.po_id));v_debits:=v_debits+round(v_value,2);end if;
      if v_source.opening_item_id is not null then
        insert into erp.wip_stage_events(po_id,stage_from,stage_to,qty_pcs,contractor_id,source_type,source_id,physical_at,created_by,notes)
        values(v_source.po_id,null,v_source.stage,v_source.qty_pcs,r.contractor_id,'INITIAL_IMPORT_WIP_OPENING',r.id,h.opening_date::timestamp at time zone 'Asia/Jakarta',erp.current_app_user_id(),'Posisi fisik pada cutover; bukan penyelesaian kerja atau upah');
      end if;
    elsif r.balance_type='BS' then
      if coalesce(r.qty,0)>0 and trunc(r.qty)=r.qty then
        if r.product_id is not null then v_product_at:=erp.product_opening_physical_at(r.product_id,h.opening_date); else v_product_at:=h.opening_date::timestamp at time zone 'Asia/Jakarta'; end if;
        insert into erp.bs_cases(bs_number,po_id,product_id,detected_at_stage,cause_source,untracked_type,responsible_contractor_id,responsible_vendor_id,qty_pcs,status,physical_at,notes,legacy_reference)
        values('OBS-'||h.opening_number||'-'||substr(r.id::text,1,8),v_source.po_id,r.product_id,coalesce(v_source.stage,'UNKNOWN'),'UNKNOWN','LEGACY',r.contractor_id,r.vendor_id,r.qty::integer,'OPEN',v_product_at,r.notes,case when v_source.opening_item_id is not null then 'OPENING:'||r.id::text else null end) returning id into v_bs;
        if v_source.opening_item_id is not null then
          update erp.initial_import_production_sources set bs_case_id=v_bs where opening_item_id=r.id;
          v_value:=v_source.original_amount;
          if v_value>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','WIP','debit',v_value,'credit',0,'po_id',v_source.po_id));v_debits:=v_debits+v_value;end if;
        end if;
      end if;
    elsif r.balance_type='CONTRACTOR_RECEIVABLE' then v_value:=coalesce(r.amount,0);if v_value<=0 or r.contractor_id is null then raise exception 'Opening contractor receivable requires contractor and positive amount';end if;v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',v_value,'credit',0,'contractor_id',r.contractor_id));v_debits:=v_debits+round(v_value,2);insert into erp.opening_subledger_balances(opening_item_id,party_type,direction,contractor_id,original_amount) values(r.id,'CONTRACTOR','RECEIVABLE',r.contractor_id,v_value);
    elsif r.balance_type='CONTRACTOR_PAYABLE' then v_value:=coalesce(r.amount,0);if v_value<=0 or r.contractor_id is null then raise exception 'Opening contractor payable requires contractor and positive amount';end if;v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',v_value,'contractor_id',r.contractor_id));v_credits:=v_credits+round(v_value,2);insert into erp.opening_subledger_balances(opening_item_id,party_type,direction,contractor_id,original_amount) values(r.id,'CONTRACTOR','PAYABLE',r.contractor_id,v_value);
    elsif r.balance_type='VENDOR_PAYABLE' then v_value:=coalesce(r.amount,0);if v_value<=0 or r.vendor_id is null then raise exception 'Opening laundry vendor payable requires vendor and positive amount';end if;v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','AP_VENDOR','debit',0,'credit',v_value,'vendor_id',r.vendor_id));v_credits:=v_credits+round(v_value,2);insert into erp.opening_subledger_balances(opening_item_id,party_type,direction,vendor_id,original_amount) values(r.id,'VENDOR','PAYABLE',r.vendor_id,v_value);
    elsif r.balance_type='SUPPLIER_PAYABLE' then v_value:=coalesce(r.amount,0);if v_value<=0 or r.supplier_id is null then raise exception 'Opening material supplier payable requires supplier and positive amount';end if;v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','AP_SUPPLIER','debit',0,'credit',v_value));v_credits:=v_credits+round(v_value,2);insert into erp.opening_subledger_balances(opening_item_id,party_type,direction,supplier_id,original_amount) values(r.id,'SUPPLIER','PAYABLE',r.supplier_id,v_value);
    elsif r.balance_type='CUSTOMER_RECEIVABLE' then v_value:=coalesce(r.amount,0);if v_value<=0 or r.customer_id is null then raise exception 'Opening customer receivable requires customer and positive amount';end if;v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','AR_CUSTOMER','debit',v_value,'credit',0,'customer_id',r.customer_id));v_debits:=v_debits+round(v_value,2);insert into erp.opening_subledger_balances(opening_item_id,party_type,direction,customer_id,original_amount) values(r.id,'CUSTOMER','RECEIVABLE',r.customer_id,v_value);
    elsif r.balance_type='CASH_BANK' then v_value:=coalesce(r.amount,0);if v_value<=0 or r.cash_account_id is null then raise exception 'Opening cash/bank requires cash_account and positive amount';end if;v_lines:=v_lines||jsonb_build_array(jsonb_build_object('account_id',(select coa_account_id from erp.cash_accounts where id=r.cash_account_id),'debit',v_value,'credit',0));v_debits:=v_debits+round(v_value,2);
    elsif r.balance_type='OTHER' then raise exception 'Generic OTHER opening balance is intentionally unsupported; use an explicit mapped balance type';
    end if;
  end loop;
  if v_debits>v_credits then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','OPENING_EQUITY','debit',0,'credit',round(v_debits-v_credits,2)));elsif v_credits>v_debits then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','OPENING_EQUITY','debit',round(v_credits-v_debits,2),'credit',0));end if;
  if jsonb_array_length(v_lines)>=2 then perform erp.post_journal('OPENING_BALANCE',h.id,h.opening_date,'ERP go-live opening balance',v_lines);end if;
  update erp.opening_balance_headers set status='POSTED' where id=h.id;
end$function$;
CREATE OR REPLACE FUNCTION erp.compute_po_hpp_gl_book_v2620e(p_po_id uuid)
 RETURNS TABLE(fg_value numeric, cogs_value numeric, other_out_value numeric)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
with lifecycle as(
  select e.id
  from erp.journal_entries e
  left join erp.journal_entries o on o.id=e.reversal_of_id
  where e.status in('POSTED','REVERSED') and(
    e.source_type in('SALE','SALES_RETURN')
    or(e.source_type='JOURNAL_REVERSAL' and o.source_type in('SALE','SALES_RETURN'))
  )
), historical_untagged as(
  select l.id
  from lifecycle l
  where not exists(
    select 1 from erp.journal_lines x
    where x.journal_entry_id=l.id
      and x.account_id in(
        erp.account_id('FG_INVENTORY'),erp.account_id('COGS'),
        erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
      ) and x.po_id is not null
  ) and exists(
    select 1
    from erp.journal_entries e
    left join erp.journal_entries o on o.id=e.reversal_of_id
    where e.id=l.id and(
      (coalesce(o.source_type,e.source_type)='SALE' and exists(
        select 1 from erp.sale_stock_allocations a
        join erp.sales_items i on i.id=a.sale_item_id
        join erp.fg_lots fl on fl.id=a.lot_id
        where i.sale_id=coalesce(o.source_id,e.source_id) and fl.po_id=p_po_id
      )) or
      (coalesce(o.source_type,e.source_type)='SALES_RETURN' and exists(
        select 1 from erp.sales_return_items i
        join erp.fg_lots fl on fl.id=i.lot_id
        where i.return_id=coalesce(o.source_id,e.source_id) and fl.po_id=p_po_id
      ))
    )
  )
), historical_book as(
  select coalesce(sum(
    erp.sale_lifecycle_po_hpp_amount_v2620d(id,p_po_id)
  ),0)::numeric cogs
  from historical_untagged
), direct_book as(
  select
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id=erp.account_id('FG_INVENTORY')),0)::numeric fg,
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id=erp.account_id('COGS')),0)::numeric cogs,
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id in(
        erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
      )),0)::numeric other_out
  from erp.journal_lines l
  join erp.journal_entries e on e.id=l.journal_entry_id
    and e.status in('POSTED','REVERSED')
  where l.po_id=p_po_id and e.source_type<>'INITIAL_IMPORT_BS_VALUE'
), residual_close as(
  select coalesce(sum(e.residual_amount),0)::numeric amount
  from erp.po_wip_close_events e
  join erp.journal_entries j on j.id=e.journal_entry_id
    and j.source_type='PO_WIP_RESIDUAL_CLOSE' and j.status='POSTED'
  where e.po_id=p_po_id
)
select round(d.fg-h.cogs,2),round(d.cogs+h.cogs,2),
  round(d.other_out-c.amount,2)
from direct_book d cross join historical_book h cross join residual_close c
$function$;
create or replace function erp.validate_initial_import_production_v1(p_batch uuid) returns void
language plpgsql security definer set search_path='' as $function$
declare r record;j jsonb;k text;t text;q numeric;v numeric;v_po jsonb;v_model text;v_size text;
begin
 perform erp.require_owner_admin();
 for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPENING_BALANCE_ITEM'
   and (nullif(normalized_payload->>'po_number','') is not null or
     (upper(normalized_payload->>'balance_type') in('WIP','BS') and nullif(normalized_payload->>'opening_source_key','') is not null)) loop
  begin
   j:=r.normalized_payload;t:=upper(j->>'balance_type');
   if t not in('WIP','BS') then raise exception 'po_number: hanya untuk saldo fisik WIP/BS';end if;
   foreach k in array array['po_number','size_code','stage','qty','opening_source_key','accessory_cost_included'] loop
    if nullif(j->>k,'') is null then raise exception '%: wajib untuk saldo fisik WIP/BS',k;end if;
   end loop;
   if j->>'accessory_cost_included' not in('true','false') then raise exception 'accessory_cost_included: isi true atau false';end if;
   if j->>'stage' not in('SEWING','LAUNDRY','QC') or (t='WIP' and j->>'stage'='QC') then
    raise exception 'stage: WIP memakai SEWING/LAUNDRY; BS boleh QC';end if;
   if j->>'stage'='SEWING' and nullif(j->>'contractor_code','') is null then raise exception 'contractor_code: mandor pemegang wajib diisi';end if;
   if j->>'stage'='LAUNDRY' and nullif(j->>'vendor_code','') is null then raise exception 'vendor_code: laundry pemegang wajib diisi';end if;
   if t='BS' and coalesce(nullif(j->>'contractor_code',''),nullif(j->>'vendor_code',''),nullif(j->>'location_code','')) is null then
    raise exception 'location_code: BS perlu gudang atau pihak pemegang yang diketahui';end if;
   if t='BS' and nullif(j->>'product_sku','') is null then raise exception 'product_sku: BS bernilai memerlukan identitas produk';end if;
   q:=(j->>'qty')::numeric;v:=coalesce(nullif(j->>'amount','')::numeric,q*nullif(j->>'unit_cost','')::numeric);
   if q<=0 or q<>trunc(q) or q>2147483647 or v is null or v<0 or v<>round(v,2) then
    raise exception 'qty: saldo fisik perlu pcs bulat positif dan nilai tepat dua desimal (nol boleh)';end if;
   if nullif(j->>'unit_cost','') is not null and (j->>'unit_cost')::numeric<0 then raise exception 'unit_cost: biaya tidak boleh negatif';end if;
   if nullif(j->>'amount','') is not null and nullif(j->>'unit_cost','') is not null
     and (j->>'amount')::numeric<>round(q*(j->>'unit_cost')::numeric,2) then raise exception 'amount: nilai harus sama dengan jumlah x biaya';end if;
   select s.normalized_payload into v_po from erp.migration_staging_rows s where s.batch_id=p_batch
     and s.entity_type='OPEN_PO' and s.normalized_payload->>'po_number'=j->>'po_number' and s.validation_status='VALID';
   if v_po is null then raise exception 'po_number: saldo fisik wajib menunjuk OPEN_PO valid dalam batch yang sama';end if;
   if v_po->>'status' in('FINISHED','CANCELLED') then raise exception 'po_number: saldo fisik belum selesai tidak boleh masuk PO selesai/batal';end if;
   if coalesce(nullif(v_po->>'target_qty_pcs','')::numeric,0)<coalesce((select sum((s.normalized_payload->>'qty')::numeric)
     from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_BALANCE_ITEM'
     and s.normalized_payload->>'po_number'=j->>'po_number' and upper(s.normalized_payload->>'balance_type') in('WIP','BS')),0) then
    raise exception 'target_qty_pcs: jumlah PO wajib mencakup seluruh WIP dan BS fisik';end if;
   if nullif(j->>'model_code','') is not null and j->>'model_code'<>v_po->>'model_code' then raise exception 'model_code: model berbeda dengan PO';end if;
   if exists(select 1 from erp.production_orders p where p.po_number=j->>'po_number' and p.migration_batch_id is distinct from p_batch) then
    raise exception 'po_number: PO sudah memiliki riwayat di luar batch ini';end if;
   if not exists(select 1 from erp.sizes where size_code=j->>'size_code' and is_active)
      and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='SIZE'
        and s.validation_status='VALID' and s.normalized_payload->>'size_code'=j->>'size_code') then raise exception 'size_code: ukuran aktif tidak ditemukan';end if;
   select m.model_code into v_model from erp.products p join erp.product_models m on m.id=p.model_id where p.sku=j->>'product_sku';
   if v_model is null then select normalized_payload->>'model_code' into v_model from erp.migration_staging_rows where batch_id=p_batch
     and entity_type='PRODUCT' and validation_status='VALID' and normalized_payload->>'sku'=j->>'product_sku';end if;
   if v_model is not null and v_model<>v_po->>'model_code' then raise exception 'product_sku: produk berbeda model dengan PO';end if;
   select z.size_code into v_size from erp.products p join erp.sizes z on z.id=p.size_id where p.sku=j->>'product_sku';
   if v_size is null then select normalized_payload->>'size_code' into v_size from erp.migration_staging_rows where batch_id=p_batch
     and entity_type='PRODUCT' and validation_status='VALID' and normalized_payload->>'sku'=j->>'product_sku';end if;
   if v_size is not null and v_size<>j->>'size_code' then raise exception 'size_code: ukuran fisik berbeda dengan produk';end if;
   if exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_BALANCE_ITEM'
     and upper(s.normalized_payload->>'balance_type')='WIP' and nullif(s.normalized_payload->>'po_number','') is null) then
    raise exception 'po_number: jangan campur ringkasan WIP tanpa PO dengan rincian fisik WIP/BS';end if;
  exception when others then update erp.migration_staging_rows set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array(sqlerrm) where id=r.id;
  end;
 end loop;
end;$function$;
revoke all on function erp.validate_initial_import_production_v1(uuid) from public,anon,authenticated,service_role;
create or replace function erp.link_initial_import_production_v1(p_batch uuid,p_row uuid,p_item uuid) returns void
language plpgsql security definer set search_path='' as $function$
declare j jsonb;i erp.opening_balance_items%rowtype;v_po uuid;v_size uuid;
begin
 perform erp.require_owner_admin();
 select normalized_payload into strict j from erp.migration_staging_rows where id=p_row and batch_id=p_batch;
 if nullif(j->>'po_number','') is null then return;end if;
 select * into strict i from erp.opening_balance_items where id=p_item;
 select id into strict v_po from erp.production_orders where po_number=j->>'po_number' and is_legacy and migration_batch_id=p_batch;
 select id into strict v_size from erp.sizes where size_code=j->>'size_code' and is_active;
 insert into erp.initial_import_production_sources(opening_item_id,source_row_id,batch_id,po_id,size_id,stage,qty_pcs,original_amount,accessory_cost_included)
 values(p_item,p_row,p_batch,v_po,v_size,j->>'stage',i.qty::integer,round(coalesce(i.amount,i.qty*i.unit_cost_snapshot),2),(j->>'accessory_cost_included')::boolean);
end;$function$;
revoke all on function erp.link_initial_import_production_v1(uuid,uuid,uuid) from public,anon,authenticated,service_role;
create or replace function erp.initial_import_source_value_v1(p_item uuid) returns numeric
language sql stable security definer set search_path='' as $function$
 select round(coalesce(i.amount,i.qty*i.unit_cost_snapshot,0),2)+coalesce((
  select sum(e.new_delta-e.previous_delta) from erp.initial_import_origin_cost_events e where e.opening_item_id=i.id),0)
 from erp.opening_balance_items i where i.id=p_item;
$function$;
revoke all on function erp.initial_import_source_value_v1(uuid) from public,anon,authenticated,service_role;
create or replace function erp.initial_import_lot_cost_v1(p_lot uuid) returns numeric
language sql stable security definer set search_path='' as $function$
 select coalesce(sum(erp.initial_import_source_value_v1(s.opening_item_id)*l.initial_qty_pcs/s.qty_pcs),0)
 from erp.fg_lots l join erp.initial_import_production_sources s on
   exists(select 1 from erp.initial_import_wip_outputs o where o.lot_id=l.id and o.opening_item_id=s.opening_item_id)
   or exists(select 1 from erp.rework_orders ro where ro.good_fg_lot_id=l.id and ro.bs_case_id=s.bs_case_id and ro.status='COMPLETED')
 where l.id=p_lot and l.lot_origin='PRODUCTION';
$function$;
revoke all on function erp.initial_import_lot_cost_v1(uuid) from public,anon,authenticated,service_role;
create or replace function erp.initial_import_production_rows_v1(p_batch uuid default null) returns jsonb
language sql stable security definer set search_path='' as $function$
 select coalesce(jsonb_agg(jsonb_build_object('opening_item_id',s.opening_item_id,'source_key',k.source_key,
  'batch_id',s.batch_id,'po_id',s.po_id,'po_number',p.po_number,'balance_type',i.balance_type,'stage',s.stage,
  'size_code',z.size_code,'qty_pcs',s.qty_pcs,'completed_qty_pcs',coalesce(o.qty,0),'remaining_qty_pcs',
    s.qty_pcs-case when s.bs_case_id is null then coalesce(o.qty,0) else coalesce(br.qty,0) end,
  'contractor_name',c.contractor_name,'vendor_name',v.vendor_name,'bs_case_id',s.bs_case_id,
  'original_amount',s.original_amount::text,'current_amount',erp.initial_import_source_value_v1(s.opening_item_id)::text,
  'outputs',coalesce((select jsonb_agg(jsonb_build_object('id',o.id,'qty_pcs',o.qty_pcs,'date',erp._cp3_business_date(o.physical_at),'reversed',exists(select 1 from erp.initial_import_wip_output_reversals rv where rv.output_id=o.id)) order by o.created_at,o.id) from erp.initial_import_wip_outputs o where o.opening_item_id=i.id),'[]'::jsonb),
  'cutover_date',h.opening_date,'product_id',i.product_id,'accessory_cost_included',s.accessory_cost_included
 ) order by p.po_number,s.stage,z.size_code,k.source_key),'[]'::jsonb)
 from erp.initial_import_production_sources s join erp.opening_balance_items i on i.id=s.opening_item_id
 join erp.initial_import_opening_stock_sources k on k.opening_item_id=i.id
 join erp.opening_balance_headers h on h.id=i.opening_id and h.status='POSTED'
 join erp.production_orders p on p.id=s.po_id join erp.sizes z on z.id=s.size_id
 left join erp.contractors c on c.id=i.contractor_id left join erp.laundry_vendors v on v.id=i.vendor_id
 left join lateral(select sum(qty_pcs) qty from erp.initial_import_wip_outputs where opening_item_id=i.id and not exists(select 1 from erp.initial_import_wip_output_reversals rv where rv.output_id=erp.initial_import_wip_outputs.id)) o on true
 left join lateral(select sum(qty_pcs) qty from erp.bs_resolutions where bs_case_id=s.bs_case_id) br on true
 where p_batch is null or s.batch_id=p_batch;
$function$;
revoke all on function erp.initial_import_production_rows_v1(uuid) from public,anon,authenticated,service_role;
create or replace function erp.validate_initial_import_cost_origins_v1(p_batch uuid) returns void
language plpgsql security definer set search_path='' as $function$
declare r record;j jsonb;k text;t jsonb;v_receipt jsonb;v_qty numeric;v_amount numeric;v_basis numeric;
begin
 perform erp.require_owner_admin();
 for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPENING_COST_ORIGIN' loop
  begin
   j:=r.normalized_payload;
   foreach k in array array['supplier_code','receipt_number','receipt_line_number','target_source_key','qty'] loop
    if nullif(j->>k,'') is null then raise exception '%: asal biaya wajib lengkap',k;end if;
   end loop;
   v_qty:=(j->>'qty')::numeric;
   if v_qty<=0 or v_qty<>round(v_qty,6) or v_qty::text in('NaN','Infinity','-Infinity') then raise exception 'qty: asal biaya harus positif maksimal enam desimal';end if;
   perform v_qty::numeric(18,6);
   if (select count(*) from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='UNINVOICED_RECEIPT'
     and s.normalized_payload->>'supplier_code'=j->>'supplier_code'
     and lower(btrim(s.normalized_payload->>'receipt_number'))=lower(btrim(j->>'receipt_number'))
     and lower(btrim(s.normalized_payload->>'receipt_line_number'))=lower(btrim(j->>'receipt_line_number')))<>1 then
    raise exception 'receipt_number: asal biaya harus menunjuk tepat satu baris penerimaan';end if;
   select s.normalized_payload into v_receipt from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='UNINVOICED_RECEIPT'
     and s.normalized_payload->>'supplier_code'=j->>'supplier_code'
     and lower(btrim(s.normalized_payload->>'receipt_number'))=lower(btrim(j->>'receipt_number'))
     and lower(btrim(s.normalized_payload->>'receipt_line_number'))=lower(btrim(j->>'receipt_line_number'));
   if (select count(*) from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_BALANCE_ITEM'
      and s.normalized_payload->>'opening_source_key'=j->>'target_source_key')<>1 then raise exception 'target_source_key: tujuan harus tepat satu rincian WIP/BS/FG';end if;
   select s.normalized_payload into t from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_BALANCE_ITEM'
     and s.normalized_payload->>'opening_source_key'=j->>'target_source_key' and s.validation_status='VALID';
   if t is null or upper(t->>'balance_type') not in('WIP','BS','FINISHED_GOODS')
     or (upper(t->>'balance_type') in('WIP','BS') and nullif(t->>'po_number','') is null)
     or upper(t->>'hpp_input_method')='PRICE_PERCENT' then raise exception 'target_source_key: perlu saldo fisik valid dengan nilai manual yang terurai';end if;
   if exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_COST_ORIGIN' and s.id<>r.id
     and s.normalized_payload->>'supplier_code'=j->>'supplier_code'
     and lower(btrim(s.normalized_payload->>'receipt_number'))=lower(btrim(j->>'receipt_number'))
     and lower(btrim(s.normalized_payload->>'receipt_line_number'))=lower(btrim(j->>'receipt_line_number'))
     and s.normalized_payload->>'target_source_key'=j->>'target_source_key') then raise exception 'target_source_key: asal dan tujuan biaya ditulis dua kali';end if;
   select sum(round((s.normalized_payload->>'qty')::numeric*(p.normalized_payload->>'unit_cost')::numeric,2)) into v_amount
   from erp.migration_staging_rows s join erp.migration_staging_rows p on p.batch_id=s.batch_id and p.entity_type='UNINVOICED_RECEIPT'
     and p.normalized_payload->>'supplier_code'=s.normalized_payload->>'supplier_code'
     and lower(btrim(p.normalized_payload->>'receipt_number'))=lower(btrim(s.normalized_payload->>'receipt_number'))
     and lower(btrim(p.normalized_payload->>'receipt_line_number'))=lower(btrim(s.normalized_payload->>'receipt_line_number'))
   where s.batch_id=p_batch and s.entity_type='OPENING_COST_ORIGIN' and s.normalized_payload->>'target_source_key'=j->>'target_source_key';
   v_basis:=round(coalesce(nullif(t->>'amount','')::numeric,(t->>'qty')::numeric*(t->>'unit_cost')::numeric),2);
   if v_basis is null or v_amount is null or v_amount>v_basis then raise exception 'target_source_key: biaya bahan terurai melebihi seluruh nilai saldo tujuan';end if;
  exception when others then update erp.migration_staging_rows set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array(sqlerrm) where id=r.id;
  end;
 end loop;
end;$function$;
revoke all on function erp.validate_initial_import_cost_origins_v1(uuid) from public,anon,authenticated,service_role;
create or replace function erp.refresh_initial_import_fg_cost_v1(p_item uuid,p_delta numeric,p_date date) returns void
language plpgsql security definer set search_path='' as $function$
declare v_lot uuid;v_hpp erp.hpp_versions%rowtype;v_state text;
begin
 perform erp.require_internal();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 select lot_id into strict v_lot from erp.fg_stock_movements where source_type='OPENING_BALANCE_ITEM' and source_id=p_item and movement_type='OPENING';
 select * into strict v_hpp from erp.hpp_versions where lot_id=v_lot and is_current for update;
 v_state:=case when exists(select 1 from erp.initial_import_cost_origins o where o.opening_item_id=p_item
    and erp.material_purchase_invoice_capacity(o.purchase_item_id)>erp.material_purchase_posted_invoice_qty(o.purchase_item_id)) then 'ESTIMATED' else 'ADJUSTED' end;
 if p_delta=0 and v_state=v_hpp.cost_state then return;end if;
 update erp.hpp_versions set is_current=false where id=v_hpp.id;
 insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,supersedes_id,calculation_reason,created_by)
 values(v_lot,v_hpp.version_no+1,v_state,v_hpp.qty_basis_pcs,v_hpp.total_cost+p_delta,true,v_hpp.id,'Harga dan kepastian asal bahan sebelum cutover',erp.current_app_user_id());
 perform erp.sync_opening_lot_hpp_to_gl(v_lot,p_date);
end;$function$;
revoke all on function erp.refresh_initial_import_fg_cost_v1(uuid,numeric,date) from public,anon,authenticated,service_role;
create or replace function erp.recost_initial_import_origins_v1(p_purchase_item uuid) returns void
language plpgsql security definer set search_path='' as $function$
declare r record;v_target numeric;v_previous numeric;v_delta numeric;v_date date;v_event uuid;v_journal uuid;
 v_lot uuid;v_hpp erp.hpp_versions%rowtype;v_new uuid;v_po uuid;v_qty integer;
begin
 perform erp.require_internal();
 perform erp.pocket_period_lock_v1();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 v_date:=coalesce(erp.invoice_recost_economic_date_v1(),erp._cp3_business_date(statement_timestamp()));
 for r in select i.* from erp.opening_balance_items i where i.id in(
   select opening_item_id from erp.initial_import_cost_origins where purchase_item_id=p_purchase_item) order by i.id for update loop
  select coalesce(sum(round(o.material_qty*erp.material_purchase_current_unit_cost(o.purchase_item_id),2)
    -round(o.material_qty*o.unit_cost_snapshot,2)),0) into v_target from erp.initial_import_cost_origins o where o.opening_item_id=r.id;
  select coalesce(sum(new_delta-previous_delta),0) into v_previous from erp.initial_import_origin_cost_events where opening_item_id=r.id;
  v_delta:=v_target-v_previous;
  if v_delta=0 then
   if r.balance_type='FINISHED_GOODS' then perform erp.refresh_initial_import_fg_cost_v1(r.id,0,v_date);
   else
    select po_id into strict v_po from erp.initial_import_production_sources where opening_item_id=r.id;
    perform erp.rebuild_po_hpp(v_po,'Kepastian harga asal bahan sebelum cutover');
    perform erp.propagate_conversion_hpp_for_po(v_po);perform erp.sync_po_hpp_to_gl(v_po,v_date);
   end if;
   continue;
  end if;
  if round(coalesce(r.amount,r.qty*r.unit_cost_snapshot),2)+v_target<0 then raise exception 'Nilai sumber setelah koreksi tidak boleh negatif';end if;
  v_event:=gen_random_uuid();v_po:=null;
  select po_id into v_po from erp.initial_import_production_sources where opening_item_id=r.id;
  insert into erp.initial_import_origin_cost_events(id,opening_item_id,previous_delta,new_delta,economic_date,created_by)
   values(v_event,r.id,v_previous,v_target,v_date,erp.current_app_user_id());
  if r.balance_type='FINISHED_GOODS' then
   perform erp.refresh_initial_import_fg_cost_v1(r.id,v_delta,v_date);
   -- The native opening-lot synchronizer owns FG/COGS and offsets opening equity.
   -- Replace only that source offset with the invoice's material-inventory leg.
   v_journal:=erp.post_journal('INITIAL_IMPORT_ORIGIN_RECOST',v_event,v_date,'Asal biaya bahan pada FG awal',jsonb_build_array(
    jsonb_build_object('mapping_key','OPENING_EQUITY','debit',greatest(v_delta,0),'credit',greatest(-v_delta,0)),
    jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',greatest(-v_delta,0),'credit',greatest(v_delta,0))));
  else
   if v_po is null then raise exception 'Asal WIP/BS harus terhubung ke PO';end if;
   v_journal:=erp.post_journal('INITIAL_IMPORT_ORIGIN_RECOST',v_event,v_date,'Asal biaya bahan pada WIP/BS awal',jsonb_build_array(
    jsonb_build_object('mapping_key','WIP','debit',greatest(v_delta,0),'credit',greatest(-v_delta,0),'po_id',v_po),
    jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',greatest(-v_delta,0),'credit',greatest(v_delta,0))));
   perform erp.sync_initial_import_bs_value_v1(r.id,v_date);
   perform erp.rebuild_po_hpp(v_po,'Koreksi asal bahan sebelum cutover');
   perform erp.propagate_conversion_hpp_for_po(v_po);
   perform erp.sync_po_hpp_to_gl(v_po,v_date);
  end if;
  update erp.initial_import_origin_cost_events set journal_entry_id=v_journal where id=v_event;
 end loop;
end;$function$;
revoke all on function erp.recost_initial_import_origins_v1(uuid) from public,anon,authenticated,service_role;
create or replace function erp.sync_initial_import_bs_value_v1(p_item uuid,p_date date) returns void
language plpgsql security definer set search_path='' as $function$
declare s erp.initial_import_production_sources%rowtype;v_qty integer;v_target numeric;v_prior numeric;v_delta numeric;v_event uuid;v_journal uuid;
begin
 perform erp.require_internal();
 if not pg_try_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0)) then raise exception 'WIP_VALUE_BUSY: penilaian stok sedang berubah, coba ulang';end if;
 select * into s from erp.initial_import_production_sources where opening_item_id=p_item for update;
 if s.bs_case_id is null then return;end if;
 select coalesce(sum(qty_pcs),0) into v_qty from erp.bs_resolutions where bs_case_id=s.bs_case_id
  and source_rework_order_id is null and resolution_type not in('REWORK_SEWING','REWORK_LAUNDRY');
 if v_qty>s.qty_pcs then raise exception 'Pengeluaran BS melebihi saldo fisik';end if;
 v_target:=round(erp.initial_import_source_value_v1(p_item)*v_qty/s.qty_pcs,2);
 select coalesce(sum(target_amount-previous_amount),0) into v_prior from erp.initial_import_bs_value_events where opening_item_id=p_item;
 v_delta:=v_target-v_prior;if v_delta=0 then return;end if;
 v_event:=gen_random_uuid();
 v_journal:=erp.post_journal('INITIAL_IMPORT_BS_VALUE',v_event,p_date,'Nilai BS saldo awal yang dikeluarkan atau dikembalikan',jsonb_build_array(
  jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',greatest(v_delta,0),'credit',greatest(-v_delta,0),'po_id',s.po_id),
  jsonb_build_object('mapping_key','WIP','debit',greatest(-v_delta,0),'credit',greatest(v_delta,0),'po_id',s.po_id)));
 insert into erp.initial_import_bs_value_events(id,opening_item_id,disposed_qty,previous_amount,target_amount,economic_date,journal_entry_id,created_by)
 values(v_event,p_item,v_qty,v_prior,v_target,p_date,v_journal,erp.current_app_user_id());
end;$function$;
revoke all on function erp.sync_initial_import_bs_value_v1(uuid,date) from public,anon,authenticated,service_role;
create or replace function erp.sync_initial_import_bs_disposition_v1() returns trigger
language plpgsql security definer set search_path='' as $function$
declare v_item uuid;v_date date;v_case uuid;v_po_status text;
begin
 if tg_op='DELETE' then v_case:=old.bs_case_id;v_date:=erp._cp3_business_date(statement_timestamp());
 else v_case:=new.bs_case_id;v_date:=erp._cp3_business_date(new.physical_at);end if;
 select opening_item_id into v_item from erp.initial_import_production_sources where bs_case_id=v_case;
 if v_item is not null and tg_op='DELETE' then
  if not pg_try_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0)) then raise exception 'WIP_VALUE_BUSY: penilaian stok sedang berubah, coba ulang';end if;
  select p.status into v_po_status from erp.production_orders p join erp.initial_import_production_sources s on s.po_id=p.id
   where s.opening_item_id=v_item for update of p;
  if v_po_status in('FINISHED','CANCELLED') then raise exception 'Buka kembali PO sebelum mengembalikan saldo BS';end if;
 end if;
 if v_item is not null then perform erp.sync_initial_import_bs_value_v1(v_item,v_date);end if;
 if tg_op='DELETE' then return old;end if;return new;
end;$function$;
revoke all on function erp.sync_initial_import_bs_disposition_v1() from public,anon,authenticated,service_role;
create or replace function erp.guard_initial_import_po_completion_v1() returns trigger
language plpgsql security definer set search_path='' as $function$
begin
 if new.status in('FINISHED','CANCELLED') and old.status is distinct from new.status and exists(
  select 1 from erp.initial_import_production_sources s where s.po_id=new.id and s.qty_pcs>
   case when s.bs_case_id is not null then coalesce((select sum(qty_pcs) from erp.bs_resolutions where bs_case_id=s.bs_case_id),0)
   else coalesce((select sum(o.qty_pcs) from erp.initial_import_wip_outputs o where o.opening_item_id=s.opening_item_id
      and not exists(select 1 from erp.initial_import_wip_output_reversals rv where rv.output_id=o.id)),0) end
 ) then raise exception 'PO masih memiliki WIP/BS saldo awal yang belum selesai';end if;
 return new;
end;$function$;
revoke all on function erp.guard_initial_import_po_completion_v1() from public,anon,authenticated,service_role;
create or replace function erp.complete_initial_import_wip_v1(p_payload jsonb) returns jsonb
language plpgsql security definer set search_path='' set DateStyle='ISO, YMD' as $function$
declare s erp.initial_import_production_sources%rowtype;i erp.opening_balance_items%rowtype;
 v_batch uuid;v_product uuid;v_location uuid;v_qty integer;v_remaining integer;v_lot uuid;v_output uuid;v_date date;v_at timestamptz;
 v_reason text;v_hpp numeric;v_prior record;v_movement uuid;v_po_status text;v_op text:=coalesce(p_payload->>'operation','COMPLETE');
begin
 perform erp.require_owner_admin();perform erp.require_permission('settings.erp.view');
 perform erp.pocket_period_lock_v1();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 v_batch:=(p_payload->>'batch_id')::uuid;v_reason:=nullif(btrim(p_payload->>'reason'),'');
 if v_reason is null then raise exception 'reason: catatan penyelesaian wajib diisi';end if;
 select * into s from erp.initial_import_production_sources where opening_item_id=(p_payload->>'opening_item_id')::uuid and batch_id=v_batch for update;
 if s.opening_item_id is null or s.bs_case_id is not null then raise exception 'Saldo fisik WIP tidak ditemukan';end if;
 select status into v_po_status from erp.production_orders where id=s.po_id for update;
 if v_po_status in('FINISHED','CANCELLED') then raise exception 'Buka kembali PO sebelum mengubah hasil WIP saldo awal';end if;
 select * into strict i from erp.opening_balance_items where id=s.opening_item_id;
 if i.balance_type<>'WIP' or not exists(select 1 from erp.opening_balance_headers where id=i.opening_id and status='POSTED')
   or not exists(select 1 from erp.migration_batches where id=v_batch and status='POSTED') then raise exception 'Saldo awal harus sudah disahkan';end if;
 select s.qty_pcs-coalesce(sum(o.qty_pcs),0) into v_remaining from erp.initial_import_wip_outputs o where o.opening_item_id=i.id
   and not exists(select 1 from erp.initial_import_wip_output_reversals rv where rv.output_id=o.id);
 if coalesce(p_payload->>'expected_remaining','') !~ '^[0-9]+$' or (p_payload->>'expected_remaining')::numeric<>v_remaining then
  raise exception 'STALE_VERSION: sisa WIP berubah, muat ulang';end if;
 perform set_config('app.change_reason',v_reason,true);
 if v_op='REVERSE' then
  select o.* into v_prior from erp.initial_import_wip_outputs o where o.id=(p_payload->>'output_id')::uuid and o.opening_item_id=i.id
    and not exists(select 1 from erp.initial_import_wip_output_reversals rv where rv.output_id=o.id) for update;
  if v_prior.id is null then raise exception 'Hasil WIP tidak ditemukan atau sudah dibatalkan';end if;
  if erp.fg_lot_has_active_downstream(v_prior.lot_id,'QC_GOOD','INITIAL_IMPORT_WIP',v_prior.id) then raise exception 'Hasil WIP masih dipakai transaksi lanjutan; batalkan transaksi tersebut dahulu';end if;
  if exists(select 1 from erp.contractor_accessory_reimbursement_entitlements where lot_id=v_prior.lot_id and payroll_status<>'UNALLOCATED') then raise exception 'Reimbursement sudah masuk payroll';end if;
  for v_movement in select id from erp.journal_entries where source_type='ACCESSORY_REIMBURSE_ACCRUAL' and source_id=v_prior.lot_id and status='POSTED' loop
   perform erp.reverse_journal(v_movement,v_reason);
  end loop;
  update erp.contractor_accessory_reimbursement_entitlements set payroll_status='CANCELLED' where lot_id=v_prior.lot_id and payroll_status='UNALLOCATED';
  for v_movement in select id from erp.fg_stock_movements where lot_id=v_prior.lot_id and source_type='INITIAL_IMPORT_WIP' and source_id=v_prior.id and movement_type='QC_GOOD'
   and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=erp.fg_stock_movements.id) loop
   perform erp.reverse_fg_movement(v_movement,v_reason);
  end loop;
  v_at:=statement_timestamp();v_date:=erp._cp3_business_date(v_at);
  insert into erp.initial_import_wip_output_reversals(output_id,reason,physical_at,created_by) values(v_prior.id,v_reason,v_at,erp.current_app_user_id());
  update erp.fg_lots set lot_origin='VOIDED_PRODUCTION',is_open=false where id=v_prior.lot_id;
  insert into erp.wip_stage_events(po_id,stage_from,stage_to,qty_pcs,contractor_id,source_type,source_id,physical_at,created_by,notes)
   values(s.po_id,'FINISHED',s.stage,v_prior.qty_pcs,i.contractor_id,'INITIAL_IMPORT_WIP_REVERSE',v_prior.id,v_at,erp.current_app_user_id(),v_reason);
  v_output:=v_prior.id;v_lot:=v_prior.lot_id;
 elsif v_op='COMPLETE' then
  if coalesce(p_payload->>'qty_pcs','') !~ '^[1-9][0-9]{0,9}$' or (p_payload->>'qty_pcs')::numeric>v_remaining then raise exception 'qty_pcs: jumlah harus bulat positif dan tidak melebihi sisa WIP';end if;
  v_qty:=(p_payload->>'qty_pcs')::integer;
  if coalesce(p_payload->>'date','') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'date: gunakan YYYY-MM-DD';end if;
  v_date:=(p_payload->>'date')::date;
  if v_date::text<>p_payload->>'date' or v_date<(select opening_date from erp.opening_balance_headers where id=i.opening_id)
    or v_date>erp._cp3_business_date(statement_timestamp()) then raise exception 'date: tanggal hasil harus sejak cutover dan tidak di masa depan';end if;
  select p.id into v_product from erp.products p join erp.production_orders po on po.id=s.po_id
    where p.sku=p_payload->>'product_sku' and p.is_active and p.model_id=po.model_id and p.size_id=s.size_id;
  if v_product is null then raise exception 'product_sku: pilih produk aktif dengan model PO dan ukuran saldo yang sama';end if;
  select id into v_location from erp.locations where location_code=p_payload->>'location_code' and is_active and location_type='FG_WAREHOUSE';
  if v_location is null then raise exception 'location_code: pilih gudang barang jadi aktif';end if;
  v_at:=erp.product_opening_physical_at(v_product,v_date);v_output:=gen_random_uuid();
  insert into erp.fg_lots(lot_number,po_id,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,is_open,lot_origin)
   values('OWIP-'||v_output::text,s.po_id,v_product,v_qty,0,v_at,true,'PRODUCTION') returning id into v_lot;
  insert into erp.initial_import_wip_outputs(id,opening_item_id,lot_id,qty_pcs,physical_at,reason,created_by)
   values(v_output,i.id,v_lot,v_qty,v_at,v_reason,erp.current_app_user_id());
  perform erp.post_fg_movement(v_product,v_lot,v_location,'GRADE_A','QC_GOOD',v_qty,0,null,'INITIAL_IMPORT_WIP',v_output,v_at,v_reason,false);
  perform erp.ensure_fg_accessory_cost_snapshot(v_lot);
  perform erp.post_accessory_reimbursement_accrual(v_lot);
  insert into erp.wip_stage_events(po_id,stage_from,stage_to,qty_pcs,contractor_id,source_type,source_id,physical_at,created_by,notes)
   values(s.po_id,s.stage,'FINISHED',v_qty,i.contractor_id,'INITIAL_IMPORT_WIP',v_output,v_at,erp.current_app_user_id(),v_reason);
 else raise exception 'Aksi hasil WIP tidak dikenal';end if;
 perform erp.rebuild_po_hpp(s.po_id,'Penyelesaian atau inverse WIP saldo awal');
 perform erp.propagate_conversion_hpp_for_po(s.po_id);
 perform erp.sync_po_hpp_to_gl(s.po_id,v_date);
 return jsonb_build_object('output_id',v_output,'lot_id',v_lot,'operation',v_op);
end;$function$;
revoke all on function erp.complete_initial_import_wip_v1(jsonb) from public,anon,authenticated,service_role;

create trigger initial_import_receipt_header_guard before insert or update or delete on erp.material_purchase_headers
 for each row execute function erp.guard_initial_import_receipt_header_v1();

create trigger trg_opening_cash_advance_deduction before insert or update or delete on erp.payroll_deductions
 for each row execute function erp.guard_opening_cash_advance_deduction_v1();
create trigger trg_opening_cash_advance_balance before update on erp.opening_subledger_balances
 for each row execute function erp.guard_opening_cash_advance_balance_v1();

create trigger initial_prepayment_immutable before update or delete on erp.initial_import_prepayments for each row execute function erp.guard_initial_prepayment_immutable_v1();
create trigger initial_prepayment_immutable before update or delete on erp.initial_import_prepayment_payments for each row execute function erp.guard_initial_prepayment_immutable_v1();
create trigger initial_prepayment_immutable before update or delete on erp.initial_import_prepayment_events for each row execute function erp.guard_initial_prepayment_immutable_v1();
create trigger initial_prepayment_payment_guard before insert or update or delete on erp.supplier_payments for each row execute function erp.guard_initial_prepayment_payment_v1();
create trigger initial_prepayment_payment_guard before insert or update or delete on erp.sales_payments for each row execute function erp.guard_initial_prepayment_payment_v1();
create trigger initial_prepayment_payment_guard before insert or update or delete on erp.vendor_payments for each row execute function erp.guard_initial_prepayment_payment_v1();
create trigger initial_prepayment_payment_guard before insert or update or delete on erp.opening_subledger_settlements for each row execute function erp.guard_initial_prepayment_payment_v1();
create trigger initial_prepayment_account_guard before update or delete on erp.chart_accounts
 for each row execute function erp.guard_initial_prepayment_account_v1();
create trigger initial_prepayment_cash_alias_guard before insert or update on erp.cash_accounts
 for each row execute function erp.guard_initial_prepayment_account_v1();
create trigger initial_prepayment_mapping_guard before insert or update on erp.accounting_account_mappings
 for each row execute function erp.guard_initial_prepayment_account_v1();


create trigger pocket_fabric_material_immutable before update or delete on erp.pocket_fabric_materials for each row execute function erp.guard_pocket_fabric_v1();
create trigger pocket_fabric_usage_immutable before update or delete on erp.pocket_fabric_usage for each row execute function erp.guard_pocket_fabric_v1();
create trigger pocket_fabric_cutting_guard before insert or update of roll_id on erp.cutting_group_rolls for each row execute function erp.guard_pocket_fabric_v1();
create trigger pocket_fabric_stock_inverse before insert on erp.material_stock_movements for each row execute function erp.guard_pocket_fabric_v1();

create trigger pocket_period_immutable before update or delete on erp.pocket_periods for each row execute function erp.guard_pocket_period_v1();
create trigger pocket_period_immutable before update or delete on erp.pocket_period_sources for each row execute function erp.guard_pocket_period_v1();
create trigger pocket_period_immutable before update or delete on erp.pocket_period_destinations for each row execute function erp.guard_pocket_period_v1();
create trigger pocket_period_immutable before update or delete on erp.pocket_period_events for each row execute function erp.guard_pocket_period_v1();
create trigger pocket_period_recost after insert on erp.material_adjustment_revaluation_facts for each row execute function erp.guard_pocket_period_v1();
create trigger pocket_period_new_source before insert on erp.pocket_fabric_usage for each row execute function erp.guard_pocket_period_v1();
create trigger pocket_period_stock_inverse before insert on erp.material_stock_movements for each row execute function erp.guard_pocket_period_v1();
create trigger pocket_period_sewing before insert on erp.sewing_terminal_events for each row execute function erp.guard_pocket_period_v1();
create trigger pocket_period_work_inverse before update of status on erp.work_completion_events for each row execute function erp.guard_pocket_period_v1();


create trigger initial_import_bs_disposition after insert or delete on erp.bs_resolutions
 for each row execute function erp.sync_initial_import_bs_disposition_v1();
create trigger initial_import_po_completion before update on erp.production_orders
 for each row execute function erp.guard_initial_import_po_completion_v1();

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
 if object_count<>7148 or fingerprint is distinct from '5c10671878a9e5630bf46e9a431cbb68b8a19c22130e8e3af29285d505d8ac20' then
  raise exception 'AP_INSTALLED_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
update erp.cp6_v2620ap_rollback_capsule c set installed_definition_sha256=encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'),'sha256'),'hex');
do $after_data$
declare v_table text;v_hash jsonb;v_after jsonb;v_preserved jsonb;
begin
 v_after:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620ap_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_after:=v_after||jsonb_build_object(v_table,v_hash);
 end loop;

 v_preserved:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620ap_rollback_capsule','initial_import_financial_sources','initial_import_opening_stock_sources','initial_import_receipt_headers','initial_import_receipt_lines','initial_import_prepayments','initial_import_prepayment_payments','initial_import_prepayment_events','pocket_fabric_materials','pocket_fabric_usage','pocket_fabric_execution_context','pocket_periods','pocket_period_sources','pocket_period_destinations','pocket_period_events','initial_import_production_sources','initial_import_cost_origins','initial_import_origin_cost_events','initial_import_wip_outputs','initial_import_bs_value_events','initial_import_wip_output_reversals']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t)-case %L when 'payroll_deductions' then array['opening_cash_advance_balance_id']::text[] else array[]::text[] end)::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table,v_table) into v_hash;
  v_preserved:=v_preserved||jsonb_build_object(v_table,v_hash);
 end loop;

 if v_preserved is distinct from (select boundary_snapshot->'before' from erp.cp6_v2620ap_rollback_capsule limit 1)
  or exists(select 1 from jsonb_each(v_after) where key=any(array['initial_import_financial_sources','initial_import_opening_stock_sources','initial_import_receipt_headers','initial_import_receipt_lines','initial_import_prepayments','initial_import_prepayment_payments','initial_import_prepayment_events','pocket_fabric_materials','pocket_fabric_usage','pocket_fabric_execution_context','pocket_periods','pocket_period_sources','pocket_period_destinations','pocket_period_events','initial_import_production_sources','initial_import_cost_origins','initial_import_origin_cost_events','initial_import_wip_outputs','initial_import_bs_value_events','initial_import_wip_output_reversals']::text[]) and (value->>'count')::bigint<>0)
  then raise exception 'AP_INSTALL_CHANGED_BUSINESS_DATA';end if;
 update erp.cp6_v2620ap_rollback_capsule set boundary_snapshot=boundary_snapshot||jsonb_build_object('after',v_after);
end $after_data$;
insert into erp.schema_migrations(version,description) values('v2.6.20ap','CP6 AP source-bound connected import, inventory and financial lifecycle package');
do $capsule_guard$
declare r record;c record;e jsonb;boundary jsonb;actual jsonb;expected jsonb;
begin
 if not exists(select 1 from pg_class where oid='erp.cp6_v2620ap_rollback_capsule'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
  or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='erp.cp6_v2620ap_rollback_capsule'::regclass and a.grantee<>p.relowner)
  or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='erp.cp6_v2620ap_rollback_capsule'::regclass and a.grantee<>'postgres'::regrole)
  or exists(select 1 from pg_policy where polrelid='erp.cp6_v2620ap_rollback_capsule'::regclass)
  or exists(select 1 from pg_trigger where tgrelid='erp.cp6_v2620ap_rollback_capsule'::regclass and not tgisinternal)
  or (select count(*) from erp.cp6_v2620ap_rollback_capsule)<>30 then raise exception 'AP_CAPSULE_SECURITY_OR_COUNT';end if;
 -- Match the complete visible column/constraint/index shape to the source-pinned
 -- AN template. Names of generated capsule indexes are intentionally immaterial.
 for r in select unnest(array['erp.cp6_v2620ap_rollback_capsule','erp.cp6_v2620an_rollback_capsule']) as rel loop
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel::regclass)) into actual;
  if expected is null then expected:=actual;elsif actual is distinct from expected then raise exception 'AP_CAPSULE_SHAPE_DRIFT';end if;
 end loop;
 select boundary_snapshot into boundary from erp.cp6_v2620ap_rollback_capsule limit 1;
 if boundary is null or exists(select 1 from erp.cp6_v2620ap_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before']) then raise exception 'AP_CAPSULE_BOUNDARY';end if;
 for r in select * from jsonb_each('{"erp._cp6_supplier_cent_state(uuid[])":{"acl":["postgres=X/postgres"],"identity":"erp._cp6_supplier_cent_state(uuid[])","installed_sha256":"3ece1106725d8d3b235f8e38723542a996819cf63b9b86472c640b6b7b67579b","owner":"postgres","predecessor_sha256":"19d43e3e32d94c6aaaf0acbb1f6e55946701fa10b9f53df7a990ea9375fad191"},"erp._validate_migration_batch_base(uuid)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp._validate_migration_batch_base(uuid)","installed_sha256":"ec62eb5d6f36c5d86eea64502cd3af2ca888b7d52e55d9110f05347990aff481","owner":"postgres","predecessor_sha256":"95c8b9493b8cfb5ee719b6bb6501836c42457302661f59857dbcfc761033a412"},"erp.apply_migration_master_rows(uuid)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.apply_migration_master_rows(uuid)","installed_sha256":"dec5ef651b4676f440c4aab55ce82cab2f9f0e0011bafc7a48c969ca6ba6ab5b","owner":"postgres","predecessor_sha256":"605407f1e9fa8c41bf768931c4b3b4e92646930005b48bb2b74ee46927016ef4"},"erp.approve_payroll(uuid)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.approve_payroll(uuid)","installed_sha256":"dbe465e385f37cb75dc6bd6c8ea96c42bf49c3a60a4760ff94aa2434e06262ff","owner":"postgres","predecessor_sha256":"f8b4f9138f846c5dd045564cf5a1a96783cd7bfb26edac01e4135bc6b94bd7e0"},"erp.compute_po_hpp_gl_book_v2620e(uuid)":{"acl":["postgres=X/postgres"],"identity":"erp.compute_po_hpp_gl_book_v2620e(uuid)","installed_sha256":"af5c69defb3b9a092ad5d551ba5e1cdc52aa4e0b3b6015f29732e1e3cf0e6975","owner":"postgres","predecessor_sha256":"a6bcb7af769d631f1ef715601f830c992b46a3f5002ee11a9507db4e878549e5"},"erp.ensure_fg_accessory_cost_snapshot(uuid)":{"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.ensure_fg_accessory_cost_snapshot(uuid)","installed_sha256":"1634377e32f56f4bab27232be686df6585aee54655953f93b1597ae912cb93bc","owner":"postgres","predecessor_sha256":"6dcaa27591993f471d4a366355c36a91879f478f5ba40d8b8b1b088e6f13a778"},"erp.finalize_migration_batch(uuid)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.finalize_migration_batch(uuid)","installed_sha256":"5ca1293383a7d8ec099c9153b343700420297c4db661f0785d7e29f80dff02ec","owner":"postgres","predecessor_sha256":"0c72dc6eda42a90a92d13845eb7e70d1ccf5c2e3efeda83d521728f2024e0022"},"erp.get_wip_control_v1(text,uuid,text,text)":{"acl":["postgres=X/postgres"],"identity":"erp.get_wip_control_v1(text,uuid,text,text)","installed_sha256":"83e417fc6fd01c37f5d7018ac2b735c4ef6c1c920d2925abbb92c8e94fea270c","owner":"postgres","predecessor_sha256":"d7708a6d51cfc0241f774e472b173650f1b3cb0a089667eee861f9bbe2aa56f4"},"erp.post_opening_balance(uuid)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.post_opening_balance(uuid)","installed_sha256":"8e13d9c07bfba22931e62591a968a6843358765e2350cfa6b9f38b76a8620f2b","owner":"postgres","predecessor_sha256":"16e667f49e6bb646d9a80cb30aa4080a0052b1ddc8bc760104c9c37c0e576d19"},"erp.post_opening_subledger_settlement(uuid)":{"acl":["authenticated=X/postgres","postgres=X/postgres"],"identity":"erp.post_opening_subledger_settlement(uuid)","installed_sha256":"8b26ff26a659da94006a9fb7dc564be78475776036de2bc6c5f4255c52f54ab8","owner":"postgres","predecessor_sha256":"2b9b0ca7dc3af6dee6327ccce58cf3255c4900f49b6c21a0b4e037493cad0d9b"},"erp.post_payroll_payment(uuid)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.post_payroll_payment(uuid)","installed_sha256":"d2c6b0dcdc2ecc162ade04b36c29fb76e18f02d84a4fe7c97ce99eb53d023876","owner":"postgres","predecessor_sha256":"6e81a5296b8b636fe33aa5a17bb5a2f4ee60a2d7698d92131c9616f1381f9a55"},"erp.post_sales_payment(uuid)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.post_sales_payment(uuid)","installed_sha256":"3b9c9cf72536abeeb199add1d269592d3cd1b2f8d38b2ee51d8a131fdac9bb4e","owner":"postgres","predecessor_sha256":"1f52492ffe261a903e31acf654c5fa1b3fe6e8b37268943c5b869f1a7c626447"},"erp.post_supplier_payment(uuid)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.post_supplier_payment(uuid)","installed_sha256":"c18615686da360b8483d8c3864a8b250baf88111109b3ffcc34ff54f3d9b30a8","owner":"postgres","predecessor_sha256":"ad780c4b00261b6ee1890391cac1c459c23d06b041859399e6ccc2f73d67f421"},"erp.post_vendor_payment(uuid)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.post_vendor_payment(uuid)","installed_sha256":"39e335ecef26dcf33c4954d1535a93e95899f4c3d97892e93f733e3eb9b9cce9","owner":"postgres","predecessor_sha256":"cf8c1105cb6426583464d7516eb70693c28d668702ae3eb23c22f4029f07f763"},"erp.prepare_migration_opening_balance(uuid,text)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.prepare_migration_opening_balance(uuid,text)","installed_sha256":"1ca3941a03a7d2eb39d1904547edc4b50e088d60ffbcb04215f8bf71a7d708a0","owner":"postgres","predecessor_sha256":"25dec082cc725d44b22283551a53d58b368714ab845f2f7daed807010305e90f"},"erp.rebuild_po_hpp(uuid,text)":{"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.rebuild_po_hpp(uuid,text)","installed_sha256":"eeff29d46ec555996e9b6d1506c049a8e61a42026e50d7a81982c449d1c0e25b","owner":"postgres","predecessor_sha256":"4e2e96017513d4990c9b2f8da2edf666b992ba016c8d688ea336daba36202d1f"},"erp.refresh_material_purchase_item_cost(uuid)":{"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.refresh_material_purchase_item_cost(uuid)","installed_sha256":"4f1acac2dd097219e6c328a1e4cb929eec5eddca7fbe63b91a28a3bf62811e75","owner":"postgres","predecessor_sha256":"de499b5baae66440960bb7689b36cb210f90ef1a98e64113a234975f4f01834f"},"erp.reverse_journal(uuid,text)":{"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.reverse_journal(uuid,text)","installed_sha256":"9c3b04353530df3c22e601e59927321714a186cecb026f7b08ff76c0ebb7e396","owner":"postgres","predecessor_sha256":"a6f635cd2319a68a1afa522fa4682921a6f7b80afd0e31fbdc4271cf53fcfef4"},"erp.reverse_opening_subledger_settlement(uuid,text)":{"acl":["authenticated=X/postgres","postgres=X/postgres"],"identity":"erp.reverse_opening_subledger_settlement(uuid,text)","installed_sha256":"18a76f83283b355cd0119c88a5fbcaf574373966d18832933a59f75788f40a30","owner":"postgres","predecessor_sha256":"3470bfe69619912700f05438a2bcf387145ba7ce886fed4476e2312b1510cfee"},"erp.reverse_paid_payroll(uuid,text)":{"acl":["authenticated=X/postgres","postgres=X/postgres"],"identity":"erp.reverse_paid_payroll(uuid,text)","installed_sha256":"1dc792b675aca5b2aa3f5dc9b5dd7a03effd5ac698aa3c2f1aec46bcdc13678b","owner":"postgres","predecessor_sha256":"083ba4a193c125fb51e08e5639c1d4783b73f6a92d426b5e7aadd61429aea149"},"erp.reverse_sales_payment(uuid,text)":{"acl":["authenticated=X/postgres","postgres=X/postgres"],"identity":"erp.reverse_sales_payment(uuid,text)","installed_sha256":"57397f698ad754aec50f623139a7024e6f07ac7f54581e208ab8cc418a0b5015","owner":"postgres","predecessor_sha256":"e5f48784389148a40b2f71fbe9a3e133ff9a7bc95ec969da74e27163b0c5b069"},"erp.reverse_supplier_payment(uuid,text)":{"acl":["authenticated=X/postgres","postgres=X/postgres"],"identity":"erp.reverse_supplier_payment(uuid,text)","installed_sha256":"d99aa18a8398d9ef1125185b2eef165d5dc6ad3608c956aa8d058e66d26363a1","owner":"postgres","predecessor_sha256":"9733b0e39d82732fb4b2ec7be17c66bcff2a088a81cccd25892eb440d4923102"},"erp.reverse_vendor_payment(uuid,text)":{"acl":["authenticated=X/postgres","postgres=X/postgres"],"identity":"erp.reverse_vendor_payment(uuid,text)","installed_sha256":"a7d822ab6e392cbcc6979d97eb8c47fd52a85e4b071f007d9827c30760640b31","owner":"postgres","predecessor_sha256":"f3bf7c7238f3e6068662ff7669c38713ae554cdba92dea948602d0874b105b03"},"erp.run_v267_financial_truth_checks()":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.run_v267_financial_truth_checks()","installed_sha256":"29fbe31e67e7792c711f4349e8382c9423c8409d1d764c3c8641789eb3007c81","owner":"postgres","predecessor_sha256":"7ead45b0a09258adcf1b9a9dae44b5627c2ba6fec36767f513706d282f076a9c"},"erp.run_v268_financial_report_checks()":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.run_v268_financial_report_checks()","installed_sha256":"ec0a83932270f8870d6ecff084c765791c49b6a6a3d1758edcbc36e24afc2793","owner":"postgres","predecessor_sha256":"bf10480574e90303e7a1bd70b29836a1ab2d4216fe1e7a030dece8e78b48561b"},"erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)","installed_sha256":"dd37b2af064e0ea4ad6abbbabc4d6863efc9b1e567db54690682ad4db080f967","owner":"postgres","predecessor_sha256":"153138b17d4993d583390e7e6d623d2abe3343741f8651a4007126d2cd75375c"},"erp.sync_material_purchase_grni_on_status()":{"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.sync_material_purchase_grni_on_status()","installed_sha256":"c509ce8cbaf2741c3c3a72271e8bae82835570093592e5d815a1139de123ee97","owner":"postgres","predecessor_sha256":"e39d7cc4b457a58b929894f4fd5a9c7f47aa0da678853a3ddbee65f9630d676c"},"erp.sync_opening_lot_hpp_to_gl(uuid,date)":{"acl":["postgres=X/postgres"],"identity":"erp.sync_opening_lot_hpp_to_gl(uuid,date)","installed_sha256":"854dda0fd4e9c902112fff34d8bee3e25876ba7908830562ce4f81a937181801","owner":"postgres","predecessor_sha256":"854dda0fd4e9c902112fff34d8bee3e25876ba7908830562ce4f81a937181801"},"erp.validate_material_supplier_invoice_line()":{"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.validate_material_supplier_invoice_line()","installed_sha256":"5b745d88b4a991799d385e663d6d0fedb5ad4546cab208aaa502f6744c6e6d47","owner":"postgres","predecessor_sha256":"6dd0e949d5cdeff4bc4fa340cba73aaed7282338bd189796a9ba80ff15bdee2d"},"erp.validate_supplier_return_source()":{"acl":["postgres=X/postgres"],"identity":"erp.validate_supplier_return_source()","installed_sha256":"7800e3577053bae4c35d0897eef071d6de36e255e56d25e28ba601e71a174378","owner":"postgres","predecessor_sha256":"d6fcd63c2605d4c9338aee18770aacaee96915714e4b7e2d67c58b70672b3415"}}'::jsonb) loop
  select * into c from erp.cp6_v2620ap_rollback_capsule where object_regidentity=r.key;e:=r.value;
  if c.object_regidentity is null or c.definition_sha256 is distinct from e->>'predecessor_sha256'
   or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex') is distinct from e->>'predecessor_sha256'
   or c.installed_definition_sha256 is distinct from e->>'installed_sha256'
   or c.owner_snapshot is distinct from e->>'owner' or to_jsonb(c.acl_snapshot) is distinct from e->'acl' then
   raise exception 'AP_CAPSULE_SOURCE_DRIFT: %',r.key;
  end if;
 end loop;
end $capsule_guard$;
commit;
