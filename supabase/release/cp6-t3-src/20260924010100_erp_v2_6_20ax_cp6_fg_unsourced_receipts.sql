-- CP6 AX: finished goods without a production source. Release candidate of the T3 combined package; closed, drained maintenance required.
begin;
-- Built by scripts/cp6_t3_awx_release.py from supabase/dev/cp6_ax_t1_family.sql (sha256 2427b901ce6991c1e36bf1b51e3e756d4d000ae39fe7608ad2888ce7b9e42503): the T1 body below is unchanged apart from the
-- ledger description; guards follow AO..AV. Capsule and catalog pins are placeholders until the T3 capture.
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
do $admission$ begin
 if exists(select 1 from erp.schema_migrations where version='v2.6.20ax') or to_regclass('erp.cp6_v2620ax_rollback_capsule') is not null
  or to_regclass('erp.fg_unsourced_receipts_v1') is not null or to_regclass('erp.fg_unsourced_repair_wages_v1') is not null
 then raise exception 'AX_EXACT_PREDECESSOR_WITHOUT_SUCCESSOR_REQUIRED';end if;
end $admission$;
do $predecessor$
begin
 if exists(select 1 from supabase_migrations.schema_migrations where version>'20260924010000') then raise exception 'AX_EXACT_PREDECESSOR_REQUIRED';end if;
