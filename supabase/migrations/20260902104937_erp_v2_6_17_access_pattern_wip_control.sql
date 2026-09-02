-- ERP Garment v2.6.17 / pre-CP5 checkpoint (CP4.5)
-- Dynamic access control, Master Pola, authoritative WIP control, and the
-- optional-brand-until-Final-SKU boundary.
--
-- This migration deliberately leaves every recorded CP3/CP4 migration and the
-- seven CP4 HPP wrappers byte-for-byte untouched. New browser access is exposed
-- only through narrow public facades; all state and permission primitives stay
-- in the private erp schema.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

do $guard$
declare
  v_current_role_md5 text;
  v_current_user_md5 text;
  v_save_user_md5 text;
  v_owner_guard_md5 text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.16') then
    raise exception 'ERP v2.6.17 requires the independently closed v2.6.16 boundary first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.17') then
    raise exception 'ERP v2.6.17 is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regclass('erp.cp45_v2617_rollback_capsule') is not null
     or to_regclass('erp.app_roles') is not null
     or to_regclass('erp.app_permissions') is not null
     or to_regclass('erp.production_patterns') is not null
     or to_regclass('erp.wip_control_flags') is not null
     or to_regclass('erp.v_wip_control_status_v1') is not null
     or to_regprocedure('erp.guard_last_owner_auth_delete()') is not null
     or to_regprocedure('erp.guard_pattern_assignment_snapshot()') is not null
     or to_regprocedure('erp.require_pattern_identity_on_app_write()') is not null
     or to_regprocedure('erp.guard_posted_qc_item_immutable()') is not null
     or exists(
       select 1 from pg_trigger
       where tgrelid='auth.users'::regclass
         and tgname='trg_cp45_guard_last_owner_auth_delete'
         and not tgisinternal
     ) or exists(
       select 1 from pg_trigger
       where tgrelid=to_regclass('erp.qc_inspection_items')
         and tgname='trg_00_guard_posted_qc_item_immutable'
         and not tgisinternal
     ) then
    raise exception 'ERP v2.6.17 target guard: prior CP4.5 residue exists';
  end if;
  if exists(
    select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and p.proname in (
      'erp_get_my_access_v1','erp_get_access_admin_v1','erp_save_role_v1',
      'erp_deactivate_role_v1','erp_save_app_user_v3','erp_list_patterns_v1',
      'erp_save_pattern_v1','erp_deactivate_pattern_v1','erp_assign_pattern_v1',
      'erp_get_wip_control_v1','erp_set_wip_control_flag_v1',
      'erp_post_final_sku_allocation_v1'
    )
  ) then
    raise exception 'ERP v2.6.17 target guard: public RPC name collision';
  end if;
  if to_regprocedure('erp.current_app_role()') is null
     or to_regprocedure('erp.current_app_user_id()') is null
     or to_regprocedure('erp.save_app_user_v2(jsonb,uuid,bigint)') is null
     or to_regprocedure('erp.require_owner_admin()') is null
     or to_regprocedure('erp.post_fg_partial_completion_v2(jsonb,uuid,bigint)') is null
     or to_regclass('erp.app_users') is null
     or to_regclass('erp.cutting_groups') is null
     or to_regclass('erp.v_fg_partial_completion_progress') is null then
    raise exception 'ERP v2.6.17 target guard: current-main contract is incomplete';
  end if;

  select md5(pg_get_functiondef('erp.current_app_role()'::regprocedure)) into v_current_role_md5;
  select md5(pg_get_functiondef('erp.current_app_user_id()'::regprocedure)) into v_current_user_md5;
  select md5(pg_get_functiondef('erp.save_app_user_v2(jsonb,uuid,bigint)'::regprocedure)) into v_save_user_md5;
  select md5(pg_get_functiondef('erp.require_owner_admin()'::regprocedure)) into v_owner_guard_md5;
  if v_current_role_md5 is distinct from '917848c31a70310425efb64961eb9ae7'
     or v_current_user_md5 is distinct from '11b9ef50bcc451a8a709babe25e4b992'
     or v_save_user_md5 is distinct from '993ede67350075707d377642c690f8fd'
     or v_owner_guard_md5 is distinct from '965de305e5a381cfdf5588f2b9d4babc' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: access boundary fingerprints changed (role %, user %, save %, owner %)',
      v_current_role_md5,v_current_user_md5,v_save_user_md5,v_owner_guard_md5;
  end if;
  if (select pg_get_constraintdef(oid,true) from pg_constraint
      where conrelid='erp.app_users'::regclass and conname='app_users_role_check')
     is distinct from 'CHECK (role::text = ANY (ARRAY[''OWNER''::character varying::text, ''ADMIN''::character varying::text, ''STAFF''::character varying::text, ''CUSTOMER''::character varying::text]))' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: app_users role constraint changed';
  end if;
  if exists(select 1 from information_schema.columns
            where table_schema='erp' and table_name='cutting_groups'
              and column_name in ('pattern_id','pattern_code_snapshot','pattern_name_snapshot','pattern_revision_snapshot')) then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: cutting_groups pattern identity columns already exist';
  end if;
end
$guard$;

create table erp.cp45_v2617_rollback_capsule(
  function_identity text primary key,
  function_definition text not null,
  definition_sha256 text not null,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp()
);
revoke all on table erp.cp45_v2617_rollback_capsule from public, anon, authenticated, service_role;

insert into erp.cp45_v2617_rollback_capsule(
  function_identity,function_definition,definition_sha256,acl_snapshot,owner_snapshot
)
select
  format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a) end,
  pg_get_userbyid(p.proowner)
from pg_proc p
join pg_namespace n on n.oid=p.pronamespace
where n.nspname='erp' and p.proname in ('current_app_role','current_app_user_id','save_app_user_v2');

do $capsule_guard$
begin
  if (select count(*) from erp.cp45_v2617_rollback_capsule)<>3
     or exists(
       select 1 from erp.cp45_v2617_rollback_capsule
       where definition_sha256 is distinct from
         encode(extensions.digest(convert_to(function_definition,'UTF8'),'sha256'),'hex')
     ) then
    raise exception 'ERP v2.6.17 rollback capsule is incomplete or invalid';
  end if;
end
$capsule_guard$;

create table erp.app_permissions(
  permission_key text primary key,
  module_key text not null,
  module_label text not null,
  action_key text not null,
  action_label text not null,
  description text not null,
  high_risk boolean not null default false,
  sort_order integer not null,
  is_active boolean not null default true,
  created_at timestamptz not null default clock_timestamp(),
  constraint app_permissions_key_check check(permission_key ~ '^[a-z][a-z0-9_.]+$'),
  constraint app_permissions_action_check check(action_key in (
    'view','create','edit_draft','post','approve','pay','reverse','adjust','export','manage'
  )),
  constraint app_permissions_sort_check check(sort_order>=0)
);

create table erp.app_roles(
  id uuid primary key default gen_random_uuid(),
  role_code text not null unique,
  role_name text not null,
  description text,
  is_system boolean not null default false,
  is_protected boolean not null default false,
  is_active boolean not null default true,
  row_version bigint not null default 1 check(row_version>0),
  created_by uuid references erp.app_users(id),
  updated_by uuid references erp.app_users(id),
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  constraint app_roles_code_check check(role_code ~ '^[A-Z][A-Z0-9_]{1,31}$'),
  constraint app_roles_name_check check(btrim(role_name)<>'')
);
create unique index uq_app_roles_active_name on erp.app_roles(lower(role_name)) where is_active;

create table erp.app_role_permissions(
  role_id uuid not null references erp.app_roles(id) on delete restrict,
  permission_key text not null references erp.app_permissions(permission_key) on delete restrict,
  granted_by uuid references erp.app_users(id),
  granted_at timestamptz not null default clock_timestamp(),
  primary key(role_id,permission_key)
);

create table erp.app_access_audit(
  id bigint generated always as identity primary key,
  entity_type text not null check(entity_type in ('ROLE','USER_ACCESS')),
  entity_id uuid not null,
  action text not null check(action in ('CREATE','UPDATE','DEACTIVATE','ASSIGN')),
  old_data jsonb,
  new_data jsonb,
  change_reason text not null check(btrim(change_reason)<>''),
  client_request_id uuid not null,
  actor_app_user_id uuid references erp.app_users(id),
  changed_at timestamptz not null default clock_timestamp()
);
create index idx_app_access_audit_entity on erp.app_access_audit(entity_type,entity_id,changed_at desc,id desc);

alter table erp.app_permissions enable row level security;
alter table erp.app_roles enable row level security;
alter table erp.app_role_permissions enable row level security;
alter table erp.app_access_audit enable row level security;
revoke all on table erp.app_permissions,erp.app_roles,erp.app_role_permissions,erp.app_access_audit
  from public,anon,authenticated,service_role;

