-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20ac -> exact AB.
-- Execute only through the AC maintenance boundary before production use.
begin;
set local lock_timeout='10s';
set local statement_timeout='360s';
set local timezone='UTC';
set local search_path='pg_catalog';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;

do $platform_guard_v2620ac$
begin
  if (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20ac_cp6_temporal_surface_closure')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260915031500' and name='erp_v2_6_20ac_cp6_temporal_surface_closure'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('9645ae6a2f80c364b3c51ef34747f6dbe313f661a3d2f9fd0b696026832b5555','7d2b7fded027a41113a07a7dcb718672e446e2062862b9be0377ebcb1d522131'))
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260915031500') then
    raise exception 'AC_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR';
  end if;
end
$platform_guard_v2620ac$;

do $lock_all_erp_v2620ac$
declare v_table text;
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='erp' and c.relkind in('r','p') order by c.relname
  loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620ac$;


create temporary table cp6_ac_expected_functions(
  identity text primary key,before_sha256 text not null,after_sha256 text not null,
  owner_name text not null,acl text[]
) on commit drop;
insert into pg_temp.cp6_ac_expected_functions values
  ('erp._cp6_apply_supplier_cent_event(text,uuid,date,text,jsonb,boolean)','390fc3fae9bf59cf35fbc699f988521b3bde572e266937fdce99e0854c1756a3','90a46f75b77fd3ef6a7cf58de0b78aa2a2874a95862702d16762c0d6a6eda4d2','postgres',array['postgres=X/postgres']::text[]),
  ('erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)','355246b52dc88e5d91643485fe796f24e7975d0629824c5b28c31074469ed7ba','4b7dfd039b49e56082d0dd0a63613cfdaf7483af244627109dd1c2ed230e9804','postgres',array['postgres=X/postgres']::text[]),
  ('erp._idempotency_complete(text,uuid,jsonb)','81c73acbc3ab89ab8c0eafc0f3225307279f097acdb7ea7a00c3d7bb1bd35609','85e6228fd91c844b6f81eafe975353f7ffd8185032eb59bdabdab4156c1827a4','postgres',array['postgres=X/postgres']::text[]),
  ('erp._post_cutting_qty_correction(uuid,text,text,text,jsonb,timestamp with time zone,uuid)','c5cf72c4dc2c2c2ece44d7e2a0686b1ad167677882952ab611f24f11f40f6710','efd9b69154bcadeb189cfbf0102a0fb6ab6a7947b5389fcb91f481cab1f70849','postgres',array['postgres=X/postgres']::text[]),
  ('erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','c1f74ab9e855bf354d62f0e9053883c7cc0efdfeb329de8f2e081e46852f50b6','50e9edac8803dea3ca8d39fc78b77fd1c4c5499820b37dbb390b13b32c233c92','postgres',array['postgres=X/postgres']::text[]),
  ('erp._validate_migration_batch_base(uuid)','639aa6094f5a662f144b899a4831e82e85d3da888e4a4ceb5f0c22c52347bdc7','78f165c0b42edec0cfa8e3fa295abb64b94cde0df9af9b5611b5f6e4ec3e1fb6','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.accessory_uom_factor(uuid,text,timestamp with time zone)','42ce324b31a71a768224d5d7e913af4589f00986be9f632e1e3147cb22aa771b','c348b5e771c0d73bf335a65d26ecc5c7b12d58923669d091332cca5b98dc38f9','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.apply_cutting_correction_and_post_laundry(uuid,uuid,text,text,text,jsonb,timestamp with time zone)','d8cbbfe79b6d74c85de758939b45ad9a2781ff86b8419ded573d772da3d178d4','dbf2e043e4113764c8eeaa3047eb0543931761be52e035510ea3d99ae9345f6d','postgres',array['postgres=X/postgres']::text[]),
  ('erp.apply_migration_master_rows(uuid)','eefd84e59645097d82903576181870a33f5e6d8a6792332f3b879cdf2dc17fd5','6fd720835a487197a9b0d4b6246d9669ba5f472c7135993ab64cd5d9970eb1c9','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.apply_migration_open_pos(uuid)','dfe8d1cec79be202cd79d3fbcf6a206ba4af2a3e2dfa5f9ed95b7e726ca15a3d','49dd168a2dc3df0be6fcec9c962446d91e5724f9a838dc9616d894717c9844f7','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.approve_payroll(uuid)','f18ff72724bcf6f738d8fe0131a69a6ba756d16c02094cb2460c11d79400f636','f8b4f9138f846c5dd045564cf5a1a96783cd7bfb26edac01e4135bc6b94bd7e0','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.assign_cutting_group_to_batch(uuid,uuid)','ba1640235ad1a19fb8c4e1b5772f8bf39e2817d74fccf6c9510d58dbcf50e2c2','232a030a9894bf4ea3c9e198866f84d7dbbb06d5c160ce17107ba216ee0b2a03','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.cancel_product_identity_successor(uuid,text)','a6ec43dcdfc8afe1643b9ee4fb61dbd9195a07284381def5ff12c8997815528a','1009952108f1d312cfa7d7999ec2e3b2c340716f33a8b0c1f86821e7020965e1','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.cancel_unpaid_payroll(uuid,text)','46f850ae3851ed6bafe72422d1a88b7413bff0a982a29b27df6fb422516a8ecd','826ea6388f9346a990bbfa2946688ccd5850fd951aeea7455b02615d1825898f','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.classify_bs_case_v2(uuid,jsonb,uuid,bigint)','9300b0f8139a8a0acfd2d51bcc04bb93d06d096b8f9fe5e0555f10f9082f2757','adc44365f579f70088f6849bd22010c2e0c69d76c818d72bc2dbb718ccdb6735','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.close_accounting_through(date,text)','7f20b0a381b049391fc3e33dce00b3b8c517b0b77ae8f2b2756cac5e0a021b42','97bf7196f1a78c7c12a15b5df6ea5aaae126e593bfb6e3206491ac2468529d76','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.create_manual_bs_case_v2(jsonb,uuid)','811da6578062ed539301cc924410d69ec8f6203583115e4371ba59e9f0adcc03','8d905e876d9ffd084412dda5840c666fc9637185605e18eaa298897cd631160c','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.edit_product_identity_effective(uuid,text,uuid,uuid,text,uuid,text,timestamp with time zone,text)','08dc802ba885f33e90b0b15295faf6dec5559bf6e94a30046e0a45f9d8ac2257','5eb8fa558cb4f7a605638da57efa42729bb487c22b0d76bdb7b5b361ab9ec8dd','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.ensure_po_work_component_snapshots(uuid,timestamp with time zone)','71534382c03d65944bd470f1cd651f1b758293ef220e8db02ac684028df4dcd4','b615c3877659057637dfe02e6ea66c7185c712560edcb968c822d92b915e6b77','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.finalize_migration_batch(uuid)','ca3e2cde078274c5002403cbc134f9275deb492cb933467f245236f18da6f9d7','b2ca642c739fda50ffe2e5fb7d165e9a3370bcc55fad2e256c358d403f1436e3','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.finish_production_order(uuid)','da17dbfb6353616cc07c3020f18c8847e36d4850c2815c275bb02d731ad11c07','2020ad81ed28a4811b30155a79047b2e6dd70821cc0bc800d0e0a51c5de3a7f9','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.get_accessory_economics(date,date)','4ef19411e9b645efc9c0a48bdc9e5c3bf65b56deb64ad232cb8c35aa68e8d87c','9b1a64cdaf736c904e675a729ee7cb0e171cc731ef1289db19d13b50f63f177b','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.get_owner_financial_snapshot_v2(date,date,date)','0afb94d932b1c7488c1a787de7f734133c1674e0a43100d366c6f3f129ffb9bb','053c092f1818eb6018ec0af8d21fe39a824faa6d5a812d619ad01f4217e7ccca','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.guard_cutting_batch_parent_change()','fb3195c0aa04ad005535848bdfc6c0881a6d3610bee700dca107a91a7f079aa2','b6df1d451fb2bd5ba8bb5e4ab9a2a24d2637fe401d6bdff82af26b0e29b73d43','postgres',array['postgres=X/postgres']::text[]),
  ('erp.guard_material_cost_correction_post_date()','f08fd0917626ab8d18667d653e16b58216b31749f3b4087ed418fceb3f9d3fa5','cde9ea6c56dd35df5bde43d82bb897e377840d09838be73105bc26c97151700e','postgres',array['postgres=X/postgres']::text[]),
  ('erp.guard_opening_balance_post_date()','3af2d47e1f676b1b295c3151a038bfb829f6ae9ce8dd914121dc91b756ca8335','3f7a0875954ad433264e574c2738e68b2f7b152d88a610ed0dda7a34930b69ac','postgres',array['postgres=X/postgres']::text[]),
  ('erp.guard_opening_hpp_correction_effective_date()','b3cfd8a75b7b2a5cb26f1c7e54c45539a6437bde166f59ebee3ac622541a3d9e','a52b294f2c279b38a6a3884fcacb5f923abd24f1d3314ffbbe5085807178ef2d','postgres',array['postgres=X/postgres']::text[]),
  ('erp.guard_vendor_invoice_post_date()','f609b43958ac45790e5a4bee19ee993cffc9c986ae7d681d28866a632ba7fb4c','a3a42799abafcc13726006d18a2c3893592a8de7e769e2289a496fbf3a07a93e','postgres',array['postgres=X/postgres']::text[]),
  ('erp.merge_eligible_work_into_payroll_v2(uuid,jsonb,uuid,bigint)','c69953696b2174e61df15e9f67ef32dc01bb67151f5def9d0d274c25d723891b','47cddbfe7a4c6584441acb222480e9287c9c92290248aa1f0f3fc19a15142dba','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.populate_payroll_draft(uuid)','5664823fdf184537ef4a000e58122bef0285be9e2d7a242f477e7c5f21b27368','cffab09cbfec17a566fb8e9a0b9b1f97bc16f4357f4452f96bce967964062a63','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_accessory_reimbursement_accrual(uuid)','b7007b635d0392c1d5ccbe2586e43229cfa0512fb58b7fd02775c3ce1b7cfbef','b10b63a72b2915cc5a6d1f3331fcbb4fe072c121112df31bbad8306856fcdacc','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_contractor_material_issue(uuid)','9e67dd30115e4edcc194ba2e8df86426b74005492ac141b7116bcb00c11d6052','752dc5b3cfc9b65876ad1b36f1f4c9607b1cfe7088e1ff9704efaeaa2132567a','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_cutting_material_issue(uuid,uuid)','a7e13c0a4cf789489118b2b2f379cf774206390f0eab70dde497c74cd1af53c4','6e96d26fea60841dc8986b7c38df82bfc687d854a27bc2ace9a972614a43a7fb','postgres',array['postgres=X/postgres']::text[]),
  ('erp.post_cutting_material_returns(uuid,uuid)','5da00c803af1a9354715c2e341ff348f226bf7892f86920489c9a413b5b810ee','017f6fd4ab55bea496382f4049d5e6a2ac1821bd8cdec5bf1cc3ef361c9ff990','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_cutting_qty_correction(uuid,text,text,text,jsonb,timestamp with time zone)','8cc72f77ce23007d43b299ec1df73e350ecc65c6617469f32f205147e3089e0b','0ce1a721f07144f5643821b7e18c8599fbbb6aa5a450ec2ed425e58e20abe4fe','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_fg_adjustment(uuid)','710778d554493ca1acb91f5878fcf8b12998020a62c67f87dcf8106bb08cdc19','f346ced6ddebd945a1e47a57c849cf4c60d34c5b66dd94cb2c92fef9744663a0','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_fg_movement(uuid,uuid,uuid,text,text,integer,numeric,uuid,text,uuid,timestamp with time zone,text,boolean)','d816692ac53d2da230a1901a779cc9364a9f59baae2516597646df47c90955c7','45bd832ce8fe92c3bacdd3a15b0adc97375abae795d3a05bdf20a10feed51480','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_fg_partial_completion_v2_legacy_v2610(jsonb,uuid,bigint)','0c0fff724542df09aad962edda77592fa1ca782a4c5b16fb1ee53f819f677963','1f7e1ef3b98d9c67930d24bc0b4872b1252b5d6d67c669b8d88e4de05810a19b','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_journal(text,uuid,date,text,jsonb)','0a84003a5e6a27cc445e835673d4f5030cbc19cb6b130037eaed922340d34d77','1f4b630c00147f88d195b3b365114eaecc60fdf3141859c384056423ae39f824','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_laundry_delivery(uuid)','2904cb57dee100fb9f45c4ddc4dfc61a1d45955c42d524ada4bf0b5d065dce99','a06ac2e457ffe36272a987d1c5de3673232d1eafe09480358c0fc1bae5bc31c7','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_laundry_receipt(uuid)','aaa95ae3a7fa4c34f7e98ccd3fd9ed4b10f6204af4b454df0da106a0cded9f4f','37118318d08c41cda8c0e1eeaa55130c95ad7a6db0ed8c29ef58da4f2e65234c','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_material_supplier_invoice(uuid)','727382a2c3b8464526bb5a8a66c68813be439fb931ca94d993898fecc1e41faf','5b455191508e0945c388f804e189055a435b8a56faab9213a01e812420784c0a','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_material_supplier_return(uuid)','541ce87729dd47bffd536847e71271c1e0b968d199e2fe24fd671a025cee027a','a19b971655bcfa7762a9d05235d9e35456833e2794ef9c67cf633f017a7f60f7','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_opening_financial_correction(uuid,numeric,text,date)','95ad1f5db523bdc19d7b21d1f1b9e1baa49a499fb791f937fe43b0291d4bd7f1','3db2afef9444d657f236a685b6f2a81eeb9e4ba99a61d9300b1b580848722c4f','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.post_opening_hpp_correction(uuid,numeric,text,date)','0fcce7b463ca220a1d565f5d6eac56d75531e1a071f42d4c11d9852642673399','ff60a0fb897707194a64867779bc84cfa5c208434908a2edee40b0cf8d6c02a5','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.post_opening_hpp_correction_from_price_percent(uuid,numeric,text,date)','fa240700a96fc5af05cf1f78a5c5d597dfc491396720ec7897485e71f9dcd6f0','473394e2cd92e63340af1def3e64232e02c6ef4d0d48b2a2a86e74b978ef75e9','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_opening_subledger_settlement(uuid)','b709ed64c78b09c113e6e0541eb757b5367dfbf7dd51752a26827207fc12e97e','2b9b0ca7dc3af6dee6327ccce58cf3255c4900f49b6c21a0b4e037493cad0d9b','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.post_payroll_payment(uuid)','1875c9d29757f63fcbf9e635f0f87970bd54d8ff73112ef4b30def7383e72f61','6e81a5296b8b636fe33aa5a17bb5a2f4ee60a2d7698d92131c9616f1381f9a55','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_product_conversion(uuid)','2f38beab669cb2dc3a1eb7a88dc6b04506234f85d79caff70331f97d09a93b90','98a2ff7add6f4b1be232168c5d3bc6804b79a5755c6354ae1777321d934586ca','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_qc(uuid)','9ecafb4c29a93c3415e35dd638673ac574e5db5a2e4e98fa22387052c6bcda45','637c1c90b22a0bd4812d01e55f64b9611b2cae1ea9979389f3997c131370cd4b','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_rework_completion(uuid)','4618b75e2fd239df3dec798b1814700cf4855577100753548158c891a4363f92','209338cc2b3099b163c0b344d1706a1f42dbdf804307e5fadee08e02f966f34d','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_sale(uuid)','5b6372d1e0ac6e3ed841dd3d1e13506af4297974aa8c7847c093e85c2181a5e0','f485761060593d1b9fac5b5ecf7556007a7907467ad5ccd90be057ec9e9823f4','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_sales_payment(uuid)','605db7b1ce7bea6b54e70625092f8e98365d3966dc09d220be7dff81014a1f1d','1f52492ffe261a903e31acf654c5fa1b3fe6e8b37268943c5b869f1a7c626447','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_sales_return(uuid)','d959c5e095cce32540b9f2a4310857520b4eec70c5200465f16d74cccfb45a46','7640b5781a8838f550595d47bbc3f452a50a846f58018e714a0a209b8f32ff02','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.post_vendor_invoice(uuid)','41f6cb2d24b0a137b819c799561ae61983bd01cb3db076e3d1f4339da4569196','6ea8c54f5fbf2b43c0c565f034fdd1b5473309de955a7a495282b82b32063ed7','postgres',array['postgres=X/postgres']::text[]),
  ('erp.post_work_completion(uuid)','50d83217e67233b6ea8f67b9ee3e9c40e3735921437d67e552222b73c4e1d219','34fbc926472f02a716149208731a9dd953d9e9fc1417e0d0a8fc1ad8e80ff913','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.prepare_migration_opening_balance(uuid,text)','723e4c3a0288a35d5df3c63ebd4f3f6b60973aaabe2b7a1f52a030a14c1b6e2e','89f419571e5de43434008e5090b1d4808089411ba839a53172354a145ec97323','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.process_cost_recalc_queue(integer)','7fe85b6739fa5684171cffd26d028eabd35efe3bb2691e2daa9e52cf40892a13','743bcf5406e34b487e558bd583d888ef07b1be49fac25f8b6bb03637208fe9be','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.refresh_accessory_hpp_after_material_recost(uuid,text)','217d96e52ed92ad6bb37afe3227007724f87607646335b292a45bdb64f3c4b37','4b3457519ad7fab4379f8e75abd048a15f9883cefac90d284bfd2d7fa361473e','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.reopen_accounting_through(date,text)','bc7bcc0b69c547dcf8d4049c7b1cf46e59c6887e7a672a043257b2c8d582e634','cba02940aceb945f448e144e003c1fc31bc365b93e261a64e8c296d9e6ac9725','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.reopen_production_order(uuid,text)','88cc0118544535795149ba8a5c3fce3bd0398802ff32fe0441331c92d7f000e7','ca1454c37faa2321952bcf3aa807351958e75bea403b6d3cae0a2685786391d0','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.replace_material_purchase(uuid,uuid,text)','677faf9208ad1f7bff90df4ceccb4bf644fc08f881a6073382cb65f6459303b8','74e651816f4795a0e7f60f05b2921a59e4fee17f926841603a0508f857473914','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.resolve_laundry_claim(uuid,text,text)','20eba16640912f04220437c21df018a6799dc48b06d8147abfbd2454e2d60425','81d84ccedf769a441894ddde8192e38bd7be54490dfa0ae02857c61a8ea685e1','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.reverse_contractor_material_issue(uuid,text)','ed838f21f8649b9e77c5aa1e0ba60b71e6951d0ff5c35f251b4cd1173c7ff399','f4e92bdc7f40a4d880b83069c9b559088470449a6f32e501c90b306f92d79e70','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.reverse_cutting_material_flow_before_sewing_v2(uuid,text,uuid,bigint)','248d85ed88acc8b66c4d776b28044bea76f4a4fd8641ca03de499444385fadb2','540552a2e0180a2ede3d05c302cfb8409a4f2ccf52381e7a0ca254bd798933c3','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.reverse_cutting_qty_correction(uuid,text)','4fdf03ca12ef34f1e6f11f4afdcf2afe771bba8e9c247793788ec8c716cb16f9','1195690e7eaba6d16756aa5a6ef1c41bacfdd3086b0e3c6c726ec40a4021f167','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.reverse_fg_adjustment(uuid,text)','2591b1f0b9cdf6a0a36629bb183386bf0e7433d585520687aec6e2be6853b8a4','f55a478eb2376141a20600b37e7bc79a6bdcf19fbe8c20fe36f9a8f7437d7729','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.reverse_laundry_claim_resolution(uuid,text)','f5e94452f4c187e7d6a4480a991e3803bba5d4c09ec6082b0981b37fe1f180b1','ffd803e1438f873efe9356f9de6fb4f38a63143dc293c92f5cd7c442093386b3','postgres',array['postgres=X/postgres']::text[]),
  ('erp.reverse_laundry_delivery(uuid,text)','ea2b08a506c4c59dfb48cfc782d6fa446bd098672819779d8b7cc260c6b99beb','a337c617885162ca1a6d7c5b04a342ceafc2effe9422e96e025f22331bc538af','postgres',array['postgres=X/postgres']::text[]),
  ('erp.reverse_laundry_receipt(uuid,text)','3d06b3dce8df8f53aa5440b7b3a1c54d793eaee80e5bc6fe92a62babffa7c712','55f1fd626aa34f4792b182c3b75661262e7b3d1470571552d432654d12497bf5','postgres',array['postgres=X/postgres']::text[]),
  ('erp.reverse_material_adjustment(uuid,text)','c90fd34d4045a060ae4d36413d6520068281066d0de52dc766583c5f6e7d7288','b744243ddca1914a386663a780efe688c82f2d87db556a417b61f477b4246ef8','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.reverse_material_purchase(uuid,text)','5ed3d75116f42f558829e1707f58c28fd1c81a2c66004ae54cf52069b147d4e1','debd64397448f14fe5be3570337d874a6bb4fd6cb0a106b1de270a6c30e758ca','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.reverse_material_supplier_return(uuid,text)','5659d9755c81ae4134a494d1ebd0aaaec29ed82b75a5a32bdfd6d048e6ebaca3','f7e130a2dfe2c249905cbfdf5515da1a5fc0730d0ec282d7da2575706d219df3','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.reverse_misc_finance(uuid,text)','5a1174b7574b521e9d003200e51dda889f5a2684ced2d5fd3bde1612f4302de9','6f3e723329c544a4ee2bcc36eac0a51a869c2bab483287426913ac188705e5c4','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.reverse_opening_financial_correction(uuid,text)','1ce99785ee8dc682b1b0f2aa9171f2110614baf4c9a99ecf4880b547496947fe','e1ad8a4e6b88ae0d109590234332236399967c5339922034ea3f415796ebe451','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.reverse_opening_hpp_correction(uuid,text)','9ea3965ec90c5f070b81ab6384a95ad573984d3a56dd01a242d31077905ca230','00fe4c4d12eb4645e4672583b684b7beb0d1b0e3fc84ce51adc45d0cf7d6a293','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.reverse_opening_subledger_settlement(uuid,text)','c01292aebb98ea09d0fb440215f9c4cdbd9ece3b98caa641b9b308faec542e1a','3470bfe69619912700f05438a2bcf387145ba7ce886fed4476e2312b1510cfee','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.reverse_paid_payroll(uuid,text)','90db5a8f5bc1b99a50a81530a7c21bef112a8ab151a1a5835a8ae722acb28d74','083ba4a193c125fb51e08e5639c1d4783b73f6a92d426b5e7aadd61429aea149','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.reverse_product_conversion(uuid,text)','4ebca88a5b379e80fe90e363e20e5fe97aafa6ce5d98956067e0a72058f09927','d3e63243bb155569f70c41033590a6298365e023d23e514e472abfd2d5b29d75','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.reverse_qc(uuid,text)','e1df604c895960e18e9df1fefea2ff98fe231cbce72296d38cab2f9068862fa2','a9b4be777025b38543b4f2a1524bb5749212d73e7773c889f137896aa884758f','postgres',array['postgres=X/postgres']::text[]),
  ('erp.reverse_rework_completion(uuid,text)','ee081e90a1a37d16e9e4dba290c93a160a934282e844fdc6c4972c1e5752607c','97de5d819004746448a544b30dcbfbf06a6681e715c9d7836974dc0ddfc5612d','postgres',array['postgres=X/postgres']::text[]),
  ('erp.reverse_sale(uuid,text)','f9bade2d172a4abefe6973fb3dc333f6f70705b1b5ba1da52d464e3f45f64726','e098db067174cb390c09c3bd5f16fbdbcbe146199d360443dffb447ba5872570','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.reverse_sales_return(uuid,text)','e7155962a8aa0f0e72f16644ffdf3563d3a11658b73c5185e94d6023090ec3cb','97be8af3d2d0b57f3c720c3ee1a1ccbf47d43be813d01c63bb4742a7eb2b623f','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.reverse_vendor_invoice(uuid,text)','8564620ed9eae2d9ee6124e96c04d2e938c370c9f3b70646da07d56470477a11','994313b784518f325cdabf14f2cea6efab9d80bd67b1fa23d2d17987edec1d83','postgres',array['postgres=X/postgres']::text[]),
  ('erp.reverse_work_completion(uuid,text)','2c04be82b2464ac2badf7c083cd1feef63cf1f4b1afb0c55f0f73a9d3c6935db','ddd39a44558d865791e43c0087c49ed4cb34e2dab9b42aadf77ce00ffd1f04c7','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.run_integrity_checks()','eaee7912a68dc4ac7be539fc0b4a51dd70f01eaed1591f5f86b00056d11ab655','901c964856838631826065300a7d585ecba8e39f7010a036b78a8b4b088d15f8','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.run_v256_integrity_checks()','341431c558816b52d295818020fff61c464899251f13ae7b9574a25caa1367b6','ed8cc408263acf733d50396593cb26f8e3f63e964a059986cb30df30db19a8e3','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.run_v257_integrity_checks()','d5198d78f5928e84ab3d8eacf6b8afa063ec53af2f6d10e361d0d5d10d2f2b27','4739f37011a64f3aceb949de2374fb249ea6d05347f9dcf35f145f721e956608','postgres',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
  ('erp.run_v262_integrity_checks()','a42cafb903d475823e8821837eb3c090b0c349a0f7844010be5a51dca88887b5','a474885334c8616cc6381590ca2b89e23f9060b6bece1012a46b98c435482157','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.save_accessory_bom_edit(uuid,jsonb,timestamp with time zone,text)','04a0073be18afd32ebab45620181406674faed2ea604e313a726c99ea11f4c2d','89a783b57604c6097cbb3d8e4ac64460ceeab3f986beb3be537a377fcd68a8e3','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.save_accessory_category_v2(jsonb,uuid,bigint)','0e16731d4381a1731faa69979970c7938b3af0a923af5843dd7443dbfcc7f9b4','b15cd280afad64da1be23757b92c0286f048b69ee0c717e3f2513255500c4e7b','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.save_accessory_material_v2(jsonb,uuid,bigint)','e476e3e48eb128f47896cdd3cd0d5a7d03d52eade7515933c7ea9ac9ad0b0161','bc6b5d7854fb50cc5a7179aae42290a598bfef20fe5924f06b0e895b850cfb7f','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.save_cutting_batch_v2(jsonb,uuid,bigint)','a6e43795b227c1ff7e53662b1cf8e562f47fbbe8eb2198cf8cc69fd3bdc7eb1a','ef22b278c2d9f3bcfbc62f6df2bc063d4b581f89be3704513280a48e8a09eff0','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.save_fabric_master_v2(jsonb,uuid,bigint)','d84d2308c6b6a3a2f0e92dd1efa8ff02ef6db93f3065d2f1e97d4d780069d122','c7488bf883a799be66e44e9c831f5fc6f69bf9ba9b76b29f23680fc88b6b7601','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.save_laundry_claim_v2(jsonb,uuid,bigint)','d12440e1305c0a1cf4cbb10127dfa67905cc897ae20988bc233a674fe3b49b93','6c92d7a8c52fda208d82440d3dc018b4c042cbd17e8294cdb9290046087c4936','postgres',array['postgres=X/postgres']::text[]),
  ('erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)','7bdb2eaa71a9475271e422e38cb52b4965ecef4a33c232e5cb89556877f54f3e','1dd037bbf2a58cf7a832b9d8ce56b7a08a62a3476bc59756d6e4d909e89cc289','postgres',array['postgres=X/postgres']::text[]),
  ('erp.save_laundry_receipt_draft_v2(jsonb,uuid,bigint)','27f5839f3f09af817fc99543bd337f72a11f9bddab57b8727303d0718e71ea67','3d6065e14df8273d2efdc875dc84590809f0f8d99fb1b1f09040d037ec1d1bb1','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.save_material_purchase_draft_v2(jsonb,uuid,bigint)','45acb811219f7dcad61f70cf0af04603245b4cb88109055fa29eab1f815e4565','cddda95a600d505c315bc79362c70bc6cda41bc7851f233612d80e823aec7a15','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.save_material_supplier_invoice_draft_v2(jsonb,uuid,bigint)','573e48793924e6c9ff1b8c81cc58f5318b0f3bb33bc6ba34ea06f47cfa7a0912','7b031001563a655ce57025f38a3e41fb7953fb34261cc624eaf5a562c789c943','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.save_worker_roster_v1(jsonb,uuid,bigint)','8f4a367b3f19b1d0a84c2cf2a598280518ffa9ac5c2dd21f411bd3583dde531b','df5d27e328760a1d2454eaa15003f669fcbd1b0bf5eaca171fe99dc0c58a85ac','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.set_accessory_uom_conversion_v2(uuid,text,numeric,timestamp with time zone,text,text,uuid,bigint)','a2c22edff7792dc8e83cafbfe56bc26fbbf405dfc06a8fd1fb004a0cd3606bd0','1684a8965612c48d6bc36bed072e46af48d43fa3a687c545ad15aff0e350c3fd','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.set_fabric_benchmark_price_v2(uuid,numeric,timestamp with time zone,text,uuid,bigint)','4ec95a50bc188b65d3a84fd2614a0f654e5319073021080f84e593486888c386','b0a38b2a91c5484d035f2aee5c6ffd7ae9ee34ff3c5d3884fb857537e0d788a9','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.set_worker_daily_rate_v1(uuid,numeric,date,text,uuid,bigint)','ef41f24702266202ae0e1d1a81b9bd8ffd5c3b50b4d63c787d0363fcff67e74c','6f20fad879ed8635e05ec06f36898d2b6e627ae308f82751e32beed249302379','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)','decff691ec2764767e983571deffc1fb39a12ec5a745400cfc75090fd769f035','0a35df9e1c385ca27f2c34f17de8e22023b58e2f6c42d9788260d0ebd69cecaa','postgres',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.sync_finished_po_wip_residual(uuid,date,text)','df837ac36fc4d7e332798ad724ec3bdf246dd0664b35194714f64e18e12db647','5a6d6184434a2502f77fde47def7fcbc5da0a96d0b8e7f5da352035ca8619200','postgres',array['postgres=X/postgres']::text[]),
  ('erp.sync_laundry_accrual(uuid,date)','7c865a7b76fa1e9b59dfcde6d1d551acef7da8f99a86bfa1e6134287e478fe5f','0069e3fedd94a40f46caa42119ece8a62cbe58575d3b0f2cd1e1001d5b6a1118','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.sync_laundry_accrual_after_rate_change()','84103577542bc889efd140f76331f0b57b2840180e847774ca8de53dbe891247','f38fa0d3b0623ea71f9c986aed27161dca7c094351b97554c6e6bec41eb87b2b','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.sync_material_cost_revaluation(uuid)','af752a5cb068d71af90c646718b55ef2b6eabd9319021202a0d8f92042892f91','7710e4d4f7b5179ec6539a1aa3957cde32c470a8a768eb417850be07bf0fbeda','postgres',array['postgres=X/postgres']::text[]),
  ('erp.sync_opening_hpp_after_fg_adjustment_status()','cb592f2717dd640a7fbdac71cf450e559dd0fadfee679b8acad2855f35b486e3','978af25c68f446e2ec74c2469e76bbfad8043dc103aea690751bb2dfcd86356a','postgres',array['postgres=X/postgres']::text[]),
  ('erp.sync_opening_hpp_after_return_status()','34a7c6b71f9042372df1c98c3cabe1f736d6d91f38649fabfbbdcef7f8a94008','ab8a8ddaa6275ce3b69f2026b1a2f4d1ac48390f3f2aaad93a1141c96f64698a','postgres',array['postgres=X/postgres']::text[]),
  ('erp.sync_opening_hpp_after_sale_status()','245bb589429b42fa46d9c0f97373c2ebdb049ebdea6a0302050b92dd1181dace','716b832feacca82bde123714e0b5b822674388c79f19b2ac405c19ddcac2c227','postgres',array['postgres=X/postgres']::text[]),
  ('erp.sync_opening_lot_hpp_to_gl(uuid,date)','2353bb967fec7d661877db745554b2b48e206ac8b3a36562af70fc60b6107998','854dda0fd4e9c902112fff34d8bee3e25876ba7908830562ce4f81a937181801','postgres',array['postgres=X/postgres']::text[]),
  ('erp.sync_po_hpp_to_gl(uuid,date)','d7899da2ab15841a906d5f5c55e5608ed1eb3a9636254f50018178ece462fd6c','a444bcb1e18ede1b5b9cb300b43ba99565c073d1050a06270046bbb2ecc666e2','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.touch_laundry_receipt_from_bs_allocation()','d92682e532e0e95e9fd78c4e99ceae041b4de6981d2a7069868501a661590f65','90135cae23dd270d6dfed9a8b2668bc9da8afd2f96208c9360a6065057dc46c9','postgres',array['postgres=X/postgres']::text[]),
  ('erp.touch_updated_at()','63521d11274096993048a5fed97ec42851a67090a7ce6e492bfb5238b1d7f403','c763f2b528a413cba95d9e5b3915c50eb7da52c83a3fea9fbdad9e39e9eddc7a','postgres',array['postgres=X/postgres','service_role=X/postgres']::text[]);

create temporary table cp6_ac_expected_views(
  identity text primary key,before_body text not null,before_sha256 text not null,
  after_body text not null,after_sha256 text not null,
  owner_name text not null,acl text[],reloptions text[],rls boolean not null,
  restore_sha256 text not null
) on commit drop;
insert into pg_temp.cp6_ac_expected_views values
  ('erp.v_accessory_category_current_cost','SELECT id AS category_id,
    category_code,
    category_name,
    base_uom_code,
    erp.accessory_category_weighted_avg_cost_at(id, now()) AS weighted_avg_cost_per_base_uom
   FROM erp.accessory_categories c
  WHERE (is_active = true)','6cec0f15f157db3ee5a8ca852527f822b0ff05327758e8f1753e1b4472ce3869','SELECT id AS category_id,
    category_code,
    category_name,
    base_uom_code,
    erp.accessory_category_weighted_avg_cost_at(id, statement_timestamp()) AS weighted_avg_cost_per_base_uom
   FROM erp.accessory_categories c
  WHERE (is_active = true)','3c65f5daf0201efb3a1c4084c1c322c2fac7563f09aeddf222a3ceba772c9d5f','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],array['security_invoker=true']::text[],false,'d789c6407e1b123a76af390e58f97856daf4c7d5d4fb1615d40c13bc45aee9c6'),
  ('erp.v_accessory_hpp_setup','SELECT p.id AS product_id,
    p.sku,
    p.product_name,
    abv.id AS bom_version_id,
    abv.effective_from,
    abv.effective_to,
    ac.category_code,
    ac.category_name,
    ac.base_uom_code,
    abi.qty_per_good_fg_base,
    abi.hpp_method,
    abi.hpp_standard_rate,
    abi.hpp_uom_code,
    abi.reimbursement_rate,
    abi.reimbursement_uom_code,
        CASE
            WHEN (abv.id IS NULL) THEN ''MISSING_BOM''::text
            WHEN (abi.id IS NULL) THEN ''NO_ACCESSORY''::text
            ELSE ''CONFIGURED''::text
        END AS setup_state,
    count(abi.id) OVER (PARTITION BY p.id, abv.id) AS bom_item_count
   FROM (((erp.v_products_current p
     LEFT JOIN erp.accessory_bom_versions abv ON (((abv.product_id = p.identity_root_id) AND (abv.is_active = true) AND (abv.effective_from <= clock_timestamp()) AND ((abv.effective_to IS NULL) OR (abv.effective_to > clock_timestamp())))))
     LEFT JOIN erp.accessory_bom_items abi ON ((abi.bom_version_id = abv.id)))
     LEFT JOIN erp.accessory_categories ac ON ((ac.id = abi.category_id)))','0bbbbd2579a046ffdbfe439c8bcd5497d84273b1a3d1a2a829ab5581c8d07986','SELECT p.id AS product_id,
    p.sku,
    p.product_name,
    abv.id AS bom_version_id,
    abv.effective_from,
    abv.effective_to,
    ac.category_code,
    ac.category_name,
    ac.base_uom_code,
    abi.qty_per_good_fg_base,
    abi.hpp_method,
    abi.hpp_standard_rate,
    abi.hpp_uom_code,
    abi.reimbursement_rate,
    abi.reimbursement_uom_code,
        CASE
            WHEN (abv.id IS NULL) THEN ''MISSING_BOM''::text
            WHEN (abi.id IS NULL) THEN ''NO_ACCESSORY''::text
            ELSE ''CONFIGURED''::text
        END AS setup_state,
    count(abi.id) OVER (PARTITION BY p.id, abv.id) AS bom_item_count
   FROM (((erp.v_products_current p
     LEFT JOIN erp.accessory_bom_versions abv ON (((abv.product_id = p.identity_root_id) AND (abv.is_active = true) AND (abv.effective_from <= statement_timestamp()) AND ((abv.effective_to IS NULL) OR (abv.effective_to > statement_timestamp())))))
     LEFT JOIN erp.accessory_bom_items abi ON ((abi.bom_version_id = abv.id)))
     LEFT JOIN erp.accessory_categories ac ON ((ac.id = abi.category_id)))','0ffbf3ab054353a4e4f765acb1bc2adb2e84eef5cab4cc15ece28fd355e9d062','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],array['security_invoker=true']::text[],false,'9a68930724dcce7a56fae5130bf256e1f8dcd8e5e091a3b0717f9f6f2792a787'),
  ('erp.v_accessory_master_browser','WITH stock AS (
         SELECT v_material_stock_balance.material_id,
            sum(v_material_stock_balance.stock_qty) AS stock_qty,
            sum(v_material_stock_balance.stock_value_at_current_ma) AS stock_value,
            max(v_material_stock_balance.last_movement_at) AS last_movement_at
           FROM erp.v_material_stock_balance
          GROUP BY v_material_stock_balance.material_id
        )
 SELECT m.id AS material_id,
    m.material_sku,
    m.material_name,
    m.is_active,
    m.unit_code AS base_uom_code,
    m.row_version,
    m.cached_stock_qty,
    m.moving_average_cost,
    ac.id AS category_id,
    ac.category_code,
    ac.category_name,
    ac.row_version AS category_row_version,
    cc.weighted_avg_cost_per_base_uom AS category_weighted_avg_cost,
    COALESCE(s.stock_qty, (0)::numeric) AS ledger_stock_qty,
    COALESCE(s.stock_value, (0)::numeric) AS stock_value,
    s.last_movement_at,
    gp.id AS global_price_version_id,
    gp.selling_price AS global_selling_price,
    gp.selling_uom_code AS global_selling_uom_code,
    gp.effective_from AS global_price_effective_from,
    gp.effective_to AS global_price_effective_to,
    concat_ws('' ''::text, m.material_sku, m.material_name, ac.category_code, ac.category_name) AS search_text
   FROM ((((erp.materials m
     JOIN erp.accessory_categories ac ON ((ac.id = m.accessory_category_id)))
     LEFT JOIN erp.v_accessory_category_current_cost cc ON ((cc.category_id = ac.id)))
     LEFT JOIN stock s ON ((s.material_id = m.id)))
     LEFT JOIN LATERAL ( SELECT p.id,
            p.contractor_id,
            p.category_id,
            p.selling_price,
            p.selling_uom_code,
            p.effective_from,
            p.effective_to,
            p.notes,
            p.created_at
           FROM erp.contractor_accessory_price_versions p
          WHERE ((p.category_id = ac.id) AND (p.contractor_id IS NULL) AND (p.effective_from <= now()) AND ((p.effective_to IS NULL) OR (p.effective_to > now())))
          ORDER BY p.effective_from DESC
         LIMIT 1) gp ON (true))
  WHERE ((m.material_type)::text = ''ACCESSORY''::text)','c39242db9de79e1e69c2679984de6bf22d52f63dc30f58ff9f12bc2d71137e6b','WITH stock AS (
         SELECT v_material_stock_balance.material_id,
            sum(v_material_stock_balance.stock_qty) AS stock_qty,
            sum(v_material_stock_balance.stock_value_at_current_ma) AS stock_value,
            max(v_material_stock_balance.last_movement_at) AS last_movement_at
           FROM erp.v_material_stock_balance
          GROUP BY v_material_stock_balance.material_id
        )
 SELECT m.id AS material_id,
    m.material_sku,
    m.material_name,
    m.is_active,
    m.unit_code AS base_uom_code,
    m.row_version,
    m.cached_stock_qty,
    m.moving_average_cost,
    ac.id AS category_id,
    ac.category_code,
    ac.category_name,
    ac.row_version AS category_row_version,
    cc.weighted_avg_cost_per_base_uom AS category_weighted_avg_cost,
    COALESCE(s.stock_qty, (0)::numeric) AS ledger_stock_qty,
    COALESCE(s.stock_value, (0)::numeric) AS stock_value,
    s.last_movement_at,
    gp.id AS global_price_version_id,
    gp.selling_price AS global_selling_price,
    gp.selling_uom_code AS global_selling_uom_code,
    gp.effective_from AS global_price_effective_from,
    gp.effective_to AS global_price_effective_to,
    concat_ws('' ''::text, m.material_sku, m.material_name, ac.category_code, ac.category_name) AS search_text
   FROM ((((erp.materials m
     JOIN erp.accessory_categories ac ON ((ac.id = m.accessory_category_id)))
     LEFT JOIN erp.v_accessory_category_current_cost cc ON ((cc.category_id = ac.id)))
     LEFT JOIN stock s ON ((s.material_id = m.id)))
     LEFT JOIN LATERAL ( SELECT p.id,
            p.contractor_id,
            p.category_id,
            p.selling_price,
            p.selling_uom_code,
            p.effective_from,
            p.effective_to,
            p.notes,
            p.created_at
           FROM erp.contractor_accessory_price_versions p
          WHERE ((p.category_id = ac.id) AND (p.contractor_id IS NULL) AND (p.effective_from <= statement_timestamp()) AND ((p.effective_to IS NULL) OR (p.effective_to > statement_timestamp())))
          ORDER BY p.effective_from DESC
         LIMIT 1) gp ON (true))
  WHERE ((m.material_type)::text = ''ACCESSORY''::text)','45d7858bb4c0650fa8c07810c6db0b0b219ade8981c26cbcf62ad078ca6be1ef','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],array['security_invoker=true']::text[],false,'abfc66c807a59209a8f9bec176b1d7b72f96917c3c548ba688d8e4e5556f66c3'),
  ('erp.v_accessory_price_browser','SELECT p.id AS price_version_id,
    p.category_id,
    ac.category_code,
    ac.category_name,
    p.contractor_id,
    c.contractor_code,
    c.contractor_name,
    p.selling_price,
    p.selling_uom_code,
    p.effective_from,
    p.effective_to,
    p.notes,
    ((p.effective_from <= now()) AND ((p.effective_to IS NULL) OR (p.effective_to > now()))) AS is_current,
    concat_ws('' ''::text, ac.category_code, ac.category_name, c.contractor_code, c.contractor_name, p.selling_uom_code) AS search_text
   FROM ((erp.contractor_accessory_price_versions p
     JOIN erp.accessory_categories ac ON ((ac.id = p.category_id)))
     LEFT JOIN erp.contractors c ON ((c.id = p.contractor_id)))','5f3d9d66e665e3eff4d491e3f4030a9cd1c4132dcb3c90fecd510aacce115d64','SELECT p.id AS price_version_id,
    p.category_id,
    ac.category_code,
    ac.category_name,
    p.contractor_id,
    c.contractor_code,
    c.contractor_name,
    p.selling_price,
    p.selling_uom_code,
    p.effective_from,
    p.effective_to,
    p.notes,
    ((p.effective_from <= statement_timestamp()) AND ((p.effective_to IS NULL) OR (p.effective_to > statement_timestamp()))) AS is_current,
    concat_ws('' ''::text, ac.category_code, ac.category_name, c.contractor_code, c.contractor_name, p.selling_uom_code) AS search_text
   FROM ((erp.contractor_accessory_price_versions p
     JOIN erp.accessory_categories ac ON ((ac.id = p.category_id)))
     LEFT JOIN erp.contractors c ON ((c.id = p.contractor_id)))','c6bd9e3d74accfb969b82adeaf33ad8e0f6207095576100052c1a76cafef176d','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],array['security_invoker=true']::text[],false,'1ca1a0f6e59f22d8e04816ce7cce4e0f9cfc785417104960a0818238f94f710f'),
  ('erp.v_current_product_prices','SELECT DISTINCT ON (product_id) product_id,
    price,
    effective_from
   FROM erp.product_price_versions ppv
  WHERE ((effective_from <= now()) AND ((effective_to IS NULL) OR (effective_to > now())))
  ORDER BY product_id, effective_from DESC, created_at DESC','37ba7e34a3190499e7b99ad44adcd5255a44649645d46e3e87e14f3dc0ec4cc0','SELECT DISTINCT ON (product_id) product_id,
    price,
    effective_from
   FROM erp.product_price_versions ppv
  WHERE ((effective_from <= statement_timestamp()) AND ((effective_to IS NULL) OR (effective_to > statement_timestamp())))
  ORDER BY product_id, effective_from DESC, created_at DESC','3610e705fd0bd193945dd8a8241d8b1706a536ecdaa567c4bdd8adc6f58e3e12','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],array['security_invoker=true']::text[],false,'8b10d8668e05b36209e14e4f00965b244cd406628fafd8b4a5f2eae89a71e46f'),
  ('erp.v_fabric_master_current_benchmark','SELECT m.id AS material_id,
    m.material_sku,
    m.material_name,
    m.unit_code AS base_uom_code,
    m.is_active,
    m.cached_stock_qty,
    m.moving_average_cost,
    m.row_version,
    fp.fabric_category,
    fp.composition,
    fp.construction,
    fp.color_name,
    fp.width_cm,
    fp.gsm,
    fp.minimum_stock_qty,
    fp.preferred_supplier_id,
    s.supplier_name AS preferred_supplier_name,
    bp.id AS benchmark_version_id,
    bp.benchmark_price_per_base_uom,
    bp.effective_from AS benchmark_effective_from,
    bp.effective_to AS benchmark_effective_to,
    (bp.benchmark_price_per_base_uom - m.moving_average_cost) AS benchmark_vs_moving_average_delta,
        CASE
            WHEN (m.moving_average_cost = (0)::numeric) THEN NULL::numeric
            ELSE round((((bp.benchmark_price_per_base_uom - m.moving_average_cost) / m.moving_average_cost) * (100)::numeric), 4)
        END AS benchmark_vs_moving_average_pct
   FROM (((erp.materials m
     LEFT JOIN erp.fabric_master_profiles fp ON ((fp.material_id = m.id)))
     LEFT JOIN erp.suppliers s ON ((s.id = fp.preferred_supplier_id)))
     LEFT JOIN LATERAL ( SELECT x.id,
            x.material_id,
            x.benchmark_price_per_base_uom,
            x.base_uom_code_snapshot,
            x.effective_from,
            x.effective_to,
            x.change_reason,
            x.created_by,
            x.created_at
           FROM erp.fabric_benchmark_price_versions x
          WHERE ((x.material_id = m.id) AND (x.effective_from <= now()) AND ((x.effective_to IS NULL) OR (now() < x.effective_to)))
          ORDER BY x.effective_from DESC
         LIMIT 1) bp ON (true))
  WHERE ((m.material_type)::text = ''FABRIC''::text)','1cab95f2bdbc370ebccd277cc745cfd476c1116bd4ba6a0d5c0fbfc374e80f8b','SELECT m.id AS material_id,
    m.material_sku,
    m.material_name,
    m.unit_code AS base_uom_code,
    m.is_active,
    m.cached_stock_qty,
    m.moving_average_cost,
    m.row_version,
    fp.fabric_category,
    fp.composition,
    fp.construction,
    fp.color_name,
    fp.width_cm,
    fp.gsm,
    fp.minimum_stock_qty,
    fp.preferred_supplier_id,
    s.supplier_name AS preferred_supplier_name,
    bp.id AS benchmark_version_id,
    bp.benchmark_price_per_base_uom,
    bp.effective_from AS benchmark_effective_from,
    bp.effective_to AS benchmark_effective_to,
    (bp.benchmark_price_per_base_uom - m.moving_average_cost) AS benchmark_vs_moving_average_delta,
        CASE
            WHEN (m.moving_average_cost = (0)::numeric) THEN NULL::numeric
            ELSE round((((bp.benchmark_price_per_base_uom - m.moving_average_cost) / m.moving_average_cost) * (100)::numeric), 4)
        END AS benchmark_vs_moving_average_pct
   FROM (((erp.materials m
     LEFT JOIN erp.fabric_master_profiles fp ON ((fp.material_id = m.id)))
     LEFT JOIN erp.suppliers s ON ((s.id = fp.preferred_supplier_id)))
     LEFT JOIN LATERAL ( SELECT x.id,
            x.material_id,
            x.benchmark_price_per_base_uom,
            x.base_uom_code_snapshot,
            x.effective_from,
            x.effective_to,
            x.change_reason,
            x.created_by,
            x.created_at
           FROM erp.fabric_benchmark_price_versions x
          WHERE ((x.material_id = m.id) AND (x.effective_from <= statement_timestamp()) AND ((x.effective_to IS NULL) OR (statement_timestamp() < x.effective_to)))
          ORDER BY x.effective_from DESC
         LIMIT 1) bp ON (true))
  WHERE ((m.material_type)::text = ''FABRIC''::text)','c194577448dbfdfbeabec3219a328c4c1e6826c83223395bb8716e285dd246b6','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],array['security_invoker=true']::text[],false,'c93e807d0f0b44b052c2413c5a4632564b604c5b702f45d9c7d75a5cc30d13d0'),
  ('erp.v_material_purchase_liability_status','SELECT h.id AS purchase_id,
    h.purchase_number,
    h.supplier_id,
    s.supplier_code,
    s.supplier_name,
    h.physical_at,
    h.status,
    h.payment_status,
    COALESCE(sum(i.line_total), (0)::numeric) AS receipt_estimate_amount,
    erp.material_purchase_final_ap_total(h.id) AS final_ap_amount,
    erp.material_purchase_grni_total(h.id) AS grni_estimated_amount,
    erp.material_purchase_total_liability(h.id) AS total_liability_amount,
    COALESCE(( SELECT sum(p.amount) AS sum
           FROM erp.supplier_payments p
          WHERE ((p.purchase_id = h.id) AND ((p.status)::text = ''POSTED''::text))), (0)::numeric) AS paid_amount,
    GREATEST((erp.material_purchase_final_ap_total(h.id) - COALESCE(( SELECT sum(p.amount) AS sum
           FROM erp.supplier_payments p
          WHERE ((p.purchase_id = h.id) AND ((p.status)::text = ''POSTED''::text))), (0)::numeric)), (0)::numeric) AS final_ap_outstanding,
        CASE
            WHEN ((erp.material_purchase_grni_total(h.id) > 0.005) AND (erp.material_purchase_final_ap_total(h.id) > 0.005)) THEN ''PARTIAL_INVOICE''::text
            WHEN (erp.material_purchase_grni_total(h.id) > 0.005) THEN ''KASBON_BELUM_DITERIMA_ESTIMASI_KEWAJIBAN''::text
            WHEN (erp.material_purchase_final_ap_total(h.id) > 0.005) THEN ''FINAL_AP''::text
            ELSE ''NO_LIABILITY''::text
        END AS liability_state,
    ( SELECT string_agg(DISTINCT (ih.invoice_number)::text, '', ''::text ORDER BY (ih.invoice_number)::text) AS string_agg
           FROM ((erp.material_supplier_invoice_lines il
             JOIN erp.material_supplier_invoices ih ON ((ih.id = il.invoice_id)))
             JOIN erp.material_purchase_items pi ON ((pi.id = il.purchase_item_id)))
          WHERE ((pi.purchase_id = h.id) AND ((ih.status)::text = ''POSTED''::text))) AS active_invoice_numbers,
    ( SELECT min(ih.due_date) AS min
           FROM ((erp.material_supplier_invoice_lines il
             JOIN erp.material_supplier_invoices ih ON ((ih.id = il.invoice_id)))
             JOIN erp.material_purchase_items pi ON ((pi.id = il.purchase_item_id)))
          WHERE ((pi.purchase_id = h.id) AND ((ih.status)::text = ''POSTED''::text))) AS earliest_due_date,
        CASE
            WHEN (erp.material_purchase_grni_total(h.id) > 0.005) THEN GREATEST((CURRENT_DATE - (h.physical_at)::date), 0)
            ELSE 0
        END AS unfinalized_days,
    h.row_version,
    h.created_at,
    h.updated_at,
    concat_ws('' ''::text, h.purchase_number, s.supplier_code, s.supplier_name, h.status) AS search_text
   FROM ((erp.material_purchase_headers h
     LEFT JOIN erp.suppliers s ON ((s.id = h.supplier_id)))
     LEFT JOIN erp.material_purchase_items i ON ((i.purchase_id = h.id)))
  GROUP BY h.id, s.id','800f8d9643bfe1091fdf7bbba4d3ff2d057e4e10a7e1970dec1832d6577f067e','SELECT h.id AS purchase_id,
    h.purchase_number,
    h.supplier_id,
    s.supplier_code,
    s.supplier_name,
    h.physical_at,
    h.status,
    h.payment_status,
    COALESCE(sum(i.line_total), (0)::numeric) AS receipt_estimate_amount,
    erp.material_purchase_final_ap_total(h.id) AS final_ap_amount,
    erp.material_purchase_grni_total(h.id) AS grni_estimated_amount,
    erp.material_purchase_total_liability(h.id) AS total_liability_amount,
    COALESCE(( SELECT sum(p.amount) AS sum
           FROM erp.supplier_payments p
          WHERE ((p.purchase_id = h.id) AND ((p.status)::text = ''POSTED''::text))), (0)::numeric) AS paid_amount,
    GREATEST((erp.material_purchase_final_ap_total(h.id) - COALESCE(( SELECT sum(p.amount) AS sum
           FROM erp.supplier_payments p
          WHERE ((p.purchase_id = h.id) AND ((p.status)::text = ''POSTED''::text))), (0)::numeric)), (0)::numeric) AS final_ap_outstanding,
        CASE
            WHEN ((erp.material_purchase_grni_total(h.id) > 0.005) AND (erp.material_purchase_final_ap_total(h.id) > 0.005)) THEN ''PARTIAL_INVOICE''::text
            WHEN (erp.material_purchase_grni_total(h.id) > 0.005) THEN ''KASBON_BELUM_DITERIMA_ESTIMASI_KEWAJIBAN''::text
            WHEN (erp.material_purchase_final_ap_total(h.id) > 0.005) THEN ''FINAL_AP''::text
            ELSE ''NO_LIABILITY''::text
        END AS liability_state,
    ( SELECT string_agg(DISTINCT (ih.invoice_number)::text, '', ''::text ORDER BY (ih.invoice_number)::text) AS string_agg
           FROM ((erp.material_supplier_invoice_lines il
             JOIN erp.material_supplier_invoices ih ON ((ih.id = il.invoice_id)))
             JOIN erp.material_purchase_items pi ON ((pi.id = il.purchase_item_id)))
          WHERE ((pi.purchase_id = h.id) AND ((ih.status)::text = ''POSTED''::text))) AS active_invoice_numbers,
    ( SELECT min(ih.due_date) AS min
           FROM ((erp.material_supplier_invoice_lines il
             JOIN erp.material_supplier_invoices ih ON ((ih.id = il.invoice_id)))
             JOIN erp.material_purchase_items pi ON ((pi.id = il.purchase_item_id)))
          WHERE ((pi.purchase_id = h.id) AND ((ih.status)::text = ''POSTED''::text))) AS earliest_due_date,
        CASE
            WHEN (erp.material_purchase_grni_total(h.id) > 0.005) THEN GREATEST((((statement_timestamp() AT TIME ZONE ''Asia/Jakarta''::text))::date - ((h.physical_at) AT TIME ZONE ''Asia/Jakarta'')::date), 0)
            ELSE 0
        END AS unfinalized_days,
    h.row_version,
    h.created_at,
    h.updated_at,
    concat_ws('' ''::text, h.purchase_number, s.supplier_code, s.supplier_name, h.status) AS search_text
   FROM ((erp.material_purchase_headers h
     LEFT JOIN erp.suppliers s ON ((s.id = h.supplier_id)))
     LEFT JOIN erp.material_purchase_items i ON ((i.purchase_id = h.id)))
  GROUP BY h.id, s.id','d0a42f5eb48da1e91534a43a7e1aa4ebeda6894805e86659880fe8603d2304f9','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],array['security_invoker=true']::text[],false,'c49b2bc36cd0d84ccff7384631a9f75ee69ea8f4db3f404f749b8f32149dc140'),
  ('erp.v_material_supplier_invoice_browser','SELECT h.id AS supplier_invoice_id,
    h.invoice_number,
    h.supplier_id,
    s.supplier_code,
    s.supplier_name,
    h.invoice_date,
    h.received_at,
    h.due_date,
    h.status,
    h.notes,
    h.posting_reason,
    h.reversal_reason,
    count(l.id) AS line_count,
    count(DISTINCT i.purchase_id) AS receipt_count,
    COALESCE(sum(l.qty_invoiced), (0)::numeric) AS matched_qty,
    COALESCE(sum(l.gross_amount), (0)::numeric) AS gross_amount,
    COALESCE(sum(l.discount_amount), (0)::numeric) AS discount_amount,
    COALESCE(sum(l.net_amount), (0)::numeric) AS net_amount,
    min(ph.physical_at) AS oldest_receipt_at,
        CASE
            WHEN (min(ph.physical_at) IS NULL) THEN 0
            ELSE GREATEST(((h.received_at)::date - (min(ph.physical_at))::date), 0)
        END AS invoice_delay_days,
    h.row_version,
    h.created_at,
    h.updated_at,
    h.posted_at,
    h.reversed_at,
    concat_ws('' ''::text, h.invoice_number, s.supplier_code, s.supplier_name, h.status, h.notes) AS search_text
   FROM ((((erp.material_supplier_invoices h
     JOIN erp.suppliers s ON ((s.id = h.supplier_id)))
     LEFT JOIN erp.material_supplier_invoice_lines l ON ((l.invoice_id = h.id)))
     LEFT JOIN erp.material_purchase_items i ON ((i.id = l.purchase_item_id)))
     LEFT JOIN erp.material_purchase_headers ph ON ((ph.id = i.purchase_id)))
  GROUP BY h.id, s.id','0dfbbe6b464276bd8a63e87d60fa8e3818bca7bb1bccb92221741317af46f3f2','SELECT h.id AS supplier_invoice_id,
    h.invoice_number,
    h.supplier_id,
    s.supplier_code,
    s.supplier_name,
    h.invoice_date,
    h.received_at,
    h.due_date,
    h.status,
    h.notes,
    h.posting_reason,
    h.reversal_reason,
    count(l.id) AS line_count,
    count(DISTINCT i.purchase_id) AS receipt_count,
    COALESCE(sum(l.qty_invoiced), (0)::numeric) AS matched_qty,
    COALESCE(sum(l.gross_amount), (0)::numeric) AS gross_amount,
    COALESCE(sum(l.discount_amount), (0)::numeric) AS discount_amount,
    COALESCE(sum(l.net_amount), (0)::numeric) AS net_amount,
    min(ph.physical_at) AS oldest_receipt_at,
        CASE
            WHEN (min(ph.physical_at) IS NULL) THEN 0
            ELSE GREATEST((((h.received_at) AT TIME ZONE ''Asia/Jakarta'')::date - ((min(ph.physical_at)) AT TIME ZONE ''Asia/Jakarta'')::date), 0)
        END AS invoice_delay_days,
    h.row_version,
    h.created_at,
    h.updated_at,
    h.posted_at,
    h.reversed_at,
    concat_ws('' ''::text, h.invoice_number, s.supplier_code, s.supplier_name, h.status, h.notes) AS search_text
   FROM ((((erp.material_supplier_invoices h
     JOIN erp.suppliers s ON ((s.id = h.supplier_id)))
     LEFT JOIN erp.material_supplier_invoice_lines l ON ((l.invoice_id = h.id)))
     LEFT JOIN erp.material_purchase_items i ON ((i.id = l.purchase_item_id)))
     LEFT JOIN erp.material_purchase_headers ph ON ((ph.id = i.purchase_id)))
  GROUP BY h.id, s.id','aed6fdcc147d2f379a31b2c3db4a5fdc78f98be5c8ee700f0871e9096a198c71','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],array['security_invoker=true']::text[],false,'50d32d01f3455eb5e94003bb920ca3e5bd5f6f586fbb690510f465b03d6a245c'),
  ('erp.v_payroll_nota_browser','SELECT n.id AS payroll_id,
    n.payroll_number,
    n.contractor_id,
    c.contractor_code,
    c.contractor_name,
    n.period_start,
    n.period_end,
    n.status,
    n.row_version,
    n.payment_date,
    n.settled_at,
    n.labor_total,
    n.attendance_total,
    n.reimburse_total,
    n.deduction_total,
    n.manual_adjustment,
    n.net_payable,
    COALESCE(x.work_line_count, (0)::bigint) AS work_line_count,
    COALESCE(x.work_qty, (0)::bigint) AS work_qty,
    COALESCE(e.eligible_line_count, (0)::bigint) AS eligible_line_count,
    COALESCE(e.eligible_qty, (0)::bigint) AS eligible_qty,
    (COALESCE(e.eligible_amount, (0)::numeric))::numeric(24,2) AS eligible_amount,
    ((n.status)::text = ANY (ARRAY[(''DRAFT''::character varying)::text, (''CALCULATED''::character varying)::text, (''REVIEW''::character varying)::text])) AS can_merge,
    ((n.status)::text = ANY (ARRAY[(''APPROVED''::character varying)::text, (''PAID''::character varying)::text, (''REVERSED''::character varying)::text])) AS is_locked,
    n.notes,
    n.created_at,
    n.updated_at
   FROM (((erp.payroll_settlements n
     JOIN erp.contractors c ON ((c.id = n.contractor_id)))
     LEFT JOIN LATERAL ( SELECT count(*) AS work_line_count,
            COALESCE(sum(w.qty_payable), (0)::bigint) AS work_qty
           FROM erp.payroll_work_items w
          WHERE (w.payroll_id = n.id)) x ON (true))
     LEFT JOIN LATERAL ( SELECT count(*) AS eligible_line_count,
            COALESCE(sum(q.remaining_qty), (0)::bigint) AS eligible_qty,
            COALESCE(sum(((q.remaining_qty)::numeric * q.rate_snapshot)), (0)::numeric) AS eligible_amount
           FROM erp.v_payroll_eligible_work_lines q
          WHERE ((q.contractor_id = n.contractor_id) AND ((q.eligible_at)::date <= n.period_end))) e ON (true))','a35e0725b883d08e3cec365ce2cf8b4d08544643dbb2d79c04c4da2baa687acd','SELECT n.id AS payroll_id,
    n.payroll_number,
    n.contractor_id,
    c.contractor_code,
    c.contractor_name,
    n.period_start,
    n.period_end,
    n.status,
    n.row_version,
    n.payment_date,
    n.settled_at,
    n.labor_total,
    n.attendance_total,
    n.reimburse_total,
    n.deduction_total,
    n.manual_adjustment,
    n.net_payable,
    COALESCE(x.work_line_count, (0)::bigint) AS work_line_count,
    COALESCE(x.work_qty, (0)::bigint) AS work_qty,
    COALESCE(e.eligible_line_count, (0)::bigint) AS eligible_line_count,
    COALESCE(e.eligible_qty, (0)::bigint) AS eligible_qty,
    (COALESCE(e.eligible_amount, (0)::numeric))::numeric(24,2) AS eligible_amount,
    ((n.status)::text = ANY (ARRAY[(''DRAFT''::character varying)::text, (''CALCULATED''::character varying)::text, (''REVIEW''::character varying)::text])) AS can_merge,
    ((n.status)::text = ANY (ARRAY[(''APPROVED''::character varying)::text, (''PAID''::character varying)::text, (''REVERSED''::character varying)::text])) AS is_locked,
    n.notes,
    n.created_at,
    n.updated_at
   FROM (((erp.payroll_settlements n
     JOIN erp.contractors c ON ((c.id = n.contractor_id)))
     LEFT JOIN LATERAL ( SELECT count(*) AS work_line_count,
            COALESCE(sum(w.qty_payable), (0)::bigint) AS work_qty
           FROM erp.payroll_work_items w
          WHERE (w.payroll_id = n.id)) x ON (true))
     LEFT JOIN LATERAL ( SELECT count(*) AS eligible_line_count,
            COALESCE(sum(q.remaining_qty), (0)::bigint) AS eligible_qty,
            COALESCE(sum(((q.remaining_qty)::numeric * q.rate_snapshot)), (0)::numeric) AS eligible_amount
           FROM erp.v_payroll_eligible_work_lines q
          WHERE ((q.contractor_id = n.contractor_id) AND (((q.eligible_at) AT TIME ZONE ''Asia/Jakarta'')::date <= n.period_end))) e ON (true))','16f47474d81b89b0639a3c46cd49c90140691926e4cc03d610e493b1677ca226','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],array['security_invoker=true']::text[],false,'278040c49bd65164dec4e31948cb910127704bf6072c0b801147270a57567989'),
  ('erp.v_product_price_current','SELECT p.id AS product_id,
    p.identity_root_id,
    p.sku,
    p.product_name,
    p.color_name,
    p.size_id,
    pp.id AS price_version_id,
    pp.price,
    pp.effective_from AS price_effective_from,
    pp.effective_to AS price_effective_to
   FROM (erp.v_products_current p
     LEFT JOIN LATERAL ( SELECT x.id,
            x.product_id,
            x.price,
            x.effective_from,
            x.effective_to,
            x.change_note,
            x.created_by,
            x.created_at
           FROM erp.product_price_versions x
          WHERE ((x.product_id = p.identity_root_id) AND (x.effective_from <= clock_timestamp()) AND ((x.effective_to IS NULL) OR (x.effective_to > clock_timestamp())))
          ORDER BY x.effective_from DESC, x.created_at DESC, x.id DESC
         LIMIT 1) pp ON (true))','8be0c344171b109c9491838533c69215886ea512ff70ddd5317a40e5acbb5a08','SELECT p.id AS product_id,
    p.identity_root_id,
    p.sku,
    p.product_name,
    p.color_name,
    p.size_id,
    pp.id AS price_version_id,
    pp.price,
    pp.effective_from AS price_effective_from,
    pp.effective_to AS price_effective_to
   FROM (erp.v_products_current p
     LEFT JOIN LATERAL ( SELECT x.id,
            x.product_id,
            x.price,
            x.effective_from,
            x.effective_to,
            x.change_note,
            x.created_by,
            x.created_at
           FROM erp.product_price_versions x
          WHERE ((x.product_id = p.identity_root_id) AND (x.effective_from <= statement_timestamp()) AND ((x.effective_to IS NULL) OR (x.effective_to > statement_timestamp())))
          ORDER BY x.effective_from DESC, x.created_at DESC, x.id DESC
         LIMIT 1) pp ON (true))','cb46a4e7294723696c58c42ebfa4a6526a896a2e4f217dc4cda1c03d82792b96','postgres',null::text[],array['security_invoker=true']::text[],false,'213ecc404bc9c0adb7d4fabbc789d7fcdd53bde6c98799b6d180355c068fa856'),
  ('erp.v_products_current','SELECT id,
    sku,
    model_id,
    brand_id,
    color_name,
    size_id,
    product_name,
    is_portal_visible,
    is_active,
    created_at,
    updated_at,
    identity_root_id,
    effective_from,
    effective_to,
    supersedes_product_id
   FROM erp.products p
  WHERE ((is_active = true) AND (effective_from <= clock_timestamp()) AND ((effective_to IS NULL) OR (effective_to > clock_timestamp())))','6dd935d31fc83aaae3237b13936ab6a15ce1f2acd45a7b4d74fe31daef3129a3','SELECT id,
    sku,
    model_id,
    brand_id,
    color_name,
    size_id,
    product_name,
    is_portal_visible,
    is_active,
    created_at,
    updated_at,
    identity_root_id,
    effective_from,
    effective_to,
    supersedes_product_id
   FROM erp.products p
  WHERE ((is_active = true) AND (effective_from <= statement_timestamp()) AND ((effective_to IS NULL) OR (effective_to > statement_timestamp())))','ff45f6e8f1265b2b3795a4241f60966a2c178df03c6b956ed8b95cb7c5e55d43','postgres',null::text[],array['security_invoker=true']::text[],false,'eb5262b3c7fd6d85739c4ed34a32c42071a84a375b02834fb98c866a94d82416'),
  ('erp.v_products_sellable','WITH stock AS (
         SELECT fg_inventory_balances.product_id,
            COALESCE(sum(fg_inventory_balances.cached_qty_pcs), (0)::bigint) AS stock_pcs
           FROM erp.fg_inventory_balances
          GROUP BY fg_inventory_balances.product_id
        )
 SELECT p.id,
    p.sku,
    p.model_id,
    p.brand_id,
    p.color_name,
    p.size_id,
    p.product_name,
    p.is_portal_visible,
    p.is_active,
    p.created_at,
    p.updated_at,
    p.identity_root_id,
    p.effective_from,
    p.effective_to,
    p.supersedes_product_id,
    COALESCE(s.stock_pcs, (0)::bigint) AS stock_pcs,
    ((p.is_active = true) AND (p.effective_from <= clock_timestamp()) AND ((p.effective_to IS NULL) OR (p.effective_to > clock_timestamp()))) AS is_current_identity
   FROM (erp.products p
     LEFT JOIN stock s ON ((s.product_id = p.id)))
  WHERE (((p.is_active = true) AND (p.effective_from <= clock_timestamp()) AND ((p.effective_to IS NULL) OR (p.effective_to > clock_timestamp()))) OR (COALESCE(s.stock_pcs, (0)::bigint) > 0))','de4ac39c54cf7001638f1f70df38ad82d07aeb372266d2cfa79caf390ebceb71','WITH stock AS (
         SELECT fg_inventory_balances.product_id,
            COALESCE(sum(fg_inventory_balances.cached_qty_pcs), (0)::bigint) AS stock_pcs
           FROM erp.fg_inventory_balances
          GROUP BY fg_inventory_balances.product_id
        )
 SELECT p.id,
    p.sku,
    p.model_id,
    p.brand_id,
    p.color_name,
    p.size_id,
    p.product_name,
    p.is_portal_visible,
    p.is_active,
    p.created_at,
    p.updated_at,
    p.identity_root_id,
    p.effective_from,
    p.effective_to,
    p.supersedes_product_id,
    COALESCE(s.stock_pcs, (0)::bigint) AS stock_pcs,
    ((p.is_active = true) AND (p.effective_from <= statement_timestamp()) AND ((p.effective_to IS NULL) OR (p.effective_to > statement_timestamp()))) AS is_current_identity
   FROM (erp.products p
     LEFT JOIN stock s ON ((s.product_id = p.id)))
  WHERE (((p.is_active = true) AND (p.effective_from <= statement_timestamp()) AND ((p.effective_to IS NULL) OR (p.effective_to > statement_timestamp()))) OR (COALESCE(s.stock_pcs, (0)::bigint) > 0))','51ab4bf4553b797c4a8ec70892f312dbaaa0154d60efc790bb29ab68c42fd884','postgres',null::text[],array['security_invoker=true']::text[],false,'3e383965410b4ebf02388db7f51428aa5be232eff32edee356c7d3039c84c88a'),
  ('erp.v_supplier_ap_aging','WITH ap AS (
         SELECT h.id AS purchase_id,
            h.purchase_number,
            h.supplier_id,
            s.supplier_name,
            (COALESCE(( SELECT string_agg(DISTINCT (ih.invoice_number)::text, '', ''::text ORDER BY (ih.invoice_number)::text) AS string_agg
                   FROM ((erp.material_supplier_invoice_lines il
                     JOIN erp.material_supplier_invoices ih ON ((ih.id = il.invoice_id)))
                     JOIN erp.material_purchase_items pi ON ((pi.id = il.purchase_item_id)))
                  WHERE ((pi.purchase_id = h.id) AND ((ih.status)::text = ''POSTED''::text))), (h.supplier_invoice_number)::text))::character varying(100) AS supplier_invoice_number,
            h.physical_at,
            COALESCE(( SELECT min(ih.due_date) AS min
                   FROM ((erp.material_supplier_invoice_lines il
                     JOIN erp.material_supplier_invoices ih ON ((ih.id = il.invoice_id)))
                     JOIN erp.material_purchase_items pi ON ((pi.id = il.purchase_item_id)))
                  WHERE ((pi.purchase_id = h.id) AND ((ih.status)::text = ''POSTED''::text))), h.due_date) AS due_date,
            erp.material_purchase_final_ap_total(h.id) AS payable_amount,
            COALESCE(( SELECT sum(sp.amount) AS sum
                   FROM erp.supplier_payments sp
                  WHERE ((sp.purchase_id = h.id) AND ((sp.status)::text = ''POSTED''::text))), (0)::numeric) AS paid_amount
           FROM (erp.material_purchase_headers h
             LEFT JOIN erp.suppliers s ON ((s.id = h.supplier_id)))
          WHERE ((h.status)::text = ''POSTED''::text)
        )
 SELECT purchase_id,
    purchase_number,
    supplier_id,
    supplier_name,
    supplier_invoice_number,
    physical_at,
    due_date,
    payable_amount,
    paid_amount,
    GREATEST((payable_amount - paid_amount), (0)::numeric) AS outstanding_amount,
        CASE
            WHEN ((due_date IS NULL) OR (payable_amount <= paid_amount)) THEN 0
            ELSE GREATEST((CURRENT_DATE - due_date), 0)
        END AS days_overdue,
        CASE
            WHEN (payable_amount <= paid_amount) THEN ''PAID''::text
            WHEN ((due_date IS NULL) OR (CURRENT_DATE <= due_date)) THEN ''CURRENT''::text
            WHEN ((CURRENT_DATE - due_date) <= 30) THEN ''1_30''::text
            WHEN ((CURRENT_DATE - due_date) <= 60) THEN ''31_60''::text
            WHEN ((CURRENT_DATE - due_date) <= 90) THEN ''61_90''::text
            ELSE ''90_PLUS''::text
        END AS aging_bucket
   FROM ap
  WHERE ((payable_amount > 0.005) OR (paid_amount > 0.005))','7726a89e13a685e9582fe8f159e63af65d1f1cd26e5e4823f81d2ed2e97f8700','WITH ap AS (
         SELECT h.id AS purchase_id,
            h.purchase_number,
            h.supplier_id,
            s.supplier_name,
            (COALESCE(( SELECT string_agg(DISTINCT (ih.invoice_number)::text, '', ''::text ORDER BY (ih.invoice_number)::text) AS string_agg
                   FROM ((erp.material_supplier_invoice_lines il
                     JOIN erp.material_supplier_invoices ih ON ((ih.id = il.invoice_id)))
                     JOIN erp.material_purchase_items pi ON ((pi.id = il.purchase_item_id)))
                  WHERE ((pi.purchase_id = h.id) AND ((ih.status)::text = ''POSTED''::text))), (h.supplier_invoice_number)::text))::character varying(100) AS supplier_invoice_number,
            h.physical_at,
            COALESCE(( SELECT min(ih.due_date) AS min
                   FROM ((erp.material_supplier_invoice_lines il
                     JOIN erp.material_supplier_invoices ih ON ((ih.id = il.invoice_id)))
                     JOIN erp.material_purchase_items pi ON ((pi.id = il.purchase_item_id)))
                  WHERE ((pi.purchase_id = h.id) AND ((ih.status)::text = ''POSTED''::text))), h.due_date) AS due_date,
            erp.material_purchase_final_ap_total(h.id) AS payable_amount,
            COALESCE(( SELECT sum(sp.amount) AS sum
                   FROM erp.supplier_payments sp
                  WHERE ((sp.purchase_id = h.id) AND ((sp.status)::text = ''POSTED''::text))), (0)::numeric) AS paid_amount
           FROM (erp.material_purchase_headers h
             LEFT JOIN erp.suppliers s ON ((s.id = h.supplier_id)))
          WHERE ((h.status)::text = ''POSTED''::text)
        )
 SELECT purchase_id,
    purchase_number,
    supplier_id,
    supplier_name,
    supplier_invoice_number,
    physical_at,
    due_date,
    payable_amount,
    paid_amount,
    GREATEST((payable_amount - paid_amount), (0)::numeric) AS outstanding_amount,
        CASE
            WHEN ((due_date IS NULL) OR (payable_amount <= paid_amount)) THEN 0
            ELSE GREATEST((((statement_timestamp() AT TIME ZONE ''Asia/Jakarta''::text))::date - due_date), 0)
        END AS days_overdue,
        CASE
            WHEN (payable_amount <= paid_amount) THEN ''PAID''::text
            WHEN ((due_date IS NULL) OR (((statement_timestamp() AT TIME ZONE ''Asia/Jakarta''::text))::date <= due_date)) THEN ''CURRENT''::text
            WHEN ((((statement_timestamp() AT TIME ZONE ''Asia/Jakarta''::text))::date - due_date) <= 30) THEN ''1_30''::text
            WHEN ((((statement_timestamp() AT TIME ZONE ''Asia/Jakarta''::text))::date - due_date) <= 60) THEN ''31_60''::text
            WHEN ((((statement_timestamp() AT TIME ZONE ''Asia/Jakarta''::text))::date - due_date) <= 90) THEN ''61_90''::text
            ELSE ''90_PLUS''::text
        END AS aging_bucket
   FROM ap
  WHERE ((payable_amount > 0.005) OR (paid_amount > 0.005))','e78b3217d9b8ec92f1eec54758c85bbb0216935d0334bcfdce476ad530700a67','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],array['security_invoker=true']::text[],false,'0fc6adaf1402343b9dc5a598bcdfea318ff67fea4e8a2a493b0c6f58d014db25');

