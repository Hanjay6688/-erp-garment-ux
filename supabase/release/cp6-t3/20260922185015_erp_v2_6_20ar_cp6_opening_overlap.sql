-- CP6 AR: cross-route opening identity and shared lock order.
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
 if exists(select 1 from erp.schema_migrations where version='v2.6.20ar') or to_regclass('erp.cp6_v2620ar_rollback_capsule') is not null
  or exists(select 1 from supabase_migrations.schema_migrations where version>'20260922161019')
 then raise exception 'AR_EXACT_AQ_WITHOUT_SUCCESSOR_REQUIRED';end if;
end $admission$;
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule')
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
 if object_count<>7138 or fingerprint is distinct from 'f98542d5e20d22f6322319f16d8ed050fa0f230a6bb901db2b050c6c7d2d779e' then
  raise exception 'AR_PREDECESSOR_CATALOG_DRIFT';
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
create table erp.cp6_v2620ar_rollback_capsule(like erp.cp6_v2620an_rollback_capsule including all);
alter table erp.cp6_v2620ar_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620ar_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620ar_rollback_capsule(object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),i.identity,pg_get_functiondef(p.oid),
 encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
 array(select a::text from unnest(p.proacl)a order by a::text),pg_get_userbyid(p.proowner)
from unnest(array['erp.post_opening_balance(uuid)','erp.prepare_migration_opening_balance(uuid,text)','erp.save_initial_import_action_v1(text,jsonb,uuid)']) i(identity)
join pg_proc p on p.oid=i.identity::regprocedure join pg_namespace n on n.oid=p.pronamespace;
do $before_data$ declare v_table text;v_hash jsonb;v_before jsonb; begin
 v_before:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620ar_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_before:=v_before||jsonb_build_object(v_table,v_hash);
 end loop;

 update erp.cp6_v2620ar_rollback_capsule set boundary_snapshot=jsonb_build_object('before',v_before,'platform_before',(select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations t where not(false)),'markers_before',(select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from erp.schema_migrations t where not(false)));