end $predecessor$;
do $prior_platform$
declare r record;
begin
 for r in select * from jsonb_to_recordset('[{"marker":"v2.6.20ac","stamp":"20260915031500","name":"erp_v2_6_20ac_cp6_temporal_surface_closure","sha":"7b5690a2eddf618833d352dc75eb95aa1ef4dbcfb25d39b30374b733d33dadbc"},{"marker":"v2.6.20ad","stamp":"20260915113627","name":"erp_v2_6_20ad_cp6_opening_material_business_day","sha":"cd4879eb9b053e3b7a975e1430f481131e377f260ece2f19f07bfb4c98498c1d"},{"marker":"v2.6.20ae","stamp":"20260915201500","name":"erp_v2_6_20ae_cp6_opening_roll_integrity","sha":"228d9185501d418835e6434e64e1445be7b12ce2f517778ea63d789d478461c1"},{"marker":"v2.6.20af","stamp":"20260916014332","name":"erp_v2_6_20af_cp6_posted_child_integrity","sha":"54c5f73b99a2e63c858a777f669432f28260177daf4c45d806bb0e8a7c7c8e8e"},{"marker":"v2.6.20ag","stamp":"20260916050822","name":"erp_v2_6_20ag_cp6_sale_reservation_lineage","sha":"bff1d7d82917ce226ad0fb8823418fa14e497407d9659e125dc01ed5e2fd5944"},{"marker":"v2.6.20ah","stamp":"20260916070451","name":"erp_v2_6_20ah_cp6_return_allocation_eligibility","sha":"e5312744a2ef9ac53717c97e155fccf96a33e2f6a0c68c4b9c45f378ac538219"},{"marker":"v2.6.20ai","stamp":"20260916090022","name":"erp_v2_6_20ai_cp6_work_source_lineage","sha":"d3a604e53e599221afd46d1397e0d0660ebd8dc48db27113dfa63d3c3613a61c"},{"marker":"v2.6.20aj","stamp":"20260916202400","name":"erp_v2_6_20aj_cp6_rework_output_lineage","sha":"2e6cd4e94b52a27c83d2ba134a996c1db66a6f7ff617a5895f8c14769673f9ea"},{"marker":"v2.6.20ak","stamp":"20260917033516","name":"erp_v2_6_20ak_cp6_import_reference_preview","sha":"0d42825b2f2fcb38b9678fe1e6982b0c63290aac012b92be224f4323d495c536"},{"marker":"v2.6.20al","stamp":"20260917054049","name":"erp_v2_6_20al_cp6_opening_value_validation","sha":"74a5d5e14d79c7bbafa731aaf2fe1708bc575299600261f7412f1f7ea7323920"},{"marker":"v2.6.20am","stamp":"20260921214120","name":"erp_v2_6_20am_cp6_transfer_integrity","sha":"d5b155edb19aa8ca949036ba8a9cf67090478083c2e1ae6cc5bbf00b445716a5"},{"marker":"v2.6.20an","stamp":"20260921223438","name":"erp_v2_6_20an_cp6_cutting_selectors","sha":"21ac97ded4ed0cee9175c7fac7ef28ab6713d08b00766e1e5adc86bd38205e6c"},{"marker":"v2.6.20ao","stamp":"20260922135612","name":"erp_v2_6_20ao_cp6_invoice_retail","sha":"5687bb0236528d7e485e738ee2f96c2be0f4bde7e0d41c16bacee3a58183bdbb"},{"marker":"v2.6.20ap","stamp":"20260922135615","name":"erp_v2_6_20ap_cp6_connected_import_materials","sha":"fb8e14f0fd505edf730c0908f7e1c500cf850e29bcc0e90b3a51877224edd61b"},{"marker":"v2.6.20aq","stamp":"20260922161019","name":"erp_v2_6_20aq_cp6_accessory_lock_order","sha":"b1b4e449ca84ad524189640bcd76302cb277b9b690ed89f739ad5706e3cfac5a"},{"marker":"v2.6.20ar","stamp":"20260922185015","name":"erp_v2_6_20ar_cp6_opening_overlap","sha":"7da20a87d48493b4b64c10c395e8e54f87c1c40a835fbd09bbf2cdbc8866fa10"},{"marker":"v2.6.20as","stamp":"20260922210815","name":"erp_v2_6_20as_cp6_event_dates_product_identity","sha":"84e95211698eb2426995fd59d702bb42674f9fff675401be4861c9aa568cc1a8"},{"marker":"v2.6.20at","stamp":"20260923005153","name":"erp_v2_6_20at_cp6_wip_temporal_identity","sha":"f114a78918138a65f761488b77cadb1ab8a70ce6a6a88ae58a9d38656d1cfdb4"},{"marker":"v2.6.20au","stamp":"20260923045944","name":"erp_v2_6_20au_cp6_controlled_product_lifecycle","sha":"593b06092c2d47e03644afb1b7b5aef46c1442a56613f853a151b78ef738f2c2"},{"marker":"v2.6.20av","stamp":"20260923110000","name":"erp_v2_6_20av_cp6_identity_new_stock_cutoff","sha":"193e84efac8ead7cab681071e40070e1f9249f82cec1b7972f0576e8df25a2dc"},{"marker":"v2.6.20aw","stamp":"20260924010000","name":"erp_v2_6_20aw_cp6_close_readiness_engine","sha":"08826a25c14f8f18f5a168040b6f96dc4efe15c4498be5e92b0834601e77407c"}]'::jsonb) as x(marker text,stamp text,name text,sha text) loop
  if not exists(select 1 from erp.schema_migrations where version=r.marker)
   or (select count(*) from supabase_migrations.schema_migrations where name=r.name)<>1
   or not exists(select 1 from supabase_migrations.schema_migrations where version=r.stamp and name=r.name
    and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')=r.sha) then
   raise exception 'AX_PRIOR_PLATFORM_DRIFT: %',r.name;
  end if;
 end loop;
end $prior_platform$;
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule')
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
 if object_count<>0 or fingerprint is distinct from '0000000000000000000000000000000000000000000000000000000000000000' then
  raise exception 'AX_PREDECESSOR_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
do $historical_capsules$
declare r record;actual text;
begin
 for r in select * from jsonb_each_text('{"bs_resolution_v2619_rollback_capsule":"28ab388833da7da87384766ecaedadc66b4d048c303ee91e16f3939e34afdc39","bs_resolution_v2619a_rollback_capsule":"de8dfaab7b63b8742d383a089cdb05e73b629aad9f4df149e6a3c9fb590ef560","bs_resolution_v2619b_rollback_capsule":"d6d4f7457743d51679b5d25bf166ed69ca4b4f098cf5902ff985937531c2505d","bs_resolution_v2619c_rollback_capsule":"0207ba4f2ffba8ed61584709bbd884f1d2ee1a5981194fd7189a45afe8b3cbe1","cp3_r4_rollback_capsule":"7c01add62e66a4e2774a7199c2e77a04cca5e5942dbbba54d22cef720f82bc1d","cp45_v2617_rollback_capsule":"b9a43ce463de9905e94dd6538fd2a4952b0586a78c145f6f9d88aab7d6da3d80","cp45_v2617a_rollback_capsule":"b065dbcfdf1b59cb799e9f58caf6dd5ca7686e9f70826fce6a1ba8f140610022","cp4_v2616_rollback_capsule":"dde0a005dbe7cc93709bdfc6b961f4b9a76bf4db06fd7177d21dc79048af4d2f","cp6_v2620_rollback_capsule":"01f1e4e23211cff3c399d2d768a41be57980bfab00790715aa759b00a515e032","cp6_v2620a_rollback_capsule":"67befaaf327d2591e1ca1d654132ee483eba39b6cbb4f891c4719d817155d448","cp6_v2620aa_rollback_capsule":"eb0d6fb4fcac2ac06929d577101e604428e9a04821813c342e5b831147dc8948","cp6_v2620ab_rollback_capsule":"3be9a9166e3a607962be819fbe23d38fe455290a7a970dc2aad068079bf30785","cp6_v2620ac_relation_rollback_capsule":"2be5cbb62d1147e1e0d053dc4e447fe1d1258439352c297814c981c985959838","cp6_v2620ac_rollback_capsule":"51a8b08c9d96e66f03c2c8ba94ed3ed8fb15b26d1a2e4c65c58c614442dfa969","cp6_v2620ad_rollback_capsule":"5c3588109395b32ed743e0f4f5d789a3c59e3fffbab7469138f1f423c877ea9d","cp6_v2620ae_rollback_capsule":"6a75e02bf7b90c542fd9f2ac9534a2de066b047f5ffea65bffb1f83fa63c17f0","cp6_v2620af_rollback_capsule":"bfa89fc0e94d34b29405acedf551935f024942835f31cdc98f0f0983a9550288","cp6_v2620ag_rollback_capsule":"7ddfe6181f0c1c7439faf8a8150c542e958b3bafd8d18b5b2d1eb454fd7a85b7","cp6_v2620ah_rollback_capsule":"361be9321e5f4dadc7c7ec0e99ed746a98e7a4150178fc8355d23707c1507a93","cp6_v2620ai_rollback_capsule":"f2428dd712aa763b1379a4ae5b1a1e1e6ee175b355d8769b854a28f1355181c8","cp6_v2620aj_rollback_capsule":"8e24026dc90a2a92292c2cc6c8faa5fc3de991a19f326db494e0af2a518436f1","cp6_v2620ak_rollback_capsule":"dc7bfce7b9ee6a42e33cdf03cabd99d64435a4615245b2037fd6e4ee399aef10","cp6_v2620al_rollback_capsule":"c9e9aca042674efa5c6fa283e4b9ee47f3353ee9ee95b34e14ef1fd6b09bfde9","cp6_v2620am_rollback_capsule":"e781e631d06c6894c20b1fe6f9c65779f461d19c405c8ae74f28ed7d83ae6a26","cp6_v2620an_rollback_capsule":"ebfa8a281a32fe54babbdc209264ab422fde27f344d48561b90d2af022fe75b3","cp6_v2620ao_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620ap_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620aq_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620ar_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620as_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620at_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620au_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620av_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620aw_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620b_rollback_capsule":"f9bf784bff0c54e647f491e257a9649fd0c3e6f10c39ddfc0944c961b9dd7601","cp6_v2620c_rollback_capsule":"f88b1f5890ee8e7041758971bf9c9a3ce2bd0a7be6989fb95332c2dd7fa139aa","cp6_v2620d_rollback_capsule":"fa300c5554da4bb6812c61d726fd64f66329c97b085fa7d6ad5d0d8e5ae31235","cp6_v2620e_rollback_capsule":"143cd291cf4c12e78ab61e74e02ed03b08a48832a5064671868ff2bd2e3e1da7","cp6_v2620f_rollback_capsule":"076133b098e821fc2713af559618adf8aa3e204908f810af440fda355fc7a57f","cp6_v2620g_rollback_capsule":"ed9f4cacb47bd026ad6bdea373d1aa87044ed12aa60323cea453e3187dc488c4","cp6_v2620h_rollback_capsule":"4c25a060a2df3c22cd6fa9ff0b297163e223118a0d930b97bf1282b4756d909d","cp6_v2620i_rollback_capsule":"051203d95c44968abd8594f5bd48e289c4ac9a6c9fa49a89eee1086ad6b2c166","cp6_v2620j_rollback_capsule":"1393a8085d0f58717b13048c9cc3f7e9969ac86c351d6dfefdd2d4f43a735bd2","cp6_v2620k_rollback_capsule":"55aa71061f616ea11b361f0fabee2fd892f6438cc3f567cb9c135552ade42409","cp6_v2620l_rollback_capsule":"b4278768fce4ef307795953c14f607278c43bf474d76d3362e477280be08eb39","cp6_v2620m_rollback_capsule":"4b5f89d7bc4557f92b47716fe15640ab244c424fc1279433eb806d9d91d234e9","cp6_v2620n_rollback_capsule":"46e5ea4524613bb7a386551ada9e06888ea35eb987f9f5b864457fdd18bc3bc1","cp6_v2620o_rollback_capsule":"044e6b1a050df7e2a1d36082b0451877bda01116c08f611dfceb7a666bdf03c8","cp6_v2620p_rollback_capsule":"b656abaf23276984567c6c8d87b311427463c008b5ecd762fbdd0c2df13795df","cp6_v2620q_rollback_capsule":"ab6c992fbaa87f19a4eba696a57a3972f98504a354d9b5fc3be660939f8ea20f","cp6_v2620r_rollback_capsule":"8eb5e0a38284c5f8e3fee56618893ba72feaae9d26605c9ca3874dae25045297","cp6_v2620s_rollback_capsule":"fb57810a75f8829a038ed61b3a1cabde33dccf1e384661bc6723c51e28b3e132","cp6_v2620t_rollback_capsule":"348db4650d788750da243500b49e23c1130fdb70bc4a6d1fdf136bf68aa21f30","cp6_v2620u_rollback_capsule":"720eb1984548a3c381387fbe4d34e3c6f00334c8a4549eab7e398b827dcb7dd4","cp6_v2620v_rollback_capsule":"573ef5842eefadf1c32469514f4c8498667c99aec20ef20651406e4f419f5f60","cp6_v2620w_rollback_capsule":"f4e2ca1d577dd9f2724cc90693e8ee8bff36365c696575b69c6463f3e8ca0324","cp6_v2620x_rollback_capsule":"064db1068b56daa69e409ae582cd8a99490cea75d269154baa4217f90d3ca0d1","cp6_v2620y_rollback_capsule":"e3b23429a7f002c85ca8de1f8c632df13a4a2fc4e4654c12e2431c212772841d","cp6_v2620z_rollback_capsule":"ad0436a1480af43070e9861cb7e28d4cf55c435edbffb5fe368ca7babb7863ef","cutting_bridge_v2618_rollback_capsule":"535d1abd25668bc5bee79d82a602afe5efe4e8ce313bf1fb5170ae2004e3cb2d","cutting_bridge_v2618a_rollback_capsule":"db0608e690b3d936fa20b62cc4cfb9b1f9e86718212526eb6131562578b8bf60"}'::jsonb) loop
  execute format($caps$select encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to((to_jsonb(t)-array['captured_at','boundary_snapshot'])::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$caps$,r.key) into actual;
  if actual is distinct from r.value then raise exception 'AX_HISTORICAL_CAPSULE_DRIFT: %',r.key;end if;
 end loop;
end $historical_capsules$;
do $prior_capsules$
declare r record;expected jsonb;actual jsonb;bad bigint;
begin
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620an_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620an_rollback_capsule'::regclass)) into expected;
 for r in select unnest(array['erp.cp6_v2620ao_rollback_capsule','erp.cp6_v2620ap_rollback_capsule','erp.cp6_v2620aq_rollback_capsule','erp.cp6_v2620ar_rollback_capsule','erp.cp6_v2620as_rollback_capsule','erp.cp6_v2620at_rollback_capsule','erp.cp6_v2620au_rollback_capsule','erp.cp6_v2620av_rollback_capsule','erp.cp6_v2620aw_rollback_capsule']::regclass[]) as rel loop
  if not exists(select 1 from pg_class where oid=r.rel and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid=r.rel and a.grantee<>p.relowner)
   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid=r.rel and a.grantee<>'postgres'::regrole)
   or exists(select 1 from pg_policy where polrelid=r.rel)
   or exists(select 1 from pg_trigger where tgrelid=r.rel and not tgisinternal) then raise exception 'AX_PRIOR_CAPSULE_SECURITY: %',r.rel;end if;
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel)) into actual;
  if actual is distinct from expected then raise exception 'AX_PRIOR_CAPSULE_SHAPE_DRIFT: %',r.rel;end if;
  execute format($b$select count(*) filter(where boundary_snapshot is null or not(boundary_snapshot ?& array['before','after','platform_before','markers_before']))
   +(case when count(distinct boundary_snapshot)=1 then 0 else 1 end) from %s$b$,r.rel) into bad;
  if bad<>0 then raise exception 'AX_PRIOR_CAPSULE_BOUNDARY: %',r.rel;end if;
 end loop;
