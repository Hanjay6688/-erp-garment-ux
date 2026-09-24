-- CP6 AV rev2: NEW_STOCK physical cutoff, manual BS origin (1C), rework GOOD as existing stock (2A), fail-closed coverage registry.
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
do $admission$ begin
 if exists(select 1 from erp.schema_migrations where version='v2.6.20av') or to_regclass('erp.cp6_v2620av_rollback_capsule') is not null
  or to_regclass('erp.bs_case_manual_origins_v1') is not null or to_regprocedure('erp.latest_new_stock_physical_at_v1(uuid)') is not null
  or to_regprocedure('erp.assert_new_stock_cutoff_coverage_v1()') is not null or to_regprocedure('erp.guard_bs_case_manual_origin_immutable_v1()') is not null
  or exists(select 1 from supabase_migrations.schema_migrations where version>'20260923045944')
 then raise exception 'AV_EXACT_AU_WITHOUT_SUCCESSOR_REQUIRED';end if;
end $admission$;
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule')
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
 if object_count<>7146 or fingerprint is distinct from '2f6a42aea4e35f54698c493b7ba4f9b6d8489254a4580e15feab9878333b3a02' then
  raise exception 'AV_PREDECESSOR_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
do $historical_capsules$
declare r record;actual text;
begin
 for r in select * from jsonb_each_text('{"bs_resolution_v2619_rollback_capsule":"28ab388833da7da87384766ecaedadc66b4d048c303ee91e16f3939e34afdc39","bs_resolution_v2619a_rollback_capsule":"de8dfaab7b63b8742d383a089cdb05e73b629aad9f4df149e6a3c9fb590ef560","bs_resolution_v2619b_rollback_capsule":"d6d4f7457743d51679b5d25bf166ed69ca4b4f098cf5902ff985937531c2505d","bs_resolution_v2619c_rollback_capsule":"0207ba4f2ffba8ed61584709bbd884f1d2ee1a5981194fd7189a45afe8b3cbe1","cp3_r4_rollback_capsule":"7c01add62e66a4e2774a7199c2e77a04cca5e5942dbbba54d22cef720f82bc1d","cp45_v2617_rollback_capsule":"b9a43ce463de9905e94dd6538fd2a4952b0586a78c145f6f9d88aab7d6da3d80","cp45_v2617a_rollback_capsule":"b065dbcfdf1b59cb799e9f58caf6dd5ca7686e9f70826fce6a1ba8f140610022","cp4_v2616_rollback_capsule":"dde0a005dbe7cc93709bdfc6b961f4b9a76bf4db06fd7177d21dc79048af4d2f","cp6_v2620_rollback_capsule":"b42b94c2380f0768259a3d8f7fb645c76ebd6f92e8bae6a37d802352f7effd4f","cp6_v2620a_rollback_capsule":"67befaaf327d2591e1ca1d654132ee483eba39b6cbb4f891c4719d817155d448","cp6_v2620aa_rollback_capsule":"eb0d6fb4fcac2ac06929d577101e604428e9a04821813c342e5b831147dc8948","cp6_v2620ab_rollback_capsule":"3be9a9166e3a607962be819fbe23d38fe455290a7a970dc2aad068079bf30785","cp6_v2620ac_relation_rollback_capsule":"63c595c956e25135e1e032613831f5a08a734ba1f5c4746c46483c84517ad5ea","cp6_v2620ac_rollback_capsule":"51a8b08c9d96e66f03c2c8ba94ed3ed8fb15b26d1a2e4c65c58c614442dfa969","cp6_v2620ad_rollback_capsule":"5c3588109395b32ed743e0f4f5d789a3c59e3fffbab7469138f1f423c877ea9d","cp6_v2620ae_rollback_capsule":"6a75e02bf7b90c542fd9f2ac9534a2de066b047f5ffea65bffb1f83fa63c17f0","cp6_v2620af_rollback_capsule":"bfa89fc0e94d34b29405acedf551935f024942835f31cdc98f0f0983a9550288","cp6_v2620ag_rollback_capsule":"7ddfe6181f0c1c7439faf8a8150c542e958b3bafd8d18b5b2d1eb454fd7a85b7","cp6_v2620ah_rollback_capsule":"361be9321e5f4dadc7c7ec0e99ed746a98e7a4150178fc8355d23707c1507a93","cp6_v2620ai_rollback_capsule":"f2428dd712aa763b1379a4ae5b1a1e1e6ee175b355d8769b854a28f1355181c8","cp6_v2620aj_rollback_capsule":"8e24026dc90a2a92292c2cc6c8faa5fc3de991a19f326db494e0af2a518436f1","cp6_v2620ak_rollback_capsule":"dc7bfce7b9ee6a42e33cdf03cabd99d64435a4615245b2037fd6e4ee399aef10","cp6_v2620al_rollback_capsule":"c9e9aca042674efa5c6fa283e4b9ee47f3353ee9ee95b34e14ef1fd6b09bfde9","cp6_v2620am_rollback_capsule":"e781e631d06c6894c20b1fe6f9c65779f461d19c405c8ae74f28ed7d83ae6a26","cp6_v2620an_rollback_capsule":"ebfa8a281a32fe54babbdc209264ab422fde27f344d48561b90d2af022fe75b3","cp6_v2620b_rollback_capsule":"f9bf784bff0c54e647f491e257a9649fd0c3e6f10c39ddfc0944c961b9dd7601","cp6_v2620c_rollback_capsule":"f88b1f5890ee8e7041758971bf9c9a3ce2bd0a7be6989fb95332c2dd7fa139aa","cp6_v2620d_rollback_capsule":"fa300c5554da4bb6812c61d726fd64f66329c97b085fa7d6ad5d0d8e5ae31235","cp6_v2620e_rollback_capsule":"143cd291cf4c12e78ab61e74e02ed03b08a48832a5064671868ff2bd2e3e1da7","cp6_v2620f_rollback_capsule":"076133b098e821fc2713af559618adf8aa3e204908f810af440fda355fc7a57f","cp6_v2620g_rollback_capsule":"ed9f4cacb47bd026ad6bdea373d1aa87044ed12aa60323cea453e3187dc488c4","cp6_v2620h_rollback_capsule":"4c25a060a2df3c22cd6fa9ff0b297163e223118a0d930b97bf1282b4756d909d","cp6_v2620i_rollback_capsule":"051203d95c44968abd8594f5bd48e289c4ac9a6c9fa49a89eee1086ad6b2c166","cp6_v2620j_rollback_capsule":"1393a8085d0f58717b13048c9cc3f7e9969ac86c351d6dfefdd2d4f43a735bd2","cp6_v2620k_rollback_capsule":"55aa71061f616ea11b361f0fabee2fd892f6438cc3f567cb9c135552ade42409","cp6_v2620l_rollback_capsule":"b4278768fce4ef307795953c14f607278c43bf474d76d3362e477280be08eb39","cp6_v2620m_rollback_capsule":"4b5f89d7bc4557f92b47716fe15640ab244c424fc1279433eb806d9d91d234e9","cp6_v2620n_rollback_capsule":"46e5ea4524613bb7a386551ada9e06888ea35eb987f9f5b864457fdd18bc3bc1","cp6_v2620o_rollback_capsule":"044e6b1a050df7e2a1d36082b0451877bda01116c08f611dfceb7a666bdf03c8","cp6_v2620p_rollback_capsule":"b656abaf23276984567c6c8d87b311427463c008b5ecd762fbdd0c2df13795df","cp6_v2620q_rollback_capsule":"ab6c992fbaa87f19a4eba696a57a3972f98504a354d9b5fc3be660939f8ea20f","cp6_v2620r_rollback_capsule":"8eb5e0a38284c5f8e3fee56618893ba72feaae9d26605c9ca3874dae25045297","cp6_v2620s_rollback_capsule":"fb57810a75f8829a038ed61b3a1cabde33dccf1e384661bc6723c51e28b3e132","cp6_v2620t_rollback_capsule":"348db4650d788750da243500b49e23c1130fdb70bc4a6d1fdf136bf68aa21f30","cp6_v2620u_rollback_capsule":"720eb1984548a3c381387fbe4d34e3c6f00334c8a4549eab7e398b827dcb7dd4","cp6_v2620v_rollback_capsule":"573ef5842eefadf1c32469514f4c8498667c99aec20ef20651406e4f419f5f60","cp6_v2620w_rollback_capsule":"f4e2ca1d577dd9f2724cc90693e8ee8bff36365c696575b69c6463f3e8ca0324","cp6_v2620x_rollback_capsule":"064db1068b56daa69e409ae582cd8a99490cea75d269154baa4217f90d3ca0d1","cp6_v2620y_rollback_capsule":"e3b23429a7f002c85ca8de1f8c632df13a4a2fc4e4654c12e2431c212772841d","cp6_v2620z_rollback_capsule":"ad0436a1480af43070e9861cb7e28d4cf55c435edbffb5fe368ca7babb7863ef","cutting_bridge_v2618_rollback_capsule":"535d1abd25668bc5bee79d82a602afe5efe4e8ce313bf1fb5170ae2004e3cb2d","cutting_bridge_v2618a_rollback_capsule":"db0608e690b3d936fa20b62cc4cfb9b1f9e86718212526eb6131562578b8bf60"}'::jsonb) loop
  execute format($caps$select encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to((to_jsonb(t)-array['captured_at','boundary_snapshot'])::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$caps$,r.key) into actual;
  if actual is distinct from r.value then raise exception 'AQ_HISTORICAL_CAPSULE_DRIFT: %',r.key;end if;
 end loop;
end $historical_capsules$;
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
do $prior_platform$ begin
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20ao')
  or (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20ao_cp6_invoice_retail')<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version='20260922135612' and name='erp_v2_6_20ao_cp6_invoice_retail'
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='696a75c5969b756ce1973191a757a8c7deade06cb57e96dc5a16d648a4c48520')
 then raise exception 'AQ_PRIOR_PLATFORM_DRIFT';end if;
end $prior_platform$;
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
do $prior_platform$ begin
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20ap')
  or (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20ap_cp6_connected_import_materials')<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version='20260922135615' and name='erp_v2_6_20ap_cp6_connected_import_materials'
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='70503bb0247c811e066830ba752960a50b7afdfdb4c0c7697dee9a265ef1778a')
 then raise exception 'AQ_PRIOR_PLATFORM_DRIFT';end if;
end $prior_platform$;
do $capsule_guard$
declare r record;c record;e jsonb;boundary jsonb;actual jsonb;expected jsonb;
begin
 if not exists(select 1 from pg_class where oid='erp.cp6_v2620aq_rollback_capsule'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
  or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='erp.cp6_v2620aq_rollback_capsule'::regclass and a.grantee<>p.relowner)
  or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='erp.cp6_v2620aq_rollback_capsule'::regclass and a.grantee<>'postgres'::regrole)
  or exists(select 1 from pg_policy where polrelid='erp.cp6_v2620aq_rollback_capsule'::regclass)
  or exists(select 1 from pg_trigger where tgrelid='erp.cp6_v2620aq_rollback_capsule'::regclass and not tgisinternal)
  or (select count(*) from erp.cp6_v2620aq_rollback_capsule)<>1 then raise exception 'AQ_CAPSULE_SECURITY_OR_COUNT';end if;
 -- Match the complete visible column/constraint/index shape to the source-pinned
 -- AN template. Names of generated capsule indexes are intentionally immaterial.
 for r in select unnest(array['erp.cp6_v2620aq_rollback_capsule','erp.cp6_v2620an_rollback_capsule']) as rel loop
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel::regclass)) into actual;
  if expected is null then expected:=actual;elsif actual is distinct from expected then raise exception 'AQ_CAPSULE_SHAPE_DRIFT';end if;
 end loop;
 select boundary_snapshot into boundary from erp.cp6_v2620aq_rollback_capsule limit 1;
 if boundary is null or exists(select 1 from erp.cp6_v2620aq_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before']) then raise exception 'AQ_CAPSULE_BOUNDARY';end if;
 for r in select * from jsonb_each('{"erp.save_contractor_material_issue_draft_v2(jsonb,uuid,bigint)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.save_contractor_material_issue_draft_v2(jsonb,uuid,bigint)","installed_sha256":"4d2e9b98d26dcda0c054de76d82906e0819af0525ed2327d476d78fbb59133f7","owner":"postgres","predecessor_sha256":"d770d21f6bdb3962818fa4c677367ec15998420e5e92c195e1feb538a2227e20"}}'::jsonb) loop
  select * into c from erp.cp6_v2620aq_rollback_capsule where object_regidentity=r.key;e:=r.value;
  if c.object_regidentity is null or c.definition_sha256 is distinct from e->>'predecessor_sha256'
   or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex') is distinct from e->>'predecessor_sha256'
   or c.installed_definition_sha256 is distinct from e->>'installed_sha256'
   or c.owner_snapshot is distinct from e->>'owner' or to_jsonb(c.acl_snapshot) is distinct from e->'acl' then
   raise exception 'AQ_CAPSULE_SOURCE_DRIFT: %',r.key;
  end if;
 end loop;
end $capsule_guard$;
do $aq_platform$ begin
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20aq')
  or (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20aq_cp6_accessory_lock_order')<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version='20260922161019' and name='erp_v2_6_20aq_cp6_accessory_lock_order'
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='34cee78ee58f612187f7683280565ce2651e788e61efb62ced5e8c4dce7f9ada')
 then raise exception 'AR_PRIOR_AQ_PLATFORM_DRIFT';end if;
end $aq_platform$;
do $capsule_guard$
declare r record;c record;e jsonb;boundary jsonb;actual jsonb;expected jsonb;
begin
 if not exists(select 1 from pg_class where oid='erp.cp6_v2620ar_rollback_capsule'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
  or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='erp.cp6_v2620ar_rollback_capsule'::regclass and a.grantee<>p.relowner)
  or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='erp.cp6_v2620ar_rollback_capsule'::regclass and a.grantee<>'postgres'::regrole)
  or exists(select 1 from pg_policy where polrelid='erp.cp6_v2620ar_rollback_capsule'::regclass)
  or exists(select 1 from pg_trigger where tgrelid='erp.cp6_v2620ar_rollback_capsule'::regclass and not tgisinternal)
  or (select count(*) from erp.cp6_v2620ar_rollback_capsule)<>3 then raise exception 'AR_CAPSULE_SECURITY_OR_COUNT';end if;
 -- Match the complete visible column/constraint/index shape to the source-pinned
 -- AN template. Names of generated capsule indexes are intentionally immaterial.
 for r in select unnest(array['erp.cp6_v2620ar_rollback_capsule','erp.cp6_v2620an_rollback_capsule']) as rel loop
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel::regclass)) into actual;
  if expected is null then expected:=actual;elsif actual is distinct from expected then raise exception 'AR_CAPSULE_SHAPE_DRIFT';end if;
 end loop;
 select boundary_snapshot into boundary from erp.cp6_v2620ar_rollback_capsule limit 1;
 if boundary is null or exists(select 1 from erp.cp6_v2620ar_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before']) then raise exception 'AR_CAPSULE_BOUNDARY';end if;
 for r in select * from jsonb_each('{"erp.post_opening_balance(uuid)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.post_opening_balance(uuid)","installed_sha256":"be2fdd37cd4c0959b81aeb7444512a51b6b7471fee4af1d1846b18f8862c16c6","owner":"postgres","predecessor_sha256":"8e13d9c07bfba22931e62591a968a6843358765e2350cfa6b9f38b76a8620f2b"},"erp.prepare_migration_opening_balance(uuid,text)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.prepare_migration_opening_balance(uuid,text)","installed_sha256":"0705ea5c2766d96d97d9e79a528d5321fc25ad07ce31f2565799b077bac49ff1","owner":"postgres","predecessor_sha256":"1ca3941a03a7d2eb39d1904547edc4b50e088d60ffbcb04215f8bf71a7d708a0"},"erp.save_initial_import_action_v1(text,jsonb,uuid)":{"acl":["postgres=X/postgres"],"identity":"erp.save_initial_import_action_v1(text,jsonb,uuid)","installed_sha256":"0b6ac7f6e0a40c8274655f356c602190f2e33cbd722d0fa82809938c7ec39a94","owner":"postgres","predecessor_sha256":"a9229b1e5ce5180fb7da9720c09d2718eb70c700c2c0759303dc38d8c6085dce"}}'::jsonb) loop
  select * into c from erp.cp6_v2620ar_rollback_capsule where object_regidentity=r.key;e:=r.value;
  if c.object_regidentity is null or c.definition_sha256 is distinct from e->>'predecessor_sha256'
   or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex') is distinct from e->>'predecessor_sha256'
   or c.installed_definition_sha256 is distinct from e->>'installed_sha256'
   or c.owner_snapshot is distinct from e->>'owner' or to_jsonb(c.acl_snapshot) is distinct from e->'acl' then
   raise exception 'AR_CAPSULE_SOURCE_DRIFT: %',r.key;
  end if;
 end loop;
end $capsule_guard$;
do $ar_platform$ begin
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20ar')
  or (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20ar_cp6_opening_overlap')<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version='20260922185015' and name='erp_v2_6_20ar_cp6_opening_overlap'
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='c5c973d47a4665723351205ccbcbe2c658c57bff7230f5552c5c2b7ca757371e')
 then raise exception 'AS_PRIOR_AR_PLATFORM_DRIFT';end if;
end $ar_platform$;
do $capsule_guard$
declare r record;c record;e jsonb;boundary jsonb;actual jsonb;expected jsonb;
begin
 if not exists(select 1 from pg_class where oid='erp.cp6_v2620as_rollback_capsule'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
  or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='erp.cp6_v2620as_rollback_capsule'::regclass and a.grantee<>p.relowner)
  or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='erp.cp6_v2620as_rollback_capsule'::regclass and a.grantee<>'postgres'::regrole)
  or exists(select 1 from pg_policy where polrelid='erp.cp6_v2620as_rollback_capsule'::regclass)
  or exists(select 1 from pg_trigger where tgrelid='erp.cp6_v2620as_rollback_capsule'::regclass and not tgisinternal)
  or (select count(*) from erp.cp6_v2620as_rollback_capsule)<>4 then raise exception 'AS_CAPSULE_SECURITY_OR_COUNT';end if;
 -- Match the complete visible column/constraint/index shape to the source-pinned
 -- AN template. Names of generated capsule indexes are intentionally immaterial.
 for r in select unnest(array['erp.cp6_v2620as_rollback_capsule','erp.cp6_v2620an_rollback_capsule']) as rel loop
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel::regclass)) into actual;
  if expected is null then expected:=actual;elsif actual is distinct from expected then raise exception 'AS_CAPSULE_SHAPE_DRIFT';end if;
 end loop;
 select boundary_snapshot into boundary from erp.cp6_v2620as_rollback_capsule limit 1;
 if boundary is null or exists(select 1 from erp.cp6_v2620as_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before']) then raise exception 'AS_CAPSULE_BOUNDARY';end if;
 for r in select * from jsonb_each('{"erp.complete_initial_import_wip_v1(jsonb)":{"acl":["postgres=X/postgres"],"identity":"erp.complete_initial_import_wip_v1(jsonb)","installed_sha256":"c93f8cca4eeed85d23c1dcd664a9b2d880446e350bc3283fb83faf62c7b5deaa","owner":"postgres","predecessor_sha256":"3def50a323533488fb3778ec99553f2f13511741e79ce84432cd531de294044b"},"erp.sync_material_cost_revaluation(uuid)":{"acl":["postgres=X/postgres"],"identity":"erp.sync_material_cost_revaluation(uuid)","installed_sha256":"bb19f298f2d8b4eeeea78130c0bb70278dfbe1becbc7aa632ac22fef3285ea51","owner":"postgres","predecessor_sha256":"ae4ad29be5dbba3db18da7da9256723c86b3388d0f0d6293db6271170f078461"},"erp.sync_po_hpp_to_gl(uuid,date)":{"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.sync_po_hpp_to_gl(uuid,date)","installed_sha256":"726f1abc349bac4f8ca55ae0d3c2550c84316923e513978bd9eb8f34f8274ce1","owner":"postgres","predecessor_sha256":"0f460c85c5c7d6cbd0ddf30dfa78336b8016c6a83d39f5dc9caf3ac2ca6a4418"},"erp.validate_initial_import_production_v1(uuid)":{"acl":["postgres=X/postgres"],"identity":"erp.validate_initial_import_production_v1(uuid)","installed_sha256":"ba9486ba8500ad6d3b2dde5d57b9759e3b53b382d95e41d13b74834e637f356f","owner":"postgres","predecessor_sha256":"85bb827bd1bea270a3a922fc497661adc4b044307e30d69048c8d72babac9be0"}}'::jsonb) loop
  select * into c from erp.cp6_v2620as_rollback_capsule where object_regidentity=r.key;e:=r.value;
  if c.object_regidentity is null or c.definition_sha256 is distinct from e->>'predecessor_sha256'
   or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex') is distinct from e->>'predecessor_sha256'
   or c.installed_definition_sha256 is distinct from e->>'installed_sha256'
   or c.owner_snapshot is distinct from e->>'owner' or to_jsonb(c.acl_snapshot) is distinct from e->'acl' then
   raise exception 'AS_CAPSULE_SOURCE_DRIFT: %',r.key;
  end if;
 end loop;
end $capsule_guard$;
do $as_platform$ begin
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20as')
  or (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20as_cp6_event_dates_product_identity')<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version='20260922210815' and name='erp_v2_6_20as_cp6_event_dates_product_identity'
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='d13e46b3451386309a0a8dc1c89a4817ad8751568b9377f94c790832f8fa53a3')
 then raise exception 'AT_PRIOR_AS_PLATFORM_DRIFT';end if;
end $as_platform$;
do $capsule_guard$
declare r record;c record;e jsonb;boundary jsonb;actual jsonb;expected jsonb;
begin
 if not exists(select 1 from pg_class where oid='erp.cp6_v2620at_rollback_capsule'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
  or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='erp.cp6_v2620at_rollback_capsule'::regclass and a.grantee<>p.relowner)
  or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='erp.cp6_v2620at_rollback_capsule'::regclass and a.grantee<>'postgres'::regrole)
  or exists(select 1 from pg_policy where polrelid='erp.cp6_v2620at_rollback_capsule'::regclass)
  or exists(select 1 from pg_trigger where tgrelid='erp.cp6_v2620at_rollback_capsule'::regclass and not tgisinternal)
  or (select count(*) from erp.cp6_v2620at_rollback_capsule)<>1 then raise exception 'AT_CAPSULE_SECURITY_OR_COUNT';end if;
 -- Match the complete visible column/constraint/index shape to the source-pinned
 -- AN template. Names of generated capsule indexes are intentionally immaterial.
 for r in select unnest(array['erp.cp6_v2620at_rollback_capsule','erp.cp6_v2620an_rollback_capsule']) as rel loop
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel::regclass)) into actual;
  if expected is null then expected:=actual;elsif actual is distinct from expected then raise exception 'AT_CAPSULE_SHAPE_DRIFT';end if;
 end loop;
 select boundary_snapshot into boundary from erp.cp6_v2620at_rollback_capsule limit 1;
 if boundary is null or exists(select 1 from erp.cp6_v2620at_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before']) then raise exception 'AT_CAPSULE_BOUNDARY';end if;
 for r in select * from jsonb_each('{"erp.complete_initial_import_wip_v1(jsonb)":{"acl":["postgres=X/postgres"],"identity":"erp.complete_initial_import_wip_v1(jsonb)","installed_sha256":"a2b61b6ebcc6bfdca9e52a841f115fcbc3a051c58799fa9c95f3298e9fb82f09","owner":"postgres","predecessor_sha256":"c93f8cca4eeed85d23c1dcd664a9b2d880446e350bc3283fb83faf62c7b5deaa"}}'::jsonb) loop
  select * into c from erp.cp6_v2620at_rollback_capsule where object_regidentity=r.key;e:=r.value;
  if c.object_regidentity is null or c.definition_sha256 is distinct from e->>'predecessor_sha256'
   or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex') is distinct from e->>'predecessor_sha256'
   or c.installed_definition_sha256 is distinct from e->>'installed_sha256'
   or c.owner_snapshot is distinct from e->>'owner' or to_jsonb(c.acl_snapshot) is distinct from e->'acl' then
   raise exception 'AT_CAPSULE_SOURCE_DRIFT: %',r.key;
  end if;
 end loop;
end $capsule_guard$;
do $as_platform$ begin
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20at')
  or (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20at_cp6_wip_temporal_identity')<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version='20260923005153' and name='erp_v2_6_20at_cp6_wip_temporal_identity'
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='5e1ea5bfba73ada9aba5a8561efa9056b02154025d39bd10d47d3e4f2494110d')
 then raise exception 'AU_PRIOR_AT_PLATFORM_DRIFT';end if;
end $as_platform$;
do $capsule_guard$
declare r record;c record;e jsonb;boundary jsonb;actual jsonb;expected jsonb;
begin
 if not exists(select 1 from pg_class where oid='erp.cp6_v2620au_rollback_capsule'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
  or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='erp.cp6_v2620au_rollback_capsule'::regclass and a.grantee<>p.relowner)
  or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='erp.cp6_v2620au_rollback_capsule'::regclass and a.grantee<>'postgres'::regrole)
  or exists(select 1 from pg_policy where polrelid='erp.cp6_v2620au_rollback_capsule'::regclass)
  or exists(select 1 from pg_trigger where tgrelid='erp.cp6_v2620au_rollback_capsule'::regclass and not tgisinternal)
  or (select count(*) from erp.cp6_v2620au_rollback_capsule)<>6 then raise exception 'AU_CAPSULE_SECURITY_OR_COUNT';end if;
 -- Match the complete visible column/constraint/index shape to the source-pinned
 -- AN template. Names of generated capsule indexes are intentionally immaterial.
 for r in select unnest(array['erp.cp6_v2620au_rollback_capsule','erp.cp6_v2620an_rollback_capsule']) as rel loop
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel::regclass)) into actual;
  if expected is null then expected:=actual;elsif actual is distinct from expected then raise exception 'AU_CAPSULE_SHAPE_DRIFT';end if;
 end loop;
 select boundary_snapshot into boundary from erp.cp6_v2620au_rollback_capsule limit 1;
 if boundary is null or exists(select 1 from erp.cp6_v2620au_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before']) then raise exception 'AU_CAPSULE_BOUNDARY';end if;
 for r in select * from jsonb_each('{"erp.assert_product_identity_time(uuid,timestamp with time zone,text)":{"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.assert_product_identity_time(uuid,timestamp with time zone,text)","installed_sha256":"4e289eed53f2618b84c08b53a6e27453c3545ef2fe199a12e4ef699d8ce347f1","owner":"postgres","predecessor_sha256":"cefde799d6ebd857309a0cc6b69616ce7aefbf0d67b6f06f4f8faad27b609950"},"erp.cancel_product_identity_successor(uuid,text)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.cancel_product_identity_successor(uuid,text)","installed_sha256":"a6e10c692acab32220bfd52c58d7b991cd7007a795755bf662c50856010cf563","owner":"postgres","predecessor_sha256":"1009952108f1d312cfa7d7999ec2e3b2c340716f33a8b0c1f86821e7020965e1"},"erp.edit_product_identity_effective(uuid,text,uuid,uuid,text,uuid,text,timestamp with time zone,text)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.edit_product_identity_effective(uuid,text,uuid,uuid,text,uuid,text,timestamp with time zone,text)","installed_sha256":"b856072c5e85cc3694850ec953bcd32a38bf254001b79b85effe420ff2aa710c","owner":"postgres","predecessor_sha256":"5eb8fa558cb4f7a605638da57efa42729bb487c22b0d76bdb7b5b361ab9ec8dd"},"erp.guard_product_delete_after_identity_history()":{"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.guard_product_delete_after_identity_history()","installed_sha256":"7ceb40dcb1a60afeb283721f018d2d4c36205ef8b839d3174a2e31758d032ba4","owner":"postgres","predecessor_sha256":"dc7c53e09f1b5285b66daa03350dc6067deabe735ab140ec4ec521a38bd9e017"},"erp.guard_product_identity_version_metadata()":{"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.guard_product_identity_version_metadata()","installed_sha256":"9fdc460239a20b798072fe15296db1f9d67f0d5fbb5bd9c9385c0dff3d282403","owner":"postgres","predecessor_sha256":"a087c4218c34a9e542b2f4d74d37ad0e66c61be0371a967da1ea984370ee9013"},"erp.validate_product_identity_period()":{"acl":["postgres=X/postgres"],"identity":"erp.validate_product_identity_period()","installed_sha256":"72aa7e9ca05c81f1a760ec3a7044a2800f504ff99d3ce6cf2f1e5af54db827ed","owner":"postgres","predecessor_sha256":"84d4e9ec250aedf192877be6a12e9c789dbd883e954086004c7f43152fc01298"}}'::jsonb) loop
  select * into c from erp.cp6_v2620au_rollback_capsule where object_regidentity=r.key;e:=r.value;
  if c.object_regidentity is null or c.definition_sha256 is distinct from e->>'predecessor_sha256'
   or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex') is distinct from e->>'predecessor_sha256'
   or c.installed_definition_sha256 is distinct from e->>'installed_sha256'
   or c.owner_snapshot is distinct from e->>'owner' or to_jsonb(c.acl_snapshot) is distinct from e->'acl' then
   raise exception 'AU_CAPSULE_SOURCE_DRIFT: %',r.key;
  end if;
 end loop;
end $capsule_guard$;
do $au_platform$ begin
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20au')
  or (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20au_cp6_controlled_product_lifecycle')<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version='20260923045944' and name='erp_v2_6_20au_cp6_controlled_product_lifecycle'
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='7d6265f081125499cb1813fe3f24c3b203363252727b5dcdfc7f74e311b85481')
 then raise exception 'AV_PRIOR_AU_PLATFORM_DRIFT';end if;
end $au_platform$;
create table erp.cp6_v2620av_rollback_capsule(like erp.cp6_v2620an_rollback_capsule including all);
alter table erp.cp6_v2620av_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620av_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620av_rollback_capsule(object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),i.identity,pg_get_functiondef(p.oid),
 encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
 array(select a::text from unnest(p.proacl)a order by a::text),pg_get_userbyid(p.proowner)
from unnest(array['erp.edit_product_identity_effective(uuid,text,uuid,uuid,text,uuid,text,timestamp with time zone,text)','erp.create_manual_bs_case_v2(jsonb,uuid)','erp.post_rework_completion(uuid)']) i(identity)
join pg_proc p on p.oid=i.identity::regprocedure join pg_namespace n on n.oid=p.pronamespace;
do $before_data$ declare v_table text;v_hash jsonb;v_before jsonb; begin
 v_before:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620av_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_before:=v_before||jsonb_build_object(v_table,v_hash);
 end loop;

 update erp.cp6_v2620av_rollback_capsule set boundary_snapshot=jsonb_build_object('before',v_before,'platform_before',(select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations t where not(false)),'markers_before',(select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from erp.schema_migrations t where not(false)));
end $before_data$;
create table erp.bs_case_manual_origins_v1 (
 bs_case_id uuid primary key references erp.bs_cases(id),
 origin_type text not null check (origin_type in ('LEGACY','OUT_OF_NOWHERE')),
 recorded_at timestamptz not null default statement_timestamp()
);
alter table erp.bs_case_manual_origins_v1 enable row level security;
revoke all on erp.bs_case_manual_origins_v1 from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.guard_bs_case_manual_origin_immutable_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
begin
  raise exception 'BS_MANUAL_ORIGIN_IMMUTABLE: asal BS manual tidak boleh diubah atau dihapus';
end;
$function$;
revoke all on function erp.guard_bs_case_manual_origin_immutable_v1() from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.latest_new_stock_physical_at_v1(p_product_id uuid)
 RETURNS timestamp with time zone
 LANGUAGE sql
 STABLE
 SET search_path TO ''
AS $function$
select max(f.physical_at) from (
  select l.produced_at as physical_at from erp.fg_lots l
  where l.product_id=p_product_id
    and not exists(select 1 from erp.rework_orders r where r.good_fg_lot_id=l.id)
  union all
  select b.physical_at from erp.bs_cases b
  where b.product_id=p_product_id
    and (b.qc_item_id is not null or b.source_laundry_bs_allocation_id is not null
      or exists(select 1 from erp.bs_case_manual_origins_v1 o where o.bs_case_id=b.id and o.origin_type='OUT_OF_NOWHERE'))
) f
$function$;
revoke all on function erp.latest_new_stock_physical_at_v1(uuid) from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.assert_new_stock_cutoff_coverage_v1()
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO ''
AS $function$
declare
  v_registry jsonb:='{"erp.accessory_bom_versions.product_id":{"class":"MASTER","reason":"Effective-dated accessory BOM; no stock instant"},"erp.bs_cases.product_id":{"class":"NEW_STOCK_FACT","reason":"physical_at of QC/laundry BS and manual OUT_OF_NOWHERE BS"},"erp.contractor_accessory_reimbursement_entitlements.product_id":{"class":"DERIVED","reason":"Accounting entitlement of an FG lot"},"erp.fg_accessory_cost_snapshots.product_id":{"class":"DERIVED","reason":"Cost snapshot of an FG lot"},"erp.fg_adjustment_items.product_id":{"class":"MOVEMENT","reason":"Adjusts an existing lot"},"erp.fg_inventory_balances.product_id":{"class":"DERIVED","reason":"Balance cache keyed by product/location/grade"},"erp.fg_lots.product_id":{"class":"NEW_STOCK_FACT","reason":"produced_at of every lot except GOOD returned by rework"},"erp.fg_stock_movements.product_id":{"class":"MOVEMENT","reason":"Movement of an existing lot"},"erp.journal_lines.product_id":{"class":"ACCOUNTING","reason":"Journal dimension"},"erp.laundry_receipt_batch_size_lines.bs_product_id":{"class":"SOURCE_DOCUMENT","reason":"Laundry receipt input; the BS fact is bs_cases"},"erp.laundry_receipt_bs_product_allocations.product_id":{"class":"SOURCE_DOCUMENT","reason":"Validated as NEW_STOCK; the BS fact is bs_cases"},"erp.non_po_hpp_gl_sync_events_v2620f.product_id":{"class":"ACCOUNTING","reason":"HPP to GL synchronisation event"},"erp.opening_balance_items.product_id":{"class":"SOURCE_DOCUMENT","reason":"Opening document; facts are OPENING lots and LEGACY BS"},"erp.po_accessory_bom_commitments.product_id":{"class":"MASTER","reason":"PO accessory BOM commitment"},"erp.product_conversions.from_product_id":{"class":"SOURCE_DOCUMENT","reason":"Conversion source, validated as EXISTING_STOCK"},"erp.product_conversions.to_product_id":{"class":"SOURCE_DOCUMENT","reason":"Conversion target; the fact is the CONVERSION lot in fg_lots"},"erp.product_identity_mutation_context_v1.product_id":{"class":"AUTHORIZATION","reason":"Private one-use identity edit context"},"erp.product_price_versions.product_id":{"class":"MASTER","reason":"Effective-dated price"},"erp.qc_inspection_items.final_product_id":{"class":"SOURCE_DOCUMENT","reason":"QC input; the facts are fg_lots and bs_cases"},"erp.sales_items.product_id":{"class":"SALES","reason":"Sale of existing stock"},"erp.sales_return_items.product_id":{"class":"SALES","reason":"Return of sold stock"},"erp.stock_explainability_snapshots.product_id":{"class":"REPORT","reason":"Stock explanation snapshot"},"erp.stock_policy_versions.product_id":{"class":"MASTER","reason":"Effective-dated stock policy"}}';
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
revoke all on function erp.assert_new_stock_cutoff_coverage_v1() from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.edit_product_identity_effective(p_product_id uuid, p_sku text, p_model_id uuid, p_brand_id uuid, p_color_name text, p_size_id uuid, p_product_name text, p_effective_from timestamp with time zone DEFAULT clock_timestamp(), p_reason text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  p erp.products%rowtype; n erp.products%rowtype; child erp.products%rowtype; r record; v_root uuid; v_new uuid; v_used boolean; v_eff timestamptz:=coalesce(p_effective_from,clock_timestamp()); v_last timestamptz;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan perubahan SKU wajib diisi'; end if;
  if nullif(trim(p_sku),'') is null or nullif(trim(p_color_name),'') is null or nullif(trim(p_product_name),'') is null then
    raise exception 'SKU, warna, dan nama produk wajib diisi';
  end if;

  perform erp.pocket_period_lock_v1();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select identity_root_id into v_root from erp.products where id=p_product_id;
  if v_root is not null then perform pg_advisory_xact_lock(hashtextextended('SKUROOT:'||v_root::text,0));end if;
  select * into p from erp.products where id=p_product_id for update;
  if p.id is null then raise exception 'SKU tidak ditemukan'; end if;
  p_sku:=btrim(p_sku);p_color_name:=btrim(p_color_name);p_product_name:=btrim(p_product_name);
  if p_model_id is null or p_brand_id is null or p_size_id is null or not isfinite(v_eff) then
    raise exception 'Identitas dan tanggal efektif SKU wajib lengkap dan finite';
  end if;

  if row(p.sku,p.model_id,p.brand_id,p.color_name,p.size_id)
     is not distinct from row(p_sku,p_model_id,p_brand_id,p_color_name,p_size_id) then
    if p.product_name is not distinct from p_product_name then return p.id;end if;
    update erp.products set product_name=p_product_name,updated_at=statement_timestamp() where id=p.id;
    insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason,new_data)
    values('products',p.id,'UPDATE',erp.current_app_user_id(),p_reason,jsonb_build_object('product_name',p_product_name));
    return p.id;
  end if;


  v_used:=false;
  for r in
    select ns.nspname,c.relname,a.attname
    from pg_constraint fk join pg_class c on c.oid=fk.conrelid
    join pg_namespace ns on ns.oid=c.relnamespace
    join pg_attribute a on a.attrelid=c.oid and a.attnum=any(fk.conkey)
    where fk.contype='f' and fk.confrelid='erp.products'::regclass
      and fk.conrelid<>'erp.products'::regclass
  loop
    execute format('select exists(select 1 from %I.%I where %I=$1)',r.nspname,r.relname,r.attname) into v_used using p.id;
    exit when v_used;
  end loop;
  if not v_used and not exists(select 1 from erp.products x where x.identity_root_id=p.identity_root_id and x.id<>p.id) then
    n:=p;n.sku:=p_sku;n.model_id:=p_model_id;n.brand_id:=p_brand_id;n.color_name:=p_color_name;n.size_id:=p_size_id;
    insert into erp.product_identity_mutation_context_v1 values(pg_backend_pid(),txid_current(),p.id,jsonb_build_array(p.id,p.sku,p.model_id,p.brand_id,p.color_name,p.size_id,p.identity_root_id,p.effective_from,p.effective_to,p.supersedes_product_id),jsonb_build_array(n.id,n.sku,n.model_id,n.brand_id,n.color_name,n.size_id,n.identity_root_id,n.effective_from,n.effective_to,n.supersedes_product_id));
    update erp.products
    set sku=trim(p_sku),model_id=p_model_id,brand_id=p_brand_id,color_name=trim(p_color_name),size_id=p_size_id,
        product_name=trim(p_product_name),updated_at=statement_timestamp()
    where id=p.id;
    insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason,new_data)
    values('products',p.id,'UPDATE',erp.current_app_user_id(),p_reason,
      jsonb_build_object('sku',p_sku,'model_id',p_model_id,'brand_id',p_brand_id,'color_name',p_color_name,'size_id',p_size_id));
    return p.id;
  end if;

  select * into child from erp.products where supersedes_product_id=p.id for update;
  if child.id is not null then
    if row(child.sku,child.model_id,child.brand_id,child.color_name,child.size_id,child.product_name,child.effective_from)
       is not distinct from row(p_sku,p_model_id,p_brand_id,p_color_name,p_size_id,p_product_name,v_eff) then return child.id;end if;
    raise exception 'Versi SKU sudah punya successor; gunakan versi paling akhir atau batalkan successor yang belum dipakai';
  end if;
  v_last:=erp.latest_new_stock_physical_at_v1(p.id);
  if v_last>=v_eff then
    raise exception 'Tanggal efektif SKU akan memotong histori produksi yang sudah tercatat (fakta fisik stok baru terakhir %). Pilih tanggal efektif sesudahnya.',v_last;
  end if;
  if v_eff<clock_timestamp()-interval '5 minutes' then
    raise exception 'Perubahan identitas SKU yang sudah punya histori hanya boleh berlaku mulai sekarang atau tanggal mendatang';
  end if;
  if v_eff<=p.effective_from or (p.effective_to is not null and v_eff>=p.effective_to) then
    raise exception 'Tanggal mulai perubahan harus berada setelah awal versi lama dan sebelum akhir versinya';
  end if;

  n:=p;n.effective_to:=v_eff;
  insert into erp.product_identity_mutation_context_v1 values(pg_backend_pid(),txid_current(),p.id,jsonb_build_array(p.id,p.sku,p.model_id,p.brand_id,p.color_name,p.size_id,p.identity_root_id,p.effective_from,p.effective_to,p.supersedes_product_id),jsonb_build_array(n.id,n.sku,n.model_id,n.brand_id,n.color_name,n.size_id,n.identity_root_id,n.effective_from,n.effective_to,n.supersedes_product_id));
  update erp.products set effective_to=v_eff,updated_at=statement_timestamp() where id=p.id;
  insert into erp.products(sku,model_id,brand_id,color_name,size_id,product_name,is_portal_visible,is_active,
                           identity_root_id,effective_from,effective_to,supersedes_product_id)
  values(trim(p_sku),p_model_id,p_brand_id,trim(p_color_name),p_size_id,trim(p_product_name),p.is_portal_visible,p.is_active,
         p.identity_root_id,v_eff,p.effective_to,p.id)
  returning id into v_new;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason,new_data)
  values('products',p.id,'UPDATE',erp.current_app_user_id(),p_reason,
    jsonb_build_object('successor_product_id',v_new,'effective_from',v_eff,'old_identity_preserved',true,'economics_shared_by_identity_root',true));
  return v_new;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.create_manual_bs_case_v2(p_payload jsonb, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_id uuid:=gen_random_uuid();
  v_type text:=upper(coalesce(p_payload->>'untracked_type',''));
  v_ref text:=nullif(btrim(p_payload->>'legacy_reference'),'');
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_physical timestamptz:=nullif(p_payload->>'physical_at','')::timestamptz;
  v_component jsonb;
  v_case erp.bs_cases%rowtype;
begin
  perform erp.require_internal();
  if v_type not in('LEGACY','OUT_OF_NOWHERE') then
    raise exception 'Manual BS is allowed only for LEGACY or OUT_OF_NOWHERE';
  end if;
  if v_ref is null then raise exception 'legacy_reference is required for manual BS traceability'; end if;
  if v_reason is null then raise exception 'change_reason is required'; end if;
  if v_physical is null or v_physical>clock_timestamp()+interval '5 minutes' then
    raise exception 'Valid non-future physical_at is required';
  end if;
  if coalesce(nullif(p_payload->>'qty_pcs','')::integer,0)<=0 then raise exception 'qty_pcs must be positive'; end if;
  v_hash:=erp._request_hash(p_payload);
  v_cached:=erp._idempotency_begin('create_manual_bs_case_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  if v_type='OUT_OF_NOWHERE' and nullif(p_payload->>'product_id','') is not null then
    perform erp.assert_product_identity_time(nullif(p_payload->>'product_id','')::uuid,v_physical,'NEW_STOCK');
  end if;
  perform set_config('app.change_reason',v_reason,true);
  insert into erp.bs_cases(
    id,bs_number,po_id,cutting_group_id,qc_item_id,product_id,
    detected_at_stage,cause_source,untracked_type,
    responsible_contractor_id,responsible_vendor_id,qty_pcs,status,
    physical_at,legacy_reference,notes
  ) values(
    v_id,coalesce(nullif(btrim(p_payload->>'bs_number'),''),
      'BS-MAN-'||to_char((v_physical AT TIME ZONE 'Asia/Jakarta'),'YYYYMMDD')||'-'||substr(v_id::text,1,8)),
    null,null,null,nullif(p_payload->>'product_id','')::uuid,
    'UNKNOWN','UNKNOWN',v_type,
    nullif(p_payload->>'responsible_contractor_id','')::uuid,
    nullif(p_payload->>'responsible_vendor_id','')::uuid,
    (p_payload->>'qty_pcs')::integer,'OPEN',v_physical,v_ref,
    nullif(btrim(p_payload->>'notes'),'')
  ) returning * into v_case;
  insert into erp.bs_case_manual_origins_v1(bs_case_id,origin_type) values(v_case.id,v_type);
  if p_payload?'components' then
    if jsonb_typeof(p_payload->'components')<>'array' then raise exception 'components must be an array'; end if;
    for v_component in select value from jsonb_array_elements(p_payload->'components') loop
      insert into erp.bs_case_components(
        bs_case_id,po_component_snapshot_id,work_component_id,completed_before_bs_qty,notes
      ) values(
        v_case.id,null,(v_component->>'work_component_id')::uuid,
        coalesce(nullif(v_component->>'completed_before_bs_qty','')::integer,0),
        nullif(btrim(v_component->>'notes'),'')
      );
    end loop;
  end if;
  select * into v_case from erp.bs_cases where id=v_case.id;
  v_response:=jsonb_build_object(
    'bs_case_id',v_case.id,'bs_number',v_case.bs_number,'status',v_case.status,
    'row_version',v_case.row_version,'untracked_type',v_case.untracked_type
  );
  return erp._idempotency_complete('create_manual_bs_case_v2',p_client_request_id,v_response);
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
end
$function$;
create trigger trg_bs_case_manual_origin_immutable before update or delete on erp.bs_case_manual_origins_v1
 for each row execute function erp.guard_bs_case_manual_origin_immutable_v1();
create trigger trg_bs_case_manual_origin_no_truncate before truncate on erp.bs_case_manual_origins_v1
 for each statement execute function erp.guard_bs_case_manual_origin_immutable_v1();
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule')
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
 if object_count<>7159 or fingerprint is distinct from 'f345b9f9cdefd97250814cb29c459cde447c1a26846354c516f058abb23a9fdf' then
  raise exception 'AV_INSTALLED_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
insert into erp.bs_case_manual_origins_v1(bs_case_id,origin_type) select b.id bs_case_id,'OUT_OF_NOWHERE'::text origin_type from erp.bs_cases b
 where coalesce((select a.new_data->>'untracked_type' from erp.audit_logs a where a.entity_type='bs_cases' and a.entity_id=b.id
   and a.action='INSERT' order by a.changed_at limit 1),b.untracked_type)='OUT_OF_NOWHERE';
update erp.cp6_v2620av_rollback_capsule set installed_definition_sha256=encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex');
do $after_data$ declare v_table text;v_hash jsonb;v_after jsonb; begin
 v_after:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620av_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_after:=v_after||jsonb_build_object(v_table,v_hash);
 end loop;

 if (v_after-'bs_case_manual_origins_v1') is distinct from (select boundary_snapshot->'before' from erp.cp6_v2620av_rollback_capsule limit 1) then raise exception 'AV_INSTALL_CHANGED_DATA';end if;
 if exists((select bs_case_id,origin_type from erp.bs_case_manual_origins_v1) except (select b.id bs_case_id,'OUT_OF_NOWHERE'::text origin_type from erp.bs_cases b
 where coalesce((select a.new_data->>'untracked_type' from erp.audit_logs a where a.entity_type='bs_cases' and a.entity_id=b.id
   and a.action='INSERT' order by a.changed_at limit 1),b.untracked_type)='OUT_OF_NOWHERE'))
  or exists((select b.id bs_case_id,'OUT_OF_NOWHERE'::text origin_type from erp.bs_cases b
 where coalesce((select a.new_data->>'untracked_type' from erp.audit_logs a where a.entity_type='bs_cases' and a.entity_id=b.id
   and a.action='INSERT' order by a.changed_at limit 1),b.untracked_type)='OUT_OF_NOWHERE') except (select bs_case_id,origin_type from erp.bs_case_manual_origins_v1))
 then raise exception 'AV_INSTALL_ORIGIN_BACKFILL_MISMATCH';end if;
 update erp.cp6_v2620av_rollback_capsule set boundary_snapshot=boundary_snapshot||jsonb_build_object('after',v_after);
end $after_data$;
do $coverage$ begin perform erp.assert_new_stock_cutoff_coverage_v1();end $coverage$;
insert into erp.schema_migrations(version,description) values('v2.6.20av','Identity family: NEW_STOCK physical cutoff, manual BS origin and rework GOOD as existing stock (AV rev2)');
do $capsule_guard$
declare r record;c record;e jsonb;boundary jsonb;actual jsonb;expected jsonb;
begin
 if not exists(select 1 from pg_class where oid='erp.cp6_v2620av_rollback_capsule'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
  or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='erp.cp6_v2620av_rollback_capsule'::regclass and a.grantee<>p.relowner)
  or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='erp.cp6_v2620av_rollback_capsule'::regclass and a.grantee<>'postgres'::regrole)
  or exists(select 1 from pg_policy where polrelid='erp.cp6_v2620av_rollback_capsule'::regclass)
  or exists(select 1 from pg_trigger where tgrelid='erp.cp6_v2620av_rollback_capsule'::regclass and not tgisinternal)
  or (select count(*) from erp.cp6_v2620av_rollback_capsule)<>3 then raise exception 'AV_CAPSULE_SECURITY_OR_COUNT';end if;
 -- Match the complete visible column/constraint/index shape to the source-pinned
 -- AN template. Names of generated capsule indexes are intentionally immaterial.
 for r in select unnest(array['erp.cp6_v2620av_rollback_capsule','erp.cp6_v2620an_rollback_capsule']) as rel loop
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel::regclass)) into actual;
  if expected is null then expected:=actual;elsif actual is distinct from expected then raise exception 'AV_CAPSULE_SHAPE_DRIFT';end if;
 end loop;
 select boundary_snapshot into boundary from erp.cp6_v2620av_rollback_capsule limit 1;
 if boundary is null or exists(select 1 from erp.cp6_v2620av_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before']) then raise exception 'AV_CAPSULE_BOUNDARY';end if;
 for r in select * from jsonb_each('{"erp.create_manual_bs_case_v2(jsonb,uuid)":{"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.create_manual_bs_case_v2(jsonb,uuid)","installed_sha256":"d9f44e4e5f9cd493558661cb0296ebe210f2ad79c5bf738f1e35d85c7b60700f","owner":"postgres","predecessor_sha256":"8d905e876d9ffd084412dda5840c666fc9637185605e18eaa298897cd631160c"},"erp.edit_product_identity_effective(uuid,text,uuid,uuid,text,uuid,text,timestamp with time zone,text)":{"acl":["authenticated=X/postgres","postgres=X/postgres","service_role=X/postgres"],"identity":"erp.edit_product_identity_effective(uuid,text,uuid,uuid,text,uuid,text,timestamp with time zone,text)","installed_sha256":"049f3e0ebe2eca3fd23182d854ce3210e77cde721e87ea223cd02e1ba15afccb","owner":"postgres","predecessor_sha256":"b856072c5e85cc3694850ec953bcd32a38bf254001b79b85effe420ff2aa710c"},"erp.post_rework_completion(uuid)":{"acl":["postgres=X/postgres","service_role=X/postgres"],"identity":"erp.post_rework_completion(uuid)","installed_sha256":"da2e61f07646849b517de25ef799c7a3d1d3edddaa016d2007e2715dbfed2f49","owner":"postgres","predecessor_sha256":"63116e419dbbb6e59296416793288d785a348a30cdc46aad7eb44d097444d6c3"}}'::jsonb) loop
  select * into c from erp.cp6_v2620av_rollback_capsule where object_regidentity=r.key;e:=r.value;
  if c.object_regidentity is null or c.definition_sha256 is distinct from e->>'predecessor_sha256'
   or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex') is distinct from e->>'predecessor_sha256'
   or c.installed_definition_sha256 is distinct from e->>'installed_sha256'
   or c.owner_snapshot is distinct from e->>'owner' or to_jsonb(c.acl_snapshot) is distinct from e->'acl' then
   raise exception 'AV_CAPSULE_SOURCE_DRIFT: %',r.key;
  end if;
 end loop;
end $capsule_guard$;
commit;
