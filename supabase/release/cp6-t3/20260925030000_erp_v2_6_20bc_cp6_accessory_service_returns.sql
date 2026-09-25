-- CP6 BC: accessory service, return and inspection workflow with owner policy settings (ACC-04b, ACC-DEC01/03..07, ERP-DEC02, ALL-C02/C03). Release candidate of the T3 combined package; closed, drained maintenance required.
begin;
-- Built by scripts/cp6_t3_awx_release.py from supabase/dev/cp6_bc_t1_family.sql (sha256 f2ffdac9ee883f869cc49077c8911afca190d0e5bb993d8bf313ef69ca5e81c2): the T1 body below is unchanged apart from the
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
 if exists(select 1 from erp.schema_migrations where version='v2.6.20bc') or to_regclass('erp.cp6_v2620bc_rollback_capsule') is not null
  or to_regclass('erp.bc_policy_settings_v1') is not null or to_regclass('erp.bc_policy_setting_events_v1') is not null or to_regclass('erp.bc_accessory_zones_v1') is not null or to_regclass('erp.bc_execution_context_v1') is not null or to_regclass('erp.bc_documents_v1') is not null or to_regclass('erp.bc_document_links_v1') is not null or to_regclass('erp.bc_adjustment_purposes_v1') is not null or to_regclass('erp.bc_internal_use_lines_v1') is not null or to_regclass('erp.bc_outstanding_returns_v1') is not null or to_regclass('erp.bc_customer_custody_v1') is not null or to_regclass('erp.bc_return_lots_v1') is not null or to_regclass('erp.bc_lot_events_v1') is not null or to_regclass('erp.bc_count_variances_v1') is not null or to_regclass('erp.bc_opening_note_lines_v1') is not null or to_regclass('erp.bc_note_roundings_v1') is not null or to_regclass('erp.bc_free_issue_lines_v1') is not null
 then raise exception 'BC_EXACT_PREDECESSOR_WITHOUT_SUCCESSOR_REQUIRED';end if;
end $admission$;
do $predecessor$
begin
 if exists(select 1 from supabase_migrations.schema_migrations where version>'20260925020000') then raise exception 'BC_EXACT_PREDECESSOR_REQUIRED';end if;
end $predecessor$;
do $prior_platform$
declare r record;
begin
 for r in select * from jsonb_to_recordset('[{"marker":"v2.6.20ac","stamp":"20260915031500","name":"erp_v2_6_20ac_cp6_temporal_surface_closure","sha":"871fb32b1d4a1e7f9aedfef684b0f2c766092732c38552620eb394061f6240d1"},{"marker":"v2.6.20ad","stamp":"20260915113627","name":"erp_v2_6_20ad_cp6_opening_material_business_day","sha":"58f8f1050e6c325339d7400a43b8c8f3d2375d2067f0c418d3eedfe85430a563"},{"marker":"v2.6.20ae","stamp":"20260915201500","name":"erp_v2_6_20ae_cp6_opening_roll_integrity","sha":"0c6bbf77a68142ddfdae99761a5cc2cd6e2e538be50b391f3303922c748c39d6"},{"marker":"v2.6.20af","stamp":"20260916014332","name":"erp_v2_6_20af_cp6_posted_child_integrity","sha":"3764349ab314c7990f6202d3f0de38b516aff53df2a3b1c4f272bc49667f6db4"},{"marker":"v2.6.20ag","stamp":"20260916050822","name":"erp_v2_6_20ag_cp6_sale_reservation_lineage","sha":"085b84cb6917617c5e6a2d375fd5177542ebe3f021a20de48e239159e34d66c0"},{"marker":"v2.6.20ah","stamp":"20260916070451","name":"erp_v2_6_20ah_cp6_return_allocation_eligibility","sha":"ade908ca9f55b2333c5eac5793b41aaabe0d57879dbb233e428fc882bab5738b"},{"marker":"v2.6.20ai","stamp":"20260916090022","name":"erp_v2_6_20ai_cp6_work_source_lineage","sha":"1ea5a602c5a5fcc9697355d9cca526709a06ee20e4eb4cdb765b2b7345c18d25"},{"marker":"v2.6.20aj","stamp":"20260916202400","name":"erp_v2_6_20aj_cp6_rework_output_lineage","sha":"b36a6359c57ad59d93ea5cb8dc5f7e90a0dd9cd59d48c331b037aa365d400986"},{"marker":"v2.6.20ak","stamp":"20260917033516","name":"erp_v2_6_20ak_cp6_import_reference_preview","sha":"9d06a91bd849c80e1ef99a6ac8996863527a30ef3b4079188be58bd8f3d4311d"},{"marker":"v2.6.20al","stamp":"20260917054049","name":"erp_v2_6_20al_cp6_opening_value_validation","sha":"2d16461cababd4a27827cfb8de01dd993a3a343460cdf049d427b44dd4cb6ea2"},{"marker":"v2.6.20am","stamp":"20260921214120","name":"erp_v2_6_20am_cp6_transfer_integrity","sha":"8fff82f72f9c76dd032778fa43aa37fd3fde98c4304de033d9c484db54f04a60"},{"marker":"v2.6.20an","stamp":"20260921223438","name":"erp_v2_6_20an_cp6_cutting_selectors","sha":"4df51d65fdb9a644fe2eeba92af23446e0c0389a1ebf9f336a0a396c144d7b71"},{"marker":"v2.6.20ao","stamp":"20260922135612","name":"erp_v2_6_20ao_cp6_invoice_retail","sha":"696a75c5969b756ce1973191a757a8c7deade06cb57e96dc5a16d648a4c48520"},{"marker":"v2.6.20ap","stamp":"20260922135615","name":"erp_v2_6_20ap_cp6_connected_import_materials","sha":"70503bb0247c811e066830ba752960a50b7afdfdb4c0c7697dee9a265ef1778a"},{"marker":"v2.6.20aq","stamp":"20260922161019","name":"erp_v2_6_20aq_cp6_accessory_lock_order","sha":"34cee78ee58f612187f7683280565ce2651e788e61efb62ced5e8c4dce7f9ada"},{"marker":"v2.6.20ar","stamp":"20260922185015","name":"erp_v2_6_20ar_cp6_opening_overlap","sha":"c5c973d47a4665723351205ccbcbe2c658c57bff7230f5552c5c2b7ca757371e"},{"marker":"v2.6.20as","stamp":"20260922210815","name":"erp_v2_6_20as_cp6_event_dates_product_identity","sha":"d13e46b3451386309a0a8dc1c89a4817ad8751568b9377f94c790832f8fa53a3"},{"marker":"v2.6.20at","stamp":"20260923005153","name":"erp_v2_6_20at_cp6_wip_temporal_identity","sha":"5e1ea5bfba73ada9aba5a8561efa9056b02154025d39bd10d47d3e4f2494110d"},{"marker":"v2.6.20au","stamp":"20260923045944","name":"erp_v2_6_20au_cp6_controlled_product_lifecycle","sha":"7d6265f081125499cb1813fe3f24c3b203363252727b5dcdfc7f74e311b85481"},{"marker":"v2.6.20av","stamp":"20260923110000","name":"erp_v2_6_20av_cp6_identity_new_stock_cutoff","sha":"c63a1fe3bf76dfc396921e07f57eb043e3bb864425b3289a9546bf66e08169a5"},{"marker":"v2.6.20aw","stamp":"20260924010000","name":"erp_v2_6_20aw_cp6_close_readiness_engine","sha":"c38edc9da084f4a90ee615bde16e6fea72e1072f79d6820d9d3bef27cc2a8ecb"},{"marker":"v2.6.20ax","stamp":"20260924010100","name":"erp_v2_6_20ax_cp6_fg_unsourced_receipts","sha":"c736049386c65f75c82fa790b502cd32c999512738207b7be17d711185c3d9f2"},{"marker":"v2.6.20ay","stamp":"20260924010200","name":"erp_v2_6_20ay_cp6_hpp_dated_from_goods","sha":"fd5ec47a16af264cc9b6a3aeed3d6e19023dc9f49beb51ceb8bfb4ecb14dc411"},{"marker":"v2.6.20az","stamp":"20260924010300","name":"erp_v2_6_20az_cp6_material_recost_dated_from_movement","sha":"e515d12a995a1806537ac08b7b0da15eb817480ead3103b035fc651b62977b8d"},{"marker":"v2.6.20ba","stamp":"20260925010000","name":"erp_v2_6_20ba_cp6_audit_closure","sha":"01bc0965cb945c25b98465a54ebc7fafabcc1d760c0698df1636de8069066960"},{"marker":"v2.6.20bb","stamp":"20260925020000","name":"erp_v2_6_20bb_cp6_open_cutover_states","sha":"ed95f1e84a8a924a830de9362ff890769875d01671b4e83c77208daf23a8df34"}]'::jsonb) as x(marker text,stamp text,name text,sha text) loop
  if not exists(select 1 from erp.schema_migrations where version=r.marker)
   or (select count(*) from supabase_migrations.schema_migrations where name=r.name)<>1
   or not exists(select 1 from supabase_migrations.schema_migrations where version=r.stamp and name=r.name
    and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')=r.sha) then
   raise exception 'BC_PRIOR_PLATFORM_DRIFT: %',r.name;
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
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule','cp6_v2620ay_rollback_capsule','cp6_v2620az_rollback_capsule','cp6_v2620ba_rollback_capsule','cp6_v2620bb_rollback_capsule','cp6_v2620bc_rollback_capsule')
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
  raise exception 'BC_PREDECESSOR_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
do $historical_capsules$
declare r record;actual text;
begin
 for r in select * from jsonb_each_text('{"bs_resolution_v2619_rollback_capsule":"28ab388833da7da87384766ecaedadc66b4d048c303ee91e16f3939e34afdc39","bs_resolution_v2619a_rollback_capsule":"de8dfaab7b63b8742d383a089cdb05e73b629aad9f4df149e6a3c9fb590ef560","bs_resolution_v2619b_rollback_capsule":"d6d4f7457743d51679b5d25bf166ed69ca4b4f098cf5902ff985937531c2505d","bs_resolution_v2619c_rollback_capsule":"0207ba4f2ffba8ed61584709bbd884f1d2ee1a5981194fd7189a45afe8b3cbe1","cp3_r4_rollback_capsule":"7c01add62e66a4e2774a7199c2e77a04cca5e5942dbbba54d22cef720f82bc1d","cp45_v2617_rollback_capsule":"b9a43ce463de9905e94dd6538fd2a4952b0586a78c145f6f9d88aab7d6da3d80","cp45_v2617a_rollback_capsule":"b065dbcfdf1b59cb799e9f58caf6dd5ca7686e9f70826fce6a1ba8f140610022","cp4_v2616_rollback_capsule":"dde0a005dbe7cc93709bdfc6b961f4b9a76bf4db06fd7177d21dc79048af4d2f","cp6_v2620_rollback_capsule":"b42b94c2380f0768259a3d8f7fb645c76ebd6f92e8bae6a37d802352f7effd4f","cp6_v2620a_rollback_capsule":"67befaaf327d2591e1ca1d654132ee483eba39b6cbb4f891c4719d817155d448","cp6_v2620aa_rollback_capsule":"eb0d6fb4fcac2ac06929d577101e604428e9a04821813c342e5b831147dc8948","cp6_v2620ab_rollback_capsule":"3be9a9166e3a607962be819fbe23d38fe455290a7a970dc2aad068079bf30785","cp6_v2620ac_relation_rollback_capsule":"63c595c956e25135e1e032613831f5a08a734ba1f5c4746c46483c84517ad5ea","cp6_v2620ac_rollback_capsule":"51a8b08c9d96e66f03c2c8ba94ed3ed8fb15b26d1a2e4c65c58c614442dfa969","cp6_v2620ad_rollback_capsule":"5c3588109395b32ed743e0f4f5d789a3c59e3fffbab7469138f1f423c877ea9d","cp6_v2620ae_rollback_capsule":"6a75e02bf7b90c542fd9f2ac9534a2de066b047f5ffea65bffb1f83fa63c17f0","cp6_v2620af_rollback_capsule":"bfa89fc0e94d34b29405acedf551935f024942835f31cdc98f0f0983a9550288","cp6_v2620ag_rollback_capsule":"7ddfe6181f0c1c7439faf8a8150c542e958b3bafd8d18b5b2d1eb454fd7a85b7","cp6_v2620ah_rollback_capsule":"361be9321e5f4dadc7c7ec0e99ed746a98e7a4150178fc8355d23707c1507a93","cp6_v2620ai_rollback_capsule":"f2428dd712aa763b1379a4ae5b1a1e1e6ee175b355d8769b854a28f1355181c8","cp6_v2620aj_rollback_capsule":"8e24026dc90a2a92292c2cc6c8faa5fc3de991a19f326db494e0af2a518436f1","cp6_v2620ak_rollback_capsule":"dc7bfce7b9ee6a42e33cdf03cabd99d64435a4615245b2037fd6e4ee399aef10","cp6_v2620al_rollback_capsule":"c9e9aca042674efa5c6fa283e4b9ee47f3353ee9ee95b34e14ef1fd6b09bfde9","cp6_v2620am_rollback_capsule":"e781e631d06c6894c20b1fe6f9c65779f461d19c405c8ae74f28ed7d83ae6a26","cp6_v2620an_rollback_capsule":"ebfa8a281a32fe54babbdc209264ab422fde27f344d48561b90d2af022fe75b3","cp6_v2620ao_rollback_capsule":"b48103dcffcfb4c0c5172d2f11a8af809149c3c82584d0c24e6c740311e18cab","cp6_v2620ap_rollback_capsule":"10123ac8749107ffe9e25e74c9e3bc3080c0e15fc3d844bfcedf06043281e3f7","cp6_v2620aq_rollback_capsule":"35dd70bc3f6eacd8640eea6e22b11d4daaaac96bd7092cc8addefe47d0e3d4b8","cp6_v2620ar_rollback_capsule":"4a445445dc1641310fd3baa2b653bc2ff65b95e2a1f1ae53df2e0bb367fba6a8","cp6_v2620as_rollback_capsule":"8ffec1b6c558d3525b2c22754c2467e92463a201c4decdea0523e68b1a950aa9","cp6_v2620at_rollback_capsule":"8a7aca28f5e2e023d4828bae009962c34c6373740ccb26e30d69b6b661486fa2","cp6_v2620au_rollback_capsule":"f8a90e3df4dcaaf19bf33f1e3348e802e9c6357df673bd9bd524b0b2c1fb5fea","cp6_v2620av_rollback_capsule":"555750c028d4e47105289ffbb7d03bbbc08fa1b7adecf45b06a29bf3abb27b8f","cp6_v2620aw_rollback_capsule":"fe0df122c718e3b373f9527a1fe0bdd4bdb473e2e59d6a710057524fe8142475","cp6_v2620ax_rollback_capsule":"bde6ca64f2ef2df40caf5fe51234a549bff8f5f67ff5276d7344f274e0192465","cp6_v2620ay_rollback_capsule":"4f4e686c95ddf0f9481c2c12c6308ec72d46a1d75f5e7a3a761808ee6ae1361c","cp6_v2620az_rollback_capsule":"1ca0d25f289d7322d649e239ec395e73903795f2c84fe652faf4dcf1d2a90853","cp6_v2620b_rollback_capsule":"f9bf784bff0c54e647f491e257a9649fd0c3e6f10c39ddfc0944c961b9dd7601","cp6_v2620ba_rollback_capsule":"c290dd07139c6e9f31945dacc5fdf680371f83315018efe8fb7f7edee31943db","cp6_v2620bb_rollback_capsule":"ee3dccf2bde5cb00e75c51a754d230964294436fe3ed976d52138844aad46102","cp6_v2620c_rollback_capsule":"f88b1f5890ee8e7041758971bf9c9a3ce2bd0a7be6989fb95332c2dd7fa139aa","cp6_v2620d_rollback_capsule":"fa300c5554da4bb6812c61d726fd64f66329c97b085fa7d6ad5d0d8e5ae31235","cp6_v2620e_rollback_capsule":"143cd291cf4c12e78ab61e74e02ed03b08a48832a5064671868ff2bd2e3e1da7","cp6_v2620f_rollback_capsule":"076133b098e821fc2713af559618adf8aa3e204908f810af440fda355fc7a57f","cp6_v2620g_rollback_capsule":"ed9f4cacb47bd026ad6bdea373d1aa87044ed12aa60323cea453e3187dc488c4","cp6_v2620h_rollback_capsule":"4c25a060a2df3c22cd6fa9ff0b297163e223118a0d930b97bf1282b4756d909d","cp6_v2620i_rollback_capsule":"051203d95c44968abd8594f5bd48e289c4ac9a6c9fa49a89eee1086ad6b2c166","cp6_v2620j_rollback_capsule":"1393a8085d0f58717b13048c9cc3f7e9969ac86c351d6dfefdd2d4f43a735bd2","cp6_v2620k_rollback_capsule":"55aa71061f616ea11b361f0fabee2fd892f6438cc3f567cb9c135552ade42409","cp6_v2620l_rollback_capsule":"b4278768fce4ef307795953c14f607278c43bf474d76d3362e477280be08eb39","cp6_v2620m_rollback_capsule":"4b5f89d7bc4557f92b47716fe15640ab244c424fc1279433eb806d9d91d234e9","cp6_v2620n_rollback_capsule":"46e5ea4524613bb7a386551ada9e06888ea35eb987f9f5b864457fdd18bc3bc1","cp6_v2620o_rollback_capsule":"044e6b1a050df7e2a1d36082b0451877bda01116c08f611dfceb7a666bdf03c8","cp6_v2620p_rollback_capsule":"b656abaf23276984567c6c8d87b311427463c008b5ecd762fbdd0c2df13795df","cp6_v2620q_rollback_capsule":"ab6c992fbaa87f19a4eba696a57a3972f98504a354d9b5fc3be660939f8ea20f","cp6_v2620r_rollback_capsule":"8eb5e0a38284c5f8e3fee56618893ba72feaae9d26605c9ca3874dae25045297","cp6_v2620s_rollback_capsule":"fb57810a75f8829a038ed61b3a1cabde33dccf1e384661bc6723c51e28b3e132","cp6_v2620t_rollback_capsule":"348db4650d788750da243500b49e23c1130fdb70bc4a6d1fdf136bf68aa21f30","cp6_v2620u_rollback_capsule":"720eb1984548a3c381387fbe4d34e3c6f00334c8a4549eab7e398b827dcb7dd4","cp6_v2620v_rollback_capsule":"573ef5842eefadf1c32469514f4c8498667c99aec20ef20651406e4f419f5f60","cp6_v2620w_rollback_capsule":"f4e2ca1d577dd9f2724cc90693e8ee8bff36365c696575b69c6463f3e8ca0324","cp6_v2620x_rollback_capsule":"064db1068b56daa69e409ae582cd8a99490cea75d269154baa4217f90d3ca0d1","cp6_v2620y_rollback_capsule":"e3b23429a7f002c85ca8de1f8c632df13a4a2fc4e4654c12e2431c212772841d","cp6_v2620z_rollback_capsule":"ad0436a1480af43070e9861cb7e28d4cf55c435edbffb5fe368ca7babb7863ef","cutting_bridge_v2618_rollback_capsule":"535d1abd25668bc5bee79d82a602afe5efe4e8ce313bf1fb5170ae2004e3cb2d","cutting_bridge_v2618a_rollback_capsule":"db0608e690b3d936fa20b62cc4cfb9b1f9e86718212526eb6131562578b8bf60"}'::jsonb) loop
  execute format($caps$select encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to((to_jsonb(t)-array['captured_at','boundary_snapshot'])::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$caps$,r.key) into actual;
  if actual is distinct from r.value then raise exception 'BC_HISTORICAL_CAPSULE_DRIFT: %',r.key;end if;
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
 for r in select unnest(array['erp.cp6_v2620ao_rollback_capsule','erp.cp6_v2620ap_rollback_capsule','erp.cp6_v2620aq_rollback_capsule','erp.cp6_v2620ar_rollback_capsule','erp.cp6_v2620as_rollback_capsule','erp.cp6_v2620at_rollback_capsule','erp.cp6_v2620au_rollback_capsule','erp.cp6_v2620av_rollback_capsule','erp.cp6_v2620aw_rollback_capsule','erp.cp6_v2620ax_rollback_capsule','erp.cp6_v2620ay_rollback_capsule','erp.cp6_v2620az_rollback_capsule','erp.cp6_v2620ba_rollback_capsule','erp.cp6_v2620bb_rollback_capsule']::regclass[]) as rel loop
  if not exists(select 1 from pg_class where oid=r.rel and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid=r.rel and a.grantee<>p.relowner)
   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid=r.rel and a.grantee<>'postgres'::regrole)
   or exists(select 1 from pg_policy where polrelid=r.rel)
   or exists(select 1 from pg_trigger where tgrelid=r.rel and not tgisinternal) then raise exception 'BC_PRIOR_CAPSULE_SECURITY: %',r.rel;end if;
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel)) into actual;
  if actual is distinct from expected then raise exception 'BC_PRIOR_CAPSULE_SHAPE_DRIFT: %',r.rel;end if;
  execute format($b$select count(*) filter(where boundary_snapshot is null or not(boundary_snapshot ?& array['before','after','platform_before','markers_before']))
   +(case when count(distinct boundary_snapshot)=1 then 0 else 1 end) from %s$b$,r.rel) into bad;
  if bad<>0 then raise exception 'BC_PRIOR_CAPSULE_BOUNDARY: %',r.rel;end if;
 end loop;
end $prior_capsules$;
create table erp.cp6_v2620bc_rollback_capsule(like erp.cp6_v2620an_rollback_capsule including all);
alter table erp.cp6_v2620bc_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620bc_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620bc_rollback_capsule(object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),i.identity,pg_get_functiondef(p.oid),
 encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
 array(select a::text from unnest(p.proacl)a order by a::text),pg_get_userbyid(p.proowner)
from unnest(array['erp.post_material_adjustment(uuid)','erp._cp6_material_adjustment_revaluation_state(uuid)','erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','erp.sync_material_cost_revaluation(uuid)','erp.populate_payroll_draft(uuid)','erp.validate_material_kasbon_deduction()','erp.refresh_contractor_issue_payroll_status(uuid)','erp.run_integrity_checks()','erp.approve_payroll(uuid)','erp.save_accessory_issue_action_v1(text,jsonb,uuid)','erp.get_accessory_issue_workspace_v1(jsonb)','erp.bb_opening_credit_lines_v1(uuid)','erp.bb_opening_credit_account_v1(uuid)','erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)','erp._validate_migration_batch_base(uuid)','erp.finalize_migration_batch(uuid)','erp.save_initial_import_action_v1(text,jsonb,uuid)','erp.get_initial_import_workspace_v1(uuid)','erp.initial_import_revision_v1(uuid)','erp.assert_new_stock_cutoff_coverage_v1()','erp.run_v265_gudang_write_integrity_checks()','erp.bb_financial_workspace_v1(uuid)']) i(identity)
join pg_proc p on p.oid=i.identity::regprocedure join pg_namespace n on n.oid=p.pronamespace;
create temp table cp6_release_functions on commit drop as
select p.oid::regprocedure::text as identity,encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') as definition_sha256,
  array(select a::text from unnest(p.proacl)a order by a::text) as acl,pg_get_userbyid(p.proowner) as owner
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p');
do $before_data$ declare v_table text;v_hash jsonb;v_before jsonb; begin
 v_before:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620bc_rollback_capsule']::text[]) order by 1 loop
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
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20bb') then raise exception 'BC_T1_REQUIRES_BB'; end if;
 if exists(select 1 from erp.schema_migrations where version='v2.6.20bc') or to_regclass('erp.bc_documents_v1') is not null then raise exception 'BC_T1_ALREADY_INSTALLED'; end if;
end $t1_guard$;
-- ================================================================ BC policy settings, zones, execution context
-- Owner decision 25 Sep 2026: policy rows ACC-DEC01, ACC-DEC03..07 and ERP-DEC02 are application settings with a fail-closed
-- default; runtime acceptance stays case evidence. Until the owner sets a value every dependent financial step is refused
-- with BC_POLICY_PENDING, while the physical steps that do not depend on it (receipt, inspection, custody) stay possible.

create table erp.bc_policy_settings_v1(
  policy_key text primary key check(policy_key in('ACC_DEC01','ACC_DEC03','ACC_DEC04','ACC_DEC05','ACC_DEC06','ACC_DEC07','ERP_DEC02')),
  status text not null default 'PENDING_POLICY_VALUE' check(status in('PENDING_POLICY_VALUE','SET')),
  value jsonb,
  version bigint not null default 1 check(version>0),
  set_by uuid,
  set_at timestamptz not null default statement_timestamp(),
  reason text not null check(length(btrim(reason))>0),
  check((status='SET')=(value is not null))
);
comment on table erp.bc_policy_settings_v1 is 'BC: owner policy settings of the accessory service/return workflow (ACC-DEC01, ACC-DEC03..07, ERP-DEC02). Default PENDING_POLICY_VALUE refuses every dependent financial step; the owner sets or clears a value with an expected version; every change is kept in bc_policy_setting_events_v1 and every document keeps the versions it used.';
create table erp.bc_policy_setting_events_v1(
  id uuid primary key default gen_random_uuid(),
  policy_key text not null references erp.bc_policy_settings_v1(policy_key),
  version bigint not null,
  status text not null check(status in('PENDING_POLICY_VALUE','SET')),
  value jsonb,
  set_by uuid,
  set_at timestamptz not null default statement_timestamp(),
  reason text not null,
  request_id uuid,
  unique(policy_key,version)
);
insert into erp.bc_policy_settings_v1(policy_key,reason)
select k,'Default fail-closed: belum ditetapkan owner' from unnest(array['ACC_DEC01','ACC_DEC03','ACC_DEC04','ACC_DEC05','ACC_DEC06','ACC_DEC07','ERP_DEC02']) k;
insert into erp.bc_policy_setting_events_v1(policy_key,version,status,value,reason)
select policy_key,version,status,value,reason from erp.bc_policy_settings_v1;

-- Zones: a service post, the inspection area and the damaged area are active raw-material warehouse locations registered
-- here (M:5018 option "reuse lokasi gudang bahan dengan sublokasi/tujuan operasional yang sah"); one ledger, the condition is
-- the location. Stock at a zone moves only through the BC facade (or an opening count at import), never through the note,
-- the generic transfer or adjustment.
create table erp.bc_accessory_zones_v1(
  location_id uuid primary key references erp.locations(id),
  zone_kind text not null check(zone_kind in('SERVICE_POST','INSPECTION','DAMAGED')),
  reason text not null check(length(btrim(reason))>0),
  created_by uuid,
  created_at timestamptz not null default statement_timestamp()
);
comment on table erp.bc_accessory_zones_v1 is 'BC: raw-material warehouse locations that are a service post (company stock ready to use at the post), the inspection area (waiting for inspection) or the damaged area (damaged, waiting for disposition). Stock there is not issueable by the mandor note and moves only through erp.save_accessory_service_action_v1.';

create table erp.bc_execution_context_v1(
  backend_pid integer not null,
  transaction_id bigint not null,
  actor_key text not null,
  primary key(backend_pid,transaction_id)
);
comment on table erp.bc_execution_context_v1 is 'BC: marks the transaction of one BC facade command so its native transfers, adjustments and reversals may touch zone stock; the row is removed at the end of the command (rolled back with it on error).';

do $rls$
declare t text;
begin
  foreach t in array array['bc_policy_settings_v1','bc_policy_setting_events_v1','bc_accessory_zones_v1','bc_execution_context_v1'] loop
    execute format('alter table erp.%I enable row level security',t);
    execute format('revoke all on erp.%I from public,anon,authenticated,service_role',t);
  end loop;
end $rls$;

CREATE OR REPLACE FUNCTION erp.bc_enter_context_v1()
 RETURNS void LANGUAGE sql SECURITY DEFINER SET search_path TO ''
AS $function$
  insert into erp.bc_execution_context_v1(backend_pid,transaction_id,actor_key)
  values(pg_backend_pid(),txid_current(),erp._idempotency_actor_key()) on conflict do nothing
$function$;

CREATE OR REPLACE FUNCTION erp.bc_leave_context_v1()
 RETURNS void LANGUAGE sql SECURITY DEFINER SET search_path TO ''
AS $function$
  delete from erp.bc_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current()
$function$;

CREATE OR REPLACE FUNCTION erp.bc_in_context_v1()
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select exists(select 1 from erp.bc_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current())
$function$;

CREATE OR REPLACE FUNCTION erp.bc_zone_kind_v1(p_location uuid)
 RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select zone_kind from erp.bc_accessory_zones_v1 where location_id=p_location $function$;

-- ---------------------------------------------------------------- policy values
CREATE OR REPLACE FUNCTION erp.bc_policy_v1(p_key text)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select case when status='SET' then value end from erp.bc_policy_settings_v1 where policy_key=p_key $function$;

CREATE OR REPLACE FUNCTION erp.bc_policy_version_v1(p_key text)
 RETURNS bigint LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select version from erp.bc_policy_settings_v1 where policy_key=p_key $function$;

CREATE OR REPLACE FUNCTION erp.bc_require_policy_v1(p_key text,p_what text)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v jsonb;
begin
  v:=erp.bc_policy_v1(p_key);
  if v is null then
    raise exception 'BC_POLICY_PENDING: % menunggu keputusan owner (%); langkah finansial ini belum dapat diposting',p_what,replace(p_key,'_','-');
  end if;
  return v;
end;$function$;

-- An active, postable chart account of the allowed types (a setting names the account itself, not a free mapping).
CREATE OR REPLACE FUNCTION erp.bc_policy_account_v1(p_value jsonb,p_field text,p_types text[])
 RETURNS uuid LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v uuid;
begin
  if jsonb_typeof(p_value->p_field) is distinct from 'string' or (p_value->>p_field)!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
    raise exception 'BC_POLICY_VALUE: % wajib id akun',p_field;
  end if;
  select id into v from erp.chart_accounts where id=(p_value->>p_field)::uuid and is_active and is_postable and account_type=any(p_types);
  if v is null then raise exception 'BC_POLICY_VALUE: % harus akun aktif yang dapat diposting berjenis %',p_field,array_to_string(p_types,'/');end if;
  return v;
end;$function$;