end $prior_capsules$;
create table erp.cp6_v2620ax_rollback_capsule(like erp.cp6_v2620an_rollback_capsule including all);
alter table erp.cp6_v2620ax_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620ax_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620ax_rollback_capsule(object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),i.identity,pg_get_functiondef(p.oid),
 encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
 array(select a::text from unnest(p.proacl)a order by a::text),pg_get_userbyid(p.proowner)
from unnest(array['erp.merge_eligible_work_into_payroll_v2(uuid,jsonb,uuid,bigint)','erp.validate_payroll_work_item_source()']) i(identity)
join pg_proc p on p.oid=i.identity::regprocedure join pg_namespace n on n.oid=p.pronamespace;
create temp table cp6_release_functions on commit drop as
select p.oid::regprocedure::text as identity,encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') as definition_sha256,
  array(select a::text from unnest(p.proacl)a order by a::text) as acl,pg_get_userbyid(p.proowner) as owner
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p');
do $before_data$ declare v_table text;v_hash jsonb;v_before jsonb; begin
 v_before:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620ax_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_before:=v_before||jsonb_build_object(v_table,v_hash);
 end loop;
 create temp table cp6_release_boundary on commit drop as select jsonb_build_object('before',v_before,
  'platform_before',(select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations t),
  'markers_before',(select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from erp.schema_migrations t)) snapshot;
end $before_data$;
set local lock_timeout='10s';set local statement_timeout='240s';set local search_path='';
do $t1_guard$
begin
 if (select count(*) from erp.schema_migrations where version in('v2.6.20av','v2.6.20aw'))<>2 then raise exception 'AX_T1_REQUIRES_AV_AND_AW'; end if;
 if exists(select 1 from erp.schema_migrations where version='v2.6.20ax') or to_regclass('erp.fg_unsourced_receipts_v1') is not null then raise exception 'AX_T1_ALREADY_INSTALLED'; end if;
end $t1_guard$;
create table erp.fg_unsourced_receipts_v1 (
  id uuid primary key default gen_random_uuid(),
  source_kind text not null check (source_kind in('FOUND_AT_OPNAME','GOOD_FROM_UNSOURCED_BS','REDYE_MIXED')),
  lot_id uuid not null unique references erp.fg_lots(id),
  bs_case_id uuid references erp.bs_cases(id),
  bs_resolution_id uuid,
  location_id uuid not null references erp.locations(id),
  quality_grade text not null,
  qty_pcs integer not null check (qty_pcs>0),
  physical_at timestamptz not null,
  unit_value numeric(18,2) not null check (unit_value>=0 and unit_value<>'NaN'::numeric),
  total_value numeric(20,2) not null check (total_value>=0 and total_value<>'NaN'::numeric),
  valuation jsonb not null check (valuation ? 'tier'),
  reason text not null check (length(btrim(reason))>0),
  status text not null default 'POSTED' check (status in('POSTED','REVERSED')),
  journal_entry_id uuid references erp.journal_entries(id),
  movement_id uuid not null,
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  reversed_by uuid,
  reversed_at timestamptz,
  reversal_reason text,
  check ((source_kind='GOOD_FROM_UNSOURCED_BS')=(bs_case_id is not null)),
  check ((status='REVERSED')=(reversed_at is not null))
);
alter table erp.fg_unsourced_receipts_v1 enable row level security;
revoke all on erp.fg_unsourced_receipts_v1 from public,anon,authenticated,service_role;
create index idx_fg_unsourced_receipts_v1_bs_case on erp.fg_unsourced_receipts_v1(bs_case_id) where bs_case_id is not null;
create table erp.fg_unsourced_repair_wages_v1 (
  id uuid primary key default gen_random_uuid(),
  receipt_id uuid not null unique references erp.fg_unsourced_receipts_v1(id),
  contractor_id uuid not null references erp.contractors(id),
  work_component_id uuid not null references erp.work_components(id),
  qty_pcs integer not null check (qty_pcs>0),
  rate_per_pcs numeric(18,2) not null check (rate_per_pcs>0 and rate_per_pcs<>'NaN'::numeric),
  amount numeric(20,2) not null check (amount>0 and amount<>'NaN'::numeric),
  physical_at timestamptz not null,
  rate_reason text not null check (length(btrim(rate_reason))>0),
  status text not null default 'POSTED' check (status in('POSTED','REVERSED')),
  created_at timestamptz not null default statement_timestamp(),
  reversed_at timestamptz,
  check (amount=round(qty_pcs::numeric*rate_per_pcs,2)),
  check ((status='REVERSED')=(reversed_at is not null))
);
alter table erp.fg_unsourced_repair_wages_v1 enable row level security;
revoke all on erp.fg_unsourced_repair_wages_v1 from public,anon,authenticated,service_role;
create index idx_fg_unsourced_repair_wages_v1_contractor on erp.fg_unsourced_repair_wages_v1(contractor_id) where status='POSTED';
CREATE OR REPLACE FUNCTION erp.guard_fg_unsourced_receipt_immutable_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
begin
  -- Only the reversal RPC may change a receipt, and only POSTED -> REVERSED with its reversal fields.
  if tg_op='UPDATE' and current_setting('erp.fg_unsourced_reversal',true)='on' and old.status='POSTED' and new.status='REVERSED'
     and (to_jsonb(new)-array['status','reversed_by','reversed_at','reversal_reason'])
       =(to_jsonb(old)-array['status','reversed_by','reversed_at','reversal_reason']) then
    return new;
  end if;
  raise exception 'FG_UNSOURCED_RECEIPT_IMMUTABLE: penerimaan barang tanpa sumber hanya bisa dibatalkan lewat RPC pembatalan';
end
$function$;
CREATE OR REPLACE FUNCTION erp.guard_bs_resolution_fg_unsourced_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
begin
  -- A BS resolution written by a POSTED AX receipt is part of that receipt: removing or changing it elsewhere (the BS
  -- workspace REVERSE_DISPOSITION) would reopen the case while the lot and its journal stay, and the same pieces could
  -- enter again. Only the AX reversal removes it, after the receipt has left POSTED.
  if exists(select 1 from erp.fg_unsourced_receipts_v1 r where r.bs_resolution_id=old.id and r.status='POSTED') then
    raise exception 'FG_UNSOURCED_BS_RESOLUTION_OWNED: resolusi BS ini dibuat penerimaan barang tanpa sumber; batalkan penerimaan itu lewat pembatalan AX';
  end if;
  return case when tg_op='DELETE' then old else new end;
end
$function$;
CREATE OR REPLACE FUNCTION erp.guard_fg_unsourced_repair_wage_immutable_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
begin
  -- A repair wage changes only with its receipt: the AX reversal turns POSTED into REVERSED and nothing else.
  if tg_op='UPDATE' and current_setting('erp.fg_unsourced_reversal',true)='on' and old.status='POSTED' and new.status='REVERSED'
     and (to_jsonb(new)-array['status','reversed_at'])=(to_jsonb(old)-array['status','reversed_at']) then
    return new;
  end if;
  raise exception 'FG_UNSOURCED_REPAIR_WAGE_IMMUTABLE: upah perbaikan hanya berubah lewat pembatalan penerimaan AX';
end
$function$;
CREATE OR REPLACE FUNCTION erp.fg_unsourced_valuation_v1(p_product_id uuid, p_physical_at timestamp with time zone)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
-- AX valuation (owner §15.1-FG, §19.2): average HPP per pcs at the physical instant, only for goods without an
-- origin value. Tiers stop at the first positive value: SKU (every version of the same identity) -> same model and
-- size, other colour -> same model -> owner input. Within a tier the stock on hand at the instant is weighted by
-- quantity (sum qty x current lot HPP / sum qty); with no stock on hand, lots produced up to the instant are weighted
-- by their initial quantity. Only production, opening, conversion and return lots count; unsourced (OTHER) and voided
-- lots never feed the average. Pieces reserved by a draft sale are still in the warehouse, so the draft reservation
-- (SALE_RESERVE, and the reversal that releases it) is not counted as an outflow; a posted sale turns the same row
-- into SALE and then counts (the ownership rule of compute_non_po_product_hpp_targets_v2620f). Each lot uses its
-- current (corrected) HPP: a later correction states the true cost of the same pieces, and the posting freezes the result. Pattern and fabric are not SKU attributes: they exist only through a SKU's own production lineage,
-- which already gives tier SKU a value, so they are reported as not available instead of guessed.
declare
  v_product erp.products%rowtype;
  v_tier text;
  r record;