end $before_data$;
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
  if current_setting('transaction_isolation')<>'read committed' then
    raise exception 'AR_OPENING_REQUIRES_READ_COMMITTED';
  end if;
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

  -- AR: all canonical posts share the lock acquired above. READ COMMITTED
  -- rechecks here after waiting, before creating any economic side effect.
  -- A legacy line has no imported source document/lot identity: an overlapping
  -- import cannot prove it represents additional opening rights or goods.
  -- Keep the inherited rules for separate imported documents/physical sources.
  if exists(
    select 1 from erp.opening_balance_items i
    join erp.opening_balance_items o on o.balance_type=i.balance_type
    join erp.opening_balance_headers oh on oh.id=o.opening_id
    left join erp.products ip on ip.id=i.product_id
    left join erp.products op on op.id=o.product_id
    where i.opening_id=h.id and oh.id<>h.id and oh.status='POSTED'
      and ((h.migration_batch_id is null)<>(oh.migration_batch_id is null))
      and case i.balance_type
        when 'CUSTOMER_RECEIVABLE' then i.customer_id=o.customer_id
        when 'SUPPLIER_PAYABLE' then i.supplier_id=o.supplier_id
        when 'VENDOR_PAYABLE' then i.vendor_id=o.vendor_id
        when 'CONTRACTOR_RECEIVABLE' then i.contractor_id=o.contractor_id
        when 'CONTRACTOR_PAYABLE' then i.contractor_id=o.contractor_id
        when 'CASH_BANK' then i.cash_account_id=o.cash_account_id
        when 'MATERIAL' then i.material_id=o.material_id
          and i.location_id=o.location_id
          and (i.roll_id is null or o.roll_id is null or i.roll_id=o.roll_id)
        when 'FINISHED_GOODS' then i.product_id=o.product_id and exists(
          select 1 from erp.fg_stock_movements fm
          where fm.source_type='OPENING_BALANCE_ITEM' and fm.source_id=o.id
            and fm.movement_type='OPENING'
            and fm.location_id=coalesce(i.location_id,v_default_fg_location)
            and fm.quality_grade=coalesce(i.quality_grade,'GRADE_A'))
        when 'WIP' then
          (coalesce(i.model_id,ip.model_id) is null or coalesce(o.model_id,op.model_id) is null
            or coalesce(i.model_id,ip.model_id)=coalesce(o.model_id,op.model_id))
          and (i.stage is null or o.stage is null or i.stage=o.stage)
          and (i.contractor_id is null or o.contractor_id is null or i.contractor_id=o.contractor_id)
        when 'BS' then
          (i.product_id is null or o.product_id is null or i.product_id=o.product_id)
          and (coalesce(i.model_id,ip.model_id) is null or coalesce(o.model_id,op.model_id) is null
            or coalesce(i.model_id,ip.model_id)=coalesce(o.model_id,op.model_id))
          and (i.contractor_id is null or o.contractor_id is null or i.contractor_id=o.contractor_id)
          and (i.vendor_id is null or o.vendor_id is null or i.vendor_id=o.vendor_id)
        else false end
  ) then
    raise exception 'AR_OPENING_ROUTE_OVERLAP: saldo/stok awal sudah disahkan melalui jalur lain; rekonsiliasi sumber sebelum mengesahkan';
  end if;

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
CREATE OR REPLACE FUNCTION erp.prepare_migration_opening_balance(p_batch_id uuid, p_opening_number text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare b erp.migration_batches%rowtype;r record;j jsonb;v_header uuid;v_material uuid;v_roll uuid;v_product uuid;v_model uuid;v_contractor uuid;v_customer uuid;v_location uuid;v_supplier uuid;v_vendor uuid;v_cash uuid;v_type text;v_number text;v_hpp_method text;v_hpp_pct numeric;v_opening_item uuid;
begin
  perform erp.require_owner_admin();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into b from erp.migration_batches where id=p_batch_id for update;if b.id is null then raise exception 'Migration batch not found';end if;if b.status not in('READY','POSTING') then raise exception 'Migration batch must be READY/POSTING';end if;if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and validation_status<>'VALID') then raise exception 'Migration batch contains unvalidated/error rows';end if;
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
 v_catalog constant jsonb:='{"LAUNDRY_VENDOR": {"label": "Vendor laundry", "required": ["vendor_code", "vendor_name"], "fields": {"vendor_code": "Kode laundry", "vendor_name": "Nama laundry", "phone": "Telepon", "is_active": "Aktif", "notes": "Catatan"}}, "LOCATION": {"label": "Lokasi dan gudang", "required": ["location_code", "location_name", "location_type"], "fields": {"location_code": "Kode lokasi", "location_name": "Nama lokasi", "location_type": "Jenis lokasi", "is_active": "Aktif"}}, "CHART_ACCOUNT": {"label": "Akun buku besar", "required": ["account_code", "account_name", "account_type", "report_group", "normal_balance"], "fields": {"account_code": "Kode akun", "account_name": "Nama akun", "account_type": "Jenis akun", "report_group": "Kelompok laporan", "normal_balance": "Saldo normal", "parent_account_code": "Kode akun induk", "is_postable": "Boleh dipakai jurnal", "is_active": "Aktif"}}, "CASH_ACCOUNT": {"label": "Rekening kas dan bank", "required": ["cash_account_code", "cash_account_name", "coa_account_code", "account_kind"], "fields": {"cash_account_code": "Kode kas bank", "cash_account_name": "Nama kas bank", "coa_account_code": "Kode akun buku besar", "account_kind": "Jenis rekening", "is_active": "Aktif"}}, "BRAND": {"label": "Merek", "required": ["brand_code", "brand_name"], "fields": {"brand_code": "Kode merek", "brand_name": "Nama merek", "is_active": "Aktif"}}, "SIZE": {"label": "Ukuran", "required": ["size_code"], "fields": {"size_code": "Kode ukuran", "sort_order": "Urutan", "is_active": "Aktif"}}, "MODEL": {"label": "Model produk", "required": ["model_code", "model_name"], "fields": {"model_code": "Kode model", "model_name": "Nama model", "description": "Keterangan", "is_active": "Aktif"}}, "PRODUCT": {"label": "Produk per ukuran", "required": ["sku", "product_name", "model_code", "brand_code", "color_name", "size_code"], "fields": {"sku": "Kode produk", "product_name": "Nama produk", "model_code": "Kode model", "brand_code": "Kode merek", "color_name": "Warna", "size_code": "Kode ukuran", "is_active": "Aktif"}}, "CUSTOMER": {"label": "Pelanggan", "required": ["customer_code", "customer_name"], "fields": {"customer_code": "Kode pelanggan", "customer_name": "Nama pelanggan", "phone": "Telepon", "address": "Alamat", "is_active": "Aktif"}}, "SUPPLIER": {"label": "Supplier", "required": ["supplier_code", "supplier_name"], "fields": {"supplier_code": "Kode supplier", "supplier_name": "Nama supplier", "supplier_type": "Jenis supplier", "phone": "Telepon", "address": "Alamat", "is_active": "Aktif"}}, "CONTRACTOR": {"label": "Mandor", "required": ["contractor_code", "contractor_name"], "fields": {"contractor_code": "Kode mandor", "contractor_name": "Nama mandor", "contractor_type": "Jenis mandor", "attendance_required": "Wajib absensi", "is_active": "Aktif", "notes": "Catatan"}}, "ACCESSORY_CATEGORY": {"label": "Kategori aksesori", "required": ["category_code", "category_name", "base_uom_code"], "fields": {"category_code": "Kode kategori", "category_name": "Nama kategori", "base_uom_code": "Satuan dasar", "is_active": "Aktif", "notes": "Catatan"}}, "MATERIAL": {"label": "Bahan dan aksesori", "required": ["material_sku", "material_name", "material_type", "unit_code"], "fields": {"material_sku": "Kode bahan", "material_name": "Nama bahan", "material_type": "Jenis bahan", "unit_code": "Satuan dasar", "accessory_category_code": "Kode kategori aksesori", "is_active": "Aktif"}}, "MATERIAL_ROLL": {"label": "Stok awal kain per roll", "required": ["material_sku", "roll_number", "opening_qty", "unit_cost", "location_code", "control_key"], "fields": {"material_sku": "Kode bahan", "roll_number": "Nomor roll", "opening_qty": "Jumlah awal", "unit_cost": "Biaya per satuan", "location_code": "Kode gudang", "supplier_code": "Kode supplier", "notes": "Catatan", "control_key": "Kode total pembanding", "opening_source_key": "Kode rincian stok asal"}}, "OPENING_BALANCE_ITEM": {"label": "Stok dan saldo awal", "required": ["balance_type", "control_key"], "fields": {"balance_type": "Jenis saldo", "material_sku": "Kode bahan", "product_sku": "Kode produk", "brand_code": "Kode merek", "model_code": "Kode model", "color_name": "Warna", "size_code": "Kode ukuran", "location_code": "Kode gudang", "contractor_code": "Kode mandor", "customer_code": "Kode pelanggan", "supplier_code": "Kode supplier", "vendor_code": "Kode laundry", "cash_account_code": "Kode kas bank", "stage": "Tahap produksi", "qty": "Jumlah", "unit_cost": "Biaya per satuan", "amount": "Nominal", "quality_grade": "Kualitas", "hpp_input_method": "Cara isi HPP", "hpp_percent_of_price": "Persentase HPP", "notes": "Catatan", "control_key": "Kode total pembanding", "document_number": "Nomor dokumen asal", "document_date": "Tanggal dokumen asal", "due_date": "Tanggal jatuh tempo", "original_amount": "Nominal dokumen awal", "settled_before_cutover": "Sudah dibayar sebelum saldo awal", "opening_source_key": "Kode rincian stok asal", "source_kind": "Jenis sumber saldo", "po_number": "Nomor PO saldo fisik", "accessory_cost_included": "Biaya aksesoris sudah termasuk (true/false)"}}, "OPEN_PO": {"label": "Pesanan produksi berjalan", "required": ["po_number", "model_code", "status", "current_stage"], "fields": {"po_number": "Nomor pesanan", "model_code": "Kode model", "contractor_code": "Kode mandor", "target_qty_pcs": "Target buah", "target_dozens": "Target lusin", "status": "Status", "current_stage": "Tahap produksi", "physical_start_at": "Waktu mulai fisik", "notes": "Catatan"}}, "OPENING_CONTROL": {"label": "Total pembanding saldo awal", "required": ["control_key", "balance_type", "amount"], "fields": {"control_key": "Kode total pembanding", "balance_type": "Jenis saldo", "qty": "Total jumlah", "amount": "Total nominal", "notes": "Catatan"}}, "UNINVOICED_RECEIPT": {"label": "Penerimaan belum ditagih — sisa bahan dan asal biaya", "required": ["receipt_number", "receipt_line_number", "receipt_date", "supplier_code", "material_sku", "location_code", "qty", "unit_cost", "control_key"], "fields": {"receipt_number": "Nomor penerimaan asal", "receipt_line_number": "Nomor baris penerimaan", "receipt_date": "Tanggal penerimaan asal", "supplier_code": "Kode supplier", "material_sku": "Kode bahan", "location_code": "Kode gudang", "qty": "Jumlah belum ditagih", "unit_cost": "Biaya estimasi per satuan", "opening_source_key": "Kode rincian stok asal", "control_key": "Kode total pembanding", "notes": "Catatan"}}, "OPENING_ADVANCE": {"label": "Uang muka tersisa", "required": ["party_type", "party_code", "coa_account_code", "document_number", "document_date", "original_amount", "settled_before_cutover", "amount", "control_key"], "fields": {"party_type": "Jenis pihak", "party_code": "Kode pihak", "coa_account_code": "Kode akun uang muka", "document_number": "Nomor bukti uang muka", "document_date": "Tanggal uang muka", "original_amount": "Nominal asal", "settled_before_cutover": "Terpakai atau kembali sebelum saldo awal", "amount": "Sisa uang muka", "control_key": "Kode total pembanding"}}, "OPENING_COST_ORIGIN": {"label": "Asal biaya yang sudah terpakai sebelum cutover", "fields": {"supplier_code": "Kode supplier", "receipt_number": "Nomor penerimaan asal", "receipt_line_number": "Nomor baris penerimaan", "target_source_key": "Kode rincian WIP/BS/FG tujuan", "qty": "Jumlah bahan yang sudah terpakai", "notes": "Catatan"}, "required": ["supplier_code", "receipt_number", "receipt_line_number", "target_source_key", "qty"]}}'::jsonb;
