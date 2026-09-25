-- CP6 BA: independent audit closure (import identity, dated WIP and advance capacity, WIP product binding, recost cents, selectors, single close filing). Release candidate of the T3 combined package; closed, drained maintenance required.
begin;
-- Built by scripts/cp6_t3_awx_release.py from supabase/dev/cp6_ba_t1_family.sql (sha256 06d6dccb5243832e07deead99d19a5b359f2cd65b1dc8917b2fa006e780c1f37): the T1 body below is unchanged apart from the
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
 if exists(select 1 from erp.schema_migrations where version='v2.6.20ba') or to_regclass('erp.cp6_v2620ba_rollback_capsule') is not null
  or to_regclass('erp.initial_import_wip_output_identity_v1') is not null
 then raise exception 'BA_EXACT_PREDECESSOR_WITHOUT_SUCCESSOR_REQUIRED';end if;
end $admission$;
do $predecessor$
begin
 if exists(select 1 from supabase_migrations.schema_migrations where version>'20260924010300') then raise exception 'BA_EXACT_PREDECESSOR_REQUIRED';end if;
end $predecessor$;
do $prior_platform$
declare r record;
begin
 for r in select * from jsonb_to_recordset('[{"marker":"v2.6.20ac","stamp":"20260915031500","name":"erp_v2_6_20ac_cp6_temporal_surface_closure","sha":"871fb32b1d4a1e7f9aedfef684b0f2c766092732c38552620eb394061f6240d1"},{"marker":"v2.6.20ad","stamp":"20260915113627","name":"erp_v2_6_20ad_cp6_opening_material_business_day","sha":"58f8f1050e6c325339d7400a43b8c8f3d2375d2067f0c418d3eedfe85430a563"},{"marker":"v2.6.20ae","stamp":"20260915201500","name":"erp_v2_6_20ae_cp6_opening_roll_integrity","sha":"0c6bbf77a68142ddfdae99761a5cc2cd6e2e538be50b391f3303922c748c39d6"},{"marker":"v2.6.20af","stamp":"20260916014332","name":"erp_v2_6_20af_cp6_posted_child_integrity","sha":"3764349ab314c7990f6202d3f0de38b516aff53df2a3b1c4f272bc49667f6db4"},{"marker":"v2.6.20ag","stamp":"20260916050822","name":"erp_v2_6_20ag_cp6_sale_reservation_lineage","sha":"085b84cb6917617c5e6a2d375fd5177542ebe3f021a20de48e239159e34d66c0"},{"marker":"v2.6.20ah","stamp":"20260916070451","name":"erp_v2_6_20ah_cp6_return_allocation_eligibility","sha":"ade908ca9f55b2333c5eac5793b41aaabe0d57879dbb233e428fc882bab5738b"},{"marker":"v2.6.20ai","stamp":"20260916090022","name":"erp_v2_6_20ai_cp6_work_source_lineage","sha":"1ea5a602c5a5fcc9697355d9cca526709a06ee20e4eb4cdb765b2b7345c18d25"},{"marker":"v2.6.20aj","stamp":"20260916202400","name":"erp_v2_6_20aj_cp6_rework_output_lineage","sha":"b36a6359c57ad59d93ea5cb8dc5f7e90a0dd9cd59d48c331b037aa365d400986"},{"marker":"v2.6.20ak","stamp":"20260917033516","name":"erp_v2_6_20ak_cp6_import_reference_preview","sha":"9d06a91bd849c80e1ef99a6ac8996863527a30ef3b4079188be58bd8f3d4311d"},{"marker":"v2.6.20al","stamp":"20260917054049","name":"erp_v2_6_20al_cp6_opening_value_validation","sha":"2d16461cababd4a27827cfb8de01dd993a3a343460cdf049d427b44dd4cb6ea2"},{"marker":"v2.6.20am","stamp":"20260921214120","name":"erp_v2_6_20am_cp6_transfer_integrity","sha":"8fff82f72f9c76dd032778fa43aa37fd3fde98c4304de033d9c484db54f04a60"},{"marker":"v2.6.20an","stamp":"20260921223438","name":"erp_v2_6_20an_cp6_cutting_selectors","sha":"4df51d65fdb9a644fe2eeba92af23446e0c0389a1ebf9f336a0a396c144d7b71"},{"marker":"v2.6.20ao","stamp":"20260922135612","name":"erp_v2_6_20ao_cp6_invoice_retail","sha":"696a75c5969b756ce1973191a757a8c7deade06cb57e96dc5a16d648a4c48520"},{"marker":"v2.6.20ap","stamp":"20260922135615","name":"erp_v2_6_20ap_cp6_connected_import_materials","sha":"70503bb0247c811e066830ba752960a50b7afdfdb4c0c7697dee9a265ef1778a"},{"marker":"v2.6.20aq","stamp":"20260922161019","name":"erp_v2_6_20aq_cp6_accessory_lock_order","sha":"34cee78ee58f612187f7683280565ce2651e788e61efb62ced5e8c4dce7f9ada"},{"marker":"v2.6.20ar","stamp":"20260922185015","name":"erp_v2_6_20ar_cp6_opening_overlap","sha":"c5c973d47a4665723351205ccbcbe2c658c57bff7230f5552c5c2b7ca757371e"},{"marker":"v2.6.20as","stamp":"20260922210815","name":"erp_v2_6_20as_cp6_event_dates_product_identity","sha":"d13e46b3451386309a0a8dc1c89a4817ad8751568b9377f94c790832f8fa53a3"},{"marker":"v2.6.20at","stamp":"20260923005153","name":"erp_v2_6_20at_cp6_wip_temporal_identity","sha":"5e1ea5bfba73ada9aba5a8561efa9056b02154025d39bd10d47d3e4f2494110d"},{"marker":"v2.6.20au","stamp":"20260923045944","name":"erp_v2_6_20au_cp6_controlled_product_lifecycle","sha":"7d6265f081125499cb1813fe3f24c3b203363252727b5dcdfc7f74e311b85481"},{"marker":"v2.6.20av","stamp":"20260923110000","name":"erp_v2_6_20av_cp6_identity_new_stock_cutoff","sha":"c63a1fe3bf76dfc396921e07f57eb043e3bb864425b3289a9546bf66e08169a5"},{"marker":"v2.6.20aw","stamp":"20260924010000","name":"erp_v2_6_20aw_cp6_close_readiness_engine","sha":"c38edc9da084f4a90ee615bde16e6fea72e1072f79d6820d9d3bef27cc2a8ecb"},{"marker":"v2.6.20ax","stamp":"20260924010100","name":"erp_v2_6_20ax_cp6_fg_unsourced_receipts","sha":"c736049386c65f75c82fa790b502cd32c999512738207b7be17d711185c3d9f2"},{"marker":"v2.6.20ay","stamp":"20260924010200","name":"erp_v2_6_20ay_cp6_hpp_dated_from_goods","sha":"fd5ec47a16af264cc9b6a3aeed3d6e19023dc9f49beb51ceb8bfb4ecb14dc411"},{"marker":"v2.6.20az","stamp":"20260924010300","name":"erp_v2_6_20az_cp6_material_recost_dated_from_movement","sha":"e515d12a995a1806537ac08b7b0da15eb817480ead3103b035fc651b62977b8d"}]'::jsonb) as x(marker text,stamp text,name text,sha text) loop
  if not exists(select 1 from erp.schema_migrations where version=r.marker)
   or (select count(*) from supabase_migrations.schema_migrations where name=r.name)<>1
   or not exists(select 1 from supabase_migrations.schema_migrations where version=r.stamp and name=r.name
    and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')=r.sha) then
   raise exception 'BA_PRIOR_PLATFORM_DRIFT: %',r.name;
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
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule','cp6_v2620ay_rollback_capsule','cp6_v2620az_rollback_capsule','cp6_v2620ba_rollback_capsule')
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
 if object_count<>7297 or fingerprint is distinct from 'd905acb582bbeb4a1d535ef494f75372ffbac0bb57305e723a862ed01f570000' then
  raise exception 'BA_PREDECESSOR_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
do $historical_capsules$
declare r record;actual text;
begin
 for r in select * from jsonb_each_text('{"bs_resolution_v2619_rollback_capsule":"28ab388833da7da87384766ecaedadc66b4d048c303ee91e16f3939e34afdc39","bs_resolution_v2619a_rollback_capsule":"de8dfaab7b63b8742d383a089cdb05e73b629aad9f4df149e6a3c9fb590ef560","bs_resolution_v2619b_rollback_capsule":"d6d4f7457743d51679b5d25bf166ed69ca4b4f098cf5902ff985937531c2505d","bs_resolution_v2619c_rollback_capsule":"0207ba4f2ffba8ed61584709bbd884f1d2ee1a5981194fd7189a45afe8b3cbe1","cp3_r4_rollback_capsule":"7c01add62e66a4e2774a7199c2e77a04cca5e5942dbbba54d22cef720f82bc1d","cp45_v2617_rollback_capsule":"b9a43ce463de9905e94dd6538fd2a4952b0586a78c145f6f9d88aab7d6da3d80","cp45_v2617a_rollback_capsule":"b065dbcfdf1b59cb799e9f58caf6dd5ca7686e9f70826fce6a1ba8f140610022","cp4_v2616_rollback_capsule":"dde0a005dbe7cc93709bdfc6b961f4b9a76bf4db06fd7177d21dc79048af4d2f","cp6_v2620_rollback_capsule":"b42b94c2380f0768259a3d8f7fb645c76ebd6f92e8bae6a37d802352f7effd4f","cp6_v2620a_rollback_capsule":"67befaaf327d2591e1ca1d654132ee483eba39b6cbb4f891c4719d817155d448","cp6_v2620aa_rollback_capsule":"eb0d6fb4fcac2ac06929d577101e604428e9a04821813c342e5b831147dc8948","cp6_v2620ab_rollback_capsule":"3be9a9166e3a607962be819fbe23d38fe455290a7a970dc2aad068079bf30785","cp6_v2620ac_relation_rollback_capsule":"63c595c956e25135e1e032613831f5a08a734ba1f5c4746c46483c84517ad5ea","cp6_v2620ac_rollback_capsule":"51a8b08c9d96e66f03c2c8ba94ed3ed8fb15b26d1a2e4c65c58c614442dfa969","cp6_v2620ad_rollback_capsule":"5c3588109395b32ed743e0f4f5d789a3c59e3fffbab7469138f1f423c877ea9d","cp6_v2620ae_rollback_capsule":"6a75e02bf7b90c542fd9f2ac9534a2de066b047f5ffea65bffb1f83fa63c17f0","cp6_v2620af_rollback_capsule":"bfa89fc0e94d34b29405acedf551935f024942835f31cdc98f0f0983a9550288","cp6_v2620ag_rollback_capsule":"7ddfe6181f0c1c7439faf8a8150c542e958b3bafd8d18b5b2d1eb454fd7a85b7","cp6_v2620ah_rollback_capsule":"361be9321e5f4dadc7c7ec0e99ed746a98e7a4150178fc8355d23707c1507a93","cp6_v2620ai_rollback_capsule":"f2428dd712aa763b1379a4ae5b1a1e1e6ee175b355d8769b854a28f1355181c8","cp6_v2620aj_rollback_capsule":"8e24026dc90a2a92292c2cc6c8faa5fc3de991a19f326db494e0af2a518436f1","cp6_v2620ak_rollback_capsule":"dc7bfce7b9ee6a42e33cdf03cabd99d64435a4615245b2037fd6e4ee399aef10","cp6_v2620al_rollback_capsule":"c9e9aca042674efa5c6fa283e4b9ee47f3353ee9ee95b34e14ef1fd6b09bfde9","cp6_v2620am_rollback_capsule":"e781e631d06c6894c20b1fe6f9c65779f461d19c405c8ae74f28ed7d83ae6a26","cp6_v2620an_rollback_capsule":"ebfa8a281a32fe54babbdc209264ab422fde27f344d48561b90d2af022fe75b3","cp6_v2620ao_rollback_capsule":"b48103dcffcfb4c0c5172d2f11a8af809149c3c82584d0c24e6c740311e18cab","cp6_v2620ap_rollback_capsule":"10123ac8749107ffe9e25e74c9e3bc3080c0e15fc3d844bfcedf06043281e3f7","cp6_v2620aq_rollback_capsule":"35dd70bc3f6eacd8640eea6e22b11d4daaaac96bd7092cc8addefe47d0e3d4b8","cp6_v2620ar_rollback_capsule":"4a445445dc1641310fd3baa2b653bc2ff65b95e2a1f1ae53df2e0bb367fba6a8","cp6_v2620as_rollback_capsule":"8ffec1b6c558d3525b2c22754c2467e92463a201c4decdea0523e68b1a950aa9","cp6_v2620at_rollback_capsule":"8a7aca28f5e2e023d4828bae009962c34c6373740ccb26e30d69b6b661486fa2","cp6_v2620au_rollback_capsule":"f8a90e3df4dcaaf19bf33f1e3348e802e9c6357df673bd9bd524b0b2c1fb5fea","cp6_v2620av_rollback_capsule":"555750c028d4e47105289ffbb7d03bbbc08fa1b7adecf45b06a29bf3abb27b8f","cp6_v2620aw_rollback_capsule":"fe0df122c718e3b373f9527a1fe0bdd4bdb473e2e59d6a710057524fe8142475","cp6_v2620ax_rollback_capsule":"bde6ca64f2ef2df40caf5fe51234a549bff8f5f67ff5276d7344f274e0192465","cp6_v2620ay_rollback_capsule":"4f4e686c95ddf0f9481c2c12c6308ec72d46a1d75f5e7a3a761808ee6ae1361c","cp6_v2620az_rollback_capsule":"1ca0d25f289d7322d649e239ec395e73903795f2c84fe652faf4dcf1d2a90853","cp6_v2620b_rollback_capsule":"f9bf784bff0c54e647f491e257a9649fd0c3e6f10c39ddfc0944c961b9dd7601","cp6_v2620c_rollback_capsule":"f88b1f5890ee8e7041758971bf9c9a3ce2bd0a7be6989fb95332c2dd7fa139aa","cp6_v2620d_rollback_capsule":"fa300c5554da4bb6812c61d726fd64f66329c97b085fa7d6ad5d0d8e5ae31235","cp6_v2620e_rollback_capsule":"143cd291cf4c12e78ab61e74e02ed03b08a48832a5064671868ff2bd2e3e1da7","cp6_v2620f_rollback_capsule":"076133b098e821fc2713af559618adf8aa3e204908f810af440fda355fc7a57f","cp6_v2620g_rollback_capsule":"ed9f4cacb47bd026ad6bdea373d1aa87044ed12aa60323cea453e3187dc488c4","cp6_v2620h_rollback_capsule":"4c25a060a2df3c22cd6fa9ff0b297163e223118a0d930b97bf1282b4756d909d","cp6_v2620i_rollback_capsule":"051203d95c44968abd8594f5bd48e289c4ac9a6c9fa49a89eee1086ad6b2c166","cp6_v2620j_rollback_capsule":"1393a8085d0f58717b13048c9cc3f7e9969ac86c351d6dfefdd2d4f43a735bd2","cp6_v2620k_rollback_capsule":"55aa71061f616ea11b361f0fabee2fd892f6438cc3f567cb9c135552ade42409","cp6_v2620l_rollback_capsule":"b4278768fce4ef307795953c14f607278c43bf474d76d3362e477280be08eb39","cp6_v2620m_rollback_capsule":"4b5f89d7bc4557f92b47716fe15640ab244c424fc1279433eb806d9d91d234e9","cp6_v2620n_rollback_capsule":"46e5ea4524613bb7a386551ada9e06888ea35eb987f9f5b864457fdd18bc3bc1","cp6_v2620o_rollback_capsule":"044e6b1a050df7e2a1d36082b0451877bda01116c08f611dfceb7a666bdf03c8","cp6_v2620p_rollback_capsule":"b656abaf23276984567c6c8d87b311427463c008b5ecd762fbdd0c2df13795df","cp6_v2620q_rollback_capsule":"ab6c992fbaa87f19a4eba696a57a3972f98504a354d9b5fc3be660939f8ea20f","cp6_v2620r_rollback_capsule":"8eb5e0a38284c5f8e3fee56618893ba72feaae9d26605c9ca3874dae25045297","cp6_v2620s_rollback_capsule":"fb57810a75f8829a038ed61b3a1cabde33dccf1e384661bc6723c51e28b3e132","cp6_v2620t_rollback_capsule":"348db4650d788750da243500b49e23c1130fdb70bc4a6d1fdf136bf68aa21f30","cp6_v2620u_rollback_capsule":"720eb1984548a3c381387fbe4d34e3c6f00334c8a4549eab7e398b827dcb7dd4","cp6_v2620v_rollback_capsule":"573ef5842eefadf1c32469514f4c8498667c99aec20ef20651406e4f419f5f60","cp6_v2620w_rollback_capsule":"f4e2ca1d577dd9f2724cc90693e8ee8bff36365c696575b69c6463f3e8ca0324","cp6_v2620x_rollback_capsule":"064db1068b56daa69e409ae582cd8a99490cea75d269154baa4217f90d3ca0d1","cp6_v2620y_rollback_capsule":"e3b23429a7f002c85ca8de1f8c632df13a4a2fc4e4654c12e2431c212772841d","cp6_v2620z_rollback_capsule":"ad0436a1480af43070e9861cb7e28d4cf55c435edbffb5fe368ca7babb7863ef","cutting_bridge_v2618_rollback_capsule":"535d1abd25668bc5bee79d82a602afe5efe4e8ce313bf1fb5170ae2004e3cb2d","cutting_bridge_v2618a_rollback_capsule":"db0608e690b3d936fa20b62cc4cfb9b1f9e86718212526eb6131562578b8bf60"}'::jsonb) loop
  execute format($caps$select encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to((to_jsonb(t)-array['captured_at','boundary_snapshot'])::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$caps$,r.key) into actual;
  if actual is distinct from r.value then raise exception 'BA_HISTORICAL_CAPSULE_DRIFT: %',r.key;end if;
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
 for r in select unnest(array['erp.cp6_v2620ao_rollback_capsule','erp.cp6_v2620ap_rollback_capsule','erp.cp6_v2620aq_rollback_capsule','erp.cp6_v2620ar_rollback_capsule','erp.cp6_v2620as_rollback_capsule','erp.cp6_v2620at_rollback_capsule','erp.cp6_v2620au_rollback_capsule','erp.cp6_v2620av_rollback_capsule','erp.cp6_v2620aw_rollback_capsule','erp.cp6_v2620ax_rollback_capsule','erp.cp6_v2620ay_rollback_capsule','erp.cp6_v2620az_rollback_capsule']::regclass[]) as rel loop
  if not exists(select 1 from pg_class where oid=r.rel and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid=r.rel and a.grantee<>p.relowner)
   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid=r.rel and a.grantee<>'postgres'::regrole)
   or exists(select 1 from pg_policy where polrelid=r.rel)
   or exists(select 1 from pg_trigger where tgrelid=r.rel and not tgisinternal) then raise exception 'BA_PRIOR_CAPSULE_SECURITY: %',r.rel;end if;
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel)) into actual;
  if actual is distinct from expected then raise exception 'BA_PRIOR_CAPSULE_SHAPE_DRIFT: %',r.rel;end if;
  execute format($b$select count(*) filter(where boundary_snapshot is null or not(boundary_snapshot ?& array['before','after','platform_before','markers_before']))
   +(case when count(distinct boundary_snapshot)=1 then 0 else 1 end) from %s$b$,r.rel) into bad;
  if bad<>0 then raise exception 'BA_PRIOR_CAPSULE_BOUNDARY: %',r.rel;end if;
 end loop;