-- Normalized value of one setting, or a refusal. Only values the implementation actually supports are accepted.
CREATE OR REPLACE FUNCTION erp.bc_check_policy_value_v1(p_key text,p_value jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v jsonb;v_x jsonb;k text;v_ids jsonb:='[]'::jsonb;v_zone jsonb:='{}'::jsonb;v_users jsonb;u text;
begin
  if jsonb_typeof(p_value) is distinct from 'object' then raise exception 'BC_POLICY_VALUE: nilai pengaturan wajib objek';end if;
  if p_key='ACC_DEC01' then
    perform erp._cp3_assert_closed_json_object(p_value,array['mode'],array['mode'],'ACC-DEC01');
    if p_value->>'mode' is distinct from 'BOTH_REAL_TIMELINES' then raise exception 'BC_POLICY_VALUE: ACC-DEC01 hanya BOTH_REAL_TIMELINES';end if;
    return jsonb_build_object('mode','BOTH_REAL_TIMELINES');
  elsif p_key='ACC_DEC03' then
    perform erp._cp3_assert_closed_json_object(p_value,array['credit_account_id','unit_value_cap'],array['credit_account_id','unit_value_cap'],'ACC-DEC03');
    if p_value->>'unit_value_cap' is null or p_value->>'unit_value_cap' not in('MOVING_AVERAGE','NONE') then
      raise exception 'BC_POLICY_VALUE: ACC-DEC03 unit_value_cap MOVING_AVERAGE atau NONE';end if;
    return jsonb_build_object('credit_account_id',erp.bc_policy_account_v1(p_value,'credit_account_id',array['REVENUE','EXPENSE']),
      'unit_value_cap',p_value->>'unit_value_cap');
  elsif p_key='ACC_DEC04' then
    perform erp._cp3_assert_closed_json_object(p_value,array[]::text[],array['CUSTOMER_SERVICE_account_id','OWN_FG_REPAIR_account_id'],'ACC-DEC04');
    v:='{}'::jsonb;
    foreach k in array array['CUSTOMER_SERVICE_account_id','OWN_FG_REPAIR_account_id'] loop
      if p_value ? k and jsonb_typeof(p_value->k)<>'null' then v:=v||jsonb_build_object(k,erp.bc_policy_account_v1(p_value,k,array['EXPENSE']));end if;
    end loop;
    if v='{}'::jsonb then raise exception 'BC_POLICY_VALUE: ACC-DEC04 memerlukan paling sedikit satu akun tujuan';end if;
    return v;
  elsif p_key='ACC_DEC05' then
    perform erp._cp3_assert_closed_json_object(p_value,array['mode','credit_conditions'],array['mode','credit_conditions'],'ACC-DEC05');
    if p_value->>'mode' is null or p_value->>'mode' not in('CREDIT_UNPAID_ONLY','CREDIT_THEN_CARRY','CREDIT_THEN_REFUND') then
      raise exception 'BC_POLICY_VALUE: ACC-DEC05 mode CREDIT_UNPAID_ONLY, CREDIT_THEN_CARRY atau CREDIT_THEN_REFUND';end if;
    if jsonb_typeof(p_value->'credit_conditions') is distinct from 'array' or jsonb_array_length(p_value->'credit_conditions') not between 1 and 2
      or exists(select 1 from jsonb_array_elements(p_value->'credit_conditions') c where c#>>'{}' not in('USABLE','DAMAGED') or jsonb_typeof(c)<>'string')
      or (select count(distinct c#>>'{}') from jsonb_array_elements(p_value->'credit_conditions') c)<>jsonb_array_length(p_value->'credit_conditions') then
      raise exception 'BC_POLICY_VALUE: ACC-DEC05 credit_conditions berisi USABLE dan/atau DAMAGED';end if;
    return jsonb_build_object('mode',p_value->>'mode','credit_conditions',
      (select jsonb_agg(c order by c) from (select distinct y#>>'{}' c from jsonb_array_elements(p_value->'credit_conditions') y) s));
  elsif p_key='ACC_DEC06' then
    perform erp._cp3_assert_closed_json_object(p_value,array['mode','gain_account_id','loss_account_id'],array['mode','gain_account_id','loss_account_id'],'ACC-DEC06');
    if p_value->>'mode' is distinct from 'NOTE_NEAREST_RUPIAH' then raise exception 'BC_POLICY_VALUE: ACC-DEC06 mode NOTE_NEAREST_RUPIAH';end if;
    return jsonb_build_object('mode','NOTE_NEAREST_RUPIAH','gain_account_id',erp.bc_policy_account_v1(p_value,'gain_account_id',array['REVENUE','EXPENSE']),
      'loss_account_id',erp.bc_policy_account_v1(p_value,'loss_account_id',array['EXPENSE']));
  elsif p_key='ACC_DEC07' then
    perform erp._cp3_assert_closed_json_object(p_value,array['owner_approval_above'],array['owner_approval_above','zone_users'],'ACC-DEC07');
    if jsonb_typeof(p_value->'owner_approval_above') is distinct from 'string' then raise exception 'BC_POLICY_VALUE: ACC-DEC07 owner_approval_above wajib nominal teks';end if;
    perform erp.bb_parse_amount_v1(p_value->>'owner_approval_above','owner_approval_above',true);
    if p_value ? 'zone_users' then
      if jsonb_typeof(p_value->'zone_users') is distinct from 'object' then raise exception 'BC_POLICY_VALUE: zone_users wajib objek lokasi -> daftar pengguna';end if;
      for k,v_users in select key,value from jsonb_each(p_value->'zone_users') loop
        if k!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' or not exists(select 1 from erp.bc_accessory_zones_v1 where location_id=k::uuid) then
          raise exception 'BC_POLICY_VALUE: % bukan zona aksesori terdaftar',k;end if;
        if jsonb_typeof(v_users) is distinct from 'array' or jsonb_array_length(v_users) not between 1 and 50 then
          raise exception 'BC_POLICY_VALUE: daftar pengguna zona % tidak valid',k;end if;
        for u in select jsonb_array_elements_text(v_users) loop
          if u!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' or not exists(select 1 from erp.app_users where id=u::uuid and is_active) then
            raise exception 'BC_POLICY_VALUE: pengguna % tidak aktif atau tidak dikenal',u;end if;
        end loop;
        v_zone:=v_zone||jsonb_build_object(k,(select jsonb_agg(distinct y order by y) from jsonb_array_elements_text(v_users) y));
      end loop;
    end if;
    return jsonb_build_object('owner_approval_above',erp.bb_parse_amount_v1(p_value->>'owner_approval_above','owner_approval_above',true)::numeric(20,2)::text,
      'zone_users',v_zone);
  elsif p_key='ERP_DEC02' then
    perform erp._cp3_assert_closed_json_object(p_value,array['special_free_category_ids'],array['special_free_category_ids'],'ERP-DEC02');
    if jsonb_typeof(p_value->'special_free_category_ids') is distinct from 'array' or jsonb_array_length(p_value->'special_free_category_ids')>50 then
      raise exception 'BC_POLICY_VALUE: ERP-DEC02 special_free_category_ids wajib daftar kategori';end if;
    for v_x in select value from jsonb_array_elements(p_value->'special_free_category_ids') loop
      if jsonb_typeof(v_x) is distinct from 'string' or v_x#>>'{}'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        or not exists(select 1 from erp.accessory_categories where id=(v_x#>>'{}')::uuid and is_active) then
        raise exception 'BC_POLICY_VALUE: kategori gratis % tidak aktif atau tidak dikenal',v_x#>>'{}';end if;
      if not v_ids @> jsonb_build_array(v_x) then v_ids:=v_ids||jsonb_build_array(v_x);end if;
    end loop;
    return jsonb_build_object('special_free_category_ids',(select coalesce(jsonb_agg(y order by y),'[]'::jsonb) from jsonb_array_elements_text(v_ids) y));
  end if;
  raise exception 'BC_POLICY_KEY: pengaturan % tidak dikenal',p_key;
end;$function$;

-- Owner only: set a value or clear it back to pending, against the version the owner saw.
CREATE OR REPLACE FUNCTION erp.bc_set_policy_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare s erp.bc_policy_settings_v1%rowtype;v_key text:=upper(btrim(coalesce(p_payload->>'policy_key','')));v_value jsonb;v_op text;
  v_reason text:=nullif(btrim(p_payload->>'reason'),'');
begin
  if session_user not in('postgres','supabase_admin') and erp.current_app_role() is distinct from 'OWNER' then
    raise exception 'BC_OWNER_ONLY: pengaturan kebijakan hanya dapat diubah owner';
  end if;
  perform erp.require_permission('settings.erp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['policy_key','operation','expected_version','reason'],
    array['policy_key','operation','expected_version','reason','value'],'policy payload');
  v_op:=upper(p_payload->>'operation');
  if v_op not in('SET','CLEAR') then raise exception 'BC_POLICY_OPERATION: SET atau CLEAR';end if;
  if v_reason is null or length(v_reason)>1000 then raise exception 'BC_REASON_REQUIRED: alasan wajib diisi, maksimal 1000 karakter';end if;
  select * into s from erp.bc_policy_settings_v1 where policy_key=replace(v_key,'-','_') for update;
  if s.policy_key is null then raise exception 'BC_POLICY_KEY: pengaturan % tidak dikenal',v_key;end if;
  if jsonb_typeof(p_payload->'expected_version') is distinct from 'string' or p_payload->>'expected_version' is distinct from s.version::text then
    raise exception 'STALE_VERSION: pengaturan % berubah; muat ulang',s.policy_key;end if;
  if v_op='SET' then v_value:=erp.bc_check_policy_value_v1(s.policy_key,p_payload->'value');
  elsif p_payload ? 'value' then raise exception 'BC_POLICY_VALUE: CLEAR tidak membawa nilai';end if;
  update erp.bc_policy_settings_v1 set status=case when v_op='SET' then 'SET' else 'PENDING_POLICY_VALUE' end,value=v_value,version=version+1,
    set_by=erp.current_app_user_id(),set_at=statement_timestamp(),reason=v_reason where policy_key=s.policy_key returning * into s;
  insert into erp.bc_policy_setting_events_v1(policy_key,version,status,value,set_by,reason,request_id)
  values(s.policy_key,s.version,s.status,s.value,s.set_by,v_reason,p_request);
  return jsonb_build_object('policy_key',s.policy_key,'status',s.status,'value',s.value,'version',s.version::text);
end;$function$;

-- ---------------------------------------------------------------- zones
CREATE OR REPLACE FUNCTION erp.bc_register_zone_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_kind text:=upper(coalesce(p_payload->>'zone_kind',''));v_code text:=btrim(coalesce(p_payload->>'location_code',''));
  v_name text:=btrim(coalesce(p_payload->>'location_name',''));v_id uuid;v_reason text:=nullif(btrim(p_payload->>'reason'),'');
begin
  perform erp.require_owner_admin();perform erp.require_permission('master.location.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['zone_kind','location_code','location_name','reason'],
    array['zone_kind','location_code','location_name','reason'],'zone payload');
  if v_kind not in('SERVICE_POST','INSPECTION','DAMAGED') then raise exception 'BC_ZONE_KIND: SERVICE_POST, INSPECTION atau DAMAGED';end if;
  if v_code!~'^[A-Za-z0-9][A-Za-z0-9._-]{1,39}$' or length(v_name) not between 2 and 120 then
    raise exception 'BC_ZONE_IDENTITY: kode lokasi 2-40 huruf/angka dan nama 2-120 karakter';end if;
  if v_reason is null then raise exception 'BC_REASON_REQUIRED: alasan wajib diisi';end if;
  if exists(select 1 from erp.locations where lower(location_code)=lower(v_code)) then raise exception 'BC_ZONE_IDENTITY: kode lokasi sudah dipakai';end if;
  insert into erp.locations(id,location_code,location_name,location_type,is_active)
  values(p_request,v_code,v_name,'RAW_MATERIAL_WAREHOUSE',true) returning id into v_id;
  insert into erp.bc_accessory_zones_v1(location_id,zone_kind,reason,created_by) values(v_id,v_kind,v_reason,erp.current_app_user_id());
  return jsonb_build_object('location_id',v_id,'zone_kind',v_kind,'location_code',v_code);
end;$function$;

-- Zone stock moves only through the BC facade; an opening count may put accessory stock at a zone (ALL-C03).
CREATE OR REPLACE FUNCTION erp.bc_guard_zone_movement_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_kind text;
begin
  select zone_kind into v_kind from erp.bc_accessory_zones_v1 where location_id=new.location_id;
  if v_kind is null then return new;end if;
  if (select material_type from erp.materials where id=new.material_id) is distinct from 'ACCESSORY' then
    raise exception 'BC_ZONE_ACCESSORY_ONLY: zona pos servis/pemeriksaan/rusak hanya untuk aksesori';end if;
  if erp.bc_in_context_v1() then return new;end if;
  if new.movement_type='OPENING' and new.qty_signed>0 then return new;end if;
  if new.movement_type='REVERSAL' and exists(select 1 from erp.material_stock_movements o where o.id=new.reversal_of_id and o.movement_type='OPENING') then
    return new;end if;
  raise exception 'BC_ZONE_NATIVE_REFUSED: stok di % hanya bergerak lewat Pemakaian & Pengembalian Aksesori',
    case v_kind when 'SERVICE_POST' then 'pos servis' when 'INSPECTION' then 'area pemeriksaan' else 'area rusak' end;
end;$function$;
create trigger trg_bc_zone_movement before insert on erp.material_stock_movements
  for each row execute function erp.bc_guard_zone_movement_v1();

-- A registered zone keeps its kind and stays a raw-material warehouse; it cannot be deactivated while it holds stock.
CREATE OR REPLACE FUNCTION erp.bc_guard_zone_location_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  if tg_table_name='bc_accessory_zones_v1' then
    if tg_op='DELETE' or new.location_id<>old.location_id or new.zone_kind<>old.zone_kind then
      raise exception 'BC_ZONE_IMMUTABLE: jenis zona tetap; buat zona baru bila perlu';end if;
    return new;
  end if;
  if exists(select 1 from erp.bc_accessory_zones_v1 where location_id=old.location_id) and (new.location_type is distinct from old.location_type
     or (old.is_active and not new.is_active and exists(select 1 from erp.material_stock_movements m where m.location_id=old.id
       group by m.material_id having sum(m.qty_signed)<>0))) then
    raise exception 'BC_ZONE_IMMUTABLE: zona tetap gudang bahan dan tidak dinonaktifkan selama masih ada stok';
  end if;
  return new;
end;$function$;
create trigger trg_bc_zone_row before update or delete on erp.bc_accessory_zones_v1
  for each row execute function erp.bc_guard_zone_location_v1();
create trigger trg_bc_zone_location before update on erp.locations
  for each row execute function erp.bc_guard_zone_location_v1();
-- ================================================================ BC documents, service post, internal use, returns, inspection
-- M:4751-4908 (flows by ownership and purpose, operator flows, buckets), M:5018-5060 (reuse native transfer/adjustment,
-- command contract), M:5066-5095 (cost treatment, recovery value pending). Every command is one BC document that links the
-- native documents it posted; nothing is written to the ledger except through the native writers.

create table erp.bc_documents_v1(
  id uuid primary key,
  document_number text not null unique,
  action text not null check(action in('FILL_POST','RETURN_TO_WAREHOUSE','INTERNAL_USE','RECEIVE_RETURN','INSPECT','VALUE_CUSTODY',
    'CREDIT_NOTE_RETURN','ALLOCATE_CARRY','DISPOSE_STOCK','CLOSE_CUSTODY','CUSTOMER_GARMENT_IN','CUSTOMER_GARMENT_OUT','COUNT_POST',
    'RESOLVE_VARIANCE','ROUND_NOTE')),
  status text not null default 'POSTED' check(status in('POSTED','REVERSED')),
  physical_at timestamptz not null,
  responsible text check(responsible is null or length(responsible) between 1 and 120),
  reference text check(reference is null or length(reference) between 1 and 200),
  reason text not null check(length(btrim(reason)) between 1 and 1000),
  payload jsonb not null,
  policy_versions jsonb not null default '{}'::jsonb,
  row_version bigint not null default 1 check(row_version>0),
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  reversed_by uuid,
  reversed_at timestamptz,
  reversal_reason text,
  check((status='REVERSED')=(reversed_at is not null and reversal_reason is not null))
);
comment on table erp.bc_documents_v1 is 'BC: one command of the Pemakaian & Pengembalian Aksesori workspace (id = its client request id). The native transfers, adjustments, movements, journals and settlements it posted are in bc_document_links_v1; the reversal is linked, never an edit.';
create table erp.bc_document_links_v1(
  document_id uuid not null references erp.bc_documents_v1(id),
  link_kind text not null check(link_kind in('TRANSFER','ADJUSTMENT','MOVEMENT','JOURNAL','SETTLEMENT','PAYROLL_LINE')),
  link_id uuid not null,
  primary key(document_id,link_kind,link_id)
);
create index bc_document_links_v1_link on erp.bc_document_links_v1(link_kind,link_id);

-- Purpose of a native adjustment posted by BC: its expense (outbound) or income (inbound valuation) account.
create table erp.bc_adjustment_purposes_v1(
  adjustment_id uuid primary key references erp.material_adjustments(id),
  document_id uuid not null references erp.bc_documents_v1(id),
  purpose text not null check(purpose in('FACTORY_USE','CUSTOMER_SERVICE','OWN_FG_REPAIR','RECOVERY_VALUATION','DAMAGE_DISPOSAL','COUNT_LOSS')),
  account_id uuid not null references erp.chart_accounts(id),
  policy_key text,
  policy_version bigint
);
comment on table erp.bc_adjustment_purposes_v1 is 'BC: purpose and account of a native material adjustment posted by the BC facade (internal use by purpose, recovery valuation, disposal). erp.post_material_adjustment and the adjustment revaluation read the account here instead of the fixed OTHER_EXPENSE/OTHER_INCOME; every other adjustment is unchanged.';

create table erp.bc_internal_use_lines_v1(
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references erp.bc_documents_v1(id),
  line_number integer not null check(line_number between 1 and 100),
  material_id uuid not null references erp.materials(id),
  location_id uuid not null references erp.locations(id),
  qty numeric(18,6) not null check(qty>0),
  physical_at timestamptz not null,
  purpose text not null check(purpose in('FACTORY_USE','CUSTOMER_SERVICE','OWN_FG_REPAIR')),
  customer_custody_id uuid,
  adjustment_id uuid not null references erp.material_adjustments(id),
  unique(document_id,line_number)
);

-- Expected returns that are not stock: an item still with a holder, the old accessory of a conversion (BE), an opening
-- UNRETURNED count (ALL-C03). A receipt may name one; received quantity never exceeds the expected quantity.
create table erp.bc_outstanding_returns_v1(
  id uuid primary key default gen_random_uuid(),
  source_kind text not null check(source_kind in('OPENING_UNRETURNED','HOLDER','CONVERSION')),
  owner_kind text not null check(owner_kind in('COMPANY','CUSTOMER')),
  material_id uuid references erp.materials(id),
  description text,
  qty_expected numeric(18,6) not null check(qty_expected>0),
  holder text not null check(length(btrim(holder)) between 1 and 120),
  reference text,
  batch_id uuid references erp.migration_batches(id),
  source_row_id uuid,
  document_id uuid references erp.bc_documents_v1(id),
  status text not null default 'OPEN' check(status in('OPEN','CANCELLED')),
  created_at timestamptz not null default statement_timestamp(),
  check(material_id is not null or description is not null)
);

-- Customer-owned garments in service (ACC-C10): custody only, never company FG, AR, refund or entitlement.
create table erp.bc_customer_custody_v1(
  id uuid primary key,
  in_document_id uuid unique references erp.bc_documents_v1(id),
  customer_id uuid not null references erp.customers(id),
  product_id uuid references erp.products(id),
  description text not null check(length(btrim(description)) between 1 and 200),
  qty numeric(18,6) not null check(qty>0 and qty=trunc(qty)),
  received_at timestamptz not null,
  batch_id uuid references erp.migration_batches(id),
  out_document_id uuid unique references erp.bc_documents_v1(id),
  check((in_document_id is null)=(batch_id is not null))
);

-- One physical return lot (one material of one receipt). Ledger lots are company stock already valued in the ledger
-- (service-post leftover at the inspection area); custody lots are not in the ledger: owned by the mandor until a credit
-- (note return), by the company with value pending (teardown, legacy, opening count), or by a customer.
create table erp.bc_return_lots_v1(
  id uuid primary key default gen_random_uuid(),
  document_id uuid references erp.bc_documents_v1(id),
  line_number integer not null default 1,
  source_kind text not null check(source_kind in('SERVICE_LEFTOVER','NOTE_RETURN','OPENING_NOTE_RETURN','TEARDOWN','LEGACY',
    'OPENING_PENDING_VALUE','OPENING_QUARANTINE','NOTE_RETURN_CREDITED')),
  owner_kind text not null check(owner_kind in('COMPANY','MANDOR')),
  value_mode text not null check(value_mode in('LEDGER','PENDING','MANDOR_OWNED')),
  material_id uuid not null references erp.materials(id),
  location_id uuid not null references erp.locations(id),
  qty_received numeric(18,6) not null check(qty_received>0),
  init_usable numeric(18,6) not null default 0 check(init_usable>=0),
  init_damaged numeric(18,6) not null default 0 check(init_damaged>=0),
  received_at timestamptz not null,
  contractor_id uuid references erp.contractors(id),
  note_item_id uuid references erp.contractor_material_issue_items(id),
  opening_note_line_id uuid,
  outstanding_id uuid references erp.bc_outstanding_returns_v1(id),
  parent_lot_id uuid references erp.bc_return_lots_v1(id),
  parent_event_id uuid,
  batch_id uuid references erp.migration_batches(id),
  source_row_id uuid,
  reference text,
  created_at timestamptz not null default statement_timestamp(),
  check(init_usable+init_damaged<=qty_received),
  check((source_kind='NOTE_RETURN')=(note_item_id is not null)),
  check((source_kind='OPENING_NOTE_RETURN')=(opening_note_line_id is not null)),
  check((owner_kind='MANDOR')=(value_mode='MANDOR_OWNED')),
  check((value_mode='LEDGER')=(source_kind in('SERVICE_LEFTOVER','OPENING_QUARANTINE'))),
  check((source_kind='NOTE_RETURN_CREDITED')=(parent_lot_id is not null and parent_event_id is not null)),
  check((document_id is null)=(batch_id is not null)),
  check((source_kind in('OPENING_PENDING_VALUE','OPENING_QUARANTINE'))=(batch_id is not null))
);
create index bc_return_lots_v1_note on erp.bc_return_lots_v1(note_item_id) where note_item_id is not null;
create index bc_return_lots_v1_opening_note on erp.bc_return_lots_v1(opening_note_line_id) where opening_note_line_id is not null;
create index bc_return_lots_v1_outstanding on erp.bc_return_lots_v1(outstanding_id) where outstanding_id is not null;

-- Events on a lot: inspection split, credit of a note return, valuation, disposition, closing. Each belongs to one BC
-- document; a reversed document's events no longer count.
create table erp.bc_lot_events_v1(
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references erp.bc_documents_v1(id),
  lot_id uuid not null references erp.bc_return_lots_v1(id),
  event_kind text not null check(event_kind in('INSPECT','CREDIT','VALUE','RETURN_TO_OWNER','DISCARD')),
  condition text check(condition in('WAITING','USABLE','DAMAGED')),
  qty_usable numeric(18,6) not null default 0 check(qty_usable>=0),
  qty_damaged numeric(18,6) not null default 0 check(qty_damaged>=0),
  qty numeric(18,6) not null default 0 check(qty>=0),
  inspector text,
  event_at timestamptz not null,
  target_location_id uuid references erp.locations(id),
  unit_value numeric(18,2),
  amount numeric(18,2),
  amount_unpaid numeric(18,2),
  amount_carry numeric(18,2),
  amount_refund numeric(18,2),
  cash_account_id uuid references erp.cash_accounts(id),
  created_at timestamptz not null default statement_timestamp(),
  check((event_kind='INSPECT')=(condition is null)),
  check(event_kind<>'INSPECT' or (qty=0 and qty_usable+qty_damaged>0 and inspector is not null)),
  check(event_kind='INSPECT' or (qty>0 and qty_usable=0 and qty_damaged=0)),
  check(event_kind in('INSPECT','RETURN_TO_OWNER') or condition<>'WAITING'),
  check((event_kind='CREDIT')=(amount is not null and amount_unpaid is not null and amount_carry is not null and amount_refund is not null)),
  check(event_kind<>'CREDIT' or amount=amount_unpaid+amount_carry+amount_refund),
  check((amount_refund>0)=(cash_account_id is not null) or event_kind<>'CREDIT')
);
create index bc_lot_events_v1_lot on erp.bc_lot_events_v1(lot_id);

-- A stock count of a service post: a difference is an unknown variance for review, never asserted as usage (ACC-B06).
create table erp.bc_count_variances_v1(
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references erp.bc_documents_v1(id),
  material_id uuid not null references erp.materials(id),
  location_id uuid not null references erp.locations(id),
  book_qty numeric(18,6) not null,
  counted_qty numeric(18,6) not null check(counted_qty>=0),
  variance numeric(18,6) not null,
  counted_at timestamptz not null,
  resolution_document_id uuid references erp.bc_documents_v1(id),
  check(variance=counted_qty-book_qty)
);

do $rls$
declare t text;
begin
  foreach t in array array['bc_documents_v1','bc_document_links_v1','bc_adjustment_purposes_v1','bc_internal_use_lines_v1',
    'bc_outstanding_returns_v1','bc_customer_custody_v1','bc_return_lots_v1','bc_lot_events_v1','bc_count_variances_v1'] loop
    execute format('alter table erp.%I enable row level security',t);
    execute format('revoke all on erp.%I from public,anon,authenticated,service_role',t);
  end loop;
end $rls$;

-- ---------------------------------------------------------------- parsing and checks
CREATE OR REPLACE FUNCTION erp.bc_parse_at_v1(p_value text,p_field text)
 RETURNS timestamptz LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO '' SET "TimeZone" TO 'UTC'
AS $function$
declare v timestamptz;
begin
  if p_value is null or p_value!~'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+07:00$' then
    raise exception 'BC_DATE_INVALID: % memakai tanggal dan jam WIB (YYYY-MM-DDTHH:MM:SS+07:00)',p_field;end if;
  begin v:=p_value::timestamptz; exception when others then raise exception 'BC_DATE_INVALID: % bukan tanggal yang ada',p_field; end;
  if to_char(v at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')||'+07:00'<>p_value then
    raise exception 'BC_DATE_INVALID: % bukan tanggal yang ada',p_field;end if;
  if v>clock_timestamp()+interval '5 minutes' then raise exception 'BC_DATE_FUTURE: % tidak boleh di masa depan',p_field;end if;
  return v;
end;$function$;

-- Whole PCS for a COUNT unit, up to six decimals otherwise (ACC-A01/A04/A05); never coerced.
CREATE OR REPLACE FUNCTION erp.bc_parse_qty_v1(p_material uuid,p_value jsonb,p_field text)
 RETURNS numeric LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_count boolean;v numeric;
begin
  select u.dimension='COUNT' into v_count from erp.materials m join erp.uom_definitions u on u.unit_code=m.unit_code where m.id=p_material;
  if jsonb_typeof(p_value) is distinct from 'string' then raise exception 'BC_QTY_INVALID: % wajib angka teks',p_field;end if;
  if v_count then
    if p_value#>>'{}'!~'^[1-9][0-9]{0,11}$' then raise exception 'BC_QTY_INVALID: % harus PCS utuh positif',p_field;end if;
  elsif p_value#>>'{}'!~'^[0-9]{1,12}(\.[0-9]{1,6})?$' then raise exception 'BC_QTY_INVALID: % harus angka positif, maksimal enam desimal',p_field;
  end if;
  v:=(p_value#>>'{}')::numeric;
  if v<=0 then raise exception 'BC_QTY_INVALID: % harus lebih dari nol',p_field;end if;
  return v;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bc_accessory_v1(p_material uuid)
 RETURNS uuid LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  if p_material is null or not exists(select 1 from erp.materials where id=p_material and is_active and material_type='ACCESSORY') then
    raise exception 'BC_MATERIAL_INVALID: pilih aksesori yang aktif';end if;
  return p_material;
end;$function$;

-- An active raw-material warehouse of the wanted kind: MAIN (not a zone) or one of the zone kinds (ACC-B05).
CREATE OR REPLACE FUNCTION erp.bc_location_v1(p_location uuid,p_kinds text[],p_field text)
 RETURNS uuid LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_kind text;
begin
  if p_location is null or not exists(select 1 from erp.locations where id=p_location and is_active and location_type='RAW_MATERIAL_WAREHOUSE') then
    raise exception 'BC_LOCATION_INVALID: % harus gudang bahan aktif',p_field;end if;
  v_kind:=coalesce(erp.bc_zone_kind_v1(p_location),'MAIN');
  if not v_kind=any(p_kinds) then
    raise exception 'BC_LOCATION_INVALID: % harus %',p_field,array_to_string(array(select case k when 'MAIN' then 'gudang utama' when 'SERVICE_POST' then 'pos servis'
      when 'INSPECTION' then 'area pemeriksaan' else 'area rusak' end from unnest(p_kinds) k),' atau ');end if;
  -- ACC-DEC07: when the owner lists the users of a zone, only they may move its stock.
  if v_kind<>'MAIN' and erp.bc_policy_v1('ACC_DEC07')->'zone_users' ? p_location::text
     and session_user not in('postgres','supabase_admin')
     and not (erp.bc_policy_v1('ACC_DEC07')->'zone_users'->p_location::text) ? coalesce(erp.current_app_user_id()::text,'') then
    raise exception 'BC_ZONE_USER_DENIED: pengguna ini tidak terdaftar untuk zona tersebut (ACC-DEC07)';end if;
  return p_location;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bc_stock_at_v1(p_material uuid,p_location uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id=p_material and location_id=p_location and roll_id is null
$function$;

-- ACC-DEC07: a valued company cost (internal use, disposal, count loss) needs owner/admin approval until the owner sets a
-- threshold, then only above it.
CREATE OR REPLACE FUNCTION erp.bc_require_value_approval_v1(p_amount numeric)
 RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v jsonb:=erp.bc_policy_v1('ACC_DEC07');
begin
  if v is null or p_amount>(v->>'owner_approval_above')::numeric then
    begin
      perform erp.require_owner_admin();
    exception when others then
      raise exception 'BC_APPROVAL_REQUIRED: biaya % memerlukan persetujuan owner/admin (ACC-DEC07 %)',p_amount::numeric(20,2),
        case when v is null then 'belum ditetapkan' else 'di atas '||(v->>'owner_approval_above') end;
    end;
  end if;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bc_text_v1(p_payload jsonb,p_field text,p_required boolean,p_max integer)
 RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v text;
begin
  if p_payload ? p_field and jsonb_typeof(p_payload->p_field) not in('string','null') then raise exception 'BC_TEXT_INVALID: % wajib teks',p_field;end if;
  v:=nullif(btrim(p_payload->>p_field),'');
  if v is null and p_required then raise exception 'BC_TEXT_REQUIRED: % wajib diisi',p_field;end if;
  if length(v)>p_max then raise exception 'BC_TEXT_INVALID: % maksimal % karakter',p_field,p_max;end if;
  return v;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bc_uuid_v1(p_payload jsonb,p_field text,p_required boolean)
 RETURNS uuid LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  if not (p_payload ? p_field) or jsonb_typeof(p_payload->p_field)='null' then
    if p_required then raise exception 'BC_ID_REQUIRED: % wajib diisi',p_field;end if;
    return null;
  end if;
  if jsonb_typeof(p_payload->p_field)<>'string' or (p_payload->>p_field)!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
    raise exception 'BC_ID_INVALID: % bukan id yang sah',p_field;end if;
  return (p_payload->>p_field)::uuid;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bc_new_document_v1(p_request uuid,p_action text,p_at timestamptz,p_payload jsonb,p_policies jsonb default '{}'::jsonb)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  insert into erp.bc_documents_v1(id,document_number,action,physical_at,responsible,reference,reason,payload,policy_versions,created_by)
  values(p_request,'BCA-'||upper(substr(replace(p_request::text,'-',''),1,16)),p_action,p_at,erp.bc_text_v1(p_payload,'responsible',false,120),
    erp.bc_text_v1(p_payload,'reference',false,200),erp.bc_text_v1(p_payload,'reason',true,1000),p_payload,p_policies,erp.current_app_user_id());
  return p_request;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bc_link_v1(p_document uuid,p_kind text,p_id uuid)
 RETURNS void LANGUAGE sql SECURITY DEFINER SET search_path TO ''
AS $function$ insert into erp.bc_document_links_v1(document_id,link_kind,link_id) values(p_document,p_kind,p_id) on conflict do nothing $function$;

-- Native transfer (value-preserving, M:5018 A) from one location to another for a set of accessory lines.
CREATE OR REPLACE FUNCTION erp.bc_post_transfer_v1(p_document uuid,p_from uuid,p_to uuid,p_at timestamptz,p_items jsonb,p_reason text)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v jsonb;v_id uuid;
begin
  v:=erp.save_material_transfer_draft_v2(jsonb_build_object('transfer_number','BCT-'||upper(substr(replace(gen_random_uuid()::text,'-',''),1,16)),
    'from_location_id',p_from,'to_location_id',p_to,'physical_at',p_at,'notes',p_reason,'change_reason',p_reason,'items',p_items),gen_random_uuid(),null);
  v_id:=(v->>'material_transfer_id')::uuid;
  perform erp.post_material_transfer_v2(v_id,gen_random_uuid(),(v->>'row_version')::bigint,p_reason);
  perform erp.bc_link_v1(p_document,'TRANSFER',v_id);
  return v_id;
end;$function$;

-- Native adjustment with the BC purpose account (read by erp.post_material_adjustment through bc_adjustment_account_v1).
CREATE OR REPLACE FUNCTION erp.bc_post_adjustment_v1(p_document uuid,p_location uuid,p_at timestamptz,p_reason_code text,p_items jsonb,
  p_reason text,p_purpose text,p_account uuid,p_policy_key text default null)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v jsonb;v_id uuid;
begin
  v:=erp.save_material_adjustment_draft_v2(jsonb_build_object('adjustment_number','BCJ-'||upper(substr(replace(gen_random_uuid()::text,'-',''),1,16)),
    'reason_code',p_reason_code,'physical_at',p_at,'location_id',p_location,'notes',p_reason,'change_reason',p_reason,'items',p_items),gen_random_uuid(),null);
  v_id:=(v->>'material_adjustment_id')::uuid;
  insert into erp.bc_adjustment_purposes_v1(adjustment_id,document_id,purpose,account_id,policy_key,policy_version)
  values(v_id,p_document,p_purpose,p_account,p_policy_key,case when p_policy_key is not null then erp.bc_policy_version_v1(p_policy_key) end);
  perform erp.post_material_adjustment_v2(v_id,gen_random_uuid(),(v->>'row_version')::bigint,p_reason);
  perform erp.bc_link_v1(p_document,'ADJUSTMENT',v_id);
  return v_id;
end;$function$;

-- The account erp.post_material_adjustment and the adjustment revaluation use for an adjustment (BC purpose, else the
-- unchanged OTHER_EXPENSE for an outbound and OTHER_INCOME for an inbound adjustment).
CREATE OR REPLACE FUNCTION erp.bc_adjustment_account_v1(p_adjustment uuid,p_mapping text)
 RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce((select account_id from erp.bc_adjustment_purposes_v1 where adjustment_id=p_adjustment
    and ((p_mapping='OTHER_EXPENSE' and purpose not in('RECOVERY_VALUATION')) or (p_mapping='OTHER_INCOME' and purpose='RECOVERY_VALUATION'))),
    (select account_id from erp.accounting_account_mappings where mapping_key=p_mapping))
$function$;

CREATE OR REPLACE FUNCTION erp.bc_adjustment_value_v1(p_adjustment uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select round(coalesce(sum(m.qty_signed*m.unit_cost_snapshot),0),2) from erp.material_stock_movements m join erp.material_adjustment_items i on i.id=m.source_id
  where m.source_type='MATERIAL_ADJUSTMENT_ITEM' and i.adjustment_id=p_adjustment and m.reversal_of_id is null
$function$;

-- Lines [{material_id, qty}] of distinct active accessories, 1..100.
CREATE OR REPLACE FUNCTION erp.bc_lines_v1(p_payload jsonb,p_extra text[] default array[]::text[])
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v jsonb:='[]'::jsonb;v_x jsonb;n integer:=0;v_material uuid;
begin
  if jsonb_typeof(p_payload->'items') is distinct from 'array' or jsonb_array_length(p_payload->'items') not between 1 and 100 then
    raise exception 'BC_LINES_INVALID: isi 1 sampai 100 baris aksesori';end if;
  for v_x in select value from jsonb_array_elements(p_payload->'items') loop
    n:=n+1;
    perform erp._cp3_assert_closed_json_object(v_x,array['material_id','qty'],array['material_id','qty']||p_extra,'accessory line');
    v_material:=erp.bc_accessory_v1(erp.bc_uuid_v1(v_x,'material_id',true));
    v:=v||jsonb_build_array(v_x||jsonb_build_object('line_number',n,'material_id',v_material,'qty',erp.bc_parse_qty_v1(v_material,v_x->'qty','qty baris '||n)::text));
  end loop;
  return v;
end;$function$;

-- ---------------------------------------------------------------- lot state
CREATE OR REPLACE FUNCTION erp.bc_lot_state_v1(p_lot uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  with l as(select * from erp.bc_return_lots_v1 where id=p_lot),
  e as(select e.* from erp.bc_lot_events_v1 e join erp.bc_documents_v1 d on d.id=e.document_id where e.lot_id=p_lot and d.status='POSTED'),
  s as(select l.*,
    l.init_usable+coalesce((select sum(qty_usable) from e where event_kind='INSPECT'),0) inspected_usable,
    l.init_damaged+coalesce((select sum(qty_damaged) from e where event_kind='INSPECT'),0) inspected_damaged,
    coalesce((select sum(qty) from e where event_kind<>'INSPECT' and condition='USABLE'),0) out_usable,
    coalesce((select sum(qty) from e where event_kind<>'INSPECT' and condition='DAMAGED'),0) out_damaged,
    coalesce((select sum(qty) from e where event_kind<>'INSPECT' and condition='WAITING'),0) out_waiting,
    coalesce((select sum(qty) from e where event_kind='CREDIT'),0) credited
   from l)
  select jsonb_build_object('lot_id',id,'received',qty_received,
    'waiting',qty_received-inspected_usable-inspected_damaged-out_waiting,
    'usable',inspected_usable-out_usable,'damaged',inspected_damaged-out_damaged,
    'inspected_usable',inspected_usable,'inspected_damaged',inspected_damaged,'credited',credited,
    'open',qty_received-out_usable-out_damaged-out_waiting)
  from s
$function$;

-- The lot state for the pages: every quantity as exact text (the pages never parse a JSON number as an amount).
CREATE OR REPLACE FUNCTION erp.bc_lot_state_text_v1(p_lot uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_object_agg(k,(st->>k)::numeric(24,6)::text)
  from erp.bc_lot_state_v1(p_lot) st,unnest(array['received','inspected_usable','inspected_damaged','usable','damaged','waiting','credited','open']) k
$function$;

-- Lock a lot (and its source) for a command; the state is read after the lock.
CREATE OR REPLACE FUNCTION erp.bc_lock_lot_v1(p_lot uuid)
 RETURNS erp.bc_return_lots_v1 LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.bc_return_lots_v1%rowtype;
begin
  select * into l from erp.bc_return_lots_v1 where id=p_lot;
  if l.id is null then raise exception 'BC_LOT_NOT_FOUND: penerimaan tidak ditemukan';end if;
  perform pg_advisory_xact_lock(hashtextextended('BCLOT|'||l.id::text,0));
  if l.document_id is not null and (select status from erp.bc_documents_v1 where id=l.document_id)<>'POSTED' then
    raise exception 'BC_LOT_REVERSED: penerimaan ini sudah dibatalkan';end if;
  if l.parent_event_id is not null and (select d.status from erp.bc_lot_events_v1 e join erp.bc_documents_v1 d on d.id=e.document_id where e.id=l.parent_event_id)<>'POSTED' then
    raise exception 'BC_LOT_REVERSED: kredit asal lot ini sudah dibatalkan';end if;
  select * into l from erp.bc_return_lots_v1 where id=p_lot for update;
  return l;
end;$function$;

-- ---------------------------------------------------------------- FILL_POST / RETURN_TO_WAREHOUSE (M:5.2, 5.4; ACC-B01/B02)
CREATE OR REPLACE FUNCTION erp.bc_move_post_v1(p_action text,p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_from uuid;v_to uuid;v_at timestamptz;v_lines jsonb;v_transfer uuid;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['from_location_id','to_location_id','physical_at','items','reason'],
    array['from_location_id','to_location_id','physical_at','items','reason','responsible','reference'],'service post payload');
  if p_action='FILL_POST' then
    v_from:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'from_location_id',true),array['MAIN'],'gudang asal');
    v_to:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'to_location_id',true),array['SERVICE_POST'],'pos tujuan');
  else
    v_from:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'from_location_id',true),array['SERVICE_POST'],'pos asal');
    v_to:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'to_location_id',true),array['MAIN'],'gudang tujuan');
  end if;
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  v_lines:=erp.bc_lines_v1(p_payload);
  if (select count(distinct x->>'material_id') from jsonb_array_elements(v_lines) x)<>jsonb_array_length(v_lines) then
    raise exception 'BC_LINES_INVALID: aksesori yang sama tidak boleh dua baris';end if;
  perform erp.bc_new_document_v1(p_request,p_action,v_at,p_payload);
  v_transfer:=erp.bc_post_transfer_v1(p_request,v_from,v_to,v_at,
    (select jsonb_agg(jsonb_build_object('material_id',x->>'material_id','qty',x->>'qty') order by (x->>'line_number')::int) from jsonb_array_elements(v_lines) x),
    btrim(p_payload->>'reason'));
  return jsonb_build_object('transfer_id',v_transfer);
end;$function$;

-- ---------------------------------------------------------------- INTERNAL_USE (M:5.1, 5.3; ACC-B03/B06)
-- Lines with their own physical time and purpose; one native adjustment per (time, purpose, location, custody). Purpose
-- FACTORY_USE keeps the existing INTERNAL_FACTORY_USE account (OTHER_EXPENSE); CUSTOMER_SERVICE and OWN_FG_REPAIR need the
-- ACC-DEC04 account. No note, receivable or reimbursement entitlement is made.
CREATE OR REPLACE FUNCTION erp.bc_internal_use_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_location uuid;v_lines jsonb;v_x jsonb;g record;v_adj uuid;v_account uuid;v_policy text;v_total numeric:=0;v_at timestamptz;
  v_dec04 jsonb;v_custody uuid;v_ids jsonb:='[]'::jsonb;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['location_id','items','reason'],
    array['location_id','items','reason','responsible','reference'],'internal use payload');
  v_location:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'location_id',true),array['MAIN','SERVICE_POST'],'lokasi sumber');
  v_lines:=erp.bc_lines_v1(p_payload,array['physical_at','purpose','customer_custody_id']);
  v_dec04:=erp.bc_policy_v1('ACC_DEC04');
  for v_x in select value from jsonb_array_elements(v_lines) loop
    if v_x->>'purpose' is null or v_x->>'purpose' not in('FACTORY_USE','CUSTOMER_SERVICE','OWN_FG_REPAIR') then
      raise exception 'BC_PURPOSE_INVALID: tujuan baris % FACTORY_USE, CUSTOMER_SERVICE atau OWN_FG_REPAIR',v_x->>'line_number';end if;
    perform erp.bc_parse_at_v1(v_x->>'physical_at','waktu baris '||(v_x->>'line_number'));
    if v_x->>'purpose'<>'FACTORY_USE' then
      perform erp.bc_require_policy_v1('ACC_DEC04','akun biaya '||case v_x->>'purpose' when 'CUSTOMER_SERVICE' then 'servis pelanggan' else 'perbaikan FG sendiri' end);
      if v_dec04->>((v_x->>'purpose')||'_account_id') is null then
        raise exception 'BC_POLICY_PENDING: akun tujuan % belum ditetapkan owner (ACC-DEC04)',v_x->>'purpose';end if;
    end if;
    v_custody:=erp.bc_uuid_v1(v_x,'customer_custody_id',false);
    if v_custody is not null and (v_x->>'purpose'<>'CUSTOMER_SERVICE' or not exists(select 1 from erp.bc_customer_custody_v1 c
        where c.id=v_custody and (c.out_document_id is null or (select status from erp.bc_documents_v1 where id=c.out_document_id)<>'POSTED')
          and (c.batch_id is not null or (select status from erp.bc_documents_v1 where id=c.in_document_id)='POSTED'))) then
      raise exception 'BC_CUSTODY_INVALID: titipan pelanggan hanya untuk servis pelanggan yang masih dititipkan';end if;
  end loop;
  select min(erp.bc_parse_at_v1(x->>'physical_at','physical_at')) into v_at from jsonb_array_elements(v_lines) x;
  perform erp.bc_new_document_v1(p_request,'INTERNAL_USE',v_at,p_payload,
    case when exists(select 1 from jsonb_array_elements(v_lines) x where x->>'purpose'<>'FACTORY_USE')
      then jsonb_build_object('ACC_DEC04',erp.bc_policy_version_v1('ACC_DEC04')) else '{}'::jsonb end
    ||jsonb_build_object('ACC_DEC07',erp.bc_policy_version_v1('ACC_DEC07')));
  for g in select erp.bc_parse_at_v1(x->>'physical_at','physical_at') at_,x->>'purpose' purpose,nullif(x->>'customer_custody_id','') custody,
      jsonb_agg(jsonb_build_object('material_id',x->>'material_id','qty_signed',(-(x->>'qty')::numeric)::text) order by (x->>'line_number')::int) items,
      jsonb_agg(x order by (x->>'line_number')::int) lines
    from jsonb_array_elements(v_lines) x group by 1,2,3 order by 1,2,3 loop
    v_account:=case g.purpose when 'FACTORY_USE' then erp.bc_adjustment_account_v1(null,'OTHER_EXPENSE')
      else (v_dec04->>(g.purpose||'_account_id'))::uuid end;
    v_policy:=case when g.purpose='FACTORY_USE' then null else 'ACC_DEC04' end;
    v_adj:=erp.bc_post_adjustment_v1(p_request,v_location,g.at_,'INTERNAL_FACTORY_USE',g.items,btrim(p_payload->>'reason'),g.purpose,v_account,v_policy);
    insert into erp.bc_internal_use_lines_v1(document_id,line_number,material_id,location_id,qty,physical_at,purpose,customer_custody_id,adjustment_id)
    select p_request,(x->>'line_number')::int,(x->>'material_id')::uuid,v_location,(x->>'qty')::numeric,g.at_,g.purpose,g.custody::uuid,v_adj
    from jsonb_array_elements(g.lines) x;
    v_total:=v_total-erp.bc_adjustment_value_v1(v_adj);
    v_ids:=v_ids||jsonb_build_array(v_adj);
  end loop;
  perform erp.bc_require_value_approval_v1(v_total);
  return jsonb_build_object('adjustment_ids',v_ids,'cost',v_total::numeric(20,2)::text);
end;$function$;

-- ---------------------------------------------------------------- RECEIVE_RETURN (M:5.6; ACC-C01..C05, C09, C11)
-- Asks the origin first. SERVICE_LEFTOVER: company stock moves from the post to the inspection area (value kept). NOTE_RETURN
-- (a posted mandor note line, native or opening): mandor-owned custody until an ACC-DEC05 credit, capped by the note line's
-- quantity less its other returns. TEARDOWN and LEGACY: company custody with value pending (ACC-DEC03), LEGACY only for
-- owner/admin (special review). The physical time is the real return time (ACC-DEC01: both real timelines).
CREATE OR REPLACE FUNCTION erp.bc_receive_return_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_kind text:=upper(coalesce(p_payload->>'source_kind',''));v_at timestamptz;v_zone uuid;v_from uuid;v_lines jsonb;v_x jsonb;
  v_lot uuid;v_lots jsonb:='[]'::jsonb;v_item erp.contractor_material_issue_items%rowtype;v_issue erp.contractor_material_issues%rowtype;
  v_used numeric;v_note record;v_out erp.bc_outstanding_returns_v1%rowtype;v_transfer uuid;v_ref text;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['source_kind','location_id','physical_at','reason'],
    array['source_kind','location_id','from_location_id','physical_at','items','note_item_id','opening_note_line_id','qty','reason',
      'responsible','reference'],'return receipt payload');
  if v_kind not in('SERVICE_LEFTOVER','NOTE_RETURN','TEARDOWN','LEGACY') then
    raise exception 'BC_SOURCE_KIND: asal pengembalian SERVICE_LEFTOVER, NOTE_RETURN, TEARDOWN atau LEGACY';end if;
  v_zone:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'location_id',true),array['INSPECTION'],'area pemeriksaan');
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  v_ref:=erp.bc_text_v1(p_payload,'reference',v_kind in('TEARDOWN','LEGACY'),200);
  if v_kind='LEGACY' then
    begin perform erp.require_owner_admin();
    exception when others then raise exception 'BC_LEGACY_REVIEW: histori lama tanpa sumber hanya dicatat owner/admin (review khusus)';end;
  end if;
  if v_kind='NOTE_RETURN' then
    if (p_payload ? 'items') or (p_payload ? 'from_location_id') then raise exception 'BC_SOURCE_KIND: retur nota memakai baris nota dan qty';end if;
    if (p_payload ? 'note_item_id')=(p_payload ? 'opening_note_line_id') then
      raise exception 'BC_NOTE_SOURCE_REQUIRED: pilih satu baris nota mandor (nota sistem atau nota saldo awal)';end if;
    perform erp.bc_new_document_v1(p_request,'RECEIVE_RETURN',v_at,p_payload);
    if p_payload ? 'note_item_id' then
      select * into v_item from erp.contractor_material_issue_items where id=erp.bc_uuid_v1(p_payload,'note_item_id',true);
      if v_item.id is null then raise exception 'BC_NOTE_SOURCE_REQUIRED: baris nota tidak ditemukan';end if;
      perform pg_advisory_xact_lock(hashtextextended('BCNOTE|'||v_item.id::text,0));
      select * into v_issue from erp.contractor_material_issues where id=v_item.issue_id for update;
      if v_issue.status<>'POSTED' then raise exception 'BC_NOTE_NOT_POSTED: retur hanya untuk nota mandor yang disahkan dan tidak dibatalkan';end if;
      if (select material_type from erp.materials where id=v_item.material_id)<>'ACCESSORY' then raise exception 'BC_NOTE_NOT_ACCESSORY: retur nota hanya untuk aksesori';end if;
      if v_at<v_issue.physical_at then raise exception 'BC_DATE_BEFORE_SOURCE: retur tidak boleh sebelum waktu nota';end if;
      select coalesce(sum(l.qty_received),0) into v_used from erp.bc_return_lots_v1 l join erp.bc_documents_v1 d on d.id=l.document_id
        where l.note_item_id=v_item.id and d.status='POSTED';
      if erp.bc_parse_qty_v1(v_item.material_id,p_payload->'qty','qty')>v_item.qty-v_used then
        raise exception 'BC_RETURN_EXCEEDS_SOURCE: sisa yang dapat dikembalikan dari baris nota ini % , diminta %',(v_item.qty-v_used)::numeric(18,6),p_payload->>'qty';end if;
      insert into erp.bc_return_lots_v1(document_id,source_kind,owner_kind,value_mode,material_id,location_id,qty_received,received_at,contractor_id,note_item_id)
      values(p_request,'NOTE_RETURN','MANDOR','MANDOR_OWNED',v_item.material_id,v_zone,(p_payload->>'qty')::numeric,v_at,v_issue.contractor_id,v_item.id)
      returning id into v_lot;
    else
      select n.*,b.contractor_id,b.status balance_status into v_note from erp.bc_opening_note_lines_v1 n
        join erp.opening_subledger_balances b on b.id=n.balance_id where n.id=erp.bc_uuid_v1(p_payload,'opening_note_line_id',true);
      if v_note.id is null then raise exception 'BC_NOTE_SOURCE_REQUIRED: baris nota saldo awal tidak ditemukan';end if;
      perform pg_advisory_xact_lock(hashtextextended('BCNOTE|'||v_note.id::text,0));
      if v_at<(select cutover_at from erp.migration_batches where id=v_note.batch_id) then
        raise exception 'BC_DATE_BEFORE_SOURCE: retur nota saldo awal dicatat pada atau sesudah cutover';end if;
      select coalesce(sum(l.qty_received),0) into v_used from erp.bc_return_lots_v1 l join erp.bc_documents_v1 d on d.id=l.document_id
        where l.opening_note_line_id=v_note.id and d.status='POSTED';
      if erp.bc_parse_qty_v1(v_note.material_id,p_payload->'qty','qty')>v_note.qty-v_used then
        raise exception 'BC_RETURN_EXCEEDS_SOURCE: sisa yang dapat dikembalikan dari baris nota ini % , diminta %',(v_note.qty-v_used)::numeric(18,6),p_payload->>'qty';end if;
      insert into erp.bc_return_lots_v1(document_id,source_kind,owner_kind,value_mode,material_id,location_id,qty_received,received_at,contractor_id,opening_note_line_id)
      values(p_request,'OPENING_NOTE_RETURN','MANDOR','MANDOR_OWNED',v_note.material_id,v_zone,(p_payload->>'qty')::numeric,v_at,v_note.contractor_id,v_note.id)
      returning id into v_lot;
    end if;
    return jsonb_build_object('lot_ids',jsonb_build_array(v_lot));
  end if;
  if (p_payload ? 'note_item_id') or (p_payload ? 'opening_note_line_id') or (p_payload ? 'qty') then
    raise exception 'BC_SOURCE_KIND: baris nota hanya untuk retur nota';end if;
  v_lines:=erp.bc_lines_v1(p_payload,array['outstanding_id']);
  perform erp.bc_new_document_v1(p_request,'RECEIVE_RETURN',v_at,p_payload);
  if v_kind='SERVICE_LEFTOVER' then
    v_from:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'from_location_id',true),array['SERVICE_POST'],'pos asal');
    if exists(select 1 from jsonb_array_elements(v_lines) x where x ? 'outstanding_id') then
      raise exception 'BC_SOURCE_KIND: sisa pos adalah stok perusahaan, bukan barang yang ditunggu';end if;
    if (select count(distinct x->>'material_id') from jsonb_array_elements(v_lines) x)<>jsonb_array_length(v_lines) then
      raise exception 'BC_LINES_INVALID: aksesori yang sama tidak boleh dua baris';end if;
    v_transfer:=erp.bc_post_transfer_v1(p_request,v_from,v_zone,v_at,
      (select jsonb_agg(jsonb_build_object('material_id',x->>'material_id','qty',x->>'qty') order by (x->>'line_number')::int) from jsonb_array_elements(v_lines) x),
      btrim(p_payload->>'reason'));
  elsif p_payload ? 'from_location_id' then raise exception 'BC_SOURCE_KIND: lokasi asal hanya untuk sisa pos';
  end if;
  for v_x in select value from jsonb_array_elements(v_lines) order by (value->>'line_number')::int loop
    if v_x ? 'outstanding_id' then
      select * into v_out from erp.bc_outstanding_returns_v1 where id=erp.bc_uuid_v1(v_x,'outstanding_id',true) for update;
      if v_out.id is null or v_out.status<>'OPEN' or v_out.owner_kind<>'COMPANY' then
        raise exception 'BC_OUTSTANDING_INVALID: barang yang ditunggu tidak ditemukan atau bukan milik perusahaan';end if;
      if v_out.material_id is distinct from (v_x->>'material_id')::uuid then raise exception 'BC_OUTSTANDING_INVALID: aksesori berbeda dari yang ditunggu';end if;
      select coalesce(sum(l.qty_received),0) into v_used from erp.bc_return_lots_v1 l left join erp.bc_documents_v1 d on d.id=l.document_id
        where l.outstanding_id=v_out.id and d.status='POSTED';
      if (v_x->>'qty')::numeric>v_out.qty_expected-v_used then
        raise exception 'BC_RETURN_EXCEEDS_SOURCE: sisa yang ditunggu % , diterima %',(v_out.qty_expected-v_used)::numeric(18,6),v_x->>'qty';end if;
    end if;
    insert into erp.bc_return_lots_v1(document_id,line_number,source_kind,owner_kind,value_mode,material_id,location_id,qty_received,received_at,
      outstanding_id,reference)
    values(p_request,(v_x->>'line_number')::int,v_kind,'COMPANY',case when v_kind='SERVICE_LEFTOVER' then 'LEDGER' else 'PENDING' end,
      (v_x->>'material_id')::uuid,v_zone,(v_x->>'qty')::numeric,v_at,nullif(v_x->>'outstanding_id','')::uuid,v_ref)
    returning id into v_lot;
    v_lots:=v_lots||jsonb_build_array(v_lot);
  end loop;
  return jsonb_build_object('lot_ids',v_lots,'transfer_id',v_transfer);