insert into erp.app_permissions(
  permission_key,module_key,module_label,action_key,action_label,description,high_risk,sort_order
) values
 ('dashboard.view','dashboard','Dashboard','view','Lihat','Melihat ringkasan operasional.',false,10),
 ('production.cutting.view','production.cutting','Buat Potongan','view','Lihat','Melihat proses potongan.',false,100),
 ('production.cutting.create','production.cutting','Buat Potongan','create','Buat','Membuat draft potongan.',false,101),
 ('production.cutting.edit_draft','production.cutting','Buat Potongan','edit_draft','Edit draft','Mengubah draft potongan.',false,102),
 ('production.cutting.post','production.cutting','Buat Potongan','post','Post','Memposting potongan.',true,103),
 ('production.distribution.view','production.distribution','Bagi Potongan','view','Lihat','Melihat distribusi potongan.',false,110),
 ('production.distribution.create','production.distribution','Bagi Potongan','create','Buat','Membuat distribusi potongan.',false,111),
 ('production.distribution.edit_draft','production.distribution','Bagi Potongan','edit_draft','Edit draft','Mengubah distribusi draft.',false,112),
 ('production.distribution.post','production.distribution','Bagi Potongan','post','Post','Memposting distribusi potongan.',true,113),
 ('production.wip.view','production.wip','WIP & Sewing','view','Lihat','Melihat status WIP authoritative.',false,120),
 ('production.wip.post','production.wip','WIP & Sewing','post','Selesai dijahit','Mencatat terminal selesai dijahit.',true,121),
 ('production.wip.adjust','production.wip','WIP & Sewing','adjust','Koreksi','Mengubah metadata atau blocker WIP.',true,122),
 ('production.wip.reverse','production.wip','WIP & Sewing','reverse','Reverse','Membalik fakta WIP yang sudah diposting.',true,123),
 ('production.laundry.view','production.laundry','Laundry','view','Lihat','Melihat pengiriman dan penerimaan Laundry.',false,130),
 ('production.laundry.create','production.laundry','Laundry','create','Buat','Membuat dokumen Laundry.',false,131),
 ('production.laundry.edit_draft','production.laundry','Laundry','edit_draft','Edit draft','Mengubah draft Laundry.',false,132),
 ('production.laundry.post','production.laundry','Laundry','post','Post','Memposting dokumen Laundry.',true,133),
 ('production.laundry.reverse','production.laundry','Laundry','reverse','Reverse','Membalik dokumen Laundry terposting.',true,134),
 ('production.final_sku.view','production.final_sku','QC & Final SKU','view','Lihat','Melihat QC dan alokasi Final SKU.',false,140),
 ('production.final_sku.post','production.final_sku','QC & Final SKU','post','Post Final SKU','Mengikat Good ke Final SKU.',true,141),
 ('production.final_sku.reverse','production.final_sku','QC & Final SKU','reverse','Reverse','Membalik posting Final SKU melalui alur pemilik.',true,142),
 ('production.fg_handoff.view','production.fg_handoff','Susun Nota FG','view','Lihat','Melihat antrean handoff FG.',false,150),
 ('production.fg_handoff.post','production.fg_handoff','Susun Nota FG','post','Post','Memposting handoff FG.',true,151),
 ('production.bs_rework.view','production.bs_rework','Barang BS & Rework','view','Lihat','Melihat kasus BS dan rework.',false,160),
 ('production.bs_rework.create','production.bs_rework','Barang BS & Rework','create','Buat','Membuat rework.',false,161),
 ('production.bs_rework.post','production.bs_rework','Barang BS & Rework','post','Post','Memposting hasil rework.',true,162),
 ('production.bs_rework.reverse','production.bs_rework','Barang BS & Rework','reverse','Reverse','Membalik hasil rework.',true,163),
 ('warehouse.dashboard.view','warehouse.dashboard','Ringkasan Gudang','view','Lihat','Melihat ringkasan Gudang.',false,200),
 ('warehouse.procurement.view','warehouse.procurement','Pembelian & Penerimaan','view','Lihat','Melihat pembelian dan penerimaan.',false,210),
 ('warehouse.procurement.create','warehouse.procurement','Pembelian & Penerimaan','create','Buat','Membuat penerimaan draft.',false,211),
 ('warehouse.procurement.post','warehouse.procurement','Pembelian & Penerimaan','post','Post','Memposting penerimaan.',true,212),
 ('warehouse.procurement.reverse','warehouse.procurement','Pembelian & Penerimaan','reverse','Reverse','Membalik penerimaan terposting.',true,213),
 ('warehouse.material.view','warehouse.material','Bahan & Roll','view','Lihat','Melihat bahan dan roll.',false,220),
 ('warehouse.accessory.view','warehouse.accessory','Aksesori','view','Lihat','Melihat stok aksesori.',false,230),
 ('warehouse.fg.view','warehouse.fg','Barang Jadi','view','Lihat','Melihat ringkasan barang jadi.',false,240),
 ('warehouse.movement.view','warehouse.movement','Mutasi Barang Jadi','view','Lihat','Melihat mutasi barang jadi.',false,250),
 ('warehouse.movement.export','warehouse.movement','Mutasi Barang Jadi','export','Export','Mengekspor mutasi barang jadi.',true,251),
 ('warehouse.stock.view','warehouse.stock','Kartu Stok FG','view','Lihat','Melihat kartu stok FG.',false,260),
 ('warehouse.stock.adjust','warehouse.stock','Stock Adjustment','adjust','Adjustment','Memposting penyesuaian stok.',true,261),
 ('warehouse.brand_conversion.view','warehouse.brand_conversion','Ganti Merek','view','Lihat','Melihat reklasifikasi Final SKU.',false,270),
 ('warehouse.brand_conversion.post','warehouse.brand_conversion','Ganti Merek','post','Post','Memposting reklasifikasi Final SKU.',true,271),
 ('warehouse.brand_conversion.reverse','warehouse.brand_conversion','Ganti Merek','reverse','Reverse','Membalik reklasifikasi Final SKU.',true,272),
 ('sales.invoice.view','sales.invoice','Penjualan & Invoice','view','Lihat','Melihat invoice.',false,300),
 ('sales.invoice.create','sales.invoice','Penjualan & Invoice','create','Buat','Membuat invoice draft.',false,301),
 ('sales.invoice.edit_draft','sales.invoice','Penjualan & Invoice','edit_draft','Edit draft','Mengubah invoice draft.',false,302),
 ('sales.invoice.post','sales.invoice','Penjualan & Invoice','post','Post','Memposting invoice.',true,303),
 ('sales.invoice.reverse','sales.invoice','Penjualan & Invoice','reverse','Reverse','Membalik invoice terposting.',true,304),
 ('sales.return.view','sales.return','Retur Penjualan','view','Lihat','Melihat retur penjualan.',false,310),
 ('sales.return.create','sales.return','Retur Penjualan','create','Buat','Membuat retur.',false,311),
 ('sales.return.post','sales.return','Retur Penjualan','post','Post','Memposting retur.',true,312),
 ('sales.return.reverse','sales.return','Retur Penjualan','reverse','Reverse','Membalik retur terposting.',true,313),
 ('sales.payment.view','sales.payment','Pembayaran Pelanggan','view','Lihat','Melihat pembayaran pelanggan.',false,320),
 ('sales.payment.create','sales.payment','Pembayaran Pelanggan','create','Buat','Membuat pembayaran.',false,321),
 ('sales.payment.post','sales.payment','Pembayaran Pelanggan','post','Post','Memposting pembayaran.',true,322),
 ('sales.payment.reverse','sales.payment','Pembayaran Pelanggan','reverse','Reverse','Membalik pembayaran.',true,323),
 ('sales.history.view','sales.history','Riwayat Pelanggan','view','Lihat','Melihat riwayat pelanggan.',false,330),
 ('sales.history.export','sales.history','Riwayat Pelanggan','export','Export','Mengekspor riwayat pelanggan.',true,331),
 ('finance.dashboard.view','finance.dashboard','Ringkasan Keuangan','view','Lihat','Melihat ringkasan Keuangan.',false,400),
 ('finance.cash.view','finance.cash','Kas & Bank','view','Lihat','Melihat kas dan bank.',false,410),
 ('finance.ap.view','finance.ap','Hutang Supplier & Vendor','view','Lihat','Melihat hutang.',false,420),
 ('finance.ap.pay','finance.ap','Hutang Supplier & Vendor','pay','Bayar','Membayar hutang.',true,421),
 ('finance.ar.view','finance.ar','Piutang Pelanggan','view','Lihat','Melihat piutang.',false,430),
 ('finance.payroll.view','finance.payroll','Payroll & Kasbon','view','Lihat','Melihat payroll.',false,440),
 ('finance.payroll.approve','finance.payroll','Payroll & Kasbon','approve','Approve','Menyetujui payroll.',true,441),
 ('finance.payroll.pay','finance.payroll','Payroll & Kasbon','pay','Bayar','Membayar payroll yang disetujui.',true,442),
 ('finance.attendance.view','finance.attendance','Absensi & Rate Harian','view','Lihat','Melihat absensi dan rate.',false,450),
 ('finance.attendance.create','finance.attendance','Absensi & Rate Harian','create','Buat','Membuat absensi draft.',false,451),
 ('finance.attendance.edit_draft','finance.attendance','Absensi & Rate Harian','edit_draft','Edit draft','Mengubah absensi draft.',false,452),
 ('finance.attendance.post','finance.attendance','Absensi & Rate Harian','post','Post','Memposting absensi.',true,453),
 ('finance.attendance.reverse','finance.attendance','Absensi & Rate Harian','reverse','Reverse','Membalik absensi terposting.',true,454),
 ('finance.contractor_accessory.view','finance.contractor_accessory','Nota Ambil Aksesori','view','Lihat','Melihat nota aksesori mandor.',false,460),
 ('finance.contractor_accessory.create','finance.contractor_accessory','Nota Ambil Aksesori','create','Buat','Membuat nota aksesori.',false,461),
 ('finance.contractor_accessory.post','finance.contractor_accessory','Nota Ambil Aksesori','post','Post','Memposting nota aksesori.',true,462),
 ('finance.contractor_accessory.reverse','finance.contractor_accessory','Nota Ambil Aksesori','reverse','Reverse','Membalik nota aksesori.',true,463),
 ('finance.hpp.view','finance.hpp','HPP & Rekalkulasi','view','Lihat','Melihat HPP.',false,470),
 ('finance.hpp.manage','finance.hpp','HPP & Rekalkulasi','manage','Rekalkulasi','Menjalankan lifecycle HPP yang diizinkan.',true,471),
 ('finance.journal.view','finance.journal','Jurnal & Transaksi Lain','view','Lihat','Melihat jurnal.',false,480),
 ('finance.journal.create','finance.journal','Jurnal & Transaksi Lain','create','Buat','Membuat jurnal draft.',false,481),
 ('finance.journal.post','finance.journal','Jurnal & Transaksi Lain','post','Post','Memposting jurnal.',true,482),
 ('finance.journal.reverse','finance.journal','Jurnal & Transaksi Lain','reverse','Reverse','Membalik jurnal melalui lifecycle pemilik.',true,483),
 ('finance.reports.view','finance.reports','Laporan & Tutup Buku','view','Lihat','Melihat laporan.',false,490),
 ('finance.reports.export','finance.reports','Laporan & Tutup Buku','export','Export','Mengekspor laporan sensitif.',true,491),
 ('finance.period_close.manage','finance.period_close','Tutup Periode','manage','Kelola','Menutup atau membuka periode melalui lifecycle pemilik.',true,492),
 ('master.fabric.view','master.fabric','Kain & Benchmark','view','Lihat','Melihat master kain.',false,500),
 ('master.fabric.manage','master.fabric','Kain & Benchmark','manage','Kelola','Mengelola master kain.',false,501),
 ('master.accessory.view','master.accessory','Aksesori & Harga Mandor','view','Lihat','Melihat master aksesori.',false,510),
 ('master.accessory.manage','master.accessory','Aksesori & Harga Mandor','manage','Kelola','Mengelola master aksesori.',false,511),
 ('master.price.edit_draft','master.price','Harga Master','edit_draft','Edit harga','Mengubah harga atau rate master.',true,512),
 ('master.product.view','master.product','Produk & SKU','view','Lihat','Melihat Produk dan SKU.',false,520),
 ('master.product.manage','master.product','Produk & SKU','manage','Kelola','Mengelola Produk dan SKU.',true,521),
 ('master.customer.view','master.customer','Pelanggan','view','Lihat','Melihat pelanggan.',false,530),
 ('master.customer.manage','master.customer','Pelanggan','manage','Kelola','Mengelola pelanggan.',false,531),
 ('master.partner.view','master.partner','Supplier & Vendor','view','Lihat','Melihat supplier dan vendor.',false,540),
 ('master.partner.manage','master.partner','Supplier & Vendor','manage','Kelola','Mengelola supplier dan vendor.',false,541),
 ('master.workforce.view','master.workforce','Mandor','view','Lihat','Melihat master mandor.',false,550),
 ('master.workforce.manage','master.workforce','Mandor','manage','Kelola','Mengelola master mandor.',false,551),
 ('master.location.view','master.location','Gudang & Lokasi','view','Lihat','Melihat lokasi.',false,560),
 ('master.location.manage','master.location','Gudang & Lokasi','manage','Kelola','Mengelola lokasi.',false,561),
 ('master.pattern.view','master.pattern','Pola','view','Lihat','Melihat Master Pola.',false,570),
 ('master.pattern.manage','master.pattern','Pola','manage','Kelola','Membuat dan mengubah Master Pola.',true,571),
 ('settings.reminder.view','settings.reminder','Reminder','view','Lihat','Melihat reminder.',false,600),
 ('settings.reminder.manage','settings.reminder','Reminder','manage','Kelola','Mengelola reminder.',false,601),
 ('settings.access.view','settings.access','Pengguna & Hak Akses','view','Lihat','Melihat role dan akses pengguna.',true,610),
 ('settings.access.manage','settings.access','Pengguna & Hak Akses','manage','Kelola','Mengelola role dan akses pengguna.',true,611),
 ('settings.erp.view','settings.erp','Pengaturan ERP','view','Lihat','Melihat pengaturan ERP.',false,620),
 ('settings.erp.manage','settings.erp','Pengaturan ERP','manage','Kelola','Mengubah pengaturan ERP.',true,621),
 ('settings.audit.view','settings.audit','Audit Trail','view','Lihat','Melihat audit trail.',true,630),
 ('settings.audit.export','settings.audit','Audit Trail','export','Export','Mengekspor audit sensitif.',true,631),
 ('portal.mandor.view','portal.mandor','Portal Mandor','view','Lihat','Fondasi scope Portal Mandor; belum terhubung.',false,700),
 ('portal.laundry.view','portal.laundry','Portal Laundry','view','Lihat','Fondasi scope Portal Laundry; belum terhubung.',false,710),
 ('portal.store.view','portal.store','Portal Toko','view','Lihat','Fondasi scope Portal Toko; belum terhubung.',false,720);

insert into erp.app_roles(role_code,role_name,description,is_system,is_protected,is_active) values
 ('OWNER','Owner','Akses penuh permanen dan terlindungi.',true,true,true),
 ('ADMIN','Admin','Template pengelola internal tanpa hak mengubah akses.',true,false,true),
 ('GUDANG','Gudang','Template operasional Gudang.',true,false,true),
 ('PRODUKSI_QC','Produksi & QC','Template Produksi, Laundry, QC, dan WIP.',true,false,true),
 ('KEUANGAN','Keuangan','Template Keuangan dan payroll.',true,false,true),
 ('SALES_KASIR','Sales & Kasir','Template Penjualan dan pembayaran pelanggan.',true,false,true),
 ('AUDITOR_VIEW_ONLY','Auditor · View Only','Template baca-saja lintas modul.',true,false,true),
 ('STAFF','Staff · Legacy','Role kompatibilitas lama; tidak memberi akses baru.',true,false,false),
 ('CUSTOMER','Customer · Legacy','Role kompatibilitas lama; portal belum terhubung.',true,false,false);