begin
  if p_product_id is null or p_physical_at is null then raise exception 'FG_UNSOURCED_VALUATION_INPUT_REQUIRED'; end if;
  select * into v_product from erp.products where id=p_product_id;
  if v_product.id is null then raise exception 'FG_UNSOURCED_PRODUCT_NOT_FOUND'; end if;
  foreach v_tier in array array['SKU','MODEL_SIZE','MODEL'] loop
    if v_tier<>'SKU' and v_product.model_id is null then continue; end if;
    select sum(l.q) filter(where l.q>0) stock_qty,sum(l.q*l.hpp) filter(where l.q>0) stock_value,
      sum(l.initial_qty) produced_qty,sum(l.initial_qty*l.hpp) produced_value,
      coalesce(bool_or(l.cost_state='ESTIMATED'),false) has_estimated,
      to_jsonb((array_agg(jsonb_build_object('lot_id',l.id,'product_id',l.product_id,'qty_at_instant',l.q,
        'initial_qty',l.initial_qty,'hpp_per_pcs',l.hpp,'cost_state',l.cost_state) order by l.produced_at,l.id))[1:50]) lots
    into r
    from (
      select fl.id,fl.product_id,fl.produced_at,fl.initial_qty_pcs::numeric initial_qty,hv.hpp_per_pcs::numeric hpp,hv.cost_state,
        coalesce((select sum(m.qty_signed) from erp.fg_stock_movements m where m.lot_id=fl.id and m.physical_at<=p_physical_at
          and m.movement_type<>'SALE_RESERVE'
          and not exists(select 1 from erp.fg_stock_movements rm where rm.id=m.reversal_of_id and rm.movement_type='SALE_RESERVE')),0)::numeric q
      from erp.fg_lots fl
      join erp.products p on p.id=fl.product_id
      join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current
      where fl.lot_origin in('PRODUCTION','OPENING','CONVERSION','RETURN') and fl.produced_at<=p_physical_at
        and hv.hpp_per_pcs is not null
        and case v_tier when 'SKU' then coalesce(p.identity_root_id,p.id)=coalesce(v_product.identity_root_id,v_product.id)
                        when 'MODEL_SIZE' then p.model_id=v_product.model_id and p.size_id is not distinct from v_product.size_id
                        else p.model_id=v_product.model_id end
    ) l;
    if coalesce(r.stock_qty,0)>0 and round(r.stock_value/r.stock_qty,2)>0 then
      return jsonb_build_object('tier',v_tier,'method','STOCK_ON_HAND_WEIGHTED','unit_value',round(r.stock_value/r.stock_qty,2),
        'raw_average',r.stock_value/r.stock_qty,'basis_qty',r.stock_qty,'contains_estimated_hpp',r.has_estimated,
        'physical_at',p_physical_at,'pattern_fabric','NOT_AVAILABLE_WITHOUT_OWN_LINEAGE','lots',r.lots);
    elsif coalesce(r.produced_qty,0)>0 and round(r.produced_value/r.produced_qty,2)>0 then
      return jsonb_build_object('tier',v_tier,'method','PRODUCED_WEIGHTED','unit_value',round(r.produced_value/r.produced_qty,2),
        'raw_average',r.produced_value/r.produced_qty,'basis_qty',r.produced_qty,'contains_estimated_hpp',r.has_estimated,
        'physical_at',p_physical_at,'pattern_fabric','NOT_AVAILABLE_WITHOUT_OWN_LINEAGE','lots',r.lots);
    end if;
  end loop;
  return jsonb_build_object('tier','OWNER_INPUT_REQUIRED','method',null,'unit_value',null,'physical_at',p_physical_at,
    'reason','Tidak ada lot pembanding bernilai; owner wajib mengisi nilai per pcs dengan alasan (tidak pernah Rp0 otomatis).');
