-- CP6 AZ: material recost corrections dated from the physical movement. Release candidate of the T3 combined package; closed, drained maintenance required.
begin;
-- Built by scripts/cp6_t3_awx_release.py from supabase/dev/cp6_az_t1_family.sql (sha256 e1968c8fe40d65274ed6e3f4e126641c744aca2f822d1cbf6d357297a3028971): the T1 body below is unchanged apart from the
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
 if exists(select 1 from erp.schema_migrations where version='v2.6.20az') or to_regclass('erp.cp6_v2620az_rollback_capsule') is not null
  or false
 then raise exception 'AZ_EXACT_PREDECESSOR_WITHOUT_SUCCESSOR_REQUIRED';end if;
end $admission$;
do $predecessor$
begin
 if exists(select 1 from supabase_migrations.schema_migrations where version>'20260924010200') then raise exception 'AZ_EXACT_PREDECESSOR_REQUIRED';end if;
end $predecessor$;
do $prior_platform$
declare r record;
begin
 for r in select * from jsonb_to_recordset('[{"marker":"v2.6.20ac","stamp":"20260915031500","name":"erp_v2_6_20ac_cp6_temporal_surface_closure","sha":"7b5690a2eddf618833d352dc75eb95aa1ef4dbcfb25d39b30374b733d33dadbc"},{"marker":"v2.6.20ad","stamp":"20260915113627","name":"erp_v2_6_20ad_cp6_opening_material_business_day","sha":"cd4879eb9b053e3b7a975e1430f481131e377f260ece2f19f07bfb4c98498c1d"},{"marker":"v2.6.20ae","stamp":"20260915201500","name":"erp_v2_6_20ae_cp6_opening_roll_integrity","sha":"228d9185501d418835e6434e64e1445be7b12ce2f517778ea63d789d478461c1"},{"marker":"v2.6.20af","stamp":"20260916014332","name":"erp_v2_6_20af_cp6_posted_child_integrity","sha":"54c5f73b99a2e63c858a777f669432f28260177daf4c45d806bb0e8a7c7c8e8e"},{"marker":"v2.6.20ag","stamp":"20260916050822","name":"erp_v2_6_20ag_cp6_sale_reservation_lineage","sha":"bff1d7d82917ce226ad0fb8823418fa14e497407d9659e125dc01ed5e2fd5944"},{"marker":"v2.6.20ah","stamp":"20260916070451","name":"erp_v2_6_20ah_cp6_return_allocation_eligibility","sha":"e5312744a2ef9ac53717c97e155fccf96a33e2f6a0c68c4b9c45f378ac538219"},{"marker":"v2.6.20ai","stamp":"20260916090022","name":"erp_v2_6_20ai_cp6_work_source_lineage","sha":"d3a604e53e599221afd46d1397e0d0660ebd8dc48db27113dfa63d3c3613a61c"},{"marker":"v2.6.20aj","stamp":"20260916202400","name":"erp_v2_6_20aj_cp6_rework_output_lineage","sha":"2e6cd4e94b52a27c83d2ba134a996c1db66a6f7ff617a5895f8c14769673f9ea"},{"marker":"v2.6.20ak","stamp":"20260917033516","name":"erp_v2_6_20ak_cp6_import_reference_preview","sha":"0d42825b2f2fcb38b9678fe1e6982b0c63290aac012b92be224f4323d495c536"},{"marker":"v2.6.20al","stamp":"20260917054049","name":"erp_v2_6_20al_cp6_opening_value_validation","sha":"74a5d5e14d79c7bbafa731aaf2fe1708bc575299600261f7412f1f7ea7323920"},{"marker":"v2.6.20am","stamp":"20260921214120","name":"erp_v2_6_20am_cp6_transfer_integrity","sha":"d5b155edb19aa8ca949036ba8a9cf67090478083c2e1ae6cc5bbf00b445716a5"},{"marker":"v2.6.20an","stamp":"20260921223438","name":"erp_v2_6_20an_cp6_cutting_selectors","sha":"21ac97ded4ed0cee9175c7fac7ef28ab6713d08b00766e1e5adc86bd38205e6c"},{"marker":"v2.6.20ao","stamp":"20260922135612","name":"erp_v2_6_20ao_cp6_invoice_retail","sha":"5687bb0236528d7e485e738ee2f96c2be0f4bde7e0d41c16bacee3a58183bdbb"},{"marker":"v2.6.20ap","stamp":"20260922135615","name":"erp_v2_6_20ap_cp6_connected_import_materials","sha":"fb8e14f0fd505edf730c0908f7e1c500cf850e29bcc0e90b3a51877224edd61b"},{"marker":"v2.6.20aq","stamp":"20260922161019","name":"erp_v2_6_20aq_cp6_accessory_lock_order","sha":"b1b4e449ca84ad524189640bcd76302cb277b9b690ed89f739ad5706e3cfac5a"},{"marker":"v2.6.20ar","stamp":"20260922185015","name":"erp_v2_6_20ar_cp6_opening_overlap","sha":"7da20a87d48493b4b64c10c395e8e54f87c1c40a835fbd09bbf2cdbc8866fa10"},{"marker":"v2.6.20as","stamp":"20260922210815","name":"erp_v2_6_20as_cp6_event_dates_product_identity","sha":"84e95211698eb2426995fd59d702bb42674f9fff675401be4861c9aa568cc1a8"},{"marker":"v2.6.20at","stamp":"20260923005153","name":"erp_v2_6_20at_cp6_wip_temporal_identity","sha":"f114a78918138a65f761488b77cadb1ab8a70ce6a6a88ae58a9d38656d1cfdb4"},{"marker":"v2.6.20au","stamp":"20260923045944","name":"erp_v2_6_20au_cp6_controlled_product_lifecycle","sha":"593b06092c2d47e03644afb1b7b5aef46c1442a56613f853a151b78ef738f2c2"},{"marker":"v2.6.20av","stamp":"20260923110000","name":"erp_v2_6_20av_cp6_identity_new_stock_cutoff","sha":"193e84efac8ead7cab681071e40070e1f9249f82cec1b7972f0576e8df25a2dc"},{"marker":"v2.6.20aw","stamp":"20260924010000","name":"erp_v2_6_20aw_cp6_close_readiness_engine","sha":"08826a25c14f8f18f5a168040b6f96dc4efe15c4498be5e92b0834601e77407c"},{"marker":"v2.6.20ax","stamp":"20260924010100","name":"erp_v2_6_20ax_cp6_fg_unsourced_receipts","sha":"32b4d33ebd80ed55951736c23be71b7eb79343c4c8dd623a32ae673924fc0a18"},{"marker":"v2.6.20ay","stamp":"20260924010200","name":"erp_v2_6_20ay_cp6_hpp_dated_from_goods","sha":"b41617d7d764e7ef3f25b323d6b6896a0f363623b1691a23c745ed34d12e5473"}]'::jsonb) as x(marker text,stamp text,name text,sha text) loop
  if not exists(select 1 from erp.schema_migrations where version=r.marker)
   or (select count(*) from supabase_migrations.schema_migrations where name=r.name)<>1
   or not exists(select 1 from supabase_migrations.schema_migrations where version=r.stamp and name=r.name
    and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')=r.sha) then
   raise exception 'AZ_PRIOR_PLATFORM_DRIFT: %',r.name;
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
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule','cp6_v2620ay_rollback_capsule','cp6_v2620az_rollback_capsule')
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
  raise exception 'AZ_PREDECESSOR_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
do $historical_capsules$
declare r record;actual text;
begin
 for r in select * from jsonb_each_text('{"bs_resolution_v2619_rollback_capsule":"28ab388833da7da87384766ecaedadc66b4d048c303ee91e16f3939e34afdc39","bs_resolution_v2619a_rollback_capsule":"de8dfaab7b63b8742d383a089cdb05e73b629aad9f4df149e6a3c9fb590ef560","bs_resolution_v2619b_rollback_capsule":"d6d4f7457743d51679b5d25bf166ed69ca4b4f098cf5902ff985937531c2505d","bs_resolution_v2619c_rollback_capsule":"0207ba4f2ffba8ed61584709bbd884f1d2ee1a5981194fd7189a45afe8b3cbe1","cp3_r4_rollback_capsule":"7c01add62e66a4e2774a7199c2e77a04cca5e5942dbbba54d22cef720f82bc1d","cp45_v2617_rollback_capsule":"b9a43ce463de9905e94dd6538fd2a4952b0586a78c145f6f9d88aab7d6da3d80","cp45_v2617a_rollback_capsule":"b065dbcfdf1b59cb799e9f58caf6dd5ca7686e9f70826fce6a1ba8f140610022","cp4_v2616_rollback_capsule":"dde0a005dbe7cc93709bdfc6b961f4b9a76bf4db06fd7177d21dc79048af4d2f","cp6_v2620_rollback_capsule":"01f1e4e23211cff3c399d2d768a41be57980bfab00790715aa759b00a515e032","cp6_v2620a_rollback_capsule":"67befaaf327d2591e1ca1d654132ee483eba39b6cbb4f891c4719d817155d448","cp6_v2620aa_rollback_capsule":"eb0d6fb4fcac2ac06929d577101e604428e9a04821813c342e5b831147dc8948","cp6_v2620ab_rollback_capsule":"3be9a9166e3a607962be819fbe23d38fe455290a7a970dc2aad068079bf30785","cp6_v2620ac_relation_rollback_capsule":"2be5cbb62d1147e1e0d053dc4e447fe1d1258439352c297814c981c985959838","cp6_v2620ac_rollback_capsule":"51a8b08c9d96e66f03c2c8ba94ed3ed8fb15b26d1a2e4c65c58c614442dfa969","cp6_v2620ad_rollback_capsule":"5c3588109395b32ed743e0f4f5d789a3c59e3fffbab7469138f1f423c877ea9d","cp6_v2620ae_rollback_capsule":"6a75e02bf7b90c542fd9f2ac9534a2de066b047f5ffea65bffb1f83fa63c17f0","cp6_v2620af_rollback_capsule":"bfa89fc0e94d34b29405acedf551935f024942835f31cdc98f0f0983a9550288","cp6_v2620ag_rollback_capsule":"7ddfe6181f0c1c7439faf8a8150c542e958b3bafd8d18b5b2d1eb454fd7a85b7","cp6_v2620ah_rollback_capsule":"361be9321e5f4dadc7c7ec0e99ed746a98e7a4150178fc8355d23707c1507a93","cp6_v2620ai_rollback_capsule":"f2428dd712aa763b1379a4ae5b1a1e1e6ee175b355d8769b854a28f1355181c8","cp6_v2620aj_rollback_capsule":"8e24026dc90a2a92292c2cc6c8faa5fc3de991a19f326db494e0af2a518436f1","cp6_v2620ak_rollback_capsule":"dc7bfce7b9ee6a42e33cdf03cabd99d64435a4615245b2037fd6e4ee399aef10","cp6_v2620al_rollback_capsule":"c9e9aca042674efa5c6fa283e4b9ee47f3353ee9ee95b34e14ef1fd6b09bfde9","cp6_v2620am_rollback_capsule":"e781e631d06c6894c20b1fe6f9c65779f461d19c405c8ae74f28ed7d83ae6a26","cp6_v2620an_rollback_capsule":"ebfa8a281a32fe54babbdc209264ab422fde27f344d48561b90d2af022fe75b3","cp6_v2620ao_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620ap_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620aq_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620ar_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620as_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620at_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620au_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620av_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620aw_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620ax_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620ay_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620b_rollback_capsule":"f9bf784bff0c54e647f491e257a9649fd0c3e6f10c39ddfc0944c961b9dd7601","cp6_v2620c_rollback_capsule":"f88b1f5890ee8e7041758971bf9c9a3ce2bd0a7be6989fb95332c2dd7fa139aa","cp6_v2620d_rollback_capsule":"fa300c5554da4bb6812c61d726fd64f66329c97b085fa7d6ad5d0d8e5ae31235","cp6_v2620e_rollback_capsule":"143cd291cf4c12e78ab61e74e02ed03b08a48832a5064671868ff2bd2e3e1da7","cp6_v2620f_rollback_capsule":"076133b098e821fc2713af559618adf8aa3e204908f810af440fda355fc7a57f","cp6_v2620g_rollback_capsule":"ed9f4cacb47bd026ad6bdea373d1aa87044ed12aa60323cea453e3187dc488c4","cp6_v2620h_rollback_capsule":"4c25a060a2df3c22cd6fa9ff0b297163e223118a0d930b97bf1282b4756d909d","cp6_v2620i_rollback_capsule":"051203d95c44968abd8594f5bd48e289c4ac9a6c9fa49a89eee1086ad6b2c166","cp6_v2620j_rollback_capsule":"1393a8085d0f58717b13048c9cc3f7e9969ac86c351d6dfefdd2d4f43a735bd2","cp6_v2620k_rollback_capsule":"55aa71061f616ea11b361f0fabee2fd892f6438cc3f567cb9c135552ade42409","cp6_v2620l_rollback_capsule":"b4278768fce4ef307795953c14f607278c43bf474d76d3362e477280be08eb39","cp6_v2620m_rollback_capsule":"4b5f89d7bc4557f92b47716fe15640ab244c424fc1279433eb806d9d91d234e9","cp6_v2620n_rollback_capsule":"46e5ea4524613bb7a386551ada9e06888ea35eb987f9f5b864457fdd18bc3bc1","cp6_v2620o_rollback_capsule":"044e6b1a050df7e2a1d36082b0451877bda01116c08f611dfceb7a666bdf03c8","cp6_v2620p_rollback_capsule":"b656abaf23276984567c6c8d87b311427463c008b5ecd762fbdd0c2df13795df","cp6_v2620q_rollback_capsule":"ab6c992fbaa87f19a4eba696a57a3972f98504a354d9b5fc3be660939f8ea20f","cp6_v2620r_rollback_capsule":"8eb5e0a38284c5f8e3fee56618893ba72feaae9d26605c9ca3874dae25045297","cp6_v2620s_rollback_capsule":"fb57810a75f8829a038ed61b3a1cabde33dccf1e384661bc6723c51e28b3e132","cp6_v2620t_rollback_capsule":"348db4650d788750da243500b49e23c1130fdb70bc4a6d1fdf136bf68aa21f30","cp6_v2620u_rollback_capsule":"720eb1984548a3c381387fbe4d34e3c6f00334c8a4549eab7e398b827dcb7dd4","cp6_v2620v_rollback_capsule":"573ef5842eefadf1c32469514f4c8498667c99aec20ef20651406e4f419f5f60","cp6_v2620w_rollback_capsule":"f4e2ca1d577dd9f2724cc90693e8ee8bff36365c696575b69c6463f3e8ca0324","cp6_v2620x_rollback_capsule":"064db1068b56daa69e409ae582cd8a99490cea75d269154baa4217f90d3ca0d1","cp6_v2620y_rollback_capsule":"e3b23429a7f002c85ca8de1f8c632df13a4a2fc4e4654c12e2431c212772841d","cp6_v2620z_rollback_capsule":"ad0436a1480af43070e9861cb7e28d4cf55c435edbffb5fe368ca7babb7863ef","cutting_bridge_v2618_rollback_capsule":"535d1abd25668bc5bee79d82a602afe5efe4e8ce313bf1fb5170ae2004e3cb2d","cutting_bridge_v2618a_rollback_capsule":"db0608e690b3d936fa20b62cc4cfb9b1f9e86718212526eb6131562578b8bf60"}'::jsonb) loop
  execute format($caps$select encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to((to_jsonb(t)-array['captured_at','boundary_snapshot'])::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$caps$,r.key) into actual;
  if actual is distinct from r.value then raise exception 'AZ_HISTORICAL_CAPSULE_DRIFT: %',r.key;end if;
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
 for r in select unnest(array['erp.cp6_v2620ao_rollback_capsule','erp.cp6_v2620ap_rollback_capsule','erp.cp6_v2620aq_rollback_capsule','erp.cp6_v2620ar_rollback_capsule','erp.cp6_v2620as_rollback_capsule','erp.cp6_v2620at_rollback_capsule','erp.cp6_v2620au_rollback_capsule','erp.cp6_v2620av_rollback_capsule','erp.cp6_v2620aw_rollback_capsule','erp.cp6_v2620ax_rollback_capsule','erp.cp6_v2620ay_rollback_capsule']::regclass[]) as rel loop
  if not exists(select 1 from pg_class where oid=r.rel and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid=r.rel and a.grantee<>p.relowner)
   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid=r.rel and a.grantee<>'postgres'::regrole)
   or exists(select 1 from pg_policy where polrelid=r.rel)
   or exists(select 1 from pg_trigger where tgrelid=r.rel and not tgisinternal) then raise exception 'AZ_PRIOR_CAPSULE_SECURITY: %',r.rel;end if;
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel)) into actual;
  if actual is distinct from expected then raise exception 'AZ_PRIOR_CAPSULE_SHAPE_DRIFT: %',r.rel;end if;
  execute format($b$select count(*) filter(where boundary_snapshot is null or not(boundary_snapshot ?& array['before','after','platform_before','markers_before']))
   +(case when count(distinct boundary_snapshot)=1 then 0 else 1 end) from %s$b$,r.rel) into bad;
  if bad<>0 then raise exception 'AZ_PRIOR_CAPSULE_BOUNDARY: %',r.rel;end if;
 end loop;
