-- CP6 AZ: material recost corrections dated from the physical movement. Release candidate of the T3 combined package; closed, drained maintenance required.
begin;
-- Built by scripts/cp6_t3_awx_release.py from supabase/dev/cp6_az_t1_family.sql (sha256 823fe2bbf072d543216f65c846188893ca6bec9455c17b5b93deae26c0ef5f0a): the T1 body below is unchanged apart from the
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
 for r in select * from jsonb_to_recordset('[{"marker":"v2.6.20ac","stamp":"20260915031500","name":"erp_v2_6_20ac_cp6_temporal_surface_closure","sha":"871fb32b1d4a1e7f9aedfef684b0f2c766092732c38552620eb394061f6240d1"},{"marker":"v2.6.20ad","stamp":"20260915113627","name":"erp_v2_6_20ad_cp6_opening_material_business_day","sha":"58f8f1050e6c325339d7400a43b8c8f3d2375d2067f0c418d3eedfe85430a563"},{"marker":"v2.6.20ae","stamp":"20260915201500","name":"erp_v2_6_20ae_cp6_opening_roll_integrity","sha":"0c6bbf77a68142ddfdae99761a5cc2cd6e2e538be50b391f3303922c748c39d6"},{"marker":"v2.6.20af","stamp":"20260916014332","name":"erp_v2_6_20af_cp6_posted_child_integrity","sha":"3764349ab314c7990f6202d3f0de38b516aff53df2a3b1c4f272bc49667f6db4"},{"marker":"v2.6.20ag","stamp":"20260916050822","name":"erp_v2_6_20ag_cp6_sale_reservation_lineage","sha":"085b84cb6917617c5e6a2d375fd5177542ebe3f021a20de48e239159e34d66c0"},{"marker":"v2.6.20ah","stamp":"20260916070451","name":"erp_v2_6_20ah_cp6_return_allocation_eligibility","sha":"ade908ca9f55b2333c5eac5793b41aaabe0d57879dbb233e428fc882bab5738b"},{"marker":"v2.6.20ai","stamp":"20260916090022","name":"erp_v2_6_20ai_cp6_work_source_lineage","sha":"1ea5a602c5a5fcc9697355d9cca526709a06ee20e4eb4cdb765b2b7345c18d25"},{"marker":"v2.6.20aj","stamp":"20260916202400","name":"erp_v2_6_20aj_cp6_rework_output_lineage","sha":"b36a6359c57ad59d93ea5cb8dc5f7e90a0dd9cd59d48c331b037aa365d400986"},{"marker":"v2.6.20ak","stamp":"20260917033516","name":"erp_v2_6_20ak_cp6_import_reference_preview","sha":"9d06a91bd849c80e1ef99a6ac8996863527a30ef3b4079188be58bd8f3d4311d"},{"marker":"v2.6.20al","stamp":"20260917054049","name":"erp_v2_6_20al_cp6_opening_value_validation","sha":"2d16461cababd4a27827cfb8de01dd993a3a343460cdf049d427b44dd4cb6ea2"},{"marker":"v2.6.20am","stamp":"20260921214120","name":"erp_v2_6_20am_cp6_transfer_integrity","sha":"8fff82f72f9c76dd032778fa43aa37fd3fde98c4304de033d9c484db54f04a60"},{"marker":"v2.6.20an","stamp":"20260921223438","name":"erp_v2_6_20an_cp6_cutting_selectors","sha":"4df51d65fdb9a644fe2eeba92af23446e0c0389a1ebf9f336a0a396c144d7b71"},{"marker":"v2.6.20ao","stamp":"20260922135612","name":"erp_v2_6_20ao_cp6_invoice_retail","sha":"696a75c5969b756ce1973191a757a8c7deade06cb57e96dc5a16d648a4c48520"},{"marker":"v2.6.20ap","stamp":"20260922135615","name":"erp_v2_6_20ap_cp6_connected_import_materials","sha":"70503bb0247c811e066830ba752960a50b7afdfdb4c0c7697dee9a265ef1778a"},{"marker":"v2.6.20aq","stamp":"20260922161019","name":"erp_v2_6_20aq_cp6_accessory_lock_order","sha":"34cee78ee58f612187f7683280565ce2651e788e61efb62ced5e8c4dce7f9ada"},{"marker":"v2.6.20ar","stamp":"20260922185015","name":"erp_v2_6_20ar_cp6_opening_overlap","sha":"c5c973d47a4665723351205ccbcbe2c658c57bff7230f5552c5c2b7ca757371e"},{"marker":"v2.6.20as","stamp":"20260922210815","name":"erp_v2_6_20as_cp6_event_dates_product_identity","sha":"d13e46b3451386309a0a8dc1c89a4817ad8751568b9377f94c790832f8fa53a3"},{"marker":"v2.6.20at","stamp":"20260923005153","name":"erp_v2_6_20at_cp6_wip_temporal_identity","sha":"5e1ea5bfba73ada9aba5a8561efa9056b02154025d39bd10d47d3e4f2494110d"},{"marker":"v2.6.20au","stamp":"20260923045944","name":"erp_v2_6_20au_cp6_controlled_product_lifecycle","sha":"7d6265f081125499cb1813fe3f24c3b203363252727b5dcdfc7f74e311b85481"},{"marker":"v2.6.20av","stamp":"20260923110000","name":"erp_v2_6_20av_cp6_identity_new_stock_cutoff","sha":"c63a1fe3bf76dfc396921e07f57eb043e3bb864425b3289a9546bf66e08169a5"},{"marker":"v2.6.20aw","stamp":"20260924010000","name":"erp_v2_6_20aw_cp6_close_readiness_engine","sha":"c38edc9da084f4a90ee615bde16e6fea72e1072f79d6820d9d3bef27cc2a8ecb"},{"marker":"v2.6.20ax","stamp":"20260924010100","name":"erp_v2_6_20ax_cp6_fg_unsourced_receipts","sha":"c736049386c65f75c82fa790b502cd32c999512738207b7be17d711185c3d9f2"},{"marker":"v2.6.20ay","stamp":"20260924010200","name":"erp_v2_6_20ay_cp6_hpp_dated_from_goods","sha":"0633aeb1b7935119d4784aea7e390f83605fef4c8df00a990270e7d67b144309"}]'::jsonb) as x(marker text,stamp text,name text,sha text) loop
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
 if object_count<>7295 or fingerprint is distinct from '484a5b40285a5e286f0bc8cbe432662b5aff35ab208569ce5a137f9c21dba958' then
  raise exception 'AZ_PREDECESSOR_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