end;$function$;

-- ---------------------------------------------------------------- INSPECT (M:5.6, 6.2; ACC-C01/C02/C11)
-- Partial, by several inspectors, never above what is still waiting. A ledger lot moves the inspected quantity from the
-- inspection area to the chosen warehouse (usable) and damaged area (damaged); a custody lot only changes its condition.
CREATE OR REPLACE FUNCTION erp.bc_inspect_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.bc_return_lots_v1%rowtype;s jsonb;v_u numeric:=0;v_d numeric:=0;v_at timestamptz;v_inspector text;v_usable_to uuid;v_damaged_to uuid;
  v_event uuid;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['lot_id','inspected_at','inspector','reason'],
    array['lot_id','inspected_at','inspector','qty_usable','qty_damaged','usable_location_id','damaged_location_id','reason','responsible','reference'],
    'inspection payload');
  l:=erp.bc_lock_lot_v1(erp.bc_uuid_v1(p_payload,'lot_id',true));
  v_at:=erp.bc_parse_at_v1(p_payload->>'inspected_at','inspected_at');
  if v_at<l.received_at then raise exception 'BC_DATE_BEFORE_SOURCE: pemeriksaan tidak boleh sebelum barang diterima';end if;
  v_inspector:=erp.bc_text_v1(p_payload,'inspector',true,120);
  if p_payload ? 'qty_usable' then v_u:=erp.bc_parse_qty_v1(l.material_id,p_payload->'qty_usable','qty_usable');end if;
  if p_payload ? 'qty_damaged' then v_d:=erp.bc_parse_qty_v1(l.material_id,p_payload->'qty_damaged','qty_damaged');end if;
  if v_u+v_d<=0 then raise exception 'BC_QTY_INVALID: isi jumlah layak dan/atau rusak';end if;
  s:=erp.bc_lot_state_v1(l.id);
  if v_u+v_d>(s->>'waiting')::numeric then
    raise exception 'BC_INSPECT_EXCEEDS_WAITING: yang belum diperiksa % , diperiksa %',((s->>'waiting')::numeric)::numeric(18,6),v_u+v_d;end if;
  if l.value_mode='LEDGER' then
    if v_u>0 then v_usable_to:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'usable_location_id',true),array['MAIN'],'gudang untuk barang layak');
    elsif p_payload ? 'usable_location_id' then raise exception 'BC_LOCATION_INVALID: tidak ada barang layak';end if;
    if v_d>0 then v_damaged_to:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'damaged_location_id',true),array['DAMAGED'],'area rusak');
    elsif p_payload ? 'damaged_location_id' then raise exception 'BC_LOCATION_INVALID: tidak ada barang rusak';end if;
  elsif (p_payload ? 'usable_location_id') or (p_payload ? 'damaged_location_id') then
    raise exception 'BC_LOCATION_INVALID: barang titipan/nilai pending tidak masuk stok saat diperiksa';
  end if;
  perform erp.bc_new_document_v1(p_request,'INSPECT',v_at,p_payload);
  insert into erp.bc_lot_events_v1(document_id,lot_id,event_kind,qty_usable,qty_damaged,inspector,event_at)
  values(p_request,l.id,'INSPECT',v_u,v_d,v_inspector,v_at) returning id into v_event;
  if v_u>0 and l.value_mode='LEDGER' then
    perform erp.bc_post_transfer_v1(p_request,l.location_id,v_usable_to,v_at,jsonb_build_array(jsonb_build_object('material_id',l.material_id,'qty',v_u::text)),btrim(p_payload->>'reason'));
  end if;
  if v_d>0 and l.value_mode='LEDGER' then
    perform erp.bc_post_transfer_v1(p_request,l.location_id,v_damaged_to,v_at,jsonb_build_array(jsonb_build_object('material_id',l.material_id,'qty',v_d::text)),btrim(p_payload->>'reason'));
  end if;
  return jsonb_build_object('event_id',v_event,'lot',erp.bc_lot_state_v1(l.id));
end;$function$;

-- ---------------------------------------------------------------- VALUE_CUSTODY (ACC-DEC03; ACC-C05, C12, ALL-C03)
-- Company custody with value pending enters the ledger only with the owner's recovery-value policy: a native inbound
-- adjustment at the approved unit value (capped by the moving average when the policy says so) against the policy
-- account, into the warehouse (usable) or the damaged area (damaged). Never a zero-value stock-in.
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
  return jsonb_build_object('event_id',v_event,'adjustment_id',v_adj,'value',round(v_qty*v_unit,2)::text,'lot',erp.bc_lot_state_v1(l.id));
end;$function$;

-- ---------------------------------------------------------------- CLOSE_CUSTODY: back to its owner, or discarded
-- A mandor-owned return goes back to the mandor (any condition); company custody without value may be discarded by
-- owner/admin (no ledger effect: it never had value there). A ledger lot is closed by inspection, never here.
CREATE OR REPLACE FUNCTION erp.bc_close_custody_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.bc_return_lots_v1%rowtype;s jsonb;v_kind text:=upper(coalesce(p_payload->>'disposition',''));v_cond text:=upper(coalesce(p_payload->>'condition',''));
  v_qty numeric;v_at timestamptz;v_event uuid;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['lot_id','disposition','condition','qty','physical_at','reason'],
    array['lot_id','disposition','condition','qty','physical_at','reason','responsible','reference'],'custody close payload');
  l:=erp.bc_lock_lot_v1(erp.bc_uuid_v1(p_payload,'lot_id',true));
  if l.value_mode='LEDGER' then raise exception 'BC_LEDGER_LOT: stok perusahaan diselesaikan lewat pemeriksaan';end if;
  if v_kind='RETURN_TO_OWNER' then
    if l.owner_kind<>'MANDOR' then raise exception 'BC_DISPOSITION_INVALID: hanya barang milik mandor yang dikembalikan ke pemiliknya';end if;
  elsif v_kind='DISCARD' then
    if l.owner_kind<>'COMPANY' then raise exception 'BC_DISPOSITION_INVALID: barang milik mandor tidak dapat dibuang perusahaan';end if;
    begin perform erp.require_owner_admin();
    exception when others then raise exception 'BC_APPROVAL_REQUIRED: pembuangan barang titipan memerlukan owner/admin';end;
  else raise exception 'BC_DISPOSITION_INVALID: RETURN_TO_OWNER atau DISCARD';end if;
  if v_cond not in('WAITING','USABLE','DAMAGED') then raise exception 'BC_CONDITION_INVALID: WAITING, USABLE atau DAMAGED';end if;
  if v_kind='DISCARD' and v_cond='WAITING' then raise exception 'BC_CONDITION_INVALID: periksa dahulu sebelum dibuang';end if;
  v_qty:=erp.bc_parse_qty_v1(l.material_id,p_payload->'qty','qty');
  s:=erp.bc_lot_state_v1(l.id);
  if v_qty>(s->>lower(v_cond))::numeric then
    raise exception 'BC_QTY_EXCEEDS_BUCKET: % yang tersedia % , diminta %',v_cond,((s->>lower(v_cond))::numeric)::numeric(18,6),v_qty;end if;
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  if v_at<l.received_at then raise exception 'BC_DATE_BEFORE_SOURCE: tidak boleh sebelum barang diterima';end if;
  perform erp.bc_new_document_v1(p_request,'CLOSE_CUSTODY',v_at,p_payload);
  insert into erp.bc_lot_events_v1(document_id,lot_id,event_kind,condition,qty,event_at)
  values(p_request,l.id,v_kind,v_cond,v_qty,v_at) returning id into v_event;
  return jsonb_build_object('event_id',v_event,'lot',erp.bc_lot_state_v1(l.id));
end;$function$;

-- ---------------------------------------------------------------- DISPOSE_STOCK: valued damaged stock written off
CREATE OR REPLACE FUNCTION erp.bc_dispose_stock_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_location uuid;v_at timestamptz;v_lines jsonb;v_adj uuid;v_value numeric;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['location_id','physical_at','items','reason'],
    array['location_id','physical_at','items','reason','responsible','reference'],'disposal payload');
  v_location:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'location_id',true),array['DAMAGED'],'area rusak');
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  v_lines:=erp.bc_lines_v1(p_payload);
  perform erp.bc_new_document_v1(p_request,'DISPOSE_STOCK',v_at,p_payload,jsonb_build_object('ACC_DEC07',erp.bc_policy_version_v1('ACC_DEC07')));
  v_adj:=erp.bc_post_adjustment_v1(p_request,v_location,v_at,'DAMAGE',
    (select jsonb_agg(jsonb_build_object('material_id',x->>'material_id','qty_signed',(-(x->>'qty')::numeric)::text) order by (x->>'line_number')::int) from jsonb_array_elements(v_lines) x),
    btrim(p_payload->>'reason'),'DAMAGE_DISPOSAL',erp.bc_adjustment_account_v1(null,'OTHER_EXPENSE'));
  v_value:=-erp.bc_adjustment_value_v1(v_adj);
  perform erp.bc_require_value_approval_v1(v_value);
  return jsonb_build_object('adjustment_id',v_adj,'cost',v_value::numeric(20,2)::text);
end;$function$;

-- ---------------------------------------------------------------- customer garment custody (ACC-C10)
CREATE OR REPLACE FUNCTION erp.bc_customer_garment_v1(p_action text,p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare c erp.bc_customer_custody_v1%rowtype;v_at timestamptz;v_customer uuid;v_product uuid;v_qty numeric;
begin
  if p_action='CUSTOMER_GARMENT_IN' then
    perform erp._cp3_assert_closed_json_object(p_payload,array['customer_id','description','qty','physical_at','reason'],
      array['customer_id','product_id','description','qty','physical_at','reason','responsible','reference'],'customer garment payload');
    v_customer:=erp.bc_uuid_v1(p_payload,'customer_id',true);
    if not exists(select 1 from erp.customers where id=v_customer and is_active) then raise exception 'BC_CUSTOMER_INVALID: pilih pelanggan aktif';end if;
    v_product:=erp.bc_uuid_v1(p_payload,'product_id',false);
    if v_product is not null and not exists(select 1 from erp.products where id=v_product) then raise exception 'BC_PRODUCT_INVALID: produk tidak ditemukan';end if;
    if jsonb_typeof(p_payload->'qty') is distinct from 'string' or p_payload->>'qty'!~'^[1-9][0-9]{0,8}$' then
      raise exception 'BC_QTY_INVALID: jumlah titipan harus PCS utuh positif';end if;
    v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
    perform erp.bc_new_document_v1(p_request,p_action,v_at,p_payload);
    insert into erp.bc_customer_custody_v1(id,in_document_id,customer_id,product_id,description,qty,received_at)
    values(p_request,p_request,v_customer,v_product,erp.bc_text_v1(p_payload,'description',true,200),(p_payload->>'qty')::numeric,v_at);
    return jsonb_build_object('custody_id',p_request);
  end if;
  perform erp._cp3_assert_closed_json_object(p_payload,array['custody_id','physical_at','reason'],
    array['custody_id','physical_at','reason','responsible','reference'],'customer garment payload');
  select * into c from erp.bc_customer_custody_v1 where id=erp.bc_uuid_v1(p_payload,'custody_id',true) for update;
  if c.id is null or (c.batch_id is null and (select status from erp.bc_documents_v1 where id=c.in_document_id)<>'POSTED') then
    raise exception 'BC_CUSTODY_INVALID: titipan pelanggan tidak ditemukan';end if;
  if c.out_document_id is not null and (select status from erp.bc_documents_v1 where id=c.out_document_id)='POSTED' then
    raise exception 'BC_CUSTODY_CLOSED: titipan sudah dikembalikan ke pelanggan';end if;
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  if v_at<c.received_at then raise exception 'BC_DATE_BEFORE_SOURCE: pengembalian tidak boleh sebelum titipan diterima';end if;
  perform erp.bc_new_document_v1(p_request,p_action,v_at,p_payload);
  update erp.bc_customer_custody_v1 set out_document_id=p_request where id=c.id;
  return jsonb_build_object('custody_id',c.id);
end;$function$;

-- ---------------------------------------------------------------- COUNT_POST / RESOLVE_VARIANCE (ACC-B06)
CREATE OR REPLACE FUNCTION erp.bc_count_post_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_location uuid;v_at timestamptz;v_x jsonb;v_book numeric;v_counted numeric;v_ids jsonb:='[]'::jsonb;v_id uuid;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['location_id','physical_at','items','reason'],
    array['location_id','physical_at','items','reason','responsible','reference'],'count payload');
  v_location:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'location_id',true),array['SERVICE_POST'],'pos servis');
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  if jsonb_typeof(p_payload->'items') is distinct from 'array' or jsonb_array_length(p_payload->'items') not between 1 and 100 then
    raise exception 'BC_LINES_INVALID: isi 1 sampai 100 baris hitung';end if;
  perform erp.bc_new_document_v1(p_request,'COUNT_POST',v_at,p_payload);
  for v_x in select value from jsonb_array_elements(p_payload->'items') loop
    perform erp._cp3_assert_closed_json_object(v_x,array['material_id','counted_qty'],array['material_id','counted_qty'],'count line');
    perform erp.bc_accessory_v1(erp.bc_uuid_v1(v_x,'material_id',true));
    if jsonb_typeof(v_x->'counted_qty') is distinct from 'string' or v_x->>'counted_qty'!~'^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$' then
      raise exception 'BC_QTY_INVALID: hasil hitung wajib angka teks nol atau lebih';end if;
    v_counted:=(v_x->>'counted_qty')::numeric;
    if exists(select 1 from erp.materials m join erp.uom_definitions u on u.unit_code=m.unit_code where m.id=(v_x->>'material_id')::uuid
        and u.dimension='COUNT') and v_counted<>trunc(v_counted) then raise exception 'BC_QTY_INVALID: hasil hitung harus PCS utuh';end if;
    select coalesce(sum(qty_signed),0) into v_book from erp.material_stock_movements
      where material_id=(v_x->>'material_id')::uuid and location_id=v_location and physical_at<=v_at;
    insert into erp.bc_count_variances_v1(document_id,material_id,location_id,book_qty,counted_qty,variance,counted_at)
    values(p_request,(v_x->>'material_id')::uuid,v_location,v_book,v_counted,v_counted-v_book,v_at) returning id into v_id;
    v_ids:=v_ids||jsonb_build_array(jsonb_build_object('variance_id',v_id,'book',v_book::text,'counted',v_counted::text,'variance',(v_counted-v_book)::text));
  end loop;
  return jsonb_build_object('variances',v_ids);
end;$function$;

-- A negative variance becomes a counted LOSS only by an explicit decision (native LOSS adjustment, valued, ACC-DEC07);
-- DISMISS keeps the book (a recount). A variance is never turned into service usage.
CREATE OR REPLACE FUNCTION erp.bc_resolve_variance_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v erp.bc_count_variances_v1%rowtype;v_kind text:=upper(coalesce(p_payload->>'resolution',''));v_at timestamptz;v_adj uuid;v_value numeric;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['variance_id','resolution','physical_at','reason'],
    array['variance_id','resolution','physical_at','reason','responsible','reference'],'variance payload');
  select * into v from erp.bc_count_variances_v1 where id=erp.bc_uuid_v1(p_payload,'variance_id',true) for update;
  if v.id is null or (select status from erp.bc_documents_v1 where id=v.document_id)<>'POSTED' then raise exception 'BC_VARIANCE_INVALID: selisih tidak ditemukan';end if;
  if v.resolution_document_id is not null and (select status from erp.bc_documents_v1 where id=v.resolution_document_id)='POSTED' then
    raise exception 'BC_VARIANCE_RESOLVED: selisih ini sudah diselesaikan';end if;
  if v_kind not in('LOSS','DISMISS') then raise exception 'BC_VARIANCE_INVALID: LOSS atau DISMISS';end if;
  if v_kind='LOSS' and v.variance>=0 then raise exception 'BC_VARIANCE_INVALID: hanya selisih kurang yang dapat dicatat hilang';end if;
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  if v_at<v.counted_at then raise exception 'BC_DATE_BEFORE_SOURCE: penyelesaian tidak boleh sebelum hitung';end if;
  perform erp.bc_location_v1(v.location_id,array['SERVICE_POST'],'pos servis');
  perform erp.bc_new_document_v1(p_request,'RESOLVE_VARIANCE',v_at,p_payload,jsonb_build_object('ACC_DEC07',erp.bc_policy_version_v1('ACC_DEC07')));
  update erp.bc_count_variances_v1 set resolution_document_id=p_request where id=v.id;
  if v_kind='LOSS' then
    v_adj:=erp.bc_post_adjustment_v1(p_request,v.location_id,v_at,'LOSS',jsonb_build_array(jsonb_build_object('material_id',v.material_id,
      'qty_signed',v.variance::text)),btrim(p_payload->>'reason'),'COUNT_LOSS',erp.bc_adjustment_account_v1(null,'OTHER_EXPENSE'));
    v_value:=-erp.bc_adjustment_value_v1(v_adj);
    perform erp.bc_require_value_approval_v1(v_value);
  end if;
  return jsonb_build_object('variance_id',v.id,'resolution',v_kind,'adjustment_id',v_adj,'cost',coalesce(v_value,0)::numeric(20,2)::text);
