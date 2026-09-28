-- CP6 BF: commercial SKU ranges, vendor-authoritative optional laundry costs and portable supplier credits. Release candidate of the T3 combined package; closed, drained maintenance required.
begin;
-- Built by scripts/cp6_t3_awx_release.py from supabase/dev/cp6_bf_t1_family.sql (sha256 58b97662a093147f3e594987bcc662e0f7cf376aaaf7664364739508ab1fafbd): the T1 body below is unchanged apart from the
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
 if exists(select 1 from erp.schema_migrations where version='v2.6.20bf') or to_regclass('erp.cp6_v2620bf_rollback_capsule') is not null
  or to_regclass('erp.bf_rollback_v1') is not null or to_regclass('erp.bf_skus_v1') is not null or to_regclass('erp.bf_sku_versions_v1') is not null or to_regclass('erp.bf_sku_members_v1') is not null or to_regclass('erp.bf_wave_skus_v1') is not null or to_regclass('erp.bf_po_boms_v1') is not null or to_regclass('erp.bf_requests_v1') is not null or to_regclass('erp.bf_context_v1') is not null or to_regclass('erp.bf_laundry_delivery_sources_v1') is not null or to_regclass('erp.bf_supplier_credit_moves_v1') is not null
 then raise exception 'BF_EXACT_PREDECESSOR_WITHOUT_SUCCESSOR_REQUIRED';end if;
end $admission$;
do $predecessor$
begin
 if exists(select 1 from supabase_migrations.schema_migrations where version>'20260926050000') then raise exception 'BF_EXACT_PREDECESSOR_REQUIRED';end if;
end $predecessor$;
do $prior_platform$
declare r record;
begin
 for r in select * from jsonb_to_recordset('[{"marker":"v2.6.20ac","stamp":"20260915031500","name":"erp_v2_6_20ac_cp6_temporal_surface_closure","sha":"871fb32b1d4a1e7f9aedfef684b0f2c766092732c38552620eb394061f6240d1"},{"marker":"v2.6.20ad","stamp":"20260915113627","name":"erp_v2_6_20ad_cp6_opening_material_business_day","sha":"58f8f1050e6c325339d7400a43b8c8f3d2375d2067f0c418d3eedfe85430a563"},{"marker":"v2.6.20ae","stamp":"20260915201500","name":"erp_v2_6_20ae_cp6_opening_roll_integrity","sha":"0c6bbf77a68142ddfdae99761a5cc2cd6e2e538be50b391f3303922c748c39d6"},{"marker":"v2.6.20af","stamp":"20260916014332","name":"erp_v2_6_20af_cp6_posted_child_integrity","sha":"3764349ab314c7990f6202d3f0de38b516aff53df2a3b1c4f272bc49667f6db4"},{"marker":"v2.6.20ag","stamp":"20260916050822","name":"erp_v2_6_20ag_cp6_sale_reservation_lineage","sha":"085b84cb6917617c5e6a2d375fd5177542ebe3f021a20de48e239159e34d66c0"},{"marker":"v2.6.20ah","stamp":"20260916070451","name":"erp_v2_6_20ah_cp6_return_allocation_eligibility","sha":"ade908ca9f55b2333c5eac5793b41aaabe0d57879dbb233e428fc882bab5738b"},{"marker":"v2.6.20ai","stamp":"20260916090022","name":"erp_v2_6_20ai_cp6_work_source_lineage","sha":"1ea5a602c5a5fcc9697355d9cca526709a06ee20e4eb4cdb765b2b7345c18d25"},{"marker":"v2.6.20aj","stamp":"20260916202400","name":"erp_v2_6_20aj_cp6_rework_output_lineage","sha":"b36a6359c57ad59d93ea5cb8dc5f7e90a0dd9cd59d48c331b037aa365d400986"},{"marker":"v2.6.20ak","stamp":"20260917033516","name":"erp_v2_6_20ak_cp6_import_reference_preview","sha":"9d06a91bd849c80e1ef99a6ac8996863527a30ef3b4079188be58bd8f3d4311d"},{"marker":"v2.6.20al","stamp":"20260917054049","name":"erp_v2_6_20al_cp6_opening_value_validation","sha":"2d16461cababd4a27827cfb8de01dd993a3a343460cdf049d427b44dd4cb6ea2"},{"marker":"v2.6.20am","stamp":"20260921214120","name":"erp_v2_6_20am_cp6_transfer_integrity","sha":"8fff82f72f9c76dd032778fa43aa37fd3fde98c4304de033d9c484db54f04a60"},{"marker":"v2.6.20an","stamp":"20260921223438","name":"erp_v2_6_20an_cp6_cutting_selectors","sha":"4df51d65fdb9a644fe2eeba92af23446e0c0389a1ebf9f336a0a396c144d7b71"},{"marker":"v2.6.20ao","stamp":"20260922135612","name":"erp_v2_6_20ao_cp6_invoice_retail","sha":"696a75c5969b756ce1973191a757a8c7deade06cb57e96dc5a16d648a4c48520"},{"marker":"v2.6.20ap","stamp":"20260922135615","name":"erp_v2_6_20ap_cp6_connected_import_materials","sha":"70503bb0247c811e066830ba752960a50b7afdfdb4c0c7697dee9a265ef1778a"},{"marker":"v2.6.20aq","stamp":"20260922161019","name":"erp_v2_6_20aq_cp6_accessory_lock_order","sha":"34cee78ee58f612187f7683280565ce2651e788e61efb62ced5e8c4dce7f9ada"},{"marker":"v2.6.20ar","stamp":"20260922185015","name":"erp_v2_6_20ar_cp6_opening_overlap","sha":"c5c973d47a4665723351205ccbcbe2c658c57bff7230f5552c5c2b7ca757371e"},{"marker":"v2.6.20as","stamp":"20260922210815","name":"erp_v2_6_20as_cp6_event_dates_product_identity","sha":"d13e46b3451386309a0a8dc1c89a4817ad8751568b9377f94c790832f8fa53a3"},{"marker":"v2.6.20at","stamp":"20260923005153","name":"erp_v2_6_20at_cp6_wip_temporal_identity","sha":"5e1ea5bfba73ada9aba5a8561efa9056b02154025d39bd10d47d3e4f2494110d"},{"marker":"v2.6.20au","stamp":"20260923045944","name":"erp_v2_6_20au_cp6_controlled_product_lifecycle","sha":"7d6265f081125499cb1813fe3f24c3b203363252727b5dcdfc7f74e311b85481"},{"marker":"v2.6.20av","stamp":"20260923110000","name":"erp_v2_6_20av_cp6_identity_new_stock_cutoff","sha":"c63a1fe3bf76dfc396921e07f57eb043e3bb864425b3289a9546bf66e08169a5"},{"marker":"v2.6.20aw","stamp":"20260924010000","name":"erp_v2_6_20aw_cp6_close_readiness_engine","sha":"c38edc9da084f4a90ee615bde16e6fea72e1072f79d6820d9d3bef27cc2a8ecb"},{"marker":"v2.6.20ax","stamp":"20260924010100","name":"erp_v2_6_20ax_cp6_fg_unsourced_receipts","sha":"c736049386c65f75c82fa790b502cd32c999512738207b7be17d711185c3d9f2"},{"marker":"v2.6.20ay","stamp":"20260924010200","name":"erp_v2_6_20ay_cp6_hpp_dated_from_goods","sha":"fd5ec47a16af264cc9b6a3aeed3d6e19023dc9f49beb51ceb8bfb4ecb14dc411"},{"marker":"v2.6.20az","stamp":"20260924010300","name":"erp_v2_6_20az_cp6_material_recost_dated_from_movement","sha":"e515d12a995a1806537ac08b7b0da15eb817480ead3103b035fc651b62977b8d"},{"marker":"v2.6.20ba","stamp":"20260925010000","name":"erp_v2_6_20ba_cp6_audit_closure","sha":"01bc0965cb945c25b98465a54ebc7fafabcc1d760c0698df1636de8069066960"},{"marker":"v2.6.20bb","stamp":"20260925020000","name":"erp_v2_6_20bb_cp6_open_cutover_states","sha":"ed95f1e84a8a924a830de9362ff890769875d01671b4e83c77208daf23a8df34"},{"marker":"v2.6.20bc","stamp":"20260925030000","name":"erp_v2_6_20bc_cp6_accessory_service_returns","sha":"23f31eafc8b8f235465dac7871f5c3cbd13e4e646552abdf591f82a2a3445bbb"},{"marker":"v2.6.20bd","stamp":"20260925040000","name":"erp_v2_6_20bd_cp6_laundry_prices_invoices","sha":"5daf8535106616c0348471a806cb00c77a3a47707bc1ece6adb3501e9b4283eb"},{"marker":"v2.6.20be","stamp":"20260926050000","name":"erp_v2_6_20be_cp6_conversion_redye_pocket","sha":"fbc6e068b9b397149c9ed26d449515a4158e96a5c37221fda26a3870a7c639ea"}]'::jsonb) as x(marker text,stamp text,name text,sha text) loop
  if not exists(select 1 from erp.schema_migrations where version=r.marker)
   or (select count(*) from supabase_migrations.schema_migrations where name=r.name)<>1
   or not exists(select 1 from supabase_migrations.schema_migrations where version=r.stamp and name=r.name
    and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')=r.sha) then
   raise exception 'BF_PRIOR_PLATFORM_DRIFT: %',r.name;
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
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule','cp6_v2620ay_rollback_capsule','cp6_v2620az_rollback_capsule','cp6_v2620ba_rollback_capsule','cp6_v2620bb_rollback_capsule','cp6_v2620bc_rollback_capsule','cp6_v2620bd_rollback_capsule','cp6_v2620be_rollback_capsule','cp6_v2620bf_rollback_capsule')
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
 if object_count<>9124 or fingerprint is distinct from 'c48175fea569d9bfd81a77c328d42a0887acacf83d2c038fd01a00a8915b57c2' then
  raise exception 'BF_PREDECESSOR_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
do $historical_capsules$
declare r record;actual text;
begin
 for r in select * from jsonb_each_text('{"bs_resolution_v2619_rollback_capsule":"28ab388833da7da87384766ecaedadc66b4d048c303ee91e16f3939e34afdc39","bs_resolution_v2619a_rollback_capsule":"de8dfaab7b63b8742d383a089cdb05e73b629aad9f4df149e6a3c9fb590ef560","bs_resolution_v2619b_rollback_capsule":"d6d4f7457743d51679b5d25bf166ed69ca4b4f098cf5902ff985937531c2505d","bs_resolution_v2619c_rollback_capsule":"0207ba4f2ffba8ed61584709bbd884f1d2ee1a5981194fd7189a45afe8b3cbe1","cp3_r4_rollback_capsule":"7c01add62e66a4e2774a7199c2e77a04cca5e5942dbbba54d22cef720f82bc1d","cp45_v2617_rollback_capsule":"b9a43ce463de9905e94dd6538fd2a4952b0586a78c145f6f9d88aab7d6da3d80","cp45_v2617a_rollback_capsule":"b065dbcfdf1b59cb799e9f58caf6dd5ca7686e9f70826fce6a1ba8f140610022","cp4_v2616_rollback_capsule":"dde0a005dbe7cc93709bdfc6b961f4b9a76bf4db06fd7177d21dc79048af4d2f","cp6_v2620_rollback_capsule":"b42b94c2380f0768259a3d8f7fb645c76ebd6f92e8bae6a37d802352f7effd4f","cp6_v2620a_rollback_capsule":"67befaaf327d2591e1ca1d654132ee483eba39b6cbb4f891c4719d817155d448","cp6_v2620aa_rollback_capsule":"eb0d6fb4fcac2ac06929d577101e604428e9a04821813c342e5b831147dc8948","cp6_v2620ab_rollback_capsule":"3be9a9166e3a607962be819fbe23d38fe455290a7a970dc2aad068079bf30785","cp6_v2620ac_relation_rollback_capsule":"63c595c956e25135e1e032613831f5a08a734ba1f5c4746c46483c84517ad5ea","cp6_v2620ac_rollback_capsule":"51a8b08c9d96e66f03c2c8ba94ed3ed8fb15b26d1a2e4c65c58c614442dfa969","cp6_v2620ad_rollback_capsule":"5c3588109395b32ed743e0f4f5d789a3c59e3fffbab7469138f1f423c877ea9d","cp6_v2620ae_rollback_capsule":"6a75e02bf7b90c542fd9f2ac9534a2de066b047f5ffea65bffb1f83fa63c17f0","cp6_v2620af_rollback_capsule":"bfa89fc0e94d34b29405acedf551935f024942835f31cdc98f0f0983a9550288","cp6_v2620ag_rollback_capsule":"7ddfe6181f0c1c7439faf8a8150c542e958b3bafd8d18b5b2d1eb454fd7a85b7","cp6_v2620ah_rollback_capsule":"361be9321e5f4dadc7c7ec0e99ed746a98e7a4150178fc8355d23707c1507a93","cp6_v2620ai_rollback_capsule":"f2428dd712aa763b1379a4ae5b1a1e1e6ee175b355d8769b854a28f1355181c8","cp6_v2620aj_rollback_capsule":"8e24026dc90a2a92292c2cc6c8faa5fc3de991a19f326db494e0af2a518436f1","cp6_v2620ak_rollback_capsule":"dc7bfce7b9ee6a42e33cdf03cabd99d64435a4615245b2037fd6e4ee399aef10","cp6_v2620al_rollback_capsule":"c9e9aca042674efa5c6fa283e4b9ee47f3353ee9ee95b34e14ef1fd6b09bfde9","cp6_v2620am_rollback_capsule":"e781e631d06c6894c20b1fe6f9c65779f461d19c405c8ae74f28ed7d83ae6a26","cp6_v2620an_rollback_capsule":"ebfa8a281a32fe54babbdc209264ab422fde27f344d48561b90d2af022fe75b3","cp6_v2620ao_rollback_capsule":"b48103dcffcfb4c0c5172d2f11a8af809149c3c82584d0c24e6c740311e18cab","cp6_v2620ap_rollback_capsule":"10123ac8749107ffe9e25e74c9e3bc3080c0e15fc3d844bfcedf06043281e3f7","cp6_v2620aq_rollback_capsule":"35dd70bc3f6eacd8640eea6e22b11d4daaaac96bd7092cc8addefe47d0e3d4b8","cp6_v2620ar_rollback_capsule":"4a445445dc1641310fd3baa2b653bc2ff65b95e2a1f1ae53df2e0bb367fba6a8","cp6_v2620as_rollback_capsule":"8ffec1b6c558d3525b2c22754c2467e92463a201c4decdea0523e68b1a950aa9","cp6_v2620at_rollback_capsule":"8a7aca28f5e2e023d4828bae009962c34c6373740ccb26e30d69b6b661486fa2","cp6_v2620au_rollback_capsule":"f8a90e3df4dcaaf19bf33f1e3348e802e9c6357df673bd9bd524b0b2c1fb5fea","cp6_v2620av_rollback_capsule":"555750c028d4e47105289ffbb7d03bbbc08fa1b7adecf45b06a29bf3abb27b8f","cp6_v2620aw_rollback_capsule":"fe0df122c718e3b373f9527a1fe0bdd4bdb473e2e59d6a710057524fe8142475","cp6_v2620ax_rollback_capsule":"bde6ca64f2ef2df40caf5fe51234a549bff8f5f67ff5276d7344f274e0192465","cp6_v2620ay_rollback_capsule":"4f4e686c95ddf0f9481c2c12c6308ec72d46a1d75f5e7a3a761808ee6ae1361c","cp6_v2620az_rollback_capsule":"1ca0d25f289d7322d649e239ec395e73903795f2c84fe652faf4dcf1d2a90853","cp6_v2620b_rollback_capsule":"f9bf784bff0c54e647f491e257a9649fd0c3e6f10c39ddfc0944c961b9dd7601","cp6_v2620ba_rollback_capsule":"c290dd07139c6e9f31945dacc5fdf680371f83315018efe8fb7f7edee31943db","cp6_v2620bb_rollback_capsule":"ee3dccf2bde5cb00e75c51a754d230964294436fe3ed976d52138844aad46102","cp6_v2620bc_rollback_capsule":"8e0e0f9b3e2e8c248d2185820e82ad2ec523b56a430153b25330157e6447ef2e","cp6_v2620bd_rollback_capsule":"af1682c8c452236f18578cdf02d79269de38b3a51b832931d1b0ece085c4e3b1","cp6_v2620be_rollback_capsule":"860781e04ec8a27025c51401ea971b4ec4b4f55656adab39d53af8f7d5f317a7","cp6_v2620c_rollback_capsule":"f88b1f5890ee8e7041758971bf9c9a3ce2bd0a7be6989fb95332c2dd7fa139aa","cp6_v2620d_rollback_capsule":"fa300c5554da4bb6812c61d726fd64f66329c97b085fa7d6ad5d0d8e5ae31235","cp6_v2620e_rollback_capsule":"143cd291cf4c12e78ab61e74e02ed03b08a48832a5064671868ff2bd2e3e1da7","cp6_v2620f_rollback_capsule":"076133b098e821fc2713af559618adf8aa3e204908f810af440fda355fc7a57f","cp6_v2620g_rollback_capsule":"ed9f4cacb47bd026ad6bdea373d1aa87044ed12aa60323cea453e3187dc488c4","cp6_v2620h_rollback_capsule":"4c25a060a2df3c22cd6fa9ff0b297163e223118a0d930b97bf1282b4756d909d","cp6_v2620i_rollback_capsule":"051203d95c44968abd8594f5bd48e289c4ac9a6c9fa49a89eee1086ad6b2c166","cp6_v2620j_rollback_capsule":"1393a8085d0f58717b13048c9cc3f7e9969ac86c351d6dfefdd2d4f43a735bd2","cp6_v2620k_rollback_capsule":"55aa71061f616ea11b361f0fabee2fd892f6438cc3f567cb9c135552ade42409","cp6_v2620l_rollback_capsule":"b4278768fce4ef307795953c14f607278c43bf474d76d3362e477280be08eb39","cp6_v2620m_rollback_capsule":"4b5f89d7bc4557f92b47716fe15640ab244c424fc1279433eb806d9d91d234e9","cp6_v2620n_rollback_capsule":"46e5ea4524613bb7a386551ada9e06888ea35eb987f9f5b864457fdd18bc3bc1","cp6_v2620o_rollback_capsule":"044e6b1a050df7e2a1d36082b0451877bda01116c08f611dfceb7a666bdf03c8","cp6_v2620p_rollback_capsule":"b656abaf23276984567c6c8d87b311427463c008b5ecd762fbdd0c2df13795df","cp6_v2620q_rollback_capsule":"ab6c992fbaa87f19a4eba696a57a3972f98504a354d9b5fc3be660939f8ea20f","cp6_v2620r_rollback_capsule":"8eb5e0a38284c5f8e3fee56618893ba72feaae9d26605c9ca3874dae25045297","cp6_v2620s_rollback_capsule":"fb57810a75f8829a038ed61b3a1cabde33dccf1e384661bc6723c51e28b3e132","cp6_v2620t_rollback_capsule":"348db4650d788750da243500b49e23c1130fdb70bc4a6d1fdf136bf68aa21f30","cp6_v2620u_rollback_capsule":"720eb1984548a3c381387fbe4d34e3c6f00334c8a4549eab7e398b827dcb7dd4","cp6_v2620v_rollback_capsule":"573ef5842eefadf1c32469514f4c8498667c99aec20ef20651406e4f419f5f60","cp6_v2620w_rollback_capsule":"f4e2ca1d577dd9f2724cc90693e8ee8bff36365c696575b69c6463f3e8ca0324","cp6_v2620x_rollback_capsule":"064db1068b56daa69e409ae582cd8a99490cea75d269154baa4217f90d3ca0d1","cp6_v2620y_rollback_capsule":"e3b23429a7f002c85ca8de1f8c632df13a4a2fc4e4654c12e2431c212772841d","cp6_v2620z_rollback_capsule":"ad0436a1480af43070e9861cb7e28d4cf55c435edbffb5fe368ca7babb7863ef","cutting_bridge_v2618_rollback_capsule":"535d1abd25668bc5bee79d82a602afe5efe4e8ce313bf1fb5170ae2004e3cb2d","cutting_bridge_v2618a_rollback_capsule":"db0608e690b3d936fa20b62cc4cfb9b1f9e86718212526eb6131562578b8bf60"}'::jsonb) loop
  execute format($caps$select encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to((to_jsonb(t)-array['captured_at','boundary_snapshot'])::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$caps$,r.key) into actual;
  if actual is distinct from r.value then raise exception 'BF_HISTORICAL_CAPSULE_DRIFT: %',r.key;end if;
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
 for r in select unnest(array['erp.cp6_v2620ao_rollback_capsule','erp.cp6_v2620ap_rollback_capsule','erp.cp6_v2620aq_rollback_capsule','erp.cp6_v2620ar_rollback_capsule','erp.cp6_v2620as_rollback_capsule','erp.cp6_v2620at_rollback_capsule','erp.cp6_v2620au_rollback_capsule','erp.cp6_v2620av_rollback_capsule','erp.cp6_v2620aw_rollback_capsule','erp.cp6_v2620ax_rollback_capsule','erp.cp6_v2620ay_rollback_capsule','erp.cp6_v2620az_rollback_capsule','erp.cp6_v2620ba_rollback_capsule','erp.cp6_v2620bb_rollback_capsule','erp.cp6_v2620bc_rollback_capsule','erp.cp6_v2620bd_rollback_capsule','erp.cp6_v2620be_rollback_capsule']::regclass[]) as rel loop
  if not exists(select 1 from pg_class where oid=r.rel and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid=r.rel and a.grantee<>p.relowner)
   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid=r.rel and a.grantee<>'postgres'::regrole)
   or exists(select 1 from pg_policy where polrelid=r.rel)
   or exists(select 1 from pg_trigger where tgrelid=r.rel and not tgisinternal) then raise exception 'BF_PRIOR_CAPSULE_SECURITY: %',r.rel;end if;
  select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid=r.rel),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=r.rel and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid=r.rel),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid=r.rel)) into actual;
  if actual is distinct from expected then raise exception 'BF_PRIOR_CAPSULE_SHAPE_DRIFT: %',r.rel;end if;
  execute format($b$select count(*) filter(where boundary_snapshot is null or not(boundary_snapshot ?& array['before','after','platform_before','markers_before']))
   +(case when count(distinct boundary_snapshot)=1 then 0 else 1 end) from %s$b$,r.rel) into bad;
  if bad<>0 then raise exception 'BF_PRIOR_CAPSULE_BOUNDARY: %',r.rel;end if;
 end loop;
end $prior_capsules$;
create table erp.cp6_v2620bf_rollback_capsule(like erp.cp6_v2620an_rollback_capsule including all);
alter table erp.cp6_v2620bf_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620bf_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620bf_rollback_capsule(object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),i.identity,pg_get_functiondef(p.oid),
 encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
 array(select a::text from unnest(p.proacl)a order by a::text),pg_get_userbyid(p.proowner)
