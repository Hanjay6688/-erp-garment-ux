-- CP6 AY: PO HPP corrections dated from the goods. Release candidate of the T3 combined package; closed, drained maintenance required.
begin;
-- Built by scripts/cp6_t3_awx_release.py from supabase/dev/cp6_ay_t1_family.sql (sha256 ca71b7e59afbf661ceda29a369b4373e42e30d97b2b5e66a4047fb195c0f6f3f): the T1 body below is unchanged apart from the
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
 if exists(select 1 from erp.schema_migrations where version='v2.6.20ay') or to_regclass('erp.cp6_v2620ay_rollback_capsule') is not null
  or to_regclass('erp.po_hpp_gl_lot_state_v1') is not null or to_regclass('erp.po_hpp_gl_material_state_v1') is not null
 then raise exception 'AY_EXACT_PREDECESSOR_WITHOUT_SUCCESSOR_REQUIRED';end if;
end $admission$;
do $predecessor$
begin
 if exists(select 1 from supabase_migrations.schema_migrations where version>'20260924010100') then raise exception 'AY_EXACT_PREDECESSOR_REQUIRED';end if;
end $predecessor$;
do $prior_platform$
declare r record;
begin
 for r in select * from jsonb_to_recordset('[{"marker":"v2.6.20ac","stamp":"20260915031500","name":"erp_v2_6_20ac_cp6_temporal_surface_closure","sha":"7b5690a2eddf618833d352dc75eb95aa1ef4dbcfb25d39b30374b733d33dadbc"},{"marker":"v2.6.20ad","stamp":"20260915113627","name":"erp_v2_6_20ad_cp6_opening_material_business_day","sha":"cd4879eb9b053e3b7a975e1430f481131e377f260ece2f19f07bfb4c98498c1d"},{"marker":"v2.6.20ae","stamp":"20260915201500","name":"erp_v2_6_20ae_cp6_opening_roll_integrity","sha":"228d9185501d418835e6434e64e1445be7b12ce2f517778ea63d789d478461c1"},{"marker":"v2.6.20af","stamp":"20260916014332","name":"erp_v2_6_20af_cp6_posted_child_integrity","sha":"54c5f73b99a2e63c858a777f669432f28260177daf4c45d806bb0e8a7c7c8e8e"},{"marker":"v2.6.20ag","stamp":"20260916050822","name":"erp_v2_6_20ag_cp6_sale_reservation_lineage","sha":"bff1d7d82917ce226ad0fb8823418fa14e497407d9659e125dc01ed5e2fd5944"},{"marker":"v2.6.20ah","stamp":"20260916070451","name":"erp_v2_6_20ah_cp6_return_allocation_eligibility","sha":"e5312744a2ef9ac53717c97e155fccf96a33e2f6a0c68c4b9c45f378ac538219"},{"marker":"v2.6.20ai","stamp":"20260916090022","name":"erp_v2_6_20ai_cp6_work_source_lineage","sha":"d3a604e53e599221afd46d1397e0d0660ebd8dc48db27113dfa63d3c3613a61c"},{"marker":"v2.6.20aj","stamp":"20260916202400","name":"erp_v2_6_20aj_cp6_rework_output_lineage","sha":"2e6cd4e94b52a27c83d2ba134a996c1db66a6f7ff617a5895f8c14769673f9ea"},{"marker":"v2.6.20ak","stamp":"20260917033516","name":"erp_v2_6_20ak_cp6_import_reference_preview","sha":"0d42825b2f2fcb38b9678fe1e6982b0c63290aac012b92be224f4323d495c536"},{"marker":"v2.6.20al","stamp":"20260917054049","name":"erp_v2_6_20al_cp6_opening_value_validation","sha":"74a5d5e14d79c7bbafa731aaf2fe1708bc575299600261f7412f1f7ea7323920"},{"marker":"v2.6.20am","stamp":"20260921214120","name":"erp_v2_6_20am_cp6_transfer_integrity","sha":"d5b155edb19aa8ca949036ba8a9cf67090478083c2e1ae6cc5bbf00b445716a5"},{"marker":"v2.6.20an","stamp":"20260921223438","name":"erp_v2_6_20an_cp6_cutting_selectors","sha":"21ac97ded4ed0cee9175c7fac7ef28ab6713d08b00766e1e5adc86bd38205e6c"},{"marker":"v2.6.20ao","stamp":"20260922135612","name":"erp_v2_6_20ao_cp6_invoice_retail","sha":"5687bb0236528d7e485e738ee2f96c2be0f4bde7e0d41c16bacee3a58183bdbb"},{"marker":"v2.6.20ap","stamp":"20260922135615","name":"erp_v2_6_20ap_cp6_connected_import_materials","sha":"fb8e14f0fd505edf730c0908f7e1c500cf850e29bcc0e90b3a51877224edd61b"},{"marker":"v2.6.20aq","stamp":"20260922161019","name":"erp_v2_6_20aq_cp6_accessory_lock_order","sha":"b1b4e449ca84ad524189640bcd76302cb277b9b690ed89f739ad5706e3cfac5a"},{"marker":"v2.6.20ar","stamp":"20260922185015","name":"erp_v2_6_20ar_cp6_opening_overlap","sha":"7da20a87d48493b4b64c10c395e8e54f87c1c40a835fbd09bbf2cdbc8866fa10"},{"marker":"v2.6.20as","stamp":"20260922210815","name":"erp_v2_6_20as_cp6_event_dates_product_identity","sha":"84e95211698eb2426995fd59d702bb42674f9fff675401be4861c9aa568cc1a8"},{"marker":"v2.6.20at","stamp":"20260923005153","name":"erp_v2_6_20at_cp6_wip_temporal_identity","sha":"f114a78918138a65f761488b77cadb1ab8a70ce6a6a88ae58a9d38656d1cfdb4"},{"marker":"v2.6.20au","stamp":"20260923045944","name":"erp_v2_6_20au_cp6_controlled_product_lifecycle","sha":"593b06092c2d47e03644afb1b7b5aef46c1442a56613f853a151b78ef738f2c2"},{"marker":"v2.6.20av","stamp":"20260923110000","name":"erp_v2_6_20av_cp6_identity_new_stock_cutoff","sha":"193e84efac8ead7cab681071e40070e1f9249f82cec1b7972f0576e8df25a2dc"},{"marker":"v2.6.20aw","stamp":"20260924010000","name":"erp_v2_6_20aw_cp6_close_readiness_engine","sha":"08826a25c14f8f18f5a168040b6f96dc4efe15c4498be5e92b0834601e77407c"},{"marker":"v2.6.20ax","stamp":"20260924010100","name":"erp_v2_6_20ax_cp6_fg_unsourced_receipts","sha":"32b4d33ebd80ed55951736c23be71b7eb79343c4c8dd623a32ae673924fc0a18"}]'::jsonb) as x(marker text,stamp text,name text,sha text) loop
  if not exists(select 1 from erp.schema_migrations where version=r.marker)
   or (select count(*) from supabase_migrations.schema_migrations where name=r.name)<>1
   or not exists(select 1 from supabase_migrations.schema_migrations where version=r.stamp and name=r.name
    and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')=r.sha) then
   raise exception 'AY_PRIOR_PLATFORM_DRIFT: %',r.name;
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
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule','cp6_v2620ay_rollback_capsule')
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
  raise exception 'AY_PREDECESSOR_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
do $historical_capsules$
declare r record;actual text;
begin
 for r in select * from jsonb_each_text('{"bs_resolution_v2619_rollback_capsule":"28ab388833da7da87384766ecaedadc66b4d048c303ee91e16f3939e34afdc39","bs_resolution_v2619a_rollback_capsule":"de8dfaab7b63b8742d383a089cdb05e73b629aad9f4df149e6a3c9fb590ef560","bs_resolution_v2619b_rollback_capsule":"d6d4f7457743d51679b5d25bf166ed69ca4b4f098cf5902ff985937531c2505d","bs_resolution_v2619c_rollback_capsule":"0207ba4f2ffba8ed61584709bbd884f1d2ee1a5981194fd7189a45afe8b3cbe1","cp3_r4_rollback_capsule":"7c01add62e66a4e2774a7199c2e77a04cca5e5942dbbba54d22cef720f82bc1d","cp45_v2617_rollback_capsule":"b9a43ce463de9905e94dd6538fd2a4952b0586a78c145f6f9d88aab7d6da3d80","cp45_v2617a_rollback_capsule":"b065dbcfdf1b59cb799e9f58caf6dd5ca7686e9f70826fce6a1ba8f140610022","cp4_v2616_rollback_capsule":"dde0a005dbe7cc93709bdfc6b961f4b9a76bf4db06fd7177d21dc79048af4d2f","cp6_v2620_rollback_capsule":"01f1e4e23211cff3c399d2d768a41be57980bfab00790715aa759b00a515e032","cp6_v2620a_rollback_capsule":"67befaaf327d2591e1ca1d654132ee483eba39b6cbb4f891c4719d817155d448","cp6_v2620aa_rollback_capsule":"eb0d6fb4fcac2ac06929d577101e604428e9a04821813c342e5b831147dc8948","cp6_v2620ab_rollback_capsule":"3be9a9166e3a607962be819fbe23d38fe455290a7a970dc2aad068079bf30785","cp6_v2620ac_relation_rollback_capsule":"2be5cbb62d1147e1e0d053dc4e447fe1d1258439352c297814c981c985959838","cp6_v2620ac_rollback_capsule":"51a8b08c9d96e66f03c2c8ba94ed3ed8fb15b26d1a2e4c65c58c614442dfa969","cp6_v2620ad_rollback_capsule":"5c3588109395b32ed743e0f4f5d789a3c59e3fffbab7469138f1f423c877ea9d","cp6_v2620ae_rollback_capsule":"6a75e02bf7b90c542fd9f2ac9534a2de066b047f5ffea65bffb1f83fa63c17f0","cp6_v2620af_rollback_capsule":"bfa89fc0e94d34b29405acedf551935f024942835f31cdc98f0f0983a9550288","cp6_v2620ag_rollback_capsule":"7ddfe6181f0c1c7439faf8a8150c542e958b3bafd8d18b5b2d1eb454fd7a85b7","cp6_v2620ah_rollback_capsule":"361be9321e5f4dadc7c7ec0e99ed746a98e7a4150178fc8355d23707c1507a93","cp6_v2620ai_rollback_capsule":"f2428dd712aa763b1379a4ae5b1a1e1e6ee175b355d8769b854a28f1355181c8","cp6_v2620aj_rollback_capsule":"8e24026dc90a2a92292c2cc6c8faa5fc3de991a19f326db494e0af2a518436f1","cp6_v2620ak_rollback_capsule":"dc7bfce7b9ee6a42e33cdf03cabd99d64435a4615245b2037fd6e4ee399aef10","cp6_v2620al_rollback_capsule":"c9e9aca042674efa5c6fa283e4b9ee47f3353ee9ee95b34e14ef1fd6b09bfde9","cp6_v2620am_rollback_capsule":"e781e631d06c6894c20b1fe6f9c65779f461d19c405c8ae74f28ed7d83ae6a26","cp6_v2620an_rollback_capsule":"ebfa8a281a32fe54babbdc209264ab422fde27f344d48561b90d2af022fe75b3","cp6_v2620ao_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620ap_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620aq_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620ar_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620as_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620at_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620au_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620av_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620aw_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620ax_rollback_capsule":"0000000000000000000000000000000000000000000000000000000000000000","cp6_v2620b_rollback_capsule":"f9bf784bff0c54e647f491e257a9649fd0c3e6f10c39ddfc0944c961b9dd7601","cp6_v2620c_rollback_capsule":"f88b1f5890ee8e7041758971bf9c9a3ce2bd0a7be6989fb95332c2dd7fa139aa","cp6_v2620d_rollback_capsule":"fa300c5554da4bb6812c61d726fd64f66329c97b085fa7d6ad5d0d8e5ae31235","cp6_v2620e_rollback_capsule":"143cd291cf4c12e78ab61e74e02ed03b08a48832a5064671868ff2bd2e3e1da7","cp6_v2620f_rollback_capsule":"076133b098e821fc2713af559618adf8aa3e204908f810af440fda355fc7a57f","cp6_v2620g_rollback_capsule":"ed9f4cacb47bd026ad6bdea373d1aa87044ed12aa60323cea453e3187dc488c4","cp6_v2620h_rollback_capsule":"4c25a060a2df3c22cd6fa9ff0b297163e223118a0d930b97bf1282b4756d909d","cp6_v2620i_rollback_capsule":"051203d95c44968abd8594f5bd48e289c4ac9a6c9fa49a89eee1086ad6b2c166","cp6_v2620j_rollback_capsule":"1393a8085d0f58717b13048c9cc3f7e9969ac86c351d6dfefdd2d4f43a735bd2","cp6_v2620k_rollback_capsule":"55aa71061f616ea11b361f0fabee2fd892f6438cc3f567cb9c135552ade42409","cp6_v2620l_rollback_capsule":"b4278768fce4ef307795953c14f607278c43bf474d76d3362e477280be08eb39","cp6_v2620m_rollback_capsule":"4b5f89d7bc4557f92b47716fe15640ab244c424fc1279433eb806d9d91d234e9","cp6_v2620n_rollback_capsule":"46e5ea4524613bb7a386551ada9e06888ea35eb987f9f5b864457fdd18bc3bc1","cp6_v2620o_rollback_capsule":"044e6b1a050df7e2a1d36082b0451877bda01116c08f611dfceb7a666bdf03c8","cp6_v2620p_rollback_capsule":"b656abaf23276984567c6c8d87b311427463c008b5ecd762fbdd0c2df13795df","cp6_v2620q_rollback_capsule":"ab6c992fbaa87f19a4eba696a57a3972f98504a354d9b5fc3be660939f8ea20f","cp6_v2620r_rollback_capsule":"8eb5e0a38284c5f8e3fee56618893ba72feaae9d26605c9ca3874dae25045297","cp6_v2620s_rollback_capsule":"fb57810a75f8829a038ed61b3a1cabde33dccf1e384661bc6723c51e28b3e132","cp6_v2620t_rollback_capsule":"348db4650d788750da243500b49e23c1130fdb70bc4a6d1fdf136bf68aa21f30","cp6_v2620u_rollback_capsule":"720eb1984548a3c381387fbe4d34e3c6f00334c8a4549eab7e398b827dcb7dd4","cp6_v2620v_rollback_capsule":"573ef5842eefadf1c32469514f4c8498667c99aec20ef20651406e4f419f5f60","cp6_v2620w_rollback_capsule":"f4e2ca1d577dd9f2724cc90693e8ee8bff36365c696575b69c6463f3e8ca0324","cp6_v2620x_rollback_capsule":"064db1068b56daa69e409ae582cd8a99490cea75d269154baa4217f90d3ca0d1","cp6_v2620y_rollback_capsule":"e3b23429a7f002c85ca8de1f8c632df13a4a2fc4e4654c12e2431c212772841d","cp6_v2620z_rollback_capsule":"ad0436a1480af43070e9861cb7e28d4cf55c435edbffb5fe368ca7babb7863ef","cutting_bridge_v2618_rollback_capsule":"535d1abd25668bc5bee79d82a602afe5efe4e8ce313bf1fb5170ae2004e3cb2d","cutting_bridge_v2618a_rollback_capsule":"db0608e690b3d936fa20b62cc4cfb9b1f9e86718212526eb6131562578b8bf60"}'::jsonb) loop
  execute format($caps$select encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to((to_jsonb(t)-array['captured_at','boundary_snapshot'])::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$caps$,r.key) into actual;
  if actual is distinct from r.value then raise exception 'AY_HISTORICAL_CAPSULE_DRIFT: %',r.key;end if;
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
 for r in select unnest(array['erp.cp6_v2620ao_rollback_capsule','erp.cp6_v2620ap_rollback_capsule','erp.cp6_v2620aq_rollback_capsule','erp.cp6_v2620ar_rollback_capsule','erp.cp6_v2620as_rollback_capsule','erp.cp6_v2620at_rollback_capsule','erp.cp6_v2620au_rollback_capsule','erp.cp6_v2620av_rollback_capsule','erp.cp6_v2620aw_rollback_capsule','erp.cp6_v2620ax_rollback_capsule']::regclass[]) as rel loop
  if not exists(select 1 from pg_class where oid=r.rel and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid=r.rel and a.grantee<>p.relowner)
   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid=r.rel and a.grantee<>'postgres'::regrole)
   or exists(select 1 from pg_policy where polrelid=r.rel)
   or exists(select 1 from pg_trigger where tgrelid=r.rel and not tgisinternal) then raise exception 'AY_PRIOR_CAPSULE_SECURITY: %',r.rel;end if;
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel)) into actual;
  if actual is distinct from expected then raise exception 'AY_PRIOR_CAPSULE_SHAPE_DRIFT: %',r.rel;end if;
  execute format($b$select count(*) filter(where boundary_snapshot is null or not(boundary_snapshot ?& array['before','after','platform_before','markers_before']))
   +(case when count(distinct boundary_snapshot)=1 then 0 else 1 end) from %s$b$,r.rel) into bad;
  if bad<>0 then raise exception 'AY_PRIOR_CAPSULE_BOUNDARY: %',r.rel;end if;
 end loop;