begin
 perform erp.require_owner_admin();
 perform erp.require_permission('settings.erp.view');
 if v_action is null or v_action not in('CREATE','SAVE_FILE','VALIDATE','FINALIZE','ALLOCATE_CASH_ADVANCE','PREPAYMENT','WIP_OUTPUT') then raise exception 'Aksi impor tidak dikenal'; end if;
 if p_payload is null or jsonb_typeof(p_payload)<>'object' or octet_length(p_payload::text)>5242880 then
   raise exception 'Isi impor harus berupa objek dan maksimal 5 MB'; end if;
 -- AR: same lock order as native prepare/post, before any batch lock.
 if v_action='WIP_OUTPUT' then perform erp.pocket_period_lock_v1();end if;
 if v_action in('FINALIZE','WIP_OUTPUT') then
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
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule')
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
 if object_count<>7138 or fingerprint is distinct from '6c2d2d70ecb492992980874f65642b2742dbbf6db8d81bc3bd8777f2341c9604' then
  raise exception 'AR_INSTALLED_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
update erp.cp6_v2620ar_rollback_capsule set installed_definition_sha256=encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex');
do $after_data$ declare v_table text;v_hash jsonb;v_after jsonb; begin
 v_after:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620ar_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_after:=v_after||jsonb_build_object(v_table,v_hash);
 end loop;

 if v_after is distinct from (select boundary_snapshot->'before' from erp.cp6_v2620ar_rollback_capsule limit 1) then raise exception 'AR_INSTALL_CHANGED_DATA';end if;
 update erp.cp6_v2620ar_rollback_capsule set boundary_snapshot=boundary_snapshot||jsonb_build_object('after',v_after);
end $after_data$;
insert into erp.schema_migrations(version,description) values('v2.6.20ar','Prevent overlapping opening balances across legacy and import routes');
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
commit;