end $prior_capsules$;
create table erp.cp6_v2620az_rollback_capsule(like erp.cp6_v2620an_rollback_capsule including all);
alter table erp.cp6_v2620az_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620az_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620az_rollback_capsule(object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),i.identity,pg_get_functiondef(p.oid),
 encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
 array(select a::text from unnest(p.proacl)a order by a::text),pg_get_userbyid(p.proowner)
from unnest(array['erp.sync_material_cost_revaluation(uuid)','erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)','erp.sync_finished_po_wip_residual(uuid,date,text)','erp.guard_pocket_period_v1()','erp.sync_initial_import_bs_value_v1(uuid,date)','erp.sync_non_po_product_hpp_to_gl_v2620f(uuid,date,text,uuid,text)','erp.refresh_accessory_hpp_after_material_recost(uuid,text)','erp.reverse_qc(uuid,text)','erp.reverse_rework_completion(uuid,text)','erp.complete_initial_import_wip_v1(jsonb)','erp.post_material_supplier_invoice(uuid)','erp.post_material_purchase_cost_correction(uuid)']) i(identity)
join pg_proc p on p.oid=i.identity::regprocedure join pg_namespace n on n.oid=p.pronamespace;
create temp table cp6_release_functions on commit drop as
select p.oid::regprocedure::text as identity,encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') as definition_sha256,
  array(select a::text from unnest(p.proacl)a order by a::text) as acl,pg_get_userbyid(p.proowner) as owner
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p');
do $before_data$ declare v_table text;v_hash jsonb;v_before jsonb; begin
 v_before:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620az_rollback_capsule']::text[]) order by 1 loop
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
 if (select count(*) from erp.schema_migrations where version in('v2.6.20av','v2.6.20aw','v2.6.20ax','v2.6.20ay'))<>4 then raise exception 'AZ_T1_REQUIRES_AV_AW_AX_AY'; end if;
 if exists(select 1 from erp.schema_migrations where version='v2.6.20az') then raise exception 'AZ_T1_ALREADY_INSTALLED'; end if;