do $historical_capsules$
declare r record;actual text;
begin
 for r in select * from jsonb_each_text('{"bs_resolution_v2619_rollback_capsule":"28ab388833da7da87384766ecaedadc66b4d048c303ee91e16f3939e34afdc39","bs_resolution_v2619a_rollback_capsule":"de8dfaab7b63b8742d383a089cdb05e73b629aad9f4df149e6a3c9fb590ef560","bs_resolution_v2619b_rollback_capsule":"d6d4f7457743d51679b5d25bf166ed69ca4b4f098cf5902ff985937531c2505d","bs_resolution_v2619c_rollback_capsule":"0207ba4f2ffba8ed61584709bbd884f1d2ee1a5981194fd7189a45afe8b3cbe1","cp3_r4_rollback_capsule":"7c01add62e66a4e2774a7199c2e77a04cca5e5942dbbba54d22cef720f82bc1d","cp45_v2617_rollback_capsule":"b9a43ce463de9905e94dd6538fd2a4952b0586a78c145f6f9d88aab7d6da3d80","cp45_v2617a_rollback_capsule":"b065dbcfdf1b59cb799e9f58caf6dd5ca7686e9f70826fce6a1ba8f140610022","cp4_v2616_rollback_capsule":"dde0a005dbe7cc93709bdfc6b961f4b9a76bf4db06fd7177d21dc79048af4d2f","cp6_v2620_rollback_capsule":"b42b94c2380f0768259a3d8f7fb645c76ebd6f92e8bae6a37d802352f7effd4f","cp6_v2620a_rollback_capsule":"67befaaf327d2591e1ca1d654132ee483eba39b6cbb4f891c4719d817155d448","cp6_v2620aa_rollback_capsule":"eb0d6fb4fcac2ac06929d577101e604428e9a04821813c342e5b831147dc8948","cp6_v2620ab_rollback_capsule":"3be9a9166e3a607962be819fbe23d38fe455290a7a970dc2aad068079bf30785","cp6_v2620ac_relation_rollback_capsule":"63c595c956e25135e1e032613831f5a08a734ba1f5c4746c46483c84517ad5ea","cp6_v2620ac_rollback_capsule":"51a8b08c9d96e66f03c2c8ba94ed3ed8fb15b26d1a2e4c65c58c614442dfa969","cp6_v2620ad_rollback_capsule":"5c3588109395b32ed743e0f4f5d789a3c59e3fffbab7469138f1f423c877ea9d","cp6_v2620ae_rollback_capsule":"6a75e02bf7b90c542fd9f2ac9534a2de066b047f5ffea65bffb1f83fa63c17f0","cp6_v2620af_rollback_capsule":"bfa89fc0e94d34b29405acedf551935f024942835f31cdc98f0f0983a9550288","cp6_v2620ag_rollback_capsule":"7ddfe6181f0c1c7439faf8a8150c542e958b3bafd8d18b5b2d1eb454fd7a85b7","cp6_v2620ah_rollback_capsule":"361be9321e5f4dadc7c7ec0e99ed746a98e7a4150178fc8355d23707c1507a93","cp6_v2620ai_rollback_capsule":"f2428dd712aa763b1379a4ae5b1a1e1e6ee175b355d8769b854a28f1355181c8","cp6_v2620aj_rollback_capsule":"8e24026dc90a2a92292c2cc6c8faa5fc3de991a19f326db494e0af2a518436f1","cp6_v2620ak_rollback_capsule":"dc7bfce7b9ee6a42e33cdf03cabd99d64435a4615245b2037fd6e4ee399aef10","cp6_v2620al_rollback_capsule":"c9e9aca042674efa5c6fa283e4b9ee47f3353ee9ee95b34e14ef1fd6b09bfde9","cp6_v2620am_rollback_capsule":"e781e631d06c6894c20b1fe6f9c65779f461d19c405c8ae74f28ed7d83ae6a26","cp6_v2620an_rollback_capsule":"ebfa8a281a32fe54babbdc209264ab422fde27f344d48561b90d2af022fe75b3","cp6_v2620ao_rollback_capsule":"b48103dcffcfb4c0c5172d2f11a8af809149c3c82584d0c24e6c740311e18cab","cp6_v2620ap_rollback_capsule":"10123ac8749107ffe9e25e74c9e3bc3080c0e15fc3d844bfcedf06043281e3f7","cp6_v2620aq_rollback_capsule":"35dd70bc3f6eacd8640eea6e22b11d4daaaac96bd7092cc8addefe47d0e3d4b8","cp6_v2620ar_rollback_capsule":"4a445445dc1641310fd3baa2b653bc2ff65b95e2a1f1ae53df2e0bb367fba6a8","cp6_v2620as_rollback_capsule":"8ffec1b6c558d3525b2c22754c2467e92463a201c4decdea0523e68b1a950aa9","cp6_v2620at_rollback_capsule":"8a7aca28f5e2e023d4828bae009962c34c6373740ccb26e30d69b6b661486fa2","cp6_v2620au_rollback_capsule":"f8a90e3df4dcaaf19bf33f1e3348e802e9c6357df673bd9bd524b0b2c1fb5fea","cp6_v2620av_rollback_capsule":"555750c028d4e47105289ffbb7d03bbbc08fa1b7adecf45b06a29bf3abb27b8f","cp6_v2620aw_rollback_capsule":"fe0df122c718e3b373f9527a1fe0bdd4bdb473e2e59d6a710057524fe8142475","cp6_v2620ax_rollback_capsule":"bde6ca64f2ef2df40caf5fe51234a549bff8f5f67ff5276d7344f274e0192465","cp6_v2620ay_rollback_capsule":"91e90d2e8b9b4a3aae597cff7e6fb41deedad244c0bfce25a131f52f55d15bfe","cp6_v2620b_rollback_capsule":"f9bf784bff0c54e647f491e257a9649fd0c3e6f10c39ddfc0944c961b9dd7601","cp6_v2620c_rollback_capsule":"f88b1f5890ee8e7041758971bf9c9a3ce2bd0a7be6989fb95332c2dd7fa139aa","cp6_v2620d_rollback_capsule":"fa300c5554da4bb6812c61d726fd64f66329c97b085fa7d6ad5d0d8e5ae31235","cp6_v2620e_rollback_capsule":"143cd291cf4c12e78ab61e74e02ed03b08a48832a5064671868ff2bd2e3e1da7","cp6_v2620f_rollback_capsule":"076133b098e821fc2713af559618adf8aa3e204908f810af440fda355fc7a57f","cp6_v2620g_rollback_capsule":"ed9f4cacb47bd026ad6bdea373d1aa87044ed12aa60323cea453e3187dc488c4","cp6_v2620h_rollback_capsule":"4c25a060a2df3c22cd6fa9ff0b297163e223118a0d930b97bf1282b4756d909d","cp6_v2620i_rollback_capsule":"051203d95c44968abd8594f5bd48e289c4ac9a6c9fa49a89eee1086ad6b2c166","cp6_v2620j_rollback_capsule":"1393a8085d0f58717b13048c9cc3f7e9969ac86c351d6dfefdd2d4f43a735bd2","cp6_v2620k_rollback_capsule":"55aa71061f616ea11b361f0fabee2fd892f6438cc3f567cb9c135552ade42409","cp6_v2620l_rollback_capsule":"b4278768fce4ef307795953c14f607278c43bf474d76d3362e477280be08eb39","cp6_v2620m_rollback_capsule":"4b5f89d7bc4557f92b47716fe15640ab244c424fc1279433eb806d9d91d234e9","cp6_v2620n_rollback_capsule":"46e5ea4524613bb7a386551ada9e06888ea35eb987f9f5b864457fdd18bc3bc1","cp6_v2620o_rollback_capsule":"044e6b1a050df7e2a1d36082b0451877bda01116c08f611dfceb7a666bdf03c8","cp6_v2620p_rollback_capsule":"b656abaf23276984567c6c8d87b311427463c008b5ecd762fbdd0c2df13795df","cp6_v2620q_rollback_capsule":"ab6c992fbaa87f19a4eba696a57a3972f98504a354d9b5fc3be660939f8ea20f","cp6_v2620r_rollback_capsule":"8eb5e0a38284c5f8e3fee56618893ba72feaae9d26605c9ca3874dae25045297","cp6_v2620s_rollback_capsule":"fb57810a75f8829a038ed61b3a1cabde33dccf1e384661bc6723c51e28b3e132","cp6_v2620t_rollback_capsule":"348db4650d788750da243500b49e23c1130fdb70bc4a6d1fdf136bf68aa21f30","cp6_v2620u_rollback_capsule":"720eb1984548a3c381387fbe4d34e3c6f00334c8a4549eab7e398b827dcb7dd4","cp6_v2620v_rollback_capsule":"573ef5842eefadf1c32469514f4c8498667c99aec20ef20651406e4f419f5f60","cp6_v2620w_rollback_capsule":"f4e2ca1d577dd9f2724cc90693e8ee8bff36365c696575b69c6463f3e8ca0324","cp6_v2620x_rollback_capsule":"064db1068b56daa69e409ae582cd8a99490cea75d269154baa4217f90d3ca0d1","cp6_v2620y_rollback_capsule":"e3b23429a7f002c85ca8de1f8c632df13a4a2fc4e4654c12e2431c212772841d","cp6_v2620z_rollback_capsule":"ad0436a1480af43070e9861cb7e28d4cf55c435edbffb5fe368ca7babb7863ef","cutting_bridge_v2618_rollback_capsule":"535d1abd25668bc5bee79d82a602afe5efe4e8ce313bf1fb5170ae2004e3cb2d","cutting_bridge_v2618a_rollback_capsule":"db0608e690b3d936fa20b62cc4cfb9b1f9e86718212526eb6131562578b8bf60"}'::jsonb) loop
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
from unnest(array['erp.sync_material_cost_revaluation(uuid)','erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)','erp.sync_finished_po_wip_residual(uuid,date,text)']) i(identity)
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
      v_target:=0;
    else
      v_target:=round((r.qty_signed*(r.unit_cost_snapshot-coalesce(r.original_unit_cost_snapshot,r.unit_cost_snapshot)))::numeric,2);
    end if;

    select s.applied_inventory_delta into v_old
    from erp.material_cost_revaluation_state s where s.movement_id=r.id for update;
    v_old:=coalesce(v_old,0);
    v_diff:=round(v_target-v_old,2);

    if abs(v_diff)>0.005 then
      v_date:=case when v_closed then v_e
        else least(greatest(v_e,erp._cp3_business_date(r.physical_at)),erp._cp3_business_date(statement_timestamp())) end;
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
      values(p_material_id,r.id,v_date,v_old,v_target,v_diff,v_counterpart,v_po,v_contractor)
      returning id into v_event;

      v_journal:=erp.post_journal('MATERIAL_COST_REVALUATION',v_event,v_date,
        'Automatic material moving-average recost: '||r.source_type,v_lines);
      update erp.material_cost_revaluation_events set journal_entry_id=v_journal,
      effective_date=(select transaction_date from erp.journal_entries where id=v_journal) where id=v_event;
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
 if object_count<>7295 or fingerprint is distinct from '75df405ae79f87a32bf89ddff7b2a266a698461013f8d83157aad2935813ec9f' then
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
   or (select count(*) from erp.cp6_v2620az_rollback_capsule)<>3 then raise exception 'AZ_CAPSULE_SECURITY_OR_COUNT';end if;
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
 if 3>0 and (boundary is null or exists(select 1 from erp.cp6_v2620az_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before'])) then raise exception 'AZ_CAPSULE_BOUNDARY';end if;
 if exists(select 1 from erp.cp6_v2620az_rollback_capsule where object_regidentity<>all(array['erp.sync_material_cost_revaluation(uuid)','erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)','erp.sync_finished_po_wip_residual(uuid,date,text)']::text[])
   or definition_sha256 is distinct from encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex')
   or installed_definition_sha256 is null or installed_definition_sha256=definition_sha256
   or installed_definition_sha256 is distinct from encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex'))
  then raise exception 'AZ_CAPSULE_SOURCE_DRIFT';end if;
end $capsule_guard$;
commit;