end;$function$;
-- ================================================================ BC mandor note returns, credits, rounding, free lines
-- M:4762/M:3912 (paid mandor note return: receipt linked to the note, credit only for a proven right, settlement checked,
-- capped by the source quantity/amount, never the latest master price), M:4458 ACC-DEC05 (credit, carry or refund after a
-- full/partial settlement: keep the original settlement, block unsupported financial finalization), M:5005 (cumulative
-- credit never above the original amount; a full return reverses it exactly), M:4459 ACC-DEC06 (whole-rupiah rounding only
-- as a separate line), M:4462 ERP-DEC02 (Special free categories: explicit, never inferred from a name or a demo seed).

-- ALL-C02: the lines of an old mandor accessory note behind an imported CONTRACTOR_RECEIVABLE document.
create table erp.bc_opening_note_lines_v1(
  id uuid primary key,
  batch_id uuid not null references erp.migration_batches(id),
  source_row_id uuid not null unique,
  balance_id uuid not null references erp.opening_subledger_balances(id),
  document_number text not null,
  line_number integer not null check(line_number between 1 and 999),
  material_id uuid not null references erp.materials(id),
  qty numeric(18,6) not null check(qty>0),
  line_amount numeric(18,2) not null check(line_amount>=0),
  unique(balance_id,line_number)
);
comment on table erp.bc_opening_note_lines_v1 is 'BC (ALL-C02): the lines (accessory, quantity, source amount) of an old mandor note whose unpaid residual was imported as a CONTRACTOR_RECEIVABLE opening document. A return after cutover is capped by the line quantity and credited at the line''s own amount, never at a current price; the historical settlement stays provenance.';

create table erp.bc_note_roundings_v1(
  id uuid primary key references erp.bc_documents_v1(id),
  issue_id uuid not null references erp.contractor_material_issues(id),
  item_id uuid not null references erp.contractor_material_issue_items(id),
  amount numeric(18,2) not null check(amount<>0 and abs(amount)<1),
  journal_entry_id uuid not null references erp.journal_entries(id)
);

create table erp.bc_free_issue_lines_v1(
  issue_id uuid not null references erp.contractor_material_issues(id),
  material_id uuid not null references erp.materials(id),
  category_id uuid not null references erp.accessory_categories(id),
  policy_version bigint not null,
  primary key(issue_id,material_id)
);
comment on table erp.bc_free_issue_lines_v1 is 'BC (ERP-DEC02): a mandor note line issued free (price 0) because its category is on the owner''s Special free list for a contractor that is Special at the physical time; the policy version is kept. Checked again at posting.';

alter table erp.payroll_reimbursements add column bc_credit_event_id uuid references erp.bc_lot_events_v1(id);
alter table erp.payroll_reimbursements drop constraint payroll_reimbursements_source_type_check;
alter table erp.payroll_reimbursements add constraint payroll_reimbursements_source_type_check
  check(source_type::text=any(array['MANUAL','ACCESSORY_BOM','OPENING_PAYABLE','OPENING_CARRY','BC_RETURN_CARRY']));
alter table erp.payroll_reimbursements add constraint payroll_reimbursements_bc_carry_check
  check((source_type::text='BC_RETURN_CARRY')=(bc_credit_event_id is not null));

alter table erp.bb_opening_credits_v1 drop constraint bb_opening_credits_v1_credit_kind_check;
alter table erp.bb_opening_credits_v1 add constraint bb_opening_credits_v1_credit_kind_check
  check(credit_kind in('CUSTOMER_ALLOWANCE','SUPPLIER_ALLOWANCE','VENDOR_ALLOWANCE','CUSTOMER_CREDIT_APPLY','ACCESSORY_NOTE_RETURN'));

do $rls$
declare t text;
begin
  foreach t in array array['bc_opening_note_lines_v1','bc_note_roundings_v1','bc_free_issue_lines_v1'] loop
    execute format('alter table erp.%I enable row level security',t);
    execute format('revoke all on erp.%I from public,anon,authenticated,service_role',t);
  end loop;
end $rls$;