end $prior_capsules$;
create table erp.cp6_v2620ba_rollback_capsule(like erp.cp6_v2620an_rollback_capsule including all);
alter table erp.cp6_v2620ba_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620ba_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620ba_rollback_capsule(object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),i.identity,pg_get_functiondef(p.oid),
 encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
 array(select a::text from unnest(p.proacl)a order by a::text),pg_get_userbyid(p.proowner)
from unnest(array['erp.post_opening_balance(uuid)','erp.complete_initial_import_wip_v1(jsonb)','erp.manage_initial_prepayment_v1(jsonb)','erp.sync_material_cost_revaluation(uuid)','erp.close_accounting_through(date,text)','erp.assert_new_stock_cutoff_coverage_v1()','erp.get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)','erp.get_initial_import_workspace_v1(uuid)']) i(identity)
join pg_proc p on p.oid=i.identity::regprocedure join pg_namespace n on n.oid=p.pronamespace;
create temp table cp6_release_functions on commit drop as
select p.oid::regprocedure::text as identity,encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') as definition_sha256,
  array(select a::text from unnest(p.proacl)a order by a::text) as acl,pg_get_userbyid(p.proowner) as owner
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p');
do $before_data$ declare v_table text;v_hash jsonb;v_before jsonb; begin
 v_before:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620ba_rollback_capsule']::text[]) order by 1 loop
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
 if (select count(*) from erp.schema_migrations where version in('v2.6.20av','v2.6.20aw','v2.6.20ax','v2.6.20ay','v2.6.20az'))<>5 then raise exception 'BA_T1_REQUIRES_AV_AW_AX_AY_AZ'; end if;
 if exists(select 1 from erp.schema_migrations where version='v2.6.20ba') or to_regclass('erp.initial_import_wip_output_identity_v1') is not null then raise exception 'BA_T1_ALREADY_INSTALLED'; end if;