-- OWNER is also materialized in the matrix for an honest locked preview. The
-- permission resolver independently grants protected OWNER every active key, so
-- an accidental mapping loss still cannot weaken it.
insert into erp.app_role_permissions(role_id,permission_key)
select r.id,p.permission_key from erp.app_roles r cross join erp.app_permissions p
where r.role_code='OWNER';

insert into erp.app_role_permissions(role_id,permission_key)
select r.id,p.permission_key from erp.app_roles r cross join erp.app_permissions p
where r.role_code='ADMIN'
  and p.permission_key not in (
    'settings.access.manage','settings.audit.export','finance.period_close.manage',
    'finance.payroll.pay','warehouse.stock.adjust','master.price.edit_draft'
  );

insert into erp.app_role_permissions(role_id,permission_key)
select r.id,p.permission_key from erp.app_roles r join erp.app_permissions p on p.permission_key=any(array[
  'dashboard.view','warehouse.dashboard.view','warehouse.procurement.view','warehouse.procurement.create',
  'warehouse.procurement.post','warehouse.material.view','warehouse.accessory.view','warehouse.fg.view',
  'warehouse.movement.view','warehouse.stock.view','production.fg_handoff.view','production.final_sku.view',
  'master.pattern.view'
]) where r.role_code='GUDANG';

insert into erp.app_role_permissions(role_id,permission_key)
select r.id,p.permission_key from erp.app_roles r join erp.app_permissions p on p.permission_key=any(array[
  'dashboard.view','production.cutting.view','production.cutting.create','production.cutting.edit_draft',
  'production.cutting.post','production.distribution.view','production.distribution.create',
  'production.distribution.edit_draft','production.distribution.post','production.wip.view',
  'production.wip.post','production.laundry.view','production.laundry.create',
  'production.laundry.edit_draft','production.laundry.post','production.final_sku.view',
  'production.final_sku.post','production.fg_handoff.view','production.fg_handoff.post',
  'production.bs_rework.view','production.bs_rework.create','production.bs_rework.post',
  'master.pattern.view'
]) where r.role_code='PRODUKSI_QC';

insert into erp.app_role_permissions(role_id,permission_key)
select r.id,p.permission_key from erp.app_roles r join erp.app_permissions p on p.permission_key=any(array[
  'dashboard.view','finance.dashboard.view','finance.cash.view','finance.ap.view','finance.ap.pay',
  'finance.ar.view','finance.payroll.view','finance.payroll.approve','finance.payroll.pay',
  'finance.attendance.view','finance.attendance.create','finance.attendance.edit_draft','finance.attendance.post',
  'finance.contractor_accessory.view','finance.hpp.view','finance.hpp.manage','finance.journal.view',
  'finance.journal.create','finance.journal.post','finance.reports.view','sales.payment.view'
]) where r.role_code='KEUANGAN';

insert into erp.app_role_permissions(role_id,permission_key)
select r.id,p.permission_key from erp.app_roles r join erp.app_permissions p on p.permission_key=any(array[
  'dashboard.view','sales.invoice.view','sales.invoice.create','sales.invoice.edit_draft','sales.invoice.post',
  'sales.return.view','sales.return.create','sales.return.post','sales.payment.view','sales.payment.create',
  'sales.payment.post','sales.history.view','warehouse.fg.view','warehouse.stock.view'
]) where r.role_code='SALES_KASIR';

insert into erp.app_role_permissions(role_id,permission_key)
select r.id,p.permission_key from erp.app_roles r cross join erp.app_permissions p
where r.role_code='AUDITOR_VIEW_ONLY' and p.action_key='view'
  and p.module_key not like 'portal.%';

alter table erp.app_users add column role_id uuid;
update erp.app_users u set role_id=r.id
from erp.app_roles r where r.role_code=upper(u.role);
do $map_guard$
begin
  if exists(select 1 from erp.app_users where role_id is null) then
    raise exception 'ERP v2.6.17 cannot map one or more legacy app_users roles';
  end if;
end
$map_guard$;
alter table erp.app_users alter column role_id set not null;
alter table erp.app_users add constraint app_users_role_id_fkey
  foreign key(role_id) references erp.app_roles(id) on delete restrict;
alter table erp.app_users drop constraint app_users_role_check;
alter table erp.app_users add constraint app_users_role_code_check
  check(role ~ '^[A-Z][A-Z0-9_]{1,31}$');

create function erp.sync_app_user_role_assignment()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare v_role erp.app_roles%rowtype;
begin
  if tg_op='INSERT' then
    if new.role_id is not null then
      select * into v_role from erp.app_roles where id=new.role_id;
    elsif nullif(btrim(new.role),'') is not null then
      select * into v_role from erp.app_roles where role_code=upper(btrim(new.role));
    end if;
  elsif new.role_id is distinct from old.role_id then
    select * into v_role from erp.app_roles where id=new.role_id;
  elsif new.role is distinct from old.role then
    select * into v_role from erp.app_roles where role_code=upper(btrim(new.role));
  else
    select * into v_role from erp.app_roles where id=new.role_id;
  end if;
  if v_role.id is null then
    raise exception using errcode='23503',message='APP_ROLE_NOT_FOUND';
  end if;
  new.role_id:=v_role.id;
  new.role:=v_role.role_code;
  return new;
end
$function$;
revoke all on function erp.sync_app_user_role_assignment() from public,anon,authenticated,service_role;

create trigger trg_01_sync_app_user_role
before insert or update of role,role_id on erp.app_users
for each row execute function erp.sync_app_user_role_assignment();

create function erp.guard_last_active_owner()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare v_old_owner boolean;v_new_owner boolean:=false;
begin
  -- A postgres-only, transaction-local escape hatch exists solely so the
  -- hosted synthetic Auth proof can return an otherwise-empty UAT to its exact
  -- zero-user baseline. It is unreachable through the Data API and does not
  -- weaken application/service-role lifecycle calls.
  if session_user in ('postgres','supabase_admin')
     and current_setting('erp.cp45_allow_synthetic_cleanup',true)='on' then
    if tg_op='DELETE' then return old; else return new; end if;
  end if;
  select (r.role_code='OWNER' and old.is_active and old.auth_user_id is not null)
  into v_old_owner from erp.app_roles r where r.id=old.role_id;
  if not coalesce(v_old_owner,false) then
    if tg_op='DELETE' then return old; else return new; end if;
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('erp.active_owner_roster',0));
  if tg_op='UPDATE' then
    select (r.role_code='OWNER' and new.is_active and new.auth_user_id is not null)
    into v_new_owner from erp.app_roles r where r.id=new.role_id;
  end if;
  if not coalesce(v_new_owner,false) and not exists(
    select 1 from erp.app_users u join erp.app_roles r on r.id=u.role_id
    where u.id<>old.id and u.is_active and u.auth_user_id is not null
      and r.role_code='OWNER' and r.is_active
  ) then
    raise exception using errcode='42501',message='LAST_ACTIVE_OWNER_PROTECTED';
  end if;
  if tg_op='DELETE' then return old; else return new; end if;
end
$function$;
revoke all on function erp.guard_last_active_owner() from public,anon,authenticated,service_role;
create trigger trg_02_guard_last_active_owner
before update or delete on erp.app_users
for each row execute function erp.guard_last_active_owner();

create function erp.guard_last_owner_auth_delete()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
begin
  if session_user in ('postgres','supabase_admin')
     and current_setting('erp.cp45_allow_synthetic_cleanup',true)='on' then
    return old;
  end if;
  if exists(
    select 1 from erp.app_users u join erp.app_roles r on r.id=u.role_id
    where u.auth_user_id=old.id and u.is_active and r.role_code='OWNER' and r.is_active
  ) then
    perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('erp.active_owner_roster',0));
    if not exists(
      select 1
      from erp.app_users u
      join erp.app_roles r on r.id=u.role_id
      join auth.users au on au.id=u.auth_user_id
      where u.auth_user_id<>old.id and u.is_active
        and r.role_code='OWNER' and r.is_active
    ) then
      raise exception using errcode='42501',message='LAST_ACTIVE_OWNER_AUTH_DELETE_PROTECTED';
    end if;
  end if;
  return old;
end
$function$;
revoke all on function erp.guard_last_owner_auth_delete() from public,anon,authenticated,service_role;
create trigger trg_cp45_guard_last_owner_auth_delete
before delete on auth.users
for each row execute function erp.guard_last_owner_auth_delete();

create function erp.guard_access_catalog_immutability()
returns trigger language plpgsql security definer set search_path=''
as $function$
begin
  if session_user in ('postgres','supabase_admin')
     and current_setting('erp.cp45_allow_synthetic_cleanup',true)='on' then
    if tg_op='DELETE' then return old; else return new; end if;
  end if;
  raise exception using errcode='42501',message='ACCESS_AUDIT_IS_IMMUTABLE';
end
$function$;
revoke all on function erp.guard_access_catalog_immutability() from public,anon,authenticated,service_role;
create trigger trg_app_access_audit_immutable
before update or delete on erp.app_access_audit
for each row execute function erp.guard_access_catalog_immutability();

create function erp.guard_protected_role()
returns trigger language plpgsql security definer set search_path=''
as $function$
declare v_code text;v_new_code text;
begin
  if tg_table_name='app_roles' then
    v_code:=old.role_code;
  elsif tg_op='INSERT' then
    select role_code into v_code from erp.app_roles where id=new.role_id;
  elsif tg_op='DELETE' then
    select role_code into v_code from erp.app_roles where id=old.role_id;
  else
    select role_code into v_code from erp.app_roles where id=old.role_id;
    select role_code into v_new_code from erp.app_roles where id=new.role_id;
  end if;
  if v_code='OWNER' or v_new_code='OWNER' then
    raise exception using errcode='42501',message='PROTECTED_OWNER_ROLE_CANNOT_BE_CHANGED';
  end if;
  if tg_op='DELETE' then return old; else return new; end if;
end
$function$;
revoke all on function erp.guard_protected_role() from public,anon,authenticated,service_role;
create trigger trg_00_guard_protected_role
before update or delete on erp.app_roles
for each row execute function erp.guard_protected_role();
create trigger trg_guard_protected_role_permissions
before insert or update or delete on erp.app_role_permissions
for each row execute function erp.guard_protected_role();

create trigger trg_10_bump_app_roles before update on erp.app_roles
for each row execute function erp.bump_row_version();
create trigger trg_20_touch_app_roles before update on erp.app_roles
for each row execute function erp.touch_updated_at();

create or replace function erp.current_app_role()
returns text
language sql
stable
security definer
set search_path=''
as $function$
  select r.role_code
  from erp.app_users u
  join erp.app_roles r on r.id=u.role_id
  where u.auth_user_id=auth.uid() and u.is_active and r.is_active
  limit 1
$function$;

create or replace function erp.current_app_user_id()
returns uuid
language sql
stable
security definer
set search_path=''
as $function$
  select u.id
  from erp.app_users u
  join erp.app_roles r on r.id=u.role_id
  where u.auth_user_id=auth.uid() and u.is_active and r.is_active
  limit 1
$function$;

revoke all on function erp.current_app_role(),erp.current_app_user_id() from public,anon,authenticated,service_role;
grant execute on function erp.current_app_role(),erp.current_app_user_id() to authenticated,service_role;

create function erp.has_permission(p_permission_key text)
returns boolean
language plpgsql
stable
security definer
set search_path=''
as $function$
declare v_jwt_role text;v_allowed boolean:=false;
begin
  begin
    v_jwt_role:=coalesce(auth.jwt()->>'role','');
  exception when others then
    v_jwt_role:='';
  end;
  if v_jwt_role='service_role' then return true; end if;
  select case
    when r.is_protected and r.role_code='OWNER' then true
    else exists(
      select 1
      from erp.app_role_permissions rp
      join erp.app_permissions p on p.permission_key=rp.permission_key and p.is_active
      where rp.role_id=r.id and rp.permission_key=p_permission_key
    ) end
  into v_allowed
  from erp.app_users u
  join erp.app_roles r on r.id=u.role_id and r.is_active
  where u.auth_user_id=auth.uid() and u.is_active
  limit 1;
  return coalesce(v_allowed,false);
end
$function$;

create function erp.require_permission(p_permission_key text)
returns void
language plpgsql
stable
security definer
set search_path=''
as $function$
begin
  if coalesce(btrim(p_permission_key),'')='' or not erp.has_permission(p_permission_key) then
    raise exception using errcode='42501',message='PERMISSION_DENIED: '||coalesce(p_permission_key,'(missing)');
  end if;