-- ---------------------------------------------------------------- amounts
-- The item's share of the note's posted receivable: the journal rounds the document total once, so the cents go to the
-- items by cumulative rounding in item id order; the shares add up to the posted amount exactly.
CREATE OR REPLACE FUNCTION erp.bc_note_item_share_v1(p_item uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  with i as(select issue_id from erp.contractor_material_issue_items where id=p_item),
  c as(select x.id,sum(coalesce(x.total_receivable,0)) over(order by x.id) cum from erp.contractor_material_issue_items x join i on i.issue_id=x.issue_id)
  select round(c.cum,2)-round(c.cum-coalesce((select total_receivable from erp.contractor_material_issue_items where id=p_item),0),2) from c where c.id=p_item
$function$;

-- Credits (their unpaid part) and roundings that change what the mandor still owes on one note line.
CREATE OR REPLACE FUNCTION erp.bc_note_item_adjustment_v1(p_item uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce((select sum(e.amount_unpaid) from erp.bc_lot_events_v1 e join erp.bc_documents_v1 d on d.id=e.document_id
      join erp.bc_return_lots_v1 l on l.id=e.lot_id where l.note_item_id=p_item and e.event_kind='CREDIT' and d.status='POSTED'),0)
   -coalesce((select sum(r.amount) from erp.bc_note_roundings_v1 r join erp.bc_documents_v1 d on d.id=r.id where r.item_id=p_item and d.status='POSTED'),0)
$function$;

-- What payroll may still collect on the line: the original receivable less credited unpaid parts plus roundings.
-- Without BC activity it is exactly total_receivable (the unchanged rule).
CREATE OR REPLACE FUNCTION erp.bc_note_item_collectible_v1(p_item uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(total_receivable,0)-erp.bc_note_item_adjustment_v1(p_item) from erp.contractor_material_issue_items where id=p_item
$function$;

CREATE OR REPLACE FUNCTION erp.bc_note_item_allocated_v1(p_item uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(sum(pd.amount),0) from erp.payroll_deductions pd join erp.payroll_settlements ps on ps.id=pd.payroll_id
  where pd.contractor_issue_item_id=p_item and pd.deduction_type='MATERIAL_KASBON' and ps.status<>'REVERSED'
$function$;

-- The CONTRACTOR_ISSUE movement of the note line a credited return belongs to (its cost is the return's cost).
CREATE OR REPLACE FUNCTION erp.bc_note_return_issue_movement_v1(p_event uuid)
 RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select m.id from erp.bc_lot_events_v1 e join erp.bc_return_lots_v1 l on l.id=e.lot_id
  join erp.material_stock_movements m on m.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and m.source_id=l.note_item_id
    and m.movement_type='CONTRACTOR_ISSUE' and m.reversal_of_id is null
  where e.id=p_event order by m.physical_at desc,m.system_created_at desc,m.id desc limit 1
$function$;

CREATE OR REPLACE FUNCTION erp.bc_carry_remaining_v1(p_event uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select e.amount_carry-coalesce((select sum(r.amount) from erp.payroll_reimbursements r join erp.payroll_settlements p on p.id=r.payroll_id
    where r.bc_credit_event_id=e.id and r.source_type='BC_RETURN_CARRY' and p.status<>'REVERSED'),0)
  from erp.bc_lot_events_v1 e join erp.bc_documents_v1 d on d.id=e.document_id where e.id=p_event and d.status='POSTED'
$function$;

-- ---------------------------------------------------------------- CREDIT_NOTE_RETURN (ACC-DEC05; ACC-A08, C09, D04; ALL-C02)
-- Credits returned quantity of one mandor lot already inspected in a condition the policy credits. The amount is the
-- cumulative share of the source line (native note: the item's share of the posted document; opening note: the line
-- amount), never a current price. The unpaid part reduces what payroll may still collect; the part already allocated or
-- paid follows the policy (refused, carried to the next payroll as a payable, or refunded in cash). A native note's
-- credited goods return to company stock at the note line's issue cost (inventory back, COGS back); an opening note's
-- credited goods become company custody with value pending (ACC-DEC03), because their old cost is not in the ledger.
CREATE OR REPLACE FUNCTION erp.bc_credit_note_return_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.bc_return_lots_v1%rowtype;s jsonb;v_policy jsonb;v_cond text:=upper(coalesce(p_payload->>'condition',''));v_qty numeric;
  v_at timestamptz;v_to uuid;v_event uuid;v_item erp.contractor_material_issue_items%rowtype;v_issue erp.contractor_material_issues%rowtype;
  n record;b erp.opening_subledger_balances%rowtype;v_before numeric;v_base numeric;v_line_qty numeric;v_amount numeric;v_unpaid numeric;
  v_rest numeric;v_carry numeric:=0;v_refund numeric:=0;v_cash uuid;v_cash_coa uuid;v_lines jsonb;v_journal uuid;v_move uuid;v_value numeric;
  v_day date;v_child uuid;v_settlement uuid;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.contractor_accessory.reverse');
  perform erp._cp3_assert_closed_json_object(p_payload,array['lot_id','condition','qty','physical_at','reason'],
    array['lot_id','condition','qty','physical_at','location_id','cash_account_id','reason','responsible','reference'],'credit payload');
  v_policy:=erp.bc_require_policy_v1('ACC_DEC05','kredit retur nota mandor');
  l:=erp.bc_lock_lot_v1(erp.bc_uuid_v1(p_payload,'lot_id',true));
  if l.owner_kind<>'MANDOR' then raise exception 'BC_NOT_NOTE_RETURN: kredit hanya untuk retur nota mandor';end if;
  if v_cond not in('USABLE','DAMAGED') then raise exception 'BC_CONDITION_INVALID: kredit hanya untuk barang yang sudah diperiksa';end if;
  if not (v_policy->'credit_conditions') ? v_cond then
    raise exception 'BC_CONDITION_NOT_CREDITED: kebijakan ACC-DEC05 tidak mengkredit barang %',case v_cond when 'USABLE' then 'layak' else 'rusak' end;end if;
  v_qty:=erp.bc_parse_qty_v1(l.material_id,p_payload->'qty','qty');
  s:=erp.bc_lot_state_v1(l.id);
  if v_qty>(s->>lower(v_cond))::numeric then
    raise exception 'BC_QTY_EXCEEDS_BUCKET: % yang tersedia % , diminta %',v_cond,((s->>lower(v_cond))::numeric)::numeric(18,6),v_qty;end if;
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  if v_at<l.received_at then raise exception 'BC_DATE_BEFORE_SOURCE: kredit tidak boleh sebelum barang diterima';end if;
  v_day:=erp._cp3_business_date(v_at);
  -- Cumulative credited quantity of the source line (every lot of it), under the source lock shared with payroll.
  if l.note_item_id is not null then
    select * into v_item from erp.contractor_material_issue_items where id=l.note_item_id;
    perform pg_advisory_xact_lock(hashtextextended('BCNOTE|'||v_item.id::text,0));
    perform pg_advisory_xact_lock(hashtextextended('PAYKASBON|'||v_item.id::text,0));
    select * into v_issue from erp.contractor_material_issues where id=v_item.issue_id for update;
    if v_issue.status<>'POSTED' then raise exception 'BC_NOTE_NOT_POSTED: nota asal tidak lagi disahkan';end if;
    v_base:=erp.bc_note_item_share_v1(v_item.id);v_line_qty:=v_item.qty;
    select coalesce(sum(e.qty),0) into v_before from erp.bc_lot_events_v1 e join erp.bc_documents_v1 d on d.id=e.document_id
      join erp.bc_return_lots_v1 x on x.id=e.lot_id where x.note_item_id=v_item.id and e.event_kind='CREDIT' and d.status='POSTED';
  else
    select * into n from erp.bc_opening_note_lines_v1 where id=l.opening_note_line_id;
    perform pg_advisory_xact_lock(hashtextextended('BCNOTE|'||n.id::text,0));
    select * into b from erp.opening_subledger_balances where id=n.balance_id for update;
    v_base:=n.line_amount;v_line_qty:=n.qty;
    select coalesce(sum(e.qty),0) into v_before from erp.bc_lot_events_v1 e join erp.bc_documents_v1 d on d.id=e.document_id
      join erp.bc_return_lots_v1 x on x.id=e.lot_id where x.opening_note_line_id=n.id and e.event_kind='CREDIT' and d.status='POSTED';
  end if;
  v_amount:=round(v_base*(v_before+v_qty)/v_line_qty,2)-round(v_base*v_before/v_line_qty,2);
  -- The part the mandor still owes and payroll has not taken: that part is credited against the receivable.
  if l.note_item_id is not null then
    v_unpaid:=greatest(least(v_amount,round(erp.bc_note_item_collectible_v1(v_item.id)-erp.bc_note_item_allocated_v1(v_item.id),2)),0);
  else
    v_unpaid:=greatest(least(v_amount,b.original_amount-b.settled_amount-erp.bb_opening_balance_reserved_v1(b.id)),0);
  end if;
  v_rest:=v_amount-v_unpaid;
  if v_rest>0 then
    if v_policy->>'mode'='CREDIT_UNPAID_ONLY' then
      raise exception 'BC_DEC05_PAID_PORTION: % dari kredit % sudah dipotong/dibayar; kebijakan ACC-DEC05 hanya mengkredit sisa yang belum dibayar',v_rest,v_amount;
    elsif v_policy->>'mode'='CREDIT_THEN_CARRY' then v_carry:=v_rest;
    else
      v_refund:=v_rest;
      select id,coa_account_id into v_cash,v_cash_coa from erp.cash_accounts where id=erp.bc_uuid_v1(p_payload,'cash_account_id',false) and is_active;
      if v_cash is null then raise exception 'BC_CASH_ACCOUNT_REQUIRED: pilih rekening kas/bank aktif untuk pengembalian uang';end if;
    end if;
  end if;
  if v_refund=0 and p_payload ? 'cash_account_id' then raise exception 'BC_CASH_ACCOUNT_REQUIRED: rekening kas hanya untuk pengembalian uang';end if;
  perform erp.bc_new_document_v1(p_request,'CREDIT_NOTE_RETURN',v_at,p_payload,jsonb_build_object('ACC_DEC05',erp.bc_policy_version_v1('ACC_DEC05')));
  if l.note_item_id is not null then
    v_to:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'location_id',true),case when v_cond='USABLE' then array['MAIN'] else array['DAMAGED'] end,
      case when v_cond='USABLE' then 'gudang untuk barang layak' else 'area rusak' end);
  elsif p_payload ? 'location_id' then raise exception 'BC_LOCATION_INVALID: barang nota saldo awal menjadi titipan bernilai pending, bukan stok';
  end if;
  insert into erp.bc_lot_events_v1(document_id,lot_id,event_kind,condition,qty,event_at,target_location_id,amount,amount_unpaid,amount_carry,amount_refund,cash_account_id)
  values(p_request,l.id,'CREDIT',v_cond,v_qty,v_at,v_to,v_amount,v_unpaid,v_carry,v_refund,v_cash) returning id into v_event;
  if l.note_item_id is not null then
    -- Money: revenue back, receivable down by the unpaid part, the rest carried or refunded.
    if v_amount>0 then
      v_lines:=jsonb_build_array(jsonb_build_object('mapping_key','MATERIAL_RECOVERY','debit',v_amount,'credit',0,'contractor_id',v_issue.contractor_id,'po_id',v_issue.po_id));
      if v_unpaid>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',0,'credit',v_unpaid,'contractor_id',v_issue.contractor_id,'po_id',v_issue.po_id));end if;
      if v_carry>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',v_carry,'contractor_id',v_issue.contractor_id,'po_id',v_issue.po_id));end if;
      if v_refund>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('account_id',v_cash_coa,'debit',0,'credit',v_refund,'contractor_id',v_issue.contractor_id,'po_id',v_issue.po_id));end if;
      v_journal:=erp.post_journal('BC_NOTE_RETURN_CREDIT',v_event,v_day,'Kredit retur nota mandor '||v_issue.issue_number,v_lines);
      perform erp.bc_link_v1(p_request,'JOURNAL',v_journal);
    end if;
    -- Goods: back to company stock at the issue cost of this note line.
    insert into erp.material_stock_movements(material_id,location_id,movement_type,qty_signed,source_type,source_id,physical_at,created_by,note)
    values(l.material_id,v_to,'ADJUSTMENT',v_qty,'BC_NOTE_RETURN_CREDIT',v_event,v_at,erp.current_app_user_id(),'Retur nota mandor dikreditkan')
    returning id into v_move;
    perform erp.bc_link_v1(p_request,'MOVEMENT',v_move);
    perform erp.recalculate_material_cost(l.material_id);
    select round(qty_signed*coalesce(original_unit_cost_snapshot,unit_cost_snapshot),2) into v_value from erp.material_stock_movements where id=v_move;
    if v_value>0 then
      v_journal:=erp.post_journal('BC_NOTE_RETURN_STOCK',v_event,v_day,'Barang retur nota mandor kembali ke stok',jsonb_build_array(
        jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',v_value,'credit',0,'contractor_id',v_issue.contractor_id,'po_id',v_issue.po_id),
        jsonb_build_object('mapping_key','ACCESSORY_RECOVERY_COGS','debit',0,'credit',v_value,'contractor_id',v_issue.contractor_id,'po_id',v_issue.po_id)));
      perform erp.bc_link_v1(p_request,'JOURNAL',v_journal);
    end if;
    perform erp.refresh_contractor_issue_payroll_status(v_item.id);
  else
    if v_unpaid>0 then
      v_settlement:=gen_random_uuid();
      insert into erp.opening_subledger_settlements(id,balance_id,settlement_number,physical_at,amount,cash_account_id,status,notes,created_by)
      values(v_settlement,b.id,'OSS-'||upper(substr(replace(v_settlement::text,'-',''),1,16)),v_at,v_unpaid,null,'DRAFT',btrim(p_payload->>'reason'),erp.current_app_user_id());
      insert into erp.bb_opening_credits_v1(settlement_id,credit_kind,credit_note_number,reason)
      values(v_settlement,'ACCESSORY_NOTE_RETURN','BCA-'||upper(substr(replace(p_request::text,'-',''),1,16)),btrim(p_payload->>'reason'));
      perform erp.post_opening_subledger_settlement(v_settlement);
      perform erp.bc_link_v1(p_request,'SETTLEMENT',v_settlement);
    end if;
    if v_carry+v_refund>0 then
      v_lines:=jsonb_build_array(jsonb_build_object('mapping_key','MATERIAL_RECOVERY','debit',v_carry+v_refund,'credit',0,'contractor_id',b.contractor_id));
      if v_carry>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',v_carry,'contractor_id',b.contractor_id));end if;
      if v_refund>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('account_id',v_cash_coa,'debit',0,'credit',v_refund,'contractor_id',b.contractor_id));end if;
      v_journal:=erp.post_journal('BC_NOTE_RETURN_CREDIT',v_event,v_day,'Kredit retur nota mandor saldo awal '||n.document_number,v_lines);
      perform erp.bc_link_v1(p_request,'JOURNAL',v_journal);
    end if;
    -- The goods become company custody with value pending (their old cost is not in the ledger).
    insert into erp.bc_return_lots_v1(document_id,source_kind,owner_kind,value_mode,material_id,location_id,qty_received,init_usable,init_damaged,
      received_at,contractor_id,parent_lot_id,parent_event_id,reference)
    values(p_request,'NOTE_RETURN_CREDITED','COMPANY','PENDING',l.material_id,l.location_id,v_qty,case when v_cond='USABLE' then v_qty else 0 end,
      case when v_cond='DAMAGED' then v_qty else 0 end,v_at,l.contractor_id,l.id,v_event,n.document_number) returning id into v_child;
  end if;
  return jsonb_build_object('event_id',v_event,'amount',v_amount::text,'unpaid',v_unpaid::text,'carry',v_carry::text,'refund',v_refund::text,
    'custody_lot_id',v_child,'lot',erp.bc_lot_state_v1(l.id));
end;$function$;

-- The journal lines of an opening note-return credit (a non-cash settlement of the imported CONTRACTOR_RECEIVABLE).
CREATE OR REPLACE FUNCTION erp.bc_opening_note_credit_lines_v1(p_settlement_id uuid)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare s erp.opening_subledger_settlements%rowtype;b erp.opening_subledger_balances%rowtype;
begin
  select * into s from erp.opening_subledger_settlements where id=p_settlement_id;
  select * into b from erp.opening_subledger_balances where id=s.balance_id;
  if b.party_type<>'CONTRACTOR' or b.direction<>'RECEIVABLE' then raise exception 'BB_CREDIT_KIND_MISMATCH: kredit retur nota hanya untuk piutang mandor';end if;
  return jsonb_build_array(
    jsonb_build_object('mapping_key','MATERIAL_RECOVERY','debit',s.amount,'credit',0,'contractor_id',b.contractor_id),
    jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',0,'credit',s.amount,'contractor_id',b.contractor_id));
end;$function$;

-- ---------------------------------------------------------------- ALLOCATE_CARRY (ACC-DEC05 CREDIT_THEN_CARRY)
CREATE OR REPLACE FUNCTION erp.bc_allocate_carry_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare e erp.bc_lot_events_v1%rowtype;p erp.payroll_settlements%rowtype;v_amount numeric;v_contractor uuid;v_line uuid;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.payroll.view');
  perform erp._cp3_assert_closed_json_object(p_payload,array['event_id','payroll_id','amount','reason'],
    array['event_id','payroll_id','amount','reason','responsible','reference'],'carry payload');
  select * into e from erp.bc_lot_events_v1 where id=erp.bc_uuid_v1(p_payload,'event_id',true);
  if e.id is null or e.event_kind<>'CREDIT' or e.amount_carry<=0 then raise exception 'BC_CARRY_INVALID: kredit tanpa bagian yang dibawa ke payroll';end if;
  perform pg_advisory_xact_lock(hashtextextended('BCCARRY|'||e.id::text,0));
  select * into p from erp.payroll_settlements where id=erp.bc_uuid_v1(p_payload,'payroll_id',true) for update;
  select coalesce(l.contractor_id,(select c.contractor_id from erp.contractor_material_issues c join erp.contractor_material_issue_items i on i.issue_id=c.id where i.id=l.note_item_id))
    into v_contractor from erp.bc_return_lots_v1 l where l.id=e.lot_id;
  if p.id is null or p.contractor_id is distinct from v_contractor or p.status not in('DRAFT','CALCULATED','REVIEW') then
    raise exception 'BC_CARRY_INVALID: pilih payroll draft mandor yang sama';end if;
  if jsonb_typeof(p_payload->'amount') is distinct from 'string' then raise exception 'BB_AMOUNT_INVALID: amount harus nominal tepat dua desimal';end if;
  v_amount:=erp.bb_parse_amount_v1(p_payload->>'amount','amount');
  if v_amount>coalesce(erp.bc_carry_remaining_v1(e.id),0) then
    raise exception 'BC_CARRY_EXCEEDS: sisa kredit yang dibawa % , diminta %',coalesce(erp.bc_carry_remaining_v1(e.id),0),v_amount;end if;
  perform erp.bc_new_document_v1(p_request,'ALLOCATE_CARRY',statement_timestamp(),p_payload);
  insert into erp.payroll_reimbursements(payroll_id,amount,description,source_type,bc_credit_event_id)
  values(p.id,v_amount,'Kredit retur nota aksesori dibawa ke payroll','BC_RETURN_CARRY',e.id) returning id into v_line;
  perform erp.bc_link_v1(p_request,'PAYROLL_LINE',v_line);
  perform erp.recalculate_payroll(p.id);
  return jsonb_build_object('payroll_line_id',v_line,'carry_remaining',erp.bc_carry_remaining_v1(e.id)::text);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bc_guard_carry_reimbursement_v1()
 RETURNS trigger LANGUAGE plpgsql SET search_path TO ''
AS $function$
declare p erp.payroll_settlements%rowtype;
begin
  if tg_op='DELETE' then
    if old.bc_credit_event_id is null then return old;end if;
    select * into p from erp.payroll_settlements where id=old.payroll_id;
    if p.status not in('DRAFT','CALCULATED','REVIEW') then raise exception 'BC_CARRY_LOCKED: kredit yang dibawa hanya dilepas dari payroll draft';end if;
    return old;
  end if;
  if new.bc_credit_event_id is null and new.source_type::text<>'BC_RETURN_CARRY' and (tg_op='INSERT' or old.bc_credit_event_id is null) then return new;end if;
  if current_user<>'postgres' then raise exception 'BC_CARRY_WRITER: kredit retur masuk payroll hanya lewat command resmi';end if;
  if tg_op='UPDATE' and (new.payroll_id<>old.payroll_id or new.bc_credit_event_id is distinct from old.bc_credit_event_id
      or new.source_type is distinct from old.source_type or new.amount<>old.amount) then
    raise exception 'BC_CARRY_LOCKED: baris kredit retur di payroll tidak dapat diubah; lepaskan lalu pilih ulang';end if;
  if new.amount<>round(new.amount,2) or new.amount<=0 then raise exception 'BC_CARRY_INVALID: nominal kredit positif dua desimal';end if;
  return new;
end;$function$;
create trigger trg_bc_carry_reimbursement before insert or update or delete on erp.payroll_reimbursements
  for each row execute function erp.bc_guard_carry_reimbursement_v1();

-- ---------------------------------------------------------------- ROUND_NOTE (ACC-DEC06)
-- One separate rounding line per note to the nearest whole rupiah of what is still collectible; PCS and the original
-- amounts are unchanged. Refused when payroll already took more than the rounded amount of a line.
CREATE OR REPLACE FUNCTION erp.bc_round_note_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_policy jsonb;h erp.contractor_material_issues%rowtype;v_item uuid;v_total numeric;v_round numeric;v_journal uuid;v_day date;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.contractor_accessory.reverse');
  perform erp._cp3_assert_closed_json_object(p_payload,array['issue_id','reason'],array['issue_id','reason','responsible','reference'],'rounding payload');
  v_policy:=erp.bc_require_policy_v1('ACC_DEC06','pembulatan rupiah nota mandor');
  select * into h from erp.contractor_material_issues where id=erp.bc_uuid_v1(p_payload,'issue_id',true) for update;
  if h.id is null or h.status<>'POSTED' then raise exception 'BC_NOTE_NOT_POSTED: pembulatan hanya untuk nota yang disahkan';end if;
  perform pg_advisory_xact_lock(hashtextextended('BCNOTE|'||i.id::text,0)) from erp.contractor_material_issue_items i where i.issue_id=h.id order by i.id;
  perform pg_advisory_xact_lock(hashtextextended('PAYKASBON|'||i.id::text,0)) from erp.contractor_material_issue_items i where i.issue_id=h.id order by i.id;
  if exists(select 1 from erp.bc_note_roundings_v1 r join erp.bc_documents_v1 d on d.id=r.id where r.issue_id=h.id and d.status='POSTED') then
    raise exception 'BC_ROUNDING_EXISTS: nota ini sudah dibulatkan; batalkan pembulatan lama dahulu';end if;
  select round(sum(coalesce(total_receivable,0)),2)-sum(erp.bc_note_item_adjustment_v1(id)) into v_total from erp.contractor_material_issue_items where issue_id=h.id;
  v_round:=round(v_total,0)-v_total;
  if v_round=0 then raise exception 'BC_ROUNDING_NONE: sisa tagihan nota sudah rupiah bulat';end if;
  select id into v_item from erp.contractor_material_issue_items where issue_id=h.id order by total_receivable desc nulls last,id limit 1;
  if erp.bc_note_item_allocated_v1(v_item)>erp.bc_note_item_collectible_v1(v_item)+v_round+0.01 then
    raise exception 'BC_ROUNDING_BELOW_PAID: potongan payroll pada nota ini melebihi hasil pembulatan';end if;
  v_day:=erp.bb_business_today_v1();
  perform erp.bc_new_document_v1(p_request,'ROUND_NOTE',statement_timestamp(),p_payload,jsonb_build_object('ACC_DEC06',erp.bc_policy_version_v1('ACC_DEC06')));
  v_journal:=erp.post_journal('BC_NOTE_ROUNDING',p_request,v_day,'Pembulatan rupiah nota mandor '||h.issue_number,
    case when v_round>0 then jsonb_build_array(
      jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',v_round,'credit',0,'contractor_id',h.contractor_id,'po_id',h.po_id),
      jsonb_build_object('account_id',(v_policy->>'gain_account_id')::uuid,'debit',0,'credit',v_round,'contractor_id',h.contractor_id,'po_id',h.po_id))
    else jsonb_build_array(
      jsonb_build_object('account_id',(v_policy->>'loss_account_id')::uuid,'debit',-v_round,'credit',0,'contractor_id',h.contractor_id,'po_id',h.po_id),
      jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',0,'credit',-v_round,'contractor_id',h.contractor_id,'po_id',h.po_id)) end);
  insert into erp.bc_note_roundings_v1(id,issue_id,item_id,amount,journal_entry_id) values(p_request,h.id,v_item,v_round,v_journal);
  perform erp.bc_link_v1(p_request,'JOURNAL',v_journal);
  perform erp.refresh_contractor_issue_payroll_status(v_item);
  return jsonb_build_object('issue_id',h.id,'rounding',v_round::text,'collectible',(v_total+v_round)::text);
end;$function$;

-- ---------------------------------------------------------------- ERP-DEC02 Special free categories
-- Free basis of one accessory for one contractor at one time: the owner's list names the category and the contractor's
-- effective HPP policy is Special. Null when the policy is pending or it does not apply (then the note needs a price).
CREATE OR REPLACE FUNCTION erp.bc_free_basis_v1(p_material uuid,p_contractor uuid,p_at timestamptz)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object('category_id',m.accessory_category_id,'policy_version',erp.bc_policy_version_v1('ERP_DEC02')::text)
  from erp.materials m
  where m.id=p_material and m.material_type='ACCESSORY'
    and coalesce(erp.bc_policy_v1('ERP_DEC02')->'special_free_category_ids','[]'::jsonb) ? m.accessory_category_id::text
    and exists(select 1 from erp.contractor_hpp_policy_versions v where v.contractor_id=p_contractor and v.is_special
      and v.effective_from<=p_at and (v.effective_to is null or v.effective_to>p_at))
$function$;

-- ---------------------------------------------------------------- guards on the source note
-- A note with a return lot or a rounding cannot be reversed by the generic note reversal: undo those first (the return
-- movement and credits depend on it).
CREATE OR REPLACE FUNCTION erp.bc_guard_note_reversal_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  if new.status='REVERSED' and old.status<>'REVERSED' and (exists(select 1 from erp.bc_return_lots_v1 l join erp.bc_documents_v1 d on d.id=l.document_id
        join erp.contractor_material_issue_items i on i.id=l.note_item_id where i.issue_id=new.id and d.status='POSTED')
      or exists(select 1 from erp.bc_note_roundings_v1 r join erp.bc_documents_v1 d on d.id=r.id where r.issue_id=new.id and d.status='POSTED')) then
    raise exception 'BC_NOTE_HAS_RETURNS: nota ini punya retur atau pembulatan aktif; batalkan dahulu lewat Pemakaian & Pengembalian Aksesori';
  end if;
  return new;
end;$function$;
create trigger trg_bc_note_reversal before update of status on erp.contractor_material_issues
  for each row execute function erp.bc_guard_note_reversal_v1();

-- An opening note-return credit is a settlement of the imported receipt made by one BC credit; it is undone only by reversing
-- that BC document (which also returns the custody), never directly through the opening-settlement continuation.
CREATE OR REPLACE FUNCTION erp.bc_guard_note_credit_settlement_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  if new.status='REVERSED' and old.status<>'REVERSED' and not erp.bc_in_context_v1()
     and exists(select 1 from erp.bb_opening_credits_v1 c where c.settlement_id=new.id and c.credit_kind='ACCESSORY_NOTE_RETURN') then
    raise exception 'BC_CREDIT_SOURCE_REVERSAL: kredit retur nota dibatalkan lewat dokumen Pemakaian & Pengembalian Aksesori-nya';
  end if;
  return new;
end;$function$;
create trigger trg_bc_note_credit_settlement before update of status on erp.opening_subledger_settlements
  for each row execute function erp.bc_guard_note_credit_settlement_v1();
-- ================================================================ BC import: ALL-C02 and ALL-C03
-- ALL-C02 (auditor r9: "old source stock issue is not replayed. Opening note receivable is only its evidenced unpaid residual
-- ... Once the 3 returned PCS are received and an explicit policy gives source credit, credit right is at most 3p ... If no
-- proven credit right, stock custody can be recorded as pending-value but no automatic contractor credit"; Fable C02: the
-- CONTRACTOR_RECEIVABLE opening document keeps 50/20 as provenance, the credit only at the old note's own price/qty).
-- New file OPENING_ACCESSORY_NOTE_LINE: the lines of the old note behind an imported CONTRACTOR_RECEIVABLE document of the same
-- batch (same contractor and document number); the line amounts add up to the document's original amount. Nothing is
-- journaled or moved; a later return uses RECEIVE_RETURN (NOTE_RETURN, opening_note_line_id) and CREDIT_NOTE_RETURN.
--
-- ALL-C03 (auditor r9: "only the evidenced usable 5 are ready stock; 2 remain quarantine ... 1 remains outstanding and is not
-- in available stock. Unknown-value recovery can be recorded physically as pending valuation with no artificial zero-cost
-- financial close"; Fable C03: M:3933 pending value, M:4882 no overlap). Valued company stock at the service post and at the
-- inspection/damaged areas is ordinary opening stock (OPENING_BALANCE_ITEM MATERIAL at the zone's location code: an opening
-- count may enter a zone). New file OPENING_ACCESSORY_CUSTODY carries what is not stock: PENDING_VALUE (company custody with
-- unknown recovery value at an inspection area, condition WAITING/USABLE/DAMAGED, labelled baseline count), UNRETURNED
-- (expected back from a holder, company- or customer-owned, not stock) and CUSTOMER_GARMENT (a customer's garment in
-- service: never company FG, AR or entitlement). Each row has a custody_key used once.

CREATE OR REPLACE FUNCTION erp.bc_check_import_row_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;v_qty numeric;v_amount numeric;v_count boolean;v_type text;v_doc record;v_kind text;
  v_zone text;v_total numeric;
begin
  perform erp.require_owner_admin();
  select * into r from erp.migration_staging_rows where id=p_row and batch_id=p_batch
    and entity_type in('OPENING_ACCESSORY_NOTE_LINE','OPENING_ACCESSORY_CUSTODY');
  if r.id is null then raise exception 'Baris aksesori saldo awal tidak ditemukan';end if;
  j:=r.normalized_payload;
  if r.entity_type='OPENING_ACCESSORY_NOTE_LINE' then
    foreach k in array array['document_number','contractor_code','line_number','material_sku','qty','line_amount'] loop
      if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk baris nota aksesori lama',k;end if;
    end loop;
    if j->>'line_number'!~'^[1-9][0-9]{0,2}$' then raise exception 'line_number: nomor baris 1-999';end if;
    select m.material_type,u.dimension='COUNT' into v_type,v_count from erp.materials m join erp.uom_definitions u on u.unit_code=m.unit_code
      where m.material_sku=j->>'material_sku' and m.is_active;
    if v_type is null then
      select upper(s.normalized_payload->>'material_type'),(select u.dimension='COUNT' from erp.uom_definitions u where u.unit_code=s.normalized_payload->>'unit_code')
        into v_type,v_count from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='MATERIAL' and s.validation_status='VALID'
          and s.normalized_payload->>'material_sku'=j->>'material_sku' limit 1;
    end if;
    if v_type is distinct from 'ACCESSORY' then raise exception 'material_sku: nota aksesori hanya untuk aksesori aktif';end if;
    if (v_count and j->>'qty'!~'^[1-9][0-9]{0,11}$') or (not v_count and j->>'qty'!~'^[0-9]{1,12}(\.[0-9]{1,6})?$') then
      raise exception 'qty: % positif',case when v_count then 'PCS utuh' else 'angka maksimal enam desimal' end;end if;
    v_qty:=(j->>'qty')::numeric;
    if v_qty<=0 then raise exception 'qty: harus lebih dari nol';end if;
    v_amount:=erp.bb_parse_amount_v1(j->>'line_amount','line_amount',true);
    -- The note's CONTRACTOR_RECEIVABLE opening document in this batch.
    select s.id,s.normalized_payload into v_doc from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_BALANCE_ITEM'
      and upper(s.normalized_payload->>'balance_type')='CONTRACTOR_RECEIVABLE' and s.normalized_payload->>'contractor_code'=j->>'contractor_code'
      and lower(btrim(s.normalized_payload->>'document_number'))=lower(btrim(j->>'document_number'));
    if v_doc.id is null then raise exception 'BC_C02_DOCUMENT_REQUIRED: piutang mandor saldo awal dengan nomor dokumen dan mandor ini tidak ada di impor';end if;
    if nullif(btrim(v_doc.normalized_payload->>'original_amount'),'') is null then
      raise exception 'BC_C02_DOCUMENT_REQUIRED: dokumen piutang mandor wajib membawa nominal dokumen awal';end if;
    if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_ACCESSORY_NOTE_LINE' and x.id<>r.id
        and lower(btrim(x.normalized_payload->>'document_number'))=lower(btrim(j->>'document_number'))
        and x.normalized_payload->>'contractor_code'=j->>'contractor_code' and x.normalized_payload->>'line_number'=j->>'line_number') then
      raise exception 'BC_C02_DUPLICATE_LINE: nomor baris nota ganda';end if;
    select sum(replace(btrim(x.normalized_payload->>'line_amount'),',','.')::numeric) into v_total from erp.migration_staging_rows x
      where x.batch_id=p_batch and x.entity_type='OPENING_ACCESSORY_NOTE_LINE' and x.normalized_payload->>'contractor_code'=j->>'contractor_code'
        and lower(btrim(x.normalized_payload->>'document_number'))=lower(btrim(j->>'document_number'))
        and btrim(x.normalized_payload->>'line_amount')~'^[0-9]+([.,][0-9]{1,2})?$';
    if v_total is distinct from replace(btrim(v_doc.normalized_payload->>'original_amount'),',','.')::numeric then
      raise exception 'BC_C02_TOTAL_MISMATCH: jumlah baris nota % tidak sama dengan nominal dokumen awal %',v_total,v_doc.normalized_payload->>'original_amount';end if;
    return jsonb_build_object('qty',v_qty,'line_amount',v_amount,'document_row_id',v_doc.id);
  end if;
  -- OPENING_ACCESSORY_CUSTODY
  v_kind:=upper(coalesce(j->>'custody_kind',''));
  if v_kind not in('PENDING_VALUE','UNRETURNED','CUSTOMER_GARMENT') then
    raise exception 'custody_kind: PENDING_VALUE, UNRETURNED atau CUSTOMER_GARMENT';end if;
  if nullif(btrim(j->>'custody_key'),'') is null or length(btrim(j->>'custody_key'))>80 then raise exception 'custody_key: wajib, maksimal 80 karakter';end if;
  if exists(select 1 from erp.migration_staging_rows x where x.entity_type='OPENING_ACCESSORY_CUSTODY' and x.id<>r.id
      and lower(btrim(x.normalized_payload->>'custody_key'))=lower(btrim(j->>'custody_key'))
      and (x.batch_id=p_batch or x.posted_entity_id is not null)) then
    raise exception 'BC_C03_DUPLICATE: custody_key sudah dipakai; satu barang fisik hanya satu baris';end if;
  if nullif(btrim(j->>'unit_cost'),'') is not null then
    raise exception 'BC_C03_VALUED_ROW: barang bernilai adalah stok saldo awal biasa (OPENING_BALANCE_ITEM MATERIAL di lokasi zona), bukan titipan';end if;
  if j->>'qty'!~'^[1-9][0-9]{0,11}$' then raise exception 'qty: PCS utuh positif';end if;
  if v_kind in('PENDING_VALUE','UNRETURNED') and not (v_kind='UNRETURNED' and nullif(btrim(j->>'material_sku'),'') is null) then
    if not exists(select 1 from erp.materials m join erp.uom_definitions u on u.unit_code=m.unit_code where m.material_sku=j->>'material_sku'
        and m.is_active and m.material_type='ACCESSORY' and u.dimension='COUNT')
      and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='MATERIAL' and s.validation_status='VALID'
        and s.normalized_payload->>'material_sku'=j->>'material_sku' and upper(s.normalized_payload->>'material_type')='ACCESSORY') then
      raise exception 'material_sku: aksesori hitung aktif tidak ditemukan';end if;
  end if;
  if v_kind='PENDING_VALUE' then
    if upper(coalesce(j->>'condition',''))not in('WAITING','USABLE','DAMAGED') then raise exception 'condition: WAITING, USABLE atau DAMAGED';end if;
    select z.zone_kind into v_zone from erp.locations l join erp.bc_accessory_zones_v1 z on z.location_id=l.id
      where l.location_code=j->>'location_code' and l.is_active;
    if v_zone is distinct from 'INSPECTION' then
      raise exception 'location_code: titipan bernilai pending berada di area pemeriksaan terdaftar';end if;
  elsif v_kind='UNRETURNED' then
    if nullif(btrim(j->>'holder'),'') is null or length(btrim(j->>'holder'))>120 then raise exception 'holder: pemegang wajib diisi';end if;
    if upper(coalesce(j->>'owner_kind',''))not in('COMPANY','CUSTOMER') then raise exception 'owner_kind: COMPANY atau CUSTOMER';end if;
    if nullif(btrim(j->>'material_sku'),'') is null and nullif(btrim(j->>'description'),'') is null then
      raise exception 'description: isi aksesori atau keterangan barang';end if;
  else
    if nullif(btrim(j->>'customer_code'),'') is null or nullif(btrim(j->>'description'),'') is null then
      raise exception 'customer_code/description: titipan pelanggan wajib pelanggan dan keterangan';end if;
    if not exists(select 1 from erp.customers where customer_code=j->>'customer_code' and is_active)
      and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='CUSTOMER' and s.validation_status='VALID'
        and s.normalized_payload->>'customer_code'=j->>'customer_code') then raise exception 'customer_code: pelanggan aktif tidak ditemukan';end if;
  end if;
  return jsonb_build_object('kind',v_kind,'qty',(j->>'qty')::numeric);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bc_validate_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;
begin
  perform erp.require_owner_admin();
  for r in select id from erp.migration_staging_rows where batch_id=p_batch and entity_type in('OPENING_ACCESSORY_NOTE_LINE','OPENING_ACCESSORY_CUSTODY')
      order by entity_type,source_row_no loop
    begin
      perform erp.bc_check_import_row_v1(p_batch,r.id);
      update erp.migration_staging_rows set validation_status='VALID',validation_errors='[]' where id=r.id;
    exception when others then
      update erp.migration_staging_rows set validation_status='ERROR',validation_errors=jsonb_build_array(sqlerrm) where id=r.id;
    end;
  end loop;
end;$function$;

-- After the opening documents and stock are posted.
CREATE OR REPLACE FUNCTION erp.bc_apply_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;j jsonb;c jsonb;b erp.migration_batches%rowtype;v_balance uuid;v_material uuid;v_location uuid;v_id uuid;v_cond text;
begin
  perform erp.require_owner_admin();
  select * into b from erp.migration_batches where id=p_batch;
  for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type in('OPENING_ACCESSORY_NOTE_LINE','OPENING_ACCESSORY_CUSTODY')
      and posted_entity_id is null order by entity_type,source_row_no loop
    if r.validation_status<>'VALID' then raise exception 'Baris aksesori saldo awal belum lolos pemeriksaan';end if;
    j:=r.normalized_payload;c:=erp.bc_check_import_row_v1(p_batch,r.id);v_id:=gen_random_uuid();
    if r.entity_type='OPENING_ACCESSORY_NOTE_LINE' then
      select ob.id into v_balance from erp.initial_import_financial_sources f join erp.opening_subledger_balances ob on ob.opening_item_id=f.opening_item_id
        where f.source_row_id=(c->>'document_row_id')::uuid;
      if v_balance is null then raise exception 'BC_C02_DOCUMENT_REQUIRED: piutang mandor dokumen % belum terbentuk',j->>'document_number';end if;
      select id into strict v_material from erp.materials where material_sku=j->>'material_sku';
      insert into erp.bc_opening_note_lines_v1(id,batch_id,source_row_id,balance_id,document_number,line_number,material_id,qty,line_amount)
      values(v_id,p_batch,r.id,v_balance,btrim(j->>'document_number'),(j->>'line_number')::int,v_material,(c->>'qty')::numeric,(c->>'line_amount')::numeric);
    elsif c->>'kind'='PENDING_VALUE' then
      select id into strict v_material from erp.materials where material_sku=j->>'material_sku';
      select id into strict v_location from erp.locations where location_code=j->>'location_code';
      v_cond:=upper(j->>'condition');
      insert into erp.bc_return_lots_v1(id,source_kind,owner_kind,value_mode,material_id,location_id,qty_received,init_usable,init_damaged,
        received_at,batch_id,source_row_id,reference)
      values(v_id,'OPENING_PENDING_VALUE','COMPANY','PENDING',v_material,v_location,(c->>'qty')::numeric,
        case when v_cond='USABLE' then (c->>'qty')::numeric else 0 end,case when v_cond='DAMAGED' then (c->>'qty')::numeric else 0 end,
        b.cutover_at,p_batch,r.id,'Opname awal '||btrim(j->>'custody_key')||coalesce(' — '||nullif(btrim(j->>'notes'),''),''));
    elsif c->>'kind'='UNRETURNED' then
      insert into erp.bc_outstanding_returns_v1(id,source_kind,owner_kind,material_id,description,qty_expected,holder,reference,batch_id,source_row_id)
      values(v_id,'OPENING_UNRETURNED',upper(j->>'owner_kind'),(select id from erp.materials where material_sku=nullif(btrim(j->>'material_sku'),'')),
        nullif(btrim(j->>'description'),''),(c->>'qty')::numeric,btrim(j->>'holder'),'Opname awal '||btrim(j->>'custody_key'),p_batch,r.id);
    else
      insert into erp.bc_customer_custody_v1(id,customer_id,product_id,description,qty,received_at,batch_id)
      values(v_id,(select id from erp.customers where customer_code=j->>'customer_code'),
        (select id from erp.products where lower(btrim(sku))=lower(btrim(nullif(j->>'product_sku','')))),
        btrim(j->>'description'),(c->>'qty')::numeric,b.cutover_at,p_batch);
    end if;
    update erp.migration_staging_rows set posted_entity_id=v_id,posted_entity_type=r.entity_type,posted_at=statement_timestamp(),
      updated_at=statement_timestamp() where id=r.id;
  end loop;
  -- Valued opening stock counted at an inspection area (ALL-C03 quarantine, value kept): one ledger lot per opening row so the
  -- inspection can later move it to the warehouse or the damaged area at its value.
  insert into erp.bc_return_lots_v1(source_kind,owner_kind,value_mode,material_id,location_id,qty_received,received_at,batch_id,source_row_id,reference)
  select 'OPENING_QUARANTINE','COMPANY','LEDGER',i.material_id,i.location_id,i.qty,b.cutover_at,p_batch,i.id,'Opname awal area pemeriksaan (saldo awal '||i.id||')'
  from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id
  join erp.bc_accessory_zones_v1 z on z.location_id=i.location_id and z.zone_kind='INSPECTION'
  where h.migration_batch_id=p_batch and i.balance_type='MATERIAL' and i.qty>0
    and not exists(select 1 from erp.bc_return_lots_v1 l where l.source_kind='OPENING_QUARANTINE' and l.source_row_id=i.id);
end;$function$;

-- The import workspace part (read only; the continuation is the accessory service workspace).
CREATE OR REPLACE FUNCTION erp.bc_import_workspace_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object(
    'accessory_note_lines',coalesce((select jsonb_agg(jsonb_build_object('line_id',n.id,'document_number',n.document_number,'line_number',n.line_number,
        'material_sku',m.material_sku,'qty',n.qty::text,'line_amount',n.line_amount::text,
        'returned',coalesce((select sum(l.qty_received) from erp.bc_return_lots_v1 l join erp.bc_documents_v1 d on d.id=l.document_id
          where l.opening_note_line_id=n.id and d.status='POSTED'),0)::numeric(24,6)::text,
        'remaining_receivable',(b.original_amount-b.settled_amount)::text) order by n.document_number,n.line_number)
      from erp.bc_opening_note_lines_v1 n join erp.materials m on m.id=n.material_id join erp.opening_subledger_balances b on b.id=n.balance_id
      where n.batch_id=p_batch),'[]'::jsonb),
    'accessory_custody',coalesce((select jsonb_agg(x order by x->>'kind',x->>'key') from (
        select jsonb_build_object('kind',case l.source_kind when 'OPENING_QUARANTINE' then 'QUARANTINE_VALUED' else 'PENDING_VALUE' end,
          'key',l.reference,'material_sku',m.material_sku,'qty',l.qty_received::text,
          'value_status',case l.value_mode when 'LEDGER' then 'Bernilai di buku' else 'Belum dinilai' end,'state',erp.bc_lot_state_text_v1(l.id)) x
        from erp.bc_return_lots_v1 l join erp.materials m on m.id=l.material_id where l.batch_id=p_batch
        union all select jsonb_build_object('kind','UNRETURNED','key',o.reference,'material_sku',m.material_sku,'description',o.description,
          'qty',o.qty_expected::text,'owner_kind',o.owner_kind,'holder',o.holder,'value_status','Belum kembali')
        from erp.bc_outstanding_returns_v1 o left join erp.materials m on m.id=o.material_id where o.batch_id=p_batch
        union all select jsonb_build_object('kind','CUSTOMER_GARMENT','key',c.description,'customer_code',k.customer_code,'qty',c.qty::text,
          'value_status','Milik pelanggan')
        from erp.bc_customer_custody_v1 c join erp.customers k on k.id=c.customer_id where c.batch_id=p_batch) s),'[]'::jsonb))
$function$;

CREATE OR REPLACE FUNCTION erp.bc_import_revision_part_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object('note_lines',(select count(*) from erp.bc_opening_note_lines_v1 where batch_id=p_batch),
    'returns',(select coalesce(jsonb_agg(jsonb_build_object('id',d.id,'status',d.status,'v',d.row_version) order by d.id),'[]'::jsonb)
      from erp.bc_documents_v1 d where exists(select 1 from erp.bc_return_lots_v1 l join erp.bc_opening_note_lines_v1 n on n.id=l.opening_note_line_id
        where l.document_id=d.id and n.batch_id=p_batch)))
$function$;
-- ================================================================ BC reversal, command router, workspace read, public RPCs

-- The inverse of one BC document, linked, in the reverse order of what depends on it (M:5040, 6.3). A reversal that
-- would take away stock or a quantity that a later document already used is refused by the native guards (negative
-- stock) or by the lot state check at the end; nothing is left half-done.
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
  return jsonb_build_object('reversed_document_id',d.id,'row_version',v_version::text);
end;$function$;

-- ---------------------------------------------------------------- the command router (one public RPC)
CREATE OR REPLACE FUNCTION erp.save_accessory_service_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET "TimeZone" TO 'UTC' SET "DateStyle" TO 'ISO, YMD'
AS $function$
declare v_action text:=upper(btrim(coalesce(p_action,'')));v_cached jsonb;v_result jsonb;v_doc uuid;
begin
  perform erp.require_permission('warehouse.accessory.view');
  if v_action not in('SET_POLICY','REGISTER_ZONE','FILL_POST','RETURN_TO_WAREHOUSE','INTERNAL_USE','RECEIVE_RETURN','INSPECT','VALUE_CUSTODY',
      'CREDIT_NOTE_RETURN','ALLOCATE_CARRY','DISPOSE_STOCK','CLOSE_CUSTODY','CUSTOMER_GARMENT_IN','CUSTOMER_GARMENT_OUT','COUNT_POST',
      'RESOLVE_VARIANCE','ROUND_NOTE','REVERSE') then
    raise exception 'BC_ACTION_UNKNOWN: tindakan aksesori tidak dikenal';end if;
  if v_action in('FILL_POST','RETURN_TO_WAREHOUSE','INTERNAL_USE','RECEIVE_RETURN','INSPECT','CLOSE_CUSTODY','DISPOSE_STOCK','CUSTOMER_GARMENT_IN',
      'CUSTOMER_GARMENT_OUT','COUNT_POST','RESOLVE_VARIANCE','REVERSE') then
    perform erp.require_permission('warehouse.stock.adjust');
  end if;
  if v_action='REVERSE' then
    begin perform erp.require_owner_admin();
    exception when others then raise exception 'BC_APPROVAL_REQUIRED: pembatalan memerlukan owner/admin';end;
  end if;
  perform erp.require_internal();
  if p_client_request_id is null then raise exception 'BC_REQUEST_ID_REQUIRED: request id wajib';end if;
  if jsonb_typeof(p_payload) is distinct from 'object' or octet_length(p_payload::text)>20000 then raise exception 'BC_PAYLOAD_INVALID: data tidak valid';end if;
  v_cached:=erp._idempotency_begin('save_accessory_service_action_v1',p_client_request_id,
    erp._request_hash(jsonb_build_object('action',v_action,'payload',p_payload)));
  if v_cached is not null then return v_cached;end if;
  if exists(select 1 from erp.bc_documents_v1 where id=p_client_request_id) then raise exception 'BC_REQUEST_REUSED: request id sudah dipakai';end if;
  perform set_config('app.change_reason',coalesce(nullif(btrim(p_payload->>'reason'),''),v_action),true);
  perform erp.bc_enter_context_v1();
  v_result:=case v_action
    when 'SET_POLICY' then erp.bc_set_policy_v1(p_payload,p_client_request_id)
    when 'REGISTER_ZONE' then erp.bc_register_zone_v1(p_payload,p_client_request_id)
    when 'FILL_POST' then erp.bc_move_post_v1(v_action,p_payload,p_client_request_id)
    when 'RETURN_TO_WAREHOUSE' then erp.bc_move_post_v1(v_action,p_payload,p_client_request_id)
    when 'INTERNAL_USE' then erp.bc_internal_use_v1(p_payload,p_client_request_id)
    when 'RECEIVE_RETURN' then erp.bc_receive_return_v1(p_payload,p_client_request_id)
    when 'INSPECT' then erp.bc_inspect_v1(p_payload,p_client_request_id)
    when 'VALUE_CUSTODY' then erp.bc_value_custody_v1(p_payload,p_client_request_id)
    when 'CREDIT_NOTE_RETURN' then erp.bc_credit_note_return_v1(p_payload,p_client_request_id)
    when 'ALLOCATE_CARRY' then erp.bc_allocate_carry_v1(p_payload,p_client_request_id)
    when 'DISPOSE_STOCK' then erp.bc_dispose_stock_v1(p_payload,p_client_request_id)
    when 'CLOSE_CUSTODY' then erp.bc_close_custody_v1(p_payload,p_client_request_id)
    when 'CUSTOMER_GARMENT_IN' then erp.bc_customer_garment_v1(v_action,p_payload,p_client_request_id)
    when 'CUSTOMER_GARMENT_OUT' then erp.bc_customer_garment_v1(v_action,p_payload,p_client_request_id)
    when 'COUNT_POST' then erp.bc_count_post_v1(p_payload,p_client_request_id)
    when 'RESOLVE_VARIANCE' then erp.bc_resolve_variance_v1(p_payload,p_client_request_id)
    when 'ROUND_NOTE' then erp.bc_round_note_v1(p_payload,p_client_request_id)
    else erp.bc_reverse_v1(p_payload,p_client_request_id) end;
  perform erp.bc_leave_context_v1();
  v_doc:=case when v_action='REVERSE' then (v_result->>'reversed_document_id')::uuid
    when v_action in('SET_POLICY','REGISTER_ZONE') then null else p_client_request_id end;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values(case when v_action='SET_POLICY' then 'bc_policy_settings_v1' when v_action='REGISTER_ZONE' then 'bc_accessory_zones_v1' else 'bc_documents_v1' end,
    coalesce(v_doc,p_client_request_id),case when v_action='REVERSE' then 'REVERSE' else 'INSERT' end,
    jsonb_build_object('action',v_action,'result',v_result),erp.current_app_user_id(),coalesce(nullif(btrim(p_payload->>'reason'),''),v_action));
  v_result:=v_result||jsonb_build_object('request_id',p_client_request_id,'action',v_action,'document_id',v_doc,
    'status',case when v_action='REVERSE' then 'REVERSED' when v_action in('SET_POLICY','REGISTER_ZONE') then 'SAVED' else 'POSTED' end,
    'row_version',case when v_action='REVERSE' then v_result->>'row_version' when v_doc is not null then
      (select row_version::text from erp.bc_documents_v1 where id=v_doc) end);
  return erp._idempotency_complete('save_accessory_service_action_v1',p_client_request_id,v_result);
end;$function$;

-- ---------------------------------------------------------------- workspace read (server-side search and pagination)
CREATE OR REPLACE FUNCTION erp.bc_bucket_label_v1(p_kind text)
 RETURNS text LANGUAGE sql IMMUTABLE SET search_path TO ''
AS $function$
  select case p_kind when 'MAIN' then 'Di gudang — siap dipakai' when 'SERVICE_POST' then 'Di pos servis — siap dipakai'
    when 'INSPECTION' then 'Menunggu pemeriksaan' when 'DAMAGED' then 'Rusak — menunggu disposisi' end
$function$;

CREATE OR REPLACE FUNCTION erp.get_accessory_service_workspace_v1(p_filters jsonb default '{}'::jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO '' SET "TimeZone" TO 'UTC'
AS $function$
declare v_query text:=lower(btrim(coalesce(p_filters->>'query','')));v_location uuid;v_page integer;v_size integer;v_offset integer;
  v_action text:=upper(nullif(btrim(p_filters->>'action'),''));v_status text:=upper(nullif(btrim(p_filters->>'status'),''));
  v_from date;v_to date;v_value boolean;v_result jsonb;v_doc uuid;v_card jsonb;v_note_query text:=lower(btrim(coalesce(p_filters->>'note_query','')));
  v_customer_query text:=lower(btrim(coalesce(p_filters->>'customer_query','')));v_admin boolean;
begin
  perform erp.require_permission('warehouse.accessory.view');
  perform erp._cp3_assert_closed_json_object(p_filters,array[]::text[],array['query','location_id','action','status','date_from','date_to','page',
    'page_size','document_id','card_material_id','card_location_id','note_query','customer_query'],'accessory service filters');
  if length(v_query)>120 or length(v_note_query)>120 or length(v_customer_query)>120 then raise exception 'BC_FILTER_INVALID: pencarian terlalu panjang';end if;
  if p_filters ? 'page' and (jsonb_typeof(p_filters->'page')<>'number' or (p_filters->>'page')!~'^[1-9][0-9]{0,5}$') then raise exception 'BC_FILTER_INVALID: halaman';end if;
  if p_filters ? 'page_size' and (jsonb_typeof(p_filters->'page_size')<>'number' or (p_filters->>'page_size')!~'^[1-9][0-9]?$' or (p_filters->>'page_size')::int>50) then
    raise exception 'BC_FILTER_INVALID: ukuran halaman 1-50';end if;
  v_page:=coalesce((p_filters->>'page')::int,1);v_size:=coalesce((p_filters->>'page_size')::int,25);v_offset:=(v_page-1)*v_size;
  v_location:=erp.bc_uuid_v1(p_filters,'location_id',false);
  if p_filters ? 'date_from' then v_from:=erp.bb_parse_date_v1(p_filters->>'date_from','date_from');end if;
  if p_filters ? 'date_to' then v_to:=erp.bb_parse_date_v1(p_filters->>'date_to','date_to');end if;
  -- Costs and values only for roles allowed to see them (M:10.2).
  v_value:=erp.has_permission('finance.hpp.view');
  v_admin:=coalesce(erp.current_app_role(),'') in('OWNER','ADMIN') or session_user in('postgres','supabase_admin');
  v_doc:=erp.bc_uuid_v1(p_filters,'document_id',false);
  if p_filters ? 'card_material_id' then
    with m as(select x.*,sum(x.qty_signed) over(order by x.physical_at,x.system_created_at,x.id) running
        from erp.material_stock_movements x where x.material_id=erp.bc_uuid_v1(p_filters,'card_material_id',true)
          and x.location_id=erp.bc_uuid_v1(p_filters,'card_location_id',true)),
      pg as(select * from m order by physical_at desc,system_created_at desc,id desc limit v_size offset v_offset)
    select jsonb_build_object('total',(select count(*) from m),'rows',coalesce(jsonb_agg(jsonb_build_object('movement_id',id,'movement_type',movement_type,
      'source_type',source_type,'physical_local',to_char(physical_at at time zone 'Asia/Jakarta','YYYY-MM-DD HH24:MI'),
      'recorded_local',to_char(system_created_at at time zone 'Asia/Jakarta','YYYY-MM-DD HH24:MI'),
      'before',(running-qty_signed)::text,'qty',qty_signed::text,'after',running::text) order by physical_at desc,system_created_at desc,id desc),'[]'::jsonb))
    into v_card from pg;
  end if;
  with loc as(select l.id,l.location_code,l.location_name,coalesce(z.zone_kind,'MAIN') kind from erp.locations l
      left join erp.bc_accessory_zones_v1 z on z.location_id=l.id where l.location_type='RAW_MATERIAL_WAREHOUSE' and l.is_active),
    stock as(select m.id material_id,m.material_sku,m.material_name,m.unit_code,c.category_name,l.id location_id,l.location_name,l.kind,
        sum(s.qty_signed) qty,max(s.system_created_at) last_at,m.moving_average_cost
      from erp.material_stock_movements s join erp.materials m on m.id=s.material_id and m.material_type='ACCESSORY'
      left join erp.accessory_categories c on c.id=m.accessory_category_id join loc l on l.id=s.location_id
      where (v_location is null or l.id=v_location)
        and (v_query='' or strpos(lower(concat_ws(' ',m.material_sku,m.material_name,c.category_name,l.location_name)),v_query)>0)
      group by m.id,m.material_sku,m.material_name,m.unit_code,c.category_name,l.id,l.location_name,l.kind,m.moving_average_cost
      having sum(s.qty_signed)<>0),
    docs as(select d.*,(select count(*) from erp.bc_document_links_v1 k where k.document_id=d.id) links from erp.bc_documents_v1 d
      where (v_action is null or d.action=v_action) and (v_status is null or d.status=v_status)
        and (v_from is null or erp._cp3_business_date(d.physical_at)>=v_from) and (v_to is null or erp._cp3_business_date(d.physical_at)<=v_to)
        and (v_query='' or strpos(lower(concat_ws(' ',d.document_number,d.reference,d.responsible,d.reason)),v_query)>0)
        and (v_location is null or exists(select 1 from erp.bc_document_links_v1 k join erp.material_transfers t on t.id=k.link_id
            where k.document_id=d.id and v_location in(t.from_location_id,t.to_location_id))
          or exists(select 1 from erp.bc_document_links_v1 k join erp.material_adjustments a on a.id=k.link_id where k.document_id=d.id and a.location_id=v_location)
          or exists(select 1 from erp.bc_return_lots_v1 l where l.document_id=d.id and l.location_id=v_location))),
    lots as(select l.*,m.material_sku,m.material_name,erp.bc_lot_state_v1(l.id) st,(select document_number from erp.bc_documents_v1 where id=l.document_id) doc_number
      from erp.bc_return_lots_v1 l join erp.materials m on m.id=l.material_id
      where (l.document_id is null or (select status from erp.bc_documents_v1 where id=l.document_id)='POSTED')
        and (l.parent_event_id is null or (select x.status from erp.bc_lot_events_v1 e join erp.bc_documents_v1 x on x.id=e.document_id where e.id=l.parent_event_id)='POSTED')
        and (v_query='' or strpos(lower(concat_ws(' ',m.material_sku,m.material_name,l.reference)),v_query)>0))
  select jsonb_build_object(
    'can_see_value',v_value,'is_admin',v_admin,'filters',p_filters,'page',v_page,'page_size',v_size,
    'policies',(select jsonb_agg(jsonb_build_object('key',replace(policy_key,'_','-'),'status',status,'version',version::text,
        'value',case when v_admin then value end,'set_at',set_at) order by policy_key) from erp.bc_policy_settings_v1),
    'locations',coalesce((select jsonb_agg(jsonb_build_object('id',id,'code',location_code,'name',location_name,'kind',kind,'label',erp.bc_bucket_label_v1(kind))
      order by kind,location_name,id) from loc),'[]'::jsonb),
    'stock_total',(select count(*) from stock),
    'stock',coalesce((select jsonb_agg(jsonb_build_object('material_id',material_id,'sku',material_sku,'name',material_name,'unit',unit_code,
        'category',category_name,'location_id',location_id,'location',location_name,'bucket',erp.bc_bucket_label_v1(kind),'kind',kind,
        'qty',qty::numeric(24,6)::text,'value',case when v_value then round(qty*moving_average_cost,2)::text end,
        'updated_local',to_char(last_at at time zone 'Asia/Jakarta','YYYY-MM-DD HH24:MI')) order by material_name,location_name,material_id,location_id)
      from (select * from stock order by material_name,location_name,material_id,location_id limit v_size offset v_offset) x),'[]'::jsonb),
    'documents_total',(select count(*) from docs),
    'documents',coalesce((select jsonb_agg(jsonb_build_object('id',id,'number',document_number,'action',action,'status',status,
        'physical_local',to_char(physical_at at time zone 'Asia/Jakarta','YYYY-MM-DD HH24:MI'),
        'recorded_local',to_char(created_at at time zone 'Asia/Jakarta','YYYY-MM-DD HH24:MI'),'responsible',responsible,'reference',reference,
        'reason',reason,'row_version',row_version::text,'links',links) order by physical_at desc,id)
      from (select * from docs order by physical_at desc,id limit v_size offset v_offset) x),'[]'::jsonb),
    'lots',coalesce((select jsonb_agg(jsonb_build_object('id',id,'document',doc_number,'source_kind',source_kind,'owner_kind',owner_kind,
        'value_status',case value_mode when 'LEDGER' then 'Bernilai di buku' when 'PENDING' then 'Belum dinilai' else 'Milik mandor — menunggu kredit' end,
        'material_id',material_id,'sku',material_sku,'name',material_name,'location_id',location_id,
        'received_local',to_char(received_at at time zone 'Asia/Jakarta','YYYY-MM-DD HH24:MI'),'note_item_id',note_item_id,
        'opening_note_line_id',opening_note_line_id,'reference',reference,
        'state',erp.bc_lot_state_text_v1(id)) order by (st->>'open')::numeric=0,received_at desc,id)
      from (select * from lots order by (st->>'open')::numeric=0,received_at desc,id limit 100) x),'[]'::jsonb),
    'outstanding',coalesce((select jsonb_agg(jsonb_build_object('id',o.id,'source_kind',o.source_kind,'owner_kind',o.owner_kind,'material_id',o.material_id,
        'description',o.description,'holder',o.holder,'reference',o.reference,'expected',o.qty_expected::text,
        'received',coalesce((select sum(l.qty_received) from erp.bc_return_lots_v1 l join erp.bc_documents_v1 d on d.id=l.document_id
          where l.outstanding_id=o.id and d.status='POSTED'),0)::numeric(24,6)::text,'label','Belum kembali') order by o.created_at desc,o.id)
      from erp.bc_outstanding_returns_v1 o where o.status='OPEN'),'[]'::jsonb),
    'customer_custody',coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'customer',k.customer_name,'description',c.description,'qty',c.qty::text,
        'received_local',to_char(c.received_at at time zone 'Asia/Jakarta','YYYY-MM-DD HH24:MI'),'returned',c.out_document_id is not null
          and (select status from erp.bc_documents_v1 where id=c.out_document_id)='POSTED') order by c.received_at desc,c.id)
      from erp.bc_customer_custody_v1 c join erp.customers k on k.id=c.customer_id
      where c.batch_id is not null or (select status from erp.bc_documents_v1 where id=c.in_document_id)='POSTED'),'[]'::jsonb),
    'variances',coalesce((select jsonb_agg(jsonb_build_object('id',v.id,'material_id',v.material_id,'location_id',v.location_id,'book',v.book_qty::text,
        'counted',v.counted_qty::text,'variance',v.variance::text,'label','Selisih belum diketahui — perlu tinjauan',
        'resolved',v.resolution_document_id is not null and (select status from erp.bc_documents_v1 where id=v.resolution_document_id)='POSTED')
        order by v.counted_at desc,v.id)
      from erp.bc_count_variances_v1 v where (select status from erp.bc_documents_v1 where id=v.document_id)='POSTED'),'[]'::jsonb),
    'notes',case when v_note_query<>'' then coalesce((select jsonb_agg(jsonb_build_object('item_id',i.id,'issue_id',h.id,'number',h.issue_number,
        'contractor',c.contractor_name,'material_id',i.material_id,'sku',m.material_sku,'name',m.material_name,'qty',i.qty::text,
        'returned',coalesce((select sum(l.qty_received) from erp.bc_return_lots_v1 l join erp.bc_documents_v1 d on d.id=l.document_id
          where l.note_item_id=i.id and d.status='POSTED'),0)::numeric(24,6)::text,
        'collectible',round(erp.bc_note_item_collectible_v1(i.id),2)::text,'allocated',erp.bc_note_item_allocated_v1(i.id)::numeric(24,2)::text,
        'payroll_status',i.payroll_status) order by h.issue_number,i.id)
      from erp.contractor_material_issue_items i join erp.contractor_material_issues h on h.id=i.issue_id join erp.contractors c on c.id=h.contractor_id
      join erp.materials m on m.id=i.material_id
      where i.id in(select i2.id from erp.contractor_material_issue_items i2 join erp.contractor_material_issues h2 on h2.id=i2.issue_id
        join erp.contractors c2 on c2.id=h2.contractor_id join erp.materials m2 on m2.id=i2.material_id
        where h2.status='POSTED' and m2.material_type='ACCESSORY' and strpos(lower(concat_ws(' ',h2.issue_number,c2.contractor_name)),v_note_query)>0
        order by h2.issue_number,i2.id limit 50)),'[]'::jsonb) end,
    'opening_notes',case when v_note_query<>'' then coalesce((select jsonb_agg(jsonb_build_object('line_id',n.id,'number',n.document_number,
        'contractor',c.contractor_name,'material_id',n.material_id,'sku',m.material_sku,'name',m.material_name,'qty',n.qty::text,
        'line_amount',n.line_amount::text,'returned',coalesce((select sum(l.qty_received) from erp.bc_return_lots_v1 l join erp.bc_documents_v1 d on d.id=l.document_id
          where l.opening_note_line_id=n.id and d.status='POSTED'),0)::numeric(24,6)::text,'remaining_receivable',(b.original_amount-b.settled_amount)::text) order by n.document_number,n.line_number)
      from erp.bc_opening_note_lines_v1 n join erp.opening_subledger_balances b on b.id=n.balance_id join erp.contractors c on c.id=b.contractor_id
      join erp.materials m on m.id=n.material_id where n.id in(select n2.id from erp.bc_opening_note_lines_v1 n2 join erp.opening_subledger_balances b2 on b2.id=n2.balance_id
        join erp.contractors c2 on c2.id=b2.contractor_id where strpos(lower(concat_ws(' ',n2.document_number,c2.contractor_name)),v_note_query)>0
        order by n2.document_number,n2.line_number limit 50)),'[]'::jsonb) end,
    'customers',case when v_customer_query<>'' then coalesce((select jsonb_agg(jsonb_build_object('id',id,'code',customer_code,'name',customer_name) order by customer_name,id)
      from (select * from erp.customers where is_active and strpos(lower(concat_ws(' ',customer_code,customer_name)),v_customer_query)>0 order by customer_name,id limit 20) x),'[]'::jsonb) end,
    'document',case when v_doc is not null then (select jsonb_build_object('id',d.id,'number',d.document_number,'action',d.action,'status',d.status,
        'row_version',d.row_version::text,'payload',d.payload,'policy_versions',d.policy_versions,'reversal_reason',d.reversal_reason,
        'links',coalesce((select jsonb_agg(jsonb_build_object('kind',k.link_kind,'id',k.link_id) order by k.link_kind,k.link_id) from erp.bc_document_links_v1 k where k.document_id=d.id),'[]'::jsonb),
        'events',coalesce((select jsonb_agg(jsonb_build_object('id',e.id,'lot_id',e.lot_id,'kind',e.event_kind,'condition',e.condition,'qty',e.qty::text,
          'qty_usable',e.qty_usable::text,'qty_damaged',e.qty_damaged::text,'inspector',e.inspector,
          'amount',case when v_value or v_admin then e.amount::text end,'unpaid',case when v_value or v_admin then e.amount_unpaid::text end,
          'carry',case when v_value or v_admin then e.amount_carry::text end,'refund',case when v_value or v_admin then e.amount_refund::text end,
          'carry_remaining',case when (v_value or v_admin) and e.event_kind='CREDIT' and e.amount_carry>0 then erp.bc_carry_remaining_v1(e.id)::text end)
          order by e.created_at,e.id)
          from erp.bc_lot_events_v1 e where e.document_id=d.id),'[]'::jsonb),
        -- ACC-DEC05 carry: the draft payrolls of the same mandor that a carried credit may enter (owner/admin with payroll view).
        'carry_payrolls',case when v_admin and erp.has_permission('finance.payroll.view') then coalesce((select jsonb_agg(jsonb_build_object('id',p.id,
            'number',p.payroll_number,'status',p.status,'period_end',p.period_end::text) order by p.period_end desc,p.id)
          from erp.payroll_settlements p where p.status in('DRAFT','CALCULATED','REVIEW') and p.contractor_id in(
            select coalesce(l.contractor_id,(select c.contractor_id from erp.contractor_material_issues c join erp.contractor_material_issue_items i on i.issue_id=c.id
              where i.id=l.note_item_id)) from erp.bc_lot_events_v1 e join erp.bc_return_lots_v1 l on l.id=e.lot_id
            where e.document_id=d.id and e.event_kind='CREDIT' and e.amount_carry>0)),'[]'::jsonb) else '[]'::jsonb end)
      from erp.bc_documents_v1 d where d.id=v_doc) end,
    'card',v_card,
    -- Pick lists for the forms: accessories matching the search, cash accounts; for owner/admin the accounts, categories and
    -- users the policy settings name.
    'materials',coalesce((select jsonb_agg(jsonb_build_object('id',id,'sku',material_sku,'name',material_name,'unit',unit_code) order by material_name,id)
      from (select m.* from erp.materials m where m.material_type='ACCESSORY' and m.is_active
        and (v_query='' or strpos(lower(concat_ws(' ',m.material_sku,m.material_name)),v_query)>0) order by m.material_name,m.id limit 50) x),'[]'::jsonb),
    'cash_accounts',case when v_admin then coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',cash_account_name) order by cash_account_name,id)
      from erp.cash_accounts where is_active),'[]'::jsonb) end,
    'accounts',case when v_admin then coalesce((select jsonb_agg(jsonb_build_object('id',id,'code',account_code,'name',account_name,'type',account_type)
      order by account_code,id) from erp.chart_accounts where is_postable and is_active),'[]'::jsonb) end,
    'categories',case when v_admin then coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',category_name) order by category_name,id)
      from erp.accessory_categories where is_active),'[]'::jsonb) end,
    'users',case when v_admin then coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',full_name) order by full_name,id)
      from erp.app_users where is_active),'[]'::jsonb) end
  ) into v_result;
  return v_result;