end $t1_guard$;
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
  v_e date;
  v_closed boolean;
  v_date date;
  v_would numeric(24,6);
  q record;
begin
  perform erp.require_internal();
  -- AZ (owner, 24 Sep 2026): a correction is dated from the physical movement it corrects when the recost date E is
  -- open, D = greatest(E, business date of the movement); a closed E keeps every posting on E (post_journal posts it
  -- on the recognition day with economic date E), as before.
  v_e:=coalesce(erp.invoice_recost_economic_date_v1(),erp._cp3_business_date(statement_timestamp()));
  v_closed:=exists(select 1 from erp.accounting_period_control c
            where c.singleton_id=1 and c.closed_through is not null and v_e<=c.closed_through);

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
      -- AZ rev2.1: revalued like the replay would value it, on its own day; its reversal takes it back (legs below).
      v_would:=case when r.qty_signed<0 then (select h.average_after from erp.material_cost_history h join erp.material_stock_movements hm on hm.id=h.movement_id
          where h.material_id=p_material_id and (hm.physical_at,hm.system_created_at,hm.id)<(r.physical_at,r.system_created_at,r.id)
          order by hm.physical_at desc,hm.system_created_at desc,hm.id desc limit 1)
        when r.source_type='CUTTING_GROUP_RETURN' then (select case when exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=x.id)
            then (select h.average_after from erp.material_cost_history h join erp.material_stock_movements hm on hm.id=h.movement_id
          where h.material_id=p_material_id and (hm.physical_at,hm.system_created_at,hm.id)<(x.physical_at,x.system_created_at,x.id)
          order by hm.physical_at desc,hm.system_created_at desc,hm.id desc limit 1) else x.unit_cost_snapshot end
          from erp.material_stock_movements x where x.material_id=r.material_id and x.source_type='CUTTING_GROUP'
            and x.source_id=r.source_id and x.movement_type='CUTTING_ISSUE' and x.roll_id is not distinct from r.roll_id
          order by x.physical_at desc,x.system_created_at desc,x.id desc limit 1) end;
      v_target:=case when v_would is null then 0
        else round((r.qty_signed*(v_would-coalesce(r.original_unit_cost_snapshot,r.unit_cost_snapshot)))::numeric,2) end;
      -- Both legs on one day (a closed E, a recost without a late invoice): the movement keeps what it has (its interim until
      -- the reversal) and the reversal nets the pair to zero that day, as the previous single posting did.
      if v_closed or least(greatest(v_e,erp._cp3_business_date(r.physical_at)),erp._cp3_business_date(statement_timestamp()))
         >=(select min(least(greatest(v_e,erp._cp3_business_date(rv.physical_at)),erp._cp3_business_date(statement_timestamp())))
            from erp.material_stock_movements rv where rv.reversal_of_id=r.id) then
        v_target:=coalesce((select s.applied_inventory_delta from erp.material_cost_revaluation_state s where s.movement_id=r.id),0);
      end if;
    else
      v_target:=round((r.qty_signed*(r.unit_cost_snapshot-coalesce(r.original_unit_cost_snapshot,r.unit_cost_snapshot)))::numeric,2);
    end if;

    -- AZ rev2.1: the movement, then each of its reversals with the opposite target on the reversal's own day.
    for q in select r.id mid,r.physical_at pat,v_target tgt
             union all select rv.id,rv.physical_at,-v_target from erp.material_stock_movements rv where rv.reversal_of_id=r.id
    loop
    select s.applied_inventory_delta into v_old
    from erp.material_cost_revaluation_state s where s.movement_id=q.mid for update;
    v_old:=coalesce(v_old,0);
    v_diff:=round(q.tgt-v_old,2);

    if abs(v_diff)>0.005 then
      v_date:=case when v_closed then v_e
        else least(greatest(v_e,erp._cp3_business_date(q.pat)),erp._cp3_business_date(statement_timestamp())) end;
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
      values(p_material_id,q.mid,v_date,v_old,q.tgt,v_diff,v_counterpart,v_po,v_contractor)
      returning id into v_event;

      v_journal:=erp.post_journal('MATERIAL_COST_REVALUATION',v_event,v_date,
        'Automatic material moving-average recost: '||r.source_type,v_lines);
      update erp.material_cost_revaluation_events set journal_entry_id=v_journal,
      effective_date=(select transaction_date from erp.journal_entries where id=v_journal) where id=v_event;
    end if;

    insert into erp.material_cost_revaluation_state(movement_id,applied_inventory_delta,updated_at)
    values(q.mid,q.tgt,statement_timestamp())
    on conflict(movement_id) do update set applied_inventory_delta=excluded.applied_inventory_delta,updated_at=statement_timestamp();
    end loop;
  end loop;
  -- AZ rev2.1: a reversed write-off (outbound item of a material adjustment; a pocket-fabric usage keeps its own period rule)
  -- left at its posting cost while the stock it came from is revalued, and the adjustment document's own cumulative
  -- revaluation (erp._cp6_sync_material_adjustment_revaluation) targets it to zero once reversed. Between the adjustment
  -- day and the reversal day the write-off carries the replayed cost: +I against the write-off account on its day, -I on the
  -- reversal's day (event and state on the reversal movement, outside the document's own book). Both legs on one day: kept.
  for r in select msm.*,rv.id rv_id,rv.physical_at rv_at
      from erp.material_stock_movements msm join erp.material_adjustment_items i on i.id=msm.source_id
      join erp.material_stock_movements rv on rv.reversal_of_id=msm.id
    where msm.material_id=p_material_id and msm.source_type='MATERIAL_ADJUSTMENT_ITEM' and msm.reversal_of_id is null
      and msm.qty_signed<0 and not exists(select 1 from erp.pocket_fabric_usage u where u.adjustment_id=i.adjustment_id)
    order by msm.physical_at,msm.system_created_at,msm.id
  loop
    select s.applied_inventory_delta into v_old from erp.material_cost_revaluation_state s where s.movement_id=r.rv_id for update;
    v_old:=coalesce(v_old,0);
    v_would:=(select h.average_after from erp.material_cost_history h join erp.material_stock_movements hm on hm.id=h.movement_id
          where h.material_id=p_material_id and (hm.physical_at,hm.system_created_at,hm.id)<(r.physical_at,r.system_created_at,r.id)
          order by hm.physical_at desc,hm.system_created_at desc,hm.id desc limit 1);
    v_target:=case when v_would is null then 0
      else round((r.qty_signed*(v_would-coalesce(r.original_unit_cost_snapshot,r.unit_cost_snapshot)))::numeric,2) end;
    if (case when v_closed then v_e else least(greatest(v_e,erp._cp3_business_date(r.physical_at)),erp._cp3_business_date(statement_timestamp())) end)>=(case when v_closed then v_e else least(greatest(v_e,erp._cp3_business_date(r.rv_at)),erp._cp3_business_date(statement_timestamp())) end) then v_target:=v_old; end if;
    v_diff:=round(v_target-v_old,2);
    if abs(v_diff)>0.005 then
      for q in select case when v_closed then v_e else least(greatest(v_e,erp._cp3_business_date(r.physical_at)),erp._cp3_business_date(statement_timestamp())) end d,v_diff amt union all select case when v_closed then v_e else least(greatest(v_e,erp._cp3_business_date(r.rv_at)),erp._cp3_business_date(statement_timestamp())) end,-v_diff
      loop
        v_lines:=case when q.amt>0 then jsonb_build_array(
            jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',q.amt,'credit',0),
            jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',0,'credit',q.amt))
          else jsonb_build_array(
            jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',abs(q.amt),'credit',0),
            jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',0,'credit',abs(q.amt))) end;
        insert into erp.material_cost_revaluation_events(material_id,movement_id,effective_date,old_inventory_delta,new_inventory_delta,delta_amount,counterpart_mapping_key,po_id,contractor_id)
        values(p_material_id,r.rv_id,q.d,v_old,v_target,q.amt,'OTHER_EXPENSE',null,null)
        returning id into v_event;
        v_journal:=erp.post_journal('MATERIAL_COST_REVALUATION',v_event,q.d,
          'Automatic material moving-average recost: reversed write-off until its reversal',v_lines);
        update erp.material_cost_revaluation_events set journal_entry_id=v_journal,
        effective_date=(select transaction_date from erp.journal_entries where id=v_journal) where id=v_event;
      end loop;
    end if;
    insert into erp.material_cost_revaluation_state(movement_id,applied_inventory_delta,updated_at)
    values(r.rv_id,v_target,statement_timestamp())
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
CREATE OR REPLACE FUNCTION erp._cp6_sync_material_adjustment_revaluation(p_adjustment uuid, p_material uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'pg_catalog', 'pg_temp'
AS $function$
declare s jsonb;v_delta jsonb;v_lines jsonb;v_event uuid;v_journal uuid;v_date date;v_e date;
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
 v_event:=gen_random_uuid();
 -- AZ: dated from the adjustment document's physical day when the recost date E is open; a closed E stays on E.
 v_e:=coalesce(erp.invoice_recost_economic_date_v1(),erp._cp3_business_date(statement_timestamp()));
 v_date:=case when exists(select 1 from erp.accounting_period_control c
            where c.singleton_id=1 and c.closed_through is not null and v_e<=c.closed_through) then v_e
   else least(greatest(v_e,(select erp._cp3_business_date(a.physical_at) from erp.material_adjustments a where a.id=p_adjustment)),
              erp._cp3_business_date(statement_timestamp())) end;
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
CREATE OR REPLACE FUNCTION erp.sync_finished_po_wip_residual(p_po_id uuid, p_effective_date date DEFAULT ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date, p_reason text DEFAULT 'Finished PO residual WIP close'::text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_status text;
  v_wip_account uuid;
  v_residual numeric(24,6):=0;
  v_event uuid;
  v_journal uuid;
  v_lines jsonb;
begin
  perform erp.require_internal();
  select status into v_status from erp.production_orders where id=p_po_id for update;
  if v_status is null then raise exception 'PO not found'; end if;
  if v_status<>'FINISHED' then return; end if;
  v_wip_account:=erp.account_id('WIP');

  select coalesce(sum(jl.debit-jl.credit),0) into v_residual
  from erp.journal_lines jl
  join erp.journal_entries je on je.id=jl.journal_entry_id
  where je.status in ('POSTED','REVERSED')
    and jl.po_id=p_po_id and jl.account_id=v_wip_account;

  if abs(v_residual)<=0.005 then return; end if;
  -- AZ: on the invoice path only (a late supplier invoice), not before the PO's last WIP posting while the date is open,
  -- never after today; a closed date and every other caller (finish, laundry estimate, pocket) stay as before.
  if erp.invoice_recost_economic_date_v1() is not null and not exists(select 1 from erp.accounting_period_control c
                where c.singleton_id=1 and c.closed_through is not null and p_effective_date<=c.closed_through) then
    select least(greatest(p_effective_date,coalesce(max(je.transaction_date),p_effective_date)),erp._cp3_business_date(statement_timestamp()))
      into p_effective_date
    from erp.journal_lines jl
    join erp.journal_entries je on je.id=jl.journal_entry_id
    where je.status in ('POSTED','REVERSED')
      and jl.po_id=p_po_id and jl.account_id=v_wip_account;
  end if;
  insert into erp.po_wip_close_events(po_id,effective_date,residual_amount,reason)
  values (p_po_id,p_effective_date,v_residual,p_reason) returning id into v_event;

  if v_residual>0 then
    v_lines:=jsonb_build_array(
      jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',round(v_residual,2),'credit',0,'po_id',p_po_id),
      jsonb_build_object('mapping_key','WIP','debit',0,'credit',round(v_residual,2),'po_id',p_po_id));
  else
    v_lines:=jsonb_build_array(
      jsonb_build_object('mapping_key','WIP','debit',round(abs(v_residual),2),'credit',0,'po_id',p_po_id),
      jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',0,'credit',round(abs(v_residual),2),'po_id',p_po_id));
  end if;
  v_journal:=erp.post_journal('PO_WIP_RESIDUAL_CLOSE',v_event,p_effective_date,p_reason,v_lines);
  update erp.po_wip_close_events set journal_entry_id=v_journal where id=v_event;
end;
$function$;
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
   -- AZ: a pocket recost is not dated before the period's own allocation (its end day) while the date is open; a closed date
   -- keeps its economic date (post_journal posts it on the recognition day), a non-invoice recost stays on today.
   perform erp.sync_pocket_period_v1(v_pool,case when exists(select 1 from erp.accounting_period_control c where c.singleton_id=1 and c.closed_through is not null and new.effective_date<=c.closed_through) then new.effective_date
     else least(greatest(new.effective_date,(select p.period_end from erp.pocket_periods p where p.id=v_pool)),erp._cp3_business_date(statement_timestamp())) end,
     'RECOST','Koreksi harga kain kantong');end loop;
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
create or replace function erp.sync_initial_import_bs_value_v1(p_item uuid,p_date date) returns void
language plpgsql security definer set search_path='' as $function$
declare s erp.initial_import_production_sources%rowtype;v_qty integer;v_target numeric;v_prior numeric;v_delta numeric;v_event uuid;v_journal uuid;
 d record;v_left numeric;v_part numeric;v_run numeric;v_done integer:=0;
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
 -- AZ: on a late supplier invoice with an open date the change reaches each disposed BS piece on the day it was disposed
 -- (bs_resolutions.physical_at), pro rata by pieces, never before the invoice date nor after today; the last day takes the
 -- remainder. Every other caller (the disposition trigger on its physical day, a closed date) posts once, as before.
 if erp.invoice_recost_economic_date_v1() is not null and v_qty>0 and not exists(select 1 from erp.accounting_period_control c where c.singleton_id=1 and c.closed_through is not null and p_date<=c.closed_through) then
  v_left:=v_delta;v_run:=v_prior;
  for d in select least(greatest(p_date,erp._cp3_business_date(r.physical_at)),erp._cp3_business_date(statement_timestamp())) bday,sum(r.qty_pcs) q
    from erp.bs_resolutions r where r.bs_case_id=s.bs_case_id and r.source_rework_order_id is null
      and r.resolution_type not in('REWORK_SEWING','REWORK_LAUNDRY') group by 1 order by 1 loop
   v_done:=v_done+d.q;
   v_part:=case when v_done>=v_qty then v_left else round(v_delta*d.q/v_qty,2) end;
   v_left:=v_left-v_part;
   if v_part<>0 then
    v_event:=gen_random_uuid();
    v_journal:=erp.post_journal('INITIAL_IMPORT_BS_VALUE',v_event,d.bday,'Nilai BS saldo awal yang dikeluarkan atau dikembalikan · tanggal pengeluaran BS',jsonb_build_array(
     jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',greatest(v_part,0),'credit',greatest(-v_part,0),'po_id',s.po_id),
     jsonb_build_object('mapping_key','WIP','debit',greatest(-v_part,0),'credit',greatest(v_part,0),'po_id',s.po_id)));
    insert into erp.initial_import_bs_value_events(id,opening_item_id,disposed_qty,previous_amount,target_amount,economic_date,journal_entry_id,created_by)
    values(v_event,p_item,least(v_done,v_qty),v_run,v_run+v_part,d.bday,v_journal,erp.current_app_user_id());
    v_run:=v_run+v_part;
   end if;
  end loop;
  if v_left<>0 then raise exception 'INITIAL_IMPORT_BS_VALUE_SPLIT_REMAINDER %',v_left;end if;
  return;
 end if;
 v_event:=gen_random_uuid();
 v_journal:=erp.post_journal('INITIAL_IMPORT_BS_VALUE',v_event,p_date,'Nilai BS saldo awal yang dikeluarkan atau dikembalikan',jsonb_build_array(
  jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',greatest(v_delta,0),'credit',greatest(-v_delta,0),'po_id',s.po_id),
  jsonb_build_object('mapping_key','WIP','debit',greatest(-v_delta,0),'credit',greatest(v_delta,0),'po_id',s.po_id)));
 insert into erp.initial_import_bs_value_events(id,opening_item_id,disposed_qty,previous_amount,target_amount,economic_date,journal_entry_id,created_by)
 values(v_event,p_item,v_qty,v_prior,v_target,p_date,v_journal,erp.current_app_user_id());
end;$function$;
CREATE OR REPLACE FUNCTION erp.sync_non_po_product_hpp_to_gl_v2620f(
  p_product_id uuid,
  p_effective_date date,
  p_trigger_source_type text,
  p_trigger_source_id uuid,
  p_reason text
)
returns void
language plpgsql
security definer
set search_path to 'erp','public'
as $function$
declare
  t record;
  b record;
  v_df numeric(20,2);
  v_dc numeric(20,2);
  v_do numeric(20,2);
  v_event uuid:=gen_random_uuid();
  v_journal uuid;
  v_lines jsonb:='[]'::jsonb;
  r record;v_acc jsonb:='{}'::jsonb;v_c numeric(20,2);v_o numeric(20,2);v_f numeric(20,2);
  v_sc numeric(20,2):=0;v_so numeric(20,2):=0;v_end date;v_ev uuid;v_rf numeric;v_rc numeric;v_ro numeric;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  if nullif(btrim(p_trigger_source_type),'') is null
     or nullif(btrim(p_reason),'') is null then
    raise exception 'Non-PO HPP synchronization requires source and reason';
  end if;
  if exists(
    select 1
    from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    join erp.fg_lots s on s.id=a.source_lot_id
    join erp.fg_lots d on d.id=a.destination_lot_id
    where(s.po_id is null or d.po_id is null)
      and(s.product_id=p_product_id or d.product_id=p_product_id)
  ) then
    raise exception 'NON_PO_CONVERSION_REQUIRES_SOURCED_HPP_WORKFLOW';
  end if;

  select * into t
  from erp.compute_non_po_product_hpp_targets_v2620f(p_product_id);
  select * into b
  from erp.compute_non_po_product_hpp_book_v2620f(p_product_id);
  if abs(t.hpp_total_cost-b.hpp_total_cost)>0.005 then
    raise exception 'NON_PO_HPP_SOURCE_VALUE_MISMATCH: product %, target total %, book total %',
      p_product_id,t.hpp_total_cost,b.hpp_total_cost;
  end if;

  v_df:=round(t.fg_value-b.fg_value,2);
  v_dc:=round(t.cogs_value-b.cogs_value,2);
  v_do:=round(t.other_out_value-b.other_out_value,2);
  if abs(v_df+v_dc+v_do)>0.005 then
    raise exception 'NON_PO_HPP_DELTA_NOT_CONSERVED: product %, fg %, cogs %, other %',
      p_product_id,v_df,v_dc,v_do;
  end if;
  if abs(v_df)<=0.005 and abs(v_dc)<=0.005 and abs(v_do)<=0.005 then
    return;
  end if;

  -- AZ (handoff §23.7): on a late supplier invoice with an open date the COGS and other legs follow each piece: the change
  -- of a lot's HPP in this statement (per piece) times its pieces sold (sales, returns, their reversals) or out otherwise
  -- (adjustment, BS, relabel, their reversals) as of each day of those movements, never before the invoice date nor after
  -- today; each day posts the change of those balances, FG balancing, and the last day takes the exact remainder. The FG
  -- source leg of the opening lot itself (OPENING_HPP_SOURCE, at the invoice date) is unchanged: the lot exists since
  -- cutover. Every other caller and a closed date post one journal on the caller's date, as before.
  if erp.invoice_recost_economic_date_v1() is not null and (abs(v_dc)>0.005 or abs(v_do)>0.005)
     and not exists(select 1 from erp.accounting_period_control c where c.singleton_id=1 and c.closed_through is not null and p_effective_date<=c.closed_through) then
    for r in
      with lots as(
        select fl.id,
          coalesce((select case when coalesce(hv.qty_basis_pcs,0)>0 then hv.total_cost/hv.qty_basis_pcs else 0 end
            from erp.hpp_versions hv where hv.lot_id=fl.id and hv.is_current),0)
          -- Independent review of AZ rev2 (3): against what the last opening-lot sync posted (its state is written after
          -- this call), so a second sync in the same statement does not count the first one's change again.
          -coalesce((select os.current_hpp from erp.opening_lot_hpp_gl_state os where os.lot_id=fl.id),
            (select case when coalesce(pv.qty_basis_pcs,0)>0 then pv.total_cost/pv.qty_basis_pcs else 0 end
            from erp.hpp_versions pv where pv.lot_id=fl.id and pv.calculated_at<statement_timestamp()
            order by pv.calculated_at desc,pv.version_no desc limit 1),0) dh
        from erp.fg_lots fl where fl.product_id=p_product_id and fl.po_id is null
          and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
      ), ev as(
        select greatest(p_effective_date,least(erp._cp3_business_date(statement_timestamp()),erp._cp3_business_date(m.physical_at))) d,l.dh,
          coalesce(o.movement_type,m.movement_type) k,m.qty_signed::numeric q
        from erp.fg_stock_movements m join lots l on l.id=m.lot_id and l.dh<>0
        left join erp.fg_stock_movements o on m.movement_type='REVERSAL' and o.id=m.reversal_of_id
        where coalesce(o.movement_type,m.movement_type) in('SALE','SALE_RETURN','ADJUSTMENT','BS_OUT','REBRAND_OUT','REBRAND_IN')
      )
      select d,sum(sum(case when k in('SALE','SALE_RETURN') then -q*dh else 0 end)) over(order by d) c,
        sum(sum(case when k in('SALE','SALE_RETURN') then 0 else -q*dh end)) over(order by d) o
      from ev group by d order by d
    loop
      v_c:=round(r.c,2);v_o:=round(r.o,2);
      v_acc:=v_acc||jsonb_build_object(r.d::text,jsonb_build_object('c',v_c-v_sc,'o',v_o-v_so));
      v_sc:=v_c;v_so:=v_o;v_end:=greatest(coalesce(v_end,r.d),r.d);
    end loop;
    v_end:=coalesce(v_end,p_effective_date);
    v_acc:=v_acc||jsonb_build_object(v_end::text,jsonb_build_object(
      'c',coalesce((v_acc->(v_end::text)->>'c')::numeric,0)+v_dc-v_sc,
      'o',coalesce((v_acc->(v_end::text)->>'o')::numeric,0)+v_do-v_so));
    v_rf:=b.fg_value;v_rc:=b.cogs_value;v_ro:=b.other_out_value;
    for r in select key::date d,value v from jsonb_each(v_acc) order by 1 loop
      v_c:=(r.v->>'c')::numeric;v_o:=(r.v->>'o')::numeric;v_f:=-(v_c+v_o);
      continue when abs(v_c)<=0.005 and abs(v_o)<=0.005;
      v_lines:='[]'::jsonb;
      if abs(v_f)>0.005 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','FG_INVENTORY',
        'debit',greatest(v_f,0),'credit',greatest(-v_f,0),'product_id',p_product_id)); end if;
      if abs(v_c)>0.005 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','COGS',
        'debit',greatest(v_c,0),'credit',greatest(-v_c,0),'product_id',p_product_id)); end if;
      -- The other bucket stays on the one account the single journal would use for the product's total other change.
      if abs(v_o)>0.005 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key',
        case when v_do>0 then 'OTHER_EXPENSE' else 'OTHER_INCOME' end,
        'debit',greatest(v_o,0),'credit',greatest(-v_o,0),'product_id',p_product_id)); end if;
      v_ev:=gen_random_uuid();
      v_journal:=erp.post_journal('NON_PO_HPP_GL_SYNC_V2620F',v_ev,r.d,
        'Cumulative non-PO HPP redistribution · dated from the goods · '||p_reason,v_lines);
      insert into erp.non_po_hpp_gl_sync_events_v2620f(
        id,product_id,trigger_source_type,trigger_source_id,effective_date,
        old_fg_value,new_fg_value,fg_delta,old_cogs_value,new_cogs_value,cogs_delta,
        old_other_out_value,new_other_out_value,other_delta,journal_entry_id,reason,created_by
      ) values(
        v_ev,p_product_id,p_trigger_source_type,p_trigger_source_id,r.d,
        v_rf,v_rf+v_f,v_f,v_rc,v_rc+v_c,v_c,v_ro,v_ro+v_o,v_o,v_journal,p_reason,erp.current_app_user_id());
      v_rf:=v_rf+v_f;v_rc:=v_rc+v_c;v_ro:=v_ro+v_o;
    end loop;
    perform erp.assert_non_po_product_hpp_target_book_v2620f(p_product_id);
    return;
  end if;

  if abs(v_df)>0.005 then
    v_lines:=v_lines||jsonb_build_array(case when v_df>0
      then jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_df,
        'credit',0,'product_id',p_product_id)
      else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,
        'credit',abs(v_df),'product_id',p_product_id) end);
  end if;
  if abs(v_dc)>0.005 then
    v_lines:=v_lines||jsonb_build_array(case when v_dc>0
      then jsonb_build_object('mapping_key','COGS','debit',v_dc,
        'credit',0,'product_id',p_product_id)
      else jsonb_build_object('mapping_key','COGS','debit',0,
        'credit',abs(v_dc),'product_id',p_product_id) end);
  end if;
  if abs(v_do)>0.005 then
    v_lines:=v_lines||jsonb_build_array(case when v_do>0
      then jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_do,
        'credit',0,'product_id',p_product_id)
      else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,
        'credit',abs(v_do),'product_id',p_product_id) end);
  end if;

  v_journal:=erp.post_journal(
    'NON_PO_HPP_GL_SYNC_V2620F',v_event,p_effective_date,
    'Cumulative non-PO HPP redistribution · '||p_reason,v_lines
  );
  insert into erp.non_po_hpp_gl_sync_events_v2620f(
    id,product_id,trigger_source_type,trigger_source_id,effective_date,
    old_fg_value,new_fg_value,fg_delta,
    old_cogs_value,new_cogs_value,cogs_delta,
    old_other_out_value,new_other_out_value,other_delta,
    journal_entry_id,reason,created_by
  ) values(
    v_event,p_product_id,p_trigger_source_type,p_trigger_source_id,
    p_effective_date,b.fg_value,t.fg_value,v_df,
    b.cogs_value,t.cogs_value,v_dc,
    b.other_out_value,t.other_out_value,v_do,
    v_journal,p_reason,erp.current_app_user_id()
  );
  perform erp.assert_non_po_product_hpp_target_book_v2620f(p_product_id);