end $prior_capsules$;
create table erp.cp6_v2620ay_rollback_capsule(like erp.cp6_v2620an_rollback_capsule including all);
alter table erp.cp6_v2620ay_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620ay_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620ay_rollback_capsule(object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),i.identity,pg_get_functiondef(p.oid),
 encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
 array(select a::text from unnest(p.proacl)a order by a::text),pg_get_userbyid(p.proowner)
from unnest(array['erp.sync_po_hpp_to_gl(uuid,date)']) i(identity)
join pg_proc p on p.oid=i.identity::regprocedure join pg_namespace n on n.oid=p.pronamespace;
create temp table cp6_release_functions on commit drop as
select p.oid::regprocedure::text as identity,encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') as definition_sha256,
  array(select a::text from unnest(p.proacl)a order by a::text) as acl,pg_get_userbyid(p.proowner) as owner
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p');
do $before_data$ declare v_table text;v_hash jsonb;v_before jsonb; begin
 v_before:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620ay_rollback_capsule']::text[]) order by 1 loop
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
 if (select count(*) from erp.schema_migrations where version in('v2.6.20av','v2.6.20aw','v2.6.20ax'))<>3 then raise exception 'AY_T1_REQUIRES_AV_AW_AX'; end if;
 if exists(select 1 from erp.schema_migrations where version='v2.6.20ay') or to_regprocedure('erp.po_hpp_gl_leg_add_v1(jsonb,date,numeric,numeric,numeric)') is not null or to_regclass('erp.po_hpp_gl_lot_state_v1') is not null or to_regclass('erp.po_hpp_gl_material_state_v1') is not null then raise exception 'AY_T1_ALREADY_INSTALLED'; end if;