end;$function$;

CREATE OR REPLACE FUNCTION public.erp_save_accessory_service_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.save_accessory_service_action_v1(p_action,p_payload,p_client_request_id) $function$;
CREATE OR REPLACE FUNCTION public.erp_get_accessory_service_workspace_v1(p_filters jsonb default '{}'::jsonb)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.get_accessory_service_workspace_v1(p_filters) $function$;

do $grants$
declare f text;
begin
  for f in select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      where n.nspname='erp' and (p.proname like 'bc\_%' or p.proname in('save_accessory_service_action_v1','get_accessory_service_workspace_v1')) loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
  end loop;
end $grants$;
revoke all on function public.erp_save_accessory_service_action_v1(text,jsonb,uuid) from public,anon;
revoke all on function public.erp_get_accessory_service_workspace_v1(jsonb) from public,anon;
grant execute on function public.erp_save_accessory_service_action_v1(text,jsonb,uuid) to authenticated,service_role;
grant execute on function public.erp_get_accessory_service_workspace_v1(jsonb) to authenticated,service_role;
CREATE OR REPLACE FUNCTION erp.post_material_adjustment(p_adjustment_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$ DECLARE h erp.material_adjustments%ROWTYPE;r record;v_type varchar(40);v_value numeric(24,6):=0; BEGIN PERFORM erp.require_internal(); SELECT * INTO h FROM erp.material_adjustments WHERE id=p_adjustment_id FOR UPDATE; IF h.id IS NULL OR h.status<>'DRAFT' THEN RAISE EXCEPTION 'Adjustment must be DRAFT'; END IF; IF h.location_id IS NULL THEN RAISE EXCEPTION 'Adjustment location is required'; END IF; v_type:=CASE h.reason_code WHEN 'PERSONAL_USE' THEN 'PERSONAL_USE' WHEN 'INTERNAL_FACTORY_USE' THEN 'INTERNAL_USE' WHEN 'SAMPLE' THEN 'SAMPLE' WHEN 'DAMAGE' THEN 'DAMAGE' WHEN 'LOSS' THEN 'LOSS' ELSE 'ADJUSTMENT' END; FOR r IN SELECT * FROM erp.material_adjustment_items WHERE adjustment_id=p_adjustment_id LOOP IF r.qty_signed>0 AND r.input_unit_cost IS NULL THEN RAISE EXCEPTION 'Positive material adjustment requires input_unit_cost'; END IF; INSERT INTO erp.material_stock_movements(material_id,roll_id,location_id,movement_type,qty_signed,input_unit_cost,source_type,source_id,physical_at,created_by) VALUES (r.material_id,r.roll_id,h.location_id,v_type,r.qty_signed,r.input_unit_cost,'MATERIAL_ADJUSTMENT_ITEM',r.id,h.physical_at,erp.current_app_user_id()); END LOOP; FOR r IN SELECT DISTINCT material_id FROM erp.material_adjustment_items WHERE adjustment_id=p_adjustment_id LOOP PERFORM erp.recalculate_material_cost(r.material_id); END LOOP; SELECT COALESCE(SUM(msm.qty_signed*msm.unit_cost_snapshot),0) INTO v_value FROM erp.material_stock_movements msm JOIN erp.material_adjustment_items mai ON mai.id=msm.source_id WHERE mai.adjustment_id=p_adjustment_id AND msm.source_type='MATERIAL_ADJUSTMENT_ITEM'; IF v_value<0 THEN PERFORM erp.post_journal('MATERIAL_ADJUSTMENT',h.id,erp._cp3_business_date(h.physical_at),'Material usage/adjustment',jsonb_build_array(jsonb_build_object('account_id',erp.bc_adjustment_account_v1(h.id,'OTHER_EXPENSE'),'debit',round(-v_value,2),'credit',0),jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',0,'credit',round(-v_value,2)))); ELSIF v_value>0 THEN PERFORM erp.post_journal('MATERIAL_ADJUSTMENT',h.id,erp._cp3_business_date(h.physical_at),'Positive material adjustment',jsonb_build_array(jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',round(v_value,2),'credit',0),jsonb_build_object('account_id',erp.bc_adjustment_account_v1(h.id,'OTHER_INCOME'),'debit',0,'credit',round(v_value,2)))); END IF; UPDATE erp.material_adjustments SET status='POSTED' WHERE id=p_adjustment_id; END; $function$;
CREATE OR REPLACE FUNCTION erp._cp6_material_adjustment_revaluation_state(p_adjustment uuid)
returns jsonb language sql stable security definer set search_path=erp,pg_catalog,pg_temp as $$
 with movements as(
  select m.*,exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id) reversed
  from erp.material_stock_movements m join erp.material_adjustment_items i on i.id=m.source_id
  where m.source_type='MATERIAL_ADJUSTMENT_ITEM' and m.reversal_of_id is null
    and i.adjustment_id=p_adjustment
 ), amounts as(
  select round(coalesce(sum(qty_signed*unit_cost_snapshot) filter(where not reversed),0),2) current_value,
    round(coalesce(sum(qty_signed*coalesce(original_unit_cost_snapshot,unit_cost_snapshot)) filter(where not reversed),0),2) original_value,
    count(*) filter(where not reversed and unit_cost_snapshot is null) incomplete_cost
  from movements
 ), desired as(
  -- BC: the purpose account of an adjustment posted by BC (erp.bc_adjustment_account_v1), else OTHER_EXPENSE/OTHER_INCOME.
  select case when mapping='MATERIAL_INVENTORY' then erp.account_id(mapping) else erp.bc_adjustment_account_v1(p_adjustment,mapping) end account_id,sum(amount) amount
  from amounts cross join lateral(values
   ('MATERIAL_INVENTORY',current_value-original_value),
   ('OTHER_EXPENSE',greatest(-current_value,0)-greatest(-original_value,0)),
   ('OTHER_INCOME',least(-current_value,0)-least(-original_value,0))
  ) values_by_account(mapping,amount)
  group by 1 having sum(amount)<>0
 ), originals as(
  select e.journal_entry_id from erp.material_cost_revaluation_events e
  join movements m on m.id=e.movement_id
  union
  select f.journal_entry_id from erp.material_adjustment_revaluation_facts f
  where f.adjustment_id=p_adjustment
 ), journals as(
  select journal_entry_id from originals
  union
  select j.id from erp.journal_entries j join originals o on j.reversal_of_id=o.journal_entry_id
 )
 select jsonb_build_object(
  'target',coalesce((select jsonb_object_agg(account_id::text,amount) from desired),'{}'::jsonb),
  'book',erp._cp6_supplier_cent_ledger((select array_agg(journal_entry_id) from journals)),
  'current_value',current_value,'original_value',original_value,'incomplete_cost',incomplete_cost
 ) from amounts
$$;
CREATE OR REPLACE FUNCTION erp._recalculate_material_cost_core(p_material_id uuid, p_recalc_from timestamp with time zone, p_allow_checkpoint boolean)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  r erp.material_stock_movements%rowtype;
  rr record;
  v_stock numeric(18,6):=0;
  v_avg numeric(18,6):=0;
  v_stock_before numeric(18,6);
  v_avg_before numeric(18,6);
  v_cost numeric(18,6);
  v_new_stock numeric(18,6);
  v_new_avg numeric(18,6);
  v_closed date;
  v_cp erp.material_cost_checkpoints%rowtype;
  v_use_checkpoint boolean:=false;
  v_cutoff timestamptz;
  v_transfer_pairs jsonb;
  v_transfer_rows bigint;
  v_transfer_pair_count bigint;
  v_location_minimum numeric;
  v_invoice_date date;
  v_queue record;
begin
  perform erp.require_internal();
  select closed_through into v_closed from erp.accounting_period_control where singleton_id=1 for share;
  perform 1 from erp.materials where id=p_material_id for update;
  if not found then raise exception 'Material not found'; end if;

  with active as (
    select m.*,row_number() over(partition by m.source_id,m.roll_id,m.physical_at,
        abs(m.qty_signed),m.movement_type order by m.system_created_at,m.id) ordinal
    from erp.material_stock_movements m
    where m.material_id=p_material_id and m.source_type='MATERIAL_TRANSFER'
      and m.reversal_of_id is null
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
  ), pairs as (
    select i.id incoming,o.id outgoing
    from active i join active o on o.source_id=i.source_id
      and o.roll_id is not distinct from i.roll_id and o.physical_at=i.physical_at
      and o.qty_signed=-i.qty_signed and o.ordinal=i.ordinal
      and o.movement_type='TRANSFER_OUT' and o.qty_signed<0
    where i.movement_type='TRANSFER_IN' and i.qty_signed>0
      and (o.physical_at,o.system_created_at,o.id)<(i.physical_at,i.system_created_at,i.id)
      and o.location_id<>i.location_id
  )
  select coalesce((select jsonb_object_agg(incoming::text,outgoing::text) from pairs),'{}'::jsonb),
    (select count(*) from active),(select count(*) from pairs)
  into v_transfer_pairs,v_transfer_rows,v_transfer_pair_count;
  if v_transfer_rows<>2*v_transfer_pair_count then
    raise exception 'AM_TRANSFER_PAIR_LINEAGE_UNPROVEN for material %',p_material_id;
  end if;

  -- The cost engine excludes a source and its linked inverse together. Apply
  -- the identical effective-history rule at each physical location/roll too;
  -- this preserves atomic receipt replacement and existing cancellation rules.
  select min(prefix) into v_location_minimum from (
    select sum(m.qty_signed) over(partition by m.location_id,m.roll_id
      order by m.physical_at,coalesce(o.system_created_at,m.system_created_at),
        coalesce(o.id,m.id),(o.id is not null) rows unbounded preceding) prefix
    from erp.material_stock_movements m
    left join erp.material_stock_movements o on o.id=(v_transfer_pairs->>m.id::text)::uuid
    where m.material_id=p_material_id and m.reversal_of_id is null
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
  ) effective_history;
  if v_location_minimum<0 then
    raise exception 'AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY for material %',p_material_id;
  end if;

  if p_allow_checkpoint and p_recalc_from is not null and v_closed is not null then
    select * into v_cp from erp.material_cost_checkpoints where material_id=p_material_id;
    if v_cp.material_id is not null
       and v_cp.checkpoint_date<=v_closed
       and erp._cp3_business_date(p_recalc_from)>v_cp.checkpoint_date then
      v_cutoff:=((v_cp.checkpoint_date+1)::timestamp at time zone 'Asia/Jakarta');

  if exists(
    with history as (
      select msm.id,msm.qty_signed,msm.unit_cost_snapshot,msm.movement_type,msm.source_type,
        h.movement_id,h.stock_before,h.stock_after,h.average_before,h.average_after,
        h.movement_qty,h.movement_unit_cost,paired_out.unit_cost_snapshot paired_cost,
        sum(msm.qty_signed) over w expected_stock,
        lag(h.average_after,1,0::numeric) over w previous_average
      from erp.material_stock_movements msm
      left join erp.material_cost_history h on h.movement_id=msm.id and h.material_id=msm.material_id
      left join erp.material_stock_movements paired_out on paired_out.id=(v_transfer_pairs->>msm.id::text)::uuid
      where msm.material_id=p_material_id and msm.physical_at<v_cutoff
        and msm.reversal_of_id is null
        and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id)
      window w as(order by msm.physical_at,coalesce(paired_out.system_created_at,msm.system_created_at),
        coalesce(paired_out.id,msm.id),(paired_out.id is not null) rows unbounded preceding)
    )
    select 1 from history where movement_id is null
      or movement_qty is distinct from qty_signed
      or movement_unit_cost is distinct from unit_cost_snapshot
      or stock_before is distinct from expected_stock-qty_signed
      or stock_after is distinct from expected_stock
      or average_before is distinct from previous_average
      or (qty_signed<0 and movement_unit_cost is distinct from average_before)
      or (movement_type='TRANSFER_IN' and source_type='MATERIAL_TRANSFER'
          and movement_unit_cost is distinct from paired_cost)
      or average_after is distinct from case
        when stock_after=0 then 0
        when qty_signed<0 then average_before
        else round((stock_before*average_before+qty_signed*movement_unit_cost)/nullif(stock_after,0),6)
      end
  ) then
    raise exception 'AM_LEGACY_COST_CHECKPOINT_REQUIRES_HISTORY_REVIEW for material %',p_material_id;
  end if;

      v_use_checkpoint:=true;
      v_stock:=v_cp.stock_qty;
      v_avg:=v_cp.moving_average_cost;
    end if;
  end if;

  if v_use_checkpoint then
    if v_cp.last_movement_id is null then
      delete from erp.material_cost_history where material_id=p_material_id;
    else
      delete from erp.material_cost_history h
      using erp.material_stock_movements msm
      where h.material_id=p_material_id and h.movement_id=msm.id
        and erp._cp3_business_date(msm.physical_at)>v_cp.checkpoint_date;
    end if;
  else
    delete from erp.material_cost_history where material_id=p_material_id;
  end if;

  for r in
    select msm.* from erp.material_stock_movements msm
  left join erp.material_stock_movements paired_out
    on paired_out.id=(v_transfer_pairs->>msm.id::text)::uuid
    where msm.material_id=p_material_id
      and msm.reversal_of_id is null
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id)
      and (
        not v_use_checkpoint
        or v_cp.last_movement_id is null
        or erp._cp3_business_date(msm.physical_at)>v_cp.checkpoint_date
      )
    order by msm.physical_at,coalesce(paired_out.system_created_at,msm.system_created_at),
      coalesce(paired_out.id,msm.id),(paired_out.id is not null)
    for update of msm
  loop
    v_stock_before:=v_stock;
    v_avg_before:=v_avg;
    if r.qty_signed>0 then
      if r.movement_type='TRANSFER_IN' and r.source_type='MATERIAL_TRANSFER' then
        -- The paired OUT must already have been replayed (or retained by the
        -- closed-period checkpoint). Its historical cost is the incoming cost,
        -- including a transfer of the entire balance that temporarily hits 0.
        select o.unit_cost_snapshot into v_cost
        from erp.material_stock_movements o
        join erp.material_cost_history h on h.movement_id=o.id and h.material_id=o.material_id
        where o.id=(v_transfer_pairs->>r.id::text)::uuid and o.material_id=p_material_id
          and o.is_cost_recalculated;
        if not found or v_cost is null then
          raise exception 'AM_TRANSFER_OUT_COST_NOT_REPLAYED for movement %',r.id;
        end if;
      elsif r.movement_type='REVERSAL' and r.reversal_of_id is not null then
        select x.unit_cost_snapshot into v_cost from erp.material_stock_movements x where x.id=r.reversal_of_id;
        v_cost:=coalesce(v_cost,r.input_unit_cost,r.unit_cost_snapshot,v_avg);
      elsif r.source_type='BC_NOTE_RETURN_CREDIT' then
        -- BC: a credited mandor note return comes back at the issue cost of its note line (like a cutting return).
        select x.unit_cost_snapshot into v_cost from erp.material_stock_movements x where x.id=erp.bc_note_return_issue_movement_v1(r.source_id);
        v_cost:=coalesce(v_cost,r.input_unit_cost,r.unit_cost_snapshot,v_avg);
      elsif r.movement_type='CUTTING_RETURN' and r.source_type='CUTTING_GROUP_RETURN' then
        select x.unit_cost_snapshot into v_cost
        from erp.material_stock_movements x
        where x.material_id=r.material_id
          and x.source_type='CUTTING_GROUP' and x.source_id=r.source_id
          and x.movement_type='CUTTING_ISSUE'
          and x.roll_id is not distinct from r.roll_id
        order by x.physical_at desc,x.system_created_at desc,x.id desc limit 1;
        v_cost:=coalesce(v_cost,r.input_unit_cost,r.unit_cost_snapshot,v_avg);
      else
        v_cost:=coalesce(r.input_unit_cost,r.unit_cost_snapshot,v_avg);
      end if;
      v_new_stock:=v_stock+r.qty_signed;
      if v_new_stock>0 then
        v_new_avg:=((v_stock*v_avg)+(r.qty_signed*v_cost))/v_new_stock;
      else
        v_new_avg:=0;
      end if;
    else
      v_new_stock:=v_stock+r.qty_signed;
      if v_new_stock<0 then
        raise exception 'Backdate/correction would create negative material stock for material %, movement %',p_material_id,r.id;
      end if;
      v_cost:=v_avg;
      v_new_avg:=case when v_new_stock=0 then 0 else v_avg end;
    end if;

    update erp.material_stock_movements
    set original_unit_cost_snapshot=coalesce(original_unit_cost_snapshot,v_cost),
        unit_cost_snapshot=v_cost,
        is_cost_recalculated=true
    where id=r.id;

    insert into erp.material_cost_history(material_id,movement_id,physical_at,stock_before,average_before,movement_qty,movement_unit_cost,stock_after,average_after)
    values(p_material_id,r.id,r.physical_at,v_stock_before,v_avg_before,r.qty_signed,v_cost,v_new_stock,v_new_avg);
    v_stock:=v_new_stock;
    v_avg:=v_new_avg;
  end loop;

  for rr in
    select mr.id as roll_id,coalesce(sum(msm.qty_signed),0)::numeric as roll_qty
    from erp.material_rolls mr
    left join erp.material_stock_movements msm on msm.roll_id=mr.id
    where mr.material_id=p_material_id
    group by mr.id
  loop
    if rr.roll_qty<0 then raise exception 'Correction would create negative roll stock for roll %',rr.roll_id; end if;
    update erp.material_rolls
    set cached_qty=rr.roll_qty,
        status=case when rr.roll_qty=0 then 'EXHAUSTED' when rr.roll_qty<original_qty then 'HALF_USED' else 'AVAILABLE' end,
        updated_at=statement_timestamp()
    where id=rr.roll_id and status<>'RETURNED_SUPPLIER';
  end loop;

  update erp.cutting_group_rolls cgr
  set unit_cost_snapshot=(
    select msm.unit_cost_snapshot
    from erp.material_stock_movements msm
    where msm.material_id=p_material_id and msm.source_type='CUTTING_GROUP'
      and msm.source_id=cgr.cutting_group_id and msm.movement_type='CUTTING_ISSUE'
      and msm.roll_id is not distinct from cgr.roll_id
    order by msm.physical_at desc,msm.system_created_at desc,msm.id desc limit 1
  )
  where exists(
    select 1 from erp.material_stock_movements msm
    where msm.material_id=p_material_id and msm.source_type='CUTTING_GROUP'
      and msm.source_id=cgr.cutting_group_id and msm.movement_type='CUTTING_ISSUE'
      and msm.roll_id is not distinct from cgr.roll_id
  );

  update erp.contractor_material_issue_items ii
  set unit_cost_snapshot=(
    select msm.unit_cost_snapshot from erp.material_stock_movements msm
    where msm.material_id=p_material_id and msm.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM'
      and msm.source_id=ii.id and msm.movement_type='CONTRACTOR_ISSUE'
    order by msm.physical_at desc,msm.system_created_at desc,msm.id desc limit 1
  )
  where ii.material_id=p_material_id and exists(
    select 1 from erp.material_stock_movements msm
    where msm.material_id=p_material_id and msm.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM'
      and msm.source_id=ii.id and msm.movement_type='CONTRACTOR_ISSUE'
  );

  update erp.materials set cached_stock_qty=v_stock,moving_average_cost=v_avg,updated_at=statement_timestamp() where id=p_material_id;

  perform erp.sync_material_cost_revaluation(p_material_id);

  insert into erp.cost_recalc_queue(entity_type,entity_id,recalc_from,reason)
  select distinct 'PO',cg.po_id,min(msm.physical_at),'Material moving-average/backdate recalculation'
  from erp.material_stock_movements msm
  join erp.cutting_groups cg on msm.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') and msm.source_id=cg.id
  where msm.material_id=p_material_id
    and exists(select 1 from erp.fg_lots fl where fl.po_id=cg.po_id)
    and not exists(select 1 from erp.cost_recalc_queue q where q.entity_type='PO' and q.entity_id=cg.po_id and (q.status in('PENDING','RUNNING') or (q.status='FAILED' and q.attempt_count<3)))
  group by cg.po_id;

  insert into erp.cost_recalc_queue(entity_type,entity_id,recalc_from,reason)
  select distinct 'PO',cmi.po_id,min(msm.physical_at),'Contractor material moving-average/backdate recalculation'
  from erp.material_stock_movements msm
  join erp.contractor_material_issue_items ii on msm.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and msm.source_id=ii.id
  join erp.contractor_material_issues cmi on cmi.id=ii.issue_id
  where msm.material_id=p_material_id and cmi.po_id is not null
    and exists(select 1 from erp.fg_lots fl where fl.po_id=cmi.po_id)
    and not exists(select 1 from erp.cost_recalc_queue q where q.entity_type='PO' and q.entity_id=cmi.po_id and (q.status in('PENDING','RUNNING') or (q.status='FAILED' and q.attempt_count<3)))
  group by cmi.po_id;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('materials',p_material_id,'RECALCULATE',jsonb_build_object('cached_stock_qty',v_stock,'moving_average_cost',v_avg,'original_movement_snapshots_preserved',true,'gl_revaluation_synced',true,'checkpoint_used',v_use_checkpoint,'recalc_from',p_recalc_from),erp.current_app_user_id(),'Material chronological moving-average recalculation');

  perform erp.refresh_accessory_hpp_after_material_recost(p_material_id,'Material chronological moving-average recalculation');

  v_invoice_date:=erp.invoice_recost_economic_date_v1();
  if v_invoice_date is not null then
    for v_queue in
      select q.* from erp.cost_recalc_queue q where q.entity_type='PO'
        and q.status in('PENDING','FAILED')
        and q.entity_id in(
          select cg.po_id from erp.cutting_groups cg join erp.material_stock_movements m
            on m.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') and m.source_id=cg.id where m.material_id=p_material_id
          union select i.po_id from erp.contractor_material_issues i join erp.contractor_material_issue_items l on l.issue_id=i.id
            where l.material_id=p_material_id and i.po_id is not null
        ) order by q.entity_id,q.queued_at,q.id for update
    loop
      perform erp.rebuild_po_hpp(v_queue.entity_id,v_queue.reason);
      perform erp.propagate_conversion_hpp_for_po(v_queue.entity_id);
      perform erp.sync_po_hpp_to_gl(v_queue.entity_id,v_invoice_date);
      if exists(select 1 from erp.production_orders where id=v_queue.entity_id and status='FINISHED') then
        perform erp.sync_finished_po_wip_residual(v_queue.entity_id,v_invoice_date,'Invoice-date material correction');
      end if;
      update erp.cost_recalc_queue set status='DONE',started_at=statement_timestamp(),completed_at=statement_timestamp(),
        last_attempt_at=statement_timestamp(),attempt_count=attempt_count+1,error_message=null,next_attempt_at=null where id=v_queue.id;
    end loop;
  end if;

  if not v_use_checkpoint and v_closed is not null then
    perform erp.refresh_material_cost_checkpoint(p_material_id,v_closed);
  end if;