from unnest(array['erp.commit_accessory_bom_for_lot(uuid)','erp.ensure_po_work_component_snapshots(uuid,timestamp with time zone)','erp.validate_work_completion()','erp.guard_work_completion_posting_consistency()','erp.seed_bs_case_component_baseline()','erp.classify_bs_case_v2(uuid,jsonb,uuid,bigint)','erp.cp6_lot_work_cost_v2620c(uuid,text)','erp.assert_new_stock_cutoff_coverage_v1()','erp.bd_priced_line_json_v1(uuid)','erp.bd_compute_pricing_v1(jsonb,jsonb)','erp.bd_attach_delivery_pricing_v1(uuid)','erp.bd_refresh_size_estimates_v1(uuid)','erp.bd_line_complete_v1(uuid)','erp.bd_delivery_line_price_unknown_v1(uuid)','erp.bd_post_invoice_v1(jsonb,uuid)','erp.bd_set_charge_price_v1(jsonb,uuid)','erp.period_blockers_v1(date,date)','erp.prepare_rework_component_line()','erp.run_v263c_bs_rework_integrity_checks()','erp.get_hpp_completeness(uuid)','erp.resolve_rework_accessory_bom_v1(uuid,timestamp with time zone)','erp.save_initial_import_action_v1(text,jsonb,uuid)','erp.bb_check_sales_import_row_v1(uuid,uuid)','erp.bb_apply_sales_imports_v1(uuid)','erp.bc_check_import_row_v1(uuid,uuid)','erp.bc_apply_imports_v1(uuid)','erp.be_check_pocket_import_v1(uuid,uuid)','erp.be_apply_pocket_imports_v1(uuid)','erp.bb_check_rework_import_row_v1(uuid,uuid)','erp.material_purchase_final_ap_total(uuid)','erp._cp6_supplier_cent_state(uuid[])','erp.post_supplier_payment(uuid)','erp.get_product_conversion_workspace_v1(jsonb)']) i(identity)
join pg_proc p on p.oid=i.identity::regprocedure join pg_namespace n on n.oid=p.pronamespace;
create temp table cp6_release_functions on commit drop as
select p.oid::regprocedure::text as identity,encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') as definition_sha256,
  array(select a::text from unnest(p.proacl)a order by a::text) as acl,pg_get_userbyid(p.proowner) as owner
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p');
do $before_data$ declare v_table text;v_hash jsonb;v_before jsonb; begin
 v_before:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620bf_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_before:=v_before||jsonb_build_object(v_table,v_hash);
 end loop;
 create temp table cp6_release_boundary on commit drop as select jsonb_build_object('before',v_before,
  'platform_before',(select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations t),
  'markers_before',(select encode(extensions.digest(convert_to(coalesce(jsonb_agg(to_jsonb(t) order by version),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') from erp.schema_migrations t)) snapshot;
end $before_data$;
do $guard$ begin if not exists(select 1 from erp.schema_migrations where version='v2.6.20be') then raise exception 'BF_REQUIRES_BE';end if;
if exists(select 1 from erp.schema_migrations where version='v2.6.20bf') then raise exception 'BF_ALREADY_INSTALLED';end if;end $guard$;

create table erp.bf_rollback_v1(payload jsonb not null);
insert into erp.bf_rollback_v1(payload)
select jsonb_build_object('functions',(select jsonb_object_agg(s,pg_get_functiondef(s::regprocedure)) from unnest(array['erp.commit_accessory_bom_for_lot(uuid)','erp.ensure_po_work_component_snapshots(uuid,timestamp with time zone)','erp.validate_work_completion()','erp.guard_work_completion_posting_consistency()','erp.seed_bs_case_component_baseline()','erp.classify_bs_case_v2(uuid,jsonb,uuid,bigint)','erp.cp6_lot_work_cost_v2620c(uuid,text)','erp.assert_new_stock_cutoff_coverage_v1()','erp.bd_priced_line_json_v1(uuid)','erp.bd_compute_pricing_v1(jsonb,jsonb)','erp.bd_attach_delivery_pricing_v1(uuid)','erp.bd_refresh_size_estimates_v1(uuid)','erp.bd_line_complete_v1(uuid)','erp.bd_delivery_line_price_unknown_v1(uuid)','erp.bd_post_invoice_v1(jsonb,uuid)','erp.bd_set_charge_price_v1(jsonb,uuid)','erp.period_blockers_v1(date,date)','erp.prepare_rework_component_line()','erp.run_v263c_bs_rework_integrity_checks()','erp.get_hpp_completeness(uuid)','erp.resolve_rework_accessory_bom_v1(uuid,timestamp with time zone)','erp.save_initial_import_action_v1(text,jsonb,uuid)','erp.bb_check_sales_import_row_v1(uuid,uuid)','erp.bb_apply_sales_imports_v1(uuid)','erp.bc_check_import_row_v1(uuid,uuid)','erp.bc_apply_imports_v1(uuid)','erp.be_check_pocket_import_v1(uuid,uuid)','erp.be_apply_pocket_imports_v1(uuid)','erp.bb_check_rework_import_row_v1(uuid,uuid)','erp.material_purchase_final_ap_total(uuid)','erp._cp6_supplier_cent_state(uuid[])','erp.post_supplier_payment(uuid)','erp.get_product_conversion_workspace_v1(jsonb)']) s),
 'snapshot_constraint',(select pg_get_constraintdef(oid) from pg_constraint where conrelid='erp.po_work_component_snapshots'::regclass and conname='po_work_component_snapshots_po_id_work_component_id_key'),
 'rework_constraint',(select pg_get_constraintdef(oid) from pg_constraint where conrelid='erp.rework_component_lines'::regclass and conname='rework_component_lines_rate_basis_check'));

-- Commercial identity is separate from the exact-size physical identity root.
create table erp.bf_skus_v1(
 id uuid primary key default gen_random_uuid(), brand_id uuid not null references erp.brands(id),
 model_id uuid not null references erp.product_models(id), color_name text not null,
 sku text not null check(length(btrim(sku)) between 1 and 100), revision bigint not null default 0,
 unique(brand_id,sku)
);
create table erp.bf_sku_versions_v1(
 id uuid primary key default gen_random_uuid(), sku_id uuid not null references erp.bf_skus_v1(id), revision bigint not null,
 effective_from timestamptz not null, effective_to timestamptz, settings jsonb not null,
 reason text not null, actor uuid, request_id uuid not null, created_at timestamptz not null default clock_timestamp(),
 unique(sku_id,revision), check(effective_to is null or effective_to>effective_from)
);
create table erp.bf_sku_members_v1(
 version_id uuid not null references erp.bf_sku_versions_v1(id), product_root uuid not null references erp.products(id),
 price_version_id uuid references erp.product_price_versions(id), bom_version_id uuid references erp.accessory_bom_versions(id),
 primary key(version_id,product_root)
);
create index bf_sku_members_root on erp.bf_sku_members_v1(product_root,version_id);
create table erp.bf_wave_skus_v1(
 cutting_group_id uuid not null references erp.cutting_groups(id) on delete cascade,
 size_id uuid not null references erp.sizes(id), sku_id uuid not null references erp.bf_skus_v1(id),
 bound_at timestamptz not null default clock_timestamp(), actor uuid, request_id uuid not null,
 primary key(cutting_group_id,size_id)
);
alter table erp.po_work_component_snapshots add column bf_sku_version_id uuid references erp.bf_sku_versions_v1(id);
alter table erp.po_work_component_snapshots drop constraint po_work_component_snapshots_po_id_work_component_id_key;
create unique index bf_work_snapshot_scope on erp.po_work_component_snapshots(po_id,work_component_id,bf_sku_version_id) nulls not distinct;
create table erp.bf_po_boms_v1(
 po_id uuid not null references erp.production_orders(id), sku_id uuid not null references erp.bf_skus_v1(id),
 version_id uuid not null references erp.bf_sku_versions_v1(id), primary key(po_id,sku_id)
);
create table erp.bf_requests_v1(request_id uuid primary key,actor uuid,action text not null,payload jsonb not null,response jsonb not null);
create table erp.bf_context_v1(backend_pid integer not null,transaction_id bigint not null,version_id uuid references erp.bf_sku_versions_v1(id),primary key(backend_pid,transaction_id));

CREATE OR REPLACE FUNCTION erp.bf_version_at_v1(p_product uuid,p_at timestamptz)
 RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select v.id from erp.products p join erp.bf_sku_members_v1 m on m.product_root=p.identity_root_id
 join erp.bf_sku_versions_v1 v on v.id=m.version_id
 where p.id=p_product and v.effective_from<=p_at and (v.effective_to is null or v.effective_to>p_at)
$function$;

-- Guard every old single-size economic write, including import/direct RPC routes.
CREATE OR REPLACE FUNCTION erp.bf_guard_economic_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r uuid; previous_root uuid; b uuid;
begin
 if exists(select 1 from erp.bf_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current()) then
   if TG_OP='DELETE' then return old;else return new;end if;
 end if;
 if TG_TABLE_NAME='accessory_bom_items' then
   b:=case when TG_OP='DELETE' then old.bom_version_id else new.bom_version_id end;
   select product_id into r from erp.accessory_bom_versions where id=b;
   if TG_OP='UPDATE' then select product_id into previous_root from erp.accessory_bom_versions where id=old.bom_version_id;end if;
 else r:=case when TG_OP='DELETE' then old.product_id else new.product_id end;end if;
 if TG_TABLE_NAME<>'accessory_bom_items' and TG_OP='UPDATE' then previous_root:=old.product_id;end if;
 if exists(select 1 from erp.bf_sku_members_v1 where product_root in(select identity_root_id from erp.products where id in(r,previous_root))) then
   raise exception 'BF_SHARED_MASTER: ubah harga/resep melalui master SKU bersama';
 end if;
 if exists(select 1 from erp.products p join erp.bf_skus_v1 s on s.brand_id=p.brand_id and s.model_id=p.model_id and s.color_name=p.color_name
   where p.id in(r,previous_root) and (s.sku=p.sku or exists(select 1 from erp.bf_sku_versions_v1 v join erp.bf_sku_members_v1 m on m.version_id=v.id
     join erp.products member on member.id=m.product_root where v.sku_id=s.id and member.sku=p.sku))) then
   raise exception 'BF_MEMBER_ADOPTION_REQUIRED: hubungkan ukuran baru ke master SKU sebelum menetapkan harga/resep';end if;
 if TG_OP='DELETE' then return old;else return new;end if;
end;$function$;
create trigger bf_shared_price before insert or update or delete on erp.product_price_versions for each row execute function erp.bf_guard_economic_v1();
create trigger bf_shared_bom before insert or update or delete on erp.accessory_bom_versions for each row execute function erp.bf_guard_economic_v1();
create trigger bf_shared_bom_item before insert or update or delete on erp.accessory_bom_items for each row execute function erp.bf_guard_economic_v1();

CREATE OR REPLACE FUNCTION erp.bf_legacy_basis_v1(p_roots uuid[],p_at timestamptz)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce(jsonb_agg(jsonb_build_object('product_root',p.id,'price',pr.price,'price_id',pr.id,
   'bom_id',b.id,'bom',case when b.id is not null then coalesce((select jsonb_agg(to_jsonb(i)-'id'-'bom_version_id' order by i.category_id,i.id)
   from erp.accessory_bom_items i where i.bom_version_id=b.id),'[]'::jsonb) end) order by p.id),'[]'::jsonb)
 from erp.products p
 left join lateral(select x.id,x.price from erp.product_price_versions x where x.product_id=p.id and x.effective_from<=p_at
   and (x.effective_to is null or x.effective_to>p_at) order by x.effective_from desc,x.id desc limit 1) pr on true
 left join lateral(select x.id from erp.accessory_bom_versions x where x.product_id=p.id and x.is_active and x.effective_from<=p_at
   and (x.effective_to is null or x.effective_to>p_at) order by x.effective_from desc,x.id desc limit 1) b on true
 where p.id=any(p_roots)
$function$;

CREATE OR REPLACE FUNCTION erp.bf_save_groups_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare at_time timestamptz; reason text; g jsonb; cfg jsonb; item jsonb; row_sku erp.bf_skus_v1%rowtype;
 root uuid; roots uuid[]; all_roots uuid[]:='{}'; group_ids uuid[]:='{}'; sid uuid; vid uuid; price_id uuid; bom_id uuid;
 result jsonb:='[]'; basis jsonb; current_v erp.bf_sku_versions_v1%rowtype; p erp.products%rowtype;
begin
 perform erp._cp3_assert_closed_json_object(p_payload,array['effective_from','reason','groups'],array['effective_from','reason','groups'],'SKU changes');
 at_time:=erp.bd_at_v1(p_payload->>'effective_from','effective_from'); reason:=erp.bc_text_v1(p_payload,'reason',true,1000);
 if at_time<statement_timestamp()-interval '5 minutes' then raise exception 'BF_HISTORY: master baru hanya mulai sekarang atau mendatang';end if;
 if jsonb_typeof(p_payload->'groups') is distinct from 'array' or jsonb_array_length(p_payload->'groups') not between 1 and 30 then
   raise exception 'BF_GROUPS: wajib 1 sampai 30 kelompok';end if;
 -- One lock also serializes movements between groups and edits arriving via different member sizes.
 perform pg_advisory_xact_lock(hashtextextended('BF:COMMERCIAL_SKUS',0));
 insert into erp.bf_context_v1(backend_pid,transaction_id) values(pg_backend_pid(),txid_current());
 -- Validate the whole edit and close all old memberships before attaching any new membership.
 for g in select value from jsonb_array_elements(p_payload->'groups') loop
   perform erp._cp3_assert_closed_json_object(g,array['id','expected_version','brand_id','model_id','color_name','sku','members','settings','legacy_basis'],
     array['id','expected_version','brand_id','model_id','color_name','sku','members','settings','legacy_basis'],'SKU group');
   sid:=erp.bd_uuid_v1(g,'id',true); if sid=any(group_ids) then raise exception 'BF_DUPLICATE_SKU';end if;
   group_ids:=group_ids||sid;
   select * into row_sku from erp.bf_skus_v1 where id=sid for update;
   if not found then
     if g->>'expected_version'<>'0' then raise exception 'STALE_VERSION';end if;
     insert into erp.bf_skus_v1(id,brand_id,model_id,color_name,sku)
     values(sid,erp.bd_uuid_v1(g,'brand_id',true),erp.bd_uuid_v1(g,'model_id',true),erp.bc_text_v1(g,'color_name',true,100),erp.bc_text_v1(g,'sku',true,100)) returning * into row_sku;
   elsif row_sku.revision::text is distinct from g->>'expected_version' then raise exception 'STALE_VERSION';
   elsif row_sku.brand_id<>erp.bd_uuid_v1(g,'brand_id',true) or row_sku.model_id<>erp.bd_uuid_v1(g,'model_id',true)
     or row_sku.color_name<>g->>'color_name' or row_sku.sku<>g->>'sku' then raise exception 'BF_IDENTITY: gunakan SKU baru untuk identitas komersial lain';end if;
   if jsonb_typeof(g->'members') is distinct from 'array' then raise exception 'BF_MEMBERS';end if;
   select coalesce(array_agg(x::uuid order by x),'{}') into roots from jsonb_array_elements_text(g->'members') x;
   if cardinality(roots)<>(select count(distinct x) from unnest(roots) x) then raise exception 'BF_DUPLICATE_MEMBER';end if;
   if roots&&all_roots then raise exception 'BF_DUPLICATE_MEMBER';end if;all_roots:=all_roots||roots;
   foreach root in array roots loop
     select * into p from erp.products where id=root for update;
     if p.id is null or p.identity_root_id<>p.id or p.brand_id<>row_sku.brand_id or p.model_id<>row_sku.model_id or p.color_name<>row_sku.color_name then
       raise exception 'BF_MEMBER_IDENTITY: anggota wajib akar fisik dengan merek/model/warna sama';end if;
   end loop;
   if cardinality(roots)<>(select count(distinct size_id) from erp.products where id=any(roots)) then raise exception 'BF_DUPLICATE_SIZE';end if;
   basis:=erp.bf_legacy_basis_v1(roots,at_time);
   if g->'legacy_basis' is distinct from basis then raise exception 'BF_BASIS_CHANGED: baca semua harga/resep anggota lalu konfirmasi pengaturan bersama';end if;
   select * into current_v from erp.bf_sku_versions_v1 where sku_id=sid and effective_to is null;
   if current_v.id is not null then
     if at_time<=current_v.effective_from then raise exception 'BF_EFFECTIVE_ORDER';end if;
     if exists(select 1 from erp.po_work_component_snapshots where bf_sku_version_id=current_v.id and committed_at>=at_time)
       or exists(select 1 from erp.bd_laundry_charge_lines_v1 c join erp.laundry_delivery_lines l on l.id=c.delivery_line_id
         join erp.laundry_deliveries d on d.id=l.delivery_id where c.bf_sku_version_id=current_v.id and d.physical_at>=at_time)
       or exists(select 1 from erp.rework_component_lines c join erp.rework_orders o on o.id=c.rework_order_id
         where c.bf_sku_version_id=current_v.id and o.physical_sent_at>=at_time) then
       raise exception 'BF_TARIFF_HISTORY: waktu perubahan mendahului pemakaian tarif yang sudah tercatat';end if;
     update erp.bf_sku_versions_v1 set effective_to=at_time where id=current_v.id;
   end if;
 end loop;
 if exists(select 1 from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id
     where m.product_root=any(all_roots) and v.effective_to is null) then raise exception 'BF_MOVE_ATOMIC: sertakan revisi kelompok asal dalam perubahan yang sama';end if;
 if exists(select 1 from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id
     where v.sku_id=any(group_ids) and v.effective_to=at_time and not(m.product_root=any(all_roots))) then
   raise exception 'BF_ORPHAN_MEMBER: anggota yang dikeluarkan wajib dipindah ke SKU tujuan';end if;
 for g in select value from jsonb_array_elements(p_payload->'groups') loop
   sid:=(g->>'id')::uuid;cfg:=g->'settings';
   perform erp._cp3_assert_closed_json_object(cfg,array['work_rates','laundry_rates'],array['price','bom','work_rates','laundry_rates'],'SKU settings');
   if not (cfg ?& array['price','bom']) then raise exception 'BF_SETTINGS_MISSING: harga/resep wajib disebut, boleh belum diisi';end if;
   if jsonb_typeof(cfg->'bom') not in('array','null') or jsonb_typeof(cfg->'work_rates') is distinct from 'array'
     or jsonb_typeof(cfg->'laundry_rates') is distinct from 'array' then raise exception 'BF_SETTINGS_ARRAY';end if;
   if cfg->'price'<>'null'::jsonb then perform erp.bd_amount_v1(cfg->'price','price',true);end if;
   perform erp.bf_validate_rates_v1(sid,cfg);
   update erp.bf_skus_v1 set revision=revision+1 where id=sid returning * into row_sku;
   insert into erp.bf_sku_versions_v1(sku_id,revision,effective_from,settings,reason,actor,request_id)
     values(sid,row_sku.revision,at_time,cfg,reason,erp.current_app_user_id(),p_request) returning id into vid;
   for root in select x::uuid from jsonb_array_elements_text(g->'members') x loop
     -- Existing historical guards reject an effective date before any already-posted financial use.
     if exists(select 1 from erp.product_price_versions where product_id=root and effective_from>=at_time)
       or exists(select 1 from erp.accessory_bom_versions where product_id=root and effective_from>=at_time) then
       raise exception 'BF_FUTURE_MASTER: selesaikan versi ekonomi mendatang sebelum mengubah kelompok';end if;
     update erp.product_price_versions set effective_to=at_time where product_id=root and (effective_to is null or effective_to>at_time);
     update erp.accessory_bom_versions set effective_to=at_time where product_id=root and (effective_to is null or effective_to>at_time);
     price_id:=null;bom_id:=null;
     if cfg->'price'<>'null'::jsonb then
       insert into erp.product_price_versions(product_id,price,effective_from,change_note,created_by)
         values(root,(cfg->>'price')::numeric,at_time,reason,erp.current_app_user_id()) returning id into price_id;
     end if;
     if cfg->'bom'<>'null'::jsonb then
       insert into erp.accessory_bom_versions(product_id,version_label,effective_from,notes,created_by)
         values(root,'SKU revision '||row_sku.revision,at_time,reason,erp.current_app_user_id()) returning id into bom_id;
     end if;
     for item in select value from jsonb_array_elements(case when cfg->'bom'='null'::jsonb then '[]'::jsonb else cfg->'bom' end) loop
       perform erp._cp3_assert_closed_json_object(item,array['category_id','qty_per_good_fg_base','hpp_method','reimbursement_rate','reimbursement_uom_code'],
         array['category_id','qty_per_good_fg_base','hpp_method','hpp_standard_rate','hpp_uom_code','reimbursement_rate','reimbursement_uom_code','notes'],'SKU accessory');
       insert into erp.accessory_bom_items(bom_version_id,category_id,qty_per_good_fg_base,hpp_method,hpp_standard_rate,hpp_uom_code,reimbursement_rate,reimbursement_uom_code,notes)
       values(bom_id,(item->>'category_id')::uuid,(item->>'qty_per_good_fg_base')::numeric,item->>'hpp_method',
         (item->>'hpp_standard_rate')::numeric,item->>'hpp_uom_code',(item->>'reimbursement_rate')::numeric,item->>'reimbursement_uom_code',item->>'notes');
     end loop;
     insert into erp.bf_sku_members_v1 values(vid,root,price_id,bom_id);
   end loop;
   result:=result||jsonb_build_object('id',sid,'version_id',vid,'revision',row_sku.revision::text);
   insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
     values('bf_skus_v1',sid,'UPDATE',jsonb_build_object('version_id',vid,'members',g->'members'),erp.current_app_user_id(),reason);
 end loop;
 delete from erp.bf_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 return jsonb_build_object('groups',result);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bf_guard_new_member_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare p erp.products%rowtype; at_time timestamptz;
begin
 if new.product_id is null then return new;end if;
 at_time:=case when TG_TABLE_NAME='fg_lots' then (to_jsonb(new)->>'produced_at')::timestamptz else (to_jsonb(new)->>'physical_at')::timestamptz end;
 select * into p from erp.products where id=new.product_id;
 if erp.bf_version_at_v1(p.id,at_time) is null and exists(
   select 1 from erp.bf_skus_v1 s join erp.bf_sku_versions_v1 v on v.sku_id=s.id
   where s.brand_id=p.brand_id and s.model_id=p.model_id and s.color_name=p.color_name
     and v.effective_from<=at_time and(v.effective_to is null or v.effective_to>at_time)
     and (s.sku=p.sku or exists(select 1 from erp.bf_sku_members_v1 m join erp.products member on member.id=m.product_root where m.version_id=v.id and member.sku=p.sku))) then
   raise exception 'BF_MEMBER_ADOPTION_REQUIRED: ukuran fisik belum menjadi anggota SKU pada tanggal barang masuk';
 end if;
 return new;
end;$function$;
create trigger bf_fg_member before insert on erp.fg_lots for each row execute function erp.bf_guard_new_member_v1();
create trigger bf_bs_member before insert on erp.bs_cases for each row execute function erp.bf_guard_new_member_v1();

CREATE OR REPLACE FUNCTION erp.bf_validate_rates_v1(p_sku uuid,p_settings jsonb)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare j jsonb; k text; ref uuid; vendor uuid; amount numeric; seen text[]:='{}'; key text;
begin
 for j in select value from jsonb_array_elements(p_settings->'work_rates') loop
   perform erp._cp3_assert_closed_json_object(j,array['work_component_id','rate'],array['contractor_id','work_component_id','rate','special'],'SKU work rate');
   vendor:=erp.bd_uuid_v1(j,'contractor_id',false);ref:=erp.bd_uuid_v1(j,'work_component_id',true);
   if (vendor is not null and not exists(select 1 from erp.contractors where id=vendor and is_active))
     or not exists(select 1 from erp.work_components where id=ref and is_active) then raise exception 'BF_WORK_RATE_REFERENCE';end if;
   if j ? 'special' and jsonb_typeof(j->'special') is distinct from 'boolean' then raise exception 'BF_SPECIAL_FLAG';end if;
   perform erp.bd_amount_v1(j->'rate','rate',true);key:=coalesce(vendor::text,'*')||':'||ref::text||':'||coalesce(j->>'special','false');
   if key=any(seen) then raise exception 'BF_DUPLICATE_RATE';end if;seen:=seen||key;
 end loop;
 seen:='{}';
 if jsonb_array_length(p_settings->'laundry_rates')>0 then
   raise exception 'BF_LAUNDRY_VENDOR_AUTHORITY: harga laundry diatur pada vendor; riwayat SKU hanya referensi pemilihan';
 end if;
end;$function$;

-- SKU base rate applies to every member size. Optional contractor/special overrides are still per SKU.
CREATE OR REPLACE FUNCTION erp.bf_work_rate_v1(p_version uuid,p_contractor uuid,p_component uuid,p_at timestamptz)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select (r->>'rate')::numeric from erp.bf_sku_versions_v1 v cross join lateral jsonb_array_elements(v.settings->'work_rates') r
 where v.id=p_version and r->>'work_component_id'=p_component::text
   and (r->>'contractor_id' is null or r->>'contractor_id'=p_contractor::text)
   and (not coalesce((r->>'special')::boolean,false) or exists(select 1 from erp.contractor_hpp_policy_versions pol
     where pol.contractor_id=p_contractor and pol.is_special and pol.effective_from<=erp._cp3_business_date(p_at)
       and (pol.effective_to is null or pol.effective_to>=erp._cp3_business_date(p_at))))
 order by (r->>'contractor_id' is not null) desc,coalesce((r->>'special')::boolean,false) desc limit 1
$function$;

CREATE OR REPLACE FUNCTION erp.bf_context_rate_v1(p_kind text,p_ref uuid,p_vendor uuid DEFAULT NULL)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 -- Legacy context helper cannot supply SKU monetary rates.
 select null::jsonb
$function$;

CREATE OR REPLACE FUNCTION erp.bf_bom_for_lot_v1(p_lot uuid)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.fg_lots%rowtype; vid uuid; pinned uuid; sid uuid; root uuid; bom uuid; frozen_bom uuid;
begin
 select * into l from erp.fg_lots where id=p_lot;
 vid:=erp.bf_version_at_v1(l.product_id,l.produced_at);
 if vid is null then return null;end if;
 select sku_id into sid from erp.bf_sku_versions_v1 where id=vid;
 select identity_root_id into root from erp.products where id=l.product_id;
 select version_id into pinned from erp.bf_po_boms_v1 where po_id=l.po_id and sku_id=sid;
 if pinned is null then
   -- Rework can be the first financial use, before any GOOD lot. Its native commitment already pins a real SKU recipe.
   select v.id into pinned from erp.po_accessory_bom_commitments c
     join erp.bf_sku_members_v1 m on m.bom_version_id=c.bom_version_id join erp.bf_sku_versions_v1 v on v.id=m.version_id
     where c.po_id=l.po_id and v.sku_id=sid order by c.committed_at,c.id limit 1;
   if pinned is not null then insert into erp.bf_po_boms_v1 values(l.po_id,sid,pinned);end if;
 end if;
 if pinned is null then
   select bom_version_id into bom from erp.bf_sku_members_v1 where version_id=vid and product_root=root;
   -- Adoption may continue an existing PO only when every old commitment has the exact same economic recipe.
   if exists(select 1 from erp.po_accessory_bom_commitments c join erp.products p on p.id=c.product_id
     join erp.bf_sku_members_v1 m on m.product_root=p.identity_root_id and m.version_id=vid
     where c.po_id=l.po_id and erp.bf_recipe_basis_v1(c.bom_version_id) is distinct from erp.bf_recipe_basis_v1(bom)) then
     raise exception 'BF_PO_LEGACY_BOM: resep PO lama berbeda; komitmen lama tidak boleh diganti diam-diam';end if;
   insert into erp.bf_po_boms_v1 values(l.po_id,sid,vid);pinned:=vid;
 end if;
 select bom_version_id into bom from erp.bf_sku_members_v1 where version_id=pinned and product_root=root;
 if bom is null then
   if exists(select 1 from erp.bf_sku_members_v1 where version_id=pinned and product_root=root) then
     raise exception 'BF_BOM_UNCONFIGURED: tentukan resep SKU (termasuk tanpa aksesori bila benar) sebelum penggunaan biaya';
   end if;
   -- Adding a size must not force a new price for the other members of a PO already in progress.
   select bom_version_id into frozen_bom from erp.bf_sku_members_v1 where version_id=pinned and bom_version_id is not null order by product_root limit 1;
   select bom_version_id into bom from erp.bf_sku_members_v1 where version_id=vid and product_root=root;
   if bom is null or erp.bf_recipe_basis_v1(bom) is distinct from erp.bf_recipe_basis_v1(frozen_bom) then
     raise exception 'BF_PO_NEW_MEMBER: resep ukuran baru berbeda dari komitmen PO';end if;
 end if;
 return bom;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bf_recipe_basis_v1(p_bom uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select case when p_bom is not null then coalesce(jsonb_agg(jsonb_build_object('category',category_id,'qty',qty_per_good_fg_base,
   'method',hpp_method,'standard',case when hpp_method='BOM_STANDARD' then hpp_standard_rate end,
   'unit',case when hpp_method='BOM_STANDARD' then hpp_uom_code end,'reimbursement',reimbursement_rate,'reimbursement_unit',reimbursement_uom_code)
   order by category_id),'[]') end from erp.accessory_bom_items where bom_version_id=p_bom
$function$;

-- A wave can contain several ranges. Its reference chooses rates, never final FG identity.
alter table erp.rework_component_lines add column bf_sku_version_id uuid references erp.bf_sku_versions_v1(id);
alter table erp.rework_component_lines drop constraint rework_component_lines_rate_basis_check;
alter table erp.rework_component_lines add constraint rework_component_lines_rate_basis_check
 check(rate_basis in('CONTRACTOR_RATE','PO_SNAPSHOT','LAUNDRY_ZERO','LEGACY_CLIENT','SKU_RATE'));

CREATE OR REPLACE FUNCTION erp.bf_bind_wave_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare g erp.cutting_groups%rowtype; r jsonb; sid uuid; v_sku uuid; vid uuid; model uuid; seen uuid[]:='{}'; before_hash text;
begin
 perform erp._cp3_assert_closed_json_object(p_payload,array['cutting_group_id','references','expected_version'],array['cutting_group_id','references','expected_version'],'wave SKU references');
 perform pg_advisory_xact_lock(hashtextextended('BF:COMMERCIAL_SKUS',0));
 select * into g from erp.cutting_groups where id=erp.bd_uuid_v1(p_payload,'cutting_group_id',true) for update;
 if g.id is null then raise exception 'BF_WAVE_MISSING';end if;
 select model_id into model from erp.production_orders where id=g.po_id;
 before_hash:=erp.bf_wave_revision_v1(g.id);
 if p_payload->>'expected_version' is distinct from before_hash then raise exception 'STALE_VERSION';end if;
 if exists(select 1 from erp.work_completion_events where cutting_group_id=g.id and status='POSTED')
   or exists(select 1 from erp.fg_lots where cutting_group_id=g.id)
   or exists(select 1 from erp.laundry_deliveries d join erp.laundry_delivery_lines l on l.delivery_id=d.id
     where l.cutting_group_id=g.id and d.status not in('DRAFT','REVERSED')) then
   raise exception 'BF_WAVE_USED: referensi pekerjaan yang sudah dipakai terkunci';end if;
 if jsonb_typeof(p_payload->'references') is distinct from 'array' then raise exception 'BF_REFERENCES';end if;
 delete from erp.bf_wave_skus_v1 where cutting_group_id=g.id;
 for r in select value from jsonb_array_elements(p_payload->'references') loop
   perform erp._cp3_assert_closed_json_object(r,array['sku_id','size_id'],array['sku_id','size_id'],'wave size SKU');
   v_sku:=erp.bd_uuid_v1(r,'sku_id',true);sid:=erp.bd_uuid_v1(r,'size_id',true);
   if sid=any(seen) then raise exception 'BF_DUPLICATE_SIZE';end if;seen:=seen||sid;
   if not exists(select 1 from erp.cutting_group_size_slots where cutting_group_id=g.id and size_id=sid) then raise exception 'BF_SIZE_NOT_IN_WAVE';end if;
   select v.id into vid from erp.bf_sku_versions_v1 v join erp.bf_skus_v1 s on s.id=v.sku_id
     join erp.bf_sku_members_v1 m on m.version_id=v.id join erp.products p on p.id=m.product_root
     where s.id=v_sku and s.model_id=model and p.size_id=sid and v.effective_from<=statement_timestamp() and(v.effective_to is null or v.effective_to>statement_timestamp());
   if vid is null then raise exception 'BF_SKU_SIZE_MODEL: SKU referensi harus memuat ukuran/model saat dipilih';end if;
   insert into erp.bf_wave_skus_v1 values(g.id,sid,v_sku,clock_timestamp(),erp.current_app_user_id(),p_request);
 end loop;
 if cardinality(seen)>0 and exists(select 1 from erp.cutting_group_size_slots where cutting_group_id=g.id and not(size_id=any(seen))) then
   raise exception 'BF_WAVE_COVERAGE: tentukan SKU referensi setiap ukuran wave';end if;
 insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
   values('cutting_groups',g.id,'UPDATE',p_payload,erp.current_app_user_id(),'Referensi tarif SKU per ukuran wave; bukan identitas FG');
 return jsonb_build_object('cutting_group_id',g.id,'revision',erp.bf_wave_revision_v1(g.id));
end;$function$;

CREATE OR REPLACE FUNCTION erp.bf_work_capacity_v1(p_group uuid,p_snapshot uuid,p_default bigint)
 RETURNS bigint LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select case when s.bf_sku_version_id is null then p_default else coalesce((
   select sum(y.qty_pcs)::bigint from erp.cutting_roll_yields y join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
   join erp.cutting_group_size_slots slot on slot.id=y.size_slot_id
   join erp.bf_wave_skus_v1 w on w.cutting_group_id=r.cutting_group_id and w.size_id=slot.size_id
   where r.cutting_group_id=p_group and w.sku_id=v.sku_id),0) end
 from erp.po_work_component_snapshots s left join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id where s.id=p_snapshot
$function$;

CREATE OR REPLACE FUNCTION erp.bf_snapshot_sku_v1(p_snapshot uuid)
 RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select v.sku_id from erp.po_work_component_snapshots s join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id where s.id=p_snapshot
$function$;

CREATE OR REPLACE FUNCTION erp.bf_wave_revision_v1(p_group uuid)
 RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select md5(coalesce((select jsonb_agg(jsonb_build_array(size_id,sku_id,request_id) order by size_id)::text from erp.bf_wave_skus_v1 where cutting_group_id=p_group),'[]'))
$function$;

CREATE OR REPLACE FUNCTION erp.bf_group_sku_v1(p_group uuid,p_product uuid)
 RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select case when p_product is null then
   (select min(w.sku_id::text)::uuid from erp.bf_wave_skus_v1 w where w.cutting_group_id=p_group having count(distinct w.sku_id)=1)
 else (select w.sku_id from erp.bf_wave_skus_v1 w join erp.products p on p.size_id=w.size_id where w.cutting_group_id=p_group and p.id=p_product) end
$function$;

CREATE OR REPLACE FUNCTION erp.bf_ensure_work_v1(p_po uuid,p_at timestamptz)
 RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare s record; base record; vid uuid; rate numeric; n integer:=0; contractor uuid;
begin
 perform pg_advisory_xact_lock(hashtextextended('BF:COMMERCIAL_SKUS',0));
 select contractor_id into contractor from erp.production_orders where id=p_po for update;
 for s in select distinct w.sku_id from erp.bf_wave_skus_v1 w join erp.cutting_groups g on g.id=w.cutting_group_id where g.po_id=p_po loop
   -- First financial use pins the SKU version for the PO. Merely cutting/binding does not pin a tariff.
   select x.bf_sku_version_id into vid from erp.po_work_component_snapshots x join erp.bf_sku_versions_v1 v on v.id=x.bf_sku_version_id
     where x.po_id=p_po and v.sku_id=s.sku_id order by x.committed_at,x.id limit 1;
   if vid is not null then continue;end if;
   select id into vid from erp.bf_sku_versions_v1 where sku_id=s.sku_id and effective_from<=p_at and(effective_to is null or effective_to>p_at);
   if vid is null then raise exception 'BF_WORK_VERSION_MISSING';end if;
   -- An unused binding is a choice, not a membership snapshot. Recheck it at
   -- first financial use under the same lock as SAVE_GROUPS. Earlier pins above
   -- retain their original version after a later membership change.
   if exists(select 1 from erp.bf_wave_skus_v1 w join erp.cutting_groups g on g.id=w.cutting_group_id
     where g.po_id=p_po and w.sku_id=s.sku_id and not exists(
       select 1 from erp.bf_sku_members_v1 m join erp.products p on p.id=m.product_root
       where m.version_id=vid and p.size_id=w.size_id)) then
     raise exception 'BF_WAVE_REFERENCE_STALE: keanggotaan ukuran berubah sebelum tarif kerja dipakai; pilih ulang SKU wave';
   end if;
   for base in select * from erp.po_work_component_snapshots where po_id=p_po and bf_sku_version_id is null order by sequence_no,id loop
     rate:=erp.bf_work_rate_v1(vid,contractor,base.work_component_id,p_at);
     insert into erp.po_work_component_snapshots(po_id,work_component_id,source_bom_version_id,sequence_no,rate_per_pcs_snapshot,source_bom_item_id,source_contractor_rate_id,committed_at,bf_sku_version_id)
       values(p_po,base.work_component_id,base.source_bom_version_id,base.sequence_no,coalesce(rate,base.rate_per_pcs_snapshot),base.source_bom_item_id,
         case when rate is null then base.source_contractor_rate_id end,p_at,vid);
     n:=n+1;
   end loop;
 end loop;
 return n;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bf_snapshot_matches_v1(p_snapshot uuid,p_group uuid,p_product uuid)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select case when erp.bf_group_sku_v1(p_group,p_product) is null then s.bf_sku_version_id is null and not exists(select 1 from erp.bf_wave_skus_v1 w where w.cutting_group_id=p_group)
   else v.sku_id=erp.bf_group_sku_v1(p_group,p_product) end
 from erp.po_work_component_snapshots s left join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id where s.id=p_snapshot
$function$;

CREATE OR REPLACE FUNCTION erp.bf_assert_work_scope_v1(p_completion uuid,p_snapshot uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare e erp.work_completion_events%rowtype; sku uuid; version uuid;
begin
 select * into e from erp.work_completion_events where id=p_completion;
 select s.bf_sku_version_id,v.sku_id into version,sku from erp.po_work_component_snapshots s left join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id where s.id=p_snapshot;
 if version is not null and not exists(select 1 from erp.bf_wave_skus_v1 where cutting_group_id=e.cutting_group_id and sku_id=sku) then raise exception 'BF_WORK_OTHER_SKU';end if;
 if version is null and exists(select 1 from erp.bf_wave_skus_v1 where cutting_group_id=e.cutting_group_id) then raise exception 'BF_WORK_SCOPE_REQUIRED: pilih tarif SKU anggota wave';end if;
end;$function$;

alter table erp.bd_laundry_charge_lines_v1 add column bf_sku_version_id uuid references erp.bf_sku_versions_v1(id);

create table erp.bf_laundry_delivery_sources_v1(
 delivery_line_id uuid primary key references erp.bd_laundry_priced_lines_v1(delivery_line_id),
 details_pending boolean not null,
 created_at timestamptz not null default statement_timestamp()
);

-- Actual cost can come from invoices while the original quote stays unknown.
-- All pieces must be returned and every source billed; reversing a bill reopens
-- the cost. Later bills cannot clear a blocker at an earlier closing date.
CREATE OR REPLACE FUNCTION erp.bf_delivery_invoiced_v1(p_line uuid,p_through date DEFAULT NULL)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce((select sum(r.qty_good_received+r.qty_bs_laundry)>=d.qty_sent_pcs
   and bool_and(exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 i on i.id=x.invoice_id
     where x.receipt_line_id=r.id and x.completes_source and i.status='POSTED'
       and(p_through is null or i.invoice_date<=p_through)))
   from erp.laundry_delivery_lines d join erp.laundry_receipt_lines r on r.delivery_line_id=d.id
   join erp.laundry_receipts h on h.id=r.receipt_id and h.status='POSTED'
   where d.id=p_line group by d.qty_sent_pcs),false)
$function$;

-- Vendor tariffs are authoritative. SKU membership is never a monetary override.
-- Keep this compatibility helper for existing callers; historical charge snapshots
-- are untouched and new charges carry the vendor rate version only.
CREATE OR REPLACE FUNCTION erp.bf_laundry_rate_v1(p_kind text,p_ref uuid,p_vendor uuid,p_group uuid,p_size uuid,p_at timestamptz)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare sku uuid;vid uuid;r jsonb;fallback record;reason text;amount numeric;
begin
 if p_kind='COMPONENT' then
   select * into fallback from erp.bd_component_rate_at_v1(p_ref,p_at);
   select x.reason into reason from erp.bd_laundry_component_rates_v1 x where id=fallback.version_id;
   return jsonb_build_object('rate',fallback.rate_per_pcs::text,'rate_status',fallback.rate_status,'reason',reason,'version_id',fallback.version_id,'sku_version_id',vid);
 elsif p_kind='PACKAGE' then
   select * into fallback from erp.bd_package_rate_at_v1(p_ref,p_at);
   return jsonb_build_object('rate',fallback.rate_per_pcs::text,'rate_status','KNOWN','version_id',fallback.version_id,'sku_version_id',vid);
 elsif p_kind='PROCESS' then
   amount:=erp.bd_process_rate_at_v1(p_vendor,p_ref,p_at);
   select id into sku from erp.laundry_vendor_rate_versions where vendor_id=p_vendor and wash_process_id=p_ref
     and effective_from<=p_at and(effective_to is null or effective_to>p_at);
   return jsonb_build_object('rate',amount::text,'rate_status','KNOWN','version_id',sku,'sku_version_id',vid);
 end if;
 raise exception 'BF_RATE_KIND';
end;$function$;

-- Combine only charges with identical tariff provenance. Two SKUs never acquire each other's price or receivers.
CREATE OR REPLACE FUNCTION erp.bf_merge_charges_v1(p_charges jsonb)
 RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path TO ''
AS $function$
 with charges as(select x, x-'amount'-'covered_qty'-'shares' metadata,n from jsonb_array_elements(p_charges) with ordinality j(x,n)),
 totals as(select metadata,min(n) n,sum((x->>'covered_qty')::bigint) qty,
   case when bool_and(x->>'amount' is not null) then sum((x->>'amount')::numeric)::text end amount from charges group by metadata)
 select coalesce(jsonb_agg(t.metadata||jsonb_build_object('covered_qty',t.qty,'amount',t.amount,
   'shares',(select jsonb_agg(s order by c.n) from charges c cross join lateral jsonb_array_elements(c.x->'shares') s where c.metadata=t.metadata)) order by t.n),'[]') from totals t
$function$;

CREATE OR REPLACE FUNCTION erp.bf_package_charges_v1(p_vendor uuid,p_package uuid,p_group uuid,p_at timestamptz,p_sizes uuid[],p_qtys integer[],p_included uuid[],p_name text)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare i integer;r jsonb;amount numeric;charges jsonb:='[]';
begin
 for i in 1..cardinality(p_sizes) loop
   r:=erp.bf_laundry_rate_v1('PACKAGE',p_package,p_vendor,p_group,p_sizes[i],p_at);
   amount:=round(p_qtys[i]*(r->>'rate')::numeric,2);
   charges:=charges||jsonb_build_object('kind','PACKAGE','ref_id',p_package,'version_id',r->'version_id','bf_sku_version_id',r->'sku_version_id',
     'label','Paket '||p_name,'covered_qty',p_qtys[i],'rate_status','KNOWN','unit_rate',r->>'rate','amount',amount::text,
     'shares',jsonb_build_array(jsonb_build_object('size_id',p_sizes[i],'amount',amount::text,'covered_qty',p_qtys[i])),
     'included_components',to_jsonb(p_included));
 end loop;
 return erp.bf_merge_charges_v1(charges);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bf_complete_shares_v1(p_charges jsonb,p_sizes uuid[])
 RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path TO ''
AS $function$
 select coalesce(jsonb_agg(j.x||jsonb_build_object('shares',(
   select jsonb_agg(coalesce((select s from jsonb_array_elements(j.x->'shares') s where s->>'size_id'=u.size_id::text),
     jsonb_build_object('size_id',u.size_id,'covered_qty',0,'amount','0.00')) order by u.n)
   from unnest(p_sizes) with ordinality u(size_id,n))) order by j.n),'[]')
 from jsonb_array_elements(p_charges) with ordinality j(x,n)
$function$;

CREATE OR REPLACE FUNCTION erp.bf_component_charge_v1(p_vendor uuid,p_line jsonb,p_at timestamptz,p_sizes uuid[],p_qtys integer[],p_total integer,
  p_kind text,p_seen uuid[],p_group uuid)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_id uuid:=erp.bd_uuid_v1(p_line,'component_id',true);v_cov integer:=erp.bd_qty_v1(p_line->'covered_qty','covered_qty');c record;r record;
  v_amount numeric;v_shares jsonb:='[]'::jsonb;i integer;v_weights integer[];v_x jsonb;v_size uuid;v_index integer;
  v_seen_sizes uuid[]:='{}';v_sum bigint:=0;v_qty integer;v_price_reason text;bf_rate jsonb;bf_charges jsonb:='[]';
begin
  if v_id=any(p_seen) then raise exception 'BD_COMPONENT_DUPLICATE: komponen yang sama dipilih dua kali untuk kiriman ini';end if;
  select * into c from erp.bd_laundry_components_v1 where id=v_id and vendor_id=p_vendor and is_active;
  if c.id is null then raise exception 'BD_COMPONENT_UNKNOWN: komponen aktif vendor ini wajib dipilih';end if;
  if v_cov>p_total then raise exception 'BD_COVERAGE_EXCEEDS_DELIVERY: cakupan % PCS melebihi kiriman % PCS',v_cov,p_total;end if;
  if cardinality(p_sizes)<>cardinality(p_qtys) or cardinality(p_sizes)=0
     or (select count(distinct x) from unnest(p_sizes) x)<>cardinality(p_sizes) then
    raise exception 'BD_COVERAGE_INVALID: ukuran kiriman harus unik dan lengkap';end if;
  v_weights:=array_fill(0,array[cardinality(p_sizes)]);
  if p_line ? 'coverage' then
    if jsonb_typeof(p_line->'coverage') is distinct from 'array' or jsonb_array_length(p_line->'coverage') not between 1 and cardinality(p_sizes) then
      raise exception 'BD_COVERAGE_INVALID: coverage wajib daftar ukuran penerima jasa';end if;
    for v_x in select value from jsonb_array_elements(p_line->'coverage') loop
      perform erp._cp3_assert_closed_json_object(v_x,array['size_id','qty'],array['size_id','qty'],'component coverage');
      v_size:=erp.bd_uuid_v1(v_x,'size_id',true);v_qty:=erp.bd_qty_v1(v_x->'qty','coverage qty');
      v_index:=array_position(p_sizes,v_size);
      if v_index is null or v_size=any(v_seen_sizes) or v_qty>p_qtys[v_index] then
        raise exception 'BD_COVERAGE_INVALID: ukuran asing/ganda atau qty jasa melebihi ukuran kiriman';end if;
      v_weights[v_index]:=v_qty;v_sum:=v_sum+v_qty;v_seen_sizes:=v_seen_sizes||v_size;
    end loop;
    if v_sum<>v_cov then raise exception 'BD_COVERAGE_MISMATCH: jumlah coverage harus sama dengan covered_qty';end if;
  elsif v_cov=p_total then
    v_weights:=p_qtys;
  elsif cardinality(p_sizes)=1 then
    -- A single source size is unambiguous, including legacy single-size callers.
    v_weights[1]:=v_cov;
  else
    raise exception 'BD_COVERAGE_REQUIRED: jasa parsial pada beberapa ukuran wajib menyebut ukuran dan qty penerimanya';
  end if;
  if p_kind='EXTRA' then perform erp.bc_text_v1(p_line,'reason',true,1000);end if;
  for i in 1..cardinality(p_sizes) loop
    if v_weights[i]=0 then continue;end if;
    bf_rate:=erp.bf_laundry_rate_v1('COMPONENT',v_id,p_vendor,p_group,p_sizes[i],p_at);
    v_amount:=case when bf_rate->>'rate_status'<>'UNKNOWN' then round(v_weights[i]*(bf_rate->>'rate')::numeric,2) end;
    bf_charges:=bf_charges||jsonb_build_object('kind',p_kind,'ref_id',v_id,'version_id',bf_rate->'version_id',
      'bf_sku_version_id',bf_rate->'sku_version_id','label',c.component_name,'covered_qty',v_weights[i],
      'rate_status',bf_rate->>'rate_status','unit_rate',bf_rate->>'rate','amount',v_amount::text,
      'shares',jsonb_build_array(jsonb_build_object('size_id',p_sizes[i],'covered_qty',v_weights[i],'amount',v_amount::text)),
      'price_reason',bf_rate->>'reason','reason',nullif(btrim(coalesce(p_line->>'reason','')),''));
  end loop;
  return erp.bf_complete_shares_v1(erp.bf_merge_charges_v1(bf_charges),p_sizes);
end;$function$;

-- Usual service selections and past observed amounts. No rate resolver calls
-- this reader. The next dispatch always resolves a fresh vendor version.
CREATE OR REPLACE FUNCTION public.erp_get_laundry_history_v1(p_filters jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare vendor uuid;wave uuid;at_time timestamptz;money boolean;result jsonb;
begin
 perform erp.require_permission('production.laundry.view');
 perform erp._cp3_assert_closed_json_object(p_filters,array['vendor_id','wave_id'],array['vendor_id','wave_id','at'],'laundry history');
 vendor:=erp.bd_uuid_v1(p_filters,'vendor_id',true);wave:=erp.bd_uuid_v1(p_filters,'wave_id',true);
 at_time:=coalesce((p_filters->>'at')::timestamptz,statement_timestamp());
 if at_time>statement_timestamp() then raise exception 'BF_HISTORY_FUTURE';end if;
 money:=erp.has_permission('finance.hpp.view') or erp.has_permission('finance.hpp.manage');
 with chosen as materialized(
   select w.sku_id,s.sku,array_agg(w.size_id order by w.size_id) sizes
   from erp.bf_wave_skus_v1 w join erp.bf_skus_v1 s on s.id=w.sku_id
   where w.cutting_group_id=wave and exists(select 1 from erp.bf_sku_versions_v1 v
     join erp.bf_sku_members_v1 m on m.version_id=v.id join erp.products p on p.id=m.product_root
     where v.sku_id=w.sku_id and p.size_id=w.size_id and v.effective_from<=at_time and(v.effective_to is null or v.effective_to>at_time))
   group by w.sku_id,s.sku
 ), past_sizes as materialized(
   select c.sku_id,l.id line_id,w.size_id from chosen c join erp.bf_wave_skus_v1 w on w.sku_id=c.sku_id
   join erp.laundry_delivery_lines l on l.cutting_group_id=w.cutting_group_id
   union
   select c.sku_id,r.delivery_line_id,p.size_id from chosen c
   join erp.bf_sku_versions_v1 v on v.sku_id=c.sku_id
   join erp.bf_sku_members_v1 m on m.version_id=v.id
   join erp.products p on p.identity_root_id=m.product_root
   join erp.fg_lots f on f.product_id=p.id and f.produced_at>=v.effective_from and(v.effective_to is null or f.produced_at<v.effective_to)
   join erp.qc_inspection_items qi on qi.id=f.qc_item_id
   join erp.laundry_receipt_lines r on r.id=qi.source_laundry_receipt_line_id
 ), history as materialized(
   select c.sku_id,c.sku,c.sizes target_sizes,d.id delivery_id,d.delivery_number,d.physical_at,
     d.target_wash_process_id process_id,l.id line_id,p.pricing_mode,p.total_complete,p.total_known,p.qty_sent,
     erp.bf_delivery_invoiced_v1(l.id,(at_time at time zone 'Asia/Jakarta')::date) actual_complete,
     (select array_agg(ps.size_id order by ps.size_id) from past_sizes ps where ps.line_id=l.id and ps.sku_id=c.sku_id) source_sizes
   from chosen c join erp.laundry_delivery_lines l on exists(select 1 from past_sizes ps where ps.line_id=l.id and ps.sku_id=c.sku_id)
   join erp.laundry_deliveries d on d.id=l.delivery_id and d.vendor_id=vendor and d.status not in('DRAFT','REVERSED') and d.physical_at<=at_time
   join erp.bd_laundry_priced_lines_v1 p on p.delivery_line_id=l.id
   order by d.physical_at desc,d.id,c.sku_id limit 20
 ) select jsonb_build_object('vendor_id',vendor,'wave_id',wave,'at',at_time,'money_visible',money,
   'known_skus',(select count(*) from chosen),
   'items',coalesce((select jsonb_agg(jsonb_build_object('sku_id',h.sku_id,'sku',h.sku,'target_size_ids',h.target_sizes,
     'delivery_id',h.delivery_id,'number',h.delivery_number,'at',h.physical_at,'process_id',h.process_id,'mode',h.pricing_mode,
     'reference_kind',case when h.actual_complete then 'ACTUAL' when h.total_complete then 'ESTIMATE' else 'UNKNOWN' end,
     'reference_total',case when money and h.actual_complete then (
       select sum(x.net_amount)::numeric(18,2)::text from erp.bd_laundry_invoice_lines_v1 x
       join erp.bd_laundry_invoices_v1 bill on bill.id=x.invoice_id and bill.status='POSTED' and bill.invoice_date<=(at_time at time zone 'Asia/Jakarta')::date
       join erp.laundry_receipt_lines receipt on receipt.id=x.receipt_line_id where receipt.delivery_line_id=h.line_id)
       when money and h.total_complete then h.total_known::numeric(18,2)::text end,
     'reference_qty',h.qty_sent,'amount_scope','WHOLE_PREVIOUS_DELIVERY',
     'charges',coalesce((select jsonb_agg(jsonb_build_object('kind',ch.kind,'ref_id',ch.ref_id,'label',ch.label,
       'all_source_pieces',not exists(select 1 from erp.bd_laundry_charge_shares_v1 sh join erp.laundry_delivery_batch_size_lines ds on ds.id=sh.delivery_batch_size_line_id
         where sh.charge_line_id=ch.id and ds.size_id=any(h.source_sizes) and sh.covered_qty<>ds.qty_sent_pcs)) order by ch.line_no)
       from erp.bd_laundry_charge_lines_v1 ch where ch.delivery_line_id=h.line_id and exists(
         select 1 from erp.bd_laundry_charge_shares_v1 sh join erp.laundry_delivery_batch_size_lines ds on ds.id=sh.delivery_batch_size_line_id
         where sh.charge_line_id=ch.id and sh.covered_qty>0 and ds.size_id=any(h.source_sizes))),
         jsonb_build_array(jsonb_build_object('kind','PROCESS_REFERENCE','ref_id',h.process_id,
           'label',(select process_name from erp.wash_processes where id=h.process_id),'all_source_pieces',true))))
     order by h.physical_at desc,h.delivery_id,h.sku_id) from history h),'[]')) into result;
 return result;
end;$function$;

-- Return credit starts on its original purchase. Moving it changes document
-- allocation only: AP in total, cash, physical stock and product costs stay put.
create table erp.bf_supplier_credit_moves_v1(
 id uuid primary key default gen_random_uuid(), return_id uuid not null references erp.material_supplier_returns(id),
 source_purchase_id uuid not null references erp.material_purchase_headers(id),
 target_purchase_id uuid not null references erp.material_purchase_headers(id),
 amount numeric(20,2) not null check(amount<>0), effective_date date not null,
 reversal_of uuid unique references erp.bf_supplier_credit_moves_v1(id),
 reason text not null, actor uuid, request_id uuid not null,
 journal_id uuid references erp.journal_entries(id), created_at timestamptz not null default clock_timestamp(),
 check(source_purchase_id<>target_purchase_id), check((amount>0)=(reversal_of is null))
);
create index bf_supplier_credit_source on erp.bf_supplier_credit_moves_v1(return_id,source_purchase_id);
create index bf_supplier_credit_target on erp.bf_supplier_credit_moves_v1(target_purchase_id,effective_date);

CREATE OR REPLACE FUNCTION erp.bf_supplier_credit_delta_v1(p_purchase uuid,p_through date DEFAULT NULL)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce(sum(case when source_purchase_id=p_purchase then amount else -amount end),0)
 from erp.bf_supplier_credit_moves_v1 where p_purchase in(source_purchase_id,target_purchase_id)
   and(p_through is null or effective_date<=p_through)
$function$;

CREATE OR REPLACE FUNCTION erp.bf_supplier_credit_source_v1(p_return uuid,p_purchase uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce((f.before_state->p_purchase::text->>'ap')::numeric-(f.after_state->p_purchase::text->>'ap')::numeric,0)
 from erp.supplier_cent_posting_facts f join erp.material_supplier_returns r on r.id=f.source_id and r.status='POSTED'
 where f.source_type='MATERIAL_SUPPLIER_RETURN' and f.phase='POST' and f.source_id=p_return
$function$;

CREATE OR REPLACE FUNCTION erp.bf_supplier_credit_revision_v1(p_return uuid)
 RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select md5(coalesce((select status||':'||row_version from erp.material_supplier_returns where id=p_return),'')||':'||
   coalesce((select string_agg(id::text,',' order by created_at,id) from erp.bf_supplier_credit_moves_v1 where return_id=p_return),''))
$function$;

CREATE OR REPLACE FUNCTION erp.bf_supplier_credit_guard_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
 if TG_TABLE_NAME='bf_supplier_credit_moves_v1' then raise exception 'BF_CREDIT_APPEND_ONLY';end if;
 if TG_TABLE_NAME='material_purchase_headers' then
   if old.status='POSTED' and new.status<>old.status and exists(select 1 from erp.bf_supplier_credit_moves_v1 e
     where old.id in(e.source_purchase_id,e.target_purchase_id) group by e.return_id,e.source_purchase_id,e.target_purchase_id having sum(e.amount)<>0) then
     raise exception 'BF_CREDIT_PURCHASE_IN_USE';end if;
   return new;
 end if;
 if old.status='POSTED' and new.status<>old.status and exists(
   select 1 from erp.bf_supplier_credit_moves_v1 e where e.return_id=old.id
   group by e.source_purchase_id,e.target_purchase_id having sum(e.amount)<>0) then
   raise exception 'BF_CREDIT_RETURN_IN_USE: kembalikan alokasi kredit sebelum membalik retur';end if;
 return new;
end;$function$;

CREATE OR REPLACE FUNCTION public.erp_get_supplier_credit_v1(p_filters jsonb DEFAULT '{}'::jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare supplier uuid; result jsonb; page_no integer;
begin
 perform erp.require_permission('finance.ap.view');
 perform erp._cp3_assert_closed_json_object(p_filters,array[]::text[],array['supplier_id','page'],'supplier credit filters');
 supplier:=erp.bd_uuid_v1(p_filters,'supplier_id',false);page_no:=greatest(1,coalesce((p_filters->>'page')::integer,1));
 with credits as materialized(
   select r.id return_id,r.return_number,r.supplier_id,r.physical_at,i.purchase_id source_purchase_id,h.purchase_number,
     erp.bf_supplier_credit_source_v1(r.id,i.purchase_id) credit,
     coalesce((select sum(e.amount) from erp.bf_supplier_credit_moves_v1 e where e.return_id=r.id and e.source_purchase_id=i.purchase_id),0) moved
   from erp.material_supplier_returns r join(select distinct return_id,purchase_id from erp.material_supplier_return_items ri
     join erp.material_purchase_items pi on pi.id=ri.purchase_item_id)i on i.return_id=r.id
   join erp.material_purchase_headers h on h.id=i.purchase_id
   where r.status='POSTED' and(supplier is null or r.supplier_id=supplier)
 ), positive as materialized(select * from credits where credit>0)
 select jsonb_build_object('supplier_id',supplier,'page',page_no,'total',(select count(*) from positive),
   'can_manage',erp.current_app_role() in('OWNER','ADMIN') and erp.has_permission('finance.ap.pay'),
   'suppliers',coalesce((select jsonb_agg(jsonb_build_object('id',s.id,'code',s.supplier_code,'name',s.supplier_name) order by s.supplier_name,s.id)
     from erp.suppliers s where exists(select 1 from erp.material_purchase_headers h where h.supplier_id=s.id and h.status='POSTED')),'[]'),
   'credits',coalesce((select jsonb_agg(jsonb_build_object('return_id',x.return_id,'return_number',x.return_number,'supplier_id',x.supplier_id,
     'source_purchase_id',x.source_purchase_id,'purchase_number',x.purchase_number,'physical_at',x.physical_at,
     'credit',x.credit::numeric(20,2)::text,'original_purchase_credit',(x.credit-x.moved)::numeric(20,2)::text,
     'version',erp.bf_supplier_credit_revision_v1(x.return_id),
     'allocations',coalesce((select jsonb_agg(jsonb_build_object('purchase_id',a.target_purchase_id,'amount',a.amount::numeric(20,2)::text))
       from(select e.target_purchase_id,sum(e.amount) amount from erp.bf_supplier_credit_moves_v1 e
         where e.return_id=x.return_id and e.source_purchase_id=x.source_purchase_id group by e.target_purchase_id having sum(e.amount)>0)a),'[]'),
     'events',coalesce((select jsonb_agg(jsonb_build_object('id',e.id,'purchase_id',e.target_purchase_id,'amount',e.amount::numeric(20,2)::text,
       'date',e.effective_date,'reason',e.reason,'reversal_of',e.reversal_of,'journal_id',e.journal_id) order by e.created_at,e.id)
       from erp.bf_supplier_credit_moves_v1 e where e.return_id=x.return_id and e.source_purchase_id=x.source_purchase_id),'[]'))
     order by x.physical_at desc,x.return_id,x.source_purchase_id) from(select * from positive order by physical_at desc,return_id,source_purchase_id limit 50 offset(page_no-1)*50)x),'[]'),
   'purchases',case when supplier is not null then coalesce((select jsonb_agg(jsonb_build_object('id',h.id,'number',h.purchase_number,
     'date',erp._cp3_business_date(h.physical_at),'final_ap',round(erp.material_purchase_final_ap_total(h.id),2)::text,
     'paid',p.paid::numeric(20,2)::text,'remaining',(round(erp.material_purchase_final_ap_total(h.id),2)-p.paid)::numeric(20,2)::text,
     'credit_delta',erp.bf_supplier_credit_delta_v1(h.id)::numeric(20,2)::text,'payment_status',h.payment_status) order by h.physical_at,h.id)
     from erp.material_purchase_headers h cross join lateral(select coalesce(sum(amount),0) paid from erp.supplier_payments where purchase_id=h.id and status='POSTED')p
     where h.supplier_id=supplier and h.status='POSTED'),'[]') else '[]'::jsonb end) into result;
 return result;
end;$function$;
create trigger bf_supplier_credit_append_only before update or delete on erp.bf_supplier_credit_moves_v1
 for each row execute function erp.bf_supplier_credit_guard_v1();
create trigger bf_supplier_return_credit_guard before update of status on erp.material_supplier_returns
 for each row execute function erp.bf_supplier_credit_guard_v1();
create trigger bf_supplier_purchase_credit_guard before update of status on erp.material_purchase_headers
 for each row execute function erp.bf_supplier_credit_guard_v1();

CREATE OR REPLACE FUNCTION erp.bf_supplier_credit_allocate_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare h erp.material_supplier_returns%rowtype; src uuid; reason text; today date:=erp.bb_business_today_v1();
 targets uuid[]; affected uuid[]; item jsonb; target uuid; amount numeric; total numeric:=0; credit numeric;
 row_move erp.bf_supplier_credit_moves_v1%rowtype; event_id uuid; journal uuid; amount_paid numeric; payable numeric;
begin
 perform erp._cp3_assert_closed_json_object(p_payload,array['return_id','source_purchase_id','expected_version','allocations','reason'],
   array['return_id','source_purchase_id','expected_version','allocations','reason'],'supplier credit allocation');
 src:=erp.bd_uuid_v1(p_payload,'source_purchase_id',true);reason:=erp.bc_text_v1(p_payload,'reason',true,1000);
 select * into h from erp.material_supplier_returns where id=erp.bd_uuid_v1(p_payload,'return_id',true) for update;
 if h.id is null or h.status<>'POSTED' then raise exception 'BF_CREDIT_RETURN_NOT_POSTED';end if;
 if erp._cp3_business_date(h.physical_at)>today then raise exception 'BF_CREDIT_NOT_YET_AVAILABLE';end if;
 if p_payload->>'expected_version' is distinct from erp.bf_supplier_credit_revision_v1(h.id) then raise exception 'STALE_VERSION';end if;
 if jsonb_typeof(p_payload->'allocations') is distinct from 'array' or jsonb_array_length(p_payload->'allocations')>100 then
   raise exception 'BF_CREDIT_ALLOCATIONS_INVALID';end if;
 targets:=array[src];
 for item in select value from jsonb_array_elements(p_payload->'allocations') loop
   perform erp._cp3_assert_closed_json_object(item,array['purchase_id','amount'],array['purchase_id','amount'],'credit target');
   target:=erp.bd_uuid_v1(item,'purchase_id',true);amount:=erp.bd_amount_v1(item->'amount','amount',false);
   if amount<=0 or amount<>round(amount,2) or target=any(targets) then raise exception 'BF_CREDIT_TARGET_INVALID';end if;
   total:=total+amount;targets:=targets||target;
 end loop;
 select array_agg(distinct x order by x) into affected from(
   select unnest(targets) x union select e.target_purchase_id from erp.bf_supplier_credit_moves_v1 e
     where e.return_id=h.id and e.source_purchase_id=src
     group by e.target_purchase_id having sum(e.amount)<>0) ids;
 perform 1 from erp.material_purchase_headers where id=any(affected) order by id for update;
 if (select count(*) from erp.material_purchase_headers where id=any(affected) and supplier_id=h.supplier_id
     and status='POSTED' and erp._cp3_business_date(physical_at)<=today)<>cardinality(affected) then
   raise exception 'BF_CREDIT_SAME_SUPPLIER_REQUIRED';end if;
 credit:=erp.bf_supplier_credit_source_v1(h.id,src);
 if credit is null or credit<=0 or total>credit then raise exception 'BF_CREDIT_EXCEEDS_RETURN';end if;
 -- Append inverses first; the following desired allocation is one transaction.
 for row_move in select e.* from erp.bf_supplier_credit_moves_v1 e where e.return_id=h.id and e.source_purchase_id=src and e.amount>0
   and not exists(select 1 from erp.bf_supplier_credit_moves_v1 undo where undo.reversal_of=e.id) order by e.id loop
   event_id:=gen_random_uuid();
   journal:=erp.post_journal('BF_SUPPLIER_CREDIT_MOVE',event_id,today,reason,
     jsonb_build_array(jsonb_build_object('mapping_key','AP_SUPPLIER','debit',row_move.amount,'credit',0),
       jsonb_build_object('mapping_key','AP_SUPPLIER','debit',0,'credit',row_move.amount)));
   insert into erp.bf_supplier_credit_moves_v1(id,return_id,source_purchase_id,target_purchase_id,amount,effective_date,reversal_of,reason,actor,request_id,journal_id)
     values(event_id,h.id,src,row_move.target_purchase_id,-row_move.amount,today,row_move.id,reason,erp.current_app_user_id(),p_request,journal);
 end loop;
 for item in select value from jsonb_array_elements(p_payload->'allocations') loop
   target:=(item->>'purchase_id')::uuid;amount:=(item->>'amount')::numeric;event_id:=gen_random_uuid();
   journal:=erp.post_journal('BF_SUPPLIER_CREDIT_MOVE',event_id,today,reason,
     jsonb_build_array(jsonb_build_object('mapping_key','AP_SUPPLIER','debit',amount,'credit',0),
       jsonb_build_object('mapping_key','AP_SUPPLIER','debit',0,'credit',amount)));
   insert into erp.bf_supplier_credit_moves_v1(id,return_id,source_purchase_id,target_purchase_id,amount,effective_date,reason,actor,request_id,journal_id)
     values(event_id,h.id,src,target,amount,today,reason,erp.current_app_user_id(),p_request,journal);
 end loop;
 foreach target in array affected loop
   select round(erp.material_purchase_final_ap_total(target),2),coalesce((select sum(p.amount) from erp.supplier_payments p
     where p.purchase_id=target and p.status='POSTED'),0) into payable,amount_paid;
   if payable<amount_paid then raise exception 'BF_CREDIT_TARGET_ALREADY_PAID: alokasi melewati sisa utang atau kredit sudah dipakai pembayaran';end if;
   update erp.material_purchase_headers set payment_status=case when amount_paid=payable then 'PAID' when amount_paid>0 then 'PARTIAL' else 'UNPAID' end where id=target;
 end loop;
 return jsonb_build_object('return_id',h.id,'source_purchase_id',src,'version',erp.bf_supplier_credit_revision_v1(h.id),
   'credit',credit::numeric(20,2)::text,'original_purchase_credit',(credit-total)::numeric(20,2)::text,'allocated_elsewhere',total::numeric(20,2)::text,'effective_date',today);
end;$function$;

CREATE OR REPLACE FUNCTION public.erp_save_supplier_credit_v1(p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare prior erp.bf_requests_v1%rowtype;result jsonb;actor uuid;
begin
 perform erp.require_owner_admin();perform erp.require_permission('finance.ap.pay');actor:=erp.current_app_user_id();
 if p_client_request_id is null then raise exception 'CLIENT_REQUEST_ID_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('BF:REQUEST:'||p_client_request_id,0));
 select * into prior from erp.bf_requests_v1 where request_id=p_client_request_id;
 if found then
   if prior.action<>'SUPPLIER_CREDIT_ALLOCATE' or prior.actor is distinct from actor or prior.payload is distinct from p_payload then
     raise exception 'CLIENT_REQUEST_ID_CONFLICT';end if;
   return prior.response||jsonb_build_object('replayed',true);
 end if;
 result:=erp.bf_supplier_credit_allocate_v1(p_payload,p_client_request_id)||jsonb_build_object('request_id',p_client_request_id,'replayed',false);
 insert into erp.bf_requests_v1 values(p_client_request_id,actor,'SUPPLIER_CREDIT_ALLOCATE',p_payload,result);
 return result;
end;$function$;

-- One physical identity for every historical row. Never distribute an imported aggregate.
CREATE OR REPLACE FUNCTION erp.bf_commercial_sku_at_v1(p_product uuid,p_at timestamptz)
 RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce(s.sku,p.sku) from erp.products p
 left join erp.bf_sku_versions_v1 v on v.id=erp.bf_version_at_v1(p.id,p_at)
 left join erp.bf_skus_v1 s on s.id=v.sku_id where p.id=p_product
$function$;

CREATE OR REPLACE FUNCTION erp.bf_resolve_import_product_v1(p_batch uuid,p_value jsonb,p_allow_staged boolean DEFAULT false,p_optional boolean DEFAULT false)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_at timestamptz;v_ids uuid[];v_count integer;v_staged integer;v_id uuid;v_key text;
begin
 select cutover_at into strict v_at from erp.migration_batches where id=p_batch;
 if nullif(btrim(p_value->>'product_sku'),'') is null and nullif(btrim(p_value->>'product_id'),'') is null then
   if p_optional then return null;end if;raise exception 'BF_IMPORT_PRODUCT_REQUIRED';
 end if;
 v_id:=erp.bd_uuid_v1(p_value,'product_id',false);
 select coalesce(array_agg(p.id),'{}') into v_ids from erp.products p
 join erp.brands b on b.id=p.brand_id join erp.product_models m on m.id=p.model_id join erp.sizes z on z.id=p.size_id
 where p.effective_from<=v_at and (v_id is null or p.id=v_id)
   and (nullif(btrim(p_value->>'product_sku'),'') is null or lower(btrim(p.sku))=lower(btrim(p_value->>'product_sku'))
     or lower(btrim(erp.bf_commercial_sku_at_v1(p.id,v_at)))=lower(btrim(p_value->>'product_sku')))
   and (nullif(btrim(p_value->>'size_code'),'') is null or lower(btrim(z.size_code))=lower(btrim(p_value->>'size_code')))
   and (nullif(btrim(p_value->>'brand_code'),'') is null or lower(btrim(b.brand_code))=lower(btrim(p_value->>'brand_code')))
   and (nullif(btrim(p_value->>'model_code'),'') is null or lower(btrim(m.model_code))=lower(btrim(p_value->>'model_code')))
   and (nullif(btrim(p_value->>'color_name'),'') is null or lower(btrim(p.color_name))=lower(btrim(p_value->>'color_name')));
 v_count:=cardinality(v_ids);v_staged:=0;
 if p_allow_staged and v_id is null then
   select count(*) into v_staged from erp.migration_staging_rows s
   where s.batch_id=p_batch and s.entity_type='PRODUCT' and s.validation_status='VALID'
     and lower(btrim(s.normalized_payload->>'sku'))=lower(btrim(p_value->>'product_sku'))
     and not exists(select 1 from unnest(array['size_code','brand_code','model_code','color_name']) k
       where nullif(btrim(p_value->>k),'') is not null and lower(btrim(s.normalized_payload->>k)) is distinct from lower(btrim(p_value->>k)))
     and not exists(select 1 from erp.products p join erp.brands b on b.id=p.brand_id join erp.product_models m on m.id=p.model_id join erp.sizes z on z.id=p.size_id
       where p.id=any(v_ids) and lower(btrim(b.brand_code))=lower(btrim(s.normalized_payload->>'brand_code'))
       and lower(btrim(m.model_code))=lower(btrim(s.normalized_payload->>'model_code')) and lower(btrim(z.size_code))=lower(btrim(s.normalized_payload->>'size_code'))
       and lower(btrim(p.color_name))=lower(btrim(s.normalized_payload->>'color_name')));
 end if;
 if v_count+v_staged=0 then raise exception 'BF_IMPORT_PRODUCT_NOT_FOUND: identitas fisik tidak cocok pada cutover';end if;
 if v_count+v_staged<>1 then raise exception 'SIZE_ALLOCATION_REQUIRED: SKU punya % identitas; isi product_id atau size_code/merek/model/warna sumber historis',v_count+v_staged;end if;
 return v_ids[1];
end;$function$;

CREATE OR REPLACE FUNCTION erp.save_sku_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare a text:=upper(btrim(p_action)); prior erp.bf_requests_v1%rowtype; result jsonb;
begin
 if erp.current_app_user_id() is null then raise exception 'BF_AUTH_REQUIRED';end if;
 if p_client_request_id is null then raise exception 'BF_REQUEST_REQUIRED';end if;
 if a not in('SAVE_GROUPS','BIND_WAVE') then raise exception 'BF_ACTION';end if;
 perform pg_advisory_xact_lock(hashtextextended('BFREQ:'||p_client_request_id::text,0));
 -- Permissions before cache, including replay following a live role change.
 if a='SAVE_GROUPS' then
   perform erp.require_owner_admin();perform erp.require_permission('master.product.manage');perform erp.require_permission('finance.hpp.manage');
 else perform erp.require_permission('production.cutting.edit_draft');end if;
 select * into prior from erp.bf_requests_v1 where request_id=p_client_request_id;
 if prior.request_id is not null then
   if prior.actor is distinct from erp.current_app_user_id() or prior.action<>a or prior.payload<>p_payload then raise exception 'BF_REQUEST_REUSED';end if;
   return prior.response||jsonb_build_object('replayed',true);
 end if;
 result:=case a when 'SAVE_GROUPS' then erp.bf_save_groups_v1(p_payload,p_client_request_id) else erp.bf_bind_wave_v1(p_payload,p_client_request_id) end;
 result:=result||jsonb_build_object('action',a,'request_id',p_client_request_id,'status','SAVED');
 insert into erp.bf_requests_v1 values(p_client_request_id,erp.current_app_user_id(),a,p_payload,result);
 return result;
end;$function$;

CREATE OR REPLACE FUNCTION erp.get_sku_workspace_v1(p_filters jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare page_no integer:=greatest(1,coalesce((p_filters->>'page')::integer,1)); q text:=coalesce(p_filters->>'query','');
 at_time timestamptz:=coalesce((p_filters->>'at')::timestamptz,statement_timestamp()); roots uuid[]; result jsonb; money boolean;
begin
 perform erp.require_permission('master.product.view');
 money:=erp.has_permission('finance.hpp.view') or erp.has_permission('finance.hpp.manage');
 select coalesce(array_agg(x::uuid),'{}') into roots from jsonb_array_elements_text(coalesce(p_filters->'roots','[]')) x;
 if cardinality(roots)>500 then raise exception 'BF_MEMBER_LIMIT';end if;
 if cardinality(roots)>0 and not money then raise exception 'BF_PRICE_PERMISSION';end if;
 with g as materialized(
   select s.*,v.id version_id,v.revision selected_revision,v.effective_from,v.effective_to,v.settings,b.brand_name,m.model_name,
     coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'size_id',p.size_id,'size',z.size_code) order by z.sort_order,z.size_code,p.id)
       from erp.bf_sku_members_v1 sm join erp.products p on p.id=sm.product_root join erp.sizes z on z.id=p.size_id
       where sm.version_id=v.id),'[]') members
   from erp.bf_skus_v1 s join erp.brands b on b.id=s.brand_id join erp.product_models m on m.id=s.model_id
   join lateral(select x.* from erp.bf_sku_versions_v1 x where x.sku_id=s.id
     and x.effective_from<=at_time and (x.effective_to is null or x.effective_to>at_time)
     order by x.revision desc limit 1) v on true
   where s.sku ilike '%'||q||'%' or b.brand_name ilike '%'||q||'%' or exists(select 1 from erp.bf_sku_members_v1 sm where sm.version_id=v.id and sm.product_root=any(roots))
 ), products as materialized(
   select p.id,p.sku,p.brand_id,b.brand_name,p.model_id,m.model_name,p.color_name,p.size_id,z.size_code size,
     (select v.sku_id from erp.bf_sku_members_v1 sm join erp.bf_sku_versions_v1 v on v.id=sm.version_id
       where sm.product_root=p.id and v.effective_from<=at_time and(v.effective_to is null or v.effective_to>at_time)) group_id
   from erp.products p join erp.brands b on b.id=p.brand_id join erp.product_models m on m.id=p.model_id join erp.sizes z on z.id=p.size_id
   where p.id=p.identity_root_id and p.is_active and (p.sku ilike '%'||q||'%' or b.brand_name ilike '%'||q||'%' or p.id=any(roots))
 ) select jsonb_build_object('at',at_time,'page',page_no,'page_size',50,'groups_total',(select count(*) from g),
   'groups',coalesce((select jsonb_agg(to_jsonb(x)) from(select id,sku,brand_id,brand_name,model_id,model_name,color_name,revision::text,selected_revision::text,version_id,
      effective_from,effective_to,members,case when money then settings end settings from g order by brand_name,sku,id limit 50 offset (page_no-1)*50)x),'[]'),
   'products_total',(select count(*) from products),'products',coalesce((select jsonb_agg(to_jsonb(x)) from(select * from products order by brand_name,sku,size,id limit 50 offset (page_no-1)*50)x),'[]'),
   'related_groups',coalesce((select jsonb_agg(to_jsonb(x)) from(select id,sku,brand_id,brand_name,model_id,model_name,color_name,revision::text,selected_revision::text,version_id,effective_from,effective_to,members,case when money then settings end settings from g
     where exists(select 1 from jsonb_array_elements(members) mem where (mem->>'id')::uuid=any(roots)))x),'[]'),
   'wave',case when nullif(p_filters->>'wave_id','') is not null then (select jsonb_build_object('id',cg.id,'number',cg.group_number,
     'revision',erp.bf_wave_revision_v1(cg.id),'can_bind',erp.has_permission('production.cutting.edit_draft'),
     'sizes',coalesce((select jsonb_agg(jsonb_build_object('id',z.id,'name',z.size_code,'sku_id',w.sku_id,'sku',s.sku) order by z.sort_order,z.size_code)
       from (select distinct size_id from erp.cutting_group_size_slots where cutting_group_id=cg.id) sl
       join erp.sizes z on z.id=sl.size_id
       left join erp.bf_wave_skus_v1 w on w.cutting_group_id=cg.id and w.size_id=z.id left join erp.bf_skus_v1 s on s.id=w.sku_id
       ),'[]')) from erp.cutting_groups cg where cg.id=(p_filters->>'wave_id')::uuid) end,
   'selected_products',coalesce((select jsonb_agg(to_jsonb(x)) from products x where id=any(roots)),'[]'),
   'lookups',case when money then jsonb_build_object(
     'accessories',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',category_name,'unit',base_uom_code) order by category_name,id) from erp.accessory_categories where is_active),'[]'),
     'work',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',component_name,'category',component_category) order by sequence_default,id) from erp.work_components where is_active),'[]'),
     'contractors',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',contractor_name) order by contractor_name,id) from erp.contractors where is_active),'[]'),
     'vendors',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',vendor_name) order by vendor_name,id) from erp.laundry_vendors where is_active),'[]'),
     'laundry',coalesce((select jsonb_agg(to_jsonb(x)) from(
       select id,process_name name,'PROCESS' kind,null::uuid vendor_id from erp.wash_processes where is_active
       union all select id,component_name,'COMPONENT',vendor_id from erp.bd_laundry_components_v1 where is_active
       union all select id,package_name,'PACKAGE',vendor_id from erp.bd_laundry_packages_v1 where is_active)x),'[]')) end,
   'legacy_basis',case when money then erp.bf_legacy_basis_v1(roots,at_time) end,'can_edit',erp.has_permission('master.product.manage') and erp.has_permission('finance.hpp.manage') and erp.current_app_role() in('OWNER','ADMIN')) into result;
 return result;
end;$function$;

CREATE OR REPLACE FUNCTION erp.get_sku_hpp_v1(p_filters jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare at_time timestamptz:=coalesce((p_filters->>'at')::timestamptz,statement_timestamp()); result jsonb;
 page_no integer:=greatest(1,coalesce((p_filters->>'page')::integer,1));
begin
 perform erp.require_permission('finance.hpp.view');
 if at_time>statement_timestamp() then raise exception 'BF_REPORT_FUTURE';end if;
 with stock as materialized(
   select m.lot_id,m.product_id,m.location_id,m.quality_grade,sum(m.qty_signed)::bigint qty
   from erp.fg_stock_movements m where m.physical_at<=at_time
     and(nullif(p_filters->>'location_id','') is null or m.location_id=(p_filters->>'location_id')::uuid)
     and(nullif(p_filters->>'grade','') is null or m.quality_grade=p_filters->>'grade')
   group by m.lot_id,m.product_id,m.location_id,m.quality_grade having sum(m.qty_signed)<>0
 ), facts as materialized(
   select coalesce(s.id::text,p.brand_id::text||':'||p.sku) group_key,coalesce(s.sku,p.sku) sku,
     p.brand_id,b.brand_name,z.size_code size,st.*,l.lot_number,h.id hpp_version_id,h.cost_state,
     (st.qty*h.total_cost/nullif(h.qty_basis_pcs,0)) value,
     (h.id is null or h.cost_state='ESTIMATED' or erp.bd_lot_laundry_unknown_v1(l.id) or (l.po_id is not null and exists(select 1 from erp.get_hpp_completeness(l.po_id) c where c.pending_reason_count>0))) provisional
   from stock st join erp.fg_lots l on l.id=st.lot_id join erp.products p on p.id=st.product_id
   join erp.brands b on b.id=p.brand_id join erp.sizes z on z.id=p.size_id
   left join erp.bf_sku_versions_v1 v on v.id=erp.bf_version_at_v1(p.id,at_time)
   left join erp.bf_skus_v1 s on s.id=v.sku_id
   left join lateral(select x.* from erp.hpp_versions x where x.lot_id=l.id and x.calculated_at<=at_time order by x.calculated_at desc,x.version_no desc limit 1) h on true
 ), groups as materialized(
   select group_key,sku,brand_id,brand_name,sum(qty)::bigint qty,
     case when bool_and(value is not null) then sum(value) end value,bool_or(provisional) provisional,
     jsonb_agg(jsonb_build_object('lot_id',lot_id,'lot_number',lot_number,'product_id',product_id,'size',size,'location_id',location_id,
       'grade',quality_grade,'qty',qty::text,'value',value::text,'hpp_version_id',hpp_version_id,'cost_state',cost_state,'provisional',provisional)
       order by size,lot_number,location_id,quality_grade) lots
   from facts group by group_key,sku,brand_id,brand_name
 ), filtered as materialized(
   select * from groups where (nullif(p_filters->>'brand_id','') is null or brand_id=(p_filters->>'brand_id')::uuid)
     and (sku ilike '%'||coalesce(p_filters->>'query','')||'%' or brand_name ilike '%'||coalesce(p_filters->>'query','')||'%')
 ) select jsonb_build_object('at',at_time,'page',page_no,'page_size',50,'total',(select count(*) from filtered),
   'groups',coalesce((select jsonb_agg(to_jsonb(x)) from(select group_key,sku,brand_id,brand_name,qty::text,value::text,
     (value/nullif(qty,0))::text hpp_per_pcs,provisional,lots from filtered order by brand_name,sku,group_key limit 50 offset (page_no-1)*50)x),'[]')) into result;
 return result;
end;$function$;

CREATE OR REPLACE FUNCTION public.erp_save_sku_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.save_sku_action_v1(p_action,p_payload,p_client_request_id) $function$;
CREATE OR REPLACE FUNCTION public.erp_get_sku_workspace_v1(p_filters jsonb DEFAULT '{}'::jsonb)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.get_sku_workspace_v1(p_filters) $function$;
CREATE OR REPLACE FUNCTION public.erp_get_sku_hpp_v1(p_filters jsonb DEFAULT '{}'::jsonb)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.get_sku_hpp_v1(p_filters) $function$;

CREATE OR REPLACE FUNCTION erp.commit_accessory_bom_for_lot(p_lot_id uuid)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  l erp.fg_lots%rowtype; p erp.production_orders%rowtype; v_product_model uuid; v_root uuid; v_bom uuid; v_distinct_boms integer;
begin
  perform erp.require_internal();
  select * into l from erp.fg_lots where id=p_lot_id for update;
  if l.id is null or l.lot_origin<>'PRODUCTION' then return null; end if;
  select * into p from erp.production_orders where id=l.po_id for update;
  if p.id is null then raise exception 'Production PO untuk lot FG tidak ditemukan'; end if;
  select model_id,identity_root_id into v_product_model,v_root from erp.products where id=l.product_id;
  if v_product_model is distinct from p.model_id then raise exception 'FG SKU model does not match production order model'; end if;

  select c.bom_version_id into v_bom from erp.po_accessory_bom_commitments c where c.po_id=l.po_id and c.product_id=l.product_id;
  if v_bom is not null then return v_bom; end if;

  select count(distinct c.bom_version_id) into v_distinct_boms
  from erp.po_accessory_bom_commitments c join erp.products cp on cp.id=c.product_id
  where c.po_id=l.po_id and cp.identity_root_id=v_root;
  if coalesce(v_distinct_boms,0)>1 then raise exception 'PO memiliki lebih dari satu accessory BOM commitment untuk logical SKU yang sama. Koreksi histori commitment sebelum membuat FG baru.'; end if;
  if coalesce(v_distinct_boms,0)=1 then
    select c.bom_version_id into v_bom from erp.po_accessory_bom_commitments c join erp.products cp on cp.id=c.product_id
    where c.po_id=l.po_id and cp.identity_root_id=v_root order by c.committed_at,c.id limit 1;
  else
    v_bom:=erp.bf_bom_for_lot_v1(p_lot_id);
    if v_bom is null then
    perform pg_advisory_xact_lock(hashtextextended('ABOM:'||v_root::text,0));
    select abv.id into v_bom from erp.accessory_bom_versions abv
    where abv.product_id=v_root and abv.is_active=true and abv.effective_from<=l.produced_at and (abv.effective_to is null or abv.effective_to>l.produced_at)
    order by abv.effective_from desc,abv.created_at desc,abv.id desc limit 1;
    end if;
    if v_bom is null then
      raise exception 'Accessory BOM SKU belum diset pada tanggal FG %. Setup BOM sebelum first HPP use. Jika produk memang tanpa aksesori, buat BOM version kosong sebagai deklarasi NO ACCESSORY.',l.produced_at;
    end if;
  end if;

  insert into erp.po_accessory_bom_commitments(po_id,product_id,bom_version_id,committed_at,commit_source,committed_by)
  values(l.po_id,l.product_id,v_bom,l.produced_at,'FIRST_FINANCIAL_USE',erp.current_app_user_id())
  on conflict (po_id,product_id) do nothing;
  select c.bom_version_id into v_bom from erp.po_accessory_bom_commitments c where c.po_id=l.po_id and c.product_id=l.product_id;
  return v_bom;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.ensure_po_work_component_snapshots(p_po_id uuid, p_basis_at timestamp with time zone DEFAULT statement_timestamp())
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  p erp.production_orders%rowtype;
  v_bom uuid;
  r record;
  v_rate_id uuid;
  v_rate numeric(18,2);
  v_count integer;
begin
  perform erp.require_internal();
  select * into p from erp.production_orders where id=p_po_id for update;
  if p.id is null then raise exception 'PO not found'; end if;
  if p.contractor_id is null then raise exception 'PO must have a mandor/contractor before work-rate snapshot'; end if;
  select count(*) into v_count from erp.po_work_component_snapshots where po_id=p.id and bf_sku_version_id is null;
  if v_count>0 then perform erp.bf_ensure_work_v1(p_po_id,p_basis_at);return v_count; end if;

  perform pg_advisory_xact_lock(hashtextextended('WBOM:'||p.model_id::text,0));
  select wbv.id into v_bom
  from erp.work_bom_versions wbv
  where wbv.model_id=p.model_id and wbv.is_active=true
    and wbv.effective_from<=p_basis_at and (wbv.effective_to is null or wbv.effective_to>p_basis_at)
    and exists(select 1 from erp.work_bom_items wbi where wbi.bom_version_id=wbv.id)
  order by wbv.effective_from desc,wbv.version_no desc,wbv.id desc limit 1;
  if v_bom is null then raise exception 'No active Work BOM for PO model at %',p_basis_at; end if;

  for r in select * from erp.work_bom_items where bom_version_id=v_bom order by sequence_no,id loop
    v_rate_id:=null; v_rate:=null;
    perform pg_advisory_xact_lock(hashtextextended('WRATE:'||p.contractor_id::text||':'||p.model_id::text||':'||r.work_component_id::text,0));
    select cwr.id,cwr.rate_per_pcs into v_rate_id,v_rate
    from erp.contractor_work_rates cwr
    where cwr.contractor_id=p.contractor_id and cwr.model_id=p.model_id and cwr.work_component_id=r.work_component_id
      and cwr.effective_from<=p_basis_at and (cwr.effective_to is null or cwr.effective_to>p_basis_at)
    order by cwr.effective_from desc,cwr.id desc limit 1;
    v_rate:=coalesce(v_rate,r.default_rate);
    if v_rate is null or v_rate<0 then raise exception 'No valid work rate for component %',r.work_component_id; end if;
    insert into erp.po_work_component_snapshots(
      po_id,work_component_id,source_bom_version_id,source_bom_item_id,source_contractor_rate_id,
      sequence_no,rate_per_pcs_snapshot,committed_at
    ) values(p.id,r.work_component_id,v_bom,r.id,v_rate_id,r.sequence_no,v_rate,p_basis_at);
  end loop;
  select count(*) into v_count from erp.po_work_component_snapshots where po_id=p.id and bf_sku_version_id is null;
  if v_count=0 then raise exception 'Work BOM snapshot produced no components'; end if;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('production_orders',p.id,'WORK_BOM_COMMIT',jsonb_build_object('bom_version_id',v_bom,'committed_at',p_basis_at,'component_count',v_count),erp.current_app_user_id(),'First work-rate/BOM use');
  perform erp.bf_ensure_work_v1(p_po_id,p_basis_at);
  return v_count;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.validate_work_completion()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_event_po uuid;
  v_event_contractor uuid;
  v_po_contractor uuid;
  v_snapshot_po uuid;
  v_snapshot_component uuid;
  v_snapshot_rate numeric(18,2);
begin
  perform erp.require_internal();
  select e.po_id,e.contractor_id into v_event_po,v_event_contractor
  from erp.work_completion_events e where e.id=new.completion_id for share of e;
  select p.contractor_id into v_po_contractor
  from erp.production_orders p where p.id=v_event_po;
  select s.po_id,s.work_component_id,s.rate_per_pcs_snapshot
  into v_snapshot_po,v_snapshot_component,v_snapshot_rate
  from erp.po_work_component_snapshots s where s.id=new.po_component_snapshot_id for share of s;
  if v_event_po is null then raise exception 'Completion event not found'; end if;
  if v_po_contractor is distinct from v_event_contractor then
    raise exception 'Completion contractor must match PO contractor';
  end if;
  if v_snapshot_po is distinct from v_event_po
     or v_snapshot_component is distinct from new.work_component_id
     or v_snapshot_rate is null then
    raise exception 'Work component snapshot does not match completion PO/component';
  end if;
  perform erp.bf_assert_work_scope_v1(new.completion_id,new.po_component_snapshot_id);
  new.rate_snapshot:=v_snapshot_rate;
  return new;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.guard_work_completion_posting_consistency()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_pickup timestamptz;
  v_effective bigint;
  r record;
  v_prior_completed bigint;
  v_prior_payable bigint;
  v_scope_capacity bigint;
begin
  if new.status='POSTED' and old.status is distinct from 'POSTED' then
    -- The DRAFT header may have changed after its lines were normalized.
    -- Recheck the current source before any work, payable or HPP is recognized.
    if not exists(select 1 from erp.production_orders ai_po
      where ai_po.id=new.po_id and ai_po.contractor_id=new.contractor_id) then
      raise exception 'AI_WORK_SOURCE_CONTRACTOR_MISMATCH';
    end if;
    perform 1 from erp.po_work_component_snapshots ai_snapshot
      join erp.work_completion_lines ai_line on ai_line.po_component_snapshot_id=ai_snapshot.id
      where ai_line.completion_id=new.id order by ai_snapshot.id for share of ai_snapshot;
    if exists(
      select 1 from erp.work_completion_lines ai_line
      left join erp.po_work_component_snapshots ai_snapshot on ai_snapshot.id=ai_line.po_component_snapshot_id
      where ai_line.completion_id=new.id and (
        ai_snapshot.id is null or ai_snapshot.po_id is distinct from new.po_id
        or ai_snapshot.work_component_id is distinct from ai_line.work_component_id
        or ai_snapshot.rate_per_pcs_snapshot is distinct from ai_line.rate_snapshot)
    ) then
      raise exception 'AI_WORK_SOURCE_SNAPSHOT_MISMATCH: rebuild the draft lines for the selected PO before posting';
    end if;

    -- BB (ALL-W02): wages after cutover on an opening WIP (no Potongan) have that opening WIP as their source.
    if new.cutting_group_id is null and new.bb_opening_item_id is not null then
      perform erp.bb_check_opening_work_v1(new.id);
      return new;
    end if;
    if new.cutting_group_id is null then
      raise exception 'Hasil kerja mandor wajib terkait Potongan. Pilih Potongan sebelum posting agar qty/upah/HPP tidak masuk ke grup yang salah.';
    end if;

    -- Serialize all work postings for the same Potongan so two tabs cannot both
    -- consume the same remaining component entitlement concurrently.
    perform 1 from erp.cutting_groups cg where cg.id=new.cutting_group_id for update;
    if not found then raise exception 'Potongan sumber hasil kerja tidak ditemukan'; end if;

    select cg.picked_up_at,coalesce(v.total_pcs,0)
      into v_pickup,v_effective
    from erp.cutting_groups cg
    left join erp.v_cutting_group_totals v on v.cutting_group_id=cg.id
    where cg.id=new.cutting_group_id and cg.po_id=new.po_id;

    if v_pickup is null then
      raise exception 'Potongan belum diambil mandor. Hasil kerja/upah tidak boleh dipost sebelum assignment/pickup fisik.';
    end if;
    if new.physical_at < v_pickup then
      raise exception 'Tanggal hasil kerja (%) lebih awal dari tanggal Potongan diambil mandor (%). Periksa tanggal sebelum posting.',new.physical_at,v_pickup;
    end if;
    if new.physical_at > clock_timestamp()+interval '5 minutes' then
      raise exception 'Tanggal/jam hasil kerja berada di masa depan. Periksa tanggal/jam sebelum posting.';
    end if;
    if v_effective<=0 then
      raise exception 'Potongan tidak memiliki qty efektif yang dapat menjadi dasar upah.';
    end if;

    for r in
      select l.id,l.po_component_snapshot_id,l.work_component_id,l.qty_completed,l.qty_payable,wc.component_name
      from erp.work_completion_lines l
      join erp.work_components wc on wc.id=l.work_component_id
      where l.completion_id=new.id
      order by l.work_component_id,l.id
    loop
      perform erp.bf_assert_work_scope_v1(new.id,r.po_component_snapshot_id);
      v_scope_capacity:=erp.bf_work_capacity_v1(new.cutting_group_id,r.po_component_snapshot_id,v_effective);
      select coalesce(sum(l2.qty_completed),0),coalesce(sum(l2.qty_payable),0)
        into v_prior_completed,v_prior_payable
      from erp.work_completion_lines l2
      join erp.work_completion_events e2 on e2.id=l2.completion_id
      where e2.cutting_group_id=new.cutting_group_id
        and l2.work_component_id=r.work_component_id
        and erp.bf_snapshot_sku_v1(l2.po_component_snapshot_id) is not distinct from erp.bf_snapshot_sku_v1(r.po_component_snapshot_id)
        and e2.status='POSTED'
        and e2.id<>new.id;

      if v_prior_completed+r.qty_completed>v_scope_capacity then
        raise exception 'Qty selesai komponen % melebihi Potongan efektif. Potongan %, sudah dipost %, input %, maksimum %.',
          r.component_name,new.cutting_group_id,v_prior_completed,r.qty_completed,v_effective;
      end if;
      if v_prior_payable+r.qty_payable>v_scope_capacity then
        raise exception 'Qty bayar komponen % melebihi Potongan efektif. Sudah menjadi hak bayar %, input %, maksimum %. Koreksi hasil kerja, jangan membayar dua kali.',
          r.component_name,v_prior_payable,r.qty_payable,v_effective;
      end if;
    end loop;
  end if;
  return new;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.seed_bs_case_component_baseline()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
begin
  if new.po_id is null then return new; end if;
  insert into erp.bs_case_components(
    bs_case_id,po_component_snapshot_id,work_component_id,
    completed_before_bs_qty,notes
  )
  select
    new.id,s.id,s.work_component_id,
    least(
      new.qty_pcs,
      coalesce((
        select sum(wcl.qty_completed)::integer
        from erp.work_completion_lines wcl
        join erp.work_completion_events wce on wce.id=wcl.completion_id
        where wce.po_id=new.po_id
          and wcl.work_component_id=s.work_component_id
          and erp.bf_snapshot_sku_v1(wcl.po_component_snapshot_id) is not distinct from erp.bf_snapshot_sku_v1(s.id)
          and wce.status='POSTED'
          and wce.physical_at<=new.physical_at
          and (new.cutting_group_id is null or wce.cutting_group_id=new.cutting_group_id)
      ),0)
    ),
    'Auto baseline from posted work history at BS detection'
  from erp.po_work_component_snapshots s
  where s.po_id=new.po_id and erp.bf_snapshot_matches_v1(s.id,new.cutting_group_id,new.product_id)
  on conflict(bs_case_id,work_component_id) do nothing;
  return new;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.classify_bs_case_v2(p_bs_case_id uuid, p_payload jsonb, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_case erp.bs_cases%rowtype;
  v_cause text;v_contractor uuid;v_vendor uuid;
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_component jsonb;v_snapshot uuid;
begin
  perform erp.require_internal();
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if v_reason is null then raise exception 'change_reason is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'bs_case_id',p_bs_case_id,'payload',p_payload,'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin('classify_bs_case_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  select * into v_case from erp.bs_cases where id=p_bs_case_id for update;
  if v_case.id is null then raise exception 'BS case not found'; end if;
  if v_case.status not in('OPEN','PARTIAL','IN_REWORK') then raise exception 'Closed/cancelled BS case cannot be classified'; end if;
  if v_case.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_case.row_version;
  end if;
  v_cause:=upper(coalesce(nullif(p_payload->>'cause_source',''),v_case.cause_source));
  v_contractor:=case when p_payload?'responsible_contractor_id'
    then nullif(p_payload->>'responsible_contractor_id','')::uuid else v_case.responsible_contractor_id end;
  v_vendor:=case when p_payload?'responsible_vendor_id'
    then nullif(p_payload->>'responsible_vendor_id','')::uuid else v_case.responsible_vendor_id end;
  if v_cause='SEWING' and v_contractor is null then raise exception 'SEWING cause requires responsible contractor'; end if;
  if v_cause='LAUNDRY' and v_vendor is null then raise exception 'LAUNDRY cause requires responsible vendor'; end if;
  if v_cause not in('SEWING','LAUNDRY','UNKNOWN') then raise exception 'Invalid cause_source'; end if;
  perform set_config('app.change_reason',v_reason,true);
  update erp.bs_cases
  set cause_source=v_cause,responsible_contractor_id=v_contractor,
      responsible_vendor_id=v_vendor,
      untracked_type=case when v_cause='UNKNOWN' then untracked_type else null end,
      notes=case when p_payload?'notes' then nullif(btrim(p_payload->>'notes'),'') else notes end,
      legacy_reference=case when p_payload?'legacy_reference' then nullif(btrim(p_payload->>'legacy_reference'),'') else legacy_reference end,
      updated_at=statement_timestamp()
  where id=v_case.id returning * into v_case;

  if p_payload?'components' then
    if exists(
      select 1 from erp.rework_component_lines rcl
      join erp.bs_case_components bcc on bcc.id=rcl.bs_case_component_id
      where bcc.bs_case_id=v_case.id
    ) then raise exception 'BS components are frozen after rework lines exist'; end if;
    if jsonb_typeof(p_payload->'components')<>'array' then raise exception 'components must be an array'; end if;
    delete from erp.bs_case_components where bs_case_id=v_case.id;
    for v_component in select value from jsonb_array_elements(p_payload->'components') loop
      select id into v_snapshot from erp.po_work_component_snapshots
      where po_id=v_case.po_id and work_component_id=(v_component->>'work_component_id')::uuid
        and erp.bf_snapshot_matches_v1(id,v_case.cutting_group_id,v_case.product_id)
      order by committed_at desc,id desc limit 1;
      insert into erp.bs_case_components(
        bs_case_id,po_component_snapshot_id,work_component_id,completed_before_bs_qty,notes
      ) values(
        v_case.id,v_snapshot,(v_component->>'work_component_id')::uuid,
        coalesce(nullif(v_component->>'completed_before_bs_qty','')::integer,0),
        nullif(btrim(v_component->>'notes'),'')
      );
    end loop;
    update erp.bs_cases set updated_at=statement_timestamp() where id=v_case.id returning * into v_case;
  end if;
  v_response:=jsonb_build_object(
    'bs_case_id',v_case.id,'status',v_case.status,'cause_source',v_case.cause_source,
    'untracked_type',v_case.untracked_type,'legacy_reference',v_case.legacy_reference,
    'row_version',v_case.row_version,'component_count',(
      select count(*) from erp.bs_case_components where bs_case_id=v_case.id
    )
  );
  return erp._idempotency_complete('classify_bs_case_v2',p_client_request_id,v_response);
end
$function$;
CREATE OR REPLACE FUNCTION erp.cp6_lot_work_cost_v2620c(p_lot_id uuid,p_category text)
returns numeric
language sql
stable
security definer
set search_path=''
as $function$
with target as(
  select fl.id,fl.po_id,coalesce(fl.cutting_group_id,qi.cutting_group_id) group_id,
    fl.initial_qty_pcs::numeric lot_qty,fl.produced_at,fl.product_id
  from erp.fg_lots fl
  left join erp.qc_inspection_items qi on qi.id=fl.qc_item_id
  where fl.id=p_lot_id and fl.lot_origin='PRODUCTION'
), position as(
  select t.*,
    erp.bf_group_sku_v1(t.group_id,t.product_id) sku_id,
    coalesce((select sum(x.initial_qty_pcs)::numeric from erp.fg_lots x
      left join erp.qc_inspection_items xqi on xqi.id=x.qc_item_id
      where x.po_id=t.po_id and x.lot_origin='PRODUCTION'
        and coalesce(x.cutting_group_id,xqi.cutting_group_id)=t.group_id
        and erp.bf_group_sku_v1(t.group_id,x.product_id)=erp.bf_group_sku_v1(t.group_id,t.product_id)
        and (x.produced_at,x.id)<(t.produced_at,t.id)),0) sku_start,
    coalesce((select sum(x.initial_qty_pcs)::numeric from erp.fg_lots x
      left join erp.qc_inspection_items xqi on xqi.id=x.qc_item_id
      where x.po_id=t.po_id and x.lot_origin='PRODUCTION'
        and coalesce(x.cutting_group_id,xqi.cutting_group_id)=t.group_id
        and (x.produced_at,x.id)<(t.produced_at,t.id)),0) group_start,
    coalesce((select sum(x.initial_qty_pcs)::numeric from erp.fg_lots x
      where x.po_id=t.po_id and x.lot_origin='PRODUCTION'
        and (x.produced_at,x.id)<(t.produced_at,t.id)),0) po_start
  from target t
), source_lines as(
  select wce.cutting_group_id,wc.component_category,erp.bf_snapshot_sku_v1(wcl.po_component_snapshot_id) sku_id,wcl.qty_completed::numeric source_qty,
    wcl.amount_payable::numeric source_cost,
    coalesce(sum(wcl.qty_completed) over(
      partition by wce.po_id,wce.cutting_group_id,wcl.work_component_id,erp.bf_snapshot_sku_v1(wcl.po_component_snapshot_id)
      order by wce.physical_at,wce.id,wcl.id rows between unbounded preceding and 1 preceding
    ),0)::numeric source_start
  from position p
  join erp.work_completion_events wce on wce.po_id=p.po_id and wce.status='POSTED'
  join erp.work_completion_lines wcl on wcl.completion_id=wce.id
  join erp.work_components wc on wc.id=wcl.work_component_id
  where wc.component_category=case when upper(p_category)='COMMISSION' then 'COMMISSION' else wc.component_category end
    and (upper(p_category)='COMMISSION' or wc.component_category<>'COMMISSION')
    and (wce.cutting_group_id=p.group_id or wce.cutting_group_id is null)
)
select coalesce(sum(
  greatest(least(
    case when s.sku_id is not null then p.sku_start+p.lot_qty when s.cutting_group_id is null then p.po_start+p.lot_qty else p.group_start+p.lot_qty end,
    s.source_start+s.source_qty
  )-greatest(
    case when s.sku_id is not null then p.sku_start when s.cutting_group_id is null then p.po_start else p.group_start end,
    s.source_start
  ),0)*s.source_cost/nullif(s.source_qty,0)
),0)::numeric
from position p left join source_lines s on s.sku_id is null or s.sku_id=p.sku_id
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
  v_registry:=v_registry||'{"erp.bf_sku_members_v1.product_root":{"class":"MASTER","reason":"Commercial SKU membership; exact physical root is preserved"}}'::jsonb;
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
CREATE OR REPLACE FUNCTION erp.bd_compute_pricing_v1(p_delivery jsonb,p_pricing jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_vendor uuid:=erp.bd_uuid_v1(p_delivery,'vendor_id',true);v_process uuid:=erp.bd_uuid_v1(p_delivery,'wash_process_id',true);
  v_batch uuid:=erp.bd_uuid_v1(p_delivery,'distribution_batch_id',true);v_at timestamptz:=erp.bd_at_v1(p_delivery->>'physical_at','physical_at');
  v_color text:=nullif(btrim(coalesce(p_delivery->>'target_dyeing_color','')),'');
  t erp.bd_laundry_vendor_terms_v1%rowtype;v_mode text;v_unit text;v_model uuid;v_sizes jsonb:='[]'::jsonb;v_sizeids uuid[]:='{}';v_qtys integer[]:='{}';
  v_total_qty integer:=0;v_charges jsonb:='[]'::jsonb;v_known numeric:=0;v_complete boolean:=true;v_units jsonb;v_dec05 jsonb;v_dec03 jsonb;
  v_versions jsonb:='{}'::jsonb;v_line jsonb;v_x jsonb;v_split numeric[];v_shares jsonb;i integer;v_rate numeric;v_scoped record;v_base numeric;
  v_pkg record;v_comp record;v_included uuid[];v_seen uuid[]:='{}';v_cov integer;v_amount numeric;v_lump numeric;v_min numeric;v_topup numeric;
  v_status text;v_label text;v_kind text;
begin
  select * into t from erp.bd_laundry_vendor_terms_v1 where vendor_id=v_vendor;
  v_mode:=coalesce(t.pricing_mode,'RATE');v_unit:=coalesce(t.pricing_unit,'PCS');
  select po.model_id into v_model from erp.cutting_distribution_batches b join erp.cutting_pickups p on p.id=b.pickup_id
    join erp.cutting_groups g on g.id=p.cutting_group_id join erp.production_orders po on po.id=g.po_id where b.id=v_batch;
  if jsonb_typeof(p_delivery->'lines') is distinct from 'array' or jsonb_array_length(p_delivery->'lines')=0 then
    raise exception 'BD_LINES_REQUIRED: baris ukuran kiriman wajib diisi';end if;
  for v_x in select value from jsonb_array_elements(p_delivery->'lines') loop
    v_sizeids:=v_sizeids||erp.bd_uuid_v1(v_x,'size_id',true);v_qtys:=v_qtys||erp.bd_qty_v1(v_x->'qty_sent_pcs','qty_sent_pcs');
  end loop;
  foreach i in array v_qtys loop v_total_qty:=v_total_qty+i;end loop;
  v_units:=coalesce(erp.bd_policy_v1('LAU_DEC01')->'units','[]'::jsonb);
  if jsonb_typeof(p_pricing) is distinct from 'object' then raise exception 'BD_PRICING_INVALID: pricing wajib objek';end if;

  if p_pricing ? 'deferred' then
    perform erp._cp3_assert_closed_json_object(p_pricing,array['deferred'],array['deferred'],'deferred pricing');
    if p_pricing->'deferred' is distinct from 'true'::jsonb then raise exception 'BD_PRICING_INVALID: deferred harus true';end if;
    v_mode:='PENDING';v_unit:='PCS';
  elsif p_pricing ? 'components' then
    v_mode:='COMPONENTS';v_unit:='PCS';
    if p_pricing->'components'='[]'::jsonb then
      perform erp._cp3_assert_closed_json_object(p_pricing,array['components'],array['components'],'deferred components');
      v_mode:='PENDING';
    end if;
  elsif p_pricing ? 'package_id' then v_mode:='PACKAGE';v_unit:='PCS';
  elsif p_pricing='{}'::jsonb and v_mode in('PACKAGE','COMPONENTS') then v_mode:='PENDING';v_unit:='PCS';
  end if;
  if v_mode='PENDING' then
    -- No synthetic charge. Known subtotal is zero; unknown price stays NULL.
    v_complete:=false;
  elsif v_unit='BATCH' then
    -- LAU-T20: a lump sum agreed for this batch, spread over its sizes by quantity; the whole amount, not per receipt.
    if not v_units @> '["BATCH"]' then perform erp.bd_require_policy_v1('LAU_DEC01','satuan borongan per batch');
      raise exception 'BD_UNIT_NOT_ALLOWED: LAU-DEC01 belum mengizinkan satuan BATCH';end if;
    perform erp._cp3_assert_closed_json_object(p_pricing,array['lump_sum'],array['lump_sum'],'batch pricing');
    v_lump:=erp.bd_amount_v1(p_pricing->'lump_sum','lump_sum',true);
    v_versions:=v_versions||jsonb_build_object('LAU_DEC01',erp.bd_policy_version_v1('LAU_DEC01'));
    v_split:=erp.bd_split_amount_v1(v_lump,v_qtys);v_shares:='[]'::jsonb;
    for i in 1..array_length(v_sizeids,1) loop v_shares:=v_shares||jsonb_build_object('size_id',v_sizeids[i],'amount',v_split[i]::text);end loop;
    v_charges:=v_charges||jsonb_build_object('kind','BATCH','ref_id',null,'version_id',null,'label','Borongan batch','covered_qty',v_total_qty,
      'rate_status','KNOWN','unit_rate',null,'amount',v_lump::text,'shares',v_shares);
    v_known:=v_lump;v_mode:='BATCH';
  elsif v_mode='RATE' then
    perform erp._cp3_assert_closed_json_object(p_pricing,array[]::text[],array[]::text[],'rate pricing');
    v_dec05:=erp.bd_policy_v1('LAU_DEC05');
    for i in 1..array_length(v_sizeids,1) loop
      select * into v_scoped from erp.bd_scoped_rate_at_v1(v_vendor,v_process,v_model,v_sizeids[i],v_color,v_at);
      if v_scoped.rate_per_pcs is not null then
        v_rate:=v_scoped.rate_per_pcs;v_kind:='SCOPED_RATE';v_label:='Tarif khusus '||v_scoped.scope;v_mode:='SCOPED';
        v_versions:=v_versions||jsonb_build_object('LAU_DEC05',erp.bd_policy_version_v1('LAU_DEC05'));
      else
        if v_dec05 is not null and v_dec05->>'fallback'='REFUSE' then
          raise exception 'BD_SCOPED_RATE_MISSING: tidak ada tarif khusus untuk ukuran ini dan LAU-DEC05 menolak tarif dasar';end if;
        v_rate:=erp.bd_process_rate_at_v1(v_vendor,v_process,v_at);v_kind:='RATE';v_label:='Tarif dasar vendor/proses';
      end if;
      v_amount:=round(v_qtys[i]*v_rate,2);
      v_charges:=v_charges||jsonb_build_object('kind',v_kind,'ref_id',v_scoped.rate_id,'version_id',v_scoped.rate_id,'label',v_label,'covered_qty',v_qtys[i],
        'rate_status','KNOWN','unit_rate',v_rate::text,'amount',v_amount::text,
        'shares',jsonb_build_array(jsonb_build_object('size_id',v_sizeids[i],'amount',v_amount::text)));
      v_known:=v_known+v_amount;
    end loop;
  elsif v_mode='PACKAGE' then
    -- LAU-T02/T06: the package price covers its included components; the same component again as an extra is refused.
    perform erp._cp3_assert_closed_json_object(p_pricing,array['package_id'],array['package_id','extras'],'package pricing');
    select p.* into v_pkg from erp.bd_laundry_packages_v1 p where p.id=erp.bd_uuid_v1(p_pricing,'package_id',true) and p.vendor_id=v_vendor and p.is_active;
    if v_pkg.id is null then raise exception 'BD_PACKAGE_UNKNOWN: paket aktif vendor ini wajib dipilih';end if;
    select * into v_scoped from erp.bd_package_rate_at_v1(v_pkg.id,v_at);
    select array_agg(component_id order by component_id) into v_included from erp.bd_laundry_package_components_v1 where package_id=v_pkg.id;
    v_split:='{}';v_shares:='[]'::jsonb;
    for i in 1..array_length(v_sizeids,1) loop v_shares:=v_shares||jsonb_build_object('size_id',v_sizeids[i],'amount',round(v_qtys[i]*v_scoped.rate_per_pcs,2)::text);end loop;
    v_amount:=round(v_total_qty*v_scoped.rate_per_pcs,2);
    v_charges:=v_charges||jsonb_build_object('kind','PACKAGE','ref_id',v_pkg.id,'version_id',v_scoped.version_id,'label','Paket '||v_pkg.package_name,
      'covered_qty',v_total_qty,'rate_status','KNOWN','unit_rate',v_scoped.rate_per_pcs::text,'amount',v_amount::text,'shares',v_shares,
      'included_components',to_jsonb(v_included));
    v_known:=v_amount;
    if p_pricing ? 'extras' and jsonb_typeof(p_pricing->'extras')<>'null' then
      if jsonb_typeof(p_pricing->'extras')<>'array' or jsonb_array_length(p_pricing->'extras')>30 then raise exception 'BD_PRICING_INVALID: extras wajib daftar';end if;
      for v_x in select value from jsonb_array_elements(p_pricing->'extras') loop
        perform erp._cp3_assert_closed_json_object(v_x,array['component_id','covered_qty','reason'],array['component_id','covered_qty','coverage','reason'],'extra component');
        if erp.bd_uuid_v1(v_x,'component_id',true)=any(v_included) then
          raise exception 'BD_COMPONENT_ALREADY_INCLUDED: komponen ini sudah termasuk dalam paket; biaya untuk cakupan yang sama tidak ditagih dua kali';end if;
        v_dec03:=erp.bd_require_policy_v1('LAU_DEC03','komponen tambahan di luar paket');
        if v_dec03->>'extra'<>'ALLOWED' then raise exception 'BD_EXTRA_REFUSED: LAU-DEC03 tidak mengizinkan komponen tambahan';end if;
        v_versions:=v_versions||jsonb_build_object('LAU_DEC03',erp.bd_policy_version_v1('LAU_DEC03'));
        v_charges:=v_charges||erp.bd_component_charge_v1(v_vendor,v_x,v_at,v_sizeids,v_qtys,v_total_qty,'EXTRA',v_seen);
        v_seen:=v_seen||erp.bd_uuid_v1(v_x,'component_id',true);
      end loop;
    end if;
  elsif v_mode='COMPONENTS' then
    -- LAU-T03/T04/T05: the delivery's components, each with the pieces it really covers (partial coverage is not the whole
    -- delivery); the physical quantity stays the delivery quantity.
    perform erp._cp3_assert_closed_json_object(p_pricing,array['components'],array['components'],'component pricing');
    if jsonb_typeof(p_pricing->'components') is distinct from 'array' or jsonb_array_length(p_pricing->'components') not between 1 and 30 then
      raise exception 'BD_PRICING_INVALID: pilih 1-30 komponen';end if;
    for v_x in select value from jsonb_array_elements(p_pricing->'components') loop
      perform erp._cp3_assert_closed_json_object(v_x,array['component_id','covered_qty'],array['component_id','covered_qty','coverage'],'component');
      v_charges:=v_charges||erp.bd_component_charge_v1(v_vendor,v_x,v_at,v_sizeids,v_qtys,v_total_qty,'COMPONENT',v_seen);
      v_seen:=v_seen||erp.bd_uuid_v1(v_x,'component_id',true);
    end loop;
  end if;

  -- Known subtotal and completeness from the component charges.
  if v_mode in('PACKAGE','COMPONENTS') then
    v_known:=0;
    for v_line in select value from jsonb_array_elements(v_charges) loop
      if v_line->>'rate_status'<>'UNKNOWN' then v_known:=v_known+(v_line->>'amount')::numeric;else v_complete:=false;end if;
    end loop;
  end if;
  if t.minimum_charge is not null and v_mode<>'PENDING' then
    if not v_units @> '["MINIMUM"]' then perform erp.bd_require_policy_v1('LAU_DEC01','minimum charge');
      raise exception 'BD_UNIT_NOT_ALLOWED: LAU-DEC01 tidak lagi mengizinkan minimum charge vendor ini';end if;
    if not v_complete then raise exception 'BD_MINIMUM_NEEDS_KNOWN_PRICE: minimum charge memerlukan semua harga komponen diketahui';end if;
    v_versions:=v_versions||jsonb_build_object('LAU_DEC01',erp.bd_policy_version_v1('LAU_DEC01'));
    if v_known<t.minimum_charge then
      v_topup:=t.minimum_charge-v_known;v_split:=erp.bd_split_amount_v1(v_topup,v_qtys);v_shares:='[]'::jsonb;
      for i in 1..array_length(v_sizeids,1) loop v_shares:=v_shares||jsonb_build_object('size_id',v_sizeids[i],'amount',v_split[i]::text);end loop;
      v_charges:=v_charges||jsonb_build_object('kind','MINIMUM_TOPUP','ref_id',null,'version_id',null,'label','Minimum charge vendor','covered_qty',v_total_qty,
        'rate_status','KNOWN','unit_rate',null,'amount',v_topup::text,'shares',v_shares);
      v_known:=t.minimum_charge;
    end if;
  end if;
  for i in 1..array_length(v_sizeids,1) loop v_sizes:=v_sizes||jsonb_build_object('size_id',v_sizeids[i],'qty',v_qtys[i]);end loop;
  return jsonb_build_object('mode',case when v_mode='PENDING' then 'COMPONENTS' else v_mode end,'deferred',v_mode='PENDING','unit',v_unit,'vendor_id',v_vendor,'qty',v_total_qty,'sizes',v_sizes,'charges',v_charges,
    'total_known',round(v_known,2)::text,'complete',v_complete,
    'avg_rate',case when v_complete then round(v_known/v_total_qty,2)::text end,'policy_versions',v_versions);
end;$function$;
CREATE OR REPLACE FUNCTION erp.bd_attach_delivery_pricing_v1(p_delivery_line uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare c erp.bd_execution_context_v1%rowtype:=erp.bd_context_v1();p jsonb;l erp.laundry_delivery_lines%rowtype;v_ch jsonb;v_sh jsonb;
  v_no integer:=0;v_charge uuid;v_size uuid;
begin
  if c.backend_pid is null or c.action<>'POST_PRICED_DELIVERY' or c.pricing is null then return;end if;
  p:=c.pricing;
  select * into l from erp.laundry_delivery_lines where id=p_delivery_line;
  if l.qty_sent_pcs<>(p->>'qty')::integer then raise exception 'BD_INTERNAL: qty kiriman berbeda dari harga yang dihitung';end if;
  insert into erp.bd_laundry_priced_lines_v1(delivery_line_id,delivery_id,vendor_id,pricing_mode,pricing_unit,qty_sent,total_known,total_complete,
    policy_versions,request_id)
  values(l.id,l.delivery_id,(p->>'vendor_id')::uuid,p->>'mode',p->>'unit',l.qty_sent_pcs,(p->>'total_known')::numeric,(p->>'complete')::boolean,
    p->'policy_versions',c.request_id);
  for v_ch in select value from jsonb_array_elements(p->'charges') loop
    v_no:=v_no+1;
    insert into erp.bd_laundry_charge_lines_v1(delivery_line_id,line_no,kind,ref_id,version_id,label,covered_qty,rate_status,unit_rate,amount,included_components,price_reason)
    values(l.id,v_no,v_ch->>'kind',(v_ch->>'ref_id')::uuid,(v_ch->>'version_id')::uuid,v_ch->>'label',(v_ch->>'covered_qty')::integer,v_ch->>'rate_status',
      (v_ch->>'unit_rate')::numeric,(v_ch->>'amount')::numeric,v_ch->'included_components',v_ch->>'price_reason')
    returning id into v_charge;
    for v_sh in select value from jsonb_array_elements(v_ch->'shares') loop
      select s.id into v_size from erp.laundry_delivery_batch_size_lines s where s.delivery_line_id=l.id and s.size_id=(v_sh->>'size_id')::uuid;
      if v_size is null then raise exception 'BD_INTERNAL: ukuran harga tidak ada pada kiriman';end if;
      insert into erp.bd_laundry_charge_shares_v1(charge_line_id,delivery_batch_size_line_id,amount,covered_qty)
      values(v_charge,v_size,(v_sh->>'amount')::numeric,coalesce((v_sh->>'covered_qty')::integer,
        (select qty_sent_pcs from erp.laundry_delivery_batch_size_lines where id=v_size)));
    end loop;
  end loop;
  insert into erp.bf_laundry_delivery_sources_v1(delivery_line_id,details_pending)
    values(l.id,coalesce((p->>'deferred')::boolean,false));
  perform erp.bd_refresh_size_estimates_v1(l.id);
end;$function$;
CREATE OR REPLACE FUNCTION erp.bd_refresh_size_estimates_v1(p_delivery_line uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  insert into erp.bd_laundry_size_estimates_v1(delivery_batch_size_line_id,delivery_line_id,qty_sent,known_amount,complete)
  select s.id,s.delivery_line_id,s.qty_sent_pcs,coalesce(sum(sh.amount),0),count(sh.charge_line_id)>0 and bool_and(sh.amount is not null)
  from erp.laundry_delivery_batch_size_lines s left join erp.bd_laundry_charge_shares_v1 sh on sh.delivery_batch_size_line_id=s.id
  where s.delivery_line_id=p_delivery_line group by s.id,s.delivery_line_id,s.qty_sent_pcs
  on conflict(delivery_batch_size_line_id) do update set known_amount=excluded.known_amount,complete=excluded.complete;
  update erp.bd_laundry_priced_lines_v1 p set total_known=x.known,total_complete=x.complete
  from (select coalesce(sum(known_amount),0) known,bool_and(complete) complete from erp.bd_laundry_size_estimates_v1 where delivery_line_id=p_delivery_line) x
  where p.delivery_line_id=p_delivery_line;
end;$function$;
CREATE OR REPLACE FUNCTION erp.bd_line_complete_v1(p_delivery_line uuid)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select coalesce((select total_complete from erp.bd_laundry_priced_lines_v1 where delivery_line_id=p_delivery_line),true) or erp.bf_delivery_invoiced_v1(p_delivery_line) $function$;
CREATE OR REPLACE FUNCTION erp.bd_delivery_line_price_unknown_v1(p_delivery_line uuid)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select not erp.bf_delivery_invoiced_v1(dl.id) and (dl.estimated_rate_snapshot is null or not erp.bd_line_complete_v1(dl.id))
  from erp.laundry_delivery_lines dl join erp.laundry_deliveries d on d.id=dl.delivery_id
  where dl.id=p_delivery_line and d.status not in('DRAFT','REVERSED')
$function$;
CREATE OR REPLACE FUNCTION erp.bd_post_invoice_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare i erp.bd_laundry_invoices_v1%rowtype;l record;v_dec02 jsonb;v_dec03 jsonb;v_dec06 jsonb;v_versions jsonb:='{}'::jsonb;v_billable jsonb;
  v_gross numeric:=0;v_positive numeric:=0;v_payable numeric;v_weights numeric[]:='{}';v_ids uuid[]:='{}';v_split numeric[];k integer;v_last uuid;
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
    if l.line_kind='BILL' then v_ids:=v_ids||l.id;v_weights:=v_weights||round(l.amount*100);v_positive:=v_positive+l.amount;v_last:=l.id;end if;
  end loop;
  if i.discount_amount>v_positive then raise exception 'BD_DISCOUNT_EXCEEDS_LINES: diskon melebihi nilai baris tagih';end if;
  update erp.bd_laundry_invoice_lines_v1 set discount_share=0,rounding_share=0 where invoice_id=i.id;
  if i.discount_amount>0 then
    if v_positive<=0 then raise exception 'BD_DISCOUNT_EXCEEDS_LINES: diskon tanpa baris tagih bernilai';end if;
    v_split:=erp.bd_split_money_v1(i.discount_amount,v_weights);
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
    -- Unknown estimates are billed directly; actual cost follows the goods.
    if not erp.bd_line_complete_v1(l.delivery_line_id) and v_dec06->>'variance_mode'<>'PRODUCT_COST' then
      raise exception 'BF_UNKNOWN_INVOICE_PRODUCT_COST: biaya yang belum diketahui harus mengikuti biaya produk';end if;
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
CREATE OR REPLACE FUNCTION erp.bd_set_charge_price_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare ch erp.bd_laundry_charge_lines_v1%rowtype;v_rate numeric;v_amount numeric;v_split numeric[];v_ids uuid[];v_qtys integer[];i integer;
  p erp.bd_laundry_priced_lines_v1%rowtype;v_reason text:=nullif(btrim(p_payload->>'reason'),'');r record;v_status text:=coalesce(p_payload->>'rate_status','KNOWN');
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['charge_line_id','rate_per_pcs','reason'],array['charge_line_id','rate_per_pcs','rate_status','reason'],'charge price');
  if v_reason is null or length(v_reason)>1000 then raise exception 'BD_REASON_REQUIRED: alasan wajib diisi, maksimal 1000 karakter';end if;
  perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||l.cutting_group_id::text,0))
    from erp.bd_laundry_charge_lines_v1 c join erp.laundry_delivery_lines l on l.id=c.delivery_line_id
    where c.id=erp.bd_uuid_v1(p_payload,'charge_line_id',true);
  select * into ch from erp.bd_laundry_charge_lines_v1 where id=erp.bd_uuid_v1(p_payload,'charge_line_id',true) for update;
  if ch.id is null then raise exception 'BD_CHARGE_UNKNOWN: baris harga tidak dikenal';end if;
  if ch.rate_status<>'UNKNOWN' then raise exception 'BD_PRICE_ALREADY_KNOWN: harga baris ini sudah diketahui; snapshot tidak ditimpa';end if;
  select * into p from erp.bd_laundry_priced_lines_v1 where delivery_line_id=ch.delivery_line_id for update;
  -- Same order as a receipt (delivery, then size estimates): a receipt posting at the same time waits or is waited for.
  perform 1 from erp.laundry_deliveries where id=p.delivery_id for update;
  if exists(select 1 from erp.laundry_deliveries where id=p.delivery_id and status='REVERSED') then raise exception 'BD_DELIVERY_REVERSED: kiriman sudah dibatalkan';end if;
  if exists(select 1 from erp.laundry_receipt_lines rl join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
            where rl.delivery_line_id=ch.delivery_line_id and rl.actual_cost_status='FINAL') then
    raise exception 'BD_ALREADY_INVOICED: kiriman sudah ditagih vendor';end if;
  if exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 i on i.id=x.invoice_id
    join erp.laundry_receipt_lines receipt on receipt.id=x.receipt_line_id where receipt.delivery_line_id=ch.delivery_line_id and i.status='POSTED') then
    raise exception 'BD_ALREADY_INVOICED: biaya sudah berasal dari kontra bon; gunakan dokumen koreksi';end if;
  if v_status not in('KNOWN','FREE','WAIVED') then raise exception 'BD_RATE_STATUS: penyelesaian harga harus KNOWN, FREE atau WAIVED';end if;
  v_rate:=erp.bd_amount_v1(p_payload->'rate_per_pcs','rate_per_pcs',v_status='KNOWN');
  if v_status in('FREE','WAIVED') and v_rate<>0 then raise exception 'BD_FREE_REQUIRES_ZERO: FREE/WAIVED wajib nominal 0.00';end if;
  v_amount:=round(ch.covered_qty*v_rate,2);
  select array_agg(s.delivery_batch_size_line_id order by s.delivery_batch_size_line_id),array_agg(s.covered_qty order by s.delivery_batch_size_line_id)
  into v_ids,v_qtys from erp.bd_laundry_charge_shares_v1 s where s.charge_line_id=ch.id;
  if (select sum(x) from unnest(v_qtys) x) is distinct from ch.covered_qty::bigint then
    raise exception 'BD_COVERAGE_MISMATCH: snapshot penerima jasa tidak lengkap';end if;
  v_split:=erp.bd_split_amount_v1(v_amount,v_qtys);
  update erp.bd_laundry_charge_lines_v1 set rate_status=v_status,unit_rate=v_rate,amount=v_amount,price_reason=v_reason,price_set_by=erp.current_app_user_id(),
    price_set_at=statement_timestamp(),price_set_request=p_request,price_set_reason=v_reason where id=ch.id;
  for i in 1..array_length(v_ids,1) loop
    update erp.bd_laundry_charge_shares_v1 set amount=v_split[i] where charge_line_id=ch.id and delivery_batch_size_line_id=v_ids[i];
  end loop;
  perform erp.bd_refresh_size_estimates_v1(ch.delivery_line_id);
  -- Reallocate the posted receipts from scratch in physical order, so each takes its share and the last of a size the residual.
  delete from erp.bd_laundry_receipt_allocations_v1 a using erp.laundry_receipt_lines rl,erp.laundry_receipts h
  where rl.id=a.receipt_line_id and h.id=rl.receipt_id and h.status='POSTED' and rl.delivery_line_id=ch.delivery_line_id;
  for r in select rl.id from erp.laundry_receipt_lines rl join erp.laundry_receipts h on h.id=rl.receipt_id and h.status='POSTED'
    where rl.delivery_line_id=ch.delivery_line_id order by h.physical_at,rl.id loop
    perform erp.bd_allocate_receipt_v1(r.id);
  end loop;
  select * into p from erp.bd_laundry_priced_lines_v1 where delivery_line_id=ch.delivery_line_id;
  update erp.laundry_delivery_lines set estimated_rate_snapshot=case when p.total_complete then round(p.total_known/p.qty_sent,2) end,
    estimated_cost_status=case when p.total_complete then 'ESTIMATED' else 'PENDING' end where id=ch.delivery_line_id;
  -- The rate-snapshot trigger returns early when the snapshot stays NULL (another price still unknown); resync explicitly.
  perform erp.bd_resync_delivery_v1(p.delivery_id);
  return jsonb_build_object('charge_line_id',ch.id,'amount',v_amount::text,'total_known',p.total_known::text,'complete',p.total_complete);
end;$function$;
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
  where not bp.total_complete and not erp.bf_delivery_invoiced_v1(bp.delivery_line_id,p_through) and ld.status not in('DRAFT','REVERSED') and ld.physical_at<v_end
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
CREATE OR REPLACE FUNCTION erp.bd_priced_line_json_v1(p_line uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object('delivery_line_id',p.delivery_line_id,'delivery_id',p.delivery_id,'mode',case when exists(select 1 from erp.bf_laundry_delivery_sources_v1 b where b.delivery_line_id=p.delivery_line_id and b.details_pending) then 'PENDING' else p.pricing_mode end,'unit',p.pricing_unit,
    'qty_sent',p.qty_sent,'total_known',p.total_known::numeric(18,2)::text,'total_complete',p.total_complete,'cost_invoiced',erp.bf_delivery_invoiced_v1(p.delivery_line_id),'has_invoice',exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 i on i.id=x.invoice_id join erp.laundry_receipt_lines r on r.id=x.receipt_line_id where r.delivery_line_id=p.delivery_line_id and i.status='POSTED'),'policy_versions',p.policy_versions,
    'charges',coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'line_no',c.line_no,'kind',c.kind,'ref_id',c.ref_id,'label',c.label,
        'covered_qty',c.covered_qty,'rate_status',c.rate_status,'unit_rate',c.unit_rate::numeric(18,2)::text,'amount',c.amount::numeric(18,2)::text,
        'included_components',c.included_components,'price_reason',c.price_reason,
        'coverage',(select jsonb_agg(jsonb_build_object('size_id',s.size_id,'qty',sh.covered_qty) order by s.size_id)
          from erp.bd_laundry_charge_shares_v1 sh join erp.laundry_delivery_batch_size_lines s on s.id=sh.delivery_batch_size_line_id
          where sh.charge_line_id=c.id and sh.covered_qty>0)) order by c.line_no) from erp.bd_laundry_charge_lines_v1 c where c.delivery_line_id=p.delivery_line_id),'[]'::jsonb),
    'sizes',coalesce((select jsonb_agg(jsonb_build_object('delivery_batch_size_line_id',e.delivery_batch_size_line_id,'size_id',s.size_id,
        'qty_sent',e.qty_sent,'known_amount',e.known_amount::numeric(18,2)::text,'complete',e.complete) order by s.size_id)
      from erp.bd_laundry_size_estimates_v1 e join erp.laundry_delivery_batch_size_lines s on s.id=e.delivery_batch_size_line_id
      where e.delivery_line_id=p.delivery_line_id),'[]'::jsonb))
  from erp.bd_laundry_priced_lines_v1 p where p.delivery_line_id=p_line
$function$;
CREATE OR REPLACE FUNCTION erp.prepare_rework_component_line()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_order erp.rework_orders%rowtype;
  v_case erp.bs_cases%rowtype;
  v_component erp.bs_case_components%rowtype;
  v_model uuid;
  v_original_contractor uuid;
  v_rate_id uuid;
  v_rate numeric(18,2);
  v_po_snapshot uuid;
  v_remaining integer;bf_sku uuid;bf_version uuid;
begin
  select * into v_order from erp.rework_orders where id=new.rework_order_id for update;
  if v_order.id is null then raise exception 'Rework order not found'; end if;
  if v_order.status not in('OPEN','IN_PROGRESS','PARTIAL') or v_order.cost_posted then
    raise exception 'Rework component lines are editable only before completion/cost posting';
  end if;
  select * into v_component from erp.bs_case_components where id=new.bs_case_component_id for update;
  if v_component.id is null then raise exception 'BS component not found'; end if;
  if v_component.bs_case_id<>v_order.bs_case_id then
    raise exception 'Rework component belongs to a different BS case';
  end if;
  select * into v_case from erp.bs_cases where id=v_order.bs_case_id;
  if new.qty_performed>v_order.qty_sent then
    raise exception 'Rework component qty performed % exceeds rework qty sent %',new.qty_performed,v_order.qty_sent;
  end if;
  v_remaining:=greatest(
    v_case.qty_pcs-v_component.completed_before_bs_qty-v_component.lifetime_newly_completed_qty,0
  );
  new.qty_newly_payable:=least(new.qty_performed,v_remaining);
  new.bf_sku_version_id:=null;
  new.source_contractor_rate_id:=null;
  new.source_po_component_snapshot_id:=null;

  if v_order.destination_type='LAUNDRY' then
    new.rate_snapshot:=0;
    new.rate_basis:='LAUNDRY_ZERO';
    return new;
  end if;

  select coalesce(po.model_id,p.model_id),coalesce(po.contractor_id,v_case.responsible_contractor_id)
  into v_model,v_original_contractor
  from erp.bs_cases bc
  left join erp.production_orders po on po.id=bc.po_id
  left join erp.products p on p.id=bc.product_id
  where bc.id=v_case.id;
  if v_model is null then
    raise exception 'Contractor rework requires PO or product model lineage for server-side rate resolution';
  end if;

  bf_sku:=erp.bf_group_sku_v1(v_case.cutting_group_id,v_case.product_id);
  if bf_sku is null and v_case.product_id is not null then
    select sku_id into bf_sku from erp.bf_sku_versions_v1 where id=erp.bf_version_at_v1(v_case.product_id,v_order.physical_sent_at);
  end if;
  if bf_sku is not null then
    if v_order.contractor_id is not distinct from v_original_contractor then
      select s.id,s.rate_per_pcs_snapshot into v_po_snapshot,v_rate from erp.po_work_component_snapshots s
        join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id
        where s.po_id=v_case.po_id and v.sku_id=bf_sku and s.work_component_id=v_component.work_component_id;
      if v_po_snapshot is not null then
        new.rate_snapshot:=v_rate;new.source_po_component_snapshot_id:=v_po_snapshot;new.rate_basis:='PO_SNAPSHOT';return new;
      end if;
    end if;
    select id into bf_version from erp.bf_sku_versions_v1 where sku_id=bf_sku and effective_from<=v_order.physical_sent_at
      and(effective_to is null or effective_to>v_order.physical_sent_at);
    v_rate:=erp.bf_work_rate_v1(bf_version,v_order.contractor_id,v_component.work_component_id,v_order.physical_sent_at);
    if v_rate is not null then
      new.rate_snapshot:=v_rate;new.bf_sku_version_id:=bf_version;new.rate_basis:='SKU_RATE';return new;
    end if;
  end if;

  select r.id,r.rate_per_pcs into v_rate_id,v_rate
  from erp.contractor_work_rates r
  where r.contractor_id=v_order.contractor_id
    and r.model_id=v_model
    and r.work_component_id=v_component.work_component_id
    and r.effective_from<=v_order.physical_sent_at
    and (r.effective_to is null or r.effective_to>v_order.physical_sent_at)
  order by r.effective_from desc,r.id desc limit 1;

  if v_rate_id is not null then
    new.rate_snapshot:=v_rate;
    new.source_contractor_rate_id:=v_rate_id;
    new.rate_basis:='CONTRACTOR_RATE';
    return new;
  end if;

  if v_order.contractor_id is distinct from v_original_contractor then
    raise exception 'Cross-Mandor rework requires an explicit effective contractor rate for this model/component';
  end if;
  select s.id,s.rate_per_pcs_snapshot into v_po_snapshot,v_rate
  from erp.po_work_component_snapshots s
  where s.po_id=v_case.po_id and s.work_component_id=v_component.work_component_id
    and erp.bf_snapshot_matches_v1(s.id,v_case.cutting_group_id,v_case.product_id)
  order by s.committed_at desc,s.id desc limit 1;
  if v_po_snapshot is null then
    raise exception 'No effective contractor rate or PO component snapshot exists for rework pricing';
  end if;
  new.rate_snapshot:=v_rate;
  new.source_po_component_snapshot_id:=v_po_snapshot;
  new.rate_basis:='PO_SNAPSHOT';
  return new;
end;
$function$;
CREATE OR REPLACE FUNCTION erp.run_v263c_bs_rework_integrity_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
  select 'rework_component_wrong_bs_case','CRITICAL',count(*)::bigint,
         'Every rework component must belong to the order BS case'
  from erp.rework_component_lines l
  join erp.rework_orders o on o.id=l.rework_order_id
  join erp.bs_case_components c on c.id=l.bs_case_component_id
  where c.bs_case_id<>o.bs_case_id

  union all
  select 'rework_rate_provenance_mismatch','CRITICAL',count(*)::bigint,
         'Server-priced rework rate must equal its immutable source snapshot'
  from erp.rework_component_lines l
  left join erp.contractor_work_rates r on r.id=l.source_contractor_rate_id
  left join erp.po_work_component_snapshots s on s.id=l.source_po_component_snapshot_id
  where (l.rate_basis='CONTRACTOR_RATE' and (r.id is null or l.rate_snapshot<>r.rate_per_pcs))
     or (l.rate_basis='PO_SNAPSHOT' and (s.id is null or l.rate_snapshot<>s.rate_per_pcs_snapshot))
     or (l.rate_basis='LAUNDRY_ZERO' and l.rate_snapshot<>0)
     or (l.rate_basis='SKU_RATE' and (l.bf_sku_version_id is null or l.rate_snapshot is distinct from (
       select erp.bf_work_rate_v1(l.bf_sku_version_id,o.contractor_id,c.work_component_id,o.physical_sent_at)
       from erp.rework_orders o join erp.bs_case_components c on c.id=l.bs_case_component_id where o.id=l.rework_order_id)))

  union all
  select 'rework_component_qty_exceeds_sent','CRITICAL',count(*)::bigint,
         'Component performed qty cannot exceed physical rework qty sent'
  from erp.rework_component_lines l join erp.rework_orders o on o.id=l.rework_order_id
  where l.qty_performed>o.qty_sent

  union all
  select 'active_cross_mandor_without_explicit_rate','CRITICAL',count(*)::bigint,
         'Cross-Mandor contractor rework requires effective contractor-rate provenance'
  from erp.rework_component_lines l
  join erp.rework_orders o on o.id=l.rework_order_id
  join erp.bs_cases b on b.id=o.bs_case_id
  left join erp.production_orders po on po.id=b.po_id
  where o.destination_type='CONTRACTOR' and o.status<>'CANCELLED'
    and o.contractor_id is distinct from coalesce(po.contractor_id,b.responsible_contractor_id)
    and not ((l.rate_basis='CONTRACTOR_RATE' and l.source_contractor_rate_id is not null) or (l.rate_basis='SKU_RATE' and l.bf_sku_version_id is not null))

  union all
  select 'active_rework_bs_status_mismatch','CRITICAL',count(*)::bigint,
         'A BS case with active rework must project IN_REWORK while unresolved'
  from erp.bs_cases b
  where b.status not in('CANCELLED','RESOLVED','SCRAPPED','WRITTEN_OFF')
    and exists(select 1 from erp.rework_orders o where o.bs_case_id=b.id and o.status in('OPEN','IN_PROGRESS','PARTIAL'))
    and b.status<>'IN_REWORK'

  union all
  select 'bs_resolution_qty_exceeds_case','CRITICAL',count(*)::bigint,
         'Lifetime BS dispositions/resolutions cannot exceed case quantity'
  from (
    select b.id
    from erp.bs_cases b join erp.bs_resolutions r on r.bs_case_id=b.id
    group by b.id,b.qty_pcs having sum(r.qty_pcs)>b.qty_pcs
  ) excessive

  union all
  select 'cash_bs_resolution_invalid_claim','CRITICAL',count(*)::bigint,
         'Cash BS disposition requires matching settled laundry claim and capacity'
  from erp.bs_resolutions r
  join erp.bs_cases b on b.id=r.bs_case_id
  left join erp.laundry_claims c on c.id=r.source_laundry_claim_id
  where r.resolution_type='CASH_COMPENSATION'
    and (c.id is null or c.status<>'SETTLED' or c.vendor_id is distinct from b.responsible_vendor_id)

  union all
  select 'manual_bs_invalid_origin','CRITICAL',count(*)::bigint,
         'Manual/untracked BS must be only LEGACY or OUT_OF_NOWHERE with traceability'
  from erp.bs_cases b
  where b.untracked_type is not null
    and (b.untracked_type not in('LEGACY','OUT_OF_NOWHERE') or b.cause_source<>'UNKNOWN' or b.legacy_reference is null)

  union all
  select 'browser_direct_bs_rework_write_grant','CRITICAL',count(*)::bigint,
         'Authenticated browser must write BS/rework only through domain RPCs'
  from information_schema.role_table_grants g
  where g.table_schema='erp' and g.grantee='authenticated'
    and g.table_name in('bs_cases','bs_case_components','bs_resolutions','rework_orders','rework_component_lines')
    and g.privilege_type in('INSERT','UPDATE','DELETE');
$function$;
CREATE OR REPLACE FUNCTION erp.get_hpp_completeness(p_po_id uuid DEFAULT NULL::uuid)
 RETURNS TABLE(po_id uuid, po_number text, po_status text, current_hpp_total numeric, qty_basis_pcs bigint, hpp_per_pcs numeric, engine_cost_state text, display_status text, is_adjusted boolean, pending_reason_count integer, pending_reasons text[], latest_hpp_at timestamp with time zone)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
with po as (
  select p.id,p.po_number::text,p.status::text,p.contractor_id
  from erp.production_orders p
  where (p_po_id is null or p.id=p_po_id)
    and erp.current_app_role() in ('OWNER','ADMIN','STAFF')
), h as (
  select fl.po_id,
         count(*) filter(where fl.lot_origin='PRODUCTION')::int active_lots,
         count(hv.hpp_version_id) filter(where fl.lot_origin='PRODUCTION')::int hpp_lots,
         coalesce(sum(hv.total_cost) filter(where fl.lot_origin='PRODUCTION'),0)::numeric total_cost,
         coalesce(sum(hv.qty_basis_pcs) filter(where fl.lot_origin='PRODUCTION'),0)::bigint qty_basis,
         max(hv.calculated_at) filter(where fl.lot_origin='PRODUCTION') latest_at,
         bool_or(hv.cost_state='ESTIMATED') filter(where fl.lot_origin='PRODUCTION') any_estimated,
         bool_or(hv.cost_state='ADJUSTED') filter(where fl.lot_origin='PRODUCTION') any_adjusted
  from erp.fg_lots fl
  left join erp.v_current_hpp hv on hv.lot_id=fl.id
  where fl.lot_origin='PRODUCTION'
  group by fl.po_id
), flags as (
 select p.id po_id,
        coalesce(h.active_lots,0) active_lots,
        coalesce(h.hpp_lots,0) hpp_lots,
        coalesce(h.total_cost,0) total_cost,
        coalesce(h.qty_basis,0) qty_basis,
        h.latest_at,
        coalesce(h.any_estimated,false) any_estimated,
        coalesce(h.any_adjusted,false) any_adjusted,
        array_remove(array[
          case when coalesce(h.active_lots,0)=0 then 'BELUM_ADA_FG' end,
          case when coalesce(h.active_lots,0)>coalesce(h.hpp_lots,0) then 'HPP_CURRENT_BELUM_TERBENTUK' end,
          case when p.status<>'FINISHED' then 'PRODUKSI_BELUM_FINISHED' end,
          case when coalesce(erp.desired_laundry_accrual(p.id),0)>0.005 then 'BIAYA_LAUNDRY_MASIH_ESTIMASI/BELUM_FINAL' end,
          case when coalesce(h.any_estimated,false) then 'HPP_ENGINE_MASIH_ESTIMATED' end,
          case when exists(select 1 from erp.cost_recalc_queue q where q.entity_type='PO' and q.entity_id=p.id and q.status in('PENDING','RUNNING','FAILED')) then 'RECOST_BELUM_SELESAI' end,
          case when exists(select 1 from erp.bs_cases b where b.po_id=p.id and b.status in('OPEN','IN_REWORK','PARTIAL')) then 'BS/REWORK_BELUM_SELESAI' end,
          case when p.contractor_id is not null and coalesce(h.active_lots,0)>0 and not exists(select 1 from erp.po_work_component_snapshots s where s.po_id=p.id) then 'BIAYA_KERJA/BOM_BELUM_DIKONFIRMASI' end,
          case when exists(
            select 1 from erp.po_work_component_snapshots s
            where s.po_id=p.id and (s.bf_sku_version_id is not null or not exists(
              select 1 from erp.cutting_groups cg join erp.bf_wave_skus_v1 w on w.cutting_group_id=cg.id where cg.po_id=p.id)
              or exists(select 1 from erp.cutting_groups cg where cg.po_id=p.id and not exists(select 1 from erp.bf_wave_skus_v1 w where w.cutting_group_id=cg.id)))
            and not exists(
              select 1 from erp.work_completion_lines wcl join erp.work_completion_events wce on wce.id=wcl.completion_id
              where wcl.po_component_snapshot_id=s.id and wce.status='POSTED'
            )
          ) then 'ADA_KOMPONEN_KERJA_BELUM_PERNAH_DIPOST' end,
          case when exists(
            select 1 from erp.fg_lots fl
            where fl.po_id=p.id and fl.lot_origin='PRODUCTION'
              and exists(select 1 from erp.accessory_bom_versions abv join erp.accessory_bom_items abi on abi.bom_version_id=abv.id where abv.product_id=fl.product_id and abv.is_active=true and abv.effective_from<=fl.produced_at and (abv.effective_to is null or abv.effective_to>fl.produced_at))
              and not exists(select 1 from erp.fg_accessory_cost_snapshots s where s.lot_id=fl.id)
          ) then 'SNAPSHOT_BIAYA_AKSESORI_BELUM_ADA' end
        ]::text[],null) reasons
 from po p left join h on h.po_id=p.id
)
select p.id,
       p.po_number,
       p.status,
       f.total_cost,
       f.qty_basis,
       case when f.qty_basis>0 then f.total_cost/f.qty_basis else null end,
       case when f.any_estimated then 'ESTIMATED' when f.any_adjusted then 'ADJUSTED' when f.hpp_lots>0 then 'ACTUAL' else null end,
       case
         when f.active_lots=0 or f.hpp_lots=0 then 'BELUM_ADA_HPP'
         when p.status<>'FINISHED' then 'SEMENTARA'
         when cardinality(f.reasons)>0 then 'BELUM_LENGKAP'
         else 'LENGKAP_BERDASARKAN_DATA_SAAT_INI'
       end,
       f.any_adjusted,
       cardinality(f.reasons),
       f.reasons,
       f.latest_at
from po p join flags f on f.po_id=p.id
order by p.po_number;
$function$;
CREATE OR REPLACE FUNCTION erp.resolve_rework_accessory_bom_v1(
  p_bs_case_id uuid,p_basis_at timestamptz
)
returns uuid language plpgsql stable security definer set search_path=''
as $function$
declare
  v_po uuid;
  v_product uuid;
  v_po_model uuid;
  v_product_model uuid;
  v_root uuid;
  v_bom uuid;
  v_distinct integer;bf_version uuid;bf_pinned uuid;bf_sku uuid;bf_frozen uuid;
begin
  select b.po_id,b.product_id,po.model_id,p.model_id,p.identity_root_id
  into v_po,v_product,v_po_model,v_product_model,v_root
  from erp.bs_cases b
  left join erp.production_orders po on po.id=b.po_id
  left join erp.products p on p.id=b.product_id
  where b.id=p_bs_case_id;
  if not found then raise exception 'BS case not found'; end if;
  if v_po is null or v_product is null then return null; end if;
  if p_basis_at is null then raise exception 'Accessory BOM basis_at is required'; end if;
  if v_product_model is distinct from v_po_model then
    raise exception 'BS product model does not match production order model';
  end if;

  select c.bom_version_id into v_bom
  from erp.po_accessory_bom_commitments c
  where c.po_id=v_po and c.product_id=v_product;
  if v_bom is not null then return v_bom; end if;

  select count(distinct c.bom_version_id) into v_distinct
  from erp.po_accessory_bom_commitments c
  join erp.products cp on cp.id=c.product_id
  where c.po_id=v_po and cp.identity_root_id=v_root;
  if coalesce(v_distinct,0)>1 then
    raise exception 'PO has ambiguous accessory BOM commitments for this logical SKU';
  end if;
  if coalesce(v_distinct,0)=1 then
    select c.bom_version_id into v_bom
    from erp.po_accessory_bom_commitments c
    join erp.products cp on cp.id=c.product_id
    where c.po_id=v_po and cp.identity_root_id=v_root
    order by c.committed_at,c.id limit 1;
    return v_bom;
  end if;

  bf_version:=erp.bf_version_at_v1(v_product,p_basis_at);
  if bf_version is not null then
    select sku_id into bf_sku from erp.bf_sku_versions_v1 where id=bf_version;
    select version_id into bf_pinned from erp.bf_po_boms_v1 where po_id=v_po and sku_id=bf_sku;
    if bf_pinned is null then
      select v.id into bf_pinned from erp.po_accessory_bom_commitments c
        join erp.bf_sku_members_v1 m on m.bom_version_id=c.bom_version_id join erp.bf_sku_versions_v1 v on v.id=m.version_id
        where c.po_id=v_po and v.sku_id=bf_sku order by c.committed_at,c.id limit 1;
    end if;
    select bom_version_id into v_bom from erp.bf_sku_members_v1 where version_id=coalesce(bf_pinned,bf_version) and product_root=v_root;
    if v_bom is null and bf_pinned is not null then
      select bom_version_id into bf_frozen from erp.bf_sku_members_v1 where version_id=bf_pinned and bom_version_id is not null order by product_root limit 1;
      select bom_version_id into v_bom from erp.bf_sku_members_v1 where version_id=bf_version and product_root=v_root;
      if erp.bf_recipe_basis_v1(v_bom) is distinct from erp.bf_recipe_basis_v1(bf_frozen) then raise exception 'BF_PO_NEW_MEMBER';end if;
    end if;
    if v_bom is null then raise exception 'BF_BOM_UNCONFIGURED';end if;
    if exists(select 1 from erp.po_accessory_bom_commitments c join erp.products cp on cp.id=c.product_id
      join erp.bf_sku_members_v1 m on m.product_root=cp.identity_root_id and m.version_id=coalesce(bf_pinned,bf_version)
      where c.po_id=v_po and erp.bf_recipe_basis_v1(c.bom_version_id) is distinct from erp.bf_recipe_basis_v1(v_bom)) then raise exception 'BF_PO_LEGACY_BOM';end if;
    return v_bom;
  end if;

  select abv.id into v_bom
  from erp.accessory_bom_versions abv
  where abv.product_id=v_root and abv.is_active
    and abv.effective_from<=p_basis_at
    and(abv.effective_to is null or abv.effective_to>p_basis_at)
  order by abv.effective_from desc,abv.created_at desc,abv.id desc limit 1;
  return v_bom;
end
$function$;
CREATE OR REPLACE FUNCTION erp.bb_check_sales_import_row_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;v_cutover date;v_date date;v_due date;v_qty integer;v_price numeric;v_discount numeric;
begin
  perform erp.require_owner_admin();
  select * into r from erp.migration_staging_rows where id=p_row and batch_id=p_batch and entity_type='OPEN_SALES_DRAFT';
  if r.id is null then raise exception 'Baris draf penjualan tidak ditemukan';end if;
  j:=r.normalized_payload;
  foreach k in array array['draft_number','line_number','draft_date','customer_code','location_code','product_sku','qty_pcs','unit_price'] loop
    if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk draf penjualan terbuka',k;end if;
  end loop;
  if length(btrim(j->>'draft_number'))>60 or length(btrim(j->>'line_number'))>60 then raise exception 'draft_number: maksimal 60 karakter';end if;
  select (cutover_at at time zone 'Asia/Jakarta')::date into v_cutover from erp.migration_batches where id=p_batch;
  v_date:=erp.bb_parse_date_v1(j->>'draft_date','draft_date');
  if v_date>v_cutover then raise exception 'draft_date: draf harus dibuat sebelum saldo awal';end if;
  if nullif(btrim(j->>'due_date'),'') is not null then v_due:=erp.bb_parse_date_v1(j->>'due_date','due_date');end if;
  if j->>'qty_pcs' !~ '^[1-9][0-9]{0,8}$' then raise exception 'qty_pcs: jumlah pcs bilangan bulat positif';end if;
  v_qty:=(j->>'qty_pcs')::integer;
  v_price:=erp.bb_parse_amount_v1(j->>'unit_price','unit_price',true);
  v_discount:=case when nullif(btrim(j->>'discount_amount'),'') is null then 0 else erp.bb_parse_amount_v1(j->>'discount_amount','discount_amount',true) end;
  if v_discount>v_qty*v_price then raise exception 'discount_amount: potongan melebihi nilai baris';end if;
  if not exists(select 1 from erp.customers where customer_code=j->>'customer_code' and is_active)
    and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='CUSTOMER' and validation_status='VALID'
      and normalized_payload->>'customer_code'=j->>'customer_code') then
    raise exception 'customer_code: pelanggan aktif tidak ditemukan';
  end if;
  if not exists(select 1 from erp.locations where location_code=j->>'location_code' and is_active and location_type='FG_WAREHOUSE')
    and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='LOCATION' and validation_status='VALID'
      and normalized_payload->>'location_code'=j->>'location_code' and normalized_payload->>'location_type'='FG_WAREHOUSE') then
    raise exception 'location_code: gudang barang jadi aktif tidak ditemukan';
  end if;
  perform erp.bf_resolve_import_product_v1(p_batch,j,true);
  -- One draft: the same customer, warehouse, dates and terms on every line, and each line number once.
  if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPEN_SALES_DRAFT' and x.id<>r.id
      and lower(btrim(x.normalized_payload->>'draft_number'))=lower(btrim(j->>'draft_number'))
      and (lower(btrim(x.normalized_payload->>'line_number'))=lower(btrim(j->>'line_number'))
        or x.normalized_payload->>'customer_code'<>j->>'customer_code' or x.normalized_payload->>'location_code'<>j->>'location_code'
        or x.normalized_payload->>'draft_date'<>j->>'draft_date' or coalesce(x.normalized_payload->>'due_date','')<>coalesce(j->>'due_date','')
        or coalesce(x.normalized_payload->>'payment_terms','')<>coalesce(j->>'payment_terms',''))) then
    raise exception 'BB_S02_DUPLICATE_DRAFT: baris draf ganda atau kepala draf tidak konsisten';
  end if;
  if exists(select 1 from erp.sales_headers where lower(btrim(sale_number))=lower(btrim(j->>'draft_number')))
    or exists(select 1 from erp.bb_open_sales_drafts_v1 where lower(btrim(draft_number))=lower(btrim(j->>'draft_number'))) then
    raise exception 'BB_S02_DUPLICATE_DRAFT: nomor draf sudah dipakai penjualan lain';
  end if;
  return jsonb_build_object('cutover_date',v_cutover,'draft_date',v_date,'due_date',v_due,'qty_pcs',v_qty,'unit_price',v_price,'discount_amount',v_discount);
end;$function$;
CREATE OR REPLACE FUNCTION erp.bb_apply_sales_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare d record;r record;j jsonb;c jsonb;b erp.migration_batches%rowtype;v_customer uuid;v_location uuid;v_items jsonb;v_sale jsonb;
  v_sale_id uuid;v_product uuid;v_lines jsonb;l jsonb;
begin
  perform erp.require_owner_admin();
  select * into b from erp.migration_batches where id=p_batch;
  for d in select lower(btrim(normalized_payload->>'draft_number')) k,min(btrim(normalized_payload->>'draft_number')) draft_number
      from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPEN_SALES_DRAFT' and posted_entity_id is null
      group by 1 order by 1 loop
    perform pg_advisory_xact_lock(hashtextextended('BB_S02_DRAFT:'||d.k,0));
    v_items:='[]'::jsonb;v_lines:='[]'::jsonb;j:=null;
    for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPEN_SALES_DRAFT' and posted_entity_id is null
        and lower(btrim(normalized_payload->>'draft_number'))=d.k order by lower(btrim(normalized_payload->>'line_number')),source_row_no loop
      if r.validation_status<>'VALID' then raise exception 'Draf penjualan belum lolos pemeriksaan';end if;
      j:=r.normalized_payload;c:=erp.bb_check_sales_import_row_v1(p_batch,r.id);
      v_product:=erp.bf_resolve_import_product_v1(p_batch,j,false);
      v_items:=v_items||jsonb_build_array(jsonb_build_object('product_id',v_product,'qty_pcs',(c->>'qty_pcs')::integer,
        'unit_price_snapshot',(c->>'unit_price')::numeric,'discount_amount',(c->>'discount_amount')::numeric,
        'notes','Baris '||btrim(j->>'line_number')||' draf lama '||d.draft_number));
      v_lines:=v_lines||jsonb_build_array(c||jsonb_build_object('row_id',r.id,'line_number',btrim(j->>'line_number'),'product_id',v_product));
    end loop;
    select id into strict v_customer from erp.customers where customer_code=j->>'customer_code' and is_active;
    select id into strict v_location from erp.locations where location_code=j->>'location_code' and is_active and location_type='FG_WAREHOUSE';
    -- The native draft and its one reservation. A reservation beyond the free finished goods of the warehouse (the lines of
    -- this draft and every draft before it) is refused by the native check and rolls the whole import back.
    begin
      v_sale:=erp.save_sale_draft_v2(jsonb_build_object('sale_number',d.draft_number,'customer_id',v_customer,'source_location_id',v_location,
        'sale_date',b.cutover_at,'due_date',c->>'due_date','payment_terms',nullif(btrim(j->>'payment_terms'),''),
        'notes','Draf penjualan terbuka saat saldo awal (draf lama '||d.draft_number||' tanggal '||(c->>'draft_date')
          ||'); ubah tanggal invoice ke tanggal nyata sebelum posting',
        'reason','Impor saldo awal: draf penjualan terbuka dengan reservasi resmi','items',v_items),
        md5('BB_S02:'||p_batch::text||':'||d.k)::uuid,null);
    exception when others then
      raise exception 'BB_S02_RESERVATION_REFUSED: draf %: %',d.draft_number,sqlerrm;
    end;
    v_sale_id:=(v_sale->>'sale_id')::uuid;
    insert into erp.bb_open_sales_drafts_v1(sale_id,batch_id,draft_number,draft_date,customer_id,cutover_at)
    values(v_sale_id,p_batch,d.draft_number,(c->>'draft_date')::date,v_customer,b.cutover_at);
    -- The lines as checked before the draft existed (a second check would see the draft's own number as taken).
    for l in select * from jsonb_array_elements(v_lines) loop
      insert into erp.bb_open_sales_draft_lines_v1(source_row_id,sale_id,line_number,product_id,qty_pcs,unit_price,discount_amount)
      values((l->>'row_id')::uuid,v_sale_id,l->>'line_number',(l->>'product_id')::uuid,(l->>'qty_pcs')::integer,(l->>'unit_price')::numeric,
        (l->>'discount_amount')::numeric);
      update erp.migration_staging_rows set posted_entity_id=v_sale_id,posted_entity_type='OPEN_SALES_DRAFT',posted_at=statement_timestamp(),
        updated_at=statement_timestamp() where id=(l->>'row_id')::uuid;
    end loop;
  end loop;
end;$function$;
CREATE OR REPLACE FUNCTION erp.bc_check_import_row_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;v_qty numeric;v_amount numeric;v_count boolean;v_type text;v_doc record;v_kind text;
  v_zone text;v_total numeric;v_source text;
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
  -- D09 (owner 26 Sep 2026, ACC-C12 option a): the pending item names its source (count sheet + line, or source lot); the same
  -- source is one item whatever custody key a later request uses. Other lines of the same sheet are other goods.
  v_source:=erp.bd_custody_source_identity_v1(j);
  if exists(select 1 from erp.bd_custody_sources_v1 s where s.source_identity=v_source)
    or exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_ACCESSORY_CUSTODY' and x.id<>r.id
      and erp.bd_custody_source_identity_v1(x.normalized_payload,false)=v_source) then
    raise exception 'BC_C12_SAME_SOURCE: rujukan sumber % sudah dipakai; barang yang sama tetap satu item walau kunci permintaan baru',v_source;end if;
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
  if v_kind='CUSTOMER_GARMENT' then perform erp.bf_resolve_import_product_v1(p_batch,j,true,true);end if;
  return jsonb_build_object('kind',v_kind,'qty',(j->>'qty')::numeric,'source',v_source);
end;$function$;
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
        erp.bf_resolve_import_product_v1(p_batch,j,false,true),
        btrim(j->>'description'),(c->>'qty')::numeric,b.cutover_at,p_batch);
    end if;
    -- D09: the source identity stays with the goods (one row per source; a concurrent import of the same source fails here).
    if r.entity_type='OPENING_ACCESSORY_CUSTODY' then
      begin
        insert into erp.bd_custody_sources_v1(source_identity,custody_kind,record_id,batch_id,source_row_id,count_sheet,sheet_line,source_lot)
        values(c->>'source',c->>'kind',v_id,p_batch,r.id,nullif(btrim(j->>'count_sheet'),''),nullif(btrim(j->>'sheet_line'),''),nullif(btrim(j->>'source_lot'),''));
      exception when unique_violation then
        raise exception 'BC_C12_SAME_SOURCE: rujukan sumber % sudah dipakai; barang yang sama tetap satu item walau kunci permintaan baru',c->>'source';
      end;
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
   perform erp.bf_resolve_import_product_v1(p_batch,j,true);
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
CREATE OR REPLACE FUNCTION erp.be_apply_pocket_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;j jsonb;c jsonb;v_id uuid;v_date date;v_journal uuid;v_item uuid;v_po uuid;
begin
 perform erp.require_owner_admin();
 -- The router already holds the batch row lock. Imports without pocket rows
 -- must retain their native request-lock behavior and not claim this domain lock.
 if not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch
   and entity_type in('OPENING_POCKET_USAGE','OPENING_POCKET_SEWING') and posted_entity_id is null) then
  return;
 end if;
 perform erp.pocket_period_lock_v1();
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
    case when upper(j->>'target_kind')='COGS' then erp.bf_resolve_import_product_v1(p_batch,j,false) end,nullif(btrim(j->>'sold_reference'),''));
  end if;
  update erp.migration_staging_rows set posted_entity_id=v_id,posted_entity_type=r.entity_type,posted_at=statement_timestamp(),updated_at=statement_timestamp() where id=r.id;
 end loop;
