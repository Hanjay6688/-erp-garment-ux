-- CP6 BB rollback: exact pre-use restore of the T3 release package to its predecessor; closed, drained maintenance required.
begin;
-- Built by scripts/cp6_t3_rollback.py from supabase/release/cp6-t3/20260925020000_erp_v2_6_20bb_cp6_open_cutover_states.sql (sha256 ed95f1e84a8a924a830de9362ff890769875d01671b4e83c77208daf23a8df34) and docs/evidence/cp6-t3/rollback_capture.json (sha256 f9eeb8d3e87ed217362abc9b82ef2ed81f67cae7927037aafe876d722977402d).
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
do $platform$ begin
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20bb')
  or (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20bb_cp6_open_cutover_states')<>1
  or not exists(select 1 from supabase_migrations.schema_migrations where version='20260925020000' and name='erp_v2_6_20bb_cp6_open_cutover_states'
   and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='ed95f1e84a8a924a830de9362ff890769875d01671b4e83c77208daf23a8df34')
  or exists(select 1 from supabase_migrations.schema_migrations where version>'20260925020000')
 then raise exception 'BB_ROLLBACK_PLATFORM_OR_SUCCESSOR';end if;
end $platform$;
do $prior_platform$
declare r record;
begin
 for r in select * from jsonb_to_recordset('[{"marker":"v2.6.20ac","stamp":"20260915031500","name":"erp_v2_6_20ac_cp6_temporal_surface_closure","sha":"871fb32b1d4a1e7f9aedfef684b0f2c766092732c38552620eb394061f6240d1"},{"marker":"v2.6.20ad","stamp":"20260915113627","name":"erp_v2_6_20ad_cp6_opening_material_business_day","sha":"58f8f1050e6c325339d7400a43b8c8f3d2375d2067f0c418d3eedfe85430a563"},{"marker":"v2.6.20ae","stamp":"20260915201500","name":"erp_v2_6_20ae_cp6_opening_roll_integrity","sha":"0c6bbf77a68142ddfdae99761a5cc2cd6e2e538be50b391f3303922c748c39d6"},{"marker":"v2.6.20af","stamp":"20260916014332","name":"erp_v2_6_20af_cp6_posted_child_integrity","sha":"3764349ab314c7990f6202d3f0de38b516aff53df2a3b1c4f272bc49667f6db4"},{"marker":"v2.6.20ag","stamp":"20260916050822","name":"erp_v2_6_20ag_cp6_sale_reservation_lineage","sha":"085b84cb6917617c5e6a2d375fd5177542ebe3f021a20de48e239159e34d66c0"},{"marker":"v2.6.20ah","stamp":"20260916070451","name":"erp_v2_6_20ah_cp6_return_allocation_eligibility","sha":"ade908ca9f55b2333c5eac5793b41aaabe0d57879dbb233e428fc882bab5738b"},{"marker":"v2.6.20ai","stamp":"20260916090022","name":"erp_v2_6_20ai_cp6_work_source_lineage","sha":"1ea5a602c5a5fcc9697355d9cca526709a06ee20e4eb4cdb765b2b7345c18d25"},{"marker":"v2.6.20aj","stamp":"20260916202400","name":"erp_v2_6_20aj_cp6_rework_output_lineage","sha":"b36a6359c57ad59d93ea5cb8dc5f7e90a0dd9cd59d48c331b037aa365d400986"},{"marker":"v2.6.20ak","stamp":"20260917033516","name":"erp_v2_6_20ak_cp6_import_reference_preview","sha":"9d06a91bd849c80e1ef99a6ac8996863527a30ef3b4079188be58bd8f3d4311d"},{"marker":"v2.6.20al","stamp":"20260917054049","name":"erp_v2_6_20al_cp6_opening_value_validation","sha":"2d16461cababd4a27827cfb8de01dd993a3a343460cdf049d427b44dd4cb6ea2"},{"marker":"v2.6.20am","stamp":"20260921214120","name":"erp_v2_6_20am_cp6_transfer_integrity","sha":"8fff82f72f9c76dd032778fa43aa37fd3fde98c4304de033d9c484db54f04a60"},{"marker":"v2.6.20an","stamp":"20260921223438","name":"erp_v2_6_20an_cp6_cutting_selectors","sha":"4df51d65fdb9a644fe2eeba92af23446e0c0389a1ebf9f336a0a396c144d7b71"},{"marker":"v2.6.20ao","stamp":"20260922135612","name":"erp_v2_6_20ao_cp6_invoice_retail","sha":"696a75c5969b756ce1973191a757a8c7deade06cb57e96dc5a16d648a4c48520"},{"marker":"v2.6.20ap","stamp":"20260922135615","name":"erp_v2_6_20ap_cp6_connected_import_materials","sha":"70503bb0247c811e066830ba752960a50b7afdfdb4c0c7697dee9a265ef1778a"},{"marker":"v2.6.20aq","stamp":"20260922161019","name":"erp_v2_6_20aq_cp6_accessory_lock_order","sha":"34cee78ee58f612187f7683280565ce2651e788e61efb62ced5e8c4dce7f9ada"},{"marker":"v2.6.20ar","stamp":"20260922185015","name":"erp_v2_6_20ar_cp6_opening_overlap","sha":"c5c973d47a4665723351205ccbcbe2c658c57bff7230f5552c5c2b7ca757371e"},{"marker":"v2.6.20as","stamp":"20260922210815","name":"erp_v2_6_20as_cp6_event_dates_product_identity","sha":"d13e46b3451386309a0a8dc1c89a4817ad8751568b9377f94c790832f8fa53a3"},{"marker":"v2.6.20at","stamp":"20260923005153","name":"erp_v2_6_20at_cp6_wip_temporal_identity","sha":"5e1ea5bfba73ada9aba5a8561efa9056b02154025d39bd10d47d3e4f2494110d"},{"marker":"v2.6.20au","stamp":"20260923045944","name":"erp_v2_6_20au_cp6_controlled_product_lifecycle","sha":"7d6265f081125499cb1813fe3f24c3b203363252727b5dcdfc7f74e311b85481"},{"marker":"v2.6.20av","stamp":"20260923110000","name":"erp_v2_6_20av_cp6_identity_new_stock_cutoff","sha":"c63a1fe3bf76dfc396921e07f57eb043e3bb864425b3289a9546bf66e08169a5"},{"marker":"v2.6.20aw","stamp":"20260924010000","name":"erp_v2_6_20aw_cp6_close_readiness_engine","sha":"c38edc9da084f4a90ee615bde16e6fea72e1072f79d6820d9d3bef27cc2a8ecb"},{"marker":"v2.6.20ax","stamp":"20260924010100","name":"erp_v2_6_20ax_cp6_fg_unsourced_receipts","sha":"c736049386c65f75c82fa790b502cd32c999512738207b7be17d711185c3d9f2"},{"marker":"v2.6.20ay","stamp":"20260924010200","name":"erp_v2_6_20ay_cp6_hpp_dated_from_goods","sha":"fd5ec47a16af264cc9b6a3aeed3d6e19023dc9f49beb51ceb8bfb4ecb14dc411"},{"marker":"v2.6.20az","stamp":"20260924010300","name":"erp_v2_6_20az_cp6_material_recost_dated_from_movement","sha":"e515d12a995a1806537ac08b7b0da15eb817480ead3103b035fc651b62977b8d"},{"marker":"v2.6.20ba","stamp":"20260925010000","name":"erp_v2_6_20ba_cp6_audit_closure","sha":"01bc0965cb945c25b98465a54ebc7fafabcc1d760c0698df1636de8069066960"}]'::jsonb) as x(marker text,stamp text,name text,sha text) loop
  if not exists(select 1 from erp.schema_migrations where version=r.marker)
   or (select count(*) from supabase_migrations.schema_migrations where name=r.name)<>1
   or not exists(select 1 from supabase_migrations.schema_migrations where version=r.stamp and name=r.name
    and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')=r.sha) then
   raise exception 'BB_PRIOR_PLATFORM_DRIFT: %',r.name;
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
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule','cp6_v2620ay_rollback_capsule','cp6_v2620az_rollback_capsule','cp6_v2620ba_rollback_capsule','cp6_v2620bb_rollback_capsule')
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
 if object_count<>7848 or fingerprint is distinct from '760f029cbbcaeb2fe81f03795e1544376b94c7b29e5088c9a28bb99bd4fa0dd4' then
  raise exception 'BB_ROLLBACK_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
do $historical_capsules$
declare r record;actual text;
begin
 for r in select * from jsonb_each_text('{"bs_resolution_v2619_rollback_capsule":"28ab388833da7da87384766ecaedadc66b4d048c303ee91e16f3939e34afdc39","bs_resolution_v2619a_rollback_capsule":"de8dfaab7b63b8742d383a089cdb05e73b629aad9f4df149e6a3c9fb590ef560","bs_resolution_v2619b_rollback_capsule":"d6d4f7457743d51679b5d25bf166ed69ca4b4f098cf5902ff985937531c2505d","bs_resolution_v2619c_rollback_capsule":"0207ba4f2ffba8ed61584709bbd884f1d2ee1a5981194fd7189a45afe8b3cbe1","cp3_r4_rollback_capsule":"7c01add62e66a4e2774a7199c2e77a04cca5e5942dbbba54d22cef720f82bc1d","cp45_v2617_rollback_capsule":"b9a43ce463de9905e94dd6538fd2a4952b0586a78c145f6f9d88aab7d6da3d80","cp45_v2617a_rollback_capsule":"b065dbcfdf1b59cb799e9f58caf6dd5ca7686e9f70826fce6a1ba8f140610022","cp4_v2616_rollback_capsule":"dde0a005dbe7cc93709bdfc6b961f4b9a76bf4db06fd7177d21dc79048af4d2f","cp6_v2620_rollback_capsule":"b42b94c2380f0768259a3d8f7fb645c76ebd6f92e8bae6a37d802352f7effd4f","cp6_v2620a_rollback_capsule":"67befaaf327d2591e1ca1d654132ee483eba39b6cbb4f891c4719d817155d448","cp6_v2620aa_rollback_capsule":"eb0d6fb4fcac2ac06929d577101e604428e9a04821813c342e5b831147dc8948","cp6_v2620ab_rollback_capsule":"3be9a9166e3a607962be819fbe23d38fe455290a7a970dc2aad068079bf30785","cp6_v2620ac_relation_rollback_capsule":"63c595c956e25135e1e032613831f5a08a734ba1f5c4746c46483c84517ad5ea","cp6_v2620ac_rollback_capsule":"51a8b08c9d96e66f03c2c8ba94ed3ed8fb15b26d1a2e4c65c58c614442dfa969","cp6_v2620ad_rollback_capsule":"5c3588109395b32ed743e0f4f5d789a3c59e3fffbab7469138f1f423c877ea9d","cp6_v2620ae_rollback_capsule":"6a75e02bf7b90c542fd9f2ac9534a2de066b047f5ffea65bffb1f83fa63c17f0","cp6_v2620af_rollback_capsule":"bfa89fc0e94d34b29405acedf551935f024942835f31cdc98f0f0983a9550288","cp6_v2620ag_rollback_capsule":"7ddfe6181f0c1c7439faf8a8150c542e958b3bafd8d18b5b2d1eb454fd7a85b7","cp6_v2620ah_rollback_capsule":"361be9321e5f4dadc7c7ec0e99ed746a98e7a4150178fc8355d23707c1507a93","cp6_v2620ai_rollback_capsule":"f2428dd712aa763b1379a4ae5b1a1e1e6ee175b355d8769b854a28f1355181c8","cp6_v2620aj_rollback_capsule":"8e24026dc90a2a92292c2cc6c8faa5fc3de991a19f326db494e0af2a518436f1","cp6_v2620ak_rollback_capsule":"dc7bfce7b9ee6a42e33cdf03cabd99d64435a4615245b2037fd6e4ee399aef10","cp6_v2620al_rollback_capsule":"c9e9aca042674efa5c6fa283e4b9ee47f3353ee9ee95b34e14ef1fd6b09bfde9","cp6_v2620am_rollback_capsule":"e781e631d06c6894c20b1fe6f9c65779f461d19c405c8ae74f28ed7d83ae6a26","cp6_v2620an_rollback_capsule":"ebfa8a281a32fe54babbdc209264ab422fde27f344d48561b90d2af022fe75b3","cp6_v2620ao_rollback_capsule":"b48103dcffcfb4c0c5172d2f11a8af809149c3c82584d0c24e6c740311e18cab","cp6_v2620ap_rollback_capsule":"10123ac8749107ffe9e25e74c9e3bc3080c0e15fc3d844bfcedf06043281e3f7","cp6_v2620aq_rollback_capsule":"35dd70bc3f6eacd8640eea6e22b11d4daaaac96bd7092cc8addefe47d0e3d4b8","cp6_v2620ar_rollback_capsule":"4a445445dc1641310fd3baa2b653bc2ff65b95e2a1f1ae53df2e0bb367fba6a8","cp6_v2620as_rollback_capsule":"8ffec1b6c558d3525b2c22754c2467e92463a201c4decdea0523e68b1a950aa9","cp6_v2620at_rollback_capsule":"8a7aca28f5e2e023d4828bae009962c34c6373740ccb26e30d69b6b661486fa2","cp6_v2620au_rollback_capsule":"f8a90e3df4dcaaf19bf33f1e3348e802e9c6357df673bd9bd524b0b2c1fb5fea","cp6_v2620av_rollback_capsule":"555750c028d4e47105289ffbb7d03bbbc08fa1b7adecf45b06a29bf3abb27b8f","cp6_v2620aw_rollback_capsule":"fe0df122c718e3b373f9527a1fe0bdd4bdb473e2e59d6a710057524fe8142475","cp6_v2620ax_rollback_capsule":"bde6ca64f2ef2df40caf5fe51234a549bff8f5f67ff5276d7344f274e0192465","cp6_v2620ay_rollback_capsule":"4f4e686c95ddf0f9481c2c12c6308ec72d46a1d75f5e7a3a761808ee6ae1361c","cp6_v2620az_rollback_capsule":"1ca0d25f289d7322d649e239ec395e73903795f2c84fe652faf4dcf1d2a90853","cp6_v2620b_rollback_capsule":"f9bf784bff0c54e647f491e257a9649fd0c3e6f10c39ddfc0944c961b9dd7601","cp6_v2620ba_rollback_capsule":"c290dd07139c6e9f31945dacc5fdf680371f83315018efe8fb7f7edee31943db","cp6_v2620c_rollback_capsule":"f88b1f5890ee8e7041758971bf9c9a3ce2bd0a7be6989fb95332c2dd7fa139aa","cp6_v2620d_rollback_capsule":"fa300c5554da4bb6812c61d726fd64f66329c97b085fa7d6ad5d0d8e5ae31235","cp6_v2620e_rollback_capsule":"143cd291cf4c12e78ab61e74e02ed03b08a48832a5064671868ff2bd2e3e1da7","cp6_v2620f_rollback_capsule":"076133b098e821fc2713af559618adf8aa3e204908f810af440fda355fc7a57f","cp6_v2620g_rollback_capsule":"ed9f4cacb47bd026ad6bdea373d1aa87044ed12aa60323cea453e3187dc488c4","cp6_v2620h_rollback_capsule":"4c25a060a2df3c22cd6fa9ff0b297163e223118a0d930b97bf1282b4756d909d","cp6_v2620i_rollback_capsule":"051203d95c44968abd8594f5bd48e289c4ac9a6c9fa49a89eee1086ad6b2c166","cp6_v2620j_rollback_capsule":"1393a8085d0f58717b13048c9cc3f7e9969ac86c351d6dfefdd2d4f43a735bd2","cp6_v2620k_rollback_capsule":"55aa71061f616ea11b361f0fabee2fd892f6438cc3f567cb9c135552ade42409","cp6_v2620l_rollback_capsule":"b4278768fce4ef307795953c14f607278c43bf474d76d3362e477280be08eb39","cp6_v2620m_rollback_capsule":"4b5f89d7bc4557f92b47716fe15640ab244c424fc1279433eb806d9d91d234e9","cp6_v2620n_rollback_capsule":"46e5ea4524613bb7a386551ada9e06888ea35eb987f9f5b864457fdd18bc3bc1","cp6_v2620o_rollback_capsule":"044e6b1a050df7e2a1d36082b0451877bda01116c08f611dfceb7a666bdf03c8","cp6_v2620p_rollback_capsule":"b656abaf23276984567c6c8d87b311427463c008b5ecd762fbdd0c2df13795df","cp6_v2620q_rollback_capsule":"ab6c992fbaa87f19a4eba696a57a3972f98504a354d9b5fc3be660939f8ea20f","cp6_v2620r_rollback_capsule":"8eb5e0a38284c5f8e3fee56618893ba72feaae9d26605c9ca3874dae25045297","cp6_v2620s_rollback_capsule":"fb57810a75f8829a038ed61b3a1cabde33dccf1e384661bc6723c51e28b3e132","cp6_v2620t_rollback_capsule":"348db4650d788750da243500b49e23c1130fdb70bc4a6d1fdf136bf68aa21f30","cp6_v2620u_rollback_capsule":"720eb1984548a3c381387fbe4d34e3c6f00334c8a4549eab7e398b827dcb7dd4","cp6_v2620v_rollback_capsule":"573ef5842eefadf1c32469514f4c8498667c99aec20ef20651406e4f419f5f60","cp6_v2620w_rollback_capsule":"f4e2ca1d577dd9f2724cc90693e8ee8bff36365c696575b69c6463f3e8ca0324","cp6_v2620x_rollback_capsule":"064db1068b56daa69e409ae582cd8a99490cea75d269154baa4217f90d3ca0d1","cp6_v2620y_rollback_capsule":"e3b23429a7f002c85ca8de1f8c632df13a4a2fc4e4654c12e2431c212772841d","cp6_v2620z_rollback_capsule":"ad0436a1480af43070e9861cb7e28d4cf55c435edbffb5fe368ca7babb7863ef","cutting_bridge_v2618_rollback_capsule":"535d1abd25668bc5bee79d82a602afe5efe4e8ce313bf1fb5170ae2004e3cb2d","cutting_bridge_v2618a_rollback_capsule":"db0608e690b3d936fa20b62cc4cfb9b1f9e86718212526eb6131562578b8bf60"}'::jsonb) loop
  execute format($caps$select encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to((to_jsonb(t)-array['captured_at','boundary_snapshot'])::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$caps$,r.key) into actual;
  if actual is distinct from r.value then raise exception 'BB_HISTORICAL_CAPSULE_DRIFT: %',r.key;end if;
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
 for r in select unnest(array['erp.cp6_v2620ao_rollback_capsule','erp.cp6_v2620ap_rollback_capsule','erp.cp6_v2620aq_rollback_capsule','erp.cp6_v2620ar_rollback_capsule','erp.cp6_v2620as_rollback_capsule','erp.cp6_v2620at_rollback_capsule','erp.cp6_v2620au_rollback_capsule','erp.cp6_v2620av_rollback_capsule','erp.cp6_v2620aw_rollback_capsule','erp.cp6_v2620ax_rollback_capsule','erp.cp6_v2620ay_rollback_capsule','erp.cp6_v2620az_rollback_capsule','erp.cp6_v2620ba_rollback_capsule']::regclass[]) as rel loop
  if not exists(select 1 from pg_class where oid=r.rel and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid=r.rel and a.grantee<>p.relowner)
   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid=r.rel and a.grantee<>'postgres'::regrole)
   or exists(select 1 from pg_policy where polrelid=r.rel)
   or exists(select 1 from pg_trigger where tgrelid=r.rel and not tgisinternal) then raise exception 'BB_PRIOR_CAPSULE_SECURITY: %',r.rel;end if;
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel)) into actual;
  if actual is distinct from expected then raise exception 'BB_PRIOR_CAPSULE_SHAPE_DRIFT: %',r.rel;end if;
  execute format($b$select count(*) filter(where boundary_snapshot is null or not(boundary_snapshot ?& array['before','after','platform_before','markers_before']))
   +(case when count(distinct boundary_snapshot)=1 then 0 else 1 end) from %s$b$,r.rel) into bad;
  if bad<>0 then raise exception 'BB_PRIOR_CAPSULE_BOUNDARY: %',r.rel;end if;
 end loop;