end
$function$;
CREATE OR REPLACE FUNCTION erp.refresh_accessory_hpp_after_material_recost(p_material_id uuid, p_reason text DEFAULT 'Accessory historical moving-average recost'::text)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_category uuid;
  r record;
  v_new numeric(18,6);
  v_changed integer:=0;
  v_po uuid;
  v_rev uuid;v_old numeric;v_newtot numeric;v_d numeric;v_lot uuid;v_lot_po uuid;v_prod uuid;v_lotday date;v_e date;v_date date;
begin
  perform erp.require_internal();
  select accessory_category_id into v_category from erp.materials where id=p_material_id and material_type='ACCESSORY';
  if v_category is null then return 0; end if;
  perform pg_advisory_xact_lock(hashtextextended('ACCESSORY_HPP_CATEGORY|'||v_category::text,0));

  create temporary table if not exists pg_temp.erp_accessory_hpp_changed_pos(po_id uuid primary key) on commit drop;
  truncate pg_temp.erp_accessory_hpp_changed_pos;

  for r in
    select s.id,s.po_id,s.costing_basis_at,s.category_avg_cost_base_snapshot,s.hpp_unit_cost_base_snapshot
    from erp.fg_accessory_cost_snapshots s
    where s.category_id=v_category and s.hpp_method='CATEGORY_MOVING_AVG'
    order by s.costing_basis_at,s.id
    for update
  loop
    v_new:=erp.accessory_category_weighted_avg_cost_at(v_category,r.costing_basis_at);
    if v_new is null then
      raise exception 'Historical accessory recost would remove the valuation basis for FG accessory snapshot %. Correct/reverse the upstream inventory event first.',r.id;
    end if;
    if abs(v_new-r.hpp_unit_cost_base_snapshot)>0.000001 then
      insert into erp.fg_accessory_cost_revisions(snapshot_id,material_id,old_category_avg_cost,new_category_avg_cost,old_hpp_unit_cost,new_hpp_unit_cost,reason,changed_by)
      values(r.id,p_material_id,r.category_avg_cost_base_snapshot,v_new,r.hpp_unit_cost_base_snapshot,v_new,coalesce(nullif(trim(p_reason),''),'Accessory historical moving-average recost'),erp.current_app_user_id())
      returning id into v_rev;
      select total_hpp_cost,lot_id into v_old,v_lot from erp.fg_accessory_cost_snapshots where id=r.id;
      update erp.fg_accessory_cost_snapshots
      set category_avg_cost_base_snapshot=v_new,hpp_unit_cost_base_snapshot=v_new
      where id=r.id;
      -- AZ (independent review of AY rev7): the lot's accessory HPP entered WIP once, with the accrual
      -- (ACCESSORY_REIMBURSE_ACCRUAL: WIP against the Mandor reimbursement and its variance); the PO HPP sync below moves the
      -- change of that HPP out of WIP, so an accrued lot's change enters WIP against the reimbursement variance (the
      -- reimbursement itself is fixed), dated as the sync dates it: the lot day (never before the invoice date, never after
      -- today) on a late invoice with an open date, the invoice date when closed, today otherwise.
      select total_hpp_cost into v_newtot from erp.fg_accessory_cost_snapshots where id=r.id;
      v_d:=round(coalesce(v_newtot,0)-coalesce(v_old,0),2);
      if abs(v_d)>0.005 and exists(select 1 from erp.journal_entries where source_type='ACCESSORY_REIMBURSE_ACCRUAL'
                                     and source_id=v_lot and status='POSTED') then
        select fl.po_id,fl.product_id,erp._cp3_business_date(fl.produced_at) into v_lot_po,v_prod,v_lotday from erp.fg_lots fl where fl.id=v_lot;
        v_e:=erp.invoice_recost_economic_date_v1();
        v_date:=case when v_e is null then erp._cp3_business_date(statement_timestamp())
                     when exists(select 1 from erp.accounting_period_control c where c.singleton_id=1 and c.closed_through is not null and v_e<=c.closed_through) then v_e
                     else least(greatest(v_e,v_lotday),erp._cp3_business_date(statement_timestamp())) end;
        perform erp.post_journal('ACCESSORY_HPP_RECOST',v_rev,v_date,'Accessory HPP recost of an accrued lot: WIP against the reimbursement variance',
          jsonb_build_array(
            jsonb_build_object('mapping_key','WIP','debit',greatest(v_d,0),'credit',greatest(-v_d,0),'po_id',v_lot_po,'product_id',v_prod),
            jsonb_build_object('mapping_key','ACCESSORY_REIMBURSE_VARIANCE','debit',greatest(-v_d,0),'credit',greatest(v_d,0),'po_id',v_lot_po,'product_id',v_prod)));
      end if;
      insert into pg_temp.erp_accessory_hpp_changed_pos(po_id) values(r.po_id) on conflict do nothing;
      v_changed:=v_changed+1;
    end if;
  end loop;

  for v_po in select po_id from pg_temp.erp_accessory_hpp_changed_pos order by po_id loop
    perform erp.rebuild_po_hpp(v_po,'Accessory moving-average recost: '||coalesce(nullif(trim(p_reason),''),'historical material recost'));
    perform erp.propagate_conversion_hpp_for_po(v_po);
    perform erp.sync_po_hpp_to_gl(v_po,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  end loop;
  return v_changed;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.reverse_qc(p_qc_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.qc_inspections%rowtype;
  r record; l record; b record;
  v_journal uuid;
  v_po_status text;
begin
  perform erp.require_internal();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal QC wajib diisi'; end if;
  select * into h from erp.qc_inspections where id=p_qc_id for update;
  if h.id is null then raise exception 'QC tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya QC POSTED yang dapat direverse'; end if;
  select status into v_po_status from erp.production_orders where id=h.po_id for update;
  if v_po_status='FINISHED' then raise exception 'PO sudah FINISHED. Reopen/koreksi downstream terlebih dahulu sebelum reversal QC.'; end if;

  for b in select bc.* from erp.bs_cases bc where bc.qc_item_id in (select id from erp.qc_inspection_items where inspection_id=h.id) and bc.status<>'CANCELLED' for update loop
    if exists(select 1 from erp.rework_orders where bs_case_id=b.id and status<>'CANCELLED')
       or exists(select 1 from erp.bs_resolutions where bs_case_id=b.id) then
      raise exception 'BS hasil QC ini sudah diproses/rework. Batalkan downstream BS terlebih dahulu.';
    end if;
  end loop;

  for l in
    select fl.* from erp.fg_lots fl
    where fl.qc_item_id in (select id from erp.qc_inspection_items where inspection_id=h.id)
      and fl.lot_origin='PRODUCTION'
    for update
  loop
    if erp.fg_lot_has_active_downstream(l.id,'QC_GOOD','QC_ITEM',l.qc_item_id) then
      raise exception 'FG hasil QC masih dipakai transaksi downstream aktif. Reverse transaksi downstream terlebih dahulu.';
    end if;
    if exists(select 1 from erp.contractor_accessory_reimbursement_entitlements e where e.lot_id=l.id and e.payroll_status<>'UNALLOCATED') then
      raise exception 'Hak reimbursement aksesori dari QC ini sudah masuk payroll. Cancel/reverse payroll terlebih dahulu.';
    end if;
  end loop;

  for l in
    select fl.* from erp.fg_lots fl
    where fl.qc_item_id in (select id from erp.qc_inspection_items where inspection_id=h.id) and fl.lot_origin='PRODUCTION'
    for update
  loop
    select id into v_journal from erp.journal_entries
    where source_type='ACCESSORY_REIMBURSE_ACCRUAL' and source_id=l.id and status='POSTED'
    order by posting_at desc,id desc limit 1;
    if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
    -- AZ rev2: the lot's accessory HPP recost journals go with its accrual.
    for v_journal in select je.id from erp.journal_entries je join erp.fg_accessory_cost_revisions rv on rv.id=je.source_id
      join erp.fg_accessory_cost_snapshots sn on sn.id=rv.snapshot_id
      where je.source_type='ACCESSORY_HPP_RECOST' and je.status='POSTED' and sn.lot_id=l.id order by je.posting_at,je.id
    loop perform erp.reverse_journal(v_journal,p_reason); end loop;
    update erp.contractor_accessory_reimbursement_entitlements set payroll_status='CANCELLED' where lot_id=l.id and payroll_status='UNALLOCATED';
    for r in select fm.id from erp.fg_stock_movements fm where fm.lot_id=l.id and fm.movement_type='QC_GOOD' and fm.source_type='QC_ITEM' and fm.source_id=l.qc_item_id and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id) loop
      perform erp.reverse_fg_movement(r.id,p_reason);
    end loop;
    update erp.fg_lots set lot_origin='VOIDED_PRODUCTION',is_open=false where id=l.id;
  end loop;

  update erp.bs_cases set status='CANCELLED',notes=concat_ws(E'\n',notes,'CANCELLED karena source QC direverse: '||p_reason),updated_at=statement_timestamp()
  where qc_item_id in (select id from erp.qc_inspection_items where inspection_id=h.id) and status<>'CANCELLED';
  update erp.qc_inspections set status='REVERSED',updated_at=statement_timestamp() where id=h.id;

  if v_po_status not in ('ON_HOLD','CANCELLED') then
    if exists(select 1 from erp.qc_inspections where po_id=h.po_id and status='POSTED')
       or exists(select 1 from erp.laundry_receipts lr join erp.laundry_deliveries ld on ld.id=lr.delivery_id where ld.po_id=h.po_id and lr.status='POSTED' and ld.status<>'REVERSED') then
      update erp.production_orders set status='QC',current_stage='QC',updated_at=statement_timestamp() where id=h.po_id;
    elsif exists(select 1 from erp.laundry_deliveries where po_id=h.po_id and status not in('DRAFT','REVERSED')) then
      update erp.production_orders set status='LAUNDRY',current_stage='LAUNDRY',updated_at=statement_timestamp() where id=h.po_id;
    elsif exists(select 1 from erp.cutting_groups where po_id=h.po_id and picked_up_at is not null) then
      update erp.production_orders set status='SEWING',current_stage='SEWING',updated_at=statement_timestamp() where id=h.po_id;
    else
      update erp.production_orders set status='CUTTING',current_stage='CUTTING',updated_at=statement_timestamp() where id=h.po_id;
    end if;
  end if;

  perform erp.sync_laundry_accrual(h.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  perform erp.rebuild_po_hpp(h.po_id,'QC reversed: '||p_reason);
  perform erp.propagate_conversion_hpp_for_po(h.po_id);
  perform erp.sync_po_hpp_to_gl(h.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('qc_inspections',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;
CREATE OR REPLACE FUNCTION erp.reverse_rework_completion(p_rework_order_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  r erp.rework_orders%rowtype;
  b erp.bs_cases%rowtype;
  x record;
  v_journal uuid;
  v_total numeric(24,6):=0;
  v_remaining integer:=0;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal hasil rework wajib diisi'; end if;
  select * into r from erp.rework_orders where id=p_rework_order_id for update;
  if r.id is null then raise exception 'Rework order tidak ditemukan'; end if;
  if r.status='CANCELLED' and r.cost_posted then return; end if;
  if r.status<>'COMPLETED' or not r.cost_posted then raise exception 'Hanya rework COMPLETED yang sudah diposting biayanya yang dapat direverse'; end if;
  select * into b from erp.bs_cases where id=r.bs_case_id for update;

  if exists(
    select 1 from erp.payroll_work_items pwi
    join erp.payroll_settlements ps on ps.id=pwi.payroll_id
    join erp.rework_component_lines rcl on rcl.id=pwi.source_id
    where pwi.source_type='REWORK' and rcl.rework_order_id=r.id and ps.status<>'REVERSED'
  ) then raise exception 'Upah rework ini sudah masuk payroll. Cancel/reverse payroll aktif terlebih dahulu.'; end if;

  if r.good_fg_lot_id is not null then
    if erp.fg_lot_has_active_downstream(r.good_fg_lot_id,'REWORK_IN','REWORK_ORDER',r.id) then
      raise exception 'FG hasil rework masih dipakai transaksi downstream aktif. Reverse transaksi downstream terlebih dahulu.';
    end if;
    if exists(select 1 from erp.contractor_accessory_reimbursement_entitlements e where e.lot_id=r.good_fg_lot_id and e.payroll_status<>'UNALLOCATED') then
      raise exception 'Reimbursement aksesori hasil rework sudah masuk payroll. Cancel/reverse payroll terlebih dahulu.';
    end if;
  end if;

  select coalesce(sum(amount_payable),0) into v_total from erp.rework_component_lines where rework_order_id=r.id;
  select id into v_journal from erp.journal_entries where source_type='REWORK_COMPLETION' and source_id=r.id and status='POSTED' order by posting_at desc,id desc limit 1;
  if r.destination_type='CONTRACTOR' and v_total>0.005 and v_journal is null then raise exception 'Jurnal biaya/upah rework tidak ditemukan; reversal dibatalkan agar hutang mandor/HPP tidak rusak'; end if;

  if r.good_fg_lot_id is not null then
    select id into v_journal from erp.journal_entries where source_type='ACCESSORY_REIMBURSE_ACCRUAL' and source_id=r.good_fg_lot_id and status='POSTED' order by posting_at desc,id desc limit 1;
    if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
    -- AZ rev2: the lot's accessory HPP recost journals go with its accrual.
    for v_journal in select je.id from erp.journal_entries je join erp.fg_accessory_cost_revisions rv on rv.id=je.source_id
      join erp.fg_accessory_cost_snapshots sn on sn.id=rv.snapshot_id
      where je.source_type='ACCESSORY_HPP_RECOST' and je.status='POSTED' and sn.lot_id=r.good_fg_lot_id order by je.posting_at,je.id
    loop perform erp.reverse_journal(v_journal,p_reason); end loop;
    update erp.contractor_accessory_reimbursement_entitlements set payroll_status='CANCELLED' where lot_id=r.good_fg_lot_id and payroll_status='UNALLOCATED';
    for x in select fm.id from erp.fg_stock_movements fm where fm.lot_id=r.good_fg_lot_id and fm.movement_type='REWORK_IN' and fm.source_type='REWORK_ORDER' and fm.source_id=r.id and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id)
    loop perform erp.reverse_fg_movement(x.id,p_reason); end loop;
    update erp.fg_lots set lot_origin='VOIDED_PRODUCTION',is_open=false where id=r.good_fg_lot_id and lot_origin='PRODUCTION';
  end if;

  select id into v_journal from erp.journal_entries where source_type='REWORK_COMPLETION' and source_id=r.id and status='POSTED' order by posting_at desc,id desc limit 1;
  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
  delete from erp.bs_resolutions where source_rework_order_id=r.id;
  update erp.rework_orders set status='CANCELLED',updated_at=statement_timestamp(),notes=concat_ws(E'\n',notes,'CANCELLED after posted completion reversal: '||p_reason) where id=r.id;

  select greatest(b.qty_pcs-coalesce(sum(br.qty_pcs),0),0)::integer into v_remaining from erp.bs_resolutions br where br.bs_case_id=b.id;
  if v_remaining<=0 then update erp.bs_cases set status='RESOLVED',updated_at=statement_timestamp() where id=b.id;
  elsif exists(select 1 from erp.rework_orders ro where ro.bs_case_id=b.id and ro.id<>r.id and ro.status in ('OPEN','IN_PROGRESS','PARTIAL')) then update erp.bs_cases set status='IN_REWORK',updated_at=statement_timestamp() where id=b.id;
  elsif v_remaining<b.qty_pcs then update erp.bs_cases set status='PARTIAL',updated_at=statement_timestamp() where id=b.id;
  else update erp.bs_cases set status='OPEN',updated_at=statement_timestamp() where id=b.id; end if;

  if b.po_id is not null then
    perform erp.rebuild_po_hpp(b.po_id,'Rework completion reversed: '||p_reason);
    perform erp.propagate_conversion_hpp_for_po(b.po_id);
    perform erp.sync_po_hpp_to_gl(b.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  end if;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason) values('rework_orders',r.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;
CREATE OR REPLACE FUNCTION erp.complete_initial_import_wip_v1(p_payload jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
 SET "DateStyle" TO 'ISO, YMD'
AS $function$
declare s erp.initial_import_production_sources%rowtype;i erp.opening_balance_items%rowtype;
 v_product_count integer;v_batch uuid;v_product uuid;v_location uuid;v_qty integer;v_remaining integer;v_lot uuid;v_output uuid;v_date date;v_at timestamptz;
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
    -- AZ rev2: the lot's accessory HPP recost journals go with its accrual.
    for v_movement in select je.id from erp.journal_entries je join erp.fg_accessory_cost_revisions rv on rv.id=je.source_id
      join erp.fg_accessory_cost_snapshots sn on sn.id=rv.snapshot_id
      where je.source_type='ACCESSORY_HPP_RECOST' and je.status='POSTED' and sn.lot_id=v_prior.lot_id order by je.posting_at,je.id
    loop perform erp.reverse_journal(v_movement,v_reason); end loop;
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
  select count(*),(array_agg(x.id order by x.id))[1] into v_product_count,v_product
  from (
    select p.id from erp.products p join erp.production_orders po on po.id=s.po_id
    join erp.brands b on b.id=p.brand_id
    where lower(btrim(p.sku))=lower(btrim(p_payload->>'product_sku'))
      and p.is_active and p.model_id=po.model_id and p.size_id=s.size_id
      and p.effective_from<(v_date+1)::timestamp at time zone 'Asia/Jakarta'
      and (p.effective_to is null or p.effective_to>v_date::timestamp at time zone 'Asia/Jakarta')
      and (nullif(btrim(p_payload->>'brand_code'),'') is null
        or lower(btrim(b.brand_code))=lower(btrim(p_payload->>'brand_code')))
      and (nullif(p_payload->>'product_id','') is null or p.id=(p_payload->>'product_id')::uuid)
    order by p.id for share of p
  ) x;
  if v_product_count=0 then raise exception 'product_sku: pilih produk aktif dengan merek, model PO, ukuran saldo, dan tanggal hasil yang sesuai';end if;
  if v_product_count<>1 then raise exception 'AS_WIP_PRODUCT_AMBIGUOUS: SKU ada pada beberapa identitas produk; pilih merek atau identitas produk yang tepat';end if;
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
  v_book_date date;
begin
  perform erp.require_owner_admin();
  select * into h from erp.material_supplier_invoices where id=p_invoice_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Material supplier invoice must be DRAFT'; end if;
  -- AZ rev2 (owner, 24 Sep 2026, option 1): booked no earlier than the latest receipt day of its lines; the invoice date
  -- stays the document date (due date, AP ageing).
  select greatest(h.invoice_date,coalesce(max(erp._cp3_business_date(ph.physical_at)),h.invoice_date)) into v_book_date
  from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id
  join erp.material_purchase_headers ph on ph.id=i.purchase_id where l.invoice_id=h.id;
  insert into erp.invoice_recost_execution_context(transaction_id,invoice_date,source_id) values(txid_current(),v_book_date,h.id);
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
  perform erp._cp6_apply_supplier_cent_event('MATERIAL_SUPPLIER_INVOICE',h.id,v_book_date,'Supplier document cents '||h.id::text,v_n_before,false);
  delete from erp.invoice_recost_execution_context where transaction_id=txid_current();
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
  v_book_date date;
begin
  perform erp.require_owner_admin();
  select * into h from erp.material_purchase_cost_corrections where id=p_correction_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Material purchase cost correction must be DRAFT'; end if;
  select * into p from erp.material_purchase_headers where id=h.purchase_id for update;
  -- AZ rev2 (owner, 24 Sep 2026, option 1, as erp.post_material_supplier_invoice): booked no earlier than the receipt day of
  -- its purchase; the invoice date stays the document date.
  v_book_date:=greatest(h.invoice_date,coalesce(erp._cp3_business_date(p.physical_at),h.invoice_date));
  insert into erp.invoice_recost_execution_context(transaction_id,invoice_date,source_id) values(txid_current(),v_book_date,h.id);
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
  perform erp._cp6_apply_supplier_cent_event('MATERIAL_PURCHASE_COST_CORRECTION',h.id,v_book_date,'Supplier document cents '||h.id::text,v_n_before,false);
  delete from erp.invoice_recost_execution_context where transaction_id=txid_current();
end;
$function$;
insert into erp.schema_migrations(version,description) values('v2.6.20az','Material recost corrections dated from the physical movement: WIP from the cutting day, material until then');
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule','cp6_v2620ay_rollback_capsule','cp6_v2620az_rollback_capsule')
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
  raise exception 'AZ_INSTALLED_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
update erp.cp6_v2620az_rollback_capsule set installed_definition_sha256=encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex');
do $after_data$ declare v_table text;v_hash jsonb;v_after jsonb;v_before jsonb; begin
 v_after:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620az_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_after:=v_after||jsonb_build_object(v_table,v_hash);
 end loop;
 select snapshot->'before' into v_before from pg_temp.cp6_release_boundary;
 if (v_after-array[]::text[]) is distinct from v_before or exists(select 1 from unnest(array[]::text[]) t where (v_after->t->>'count') is distinct from '0')
  then raise exception 'AZ_INSTALL_CHANGED_DATA';end if;
 if exists(with live as (select p.oid::regprocedure::text as identity,encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') as definition_sha256,
  array(select a::text from unnest(p.proacl)a order by a::text) as acl,pg_get_userbyid(p.proowner) as owner
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p')) select 1 from pg_temp.cp6_release_functions f left join live x on x.identity=f.identity
  where f.identity<>all(coalesce((select array_agg(object_regidentity) from erp.cp6_v2620az_rollback_capsule),'{}'))
  and (x.identity is null or (x.definition_sha256,x.acl,x.owner) is distinct from (f.definition_sha256,f.acl,f.owner)))
  then raise exception 'AZ_CAPSULE_INCOMPLETE';end if;
 update erp.cp6_v2620az_rollback_capsule set boundary_snapshot=(select snapshot from pg_temp.cp6_release_boundary)||jsonb_build_object('after',v_after);
end $after_data$;
do $capsule_guard$
declare expected jsonb;actual jsonb;boundary jsonb;
begin
 if not exists(select 1 from pg_class where oid='erp.cp6_v2620az_rollback_capsule'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='erp.cp6_v2620az_rollback_capsule'::regclass and a.grantee<>p.relowner)
   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='erp.cp6_v2620az_rollback_capsule'::regclass and a.grantee<>'postgres'::regrole)
   or exists(select 1 from pg_policy where polrelid='erp.cp6_v2620az_rollback_capsule'::regclass)
   or exists(select 1 from pg_trigger where tgrelid='erp.cp6_v2620az_rollback_capsule'::regclass and not tgisinternal)
   or (select count(*) from erp.cp6_v2620az_rollback_capsule)<>12 then raise exception 'AZ_CAPSULE_SECURITY_OR_COUNT';end if;
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620an_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620an_rollback_capsule'::regclass)) into expected;
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620az_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620az_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620az_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620az_rollback_capsule'::regclass)) into actual;
 if actual is distinct from expected then raise exception 'AZ_CAPSULE_SHAPE_DRIFT';end if;
 select boundary_snapshot into boundary from erp.cp6_v2620az_rollback_capsule limit 1;
 if 12>0 and (boundary is null or exists(select 1 from erp.cp6_v2620az_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before'])) then raise exception 'AZ_CAPSULE_BOUNDARY';end if;
 if exists(select 1 from erp.cp6_v2620az_rollback_capsule where object_regidentity<>all(array['erp.sync_material_cost_revaluation(uuid)','erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)','erp.sync_finished_po_wip_residual(uuid,date,text)','erp.guard_pocket_period_v1()','erp.sync_initial_import_bs_value_v1(uuid,date)','erp.sync_non_po_product_hpp_to_gl_v2620f(uuid,date,text,uuid,text)','erp.refresh_accessory_hpp_after_material_recost(uuid,text)','erp.reverse_qc(uuid,text)','erp.reverse_rework_completion(uuid,text)','erp.complete_initial_import_wip_v1(jsonb)','erp.post_material_supplier_invoice(uuid)','erp.post_material_purchase_cost_correction(uuid)']::text[])
   or definition_sha256 is distinct from encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex')
   or installed_definition_sha256 is null or installed_definition_sha256=definition_sha256
   or installed_definition_sha256 is distinct from encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex'))
  then raise exception 'AZ_CAPSULE_SOURCE_DRIFT';end if;
end $capsule_guard$;
commit;
