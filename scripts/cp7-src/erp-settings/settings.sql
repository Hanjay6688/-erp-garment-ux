-- R3-03 (owner D16-1, 16 Okt 2026: "selesain biar gausa sembunyiin"): the Pengaturan ERP screen (menu admin-settings) in the
-- Enteng build. One bounded read facade over the owner policy settings of the accessory workflow (BC: ACC-DEC01, ACC-DEC03..07,
-- ERP-DEC02; erp.bc_policy_settings_v1 + erp.bc_policy_setting_events_v1) and of the laundry workflow (BD: LAU-DEC01..06;
-- erp.bd_policy_settings_v1 + erp.bd_policy_setting_events_v1), plus the official cutover date (cp7_cutover, read only; it is
-- changed on Impor data awal). It writes nothing (business_DML false). Every change goes through the accepted Native writers the
-- Aksesori and Laundry pages already call: erp_save_accessory_service_action_v1 / erp_save_laundry_bd_action_v1 with action
-- SET_POLICY (owner only, settings.erp.manage, expected version, reason, request id, idempotent, audited). No Native definition
-- or grant changes; the schema is owned by cp7_erp_settings_read and dropped with it on uninstall.
--
-- Access: an authenticated, allowed ERP user with settings.erp.view (the access catalog key of admin-settings), else 42501
-- CP7_ERP_SETTINGS_DENIED. A family is read only by a user who also holds that family's Native read key
-- (warehouse.accessory.view for erp.get_accessory_service_workspace_v1, production.laundry.view for erp.get_laundry_bd_workspace_v1),
-- so this page never shows more than those pages. Values, reasons, who changed them, the pick lists and the cutover date are for
-- OWNER/ADMIN only (the accessory workspace shows policy values to OWNER/ADMIN only; the cutover workspace is OWNER/ADMIN only;
-- the laundry values are kept to the same OWNER/ADMIN rule here). can_set repeats the Native writers' own predicates: accessory =
-- OWNER and settings.erp.manage and warehouse.accessory.view (the router's first check); laundry = OWNER and settings.erp.manage
-- and an active ERP user. The texts are the ones the Aksesori/Laundry pages and the readiness summary show
-- (src/accessoryService.ts POLICY_LABEL, src/laundryBd.ts LAU_POLICY_LABEL, src/cp6Readiness.ts POLICY_EFFECT/policyStatus).
create role cp7_erp_settings_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_erp_settings authorization cp7_erp_settings_read;
revoke all on schema cp7_erp_settings from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_erp_settings to postgres;

-- Fixed list of the owner policies with the texts the existing pages show; sort_no follows ACCESSORY_POLICY_KEYS/LAU_POLICY_KEYS.
create function cp7_erp_settings.catalog()
returns table(family text,policy_key text,native_key text,sort_no integer,label text,pending_effect text,owner_choice boolean)
language sql immutable security definer set search_path='' as $$
 select * from(values
  ('ACCESSORY','ACC-DEC01','ACC_DEC01',1,'Garis waktu kembali & periksa','Tanggal fisik dan tanggal pencatatan tetap terpisah. Transaksi tidak tertahan.',false),
  ('ACCESSORY','ACC-DEC03','ACC_DEC03',2,'Nilai titipan belum dinilai','Penilaian barang titipan menunggu akun tujuan dan batas nilai. Barang tetap dapat diterima dan diperiksa.',false),
  ('ACCESSORY','ACC-DEC04','ACC_DEC04',3,'Akun biaya pemakaian per tujuan','Pemakaian untuk servis pelanggan atau perbaikan barang jadi menunggu akun beban. Pemakaian pabrik tetap berjalan.',false),
  ('ACCESSORY','ACC-DEC05','ACC_DEC05',4,'Retur nota mandor yang sudah dibayar','Kredit retur nota menunggu pengaturan. Owner sudah memilih barang layak; sisa kredit dibayar sekali lewat payroll berikutnya.',true),
  ('ACCESSORY','ACC-DEC06','ACC_DEC06',5,'Pembulatan nota ke rupiah','Pembulatan nota menunggu pilihan akun selisih naik dan turun.',false),
  ('ACCESSORY','ACC-DEC07','ACC_DEC07',6,'Batas persetujuan owner & petugas area','Owner memilih tanpa persetujuan tambahan sementara. Sebelum diterapkan, biaya bernilai tetap perlu owner/admin.',true),
  ('ACCESSORY','ERP-DEC02','ERP_DEC02',7,'Kategori gratis mandor Special','Baris gratis menunggu daftar kategori yang diizinkan owner. Harga yang belum diketahui tidak dianggap gratis.',false),
  ('LAUNDRY','LAU-DEC01','LAU_DEC01',1,'Satuan harga selain per PCS (borongan, minimum)','Tarif per PCS tetap berjalan. Borongan dan minimum hanya dipakai setelah owner mengizinkannya.',false),
  ('LAUNDRY','LAU-DEC02','LAU_DEC02',2,'Qty yang boleh ditagih vendor','Posting invoice menunggu keputusan hasil baik, BS, atau cuci gagal yang boleh ditagih vendor. Draf dapat disiapkan.',false),
  ('LAUNDRY','LAU-DEC03','LAU_DEC03',3,'Diskon, tambahan, pajak, pembulatan invoice','Diskon, tambahan, pajak, dan pembulatan invoice menunggu aturan owner bila digunakan.',false),
  ('LAUNDRY','LAU-DEC04','LAU_DEC04',4,'Jual barang yang harga laundrynya belum diketahui','Owner mengizinkan penjualan dengan HPP belum final. Sebelum diterapkan, harga laundry yang belum diketahui menahan penjualan.',true),
  ('LAUNDRY','LAU-DEC05','LAU_DEC05',5,'Tarif khusus model / ukuran / warna','Tarif khusus sengaja tidak diaktifkan. Tarif vendor, proses, dan paket biasa tetap berjalan.',false),
  ('LAUNDRY','LAU-DEC06','LAU_DEC06',6,'Selisih invoice dan koreksi sesudah bayar','Posting invoice menunggu penerapan keputusan owner: selisih masuk biaya produk dan koreksi sesudah bayar memakai dokumen tertaut. Draf dapat disiapkan.',true)
 )k(family,policy_key,native_key,sort_no,label,pending_effect,owner_choice)
$$;

create function cp7_erp_settings.access_now()
returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare v_access jsonb;
begin
 if auth.uid() is null or coalesce(auth.jwt()->>'role','') is distinct from 'authenticated' then
  raise exception using errcode='42501',message='CP7_ERP_SETTINGS_DENIED';end if;
 v_access:=erp.get_my_access_v1();
 if v_access->'allowed' is distinct from 'true'::jsonb or not erp.has_permission('settings.erp.view') then
  raise exception using errcode='42501',message='CP7_ERP_SETTINGS_DENIED';end if;
 return v_access;
end $$;

create function cp7_erp_settings.stamp(p_at timestamptz)
returns text
language sql immutable security definer set search_path='' as $$
 select to_char(p_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
$$;

-- The user name behind a set_by id (null stays null: the fail-closed default row was never changed by a person).
create function cp7_erp_settings.user_name(p_user uuid)
returns text
language sql stable security definer set search_path='' as $$
 select case when p_user is null then null else coalesce((select au.full_name from erp.app_users au where au.id=p_user),'Pengguna tidak dikenal') end
$$;

-- One family: every policy row of its Native table with the page texts, the status the readiness summary says, and its last
-- five events (newest first). Values, reasons and names only when p_admin.
create function cp7_erp_settings.family_json(p_family text,p_visible boolean,p_can_set boolean,p_admin boolean)
returns jsonb
language sql stable security definer set search_path='' as $$
 select jsonb_build_object('family',p_family,
  'label',case p_family when 'ACCESSORY' then 'Kebijakan aksesori' else 'Kebijakan laundry' end,
  'source_page',case p_family when 'ACCESSORY' then 'Aksesori, bagian Kebijakan & area' else 'Laundry, bagian Harga & Tagihan, Kebijakan owner' end,
  'visible',p_visible,'can_set',p_visible and p_can_set,
  'policies',case when p_visible then(
   select coalesce(jsonb_agg(jsonb_build_object('key',k.policy_key,'label',k.label,'status',r.status,
     'status_text',case when r.status='SET' then 'Ditetapkan di aplikasi' when k.policy_key='LAU-DEC05' then 'Sengaja tidak diaktifkan'
       when k.owner_choice then 'Keputusan owner belum diterapkan' else 'Perlu isian owner' end,
     'pending_effect',case when r.status='SET' then null else k.pending_effect end,'owner_choice',k.owner_choice,
     'version',r.version::text,'set_at',cp7_erp_settings.stamp(r.set_at),
     'set_by',case when p_admin then cp7_erp_settings.user_name(r.set_by) end,
     'reason',case when p_admin then r.reason end,'value',case when p_admin then r.value end,
     'event_count',(select count(*) from(
        select 1 from erp.bc_policy_setting_events_v1 c1 where p_family='ACCESSORY' and c1.policy_key=k.native_key
        union all select 1 from erp.bd_policy_setting_events_v1 c2 where p_family='LAUNDRY' and c2.policy_key=k.native_key)n),
     'events',(select coalesce(jsonb_agg(jsonb_build_object('version',w.version::text,'status',w.status,
        'value',case when p_admin then w.value end,'reason',case when p_admin then w.reason end,
        'set_at',cp7_erp_settings.stamp(w.set_at),'set_by',case when p_admin then cp7_erp_settings.user_name(w.set_by) end)
        order by w.version desc),'[]'::jsonb)
      from(select * from(
        select e1.version,e1.status,e1.value,e1.reason,e1.set_at,e1.set_by from erp.bc_policy_setting_events_v1 e1
         where p_family='ACCESSORY' and e1.policy_key=k.native_key
        union all
        select e2.version,e2.status,e2.value,e2.reason,e2.set_at,e2.set_by from erp.bd_policy_setting_events_v1 e2
         where p_family='LAUNDRY' and e2.policy_key=k.native_key)u order by u.version desc limit 5)w))
    order by k.sort_no),'[]'::jsonb)
   from cp7_erp_settings.catalog() k
   join lateral(
    select s1.status,s1.value,s1.version,s1.set_by,s1.set_at,s1.reason from erp.bc_policy_settings_v1 s1
     where p_family='ACCESSORY' and s1.policy_key=k.native_key
    union all
    select s2.status,s2.value,s2.version,s2.set_by,s2.set_at,s2.reason from erp.bd_policy_settings_v1 s2
     where p_family='LAUNDRY' and s2.policy_key=k.native_key)r on true
   where k.family=p_family) end)
$$;

-- Pick lists for the owner's edit form and for naming the accounts/categories a value holds (OWNER/ADMIN only, as the accessory
-- workspace gives them only to OWNER/ADMIN). Bounded: at most 100 per account type and 100 per list, with the full counts.
create function cp7_erp_settings.choices()
returns jsonb
language sql stable security definer set search_path='' as $$
 select jsonb_build_object(
  'accounts',(select coalesce(jsonb_agg(jsonb_build_object('id',t.id,'code',t.account_code,'name',t.account_name,'type',t.account_type)
     order by t.account_code,t.id),'[]'::jsonb)
    from(select ca.id,ca.account_code,ca.account_name,ca.account_type,
      row_number() over(partition by ca.account_type order by ca.account_code,ca.id) n
     from erp.chart_accounts ca where ca.is_active and ca.is_postable and ca.account_type in('ASSET','EXPENSE','REVENUE'))t where t.n<=100),
  'accounts_total',(select count(*) from erp.chart_accounts cb where cb.is_active and cb.is_postable and cb.account_type in('ASSET','EXPENSE','REVENUE')),
  'categories',(select coalesce(jsonb_agg(jsonb_build_object('id',g.id,'name',g.category_name) order by g.category_name,g.id),'[]'::jsonb)
    from(select ac.id,ac.category_name from erp.accessory_categories ac where ac.is_active order by ac.category_name,ac.id limit 100)g),
  'categories_total',(select count(*) from erp.accessory_categories ad where ad.is_active),
  'users',(select coalesce(jsonb_agg(jsonb_build_object('id',m.id,'name',m.full_name) order by m.full_name,m.id),'[]'::jsonb)
    from(select ua.id,ua.full_name from erp.app_users ua where ua.is_active order by ua.full_name,ua.id limit 100)m),
  'users_total',(select count(*) from erp.app_users ub where ub.is_active),
  'zones',(select coalesce(jsonb_agg(jsonb_build_object('id',zz.location_id,'code',zz.location_code,'name',zz.location_name,'kind',zz.zone_kind)
     order by zz.location_name,zz.location_id),'[]'::jsonb)
    from(select za.location_id,lo.location_code,lo.location_name,za.zone_kind from erp.bc_accessory_zones_v1 za join erp.locations lo on lo.id=za.location_id
     order by lo.location_name,za.location_id limit 100)zz),
  'zones_total',(select count(*) from erp.bc_accessory_zones_v1 zb))
$$;

-- The official cutover date as the cutover workspace shows it (current version, date, when and by whom). Read only.
create function cp7_erp_settings.cutover()
returns jsonb
language sql stable security definer set search_path='' as $$
 select jsonb_build_object('version',co.version,'cutover_date',to_char(co.cutover_date,'YYYY-MM-DD'),
  'set_at',case when hi.version is not null then cp7_erp_settings.stamp(hi.recorded_at) end,
  'set_by',case when hi.version is not null then coalesce(ux.full_name,'Pengguna tidak dikenal') end,
  'reason',hi.reason,'change_on','Impor data awal')
 from cp7_cutover.control co left join cp7_cutover.history hi on hi.version=co.version
  left join erp.app_users ux on ux.id=hi.app_user
 where co.singleton_id=1
$$;

create function cp7_erp_settings.workspace()
returns jsonb
language plpgsql stable security definer set search_path='' set TimeZone='UTC' as $$
declare v_access jsonb;v_role text;v_admin boolean;v_owner boolean;v_manage boolean;v_acc boolean;v_lau boolean;v_user uuid;
begin
 v_access:=cp7_erp_settings.access_now();
 v_role:=coalesce(v_access->'profile'->>'role_code','');
 v_admin:=v_role in('OWNER','ADMIN');v_owner:=v_role='OWNER';
 v_manage:=erp.has_permission('settings.erp.manage');
 v_acc:=erp.has_permission('warehouse.accessory.view');
 v_lau:=erp.has_permission('production.laundry.view');
 v_user:=erp.current_app_user_id();
 return jsonb_build_object('contract_version','cp7.erp-settings.v1',
  'read_at',cp7_erp_settings.stamp(statement_timestamp()),
  'can_see_values',v_admin,
  'families',jsonb_build_array(
   cp7_erp_settings.family_json('ACCESSORY',v_acc,v_owner and v_manage and v_acc,v_admin),
   cp7_erp_settings.family_json('LAUNDRY',v_lau,v_owner and v_manage and v_user is not null,v_admin)),
  'cutover_visible',v_admin,
  'cutover',case when v_admin then cp7_erp_settings.cutover() end,
  'choices',case when v_admin then cp7_erp_settings.choices() end,
  'business_DML',false);
end $$;

create function public.erp_cp7_get_erp_settings_v1()
returns jsonb
language sql stable security definer set search_path='' as $$select cp7_erp_settings.workspace()$$;

alter function cp7_erp_settings.catalog() owner to postgres;
alter function cp7_erp_settings.access_now() owner to postgres;
alter function cp7_erp_settings.stamp(timestamptz) owner to postgres;
alter function cp7_erp_settings.user_name(uuid) owner to postgres;
alter function cp7_erp_settings.family_json(text,boolean,boolean,boolean) owner to postgres;
alter function cp7_erp_settings.choices() owner to postgres;
alter function cp7_erp_settings.cutover() owner to postgres;
alter function cp7_erp_settings.workspace() owner to postgres;
grant create on schema public to cp7_erp_settings_read;
alter function public.erp_cp7_get_erp_settings_v1() owner to cp7_erp_settings_read;
revoke create on schema public from cp7_erp_settings_read;
revoke all on function cp7_erp_settings.catalog(),cp7_erp_settings.access_now(),cp7_erp_settings.stamp(timestamptz),
 cp7_erp_settings.user_name(uuid),cp7_erp_settings.family_json(text,boolean,boolean,boolean),cp7_erp_settings.choices(),
 cp7_erp_settings.cutover(),cp7_erp_settings.workspace()
 from public,anon,authenticated,service_role,cp7_capture,cp7_erp_settings_read;
grant execute on function cp7_erp_settings.workspace() to cp7_erp_settings_read;
revoke all on function public.erp_cp7_get_erp_settings_v1() from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_erp_settings_v1() to authenticated;