end $t1_guard$;
create table erp.initial_import_wip_output_identity_v1(
  output_id uuid primary key references erp.initial_import_wip_outputs(id),
  basis text not null check(basis in('OPENING_PRODUCT','SOURCE_ATTRIBUTES','ASSIGNED_AT_COMPLETION')),
  opening_product_id uuid references erp.products(id),
  output_product_id uuid not null references erp.products(id),
  checked text[] not null,
  unknown text[] not null,
  source_attributes jsonb not null,
  created_at timestamptz not null default statement_timestamp(),
  check((basis='OPENING_PRODUCT')=(opening_product_id is not null))
);
comment on table erp.initial_import_wip_output_identity_v1 is 'BA (audit A10, owner D03=A): why each opening WIP output got its product (OPENING_PRODUCT: the product filled in on the opening WIP; SOURCE_ATTRIBUTES: the brand/colour of its source row matched; ASSIGNED_AT_COMPLETION: no product, brand or colour on the source, the PO model and size matched), what was checked and what stayed unknown (never recorded as matched).';
alter table erp.initial_import_wip_output_identity_v1 enable row level security;
revoke all on erp.initial_import_wip_output_identity_v1 from public,anon,authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.initial_prepayment_dated_floor_v1(p_advance_id uuid,p_from date)
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_floor numeric;
begin
  -- BA (audit A9): the lowest remaining capacity of one advance on p_from and every later day, from the lines on its own
  -- account of its events and of its payments and their reversals (economic date), on top of its opening amount.
  with a as (select * from erp.initial_import_prepayments where id=p_advance_id),
  js as (
    select e.journal_entry_id id from erp.initial_import_prepayment_events e where e.advance_id=p_advance_id and e.journal_entry_id is not null
    union select j.id from erp.journal_entries j join erp.initial_import_prepayment_payments l on l.payment_id=j.source_id
      where l.advance_id=p_advance_id
    union select r.id from erp.journal_entries r join erp.journal_entries j on j.id=r.reversal_of_id
      join erp.initial_import_prepayment_payments l on l.payment_id=j.source_id where l.advance_id=p_advance_id),
  moves as (
    select je.economic_date as day,case when a.party_type='CUSTOMER' then jl.credit-jl.debit else jl.debit-jl.credit end as amount
    from js join erp.journal_entries je on je.id=js.id and je.status in('POSTED','REVERSED')
    join erp.journal_lines jl on jl.journal_entry_id=je.id
    cross join a where jl.account_id=a.coa_account_id)
  select min(a.amount+coalesce((select sum(m.amount) from moves m where m.day<=d.day),0)) into v_floor
  from a cross join (select p_from as day union select m.day from moves m where m.day>p_from) d;
  return v_floor;