end;$function$;
CREATE OR REPLACE FUNCTION erp.bb_check_rework_import_row_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO '' SET "DateStyle" TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;v_cutover date;v_bs erp.migration_staging_rows%rowtype;b jsonb;v_po jsonb;
  w erp.migration_staging_rows%rowtype;wj jsonb;v_sent integer;v_returned integer;v_open integer;v_date date;v_total integer;
  v_product uuid;v_root uuid;v_model uuid;v_contractor uuid;v_component uuid;v_rate numeric;v_found numeric;v_before integer;v_qty integer;
begin
  perform erp.require_owner_admin();
  select * into r from erp.migration_staging_rows where id=p_row and batch_id=p_batch;
  if r.id is null then raise exception 'Baris impor tidak ditemukan';end if;
  select (cutover_at at time zone 'Asia/Jakarta')::date into v_cutover from erp.migration_batches where id=p_batch;
  if r.entity_type='OPENING_REWORK' then w:=r;
  else
    j:=r.normalized_payload;
    foreach k in array array['rework_number','work_component_code','completed_before_bs_qty','qty_performed','rate_per_pcs'] loop
      if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk komponen rework terbuka',k;end if;
    end loop;
    select * into w from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_REWORK'
      and lower(btrim(x.normalized_payload->>'rework_number'))=lower(btrim(j->>'rework_number'));
    if w.id is null then raise exception 'BB_REWORK_UNKNOWN: nomor rework tidak ada di file rework terbuka impor ini';end if;
  end if;
  wj:=w.normalized_payload;
  foreach k in array array['rework_number','bs_source_key','destination_type','sent_date','qty_sent_original','qty_returned_before_cutover','qty_open'] loop
    if nullif(btrim(wj->>k),'') is null then raise exception '%: wajib diisi untuk rework terbuka',k;end if;
  end loop;
  if length(btrim(wj->>'rework_number'))>50 then raise exception 'rework_number: maksimal 50 karakter';end if;
  if (select count(*) from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_REWORK'
      and lower(btrim(x.normalized_payload->>'rework_number'))=lower(btrim(wj->>'rework_number')))>1
     or exists(select 1 from erp.rework_orders ro where lower(ro.rework_number)=lower('ORW-'||btrim(wj->>'rework_number'))) then
    raise exception 'BB_REWORK_NUMBER_DUPLICATE: nomor rework sudah dipakai';
  end if;
  select * into v_bs from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_BALANCE_ITEM'
    and upper(x.normalized_payload->>'balance_type')='BS' and nullif(x.normalized_payload->>'po_number','') is not null
    and x.normalized_payload->>'opening_source_key'=wj->>'bs_source_key' and x.validation_status='VALID';
  if v_bs.id is null then
    raise exception 'BB_REWORK_BS_SOURCE_REQUIRED: bs_source_key harus menunjuk baris BS ber-PO yang valid di impor ini';
  end if;
  b:=v_bs.normalized_payload;
  v_sent:=erp.bb_parse_count_v1(wj->>'qty_sent_original','qty_sent_original',1);
  v_returned:=erp.bb_parse_count_v1(wj->>'qty_returned_before_cutover','qty_returned_before_cutover',0);
  v_open:=erp.bb_parse_count_v1(wj->>'qty_open','qty_open',1);
  if v_open<>v_sent-v_returned then
    raise exception 'BB_REWORK_OPEN_QTY_MISMATCH: sisa di rework (%) harus sama dengan dikirim (%) dikurangi kembali sebelum cutover (%)',v_open,v_sent,v_returned;
  end if;
  select coalesce(sum((x.normalized_payload->>'qty_open')::integer),0) into v_total from erp.migration_staging_rows x
    where x.batch_id=p_batch and x.entity_type='OPENING_REWORK' and x.normalized_payload->>'bs_source_key'=wj->>'bs_source_key'
      and x.normalized_payload->>'qty_open' ~ '^[0-9]{1,9}$';
  if v_total>(b->>'qty')::numeric then raise exception 'BB_REWORK_EXCEEDS_BS: rework terbuka melebihi jumlah BS asalnya';end if;
  v_date:=erp.bb_parse_date_v1(wj->>'sent_date','sent_date');
  if v_date>v_cutover then raise exception 'BB_REWORK_SENT_DATE: rework terbuka dikirim sebelum atau pada tanggal saldo awal';end if;
  if upper(wj->>'destination_type')='CONTRACTOR' then
    if nullif(btrim(wj->>'vendor_code'),'') is not null or nullif(btrim(wj->>'contractor_code'),'') is null
       or wj->>'contractor_code' is distinct from b->>'contractor_code' then
      raise exception 'BB_REWORK_HOLDER_MISMATCH: rework ke mandor harus ke mandor pemegang baris BS asalnya';
    end if;
    select c.id into v_contractor from erp.contractors c where c.contractor_code=wj->>'contractor_code' and c.is_active and c.contractor_type='MANDOR';
    if v_contractor is null then raise exception 'BB_REWORK_MANDOR: mandor rework harus mandor aktif yang sudah ada';end if;
    if not exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_REWORK_COMPONENT'
        and lower(btrim(x.normalized_payload->>'rework_number'))=lower(btrim(wj->>'rework_number'))) then
      raise exception 'BB_REWORK_COMPONENT_REQUIRED: rework ke mandor memerlukan komponen kerja';
    end if;
  elsif upper(wj->>'destination_type')='LAUNDRY' then
    if nullif(btrim(wj->>'contractor_code'),'') is not null or nullif(btrim(wj->>'vendor_code'),'') is null
       or wj->>'vendor_code' is distinct from b->>'vendor_code' then
      raise exception 'BB_REWORK_HOLDER_MISMATCH: rework ke laundry harus ke laundry pemegang baris BS asalnya';
    end if;
    if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_REWORK_COMPONENT'
        and lower(btrim(x.normalized_payload->>'rework_number'))=lower(btrim(wj->>'rework_number'))) then
      raise exception 'BB_REWORK_LAUNDRY_COMPONENT: rework laundry tidak memakai komponen upah mandor';
    end if;
  else raise exception 'destination_type: isi CONTRACTOR atau LAUNDRY';
  end if;
  -- The native rework of a BS with PO and product needs the product's accessory BOM (an explicit empty one is enough).
  v_product:=erp.bf_resolve_import_product_v1(p_batch,b,false);
  select p.identity_root_id,p.model_id into v_root,v_model from erp.products p where p.id=v_product;
  if v_product is null or not exists(select 1 from erp.accessory_bom_versions a where a.product_id=v_root and a.is_active
      and a.effective_from<=((v_cutover+1)::timestamp at time zone 'Asia/Jakarta')
      and (a.effective_to is null or a.effective_to>(v_cutover::timestamp at time zone 'Asia/Jakarta'))) then
    raise exception 'BB_REWORK_ACCESSORY_BOM_REQUIRED: produk BS asal belum punya BOM aksesori yang berlaku (BOM kosong pun harus dicatat)';
  end if;
  if r.entity_type='OPENING_REWORK' then
    return jsonb_build_object('kind','REWORK','open_qty',v_open,'sent_qty',v_sent,'returned_qty',v_returned,'sent_date',v_date);
  end if;
  -- Component row.
  if upper(wj->>'destination_type')<>'CONTRACTOR' then raise exception 'BB_REWORK_LAUNDRY_COMPONENT: rework laundry tidak memakai komponen upah mandor';end if;
  select id into v_component from erp.work_components where component_code=j->>'work_component_code' and is_active;
  if v_component is null then raise exception 'BB_REWORK_COMPONENT_UNKNOWN: komponen kerja aktif tidak ditemukan';end if;
  if (select count(*) from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_REWORK_COMPONENT'
      and lower(btrim(x.normalized_payload->>'rework_number'))=lower(btrim(j->>'rework_number'))
      and x.normalized_payload->>'work_component_code'=j->>'work_component_code')>1 then
    raise exception 'BB_REWORK_COMPONENT_DUPLICATE: komponen yang sama tercatat dua kali pada rework ini';
  end if;
  v_qty:=erp.bb_parse_count_v1(j->>'qty_performed','qty_performed',1);
  if v_qty>v_open then raise exception 'BB_REWORK_COMPONENT_QTY: qty dikerjakan tidak boleh melebihi sisa di rework';end if;
  v_before:=erp.bb_parse_count_v1(j->>'completed_before_bs_qty','completed_before_bs_qty',0);
  if v_before>(b->>'qty')::numeric then raise exception 'BB_REWORK_BASELINE: pcs yang sudah selesai sebelum BS tidak boleh melebihi jumlah BS';end if;
  if exists(select 1 from erp.migration_staging_rows x join erp.migration_staging_rows y on y.batch_id=x.batch_id and y.entity_type='OPENING_REWORK'
      and lower(btrim(y.normalized_payload->>'rework_number'))=lower(btrim(x.normalized_payload->>'rework_number'))
      where x.batch_id=p_batch and x.entity_type='OPENING_REWORK_COMPONENT' and x.id<>r.id
        and y.normalized_payload->>'bs_source_key'=wj->>'bs_source_key' and x.normalized_payload->>'work_component_code'=j->>'work_component_code'
        and x.normalized_payload->>'completed_before_bs_qty' is distinct from j->>'completed_before_bs_qty') then
    raise exception 'BB_REWORK_BASELINE_CONFLICT: pcs selesai sebelum BS untuk komponen yang sama harus sama pada setiap rework BS itu';
  end if;
  v_rate:=erp.bb_parse_amount_v1(j->>'rate_per_pcs','rate_per_pcs',true);
  select po.normalized_payload into v_po from erp.migration_staging_rows po where po.batch_id=p_batch and po.entity_type='OPEN_PO'
    and po.normalized_payload->>'po_number'=b->>'po_number' and po.validation_status='VALID';
  select m.id into v_model from erp.product_models m where m.model_code=v_po->>'model_code';
  select cwr.rate_per_pcs into v_found from erp.contractor_work_rates cwr where cwr.contractor_id=v_contractor and cwr.model_id=v_model
    and cwr.work_component_id=v_component and cwr.effective_from<=(v_cutover::timestamp at time zone 'Asia/Jakarta')
    and (cwr.effective_to is null or cwr.effective_to>(v_cutover::timestamp at time zone 'Asia/Jakarta'))
    order by cwr.effective_from desc,cwr.id desc limit 1;
  if v_found is null then raise exception 'BB_REWORK_RATE_MISSING: tarif mandor untuk model dan komponen ini belum berlaku pada cutover';end if;
  if v_found<>v_rate then raise exception 'BB_REWORK_RATE_MISMATCH: tarif baris (%) berbeda dengan tarif mandor yang berlaku (%)',v_rate,v_found;end if;
  return jsonb_build_object('kind','COMPONENT','work_component_id',v_component,'qty_performed',v_qty,'completed_before_bs_qty',v_before,'rate',v_rate);
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
 v_catalog constant jsonb:='{"LAUNDRY_VENDOR": {"label": "Vendor laundry", "required": ["vendor_code", "vendor_name"], "fields": {"vendor_code": "Kode laundry", "vendor_name": "Nama laundry", "phone": "Telepon", "is_active": "Aktif", "notes": "Catatan"}}, "LOCATION": {"label": "Lokasi dan gudang", "required": ["location_code", "location_name", "location_type"], "fields": {"location_code": "Kode lokasi", "location_name": "Nama lokasi", "location_type": "Jenis lokasi", "is_active": "Aktif"}}, "CHART_ACCOUNT": {"label": "Akun buku besar", "required": ["account_code", "account_name", "account_type", "report_group", "normal_balance"], "fields": {"account_code": "Kode akun", "account_name": "Nama akun", "account_type": "Jenis akun", "report_group": "Kelompok laporan", "normal_balance": "Saldo normal", "parent_account_code": "Kode akun induk", "is_postable": "Boleh dipakai jurnal", "is_active": "Aktif"}}, "CASH_ACCOUNT": {"label": "Rekening kas dan bank", "required": ["cash_account_code", "cash_account_name", "coa_account_code", "account_kind"], "fields": {"cash_account_code": "Kode kas bank", "cash_account_name": "Nama kas bank", "coa_account_code": "Kode akun buku besar", "account_kind": "Jenis rekening", "is_active": "Aktif"}}, "BRAND": {"label": "Merek", "required": ["brand_code", "brand_name"], "fields": {"brand_code": "Kode merek", "brand_name": "Nama merek", "is_active": "Aktif"}}, "SIZE": {"label": "Ukuran", "required": ["size_code"], "fields": {"size_code": "Kode ukuran", "sort_order": "Urutan", "is_active": "Aktif"}}, "MODEL": {"label": "Model produk", "required": ["model_code", "model_name"], "fields": {"model_code": "Kode model", "model_name": "Nama model", "description": "Keterangan", "is_active": "Aktif"}}, "PRODUCT": {"label": "Produk per ukuran", "required": ["sku", "product_name", "model_code", "brand_code", "color_name", "size_code"], "fields": {"sku": "Kode produk", "product_name": "Nama produk", "model_code": "Kode model", "brand_code": "Kode merek", "color_name": "Warna", "size_code": "Kode ukuran", "is_active": "Aktif"}}, "CUSTOMER": {"label": "Pelanggan", "required": ["customer_code", "customer_name"], "fields": {"customer_code": "Kode pelanggan", "customer_name": "Nama pelanggan", "phone": "Telepon", "address": "Alamat", "is_active": "Aktif"}}, "SUPPLIER": {"label": "Supplier", "required": ["supplier_code", "supplier_name"], "fields": {"supplier_code": "Kode supplier", "supplier_name": "Nama supplier", "supplier_type": "Jenis supplier", "phone": "Telepon", "address": "Alamat", "is_active": "Aktif"}}, "CONTRACTOR": {"label": "Mandor", "required": ["contractor_code", "contractor_name"], "fields": {"contractor_code": "Kode mandor", "contractor_name": "Nama mandor", "contractor_type": "Jenis mandor", "attendance_required": "Wajib absensi", "is_active": "Aktif", "notes": "Catatan"}}, "ACCESSORY_CATEGORY": {"label": "Kategori aksesori", "required": ["category_code", "category_name", "base_uom_code"], "fields": {"category_code": "Kode kategori", "category_name": "Nama kategori", "base_uom_code": "Satuan dasar", "is_active": "Aktif", "notes": "Catatan"}}, "MATERIAL": {"label": "Bahan dan aksesori", "required": ["material_sku", "material_name", "material_type", "unit_code"], "fields": {"material_sku": "Kode bahan", "material_name": "Nama bahan", "material_type": "Jenis bahan", "unit_code": "Satuan dasar", "accessory_category_code": "Kode kategori aksesori", "is_active": "Aktif"}}, "MATERIAL_ROLL": {"label": "Stok awal kain per roll", "required": ["material_sku", "roll_number", "opening_qty", "unit_cost", "location_code", "control_key"], "fields": {"material_sku": "Kode bahan", "roll_number": "Nomor roll", "opening_qty": "Jumlah awal", "unit_cost": "Biaya per satuan", "location_code": "Kode gudang", "supplier_code": "Kode supplier", "notes": "Catatan", "control_key": "Kode total pembanding", "opening_source_key": "Kode rincian stok asal"}}, "OPENING_BALANCE_ITEM": {"label": "Stok dan saldo awal", "required": ["balance_type", "control_key"], "fields": {"balance_type": "Jenis saldo", "material_sku": "Kode bahan", "product_sku": "Kode produk", "brand_code": "Kode merek", "model_code": "Kode model", "color_name": "Warna", "size_code": "Kode ukuran", "location_code": "Kode gudang", "contractor_code": "Kode mandor", "customer_code": "Kode pelanggan", "supplier_code": "Kode supplier", "vendor_code": "Kode laundry", "cash_account_code": "Kode kas bank", "stage": "Tahap produksi", "qty": "Jumlah", "unit_cost": "Biaya per satuan", "amount": "Nominal", "quality_grade": "Kualitas", "hpp_input_method": "Cara isi HPP", "hpp_percent_of_price": "Persentase HPP", "notes": "Catatan", "control_key": "Kode total pembanding", "document_number": "Nomor dokumen asal", "document_date": "Tanggal dokumen asal", "due_date": "Tanggal jatuh tempo", "original_amount": "Nominal dokumen awal", "settled_before_cutover": "Sudah dibayar sebelum saldo awal", "opening_source_key": "Kode rincian stok asal", "source_kind": "Jenis sumber saldo", "po_number": "Nomor PO saldo fisik", "accessory_cost_included": "Biaya aksesoris sudah termasuk (true/false)"}}, "OPEN_PO": {"label": "Pesanan produksi berjalan", "required": ["po_number", "model_code", "status", "current_stage"], "fields": {"po_number": "Nomor pesanan", "model_code": "Kode model", "contractor_code": "Kode mandor", "target_qty_pcs": "Target buah", "target_dozens": "Target lusin", "status": "Status", "current_stage": "Tahap produksi", "physical_start_at": "Waktu mulai fisik", "notes": "Catatan"}}, "OPENING_CONTROL": {"label": "Total pembanding saldo awal", "required": ["control_key", "balance_type", "amount"], "fields": {"control_key": "Kode total pembanding", "balance_type": "Jenis saldo", "qty": "Total jumlah", "amount": "Total nominal", "notes": "Catatan"}}, "UNINVOICED_RECEIPT": {"label": "Penerimaan belum ditagih — sisa bahan dan asal biaya", "required": ["receipt_number", "receipt_line_number", "receipt_date", "supplier_code", "material_sku", "location_code", "qty", "unit_cost", "control_key"], "fields": {"receipt_number": "Nomor penerimaan asal", "receipt_line_number": "Nomor baris penerimaan", "receipt_date": "Tanggal penerimaan asal", "supplier_code": "Kode supplier", "material_sku": "Kode bahan", "location_code": "Kode gudang", "qty": "Jumlah belum ditagih", "unit_cost": "Biaya estimasi per satuan", "opening_source_key": "Kode rincian stok asal", "control_key": "Kode total pembanding", "notes": "Catatan", "invoice_document_number": "Nomor invoice asal untuk bagian yang sudah ditagih", "invoiced_qty": "Jumlah yang sudah ditagih sebelum saldo awal"}}, "OPENING_ADVANCE": {"label": "Uang muka tersisa", "required": ["party_type", "party_code", "coa_account_code", "document_number", "document_date", "original_amount", "settled_before_cutover", "amount", "control_key"], "fields": {"party_type": "Jenis pihak", "party_code": "Kode pihak", "coa_account_code": "Kode akun uang muka", "document_number": "Nomor bukti uang muka", "document_date": "Tanggal uang muka", "original_amount": "Nominal asal", "settled_before_cutover": "Terpakai atau kembali sebelum saldo awal", "amount": "Sisa uang muka", "control_key": "Kode total pembanding"}}, "OPENING_COST_ORIGIN": {"label": "Asal biaya yang sudah terpakai sebelum cutover", "fields": {"supplier_code": "Kode supplier", "receipt_number": "Nomor penerimaan asal", "receipt_line_number": "Nomor baris penerimaan", "target_source_key": "Kode rincian WIP/BS/FG tujuan", "qty": "Jumlah bahan yang sudah terpakai", "notes": "Catatan"}, "required": ["supplier_code", "receipt_number", "receipt_line_number", "target_source_key", "qty"]}, "LEGACY_DOCUMENT": {"label": "Dokumen lama yang sudah lunas penuh", "required": ["balance_type", "party_code", "document_number", "document_date", "original_amount", "settled_before_cutover"], "fields": {"balance_type": "Jenis saldo dokumen", "party_code": "Kode pihak", "document_number": "Nomor dokumen asal", "document_date": "Tanggal dokumen asal", "original_amount": "Nominal dokumen awal", "settled_before_cutover": "Sudah dibayar sebelum saldo awal", "notes": "Catatan"}}, "OPENING_CUSTOMER_CREDIT": {"label": "Kredit retur pelanggan yang belum dikembalikan", "required": ["customer_code", "coa_account_code", "document_number", "document_date", "original_amount", "settled_before_cutover", "amount"], "fields": {"customer_code": "Kode pelanggan", "coa_account_code": "Kode akun kredit pelanggan", "document_number": "Nomor nota retur/kredit", "document_date": "Tanggal nota retur/kredit", "original_amount": "Nominal kredit asal", "settled_before_cutover": "Sudah dikembalikan sebelum saldo awal", "amount": "Sisa kredit", "notes": "Catatan"}}, "OPENING_SALE_RETURN": {"label": "Hak retur penjualan lama yang barangnya belum kembali", "required": ["customer_code", "return_number", "invoice_document_number", "product_sku", "qty", "credit_unit_price", "unit_cost", "credit_coa_account_code"], "fields": {"customer_code": "Kode pelanggan", "return_number": "Nomor persetujuan retur", "invoice_document_number": "Nomor invoice asal", "product_sku": "Kode produk", "brand_code": "Kode merek", "model_code": "Kode model", "color_name": "Warna", "size_code": "Kode ukuran", "qty": "Jumlah pcs boleh diretur", "credit_unit_price": "Kredit per pcs", "unit_cost": "Nilai persediaan per pcs", "credit_coa_account_code": "Kode akun kredit pelanggan", "notes": "Catatan"}}, "OPEN_PURCHASE_ORDER": {"label": "PO pembelian yang belum diterima penuh saat saldo awal", "required": ["po_number", "po_line_number", "po_date", "supplier_code", "location_code", "material_sku", "ordered_qty", "received_before_cutover_qty", "cancelled_before_cutover_qty", "remaining_qty", "unit_price"], "fields": {"po_number": "Nomor PO pembelian", "po_line_number": "Nomor baris PO", "po_date": "Tanggal PO", "supplier_code": "Kode supplier", "location_code": "Kode gudang tujuan", "material_sku": "Kode bahan", "ordered_qty": "Jumlah dipesan", "received_before_cutover_qty": "Sudah diterima sebelum saldo awal", "cancelled_before_cutover_qty": "Sudah dibatalkan sebelum saldo awal", "remaining_qty": "Sisa yang masih ditunggu", "unit_price": "Harga estimasi per satuan", "expected_date": "Perkiraan tanggal datang", "notes": "Catatan"}}, "OPENING_PAYROLL_ENTITLEMENT": {"label": "Hak upah, absensi, atau reimburse sebelum saldo awal yang belum disetujui", "required": ["kind", "contractor_code", "document_number", "line_number", "document_date", "rate"], "fields": {"kind": "Jenis hak (SEWING_WORK/ATTENDANCE/ACCESSORY_REIMBURSEMENT)", "contractor_code": "Kode mandor", "document_number": "Nomor dokumen hutang mandor", "line_number": "Nomor baris", "document_date": "Tanggal hak timbul", "rate": "Tarif", "po_number": "Nomor PO (upah jahit)", "work_component_code": "Kode komponen kerja", "earned_qty": "Jumlah dikerjakan", "paid_before_qty": "Jumlah sudah dibayar sebelum saldo awal", "carry_qty": "Jumlah komponen dibawa (carry)", "worker_name": "Nama pekerja (absensi)", "period_start": "Awal periode absensi", "period_end": "Akhir periode absensi", "days": "Jumlah hari dibayar", "category_code": "Kode kategori aksesori", "good_qty": "Jumlah GOOD", "paid_before_amount": "Nominal sudah dibayar sebelum saldo awal", "notes": "Catatan"}}, "OPENING_REWORK": {"label": "Rework yang masih di mandor atau laundry saat saldo awal", "required": ["rework_number", "bs_source_key", "destination_type", "sent_date", "qty_sent_original", "qty_returned_before_cutover", "qty_open"], "fields": {"rework_number": "Nomor rework asal", "bs_source_key": "Kode rincian BS asal (opening_source_key baris BS)", "destination_type": "Tujuan rework (CONTRACTOR/LAUNDRY)", "contractor_code": "Kode mandor rework", "vendor_code": "Kode laundry rework", "sent_date": "Tanggal kirim rework", "qty_sent_original": "Jumlah dikirim", "qty_returned_before_cutover": "Sudah kembali sebelum saldo awal", "qty_open": "Masih di rework saat saldo awal", "notes": "Catatan"}}, "OPENING_REWORK_COMPONENT": {"label": "Komponen upah rework terbuka", "required": ["rework_number", "work_component_code", "completed_before_bs_qty", "qty_performed", "rate_per_pcs"], "fields": {"rework_number": "Nomor rework asal", "work_component_code": "Kode komponen kerja", "completed_before_bs_qty": "Pcs yang komponennya sudah selesai sebelum BS", "qty_performed": "Pcs yang akan dikerjakan", "rate_per_pcs": "Tarif per pcs"}}, "OPEN_SALES_DRAFT": {"label": "Draf penjualan yang masih terbuka saat saldo awal (dengan reservasi)", "required": ["draft_number", "line_number", "draft_date", "customer_code", "location_code", "product_sku", "qty_pcs", "unit_price"], "fields": {"draft_number": "Nomor draf penjualan", "line_number": "Nomor baris draf", "draft_date": "Tanggal draf lama", "customer_code": "Kode pelanggan", "location_code": "Kode gudang barang jadi", "product_sku": "Kode produk", "qty_pcs": "Jumlah pcs yang direservasi", "unit_price": "Harga per pcs", "discount_amount": "Potongan baris", "due_date": "Jatuh tempo", "payment_terms": "Syarat pembayaran", "notes": "Catatan", "product_id": "ID produk fisik asal (opsional; harus cocok dengan identitas baris)", "size_code": "Ukuran fisik asal", "brand_code": "Kode merek asal", "model_code": "Kode model asal", "color_name": "Warna asal"}}, "OPENING_ACCESSORY_NOTE_LINE": {"label": "Baris nota aksesori mandor lama (di balik piutang mandor saldo awal)", "required": ["document_number", "contractor_code", "line_number", "material_sku", "qty", "line_amount"], "fields": {"document_number": "Nomor nota lama (sama dengan dokumen piutang mandor)", "contractor_code": "Kode mandor", "line_number": "Nomor baris nota", "material_sku": "Kode aksesori", "qty": "Jumlah (PCS utuh untuk aksesori hitung)", "line_amount": "Nominal baris nota asal", "notes": "Catatan"}}, "OPENING_ACCESSORY_CUSTODY": {"label": "Aksesori yang bukan stok siap pakai: titipan belum dinilai, belum kembali, titipan pelanggan", "required": ["custody_kind", "custody_key", "qty"], "fields": {"custody_kind": "Jenis (PENDING_VALUE, UNRETURNED, CUSTOMER_GARMENT)", "custody_key": "Kode opname (satu barang fisik satu kode)", "material_sku": "Kode aksesori", "location_code": "Kode area pemeriksaan (PENDING_VALUE)", "condition": "Kondisi (WAITING, USABLE, DAMAGED)", "qty": "Jumlah PCS", "holder": "Pemegang (UNRETURNED)", "owner_kind": "Pemilik (COMPANY atau CUSTOMER)", "customer_code": "Kode pelanggan (CUSTOMER_GARMENT)", "product_sku": "Kode produk (opsional)", "description": "Keterangan barang", "notes": "Catatan", "count_sheet": "Nomor lembar hitung sumber (D09: isi bersama baris lembar, atau pakai lot sumber)", "sheet_line": "Baris/item di lembar hitung", "source_lot": "Lot sumber (pengganti lembar hitung + baris)", "product_id": "ID produk fisik asal (opsional; harus cocok dengan identitas baris)", "size_code": "Ukuran fisik asal", "brand_code": "Kode merek asal", "model_code": "Kode model asal", "color_name": "Warna asal"}}, "OPENING_LAUNDRY_CLAIM": {"label": "Klaim laundry yang terdokumentasi atas WIP di vendor (hilang, tertahan, rusak)", "required": ["claim_number", "source_key", "vendor_code", "claim_type", "qty", "claim_date"], "fields": {"claim_number": "Nomor klaim", "source_key": "Kode rincian WIP laundry (opening_source_key)", "vendor_code": "Kode laundry (sama dengan pemegang WIP)", "claim_type": "Jenis klaim (MISSING, STUCK, DAMAGE)", "qty": "Jumlah PCS yang diklaim", "claim_date": "Tanggal klaim (sebelum atau pada tanggal saldo awal)", "dispatch_number": "Nomor kirim laundry lama", "notes": "Catatan"}}, "OPENING_LAUNDRY_UNINVOICED": {"label": "Hasil laundry yang sudah kembali sebelum cutover tetapi belum ditagih vendor", "required": ["document_number", "vendor_code", "receipt_date", "category", "qty"], "fields": {"document_number": "Nomor terima laundry lama", "vendor_code": "Kode laundry", "receipt_date": "Tanggal terima (sebelum atau pada tanggal saldo awal)", "category": "Kategori tagihan (GOOD, BS, FAILED_ATTEMPT)", "qty": "Jumlah PCS belum ditagih", "estimated_amount": "Estimasi tagihan yang terbukti (kosong = belum diketahui)", "po_number": "Nomor PO asal", "dispatch_number": "Nomor kirim laundry lama", "notes": "Catatan"}}, "OPENING_POCKET_USAGE": {"label": "Kain kantong keluar sebelum cutover", "required": ["document_number", "line_number", "physical_date", "material_sku", "qty", "amount", "allocation_status", "control_key", "control_qty", "control_amount"], "fields": {"document_number": "Nomor lembar pengeluaran asal", "line_number": "Baris asal", "physical_date": "Tanggal keluar sebelum cutover", "material_sku": "Kode bahan", "qty": "Jumlah kain sudah keluar", "amount": "Nilai historis", "allocation_status": "ALLOCATED / UNALLOCATED", "prior_allocation_reference": "Referensi pembagian lama (ALLOCATED)", "control_key": "Identitas total pembanding", "control_qty": "Total jumlah pada lembar pembanding", "control_amount": "Total nilai pada lembar pembanding", "notes": "Catatan", "supplier_code": "Supplier penerimaan belum ditagih (opsional)", "receipt_number": "Nomor penerimaan asal (opsional)", "receipt_line_number": "Baris penerimaan asal (opsional)"}}, "OPENING_POCKET_SEWING": {"label": "Hasil jahit sebelum cutover untuk pembagian kain kantong", "required": ["document_number", "line_number", "physical_date", "contractor_code", "qty", "target_kind", "control_key", "control_qty"], "fields": {"document_number": "Nomor lembar hasil jahit", "line_number": "Baris asal", "physical_date": "Tanggal selesai dijahit sebelum cutover", "contractor_code": "Kode mandor (termasuk khusus)", "qty": "PCS selesai dijahit", "target_kind": "WIP / BS / FINISHED_GOODS / COGS", "target_source_key": "Kode rincian stok awal tujuan", "product_sku": "SKU yang sudah terjual (COGS)", "sold_reference": "Bukti penjualan historis (COGS)", "notes": "Catatan", "control_key": "Identitas total hasil jahit pembanding", "control_qty": "Total PCS pada lembar pembanding", "product_id": "ID produk fisik asal (opsional; harus cocok dengan identitas baris)", "size_code": "Ukuran fisik asal", "brand_code": "Kode merek asal", "model_code": "Kode model asal", "color_name": "Warna asal"}}}'::jsonb;
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
CREATE OR REPLACE FUNCTION erp.material_purchase_final_ap_total(p_purchase_id uuid)
 RETURNS numeric
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
with item_ap as(
  select i.id,
    case when i.invoice_match_state='DIRECT_FINAL'
      then i.qty*erp.material_purchase_current_unit_cost(i.id)
      else coalesce((
        select sum(l.net_amount)
        from erp.material_supplier_invoice_lines l
        join erp.material_supplier_invoices h on h.id=l.invoice_id
        where l.purchase_item_id=i.id and h.status='POSTED'
      ),0)
    end as gross_ap
  from erp.material_purchase_items i where i.purchase_id=$1
),return_relief as(
  select coalesce(sum(coalesce(ri.ap_relief_amount_snapshot,0)),0) amount
  from erp.material_supplier_return_items ri
  join erp.material_supplier_returns r on r.id=ri.return_id
  join erp.material_purchase_items i on i.id=ri.purchase_item_id
  where i.purchase_id=$1 and r.status='POSTED'
)
select greatest(coalesce(sum(item_ap.gross_ap),0)-(select amount from return_relief),0)::numeric+erp.bf_supplier_credit_delta_v1(p_purchase_id)
from item_ap
$function$;
CREATE OR REPLACE FUNCTION erp._cp6_supplier_cent_state(p_purchases uuid[])
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'pg_catalog', 'pg_temp'
AS $function$
 select coalesce(jsonb_object_agg(h.id::text,jsonb_build_object(
  'ap',round(erp.material_purchase_final_ap_total(h.id)-erp.bf_supplier_credit_delta_v1(h.id),2),
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
CREATE OR REPLACE FUNCTION erp.post_supplier_payment(p_payment_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare p erp.supplier_payments%rowtype;h erp.material_purchase_headers%rowtype;v_cash uuid;v_paid numeric(20,2);v_total numeric(20,2);
begin
  perform erp.require_internal();select * into p from erp.supplier_payments where id=p_payment_id for update;
  if p.id is null or p.status<>'DRAFT' then raise exception 'Supplier payment must be DRAFT'; end if;
  select * into h from erp.material_purchase_headers where id=p.purchase_id for update;
  if h.id is null or h.status<>'POSTED' then raise exception 'Material purchase must be POSTED before payment'; end if;
  select least(erp.material_purchase_payable_total(h.id),
         erp.material_purchase_payable_total(h.id)-erp.bf_supplier_credit_delta_v1(h.id)
         +erp.bf_supplier_credit_delta_v1(h.id,erp._cp3_business_date(p.payment_date)))::numeric(20,2) into v_total;
  select coalesce(sum(amount),0)::numeric(20,2) into v_paid from erp.supplier_payments where purchase_id=h.id and status='POSTED';
  if v_paid+p.amount>v_total then raise exception 'Supplier payment exceeds remaining payable. Net payable %, already paid %, requested %',v_total,v_paid,p.amount; end if;
  v_cash:=erp.initial_prepayment_funding_v1(p.id,'SUPPLIER',h.supplier_id,p.amount,erp._cp3_business_date(p.payment_date),greatest(erp._cp3_business_date(h.physical_at),(select max(i.invoice_date) from erp.material_supplier_invoices i join erp.material_supplier_invoice_lines l on l.invoice_id=i.id join erp.material_purchase_items pi on pi.id=l.purchase_item_id where pi.purchase_id=h.id and i.status='POSTED')));
  if v_cash is null then
  select coa_account_id into v_cash from erp.cash_accounts where id=p.cash_account_id and is_active=true;
  end if;
  if v_cash is null then raise exception 'Active cash/bank account is required'; end if;
  perform erp.post_journal('SUPPLIER_PAYMENT',p.id,erp._cp3_business_date(p.payment_date),'Material supplier payment',jsonb_build_array(
    jsonb_build_object('mapping_key','AP_SUPPLIER','debit',p.amount,'credit',0),jsonb_build_object('account_id',v_cash,'debit',0,'credit',p.amount)));
  update erp.supplier_payments set status='POSTED' where id=p.id;v_paid:=v_paid+p.amount;
  update erp.material_purchase_headers set payment_status=case when v_paid=round(erp.material_purchase_payable_total(h.id),2) then 'PAID' else 'PARTIAL' end where id=h.id;
end;$function$;
CREATE OR REPLACE FUNCTION erp.get_product_conversion_workspace_v1(p_filters jsonb default '{}'::jsonb)
 RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path TO ''
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
 with lots as(select l.id,l.lot_number,l.product_id,l.po_id,l.produced_at,erp.bf_commercial_sku_at_v1(p.id,statement_timestamp()) sku,p.product_name,p.model_id,p.size_id,
       m.location_id,loc.location_name,sum(m.qty_signed)::integer qty
     from erp.fg_lots l join erp.products p on p.id=l.product_id join erp.fg_stock_movements m on m.lot_id=l.id
     join erp.locations loc on loc.id=m.location_id
     where m.quality_grade='GRADE_A' and (v_lot is null or l.id=v_lot)
       and (v_query='' or lower(concat_ws(' ',p.sku,erp.bf_commercial_sku_at_v1(p.id,statement_timestamp()),p.product_name,l.lot_number)) like '%'||v_query||'%')
     group by l.id,p.id,m.location_id,loc.location_name having sum(m.qty_signed)>0),
   pg as(select * from lots order by produced_at,id,location_id limit v_size offset (v_page-1)*v_size)
 select jsonb_build_object('total',(select count(*) from lots),'page',v_page,'page_size',v_size,
   'lots',coalesce(jsonb_agg(to_jsonb(pg)||jsonb_build_object('source_revision',erp.be_source_revision_v1(id,location_id),
     'unit_hpp',case when v_values then (select hpp_per_pcs::text from erp.v_current_hpp where lot_id=pg.id) end) order by produced_at,id,location_id),'[]'::jsonb))
 into v_result from pg;
 with targets as(select p.id,erp.bf_commercial_sku_at_v1(p.id,statement_timestamp()) sku,p.product_name,p.model_id,p.size_id from erp.products p
    join erp.products source_product on source_product.id=v_product
    where p.is_active and p.model_id=source_product.model_id and p.size_id=source_product.size_id and p.id<>source_product.id
      and (v_target_query='' or lower(concat_ws(' ',p.sku,erp.bf_commercial_sku_at_v1(p.id,statement_timestamp()),p.product_name)) like '%'||v_target_query||'%')),
   target_page as(select * from targets order by sku,id limit v_size offset (v_target_page-1)*v_size)
 select v_result||jsonb_build_object('targets',coalesce((select jsonb_agg(to_jsonb(x) order by x.sku,x.id) from target_page x),'[]'::jsonb),
   'targets_total',(select count(*) from targets),'target_page',v_target_page) into v_result;
 with docs as(select c.id,c.conversion_number,c.status,c.qty_pcs,c.physical_at,c.notes,s.origin_kind,s.source_lot_id,s.rework_id,
    erp.bf_commercial_sku_at_v1(p.id,c.physical_at) source_sku,erp.bf_commercial_sku_at_v1(t.id,c.physical_at) target_sku,a.destination_lot_id,erp.be_conversion_revision_v1(c.id) revision,
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

do $grants$ declare t text;f record;begin
 foreach t in array ARRAY['bf_rollback_v1','bf_skus_v1','bf_sku_versions_v1','bf_sku_members_v1','bf_wave_skus_v1','bf_po_boms_v1','bf_requests_v1','bf_context_v1','bf_laundry_delivery_sources_v1','bf_supplier_credit_moves_v1'] loop
   execute format('alter table erp.%I enable row level security',t);
   execute format('revoke all on erp.%I from public,anon,authenticated,service_role',t);
 end loop;
 for f in select p.oid::regprocedure sig,n.nspname from pg_proc p join pg_namespace n on n.oid=p.pronamespace
   where (n.nspname='erp' and(p.proname like 'bf\_%' or p.proname in('save_sku_action_v1','get_sku_workspace_v1','get_sku_hpp_v1')))
     or (n.nspname='public' and p.proname in('erp_save_sku_action_v1','erp_get_sku_workspace_v1','erp_get_sku_hpp_v1','erp_get_laundry_history_v1','erp_save_supplier_credit_v1','erp_get_supplier_credit_v1')) loop
   execute format('revoke all on function %s from public,anon,authenticated,service_role',f.sig);
   if f.nspname='public' then execute format('grant execute on function %s to authenticated,service_role',f.sig);end if;
 end loop;
end $grants$;


update erp.bf_rollback_v1 set payload=payload||jsonb_build_object('installed',(
 select jsonb_object_agg(p.oid::regprocedure::text,md5(pg_get_functiondef(p.oid))) from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname||'.'||p.proname=any(array['erp.commit_accessory_bom_for_lot','erp.ensure_po_work_component_snapshots','erp.validate_work_completion','erp.guard_work_completion_posting_consistency','erp.seed_bs_case_component_baseline','erp.classify_bs_case_v2','erp.cp6_lot_work_cost_v2620c','erp.assert_new_stock_cutoff_coverage_v1','erp.bd_priced_line_json_v1','erp.bd_compute_pricing_v1','erp.bd_attach_delivery_pricing_v1','erp.bd_refresh_size_estimates_v1','erp.bd_line_complete_v1','erp.bd_delivery_line_price_unknown_v1','erp.bd_post_invoice_v1','erp.bd_set_charge_price_v1','erp.period_blockers_v1','erp.prepare_rework_component_line','erp.run_v263c_bs_rework_integrity_checks','erp.get_hpp_completeness','erp.resolve_rework_accessory_bom_v1','erp.save_initial_import_action_v1','erp.bb_check_sales_import_row_v1','erp.bb_apply_sales_imports_v1','erp.bc_check_import_row_v1','erp.bc_apply_imports_v1','erp.be_check_pocket_import_v1','erp.be_apply_pocket_imports_v1','erp.bb_check_rework_import_row_v1','erp.material_purchase_final_ap_total','erp._cp6_supplier_cent_state','erp.post_supplier_payment','erp.get_product_conversion_workspace_v1','erp.bf_version_at_v1','erp.bf_guard_economic_v1','erp.bf_legacy_basis_v1','erp.bf_save_groups_v1','erp.bf_guard_new_member_v1','erp.bf_validate_rates_v1','erp.bf_work_rate_v1','erp.bf_context_rate_v1','erp.bf_bom_for_lot_v1','erp.bf_recipe_basis_v1','erp.bf_bind_wave_v1','erp.bf_work_capacity_v1','erp.bf_snapshot_sku_v1','erp.bf_wave_revision_v1','erp.bf_group_sku_v1','erp.bf_ensure_work_v1','erp.bf_snapshot_matches_v1','erp.bf_assert_work_scope_v1','erp.bf_delivery_invoiced_v1','erp.bf_laundry_rate_v1','erp.bf_merge_charges_v1','erp.bf_package_charges_v1','erp.bf_complete_shares_v1','erp.bf_component_charge_v1','public.erp_get_laundry_history_v1','erp.bf_supplier_credit_delta_v1','erp.bf_supplier_credit_source_v1','erp.bf_supplier_credit_revision_v1','erp.bf_supplier_credit_guard_v1','public.erp_get_supplier_credit_v1','erp.bf_supplier_credit_allocate_v1','public.erp_save_supplier_credit_v1','erp.bf_commercial_sku_at_v1','erp.bf_resolve_import_product_v1','erp.save_sku_action_v1','erp.get_sku_workspace_v1','erp.get_sku_hpp_v1','public.erp_save_sku_action_v1','public.erp_get_sku_workspace_v1','public.erp_get_sku_hpp_v1'])));

insert into erp.schema_migrations(version,description) values('v2.6.20bf','Commercial SKU ranges with physical-size lineage, optional vendor laundry details and same-supplier return credit allocation');
do $catalog_guard$
declare actual jsonb;fingerprint text;object_count bigint;
begin
 select * into actual from (
with relations as (
 select c.*,n.nspname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname in('erp','public') and c.relkind in('r','p','v','m','S','c','f')
 and c.relname not in('cp6_v2620ao_rollback_capsule','cp6_v2620ap_rollback_capsule','cp6_v2620aq_rollback_capsule','cp6_v2620ar_rollback_capsule','cp6_v2620as_rollback_capsule','cp6_v2620at_rollback_capsule','cp6_v2620au_rollback_capsule','cp6_v2620av_rollback_capsule','cp6_v2620aw_rollback_capsule','cp6_v2620ax_rollback_capsule','cp6_v2620ay_rollback_capsule','cp6_v2620az_rollback_capsule','cp6_v2620ba_rollback_capsule','cp6_v2620bb_rollback_capsule','cp6_v2620bc_rollback_capsule','cp6_v2620bd_rollback_capsule','cp6_v2620be_rollback_capsule','cp6_v2620bf_rollback_capsule')
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
 if object_count<>9292 or fingerprint is distinct from 'ea5ef2829f732c7302c8e17e168a2679a539c2afa48cc78fb316fb019bb03234' then
  raise exception 'BF_INSTALLED_CATALOG_DRIFT';
 end if;
end $catalog_guard$;
update erp.cp6_v2620bf_rollback_capsule set installed_definition_sha256=encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex');
do $after_data$ declare v_table text;v_hash jsonb;v_after jsonb;v_before jsonb;v_cmp jsonb;v_cols text[];v_nonnull bigint; begin
 v_after:='{}'::jsonb;
 for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array['schema_migrations','cp6_v2620bf_rollback_capsule']::text[]) order by 1 loop
  execute format($data$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')) from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s$data$,v_table) into v_hash;
  v_after:=v_after||jsonb_build_object(v_table,v_hash);
 end loop;
 select snapshot->'before' into v_before from pg_temp.cp6_release_boundary;
 v_cmp:=v_after;
 for v_table,v_cols in select key,array(select jsonb_array_elements_text(value)) from jsonb_each('{"bd_laundry_charge_lines_v1":["bf_sku_version_id"],"po_work_component_snapshots":["bf_sku_version_id"],"rework_component_lines":["bf_sku_version_id"]}'::jsonb) loop
  execute format($strip$select jsonb_build_object('count',count(*),'sha256',encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex')),
   count(*) filter(where n) from(select encode(extensions.digest(convert_to((to_jsonb(t)-%L::text[])::text,'UTF8'),'sha256'),'hex') h,
   jsonb_strip_nulls(to_jsonb(t))?|%L::text[] n from erp.%I t)s$strip$,v_cols,v_cols,v_table) into v_hash,v_nonnull;
  if v_nonnull<>0 then raise exception 'BF_ADDED_COLUMNS_NOT_EMPTY: %',v_table;end if;
  v_cmp:=v_cmp||jsonb_build_object(v_table,v_hash);
 end loop;
 if (v_cmp-array['bf_rollback_v1','bf_skus_v1','bf_sku_versions_v1','bf_sku_members_v1','bf_wave_skus_v1','bf_po_boms_v1','bf_requests_v1','bf_context_v1','bf_laundry_delivery_sources_v1','bf_supplier_credit_moves_v1']::text[]) is distinct from v_before or exists(select 1 from unnest(array['bf_skus_v1','bf_sku_versions_v1','bf_sku_members_v1','bf_wave_skus_v1','bf_po_boms_v1','bf_requests_v1','bf_context_v1','bf_laundry_delivery_sources_v1','bf_supplier_credit_moves_v1']::text[]) t where (v_after->t->>'count') is distinct from '0')
  then raise exception 'BF_INSTALL_CHANGED_DATA';end if;
 if (v_after->'bf_rollback_v1'->>'count') is distinct from '1' then raise exception 'BF_SEED_CHANGED: bf_rollback_v1';end if;
 if exists(select 1 from erp.bf_rollback_v1 where not(payload ?& array['functions','installed','snapshot_constraint','rework_constraint']) or jsonb_typeof(payload->'functions') is distinct from 'object' or jsonb_typeof(payload->'installed') is distinct from 'object') then raise exception 'BF_SEED_NOT_PENDING';end if;
 if exists(with live as (select p.oid::regprocedure::text as identity,encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') as definition_sha256,
  array(select a::text from unnest(p.proacl)a order by a::text) as acl,pg_get_userbyid(p.proowner) as owner
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public') and p.prokind in('f','p')) select 1 from pg_temp.cp6_release_functions f left join live x on x.identity=f.identity
  where f.identity<>all(coalesce((select array_agg(object_regidentity) from erp.cp6_v2620bf_rollback_capsule),'{}'))
  and (x.identity is null or (x.definition_sha256,x.acl,x.owner) is distinct from (f.definition_sha256,f.acl,f.owner)))
  then raise exception 'BF_CAPSULE_INCOMPLETE';end if;
 update erp.cp6_v2620bf_rollback_capsule set boundary_snapshot=(select snapshot from pg_temp.cp6_release_boundary)||jsonb_build_object('after',v_after);
end $after_data$;
do $capsule_guard$
declare expected jsonb;actual jsonb;boundary jsonb;
begin
 if not exists(select 1 from pg_class where oid='erp.cp6_v2620bf_rollback_capsule'::regclass and relrowsecurity and not relforcerowsecurity and pg_get_userbyid(relowner)='postgres')
   or exists(select 1 from pg_class p cross join lateral aclexplode(coalesce(p.relacl,acldefault('r',p.relowner)))a where p.oid='erp.cp6_v2620bf_rollback_capsule'::regclass and a.grantee<>p.relowner)
   or exists(select 1 from pg_attribute p cross join lateral aclexplode(p.attacl)a where p.attrelid='erp.cp6_v2620bf_rollback_capsule'::regclass and a.grantee<>'postgres'::regrole)
   or exists(select 1 from pg_policy where polrelid='erp.cp6_v2620bf_rollback_capsule'::regclass)
   or exists(select 1 from pg_trigger where tgrelid='erp.cp6_v2620bf_rollback_capsule'::regclass and not tgisinternal)
   or (select count(*) from erp.cp6_v2620bf_rollback_capsule)<>33 then raise exception 'BF_CAPSULE_SECURITY_OR_COUNT';end if;
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620an_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620an_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620an_rollback_capsule'::regclass)) into expected;
 select jsonb_build_object(
   'relation',(select jsonb_build_array(relkind,relpersistence,relreplident,relispartition,reloptions) from pg_class where oid='erp.cp6_v2620bf_rollback_capsule'::regclass),
   'columns',(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)) order by a.attnum) from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='erp.cp6_v2620bf_rollback_capsule'::regclass and a.attnum>0 and not a.attisdropped),
   'constraints',(select jsonb_agg(jsonb_build_array(contype,pg_get_constraintdef(oid),condeferrable,condeferred,convalidated) order by contype,pg_get_constraintdef(oid)) from pg_constraint where conrelid='erp.cp6_v2620bf_rollback_capsule'::regclass),
   'indexes',(select jsonb_agg(jsonb_build_array(indisunique,indisprimary,indisexclusion,indisvalid,indisready,indkey::text,indclass::text,indoption::text,pg_get_expr(indexprs,indrelid),pg_get_expr(indpred,indrelid)) order by indkey::text) from pg_index where indrelid='erp.cp6_v2620bf_rollback_capsule'::regclass)) into actual;
 if actual is distinct from expected then raise exception 'BF_CAPSULE_SHAPE_DRIFT';end if;
 select boundary_snapshot into boundary from erp.cp6_v2620bf_rollback_capsule limit 1;
 if 33>0 and (boundary is null or exists(select 1 from erp.cp6_v2620bf_rollback_capsule where boundary_snapshot is distinct from boundary)
  or not(boundary ?& array['before','after','platform_before','markers_before'])) then raise exception 'BF_CAPSULE_BOUNDARY';end if;
 if exists(select 1 from erp.cp6_v2620bf_rollback_capsule where object_regidentity<>all(array['erp.commit_accessory_bom_for_lot(uuid)','erp.ensure_po_work_component_snapshots(uuid,timestamp with time zone)','erp.validate_work_completion()','erp.guard_work_completion_posting_consistency()','erp.seed_bs_case_component_baseline()','erp.classify_bs_case_v2(uuid,jsonb,uuid,bigint)','erp.cp6_lot_work_cost_v2620c(uuid,text)','erp.assert_new_stock_cutoff_coverage_v1()','erp.bd_priced_line_json_v1(uuid)','erp.bd_compute_pricing_v1(jsonb,jsonb)','erp.bd_attach_delivery_pricing_v1(uuid)','erp.bd_refresh_size_estimates_v1(uuid)','erp.bd_line_complete_v1(uuid)','erp.bd_delivery_line_price_unknown_v1(uuid)','erp.bd_post_invoice_v1(jsonb,uuid)','erp.bd_set_charge_price_v1(jsonb,uuid)','erp.period_blockers_v1(date,date)','erp.prepare_rework_component_line()','erp.run_v263c_bs_rework_integrity_checks()','erp.get_hpp_completeness(uuid)','erp.resolve_rework_accessory_bom_v1(uuid,timestamp with time zone)','erp.save_initial_import_action_v1(text,jsonb,uuid)','erp.bb_check_sales_import_row_v1(uuid,uuid)','erp.bb_apply_sales_imports_v1(uuid)','erp.bc_check_import_row_v1(uuid,uuid)','erp.bc_apply_imports_v1(uuid)','erp.be_check_pocket_import_v1(uuid,uuid)','erp.be_apply_pocket_imports_v1(uuid)','erp.bb_check_rework_import_row_v1(uuid,uuid)','erp.material_purchase_final_ap_total(uuid)','erp._cp6_supplier_cent_state(uuid[])','erp.post_supplier_payment(uuid)','erp.get_product_conversion_workspace_v1(jsonb)']::text[])
   or definition_sha256 is distinct from encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex')
   or installed_definition_sha256 is null or installed_definition_sha256=definition_sha256
   or installed_definition_sha256 is distinct from encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex'))
  then raise exception 'BF_CAPSULE_SOURCE_DRIFT';end if;
end $capsule_guard$;
commit;