end
$function$;
revoke all on function erp.has_permission(text),erp.require_permission(text)
  from public,anon,authenticated,service_role;
grant execute on function erp.has_permission(text),erp.require_permission(text) to service_role;

create function erp.role_permission_keys(p_role_id uuid)
returns jsonb
language sql
stable
security definer
set search_path=''
as $function$
  select coalesce(jsonb_agg(p.permission_key order by p.sort_order,p.permission_key),'[]'::jsonb)
  from erp.app_permissions p
  where p.is_active and (
    exists(select 1 from erp.app_roles r where r.id=p_role_id and r.role_code='OWNER' and r.is_protected)
    or exists(select 1 from erp.app_role_permissions rp where rp.role_id=p_role_id and rp.permission_key=p.permission_key)
  )
$function$;
revoke all on function erp.role_permission_keys(uuid) from public,anon,authenticated,service_role;

create function erp.get_my_access_v1()
returns jsonb
language plpgsql
stable
security definer
set search_path=''
as $function$
declare v_auth_user_id uuid:=auth.uid();v_user erp.app_users%rowtype;v_role erp.app_roles%rowtype;
begin
  if v_auth_user_id is null then
    return jsonb_build_object('allowed',false,'reason','AUTH_REQUIRED');
  end if;
  select * into v_user from erp.app_users where auth_user_id=v_auth_user_id limit 1;
  if v_user.id is null then
    return jsonb_build_object('allowed',false,'reason','APP_USER_NOT_FOUND');
  end if;
  if not v_user.is_active then
    return jsonb_build_object('allowed',false,'reason','APP_USER_INACTIVE');
  end if;
  select * into v_role from erp.app_roles where id=v_user.role_id;
  if v_role.id is null then
    return jsonb_build_object('allowed',false,'reason','APP_ROLE_NOT_FOUND');
  end if;
  if not v_role.is_active then
    return jsonb_build_object('allowed',false,'reason','APP_ROLE_INACTIVE');
  end if;
  return jsonb_build_object(
    'allowed',true,
    'profile',jsonb_build_object(
      'id',v_user.id,'auth_user_id',v_user.auth_user_id,'full_name',v_user.full_name,
      'role_id',v_role.id,'role_code',v_role.role_code,'role_name',v_role.role_name,
      'is_active',v_user.is_active,'row_version',v_user.row_version,
      'role_row_version',v_role.row_version
    ),
    'permissions',erp.role_permission_keys(v_role.id),
    'external_portals',jsonb_build_object('mandor','NOT CONNECTED','laundry','NOT CONNECTED','store','NOT CONNECTED')
  );
end
$function$;
revoke all on function erp.get_my_access_v1() from public,anon,authenticated,service_role;

create function erp.get_access_admin_v1()
returns jsonb
language plpgsql
stable
security definer
set search_path=''
as $function$
begin
  perform erp.require_permission('settings.access.view');
  return jsonb_build_object(
    'permissions',(
      select coalesce(jsonb_agg(jsonb_build_object(
        'key',p.permission_key,'module_key',p.module_key,'module_label',p.module_label,
        'action',p.action_key,'action_label',p.action_label,'description',p.description,
        'high_risk',p.high_risk,'sort_order',p.sort_order
      ) order by p.sort_order,p.permission_key),'[]'::jsonb)
      from erp.app_permissions p where p.is_active
    ),
    'roles',(
      select coalesce(jsonb_agg(jsonb_build_object(
        'id',r.id,'code',r.role_code,'name',r.role_name,'description',r.description,
        'is_system',r.is_system,'is_protected',r.is_protected,'is_active',r.is_active,
        'row_version',r.row_version,'active_user_count',(
          select count(*) from erp.app_users u where u.role_id=r.id and u.is_active
        ),
        'permissions',erp.role_permission_keys(r.id),
        'updated_at',r.updated_at,'updated_by',ub.full_name
      ) order by case when r.role_code='OWNER' then 0 when r.is_system then 1 else 2 end,r.role_name,r.id),'[]'::jsonb)
      from erp.app_roles r left join erp.app_users ub on ub.id=r.updated_by
    ),
    'users',(
      select coalesce(jsonb_agg(jsonb_build_object(
        'id',u.id,'auth_user_id',u.auth_user_id,'full_name',u.full_name,
        'role_id',r.id,'role_code',r.role_code,'role_name',r.role_name,
        'is_active',u.is_active,'mapped',u.auth_user_id is not null,
        'row_version',u.row_version,'last_sign_in_at',au.last_sign_in_at
      ) order by u.full_name,u.id),'[]'::jsonb)
      from erp.app_users u join erp.app_roles r on r.id=u.role_id
      left join auth.users au on au.id=u.auth_user_id
    ),
    'audit',(
      select coalesce(jsonb_agg(jsonb_build_object(
        'id',a.id,'entity_type',a.entity_type,'entity_id',a.entity_id,'action',a.action,
        'old_data',a.old_data,'new_data',a.new_data,'change_reason',a.change_reason,
        'changed_at',a.changed_at,'changed_by',u.full_name
      ) order by a.changed_at desc,a.id desc),'[]'::jsonb)
      from (select * from erp.app_access_audit order by changed_at desc,id desc limit 100) a
      left join erp.app_users u on u.id=a.actor_app_user_id
    )
  );
end
$function$;
revoke all on function erp.get_access_admin_v1() from public,anon,authenticated,service_role;