end $t1_guard$;
create table erp.po_hpp_gl_lot_state_v1(
  lot_id uuid primary key,
  po_id uuid not null,
  hpp_per_pcs numeric not null,
  updated_at timestamptz not null default statement_timestamp());
comment on table erp.po_hpp_gl_lot_state_v1 is 'AY: HPP per piece of each lot as erp.sync_po_hpp_to_gl last posted it (base of the per-lot correction of the next sync).';
alter table erp.po_hpp_gl_lot_state_v1 enable row level security;
revoke all on erp.po_hpp_gl_lot_state_v1 from public,anon,authenticated,service_role;
create table erp.po_hpp_gl_material_state_v1(
  po_id uuid not null,
  source_key text not null,
  material_value numeric not null,
  updated_at timestamptz not null default statement_timestamp(),
  primary key(po_id,source_key));
comment on table erp.po_hpp_gl_material_state_v1 is 'AY rev7: value of each material fact behind a PO HPP (cutting issue/return M:<movement>, also of other POs'' groups in the same cutting batch; contractor issue C:<item>) as that PO''s last erp.sync_po_hpp_to_gl saw it; base of the per-fact correction dated on its own day.';
alter table erp.po_hpp_gl_material_state_v1 enable row level security;
revoke all on erp.po_hpp_gl_material_state_v1 from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.po_hpp_gl_leg_add_v1(p_acc jsonb, p_day date, p_fg numeric, p_cogs numeric, p_other numeric)
 RETURNS jsonb
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO ''
AS $function$
-- AY: add one dated leg (FG, COGS, other) to the per-date accumulator of erp.sync_po_hpp_to_gl.
select coalesce(p_acc,'{}'::jsonb)||jsonb_build_object(p_day::text,jsonb_build_object(
  'fg',coalesce((p_acc->(p_day::text)->>'fg')::numeric,0)+coalesce(p_fg,0),
  'cogs',coalesce((p_acc->(p_day::text)->>'cogs')::numeric,0)+coalesce(p_cogs,0),
  'other',coalesce((p_acc->(p_day::text)->>'other')::numeric,0)+coalesce(p_other,0)))
