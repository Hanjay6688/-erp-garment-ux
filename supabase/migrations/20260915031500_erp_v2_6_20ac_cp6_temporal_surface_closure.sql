-- CP6 AC: complete classified temporal surface closure.
-- 208/208 open hits resolved plus 216 transaction-clock metadata hardenings.
-- Total reviewed: 709; changes: 422; retained: 285; two date-only exclusions.
-- Evidence SHA-256: 28c39de13bfb8707cd518207d369eab57f4b90d51308517e83f581236db22576
-- AB SQL remains immutable. production_go:false.
begin;
set local lock_timeout='10s';
set local statement_timeout='360s';
set local timezone='UTC';
set local search_path='pg_catalog';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;

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
  WHERE (is_active = true)','3c65f5daf0201efb3a1c4084c1c322c2fac7563f09aeddf222a3ceba772c9d5f','postgres',array['authenticated=r/postgres','postgres=arwdDxt/postgres','service_role=arwdDxt/postgres']::text[],array['security_invoker=true']::text[],false,'d789c6407e1b123a76af390e58f97856daf4c7d5d4fb1615d40c13bc45aee9c6'),
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
     LEFT JOIN erp.accessory_categories ac ON ((ac.id = abi.category_id)))','0ffbf3ab054353a4e4f765acb1bc2adb2e84eef5cab4cc15ece28fd355e9d062','postgres',array['authenticated=r/postgres','postgres=arwdDxt/postgres','service_role=arwdDxt/postgres']::text[],array['security_invoker=true']::text[],false,'9a68930724dcce7a56fae5130bf256e1f8dcd8e5e091a3b0717f9f6f2792a787'),
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
  WHERE ((m.material_type)::text = ''ACCESSORY''::text)','45d7858bb4c0650fa8c07810c6db0b0b219ade8981c26cbcf62ad078ca6be1ef','postgres',array['authenticated=r/postgres','postgres=arwdDxt/postgres']::text[],array['security_invoker=true']::text[],false,'abfc66c807a59209a8f9bec176b1d7b72f96917c3c548ba688d8e4e5556f66c3'),
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
     LEFT JOIN erp.contractors c ON ((c.id = p.contractor_id)))','c6bd9e3d74accfb969b82adeaf33ad8e0f6207095576100052c1a76cafef176d','postgres',array['authenticated=r/postgres','postgres=arwdDxt/postgres']::text[],array['security_invoker=true']::text[],false,'1ca1a0f6e59f22d8e04816ce7cce4e0f9cfc785417104960a0818238f94f710f'),
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
  ORDER BY product_id, effective_from DESC, created_at DESC','3610e705fd0bd193945dd8a8241d8b1706a536ecdaa567c4bdd8adc6f58e3e12','postgres',array['authenticated=r/postgres','postgres=arwdDxt/postgres','service_role=arwdDxt/postgres']::text[],array['security_invoker=true']::text[],false,'8b10d8668e05b36209e14e4f00965b244cd406628fafd8b4a5f2eae89a71e46f'),
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
  WHERE ((m.material_type)::text = ''FABRIC''::text)','c194577448dbfdfbeabec3219a328c4c1e6826c83223395bb8716e285dd246b6','postgres',array['authenticated=r/postgres','postgres=arwdDxt/postgres']::text[],array['security_invoker=true']::text[],false,'c93e807d0f0b44b052c2413c5a4632564b604c5b702f45d9c7d75a5cc30d13d0'),
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
  GROUP BY h.id, s.id','d0a42f5eb48da1e91534a43a7e1aa4ebeda6894805e86659880fe8603d2304f9','postgres',array['authenticated=r/postgres','postgres=arwdDxt/postgres']::text[],array['security_invoker=true']::text[],false,'c49b2bc36cd0d84ccff7384631a9f75ee69ea8f4db3f404f749b8f32149dc140'),
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
  GROUP BY h.id, s.id','aed6fdcc147d2f379a31b2c3db4a5fdc78f98be5c8ee700f0871e9096a198c71','postgres',array['authenticated=r/postgres','postgres=arwdDxt/postgres']::text[],array['security_invoker=true']::text[],false,'50d32d01f3455eb5e94003bb920ca3e5bd5f6f586fbb690510f465b03d6a245c'),
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
          WHERE ((q.contractor_id = n.contractor_id) AND (((q.eligible_at) AT TIME ZONE ''Asia/Jakarta'')::date <= n.period_end))) e ON (true))','16f47474d81b89b0639a3c46cd49c90140691926e4cc03d610e493b1677ca226','postgres',array['authenticated=r/postgres','postgres=arwdDxt/postgres']::text[],array['security_invoker=true']::text[],false,'278040c49bd65164dec4e31948cb910127704bf6072c0b801147270a57567989'),
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
  WHERE ((payable_amount > 0.005) OR (paid_amount > 0.005))','e78b3217d9b8ec92f1eec54758c85bbb0216935d0334bcfdce476ad530700a67','postgres',array['authenticated=r/postgres','postgres=arwdDxt/postgres']::text[],array['security_invoker=true']::text[],false,'0fc6adaf1402343b9dc5a598bcdfea318ff67fea4e8a2a493b0c6f58d014db25');

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


do $predecessor_v2620ac$
declare r record;c record;v_live_sha text;v_expected_sha text;v_owner text;
  v_acl text[];v_reloptions text[];v_expression text;v_rls boolean;
begin
  if (select count(*) from erp.schema_migrations where version='v2.6.20ab')<>1
     or exists(select 1 from erp.schema_migrations where version='v2.6.20ac')
     or to_regclass('erp.cp6_v2620ac_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620ac_relation_rollback_capsule') is not null
     or (select count(*) from supabase_migrations.schema_migrations
         where name='erp_v2_6_20ab_cp6_operational_business_clock')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260914190500' and name='erp_v2_6_20ab_cp6_operational_business_clock'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
             in('7b31f000b3ca89f4bc776d93f3211f39dce5adbc73445291b9c0e0268f2d7fe3','8e12af37b972bea6043f6ea83f06f495c669e11647042918bfa822cfe250b757'))
     or exists(select 1 from supabase_migrations.schema_migrations
       where version>'20260914190500')
     or (select count(*) from erp.cp6_v2620ab_rollback_capsule)<>5 then
    raise exception 'AC_REQUIRES_EXACT_AB_WITHOUT_SUCCESSOR_RESIDUE';
  end if;

  for r in select * from(values
    ('erp.sync_material_cost_revaluation(uuid)','af752a5cb068d71af90c646718b55ef2b6eabd9319021202a0d8f92042892f91',array['postgres=X/postgres']::text[]),
  ('erp.process_cost_recalc_queue(integer)','7fe85b6739fa5684171cffd26d028eabd35efe3bb2691e2daa9e52cf40892a13',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
  ('erp.resolve_accounting_transaction_date(date)','656ac4cd3ae6a2df24bd11f4c1c044c3e9bf423cc6c7343ab863bad16eee6803',array['postgres=X/postgres']::text[]),
  ('erp._cp3_r4_reverse_journal_internal(uuid,text)','2996d1c16396768097306556b5916ba93996d2ff451f3c5e7cd35deea7a3ac6f',array['postgres=X/postgres']::text[]),
  ('erp.post_journal(text,uuid,date,text,jsonb)','0a84003a5e6a27cc445e835673d4f5030cbc19cb6b130037eaed922340d34d77',array['postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,installed_sha256,acl) loop
    select cap.*,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c from erp.cp6_v2620ab_rollback_capsule cap
    left join pg_proc p on p.oid=to_regprocedure(cap.object_regidentity)
    where cap.object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_actual is distinct from c.definition_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.installed_actual is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres'
       or c.installed_owner is distinct from 'postgres'
       or c.acl_snapshot is distinct from r.acl
       or c.installed_acl is distinct from r.acl then
      raise exception 'AC_TRUSTED_AB_CAPSULE_MISMATCH: %',r.identity;
    end if;
  end loop;

  for r in select * from pg_temp.cp6_ac_expected_functions loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') sha256,
      pg_get_userbyid(p.proowner) owner_name,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end acl
    into c from pg_proc p where p.oid=to_regprocedure(r.identity);
    if c.sha256 is distinct from r.before_sha256
       or c.owner_name is distinct from r.owner_name
       or c.acl is distinct from r.acl then
      raise exception 'AC_FUNCTION_PREDECESSOR_MISMATCH: %',r.identity;
    end if;
  end loop;

  for r in select * from pg_temp.cp6_ac_expected_views loop
    v_expected_sha:=pg_temp.cp6_ac_normalized_view_sha256(r.before_body);
    select encode(extensions.digest(convert_to(btrim(pg_get_viewdef(catalog_rel.oid,false),E' \n\t\r;'),'UTF8'),'sha256'),'hex'),
      pg_get_userbyid(catalog_rel.relowner),
      case when catalog_rel.relacl is null then null else
        array(select a::text from unnest(catalog_rel.relacl) a order by a::text) end,
      case when catalog_rel.reloptions is null then null else
        array(select x from unnest(catalog_rel.reloptions) x order by x) end,
      catalog_rel.relrowsecurity
    into v_live_sha,v_owner,v_acl,v_reloptions,v_rls
    from pg_class catalog_rel
    where catalog_rel.oid=r.identity::regclass and catalog_rel.relkind='v';
    if encode(extensions.digest(convert_to(r.before_body,'UTF8'),'sha256'),'hex')
         is distinct from r.before_sha256
       or v_live_sha is distinct from v_expected_sha
       or v_owner is distinct from r.owner_name
       or v_acl is distinct from r.acl
       or v_reloptions is distinct from r.reloptions
       or v_rls is distinct from r.rls then
      raise exception 'AC_VIEW_PREDECESSOR_MISMATCH: %',r.identity using detail=format(
        'source=%s body=%s owner=%s acl=%s options=%s rls=%s',
        encode(extensions.digest(convert_to(r.before_body,'UTF8'),'sha256'),'hex')
          is not distinct from r.before_sha256,
        v_live_sha is not distinct from v_expected_sha,
        v_owner is not distinct from r.owner_name,
        v_acl is not distinct from r.acl,
        v_reloptions is not distinct from r.reloptions,
        v_rls is not distinct from r.rls);
    end if;
  end loop;

  for r in select * from pg_temp.cp6_ac_expected_defaults loop
    select pg_get_expr(d.adbin,d.adrelid),pg_get_userbyid(catalog_rel.relowner),
      case when catalog_rel.relacl is null then null else
        array(select x::text from unnest(catalog_rel.relacl) x order by x::text) end,
      catalog_rel.relrowsecurity
    into v_expression,v_owner,v_acl,v_rls
    from pg_class catalog_rel
    join pg_namespace n on n.oid=catalog_rel.relnamespace
    join pg_attribute a on a.attrelid=catalog_rel.oid and a.attname=r.column_name
    left join pg_attrdef d on d.adrelid=catalog_rel.oid and d.adnum=a.attnum
    where n.nspname='erp' and catalog_rel.relname=r.table_name
      and catalog_rel.relkind in('r','p');
    if v_expression is distinct from r.before_expression
       or v_owner is distinct from r.owner_name
       or v_acl is distinct from r.acl
       or v_rls is distinct from r.rls then
      raise exception 'AC_DEFAULT_PREDECESSOR_MISMATCH: %',r.identity;
    end if;
  end loop;
end
$predecessor_v2620ac$;


create table erp.cp6_v2620ac_rollback_capsule(
  like erp.cp6_v2620ab_rollback_capsule including all
);
alter table erp.cp6_v2620ac_rollback_capsule owner to postgres;
alter table erp.cp6_v2620ac_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620ac_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620ac_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,
  acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,
    pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else
    array(select a::text from unnest(p.proacl) a order by a::text) end,
  pg_get_userbyid(p.proowner)
from pg_temp.cp6_ac_expected_functions e
join pg_proc p on p.oid=to_regprocedure(e.identity)
join pg_namespace n on n.oid=p.pronamespace;

create table erp.cp6_v2620ac_relation_rollback_capsule(
  object_kind text not null check(object_kind in('VIEW','COLUMN_DEFAULT')),
  object_identity text primary key,
  object_definition text not null,
  definition_sha256 text not null,
  installed_definition_sha256 text,
  acl_snapshot text[],
  owner_snapshot text not null,
  reloptions_snapshot text[],
  rls_snapshot boolean not null,
  captured_at timestamptz not null default clock_timestamp()
);
alter table erp.cp6_v2620ac_relation_rollback_capsule owner to postgres;
alter table erp.cp6_v2620ac_relation_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620ac_relation_rollback_capsule from public,anon,authenticated,service_role;

insert into erp.cp6_v2620ac_relation_rollback_capsule(
  object_kind,object_identity,object_definition,definition_sha256,
  acl_snapshot,owner_snapshot,reloptions_snapshot,rls_snapshot
)
select 'VIEW',e.identity,
  format('CREATE OR REPLACE VIEW %s%s AS%s%s;',e.identity,
    case when e.reloptions is null then '' else
      ' WITH ('||array_to_string(e.reloptions,',')||')' end,E'\n',e.before_body),
  encode(extensions.digest(convert_to(e.before_body,'UTF8'),'sha256'),'hex'),
  case when c.relacl is null then null else
    array(select a::text from unnest(c.relacl) a order by a::text) end,
  pg_get_userbyid(c.relowner),
  case when c.reloptions is null then null else
    array(select x from unnest(c.reloptions) x order by x) end,
  c.relrowsecurity
from pg_temp.cp6_ac_expected_views e
join pg_class c on c.oid=e.identity::regclass and c.relkind='v';

insert into erp.cp6_v2620ac_relation_rollback_capsule(
  object_kind,object_identity,object_definition,definition_sha256,
  acl_snapshot,owner_snapshot,reloptions_snapshot,rls_snapshot
)
select 'COLUMN_DEFAULT',e.identity,
  format('ALTER TABLE erp.%I ALTER COLUMN %I SET DEFAULT %s;',
    e.table_name,e.column_name,pg_get_expr(d.adbin,d.adrelid)),
  encode(extensions.digest(convert_to(pg_get_expr(d.adbin,d.adrelid),'UTF8'),'sha256'),'hex'),
  case when c.relacl is null then null else
    array(select a::text from unnest(c.relacl) a order by a::text) end,
  pg_get_userbyid(c.relowner),null,c.relrowsecurity
from pg_temp.cp6_ac_expected_defaults e
join pg_class c on c.relname=e.table_name
join pg_namespace n on n.oid=c.relnamespace and n.nspname='erp'
join pg_attribute a on a.attrelid=c.oid and a.attname=e.column_name
join pg_attrdef d on d.adrelid=c.oid and d.adnum=a.attnum;

do $capsule_v2620ac$
begin
  if (select count(*) from erp.cp6_v2620ac_rollback_capsule)<>115
     or (select count(*) from erp.cp6_v2620ac_relation_rollback_capsule where object_kind='VIEW')<>13
     or (select count(*) from erp.cp6_v2620ac_relation_rollback_capsule where object_kind='COLUMN_DEFAULT')<>144
     or exists(
       select 1 from erp.cp6_v2620ac_relation_rollback_capsule cap
       join pg_temp.cp6_ac_expected_views e on e.identity=cap.object_identity
       where cap.object_kind='VIEW'
         and (cap.definition_sha256 is distinct from e.before_sha256
           or encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),
             'sha256'),'hex') is distinct from e.restore_sha256
           or cap.owner_snapshot is distinct from e.owner_name
           or cap.acl_snapshot is distinct from e.acl
           or cap.reloptions_snapshot is distinct from e.reloptions
           or cap.rls_snapshot is distinct from e.rls)
     )
     or exists(
       select 1 from erp.cp6_v2620ac_relation_rollback_capsule cap
       join pg_temp.cp6_ac_expected_defaults e on e.identity=cap.object_identity
       where cap.object_kind='COLUMN_DEFAULT'
         and (cap.definition_sha256 is distinct from encode(extensions.digest(
             convert_to(e.before_expression,'UTF8'),'sha256'),'hex')
           or encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),
             'sha256'),'hex') is distinct from e.restore_sha256
           or cap.owner_snapshot is distinct from e.owner_name
           or cap.acl_snapshot is distinct from e.acl
           or cap.reloptions_snapshot is not null
           or cap.rls_snapshot is distinct from e.rls)
     ) then
    raise exception 'AC_CAPSULE_CARDINALITY_MISMATCH';
  end if;
end
$capsule_v2620ac$;


-- Generated only from the 709/709 reviewed disposition; do not hand-edit.
CREATE OR REPLACE FUNCTION erp._cp6_apply_supplier_cent_event(p_source text, p_id uuid, p_date date, p_description text, p_before jsonb, p_reverse boolean DEFAULT false)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'pg_catalog', 'pg_temp'
AS $function$
declare
 v_purchases uuid[];v_after jsonb;v_ap numeric;v_grni numeric;v_inventory numeric;
 v_expected jsonb;v_adjust jsonb;v_lines jsonb;v_original uuid;v_journal uuid;v_adjustment uuid;
 v_fact erp.supplier_cent_posting_facts%rowtype;v_status text;v_phase text;
begin
 perform erp.require_internal();
 v_phase:=case when p_reverse then 'REVERSE' else 'POST' end;
 if p_source='MATERIAL_PURCHASE_COST_CORRECTION' then
  select array[h.purchase_id],h.status into v_purchases,v_status from erp.material_purchase_cost_corrections h where h.id=p_id;
 elsif p_source='MATERIAL_SUPPLIER_INVOICE' then
  select array_agg(distinct i.purchase_id order by i.purchase_id),h.status into v_purchases,v_status
  from erp.material_supplier_invoices h join erp.material_supplier_invoice_lines l on l.invoice_id=h.id
  join erp.material_purchase_items i on i.id=l.purchase_item_id where h.id=p_id group by h.status;
 elsif p_source='MATERIAL_SUPPLIER_RETURN' then
  select array_agg(distinct i.purchase_id order by i.purchase_id),h.status into v_purchases,v_status
  from erp.material_supplier_returns h join erp.material_supplier_return_items l on l.return_id=h.id
  join erp.material_purchase_items i on i.id=l.purchase_item_id where h.id=p_id group by h.status;
 else raise exception 'N_UNSUPPORTED_SUPPLIER_CENT_SOURCE';end if;
 if v_status is distinct from (case when p_reverse then 'REVERSED' else 'POSTED' end)
   or v_purchases is null or jsonb_typeof(p_before) is distinct from 'object'
   or (select array_agg(key::uuid order by key::uuid) from jsonb_object_keys(p_before) key) is distinct from v_purchases then
  raise exception 'N_SUPPLIER_CENT_SOURCE_STATE_MISMATCH';end if;
 v_after:=erp._cp6_supplier_cent_state(v_purchases);
 if (select count(*) from jsonb_object_keys(v_after))<>cardinality(v_purchases) then
  raise exception 'N_SUPPLIER_CENT_PURCHASE_STATE_MISMATCH';end if;
 select sum((a.value->>'ap')::numeric-(b.value->>'ap')::numeric),
  sum((a.value->>'grni')::numeric-(b.value->>'grni')::numeric),
  sum((a.value->>'inventory')::numeric-(b.value->>'inventory')::numeric)
 into v_ap,v_grni,v_inventory
 from jsonb_each(v_after) a join jsonb_each(p_before) b using(key);
 if v_ap::text in('NaN','Infinity','-Infinity') or v_grni::text in('NaN','Infinity','-Infinity')
   or v_inventory::text in('NaN','Infinity','-Infinity') then raise exception 'N_NONFINITE_SUPPLIER_CENT_DELTA';end if;
 select coalesce(jsonb_object_agg(account_id::text,amount),'{}') into v_expected from(
  select erp.account_id(mapping) account_id,sum(amount) amount from(values
   ('AP_SUPPLIER',-v_ap),('GRNI_MATERIAL',-v_grni),
   ('MATERIAL_INVENTORY',v_inventory),('MATERIAL_PURCHASE_VARIANCE',v_ap+v_grni-v_inventory)
  ) d(mapping,amount) group by erp.account_id(mapping) having sum(amount)<>0
 ) net;
 v_adjust:=v_expected;
 if p_reverse then
  select * into v_fact from erp.supplier_cent_posting_facts
  where source_type=p_source and source_id=p_id and phase='POST' for update;
  select id into v_original from erp.journal_entries where source_type=p_source and source_id=p_id and status='POSTED';
  if v_fact.source_id is not null and (v_original is distinct from v_fact.journal_entry_id
    or erp._cp6_supplier_cent_ledger(array[v_original]) is distinct from v_fact.ledger_delta) then
   raise exception 'N_SUPPLIER_CENT_ORIGINAL_JOURNAL_DRIFT';end if;
  if v_original is not null then
   v_journal:=erp.reverse_journal(v_original,p_description);
   select coalesce(jsonb_object_agg(k,amount),'{}') into v_adjust from(
    select coalesce(e.key,a.key) k,coalesce(e.value::numeric,0)-coalesce(a.value::numeric,0) amount
    from jsonb_each_text(v_expected) e full join jsonb_each_text(erp._cp6_supplier_cent_ledger(array[v_journal])) a using(key)
   ) d where amount<>0;
  end if;
 end if;
 select coalesce(jsonb_agg(jsonb_build_object('account_id',key::uuid,
  'debit',greatest(value::numeric,0),'credit',greatest(-value::numeric,0)) order by key),'[]')
 into v_lines from jsonb_each_text(v_adjust);
 if jsonb_array_length(v_lines)>0 then
  if p_reverse then
   v_adjustment:=erp.post_journal('CENT_INVERSE:'||p_source,p_id,
    coalesce((select economic_date from erp.journal_entries where id=v_journal),((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date),
    'Linked cumulative-cent adjustment: '||p_description,v_lines);
  else
   v_journal:=erp.post_journal(p_source,p_id,p_date,p_description,v_lines);
  end if;
 end if;
 insert into erp.supplier_cent_posting_facts(source_type,source_id,phase,before_state,after_state,
  ledger_delta,journal_entry_id,adjustment_journal_entry_id,legacy_original)
 values(p_source,p_id,v_phase,p_before,v_after,v_expected,v_journal,v_adjustment,p_reverse and v_fact.source_id is null);
 if erp._cp6_supplier_cent_ledger(array[v_journal,v_adjustment]) is distinct from v_expected then
  raise exception 'N_SUPPLIER_CENT_POSTCONDITION_FAILED';end if;
end;
$function$;

CREATE OR REPLACE FUNCTION erp._cp6_sync_material_adjustment_revaluation(p_adjustment uuid, p_material uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'pg_catalog', 'pg_temp'
AS $function$
declare s jsonb;v_delta jsonb;v_lines jsonb;v_event uuid;v_journal uuid;v_date date;
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
 v_event:=gen_random_uuid();v_date:=erp._cp3_business_date(statement_timestamp());
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

CREATE OR REPLACE FUNCTION erp._idempotency_complete(p_operation_name text, p_client_request_id uuid, p_response jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_actor text := erp._idempotency_actor_key();
begin
  update erp.idempotency_requests
  set status = 'COMPLETED', response_payload = p_response, updated_at = statement_timestamp()
  where actor_key = v_actor
    and operation_name = p_operation_name
    and client_request_id = p_client_request_id
    and status = 'IN_PROGRESS';
  if not found then
    raise exception 'Idempotency request is missing or already completed';
  end if;
  return p_response;
end;
$function$;

CREATE OR REPLACE FUNCTION erp._post_cutting_qty_correction(p_cutting_batch_id uuid, p_correction_type text, p_reason_code text, p_reason text, p_lines jsonb, p_physical_at timestamp with time zone, p_reversal_of_id uuid DEFAULT NULL::uuid)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
DECLARE
  v_id uuid;
  v_po_id uuid;
  v_number text;
  v_total_delta bigint;
  v_line_count integer;
  v_current bigint;
  v_committed bigint;
  v_new bigint;
  v_group_batch uuid;
  r record;
BEGIN
  PERFORM erp.require_internal();

  SELECT po_id INTO v_po_id
  FROM erp.cutting_batches
  WHERE id=p_cutting_batch_id
  FOR UPDATE;
  IF v_po_id IS NULL THEN
    RAISE EXCEPTION 'Cutting batch not found';
  END IF;

  IF p_correction_type NOT IN ('RECOUNT','REDISTRIBUTION','REVERSAL','OTHER') THEN
    RAISE EXCEPTION 'Invalid cutting correction type';
  END IF;
  IF COALESCE(btrim(p_reason_code),'')='' OR COALESCE(btrim(p_reason),'')='' THEN
    RAISE EXCEPTION 'Correction reason code and reason are required';
  END IF;
  IF jsonb_typeof(p_lines) <> 'array' OR jsonb_array_length(p_lines)=0 THEN
    RAISE EXCEPTION 'Correction requires at least one line';
  END IF;

  IF p_reversal_of_id IS NULL AND p_correction_type='REVERSAL' THEN
    RAISE EXCEPTION 'REVERSAL requires a source correction';
  END IF;
  IF p_reversal_of_id IS NOT NULL THEN
    IF p_correction_type <> 'REVERSAL' THEN
      RAISE EXCEPTION 'reversal_of_id is only valid for REVERSAL';
    END IF;
    IF NOT EXISTS (
      SELECT 1 FROM erp.cutting_qty_corrections c
      WHERE c.id=p_reversal_of_id AND c.cutting_batch_id=p_cutting_batch_id
    ) THEN
      RAISE EXCEPTION 'Source correction not found in this cutting batch';
    END IF;
    IF EXISTS (SELECT 1 FROM erp.cutting_qty_corrections c WHERE c.reversal_of_id=p_reversal_of_id) THEN
      RAISE EXCEPTION 'Correction has already been reversed';
    END IF;
  END IF;

  WITH parsed AS (
    SELECT
      NULLIF(x->>'cutting_group_id','')::uuid AS group_id,
      NULLIF(x->>'size_slot_id','')::uuid AS size_slot_id,
      (x->>'qty_delta_pcs')::integer AS delta
    FROM jsonb_array_elements(p_lines) x
  )
  SELECT COALESCE(SUM(delta),0)::bigint, COUNT(*)::integer
  INTO v_total_delta,v_line_count
  FROM parsed
  WHERE group_id IS NOT NULL AND delta <> 0;

  IF v_line_count=0 THEN
    RAISE EXCEPTION 'Correction contains no valid non-zero lines';
  END IF;
  IF p_correction_type='REDISTRIBUTION' AND v_total_delta<>0 THEN
    RAISE EXCEPTION 'REDISTRIBUTION must net to zero across groups';
  END IF;

  FOR r IN
    WITH parsed AS (
      SELECT NULLIF(x->>'cutting_group_id','')::uuid AS group_id,
             (x->>'qty_delta_pcs')::integer AS delta
      FROM jsonb_array_elements(p_lines) x
    )
    SELECT group_id,SUM(delta)::bigint AS delta
    FROM parsed
    WHERE group_id IS NOT NULL AND delta<>0
    GROUP BY group_id
  LOOP
    SELECT cutting_batch_id INTO v_group_batch
    FROM erp.cutting_groups
    WHERE id=r.group_id
    FOR UPDATE;
    IF v_group_batch IS NULL OR v_group_batch<>p_cutting_batch_id THEN
      RAISE EXCEPTION 'Cutting group % does not belong to correction batch',r.group_id;
    END IF;

    SELECT total_pcs INTO v_current
    FROM erp.v_cutting_group_totals
    WHERE cutting_group_id=r.group_id;
    v_current:=COALESCE(v_current,0);
    v_new:=v_current+r.delta;
    v_committed:=erp.cutting_group_downstream_committed_qty(r.group_id);

    IF v_new<0 THEN
      RAISE EXCEPTION 'Correction would make cutting group % negative: % pcs',r.group_id,v_new;
    END IF;
    IF v_new<v_committed THEN
      RAISE EXCEPTION 'Correction would reduce group % to % pcs, but % pcs are already committed downstream',r.group_id,v_new,v_committed;
    END IF;
  END LOOP;

  v_number:='CQC-'||to_char(COALESCE(p_physical_at,statement_timestamp()) AT TIME ZONE 'Asia/Jakarta','YYYYMMDD')||'-'||lpad(nextval('erp.cutting_qty_correction_seq')::text,6,'0');

  INSERT INTO erp.cutting_qty_corrections(
    correction_number,cutting_batch_id,correction_type,reason_code,reason,physical_at,reversal_of_id,posted_by
  ) VALUES (
    v_number,p_cutting_batch_id,p_correction_type,p_reason_code,p_reason,COALESCE(p_physical_at,statement_timestamp()),p_reversal_of_id,erp.current_app_user_id()
  ) RETURNING id INTO v_id;

  INSERT INTO erp.cutting_qty_correction_lines(correction_id,cutting_group_id,size_slot_id,qty_delta_pcs,notes)
  WITH parsed AS (
    SELECT NULLIF(x->>'cutting_group_id','')::uuid AS group_id,
           NULLIF(x->>'size_slot_id','')::uuid AS size_slot_id,
           (x->>'qty_delta_pcs')::integer AS delta,
           NULLIF(x->>'notes','') AS notes
    FROM jsonb_array_elements(p_lines) x
  )
  SELECT v_id,group_id,size_slot_id,SUM(delta)::integer,MAX(notes)
  FROM parsed
  WHERE group_id IS NOT NULL AND delta<>0
  GROUP BY group_id,size_slot_id
  HAVING SUM(delta)<>0;

  INSERT INTO erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  VALUES (
    'cutting_qty_corrections',v_id,'POST',
    jsonb_build_object('correction_number',v_number,'type',p_correction_type,'batch_id',p_cutting_batch_id,'net_delta_pcs',v_total_delta,'lines',p_lines),
    erp.current_app_user_id(),p_reason
  );

  IF EXISTS (SELECT 1 FROM erp.fg_lots WHERE po_id=v_po_id AND lot_origin='PRODUCTION') THEN
    PERFORM erp.rebuild_po_hpp(v_po_id,'Cutting quantity correction '||v_number);
    PERFORM erp.propagate_conversion_hpp_for_po(v_po_id);
    PERFORM erp.sync_po_hpp_to_gl(v_po_id,(COALESCE(p_physical_at,statement_timestamp()) AT TIME ZONE 'Asia/Jakarta')::date);
  END IF;

  RETURN v_id;
END;
$function$;

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
begin
  perform erp.require_internal();
  select closed_through into v_closed from erp.accounting_period_control where singleton_id=1 for share;
  perform 1 from erp.materials where id=p_material_id for update;
  if not found then raise exception 'Material not found'; end if;

  if p_allow_checkpoint and p_recalc_from is not null and v_closed is not null then
    select * into v_cp from erp.material_cost_checkpoints where material_id=p_material_id;
    if v_cp.material_id is not null
       and v_cp.checkpoint_date<=v_closed
       and erp._cp3_business_date(p_recalc_from)>v_cp.checkpoint_date then
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
        and (msm.physical_at,msm.system_created_at,msm.id)>(v_cp.last_physical_at,v_cp.last_system_created_at,v_cp.last_movement_id);
    end if;
  else
    delete from erp.material_cost_history where material_id=p_material_id;
  end if;

  for r in
    select * from erp.material_stock_movements msm
    where msm.material_id=p_material_id
      and msm.reversal_of_id is null
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id)
      and (
        not v_use_checkpoint
        or v_cp.last_movement_id is null
        or (msm.physical_at,msm.system_created_at,msm.id)>(v_cp.last_physical_at,v_cp.last_system_created_at,v_cp.last_movement_id)
      )
    order by msm.physical_at,msm.system_created_at,msm.id
    for update
  loop
    v_stock_before:=v_stock;
    v_avg_before:=v_avg;
    if r.qty_signed>0 then
      if r.movement_type='REVERSAL' and r.reversal_of_id is not null then
        select x.unit_cost_snapshot into v_cost from erp.material_stock_movements x where x.id=r.reversal_of_id;
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

  if not v_use_checkpoint and v_closed is not null then
    perform erp.refresh_material_cost_checkpoint(p_material_id,v_closed);
  end if;
end;
$function$;

CREATE OR REPLACE FUNCTION erp._validate_migration_batch_base(p_batch_id uuid)
 RETURNS TABLE(total_rows bigint, valid_rows bigint, error_rows bigint)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare r record;e jsonb;v_required text[];k text;v_total bigint;v_valid bigint;v_error bigint;v_bt text;v_material_type text;
begin
  perform erp.require_owner_admin();
  if not exists(select 1 from erp.migration_batches where id=p_batch_id) then raise exception 'Migration batch not found'; end if;
  update erp.migration_batches set status='VALIDATING',error_message=null where id=p_batch_id;
  update erp.migration_staging_rows set validation_status='PENDING',validation_errors='[]'::jsonb,updated_at=statement_timestamp() where batch_id=p_batch_id;
  update erp.migration_staging_rows s set validation_status='ERROR',validation_errors=jsonb_build_array('Duplicate legacy_key inside entity type'),updated_at=statement_timestamp()
  where s.batch_id=p_batch_id and s.legacy_key is not null and exists(select 1 from erp.migration_staging_rows d where d.batch_id=s.batch_id and d.entity_type=s.entity_type and d.legacy_key=s.legacy_key and d.id<>s.id);

  for r in select * from erp.migration_staging_rows where batch_id=p_batch_id order by entity_type,source_row_no loop
    e:='[]'::jsonb;
    if jsonb_typeof(r.normalized_payload)<>'object' then e:=e||jsonb_build_array('normalized_payload must be a JSON object'); end if;
    v_required:=case r.entity_type
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
      if not exists(select 1 from erp.locations where location_code=r.normalized_payload->>'location_code' and location_type='RAW_MATERIAL_WAREHOUSE' and is_active=true) then e:=e||jsonb_build_array('MATERIAL_ROLL location_code must be an active raw-material warehouse'); end if;
      if nullif(trim(coalesce(r.normalized_payload->>'supplier_code','')),'') is not null
         and not exists(select 1 from erp.suppliers where supplier_code=r.normalized_payload->>'supplier_code')
         and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='SUPPLIER' and s.normalized_payload->>'supplier_code'=r.normalized_payload->>'supplier_code') then
        e:=e||jsonb_build_array('Unknown MATERIAL_ROLL supplier_code');
      end if;
      if exists(select 1 from erp.migration_staging_rows d where d.batch_id=p_batch_id and d.entity_type='MATERIAL_ROLL' and d.id<>r.id
                and d.normalized_payload->>'material_sku'=r.normalized_payload->>'material_sku' and d.normalized_payload->>'roll_number'=r.normalized_payload->>'roll_number') then
        e:=e||jsonb_build_array('Duplicate roll_number for material inside migration batch');
      end if;
      if exists(select 1 from erp.material_rolls mr join erp.materials m on m.id=mr.material_id where m.material_sku=r.normalized_payload->>'material_sku' and mr.roll_number=r.normalized_payload->>'roll_number') then
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
    if r.validation_status='ERROR' and jsonb_array_length(r.validation_errors)>0 then e:=r.validation_errors||e; end if;
    update erp.migration_staging_rows set validation_status=case when jsonb_array_length(e)=0 then 'VALID' else 'ERROR' end,validation_errors=e,updated_at=statement_timestamp() where id=r.id;
  end loop;
  select count(*),count(*) filter(where validation_status='VALID'),count(*) filter(where validation_status='ERROR') into v_total,v_valid,v_error from erp.migration_staging_rows where batch_id=p_batch_id;
  update erp.migration_batches set status=case when v_error=0 then 'READY' else 'DRAFT' end,validated_at=statement_timestamp(),error_message=case when v_error=0 then null else v_error||' staging row(s) failed validation' end where id=p_batch_id;
  return query select v_total,v_valid,v_error;
end;$function$;

CREATE OR REPLACE FUNCTION erp.accessory_uom_factor(p_category_id uuid, p_uom_code text, p_at timestamp with time zone DEFAULT statement_timestamp())
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$ DECLARE v_base varchar(20);v_factor numeric(18,6); BEGIN PERFORM erp.require_internal();SELECT base_uom_code INTO v_base FROM erp.accessory_categories WHERE id=p_category_id; IF v_base IS NULL THEN RAISE EXCEPTION 'Accessory category not found'; END IF; IF upper(p_uom_code)=upper(v_base) THEN RETURN 1; END IF; SELECT base_qty_per_uom INTO v_factor FROM erp.accessory_category_uom_conversions WHERE category_id=p_category_id AND upper(uom_code)=upper(p_uom_code) AND effective_from<=p_at AND (effective_to IS NULL OR effective_to>p_at) ORDER BY effective_from DESC LIMIT 1; IF v_factor IS NULL THEN RAISE EXCEPTION 'No active UOM conversion for category %, UOM %, at %',p_category_id,p_uom_code,p_at; END IF;RETURN v_factor;END; $function$;

CREATE OR REPLACE FUNCTION erp.apply_cutting_correction_and_post_laundry(p_delivery_id uuid, p_cutting_batch_id uuid, p_correction_type text, p_reason_code text, p_reason text, p_lines jsonb, p_physical_at timestamp with time zone DEFAULT statement_timestamp())
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
DECLARE v_correction_id uuid;
BEGIN
  PERFORM erp.require_internal();
  v_correction_id:=erp.post_cutting_qty_correction(
    p_cutting_batch_id,p_correction_type,p_reason_code,p_reason,p_lines,p_physical_at
  );
  PERFORM erp.post_laundry_delivery(p_delivery_id);
  RETURN v_correction_id;
END;
$function$;

CREATE OR REPLACE FUNCTION erp.apply_migration_master_rows(p_batch_id uuid)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  r record;
  j jsonb;
  v_id uuid;
  v_model uuid;
  v_brand uuid;
  v_size uuid;
  v_category uuid;
  v_material uuid;
  v_supplier uuid;
  v_cutover timestamptz;
  v_count integer:=0;
  v_existing record;
begin
  perform erp.require_owner_admin();
  if (select status from erp.migration_batches where id=p_batch_id) not in('READY','POSTING') then
    raise exception 'Migration batch must be READY';
  end if;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and validation_status<>'VALID') then
    raise exception 'Migration batch contains unvalidated/error rows';
  end if;
  select cutover_at into v_cutover from erp.migration_batches where id=p_batch_id;
  update erp.migration_batches set status='POSTING',error_message=null where id=p_batch_id;

  for r in
    select * from erp.migration_staging_rows
    where batch_id=p_batch_id and validation_status='VALID'
      and entity_type in(
        'BRAND','SIZE','MODEL','CUSTOMER','SUPPLIER','CONTRACTOR',
        'ACCESSORY_CATEGORY','MATERIAL','MATERIAL_ROLL','PRODUCT'
      )
    order by case entity_type
      when 'BRAND' then 10 when 'SIZE' then 20 when 'MODEL' then 30
      when 'CUSTOMER' then 40 when 'SUPPLIER' then 50 when 'CONTRACTOR' then 60
      when 'ACCESSORY_CATEGORY' then 70 when 'MATERIAL' then 80
      when 'MATERIAL_ROLL' then 85 when 'PRODUCT' then 90 else 999 end,
      source_row_no
  loop
    j:=r.normalized_payload;
    v_id:=null;
    case r.entity_type
      when 'BRAND' then
        insert into erp.brands(brand_code,brand_name,is_active)
        values(j->>'brand_code',j->>'brand_name',coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(brand_code) do update set
          brand_name=excluded.brand_name,is_active=excluded.is_active,updated_at=statement_timestamp()
        returning id into v_id;
      when 'SIZE' then
        insert into erp.sizes(size_code,sort_order,is_active)
        values(j->>'size_code',coalesce(nullif(j->>'sort_order','')::integer,0),
          coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(size_code) do update set
          sort_order=excluded.sort_order,is_active=excluded.is_active
        returning id into v_id;
      when 'MODEL' then
        insert into erp.product_models(model_code,model_name,description,is_active)
        values(j->>'model_code',j->>'model_name',j->>'description',
          coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(model_code) do update set
          model_name=excluded.model_name,description=excluded.description,
          is_active=excluded.is_active,updated_at=statement_timestamp()
        returning id into v_id;
      when 'CUSTOMER' then
        insert into erp.customers(customer_code,customer_name,phone,address,is_active)
        values(j->>'customer_code',j->>'customer_name',j->>'phone',j->>'address',
          coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(customer_code) do update set
          customer_name=excluded.customer_name,phone=excluded.phone,address=excluded.address,
          is_active=excluded.is_active,updated_at=statement_timestamp()
        returning id into v_id;
      when 'SUPPLIER' then
        insert into erp.suppliers(
          supplier_code,supplier_name,supplier_type,phone,address,is_active
        ) values(
          j->>'supplier_code',j->>'supplier_name',
          coalesce(nullif(upper(j->>'supplier_type'),''),'MATERIAL'),
          j->>'phone',j->>'address',coalesce(nullif(j->>'is_active','')::boolean,true)
        )
        on conflict(supplier_code) do update set
          supplier_name=excluded.supplier_name,supplier_type=excluded.supplier_type,
          phone=excluded.phone,address=excluded.address,is_active=excluded.is_active
        returning id into v_id;
      when 'CONTRACTOR' then
        insert into erp.contractors(
          contractor_code,contractor_name,contractor_type,attendance_required,is_active,notes
        ) values(
          j->>'contractor_code',j->>'contractor_name',
          coalesce(nullif(upper(j->>'contractor_type'),''),'MANDOR'),
          coalesce(nullif(j->>'attendance_required','')::boolean,true),
          coalesce(nullif(j->>'is_active','')::boolean,true),j->>'notes'
        )
        on conflict(contractor_code) do update set
          contractor_name=excluded.contractor_name,contractor_type=excluded.contractor_type,
          attendance_required=excluded.attendance_required,is_active=excluded.is_active,
          notes=excluded.notes,updated_at=statement_timestamp()
        returning id into v_id;
      when 'ACCESSORY_CATEGORY' then
        insert into erp.accessory_categories(
          category_code,category_name,base_uom_code,is_active,notes
        ) values(
          j->>'category_code',j->>'category_name',upper(j->>'base_uom_code'),
          coalesce(nullif(j->>'is_active','')::boolean,true),j->>'notes'
        )
        on conflict(category_code) do update set
          category_name=excluded.category_name,is_active=excluded.is_active,
          notes=excluded.notes,updated_at=statement_timestamp()
        returning id into v_id;
      when 'MATERIAL' then
        v_category:=null;
        if nullif(btrim(coalesce(j->>'accessory_category_code','')),'') is not null then
          select id into v_category from erp.accessory_categories
          where category_code=j->>'accessory_category_code';
          if v_category is null then
            raise exception 'Unknown accessory category % for material %',
              j->>'accessory_category_code',j->>'material_sku';
          end if;
        end if;
        insert into erp.materials(
          material_sku,material_name,material_type,unit_code,accessory_category_id,is_active
        ) values(
          j->>'material_sku',j->>'material_name',upper(j->>'material_type'),
          upper(j->>'unit_code'),v_category,
          coalesce(nullif(j->>'is_active','')::boolean,true)
        )
        on conflict(material_sku) do update set
          material_name=excluded.material_name,
          accessory_category_id=excluded.accessory_category_id,
          is_active=excluded.is_active,updated_at=statement_timestamp()
        returning id into v_id;
      when 'MATERIAL_ROLL' then
        select id into v_material from erp.materials
        where material_sku=j->>'material_sku' and material_type='FABRIC';
        if v_material is null then
          raise exception 'MATERIAL_ROLL material % is not a FABRIC material',j->>'material_sku';
        end if;
        v_supplier:=null;
        if nullif(btrim(coalesce(j->>'supplier_code','')),'') is not null then
          select id into v_supplier from erp.suppliers where supplier_code=j->>'supplier_code';
          if v_supplier is null then
            raise exception 'Unknown supplier % for roll %',j->>'supplier_code',j->>'roll_number';
          end if;
        end if;
        if exists(select 1 from erp.material_rolls
          where material_id=v_material and roll_number=j->>'roll_number') then
          raise exception 'Migration roll already exists for material %, roll %',
            j->>'material_sku',j->>'roll_number';
        end if;
        insert into erp.material_rolls(
          material_id,purchase_item_id,supplier_id,roll_number,original_qty,
          cached_qty,status,received_at,notes
        ) values(
          v_material,null,v_supplier,j->>'roll_number',(j->>'opening_qty')::numeric,
          0,'AVAILABLE',v_cutover,coalesce(j->>'notes','Legacy roll at migration cutover')
        ) returning id into v_id;
      when 'PRODUCT' then
        select id into v_model from erp.product_models where model_code=j->>'model_code';
        select id into v_brand from erp.brands where brand_code=j->>'brand_code';
        select id into v_size from erp.sizes where size_code=j->>'size_code';
        if v_model is null or v_brand is null or v_size is null then
          raise exception 'Product % has unresolved model/brand/size mapping',j->>'sku';
        end if;
        insert into erp.product_model_sizes(model_id,size_id)
        values(v_model,v_size) on conflict(model_id,size_id) do nothing;

        select p.* into v_existing
        from erp.products p
        where p.brand_id=v_brand
          and lower(btrim(p.sku))=lower(btrim(j->>'sku'))
          and p.size_id=v_size
          and p.effective_from<=v_cutover
          and(p.effective_to is null or p.effective_to>v_cutover)
        order by p.effective_from desc,p.id desc limit 1;

        if v_existing.id is null then
          if exists(
            select 1 from erp.products p
            where p.brand_id=v_brand
              and lower(btrim(p.sku))=lower(btrim(j->>'sku'))
              and p.size_id=v_size
          ) then
            raise exception 'Migration product % already has identity history for brand % / size % but no version valid at cutover %. Do not guess a historical version; fix migration mapping/effective dates first.',
              j->>'sku',j->>'brand_code',j->>'size_code',v_cutover;
          end if;
          insert into erp.products(
            sku,model_id,brand_id,color_name,size_id,product_name,
            is_portal_visible,is_active,effective_from
          ) values(
            j->>'sku',v_model,v_brand,j->>'color_name',v_size,j->>'product_name',
            coalesce(nullif(j->>'is_portal_visible','')::boolean,true),
            coalesce(nullif(j->>'is_active','')::boolean,true),v_cutover
          ) returning id into v_id;
        else
          if v_existing.model_id is distinct from v_model
             or v_existing.brand_id is distinct from v_brand
             or lower(btrim(v_existing.color_name)) is distinct from lower(btrim(j->>'color_name'))
             or v_existing.size_id is distinct from v_size then
            raise exception 'Migration product % identity differs from the brand + SKU version already valid at cutover. Use controlled identity-version mapping instead of overwriting history.',j->>'sku';
          end if;
          v_id:=v_existing.id;
          update erp.products set
            product_name=j->>'product_name',
            is_portal_visible=coalesce(nullif(j->>'is_portal_visible','')::boolean,true),
            is_active=coalesce(nullif(j->>'is_active','')::boolean,true),updated_at=statement_timestamp()
          where id=v_id;
        end if;
    end case;
    update erp.migration_staging_rows set
      posted_entity_type=r.entity_type,posted_entity_id=v_id,
      posted_at=statement_timestamp(),updated_at=statement_timestamp()
    where id=r.id;
    v_count:=v_count+1;
  end loop;
  return v_count;
end
$function$;

CREATE OR REPLACE FUNCTION erp.apply_migration_open_pos(p_batch_id uuid)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$ DECLARE b erp.migration_batches%ROWTYPE;r record;j jsonb;v_model uuid;v_contractor uuid;v_id uuid;v_count integer:=0; BEGIN PERFORM erp.require_owner_admin();SELECT * INTO b FROM erp.migration_batches WHERE id=p_batch_id FOR UPDATE; IF b.id IS NULL THEN RAISE EXCEPTION 'Migration batch not found'; END IF; IF b.status NOT IN ('READY','POSTING') THEN RAISE EXCEPTION 'Migration batch must be READY/POSTING'; END IF; FOR r IN SELECT * FROM erp.migration_staging_rows WHERE batch_id=p_batch_id AND entity_type='OPEN_PO' AND validation_status='VALID' ORDER BY source_row_no LOOP j:=r.normalized_payload;SELECT id INTO v_model FROM erp.product_models WHERE model_code=j->>'model_code'; IF v_model IS NULL THEN RAISE EXCEPTION 'OPEN_PO row %: unknown model %',r.source_row_no,j->>'model_code'; END IF;v_contractor:=NULL; IF NULLIF(trim(COALESCE(j->>'contractor_code','')),'') IS NOT NULL THEN SELECT id INTO v_contractor FROM erp.contractors WHERE contractor_code=j->>'contractor_code'; IF v_contractor IS NULL THEN RAISE EXCEPTION 'OPEN_PO row %: unknown contractor %',r.source_row_no,j->>'contractor_code'; END IF; END IF;SELECT id INTO v_id FROM erp.production_orders WHERE po_number=j->>'po_number'; IF v_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM erp.production_orders WHERE id=v_id AND is_legacy=true AND migration_batch_id=p_batch_id) THEN RAISE EXCEPTION 'OPEN_PO row % conflicts with an existing non-migration PO number %',r.source_row_no,j->>'po_number'; END IF;v_id:=NULL;INSERT INTO erp.production_orders(po_number,model_id,contractor_id,target_qty_pcs,target_dozens,status,current_stage,physical_start_at,notes,migration_batch_id,is_legacy,legacy_reference,created_by) VALUES (j->>'po_number',v_model,v_contractor,NULLIF(j->>'target_qty_pcs','')::integer,NULLIF(j->>'target_dozens','')::numeric,upper(j->>'status'),upper(j->>'current_stage'),NULLIF(j->>'physical_start_at','')::timestamptz,COALESCE(j->>'notes','Migrated open PO'),p_batch_id,true,COALESCE(r.legacy_key,j->>'po_number'),erp.current_app_user_id()) ON CONFLICT (po_number) DO UPDATE SET contractor_id=EXCLUDED.contractor_id,target_qty_pcs=EXCLUDED.target_qty_pcs,target_dozens=EXCLUDED.target_dozens,status=EXCLUDED.status,current_stage=EXCLUDED.current_stage,physical_start_at=EXCLUDED.physical_start_at,notes=EXCLUDED.notes,migration_batch_id=EXCLUDED.migration_batch_id,is_legacy=true,legacy_reference=EXCLUDED.legacy_reference,updated_at=statement_timestamp() WHERE production_orders.is_legacy=true AND production_orders.migration_batch_id=p_batch_id RETURNING id INTO v_id; IF v_id IS NULL THEN RAISE EXCEPTION 'OPEN_PO row % could not be applied safely',r.source_row_no; END IF;UPDATE erp.migration_staging_rows SET posted_entity_type='PRODUCTION_ORDER',posted_entity_id=v_id,posted_at=statement_timestamp(),updated_at=statement_timestamp() WHERE id=r.id;v_count:=v_count+1; END LOOP;RETURN v_count;END; $function$;

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
  where payroll_id=p.id and source_type<>'ACCESSORY_BOM';
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

CREATE OR REPLACE FUNCTION erp.assign_cutting_group_to_batch(p_cutting_group_id uuid, p_cutting_batch_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
BEGIN
  PERFORM erp.require_internal();
  UPDATE erp.cutting_groups
  SET cutting_batch_id=p_cutting_batch_id,updated_at=statement_timestamp()
  WHERE id=p_cutting_group_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'Cutting group not found'; END IF;
END;
$function$;

CREATE OR REPLACE FUNCTION erp.cancel_product_identity_successor(p_product_id uuid, p_reason text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  p erp.products%rowtype;
  prev erp.products%rowtype;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan pembatalan perubahan SKU wajib diisi'; end if;

  select * into p from erp.products where id=p_product_id for update;
  if p.id is null then raise exception 'Versi SKU tidak ditemukan'; end if;
  if p.supersedes_product_id is null then raise exception 'SKU ini bukan successor. Hapus biasa hanya boleh untuk SKU baru yang benar-benar belum pernah dipakai.'; end if;
  if exists(select 1 from erp.products x where x.supersedes_product_id=p.id) then
    raise exception 'Versi SKU ini sudah memiliki successor berikutnya. Batalkan versi paling akhir terlebih dahulu.';
  end if;
  if exists(select 1 from erp.fg_lots x where x.product_id=p.id)
     or exists(select 1 from erp.sales_items x where x.product_id=p.id)
     or exists(select 1 from erp.qc_inspection_items x where x.final_product_id=p.id)
     or exists(select 1 from erp.opening_balance_items x where x.product_id=p.id)
     or exists(select 1 from erp.bs_cases x where x.product_id=p.id)
     or exists(select 1 from erp.po_accessory_bom_commitments x where x.product_id=p.id)
     or exists(select 1 from erp.product_conversions x where x.from_product_id=p.id or x.to_product_id=p.id) then
    raise exception 'Perubahan SKU ini sudah dipakai transaksi/stok/HPP dan tidak boleh dibatalkan. Buat perubahan efektif baru sebagai koreksi.';
  end if;

  select * into prev from erp.products where id=p.supersedes_product_id for update;
  if prev.id is null or prev.identity_root_id is distinct from p.identity_root_id or prev.effective_to is distinct from p.effective_from then
    raise exception 'Chain versi SKU tidak konsisten; pembatalan dihentikan agar histori tidak rusak.';
  end if;

  perform set_config('app.product_identity_controlled','on',true);
  delete from erp.products where id=p.id;
  update erp.products set effective_to=p.effective_to,updated_at=statement_timestamp() where id=prev.id;

  insert into erp.audit_logs(entity_type,entity_id,action,old_data,new_data,changed_by,change_reason)
  values('products',prev.id,'UPDATE',to_jsonb(prev),jsonb_build_object('cancelled_successor_product_id',p.id,'restored_effective_to',p.effective_to),erp.current_app_user_id(),p_reason);
  return prev.id;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.cancel_unpaid_payroll(p_payroll_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  p erp.payroll_settlements%rowtype;
  r record;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Cancellation reason is required'; end if;
  select * into p from erp.payroll_settlements where id=p_payroll_id for update;
  if p.id is null then raise exception 'Payroll not found'; end if;
  if p.status='PAID' then raise exception 'Paid payroll requires a dedicated financial reversal, not unpaid cancellation'; end if;
  if p.status='REVERSED' then return; end if;
  if p.status not in ('DRAFT','CALCULATED','REVIEW','APPROVED') then raise exception 'Payroll cannot be cancelled in status %',p.status; end if;
  perform erp._cp3_lock_business_period(p.period_start,p.period_end);

  if exists(
    select 1 from erp.attendance_hpp_pool_sources s
    join erp.attendance_hpp_pools hp on hp.id=s.pool_id
    where s.payroll_id=p.id and hp.status='ACTIVE'
  ) then
    raise exception 'PAYROLL_CONSUMED_BY_ACTIVE_HPP_POOL: cancel the active attendance HPP pool first';
  end if;

  for r in
    select je.id from erp.journal_entries je
    where je.source_id=p.id
      and je.source_type in ('PAYROLL_ATTENDANCE_ACCRUAL','PAYROLL_EXTRA_ACCRUAL','PAYROLL_MANUAL_REDUCTION')
      and je.status='POSTED'
    order by je.posting_at desc,je.id desc
  loop perform erp._cp3_r4_reverse_journal_internal(r.id,p_reason); end loop;

  update erp.payroll_settlements set status='REVERSED',settled_at=null,updated_at=statement_timestamp() where id=p.id;
  for r in select distinct pd.contractor_issue_item_id id from erp.payroll_deductions pd
           where pd.payroll_id=p.id and pd.contractor_issue_item_id is not null
  loop perform erp.refresh_contractor_issue_payroll_status(r.id); end loop;
  for r in select distinct pr.source_id id from erp.payroll_reimbursements pr
           where pr.payroll_id=p.id and pr.source_type='ACCESSORY_BOM' and pr.source_id is not null
  loop
    update erp.contractor_accessory_reimbursement_entitlements e
    set payroll_status=case
      when exists(select 1 from erp.payroll_reimbursements pr2 join erp.payroll_settlements ps2 on ps2.id=pr2.payroll_id
                  where pr2.source_type='ACCESSORY_BOM' and pr2.source_id=e.id and ps2.status='PAID') then 'SETTLED'
      when exists(select 1 from erp.payroll_reimbursements pr2 join erp.payroll_settlements ps2 on ps2.id=pr2.payroll_id
                  where pr2.source_type='ACCESSORY_BOM' and pr2.source_id=e.id and ps2.status<>'REVERSED') then 'ALLOCATED'
      else 'UNALLOCATED' end
    where e.id=r.id;
  end loop;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('payroll_settlements',p.id,'CANCEL_UNPAID',jsonb_build_object('previous_status',p.status),erp.current_app_user_id(),p_reason);
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

CREATE OR REPLACE FUNCTION erp.close_accounting_through(p_closed_through date, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare v_old date; v_material uuid;
begin
  perform erp.require_owner_admin();
  if p_closed_through is null then raise exception 'Tanggal tutup buku wajib diisi'; end if;
  if p_closed_through>=erp._cp3_business_date(statement_timestamp()) then raise exception 'Tutup buku hanya boleh sampai tanggal sebelum hari ini'; end if;
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan tutup buku wajib diisi'; end if;
  select closed_through into v_old from erp.accounting_period_control where singleton_id=1 for update;
  if v_old is not null and p_closed_through<v_old then
    raise exception 'Untuk membuka kembali periode gunakan reopen_accounting_through(); periode saat ini sudah ditutup sampai %',v_old;
  end if;
  update erp.accounting_period_control
  set closed_through=p_closed_through,updated_at=statement_timestamp(),updated_by=erp.current_app_user_id(),change_reason=p_reason
  where singleton_id=1;

  for v_material in select id from erp.materials order by id loop
    perform erp.refresh_material_cost_checkpoint(v_material,p_closed_through);
  end loop;

  insert into erp.audit_logs(entity_type,entity_id,action,old_data,new_data,changed_by,change_reason)
  values('accounting_period_control',null,'UPDATE',jsonb_build_object('closed_through',v_old),jsonb_build_object('closed_through',p_closed_through,'material_cost_checkpoints_refreshed',true),erp.current_app_user_id(),p_reason);
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

CREATE OR REPLACE FUNCTION erp.edit_product_identity_effective(p_product_id uuid, p_sku text, p_model_id uuid, p_brand_id uuid, p_color_name text, p_size_id uuid, p_product_name text, p_effective_from timestamp with time zone DEFAULT clock_timestamp(), p_reason text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  p erp.products%rowtype; v_new uuid; v_used boolean; v_eff timestamptz:=coalesce(p_effective_from,clock_timestamp());
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan perubahan SKU wajib diisi'; end if;
  if nullif(trim(p_sku),'') is null or nullif(trim(p_color_name),'') is null or nullif(trim(p_product_name),'') is null then
    raise exception 'SKU, warna, dan nama produk wajib diisi';
  end if;
  select * into p from erp.products where id=p_product_id for update;
  if p.id is null then raise exception 'SKU tidak ditemukan'; end if;

  if row(p.sku,p.model_id,p.brand_id,p.color_name,p.size_id)
     is not distinct from row(p_sku,p_model_id,p_brand_id,p_color_name,p_size_id) then
    update erp.products set product_name=p_product_name,updated_at=statement_timestamp() where id=p.id;
    insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason,new_data)
    values('products',p.id,'UPDATE',erp.current_app_user_id(),p_reason,jsonb_build_object('product_name',p_product_name));
    return p.id;
  end if;

  select (
    exists(select 1 from erp.fg_lots where product_id=p.id)
    or exists(select 1 from erp.sales_items where product_id=p.id)
    or exists(select 1 from erp.qc_inspection_items where final_product_id=p.id)
    or exists(select 1 from erp.opening_balance_items where product_id=p.id)
    or exists(select 1 from erp.bs_cases where product_id=p.id)
    or exists(select 1 from erp.po_accessory_bom_commitments where product_id=p.id)
    or exists(select 1 from erp.product_conversions where from_product_id=p.id or to_product_id=p.id)
  ) into v_used;

  if not v_used and not exists(select 1 from erp.products x where x.identity_root_id=p.identity_root_id and x.id<>p.id) then
    update erp.products
    set sku=trim(p_sku),model_id=p_model_id,brand_id=p_brand_id,color_name=trim(p_color_name),size_id=p_size_id,
        product_name=trim(p_product_name),updated_at=statement_timestamp()
    where id=p.id;
    insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason,new_data)
    values('products',p.id,'UPDATE',erp.current_app_user_id(),p_reason,
      jsonb_build_object('sku',p_sku,'model_id',p_model_id,'brand_id',p_brand_id,'color_name',p_color_name,'size_id',p_size_id));
    return p.id;
  end if;

  if v_eff<clock_timestamp()-interval '5 minutes' then
    raise exception 'Perubahan identitas SKU yang sudah punya histori hanya boleh berlaku mulai sekarang atau tanggal mendatang';
  end if;
  if v_eff<=p.effective_from or (p.effective_to is not null and v_eff>=p.effective_to) then
    raise exception 'Tanggal mulai perubahan harus berada setelah awal versi lama dan sebelum akhir versinya';
  end if;

  perform set_config('app.product_identity_controlled','on',true);
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
  select count(*) into v_count from erp.po_work_component_snapshots where po_id=p.id;
  if v_count>0 then return v_count; end if;

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
  select count(*) into v_count from erp.po_work_component_snapshots where po_id=p.id;
  if v_count=0 then raise exception 'Work BOM snapshot produced no components'; end if;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('production_orders',p.id,'WORK_BOM_COMMIT',jsonb_build_object('bom_version_id',v_bom,'committed_at',p_basis_at,'component_count',v_count),erp.current_app_user_id(),'First work-rate/BOM use');
  return v_count;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.finalize_migration_batch(p_batch_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare v_opening uuid;v_status text;
begin
  perform erp.require_owner_admin();select status into v_status from erp.migration_batches where id=p_batch_id for update;if v_status not in('READY','POSTING') then raise exception 'Migration batch must be READY/POSTING';end if;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and validation_status<>'VALID') then raise exception 'Migration batch has validation errors';end if;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type in('BRAND','SIZE','MODEL','PRODUCT','CUSTOMER','SUPPLIER','CONTRACTOR','ACCESSORY_CATEGORY','MATERIAL','MATERIAL_ROLL','OPEN_PO') and posted_entity_id is null) then raise exception 'Migration batch still has unapplied master/roll/open-PO rows';end if;
  select id into v_opening from erp.opening_balance_headers where migration_batch_id=p_batch_id order by created_at limit 1;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type in('OPENING_BALANCE_ITEM','MATERIAL_ROLL')) then
    if v_opening is null then raise exception 'Opening stock/balance rows exist but opening document was not prepared';end if;
    if (select status from erp.opening_balance_headers where id=v_opening)<>'POSTED' then raise exception 'Migration opening balance must be POSTED before finalizing batch';end if;
  end if;
  update erp.migration_batches set status='POSTED',posted_at=statement_timestamp(),error_message=null where id=p_batch_id;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason) values('migration_batches',p_batch_id,'POST',jsonb_build_object('status','POSTED'),erp.current_app_user_id(),'Finalize migration batch');
end;$function$;

CREATE OR REPLACE FUNCTION erp.finish_production_order(p_po_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_status text;
  v_sent bigint;
  v_returned bigint;
  v_claimed bigint;
  v_laundry_good bigint;
  v_qc_accounted bigint;
  v_fg_good bigint;
  v_open_bs bigint;
begin
  perform erp.require_internal();
  select status into v_status from erp.production_orders where id=p_po_id for update;
  if v_status is null then raise exception 'PO not found'; end if;
  if v_status='FINISHED' then return; end if;
  if v_status='CANCELLED' then raise exception 'Cancelled PO cannot be finished'; end if;

  select coalesce(sum(ldl.qty_sent_pcs),0) into v_sent
  from erp.laundry_delivery_lines ldl join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
  where ld.po_id=p_po_id and ld.status not in ('DRAFT','REVERSED');
  select coalesce(sum(lrl.qty_good_received+lrl.qty_bs_laundry),0) into v_returned
  from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id join erp.laundry_deliveries ld on ld.id=lr.delivery_id
  where ld.po_id=p_po_id and lr.status='POSTED' and ld.status<>'REVERSED';
  select coalesce(sum(lc.qty_claimed),0) into v_claimed
  from erp.laundry_claims lc
  where lc.delivery_id in (select id from erp.laundry_deliveries where po_id=p_po_id)
    and lc.claim_type in ('MISSING','STUCK') and lc.status in ('SETTLED','WRITTEN_OFF');
  if v_returned+v_claimed<v_sent then raise exception 'PO still has unresolved laundry outstanding qty %',v_sent-v_returned-v_claimed; end if;

  if v_sent>0 then
    select coalesce(sum(lrl.qty_good_received),0) into v_laundry_good
    from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id join erp.laundry_deliveries ld on ld.id=lr.delivery_id
    where ld.po_id=p_po_id and lr.status='POSTED';
    select coalesce(sum(qii.qty_good_pcs+qii.qty_bs_pcs),0) into v_qc_accounted
    from erp.qc_inspection_items qii join erp.qc_inspections qi on qi.id=qii.inspection_id
    where qi.po_id=p_po_id and qi.status='POSTED' and qii.source_laundry_receipt_line_id is not null;
    if v_qc_accounted<v_laundry_good then raise exception 'PO still has laundry GOOD pieces not yet accounted by QC: %',v_laundry_good-v_qc_accounted; end if;
  end if;

  select count(*) into v_open_bs from erp.bs_cases where po_id=p_po_id and status in ('OPEN','IN_REWORK','PARTIAL');
  if v_open_bs>0 then raise exception 'PO still has % unresolved BS case(s)',v_open_bs; end if;

  select coalesce(sum(initial_qty_pcs),0) into v_fg_good from erp.fg_lots where po_id=p_po_id and lot_origin='PRODUCTION';
  if v_fg_good<=0 then raise exception 'PO cannot finish without finished-goods output'; end if;

  perform erp.rebuild_po_hpp(p_po_id,'Final production close HPP rebuild');
  perform erp.propagate_conversion_hpp_for_po(p_po_id);
  perform erp.sync_po_hpp_to_gl(p_po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  update erp.production_orders set status='FINISHED',current_stage='FINISHED',updated_at=statement_timestamp() where id=p_po_id;
  perform erp.sync_finished_po_wip_residual(p_po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date,'Production order final residual WIP close');
end;
$function$;

CREATE OR REPLACE FUNCTION erp.get_accessory_economics(p_from date, p_to date)
 RETURNS TABLE(metric text, amount numeric)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$ DECLARE v_sales numeric(24,6);v_actual_cost numeric(24,6);v_reimburse numeric(24,6);v_hpp_basis numeric(24,6); BEGIN PERFORM erp.require_owner_admin();SELECT COALESCE(SUM(cmii.total_receivable),0),COALESCE(SUM(cmii.qty*cmii.unit_cost_snapshot),0) INTO v_sales,v_actual_cost FROM erp.contractor_material_issue_items cmii JOIN erp.contractor_material_issues cmi ON cmi.id=cmii.issue_id JOIN erp.materials m ON m.id=cmii.material_id WHERE cmi.status='POSTED' AND m.material_type='ACCESSORY' AND (cmi.physical_at AT TIME ZONE 'Asia/Jakarta')::date BETWEEN p_from AND p_to;SELECT COALESCE(SUM(e.amount),0) INTO v_reimburse FROM erp.contractor_accessory_reimbursement_entitlements e WHERE (e.physical_at AT TIME ZONE 'Asia/Jakarta')::date BETWEEN p_from AND p_to;SELECT COALESCE(SUM(s.total_hpp_cost),0) INTO v_hpp_basis FROM erp.fg_accessory_cost_snapshots s JOIN erp.fg_lots fl ON fl.id=s.lot_id WHERE (fl.produced_at AT TIME ZONE 'Asia/Jakarta')::date BETWEEN p_from AND p_to;RETURN QUERY VALUES ('MANDOR_ACCESSORY_CHARGE'::text,round(v_sales,2)),('ACTUAL_ACCESSORY_INVENTORY_COST'::text,round(v_actual_cost,2)),('GOOD_FG_REIMBURSEMENT'::text,round(v_reimburse,2)),('ACCESSORY_HPP_BASIS'::text,round(v_hpp_basis,2)),('REIMBURSEMENT_MINUS_HPP_VARIANCE'::text,round(v_reimburse-v_hpp_basis,2)),('NET_ECONOMIC_ACCESSORY_COST'::text,round(v_actual_cost+v_reimburse-v_sales,2)); END; $function$;

CREATE OR REPLACE FUNCTION erp.get_owner_financial_snapshot_v2(p_from date, p_to date, p_as_of date DEFAULT ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_catalog', 'pg_temp'
AS $function$
declare
  v_assets numeric:=0;v_liabilities numeric:=0;v_equity numeric:=0;v_current_earnings numeric:=0;
  v_cash numeric:=0;v_ar numeric:=0;v_material numeric:=0;v_wip numeric:=0;v_fg numeric:=0;
  v_ap numeric:=0;v_grni numeric:=0;
  v_sales_revenue numeric:=0;v_cogs numeric:=0;v_other_income numeric:=0;v_opex numeric:=0;v_net_profit numeric:=0;
  v_gross_sales numeric:=0;v_discounts numeric:=0;v_sales_returns numeric:=0;
  v_operational_net_sales numeric:=0;v_sales_revenue_bridge numeric:=0;
  v_qc_good numeric:=0;v_qc_bs numeric:=0;
  v_laundry_good numeric:=0;v_laundry_bs numeric:=0;v_laundry_stuck numeric:=0;v_laundry_missing numeric:=0;
  v_laundry_outstanding numeric:=0;
  v_failed_checks jsonb:='[]'::jsonb;
  v_grni_docs bigint:=0;v_grni_oldest integer:=0;v_ap_docs bigint:=0;v_ap_overdue numeric:=0;
  v_critical bigint:=0;v_warning bigint:=0;v_pending bigint:=0;
begin
  perform erp.require_owner_admin();
  if p_from is null or p_to is null or p_as_of is null then raise exception 'p_from, p_to and p_as_of are required'; end if;
  if p_from>p_to then raise exception 'p_from cannot be after p_to'; end if;
  if p_to>p_as_of then raise exception 'p_to cannot be after p_as_of'; end if;

  select
    coalesce(sum(case when ca.account_type='ASSET' then a.debit_total-a.credit_total else 0 end),0),
    coalesce(sum(case when ca.account_type='LIABILITY' then a.credit_total-a.debit_total else 0 end),0),
    coalesce(sum(case when ca.account_type='EQUITY' then a.credit_total-a.debit_total else 0 end),0),
    coalesce(sum(case when ca.account_type in('REVENUE','EXPENSE') then a.credit_total-a.debit_total else 0 end),0)
  into v_assets,v_liabilities,v_equity,v_current_earnings
  from erp.account_daily_balances a join erp.chart_accounts ca on ca.id=a.account_id
  where a.balance_date<=p_as_of;

  select coalesce(sum(a.debit_total-a.credit_total),0) into v_cash
  from erp.account_daily_balances a
  where a.balance_date<=p_as_of and a.account_id in(
    select ca.coa_account_id from erp.cash_accounts ca
    union select erp.account_id('CASH')
  );
  select coalesce(sum(a.debit_total-a.credit_total),0) into v_ar
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('AR_CUSTOMER');
  select coalesce(sum(a.debit_total-a.credit_total),0) into v_material
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('MATERIAL_INVENTORY');
  select coalesce(sum(a.debit_total-a.credit_total),0) into v_wip
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('WIP');
  select coalesce(sum(a.debit_total-a.credit_total),0) into v_fg
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('FG_INVENTORY');
  select coalesce(sum(a.credit_total-a.debit_total),0) into v_ap
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('AP_SUPPLIER');
  select coalesce(sum(a.credit_total-a.debit_total),0) into v_grni
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('GRNI_MATERIAL');

  select
    coalesce(sum(case when a.account_id=erp.account_id('SALES_REVENUE') then a.credit_total-a.debit_total else 0 end),0),
    coalesce(sum(case when a.account_id=erp.account_id('COGS') then a.debit_total-a.credit_total else 0 end),0),
    coalesce(sum(case when ca.account_type='REVENUE' and a.account_id<>erp.account_id('SALES_REVENUE') then a.credit_total-a.debit_total else 0 end),0),
    coalesce(sum(case when ca.account_type='EXPENSE' and a.account_id<>erp.account_id('COGS') then a.debit_total-a.credit_total else 0 end),0),
    coalesce(sum(case when ca.account_type in('REVENUE','EXPENSE') then a.credit_total-a.debit_total else 0 end),0)
  into v_sales_revenue,v_cogs,v_other_income,v_opex,v_net_profit
  from erp.account_daily_balances a join erp.chart_accounts ca on ca.id=a.account_id
  where a.balance_date between p_from and p_to;

  with sale_events as(
    select original.source_id sale_id,1::integer event_sign
    from erp.journal_entries original
    where original.source_type='SALE' and original.status in('POSTED','REVERSED')
      and original.transaction_date between p_from and p_to
    union all
    select original.source_id,-1::integer
    from erp.journal_entries reversal
    join erp.journal_entries original on original.id=reversal.reversal_of_id
      and original.source_type='SALE'
    where reversal.source_type='JOURNAL_REVERSAL' and reversal.status='POSTED'
      and reversal.transaction_date between p_from and p_to
  )
  select coalesce(sum(e.event_sign*i.qty_pcs*i.unit_price_snapshot),0),
         coalesce(sum(e.event_sign*i.discount_amount),0)
  into v_gross_sales,v_discounts
  from sale_events e join erp.sales_items i on i.sale_id=e.sale_id;

  with return_events as(
    select original.source_id return_id,1::integer event_sign
    from erp.journal_entries original
    where original.source_type='SALES_RETURN' and original.status in('POSTED','REVERSED')
      and original.transaction_date between p_from and p_to
    union all
    select original.source_id,-1::integer
    from erp.journal_entries reversal
    join erp.journal_entries original on original.id=reversal.reversal_of_id
      and original.source_type='SALES_RETURN'
    where reversal.source_type='JOURNAL_REVERSAL' and reversal.status='POSTED'
      and reversal.transaction_date between p_from and p_to
  )
  select coalesce(sum(e.event_sign*i.refund_amount),0) into v_sales_returns
  from return_events e join erp.sales_return_items i on i.return_id=e.return_id;
  v_operational_net_sales:=round(v_gross_sales-v_discounts-v_sales_returns,2);
  v_sales_revenue_bridge:=round(v_operational_net_sales-v_sales_revenue,2);

  select coalesce(sum(i.qty_good_pcs),0),coalesce(sum(i.qty_bs_pcs),0)
  into v_qc_good,v_qc_bs
  from erp.qc_inspection_items i join erp.qc_inspections h on h.id=i.inspection_id
  where h.status='POSTED' and erp._cp3_business_date(h.physical_at) between p_from and p_to;
  select coalesce(sum(i.qty_good_received),0),coalesce(sum(i.qty_bs_laundry),0),
         coalesce(sum(i.qty_stuck),0),coalesce(sum(i.qty_missing),0)
  into v_laundry_good,v_laundry_bs,v_laundry_stuck,v_laundry_missing
  from erp.laundry_receipt_lines i join erp.laundry_receipts h on h.id=i.receipt_id
  where h.status='POSTED' and erp._cp3_business_date(h.physical_at) between p_from and p_to;

  select greatest(coalesce(sum(case
    when w.stage_to='LAUNDRY' then w.qty_pcs
    when w.stage_from='LAUNDRY' then -w.qty_pcs
    else 0 end),0),0)
  into v_laundry_outstanding
  from erp.wip_stage_events w
  where erp._cp3_business_date(w.physical_at)<=p_as_of
    and w.source_type in(
      'LAUNDRY_DELIVERY_LINE','LAUNDRY_RECEIPT_LINE',
      'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL','CP6_LAUNDRY_RECEIPT_WIP_REVERSAL'
    );

  select count(*)::bigint,coalesce(max(unfinalized_days),0)::integer
  into v_grni_docs,v_grni_oldest from erp.v_material_grni_aging;
  select count(*)::bigint,coalesce(sum(case when days_overdue>0 then outstanding_amount else 0 end),0)
  into v_ap_docs,v_ap_overdue from erp.v_supplier_ap_aging where outstanding_amount>0.005;

  select coalesce(sum(issue_count) filter(where severity='CRITICAL'),0)::bigint,
         coalesce(sum(issue_count) filter(where severity='WARNING'),0)::bigint
  into v_critical,v_warning from erp.run_v268_financial_report_checks();
  select coalesce(jsonb_agg(jsonb_build_object(
    'check_name',c.check_name,'severity',c.severity,'issue_count',c.issue_count,
    'details',c.details) order by c.severity,c.check_name),'[]'::jsonb)
  into v_failed_checks from erp.run_v268_financial_report_checks() c
  where c.issue_count>0;
  if abs(v_sales_revenue_bridge)>0.005 then
    v_critical:=v_critical+1;
    v_failed_checks:=v_failed_checks||jsonb_build_array(jsonb_build_object(
      'check_name','V2620D_PERIOD_SALES_REVENUE_BRIDGE_MISMATCH',
      'severity','CRITICAL','issue_count',1,
      'details','Signed Sale/Sales-return lifecycle events do not reconcile to SALES_REVENUE for the selected posting period'
    ));
  end if;
  select count(*)::bigint into v_pending from erp.cost_recalc_queue
  where status in('PENDING','RUNNING') or(status='FAILED' and attempt_count<3);

  return jsonb_build_object(
    'basis',jsonb_build_object(
      'period_from',p_from,'period_to',p_to,'balance_sheet_as_of',p_as_of,
      'supplier_exposure_basis','CURRENT_OPERATIONAL_STATE',
      'performance_lifecycle_basis','SIGNED_JOURNAL_LIFECYCLE_EVENTS_IN_POSTING_PERIOD',
      'performance_reconciliation_basis','OPERATIONAL_NET_SALES_MINUS_SALES_REVENUE_GL',
      'quality_event_basis','CURRENT_OPERATIONAL_STATE_WITH_EVENT_DATE_CUTOFF',
      'laundry_outstanding_basis','IMMUTABLE_WIP_STAGE_EVENT_NET_AS_OF_BALANCE_DATE'
    ),
    'data_confidence',jsonb_build_object(
      'status',case when v_critical>0 then 'BLOCKED'
                    when v_pending>0 then 'RECALC_PENDING' else 'READY' end,
      'critical_issue_count',v_critical,'warning_issue_count',v_warning,
      'pending_cost_recalc_count',v_pending,'failed_checks',v_failed_checks
    ),
    'financial_position',jsonb_build_object(
      'assets',round(v_assets,2),'cash',round(v_cash,2),'customer_ar',round(v_ar,2),
      'material_inventory',round(v_material,2),'wip_inventory',round(v_wip,2),'fg_inventory',round(v_fg,2),
      'liabilities',round(v_liabilities,2),'supplier_final_ap',round(v_ap,2),
      'grni_estimated_liability',round(v_grni,2),'recorded_equity',round(v_equity,2),
      'current_earnings',round(v_current_earnings,2),
      'liabilities_plus_equity',round(v_liabilities+v_equity+v_current_earnings,2),
      'balance_difference',round(v_assets-v_liabilities-v_equity-v_current_earnings,2)
    ),
    'performance',jsonb_build_object(
      'sales_revenue_gl',round(v_sales_revenue,2),'cogs_gl',round(v_cogs,2),
      'gross_profit',round(v_sales_revenue-v_cogs,2),
      'gross_margin_pct',case when abs(v_sales_revenue)>0.005 then round((v_sales_revenue-v_cogs)*100/v_sales_revenue,4) else null end,
      'other_income',round(v_other_income,2),'operating_and_other_expense',round(v_opex,2),
      'net_profit',round(v_net_profit,2),
      'net_margin_pct',case when abs(v_sales_revenue)>0.005 then round(v_net_profit*100/v_sales_revenue,4) else null end,
      'gross_sales_before_discount',round(v_gross_sales,2),'line_discounts',round(v_discounts,2),
      'posted_sales_returns',round(v_sales_returns,2),
      'operational_net_sales',v_operational_net_sales,
      'sales_revenue_bridge_delta',v_sales_revenue_bridge,
      'sales_revenue_reconciled',abs(v_sales_revenue_bridge)<=0.005
    ),
    'quality',jsonb_build_object(
      'qc_good_pcs',v_qc_good,'qc_bs_pcs',v_qc_bs,
      'qc_defect_rate_pct',case when v_qc_good+v_qc_bs>0 then round(v_qc_bs*100/(v_qc_good+v_qc_bs),4) else null end,
      'laundry_good_received_pcs',v_laundry_good,'laundry_bs_pcs',v_laundry_bs,
      'laundry_bs_rate_on_resolved_receipts_pct',case when v_laundry_good+v_laundry_bs>0 then round(v_laundry_bs*100/(v_laundry_good+v_laundry_bs),4) else null end,
      'laundry_outstanding_pcs',v_laundry_outstanding,
      'legacy_receipt_stuck_pcs',v_laundry_stuck,'legacy_receipt_missing_pcs',v_laundry_missing
    ),
    'supplier_exposure',jsonb_build_object(
      'unfinalized_receipt_count',v_grni_docs,'oldest_unfinalized_days',v_grni_oldest,
      'open_final_ap_document_count',v_ap_docs,'overdue_final_ap_amount',round(v_ap_overdue,2)
    )
  );
end
$function$;

CREATE OR REPLACE FUNCTION erp.guard_cutting_batch_parent_change()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
BEGIN
  IF TG_OP='UPDATE' AND OLD.po_id IS DISTINCT FROM NEW.po_id
     AND EXISTS (SELECT 1 FROM erp.cutting_groups g WHERE g.cutting_batch_id=OLD.id) THEN
    RAISE EXCEPTION 'Cannot move a cutting batch to another PO after groups exist';
  END IF;
  NEW.updated_at := statement_timestamp();
  RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION erp.guard_material_cost_correction_post_date()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
begin
  if new.status='POSTED' and old.status is distinct from 'POSTED' and new.invoice_date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date then
    raise exception 'Tanggal invoice/koreksi harga supplier berada di masa depan. Periksa tanggal invoice sebelum posting.';
  end if;
  return new;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.guard_opening_balance_post_date()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
begin
  if new.status='POSTED' and old.status is distinct from 'POSTED' and new.opening_date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date then
    raise exception 'Tanggal saldo awal berada di masa depan. Periksa tanggal cutover/opening sebelum posting.';
  end if;
  return new;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.guard_opening_hpp_correction_effective_date()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
begin
  if new.effective_date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date then
    raise exception 'Tanggal koreksi HPP opening berada di masa depan. Periksa tanggal koreksi sebelum posting.';
  end if;
  return new;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.guard_vendor_invoice_post_date()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
begin
  if new.status in ('POSTED','PARTIAL_PAID','PAID') and old.status is distinct from new.status
     and new.invoice_date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date then
    raise exception 'Tanggal invoice vendor laundry berada di masa depan. Periksa tanggal invoice sebelum posting.';
  end if;
  return new;
end$function$;

CREATE OR REPLACE FUNCTION erp.merge_eligible_work_into_payroll_v2(p_payroll_id uuid, p_lines jsonb, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_payroll erp.payroll_settlements%rowtype;
  v_line jsonb;
  v_eligible record;
  v_qty integer;
  v_added_qty integer:=0;
  v_added_amount numeric(24,2):=0;
begin
  perform erp.require_internal();
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if coalesce(jsonb_typeof(p_lines),'null')<>'array' then
    raise exception 'Eligible lines must be a JSON array';
  end if;
  if jsonb_array_length(p_lines)=0 then raise exception 'At least one eligible line is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'payroll_id',p_payroll_id,'lines',p_lines,'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin('merge_eligible_work_into_payroll_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_payroll from erp.payroll_settlements where id=p_payroll_id for update;
  if v_payroll.id is null then raise exception 'Nota payroll not found'; end if;
  if v_payroll.status not in ('DRAFT','CALCULATED','REVIEW') then
    raise exception 'APPROVED/PAID/REVERSED Nota is locked; use reversal/correction';
  end if;
  if v_payroll.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_payroll.row_version;
  end if;
  perform pg_advisory_xact_lock(hashtextextended(v_payroll.contractor_id::text,0));

  for v_line in
    select value from jsonb_array_elements(p_lines)
    order by value->>'source_type',value->>'source_id'
  loop
    if upper(v_line->>'source_type')='PRODUCTION' then
      perform 1 from erp.work_completion_lines
      where id=(v_line->>'source_id')::uuid for update;
    elsif upper(v_line->>'source_type')='REWORK' then
      perform 1 from erp.rework_component_lines
      where id=(v_line->>'source_id')::uuid for update;
    else
      raise exception 'Unknown eligible source_type';
    end if;

    select * into v_eligible
    from erp.v_payroll_eligible_work_lines e
    where e.source_type=upper(v_line->>'source_type')
      and e.source_id=(v_line->>'source_id')::uuid;
    if v_eligible.source_id is null then raise exception 'Selected work line is no longer eligible'; end if;
    if v_eligible.contractor_id<>v_payroll.contractor_id then
      raise exception 'Eligible work belongs to a different Mandor';
    end if;
    if (v_eligible.eligible_at AT TIME ZONE 'Asia/Jakarta')::date>v_payroll.period_end then
      raise exception 'Eligible work is after the Nota period end';
    end if;
    v_qty:=coalesce(nullif(v_line->>'qty','')::integer,v_eligible.remaining_qty);
    if v_qty<=0 or v_qty>v_eligible.remaining_qty then
      raise exception 'Requested qty % exceeds remaining eligible qty %',v_qty,v_eligible.remaining_qty;
    end if;
    insert into erp.payroll_work_items(
      payroll_id,po_id,work_component_id,source_type,source_id,qty_payable,rate_snapshot
    ) values(
      v_payroll.id,v_eligible.po_id,v_eligible.work_component_id,
      v_eligible.source_type,v_eligible.source_id,v_qty,v_eligible.rate_snapshot
    )
    on conflict (payroll_id,source_type,source_id,work_component_id) do update
    set qty_payable=erp.payroll_work_items.qty_payable+excluded.qty_payable,
        rate_snapshot=excluded.rate_snapshot;
    v_added_qty:=v_added_qty+v_qty;
    v_added_amount:=v_added_amount+round(v_qty*v_eligible.rate_snapshot,2);
  end loop;

  perform erp.recalculate_payroll(v_payroll.id);
  select * into v_payroll from erp.payroll_settlements where id=v_payroll.id;
  v_response:=jsonb_build_object(
    'payroll_id',v_payroll.id,'status',v_payroll.status,
    'row_version',v_payroll.row_version,'added_qty',v_added_qty,
    'added_amount',v_added_amount,'net_payable',v_payroll.net_payable
  );
  return erp._idempotency_complete('merge_eligible_work_into_payroll_v2',p_client_request_id,v_response);
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
      cmii.total_receivable - coalesce((
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

CREATE OR REPLACE FUNCTION erp.post_accessory_reimbursement_accrual(p_lot_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  l erp.fg_lots%rowtype;
  v_hpp numeric(24,6);
  v_reimburse numeric(24,6);
  v_entitlement_total numeric(24,6);
  v_variance numeric(24,6);
  v_lines jsonb:='[]'::jsonb;
  v_contractor uuid;
  v_contractor_count integer;
begin
  perform erp.require_internal();
  perform erp.ensure_fg_accessory_cost_snapshot(p_lot_id);
  select * into l from erp.fg_lots where id=p_lot_id;
  if l.id is null or l.lot_origin<>'PRODUCTION' then return; end if;
  select coalesce(sum(total_hpp_cost),0),coalesce(sum(total_reimbursement),0)
  into v_hpp,v_reimburse
  from erp.fg_accessory_cost_snapshots where lot_id=l.id;
  if v_hpp=0 and v_reimburse=0 then return; end if;
  if exists(
    select 1 from erp.journal_entries
    where source_type='ACCESSORY_REIMBURSE_ACCRUAL'
      and source_id=l.id and status='POSTED'
  ) then return; end if;
  select count(distinct e.contractor_id),
    (array_agg(distinct e.contractor_id order by e.contractor_id))[1],
    coalesce(sum(e.amount),0)
  into v_contractor_count,v_contractor,v_entitlement_total
  from erp.contractor_accessory_reimbursement_entitlements e
  where e.lot_id=l.id and e.payroll_status<>'CANCELLED';
  if abs(v_entitlement_total-v_reimburse)>0.005 then
    raise exception 'Accessory entitlement total does not match immutable snapshot reimbursement';
  end if;
  if v_reimburse>0 and v_contractor_count<>1 then
    raise exception 'Accessory reimbursement requires exactly one authoritative Mandor';
  end if;
  if v_hpp>0 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','WIP','debit',round(v_hpp,2),'credit',0,
      'contractor_id',v_contractor,'po_id',l.po_id,'product_id',l.product_id
    ));
  end if;
  v_variance:=v_reimburse-v_hpp;
  if v_variance>0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','ACCESSORY_REIMBURSE_VARIANCE',
      'debit',round(v_variance,2),'credit',0,
      'contractor_id',v_contractor,'po_id',l.po_id,'product_id',l.product_id
    ));
  elsif v_variance< -0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','ACCESSORY_REIMBURSE_VARIANCE',
      'debit',0,'credit',round(abs(v_variance),2),
      'contractor_id',v_contractor,'po_id',l.po_id,'product_id',l.product_id
    ));
  end if;
  if v_reimburse>0 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',round(v_reimburse,2),
      'contractor_id',v_contractor,'po_id',l.po_id,'product_id',l.product_id
    ));
  end if;
  if v_reimburse=0 and v_hpp>0 then
    raise exception 'Accessory HPP snapshot has cost but zero Mandor reimbursement; configure reimbursement or use normal material issue flow';
  end if;
  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal(
      'ACCESSORY_REIMBURSE_ACCRUAL',l.id,(l.produced_at AT TIME ZONE 'Asia/Jakarta')::date,
      'Selected accessory HPP + Mandor reimbursement from GOOD rework/FG',v_lines
    );
  end if;
end
$function$;

CREATE OR REPLACE FUNCTION erp.post_contractor_material_issue(p_issue_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.contractor_material_issues%rowtype;
  r record;
  v_accessory_cost numeric(24,6):=0;
  v_other_cost numeric(24,6):=0;
  v_receivable numeric(24,6):=0;
  v_line_cost numeric(24,6);
  v_line_receivable numeric(24,6);
begin
  perform erp.require_internal();
  select * into h from erp.contractor_material_issues where id=p_issue_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Contractor material issue must be DRAFT'; end if;
  if h.location_id is null then raise exception 'Issue location is required'; end if;
  if not exists (select 1 from erp.contractor_material_issue_items where issue_id=h.id) then raise exception 'Contractor material issue has no lines'; end if;

  if h.po_id is not null and not exists(
    select 1 from erp.production_orders po where po.id=h.po_id and po.contractor_id=h.contractor_id
  ) then
    raise exception 'Mandor issue tidak sama dengan mandor pada PO. Pilih PO milik mandor yang sama agar biaya, piutang mandor, dan HPP tidak silang.';
  end if;

  if h.po_id is null and exists(
    select 1
    from erp.contractor_material_issue_items cmii
    join erp.materials m on m.id=cmii.material_id
    where cmii.issue_id=h.id and m.material_type<>'ACCESSORY'
  ) then
    raise exception 'Material non-accessory yang diberikan ke mandor wajib terkait ke PO supaya biaya WIP dapat masuk ke HPP produksi. Pilih PO sebelum posting.';
  end if;

  update erp.contractor_material_issue_items set transaction_qty=transaction_qty where issue_id=h.id;
  for r in
    select cmii.*,m.material_type
    from erp.contractor_material_issue_items cmii
    join erp.materials m on m.id=cmii.material_id
    where cmii.issue_id=h.id
    order by cmii.id
  loop
    insert into erp.material_stock_movements(material_id,roll_id,location_id,movement_type,qty_signed,source_type,source_id,physical_at,created_by)
    values (r.material_id,r.roll_id,h.location_id,'CONTRACTOR_ISSUE',-r.qty,'CONTRACTOR_MATERIAL_ISSUE_ITEM',r.id,h.physical_at,erp.current_app_user_id());
    perform erp.recalculate_material_cost(r.material_id);
    update erp.contractor_material_issue_items
    set unit_cost_snapshot=coalesce((
      select unit_cost_snapshot from erp.material_stock_movements
      where source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and source_id=r.id
      order by system_created_at desc limit 1
    ),0)
    where id=r.id;
    select qty*unit_cost_snapshot,total_receivable into v_line_cost,v_line_receivable
    from erp.contractor_material_issue_items where id=r.id;
    if r.material_type='ACCESSORY' then v_accessory_cost:=v_accessory_cost+coalesce(v_line_cost,0);
    else v_other_cost:=v_other_cost+coalesce(v_line_cost,0); end if;
    v_receivable:=v_receivable+coalesce(v_line_receivable,0);
  end loop;

  update erp.contractor_material_issues set status='POSTED' where id=h.id;
  if v_accessory_cost>0 then
    perform erp.post_journal('CONTRACTOR_ACCESSORY_STOCK_COST',h.id,(h.physical_at AT TIME ZONE 'Asia/Jakarta')::date,'Actual inventory cost of accessories physically sold/issued to mandor',jsonb_build_array(
      jsonb_build_object('mapping_key','ACCESSORY_RECOVERY_COGS','debit',round(v_accessory_cost,2),'credit',0,'contractor_id',h.contractor_id,'po_id',h.po_id),
      jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',0,'credit',round(v_accessory_cost,2),'contractor_id',h.contractor_id,'po_id',h.po_id)));
  end if;
  if v_other_cost>0 then
    perform erp.post_journal('CONTRACTOR_NONACCESSORY_MATERIAL_COST',h.id,(h.physical_at AT TIME ZONE 'Asia/Jakarta')::date,'Non-accessory material issued to contractor',jsonb_build_array(
      jsonb_build_object('mapping_key','WIP','debit',round(v_other_cost,2),'credit',0,'contractor_id',h.contractor_id,'po_id',h.po_id),
      jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',0,'credit',round(v_other_cost,2),'contractor_id',h.contractor_id,'po_id',h.po_id)));
  end if;
  if v_receivable>0 then
    perform erp.post_journal('CONTRACTOR_MATERIAL_RECEIVABLE',h.id,(h.physical_at AT TIME ZONE 'Asia/Jakarta')::date,'Material/accessory charge to mandor at configured selling price',jsonb_build_array(
      jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',round(v_receivable,2),'credit',0,'contractor_id',h.contractor_id,'po_id',h.po_id),
      jsonb_build_object('mapping_key','MATERIAL_RECOVERY','debit',0,'credit',round(v_receivable,2),'contractor_id',h.contractor_id,'po_id',h.po_id)));
  end if;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_cutting_material_issue(p_cutting_group_id uuid, p_location_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  g erp.cutting_groups%rowtype;
  r record;
  v_available numeric(24,6);
  v_unit_cost numeric(24,6);
  v_total numeric(24,6):=0;
begin
  perform erp.require_permission('production.cutting.post');
  select * into g from erp.cutting_groups where id=p_cutting_group_id for update;
  if g.id is null then raise exception 'Cutting group not found'; end if;
  if g.material_issue_posted then raise exception 'Cutting material issue already posted'; end if;
  if g.pattern_id is null then
    raise exception using errcode='23502',message='PATTERN_ID_REQUIRED_FOR_CUTTING_TRANSACTION';
  end if;
  if g.status<>'CUT' or g.picked_up_at is not null then
    raise exception using errcode='23514',message='CUTTING_POST_REQUIRES_UNPICKED_CUT_DRAFT';
  end if;
  if p_location_id is null or p_location_id is distinct from g.source_location_id then
    raise exception using errcode='23514',message='CUTTING_SOURCE_LOCATION_MISMATCH';
  end if;
  if not exists(
    select 1 from erp.locations l
    where l.id=p_location_id and l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
  ) then raise exception 'Active raw-material warehouse is required'; end if;
  if not exists(select 1 from erp.cutting_group_rolls x where x.cutting_group_id=g.id) then
    raise exception 'At least one roll is required before posting';
  end if;
  if not exists(
    select 1 from erp.cutting_roll_yields y
    join erp.cutting_group_rolls x on x.id=y.cutting_group_roll_id
    where x.cutting_group_id=g.id and y.qty_pcs>0
  ) then raise exception 'At least one positive cutting yield is required before posting'; end if;

  insert into erp.cutting_bridge_execution_context(
    backend_pid,transaction_id,actor_key,action,permission_key
  ) values(
    pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),
    'POST_CUTTING','production.cutting.post'
  );

  for r in
    select cgr.*,mr.material_id,mr.status as roll_status
    from erp.cutting_group_rolls cgr
    join erp.material_rolls mr on mr.id=cgr.roll_id
    where cgr.cutting_group_id=g.id
    order by mr.id
    for update of mr,cgr
  loop
    perform pg_advisory_xact_lock(hashtextextended(
      'MATSTOCK|'||r.material_id::text||'|'||r.roll_id::text||'|'||p_location_id::text,0
    ));
    select coalesce(sum(msm.qty_signed),0) into v_available
    from erp.material_stock_movements msm
    where msm.material_id=r.material_id and msm.roll_id=r.roll_id and msm.location_id=p_location_id;
    if r.roll_status not in ('AVAILABLE','HALF_USED') or v_available+0.000001<r.qty_issued then
      raise exception using errcode='23514',message=format(
        'INSUFFICIENT_ROLL_STOCK roll %s available %s requested %s',r.roll_id,v_available,r.qty_issued
      );
    end if;

    insert into erp.material_stock_movements(
      material_id,roll_id,location_id,movement_type,qty_signed,
      source_type,source_id,physical_at,created_by
    ) values(
      r.material_id,r.roll_id,p_location_id,'CUTTING_ISSUE',-r.qty_issued,
      'CUTTING_GROUP',g.id,g.cut_at,erp.current_app_user_id()
    );
    perform erp.recalculate_material_cost(r.material_id);
    select msm.unit_cost_snapshot into v_unit_cost
    from erp.material_stock_movements msm
    where msm.source_type='CUTTING_GROUP' and msm.source_id=g.id
      and msm.roll_id=r.roll_id and msm.movement_type='CUTTING_ISSUE'
    order by msm.system_created_at desc,msm.id desc limit 1;
    update erp.cutting_group_rolls set unit_cost_snapshot=v_unit_cost where id=r.id;
    v_total:=v_total+(r.qty_issued*coalesce(v_unit_cost,0));
  end loop;

  update erp.cutting_groups set material_issue_posted=true,updated_at=clock_timestamp()
  where id=g.id;
  if v_total>0 then
    perform erp.post_journal(
      'CUTTING_MATERIAL_ISSUE',g.id,(g.cut_at AT TIME ZONE 'Asia/Jakarta')::date,'Material issued to cutting',
      jsonb_build_array(
        jsonb_build_object('mapping_key','WIP','debit',round(v_total,2),'credit',0,'po_id',g.po_id),
        jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',0,'credit',round(v_total,2),'po_id',g.po_id)
      )
    );
  end if;
  delete from erp.cutting_bridge_execution_context
  where backend_pid=pg_backend_pid()
    and transaction_id=txid_current()
    and actor_key=erp._idempotency_actor_key();
  if not found then raise exception 'Cutting Bridge execution context was lost before completion'; end if;
end
$function$;

CREATE OR REPLACE FUNCTION erp.post_cutting_material_returns(p_cutting_group_id uuid, p_location_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  g erp.cutting_groups%rowtype;
  r record;
  v_value numeric(24,6);
begin
  perform erp.require_internal();
  select * into g from erp.cutting_groups where id=p_cutting_group_id for update;
  if g.id is null or not g.material_issue_posted then raise exception 'Cutting issue must be posted first'; end if;
  if g.material_return_posted then raise exception 'Cutting return already posted'; end if;
  if p_location_id is null or not exists(select 1 from erp.locations where id=p_location_id and is_active=true and location_type='RAW_MATERIAL_WAREHOUSE') then
    raise exception 'Lokasi return cutting harus gudang bahan aktif';
  end if;
  if exists(select 1 from erp.cutting_group_rolls where cutting_group_id=p_cutting_group_id and qty_physically_returned>0 and coalesce(return_destination,'NONE')<>'WAREHOUSE') then
    raise exception 'Positive cutting returns with destination other than WAREHOUSE require a dedicated supplier/scrap flow; they cannot be silently posted as warehouse returns';
  end if;
  if exists(select 1 from erp.cutting_group_rolls where cutting_group_id=p_cutting_group_id and qty_physically_returned>0 and return_destination='WAREHOUSE' and returned_at is null) then
    raise exception 'Tanggal/jam fisik return cutting wajib diisi untuk setiap roll yang kembali ke gudang';
  end if;

  for r in
    select cgr.*,mr.material_id
    from erp.cutting_group_rolls cgr join erp.material_rolls mr on mr.id=cgr.roll_id
    where cgr.cutting_group_id=p_cutting_group_id and cgr.qty_physically_returned>0 and cgr.return_destination='WAREHOUSE'
    order by cgr.returned_at,cgr.id
  loop
    insert into erp.material_stock_movements(material_id,roll_id,location_id,movement_type,qty_signed,input_unit_cost,source_type,source_id,physical_at,created_by)
    values(r.material_id,r.roll_id,p_location_id,'CUTTING_RETURN',r.qty_physically_returned,r.unit_cost_snapshot,'CUTTING_GROUP_RETURN',p_cutting_group_id,r.returned_at,erp.current_app_user_id());
    perform erp.recalculate_material_cost(r.material_id);
    v_value:=r.qty_physically_returned*coalesce(r.unit_cost_snapshot,0);
    if abs(v_value)>0.005 then
      perform erp.post_journal('CUTTING_MATERIAL_RETURN_LINE',r.id,(r.returned_at AT TIME ZONE 'Asia/Jakarta')::date,'Unused cutting material physically returned',jsonb_build_array(
        jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',round(v_value,2),'credit',0,'po_id',g.po_id),
        jsonb_build_object('mapping_key','WIP','debit',0,'credit',round(v_value,2),'po_id',g.po_id)
      ));
    end if;
  end loop;
  update erp.cutting_groups set material_return_posted=true where id=p_cutting_group_id;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_cutting_qty_correction(p_cutting_batch_id uuid, p_correction_type text, p_reason_code text, p_reason text, p_lines jsonb, p_physical_at timestamp with time zone DEFAULT statement_timestamp())
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
begin
  perform erp.require_internal();
  if coalesce(p_physical_at,statement_timestamp())>clock_timestamp()+interval '5 minutes' then raise exception 'Tanggal/jam Koreksi Potongan berada di masa depan'; end if;
  return erp._post_cutting_qty_correction(p_cutting_batch_id,upper(p_correction_type),upper(p_reason_code),p_reason,p_lines,p_physical_at,null);
end$function$;

CREATE OR REPLACE FUNCTION erp.post_fg_adjustment(p_adjustment_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.fg_adjustments%rowtype;
  r record;
  lk record;
  v_value numeric(24,6);
  v_hpp numeric(18,6);
  v_lines jsonb:='[]'::jsonb;
  v_po uuid;
  v_native boolean;
begin
  perform erp.require_owner_admin();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into h from erp.fg_adjustments where id=p_adjustment_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'FG adjustment harus DRAFT'; end if;
  if nullif(trim(h.reason),'') is null then raise exception 'Alasan FG adjustment wajib diisi'; end if;
  if not exists(select 1 from erp.locations where id=h.location_id and is_active=true and location_type='FG_WAREHOUSE') then
    raise exception 'Lokasi FG adjustment harus gudang barang jadi yang aktif';
  end if;
  if not exists(select 1 from erp.fg_adjustment_items where adjustment_id=h.id) then raise exception 'FG adjustment belum memiliki item'; end if;

  for r in
    select distinct fl.product_id
    from erp.fg_adjustment_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.adjustment_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  update erp.fg_adjustment_items set qty_signed=qty_signed where adjustment_id=h.id;

  for lk in
    select distinct product_id,quality_grade
    from erp.fg_adjustment_items
    where adjustment_id=h.id
    order by product_id,quality_grade
  loop
    insert into erp.fg_inventory_balances(product_id,location_id,quality_grade,cached_qty_pcs)
    values(lk.product_id,h.location_id,lk.quality_grade,0)
    on conflict(product_id,location_id,quality_grade) do nothing;
    perform 1 from erp.fg_inventory_balances
    where product_id=lk.product_id and location_id=h.location_id and quality_grade=lk.quality_grade
    for update;
  end loop;

  for r in
    select fai.*,fl.po_id,fl.lot_origin
    from erp.fg_adjustment_items fai
    join erp.fg_lots fl on fl.id=fai.lot_id
    where fai.adjustment_id=h.id
    order by fai.product_id,fai.quality_grade,fai.lot_id,fai.id
  loop
    perform 1 from erp.fg_lots where id=r.lot_id for update;
    v_hpp:=coalesce(erp.lock_current_hpp_per_pcs(r.lot_id),0);
    update erp.fg_adjustment_items set unit_hpp_snapshot=v_hpp where id=r.id;
    v_native:=r.po_id is not null and r.lot_origin in ('PRODUCTION','CONVERSION');

    perform erp.post_fg_movement(r.product_id,r.lot_id,h.location_id,r.quality_grade,'ADJUSTMENT',r.qty_signed,v_hpp,null,'FG_ADJUSTMENT_ITEM',r.id,h.physical_at,h.reason||coalesce(' - '||r.notes,''),false);
    v_value:=abs(r.qty_signed*v_hpp);

    if v_native then
      v_po:=r.po_id;
    elsif v_value>0.005 then
      if r.qty_signed<0 then
        v_lines:=v_lines||jsonb_build_array(
          jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',round(v_value,2),'credit',0,'product_id',r.product_id),
          jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',round(v_value,2),'product_id',r.product_id));
      else
        v_lines:=v_lines||jsonb_build_array(
          jsonb_build_object('mapping_key','FG_INVENTORY','debit',round(v_value,2),'credit',0,'product_id',r.product_id),
          jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',round(v_value,2),'product_id',r.product_id));
      end if;
    end if;
  end loop;

  update erp.fg_adjustments set status='POSTED' where id=h.id;
  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal('FG_ADJUSTMENT',h.id,(h.physical_at AT TIME ZONE 'Asia/Jakarta')::date,'Controlled FG stock adjustment: '||h.reason,v_lines);
  end if;

  for v_po in
    select distinct fl.po_id
    from erp.fg_adjustment_items fai join erp.fg_lots fl on fl.id=fai.lot_id
    where fai.adjustment_id=h.id and fl.po_id is not null and fl.lot_origin in ('PRODUCTION','CONVERSION')
  loop
    perform erp.sync_po_hpp_to_gl(v_po,(h.physical_at AT TIME ZONE 'Asia/Jakarta')::date);
  end loop;

  for r in
    select distinct fl.product_id
    from erp.fg_adjustment_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.adjustment_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.sync_non_po_product_hpp_to_gl_v2620f(
      r.product_id,case when h.status='DRAFT' then (h.physical_at AT TIME ZONE 'Asia/Jakarta')::date else ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date end,
      case when h.status='DRAFT' then 'FG_ADJUSTMENT' else 'FG_ADJUSTMENT_REVERSAL' end,
      h.id,'Cumulative adjustment lifecycle: '||h.reason
    );
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values ('fg_adjustments',h.id,'POST',erp.current_app_user_id(),h.reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_fg_movement(p_product_id uuid, p_lot_id uuid, p_location_id uuid, p_quality_grade text, p_movement_type text, p_qty_signed integer, p_unit_hpp numeric, p_customer_id uuid, p_source_type text, p_source_id uuid, p_physical_at timestamp with time zone, p_note text DEFAULT NULL::text, p_allow_negative boolean DEFAULT false)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_id uuid;
  v_balance integer;
  v_lot_qty integer;
  v_lot_product uuid;
  v_lot_produced_at timestamptz;
begin
  perform erp.require_internal();
  if p_qty_signed=0 then raise exception 'FG movement qty cannot be zero'; end if;
  if p_physical_at is null then raise exception 'Finished-goods movement physical date/time is required'; end if;
  if p_location_id is null or not exists (
    select 1 from erp.locations l
    where l.id=p_location_id and l.is_active=true and l.location_type='FG_WAREHOUSE'
  ) then
    raise exception 'Finished-goods movement location must be an active FG warehouse';
  end if;

  insert into erp.fg_inventory_balances(product_id,location_id,quality_grade,cached_qty_pcs)
  values (p_product_id,p_location_id,coalesce(p_quality_grade,'GRADE_A'),0)
  on conflict (product_id,location_id,quality_grade) do nothing;

  select cached_qty_pcs into v_balance
  from erp.fg_inventory_balances
  where product_id=p_product_id
    and location_id=p_location_id
    and quality_grade=coalesce(p_quality_grade,'GRADE_A')
  for update;

  if not p_allow_negative and v_balance+p_qty_signed<0 then
    raise exception 'Finished goods stock cannot become negative';
  end if;

  if p_lot_id is not null then
    select cached_qty_pcs,product_id,produced_at
      into v_lot_qty,v_lot_product,v_lot_produced_at
    from erp.fg_lots where id=p_lot_id for update;
    if v_lot_qty is null then raise exception 'FG lot not found'; end if;
    if v_lot_product is distinct from p_product_id then
      raise exception 'FG lot product does not match movement product';
    end if;
    if p_physical_at<v_lot_produced_at then
      raise exception 'Tanggal mutasi FG % lebih awal dari tanggal barang/lot tersedia %. Koreksi tanggal transaksi atau sumber barang terlebih dahulu.',p_physical_at,v_lot_produced_at;
    end if;
    if not p_allow_negative and v_lot_qty+p_qty_signed<0 then
      raise exception 'FG lot stock cannot become negative';
    end if;
  end if;

  insert into erp.fg_stock_movements(
    product_id,lot_id,location_id,quality_grade,movement_type,qty_signed,
    unit_hpp_snapshot,customer_id,source_type,source_id,physical_at,created_by,notes
  ) values (
    p_product_id,p_lot_id,p_location_id,coalesce(p_quality_grade,'GRADE_A'),p_movement_type,p_qty_signed,
    coalesce(p_unit_hpp,0),p_customer_id,p_source_type,p_source_id,p_physical_at,erp.current_app_user_id(),p_note
  ) returning id into v_id;

  if not p_allow_negative then
    perform erp.assert_fg_chronological_nonnegative(p_product_id,p_lot_id,p_location_id,coalesce(p_quality_grade,'GRADE_A'));
  end if;

  update erp.fg_inventory_balances
  set cached_qty_pcs=cached_qty_pcs+p_qty_signed,updated_at=statement_timestamp()
  where product_id=p_product_id
    and location_id=p_location_id
    and quality_grade=coalesce(p_quality_grade,'GRADE_A');

  if p_lot_id is not null then
    update erp.fg_lots
    set cached_qty_pcs=cached_qty_pcs+p_qty_signed,
        is_open=(cached_qty_pcs+p_qty_signed)>0
    where id=p_lot_id;
  end if;
  return v_id;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_fg_partial_completion_v2_legacy_v2610(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_operation constant text := 'post_fg_partial_completion_v2';
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_group erp.cutting_groups%rowtype;
  v_po_status text;
  v_group_id uuid := nullif(p_payload->>'cutting_group_id', '')::uuid;
  v_destination_location_id uuid := nullif(p_payload->>'destination_location_id', '')::uuid;
  v_physical_at timestamptz := coalesce(
    nullif(p_payload->>'physical_at', '')::timestamptz,
    clock_timestamp()
  );
  v_reason text := nullif(btrim(p_payload->>'reason'), '');
  v_lines jsonb := p_payload->'lines';
  v_qc_id uuid := gen_random_uuid();
  v_inspection_number text;
  v_total_qty bigint;
  v_good_qty bigint;
  v_bs_qty bigint;
  v_effective_qty bigint;
  v_prior_qty bigint;
  v_stock_qty bigint;
  v_stock_event_count bigint;
  v_progress erp.v_fg_partial_completion_progress%rowtype;
begin
  perform erp.require_internal();
  if p_expected_version is null then
    raise exception 'expected_version is required';
  end if;
  if v_group_id is null then
    raise exception 'cutting_group_id is required';
  end if;
  if v_destination_location_id is null then
    raise exception 'destination_location_id is required';
  end if;
  if v_reason is null then
    raise exception 'Completion reason is required';
  end if;
  if v_physical_at > clock_timestamp() + interval '5 minutes' then
    raise exception 'Tanggal/jam penyelesaian FG berada di masa depan';
  end if;
  if jsonb_typeof(v_lines) <> 'array' or jsonb_array_length(v_lines) = 0 then
    raise exception 'Partial FG completion requires at least one line';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'payload', p_payload,
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then
    return v_cached;
  end if;

  perform set_config('app.change_reason', v_reason, true);

  select * into v_group
  from erp.cutting_groups
  where id = v_group_id
  for update;
  if v_group.id is null then
    raise exception 'Potongan not found';
  end if;
  if v_group.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',
      p_expected_version, v_group.row_version;
  end if;

  select status into v_po_status
  from erp.production_orders
  where id = v_group.po_id
  for update;
  if v_po_status in ('FINISHED', 'CANCELLED') then
    raise exception 'PO berstatus % dan tidak menerima penyelesaian FG baru', v_po_status;
  end if;

  if not exists (
    select 1 from erp.locations l
    where l.id = v_destination_location_id
      and l.is_active = true
      and l.location_type = 'FG_WAREHOUSE'
  ) then
    raise exception 'Destination must be an active FG warehouse';
  end if;

  if exists (
    select 1
    from jsonb_to_recordset(v_lines) as x(
      final_product_id uuid,
      qty_good_pcs integer,
      qty_bs_pcs integer,
      source_laundry_receipt_line_id uuid,
      notes text
    )
    where coalesce(x.qty_good_pcs, 0) < 0
       or coalesce(x.qty_bs_pcs, 0) < 0
       or coalesce(x.qty_good_pcs, 0) + coalesce(x.qty_bs_pcs, 0) <= 0
       or x.final_product_id is null
  ) then
    raise exception 'Every completion line requires a SKU and a positive GOOD/BS quantity';
  end if;

  if exists (
    select 1
    from jsonb_to_recordset(v_lines) as x(
      final_product_id uuid,
      qty_good_pcs integer,
      qty_bs_pcs integer,
      source_laundry_receipt_line_id uuid,
      notes text
    )
    group by x.final_product_id, x.source_laundry_receipt_line_id
    having count(*) > 1
  ) then
    raise exception 'Duplicate SKU and laundry source lines are not allowed';
  end if;

  select
    sum(coalesce(x.qty_good_pcs, 0) + coalesce(x.qty_bs_pcs, 0))::bigint,
    sum(coalesce(x.qty_good_pcs, 0))::bigint,
    sum(coalesce(x.qty_bs_pcs, 0))::bigint
  into v_total_qty, v_good_qty, v_bs_qty
  from jsonb_to_recordset(v_lines) as x(
    final_product_id uuid,
    qty_good_pcs integer,
    qty_bs_pcs integer,
    source_laundry_receipt_line_id uuid,
    notes text
  );

  select effective_qty_pcs, qc_accounted_qty_pcs
  into v_effective_qty, v_prior_qty
  from erp.v_fg_partial_completion_progress
  where cutting_group_id = v_group.id;
  if coalesce(v_effective_qty, 0) <= 0 then
    raise exception 'Potongan has no effective quantity available for FG';
  end if;
  if coalesce(v_prior_qty, 0) + coalesce(v_total_qty, 0) > v_effective_qty then
    raise exception
      'Qty penyelesaian melebihi sisa Potongan. Efektif %, sudah diposting %, input %.',
      v_effective_qty, coalesce(v_prior_qty, 0), coalesce(v_total_qty, 0);
  end if;

  -- The request UUID is already the idempotency identity. Use all 128 bits
  -- in the human document key: truncating to 40 bits lets distinct valid
  -- requests collide and rejects a real posting at the unique constraint.
  v_inspection_number := 'FGP-'
    || to_char((v_physical_at AT TIME ZONE 'Asia/Jakarta'), 'YYMMDD') || '-'
    || upper(replace(p_client_request_id::text, '-', ''));

  insert into erp.qc_inspections(
    id, inspection_number, po_id, physical_at, status,
    notes, created_by, destination_location_id
  ) values (
    v_qc_id, v_inspection_number, v_group.po_id, v_physical_at, 'DRAFT',
    'Partial FG completion: ' || v_reason,
    erp.current_app_user_id(), v_destination_location_id
  );

  insert into erp.qc_inspection_items(
    inspection_id, cutting_group_id, source_laundry_receipt_line_id,
    final_product_id, qty_good_pcs, qty_bs_pcs, notes
  )
  select
    v_qc_id,
    v_group.id,
    x.source_laundry_receipt_line_id,
    x.final_product_id,
    coalesce(x.qty_good_pcs, 0),
    coalesce(x.qty_bs_pcs, 0),
    nullif(btrim(x.notes), '')
  from jsonb_to_recordset(v_lines) as x(
    final_product_id uuid,
    qty_good_pcs integer,
    qty_bs_pcs integer,
    source_laundry_receipt_line_id uuid,
    notes text
  );

  perform erp.post_qc(v_qc_id);

  -- Invalidate stale partial-completion drafts after every successful posting.
  update erp.cutting_groups
  set updated_at = clock_timestamp()
  where id = v_group.id
  returning * into v_group;

  select * into v_progress
  from erp.v_fg_partial_completion_progress
  where cutting_group_id = v_group.id;

  select
    coalesce(sum(m.qty_signed), 0)::bigint,
    count(*)::bigint
  into v_stock_qty, v_stock_event_count
  from erp.fg_stock_movements m
  where m.movement_type = 'QC_GOOD'
    and m.source_type = 'QC_ITEM'
    and m.source_id in (
      select i.id from erp.qc_inspection_items i where i.inspection_id = v_qc_id
    );

  v_response := jsonb_build_object(
    'qc_inspection_id', v_qc_id,
    'inspection_number', v_inspection_number,
    'cutting_group_id', v_group.id,
    'po_id', v_group.po_id,
    'completion_status', v_progress.completion_status,
    'posted_qty_pcs', v_total_qty,
    'good_qty_pcs', v_good_qty,
    'bs_qty_pcs', v_bs_qty,
    'fg_stock_in_qty_pcs', v_stock_qty,
    'fg_stock_event_count', v_stock_event_count,
    'cumulative_qc_qty_pcs', v_progress.qc_accounted_qty_pcs,
    'remaining_qc_qty_pcs', v_progress.remaining_qc_qty_pcs,
    'completion_count', v_progress.completion_count,
    'row_version', v_group.row_version,
    'document_status', 'POSTED'
  );

  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_journal(p_source_type text, p_source_id uuid, p_transaction_date date, p_description text, p_lines jsonb)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_entry_id uuid;
  v_input_debit numeric;
  v_input_credit numeric;
  v_cent_lines jsonb := '[]'::jsonb;
  v_number text;
  v_debit numeric(20,2);
  v_credit numeric(20,2);
  r jsonb;
  v_account_id uuid;
  v_gl_date date;
  v_ap_vendor_account uuid;
  v_vendor_id uuid;
  v_vendor_balance numeric(24,6);
  v_vendor_delta numeric(24,6);
begin
  perform erp.require_internal();
  if jsonb_typeof(p_lines) is distinct from 'array' then
    raise exception 'JOURNAL_LINES_ARRAY_REQUIRED';
  end if;
  if jsonb_array_length(p_lines)<2 then
    raise exception 'Journal requires at least two lines';
  end if;
  -- Canonicalize each monetary line exactly as it will be stored. All balance
  -- and vendor-admission checks below consume these same cent amounts.
  for r in select * from jsonb_array_elements(p_lines) loop
    if jsonb_typeof(r) is distinct from 'object' then
      raise exception 'JOURNAL_LINE_OBJECT_REQUIRED';
    end if;
    v_input_debit:=coalesce((r->>'debit')::numeric,0);
    v_input_credit:=coalesce((r->>'credit')::numeric,0);
    if v_input_debit::text in('NaN','Infinity','-Infinity')
       or v_input_credit::text in('NaN','Infinity','-Infinity')
       or v_input_debit<0 or v_input_credit<0 then
      raise exception 'JOURNAL_FINITE_NONNEGATIVE_MONEY_REQUIRED';
    end if;
    v_cent_lines:=v_cent_lines||jsonb_build_array(r||jsonb_build_object(
      'debit',round(v_input_debit,2),'credit',round(v_input_credit,2)));
  end loop;
  p_lines:=v_cent_lines;
  select coalesce(sum(coalesce((x->>'debit')::numeric,0)),0),coalesce(sum(coalesce((x->>'credit')::numeric,0)),0)
  into v_debit,v_credit from jsonb_array_elements(p_lines) x;
  if v_debit<>v_credit or v_debit<=0 then raise exception 'Journal is not balanced. Debit %, Credit %',v_debit,v_credit; end if;
  if exists(select 1 from erp.journal_entries where source_type=p_source_type and source_id=p_source_id and status='POSTED') then
    raise exception 'A posted journal already exists for this source';
  end if;

  -- Serialize journal posting with accounting close/reopen. A close that starts
  -- first blocks this journal until the new closed-through date is visible; a
  -- journal that starts first keeps the close waiting until this posting commits.
  perform 1 from erp.accounting_period_control where singleton_id=1 for share;

  -- Vendor AP is allowed to reach zero, but not become negative. Negative AP
  -- means the company has a receivable/advance from the vendor and requires a
  -- separate explicit workflow instead of silently crossing the account sign.
  v_ap_vendor_account:=erp.account_id('AP_VENDOR');
  for v_vendor_id in
    select distinct nullif(x->>'vendor_id','')::uuid
    from jsonb_array_elements(p_lines) x
    where nullif(x->>'vendor_id','') is not null
      and coalesce((x->>'debit')::numeric,0)>coalesce((x->>'credit')::numeric,0)
      and (
        (x ? 'mapping_key' and x->>'mapping_key'='AP_VENDOR')
        or (x ? 'account_id' and nullif(x->>'account_id','')::uuid=v_ap_vendor_account)
      )
    order by 1
  loop
    perform pg_advisory_xact_lock(hashtextextended('VENDOR_AP|'||v_vendor_id::text,0));

    select coalesce(sum(jl.credit-jl.debit),0)
      into v_vendor_balance
    from erp.journal_lines jl
    join erp.journal_entries je on je.id=jl.journal_entry_id
    where je.status in ('POSTED','REVERSED')
      and jl.account_id=v_ap_vendor_account
      and jl.vendor_id=v_vendor_id;

    select coalesce(sum(
      coalesce((x->>'credit')::numeric,0)-coalesce((x->>'debit')::numeric,0)
    ),0)
      into v_vendor_delta
    from jsonb_array_elements(p_lines) x
    where nullif(x->>'vendor_id','')::uuid=v_vendor_id
      and (
        (x ? 'mapping_key' and x->>'mapping_key'='AP_VENDOR')
        or (x ? 'account_id' and nullif(x->>'account_id','')::uuid=v_ap_vendor_account)
      );

    if v_vendor_balance::text in('NaN','Infinity','-Infinity') or v_vendor_balance+v_vendor_delta < 0 then
      raise exception 'Transaksi ini membuat hutang vendor menjadi negatif. Hutang saat ini %, perubahan %, hasil %. Reverse/koreksi pembayaran, claim, atau invoice terkait dulu; kelebihan bayar/claim vendor harus masuk workflow piutang vendor terpisah.',
        round(v_vendor_balance,2),round(v_vendor_delta,2),round(v_vendor_balance+v_vendor_delta,2);
    end if;
  end loop;

  v_gl_date:=erp.resolve_accounting_transaction_date(p_transaction_date);
  v_number:='JRN-'||to_char((clock_timestamp() AT TIME ZONE 'Asia/Jakarta'),'YYYYMMDDHH24MISSMS')||'-'||substr(gen_random_uuid()::text,1,8);
  insert into erp.journal_entries(journal_number,economic_date,transaction_date,posting_at,source_type,source_id,description,status,created_by)
  values(v_number,p_transaction_date,v_gl_date,statement_timestamp(),p_source_type,p_source_id,p_description,'POSTED',erp.current_app_user_id()) returning id into v_entry_id;

  for r in select * from jsonb_array_elements(p_lines) loop
    if r?'account_id' then v_account_id:=(r->>'account_id')::uuid; else v_account_id:=erp.account_id(r->>'mapping_key'); end if;
    insert into erp.journal_lines(journal_entry_id,account_id,description,debit,credit,customer_id,vendor_id,contractor_id,po_id,product_id)
    values(v_entry_id,v_account_id,r->>'description',coalesce((r->>'debit')::numeric,0),coalesce((r->>'credit')::numeric,0),nullif(r->>'customer_id','')::uuid,nullif(r->>'vendor_id','')::uuid,nullif(r->>'contractor_id','')::uuid,nullif(r->>'po_id','')::uuid,nullif(r->>'product_id','')::uuid);
  end loop;

  insert into erp.account_daily_balances(balance_date,account_id,debit_total,credit_total)
  select v_gl_date,jl.account_id,sum(jl.debit),sum(jl.credit) from erp.journal_lines jl where jl.journal_entry_id=v_entry_id group by jl.account_id
  on conflict(balance_date,account_id) do update set debit_total=erp.account_daily_balances.debit_total+excluded.debit_total,credit_total=erp.account_daily_balances.credit_total+excluded.credit_total,updated_at=statement_timestamp();

  if v_gl_date<>p_transaction_date then
    insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
    values('journal_entries',v_entry_id,'POST',jsonb_build_object('economic_date',p_transaction_date,'transaction_date',v_gl_date,'period_shifted',true,'source_type',p_source_type,'source_id',p_source_id),erp.current_app_user_id(),'Late/backdated posting moved to open accounting period');
  end if;
  return v_entry_id;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_laundry_delivery(p_delivery_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare h erp.laundry_deliveries%rowtype; r record; v_group_total bigint; v_already_sent bigint; v_rate numeric(18,2); v_pickup timestamptz;
begin
  perform erp.require_internal();
  select * into h from erp.laundry_deliveries where id=p_delivery_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Laundry delivery must be DRAFT'; end if;
  if not exists(select 1 from erp.laundry_delivery_lines where delivery_id=h.id) then raise exception 'Laundry delivery has no lines'; end if;
  for r in select * from erp.laundry_delivery_lines where delivery_id=h.id loop
    if not exists(select 1 from erp.cutting_groups cg where cg.id=r.cutting_group_id and cg.po_id=h.po_id) then raise exception 'Cutting group does not belong to delivery PO'; end if;
    select picked_up_at into v_pickup from erp.cutting_groups where id=r.cutting_group_id;
    if v_pickup is null then raise exception 'Cutting group % has not been picked up by the mandor yet',r.cutting_group_id; end if;
    if h.physical_at<v_pickup then raise exception 'Tanggal/jam kirim laundry tidak boleh lebih awal dari tanggal/jam potongan diambil mandor'; end if;
    select total_pcs into v_group_total from erp.v_cutting_group_totals where cutting_group_id=r.cutting_group_id;
    select coalesce(sum(ldl2.qty_sent_pcs),0) into v_already_sent
    from erp.laundry_delivery_lines ldl2 join erp.laundry_deliveries ld2 on ld2.id=ldl2.delivery_id
    where ldl2.cutting_group_id=r.cutting_group_id and ld2.id<>h.id and ld2.status not in('DRAFT','REVERSED');
    if coalesce(v_group_total,0)<v_already_sent+r.qty_sent_pcs then
      raise exception 'Laundry qty exceeds effective cutting qty for group %. Effective %, already sent %, requested %. Post a local cutting quantity correction instead of reversing sibling groups.',r.cutting_group_id,coalesce(v_group_total,0),v_already_sent,r.qty_sent_pcs;
    end if;
    v_rate:=r.estimated_rate_snapshot;
    if v_rate is null and h.target_wash_process_id is not null then
      perform pg_advisory_xact_lock(hashtextextended('LRATE:'||h.vendor_id::text||':'||h.target_wash_process_id::text,0));
      select rate_per_pcs into v_rate from erp.laundry_vendor_rate_versions
      where vendor_id=h.vendor_id and wash_process_id=h.target_wash_process_id and effective_from<=h.physical_at and (effective_to is null or effective_to>h.physical_at)
      order by effective_from desc,created_at desc limit 1;
      if v_rate is not null then update erp.laundry_delivery_lines set estimated_rate_snapshot=v_rate,estimated_cost_status='ESTIMATED' where id=r.id; end if;
    end if;
    insert into erp.wip_stage_events(po_id,cutting_group_id,stage_from,stage_to,qty_pcs,contractor_id,source_type,source_id,physical_at,created_by,notes)
    select h.po_id,r.cutting_group_id,'SEWING','LAUNDRY',r.qty_sent_pcs,po.contractor_id,'LAUNDRY_DELIVERY_LINE',r.id,h.physical_at,erp.current_app_user_id(),h.target_dyeing_color
    from erp.production_orders po where po.id=h.po_id;
    update erp.cutting_groups set status='LAUNDRY' where id=r.cutting_group_id;
  end loop;
  update erp.laundry_deliveries set status='SENT',updated_at=statement_timestamp() where id=h.id;
  update erp.production_orders set status='LAUNDRY',current_stage='LAUNDRY',updated_at=statement_timestamp() where id=h.po_id;
  perform erp.sync_laundry_accrual(h.po_id,(h.physical_at AT TIME ZONE 'Asia/Jakarta')::date);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_laundry_receipt(p_receipt_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  h erp.laundry_receipts%rowtype;
  d erp.laundry_deliveries%rowtype;
  r record;
  a record;
  v_sent bigint;
  v_returned bigint;
  v_allocated integer;
  v_bs_number text;
begin
  perform erp.require_internal();
  select * into h from erp.laundry_receipts where id=p_receipt_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Laundry receipt must be DRAFT'; end if;
  select * into d from erp.laundry_deliveries where id=h.delivery_id for update;
  if d.status not in ('SENT','PARTIAL_RETURN') then raise exception 'Laundry delivery must already be sent'; end if;
  if not exists(select 1 from erp.laundry_receipt_lines where receipt_id=h.id) then
    raise exception 'Laundry receipt has no lines';
  end if;

  for r in
    select lrl.*,ldl.cutting_group_id
    from erp.laundry_receipt_lines lrl
    join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
    where lrl.receipt_id=h.id order by lrl.id
  loop
    select coalesce(sum(x.qty_bs),0)::integer into v_allocated
    from erp.laundry_receipt_bs_product_allocations x where x.receipt_line_id=r.id;
    if v_allocated<>r.qty_bs_laundry then
      raise exception 'Laundry BS product allocation % must equal BS qty % for receipt line %',
        v_allocated,r.qty_bs_laundry,r.id;
    end if;

    if r.qty_good_received+r.qty_bs_laundry>0 and exists(
      select 1
      from erp.laundry_claims lc
      left join erp.laundry_receipt_lines prior_line on prior_line.id=lc.receipt_line_id
      where lc.status in ('SETTLED','WRITTEN_OFF')
        and lc.claim_type in ('MISSING','STUCK')
        and (
          prior_line.delivery_line_id=r.delivery_line_id
          or (lc.receipt_line_id is null and lc.delivery_id=d.id)
        )
    ) then
      raise exception 'Late physical return is blocked after a STUCK/MISSING claim is SETTLED/WRITTEN_OFF; reverse the claim resolution first';
    end if;

    if r.qty_good_received+r.qty_bs_laundry>0 then
      insert into erp.wip_stage_events(
        po_id,cutting_group_id,stage_from,stage_to,qty_pcs,
        source_type,source_id,physical_at,created_by,notes
      ) values(
        d.po_id,r.cutting_group_id,'LAUNDRY','QC',r.qty_good_received+r.qty_bs_laundry,
        'LAUNDRY_RECEIPT_LINE',r.id,h.physical_at,erp.current_app_user_id(),
        'Physically returned from laundry'
      );
      update erp.cutting_groups set status='RETURNED' where id=r.cutting_group_id;
    end if;

    for a in
      select * from erp.laundry_receipt_bs_product_allocations
      where receipt_line_id=r.id order by id
    loop
      perform erp.assert_product_identity_time(a.product_id,h.physical_at,'NEW_STOCK');
      v_bs_number:='BS-LAU-'||left(h.receipt_number,28)||'-'||substr(r.id::text,1,8)||'-'||substr(a.id::text,1,6);
      insert into erp.bs_cases(
        bs_number,po_id,cutting_group_id,product_id,
        source_laundry_receipt_line_id,source_laundry_bs_allocation_id,
        detected_at_stage,cause_source,responsible_vendor_id,
        qty_pcs,status,physical_at,notes
      ) values(
        v_bs_number,d.po_id,r.cutting_group_id,a.product_id,r.id,a.id,
        'LAUNDRY','LAUNDRY',d.vendor_id,a.qty_bs,'OPEN',h.physical_at,
        'Auto-created from laundry receipt with product/size lineage'
      ) on conflict(source_laundry_bs_allocation_id) where source_laundry_bs_allocation_id is not null do nothing;
    end loop;
  end loop;

  update erp.laundry_receipts set status='POSTED',updated_at=statement_timestamp() where id=h.id;
  select coalesce(sum(qty_sent_pcs),0) into v_sent
  from erp.laundry_delivery_lines where delivery_id=d.id;
  select coalesce(sum(lrl.qty_good_received+lrl.qty_bs_laundry),0) into v_returned
  from erp.laundry_receipt_lines lrl
  join erp.laundry_receipts lr on lr.id=lrl.receipt_id
  where lr.delivery_id=d.id and lr.status='POSTED';
  update erp.laundry_deliveries
  set status=case when v_returned>=v_sent then 'RETURNED' else 'PARTIAL_RETURN' end,
      updated_at=statement_timestamp()
  where id=d.id;
  if v_returned>0 then
    update erp.production_orders set status='QC',current_stage='QC',updated_at=statement_timestamp() where id=d.po_id;
  end if;
  perform erp.sync_laundry_accrual(d.po_id,(h.physical_at AT TIME ZONE 'Asia/Jakarta')::date);
  if exists(select 1 from erp.fg_lots where po_id=d.po_id) then
    perform erp.rebuild_po_hpp(d.po_id,'Laundry receipt posted/corrected');
    perform erp.propagate_conversion_hpp_for_po(d.po_id);
    perform erp.sync_po_hpp_to_gl(d.po_id,(h.physical_at AT TIME ZONE 'Asia/Jakarta')::date);
  end if;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_material_supplier_invoice(p_invoice_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_n_before jsonb;v_n_purchases uuid[];
  h erp.material_supplier_invoices%rowtype;
  r record;
  v_capacity numeric;
  v_matched numeric;
  v_old_cost numeric;
  v_new_cost numeric;
  v_basis_qty numeric;
  v_delta_before numeric;
  v_delta_after numeric;
  v_inventory_delta numeric;
  v_liability_delta numeric;
  v_bridge numeric;
  v_purchase uuid;
  v_paid numeric;
  v_payable numeric;
begin
  perform erp.require_owner_admin();
  select * into h from erp.material_supplier_invoices where id=p_invoice_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Material supplier invoice must be DRAFT'; end if;
  if h.invoice_date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date then raise exception 'Supplier invoice date cannot be in the future'; end if;
  if (h.received_at AT TIME ZONE 'Asia/Jakarta')::date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date then raise exception 'Supplier invoice received_at cannot be in the future'; end if;
  if not exists(select 1 from erp.material_supplier_invoice_lines where invoice_id=h.id) then
    raise exception 'Material supplier invoice has no lines';
  end if;

  -- Deterministic lock order protects concurrent invoice/payment/return clicks.
  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.purchase_id
  loop
    perform 1 from erp.material_purchase_headers where id=v_purchase for update;
  end loop;
  select array_agg(distinct i.purchase_id order by i.purchase_id) into v_n_purchases
  from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=h.id;
  perform 1 from erp.material_purchase_headers where id=any(v_n_purchases) order by id for update;
  v_n_before:=erp._cp6_supplier_cent_state(v_n_purchases);
  for r in
    select distinct i.id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.id
  loop
    perform 1 from erp.material_purchase_items where id=r.id for update;
  end loop;

  for r in
    select l.*,i.qty as receipt_qty,i.unit_price as estimate_unit_cost,
           i.material_id,i.purchase_id,i.invoice_match_state,
           ph.supplier_id,ph.physical_at
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    join erp.material_purchase_headers ph on ph.id=i.purchase_id
    where l.invoice_id=h.id order by i.id
  loop
    if r.supplier_id is distinct from h.supplier_id then
      raise exception 'Invoice supplier does not match receipt supplier for item %',r.purchase_item_id;
    end if;
    if r.invoice_match_state='DIRECT_FINAL' then
      raise exception 'Receipt item % was already final-invoiced at physical receipt',r.purchase_item_id;
    end if;
    v_capacity:=erp.material_purchase_invoice_capacity(r.purchase_item_id);
    v_matched:=erp.material_purchase_posted_invoice_qty(r.purchase_item_id);
    if v_matched+r.qty_invoiced>v_capacity then
      raise exception 'Invoice quantity exceeds unmatched receipt quantity for item %. Capacity %, already matched %, requested %',
        r.purchase_item_id,v_capacity,v_matched,r.qty_invoiced;
    end if;

    v_old_cost:=erp.material_purchase_current_unit_cost(r.purchase_item_id);
    v_basis_qty:=v_capacity;
    select coalesce(sum(x.net_amount-(x.qty_invoiced*r.estimate_unit_cost)),0)
    into v_delta_before
    from erp.material_supplier_invoice_lines x
    join erp.material_supplier_invoices xh on xh.id=x.invoice_id
    where x.purchase_item_id=r.purchase_item_id and xh.status='POSTED';
    v_delta_after:=v_delta_before+(r.net_amount-(r.qty_invoiced*r.estimate_unit_cost));
    v_new_cost:=greatest(((v_basis_qty*r.estimate_unit_cost)+v_delta_after)/v_basis_qty,0);
    v_inventory_delta:=r.receipt_qty*(v_new_cost-v_old_cost);
    v_liability_delta:=r.net_amount-(r.qty_invoiced*r.estimate_unit_cost);
    v_bridge:=v_inventory_delta-v_liability_delta;

    update erp.material_supplier_invoice_lines
    set receipt_estimate_unit_cost_snapshot=r.estimate_unit_cost,
        prior_blended_unit_cost_snapshot=v_old_cost,
        posted_blended_unit_cost_snapshot=v_new_cost,
        grni_clear_amount_snapshot=r.qty_invoiced*r.estimate_unit_cost,
        ap_create_amount_snapshot=r.net_amount,
        inventory_revaluation_snapshot=v_inventory_delta,
        bridge_variance_snapshot=v_bridge
    where id=r.id;

  end loop;

  update erp.material_supplier_invoices
  set status='POSTED',posted_at=clock_timestamp(),posting_reason=coalesce(posting_reason,'Supplier invoice posted')
  where id=h.id;

  for r in
    select distinct l.purchase_item_id
    from erp.material_supplier_invoice_lines l
    where l.invoice_id=h.id order by l.purchase_item_id
  loop
    perform erp.refresh_material_purchase_item_cost(r.purchase_item_id);
    perform erp.refresh_material_purchase_item_match_state(r.purchase_item_id);
  end loop;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.purchase_id
  loop
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0)
    into v_payable,v_paid;
    update erp.material_purchase_headers
    set supplier_invoice_number=h.invoice_number,
        due_date=coalesce(h.due_date,due_date),
        payment_status=case when v_paid=round(v_payable,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end
    where id=v_purchase;
  end loop;
  perform erp._cp6_apply_supplier_cent_event('MATERIAL_SUPPLIER_INVOICE',h.id,h.invoice_date,'Supplier document cents '||h.id::text,v_n_before,false);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_material_supplier_return(p_return_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_n_before jsonb;v_n_purchases uuid[];
  h erp.material_supplier_returns%rowtype;
  r record;
  v_purchase uuid;
  v_invoiced_qty numeric;
  v_prior_ap_qty numeric;
  v_current_purchase_item uuid;
  v_document_ap_qty numeric:=0;
  v_ap_qty numeric;
  v_grni_qty numeric;
  v_paid numeric;
  v_payable numeric;
  v_proposed_relief numeric;
begin
  perform erp.require_internal();
  select * into h from erp.material_supplier_returns where id=p_return_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Supplier return must be DRAFT'; end if;
  if h.location_id is null then raise exception 'Supplier return location is required'; end if;
  if not exists(select 1 from erp.material_supplier_return_items where return_id=h.id) then
    raise exception 'Supplier return has no lines';
  end if;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by i.purchase_id
  loop
    perform 1 from erp.material_purchase_headers where id=v_purchase for update;
  end loop;

  select array_agg(distinct i.purchase_id order by i.purchase_id) into v_n_purchases
  from erp.material_supplier_return_items l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.return_id=h.id;
  perform 1 from erp.material_purchase_headers where id=any(v_n_purchases) order by id for update;
  v_n_before:=erp._cp6_supplier_cent_state(v_n_purchases);
  -- Allocate each physical return against already-final AP first; any remaining
  -- quantity cancels the receipt estimate in GRNI. These snapshots are immutable
  -- once the document posts and make reversal deterministic.
  for r in
    select ri.*,i.qty as receipt_qty,i.unit_price as estimate_unit_cost,
           i.invoice_match_state,i.purchase_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by i.id,ri.id
  loop
    perform 1 from erp.material_purchase_items where id=r.purchase_item_id for update;
    if v_current_purchase_item is distinct from r.purchase_item_id then
      v_current_purchase_item:=r.purchase_item_id;
      v_document_ap_qty:=0;
      v_invoiced_qty:=case when r.invoice_match_state='DIRECT_FINAL'
        then r.receipt_qty else erp.material_purchase_posted_invoice_qty(r.purchase_item_id) end;
      select coalesce(sum(coalesce(x.ap_relief_qty_snapshot,0)),0)
      into v_prior_ap_qty
      from erp.material_supplier_return_items x
      join erp.material_supplier_returns xh on xh.id=x.return_id
      where x.purchase_item_id=r.purchase_item_id and xh.status='POSTED';
    end if;
    v_ap_qty:=least(r.qty,
      greatest(v_invoiced_qty-v_prior_ap_qty-v_document_ap_qty,0));
    v_grni_qty:=r.qty-v_ap_qty;
    update erp.material_supplier_return_items
    set ap_relief_qty_snapshot=v_ap_qty,
        grni_relief_qty_snapshot=v_grni_qty,
        ap_relief_amount_snapshot=v_ap_qty*r.supplier_credit_unit_price,
        grni_relief_amount_snapshot=v_grni_qty*r.estimate_unit_cost
    where id=r.id;
    v_document_ap_qty:=v_document_ap_qty+v_ap_qty;
  end loop;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by i.purchase_id
  loop
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0),
           coalesce(sum(ri.ap_relief_amount_snapshot),0)
    into v_payable,v_paid,v_proposed_relief
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id and i.purchase_id=v_purchase;
    if v_paid>round(v_payable-v_proposed_relief,2) then
      raise exception 'Supplier return would make payment % exceed projected final AP %. Reverse/correct supplier payment first.',
        v_paid,v_payable-v_proposed_relief;
    end if;
  end loop;

  update erp.material_supplier_returns set status='POSTED' where id=h.id;

  for r in
    select ri.*
    from erp.material_supplier_return_items ri
    where ri.return_id=h.id order by ri.material_id,ri.id
  loop
    insert into erp.material_stock_movements(
      material_id,roll_id,location_id,movement_type,qty_signed,
      source_type,source_id,physical_at,created_by,note
    ) values(
      r.material_id,r.roll_id,h.location_id,'SUPPLIER_RETURN',-r.qty,
      'MATERIAL_SUPPLIER_RETURN_ITEM',r.id,h.physical_at,erp.current_app_user_id(),h.reason
    );

    -- GRNI-backed returns reduce the cost-basis quantity. Recompute the source
    -- purchase layer before replaying chronological MA.
    perform erp.refresh_material_purchase_item_cost(r.purchase_item_id);
    perform erp.refresh_material_purchase_item_match_state(r.purchase_item_id);
    if r.roll_id is not null then
      update erp.material_rolls
      set status=case when cached_qty=0 then 'RETURNED_SUPPLIER' else status end,updated_at=statement_timestamp()
      where id=r.roll_id;
    end if;
  end loop;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by i.purchase_id
  loop
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0)
    into v_payable,v_paid;
    update erp.material_purchase_headers
    set payment_status=case when v_paid=round(v_payable,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end
    where id=v_purchase;
  end loop;
  perform erp._cp6_apply_supplier_cent_event('MATERIAL_SUPPLIER_RETURN',h.id,erp._cp3_business_date(h.physical_at),'Supplier document cents '||h.id::text,v_n_before,false);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_opening_financial_correction(p_opening_item_id uuid, p_corrected_amount numeric, p_reason text, p_effective_date date DEFAULT ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  i erp.opening_balance_items%rowtype;
  h_status text;
  b erp.opening_subledger_balances%rowtype;
  v_old numeric(20,2);
  v_new numeric(20,2);
  v_delta numeric(20,2);
  v_id uuid;
  v_no text;
  v_lines jsonb:='[]'::jsonb;
  v_cash uuid;
  v_abs numeric(20,2);
  v_seq bigint;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan koreksi saldo awal wajib diisi'; end if;
  if p_corrected_amount is null or p_corrected_amount<0 then raise exception 'Saldo awal hasil koreksi tidak boleh negatif'; end if;
  if p_effective_date is null then raise exception 'Tanggal koreksi saldo awal wajib diisi'; end if;

  select * into i from erp.opening_balance_items where id=p_opening_item_id for update;
  if i.id is null then raise exception 'Item saldo awal tidak ditemukan'; end if;
  select status into h_status from erp.opening_balance_headers where id=i.opening_id for update;
  if h_status<>'POSTED' then raise exception 'Saldo awal harus sudah POSTED sebelum dikoreksi'; end if;
  if i.balance_type not in ('WIP','CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE','VENDOR_PAYABLE','SUPPLIER_PAYABLE','CUSTOMER_RECEIVABLE','CASH_BANK') then
    raise exception 'Jenis saldo awal % tidak dikoreksi lewat jalur finansial ini. Stok MATERIAL/FG gunakan stock adjustment agar lineage tetap aman.',i.balance_type;
  end if;

  select coalesce(max(c.correction_seq),0)+1
    into v_seq
  from erp.opening_financial_corrections c
  where c.opening_item_id=i.id;

  if i.balance_type in ('CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE','VENDOR_PAYABLE','SUPPLIER_PAYABLE','CUSTOMER_RECEIVABLE') then
    select * into b from erp.opening_subledger_balances where opening_item_id=i.id for update;
    if b.id is null then raise exception 'Opening subledger untuk item ini tidak ditemukan'; end if;
    v_old:=b.original_amount;
    if round(p_corrected_amount,2) < b.settled_amount then
      raise exception 'Saldo awal tidak boleh dikoreksi menjadi % karena sudah disettle %. Reverse settlement terkait terlebih dahulu.',p_corrected_amount,b.settled_amount;
    end if;
  else
    select coalesce((select c.corrected_amount from erp.opening_financial_corrections c where c.opening_item_id=i.id and c.status='POSTED' order by c.correction_seq desc limit 1),
                    case when i.balance_type='WIP' then coalesce(i.amount,coalesce(i.qty,0)*coalesce(i.unit_cost_snapshot,0)) else coalesce(i.amount,0) end)::numeric(20,2)
    into v_old;
  end if;

  v_new:=round(p_corrected_amount::numeric,2);
  v_delta:=v_new-v_old;
  if abs(v_delta)<=0.005 then raise exception 'Nilai koreksi sama dengan saldo awal efektif saat ini (%)',v_old; end if;
  v_no:='OFC-'||to_char((clock_timestamp() AT TIME ZONE 'Asia/Jakarta'),'YYYYMMDDHH24MISSMS')||'-'||substr(gen_random_uuid()::text,1,6);
  insert into erp.opening_financial_corrections(correction_number,opening_item_id,previous_amount_snapshot,corrected_amount,delta_amount,effective_date,reason,created_by,created_at,correction_seq)
  values(v_no,i.id,v_old,v_new,v_delta,p_effective_date,p_reason,erp.current_app_user_id(),clock_timestamp(),v_seq) returning id into v_id;

  v_abs:=round(abs(v_delta),2);
  if i.balance_type='CASH_BANK' then
    select coa_account_id into v_cash from erp.cash_accounts where id=i.cash_account_id;
    if v_cash is null then raise exception 'Cash/bank account saldo awal tidak ditemukan'; end if;
    if v_delta>0 then v_lines:=jsonb_build_array(
      jsonb_build_object('account_id',v_cash,'debit',v_abs,'credit',0),
      jsonb_build_object('mapping_key','OPENING_EQUITY','debit',0,'credit',v_abs));
    else v_lines:=jsonb_build_array(
      jsonb_build_object('mapping_key','OPENING_EQUITY','debit',v_abs,'credit',0),
      jsonb_build_object('account_id',v_cash,'debit',0,'credit',v_abs)); end if;
  elsif i.balance_type in ('WIP','CUSTOMER_RECEIVABLE','CONTRACTOR_RECEIVABLE') then
    if v_delta>0 then v_lines:=jsonb_build_array(
      case when i.balance_type='WIP' then jsonb_build_object('mapping_key','WIP','debit',v_abs,'credit',0)
           when i.balance_type='CUSTOMER_RECEIVABLE' then jsonb_build_object('mapping_key','AR_CUSTOMER','debit',v_abs,'credit',0,'customer_id',i.customer_id)
           else jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',v_abs,'credit',0,'contractor_id',i.contractor_id) end,
      jsonb_build_object('mapping_key','OPENING_EQUITY','debit',0,'credit',v_abs));
    else v_lines:=jsonb_build_array(
      jsonb_build_object('mapping_key','OPENING_EQUITY','debit',v_abs,'credit',0),
      case when i.balance_type='WIP' then jsonb_build_object('mapping_key','WIP','debit',0,'credit',v_abs)
           when i.balance_type='CUSTOMER_RECEIVABLE' then jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',v_abs,'customer_id',i.customer_id)
           else jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',0,'credit',v_abs,'contractor_id',i.contractor_id) end); end if;
  else
    if v_delta>0 then v_lines:=jsonb_build_array(
      jsonb_build_object('mapping_key','OPENING_EQUITY','debit',v_abs,'credit',0),
      case when i.balance_type='SUPPLIER_PAYABLE' then jsonb_build_object('mapping_key','AP_SUPPLIER','debit',0,'credit',v_abs)
           when i.balance_type='VENDOR_PAYABLE' then jsonb_build_object('mapping_key','AP_VENDOR','debit',0,'credit',v_abs,'vendor_id',i.vendor_id)
           else jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',v_abs,'contractor_id',i.contractor_id) end);
    else v_lines:=jsonb_build_array(
      case when i.balance_type='SUPPLIER_PAYABLE' then jsonb_build_object('mapping_key','AP_SUPPLIER','debit',v_abs,'credit',0)
           when i.balance_type='VENDOR_PAYABLE' then jsonb_build_object('mapping_key','AP_VENDOR','debit',v_abs,'credit',0,'vendor_id',i.vendor_id)
           else jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',v_abs,'credit',0,'contractor_id',i.contractor_id) end,
      jsonb_build_object('mapping_key','OPENING_EQUITY','debit',0,'credit',v_abs)); end if;
  end if;

  perform erp.post_journal('OPENING_FINANCIAL_CORRECTION',v_id,p_effective_date,'Correction saldo awal: '||p_reason,v_lines);
  if b.id is not null then
    update erp.opening_subledger_balances
    set original_amount=v_new,
        status=case when settled_amount=v_new then 'SETTLED' when settled_amount>0 then 'PARTIAL' else 'OPEN' end,
        updated_at=statement_timestamp()
    where id=b.id;
  end if;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('opening_balance_items',i.id,'UPDATE',jsonb_build_object('correction_id',v_id,'previous_amount',v_old,'corrected_amount',v_new,'delta',v_delta,'correction_type','OPENING_FINANCIAL_CORRECTION'),erp.current_app_user_id(),p_reason);
  return v_id;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_opening_hpp_correction(p_lot_id uuid, p_new_hpp numeric, p_reason text, p_effective_date date DEFAULT ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare l erp.fg_lots%rowtype;v_old_id uuid;v_old_hpp numeric(20,6);v_ver integer;v_new_id uuid;v_corr uuid;v_no text;
begin
  perform erp.require_owner_admin();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan koreksi HPP opening wajib diisi'; end if;
  if p_new_hpp is null or p_new_hpp<0 then raise exception 'HPP opening hasil koreksi tidak boleh negatif'; end if;
  select * into l from erp.fg_lots where id=p_lot_id for update;
  if l.id is null or l.lot_origin<>'OPENING' then raise exception 'Koreksi HPP opening hanya untuk lot saldo awal'; end if;
  if exists(select 1 from erp.product_conversion_allocations pca join erp.product_conversions pc on pc.id=pca.conversion_id where pca.source_lot_id=l.id and pc.status='POSTED') then
    raise exception 'Lot opening sudah pernah dipakai conversion/rebrand. Reverse/correct conversion tersebut dulu sebelum mengubah HPP opening.';
  end if;
  perform erp.assert_non_po_product_hpp_target_book_v2620f(l.product_id);
  select hpp_version_id,hpp_per_pcs into v_old_id,v_old_hpp from erp.v_current_hpp where lot_id=l.id;
  if v_old_id is null then raise exception 'Current HPP lot opening tidak ditemukan'; end if;
  if abs(v_old_hpp-p_new_hpp)<=0.000001 then raise exception 'HPP baru sama dengan HPP current (%)',v_old_hpp; end if;
  select coalesce(max(version_no),0)+1 into v_ver from erp.hpp_versions where lot_id=l.id;
  update erp.hpp_versions set is_current=false where lot_id=l.id and is_current=true;
  insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,supersedes_id,calculation_reason,created_by)
  values(l.id,v_ver,'ADJUSTED',l.initial_qty_pcs,l.initial_qty_pcs*p_new_hpp,true,v_old_id,'Controlled opening HPP correction: '||p_reason,erp.current_app_user_id()) returning id into v_new_id;
  v_no:='OHPP-'||to_char((clock_timestamp() AT TIME ZONE 'Asia/Jakarta'),'YYYYMMDDHH24MISSMS')||'-'||substr(gen_random_uuid()::text,1,6);
  insert into erp.opening_hpp_corrections(correction_number,lot_id,previous_hpp_snapshot,corrected_hpp,effective_date,reason,hpp_version_id,created_by)
  values(v_no,l.id,v_old_hpp,p_new_hpp,p_effective_date,p_reason,v_new_id,erp.current_app_user_id()) returning id into v_corr;
  perform erp.sync_opening_lot_hpp_to_gl(l.id,p_effective_date);
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('fg_lots',l.id,'UPDATE',jsonb_build_object('correction_id',v_corr,'previous_hpp',v_old_hpp,'corrected_hpp',p_new_hpp),erp.current_app_user_id(),p_reason);
  return v_corr;
end;$function$;

CREATE OR REPLACE FUNCTION erp.post_opening_hpp_correction_from_price_percent(p_lot_id uuid, p_percent numeric, p_reason text, p_effective_date date DEFAULT ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  l erp.fg_lots%rowtype;
  v_price numeric(20,6);
  v_hpp numeric(20,6);
  v_corr uuid;
begin
  perform erp.require_owner_admin();
  if p_percent is null or p_percent<=0 or p_percent>1000 then raise exception 'Persentase HPP harus >0 dan masuk akal'; end if;
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan koreksi HPP opening wajib diisi'; end if;

  select * into l from erp.fg_lots where id=p_lot_id for update;
  if l.id is null or l.lot_origin<>'OPENING' then raise exception 'Lot opening tidak ditemukan'; end if;

  -- Business rule: percentage-based opening HPP is always based on the selling
  -- price valid at the opening/cutover physical timestamp. A later correction
  -- date changes the correction journal date, not the historical price basis.
  v_price:=erp.resolve_product_price_at(l.product_id,l.produced_at);
  if v_price is null then
    raise exception 'Harga jual historis produk tidak tersedia pada waktu opening/cutover %. Isi histori harga tersebut atau gunakan koreksi HPP manual.',l.produced_at;
  end if;

  v_hpp:=round(v_price*p_percent/100.0,6);
  v_corr:=erp.post_opening_hpp_correction(l.id,v_hpp,p_reason,p_effective_date);
  update erp.opening_hpp_corrections
  set source_method='PRICE_PERCENT',reference_sell_price_snapshot=v_price,percent_of_price=p_percent
  where id=v_corr;
  return v_corr;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_opening_subledger_settlement(p_settlement_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
DECLARE s erp.opening_subledger_settlements%ROWTYPE;b erp.opening_subledger_balances%ROWTYPE;v_cash uuid;v_remaining numeric(20,2);v_lines jsonb;
BEGIN PERFORM erp.require_owner_admin();SELECT * INTO s FROM erp.opening_subledger_settlements WHERE id=p_settlement_id FOR UPDATE;IF s.id IS NULL OR s.status<>'DRAFT' THEN RAISE EXCEPTION 'Opening subledger settlement must be DRAFT';END IF;SELECT * INTO b FROM erp.opening_subledger_balances WHERE id=s.balance_id FOR UPDATE;IF b.id IS NULL OR b.status='SETTLED' THEN RAISE EXCEPTION 'Opening subledger balance is not open';END IF;v_remaining:=b.original_amount-b.settled_amount;IF s.amount>v_remaining THEN RAISE EXCEPTION 'Settlement exceeds opening outstanding. Remaining %, requested %',v_remaining,s.amount;END IF;SELECT coa_account_id INTO v_cash FROM erp.cash_accounts WHERE id=s.cash_account_id AND is_active=true;IF v_cash IS NULL THEN RAISE EXCEPTION 'Active cash/bank account is required';END IF;
IF b.direction='RECEIVABLE' AND b.party_type='CUSTOMER' THEN v_lines:=jsonb_build_array(jsonb_build_object('account_id',v_cash,'debit',s.amount,'credit',0,'customer_id',b.customer_id),jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',s.amount,'customer_id',b.customer_id));ELSIF b.direction='RECEIVABLE' AND b.party_type='CONTRACTOR' THEN v_lines:=jsonb_build_array(jsonb_build_object('account_id',v_cash,'debit',s.amount,'credit',0,'contractor_id',b.contractor_id),jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',0,'credit',s.amount,'contractor_id',b.contractor_id));ELSIF b.direction='PAYABLE' AND b.party_type='SUPPLIER' THEN v_lines:=jsonb_build_array(jsonb_build_object('mapping_key','AP_SUPPLIER','debit',s.amount,'credit',0),jsonb_build_object('account_id',v_cash,'debit',0,'credit',s.amount));ELSIF b.direction='PAYABLE' AND b.party_type='VENDOR' THEN v_lines:=jsonb_build_array(jsonb_build_object('mapping_key','AP_VENDOR','debit',s.amount,'credit',0,'vendor_id',b.vendor_id),jsonb_build_object('account_id',v_cash,'debit',0,'credit',s.amount,'vendor_id',b.vendor_id));ELSIF b.direction='PAYABLE' AND b.party_type='CONTRACTOR' THEN v_lines:=jsonb_build_array(jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',s.amount,'credit',0,'contractor_id',b.contractor_id),jsonb_build_object('account_id',v_cash,'debit',0,'credit',s.amount,'contractor_id',b.contractor_id));ELSE RAISE EXCEPTION 'Unsupported opening subledger direction/party combination';END IF;
PERFORM erp.post_journal('OPENING_SUBLEDGER_SETTLEMENT',s.id,erp._cp3_business_date(s.physical_at),'Opening subledger settlement '||s.settlement_number,v_lines);UPDATE erp.opening_subledger_settlements SET status='POSTED',updated_at=statement_timestamp() WHERE id=s.id;UPDATE erp.opening_subledger_balances SET settled_amount=settled_amount+s.amount,status=CASE WHEN settled_amount+s.amount=original_amount THEN 'SETTLED' ELSE 'PARTIAL' END,updated_at=statement_timestamp() WHERE id=b.id;END;$function$;

CREATE OR REPLACE FUNCTION erp.post_payroll_payment(p_payroll_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  p erp.payroll_settlements%rowtype;
  v_cash uuid;
  v_material_deduction numeric(20,2):=0;
  v_other_deduction numeric(20,2):=0;
  v_expected_attendance numeric(20,2):=0;
  v_actual_attendance numeric(20,2):=0;
  v_attendance_journal_count bigint:=0;
  r record;
begin
  perform erp.require_internal();
  select * into p from erp.payroll_settlements where id=p_payroll_id for update;
  if p.id is null or p.status<>'APPROVED' then raise exception 'Payroll must be APPROVED'; end if;
  perform erp._cp3_lock_business_period(p.period_start,p.period_end);
  if p.net_payable<0 then raise exception 'Payroll net payable cannot be negative; carry deductions forward instead'; end if;
  if p.payment_date is null then raise exception 'Payroll payment date is required'; end if;
  if p.payment_date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date then raise exception 'Tanggal pembayaran payroll berada di masa depan'; end if;
  if p.net_payable>0 then
    select coa_account_id into v_cash from erp.cash_accounts where id=p.payment_cash_account_id and is_active=true;
    if v_cash is null then raise exception 'Active payroll cash/bank account is required when cash payment is positive'; end if;
  end if;

  v_expected_attendance:=round(coalesce(p.attendance_total,0),2);
  select count(distinct je.id),coalesce(sum(jl.debit),0)
    into v_attendance_journal_count,v_actual_attendance
  from erp.journal_entries je
  join erp.journal_lines jl on jl.journal_entry_id=je.id
  where je.source_type='PAYROLL_ATTENDANCE_ACCRUAL' and je.source_id=p.id and je.status='POSTED'
    and jl.account_id=erp.account_id('WIP') and jl.debit>0;
  if (v_expected_attendance=0 and v_attendance_journal_count<>0)
     or (v_expected_attendance>0 and (v_attendance_journal_count<>1 or round(v_actual_attendance,2) is distinct from v_expected_attendance)) then
    raise exception 'PAYROLL_APPROVAL_ACCRUAL_MISSING_OR_MISMATCH: expected attendance %, journal count %, WIP debit %',
      v_expected_attendance,v_attendance_journal_count,round(v_actual_attendance,2);
  end if;

  select coalesce(sum(amount),0) into v_material_deduction
  from erp.payroll_deductions where payroll_id=p.id and deduction_type='MATERIAL_KASBON';
  select coalesce(sum(amount),0) into v_other_deduction
  from erp.payroll_deductions where payroll_id=p.id and deduction_type<>'MATERIAL_KASBON';
  if v_material_deduction>0 then
    perform erp.post_journal('PAYROLL_MATERIAL_DEDUCTION',p.id,p.payment_date,
      'Physical material/accessory purchase deduction',jsonb_build_array(
        jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',v_material_deduction,'credit',0,'contractor_id',p.contractor_id),
        jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',0,'credit',v_material_deduction,'contractor_id',p.contractor_id)));
  end if;
  if v_other_deduction>0 then
    perform erp.post_journal('PAYROLL_OTHER_DEDUCTION',p.id,p.payment_date,
      'BS/penalty/other payroll deduction',jsonb_build_array(
        jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',v_other_deduction,'credit',0,'contractor_id',p.contractor_id),
        jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',v_other_deduction,'contractor_id',p.contractor_id)));
  end if;
  if p.net_payable>0 then
    perform erp.post_journal('PAYROLL_PAYMENT',p.id,p.payment_date,'Mandor payroll payment',jsonb_build_array(
      jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',p.net_payable,'credit',0,'contractor_id',p.contractor_id),
      jsonb_build_object('account_id',v_cash,'debit',0,'credit',p.net_payable,'contractor_id',p.contractor_id)));
  end if;

  update erp.payroll_settlements set status='PAID',settled_at=statement_timestamp(),updated_at=statement_timestamp() where id=p.id;
  for r in select distinct pd.contractor_issue_item_id id from erp.payroll_deductions pd
           where pd.payroll_id=p.id and pd.contractor_issue_item_id is not null
  loop perform erp.refresh_contractor_issue_payroll_status(r.id); end loop;
  update erp.contractor_accessory_reimbursement_entitlements e set payroll_status='SETTLED'
  where e.id in(select pr.source_id from erp.payroll_reimbursements pr
                where pr.payroll_id=p.id and pr.source_type='ACCESSORY_BOM' and pr.source_id is not null);
  for r in
    select distinct bc.id as bs_case_id from erp.bs_cases bc
    where exists(select 1 from erp.payroll_work_items pwi where pwi.payroll_id=p.id and pwi.po_id=bc.po_id)
       or exists(select 1 from erp.payroll_work_items pwi join erp.rework_component_lines rcl on rcl.id=pwi.source_id
                 join erp.bs_case_components bcc on bcc.id=rcl.bs_case_component_id
                 where pwi.payroll_id=p.id and bcc.bs_case_id=bc.id)
  loop perform erp.rebuild_bs_component_counters(r.bs_case_id); end loop;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('payroll_settlements',p.id,'POST',
    jsonb_build_object('lifecycle_action','PAY','payment_settlement_only',true,'attendance_accrual_created_at_payment',false),
    erp.current_app_user_id(),'Payroll payment settled approved payable without recognizing attendance cost again');
end;
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
    where fl.product_id=h.from_product_id and fl.po_id is null
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
    where fl.product_id=h.from_product_id and fl.po_id is not null
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
    where a.conversion_id=h.id order by fl.po_id
  loop
    perform erp.propagate_conversion_hpp_for_po(v_po);
    perform erp.refresh_po_hpp_gl_baseline(v_po);
    perform erp.assert_po_hpp_target_book_v2620e(v_po);
  end loop;
end
$function$;

CREATE OR REPLACE FUNCTION erp.post_qc(p_qc_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.qc_inspections%rowtype;
  r record;
  v_lot_id uuid;
  v_lot_number text;
begin
  perform erp.require_internal();
  select * into h from erp.qc_inspections where id=p_qc_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'QC must be DRAFT'; end if;
  if h.destination_location_id is null then raise exception 'QC destination FG location is required'; end if;
  if not exists(select 1 from erp.qc_inspection_items where inspection_id=h.id) then raise exception 'QC has no items'; end if;

  -- Validate all SKU identities before creating any FG/BS side effect.
  for r in
    select qi.*,p.sku
    from erp.qc_inspection_items qi
    join erp.products p on p.id=qi.final_product_id
    where qi.inspection_id=h.id
    order by qi.id
  loop
    perform erp.assert_product_identity_time(r.final_product_id,h.physical_at,'NEW_STOCK');
  end loop;

  for r in
    select qi.*,p.sku
    from erp.qc_inspection_items qi
    join erp.products p on p.id=qi.final_product_id
    where qi.inspection_id=h.id
    order by qi.id
  loop
    if r.qty_good_pcs>0 then
      v_lot_number:=h.inspection_number||'-'||regexp_replace(r.sku,'[^A-Za-z0-9]+','','g')||'-'||substr(r.id::text,1,8);
      insert into erp.fg_lots(
        lot_number,po_id,qc_item_id,cutting_group_id,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,lot_origin
      ) values(
        v_lot_number,h.po_id,r.id,r.cutting_group_id,r.final_product_id,r.qty_good_pcs,0,h.physical_at,'PRODUCTION'
      ) returning id into v_lot_id;
      perform erp.post_fg_movement(r.final_product_id,v_lot_id,h.destination_location_id,'GRADE_A','QC_GOOD',r.qty_good_pcs,0,null,'QC_ITEM',r.id,h.physical_at,'QC good output',false);
      perform erp.ensure_fg_accessory_cost_snapshot(v_lot_id);
      perform erp.post_accessory_reimbursement_accrual(v_lot_id);
    end if;

    if r.qty_bs_pcs>0 then
      insert into erp.bs_cases(bs_number,po_id,cutting_group_id,qc_item_id,product_id,detected_at_stage,cause_source,qty_pcs,status,physical_at,notes)
      values('BS-QC-'||h.inspection_number||'-'||substr(r.id::text,1,8),h.po_id,r.cutting_group_id,r.id,r.final_product_id,'QC','UNKNOWN',r.qty_bs_pcs,'OPEN',h.physical_at,'Detected at QC; classify cause when known')
      on conflict(bs_number) do nothing;
    end if;
  end loop;

  update erp.qc_inspections set status='POSTED',updated_at=statement_timestamp() where id=h.id;
  update erp.production_orders set status='QC',current_stage='QC',updated_at=statement_timestamp() where id=h.po_id;
  perform erp.sync_laundry_accrual(h.po_id,(h.physical_at AT TIME ZONE 'Asia/Jakarta')::date);
  perform erp.rebuild_po_hpp(h.po_id,'QC posted / batch-lineage HPP snapshot / output lot created');
  perform erp.propagate_conversion_hpp_for_po(h.po_id);
  perform erp.sync_po_hpp_to_gl(h.po_id,(h.physical_at AT TIME ZONE 'Asia/Jakarta')::date);
end$function$;

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
      v_lot_number,b.po_id,b.qc_item_id,b.cutting_group_id,b.product_id,
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

CREATE OR REPLACE FUNCTION erp.post_sale(p_sale_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  h erp.sales_headers%rowtype;
  r record;
  v_sales numeric(24,6):=0;
  v_item_qty bigint;
  v_reserved_qty bigint;
  v_delta_cogs numeric(24,6);
  v_delta_fg numeric(24,6);
  v_delta_other numeric(24,6);
  v_target_hpp numeric(24,6);
  v_target_other numeric(24,6);
  v_book_hpp numeric(24,6);
  v_book_other numeric(24,6);
  v_lines jsonb:='[]'::jsonb;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into h from erp.sales_headers where id=p_sale_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Sale must be DRAFT'; end if;
  if h.source_location_id is null then raise exception 'Sale source FG location is required'; end if;
  if not exists(select 1 from erp.sales_items where sale_id=p_sale_id) then raise exception 'Sale has no items'; end if;

  select coalesce(sum(qty_pcs),0),coalesce(sum(line_total),0)
  into v_item_qty,v_sales from erp.sales_items where sale_id=h.id;
  select coalesce(sum(abs(m.qty_signed)),0) into v_reserved_qty
  from erp.fg_stock_movements m
  join erp.sales_items i on i.id=m.source_id
  where i.sale_id=h.id and m.source_type='SALE_ITEM' and m.movement_type='SALE_RESERVE'
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);

  if v_reserved_qty=0 then v_reserved_qty:=erp._reserve_sale_draft(h.id); end if;
  if v_reserved_qty<>v_item_qty then
    raise exception 'Sale Draft reservation mismatch. Items %, active reservation %',v_item_qty,v_reserved_qty;
  end if;
  if exists(
    select 1 from erp.sales_items i
    left join(select sale_item_id,sum(qty_pcs)::bigint qty_pcs
      from erp.sale_stock_allocations group by sale_item_id) a on a.sale_item_id=i.id
    where i.sale_id=h.id and coalesce(a.qty_pcs,0)<>i.qty_pcs
  ) then raise exception 'Sale allocation does not match Draft line quantity'; end if;

  for r in
    select distinct fl.product_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  update erp.sale_stock_allocations a
  set unit_hpp_snapshot=coalesce(erp.lock_current_hpp_per_pcs(a.lot_id),0)
  from erp.sales_items i
  where i.id=a.sale_item_id and i.sale_id=h.id;

  update erp.fg_stock_movements m
  set unit_hpp_snapshot=a.unit_hpp_snapshot
  from erp.sales_items i
  join erp.sale_stock_allocations a on a.sale_item_id=i.id
  where i.id=m.source_id and i.sale_id=h.id
    and a.lot_id=m.lot_id
    and m.source_type='SALE_ITEM' and m.movement_type='SALE_RESERVE'
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);

  update erp.fg_stock_movements m
  set movement_type='SALE',notes='Sale posted · quantity reserved in Draft; HPP frozen at POST'
  from erp.sales_items i
  where i.id=m.source_id and i.sale_id=h.id
    and m.source_type='SALE_ITEM' and m.movement_type='SALE_RESERVE'
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);

  update erp.sales_headers set status='POSTED' where id=h.id;
  if abs(v_sales)>0.005 then
    v_lines:=v_lines||jsonb_build_array(
      jsonb_build_object('mapping_key','AR_CUSTOMER','debit',round(v_sales,2),'credit',0,'customer_id',h.customer_id),
      jsonb_build_object('mapping_key','SALES_REVENUE','debit',0,'credit',round(v_sales,2),'customer_id',h.customer_id));
  end if;

  -- One cumulative target per product, composed from per-lot lifecycle truth.
  for r in
    select distinct fl.product_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    select round(t.fg_value-b.fg_value,2),
      round(t.cogs_value-b.cogs_value,2),
      round(t.other_out_value-b.other_out_value,2)
    into v_delta_fg,v_delta_cogs,v_delta_other
    from erp.compute_non_po_product_hpp_targets_v2620f(r.product_id) t
    cross join lateral erp.compute_non_po_product_hpp_book_v2620f(r.product_id) b;
    if abs(v_delta_fg+v_delta_cogs+v_delta_other)>0.005 then
      raise exception 'Sale non-PO HPP delta does not conserve source value for product %: fg %, cogs %, other %',
        r.product_id,v_delta_fg,v_delta_cogs,v_delta_other;
    end if;
    if abs(v_delta_fg)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_fg>0
        then jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_delta_fg,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,
          'credit',abs(v_delta_fg),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
    if abs(v_delta_cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_cogs>0
        then jsonb_build_object('mapping_key','COGS','debit',v_delta_cogs,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','COGS','debit',0,
          'credit',abs(v_delta_cogs),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
    if abs(v_delta_other)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_other>0
        then jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_delta_other,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,
          'credit',abs(v_delta_other),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
  end loop;

  for r in
    select distinct fl.po_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is not null
    order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    select
      round(coalesce(t.cogs_value,0),2)-s.cogs_value,
      round(coalesce(t.fg_value,0),2)-s.fg_value,
      (round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)
        -round(coalesce(t.cogs_value,0),2))-s.other_out_value,
      round(coalesce(t.hpp_total_cost,0),2),
      round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)-round(coalesce(t.cogs_value,0),2),
      s.hpp_total_cost,s.other_out_value
    into v_delta_cogs,v_delta_fg,v_delta_other,
      v_target_hpp,v_target_other,v_book_hpp,v_book_other
    from erp.po_hpp_gl_state s
    cross join lateral erp.compute_po_hpp_gl_targets_v2620d(r.po_id) t
    where s.po_id=r.po_id for update of s;
    if v_delta_cogs<-0.005 or v_delta_fg>0.005
       or abs(v_delta_cogs+v_delta_fg+v_delta_other)>0.005
       or v_target_hpp is distinct from v_book_hpp then
      raise exception 'Sale cumulative HPP target does not conserve PO value %. dc %, df %, do %, target/book hpp %/%',
        r.po_id,v_delta_cogs,v_delta_fg,v_delta_other,v_target_hpp,v_book_hpp;
    end if;
    if abs(v_delta_cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_cogs>0 then
        jsonb_build_object('mapping_key','COGS','debit',v_delta_cogs,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','COGS','debit',0,'credit',abs(v_delta_cogs),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
    if abs(v_delta_fg)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_fg>0 then
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_delta_fg,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',abs(v_delta_fg),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
    if abs(v_delta_other)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_other>0 then
        jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_delta_other,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',abs(v_delta_other),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
  end loop;
  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal('SALE',h.id,(h.sale_date AT TIME ZONE 'Asia/Jakarta')::date,
      'Sales to customer/toko · cumulative exact HPP target',v_lines);
  end if;

  for r in
    select distinct fl.product_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  for r in
    select distinct fl.po_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is not null
    order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    perform erp.assert_po_hpp_target_book_v2620e(r.po_id);
  end loop;
end
$function$;

CREATE OR REPLACE FUNCTION erp.post_sales_payment(p_payment_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
 SET "TimeZone" TO 'UTC'
AS $function$
declare
  p erp.sales_payments%rowtype;
  h erp.sales_headers%rowtype;
  prior_payment erp.sales_payments%rowtype;
  prior_fact erp.sales_payment_posting_facts%rowtype;
  prior_reversal erp.sales_payment_reversal_facts%rowtype;
  j erp.journal_entries%rowtype;
  v_cash uuid;
  v_paid numeric(20,2);
  v_total numeric(20,2);
  v_amount numeric(20,2);
  v_journal uuid;
  v_snapshot jsonb;
  v_digest text;
begin
  perform erp.require_internal();
  select * into p from erp.sales_payments where id=p_payment_id for update;
  if p.id is null or p.status<>'DRAFT' then raise exception 'Sales payment must be DRAFT'; end if;
  v_amount:=round(p.amount,2)::numeric(20,2);
  if p.amount is distinct from v_amount or v_amount<=0 then
    raise exception 'Customer payment must be a positive exact two-decimal amount';
  end if;
  if erp._cp3_business_date(p.payment_date)>erp._cp3_business_date(statement_timestamp()) then
    raise exception 'Customer payment business date cannot be in the future';
  end if;
  select * into h from erp.sales_headers where id=p.sale_id for update;
  if h.status not in('POSTED','PARTIAL_PAID') then
    raise exception 'Sale must be posted and still unpaid before payment';
  end if;
  if p.replaces_payment_id is not null then
    if p.replaces_payment_id=p.id then raise exception 'Payment cannot replace itself'; end if;
    perform pg_advisory_xact_lock(hashtextextended('SALES_PAYMENT_REPLACEMENT|'||p.replaces_payment_id::text,0));
    select * into prior_payment from erp.sales_payments
    where id=p.replaces_payment_id for update;
    select * into prior_fact from erp.sales_payment_posting_facts
    where payment_id=p.replaces_payment_id;
    select * into prior_reversal from erp.sales_payment_reversal_facts
    where payment_id=p.replaces_payment_id;
    if prior_payment.id is null or prior_payment.status<>'REVERSED'
       or prior_fact.payment_id is null or prior_reversal.payment_id is null then
      raise exception 'Replacement requires one fully reversed posted payment';
    end if;
    if prior_fact.customer_id is distinct from h.customer_id
       or prior_fact.sale_id=p.sale_id
       or prior_fact.amount is distinct from v_amount
       or prior_fact.cash_account_id is distinct from p.cash_account_id
       or prior_fact.payment_date is distinct from p.payment_date then
      raise exception 'Allocation replacement must preserve customer, amount, cash account and original payment clock while changing invoice';
    end if;
    if exists(select 1 from erp.sales_payment_posting_facts f
      where f.replaces_payment_id=p.replaces_payment_id) then
      raise exception 'Reversed payment already owns a linked replacement';
    end if;
  end if;
  select round(erp.sale_net_total(h.id),2)::numeric(20,2) into v_total;
  select round(coalesce(sum(round(sp.amount,2)),0),2)::numeric(20,2) into v_paid
  from erp.sales_payments sp where sp.sale_id=h.id and sp.status='POSTED';
  if v_paid>=v_total then
    raise exception 'Sale has no remaining receivable after returns/credits. Net sale %, already paid %',v_total,v_paid;
  end if;
  if v_paid+v_amount>v_total then
    raise exception 'Customer payment exceeds exact remaining receivable. Net sale %, already paid %, requested %',v_total,v_paid,v_amount;
  end if;
  select coa_account_id into v_cash from erp.cash_accounts where id=p.cash_account_id and is_active=true;
  if v_cash is null then raise exception 'Active cash/bank account is required'; end if;
  v_journal:=erp.post_journal('SALES_PAYMENT',p_payment_id,
    case when p.replaces_payment_id is null then erp._cp3_business_date(p.payment_date)
      else prior_reversal.reversal_economic_date end,'Customer payment',jsonb_build_array(
    jsonb_build_object('account_id',v_cash,'debit',v_amount,'credit',0,'customer_id',h.customer_id),
    jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',v_amount,'customer_id',h.customer_id)));
  select * into strict j from erp.journal_entries where id=v_journal;
  if p.replaces_payment_id is not null and(
    j.economic_date is distinct from prior_reversal.reversal_economic_date
    or j.transaction_date is distinct from prior_reversal.reversal_transaction_date
    or j.posting_at<prior_reversal.reversal_posting_at) then
    raise exception 'PAYMENT_REPLACEMENT_DATE_CONSERVATION_REQUIRED';
  end if;
  v_snapshot:=to_jsonb(p)-'status';
  v_digest:=encode(extensions.digest(convert_to(jsonb_build_array(
    p.id,p.sale_id,h.customer_id,p.payment_number,p.payment_date,v_amount,
    p.cash_account_id,j.id,j.economic_date,j.transaction_date,j.posting_at,
    p.replaces_payment_id,prior_reversal.reversal_journal_entry_id,v_snapshot
  )::text,'UTF8'),'sha256'),'hex');
  insert into erp.sales_payment_posting_facts(
    payment_id,sale_id,customer_id,payment_number,payment_date,amount,cash_account_id,
    original_journal_entry_id,journal_economic_date,journal_transaction_date,
    journal_posting_at,replaces_payment_id,predecessor_reversal_journal_id,
    payment_snapshot,lineage_sha256,recorded_by
  ) values(
    p.id,p.sale_id,h.customer_id,p.payment_number,p.payment_date,v_amount,p.cash_account_id,
    j.id,j.economic_date,j.transaction_date,j.posting_at,p.replaces_payment_id,
    prior_reversal.reversal_journal_entry_id,v_snapshot,v_digest,erp.current_app_user_id()
  );
  update erp.sales_payments set status='POSTED' where id=p_payment_id;
  v_paid:=v_paid+v_amount;
  update erp.sales_headers
  set status=case when v_paid=v_total then 'PAID' else 'PARTIAL_PAID' end
  where id=h.id;
end
$function$;

CREATE OR REPLACE FUNCTION erp.post_sales_return(p_return_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.sales_returns%rowtype;
  s erp.sales_headers%rowtype;
  r record;
  v_refund numeric(24,6):=0;
  v_sold_qty integer;
  v_prior_returned integer;
  v_current_return integer;
  v_product_sale_value numeric(24,6);
  v_prior_product_refund numeric(24,6);
  v_current_product_refund numeric(24,6);
  v_original_hpp numeric(18,6);
  v_unit_hpp numeric(18,6);
  v_net_total numeric(20,2);
  v_paid numeric(20,2);
  v_delta_cogs numeric(24,6);
  v_delta_fg numeric(24,6);
  v_delta_other numeric(24,6);
  v_target_hpp numeric(24,6);
  v_target_other numeric(24,6);
  v_book_hpp numeric(24,6);
  v_book_other numeric(24,6);
  v_lines jsonb:='[]'::jsonb;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into h from erp.sales_returns where id=p_return_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Sales return must be DRAFT'; end if;
  if h.sale_id is null then raise exception 'Native sales return must reference the original sale'; end if;
  select * into s from erp.sales_headers where id=h.sale_id for update;
  if s.id is null or s.status not in('POSTED','PARTIAL_PAID','PAID') then raise exception 'Original sale must be active/posted'; end if;
  if s.customer_id is distinct from h.customer_id then raise exception 'Sales return customer does not match original sale customer'; end if;
  if not exists(select 1 from erp.sales_return_items where return_id=h.id) then raise exception 'Sales return has no lines'; end if;

  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  for r in
    select * from erp.sales_return_items where return_id=h.id
    order by product_id,location_id,quality_grade,lot_id,id
  loop
    if r.lot_id is null then raise exception 'Sales return line requires original FG lot'; end if;
    if not exists(select 1 from erp.fg_lots fl where fl.id=r.lot_id and fl.product_id=r.product_id) then raise exception 'Sales return lot does not belong to selected product'; end if;

    insert into erp.fg_inventory_balances(product_id,location_id,quality_grade,cached_qty_pcs)
    values(r.product_id,r.location_id,r.quality_grade,0)
    on conflict(product_id,location_id,quality_grade) do nothing;
    perform 1 from erp.fg_inventory_balances
    where product_id=r.product_id and location_id=r.location_id and quality_grade=r.quality_grade
    for update;
    perform 1 from erp.fg_lots where id=r.lot_id for update;

    select coalesce(sum(a.qty_pcs),0)::integer,
           case when coalesce(sum(a.qty_pcs),0)>0 then sum(a.qty_pcs*a.unit_hpp_snapshot)/sum(a.qty_pcs) else null end
    into v_sold_qty,v_original_hpp
    from erp.sale_stock_allocations a
    join erp.sales_items si on si.id=a.sale_item_id
    where si.sale_id=h.sale_id and si.product_id=r.product_id and a.lot_id=r.lot_id and a.location_id=r.location_id;
    if v_sold_qty<=0 or v_original_hpp is null then raise exception 'Returned product/lot/location was not allocated on the original sale'; end if;

    v_unit_hpp:=coalesce(erp.lock_current_hpp_per_pcs(r.lot_id),v_original_hpp);
    select coalesce(sum(sri.qty_pcs),0)::integer into v_prior_returned
    from erp.sales_return_items sri join erp.sales_returns sr on sr.id=sri.return_id
    where sr.sale_id=h.sale_id and sr.id<>h.id and sr.status='POSTED'
      and sri.product_id=r.product_id and sri.lot_id=r.lot_id and sri.location_id=r.location_id;
    select coalesce(sum(sri.qty_pcs),0)::integer into v_current_return
    from erp.sales_return_items sri
    where sri.return_id=h.id and sri.product_id=r.product_id and sri.lot_id=r.lot_id and sri.location_id=r.location_id;
    if v_prior_returned+v_current_return>v_sold_qty then
      raise exception 'Sales return exceeds quantity originally sold for this lot/location. Sold %, prior returned %, current return %',v_sold_qty,v_prior_returned,v_current_return;
    end if;

    select coalesce(sum(si.line_total),0) into v_product_sale_value
    from erp.sales_items si where si.sale_id=h.sale_id and si.product_id=r.product_id;
    select coalesce(sum(sri.refund_amount),0) into v_prior_product_refund
    from erp.sales_return_items sri join erp.sales_returns sr on sr.id=sri.return_id
    where sr.sale_id=h.sale_id and sr.id<>h.id and sr.status='POSTED' and sri.product_id=r.product_id;
    select coalesce(sum(sri.refund_amount),0) into v_current_product_refund
    from erp.sales_return_items sri where sri.return_id=h.id and sri.product_id=r.product_id;
    if v_prior_product_refund+v_current_product_refund>v_product_sale_value then
      raise exception 'Refund exceeds original net sale value for product. Sold value %, prior refund %, current refund %',v_product_sale_value,v_prior_product_refund,v_current_product_refund;
    end if;

    update erp.sales_return_items set unit_hpp_snapshot=v_unit_hpp where id=r.id;
    perform erp.post_fg_movement(r.product_id,r.lot_id,r.location_id,r.quality_grade,
      'SALE_RETURN',r.qty_pcs,v_unit_hpp,h.customer_id,'SALES_RETURN_ITEM',r.id,
      h.physical_at,'Customer sales return',false);
    v_refund:=v_refund+r.refund_amount;
  end loop;

  select greatest(erp.sale_net_total(h.sale_id)-v_refund,0)::numeric(20,2) into v_net_total;
  select coalesce(sum(sp.amount),0)::numeric(20,2) into v_paid
  from erp.sales_payments sp where sp.sale_id=h.sale_id and sp.status='POSTED';
  if v_paid>v_net_total then
    raise exception 'Retur ini membuat pembayaran customer melebihi nilai penjualan tersisa. Nilai setelah retur %, sudah dibayar %. Reverse/koreksi pembayaran customer dulu agar kelebihan bayar tidak hilang dari pembukuan.',v_net_total,v_paid;
  end if;

  update erp.sales_returns set status='POSTED' where id=h.id;
  if abs(v_refund)>0.005 then
    v_lines:=v_lines||jsonb_build_array(
      jsonb_build_object('mapping_key','SALES_REVENUE','debit',round(v_refund,2),'credit',0,'customer_id',h.customer_id),
      jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',round(v_refund,2),'customer_id',h.customer_id));
  end if;

  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    select round(t.fg_value-b.fg_value,2),
      round(t.cogs_value-b.cogs_value,2),
      round(t.other_out_value-b.other_out_value,2)
    into v_delta_fg,v_delta_cogs,v_delta_other
    from erp.compute_non_po_product_hpp_targets_v2620f(r.product_id) t
    cross join lateral erp.compute_non_po_product_hpp_book_v2620f(r.product_id) b;
    if abs(v_delta_fg+v_delta_cogs+v_delta_other)>0.005 then
      raise exception 'Return non-PO HPP delta does not conserve source value for product %: fg %, cogs %, other %',
        r.product_id,v_delta_fg,v_delta_cogs,v_delta_other;
    end if;
    if abs(v_delta_fg)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_fg>0
        then jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_delta_fg,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,
          'credit',abs(v_delta_fg),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
    if abs(v_delta_cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_cogs>0
        then jsonb_build_object('mapping_key','COGS','debit',v_delta_cogs,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','COGS','debit',0,
          'credit',abs(v_delta_cogs),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
    if abs(v_delta_other)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_other>0
        then jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_delta_other,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,
          'credit',abs(v_delta_other),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
  end loop;

  for r in
    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    select
      round(coalesce(t.cogs_value,0),2)-st.cogs_value,
      round(coalesce(t.fg_value,0),2)-st.fg_value,
      (round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)
        -round(coalesce(t.cogs_value,0),2))-st.other_out_value,
      round(coalesce(t.hpp_total_cost,0),2),
      round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)-round(coalesce(t.cogs_value,0),2),
      st.hpp_total_cost,st.other_out_value
    into v_delta_cogs,v_delta_fg,v_delta_other,
      v_target_hpp,v_target_other,v_book_hpp,v_book_other
    from erp.po_hpp_gl_state st
    cross join lateral erp.compute_po_hpp_gl_targets_v2620d(r.po_id) t
    where st.po_id=r.po_id for update of st;
    if v_delta_cogs>0.005 or v_delta_fg<-0.005
       or abs(v_delta_cogs+v_delta_fg+v_delta_other)>0.005
       or v_target_hpp is distinct from v_book_hpp then
      raise exception 'Sales-return cumulative HPP target does not conserve PO value %. dc %, df %, do %, target/book hpp %/%',
        r.po_id,v_delta_cogs,v_delta_fg,v_delta_other,v_target_hpp,v_book_hpp;
    end if;
    if abs(v_delta_cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_cogs>0 then
        jsonb_build_object('mapping_key','COGS','debit',v_delta_cogs,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','COGS','debit',0,'credit',abs(v_delta_cogs),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
    if abs(v_delta_fg)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_fg>0 then
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_delta_fg,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',abs(v_delta_fg),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
    if abs(v_delta_other)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_other>0 then
        jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_delta_other,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',abs(v_delta_other),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
  end loop;
  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal('SALES_RETURN',h.id,(h.physical_at AT TIME ZONE 'Asia/Jakarta')::date,
      'Sales return from customer · cumulative exact HPP target',v_lines);
  end if;

  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  update erp.sales_headers
  set status=case when v_paid=v_net_total then 'PAID' when v_paid>0 and v_paid<v_net_total then 'PARTIAL_PAID' else 'POSTED' end
  where id=h.sale_id;
  for r in
    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    perform erp.assert_po_hpp_target_book_v2620e(r.po_id);
  end loop;
end
$function$;

CREATE OR REPLACE FUNCTION erp.post_vendor_invoice(p_invoice_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.vendor_invoices%rowtype;
  r record;
  v_total numeric(20,2):=0;
  v_old numeric(20,2);
  v_po uuid;
  v_group_id uuid;
  v_lines jsonb:='[]'::jsonb;
begin
  perform erp.require_internal();
  select * into h from erp.vendor_invoices where id=p_invoice_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Vendor invoice must be DRAFT'; end if;
  if not exists (select 1 from erp.vendor_invoice_items where invoice_id=h.id) then raise exception 'Vendor invoice has no lines'; end if;

  for v_group_id in
    select distinct ldl.cutting_group_id
    from erp.vendor_invoice_items vii
    join erp.laundry_receipt_lines lrl on lrl.id=vii.receipt_line_id
    join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
    where vii.invoice_id=h.id
    order by ldl.cutting_group_id
  loop
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
  end loop;
  perform 1
  from erp.laundry_receipts lr
  where lr.id in(
    select distinct lrl.receipt_id
    from erp.vendor_invoice_items vii
    join erp.laundry_receipt_lines lrl on lrl.id=vii.receipt_line_id
    where vii.invoice_id=h.id
  )
  order by lr.id
  for update;
  perform 1
  from erp.laundry_receipt_lines lrl
  where lrl.id in(
    select vii.receipt_line_id
    from erp.vendor_invoice_items vii where vii.invoice_id=h.id
  )
  order by lrl.id
  for update;

  for r in
    select vii.*,lrl.actual_rate_snapshot as previous_rate,lrl.actual_cost_status as previous_status,lrl.actual_cost as previous_cost,
           ld.po_id,ld.vendor_id as source_vendor_id
    from erp.vendor_invoice_items vii
    join erp.laundry_receipt_lines lrl on lrl.id=vii.receipt_line_id
    join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
    join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
    where vii.invoice_id=p_invoice_id
    order by vii.receipt_line_id,vii.id
  loop
    perform 1 from erp.laundry_receipt_lines where id=r.receipt_line_id for update;
    if r.source_vendor_id is distinct from h.vendor_id then raise exception 'Vendor invoice vendor does not match laundry delivery vendor'; end if;
    if not exists (
      select 1 from erp.laundry_receipts lr
      join erp.laundry_receipt_lines x on x.receipt_id=lr.id
      where x.id=r.receipt_line_id and lr.status='POSTED'
    ) then raise exception 'Vendor invoice can only bill POSTED laundry receipt lines'; end if;
    if exists (
      select 1 from erp.vendor_invoice_items vii2
      join erp.vendor_invoices vi2 on vi2.id=vii2.invoice_id
      where vii2.receipt_line_id=r.receipt_line_id and vi2.id<>h.id
        and vi2.status in ('POSTED','PARTIAL_PAID','PAID')
    ) then raise exception 'Laundry receipt line is already billed by another active vendor invoice'; end if;

    update erp.vendor_invoice_items
    set prior_actual_rate_snapshot=r.previous_rate,
        prior_actual_cost_status=r.previous_status,
        prior_actual_cost=r.previous_cost
    where id=r.id;

    v_old:=coalesce(r.previous_cost,0);
    v_total:=v_total+r.actual_amount;

    update erp.laundry_receipt_lines
    set actual_rate_snapshot=coalesce(r.actual_rate,actual_rate_snapshot),
        actual_cost=r.actual_amount,
        actual_cost_status='FINAL'
    where id=r.receipt_line_id;

    insert into erp.cost_adjustments(adjustment_number,po_id,component_type,source_type,source_id,economic_date,old_amount,new_amount,reason,created_by)
    values ('CADJ-'||substr(gen_random_uuid()::text,1,12),r.po_id,'LAUNDRY','VENDOR_INVOICE_ITEM',r.id,h.invoice_date,v_old,r.actual_amount,'Final laundry vendor invoice',erp.current_app_user_id());

    v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','WIP','debit',r.actual_amount,'credit',0,'vendor_id',h.vendor_id,'po_id',r.po_id));
  end loop;

  if round(v_total,2)<>round(h.total_amount,2) then raise exception 'Vendor invoice item total % does not match header total %',v_total,h.total_amount; end if;
  if h.total_amount>0 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','AP_VENDOR','debit',0,'credit',h.total_amount,'vendor_id',h.vendor_id));
    perform erp.post_journal('VENDOR_INVOICE',h.id,h.invoice_date,'Laundry vendor invoice '||h.invoice_number,v_lines);
  end if;

  update erp.vendor_invoices set status='POSTED',updated_at=statement_timestamp() where id=h.id;

  for v_po in
    select distinct ld.po_id
    from erp.vendor_invoice_items vii
    join erp.laundry_receipt_lines lrl on lrl.id=vii.receipt_line_id
    join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
    join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
    where vii.invoice_id=p_invoice_id
  loop
    perform erp.sync_laundry_accrual(v_po,h.invoice_date);
    if exists (select 1 from erp.fg_lots where po_id=v_po) then
      perform erp.rebuild_po_hpp(v_po,'Final laundry vendor invoice posted');
      perform erp.propagate_conversion_hpp_for_po(v_po);
      perform erp.sync_po_hpp_to_gl(v_po,h.invoice_date);
    end if;
  end loop;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_work_completion(p_completion_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare h erp.work_completion_events%rowtype;v_total numeric(24,6);v_group_count integer;v_only_group uuid;
begin
  perform erp.require_internal();select * into h from erp.work_completion_events where id=p_completion_id for update;if h.id is null or h.status<>'DRAFT' then raise exception 'Work completion must be DRAFT';end if;if not exists(select 1 from erp.production_orders po where po.id=h.po_id and po.contractor_id=h.contractor_id) then raise exception 'Work completion contractor does not match PO contractor';end if;
  if h.cutting_group_id is not null then if not exists(select 1 from erp.cutting_groups cg where cg.id=h.cutting_group_id and cg.po_id=h.po_id) then raise exception 'Work completion cutting group does not belong to PO';end if;
  else select count(*),(array_agg(id order by id))[1] into v_group_count,v_only_group from erp.cutting_groups where po_id=h.po_id;if v_group_count=1 then update erp.work_completion_events set cutting_group_id=v_only_group where id=h.id;h.cutting_group_id:=v_only_group;elsif v_group_count>1 then raise exception 'PO has multiple cutting groups; select the grouping for this work completion so HPP stays on the correct lot';end if;end if;
  if not exists(select 1 from erp.po_work_component_snapshots where po_id=h.po_id) then raise exception 'Work BOM/rate snapshot is not committed for this PO; call ensure_po_work_component_snapshots using the work physical date before entering/posting lines';end if;
  if not exists(select 1 from erp.work_completion_lines where completion_id=h.id) then raise exception 'Work completion has no lines';end if;
  select coalesce(sum(amount_payable),0) into v_total from erp.work_completion_lines where completion_id=p_completion_id;update erp.work_completion_events set status='POSTED' where id=p_completion_id;
  if v_total>0 then perform erp.post_journal('WORK_COMPLETION',p_completion_id,(h.physical_at AT TIME ZONE 'Asia/Jakarta')::date,'Mandor work completion accrual',jsonb_build_array(jsonb_build_object('mapping_key','WIP','debit',round(v_total,2),'credit',0,'contractor_id',h.contractor_id,'po_id',h.po_id),jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',round(v_total,2),'contractor_id',h.contractor_id,'po_id',h.po_id)));end if;
end;$function$;

CREATE OR REPLACE FUNCTION erp.prepare_migration_opening_balance(p_batch_id uuid, p_opening_number text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare b erp.migration_batches%rowtype;r record;j jsonb;v_header uuid;v_material uuid;v_roll uuid;v_product uuid;v_model uuid;v_contractor uuid;v_customer uuid;v_location uuid;v_supplier uuid;v_vendor uuid;v_cash uuid;v_type text;v_number text;v_hpp_method text;v_hpp_pct numeric;
begin
  perform erp.require_owner_admin();select * into b from erp.migration_batches where id=p_batch_id for update;if b.id is null then raise exception 'Migration batch not found';end if;if b.status not in('READY','POSTING') then raise exception 'Migration batch must be READY/POSTING';end if;if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and validation_status<>'VALID') then raise exception 'Migration batch contains unvalidated/error rows';end if;
  if exists(select 1 from erp.opening_balance_headers where migration_batch_id=p_batch_id) then select id into v_header from erp.opening_balance_headers where migration_batch_id=p_batch_id order by created_at limit 1;return v_header;end if;
  v_number:=coalesce(nullif(trim(p_opening_number),''),'MIG-'||b.batch_code);insert into erp.opening_balance_headers(opening_number,opening_date,status,notes,created_by,migration_batch_id) values(v_number,(b.cutover_at AT TIME ZONE 'Asia/Jakarta')::date,'DRAFT','Prepared from migration batch '||b.batch_code,erp.current_app_user_id(),b.id) returning id into v_header;
  for r in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='MATERIAL_ROLL' and validation_status='VALID' order by source_row_no loop
    j:=r.normalized_payload;select m.id,mr.id into v_material,v_roll from erp.materials m join erp.material_rolls mr on mr.material_id=m.id where m.material_sku=j->>'material_sku' and mr.roll_number=j->>'roll_number';select id into v_location from erp.locations where location_code=j->>'location_code' and location_type='RAW_MATERIAL_WAREHOUSE' and is_active=true;if v_material is null or v_roll is null or v_location is null then raise exception 'MATERIAL_ROLL row % was not applied/resolved safely',r.source_row_no;end if;
    insert into erp.opening_balance_items(opening_id,balance_type,material_id,roll_id,location_id,qty,unit_cost_snapshot,notes) values(v_header,'MATERIAL',v_material,v_roll,v_location,(j->>'opening_qty')::numeric,(j->>'unit_cost')::numeric,coalesce(j->>'notes','Legacy roll opening row '||r.source_row_no));
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
    values(v_header,v_type,v_material,v_product,v_model,v_contractor,v_customer,v_location,v_supplier,v_vendor,v_cash,nullif(j->>'stage',''),nullif(j->>'qty','')::numeric,nullif(j->>'amount','')::numeric,nullif(j->>'unit_cost','')::numeric,nullif(j->>'quality_grade',''),coalesce(j->>'notes','Legacy migration row '||r.source_row_no),case when v_type='FINISHED_GOODS' then v_hpp_method else 'MANUAL' end,case when v_type='FINISHED_GOODS' and v_hpp_method='PRICE_PERCENT' then v_hpp_pct else null end);
    update erp.migration_staging_rows set posted_entity_type='OPENING_BALANCE_HEADER',posted_entity_id=v_header,posted_at=statement_timestamp(),updated_at=statement_timestamp() where id=r.id;
  end loop;return v_header;
end$function$;

CREATE OR REPLACE FUNCTION erp.process_cost_recalc_queue(p_limit integer DEFAULT 20)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  r record;
  v_count integer:=0;
  v_attempt integer;
  v_po_status text;
begin
  perform erp.require_internal();
  for r in
    select * from erp.cost_recalc_queue
    where status='PENDING' or (status='FAILED' and attempt_count<3 and coalesce(next_attempt_at,statement_timestamp())<=statement_timestamp())
    order by queued_at,id limit greatest(p_limit,1) for update skip locked
  loop
    v_attempt:=r.attempt_count+1;
    begin
      update erp.cost_recalc_queue set status='RUNNING',started_at=statement_timestamp(),last_attempt_at=statement_timestamp(),attempt_count=v_attempt where id=r.id;
      if r.entity_type='PO' then
        perform erp.rebuild_po_hpp(r.entity_id,r.reason);
        perform erp.propagate_conversion_hpp_for_po(r.entity_id);
        perform erp.sync_po_hpp_to_gl(r.entity_id,erp._cp3_business_date(statement_timestamp()));
        select status into v_po_status from erp.production_orders where id=r.entity_id;
        if v_po_status='FINISHED' then perform erp.sync_finished_po_wip_residual(r.entity_id,erp._cp3_business_date(statement_timestamp()),'Post-close HPP/material recost residual adjustment'); end if;
      else
        raise exception 'Unsupported cost recalc entity_type %',r.entity_type;
      end if;
      update erp.cost_recalc_queue set status='DONE',completed_at=statement_timestamp(),error_message=null,next_attempt_at=null,last_attempt_at=statement_timestamp(),attempt_count=v_attempt where id=r.id;
      v_count:=v_count+1;
    exception when others then
      update erp.cost_recalc_queue set status='FAILED',completed_at=statement_timestamp(),error_message=sqlerrm,last_attempt_at=statement_timestamp(),attempt_count=v_attempt,
        next_attempt_at=case when v_attempt<3 then statement_timestamp()+(interval '5 minutes'*v_attempt) else null end where id=r.id;
    end;
  end loop;
  return v_count;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.refresh_accessory_hpp_after_material_recost(p_material_id uuid, p_reason text DEFAULT 'Accessory historical moving-average recost'::text)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_category uuid;
  r record;
  v_new numeric(18,6);
  v_changed integer:=0;
  v_po uuid;
begin
  perform erp.require_internal();
  select accessory_category_id into v_category from erp.materials where id=p_material_id and material_type='ACCESSORY';
  if v_category is null then return 0; end if;
  perform pg_advisory_xact_lock(hashtextextended('ACCESSORY_HPP_CATEGORY|'||v_category::text,0));

  create temporary table if not exists pg_temp.erp_accessory_hpp_changed_pos(po_id uuid primary key) on commit drop;
  truncate pg_temp.erp_accessory_hpp_changed_pos;

  for r in
    select s.id,s.po_id,s.costing_basis_at,s.category_avg_cost_base_snapshot,s.hpp_unit_cost_base_snapshot
    from erp.fg_accessory_cost_snapshots s
    where s.category_id=v_category and s.hpp_method='CATEGORY_MOVING_AVG'
    order by s.costing_basis_at,s.id
    for update
  loop
    v_new:=erp.accessory_category_weighted_avg_cost_at(v_category,r.costing_basis_at);
    if v_new is null then
      raise exception 'Historical accessory recost would remove the valuation basis for FG accessory snapshot %. Correct/reverse the upstream inventory event first.',r.id;
    end if;
    if abs(v_new-r.hpp_unit_cost_base_snapshot)>0.000001 then
      insert into erp.fg_accessory_cost_revisions(snapshot_id,material_id,old_category_avg_cost,new_category_avg_cost,old_hpp_unit_cost,new_hpp_unit_cost,reason,changed_by)
      values(r.id,p_material_id,r.category_avg_cost_base_snapshot,v_new,r.hpp_unit_cost_base_snapshot,v_new,coalesce(nullif(trim(p_reason),''),'Accessory historical moving-average recost'),erp.current_app_user_id());
      update erp.fg_accessory_cost_snapshots
      set category_avg_cost_base_snapshot=v_new,hpp_unit_cost_base_snapshot=v_new
      where id=r.id;
      insert into pg_temp.erp_accessory_hpp_changed_pos(po_id) values(r.po_id) on conflict do nothing;
      v_changed:=v_changed+1;
    end if;
  end loop;

  for v_po in select po_id from pg_temp.erp_accessory_hpp_changed_pos order by po_id loop
    perform erp.rebuild_po_hpp(v_po,'Accessory moving-average recost: '||coalesce(nullif(trim(p_reason),''),'historical material recost'));
    perform erp.propagate_conversion_hpp_for_po(v_po);
    perform erp.sync_po_hpp_to_gl(v_po,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  end loop;
  return v_changed;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reopen_accounting_through(p_new_closed_through date, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare v_old date;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan membuka kembali periode wajib diisi'; end if;
  select closed_through into v_old from erp.accounting_period_control where singleton_id=1 for update;
  if v_old is null then return; end if;
  if p_new_closed_through is not null and p_new_closed_through>=v_old then
    raise exception 'Tanggal reopen harus lebih awal dari periode tertutup saat ini % atau NULL untuk membuka seluruh periode',v_old;
  end if;
  if p_new_closed_through is not null and p_new_closed_through>=((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date then
    raise exception 'Tanggal tutup buku baru harus sebelum hari ini';
  end if;
  update erp.accounting_period_control
  set closed_through=p_new_closed_through,updated_at=statement_timestamp(),updated_by=erp.current_app_user_id(),change_reason=p_reason
  where singleton_id=1;
  insert into erp.audit_logs(entity_type,entity_id,action,old_data,new_data,changed_by,change_reason)
  values('accounting_period_control',null,'UPDATE',jsonb_build_object('closed_through',v_old),jsonb_build_object('closed_through',p_new_closed_through),erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reopen_production_order(p_po_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_status text;
  v_stage text;
  r record;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then
    raise exception 'Alasan reopen PO wajib diisi';
  end if;

  select status into v_status from erp.production_orders where id=p_po_id for update;
  if v_status is null then raise exception 'PO tidak ditemukan'; end if;
  if v_status<>'FINISHED' then
    raise exception 'Hanya PO FINISHED yang dapat direopen. Status saat ini %',v_status;
  end if;

  for r in
    select je.id
    from erp.po_wip_close_events e
    join erp.journal_entries je on je.id=e.journal_entry_id
    where e.po_id=p_po_id and je.source_type='PO_WIP_RESIDUAL_CLOSE' and je.status='POSTED'
    order by je.posting_at desc,je.id desc
  loop
    perform erp.reverse_journal(r.id,'Reopen PO: '||p_reason);
  end loop;

  if exists(select 1 from erp.qc_inspections q where q.po_id=p_po_id and q.status='POSTED')
     or exists(select 1 from erp.laundry_receipts lr join erp.laundry_deliveries ld on ld.id=lr.delivery_id where ld.po_id=p_po_id and lr.status='POSTED' and ld.status<>'REVERSED')
     or exists(select 1 from erp.fg_lots fl where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION') then
    v_stage:='QC';
  elsif exists(select 1 from erp.laundry_deliveries ld where ld.po_id=p_po_id and ld.status not in('DRAFT','REVERSED')) then
    v_stage:='LAUNDRY';
  elsif exists(select 1 from erp.cutting_groups cg where cg.po_id=p_po_id and cg.picked_up_at is not null) then
    v_stage:='SEWING';
  elsif exists(select 1 from erp.cutting_groups cg where cg.po_id=p_po_id) then
    v_stage:='CUTTING';
  else
    v_stage:='DRAFT';
  end if;

  update erp.production_orders
  set status=case when v_stage='DRAFT' then 'DRAFT' else v_stage end,
      current_stage=case when v_stage='DRAFT' then 'CUTTING' else v_stage end,
      updated_at=statement_timestamp()
  where id=p_po_id;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('production_orders',p_po_id,'UPDATE',jsonb_build_object('correction_type','PO_REOPEN','previous_status','FINISHED','restored_stage',v_stage),erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.replace_material_purchase(p_original_purchase_id uuid, p_replacement_purchase_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  o erp.material_purchase_headers%rowtype;
  n erp.material_purchase_headers%rowtype;
  v_journal uuid;
  v_total numeric(24,6);
  v_material_id uuid;
begin
  perform erp.require_owner_admin();
  if p_original_purchase_id=p_replacement_purchase_id then raise exception 'Pembelian pengganti harus dokumen berbeda'; end if;
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan koreksi/replacement pembelian wajib diisi'; end if;

  select * into o from erp.material_purchase_headers where id=p_original_purchase_id for update;
  select * into n from erp.material_purchase_headers where id=p_replacement_purchase_id for update;
  if o.id is null or o.status<>'POSTED' then raise exception 'Pembelian lama harus POSTED'; end if;
  if n.id is null or n.status<>'DRAFT' then raise exception 'Pembelian pengganti harus sudah disiapkan sebagai DRAFT'; end if;
  if o.supplier_id is distinct from n.supplier_id then raise exception 'Pembelian pengganti harus memakai supplier yang sama; perubahan supplier perlu dokumen reversal/repost terpisah'; end if;
  if o.physical_at is distinct from n.physical_at then raise exception 'Pembelian pengganti harus memakai tanggal/jam fisik yang sama dengan source lama agar chronology stok tidak berubah diam-diam'; end if;
  if exists(select 1 from erp.supplier_payments where purchase_id=o.id and status='POSTED') then raise exception 'Pembelian lama sudah dibayar. Reverse pembayaran supplier terlebih dahulu sebelum replacement.'; end if;
  if exists(select 1 from erp.material_supplier_return_items ri join erp.material_supplier_returns rh on rh.id=ri.return_id join erp.material_purchase_items pi on pi.id=ri.purchase_item_id where pi.purchase_id=o.id and rh.status='POSTED') then raise exception 'Pembelian lama punya retur supplier aktif. Reverse retur terlebih dahulu.'; end if;
  if exists(select 1 from erp.material_purchase_cost_corrections where purchase_id=o.id and status='POSTED') then raise exception 'Pembelian lama punya koreksi harga aktif. Reverse koreksi harga terlebih dahulu.'; end if;

  -- Canonical material locks cover both the old and replacement material sets.
  -- This keeps cross-material replacements deterministic and ensures the final
  -- recost sees the complete old-source reversal + replacement posting.
  for v_material_id in
    select material_id
    from (
      select material_id from erp.material_purchase_items where purchase_id=o.id
      union
      select material_id from erp.material_purchase_items where purchase_id=n.id
    ) s
    order by material_id
  loop
    perform 1 from erp.materials where id=v_material_id for update;
  end loop;

  select coalesce(sum(line_total),0) into v_total from erp.material_purchase_items where purchase_id=o.id;
  select id into v_journal from erp.journal_entries where source_type='MATERIAL_PURCHASE' and source_id=o.id and status='POSTED' order by posting_at desc,id desc limit 1;
  if v_total>0.005 and v_journal is null then raise exception 'Jurnal pembelian lama tidak ditemukan; replacement dibatalkan'; end if;

  update erp.material_purchase_headers set status='REVERSED',updated_at=statement_timestamp() where id=o.id;
  perform set_config('erp.allow_source_replacement_negative','on',true);
  perform erp._stage_reverse_material_purchase_stock_at_source_time(o.id,'Replaced by purchase '||n.purchase_number||': '||p_reason);
  perform set_config('erp.allow_source_replacement_negative','off',true);

  perform erp.post_material_purchase(n.id);

  -- post_material_purchase recalculates replacement materials. Recalculate the
  -- complete union again so materials that existed only on the old purchase are
  -- also brought back in sync with their movement ledger.
  for v_material_id in
    select material_id
    from (
      select material_id from erp.material_purchase_items where purchase_id=o.id
      union
      select material_id from erp.material_purchase_items where purchase_id=n.id
    ) s
    order by material_id
  loop
    perform erp.recalculate_material_cost(v_material_id);
  end loop;

  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
  update erp.material_purchase_headers set payment_status='UNPAID',updated_at=statement_timestamp() where id=o.id;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('material_purchase_headers',o.id,'REVERSE',jsonb_build_object('replacement_purchase_id',n.id,'replacement_purchase_number',n.purchase_number),erp.current_app_user_id(),p_reason);
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('material_purchase_headers',n.id,'UPDATE',jsonb_build_object('replaces_purchase_id',o.id,'replaces_purchase_number',o.purchase_number),erp.current_app_user_id(),'Replacement for corrected posted purchase: '||p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.resolve_laundry_claim(p_claim_id uuid, p_resolution text, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare c erp.laundry_claims%rowtype;v_ap_account uuid;v_ap_balance numeric(24,6):=0;v_effective_date date;
begin
  perform erp.require_owner_admin();
  if p_resolution not in ('SETTLED','WRITTEN_OFF') then raise exception 'Claim resolution must be SETTLED or WRITTEN_OFF'; end if;
  if nullif(trim(p_reason),'') is null then raise exception 'Claim resolution reason is required'; end if;
  select * into c from erp.laundry_claims where id=p_claim_id for update;
  if c.id is null then raise exception 'Laundry claim not found'; end if;
  if c.status in ('SETTLED','WRITTEN_OFF') then return; end if;
  if c.status='REJECTED' then raise exception 'Rejected laundry claim cannot be settled/write-off without reopening'; end if;
  if p_resolution='WRITTEN_OFF' and c.compensation_amount>0 then raise exception 'WRITTEN_OFF claim must have zero compensation; set compensation to zero or use SETTLED'; end if;
  v_effective_date:=coalesce(c.resolution_date,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  if v_effective_date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date then raise exception 'Tanggal penyelesaian claim laundry berada di masa depan'; end if;
  if p_resolution='SETTLED' and c.compensation_amount>0 then
    v_ap_account:=erp.account_id('AP_VENDOR');
    select coalesce(sum(jl.credit-jl.debit),0) into v_ap_balance from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
    where je.status in ('POSTED','REVERSED') and jl.vendor_id=c.vendor_id and jl.account_id=v_ap_account;
    if v_ap_balance<c.compensation_amount then raise exception 'Claim compensation % exceeds current laundry vendor payable %. Cash/receivable settlement needs a separate receivable workflow',c.compensation_amount,round(v_ap_balance,2); end if;
    perform erp.post_journal('LAUNDRY_CLAIM_SETTLEMENT',c.id,v_effective_date,'Laundry claim compensation offset',jsonb_build_array(
      jsonb_build_object('mapping_key','AP_VENDOR','debit',round(c.compensation_amount,2),'credit',0,'vendor_id',c.vendor_id),
      jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',0,'credit',round(c.compensation_amount,2),'vendor_id',c.vendor_id)));
  end if;
  update erp.laundry_claims set status=p_resolution,resolution_date=v_effective_date,resolved_at=statement_timestamp(),notes=concat_ws(E'\n',notes,'Resolution: '||p_reason) where id=c.id;
end$function$;

CREATE OR REPLACE FUNCTION erp.reverse_contractor_material_issue(p_issue_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.contractor_material_issues%rowtype;
  r record;
  j record;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal pengambilan material/aksesoris mandor wajib diisi'; end if;

  select * into h from erp.contractor_material_issues where id=p_issue_id for update;
  if h.id is null then raise exception 'Transaksi pengambilan material/aksesoris mandor tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya pengambilan material/aksesoris mandor yang sudah POSTED yang dapat direverse'; end if;

  if exists(
    select 1
    from erp.payroll_deductions pd
    join erp.payroll_settlements ps on ps.id=pd.payroll_id
    join erp.contractor_material_issue_items ii on ii.id=pd.contractor_issue_item_id
    where ii.issue_id=h.id and ps.status<>'REVERSED'
  ) then
    raise exception 'Pengambilan ini sudah masuk payroll/kasbon mandor. Cancel atau reverse payroll yang masih aktif terlebih dahulu agar potongan gaji dan piutang mandor tidak beda.';
  end if;

  for r in
    select msm.id
    from erp.material_stock_movements msm
    join erp.contractor_material_issue_items ii on ii.id=msm.source_id
    where ii.issue_id=h.id
      and msm.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM'
      and msm.movement_type='CONTRACTOR_ISSUE'
    order by msm.system_created_at desc,msm.id desc
  loop
    perform erp.reverse_material_movement(r.id,p_reason);
  end loop;

  for j in
    select je.id
    from erp.journal_entries je
    where je.source_id=h.id
      and je.source_type in ('CONTRACTOR_ACCESSORY_STOCK_COST','CONTRACTOR_NONACCESSORY_MATERIAL_COST','CONTRACTOR_MATERIAL_RECEIVABLE')
      and je.status='POSTED'
    order by je.posting_at desc,je.id desc
  loop
    perform erp.reverse_journal(j.id,p_reason);
  end loop;

  update erp.contractor_material_issues set status='REVERSED',updated_at=statement_timestamp() where id=h.id;
  update erp.contractor_material_issue_items set payroll_status='UNALLOCATED' where issue_id=h.id;

  if h.po_id is not null and exists(select 1 from erp.fg_lots where po_id=h.po_id) then
    perform erp.rebuild_po_hpp(h.po_id,'Mandor material issue reversed: '||p_reason);
    perform erp.propagate_conversion_hpp_for_po(h.po_id);
    perform erp.sync_po_hpp_to_gl(h.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  end if;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values ('contractor_material_issues',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_cutting_material_flow_before_sewing_v2(p_cutting_group_id uuid, p_reason text, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_group erp.cutting_groups%rowtype;
  r record;
  v_reversed_movements integer := 0;
  v_reversed_journals integer := 0;
begin
  perform erp.require_owner_admin();
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if nullif(btrim(p_reason), '') is null then raise exception 'Reversal reason is required'; end if;
  v_hash := erp._request_hash(jsonb_build_object(
    'cutting_group_id', p_cutting_group_id,
    'reason', btrim(p_reason),
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(
    'reverse_cutting_material_flow_before_sewing_v2', p_client_request_id, v_hash
  );
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason', btrim(p_reason), true);

  select * into v_group
  from erp.cutting_groups where id = p_cutting_group_id for update;
  if v_group.id is null then raise exception 'Potongan not found'; end if;
  if v_group.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_group.row_version;
  end if;
  if v_group.status not in ('CUT','PICKED_UP') then
    raise exception 'Only CUT/PICKED_UP Potongan can use pre-sewing material reversal';
  end if;
  if erp.cutting_group_has_downstream_after_pickup(v_group.id) then
    raise exception 'Potongan already has sewing/downstream evidence; reverse downstream documents instead';
  end if;
  if not v_group.material_issue_posted
     and not v_group.material_return_posted
     and not exists (
       select 1 from erp.material_stock_movements m
       where m.source_id = v_group.id
         and m.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN')
         and not exists (
           select 1 from erp.material_stock_movements rv where rv.reversal_of_id = m.id
         )
     )
  then raise exception 'Potongan has no active cutting material flow to reverse'; end if;

  -- Reverse posted return journals first, then the original issue journal.
  -- Any later failure rolls this whole function back atomically.
  for r in
    select je.id
    from erp.journal_entries je
    join erp.cutting_group_rolls cgr on cgr.id = je.source_id
    where cgr.cutting_group_id = v_group.id
      and je.source_type = 'CUTTING_MATERIAL_RETURN_LINE'
      and je.status = 'POSTED'
    order by je.posting_at desc, je.id desc
  loop
    perform erp.reverse_journal(r.id, btrim(p_reason));
    v_reversed_journals := v_reversed_journals + 1;
  end loop;

  for r in
    select je.id
    from erp.journal_entries je
    where je.source_type = 'CUTTING_MATERIAL_ISSUE'
      and je.source_id = v_group.id
      and je.status = 'POSTED'
    order by je.posting_at desc, je.id desc
  loop
    perform erp.reverse_journal(r.id, btrim(p_reason));
    v_reversed_journals := v_reversed_journals + 1;
  end loop;

  -- Positive cutting returns are removed from warehouse first. The normal
  -- negative-stock guard blocks reversal if that returned quantity was consumed.
  -- The original issue is then restored to its source warehouse.
  for r in
    select m.*
    from erp.material_stock_movements m
    where m.source_id = v_group.id
      and m.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN')
      and not exists (
        select 1 from erp.material_stock_movements rv where rv.reversal_of_id = m.id
      )
    order by case m.source_type when 'CUTTING_GROUP_RETURN' then 0 else 1 end,
             m.system_created_at, m.id
  loop
    insert into erp.material_stock_movements(
      material_id, roll_id, location_id, movement_type, qty_signed,
      input_unit_cost, source_type, source_id, physical_at, created_by,
      reversal_of_id, note
    ) values (
      r.material_id, r.roll_id, r.location_id, 'REVERSAL', -r.qty_signed,
      r.unit_cost_snapshot, 'CUTTING_PRESEWING_REVERSAL', v_group.id,
      greatest(clock_timestamp(), r.physical_at), erp.current_app_user_id(),
      r.id, btrim(p_reason)
    );
    v_reversed_movements := v_reversed_movements + 1;
  end loop;

  for r in
    select distinct m.material_id
    from erp.material_stock_movements m
    where m.source_id = v_group.id
      and m.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN')
  loop
    perform erp.recalculate_material_cost(r.material_id);
  end loop;

  update erp.cutting_groups
  set material_issue_posted = false,
      material_return_posted = false,
      status = case when picked_up_at is null then 'CUT' else 'PICKED_UP' end,
      updated_at = statement_timestamp()
  where id = v_group.id
  returning * into v_group;

  v_response := jsonb_build_object(
    'cutting_group_id', v_group.id,
    'status', v_group.status,
    'row_version', v_group.row_version,
    'reversed_movement_count', v_reversed_movements,
    'reversed_journal_count', v_reversed_journals,
    'presewing_reversible', erp.is_cutting_group_presewing_reversible(v_group.id)
  );
  return erp._idempotency_complete(
    'reverse_cutting_material_flow_before_sewing_v2',
    p_client_request_id, v_response
  );
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_cutting_qty_correction(p_correction_id uuid, p_reason text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
DECLARE
  v_batch uuid;
  v_lines jsonb;
BEGIN
  PERFORM erp.require_internal();
  SELECT cutting_batch_id INTO v_batch
  FROM erp.cutting_qty_corrections
  WHERE id=p_correction_id
  FOR UPDATE;
  IF v_batch IS NULL THEN RAISE EXCEPTION 'Correction not found'; END IF;

  SELECT jsonb_agg(jsonb_build_object(
    'cutting_group_id',l.cutting_group_id,
    'size_slot_id',l.size_slot_id,
    'qty_delta_pcs',-l.qty_delta_pcs,
    'notes','Reversal of '||p_correction_id::text
  ))
  INTO v_lines
  FROM erp.cutting_qty_correction_lines l
  WHERE l.correction_id=p_correction_id;

  RETURN erp._post_cutting_qty_correction(
    v_batch,'REVERSAL','REVERSAL',p_reason,v_lines,statement_timestamp(),p_correction_id
  );
END;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_fg_adjustment(p_adjustment_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.fg_adjustments%rowtype;
  r record;
  v_journal uuid;
  v_po uuid;
begin
  perform erp.require_owner_admin();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal FG adjustment wajib diisi'; end if;
  select * into h from erp.fg_adjustments where id=p_adjustment_id for update;
  if h.id is null then raise exception 'FG adjustment tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya FG adjustment POSTED yang dapat direverse'; end if;

  for r in
    select distinct fl.product_id
    from erp.fg_adjustment_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.adjustment_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  for r in
    select fm.id
    from erp.fg_stock_movements fm
    join erp.fg_adjustment_items fai on fai.id=fm.source_id
    where fai.adjustment_id=h.id and fm.source_type='FG_ADJUSTMENT_ITEM' and fm.movement_type='ADJUSTMENT'
    order by fm.physical_at desc,fm.id desc
  loop
    perform erp.reverse_fg_movement(r.id,p_reason);
  end loop;

  select id into v_journal from erp.journal_entries
  where source_type='FG_ADJUSTMENT' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;

  update erp.fg_adjustments set status='REVERSED' where id=h.id;

  for v_po in
    select distinct fl.po_id
    from erp.fg_adjustment_items fai join erp.fg_lots fl on fl.id=fai.lot_id
    where fai.adjustment_id=h.id and fl.po_id is not null and fl.lot_origin in ('PRODUCTION','CONVERSION')
  loop
    perform erp.sync_po_hpp_to_gl(v_po,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  end loop;

  for r in
    select distinct fl.product_id
    from erp.fg_adjustment_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.adjustment_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.sync_non_po_product_hpp_to_gl_v2620f(
      r.product_id,case when h.status='DRAFT' then (h.physical_at AT TIME ZONE 'Asia/Jakarta')::date else ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date end,
      case when h.status='DRAFT' then 'FG_ADJUSTMENT' else 'FG_ADJUSTMENT_REVERSAL' end,
      h.id,'Cumulative adjustment lifecycle: '||h.reason
    );
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values ('fg_adjustments',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_laundry_claim_resolution(p_claim_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  c erp.laundry_claims%rowtype;
  v_journal uuid;
  v_po uuid;
  v_po_status text;
begin
  perform erp.require_owner_admin();
  if nullif(pg_catalog.btrim(p_reason),'') is null then
    raise exception 'Alasan pembatalan resolusi claim laundry wajib diisi';
  end if;

  -- CASH_COMPENSATION creators lock this same claim row before inserting.
  -- Therefore the dependency check and creation serialize in both orders.
  select * into c from erp.laundry_claims where id=p_claim_id for update;
  if c.id is null then raise exception 'Laundry claim tidak ditemukan'; end if;
  if c.status='REJECTED' then return; end if;
  if c.status not in('SETTLED','WRITTEN_OFF') then
    raise exception 'Hanya claim yang sudah SETTLED/WRITTEN_OFF yang dapat dibatalkan resolusinya';
  end if;
  if exists(
    select 1 from erp.bs_resolutions r
    where r.source_laundry_claim_id=c.id
      and r.resolution_type='CASH_COMPENSATION'
  ) then
    raise exception using
      errcode='23503',
      message='CLAIM_RESOLUTION_IN_USE_BY_ACTIVE_BS_CASH_COMPENSATION',
      detail='Reverse the dependent BS CASH_COMPENSATION disposition first; claim money and BS status cannot diverge.';
  end if;

  select je.id into v_journal
  from erp.journal_entries je
  where je.source_type='LAUNDRY_CLAIM_SETTLEMENT'
    and je.source_id=c.id and je.status='POSTED'
  order by je.posting_at desc,je.id desc limit 1;

  if c.status='SETTLED' and c.compensation_amount>0 and v_journal is null then
    raise exception 'Jurnal settlement claim tidak ditemukan; pembatalan dihentikan agar AP vendor tidak rusak';
  end if;
  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;

  if c.delivery_id is not null and c.claim_type in('MISSING','STUCK') then
    select ld.po_id into v_po from erp.laundry_deliveries ld where ld.id=c.delivery_id;
    if v_po is not null then
      select po.status into v_po_status
      from erp.production_orders po where po.id=v_po for update;
      if v_po_status='FINISHED' then
        perform erp.reopen_production_order(v_po,'Laundry claim resolution reversed: '||p_reason);
        update erp.production_orders
        set status='LAUNDRY',current_stage='LAUNDRY',updated_at=statement_timestamp()
        where id=v_po;
      end if;
    end if;
  end if;

  update erp.laundry_claims
  set status='REJECTED',
      notes=pg_catalog.concat_ws(E'\n',notes,'Resolution reversed/cancelled: '||p_reason)
  where id=c.id;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('laundry_claims',c.id,'REVERSE',jsonb_build_object(
    'previous_status',c.status,
    'new_status','REJECTED',
    'settlement_journal_reversed',v_journal is not null,
    'finished_po_reopened',v_po_status='FINISHED'
  ),erp.current_app_user_id(),p_reason);
end
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_laundry_delivery(p_delivery_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.laundry_deliveries%rowtype;
  r record;
  v_po_status text;
begin
  perform erp.require_internal();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal pengiriman laundry wajib diisi'; end if;

  select * into h from erp.laundry_deliveries where id=p_delivery_id for update;
  if h.id is null then raise exception 'Pengiriman laundry tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status not in ('SENT','PARTIAL_RETURN','RETURNED','CLOSED') then
    raise exception 'Hanya pengiriman laundry yang sudah diposting yang dapat direverse';
  end if;

  select status into v_po_status from erp.production_orders where id=h.po_id for update;
  if v_po_status='FINISHED' then
    raise exception 'PO sudah FINISHED. Jangan reverse pengiriman laundry langsung; koreksi/reopen transaksi downstream terlebih dahulu.';
  end if;

  if exists(select 1 from erp.laundry_receipts where delivery_id=h.id and status<>'REVERSED') then
    raise exception 'Pengiriman laundry ini sudah memiliki penerimaan aktif. Reverse penerimaan laundry terlebih dahulu.';
  end if;
  if exists(select 1 from erp.laundry_claims where delivery_id=h.id and status<>'REJECTED') then
    raise exception 'Pengiriman laundry ini sudah memiliki claim aktif/terselesaikan. Bereskan claim terlebih dahulu sebelum reversal.';
  end if;

  update erp.laundry_deliveries set status='REVERSED',updated_at=statement_timestamp() where id=h.id;

  for r in select distinct cutting_group_id from erp.laundry_delivery_lines where delivery_id=h.id loop
    if exists(
      select 1 from erp.laundry_receipt_lines lrl
      join erp.laundry_receipts lr on lr.id=lrl.receipt_id
      join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
      join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
      where ldl.cutting_group_id=r.cutting_group_id and lr.status='POSTED' and ld.status<>'REVERSED'
    ) then
      update erp.cutting_groups set status='RETURNED' where id=r.cutting_group_id;
    elsif exists(
      select 1 from erp.laundry_delivery_lines ldl join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
      where ldl.cutting_group_id=r.cutting_group_id and ld.status not in('DRAFT','REVERSED')
    ) then
      update erp.cutting_groups set status='LAUNDRY' where id=r.cutting_group_id;
    else
      update erp.cutting_groups
      set status=case when picked_up_at is not null then 'PICKED_UP' else 'CUT' end
      where id=r.cutting_group_id;
    end if;
  end loop;

  if v_po_status not in ('ON_HOLD','CANCELLED') then
    if exists(select 1 from erp.qc_inspections where po_id=h.po_id and status='POSTED')
       or exists(
         select 1 from erp.laundry_receipts lr join erp.laundry_deliveries ld on ld.id=lr.delivery_id
         where ld.po_id=h.po_id and lr.status='POSTED' and ld.status<>'REVERSED'
       ) then
      update erp.production_orders set status='QC',current_stage='QC',updated_at=statement_timestamp() where id=h.po_id;
    elsif exists(select 1 from erp.laundry_deliveries where po_id=h.po_id and status not in('DRAFT','REVERSED')) then
      update erp.production_orders set status='LAUNDRY',current_stage='LAUNDRY',updated_at=statement_timestamp() where id=h.po_id;
    elsif exists(select 1 from erp.cutting_groups where po_id=h.po_id and picked_up_at is not null) then
      update erp.production_orders set status='SEWING',current_stage='SEWING',updated_at=statement_timestamp() where id=h.po_id;
    else
      update erp.production_orders set status='CUTTING',current_stage='CUTTING',updated_at=statement_timestamp() where id=h.po_id;
    end if;
  end if;

  perform erp.sync_laundry_accrual(h.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  if exists(select 1 from erp.fg_lots where po_id=h.po_id) then
    perform erp.rebuild_po_hpp(h.po_id,'Laundry delivery reversed: '||p_reason);
    perform erp.propagate_conversion_hpp_for_po(h.po_id);
    perform erp.sync_po_hpp_to_gl(h.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  end if;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('laundry_deliveries',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_laundry_receipt(p_receipt_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  h erp.laundry_receipts%rowtype;
  d erp.laundry_deliveries%rowtype;
  r record;
  b record;
  v_sent bigint;
  v_returned bigint;
  v_po_status text;
begin
  perform erp.require_internal();
  if nullif(btrim(p_reason),'') is null then raise exception 'Alasan reversal penerimaan laundry wajib diisi'; end if;
  select * into h from erp.laundry_receipts where id=p_receipt_id for update;
  if h.id is null then raise exception 'Penerimaan laundry tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya penerimaan laundry POSTED yang dapat direverse'; end if;
  select * into d from erp.laundry_deliveries where id=h.delivery_id for update;
  if d.id is null or d.status='REVERSED' then raise exception 'Pengiriman laundry sumber tidak aktif'; end if;
  select status into v_po_status from erp.production_orders where id=d.po_id for update;
  if v_po_status='FINISHED' then
    raise exception 'PO sudah FINISHED. Reopen/koreksi transaksi downstream terlebih dahulu sebelum reversal penerimaan laundry.';
  end if;

  perform erp.assert_laundry_receipt_reversal_payroll_safe(h.id);
  if exists(
    select 1 from erp.qc_inspection_items qi
    join erp.qc_inspections qh on qh.id=qi.inspection_id
    where qi.source_laundry_receipt_line_id in(select id from erp.laundry_receipt_lines where receipt_id=h.id)
      and qh.status<>'REVERSED'
  ) then raise exception 'Penerimaan laundry ini sudah dipakai QC. Reverse QC aktif terlebih dahulu.'; end if;
  if exists(
    select 1 from erp.vendor_invoice_items vii join erp.vendor_invoices vi on vi.id=vii.invoice_id
    where vii.receipt_line_id in(select id from erp.laundry_receipt_lines where receipt_id=h.id)
      and vi.status<>'REVERSED'
  ) then raise exception 'Penerimaan laundry ini sudah masuk invoice vendor. Reverse invoice vendor aktif terlebih dahulu.'; end if;
  if exists(
    select 1 from erp.laundry_claims lc
    where (lc.receipt_line_id in(select id from erp.laundry_receipt_lines where receipt_id=h.id) or lc.delivery_id=d.id)
      and lc.status<>'REJECTED'
  ) then raise exception 'Penerimaan/delivery laundry ini sudah memiliki claim aktif/terselesaikan. Bereskan claim terlebih dahulu.'; end if;

  for r in select * from erp.laundry_receipt_lines where receipt_id=h.id and qty_bs_laundry>0
  loop
    for b in
      select * from erp.bs_cases bc
      where bc.source_laundry_receipt_line_id=r.id
         or bc.bs_number='BS-LAU-'||h.receipt_number||'-'||substr(r.id::text,1,8)
      for update
    loop
      if exists(select 1 from erp.rework_orders where bs_case_id=b.id and status<>'CANCELLED')
         or exists(select 1 from erp.bs_resolutions where bs_case_id=b.id) then
        raise exception 'BS dari penerimaan laundry ini sudah diproses/rework. Batalkan downstream BS terlebih dahulu.';
      end if;
      update erp.bs_cases
      set status='CANCELLED',notes=concat_ws(E'\n',notes,'CANCELLED karena source laundry receipt direverse: '||p_reason),updated_at=statement_timestamp()
      where id=b.id;
    end loop;
  end loop;

  update erp.laundry_receipts set status='REVERSED',updated_at=statement_timestamp() where id=h.id;
  select coalesce(sum(qty_sent_pcs),0) into v_sent from erp.laundry_delivery_lines where delivery_id=d.id;
  select coalesce(sum(lrl.qty_good_received+lrl.qty_bs_laundry),0) into v_returned
  from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id
  where lr.delivery_id=d.id and lr.status='POSTED';
  update erp.laundry_deliveries
  set status=case when v_returned>=v_sent and v_sent>0 then 'RETURNED'
                  when v_returned>0 then 'PARTIAL_RETURN' else 'SENT' end,
      updated_at=statement_timestamp()
  where id=d.id;

  for r in
    select distinct ldl.cutting_group_id
    from erp.laundry_receipt_lines lrl
    join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
    where lrl.receipt_id=h.id
  loop
    if exists(
      select 1 from erp.laundry_receipt_lines x
      join erp.laundry_receipts xr on xr.id=x.receipt_id
      join erp.laundry_delivery_lines xdl on xdl.id=x.delivery_line_id
      where xdl.cutting_group_id=r.cutting_group_id and xr.status='POSTED'
    ) then update erp.cutting_groups set status='RETURNED' where id=r.cutting_group_id;
    elsif exists(
      select 1 from erp.laundry_delivery_lines xdl
      join erp.laundry_deliveries xd on xd.id=xdl.delivery_id
      where xdl.cutting_group_id=r.cutting_group_id and xd.status not in('DRAFT','REVERSED')
    ) then update erp.cutting_groups set status='LAUNDRY' where id=r.cutting_group_id;
    else update erp.cutting_groups
      set status=case when picked_up_at is not null then 'PICKED_UP' else 'CUT' end
      where id=r.cutting_group_id;
    end if;
  end loop;

  if v_po_status not in ('ON_HOLD','CANCELLED') then
    if exists(select 1 from erp.qc_inspections where po_id=d.po_id and status='POSTED')
       or exists(select 1 from erp.laundry_receipts lr join erp.laundry_deliveries ld on ld.id=lr.delivery_id
                 where ld.po_id=d.po_id and lr.status='POSTED' and ld.status<>'REVERSED') then
      update erp.production_orders set status='QC',current_stage='QC',updated_at=statement_timestamp() where id=d.po_id;
    elsif exists(select 1 from erp.laundry_deliveries where po_id=d.po_id and status not in('DRAFT','REVERSED')) then
      update erp.production_orders set status='LAUNDRY',current_stage='LAUNDRY',updated_at=statement_timestamp() where id=d.po_id;
    elsif exists(select 1 from erp.cutting_groups where po_id=d.po_id and picked_up_at is not null) then
      update erp.production_orders set status='SEWING',current_stage='SEWING',updated_at=statement_timestamp() where id=d.po_id;
    else update erp.production_orders set status='CUTTING',current_stage='CUTTING',updated_at=statement_timestamp() where id=d.po_id;
    end if;
  end if;

  perform erp.sync_laundry_accrual(d.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  if exists(select 1 from erp.fg_lots where po_id=d.po_id) then
    perform erp.rebuild_po_hpp(d.po_id,'Laundry receipt reversed: '||p_reason);
    perform erp.propagate_conversion_hpp_for_po(d.po_id);
    perform erp.sync_po_hpp_to_gl(d.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  end if;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('laundry_receipts',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_material_adjustment(p_adjustment_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare h erp.material_adjustments%rowtype;r record;v_journal uuid;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal adjustment bahan wajib diisi'; end if;
  select * into h from erp.material_adjustments where id=p_adjustment_id for update;
  if h.id is null then raise exception 'Material adjustment tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya material adjustment POSTED yang dapat direverse'; end if;

  for r in
    select msm.id
    from erp.material_stock_movements msm
    join erp.material_adjustment_items mai on mai.id=msm.source_id
    where mai.adjustment_id=h.id and msm.source_type='MATERIAL_ADJUSTMENT_ITEM' and msm.movement_type<>'REVERSAL'
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id)
    order by msm.physical_at desc,msm.id desc
  loop perform erp.reverse_material_movement(r.id,p_reason); end loop;

  select id into v_journal from erp.journal_entries where source_type='MATERIAL_ADJUSTMENT' and source_id=h.id and status='POSTED' order by posting_at desc,id desc limit 1;
  if exists(select 1 from erp.material_adjustment_items where adjustment_id=h.id) and v_journal is null
     and coalesce((select round(sum(msm.qty_signed*coalesce(msm.original_unit_cost_snapshot,msm.unit_cost_snapshot)),2)
       from erp.material_stock_movements msm
       join erp.material_adjustment_items mai on mai.id=msm.source_id
       where mai.adjustment_id=h.id and msm.source_type='MATERIAL_ADJUSTMENT_ITEM'
         and msm.reversal_of_id is null),0)<>0 then
    raise exception 'Jurnal material adjustment tidak ditemukan; reversal dibatalkan agar stok dan pembukuan tidak berbeda';
  end if;
  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
  update erp.material_adjustments set status='REVERSED',updated_at=statement_timestamp() where id=h.id;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('material_adjustments',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;$function$;

CREATE OR REPLACE FUNCTION erp.reverse_material_purchase(p_purchase_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare h erp.material_purchase_headers%rowtype;v_journal uuid;v_total numeric(24,6);
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal pembelian bahan wajib diisi'; end if;
  select * into h from erp.material_purchase_headers where id=p_purchase_id for update;
  if h.id is null then raise exception 'Pembelian bahan tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya pembelian bahan POSTED yang dapat direverse'; end if;


  -- The receipt row is already locked. Invoice posting takes the same row lock
  -- and rechecks source state, so either serialization order preserves the link.
  -- Do not lock invoice headers here: invoice writers acquire those first.
  if exists(
    select 1 from erp.material_supplier_invoice_lines il
    join erp.material_supplier_invoices ih on ih.id=il.invoice_id
    join erp.material_purchase_items pi on pi.id=il.purchase_item_id
    where pi.purchase_id=h.id and ih.status='POSTED'
  ) then
    raise exception 'Reverse posted supplier invoices before reversing this receipt';
  end if;

  if exists(select 1 from erp.supplier_payments where purchase_id=h.id and status='POSTED') then
    raise exception 'Pembelian ini sudah memiliki pembayaran supplier. Reverse pembayaran aktif terlebih dahulu.';
  end if;
  if exists(
    select 1 from erp.material_supplier_return_items ri join erp.material_supplier_returns rh on rh.id=ri.return_id
    join erp.material_purchase_items pi on pi.id=ri.purchase_item_id
    where pi.purchase_id=h.id and rh.status='POSTED'
  ) then raise exception 'Pembelian ini sudah memiliki retur supplier POSTED. Reverse retur terlebih dahulu.'; end if;
  if exists(select 1 from erp.material_purchase_cost_corrections where purchase_id=h.id and status='POSTED') then
    raise exception 'Pembelian ini sudah memiliki koreksi harga POSTED. Reverse koreksi harga terlebih dahulu.';
  end if;

  select coalesce(sum(line_total),0) into v_total from erp.material_purchase_items where purchase_id=h.id;
  select id into v_journal from erp.journal_entries where source_type='MATERIAL_PURCHASE' and source_id=h.id and status='POSTED' order by posting_at desc,id desc limit 1;
  if v_total>0.005 and v_journal is null then raise exception 'Jurnal pembelian bahan tidak ditemukan; reversal dibatalkan agar stok/AP tidak rusak'; end if;

  -- Exact source-time cancellation. Recalculation will reject the whole transaction if
  -- removing this purchase would make historical material/roll stock negative.
  perform erp._reverse_material_purchase_stock_at_source_time(h.id,p_reason);
  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
  update erp.material_purchase_headers set status='REVERSED',payment_status='UNPAID',updated_at=statement_timestamp() where id=h.id;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('material_purchase_headers',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_material_supplier_return(p_return_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_n_before jsonb;v_n_purchases uuid[];
  h erp.material_supplier_returns%rowtype;
  r record;
  v_journal uuid;
  v_purchase uuid;
  v_payable numeric;
  v_paid numeric;
  v_roll_qty numeric;
  v_cost numeric;
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_reason),'') is null then raise exception 'Alasan reversal retur supplier wajib diisi'; end if;
  select * into h from erp.material_supplier_returns where id=p_return_id for update;
  if h.id is null then raise exception 'Retur supplier tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya retur supplier POSTED yang dapat direverse'; end if;

  perform erp.lock_supplier_return_source_purchases(h.id);  select array_agg(distinct i.purchase_id order by i.purchase_id) into v_n_purchases
  from erp.material_supplier_return_items l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.return_id=h.id;
  perform 1 from erp.material_purchase_headers where id=any(v_n_purchases) order by id for update;
  v_n_before:=erp._cp6_supplier_cent_state(v_n_purchases);

  select id into v_journal from erp.journal_entries
  where source_type='MATERIAL_SUPPLIER_RETURN' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if exists(
    select 1 from erp.material_supplier_return_items
    where return_id=h.id and(
      coalesce(ap_relief_amount_snapshot,0)<>0
      or coalesce(grni_relief_amount_snapshot,0)<>0
    )
  ) and v_journal is null and not exists(select 1 from erp.supplier_cent_posting_facts where source_type='MATERIAL_SUPPLIER_RETURN' and source_id=h.id and phase='POST') then
    raise exception 'Jurnal retur supplier tidak ditemukan; reversal dibatalkan agar stok/AP/GRNI tidak rusak';
  end if;

  update erp.material_supplier_returns set status='REVERSED',updated_at=statement_timestamp() where id=h.id;

  -- Recalculate the purchase source input before reverse_material_movement runs,
  -- so its single chronological replay sees the restored GRNI cost-basis.
  for r in
    select distinct ri.purchase_item_id,i.material_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by ri.purchase_item_id
  loop
    v_cost:=erp.material_purchase_current_unit_cost(r.purchase_item_id);
    update erp.material_stock_movements msm
    set input_unit_cost=v_cost
    where msm.movement_type='PURCHASE' and msm.qty_signed>0 and(
      (msm.source_type='MATERIAL_PURCHASE_ITEM' and msm.source_id=r.purchase_item_id)
      or
      (msm.source_type='MATERIAL_PURCHASE_ROLL' and msm.source_id in(
        select mr.id from erp.material_rolls mr where mr.purchase_item_id=r.purchase_item_id
      ))
    );
  end loop;

  for r in
    select msm.id,ri.roll_id,ri.purchase_item_id
    from erp.material_stock_movements msm
    join erp.material_supplier_return_items ri on ri.id=msm.source_id
    where ri.return_id=h.id
      and msm.source_type='MATERIAL_SUPPLIER_RETURN_ITEM'
      and msm.movement_type='SUPPLIER_RETURN'
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id)
    order by msm.physical_at desc,msm.id desc
  loop
    perform erp.reverse_material_movement(r.id,p_reason);
    perform erp.refresh_material_purchase_item_match_state(r.purchase_item_id);
    if r.roll_id is not null then
      select coalesce(sum(qty_signed),0) into v_roll_qty
      from erp.material_stock_movements where roll_id=r.roll_id;
      update erp.material_rolls
      set cached_qty=v_roll_qty,
          status=case when v_roll_qty<=0 then 'EXHAUSTED'
                      when v_roll_qty<original_qty then 'HALF_USED' else 'AVAILABLE' end,
          updated_at=statement_timestamp()
      where id=r.roll_id;
    end if;
  end loop;


  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by i.purchase_id
  loop
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0)
    into v_payable,v_paid;
    update erp.material_purchase_headers
    set payment_status=case when v_paid=round(v_payable,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end
    where id=v_purchase;
  end loop;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('material_supplier_returns',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
  perform erp._cp6_apply_supplier_cent_event('MATERIAL_SUPPLIER_RETURN',h.id,erp._cp3_business_date(h.physical_at),p_reason,v_n_before,true);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_misc_finance(p_transaction_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  t erp.misc_finance_transactions%rowtype;
  v_journal uuid;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal pendapatan/pengeluaran lain-lain wajib diisi'; end if;

  select * into t from erp.misc_finance_transactions where id=p_transaction_id for update;
  if t.id is null then raise exception 'Transaksi pendapatan/pengeluaran lain-lain tidak ditemukan'; end if;
  if t.status='REVERSED' then return; end if;
  if t.status<>'POSTED' then raise exception 'Hanya transaksi lain-lain yang sudah POSTED yang dapat direverse'; end if;

  select id into v_journal
  from erp.journal_entries
  where source_type='MISC_FINANCE' and source_id=t.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if v_journal is null then raise exception 'Jurnal transaksi lain-lain tidak ditemukan; reversal dibatalkan agar kas tidak rusak'; end if;

  perform erp.reverse_journal(v_journal,p_reason);
  update erp.misc_finance_transactions set status='REVERSED',updated_at=statement_timestamp() where id=t.id;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values ('misc_finance_transactions',t.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_opening_financial_correction(p_correction_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare c erp.opening_financial_corrections%rowtype;i erp.opening_balance_items%rowtype;b erp.opening_subledger_balances%rowtype;v_journal uuid;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal koreksi saldo awal wajib diisi'; end if;
  select * into c from erp.opening_financial_corrections where id=p_correction_id for update;
  if c.id is null then raise exception 'Koreksi saldo awal tidak ditemukan'; end if;
  if c.status='REVERSED' then return; end if;
  if exists(select 1 from erp.opening_financial_corrections x where x.opening_item_id=c.opening_item_id and x.status='POSTED' and x.id<>c.id and x.correction_seq>c.correction_seq) then
    raise exception 'Ada koreksi saldo awal yang lebih baru. Reverse koreksi terbaru terlebih dahulu.';
  end if;
  select * into i from erp.opening_balance_items where id=c.opening_item_id for update;
  if i.balance_type in ('CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE','VENDOR_PAYABLE','SUPPLIER_PAYABLE','CUSTOMER_RECEIVABLE') then
    select * into b from erp.opening_subledger_balances where opening_item_id=i.id for update;
    if b.settled_amount>c.previous_amount_snapshot then
      raise exception 'Reversal koreksi akan menurunkan saldo awal ke %, tetapi sudah disettle %. Reverse settlement terkait terlebih dahulu.',c.previous_amount_snapshot,b.settled_amount;
    end if;
  end if;
  select id into v_journal from erp.journal_entries where source_type='OPENING_FINANCIAL_CORRECTION' and source_id=c.id and status='POSTED' order by posting_at desc,id desc limit 1;
  if v_journal is null then raise exception 'Jurnal koreksi saldo awal tidak ditemukan'; end if;
  perform erp.reverse_journal(v_journal,p_reason);
  if b.id is not null then
    update erp.opening_subledger_balances set original_amount=c.previous_amount_snapshot,
      status=case when settled_amount=c.previous_amount_snapshot then 'SETTLED' when settled_amount>0 then 'PARTIAL' else 'OPEN' end,
      updated_at=statement_timestamp() where id=b.id;
  end if;
  update erp.opening_financial_corrections set status='REVERSED',reversed_at=clock_timestamp(),reversal_reason=p_reason where id=c.id;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('opening_balance_items',i.id,'REVERSE',jsonb_build_object('correction_id',c.id,'restored_amount',c.previous_amount_snapshot,'correction_type','OPENING_FINANCIAL_CORRECTION'),erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_opening_hpp_correction(p_correction_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  c erp.opening_hpp_corrections%rowtype;
  l erp.fg_lots%rowtype;
  v_current_id uuid;
  v_current_hpp numeric(20,6);
  v_ver integer;
  v_new_id uuid;
  v_descends boolean;
begin
  perform erp.require_owner_admin();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal koreksi HPP opening wajib diisi'; end if;
  select * into c from erp.opening_hpp_corrections where id=p_correction_id for update;
  if c.id is null then raise exception 'Koreksi HPP opening tidak ditemukan'; end if;
  if c.status='REVERSED' then return; end if;

  if exists(
    select 1
    from erp.opening_hpp_corrections x
    join erp.hpp_versions hx on hx.id=x.hpp_version_id
    join erp.hpp_versions hc on hc.id=c.hpp_version_id
    where x.lot_id=c.lot_id and x.status='POSTED' and x.id<>c.id
      and hx.version_no>hc.version_no
  ) then
    raise exception 'Ada koreksi HPP opening yang lebih baru. Reverse yang terbaru dulu.';
  end if;

  select * into l from erp.fg_lots where id=c.lot_id for update;
  if exists(
    select 1
    from erp.product_conversion_allocations pca
    join erp.product_conversions pc on pc.id=pca.conversion_id
    where pca.source_lot_id=l.id and pc.status='POSTED'
      and pca.original_hpp_per_pcs is distinct from c.previous_hpp_snapshot
  ) then
    raise exception 'Lot sudah dipakai conversion dengan HPP hasil koreksi. Reverse/correct conversion dulu sebelum reversal HPP.';
  end if;

  perform erp.assert_non_po_product_hpp_target_book_v2620f(l.product_id);
  select hpp_version_id,hpp_per_pcs into v_current_id,v_current_hpp
  from erp.v_current_hpp where lot_id=l.id;
  if v_current_id is null then raise exception 'Current HPP lot opening tidak ditemukan'; end if;

  if v_current_id is distinct from c.hpp_version_id then
    with recursive chain as (
      select h.id,h.supersedes_id from erp.hpp_versions h where h.id=v_current_id
      union all
      select h.id,h.supersedes_id
      from erp.hpp_versions h
      join chain x on h.id=x.supersedes_id
    )
    select exists(select 1 from chain where id=c.hpp_version_id) into v_descends;

    if not coalesce(v_descends,false) or abs(v_current_hpp-c.corrected_hpp)>0.000001 then
      raise exception 'Current HPP version tidak lagi konsisten dengan correction ini';
    end if;
  end if;

  select coalesce(max(version_no),0)+1 into v_ver from erp.hpp_versions where lot_id=l.id;
  update erp.hpp_versions set is_current=false where lot_id=l.id and is_current=true;
  insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,supersedes_id,calculation_reason,created_by)
  values(l.id,v_ver,'ADJUSTED',l.initial_qty_pcs,l.initial_qty_pcs*c.previous_hpp_snapshot,true,v_current_id,'Reversal opening HPP correction: '||p_reason,erp.current_app_user_id())
  returning id into v_new_id;

  update erp.opening_hpp_corrections
  set status='REVERSED',reversed_at=statement_timestamp(),reversal_reason=p_reason
  where id=c.id;
  perform erp.sync_opening_lot_hpp_to_gl(l.id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('fg_lots',l.id,'REVERSE',jsonb_build_object('correction_id',c.id,'restored_hpp',c.previous_hpp_snapshot),erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_opening_subledger_settlement(p_settlement_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
DECLARE s erp.opening_subledger_settlements%ROWTYPE;b erp.opening_subledger_balances%ROWTYPE;v_journal uuid;
BEGIN PERFORM erp.require_owner_admin();SELECT * INTO s FROM erp.opening_subledger_settlements WHERE id=p_settlement_id FOR UPDATE;IF s.id IS NULL OR s.status<>'POSTED' THEN RAISE EXCEPTION 'Only POSTED opening settlement can be reversed';END IF;SELECT * INTO b FROM erp.opening_subledger_balances WHERE id=s.balance_id FOR UPDATE;SELECT id INTO v_journal FROM erp.journal_entries WHERE source_type='OPENING_SUBLEDGER_SETTLEMENT' AND source_id=s.id AND status='POSTED' ORDER BY posting_at DESC LIMIT 1;IF v_journal IS NULL THEN RAISE EXCEPTION 'Opening settlement journal not found';END IF;PERFORM erp.reverse_journal(v_journal,COALESCE(NULLIF(trim(p_reason),''),'Opening settlement reversal'));UPDATE erp.opening_subledger_settlements SET status='REVERSED',updated_at=statement_timestamp() WHERE id=s.id;UPDATE erp.opening_subledger_balances SET settled_amount=GREATEST(settled_amount-s.amount,0),status=CASE WHEN GREATEST(settled_amount-s.amount,0)=0 THEN 'OPEN' WHEN GREATEST(settled_amount-s.amount,0)=original_amount THEN 'SETTLED' ELSE 'PARTIAL' END,updated_at=statement_timestamp() WHERE id=b.id;END;$function$;

CREATE OR REPLACE FUNCTION erp.reverse_paid_payroll(p_payroll_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  p erp.payroll_settlements%rowtype;
  r record;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Payroll reversal reason is required'; end if;
  select * into p from erp.payroll_settlements where id=p_payroll_id for update;
  if p.id is null then raise exception 'Payroll not found'; end if;
  if p.status='REVERSED' then return; end if;
  if p.status<>'PAID' then raise exception 'Only PAID payroll uses reverse_paid_payroll; unpaid payroll uses cancel_unpaid_payroll'; end if;
  perform erp._cp3_lock_business_period(p.period_start,p.period_end);
  if exists(
    select 1 from erp.attendance_hpp_pool_sources s
    join erp.attendance_hpp_pools hp on hp.id=s.pool_id
    where s.payroll_id=p.id and hp.status='ACTIVE'
  ) then
    raise exception 'PAYROLL_CONSUMED_BY_ACTIVE_HPP_POOL: cancel the active attendance HPP pool first';
  end if;

  for r in
    select je.id from erp.journal_entries je
    where je.source_id=p.id
      and je.source_type in ('PAYROLL_ATTENDANCE_ACCRUAL','PAYROLL_EXTRA_ACCRUAL','PAYROLL_MANUAL_REDUCTION',
                             'PAYROLL_MATERIAL_DEDUCTION','PAYROLL_OTHER_DEDUCTION','PAYROLL_PAYMENT')
      and je.status='POSTED'
    order by je.posting_at desc,je.id desc
  loop perform erp._cp3_r4_reverse_journal_internal(r.id,p_reason); end loop;

  update erp.payroll_settlements set status='REVERSED',settled_at=null,updated_at=statement_timestamp() where id=p.id;
  for r in select distinct pd.contractor_issue_item_id id from erp.payroll_deductions pd
           where pd.payroll_id=p.id and pd.contractor_issue_item_id is not null
  loop perform erp.refresh_contractor_issue_payroll_status(r.id); end loop;
  for r in select distinct pr.source_id id from erp.payroll_reimbursements pr
           where pr.payroll_id=p.id and pr.source_type='ACCESSORY_BOM' and pr.source_id is not null
  loop
    update erp.contractor_accessory_reimbursement_entitlements e
    set payroll_status=case
      when exists(select 1 from erp.payroll_reimbursements pr2 join erp.payroll_settlements ps2 on ps2.id=pr2.payroll_id
                  where pr2.source_type='ACCESSORY_BOM' and pr2.source_id=e.id and ps2.status='PAID') then 'SETTLED'
      when exists(select 1 from erp.payroll_reimbursements pr2 join erp.payroll_settlements ps2 on ps2.id=pr2.payroll_id
                  where pr2.source_type='ACCESSORY_BOM' and pr2.source_id=e.id and ps2.status<>'REVERSED') then 'ALLOCATED'
      else 'UNALLOCATED' end
    where e.id=r.id;
  end loop;
  for r in
    select distinct bc.id as bs_case_id from erp.bs_cases bc
    where exists(select 1 from erp.payroll_work_items pwi where pwi.payroll_id=p.id and pwi.po_id=bc.po_id)
       or exists(select 1 from erp.payroll_work_items pwi join erp.rework_component_lines rcl on rcl.id=pwi.source_id
                 join erp.bs_case_components bcc on bcc.id=rcl.bs_case_component_id
                 where pwi.payroll_id=p.id and bcc.bs_case_id=bc.id)
  loop perform erp.rebuild_bs_component_counters(r.bs_case_id); end loop;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('payroll_settlements',p.id,'REVERSE_PAID',jsonb_build_object('previous_status','PAID'),erp.current_app_user_id(),p_reason);
end;
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

  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
  update erp.product_conversions set status='REVERSED' where id=h.id;

  for v_po in
    select distinct fl.po_id from erp.product_conversion_allocations a join erp.fg_lots fl on fl.id=a.source_lot_id where a.conversion_id=h.id and fl.po_id is not null
  loop perform erp.sync_po_hpp_to_gl(v_po,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date); end loop;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason) values('product_conversions',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_qc(p_qc_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.qc_inspections%rowtype;
  r record; l record; b record;
  v_journal uuid;
  v_po_status text;
begin
  perform erp.require_internal();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal QC wajib diisi'; end if;
  select * into h from erp.qc_inspections where id=p_qc_id for update;
  if h.id is null then raise exception 'QC tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya QC POSTED yang dapat direverse'; end if;
  select status into v_po_status from erp.production_orders where id=h.po_id for update;
  if v_po_status='FINISHED' then raise exception 'PO sudah FINISHED. Reopen/koreksi downstream terlebih dahulu sebelum reversal QC.'; end if;

  for b in select bc.* from erp.bs_cases bc where bc.qc_item_id in (select id from erp.qc_inspection_items where inspection_id=h.id) and bc.status<>'CANCELLED' for update loop
    if exists(select 1 from erp.rework_orders where bs_case_id=b.id and status<>'CANCELLED')
       or exists(select 1 from erp.bs_resolutions where bs_case_id=b.id) then
      raise exception 'BS hasil QC ini sudah diproses/rework. Batalkan downstream BS terlebih dahulu.';
    end if;
  end loop;

  for l in
    select fl.* from erp.fg_lots fl
    where fl.qc_item_id in (select id from erp.qc_inspection_items where inspection_id=h.id)
      and fl.lot_origin='PRODUCTION'
    for update
  loop
    if erp.fg_lot_has_active_downstream(l.id,'QC_GOOD','QC_ITEM',l.qc_item_id) then
      raise exception 'FG hasil QC masih dipakai transaksi downstream aktif. Reverse transaksi downstream terlebih dahulu.';
    end if;
    if exists(select 1 from erp.contractor_accessory_reimbursement_entitlements e where e.lot_id=l.id and e.payroll_status<>'UNALLOCATED') then
      raise exception 'Hak reimbursement aksesori dari QC ini sudah masuk payroll. Cancel/reverse payroll terlebih dahulu.';
    end if;
  end loop;

  for l in
    select fl.* from erp.fg_lots fl
    where fl.qc_item_id in (select id from erp.qc_inspection_items where inspection_id=h.id) and fl.lot_origin='PRODUCTION'
    for update
  loop
    select id into v_journal from erp.journal_entries
    where source_type='ACCESSORY_REIMBURSE_ACCRUAL' and source_id=l.id and status='POSTED'
    order by posting_at desc,id desc limit 1;
    if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
    update erp.contractor_accessory_reimbursement_entitlements set payroll_status='CANCELLED' where lot_id=l.id and payroll_status='UNALLOCATED';
    for r in select fm.id from erp.fg_stock_movements fm where fm.lot_id=l.id and fm.movement_type='QC_GOOD' and fm.source_type='QC_ITEM' and fm.source_id=l.qc_item_id and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id) loop
      perform erp.reverse_fg_movement(r.id,p_reason);
    end loop;
    update erp.fg_lots set lot_origin='VOIDED_PRODUCTION',is_open=false where id=l.id;
  end loop;

  update erp.bs_cases set status='CANCELLED',notes=concat_ws(E'\n',notes,'CANCELLED karena source QC direverse: '||p_reason),updated_at=statement_timestamp()
  where qc_item_id in (select id from erp.qc_inspection_items where inspection_id=h.id) and status<>'CANCELLED';
  update erp.qc_inspections set status='REVERSED',updated_at=statement_timestamp() where id=h.id;

  if v_po_status not in ('ON_HOLD','CANCELLED') then
    if exists(select 1 from erp.qc_inspections where po_id=h.po_id and status='POSTED')
       or exists(select 1 from erp.laundry_receipts lr join erp.laundry_deliveries ld on ld.id=lr.delivery_id where ld.po_id=h.po_id and lr.status='POSTED' and ld.status<>'REVERSED') then
      update erp.production_orders set status='QC',current_stage='QC',updated_at=statement_timestamp() where id=h.po_id;
    elsif exists(select 1 from erp.laundry_deliveries where po_id=h.po_id and status not in('DRAFT','REVERSED')) then
      update erp.production_orders set status='LAUNDRY',current_stage='LAUNDRY',updated_at=statement_timestamp() where id=h.po_id;
    elsif exists(select 1 from erp.cutting_groups where po_id=h.po_id and picked_up_at is not null) then
      update erp.production_orders set status='SEWING',current_stage='SEWING',updated_at=statement_timestamp() where id=h.po_id;
    else
      update erp.production_orders set status='CUTTING',current_stage='CUTTING',updated_at=statement_timestamp() where id=h.po_id;
    end if;
  end if;

  perform erp.sync_laundry_accrual(h.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  perform erp.rebuild_po_hpp(h.po_id,'QC reversed: '||p_reason);
  perform erp.propagate_conversion_hpp_for_po(h.po_id);
  perform erp.sync_po_hpp_to_gl(h.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('qc_inspections',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
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

CREATE OR REPLACE FUNCTION erp.reverse_sale(p_sale_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.sales_headers%rowtype;
  r record;
  v_journal uuid;
  v_expected numeric(24,6);
  v_po uuid;
begin
  perform erp.require_owner_admin();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal penjualan wajib diisi'; end if;

  select * into h from erp.sales_headers where id=p_sale_id for update;
  if h.id is null then raise exception 'Penjualan tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status not in('POSTED','PARTIAL_PAID','PAID') then
    raise exception 'Hanya penjualan yang sudah POSTED/aktif yang dapat direverse';
  end if;
  if exists(select 1 from erp.sales_payments where sale_id=h.id and status='POSTED') then
    raise exception 'Penjualan ini sudah memiliki pembayaran customer. Reverse pembayaran aktif terlebih dahulu.';
  end if;
  if exists(select 1 from erp.sales_returns where sale_id=h.id and status='POSTED') then
    raise exception 'Penjualan ini sudah memiliki retur POSTED. Reverse retur aktif terlebih dahulu.';
  end if;

  -- A missing PO HPP journal is corruption. A sub-cent allocation whose
  -- cumulative PO target did not move is legitimately journal-free.
  for v_po in
    select distinct fl.po_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.assert_po_hpp_target_book_v2620e(v_po);
  end loop;

  for r in
    select distinct fl.product_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  -- HPP may legitimately have had zero document delta.  Global target/book
  -- proof above detects missing value; only commercial value requires a SALE journal.
  select round(coalesce((select sum(line_total)
           from erp.sales_items where sale_id=h.id),0),2)
  into v_expected;
  select id into v_journal from erp.journal_entries
  where source_type='SALE' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if v_expected>0.005 and v_journal is null then
    raise exception 'Jurnal penjualan tidak ditemukan; reversal dibatalkan agar piutang/HPP tidak rusak';
  end if;

  for r in
    select fm.id
    from erp.fg_stock_movements fm
    join erp.sales_items i on i.id=fm.source_id
    where i.sale_id=h.id and fm.source_type='SALE_ITEM' and fm.movement_type='SALE'
      and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id)
    order by fm.physical_at desc,fm.id desc
  loop
    perform erp.reverse_fg_movement(r.id,p_reason);
  end loop;

  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
  update erp.sales_headers set status='REVERSED' where id=h.id;

  for r in
    select distinct fl.product_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.sync_non_po_product_hpp_to_gl_v2620f(
      r.product_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date,'SALE_REVERSAL',h.id,
      'Reverse Sale '||h.id::text||': '||p_reason
    );
  end loop;

  for v_po in
    select distinct fl.po_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    -- First reflect only the exact compensating journal, then let the normal
    -- synchronizer post any cumulative-rounding redistribution still needed by
    -- the remaining active sales.
    perform erp.refresh_po_hpp_gl_baseline(v_po);
    perform erp.sync_po_hpp_to_gl(v_po,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
    perform erp.refresh_po_hpp_gl_baseline(v_po);
    perform erp.assert_po_hpp_target_book_v2620e(v_po);
  end loop;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('sales_headers',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_sales_return(p_return_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.sales_returns%rowtype;
  s erp.sales_headers%rowtype;
  r record;
  v_journal uuid;
  v_expected numeric(24,6);
  v_paid numeric(20,2);
  v_total numeric(20,2);
  v_po uuid;
begin
  perform erp.require_owner_admin();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal retur penjualan wajib diisi'; end if;

  select * into h from erp.sales_returns where id=p_return_id for update;
  if h.id is null then raise exception 'Retur penjualan tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya retur penjualan POSTED yang dapat direverse'; end if;
  select * into s from erp.sales_headers where id=h.sale_id for update;
  if s.id is null or s.status='REVERSED' then raise exception 'Penjualan sumber retur tidak aktif'; end if;

  for v_po in
    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.assert_po_hpp_target_book_v2620e(v_po);
  end loop;

  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  select round(coalesce(sum(i.refund_amount),0),2)
  into v_expected
  from erp.sales_return_items i
  where i.return_id=h.id;
  select id into v_journal from erp.journal_entries
  where source_type='SALES_RETURN' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if v_expected>0.005 and v_journal is null then
    raise exception 'Jurnal retur penjualan tidak ditemukan; reversal dibatalkan agar piutang/HPP tidak rusak';
  end if;

  for r in
    select fm.id,fm.qty_signed,fl.cached_qty_pcs
    from erp.fg_stock_movements fm
    join erp.sales_return_items i on i.id=fm.source_id
    join erp.fg_lots fl on fl.id=fm.lot_id
    where i.return_id=h.id and fm.source_type='SALES_RETURN_ITEM'
      and fm.movement_type='SALE_RETURN'
      and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id)
    order by fm.physical_at desc,fm.id desc
  loop
    if r.cached_qty_pcs<r.qty_signed then
      raise exception 'Barang dari retur ini sudah dipakai/dijual lagi. Reverse transaksi downstream dulu sebelum membatalkan retur.';
    end if;
    perform erp.reverse_fg_movement(r.id,p_reason);
  end loop;

  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
  update erp.sales_returns set status='REVERSED' where id=h.id;

  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.sync_non_po_product_hpp_to_gl_v2620f(
      r.product_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date,'SALES_RETURN_REVERSAL',h.id,
      'Reverse Sales return '||h.id::text||': '||p_reason
    );
  end loop;

  select erp.sale_net_total(s.id)::numeric(20,2) into v_total;
  select coalesce(sum(amount),0)::numeric(20,2) into v_paid
  from erp.sales_payments where sale_id=s.id and status='POSTED';
  update erp.sales_headers
  set status=case when v_paid=v_total then 'PAID' when v_paid>0 and v_paid<v_total then 'PARTIAL_PAID' else 'POSTED' end
  where id=s.id;

  for v_po in
    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(v_po);
    perform erp.sync_po_hpp_to_gl(v_po,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
    perform erp.refresh_po_hpp_gl_baseline(v_po);
    perform erp.assert_po_hpp_target_book_v2620e(v_po);
  end loop;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('sales_returns',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_vendor_invoice(p_invoice_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.vendor_invoices%rowtype;
  r record;
  v_journal uuid;
  v_po uuid;
  v_prior_cost numeric(24,6);
  v_prior_rate numeric(18,6);
  v_prior_status varchar(20);
  v_qty integer;
  v_group_id uuid;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal invoice vendor laundry wajib diisi'; end if;

  select * into h from erp.vendor_invoices where id=p_invoice_id for update;
  if h.id is null then raise exception 'Invoice vendor laundry tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status in ('PARTIAL_PAID','PAID') or exists(select 1 from erp.vendor_payments vp where vp.vendor_invoice_id=h.id and vp.status='POSTED') then
    raise exception 'Invoice vendor laundry sudah memiliki pembayaran. Reverse pembayaran vendor yang masih POSTED terlebih dahulu agar kas dan hutang tetap cocok.';
  end if;
  if h.status<>'POSTED' then raise exception 'Hanya invoice vendor laundry yang sudah POSTED yang dapat direverse'; end if;

  for v_group_id in
    select distinct ldl.cutting_group_id
    from erp.vendor_invoice_items vii
    join erp.laundry_receipt_lines lrl on lrl.id=vii.receipt_line_id
    join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
    where vii.invoice_id=h.id
    order by ldl.cutting_group_id
  loop
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
  end loop;
  perform 1
  from erp.laundry_receipts lr
  where lr.id in(
    select distinct lrl.receipt_id
    from erp.vendor_invoice_items vii
    join erp.laundry_receipt_lines lrl on lrl.id=vii.receipt_line_id
    where vii.invoice_id=h.id
  )
  order by lr.id
  for update;
  perform 1
  from erp.laundry_receipt_lines lrl
  where lrl.id in(
    select vii.receipt_line_id
    from erp.vendor_invoice_items vii where vii.invoice_id=h.id
  )
  order by lrl.id
  for update;

  select id into v_journal
  from erp.journal_entries
  where source_type='VENDOR_INVOICE' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if h.total_amount>0 and v_journal is null then
    raise exception 'Jurnal invoice vendor laundry tidak ditemukan; reversal dibatalkan agar hutang/HPP tidak rusak';
  end if;

  for r in
    select vii.*,lrl.qty_good_received,lrl.qty_bs_laundry,ld.po_id,ldl.estimated_rate_snapshot,
           ca.old_amount as legacy_old_amount
    from erp.vendor_invoice_items vii
    join erp.laundry_receipt_lines lrl on lrl.id=vii.receipt_line_id
    join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
    join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
    left join lateral (
      select x.old_amount
      from erp.cost_adjustments x
      where x.source_type='VENDOR_INVOICE_ITEM' and x.source_id=vii.id
      order by x.entered_at desc,x.id desc limit 1
    ) ca on true
    where vii.invoice_id=h.id
    order by vii.id
  loop
    perform 1 from erp.laundry_receipt_lines where id=r.receipt_line_id for update;
    v_qty:=coalesce(r.qty_good_received,0)+coalesce(r.qty_bs_laundry,0);
    v_prior_cost:=coalesce(r.prior_actual_cost,r.legacy_old_amount);
    v_prior_status:=r.prior_actual_cost_status;
    v_prior_rate:=r.prior_actual_rate_snapshot;

    if v_prior_status is null then
      if v_prior_cost is null or (abs(v_prior_cost)<=0.000001 and r.estimated_rate_snapshot is null) then
        v_prior_status:='PENDING';
        v_prior_cost:=null;
        v_prior_rate:=null;
      else
        v_prior_status:='ESTIMATED';
        if v_prior_cost is null and r.estimated_rate_snapshot is not null then v_prior_cost:=v_qty*r.estimated_rate_snapshot; end if;
        if v_prior_rate is null and v_qty>0 and v_prior_cost is not null then v_prior_rate:=v_prior_cost/v_qty; end if;
      end if;
    end if;

    if v_prior_status='PENDING' then
      v_prior_cost:=null;
      v_prior_rate:=null;
    elsif v_prior_rate is null and v_qty>0 and v_prior_cost is not null then
      v_prior_rate:=v_prior_cost/v_qty;
    end if;

    update erp.laundry_receipt_lines
    set actual_rate_snapshot=v_prior_rate,
        actual_cost=v_prior_cost,
        actual_cost_status=v_prior_status
    where id=r.receipt_line_id;

    insert into erp.cost_adjustments(adjustment_number,po_id,component_type,source_type,source_id,economic_date,old_amount,new_amount,reason,created_by)
    values ('CADJ-REV-'||substr(gen_random_uuid()::text,1,8),r.po_id,'LAUNDRY','VENDOR_INVOICE_REVERSAL',r.id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date,
            r.actual_amount,coalesce(v_prior_cost,0),'Reversal vendor invoice: '||p_reason,erp.current_app_user_id());
  end loop;

  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
  update erp.vendor_invoices set status='REVERSED',updated_at=statement_timestamp() where id=h.id;

  for v_po in
    select distinct ld.po_id
    from erp.vendor_invoice_items vii
    join erp.laundry_receipt_lines lrl on lrl.id=vii.receipt_line_id
    join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
    join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
    where vii.invoice_id=h.id
  loop
    perform erp.sync_laundry_accrual(v_po,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
    if exists(select 1 from erp.fg_lots where po_id=v_po) then
      perform erp.rebuild_po_hpp(v_po,'Vendor laundry invoice reversed: '||p_reason);
      perform erp.propagate_conversion_hpp_for_po(v_po);
      perform erp.sync_po_hpp_to_gl(v_po,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
    end if;
  end loop;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values ('vendor_invoices',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_work_completion(p_completion_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.work_completion_events%rowtype;
  v_journal uuid;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal hasil kerja mandor wajib diisi'; end if;

  select * into h from erp.work_completion_events where id=p_completion_id for update;
  if h.id is null then raise exception 'Transaksi hasil kerja mandor tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya hasil kerja mandor yang sudah POSTED yang dapat direverse'; end if;

  perform erp._cp3_lock_business_date(erp._cp3_business_date(h.physical_at));
  if exists(
    select 1
    from erp.sewing_terminal_events e
    where e.source_work_completion_id=h.id
      and e.event_kind='SELESAI_DIJAHIT'
      and not exists(
        select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=e.id
      )
  ) then
    raise exception 'Work completion masih memiliki SELESAI_DIJAHIT aktif. Reverse melalui reverse_sewing_terminal_v1() terlebih dahulu; jika sudah dikonsumsi ACTIVE pool, cancel pool tersebut lebih dulu.';
  end if;

  if exists(
    select 1
    from erp.payroll_work_items pwi
    join erp.payroll_settlements ps on ps.id=pwi.payroll_id
    join erp.work_completion_lines wcl on wcl.id=pwi.source_id
    where wcl.completion_id=h.id and pwi.source_type='PRODUCTION' and ps.status<>'REVERSED'
  ) then
    raise exception 'Hasil kerja ini sudah masuk payroll mandor. Cancel atau reverse payroll yang masih aktif terlebih dahulu supaya upah tidak dibayar/dicabut dua kali.';
  end if;

  select id into v_journal
  from erp.journal_entries
  where source_type='WORK_COMPLETION' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;

  if exists(select 1 from erp.work_completion_lines where completion_id=h.id and amount_payable>0) and v_journal is null then
    raise exception 'Jurnal hasil kerja mandor tidak ditemukan; reversal dibatalkan agar hutang upah/HPP tidak rusak';
  end if;
  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;

  update erp.work_completion_events set status='REVERSED',updated_at=statement_timestamp() where id=h.id;

  if exists(select 1 from erp.fg_lots where po_id=h.po_id) then
    perform erp.rebuild_po_hpp(h.po_id,'Work completion reversed: '||p_reason);
    perform erp.propagate_conversion_hpp_for_po(h.po_id);
    perform erp.sync_po_hpp_to_gl(h.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  end if;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values ('work_completion_events',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
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
    HAVING COALESCE(SUM(CASE WHEN ps.id IS NOT NULL THEN pd.amount ELSE 0 END),0)>COALESCE(cmii.total_receivable,0)+0.01
  ) x;

  RETURN QUERY SELECT 'KASBON_STATUS_MISMATCH','ERROR',COUNT(*)::bigint,'Kasbon status differs from amount actually paid/allocated'
  FROM (
    SELECT cmii.id,cmii.payroll_status,COALESCE(cmii.total_receivable,0) total_receivable,
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

CREATE OR REPLACE FUNCTION erp.run_v256_integrity_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
begin
  perform erp.require_owner_admin();

  return query
  with ledger as (
    select je.transaction_date balance_date,jl.account_id,
           round(sum(jl.debit),2) debit_total,round(sum(jl.credit),2) credit_total
    from erp.journal_entries je
    join erp.journal_lines jl on jl.journal_entry_id=je.id
    where je.status in ('POSTED','REVERSED')
    group by je.transaction_date,jl.account_id
  ), cmp as (
    select coalesce(l.balance_date,a.balance_date) balance_date,
           coalesce(l.account_id,a.account_id) account_id
    from ledger l full join erp.account_daily_balances a
      on a.balance_date=l.balance_date and a.account_id=l.account_id
    where abs(coalesce(l.debit_total,0)-coalesce(a.debit_total,0))>0.01
       or abs(coalesce(l.credit_total,0)-coalesce(a.credit_total,0))>0.01
  )
  select 'ACCOUNT_DAILY_BALANCE_MISMATCH','ERROR',count(*)::bigint,
         'P&L/Balance Sheet cache differs from journal ledger (original REVERSED journals plus POSTED reversals are both part of accounting history)'
  from cmp;

  return query select 'FUTURE_MATERIAL_MOVEMENT','ERROR',count(*)::bigint,
    'Material physical movement dated more than 5 minutes in the future'
  from erp.material_stock_movements where physical_at>clock_timestamp()+interval '5 minutes';

  return query select 'FUTURE_FG_MOVEMENT','ERROR',count(*)::bigint,
    'Finished-goods physical movement dated more than 5 minutes in the future'
  from erp.fg_stock_movements where physical_at>clock_timestamp()+interval '5 minutes';

  return query select 'FUTURE_WIP_EVENT','ERROR',count(*)::bigint,
    'WIP stage event dated more than 5 minutes in the future'
  from erp.wip_stage_events where physical_at>clock_timestamp()+interval '5 minutes';

  return query select 'FUTURE_JOURNAL_DATE','ERROR',count(*)::bigint,
    'Journal economic/accounting date is in the future'
  from erp.journal_entries where economic_date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date or transaction_date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date;

  return query
  with ctl as (select closed_through,updated_at from erp.accounting_period_control where singleton_id=1)
  select 'CLOSED_PERIOD_LATE_POSTING_LEAK','ERROR',count(*)::bigint,
    'Journal posted after the current close operation has an economic date in the closed period but was not shifted to an open accounting date'
  from erp.journal_entries je cross join ctl
  where ctl.closed_through is not null
    and je.posting_at>ctl.updated_at
    and je.economic_date<=ctl.closed_through
    and je.transaction_date<=ctl.closed_through;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.run_v257_integrity_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
begin
  perform erp.require_owner_admin();

  return query
  select 'WORK_COMPLETION_OVER_EFFECTIVE_QTY','ERROR',count(*)::bigint,
         'Posted work component completed/payable qty exceeds effective Potongan qty'
  from (
    select e.cutting_group_id,l.work_component_id
    from erp.work_completion_events e
    join erp.work_completion_lines l on l.completion_id=e.id
    join erp.v_cutting_group_totals v on v.cutting_group_id=e.cutting_group_id
    where e.status='POSTED'
    group by e.cutting_group_id,l.work_component_id,v.total_pcs
    having sum(l.qty_completed)>v.total_pcs or sum(l.qty_payable)>v.total_pcs
  ) x;

  return query
  select 'WORK_COMPLETION_BEFORE_PICKUP','ERROR',count(*)::bigint,
         'Posted mandor work event has no pickup source or is dated before Potongan pickup'
  from erp.work_completion_events e
  left join erp.cutting_groups cg on cg.id=e.cutting_group_id
  where e.status='POSTED' and (e.cutting_group_id is null or cg.picked_up_at is null or e.physical_at<cg.picked_up_at);

  return query
  select 'FUTURE_WORK_COMPLETION','ERROR',count(*)::bigint,
         'Posted mandor work event is dated more than 5 minutes in the future'
  from erp.work_completion_events e
  where e.status='POSTED' and e.physical_at>clock_timestamp()+interval '5 minutes';

  return query
  select 'QC_OVER_EFFECTIVE_CUTTING_QTY','ERROR',count(*)::bigint,
         'Posted QC GOOD+BS exceeds effective Potongan quantity'
  from (
    select i.cutting_group_id
    from erp.qc_inspection_items i
    join erp.qc_inspections q on q.id=i.inspection_id
    join erp.v_cutting_group_totals v on v.cutting_group_id=i.cutting_group_id
    where q.status='POSTED'
    group by i.cutting_group_id,v.total_pcs
    having sum(i.qty_good_pcs+i.qty_bs_pcs)>v.total_pcs
  ) x;

  return query
  select 'QC_POSTED_WITHOUT_CUTTING_LINEAGE','ERROR',count(*)::bigint,
         'Posted production QC item has no Potongan lineage'
  from erp.qc_inspection_items i join erp.qc_inspections q on q.id=i.inspection_id
  where q.status='POSTED' and i.cutting_group_id is null;

  return query
  select 'FUTURE_QC','ERROR',count(*)::bigint,
         'Posted QC is dated more than 5 minutes in the future'
  from erp.qc_inspections q where q.status='POSTED' and q.physical_at>clock_timestamp()+interval '5 minutes';

  return query select 'FUTURE_OPENING_BALANCE','ERROR',count(*)::bigint,
    'Posted opening balance has a future opening date'
  from erp.opening_balance_headers where status='POSTED' and opening_date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date;

  return query select 'FUTURE_MATERIAL_COST_CORRECTION','ERROR',count(*)::bigint,
    'Posted material cost correction has a future supplier invoice date'
  from erp.material_purchase_cost_corrections where status='POSTED' and invoice_date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date;

  return query select 'FUTURE_OPENING_HPP_CORRECTION','ERROR',count(*)::bigint,
    'Opening HPP correction has a future effective date'
  from erp.opening_hpp_corrections where effective_date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date;

  return query
  with wip as (
    select po.id,
           coalesce(sum(case when jl.account_id=erp.account_id('WIP') then jl.debit-jl.credit else 0 end),0) as residual
    from erp.production_orders po
    left join erp.journal_lines jl on jl.po_id=po.id
    left join erp.journal_entries je on je.id=jl.journal_entry_id and je.status in('POSTED','REVERSED')
    where po.status='FINISHED'
    group by po.id
  )
  select 'FINISHED_PO_WIP_RESIDUAL','ERROR',count(*)::bigint,
         'FINISHED PO still has non-zero WIP balance after final residual close'
  from wip where abs(residual)>0.01;

  return query
  select 'FINISHED_PO_OPEN_BS','ERROR',count(*)::bigint,
         'FINISHED PO still has unresolved BS case(s)'
  from erp.production_orders po
  where po.status='FINISHED' and exists(
    select 1 from erp.bs_cases b where b.po_id=po.id and b.status in('OPEN','IN_REWORK','PARTIAL')
  );

  return query
  select 'FINISHED_PO_WITHOUT_FG','ERROR',count(*)::bigint,
         'FINISHED PO has no active production finished-goods output'
  from erp.production_orders po
  where po.status='FINISHED' and not exists(
    select 1 from erp.fg_lots fl where fl.po_id=po.id and fl.lot_origin='PRODUCTION'
  );

  return query
  with sent as (
    select po.id,
      coalesce((select sum(ldl.qty_sent_pcs) from erp.laundry_delivery_lines ldl join erp.laundry_deliveries ld on ld.id=ldl.delivery_id where ld.po_id=po.id and ld.status not in('DRAFT','REVERSED')),0) sent_qty,
      coalesce((select sum(lrl.qty_good_received+lrl.qty_bs_laundry) from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id join erp.laundry_deliveries ld on ld.id=lr.delivery_id where ld.po_id=po.id and lr.status='POSTED' and ld.status<>'REVERSED'),0) returned_qty,
      coalesce((select sum(lc.qty_claimed) from erp.laundry_claims lc where lc.delivery_id in(select id from erp.laundry_deliveries where po_id=po.id) and lc.claim_type in('MISSING','STUCK') and lc.status in('SETTLED','WRITTEN_OFF')),0) claimed_qty
    from erp.production_orders po where po.status='FINISHED'
  )
  select 'FINISHED_PO_LAUNDRY_OUTSTANDING','ERROR',count(*)::bigint,
         'FINISHED PO still has unresolved laundry quantity'
  from sent where returned_qty+claimed_qty<sent_qty;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.run_v262_integrity_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
  select
    'fabric_profile_non_fabric', 'CRITICAL', count(*)::bigint,
    'Fabric profile rows must reference materials.material_type=FABRIC'
  from erp.fabric_master_profiles fp
  join erp.materials m on m.id = fp.material_id
  where m.material_type <> 'FABRIC'

  union all
  select
    'fabric_benchmark_non_fabric', 'CRITICAL', count(*)::bigint,
    'Fabric benchmark rows must reference materials.material_type=FABRIC'
  from erp.fabric_benchmark_price_versions bp
  join erp.materials m on m.id = bp.material_id
  where m.material_type <> 'FABRIC'

  union all
  select
    'fabric_benchmark_period_overlap', 'CRITICAL', count(*)::bigint,
    'Effective benchmark periods for one fabric must not overlap'
  from erp.fabric_benchmark_price_versions a
  join erp.fabric_benchmark_price_versions b
    on b.material_id = a.material_id and b.id > a.id
   and tstzrange(a.effective_from, a.effective_to, '[)')
       && tstzrange(b.effective_from, b.effective_to, '[)')

  union all
  select
    'purchase_benchmark_snapshot_mismatch', 'CRITICAL', count(*)::bigint,
    'BENCHMARK purchase lines must preserve the referenced price and material snapshot'
  from erp.material_purchase_items i
  left join erp.fabric_benchmark_price_versions bp on bp.id = i.benchmark_price_version_id
  where i.price_source = 'BENCHMARK'
    and (
      bp.id is null
      or bp.material_id <> i.material_id
      or abs(bp.benchmark_price_per_base_uom - i.benchmark_unit_price_snapshot) > 0.000001
      or abs(i.unit_price - i.benchmark_unit_price_snapshot) > 0.000001
    )

  union all
  select
    'purchase_final_price_missing_provenance', 'CRITICAL', count(*)::bigint,
    'FINAL lines require final snapshot, timestamp, and a final source'
  from erp.material_purchase_items i
  where i.price_state = 'FINAL'
    and (
      i.price_source not in ('SUPPLIER_INVOICE','MIGRATION')
      or i.supplier_final_unit_price_snapshot is null
      or i.price_finalized_at is null
    )

  union all
  select
    'posted_purchase_without_lines', 'CRITICAL', count(*)::bigint,
    'Posted purchases must contain at least one line'
  from erp.material_purchase_headers h
  where h.status = 'POSTED'
    and not exists (select 1 from erp.material_purchase_items i where i.purchase_id = h.id)

  union all
  select
    'posted_fabric_roll_total_mismatch', 'CRITICAL', count(*)::bigint,
    'When rolls are used, their original quantity must equal the posted fabric line quantity'
  from erp.material_purchase_items i
  join erp.material_purchase_headers h on h.id = i.purchase_id and h.status = 'POSTED'
  join erp.materials m on m.id = i.material_id and m.material_type = 'FABRIC'
  cross join lateral (
    select count(*) roll_count, coalesce(sum(r.original_qty),0) roll_qty
    from erp.material_rolls r where r.purchase_item_id = i.id
  ) x
  where x.roll_count > 0 and abs(x.roll_qty - i.qty) > 0.000001

  union all
  select
    'stale_idempotency_in_progress', 'WARNING', count(*)::bigint,
    'IN_PROGRESS idempotency rows older than 15 minutes indicate an interrupted request'
  from erp.idempotency_requests
  where status = 'IN_PROGRESS' and updated_at < statement_timestamp() - interval '15 minutes'

  union all
  select
    'app_users_without_active_owner', 'CRITICAL',
    case
      when exists(select 1 from erp.app_users)
       and not exists(select 1 from erp.app_users where role='OWNER' and is_active)
      then 1 else 0
    end::bigint,
    'A non-empty app user registry must retain at least one active OWNER';
$function$;

CREATE OR REPLACE FUNCTION erp.save_accessory_bom_edit(p_bom_version_id uuid, p_items jsonb, p_effective_from timestamp with time zone DEFAULT clock_timestamp(), p_notes text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare b erp.accessory_bom_versions%rowtype;v_last_commit timestamptz;v_eff timestamptz:=coalesce(p_effective_from,clock_timestamp());v_next timestamptz;v_new_end timestamptz;v_new uuid;j jsonb;
begin
  perform erp.require_owner_admin();
  if jsonb_typeof(p_items)<>'array' then raise exception 'BOM accessory items harus berupa array; gunakan [] untuk deklarasi produk tanpa aksesori'; end if;
  select * into b from erp.accessory_bom_versions where id=p_bom_version_id for update;
  if b.id is null then raise exception 'BOM accessory tidak ditemukan'; end if;
  v_last_commit:=erp.accessory_bom_last_committed_at(b.id);
  if v_last_commit is null and not exists(select 1 from erp.po_accessory_bom_commitments where bom_version_id=b.id) then
    delete from erp.accessory_bom_items where bom_version_id=b.id;
    for j in select value from jsonb_array_elements(p_items) loop
      insert into erp.accessory_bom_items(bom_version_id,category_id,qty_per_good_fg_base,hpp_method,hpp_standard_rate,hpp_uom_code,reimbursement_rate,reimbursement_uom_code,notes)
      values(b.id,(j->>'category_id')::uuid,(j->>'qty_per_good_fg_base')::numeric,coalesce(nullif(j->>'hpp_method',''),'CATEGORY_MOVING_AVG'),nullif(j->>'hpp_standard_rate','')::numeric,nullif(j->>'hpp_uom_code',''),coalesce(nullif(j->>'reimbursement_rate','')::numeric,0),nullif(j->>'reimbursement_uom_code',''),j->>'notes');
    end loop;
    update erp.accessory_bom_versions set notes=coalesce(p_notes,notes) where id=b.id;
    insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason,new_data) values('accessory_bom_versions',b.id,'UPDATE',erp.current_app_user_id(),'BOM accessory edited before financial commitment',jsonb_build_object('item_count',jsonb_array_length(p_items),'in_place',true,'explicit_no_accessory',jsonb_array_length(p_items)=0));
    return b.id;
  end if;
  if v_eff<=coalesce(v_last_commit,b.effective_from) or v_eff<=b.effective_from then raise exception 'Tanggal mulai BOM baru harus setelah penggunaan finansial terakhir dan setelah awal versi lama'; end if;
  if b.effective_to is not null and v_eff>=b.effective_to then raise exception 'Tanggal mulai BOM baru harus sebelum akhir versi lama'; end if;
  select min(x.effective_from) into v_next from erp.accessory_bom_versions x where x.product_id=b.product_id and x.id<>b.id and x.effective_from>v_eff;
  v_new_end:=case when b.effective_to is null then v_next when v_next is null then b.effective_to else least(b.effective_to,v_next) end;
  update erp.accessory_bom_versions set effective_to=v_eff where id=b.id;
  insert into erp.accessory_bom_versions(product_id,version_label,effective_from,effective_to,is_active,notes,created_by)
  values(b.product_id,concat(coalesce(b.version_label,'BOM'),' / ',to_char((v_eff AT TIME ZONE 'Asia/Jakarta'),'YYYYMMDD-HH24MI')),v_eff,v_new_end,true,coalesce(p_notes,'Successor BOM from Edit'),erp.current_app_user_id()) returning id into v_new;
  for j in select value from jsonb_array_elements(p_items) loop
    insert into erp.accessory_bom_items(bom_version_id,category_id,qty_per_good_fg_base,hpp_method,hpp_standard_rate,hpp_uom_code,reimbursement_rate,reimbursement_uom_code,notes)
    values(v_new,(j->>'category_id')::uuid,(j->>'qty_per_good_fg_base')::numeric,coalesce(nullif(j->>'hpp_method',''),'CATEGORY_MOVING_AVG'),nullif(j->>'hpp_standard_rate','')::numeric,nullif(j->>'hpp_uom_code',''),coalesce(nullif(j->>'reimbursement_rate','')::numeric,0),nullif(j->>'reimbursement_uom_code',''),j->>'notes');
  end loop;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason,new_data) values('accessory_bom_versions',b.id,'UPDATE',erp.current_app_user_id(),'Committed BOM edited by creating successor',jsonb_build_object('successor_bom_version_id',v_new,'effective_from',v_eff,'item_count',jsonb_array_length(p_items),'explicit_no_accessory',jsonb_array_length(p_items)=0));
  return v_new;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.save_accessory_category_v2(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_id uuid:=nullif(p_payload->>'id','')::uuid;
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_row erp.accessory_categories%rowtype;
  v_active boolean:=coalesce((p_payload->>'is_active')::boolean,true);
begin
  perform erp.require_owner_admin();
  if v_reason is null then raise exception 'change_reason is required';end if;
  if coalesce(btrim(p_payload->>'category_code'),'')='' then raise exception 'category_code is required';end if;
  if coalesce(btrim(p_payload->>'category_name'),'')='' then raise exception 'category_name is required';end if;
  if coalesce(btrim(p_payload->>'base_uom_code'),'')='' then raise exception 'base_uom_code is required';end if;

  v_hash:=erp._request_hash(jsonb_build_object('payload',p_payload,'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('save_accessory_category_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached;end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_id is null then
    if p_expected_version is not null then raise exception 'expected_version must be null on create';end if;
    insert into erp.accessory_categories(
      category_code,category_name,base_uom_code,is_active,notes
    ) values(
      upper(btrim(p_payload->>'category_code')),
      btrim(p_payload->>'category_name'),
      upper(btrim(p_payload->>'base_uom_code')),
      v_active,nullif(btrim(p_payload->>'notes'),'')
    ) returning * into v_row;
  else
    if p_expected_version is null then raise exception 'expected_version is required on update';end if;
    select * into v_row from erp.accessory_categories where id=v_id for update;
    if v_row.id is null then raise exception 'Accessory category not found';end if;
    if v_row.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_row.row_version;
    end if;
    if not v_active and exists(
      select 1 from erp.materials m
      where m.accessory_category_id=v_id and m.is_active
    ) then raise exception 'Accessory category with active material variants cannot be deactivated';end if;
    update erp.accessory_categories
    set category_code=upper(btrim(p_payload->>'category_code')),
        category_name=btrim(p_payload->>'category_name'),
        base_uom_code=upper(btrim(p_payload->>'base_uom_code')),
        is_active=v_active,
        notes=case when p_payload?'notes' then nullif(btrim(p_payload->>'notes'),'') else notes end,
        updated_at=statement_timestamp()
    where id=v_id returning * into v_row;
  end if;

  v_response:=jsonb_build_object(
    'accessory_category_id',v_row.id,'row_version',v_row.row_version,
    'category_code',v_row.category_code,
    'status',case when v_row.is_active then 'ACTIVE' else 'INACTIVE' end
  );
  return erp._idempotency_complete('save_accessory_category_v2',p_client_request_id,v_response);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.save_accessory_material_v2(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_id uuid:=nullif(p_payload->>'id','')::uuid;
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_category uuid:=nullif(p_payload->>'accessory_category_id','')::uuid;
  v_base_uom text;
  v_row erp.materials%rowtype;
  v_active boolean:=coalesce((p_payload->>'is_active')::boolean,true);
begin
  perform erp.require_owner_admin();
  if v_reason is null then raise exception 'change_reason is required';end if;
  if coalesce(btrim(p_payload->>'material_sku'),'')='' then raise exception 'material_sku is required';end if;
  if coalesce(btrim(p_payload->>'material_name'),'')='' then raise exception 'material_name is required';end if;
  if v_category is null then raise exception 'accessory_category_id is required';end if;
  select base_uom_code into v_base_uom
  from erp.accessory_categories
  where id=v_category and is_active;
  if v_base_uom is null then raise exception 'Active accessory category is required';end if;

  v_hash:=erp._request_hash(jsonb_build_object('payload',p_payload,'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('save_accessory_material_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached;end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_id is null then
    if p_expected_version is not null then raise exception 'expected_version must be null on create';end if;
    insert into erp.materials(
      material_sku,material_name,material_type,unit_code,accessory_category_id,is_active
    ) values(
      upper(btrim(p_payload->>'material_sku')),btrim(p_payload->>'material_name'),
      'ACCESSORY',v_base_uom,v_category,v_active
    ) returning * into v_row;
  else
    if p_expected_version is null then raise exception 'expected_version is required on update';end if;
    select * into v_row from erp.materials where id=v_id for update;
    if v_row.id is null or v_row.material_type<>'ACCESSORY' then
      raise exception 'Accessory material not found';
    end if;
    if v_row.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_row.row_version;
    end if;
    if not v_active and abs(v_row.cached_stock_qty)>0.000001 then
      raise exception 'Accessory with non-zero stock cannot be deactivated';
    end if;
    update erp.materials
    set material_sku=upper(btrim(p_payload->>'material_sku')),
        material_name=btrim(p_payload->>'material_name'),
        unit_code=v_base_uom,
        accessory_category_id=v_category,
        is_active=v_active,
        updated_at=statement_timestamp()
    where id=v_id returning * into v_row;
  end if;

  v_response:=jsonb_build_object(
    'material_id',v_row.id,'row_version',v_row.row_version,
    'material_sku',v_row.material_sku,'accessory_category_id',v_row.accessory_category_id,
    'base_uom_code',v_row.unit_code,
    'status',case when v_row.is_active then 'ACTIVE' else 'INACTIVE' end
  );
  return erp._idempotency_complete('save_accessory_material_v2',p_client_request_id,v_response);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.save_cutting_batch_v2(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_id uuid := nullif(p_payload->>'id', '')::uuid;
  v_action text := upper(coalesce(nullif(btrim(p_payload->>'action'), ''), 'SAVE'));
  v_reason text := nullif(btrim(p_payload->>'change_reason'), '');
  v_batch erp.cutting_batches%rowtype;
begin
  perform erp.require_internal();
  if v_reason is null then raise exception 'change_reason is required'; end if;
  if v_action not in ('SAVE','DELETE') then raise exception 'Invalid cutting batch action'; end if;

  v_hash := erp._request_hash(jsonb_build_object('payload', p_payload, 'expected_version', p_expected_version));
  v_cached := erp._idempotency_begin('save_cutting_batch_v2', p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason', v_reason, true);

  if v_id is null then
    if v_action = 'DELETE' then raise exception 'Batch id is required for DELETE'; end if;
    if p_expected_version is not null then raise exception 'expected_version must be null when creating a batch'; end if;
    if nullif(p_payload->>'po_id', '')::uuid is null then raise exception 'po_id is required'; end if;
    if coalesce(btrim(p_payload->>'batch_number'), '') = '' then raise exception 'batch_number is required'; end if;
    if nullif(p_payload->>'cut_at', '')::timestamptz is null then raise exception 'cut_at is required'; end if;
    insert into erp.cutting_batches(
      po_id, batch_number, cut_at, status, notes, created_by
    ) values (
      (p_payload->>'po_id')::uuid, btrim(p_payload->>'batch_number'),
      (p_payload->>'cut_at')::timestamptz,
      upper(coalesce(nullif(btrim(p_payload->>'status'), ''), 'OPEN')),
      nullif(btrim(p_payload->>'notes'), ''), erp.current_app_user_id()
    ) returning * into v_batch;
  else
    if p_expected_version is null then raise exception 'expected_version is required'; end if;
    select * into v_batch from erp.cutting_batches where id = v_id for update;
    if v_batch.id is null then raise exception 'Cutting batch not found'; end if;
    if v_batch.row_version <> p_expected_version then
      raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_batch.row_version;
    end if;
    if v_action = 'DELETE' then
      if exists(select 1 from erp.cutting_groups where cutting_batch_id = v_id) then
        raise exception 'Delete or reassign eligible Potongan before deleting the batch';
      end if;
      if exists(select 1 from erp.cutting_qty_corrections where cutting_batch_id = v_id) then
        raise exception 'Batch with posted quantity corrections cannot be deleted';
      end if;
      delete from erp.cutting_batches where id = v_id;
      v_response := jsonb_build_object('cutting_batch_id', v_id, 'status', 'DELETED');
      return erp._idempotency_complete('save_cutting_batch_v2', p_client_request_id, v_response);
    end if;

    update erp.cutting_batches
    set po_id = case when p_payload ? 'po_id' then nullif(p_payload->>'po_id', '')::uuid else v_batch.po_id end,
        batch_number = coalesce(nullif(btrim(p_payload->>'batch_number'), ''), v_batch.batch_number),
        cut_at = coalesce(nullif(p_payload->>'cut_at', '')::timestamptz, v_batch.cut_at),
        status = upper(coalesce(nullif(btrim(p_payload->>'status'), ''), v_batch.status)),
        notes = case when p_payload ? 'notes' then nullif(btrim(p_payload->>'notes'), '') else v_batch.notes end,
        updated_at = statement_timestamp()
    where id = v_id
    returning * into v_batch;
  end if;

  v_response := jsonb_build_object(
    'cutting_batch_id', v_batch.id, 'status', v_batch.status,
    'row_version', v_batch.row_version
  );
  return erp._idempotency_complete('save_cutting_batch_v2', p_client_request_id, v_response);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.save_fabric_master_v2(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_id uuid := nullif(p_payload->>'id', '')::uuid;
  v_material erp.materials%rowtype;
  v_profile jsonb := coalesce(p_payload->'profile', '{}'::jsonb);
  v_reason text := nullif(btrim(p_payload->>'change_reason'), '');
  v_is_active boolean := coalesce((p_payload->>'is_active')::boolean, true);
begin
  perform erp.require_owner_admin();
  if v_reason is null then raise exception 'change_reason is required'; end if;
  if coalesce(btrim(p_payload->>'material_sku'), '') = '' then raise exception 'material_sku is required'; end if;
  if coalesce(btrim(p_payload->>'material_name'), '') = '' then raise exception 'material_name is required'; end if;
  if coalesce(btrim(p_payload->>'unit_code'), '') = '' then raise exception 'unit_code is required'; end if;

  v_hash := erp._request_hash(jsonb_build_object('payload', p_payload, 'expected_version', p_expected_version));
  v_cached := erp._idempotency_begin('save_fabric_master_v2', p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason', v_reason, true);

  if v_id is null then
    if p_expected_version is not null then
      raise exception 'expected_version must be null when creating a fabric';
    end if;
    insert into erp.materials(
      material_sku, material_name, material_type, unit_code, is_active
    ) values (
      btrim(p_payload->>'material_sku'), btrim(p_payload->>'material_name'),
      'FABRIC', upper(btrim(p_payload->>'unit_code')), v_is_active
    ) returning * into v_material;
    v_id := v_material.id;
  else
    if p_expected_version is null then raise exception 'expected_version is required when updating a fabric'; end if;
    select * into v_material from erp.materials where id = v_id for update;
    if v_material.id is null then raise exception 'Fabric material not found'; end if;
    if v_material.material_type <> 'FABRIC' then raise exception 'Material is not FABRIC'; end if;
    if v_material.row_version <> p_expected_version then
      raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_material.row_version;
    end if;
    if not v_is_active and abs(v_material.cached_stock_qty) > 0.000001 then
      raise exception 'Fabric with non-zero stock cannot be deactivated';
    end if;
    update erp.materials
    set material_sku = btrim(p_payload->>'material_sku'),
        material_name = btrim(p_payload->>'material_name'),
        unit_code = upper(btrim(p_payload->>'unit_code')),
        is_active = v_is_active,
        updated_at = statement_timestamp()
    where id = v_id
    returning * into v_material;
  end if;

  insert into erp.fabric_master_profiles(
    material_id, fabric_category, composition, construction, color_name,
    width_cm, gsm, minimum_stock_qty, preferred_supplier_id, notes,
    created_by, updated_by
  ) values (
    v_id,
    nullif(btrim(v_profile->>'fabric_category'), ''),
    nullif(btrim(v_profile->>'composition'), ''),
    nullif(btrim(v_profile->>'construction'), ''),
    nullif(btrim(v_profile->>'color_name'), ''),
    nullif(v_profile->>'width_cm', '')::numeric,
    nullif(v_profile->>'gsm', '')::numeric,
    coalesce(nullif(v_profile->>'minimum_stock_qty', '')::numeric, 0),
    nullif(v_profile->>'preferred_supplier_id', '')::uuid,
    nullif(btrim(v_profile->>'notes'), ''),
    erp.current_app_user_id(), erp.current_app_user_id()
  )
  on conflict (material_id) do update
  set fabric_category = excluded.fabric_category,
      composition = excluded.composition,
      construction = excluded.construction,
      color_name = excluded.color_name,
      width_cm = excluded.width_cm,
      gsm = excluded.gsm,
      minimum_stock_qty = excluded.minimum_stock_qty,
      preferred_supplier_id = excluded.preferred_supplier_id,
      notes = excluded.notes,
      updated_by = erp.current_app_user_id(),
      updated_at = statement_timestamp();

  select * into v_material from erp.materials where id = v_id;
  v_response := jsonb_build_object(
    'material_id', v_id,
    'row_version', v_material.row_version,
    'material_sku', v_material.material_sku,
    'status', case when v_material.is_active then 'ACTIVE' else 'INACTIVE' end
  );
  return erp._idempotency_complete('save_fabric_master_v2', p_client_request_id, v_response);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.save_laundry_claim_v2(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_id uuid;
  v_action text;
  v_reason text;
  v_claim erp.laundry_claims%rowtype;
  v_target_status text;
  v_unknown text;
  v_claim_type text;
begin
  perform erp.require_internal();
  if p_payload is null or jsonb_typeof(p_payload)<>'object' then
    raise exception 'Claim payload must be a JSON object';
  end if;
  select string_agg(k,',' order by k) into v_unknown
  from jsonb_object_keys(p_payload) k
  where not(k=any(array[
    'id','action','claim_number','vendor_id','delivery_id','receipt_line_id',
    'qty_claimed','claim_type','compensation_amount','status','opened_at',
    'resolution_date','notes','change_reason'
  ]::text[]));
  if v_unknown is not null then raise exception 'Unknown Laundry claim payload keys: %',v_unknown; end if;

  v_id:=nullif(p_payload->>'id','')::uuid;
  v_action:=upper(coalesce(nullif(p_payload->>'action',''),'SAVE'));
  v_reason:=nullif(btrim(p_payload->>'change_reason'),'');
  if v_action not in('SAVE','REJECT','REOPEN') then
    raise exception 'Claim action must be SAVE, REJECT, or REOPEN';
  end if;
  if v_reason is null then raise exception 'change_reason is required'; end if;
  if p_payload?'claim_type' then
    v_claim_type:=upper(coalesce(nullif(p_payload->>'claim_type',''),''));
    if v_claim_type not in('MISSING','STUCK','DAMAGE') then
      raise exception 'Laundry claim type must be MISSING, STUCK, or DAMAGE';
    end if;
  end if;
  if p_payload?'opened_at'
     and nullif(p_payload->>'opened_at','')::timestamptz>clock_timestamp()+interval '5 minutes' then
    raise exception 'Claim opened_at cannot be in the future';
  end if;

  v_hash:=erp._request_hash(jsonb_build_object('payload',p_payload,'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('save_laundry_claim_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_id is null then
    if v_action<>'SAVE' then raise exception 'Create a claim with SAVE first'; end if;
    if p_expected_version is not null then raise exception 'expected_version must be null when creating a claim'; end if;
    if coalesce(btrim(p_payload->>'claim_number'),'')='' then raise exception 'claim_number is required'; end if;
    if not(p_payload?'vendor_id') or not(p_payload?'qty_claimed') or not(p_payload?'claim_type') then
      raise exception 'vendor_id, qty_claimed, and claim_type are required';
    end if;
    insert into erp.laundry_claims(
      claim_number,vendor_id,delivery_id,receipt_line_id,qty_claimed,claim_type,
      compensation_amount,status,opened_at,resolution_date,notes
    ) values(
      btrim(p_payload->>'claim_number'),(p_payload->>'vendor_id')::uuid,
      nullif(p_payload->>'delivery_id','')::uuid,nullif(p_payload->>'receipt_line_id','')::uuid,
      (p_payload->>'qty_claimed')::integer,v_claim_type,
      coalesce(nullif(p_payload->>'compensation_amount','')::numeric,0),'OPEN',
      coalesce(nullif(p_payload->>'opened_at','')::timestamptz,statement_timestamp()),
      nullif(p_payload->>'resolution_date','')::date,nullif(btrim(p_payload->>'notes'),'')
    ) returning * into v_claim;
  else
    if p_expected_version is null then raise exception 'expected_version is required'; end if;
    select * into v_claim from erp.laundry_claims where id=v_id for update;
    if not found then raise exception 'Laundry claim not found'; end if;
    if v_claim.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_claim.row_version;
    end if;
    if v_claim.status in('SETTLED','WRITTEN_OFF') then
      raise exception 'Final claim is locked; use reverse_laundry_claim_resolution first';
    end if;
    if v_action<>'SAVE' and p_payload ?| array[
      'claim_number','vendor_id','delivery_id','receipt_line_id','qty_claimed',
      'claim_type','compensation_amount','status','opened_at','resolution_date','notes'
    ] then raise exception 'REJECT/REOPEN may not edit claim facts'; end if;
    if v_claim.status<>'OPEN' and p_payload ?| array[
      'vendor_id','delivery_id','receipt_line_id','qty_claimed','claim_type','opened_at'
    ] then raise exception 'Accepted claim source, type, quantity, and physical time are immutable'; end if;

    if v_action='REOPEN' then
      perform erp.require_owner_admin();v_target_status:='OPEN';
    elsif v_action='REJECT' then
      v_target_status:='REJECTED';
    else
      if v_claim.status='REJECTED' then raise exception 'Rejected claim requires REOPEN by OWNER/ADMIN'; end if;
      v_target_status:=upper(coalesce(nullif(p_payload->>'status',''),v_claim.status));
      if v_target_status not in('OPEN','ACCEPTED') then
        raise exception 'SAVE claim status must be OPEN or ACCEPTED';
      end if;
    end if;
    update erp.laundry_claims
    set claim_number=coalesce(nullif(btrim(p_payload->>'claim_number'),''),v_claim.claim_number),
        vendor_id=case when p_payload?'vendor_id' then (p_payload->>'vendor_id')::uuid else v_claim.vendor_id end,
        delivery_id=case when p_payload?'delivery_id' then nullif(p_payload->>'delivery_id','')::uuid else v_claim.delivery_id end,
        receipt_line_id=case when p_payload?'receipt_line_id' then nullif(p_payload->>'receipt_line_id','')::uuid else v_claim.receipt_line_id end,
        qty_claimed=case when p_payload?'qty_claimed' then (p_payload->>'qty_claimed')::integer else v_claim.qty_claimed end,
        claim_type=coalesce(v_claim_type,v_claim.claim_type),
        compensation_amount=case when p_payload?'compensation_amount' then (p_payload->>'compensation_amount')::numeric else v_claim.compensation_amount end,
        status=v_target_status,
        opened_at=case when p_payload?'opened_at' then (p_payload->>'opened_at')::timestamptz else v_claim.opened_at end,
        resolution_date=case when p_payload?'resolution_date' then nullif(p_payload->>'resolution_date','')::date else v_claim.resolution_date end,
        notes=case when p_payload?'notes' then nullif(btrim(p_payload->>'notes'),'') else v_claim.notes end
    where id=v_claim.id returning * into v_claim;
  end if;
  v_response:=jsonb_build_object(
    'laundry_claim_id',v_claim.id,'claim_number',v_claim.claim_number,
    'status',v_claim.status,'row_version',v_claim.row_version,
    'qty_claimed',v_claim.qty_claimed,'compensation_amount',v_claim.compensation_amount
  );
  return erp._idempotency_complete('save_laundry_claim_v2',p_client_request_id,v_response);
end
$function$;

CREATE OR REPLACE FUNCTION erp.save_laundry_qc_action_v1(p_action text, p_payload jsonb, p_client_request_id uuid, p_expected_version bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_action text:=upper(nullif(btrim(p_action),''));
  v_reason text:=nullif(btrim(p_payload->>'reason'),'');
  v_custody_outcome text:=upper(nullif(btrim(p_payload->>'custody_outcome'),''));
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_actor uuid:=erp.current_app_user_id();
  v_physical_raw text:=nullif(btrim(p_payload->>'physical_at'),'');
  v_physical_at timestamptz;
  v_batch_id uuid:=nullif(p_payload->>'distribution_batch_id','')::uuid;
  v_group_id uuid:=nullif(p_payload->>'cutting_group_id','')::uuid;
  v_delivery_id uuid:=nullif(p_payload->>'delivery_id','')::uuid;
  v_receipt_id uuid;
  v_failed_wash_attempt_id uuid;
  v_return_wip_event_id uuid;
  v_qc_id uuid:=nullif(p_payload->>'qc_inspection_id','')::uuid;
  v_vendor_id uuid:=nullif(p_payload->>'vendor_id','')::uuid;
  v_process_id uuid:=nullif(p_payload->>'wash_process_id','')::uuid;
  v_location_id uuid:=nullif(p_payload->>'destination_location_id','')::uuid;
  v_target_color text:=nullif(btrim(p_payload->>'target_dyeing_color'),'');
  v_lines jsonb:=p_payload->'lines';
  v_line jsonb;
  v_rate numeric(18,2);
  v_rate_count integer;
  v_group_count integer;
  v_total bigint;
  v_good bigint;
  v_bs bigint;
  v_available bigint;
  v_available_at_physical_time bigint;
  v_ready_after_qc bigint;
  v_delivery_line_id uuid;
  v_receipt_line_id uuid;
  v_number text;
  v_nested jsonb;
  v_group erp.cutting_groups%rowtype;
  v_po erp.production_orders%rowtype;
  v_delivery erp.laundry_deliveries%rowtype;
  v_receipt erp.laundry_receipts%rowtype;
  v_qc erp.qc_inspections%rowtype;
begin
  if p_client_request_id is null then raise exception 'client_request_id UUID is required'; end if;
  if v_actor is null then raise exception 'Active ERP app user is required'; end if;
  if v_action not in(
    'POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH','REVERSE_DELIVERY',
    'REVERSE_RECEIPT','POST_FINAL_SKU','REVERSE_FINAL_SKU'
  ) then raise exception 'Unsupported CP6 Laundry/QC action %',coalesce(v_action,'NULL'); end if;

  -- Physical time is operator intent. Validate it before the generic closed-payload
  -- gate so missing, timezone-less, and calendar-invalid values all fail with one
  -- actionable domain message instead of a helper or native cast error.
  if v_action in('POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH','POST_FINAL_SKU') then
    if jsonb_typeof(p_payload->'physical_at') is distinct from 'string'
       or v_physical_raw is null
       or v_physical_raw !~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}(:\d{2})?)$' then
      raise exception 'An explicit timezone-qualified physical_at is required; server time is never a transactional default';
    end if;
    begin
      v_physical_at:=v_physical_raw::timestamptz;
    exception
      when data_exception then
        raise exception 'An explicit timezone-qualified physical_at is required; server time is never a transactional default';
    end;
  end if;

  -- Do not let JSON coercion reinterpret a physical count or silently ignore
  -- a misspelled field.  Every connected writer uses one closed, canonical
  -- payload shape before idempotency or business mutation begins.
  if v_action='POST_DELIVERY' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,
      array['distribution_batch_id','vendor_id','wash_process_id','target_dyeing_color',
        'physical_at','reason','lines'],
      array['distribution_batch_id','vendor_id','wash_process_id','target_dyeing_color',
        'physical_at','reason','notes','lines'],
      'CP6 POST_DELIVERY payload'
    );
    if jsonb_typeof(p_payload->'distribution_batch_id')<>'string'
       or jsonb_typeof(p_payload->'vendor_id')<>'string'
       or jsonb_typeof(p_payload->'wash_process_id')<>'string'
       or jsonb_typeof(p_payload->'target_dyeing_color')<>'string'
       or jsonb_typeof(p_payload->'physical_at')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string'
       or jsonb_typeof(p_payload->'lines')<>'array'
       or(p_payload ? 'notes' and jsonb_typeof(p_payload->'notes') not in('string','null')) then
      raise exception 'CP6 POST_DELIVERY payload has invalid field types';
    end if;
    for v_line in select value from jsonb_array_elements(v_lines) loop
      perform erp._cp3_assert_closed_json_object(
        v_line,array['size_id','qty_sent_pcs'],array['size_id','qty_sent_pcs'],
        'CP6 POST_DELIVERY line'
      );
      if jsonb_typeof(v_line->'size_id')<>'string'
         or jsonb_typeof(v_line->'qty_sent_pcs')<>'number'
         or(v_line->>'qty_sent_pcs')!~'^(0|[1-9][0-9]*)$' then
        raise exception 'CP6 POST_DELIVERY line has invalid field types';
      end if;
    end loop;
  elsif v_action='POST_RECEIPT' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,array['delivery_id','wash_process_id','physical_at','reason','lines'],
      array['delivery_id','wash_process_id','physical_at','reason','lines'],
      'CP6 POST_RECEIPT payload'
    );
    if jsonb_typeof(p_payload->'delivery_id')<>'string'
       or jsonb_typeof(p_payload->'wash_process_id')<>'string'
       or jsonb_typeof(p_payload->'physical_at')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string'
       or jsonb_typeof(p_payload->'lines')<>'array' then
      raise exception 'CP6 POST_RECEIPT payload has invalid field types';
    end if;
    for v_line in select value from jsonb_array_elements(v_lines) loop
      perform erp._cp3_assert_closed_json_object(
        v_line,
        array['delivery_batch_size_line_id','qty_good_received','qty_bs_laundry'],
        array['delivery_batch_size_line_id','qty_good_received','qty_bs_laundry','bs_product_id'],
        'CP6 POST_RECEIPT line'
      );
      if not(v_line ? 'bs_product_id')
         or jsonb_typeof(v_line->'delivery_batch_size_line_id')<>'string'
         or jsonb_typeof(v_line->'qty_good_received')<>'number'
         or(v_line->>'qty_good_received')!~'^(0|[1-9][0-9]*)$'
         or jsonb_typeof(v_line->'qty_bs_laundry')<>'number'
         or(v_line->>'qty_bs_laundry')!~'^(0|[1-9][0-9]*)$'
         or jsonb_typeof(v_line->'bs_product_id') not in('string','null') then
        raise exception 'CP6 POST_RECEIPT line has invalid field types';
      end if;
    end loop;
  elsif v_action='POST_FAILED_WASH' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,
      array['delivery_id','wash_process_id','custody_outcome','physical_at','reason','lines'],
      array['delivery_id','wash_process_id','custody_outcome','physical_at','reason','lines'],
      'CP6 POST_FAILED_WASH payload'
    );
    if jsonb_typeof(p_payload->'delivery_id')<>'string'
       or jsonb_typeof(p_payload->'wash_process_id')<>'string'
       or jsonb_typeof(p_payload->'custody_outcome')<>'string'
       or v_custody_outcome not in('RETRY_AT_VENDOR','RETURN_UNPROCESSED')
       or jsonb_typeof(p_payload->'physical_at')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string'
       or jsonb_typeof(p_payload->'lines')<>'array' then
      raise exception 'CP6 POST_FAILED_WASH payload has invalid field types';
    end if;
    for v_line in select value from jsonb_array_elements(v_lines) loop
      perform erp._cp3_assert_closed_json_object(
        v_line,array['delivery_batch_size_line_id','qty_attempted_pcs'],
        array['delivery_batch_size_line_id','qty_attempted_pcs'],
        'CP6 POST_FAILED_WASH line'
      );
      if jsonb_typeof(v_line->'delivery_batch_size_line_id')<>'string'
         or jsonb_typeof(v_line->'qty_attempted_pcs')<>'number'
         or(v_line->>'qty_attempted_pcs')!~'^[1-9][0-9]*$' then
        raise exception 'CP6 POST_FAILED_WASH line has invalid field types';
      end if;
    end loop;
  elsif v_action='POST_FINAL_SKU' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,
      array['cutting_group_id','destination_location_id','physical_at','reason',
        'good_qty_pcs','completion_mode','lines'],
      array['cutting_group_id','destination_location_id','physical_at','reason',
        'good_qty_pcs','completion_mode','lines'],
      'CP6 POST_FINAL_SKU payload'
    );
    if jsonb_typeof(p_payload->'cutting_group_id')<>'string'
       or jsonb_typeof(p_payload->'destination_location_id')<>'string'
       or jsonb_typeof(p_payload->'physical_at')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string'
       or jsonb_typeof(p_payload->'good_qty_pcs')<>'number'
       or(p_payload->>'good_qty_pcs')!~'^(0|[1-9][0-9]*)$'
       or jsonb_typeof(p_payload->'completion_mode')<>'string'
       or(p_payload->>'completion_mode') not in('ALL_READY','PARTIAL_SELECTION')
       or jsonb_typeof(p_payload->'lines')<>'array' then
      raise exception 'CP6 POST_FINAL_SKU payload has invalid field types';
    end if;
    for v_line in select value from jsonb_array_elements(v_lines) loop
      perform erp._cp3_assert_closed_json_object(
        v_line,
        array['final_product_id','qty_good_pcs','qty_bs_pcs',
          'source_laundry_receipt_line_id','source_laundry_receipt_batch_size_line_id'],
        array['final_product_id','qty_good_pcs','qty_bs_pcs',
          'source_laundry_receipt_line_id','source_laundry_receipt_batch_size_line_id','notes'],
        'CP6 POST_FINAL_SKU line'
      );
      if jsonb_typeof(v_line->'final_product_id')<>'string'
         or jsonb_typeof(v_line->'qty_good_pcs')<>'number'
         or(v_line->>'qty_good_pcs')!~'^(0|[1-9][0-9]*)$'
         or jsonb_typeof(v_line->'qty_bs_pcs')<>'number'
         or(v_line->>'qty_bs_pcs')!~'^(0|[1-9][0-9]*)$'
         or jsonb_typeof(v_line->'source_laundry_receipt_line_id')<>'string'
         or jsonb_typeof(v_line->'source_laundry_receipt_batch_size_line_id')<>'string'
         or(v_line ? 'notes' and jsonb_typeof(v_line->'notes') not in('string','null')) then
        raise exception 'CP6 POST_FINAL_SKU line has invalid field types';
      end if;
    end loop;
  elsif v_action='REVERSE_DELIVERY' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,array['delivery_id','reason'],array['delivery_id','reason'],
      'CP6 REVERSE_DELIVERY payload'
    );
    if jsonb_typeof(p_payload->'delivery_id')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string' then
      raise exception 'CP6 REVERSE_DELIVERY payload has invalid field types';
    end if;
  elsif v_action='REVERSE_RECEIPT' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,array['receipt_id','reason'],array['receipt_id','reason'],
      'CP6 REVERSE_RECEIPT payload'
    );
    if jsonb_typeof(p_payload->'receipt_id')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string' then
      raise exception 'CP6 REVERSE_RECEIPT payload has invalid field types';
    end if;
  else
    perform erp._cp3_assert_closed_json_object(
      p_payload,array['qc_inspection_id','reason'],array['qc_inspection_id','reason'],
      'CP6 REVERSE_FINAL_SKU payload'
    );
    if jsonb_typeof(p_payload->'qc_inspection_id')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string' then
      raise exception 'CP6 REVERSE_FINAL_SKU payload has invalid field types';
    end if;
  end if;
  if v_reason is null or length(v_reason)<4 then raise exception 'A clear reason of at least 4 characters is required'; end if;
  if v_physical_at>clock_timestamp()+interval '5 minutes' then
    raise exception 'Physical time cannot be more than five minutes in the future';
  end if;

  if v_action in('POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH') then
    perform erp.require_permission('production.laundry.post');
    if v_action='POST_DELIVERY' then perform erp.require_permission('production.laundry.create'); end if;
  elsif v_action in('REVERSE_DELIVERY','REVERSE_RECEIPT') then
    perform erp.require_permission('production.laundry.reverse');
  elsif v_action='POST_FINAL_SKU' then
    perform erp.require_permission('production.final_sku.post');
  else
    perform erp.require_permission('production.final_sku.reverse');
  end if;

  v_hash:=erp._request_hash(jsonb_build_object(
    'action',v_action,'payload',p_payload,'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin(
    'cp6_laundry_qc_action_v1:'||lower(v_action),p_client_request_id,v_hash
  );
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_action in('REVERSE_DELIVERY','REVERSE_RECEIPT','REVERSE_FINAL_SKU') then
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      case when v_action in('REVERSE_DELIVERY','REVERSE_RECEIPT')
        then 'production.laundry.reverse' else 'production.final_sku.reverse' end,
      p_client_request_id,p_payload
    );
  end if;

  if v_action='POST_DELIVERY' then
    if p_expected_version is null then raise exception 'Potongan expected_version is required'; end if;
    if v_batch_id is null or v_vendor_id is null or v_process_id is null
       or v_target_color is null then
      raise exception 'Distribution batch, vendor, wash process, and target color are required';
    end if;
    if jsonb_typeof(v_lines)<>'array' or jsonb_array_length(v_lines)=0 then
      raise exception 'Laundry delivery requires positive size lines';
    end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer)
      where x.size_id is null or coalesce(x.qty_sent_pcs,0)<=0
    ) or exists(
      select 1 from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer)
      group by x.size_id having count(*)>1
    ) then raise exception 'Laundry delivery size lines must be unique and positive'; end if;

    -- Resolve the immutable Potongan key without retaining a row lock, then
    -- take the shared CP6 fence before every business row.  The locked re-read
    -- below rejects a source that changed while this transaction waited; it
    -- must never continue under a fence for the wrong Potongan.
    select p.cutting_group_id into v_group_id
    from erp.cutting_distribution_batches b
    join erp.cutting_pickups p on p.id=b.pickup_id and p.status='POSTED'
    where b.id=v_batch_id;
    if v_group_id is null then raise exception 'Authoritative POSTED distribution batch was not found'; end if;
    -- Every CP6 mutation that can change Laundry/QC progress shares this
    -- transaction fence.  Cross-document actions on one Potongan therefore
    -- have one serial order even when their individual row locks do not meet.
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    perform 1
    from erp.cutting_distribution_batches b
    join erp.cutting_pickups p on p.id=b.pickup_id
    where b.id=v_batch_id and p.status='POSTED'
      and p.cutting_group_id=v_group_id
    for update of b,p;
    if not found then
      raise exception 'Authoritative POSTED distribution batch changed while waiting for the Potongan fence; refetch before retrying';
    end if;
    select * into v_group from erp.cutting_groups where id=v_group_id for update;
    if v_group.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_group.row_version;
    end if;
    select * into v_po from erp.production_orders where id=v_group.po_id for update;
    if v_po.status in('FINISHED','CANCELLED') then
      raise exception 'PO status % cannot receive a new Laundry delivery',v_po.status;
    end if;
    if v_physical_at<v_group.picked_up_at then
      raise exception 'Laundry send time cannot be earlier than the physical contractor pickup';
    end if;
    perform 1 from erp.laundry_vendors v
    where v.id=v_vendor_id and v.is_active for share;
    if not found then
      raise exception 'An active authoritative Laundry vendor is required';
    end if;
    perform 1 from erp.wash_processes w
    where w.id=v_process_id and w.is_active for share;
    if not found then
      raise exception 'An active authoritative wash process is required';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('LRATE:'||v_vendor_id::text||':'||v_process_id::text,0));
    select count(*)::integer,min(r.rate_per_pcs) into v_rate_count,v_rate
    from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at);
    if v_rate_count<>1 then
      raise exception 'Exactly one authoritative Laundry rate must be effective for this vendor/process/time; found %',v_rate_count;
    end if;
    perform 1 from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at)
    order by r.id for share;

    if exists(
      select 1
      from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer)
      left join lateral(
        select coalesce(sum(a.qty_pcs),0)::bigint qty
        from erp.cutting_distribution_allocations a
        join erp.cutting_roll_yields y on y.id=a.cutting_roll_yield_id
        join erp.cutting_group_size_slots s on s.id=y.size_slot_id
        where a.batch_id=v_batch_id and s.size_id=x.size_id
      ) cap on true
      left join lateral(
        select coalesce(sum(sx.qty_sent_pcs),0)::bigint qty
        from erp.laundry_delivery_batch_size_lines sx
        join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
        join erp.laundry_deliveries d on d.id=dl.delivery_id
        where sx.distribution_batch_id=v_batch_id and sx.size_id=x.size_id
          and d.status not in('DRAFT','REVERSED')
      ) used on true
      where x.qty_sent_pcs>cap.qty-used.qty
    ) then raise exception 'Requested Laundry size quantity exceeds its remaining distribution-batch capacity'; end if;

    if exists(
      select 1
      from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer)
      left join lateral(
        select coalesce(sum(a.qty_pcs),0)::bigint qty
        from erp.cutting_distribution_allocations a
        join erp.cutting_roll_yields y on y.id=a.cutting_roll_yield_id
        join erp.cutting_group_size_slots s on s.id=y.size_slot_id
        where a.batch_id=v_batch_id and s.size_id=x.size_id
      ) cap on true
      left join lateral(
        select coalesce(sum(sx.qty_sent_pcs),0)::bigint qty
        from erp.laundry_delivery_batch_size_lines sx
        join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
        join erp.laundry_deliveries d on d.id=dl.delivery_id
        where sx.distribution_batch_id=v_batch_id and sx.size_id=x.size_id
          and d.status<>'DRAFT' and d.physical_at<=v_physical_at
      ) dispatched_at_prefix on true
      left join lateral(
        select coalesce(sum(sx.qty_sent_pcs),0)::bigint qty
        from erp.laundry_delivery_batch_size_lines sx
        join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
        join erp.wip_stage_events src
          on src.source_type='LAUNDRY_DELIVERY_LINE' and src.source_id=dl.id
        join erp.wip_stage_events rv
          on rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
         and rv.source_id=src.id and rv.physical_at<=v_physical_at
        where sx.distribution_batch_id=v_batch_id and sx.size_id=x.size_id
      ) returned_at_prefix on true
      where x.qty_sent_pcs>cap.qty-dispatched_at_prefix.qty+returned_at_prefix.qty
    ) then
      raise exception 'Laundry redispatch time precedes sufficient linked physical return for this distribution batch/size';
    end if;

    select sum(x.qty_sent_pcs)::bigint into v_total
    from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer);
    select coalesce(w.unsent_ready_qty_pcs,0)::bigint into v_available
    from erp.v_wip_control_status_v1 w where w.cutting_group_id=v_group.id;
    if v_total>coalesce(v_available,0) then
      raise exception 'Laundry send exceeds sewn-and-unsent capacity. Ready %, requested %',coalesce(v_available,0),v_total;
    end if;
    select greatest(
      coalesce((
        select sum(e.qty_signed) from erp.sewing_terminal_events e
        where e.cutting_group_id=v_group.id and e.physical_at<=v_physical_at
      ),0)
      -coalesce((
        select sum(dl.qty_sent_pcs)
        from erp.laundry_delivery_lines dl
        join erp.laundry_deliveries d on d.id=dl.delivery_id
        where dl.cutting_group_id=v_group.id
          and d.status<>'DRAFT' and d.physical_at<=v_physical_at
      ),0)
      +coalesce((
        select sum(rv.qty_pcs)
        from erp.wip_stage_events rv
        join erp.wip_stage_events src
          on src.id=rv.source_id and src.source_type='LAUNDRY_DELIVERY_LINE'
        where rv.cutting_group_id=v_group.id
          and rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
          and rv.physical_at<=v_physical_at
      ),0)
      -coalesce((
        select sum(i.qty_good_pcs+i.qty_bs_pcs)
        from erp.qc_inspection_items i
        join erp.qc_inspections q on q.id=i.inspection_id
        where i.cutting_group_id=v_group.id
          and i.source_laundry_receipt_line_id is null
          and q.status='POSTED' and q.physical_at<=v_physical_at
      ),0),0
    )::bigint into v_available_at_physical_time;
    if v_total>v_available_at_physical_time then
      raise exception 'Laundry send time predates sufficient authoritative sewing output. Ready at physical time %, requested %',
        v_available_at_physical_time,v_total;
    end if;

    perform erp.assert_cp6_dispatch_timeline_v2620b(
      v_batch_id,v_group.id,v_physical_at,v_lines
    );
    v_delivery_id:=gen_random_uuid();
    v_delivery_line_id:=gen_random_uuid();
    -- The UUID is already the immutable document identity. Keep all 128 bits
    -- in the unique human key so two valid postings can never be rejected by
    -- the former 40-bit display prefix collision surface.
    v_number:='LDR-'||to_char((v_physical_at AT TIME ZONE 'Asia/Jakarta'),'YYMMDD')||'-'
      ||upper(replace(v_delivery_id::text,'-',''));
    insert into erp.laundry_deliveries(
      id,delivery_number,po_id,vendor_id,target_dyeing_color,target_wash_process_id,
      special_instruction,physical_at,status,created_by
    ) values(
      v_delivery_id,v_number,v_group.po_id,v_vendor_id,v_target_color,v_process_id,
      nullif(btrim(p_payload->>'notes'),''),v_physical_at,'DRAFT',v_actor
    );
    insert into erp.laundry_delivery_lines(
      id,delivery_id,cutting_group_id,qty_sent_pcs,estimated_rate_snapshot,
      estimated_cost_status,notes
    ) values(
      v_delivery_line_id,v_delivery_id,v_group.id,v_total,v_rate,'ESTIMATED',
      'CP6 immutable distribution batch/size handoff: '||v_reason
    );
    insert into erp.laundry_delivery_batch_size_lines(
      delivery_line_id,distribution_batch_id,size_id,qty_sent_pcs,created_by
    ) select v_delivery_line_id,v_batch_id,x.size_id,x.qty_sent_pcs,v_actor
      from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer);
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      'production.laundry.post',p_client_request_id,p_payload
    );
    if exists(
      select 1 from erp.schema_migrations where version='v2.6.20d'
    ) then
      if to_regprocedure('erp.allocate_laundry_redispatch_participants_v2620e(uuid)') is null then
        raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20d redispatch allocator is missing';
      end if;
      perform erp.allocate_laundry_redispatch_participants_v2620e(v_delivery_line_id);
    end if;
    perform erp.post_laundry_delivery(v_delivery_id);
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    if not found then raise exception 'CP6 execution context cleanup failed'; end if;
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery_id;
    select * into v_group from erp.cutting_groups where id=v_group.id;
    v_response:=jsonb_build_object(
      'action',v_action,'delivery_id',v_delivery.id,'delivery_number',v_delivery.delivery_number,
      'status',v_delivery.status,'row_version',v_delivery.row_version,
      'cutting_group_id',v_group.id,'cutting_group_row_version',v_group.row_version,
      'qty_sent_pcs',v_total,'rate_per_pcs',v_rate,
      'estimated_cost',round(v_total*v_rate,2),
      'stock_effect','SEWING_TO_LAUNDRY','hpp_effect','LAUNDRY_ACCRUAL_REBUILT'
    );

  elsif v_action='POST_RECEIPT' then
    if p_expected_version is null or v_delivery_id is null then
      raise exception 'Delivery and expected_version are required';
    end if;
    if v_process_id is null then raise exception 'Actual wash process is required'; end if;
    if jsonb_typeof(v_lines)<>'array' or jsonb_array_length(v_lines)=0 then
      raise exception 'Laundry receipt requires positive batch/size return lines';
    end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) where x.delivery_batch_size_line_id is null
        or coalesce(x.qty_good_received,0)<0 or coalesce(x.qty_bs_laundry,0)<0
        or coalesce(x.qty_good_received,0)+coalesce(x.qty_bs_laundry,0)<=0
        or(coalesce(x.qty_bs_laundry,0)>0 and x.bs_product_id is null)
        or(coalesce(x.qty_bs_laundry,0)=0 and x.bs_product_id is not null)
    ) or exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) group by x.delivery_batch_size_line_id having count(*)>1
    ) then raise exception 'Receipt size lines must be unique, positive, and bind every Laundry BS to a product'; end if;

    select min(dl.cutting_group_id::text)::uuid,count(*)::integer
      into v_group_id,v_group_count
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected CP6 receipt requires one authoritative delivery line';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery_id for update;
    if v_delivery.id is null or v_delivery.status not in('SENT','PARTIAL_RETURN') then
      raise exception 'Laundry receipt requires an active SENT/PARTIAL_RETURN delivery';
    end if;
    if v_delivery.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_delivery.row_version;
    end if;
    if v_physical_at<v_delivery.physical_at then
      raise exception 'Laundry return time cannot be earlier than the send time';
    end if;
    if exists(select 1 from erp.laundry_claims c where c.delivery_id=v_delivery.id
      and c.claim_type in('STUCK','MISSING') and c.status<>'REJECTED') then
      raise exception 'Reverse/reject the active STUCK/MISSING claim before posting a late physical return';
    end if;
    perform 1 from erp.wash_processes w
    where w.id=v_process_id and w.is_active for share;
    if not found then
      raise exception 'An active authoritative actual wash process is required';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('LRATE:'||v_delivery.vendor_id::text||':'||v_process_id::text,0));
    select count(*)::integer,min(r.rate_per_pcs) into v_rate_count,v_rate
    from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at);
    if v_rate_count<>1 then
      raise exception 'Exactly one authoritative actual Laundry rate must be effective for this vendor/process/time; found %',v_rate_count;
    end if;
    perform 1 from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at)
    order by r.id for share;
    select min(dl.id::text)::uuid into v_delivery_line_id
    from erp.laundry_delivery_lines dl
    where dl.delivery_id=v_delivery.id and dl.cutting_group_id=v_group_id;
    if v_delivery_line_id is null or(
      select count(*) from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery.id
    )<>1 then raise exception 'Connected CP6 receipt requires one authoritative delivery line'; end if;
    perform 1
    from erp.laundry_delivery_batch_size_lines sx
    join jsonb_to_recordset(v_lines) x(
      delivery_batch_size_line_id uuid,qty_good_received integer,
      qty_bs_laundry integer,bs_product_id uuid
    ) on x.delivery_batch_size_line_id=sx.id
    order by sx.id for update of sx;
    if(
      select count(*) from erp.laundry_delivery_batch_size_lines sx
      join jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) on x.delivery_batch_size_line_id=sx.id
      where sx.delivery_line_id=v_delivery_line_id
    )<>jsonb_array_length(v_lines) then
      raise exception 'A receipt source does not belong to this CP6 delivery';
    end if;
    if exists(
      select 1
      from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      )
      join erp.laundry_delivery_batch_size_lines sx on sx.id=x.delivery_batch_size_line_id
      where coalesce(x.qty_good_received,0)+coalesce(x.qty_bs_laundry,0)>
        sx.qty_sent_pcs-coalesce((
          select sum(rx.qty_good_received+rx.qty_bs_laundry)
          from erp.laundry_receipt_batch_size_lines rx
          join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
          join erp.laundry_receipts rh on rh.id=rl.receipt_id
          where rx.delivery_batch_size_line_id=sx.id and rh.status='POSTED'
        ),0)
    ) then raise exception 'Laundry receipt exceeds remaining quantity for an exact batch/size source'; end if;

    select sum(coalesce(x.qty_good_received,0))::bigint,
           sum(coalesce(x.qty_bs_laundry,0))::bigint
      into v_good,v_bs
    from jsonb_to_recordset(v_lines) x(
      delivery_batch_size_line_id uuid,qty_good_received integer,
      qty_bs_laundry integer,bs_product_id uuid
    );
    v_total:=v_good+v_bs;
    v_receipt_id:=gen_random_uuid();
    v_receipt_line_id:=gen_random_uuid();
    v_number:='LRC-'||to_char((v_physical_at AT TIME ZONE 'Asia/Jakarta'),'YYMMDD')||'-'
      ||upper(replace(v_receipt_id::text,'-',''));
    insert into erp.laundry_receipts(
      id,receipt_number,delivery_id,physical_at,status,created_by
    ) values(v_receipt_id,v_number,v_delivery.id,v_physical_at,'DRAFT',v_actor);
    insert into erp.laundry_receipt_lines(
      id,receipt_id,delivery_line_id,actual_wash_process_id,
      qty_good_received,qty_bs_laundry,qty_stuck,qty_missing,
      actual_rate_snapshot,actual_cost_status,actual_cost,notes
    ) values(
      v_receipt_line_id,v_receipt_id,v_delivery_line_id,v_process_id,
      -- A physical receipt proves the process/rate snapshot, not the vendor
      -- invoice.  Keep the amount ESTIMATED so the delivery accrual remains a
      -- liability until post_vendor_invoice atomically replaces it with AP.
      -- Marking this FINAL here would release accrual early and leave negative
      -- WIP after the same cost moves into FG/HPP.
      v_good,v_bs,0,0,v_rate,'ESTIMATED',round(v_total*v_rate,2),
      'CP6 immutable physical batch/size return: '||v_reason
    );
    insert into erp.laundry_receipt_batch_size_lines(
      receipt_line_id,delivery_batch_size_line_id,size_id,
      qty_good_received,qty_bs_laundry,bs_product_id,created_by
    ) select v_receipt_line_id,x.delivery_batch_size_line_id,sx.size_id,
        coalesce(x.qty_good_received,0),coalesce(x.qty_bs_laundry,0),x.bs_product_id,v_actor
      from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) join erp.laundry_delivery_batch_size_lines sx on sx.id=x.delivery_batch_size_line_id;
    insert into erp.laundry_receipt_bs_product_allocations(
      receipt_line_id,product_id,qty_bs,notes,created_by
    ) select v_receipt_line_id,x.bs_product_id,sum(x.qty_bs_laundry)::integer,
        'CP6 immutable Laundry-BS product/size declaration',v_actor
      from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) where x.qty_bs_laundry>0 group by x.bs_product_id;
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      'production.laundry.post',p_client_request_id,p_payload
    );
    perform erp.post_laundry_receipt(v_receipt_id);
    -- The predecessor function records every physical return as LAUNDRY → QC.
    -- Laundry BS is terminal at this boundary, so append the balancing
    -- QC → ON_HOLD event instead of rewriting/deleting the predecessor event.
    insert into erp.wip_stage_events(
      po_id,cutting_group_id,stage_from,stage_to,qty_pcs,
      source_type,source_id,physical_at,created_by,notes
    )
    select v_delivery.po_id,dl.cutting_group_id,'QC','ON_HOLD',x.qty_bs_laundry,
      'CP6_LAUNDRY_BS_SIZE_LINE',x.id,v_physical_at,v_actor,
      'Laundry BS is terminal and must never become QC-ready'
    from erp.laundry_receipt_batch_size_lines x
    join erp.laundry_receipt_lines rl on rl.id=x.receipt_line_id
    join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
    where x.receipt_line_id=v_receipt_line_id and x.qty_bs_laundry>0;
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    if not found then raise exception 'CP6 execution context cleanup failed'; end if;
    select * into v_receipt from erp.laundry_receipts where id=v_receipt_id;
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery.id;
    v_response:=jsonb_build_object(
      'action',v_action,'receipt_id',v_receipt.id,'receipt_number',v_receipt.receipt_number,
      'receipt_status',v_receipt.status,'receipt_row_version',v_receipt.row_version,
      'delivery_id',v_delivery.id,'delivery_status',v_delivery.status,
      'delivery_row_version',v_delivery.row_version,'good_qty_pcs',v_good,'bs_qty_pcs',v_bs,
      'rate_per_pcs',v_rate,'actual_cost',round(v_total*v_rate,2),
      'cost_status','ESTIMATED_UNBILLED','accrual_effect','PRESERVED_UNTIL_VENDOR_INVOICE',
      'stock_effect','LAUNDRY_GOOD_TO_QC_AND_BS_TO_ON_HOLD',
      'hpp_effect','ACTUAL_LAUNDRY_COST_REBUILT'
    );

  elsif v_action='POST_FAILED_WASH' then
    if p_expected_version is null or v_delivery_id is null or v_process_id is null then
      raise exception 'Delivery, failed process, and expected_version are required';
    end if;
    if jsonb_typeof(v_lines)<>'array' or jsonb_array_length(v_lines)=0 then
      raise exception 'Paid failed wash requires positive attempted batch/size lines';
    end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_attempted_pcs integer
      ) where x.delivery_batch_size_line_id is null or coalesce(x.qty_attempted_pcs,0)<=0
    ) or exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_attempted_pcs integer
      ) group by x.delivery_batch_size_line_id having count(*)>1
    ) then
      raise exception 'Failed-wash size lines must be unique positive integer pieces';
    end if;

    select min(dl.cutting_group_id::text)::uuid,count(*)::integer
      into v_group_id,v_group_count
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected failed-wash action requires one authoritative delivery line';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_delivery from erp.laundry_deliveries
    where id=v_delivery_id for update;
    if v_delivery.id is null or v_delivery.status not in('SENT','PARTIAL_RETURN') then
      raise exception 'Paid failed wash requires an active SENT/PARTIAL_RETURN delivery';
    end if;
    if v_delivery.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_delivery.row_version;
    end if;
    if v_physical_at<v_delivery.physical_at
       or exists(select 1 from erp.laundry_receipts r
         where r.delivery_id=v_delivery.id and r.status='POSTED'
           and r.physical_at>v_physical_at) then
      raise exception 'Failed-wash physical time cannot precede the send or later posted Laundry history';
    end if;
    if exists(select 1 from erp.laundry_claims c
      where c.delivery_id=v_delivery.id and c.status<>'REJECTED') then
      raise exception 'Resolve/reject active Laundry claims before recording a failed-wash service attempt';
    end if;
    perform 1 from erp.wash_processes w
    where w.id=v_process_id and w.is_active for share;
    if not found then raise exception 'An active authoritative failed wash process is required'; end if;
    perform pg_advisory_xact_lock(hashtextextended(
      'LRATE:'||v_delivery.vendor_id::text||':'||v_process_id::text,0
    ));
    select count(*)::integer,min(r.rate_per_pcs) into v_rate_count,v_rate
    from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at);
    if v_rate_count<>1 then
      raise exception 'Exactly one authoritative failed-wash rate must be effective for this vendor/process/time; found %',v_rate_count;
    end if;
    perform 1 from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at)
    order by r.id for share;
    select min(dl.id::text)::uuid into v_delivery_line_id
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery.id;
    perform 1
    from erp.laundry_delivery_batch_size_lines s
    join jsonb_to_recordset(v_lines) x(
      delivery_batch_size_line_id uuid,qty_attempted_pcs integer
    ) on x.delivery_batch_size_line_id=s.id
    order by s.id for update of s;
    if (select count(*)
        from erp.laundry_delivery_batch_size_lines s
        join jsonb_to_recordset(v_lines) x(
          delivery_batch_size_line_id uuid,qty_attempted_pcs integer
        ) on x.delivery_batch_size_line_id=s.id
        where s.delivery_line_id=v_delivery_line_id)<>jsonb_array_length(v_lines)
       or exists(
         select 1
         from jsonb_to_recordset(v_lines) x(
           delivery_batch_size_line_id uuid,qty_attempted_pcs integer
         )
         join erp.laundry_delivery_batch_size_lines s
           on s.id=x.delivery_batch_size_line_id
         where x.qty_attempted_pcs>s.qty_sent_pcs-coalesce((
           select sum(rx.qty_good_received+rx.qty_bs_laundry)
           from erp.laundry_receipt_batch_size_lines rx
           join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
           join erp.laundry_receipts rh on rh.id=rl.receipt_id
           where rx.delivery_batch_size_line_id=s.id and rh.status='POSTED'
         ),0)
       ) then
      raise exception 'Failed-wash attempted quantity exceeds the exact pieces still in Laundry custody';
    end if;
    select sum(x.qty_attempted_pcs)::bigint into v_total
    from jsonb_to_recordset(v_lines) x(
      delivery_batch_size_line_id uuid,qty_attempted_pcs integer
    );
    if v_custody_outcome='RETURN_UNPROCESSED' and(
      v_delivery.status<>'SENT'
      or exists(
        select 1 from erp.laundry_receipt_lines rl
        join erp.laundry_receipts rh on rh.id=rl.receipt_id
        left join erp.laundry_failed_wash_attempts a on a.receipt_line_id=rl.id
        where rh.delivery_id=v_delivery.id and rh.status='POSTED'
          and a.id is null and rl.qty_good_received+rl.qty_bs_laundry>0
      )
      or jsonb_array_length(v_lines)<>(
        select count(*) from erp.laundry_delivery_batch_size_lines s
        where s.delivery_line_id=v_delivery_line_id
      )
      or exists(
        select 1 from erp.laundry_delivery_batch_size_lines s
        left join jsonb_to_recordset(v_lines) x(
          delivery_batch_size_line_id uuid,qty_attempted_pcs integer
        ) on x.delivery_batch_size_line_id=s.id
        where s.delivery_line_id=v_delivery_line_id
          and x.qty_attempted_pcs is distinct from s.qty_sent_pcs
      )
    ) then
      raise exception 'Return-unprocessed is deliberately all-or-nothing: every exact sent size must return before redispatch';
    end if;

    v_receipt_id:=gen_random_uuid();
    v_receipt_line_id:=gen_random_uuid();
    v_failed_wash_attempt_id:=gen_random_uuid();
    v_number:='LFW-'||to_char((v_physical_at AT TIME ZONE 'Asia/Jakarta'),'YYMMDD')||'-'
      ||upper(replace(v_receipt_id::text,'-',''));
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      'production.laundry.post',p_client_request_id,p_payload
    );
    insert into erp.laundry_receipts(
      id,receipt_number,delivery_id,physical_at,status,created_by
    ) values(v_receipt_id,v_number,v_delivery.id,v_physical_at,'DRAFT',v_actor);
    insert into erp.laundry_receipt_lines(
      id,receipt_id,delivery_line_id,actual_wash_process_id,
      qty_good_received,qty_bs_laundry,qty_stuck,qty_missing,
      actual_rate_snapshot,actual_cost_status,actual_cost,notes
    ) values(
      v_receipt_line_id,v_receipt_id,v_delivery_line_id,v_process_id,
      0,0,0,0,v_rate,'ESTIMATED',round(v_total*v_rate,2),
      'CP6 paid failed-wash service only; no physical Good/BS receipt: '||v_reason
    );
    insert into erp.laundry_failed_wash_attempts(
      id,receipt_id,receipt_line_id,delivery_id,custody_outcome,
      qty_attempted_pcs,reason,created_by
    ) values(
      v_failed_wash_attempt_id,v_receipt_id,v_receipt_line_id,v_delivery.id,
      v_custody_outcome,v_total,v_reason,v_actor
    );
    insert into erp.laundry_failed_wash_batch_size_lines(
      attempt_id,delivery_batch_size_line_id,size_id,qty_attempted_pcs,created_by
    ) select v_failed_wash_attempt_id,x.delivery_batch_size_line_id,s.size_id,
        x.qty_attempted_pcs,v_actor
      from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_attempted_pcs integer
      ) join erp.laundry_delivery_batch_size_lines s
        on s.id=x.delivery_batch_size_line_id;

    if v_custody_outcome='RETURN_UNPROCESSED' then
      perform set_config('app.physical_at',v_physical_at::text,true);
      update erp.laundry_deliveries
      set status='REVERSED',updated_at=clock_timestamp()
      where id=v_delivery.id;
      select min(rv.id::text)::uuid,count(*)::integer
        into v_return_wip_event_id,v_group_count
      from erp.wip_stage_events rv
      join erp.wip_stage_events src
        on src.id=rv.source_id and src.source_type='LAUNDRY_DELIVERY_LINE'
      join erp.laundry_delivery_lines dl
        on dl.id=src.source_id and dl.delivery_id=v_delivery.id
      where rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL';
      if v_group_count<>1 or v_return_wip_event_id is null then
        raise exception 'Return-unprocessed did not create exactly one linked physical WIP inverse';
      end if;
      update erp.laundry_failed_wash_attempts
      set return_wip_event_id=v_return_wip_event_id
      where id=v_failed_wash_attempt_id;
    else
      update erp.laundry_deliveries set updated_at=clock_timestamp()
      where id=v_delivery.id;
    end if;

    update erp.laundry_receipts
    set status='POSTED',updated_at=clock_timestamp()
    where id=v_receipt_id;

    if v_custody_outcome='RETURN_UNPROCESSED' then
      update erp.cutting_groups g
      set status=case
        when exists(
          select 1 from erp.laundry_receipt_lines rl
          join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
          join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
          join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
          where dl.cutting_group_id=g.id and rl.qty_good_received+rl.qty_bs_laundry>0
        ) then 'RETURNED'
        when exists(
          select 1 from erp.laundry_delivery_lines dl
          join erp.laundry_deliveries d on d.id=dl.delivery_id
          where dl.cutting_group_id=g.id and d.status not in('DRAFT','REVERSED')
        ) then 'LAUNDRY'
        when g.picked_up_at is not null then 'PICKED_UP' else 'CUT' end
      where g.id=v_group_id;
      select * into v_po from erp.production_orders where id=v_delivery.po_id for update;
      if v_po.status not in('ON_HOLD','CANCELLED') then
        update erp.production_orders po set
          status=case
            when exists(select 1 from erp.qc_inspections q
              where q.po_id=po.id and q.status='POSTED') then 'QC'
            when exists(select 1 from erp.laundry_deliveries d
              where d.po_id=po.id and d.status not in('DRAFT','REVERSED')) then 'LAUNDRY'
            when exists(select 1 from erp.cutting_groups g
              where g.po_id=po.id and g.picked_up_at is not null) then 'SEWING'
            else 'CUTTING' end,
          current_stage=case
            when exists(select 1 from erp.qc_inspections q
              where q.po_id=po.id and q.status='POSTED') then 'QC'
            when exists(select 1 from erp.laundry_deliveries d
              where d.po_id=po.id and d.status not in('DRAFT','REVERSED')) then 'LAUNDRY'
            when exists(select 1 from erp.cutting_groups g
              where g.po_id=po.id and g.picked_up_at is not null) then 'SEWING'
            else 'CUTTING' end,
          updated_at=clock_timestamp()
        where po.id=v_po.id;
      end if;
    end if;

    perform erp.sync_laundry_accrual(v_delivery.po_id,(v_physical_at AT TIME ZONE 'Asia/Jakarta')::date);
    if exists(select 1 from erp.fg_lots f where f.po_id=v_delivery.po_id) then
      perform erp.rebuild_po_hpp(
        v_delivery.po_id,'Paid failed-wash service attempt '||v_failed_wash_attempt_id::text
      );
      perform erp.propagate_conversion_hpp_for_po(v_delivery.po_id);
      perform erp.sync_po_hpp_to_gl(v_delivery.po_id,(v_physical_at AT TIME ZONE 'Asia/Jakarta')::date);
    end if;
    insert into erp.audit_logs(
      entity_type,entity_id,action,new_data,changed_by,change_reason
    ) values(
      'laundry_failed_wash_attempts',v_failed_wash_attempt_id,'POST',
      jsonb_build_object(
        'receipt_id',v_receipt_id,'delivery_id',v_delivery.id,
        'custody_outcome',v_custody_outcome,'qty_attempted_pcs',v_total,
        'rate_per_pcs',v_rate,'estimated_cost',round(v_total*v_rate,2),
        'history_deleted',false
      ),v_actor,v_reason
    );
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    if not found then raise exception 'CP6 execution context cleanup failed'; end if;
    select * into v_receipt from erp.laundry_receipts where id=v_receipt_id;
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery.id;
    v_response:=jsonb_build_object(
      'action',v_action,'failed_wash_attempt_id',v_failed_wash_attempt_id,
      'receipt_id',v_receipt.id,'receipt_number',v_receipt.receipt_number,
      'receipt_status',v_receipt.status,'receipt_row_version',v_receipt.row_version,
      'delivery_id',v_delivery.id,'delivery_status',v_delivery.status,
      'delivery_row_version',v_delivery.row_version,
      'custody_outcome',v_custody_outcome,'qty_attempted_pcs',v_total,
      'rate_per_pcs',v_rate,'actual_cost',round(v_total*v_rate,2),
      'cost_status','ESTIMATED_UNBILLED',
      'stock_effect',case when v_custody_outcome='RETRY_AT_VENDOR'
        then 'PHYSICAL_STAYS_AT_LAUNDRY' else 'LAUNDRY_TO_SEWING_RETURN' end,
      'hpp_effect','FAILED_WASH_COST_REBUILT_WITHOUT_GOOD_BS_OR_FG'
    );

  elsif v_action='REVERSE_DELIVERY' then
    if p_expected_version is null or v_delivery_id is null then
      raise exception 'Delivery and expected_version are required';
    end if;
    select min(dl.cutting_group_id::text)::uuid,count(distinct dl.cutting_group_id)::integer
      into v_group_id,v_group_count
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected CP6 delivery reversal requires one Potongan';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery_id for update;
    if v_delivery.id is null then raise exception 'Laundry delivery not found'; end if;
    if v_delivery.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_delivery.row_version;
    end if;
    perform erp.reverse_laundry_delivery(v_delivery.id,v_reason);
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery.id;
    v_response:=jsonb_build_object(
      'action',v_action,'delivery_id',v_delivery.id,'status',v_delivery.status,
      'row_version',v_delivery.row_version,'history_deleted',false,
      'stock_effect','LAUNDRY_TO_SEWING_REVERSED','hpp_effect','LAUNDRY_ACCRUAL_REBUILT'
    );

  elsif v_action='REVERSE_RECEIPT' then
    if p_expected_version is null or nullif(p_payload->>'receipt_id','') is null then
      raise exception 'Receipt and expected_version are required';
    end if;
    v_receipt_id:=(p_payload->>'receipt_id')::uuid;
    select min(dl.cutting_group_id::text)::uuid,count(distinct dl.cutting_group_id)::integer
      into v_group_id,v_group_count
    from erp.laundry_receipt_lines rl
    join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
    where rl.receipt_id=v_receipt_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected CP6 receipt reversal requires one Potongan';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_receipt from erp.laundry_receipts where id=v_receipt_id for update;
    if v_receipt.id is null then raise exception 'Laundry receipt not found'; end if;
    if v_receipt.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_receipt.row_version;
    end if;
    select a.id,a.custody_outcome into v_failed_wash_attempt_id,v_custody_outcome
    from erp.laundry_failed_wash_attempts a where a.receipt_id=v_receipt.id
    for update;
    if v_failed_wash_attempt_id is null then
      perform erp.reverse_laundry_receipt(v_receipt.id,v_reason);
      select * into v_receipt from erp.laundry_receipts where id=v_receipt.id;
      v_response:=jsonb_build_object(
        'action',v_action,'receipt_id',v_receipt.id,'status',v_receipt.status,
        'row_version',v_receipt.row_version,'history_deleted',false,
        'stock_effect','LAUNDRY_RETURN_REVERSED','hpp_effect','LAUNDRY_AND_FG_HPP_REBUILT'
      );
    else
      if v_receipt.status='REVERSED' then
        v_response:=jsonb_build_object(
          'action',v_action,'receipt_id',v_receipt.id,'status',v_receipt.status,
          'row_version',v_receipt.row_version,'history_deleted',false,
          'stock_effect','NO_OP_ALREADY_REVERSED',
          'hpp_effect','NO_OP_ALREADY_REVERSED'
        );
      else
        if v_receipt.status<>'POSTED' then
          raise exception 'Only a POSTED failed-wash service attempt can be reversed';
        end if;
        select * into v_delivery from erp.laundry_deliveries
        where id=v_receipt.delivery_id for update;
        select * into v_po from erp.production_orders
        where id=v_delivery.po_id for update;
        if v_po.status='FINISHED' then
          raise exception 'PO sudah FINISHED. Reopen downstream before reversing failed-wash cost history.';
        end if;
        if exists(
          select 1 from erp.vendor_invoice_items i
          join erp.vendor_invoices h on h.id=i.invoice_id
          where i.receipt_line_id in(
            select l.id from erp.laundry_receipt_lines l where l.receipt_id=v_receipt.id
          ) and h.status<>'REVERSED'
        ) then
          raise exception 'Penerimaan laundry ini sudah masuk invoice vendor. Reverse invoice vendor aktif terlebih dahulu.';
        end if;
        if exists(
          select 1 from erp.qc_inspection_items i
          join erp.qc_inspections h on h.id=i.inspection_id
          where i.source_laundry_receipt_line_id in(
            select l.id from erp.laundry_receipt_lines l where l.receipt_id=v_receipt.id
          ) and h.status<>'REVERSED'
        ) or exists(
          select 1 from erp.laundry_receipt_batch_size_lines x
          join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
          where l.receipt_id=v_receipt.id
        ) then
          raise exception 'Failed-wash service-only receipt unexpectedly owns physical/QC facts; reversal stopped for investigation';
        end if;
        update erp.laundry_receipts
        set status='REVERSED',updated_at=clock_timestamp()
        where id=v_receipt.id;
        -- A RETURN_UNPROCESSED custody fact remains immutable. Reversing the
        -- vendor charge never resurrects the old dispatch; a later physical
        -- handoff is a new delivery with its own time, rate, and lineage.
        update erp.laundry_deliveries set updated_at=clock_timestamp()
        where id=v_delivery.id;
        perform erp.sync_laundry_accrual(v_delivery.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
        if exists(select 1 from erp.fg_lots f where f.po_id=v_delivery.po_id) then
          perform erp.rebuild_po_hpp(
            v_delivery.po_id,'Failed-wash service cost reversed '||v_failed_wash_attempt_id::text
          );
          perform erp.propagate_conversion_hpp_for_po(v_delivery.po_id);
          perform erp.sync_po_hpp_to_gl(v_delivery.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
        end if;
        insert into erp.audit_logs(
          entity_type,entity_id,action,new_data,changed_by,change_reason
        ) values(
          'laundry_failed_wash_attempts',v_failed_wash_attempt_id,'REVERSE',
          jsonb_build_object(
            'receipt_id',v_receipt.id,'custody_outcome',v_custody_outcome,
            'physical_return_preserved',v_custody_outcome='RETURN_UNPROCESSED',
            'history_deleted',false
          ),v_actor,v_reason
        );
        select * into v_receipt from erp.laundry_receipts where id=v_receipt.id;
        select * into v_delivery from erp.laundry_deliveries where id=v_delivery.id;
        v_response:=jsonb_build_object(
          'action',v_action,'receipt_id',v_receipt.id,'status',v_receipt.status,
          'row_version',v_receipt.row_version,'delivery_id',v_delivery.id,
          'delivery_status',v_delivery.status,'delivery_row_version',v_delivery.row_version,
          'history_deleted',false,'custody_outcome',v_custody_outcome,
          'stock_effect',case when v_custody_outcome='RETURN_UNPROCESSED'
            then 'PHYSICAL_RETURN_PRESERVED' else 'PHYSICAL_STAYS_AT_LAUNDRY' end,
          'hpp_effect','FAILED_WASH_COST_REVERSED_AND_REPORTS_REBUILT'
        );
      end if;
    end if;

  elsif v_action='POST_FINAL_SKU' then
    if p_expected_version is null or v_group_id is null or v_location_id is null then
      raise exception 'Potongan, destination FG location, and expected_version are required';
    end if;
    if jsonb_typeof(v_lines)<>'array' or jsonb_array_length(v_lines)=0 then
      raise exception 'Final SKU posting requires at least one allocation line';
    end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer,
        source_laundry_receipt_line_id uuid,
        source_laundry_receipt_batch_size_line_id uuid,notes text
      ) where x.final_product_id is null
        or coalesce(x.qty_good_pcs,0)<0 or coalesce(x.qty_bs_pcs,0)<0
        or coalesce(x.qty_good_pcs,0)+coalesce(x.qty_bs_pcs,0)<=0
        or x.source_laundry_receipt_line_id is null
        or x.source_laundry_receipt_batch_size_line_id is null
    ) then raise exception 'Every connected Final SKU line needs positive quantity and exact receipt/batch/size lineage'; end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer,
        source_laundry_receipt_line_id uuid,
        source_laundry_receipt_batch_size_line_id uuid,notes text
      ) group by x.final_product_id,x.source_laundry_receipt_line_id
      having count(*)>1
    ) then raise exception 'Duplicate Final SKU/source lines are not allowed'; end if;

    perform 1 from erp.locations l
    where l.id=v_location_id and l.is_active and l.location_type='FG_WAREHOUSE'
    for share;
    if not found then raise exception 'Destination must be an active FG warehouse'; end if;

    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    -- The shared Potongan fence is acquired before receipt headers. A
    -- concurrent reversal cannot change
    -- POSTED -> REVERSED after a child source was checked but before QC/FG was
    -- committed.  Lock every referenced header deterministically, then
    -- re-check the complete exact-source chain while those locks are held.
    perform 1
    from erp.laundry_receipts r
    where r.id in(
      select distinct rl.receipt_id
      from jsonb_to_recordset(v_lines) x(
        final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer,
        source_laundry_receipt_line_id uuid,
        source_laundry_receipt_batch_size_line_id uuid,notes text
      )
      join erp.laundry_receipt_batch_size_lines sx
        on sx.id=x.source_laundry_receipt_batch_size_line_id
      join erp.laundry_receipt_lines rl
        on rl.id=sx.receipt_line_id
    )
    order by r.id
    for update;
    if(
      select count(*)
      from jsonb_to_recordset(v_lines) x(
        final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer,
        source_laundry_receipt_line_id uuid,
        source_laundry_receipt_batch_size_line_id uuid,notes text
      )
      join erp.laundry_receipt_batch_size_lines sx
        on sx.id=x.source_laundry_receipt_batch_size_line_id
      join erp.laundry_receipt_lines rl
        on rl.id=sx.receipt_line_id
       and rl.id=x.source_laundry_receipt_line_id
      join erp.laundry_receipts r on r.id=rl.receipt_id and r.status='POSTED'
      join erp.laundry_delivery_lines dl
        on dl.id=rl.delivery_line_id and dl.cutting_group_id=v_group_id
      join erp.laundry_deliveries d
        on d.id=dl.delivery_id and d.status<>'REVERSED'
      join erp.cutting_groups g
        on g.id=v_group_id and g.po_id=d.po_id
    )<>jsonb_array_length(v_lines) then
      raise exception 'Every Final SKU source must belong to the same Potongan and an authoritative POSTED Laundry receipt';
    end if;
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      'production.final_sku.post',p_client_request_id,p_payload
    );
    v_nested:=erp.post_final_sku_allocation_v1(p_payload,p_client_request_id,p_expected_version);
    -- completion_mode is operational/reporting state, not browser-owned
    -- metadata.  The predecessor persists the declaration before returning
    -- the authoritative post-mutation progress.  Reject a lie in either
    -- direction here; the exception rolls the nested QC, FG, BS, HPP,
    -- journal, row-version, and both idempotency envelopes back atomically.
    v_ready_after_qc:=nullif(v_nested->>'ready_for_qc_qty_pcs','')::bigint;
    if v_ready_after_qc is null then
      raise exception 'CP6 Final-SKU writer did not return authoritative ready-for-QC balance';
    end if;
    if ((p_payload->>'completion_mode')='ALL_READY' and v_ready_after_qc<>0)
       or ((p_payload->>'completion_mode')='PARTIAL_SELECTION' and v_ready_after_qc=0) then
      raise exception
        'CP6 completion_mode % conflicts with authoritative ready-for-QC remainder % after atomic posting',
        p_payload->>'completion_mode',v_ready_after_qc;
    end if;
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    if not found then raise exception 'CP6 execution context cleanup failed'; end if;
    v_qc_id:=nullif(v_nested->>'qc_inspection_id','')::uuid;
    select * into v_qc from erp.qc_inspections where id=v_qc_id;
    v_response:=v_nested||jsonb_build_object(
      'action',v_action,'qc_row_version',v_qc.row_version,
      'stock_effect','FG_GOOD_AND_QC_BS_POSTED',
      'hpp_effect','SERVER_REBUILT_FROM_IMMUTABLE_SNAPSHOTS',
      'browser_formula_used',false
    );

  else
    if p_expected_version is null or v_qc_id is null then
      raise exception 'QC inspection and expected_version are required';
    end if;
    select min(i.cutting_group_id::text)::uuid,count(distinct i.cutting_group_id)::integer
      into v_group_id,v_group_count
    from erp.qc_inspection_items i where i.inspection_id=v_qc_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected CP6 Final-SKU reversal requires one Potongan';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_qc from erp.qc_inspections where id=v_qc_id for update;
    if v_qc.id is null then raise exception 'QC inspection not found'; end if;
    if v_qc.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_qc.row_version;
    end if;
    perform erp.reverse_qc(v_qc.id,v_reason);
    select * into v_qc from erp.qc_inspections where id=v_qc.id;
    v_response:=jsonb_build_object(
      'action',v_action,'qc_inspection_id',v_qc.id,'status',v_qc.status,
      'row_version',v_qc.row_version,'history_deleted',false,
      'stock_effect','FG_AND_BS_REVERSED','hpp_effect','HPP_AND_GL_REBUILT'
    );
  end if;

  if v_action in('REVERSE_DELIVERY','REVERSE_RECEIPT','REVERSE_FINAL_SKU') then
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current()
      and actor_key=erp._idempotency_actor_key() and action=v_action
      and client_request_id=p_client_request_id;
    if not found then raise exception 'CP6 reverse execution context cleanup failed'; end if;
  end if;
  if exists(
    select 1 from erp.cp6_laundry_qc_execution_context c
    where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()
  ) then raise exception 'CP6 execution context leaked after action'; end if;
  v_response:=v_response||jsonb_build_object(
    'contract_version','CP6_V2620',
    'client_request_id',p_client_request_id,
    'committed',true
  );
  return erp._idempotency_complete(
    'cp6_laundry_qc_action_v1:'||lower(v_action),p_client_request_id,v_response
  );
end
$function$;

CREATE OR REPLACE FUNCTION erp.save_laundry_receipt_draft_v2(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_receipt erp.laundry_receipts%rowtype;
  v_id uuid:=nullif(p_payload->>'id','')::uuid;
  v_action text:=upper(coalesce(nullif(btrim(p_payload->>'action'),''),'SAVE'));
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_line jsonb;
  v_allocation jsonb;
  v_line_id uuid;
begin
  perform erp.require_internal();
  if v_reason is null then raise exception 'change_reason is required'; end if;
  if v_action not in ('SAVE','DELETE') then raise exception 'Invalid laundry receipt action'; end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'payload',p_payload,'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin('save_laundry_receipt_draft_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_id is null then
    if v_action='DELETE' then raise exception 'Laundry receipt id is required for DELETE'; end if;
    if p_expected_version is not null then raise exception 'expected_version must be null when creating a receipt'; end if;
    if coalesce(btrim(p_payload->>'receipt_number'),'')='' then raise exception 'receipt_number is required'; end if;
    insert into erp.laundry_receipts(
      receipt_number,delivery_id,physical_at,status,created_by
    ) values(
      btrim(p_payload->>'receipt_number'),(p_payload->>'delivery_id')::uuid,
      (p_payload->>'physical_at')::timestamptz,'DRAFT',erp.current_app_user_id()
    ) returning * into v_receipt;
    v_id:=v_receipt.id;
  else
    if p_expected_version is null then raise exception 'expected_version is required'; end if;
    select * into v_receipt from erp.laundry_receipts where id=v_id for update;
    if v_receipt.id is null then raise exception 'Laundry receipt not found'; end if;
    if v_receipt.status<>'DRAFT' then raise exception 'Posted receipt is locked; use reversal/correction'; end if;
    if v_receipt.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_receipt.row_version;
    end if;
    if v_action='DELETE' then
      delete from erp.laundry_receipts where id=v_id;
      v_response:=jsonb_build_object('laundry_receipt_id',v_id,'status','DELETED');
      return erp._idempotency_complete('save_laundry_receipt_draft_v2',p_client_request_id,v_response);
    end if;
    update erp.laundry_receipts
    set receipt_number=coalesce(nullif(btrim(p_payload->>'receipt_number'),''),v_receipt.receipt_number),
        delivery_id=case when p_payload?'delivery_id' then (p_payload->>'delivery_id')::uuid else v_receipt.delivery_id end,
        physical_at=case when p_payload?'physical_at' then (p_payload->>'physical_at')::timestamptz else v_receipt.physical_at end,
        updated_at=statement_timestamp()
    where id=v_id returning * into v_receipt;
  end if;

  if p_payload?'lines' then
    if jsonb_typeof(p_payload->'lines')<>'array' then raise exception 'lines must be an array'; end if;
    delete from erp.laundry_receipt_lines where receipt_id=v_id;
    for v_line in select value from jsonb_array_elements(p_payload->'lines')
    loop
      v_line_id:=coalesce(nullif(v_line->>'id','')::uuid,gen_random_uuid());
      insert into erp.laundry_receipt_lines(
        id,receipt_id,delivery_line_id,actual_wash_process_id,
        qty_good_received,qty_bs_laundry,qty_stuck,qty_missing,
        actual_rate_snapshot,actual_cost_status,actual_cost,notes
      ) values(
        v_line_id,v_id,(v_line->>'delivery_line_id')::uuid,
        nullif(v_line->>'actual_wash_process_id','')::uuid,
        coalesce(nullif(v_line->>'qty_good_received','')::integer,0),
        coalesce(nullif(v_line->>'qty_bs_laundry','')::integer,0),
        coalesce(nullif(v_line->>'qty_stuck','')::integer,0),
        coalesce(nullif(v_line->>'qty_missing','')::integer,0),
        nullif(v_line->>'actual_rate_snapshot','')::numeric,
        upper(coalesce(nullif(v_line->>'actual_cost_status',''),'PENDING')),
        nullif(v_line->>'actual_cost','')::numeric,
        nullif(btrim(v_line->>'notes'),'')
      );
      if v_line?'bs_allocations' then
        if jsonb_typeof(v_line->'bs_allocations')<>'array' then
          raise exception 'bs_allocations must be an array';
        end if;
        for v_allocation in select value from jsonb_array_elements(v_line->'bs_allocations')
        loop
          insert into erp.laundry_receipt_bs_product_allocations(
            id,receipt_line_id,product_id,qty_bs,notes,created_by
          ) values(
            coalesce(nullif(v_allocation->>'id','')::uuid,gen_random_uuid()),
            v_line_id,(v_allocation->>'product_id')::uuid,
            (v_allocation->>'qty_bs')::integer,
            nullif(btrim(v_allocation->>'notes'),''),erp.current_app_user_id()
          );
        end loop;
      end if;
    end loop;
    update erp.laundry_receipts set updated_at=statement_timestamp() where id=v_id returning * into v_receipt;
  end if;

  select * into v_receipt from erp.laundry_receipts where id=v_id;
  v_response:=jsonb_build_object(
    'laundry_receipt_id',v_receipt.id,'status',v_receipt.status,
    'row_version',v_receipt.row_version,
    'line_count',(select count(*) from erp.laundry_receipt_lines where receipt_id=v_receipt.id),
    'lines',coalesce((
      select jsonb_agg(jsonb_build_object(
        'receipt_line_id',l.id,'delivery_line_id',l.delivery_line_id,
        'qty_good_received',l.qty_good_received,'qty_bs_laundry',l.qty_bs_laundry,
        'qty_stuck',l.qty_stuck,'qty_missing',l.qty_missing,
        'bs_allocations',coalesce((select jsonb_agg(jsonb_build_object(
          'allocation_id',a.id,'product_id',a.product_id,'qty_bs',a.qty_bs
        ) order by a.id) from erp.laundry_receipt_bs_product_allocations a
        where a.receipt_line_id=l.id),'[]'::jsonb)
      ) order by l.id) from erp.laundry_receipt_lines l where l.receipt_id=v_receipt.id
    ),'[]'::jsonb)
  );
  return erp._idempotency_complete('save_laundry_receipt_draft_v2',p_client_request_id,v_response);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.save_material_purchase_draft_v2(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_purchase_id uuid := nullif(p_payload->>'id', '')::uuid;
  v_header erp.material_purchase_headers%rowtype;
  v_line jsonb;
  v_roll jsonb;
  v_material erp.materials%rowtype;
  v_item_id uuid;
  v_roll_id uuid;
  v_qty numeric;
  v_unit_price numeric;
  v_effective_unit_price numeric;
  v_benchmark_id uuid;
  v_benchmark_price numeric;
  v_price_state text;
  v_price_source text;
  v_roll_total numeric;
  v_roll_count integer;
  v_reason text := nullif(btrim(p_payload->>'change_reason'), '');
  v_physical_at timestamptz := nullif(p_payload->>'physical_at', '')::timestamptz;
begin
  perform erp.require_internal();
  if v_reason is null then raise exception 'change_reason is required'; end if;
  if coalesce(btrim(p_payload->>'purchase_number'), '') = '' then raise exception 'purchase_number is required'; end if;
  if v_physical_at is null then raise exception 'physical_at is required'; end if;
  if v_physical_at > clock_timestamp() + interval '5 minutes' then raise exception 'physical_at cannot be in the future'; end if;
  if p_payload ? 'lines' and jsonb_typeof(p_payload->'lines') <> 'array' then raise exception 'lines must be an array'; end if;

  v_hash := erp._request_hash(jsonb_build_object('payload', p_payload, 'expected_version', p_expected_version));
  v_cached := erp._idempotency_begin('save_material_purchase_draft_v2', p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason', v_reason, true);

  if v_purchase_id is null then
    if p_expected_version is not null then raise exception 'expected_version must be null when creating a purchase'; end if;
    insert into erp.material_purchase_headers(
      purchase_number, supplier_id, physical_at, status, notes, created_by,
      location_id, supplier_invoice_number, due_date
    ) values (
      btrim(p_payload->>'purchase_number'),
      nullif(p_payload->>'supplier_id', '')::uuid,
      v_physical_at, 'DRAFT', nullif(btrim(p_payload->>'notes'), ''),
      erp.current_app_user_id(), nullif(p_payload->>'location_id', '')::uuid,
      nullif(btrim(p_payload->>'supplier_invoice_number'), ''),
      nullif(p_payload->>'due_date', '')::date
    ) returning * into v_header;
    v_purchase_id := v_header.id;
  else
    if p_expected_version is null then raise exception 'expected_version is required when updating a purchase'; end if;
    select * into v_header
    from erp.material_purchase_headers where id = v_purchase_id for update;
    if v_header.id is null then raise exception 'Material purchase not found'; end if;
    if v_header.status <> 'DRAFT' then raise exception 'Only DRAFT material purchases can be saved'; end if;
    if v_header.row_version <> p_expected_version then
      raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_header.row_version;
    end if;
    update erp.material_purchase_headers
    set purchase_number = btrim(p_payload->>'purchase_number'),
        supplier_id = nullif(p_payload->>'supplier_id', '')::uuid,
        physical_at = v_physical_at,
        notes = nullif(btrim(p_payload->>'notes'), ''),
        location_id = nullif(p_payload->>'location_id', '')::uuid,
        supplier_invoice_number = nullif(btrim(p_payload->>'supplier_invoice_number'), ''),
        due_date = nullif(p_payload->>'due_date', '')::date,
        updated_at = statement_timestamp()
    where id = v_purchase_id
    returning * into v_header;
  end if;

  delete from erp.material_rolls r
  using erp.material_purchase_items i
  where r.purchase_item_id = i.id and i.purchase_id = v_purchase_id;
  delete from erp.material_purchase_items where purchase_id = v_purchase_id;

  for v_line in
    select value from jsonb_array_elements(coalesce(p_payload->'lines', '[]'::jsonb))
  loop
    if coalesce(nullif(v_line->>'material_id', ''), '') = '' then raise exception 'Each purchase line requires material_id'; end if;
    select * into v_material
    from erp.materials where id = (v_line->>'material_id')::uuid;
    if v_material.id is null then raise exception 'Purchase material not found'; end if;
    if not v_material.is_active then raise exception 'Inactive material % cannot be purchased', v_material.material_sku; end if;

    v_qty := coalesce(
      nullif(v_line->>'qty', '')::numeric,
      nullif(v_line->>'purchase_qty_entered', '')::numeric
        * coalesce(nullif(v_line->>'purchase_uom_factor_snapshot', '')::numeric, 1)
    );
    if v_qty is null or v_qty <= 0 then raise exception 'Purchase quantity must be positive'; end if;

    v_benchmark_id := null;
    v_benchmark_price := null;
    v_unit_price := nullif(v_line->>'unit_price', '')::numeric;
    v_price_source := upper(coalesce(nullif(btrim(v_line->>'price_source'), ''), 'MANUAL_ESTIMATE'));
    v_price_state := upper(coalesce(nullif(btrim(v_line->>'price_state'), ''),
      case when v_price_source = 'SUPPLIER_INVOICE' then 'FINAL' else 'ESTIMATED' end));

    if v_unit_price is null and v_material.material_type = 'FABRIC' then
      select id, benchmark_price_per_base_uom
      into v_benchmark_id, v_benchmark_price
      from erp.fabric_benchmark_price_versions
      where material_id = v_material.id
        and effective_from <= v_physical_at
        and (effective_to is null or v_physical_at < effective_to)
      order by effective_from desc
      limit 1;
      if v_benchmark_id is null then
        raise exception 'Fabric % has no benchmark price effective at receipt time', v_material.material_sku;
      end if;
      v_unit_price := v_benchmark_price;
      v_price_source := 'BENCHMARK';
      v_price_state := 'ESTIMATED';
    elsif v_price_source = 'BENCHMARK' then
      select id, benchmark_price_per_base_uom
      into v_benchmark_id, v_benchmark_price
      from erp.fabric_benchmark_price_versions
      where material_id = v_material.id
        and effective_from <= v_physical_at
        and (effective_to is null or v_physical_at < effective_to)
      order by effective_from desc
      limit 1;
      if v_benchmark_id is null then raise exception 'Benchmark source has no effective benchmark version'; end if;
      if abs(v_unit_price - v_benchmark_price) > 0.000001 then
        raise exception 'Benchmark source price must match the effective benchmark snapshot';
      end if;
    end if;

    if v_price_state not in ('ESTIMATED','FINAL') then raise exception 'Invalid price_state'; end if;
    if v_price_source not in ('BENCHMARK','SUPPLIER_QUOTE','SUPPLIER_INVOICE','MANUAL_ESTIMATE','MIGRATION') then
      raise exception 'Invalid price_source';
    end if;
    if v_price_state = 'FINAL' and v_price_source not in ('SUPPLIER_INVOICE','MIGRATION') then
      raise exception 'FINAL purchase price must come from SUPPLIER_INVOICE or MIGRATION';
    end if;
    if v_unit_price is null and v_line->>'purchase_price_per_uom_snapshot' is null then
      raise exception 'unit_price or purchase_price_per_uom_snapshot is required';
    end if;
    if v_unit_price is not null and v_unit_price < 0 then raise exception 'unit_price cannot be negative'; end if;

    v_item_id := coalesce(nullif(v_line->>'id', '')::uuid, gen_random_uuid());
    insert into erp.material_purchase_items(
      id, purchase_id, material_id, qty, unit_price, lot_number, notes,
      purchase_qty_entered, purchase_uom_code, purchase_uom_factor_snapshot,
      purchase_price_per_uom_snapshot, price_state, price_source,
      benchmark_price_version_id, benchmark_unit_price_snapshot,
      supplier_final_unit_price_snapshot, price_finalized_at, price_finalized_by
    ) values (
      v_item_id, v_purchase_id, v_material.id, v_qty, v_unit_price,
      nullif(btrim(v_line->>'lot_number'), ''), nullif(btrim(v_line->>'notes'), ''),
      nullif(v_line->>'purchase_qty_entered', '')::numeric,
      nullif(upper(btrim(v_line->>'purchase_uom_code')), ''),
      nullif(v_line->>'purchase_uom_factor_snapshot', '')::numeric,
      nullif(v_line->>'purchase_price_per_uom_snapshot', '')::numeric,
      v_price_state, v_price_source, v_benchmark_id,
      v_benchmark_price,
      case when v_price_state = 'FINAL' then v_unit_price else null end,
      case when v_price_state = 'FINAL' then statement_timestamp() else null end,
      case when v_price_state = 'FINAL' then erp.current_app_user_id() else null end
    ) returning unit_price into v_effective_unit_price;

    if v_price_state = 'FINAL' and v_unit_price is null then
      update erp.material_purchase_items
      set supplier_final_unit_price_snapshot = v_effective_unit_price
      where id = v_item_id;
    end if;

    v_roll_total := 0;
    v_roll_count := 0;
    if v_line ? 'rolls' and jsonb_typeof(v_line->'rolls') <> 'array' then raise exception 'rolls must be an array'; end if;
    for v_roll in
      select value from jsonb_array_elements(coalesce(v_line->'rolls', '[]'::jsonb))
    loop
      if coalesce(btrim(v_roll->>'roll_number'), '') = '' then raise exception 'roll_number is required'; end if;
      if nullif(v_roll->>'qty', '')::numeric is null or nullif(v_roll->>'qty', '')::numeric <= 0 then
        raise exception 'Roll quantity must be positive';
      end if;
      v_roll_id := coalesce(nullif(v_roll->>'id', '')::uuid, gen_random_uuid());
      insert into erp.material_rolls(
        id, material_id, purchase_item_id, supplier_id, roll_number,
        original_qty, cached_qty, status, received_at, notes
      ) values (
        v_roll_id, v_material.id, v_item_id, v_header.supplier_id,
        btrim(v_roll->>'roll_number'), (v_roll->>'qty')::numeric,
        (v_roll->>'qty')::numeric, 'AVAILABLE', v_physical_at,
        nullif(btrim(v_roll->>'notes'), '')
      );
      v_roll_total := v_roll_total + (v_roll->>'qty')::numeric;
      v_roll_count := v_roll_count + 1;
    end loop;
    if v_roll_count > 0 and abs(v_roll_total - v_qty) > 0.000001 then
      raise exception 'Line quantity % does not equal roll total %', v_qty, v_roll_total;
    end if;
  end loop;

  select * into v_header from erp.material_purchase_headers where id = v_purchase_id;
  v_response := jsonb_build_object(
    'purchase_id', v_purchase_id,
    'status', v_header.status,
    'row_version', v_header.row_version,
    'lines', coalesce((
      select jsonb_agg(jsonb_build_object(
        'id', i.id, 'material_id', i.material_id, 'qty', i.qty,
        'unit_price', i.unit_price, 'price_state', i.price_state,
        'price_source', i.price_source
      ) order by i.id)
      from erp.material_purchase_items i where i.purchase_id = v_purchase_id
    ), '[]'::jsonb)
  );
  return erp._idempotency_complete('save_material_purchase_draft_v2', p_client_request_id, v_response);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.save_material_supplier_invoice_draft_v2(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_id uuid:=nullif(p_payload->>'id','')::uuid;
  v_action text:=upper(coalesce(nullif(p_payload->>'action',''),'SAVE'));
  h erp.material_supplier_invoices%rowtype;
  j jsonb;v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
begin
  perform erp.require_owner_admin();
  if v_reason is null then raise exception 'change_reason is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object('payload',p_payload,'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('save_material_supplier_invoice_draft_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_action='DELETE' then
    if v_id is null or p_expected_version is null then raise exception 'id and expected_version are required for delete'; end if;
    select * into h from erp.material_supplier_invoices where id=v_id for update;
    if h.id is null then raise exception 'Supplier invoice draft not found'; end if;
    if h.status<>'DRAFT' then raise exception 'Only a DRAFT supplier invoice may be deleted'; end if;
    if h.row_version<>p_expected_version then raise exception 'STALE_VERSION expected %, current %',p_expected_version,h.row_version; end if;
    delete from erp.material_supplier_invoices where id=h.id;
    v_response:=jsonb_build_object('supplier_invoice_id',v_id,'deleted',true);
    return erp._idempotency_complete('save_material_supplier_invoice_draft_v2',p_client_request_id,v_response);
  elsif v_action<>'SAVE' then
    raise exception 'Unsupported action %',v_action;
  end if;

  if nullif(btrim(p_payload->>'invoice_number'),'') is null then raise exception 'invoice_number is required'; end if;
  if nullif(p_payload->>'supplier_id','') is null then raise exception 'supplier_id is required'; end if;
  if nullif(p_payload->>'invoice_date','') is null then raise exception 'invoice_date is required'; end if;
  if (p_payload->>'invoice_date')::date>((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date then raise exception 'invoice_date cannot be in the future'; end if;
  if coalesce(jsonb_typeof(p_payload->'lines'),'null')<>'array'
     or jsonb_array_length(p_payload->'lines')=0 then raise exception 'At least one invoice line is required'; end if;

  if v_id is null then
    v_id:=gen_random_uuid();
    insert into erp.material_supplier_invoices(
      id,invoice_number,supplier_id,invoice_date,received_at,due_date,notes,created_by
    ) values(
      v_id,btrim(p_payload->>'invoice_number'),(p_payload->>'supplier_id')::uuid,
      (p_payload->>'invoice_date')::date,
      coalesce(nullif(p_payload->>'received_at','')::timestamptz,clock_timestamp()),
      nullif(p_payload->>'due_date','')::date,nullif(btrim(p_payload->>'notes'),''),
      erp.current_app_user_id()
    );
  else
    if p_expected_version is null then raise exception 'expected_version is required for update'; end if;
    select * into h from erp.material_supplier_invoices where id=v_id for update;
    if h.id is null or h.status<>'DRAFT' then raise exception 'Supplier invoice must be DRAFT'; end if;
    if h.row_version<>p_expected_version then raise exception 'STALE_VERSION expected %, current %',p_expected_version,h.row_version; end if;
    update erp.material_supplier_invoices
    set invoice_number=btrim(p_payload->>'invoice_number'),
        supplier_id=(p_payload->>'supplier_id')::uuid,
        invoice_date=(p_payload->>'invoice_date')::date,
        received_at=coalesce(nullif(p_payload->>'received_at','')::timestamptz,received_at),
        due_date=nullif(p_payload->>'due_date','')::date,
        notes=nullif(btrim(p_payload->>'notes'),'')
    where id=v_id;
    delete from erp.material_supplier_invoice_lines where invoice_id=v_id;
  end if;

  for j in select value from jsonb_array_elements(p_payload->'lines') loop
    insert into erp.material_supplier_invoice_lines(
      invoice_id,purchase_item_id,qty_invoiced,unit_price,discount_amount,notes
    ) values(
      v_id,(j->>'purchase_item_id')::uuid,(j->>'qty_invoiced')::numeric,
      (j->>'unit_price')::numeric,coalesce(nullif(j->>'discount_amount','')::numeric,0),
      nullif(btrim(j->>'notes'),'')
    );
  end loop;
  update erp.material_supplier_invoices set updated_at=clock_timestamp() where id=v_id;
  select * into h from erp.material_supplier_invoices where id=v_id;
  v_response:=jsonb_build_object(
    'supplier_invoice_id',h.id,'invoice_number',h.invoice_number,'status',h.status,
    'row_version',h.row_version,
    'line_count',(select count(*) from erp.material_supplier_invoice_lines where invoice_id=h.id),
    'gross_amount',(select coalesce(sum(gross_amount),0) from erp.material_supplier_invoice_lines where invoice_id=h.id),
    'discount_amount',(select coalesce(sum(discount_amount),0) from erp.material_supplier_invoice_lines where invoice_id=h.id),
    'net_amount',(select coalesce(sum(net_amount),0) from erp.material_supplier_invoice_lines where invoice_id=h.id)
  );
  return erp._idempotency_complete('save_material_supplier_invoice_draft_v2',p_client_request_id,v_response);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.save_worker_roster_v1(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_operation constant text := 'save_worker_roster_v1';
  v_hash text;
  v_cached jsonb;
  v_worker_id uuid := nullif(p_payload->>'worker_id', '')::uuid;
  v_contractor_id uuid := nullif(p_payload->>'contractor_id', '')::uuid;
  v_worker_name text := nullif(btrim(p_payload->>'worker_name'), '');
  v_job_description text := nullif(btrim(p_payload->>'job_description'), '');
  v_pay_scheme text := upper(coalesce(nullif(btrim(p_payload->>'pay_scheme'), ''), 'DAILY'));
  v_joined_at date := nullif(p_payload->>'joined_at', '')::date;
  v_left_at date := nullif(p_payload->>'left_at', '')::date;
  v_reactivated_on date := nullif(p_payload->>'reactivated_at', '')::date;
  v_is_active boolean := coalesce((p_payload->>'is_active')::boolean, true);
  v_initial_rate numeric := coalesce((p_payload->>'initial_daily_rate')::numeric, 0);
  v_rate_from date := coalesce(nullif(p_payload->>'rate_effective_from', '')::date, v_joined_at, ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  v_reason text := nullif(btrim(p_payload->>'reason'), '');
  v_existing erp.contractor_workers%rowtype;
  v_response jsonb;
begin
  perform erp.require_owner_admin();

  if v_contractor_id is null or v_worker_name is null
     or v_job_description is null or v_joined_at is null then
    raise exception 'contractor_id, worker_name, job_description, and joined_at are required';
  end if;
  if not exists (
    select 1 from erp.contractors c
    where c.id = v_contractor_id and c.contractor_type = 'MANDOR'
  ) then
    raise exception 'Worker roster contractor must be an existing MANDOR';
  end if;
  if v_reason is null then raise exception 'Worker change reason is required'; end if;
  if v_pay_scheme not in ('DAILY','PIECE','HYBRID','NONE') then
    raise exception 'Unsupported pay_scheme';
  end if;
  if v_left_at is not null and v_is_active then
    raise exception 'An active worker cannot have a stop date; clear left_at or deactivate the worker';
  end if;
  if not v_is_active and v_left_at is null then
    raise exception 'A deactivated worker requires left_at';
  end if;
  if not v_is_active and v_left_at > ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date then
    raise exception 'A worker stop date cannot be in the future because roster status changes immediately';
  end if;
  if v_reactivated_on > ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date then
    raise exception 'reactivated_at cannot be in the future because roster status changes immediately';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'payload', p_payload,
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  perform set_config('app.change_reason', v_reason, true);

  if v_worker_id is null then
    if p_expected_version is not null then
      raise exception 'expected_version must be null when creating a worker';
    end if;
    if v_initial_rate < 0 then
      raise exception 'initial_daily_rate cannot be negative';
    end if;
    if v_rate_from > v_joined_at then
      raise exception 'Initial daily rate must cover the worker start date';
    end if;
    if exists (
      select 1
      from erp.attendance_periods p
      where p.contractor_id = v_contractor_id
        and p.status in ('POSTED','CORRECTED')
        and daterange(p.period_start, p.period_end + 1, '[)')
            && daterange(v_joined_at, coalesce(v_left_at + 1, 'infinity'::date), '[)')
    ) then
      raise exception 'A new worker start cannot overlap posted attendance history; reverse/correct roster chronology first';
    end if;

    insert into erp.contractor_workers(
      contractor_id, worker_code, worker_name, job_description, pay_scheme,
      daily_rate, is_active, joined_at, left_at, notes, created_by, updated_by
    ) values (
      v_contractor_id, nullif(btrim(p_payload->>'worker_code'), ''), v_worker_name,
      v_job_description, v_pay_scheme,
      v_initial_rate, v_is_active, v_joined_at, v_left_at,
      nullif(btrim(p_payload->>'notes'), ''),
      erp.current_app_user_id(), erp.current_app_user_id()
    ) returning id into v_worker_id;

    perform set_config('app.worker_rate_write', 'on', true);
    insert into erp.worker_daily_rate_versions(
      worker_id, daily_rate, effective_from, change_reason, created_by
    ) values (
      v_worker_id, v_initial_rate, v_rate_from, v_reason, erp.current_app_user_id()
    );

    perform set_config('app.worker_employment_write', 'on', true);
    insert into erp.worker_employment_periods(
      worker_id, started_on, ended_on, start_reason, end_reason,
      created_by, ended_by, ended_at
    ) values (
      v_worker_id, v_joined_at, v_left_at, v_reason,
      case when v_left_at is null then null else v_reason end,
      erp.current_app_user_id(),
      case when v_left_at is null then null else erp.current_app_user_id() end,
      case when v_left_at is null then null else clock_timestamp() end
    );
  else
    select * into v_existing
    from erp.contractor_workers
    where id = v_worker_id
    for update;

    if v_existing.id is null then raise exception 'Worker not found'; end if;
    if p_expected_version is null or v_existing.row_version <> p_expected_version then
      raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_existing.row_version;
    end if;
    if v_existing.contractor_id <> v_contractor_id then
      raise exception 'A worker cannot be moved between contractors; create a new roster identity';
    end if;
    if v_pay_scheme is distinct from v_existing.pay_scheme and exists (
      select 1
      from erp.attendance_periods p
      join erp.worker_employment_periods e on e.worker_id = v_worker_id
      where p.contractor_id = v_contractor_id
        and p.status in ('POSTED','CORRECTED')
        and daterange(p.period_start, p.period_end + 1, '[)')
            && daterange(e.started_on, coalesce(e.ended_on + 1, 'infinity'::date), '[)')
    ) then
      raise exception 'Worker pay_scheme cannot change across posted attendance history';
    end if;
    if v_joined_at is distinct from v_existing.joined_at then
      raise exception 'Original worker start date is immutable; use employment episodes for reactivation';
    end if;
    if v_joined_at is not null and v_joined_at < (
      select min(r.effective_from)
      from erp.worker_daily_rate_versions r
      where r.worker_id = v_worker_id
    ) then
      raise exception 'Worker start date cannot precede the first daily-rate version';
    end if;
    if exists (
      select 1
      from erp.attendance_records a
      where a.worker_id = v_worker_id
        and (a.attendance_date < v_joined_at
          or (v_left_at is not null and a.attendance_date > v_left_at))
    ) then
      raise exception 'Worker start/stop dates cannot exclude existing attendance history';
    end if;

    perform set_config('app.worker_employment_write', 'on', true);
    if v_existing.is_active and not v_is_active then
      update erp.worker_employment_periods e
      set ended_on = v_left_at,
          end_reason = v_reason,
          ended_by = erp.current_app_user_id(),
          ended_at = clock_timestamp()
      where e.worker_id = v_worker_id and e.ended_on is null;
      if not found then
        raise exception 'Active worker has no open employment episode';
      end if;
    elsif not v_existing.is_active and v_is_active then
      if v_reactivated_on is null then
        raise exception 'reactivated_at is required when activating a stopped worker';
      end if;
      if v_reactivated_on <= coalesce((
        select max(e.ended_on) from erp.worker_employment_periods e where e.worker_id = v_worker_id
      ), '-infinity'::date) then
        raise exception 'reactivated_at must be after the previous employment stop date';
      end if;
      if exists (
        select 1
        from erp.attendance_periods p
        where p.contractor_id = v_contractor_id
          and p.status in ('POSTED','CORRECTED')
          and daterange(p.period_start, p.period_end + 1, '[)')
              && daterange(v_reactivated_on, 'infinity'::date, '[)')
      ) then
        raise exception 'A reactivation start cannot overlap posted attendance history; reverse/correct roster chronology first';
      end if;
      perform erp.require_worker_daily_rate_at(v_worker_id, v_reactivated_on);
      insert into erp.worker_employment_periods(
        worker_id, started_on, start_reason, created_by
      ) values (
        v_worker_id, v_reactivated_on, v_reason, erp.current_app_user_id()
      );
    elsif not v_existing.is_active and not v_is_active
          and v_left_at is distinct from v_existing.left_at then
      raise exception 'Stopped employment date is historical; reactivate then create a new episode';
    end if;

    update erp.contractor_workers
    set worker_code = nullif(btrim(p_payload->>'worker_code'), ''),
        worker_name = v_worker_name,
        job_description = v_job_description,
        pay_scheme = v_pay_scheme,
        is_active = v_is_active,
        joined_at = v_joined_at,
        left_at = v_left_at,
        notes = nullif(btrim(p_payload->>'notes'), ''),
        updated_by = erp.current_app_user_id()
    where id = v_worker_id;
  end if;

  select jsonb_build_object(
    'worker_id', w.id,
    'contractor_id', w.contractor_id,
    'worker_name', w.worker_name,
    'job_description', w.job_description,
    'pay_scheme', w.pay_scheme,
    'daily_rate', erp.worker_daily_rate_at(w.id, ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date),
    'is_active', w.is_active,
    'joined_at', w.joined_at,
    'left_at', w.left_at,
    'reactivated_at', (
      select max(e.started_on) from erp.worker_employment_periods e where e.worker_id = w.id
    ),
    'notes', w.notes,
    'row_version', w.row_version
  ) into v_response
  from erp.contractor_workers w
  where w.id = v_worker_id;

  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.set_accessory_uom_conversion_v2(p_category_id uuid, p_uom_code text, p_base_qty_per_uom numeric, p_effective_from timestamp with time zone, p_notes text, p_change_reason text, p_client_request_id uuid, p_expected_category_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_category erp.accessory_categories%rowtype;
  v_prev erp.accessory_category_uom_conversions%rowtype;
  v_next_at timestamptz;v_new_id uuid;
  v_uom text:=upper(btrim(p_uom_code));
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_change_reason),'') is null then raise exception 'change_reason is required';end if;
  if p_expected_category_version is null then raise exception 'expected_category_version is required';end if;
  if p_effective_from is null then raise exception 'effective_from is required';end if;
  if coalesce(p_base_qty_per_uom,0)<=0 then raise exception 'base_qty_per_uom must be positive';end if;

  v_hash:=erp._request_hash(jsonb_build_object(
    'category_id',p_category_id,'uom_code',v_uom,'factor',p_base_qty_per_uom,
    'effective_from',p_effective_from,'notes',p_notes,
    'reason',btrim(p_change_reason),'expected_category_version',p_expected_category_version
  ));
  v_cached:=erp._idempotency_begin('set_accessory_uom_conversion_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached;end if;
  perform set_config('app.change_reason',btrim(p_change_reason),true);
  perform pg_advisory_xact_lock(hashtextextended('ACCUOM:'||p_category_id::text||':'||v_uom,0));

  select * into v_category from erp.accessory_categories where id=p_category_id for update;
  if v_category.id is null or not v_category.is_active then raise exception 'Active accessory category not found';end if;
  if v_category.row_version<>p_expected_category_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_category_version,v_category.row_version;
  end if;
  if v_uom=v_category.base_uom_code then
    raise exception 'Base UOM always has factor 1 and must not be versioned';
  end if;
  if not exists(select 1 from erp.uom_definitions where unit_code=v_uom) then
    raise exception 'UOM % is not registered',v_uom;
  end if;
  if exists(
    select 1 from erp.accessory_category_uom_conversions
    where category_id=p_category_id and uom_code=v_uom and effective_from=p_effective_from
  ) then raise exception 'A conversion version already starts at this effective_from';end if;

  select * into v_prev
  from erp.accessory_category_uom_conversions
  where category_id=p_category_id and uom_code=v_uom
    and effective_from<p_effective_from
    and (effective_to is null or effective_to>p_effective_from)
  order by effective_from desc limit 1 for update;

  select min(effective_from) into v_next_at
  from erp.accessory_category_uom_conversions
  where category_id=p_category_id and uom_code=v_uom
    and effective_from>p_effective_from;

  if v_prev.id is not null then
    update erp.accessory_category_uom_conversions
    set effective_to=p_effective_from
    where id=v_prev.id;
  end if;

  insert into erp.accessory_category_uom_conversions(
    category_id,uom_code,base_qty_per_uom,effective_from,effective_to,notes
  ) values(
    p_category_id,v_uom,p_base_qty_per_uom,p_effective_from,v_next_at,nullif(btrim(p_notes),'')
  ) returning id into v_new_id;

  update erp.accessory_categories set updated_at=statement_timestamp() where id=p_category_id
  returning * into v_category;

  v_response:=jsonb_build_object(
    'accessory_uom_conversion_id',v_new_id,'category_id',p_category_id,
    'uom_code',v_uom,'base_qty_per_uom',p_base_qty_per_uom,
    'effective_from',p_effective_from,'effective_to',v_next_at,
    'category_row_version',v_category.row_version
  );
  return erp._idempotency_complete('set_accessory_uom_conversion_v2',p_client_request_id,v_response);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.set_fabric_benchmark_price_v2(p_material_id uuid, p_benchmark_price numeric, p_effective_from timestamp with time zone, p_change_reason text, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_material erp.materials%rowtype;
  v_open erp.fabric_benchmark_price_versions%rowtype;
  v_version_id uuid;
begin
  perform erp.require_owner_admin();
  if p_material_id is null or p_benchmark_price is null or p_benchmark_price <= 0 then
    raise exception 'Material and positive benchmark price are required';
  end if;
  if p_effective_from is null then raise exception 'effective_from is required'; end if;
  if coalesce(btrim(p_change_reason), '') = '' then raise exception 'change_reason is required'; end if;
  if p_expected_version is null then raise exception 'expected_version is required'; end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'material_id', p_material_id, 'benchmark_price', p_benchmark_price,
    'effective_from', p_effective_from, 'change_reason', p_change_reason,
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin('set_fabric_benchmark_price_v2', p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  perform pg_advisory_xact_lock(hashtextextended('fabric-benchmark:' || p_material_id::text, 0));
  select * into v_material from erp.materials where id = p_material_id for update;
  if v_material.id is null or v_material.material_type <> 'FABRIC' then
    raise exception 'FABRIC material not found';
  end if;
  if v_material.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_material.row_version;
  end if;

  select * into v_open
  from erp.fabric_benchmark_price_versions
  where material_id = p_material_id and effective_to is null
  for update;

  if v_open.id is not null then
    if p_effective_from <= v_open.effective_from then
      raise exception 'New benchmark effective_from must be later than the current version';
    end if;
    update erp.fabric_benchmark_price_versions
    set effective_to = p_effective_from
    where id = v_open.id;
  elsif exists (
    select 1 from erp.fabric_benchmark_price_versions
    where material_id = p_material_id and effective_from >= p_effective_from
  ) then
    raise exception 'Backdated benchmark would overlap existing history';
  end if;

  perform set_config('app.change_reason', btrim(p_change_reason), true);
  insert into erp.fabric_benchmark_price_versions(
    material_id, benchmark_price_per_base_uom, base_uom_code_snapshot,
    effective_from, change_reason, created_by
  ) values (
    p_material_id, p_benchmark_price, v_material.unit_code,
    p_effective_from, btrim(p_change_reason), erp.current_app_user_id()
  ) returning id into v_version_id;

  update erp.materials set updated_at = statement_timestamp() where id = p_material_id
  returning * into v_material;

  v_response := jsonb_build_object(
    'material_id', p_material_id,
    'benchmark_version_id', v_version_id,
    'benchmark_price', p_benchmark_price,
    'effective_from', p_effective_from,
    'row_version', v_material.row_version
  );
  return erp._idempotency_complete('set_fabric_benchmark_price_v2', p_client_request_id, v_response);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.set_worker_daily_rate_v1(p_worker_id uuid, p_daily_rate numeric, p_effective_from date, p_reason text, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_operation constant text := 'set_worker_daily_rate_v1';
  v_hash text;
  v_cached jsonb;
  v_worker erp.contractor_workers%rowtype;
  v_next_from date;
  v_new_id uuid;
  v_response jsonb;
begin
  perform erp.require_owner_admin();

  if p_worker_id is null or p_effective_from is null or p_expected_version is null then
    raise exception 'worker_id, effective_from, and expected_version are required';
  end if;
  if p_daily_rate is null or p_daily_rate < 0 then
    raise exception 'daily_rate must be zero or positive';
  end if;
  if coalesce(btrim(p_reason), '') = '' then
    raise exception 'Rate change reason is required';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'worker_id', p_worker_id,
    'daily_rate', p_daily_rate,
    'effective_from', p_effective_from,
    'reason', p_reason,
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_worker
  from erp.contractor_workers
  where id = p_worker_id
  for update;

  if v_worker.id is null then raise exception 'Worker not found'; end if;
  if v_worker.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_worker.row_version;
  end if;
  if v_worker.joined_at is not null and p_effective_from < v_worker.joined_at then
    raise exception 'Rate effective date cannot be earlier than worker start date';
  end if;
  if exists (
    select 1 from erp.worker_daily_rate_versions r
    where r.worker_id = p_worker_id and r.effective_from = p_effective_from
  ) then
    raise exception 'A worker rate version already starts on this date; use a later effective date';
  end if;

  perform set_config('app.change_reason', p_reason, true);
  perform set_config('app.worker_rate_write', 'on', true);
  perform pg_advisory_xact_lock(hashtextextended('WORKER_RATE|' || p_worker_id::text, 0));

  select min(r.effective_from) into v_next_from
  from erp.worker_daily_rate_versions r
  where r.worker_id = p_worker_id and r.effective_from > p_effective_from;

  update erp.worker_daily_rate_versions r
  set effective_to = p_effective_from - 1
  where r.worker_id = p_worker_id
    and r.effective_from < p_effective_from
    and (r.effective_to is null or r.effective_to >= p_effective_from);

  insert into erp.worker_daily_rate_versions(
    worker_id, daily_rate, effective_from, effective_to, change_reason, created_by
  ) values (
    p_worker_id, p_daily_rate, p_effective_from,
    case when v_next_from is null then null else v_next_from - 1 end,
    p_reason, erp.current_app_user_id()
  ) returning id into v_new_id;

  update erp.contractor_workers w
  set daily_rate = coalesce(erp.worker_daily_rate_at(w.id, ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date), w.daily_rate),
      updated_by = erp.current_app_user_id()
  where w.id = p_worker_id;

  select jsonb_build_object(
    'worker_id', w.id,
    'rate_version_id', v_new_id,
    'daily_rate', p_daily_rate,
    'effective_from', p_effective_from,
    'effective_to', case when v_next_from is null then null else v_next_from - 1 end,
    'current_daily_rate', w.daily_rate,
    'row_version', w.row_version
  ) into v_response
  from erp.contractor_workers w
  where w.id = p_worker_id;

  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
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
  if v_status not in ('DRAFT','VALIDATING','READY') then raise exception 'Migration batch % cannot be staged while status is %',p_batch_id,v_status; end if;
  if p_source_row_no is null or p_source_row_no<=0 then raise exception 'source_row_no must be positive'; end if;
  if v_type not in ('BRAND','SIZE','MODEL','PRODUCT','CUSTOMER','SUPPLIER','CONTRACTOR','ACCESSORY_CATEGORY','MATERIAL','MATERIAL_ROLL','OPENING_BALANCE_ITEM','OPEN_PO') then
    raise exception 'Unsupported migration entity_type %',v_type;
  end if;
  insert into erp.migration_staging_rows(batch_id,entity_type,source_row_no,legacy_key,source_payload,normalized_payload,validation_status,validation_errors,updated_at)
  values (p_batch_id,v_type,p_source_row_no,nullif(trim(p_legacy_key),''),coalesce(p_source_payload,'{}'::jsonb),coalesce(p_normalized_payload,'{}'::jsonb),'PENDING','[]'::jsonb,statement_timestamp())
  on conflict (batch_id,entity_type,source_row_no) do update set
    legacy_key=excluded.legacy_key,source_payload=excluded.source_payload,normalized_payload=excluded.normalized_payload,
    validation_status='PENDING',validation_errors='[]'::jsonb,posted_entity_type=null,posted_entity_id=null,posted_at=null,updated_at=statement_timestamp()
  returning id into v_id;
  update erp.migration_batches set status='DRAFT',validated_at=null,error_message=null where id=p_batch_id;
  return v_id;
end;$function$;

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

CREATE OR REPLACE FUNCTION erp.sync_laundry_accrual(p_po_id uuid, p_effective_date date DEFAULT ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_old numeric(24,6):=0;
  v_new numeric(24,6):=0;
  v_delta numeric(24,6):=0;
  v_event uuid;
  v_journal uuid;
  v_abs numeric(24,2);
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('PO_HPP:'||p_po_id::text,0));
  select accrued_amount into v_old
  from erp.laundry_cost_accrual_state
  where po_id=p_po_id
  for update;
  v_old:=coalesce(v_old,0);
  v_new:=coalesce(erp.desired_laundry_accrual(p_po_id),0);
  v_delta:=v_new-v_old;
  if abs(v_delta)<=0.005 then
    insert into erp.laundry_cost_accrual_state(po_id,accrued_amount,updated_at)
    values(p_po_id,v_new,statement_timestamp())
    on conflict(po_id) do update set
      accrued_amount=excluded.accrued_amount,updated_at=statement_timestamp();
    return;
  end if;
  insert into erp.laundry_cost_accrual_events(
    po_id,old_amount,new_amount,delta_amount,effective_date
  ) values(p_po_id,v_old,v_new,v_delta,p_effective_date)
  returning id into v_event;
  v_abs:=round(abs(v_delta),2);
  if v_delta>0 then
    v_journal:=erp.post_journal(
      'LAUNDRY_ESTIMATE_ACCRUAL',v_event,p_effective_date,
      'Laundry estimate accrual',jsonb_build_array(
        jsonb_build_object('mapping_key','WIP','debit',v_abs,'credit',0,'po_id',p_po_id),
        jsonb_build_object('mapping_key','ACCRUED_MANUFACTURING','debit',0,'credit',v_abs,'po_id',p_po_id)
      )
    );
  else
    v_journal:=erp.post_journal(
      'LAUNDRY_ESTIMATE_ACCRUAL',v_event,p_effective_date,
      'Laundry estimate accrual reduction',jsonb_build_array(
        jsonb_build_object('mapping_key','ACCRUED_MANUFACTURING','debit',v_abs,'credit',0,'po_id',p_po_id),
        jsonb_build_object('mapping_key','WIP','debit',0,'credit',v_abs,'po_id',p_po_id)
      )
    );
  end if;
  update erp.laundry_cost_accrual_events
  set journal_entry_id=v_journal where id=v_event;
  insert into erp.laundry_cost_accrual_state(po_id,accrued_amount,updated_at)
  values(p_po_id,v_new,statement_timestamp())
  on conflict(po_id) do update set
    accrued_amount=excluded.accrued_amount,updated_at=statement_timestamp();
end
$function$;

CREATE OR REPLACE FUNCTION erp.sync_laundry_accrual_after_rate_change()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$ DECLARE v_po uuid;v_status text;v_date date; BEGIN IF NEW.estimated_rate_snapshot IS NOT DISTINCT FROM OLD.estimated_rate_snapshot THEN RETURN NEW; END IF; SELECT ld.po_id,ld.status,(ld.physical_at AT TIME ZONE 'Asia/Jakarta')::date INTO v_po,v_status,v_date FROM erp.laundry_deliveries ld WHERE ld.id=NEW.delivery_id; IF v_status NOT IN ('DRAFT','REVERSED') THEN PERFORM erp.sync_laundry_accrual(v_po,COALESCE(v_date,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date)); IF EXISTS (SELECT 1 FROM erp.fg_lots WHERE po_id=v_po) THEN PERFORM erp.rebuild_po_hpp(v_po,'Laundry estimate rate corrected'); PERFORM erp.propagate_conversion_hpp_for_po(v_po); PERFORM erp.sync_po_hpp_to_gl(v_po,COALESCE(v_date,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date)); END IF; END IF;RETURN NEW;END; $function$;

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
begin
  perform erp.require_internal();

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
      values(p_material_id,r.id,erp._cp3_business_date(statement_timestamp()),v_old,v_target,v_diff,v_counterpart,v_po,v_contractor)
      returning id into v_event;

      v_journal:=erp.post_journal('MATERIAL_COST_REVALUATION',v_event,erp._cp3_business_date(statement_timestamp()),
        'Automatic material moving-average recost: '||r.source_type,v_lines);
      update erp.material_cost_revaluation_events set journal_entry_id=v_journal where id=v_event;
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

CREATE OR REPLACE FUNCTION erp.sync_opening_hpp_after_fg_adjustment_status()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare r record;
begin
  if new.status is not distinct from old.status then return new; end if;
  for r in select distinct fai.lot_id from erp.fg_adjustment_items fai join erp.fg_lots fl on fl.id=fai.lot_id where fai.adjustment_id=new.id and fl.lot_origin='OPENING' and exists(select 1 from erp.opening_lot_hpp_gl_state s where s.lot_id=fl.id)
  loop perform erp.sync_opening_lot_hpp_to_gl(r.lot_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date); end loop;
  return new;
end;$function$;

CREATE OR REPLACE FUNCTION erp.sync_opening_hpp_after_return_status()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare r record;
begin
  if new.status is not distinct from old.status then return new; end if;
  for r in select distinct sri.lot_id from erp.sales_return_items sri join erp.fg_lots fl on fl.id=sri.lot_id where sri.return_id=new.id and fl.lot_origin='OPENING' and exists(select 1 from erp.opening_lot_hpp_gl_state s where s.lot_id=fl.id)
  loop perform erp.sync_opening_lot_hpp_to_gl(r.lot_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date); end loop;
  return new;
end;$function$;

CREATE OR REPLACE FUNCTION erp.sync_opening_hpp_after_sale_status()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare r record;
begin
  if new.status is not distinct from old.status then return new; end if;
  for r in select distinct a.lot_id from erp.sale_stock_allocations a join erp.sales_items si on si.id=a.sale_item_id join erp.fg_lots fl on fl.id=a.lot_id where si.sale_id=new.id and fl.lot_origin='OPENING' and exists(select 1 from erp.opening_lot_hpp_gl_state s where s.lot_id=fl.id)
  loop perform erp.sync_opening_lot_hpp_to_gl(r.lot_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date); end loop;
  return new;
end;$function$;

CREATE OR REPLACE FUNCTION erp.sync_opening_lot_hpp_to_gl(p_lot_id uuid, p_effective_date date DEFAULT ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  l erp.fg_lots%rowtype; s erp.opening_lot_hpp_gl_state%rowtype;
  h erp.hpp_versions%rowtype; v_baseline numeric; v_source_delta numeric;
  v_expected_delta numeric; v_current_qty numeric; v_base_fg numeric;
  v_net_sold_qty numeric; v_actual_cogs numeric; v_expense numeric; v_income numeric;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into l from erp.fg_lots where id=p_lot_id for update;
  if l.id is null or l.lot_origin<>'OPENING' then return; end if;
  select * into h from erp.hpp_versions where lot_id=l.id and is_current;
  if h.id is null then raise exception 'Opening current HPP is missing'; end if;
  select fm.unit_hpp_snapshot into v_baseline from erp.fg_stock_movements fm
  where fm.lot_id=l.id and fm.movement_type='OPENING'
  order by fm.physical_at,fm.system_created_at,fm.id limit 1;
  if v_baseline is null then raise exception 'Opening lot % has no source movement',l.lot_number; end if;
  if exists(select 1 from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id
    where a.source_lot_id=l.id and c.status='POSTED') then
    raise exception 'Opening HPP conversion requires a sourced descendant correction workflow';
  end if;
  select * into s from erp.opening_lot_hpp_gl_state where lot_id=l.id for update;
  v_expected_delta:=round(h.total_cost,2)
    -round(l.initial_qty_pcs*coalesce(s.current_hpp,v_baseline),2);
  select t.hpp_total_cost-b.hpp_total_cost into v_source_delta
  from erp.compute_non_po_product_hpp_targets_v2620f(l.product_id) t
  cross join lateral erp.compute_non_po_product_hpp_book_v2620f(l.product_id) b;
  if v_source_delta is distinct from v_expected_delta then
    raise exception 'OPENING_SOURCE_CHANGE_NOT_EXACT: product %, pending lot basis %, target/book source delta %',
      l.product_id,v_expected_delta,v_source_delta;
  end if;
  if v_source_delta<>0 then
    perform erp.post_journal('OPENING_HPP_SOURCE_V2620G',h.id,p_effective_date,
      'Source lot basis correction for '||l.lot_number||' / HPP version '||h.id,
      jsonb_build_array(
        jsonb_build_object('mapping_key','FG_INVENTORY',
          'debit',greatest(v_source_delta,0),'credit',greatest(-v_source_delta,0),'product_id',l.product_id),
        jsonb_build_object('mapping_key','OPENING_EQUITY',
          'debit',greatest(-v_source_delta,0),'credit',greatest(v_source_delta,0))
      ));
  end if;
  perform erp.sync_non_po_product_hpp_to_gl_v2620f(l.product_id,p_effective_date,
    'OPENING_HPP_LIFECYCLE_V2620G',h.id,'Exact rounded opening source and cumulative physical lifecycle');
  perform erp.assert_non_po_product_hpp_target_book_v2620f(l.product_id);

  -- Preserve the historical raw revaluation diagnostics and trigger-activation
  -- contract. These projections are not used as monetary posting authority:
  -- actual journals and F's cumulative source/target/book checks are.
  -- DRAFT reservations reduce sellable qty, not company ownership.
  select coalesce(sum(fm.qty_signed),0),coalesce(sum(fm.qty_signed*fm.unit_hpp_snapshot),0)
    into v_current_qty,v_base_fg from erp.fg_stock_movements fm where fm.lot_id=l.id;
  select v_current_qty+coalesce(sum(abs(fm.qty_signed)),0),
    v_base_fg+coalesce(sum(abs(fm.qty_signed)*fm.unit_hpp_snapshot),0)
    into v_current_qty,v_base_fg from erp.fg_stock_movements fm
    where fm.lot_id=l.id and fm.movement_type='SALE_RESERVE'
      and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id);
  select coalesce(sum(a.qty_pcs),0),coalesce(sum(a.qty_pcs*a.unit_hpp_snapshot),0)
    into v_net_sold_qty,v_actual_cogs from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id join erp.sales_headers sh on sh.id=i.sale_id
    where a.lot_id=l.id and sh.status in('POSTED','PARTIAL_PAID','PAID');
  select v_net_sold_qty-coalesce(sum(i.qty_pcs),0),v_actual_cogs-coalesce(sum(i.qty_pcs*i.unit_hpp_snapshot),0)
    into v_net_sold_qty,v_actual_cogs from erp.sales_return_items i
    join erp.sales_returns rh on rh.id=i.return_id where i.lot_id=l.id and rh.status='POSTED';
  select coalesce(sum(case when i.qty_signed<0 then -i.qty_signed*(h.hpp_per_pcs-i.unit_hpp_snapshot) else 0 end),0),
    coalesce(sum(case when i.qty_signed>0 then i.qty_signed*(h.hpp_per_pcs-i.unit_hpp_snapshot) else 0 end),0)
    into v_expense,v_income from erp.fg_adjustment_items i
    join erp.fg_adjustments a on a.id=i.adjustment_id where i.lot_id=l.id and a.status='POSTED';
  insert into erp.opening_lot_hpp_gl_state(lot_id,current_hpp,fg_revaluation,cogs_revaluation,
    expense_revaluation,income_revaluation,equity_revaluation,updated_at)
  values(l.id,h.hpp_per_pcs,v_current_qty*h.hpp_per_pcs-v_base_fg,
    v_net_sold_qty*h.hpp_per_pcs-v_actual_cogs,v_expense,v_income,
    l.initial_qty_pcs*(h.hpp_per_pcs-v_baseline),statement_timestamp())
  on conflict(lot_id) do update set current_hpp=excluded.current_hpp,
    fg_revaluation=excluded.fg_revaluation,cogs_revaluation=excluded.cogs_revaluation,
    expense_revaluation=excluded.expense_revaluation,income_revaluation=excluded.income_revaluation,
    equity_revaluation=excluded.equity_revaluation,updated_at=statement_timestamp();
end
$function$;

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
begin
  perform erp.require_internal();
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
    update erp.po_hpp_gl_events set journal_entry_id=v_journal where id=v_event;
  end if;

  insert into erp.po_hpp_gl_state(po_id,base_output_qty,hpp_total_cost,fg_value,cogs_value,other_out_value,updated_at)
  values(p_po_id,v_target_qty,v_target_hpp,v_target_fg,v_target_cogs,v_target_other,statement_timestamp())
  on conflict(po_id) do update set base_output_qty=excluded.base_output_qty,
    hpp_total_cost=excluded.hpp_total_cost,fg_value=excluded.fg_value,
    cogs_value=excluded.cogs_value,other_out_value=excluded.other_out_value,updated_at=statement_timestamp();
end
$function$;

CREATE OR REPLACE FUNCTION erp.touch_laundry_receipt_from_bs_allocation()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare v_line uuid:=case when tg_op='DELETE' then old.receipt_line_id else new.receipt_line_id end;
begin
  update erp.laundry_receipts lr
  set updated_at=statement_timestamp()
  from erp.laundry_receipt_lines lrl
  where lrl.id=v_line and lr.id=lrl.receipt_id and lr.status='DRAFT';
  if tg_op='DELETE' then return old; else return new; end if;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.touch_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
BEGIN
  NEW.updated_at := statement_timestamp();
  RETURN NEW;
END;
$function$;

CREATE OR REPLACE VIEW erp.v_accessory_category_current_cost WITH (security_invoker='true') AS
 SELECT id AS category_id,
    category_code,
    category_name,
    base_uom_code,
    erp.accessory_category_weighted_avg_cost_at(id, statement_timestamp()) AS weighted_avg_cost_per_base_uom
   FROM erp.accessory_categories c
  WHERE (is_active = true);

CREATE OR REPLACE VIEW erp.v_accessory_hpp_setup WITH (security_invoker='true') AS
 SELECT p.id AS product_id,
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
            WHEN (abv.id IS NULL) THEN 'MISSING_BOM'::text
            WHEN (abi.id IS NULL) THEN 'NO_ACCESSORY'::text
            ELSE 'CONFIGURED'::text
        END AS setup_state,
    count(abi.id) OVER (PARTITION BY p.id, abv.id) AS bom_item_count
   FROM (((erp.v_products_current p
     LEFT JOIN erp.accessory_bom_versions abv ON (((abv.product_id = p.identity_root_id) AND (abv.is_active = true) AND (abv.effective_from <= statement_timestamp()) AND ((abv.effective_to IS NULL) OR (abv.effective_to > statement_timestamp())))))
     LEFT JOIN erp.accessory_bom_items abi ON ((abi.bom_version_id = abv.id)))
     LEFT JOIN erp.accessory_categories ac ON ((ac.id = abi.category_id)));

CREATE OR REPLACE VIEW erp.v_accessory_master_browser WITH (security_invoker='true') AS
 WITH stock AS (
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
    concat_ws(' '::text, m.material_sku, m.material_name, ac.category_code, ac.category_name) AS search_text
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
  WHERE ((m.material_type)::text = 'ACCESSORY'::text);

CREATE OR REPLACE VIEW erp.v_accessory_price_browser WITH (security_invoker='true') AS
 SELECT p.id AS price_version_id,
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
    concat_ws(' '::text, ac.category_code, ac.category_name, c.contractor_code, c.contractor_name, p.selling_uom_code) AS search_text
   FROM ((erp.contractor_accessory_price_versions p
     JOIN erp.accessory_categories ac ON ((ac.id = p.category_id)))
     LEFT JOIN erp.contractors c ON ((c.id = p.contractor_id)));

CREATE OR REPLACE VIEW erp.v_current_product_prices WITH (security_invoker='true') AS
 SELECT DISTINCT ON (product_id) product_id,
    price,
    effective_from
   FROM erp.product_price_versions ppv
  WHERE ((effective_from <= statement_timestamp()) AND ((effective_to IS NULL) OR (effective_to > statement_timestamp())))
  ORDER BY product_id, effective_from DESC, created_at DESC;

CREATE OR REPLACE VIEW erp.v_fabric_master_current_benchmark WITH (security_invoker='true') AS
 SELECT m.id AS material_id,
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
  WHERE ((m.material_type)::text = 'FABRIC'::text);

CREATE OR REPLACE VIEW erp.v_material_purchase_liability_status WITH (security_invoker='true') AS
 SELECT h.id AS purchase_id,
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
          WHERE ((p.purchase_id = h.id) AND ((p.status)::text = 'POSTED'::text))), (0)::numeric) AS paid_amount,
    GREATEST((erp.material_purchase_final_ap_total(h.id) - COALESCE(( SELECT sum(p.amount) AS sum
           FROM erp.supplier_payments p
          WHERE ((p.purchase_id = h.id) AND ((p.status)::text = 'POSTED'::text))), (0)::numeric)), (0)::numeric) AS final_ap_outstanding,
        CASE
            WHEN ((erp.material_purchase_grni_total(h.id) > 0.005) AND (erp.material_purchase_final_ap_total(h.id) > 0.005)) THEN 'PARTIAL_INVOICE'::text
            WHEN (erp.material_purchase_grni_total(h.id) > 0.005) THEN 'KASBON_BELUM_DITERIMA_ESTIMASI_KEWAJIBAN'::text
            WHEN (erp.material_purchase_final_ap_total(h.id) > 0.005) THEN 'FINAL_AP'::text
            ELSE 'NO_LIABILITY'::text
        END AS liability_state,
    ( SELECT string_agg(DISTINCT (ih.invoice_number)::text, ', '::text ORDER BY (ih.invoice_number)::text) AS string_agg
           FROM ((erp.material_supplier_invoice_lines il
             JOIN erp.material_supplier_invoices ih ON ((ih.id = il.invoice_id)))
             JOIN erp.material_purchase_items pi ON ((pi.id = il.purchase_item_id)))
          WHERE ((pi.purchase_id = h.id) AND ((ih.status)::text = 'POSTED'::text))) AS active_invoice_numbers,
    ( SELECT min(ih.due_date) AS min
           FROM ((erp.material_supplier_invoice_lines il
             JOIN erp.material_supplier_invoices ih ON ((ih.id = il.invoice_id)))
             JOIN erp.material_purchase_items pi ON ((pi.id = il.purchase_item_id)))
          WHERE ((pi.purchase_id = h.id) AND ((ih.status)::text = 'POSTED'::text))) AS earliest_due_date,
        CASE
            WHEN (erp.material_purchase_grni_total(h.id) > 0.005) THEN GREATEST((((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date - ((h.physical_at) AT TIME ZONE 'Asia/Jakarta')::date), 0)
            ELSE 0
        END AS unfinalized_days,
    h.row_version,
    h.created_at,
    h.updated_at,
    concat_ws(' '::text, h.purchase_number, s.supplier_code, s.supplier_name, h.status) AS search_text
   FROM ((erp.material_purchase_headers h
     LEFT JOIN erp.suppliers s ON ((s.id = h.supplier_id)))
     LEFT JOIN erp.material_purchase_items i ON ((i.purchase_id = h.id)))
  GROUP BY h.id, s.id;

CREATE OR REPLACE VIEW erp.v_material_supplier_invoice_browser WITH (security_invoker='true') AS
 SELECT h.id AS supplier_invoice_id,
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
            ELSE GREATEST((((h.received_at) AT TIME ZONE 'Asia/Jakarta')::date - ((min(ph.physical_at)) AT TIME ZONE 'Asia/Jakarta')::date), 0)
        END AS invoice_delay_days,
    h.row_version,
    h.created_at,
    h.updated_at,
    h.posted_at,
    h.reversed_at,
    concat_ws(' '::text, h.invoice_number, s.supplier_code, s.supplier_name, h.status, h.notes) AS search_text
   FROM ((((erp.material_supplier_invoices h
     JOIN erp.suppliers s ON ((s.id = h.supplier_id)))
     LEFT JOIN erp.material_supplier_invoice_lines l ON ((l.invoice_id = h.id)))
     LEFT JOIN erp.material_purchase_items i ON ((i.id = l.purchase_item_id)))
     LEFT JOIN erp.material_purchase_headers ph ON ((ph.id = i.purchase_id)))
  GROUP BY h.id, s.id;

CREATE OR REPLACE VIEW erp.v_payroll_nota_browser WITH (security_invoker='true') AS
 SELECT n.id AS payroll_id,
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
    ((n.status)::text = ANY (ARRAY[('DRAFT'::character varying)::text, ('CALCULATED'::character varying)::text, ('REVIEW'::character varying)::text])) AS can_merge,
    ((n.status)::text = ANY (ARRAY[('APPROVED'::character varying)::text, ('PAID'::character varying)::text, ('REVERSED'::character varying)::text])) AS is_locked,
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
          WHERE ((q.contractor_id = n.contractor_id) AND (((q.eligible_at) AT TIME ZONE 'Asia/Jakarta')::date <= n.period_end))) e ON (true));

CREATE OR REPLACE VIEW erp.v_product_price_current WITH (security_invoker='true') AS
 SELECT p.id AS product_id,
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
         LIMIT 1) pp ON (true));

CREATE OR REPLACE VIEW erp.v_products_current WITH (security_invoker='true') AS
 SELECT id,
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
  WHERE ((is_active = true) AND (effective_from <= statement_timestamp()) AND ((effective_to IS NULL) OR (effective_to > statement_timestamp())));

CREATE OR REPLACE VIEW erp.v_products_sellable WITH (security_invoker='true') AS
 WITH stock AS (
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
  WHERE (((p.is_active = true) AND (p.effective_from <= statement_timestamp()) AND ((p.effective_to IS NULL) OR (p.effective_to > statement_timestamp()))) OR (COALESCE(s.stock_pcs, (0)::bigint) > 0));

CREATE OR REPLACE VIEW erp.v_supplier_ap_aging WITH (security_invoker='true') AS
 WITH ap AS (
         SELECT h.id AS purchase_id,
            h.purchase_number,
            h.supplier_id,
            s.supplier_name,
            (COALESCE(( SELECT string_agg(DISTINCT (ih.invoice_number)::text, ', '::text ORDER BY (ih.invoice_number)::text) AS string_agg
                   FROM ((erp.material_supplier_invoice_lines il
                     JOIN erp.material_supplier_invoices ih ON ((ih.id = il.invoice_id)))
                     JOIN erp.material_purchase_items pi ON ((pi.id = il.purchase_item_id)))
                  WHERE ((pi.purchase_id = h.id) AND ((ih.status)::text = 'POSTED'::text))), (h.supplier_invoice_number)::text))::character varying(100) AS supplier_invoice_number,
            h.physical_at,
            COALESCE(( SELECT min(ih.due_date) AS min
                   FROM ((erp.material_supplier_invoice_lines il
                     JOIN erp.material_supplier_invoices ih ON ((ih.id = il.invoice_id)))
                     JOIN erp.material_purchase_items pi ON ((pi.id = il.purchase_item_id)))
                  WHERE ((pi.purchase_id = h.id) AND ((ih.status)::text = 'POSTED'::text))), h.due_date) AS due_date,
            erp.material_purchase_final_ap_total(h.id) AS payable_amount,
            COALESCE(( SELECT sum(sp.amount) AS sum
                   FROM erp.supplier_payments sp
                  WHERE ((sp.purchase_id = h.id) AND ((sp.status)::text = 'POSTED'::text))), (0)::numeric) AS paid_amount
           FROM (erp.material_purchase_headers h
             LEFT JOIN erp.suppliers s ON ((s.id = h.supplier_id)))
          WHERE ((h.status)::text = 'POSTED'::text)
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
            ELSE GREATEST((((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date - due_date), 0)
        END AS days_overdue,
        CASE
            WHEN (payable_amount <= paid_amount) THEN 'PAID'::text
            WHEN ((due_date IS NULL) OR (((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date <= due_date)) THEN 'CURRENT'::text
            WHEN ((((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date - due_date) <= 30) THEN '1_30'::text
            WHEN ((((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date - due_date) <= 60) THEN '31_60'::text
            WHEN ((((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date - due_date) <= 90) THEN '61_90'::text
            ELSE '90_PLUS'::text
        END AS aging_bucket
   FROM ap
  WHERE ((payable_amount > 0.005) OR (paid_amount > 0.005));

alter table erp.accessory_bom_versions alter column effective_from set default statement_timestamp();
alter table erp.accessory_bom_versions alter column created_at set default statement_timestamp();
alter table erp.accessory_categories alter column created_at set default statement_timestamp();
alter table erp.accessory_categories alter column updated_at set default statement_timestamp();
alter table erp.accessory_category_uom_conversions alter column effective_from set default statement_timestamp();
alter table erp.accessory_category_uom_conversions alter column created_at set default statement_timestamp();
alter table erp.account_daily_balances alter column updated_at set default statement_timestamp();
alter table erp.accounting_period_control alter column updated_at set default statement_timestamp();
alter table erp.app_users alter column created_at set default statement_timestamp();
alter table erp.app_users alter column updated_at set default statement_timestamp();
alter table erp.attendance_records alter column created_at set default statement_timestamp();
alter table erp.attendance_records alter column updated_at set default statement_timestamp();
alter table erp.audit_logs alter column changed_at set default statement_timestamp();
alter table erp.brands alter column created_at set default statement_timestamp();
alter table erp.brands alter column updated_at set default statement_timestamp();
alter table erp.bs_cases alter column created_at set default statement_timestamp();
alter table erp.bs_cases alter column updated_at set default statement_timestamp();
alter table erp.bs_resolutions alter column created_at set default statement_timestamp();
alter table erp.chart_accounts alter column created_at set default statement_timestamp();
alter table erp.contractor_accessory_price_versions alter column effective_from set default statement_timestamp();
alter table erp.contractor_accessory_price_versions alter column created_at set default statement_timestamp();
alter table erp.contractor_accessory_reimbursement_entitlements alter column created_at set default statement_timestamp();
alter table erp.contractor_material_issues alter column created_at set default statement_timestamp();
alter table erp.contractor_material_issues alter column updated_at set default statement_timestamp();
alter table erp.contractor_material_price_versions alter column effective_from set default statement_timestamp();
alter table erp.contractor_material_price_versions alter column created_at set default statement_timestamp();
alter table erp.contractor_work_rates alter column effective_from set default statement_timestamp();
alter table erp.contractor_work_rates alter column created_at set default statement_timestamp();
alter table erp.contractor_workers alter column created_at set default statement_timestamp();
alter table erp.contractor_workers alter column updated_at set default statement_timestamp();
alter table erp.contractors alter column created_at set default statement_timestamp();
alter table erp.contractors alter column updated_at set default statement_timestamp();
alter table erp.cost_adjustments alter column entered_at set default statement_timestamp();
alter table erp.cost_recalc_queue alter column queued_at set default statement_timestamp();
alter table erp.customer_user_access alter column created_at set default statement_timestamp();
alter table erp.customers alter column created_at set default statement_timestamp();
alter table erp.customers alter column updated_at set default statement_timestamp();
alter table erp.cutting_batches alter column created_at set default statement_timestamp();
alter table erp.cutting_batches alter column updated_at set default statement_timestamp();
alter table erp.cutting_groups alter column created_at set default statement_timestamp();
alter table erp.cutting_groups alter column updated_at set default statement_timestamp();
alter table erp.cutting_qty_correction_lines alter column created_at set default statement_timestamp();
alter table erp.cutting_qty_corrections alter column created_at set default statement_timestamp();
alter table erp.fabric_benchmark_price_versions alter column created_at set default statement_timestamp();
alter table erp.fabric_master_profiles alter column created_at set default statement_timestamp();
alter table erp.fabric_master_profiles alter column updated_at set default statement_timestamp();
alter table erp.fg_accessory_cost_snapshots alter column snapshotted_at set default statement_timestamp();
alter table erp.fg_adjustments alter column created_at set default statement_timestamp();
alter table erp.fg_adjustments alter column updated_at set default statement_timestamp();
alter table erp.fg_inventory_balances alter column updated_at set default statement_timestamp();
alter table erp.fg_lots alter column created_at set default statement_timestamp();
alter table erp.hpp_version_components alter column created_at set default statement_timestamp();
alter table erp.hpp_versions alter column calculated_at set default statement_timestamp();
alter table erp.idempotency_requests alter column created_at set default statement_timestamp();
alter table erp.idempotency_requests alter column updated_at set default statement_timestamp();
alter table erp.idempotency_requests alter column expires_at set default (statement_timestamp() + '30 days'::interval);
alter table erp.journal_entries alter column posting_at set default statement_timestamp();
alter table erp.journal_entries alter column created_at set default statement_timestamp();
alter table erp.laundry_claims alter column opened_at set default statement_timestamp();
alter table erp.laundry_cost_accrual_events alter column created_at set default statement_timestamp();
alter table erp.laundry_cost_accrual_state alter column updated_at set default statement_timestamp();
alter table erp.laundry_deliveries alter column created_at set default statement_timestamp();
alter table erp.laundry_deliveries alter column updated_at set default statement_timestamp();
alter table erp.laundry_receipt_bs_product_allocations alter column created_at set default statement_timestamp();
alter table erp.laundry_receipts alter column created_at set default statement_timestamp();
alter table erp.laundry_receipts alter column updated_at set default statement_timestamp();
alter table erp.laundry_vendor_rate_versions alter column effective_from set default statement_timestamp();
alter table erp.laundry_vendor_rate_versions alter column created_at set default statement_timestamp();
alter table erp.laundry_vendors alter column created_at set default statement_timestamp();
alter table erp.laundry_vendors alter column updated_at set default statement_timestamp();
alter table erp.locations alter column created_at set default statement_timestamp();
alter table erp.material_adjustments alter column created_at set default statement_timestamp();
alter table erp.material_adjustments alter column updated_at set default statement_timestamp();
alter table erp.material_cost_history alter column recorded_at set default statement_timestamp();
alter table erp.material_cost_revaluation_events alter column created_at set default statement_timestamp();
alter table erp.material_cost_revaluation_state alter column updated_at set default statement_timestamp();
alter table erp.material_purchase_cost_corrections alter column created_at set default statement_timestamp();
alter table erp.material_purchase_headers alter column created_at set default statement_timestamp();
alter table erp.material_purchase_headers alter column updated_at set default statement_timestamp();
alter table erp.material_rolls alter column created_at set default statement_timestamp();
alter table erp.material_rolls alter column updated_at set default statement_timestamp();
alter table erp.material_supplier_returns alter column created_at set default statement_timestamp();
alter table erp.material_supplier_returns alter column updated_at set default statement_timestamp();
alter table erp.material_transfer_items alter column created_at set default statement_timestamp();
alter table erp.material_transfers alter column created_at set default statement_timestamp();
alter table erp.material_transfers alter column updated_at set default statement_timestamp();
alter table erp.materials alter column created_at set default statement_timestamp();
alter table erp.materials alter column updated_at set default statement_timestamp();
alter table erp.migration_batches alter column created_at set default statement_timestamp();
alter table erp.migration_staging_rows alter column created_at set default statement_timestamp();
alter table erp.migration_staging_rows alter column updated_at set default statement_timestamp();
alter table erp.misc_finance_transactions alter column created_at set default statement_timestamp();
alter table erp.misc_finance_transactions alter column updated_at set default statement_timestamp();
alter table erp.opening_balance_headers alter column created_at set default statement_timestamp();
alter table erp.opening_financial_corrections alter column created_at set default statement_timestamp();
alter table erp.opening_hpp_corrections alter column created_at set default statement_timestamp();
alter table erp.opening_lot_hpp_gl_state alter column updated_at set default statement_timestamp();
alter table erp.opening_subledger_balances alter column created_at set default statement_timestamp();
alter table erp.opening_subledger_balances alter column updated_at set default statement_timestamp();
alter table erp.opening_subledger_settlements alter column created_at set default statement_timestamp();
alter table erp.opening_subledger_settlements alter column updated_at set default statement_timestamp();
alter table erp.payroll_settlements alter column created_at set default statement_timestamp();
alter table erp.payroll_settlements alter column updated_at set default statement_timestamp();
alter table erp.payroll_settlements alter column payment_date set default ((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date;
alter table erp.po_accessory_bom_commitments alter column created_at set default statement_timestamp();
alter table erp.po_hpp_gl_events alter column created_at set default statement_timestamp();
alter table erp.po_hpp_gl_state alter column updated_at set default statement_timestamp();
alter table erp.po_wip_close_events alter column created_at set default statement_timestamp();
alter table erp.po_work_component_snapshots alter column created_at set default statement_timestamp();
alter table erp.product_conversions alter column created_at set default statement_timestamp();
alter table erp.product_conversions alter column updated_at set default statement_timestamp();
alter table erp.product_models alter column created_at set default statement_timestamp();
alter table erp.product_models alter column updated_at set default statement_timestamp();
alter table erp.product_price_versions alter column effective_from set default statement_timestamp();
alter table erp.product_price_versions alter column created_at set default statement_timestamp();
alter table erp.production_orders alter column created_at set default statement_timestamp();
alter table erp.production_orders alter column updated_at set default statement_timestamp();
alter table erp.products alter column created_at set default statement_timestamp();
alter table erp.products alter column updated_at set default statement_timestamp();
alter table erp.qc_inspections alter column created_at set default statement_timestamp();
alter table erp.qc_inspections alter column updated_at set default statement_timestamp();
alter table erp.rework_orders alter column created_at set default statement_timestamp();
alter table erp.rework_orders alter column updated_at set default statement_timestamp();
alter table erp.sales_headers alter column created_at set default statement_timestamp();
alter table erp.sales_headers alter column updated_at set default statement_timestamp();
alter table erp.sales_payments alter column created_at set default statement_timestamp();
alter table erp.sales_returns alter column created_at set default statement_timestamp();
alter table erp.schema_migrations alter column installed_at set default statement_timestamp();
alter table erp.scrap_batches alter column created_at set default statement_timestamp();
alter table erp.scrap_sales alter column created_at set default statement_timestamp();
alter table erp.supplier_payments alter column created_at set default statement_timestamp();
alter table erp.suppliers alter column created_at set default statement_timestamp();
alter table erp.system_release_info alter column installed_at set default statement_timestamp();
alter table erp.uom_definitions alter column created_at set default statement_timestamp();
alter table erp.vendor_invoices alter column received_at set default statement_timestamp();
alter table erp.vendor_invoices alter column created_at set default statement_timestamp();
alter table erp.vendor_invoices alter column updated_at set default statement_timestamp();
alter table erp.vendor_payments alter column created_at set default statement_timestamp();
alter table erp.wip_stage_events alter column created_at set default statement_timestamp();
alter table erp.work_bom_versions alter column effective_from set default statement_timestamp();
alter table erp.work_bom_versions alter column created_at set default statement_timestamp();
alter table erp.work_completion_events alter column created_at set default statement_timestamp();
alter table erp.work_completion_events alter column updated_at set default statement_timestamp();
alter table erp.work_components alter column created_at set default statement_timestamp();


do $installed_v2620ac$
declare r record;c record;v_live_sha text;v_expected_sha text;v_owner text;
  v_acl text[];v_reloptions text[];v_expression text;v_rls boolean;
begin
  update erp.cp6_v2620ac_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
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
      raise exception 'AC_INSTALLED_FUNCTION_MISMATCH: %',r.identity;
    end if;
  end loop;

  for r in select * from pg_temp.cp6_ac_expected_views loop
    v_expected_sha:=pg_temp.cp6_ac_normalized_view_sha256(r.after_body);
    select encode(extensions.digest(convert_to(btrim(pg_get_viewdef(catalog_rel.oid,false),E' \n\t\r;'),'UTF8'),'sha256'),'hex'),
      pg_get_userbyid(catalog_rel.relowner),
      case when catalog_rel.relacl is null then null else
        array(select a::text from unnest(catalog_rel.relacl) a order by a::text) end,
      case when catalog_rel.reloptions is null then null else
        array(select x from unnest(catalog_rel.reloptions) x order by x) end,
      catalog_rel.relrowsecurity
    into v_live_sha,v_owner,v_acl,v_reloptions,v_rls
    from pg_class catalog_rel
    where catalog_rel.oid=r.identity::regclass and catalog_rel.relkind='v';
    if encode(extensions.digest(convert_to(r.after_body,'UTF8'),'sha256'),'hex')
         is distinct from r.after_sha256
       or v_live_sha is distinct from v_expected_sha
       or v_owner is distinct from r.owner_name
       or v_acl is distinct from r.acl
       or v_reloptions is distinct from r.reloptions
       or v_rls is distinct from r.rls then
      raise exception 'AC_INSTALLED_VIEW_MISMATCH: %',r.identity using detail=format(
        'source=%s body=%s owner=%s acl=%s options=%s rls=%s',
        encode(extensions.digest(convert_to(r.after_body,'UTF8'),'sha256'),'hex')
          is not distinct from r.after_sha256,
        v_live_sha is not distinct from v_expected_sha,
        v_owner is not distinct from r.owner_name,
        v_acl is not distinct from r.acl,
        v_reloptions is not distinct from r.reloptions,
        v_rls is not distinct from r.rls);
    end if;
    update erp.cp6_v2620ac_relation_rollback_capsule set installed_definition_sha256=v_live_sha
    where object_kind='VIEW' and object_identity=r.identity;
  end loop;

  for r in select * from pg_temp.cp6_ac_expected_defaults loop
    select pg_get_expr(d.adbin,d.adrelid),pg_get_userbyid(catalog_rel.relowner),
      case when catalog_rel.relacl is null then null else
        array(select x::text from unnest(catalog_rel.relacl) x order by x::text) end,
      catalog_rel.relrowsecurity
    into v_expression,v_owner,v_acl,v_rls
    from pg_class catalog_rel
    join pg_namespace n on n.oid=catalog_rel.relnamespace
    join pg_attribute a on a.attrelid=catalog_rel.oid and a.attname=r.column_name
    left join pg_attrdef d on d.adrelid=catalog_rel.oid and d.adnum=a.attnum
    where n.nspname='erp' and catalog_rel.relname=r.table_name
      and catalog_rel.relkind in('r','p');
    if v_expression is distinct from r.after_expression
       or v_owner is distinct from r.owner_name
       or v_acl is distinct from r.acl
       or v_rls is distinct from r.rls then
      raise exception 'AC_INSTALLED_DEFAULT_MISMATCH: %',r.identity;
    end if;
    update erp.cp6_v2620ac_relation_rollback_capsule set installed_definition_sha256=
      encode(extensions.digest(convert_to(v_expression,'UTF8'),'sha256'),'hex')
    where object_kind='COLUMN_DEFAULT' and object_identity=r.identity;
  end loop;
end
$installed_v2620ac$;


do $boundary_v2620ac$
declare v_table text;v_hash text;v_snapshot jsonb:='{}';
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='erp' and c.relkind in('r','p')
      and c.relname not in('schema_migrations','cp6_v2620ac_rollback_capsule',
        'cp6_v2620ac_relation_rollback_capsule') order by c.relname
  loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  if (select count(*) from jsonb_object_keys(v_snapshot))<>214 then
    raise exception 'AC_FULL_ERP_BOUNDARY_CARDINALITY expected214 actual%',
      (select count(*) from jsonb_object_keys(v_snapshot));
  end if;
  update erp.cp6_v2620ac_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620ac$;

insert into erp.schema_migrations(version,description)
values('v2.6.20ac','Complete CP6 temporal surface: Jakarta statement-date semantics, explicit instant-to-date conversion, stable current views, and operational statement timestamps');
commit;