end
$function$;
CREATE OR REPLACE FUNCTION erp.post_fg_unsourced_receipt_v1(p_payload jsonb, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
-- AX (owner §15.1-FG, §19.2): finished goods entering without a production source: found at stock opname, GOOD from a
-- found (OUT_OF_NOWHERE) BS case, or a rare mixed re-dye. A new non-PO lot (origin OTHER) valued at the average HPP of
-- erp.fg_unsourced_valuation_v1 at the physical instant and frozen at posting; never Rp0 unless the owner enters it
-- with a reason. Journal Dr FG_INVENTORY (with product) / Cr OTHER_INCOME (without product, like the opening equity
-- side, so the non-PO HPP book stays equal to its target) on the physical date; post_journal moves the GL date into
-- the open period when that date is closed. GOOD from an ordinary BS stays on rework (decision 2A).
-- Repair wage (owner 24 Sep 2026, "Utang, dibayar via payroll"): GOOD repaired from a found BS may carry a wage per pcs
-- paid to a contractor. The lot value is the base value plus the wage (Rp52.000 + Rp2.000 = Rp54.000/pcs); the wage part
-- is credited to CONTRACTOR_PAYABLE (a debt) and reaches the contractor's payroll as a FG_REPAIR work line, paid by the
-- ordinary payroll payment. Without a repair wage the receipt is unchanged (a free repair keeps the base value).
declare
  v_kind text:=upper(nullif(btrim(p_payload->>'source_kind'),''));
  v_reason text:=nullif(btrim(p_payload->>'reason'),'');
  v_id uuid:=gen_random_uuid();
  v_hash text;v_cached jsonb;
  v_product uuid;v_location uuid;v_grade text;v_qty numeric;v_at timestamptz;
  v_bs erp.bs_cases%rowtype;v_open bigint;v_in_rework bigint;v_root uuid;v_override numeric;v_override_text text;
  v_valuation jsonb;v_unit numeric(18,2);v_total numeric(20,2);
  v_lot uuid;v_movement uuid;v_journal uuid;v_resolution uuid;
  v_repair jsonb:=p_payload->'repair';v_rate numeric;v_contractor uuid;v_component uuid;v_rate_reason text;
  v_base numeric(18,2);v_wage numeric(20,2):=0;v_wage_id uuid;v_lines jsonb;
begin
  perform erp.require_owner_admin();
  if p_client_request_id is null then raise exception 'FG_UNSOURCED_REQUEST_ID_REQUIRED'; end if;
  if v_reason is null then raise exception 'FG_UNSOURCED_REASON_REQUIRED'; end if;
  if v_kind is null or v_kind not in('FOUND_AT_OPNAME','GOOD_FROM_UNSOURCED_BS','REDYE_MIXED') then
    raise exception 'FG_UNSOURCED_KIND_INVALID';
  end if;
  v_hash:=erp._request_hash(p_payload);
  v_cached:=erp._idempotency_begin('post_fg_unsourced_receipt_v1',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  -- Numbers: whole positive pieces; an owner value is a finite, non-negative amount with at most two decimals.
  begin v_qty:=(p_payload->>'qty_pcs')::numeric;
  exception when others then raise exception 'FG_UNSOURCED_QTY_INVALID'; end;
  if v_qty is null or v_qty='NaN'::numeric or v_qty<=0 or v_qty>2147483647 or v_qty<>trunc(v_qty) then
    raise exception 'FG_UNSOURCED_QTY_INVALID';
  end if;
  v_override_text:=nullif(btrim(p_payload->>'owner_unit_value'),'');
  if v_override_text is not null then
    begin v_override:=v_override_text::numeric;
    exception when others then raise exception 'FG_UNSOURCED_VALUE_INVALID'; end;
    -- Storage bound: lot HPP per pcs and movement unit HPP are numeric(18,6), so a unit value stays below 1e12.
    if v_override='NaN'::numeric or v_override<0 or v_override>=1000000000000::numeric or v_override<>round(v_override,2) then
      raise exception 'FG_UNSOURCED_VALUE_INVALID';
    end if;
    if nullif(btrim(p_payload->>'owner_value_reason'),'') is null then raise exception 'FG_UNSOURCED_VALUE_REASON_REQUIRED'; end if;
  end if;
  begin v_at:=(p_payload->>'physical_at')::timestamptz;
  exception when others then raise exception 'FG_UNSOURCED_PHYSICAL_AT_INVALID'; end;
  if v_at is null or not isfinite(v_at) then raise exception 'FG_UNSOURCED_PHYSICAL_AT_INVALID'; end if;
  if v_at>statement_timestamp()+interval '5 minutes' then raise exception 'FG_UNSOURCED_PHYSICAL_AT_FUTURE'; end if;
  begin
    v_location:=(p_payload->>'location_id')::uuid;
    v_product:=(p_payload->>'product_id')::uuid;
  exception when others then raise exception 'FG_UNSOURCED_REFERENCE_INVALID'; end;
  v_grade:=coalesce(nullif(btrim(p_payload->>'quality_grade'),''),'GRADE_A');
  -- GOOD goods only: reservations, sales and conversions handle GRADE_A stock, anything else could never leave.
  if v_grade<>'GRADE_A' then raise exception 'FG_UNSOURCED_GRADE_INVALID: barang masuk lewat jalur ini harus GRADE_A'; end if;
  -- One lock order with every FG posting (sale, adjustment, conversion, reversal): the FG/HPP advisory lock first,
  -- then rows; the reversal holds this lock before its BS trigger locks the case.
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));

  if v_kind='GOOD_FROM_UNSOURCED_BS' then
    select * into v_bs from erp.bs_cases where id=(p_payload->>'bs_case_id')::uuid for update;
    if v_bs.id is null then raise exception 'FG_UNSOURCED_BS_NOT_FOUND'; end if;
    if not exists(select 1 from erp.bs_case_manual_origins_v1 o where o.bs_case_id=v_bs.id and o.origin_type='OUT_OF_NOWHERE') then
      raise exception 'FG_UNSOURCED_BS_HAS_ORIGIN_VALUE: GOOD dari BS biasa memakai rework (2A)';
    end if;
    if v_bs.status in('RESOLVED','SCRAPPED','WRITTEN_OFF','CANCELLED','ON_HOLD') then
      raise exception 'FG_UNSOURCED_BS_NOT_OPEN: status %',v_bs.status;
    end if;
    -- GOOD is new stock at its own physical instant (decision 1C): it takes the version of the BS product's identity
    -- that is in force then, which may be a successor started after the BS was found.
    select coalesce(p.identity_root_id,p.id) into v_root from erp.products p where p.id=v_bs.product_id;
    if v_root is null then raise exception 'FG_UNSOURCED_BS_PRODUCT_MISMATCH'; end if;
    if v_product is null then
      select p.id into v_product from erp.products p
      where coalesce(p.identity_root_id,p.id)=v_root and p.effective_from<=v_at and (p.effective_to is null or v_at<p.effective_to)
      order by p.effective_from desc,p.id limit 1;
      v_product:=coalesce(v_product,v_bs.product_id);
    elsif not exists(select 1 from erp.products p where p.id=v_product and coalesce(p.identity_root_id,p.id)=v_root) then
      raise exception 'FG_UNSOURCED_BS_PRODUCT_MISMATCH';
    end if;
    -- Same availability rule as the platform's disposition and rework guards: pieces out at an active rework order
    -- are not available.
    select coalesce(sum(r.qty_pcs),0) into v_open from erp.bs_resolutions r where r.bs_case_id=v_bs.id;
    select coalesce(sum(ro.qty_sent),0) into v_in_rework from erp.rework_orders ro
      where ro.bs_case_id=v_bs.id and ro.status in('OPEN','IN_PROGRESS','PARTIAL');
    v_open:=greatest(v_bs.qty_pcs-v_open-v_in_rework,0);
    if v_qty>v_open then raise exception 'FG_UNSOURCED_BS_QTY_EXCEEDS_OPEN: % > %',v_qty,v_open; end if;
    if v_at<v_bs.physical_at then raise exception 'FG_UNSOURCED_BEFORE_BS_FOUND'; end if;
  elsif nullif(p_payload->>'bs_case_id','') is not null then
    raise exception 'FG_UNSOURCED_BS_ONLY_FOR_GOOD_FROM_BS';
  end if;
  if v_product is null then raise exception 'FG_UNSOURCED_PRODUCT_REQUIRED'; end if;
  if v_location is null then raise exception 'FG_UNSOURCED_LOCATION_REQUIRED'; end if;
  if v_repair is not null and jsonb_typeof(v_repair)<>'null' then
    if v_kind<>'GOOD_FROM_UNSOURCED_BS' then
      raise exception 'FG_UNSOURCED_REPAIR_ONLY_FOR_FOUND_BS: upah perbaikan hanya untuk GOOD dari BS temuan';
    end if;
    if jsonb_typeof(v_repair)<>'object' then raise exception 'FG_UNSOURCED_REPAIR_INVALID'; end if;
    begin
      v_rate:=(v_repair->>'rate_per_pcs')::numeric;
      v_contractor:=(v_repair->>'contractor_id')::uuid;
      v_component:=(v_repair->>'work_component_id')::uuid;
    exception when others then raise exception 'FG_UNSOURCED_REPAIR_INVALID'; end;
    v_rate_reason:=nullif(btrim(v_repair->>'rate_reason'),'');
    -- A paid repair has a wage above zero (a free repair sends no repair object); same bounds as a unit value.
    if v_rate is null or v_rate='NaN'::numeric or v_rate<=0 or v_rate>=1000000000000::numeric or v_rate<>round(v_rate,2) then
      raise exception 'FG_UNSOURCED_REPAIR_RATE_INVALID';
    end if;
    if v_rate_reason is null then raise exception 'FG_UNSOURCED_REPAIR_REASON_REQUIRED'; end if;
    if v_contractor is null or not exists(select 1 from erp.contractors c where c.id=v_contractor and c.is_active) then
      raise exception 'FG_UNSOURCED_REPAIR_CONTRACTOR_INVALID';
    end if;
    if v_component is null or not exists(select 1 from erp.work_components w where w.id=v_component and w.is_active) then
      raise exception 'FG_UNSOURCED_REPAIR_COMPONENT_INVALID';
    end if;
  end if;

  -- The SKU version must be active at the physical instant (NEW_STOCK, owner decision 1C).
  perform erp.assert_product_identity_time(v_product,v_at,'NEW_STOCK');
  perform erp.assert_non_po_product_hpp_target_book_v2620f(v_product);

  v_valuation:=erp.fg_unsourced_valuation_v1(v_product,v_at);
  -- Owner decision: the average is the value whenever a reference exists; an owner value is only the last tier.
  if v_override is not null and v_valuation->>'tier'<>'OWNER_INPUT_REQUIRED' then
    raise exception using message='FG_UNSOURCED_OWNER_VALUE_NOT_ALLOWED: ada pembanding HPP; nilai mengikuti rata-rata pada tanggal fisik',
      detail=v_valuation::text;
  end if;
  if v_override is not null then
    v_valuation:=jsonb_build_object('tier','OWNER_VALUE','unit_value',v_override,
      'owner_value_reason',btrim(p_payload->>'owner_value_reason'),'computed',v_valuation);
  elsif v_valuation->>'tier'='OWNER_INPUT_REQUIRED' then
    raise exception using message='FG_UNSOURCED_VALUE_REQUIRED: tidak ada pembanding HPP; owner wajib mengisi nilai per pcs dengan alasan',
      detail=v_valuation::text;
  end if;
  v_unit:=(v_valuation->>'unit_value')::numeric;
  if v_rate is not null then
    v_base:=v_unit;v_unit:=v_base+v_rate;
    if v_unit>=1000000000000::numeric then raise exception 'FG_UNSOURCED_VALUE_INVALID: nilai per pcs melebihi batas penyimpanan'; end if;
    v_valuation:=v_valuation||jsonb_build_object('base_unit_value',v_base,'repair_wage_per_pcs',v_rate,'unit_value',v_unit,
      'repair_contractor_id',v_contractor,'repair_work_component_id',v_component,'repair_rate_reason',v_rate_reason);
    v_wage:=round(v_rate*v_qty,2);
  end if;
  if v_unit*v_qty>=1000000000000000000::numeric then raise exception 'FG_UNSOURCED_VALUE_INVALID: total melebihi batas penyimpanan'; end if;
  v_total:=round(v_unit*v_qty,2);

  insert into erp.fg_lots(lot_number,po_id,qc_item_id,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,is_open,lot_origin)
  values('AX-'||to_char(v_at at time zone 'Asia/Jakarta','YYYYMMDD')||'-'||substr(v_id::text,1,8),null,null,v_product,
    v_qty::integer,0,v_at,true,'OTHER')
  returning id into v_lot;
  insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,calculation_reason,created_by)
  values(v_lot,1,'ADJUSTED',v_qty::integer,v_total,true,
    'Unsourced FG valued at '||(v_valuation->>'tier')||' average HPP'
      ||case when v_rate is not null then ' plus repair wage '||v_rate||' per pcs' else '' end||'; frozen at posting',erp.current_app_user_id());
  v_movement:=erp.post_fg_movement(v_product,v_lot,v_location,v_grade,'ADJUSTMENT',v_qty::integer,v_unit,null,
    'FG_UNSOURCED_RECEIPT',v_id,v_at,'Barang jadi tanpa sumber produksi: '||v_kind,false);
  if v_total>0 then
    v_lines:=jsonb_build_array(jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_total,'credit',0,'product_id',v_product));
    if v_total-v_wage>0 then
      v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',v_total-v_wage));
    end if;
    if v_wage>0 then
      v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',v_wage,
        'contractor_id',v_contractor));
    end if;
    v_journal:=erp.post_journal('FG_UNSOURCED_RECEIPT',v_id,(v_at at time zone 'Asia/Jakarta')::date,
      'Barang jadi tanpa sumber produksi · '||v_reason,v_lines);
  end if;
  if v_kind='GOOD_FROM_UNSOURCED_BS' then
    insert into erp.bs_resolutions(bs_case_id,resolution_type,qty_pcs,compensation_amount,physical_at,notes)
    values(v_bs.id,'OTHER',v_qty::integer,0,v_at,'GOOD dari BS temuan, penerimaan '||v_id)
    returning id into v_resolution;
    perform erp.refresh_bs_case_status(v_bs.id);
  end if;
  insert into erp.fg_unsourced_receipts_v1(id,source_kind,lot_id,bs_case_id,bs_resolution_id,location_id,quality_grade,qty_pcs,
    physical_at,unit_value,total_value,valuation,reason,journal_entry_id,movement_id,created_by)
  values(v_id,v_kind,v_lot,v_bs.id,v_resolution,v_location,v_grade,v_qty::integer,v_at,v_unit,v_total,v_valuation,v_reason,
    v_journal,v_movement,erp.current_app_user_id());
  if v_rate is not null then
    insert into erp.fg_unsourced_repair_wages_v1(receipt_id,contractor_id,work_component_id,qty_pcs,rate_per_pcs,amount,physical_at,rate_reason)
    values(v_id,v_contractor,v_component,v_qty::integer,v_rate,v_wage,v_at,v_rate_reason)
    returning id into v_wage_id;
  end if;
  perform erp.assert_non_po_product_hpp_target_book_v2620f(v_product);
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('fg_unsourced_receipts_v1',v_id,'POST',erp.current_app_user_id(),v_reason);
  return erp._idempotency_complete('post_fg_unsourced_receipt_v1',p_client_request_id,jsonb_build_object(
    'receipt_id',v_id,'lot_id',v_lot,'product_id',v_product,'source_kind',v_kind,'qty_pcs',v_qty::integer,
    'unit_value',v_unit,'total_value',v_total,'valuation',v_valuation,'journal_entry_id',v_journal,
    'bs_resolution_id',v_resolution,'repair_wage',case when v_wage_id is null then null else jsonb_build_object(
      'wage_id',v_wage_id,'contractor_id',v_contractor,'work_component_id',v_component,'rate_per_pcs',v_rate,'amount',v_wage) end));