end $prior_capsules$;
do $capsule_guard$
declare expected jsonb;actual jsonb;boundary jsonb;
begin
 if not exists(select 1 from pg_class where oid='erp.cp6_v2620bb_rollback_capsule'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='erp.cp6_v2620bb_rollback_capsule'::regclass and a.grantee<>p.relowner)
   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='erp.cp6_v2620bb_rollback_capsule'::regclass and a.grantee<>'postgres'::regrole)
   or exists(select 1 from pg_policy where polrelid='erp.cp6_v2620bb_rollback_capsule'::regclass)
   or exists(select 1 from pg_trigger where tgrelid='erp.cp6_v2620bb_rollback_capsule'::regclass and not tgisinternal)
   or (select count(*) from erp.cp6_v2620bb_rollback_capsule)<>30 then raise exception 'BB_CAPSULE_SECURITY_OR_COUNT';end if;
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620an_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620an_rollback_capsule'::regclass)) into expected;
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620bb_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620bb_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620bb_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620bb_rollback_capsule'::regclass)) into actual;
 if actual is distinct from expected then raise exception 'BB_CAPSULE_SHAPE_DRIFT';end if;
 select boundary_snapshot into boundary from erp.cp6_v2620bb_rollback_capsule limit 1;
 if 30>0 and (boundary is null or exists(select 1 from erp.cp6_v2620bb_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before'])) then raise exception 'BB_CAPSULE_BOUNDARY';end if;
 if exists(select 1 from erp.cp6_v2620bb_rollback_capsule where object_regidentity<>all(array['erp.post_opening_subledger_settlement(uuid)','erp.post_opening_financial_correction(uuid,numeric,text,date)','erp.reverse_opening_financial_correction(uuid,text)','erp.approve_payroll(uuid)','erp.post_payroll_payment(uuid)','erp.reverse_paid_payroll(uuid,text)','erp.initial_import_revision_v1(uuid)','erp.get_initial_import_workspace_v1(uuid)','erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)','erp._validate_migration_batch_base(uuid)','erp.finalize_migration_batch(uuid)','erp.save_initial_import_action_v1(text,jsonb,uuid)','erp.run_v267_financial_truth_checks()','erp.assert_new_stock_cutoff_coverage_v1()','erp.material_purchase_posted_invoice_qty(uuid)','erp.material_purchase_current_unit_cost(uuid)','erp.refresh_material_purchase_item_match_state(uuid)','erp.sync_material_purchase_grni_on_status()','erp.check_initial_import_receipt_v1(uuid,uuid)','erp.apply_initial_import_receipts_v1(uuid)','erp.complete_initial_import_wip_v1(jsonb)','erp.validate_initial_import_production_v1(uuid)','erp.initial_import_lot_cost_v1(uuid)','erp.initial_import_production_rows_v1(uuid)','erp.sync_initial_import_bs_disposition_v1()','erp.guard_initial_import_po_completion_v1()','erp.recost_initial_import_origins_v1(uuid)','erp.run_v268_financial_report_checks()','erp.guard_work_completion_posting_consistency()','erp.post_work_completion(uuid)']::text[])
   or definition_sha256 is distinct from encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex')
   or installed_definition_sha256 is null or installed_definition_sha256=definition_sha256
   or installed_definition_sha256 is distinct from encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex'))
  then raise exception 'BB_CAPSULE_SOURCE_DRIFT';end if;
end $capsule_guard$;
create temporary table cp6_t3_rollback_boundary on commit drop as select boundary_snapshot from erp.cp6_v2620bb_rollback_capsule limit 1;
do $pre_use$ declare v_table text;v_hash jsonb;v_after jsonb;b jsonb; begin
 select boundary_snapshot into b from pg_temp.cp6_t3_rollback_boundary;
 v_after:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620bb_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_after:=v_after||jsonb_build_object(v_table,v_hash);
 end loop;
 if b is null or v_after is distinct from b->'after' then raise exception 'BB_POST_USE_ROLLBACK_REFUSED';end if;
 if (select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations t where version<>'20260925020000') is distinct from b->>'platform_before'
  or (select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from erp.schema_migrations t where version<>'v2.6.20bb') is distinct from b->>'markers_before'
 then raise exception 'BB_PRIOR_HISTORY_DRIFT';end if;
end $pre_use$;
do $restore_function$ declare r record; begin
 for r in select object_definition from erp.cp6_v2620bb_rollback_capsule order by object_regidentity loop execute r.object_definition;end loop;
 if exists(select 1 from erp.cp6_v2620bb_rollback_capsule x join pg_proc p on p.oid=to_regprocedure(x.object_regidentity)
  where encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') is distinct from x.definition_sha256
   or array(select a::text from unnest(p.proacl)a order by a::text) is distinct from x.acl_snapshot
   or pg_get_userbyid(p.proowner) is distinct from x.owner_snapshot)
  or (select count(*) from erp.cp6_v2620bb_rollback_capsule x where to_regprocedure(x.object_regidentity) is not null)<>30
 then raise exception 'BB_FUNCTION_RESTORE_MISMATCH';end if;
end $restore_function$;
drop trigger trg_bb_financial_source_legacy_identity on erp.initial_import_financial_sources;
drop trigger trg_bb_commitment_draft on erp.material_purchase_headers;
drop trigger trg_bb_opening_balance_reserved on erp.opening_subledger_balances;
drop trigger trg_bb_opening_carry_reimbursement on erp.payroll_reimbursements;
drop trigger trg_bb_opening_payable_reimbursement on erp.payroll_reimbursements;
drop trigger trg_bb_open_sales_draft on erp.sales_headers;
alter table erp.payroll_reimbursements drop constraint payroll_reimbursements_opening_carry_check;
alter table erp.payroll_reimbursements drop constraint payroll_reimbursements_opening_carry_entitlement_id_fkey;
alter table erp.payroll_reimbursements drop constraint payroll_reimbursements_opening_payable_balance_id_fkey;
alter table erp.payroll_reimbursements drop constraint payroll_reimbursements_opening_payable_check;
alter table erp.work_completion_events drop constraint work_completion_events_bb_opening_item_id_fkey;
alter table erp.work_completion_events drop constraint work_completion_events_bb_source_check;
drop index erp.payroll_reimbursements_opening_carry_unique;
drop index erp.payroll_reimbursements_opening_payable_unique;
drop index erp.work_completion_events_bb_opening_item;
alter table erp.payroll_reimbursements drop column opening_carry_entitlement_id;
alter table erp.payroll_reimbursements drop column opening_carry_qty;
alter table erp.payroll_reimbursements drop column opening_payable_balance_id;
alter table erp.work_completion_events drop column bb_opening_item_id;
alter table erp.initial_import_production_sources drop constraint initial_import_production_sources_stage_check;
alter table erp.initial_import_production_sources add constraint initial_import_production_sources_stage_check CHECK ((stage = ANY (ARRAY['SEWING'::text, 'LAUNDRY'::text, 'QC'::text])));
alter table erp.payroll_reimbursements drop constraint payroll_reimbursements_source_type_check;
alter table erp.payroll_reimbursements add constraint payroll_reimbursements_source_type_check CHECK (((source_type)::text = ANY (ARRAY[('MANUAL'::character varying)::text, ('ACCESSORY_BOM'::character varying)::text])));
drop trigger trg_bb_legacy_document_identity on erp.bb_legacy_documents_v1;
drop trigger bb_opening_reworks_v1_immutable on erp.bb_opening_reworks_v1;
drop trigger trg_bb_receipt_invoiced_part_immutable on erp.bb_receipt_invoiced_parts_v1;
drop trigger bb_wip_bs_splits_v1_immutable on erp.bb_wip_bs_splits_v1;
drop trigger bb_wip_pickups_v1_immutable on erp.bb_wip_pickups_v1;
drop trigger bb_wip_split_value_events_v1_immutable on erp.bb_wip_split_value_events_v1;
drop function erp.bb_apply_financial_imports_v1(uuid);
drop function erp.bb_apply_labour_imports_v1(uuid);
drop function erp.bb_apply_production_imports_v1(uuid);
drop function erp.bb_apply_purchase_imports_v1(uuid);
drop function erp.bb_apply_sales_imports_v1(uuid);
drop function erp.bb_assert_opening_balance_floor_v1(uuid,date);
drop function erp.bb_assert_wip_ready_v1(uuid,date);
drop function erp.bb_business_today_v1();
drop function erp.bb_check_credit_account_v1(uuid,jsonb);
drop function erp.bb_check_cutting_wip_row_v1(uuid,jsonb);
drop function erp.bb_check_import_row_v1(uuid,uuid);
drop function erp.bb_check_labour_import_row_v1(uuid,uuid);
drop function erp.bb_check_opening_payable_payroll_v1(uuid);
drop function erp.bb_check_opening_work_v1(uuid);
drop function erp.bb_check_purchase_import_row_v1(uuid,uuid);
drop function erp.bb_check_rework_import_row_v1(uuid,uuid);
drop function erp.bb_check_sales_import_row_v1(uuid,uuid);
drop function erp.bb_commitment_line_remaining_v1(uuid,uuid);
drop function erp.bb_customer_credit_dated_floor_v1(uuid,date);
drop function erp.bb_customer_credit_state_v1(uuid);
drop function erp.bb_entitlement_carry_used_v1(uuid,uuid);
drop function erp.bb_financial_revision_part_v1(uuid);
drop function erp.bb_financial_workspace_v1(uuid);
drop function erp.bb_guard_append_only_v1();
drop function erp.bb_guard_commitment_draft_v1();
drop function erp.bb_guard_legacy_document_identity_v1();
drop function erp.bb_guard_open_sales_draft_v1();
drop function erp.bb_guard_opening_balance_reserved_v1();
drop function erp.bb_guard_opening_carry_reimbursement_v1();
drop function erp.bb_guard_opening_payable_reimbursement_v1();
drop function erp.bb_guard_receipt_invoiced_part_v1();
drop function erp.bb_guard_wip_history_v1();
drop function erp.bb_labour_revision_part_v1(uuid);
drop function erp.bb_labour_row_amount_v1(uuid,uuid);
drop function erp.bb_labour_workspace_v1(uuid);
drop function erp.bb_manage_customer_credit_v1(jsonb,uuid);
drop function erp.bb_manage_opening_sale_return_v1(jsonb,uuid);
drop function erp.bb_manage_opening_settlement_v1(jsonb,uuid);
drop function erp.bb_manage_opening_wip_v1(jsonb,uuid);
drop function erp.bb_manage_payroll_entitlement_v1(jsonb,uuid);
drop function erp.bb_manage_purchase_commitment_v1(jsonb,uuid);
drop function erp.bb_open_commitment_draft_v1(uuid,timestamp with time zone,text);
drop function erp.bb_opening_balance_context_v1(uuid);
drop function erp.bb_opening_balance_dated_floor_v1(uuid,date);
drop function erp.bb_opening_balance_reserved_v1(uuid,uuid);
drop function erp.bb_opening_credit_account_v1(uuid);
drop function erp.bb_opening_credit_lines_v1(uuid);
drop function erp.bb_opening_work_source_v1(uuid,uuid);
drop function erp.bb_parse_amount_v1(text,text,boolean);
drop function erp.bb_parse_count_v1(text,text,integer);
drop function erp.bb_parse_date_v1(text,text);
drop function erp.bb_party_of_v1(uuid,text,text);
drop function erp.bb_physical_at_v1(date);
drop function erp.bb_po_contractor_used_v1(uuid);
drop function erp.bb_po_open_split_bs_v1(uuid);
drop function erp.bb_production_revision_part_v1(uuid);
drop function erp.bb_production_workspace_v1(uuid);
drop function erp.bb_purchase_revision_part_v1(uuid);
drop function erp.bb_purchase_workspace_v1(uuid);
drop function erp.bb_receipt_invoiced_qty_v1(uuid);
drop function erp.bb_receipt_opening_unit_cost_v1(uuid);
drop function erp.bb_receipt_row_invoiced_part_v1(uuid,uuid);
drop function erp.bb_sales_workspace_v1(uuid);
drop function erp.bb_set_opening_payable_payroll_v1(uuid,uuid,numeric,bigint);
drop function erp.bb_split_opening_wip_bs_v1(uuid,uuid,integer,timestamp with time zone,text,text);
drop function erp.bb_sync_item_split_values_v1(uuid,date);
drop function erp.bb_sync_split_bs_disposition_v1(uuid,date,boolean);
drop function erp.bb_sync_split_bs_value_v1(uuid,date);
drop function erp.bb_validate_financial_imports_v1(uuid);
drop function erp.bb_validate_labour_imports_v1(uuid);
drop function erp.bb_validate_production_imports_v1(uuid);
drop function erp.bb_validate_purchase_imports_v1(uuid);
drop function erp.bb_validate_sales_imports_v1(uuid);
drop function erp.bb_wip_active_pickup_v1(uuid);
drop function erp.bb_wip_holder_v1(uuid);
drop function erp.bb_wip_min_output_at_v1(uuid,date);
drop function erp.bb_wip_row_part_v1(uuid);
drop function erp.bb_wip_split_active_qty_v1(uuid);
drop function erp.bb_wip_split_days_v1(uuid);
drop function erp.bb_wip_split_net_asof_v1(uuid,date);
drop function erp.bb_wip_stage_v1(uuid);
alter table erp.bb_customer_credits_v1 drop constraint bb_customer_credits_v1_return_receipt_fkey;
drop table erp.bb_open_sales_draft_lines_v1;
drop table erp.bb_open_sales_drafts_v1;
drop table erp.bb_opening_reworks_v1;
drop table erp.bb_wip_split_value_events_v1;
drop table erp.bb_wip_bs_splits_v1;
drop table erp.bb_wip_pickups_v1;
drop table erp.bb_payroll_entitlements_v1;
drop table erp.bb_purchase_commitment_cancellations_v1;
drop table erp.bb_purchase_commitment_drafts_v1;
drop table erp.bb_purchase_commitment_lines_v1;
drop table erp.bb_purchase_commitments_v1;
drop table erp.bb_receipt_invoiced_parts_v1;
drop table erp.bb_opening_credits_v1;
drop table erp.bb_opening_sale_return_receipts_v1;
drop table erp.bb_opening_sale_return_rights_v1;
drop table erp.bb_customer_credit_events_v1;
drop table erp.bb_customer_credits_v1;
drop table erp.bb_legacy_documents_v1;
drop table erp.cp6_v2620bb_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20bb';
delete from supabase_migrations.schema_migrations where version='20260925020000' and name='erp_v2_6_20bb_cp6_open_cutover_states';
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule','cp6_v2620ay_rollback_capsule','cp6_v2620az_rollback_capsule','cp6_v2620ba_rollback_capsule','cp6_v2620bb_rollback_capsule')
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
 if object_count<>7314 or fingerprint is distinct from '68e3b1dac2c8e577ffae9fc0ef0b8ac18e66c7357a7b9e82aa503c8041d0560d' then
  raise exception 'BB_RESTORED_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
do $restored_data$ declare v_table text;v_hash jsonb;v_before jsonb;b jsonb; begin
 select boundary_snapshot into b from pg_temp.cp6_t3_rollback_boundary;
 v_before:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_before:=v_before||jsonb_build_object(v_table,v_hash);
 end loop;
 if v_before is distinct from b->'before'
  or (select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations t) is distinct from b->>'platform_before'
  or (select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from erp.schema_migrations t) is distinct from b->>'markers_before'
 then raise exception 'BB_EXACT_RESTORE_FAILED';end if;
end $restored_data$;
commit;