create temporary table cp6_ac_expected_defaults(
  identity text primary key,table_name text not null,column_name text not null,
  before_expression text not null,after_expression text not null,
  owner_name text not null,acl text[],rls boolean not null,
  restore_sha256 text not null
) on commit drop;
insert into pg_temp.cp6_ac_expected_defaults values
  ('erp.accessory_bom_versions.effective_from','accessory_bom_versions','effective_from','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'1832574a66e0c072be5cae5f583e72ce4738bbb4a4c3841bdabaabfbe6411717'),
  ('erp.accessory_bom_versions.created_at','accessory_bom_versions','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'1cc4ec1945e068dba2860ed293332009da255e86ff6e116a5699620e1a50f4ea'),
  ('erp.accessory_categories.created_at','accessory_categories','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'cfc10b698e9119f6b4a7548bb8854c32c19832d565ccc4c75b52fffac545ab4a'),
  ('erp.accessory_categories.updated_at','accessory_categories','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'0971cd641fb98ec092300ceea2e2c73f424fd079cface78598e9b4ca1cc7b1a3'),
  ('erp.accessory_category_uom_conversions.effective_from','accessory_category_uom_conversions','effective_from','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'cd15ea3a77a40810d4b2187b12f69649b02fa8810eb599c073ba232f49209ab9'),
  ('erp.accessory_category_uom_conversions.created_at','accessory_category_uom_conversions','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'ef493b3fb08cd406c51bb6d4a1c48110ce3583f34cfc7b7435b1c42cd19e0200'),
  ('erp.account_daily_balances.updated_at','account_daily_balances','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'acc3eddd0580bae7d8c45c95dbf902f9f56539e546bba4f0d0d8203de1be42ca'),
  ('erp.accounting_period_control.updated_at','accounting_period_control','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'ea31bb3b8a67391734966924e644dea98d2d8f05f8eeb19bbf94519453d38a66'),
  ('erp.app_users.created_at','app_users','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'3cfbf40d1f04f0a58fd825331a25b053bbb626b75d65d3fd165fa8592d9e9e43'),
  ('erp.app_users.updated_at','app_users','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'86dddf7a28122df3d63a7370046754e621597007ce052c78efb565333bf4cb43'),
  ('erp.attendance_records.created_at','attendance_records','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'256d3d81c9676bed2a99fcd8eb7e67ca5510e694140eac714d022c553008237e'),
  ('erp.attendance_records.updated_at','attendance_records','updated_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'45319db494c7fe116c1d65f355b269400c03236d92e8247c7ca3abb8e731f470'),
  ('erp.audit_logs.changed_at','audit_logs','changed_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'8ab8cc5995fb290153515e0b25d505c70251ce3604dc5a12b5d416b4cf1e7d5a'),
  ('erp.brands.created_at','brands','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'951f1dab8f5eaf5a604416275a4d1415ef436c33f339416a37ac42b1b6ac2f7f'),
  ('erp.brands.updated_at','brands','updated_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'b98aed247ff3bcdfc2184a81f53e1243214414c1f05dbf679e31943975782654'),
  ('erp.bs_cases.created_at','bs_cases','created_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'77c131e71dfaf3ac417a55b182f4b354fd4fa327c3b981cef7eefc710dea6ba4'),
  ('erp.bs_cases.updated_at','bs_cases','updated_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'5e0602d95947a59f19c3fae5f3b420ff6920ec64abf7ae193b954a9bcee44961'),
  ('erp.bs_resolutions.created_at','bs_resolutions','created_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'62fc66b5218a745777dcb18ac09de61bca60ed5b23818ed9e8200148313a893a'),
  ('erp.chart_accounts.created_at','chart_accounts','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'e72d6257a98fd0bf8fac7a2ff06f4804ceded0856428275ad2e0dbc9a31aaf3f'),
  ('erp.contractor_accessory_price_versions.effective_from','contractor_accessory_price_versions','effective_from','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'ed912c04eb8878aa70b9c3f57cc87472d428fb260353cf98262b365dbf6a3068'),
  ('erp.contractor_accessory_price_versions.created_at','contractor_accessory_price_versions','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'5e38b8b5874602e7861f78c1e357010c5cbde4167f6011b8e79a2ec8b4097dc6'),
  ('erp.contractor_accessory_reimbursement_entitlements.created_at','contractor_accessory_reimbursement_entitlements','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'37bca95c83aff7a0687037a0d77c72e833de2d7cb9d056d195bbf8113ce05f65'),
  ('erp.contractor_material_issues.created_at','contractor_material_issues','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'85fc12c2ee552d9cb4992f733f35f59f568c75b07cb06045b09fe8c2b11480ea'),
  ('erp.contractor_material_issues.updated_at','contractor_material_issues','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'c1dccfc8724951a88e81395f40f609c722b98c0c23feb1c0501b5185bee3c83c'),
  ('erp.contractor_material_price_versions.effective_from','contractor_material_price_versions','effective_from','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'f297779384c5b744335a3d38a733175283316a5c9ec19fde0654b24c9caf1bbf'),
  ('erp.contractor_material_price_versions.created_at','contractor_material_price_versions','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'345785aaadca2e5ff643d2ec6f4d041d125892ec4c51821e85b8c0117c27e8da'),
  ('erp.contractor_work_rates.effective_from','contractor_work_rates','effective_from','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'430aaee8e1a6c43c2b3cf8de4b37b8253c22fa7336a34c756b0f4fe7fd0607ed'),
  ('erp.contractor_work_rates.created_at','contractor_work_rates','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'d83053eb518595f6e6b876ea5e0248f00cbddadfd4a7b40e84ca2cc02f0fbac3'),
  ('erp.contractor_workers.created_at','contractor_workers','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'bb356259c1449a48e01efba691ad3a835538c17410282c02de2defae811dfdc9'),
  ('erp.contractor_workers.updated_at','contractor_workers','updated_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'74edf2e3985f8d41d5213233c1a4e432ea0b5eb7912d77cadfad6f47b8f5d47c'),
  ('erp.contractors.created_at','contractors','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'c1968987218cd11baf5facc9a4092ae78cd8ecc91cd629868e9df81da844d9a4'),
  ('erp.contractors.updated_at','contractors','updated_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'acf3c2ddff4c21a596ba500fca70794743970f66cfb211204fd664a291e71c86'),
  ('erp.cost_adjustments.entered_at','cost_adjustments','entered_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'d64237b43f3449c760bc9e829e2558814b61c8d57628546b155a61ca41781fc5'),
  ('erp.cost_recalc_queue.queued_at','cost_recalc_queue','queued_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'27ad72ec6c8fb166f98934eb9987b9fe9cd3f9f1300f42e932d58733a95ef97f'),
  ('erp.customer_user_access.created_at','customer_user_access','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'36cb99cabf3db6965e13a0426f9b5a9ee4cfe01643f1f136a8288cb10b3a37c8'),
  ('erp.customers.created_at','customers','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'c97dc14aee242dcd313807d5f4ba6301a2e2f38a06259ec8c965553a013656b6'),
  ('erp.customers.updated_at','customers','updated_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'4c0291ea9029fc63b6d406d2af3d486f0f9589b4d01edfe8b862e73ed1f71ee5'),
  ('erp.cutting_batches.created_at','cutting_batches','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'363ffab9966fd3ff86c4c448bb92d502a2b5e6a0342b421cb8a395ac7182a695'),
  ('erp.cutting_batches.updated_at','cutting_batches','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'a05894d8a3b878664a8e2998050ab976ac7f5d4c61f7339a36f5fa73c8c517a0'),
  ('erp.cutting_groups.created_at','cutting_groups','created_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'d9fd2e249d968bceb076454f656a4cacf541498c01dbe055985ffce43343297a'),
  ('erp.cutting_groups.updated_at','cutting_groups','updated_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'8a28eca77ccad6900822cc12faa58e85d663c85507dc7707afbb76b1fc0bb607'),
  ('erp.cutting_qty_correction_lines.created_at','cutting_qty_correction_lines','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'6095c5e65962aed1968cdc8ee482b13104b9594571e674b090eb7a6242b6652e'),
  ('erp.cutting_qty_corrections.created_at','cutting_qty_corrections','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'7bb7ec79c834a594123ec9d7b1e2a8b0603d99288dab15b97f944e575755f27c'),
  ('erp.fabric_benchmark_price_versions.created_at','fabric_benchmark_price_versions','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'b0f67ad2724ffdae3680c7cd26436ea80a35814628b9219bab49eb24dc0b5483'),
  ('erp.fabric_master_profiles.created_at','fabric_master_profiles','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'3faaa565043f36249dc3a94a141caa91a661c4d4e3b89fea3dfcc59020e66709'),
  ('erp.fabric_master_profiles.updated_at','fabric_master_profiles','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'c1e670632807bc16efa99b31d8cc9221269645861702e841f5e57fc62bb34abb'),
  ('erp.fg_accessory_cost_snapshots.snapshotted_at','fg_accessory_cost_snapshots','snapshotted_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'6a302c5bf74ab1fbfb0278ddfab01347442c001a8dc6eee9b00ab56ad121e2b1'),
  ('erp.fg_adjustments.created_at','fg_adjustments','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'9c523baf997ba6686a36ae59a14ce41159ed2553fc0af8a525eec89578cd5861'),
  ('erp.fg_adjustments.updated_at','fg_adjustments','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'cd19809b32165c150a65b3f2867a39e4f8503663d67e0ae782588a914ca48095'),
  ('erp.fg_inventory_balances.updated_at','fg_inventory_balances','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'3bc7fb3734ba98638b0e78dd864084cdf559ea20ae86fcc4fff61d71af182d2a'),
  ('erp.fg_lots.created_at','fg_lots','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'185b1b3ba4447c12124f91306c2441c6b9306ffd86d8f698293bcb0857e15eb0'),
  ('erp.hpp_version_components.created_at','hpp_version_components','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'499c97331e2d96b38152a511ab37c82b5a46def019c9b7f8f53252367a860258'),
  ('erp.hpp_versions.calculated_at','hpp_versions','calculated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'ea489d45dcecdd2af31f4bdb3adf8bce4607fa83a959a7b37ff8326395761d49'),
  ('erp.idempotency_requests.created_at','idempotency_requests','created_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres']::text[],true,'910f24e14468cb042e07e19d755a8c21c604435df0137c099e04dfee6b9ce21c'),
  ('erp.idempotency_requests.updated_at','idempotency_requests','updated_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres']::text[],true,'fd8c075882c0b0b8809c5805fd24a55cbb68b223e6713b2fb35d44922b24b12d'),
  ('erp.idempotency_requests.expires_at','idempotency_requests','expires_at','(now() + ''30 days''::interval)','(statement_timestamp() + ''30 days''::interval)','postgres',array['postgres=arwdDxtm/postgres']::text[],true,'5214de31e61b5693b796cf4c554b86bcf756101298d3fd0eb11643f8dd79aa47'),
  ('erp.journal_entries.posting_at','journal_entries','posting_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'b1e281ac8550c1ce7086a6127a2c6a0925e0089f2b51cc453fb5b2694a896189'),
  ('erp.journal_entries.created_at','journal_entries','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'8b084a5daf006a362c77997db8604daf19ceae38630f65f638bd427a01cd0b21'),
  ('erp.laundry_claims.opened_at','laundry_claims','opened_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'6c750412b1cf33416ba1520cc6edb0519767660f866ff9afeef038d3e1e73bb0'),
  ('erp.laundry_cost_accrual_events.created_at','laundry_cost_accrual_events','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'616a7fb8334528de16fcb5cc09dc4511eb688f0c95bd3b5ff5f97676452b46fb'),
  ('erp.laundry_cost_accrual_state.updated_at','laundry_cost_accrual_state','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'6c6fa700d10a67e88f2012d4d97aa1cce9602da0436c38923451a76ffd29800d'),
  ('erp.laundry_deliveries.created_at','laundry_deliveries','created_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'51b14dbe36eaa5a545da9d7ed1aaa0603c5b507597e4f74bd193670e8c57f42a'),
  ('erp.laundry_deliveries.updated_at','laundry_deliveries','updated_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'298b9571baa9cf76da105b75c3ff6afa0c03db8788a03a729c7b8ded614e0944'),
  ('erp.laundry_receipt_bs_product_allocations.created_at','laundry_receipt_bs_product_allocations','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'d5ddafde32205afac2b8c779084ee47ef4fbe3d312ebb19517e1738d88a51952'),
  ('erp.laundry_receipts.created_at','laundry_receipts','created_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'96a84881d76e801a5cbd17383c4d0cdeaed48eef4523f052212e65ab32c5d3fd'),
  ('erp.laundry_receipts.updated_at','laundry_receipts','updated_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'4c77d5d7adc52dd1eb7c1c7552494f9020e0ef1619a50a10cd60d430878d990f'),
  ('erp.laundry_vendor_rate_versions.effective_from','laundry_vendor_rate_versions','effective_from','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'7cc270470f420fbe15b3b898cb694188a6d6ba18561c7fdf1c025ea38d7854a9'),
  ('erp.laundry_vendor_rate_versions.created_at','laundry_vendor_rate_versions','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'2ea3847f689960f5e0311bdd183565771b6b12c13b340e9580d156fae2920422'),
  ('erp.laundry_vendors.created_at','laundry_vendors','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'93084029dfe5bfa35ce0c819b9e35b5a1701e5d1a05b4e60e37040e02f29bc8d'),
  ('erp.laundry_vendors.updated_at','laundry_vendors','updated_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'7a9b031f5fbc374f8008c23e5c47ea2b85e87bb037002e3240ebc5af1f8e6a68'),
  ('erp.locations.created_at','locations','created_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'9a7c4d272bc4c3b87abb6cf0dca713a154f96f6297f09e1e9b9a0411bbaeb1d7'),
  ('erp.material_adjustments.created_at','material_adjustments','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'eea9eca510de78bbd1ce14bd86fd01ba3111bd36b78589ce6c805d1814a2efbb'),
  ('erp.material_adjustments.updated_at','material_adjustments','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'b5f9c8a50736bf048170b33d6a559127f3ce28ca5e81057cd521236e07356567'),
  ('erp.material_cost_history.recorded_at','material_cost_history','recorded_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'ddbe9c00b4ba109db7f09d0afc79476c3930e8c2a38a1a584451c1102d9bf4e5'),
  ('erp.material_cost_revaluation_events.created_at','material_cost_revaluation_events','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'e631e7dca84931daa7ff325e2f7809ab6222e559d9023fdbe956840b9606eb00'),
  ('erp.material_cost_revaluation_state.updated_at','material_cost_revaluation_state','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'cf43ce948ed040b605fa160c4de15f4831a816baa07c46a8ba6596d0a969a82c'),
  ('erp.material_purchase_cost_corrections.created_at','material_purchase_cost_corrections','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres']::text[],true,'81b1c03d6909dda60c5704affef6b7103a8b071c174707ca933b03034eef1fae'),
  ('erp.material_purchase_headers.created_at','material_purchase_headers','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'2db469a30771c53e7d2347d1a6896be4a92d486b28ec8ac3ac4d0f4ae520fdad'),
  ('erp.material_purchase_headers.updated_at','material_purchase_headers','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'2fc20a08d858654b16e867be6a1543b2132e2d14492c1b4a54717f67bb691781'),
  ('erp.material_rolls.created_at','material_rolls','created_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'16bc91c115ce4281e5874b4ed3498068e0c8f3137a72970f447fc7ea13261385'),
  ('erp.material_rolls.updated_at','material_rolls','updated_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'31ae01be7b6f0b7237e3f706e3db9df185a06370d0e2821d4d5918ea6ec92249'),
  ('erp.material_supplier_returns.created_at','material_supplier_returns','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'d78dffc959e1a9d19516134f767c2dc75e0c8761c08cf40619a406a00b76861e'),
  ('erp.material_supplier_returns.updated_at','material_supplier_returns','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'b78dd75c38c55b721e44f95a0de7d44778e39f111295c0a03ec6b2ba31d758aa'),
  ('erp.material_transfer_items.created_at','material_transfer_items','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=r/postgres']::text[],true,'87da2bb250ecca75da022de801789b8ec0506c43960bacc60f133a2f742cc202'),
  ('erp.material_transfers.created_at','material_transfers','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=r/postgres']::text[],true,'7dab4236c60535b1b22278f6b22f4fa2bb711a0dc26c44479594fa62bb51c62e'),
  ('erp.material_transfers.updated_at','material_transfers','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=r/postgres']::text[],true,'99f0e8cb6854f1929d2620969b904810d7a9991496ae431fa0efb07f4fcb9600'),
  ('erp.materials.created_at','materials','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'7a4f2b6196a8a41a886cab7dd8874f75c9f5976ab7d188c95c6ce8b4461ae31a'),
  ('erp.materials.updated_at','materials','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'8423b5ae7976f32c6380218bf84f4bd0019a163803cebc7e50fe4185afd6d895'),
  ('erp.migration_batches.created_at','migration_batches','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'0cb7db32d60e9c5cf3818a09f7497e46266c363dd9f8f613f8e31a2fb98bcc3b'),
  ('erp.migration_staging_rows.created_at','migration_staging_rows','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'88525a86301457341b732aa6e2e8aa2c783b463fa46895ccdfa987e11f0165df'),
  ('erp.migration_staging_rows.updated_at','migration_staging_rows','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'166d54384f6fde4a49789647b9d1e24f6ea40bf2d13f8bd3c29f7db33a283bd1'),
  ('erp.misc_finance_transactions.created_at','misc_finance_transactions','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'862ab2bfd834ba15f26b313937a2c10c36026a8e94f6afe1b71689a26d804452'),
  ('erp.misc_finance_transactions.updated_at','misc_finance_transactions','updated_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'beff9932d7e8b1ae17f1bd6a641e2eae892f5b1a6c03016ce872efae20ed932a'),
  ('erp.opening_balance_headers.created_at','opening_balance_headers','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'da75b562014c628ee7fc38f483677b7c8ab33a3af792594642ed329de7f1fe44'),
  ('erp.opening_financial_corrections.created_at','opening_financial_corrections','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'ba2798124f9da166b7a51176018bd8c1eb938a887ce8aa19fd0d09473452e6c2'),
  ('erp.opening_hpp_corrections.created_at','opening_hpp_corrections','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'5823c94d404187a1e45cc1e8d8b6a42125d1079a627051ad4dee3c86bfa3df95'),
  ('erp.opening_lot_hpp_gl_state.updated_at','opening_lot_hpp_gl_state','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'0d03e6197255c92e2b08a8c6d106a392249de103012e1d48e533b32219408cd3'),
  ('erp.opening_subledger_balances.created_at','opening_subledger_balances','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres']::text[],true,'42328beb7bee19700516671b81ccc55390115ec92862ec7dd40b6957c2950056'),
  ('erp.opening_subledger_balances.updated_at','opening_subledger_balances','updated_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres']::text[],true,'9d0ca412fe466e0a188b4f113666483a9686b3349c25f744053f1289b8f31e64'),
  ('erp.opening_subledger_settlements.created_at','opening_subledger_settlements','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres']::text[],true,'d8262f4e714f49e4ad1a6669a02f639478f75d2c27ebb2c00edbd1dde2d5996b'),
  ('erp.opening_subledger_settlements.updated_at','opening_subledger_settlements','updated_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres']::text[],true,'f495894ba303f59c31933418a539bc43cdd6e82b743c1f69a63125f16c932f2f'),
  ('erp.payroll_settlements.created_at','payroll_settlements','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'e43dc192ba5fd1fd8b6e55c5f51b8bfcb279fb487530c7213da2991198111d9d'),
  ('erp.payroll_settlements.updated_at','payroll_settlements','updated_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'1a38a4ad710ba64f7bb8b74d973c38a4d4ae3049a4b41d498682fbb5629b1dd3'),
  ('erp.payroll_settlements.payment_date','payroll_settlements','payment_date','CURRENT_DATE','((statement_timestamp() AT TIME ZONE ''Asia/Jakarta''::text))::date','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'632052aa8135f354a9baa45b2582c72b19be36b8589c6b8601d1864334676f38'),
  ('erp.po_accessory_bom_commitments.created_at','po_accessory_bom_commitments','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'40ae9faf97d431da1e96fb98986299e31f1a409e10c87fc31ca5b81469c02091'),
  ('erp.po_hpp_gl_events.created_at','po_hpp_gl_events','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'b1ce4f469e8f0a2153c3f17e0f414bec54aff006ad925852ce53e760bd3a6f09'),
  ('erp.po_hpp_gl_state.updated_at','po_hpp_gl_state','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'6dbb3f53555729564c7d6b39f701855aee7f008a202c30ad063b3eec2fa88065'),
  ('erp.po_wip_close_events.created_at','po_wip_close_events','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres']::text[],true,'8284cf07a05aa515450861a0ebeb24b1f1d0d550918bf1d121a032be0df52312'),
  ('erp.po_work_component_snapshots.created_at','po_work_component_snapshots','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'6aa70c842548cee776ddb8ad8ae1be8f58495ef51613532b1d0bf85049db4acb'),
  ('erp.product_conversions.created_at','product_conversions','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'019582e9a81b05aa2e406b5b1454de3dc110111cd429997a6bd4c24373ab1d55'),
  ('erp.product_conversions.updated_at','product_conversions','updated_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'f6f7579cd393107bf93f65607a0c7ad93e2ef89ba175198414431ebef133cce3'),
  ('erp.product_models.created_at','product_models','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'304accbbbee9f7280f51c5d56208bf4783708a09da3b94be87f56b9070a553df'),
  ('erp.product_models.updated_at','product_models','updated_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'734489a8a90a93a2033964f9e4397abe527135d1d3c97bab8e1c50fa68c0e795'),
  ('erp.product_price_versions.effective_from','product_price_versions','effective_from','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'8c6523a1d601baf7fc0f4e9157723f4147c388e66ddbabfe3f1845554dc57bc2'),
  ('erp.product_price_versions.created_at','product_price_versions','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'441a7b8cf7c1f0f2dadde1d4e8846e47171051ad6019b494b0a3c1a32fa61566'),
  ('erp.production_orders.created_at','production_orders','created_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'2e95490a6cba3458d5beaed664c0aae58974473c78bdd6feecfc04924fccbbec'),
  ('erp.production_orders.updated_at','production_orders','updated_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'777669aeb49ca59fdaedc4ad1e92ca46f680a6547ae350f8a2bc7ca7a01a8e1c'),
  ('erp.products.created_at','products','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'8791615cf6d9a0887cccb9652662d003308876502f90f125cff568a98c5b4d4c'),
  ('erp.products.updated_at','products','updated_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'09ca4db80946d8e699a3ef1704afb9ea6bb718ecbb9b2eb01887c2ec68acbcfd'),
  ('erp.qc_inspections.created_at','qc_inspections','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'58ceddcab400a837cd93b5cd4ac79fa4fdc81da260d3e56dd4a564bef048688a'),
  ('erp.qc_inspections.updated_at','qc_inspections','updated_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'bc969a52ec144ee072f238ae9dd2d3d5e14f71e2c75a58c421d17070b68e0f49'),
  ('erp.rework_orders.created_at','rework_orders','created_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'16716fe832914c1f36c924a6e4004fecaa8bf8a4ac542f16cea7138139b1c4a3'),
  ('erp.rework_orders.updated_at','rework_orders','updated_at','now()','statement_timestamp()','postgres',array['postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'5ef6cc73531ab393f4b5453f75e426e7eff1d23d90832cfda5c37a3b84a0f758'),
  ('erp.sales_headers.created_at','sales_headers','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'e25844786c3165138512ebcca82a19c45762adf3bf118a177517a2ab3b7281c7'),
  ('erp.sales_headers.updated_at','sales_headers','updated_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'4cc34b10c228a487340c539a2cbd376ef757e948603d96c1db9526a07f4023ef'),
  ('erp.sales_payments.created_at','sales_payments','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'24bec99a6f236875e7e7375b1136b1b6ddee1468918b8d2877a07f1856a0d927'),
  ('erp.sales_returns.created_at','sales_returns','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'1604a99674ed2f869a0dece1d360f0931eb1c000c0c34566cd5932dcb6538b87'),
  ('erp.schema_migrations.installed_at','schema_migrations','installed_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'a95b0c9a712c7a360f0d47129bd6a3dfd55b7d0c23001102365ccdd70935608f'),
  ('erp.scrap_batches.created_at','scrap_batches','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'20b93d4d3dc815c93d1aa4009eb8efd3a8e0b8ba7ba6453a8510a7bc7936277f'),
  ('erp.scrap_sales.created_at','scrap_sales','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'a6fce7e38ed3cd816db608337875e77dbfa8266bfad112465fba8da543691a06'),
  ('erp.supplier_payments.created_at','supplier_payments','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'c0a1cf01f3270abf05d402b7bf96c4f107bb68eb23ccce982a3d67b107cd84d8'),
  ('erp.suppliers.created_at','suppliers','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'5a18d18c767e4006ab0e066710516c391545526a6358200ad879273666f53c3a'),
  ('erp.system_release_info.installed_at','system_release_info','installed_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'ee603ff682c8aa9fc648b4ab21c6aae4a3ec304ebaf94439dc1e5c7c254258a3'),
  ('erp.uom_definitions.created_at','uom_definitions','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'888d157aa6ac06f0f62a8a16133854eae1016043cff26d9257248b918a485317'),
  ('erp.vendor_invoices.received_at','vendor_invoices','received_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'a7618afe30ac2aa3787c7a35edc86fbb8bf399826d04d21f765e17f46690006c'),
  ('erp.vendor_invoices.created_at','vendor_invoices','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'992a5935d488ef6ebbeb00e0ee0164bc2c5533dab939c89ea2bb88ad33173d8e'),
  ('erp.vendor_invoices.updated_at','vendor_invoices','updated_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'78dc669ae5fdc1c161f13f37a9afc0dc324481cf8443eedc524c4fd381739e50'),
  ('erp.vendor_payments.created_at','vendor_payments','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'6c6b6ad887ac33c49539bed16eddcf1cdb8d65da2bbcbf5c635481965a90f861'),
  ('erp.wip_stage_events.created_at','wip_stage_events','created_at','now()','statement_timestamp()','postgres',array['authenticated=r/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'c9747d96feec69893578a2b5ccbc178a1e6ee75361c6bcbd4248ed55ad0f458c'),
  ('erp.work_bom_versions.effective_from','work_bom_versions','effective_from','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'a48724bd538eb7d05c62c9ee633aff5f5d69cade6f3d5051f45a999842851569'),
  ('erp.work_bom_versions.created_at','work_bom_versions','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'a0be12407c3ce3f25abd02c413bef236dc758fd2f2d4965f153e91a3d592e00e'),
  ('erp.work_completion_events.created_at','work_completion_events','created_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'03d3e69e0b7281b4074d14f6e1d9e573936a83098c3b06c1bb0305e6dcda993f'),
  ('erp.work_completion_events.updated_at','work_completion_events','updated_at','now()','statement_timestamp()','postgres',array['authenticated=arwd/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'b66d8daffb2da71134c7492f8e703c712549f787ccfe31574d5c6b5d965e005c'),
  ('erp.work_components.created_at','work_components','created_at','now()','statement_timestamp()','postgres',array['authenticated=arw/postgres','postgres=arwdDxtm/postgres','service_role=arwdDxtm/postgres']::text[],true,'8bf30cb49a2d9fe0cfbefd3e457e8aa8cc988b7b961505936a085cc2bc1f0e78');

create or replace function pg_temp.cp6_ac_normalized_view_sha256(p_body text)
returns text
language plpgsql
set search_path to pg_catalog
as $cp6_ac_view_probe$
declare v_sha256 text;
begin
  execute format('create temporary view cp6_ac_normalization_probe as %s',p_body);
  select encode(extensions.digest(convert_to(btrim(pg_get_viewdef(
    'pg_temp.cp6_ac_normalization_probe'::regclass,false),E' \n\t\r;'),
    'UTF8'),'sha256'),'hex') into v_sha256;
  execute 'drop view pg_temp.cp6_ac_normalization_probe';
  return v_sha256;
exception when others then
  execute 'drop view if exists pg_temp.cp6_ac_normalization_probe';
  raise;
end
$cp6_ac_view_probe$;


do $restore_v2620ac$
declare r record;c record;v_table text;v_hash text;v_expected jsonb;
  v_live_sha text;v_expected_sha text;v_expression text;v_owner text;
  v_acl text[];v_reloptions text[];v_rls boolean;
begin
  if (select count(*) from erp.schema_migrations where version='v2.6.20ac')<>1
     or (select count(*) from erp.schema_migrations where version='v2.6.20ab')<>1
     or (select count(*) from erp.cp6_v2620ac_rollback_capsule)<>115
     or (select count(*) from erp.cp6_v2620ac_relation_rollback_capsule)<>157 then
    raise exception 'AC_ROLLBACK_MARKER_OR_CAPSULE_MISMATCH';
  end if;

  for r in select * from pg_temp.cp6_ac_expected_functions loop
    select cap.*,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c from erp.cp6_v2620ac_rollback_capsule cap
    left join pg_proc p on p.oid=to_regprocedure(cap.object_regidentity)
    where cap.object_regidentity=r.identity;
    if c.definition_sha256 is distinct from r.before_sha256
       or c.definition_actual is distinct from r.before_sha256
       or c.installed_definition_sha256 is distinct from r.after_sha256
       or c.installed_actual is distinct from r.after_sha256
       or c.owner_snapshot is distinct from r.owner_name
       or c.installed_owner is distinct from r.owner_name
       or c.acl_snapshot is distinct from r.acl
       or c.installed_acl is distinct from r.acl then
      raise exception 'AC_ROLLBACK_FUNCTION_GUARD: %',r.identity;
    end if;
  end loop;

  for r in select * from pg_temp.cp6_ac_expected_views loop
    select cap.* into c from erp.cp6_v2620ac_relation_rollback_capsule cap
      where cap.object_kind='VIEW' and cap.object_identity=r.identity;
    v_expected_sha:=pg_temp.cp6_ac_normalized_view_sha256(r.after_body);
    select encode(extensions.digest(convert_to(btrim(pg_get_viewdef(v.oid,false),E' \n\t\r;'),'UTF8'),'sha256'),'hex'),
      pg_get_userbyid(v.relowner),
      case when v.relacl is null then null else
        array(select x::text from unnest(v.relacl) x order by x::text) end,
      case when v.reloptions is null then null else
        array(select x from unnest(v.reloptions) x order by x) end,
      v.relrowsecurity
    into v_live_sha,v_owner,v_acl,v_reloptions,v_rls
    from pg_class v where v.oid=r.identity::regclass and v.relkind='v';
    if encode(extensions.digest(convert_to(r.before_body,'UTF8'),'sha256'),'hex')
         is distinct from r.before_sha256
       or encode(extensions.digest(convert_to(r.after_body,'UTF8'),'sha256'),'hex')
         is distinct from r.after_sha256
       or c.definition_sha256 is distinct from r.before_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),
         'sha256'),'hex') is distinct from r.restore_sha256
       or c.installed_definition_sha256 is distinct from v_live_sha
       or v_live_sha is distinct from v_expected_sha
       or c.owner_snapshot is distinct from r.owner_name
       or c.acl_snapshot is distinct from r.acl
       or c.reloptions_snapshot is distinct from r.reloptions
       or c.rls_snapshot is distinct from r.rls
       or v_owner is distinct from r.owner_name
       or v_acl is distinct from r.acl
       or v_reloptions is distinct from r.reloptions
       or v_rls is distinct from r.rls then
      raise exception 'AC_ROLLBACK_VIEW_GUARD: %',r.identity;
    end if;
  end loop;

  for r in select * from pg_temp.cp6_ac_expected_defaults loop
    select cap.* into c from erp.cp6_v2620ac_relation_rollback_capsule cap
      where cap.object_kind='COLUMN_DEFAULT' and cap.object_identity=r.identity;
    select pg_get_expr(d.adbin,d.adrelid),pg_get_userbyid(t.relowner),
      case when t.relacl is null then null else
        array(select x::text from unnest(t.relacl) x order by x::text) end,
      t.relrowsecurity
    into v_expression,v_owner,v_acl,v_rls
    from pg_class t join pg_namespace n on n.oid=t.relnamespace
    join pg_attribute a on a.attrelid=t.oid and a.attname=r.column_name
    left join pg_attrdef d on d.adrelid=t.oid and d.adnum=a.attnum
    where n.nspname='erp' and t.relname=r.table_name and t.relkind in('r','p');
    if c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(r.before_expression,'UTF8'),'sha256'),'hex')
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),
         'sha256'),'hex') is distinct from r.restore_sha256
       or c.installed_definition_sha256 is distinct from encode(extensions.digest(
         convert_to(r.after_expression,'UTF8'),'sha256'),'hex')
       or v_expression is distinct from r.after_expression
       or c.owner_snapshot is distinct from r.owner_name
       or c.acl_snapshot is distinct from r.acl
       or c.rls_snapshot is distinct from r.rls
       or v_owner is distinct from r.owner_name
       or v_acl is distinct from r.acl
       or v_rls is distinct from r.rls then
      raise exception 'AC_ROLLBACK_DEFAULT_GUARD: %',r.identity;
    end if;
  end loop;

  select boundary_snapshot into v_expected from erp.cp6_v2620ac_rollback_capsule limit 1;
  if v_expected is null or (select count(*) from jsonb_object_keys(v_expected))<>214
     or (select count(*) from pg_class rel join pg_namespace n on n.oid=rel.relnamespace
         where n.nspname='erp' and rel.relkind in('r','p')
           and rel.relname not in('schema_migrations','cp6_v2620ac_rollback_capsule',
             'cp6_v2620ac_relation_rollback_capsule'))<>214
     or exists(select 1 from erp.cp6_v2620ac_rollback_capsule where boundary_snapshot is distinct from v_expected) then
    raise exception 'AC_ROLLBACK_BOUNDARY_CAPSULE_MISMATCH';
  end if;
  for v_table in select rel.relname from pg_class rel join pg_namespace n on n.oid=rel.relnamespace
    where n.nspname='erp' and rel.relkind in('r','p')
      and rel.relname not in('schema_migrations','cp6_v2620ac_rollback_capsule',
        'cp6_v2620ac_relation_rollback_capsule') order by rel.relname
  loop
    execute format($q$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$q$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'AC_POST_USE_ROLLBACK_REFUSED: %',v_table;
    end if;
  end loop;

  for c in select * from erp.cp6_v2620ac_rollback_capsule order by object_regidentity loop
    execute c.object_definition;
  end loop;
  for c in select * from erp.cp6_v2620ac_relation_rollback_capsule where object_kind='VIEW'
    order by object_identity loop
    execute c.object_definition;
  end loop;
  for c in select * from erp.cp6_v2620ac_relation_rollback_capsule where object_kind='COLUMN_DEFAULT'
    order by object_identity loop
    execute c.object_definition;
  end loop;

  for r in select * from pg_temp.cp6_ac_expected_functions loop
    if encode(extensions.digest(convert_to(pg_get_functiondef(
        to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.before_sha256 then
      raise exception 'AC_ROLLBACK_FUNCTION_RESTORE_MISMATCH: %',r.identity;
    end if;
  end loop;
  for r in select * from pg_temp.cp6_ac_expected_views loop
    v_expected_sha:=pg_temp.cp6_ac_normalized_view_sha256(r.before_body);
    select encode(extensions.digest(convert_to(btrim(pg_get_viewdef(v.oid,false),E' \n\t\r;'),'UTF8'),'sha256'),'hex')
    into v_live_sha from pg_class v
      where v.oid=r.identity::regclass and v.relkind='v';
    if v_live_sha is distinct from v_expected_sha then
      raise exception 'AC_ROLLBACK_VIEW_RESTORE_MISMATCH: %',r.identity;
    end if;
  end loop;
  for r in select * from pg_temp.cp6_ac_expected_defaults loop
    select pg_get_expr(d.adbin,d.adrelid),pg_get_userbyid(t.relowner),
      case when t.relacl is null then null else
        array(select x::text from unnest(t.relacl) x order by x::text) end,
      t.relrowsecurity
    into v_expression,v_owner,v_acl,v_rls
    from pg_class t join pg_namespace n on n.oid=t.relnamespace
    join pg_attribute a on a.attrelid=t.oid and a.attname=r.column_name
    left join pg_attrdef d on d.adrelid=t.oid and d.adnum=a.attnum
    where n.nspname='erp' and t.relname=r.table_name;
    if v_expression is distinct from r.before_expression
       or v_owner is distinct from r.owner_name
       or v_acl is distinct from r.acl
       or v_rls is distinct from r.rls then
      raise exception 'AC_ROLLBACK_DEFAULT_RESTORE_MISMATCH: %',r.identity;
    end if;
  end loop;
end
$restore_v2620ac$;

drop table erp.cp6_v2620ac_relation_rollback_capsule;
drop table erp.cp6_v2620ac_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20ac';
delete from supabase_migrations.schema_migrations
where version='20260915031500' and name='erp_v2_6_20ac_cp6_temporal_surface_closure'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
    in('9645ae6a2f80c364b3c51ef34747f6dbe313f661a3d2f9fd0b696026832b5555','7d2b7fded027a41113a07a7dcb718672e446e2062862b9be0377ebcb1d522131');

do $postcheck_v2620ac$
begin
  if exists(select 1 from erp.schema_migrations where version='v2.6.20ac')
     or exists(select 1 from supabase_migrations.schema_migrations where name='erp_v2_6_20ac_cp6_temporal_surface_closure')
     or to_regclass('erp.cp6_v2620ac_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620ac_relation_rollback_capsule') is not null
     or (select count(*) from erp.schema_migrations where version='v2.6.20ab')<>1
     or (select count(*) from erp.cp6_v2620ab_rollback_capsule)<>5 then
    raise exception 'AC_ROLLBACK_POSTCONDITION_FAILED';
  end if;
end
$postcheck_v2620ac$;
commit;