create function erp.save_role_v1(
  p_payload jsonb,p_client_request_id uuid,p_expected_version bigint default null
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_operation constant text:='save_role_v1';
  v_hash text;v_cached jsonb;v_response jsonb;v_old jsonb;
  v_id uuid:=nullif(p_payload->>'id','')::uuid;
  v_code text:=upper(nullif(btrim(p_payload->>'code'),''));
  v_name text:=nullif(btrim(p_payload->>'name'),'');
  v_description text:=nullif(btrim(p_payload->>'description'),'');
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_permissions jsonb:=coalesce(p_payload->'permission_keys','[]'::jsonb);
  v_role erp.app_roles%rowtype;v_actor uuid:=erp.current_app_user_id();
begin
  perform erp.require_permission('settings.access.manage');
  if v_reason is null then raise exception 'change_reason is required'; end if;
  if v_name is null then raise exception 'role name is required'; end if;
  if jsonb_typeof(v_permissions)<>'array' then raise exception 'permission_keys must be an array'; end if;
  if exists(
    select 1 from jsonb_array_elements_text(v_permissions) x(key)
    left join erp.app_permissions p on p.permission_key=x.key and p.is_active
    where p.permission_key is null
  ) then raise exception 'Unknown or inactive permission key'; end if;
  if exists(
    select 1 from jsonb_array_elements_text(v_permissions) x(key)
    join erp.app_permissions p on p.permission_key=x.key
    where p.high_risk
  ) and coalesce((p_payload->>'confirm_high_risk')::boolean,false) is not true then
    raise exception 'HIGH_RISK_PERMISSION_CONFIRMATION_REQUIRED';
  end if;
  v_hash:=erp._request_hash(jsonb_build_object('payload',p_payload,'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin(v_operation,p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;

  if v_id is null then
    if p_expected_version is not null then raise exception 'expected_version must be null when creating a role'; end if;
    if v_code is null or v_code !~ '^[A-Z][A-Z0-9_]{1,31}$' then raise exception 'invalid role code'; end if;
    insert into erp.app_roles(role_code,role_name,description,is_system,is_protected,is_active,created_by,updated_by)
    values(v_code,v_name,v_description,false,false,true,v_actor,v_actor)
    returning * into v_role;
    v_old:=null;
  else
    select * into v_role from erp.app_roles where id=v_id for update;
    if v_role.id is null then raise exception 'App role not found'; end if;
    if v_role.is_system or v_role.is_protected then raise exception 'SYSTEM_ROLE_MUST_BE_DUPLICATED_BEFORE_EDIT'; end if;
    if p_expected_version is null then raise exception 'expected_version is required when updating a role'; end if;
    if v_role.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_role.row_version;
    end if;
    if v_code is not null and v_code<>v_role.role_code then raise exception 'role code is immutable'; end if;
    v_old:=to_jsonb(v_role)||jsonb_build_object('permissions',erp.role_permission_keys(v_role.id));
    update erp.app_roles set role_name=v_name,description=v_description,updated_by=v_actor,updated_at=clock_timestamp()
    where id=v_role.id returning * into v_role;
    delete from erp.app_role_permissions where role_id=v_role.id;
  end if;

  insert into erp.app_role_permissions(role_id,permission_key,granted_by)
  select v_role.id,x.key,v_actor
  from (select distinct value as key from jsonb_array_elements_text(v_permissions)) x;
  insert into erp.app_access_audit(
    entity_type,entity_id,action,old_data,new_data,change_reason,client_request_id,actor_app_user_id
  ) values(
    'ROLE',v_role.id,case when v_old is null then 'CREATE' else 'UPDATE' end,v_old,
    to_jsonb(v_role)||jsonb_build_object('permissions',erp.role_permission_keys(v_role.id)),
    v_reason,p_client_request_id,v_actor
  );
  v_response:=jsonb_build_object(
    'role_id',v_role.id,'role_code',v_role.role_code,'role_name',v_role.role_name,
    'is_active',v_role.is_active,'row_version',v_role.row_version,
    'permissions',erp.role_permission_keys(v_role.id)
  );
  return erp._idempotency_complete(v_operation,p_client_request_id,v_response);
end
$function$;

create function erp.deactivate_role_v1(
  p_role_id uuid,p_reason text,p_client_request_id uuid,p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
declare v_role erp.app_roles%rowtype;v_hash text;v_cached jsonb;v_response jsonb;v_actor uuid:=erp.current_app_user_id();
begin
  perform erp.require_permission('settings.access.manage');
  if nullif(btrim(p_reason),'') is null then raise exception 'reason is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object('role_id',p_role_id,'reason',btrim(p_reason),'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('deactivate_role_v1',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  select * into v_role from erp.app_roles where id=p_role_id for update;
  if v_role.id is null then raise exception 'App role not found'; end if;
  if v_role.is_system or v_role.is_protected then raise exception 'SYSTEM_ROLE_CANNOT_BE_DEACTIVATED'; end if;
  if v_role.row_version<>p_expected_version then raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_role.row_version; end if;
  if exists(select 1 from erp.app_users where role_id=v_role.id and is_active) then
    raise exception 'ROLE_HAS_ACTIVE_USERS';
  end if;
  update erp.app_roles set is_active=false,updated_by=v_actor,updated_at=clock_timestamp()
  where id=v_role.id returning * into v_role;
  insert into erp.app_access_audit(entity_type,entity_id,action,old_data,new_data,change_reason,client_request_id,actor_app_user_id)
  values('ROLE',v_role.id,'DEACTIVATE',jsonb_build_object('is_active',true),to_jsonb(v_role),btrim(p_reason),p_client_request_id,v_actor);
  v_response:=jsonb_build_object('role_id',v_role.id,'is_active',false,'row_version',v_role.row_version);
  return erp._idempotency_complete('deactivate_role_v1',p_client_request_id,v_response);
end
$function$;

create or replace function erp.save_app_user_v2(
  p_payload jsonb,p_client_request_id uuid,p_expected_version bigint default null
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;v_old jsonb;
  v_id uuid:=nullif(p_payload->>'id','')::uuid;
  v_target erp.app_users%rowtype;v_role erp.app_roles%rowtype;
  v_new_active boolean:=coalesce((p_payload->>'is_active')::boolean,true);
  v_new_auth_user_id uuid;v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_actor uuid:=erp.current_app_user_id();
begin
  perform erp.require_permission('settings.access.manage');
  if v_reason is null then raise exception 'change_reason is required'; end if;
  if coalesce(btrim(p_payload->>'full_name'),'')='' then raise exception 'full_name is required'; end if;
  if p_payload ? 'role_id' then
    select * into v_role from erp.app_roles where id=nullif(p_payload->>'role_id','')::uuid;
  else
    select * into v_role from erp.app_roles where role_code=upper(coalesce(
      nullif(btrim(p_payload->>'role_code'),''),nullif(btrim(p_payload->>'role'),'')
    ));
  end if;
  if v_role.id is null or not v_role.is_active then raise exception 'Active app role is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object('payload',p_payload,'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('save_app_user_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;

  if v_id is null then
    if p_expected_version is not null then raise exception 'expected_version must be null when creating a user'; end if;
    v_new_auth_user_id:=nullif(p_payload->>'auth_user_id','')::uuid;
    insert into erp.app_users(auth_user_id,full_name,role,role_id,is_active)
    values(v_new_auth_user_id,btrim(p_payload->>'full_name'),v_role.role_code,v_role.id,v_new_active)
    returning * into v_target;
    v_old:=null;
  else
    if p_expected_version is null then raise exception 'expected_version is required when updating a user'; end if;
    select * into v_target from erp.app_users where id=v_id for update;
    if v_target.id is null then raise exception 'App user not found'; end if;
    if v_target.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_target.row_version;
    end if;
    v_old:=to_jsonb(v_target);
    v_new_auth_user_id:=case when p_payload ? 'auth_user_id'
      then nullif(p_payload->>'auth_user_id','')::uuid else v_target.auth_user_id end;
    update erp.app_users set
      auth_user_id=v_new_auth_user_id,full_name=btrim(p_payload->>'full_name'),
      role=v_role.role_code,role_id=v_role.id,is_active=v_new_active,updated_at=clock_timestamp()
    where id=v_id returning * into v_target;
  end if;
  insert into erp.app_access_audit(entity_type,entity_id,action,old_data,new_data,change_reason,client_request_id,actor_app_user_id)
  values('USER_ACCESS',v_target.id,case when v_old is null then 'ASSIGN' else 'UPDATE' end,
    v_old,to_jsonb(v_target),v_reason,p_client_request_id,v_actor);
  v_response:=jsonb_build_object(
    'app_user_id',v_target.id,'role_id',v_target.role_id,'role',v_target.role,
    'is_active',v_target.is_active,'mapped',v_target.auth_user_id is not null,'row_version',v_target.row_version
  );
  return erp._idempotency_complete('save_app_user_v2',p_client_request_id,v_response);
end
$function$;

revoke all on function erp.save_role_v1(jsonb,uuid,bigint),erp.deactivate_role_v1(uuid,text,uuid,bigint)
  from public,anon,authenticated,service_role;
revoke all on function erp.save_app_user_v2(jsonb,uuid,bigint) from public,anon,authenticated,service_role;
grant execute on function erp.save_app_user_v2(jsonb,uuid,bigint) to service_role;

create function public.erp_get_my_access_v1()
returns jsonb language plpgsql stable security definer set search_path=''
as $function$ begin return erp.get_my_access_v1(); end $function$;
create function public.erp_get_access_admin_v1()
returns jsonb language plpgsql stable security definer set search_path=''
as $function$ begin return erp.get_access_admin_v1(); end $function$;
create function public.erp_save_role_v1(p_payload jsonb,p_client_request_id uuid,p_expected_version bigint default null)
returns jsonb language plpgsql security definer set search_path=''
as $function$ begin return erp.save_role_v1(p_payload,p_client_request_id,p_expected_version); end $function$;
create function public.erp_deactivate_role_v1(p_role_id uuid,p_reason text,p_client_request_id uuid,p_expected_version bigint)
returns jsonb language plpgsql security definer set search_path=''
as $function$ begin return erp.deactivate_role_v1(p_role_id,p_reason,p_client_request_id,p_expected_version); end $function$;
create function public.erp_save_app_user_v3(p_payload jsonb,p_client_request_id uuid,p_expected_version bigint default null)
returns jsonb language plpgsql security definer set search_path=''
as $function$ begin return erp.save_app_user_v2(p_payload,p_client_request_id,p_expected_version); end $function$;

revoke all on function public.erp_get_my_access_v1(),public.erp_get_access_admin_v1(),
  public.erp_save_role_v1(jsonb,uuid,bigint),public.erp_deactivate_role_v1(uuid,text,uuid,bigint),
  public.erp_save_app_user_v3(jsonb,uuid,bigint)
  from public,anon,authenticated,service_role;
grant execute on function public.erp_get_my_access_v1(),public.erp_get_access_admin_v1(),
  public.erp_save_role_v1(jsonb,uuid,bigint),public.erp_deactivate_role_v1(uuid,text,uuid,bigint),
  public.erp_save_app_user_v3(jsonb,uuid,bigint)
  to authenticated,service_role;

create table erp.production_patterns(
  id uuid primary key default gen_random_uuid(),
  pattern_code text not null,
  revision text not null default 'R1',
  pattern_name text not null,
  sort_order integer not null default 100,
  is_active boolean not null default true,
  row_version bigint not null default 1 check(row_version>0),
  created_by uuid references erp.app_users(id),
  updated_by uuid references erp.app_users(id),
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  constraint production_patterns_code_check check(pattern_code ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'),
  constraint production_patterns_revision_check check(revision ~ '^[A-Z0-9][A-Z0-9._-]{0,15}$'),
  constraint production_patterns_name_check check(btrim(pattern_name)<>'' and length(pattern_name)<=100),
  constraint production_patterns_sort_check check(sort_order between 0 and 999999)
);
create unique index uq_production_patterns_code_revision
  on erp.production_patterns(lower(pattern_code),lower(revision));
create unique index uq_production_patterns_active_name_revision
  on erp.production_patterns(lower(pattern_name),lower(revision)) where is_active;
create index idx_production_patterns_browse
  on erp.production_patterns(is_active,sort_order,lower(pattern_code),lower(revision),id);

create table erp.production_pattern_audit(
  id bigint generated always as identity primary key,
  entity_type text not null check(entity_type in ('PATTERN','ASSIGNMENT')),
  entity_id uuid not null,
  pattern_id uuid references erp.production_patterns(id),
  action text not null check(action in ('CREATE','UPDATE','DEACTIVATE','ASSIGN')),
  old_data jsonb,
  new_data jsonb,
  change_reason text not null check(btrim(change_reason)<>''),
  client_request_id uuid not null,
  actor_app_user_id uuid references erp.app_users(id),
  changed_at timestamptz not null default clock_timestamp()
);
create index idx_production_pattern_audit_entity
  on erp.production_pattern_audit(entity_type,entity_id,changed_at desc,id desc);

alter table erp.production_patterns enable row level security;
alter table erp.production_pattern_audit enable row level security;
revoke all on table erp.production_patterns,erp.production_pattern_audit
  from public,anon,authenticated,service_role;

alter table erp.cutting_groups
  add column pattern_id uuid,
  add column pattern_code_snapshot text,
  add column pattern_name_snapshot text,
  add column pattern_revision_snapshot text;
alter table erp.cutting_groups add constraint cutting_groups_pattern_id_fkey
  foreign key(pattern_id) references erp.production_patterns(id) on delete restrict;
alter table erp.cutting_groups add constraint cutting_groups_pattern_snapshot_check check(
  (pattern_id is null and pattern_code_snapshot is null and pattern_name_snapshot is null and pattern_revision_snapshot is null)
  or
  (pattern_id is not null and pattern_code_snapshot is not null and pattern_name_snapshot is not null and pattern_revision_snapshot is not null)
);
create index idx_cutting_groups_pattern_id on erp.cutting_groups(pattern_id);

create function erp.guard_pattern_assignment_snapshot()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare v_pattern erp.production_patterns%rowtype;
begin
  if tg_op='UPDATE' and new.pattern_id is not distinct from old.pattern_id then
    if new.pattern_code_snapshot is distinct from old.pattern_code_snapshot
       or new.pattern_name_snapshot is distinct from old.pattern_name_snapshot
       or new.pattern_revision_snapshot is distinct from old.pattern_revision_snapshot
       or new.pattern_type is distinct from old.pattern_type then
      raise exception using errcode='42501',message='PATTERN_ASSIGNMENT_SNAPSHOT_IMMUTABLE';
    end if;
    return new;
  end if;
  if new.pattern_id is null then
    new.pattern_code_snapshot:=null;
    new.pattern_name_snapshot:=null;
    new.pattern_revision_snapshot:=null;
    new.pattern_type:=null;
    return new;
  end if;
  select * into v_pattern from erp.production_patterns where id=new.pattern_id and is_active;
  if v_pattern.id is null then
    raise exception using errcode='23503',message='ACTIVE_PATTERN_REQUIRED_FOR_NEW_ASSIGNMENT';
  end if;
  new.pattern_code_snapshot:=v_pattern.pattern_code;
  new.pattern_name_snapshot:=v_pattern.pattern_name;
  new.pattern_revision_snapshot:=v_pattern.revision;
  new.pattern_type:=v_pattern.pattern_name;
  return new;
end
$function$;
revoke all on function erp.guard_pattern_assignment_snapshot() from public,anon,authenticated,service_role;
create trigger trg_05_pattern_assignment_snapshot
before insert or update of pattern_id,pattern_code_snapshot,pattern_name_snapshot,pattern_revision_snapshot,pattern_type
on erp.cutting_groups
for each row execute function erp.guard_pattern_assignment_snapshot();

-- Existing history is intentionally not backfilled: Master Pola may begin
-- empty. Every new or changed Potongan that enters through a JWT application
-- request must, however, carry the canonical pattern_id. Trusted database
-- maintenance and frozen pre-CP4.5 SQL fixtures have no request JWT and keep a
-- narrow compatibility path.
create function erp.require_pattern_identity_on_app_write()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare v_jwt_role text;
begin
  begin
    v_jwt_role:=coalesce(auth.jwt()->>'role','');
  exception when others then
    v_jwt_role:='';
  end;
  if v_jwt_role in ('authenticated','service_role') and new.pattern_id is null then
    raise exception using errcode='23502',message='PATTERN_ID_REQUIRED_FOR_CUTTING_TRANSACTION';
  end if;
  return new;
end
$function$;
revoke all on function erp.require_pattern_identity_on_app_write() from public,anon,authenticated,service_role;
create trigger trg_06_require_pattern_identity
before insert or update on erp.cutting_groups
for each row execute function erp.require_pattern_identity_on_app_write();

create trigger trg_10_bump_production_patterns before update on erp.production_patterns
for each row execute function erp.bump_row_version();
create trigger trg_20_touch_production_patterns before update on erp.production_patterns
for each row execute function erp.touch_updated_at();
create trigger trg_production_pattern_audit_immutable
before update or delete on erp.production_pattern_audit
for each row execute function erp.guard_access_catalog_immutability();

create function erp.list_patterns_v1(
  p_status text default 'ACTIVE',p_query text default null,
  p_limit integer default 100,p_offset integer default 0
)
returns jsonb
language plpgsql
stable
security definer
set search_path=''
as $function$
declare v_status text:=upper(coalesce(nullif(btrim(p_status),''),'ACTIVE'));
  v_query text:=lower(nullif(btrim(p_query),''));
begin
  if not erp.has_permission('master.pattern.view')
     and not erp.has_permission('production.cutting.view')
     and not erp.has_permission('production.wip.view') then
    raise exception using errcode='42501',message='PERMISSION_DENIED: master.pattern.view or production lookup access';
  end if;
  if v_status not in ('ACTIVE','INACTIVE','ALL') then raise exception 'status must be ACTIVE, INACTIVE, or ALL'; end if;
  if p_limit is null or p_limit<1 or p_limit>200 then raise exception 'limit must be between 1 and 200'; end if;
  if p_offset is null or p_offset<0 then raise exception 'offset must be nonnegative'; end if;
  return jsonb_build_object(
    'status',v_status,'query',v_query,'limit',p_limit,'offset',p_offset,
    'total',(
      select count(*) from erp.production_patterns p
      where (v_status='ALL' or p.is_active=(v_status='ACTIVE'))
        and (v_query is null or lower(concat_ws(' ',p.pattern_code,p.revision,p.pattern_name)) like '%'||v_query||'%')
    ),
    'rows',coalesce((
      select jsonb_agg(jsonb_build_object(
        'id',x.id,'code',x.pattern_code,'revision',x.revision,'name',x.pattern_name,
        'sort_order',x.sort_order,'is_active',x.is_active,'row_version',x.row_version,
        'updated_at',x.updated_at,'updated_by',x.updated_by_name,'usage_count',x.usage_count
      ) order by x.sort_order,x.pattern_code,x.revision,x.id)
      from (
        select p.*,u.full_name as updated_by_name,(
          select count(*) from erp.cutting_groups g where g.pattern_id=p.id
        ) usage_count
        from erp.production_patterns p left join erp.app_users u on u.id=p.updated_by
        where (v_status='ALL' or p.is_active=(v_status='ACTIVE'))
          and (v_query is null or lower(concat_ws(' ',p.pattern_code,p.revision,p.pattern_name)) like '%'||v_query||'%')
        order by p.sort_order,p.pattern_code,p.revision,p.id
        limit p_limit offset p_offset
      ) x
    ),'[]'::jsonb)
  );
end
$function$;

create function erp.save_pattern_v1(
  p_payload jsonb,p_client_request_id uuid,p_expected_version bigint default null
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_id uuid:=nullif(p_payload->>'id','')::uuid;
  v_code text:=upper(nullif(btrim(p_payload->>'code'),''));
  v_revision text:=upper(coalesce(nullif(btrim(p_payload->>'revision'),''),'R1'));
  v_name text:=nullif(btrim(p_payload->>'name'),'');
  v_sort integer:=nullif(p_payload->>'sort_order','')::integer;
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_hash text;v_cached jsonb;v_response jsonb;v_old jsonb;
  v_pattern erp.production_patterns%rowtype;v_actor uuid:=erp.current_app_user_id();
begin
  perform erp.require_permission('master.pattern.manage');
  if v_code is null or v_code !~ '^[A-Z0-9][A-Z0-9_-]{0,31}$' then raise exception 'invalid pattern code'; end if;
  if v_revision !~ '^[A-Z0-9][A-Z0-9._-]{0,15}$' then raise exception 'invalid pattern revision'; end if;
  if v_name is null or length(v_name)>100 then raise exception 'invalid pattern name'; end if;
  if v_sort is null or v_sort<0 or v_sort>999999 then raise exception 'invalid pattern sort_order'; end if;
  if v_reason is null then raise exception 'change_reason is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object('payload',p_payload,'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('save_pattern_v1',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  if v_id is null then
    if p_expected_version is not null then raise exception 'expected_version must be null when creating a pattern'; end if;
    begin
      insert into erp.production_patterns(pattern_code,revision,pattern_name,sort_order,created_by,updated_by)
      values(v_code,v_revision,v_name,v_sort,v_actor,v_actor) returning * into v_pattern;
    exception when unique_violation then
      raise exception using errcode='23505',message='PATTERN_CODE_REVISION_OR_NAME_REVISION_ALREADY_EXISTS';
    end;
    v_old:=null;
  else
    if p_expected_version is null then raise exception 'expected_version is required when updating a pattern'; end if;
    select * into v_pattern from erp.production_patterns where id=v_id for update;
    if v_pattern.id is null then raise exception 'Pattern not found'; end if;
    if v_pattern.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_pattern.row_version;
    end if;
    if not v_pattern.is_active then raise exception 'Inactive pattern cannot be edited'; end if;
    if v_code<>v_pattern.pattern_code then raise exception 'pattern code is immutable; create a new pattern identity'; end if;
    if v_revision<>v_pattern.revision then raise exception 'pattern revision is immutable; create a new revision'; end if;
    v_old:=to_jsonb(v_pattern);
    begin
      update erp.production_patterns set pattern_name=v_name,sort_order=v_sort,
        updated_by=v_actor,updated_at=clock_timestamp()
      where id=v_pattern.id returning * into v_pattern;
    exception when unique_violation then
      raise exception using errcode='23505',message='PATTERN_CODE_REVISION_OR_NAME_REVISION_ALREADY_EXISTS';
    end;
  end if;
  insert into erp.production_pattern_audit(
    entity_type,entity_id,pattern_id,action,old_data,new_data,change_reason,client_request_id,actor_app_user_id
  ) values(
    'PATTERN',v_pattern.id,v_pattern.id,case when v_old is null then 'CREATE' else 'UPDATE' end,
    v_old,to_jsonb(v_pattern),v_reason,p_client_request_id,v_actor
  );
  v_response:=jsonb_build_object(
    'pattern_id',v_pattern.id,'code',v_pattern.pattern_code,'revision',v_pattern.revision,'name',v_pattern.pattern_name,
    'sort_order',v_pattern.sort_order,'is_active',v_pattern.is_active,'row_version',v_pattern.row_version
  );
  return erp._idempotency_complete('save_pattern_v1',p_client_request_id,v_response);
end
$function$;

create function erp.deactivate_pattern_v1(
  p_pattern_id uuid,p_reason text,p_client_request_id uuid,p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
declare v_pattern erp.production_patterns%rowtype;v_hash text;v_cached jsonb;v_response jsonb;v_actor uuid:=erp.current_app_user_id();
begin
  perform erp.require_permission('master.pattern.manage');
  if nullif(btrim(p_reason),'') is null then raise exception 'reason is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object('pattern_id',p_pattern_id,'reason',btrim(p_reason),'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('deactivate_pattern_v1',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  select * into v_pattern from erp.production_patterns where id=p_pattern_id for update;
  if v_pattern.id is null then raise exception 'Pattern not found'; end if;
  if v_pattern.row_version<>p_expected_version then raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_pattern.row_version; end if;
  if not v_pattern.is_active then raise exception 'Pattern is already inactive'; end if;
  update erp.production_patterns set is_active=false,updated_by=v_actor,updated_at=clock_timestamp()
  where id=v_pattern.id returning * into v_pattern;
  insert into erp.production_pattern_audit(
    entity_type,entity_id,pattern_id,action,old_data,new_data,change_reason,client_request_id,actor_app_user_id
  ) values('PATTERN',v_pattern.id,v_pattern.id,'DEACTIVATE',jsonb_build_object('is_active',true),
    to_jsonb(v_pattern),btrim(p_reason),p_client_request_id,v_actor);
  v_response:=jsonb_build_object('pattern_id',v_pattern.id,'is_active',false,'row_version',v_pattern.row_version);
  return erp._idempotency_complete('deactivate_pattern_v1',p_client_request_id,v_response);
end
$function$;

create function erp.assign_pattern_v1(
  p_cutting_group_id uuid,p_pattern_id uuid,p_reason text,p_client_request_id uuid,p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_group erp.cutting_groups%rowtype;v_pattern erp.production_patterns%rowtype;
  v_hash text;v_cached jsonb;v_response jsonb;v_actor uuid:=erp.current_app_user_id();v_old_snapshot jsonb;
begin
  if not erp.has_permission('production.cutting.edit_draft')
     and not erp.has_permission('production.wip.adjust') then
    raise exception using errcode='42501',message='PERMISSION_DENIED: production pattern assignment';
  end if;
  if nullif(btrim(p_reason),'') is null then raise exception 'reason is required'; end if;
  if p_pattern_id is null then
    raise exception using errcode='23502',message='PATTERN_ID_REQUIRED_FOR_CUTTING_TRANSACTION';
  end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'cutting_group_id',p_cutting_group_id,'pattern_id',p_pattern_id,
    'reason',btrim(p_reason),'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin('assign_pattern_v1',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  select * into v_group from erp.cutting_groups where id=p_cutting_group_id for update;
  if v_group.id is null then raise exception 'Potongan not found'; end if;
  if v_group.row_version<>p_expected_version then raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_group.row_version; end if;
  select * into v_pattern from erp.production_patterns where id=p_pattern_id;
  if v_pattern.id is null or not v_pattern.is_active then raise exception 'Active pattern is required for new assignment'; end if;
  v_old_snapshot:=jsonb_build_object(
    'pattern_id',v_group.pattern_id,'code',v_group.pattern_code_snapshot,
    'revision',v_group.pattern_revision_snapshot,'name',v_group.pattern_name_snapshot
  );
  update erp.cutting_groups set pattern_id=p_pattern_id,updated_at=clock_timestamp()
  where id=v_group.id returning * into v_group;
  insert into erp.production_pattern_audit(
    entity_type,entity_id,pattern_id,action,old_data,new_data,change_reason,client_request_id,actor_app_user_id
  ) values(
    'ASSIGNMENT',v_group.id,p_pattern_id,'ASSIGN',
    v_old_snapshot,
    jsonb_build_object(
      'pattern_id',v_group.pattern_id,'code',v_group.pattern_code_snapshot,
      'revision',v_group.pattern_revision_snapshot,'name',v_group.pattern_name_snapshot,
      'pattern_type_snapshot',v_group.pattern_type,'row_version',v_group.row_version
    ),
    btrim(p_reason),p_client_request_id,v_actor
  );
  v_response:=jsonb_build_object(
    'cutting_group_id',v_group.id,'pattern_id',v_group.pattern_id,
    'code_snapshot',v_group.pattern_code_snapshot,'revision_snapshot',v_group.pattern_revision_snapshot,
    'name_snapshot',v_group.pattern_name_snapshot,'pattern_type_snapshot',v_group.pattern_type,
    'row_version',v_group.row_version
  );
  return erp._idempotency_complete('assign_pattern_v1',p_client_request_id,v_response);
end
$function$;

revoke all on function erp.list_patterns_v1(text,text,integer,integer),erp.save_pattern_v1(jsonb,uuid,bigint),
  erp.deactivate_pattern_v1(uuid,text,uuid,bigint),erp.assign_pattern_v1(uuid,uuid,text,uuid,bigint)
  from public,anon,authenticated,service_role;

create function public.erp_list_patterns_v1(
  p_status text default 'ACTIVE',p_query text default null,
  p_limit integer default 100,p_offset integer default 0
)
returns jsonb language plpgsql stable security definer set search_path=''
as $function$ begin return erp.list_patterns_v1(p_status,p_query,p_limit,p_offset); end $function$;
create function public.erp_save_pattern_v1(p_payload jsonb,p_client_request_id uuid,p_expected_version bigint default null)
returns jsonb language plpgsql security definer set search_path=''
as $function$ begin return erp.save_pattern_v1(p_payload,p_client_request_id,p_expected_version); end $function$;
create function public.erp_deactivate_pattern_v1(p_pattern_id uuid,p_reason text,p_client_request_id uuid,p_expected_version bigint)
returns jsonb language plpgsql security definer set search_path=''
as $function$ begin return erp.deactivate_pattern_v1(p_pattern_id,p_reason,p_client_request_id,p_expected_version); end $function$;
create function public.erp_assign_pattern_v1(
  p_cutting_group_id uuid,p_pattern_id uuid,p_reason text,p_client_request_id uuid,p_expected_version bigint
)
returns jsonb language plpgsql security definer set search_path=''
as $function$ begin return erp.assign_pattern_v1(p_cutting_group_id,p_pattern_id,p_reason,p_client_request_id,p_expected_version); end $function$;

revoke all on function public.erp_list_patterns_v1(text,text,integer,integer),public.erp_save_pattern_v1(jsonb,uuid,bigint),
  public.erp_deactivate_pattern_v1(uuid,text,uuid,bigint),public.erp_assign_pattern_v1(uuid,uuid,text,uuid,bigint)
  from public,anon,authenticated,service_role;
grant execute on function public.erp_list_patterns_v1(text,text,integer,integer),public.erp_save_pattern_v1(jsonb,uuid,bigint),
  public.erp_deactivate_pattern_v1(uuid,text,uuid,bigint),public.erp_assign_pattern_v1(uuid,uuid,text,uuid,bigint)
  to authenticated,service_role;

-- Explicit flags model operational work that cannot be inferred from posted
-- quantity facts (a pending correction, reversal, handoff, or other operator
-- action). They are blockers only; they never alter stock, HPP, payroll, or
-- accounting identity.
create table erp.wip_control_flags(
  id uuid primary key default gen_random_uuid(),
  cutting_group_id uuid not null references erp.cutting_groups(id) on delete restrict,
  flag_type text not null check(flag_type in (
    'PENDING_CORRECTION','PENDING_REVERSAL','PENDING_HANDOFF','OPERATOR_ACTION'
  )),
  status text not null default 'OPEN' check(status in ('OPEN','RESOLVED')),
  note text not null check(btrim(note)<>''),
  row_version bigint not null default 1 check(row_version>0),
  created_by uuid references erp.app_users(id),
  resolved_by uuid references erp.app_users(id),
  created_at timestamptz not null default clock_timestamp(),
  resolved_at timestamptz,
  updated_at timestamptz not null default clock_timestamp(),
  constraint wip_control_flags_resolution_check check(
    (status='OPEN' and resolved_at is null and resolved_by is null)
    or (status='RESOLVED' and resolved_at is not null)
  )
);
create unique index uq_wip_control_open_flag
  on erp.wip_control_flags(cutting_group_id,flag_type) where status='OPEN';
create index idx_wip_control_flags_group on erp.wip_control_flags(cutting_group_id,status);
alter table erp.wip_control_flags enable row level security;
revoke all on table erp.wip_control_flags from public,anon,authenticated,service_role;
create trigger trg_10_bump_wip_control_flags before update on erp.wip_control_flags
for each row execute function erp.bump_row_version();
create trigger trg_20_touch_wip_control_flags before update on erp.wip_control_flags
for each row execute function erp.touch_updated_at();

create view erp.v_wip_control_status_v1
with (security_invoker=true)
as
with sewing as (
  select e.cutting_group_id,coalesce(sum(e.qty_signed),0)::bigint sewn_qty_pcs
  from erp.sewing_terminal_events e
  where e.cutting_group_id is not null
  group by e.cutting_group_id
), laundry as (
  select l.cutting_group_id,
    coalesce(sum(l.qty_sent_pcs) filter(where d.status='DRAFT'),0)::bigint laundry_draft_qty_pcs,
    coalesce(sum(l.qty_sent_pcs) filter(where d.status not in ('DRAFT','REVERSED')),0)::bigint laundry_sent_qty_pcs
  from erp.laundry_delivery_lines l
  join erp.laundry_deliveries d on d.id=l.delivery_id
  group by l.cutting_group_id
), receipt as (
  select dl.cutting_group_id,
    coalesce(sum(rl.qty_good_received+rl.qty_bs_laundry),0)::bigint laundry_good_bs_qty_pcs,
    coalesce(sum(rl.qty_stuck),0)::bigint laundry_stuck_qty_pcs,
    coalesce(sum(rl.qty_missing),0)::bigint laundry_missing_qty_pcs,
    coalesce(sum(rl.qty_good_received+rl.qty_bs_laundry+rl.qty_stuck+rl.qty_missing),0)::bigint laundry_accounted_qty_pcs
  from erp.laundry_receipt_lines rl
  join erp.laundry_receipts rr on rr.id=rl.receipt_id and rr.status='POSTED'
  join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
  join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
  group by dl.cutting_group_id
), resolved_claim as (
  select dl.cutting_group_id,coalesce(sum(c.qty_claimed),0)::bigint resolved_issue_qty_pcs
  from erp.laundry_claims c
  join erp.laundry_receipt_lines rl on rl.id=c.receipt_line_id
  join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
  where c.claim_type in ('MISSING','STUCK') and c.status in ('SETTLED','WRITTEN_OFF')
  group by dl.cutting_group_id
), bs as (
  select b.cutting_group_id,count(*)::bigint open_bs_count
  from erp.bs_cases b
  where b.cutting_group_id is not null
    and b.status not in ('RESOLVED','SCRAPPED','WRITTEN_OFF','CANCELLED')
  group by b.cutting_group_id
), rework as (
  select b.cutting_group_id,count(*)::bigint open_rework_count
  from erp.rework_orders r join erp.bs_cases b on b.id=r.bs_case_id
  where b.cutting_group_id is not null and r.status not in ('COMPLETED','CANCELLED')
  group by b.cutting_group_id
), blocker as (
  select f.cutting_group_id,count(*)::bigint open_flag_count,
    coalesce(jsonb_agg(jsonb_build_object('id',f.id,'type',f.flag_type,'note',f.note,'row_version',f.row_version)
      order by f.flag_type,f.id),'[]'::jsonb) open_flags
  from erp.wip_control_flags f where f.status='OPEN'
  group by f.cutting_group_id
), measured as (
  select
    g.id cutting_group_id,g.po_id,g.cutting_batch_id,g.group_number,g.status group_status,
    g.row_version,g.updated_at,po.po_number,po.status po_status,po.current_stage,
    m.model_code,m.model_name,g.executor_name,g.picked_up_at,g.notes,
    g.pattern_id,
    coalesce(g.pattern_code_snapshot,p.pattern_code) pattern_code,
    coalesce(g.pattern_revision_snapshot,p.revision) pattern_revision,
    coalesce(g.pattern_name_snapshot,p.pattern_name,g.pattern_type) pattern_name,
    p.sort_order pattern_sort_order,p.is_active pattern_is_active,
    coalesce(q.total_pcs,0)::bigint effective_qty_pcs,
    greatest(coalesce(s.sewn_qty_pcs,0),0)::bigint sewn_qty_pcs,
    greatest(coalesce(q.total_pcs,0)-greatest(
      coalesce(s.sewn_qty_pcs,0),coalesce(l.laundry_sent_qty_pcs,0),coalesce(fg.qc_accounted_qty_pcs,0)
    ),0)::bigint unfinished_sewing_qty_pcs,
    greatest(coalesce(s.sewn_qty_pcs,0)-coalesce(l.laundry_sent_qty_pcs,0)-coalesce(fg.direct_qc_accounted_qty_pcs,0),0)::bigint unsent_ready_qty_pcs,
    coalesce(l.laundry_draft_qty_pcs,0)::bigint laundry_draft_qty_pcs,
    coalesce(l.laundry_sent_qty_pcs,0)::bigint laundry_sent_qty_pcs,
    greatest(coalesce(l.laundry_sent_qty_pcs,0)-coalesce(rr.laundry_accounted_qty_pcs,0),0)::bigint laundry_in_transit_qty_pcs,
    coalesce(rr.laundry_good_bs_qty_pcs,0)::bigint laundry_good_bs_qty_pcs,
    greatest(coalesce(rr.laundry_stuck_qty_pcs,0)+coalesce(rr.laundry_missing_qty_pcs,0)-coalesce(rc.resolved_issue_qty_pcs,0),0)::bigint unresolved_laundry_issue_qty_pcs,
    coalesce(fg.ready_for_qc_qty_pcs,0)::bigint pending_final_sku_handoff_qty_pcs,
    coalesce(fg.remaining_qc_qty_pcs,coalesce(q.total_pcs,0))::bigint remaining_final_sku_qty_pcs,
    coalesce(bs.open_bs_count,0)::bigint open_bs_count,
    coalesce(rw.open_rework_count,0)::bigint open_rework_count,
    coalesce(bl.open_flag_count,0)::bigint open_flag_count,
    coalesce(bl.open_flags,'[]'::jsonb) open_flags
  from erp.cutting_groups g
  join erp.production_orders po on po.id=g.po_id
  join erp.product_models m on m.id=po.model_id
  left join erp.production_patterns p on p.id=g.pattern_id
  left join erp.v_cutting_group_totals q on q.cutting_group_id=g.id
  left join sewing s on s.cutting_group_id=g.id
  left join laundry l on l.cutting_group_id=g.id
  left join receipt rr on rr.cutting_group_id=g.id
  left join resolved_claim rc on rc.cutting_group_id=g.id
  left join erp.v_fg_partial_completion_progress fg on fg.cutting_group_id=g.id
  left join bs on bs.cutting_group_id=g.id
  left join rework rw on rw.cutting_group_id=g.id
  left join blocker bl on bl.cutting_group_id=g.id
)
select measured.*,
  case
    when po_status='CANCELLED'
      and unsent_ready_qty_pcs=0
      and laundry_draft_qty_pcs=0
      and laundry_in_transit_qty_pcs=0
      and unresolved_laundry_issue_qty_pcs=0
      and pending_final_sku_handoff_qty_pcs=0
      and open_bs_count=0 and open_rework_count=0 and open_flag_count=0
      then 'COMPLETED'
    when effective_qty_pcs>0
      and unfinished_sewing_qty_pcs=0
      and unsent_ready_qty_pcs=0
      and laundry_draft_qty_pcs=0
      and laundry_in_transit_qty_pcs=0
      and unresolved_laundry_issue_qty_pcs=0
      and pending_final_sku_handoff_qty_pcs=0
      and remaining_final_sku_qty_pcs=0
      and open_bs_count=0 and open_rework_count=0 and open_flag_count=0
      then 'COMPLETED'
    else 'ACTIVE'
  end::text control_status,
  jsonb_build_object(
    'unfinished_sewing',unfinished_sewing_qty_pcs>0,
    'unsent_ready',unsent_ready_qty_pcs>0,
    'laundry_draft',laundry_draft_qty_pcs>0,
    'laundry_in_transit',laundry_in_transit_qty_pcs>0,
    'laundry_issue',unresolved_laundry_issue_qty_pcs>0,
    'pending_final_sku_handoff',pending_final_sku_handoff_qty_pcs>0,
    'remaining_final_sku',remaining_final_sku_qty_pcs>0,
    'open_bs',open_bs_count>0,'open_rework',open_rework_count>0,'operator_flag',open_flag_count>0
  ) blockers
from measured;
revoke all on table erp.v_wip_control_status_v1 from public,anon,authenticated,service_role;

create function erp.get_wip_control_v1(
  p_filter text default 'ACTIVE',p_pattern_id uuid default null,
  p_sort text default 'PATTERN',p_query text default null
)
returns jsonb
language plpgsql
stable
security definer
set search_path=''
as $function$
declare v_filter text:=upper(coalesce(nullif(btrim(p_filter),''),'ACTIVE'));
  v_sort text:=upper(coalesce(nullif(btrim(p_sort),''),'PATTERN'));v_query text:=lower(nullif(btrim(p_query),''));
begin
  perform erp.require_permission('production.wip.view');
  if v_filter not in ('ACTIVE','COMPLETED','ALL') then raise exception 'filter must be ACTIVE, COMPLETED, or ALL'; end if;
  if v_sort not in ('PATTERN','PRODUCTION','UPDATED') then raise exception 'sort must be PATTERN, PRODUCTION, or UPDATED'; end if;
  return jsonb_build_object(
    'filter',v_filter,'sort',v_sort,'pattern_id',p_pattern_id,
    'rows',coalesce((
      select jsonb_agg(to_jsonb(w) order by
        case when v_sort='PATTERN' then coalesce(w.pattern_sort_order,2147483647) end,
        case when v_sort='PATTERN' then coalesce(w.pattern_code,'~') end,
        case when v_sort='UPDATED' then w.updated_at end desc,
        w.po_number,w.group_number,w.cutting_group_id
      )
      from erp.v_wip_control_status_v1 w
      where (v_filter='ALL' or w.control_status=v_filter)
        and (p_pattern_id is null or w.pattern_id=p_pattern_id)
        and (v_query is null or lower(concat_ws(' ',w.po_number,w.group_number,w.model_code,w.model_name,
          w.pattern_code,w.pattern_name,w.executor_name,w.group_status,w.notes)) like '%'||v_query||'%')
    ),'[]'::jsonb)
  );
end
$function$;

create function erp.set_wip_control_flag_v1(
  p_payload jsonb,p_client_request_id uuid,p_expected_version bigint default null
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_id uuid:=nullif(p_payload->>'id','')::uuid;v_group uuid:=nullif(p_payload->>'cutting_group_id','')::uuid;
  v_type text:=upper(nullif(btrim(p_payload->>'flag_type'),''));v_status text:=upper(coalesce(nullif(btrim(p_payload->>'status'),''),'OPEN'));
  v_note text:=nullif(btrim(p_payload->>'note'),'');v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_hash text;v_cached jsonb;v_response jsonb;v_flag erp.wip_control_flags%rowtype;v_actor uuid:=erp.current_app_user_id();
begin
  perform erp.require_permission('production.wip.adjust');
  if v_reason is null or v_note is null then raise exception 'note and change_reason are required'; end if;
  if v_type not in ('PENDING_CORRECTION','PENDING_REVERSAL','PENDING_HANDOFF','OPERATOR_ACTION') then raise exception 'invalid WIP flag type'; end if;
  if v_status not in ('OPEN','RESOLVED') then raise exception 'invalid WIP flag status'; end if;
  v_hash:=erp._request_hash(jsonb_build_object('payload',p_payload,'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('set_wip_control_flag_v1',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  if v_id is null then
    if p_expected_version is not null or v_status<>'OPEN' then raise exception 'new WIP flag must be OPEN without expected_version'; end if;
    if not exists(select 1 from erp.cutting_groups where id=v_group) then raise exception 'Potongan not found'; end if;
    insert into erp.wip_control_flags(cutting_group_id,flag_type,status,note,created_by)
    values(v_group,v_type,'OPEN',v_note,v_actor) returning * into v_flag;
  else
    if p_expected_version is null then raise exception 'expected_version is required when resolving a WIP flag'; end if;
    select * into v_flag from erp.wip_control_flags where id=v_id for update;
    if v_flag.id is null then raise exception 'WIP flag not found'; end if;
    if v_flag.row_version<>p_expected_version then raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_flag.row_version; end if;
    if v_flag.status<>'OPEN' or v_status<>'RESOLVED' then raise exception 'Only an OPEN flag can transition to RESOLVED'; end if;
    update erp.wip_control_flags set status='RESOLVED',note=v_note,resolved_by=v_actor,
      resolved_at=clock_timestamp(),updated_at=clock_timestamp()
    where id=v_flag.id returning * into v_flag;
  end if;
  insert into erp.audit_logs(entity_type,entity_id,action,old_data,new_data,changed_by,change_reason)
  values('wip_control_flags',v_flag.id,case when v_flag.row_version=1 then 'INSERT' else 'UPDATE' end,
    null,to_jsonb(v_flag),v_actor,v_reason);
  v_response:=jsonb_build_object('flag_id',v_flag.id,'status',v_flag.status,'row_version',v_flag.row_version);
  return erp._idempotency_complete('set_wip_control_flag_v1',p_client_request_id,v_response);
end
$function$;

revoke all on function erp.get_wip_control_v1(text,uuid,text,text),erp.set_wip_control_flag_v1(jsonb,uuid,bigint)
  from public,anon,authenticated,service_role;

create function public.erp_get_wip_control_v1(
  p_filter text default 'ACTIVE',p_pattern_id uuid default null,p_sort text default 'PATTERN',p_query text default null
)
returns jsonb language plpgsql stable security definer set search_path=''
as $function$ begin return erp.get_wip_control_v1(p_filter,p_pattern_id,p_sort,p_query); end $function$;
create function public.erp_set_wip_control_flag_v1(p_payload jsonb,p_client_request_id uuid,p_expected_version bigint default null)
returns jsonb language plpgsql security definer set search_path=''
as $function$ begin return erp.set_wip_control_flag_v1(p_payload,p_client_request_id,p_expected_version); end $function$;

revoke all on function public.erp_get_wip_control_v1(text,uuid,text,text),
  public.erp_set_wip_control_flag_v1(jsonb,uuid,bigint)
  from public,anon,authenticated,service_role;
grant execute on function public.erp_get_wip_control_v1(text,uuid,text,text),
  public.erp_set_wip_control_flag_v1(jsonb,uuid,bigint)
  to authenticated,service_role;

-- A Final-SKU allocation is inserted while its QC document is DRAFT. Once the
-- document is posted (or otherwise leaves DRAFT), every item is historical
-- fact: correction belongs to an owning reversal/reclassification, never an
-- UPDATE/DELETE or a late INSERT against the old posting.
create function erp.guard_posted_qc_item_immutable()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare v_status text;
begin
  if tg_op in ('UPDATE','DELETE') then
    select q.status into v_status
    from erp.qc_inspections q where q.id=old.inspection_id;
    if v_status is not null and v_status<>'DRAFT' then
      raise exception using errcode='42501',message='POSTED_FINAL_SKU_IDENTITY_IMMUTABLE';
    end if;
  end if;
  if tg_op in ('INSERT','UPDATE') then
    select q.status into v_status
    from erp.qc_inspections q where q.id=new.inspection_id;
    if v_status is not null and v_status<>'DRAFT' then
      raise exception using errcode='42501',message='POSTED_FINAL_SKU_IDENTITY_IMMUTABLE';
    end if;
  end if;
  if tg_op='DELETE' then return old; end if;
  return new;
end;
$function$;
revoke all on function erp.guard_posted_qc_item_immutable()
from public,anon,authenticated,service_role;
create trigger trg_00_guard_posted_qc_item_immutable
before insert or update or delete on erp.qc_inspection_items
for each row execute function erp.guard_posted_qc_item_immutable();

-- Brand remains absent from PO, Potongan, sewing, and Laundry. This wrapper
-- adds an explicit declared-Good reconciliation at the only binding boundary:
-- each Good piece must resolve to an active Final SKU/product.
create function erp.post_final_sku_allocation_v1(
  p_payload jsonb,p_client_request_id uuid,p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
declare v_declared bigint:=nullif(p_payload->>'good_qty_pcs','')::bigint;
  v_allocated bigint;v_physical_at timestamptz:=coalesce(nullif(p_payload->>'physical_at','')::timestamptz,clock_timestamp());
begin
  perform erp.require_permission('production.final_sku.post');
  if v_declared is null or v_declared<0 then raise exception 'good_qty_pcs is required'; end if;
  if jsonb_typeof(p_payload->'lines')<>'array' then raise exception 'Final SKU lines are required'; end if;
  if exists(
    select 1 from jsonb_to_recordset(p_payload->'lines')
      as x(final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer)
    where coalesce(x.qty_good_pcs,0)<0 or coalesce(x.qty_bs_pcs,0)<0
  ) then raise exception 'Final SKU quantities cannot be negative'; end if;
  select coalesce(sum(coalesce(x.qty_good_pcs,0)),0)::bigint into v_allocated
  from jsonb_to_recordset(p_payload->'lines') as x(final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer);
  if v_allocated<>v_declared then
    raise exception 'FINAL_SKU_GOOD_ALLOCATION_MISMATCH declared %, allocated %',v_declared,v_allocated;
  end if;
  if exists(
    select 1
    from jsonb_to_recordset(p_payload->'lines') as x(final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer)
    left join erp.products p on p.id=x.final_product_id
    where coalesce(x.qty_good_pcs,0)>0 and (
      p.id is null or not p.is_active or p.effective_from>v_physical_at
      or (p.effective_to is not null and p.effective_to<=v_physical_at)
    )
  ) then raise exception 'Every Good allocation requires an active Final SKU at physical_at'; end if;
  return erp.post_fg_partial_completion_v2(p_payload,p_client_request_id,p_expected_version);
end
$function$;
revoke all on function erp.post_final_sku_allocation_v1(jsonb,uuid,bigint)
  from public,anon,authenticated,service_role;

create function public.erp_post_final_sku_allocation_v1(
  p_payload jsonb,p_client_request_id uuid,p_expected_version bigint
)
returns jsonb language plpgsql security definer set search_path=''
as $function$ begin return erp.post_final_sku_allocation_v1(p_payload,p_client_request_id,p_expected_version); end $function$;
revoke all on function public.erp_post_final_sku_allocation_v1(jsonb,uuid,bigint)
  from public,anon,authenticated,service_role;
grant execute on function public.erp_post_final_sku_allocation_v1(jsonb,uuid,bigint)
  to authenticated,service_role;

do $post_guard$
declare v_bad text;v_public_count integer;v_active_permission_count integer;
begin
  select count(*) into v_public_count
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='public' and p.proname in (
    'erp_get_my_access_v1','erp_get_access_admin_v1','erp_save_role_v1',
    'erp_deactivate_role_v1','erp_save_app_user_v3','erp_list_patterns_v1',
    'erp_save_pattern_v1','erp_deactivate_pattern_v1','erp_assign_pattern_v1',
    'erp_get_wip_control_v1','erp_set_wip_control_flag_v1',
    'erp_post_final_sku_allocation_v1'
  );
  if v_public_count<>12 then raise exception 'ERP v2.6.17 expected 12 public facades, found %',v_public_count; end if;

  select string_agg(p.proname,',' order by p.proname) into v_bad
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='public' and p.proname in (
    'erp_get_my_access_v1','erp_get_access_admin_v1','erp_save_role_v1',
    'erp_deactivate_role_v1','erp_save_app_user_v3','erp_list_patterns_v1',
    'erp_save_pattern_v1','erp_deactivate_pattern_v1','erp_assign_pattern_v1',
    'erp_get_wip_control_v1','erp_set_wip_control_flag_v1',
    'erp_post_final_sku_allocation_v1'
  ) and (
    has_function_privilege('public',p.oid,'EXECUTE')
    or has_function_privilege('anon',p.oid,'EXECUTE')
    or not has_function_privilege('authenticated',p.oid,'EXECUTE')
    or not has_function_privilege('service_role',p.oid,'EXECUTE')
    or not p.prosecdef
    or pg_get_functiondef(p.oid) not like '%SET search_path TO ''''%'
  );
  if v_bad is not null then raise exception 'ERP v2.6.17 public facade ACL/search_path mismatch: %',v_bad; end if;

  if has_function_privilege('public','erp.has_permission(text)','EXECUTE')
     or has_function_privilege('anon','erp.has_permission(text)','EXECUTE')
     or has_function_privilege('authenticated','erp.has_permission(text)','EXECUTE')
     or has_function_privilege('public','erp.require_permission(text)','EXECUTE')
     or has_function_privilege('anon','erp.require_permission(text)','EXECUTE')
     or has_function_privilege('authenticated','erp.require_permission(text)','EXECUTE')
     or has_function_privilege('public','erp.guard_pattern_assignment_snapshot()','EXECUTE')
     or has_function_privilege('anon','erp.guard_pattern_assignment_snapshot()','EXECUTE')
     or has_function_privilege('authenticated','erp.guard_pattern_assignment_snapshot()','EXECUTE')
     or has_function_privilege('service_role','erp.guard_pattern_assignment_snapshot()','EXECUTE')
     or has_function_privilege('public','erp.require_pattern_identity_on_app_write()','EXECUTE')
     or has_function_privilege('anon','erp.require_pattern_identity_on_app_write()','EXECUTE')
     or has_function_privilege('authenticated','erp.require_pattern_identity_on_app_write()','EXECUTE')
     or has_function_privilege('service_role','erp.require_pattern_identity_on_app_write()','EXECUTE') then
    raise exception 'ERP v2.6.17 private permission primitive gained browser execute';
  end if;

  if has_function_privilege('public','erp.guard_posted_qc_item_immutable()','EXECUTE')
     or has_function_privilege('anon','erp.guard_posted_qc_item_immutable()','EXECUTE')
     or has_function_privilege('authenticated','erp.guard_posted_qc_item_immutable()','EXECUTE')
     or has_function_privilege('service_role','erp.guard_posted_qc_item_immutable()','EXECUTE')
     or not exists(
       select 1 from pg_trigger
       where tgrelid='erp.qc_inspection_items'::regclass
         and tgname='trg_00_guard_posted_qc_item_immutable' and not tgisinternal
     ) then
    raise exception 'ERP v2.6.17 posted Final-SKU immutability boundary is incomplete';
  end if;

  if has_table_privilege('public','erp.app_roles','SELECT')
     or has_table_privilege('anon','erp.app_roles','SELECT')
     or has_table_privilege('authenticated','erp.app_roles','SELECT')
     or has_table_privilege('service_role','erp.app_roles','SELECT')
     or has_table_privilege('authenticated','erp.production_patterns','SELECT')
     or has_table_privilege('authenticated','erp.wip_control_flags','SELECT') then
    raise exception 'ERP v2.6.17 private table gained a direct Data API grant';
  end if;

  select count(*) into v_active_permission_count from erp.app_permissions where is_active;
  if v_active_permission_count<90 then raise exception 'ERP v2.6.17 permission catalog unexpectedly incomplete: %',v_active_permission_count; end if;
  if (select jsonb_array_length(erp.role_permission_keys(id)) from erp.app_roles where role_code='OWNER')
     <>v_active_permission_count then
    raise exception 'ERP v2.6.17 protected OWNER does not resolve every active permission';
  end if;
  if exists(
    select 1 from erp.app_users u left join erp.app_roles r on r.id=u.role_id
    where r.id is null or u.role<>r.role_code
  ) then raise exception 'ERP v2.6.17 app user role compatibility snapshot is inconsistent'; end if;

  if not exists(
       select 1 from pg_trigger
       where tgrelid='erp.cutting_groups'::regclass
         and tgname='trg_05_pattern_assignment_snapshot' and not tgisinternal
     ) or not exists(
       select 1 from pg_trigger
       where tgrelid='erp.cutting_groups'::regclass
         and tgname='trg_06_require_pattern_identity' and not tgisinternal
     ) or exists(
       select 1 from erp.cutting_groups
       where (pattern_id is null) is distinct from
         (pattern_code_snapshot is null and pattern_name_snapshot is null and pattern_revision_snapshot is null)
     ) then
    raise exception 'ERP v2.6.17 pattern identity snapshot boundary is incomplete';
  end if;

  if md5(pg_get_functiondef('erp.require_owner_admin()'::regprocedure))
     is distinct from '965de305e5a381cfdf5588f2b9d4babc' then
    raise exception 'ERP v2.6.17 changed the frozen CP4 owner guard';
  end if;
end
$post_guard$;

insert into erp.schema_migrations(version,description)
values('v2.6.17','Pre-CP5 dynamic role access, Master Pola, authoritative WIP control, and Final-SKU brand boundary');

select pg_notify('pgrst','reload schema');
commit;