end;
$function$;
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
end;
$function$;
CREATE OR REPLACE FUNCTION erp.populate_payroll_draft(p_payroll_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  p erp.payroll_settlements%rowtype;
  r record;
  v_remaining numeric(24,6);
  v_apply numeric(24,6);
  v_budget numeric(24,6) := 0;
  v_attendance_required boolean;
begin
  perform erp.require_internal();
  select * into p from erp.payroll_settlements where id = p_payroll_id for update;
  if p.id is null or p.status not in ('DRAFT','CALCULATED','REVIEW') then
    raise exception 'Payroll draft cannot be rebuilt in current status';
  end if;
  perform pg_advisory_xact_lock(hashtextextended(p.contractor_id::text, 0));

  delete from erp.payroll_work_items where payroll_id = p.id;
  delete from erp.payroll_attendance_items where payroll_id = p.id;
  delete from erp.payroll_deductions
    where payroll_id = p.id and contractor_issue_item_id is not null;
  delete from erp.payroll_reimbursements
    where payroll_id = p.id and source_type = 'ACCESSORY_BOM';

  insert into erp.payroll_work_items(
    payroll_id, po_id, work_component_id, source_type, source_id,
    qty_payable, rate_snapshot
  )
  select p.id, e.po_id, e.work_component_id, e.source_type, e.source_id,
         e.remaining_qty, e.rate_snapshot
  from erp.v_payroll_eligible_work_lines e
  where e.contractor_id = p.contractor_id
    and (e.eligible_at AT TIME ZONE 'Asia/Jakarta')::date <= p.period_end
    and e.remaining_qty > 0
  order by e.eligible_at, e.source_type, e.source_id;

  select attendance_required into v_attendance_required
  from erp.contractors where id = p.contractor_id;

  if v_attendance_required then
    insert into erp.payroll_attendance_items(
      payroll_id, worker_id, attendance_record_id,
      paid_fraction_snapshot, daily_rate_snapshot,
      worker_rate_version_id, attendance_date_snapshot,
      worker_name_snapshot, job_description_snapshot
    )
    select
      p.id,
      ar.worker_id,
      ar.id,
      ar.paid_fraction,
      erp.require_worker_daily_rate_at(ar.worker_id, ar.attendance_date),
      erp.worker_daily_rate_version_id_at(ar.worker_id, ar.attendance_date),
      ar.attendance_date,
      cw.worker_name,
      cw.job_description
    from erp.attendance_records ar
    join erp.contractor_workers cw on cw.id = ar.worker_id
    left join erp.attendance_periods ap on ap.id = ar.attendance_period_id
    where ar.contractor_id = p.contractor_id
      and ar.attendance_date between p.period_start and p.period_end
      and cw.pay_scheme in ('DAILY','HYBRID')
      and ar.paid_fraction > 0
      and (ar.attendance_period_id is null or ap.status = 'POSTED')
      and coalesce(ar.record_lifecycle, 'POSTED') = 'POSTED'
    order by ar.attendance_date, ar.id;
  end if;

  insert into erp.payroll_reimbursements(
    payroll_id, amount, description, source_type, source_id, po_id
  )
  select p.id, round(e.amount, 2),
         'Accessory reimbursement from accepted GOOD FG',
         'ACCESSORY_BOM', e.id, e.po_id
  from erp.contractor_accessory_reimbursement_entitlements e
  where e.contractor_id = p.contractor_id
    and e.amount > 0
    and e.payroll_status <> 'CANCELLED'
    and (e.physical_at AT TIME ZONE 'Asia/Jakarta')::date <= p.period_end
    and not exists (
      select 1
      from erp.payroll_reimbursements pr
      join erp.payroll_settlements ps2 on ps2.id = pr.payroll_id
      where pr.source_type = 'ACCESSORY_BOM'
        and pr.source_id = e.id
        and ps2.id <> p.id
        and ps2.status <> 'REVERSED'
    )
  order by e.physical_at, e.id;

  update erp.contractor_accessory_reimbursement_entitlements e
  set payroll_status = 'ALLOCATED'
  where exists (
    select 1
    from erp.payroll_reimbursements pr
    where pr.payroll_id = p.id
      and pr.source_type = 'ACCESSORY_BOM'
      and pr.source_id = e.id
  );

  perform erp.recalculate_payroll(p.id);
  select greatest(net_payable, 0) into v_budget
  from erp.payroll_settlements where id = p.id;

  for r in
    select
      cmii.id,
      cmii.total_receivable,
      cmi.physical_at,
      erp.bc_note_item_collectible_v1(cmii.id) - coalesce((
        select sum(pd.amount)
        from erp.payroll_deductions pd
        join erp.payroll_settlements ps2 on ps2.id = pd.payroll_id
        where pd.contractor_issue_item_id = cmii.id
          and ps2.id <> p.id
          and ps2.status <> 'REVERSED'
      ), 0) as remaining_amount
    from erp.contractor_material_issue_items cmii
    join erp.contractor_material_issues cmi on cmi.id = cmii.issue_id
    where cmi.contractor_id = p.contractor_id
      and cmi.status = 'POSTED'
      and (cmi.physical_at AT TIME ZONE 'Asia/Jakarta')::date <= p.period_end
    order by cmi.physical_at, cmii.id
  loop
    exit when v_budget <= 0;
    v_remaining := greatest(r.remaining_amount, 0);
    v_apply := least(v_remaining, v_budget);
    if v_apply > 0 then
      insert into erp.payroll_deductions(
        payroll_id, deduction_type, contractor_issue_item_id, amount, notes
      ) values (
        p.id, 'MATERIAL_KASBON', r.id, round(v_apply, 2),
        'Auto capped outstanding material/accessory kasbon (FIFO)'
      );
      v_budget := greatest(v_budget - round(v_apply, 2), 0);
    end if;
  end loop;

  perform erp.recalculate_payroll(p.id);
  for r in
    select cmii.id
    from erp.contractor_material_issue_items cmii
    join erp.contractor_material_issues cmi on cmi.id = cmii.issue_id
    where cmi.contractor_id = p.contractor_id
      and cmi.status = 'POSTED'
  loop
    perform erp.refresh_contractor_issue_payroll_status(r.id);
  end loop;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.validate_material_kasbon_deduction()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_payroll_contractor uuid;v_issue_contractor uuid;v_total numeric(24,6);v_already_item numeric(24,6):=0;
  v_labor numeric(24,6):=0;v_attendance numeric(24,6):=0;v_reimburse numeric(24,6):=0;v_manual numeric(24,6):=0;
  v_other_deduction numeric(24,6):=0;v_material_current numeric(24,6):=0;v_available numeric(24,6):=0;
begin
  if new.deduction_type<>'MATERIAL_KASBON' then return new; end if;
  if new.contractor_issue_item_id is null then raise exception 'MATERIAL_KASBON deduction requires contractor issue item'; end if;
  if new.amount is null or new.amount<=0 then raise exception 'MATERIAL_KASBON deduction amount must be positive'; end if;
  perform pg_advisory_xact_lock(hashtextextended('PAYKASBON|'||new.contractor_issue_item_id::text,0));
  select ps.contractor_id,ps.manual_adjustment into v_payroll_contractor,v_manual from erp.payroll_settlements ps where ps.id=new.payroll_id;
  select cmi.contractor_id,erp.bc_note_item_collectible_v1(cmii.id) into v_issue_contractor,v_total
  from erp.contractor_material_issue_items cmii join erp.contractor_material_issues cmi on cmi.id=cmii.issue_id
  where cmii.id=new.contractor_issue_item_id;
  if v_issue_contractor is null or v_issue_contractor is distinct from v_payroll_contractor then raise exception 'Kasbon item contractor does not match payroll contractor'; end if;
  select coalesce(sum(pd.amount),0) into v_already_item
  from erp.payroll_deductions pd join erp.payroll_settlements ps on ps.id=pd.payroll_id
  where pd.contractor_issue_item_id=new.contractor_issue_item_id and pd.deduction_type='MATERIAL_KASBON'
    and pd.id<>new.id and ps.status<>'REVERSED';
  if v_already_item+new.amount>v_total+0.01 then raise exception 'Kasbon deduction exceeds outstanding receivable. Total %, already allocated %, requested %',v_total,v_already_item,new.amount; end if;
  select coalesce(sum(amount),0) into v_labor from erp.payroll_work_items where payroll_id=new.payroll_id;
  select coalesce(sum(amount),0) into v_attendance from erp.payroll_attendance_items where payroll_id=new.payroll_id;
  select coalesce(sum(amount),0) into v_reimburse from erp.payroll_reimbursements where payroll_id=new.payroll_id;
  select coalesce(sum(amount),0) into v_other_deduction from erp.payroll_deductions where payroll_id=new.payroll_id and deduction_type<>'MATERIAL_KASBON' and id<>new.id;
  select coalesce(sum(amount),0) into v_material_current from erp.payroll_deductions where payroll_id=new.payroll_id and deduction_type='MATERIAL_KASBON' and id<>new.id;
  v_available:=greatest(v_labor+v_attendance+v_reimburse+coalesce(v_manual,0)-v_other_deduction-v_material_current,0);
  if new.amount>v_available+0.01 then raise exception 'Kasbon deduction is capped by available payroll earnings. Available %, requested %',v_available,new.amount; end if;
  return new;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.refresh_contractor_issue_payroll_status(p_item_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
DECLARE
  v_total numeric(24,6);
  v_paid numeric(24,6):=0;
  v_allocated numeric(24,6):=0;
  v_status varchar(20);
BEGIN
  PERFORM erp.require_internal();
  SELECT erp.bc_note_item_collectible_v1(id) INTO v_total
  FROM erp.contractor_material_issue_items WHERE id=p_item_id FOR UPDATE;
  IF NOT FOUND THEN RETURN; END IF;

  SELECT
    COALESCE(SUM(CASE WHEN ps.status='PAID' THEN pd.amount ELSE 0 END),0),
    COALESCE(SUM(CASE WHEN ps.status<>'REVERSED' THEN pd.amount ELSE 0 END),0)
  INTO v_paid,v_allocated
  FROM erp.payroll_deductions pd
  JOIN erp.payroll_settlements ps ON ps.id=pd.payroll_id
  WHERE pd.contractor_issue_item_id=p_item_id
    AND pd.deduction_type='MATERIAL_KASBON';

  v_status:=CASE
    WHEN v_total<=0 OR v_paid>=v_total-0.01 THEN 'SETTLED'
    WHEN v_paid>0 THEN 'PARTIAL'
    WHEN v_allocated>0 THEN 'ALLOCATED'
    ELSE 'UNALLOCATED'
  END;

  UPDATE erp.contractor_material_issue_items
  SET payroll_status=v_status
  WHERE id=p_item_id;
END;
$function$;
CREATE OR REPLACE FUNCTION erp.run_integrity_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
BEGIN
  PERFORM erp.require_owner_admin();

  RETURN QUERY SELECT 'UNBALANCED_POSTED_JOURNALS','ERROR',COUNT(*)::bigint,'Posted journals where total debit differs from total credit'
  FROM (SELECT je.id FROM erp.journal_entries je JOIN erp.journal_lines jl ON jl.journal_entry_id=je.id WHERE je.status='POSTED' GROUP BY je.id HAVING ABS(SUM(jl.debit)-SUM(jl.credit))>0.01) x;

  RETURN QUERY SELECT 'NEGATIVE_MATERIAL_LOCATION_BALANCE','ERROR',COUNT(*)::bigint,'Material/location/roll balances below zero'
  FROM (SELECT material_id,location_id,roll_id FROM erp.material_stock_movements GROUP BY material_id,location_id,roll_id HAVING SUM(qty_signed)<-0.000001) x;

  RETURN QUERY SELECT 'NEGATIVE_FG_BALANCE','ERROR',COUNT(*)::bigint,'Finished-goods product/location/grade balances below zero'
  FROM (SELECT product_id,location_id,quality_grade FROM erp.fg_stock_movements GROUP BY product_id,location_id,quality_grade HAVING SUM(qty_signed)<0) x;

  RETURN QUERY SELECT 'FG_CACHE_MISMATCH','ERROR',COUNT(*)::bigint,'FG cache differs from ledger source of truth'
  FROM (SELECT COALESCE(l.product_id,c.product_id) product_id,COALESCE(l.location_id,c.location_id) location_id,COALESCE(l.quality_grade,c.quality_grade) quality_grade FROM (SELECT product_id,location_id,quality_grade,SUM(qty_signed)::bigint qty FROM erp.fg_stock_movements GROUP BY product_id,location_id,quality_grade) l FULL JOIN erp.fg_inventory_balances c ON c.product_id=l.product_id AND c.location_id=l.location_id AND c.quality_grade=l.quality_grade WHERE COALESCE(l.qty,0)<>COALESCE(c.cached_qty_pcs,0)) x;

  RETURN QUERY SELECT 'DUPLICATE_CURRENT_HPP','ERROR',COUNT(*)::bigint,'Lots with more than one current HPP version'
  FROM (SELECT lot_id FROM erp.hpp_versions WHERE is_current GROUP BY lot_id HAVING COUNT(*)>1) x;

  RETURN QUERY SELECT 'LAUNDRY_OVER_RETURN','ERROR',COUNT(*)::bigint,'Cumulative GOOD+BS laundry returns exceed sent quantity'
  FROM (SELECT ldl.id FROM erp.laundry_delivery_lines ldl LEFT JOIN erp.laundry_receipt_lines lrl ON lrl.delivery_line_id=ldl.id LEFT JOIN erp.laundry_receipts lr ON lr.id=lrl.receipt_id AND lr.status<>'REVERSED' GROUP BY ldl.id,ldl.qty_sent_pcs HAVING COALESCE(SUM(CASE WHEN lr.id IS NOT NULL THEN lrl.qty_good_received+lrl.qty_bs_laundry ELSE 0 END),0)>ldl.qty_sent_pcs) x;

  RETURN QUERY SELECT 'QC_SOURCE_OVER_ALLOCATION','ERROR',COUNT(*)::bigint,'QC GOOD+BS exceeds its posted laundry GOOD source'
  FROM (SELECT lrl.id FROM erp.laundry_receipt_lines lrl JOIN erp.laundry_receipts lr ON lr.id=lrl.receipt_id LEFT JOIN erp.qc_inspection_items qii ON qii.source_laundry_receipt_line_id=lrl.id LEFT JOIN erp.qc_inspections qi ON qi.id=qii.inspection_id AND qi.status<>'REVERSED' WHERE lr.status='POSTED' GROUP BY lrl.id,lrl.qty_good_received HAVING COALESCE(SUM(CASE WHEN qi.id IS NOT NULL THEN qii.qty_good_pcs+qii.qty_bs_pcs ELSE 0 END),0)>lrl.qty_good_received) x;

  RETURN QUERY SELECT 'PAYROLL_ATTENDANCE_DUPLICATE','ERROR',COUNT(*)::bigint,'Same attendance record allocated to multiple non-reversed payrolls'
  FROM (SELECT pai.attendance_record_id FROM erp.payroll_attendance_items pai JOIN erp.payroll_settlements ps ON ps.id=pai.payroll_id WHERE ps.status<>'REVERSED' GROUP BY pai.attendance_record_id HAVING COUNT(*)>1) x;

  RETURN QUERY SELECT 'REWORK_PAYROLL_BEFORE_COST_POST','ERROR',COUNT(*)::bigint,'Rework payroll item references rework whose production cost is not posted'
  FROM erp.payroll_work_items pwi JOIN erp.rework_component_lines rcl ON rcl.id=pwi.source_id JOIN erp.rework_orders ro ON ro.id=rcl.rework_order_id JOIN erp.payroll_settlements ps ON ps.id=pwi.payroll_id WHERE pwi.source_type='REWORK' AND ps.status<>'REVERSED' AND COALESCE(ro.cost_posted,false)=false;

  RETURN QUERY SELECT 'PAYROLL_PAID_NEGATIVE_NET','ERROR',COUNT(*)::bigint,'A paid payroll must never have negative net payable'
  FROM erp.payroll_settlements WHERE status='PAID' AND net_payable<0;

  RETURN QUERY SELECT 'KASBON_PAID_OVERSETTLED','ERROR',COUNT(*)::bigint,'Paid payroll deductions exceed original contractor receivable'
  FROM (
    SELECT cmii.id
    FROM erp.contractor_material_issue_items cmii
    LEFT JOIN erp.payroll_deductions pd ON pd.contractor_issue_item_id=cmii.id AND pd.deduction_type='MATERIAL_KASBON'
    LEFT JOIN erp.payroll_settlements ps ON ps.id=pd.payroll_id AND ps.status='PAID'
    GROUP BY cmii.id,cmii.total_receivable
    HAVING COALESCE(SUM(CASE WHEN ps.id IS NOT NULL THEN pd.amount ELSE 0 END),0)>erp.bc_note_item_collectible_v1(cmii.id)+0.01
  ) x;

  RETURN QUERY SELECT 'KASBON_STATUS_MISMATCH','ERROR',COUNT(*)::bigint,'Kasbon status differs from amount actually paid/allocated'
  FROM (
    SELECT cmii.id,cmii.payroll_status,erp.bc_note_item_collectible_v1(cmii.id) total_receivable,
      COALESCE(SUM(CASE WHEN ps.status='PAID' THEN pd.amount ELSE 0 END),0) paid_amt,
      COALESCE(SUM(CASE WHEN ps.status<>'REVERSED' THEN pd.amount ELSE 0 END),0) allocated_amt
    FROM erp.contractor_material_issue_items cmii
    LEFT JOIN erp.payroll_deductions pd ON pd.contractor_issue_item_id=cmii.id AND pd.deduction_type='MATERIAL_KASBON'
    LEFT JOIN erp.payroll_settlements ps ON ps.id=pd.payroll_id
    GROUP BY cmii.id,cmii.payroll_status,cmii.total_receivable
  ) s
  WHERE s.payroll_status IS DISTINCT FROM CASE
    WHEN s.total_receivable<=0 OR s.paid_amt>=s.total_receivable-0.01 THEN 'SETTLED'
    WHEN s.paid_amt>0 THEN 'PARTIAL'
    WHEN s.allocated_amt>0 THEN 'ALLOCATED'
    ELSE 'UNALLOCATED' END;

  RETURN QUERY SELECT 'REWORK_COMPLETION_UNRECONCILED','ERROR',COUNT(*)::bigint,'Completed rework must have GOOD + BS exactly equal to qty sent'
  FROM erp.rework_orders WHERE status='COMPLETED' AND qty_good_returned+qty_bs_returned<>qty_sent;

  RETURN QUERY SELECT 'REWORK_GOOD_WITHOUT_FG','ERROR',COUNT(*)::bigint,'Posted completed rework with GOOD output must have an FG lot'
  FROM erp.rework_orders WHERE status='COMPLETED' AND cost_posted=true AND qty_good_returned>0 AND good_fg_lot_id IS NULL;

  RETURN QUERY SELECT 'REWORK_FG_QTY_MISMATCH','ERROR',COUNT(*)::bigint,'Rework GOOD qty must equal REWORK_IN FG ledger qty'
  FROM erp.rework_orders ro
  WHERE ro.cost_posted=true AND ro.qty_good_returned>0
    AND COALESCE((SELECT SUM(fsm.qty_signed) FROM erp.fg_stock_movements fsm WHERE fsm.lot_id=ro.good_fg_lot_id AND fsm.movement_type='REWORK_IN'),0)<>ro.qty_good_returned;

  RETURN QUERY SELECT 'BS_RESOLUTION_OVER_QTY','ERROR',COUNT(*)::bigint,'Resolved BS quantity cannot exceed original BS case quantity'
  FROM (SELECT bc.id FROM erp.bs_cases bc LEFT JOIN erp.bs_resolutions br ON br.bs_case_id=bc.id GROUP BY bc.id,bc.qty_pcs HAVING COALESCE(SUM(br.qty_pcs),0)>bc.qty_pcs) x;

  RETURN QUERY SELECT 'STALE_RECOST_QUEUE','WARN',COUNT(*)::bigint,'Recost queue has PENDING/RUNNING work older than 10 minutes'
  FROM erp.cost_recalc_queue WHERE status IN ('PENDING','RUNNING') AND queued_at<statement_timestamp()-interval '10 minutes';

  RETURN QUERY SELECT 'FAILED_RECOST_QUEUE','WARN',COUNT(*)::bigint,'Cost recalculation jobs exhausted or awaiting retry'
  FROM erp.cost_recalc_queue WHERE status='FAILED';
END;
$function$;
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
  perform erp.bb_check_opening_payable_payroll_v1(p.id);
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
  -- BB (ALL-Y01): an imported contractor payable was recognized at cutover; paying it through payroll accrues nothing again.
  -- BC: a carried note return credit was recognized as CONTRACTOR_PAYABLE at the credit.
  where payroll_id=p.id and source_type not in('ACCESSORY_BOM','OPENING_PAYABLE','BC_RETURN_CARRY');
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
create or replace function erp.save_accessory_issue_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
returns jsonb language plpgsql security definer set search_path='' set TimeZone='UTC' as $function$
declare v_action text:=upper(btrim(p_action));v_cached jsonb;v_result jsonb;v_native jsonb;v_line jsonb;v_quote jsonb;v_free jsonb;
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
   perform erp._cp3_assert_closed_json_object(v_line,array['material_id','qty','mode'],array['material_id','qty','mode','manual_price','price_version_id','factor','free_policy_version'],'accessory issue line');
   if jsonb_typeof(v_line->'qty') is distinct from 'string' or (v_line->>'qty')!~'^[1-9][0-9]{0,11}$' then raise exception 'Jumlah aksesori harus PCS utuh positif';end if;
   v_quote:=erp.accessory_issue_quote_v1((v_line->>'material_id')::uuid,v_contractor,v_at);
   if v_quote is null then raise exception 'Aksesori hitung aktif tidak ditemukan';end if;
   if v_line->>'mode'='MANUAL' then
    if jsonb_typeof(v_line->'manual_price') is distinct from 'string' or (v_line->>'manual_price')!~'^[0-9]{1,12}(\.[0-9]{1,2})?$' then raise exception 'Harga eceran wajib nominal nonnegatif, maksimal dua desimal';end if;
    -- BC (M:5023, ERP-DEC02): a price of 0 is free; free is never a way around the note price, only an owner-listed Special category.
    if (v_line->>'manual_price')::numeric=0 then raise exception 'BC_FREE_REQUIRES_POLICY: harga eceran 0 hanya lewat gratis Special yang ditetapkan owner (ERP-DEC02)';end if;
    v_items:=v_items||jsonb_build_array(jsonb_build_object('material_id',v_line->>'material_id','qty',v_line->>'qty','manual_retail_unit_price',v_line->>'manual_price'));
   elsif v_line->>'mode'='MASTER' then
    if v_line->>'manual_price' is not null then raise exception 'Pilih satu dasar harga';end if;
    if v_quote->>'price_version_id' is null or v_line->>'price_version_id' is distinct from v_quote->>'price_version_id'
     or v_line->>'factor' is distinct from v_quote->>'factor' then raise exception 'STALE_PRICE: harga master berubah atau belum tersedia, muat ulang';end if;
    v_items:=v_items||jsonb_build_array(jsonb_build_object('material_id',v_line->>'material_id','qty',v_line->>'qty'));
   elsif v_line->>'mode'='FREE' then
    -- BC (ERP-DEC02): only a category on the owner's Special free list, for a Special contractor at the physical time.
    if v_line ? 'manual_price' or v_line ? 'price_version_id' or v_line ? 'factor' then raise exception 'Pilih satu dasar harga';end if;
    perform 1 from erp.bc_policy_settings_v1 where policy_key='ERP_DEC02' for share;
    v_free:=erp.bc_free_basis_v1((v_line->>'material_id')::uuid,v_contractor,v_at);
    if v_free is null then raise exception 'BC_FREE_NOT_ALLOWED: aksesori ini tidak gratis untuk mandor pada tanggal nota (ERP-DEC02 belum ditetapkan atau kategori/mandor tidak termasuk)';end if;
    if v_line->>'free_policy_version' is distinct from v_free->>'policy_version' then raise exception 'STALE_PRICE: daftar kategori gratis berubah, muat ulang';end if;
    v_items:=v_items||jsonb_build_array(jsonb_build_object('material_id',v_line->>'material_id','qty',v_line->>'qty','manual_retail_unit_price','0'));
   else raise exception 'Pilih harga master, eceran per pcs, atau gratis Special';end if;
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
  -- BC (ERP-DEC02): the free lines of this note with the policy version they used.
  delete from erp.bc_free_issue_lines_v1 where issue_id=v_id;
  insert into erp.bc_free_issue_lines_v1(issue_id,material_id,category_id,policy_version)
  select v_id,m.id,m.accessory_category_id,(x->>'free_policy_version')::bigint from jsonb_array_elements(p_payload->'items') x
   join erp.materials m on m.id=(x->>'material_id')::uuid where x->>'mode'='FREE';
  if v_action='POST' then v_native:=erp.post_contractor_material_issue_v2(v_id,p_client_request_id,(v_native->>'row_version')::bigint,v_reason);end if;
 elsif v_action='DELETE' then
  v_native:=erp.save_contractor_material_issue_draft_v2(jsonb_build_object('id',v_id,'action','DELETE','change_reason',v_reason),p_client_request_id,v_version);
 else v_native:=erp.reverse_contractor_material_issue_v2(v_id,v_reason,p_client_request_id,v_version);
 end if;
 select * into h from erp.contractor_material_issues where id=v_id;
 v_result:=jsonb_build_object('id',v_id,'action',v_action,'request_id',p_client_request_id,'status',case when v_action='DELETE' then 'DELETED' else h.status end,'row_version',h.row_version::text);
 return erp._idempotency_complete('save_accessory_issue_action_v1',p_client_request_id,v_result);
end;$function$;
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
   'rounding',(select jsonb_build_object('document_id',r.id,'amount',r.amount::text,'row_version',d.row_version::text)
     from erp.bc_note_roundings_v1 r join erp.bc_documents_v1 d on d.id=r.id where r.issue_id=h.id and d.status='POSTED'),
   'payroll_locked',exists(select 1 from erp.payroll_deductions d join erp.payroll_settlements s on s.id=d.payroll_id
     join erp.contractor_material_issue_items i on i.id=d.contractor_issue_item_id where i.issue_id=h.id and s.status<>'REVERSED'),
   'items',coalesce((select jsonb_agg(jsonb_build_object('id',i.id,'material_id',i.material_id,'sku',m.material_sku,'name',m.material_name,
     'unit',m.unit_code,'qty',i.qty::numeric(24,6)::text,'manual_price',i.manual_retail_unit_price::numeric(24,2)::text,
     'price',i.unit_sale_price_snapshot::numeric(24,6)::text,'factor',i.base_qty_per_transaction_uom::numeric(24,6)::text,
     'price_unit',i.transaction_uom_code,'price_version_id',i.accessory_price_version_id,
     'amount',i.total_receivable::numeric(24,6)::text,'payroll_status',i.payroll_status,
     'free',exists(select 1 from erp.bc_free_issue_lines_v1 f where f.issue_id=i.issue_id and f.material_id=i.material_id),
     'collectible',round(erp.bc_note_item_collectible_v1(i.id),2)::text) order by i.id)
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
  'materials',coalesce((select jsonb_agg(quote||jsonb_build_object('stock',stock,'free',erp.bc_free_basis_v1(id,v_contractor,v_at)) order by quote->>'name',id) from selected),'[]'::jsonb),
  'contractors',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',contractor_name) order by contractor_name,id) from erp.contractors where is_active and contractor_type='MANDOR'),'[]'::jsonb),
  'locations',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',location_name) order by location_name,id) from erp.locations where is_active and location_type='RAW_MATERIAL_WAREHOUSE'
    and not exists(select 1 from erp.bc_accessory_zones_v1 z where z.location_id=locations.id)),'[]'::jsonb),
  'orders',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',po_number) order by po_number,id) from erp.production_orders where contractor_id=v_contractor and status not in('FINISHED','CANCELLED')),'[]'::jsonb)
 ) into v_result;
 return v_result;
end;$function$;
CREATE OR REPLACE FUNCTION erp.bb_opening_credit_lines_v1(p_settlement_id uuid)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare c erp.bb_opening_credits_v1%rowtype;s erp.opening_subledger_settlements%rowtype;b erp.opening_subledger_balances%rowtype;
  v_credit erp.bb_customer_credits_v1%rowtype;
begin
  select * into c from erp.bb_opening_credits_v1 where settlement_id=p_settlement_id;
  select * into s from erp.opening_subledger_settlements where id=p_settlement_id;
  select * into b from erp.opening_subledger_balances where id=s.balance_id;
  -- BC (ALL-C02): a note return credited on the imported mandor receivable.
  if c.credit_kind='ACCESSORY_NOTE_RETURN' then return erp.bc_opening_note_credit_lines_v1(p_settlement_id);end if;
  if c.credit_kind in('CUSTOMER_ALLOWANCE','CUSTOMER_CREDIT_APPLY') then
    if b.party_type<>'CUSTOMER' or b.direction<>'RECEIVABLE' then raise exception 'BB_CREDIT_KIND_MISMATCH: kredit pelanggan hanya untuk piutang pelanggan';end if;
    if c.credit_kind='CUSTOMER_CREDIT_APPLY' then
      select * into v_credit from erp.bb_customer_credits_v1 where id=c.customer_credit_id;
      if v_credit.customer_id is distinct from b.customer_id then raise exception 'BB_CREDIT_PARTY_MISMATCH: kredit dan piutang harus milik pelanggan yang sama';end if;
      return jsonb_build_array(
        jsonb_build_object('account_id',v_credit.coa_account_id,'debit',s.amount,'credit',0,'customer_id',b.customer_id),
        jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',s.amount,'customer_id',b.customer_id));
    end if;
    return jsonb_build_array(
      jsonb_build_object('mapping_key','SALES_REVENUE','debit',s.amount,'credit',0,'customer_id',b.customer_id),
      jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',s.amount,'customer_id',b.customer_id));
  elsif c.credit_kind='SUPPLIER_ALLOWANCE' then
    if b.party_type<>'SUPPLIER' or b.direction<>'PAYABLE' then raise exception 'BB_CREDIT_KIND_MISMATCH: potongan supplier hanya untuk hutang supplier';end if;
    return jsonb_build_array(
      jsonb_build_object('mapping_key','AP_SUPPLIER','debit',s.amount,'credit',0),
      jsonb_build_object('mapping_key','MATERIAL_PURCHASE_VARIANCE','debit',0,'credit',s.amount));
  elsif c.credit_kind='VENDOR_ALLOWANCE' then
    if b.party_type<>'VENDOR' or b.direction<>'PAYABLE' then raise exception 'BB_CREDIT_KIND_MISMATCH: potongan laundry hanya untuk hutang vendor laundry';end if;
    return jsonb_build_array(
      jsonb_build_object('mapping_key','AP_VENDOR','debit',s.amount,'credit',0,'vendor_id',b.vendor_id),
      jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',s.amount,'vendor_id',b.vendor_id));
  end if;
  raise exception 'BB_CREDIT_KIND_MISMATCH';
end;$function$;
CREATE OR REPLACE FUNCTION erp.bb_opening_credit_account_v1(p_settlement_id uuid)
 RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select case c.credit_kind when 'ACCESSORY_NOTE_RETURN' then erp.account_id('MATERIAL_RECOVERY') when 'CUSTOMER_ALLOWANCE' then erp.account_id('SALES_REVENUE')
    when 'SUPPLIER_ALLOWANCE' then erp.account_id('MATERIAL_PURCHASE_VARIANCE') when 'VENDOR_ALLOWANCE' then erp.account_id('OTHER_INCOME')
    else (select k.coa_account_id from erp.bb_customer_credits_v1 k where k.id=c.customer_credit_id) end
  from erp.bb_opening_credits_v1 c where c.settlement_id=p_settlement_id
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
  if v_type not in ('BRAND','SIZE','MODEL','PRODUCT','CUSTOMER','SUPPLIER','CONTRACTOR','ACCESSORY_CATEGORY','MATERIAL','MATERIAL_ROLL','OPENING_BALANCE_ITEM','OPEN_PO','OPENING_CONTROL','OPENING_ADVANCE','OPENING_COST_ORIGIN','UNINVOICED_RECEIPT','LAUNDRY_VENDOR','LOCATION','CHART_ACCOUNT','CASH_ACCOUNT','LEGACY_DOCUMENT','OPENING_CUSTOMER_CREDIT','OPENING_SALE_RETURN','OPEN_PURCHASE_ORDER','OPENING_PAYROLL_ENTITLEMENT','OPENING_REWORK','OPENING_REWORK_COMPONENT','OPEN_SALES_DRAFT','OPENING_ACCESSORY_NOTE_LINE','OPENING_ACCESSORY_CUSTODY') then
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
    from erp.migration_staging_rows where batch_id=p_batch_id and entity_type not in('MATERIAL_ROLL','OPENING_BALANCE_ITEM','OPENING_CONTROL','OPENING_COST_ORIGIN','UNINVOICED_RECEIPT','OPENING_ADVANCE','LEGACY_DOCUMENT','OPENING_CUSTOMER_CREDIT','OPENING_SALE_RETURN','OPEN_PURCHASE_ORDER','OPENING_PAYROLL_ENTITLEMENT','OPENING_REWORK','OPENING_REWORK_COMPONENT','OPEN_SALES_DRAFT','OPENING_ACCESSORY_NOTE_LINE','OPENING_ACCESSORY_CUSTODY')
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
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type in('BRAND','SIZE','MODEL','PRODUCT','CUSTOMER','SUPPLIER','CONTRACTOR','ACCESSORY_CATEGORY','MATERIAL','MATERIAL_ROLL','OPEN_PO','LAUNDRY_VENDOR','LOCATION','CHART_ACCOUNT','CASH_ACCOUNT','OPENING_COST_ORIGIN','UNINVOICED_RECEIPT','OPENING_ADVANCE','LEGACY_DOCUMENT','OPENING_CUSTOMER_CREDIT','OPENING_SALE_RETURN','OPEN_PURCHASE_ORDER','OPENING_PAYROLL_ENTITLEMENT','OPENING_REWORK','OPENING_REWORK_COMPONENT','OPEN_SALES_DRAFT','OPENING_ACCESSORY_NOTE_LINE','OPENING_ACCESSORY_CUSTODY') and posted_entity_id is null) then raise exception 'Migration batch still has unapplied master/roll/open-PO rows';end if;
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
 v_catalog constant jsonb:='{"LAUNDRY_VENDOR": {"label": "Vendor laundry", "required": ["vendor_code", "vendor_name"], "fields": {"vendor_code": "Kode laundry", "vendor_name": "Nama laundry", "phone": "Telepon", "is_active": "Aktif", "notes": "Catatan"}}, "LOCATION": {"label": "Lokasi dan gudang", "required": ["location_code", "location_name", "location_type"], "fields": {"location_code": "Kode lokasi", "location_name": "Nama lokasi", "location_type": "Jenis lokasi", "is_active": "Aktif"}}, "CHART_ACCOUNT": {"label": "Akun buku besar", "required": ["account_code", "account_name", "account_type", "report_group", "normal_balance"], "fields": {"account_code": "Kode akun", "account_name": "Nama akun", "account_type": "Jenis akun", "report_group": "Kelompok laporan", "normal_balance": "Saldo normal", "parent_account_code": "Kode akun induk", "is_postable": "Boleh dipakai jurnal", "is_active": "Aktif"}}, "CASH_ACCOUNT": {"label": "Rekening kas dan bank", "required": ["cash_account_code", "cash_account_name", "coa_account_code", "account_kind"], "fields": {"cash_account_code": "Kode kas bank", "cash_account_name": "Nama kas bank", "coa_account_code": "Kode akun buku besar", "account_kind": "Jenis rekening", "is_active": "Aktif"}}, "BRAND": {"label": "Merek", "required": ["brand_code", "brand_name"], "fields": {"brand_code": "Kode merek", "brand_name": "Nama merek", "is_active": "Aktif"}}, "SIZE": {"label": "Ukuran", "required": ["size_code"], "fields": {"size_code": "Kode ukuran", "sort_order": "Urutan", "is_active": "Aktif"}}, "MODEL": {"label": "Model produk", "required": ["model_code", "model_name"], "fields": {"model_code": "Kode model", "model_name": "Nama model", "description": "Keterangan", "is_active": "Aktif"}}, "PRODUCT": {"label": "Produk per ukuran", "required": ["sku", "product_name", "model_code", "brand_code", "color_name", "size_code"], "fields": {"sku": "Kode produk", "product_name": "Nama produk", "model_code": "Kode model", "brand_code": "Kode merek", "color_name": "Warna", "size_code": "Kode ukuran", "is_active": "Aktif"}}, "CUSTOMER": {"label": "Pelanggan", "required": ["customer_code", "customer_name"], "fields": {"customer_code": "Kode pelanggan", "customer_name": "Nama pelanggan", "phone": "Telepon", "address": "Alamat", "is_active": "Aktif"}}, "SUPPLIER": {"label": "Supplier", "required": ["supplier_code", "supplier_name"], "fields": {"supplier_code": "Kode supplier", "supplier_name": "Nama supplier", "supplier_type": "Jenis supplier", "phone": "Telepon", "address": "Alamat", "is_active": "Aktif"}}, "CONTRACTOR": {"label": "Mandor", "required": ["contractor_code", "contractor_name"], "fields": {"contractor_code": "Kode mandor", "contractor_name": "Nama mandor", "contractor_type": "Jenis mandor", "attendance_required": "Wajib absensi", "is_active": "Aktif", "notes": "Catatan"}}, "ACCESSORY_CATEGORY": {"label": "Kategori aksesori", "required": ["category_code", "category_name", "base_uom_code"], "fields": {"category_code": "Kode kategori", "category_name": "Nama kategori", "base_uom_code": "Satuan dasar", "is_active": "Aktif", "notes": "Catatan"}}, "MATERIAL": {"label": "Bahan dan aksesori", "required": ["material_sku", "material_name", "material_type", "unit_code"], "fields": {"material_sku": "Kode bahan", "material_name": "Nama bahan", "material_type": "Jenis bahan", "unit_code": "Satuan dasar", "accessory_category_code": "Kode kategori aksesori", "is_active": "Aktif"}}, "MATERIAL_ROLL": {"label": "Stok awal kain per roll", "required": ["material_sku", "roll_number", "opening_qty", "unit_cost", "location_code", "control_key"], "fields": {"material_sku": "Kode bahan", "roll_number": "Nomor roll", "opening_qty": "Jumlah awal", "unit_cost": "Biaya per satuan", "location_code": "Kode gudang", "supplier_code": "Kode supplier", "notes": "Catatan", "control_key": "Kode total pembanding", "opening_source_key": "Kode rincian stok asal"}}, "OPENING_BALANCE_ITEM": {"label": "Stok dan saldo awal", "required": ["balance_type", "control_key"], "fields": {"balance_type": "Jenis saldo", "material_sku": "Kode bahan", "product_sku": "Kode produk", "brand_code": "Kode merek", "model_code": "Kode model", "color_name": "Warna", "size_code": "Kode ukuran", "location_code": "Kode gudang", "contractor_code": "Kode mandor", "customer_code": "Kode pelanggan", "supplier_code": "Kode supplier", "vendor_code": "Kode laundry", "cash_account_code": "Kode kas bank", "stage": "Tahap produksi", "qty": "Jumlah", "unit_cost": "Biaya per satuan", "amount": "Nominal", "quality_grade": "Kualitas", "hpp_input_method": "Cara isi HPP", "hpp_percent_of_price": "Persentase HPP", "notes": "Catatan", "control_key": "Kode total pembanding", "document_number": "Nomor dokumen asal", "document_date": "Tanggal dokumen asal", "due_date": "Tanggal jatuh tempo", "original_amount": "Nominal dokumen awal", "settled_before_cutover": "Sudah dibayar sebelum saldo awal", "opening_source_key": "Kode rincian stok asal", "source_kind": "Jenis sumber saldo", "po_number": "Nomor PO saldo fisik", "accessory_cost_included": "Biaya aksesoris sudah termasuk (true/false)"}}, "OPEN_PO": {"label": "Pesanan produksi berjalan", "required": ["po_number", "model_code", "status", "current_stage"], "fields": {"po_number": "Nomor pesanan", "model_code": "Kode model", "contractor_code": "Kode mandor", "target_qty_pcs": "Target buah", "target_dozens": "Target lusin", "status": "Status", "current_stage": "Tahap produksi", "physical_start_at": "Waktu mulai fisik", "notes": "Catatan"}}, "OPENING_CONTROL": {"label": "Total pembanding saldo awal", "required": ["control_key", "balance_type", "amount"], "fields": {"control_key": "Kode total pembanding", "balance_type": "Jenis saldo", "qty": "Total jumlah", "amount": "Total nominal", "notes": "Catatan"}}, "UNINVOICED_RECEIPT": {"label": "Penerimaan belum ditagih — sisa bahan dan asal biaya", "required": ["receipt_number", "receipt_line_number", "receipt_date", "supplier_code", "material_sku", "location_code", "qty", "unit_cost", "control_key"], "fields": {"receipt_number": "Nomor penerimaan asal", "receipt_line_number": "Nomor baris penerimaan", "receipt_date": "Tanggal penerimaan asal", "supplier_code": "Kode supplier", "material_sku": "Kode bahan", "location_code": "Kode gudang", "qty": "Jumlah belum ditagih", "unit_cost": "Biaya estimasi per satuan", "opening_source_key": "Kode rincian stok asal", "control_key": "Kode total pembanding", "notes": "Catatan", "invoice_document_number": "Nomor invoice asal untuk bagian yang sudah ditagih", "invoiced_qty": "Jumlah yang sudah ditagih sebelum saldo awal"}}, "OPENING_ADVANCE": {"label": "Uang muka tersisa", "required": ["party_type", "party_code", "coa_account_code", "document_number", "document_date", "original_amount", "settled_before_cutover", "amount", "control_key"], "fields": {"party_type": "Jenis pihak", "party_code": "Kode pihak", "coa_account_code": "Kode akun uang muka", "document_number": "Nomor bukti uang muka", "document_date": "Tanggal uang muka", "original_amount": "Nominal asal", "settled_before_cutover": "Terpakai atau kembali sebelum saldo awal", "amount": "Sisa uang muka", "control_key": "Kode total pembanding"}}, "OPENING_COST_ORIGIN": {"label": "Asal biaya yang sudah terpakai sebelum cutover", "fields": {"supplier_code": "Kode supplier", "receipt_number": "Nomor penerimaan asal", "receipt_line_number": "Nomor baris penerimaan", "target_source_key": "Kode rincian WIP/BS/FG tujuan", "qty": "Jumlah bahan yang sudah terpakai", "notes": "Catatan"}, "required": ["supplier_code", "receipt_number", "receipt_line_number", "target_source_key", "qty"]}, "LEGACY_DOCUMENT": {"label": "Dokumen lama yang sudah lunas penuh", "required": ["balance_type", "party_code", "document_number", "document_date", "original_amount", "settled_before_cutover"], "fields": {"balance_type": "Jenis saldo dokumen", "party_code": "Kode pihak", "document_number": "Nomor dokumen asal", "document_date": "Tanggal dokumen asal", "original_amount": "Nominal dokumen awal", "settled_before_cutover": "Sudah dibayar sebelum saldo awal", "notes": "Catatan"}}, "OPENING_CUSTOMER_CREDIT": {"label": "Kredit retur pelanggan yang belum dikembalikan", "required": ["customer_code", "coa_account_code", "document_number", "document_date", "original_amount", "settled_before_cutover", "amount"], "fields": {"customer_code": "Kode pelanggan", "coa_account_code": "Kode akun kredit pelanggan", "document_number": "Nomor nota retur/kredit", "document_date": "Tanggal nota retur/kredit", "original_amount": "Nominal kredit asal", "settled_before_cutover": "Sudah dikembalikan sebelum saldo awal", "amount": "Sisa kredit", "notes": "Catatan"}}, "OPENING_SALE_RETURN": {"label": "Hak retur penjualan lama yang barangnya belum kembali", "required": ["customer_code", "return_number", "invoice_document_number", "product_sku", "qty", "credit_unit_price", "unit_cost", "credit_coa_account_code"], "fields": {"customer_code": "Kode pelanggan", "return_number": "Nomor persetujuan retur", "invoice_document_number": "Nomor invoice asal", "product_sku": "Kode produk", "brand_code": "Kode merek", "model_code": "Kode model", "color_name": "Warna", "size_code": "Kode ukuran", "qty": "Jumlah pcs boleh diretur", "credit_unit_price": "Kredit per pcs", "unit_cost": "Nilai persediaan per pcs", "credit_coa_account_code": "Kode akun kredit pelanggan", "notes": "Catatan"}}, "OPEN_PURCHASE_ORDER": {"label": "PO pembelian yang belum diterima penuh saat saldo awal", "required": ["po_number", "po_line_number", "po_date", "supplier_code", "location_code", "material_sku", "ordered_qty", "received_before_cutover_qty", "cancelled_before_cutover_qty", "remaining_qty", "unit_price"], "fields": {"po_number": "Nomor PO pembelian", "po_line_number": "Nomor baris PO", "po_date": "Tanggal PO", "supplier_code": "Kode supplier", "location_code": "Kode gudang tujuan", "material_sku": "Kode bahan", "ordered_qty": "Jumlah dipesan", "received_before_cutover_qty": "Sudah diterima sebelum saldo awal", "cancelled_before_cutover_qty": "Sudah dibatalkan sebelum saldo awal", "remaining_qty": "Sisa yang masih ditunggu", "unit_price": "Harga estimasi per satuan", "expected_date": "Perkiraan tanggal datang", "notes": "Catatan"}}, "OPENING_PAYROLL_ENTITLEMENT": {"label": "Hak upah, absensi, atau reimburse sebelum saldo awal yang belum disetujui", "required": ["kind", "contractor_code", "document_number", "line_number", "document_date", "rate"], "fields": {"kind": "Jenis hak (SEWING_WORK/ATTENDANCE/ACCESSORY_REIMBURSEMENT)", "contractor_code": "Kode mandor", "document_number": "Nomor dokumen hutang mandor", "line_number": "Nomor baris", "document_date": "Tanggal hak timbul", "rate": "Tarif", "po_number": "Nomor PO (upah jahit)", "work_component_code": "Kode komponen kerja", "earned_qty": "Jumlah dikerjakan", "paid_before_qty": "Jumlah sudah dibayar sebelum saldo awal", "carry_qty": "Jumlah komponen dibawa (carry)", "worker_name": "Nama pekerja (absensi)", "period_start": "Awal periode absensi", "period_end": "Akhir periode absensi", "days": "Jumlah hari dibayar", "category_code": "Kode kategori aksesori", "good_qty": "Jumlah GOOD", "paid_before_amount": "Nominal sudah dibayar sebelum saldo awal", "notes": "Catatan"}}, "OPENING_REWORK": {"label": "Rework yang masih di mandor atau laundry saat saldo awal", "required": ["rework_number", "bs_source_key", "destination_type", "sent_date", "qty_sent_original", "qty_returned_before_cutover", "qty_open"], "fields": {"rework_number": "Nomor rework asal", "bs_source_key": "Kode rincian BS asal (opening_source_key baris BS)", "destination_type": "Tujuan rework (CONTRACTOR/LAUNDRY)", "contractor_code": "Kode mandor rework", "vendor_code": "Kode laundry rework", "sent_date": "Tanggal kirim rework", "qty_sent_original": "Jumlah dikirim", "qty_returned_before_cutover": "Sudah kembali sebelum saldo awal", "qty_open": "Masih di rework saat saldo awal", "notes": "Catatan"}}, "OPENING_REWORK_COMPONENT": {"label": "Komponen upah rework terbuka", "required": ["rework_number", "work_component_code", "completed_before_bs_qty", "qty_performed", "rate_per_pcs"], "fields": {"rework_number": "Nomor rework asal", "work_component_code": "Kode komponen kerja", "completed_before_bs_qty": "Pcs yang komponennya sudah selesai sebelum BS", "qty_performed": "Pcs yang akan dikerjakan", "rate_per_pcs": "Tarif per pcs"}}, "OPEN_SALES_DRAFT": {"label": "Draf penjualan yang masih terbuka saat saldo awal (dengan reservasi)", "required": ["draft_number", "line_number", "draft_date", "customer_code", "location_code", "product_sku", "qty_pcs", "unit_price"], "fields": {"draft_number": "Nomor draf penjualan", "line_number": "Nomor baris draf", "draft_date": "Tanggal draf lama", "customer_code": "Kode pelanggan", "location_code": "Kode gudang barang jadi", "product_sku": "Kode produk", "qty_pcs": "Jumlah pcs yang direservasi", "unit_price": "Harga per pcs", "discount_amount": "Potongan baris", "due_date": "Jatuh tempo", "payment_terms": "Syarat pembayaran", "notes": "Catatan"}}, "OPENING_ACCESSORY_NOTE_LINE": {"label": "Baris nota aksesori mandor lama (di balik piutang mandor saldo awal)", "required": ["document_number", "contractor_code", "line_number", "material_sku", "qty", "line_amount"], "fields": {"document_number": "Nomor nota lama (sama dengan dokumen piutang mandor)", "contractor_code": "Kode mandor", "line_number": "Nomor baris nota", "material_sku": "Kode aksesori", "qty": "Jumlah (PCS utuh untuk aksesori hitung)", "line_amount": "Nominal baris nota asal", "notes": "Catatan"}}, "OPENING_ACCESSORY_CUSTODY": {"label": "Aksesori yang bukan stok siap pakai: titipan belum dinilai, belum kembali, titipan pelanggan", "required": ["custody_kind", "custody_key", "qty"], "fields": {"custody_kind": "Jenis (PENDING_VALUE, UNRETURNED, CUSTOMER_GARMENT)", "custody_key": "Kode opname (satu barang fisik satu kode)", "material_sku": "Kode aksesori", "location_code": "Kode area pemeriksaan (PENDING_VALUE)", "condition": "Kondisi (WAITING, USABLE, DAMAGED)", "qty": "Jumlah PCS", "holder": "Pemegang (UNRETURNED)", "owner_kind": "Pemilik (COMPANY atau CUSTOMER)", "customer_code": "Kode pelanggan (CUSTOMER_GARMENT)", "product_sku": "Kode produk (opsional)", "description": "Keterangan barang", "notes": "Catatan"}}}'::jsonb;
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
     perform erp.validate_initial_import_receipts_v1(b.id);
     perform erp.validate_initial_prepayments_v1(b.id);
     perform erp.bb_validate_financial_imports_v1(b.id);
     perform erp.bb_validate_purchase_imports_v1(b.id);
     perform erp.bb_validate_labour_imports_v1(b.id);
     perform erp.bb_validate_production_imports_v1(b.id);
     perform erp.bb_validate_sales_imports_v1(b.id);
     perform erp.bc_validate_imports_v1(b.id);
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
   v_batch:=v_batch||erp.bb_financial_workspace_v1(b.id)||erp.bb_purchase_workspace_v1(b.id)||erp.bb_labour_workspace_v1(b.id)||erp.bb_production_workspace_v1(b.id)||erp.bb_sales_workspace_v1(b.id)||erp.bc_import_workspace_v1(b.id);
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
   'bc',erp.bc_import_revision_part_v1(p_batch_id)
 )::text,'UTF8'),'sha256'),'hex');