$function$;
revoke all on function erp.po_hpp_gl_leg_add_v1(jsonb,date,numeric,numeric,numeric) from public,anon,authenticated,service_role;
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
  v_acc jsonb:='{}'::jsonb;v_f numeric(24,6);v_c numeric(24,6);v_o numeric(24,6);v_wip numeric(24,6);r record;
  v_cap date;v_end date;v_sf numeric(24,6):=0;v_sc numeric(24,6):=0;v_so numeric(24,6):=0;
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

  -- AY (owner, 24 Sep 2026): on the late supplier invoice path the correction of each piece is dated from the physical
  -- facts of that piece: WIP -> FG when it enters FG, FG -> COGS when it is sold (back when returned or when the sale is
  -- reversed), FG -> other when it is written off, BS'd or relabelled; never before the piece was there. Per-account
  -- totals equal the previous single journal (the last date takes the exact remainder).
  -- The period rule is applied as before AY when the effective date E is already closed: every date is capped at E,
  -- so the correction is one journal with economic date E that post_journal (erp.resolve_accounting_transaction_date)
  -- posts on the recognition day; no report before that day changes and the economic date is kept. Only an open E
  -- moves forward to the goods (an open E caps the physical dates at today: the product allows a physical time a few
  -- minutes ahead of the clock).
  v_cap:=erp._cp3_business_date(statement_timestamp());
  if exists(select 1 from erp.accounting_period_control c
            where c.singleton_id=1 and c.closed_through is not null and p_effective_date<=c.closed_through) then
    v_cap:=p_effective_date;
  end if;
  if erp.invoice_recost_economic_date_v1() is null then
  -- Independent review 24 Sep (M1): outside a late supplier invoice the posting is exactly the AS posting (one journal on
  -- the caller's date); several callers pass a physical date (FG adjustment, QC, laundry receipt, ...), whose write-off
  -- must stay on that date.
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
    update erp.po_hpp_gl_events set journal_entry_id=v_journal,
      effective_date=(select transaction_date from erp.journal_entries where id=v_journal) where id=v_event;
  end if;

  else
  -- rev6/rev7 (independent reviews 24 Sep of rev4, rev5 and rev6): daily balances. For every date D of a physical fact
  -- (an FG movement of the PO's lots, including reversals and voided lots; a material fact behind the PO's HPP; the
  -- cutting day of a group in a cutting batch) the correction held in FG, COGS and other is each lot's per-piece
  -- correction as of D times its pieces in FG, sold (sales and returns and their reversals) and out otherwise
  -- (adjustment, BS, relabel, and their reversals) as of D; each date posts the change of those balances (cents), WIP
  -- balancing, and the last date the exact remainder to the targets. Per-piece correction of a lot: its HPP now minus
  -- the HPP last posted (erp.po_hpp_gl_lot_state_v1 when written with or after the PO state; else the version current
  -- at the last sync; else the lot's first version, for a lot made by a flow that does not sync, e.g. a relabel; else
  -- zero), less the part of its material correction whose fact (erp.po_hpp_gl_material_state_v1) is dated after D.
  v_end:=p_effective_date;
  for r in
    with lot0 as(
      select fl.id,fl.lot_origin,coalesce(fl.cutting_group_id,qi.cutting_group_id) grp,
        coalesce((select max(case when coalesce(hv.qty_basis_pcs,0)>0 then hv.total_cost/hv.qty_basis_pcs else 0 end)
                  from erp.hpp_versions hv where hv.lot_id=fl.id and hv.is_current),0)::numeric h,
        coalesce((select ls.hpp_per_pcs from erp.po_hpp_gl_lot_state_v1 ls where ls.lot_id=fl.id and ls.updated_at>=s.updated_at),
                 (select case when coalesce(ov.qty_basis_pcs,0)>0 then ov.total_cost/ov.qty_basis_pcs else 0 end
                  from erp.hpp_versions ov where ov.lot_id=fl.id and ov.calculated_at<=s.updated_at
                  order by ov.calculated_at desc,ov.version_no desc limit 1),
                 (select case when coalesce(fv.qty_basis_pcs,0)>0 then fv.total_cost/fv.qty_basis_pcs else 0 end
                  from erp.hpp_versions fv where fv.lot_id=fl.id order by fv.version_no,fv.calculated_at limit 1),0)::numeric o,
        (select pa.source_lot_id from erp.product_conversion_allocations pa where pa.destination_lot_id=fl.id order by pa.id limit 1) src,
        (select pc.status from erp.product_conversion_allocations pa join erp.product_conversions pc on pc.id=pa.conversion_id
          where pa.destination_lot_id=fl.id order by pa.id limit 1) cst
      from erp.fg_lots fl left join erp.qc_inspection_items qi on qi.id=fl.qc_item_id
      where fl.po_id=p_po_id and fl.lot_origin in('PRODUCTION','CONVERSION','VOIDED_PRODUCTION')
    ), grp as(
      -- The PO's cutting groups and every group of their cutting batches (a batch may hold groups of other POs; its
      -- material is pooled over all of them): pieces and the day the group was first cut.
      select g.id,g.po_id,g.cutting_batch_id batch,
        coalesce((select gt.total_pcs from erp.v_cutting_group_totals gt where gt.cutting_group_id=g.id),0)::numeric pcs,
        greatest(p_effective_date,least(v_cap,coalesce((select min(erp._cp3_business_date(mm.physical_at)) from erp.material_stock_movements mm
          where mm.source_id=g.id and mm.source_type='CUTTING_GROUP'),erp._cp3_business_date(g.cut_at)))) cd
      from erp.cutting_groups g
      where g.po_id=p_po_id or g.cutting_batch_id in(select g0.cutting_batch_id from erp.cutting_groups g0
                                                     where g0.po_id=p_po_id and g0.cutting_batch_id is not null)
    ), bt as(
      -- Each batch: pieces of its groups and the effective pieces erp.rebuild_po_hpp divides its material by.
      select gr.batch,sum(gr.pcs) spcs,
        coalesce((select vb.effective_pcs from erp.v_cutting_batch_totals vb where vb.cutting_batch_id=gr.batch),0)::numeric eff
      from grp gr where gr.batch is not null group by gr.batch
    ), mk as(
      -- When the material state was last written (a sync right after erp.rebuild_po_hpp).
      select (select ms.updated_at from erp.po_hpp_gl_material_state_v1 ms where ms.po_id=p_po_id and ms.source_key='SYNC') ts
    ), mat as(
      -- Every material fact behind the PO's HPP (erp.rebuild_po_hpp): cutting issues and returns of each group (pooled per
      -- cutting batch when the group is in one; the PO-wide pool takes the PO's own groups) and non-accessory contractor
      -- issues (PO-wide over the source quantity), each on the physical day erp.sync_material_cost_revaluation dates its
      -- WIP revaluation (AZ), with its change since the HPP last posted: its state, else zero for a fact created after
      -- the state was written (no posted HPP has it), else unknown (null: the pool keeps the constant correction).
      select case when gr.batch is not null then 'B:'||gr.batch::text else 'G:'||gr.id::text end pool,gr.po_id=p_po_id own,
        greatest(p_effective_date,least(v_cap,erp._cp3_business_date(mm.physical_at))) d,
        -mm.qty_signed*mm.unit_cost_snapshot-coalesce(ms.material_value,case when mm.system_created_at>mk.ts then 0 end) dv
      from erp.material_stock_movements mm join grp gr on gr.id=mm.source_id cross join mk
      left join erp.po_hpp_gl_material_state_v1 ms on ms.po_id=p_po_id and ms.source_key='M:'||mm.id::text
      where mm.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN')
      union all
      select 'CONTRACTOR',false,greatest(p_effective_date,least(v_cap,erp._cp3_business_date(coalesce(cv.pa,cm.physical_at)))),
        ci.qty*ci.unit_cost_snapshot-coalesce(ms.material_value,case when cv.ca>mk.ts then 0 end)
      from erp.contractor_material_issue_items ci join erp.contractor_material_issues cm on cm.id=ci.issue_id
      join erp.materials mt on mt.id=ci.material_id cross join mk
      cross join lateral(select min(cm2.physical_at) pa,min(cm2.system_created_at) ca from erp.material_stock_movements cm2
        where cm2.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and cm2.source_id=ci.id) cv
      left join erp.po_hpp_gl_material_state_v1 ms on ms.po_id=p_po_id and ms.source_key='C:'||ci.id::text
      where cm.po_id=p_po_id and cm.status='POSTED' and mt.material_type<>'ACCESSORY'
    ), matp as(
      select pool,d,dv from mat union all select 'PO',d,dv from mat where own
    ), pools as(
      select pool,bool_and(dv is not null) ok,coalesce(sum(dv),0) dvf from matp group by pool
    ), lot as(
      -- The material pool of each lot as erp.rebuild_po_hpp allocates it (its cutting batch over the batch's effective
      -- pieces, else its lineage group over the group's pieces, else the PO over the PO's production pieces) and qf, the
      -- pieces behind that pool now.
      select l.*,gr.batch,
        case when gr.batch is not null then case when b.eff>0 then 'B:'||gr.batch::text else 'PO' end
             when gr.pcs>0 then 'G:'||gr.id::text else 'PO' end pool,
        case when gr.batch is not null and b.eff>0 then b.eff
             when gr.batch is null and gr.pcs>0 then gr.pcs
             else nullif((select sum(f2.initial_qty_pcs) from erp.fg_lots f2 where f2.po_id=p_po_id and f2.lot_origin='PRODUCTION'),0) end qf
      from lot0 l left join grp gr on gr.id=l.grp left join bt b on b.batch=gr.batch
    ), srcq as(
      select nullif(erp.cp6_po_source_qty_v2620c(p_po_id),0)::numeric q
    ), lotd as(
      select l.id,l.pool,l.qf,l.batch,l.src,l.cst,case when l.lot_origin='VOIDED_PRODUCTION'
          then coalesce((select avg(l2.h-l2.o) from lot0 l2 where l2.grp=l.grp and l2.lot_origin='PRODUCTION'),
                        coalesce((select p.dvf/l.qf from pools p where p.pool=l.pool and p.ok),0)
                        +coalesce((select p.dvf/(select q from srcq) from pools p where p.pool='CONTRACTOR' and p.ok),0))
          else l.h-l.o end dh
      from lot l
    ), ev as(
      select m.lot_id,greatest(p_effective_date,least(v_cap,erp._cp3_business_date(m.physical_at))) d,
        coalesce(o.movement_type,m.movement_type) k,m.qty_signed::numeric q
      from erp.fg_stock_movements m join lotd l on l.id=m.lot_id
      left join erp.fg_stock_movements o on m.movement_type='REVERSAL' and o.id=m.reversal_of_id
      where coalesce(o.movement_type,m.movement_type) in('QC_GOOD','REWORK_IN','OPENING','SALE','SALE_RETURN',
                                                         'ADJUSTMENT','BS_OUT','REBRAND_OUT','REBRAND_IN')
    ), dates as(
      select d from ev union select m.d from matp m join pools p on p.pool=m.pool and p.ok
      union select gr.cd from grp gr where gr.batch is not null
    ), daily as(
      select lot_id,d,
        sum(case when k in('QC_GOOD','REWORK_IN','OPENING') then q else 0 end) p,
        sum(case when k in('SALE','SALE_RETURN') then -q else 0 end) sd,
        sum(case when k in('ADJUSTMENT','BS_OUT','REBRAND_OUT','REBRAND_IN') then -q else 0 end) ot
      from ev group by 1,2
    ), cumq as(
      -- Pieces of each lot in FG / sold / out otherwise as of each date: running sums (independent review of rev6, M-4:
      -- no dates x movements join).
      select g.lot_id,g.d,
        sum(coalesce(dy.p,0)) over w p,sum(coalesce(dy.sd,0)) over w sd,sum(coalesce(dy.ot,0)) over w ot
      from (select l.id lot_id,dt.d from lotd l cross join dates dt) g
      left join daily dy on dy.lot_id=g.lot_id and dy.d=g.d
      window w as(partition by g.lot_id order by g.d rows unbounded preceding)
    ), pday as(
      select pool,d,sum(dv) dv from matp group by 1,2
    ), pcum as(
      -- Each pool's material correction as of each date (running sum).
      select p.pool,dt.d,sum(coalesce(pd.dv,0)) over(partition by p.pool order by dt.d rows unbounded preceding) dv
      from pools p cross join dates dt left join pday pd on pd.pool=p.pool and pd.d=dt.d where p.ok
    ), bcum as(
      -- Each batch's pieces cut by each date, scaled to its effective pieces.
      select b.batch,dt.d,
        case when b.spcs>0 then b.eff*sum(coalesce(bd.pcs,0)) over(partition by b.batch order by dt.d rows unbounded preceding)/b.spcs
             else b.eff end pcs
      from bt b cross join dates dt
      left join (select gr.batch,gr.cd,sum(gr.pcs) pcs from grp gr where gr.batch is not null group by 1,2) bd on bd.batch=b.batch and bd.cd=dt.d
    ), cl as(
      -- Per-piece correction of each lot as of each date: its correction now, less the part of its pool's (and the PO's
      -- contractor) material correction whose fact is not there yet on that date. A batch divides by the (effective)
      -- pieces of the groups cut by then.
      select c.lot_id,c.d,c.p,c.sd,c.ot,
        l.dh+coalesce(pc.dv/nullif(case when l.pool like 'B:%' then bc.pcs else l.qf end,0),0)-coalesce(pp.dvf/l.qf,0)
          +coalesce((cc.dv-cp.dvf)/(select q from srcq),0) cv
      from cumq c join lotd l on l.id=c.lot_id
      left join pools pp on pp.pool=l.pool and pp.ok
      left join pcum pc on pc.pool=l.pool and pc.d=c.d
      left join bcum bc on bc.batch=l.batch and bc.d=c.d
      left join pools cp on cp.pool='CONTRACTOR' and cp.ok
      left join pcum cc on cc.pool='CONTRACTOR' and cc.d=c.d
    ), cl2 as(
      -- A relabelled lot follows its source lot (independent review of rev6, F6: a reversed relabel takes the source's
      -- correction, so the pair nets out; a posted one adds its own difference).
      select c.d,c.p,c.sd,c.ot,
        case when l.src is not null and cs.cv is not null
          then cs.cv+case when l.cst='POSTED' then l.dh-ls.dh else 0 end else c.cv end cv
      from cl c join lotd l on l.id=c.lot_id
      left join cl cs on cs.lot_id=l.src and cs.d=c.d left join lotd ls on ls.id=l.src
    )
    select d,sum(cv*(p-sd-ot)) f,sum(cv*sd) c,sum(cv*ot) o from cl2 group by d order by d
  loop
    -- The change of the rounded balances since the previous date; the total is rounded once and FG takes the rest, so a
    -- pure sale day (FG -> COGS) moves no cent through WIP (independent review of rev6, m-1).
    v_f:=round(r.f+r.c+r.o,2)-round(r.c,2)-round(r.o,2);
    v_acc:=erp.po_hpp_gl_leg_add_v1(v_acc,r.d,v_f-v_sf,round(r.c,2)-v_sc,round(r.o,2)-v_so);
    v_sf:=v_f;v_sc:=round(r.c,2);v_so:=round(r.o,2);v_end:=greatest(v_end,r.d);
  end loop;
  -- The last date takes the exact remainder to the targets (rounding, or anything the balances do not explain).
  v_acc:=erp.po_hpp_gl_leg_add_v1(v_acc,v_end,v_df-v_sf,v_dc-v_sc,v_do-v_so);
  -- One event and one journal per requested date; WIP balances each date.
  for r in select key::date d,value v from jsonb_each(v_acc) order by 1 loop
    v_f:=(r.v->>'fg')::numeric;v_c:=(r.v->>'cogs')::numeric;v_o:=(r.v->>'other')::numeric;v_wip:=-(v_f+v_c+v_o);
    v_lines:='[]'::jsonb;
    if abs(v_f)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_f>0
      then jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_f,'credit',0,'po_id',p_po_id)
      else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',abs(v_f),'po_id',p_po_id) end); end if;
    if abs(v_c)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_c>0
      then jsonb_build_object('mapping_key','COGS','debit',v_c,'credit',0,'po_id',p_po_id)
      else jsonb_build_object('mapping_key','COGS','debit',0,'credit',abs(v_c),'po_id',p_po_id) end); end if;
    -- The other bucket stays on one account, the one the AS journal would use for the PO's total other change, so each
    -- account's total equals the AS journal (independent review of rev6, M-3/F5).
    if abs(v_o)>0.005 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key',case when v_do>=0 then 'OTHER_EXPENSE' else 'OTHER_INCOME' end,
      'debit',greatest(v_o,0),'credit',greatest(-v_o,0),'po_id',p_po_id)); end if;
    if abs(v_wip)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_wip>0
      then jsonb_build_object('mapping_key','WIP','debit',v_wip,'credit',0,'po_id',p_po_id)
      else jsonb_build_object('mapping_key','WIP','debit',0,'credit',abs(v_wip),'po_id',p_po_id) end); end if;
    if jsonb_array_length(v_lines)>=2 then
      insert into erp.po_hpp_gl_events(po_id,effective_date,old_hpp_total,new_hpp_total,fg_delta,cogs_delta,other_delta)
      values(p_po_id,r.d,round(coalesce(s.hpp_total_cost,0),2),v_target_hpp,v_f,v_c,v_o)
      returning id into v_event;
      v_journal:=erp.post_journal('PO_HPP_GL_SYNC',v_event,r.d,
        'Latest corrected HPP allocation · exact minor-unit targets · dated from the goods',v_lines);
      update erp.po_hpp_gl_events set journal_entry_id=v_journal,
        effective_date=(select transaction_date from erp.journal_entries where id=v_journal) where id=v_event;
    end if;
  end loop;
  end if;
  -- The HPP this sync posted for each lot and the value of each material fact it saw: the bases of the next sync.
  insert into erp.po_hpp_gl_lot_state_v1(lot_id,po_id,hpp_per_pcs,updated_at)
  select fl.id,p_po_id,coalesce((select max(case when coalesce(hv.qty_basis_pcs,0)>0 then hv.total_cost/hv.qty_basis_pcs else 0 end)
    from erp.hpp_versions hv where hv.lot_id=fl.id and hv.is_current),0),statement_timestamp()
  from erp.fg_lots fl where fl.po_id=p_po_id and fl.lot_origin in('PRODUCTION','CONVERSION','VOIDED_PRODUCTION')
  on conflict(lot_id) do update set po_id=excluded.po_id,hpp_per_pcs=excluded.hpp_per_pcs,updated_at=excluded.updated_at;
  -- The material state is the value of each fact inside the HPP just posted, so it is written only when that HPP was
  -- rebuilt in this statement (every erp.rebuild_po_hpp caller syncs right after it; a sync without a rebuild, e.g. FG
  -- adjustment or a sale reversal, posts the HPP of the last rebuild, which the kept state still describes).
  if exists(select 1 from erp.hpp_versions hv join erp.fg_lots fl on fl.id=hv.lot_id
            where fl.po_id=p_po_id and hv.is_current and hv.calculated_at>=statement_timestamp()) then
    insert into erp.po_hpp_gl_material_state_v1(po_id,source_key,material_value,updated_at)
    select p_po_id,'M:'||mm.id::text,-mm.qty_signed*mm.unit_cost_snapshot,statement_timestamp()
    from erp.material_stock_movements mm join erp.cutting_groups g on g.id=mm.source_id
    where mm.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN')
      and (g.po_id=p_po_id or g.cutting_batch_id in(select g0.cutting_batch_id from erp.cutting_groups g0
                                                    where g0.po_id=p_po_id and g0.cutting_batch_id is not null))
    union all
    select p_po_id,'C:'||ci.id::text,ci.qty*ci.unit_cost_snapshot,statement_timestamp()
    from erp.contractor_material_issue_items ci join erp.contractor_material_issues cm on cm.id=ci.issue_id
    where cm.po_id=p_po_id and cm.status='POSTED'
    union all
    select p_po_id,'SYNC',0,statement_timestamp()
    on conflict(po_id,source_key) do update set material_value=excluded.material_value,updated_at=excluded.updated_at;
  end if;

  insert into erp.po_hpp_gl_state(po_id,base_output_qty,hpp_total_cost,fg_value,cogs_value,other_out_value,updated_at)
  values(p_po_id,v_target_qty,v_target_hpp,v_target_fg,v_target_cogs,v_target_other,statement_timestamp())
  on conflict(po_id) do update set base_output_qty=excluded.base_output_qty,
    hpp_total_cost=excluded.hpp_total_cost,fg_value=excluded.fg_value,
    cogs_value=excluded.cogs_value,other_out_value=excluded.other_out_value,updated_at=statement_timestamp();
