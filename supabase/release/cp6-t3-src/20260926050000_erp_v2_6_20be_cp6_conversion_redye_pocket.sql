-- CP6 BE: physical SKU conversion, rework/redye service and historical pocket allocation (LAU-06b and ALL-C04). Release candidate of the T3 combined package; closed, drained maintenance required.
begin;
-- Built by scripts/cp6_t3_awx_release.py from supabase/dev/cp6_be_t1_family.sql (sha256 68e5276a7f4fe18a17722fccc8187cab13bda0f002e9f540abb84839c1422940): the T1 body below is unchanged apart from the
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
 if exists(select 1 from erp.schema_migrations where version='v2.6.20be') or to_regclass('erp.cp6_v2620be_rollback_capsule') is not null
  or to_regclass('erp.be_execution_context_v1') is not null or to_regclass('erp.be_conversion_sources_v1') is not null or to_regclass('erp.be_conversion_returns_v1') is not null or to_regclass('erp.be_conversion_cost_sources_v1') is not null or to_regclass('erp.be_conversion_cost_events_v1') is not null or to_regclass('erp.be_nonpo_transfer_events_v1') is not null or to_regclass('erp.be_rework_targets_v1') is not null or to_regclass('erp.be_redye_services_v1') is not null or to_regclass('erp.be_redye_price_events_v1') is not null or to_regclass('erp.be_pocket_usage_v1') is not null or to_regclass('erp.be_pocket_sewing_v1') is not null or to_regclass('erp.be_pocket_source_events_v1') is not null or to_regclass('erp.be_pocket_target_events_v1') is not null or to_regclass('erp.be_pocket_receipt_origins_v1') is not null
 then raise exception 'BE_EXACT_PREDECESSOR_WITHOUT_SUCCESSOR_REQUIRED';end if;
end $admission$;
do $predecessor$
begin
 if exists(select 1 from supabase_migrations.schema_migrations where version>'20260925040000') then raise exception 'BE_EXACT_PREDECESSOR_REQUIRED';end if;
end $predecessor$;
do $prior_platform$
declare r record;
begin
 for r in select * from jsonb_to_recordset('[{"marker":"v2.6.20ac","stamp":"20260915031500","name":"erp_v2_6_20ac_cp6_temporal_surface_closure","sha":"7b5690a2eddf618833d352dc75eb95aa1ef4dbcfb25d39b30374b733d33dadbc"},{"marker":"v2.6.20ad","stamp":"20260915113627","name":"erp_v2_6_20ad_cp6_opening_material_business_day","sha":"cd4879eb9b053e3b7a975e1430f481131e377f260ece2f19f07bfb4c98498c1d"},{"marker":"v2.6.20ae","stamp":"20260915201500","name":"erp_v2_6_20ae_cp6_opening_roll_integrity","sha":"228d9185501d418835e6434e64e1445be7b12ce2f517778ea63d789d478461c1"},{"marker":"v2.6.20af","stamp":"20260916014332","name":"erp_v2_6_20af_cp6_posted_child_integrity","sha":"54c5f73b99a2e63c858a777f669432f28260177daf4c45d806bb0e8a7c7c8e8e"},{"marker":"v2.6.20ag","stamp":"20260916050822","name":"erp_v2_6_20ag_cp6_sale_reservation_lineage","sha":"bff1d7d82917ce226ad0fb8823418fa14e497407d9659e125dc01ed5e2fd5944"},{"marker":"v2.6.20ah","stamp":"20260916070451","name":"erp_v2_6_20ah_cp6_return_allocation_eligibility","sha":"e5312744a2ef9ac53717c97e155fccf96a33e2f6a0c68c4b9c45f378ac538219"},{"marker":"v2.6.20ai","stamp":"20260916090022","name":"erp_v2_6_20ai_cp6_work_source_lineage","sha":"d3a604e53e599221afd46d1397e0d0660ebd8dc48db27113dfa63d3c3613a61c"},{"marker":"v2.6.20aj","stamp":"20260916202400","name":"erp_v2_6_20aj_cp6_rework_output_lineage","sha":"2e6cd4e94b52a27c83d2ba134a996c1db66a6f7ff617a5895f8c14769673f9ea"},{"marker":"v2.6.20ak","stamp":"20260917033516","name":"erp_v2_6_20ak_cp6_import_reference_preview","sha":"0d42825b2f2fcb38b9678fe1e6982b0c63290aac012b92be224f4323d495c536"},{"marker":"v2.6.20al","stamp":"20260917054049","name":"erp_v2_6_20al_cp6_opening_value_validation","sha":"74a5d5e14d79c7bbafa731aaf2fe1708bc575299600261f7412f1f7ea7323920"},{"marker":"v2.6.20am","stamp":"20260921214120","name":"erp_v2_6_20am_cp6_transfer_integrity","sha":"d5b155edb19aa8ca949036ba8a9cf67090478083c2e1ae6cc5bbf00b445716a5"},{"marker":"v2.6.20an","stamp":"20260921223438","name":"erp_v2_6_20an_cp6_cutting_selectors","sha":"21ac97ded4ed0cee9175c7fac7ef28ab6713d08b00766e1e5adc86bd38205e6c"},{"marker":"v2.6.20ao","stamp":"20260922135612","name":"erp_v2_6_20ao_cp6_invoice_retail","sha":"5687bb0236528d7e485e738ee2f96c2be0f4bde7e0d41c16bacee3a58183bdbb"},{"marker":"v2.6.20ap","stamp":"20260922135615","name":"erp_v2_6_20ap_cp6_connected_import_materials","sha":"fb8e14f0fd505edf730c0908f7e1c500cf850e29bcc0e90b3a51877224edd61b"},{"marker":"v2.6.20aq","stamp":"20260922161019","name":"erp_v2_6_20aq_cp6_accessory_lock_order","sha":"b1b4e449ca84ad524189640bcd76302cb277b9b690ed89f739ad5706e3cfac5a"},{"marker":"v2.6.20ar","stamp":"20260922185015","name":"erp_v2_6_20ar_cp6_opening_overlap","sha":"7da20a87d48493b4b64c10c395e8e54f87c1c40a835fbd09bbf2cdbc8866fa10"},{"marker":"v2.6.20as","stamp":"20260922210815","name":"erp_v2_6_20as_cp6_event_dates_product_identity","sha":"84e95211698eb2426995fd59d702bb42674f9fff675401be4861c9aa568cc1a8"},{"marker":"v2.6.20at","stamp":"20260923005153","name":"erp_v2_6_20at_cp6_wip_temporal_identity","sha":"f114a78918138a65f761488b77cadb1ab8a70ce6a6a88ae58a9d38656d1cfdb4"},{"marker":"v2.6.20au","stamp":"20260923045944","name":"erp_v2_6_20au_cp6_controlled_product_lifecycle","sha":"593b06092c2d47e03644afb1b7b5aef46c1442a56613f853a151b78ef738f2c2"},{"marker":"v2.6.20av","stamp":"20260923110000","name":"erp_v2_6_20av_cp6_identity_new_stock_cutoff","sha":"193e84efac8ead7cab681071e40070e1f9249f82cec1b7972f0576e8df25a2dc"},{"marker":"v2.6.20aw","stamp":"20260924010000","name":"erp_v2_6_20aw_cp6_close_readiness_engine","sha":"08826a25c14f8f18f5a168040b6f96dc4efe15c4498be5e92b0834601e77407c"},{"marker":"v2.6.20ax","stamp":"20260924010100","name":"erp_v2_6_20ax_cp6_fg_unsourced_receipts","sha":"32b4d33ebd80ed55951736c23be71b7eb79343c4c8dd623a32ae673924fc0a18"},{"marker":"v2.6.20ay","stamp":"20260924010200","name":"erp_v2_6_20ay_cp6_hpp_dated_from_goods","sha":"b41617d7d764e7ef3f25b323d6b6896a0f363623b1691a23c745ed34d12e5473"},{"marker":"v2.6.20az","stamp":"20260924010300","name":"erp_v2_6_20az_cp6_material_recost_dated_from_movement","sha":"576749761dbfb711005f76962f5c0287a151a80f6c6fe97b4e8f28e70671c0c2"},{"marker":"v2.6.20ba","stamp":"20260925010000","name":"erp_v2_6_20ba_cp6_audit_closure","sha":"e8fba02c91177eef3ccec94cd8156e04bcf2c550278caf9bf34244284b4cb123"},{"marker":"v2.6.20bb","stamp":"20260925020000","name":"erp_v2_6_20bb_cp6_open_cutover_states","sha":"966939292e04f0cbfbbf113f7ec831e4a448958f6e6861fc0eb16bc31a5fcab1"},{"marker":"v2.6.20bc","stamp":"20260925030000","name":"erp_v2_6_20bc_cp6_accessory_service_returns","sha":"6257d5d8acc9b466a99090ea8d6c4b7f9874da605b77079d0ba0f3c1878f5539"},{"marker":"v2.6.20bd","stamp":"20260925040000","name":"erp_v2_6_20bd_cp6_laundry_prices_invoices","sha":"6ca8fbb51e7257ab14191ea0606e6e1795bf06835bce2e02eb6b4014854fbf46"}]'::jsonb) as x(marker text,stamp text,name text,sha text) loop
  if not exists(select 1 from erp.schema_migrations where version=r.marker)
   or (select count(*) from supabase_migrations.schema_migrations where name=r.name)<>1
   or not exists(select 1 from supabase_migrations.schema_migrations where version=r.stamp and name=r.name
    and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')=r.sha) then
   raise exception 'BE_PRIOR_PLATFORM_DRIFT: %',r.name;
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
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule','cp6_v2620ay_rollback_capsule','cp6_v2620az_rollback_capsule','cp6_v2620ba_rollback_capsule','cp6_v2620bb_rollback_capsule','cp6_v2620bc_rollback_capsule','cp6_v2620bd_rollback_capsule','cp6_v2620be_rollback_capsule')
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
  raise exception 'BE_PREDECESSOR_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
do $historical_capsules$
declare r record;actual text;
begin
 for r in select * from jsonb_each_text('{"bs_resolution_v2619_rollback_capsule":"28ab388833da7da87384766ecaedadc66b4d048c303ee91e16f3939e34afdc39","bs_resolution_v2619a_rollback_capsule":"de8dfaab7b63b8742d383a089cdb05e73b629aad9f4df149e6a3c9fb590ef560","bs_resolution_v2619b_rollback_capsule":"d6d4f7457743d51679b5d25bf166ed69ca4b4f098cf5902ff985937531c2505d","bs_resolution_v2619c_rollback_capsule":"0207ba4f2ffba8ed61584709bbd884f1d2ee1a5981194fd7189a45afe8b3cbe1","cp3_r4_rollback_capsule":"7c01add62e66a4e2774a7199c2e77a04cca5e5942dbbba54d22cef720f82bc1d","cp45_v2617_rollback_capsule":"b9a43ce463de9905e94dd6538fd2a4952b0586a78c145f6f9d88aab7d6da3d80","cp45_v2617a_rollback_capsule":"b065dbcfdf1b59cb799e9f58caf6dd5ca7686e9f70826fce6a1ba8f140610022","cp4_v2616_rollback_capsule":"dde0a005dbe7cc93709bdfc6b961f4b9a76bf4db06fd7177d21dc79048af4d2f","cp6_v2620_rollback_capsule":"01f1e4e23211cff3c399d2d768a41be57980bfab00790715aa759b00a515e032","cp6_v2620a_rollback_capsule":"67befaaf327d2591e1ca1d654132ee483eba39b6cbb4f891c4719d817155d448","cp6_v2620aa_rollback_capsule":"eb0d6fb4fcac2ac06929d577101e604428e9a04821813c342e5b831147dc8948","cp6_v2620ab_rollback_capsule":"3be9a9166e3a607962be819fbe23d38fe455290a7a970dc2aad068079bf30785","cp6_v2620ac_relation_rollback_capsule":"2be5cbb62d1147e1e0d053dc4e447fe1d1258439352c297814c981c985959838","cp6_v2620ac_rollback_capsule":"51a8b08c9d96e66f03c2c8ba94ed3ed8fb15b26d1a2e4c65c58c614442dfa969","cp6_v2620ad_rollback_capsule":"5c3588109395b32ed743e0f4f5d789a3c59e3fffbab7469138f1f423c877ea9d","cp6_v2620ae_rollback_capsule":"6a75e02bf7b90c542fd9f2ac9534a2de066b047f5ffea65bffb1f83fa63c17f0","cp6_v2620af_rollback_capsule":"bfa89fc0e94d34b29405acedf551935f024942835f31cdc98f0f0983a9550288","cp6_v2620ag_rollback_capsule":"7ddfe6181f0c1c7439faf8a8150c542e958b3bafd8d18b5b2d1eb454fd7a85b7","cp6_v2620ah_rollback_capsule":"361be9321e5f4dadc7c7ec0e99ed746a98e7a4150178fc8355d23707c1507a93","cp6_v2620ai_rollback_capsule":"f2428dd712aa763b1379a4ae5b1a1e1e6ee175b355d8769b854a28f1355181c8","cp6_v2620aj_rollback_capsule":"8e24026dc90a2a92292c2cc6c8faa5fc3de991a19f326db494e0af2a518436f1","cp6_v2620ak_rollback_capsule":"dc7bfce7b9ee6a42e33cdf03cabd99d64435a4615245b2037fd6e4ee399aef10","cp6_v2620al_rollback_capsule":"c9e9aca042674efa5c6fa283e4b9ee47f3353ee9ee95b34e14ef1fd6b09bfde9","cp6_v2620am_rollback_capsule":"e781e631d06c6894c20b1fe6f9c65779f461d19c405c8ae74f28ed7d83ae6a26","cp6_v2620an_rollback_capsule":"ebfa8a281a32fe54babbdc209264ab422fde27f344d48561b90d2af022fe75b3","cp6_v2620ao_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620ap_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620aq_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620ar_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620as_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620at_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620au_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620av_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620aw_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620ax_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620ay_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620az_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620b_rollback_capsule":"f9bf784bff0c54e647f491e257a9649fd0c3e6f10c39ddfc0944c961b9dd7601","cp6_v2620ba_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620bb_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620bc_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620bd_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620c_rollback_capsule":"f88b1f5890ee8e7041758971bf9c9a3ce2bd0a7be6989fb95332c2dd7fa139aa","cp6_v2620d_rollback_capsule":"fa300c5554da4bb6812c61d726fd64f66329c97b085fa7d6ad5d0d8e5ae31235","cp6_v2620e_rollback_capsule":"143cd291cf4c12e78ab61e74e02ed03b08a48832a5064671868ff2bd2e3e1da7","cp6_v2620f_rollback_capsule":"076133b098e821fc2713af559618adf8aa3e204908f810af440fda355fc7a57f","cp6_v2620g_rollback_capsule":"ed9f4cacb47bd026ad6bdea373d1aa87044ed12aa60323cea453e3187dc488c4","cp6_v2620h_rollback_capsule":"4c25a060a2df3c22cd6fa9ff0b297163e223118a0d930b97bf1282b4756d909d","cp6_v2620i_rollback_capsule":"051203d95c44968abd8594f5bd48e289c4ac9a6c9fa49a89eee1086ad6b2c166","cp6_v2620j_rollback_capsule":"1393a8085d0f58717b13048c9cc3f7e9969ac86c351d6dfefdd2d4f43a735bd2","cp6_v2620k_rollback_capsule":"55aa71061f616ea11b361f0fabee2fd892f6438cc3f567cb9c135552ade42409","cp6_v2620l_rollback_capsule":"b4278768fce4ef307795953c14f607278c43bf474d76d3362e477280be08eb39","cp6_v2620m_rollback_capsule":"4b5f89d7bc4557f92b47716fe15640ab244c424fc1279433eb806d9d91d234e9","cp6_v2620n_rollback_capsule":"46e5ea4524613bb7a386551ada9e06888ea35eb987f9f5b864457fdd18bc3bc1","cp6_v2620o_rollback_capsule":"044e6b1a050df7e2a1d36082b0451877bda01116c08f611dfceb7a666bdf03c8","cp6_v2620p_rollback_capsule":"b656abaf23276984567c6c8d87b311427463c008b5ecd762fbdd0c2df13795df","cp6_v2620q_rollback_capsule":"ab6c992fbaa87f19a4eba696a57a3972f98504a354d9b5fc3be660939f8ea20f","cp6_v2620r_rollback_capsule":"8eb5e0a38284c5f8e3fee56618893ba72feaae9d26605c9ca3874dae25045297","cp6_v2620s_rollback_capsule":"fb57810a75f8829a038ed61b3a1cabde33dccf1e384661bc6723c51e28b3e132","cp6_v2620t_rollback_capsule":"348db4650d788750da243500b49e23c1130fdb70bc4a6d1fdf136bf68aa21f30","cp6_v2620u_rollback_capsule":"720eb1984548a3c381387fbe4d34e3c6f00334c8a4549eab7e398b827dcb7dd4","cp6_v2620v_rollback_capsule":"573ef5842eefadf1c32469514f4c8498667c99aec20ef20651406e4f419f5f60","cp6_v2620w_rollback_capsule":"f4e2ca1d577dd9f2724cc90693e8ee8bff36365c696575b69c6463f3e8ca0324","cp6_v2620x_rollback_capsule":"064db1068b56daa69e409ae582cd8a99490cea75d269154baa4217f90d3ca0d1","cp6_v2620y_rollback_capsule":"e3b23429a7f002c85ca8de1f8c632df13a4a2fc4e4654c12e2431c212772841d","cp6_v2620z_rollback_capsule":"ad0436a1480af43070e9861cb7e28d4cf55c435edbffb5fe368ca7babb7863ef","cutting_bridge_v2618_rollback_capsule":"535d1abd25668bc5bee79d82a602afe5efe4e8ce313bf1fb5170ae2004e3cb2d","cutting_bridge_v2618a_rollback_capsule":"db0608e690b3d936fa20b62cc4cfb9b1f9e86718212526eb6131562578b8bf60"}'::jsonb) loop
  execute format($caps$select encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to((to_jsonb(t)-array['captured_at','boundary_snapshot'])::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$caps$,r.key) into actual;
  if actual is distinct from r.value then raise exception 'BE_HISTORICAL_CAPSULE_DRIFT: %',r.key;end if;
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
 for r in select unnest(array['erp.cp6_v2620ao_rollback_capsule','erp.cp6_v2620ap_rollback_capsule','erp.cp6_v2620aq_rollback_capsule','erp.cp6_v2620ar_rollback_capsule','erp.cp6_v2620as_rollback_capsule','erp.cp6_v2620at_rollback_capsule','erp.cp6_v2620au_rollback_capsule','erp.cp6_v2620av_rollback_capsule','erp.cp6_v2620aw_rollback_capsule','erp.cp6_v2620ax_rollback_capsule','erp.cp6_v2620ay_rollback_capsule','erp.cp6_v2620az_rollback_capsule','erp.cp6_v2620ba_rollback_capsule','erp.cp6_v2620bb_rollback_capsule','erp.cp6_v2620bc_rollback_capsule','erp.cp6_v2620bd_rollback_capsule']::regclass[]) as rel loop
  if not exists(select 1 from pg_class where oid=r.rel and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid=r.rel and a.grantee<>p.relowner)
   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid=r.rel and a.grantee<>'postgres'::regrole)
   or exists(select 1 from pg_policy where polrelid=r.rel)
   or exists(select 1 from pg_trigger where tgrelid=r.rel and not tgisinternal) then raise exception 'BE_PRIOR_CAPSULE_SECURITY: %',r.rel;end if;
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel)) into actual;
  if actual is distinct from expected then raise exception 'BE_PRIOR_CAPSULE_SHAPE_DRIFT: %',r.rel;end if;
  execute format($b$select count(*) filter(where boundary_snapshot is null or not(boundary_snapshot ?& array['before','after','platform_before','markers_before']))
   +(case when count(distinct boundary_snapshot)=1 then 0 else 1 end) from %s$b$,r.rel) into bad;
  if bad<>0 then raise exception 'BE_PRIOR_CAPSULE_BOUNDARY: %',r.rel;end if;
 end loop;
end $prior_capsules$;
create table erp.cp6_v2620be_rollback_capsule(like erp.cp6_v2620an_rollback_capsule including all);
alter table erp.cp6_v2620be_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620be_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620be_rollback_capsule(object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),i.identity,pg_get_functiondef(p.oid),
 encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
 array(select a::text from unnest(p.proacl)a order by a::text),pg_get_userbyid(p.proowner)
from unnest(array['erp.post_product_conversion(uuid)','erp.propagate_conversion_hpp_for_po(uuid)','erp.compute_po_hpp_gl_targets_v2620d(uuid)','erp.bc_value_custody_v1(jsonb,uuid)','erp.bc_reverse_v1(jsonb,uuid)','erp.sync_material_cost_revaluation(uuid)','erp.run_v268_financial_report_checks()','erp.reverse_product_conversion(uuid,text)','erp.compute_non_po_product_hpp_targets_v2620f(uuid)','erp.compute_non_po_product_hpp_book_v2620f(uuid)','erp.assert_non_po_product_hpp_target_book_v2620f(uuid)','erp.sync_non_po_product_hpp_to_gl_v2620f(uuid,date,text,uuid,text)','erp.post_rework_completion(uuid)','erp.reverse_rework_completion(uuid,text)','erp.assert_new_stock_cutoff_coverage_v1()','erp.get_laundry_bd_workspace_v1(jsonb)','erp.save_laundry_bd_action_v1(text,jsonb,uuid)','erp.bd_save_invoice_draft_v1(jsonb,uuid)','erp.bd_check_correction_sources_v1(uuid)','erp.bd_invoice_lines_json_v1(uuid)','erp.bd_post_invoice_v1(jsonb,uuid)','erp.bd_invoice_resync_v1(uuid,date)','erp.bd_reverse_invoice_v1(jsonb,uuid)','erp.desired_laundry_accrual(uuid)','erp.rebuild_po_hpp(uuid,text)','erp.bd_lot_laundry_unknown_v1(uuid)','erp.cp6_lot_rework_cost_v2620c(uuid)','erp.period_blockers_v1(date,date)','erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)','erp._validate_migration_batch_base(uuid)','erp.finalize_migration_batch(uuid)','erp.save_initial_import_action_v1(text,jsonb,uuid)','erp.get_initial_import_workspace_v1(uuid)','erp.initial_import_revision_v1(uuid)','erp.pocket_period_total_v1(uuid)','erp.pocket_period_manifest_v1(date,date)','erp.pocket_period_target_v1(uuid,boolean)','erp.pocket_period_book_v1(uuid)','erp.sync_pocket_period_v1(uuid,date,text,text)','erp.save_pocket_period_action_v1(text,jsonb,uuid)','erp.initial_import_source_value_v1(uuid)','erp.check_initial_import_receipt_v1(uuid,uuid)','erp.recost_initial_import_origins_v1(uuid)','erp.run_v267_financial_truth_checks()','erp._cp6_supplier_cent_state(uuid[])','erp.get_pocket_fabric_workspace_v1(text)','erp.pocket_period_checks_v1()','erp.save_pocket_fabric_action_v1(text,jsonb,uuid)','erp.preview_pocket_period_v1(date,date)']) i(identity)
join pg_proc p on p.oid=i.identity::regprocedure join pg_namespace n on n.oid=p.pronamespace;
create temp table cp6_release_functions on commit drop as
select p.oid::regprocedure::text as identity,encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') as definition_sha256,
  array(select a::text from unnest(p.proacl)a order by a::text) as acl,pg_get_userbyid(p.proowner) as owner
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p');
do $before_data$ declare v_table text;v_hash jsonb;v_before jsonb; begin
 v_before:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620be_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_before:=v_before||jsonb_build_object(v_table,v_hash);
 end loop;
 create temp table cp6_release_boundary on commit drop as select jsonb_build_object('before',v_before,
  'platform_before',(select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations t),
  'markers_before',(select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from erp.schema_migrations t)) snapshot;
end $before_data$;
set local search_path='';set local lock_timeout='10s';set local statement_timeout='240s';
do $guard$ begin if not exists(select 1 from erp.schema_migrations where version='v2.6.20bd') then raise exception 'BE_REQUIRES_BD';end if;
if exists(select 1 from erp.schema_migrations where version='v2.6.20be') then raise exception 'BE_ALREADY_INSTALLED';end if;end $guard$;
-- BE: one selected physical lot becomes one target SKU. M:4828-4843/5057-5096.
-- Native product_conversions, allocations, movements and HPP versions remain the facts.
create table erp.be_execution_context_v1(
  backend_pid integer not null, transaction_id bigint not null, request_id uuid not null,
  syncing_nonpo boolean not null default false,
  primary key(backend_pid,transaction_id)
);
create table erp.be_conversion_sources_v1(
  conversion_id uuid primary key references erp.product_conversions(id),
  source_lot_id uuid not null references erp.fg_lots(id),
  origin_kind text not null check(origin_kind in('FG','REWORK','REDYE')),
  rework_id uuid references erp.rework_orders(id),
  source_revision text not null,
  created_by uuid, created_at timestamptz not null default statement_timestamp(),
  check((origin_kind='FG')=(rework_id is null))
);
create table erp.be_conversion_returns_v1(
  outstanding_id uuid primary key references erp.bc_outstanding_returns_v1(id),
  conversion_id uuid not null references erp.product_conversions(id),
  line_no integer not null check(line_no>0),
  unique(conversion_id,line_no)
);

CREATE OR REPLACE FUNCTION erp.be_in_context_v1()
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select exists(select 1 from erp.be_execution_context_v1
   where backend_pid=pg_backend_pid() and transaction_id=txid_current())
$function$;

CREATE OR REPLACE FUNCTION erp.be_guard_fact_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
 if not erp.be_in_context_v1() then raise exception 'BE_FACADE_REQUIRED: gunakan alur konversi';end if;
 if TG_OP<>'INSERT' then raise exception 'BE_IMMUTABLE_FACT: fakta konversi tidak dapat ditimpa';end if;
 return new;
end;$function$;
create trigger be_conversion_sources_fact before insert or update or delete on erp.be_conversion_sources_v1
 for each row execute function erp.be_guard_fact_v1();
create trigger be_conversion_returns_fact before insert or update or delete on erp.be_conversion_returns_v1
 for each row execute function erp.be_guard_fact_v1();

CREATE OR REPLACE FUNCTION erp.be_source_revision_v1(p_lot uuid,p_location uuid)
 RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select md5(jsonb_build_object('lot',p_lot,'location',p_location,
   'hpp',(select hv.id from erp.hpp_versions hv where hv.lot_id=p_lot and hv.is_current),
   'movements',coalesce((select jsonb_agg(jsonb_build_array(m.id,m.qty_signed,extract(epoch from m.physical_at)) order by m.id)
      from erp.fg_stock_movements m where m.lot_id=p_lot and m.location_id=p_location),'[]'::jsonb))::text)
$function$;

CREATE OR REPLACE FUNCTION erp.be_conversion_preview_v1(p_payload jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.fg_lots%rowtype;s erp.products%rowtype;t erp.products%rowtype;v_location uuid;v_qty integer;
 v_at timestamptz;v_current numeric;v_dated numeric;v_hpp numeric;v_cost jsonb;
begin
 perform erp.require_permission('warehouse.brand_conversion.view');
 perform erp._cp3_assert_closed_json_object(p_payload,
   array['source_lot_id','target_product_id','location_id','qty_pcs','physical_at','reason','expected_version'],
   array['source_lot_id','target_product_id','location_id','qty_pcs','physical_at','reason','expected_version','expected_returns'],'konversi');
 select * into l from erp.fg_lots where id=erp.bd_uuid_v1(p_payload,'source_lot_id',true);
 if l.id is null then raise exception 'BE_SOURCE_NOT_FOUND: lot sumber tidak ditemukan';end if;
 select * into s from erp.products where id=l.product_id;
 select * into t from erp.products where id=erp.bd_uuid_v1(p_payload,'target_product_id',true);
 if t.id is null or not t.is_active then raise exception 'BE_TARGET_NOT_ACTIVE: SKU tujuan tidak aktif';end if;
 if t.id=s.id then raise exception 'BE_SAME_SKU: pilih SKU tujuan yang berbeda';end if;
 if t.model_id is distinct from s.model_id or t.size_id is distinct from s.size_id then
   raise exception 'BE_DIMENSION_MISMATCH: model konstruksi dan ukuran harus tetap';end if;
 v_location:=erp.bd_uuid_v1(p_payload,'location_id',true);
 v_qty:=erp.bd_qty_v1(p_payload->'qty_pcs','qty_pcs');
 v_at:=erp.bd_at_v1(p_payload->>'physical_at','physical_at');
 perform erp.bc_text_v1(p_payload,'reason',true,1000);
 if v_at<l.produced_at then raise exception 'BE_BEFORE_SOURCE: waktu konversi sebelum lot tersedia';end if;
 perform erp.assert_product_identity_time(s.id,v_at,'EXISTING_STOCK');
 perform erp.assert_product_identity_time(t.id,v_at,'NEW_STOCK');
 if jsonb_typeof(p_payload->'expected_version') is distinct from 'string'
   or p_payload->>'expected_version' is distinct from erp.be_source_revision_v1(l.id,v_location) then
   raise exception 'STALE_VERSION: stok atau HPP sumber berubah; muat ulang';end if;
 select coalesce(sum(m.qty_signed),0),coalesce(sum(m.qty_signed) filter(where m.physical_at<=v_at),0)
   into v_current,v_dated from erp.fg_stock_movements m
   where m.lot_id=l.id and m.location_id=v_location and m.quality_grade='GRADE_A';
 if v_qty>least(v_current,v_dated) then raise exception 'BE_SOURCE_CAPACITY: jumlah melebihi stok sumber pada tanggalnya';end if;
 select hpp_per_pcs into v_hpp from erp.v_current_hpp where lot_id=l.id;
 if v_hpp is null then raise exception 'BE_SOURCE_HPP_UNKNOWN: nilai sumber belum diketahui';end if;
 v_cost:=case when erp.has_permission('finance.hpp.view') then
   jsonb_build_object('source_unit_hpp',v_hpp::text,'source_value',round(v_hpp*v_qty,2)::text) else '{}'::jsonb end;
 return jsonb_build_object('source_lot_id',l.id,'source_product_id',s.id,'target_product_id',t.id,
   'source_sku',s.sku,'target_sku',t.sku,'location_id',v_location,'qty_pcs',v_qty,'physical_at',v_at,
   'source_revision',p_payload->>'expected_version','cost',v_cost);
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_post_conversion_v1(p_payload jsonb,p_request uuid,p_origin text default 'FG',p_rework uuid default null)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v jsonb;l erp.fg_lots%rowtype;r jsonb;i integer:=0;v_return uuid;v_qty numeric;v_material uuid;v_dest uuid;
begin
 perform erp.require_permission('warehouse.brand_conversion.post');
 if not erp.be_in_context_v1() then raise exception 'BE_FACADE_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 select * into l from erp.fg_lots where id=erp.bd_uuid_v1(p_payload,'source_lot_id',true) for update;
 v:=erp.be_conversion_preview_v1(p_payload);
 insert into erp.product_conversions(id,conversion_number,from_product_id,to_product_id,location_id,qty_pcs,conversion_type,
   physical_at,status,conversion_cost_total,notes,created_by)
 values(p_request,'BE-'||p_request::text,l.product_id,(v->>'target_product_id')::uuid,(v->>'location_id')::uuid,
   (v->>'qty_pcs')::int,'REBRAND',(v->>'physical_at')::timestamptz,'DRAFT',0,btrim(p_payload->>'reason'),erp.current_app_user_id());
 insert into erp.be_conversion_sources_v1(conversion_id,source_lot_id,origin_kind,rework_id,source_revision,created_by)
 values(p_request,l.id,p_origin,p_rework,v->>'source_revision',erp.current_app_user_id());
 perform erp.post_product_conversion(p_request);
 if p_payload ? 'expected_returns' then
   if jsonb_typeof(p_payload->'expected_returns') is distinct from 'array' or jsonb_array_length(p_payload->'expected_returns')>100 then
     raise exception 'BE_RETURN_LINES: maksimal 100 baris bongkaran';end if;
   for r in select value from jsonb_array_elements(p_payload->'expected_returns') loop
     perform erp._cp3_assert_closed_json_object(r,array['material_id','qty','holder'],array['material_id','qty','holder'],'bongkaran');
     v_material:=erp.bc_uuid_v1(r,'material_id',true);v_qty:=erp.bc_parse_qty_v1(v_material,r->'qty','qty');
     insert into erp.bc_outstanding_returns_v1(source_kind,owner_kind,material_id,qty_expected,holder,reference)
     values('CONVERSION','COMPANY',v_material,v_qty,erp.bc_text_v1(r,'holder',true,120),'BE-'||p_request::text) returning id into v_return;
     i:=i+1;insert into erp.be_conversion_returns_v1(outstanding_id,conversion_id,line_no) values(v_return,p_request,i);
   end loop;
 end if;
 select destination_lot_id into strict v_dest from erp.product_conversion_allocations where conversion_id=p_request;
 return v||jsonb_build_object('conversion_id',p_request,'destination_lot_id',v_dest,'status','POSTED','pending_returns',i);
end;$function$;

CREATE OR REPLACE FUNCTION erp.save_product_conversion_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET "TimeZone" TO 'UTC' SET "DateStyle" TO 'ISO, YMD'
AS $function$
declare a text:=upper(btrim(coalesce(p_action,'')));v jsonb;v_cached jsonb;v_id uuid;
begin
 perform erp.require_permission('warehouse.brand_conversion.view');
 if a not in('POST','REVERSE','POST_USAGE','SAVE_REWORK','SAVE_REDYE','SET_REDYE_PRICE') then raise exception 'BE_ACTION_UNKNOWN: tindakan tidak dikenal';end if;
 perform erp.require_permission(case when a='REVERSE' then 'warehouse.brand_conversion.reverse' else 'warehouse.brand_conversion.post' end);
 if a='REVERSE' then perform erp.require_owner_admin();end if;
 perform erp.require_internal();
 if p_client_request_id is null or jsonb_typeof(p_payload) is distinct from 'object' or octet_length(p_payload::text)>30000 then
   raise exception 'BE_REQUEST_INVALID: request id dan data wajib';end if;
 v_cached:=erp._idempotency_begin('save_product_conversion_action_v1',p_client_request_id,
   erp._request_hash(jsonb_build_object('action',a,'payload',p_payload)));
 if v_cached is not null then return v_cached;end if;
 perform set_config('app.change_reason',erp.bc_text_v1(p_payload,'reason',true,1000),true);
 insert into erp.be_execution_context_v1 values(pg_backend_pid(),txid_current(),p_client_request_id);
 if a='POST' then v:=erp.be_post_conversion_v1(p_payload,p_client_request_id);
 elsif a='POST_USAGE' then v:=erp.be_post_usage_v1(p_payload,p_client_request_id);
 elsif a='SAVE_REDYE' then v:=erp.be_save_redye_v1(p_payload,p_client_request_id);
 elsif a='SET_REDYE_PRICE' then v:=erp.be_set_redye_price_v1(p_payload,p_client_request_id);
 elsif a='SAVE_REWORK' then v:=erp.be_save_rework_v1(p_payload,p_client_request_id);
 else
   perform erp._cp3_assert_closed_json_object(p_payload,array['conversion_id','reason'],array['conversion_id','reason'],'pembatalan konversi');
   v_id:=erp.bd_uuid_v1(p_payload,'conversion_id',true);
   perform erp.be_reverse_conversion_v1(v_id,p_payload->>'reason');
   v:=jsonb_build_object('conversion_id',v_id,'status','REVERSED');
 end if;
 delete from erp.be_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
 values(case when a='SAVE_REWORK' then 'rework_orders' else 'product_conversions' end,
   coalesce(v->>'conversion_id',v->>'rework_id',v->>'service_id')::uuid,case when a='REVERSE' then 'REVERSE' else 'POST' end,v,erp.current_app_user_id(),p_payload->>'reason');
 return erp._idempotency_complete('save_product_conversion_action_v1',p_client_request_id,v||jsonb_build_object('request_id',p_client_request_id,'action',a));
end;$function$;

CREATE OR REPLACE FUNCTION erp.get_product_conversion_workspace_v1(p_filters jsonb default '{}'::jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_page integer;v_size integer:=25;v_query text;v_lot uuid;v_result jsonb;v_values boolean;v_product uuid;v_target_query text;v_target_page int;v_doc_page int;
begin
 perform erp.require_permission('warehouse.brand_conversion.view');
 perform erp._cp3_assert_closed_json_object(p_filters,array[]::text[],array['query','page','source_lot_id','source_product_id','target_query','target_page','document_page','preview'],'konversi filters');
 if p_filters ? 'preview' then return jsonb_build_object('preview',erp.be_conversion_preview_v1(p_filters->'preview'));end if;
 if p_filters ? 'page' and (jsonb_typeof(p_filters->'page')<>'number' or (p_filters->>'page')!~'^[1-9][0-9]{0,5}$') then
   raise exception 'BE_PAGE_INVALID';end if;
 foreach v_query in array array['target_page','document_page'] loop
  if p_filters ? v_query and (jsonb_typeof(p_filters->v_query)<>'number' or p_filters->>v_query!~'^[1-9][0-9]{0,5}$') then raise exception 'BE_PAGE_INVALID';end if;
 end loop;
 v_target_page:=coalesce((p_filters->>'target_page')::int,1);v_doc_page:=coalesce((p_filters->>'document_page')::int,1);
 v_target_query:=lower(coalesce(erp.bc_text_v1(p_filters,'target_query',false,120),''));
 v_page:=coalesce((p_filters->>'page')::int,1);v_query:=lower(coalesce(erp.bc_text_v1(p_filters,'query',false,120),''));
 v_product:=erp.bd_uuid_v1(p_filters,'source_product_id',false);
 v_lot:=erp.bd_uuid_v1(p_filters,'source_lot_id',false);
 if v_lot is not null then select product_id into v_product from erp.fg_lots where id=v_lot;end if;v_values:=erp.has_permission('finance.hpp.view');
 with lots as(select l.id,l.lot_number,l.product_id,l.po_id,l.produced_at,p.sku,p.product_name,p.model_id,p.size_id,
       m.location_id,loc.location_name,sum(m.qty_signed)::integer qty
     from erp.fg_lots l join erp.products p on p.id=l.product_id join erp.fg_stock_movements m on m.lot_id=l.id
     join erp.locations loc on loc.id=m.location_id
     where m.quality_grade='GRADE_A' and (v_lot is null or l.id=v_lot)
       and (v_query='' or lower(p.sku||' '||p.product_name||' '||l.lot_number) like '%'||v_query||'%')
     group by l.id,p.id,m.location_id,loc.location_name having sum(m.qty_signed)>0),
   pg as(select * from lots order by produced_at,id,location_id limit v_size offset (v_page-1)*v_size)
 select jsonb_build_object('total',(select count(*) from lots),'page',v_page,'page_size',v_size,
   'lots',coalesce(jsonb_agg(to_jsonb(pg)||jsonb_build_object('source_revision',erp.be_source_revision_v1(id,location_id),
     'unit_hpp',case when v_values then (select hpp_per_pcs::text from erp.v_current_hpp where lot_id=pg.id) end) order by produced_at,id,location_id),'[]'::jsonb))
 into v_result from pg;
 with targets as(select p.id,p.sku,p.product_name,p.model_id,p.size_id from erp.products p
    join erp.products source_product on source_product.id=v_product
    where p.is_active and p.model_id=source_product.model_id and p.size_id=source_product.size_id and p.id<>source_product.id
      and (v_target_query='' or lower(p.sku||' '||p.product_name) like '%'||v_target_query||'%')),
   target_page as(select * from targets order by sku,id limit v_size offset (v_target_page-1)*v_size)
 select v_result||jsonb_build_object('targets',coalesce((select jsonb_agg(to_jsonb(x) order by x.sku,x.id) from target_page x),'[]'::jsonb),
   'targets_total',(select count(*) from targets),'target_page',v_target_page) into v_result;
 with docs as(select c.id,c.conversion_number,c.status,c.qty_pcs,c.physical_at,c.notes,s.origin_kind,s.source_lot_id,s.rework_id,
    p.sku source_sku,t.sku target_sku,a.destination_lot_id,erp.be_conversion_revision_v1(c.id) revision,
    case when v_values then erp.be_conversion_extra_v1(c.id)::text end extra_cost,
    case when v_values then (select total_cost::text from erp.hpp_versions where lot_id=a.destination_lot_id and is_current) end target_value,
    (select count(*) from erp.be_conversion_returns_v1 br join erp.bc_outstanding_returns_v1 o on o.id=br.outstanding_id
      where br.conversion_id=c.id and o.status<>'CANCELLED') pending_returns,
    erp.be_conversion_value_state_v1(c.id) value_state,erp.be_return_progress_v1(c.id) returns
   from erp.be_conversion_sources_v1 s join erp.product_conversions c on c.id=s.conversion_id
    join erp.products p on p.id=c.from_product_id join erp.products t on t.id=c.to_product_id
    join erp.product_conversion_allocations a on a.conversion_id=c.id),
   doc_page as(select * from docs order by physical_at desc,id desc limit v_size offset (v_doc_page-1)*v_size)
 select v_result||jsonb_build_object('documents_total',(select count(*) from docs),'document_page',v_doc_page,
   'documents',coalesce((select jsonb_agg(to_jsonb(x) order by x.physical_at desc,x.id desc) from doc_page x),'[]'::jsonb)) into v_result;
 return v_result;
end;$function$;

CREATE OR REPLACE FUNCTION public.erp_save_product_conversion_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.save_product_conversion_action_v1(p_action,p_payload,p_client_request_id) $function$;
CREATE OR REPLACE FUNCTION public.erp_get_product_conversion_workspace_v1(p_filters jsonb default '{}'::jsonb)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.get_product_conversion_workspace_v1(p_filters) $function$;
-- Actual accessory use and approved recovery are native BC documents. BE moves
-- that exact sourced value into/out of conversion HPP; it never accepts manual HPP.
create table erp.be_conversion_cost_sources_v1(
  document_id uuid primary key references erp.bc_documents_v1(id),
  conversion_id uuid not null references erp.product_conversions(id),
  kind text not null check(kind in('USAGE','RECOVERY')),
  created_at timestamptz not null default statement_timestamp()
);
create table erp.be_conversion_cost_events_v1(
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references erp.be_conversion_cost_sources_v1(document_id),
  adjustment_id uuid not null references erp.material_adjustments(id),
  previous_amount numeric(20,2) not null,target_amount numeric(20,2) not null,
  journal_id uuid not null references erp.journal_entries(id),
  economic_date date not null,created_at timestamptz not null default statement_timestamp(),created_by uuid
);
create trigger be_conversion_cost_sources_fact before insert or update or delete on erp.be_conversion_cost_sources_v1
 for each row execute function erp.be_guard_fact_v1();
create trigger be_conversion_cost_events_fact before insert or update or delete on erp.be_conversion_cost_events_v1
 for each row execute function erp.be_guard_fact_v1();

CREATE OR REPLACE FUNCTION erp.be_conversion_extra_v1(p_conversion uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce(sum(e.target_amount-e.previous_amount),0) from erp.be_conversion_cost_sources_v1 s
 join erp.be_conversion_cost_events_v1 e on e.document_id=s.document_id where s.conversion_id=p_conversion
$function$;

CREATE OR REPLACE FUNCTION erp.be_allocation_extra_v1(p_allocation uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select a.conversion_cost_allocated+erp.be_conversion_extra_v1(a.conversion_id)
 from erp.product_conversion_allocations a where a.id=p_allocation
$function$;

CREATE OR REPLACE FUNCTION erp.be_po_extra_v1(p_po uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce(sum(erp.be_conversion_extra_v1(c.id)),0) from erp.product_conversions c
 join erp.be_conversion_sources_v1 s on s.conversion_id=c.id join erp.fg_lots l on l.id=s.source_lot_id
 where c.status='POSTED' and l.po_id=p_po
$function$;

CREATE OR REPLACE FUNCTION erp.be_conversion_revision_v1(p_conversion uuid)
 RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select md5(jsonb_build_object('id',c.id,'status',c.status,
   'cost_events',coalesce((select jsonb_agg(e.id order by e.id) from erp.be_conversion_cost_events_v1 e
     join erp.be_conversion_cost_sources_v1 s on s.document_id=e.document_id where s.conversion_id=c.id),'[]'::jsonb))::text)
 from erp.product_conversions c where c.id=p_conversion
$function$;

CREATE OR REPLACE FUNCTION erp.be_reconcile_cost_document_v1(p_document uuid,p_date date)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare s erp.be_conversion_cost_sources_v1%rowtype;c erp.product_conversions%rowtype;l erp.fg_lots%rowtype;
 r record;v_target numeric;v_before numeric;v_delta numeric;v_journal uuid;v_own boolean;v_event uuid;
begin
 perform erp.require_internal();
 select * into s from erp.be_conversion_cost_sources_v1 where document_id=p_document;
 if s.document_id is null then return;end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 select * into c from erp.product_conversions where id=s.conversion_id for update;
 select * into l from erp.fg_lots where id=(select source_lot_id from erp.be_conversion_sources_v1 where conversion_id=c.id);
 if c.status<>'POSTED' then raise exception 'BE_COST_SOURCE_NOT_POSTED';end if;
 v_own:=not erp.be_in_context_v1();
 if v_own then insert into erp.be_execution_context_v1 values(pg_backend_pid(),txid_current(),gen_random_uuid());end if;
 for r in select p.adjustment_id,p.account_id,d.status from erp.bc_adjustment_purposes_v1 p
    join erp.bc_documents_v1 d on d.id=p.document_id where p.document_id=p_document order by p.adjustment_id loop
   v_target:=case when r.status='POSTED' then -(erp._cp6_material_adjustment_revaluation_state(r.adjustment_id)->>'current_value')::numeric else 0 end;
   if (s.kind='USAGE' and v_target<0) or (s.kind='RECOVERY' and v_target>0) then raise exception 'BE_COST_DIRECTION';end if;
   select coalesce(sum(target_amount-previous_amount),0) into v_before from erp.be_conversion_cost_events_v1 where adjustment_id=r.adjustment_id;
   v_delta:=v_target-v_before;
   if v_delta<>0 then
     v_event:=gen_random_uuid();
     v_journal:=erp.post_journal('BE_CONVERSION_SOURCED_COST',v_event,p_date,'Biaya/pemulihan konversi dari dokumen '||p_document::text,
       jsonb_build_array(jsonb_build_object('mapping_key',case when l.po_id is null then 'FG_INVENTORY' else 'WIP' end,
         'po_id',l.po_id,'product_id',case when l.po_id is null then c.to_product_id end,'debit',greatest(v_delta,0),'credit',greatest(-v_delta,0)),
         jsonb_build_object('account_id',r.account_id,'debit',greatest(-v_delta,0),'credit',greatest(v_delta,0))));
     insert into erp.be_conversion_cost_events_v1(id,document_id,adjustment_id,previous_amount,target_amount,journal_id,economic_date,created_by)
     values(v_event,p_document,r.adjustment_id,v_before,v_target,v_journal,p_date,erp.current_app_user_id());
   end if;
 end loop;
 if l.po_id is null then
   perform erp.be_nonpo_sync_all_v1(p_date,'BE_COST_SOURCE',p_document,'Biaya/pemulihan konversi non-PO');
 else
   perform erp.propagate_conversion_hpp_for_po(l.po_id);
   perform erp.sync_po_hpp_to_gl(l.po_id,p_date);
   perform erp.assert_po_hpp_target_book_v2620e(l.po_id);
 end if;
 if v_own then delete from erp.be_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();end if;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_sync_material_cost_v1(p_material uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare d uuid;
begin
 for d in select distinct s.document_id from erp.be_conversion_cost_sources_v1 s join erp.bc_adjustment_purposes_v1 p on p.document_id=s.document_id
   join erp.material_adjustment_items i on i.adjustment_id=p.adjustment_id where i.material_id=p_material order by s.document_id loop
   perform erp.be_reconcile_cost_document_v1(d,coalesce(erp.invoice_recost_economic_date_v1(),erp._cp3_business_date(current_timestamp)));
 end loop;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_link_recovery_v1(p_document uuid,p_return_lot uuid,p_date date)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_conversion uuid;v_own boolean;
begin
 select s.conversion_id into v_conversion from erp.be_conversion_returns_v1 s join erp.bc_return_lots_v1 l on l.outstanding_id=s.outstanding_id
 where l.id=p_return_lot;
 if v_conversion is null then return;end if;
 v_own:=not erp.be_in_context_v1();
 if v_own then insert into erp.be_execution_context_v1 values(pg_backend_pid(),txid_current(),gen_random_uuid());end if;
 insert into erp.be_conversion_cost_sources_v1(document_id,conversion_id,kind) values(p_document,v_conversion,'RECOVERY');
 perform erp.be_reconcile_cost_document_v1(p_document,p_date);
 if v_own then delete from erp.be_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();end if;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_post_usage_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare c erp.product_conversions%rowtype;v_result jsonb;v_at timestamptz;v_items jsonb;v_doc uuid:=gen_random_uuid();
begin
 perform erp.require_permission('warehouse.stock.adjust');
 perform erp._cp3_assert_closed_json_object(p_payload,array['conversion_id','expected_version','location_id','items','physical_at','reason'],
   array['conversion_id','expected_version','location_id','items','physical_at','reason'],'aksesori konversi');
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 select * into c from erp.product_conversions where id=erp.bd_uuid_v1(p_payload,'conversion_id',true) for update;
 if c.id is null or c.status<>'POSTED' or not exists(select 1 from erp.be_conversion_sources_v1 where conversion_id=c.id) then
   raise exception 'BE_DOCUMENT_NOT_POSTED';end if;
 if p_payload->>'expected_version' is distinct from erp.be_conversion_revision_v1(c.id) then raise exception 'STALE_VERSION';end if;
 v_at:=erp.bd_at_v1(p_payload->>'physical_at','physical_at');
 if v_at<c.physical_at then raise exception 'BE_BEFORE_CONVERSION';end if;
 v_items:=erp.bc_lines_v1(p_payload);
 select jsonb_agg((x-'line_number')||jsonb_build_object('purpose','OWN_FG_REPAIR',
   'physical_at',to_char(v_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')||'+07:00') order by (x->>'line_number')::int)
 into v_items from jsonb_array_elements(v_items) x;
 v_result:=erp.save_accessory_service_action_v1('INTERNAL_USE',jsonb_build_object('location_id',p_payload->>'location_id',
   'items',v_items,'reason',p_payload->>'reason','reference','Konversi '||c.conversion_number),v_doc);
 insert into erp.be_conversion_cost_sources_v1(document_id,conversion_id,kind) values(v_doc,c.id,'USAGE');
 perform erp.be_reconcile_cost_document_v1(v_doc,erp._cp3_business_date(v_at));
 return jsonb_build_object('conversion_id',c.id,'cost_document_id',v_doc,'status','POSTED','source',v_result,
   'expected_version',erp.be_conversion_revision_v1(c.id));
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_return_progress_v1(p_conversion uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce(jsonb_agg(jsonb_build_object('id',o.id,'material_id',o.material_id,'material',m.material_name,'holder',o.holder,
  'expected',o.qty_expected::text,'received',coalesce(x.received,0)::numeric(18,6)::text,
  'awaiting_value',coalesce(x.pending,0)::numeric(18,6)::text,
  'unreturned',greatest(o.qty_expected-coalesce(x.received,0),0)::numeric(18,6)::text) order by br.line_no),'[]')
 from erp.be_conversion_returns_v1 br join erp.bc_outstanding_returns_v1 o on o.id=br.outstanding_id and o.status<>'CANCELLED'
 join erp.materials m on m.id=o.material_id
 left join lateral(select sum(l.qty_received) received,sum(case when l.value_mode='PENDING' then (erp.bc_lot_state_v1(l.id)->>'open')::numeric else 0 end) pending
  from erp.bc_return_lots_v1 l join erp.bc_documents_v1 d on d.id=l.document_id where l.outstanding_id=o.id and d.status='POSTED') x on true
 where br.conversion_id=p_conversion
$function$;
CREATE OR REPLACE FUNCTION erp.be_conversion_value_state_v1(p_conversion uuid)
 RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select case when exists(select 1 from jsonb_array_elements(erp.be_return_progress_v1(p_conversion)) x
  where (x->>'unreturned')::numeric>0 or (x->>'awaiting_value')::numeric>0) then 'PROVISIONAL_RECOVERY' else 'SOURCED_TO_DATE' end
$function$;
-- Opening/non-PO conversion has an explicit value source. Current value moves
-- between SKU dimensions; only disposal/sales become expense. Historical sale
-- snapshots and allocation.original_hpp_per_pcs remain immutable.
create table erp.be_nonpo_transfer_events_v1(
 id uuid primary key default gen_random_uuid(),conversion_id uuid not null references erp.product_conversions(id),
 previous_value numeric(20,2) not null,target_value numeric(20,2) not null,
 journal_id uuid not null references erp.journal_entries(id),economic_date date not null,
 created_at timestamptz not null default statement_timestamp()
);
create trigger be_nonpo_transfer_events_fact before insert or update or delete on erp.be_nonpo_transfer_events_v1
 for each row execute function erp.be_guard_fact_v1();

CREATE OR REPLACE FUNCTION erp.be_nonpo_admitted_v1(p_conversion uuid)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select exists(select 1 from erp.be_conversion_sources_v1 b join erp.product_conversions c on c.id=b.conversion_id
  join erp.fg_lots l on l.id=b.source_lot_id join erp.v_current_hpp h on h.lot_id=l.id
  where b.conversion_id=p_conversion and l.po_id is null and l.product_id=c.from_product_id
   and l.lot_origin<>'VOIDED_PRODUCTION' and h.hpp_per_pcs>=0)
$function$;

CREATE OR REPLACE FUNCTION erp.be_nonpo_in_sync_v1()
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce((select syncing_nonpo from erp.be_execution_context_v1
   where backend_pid=pg_backend_pid() and transaction_id=txid_current()),false)
$function$;

CREATE OR REPLACE FUNCTION erp.be_nonpo_sync_all_v1(p_date date,p_source_type text,p_source_id uuid,p_reason text)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;v_own boolean;v_old numeric;v_new numeric;v_delta numeric;v_journal uuid;v_event uuid;v_product uuid;
begin
 perform erp.require_internal();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if erp.be_nonpo_in_sync_v1() then raise exception 'BE_NON_PO_RECURSION';end if;
 v_own:=not erp.be_in_context_v1();
 if v_own then insert into erp.be_execution_context_v1(backend_pid,transaction_id,request_id) values(pg_backend_pid(),txid_current(),gen_random_uuid());end if;
 update erp.be_execution_context_v1 set syncing_nonpo=true where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 perform erp.be_propagate_nonpo_v1();
 for r in select c.id,c.from_product_id,c.to_product_id,a.id allocation_id,a.qty_pcs,a.original_hpp_per_pcs,
    h.hpp_per_pcs from erp.product_conversions c join erp.product_conversion_allocations a on a.conversion_id=c.id
    join erp.fg_lots l on l.id=a.source_lot_id join erp.v_current_hpp h on h.lot_id=l.id
    where l.po_id is null and c.status='POSTED' order by c.physical_at,c.id loop
   if not erp.be_nonpo_admitted_v1(r.id) then raise exception 'NON_PO_CONVERSION_REQUIRES_SOURCED_HPP_WORKFLOW';end if;
   select round(r.qty_pcs*r.original_hpp_per_pcs,2)+coalesce(sum(target_value-previous_value),0) into v_old
     from erp.be_nonpo_transfer_events_v1 where conversion_id=r.id;
   v_new:=round(r.qty_pcs*r.hpp_per_pcs,2);v_delta:=v_new-v_old;
   if v_delta<>0 then
     v_event:=gen_random_uuid();
     v_journal:=erp.post_journal('BE_NONPO_CONVERSION_RECOST',v_event,p_date,'Nilai sumber terkini konversi '||r.id::text,
       jsonb_build_array(jsonb_build_object('mapping_key','FG_INVENTORY','product_id',r.to_product_id,'debit',greatest(v_delta,0),'credit',greatest(-v_delta,0)),
         jsonb_build_object('mapping_key','FG_INVENTORY','product_id',r.from_product_id,'debit',greatest(-v_delta,0),'credit',greatest(v_delta,0))));
     insert into erp.be_nonpo_transfer_events_v1(id,conversion_id,previous_value,target_value,journal_id,economic_date)
       values(v_event,r.id,v_old,v_new,v_journal,p_date);
   end if;
 end loop;
 for v_product in select distinct product_id from erp.fg_lots where po_id is null order by product_id loop
   perform erp.sync_non_po_product_hpp_to_gl_v2620f(v_product,p_date,p_source_type,p_source_id,p_reason);
 end loop;
 update erp.be_execution_context_v1 set syncing_nonpo=false where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 if v_own then delete from erp.be_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();end if;
end;$function$;
-- Rework keeps the native BS lifecycle. Only the GOOD lot produced by COMPLETE
-- is converted; partial saves never make stock or payable. Both facts commit atomically.
create table erp.be_rework_targets_v1(
 rework_id uuid primary key references erp.rework_orders(id),
 target_product_id uuid not null references erp.products(id),
 mode text not null check(mode in('REWORK_SKU','REDYE_SKU')),
 reason text not null,created_by uuid,created_at timestamptz not null default statement_timestamp()
);
create trigger be_rework_targets_fact before insert or update or delete on erp.be_rework_targets_v1
 for each row execute function erp.be_guard_fact_v1();

CREATE OR REPLACE FUNCTION erp.be_guard_rework_source_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
 if exists(select 1 from erp.be_rework_targets_v1 where rework_id=old.id) then
   if TG_OP='DELETE' then raise exception 'BE_REWORK_SOURCE_IMMUTABLE';end if;
   if (new.bs_case_id,new.destination_type,new.contractor_id,new.vendor_id,new.qty_sent,new.physical_sent_at)
      is distinct from (old.bs_case_id,old.destination_type,old.contractor_id,old.vendor_id,old.qty_sent,old.physical_sent_at) then
     raise exception 'BE_REWORK_SOURCE_IMMUTABLE: sumber/tujuan kiriman sudah terikat; batalkan lalu buat dokumen baru';end if;
 end if;
 if TG_OP='DELETE' then return old;end if;return new;
end;$function$;
create trigger be_rework_source_immutable before update or delete on erp.rework_orders
 for each row execute function erp.be_guard_rework_source_v1();

CREATE OR REPLACE FUNCTION erp.be_save_rework_v1(p_payload jsonb,p_request uuid,p_redye boolean default false)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare b erp.bs_cases%rowtype;s erp.products%rowtype;t erp.products%rowtype;v_order uuid;v_result jsonb;v_payload jsonb;
begin
 perform erp.require_permission('production.bs_rework.create');
 perform erp._cp3_assert_closed_json_object(p_payload,array['order','target_product_id','reason'],array['order','target_product_id','reason'],'rework SKU baru');
 if jsonb_typeof(p_payload->'order') is distinct from 'object' or nullif(p_payload->'order'->>'id','') is not null then
   raise exception 'BE_NEW_REWORK_REQUIRED: target SKU ditentukan pada order baru';end if;
 v_payload:=(p_payload->'order')||jsonb_build_object('change_reason',p_payload->>'reason');
 select * into b from erp.bs_cases where id=erp.bd_uuid_v1(v_payload,'bs_case_id',true) for update;
 select * into s from erp.products where id=b.product_id;
 select * into t from erp.products where id=erp.bd_uuid_v1(p_payload,'target_product_id',true);
 if b.id is null or s.id is null then raise exception 'BE_REWORK_SOURCE_IDENTITY_UNKNOWN';end if;
 if t.id is null or not t.is_active or t.id=s.id or t.model_id<>s.model_id or t.size_id<>s.size_id then
   raise exception 'BE_DIMENSION_MISMATCH: SKU baru harus berbeda, dengan model konstruksi dan ukuran sumber';end if;
 v_result:=erp.save_bs_resolution_action_v1('SAVE_REWORK',v_payload,p_request,null);
 v_order:=(v_result->'result'->>'rework_order_id')::uuid;
 if v_order is null then raise exception 'BE_NATIVE_REWORK_RESPONSE_INVALID';end if;
 insert into erp.be_rework_targets_v1(rework_id,target_product_id,mode,reason,created_by)
 values(v_order,t.id,case when p_redye then 'REDYE_SKU' else 'REWORK_SKU' end,erp.bc_text_v1(p_payload,'reason',true,1000),erp.current_app_user_id());
 return jsonb_build_object('rework_id',v_order,'target_product_id',t.id,'status','IN_PROGRESS','native',v_result);
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_complete_rework_target_v1(p_rework uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare b erp.be_rework_targets_v1%rowtype;r erp.rework_orders%rowtype;v_own boolean;v_result jsonb;
begin
 select * into b from erp.be_rework_targets_v1 where rework_id=p_rework;
 if b.rework_id is null then return;end if;
 select * into r from erp.rework_orders where id=p_rework for update;
 if not r.cost_posted or r.status<>'COMPLETED' then raise exception 'BE_REWORK_NOT_COMPLETE';end if;
 if r.qty_good_returned=0 then return;end if;
 if r.good_fg_lot_id is null then raise exception 'BE_REWORK_GOOD_LOT_MISSING';end if;
 if exists(select 1 from erp.be_conversion_sources_v1 s join erp.product_conversions c on c.id=s.conversion_id
      where s.rework_id=r.id and s.source_lot_id=r.good_fg_lot_id and c.status='POSTED') then return;end if;
 v_own:=not erp.be_in_context_v1();
 if v_own then insert into erp.be_execution_context_v1(backend_pid,transaction_id,request_id) values(pg_backend_pid(),txid_current(),gen_random_uuid());end if;
 v_result:=erp.be_post_conversion_v1(jsonb_build_object('source_lot_id',r.good_fg_lot_id,'target_product_id',b.target_product_id,
   'location_id',r.return_fg_location_id,'qty_pcs',r.qty_good_returned,'physical_at',r.completed_at,'reason',b.reason,
   'expected_version',erp.be_source_revision_v1(r.good_fg_lot_id,r.return_fg_location_id)),gen_random_uuid(),
   case when b.mode='REDYE_SKU' then 'REDYE' else 'REWORK' end,r.id);
 if v_own then delete from erp.be_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();end if;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_reverse_conversion_v1(p_conversion uuid,p_reason text)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
 perform erp.require_permission('warehouse.brand_conversion.reverse');perform erp.require_owner_admin();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if not exists(select 1 from erp.be_conversion_sources_v1 where conversion_id=p_conversion) then raise exception 'BE_DOCUMENT_NOT_FOUND';end if;
 if exists(select 1 from erp.be_conversion_cost_sources_v1 s join erp.bc_documents_v1 d on d.id=s.document_id
     where s.conversion_id=p_conversion and d.status='POSTED') then raise exception 'BE_REVERSE_DEPENDANTS: batalkan dahulu sumber biaya/pemulihan';end if;
 if exists(select 1 from erp.be_conversion_returns_v1 s join erp.bc_return_lots_v1 l on l.outstanding_id=s.outstanding_id
     join erp.bc_documents_v1 d on d.id=l.document_id where s.conversion_id=p_conversion and d.status='POSTED') then
   raise exception 'BE_REVERSE_DEPENDANTS: batalkan dahulu penerimaan bongkaran';end if;
 perform erp.reverse_product_conversion(p_conversion,p_reason);
 update erp.bc_outstanding_returns_v1 set status='CANCELLED' where id in(select outstanding_id from erp.be_conversion_returns_v1 where conversion_id=p_conversion);
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_reverse_rework_target_v1(p_rework uuid,p_reason text)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v uuid;v_own boolean;
begin
 if not exists(select 1 from erp.be_rework_targets_v1 where rework_id=p_rework) then return;end if;
 v_own:=not erp.be_in_context_v1();
 if v_own then insert into erp.be_execution_context_v1(backend_pid,transaction_id,request_id) values(pg_backend_pid(),txid_current(),gen_random_uuid());end if;
 for v in select s.conversion_id from erp.be_conversion_sources_v1 s join erp.product_conversions c on c.id=s.conversion_id
    where s.rework_id=p_rework and c.status='POSTED' order by c.physical_at desc,c.id desc loop
   perform erp.be_reverse_conversion_v1(v,p_reason);
 end loop;
 if v_own then delete from erp.be_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();end if;
end;$function$;
-- Paid BS redye is its own real service attempt, never a synthetic production receipt.
create table erp.be_redye_services_v1(
 id uuid primary key references erp.rework_orders(id),vendor_id uuid not null references erp.laundry_vendors(id),
 wash_process_id uuid not null references erp.wash_processes(id),po_id uuid not null references erp.production_orders(id),
 sent_at timestamptz not null,qty integer not null check(qty>0),rate_version_id uuid references erp.laundry_vendor_rate_versions(id),
 initial_rate numeric(18,6) check(initial_rate>=0),created_by uuid,created_at timestamptz not null default statement_timestamp()
);
create table erp.be_redye_price_events_v1(
 id uuid primary key default gen_random_uuid(),service_id uuid not null unique references erp.be_redye_services_v1(id),
 rate numeric(18,6) not null check(rate>=0),reason text not null,created_by uuid,created_at timestamptz not null default statement_timestamp()
);
create trigger be_redye_service_fact before insert or update or delete on erp.be_redye_services_v1 for each row execute function erp.be_guard_fact_v1();
create trigger be_redye_price_fact before insert or update or delete on erp.be_redye_price_events_v1 for each row execute function erp.be_guard_fact_v1();
alter table erp.bd_laundry_invoice_lines_v1 add column rework_service_id uuid references erp.be_redye_services_v1(id);
do $source_check$
declare n text;
begin
 select conname into strict n from pg_constraint where conrelid='erp.bd_laundry_invoice_lines_v1'::regclass
   and contype='c' and pg_get_constraintdef(oid) like '%num_nonnulls(receipt_line_id, opening_uninvoiced_id)%';
 execute format('alter table erp.bd_laundry_invoice_lines_v1 drop constraint %I',n);
 execute format('alter table erp.bd_laundry_invoice_lines_v1 add constraint %I check(num_nonnulls(receipt_line_id,opening_uninvoiced_id,rework_service_id)=1)',n);
end;$source_check$;
create index be_invoice_redye_source on erp.bd_laundry_invoice_lines_v1(rework_service_id);

CREATE OR REPLACE FUNCTION erp.be_redye_rate_v1(p_service uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select coalesce(e.rate,s.initial_rate) from erp.be_redye_services_v1 s left join erp.be_redye_price_events_v1 e on e.service_id=s.id where s.id=p_service $function$;
CREATE OR REPLACE FUNCTION erp.be_redye_estimate_v1(p_service uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select round(s.qty*erp.be_redye_rate_v1(s.id),2) from erp.be_redye_services_v1 s join erp.rework_orders r on r.id=s.id where s.id=p_service and r.status<>'CANCELLED' $function$;
CREATE OR REPLACE FUNCTION erp.be_redye_cost_v1(p_service uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select coalesce(erp.be_redye_estimate_v1(p_service),0)+coalesce((select sum(l.product_variance) from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id where l.rework_service_id=p_service and i.status='POSTED'),0) $function$;
CREATE OR REPLACE FUNCTION erp.be_redye_po_cost_v1(p_po uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select coalesce(sum(erp.be_redye_cost_v1(s.id)),0) from erp.be_redye_services_v1 s join erp.rework_orders r on r.id=s.id where s.po_id=p_po and r.status<>'CANCELLED' $function$;
CREATE OR REPLACE FUNCTION erp.be_redye_accrual_v1(p_po uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select coalesce(sum(coalesce(erp.be_redye_estimate_v1(s.id),0)-coalesce((select sum(l.released_estimate) from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id where i.status='POSTED' and l.rework_service_id=s.id),0)),0)
 from erp.be_redye_services_v1 s join erp.rework_orders r on r.id=s.id where s.po_id=p_po and r.status<>'CANCELLED' $function$;
CREATE OR REPLACE FUNCTION erp.be_redye_capacity_v1(p_service uuid,p_category text)
 RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select case when r.status<>'COMPLETED' or not r.cost_posted then 0 when p_category='GOOD' then r.qty_good_returned when p_category='BS' then r.qty_bs_returned else 0 end from erp.rework_orders r where r.id=p_service $function$;
CREATE OR REPLACE FUNCTION erp.be_redye_billed_v1(p_service uuid,p_category text)
 RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select coalesce(sum(l.qty),0)::int from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id where i.status='POSTED' and l.rework_service_id=p_service and l.line_kind='BILL' and l.category=p_category $function$;
CREATE OR REPLACE FUNCTION erp.be_redye_resync_v1(p_service uuid,p_date date)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_po uuid;
begin
 select po_id into v_po from erp.be_redye_services_v1 where id=p_service;
 if v_po is null then return;end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform erp.sync_laundry_accrual(v_po,p_date);
 if exists(select 1 from erp.fg_lots where po_id=v_po) then
   perform erp.rebuild_po_hpp(v_po,'BE celup ulang: sumber jasa/invoice');perform erp.propagate_conversion_hpp_for_po(v_po);perform erp.sync_po_hpp_to_gl(v_po,p_date);
 end if;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_save_redye_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_result jsonb;v_id uuid;r erp.rework_orders%rowtype;b erp.bs_cases%rowtype;v_process uuid;v_n int;v_rate numeric;v_version uuid;
begin
 perform erp.require_owner_admin();perform erp.require_permission('production.bs_rework.create');perform erp.require_permission('finance.hpp.manage');
 perform erp._cp3_assert_closed_json_object(p_payload,array['order','target_product_id','wash_process_id','price_status','reason'],array['order','target_product_id','wash_process_id','price_status','reason'],'celup ulang berbayar');
 if p_payload->'order'->>'destination_type' is distinct from 'LAUNDRY' then raise exception 'BE_REDYE_VENDOR_REQUIRED';end if;
 v_process:=erp.bd_uuid_v1(p_payload,'wash_process_id',true);
 if not exists(select 1 from erp.wash_processes where id=v_process and is_active) then raise exception 'BE_PROCESS_INACTIVE';end if;
 -- The ordinary binding helper is called with its own closed payload; no arbitrary conversion cost is accepted.
 v_result:=erp.be_save_rework_v1(p_payload-'wash_process_id'-'price_status',p_request,true);v_id:=(v_result->>'rework_id')::uuid;
 select * into r from erp.rework_orders where id=v_id;select * into b from erp.bs_cases where id=r.bs_case_id;
 if b.po_id is null then raise exception 'BE_REDYE_PO_SOURCE_REQUIRED';end if;
 select count(*)::int into v_n from erp.laundry_vendor_rate_versions where vendor_id=r.vendor_id and wash_process_id=v_process
   and effective_from<=r.physical_sent_at and (effective_to is null or effective_to>r.physical_sent_at);
 if p_payload->>'price_status' not in('KNOWN','UNKNOWN') then raise exception 'BE_PRICE_STATUS_REQUIRED';end if;
 if v_n=0 and p_payload->>'price_status'<>'UNKNOWN' then raise exception 'BD_RATE_NOT_EXACT';end if;
 if v_n=1 and p_payload->>'price_status'='UNKNOWN' then raise exception 'BE_PRICE_ALREADY_KNOWN';end if;
 if v_n>1 then raise exception 'BD_RATE_NOT_EXACT: tarif vendor/proses bertumpuk';end if;
 if v_n=1 then select id,rate_per_pcs into v_version,v_rate from erp.laundry_vendor_rate_versions where vendor_id=r.vendor_id and wash_process_id=v_process
   and effective_from<=r.physical_sent_at and (effective_to is null or effective_to>r.physical_sent_at);end if;
 insert into erp.be_redye_services_v1(id,vendor_id,wash_process_id,po_id,sent_at,qty,rate_version_id,initial_rate,created_by)
 values(r.id,r.vendor_id,v_process,b.po_id,r.physical_sent_at,r.qty_sent,v_version,v_rate,erp.current_app_user_id());
 perform erp.be_redye_resync_v1(r.id,erp._cp3_business_date(r.physical_sent_at));
 return v_result||jsonb_build_object('service_id',r.id,'price_status',case when v_rate is null then 'UNKNOWN' else 'KNOWN' end,'rate',v_rate::text);
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_set_redye_price_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare s erp.be_redye_services_v1%rowtype;v_rate numeric;
begin
 perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
 perform erp._cp3_assert_closed_json_object(p_payload,array['service_id','rate','reason'],array['service_id','rate','reason'],'harga jasa celup');
 select * into s from erp.be_redye_services_v1 where id=erp.bd_uuid_v1(p_payload,'service_id',true) for update;
 if s.id is null then raise exception 'BE_SERVICE_NOT_FOUND';end if;
 if erp.be_redye_rate_v1(s.id) is not null then raise exception 'BE_PRICE_ALREADY_KNOWN: koreksi harga memakai invoice sumber';end if;
 v_rate:=erp.bd_amount_v1(p_payload->'rate','rate',false);
 insert into erp.be_redye_price_events_v1(service_id,rate,reason,created_by) values(s.id,v_rate,erp.bc_text_v1(p_payload,'reason',true,1000),erp.current_app_user_id());
 perform erp.be_redye_resync_v1(s.id,erp._cp3_business_date(statement_timestamp()));
 return jsonb_build_object('service_id',s.id,'rate',v_rate::text,'price_status','KNOWN');
end;$function$;

-- Called under the invoice's source locks, before any invoice journal is posted.
CREATE OR REPLACE FUNCTION erp.be_invoice_redye_line_v1(p_line uuid,p_billable jsonb,p_dec06 jsonb)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.bd_laundry_invoice_lines_v1%rowtype;i erp.bd_laundry_invoices_v1%rowtype;s erp.be_redye_services_v1%rowtype;
 v_billed int;v_cap int;v_complete bool;v_prior numeric;v_pool numeric;v_rel numeric;v_net numeric;v_paid bool;v_floor numeric;
begin
 select * into l from erp.bd_laundry_invoice_lines_v1 where id=p_line;select * into i from erp.bd_laundry_invoices_v1 where id=l.invoice_id;
 select * into s from erp.be_redye_services_v1 where id=l.rework_service_id for update;
 if s.id is null or s.vendor_id<>i.vendor_id then raise exception 'BD_INVOICE_VENDOR';end if;
 if i.invoice_date<erp._cp3_business_date((select completed_at from erp.rework_orders where id=s.id)) then raise exception 'BE_INVOICE_BEFORE_SERVICE';end if;
 v_pool:=erp.be_redye_estimate_v1(s.id);
 if v_pool is null then raise exception 'BE_PRICE_UNKNOWN_SET_FIRST';end if;
 if not p_billable @> to_jsonb(l.category) then raise exception 'BD_CATEGORY_NOT_BILLABLE';end if;
 select coalesce(sum(x.released_estimate),0) into v_prior from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id
   where x.rework_service_id=s.id and (y.status='POSTED' or (y.id=i.id and x.line_no<l.line_no));
 if l.line_kind='BILL' then
   v_cap:=erp.be_redye_capacity_v1(s.id,l.category);
   v_billed:=erp.be_redye_billed_v1(s.id,l.category)+coalesce((select sum(x.qty) from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id and x.rework_service_id=s.id and x.category=l.category and x.line_kind='BILL' and x.line_no<l.line_no),0);
   if v_billed+l.qty>v_cap then raise exception 'BD_INVOICE_CAPACITY';end if;
   select bool_and(erp.be_redye_billed_v1(s.id,c)+coalesce((select sum(x.qty) from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id and x.rework_service_id=s.id and x.category=c and x.line_kind='BILL' and x.line_no<=l.line_no),0)>=erp.be_redye_capacity_v1(s.id,c))
     into v_complete from jsonb_array_elements_text(p_billable) c;
   v_rel:=case when v_complete then v_pool-v_prior else least(round(v_pool*l.qty/s.qty,2),v_pool-v_prior) end;
 else
   if not exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id where x.rework_service_id=s.id and x.line_kind='BILL' and y.status='POSTED') then raise exception 'BD_CORRECTION_WITHOUT_BILL';end if;
   select exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id join erp.vendor_payments p on p.vendor_invoice_id=y.id and p.status='POSTED' where x.rework_service_id=s.id and y.status='POSTED') into v_paid;
   if v_paid and p_dec06->>'after_payment'<>'CORRECTION_DOCUMENT' then raise exception 'BD_PAID_CORRECTION_REFUSED';end if;
   select coalesce(sum(x.net_amount),0) into v_floor from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id where x.rework_service_id=s.id and y.status='POSTED';
   v_floor:=v_floor+coalesce((select sum(x.amount) from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id and x.rework_service_id=s.id and x.line_no<=l.line_no),0);
   if v_floor<0 then raise exception 'BD_CORRECTION_BELOW_ZERO';end if;
   v_rel:=0;v_complete:=false;
 end if;
 v_net:=l.amount-l.discount_share+l.rounding_share;
 if v_rel<0 then raise exception 'BE_NEGATIVE_RELEASE';end if;
 update erp.bd_laundry_invoice_lines_v1 set net_amount=v_net,released_estimate=v_rel,variance=v_net-v_rel,
  product_variance=case when p_dec06->>'variance_mode'='PRODUCT_COST' then v_net-v_rel else 0 end,completes_source=v_complete where id=l.id;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_redye_status_change_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
 if new.status='CANCELLED' and old.status is distinct from new.status and exists(select 1 from erp.be_redye_services_v1 where id=new.id) then
   if exists(select 1 from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id where l.rework_service_id=new.id and i.status='POSTED') then
     raise exception 'BE_REDYE_INVOICED: batalkan dahulu invoice sumber dan dependensinya';end if;
   perform erp.be_redye_resync_v1(new.id,erp._cp3_business_date(statement_timestamp()));
 end if;
 return new;
end;$function$;
create trigger be_redye_status after update of status on erp.rework_orders for each row execute function erp.be_redye_status_change_v1();

CREATE OR REPLACE FUNCTION erp.be_redye_workspace_v1(p_vendor uuid,p_money boolean)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce(jsonb_agg(jsonb_build_object('id',s.id,'number',r.rework_number,'vendor_id',s.vendor_id,'po_number',p.po_number,
   'status',r.status,'qty',s.qty,'good',r.qty_good_returned,'bs',r.qty_bs_returned,
   'billed_good',erp.be_redye_billed_v1(s.id,'GOOD'),'billed_bs',erp.be_redye_billed_v1(s.id,'BS'),
   'process',w.process_name,'price_known',erp.be_redye_rate_v1(s.id) is not null,
   'rate',case when p_money then erp.be_redye_rate_v1(s.id)::numeric(20,2)::text end,
   'cost',case when p_money then erp.be_redye_cost_v1(s.id)::numeric(20,2)::text end) order by s.sent_at desc,s.id),'[]'::jsonb)
 from erp.be_redye_services_v1 s join erp.rework_orders r on r.id=s.id join erp.production_orders p on p.id=s.po_id join erp.wash_processes w on w.id=s.wash_process_id
 where p_vendor is not null and s.vendor_id=p_vendor
$function$;
-- ALL-C04: evidenced historical expense and sewing output. No synthetic stock/work events.
create table erp.be_pocket_usage_v1(
 id uuid primary key,source_row_id uuid not null unique references erp.migration_staging_rows(id),batch_id uuid not null references erp.migration_batches(id),
 document_number text not null,line_number text not null,physical_date date not null,material_id uuid not null references erp.materials(id),
 material_qty numeric(18,6) not null check(material_qty>0),original_amount numeric(20,2) not null check(original_amount>0),
 allocation_status text not null check(allocation_status in('ALLOCATED','UNALLOCATED')),prior_allocation_reference text,
 journal_id uuid references erp.journal_entries(id),created_at timestamptz not null default statement_timestamp(),
 check((allocation_status='ALLOCATED')=(prior_allocation_reference is not null))
);
create unique index be_pocket_usage_identity on erp.be_pocket_usage_v1(lower(btrim(document_number)),lower(btrim(line_number)));
create table erp.be_pocket_sewing_v1(
 id uuid primary key,source_row_id uuid not null unique references erp.migration_staging_rows(id),batch_id uuid not null references erp.migration_batches(id),
 document_number text not null,line_number text not null,physical_date date not null,contractor_id uuid not null references erp.contractors(id),
 qty bigint not null check(qty>0),target_kind text not null check(target_kind in('WIP','BS','FINISHED_GOODS','COGS')),
 opening_item_id uuid references erp.opening_balance_items(id),po_id uuid references erp.production_orders(id),product_id uuid references erp.products(id),
 sold_reference text,created_at timestamptz not null default statement_timestamp(),
 check((target_kind='COGS' and opening_item_id is null and product_id is not null and sold_reference is not null)
   or (target_kind<>'COGS' and opening_item_id is not null and sold_reference is null))
);
create unique index be_pocket_sewing_identity on erp.be_pocket_sewing_v1(lower(btrim(document_number)),lower(btrim(line_number)));
create table erp.be_pocket_source_events_v1(
 id uuid primary key,usage_id uuid not null references erp.be_pocket_usage_v1(id),previous_amount numeric(20,2) not null,
 new_amount numeric(20,2) not null check(new_amount>=0),economic_date date not null,reason text not null,
 journal_id uuid not null references erp.journal_entries(id),created_by uuid,created_at timestamptz not null default clock_timestamp()
);
create table erp.be_pocket_target_events_v1(
 id uuid primary key default gen_random_uuid(),pool_id uuid not null references erp.pocket_periods(id),
 sewing_id uuid not null references erp.be_pocket_sewing_v1(id),opening_item_id uuid not null references erp.opening_balance_items(id),
 previous_amount numeric(20,2) not null,new_amount numeric(20,2) not null,economic_date date not null,
 created_by uuid,created_at timestamptz not null default clock_timestamp()
);
-- Preserve the old unique native source identity; add an explicit alternative FK for history.
alter table erp.pocket_period_sources drop constraint pocket_period_sources_pkey;
alter table erp.pocket_period_sources alter column adjustment_id drop not null;
alter table erp.pocket_period_sources add column historical_usage_id uuid references erp.be_pocket_usage_v1(id);
alter table erp.pocket_period_sources add column id uuid generated always as(coalesce(adjustment_id,historical_usage_id)) stored;
alter table erp.pocket_period_sources add primary key(pool_id,id);
alter table erp.pocket_period_sources add constraint be_pocket_source_exactly_one check(num_nonnulls(adjustment_id,historical_usage_id)=1);
create unique index be_pocket_source_native on erp.pocket_period_sources(pool_id,adjustment_id);
create unique index be_pocket_source_history on erp.pocket_period_sources(pool_id,historical_usage_id);
alter table erp.pocket_period_destinations drop constraint pocket_period_destinations_pkey;
alter table erp.pocket_period_destinations alter column event_id drop not null;
alter table erp.pocket_period_destinations alter column po_id drop not null;
alter table erp.pocket_period_destinations add column historical_sewing_id uuid references erp.be_pocket_sewing_v1(id);
alter table erp.pocket_period_destinations add column id uuid generated always as(coalesce(event_id,historical_sewing_id)) stored;
alter table erp.pocket_period_destinations add primary key(pool_id,id);
alter table erp.pocket_period_destinations add constraint be_pocket_destination_exactly_one check(num_nonnulls(event_id,historical_sewing_id)=1 and (event_id is null or po_id is not null));
create unique index be_pocket_destination_native on erp.pocket_period_destinations(pool_id,event_id);
create unique index be_pocket_destination_history on erp.pocket_period_destinations(pool_id,historical_sewing_id);

CREATE OR REPLACE FUNCTION erp.be_pocket_immutable_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$ begin raise exception 'BE_POCKET_HISTORY_IMMUTABLE: gunakan koreksi atau pembatalan tertaut';end;$function$;
create trigger be_pocket_usage_immutable before update or delete on erp.be_pocket_usage_v1 for each row execute function erp.be_pocket_immutable_v1();
create trigger be_pocket_sewing_immutable before update or delete on erp.be_pocket_sewing_v1 for each row execute function erp.be_pocket_immutable_v1();
create trigger be_pocket_source_event_immutable before update or delete on erp.be_pocket_source_events_v1 for each row execute function erp.be_pocket_immutable_v1();
create trigger be_pocket_target_event_immutable before update or delete on erp.be_pocket_target_events_v1 for each row execute function erp.be_pocket_immutable_v1();

CREATE OR REPLACE FUNCTION erp.be_pocket_usage_amount_v1(p_usage uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select u.original_amount+coalesce((select sum(e.new_amount-e.previous_amount) from erp.be_pocket_source_events_v1 e where e.usage_id=u.id),0)
 from erp.be_pocket_usage_v1 u where u.id=p_usage
$function$;
CREATE OR REPLACE FUNCTION erp.be_pocket_opening_extra_v1(p_item uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select coalesce(sum(new_amount-previous_amount),0) from erp.be_pocket_target_events_v1 where opening_item_id=p_item $function$;

CREATE OR REPLACE FUNCTION erp.be_check_pocket_import_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;c date;d date;t record;v_qty numeric;v_amount numeric;v_kind text;
begin
 perform erp.require_owner_admin();perform erp.pocket_period_lock_v1();
 select * into strict r from erp.migration_staging_rows where id=p_row and batch_id=p_batch;
 j:=r.normalized_payload;select null::uuid id,null::jsonb p into t;
 foreach k in array array['document_number','line_number','physical_date','qty'] loop
  if nullif(btrim(j->>k),'') is null or length(j->>k)>120 then raise exception 'BE_POCKET_PROVENANCE: % wajib dan maksimal 120 karakter',k;end if;
 end loop;
 if j->>'physical_date' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'BE_POCKET_DATE';end if;
 d:=(j->>'physical_date')::date;select erp._cp3_business_date(cutover_at) into c from erp.migration_batches where id=p_batch;
 if d>=c or d::text<>j->>'physical_date' then raise exception 'BE_POCKET_DATE: riwayat harus sebelum tanggal cutover';end if;
 if j->>'qty' !~ '^[0-9]+([.][0-9]{1,6})?$' or (j->>'qty')::numeric<=0 then raise exception 'BE_POCKET_QTY';end if;
 v_qty:=(j->>'qty')::numeric(18,6);
 if exists(select 1 from erp.migration_staging_rows x where x.entity_type=r.entity_type and x.id<>r.id
   and lower(btrim(x.normalized_payload->>'document_number'))=lower(btrim(j->>'document_number'))
   and lower(btrim(x.normalized_payload->>'line_number'))=lower(btrim(j->>'line_number'))
   and (x.batch_id=p_batch or x.posted_entity_id is not null)) then raise exception 'BE_POCKET_DUPLICATE_SOURCE: dokumen dan baris telah dipakai';end if;
 if exists(select 1 from erp.pocket_periods p where erp.pocket_period_active_v1(p.id) and d between p.period_start and p.period_end) then
  raise exception 'BE_POCKET_PERIOD_ACTIVE: batalkan alokasi periode sebelum menambah sumber historis';end if;
 if r.entity_type='OPENING_POCKET_USAGE' then
  v_amount:=erp.bb_parse_amount_v1(j->>'amount','amount',false);v_kind:=upper(j->>'allocation_status');
  if v_kind is null or v_kind not in('ALLOCATED','UNALLOCATED') then raise exception 'BE_POCKET_ALLOCATION_STATUS';end if;
  if (v_kind='ALLOCATED')<>(nullif(btrim(j->>'prior_allocation_reference'),'') is not null) then raise exception 'BE_POCKET_PRIOR_ALLOCATION: referensi wajib hanya untuk nilai yang telah dialokasikan';end if;
  if not exists(select 1 from erp.materials where material_sku=j->>'material_sku' and is_active)
   and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='MATERIAL' and validation_status='VALID' and normalized_payload->>'material_sku'=j->>'material_sku') then raise exception 'BE_POCKET_MATERIAL';end if;
  -- An independent source-sheet total is a control, never a second journal.
  if nullif(btrim(j->>'control_key'),'') is null then raise exception 'BE_POCKET_CONTROL_REQUIRED';end if;
  if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type=r.entity_type and x.normalized_payload->>'control_key'=j->>'control_key'
    and (x.normalized_payload->>'control_amount' is distinct from j->>'control_amount' or x.normalized_payload->>'control_qty' is distinct from j->>'control_qty')) then raise exception 'BE_POCKET_CONTROL_INCONSISTENT';end if;
  if (select sum((normalized_payload->>'amount')::numeric) from erp.migration_staging_rows where batch_id=p_batch and entity_type=r.entity_type and normalized_payload->>'control_key'=j->>'control_key')
      is distinct from erp.bb_parse_amount_v1(j->>'control_amount','control_amount',false)
   or (select sum((normalized_payload->>'qty')::numeric) from erp.migration_staging_rows where batch_id=p_batch and entity_type=r.entity_type and normalized_payload->>'control_key'=j->>'control_key')
      is distinct from (j->>'control_qty')::numeric then raise exception 'BE_POCKET_CONTROL_MISMATCH';end if;
  perform erp.be_pocket_check_receipt_origin_v1(p_batch,j);
  return jsonb_build_object('qty',v_qty,'amount',v_amount,'physical_date',d,'kind',v_kind);
 elsif r.entity_type='OPENING_POCKET_SEWING' then
  if v_qty<>trunc(v_qty) or v_qty>2147483647 then raise exception 'BE_POCKET_SEWING_PCS';end if;
  if nullif(btrim(j->>'control_key'),'') is null or coalesce(j->>'control_qty','') !~ '^[1-9][0-9]*$' then raise exception 'BE_POCKET_DENOMINATOR_CONTROL_REQUIRED';end if;
  if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type=r.entity_type and x.normalized_payload->>'control_key'=j->>'control_key'
     and x.normalized_payload->>'control_qty' is distinct from j->>'control_qty')
   or (select sum((x.normalized_payload->>'qty')::numeric) from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type=r.entity_type and x.normalized_payload->>'control_key'=j->>'control_key')
     is distinct from (j->>'control_qty')::numeric then raise exception 'BE_POCKET_DENOMINATOR_INCOMPLETE';end if;
  v_kind:=upper(j->>'target_kind');
  if v_kind is null or v_kind not in('WIP','BS','FINISHED_GOODS','COGS') then raise exception 'BE_POCKET_TARGET';end if;
  if not exists(select 1 from erp.contractors where contractor_code=j->>'contractor_code')
   and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='CONTRACTOR' and validation_status='VALID' and normalized_payload->>'contractor_code'=j->>'contractor_code') then raise exception 'BE_POCKET_CONTRACTOR';end if;
  if v_kind='COGS' then
   if nullif(btrim(j->>'sold_reference'),'') is null or nullif(btrim(j->>'target_source_key'),'') is not null then raise exception 'BE_POCKET_SOLD_PROVENANCE';end if;
   if not exists(select 1 from erp.products where sku=j->>'product_sku')
    and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='PRODUCT' and validation_status='VALID' and normalized_payload->>'sku'=j->>'product_sku') then raise exception 'BE_POCKET_PRODUCT';end if;
  else
   if nullif(btrim(j->>'sold_reference'),'') is not null then raise exception 'BE_POCKET_TARGET_AMBIGUOUS';end if;
   select s.id,s.normalized_payload p into t from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_BALANCE_ITEM'
     and s.validation_status='VALID' and s.normalized_payload->>'opening_source_key'=j->>'target_source_key';
   if t.id is null or upper(t.p->>'balance_type')<>v_kind or (v_kind in('WIP','BS') and nullif(t.p->>'po_number','') is null) then raise exception 'BE_POCKET_TARGET_SOURCE_REQUIRED';end if;
   if (select sum((x.normalized_payload->>'qty')::numeric) from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type=r.entity_type and x.normalized_payload->>'target_source_key'=j->>'target_source_key')>(t.p->>'qty')::numeric then raise exception 'BE_POCKET_SEWING_EXCEEDS_OPENING';end if;
  end if;
  return jsonb_build_object('qty',v_qty,'physical_date',d,'kind',v_kind,'target_row',case when v_kind<>'COGS' then t.id end);
 end if;
 raise exception 'BE_POCKET_IMPORT_ENTITY';
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_validate_pocket_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;
begin
 for r in select id from erp.migration_staging_rows where batch_id=p_batch and entity_type in('OPENING_POCKET_USAGE','OPENING_POCKET_SEWING') order by entity_type,source_row_no loop
  begin
   perform erp.be_check_pocket_import_v1(p_batch,r.id);
   update erp.migration_staging_rows set validation_status='VALID',validation_errors='[]' where id=r.id;
  exception when others then update erp.migration_staging_rows set validation_status='ERROR',validation_errors=jsonb_build_array(sqlerrm) where id=r.id;end;
 end loop;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_apply_pocket_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;j jsonb;c jsonb;v_id uuid;v_date date;v_journal uuid;v_item uuid;v_po uuid;
begin
 perform erp.require_owner_admin();perform erp.pocket_period_lock_v1();
 select erp._cp3_business_date(cutover_at) into strict v_date from erp.migration_batches where id=p_batch;
 for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type in('OPENING_POCKET_USAGE','OPENING_POCKET_SEWING') and posted_entity_id is null order by entity_type,source_row_no loop
  if r.validation_status<>'VALID' then raise exception 'BE_POCKET_IMPORT_NOT_VALID';end if;
  j:=r.normalized_payload;c:=erp.be_check_pocket_import_v1(p_batch,r.id);v_id:=gen_random_uuid();v_journal:=null;
  if r.entity_type='OPENING_POCKET_USAGE' then
   if c->>'kind'='UNALLOCATED' then
    v_journal:=erp.post_journal('BE_OPENING_POCKET_EXPENSE',v_id,v_date,'Pengeluaran kain kantong sebelum cutover '||btrim(j->>'document_number'),jsonb_build_array(
     jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',(c->>'amount')::numeric,'credit',0),
     jsonb_build_object('mapping_key','OPENING_EQUITY','debit',0,'credit',(c->>'amount')::numeric)));
   end if;
   insert into erp.be_pocket_usage_v1(id,source_row_id,batch_id,document_number,line_number,physical_date,material_id,material_qty,original_amount,allocation_status,prior_allocation_reference,journal_id)
   values(v_id,r.id,p_batch,btrim(j->>'document_number'),btrim(j->>'line_number'),(c->>'physical_date')::date,
    (select id from erp.materials where material_sku=j->>'material_sku'),(c->>'qty')::numeric,(c->>'amount')::numeric,c->>'kind',nullif(btrim(j->>'prior_allocation_reference'),''),v_journal);
   perform erp.be_pocket_link_receipt_origin_v1(v_id,p_batch,j);
  else
   v_item:=null;v_po:=null;
   if c->>'target_row' is not null then
    select opening_item_id into strict v_item from erp.initial_import_opening_stock_sources where batch_id=p_batch and source_row_id=(c->>'target_row')::uuid;
    select po_id into v_po from erp.initial_import_production_sources where opening_item_id=v_item;
   end if;
   insert into erp.be_pocket_sewing_v1(id,source_row_id,batch_id,document_number,line_number,physical_date,contractor_id,qty,target_kind,opening_item_id,po_id,product_id,sold_reference)
   values(v_id,r.id,p_batch,btrim(j->>'document_number'),btrim(j->>'line_number'),(c->>'physical_date')::date,
    (select id from erp.contractors where contractor_code=j->>'contractor_code'),(c->>'qty')::numeric::bigint,c->>'kind',v_item,v_po,
    (select id from erp.products where sku=j->>'product_sku'),nullif(btrim(j->>'sold_reference'),''));
  end if;
  update erp.migration_staging_rows set posted_entity_id=v_id,posted_entity_type=r.entity_type,posted_at=statement_timestamp(),updated_at=statement_timestamp() where id=r.id;
 end loop;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_pocket_import_workspace_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select jsonb_build_object('pocket_usage',coalesce((select jsonb_agg(jsonb_build_object('id',u.id,'document_number',u.document_number,'line_number',u.line_number,
  'date',u.physical_date,'material_sku',m.material_sku,'qty',u.material_qty::text,'original_amount',u.original_amount::text,'amount',erp.be_pocket_usage_amount_v1(u.id)::numeric(20,2)::text,
  'allocation_status',u.allocation_status,'prior_allocation_reference',u.prior_allocation_reference,
  'active_period',(select s.pool_id from erp.pocket_period_sources s where s.historical_usage_id=u.id and erp.pocket_period_active_v1(s.pool_id))) order by u.physical_date,u.document_number,u.line_number)
  from erp.be_pocket_usage_v1 u join erp.materials m on m.id=u.material_id where u.batch_id=p_batch),'[]'),
 'pocket_sewing',coalesce((select jsonb_agg(jsonb_build_object('id',s.id,'document_number',s.document_number,'line_number',s.line_number,'date',s.physical_date,
  'contractor_name',c.contractor_name,'qty',s.qty,'target_kind',s.target_kind,'opening_item_id',s.opening_item_id,'po_id',s.po_id,'sold_reference',s.sold_reference,
  'allocated_amount',coalesce((select sum(erp.pocket_period_amount_v1(d.pool_id,d.preceding_qty,d.sewing_qty)) from erp.pocket_period_destinations d where d.historical_sewing_id=s.id),0)::numeric(20,2)::text) order by s.physical_date,s.document_number,s.line_number)
  from erp.be_pocket_sewing_v1 s join erp.contractors c on c.id=s.contractor_id where s.batch_id=p_batch),'[]'))
$function$;

CREATE OR REPLACE FUNCTION erp.be_pocket_sync_targets_v1(p_pool uuid,p_date date,p_cancel boolean)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;v_before numeric;v_target numeric;v_delta numeric;
begin
 perform erp.require_internal();perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 for r in select d.*,s.opening_item_id,s.target_kind from erp.pocket_period_destinations d join erp.be_pocket_sewing_v1 s on s.id=d.historical_sewing_id
   where d.pool_id=p_pool and s.opening_item_id is not null order by s.opening_item_id,s.id loop
  select coalesce(sum(new_amount-previous_amount),0) into v_before from erp.be_pocket_target_events_v1 where pool_id=p_pool and sewing_id=r.historical_sewing_id;
  v_target:=case when p_cancel then 0 else erp.pocket_period_amount_v1(p_pool,r.preceding_qty,r.sewing_qty) end;v_delta:=v_target-v_before;
  if v_delta=0 then continue;end if;
  insert into erp.be_pocket_target_events_v1(pool_id,sewing_id,opening_item_id,previous_amount,new_amount,economic_date,created_by)
   values(p_pool,r.historical_sewing_id,r.opening_item_id,v_before,v_target,p_date,erp.current_app_user_id());
  if r.target_kind='FINISHED_GOODS' then perform erp.refresh_initial_import_fg_cost_v1(r.opening_item_id,v_delta,p_date);
  else
   perform erp.sync_initial_import_bs_value_v1(r.opening_item_id,p_date);
   perform erp.bb_sync_item_split_values_v1(r.opening_item_id,p_date);
  end if;
 end loop;
end;$function$;

-- Historical documents select a period; their opening value first exists at cutover.
-- This never changes the closed-period lock for a period containing native transactions.
CREATE OR REPLACE FUNCTION erp.be_pocket_period_post_date_v1(p_manifest jsonb,p_end date)
 RETURNS date LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select greatest(p_end,(select max(erp._cp3_business_date(b.cutover_at)) from erp.migration_batches b where b.id in(
  select u.batch_id from erp.be_pocket_usage_v1 u join jsonb_array_elements(p_manifest->'sources') x on u.id=(x->>'historical_usage_id')::uuid
  union select s.batch_id from erp.be_pocket_sewing_v1 s join jsonb_array_elements(p_manifest->'destinations') x on s.id=(x->>'historical_sewing_id')::uuid)))
$function$;

CREATE OR REPLACE FUNCTION erp.be_correct_pocket_usage_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare u erp.be_pocket_usage_v1%rowtype;v_amount numeric;v_old numeric;v_date date;v_reason text;v_journal uuid;v_pool uuid;v_cached jsonb;r jsonb;
begin
 perform erp.require_owner_admin();perform erp.require_permission('warehouse.stock.adjust');perform erp.require_permission('finance.hpp.manage');
 perform erp._cp3_assert_closed_json_object(p_payload,array['usage_id','amount','economic_date','expected_amount','reason'],array['usage_id','amount','economic_date','expected_amount','reason'],'koreksi kain kantong');
 v_cached:=erp._idempotency_begin('be_correct_pocket_usage_v1',p_request,erp._request_hash(p_payload));if v_cached is not null then return v_cached;end if;
 perform erp.pocket_period_lock_v1();select * into u from erp.be_pocket_usage_v1 where id=(p_payload->>'usage_id')::uuid for update;
 if u.id is null or u.allocation_status<>'UNALLOCATED' then raise exception 'BE_POCKET_CORRECTION_SOURCE: pilih sumber pool yang belum dialokasikan sebelum cutover';end if;
 if exists(select 1 from erp.be_pocket_receipt_origins_v1 where usage_id=u.id) then raise exception 'BE_POCKET_USE_SUPPLIER_INVOICE: koreksi nilai harus melalui nota supplier sumber';end if;
 v_old:=erp.be_pocket_usage_amount_v1(u.id);v_amount:=erp.bb_parse_amount_v1(p_payload->>'amount','amount',true);
 if v_old is distinct from (p_payload->>'expected_amount')::numeric then raise exception 'STALE_VERSION: nilai sumber kain kantong berubah';end if;
 v_date:=(p_payload->>'economic_date')::date;v_reason:=nullif(btrim(p_payload->>'reason'),'');
 if v_date is null or v_date<(select erp._cp3_business_date(cutover_at) from erp.migration_batches where id=u.batch_id)
  or v_date>erp._cp3_business_date(statement_timestamp()) or v_reason is null then raise exception 'BE_POCKET_CORRECTION_DATE_REASON';end if;
 if v_amount=v_old then raise exception 'BE_POCKET_NO_CHANGE';end if;
 v_journal:=erp.post_journal('BE_POCKET_SOURCE_CORRECTION',p_request,v_date,v_reason,jsonb_build_array(
  jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',greatest(v_amount-v_old,0),'credit',greatest(v_old-v_amount,0)),
  jsonb_build_object('mapping_key','OPENING_EQUITY','debit',greatest(v_old-v_amount,0),'credit',greatest(v_amount-v_old,0))));
 insert into erp.be_pocket_source_events_v1(id,usage_id,previous_amount,new_amount,economic_date,reason,journal_id,created_by)
 values(p_request,u.id,v_old,v_amount,v_date,v_reason,v_journal,erp.current_app_user_id());
 for v_pool in select pool_id from erp.pocket_period_sources where historical_usage_id=u.id and erp.pocket_period_active_v1(pool_id) order by pool_id loop
  perform erp.sync_pocket_period_v1(v_pool,v_date,'RECOST',v_reason);
 end loop;
 r:=jsonb_build_object('action','CORRECT_OPENING_USAGE','request_id',p_request,'id',u.id,'status','CORRECTED','usage_id',u.id,'amount',v_amount::numeric(20,2)::text);
 return erp._idempotency_complete('be_correct_pocket_usage_v1',p_request,r);
end;$function$;

-- Historical consumed receipt quantities are explicit origins, never stock movements.
create table erp.be_pocket_receipt_origins_v1(
 usage_id uuid primary key references erp.be_pocket_usage_v1(id),purchase_item_id uuid not null references erp.material_purchase_items(id),
 material_qty numeric(18,6) not null check(material_qty>0),unit_cost_snapshot numeric(18,6) not null check(unit_cost_snapshot>=0)
);
create trigger be_pocket_receipt_immutable before update or delete on erp.be_pocket_receipt_origins_v1 for each row execute function erp.be_pocket_immutable_v1();
CREATE OR REPLACE FUNCTION erp.be_pocket_receipt_staged_qty_v1(p_batch uuid,p_receipt jsonb)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce(sum((x.normalized_payload->>'qty')::numeric),0) from erp.migration_staging_rows x
 where x.batch_id=p_batch and x.entity_type='OPENING_POCKET_USAGE' and x.validation_status='VALID'
  and x.normalized_payload->>'supplier_code'=p_receipt->>'supplier_code'
  and lower(btrim(x.normalized_payload->>'receipt_number'))=lower(btrim(p_receipt->>'receipt_number'))
  and lower(btrim(x.normalized_payload->>'receipt_line_number'))=lower(btrim(p_receipt->>'receipt_line_number'))
$function$;
CREATE OR REPLACE FUNCTION erp.be_pocket_check_receipt_origin_v1(p_batch uuid,p_usage jsonb)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare n integer;r erp.migration_staging_rows%rowtype;v_part jsonb;v_cost numeric;
begin
 n:=num_nonnulls(nullif(btrim(p_usage->>'supplier_code'),''),nullif(btrim(p_usage->>'receipt_number'),''),nullif(btrim(p_usage->>'receipt_line_number'),''));
 if n=0 then return;end if;
 if n<>3 or upper(p_usage->>'allocation_status')<>'UNALLOCATED' then raise exception 'BE_POCKET_RECEIPT_IDENTITY: sumber penerimaan wajib lengkap, hanya pool yang belum dialokasikan';end if;
 if (select count(*) from erp.migration_staging_rows where batch_id=p_batch and entity_type='UNINVOICED_RECEIPT'
  and normalized_payload->>'supplier_code'=p_usage->>'supplier_code'
  and lower(btrim(normalized_payload->>'receipt_number'))=lower(btrim(p_usage->>'receipt_number'))
  and lower(btrim(normalized_payload->>'receipt_line_number'))=lower(btrim(p_usage->>'receipt_line_number')))<>1 then raise exception 'BE_POCKET_RECEIPT_REQUIRED';end if;
 select * into r from erp.migration_staging_rows where batch_id=p_batch and entity_type='UNINVOICED_RECEIPT'
  and normalized_payload->>'supplier_code'=p_usage->>'supplier_code'
  and lower(btrim(normalized_payload->>'receipt_number'))=lower(btrim(p_usage->>'receipt_number'))
  and lower(btrim(normalized_payload->>'receipt_line_number'))=lower(btrim(p_usage->>'receipt_line_number'));
 if r.normalized_payload->>'material_sku' is distinct from p_usage->>'material_sku' then raise exception 'BE_POCKET_RECEIPT_MATERIAL';end if;
 v_part:=erp.bb_receipt_row_invoiced_part_v1(p_batch,r.id);v_cost:=(r.normalized_payload->>'unit_cost')::numeric;
 if v_part is not null then v_cost:=round(((r.normalized_payload->>'qty')::numeric*v_cost+(v_part->>'invoiced_amount')::numeric)/((r.normalized_payload->>'qty')::numeric+(v_part->>'invoiced_qty')::numeric),6);end if;
 if round((p_usage->>'qty')::numeric*v_cost,2) is distinct from (p_usage->>'amount')::numeric then raise exception 'BE_POCKET_RECEIPT_VALUE: nilai sumber harus sama dengan qty bahan dikali biaya penerimaan';end if;
end;$function$;
CREATE OR REPLACE FUNCTION erp.be_pocket_link_receipt_origin_v1(p_usage uuid,p_batch uuid,p_payload jsonb)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_item uuid;
begin
 if nullif(btrim(p_payload->>'receipt_number'),'') is null then return;end if;
 select l.purchase_item_id into strict v_item from erp.initial_import_receipt_lines l join erp.initial_import_receipt_headers h on h.purchase_id=l.purchase_id
  join erp.suppliers s on s.id=h.supplier_id where h.batch_id=p_batch and s.supplier_code=p_payload->>'supplier_code'
  and lower(btrim(h.receipt_number))=lower(btrim(p_payload->>'receipt_number')) and lower(btrim(l.receipt_line_number))=lower(btrim(p_payload->>'receipt_line_number'));
 insert into erp.be_pocket_receipt_origins_v1(usage_id,purchase_item_id,material_qty,unit_cost_snapshot)
 values(p_usage,v_item,(p_payload->>'qty')::numeric,erp.bb_receipt_opening_unit_cost_v1(v_item));
end;$function$;
CREATE OR REPLACE FUNCTION erp.be_pocket_recost_receipt_v1(p_item uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;v_old numeric;v_new numeric;v_delta numeric;v_event uuid;v_journal uuid;v_date date;v_pool uuid;
begin
 perform erp.require_internal();perform erp.pocket_period_lock_v1();
 v_date:=coalesce(erp.invoice_recost_economic_date_v1(),erp._cp3_business_date(statement_timestamp()));
 for r in select * from erp.be_pocket_receipt_origins_v1 where purchase_item_id=p_item order by usage_id loop
  v_old:=erp.be_pocket_usage_amount_v1(r.usage_id);v_new:=round(r.material_qty*erp.material_purchase_current_unit_cost(p_item),2);v_delta:=v_new-v_old;
  if v_delta=0 then continue;end if;v_event:=gen_random_uuid();
  v_journal:=erp.post_journal('BE_POCKET_RECEIPT_RECOST',v_event,v_date,'Koreksi nota sumber kain kantong sebelum cutover',jsonb_build_array(
   jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',greatest(v_delta,0),'credit',greatest(-v_delta,0)),
   jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',greatest(-v_delta,0),'credit',greatest(v_delta,0))));
  insert into erp.be_pocket_source_events_v1(id,usage_id,previous_amount,new_amount,economic_date,reason,journal_id,created_by)
   values(v_event,r.usage_id,v_old,v_new,v_date,'Koreksi nota sumber kain kantong sebelum cutover',v_journal,erp.current_app_user_id());
  for v_pool in select pool_id from erp.pocket_period_sources where historical_usage_id=r.usage_id and erp.pocket_period_active_v1(pool_id) order by pool_id loop
   perform erp.sync_pocket_period_v1(v_pool,v_date,'RECOST','Koreksi nota sumber kain kantong sebelum cutover');
  end loop;
 end loop;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_pocket_workspace_v1(p_query text)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 with sources as(select u.id,u.document_number,u.line_number,u.physical_date date,m.material_sku,m.material_name,u.material_qty::text qty,
  u.original_amount::text original_amount,erp.be_pocket_usage_amount_v1(u.id)::numeric(20,2)::text amount,u.allocation_status,u.prior_allocation_reference,
  exists(select 1 from erp.be_pocket_receipt_origins_v1 o where o.usage_id=u.id) receipt_backed,
  (select s.pool_id from erp.pocket_period_sources s where s.historical_usage_id=u.id and erp.pocket_period_active_v1(s.pool_id)) active_period
  from erp.be_pocket_usage_v1 u join erp.materials m on m.id=u.material_id
  where coalesce(btrim(p_query),'')='' or strpos(lower(concat_ws(' ',u.document_number,u.line_number,m.material_sku,m.material_name)),lower(btrim(p_query)))>0),
 targets as(select s.id,s.document_number,s.line_number,s.physical_date date,c.contractor_name,s.qty,s.target_kind,s.sold_reference,
  coalesce(k.source_key,p.sku) target_reference,
  coalesce((select sum(erp.pocket_period_amount_v1(d.pool_id,d.preceding_qty,d.sewing_qty)) from erp.pocket_period_destinations d where d.historical_sewing_id=s.id),0)::numeric(20,2)::text allocated_amount
  from erp.be_pocket_sewing_v1 s join erp.contractors c on c.id=s.contractor_id
  left join erp.initial_import_opening_stock_sources k on k.opening_item_id=s.opening_item_id left join erp.products p on p.id=s.product_id
  where coalesce(btrim(p_query),'')='' or strpos(lower(concat_ws(' ',s.document_number,s.line_number,c.contractor_name,k.source_key,p.sku)),lower(btrim(p_query)))>0)
 select jsonb_build_object('opening_usage',coalesce((select jsonb_agg(to_jsonb(x) order by x.date desc,x.id) from(select * from sources order by date desc,id limit 100) x),'[]'),
  'opening_usage_count',(select count(*) from sources),'opening_sewing',coalesce((select jsonb_agg(to_jsonb(x) order by x.date desc,x.id) from(select * from targets order by date desc,id limit 100) x),'[]'),
  'opening_sewing_count',(select count(*) from targets))
$function$;
CREATE OR REPLACE FUNCTION erp.post_product_conversion(p_conversion_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.product_conversions%rowtype;
  r record;
  v_need integer;
  v_take integer;
  v_source_hpp numeric(18,6);
  v_dest_hpp numeric(18,6);
  v_dest_lot uuid;
  v_dest_lot_no text;
  v_source_value numeric(24,6):=0;
  v_lock_product uuid;
  v_po uuid;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into h from erp.product_conversions
  where id=p_conversion_id for update;
  if h.id is null or h.status<>'DRAFT' then
    raise exception 'Product conversion must be DRAFT';
  end if;
  if coalesce(h.conversion_cost_total,0)<>0 then
    raise exception 'Non-zero conversion cost requires a sourced accounting workflow; unsafe unsourced HPP capitalization is blocked';
  end if;

  perform erp.assert_product_identity_time(
    h.from_product_id,h.physical_at,'EXISTING_STOCK');
  perform erp.assert_product_identity_time(
    h.to_product_id,h.physical_at,'NEW_STOCK');

  -- Fail before the first new fact.  A mixed PO/non-PO FIFO pool is also
  -- rejected rather than silently attributing only part of the conversion.
  if exists(
    select 1
    from erp.fg_lots fl
    join erp.fg_stock_movements fm on fm.lot_id=fl.id
    where fl.product_id=h.from_product_id and fl.po_id is null and not erp.be_nonpo_admitted_v1(h.id)
      and (not exists(select 1 from erp.be_conversion_sources_v1 where conversion_id=h.id)
        or fl.id=(select source_lot_id from erp.be_conversion_sources_v1 where conversion_id=h.id))
      and fm.location_id=h.location_id and fm.quality_grade='GRADE_A'
    group by fl.id
    having sum(fm.qty_signed)>0
  ) then
    raise exception 'NON_PO_CONVERSION_REQUIRES_SOURCED_HPP_WORKFLOW';
  end if;

  insert into erp.fg_inventory_balances(
    product_id,location_id,quality_grade,cached_qty_pcs
  ) values(h.from_product_id,h.location_id,'GRADE_A',0)
  on conflict(product_id,location_id,quality_grade) do nothing;
  insert into erp.fg_inventory_balances(
    product_id,location_id,quality_grade,cached_qty_pcs
  ) values(h.to_product_id,h.location_id,'GRADE_A',0)
  on conflict(product_id,location_id,quality_grade) do nothing;
  for v_lock_product in
    select x from (values(h.from_product_id),(h.to_product_id)) v(x)
    group by x order by x
  loop
    perform 1 from erp.fg_inventory_balances
    where product_id=v_lock_product and location_id=h.location_id
      and quality_grade='GRADE_A' for update;
  end loop;

  v_need:=h.qty_pcs;
  delete from erp.product_conversion_allocations where conversion_id=h.id;
  for r in
    select fl.id,fl.po_id,fl.produced_at,
      sum(fm.qty_signed)::integer location_qty
    from erp.fg_lots fl
    join erp.fg_stock_movements fm on fm.lot_id=fl.id
    where fl.product_id=h.from_product_id and (fl.po_id is not null or erp.be_nonpo_admitted_v1(h.id))
      and (not exists(select 1 from erp.be_conversion_sources_v1 where conversion_id=h.id)
        or fl.id=(select source_lot_id from erp.be_conversion_sources_v1 where conversion_id=h.id))
      and fm.location_id=h.location_id and fm.quality_grade='GRADE_A'
    group by fl.id,fl.po_id,fl.produced_at
    having sum(fm.qty_signed)>0
    order by fl.produced_at,fl.id
  loop
    exit when v_need<=0;
    v_take:=least(v_need,r.location_qty);
    perform 1 from erp.fg_lots where id=r.id for update;
    v_source_hpp:=coalesce(erp.lock_current_hpp_per_pcs(r.id),0);
    v_dest_hpp:=v_source_hpp;
    v_dest_lot_no:=h.conversion_number||'-'||substr(r.id::text,1,8)
      ||'-'||substr(gen_random_uuid()::text,1,6);
    insert into erp.fg_lots(
      lot_number,po_id,qc_item_id,product_id,initial_qty_pcs,cached_qty_pcs,
      produced_at,is_open,lot_origin,source_lot_id
    ) values(
      v_dest_lot_no,r.po_id,null,h.to_product_id,v_take,0,h.physical_at,
      true,'CONVERSION',r.id
    ) returning id into v_dest_lot;
    insert into erp.hpp_versions(
      lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,
      calculation_reason,created_by
    ) values(
      v_dest_lot,1,'ADJUSTED',v_take,v_take*v_dest_hpp,true,
      'SKU conversion/rebrand carry-forward',erp.current_app_user_id()
    );
    insert into erp.hpp_version_components(
      hpp_version_id,component_type,description,qty_basis,unit_cost,
      total_cost,source_type,source_id
    )
    select hv.id,'OTHER','HPP carried from source lot',v_take,
      v_source_hpp,v_take*v_source_hpp,'FG_LOT',r.id
    from erp.hpp_versions hv
    where hv.lot_id=v_dest_lot and hv.version_no=1;
    perform erp.post_fg_movement(
      h.from_product_id,r.id,h.location_id,'GRADE_A','REBRAND_OUT',-v_take,
      v_source_hpp,null,'PRODUCT_CONVERSION',h.id,h.physical_at,
      'SKU conversion OUT',false
    );
    perform erp.post_fg_movement(
      h.to_product_id,v_dest_lot,h.location_id,'GRADE_A','REBRAND_IN',v_take,
      v_dest_hpp,null,'PRODUCT_CONVERSION',h.id,h.physical_at,
      'SKU conversion IN',false
    );
    insert into erp.product_conversion_allocations(
      conversion_id,source_lot_id,destination_lot_id,qty_pcs,
      original_hpp_per_pcs,conversion_cost_allocated
    ) values(h.id,r.id,v_dest_lot,v_take,v_source_hpp,0);
    v_source_value:=v_source_value+(v_take*v_source_hpp);
    v_need:=v_need-v_take;
  end loop;
  if v_need>0 then
    raise exception 'Insufficient source stock for conversion; short % pcs',v_need;
  end if;

  update erp.product_conversions set status='POSTED' where id=h.id;
  if round(v_source_value,2)>0.005 then
    perform erp.post_journal(
      'PRODUCT_CONVERSION',h.id,(h.physical_at AT TIME ZONE 'Asia/Jakarta')::date,'SKU conversion/rebrand',
      jsonb_build_array(
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',
          round(v_source_value,2),'credit',0,'product_id',h.to_product_id),
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',
          round(v_source_value,2),'product_id',h.from_product_id)
      )
    );
  end if;

  for v_po in
    select distinct fl.po_id
    from erp.product_conversion_allocations a
    join erp.fg_lots fl on fl.id=a.source_lot_id
    where a.conversion_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.propagate_conversion_hpp_for_po(v_po);
    perform erp.refresh_po_hpp_gl_baseline(v_po);
    perform erp.assert_po_hpp_target_book_v2620e(v_po);
  end loop;
  if erp.be_nonpo_admitted_v1(h.id) then perform erp.be_nonpo_sync_all_v1(erp._cp3_business_date(h.physical_at),'PRODUCT_CONVERSION',h.id,'Konversi non-PO');end if;
end
$function$;
create or replace function erp.propagate_conversion_hpp_for_po(p_po_id uuid)
returns void
language plpgsql
security definer
set search_path to 'erp','public'
as $function$
declare
  r record;
  v_source_hpp numeric(18,6);
  v_desired numeric(18,6);
  v_current numeric(18,6);
  v_old_id uuid;
  v_new_id uuid;
  v_ver integer;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  perform 1 from erp.fg_lots
  where po_id=p_po_id and lot_origin in('PRODUCTION','CONVERSION')
  order by id for update;

  for r in
    with recursive rooted(lot_id,depth,path) as(
      select fl.id,0,array[fl.id]
      from erp.fg_lots fl
      where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION'
      union all
      select a.destination_lot_id,x.depth+1,x.path||a.destination_lot_id
      from rooted x
      join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
      join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
      where a.destination_lot_id is not null
        and not a.destination_lot_id=any(x.path)
        and x.depth<128
    )
    select a.*,x.depth source_depth
    from rooted x
    join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    where a.destination_lot_id is not null
    order by x.depth,a.id
  loop
    select hpp_per_pcs into v_source_hpp
    from erp.v_current_hpp where lot_id=r.source_lot_id;
    if v_source_hpp is null or r.qty_pcs<=0 then continue; end if;
    v_desired:=v_source_hpp+(erp.be_allocation_extra_v1(r.id)/r.qty_pcs);
    if v_desired<0 then raise exception 'BE_RECOVERY_EXCEEDS_VALUE: nilai pemulihan melebihi nilai sumber dan biaya sah';end if;
    select hpp_version_id,hpp_per_pcs into v_old_id,v_current
    from erp.v_current_hpp where lot_id=r.destination_lot_id;
    if v_old_id is null or abs(coalesce(v_current,0)-v_desired)>0.000001 then
      select coalesce(max(version_no),0)+1 into v_ver
      from erp.hpp_versions where lot_id=r.destination_lot_id;
      update erp.hpp_versions set is_current=false
      where lot_id=r.destination_lot_id and is_current;
      insert into erp.hpp_versions(
        lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,
        supersedes_id,calculation_reason,created_by
      ) values(
        r.destination_lot_id,v_ver,'ADJUSTED',r.qty_pcs,r.qty_pcs*v_desired,
        true,v_old_id,'Root-to-leaf propagated source HPP through SKU conversion',
        erp.current_app_user_id()
      ) returning id into v_new_id;
      insert into erp.hpp_version_components(
        hpp_version_id,component_type,description,qty_basis,unit_cost,total_cost,
        source_type,source_id
      ) values
        (v_new_id,'OTHER','Latest source lot HPP carry-forward',r.qty_pcs,
          v_source_hpp,r.qty_pcs*v_source_hpp,'FG_LOT',r.source_lot_id),
        (v_new_id,'CONVERSION','Conversion/relabel cost',r.qty_pcs,
          erp.be_allocation_extra_v1(r.id)/r.qty_pcs,erp.be_allocation_extra_v1(r.id),
          'PRODUCT_CONVERSION_ALLOCATION',r.id);
    end if;
  end loop;

  if exists(
    with recursive reachable(lot_id,path,depth) as(
      select fl.id,array[fl.id],0
      from erp.fg_lots fl
      where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION'
      union all
      select a.destination_lot_id,x.path||a.destination_lot_id,x.depth+1
      from reachable x
      join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
      join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
      where a.destination_lot_id is not null
        and not a.destination_lot_id=any(x.path) and x.depth<128
    )
    select 1
    from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    join erp.fg_lots s on s.id=a.source_lot_id and s.po_id=p_po_id
    join erp.fg_lots d on d.id=a.destination_lot_id
    where not exists(select 1 from reachable x where x.lot_id=a.destination_lot_id)
       or s.po_id is null or d.po_id is distinct from s.po_id
       or d.lot_origin<>'CONVERSION' or d.source_lot_id is distinct from s.id
       or a.qty_pcs<=0
  ) then
    raise exception 'CONVERSION_LINEAGE_ORPHAN_OR_CYCLE: PO % conversion graph is not rooted and acyclic',p_po_id;
  end if;
end
$function$;
create or replace function erp.compute_po_hpp_gl_targets_v2620d(p_po_id uuid)
returns table(
  base_output_qty integer,hpp_total_cost numeric,fg_value numeric,
  cogs_value numeric,other_out_value numeric
)
language sql
stable
security definer
set search_path=''
as $function$
with base as(
  select coalesce(sum(fl.initial_qty_pcs),0)::integer qty,
    (coalesce(sum(hv.total_cost),0)+erp.be_po_extra_v1(p_po_id))::numeric raw_total
  from erp.fg_lots fl
  left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current
  where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION'
), lot_hpp as(
  select fl.id lot_id,
    case when coalesce(hv.qty_basis_pcs,0)>0
      then hv.total_cost/hv.qty_basis_pcs else 0 end::numeric hpp_per_pcs
  from erp.fg_lots fl
  left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current
  where fl.po_id=p_po_id
    and fl.lot_origin in('PRODUCTION','CONVERSION')
), lot_balance as(
  select lh.lot_id,lh.hpp_per_pcs,
    (coalesce(sum(fm.qty_signed),0)+coalesce(sum(abs(fm.qty_signed)) filter(
      where fm.movement_type='SALE_RESERVE'
        and not exists(select 1 from erp.fg_stock_movements rv
          where rv.reversal_of_id=fm.id)
    ),0))::numeric owned_qty
  from lot_hpp lh
  left join erp.fg_stock_movements fm on fm.lot_id=lh.lot_id
  group by lh.lot_id,lh.hpp_per_pcs
), sold as(
  select a.lot_id,coalesce(sum(a.qty_pcs),0)::numeric qty
  from erp.sale_stock_allocations a
  join erp.sales_items i on i.id=a.sale_item_id
  join erp.sales_headers h on h.id=i.sale_id
  join erp.fg_lots fl on fl.id=a.lot_id
  where fl.po_id=p_po_id and h.status in('POSTED','PARTIAL_PAID','PAID')
  group by a.lot_id
), returned as(
  select i.lot_id,coalesce(sum(i.qty_pcs),0)::numeric qty
  from erp.sales_return_items i
  join erp.sales_returns h on h.id=i.return_id
  join erp.fg_lots fl on fl.id=i.lot_id
  where fl.po_id=p_po_id and h.status='POSTED'
  group by i.lot_id
), raw_values as(
  select b.qty,b.raw_total,
    coalesce(sum(greatest(lb.owned_qty,0)*lb.hpp_per_pcs),0)::numeric raw_owned,
    coalesce(sum(greatest(coalesce(s.qty,0)-coalesce(r.qty,0),0)
      *lb.hpp_per_pcs),0)::numeric raw_cogs
  from base b left join lot_balance lb on true
  left join sold s on s.lot_id=lb.lot_id
  left join returned r on r.lot_id=lb.lot_id
  group by b.qty,b.raw_total
), cents as(
  select qty,round(raw_total,2)::numeric hpp,
    round(raw_total-raw_owned,2)::numeric total_out,
    round(raw_cogs,2)::numeric cogs
  from raw_values
)
select qty,hpp,(hpp-total_out)::numeric,cogs,(total_out-cogs)::numeric
from cents
$function$;
CREATE OR REPLACE FUNCTION erp.bc_value_custody_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.bc_return_lots_v1%rowtype;s jsonb;v_policy jsonb;v_cond text:=upper(coalesce(p_payload->>'condition',''));v_qty numeric;v_unit numeric;
  v_to uuid;v_at timestamptz;v_adj uuid;v_event uuid;v_avg numeric;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['lot_id','condition','qty','unit_value','location_id','physical_at','reason'],
    array['lot_id','condition','qty','unit_value','location_id','physical_at','reason','responsible','reference'],'valuation payload');
  v_policy:=erp.bc_require_policy_v1('ACC_DEC03','nilai pemulihan barang bekas');
  l:=erp.bc_lock_lot_v1(erp.bc_uuid_v1(p_payload,'lot_id',true));
  if l.value_mode<>'PENDING' then raise exception 'BC_NOT_PENDING_VALUE: hanya barang perusahaan bernilai pending yang dapat dinilai';end if;
  if v_cond not in('USABLE','DAMAGED') then raise exception 'BC_CONDITION_INVALID: nilai hanya untuk barang yang sudah diperiksa (USABLE atau DAMAGED)';end if;
  v_qty:=erp.bc_parse_qty_v1(l.material_id,p_payload->'qty','qty');
  s:=erp.bc_lot_state_v1(l.id);
  if v_qty>(s->>lower(v_cond))::numeric then
    raise exception 'BC_QTY_EXCEEDS_BUCKET: % yang tersedia % , diminta %',v_cond,((s->>lower(v_cond))::numeric)::numeric(18,6),v_qty;end if;
  if jsonb_typeof(p_payload->'unit_value') is distinct from 'string' then raise exception 'BB_AMOUNT_INVALID: unit_value harus nominal tepat dua desimal';end if;
  v_unit:=erp.bb_parse_amount_v1(p_payload->>'unit_value','unit_value');
  if v_policy->>'unit_value_cap'='MOVING_AVERAGE' then
    select moving_average_cost into v_avg from erp.materials where id=l.material_id for update;
    if v_avg is null or v_avg<=0 or v_unit>v_avg then
      raise exception 'BC_VALUE_ABOVE_CAP: nilai pemulihan % melebihi rata-rata biaya barang baru %',v_unit,coalesce(v_avg,0)::numeric(18,6);end if;
  end if;
  v_to:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'location_id',true),case when v_cond='USABLE' then array['MAIN'] else array['DAMAGED'] end,
    case when v_cond='USABLE' then 'gudang untuk barang layak' else 'area rusak' end);
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  if v_at<l.received_at then raise exception 'BC_DATE_BEFORE_SOURCE: penilaian tidak boleh sebelum barang diterima';end if;
  perform erp.bc_new_document_v1(p_request,'VALUE_CUSTODY',v_at,p_payload,jsonb_build_object('ACC_DEC03',erp.bc_policy_version_v1('ACC_DEC03')));
  insert into erp.bc_lot_events_v1(document_id,lot_id,event_kind,condition,qty,event_at,target_location_id,unit_value,amount)
  values(p_request,l.id,'VALUE',v_cond,v_qty,v_at,v_to,v_unit,round(v_qty*v_unit,2)) returning id into v_event;
  v_adj:=erp.bc_post_adjustment_v1(p_request,v_to,v_at,'OTHER',jsonb_build_array(jsonb_build_object('material_id',l.material_id,
    'qty_signed',v_qty::text,'input_unit_cost',v_unit::text)),btrim(p_payload->>'reason'),'RECOVERY_VALUATION',(v_policy->>'credit_account_id')::uuid,'ACC_DEC03');
  perform erp.be_link_recovery_v1(p_request,l.id,erp._cp3_business_date(v_at));
  return jsonb_build_object('event_id',v_event,'adjustment_id',v_adj,'value',round(v_qty*v_unit,2)::text,'lot',erp.bc_lot_state_v1(l.id));
end;$function$;
CREATE OR REPLACE FUNCTION erp.bc_reverse_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare d erp.bc_documents_v1%rowtype;v_reason text;r record;v_lot uuid;v_event erp.bc_lot_events_v1%rowtype;v_item uuid;v_lots uuid[]:='{}';
  s jsonb;v_version bigint;v_payroll uuid;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['document_id','expected_version','reason'],array['document_id','expected_version','reason'],
    'reversal payload');
  v_reason:=erp.bc_text_v1(p_payload,'reason',true,1000);
  select * into d from erp.bc_documents_v1 where id=erp.bc_uuid_v1(p_payload,'document_id',true) for update;
  if d.id is null then raise exception 'BC_DOCUMENT_NOT_FOUND: dokumen tidak ditemukan';end if;
  if jsonb_typeof(p_payload->'expected_version') is distinct from 'string' or p_payload->>'expected_version' is distinct from d.row_version::text then
    raise exception 'STALE_VERSION: dokumen berubah; muat ulang';end if;
  if d.status<>'POSTED' then raise exception 'BC_ALREADY_REVERSED: dokumen sudah dibatalkan';end if;
  if d.action in('VALUE_CUSTODY') then perform erp.require_permission('finance.hpp.manage');end if;
  if d.action in('CREDIT_NOTE_RETURN','ROUND_NOTE') then perform erp.require_permission('finance.contractor_accessory.reverse');end if;
  if d.action='ALLOCATE_CARRY' then perform erp.require_permission('finance.payroll.approve');end if;
  -- Lots this document created or touched, locked in id order.
  for v_lot in select x from (select id x from erp.bc_return_lots_v1 where document_id=d.id union select lot_id from erp.bc_lot_events_v1 where document_id=d.id
      union select parent_lot_id from erp.bc_return_lots_v1 where document_id=d.id and parent_lot_id is not null) z order by x loop
    perform pg_advisory_xact_lock(hashtextextended('BCLOT|'||v_lot::text,0));
    v_lots:=v_lots||v_lot;
  end loop;
  -- Dependants first: a receipt whose lots have live events or credited children, an in-custody garment used by an internal
  -- use, a count whose variance was resolved, a credit whose carry is in a payroll or whose custody child has events.
  if exists(select 1 from erp.bc_return_lots_v1 l join erp.bc_lot_events_v1 e on e.lot_id=l.id join erp.bc_documents_v1 x on x.id=e.document_id
      where l.document_id=d.id and x.status='POSTED' and x.id<>d.id) then
    raise exception 'BC_REVERSE_DEPENDANTS: batalkan dahulu pemeriksaan, kredit atau penilaian atas penerimaan ini';end if;
  if d.action='CUSTOMER_GARMENT_IN' and (exists(select 1 from erp.bc_customer_custody_v1 c join erp.bc_documents_v1 x on x.id=c.out_document_id
        where c.in_document_id=d.id and x.status='POSTED')
      or exists(select 1 from erp.bc_internal_use_lines_v1 u join erp.bc_documents_v1 x on x.id=u.document_id where u.customer_custody_id=d.id and x.status='POSTED')) then
    raise exception 'BC_REVERSE_DEPENDANTS: titipan ini sudah dikembalikan atau dipakai pada pemakaian servis';end if;
  if d.action='COUNT_POST' and exists(select 1 from erp.bc_count_variances_v1 v join erp.bc_documents_v1 x on x.id=v.resolution_document_id
      where v.document_id=d.id and x.status='POSTED') then
    raise exception 'BC_REVERSE_DEPENDANTS: batalkan dahulu penyelesaian selisih hitung';end if;
  if d.action='CREDIT_NOTE_RETURN' then
    select * into v_event from erp.bc_lot_events_v1 where document_id=d.id;
    -- The carry lock of ALLOCATE_CARRY: a reversal and an allocation of the same credit never run at once.
    perform pg_advisory_xact_lock(hashtextextended('BCCARRY|'||v_event.id::text,0));
    if v_event.amount_carry>0 and erp.bc_carry_remaining_v1(v_event.id)<>v_event.amount_carry then
      raise exception 'BC_REVERSE_DEPENDANTS: lepaskan dahulu kredit yang sudah masuk payroll';end if;
  end if;

  update erp.bc_documents_v1 set status='REVERSED',reversed_at=clock_timestamp(),reversed_by=erp.current_app_user_id(),reversal_reason=v_reason,
    row_version=row_version+1 where id=d.id returning row_version into v_version;
  -- Native inverses in reverse creation order.
  for r in select l.link_kind,l.link_id from erp.bc_document_links_v1 l where l.document_id=d.id
      order by case l.link_kind when 'PAYROLL_LINE' then 1 when 'JOURNAL' then 2 when 'SETTLEMENT' then 3 when 'MOVEMENT' then 4 else 5 end,
        l.link_id desc loop
    if r.link_kind='TRANSFER' then
      perform erp.reverse_material_transfer_v2(r.link_id,v_reason,gen_random_uuid(),(select row_version from erp.material_transfers where id=r.link_id));
    elsif r.link_kind='ADJUSTMENT' then
      perform erp.reverse_material_adjustment_v2(r.link_id,v_reason,gen_random_uuid(),(select row_version from erp.material_adjustments where id=r.link_id));
    elsif r.link_kind='MOVEMENT' then
      perform erp.reverse_material_movement(r.link_id,v_reason);
      perform erp.recalculate_material_cost((select material_id from erp.material_stock_movements where id=r.link_id));
    elsif r.link_kind='JOURNAL' then
      perform erp._cp3_r4_reverse_journal_internal(r.link_id,v_reason);
    elsif r.link_kind='SETTLEMENT' then
      perform erp.reverse_opening_subledger_settlement(r.link_id,v_reason);
    elsif r.link_kind='PAYROLL_LINE' then
      select payroll_id into v_payroll from erp.payroll_reimbursements where id=r.link_id;
      delete from erp.payroll_reimbursements where id=r.link_id;
      perform erp.recalculate_payroll(v_payroll);
    end if;
  end loop;
  if d.action='CUSTOMER_GARMENT_OUT' then update erp.bc_customer_custody_v1 set out_document_id=null where out_document_id=d.id;end if;
  if d.action in('CREDIT_NOTE_RETURN','ROUND_NOTE') then
    for v_item in select coalesce(l.note_item_id,null) from erp.bc_lot_events_v1 e join erp.bc_return_lots_v1 l on l.id=e.lot_id where e.document_id=d.id and l.note_item_id is not null
      union select item_id from erp.bc_note_roundings_v1 where id=d.id loop
      if erp.bc_note_item_allocated_v1(v_item)>erp.bc_note_item_collectible_v1(v_item)+0.01 then
        raise exception 'BC_REVERSE_BELOW_PAID: potongan payroll melebihi tagihan sesudah pembatalan';end if;
      perform erp.refresh_contractor_issue_payroll_status(v_item);
    end loop;
  end if;
  -- Every lot keeps non-negative buckets.
  foreach v_lot in array v_lots loop
    s:=erp.bc_lot_state_v1(v_lot);
    if (s->>'waiting')::numeric<0 or (s->>'usable')::numeric<0 or (s->>'damaged')::numeric<0 then
      raise exception 'BC_REVERSE_DEPENDANTS: jumlah ini sudah dipakai dokumen sesudahnya; batalkan dokumen itu dahulu';end if;
  end loop;
  perform erp.be_reconcile_cost_document_v1(d.id,erp._cp3_business_date(current_timestamp));
  return jsonb_build_object('reversed_document_id',d.id,'row_version',v_version::text);
end;$function$;
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
  v_now numeric(24,2);
  v_posted numeric(24,2);
  v_drift numeric(24,2);
  v_prev_at timestamptz;
  v_prev_created timestamptz;
  v_prev_id uuid;
  v_first boolean;
  v_lowest uuid;
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
      and msm.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN','CONTRACTOR_MATERIAL_ISSUE_ITEM','MATERIAL_SUPPLIER_RETURN_ITEM','BC_NOTE_RETURN_CREDIT')
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
    elsif r.source_type='BC_NOTE_RETURN_CREDIT' then
      -- BC: a credited note return is revalued with its note line's issue, against the accessory recovery cost.
      select cmi.po_id,cmi.contractor_id into v_po,v_contractor from erp.bc_lot_events_v1 e join erp.bc_return_lots_v1 l on l.id=e.lot_id
        join erp.contractor_material_issue_items ii on ii.id=l.note_item_id join erp.contractor_material_issues cmi on cmi.id=ii.issue_id
        where e.id=r.source_id;
      v_counterpart:='ACCESSORY_RECOVERY_COGS';
    end if;

    if v_counterpart is null then continue; end if;

    if exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=r.id) then
      -- AZ rev2.1: revalued like the replay would value it, on its own day; its reversal takes it back (legs below).
      v_would:=case when r.qty_signed<0 then (select h.average_after from erp.material_cost_history h join erp.material_stock_movements hm on hm.id=h.movement_id
          where h.material_id=p_material_id and (hm.physical_at,hm.system_created_at,hm.id)<(r.physical_at,r.system_created_at,r.id)
          order by hm.physical_at desc,hm.system_created_at desc,hm.id desc limit 1)
        when r.source_type='BC_NOTE_RETURN_CREDIT' then (select x.unit_cost_snapshot from erp.material_stock_movements x
            where x.id=erp.bc_note_return_issue_movement_v1(r.source_id))
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
    elsif r.source_type='MATERIAL_SUPPLIER_RETURN_ITEM' then
      -- BA fix (T2 run 36087253697, CROSS:SUPPLIER_CENT:SPLIT_RETURN and CROSS_SOURCE_INVERSE_IDENTITY): a supplier return's
      -- inventory credit is set by the supplier cent state of its purchase lines (v2.6.20n, cumulative over the documents of
      -- the line), not by the return's own rounding; the whole-cent rule below would move those cents a second time. A
      -- supplier return keeps AZ's rule: only a change of its cost is revalued.
      v_target:=round((r.qty_signed*(r.unit_cost_snapshot-coalesce(r.original_unit_cost_snapshot,r.unit_cost_snapshot)))::numeric,2);
    else
      -- BA (audit A4, CP6-03): the recost is the movement's value now minus what was posted for it, both in whole cents. Value
      -- now: difference of the rounded stock value before and after it (material_cost_history), so the movements that
      -- empty the stock take exactly the rest and zero stock keeps zero value. Posted: cumulative rounding inside its
      -- posting document (same source and movement type; a cutting group posts one rounded total for its rolls).
      select round(h.stock_after*h.average_after,2)-round(h.stock_before*h.average_before,2) into v_now
      from erp.material_cost_history h where h.movement_id=r.id;
      select round(sum(abs(x.qty_signed)*coalesce(x.original_unit_cost_snapshot,x.unit_cost_snapshot)),2)
        -coalesce(round(sum(abs(x.qty_signed)*coalesce(x.original_unit_cost_snapshot,x.unit_cost_snapshot))
            filter(where (x.physical_at,x.system_created_at,x.id)<(r.physical_at,r.system_created_at,r.id)),2),0)
        into v_posted
      from erp.material_stock_movements x
      where x.material_id=r.material_id and x.source_type=r.source_type and x.source_id=r.source_id
        and x.movement_type=r.movement_type and x.reversal_of_id is null
        and (x.physical_at,x.system_created_at,x.id)<=(r.physical_at,r.system_created_at,r.id);
      -- BA W8 (independent audit round 9, CP6-03 with several receipts; M:835, M:3820, M:6632): a purchase document's
      -- inventory is round(sum of qty x unit cost) per document (supplier cent state, v2.6.20n), while the moving
      -- average added the change of round(stock x average). The difference for the documents received since the previous
      -- consumption goes with the next consumption, so the consumptions total the documents' own cents and a used-up
      -- material keeps zero value. A document with several materials gives its document-level cent to the lowest
      -- material id among its items. Returns to the supplier keep their own rule above; opening stock keeps its line basis.
      if v_now is not null and r.qty_signed<0 then
        select coalesce(sum(d.doc_value-d.average_value),0) into v_drift
        from (
          -- the receipt's own input cost (what the moving average took in): a cost correction sets it before it recosts,
          -- while the corrected price counts in material_purchase_current_unit_cost only once the correction is POSTED
          select x.purchase_id,
            round(sum(x.qty_signed*x.input_unit_cost),2)
            +case when (select min(pi.material_id::text) from erp.material_purchase_items pi where pi.purchase_id=x.purchase_id)=r.material_id::text
              then (select round(sum(t.v),2)-sum(round(t.v,2)) from (select sum(pm.qty_signed*pm.input_unit_cost) v
                    from erp.material_stock_movements pm
                    join erp.material_purchase_items ppi on ppi.id=case when pm.source_type='MATERIAL_PURCHASE_ITEM' then pm.source_id
                      else (select mr.purchase_item_id from erp.material_rolls mr where mr.id=pm.source_id) end
                    where ppi.purchase_id=x.purchase_id and pm.movement_type='PURCHASE' and pm.qty_signed>0
                      and pm.source_type in('MATERIAL_PURCHASE_ITEM','MATERIAL_PURCHASE_ROLL')
                      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=pm.id)
                    group by pm.material_id) t)
              else 0 end doc_value,
            sum(x.average_change) average_value
          from (
            select pi.purchase_id,m.qty_signed,m.input_unit_cost,
              round(h.stock_after*h.average_after,2)-round(h.stock_before*h.average_before,2) average_change
            from erp.material_stock_movements m
            join erp.material_purchase_items pi on pi.id=case when m.source_type='MATERIAL_PURCHASE_ITEM' then m.source_id
              else (select mr.purchase_item_id from erp.material_rolls mr where mr.id=m.source_id) end
            join erp.material_cost_history h on h.movement_id=m.id
            where m.material_id=r.material_id and m.movement_type='PURCHASE' and m.qty_signed>0
              and m.source_type in('MATERIAL_PURCHASE_ITEM','MATERIAL_PURCHASE_ROLL')
              and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
              and (m.physical_at,m.system_created_at,m.id)<(r.physical_at,r.system_created_at,r.id)
              and (v_prev_id is null or (m.physical_at,m.system_created_at,m.id)>(v_prev_at,v_prev_created,v_prev_id))
          ) x group by x.purchase_id
        ) d;
        v_now:=v_now-v_drift;
        v_prev_at:=r.physical_at;v_prev_created:=r.system_created_at;v_prev_id:=r.id;
      end if;
      v_target:=case when v_now is null then round((r.qty_signed*(r.unit_cost_snapshot-coalesce(r.original_unit_cost_snapshot,r.unit_cost_snapshot)))::numeric,2)
        else v_now-sign(r.qty_signed)*v_posted end;
    end if;

    -- AZ rev2.1: the movement, then each of its reversals with the opposite target on the reversal's own day.
    for q in select r.id mid,r.physical_at pat,v_target tgt
             union all select rv.id,rv.physical_at,-v_target from erp.material_stock_movements rv where rv.reversal_of_id=r.id
    loop
    select s.applied_inventory_delta into v_old
    from erp.material_cost_revaluation_state s where s.movement_id=q.mid for update;
    v_first:=not found;
    v_old:=coalesce(v_old,0);
    v_diff:=round(q.tgt-v_old,2);

    if abs(v_diff)>0.005 then
      v_date:=case when v_closed then v_e
        when v_first and erp.invoice_recost_economic_date_v1() is null and not exists(select 1 from erp.accounting_period_control c
            where c.singleton_id=1 and c.closed_through is not null and erp._cp3_business_date(q.pat)<=c.closed_through)
          then least(erp._cp3_business_date(q.pat),erp._cp3_business_date(statement_timestamp()))
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
  -- AZ rev2.1: a reversed write-off (outbound item of a material adjustment, a pocket-fabric usage included: its reversal
  -- is only possible while no pocket period covers it, so it is then a plain write-off against OTHER_EXPENSE; GPT audit of
  -- 737649b, AB-01) left at its posting cost while the stock it came from is revalued, and the adjustment document's own cumulative
  -- revaluation (erp._cp6_sync_material_adjustment_revaluation) targets it to zero once reversed. Between the adjustment
  -- day and the reversal day the write-off carries the replayed cost: +I against the write-off account on its day, -I on the
  -- reversal's day (event and state on the reversal movement, outside the document's own book). Both legs on one day: kept.
  for r in select msm.*,rv.id rv_id,rv.physical_at rv_at,i.adjustment_id adj_id
      from erp.material_stock_movements msm join erp.material_adjustment_items i on i.id=msm.source_id
      join erp.material_stock_movements rv on rv.reversal_of_id=msm.id
    where msm.material_id=p_material_id and msm.source_type='MATERIAL_ADJUSTMENT_ITEM' and msm.reversal_of_id is null
      and msm.qty_signed<0
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
            jsonb_build_object('account_id',erp.bc_adjustment_account_v1(r.adj_id,'OTHER_EXPENSE'),'debit',0,'credit',q.amt))
          else jsonb_build_array(
            jsonb_build_object('account_id',erp.bc_adjustment_account_v1(r.adj_id,'OTHER_EXPENSE'),'debit',abs(q.amt),'credit',0),
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
  for v_lowest in
    select distinct (select min(o.material_id::text) from erp.material_purchase_items o where o.purchase_id=pi.purchase_id)::uuid
    from erp.material_purchase_items pi where pi.material_id=p_material_id
  loop
    if v_lowest::text<p_material_id::text then perform erp.sync_material_cost_revaluation(v_lowest); end if;
  end loop;
  perform erp.be_sync_material_cost_v1(p_material_id);
end;
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
      -- BD (LAU-DEC06 PRODUCT_COST): the invoiced difference to the released estimate is product cost of the PO.
      +coalesce((select sum(l.product_variance) from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id
        where i.status='POSTED' and l.receipt_line_id is not null and l.po_id=s.po_id),0)
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
      -coalesce((select sum(e.target_amount-e.previous_amount) from erp.bb_wip_split_value_events_v1 e join erp.bb_wip_bs_splits_v1 x on x.id=e.split_id join erp.initial_import_production_sources ps on ps.opening_item_id=x.opening_item_id where ps.po_id=s.po_id),0)
      +coalesce((select sum(erp.pocket_period_amount_v1(d.pool_id,d.preceding_qty,d.sewing_qty)) from erp.pocket_period_destinations d where d.event_id is not null and d.po_id=s.po_id),0)
      +erp.be_po_extra_v1(s.po_id)+erp.be_redye_po_cost_v1(s.po_id)
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
    or abs(ch.total_cost-erp.be_pocket_opening_extra_v1(oi.id)-fl.initial_qty_pcs
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
    'Every posted conversion has an admitted source, exact OUT/IN facts, rooted lineage and current HPP equal to source plus linked cost less recovery'
  from erp.product_conversion_allocations a
  join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
  join erp.fg_lots s on s.id=a.source_lot_id
  left join erp.fg_lots d on d.id=a.destination_lot_id
  left join erp.v_current_hpp sh on sh.lot_id=s.id
  left join erp.v_current_hpp dh on dh.lot_id=d.id
  where (s.po_id is null and not erp.be_nonpo_admitted_v1(c.id)) or d.id is null or d.po_id is distinct from s.po_id
     or d.lot_origin<>'CONVERSION' or d.source_lot_id is distinct from s.id
     or d.initial_qty_pcs is distinct from a.qty_pcs or a.qty_pcs<=0
     or sh.hpp_per_pcs is null or dh.hpp_per_pcs is null
     or abs(dh.hpp_per_pcs-(sh.hpp_per_pcs
       +erp.be_allocation_extra_v1(a.id)/nullif(a.qty_pcs,0)))>0.000001
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
 where ai_snapshot.id is null or ai_po.id is null or (ai_group.id is null and not erp.bb_opening_work_source_v1(ai_event.bb_opening_item_id,ai_event.po_id))
   or ai_snapshot.po_id is distinct from ai_event.po_id
   or ai_snapshot.work_component_id is distinct from ai_line.work_component_id
   or ai_snapshot.rate_per_pcs_snapshot is distinct from ai_line.rate_snapshot
   or (ai_group.id is not null and ai_group.po_id is distinct from ai_event.po_id)
   or ai_po.contractor_id is distinct from ai_event.contractor_id
 union all
 select ai_event.id from erp.work_completion_events ai_event
 where ai_event.status='POSTED' and not exists(select 1 from erp.work_completion_lines ai_line where ai_line.completion_id=ai_event.id)
) ai_broken),'Posted work must retain the selected PO, contractor, component and committed rate snapshot'::text;
end
$function$;
create or replace function erp.be_propagate_nonpo_v1()
returns void
language plpgsql
security definer
set search_path to 'erp','public'
as $function$
declare
  r record;
  v_source_hpp numeric(18,6);
  v_desired numeric(18,6);
  v_current numeric(18,6);
  v_old_id uuid;
  v_new_id uuid;
  v_ver integer;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  perform 1 from erp.fg_lots
  where po_id is null and lot_origin<>'VOIDED_PRODUCTION'
  order by id for update;

  for r in
    with recursive rooted(lot_id,depth,path) as(
      select fl.id,0,array[fl.id]
      from erp.fg_lots fl
      where fl.po_id is null and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
      union all
      select a.destination_lot_id,x.depth+1,x.path||a.destination_lot_id
      from rooted x
      join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
      join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
      where a.destination_lot_id is not null
        and not a.destination_lot_id=any(x.path)
        and x.depth<128
    )
    select a.*,x.depth source_depth
    from rooted x
    join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    where a.destination_lot_id is not null
    order by x.depth,a.id
  loop
    select hpp_per_pcs into v_source_hpp
    from erp.v_current_hpp where lot_id=r.source_lot_id;
    if v_source_hpp is null or r.qty_pcs<=0 then continue; end if;
    v_desired:=v_source_hpp+(erp.be_allocation_extra_v1(r.id)/r.qty_pcs);
    if v_desired<0 then raise exception 'BE_RECOVERY_EXCEEDS_VALUE: nilai pemulihan melebihi nilai sumber dan biaya sah';end if;
    select hpp_version_id,hpp_per_pcs into v_old_id,v_current
    from erp.v_current_hpp where lot_id=r.destination_lot_id;
    if v_old_id is null or abs(coalesce(v_current,0)-v_desired)>0.000001 then
      select coalesce(max(version_no),0)+1 into v_ver
      from erp.hpp_versions where lot_id=r.destination_lot_id;
      update erp.hpp_versions set is_current=false
      where lot_id=r.destination_lot_id and is_current;
      insert into erp.hpp_versions(
        lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,
        supersedes_id,calculation_reason,created_by
      ) values(
        r.destination_lot_id,v_ver,'ADJUSTED',r.qty_pcs,r.qty_pcs*v_desired,
        true,v_old_id,'Root-to-leaf propagated source HPP through SKU conversion',
        erp.current_app_user_id()
      ) returning id into v_new_id;
      insert into erp.hpp_version_components(
        hpp_version_id,component_type,description,qty_basis,unit_cost,total_cost,
        source_type,source_id
      ) values
        (v_new_id,'OTHER','Latest source lot HPP carry-forward',r.qty_pcs,
          v_source_hpp,r.qty_pcs*v_source_hpp,'FG_LOT',r.source_lot_id),
        (v_new_id,'CONVERSION','Conversion/relabel cost',r.qty_pcs,
          erp.be_allocation_extra_v1(r.id)/r.qty_pcs,erp.be_allocation_extra_v1(r.id),
          'PRODUCT_CONVERSION_ALLOCATION',r.id);
    end if;
  end loop;

  if exists(
    with recursive reachable(lot_id,path,depth) as(
      select fl.id,array[fl.id],0
      from erp.fg_lots fl
      where fl.po_id is null and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
      union all
      select a.destination_lot_id,x.path||a.destination_lot_id,x.depth+1
      from reachable x
      join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
      join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
      where a.destination_lot_id is not null
        and not a.destination_lot_id=any(x.path) and x.depth<128
    )
    select 1
    from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    join erp.fg_lots s on s.id=a.source_lot_id and s.po_id is null
    join erp.fg_lots d on d.id=a.destination_lot_id
    where not exists(select 1 from reachable x where x.lot_id=a.destination_lot_id)
       or not erp.be_nonpo_admitted_v1(c.id) or d.po_id is distinct from s.po_id
       or d.lot_origin<>'CONVERSION' or d.source_lot_id is distinct from s.id
       or a.qty_pcs<=0
  ) then
    raise exception 'BE_NON_PO_LINEAGE_ORPHAN_OR_CYCLE';
  end if;
end
$function$;
CREATE OR REPLACE FUNCTION erp.compute_non_po_product_hpp_targets_v2620f(p_product_id uuid)
returns table(
  hpp_total_cost numeric,fg_value numeric,cogs_value numeric,
  other_out_value numeric
)
language sql
stable
security definer
set search_path=''
as $function$
with lots as(
  select fl.id,
    (case when fl.lot_origin<>'CONVERSION' or exists(select 1 from erp.product_conversion_allocations a join erp.product_conversions c on c.id=a.conversion_id
       where a.destination_lot_id=fl.id and c.status='POSTED') then coalesce(hv.total_cost,0) else 0 end
     -coalesce((select sum(a.qty_pcs*(hv.total_cost/nullif(hv.qty_basis_pcs,0))) from erp.product_conversion_allocations a
       join erp.product_conversions c on c.id=a.conversion_id where a.source_lot_id=fl.id and c.status='POSTED'),0))::numeric raw_total,
    case when coalesce(hv.qty_basis_pcs,0)>0
      then hv.total_cost/hv.qty_basis_pcs else 0 end::numeric hpp_per_pcs
  from erp.fg_lots fl
  left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current
  where fl.product_id=p_product_id and fl.po_id is null
    and fl.lot_origin<>'VOIDED_PRODUCTION'
), balances as(
  select l.id,l.raw_total,l.hpp_per_pcs,
    (coalesce(sum(m.qty_signed),0)+coalesce(sum(abs(m.qty_signed)) filter(
      where m.movement_type='SALE_RESERVE' and not exists(
        select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id
      )),0))::numeric owned_qty
  from lots l
  left join erp.fg_stock_movements m on m.lot_id=l.id
  group by l.id,l.raw_total,l.hpp_per_pcs
), sold as(
  select a.lot_id,coalesce(sum(a.qty_pcs),0)::numeric qty
  from erp.sale_stock_allocations a
  join erp.sales_items i on i.id=a.sale_item_id
  join erp.sales_headers h on h.id=i.sale_id
  join lots l on l.id=a.lot_id
  where h.status in('POSTED','PARTIAL_PAID','PAID')
  group by a.lot_id
), returned as(
  select i.lot_id,coalesce(sum(i.qty_pcs),0)::numeric qty
  from erp.sales_return_items i
  join erp.sales_returns h on h.id=i.return_id
  join lots l on l.id=i.lot_id
  where h.status='POSTED'
  group by i.lot_id
), per_lot as(
  select b.id,round(b.raw_total,2)::numeric hpp,
    round(b.raw_total-greatest(b.owned_qty,0)*b.hpp_per_pcs,2)::numeric total_out,
    round(greatest(coalesce(s.qty,0)-coalesce(r.qty,0),0)
      *b.hpp_per_pcs,2)::numeric cogs
  from balances b
  left join sold s on s.lot_id=b.id
  left join returned r on r.lot_id=b.id
)
select coalesce(sum(hpp),0)::numeric,
  coalesce(sum(hpp-total_out),0)::numeric,
  coalesce(sum(cogs),0)::numeric,
  coalesce(sum(total_out-cogs),0)::numeric
from per_lot
$function$;
CREATE OR REPLACE FUNCTION erp.compute_non_po_product_hpp_book_v2620f(p_product_id uuid)
returns table(
  hpp_total_cost numeric,fg_value numeric,cogs_value numeric,
  other_out_value numeric
)
language sql
stable
security definer
set search_path=''
as $function$
with book as(
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
  left join erp.journal_entries o on o.id=e.reversal_of_id
  where l.po_id is null and l.product_id=p_product_id

)
select (fg+cogs+other_out)::numeric,fg,cogs,other_out from book
$function$;
CREATE OR REPLACE FUNCTION erp.assert_non_po_product_hpp_target_book_v2620f(
  p_product_id uuid
)
returns void
language plpgsql
stable
security definer
set search_path to 'erp','public'
as $function$
declare
  t record;
  b record;
begin
  perform erp.require_internal();
  if exists(
    select 1
    from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    join erp.fg_lots s on s.id=a.source_lot_id
    join erp.fg_lots d on d.id=a.destination_lot_id
    where(s.po_id is null or d.po_id is null) and not erp.be_nonpo_admitted_v1(c.id)
      and(s.product_id=p_product_id or d.product_id=p_product_id)
  ) then
    raise exception 'NON_PO_CONVERSION_REQUIRES_SOURCED_HPP_WORKFLOW';
  end if;
  select * into t
  from erp.compute_non_po_product_hpp_targets_v2620f(p_product_id);
  select * into b
  from erp.compute_non_po_product_hpp_book_v2620f(p_product_id);
  if abs(t.hpp_total_cost-b.hpp_total_cost)>0.005
     or abs(t.fg_value-b.fg_value)>0.005
     or abs(t.cogs_value-b.cogs_value)>0.005
     or abs(t.other_out_value-b.other_out_value)>0.005 then
    raise exception 'NON_PO_HPP_TARGET_BOOK_MISMATCH: product %, target hpp/fg/cogs/other %/%/%/%, book %/%/%/%',
      p_product_id,t.hpp_total_cost,t.fg_value,t.cogs_value,t.other_out_value,
      b.hpp_total_cost,b.fg_value,b.cogs_value,b.other_out_value;
  end if;
end
$function$;
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
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  if nullif(btrim(p_trigger_source_type),'') is null
     or nullif(btrim(p_reason),'') is null then
    raise exception 'Non-PO HPP synchronization requires source and reason';
  end if;
  if not erp.be_nonpo_in_sync_v1() and exists(select 1 from erp.be_conversion_sources_v1 be_source
      join erp.fg_lots be_lot on be_lot.id=be_source.source_lot_id where be_lot.po_id is null) then
    perform erp.be_nonpo_sync_all_v1(p_effective_date,p_trigger_source_type,p_trigger_source_id,p_reason);return;
  end if;
  if exists(
    select 1
    from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    join erp.fg_lots s on s.id=a.source_lot_id
    join erp.fg_lots d on d.id=a.destination_lot_id
    where(s.po_id is null or d.po_id is null) and not erp.be_nonpo_admitted_v1(c.id)
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
CREATE OR REPLACE FUNCTION erp.reverse_product_conversion(p_conversion_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.product_conversions%rowtype;
  r record;
  v_journal uuid;
  v_expected numeric(24,6);
  v_po uuid;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal conversion/rebrand wajib diisi'; end if;
  select * into h from erp.product_conversions where id=p_conversion_id for update;
  if h.id is null then raise exception 'Conversion/rebrand tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya conversion/rebrand POSTED yang dapat direverse'; end if;

  if exists(
    select 1
    from erp.product_conversion_allocations a
    where a.conversion_id=h.id
      and erp.fg_lot_has_active_downstream(a.destination_lot_id,'REBRAND_IN','PRODUCT_CONVERSION',h.id)
  ) then raise exception 'Hasil conversion/rebrand masih dipakai transaksi downstream aktif. Reverse transaksi downstream terlebih dahulu.'; end if;

  select coalesce(sum(a.qty_pcs*a.original_hpp_per_pcs),0) into v_expected from erp.product_conversion_allocations a where a.conversion_id=h.id;
  select id into v_journal from erp.journal_entries where source_type='PRODUCT_CONVERSION' and source_id=h.id and status='POSTED' order by posting_at desc,id desc limit 1;
  if v_expected>0.005 and v_journal is null then raise exception 'Jurnal conversion/rebrand tidak ditemukan; reversal dibatalkan agar nilai persediaan tidak rusak'; end if;

  for r in
    select fm.id from erp.fg_stock_movements fm
    join erp.product_conversion_allocations a on a.destination_lot_id=fm.lot_id
    where a.conversion_id=h.id and fm.movement_type='REBRAND_IN' and fm.source_type='PRODUCT_CONVERSION' and fm.source_id=h.id
      and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id)
    order by fm.physical_at desc,fm.id desc
  loop perform erp.reverse_fg_movement(r.id,p_reason); end loop;

  for r in
    select fm.id from erp.fg_stock_movements fm
    join erp.product_conversion_allocations a on a.source_lot_id=fm.lot_id
    where a.conversion_id=h.id and fm.movement_type='REBRAND_OUT' and fm.source_type='PRODUCT_CONVERSION' and fm.source_id=h.id
      and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id)
    order by fm.physical_at desc,fm.id desc
  loop perform erp.reverse_fg_movement(r.id,p_reason); end loop;

  for r in select e.journal_id from erp.be_nonpo_transfer_events_v1 e join erp.journal_entries j on j.id=e.journal_id
    where e.conversion_id=h.id and j.status='POSTED' order by e.created_at desc,e.id desc loop
    perform erp.reverse_journal(r.journal_id,p_reason);
  end loop;
  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
  update erp.product_conversions set status='REVERSED' where id=h.id;

  for v_po in
    select distinct fl.po_id from erp.product_conversion_allocations a join erp.fg_lots fl on fl.id=a.source_lot_id where a.conversion_id=h.id and fl.po_id is not null
  loop perform erp.sync_po_hpp_to_gl(v_po,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date); end loop;

  if erp.be_nonpo_admitted_v1(h.id) then perform erp.be_nonpo_sync_all_v1(erp._cp3_business_date(current_timestamp),'PRODUCT_CONVERSION_REVERSE',h.id,p_reason);end if;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason) values('product_conversions',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;
CREATE OR REPLACE FUNCTION erp.post_rework_completion(p_rework_order_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  r erp.rework_orders%rowtype;
  b erp.bs_cases%rowtype;
  v_total numeric(20,2):=0;
  v_location uuid;
  v_location_count integer:=0;
  v_lot uuid;
  v_lot_number text;
  v_hpp numeric(18,6):=0;
  v_remaining integer:=0;
  v_completed_at timestamptz;
begin
  perform erp.require_internal();
  select * into r from erp.rework_orders where id=p_rework_order_id for update;
  if r.id is null then raise exception 'Rework order not found'; end if;
  if r.status<>'COMPLETED' then raise exception 'Rework must be COMPLETED before posting'; end if;
  if r.qty_good_returned+r.qty_bs_returned<>r.qty_sent then
    raise exception 'Rework completion must reconcile exactly: GOOD + BS must equal qty sent';
  end if;
  if r.cost_posted then return; end if;
  if not exists(
    select 1 from erp.rework_accessory_decisions d where d.rework_order_id=r.id
  ) then raise exception 'Rework accessory decision lineage is missing'; end if;
  select * into b from erp.bs_cases where id=r.bs_case_id for update;
  if b.id is null then raise exception 'BS case not found'; end if;
  v_completed_at:=coalesce(r.completed_at,clock_timestamp());

  if r.qty_good_returned>0 then
    if b.po_id is null or b.product_id is null then
      raise exception 'GOOD rework return requires native production PO and product lineage';
    end if;
    perform erp.assert_product_identity_time(b.product_id,v_completed_at,'EXISTING_STOCK');
    if r.return_fg_location_id is not null then
      select id into v_location from erp.locations
      where id=r.return_fg_location_id and is_active and location_type='FG_WAREHOUSE';
      if v_location is null then
        raise exception 'Selected rework return location must be an active FG warehouse';
      end if;
    else
      select count(*),(array_agg(id order by id))[1]
      into v_location_count,v_location
      from erp.locations where is_active and location_type='FG_WAREHOUSE';
      if v_location_count<>1 then
        raise exception 'Select return FG warehouse for rework GOOD output; active FG warehouse count is %',v_location_count;
      end if;
    end if;
    v_lot_number:='RW-'||r.rework_number||'-'||substr(r.id::text,1,8);
    insert into erp.fg_lots(
      lot_number,po_id,qc_item_id,cutting_group_id,product_id,
      initial_qty_pcs,cached_qty_pcs,produced_at,is_open,lot_origin
    ) values(
      -- qc_item_id identifies the single original QC output. Recovery is
      -- identified by rework_orders.good_fg_lot_id -> bs_cases -> source QC.
      v_lot_number,b.po_id,null,b.cutting_group_id,b.product_id,
      r.qty_good_returned,0,v_completed_at,true,'PRODUCTION'
    ) returning id into v_lot;
    perform erp.post_fg_movement(
      b.product_id,v_lot,v_location,'GRADE_A','REWORK_IN',r.qty_good_returned,
      0,null,'REWORK_ORDER',r.id,v_completed_at,'GOOD returned from rework',false
    );
    -- Link the lot before snapshotting so the immutable selection, including
    -- an explicit empty selection, is the only source the snapshotter can use.
    update erp.rework_orders
    set good_fg_lot_id=v_lot,return_fg_location_id=v_location,completed_at=v_completed_at
    where id=r.id;
    perform erp.ensure_fg_accessory_cost_snapshot(v_lot);
    perform erp.post_accessory_reimbursement_accrual(v_lot);
    insert into erp.bs_resolutions(
      bs_case_id,resolution_type,qty_pcs,compensation_amount,
      responsible_contractor_id,responsible_vendor_id,
      source_rework_order_id,physical_at,notes
    ) values(
      b.id,case when r.destination_type='CONTRACTOR'
        then 'REWORK_SEWING' else 'REWORK_LAUNDRY' end,
      r.qty_good_returned,0,r.contractor_id,r.vendor_id,r.id,v_completed_at,
      'Recovered to GOOD FG from rework'
    );
  else
    update erp.rework_orders set completed_at=v_completed_at where id=r.id;
  end if;

  select greatest(b.qty_pcs-coalesce(sum(br.qty_pcs),0),0)::integer
  into v_remaining from erp.bs_resolutions br where br.bs_case_id=b.id;
  update erp.bs_cases
  set status=case when v_remaining=0 then 'RESOLVED' else 'PARTIAL' end,
      updated_at=clock_timestamp()
  where id=b.id;
  if r.destination_type='CONTRACTOR' then
    select coalesce(sum(amount_payable),0) into v_total
    from erp.rework_component_lines where rework_order_id=r.id;
    if v_total>0 then
      perform erp.post_journal(
        'REWORK_COMPLETION',r.id,(v_completed_at AT TIME ZONE 'Asia/Jakarta')::date,'Rework labor completion',
        jsonb_build_array(
          jsonb_build_object(
            'mapping_key','WIP','debit',round(v_total,2),'credit',0,
            'contractor_id',r.contractor_id,'po_id',b.po_id
          ),
          jsonb_build_object(
            'mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',round(v_total,2),
            'contractor_id',r.contractor_id,'po_id',b.po_id
          )
        )
      );
    end if;
  end if;
  update erp.rework_orders set cost_posted=true where id=r.id;
  if b.po_id is not null and exists(select 1 from erp.fg_lots where po_id=b.po_id) then
    perform erp.rebuild_po_hpp(b.po_id,'Rework completion posted with physical GOOD return');
    perform erp.propagate_conversion_hpp_for_po(b.po_id);
    perform erp.sync_po_hpp_to_gl(b.po_id,(v_completed_at AT TIME ZONE 'Asia/Jakarta')::date);
    if v_lot is not null then
      select coalesce(hpp_per_pcs,0) into v_hpp
      from erp.v_current_hpp where lot_id=v_lot;
      update erp.fg_stock_movements set unit_hpp_snapshot=v_hpp
      where lot_id=v_lot and movement_type='REWORK_IN'
        and source_type='REWORK_ORDER' and source_id=r.id;
    end if;
  end if;
  perform erp.be_complete_rework_target_v1(r.id);
end
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

  perform erp.be_reverse_rework_target_v1(r.id,p_reason);
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
CREATE OR REPLACE FUNCTION erp.assert_new_stock_cutoff_coverage_v1()
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO ''
AS $function$
declare
  v_registry jsonb:='{"erp.accessory_bom_versions.product_id":{"class":"MASTER","reason":"Effective-dated accessory BOM; no stock instant"},"erp.bs_cases.product_id":{"class":"NEW_STOCK_FACT","reason":"physical_at of QC/laundry BS and manual OUT_OF_NOWHERE BS"},"erp.contractor_accessory_reimbursement_entitlements.product_id":{"class":"DERIVED","reason":"Accounting entitlement of an FG lot"},"erp.fg_accessory_cost_snapshots.product_id":{"class":"DERIVED","reason":"Cost snapshot of an FG lot"},"erp.fg_adjustment_items.product_id":{"class":"MOVEMENT","reason":"Adjusts an existing lot"},"erp.fg_inventory_balances.product_id":{"class":"DERIVED","reason":"Balance cache keyed by product/location/grade"},"erp.fg_lots.product_id":{"class":"NEW_STOCK_FACT","reason":"produced_at of every lot except GOOD returned by rework"},"erp.fg_stock_movements.product_id":{"class":"MOVEMENT","reason":"Movement of an existing lot"},"erp.bb_opening_sale_return_rights_v1.product_id":{"class":"SOURCE_DOCUMENT","reason":"Return right of an old invoice; the stock fact is the RETURN lot in fg_lots, validated as NEW_STOCK at receipt"},"erp.bb_opening_sale_return_receipts_v1.product_id":{"class":"DERIVED","reason":"Provenance of a return receipt; the stock fact is its fg_lots lot"},"erp.bb_wip_bs_splits_v1.product_id":{"class":"DERIVED","reason":"Provenance of an opening WIP BS split; the stock fact is its bs_cases row (NEW_STOCK_FACT at its physical_at)"},"erp.bb_open_sales_draft_lines_v1.product_id":{"class":"DERIVED","reason":"Provenance of a sales draft open at cutover; the sale is its native sales_items line (reservation of existing stock)"},"erp.be_pocket_sewing_v1.product_id":{"class":"SOURCE_DOCUMENT","reason":"Evidence of a sold SKU before cutover; no new stock identity is created"},"erp.be_rework_targets_v1.target_product_id":{"class":"SOURCE_DOCUMENT","reason":"Requested rework/redye target; checked as NEW_STOCK when the native GOOD lot is converted atomically"},"erp.bc_customer_custody_v1.product_id":{"class":"SOURCE_DOCUMENT","reason":"A customer-owned garment in service (ACC-C10); never company stock, no stock fact"},"erp.initial_import_wip_output_identity_v1.opening_product_id":{"class":"DERIVED","reason":"Provenance of an opening WIP output: the product filled in on its opening item"},"erp.initial_import_wip_output_identity_v1.output_product_id":{"class":"DERIVED","reason":"Provenance of an opening WIP output; the stock fact is its fg_lots lot"},"erp.journal_lines.product_id":{"class":"ACCOUNTING","reason":"Journal dimension"},"erp.laundry_receipt_batch_size_lines.bs_product_id":{"class":"SOURCE_DOCUMENT","reason":"Laundry receipt input; the BS fact is bs_cases"},"erp.laundry_receipt_bs_product_allocations.product_id":{"class":"SOURCE_DOCUMENT","reason":"Validated as NEW_STOCK; the BS fact is bs_cases"},"erp.non_po_hpp_gl_sync_events_v2620f.product_id":{"class":"ACCOUNTING","reason":"HPP to GL synchronisation event"},"erp.opening_balance_items.product_id":{"class":"SOURCE_DOCUMENT","reason":"Opening document; facts are OPENING lots and LEGACY BS"},"erp.po_accessory_bom_commitments.product_id":{"class":"MASTER","reason":"PO accessory BOM commitment"},"erp.product_conversions.from_product_id":{"class":"SOURCE_DOCUMENT","reason":"Conversion source, validated as EXISTING_STOCK"},"erp.product_conversions.to_product_id":{"class":"SOURCE_DOCUMENT","reason":"Conversion target; the fact is the CONVERSION lot in fg_lots"},"erp.product_identity_mutation_context_v1.product_id":{"class":"AUTHORIZATION","reason":"Private one-use identity edit context"},"erp.product_price_versions.product_id":{"class":"MASTER","reason":"Effective-dated price"},"erp.qc_inspection_items.final_product_id":{"class":"SOURCE_DOCUMENT","reason":"QC input; the facts are fg_lots and bs_cases"},"erp.sales_items.product_id":{"class":"SALES","reason":"Sale of existing stock"},"erp.sales_return_items.product_id":{"class":"SALES","reason":"Return of sold stock"},"erp.stock_explainability_snapshots.product_id":{"class":"REPORT","reason":"Stock explanation snapshot"},"erp.stock_policy_versions.product_id":{"class":"MASTER","reason":"Effective-dated stock policy"}}';
  v_helper_tables text[]:=array['bs_case_manual_origins_v1','bs_cases','fg_lots','rework_orders'];
  v_actual text[];
  v_unclassified text[];
  v_stale text[];
  v_facts text[];
  v_helper text[];
begin
  -- Structural catalog read: any FK to erp.products in any schema, plus any
  -- product-named uuid column in erp/public that no FK protects.
  select array_agg(distinct ref order by ref) into v_actual from (
    select format('%s.%s.%s',n.nspname,c.relname,a.attname) ref
    from pg_constraint fk join pg_class c on c.oid=fk.conrelid
    join pg_namespace n on n.oid=c.relnamespace
    join pg_attribute a on a.attrelid=c.oid and a.attnum=any(fk.conkey)
    where fk.contype='f' and fk.confrelid='erp.products'::regclass and fk.conrelid<>'erp.products'::regclass
    union
    select format('%s.%s.%s',n.nspname,c.relname,a.attname)
    from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace
    where n.nspname in('erp','public') and c.relkind in('r','p') and c.oid<>'erp.products'::regclass
      and a.attnum>0 and not a.attisdropped and a.atttypid='uuid'::regtype
      and (a.attname='product_id' or a.attname like '%\_product\_id')
  ) r;
  select array_agg(k order by k) into v_unclassified from unnest(v_actual) k where not v_registry ? k;
  if v_unclassified is not null then
    raise exception 'NEW_STOCK_CUTOFF_REFERENCE_UNCLASSIFIED: %',array_to_string(v_unclassified,', ');
  end if;
  select array_agg(k order by k) into v_stale from jsonb_object_keys(v_registry) k where k<>all(v_actual);
  if v_stale is not null then
    raise exception 'NEW_STOCK_CUTOFF_REGISTRY_STALE: %',array_to_string(v_stale,', ');
  end if;
  select array_agg(distinct split_part(key,'.',2) order by split_part(key,'.',2)) into v_facts
  from jsonb_each(v_registry) where value->>'class'='NEW_STOCK_FACT';
  select array_agg(distinct m[1] order by m[1]) into v_helper
  from pg_proc p cross join lateral regexp_matches(lower(p.prosrc),'erp\.([a-z0-9_]+)','g') m
  where p.oid='erp.latest_new_stock_physical_at_v1(uuid)'::regprocedure;
  if v_helper is null or not (v_helper @> v_helper_tables and v_helper <@ v_helper_tables and v_helper @> v_facts) then
    raise exception 'NEW_STOCK_CUTOFF_HELPER_SCOPE_DRIFT: %',v_helper;
  end if;
  if lower((select p.prosrc from pg_proc p where p.oid='erp.edit_product_identity_effective(uuid,text,uuid,uuid,text,uuid,text,timestamp with time zone,text)'::regprocedure))
     !~ 'erp\.latest_new_stock_physical_at_v1\s*\(' then
    raise exception 'NEW_STOCK_CUTOFF_CONSUMER_DRIFT';
  end if;
  return jsonb_build_object('references',coalesce(array_length(v_actual,1),0),'new_stock_fact_tables',v_facts,'registry',v_registry);
end;
$function$;
CREATE OR REPLACE FUNCTION erp.bd_save_invoice_draft_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_id uuid;i erp.bd_laundry_invoices_v1%rowtype;v_vendor uuid;v_x jsonb;v_no integer:=0;v_rl record;v_kind text;v_qty integer;v_amount numeric;
  v_rounding numeric;v_open erp.bd_opening_laundry_uninvoiced_v1%rowtype;v_total numeric;v_corrects uuid;v_has_bill boolean;v_has_corr boolean;
  v_redye erp.be_redye_services_v1%rowtype;v_origins uuid[];o erp.bd_laundry_invoices_v1%rowtype;v_discount numeric;v_tax numeric;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['vendor_id','invoice_number','invoice_date','header_total','lines'],
    array['invoice_id','expected_version','vendor_id','invoice_number','invoice_date','due_date','header_total','discount_amount','tax_amount',
      'rounding_amount','notes','lines','corrects_invoice_id'],'laundry invoice draft');
  v_id:=erp.bd_uuid_v1(p_payload,'invoice_id',false);v_vendor:=erp.bd_uuid_v1(p_payload,'vendor_id',true);
  if not exists(select 1 from erp.laundry_vendors where id=v_vendor) then raise exception 'BD_VENDOR_INACTIVE: vendor laundry tidak dikenal';end if;
  if jsonb_typeof(p_payload->'invoice_date') is distinct from 'string' or p_payload->>'invoice_date'!~'^\d{4}-\d{2}-\d{2}$' then
    raise exception 'BD_FIELD_INVALID: invoice_date wajib tanggal YYYY-MM-DD';end if;
  if p_payload ? 'due_date' and jsonb_typeof(p_payload->'due_date')<>'null' and (jsonb_typeof(p_payload->'due_date')<>'string' or p_payload->>'due_date'!~'^\d{4}-\d{2}-\d{2}$') then
    raise exception 'BD_FIELD_INVALID: due_date wajib tanggal YYYY-MM-DD';end if;
  if jsonb_typeof(p_payload->'lines') is distinct from 'array' or jsonb_array_length(p_payload->'lines') not between 1 and 200 then
    raise exception 'BD_INVOICE_LINES: invoice memuat 1-200 baris';end if;
  v_rounding:=0;
  if p_payload ? 'rounding_amount' and jsonb_typeof(p_payload->'rounding_amount')<>'null' then
    if jsonb_typeof(p_payload->'rounding_amount')<>'string' or p_payload->>'rounding_amount'!~'^-?(0|[1-9][0-9]{0,2})\.[0-9]{2}$' then
      raise exception 'BD_AMOUNT_INVALID: rounding_amount wajib nominal teks bertanda dengan tepat dua desimal, kurang dari 1000';end if;
    v_rounding:=(p_payload->>'rounding_amount')::numeric;
  end if;
  v_discount:=case when p_payload ? 'discount_amount' and jsonb_typeof(p_payload->'discount_amount')<>'null' then erp.bd_amount_v1(p_payload->'discount_amount','discount_amount',false) else 0 end;
  v_tax:=case when p_payload ? 'tax_amount' and jsonb_typeof(p_payload->'tax_amount')<>'null' then erp.bd_amount_v1(p_payload->'tax_amount','tax_amount',false) else 0 end;
  -- Invoice or correction document (owner decision no. 13): correction lines never share a document with billing lines.
  select bool_or(x->>'line_kind'='BILL'),bool_or(x->>'line_kind'='CORRECTION') into v_has_bill,v_has_corr from jsonb_array_elements(p_payload->'lines') x;
  v_corrects:=erp.bd_uuid_v1(p_payload,'corrects_invoice_id',false);
  if coalesce(v_has_bill,false) and (coalesce(v_has_corr,false) or v_corrects is not null) then
    raise exception 'BD_CORRECTION_SEPARATE_DOCUMENT: koreksi dibuat sebagai dokumen koreksi tersendiri yang tertaut ke invoice asal; pisahkan dari baris tagih';end if;
  if coalesce(v_has_corr,false) then
    if v_corrects is null then
      select array_agg(distinct y.id) into v_origins from jsonb_array_elements(p_payload->'lines') x
        join erp.bd_laundry_invoice_lines_v1 b on b.line_kind='BILL' and (b.receipt_line_id=erp.bd_uuid_v1(x,'receipt_line_id',false)
          or b.opening_uninvoiced_id=erp.bd_uuid_v1(x,'opening_uninvoiced_id',false) or b.rework_service_id=erp.bd_uuid_v1(x,'rework_service_id',false))
        join erp.bd_laundry_invoices_v1 y on y.id=b.invoice_id and y.status='POSTED' and y.corrects_invoice_id is null;
      if coalesce(cardinality(v_origins),0)<>1 then
        raise exception 'BD_CORRECTION_ORIGIN_REQUIRED: pilih invoice asal yang dikoreksi (sumber ini ditagih % invoice)',coalesce(cardinality(v_origins),0);end if;
      v_corrects:=v_origins[1];
    end if;
    select * into o from erp.bd_laundry_invoices_v1 where id=v_corrects;
    if o.id is null or o.status<>'POSTED' or o.corrects_invoice_id is not null then
      raise exception 'BD_CORRECTION_ORIGIN_INVALID: invoice asal harus invoice vendor laundry POSTED (bukan dokumen koreksi)';end if;
    if o.vendor_id<>v_vendor then raise exception 'BD_INVOICE_VENDOR: invoice asal milik vendor lain';end if;
    if v_discount<>0 or v_tax<>0 or v_rounding<>0 then
      raise exception 'BD_CORRECTION_NO_DISCOUNT_TAX: dokumen koreksi tidak memuat diskon, pajak, atau pembulatan; nominal koreksi sudah bersih';end if;
    if jsonb_typeof(p_payload->'header_total') is distinct from 'string' or p_payload->>'header_total'!~'^-?(0|[1-9][0-9]{0,15})\.[0-9]{2}$' then
      raise exception 'BD_AMOUNT_INVALID: header_total wajib nominal teks bertanda dengan tepat dua desimal';end if;
    v_total:=(p_payload->>'header_total')::numeric;
    if v_total=0 then raise exception 'BD_AMOUNT_INVALID: total dokumen koreksi tidak boleh nol';end if;
  else
    v_total:=erp.bd_amount_v1(p_payload->'header_total','header_total',true);
  end if;
  if v_id is null then
    insert into erp.bd_laundry_invoices_v1(vendor_id,invoice_number,invoice_date,due_date,status,header_total,corrects_invoice_id,discount_amount,tax_amount,rounding_amount,notes,created_by)
    values(v_vendor,btrim(p_payload->>'invoice_number'),(p_payload->>'invoice_date')::date,(p_payload->>'due_date')::date,'DRAFT',v_total,v_corrects,
      v_discount,v_tax,v_rounding,nullif(btrim(coalesce(p_payload->>'notes','')),''),erp.current_app_user_id()) returning * into i;
  else
    select * into i from erp.bd_laundry_invoices_v1 where id=v_id for update;
    if i.id is null or i.status<>'DRAFT' then raise exception 'BD_INVOICE_NOT_DRAFT: hanya draf invoice yang dapat diubah';end if;
    if jsonb_typeof(p_payload->'expected_version') is distinct from 'string' or p_payload->>'expected_version' is distinct from i.row_version::text then
      raise exception 'STALE_VERSION: draf invoice berubah; muat ulang';end if;
    update erp.bd_laundry_invoices_v1 set vendor_id=v_vendor,invoice_number=btrim(p_payload->>'invoice_number'),invoice_date=(p_payload->>'invoice_date')::date,
      due_date=(p_payload->>'due_date')::date,header_total=v_total,corrects_invoice_id=v_corrects,discount_amount=v_discount,tax_amount=v_tax,
      rounding_amount=v_rounding,notes=nullif(btrim(coalesce(p_payload->>'notes','')),''),row_version=row_version+1
    where id=i.id returning * into i;
    delete from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id;
  end if;
  for v_x in select value from jsonb_array_elements(p_payload->'lines') loop
    v_no:=v_no+1;
    perform erp._cp3_assert_closed_json_object(v_x,array['line_kind','category','qty','amount'],
      array['line_kind','receipt_line_id','opening_uninvoiced_id','rework_service_id','category','qty','amount','note'],'invoice line');
    if (v_x ? 'receipt_line_id')::int+(v_x ? 'opening_uninvoiced_id')::int+(v_x ? 'rework_service_id')::int<>1 then
      raise exception 'BD_INVOICE_SOURCE: setiap baris menunjuk satu sumber, baris penerimaan (receipt_line_id) atau penerimaan saldo awal (opening_uninvoiced_id)';end if;
    v_kind:=v_x->>'line_kind';
    if v_kind not in('BILL','CORRECTION') then raise exception 'BD_INVOICE_LINE_KIND: BILL atau CORRECTION';end if;
    if v_x->>'category' not in('GOOD','BS','FAILED_ATTEMPT') then raise exception 'BD_INVOICE_CATEGORY: GOOD, BS atau FAILED_ATTEMPT';end if;
    if jsonb_typeof(v_x->'qty') is distinct from 'number' or v_x->>'qty'!~'^(0|[1-9][0-9]{0,8})$' then raise exception 'BD_QTY_INVALID: qty wajib bilangan bulat >= 0';end if;
    v_qty:=(v_x->>'qty')::integer;
    if jsonb_typeof(v_x->'amount') is distinct from 'string' or v_x->>'amount'!~'^-?(0|[1-9][0-9]{0,15})\.[0-9]{2}$' then
      raise exception 'BD_AMOUNT_INVALID: amount wajib nominal teks dengan tepat dua desimal';end if;
    v_amount:=(v_x->>'amount')::numeric;
    if v_kind='BILL' and (v_qty<=0 or v_amount<0) then raise exception 'BD_INVOICE_LINE: baris tagih wajib qty > 0 dan nominal >= 0';end if;
    if v_kind='CORRECTION' and (v_qty<>0 or v_amount=0) then raise exception 'BD_INVOICE_LINE: baris koreksi wajib qty 0 dan nominal tidak nol';end if;
    if v_kind='CORRECTION' and sign(v_amount)<>sign(v_total) then
      raise exception 'BD_CORRECTION_MIXED_SIGN: satu dokumen koreksi hanya menaikkan atau hanya menurunkan tagihan';end if;
    if v_x ? 'rework_service_id' then
      select * into v_redye from erp.be_redye_services_v1 where id=erp.bd_uuid_v1(v_x,'rework_service_id',true);
      if v_redye.id is null then raise exception 'BD_INVOICE_SOURCE: jasa celup ulang tidak ditemukan';end if;
      if v_redye.vendor_id<>v_vendor then raise exception 'BD_INVOICE_VENDOR';end if;
      insert into erp.bd_laundry_invoice_lines_v1(invoice_id,line_no,line_kind,rework_service_id,category,qty,amount,note,po_id)
      values(i.id,v_no,v_kind,v_redye.id,v_x->>'category',v_qty,v_amount,nullif(btrim(coalesce(v_x->>'note','')),''),v_redye.po_id);
      continue;
    end if;
    if v_x ? 'opening_uninvoiced_id' then
      select * into v_open from erp.bd_opening_laundry_uninvoiced_v1 where id=erp.bd_uuid_v1(v_x,'opening_uninvoiced_id',true);
      if v_open.id is null then raise exception 'BD_INVOICE_SOURCE: penerimaan laundry saldo awal tidak ditemukan';end if;
      if v_open.vendor_id<>v_vendor then raise exception 'BD_INVOICE_VENDOR: penerimaan saldo awal milik vendor lain';end if;
      if v_open.category<>v_x->>'category' then raise exception 'BD_INVOICE_CATEGORY: penerimaan saldo awal ini berkategori %',v_open.category;end if;
      insert into erp.bd_laundry_invoice_lines_v1(invoice_id,line_no,line_kind,opening_uninvoiced_id,category,qty,amount,note,po_id)
      values(i.id,v_no,v_kind,v_open.id,v_x->>'category',v_qty,v_amount,nullif(btrim(coalesce(v_x->>'note','')),''),v_open.po_id);
      continue;
    end if;
    select rl.id,d.vendor_id,d.po_id,r.status into v_rl from erp.laundry_receipt_lines rl join erp.laundry_receipts r on r.id=rl.receipt_id
      join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id join erp.laundry_deliveries d on d.id=dl.delivery_id
      where rl.id=erp.bd_uuid_v1(v_x,'receipt_line_id',true);
    if v_rl.id is null or v_rl.status<>'POSTED' then raise exception 'BD_INVOICE_SOURCE: sumber tagihan wajib baris penerimaan laundry POSTED';end if;
    if v_rl.vendor_id<>v_vendor then raise exception 'BD_INVOICE_VENDOR: baris penerimaan milik vendor lain';end if;
    insert into erp.bd_laundry_invoice_lines_v1(invoice_id,line_no,line_kind,receipt_line_id,category,qty,amount,note,po_id)
    values(i.id,v_no,v_kind,v_rl.id,v_x->>'category',v_qty,v_amount,nullif(btrim(coalesce(v_x->>'note','')),''),v_rl.po_id);
  end loop;
  if v_corrects is not null then perform erp.bd_check_correction_sources_v1(i.id);end if;
  return erp.bd_invoice_json_v1(i.id);
end;$function$;
CREATE OR REPLACE FUNCTION erp.bd_check_correction_sources_v1(p_invoice uuid)
 RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare i erp.bd_laundry_invoices_v1%rowtype;
begin
  select * into i from erp.bd_laundry_invoices_v1 where id=p_invoice;
  if exists(select 1 from erp.bd_laundry_invoice_lines_v1 l where l.invoice_id=i.id and (l.line_kind<>'CORRECTION' or not exists(
      select 1 from erp.bd_laundry_invoice_lines_v1 b where b.invoice_id=i.corrects_invoice_id and b.line_kind='BILL'
        and (b.receipt_line_id=l.receipt_line_id or b.opening_uninvoiced_id=l.opening_uninvoiced_id or b.rework_service_id=l.rework_service_id)))) then
    raise exception 'BD_CORRECTION_SOURCE_NOT_IN_ORIGIN: dokumen koreksi hanya mengoreksi sumber yang ditagih invoice asalnya';end if;
end;$function$;
CREATE OR REPLACE FUNCTION erp.bd_invoice_lines_json_v1(p_invoice uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(jsonb_agg(jsonb_build_object('id',l.id,'line_no',l.line_no,'line_kind',l.line_kind,'receipt_line_id',l.receipt_line_id,
    'opening_uninvoiced_id',l.opening_uninvoiced_id,'rework_service_id',l.rework_service_id,
    'category',l.category,'qty',l.qty,'amount',l.amount::text,'note',l.note,'po_id',l.po_id,'discount_share',l.discount_share::text,
    'rounding_share',l.rounding_share::text,'net_amount',l.net_amount::text,'released_estimate',l.released_estimate::text,
    'variance',l.variance::text,'product_variance',l.product_variance::text,'completes_source',l.completes_source) order by l.line_no),'[]'::jsonb)
  from erp.bd_laundry_invoice_lines_v1 l where l.invoice_id=p_invoice
$function$;
CREATE OR REPLACE FUNCTION erp.bd_post_invoice_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare i erp.bd_laundry_invoices_v1%rowtype;l record;v_dec02 jsonb;v_dec03 jsonb;v_dec06 jsonb;v_versions jsonb:='{}'::jsonb;v_billable jsonb;
  v_gross numeric:=0;v_positive numeric:=0;v_payable numeric;v_weights integer[]:='{}';v_ids uuid[]:='{}';v_split numeric[];k integer;v_last uuid;
  v_pool numeric;v_pieces integer;v_prior numeric;v_released numeric;v_complete boolean;v_cap integer;v_billed integer;v_paid boolean;
  v_lines jsonb:='[]'::jsonb;v_po record;v_journal uuid;v_group uuid;v_line_ids uuid[];v_net numeric;v_open_rel numeric;v_open_var numeric;
  o erp.bd_laundry_invoices_v1%rowtype;v_source_net numeric;v_ap numeric;v_origin_left numeric;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['invoice_id','expected_version'],array['invoice_id','expected_version'],'post invoice');
  select * into i from erp.bd_laundry_invoices_v1 where id=erp.bd_uuid_v1(p_payload,'invoice_id',true) for update;
  if i.id is null or i.status<>'DRAFT' then raise exception 'BD_INVOICE_NOT_DRAFT: hanya draf invoice yang dapat diposting';end if;
  if p_payload->>'expected_version' is distinct from i.row_version::text then raise exception 'STALE_VERSION: draf invoice berubah; muat ulang';end if;
  if i.invoice_date>(statement_timestamp() at time zone 'Asia/Jakarta')::date then
    raise exception 'BD_INVOICE_FUTURE_DATE: tanggal invoice vendor laundry berada di masa depan';end if;
  if exists(select 1 from erp.bd_laundry_invoices_v1 x where x.vendor_id=i.vendor_id and lower(btrim(x.invoice_number))=lower(btrim(i.invoice_number))
      and x.status='POSTED') or exists(select 1 from erp.vendor_invoices v where v.vendor_id=i.vendor_id
      and lower(btrim(v.invoice_number))=lower(btrim(i.invoice_number)) and v.status in('POSTED','PARTIAL_PAID','PAID')) then
    raise exception 'BD_INVOICE_DUPLICATE_NUMBER: nomor invoice vendor ini sudah diposting';end if;
  -- Owner settings (fail closed): billable categories, variance treatment, and discount/tax/rounding when used.
  v_dec02:=erp.bd_require_policy_v1('LAU_DEC02','dasar qty yang ditagih vendor laundry');v_billable:=v_dec02->'billable';
  v_dec06:=erp.bd_require_policy_v1('LAU_DEC06','perlakuan selisih invoice laundry');
  v_versions:=jsonb_build_object('LAU_DEC02',erp.bd_policy_version_v1('LAU_DEC02'),'LAU_DEC06',erp.bd_policy_version_v1('LAU_DEC06'));
  if i.discount_amount>0 or i.tax_amount>0 or i.rounding_amount<>0 then
    v_dec03:=erp.bd_require_policy_v1('LAU_DEC03','diskon, pajak atau pembulatan invoice laundry');
    v_versions:=v_versions||jsonb_build_object('LAU_DEC03',erp.bd_policy_version_v1('LAU_DEC03'));
    if i.discount_amount>0 and v_dec03->>'discount'<>'ALLOWED' then raise exception 'BD_DISCOUNT_REFUSED: LAU-DEC03 tidak mengizinkan diskon invoice laundry';end if;
    if i.rounding_amount<>0 and v_dec03->>'rounding'<>'LAST_LINE' then raise exception 'BD_ROUNDING_REFUSED: LAU-DEC03 tidak mengizinkan baris pembulatan';end if;
    if i.tax_amount>0 and v_dec03->>'tax_account_id' is null then raise exception 'BD_TAX_ACCOUNT_REQUIRED: LAU-DEC03 belum menetapkan akun pajak masukan';end if;
  end if;
  if not exists(select 1 from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id) then raise exception 'BD_INVOICE_LINES: invoice tanpa baris';end if;
  -- A correction document (owner decision no. 13) corrects one posted invoice of the same vendor, on or after its date, only in
  -- the sources that invoice billed; the origin row is locked so it cannot be reversed meanwhile.
  if i.corrects_invoice_id is null then
    if exists(select 1 from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id and line_kind='CORRECTION') then
      raise exception 'BD_CORRECTION_SEPARATE_DOCUMENT: koreksi dibuat sebagai dokumen koreksi tersendiri yang tertaut ke invoice asal';end if;
  else
    select * into o from erp.bd_laundry_invoices_v1 where id=i.corrects_invoice_id for update;
    if o.status<>'POSTED' or o.corrects_invoice_id is not null or o.vendor_id<>i.vendor_id then
      raise exception 'BD_CORRECTION_ORIGIN_INVALID: invoice asal harus invoice vendor laundry POSTED milik vendor yang sama';end if;
    if i.invoice_date<o.invoice_date then
      raise exception 'BD_CORRECTION_BEFORE_ORIGIN: tanggal dokumen koreksi % sebelum tanggal invoice asal %',i.invoice_date,o.invoice_date;end if;
    perform erp.bd_check_correction_sources_v1(i.id);
    if exists(select 1 from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id and sign(amount)<>sign(i.header_total)) then
      raise exception 'BD_CORRECTION_MIXED_SIGN: satu dokumen koreksi hanya menaikkan atau hanya menurunkan tagihan';end if;
  end if;
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  perform 1 from erp.be_redye_services_v1 where id in(select rework_service_id from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id) order by id for update;
  -- Lock the sources in a fixed order (with the baseline's per-cutting-group flow lock) before reading capacity and estimates.
  for v_group in select distinct dl.cutting_group_id from erp.bd_laundry_invoice_lines_v1 x join erp.laundry_receipt_lines rl on rl.id=x.receipt_line_id
      join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id where x.invoice_id=i.id order by 1 loop
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group::text,0));
  end loop;
  select array_agg(distinct x.receipt_line_id order by x.receipt_line_id) into v_line_ids from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id;
  perform 1 from erp.laundry_receipt_lines where id=any(v_line_ids) order by id for update;
  perform 1 from erp.bd_opening_laundry_uninvoiced_v1 where id in(select x.opening_uninvoiced_id from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id)
    order by id for update;
  -- Discount spread over the billed amounts (largest remainder on cents); rounding on the last billing line.
  for l in select * from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id order by line_no loop
    v_gross:=v_gross+l.amount;
    if l.line_kind='BILL' then v_ids:=v_ids||l.id;v_weights:=v_weights||round(l.amount*100)::integer;v_positive:=v_positive+l.amount;v_last:=l.id;end if;
  end loop;
  if i.discount_amount>v_positive then raise exception 'BD_DISCOUNT_EXCEEDS_LINES: diskon melebihi nilai baris tagih';end if;
  update erp.bd_laundry_invoice_lines_v1 set discount_share=0,rounding_share=0 where invoice_id=i.id;
  if i.discount_amount>0 then
    if v_positive<=0 then raise exception 'BD_DISCOUNT_EXCEEDS_LINES: diskon tanpa baris tagih bernilai';end if;
    v_split:=erp.bd_split_amount_v1(i.discount_amount,v_weights);
    for k in 1..array_length(v_ids,1) loop update erp.bd_laundry_invoice_lines_v1 set discount_share=v_split[k] where id=v_ids[k];end loop;
  end if;
  if i.rounding_amount<>0 then
    if v_last is null then raise exception 'BD_ROUNDING_REFUSED: pembulatan memerlukan baris tagih';end if;
    update erp.bd_laundry_invoice_lines_v1 set rounding_share=i.rounding_amount where id=v_last;
  end if;
  v_payable:=v_gross-i.discount_amount+i.rounding_amount+i.tax_amount;
  if v_payable<>i.header_total then
    raise exception 'BD_INVOICE_TOTAL_MISMATCH: total invoice % tidak sama dengan baris - diskon + pembulatan + pajak = %',i.header_total,v_payable;end if;
  if (i.corrects_invoice_id is null and i.header_total<=0) or i.header_total=0 then
    raise exception 'BD_INVOICE_TOTAL_MISMATCH: total invoice harus lebih dari 0 (dokumen koreksi: tidak nol)';end if;
  -- Each line in order: category billable, capacity, released estimate, variance.
  for l in select x.*,rl.actual_cost,rl.actual_cost_status,rl.delivery_line_id,u.accrued_amount opening_pool,u.qty opening_qty
      from erp.bd_laundry_invoice_lines_v1 x left join erp.laundry_receipt_lines rl on rl.id=x.receipt_line_id
      left join erp.bd_opening_laundry_uninvoiced_v1 u on u.id=x.opening_uninvoiced_id where x.invoice_id=i.id order by x.line_no loop
    if l.rework_service_id is not null then perform erp.be_invoice_redye_line_v1(l.id,v_billable,v_dec06);continue;end if;
    -- ALL-W05: an opening record of work returned before cutover releases its opening accrual (none while its estimate is
    -- unknown); the difference is not a PO's product cost, so it needs the owner's LAU-DEC06 variance account.
    if l.opening_uninvoiced_id is not null then
      if not v_billable @> to_jsonb(l.category) then
        raise exception 'BD_CATEGORY_NOT_BILLABLE: LAU-DEC02 tidak menetapkan % sebagai qty yang ditagih',l.category;end if;
      v_pool:=l.opening_pool;
      v_prior:=erp.bd_opening_released_v1(l.opening_uninvoiced_id)+coalesce((select sum(x.released_estimate) from erp.bd_laundry_invoice_lines_v1 x
        where x.invoice_id=i.id and x.opening_uninvoiced_id=l.opening_uninvoiced_id and x.line_no<l.line_no),0);
      if l.line_kind='BILL' then
        v_billed:=erp.bd_opening_billed_v1(l.opening_uninvoiced_id)+coalesce((select sum(x.qty) from erp.bd_laundry_invoice_lines_v1 x
          where x.invoice_id=i.id and x.opening_uninvoiced_id=l.opening_uninvoiced_id and x.line_kind='BILL' and x.line_no<l.line_no),0);
        if v_billed+l.qty>l.opening_qty then
          raise exception 'BD_INVOICE_CAPACITY: % % sudah ditagih dari % yang tersedia pada penerimaan saldo awal ini; diminta %',v_billed,l.category,l.opening_qty,l.qty;end if;
        v_complete:=v_billed+l.qty>=l.opening_qty;
        if v_complete then v_released:=v_pool-v_prior;
        else v_released:=least(round(v_pool*l.qty/l.opening_qty,2),v_pool-v_prior);end if;
      else
        if not exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id
            where x.opening_uninvoiced_id=l.opening_uninvoiced_id and x.line_kind='BILL' and (y.status='POSTED' or (y.id=i.id and x.line_no<l.line_no))) then
          raise exception 'BD_CORRECTION_WITHOUT_BILL: koreksi hanya untuk sumber yang sudah ditagih';end if;
        select exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id
            join erp.vendor_payments p on p.vendor_invoice_id=y.id and p.status='POSTED'
            where x.opening_uninvoiced_id=l.opening_uninvoiced_id and y.status='POSTED') into v_paid;
        if v_paid and v_dec06->>'after_payment'<>'CORRECTION_DOCUMENT' then
          raise exception 'BD_PAID_CORRECTION_REFUSED: invoice sumber sudah dibayar dan LAU-DEC06 tidak mengizinkan dokumen koreksi';end if;
        select coalesce(sum(x.net_amount),0) into v_source_net from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id
          where y.status='POSTED' and x.opening_uninvoiced_id=l.opening_uninvoiced_id;
        v_source_net:=v_source_net+(select coalesce(sum(x.amount),0) from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id
          and x.opening_uninvoiced_id=l.opening_uninvoiced_id and x.line_no<=l.line_no);
        if v_source_net<0 then raise exception 'BD_CORRECTION_BELOW_ZERO: koreksi membuat biaya tertagih sumber ini negatif (%)',v_source_net;end if;
        v_released:=0;v_complete:=false;
      end if;
      if v_released<0 then raise exception 'BD_INTERNAL: estimasi yang dilepas negatif';end if;
      v_net:=l.amount-l.discount_share+l.rounding_share;
      if v_net-v_released<>0 and v_dec06->>'variance_mode'<>'VARIANCE_ACCOUNT' then
        raise exception 'BD_OPENING_VARIANCE_NEEDS_ACCOUNT: selisih % pada penerimaan laundry saldo awal bukan biaya produk PO; LAU-DEC06 harus memakai akun selisih (VARIANCE_ACCOUNT)',v_net-v_released;end if;
      update erp.bd_laundry_invoice_lines_v1 x set net_amount=v_net,released_estimate=v_released,variance=v_net-v_released,product_variance=0,
        completes_source=v_complete where x.id=l.id;
      continue;
    end if;
    if l.actual_cost_status<>'ESTIMATED' or l.actual_cost is null then
      raise exception 'BD_INVOICE_SOURCE_NOT_ESTIMATED: baris penerimaan belum berbiaya estimasi atau sudah final (status %)',l.actual_cost_status;end if;
    if not erp.bd_line_complete_v1(l.delivery_line_id) then
      raise exception 'BD_PRICE_UNKNOWN_SET_FIRST: harga komponen kiriman ini belum diketahui; isi harganya sebelum menagih';end if;
    if not v_billable @> to_jsonb(l.category) then
      raise exception 'BD_CATEGORY_NOT_BILLABLE: LAU-DEC02 tidak menetapkan % sebagai qty yang ditagih',l.category;end if;
    -- Posted invoices plus the earlier lines of this invoice (the invoice is still DRAFT here).
    v_pool:=l.actual_cost;v_pieces:=erp.bd_invoice_pieces_v1(l.receipt_line_id);
    v_prior:=erp.bd_released_estimate_v1(l.receipt_line_id)+coalesce((select sum(x.released_estimate) from erp.bd_laundry_invoice_lines_v1 x
      where x.invoice_id=i.id and x.receipt_line_id=l.receipt_line_id and x.line_no<l.line_no),0);
    if l.line_kind='BILL' then
      v_cap:=erp.bd_invoice_capacity_v1(l.receipt_line_id,l.category);
      v_billed:=erp.bd_invoice_billed_v1(l.receipt_line_id,l.category)+coalesce((select sum(x.qty) from erp.bd_laundry_invoice_lines_v1 x
        where x.invoice_id=i.id and x.receipt_line_id=l.receipt_line_id and x.category=l.category and x.line_kind='BILL' and x.line_no<l.line_no),0);
      if v_billed+l.qty>v_cap then
        raise exception 'BD_INVOICE_CAPACITY: % % sudah ditagih dari % yang tersedia pada baris penerimaan ini; diminta %',v_billed,l.category,v_cap,l.qty;end if;
      -- Complete when every billable category of the source is billed up to its capacity with this line.
      select bool_and(erp.bd_invoice_billed_v1(l.receipt_line_id,c)+coalesce((select sum(x.qty) from erp.bd_laundry_invoice_lines_v1 x
          where x.invoice_id=i.id and x.receipt_line_id=l.receipt_line_id and x.category=c and x.line_kind='BILL' and x.line_no<=l.line_no),0)
          >=erp.bd_invoice_capacity_v1(l.receipt_line_id,c))
        into v_complete from jsonb_array_elements_text(v_billable) c;
      if v_complete then v_released:=v_pool-v_prior;
      else v_released:=least(round(v_pool*l.qty/nullif(v_pieces,0),2),v_pool-v_prior);end if;
    else
      if not exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id
          where x.receipt_line_id=l.receipt_line_id and x.line_kind='BILL' and (y.status='POSTED' or (y.id=i.id and x.line_no<l.line_no))) then
        raise exception 'BD_CORRECTION_WITHOUT_BILL: koreksi hanya untuk baris penerimaan yang sudah ditagih';end if;
      select exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id
          join erp.vendor_payments p on p.vendor_invoice_id=y.id and p.status='POSTED'
          where x.receipt_line_id=l.receipt_line_id and y.status='POSTED') into v_paid;
      if v_paid and v_dec06->>'after_payment'<>'CORRECTION_DOCUMENT' then
        raise exception 'BD_PAID_CORRECTION_REFUSED: invoice sumber sudah dibayar dan LAU-DEC06 tidak mengizinkan dokumen koreksi';end if;
      select coalesce(sum(x.net_amount),0) into v_source_net from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id
        where y.status='POSTED' and x.receipt_line_id=l.receipt_line_id;
      v_source_net:=v_source_net+(select coalesce(sum(x.amount),0) from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id
        and x.receipt_line_id=l.receipt_line_id and x.line_no<=l.line_no);
      if v_source_net<0 then raise exception 'BD_CORRECTION_BELOW_ZERO: koreksi membuat biaya tertagih sumber ini negatif (%)',v_source_net;end if;
      v_released:=0;v_complete:=false;
    end if;
    if v_released<0 then raise exception 'BD_INTERNAL: estimasi yang dilepas negatif';end if;
    update erp.bd_laundry_invoice_lines_v1 x set net_amount=x.amount-x.discount_share+x.rounding_share,released_estimate=v_released,
      variance=x.amount-x.discount_share+x.rounding_share-v_released,
      product_variance=case when v_dec06->>'variance_mode'='PRODUCT_COST' then x.amount-x.discount_share+x.rounding_share-v_released else 0 end,
      completes_source=coalesce(v_complete,false)
    where x.id=l.id;
  end loop;
  if exists(select 1 from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id and net_amount<0 and line_kind='BILL') then
    raise exception 'BD_INVOICE_LINE: nilai bersih baris tagih negatif';end if;
  -- Journal: cost per PO (WIP), variance account when chosen, input tax, payable to the vendor.
  for v_po in select po_id,sum(net_amount) net,sum(released_estimate) rel,sum(variance) var from erp.bd_laundry_invoice_lines_v1
      where invoice_id=i.id and opening_uninvoiced_id is null group by po_id order by po_id loop
    if v_dec06->>'variance_mode'='PRODUCT_COST' then
      if v_po.net<>0 then v_lines:=v_lines||jsonb_build_object('mapping_key','WIP','debit',greatest(v_po.net,0),'credit',greatest(-v_po.net,0),'po_id',v_po.po_id,'vendor_id',i.vendor_id);end if;
    else
      if v_po.rel<>0 then v_lines:=v_lines||jsonb_build_object('mapping_key','WIP','debit',v_po.rel,'credit',0,'po_id',v_po.po_id,'vendor_id',i.vendor_id);end if;
      if v_po.var<>0 then v_lines:=v_lines||jsonb_build_object('account_id',v_dec06->>'variance_account_id','debit',greatest(v_po.var,0),
        'credit',greatest(-v_po.var,0),'po_id',v_po.po_id,'vendor_id',i.vendor_id,'description','Selisih invoice laundry');end if;
    end if;
  end loop;
  -- ALL-W05: opening records release the opening accrual; their difference goes to the owner's variance account.
  select coalesce(sum(released_estimate),0),coalesce(sum(variance),0) into v_open_rel,v_open_var from erp.bd_laundry_invoice_lines_v1
    where invoice_id=i.id and opening_uninvoiced_id is not null;
  if v_open_rel<>0 then v_lines:=v_lines||jsonb_build_object('mapping_key','ACCRUED_MANUFACTURING','debit',v_open_rel,'credit',0,'vendor_id',i.vendor_id,
    'description','Akrual laundry saldo awal');end if;
  if v_open_var<>0 then v_lines:=v_lines||jsonb_build_object('account_id',v_dec06->>'variance_account_id','debit',greatest(v_open_var,0),
    'credit',greatest(-v_open_var,0),'vendor_id',i.vendor_id,'description','Selisih invoice laundry saldo awal');end if;
  if i.tax_amount>0 then v_lines:=v_lines||jsonb_build_object('account_id',v_dec03->>'tax_account_id','debit',i.tax_amount,'credit',0,'vendor_id',i.vendor_id,'description','Pajak masukan invoice laundry');end if;
  if i.header_total>0 then
    v_lines:=v_lines||jsonb_build_object('mapping_key','AP_VENDOR','debit',0,'credit',i.header_total,'vendor_id',i.vendor_id);
    -- The payable as an ordinary laundry vendor invoice (payments and AP checks read it); an upward correction document too.
    -- Created as DRAFT and posted by a status change, so the vendor invoice post-date guard and the receipt guard run on it.
    insert into erp.vendor_invoices(id,invoice_number,vendor_id,invoice_date,due_date,status,total_amount,notes,created_by)
    values(i.id,i.invoice_number,i.vendor_id,i.invoice_date,i.due_date,'DRAFT',i.header_total,
      case when i.corrects_invoice_id is null then 'BD invoice laundry (LAU-05b)' else 'BD koreksi naik atas invoice laundry '||o.invoice_number end,
      erp.current_app_user_id());
    update erp.vendor_invoices set status='POSTED' where id=i.id;
    v_journal:=erp.post_journal('VENDOR_INVOICE',i.id,i.invoice_date,
      case when i.corrects_invoice_id is null then 'Invoice vendor laundry ' else 'Koreksi naik invoice laundry '||o.invoice_number||': ' end||i.invoice_number,v_lines);
  else
    -- Downward correction: the vendor's payable falls on the correction date. It must be covered by what the vendor is still
    -- owed (a vendor receivable is not silently created).
    select coalesce(sum(jl.credit-jl.debit),0) into v_ap from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
      where je.status in('POSTED','REVERSED') and jl.account_id=erp.account_id('AP_VENDOR') and jl.vendor_id=i.vendor_id;
    if -i.header_total>v_ap then
      raise exception 'BD_CORRECTION_EXCEEDS_PAYABLE: koreksi turun % melebihi utang ke vendor ini saat ini %; kelebihan bayar ke vendor perlu alur piutang vendor tersendiri',
        -i.header_total,v_ap;end if;
    v_lines:=v_lines||jsonb_build_object('mapping_key','AP_VENDOR','debit',-i.header_total,'credit',0,'vendor_id',i.vendor_id);
    v_journal:=erp.post_journal('BD_LAUNDRY_CORRECTION_CREDIT',i.id,i.invoice_date,'Koreksi turun invoice laundry '||o.invoice_number||': '||i.invoice_number,v_lines);
  end if;
  update erp.bd_laundry_invoices_v1 set status='POSTED',policy_versions=v_versions,variance_mode=v_dec06->>'variance_mode',
    variance_account_id=(v_dec06->>'variance_account_id')::uuid,tax_account_id=(v_dec03->>'tax_account_id')::uuid,journal_id=v_journal,
    posted_by=erp.current_app_user_id(),posted_at=statement_timestamp(),row_version=row_version+1 where id=i.id;
  -- A downward correction first settles what its origin still owes (same date); the rest stays a vendor credit.
  if i.header_total<0 then
    select v.total_amount-erp.bd_vendor_invoice_paid_v1(v.id,null) into v_origin_left from erp.vendor_invoices v where v.id=o.id;
    if coalesce(v_origin_left,0)>0 then
      perform erp.bd_apply_vendor_credit_v1('INVOICE_CORRECTION',i.id,'VENDOR_INVOICE',o.id,least(-i.header_total,v_origin_left),i.invoice_date,
        'Koreksi turun '||i.invoice_number||' atas invoice asal',gen_random_uuid());
    end if;
  end if;
  perform erp.bd_invoice_resync_v1(i.id,i.invoice_date);
  return erp.bd_invoice_json_v1(i.id);
end;$function$;
CREATE OR REPLACE FUNCTION erp.bd_invoice_resync_v1(p_invoice uuid,p_date date)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_po uuid;v_service uuid;
begin
  for v_service in select distinct rework_service_id from erp.bd_laundry_invoice_lines_v1 where invoice_id=p_invoice and rework_service_id is not null order by 1 loop
    perform erp.be_redye_resync_v1(v_service,p_date);
  end loop;
  for v_po in select distinct po_id from erp.bd_laundry_invoice_lines_v1 where invoice_id=p_invoice and receipt_line_id is not null order by 1 loop
    perform erp.sync_laundry_accrual(v_po,p_date);
    if exists(select 1 from erp.fg_lots where po_id=v_po) then
      perform erp.rebuild_po_hpp(v_po,'BD laundry vendor invoice');
      perform erp.propagate_conversion_hpp_for_po(v_po);
      perform erp.sync_po_hpp_to_gl(v_po,p_date);
    end if;
  end loop;
end;$function$;
CREATE OR REPLACE FUNCTION erp.bd_reverse_invoice_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare i erp.bd_laundry_invoices_v1%rowtype;v_reason text:=nullif(btrim(p_payload->>'reason'),'');v_rev uuid;v_group uuid;v_line_ids uuid[];
  v_open_ids uuid[];
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['invoice_id','expected_version','reason'],array['invoice_id','expected_version','reason'],'reverse invoice');
  if v_reason is null then raise exception 'BD_REASON_REQUIRED: alasan wajib diisi';end if;
  select * into i from erp.bd_laundry_invoices_v1 where id=erp.bd_uuid_v1(p_payload,'invoice_id',true) for update;
  if i.id is null or i.status<>'POSTED' then raise exception 'BD_INVOICE_NOT_POSTED: hanya invoice POSTED yang dapat dibatalkan';end if;
  if p_payload->>'expected_version' is distinct from i.row_version::text then raise exception 'STALE_VERSION: invoice berubah; muat ulang';end if;
  perform 1 from erp.vendor_invoices where id=i.id for update;
  if exists(select 1 from erp.vendor_payments p where p.vendor_invoice_id=i.id and p.status='POSTED') then
    raise exception 'BD_INVOICE_PAID: invoice sudah dibayar; batalkan pembayaran dulu, atau koreksi dengan dokumen koreksi bila LAU-DEC06 mengizinkan';end if;
  -- A downward correction whose credit settles a document stays until that settlement is reversed.
  if i.header_total<0 and erp.bd_claim_credit_applied_v1('INVOICE_CORRECTION',i.id)>0 then
    raise exception 'BD_CLAIM_CREDIT_IN_USE: kredit koreksi % sudah dipakai untuk melunasi tagihan; batalkan pemakaiannya dulu',i.invoice_number;end if;
  for v_group in select distinct dl.cutting_group_id from erp.bd_laundry_invoice_lines_v1 x join erp.laundry_receipt_lines rl on rl.id=x.receipt_line_id
      join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id where x.invoice_id=i.id order by 1 loop
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group::text,0));
  end loop;
  select array_agg(distinct x.receipt_line_id order by x.receipt_line_id) into v_line_ids from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id;
  perform 1 from erp.laundry_receipt_lines where id=any(v_line_ids) order by id for update;
  select array_agg(distinct x.opening_uninvoiced_id order by x.opening_uninvoiced_id) into v_open_ids from erp.bd_laundry_invoice_lines_v1 x
    where x.invoice_id=i.id and x.opening_uninvoiced_id is not null;
  perform 1 from erp.bd_opening_laundry_uninvoiced_v1 where id=any(v_open_ids) order by id for update;
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  perform 1 from erp.be_redye_services_v1 where id in(select rework_service_id from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id) order by id for update;
  -- A later invoice that completed the same source took the residual after this one; reverse that one first.
  if exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id
      where y.status='POSTED' and y.id<>i.id and (x.receipt_line_id=any(v_line_ids) or x.opening_uninvoiced_id=any(v_open_ids) or x.rework_service_id in(select rework_service_id from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id)) and y.posted_at>i.posted_at) then
    raise exception 'BD_LATER_INVOICE_EXISTS: invoice lain yang diposting sesudahnya menagih sumber yang sama; batalkan yang terbaru dulu';end if;
  v_rev:=erp.reverse_journal(i.journal_id,'Batal invoice laundry: '||v_reason);
  update erp.vendor_invoices set status='REVERSED' where id=i.id;
  update erp.bd_laundry_invoices_v1 set status='REVERSED',reversal_journal_id=v_rev,reversed_by=erp.current_app_user_id(),reversed_at=statement_timestamp(),
    reverse_reason=v_reason,row_version=row_version+1 where id=i.id;
  perform erp.bd_invoice_resync_v1(i.id,(statement_timestamp() at time zone 'Asia/Jakarta')::date);
  return erp.bd_invoice_json_v1(i.id);
end;$function$;
create or replace function erp.desired_laundry_accrual(p_po_id uuid)
returns numeric
language sql
stable
security definer
set search_path=''
as $function$
  with posted_receipt_cost as(
    select
      lrl.delivery_line_id,
      coalesce(sum(lrl.qty_good_received+lrl.qty_bs_laundry) filter(
        where lr.status='POSTED'
          and lrl.actual_cost_status in('ESTIMATED','FINAL')
      ),0) as costed_qty,
      -- BD: less the estimate a posted laundry invoice line has already replaced (erp.bd_released_estimate_v1).
      coalesce(sum(lrl.actual_cost-erp.bd_released_estimate_v1(lrl.id)) filter(
        where lr.status='POSTED' and lrl.actual_cost_status='ESTIMATED'
      ),0) as unbilled_actual_estimate
    from erp.laundry_receipt_lines lrl
    join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    group by lrl.delivery_line_id
  ), line_status as(
    select
      ldl.id,
      ldl.qty_sent_pcs,
      ldl.estimated_rate_snapshot,
      coalesce(rc.costed_qty,0) as costed_qty,
      coalesce(rc.unbilled_actual_estimate,0) as unbilled_actual_estimate
    from erp.laundry_delivery_lines ldl
    join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
    left join posted_receipt_cost rc on rc.delivery_line_id=ldl.id
    where ld.po_id=p_po_id and ld.status not in('DRAFT','REVERSED')
  ), active_delivery_amount as(
    select coalesce(sum(
      unbilled_actual_estimate
      -- BD: a priced line's estimate less the shares taken by posted receipts; the old formula for any other line.
      +erp.bd_uncosted_estimate_v1(id,qty_sent_pcs,costed_qty,estimated_rate_snapshot)
    ),0)::numeric amount
    from line_status
  ), returned_failed_wash_amount as(
    select coalesce(sum(rl.actual_cost-erp.bd_released_estimate_v1(rl.id)),0)::numeric amount
    from erp.laundry_failed_wash_attempts a
    join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
    join erp.laundry_receipts r on r.id=a.receipt_id and r.status='POSTED'
    join erp.laundry_deliveries d on d.id=a.delivery_id and d.status='REVERSED'
    where d.po_id=p_po_id and rl.actual_cost_status='ESTIMATED'
  )
  select a.amount+f.amount+erp.be_redye_accrual_v1(p_po_id)
  from active_delivery_amount a cross join returned_failed_wash_amount f
$function$;
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
  select coalesce(sum(erp.pocket_period_amount_v1(d.pool_id,d.preceding_qty,d.sewing_qty)),0) into v_pocket from erp.pocket_period_destinations d where d.event_id is not null and d.po_id=p_po_id;
  -- One lock order covers Draft reservation, post/reversal, late recost, and GL sync.
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  perform pg_advisory_xact_lock(hashtextextended('PO_HPP:'||p_po_id::text,0));

  select coalesce(sum(-msm.qty_signed*msm.unit_cost_snapshot),0) into v_material
  from erp.material_stock_movements msm
  where ((msm.source_type='CUTTING_GROUP' and msm.source_id in (select id from erp.cutting_groups where po_id=p_po_id))
     or (msm.source_type='CUTTING_GROUP_RETURN' and msm.source_id in (select id from erp.cutting_groups where po_id=p_po_id)))
    and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id);

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
           -- BD: plus the product-cost variance of posted laundry invoice lines; a fully invoiced source is no longer pending.
           coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then coalesce(lrl.actual_cost,0)+erp.bd_product_variance_v1(lrl.id) else 0 end),0) as actual_cost,
           bool_or(lr.status='POSTED' and lrl.actual_cost_status in('PENDING','ESTIMATED') and not erp.bd_receipt_invoiced_v1(lrl.id)) as has_pending_receipt
    from erp.laundry_delivery_lines ldl
    join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
    left join erp.laundry_receipt_lines lrl on lrl.delivery_line_id=ldl.id
    left join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where ld.po_id=p_po_id and ld.status<>'REVERSED'
    group by ldl.id,ldl.cutting_group_id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot
  )
  -- BD: uncosted part of a priced line by its exact shares; an unknown component price keeps the HPP pending.
  select coalesce(sum(actual_cost+erp.bd_uncosted_estimate_v1(id,qty_sent_pcs,qty_costed_actual,estimated_rate_snapshot)),0),
         coalesce(bool_or(has_pending_receipt or qty_sent_pcs>qty_costed_actual or not erp.bd_line_complete_v1(id)),false)
  into v_laundry,v_pending from dl;

  select v_laundry+coalesce(sum(rl.actual_cost+erp.bd_product_variance_v1(rl.id)),0)
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
    where ld.po_id=p_po_id and rl.actual_cost_status='ESTIMATED' and not erp.bd_receipt_invoiced_v1(rl.id)
  );


  select coalesce(sum(rcl.amount_payable),0),
         coalesce(sum(case when bc.cutting_group_id is null then rcl.amount_payable else 0 end),0)
  into v_rework,v_shared_rework
  from erp.rework_component_lines rcl
  join erp.rework_orders ro on ro.id=rcl.rework_order_id
  join erp.bs_cases bc on bc.id=ro.bs_case_id
  where bc.po_id=p_po_id and ro.status<>'CANCELLED' and coalesce(ro.cost_posted,false)=true;

  v_rework:=v_rework+erp.be_redye_po_cost_v1(p_po_id);
  v_pending:=v_pending or exists(select 1 from erp.be_redye_services_v1 bs join erp.rework_orders br on br.id=bs.id
    where bs.po_id=p_po_id and br.status<>'CANCELLED' and erp.be_redye_accrual_v1(p_po_id)<>0)
    or exists(select 1 from erp.be_redye_services_v1 bs join erp.rework_orders br on br.id=bs.id where bs.po_id=p_po_id and br.status<>'CANCELLED' and erp.be_redye_rate_v1(bs.id) is null);
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
        where ((msm.source_type='CUTTING_GROUP' and msm.source_id in (select id from erp.cutting_groups where cutting_batch_id=v_batch_id))
           or (msm.source_type='CUTTING_GROUP_RETURN' and msm.source_id in (select id from erp.cutting_groups where cutting_batch_id=v_batch_id)))
          and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id);
        select effective_pcs::numeric into v_pool_qty from erp.v_cutting_batch_totals where cutting_batch_id=v_batch_id;
      else
        select coalesce(sum(-msm.qty_signed*msm.unit_cost_snapshot),0) into v_pool_material
        from erp.material_stock_movements msm
        where msm.source_id=r.lineage_group_id and msm.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN')
          and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id);
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
               coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then coalesce(lrl.actual_cost,0)+erp.bd_product_variance_v1(lrl.id) else 0 end),0) as actual_cost
        from erp.laundry_delivery_lines ldl
        join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
        left join erp.laundry_receipt_lines lrl on lrl.delivery_line_id=ldl.id
        left join erp.laundry_receipts lr on lr.id=lrl.receipt_id
        where ld.po_id=p_po_id and ld.status<>'REVERSED' and ldl.cutting_group_id=r.lineage_group_id
        group by ldl.id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot
      )
      select coalesce(sum(actual_cost+erp.bd_uncosted_estimate_v1(id,qty_sent_pcs,qty_costed_actual,estimated_rate_snapshot)),0)
      into v_group_laundry from dl;

      select v_group_laundry+coalesce(sum(rl.actual_cost+erp.bd_product_variance_v1(rl.id)),0)
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
            -- BD: a lot from a priced receipt size takes that size's own amount (sizes may be priced differently).
            then coalesce((select ba.amount/nullif(ba.qty,0) from erp.bd_laundry_receipt_allocations_v1 ba where ba.receipt_batch_size_line_id=rx.id),
              rl.actual_cost/nullif(rl.qty_good_received+rl.qty_bs_laundry,0))
              +erp.bd_product_variance_v1(rl.id)/nullif(rl.qty_good_received+rl.qty_bs_laundry,0)
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
CREATE OR REPLACE FUNCTION erp.cp6_lot_rework_cost_v2620c(p_lot_id uuid)
returns numeric
language sql
stable
security definer
set search_path=''
as $function$
  select coalesce(sum(rcl.amount_payable::numeric*fl.initial_qty_pcs/nullif(ro.qty_sent,0)),0)::numeric
    +coalesce((select erp.be_redye_cost_v1(rs.id)*rr.qty_good_returned/nullif(rr.qty_sent,0) from erp.be_redye_services_v1 rs join erp.rework_orders rr on rr.id=rs.id where rr.good_fg_lot_id=p_lot_id and rr.status<>'CANCELLED' and rr.cost_posted),0)
  from erp.fg_lots fl
  join erp.rework_orders ro on ro.good_fg_lot_id=fl.id
    and ro.status<>'CANCELLED' and ro.cost_posted=true
  join erp.rework_component_lines rcl on rcl.rework_order_id=ro.id
  where fl.id=p_lot_id and fl.lot_origin='PRODUCTION'
$function$;
CREATE OR REPLACE FUNCTION erp.period_blockers_v1(p_through date, p_window_from date)
 RETURNS TABLE(family text, code text, severity text, scope text, impact_date date, reference jsonb, reason text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
-- One engine for close, preview and report confidence (S06/B04).
-- Open items (recost, laundry price, payroll due, dated integrity) use every fact dated on or before p_through.
-- Completeness (attendance cells) uses the window [p_window_from, p_through]; a null start means unbounded. Callers
-- pass erp.period_completeness_from_v1(), the first date this engine was responsible for, so a closed date inside
-- the engine's era is re-checked after a later correction (P-01). Before that start only cells that once had a
-- posted record and lost it (reversed, not replaced) are reported.
-- Stock history follows the posting guards' own order (P-04). A current-state check whose defect is scoped by a
-- dated detector is reported as INFO once the detector confirms it; every other failing current-state check blocks
-- every date and names its class (P-03). Unknown check names block (fail closed).
declare
  v_end timestamptz := ((p_through + 1)::timestamp AT TIME ZONE 'Asia/Jakarta');
  v_fg jsonb;
  v_material jsonb;
  v_fg_confirmed boolean;
  v_material_confirmed boolean;
begin
  if p_through is null then raise exception 'PERIOD_BLOCKERS_DATE_REQUIRED'; end if;

  -- RECOST: open queue rows whose PO has a dated fact on or before the date.
  return query
  select 'RECOST'::text,
    case when q.status='FAILED' and q.attempt_count>=3 then 'RECOST_FAILED_EXHAUSTED' else 'RECOST_PENDING' end,
    case when q.status='FAILED' and q.attempt_count>=3 then 'CRITICAL' else 'RECALC' end,
    'AS_OF'::text, f.first_date,
    jsonb_build_object('queue_id',q.id,'po_id',q.entity_id,'po_number',po.po_number,'status',q.status,
      'attempt_count',q.attempt_count,'recalc_from',q.recalc_from,'facts',f.facts),
    format('Hitung ulang biaya PO %s belum selesai (status %s, percobaan %s); PO ini punya fakta pada atau sebelum %s.',
      coalesce(po.po_number,q.entity_id::text),q.status,q.attempt_count,p_through)
  from erp.cost_recalc_queue q
  left join erp.production_orders po on po.id=q.entity_id
  cross join lateral (
    select min(x.d) first_date, jsonb_agg(distinct x.k) facts from (
      select 'RECALC_FROM' k, erp._cp3_business_date(q.recalc_from) d where q.recalc_from is not null and q.recalc_from<v_end
      union all
      select 'CUTTING_MATERIAL', min(erp._cp3_business_date(m.physical_at))
        from erp.material_stock_movements m join erp.cutting_groups cg on cg.id=m.source_id
        where m.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') and cg.po_id=q.entity_id and m.physical_at<v_end
        having count(*)>0
      union all
      select 'CONTRACTOR_MATERIAL', min(erp._cp3_business_date(m.physical_at))
        from erp.material_stock_movements m
        join erp.contractor_material_issue_items ii on ii.id=m.source_id
        join erp.contractor_material_issues cmi on cmi.id=ii.issue_id
        where m.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and cmi.po_id=q.entity_id and m.physical_at<v_end
        having count(*)>0
      union all
      select 'FG_LOT', min(erp._cp3_business_date(fl.produced_at))
        from erp.fg_lots fl where fl.po_id=q.entity_id and fl.produced_at<v_end having count(*)>0
      union all
      select 'PO_JOURNAL', min(je.economic_date)
        from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
        where jl.po_id=q.entity_id and je.status in('POSTED','REVERSED') and je.economic_date<=p_through
        having count(*)>0
    ) x
  ) f
  where q.entity_type='PO' and q.status in('PENDING','RUNNING','FAILED') and f.first_date is not null;

  -- A PO queue row whose PO has no dated fact at all cannot be scoped to a date: it applies to every date.
  return query
  select 'RECOST'::text,'RECOST_UNSCOPED_ENTITY'::text,
    case when q.status='FAILED' and q.attempt_count>=3 then 'CRITICAL' else 'RECALC' end,'CURRENT_STATE'::text,null::date,
    jsonb_build_object('queue_id',q.id,'entity_type',q.entity_type,'entity_id',q.entity_id,'status',q.status,'attempt_count',q.attempt_count),
    format('Antrean hitung ulang PO %s belum selesai dan PO ini belum punya fakta bertanggal; berlaku untuk semua tanggal.',q.entity_id)
  from erp.cost_recalc_queue q
  where q.entity_type='PO' and q.status in('PENDING','RUNNING','FAILED') and q.recalc_from is null
    and not exists(select 1 from erp.material_stock_movements m join erp.cutting_groups cg on cg.id=m.source_id
      where m.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') and cg.po_id=q.entity_id)
    and not exists(select 1 from erp.material_stock_movements m join erp.contractor_material_issue_items ii on ii.id=m.source_id
      join erp.contractor_material_issues cmi on cmi.id=ii.issue_id
      where m.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and cmi.po_id=q.entity_id)
    and not exists(select 1 from erp.fg_lots fl where fl.po_id=q.entity_id)
    and not exists(select 1 from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
      where jl.po_id=q.entity_id and je.status in('POSTED','REVERSED'));

  -- A queue row for another entity type cannot be scoped to a date: conservative, every date.
  return query
  select 'RECOST'::text,'RECOST_UNSCOPED_ENTITY'::text,'CRITICAL'::text,'CURRENT_STATE'::text,null::date,
    jsonb_build_object('queue_id',q.id,'entity_type',q.entity_type,'entity_id',q.entity_id,'status',q.status),
    format('Antrean hitung ulang %s %s belum selesai dan tidak dapat dibatasi ke tanggal.',q.entity_type,q.entity_id)
  from erp.cost_recalc_queue q
  where q.entity_type<>'PO' and q.status in('PENDING','RUNNING','FAILED');

  -- FG history per SKU and per lot, in the order the posting guard uses (physical_at, system_created_at, id): every
  -- prefix, not the net per instant (P-04). Computed over the whole history once; a key blocks the dates from its
  -- first negative instant.
  select coalesce(jsonb_agg(z.k),'[]'::jsonb) into v_fg from (
    select jsonb_build_object('level',s.lvl,'product_id',min(s.product_id::text),'lot_id',s.lot_id,
      'location_id',s.location_id,'quality_grade',s.quality_grade,
      'first_negative_at',min(s.physical_at) filter(where s.balance<0),
      'lowest_qty',min(s.balance)) k
    from (
      select 'SKU'::text lvl,m.product_id,null::uuid lot_id,m.location_id,m.quality_grade,m.physical_at,
        sum(m.qty_signed) over(partition by m.product_id,m.location_id,m.quality_grade
          order by m.physical_at,m.system_created_at,m.id rows unbounded preceding) balance
      from erp.fg_stock_movements m
      union all
      select 'LOT'::text,m.product_id,m.lot_id,m.location_id,m.quality_grade,m.physical_at,
        sum(m.qty_signed) over(partition by m.lot_id,m.location_id,m.quality_grade
          order by m.physical_at,m.system_created_at,m.id rows unbounded preceding)
      from erp.fg_stock_movements m where m.lot_id is not null
    ) s
    group by s.lvl,case when s.lvl='SKU' then s.product_id end,s.lot_id,s.location_id,s.quality_grade
    having bool_or(s.balance<0)
  ) z;

  return query
  select 'INTEGRITY'::text,'FG_QTY_NEGATIVE_ASOF'::text,'CRITICAL'::text,'AS_OF'::text,
    erp._cp3_business_date((k->>'first_negative_at')::timestamptz),k,
    format('Stok barang jadi (%s) negatif sejak %s untuk produk %s di lokasi %s.',
      k->>'level',k->>'first_negative_at',k->>'product_id',k->>'location_id')
  from jsonb_array_elements(v_fg) k
  where (k->>'first_negative_at')::timestamptz<v_end;

  -- Material history on the cost engine's effective history and its exact order (reversed pairs excluded, a
  -- transfer-in ordered right after its transfer-out), per material, location and roll.
  select coalesce(jsonb_agg(z.k),'[]'::jsonb) into v_material from (
    with active as (
      select m.*,row_number() over(partition by m.material_id,m.source_id,m.roll_id,m.physical_at,
          abs(m.qty_signed),m.movement_type order by m.system_created_at,m.id) ordinal
      from erp.material_stock_movements m
      where m.source_type='MATERIAL_TRANSFER' and m.reversal_of_id is null
        and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
    ), pairs as (
      select i.id incoming,o.id outgoing,o.system_created_at out_created
      from active i join active o on o.material_id=i.material_id and o.source_id=i.source_id
        and o.roll_id is not distinct from i.roll_id and o.physical_at=i.physical_at
        and o.qty_signed=-i.qty_signed and o.ordinal=i.ordinal
        and o.movement_type='TRANSFER_OUT' and o.qty_signed<0
      where i.movement_type='TRANSFER_IN' and i.qty_signed>0
        and (o.physical_at,o.system_created_at,o.id)<(i.physical_at,i.system_created_at,i.id)
        and o.location_id<>i.location_id
    ), history as (
      select m.material_id,m.location_id,m.roll_id,m.physical_at,
        sum(m.qty_signed) over(partition by m.material_id,m.location_id,m.roll_id
          order by m.physical_at,coalesce(p.out_created,m.system_created_at),coalesce(p.outgoing,m.id),
            (p.outgoing is not null) rows unbounded preceding) balance
      from erp.material_stock_movements m
      left join pairs p on p.incoming=m.id
      where m.reversal_of_id is null
        and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
    )
    select jsonb_build_object('material_id',h.material_id,'location_id',h.location_id,'roll_id',h.roll_id,
      'first_negative_at',min(h.physical_at) filter(where h.balance<0),'lowest_qty',min(h.balance)) k
    from history h
    group by h.material_id,h.location_id,h.roll_id
    having bool_or(h.balance<0)
  ) z;

  return query
  select 'INTEGRITY'::text,'MATERIAL_QTY_NEGATIVE_ASOF'::text,'CRITICAL'::text,'AS_OF'::text,
    erp._cp3_business_date((k->>'first_negative_at')::timestamptz),k,
    format('Stok bahan negatif sejak %s untuk bahan %s.',k->>'first_negative_at',k->>'material_id')
  from jsonb_array_elements(v_material) k
  where (k->>'first_negative_at')::timestamptz<v_end;

  -- Per-key confirmation (P-03): a current-state check scoped by a detector is INFO only when every key failing it
  -- now is a key the detector found; an empty or partial match blocks every date.
  select count(*)>0 and coalesce(bool_and(exists(select 1 from jsonb_array_elements(v_fg) x where x->>'level'='SKU'
      and x->>'product_id'=k.product_id::text and x->>'location_id' is not distinct from k.location_id::text
      and x->>'quality_grade' is not distinct from k.quality_grade)),false)
  into v_fg_confirmed
  from (select m.product_id,m.location_id,m.quality_grade from erp.fg_stock_movements m
        group by m.product_id,m.location_id,m.quality_grade having sum(m.qty_signed)<0) k;
  select count(*)>0 and coalesce(bool_and(exists(select 1 from jsonb_array_elements(v_material) x
      where x->>'material_id'=k.material_id::text and x->>'location_id' is not distinct from k.location_id::text
      and x->>'roll_id' is not distinct from k.roll_id::text)),false)
  into v_material_confirmed
  from (select m.material_id,m.location_id,m.roll_id from erp.material_stock_movements m
        group by m.material_id,m.location_id,m.roll_id having sum(m.qty_signed)<-0.000001) k;

  -- INTEGRITY (current state), classified (P-03). Queue checks are handled per date by RECOST above.
  return query
  with failing as (
    select distinct on (c.check_name) c.check_name,c.src,c.issue_count,c.details from (
      select 'run_v268_financial_report_checks' src,r.check_name,r.severity,r.issue_count,r.details from erp.run_v268_financial_report_checks() r
      union all
      select 'run_v267_financial_truth_checks',r.check_name,r.severity,r.issue_count,r.details from erp.run_v267_financial_truth_checks() r
      union all
      select 'run_integrity_checks',r.check_name,r.severity,r.issue_count,r.details from erp.run_integrity_checks() r
    ) c
    where c.issue_count>0 and c.severity in('CRITICAL','ERROR')
      and c.check_name not in('V268_COST_RECALC_EXHAUSTED','V268_COST_RECALC_PENDING','STALE_RECOST_QUEUE','FAILED_RECOST_QUEUE')
    order by c.check_name,c.src
  ), registry(check_name,check_class,dated_by) as (
    select * from erp.period_integrity_check_registry_v1()
  ), classified as (
    select f.*,coalesce(r.check_class,'UNCLASSIFIED') check_class,r.dated_by,
      case r.dated_by when 'FG_QTY_NEGATIVE_ASOF' then v_fg_confirmed
                      when 'MATERIAL_QTY_NEGATIVE_ASOF' then v_material_confirmed
                      else false end confirmed
    from failing f left join registry r on r.check_name=f.check_name
  )
  select 'INTEGRITY'::text,c.check_name,
    case when c.check_class='DATED_EQUIVALENT' and c.confirmed then 'INFO' else 'CRITICAL' end,
    'CURRENT_STATE'::text,null::date,
    jsonb_build_object('check_name',c.check_name,'issue_count',c.issue_count,'source',c.src,'class',c.check_class,
      'dated_by',c.dated_by,'dated_detector_confirmed',c.confirmed,
      'date_policy',case when c.check_class='DATED_EQUIVALENT' and c.confirmed then 'SCOPED_BY_DATED_DETECTOR'
                         else 'BLOCKS_EVERY_DATE' end),
    case when c.check_class='DATED_EQUIVALENT' and c.confirmed
      then format('%s: dibatasi per tanggal oleh %s.',coalesce(c.details,c.check_name),c.dated_by)
      else coalesce(c.details,c.check_name) end
  from classified c;

  -- INTEGRITY (dated): GL inventory balance negative at any balance date on or before the date.
  return query
  select 'INTEGRITY'::text,'GL_INVENTORY_NEGATIVE_ASOF'::text,'CRITICAL'::text,'AS_OF'::text,min(g.balance_date),
    jsonb_build_object('account',g.mapping_key,'first_negative_date',min(g.balance_date),'lowest_balance',min(g.balance)),
    format('Saldo buku %s negatif sejak %s (terendah %s).',g.mapping_key,min(g.balance_date),min(g.balance))
  from (
    select k.mapping_key,a.balance_date,
      sum(a.debit_total-a.credit_total) over(partition by a.account_id order by a.balance_date) balance
    from erp.account_daily_balances a
    join (values('MATERIAL_INVENTORY'),('WIP'),('FG_INVENTORY')) k(mapping_key) on a.account_id=erp.account_id(k.mapping_key)
    where a.balance_date<=p_through
  ) g
  where g.balance<-0.005
  group by g.mapping_key;

  -- ATTENDANCE (window): eligible worker-days without a current posted record (owner: existing rule, OFF recorded).
  return query
  select 'ATTENDANCE'::text,'ATTENDANCE_CELL_MISSING'::text,'POLICY'::text,'WINDOW'::text,min(x.work_day),
    jsonb_build_object('contractor_id',x.contractor_id,'contractor_name',x.contractor_name,'worker_id',x.worker_id,
      'worker_name',x.worker_name,'missing_days',count(*),'first_missing',min(x.work_day),'last_missing',max(x.work_day),
      'sample_days',(array_agg(x.work_day order by x.work_day))[1:10],'window_from',p_window_from),
    format('Absensi %s (%s) kosong %s hari antara %s dan %s; hari libur dicatat OFF.',
      x.worker_name,x.contractor_name,count(*),min(x.work_day),max(x.work_day))
  from (
    select w.contractor_id,c.contractor_name,w.id worker_id,w.worker_name,gs.d::date as work_day
    from erp.contractor_workers w
    join erp.contractors c on c.id=w.contractor_id
    join erp.worker_employment_periods e on e.worker_id=w.id
    cross join lateral generate_series(
      greatest(e.started_on,coalesce(p_window_from,e.started_on))::timestamp,
      least(coalesce(e.ended_on,p_through),p_through)::timestamp,interval '1 day') gs(d)
    where c.attendance_required and w.pay_scheme in('DAILY','HYBRID')
      and not exists(select 1 from erp.attendance_records a
        where a.worker_id=w.id and a.attendance_date=gs.d::date and coalesce(a.record_lifecycle,'POSTED')='POSTED')
  ) x
  group by x.contractor_id,x.contractor_name,x.worker_id,x.worker_name;

  -- ATTENDANCE (before the window): an eligible worker-day that had a posted record which was later reversed and
  -- never replaced. The date was complete when it was accepted; a later change removed it (P-01).
  return query
  select 'ATTENDANCE'::text,'ATTENDANCE_CELL_REVERSED_UNREPLACED'::text,'POLICY'::text,'AS_OF'::text,min(x.work_day),
    jsonb_build_object('contractor_id',x.contractor_id,'contractor_name',x.contractor_name,'worker_id',x.worker_id,
      'worker_name',x.worker_name,'missing_days',count(*),'first_missing',min(x.work_day),'last_missing',max(x.work_day),
      'sample_days',(array_agg(x.work_day order by x.work_day))[1:10],'window_from',p_window_from),
    format('Absensi %s (%s) pada %s hari antara %s dan %s sudah dibatalkan dan belum dicatat ulang.',
      x.worker_name,x.contractor_name,count(*),min(x.work_day),max(x.work_day))
  from (
    select distinct w.contractor_id,c.contractor_name,w.id worker_id,w.worker_name,r.attendance_date work_day
    from erp.attendance_records r
    join erp.contractor_workers w on w.id=r.worker_id
    join erp.contractors c on c.id=w.contractor_id
    where p_window_from is not null and r.attendance_date<p_window_from and r.attendance_date<=p_through
      and r.record_lifecycle='REVERSED'
      and c.attendance_required and w.pay_scheme in('DAILY','HYBRID')
      and exists(select 1 from erp.worker_employment_periods e where e.worker_id=w.id
        and r.attendance_date between e.started_on and coalesce(e.ended_on,r.attendance_date))
      and not exists(select 1 from erp.attendance_records a
        where a.worker_id=w.id and a.attendance_date=r.attendance_date and coalesce(a.record_lifecycle,'POSTED')='POSTED')
  ) x
  group by x.contractor_id,x.contractor_name,x.worker_id,x.worker_name;

  -- PAYROLL: payroll due on or before the date that is not approved (owner: labour recognised at period_end).
  return query
  select 'PAYROLL'::text,'PAYROLL_NOT_APPROVED'::text,'POLICY'::text,'AS_OF'::text,ps.period_end,
    jsonb_build_object('payroll_id',ps.id,'payroll_number',ps.payroll_number,'contractor_id',ps.contractor_id,
      'period_start',ps.period_start,'period_end',ps.period_end,'status',ps.status),
    format('Payroll %s (%s s/d %s) masih %s; belum disetujui.',ps.payroll_number,ps.period_start,ps.period_end,ps.status)
  from erp.payroll_settlements ps
  where ps.status in('DRAFT','CALCULATED','REVIEW') and ps.period_end<=p_through;

  -- PAYROLL: paid attendance on or before the date that no non-reversed payroll has taken (linkage, not date range).
  return query
  select 'PAYROLL'::text,'PAYROLL_ATTENDANCE_UNCOVERED'::text,'POLICY'::text,'AS_OF'::text,min(ar.attendance_date),
    jsonb_build_object('contractor_id',ar.contractor_id,'worker_id',ar.worker_id,'worker_name',w.worker_name,
      'records',count(*),'first_date',min(ar.attendance_date),'last_date',max(ar.attendance_date)),
    format('Absensi %s: %s hari berbayar antara %s dan %s belum masuk payroll.',w.worker_name,count(*),min(ar.attendance_date),max(ar.attendance_date))
  from erp.attendance_records ar
  join erp.contractor_workers w on w.id=ar.worker_id
  join erp.contractors c on c.id=ar.contractor_id
  where ar.attendance_date<=p_through and coalesce(ar.record_lifecycle,'POSTED')='POSTED'
    and ar.paid_fraction>0 and w.pay_scheme in('DAILY','HYBRID') and c.attendance_required
    and not exists(select 1 from erp.payroll_attendance_items pai join erp.payroll_settlements ps on ps.id=pai.payroll_id
      where pai.attendance_record_id=ar.id and ps.status<>'REVERSED')
  group by ar.contractor_id,ar.worker_id,w.worker_name;

  -- PAYROLL: eligible piece or rework work on or before the date that no non-reversed payroll has taken.
  return query
  select 'PAYROLL'::text,'PAYROLL_WORK_UNCOVERED'::text,'POLICY'::text,'AS_OF'::text,
    min(erp._cp3_business_date(e.eligible_at)),
    jsonb_build_object('contractor_id',e.contractor_id,'lines',count(*),'remaining_qty',sum(e.remaining_qty),
      'remaining_amount',sum(e.remaining_amount),'first_eligible_at',min(e.eligible_at)),
    format('Hasil kerja kontraktor %s: %s baris (%s pcs) pada atau sebelum %s belum masuk payroll.',
      e.contractor_id,count(*),sum(e.remaining_qty),p_through)
  from erp.v_payroll_eligible_work_lines e
  where e.eligible_at<v_end and e.remaining_qty>0
  group by e.contractor_id;

  -- LAUNDRY: sent quantity still costed at an unknown (null) delivery rate on or before the date.
  return query
  select 'LAUNDRY'::text,'LAUNDRY_PRICE_UNKNOWN'::text,'POLICY'::text,'AS_OF'::text,
    erp._cp3_business_date(ld.physical_at),
    jsonb_build_object('delivery_id',ld.id,'delivery_number',ld.delivery_number,'delivery_line_id',ldl.id,
      'po_id',ld.po_id,'uncosted_qty',greatest(ldl.qty_sent_pcs-coalesce(rc.costed_qty,0),0)),
    format('Harga laundry kiriman %s belum diketahui untuk %s pcs; isi estimasi owner.',
      ld.delivery_number,greatest(ldl.qty_sent_pcs-coalesce(rc.costed_qty,0),0))
  from erp.laundry_delivery_lines ldl
  join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
  left join lateral (select sum(lrl.qty_good_received+lrl.qty_bs_laundry) costed_qty
    from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where lrl.delivery_line_id=ldl.id and lr.status='POSTED' and lrl.actual_cost_status in('ESTIMATED','FINAL')) rc on true
  where ld.status not in('DRAFT','REVERSED') and ldl.estimated_rate_snapshot is null
    and ld.physical_at<v_end and ldl.qty_sent_pcs-coalesce(rc.costed_qty,0)>0;

  -- BD (LAU-05b, LAU-T12): a component price of a priced delivery still unknown on or before the date, reported here when
  -- LAUNDRY_PRICE_UNKNOWN does not (every piece already returned and costed at the known part only).
  return query
  select 'LAUNDRY'::text,'BD_LAUNDRY_COMPONENT_PRICE_UNKNOWN'::text,'POLICY'::text,'AS_OF'::text,
    erp._cp3_business_date(ld.physical_at),
    jsonb_build_object('delivery_id',ld.id,'delivery_number',ld.delivery_number,'delivery_line_id',bp.delivery_line_id,'po_id',ld.po_id,
      'unknown_charges',(select count(*) from erp.bd_laundry_charge_lines_v1 c where c.delivery_line_id=bp.delivery_line_id and c.rate_status='UNKNOWN')),
    format('Harga komponen laundry kiriman %s belum diketahui; isi harga komponen di halaman harga laundry.',ld.delivery_number)
  from erp.bd_laundry_priced_lines_v1 bp
  join erp.laundry_delivery_lines ldl on ldl.id=bp.delivery_line_id
  join erp.laundry_deliveries ld on ld.id=bp.delivery_id
  left join lateral (select sum(lrl.qty_good_received+lrl.qty_bs_laundry) costed_qty
    from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where lrl.delivery_line_id=ldl.id and lr.status='POSTED' and lrl.actual_cost_status in('ESTIMATED','FINAL')) rc on true
  where not bp.total_complete and ld.status not in('DRAFT','REVERSED') and ld.physical_at<v_end
    and not(ldl.estimated_rate_snapshot is null and ldl.qty_sent_pcs-coalesce(rc.costed_qty,0)>0);

  -- BD (ALL-W05): laundry work returned before cutover whose value is still unknown (no estimate, not fully billed).
  return query
  select 'LAUNDRY'::text,'BD_OPENING_LAUNDRY_PRICE_UNKNOWN'::text,'POLICY'::text,'AS_OF'::text,u.receipt_date,
    jsonb_build_object('opening_uninvoiced_id',u.id,'document_number',u.document_number,'vendor_id',u.vendor_id,'category',u.category,'qty',u.qty),
    format('Nilai laundry saldo awal %s (%s) belum diketahui; isi estimasi atau posting invoice vendornya.',u.document_number,u.category)
  from erp.bd_opening_laundry_uninvoiced_v1 u
  where u.estimated_amount is null and u.receipt_date<=p_through and not erp.bd_opening_invoiced_v1(u.id);

  return query
  select 'LAUNDRY'::text,'BE_REDYE_PRICE_UNKNOWN'::text,'POLICY'::text,'AS_OF'::text,erp._cp3_business_date(s.sent_at),
    jsonb_build_object('rework_service_id',s.id,'vendor_id',s.vendor_id,'po_id',s.po_id),
    'Harga jasa celup ulang belum diketahui; isi harga sumber sebelum tutup buku.'::text
  from erp.be_redye_services_v1 s join erp.rework_orders r on r.id=s.id
  where r.status<>'CANCELLED' and s.sent_at<v_end and erp.be_redye_rate_v1(s.id) is null;

  -- LAUNDRY: a delivery rate that is not a finite non-negative number is not a known price (P-02).
  return query
  select 'LAUNDRY'::text,'LAUNDRY_PRICE_INVALID'::text,'CRITICAL'::text,'AS_OF'::text,
    erp._cp3_business_date(ld.physical_at),
    jsonb_build_object('delivery_id',ld.id,'delivery_number',ld.delivery_number,'delivery_line_id',ldl.id,
      'po_id',ld.po_id,'rate',ldl.estimated_rate_snapshot::text),
    format('Harga laundry kiriman %s tidak valid (%s); harga harus angka hingga dan tidak negatif.',
      ld.delivery_number,ldl.estimated_rate_snapshot::text)
  from erp.laundry_delivery_lines ldl
  join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
  where ld.status not in('DRAFT','REVERSED') and ld.physical_at<v_end
    and (ldl.estimated_rate_snapshot='NaN'::numeric or ldl.estimated_rate_snapshot<0);

  -- GRNI: owner allows close with an estimate; reported, never blocking.
  return query
  select 'GRNI'::text,'GRNI_ESTIMATE_OPEN'::text,'INFO'::text,'CURRENT_STATE'::text,
    erp._cp3_business_date(min(g.physical_at)),
    jsonb_build_object('receipts',count(*),'estimated_amount',sum(g.grni_estimated_amount)),
    format('%s penerimaan bahan masih memakai estimasi GRNI (total %s); boleh ditutup dengan estimasi.',count(*),sum(g.grni_estimated_amount))
  from erp.v_material_grni_aging g
  where g.physical_at<v_end
  having count(*)>0;
end
$function$;
CREATE OR REPLACE FUNCTION erp.bd_lot_laundry_unknown_v1(p_lot uuid)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select exists(select 1 from erp.fg_lots be_lot join erp.be_redye_services_v1 be_s on be_s.po_id=be_lot.po_id join erp.rework_orders be_r on be_r.id=be_s.id where be_lot.id=p_lot and be_r.status<>'CANCELLED' and erp.be_redye_rate_v1(be_s.id) is null) or coalesce((select erp.bd_delivery_line_price_unknown_v1(rl.delivery_line_id) from erp.fg_lots l join erp.qc_inspection_items qi on qi.id=l.qc_item_id
      join erp.laundry_receipt_lines rl on rl.id=qi.source_laundry_receipt_line_id where l.id=p_lot),
    exists(select 1 from erp.fg_lots l join erp.laundry_deliveries d on d.po_id=l.po_id and d.status not in('DRAFT','REVERSED')
      join erp.laundry_delivery_lines dl on dl.delivery_id=d.id where l.id=p_lot and erp.bd_delivery_line_price_unknown_v1(dl.id)))
$function$;
CREATE OR REPLACE FUNCTION erp.get_laundry_bd_workspace_v1(p_filters jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_vendor uuid;v_now timestamptz:=statement_timestamp();v_money boolean;
begin
  perform erp.require_permission('production.laundry.view');
  if jsonb_typeof(coalesce(p_filters,'{}'::jsonb)) is distinct from 'object' then raise exception 'BD_FILTER_INVALID: filter wajib objek';end if;
  v_vendor:=erp.bd_uuid_v1(coalesce(p_filters,'{}'::jsonb),'vendor_id',false);
  v_money:=erp.has_permission('finance.hpp.view') or erp.has_permission('finance.hpp.manage');
  return jsonb_build_object(
    'redye_services',erp.be_redye_workspace_v1(v_vendor,v_money),
    'filters',coalesce(p_filters,'{}'::jsonb),'money_visible',v_money,
    'can_manage_master',erp.current_app_role() in('OWNER','ADMIN') and erp.has_permission('master.partner.manage'),
    'can_set_price',erp.current_app_role() in('OWNER','ADMIN') and erp.has_permission('finance.hpp.manage'),
    'is_owner',erp.current_app_role()='OWNER',
    'policies',(select jsonb_agg(jsonb_build_object('key',replace(policy_key,'_','-'),'status',status,'value',value,'version',version::text,
        'set_at',to_char(set_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),'reason',reason) order by policy_key) from erp.bd_policy_settings_v1),
    'vendors',coalesce((select jsonb_agg(jsonb_build_object('id',v.id,'code',v.vendor_code,'name',v.vendor_name,
        'pricing_mode',coalesce(t.pricing_mode,'RATE'),'pricing_unit',coalesce(t.pricing_unit,'PCS'),
        'bd_priced',t.pricing_mode is distinct from null and (t.pricing_mode<>'RATE' or t.pricing_unit<>'PCS' or t.minimum_charge is not null)
          or exists(select 1 from erp.bd_laundry_scoped_rates_v1 r where r.vendor_id=v.id),
        'minimum_charge',case when v_money then t.minimum_charge::numeric(18,2)::text end,'terms_version',coalesce(t.row_version,0)::text) order by v.vendor_name,v.id)
      from erp.laundry_vendors v left join erp.bd_laundry_vendor_terms_v1 t on t.vendor_id=v.id where v.is_active),'[]'::jsonb),
    'processes',coalesce((select jsonb_agg(jsonb_build_object('id',w.id,'code',w.process_code,'name',w.process_name) order by w.process_name,w.id)
      from erp.wash_processes w where w.is_active),'[]'::jsonb),
    'components',coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'vendor_id',c.vendor_id,'code',c.component_code,'name',c.component_name,
        'is_active',c.is_active,'current',(select jsonb_build_object('status',r.rate_status,'rate',case when v_money then r.rate_per_pcs::numeric(18,2)::text end,
          'from',to_char(r.effective_from at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'))
          from erp.bd_laundry_component_rates_v1 r where r.component_id=c.id and r.effective_from<=v_now and (r.effective_to is null or r.effective_to>v_now)))
        order by c.component_name,c.id)
      from erp.bd_laundry_components_v1 c where v_vendor is null or c.vendor_id=v_vendor),'[]'::jsonb),
    'packages',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'vendor_id',p.vendor_id,'code',p.package_code,'name',p.package_name,'is_active',p.is_active,
        'component_ids',(select coalesce(jsonb_agg(pc.component_id order by pc.component_id),'[]'::jsonb) from erp.bd_laundry_package_components_v1 pc where pc.package_id=p.id),
        'current_rate',(select case when v_money then r.rate_per_pcs::numeric(18,2)::text end from erp.bd_laundry_package_rates_v1 r
          where r.package_id=p.id and r.effective_from<=v_now and (r.effective_to is null or r.effective_to>v_now))) order by p.package_name,p.id)
      from erp.bd_laundry_packages_v1 p where v_vendor is null or p.vendor_id=v_vendor),'[]'::jsonb),
    'process_rates',coalesce((select jsonb_agg(jsonb_build_object('id',r.id,'vendor_id',r.vendor_id,'wash_process_id',r.wash_process_id,
        'rate',case when v_money then r.rate_per_pcs::numeric(18,2)::text end,'from',to_char(r.effective_from at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),
        'to',to_char(r.effective_to at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')) order by r.vendor_id,r.wash_process_id,r.effective_from)
      from erp.laundry_vendor_rate_versions r where (v_vendor is null or r.vendor_id=v_vendor) and (r.effective_to is null or r.effective_to>v_now - interval '120 days')),'[]'::jsonb),
    'scoped_rates',coalesce((select jsonb_agg(jsonb_build_object('id',r.id,'vendor_id',r.vendor_id,'wash_process_id',r.wash_process_id,'scope',r.scope,
        'model_id',r.model_id,'size_id',r.size_id,'color_name',r.color_name,'rate',case when v_money then r.rate_per_pcs::numeric(18,2)::text end,
        'from',to_char(r.effective_from at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')) order by r.created_at)
      from erp.bd_laundry_scoped_rates_v1 r where v_vendor is null or r.vendor_id=v_vendor),'[]'::jsonb),
    -- Amounts of a priced delivery only for money readers (quantities, labels and price status for everyone).
    'priced_deliveries',coalesce((select jsonb_agg(case when v_money then x.j else (x.j-'total_known')||jsonb_build_object(
        'charges',(select coalesce(jsonb_agg(c-'unit_rate'-'amount' order by (c->>'line_no')::integer),'[]'::jsonb) from jsonb_array_elements(x.j->'charges') c),
        'sizes',(select coalesce(jsonb_agg(s-'known_amount' order by s->>'size_id'),'[]'::jsonb) from jsonb_array_elements(x.j->'sizes') s)) end
      order by x.at desc) from (
        select erp.bd_priced_line_json_v1(p.delivery_line_id)||jsonb_build_object('delivery_number',d.delivery_number,'status',d.status,
          'physical_local',to_char(d.physical_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')) j,d.physical_at at
        from erp.bd_laundry_priced_lines_v1 p join erp.laundry_deliveries d on d.id=p.delivery_id
        where v_vendor is null or p.vendor_id=v_vendor order by d.physical_at desc limit 50) x),'[]'::jsonb),
    -- ALL-W05: laundry work returned before cutover and not yet billed (billed later by an invoice line with opening_uninvoiced_id).
    'opening_uninvoiced',coalesce((select jsonb_agg(jsonb_build_object('id',u.id,'vendor_id',u.vendor_id,'vendor_code',v.vendor_code,
        'document_number',u.document_number,'receipt_date',u.receipt_date,'category',u.category,'qty',u.qty,'billed',erp.bd_opening_billed_v1(u.id),
        'estimate_status',case when u.estimated_amount is null then 'UNKNOWN' else 'KNOWN' end,
        'estimated_amount',case when v_money then u.estimated_amount::text end,'released',case when v_money then erp.bd_opening_released_v1(u.id)::numeric(18,2)::text end,
        'invoiced',erp.bd_opening_invoiced_v1(u.id),'po_number',(select po_number from erp.production_orders where id=u.po_id),
        'dispatch_number',u.dispatch_number,'row_version',u.row_version::text) order by u.receipt_date,u.document_number,u.category)
      from erp.bd_opening_laundry_uninvoiced_v1 u join erp.laundry_vendors v on v.id=u.vendor_id where v_vendor is null or u.vendor_id=v_vendor),'[]'::jsonb),
    -- Money readers only (null otherwise: hidden, never empty): the latest invoices and, for one vendor, the receipt lines it
    -- can still bill (capacity and billed quantity per category), and the accounts the owner may pick in LAU-DEC03/06.
    'invoices',case when v_money then coalesce((select jsonb_agg(erp.bd_invoice_json_v1(i.id)||jsonb_build_object('vendor_code',v.vendor_code) order by i.created_at desc,i.id)
        from (select * from erp.bd_laundry_invoices_v1 x where v_vendor is null or x.vendor_id=v_vendor order by x.created_at desc,x.id limit 50) i
        join erp.laundry_vendors v on v.id=i.vendor_id),'[]'::jsonb) end,
    'billable_receipts',case when v_money and v_vendor is not null then coalesce((select jsonb_agg(x.j order by x.at desc,x.id) from (
        select rl.id,r.physical_at at,jsonb_build_object('receipt_line_id',rl.id,'receipt_number',r.receipt_number,'delivery_number',d.delivery_number,
          'po_number',po.po_number,'received_local',to_char(r.physical_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),
          'failed_attempt',a.id is not null,'estimate',rl.actual_cost::numeric(18,2)::text,'released',erp.bd_released_estimate_v1(rl.id)::numeric(18,2)::text,
          'price_known',erp.bd_line_complete_v1(rl.delivery_line_id),
          'capacity',jsonb_build_object('GOOD',erp.bd_invoice_capacity_v1(rl.id,'GOOD'),'BS',erp.bd_invoice_capacity_v1(rl.id,'BS'),
            'FAILED_ATTEMPT',erp.bd_invoice_capacity_v1(rl.id,'FAILED_ATTEMPT')),
          'billed',jsonb_build_object('GOOD',erp.bd_invoice_billed_v1(rl.id,'GOOD'),'BS',erp.bd_invoice_billed_v1(rl.id,'BS'),
            'FAILED_ATTEMPT',erp.bd_invoice_billed_v1(rl.id,'FAILED_ATTEMPT'))) j
        from erp.laundry_receipt_lines rl join erp.laundry_receipts r on r.id=rl.receipt_id and r.status='POSTED'
        join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id join erp.laundry_deliveries d on d.id=dl.delivery_id
        join erp.production_orders po on po.id=d.po_id left join erp.laundry_failed_wash_attempts a on a.receipt_line_id=rl.id
        where d.vendor_id=v_vendor and rl.actual_cost_status='ESTIMATED' and rl.actual_cost is not null and not erp.bd_receipt_invoiced_v1(rl.id)
        order by r.physical_at desc,rl.id limit 200) x),'[]'::jsonb) end,
    'accounts',case when v_money then coalesce((select jsonb_agg(jsonb_build_object('id',a.id,'code',a.account_code,'name',a.account_name,'type',a.account_type)
        order by a.account_code) from erp.chart_accounts a where a.is_active and a.is_postable and a.account_type in('ASSET','EXPENSE')),'[]'::jsonb) end,
    -- D12: the payment screen of one vendor (money readers only): documents with cash, claim credit and remaining, claim credits,
    -- and the ledger check.
    'payables',case when v_money and v_vendor is not null then erp.bd_vendor_payables_v1(v_vendor) end,
    -- LAU-DEC04 ALLOW_PENDING (owner decision no. 11): goods and sales whose HPP is not final while a laundry price is unknown.
    'pending_cost',erp.bd_pending_cost_json_v1(v_vendor,v_money));
end;$function$;
CREATE OR REPLACE FUNCTION erp.save_laundry_bd_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_action text:=upper(btrim(coalesce(p_action,'')));v_prior erp.bd_requests_v1%rowtype;v_result jsonb;
begin
  if erp.current_app_user_id() is null and session_user not in('postgres','supabase_admin') then raise exception 'BD_AUTH_REQUIRED: login ERP diperlukan';end if;
  if p_client_request_id is null then raise exception 'BD_REQUEST_REQUIRED: id permintaan wajib';end if;
  if jsonb_typeof(p_payload) is distinct from 'object' then raise exception 'BD_PAYLOAD_INVALID: payload wajib objek';end if;
  if v_action not in('SET_REDYE_PRICE','SET_POLICY','SAVE_VENDOR_TERMS','SAVE_COMPONENT','SAVE_COMPONENT_RATE','SAVE_PACKAGE','SAVE_PACKAGE_RATE','SAVE_PROCESS_RATE',
    'SAVE_SCOPED_RATE','POST_PRICED_DELIVERY','SET_CHARGE_PRICE','SAVE_INVOICE_DRAFT','CANCEL_INVOICE_DRAFT','POST_INVOICE','REVERSE_INVOICE','SET_OPENING_ESTIMATE',
    'APPLY_CLAIM_CREDIT','PAY_VENDOR_DOCUMENT','REVERSE_VENDOR_SETTLEMENT') then
    raise exception 'BD_ACTION_UNKNOWN: aksi laundry % tidak dikenal',v_action;end if;
  if v_action='SET_REDYE_PRICE' then perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');perform erp.require_permission('warehouse.brand_conversion.post');end if;
  perform pg_advisory_xact_lock(hashtextextended('BDREQ:'||p_client_request_id::text,0));
  select * into v_prior from erp.bd_requests_v1 where request_id=p_client_request_id;
  if v_prior.request_id is not null then
    if v_prior.action<>v_action or v_prior.payload<>p_payload or v_prior.actor is distinct from erp.current_app_user_id() then
      raise exception 'BD_REQUEST_REUSED: id permintaan sudah dipakai untuk isi lain';end if;
    return v_prior.response||jsonb_build_object('replayed',true);
  end if;
  v_result:=case v_action
    when 'SET_REDYE_PRICE' then erp.save_product_conversion_action_v1('SET_REDYE_PRICE',p_payload,p_client_request_id)
    when 'SET_POLICY' then erp.bd_set_policy_v1(p_payload,p_client_request_id)
    when 'POST_PRICED_DELIVERY' then erp.bd_post_priced_delivery_v1(p_payload,p_client_request_id)
    when 'SET_CHARGE_PRICE' then erp.bd_set_charge_price_v1(p_payload,p_client_request_id)
    when 'SAVE_INVOICE_DRAFT' then erp.bd_save_invoice_draft_v1(p_payload,p_client_request_id)
    when 'CANCEL_INVOICE_DRAFT' then erp.bd_cancel_invoice_draft_v1(p_payload,p_client_request_id)
    when 'POST_INVOICE' then erp.bd_post_invoice_v1(p_payload,p_client_request_id)
    when 'REVERSE_INVOICE' then erp.bd_reverse_invoice_v1(p_payload,p_client_request_id)
    when 'SET_OPENING_ESTIMATE' then erp.bd_set_opening_estimate_v1(p_payload,p_client_request_id)
    when 'APPLY_CLAIM_CREDIT' then erp.bd_apply_claim_credit_v1(p_payload,p_client_request_id)
    when 'PAY_VENDOR_DOCUMENT' then erp.bd_pay_vendor_document_v1(p_payload,p_client_request_id)
    when 'REVERSE_VENDOR_SETTLEMENT' then erp.bd_reverse_vendor_settlement_v1(p_payload,p_client_request_id)
    else erp.bd_save_master_v1(v_action,p_payload,p_client_request_id) end;
  v_result:=jsonb_build_object('action',v_action,'request_id',p_client_request_id,'status','SAVED')||v_result;
  insert into erp.bd_requests_v1(request_id,action,actor,payload,response) values(p_client_request_id,v_action,erp.current_app_user_id(),p_payload,v_result);
  return v_result;
end;$function$;
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
 return v_result||erp.be_pocket_workspace_v1(v_query);
end;$function$;
CREATE OR REPLACE FUNCTION erp.check_initial_import_receipt_v1(p_batch_id uuid,p_row_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD' AS $function$
declare r erp.migration_staging_rows%rowtype;s erp.migration_staging_rows%rowtype;
 j jsonb;v_cutover date;v_party uuid;v_key text;v_number text;v_line text;v_date date;v_qty numeric;v_cost numeric;k text;
 v_part jsonb;v_invoiced numeric:=0;v_blend numeric;
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
 -- BB (ALL-P03): a part of this line invoiced before cutover (its imported SUPPLIER_PAYABLE document): the line keeps
 -- its full quantity (unbilled + invoiced = stock + consumed origins) and its stock carries the blended cost.
 v_part:=erp.bb_receipt_row_invoiced_part_v1(p_batch_id,p_row_id);
 v_invoiced:=coalesce((v_part->>'invoiced_qty')::numeric,0);
 v_blend:=case when v_part is null then v_cost else round((v_qty*v_cost+(v_part->>'invoiced_amount')::numeric)/(v_qty+v_invoiced),6) end;

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
   or (s.normalized_payload->>'unit_cost')::numeric is distinct from v_blend then
   raise exception 'opening_source_key: bahan, gudang, dan biaya harus sama dengan stok awal (biaya per satuan %)',v_blend;end if;
  if nullif(s.normalized_payload->>'supplier_code','') is not null and s.normalized_payload->>'supplier_code'<>j->>'supplier_code' then
   raise exception 'supplier_code: supplier berbeda dengan stok asal';end if;
 end if;
 if v_qty+v_invoiced is distinct from coalesce((s.normalized_payload->>case when s.entity_type='MATERIAL_ROLL' then 'opening_qty' else 'qty' end)::numeric,0)
   +coalesce((select sum((x.normalized_payload->>'qty')::numeric) from erp.migration_staging_rows x where x.batch_id=p_batch_id
     and x.entity_type='OPENING_COST_ORIGIN' and x.validation_status='VALID'
     and x.normalized_payload->>'supplier_code'=j->>'supplier_code'
     and lower(btrim(x.normalized_payload->>'receipt_number'))=lower(v_number)
     and lower(btrim(x.normalized_payload->>'receipt_line_number'))=lower(v_line)),0)+erp.be_pocket_receipt_staged_qty_v1(p_batch_id,j) then
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
   perform erp.bb_sync_item_split_values_v1(r.id,v_date);
   perform erp.rebuild_po_hpp(v_po,'Koreksi asal bahan sebelum cutover');
   perform erp.propagate_conversion_hpp_for_po(v_po);
   perform erp.sync_po_hpp_to_gl(v_po,v_date);
  end if;
  update erp.initial_import_origin_cost_events set journal_entry_id=v_journal where id=v_event;
 end loop;
 perform erp.be_pocket_recost_receipt_v1(p_purchase_item);
end;$function$;
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
      where d.opening_cash_advance_balance_id=b.id and p.status='PAID'),0)
    +coalesce((select sum(r.amount) from erp.payroll_reimbursements r join erp.payroll_settlements p on p.id=r.payroll_id
      where r.opening_payable_balance_id=b.id and p.status='PAID'),0) paid) x
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
  where x.amount<=0 or x.amount::text in('NaN','Infinity','-Infinity') or (ca.id is null and erp.initial_prepayment_account_v1(x.id) is null and erp.bb_opening_credit_account_v1(x.id) is null)
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
          or not((l.account_id=coalesce(erp.initial_prepayment_account_v1(x.id),erp.bb_opening_credit_account_v1(x.id),ca.coa_account_id) and
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
            or not((l.account_id=coalesce(erp.initial_prepayment_account_v1(x.id),erp.bb_opening_credit_account_v1(x.id),ca.coa_account_id) and
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
        or pi.qty is distinct from coalesce(oi.qty,0)+coalesce((select sum(material_qty) from erp.initial_import_cost_origins where purchase_item_id=pi.id),0)+coalesce((select sum(material_qty) from erp.be_pocket_receipt_origins_v1 where purchase_item_id=pi.id),0)
        or (l.opening_item_id is not null and (pi.material_id is distinct from oi.material_id or erp.bb_receipt_opening_unit_cost_v1(pi.id) is distinct from oi.unit_cost_snapshot
        or oi.location_id is distinct from h.location_id))
        or (l.opening_item_id is not null and (select count(*) from erp.material_stock_movements m where m.source_type='OPENING_BALANCE_ITEM'
          and m.source_id=oi.id and m.movement_type='OPENING' and m.qty_signed=oi.qty)<>1)
        or exists(select 1 from erp.material_stock_movements m where m.source_type='MATERIAL_PURCHASE_ITEM' and m.source_id=pi.id)))
  union all
  select 'AP_OPENING_RECEIPT_JOURNAL_DRIFT','CRITICAL',count(*)::bigint,
    'Imported GRNI opening has exact value, opening equity offset, and cutover date'
  from erp.initial_import_receipt_headers rh
  cross join lateral(select round(sum((qty-erp.bb_receipt_invoiced_qty_v1(id))*unit_price),2) value from erp.material_purchase_items where purchase_id=rh.purchase_id) v
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
       +coalesce((select sum(round(o.material_qty*erp.material_purchase_current_unit_cost(i.id),2)) from erp.initial_import_cost_origins o where o.purchase_item_id=i.id),0)+coalesce((select sum(round(o.material_qty*erp.material_purchase_current_unit_cost(i.id),2)) from erp.be_pocket_receipt_origins_v1 o where o.purchase_item_id=i.id),0)
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
  if v_type not in ('BRAND','SIZE','MODEL','PRODUCT','CUSTOMER','SUPPLIER','CONTRACTOR','ACCESSORY_CATEGORY','MATERIAL','MATERIAL_ROLL','OPENING_BALANCE_ITEM','OPEN_PO','OPENING_CONTROL','OPENING_ADVANCE','OPENING_COST_ORIGIN','UNINVOICED_RECEIPT','LAUNDRY_VENDOR','LOCATION','CHART_ACCOUNT','CASH_ACCOUNT','LEGACY_DOCUMENT','OPENING_CUSTOMER_CREDIT','OPENING_SALE_RETURN','OPEN_PURCHASE_ORDER','OPENING_PAYROLL_ENTITLEMENT','OPENING_REWORK','OPENING_REWORK_COMPONENT','OPEN_SALES_DRAFT','OPENING_ACCESSORY_NOTE_LINE','OPENING_ACCESSORY_CUSTODY','OPENING_LAUNDRY_CLAIM','OPENING_LAUNDRY_UNINVOICED','OPENING_POCKET_USAGE','OPENING_POCKET_SEWING') then
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
    from erp.migration_staging_rows where batch_id=p_batch_id and entity_type not in('MATERIAL_ROLL','OPENING_BALANCE_ITEM','OPENING_CONTROL','OPENING_COST_ORIGIN','UNINVOICED_RECEIPT','OPENING_ADVANCE','LEGACY_DOCUMENT','OPENING_CUSTOMER_CREDIT','OPENING_SALE_RETURN','OPEN_PURCHASE_ORDER','OPENING_PAYROLL_ENTITLEMENT','OPENING_REWORK','OPENING_REWORK_COMPONENT','OPEN_SALES_DRAFT','OPENING_ACCESSORY_NOTE_LINE','OPENING_ACCESSORY_CUSTODY','OPENING_LAUNDRY_CLAIM','OPENING_LAUNDRY_UNINVOICED','OPENING_POCKET_USAGE','OPENING_POCKET_SEWING')
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
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type in('BRAND','SIZE','MODEL','PRODUCT','CUSTOMER','SUPPLIER','CONTRACTOR','ACCESSORY_CATEGORY','MATERIAL','MATERIAL_ROLL','OPEN_PO','LAUNDRY_VENDOR','LOCATION','CHART_ACCOUNT','CASH_ACCOUNT','OPENING_COST_ORIGIN','UNINVOICED_RECEIPT','OPENING_ADVANCE','LEGACY_DOCUMENT','OPENING_CUSTOMER_CREDIT','OPENING_SALE_RETURN','OPEN_PURCHASE_ORDER','OPENING_PAYROLL_ENTITLEMENT','OPENING_REWORK','OPENING_REWORK_COMPONENT','OPEN_SALES_DRAFT','OPENING_ACCESSORY_NOTE_LINE','OPENING_ACCESSORY_CUSTODY','OPENING_LAUNDRY_CLAIM','OPENING_LAUNDRY_UNINVOICED','OPENING_POCKET_USAGE','OPENING_POCKET_SEWING') and posted_entity_id is null) then raise exception 'Migration batch still has unapplied master/roll/open-PO rows';end if;
  select id into v_opening from erp.opening_balance_headers where migration_batch_id=p_batch_id order by created_at limit 1;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type in('OPENING_BALANCE_ITEM','MATERIAL_ROLL')) then
    if v_opening is null then raise exception 'Opening stock/balance rows exist but opening document was not prepared';end if;
    if (select status from erp.opening_balance_headers where id=v_opening)<>'POSTED' then raise exception 'Migration opening balance must be POSTED before finalizing batch';end if;
  end if;
  update erp.migration_batches set status='POSTED',posted_at=statement_timestamp(),error_message=null where id=p_batch_id;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason) values('migration_batches',p_batch_id,'POST',jsonb_build_object('status','POSTED'),erp.current_app_user_id(),'Finalize migration batch');
end;$function$;
CREATE OR REPLACE FUNCTION erp.save_initial_import_action_v1(p_action text, p_payload jsonb, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
 v_action text:=upper(btrim(p_action)); v_batch uuid; v_type text;
 b erp.migration_batches%rowtype; v_cached jsonb; v_result jsonb; v_row jsonb; v_normal jsonb;
 v_field text; v_text text; v_number numeric; v_line integer; v_seen integer[]:='{}';
 v_total bigint; v_valid bigint; v_errors bigint; v_opening uuid; v_date date;
 v_catalog constant jsonb:='{"LAUNDRY_VENDOR": {"label": "Vendor laundry", "required": ["vendor_code", "vendor_name"], "fields": {"vendor_code": "Kode laundry", "vendor_name": "Nama laundry", "phone": "Telepon", "is_active": "Aktif", "notes": "Catatan"}}, "LOCATION": {"label": "Lokasi dan gudang", "required": ["location_code", "location_name", "location_type"], "fields": {"location_code": "Kode lokasi", "location_name": "Nama lokasi", "location_type": "Jenis lokasi", "is_active": "Aktif"}}, "CHART_ACCOUNT": {"label": "Akun buku besar", "required": ["account_code", "account_name", "account_type", "report_group", "normal_balance"], "fields": {"account_code": "Kode akun", "account_name": "Nama akun", "account_type": "Jenis akun", "report_group": "Kelompok laporan", "normal_balance": "Saldo normal", "parent_account_code": "Kode akun induk", "is_postable": "Boleh dipakai jurnal", "is_active": "Aktif"}}, "CASH_ACCOUNT": {"label": "Rekening kas dan bank", "required": ["cash_account_code", "cash_account_name", "coa_account_code", "account_kind"], "fields": {"cash_account_code": "Kode kas bank", "cash_account_name": "Nama kas bank", "coa_account_code": "Kode akun buku besar", "account_kind": "Jenis rekening", "is_active": "Aktif"}}, "BRAND": {"label": "Merek", "required": ["brand_code", "brand_name"], "fields": {"brand_code": "Kode merek", "brand_name": "Nama merek", "is_active": "Aktif"}}, "SIZE": {"label": "Ukuran", "required": ["size_code"], "fields": {"size_code": "Kode ukuran", "sort_order": "Urutan", "is_active": "Aktif"}}, "MODEL": {"label": "Model produk", "required": ["model_code", "model_name"], "fields": {"model_code": "Kode model", "model_name": "Nama model", "description": "Keterangan", "is_active": "Aktif"}}, "PRODUCT": {"label": "Produk per ukuran", "required": ["sku", "product_name", "model_code", "brand_code", "color_name", "size_code"], "fields": {"sku": "Kode produk", "product_name": "Nama produk", "model_code": "Kode model", "brand_code": "Kode merek", "color_name": "Warna", "size_code": "Kode ukuran", "is_active": "Aktif"}}, "CUSTOMER": {"label": "Pelanggan", "required": ["customer_code", "customer_name"], "fields": {"customer_code": "Kode pelanggan", "customer_name": "Nama pelanggan", "phone": "Telepon", "address": "Alamat", "is_active": "Aktif"}}, "SUPPLIER": {"label": "Supplier", "required": ["supplier_code", "supplier_name"], "fields": {"supplier_code": "Kode supplier", "supplier_name": "Nama supplier", "supplier_type": "Jenis supplier", "phone": "Telepon", "address": "Alamat", "is_active": "Aktif"}}, "CONTRACTOR": {"label": "Mandor", "required": ["contractor_code", "contractor_name"], "fields": {"contractor_code": "Kode mandor", "contractor_name": "Nama mandor", "contractor_type": "Jenis mandor", "attendance_required": "Wajib absensi", "is_active": "Aktif", "notes": "Catatan"}}, "ACCESSORY_CATEGORY": {"label": "Kategori aksesori", "required": ["category_code", "category_name", "base_uom_code"], "fields": {"category_code": "Kode kategori", "category_name": "Nama kategori", "base_uom_code": "Satuan dasar", "is_active": "Aktif", "notes": "Catatan"}}, "MATERIAL": {"label": "Bahan dan aksesori", "required": ["material_sku", "material_name", "material_type", "unit_code"], "fields": {"material_sku": "Kode bahan", "material_name": "Nama bahan", "material_type": "Jenis bahan", "unit_code": "Satuan dasar", "accessory_category_code": "Kode kategori aksesori", "is_active": "Aktif"}}, "MATERIAL_ROLL": {"label": "Stok awal kain per roll", "required": ["material_sku", "roll_number", "opening_qty", "unit_cost", "location_code", "control_key"], "fields": {"material_sku": "Kode bahan", "roll_number": "Nomor roll", "opening_qty": "Jumlah awal", "unit_cost": "Biaya per satuan", "location_code": "Kode gudang", "supplier_code": "Kode supplier", "notes": "Catatan", "control_key": "Kode total pembanding", "opening_source_key": "Kode rincian stok asal"}}, "OPENING_BALANCE_ITEM": {"label": "Stok dan saldo awal", "required": ["balance_type", "control_key"], "fields": {"balance_type": "Jenis saldo", "material_sku": "Kode bahan", "product_sku": "Kode produk", "brand_code": "Kode merek", "model_code": "Kode model", "color_name": "Warna", "size_code": "Kode ukuran", "location_code": "Kode gudang", "contractor_code": "Kode mandor", "customer_code": "Kode pelanggan", "supplier_code": "Kode supplier", "vendor_code": "Kode laundry", "cash_account_code": "Kode kas bank", "stage": "Tahap produksi", "qty": "Jumlah", "unit_cost": "Biaya per satuan", "amount": "Nominal", "quality_grade": "Kualitas", "hpp_input_method": "Cara isi HPP", "hpp_percent_of_price": "Persentase HPP", "notes": "Catatan", "control_key": "Kode total pembanding", "document_number": "Nomor dokumen asal", "document_date": "Tanggal dokumen asal", "due_date": "Tanggal jatuh tempo", "original_amount": "Nominal dokumen awal", "settled_before_cutover": "Sudah dibayar sebelum saldo awal", "opening_source_key": "Kode rincian stok asal", "source_kind": "Jenis sumber saldo", "po_number": "Nomor PO saldo fisik", "accessory_cost_included": "Biaya aksesoris sudah termasuk (true/false)"}}, "OPEN_PO": {"label": "Pesanan produksi berjalan", "required": ["po_number", "model_code", "status", "current_stage"], "fields": {"po_number": "Nomor pesanan", "model_code": "Kode model", "contractor_code": "Kode mandor", "target_qty_pcs": "Target buah", "target_dozens": "Target lusin", "status": "Status", "current_stage": "Tahap produksi", "physical_start_at": "Waktu mulai fisik", "notes": "Catatan"}}, "OPENING_CONTROL": {"label": "Total pembanding saldo awal", "required": ["control_key", "balance_type", "amount"], "fields": {"control_key": "Kode total pembanding", "balance_type": "Jenis saldo", "qty": "Total jumlah", "amount": "Total nominal", "notes": "Catatan"}}, "UNINVOICED_RECEIPT": {"label": "Penerimaan belum ditagih — sisa bahan dan asal biaya", "required": ["receipt_number", "receipt_line_number", "receipt_date", "supplier_code", "material_sku", "location_code", "qty", "unit_cost", "control_key"], "fields": {"receipt_number": "Nomor penerimaan asal", "receipt_line_number": "Nomor baris penerimaan", "receipt_date": "Tanggal penerimaan asal", "supplier_code": "Kode supplier", "material_sku": "Kode bahan", "location_code": "Kode gudang", "qty": "Jumlah belum ditagih", "unit_cost": "Biaya estimasi per satuan", "opening_source_key": "Kode rincian stok asal", "control_key": "Kode total pembanding", "notes": "Catatan", "invoice_document_number": "Nomor invoice asal untuk bagian yang sudah ditagih", "invoiced_qty": "Jumlah yang sudah ditagih sebelum saldo awal"}}, "OPENING_ADVANCE": {"label": "Uang muka tersisa", "required": ["party_type", "party_code", "coa_account_code", "document_number", "document_date", "original_amount", "settled_before_cutover", "amount", "control_key"], "fields": {"party_type": "Jenis pihak", "party_code": "Kode pihak", "coa_account_code": "Kode akun uang muka", "document_number": "Nomor bukti uang muka", "document_date": "Tanggal uang muka", "original_amount": "Nominal asal", "settled_before_cutover": "Terpakai atau kembali sebelum saldo awal", "amount": "Sisa uang muka", "control_key": "Kode total pembanding"}}, "OPENING_COST_ORIGIN": {"label": "Asal biaya yang sudah terpakai sebelum cutover", "fields": {"supplier_code": "Kode supplier", "receipt_number": "Nomor penerimaan asal", "receipt_line_number": "Nomor baris penerimaan", "target_source_key": "Kode rincian WIP/BS/FG tujuan", "qty": "Jumlah bahan yang sudah terpakai", "notes": "Catatan"}, "required": ["supplier_code", "receipt_number", "receipt_line_number", "target_source_key", "qty"]}, "LEGACY_DOCUMENT": {"label": "Dokumen lama yang sudah lunas penuh", "required": ["balance_type", "party_code", "document_number", "document_date", "original_amount", "settled_before_cutover"], "fields": {"balance_type": "Jenis saldo dokumen", "party_code": "Kode pihak", "document_number": "Nomor dokumen asal", "document_date": "Tanggal dokumen asal", "original_amount": "Nominal dokumen awal", "settled_before_cutover": "Sudah dibayar sebelum saldo awal", "notes": "Catatan"}}, "OPENING_CUSTOMER_CREDIT": {"label": "Kredit retur pelanggan yang belum dikembalikan", "required": ["customer_code", "coa_account_code", "document_number", "document_date", "original_amount", "settled_before_cutover", "amount"], "fields": {"customer_code": "Kode pelanggan", "coa_account_code": "Kode akun kredit pelanggan", "document_number": "Nomor nota retur/kredit", "document_date": "Tanggal nota retur/kredit", "original_amount": "Nominal kredit asal", "settled_before_cutover": "Sudah dikembalikan sebelum saldo awal", "amount": "Sisa kredit", "notes": "Catatan"}}, "OPENING_SALE_RETURN": {"label": "Hak retur penjualan lama yang barangnya belum kembali", "required": ["customer_code", "return_number", "invoice_document_number", "product_sku", "qty", "credit_unit_price", "unit_cost", "credit_coa_account_code"], "fields": {"customer_code": "Kode pelanggan", "return_number": "Nomor persetujuan retur", "invoice_document_number": "Nomor invoice asal", "product_sku": "Kode produk", "brand_code": "Kode merek", "model_code": "Kode model", "color_name": "Warna", "size_code": "Kode ukuran", "qty": "Jumlah pcs boleh diretur", "credit_unit_price": "Kredit per pcs", "unit_cost": "Nilai persediaan per pcs", "credit_coa_account_code": "Kode akun kredit pelanggan", "notes": "Catatan"}}, "OPEN_PURCHASE_ORDER": {"label": "PO pembelian yang belum diterima penuh saat saldo awal", "required": ["po_number", "po_line_number", "po_date", "supplier_code", "location_code", "material_sku", "ordered_qty", "received_before_cutover_qty", "cancelled_before_cutover_qty", "remaining_qty", "unit_price"], "fields": {"po_number": "Nomor PO pembelian", "po_line_number": "Nomor baris PO", "po_date": "Tanggal PO", "supplier_code": "Kode supplier", "location_code": "Kode gudang tujuan", "material_sku": "Kode bahan", "ordered_qty": "Jumlah dipesan", "received_before_cutover_qty": "Sudah diterima sebelum saldo awal", "cancelled_before_cutover_qty": "Sudah dibatalkan sebelum saldo awal", "remaining_qty": "Sisa yang masih ditunggu", "unit_price": "Harga estimasi per satuan", "expected_date": "Perkiraan tanggal datang", "notes": "Catatan"}}, "OPENING_PAYROLL_ENTITLEMENT": {"label": "Hak upah, absensi, atau reimburse sebelum saldo awal yang belum disetujui", "required": ["kind", "contractor_code", "document_number", "line_number", "document_date", "rate"], "fields": {"kind": "Jenis hak (SEWING_WORK/ATTENDANCE/ACCESSORY_REIMBURSEMENT)", "contractor_code": "Kode mandor", "document_number": "Nomor dokumen hutang mandor", "line_number": "Nomor baris", "document_date": "Tanggal hak timbul", "rate": "Tarif", "po_number": "Nomor PO (upah jahit)", "work_component_code": "Kode komponen kerja", "earned_qty": "Jumlah dikerjakan", "paid_before_qty": "Jumlah sudah dibayar sebelum saldo awal", "carry_qty": "Jumlah komponen dibawa (carry)", "worker_name": "Nama pekerja (absensi)", "period_start": "Awal periode absensi", "period_end": "Akhir periode absensi", "days": "Jumlah hari dibayar", "category_code": "Kode kategori aksesori", "good_qty": "Jumlah GOOD", "paid_before_amount": "Nominal sudah dibayar sebelum saldo awal", "notes": "Catatan"}}, "OPENING_REWORK": {"label": "Rework yang masih di mandor atau laundry saat saldo awal", "required": ["rework_number", "bs_source_key", "destination_type", "sent_date", "qty_sent_original", "qty_returned_before_cutover", "qty_open"], "fields": {"rework_number": "Nomor rework asal", "bs_source_key": "Kode rincian BS asal (opening_source_key baris BS)", "destination_type": "Tujuan rework (CONTRACTOR/LAUNDRY)", "contractor_code": "Kode mandor rework", "vendor_code": "Kode laundry rework", "sent_date": "Tanggal kirim rework", "qty_sent_original": "Jumlah dikirim", "qty_returned_before_cutover": "Sudah kembali sebelum saldo awal", "qty_open": "Masih di rework saat saldo awal", "notes": "Catatan"}}, "OPENING_REWORK_COMPONENT": {"label": "Komponen upah rework terbuka", "required": ["rework_number", "work_component_code", "completed_before_bs_qty", "qty_performed", "rate_per_pcs"], "fields": {"rework_number": "Nomor rework asal", "work_component_code": "Kode komponen kerja", "completed_before_bs_qty": "Pcs yang komponennya sudah selesai sebelum BS", "qty_performed": "Pcs yang akan dikerjakan", "rate_per_pcs": "Tarif per pcs"}}, "OPEN_SALES_DRAFT": {"label": "Draf penjualan yang masih terbuka saat saldo awal (dengan reservasi)", "required": ["draft_number", "line_number", "draft_date", "customer_code", "location_code", "product_sku", "qty_pcs", "unit_price"], "fields": {"draft_number": "Nomor draf penjualan", "line_number": "Nomor baris draf", "draft_date": "Tanggal draf lama", "customer_code": "Kode pelanggan", "location_code": "Kode gudang barang jadi", "product_sku": "Kode produk", "qty_pcs": "Jumlah pcs yang direservasi", "unit_price": "Harga per pcs", "discount_amount": "Potongan baris", "due_date": "Jatuh tempo", "payment_terms": "Syarat pembayaran", "notes": "Catatan"}}, "OPENING_ACCESSORY_NOTE_LINE": {"label": "Baris nota aksesori mandor lama (di balik piutang mandor saldo awal)", "required": ["document_number", "contractor_code", "line_number", "material_sku", "qty", "line_amount"], "fields": {"document_number": "Nomor nota lama (sama dengan dokumen piutang mandor)", "contractor_code": "Kode mandor", "line_number": "Nomor baris nota", "material_sku": "Kode aksesori", "qty": "Jumlah (PCS utuh untuk aksesori hitung)", "line_amount": "Nominal baris nota asal", "notes": "Catatan"}}, "OPENING_ACCESSORY_CUSTODY": {"label": "Aksesori yang bukan stok siap pakai: titipan belum dinilai, belum kembali, titipan pelanggan", "required": ["custody_kind", "custody_key", "qty"], "fields": {"custody_kind": "Jenis (PENDING_VALUE, UNRETURNED, CUSTOMER_GARMENT)", "custody_key": "Kode opname (satu barang fisik satu kode)", "material_sku": "Kode aksesori", "location_code": "Kode area pemeriksaan (PENDING_VALUE)", "condition": "Kondisi (WAITING, USABLE, DAMAGED)", "qty": "Jumlah PCS", "holder": "Pemegang (UNRETURNED)", "owner_kind": "Pemilik (COMPANY atau CUSTOMER)", "customer_code": "Kode pelanggan (CUSTOMER_GARMENT)", "product_sku": "Kode produk (opsional)", "description": "Keterangan barang", "notes": "Catatan", "count_sheet": "Nomor lembar hitung sumber (D09: isi bersama baris lembar, atau pakai lot sumber)", "sheet_line": "Baris/item di lembar hitung", "source_lot": "Lot sumber (pengganti lembar hitung + baris)"}}, "OPENING_LAUNDRY_CLAIM": {"label": "Klaim laundry yang terdokumentasi atas WIP di vendor (hilang, tertahan, rusak)", "required": ["claim_number", "source_key", "vendor_code", "claim_type", "qty", "claim_date"], "fields": {"claim_number": "Nomor klaim", "source_key": "Kode rincian WIP laundry (opening_source_key)", "vendor_code": "Kode laundry (sama dengan pemegang WIP)", "claim_type": "Jenis klaim (MISSING, STUCK, DAMAGE)", "qty": "Jumlah PCS yang diklaim", "claim_date": "Tanggal klaim (sebelum atau pada tanggal saldo awal)", "dispatch_number": "Nomor kirim laundry lama", "notes": "Catatan"}}, "OPENING_LAUNDRY_UNINVOICED": {"label": "Hasil laundry yang sudah kembali sebelum cutover tetapi belum ditagih vendor", "required": ["document_number", "vendor_code", "receipt_date", "category", "qty"], "fields": {"document_number": "Nomor terima laundry lama", "vendor_code": "Kode laundry", "receipt_date": "Tanggal terima (sebelum atau pada tanggal saldo awal)", "category": "Kategori tagihan (GOOD, BS, FAILED_ATTEMPT)", "qty": "Jumlah PCS belum ditagih", "estimated_amount": "Estimasi tagihan yang terbukti (kosong = belum diketahui)", "po_number": "Nomor PO asal", "dispatch_number": "Nomor kirim laundry lama", "notes": "Catatan"}}, "OPENING_POCKET_USAGE": {"label": "Kain kantong keluar sebelum cutover", "required": ["document_number", "line_number", "physical_date", "material_sku", "qty", "amount", "allocation_status", "control_key", "control_qty", "control_amount"], "fields": {"document_number": "Nomor lembar pengeluaran asal", "line_number": "Baris asal", "physical_date": "Tanggal keluar sebelum cutover", "material_sku": "Kode bahan", "qty": "Jumlah kain sudah keluar", "amount": "Nilai historis", "allocation_status": "ALLOCATED / UNALLOCATED", "prior_allocation_reference": "Referensi pembagian lama (ALLOCATED)", "control_key": "Identitas total pembanding", "control_qty": "Total jumlah pada lembar pembanding", "control_amount": "Total nilai pada lembar pembanding", "notes": "Catatan", "supplier_code": "Supplier penerimaan belum ditagih (opsional)", "receipt_number": "Nomor penerimaan asal (opsional)", "receipt_line_number": "Baris penerimaan asal (opsional)"}}, "OPENING_POCKET_SEWING": {"label": "Hasil jahit sebelum cutover untuk pembagian kain kantong", "required": ["document_number", "line_number", "physical_date", "contractor_code", "qty", "target_kind", "control_key", "control_qty"], "fields": {"document_number": "Nomor lembar hasil jahit", "line_number": "Baris asal", "physical_date": "Tanggal selesai dijahit sebelum cutover", "contractor_code": "Kode mandor (termasuk khusus)", "qty": "PCS selesai dijahit", "target_kind": "WIP / BS / FINISHED_GOODS / COGS", "target_source_key": "Kode rincian stok awal tujuan", "product_sku": "SKU yang sudah terjual (COGS)", "sold_reference": "Bukti penjualan historis (COGS)", "notes": "Catatan", "control_key": "Identitas total hasil jahit pembanding", "control_qty": "Total PCS pada lembar pembanding"}}}'::jsonb;
begin
 perform erp.require_owner_admin();
 perform erp.require_permission('settings.erp.view');
 if v_action is null or v_action not in('CREATE','SAVE_FILE','VALIDATE','FINALIZE','ALLOCATE_CASH_ADVANCE','PREPAYMENT','WIP_OUTPUT','OPENING_SETTLEMENT','CUSTOMER_CREDIT','OPENING_RETURN','PURCHASE_COMMITMENT','PAYROLL_ENTITLEMENT') then raise exception 'Aksi impor tidak dikenal'; end if;
 if p_payload is null or jsonb_typeof(p_payload)<>'object' or octet_length(p_payload::text)>5242880 then
   raise exception 'Isi impor harus berupa objek dan maksimal 5 MB'; end if;
 -- AR: same lock order as native prepare/post, before any batch lock.
 if v_action='WIP_OUTPUT' then perform erp.pocket_period_lock_v1();end if;
 if v_action in('FINALIZE','WIP_OUTPUT','OPENING_RETURN') then
   perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 end if;
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
 elsif v_action in('OPENING_SETTLEMENT','CUSTOMER_CREDIT','OPENING_RETURN','PURCHASE_COMMITMENT','PAYROLL_ENTITLEMENT') then
   -- BB: continuations of a posted import (ALL-P02/S01/S03/Y01), one transaction and one request identity each.
   v_batch:=(p_payload->>'batch_id')::uuid;
   select * into b from erp.migration_batches where id=v_batch for update;
   if b.id is null or b.status<>'POSTED' then raise exception 'BB_IMPORT_NOT_POSTED: lanjutan hanya untuk impor yang sudah disahkan';end if;
   if p_payload->>'expected_revision' is distinct from erp.initial_import_revision_v1(b.id) then
     raise exception 'STALE_VERSION: saldo impor berubah; muat ulang sebelum melanjutkan';end if;
   v_result:=case v_action when 'OPENING_SETTLEMENT' then erp.bb_manage_opening_settlement_v1(p_payload,p_client_request_id)
     when 'CUSTOMER_CREDIT' then erp.bb_manage_customer_credit_v1(p_payload,p_client_request_id)
     when 'PURCHASE_COMMITMENT' then erp.bb_manage_purchase_commitment_v1(p_payload,p_client_request_id)
     when 'PAYROLL_ENTITLEMENT' then erp.bb_manage_payroll_entitlement_v1(p_payload,p_client_request_id)
     else erp.bb_manage_opening_sale_return_v1(p_payload,p_client_request_id) end;
   v_result:=v_result||jsonb_build_object('request_id',p_client_request_id,'action',v_action,'batch_id',v_batch,'status','POSTED',
     'revision',erp.initial_import_revision_v1(v_batch));
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
         if v_field in('qty','opening_qty','unit_cost','amount','original_amount','settled_before_cutover','hpp_percent_of_price','target_dozens','target_qty_pcs','sort_order','credit_unit_price','invoiced_qty') and v_text<>'' then
           if v_text !~ '^-?[0-9]+([.,][0-9]+)?$' then
             raise exception 'Baris %, kolom %: isi angka tanpa pemisah ribuan',v_line,v_field; end if;
           v_text:=replace(v_text,',','.');v_number:=v_text::numeric;
           if (v_field in('amount','original_amount','settled_before_cutover','credit_unit_price') and v_number<>round(v_number,2))
             or (v_field in('qty','opening_qty','unit_cost','target_dozens','invoiced_qty') and v_number<>round(v_number,6))
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
     perform erp.be_validate_pocket_imports_v1(b.id);
     perform erp.validate_initial_import_receipts_v1(b.id);
     perform erp.validate_initial_prepayments_v1(b.id);
     perform erp.bb_validate_financial_imports_v1(b.id);
     perform erp.bb_validate_purchase_imports_v1(b.id);
     perform erp.bb_validate_labour_imports_v1(b.id);
     perform erp.bb_validate_production_imports_v1(b.id);
     perform erp.bb_validate_sales_imports_v1(b.id);
     perform erp.bc_validate_imports_v1(b.id);
     perform erp.bd_validate_imports_v1(b.id);
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
       perform erp.bb_apply_financial_imports_v1(b.id);
       perform erp.bb_apply_purchase_imports_v1(b.id);
       perform erp.bb_apply_labour_imports_v1(b.id);
       perform erp.bb_apply_production_imports_v1(b.id);
       perform erp.bb_apply_sales_imports_v1(b.id);
       perform erp.bc_apply_imports_v1(b.id);
       perform erp.bd_apply_imports_v1(b.id);
       perform erp.be_apply_pocket_imports_v1(b.id);
       perform erp.finalize_migration_batch(b.id);
     end if;
   end if;
 end if;
 v_result:=jsonb_build_object('request_id',p_client_request_id,'action',v_action,'batch_id',v_batch,
   'status',(select status from erp.migration_batches where id=v_batch),'total_rows',v_total,
   'valid_rows',v_valid,'error_rows',v_errors,'revision',erp.initial_import_revision_v1(v_batch));
 return erp._idempotency_complete('save_initial_import_action_v1',p_client_request_id,v_result);
end;$function$;
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
       ) x),'[]'::jsonb),
     'prepayments',coalesce((select jsonb_agg(erp.initial_prepayment_state_v1(a.id)||jsonb_build_object(
       'party_name',case a.party_type when 'SUPPLIER' then (select supplier_name from erp.suppliers where id=a.party_id)
         when 'CUSTOMER' then (select customer_name from erp.customers where id=a.party_id) else (select vendor_name from erp.laundry_vendors where id=a.party_id) end,
       'targets',coalesce((select jsonb_agg(to_jsonb(t) order by t.target_date,t.id) from (
         select * from erp.initial_prepayment_targets_v1(a.id) where remaining_amount::numeric>0) t),'[]'::jsonb),
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
   -- BB: opening balances with their settlements and payroll lines, customer credits, return rights, legacy documents.
   v_batch:=v_batch||erp.bb_financial_workspace_v1(b.id)||erp.bb_purchase_workspace_v1(b.id)||erp.bb_labour_workspace_v1(b.id)||erp.bb_production_workspace_v1(b.id)||erp.bb_sales_workspace_v1(b.id)||erp.bc_import_workspace_v1(b.id)||erp.bd_import_workspace_v1(b.id)||erp.be_pocket_import_workspace_v1(b.id);
 end if;
 -- BA (audit A5, CP6-04): every batch not posted yet stays listed (an older editable draft is never cut off), with
 -- the latest 50 of any status.
 return jsonb_build_object('batch',v_batch,'recent',coalesce((select jsonb_agg(x order by x.created_at desc,x.id)
   from (select id,batch_code,status,cutover_at,created_at from erp.migration_batches where status<>'POSTED'
     union select * from (select id,batch_code,status,cutover_at,created_at from erp.migration_batches
       order by created_at desc,id limit 50) latest) x),'[]'::jsonb));
end;$function$;
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
     where h.migration_batch_id=p_batch_id),'[]'::jsonb),
   'bb',erp.bb_financial_revision_part_v1(p_batch_id),
   'bb_purchase',erp.bb_purchase_revision_part_v1(p_batch_id),
   'bb_labour',erp.bb_labour_revision_part_v1(p_batch_id),
   'bb_production',erp.bb_production_revision_part_v1(p_batch_id),
   'bc',erp.bc_import_revision_part_v1(p_batch_id),
   'bd',erp.bd_import_revision_part_v1(p_batch_id),'be',erp.be_pocket_import_workspace_v1(p_batch_id)
 )::text,'UTF8'),'sha256'),'hex');
$function$;
create or replace function erp.pocket_period_total_v1(p_pool uuid) returns numeric
language sql stable security definer set search_path='' as $function$
 select coalesce(sum(case when s.historical_usage_id is not null then erp.be_pocket_usage_amount_v1(s.historical_usage_id) else -((erp._cp6_material_adjustment_revaluation_state(s.adjustment_id)->>'current_value')::numeric) end),0)::numeric(20,2)
 from erp.pocket_period_sources s where s.pool_id=p_pool;
$function$;
create or replace function erp.pocket_period_manifest_v1(p_start date,p_end date) returns jsonb
language sql stable security definer set search_path='' set TimeZone='UTC' as $function$
 with sources as(
  select u.adjustment_id,null::uuid historical_usage_id,h.row_version::text version,erp._cp3_business_date(h.physical_at) date,
   u.material_id,u.roll_id,u.issued_quantity::text quantity,
   (-((erp._cp6_material_adjustment_revaluation_state(h.id)->>'current_value')::numeric))::numeric(20,2)::text amount
  from erp.pocket_fabric_usage u join erp.material_adjustments h on h.id=u.adjustment_id
  where h.status='POSTED' and erp._cp3_business_date(h.physical_at) between p_start and p_end
  union all select null::uuid,u.id,erp.be_pocket_usage_amount_v1(u.id)::text,u.physical_date,u.material_id,null::uuid,u.material_qty::text,erp.be_pocket_usage_amount_v1(u.id)::numeric(20,2)::text
  from erp.be_pocket_usage_v1 u where u.allocation_status='UNALLOCATED' and u.physical_date between p_start and p_end
 ), native_destinations as(
  select e.id event_id,null::uuid historical_sewing_id,e.physical_at,0 sort_kind,e.po_id,e.contractor_id,e.cutting_group_id,e.qty_signed::bigint sewing_qty,
   to_jsonb(e) source_snapshot
  from erp.sewing_terminal_events e join erp.work_completion_events w on w.id=e.source_work_completion_id
  where e.event_kind='SELESAI_DIJAHIT' and e.qty_signed>0 and w.status='POSTED'
   and erp._cp3_business_date(e.physical_at) between p_start and p_end
   and not exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=e.id)
 ), all_destinations as(
  select * from native_destinations
  union all select null::uuid,s.id,s.physical_date::timestamp at time zone 'Asia/Jakarta',case s.target_kind when 'FINISHED_GOODS' then 1 when 'COGS' then 2 else 3 end,
   s.po_id,s.contractor_id,null::uuid,s.qty,to_jsonb(s)
  from erp.be_pocket_sewing_v1 s where s.physical_date between p_start and p_end
 ), destinations as(
  select event_id,historical_sewing_id,po_id,contractor_id,cutting_group_id,sewing_qty,
   coalesce(sum(sewing_qty) over(order by physical_at,sort_kind,coalesce(event_id,historical_sewing_id) rows between unbounded preceding and 1 preceding),0)::bigint preceding_qty,source_snapshot
  from all_destinations
 ) select jsonb_build_object('period_start',p_start,'period_end',p_end,
  'sources',coalesce((select jsonb_agg(to_jsonb(s) order by coalesce(adjustment_id,historical_usage_id)) from sources s),'[]'::jsonb),
  'destinations',coalesce((select jsonb_agg(to_jsonb(d) order by preceding_qty,coalesce(event_id,historical_sewing_id)) from destinations d),'[]'::jsonb),
  'amount',coalesce((select sum(amount::numeric) from sources),0)::numeric(20,2)::text,
  'quantity',coalesce((select sum(sewing_qty) from destinations),0)::bigint::text,
  'blocked_by',coalesce((select jsonb_agg(p.id order by p.id) from erp.pocket_periods p
   where erp.pocket_period_active_v1(p.id) and p.period_start<=p_end and p.period_end>=p_start),'[]'::jsonb));
$function$;
create or replace function erp.pocket_period_target_v1(p_pool uuid,p_cancel boolean default false) returns jsonb
language sql stable security definer set search_path='' as $function$
 with values_by_key as(
  select case when s.target_kind='FINISHED_GOODS' then 'OPENING_EQUITY' when s.target_kind='COGS' then 'COGS' else 'WIP|'||d.po_id::text end key,
   sum(erp.pocket_period_amount_v1(d.pool_id,d.preceding_qty,d.sewing_qty)) amount
  from erp.pocket_period_destinations d left join erp.be_pocket_sewing_v1 s on s.id=d.historical_sewing_id where d.pool_id=p_pool group by 1
  union all select 'OTHER_EXPENSE',-erp.pocket_period_total_v1(p_pool)
 ) select case when p_cancel or not erp.pocket_period_active_v1(p_pool) then '{}'::jsonb else
 coalesce((select jsonb_object_agg(key,amount) from values_by_key where amount<>0),'{}'::jsonb) end;
$function$;
create or replace function erp.pocket_period_book_v1(p_pool uuid) returns jsonb
language sql stable security definer set search_path='' as $function$
 with sums as(
  select case when l.account_id=erp.account_id('WIP') and l.po_id is not null then 'WIP|'||l.po_id::text
   when l.account_id=erp.account_id('OTHER_EXPENSE') and l.po_id is null then 'OTHER_EXPENSE'
   when l.account_id=erp.account_id('OPENING_EQUITY') and l.po_id is null then 'OPENING_EQUITY'
   when l.account_id=erp.account_id('COGS') and l.po_id is null then 'COGS'
   else 'INVALID|'||l.account_id::text||'|'||coalesce(l.po_id::text,'') end key,sum(l.debit-l.credit) amount
  from erp.pocket_period_events e join erp.journal_entries j on j.id=e.journal_entry_id
   join erp.journal_lines l on l.journal_entry_id=j.id where e.pool_id=p_pool group by 1
 ) select coalesce(jsonb_object_agg(key,amount) filter(where amount<>0),'{}'::jsonb) from sums;
$function$;
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
 perform erp.be_pocket_sync_targets_v1(p_pool,p_date,p_kind='CANCEL');
 for v_po in select distinct po_id from erp.pocket_period_destinations where pool_id=p_pool and po_id is not null order by po_id loop
  perform erp.rebuild_po_hpp(v_po,p_reason);perform erp.propagate_conversion_hpp_for_po(v_po);
  perform erp.sync_po_hpp_to_gl(v_po,p_date);
  if exists(select 1 from erp.production_orders where id=v_po and status='FINISHED') then
   perform erp.sync_finished_po_wip_residual(v_po,coalesce(v_book_date,p_date),p_reason);end if;
 end loop;
 if erp.pocket_period_book_v1(p_pool) is distinct from target then raise exception 'Pocket allocation ledger mismatch';end if;
end;$function$;
create or replace function erp.save_pocket_period_action_v1(p_action text,p_payload jsonb,p_request uuid) returns jsonb
language plpgsql security definer set search_path='' set TimeZone='UTC' set DateStyle='ISO, YMD' as $function$
declare cached jsonb;m jsonb;v jsonb;r jsonb;ident uuid;start_day date;end_day date;reason text;post_day date;
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
  m:=erp.pocket_period_manifest_v1(start_day,end_day);post_day:=erp.be_pocket_period_post_date_v1(m,end_day);
  if exists(select 1 from jsonb_array_elements(m->'sources') x where x->>'adjustment_id' is not null)
   or exists(select 1 from jsonb_array_elements(m->'destinations') x where x->>'event_id' is not null) then
   perform erp._cp3_lock_business_period(start_day,end_day);end if;
  perform erp._cp3_lock_business_period(post_day,post_day);ident:=gen_random_uuid();
  insert into erp.pocket_periods(id,period_start,period_end,manifest,denominator,original_amount,reason,created_by)
  values(ident,start_day,end_day,m,(m->>'quantity')::bigint,(m->>'amount')::numeric,reason,erp.current_app_user_id());
  insert into erp.pocket_period_sources(pool_id,adjustment_id,historical_usage_id,original_amount)
  select ident,(x->>'adjustment_id')::uuid,(x->>'historical_usage_id')::uuid,(x->>'amount')::numeric from jsonb_array_elements(m->'sources') x;
  insert into erp.pocket_period_destinations(pool_id,event_id,historical_sewing_id,po_id,contractor_id,cutting_group_id,sewing_qty,preceding_qty,source_snapshot)
  select ident,(x->>'event_id')::uuid,(x->>'historical_sewing_id')::uuid,(x->>'po_id')::uuid,(x->>'contractor_id')::uuid,(x->>'cutting_group_id')::uuid,
   (x->>'sewing_qty')::bigint,(x->>'preceding_qty')::bigint,x->'source_snapshot' from jsonb_array_elements(m->'destinations') x;
  perform erp.sync_pocket_period_v1(ident,post_day,'POST',reason);
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
create or replace function erp.initial_import_source_value_v1(p_item uuid) returns numeric
language sql stable security definer set search_path='' as $function$
 select round(coalesce(i.amount,i.qty*i.unit_cost_snapshot,0),2)+coalesce((
  select sum(e.new_delta-e.previous_delta) from erp.initial_import_origin_cost_events e where e.opening_item_id=i.id),0)
 +erp.be_pocket_opening_extra_v1(i.id)
 from erp.opening_balance_items i where i.id=p_item;
$function$;
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
  or exists(select 1 from erp.pocket_period_destinations d join erp.be_pocket_sewing_v1 s on s.id=d.historical_sewing_id where d.pool_id=p.id and to_jsonb(s)<>d.source_snapshot)
 union all select 'AP_PERIOD_POCKET_OVERLAP','CRITICAL',count(*),'Active allocation periods never overlap'
 from erp.pocket_periods p join erp.pocket_periods q on p.id<q.id and p.period_start<=q.period_end and p.period_end>=q.period_start
 where erp.pocket_period_active_v1(p.id) and erp.pocket_period_active_v1(q.id)
 union all select 'AP_PERIOD_POCKET_HPP','CRITICAL',count(*),'Current lot HPP includes the exact period source share'
 from erp.fg_lots l join erp.hpp_versions h on h.lot_id=l.id and h.is_current
 where l.lot_origin='PRODUCTION' and exists(select 1 from erp.pocket_period_destinations d where d.po_id=l.po_id)
 and abs(erp.pocket_lot_cost_v1(l.id)-coalesce((select sum(c.total_cost) from erp.hpp_version_components c
  where c.hpp_version_id=h.id and c.source_type='POCKET_PERIOD_ALLOCATION'),0))>0.000001;
$function$;
create or replace function erp.save_pocket_fabric_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
returns jsonb language plpgsql security definer set search_path='' set TimeZone='UTC' set DateStyle='ISO, YMD' as $function$
declare v_action text:=upper(btrim(p_action));v_cached jsonb;v_result jsonb;v_reason text;v_mode text;
 v_material uuid;v_roll uuid;v_location uuid;v_id uuid;v_stock numeric;v_input numeric;v_qty numeric;v_date date;
 v_revision text;v_native jsonb;h erp.material_adjustments%rowtype;u erp.pocket_fabric_usage%rowtype;
begin
 perform erp.require_owner_admin();perform erp.require_permission('warehouse.stock.adjust');
 if v_action='CORRECT_OPENING_USAGE' then return erp.be_correct_pocket_usage_v1(p_payload,p_client_request_id);end if;
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
create or replace function erp.preview_pocket_period_v1(p_start date,p_end date) returns jsonb
language plpgsql stable security definer set search_path='' set TimeZone='UTC' as $function$
declare m jsonb;q numeric;v numeric;
begin
 perform erp.require_owner_admin();perform erp.require_permission('warehouse.stock.adjust');perform erp.require_permission('finance.hpp.manage');
 if p_start is null or p_end is null or p_end<p_start or p_end-p_start>366
  or p_end>erp._cp3_business_date(statement_timestamp()) then raise exception 'Pilih periode yang valid, maksimal 367 hari sampai hari ini';end if;
 m:=erp.pocket_period_manifest_v1(p_start,p_end);q:=(m->>'quantity')::numeric;v:=(m->>'amount')::numeric;
 return jsonb_build_object('period_start',p_start,'period_end',p_end,'economic_date',erp.be_pocket_period_post_date_v1(m,p_end),'amount',m->>'amount','quantity',m->>'quantity',
  'source_count',jsonb_array_length(m->'sources'),'per_piece',(case when q>0 then v/q else 0 end)::numeric(24,6)::text,
  'blocked',jsonb_array_length(m->'blocked_by')>0,'can_post',q>0 and v>0 and jsonb_array_length(m->'blocked_by')=0,
  'revision',encode(extensions.digest(convert_to(m::text,'UTF8'),'sha256'),'hex'));
end;$function$;
do $grants$
declare t text;f text;
begin
 foreach t in array array['be_execution_context_v1','be_conversion_sources_v1','be_conversion_returns_v1',
   'be_conversion_cost_sources_v1','be_conversion_cost_events_v1','be_nonpo_transfer_events_v1','be_rework_targets_v1','be_redye_services_v1','be_redye_price_events_v1','be_pocket_usage_v1','be_pocket_sewing_v1','be_pocket_source_events_v1','be_pocket_target_events_v1','be_pocket_receipt_origins_v1'] loop
   execute format('alter table erp.%I enable row level security',t);
   execute format('revoke all on erp.%I from public,anon,authenticated,service_role',t);
 end loop;
 for f in select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace
   where n.nspname='erp' and (p.proname like 'be\_%' or p.proname in('save_product_conversion_action_v1','get_product_conversion_workspace_v1')) loop
   execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
 end loop;
end $grants$;
revoke all on function public.erp_save_product_conversion_action_v1(text,jsonb,uuid) from public,anon;
revoke all on function public.erp_get_product_conversion_workspace_v1(jsonb) from public,anon;
grant execute on function public.erp_save_product_conversion_action_v1(text,jsonb,uuid) to authenticated,service_role;
grant execute on function public.erp_get_product_conversion_workspace_v1(jsonb) to authenticated,service_role;

insert into erp.schema_migrations(version,description) values('v2.6.20be','Physical SKU conversion with sourced cost and recovery; rework/redye target identity; real redye invoices; historical pocket sources and denominator');
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule','cp6_v2620ay_rollback_capsule','cp6_v2620az_rollback_capsule','cp6_v2620ba_rollback_capsule','cp6_v2620bb_rollback_capsule','cp6_v2620bc_rollback_capsule','cp6_v2620bd_rollback_capsule','cp6_v2620be_rollback_capsule')
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
  raise exception 'BE_INSTALLED_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
update erp.cp6_v2620be_rollback_capsule set installed_definition_sha256=encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex');
do $after_data$ declare v_table text;v_hash jsonb;v_after jsonb;v_before jsonb;v_cmp jsonb;v_cols text[];v_nonnull bigint; begin
 v_after:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620be_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_after:=v_after||jsonb_build_object(v_table,v_hash);
 end loop;
 select snapshot->'before' into v_before from pg_temp.cp6_release_boundary;
 v_cmp:=v_after;
 select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')), count(*) filter(where bad) into v_hash,v_nonnull
 from(select encode(extensions.digest(convert_to((to_jsonb(t)-array['rework_service_id']::text[])::text,'UTF8'),'sha256'),'hex') h,(rework_service_id is not null) bad from erp.bd_laundry_invoice_lines_v1 t)s;
 if v_nonnull<>0 then raise exception 'BE_ADDED_COLUMN_DERIVATION: bd_laundry_invoice_lines_v1';end if;
 v_cmp:=v_cmp||jsonb_build_object('bd_laundry_invoice_lines_v1',v_hash);
 select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')), count(*) filter(where bad) into v_hash,v_nonnull
 from(select encode(extensions.digest(convert_to((to_jsonb(t)-array['historical_sewing_id','id']::text[])::text,'UTF8'),'sha256'),'hex') h,(historical_sewing_id is not null or id is distinct from coalesce(event_id,historical_sewing_id)) bad from erp.pocket_period_destinations t)s;
 if v_nonnull<>0 then raise exception 'BE_ADDED_COLUMN_DERIVATION: pocket_period_destinations';end if;
 v_cmp:=v_cmp||jsonb_build_object('pocket_period_destinations',v_hash);
 select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')), count(*) filter(where bad) into v_hash,v_nonnull
 from(select encode(extensions.digest(convert_to((to_jsonb(t)-array['historical_usage_id','id']::text[])::text,'UTF8'),'sha256'),'hex') h,(historical_usage_id is not null or id is distinct from coalesce(adjustment_id,historical_usage_id)) bad from erp.pocket_period_sources t)s;
 if v_nonnull<>0 then raise exception 'BE_ADDED_COLUMN_DERIVATION: pocket_period_sources';end if;
 v_cmp:=v_cmp||jsonb_build_object('pocket_period_sources',v_hash);
 if (v_cmp-array['be_execution_context_v1','be_conversion_sources_v1','be_conversion_returns_v1','be_conversion_cost_sources_v1','be_conversion_cost_events_v1','be_nonpo_transfer_events_v1','be_rework_targets_v1','be_redye_services_v1','be_redye_price_events_v1','be_pocket_usage_v1','be_pocket_sewing_v1','be_pocket_source_events_v1','be_pocket_target_events_v1','be_pocket_receipt_origins_v1']::text[]) is distinct from v_before or exists(select 1 from unnest(array['be_execution_context_v1','be_conversion_sources_v1','be_conversion_returns_v1','be_conversion_cost_sources_v1','be_conversion_cost_events_v1','be_nonpo_transfer_events_v1','be_rework_targets_v1','be_redye_services_v1','be_redye_price_events_v1','be_pocket_usage_v1','be_pocket_sewing_v1','be_pocket_source_events_v1','be_pocket_target_events_v1','be_pocket_receipt_origins_v1']::text[]) t where (v_after->t->>'count') is distinct from '0')
  then raise exception 'BE_INSTALL_CHANGED_DATA';end if;
 if exists(with live as (select p.oid::regprocedure::text as identity,encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') as definition_sha256,
  array(select a::text from unnest(p.proacl)a order by a::text) as acl,pg_get_userbyid(p.proowner) as owner
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p')) select 1 from pg_temp.cp6_release_functions f left join live x on x.identity=f.identity
  where f.identity<>all(coalesce((select array_agg(object_regidentity) from erp.cp6_v2620be_rollback_capsule),'{}'))
  and (x.identity is null or (x.definition_sha256,x.acl,x.owner) is distinct from (f.definition_sha256,f.acl,f.owner)))
  then raise exception 'BE_CAPSULE_INCOMPLETE';end if;
 update erp.cp6_v2620be_rollback_capsule set boundary_snapshot=(select snapshot from pg_temp.cp6_release_boundary)||jsonb_build_object('after',v_after);
end $after_data$;
do $capsule_guard$
declare expected jsonb;actual jsonb;boundary jsonb;
begin
 if not exists(select 1 from pg_class where oid='erp.cp6_v2620be_rollback_capsule'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='erp.cp6_v2620be_rollback_capsule'::regclass and a.grantee<>p.relowner)
   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='erp.cp6_v2620be_rollback_capsule'::regclass and a.grantee<>'postgres'::regrole)
   or exists(select 1 from pg_policy where polrelid='erp.cp6_v2620be_rollback_capsule'::regclass)
   or exists(select 1 from pg_trigger where tgrelid='erp.cp6_v2620be_rollback_capsule'::regclass and not tgisinternal)
   or (select count(*) from erp.cp6_v2620be_rollback_capsule)<>49 then raise exception 'BE_CAPSULE_SECURITY_OR_COUNT';end if;
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620an_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620an_rollback_capsule'::regclass)) into expected;
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620be_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620be_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620be_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620be_rollback_capsule'::regclass)) into actual;
 if actual is distinct from expected then raise exception 'BE_CAPSULE_SHAPE_DRIFT';end if;
 select boundary_snapshot into boundary from erp.cp6_v2620be_rollback_capsule limit 1;
 if 49>0 and (boundary is null or exists(select 1 from erp.cp6_v2620be_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before'])) then raise exception 'BE_CAPSULE_BOUNDARY';end if;
 if exists(select 1 from erp.cp6_v2620be_rollback_capsule where object_regidentity<>all(array['erp.post_product_conversion(uuid)','erp.propagate_conversion_hpp_for_po(uuid)','erp.compute_po_hpp_gl_targets_v2620d(uuid)','erp.bc_value_custody_v1(jsonb,uuid)','erp.bc_reverse_v1(jsonb,uuid)','erp.sync_material_cost_revaluation(uuid)','erp.run_v268_financial_report_checks()','erp.reverse_product_conversion(uuid,text)','erp.compute_non_po_product_hpp_targets_v2620f(uuid)','erp.compute_non_po_product_hpp_book_v2620f(uuid)','erp.assert_non_po_product_hpp_target_book_v2620f(uuid)','erp.sync_non_po_product_hpp_to_gl_v2620f(uuid,date,text,uuid,text)','erp.post_rework_completion(uuid)','erp.reverse_rework_completion(uuid,text)','erp.assert_new_stock_cutoff_coverage_v1()','erp.get_laundry_bd_workspace_v1(jsonb)','erp.save_laundry_bd_action_v1(text,jsonb,uuid)','erp.bd_save_invoice_draft_v1(jsonb,uuid)','erp.bd_check_correction_sources_v1(uuid)','erp.bd_invoice_lines_json_v1(uuid)','erp.bd_post_invoice_v1(jsonb,uuid)','erp.bd_invoice_resync_v1(uuid,date)','erp.bd_reverse_invoice_v1(jsonb,uuid)','erp.desired_laundry_accrual(uuid)','erp.rebuild_po_hpp(uuid,text)','erp.bd_lot_laundry_unknown_v1(uuid)','erp.cp6_lot_rework_cost_v2620c(uuid)','erp.period_blockers_v1(date,date)','erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)','erp._validate_migration_batch_base(uuid)','erp.finalize_migration_batch(uuid)','erp.save_initial_import_action_v1(text,jsonb,uuid)','erp.get_initial_import_workspace_v1(uuid)','erp.initial_import_revision_v1(uuid)','erp.pocket_period_total_v1(uuid)','erp.pocket_period_manifest_v1(date,date)','erp.pocket_period_target_v1(uuid,boolean)','erp.pocket_period_book_v1(uuid)','erp.sync_pocket_period_v1(uuid,date,text,text)','erp.save_pocket_period_action_v1(text,jsonb,uuid)','erp.initial_import_source_value_v1(uuid)','erp.check_initial_import_receipt_v1(uuid,uuid)','erp.recost_initial_import_origins_v1(uuid)','erp.run_v267_financial_truth_checks()','erp._cp6_supplier_cent_state(uuid[])','erp.get_pocket_fabric_workspace_v1(text)','erp.pocket_period_checks_v1()','erp.save_pocket_fabric_action_v1(text,jsonb,uuid)','erp.preview_pocket_period_v1(date,date)']::text[])
   or definition_sha256 is distinct from encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex')
   or installed_definition_sha256 is null or installed_definition_sha256=definition_sha256
   or installed_definition_sha256 is distinct from encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex'))
  then raise exception 'BE_CAPSULE_SOURCE_DRIFT';end if;
end $capsule_guard$;
commit;