$function$;
CREATE OR REPLACE FUNCTION erp.assert_new_stock_cutoff_coverage_v1()
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO ''
AS $function$
declare
  v_registry jsonb:='{"erp.accessory_bom_versions.product_id":{"class":"MASTER","reason":"Effective-dated accessory BOM; no stock instant"},"erp.bs_cases.product_id":{"class":"NEW_STOCK_FACT","reason":"physical_at of QC/laundry BS and manual OUT_OF_NOWHERE BS"},"erp.contractor_accessory_reimbursement_entitlements.product_id":{"class":"DERIVED","reason":"Accounting entitlement of an FG lot"},"erp.fg_accessory_cost_snapshots.product_id":{"class":"DERIVED","reason":"Cost snapshot of an FG lot"},"erp.fg_adjustment_items.product_id":{"class":"MOVEMENT","reason":"Adjusts an existing lot"},"erp.fg_inventory_balances.product_id":{"class":"DERIVED","reason":"Balance cache keyed by product/location/grade"},"erp.fg_lots.product_id":{"class":"NEW_STOCK_FACT","reason":"produced_at of every lot except GOOD returned by rework"},"erp.fg_stock_movements.product_id":{"class":"MOVEMENT","reason":"Movement of an existing lot"},"erp.bb_opening_sale_return_rights_v1.product_id":{"class":"SOURCE_DOCUMENT","reason":"Return right of an old invoice; the stock fact is the RETURN lot in fg_lots, validated as NEW_STOCK at receipt"},"erp.bb_opening_sale_return_receipts_v1.product_id":{"class":"DERIVED","reason":"Provenance of a return receipt; the stock fact is its fg_lots lot"},"erp.bb_wip_bs_splits_v1.product_id":{"class":"DERIVED","reason":"Provenance of an opening WIP BS split; the stock fact is its bs_cases row (NEW_STOCK_FACT at its physical_at)"},"erp.bb_open_sales_draft_lines_v1.product_id":{"class":"DERIVED","reason":"Provenance of a sales draft open at cutover; the sale is its native sales_items line (reservation of existing stock)"},"erp.bc_customer_custody_v1.product_id":{"class":"SOURCE_DOCUMENT","reason":"A customer-owned garment in service (ACC-C10); never company stock, no stock fact"},"erp.initial_import_wip_output_identity_v1.opening_product_id":{"class":"DERIVED","reason":"Provenance of an opening WIP output: the product filled in on its opening item"},"erp.initial_import_wip_output_identity_v1.output_product_id":{"class":"DERIVED","reason":"Provenance of an opening WIP output; the stock fact is its fg_lots lot"},"erp.journal_lines.product_id":{"class":"ACCOUNTING","reason":"Journal dimension"},"erp.laundry_receipt_batch_size_lines.bs_product_id":{"class":"SOURCE_DOCUMENT","reason":"Laundry receipt input; the BS fact is bs_cases"},"erp.laundry_receipt_bs_product_allocations.product_id":{"class":"SOURCE_DOCUMENT","reason":"Validated as NEW_STOCK; the BS fact is bs_cases"},"erp.non_po_hpp_gl_sync_events_v2620f.product_id":{"class":"ACCOUNTING","reason":"HPP to GL synchronisation event"},"erp.opening_balance_items.product_id":{"class":"SOURCE_DOCUMENT","reason":"Opening document; facts are OPENING lots and LEGACY BS"},"erp.po_accessory_bom_commitments.product_id":{"class":"MASTER","reason":"PO accessory BOM commitment"},"erp.product_conversions.from_product_id":{"class":"SOURCE_DOCUMENT","reason":"Conversion source, validated as EXISTING_STOCK"},"erp.product_conversions.to_product_id":{"class":"SOURCE_DOCUMENT","reason":"Conversion target; the fact is the CONVERSION lot in fg_lots"},"erp.product_identity_mutation_context_v1.product_id":{"class":"AUTHORIZATION","reason":"Private one-use identity edit context"},"erp.product_price_versions.product_id":{"class":"MASTER","reason":"Effective-dated price"},"erp.qc_inspection_items.final_product_id":{"class":"SOURCE_DOCUMENT","reason":"QC input; the facts are fg_lots and bs_cases"},"erp.sales_items.product_id":{"class":"SALES","reason":"Sale of existing stock"},"erp.sales_return_items.product_id":{"class":"SALES","reason":"Return of sold stock"},"erp.stock_explainability_snapshots.product_id":{"class":"REPORT","reason":"Stock explanation snapshot"},"erp.stock_policy_versions.product_id":{"class":"MASTER","reason":"Effective-dated stock policy"}}';
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
CREATE OR REPLACE FUNCTION erp.run_v265_gudang_write_integrity_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_catalog', 'information_schema', 'pg_temp'
AS $function$
  select 'browser_direct_gudang_document_write','CRITICAL',count(*)::bigint,
         'Gudang adjustments, supplier returns and contractor issues must mutate only through aggregate RPCs'
  from information_schema.role_table_grants g
  where g.table_schema='erp'
    and g.table_name in(
      'material_adjustments','material_adjustment_items',
      'material_supplier_returns','material_supplier_return_items',
      'contractor_material_issues','contractor_material_issue_items'
    ) and g.grantee in('PUBLIC','anon','authenticated')
    and g.privilege_type in('INSERT','UPDATE','DELETE')

  union all
  select 'browser_legacy_gudang_post_execute','CRITICAL',count(*)::bigint,
         'Authenticated browser must use idempotent/versioned v2 posting and reversal wrappers'
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='erp' and p.proname in(
    'post_material_adjustment','reverse_material_adjustment',
    'post_material_supplier_return','reverse_material_supplier_return',
    'post_contractor_material_issue','reverse_contractor_material_issue'
  ) and has_function_privilege('authenticated',p.oid,'EXECUTE')

  union all
  select 'posted_adjustment_without_active_movement','CRITICAL',count(*)::bigint,
         'Every POSTED adjustment line needs an unreversed stock movement'
  from erp.material_adjustment_items i join erp.material_adjustments h on h.id=i.adjustment_id and h.status='POSTED'
  where not exists(select 1 from erp.material_stock_movements m where m.source_type='MATERIAL_ADJUSTMENT_ITEM' and m.source_id=i.id
    and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id))

  union all
  select 'posted_supplier_return_without_active_movement','CRITICAL',count(*)::bigint,
         'Every POSTED supplier return line needs an unreversed stock movement'
  from erp.material_supplier_return_items i join erp.material_supplier_returns h on h.id=i.return_id and h.status='POSTED'
  where not exists(select 1 from erp.material_stock_movements m where m.source_type='MATERIAL_SUPPLIER_RETURN_ITEM' and m.source_id=i.id
    and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id))

  union all
  select 'posted_contractor_issue_without_active_movement','CRITICAL',count(*)::bigint,
         'Every POSTED contractor issue line needs an unreversed stock movement'
  from erp.contractor_material_issue_items i join erp.contractor_material_issues h on h.id=i.issue_id and h.status='POSTED'
  where not exists(select 1 from erp.material_stock_movements m where m.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and m.source_id=i.id
    and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id))

  union all
  select 'supplier_return_client_price_provenance_gap','CRITICAL',count(*)::bigint,
         'Supplier return credit price must be populated from its source purchase'
  from erp.material_supplier_return_items i
  where i.supplier_credit_unit_price is null or i.purchase_item_id is null

  union all
  select 'contractor_issue_price_provenance_gap','CRITICAL',count(*)::bigint,
         'Contractor issue selling price must retain an authoritative version id'
  from erp.contractor_material_issue_items i join erp.materials m on m.id=i.material_id
  where (m.material_type='ACCESSORY' and i.accessory_price_version_id is null and i.manual_retail_unit_price is null)
     or (m.material_type<>'ACCESSORY' and i.material_price_version_id is null);
$function$;
CREATE OR REPLACE FUNCTION erp.bb_financial_workspace_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object(
    'opening_balances',coalesce((select jsonb_agg(jsonb_build_object(
        'balance_id',b.id,'balance_type',f.balance_type,'source_kind',f.source_kind,'source_mode',f.source_mode,
        'party_type',b.party_type,'party_id',f.party_id,'party_code',coalesce(cu.customer_code,su.supplier_code,ve.vendor_code,co.contractor_code),
        'party_name',coalesce(cu.customer_name,su.supplier_name,ve.vendor_name,co.contractor_name),
        'document_number',f.document_number,'document_date',f.document_date,'due_date',f.due_date,'cutover_date',f.cutover_date,
        'original_amount',f.original_amount::text,'settled_before_cutover',f.settled_before_cutover::text,
        'opening_amount',b.original_amount::text,'settled_amount',b.settled_amount::text,
        'reserved_amount',erp.bb_opening_balance_reserved_v1(b.id)::numeric(20,2)::text,
        'remaining_amount',(b.original_amount-b.settled_amount)::text,
        'available_amount',(b.original_amount-b.settled_amount-erp.bb_opening_balance_reserved_v1(b.id))::text,'status',b.status,
        'settlements',coalesce((select jsonb_agg(jsonb_build_object('id',s.id,'number',s.settlement_number,
            'date',erp._cp3_business_date(s.physical_at),'amount',s.amount::text,'status',s.status,
            'method',case when c.settlement_id is not null then 'CREDIT' when s.cash_account_id is null then 'ADVANCE' else 'CASH' end,
            'credit_kind',c.credit_kind,'credit_note_number',c.credit_note_number,
            'reversible',coalesce(s.status='POSTED' and c.credit_kind is distinct from 'CUSTOMER_CREDIT_APPLY' and s.cash_account_id is not null or
              (s.status='POSTED' and c.credit_kind in('CUSTOMER_ALLOWANCE','SUPPLIER_ALLOWANCE','VENDOR_ALLOWANCE')),false))
            order by s.physical_at,s.id)
          from erp.opening_subledger_settlements s left join erp.bb_opening_credits_v1 c on c.settlement_id=s.id
          where s.balance_id=b.id),'[]'::jsonb),
        'payroll_lines',coalesce((select jsonb_agg(jsonb_build_object('payroll_id',p.id,'payroll_number',p.payroll_number,'status',p.status,
            'row_version',p.row_version::text,'amount',r.amount::text) order by p.period_end,p.id)
          from erp.payroll_reimbursements r join erp.payroll_settlements p on p.id=r.payroll_id
          where r.opening_payable_balance_id=b.id and p.status<>'REVERSED'),'[]'::jsonb))
        order by f.balance_type,f.document_number,b.id)
      from erp.initial_import_financial_sources f join erp.opening_subledger_balances b on b.opening_item_id=f.opening_item_id
      left join erp.customers cu on cu.id=b.customer_id left join erp.suppliers su on su.id=b.supplier_id
      left join erp.laundry_vendors ve on ve.id=b.vendor_id left join erp.contractors co on co.id=b.contractor_id
      where f.batch_id=p_batch and f.source_kind<>'CONTRACTOR_CASH_ADVANCE'),'[]'::jsonb),
    'opening_payable_payrolls',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'payroll_number',p.payroll_number,
        'contractor_id',p.contractor_id,'period_end',p.period_end,'row_version',p.row_version::text,'net_payable',p.net_payable::text)
        order by p.period_end,p.id)
      from erp.payroll_settlements p where p.status in('DRAFT','CALCULATED','REVIEW') and exists(select 1 from erp.initial_import_financial_sources f
        where f.batch_id=p_batch and f.balance_type='CONTRACTOR_PAYABLE' and f.party_id=p.contractor_id)),'[]'::jsonb),
    'legacy_documents',coalesce((select jsonb_agg(jsonb_build_object('id',d.id,'balance_type',d.balance_type,'party_id',d.party_id,
        'document_number',d.document_number,'document_date',d.document_date,'original_amount',d.original_amount::text) order by d.document_number,d.id)
      from erp.bb_legacy_documents_v1 d where d.batch_id=p_batch),'[]'::jsonb),
    'customer_credits',coalesce((select jsonb_agg(erp.bb_customer_credit_state_v1(c.id)||jsonb_build_object(
        'customer_code',cu.customer_code,'customer_name',cu.customer_name,
        'open_receivables',coalesce((select jsonb_agg(jsonb_build_object('balance_id',b.id,'document_number',f.document_number,
            'remaining_amount',(b.original_amount-b.settled_amount)::text) order by f.document_number,b.id)
          from erp.initial_import_financial_sources f join erp.opening_subledger_balances b on b.opening_item_id=f.opening_item_id
          where f.balance_type='CUSTOMER_RECEIVABLE' and f.party_id=c.customer_id and b.original_amount>b.settled_amount),'[]'::jsonb),
        'events',coalesce((select jsonb_agg(jsonb_build_object('id',e.id,'kind',e.event_type,'amount',e.amount::text,'date',e.effective_date,
            'reason',e.reason,'reversed',e.reversed_at is not null or (e.event_type='APPLY_OPENING_AR'
              and (select status from erp.opening_subledger_settlements where id=e.settlement_id)<>'POSTED')) order by e.created_at,e.id)
          from erp.bb_customer_credit_events_v1 e where e.credit_id=c.id),'[]'::jsonb)) order by c.document_number,c.id)
      from erp.bb_customer_credits_v1 c join erp.customers cu on cu.id=c.customer_id where c.batch_id=p_batch),'[]'::jsonb),
    'sale_return_rights',coalesce((select jsonb_agg(jsonb_build_object('id',r.id,'return_number',r.return_number,
        'customer_code',cu.customer_code,'invoice_document_number',r.invoice_document_number,
        'invoice_state',case when r.invoice_source_id is not null then 'OPEN' else 'SETTLED_BEFORE_CUTOVER' end,
        'product_sku',p.sku,'qty_pcs',r.qty_pcs,'credit_unit_price',r.credit_unit_price::text,'unit_cost',r.unit_cost::text,
        'received_pcs',coalesce((select sum(x.qty_pcs) from erp.bb_opening_sale_return_receipts_v1 x where x.right_id=r.id and x.status='POSTED'),0),
        'receipts',coalesce((select jsonb_agg(jsonb_build_object('id',x.id,'qty_pcs',x.qty_pcs,'date',erp._cp3_business_date(x.physical_at),
            'status',x.status,'credit_id',x.credit_id) order by x.physical_at,x.id)
          from erp.bb_opening_sale_return_receipts_v1 x where x.right_id=r.id),'[]'::jsonb)) order by r.return_number,r.id)
      from erp.bb_opening_sale_return_rights_v1 r join erp.customers cu on cu.id=r.customer_id join erp.products p on p.id=r.product_id
      where r.batch_id=p_batch),'[]'::jsonb),
    'fg_locations',coalesce((select jsonb_agg(jsonb_build_object('id',l.id,'code',l.location_code,'name',l.location_name) order by l.location_code)
      from erp.locations l where l.is_active and l.location_type='FG_WAREHOUSE'),'[]'::jsonb))
$function$;
do $coverage$ begin perform erp.assert_new_stock_cutoff_coverage_v1(); end $coverage$;
insert into erp.schema_migrations(version,description) values('v2.6.20bc','Accessory service, return and inspection workflow with owner policy settings pending by default, note return credit, rounding line, Special free lines, opening accessory states');
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule','cp6_v2620ay_rollback_capsule','cp6_v2620az_rollback_capsule','cp6_v2620ba_rollback_capsule','cp6_v2620bb_rollback_capsule','cp6_v2620bc_rollback_capsule')
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
 if object_count<>8243 or fingerprint is distinct from '7d5af588107baae6b9bc6cfbb0837e5762f7036ef3626e8446f4634a6e221040' then
  raise exception 'BC_INSTALLED_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
update erp.cp6_v2620bc_rollback_capsule set installed_definition_sha256=encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex');
do $after_data$ declare v_table text;v_hash jsonb;v_after jsonb;v_before jsonb;v_cmp jsonb;v_cols text[];v_nonnull bigint; begin
 v_after:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620bc_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_after:=v_after||jsonb_build_object(v_table,v_hash);
 end loop;
 select snapshot->'before' into v_before from pg_temp.cp6_release_boundary;
 v_cmp:=v_after;
 for v_table,v_cols in select key,array(select jsonb_array_elements_text(value)) from jsonb_each('{"payroll_reimbursements":["bc_credit_event_id"]}'::jsonb) loop
  execute format($strip$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')),
   count(*) filter(where n) from(select encode(extensions.digest(convert_to((to_jsonb(t)-%L::text[])::text,'UTF8'),'sha256'),'hex') h,
   jsonb_strip_nulls(to_jsonb(t))?|%L::text[] n from erp.%I t)s$strip$,v_cols,v_cols,v_table) into v_hash,v_nonnull;
  if v_nonnull<>0 then raise exception 'BC_ADDED_COLUMNS_NOT_EMPTY: %',v_table;end if;
  v_cmp:=v_cmp||jsonb_build_object(v_table,v_hash);
 end loop;
 if (v_cmp-array['bc_policy_settings_v1','bc_policy_setting_events_v1','bc_accessory_zones_v1','bc_execution_context_v1','bc_documents_v1','bc_document_links_v1','bc_adjustment_purposes_v1','bc_internal_use_lines_v1','bc_outstanding_returns_v1','bc_customer_custody_v1','bc_return_lots_v1','bc_lot_events_v1','bc_count_variances_v1','bc_opening_note_lines_v1','bc_note_roundings_v1','bc_free_issue_lines_v1']::text[]) is distinct from v_before or exists(select 1 from unnest(array['bc_accessory_zones_v1','bc_execution_context_v1','bc_documents_v1','bc_document_links_v1','bc_adjustment_purposes_v1','bc_internal_use_lines_v1','bc_outstanding_returns_v1','bc_customer_custody_v1','bc_return_lots_v1','bc_lot_events_v1','bc_count_variances_v1','bc_opening_note_lines_v1','bc_note_roundings_v1','bc_free_issue_lines_v1']::text[]) t where (v_after->t->>'count') is distinct from '0')
  then raise exception 'BC_INSTALL_CHANGED_DATA';end if;
 if (v_after->'bc_policy_setting_events_v1'->>'count') is distinct from '7' then raise exception 'BC_SEED_CHANGED: bc_policy_setting_events_v1';end if;
 if (v_after->'bc_policy_settings_v1'->>'count') is distinct from '7' then raise exception 'BC_SEED_CHANGED: bc_policy_settings_v1';end if;
 if exists(select 1 from erp.bc_policy_settings_v1 where status<>'PENDING_POLICY_VALUE' or value is not null or version<>1 or set_by is not null) or exists(select 1 from erp.bc_policy_setting_events_v1 where status<>'PENDING_POLICY_VALUE' or value is not null or version<>1) or (select array_agg(policy_key order by policy_key) from erp.bc_policy_settings_v1) is distinct from array['ACC_DEC01','ACC_DEC03','ACC_DEC04','ACC_DEC05','ACC_DEC06','ACC_DEC07','ERP_DEC02']::text[] then raise exception 'BC_SEED_NOT_PENDING';end if;
 if exists(with live as (select p.oid::regprocedure::text as identity,encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') as definition_sha256,
  array(select a::text from unnest(p.proacl)a order by a::text) as acl,pg_get_userbyid(p.proowner) as owner
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p')) select 1 from pg_temp.cp6_release_functions f left join live x on x.identity=f.identity
  where f.identity<>all(coalesce((select array_agg(object_regidentity) from erp.cp6_v2620bc_rollback_capsule),'{}'))
  and (x.identity is null or (x.definition_sha256,x.acl,x.owner) is distinct from (f.definition_sha256,f.acl,f.owner)))
  then raise exception 'BC_CAPSULE_INCOMPLETE';end if;
 update erp.cp6_v2620bc_rollback_capsule set boundary_snapshot=(select snapshot from pg_temp.cp6_release_boundary)||jsonb_build_object('after',v_after);
end $after_data$;
do $capsule_guard$
declare expected jsonb;actual jsonb;boundary jsonb;
begin
 if not exists(select 1 from pg_class where oid='erp.cp6_v2620bc_rollback_capsule'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='erp.cp6_v2620bc_rollback_capsule'::regclass and a.grantee<>p.relowner)
   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='erp.cp6_v2620bc_rollback_capsule'::regclass and a.grantee<>'postgres'::regrole)
   or exists(select 1 from pg_policy where polrelid='erp.cp6_v2620bc_rollback_capsule'::regclass)
   or exists(select 1 from pg_trigger where tgrelid='erp.cp6_v2620bc_rollback_capsule'::regclass and not tgisinternal)
   or (select count(*) from erp.cp6_v2620bc_rollback_capsule)<>22 then raise exception 'BC_CAPSULE_SECURITY_OR_COUNT';end if;
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620an_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620an_rollback_capsule'::regclass)) into expected;
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620bc_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620bc_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620bc_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620bc_rollback_capsule'::regclass)) into actual;
 if actual is distinct from expected then raise exception 'BC_CAPSULE_SHAPE_DRIFT';end if;
 select boundary_snapshot into boundary from erp.cp6_v2620bc_rollback_capsule limit 1;
 if 22>0 and (boundary is null or exists(select 1 from erp.cp6_v2620bc_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before'])) then raise exception 'BC_CAPSULE_BOUNDARY';end if;
 if exists(select 1 from erp.cp6_v2620bc_rollback_capsule where object_regidentity<>all(array['erp.post_material_adjustment(uuid)','erp._cp6_material_adjustment_revaluation_state(uuid)','erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','erp.sync_material_cost_revaluation(uuid)','erp.populate_payroll_draft(uuid)','erp.validate_material_kasbon_deduction()','erp.refresh_contractor_issue_payroll_status(uuid)','erp.run_integrity_checks()','erp.approve_payroll(uuid)','erp.save_accessory_issue_action_v1(text,jsonb,uuid)','erp.get_accessory_issue_workspace_v1(jsonb)','erp.bb_opening_credit_lines_v1(uuid)','erp.bb_opening_credit_account_v1(uuid)','erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)','erp._validate_migration_batch_base(uuid)','erp.finalize_migration_batch(uuid)','erp.save_initial_import_action_v1(text,jsonb,uuid)','erp.get_initial_import_workspace_v1(uuid)','erp.initial_import_revision_v1(uuid)','erp.assert_new_stock_cutoff_coverage_v1()','erp.run_v265_gudang_write_integrity_checks()','erp.bb_financial_workspace_v1(uuid)']::text[])
   or definition_sha256 is distinct from encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex')
   or installed_definition_sha256 is null or installed_definition_sha256=definition_sha256
   or installed_definition_sha256 is distinct from encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex'))
  then raise exception 'BC_CAPSULE_SOURCE_DRIFT';end if;
end $capsule_guard$;
commit;