end
$function$;
insert into erp.schema_migrations(version,description) values('v2.6.20ay','PO HPP corrections dated from the goods: FG from the lot date, COGS from the sale date');
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule','cp6_v2620ay_rollback_capsule')
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
  raise exception 'AY_INSTALLED_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
update erp.cp6_v2620ay_rollback_capsule set installed_definition_sha256=encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex');
do $after_data$ declare v_table text;v_hash jsonb;v_after jsonb;v_before jsonb; begin
 v_after:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620ay_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_after:=v_after||jsonb_build_object(v_table,v_hash);
 end loop;
 select snapshot->'before' into v_before from pg_temp.cp6_release_boundary;
 if (v_after-array['po_hpp_gl_lot_state_v1','po_hpp_gl_material_state_v1']::text[]) is distinct from v_before or exists(select 1 from unnest(array['po_hpp_gl_lot_state_v1','po_hpp_gl_material_state_v1']::text[]) t where (v_after->t->>'count') is distinct from '0')
  then raise exception 'AY_INSTALL_CHANGED_DATA';end if;
 if exists(with live as (select p.oid::regprocedure::text as identity,encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') as definition_sha256,
  array(select a::text from unnest(p.proacl)a order by a::text) as acl,pg_get_userbyid(p.proowner) as owner
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p')) select 1 from pg_temp.cp6_release_functions f left join live x on x.identity=f.identity
  where f.identity<>all(coalesce((select array_agg(object_regidentity) from erp.cp6_v2620ay_rollback_capsule),'{}'))
  and (x.identity is null or (x.definition_sha256,x.acl,x.owner) is distinct from (f.definition_sha256,f.acl,f.owner)))
  then raise exception 'AY_CAPSULE_INCOMPLETE';end if;
 update erp.cp6_v2620ay_rollback_capsule set boundary_snapshot=(select snapshot from pg_temp.cp6_release_boundary)||jsonb_build_object('after',v_after);
end $after_data$;
do $capsule_guard$
declare expected jsonb;actual jsonb;boundary jsonb;
begin
 if not exists(select 1 from pg_class where oid='erp.cp6_v2620ay_rollback_capsule'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='erp.cp6_v2620ay_rollback_capsule'::regclass and a.grantee<>p.relowner)
   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='erp.cp6_v2620ay_rollback_capsule'::regclass and a.grantee<>'postgres'::regrole)
   or exists(select 1 from pg_policy where polrelid='erp.cp6_v2620ay_rollback_capsule'::regclass)
   or exists(select 1 from pg_trigger where tgrelid='erp.cp6_v2620ay_rollback_capsule'::regclass and not tgisinternal)
   or (select count(*) from erp.cp6_v2620ay_rollback_capsule)<>1 then raise exception 'AY_CAPSULE_SECURITY_OR_COUNT';end if;
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620an_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620an_rollback_capsule'::regclass)) into expected;
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620ay_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620ay_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620ay_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620ay_rollback_capsule'::regclass)) into actual;
 if actual is distinct from expected then raise exception 'AY_CAPSULE_SHAPE_DRIFT';end if;
 select boundary_snapshot into boundary from erp.cp6_v2620ay_rollback_capsule limit 1;
 if 1>0 and (boundary is null or exists(select 1 from erp.cp6_v2620ay_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before'])) then raise exception 'AY_CAPSULE_BOUNDARY';end if;
 if exists(select 1 from erp.cp6_v2620ay_rollback_capsule where object_regidentity<>all(array['erp.sync_po_hpp_to_gl(uuid,date)']::text[])
   or definition_sha256 is distinct from encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex')
   or installed_definition_sha256 is null or installed_definition_sha256=definition_sha256
   or installed_definition_sha256 is distinct from encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex'))
  then raise exception 'AY_CAPSULE_SOURCE_DRIFT';end if;
end $capsule_guard$;
commit;