end
$function$;
CREATE OR REPLACE FUNCTION erp.reverse_fg_unsourced_receipt_v1(p_receipt_id uuid, p_reason text, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
-- AX reversal: allowed only while the lot has no downstream use (sale, reservation, conversion). The inflow is
-- reversed, the lot is voided (it leaves the non-PO HPP target), the journal is reversed and a BS resolution created
-- by the receipt is removed, so the found BS is open again. A repair wage that a payroll (not reversed) has taken blocks
-- the reversal until that payroll is cancelled; otherwise the wage is reversed with the receipt (the one journal reversal
-- also reverses its CONTRACTOR_PAYABLE credit).
declare
  v erp.fg_unsourced_receipts_v1%rowtype;
  v_product uuid;v_hash text;v_cached jsonb;v_reversal uuid;
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_reason),'') is null then raise exception 'FG_UNSOURCED_REVERSAL_REASON_REQUIRED'; end if;
  if p_client_request_id is null then raise exception 'FG_UNSOURCED_REQUEST_ID_REQUIRED'; end if;
  v_hash:=erp._request_hash(jsonb_build_object('receipt_id',p_receipt_id,'reason',btrim(p_reason)));
  v_cached:=erp._idempotency_begin('reverse_fg_unsourced_receipt_v1',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',btrim(p_reason),true);
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into v from erp.fg_unsourced_receipts_v1 where id=p_receipt_id for update;
  if v.id is null then raise exception 'FG_UNSOURCED_RECEIPT_NOT_FOUND'; end if;
  if v.status<>'POSTED' then raise exception 'FG_UNSOURCED_RECEIPT_ALREADY_REVERSED'; end if;
  select product_id into v_product from erp.fg_lots where id=v.lot_id for update;
  if erp.fg_lot_has_active_downstream(v.lot_id,'ADJUSTMENT','FG_UNSOURCED_RECEIPT',v.id) then
    raise exception 'FG_UNSOURCED_LOT_IN_USE: lot sudah dipakai transaksi lain; batalkan transaksi itu lebih dulu';
  end if;
  perform 1 from erp.fg_unsourced_repair_wages_v1 w where w.receipt_id=v.id for update;
  if exists(select 1 from erp.fg_unsourced_repair_wages_v1 w
      join erp.payroll_work_items pwi on pwi.source_type='FG_REPAIR' and pwi.source_id=w.id
      join erp.payroll_settlements ps on ps.id=pwi.payroll_id
      where w.receipt_id=v.id and ps.status<>'REVERSED') then
    raise exception 'FG_UNSOURCED_REPAIR_WAGE_IN_PAYROLL: upah perbaikan sudah masuk payroll; batalkan payroll itu lebih dulu';
  end if;
  perform erp.reverse_fg_movement(v.movement_id,btrim(p_reason));
  update erp.fg_lots set lot_origin='VOIDED_PRODUCTION',is_open=false where id=v.lot_id;
  if v.journal_entry_id is not null then v_reversal:=erp.reverse_journal(v.journal_entry_id,btrim(p_reason)); end if;
  perform set_config('erp.fg_unsourced_reversal','on',true);
  update erp.fg_unsourced_receipts_v1 set status='REVERSED',reversed_by=erp.current_app_user_id(),
    reversed_at=clock_timestamp(),reversal_reason=btrim(p_reason) where id=v.id;
  update erp.fg_unsourced_repair_wages_v1 set status='REVERSED',reversed_at=clock_timestamp() where receipt_id=v.id and status='POSTED';
  perform set_config('erp.fg_unsourced_reversal','off',true);
  if v.bs_resolution_id is not null then
    delete from erp.bs_resolutions where id=v.bs_resolution_id;
    if not found then raise exception 'FG_UNSOURCED_BS_RESOLUTION_MISSING: resolusi BS penerimaan ini sudah tidak ada'; end if;
    perform erp.refresh_bs_case_status(v.bs_case_id);
  end if;
  perform erp.assert_non_po_product_hpp_target_book_v2620f(v_product);
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('fg_unsourced_receipts_v1',v.id,'REVERSE',erp.current_app_user_id(),btrim(p_reason));
  return erp._idempotency_complete('reverse_fg_unsourced_receipt_v1',p_client_request_id,jsonb_build_object(
    'receipt_id',v.id,'status','REVERSED','lot_id',v.lot_id,'reversal_journal_entry_id',v_reversal));
end
$function$;
CREATE OR REPLACE FUNCTION public.erp_preview_fg_unsourced_value_v1(p_product_id uuid, p_physical_at timestamp with time zone)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
begin
  perform erp.require_owner_admin();
  return erp.fg_unsourced_valuation_v1(p_product_id,p_physical_at);
end
$function$;
CREATE OR REPLACE FUNCTION public.erp_post_fg_unsourced_receipt_v1(p_payload jsonb, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
 select erp.post_fg_unsourced_receipt_v1(p_payload,p_client_request_id);
$function$;
CREATE OR REPLACE FUNCTION public.erp_reverse_fg_unsourced_receipt_v1(p_receipt_id uuid, p_reason text, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
 select erp.reverse_fg_unsourced_receipt_v1(p_receipt_id,p_reason,p_client_request_id);
$function$;
alter table erp.payroll_work_items drop constraint payroll_work_items_source_type_check;
alter table erp.payroll_work_items add constraint payroll_work_items_source_type_check CHECK (source_type::text = ANY (ARRAY['PRODUCTION'::text, 'REWORK'::text, 'FG_REPAIR'::text]));
create or replace view "erp"."v_payroll_eligible_work_lines" with (security_invoker=true) as
 SELECT 'PRODUCTION'::text AS source_type,
    p.source_id,
    p.contractor_id,
    p.po_id,
    p.cutting_group_id,
    NULL::uuid AS bs_case_id,
    p.work_component_id,
    p.physical_at AS eligible_at,
    p.source_qty_payable AS source_qty,
    p.eligible_after_laundry_qty AS eligible_qty,
    p.allocated_to_nonreversed_payroll_qty AS allocated_qty,
    p.remaining_eligible_qty AS remaining_qty,
    p.held_for_laundry_qty AS held_qty,
    p.rate_snapshot,
    p.remaining_eligible_amount AS remaining_amount,
    p.eligibility_state AS eligibility_reason
   FROM erp.v_payroll_production_work_eligibility p
  WHERE p.remaining_eligible_qty > 0
UNION ALL
 SELECT 'REWORK'::text AS source_type,
    rcl.id AS source_id,
    ro.contractor_id,
    bc.po_id,
    bc.cutting_group_id,
    bc.id AS bs_case_id,
    bcc.work_component_id,
    COALESCE(ro.completed_at, ro.physical_sent_at) AS eligible_at,
    rcl.qty_newly_payable AS source_qty,
    rcl.qty_newly_payable AS eligible_qty,
    COALESCE(a.allocated_qty, 0) AS allocated_qty,
    GREATEST(rcl.qty_newly_payable - COALESCE(a.allocated_qty, 0), 0) AS remaining_qty,
    0 AS held_qty,
    rcl.rate_snapshot,
    round(GREATEST(rcl.qty_newly_payable - COALESCE(a.allocated_qty, 0), 0)::numeric * rcl.rate_snapshot, 2) AS remaining_amount,
    'BS_CASE_RESOLVED'::text AS eligibility_reason
   FROM erp.rework_component_lines rcl
     JOIN erp.rework_orders ro ON ro.id = rcl.rework_order_id
     JOIN erp.bs_case_components bcc ON bcc.id = rcl.bs_case_component_id
     JOIN erp.bs_cases bc ON bc.id = bcc.bs_case_id
     LEFT JOIN LATERAL ( SELECT sum(pwi.qty_payable)::integer AS allocated_qty
           FROM erp.payroll_work_items pwi
             JOIN erp.payroll_settlements ps ON ps.id = pwi.payroll_id
          WHERE pwi.source_type::text = 'REWORK'::text AND pwi.source_id = rcl.id AND ps.status::text <> 'REVERSED'::text) a ON true
  WHERE ro.destination_type::text = 'CONTRACTOR'::text AND ro.status::text = 'COMPLETED'::text AND ro.cost_posted AND bc.status::text = 'RESOLVED'::text AND GREATEST(rcl.qty_newly_payable - COALESCE(a.allocated_qty, 0), 0) > 0
UNION ALL
 SELECT 'FG_REPAIR'::text AS source_type,
    w.id AS source_id,
    w.contractor_id,
    NULL::uuid AS po_id,
    NULL::uuid AS cutting_group_id,
    r.bs_case_id,
    w.work_component_id,
    w.physical_at AS eligible_at,
    w.qty_pcs AS source_qty,
    w.qty_pcs AS eligible_qty,
    COALESCE(a.allocated_qty, 0) AS allocated_qty,
    GREATEST(w.qty_pcs - COALESCE(a.allocated_qty, 0), 0) AS remaining_qty,
    0 AS held_qty,
    w.rate_per_pcs AS rate_snapshot,
    round(GREATEST(w.qty_pcs - COALESCE(a.allocated_qty, 0), 0)::numeric * w.rate_per_pcs, 2) AS remaining_amount,
    'FG_UNSOURCED_REPAIR_POSTED'::text AS eligibility_reason
   FROM erp.fg_unsourced_repair_wages_v1 w
     JOIN erp.fg_unsourced_receipts_v1 r ON r.id = w.receipt_id
     LEFT JOIN LATERAL ( SELECT sum(pwi.qty_payable)::integer AS allocated_qty
           FROM erp.payroll_work_items pwi
             JOIN erp.payroll_settlements ps ON ps.id = pwi.payroll_id
          WHERE pwi.source_type::text = 'FG_REPAIR'::text AND pwi.source_id = w.id AND ps.status::text <> 'REVERSED'::text) a ON true
  WHERE w.status = 'POSTED'::text AND r.status = 'POSTED'::text AND GREATEST(w.qty_pcs - COALESCE(a.allocated_qty, 0), 0) > 0;
CREATE OR REPLACE FUNCTION erp.validate_payroll_work_item_source()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_source_qty integer;
  v_source_component uuid;
  v_source_po uuid;
  v_source_contractor uuid;
  v_payroll_contractor uuid;
  v_already integer;
begin
  perform pg_advisory_xact_lock(hashtextextended(
    'PAYWORK|'||new.source_type||'|'||new.source_id::text||'|'||new.work_component_id::text,0
  ));
  select contractor_id into v_payroll_contractor
  from erp.payroll_settlements where id=new.payroll_id;

  if new.source_type='PRODUCTION' then
    select eligible_after_laundry_qty,work_component_id,po_id,contractor_id
    into v_source_qty,v_source_component,v_source_po,v_source_contractor
    from erp.v_payroll_production_work_eligibility
    where source_id=new.source_id;
  elsif new.source_type='REWORK' then
    select rcl.qty_newly_payable,bcc.work_component_id,bc.po_id,ro.contractor_id
    into v_source_qty,v_source_component,v_source_po,v_source_contractor
    from erp.rework_component_lines rcl
    join erp.bs_case_components bcc on bcc.id=rcl.bs_case_component_id
    join erp.bs_cases bc on bc.id=bcc.bs_case_id
    join erp.rework_orders ro on ro.id=rcl.rework_order_id
    where rcl.id=new.source_id
      and ro.destination_type='CONTRACTOR'
      and ro.status='COMPLETED'
      and ro.cost_posted
      and bc.status='RESOLVED';
  elsif new.source_type='FG_REPAIR' then
    -- AX repair wage of a found BS repaired to GOOD (owner 24 Sep 2026): a contractor debt paid through payroll. The row
    -- is locked FOR SHARE so an AX reversal (FOR UPDATE) and a payroll line on the same wage serialize.
    select w.qty_pcs,w.work_component_id,null::uuid,w.contractor_id
    into v_source_qty,v_source_component,v_source_po,v_source_contractor
    from erp.fg_unsourced_repair_wages_v1 w
    where w.id=new.source_id and w.status='POSTED'
    for share;
  else
    raise exception 'Payroll source_type must be PRODUCTION, REWORK or FG_REPAIR';
  end if;

  if v_source_qty is null then raise exception 'Payroll source is not currently eligible'; end if;
  if new.work_component_id<>v_source_component then raise exception 'Payroll work component does not match source'; end if;
  if new.po_id is distinct from v_source_po then raise exception 'Payroll PO does not match source'; end if;
  if v_source_contractor is not null and v_payroll_contractor<>v_source_contractor then
    raise exception 'Payroll contractor does not match work source';
  end if;

  select coalesce(sum(pwi.qty_payable),0) into v_already
  from erp.payroll_work_items pwi
  join erp.payroll_settlements ps on ps.id=pwi.payroll_id
  where pwi.source_type=new.source_type and pwi.source_id=new.source_id
    and pwi.work_component_id=new.work_component_id and pwi.id<>new.id
    and ps.status<>'REVERSED';
  if v_already+new.qty_payable>v_source_qty then
    raise exception 'Payroll would overpay/early-pay work source. Eligible %, already %, new %',
      v_source_qty,v_already,new.qty_payable;
  end if;
  return new;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.merge_eligible_work_into_payroll_v2(p_payroll_id uuid, p_lines jsonb, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_payroll erp.payroll_settlements%rowtype;
  v_line jsonb;
  v_eligible record;
  v_qty integer;
  v_added_qty integer:=0;
  v_added_amount numeric(24,2):=0;
begin
  perform erp.require_internal();
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if coalesce(jsonb_typeof(p_lines),'null')<>'array' then
    raise exception 'Eligible lines must be a JSON array';
  end if;
  if jsonb_array_length(p_lines)=0 then raise exception 'At least one eligible line is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'payroll_id',p_payroll_id,'lines',p_lines,'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin('merge_eligible_work_into_payroll_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_payroll from erp.payroll_settlements where id=p_payroll_id for update;
  if v_payroll.id is null then raise exception 'Nota payroll not found'; end if;
  if v_payroll.status not in ('DRAFT','CALCULATED','REVIEW') then
    raise exception 'APPROVED/PAID/REVERSED Nota is locked; use reversal/correction';
  end if;
  if v_payroll.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_payroll.row_version;
  end if;
  perform pg_advisory_xact_lock(hashtextextended(v_payroll.contractor_id::text,0));

  for v_line in
    select value from jsonb_array_elements(p_lines)
    order by value->>'source_type',value->>'source_id'
  loop
    if upper(v_line->>'source_type')='PRODUCTION' then
      perform 1 from erp.work_completion_lines
      where id=(v_line->>'source_id')::uuid for update;
    elsif upper(v_line->>'source_type')='REWORK' then
      perform 1 from erp.rework_component_lines
      where id=(v_line->>'source_id')::uuid for update;
    elsif upper(v_line->>'source_type')='FG_REPAIR' then
      perform 1 from erp.fg_unsourced_repair_wages_v1
      where id=(v_line->>'source_id')::uuid for update;
    else
      raise exception 'Unknown eligible source_type';
    end if;

    select * into v_eligible
    from erp.v_payroll_eligible_work_lines e
    where e.source_type=upper(v_line->>'source_type')
      and e.source_id=(v_line->>'source_id')::uuid;
    if v_eligible.source_id is null then raise exception 'Selected work line is no longer eligible'; end if;
    if v_eligible.contractor_id<>v_payroll.contractor_id then
      raise exception 'Eligible work belongs to a different Mandor';
    end if;
    if (v_eligible.eligible_at AT TIME ZONE 'Asia/Jakarta')::date>v_payroll.period_end then
      raise exception 'Eligible work is after the Nota period end';
    end if;
    v_qty:=coalesce(nullif(v_line->>'qty','')::integer,v_eligible.remaining_qty);
    if v_qty<=0 or v_qty>v_eligible.remaining_qty then
      raise exception 'Requested qty % exceeds remaining eligible qty %',v_qty,v_eligible.remaining_qty;
    end if;
    insert into erp.payroll_work_items(
      payroll_id,po_id,work_component_id,source_type,source_id,qty_payable,rate_snapshot
    ) values(
      v_payroll.id,v_eligible.po_id,v_eligible.work_component_id,
      v_eligible.source_type,v_eligible.source_id,v_qty,v_eligible.rate_snapshot
    )
    on conflict (payroll_id,source_type,source_id,work_component_id) do update
    set qty_payable=erp.payroll_work_items.qty_payable+excluded.qty_payable,
        rate_snapshot=excluded.rate_snapshot;
    v_added_qty:=v_added_qty+v_qty;
    v_added_amount:=v_added_amount+round(v_qty*v_eligible.rate_snapshot,2);
  end loop;

  perform erp.recalculate_payroll(v_payroll.id);
  select * into v_payroll from erp.payroll_settlements where id=v_payroll.id;
  v_response:=jsonb_build_object(
    'payroll_id',v_payroll.id,'status',v_payroll.status,
    'row_version',v_payroll.row_version,'added_qty',v_added_qty,
    'added_amount',v_added_amount,'net_payable',v_payroll.net_payable
  );
  return erp._idempotency_complete('merge_eligible_work_into_payroll_v2',p_client_request_id,v_response);
end;
$function$;
create trigger trg_guard_fg_unsourced_receipts_v1_immutable before update or delete on erp.fg_unsourced_receipts_v1
  for each row execute function erp.guard_fg_unsourced_receipt_immutable_v1();
create trigger trg_guard_fg_unsourced_receipts_v1_truncate before truncate on erp.fg_unsourced_receipts_v1
  for each statement execute function erp.guard_fg_unsourced_receipt_immutable_v1();
create trigger trg_guard_bs_resolution_fg_unsourced_v1 before update or delete on erp.bs_resolutions
  for each row execute function erp.guard_bs_resolution_fg_unsourced_v1();
create trigger trg_guard_fg_unsourced_repair_wages_v1_immutable before update or delete on erp.fg_unsourced_repair_wages_v1
  for each row execute function erp.guard_fg_unsourced_repair_wage_immutable_v1();
create trigger trg_guard_fg_unsourced_repair_wages_v1_truncate before truncate on erp.fg_unsourced_repair_wages_v1
  for each statement execute function erp.guard_fg_unsourced_repair_wage_immutable_v1();
revoke all on function erp.guard_fg_unsourced_receipt_immutable_v1() from public,anon,authenticated,service_role;
revoke all on function erp.guard_bs_resolution_fg_unsourced_v1() from public,anon,authenticated,service_role;
revoke all on function erp.guard_fg_unsourced_repair_wage_immutable_v1() from public,anon,authenticated,service_role;
revoke all on function erp.fg_unsourced_valuation_v1(uuid,timestamp with time zone) from public,anon,authenticated,service_role;
revoke all on function erp.post_fg_unsourced_receipt_v1(jsonb,uuid) from public,anon,authenticated,service_role;
revoke all on function erp.reverse_fg_unsourced_receipt_v1(uuid,text,uuid) from public,anon,authenticated,service_role;
revoke all on function public.erp_preview_fg_unsourced_value_v1(uuid,timestamp with time zone) from public,anon;
grant execute on function public.erp_preview_fg_unsourced_value_v1(uuid,timestamp with time zone) to authenticated,service_role;
revoke all on function public.erp_post_fg_unsourced_receipt_v1(jsonb,uuid) from public,anon;
grant execute on function public.erp_post_fg_unsourced_receipt_v1(jsonb,uuid) to authenticated,service_role;
revoke all on function public.erp_reverse_fg_unsourced_receipt_v1(uuid,text,uuid) from public,anon;
grant execute on function public.erp_reverse_fg_unsourced_receipt_v1(uuid,text,uuid) to authenticated,service_role;
do $coverage$ begin perform erp.assert_new_stock_cutoff_coverage_v1(); end $coverage$;
insert into erp.schema_migrations(version,description) values('v2.6.20ax','Finished goods without a production source: owner receipt with average HPP and reversal');
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule')
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
 if object_count<>0 or fingerprint is distinct from '0000000000000000000000000000000000000000000000000000000000000000' then
  raise exception 'AX_INSTALLED_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
update erp.cp6_v2620ax_rollback_capsule set installed_definition_sha256=encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex');
do $after_data$ declare v_table text;v_hash jsonb;v_after jsonb;v_before jsonb; begin
 v_after:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620ax_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_after:=v_after||jsonb_build_object(v_table,v_hash);
 end loop;
 select snapshot->'before' into v_before from pg_temp.cp6_release_boundary;
 if (v_after-array['fg_unsourced_receipts_v1','fg_unsourced_repair_wages_v1']::text[]) is distinct from v_before or exists(select 1 from unnest(array['fg_unsourced_receipts_v1','fg_unsourced_repair_wages_v1']::text[]) t where (v_after->t->>'count') is distinct from '0')
  then raise exception 'AX_INSTALL_CHANGED_DATA';end if;
 if exists(with live as (select p.oid::regprocedure::text as identity,encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') as definition_sha256,
  array(select a::text from unnest(p.proacl)a order by a::text) as acl,pg_get_userbyid(p.proowner) as owner
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p')) select 1 from pg_temp.cp6_release_functions f left join live x on x.identity=f.identity
  where f.identity<>all(coalesce((select array_agg(object_regidentity) from erp.cp6_v2620ax_rollback_capsule),'{}'))
  and (x.identity is null or (x.definition_sha256,x.acl,x.owner) is distinct from (f.definition_sha256,f.acl,f.owner)))
  then raise exception 'AX_CAPSULE_INCOMPLETE';end if;
 update erp.cp6_v2620ax_rollback_capsule set boundary_snapshot=(select snapshot from pg_temp.cp6_release_boundary)||jsonb_build_object('after',v_after);
end $after_data$;
do $capsule_guard$
declare expected jsonb;actual jsonb;boundary jsonb;
begin
 if not exists(select 1 from pg_class where oid='erp.cp6_v2620ax_rollback_capsule'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='erp.cp6_v2620ax_rollback_capsule'::regclass and a.grantee<>p.relowner)
   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='erp.cp6_v2620ax_rollback_capsule'::regclass and a.grantee<>'postgres'::regrole)
   or exists(select 1 from pg_policy where polrelid='erp.cp6_v2620ax_rollback_capsule'::regclass)
   or exists(select 1 from pg_trigger where tgrelid='erp.cp6_v2620ax_rollback_capsule'::regclass and not tgisinternal)
   or (select count(*) from erp.cp6_v2620ax_rollback_capsule)<>2 then raise exception 'AX_CAPSULE_SECURITY_OR_COUNT';end if;
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620an_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620an_rollback_capsule'::regclass)) into expected;
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620ax_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620ax_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620ax_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620ax_rollback_capsule'::regclass)) into actual;
 if actual is distinct from expected then raise exception 'AX_CAPSULE_SHAPE_DRIFT';end if;
 select boundary_snapshot into boundary from erp.cp6_v2620ax_rollback_capsule limit 1;
 if 2>0 and (boundary is null or exists(select 1 from erp.cp6_v2620ax_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before'])) then raise exception 'AX_CAPSULE_BOUNDARY';end if;
 if exists(select 1 from erp.cp6_v2620ax_rollback_capsule where object_regidentity<>all(array['erp.merge_eligible_work_into_payroll_v2(uuid,jsonb,uuid,bigint)','erp.validate_payroll_work_item_source()']::text[])
   or definition_sha256 is distinct from encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex')
   or installed_definition_sha256 is null or installed_definition_sha256=definition_sha256
   or installed_definition_sha256 is distinct from encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex'))
  then raise exception 'AX_CAPSULE_SOURCE_DRIFT';end if;
end $capsule_guard$;
commit;