end;$function$;
revoke all on function erp.initial_prepayment_dated_floor_v1(uuid,date) from public,anon,authenticated,service_role;
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
  v_dup_type text;v_dup_batch text;
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

  -- BA (audit A1, CP6-09): an import batch may not post an opening item another import batch already posted with the same
  -- identity (AR above compares only import with legacy). Plain material stock: material, warehouse and roll; finished
  -- goods: product, warehouse and grade; cash: account; WIP and BS without a PO source: AR's model/stage/holder rule.
  -- Distinct sources stay admissible: stock both batches tie to their own uninvoiced receipt (receipt identity is unique
  -- across batches) and WIP/BS both carrying a PO source (each batch creates its own, uniquely numbered POs). Party
  -- balances and advances keep their document identity checks. Runs after the shared lock above, like AR.
  if h.migration_batch_id is not null then
    select i.balance_type,ob.batch_code into v_dup_type,v_dup_batch
    from erp.opening_balance_items i
    join erp.opening_balance_items o on o.balance_type=i.balance_type
    join erp.opening_balance_headers oh on oh.id=o.opening_id
    join erp.migration_batches ob on ob.id=oh.migration_batch_id
    left join erp.products ip on ip.id=i.product_id
    left join erp.products op on op.id=o.product_id
    where i.opening_id=h.id and oh.id<>h.id and oh.status='POSTED'
      and oh.migration_batch_id is not null and oh.migration_batch_id<>h.migration_batch_id
      and case i.balance_type
        when 'CASH_BANK' then i.cash_account_id=o.cash_account_id
        when 'MATERIAL' then i.material_id=o.material_id
          and i.location_id=o.location_id
          and i.roll_id is not distinct from o.roll_id
          and not (exists(select 1 from erp.initial_import_receipt_lines rl where rl.opening_item_id=o.id)
            and exists(select 1 from erp.initial_import_opening_stock_sources ss
              join erp.migration_staging_rows x on x.batch_id=ss.batch_id and x.entity_type='UNINVOICED_RECEIPT'
                and x.normalized_payload->>'opening_source_key'=ss.source_key
              where ss.opening_item_id=i.id))
        when 'FINISHED_GOODS' then i.product_id=o.product_id and exists(
          select 1 from erp.fg_stock_movements fm
          where fm.source_type='OPENING_BALANCE_ITEM' and fm.source_id=o.id
            and fm.movement_type='OPENING'
            and fm.location_id=coalesce(i.location_id,v_default_fg_location)
            and fm.quality_grade=coalesce(i.quality_grade,'GRADE_A'))
        when 'WIP' then
          not (exists(select 1 from erp.initial_import_production_sources ps where ps.opening_item_id=i.id)
            and exists(select 1 from erp.initial_import_production_sources ps where ps.opening_item_id=o.id))
          and (coalesce(i.model_id,ip.model_id) is null or coalesce(o.model_id,op.model_id) is null
            or coalesce(i.model_id,ip.model_id)=coalesce(o.model_id,op.model_id))
          and (i.stage is null or o.stage is null or i.stage=o.stage)
          and (i.contractor_id is null or o.contractor_id is null or i.contractor_id=o.contractor_id)
        when 'BS' then
          not (exists(select 1 from erp.initial_import_production_sources ps where ps.opening_item_id=i.id)
            and exists(select 1 from erp.initial_import_production_sources ps where ps.opening_item_id=o.id))
          and (i.product_id is null or o.product_id is null or i.product_id=o.product_id)
          and (coalesce(i.model_id,ip.model_id) is null or coalesce(o.model_id,op.model_id) is null
            or coalesce(i.model_id,ip.model_id)=coalesce(o.model_id,op.model_id))
          and (i.contractor_id is null or o.contractor_id is null or i.contractor_id=o.contractor_id)
          and (i.vendor_id is null or o.vendor_id is null or i.vendor_id=o.vendor_id)
        else false end
    order by i.id,oh.id limit 1;
    if v_dup_type is not null then
      raise exception 'BA_IMPORT_OPENING_ALREADY_POSTED: saldo % yang sama sudah dibukukan oleh batch impor %; tambahan untuk item yang sama dicatat lewat penyesuaian, bukan saldo awal kedua',v_dup_type,v_dup_batch;
    end if;
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
 v_floor integer;v_bound uuid;v_src jsonb;v_basis text;
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
  -- BA (audit A3, CP6-02): the pieces must be in the source stage on the output date and on every later day; a completion
  -- dated before an earlier output's reversal cannot use the pieces that reversal returned later.
  select min(x.left_qty) into v_floor from (
    select s.qty_pcs
      -coalesce((select sum(o.qty_pcs) from erp.initial_import_wip_outputs o
          where o.opening_item_id=i.id and erp._cp3_business_date(o.physical_at)<=d.day),0)
      +coalesce((select sum(o.qty_pcs) from erp.initial_import_wip_output_reversals rv
          join erp.initial_import_wip_outputs o on o.id=rv.output_id
          where o.opening_item_id=i.id and erp._cp3_business_date(rv.physical_at)<=d.day),0) left_qty
    from (select v_date as day
          union select erp._cp3_business_date(o.physical_at) from erp.initial_import_wip_outputs o where o.opening_item_id=i.id
          union select erp._cp3_business_date(rv.physical_at) from erp.initial_import_wip_output_reversals rv
            join erp.initial_import_wip_outputs o on o.id=rv.output_id where o.opening_item_id=i.id) d
    where d.day>=v_date) x;
  if v_qty>v_floor then
    raise exception 'BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING: pada % atau sesudahnya hanya % pcs tersisa di tahap sumber; hasil bertanggal lebih awal tidak boleh memakai potongan yang baru kembali kemudian',v_date,v_floor;
  end if;
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
  -- BA (audit A10, CP6-18; owner D03=A): a product filled in on the opening WIP binds its output (the same product identity,
  -- i.e. its version on the output date); another product, brand, colour or size is refused. Without a product the brand
  -- and colour the source row gives must match (the PO model and the size are matched above). The output records what
  -- was checked and what stayed unknown; unknown data is never recorded as matched.
  select coalesce(p.identity_root_id,p.id) into v_bound from erp.products p where p.id=i.product_id;
  if v_bound is not null then
    if not exists(select 1 from erp.products p where p.id=v_product and coalesce(p.identity_root_id,p.id)=v_bound) then
      raise exception 'BA_WIP_OUTPUT_PRODUCT_BOUND: saldo WIP awal ini terikat pada produk yang diisi di sumbernya; hasil tidak boleh menjadi produk, merek, warna, atau ukuran lain';
    end if;
    v_basis:='OPENING_PRODUCT';
  else
    select x.normalized_payload into v_src from erp.migration_staging_rows x where x.id=s.source_row_id;
    if exists(select 1 from erp.products p join erp.brands b on b.id=p.brand_id where p.id=v_product and (
        (nullif(btrim(v_src->>'brand_code'),'') is not null and lower(btrim(b.brand_code))<>lower(btrim(v_src->>'brand_code')))
        or (nullif(btrim(v_src->>'color_name'),'') is not null and lower(btrim(coalesce(p.color_name,'')))<>lower(btrim(v_src->>'color_name'))))) then
      raise exception 'BA_WIP_OUTPUT_SOURCE_MISMATCH: merek atau warna hasil tidak cocok dengan rincian WIP awal';
    end if;
    v_basis:=case when nullif(btrim(v_src->>'brand_code'),'') is null and nullif(btrim(v_src->>'color_name'),'') is null
      then 'ASSIGNED_AT_COMPLETION' else 'SOURCE_ATTRIBUTES' end;
  end if;
  select id into v_location from erp.locations where location_code=p_payload->>'location_code' and is_active and location_type='FG_WAREHOUSE';
  if v_location is null then raise exception 'location_code: pilih gudang barang jadi aktif';end if;
  v_at:=erp.product_opening_physical_at(v_product,v_date);v_output:=gen_random_uuid();
  -- BA (audit A3): on the day of a reversal the output is recorded after it, so the physical stage timeline never shows the
  -- pieces leaving before they came back (the dated check above counts that day's reversals).
  v_at:=greatest(v_at,(select max(rv.physical_at)+interval '1 microsecond' from erp.initial_import_wip_output_reversals rv
    join erp.initial_import_wip_outputs o on o.id=rv.output_id
    where o.opening_item_id=i.id and erp._cp3_business_date(rv.physical_at)=v_date));
  insert into erp.fg_lots(lot_number,po_id,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,is_open,lot_origin)
   values('OWIP-'||v_output::text,s.po_id,v_product,v_qty,0,v_at,true,'PRODUCTION') returning id into v_lot;
  insert into erp.initial_import_wip_outputs(id,opening_item_id,lot_id,qty_pcs,physical_at,reason,created_by)
   values(v_output,i.id,v_lot,v_qty,v_at,v_reason,erp.current_app_user_id());
  insert into erp.initial_import_wip_output_identity_v1(output_id,basis,opening_product_id,output_product_id,checked,unknown,source_attributes)
   values(v_output,v_basis,i.product_id,v_product,
     case when v_basis='OPENING_PRODUCT' then array['PRODUCT_IDENTITY','PO_MODEL','SIZE']
       else array_remove(array['PO_MODEL','SIZE',case when nullif(btrim(v_src->>'brand_code'),'') is not null then 'BRAND' end,
         case when nullif(btrim(v_src->>'color_name'),'') is not null then 'COLOR' end],null) end,
     case when v_basis='OPENING_PRODUCT' then array[]::text[]
       else array_remove(array[case when nullif(btrim(v_src->>'brand_code'),'') is null then 'BRAND' end,
         case when nullif(btrim(v_src->>'color_name'),'') is null then 'COLOR' end,'PATTERN','MATERIAL'],null) end,
     jsonb_build_object('product_sku',p_payload->>'product_sku','brand_code',v_src->>'brand_code','color_name',v_src->>'color_name'));
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
 -- BA (audit A9, CP6-07; owner D02=A): what lowers the advance uses only the capacity it has on its own date and keeps every
 -- later day non-negative; a later correction does not fund an earlier refund or use.
 if v_op in('APPLY','REFUND') or (v_op in('CORRECT','REVERSE_EVENT') and v_delta<0) then
   if erp.initial_prepayment_dated_floor_v1(a.id,v_date)<0 then
     raise exception 'BA_ADVANCE_DATED_CAPACITY: sisa uang muka pada % dan tanggal sesudahnya tidak mencukupi; kapasitas dari tanggal yang lebih akhir tidak boleh dipakai lebih awal',v_date;
   end if;
 end if;
 insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
   values('initial_import_prepayments',a.id,'UPDATE',jsonb_build_object('operation',v_op,'payment_id',v_payment,'event_id',v_id),erp.current_app_user_id(),v_reason);
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
      v_target:=case when v_now is null then round((r.qty_signed*(r.unit_cost_snapshot-coalesce(r.original_unit_cost_snapshot,r.unit_cost_snapshot)))::numeric,2)
        else v_now-sign(r.qty_signed)*v_posted end;
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
  -- AZ rev2.1: a reversed write-off (outbound item of a material adjustment, a pocket-fabric usage included: its reversal
  -- is only possible while no pocket period covers it, so it is then a plain write-off against OTHER_EXPENSE; GPT audit of
  -- 737649b, AB-01) left at its posting cost while the stock it came from is revalued, and the adjustment document's own cumulative
  -- revaluation (erp._cp6_sync_material_adjustment_revaluation) targets it to zero once reversed. Between the adjustment
  -- day and the reversal day the write-off carries the replayed cost: +I against the write-off account on its day, -I on the
  -- reversal's day (event and state on the reversal movement, outside the document's own book). Both legs on one day: kept.
  for r in select msm.*,rv.id rv_id,rv.physical_at rv_at
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
CREATE OR REPLACE FUNCTION erp.close_accounting_through(p_closed_through date, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare v_old date; v_material uuid; v_readiness jsonb;
begin
  perform erp.require_owner_admin();
  if p_closed_through is null then raise exception 'Tanggal tutup buku wajib diisi'; end if;
  if p_closed_through>=erp._cp3_business_date(statement_timestamp()) then raise exception 'Tutup buku hanya boleh sampai tanggal sebelum hari ini'; end if;
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan tutup buku wajib diisi'; end if;
  select closed_through into v_old from erp.accounting_period_control where singleton_id=1 for update;
  if v_old is not null and p_closed_through<v_old then
    raise exception 'Untuk membuka kembali periode gunakan reopen_accounting_through(); periode saat ini sudah ditutup sampai %',v_old;
  end if;
  -- BA (audit A6, CP6-24): the date already closed files nothing new; filings are immutable, so a second close would file
  -- twice. A close after a reopen stays allowed.
  if v_old is not null and p_closed_through=v_old then
    raise exception 'CLOSE_ALREADY_CLOSED: periode sudah ditutup sampai %; tidak ada filing baru',v_old;
  end if;
  -- One engine, evaluated after the control row lock so posting paths that read closed_through wait for this close.
  v_readiness:=erp.period_readiness_v1(p_closed_through,erp.period_completeness_from_v1());
  if v_readiness->>'status'<>'READY' then
    raise exception using message=format('CLOSE_BLOCKED: tutup buku sampai %s ditolak, %s penghalang (%s).',p_closed_through,
      v_readiness->>'blocker_count',(select string_agg(distinct b->>'code',', ') from jsonb_array_elements(v_readiness->'blockers') b)),
      detail=v_readiness::text,hint='Lihat erp_accounting_close_preflight_v1 untuk daftar lengkap.';
  end if;
  update erp.accounting_period_control
  set closed_through=p_closed_through,updated_at=statement_timestamp(),updated_by=erp.current_app_user_id(),change_reason=p_reason
  where singleton_id=1;

  for v_material in select id from erp.materials order by id loop
    perform erp.refresh_material_cost_checkpoint(v_material,p_closed_through);
  end loop;

  insert into erp.audit_logs(entity_type,entity_id,action,old_data,new_data,changed_by,change_reason)
  values('accounting_period_control',null,'UPDATE',jsonb_build_object('closed_through',v_old),jsonb_build_object('closed_through',p_closed_through,'material_cost_checkpoints_refreshed',true),erp.current_app_user_id(),p_reason);

  -- Filed snapshot: never overwritten; later corrections are read from the engine as current-corrected values.
  insert into erp.accounting_close_filings_v1(closed_through,previous_closed_through,filed_by,reason,readiness,gl_balances)
  values(p_closed_through,v_old,erp.current_app_user_id(),p_reason,v_readiness,
    (select coalesce(jsonb_object_agg(ca.account_code,round(b.balance,2) order by ca.account_code),'{}'::jsonb)
     from (select a.account_id,sum(a.debit_total-a.credit_total) balance from erp.account_daily_balances a
           where a.balance_date<=p_closed_through group by a.account_id) b
     join erp.chart_accounts ca on ca.id=b.account_id));
end;
$function$;
CREATE OR REPLACE FUNCTION erp.assert_new_stock_cutoff_coverage_v1()
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO ''
AS $function$
declare
  v_registry jsonb:='{"erp.accessory_bom_versions.product_id":{"class":"MASTER","reason":"Effective-dated accessory BOM; no stock instant"},"erp.bs_cases.product_id":{"class":"NEW_STOCK_FACT","reason":"physical_at of QC/laundry BS and manual OUT_OF_NOWHERE BS"},"erp.contractor_accessory_reimbursement_entitlements.product_id":{"class":"DERIVED","reason":"Accounting entitlement of an FG lot"},"erp.fg_accessory_cost_snapshots.product_id":{"class":"DERIVED","reason":"Cost snapshot of an FG lot"},"erp.fg_adjustment_items.product_id":{"class":"MOVEMENT","reason":"Adjusts an existing lot"},"erp.fg_inventory_balances.product_id":{"class":"DERIVED","reason":"Balance cache keyed by product/location/grade"},"erp.fg_lots.product_id":{"class":"NEW_STOCK_FACT","reason":"produced_at of every lot except GOOD returned by rework"},"erp.fg_stock_movements.product_id":{"class":"MOVEMENT","reason":"Movement of an existing lot"},"erp.initial_import_wip_output_identity_v1.opening_product_id":{"class":"DERIVED","reason":"Provenance of an opening WIP output: the product filled in on its opening item"},"erp.initial_import_wip_output_identity_v1.output_product_id":{"class":"DERIVED","reason":"Provenance of an opening WIP output; the stock fact is its fg_lots lot"},"erp.journal_lines.product_id":{"class":"ACCOUNTING","reason":"Journal dimension"},"erp.laundry_receipt_batch_size_lines.bs_product_id":{"class":"SOURCE_DOCUMENT","reason":"Laundry receipt input; the BS fact is bs_cases"},"erp.laundry_receipt_bs_product_allocations.product_id":{"class":"SOURCE_DOCUMENT","reason":"Validated as NEW_STOCK; the BS fact is bs_cases"},"erp.non_po_hpp_gl_sync_events_v2620f.product_id":{"class":"ACCOUNTING","reason":"HPP to GL synchronisation event"},"erp.opening_balance_items.product_id":{"class":"SOURCE_DOCUMENT","reason":"Opening document; facts are OPENING lots and LEGACY BS"},"erp.po_accessory_bom_commitments.product_id":{"class":"MASTER","reason":"PO accessory BOM commitment"},"erp.product_conversions.from_product_id":{"class":"SOURCE_DOCUMENT","reason":"Conversion source, validated as EXISTING_STOCK"},"erp.product_conversions.to_product_id":{"class":"SOURCE_DOCUMENT","reason":"Conversion target; the fact is the CONVERSION lot in fg_lots"},"erp.product_identity_mutation_context_v1.product_id":{"class":"AUTHORIZATION","reason":"Private one-use identity edit context"},"erp.product_price_versions.product_id":{"class":"MASTER","reason":"Effective-dated price"},"erp.qc_inspection_items.final_product_id":{"class":"SOURCE_DOCUMENT","reason":"QC input; the facts are fg_lots and bs_cases"},"erp.sales_items.product_id":{"class":"SALES","reason":"Sale of existing stock"},"erp.sales_return_items.product_id":{"class":"SALES","reason":"Return of sold stock"},"erp.stock_explainability_snapshots.product_id":{"class":"REPORT","reason":"Stock explanation snapshot"},"erp.stock_policy_versions.product_id":{"class":"MASTER","reason":"Effective-dated stock policy"}}';
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
CREATE OR REPLACE FUNCTION erp.get_bs_resolution_workspace_v1(
  p_filter text default 'ACTIVE',p_kind text default 'ALL',
  p_pattern_id uuid default null,p_query text default null,
  p_limit integer default 50,p_offset integer default 0
)
returns jsonb
language plpgsql
stable
security definer
set search_path=''
as $function$
declare
  v_filter text:=upper(coalesce(nullif(btrim(p_filter),''),'ACTIVE'));
  v_kind text:=upper(coalesce(nullif(btrim(p_kind),''),'ALL'));
  v_query text:=lower(nullif(btrim(p_query),''));
  v_result jsonb;
begin
  perform erp.require_permission('production.bs_rework.view');
  if v_filter not in('ACTIVE','CLOSED','ALL') then
    raise exception 'filter must be ACTIVE, CLOSED, or ALL';
  end if;
  if v_kind not in('BS','LAUNDRY_CLAIM','ALL') then
    raise exception 'kind must be BS, LAUNDRY_CLAIM, or ALL';
  end if;
  if p_limit is null or p_limit<1 or p_limit>100 then
    raise exception 'limit must be between 1 and 100';
  end if;
  if p_offset is null or p_offset<0 then raise exception 'offset must be nonnegative'; end if;

  with base as (
    select
      'BS'::text kind,'BS:'||b.id::text case_key,b.id,b.bs_number number,
      b.status::text status,b.row_version,b.qty_pcs,
      coalesce(rs.resolved_qty,0)::integer resolved_qty,
      coalesce(rw.active_rework_qty,0)::integer active_rework_qty,
      greatest(b.qty_pcs-coalesce(rs.resolved_qty,0)-coalesce(rw.active_rework_qty,0),0)::integer available_qty,
      b.physical_at opened_at,
      b.po_id,po.po_number,pm.model_name,b.cutting_group_id,cg.group_number,
      case when cg.pattern_id is null then '[]'::jsonb else jsonb_build_array(jsonb_build_object(
        'id',cg.pattern_id,'code',cg.pattern_code_snapshot,
        'revision',cg.pattern_revision_snapshot,'name',cg.pattern_name_snapshot
      )) end patterns,
      b.product_id,p.sku,p.product_name,
      b.responsible_contractor_id,ct.contractor_name,
      b.responsible_vendor_id,lv.vendor_name,
      b.detected_at_stage::text detected_stage,b.cause_source::text cause_source,
      b.untracked_type::text untracked_type,
      null::text claim_type,0::numeric compensation_amount,
      source_receipt.delivery_id laundry_delivery_id,
      b.source_laundry_receipt_line_id laundry_receipt_line_id,
      b.legacy_reference,b.notes,
      case when b.status='ON_HOLD' then 'RELEASE_HOLD'
           when b.status in('OPEN','PARTIAL') then 'START_REWORK_OR_DISPOSITION'
           when b.status='IN_REWORK' then 'COMPLETE_REWORK'
           else 'VIEW_OR_REVERSE' end next_action,
      (b.status in('RESOLVED','SCRAPPED','WRITTEN_OFF','CANCELLED')) is_closed,
      lower(concat_ws(' ',b.bs_number,po.po_number,pm.model_name,cg.group_number,
        cg.pattern_code_snapshot,cg.pattern_revision_snapshot,cg.pattern_name_snapshot,
        p.sku,p.product_name,ct.contractor_name,lv.vendor_name,b.status,
        b.detected_at_stage,b.cause_source,b.untracked_type,b.legacy_reference,b.notes)) search_text,
      coalesce((
        select jsonb_agg(jsonb_build_object(
          'id',bc.id,'work_component_id',bc.work_component_id,
          'code',wc.component_code,'name',wc.component_name,'category',wc.component_category,
          'completed_before_bs_qty',bc.completed_before_bs_qty,
          'lifetime_newly_completed_qty',bc.lifetime_newly_completed_qty,
          'lifetime_paid_qty',bc.lifetime_paid_qty,'notes',bc.notes
        ) order by wc.sequence_default,wc.component_code,bc.id)
        from erp.bs_case_components bc
        join erp.work_components wc on wc.id=bc.work_component_id
        where bc.bs_case_id=b.id
      ),'[]'::jsonb) components,
      coalesce((
        select jsonb_agg(jsonb_build_object(
          'id',br.id,'resolution_type',br.resolution_type,'qty_pcs',br.qty_pcs,
          'compensation_amount',br.compensation_amount,
          'responsible_contractor_id',br.responsible_contractor_id,
          'responsible_vendor_id',br.responsible_vendor_id,
          'source_rework_order_id',br.source_rework_order_id,
          'source_laundry_claim_id',br.source_laundry_claim_id,
          'physical_at',br.physical_at,'notes',br.notes,'created_at',br.created_at
        ) order by br.physical_at desc,br.created_at desc,br.id desc)
        from erp.bs_resolutions br where br.bs_case_id=b.id
      ),'[]'::jsonb) resolutions,
      coalesce((
        select jsonb_agg(jsonb_build_object(
          'id',ro.id,'rework_number',ro.rework_number,
          'destination_type',ro.destination_type,'contractor_id',ro.contractor_id,
          'contractor_name',rc.contractor_name,'vendor_id',ro.vendor_id,
          'vendor_name',rv.vendor_name,'qty_sent',ro.qty_sent,
          'qty_good_returned',ro.qty_good_returned,'qty_bs_returned',ro.qty_bs_returned,
          'physical_sent_at',ro.physical_sent_at,'completed_at',ro.completed_at,
          'status',ro.status,'cost_posted',ro.cost_posted,
          'return_fg_location_id',ro.return_fg_location_id,
          'return_fg_location_name',rl.location_name,'good_fg_lot_id',ro.good_fg_lot_id,
          'row_version',ro.row_version,'notes',ro.notes,
          'components',coalesce((
            select jsonb_agg(jsonb_build_object(
              'id',rcl.id,'bs_case_component_id',rcl.bs_case_component_id,
              'work_component_id',bcc.work_component_id,'component_code',rwc.component_code,
              'component_name',rwc.component_name,'qty_performed',rcl.qty_performed,
              'qty_newly_payable',rcl.qty_newly_payable,'rate_snapshot',rcl.rate_snapshot,
              'amount_payable',rcl.amount_payable,'rate_basis',rcl.rate_basis,'notes',rcl.notes
            ) order by rwc.sequence_default,rwc.component_code,rcl.id)
            from erp.rework_component_lines rcl
            join erp.bs_case_components bcc on bcc.id=rcl.bs_case_component_id
            join erp.work_components rwc on rwc.id=bcc.work_component_id
            where rcl.rework_order_id=ro.id
          ),'[]'::jsonb)
        ) order by ro.physical_sent_at desc,ro.created_at desc,ro.id desc)
        from erp.rework_orders ro
        left join erp.contractors rc on rc.id=ro.contractor_id
        left join erp.laundry_vendors rv on rv.id=ro.vendor_id
        left join erp.locations rl on rl.id=ro.return_fg_location_id
        where ro.bs_case_id=b.id
      ),'[]'::jsonb) rework_orders,
      coalesce((
        select jsonb_agg(jsonb_build_object(
          'id',he.id,'action',he.action,'previous_status',he.previous_status,
          'resulting_status',he.resulting_status,'reason',he.reason,
          'physical_at',he.physical_at,'actor_id',he.actor_id,
          'actor_name',hu.full_name,'created_at',he.created_at
        ) order by he.physical_at desc,he.created_at desc,he.id desc)
        from erp.bs_case_hold_events he
        left join erp.app_users hu on hu.id=he.actor_id
        where he.bs_case_id=b.id
      ),'[]'::jsonb) hold_events
    from erp.bs_cases b
    left join erp.production_orders po on po.id=b.po_id
    left join erp.product_models pm on pm.id=po.model_id
    left join erp.cutting_groups cg on cg.id=b.cutting_group_id
    left join erp.laundry_receipt_lines source_receipt_line
      on source_receipt_line.id=b.source_laundry_receipt_line_id
    left join erp.laundry_receipts source_receipt
      on source_receipt.id=source_receipt_line.receipt_id
    left join erp.products p on p.id=b.product_id
    left join erp.contractors ct on ct.id=b.responsible_contractor_id
    left join erp.laundry_vendors lv on lv.id=b.responsible_vendor_id
    left join lateral(
      select coalesce(sum(x.qty_pcs),0)::integer resolved_qty
      from erp.bs_resolutions x where x.bs_case_id=b.id
    ) rs on true
    left join lateral(
      select coalesce(sum(x.qty_sent),0)::integer active_rework_qty
      from erp.rework_orders x
      where x.bs_case_id=b.id and x.status in('OPEN','IN_PROGRESS','PARTIAL')
    ) rw on true
    where (p_pattern_id is null or cg.pattern_id=p_pattern_id)

    union all

    select
      'LAUNDRY_CLAIM'::text kind,'LAUNDRY_CLAIM:'||c.id::text case_key,
      c.id,c.claim_number number,c.status::text status,c.row_version,c.qty_claimed qty_pcs,
      case when c.status in('SETTLED','WRITTEN_OFF') then c.qty_claimed else 0 end resolved_qty,
      0::integer active_rework_qty,
      case when c.status in('SETTLED','WRITTEN_OFF','REJECTED') then 0 else c.qty_claimed end available_qty,
      c.opened_at,ld.po_id,po.po_number,pm.model_name,null::uuid cutting_group_id,
      null::text group_number,coalesce(cp.patterns,'[]'::jsonb) patterns,
      null::uuid product_id,null::text sku,null::text product_name,
      null::uuid responsible_contractor_id,null::text contractor_name,
      c.vendor_id responsible_vendor_id,lv.vendor_name,
      'LAUNDRY'::text detected_stage,'LAUNDRY'::text cause_source,
      null::text untracked_type,c.claim_type::text claim_type,c.compensation_amount,
      ld.id laundry_delivery_id,c.receipt_line_id laundry_receipt_line_id,
      null::text legacy_reference,c.notes,
      case when c.status in('OPEN','ACCEPTED') then 'RESOLVE_CLAIM' else 'VIEW_OR_REVERSE' end next_action,
      (c.status in('SETTLED','WRITTEN_OFF','REJECTED')) is_closed,
      lower(concat_ws(' ',c.claim_number,c.claim_type,c.status,ld.delivery_number,
        po.po_number,pm.model_name,lv.vendor_name,c.qty_claimed,c.compensation_amount,
        cp.search_patterns,c.notes)) search_text,
      '[]'::jsonb components,
      coalesce((
        select jsonb_agg(jsonb_build_object(
          'id',br.id,'bs_case_id',br.bs_case_id,'resolution_type',br.resolution_type,
          'qty_pcs',br.qty_pcs,'compensation_amount',br.compensation_amount,
          'source_laundry_claim_id',br.source_laundry_claim_id,
          'physical_at',br.physical_at,'notes',br.notes,'created_at',br.created_at
        ) order by br.physical_at desc,br.created_at desc,br.id desc)
        from erp.bs_resolutions br where br.source_laundry_claim_id=c.id
      ),'[]'::jsonb) resolutions,
      '[]'::jsonb rework_orders,'[]'::jsonb hold_events
    from erp.laundry_claims c
    left join erp.laundry_receipt_lines lrl on lrl.id=c.receipt_line_id
    left join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    left join erp.laundry_deliveries ld on ld.id=coalesce(c.delivery_id,lr.delivery_id)
    left join erp.production_orders po on po.id=ld.po_id
    left join erp.product_models pm on pm.id=po.model_id
    left join erp.laundry_vendors lv on lv.id=c.vendor_id
    left join lateral(
      select jsonb_agg(jsonb_build_object(
          'id',z.pattern_id,'code',z.pattern_code_snapshot,
          'revision',z.pattern_revision_snapshot,'name',z.pattern_name_snapshot
        ) order by z.pattern_code_snapshot,z.pattern_revision_snapshot,z.pattern_id) patterns,
        string_agg(concat_ws(' ',z.pattern_code_snapshot,z.pattern_revision_snapshot,z.pattern_name_snapshot),' ') search_patterns
      from(
        select distinct cg.pattern_id,cg.pattern_code_snapshot,
          cg.pattern_revision_snapshot,cg.pattern_name_snapshot
        from erp.laundry_delivery_lines dl
        join erp.cutting_groups cg on cg.id=dl.cutting_group_id
        where cg.pattern_id is not null and (
          (c.receipt_line_id is not null and dl.id=lrl.delivery_line_id)
          or (c.receipt_line_id is null and dl.delivery_id=ld.id)
        )
      ) z
    ) cp on true
    where p_pattern_id is null or exists(
      select 1 from erp.laundry_delivery_lines fdl
      join erp.cutting_groups fcg on fcg.id=fdl.cutting_group_id
      where fcg.pattern_id=p_pattern_id and (
        (c.receipt_line_id is not null and fdl.id=lrl.delivery_line_id)
        or (c.receipt_line_id is null and fdl.delivery_id=ld.id)
      )
    )
  ), filtered as (
    select * from base
    where (v_kind='ALL' or kind=v_kind)
      and (v_filter='ALL' or (v_filter='ACTIVE' and not is_closed) or (v_filter='CLOSED' and is_closed))
      and (v_query is null or search_text like '%'||v_query||'%')
  ), page as (
    select * from filtered
    order by is_closed,opened_at desc,number,id
    limit p_limit offset p_offset
  )
  select jsonb_build_object(
    'filter',v_filter,'kind',v_kind,'pattern_id',p_pattern_id,'query',v_query,
    'limit',p_limit,'offset',p_offset,'total',(select count(*) from filtered),
    'lookups',jsonb_build_object(
      'contractors',coalesce((select jsonb_agg(jsonb_build_object(
        'id',x.id,'code',x.contractor_code,'name',x.contractor_name
      ) order by x.contractor_name,x.contractor_code,x.id)
        from erp.contractors x where x.is_active and x.contractor_type='MANDOR'),'[]'::jsonb),
      'vendors',coalesce((select jsonb_agg(jsonb_build_object(
        'id',x.id,'code',x.vendor_code,'name',x.vendor_name
      ) order by x.vendor_name,x.vendor_code,x.id)
        from erp.laundry_vendors x where x.is_active),'[]'::jsonb),
      'fg_locations',coalesce((select jsonb_agg(jsonb_build_object(
        'id',x.id,'code',x.location_code,'name',x.location_name
      ) order by x.location_name,x.location_code,x.id)
        from erp.locations x where x.is_active and x.location_type='FG_WAREHOUSE'),'[]'::jsonb),
      'work_components',coalesce((select jsonb_agg(jsonb_build_object(
        'id',x.id,'code',x.component_code,'name',x.component_name,'category',x.component_category
      ) order by x.sequence_default,x.component_code,x.id)
        from erp.work_components x where x.is_active),'[]'::jsonb),
      'products',coalesce((select jsonb_agg(jsonb_build_object(
        'id',x.id,'sku',x.sku,'name',x.product_name
      ) order by x.sku,x.id)
        from erp.products x where x.is_active and x.effective_to is null),'[]'::jsonb),
      'laundry_sources',coalesce((select jsonb_agg(jsonb_build_object(
        'id',s.id,'number',s.delivery_number,'vendor_id',s.vendor_id,
        'vendor_name',s.vendor_name,'po_number',s.po_number,
        'physical_at',s.physical_at,'qty_sent_pcs',s.qty_sent_pcs,
        'qty_claimable_pcs',s.qty_claimable_pcs
      ) order by s.physical_at desc,s.delivery_number,s.id)
        from(
          select d.id,d.delivery_number,d.vendor_id,v.vendor_name,po.po_number,
            d.physical_at,sum(dl.qty_sent_pcs)::integer qty_sent_pcs,
            greatest(
              sum(dl.qty_sent_pcs)
              -coalesce((
                select sum(rl.qty_good_received+rl.qty_bs_laundry)
                from erp.laundry_receipt_lines rl
                join erp.laundry_receipts r on r.id=rl.receipt_id
                where r.delivery_id=d.id and r.status='POSTED'
              ),0)
              -coalesce((
                select sum(c.qty_claimed) from erp.laundry_claims c
                where c.delivery_id=d.id and c.claim_type in('MISSING','STUCK')
                  and c.status<>'REJECTED'
              ),0),0
            )::integer qty_claimable_pcs
          from erp.laundry_deliveries d
          join erp.laundry_delivery_lines dl on dl.delivery_id=d.id
          join erp.laundry_vendors v on v.id=d.vendor_id
          join erp.production_orders po on po.id=d.po_id
          where d.status in('SENT','PARTIAL_RETURN','RETURNED','CLOSED')
          group by d.id,d.delivery_number,d.vendor_id,v.vendor_name,po.po_number,d.physical_at
        ) s where s.qty_claimable_pcs>0),'[]'::jsonb),
      'laundry_receipt_sources',coalesce((select jsonb_agg(jsonb_build_object(
        'id',s.id,'receipt_id',s.receipt_id,'number',s.receipt_number,
        'delivery_id',s.delivery_id,'delivery_number',s.delivery_number,
        'vendor_id',s.vendor_id,'vendor_name',s.vendor_name,'po_number',s.po_number,
        'physical_at',s.physical_at,'qty_bs_laundry',s.qty_bs_laundry,
        'qty_claimable_pcs',s.qty_claimable_pcs
      ) order by s.physical_at desc,s.receipt_number,s.id)
        from(
          select rl.id,r.id receipt_id,r.receipt_number,d.id delivery_id,
            d.delivery_number,d.vendor_id,v.vendor_name,po.po_number,r.physical_at,
            rl.qty_bs_laundry,
            greatest(rl.qty_bs_laundry-coalesce((
              select sum(c.qty_claimed) from erp.laundry_claims c
              where c.receipt_line_id=rl.id and c.claim_type='DAMAGE'
                and c.status<>'REJECTED'
            ),0),0)::integer qty_claimable_pcs
          from erp.laundry_receipt_lines rl
          join erp.laundry_receipts r on r.id=rl.receipt_id and r.status='POSTED'
          join erp.laundry_deliveries d on d.id=r.delivery_id
          join erp.laundry_vendors v on v.id=d.vendor_id
          join erp.production_orders po on po.id=d.po_id
          where rl.qty_bs_laundry>0
            and rl.qty_bs_laundry>coalesce((
              select sum(c.qty_claimed) from erp.laundry_claims c
              where c.receipt_line_id=rl.id and c.claim_type='DAMAGE'
                and c.status<>'REJECTED'
            ),0)
        ) s where s.qty_claimable_pcs>0),'[]'::jsonb),
      'settled_claims',coalesce((select jsonb_agg(jsonb_build_object(
        'id',s.id,'number',s.claim_number,'vendor_id',s.vendor_id,
        'vendor_name',s.vendor_name,'delivery_id',s.delivery_id,
        'receipt_line_id',s.receipt_line_id,'qty_claimed',s.qty_claimed,
        'compensation_amount',s.compensation_amount,
        'available_qty',s.available_qty,'available_amount',s.available_amount
      ) order by s.resolved_at desc,s.claim_number,s.id)
        from(
          select c.id,c.claim_number,c.vendor_id,v.vendor_name,
            coalesce(c.delivery_id,claim_receipt.delivery_id) delivery_id,
            c.receipt_line_id,c.qty_claimed,c.compensation_amount,c.resolved_at,
            greatest(c.qty_claimed-coalesce(u.used_qty,0),0)::integer available_qty,
            greatest(c.compensation_amount-coalesce(u.used_amount,0),0)::numeric available_amount
          from erp.laundry_claims c
          join erp.laundry_vendors v on v.id=c.vendor_id
          left join erp.laundry_receipt_lines claim_receipt_line
            on claim_receipt_line.id=c.receipt_line_id
          left join erp.laundry_receipts claim_receipt
            on claim_receipt.id=claim_receipt_line.receipt_id
          left join lateral(
            select coalesce(sum(br.qty_pcs),0)::integer used_qty,
              coalesce(sum(br.compensation_amount),0)::numeric used_amount
            from erp.bs_resolutions br where br.source_laundry_claim_id=c.id
          ) u on true
          where c.status='SETTLED'
            and c.qty_claimed>coalesce(u.used_qty,0)
            and c.compensation_amount>coalesce(u.used_amount,0)
        ) s where s.available_qty>0 and s.available_amount>0),'[]'::jsonb)
    ),
    'rows',coalesce((select jsonb_agg(jsonb_build_object(
      'case_key',x.case_key,'kind',x.kind,'id',x.id,'number',x.number,
      'status',x.status,'row_version',x.row_version,'qty_pcs',x.qty_pcs,
      'resolved_qty',x.resolved_qty,'active_rework_qty',x.active_rework_qty,
      'available_qty',x.available_qty,'opened_at',x.opened_at,
      'po_id',x.po_id,'po_number',x.po_number,'model_name',x.model_name,
      'cutting_group_id',x.cutting_group_id,'group_number',x.group_number,
      'patterns',x.patterns,'product_id',x.product_id,'sku',x.sku,
      'product_name',x.product_name,
      'responsible_contractor_id',x.responsible_contractor_id,
      'contractor_name',x.contractor_name,
      'responsible_vendor_id',x.responsible_vendor_id,'vendor_name',x.vendor_name,
      'detected_stage',x.detected_stage,'cause_source',x.cause_source,
      'untracked_type',x.untracked_type,'claim_type',x.claim_type,
      'compensation_amount',x.compensation_amount,
      'laundry_delivery_id',x.laundry_delivery_id,
      'laundry_receipt_line_id',x.laundry_receipt_line_id,
      'legacy_reference',x.legacy_reference,'notes',x.notes,
      'next_action',x.next_action,'is_closed',x.is_closed,
      'components',x.components,'resolutions',x.resolutions,
      'rework_orders',x.rework_orders,'hold_events',x.hold_events
    ) order by x.is_closed,x.opened_at desc,x.number,x.id) from page x),'[]'::jsonb)
  ) into v_result;
  return v_result;
end
$function$;
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
 end if;
 -- BA (audit A5, CP6-04): every batch not posted yet stays listed (an older editable draft is never cut off), with
 -- the latest 50 of any status.
 return jsonb_build_object('batch',v_batch,'recent',coalesce((select jsonb_agg(x order by x.created_at desc,x.id)
   from (select id,batch_code,status,cutover_at,created_at from erp.migration_batches where status<>'POSTED'
     union select * from (select id,batch_code,status,cutover_at,created_at from erp.migration_batches
       order by created_at desc,id limit 50) latest) x),'[]'::jsonb));
end;$function$;
do $coverage$ begin perform erp.assert_new_stock_cutoff_coverage_v1(); end $coverage$;
insert into erp.schema_migrations(version,description) values('v2.6.20ba','Independent audit closure: import identity, dated WIP and advance capacity, WIP product binding, recost cents, selectors, single close filing');
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule','cp6_v2620ay_rollback_capsule','cp6_v2620az_rollback_capsule','cp6_v2620ba_rollback_capsule')
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
 if object_count<>7314 or fingerprint is distinct from '3fe2f0ccdeb8136cd9c7b47ebbc67743a10c64afeadb71e78fa5148b1487989b' then
  raise exception 'BA_INSTALLED_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
update erp.cp6_v2620ba_rollback_capsule set installed_definition_sha256=encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex');
do $after_data$ declare v_table text;v_hash jsonb;v_after jsonb;v_before jsonb; begin
 v_after:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620ba_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_after:=v_after||jsonb_build_object(v_table,v_hash);
 end loop;
 select snapshot->'before' into v_before from pg_temp.cp6_release_boundary;
 if (v_after-array['initial_import_wip_output_identity_v1']::text[]) is distinct from v_before or exists(select 1 from unnest(array['initial_import_wip_output_identity_v1']::text[]) t where (v_after->t->>'count') is distinct from '0')
  then raise exception 'BA_INSTALL_CHANGED_DATA';end if;
 if exists(with live as (select p.oid::regprocedure::text as identity,encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') as definition_sha256,
  array(select a::text from unnest(p.proacl)a order by a::text) as acl,pg_get_userbyid(p.proowner) as owner
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p')) select 1 from pg_temp.cp6_release_functions f left join live x on x.identity=f.identity
  where f.identity<>all(coalesce((select array_agg(object_regidentity) from erp.cp6_v2620ba_rollback_capsule),'{}'))
  and (x.identity is null or (x.definition_sha256,x.acl,x.owner) is distinct from (f.definition_sha256,f.acl,f.owner)))
  then raise exception 'BA_CAPSULE_INCOMPLETE';end if;
 update erp.cp6_v2620ba_rollback_capsule set boundary_snapshot=(select snapshot from pg_temp.cp6_release_boundary)||jsonb_build_object('after',v_after);
end $after_data$;
do $capsule_guard$
declare expected jsonb;actual jsonb;boundary jsonb;
begin
 if not exists(select 1 from pg_class where oid='erp.cp6_v2620ba_rollback_capsule'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='erp.cp6_v2620ba_rollback_capsule'::regclass and a.grantee<>p.relowner)
   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='erp.cp6_v2620ba_rollback_capsule'::regclass and a.grantee<>'postgres'::regrole)
   or exists(select 1 from pg_policy where polrelid='erp.cp6_v2620ba_rollback_capsule'::regclass)
   or exists(select 1 from pg_trigger where tgrelid='erp.cp6_v2620ba_rollback_capsule'::regclass and not tgisinternal)
   or (select count(*) from erp.cp6_v2620ba_rollback_capsule)<>8 then raise exception 'BA_CAPSULE_SECURITY_OR_COUNT';end if;
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620an_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620an_rollback_capsule'::regclass)) into expected;
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620ba_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620ba_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620ba_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620ba_rollback_capsule'::regclass)) into actual;
 if actual is distinct from expected then raise exception 'BA_CAPSULE_SHAPE_DRIFT';end if;
 select boundary_snapshot into boundary from erp.cp6_v2620ba_rollback_capsule limit 1;
 if 8>0 and (boundary is null or exists(select 1 from erp.cp6_v2620ba_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before'])) then raise exception 'BA_CAPSULE_BOUNDARY';end if;
 if exists(select 1 from erp.cp6_v2620ba_rollback_capsule where object_regidentity<>all(array['erp.post_opening_balance(uuid)','erp.complete_initial_import_wip_v1(jsonb)','erp.manage_initial_prepayment_v1(jsonb)','erp.sync_material_cost_revaluation(uuid)','erp.close_accounting_through(date,text)','erp.assert_new_stock_cutoff_coverage_v1()','erp.get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)','erp.get_initial_import_workspace_v1(uuid)']::text[])
   or definition_sha256 is distinct from encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex')
   or installed_definition_sha256 is null or installed_definition_sha256=definition_sha256
   or installed_definition_sha256 is distinct from encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex'))
  then raise exception 'BA_CAPSULE_SOURCE_DRIFT';end if;
end $capsule_guard$;
commit;
