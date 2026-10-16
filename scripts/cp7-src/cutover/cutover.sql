-- Owner D15-5 (Fable FABLE-011), 16 Okt 2026: "1. Ya, untuk transaksi operasional baru. Gunakan tanggal cutover resmi yang
-- saya sahkan dalam WIB, bukan tanggal pertama login atau uji coba. Pengamannya wajib di server. Data sebelum cutover masuk
-- melalui saldo awal/migrasi. Invoice terlambat yang merujuk penerimaan saldo awal, pelunasan sesudah cutover, serta koreksi
-- dokumen lama tetap memakai jalur resminya. Tanggal asli tetap tersimpan dan efeknya tidak boleh dihitung dua kali."
--
-- The official cutover date (WIB) is set by the owner in the app and kept with an immutable history. Until it is set
-- nothing changes. Once set, the server refuses every new row that carries value or goods dated before it, whichever
-- writer inserts it: erp.journal_entries on its economic date, erp.material_stock_movements and erp.fg_stock_movements on
-- the WIB date of physical_at. Not refused: the opening/migration postings (source types OPENING_*, INITIAL_IMPORT_*,
-- BB_*, BD_OPENING_*, BE_OPENING_*), and inverses of rows already in the books (reversal_of_id set, JOURNAL_REVERSAL,
-- CENT_INVERSE:*, *_TIME_NEUTRAL, RECEIPT_FIX_INVOICE_REVERSAL_DATE), which only cancel what exists.
-- Two rules keep the opening path whole: the official date may not lie after any import batch's cutover date, and an
-- import batch may not take a cutover date before the official one. Opening data therefore always sits on or after the
-- official date, so a late invoice on an opening receipt (booked at max(invoice date, receipt date), AZ) and a
-- settlement after cutover post on their official paths; the original document dates stay in the import tables.
-- The official date may not lie after the earliest operational row already in the books either (it would make that row
-- "before cutover"). Posting and setting serialise on one control row: a posting holds it FOR SHARE while it inserts,
-- the owner's change holds it FOR UPDATE while it checks.
create role cp7_cutover_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create role cp7_cutover_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_cutover authorization cp7_cutover_read;
revoke all on schema cp7_cutover from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_cutover to postgres,cp7_cutover_write;
create table cp7_cutover.control(
 singleton_id smallint primary key check(singleton_id=1),version integer not null default 0 check(version>=0),cutover_date date,
 check((version=0)=(cutover_date is null))
);
insert into cp7_cutover.control(singleton_id)values(1);
create table cp7_cutover.history(
 version integer primary key check(version>0),cutover_date date not null,previous_date date,reason text not null,
 actor uuid not null,app_user uuid not null,request_id uuid not null,latest_allowed date,
 recorded_at timestamptz not null default clock_timestamp()
);
create table cp7_cutover.requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,response jsonb,primary key(actor,request_id)
);
alter table cp7_cutover.control owner to postgres;
alter table cp7_cutover.history owner to postgres;
alter table cp7_cutover.requests owner to postgres;
alter table cp7_cutover.control enable row level security;
alter table cp7_cutover.history enable row level security;
alter table cp7_cutover.requests enable row level security;
create policy private_control on cp7_cutover.control for all using(false)with check(false);
create policy private_history on cp7_cutover.history for all using(false)with check(false);
create policy private_requests on cp7_cutover.requests for all using(false)with check(false);
revoke all on all tables in schema cp7_cutover from public,anon,authenticated,service_role,cp7_capture,cp7_cutover_read,cp7_cutover_write;

create function cp7_cutover.immutable()returns trigger
language plpgsql security invoker set search_path=''as $$
begin raise exception 'CP7_CUTOVER_HISTORY_IMMUTABLE';end $$;
create trigger immutable_history before update or delete on cp7_cutover.history
 for each row execute function cp7_cutover.immutable();
create trigger immutable_history_truncate before truncate on cp7_cutover.history
 for each statement execute function cp7_cutover.immutable();
create trigger control_kept before delete on cp7_cutover.control
 for each row execute function cp7_cutover.immutable();
create trigger control_kept_truncate before truncate on cp7_cutover.control
 for each statement execute function cp7_cutover.immutable();

-- The official paths that may carry a date before cutover: opening/migration postings and inverses of existing rows.
create function cp7_cutover.exempt(p_source_type text)returns boolean
language sql immutable set search_path=''as $$
 select coalesce(p_source_type like 'OPENING\_%' or p_source_type like 'INITIAL\_IMPORT\_%' or p_source_type like 'BB\_%'
  or p_source_type like 'BD\_OPENING\_%' or p_source_type like 'BE\_OPENING\_%'
  or p_source_type='JOURNAL_REVERSAL' or p_source_type like 'CENT\_INVERSE:%' or p_source_type like '%\_TIME\_NEUTRAL'
  or p_source_type='RECEIPT_FIX_INVOICE_REVERSAL_DATE',false)$$;

-- The official date, read under FOR SHARE so that a change waits for postings in flight and a posting waits for a change.
create function cp7_cutover.floor()returns date
language plpgsql volatile security definer set search_path=''as $$
declare v date;
begin
 select cutover_date into v from cp7_cutover.control where singleton_id=1 for share;
 return v;
end $$;

create function cp7_cutover.refuse(p_kind text,p_date date,p_floor date,p_source_type text)returns void
language plpgsql volatile security definer set search_path=''as $$
begin
 raise exception using errcode='P0001',
  message=format('CP7_CUTOVER_BEFORE: %s bertanggal %s jatuh sebelum tanggal mulai pakai aplikasi %s (cutover resmi). Data sebelum tanggal itu masuk lewat Impor Saldo Awal; dokumen lama dibetulkan lewat jalur koreksinya.',
   p_kind,to_char(p_date,'YYYY-MM-DD'),to_char(p_floor,'YYYY-MM-DD')),
  detail=jsonb_build_object('date',p_date,'cutover_date',p_floor,'source_type',p_source_type)::text;
end $$;

create function cp7_cutover.guard_journal()returns trigger
language plpgsql volatile security definer set search_path=''as $$
declare v date;
begin
 v:=cp7_cutover.floor();
 if v is null or new.economic_date is null or new.economic_date>=v or new.reversal_of_id is not null or cp7_cutover.exempt(new.source_type)then
  return new;end if;
 perform cp7_cutover.refuse('Transaksi',new.economic_date,v,new.source_type);
 return null;
end $$;

create function cp7_cutover.guard_movement()returns trigger
language plpgsql volatile security definer set search_path=''as $$
declare v date;d date;
begin
 v:=cp7_cutover.floor();
 if v is null or new.physical_at is null then return new;end if;
 d:=(new.physical_at at time zone 'Asia/Jakarta')::date;
 if d>=v or new.reversal_of_id is not null or cp7_cutover.exempt(new.source_type)then return new;end if;
 perform cp7_cutover.refuse(case tg_table_name when'material_stock_movements'then'Mutasi stok bahan'else'Mutasi stok barang jadi'end,d,v,new.source_type);
 return null;
end $$;

-- An import batch may not take a cutover date before the official one (its opening data would fall before cutover).
create function cp7_cutover.guard_batch()returns trigger
language plpgsql volatile security definer set search_path=''as $$
declare v date;d date;
begin
 v:=cp7_cutover.floor();
 if v is null or new.cutover_at is null then return new;end if;
 d:=(new.cutover_at at time zone 'Asia/Jakarta')::date;
 if d>=v then return new;end if;
 raise exception using errcode='P0001',
  message=format('CP7_CUTOVER_IMPORT_DATE: tanggal cutover impor %s sebelum tanggal mulai pakai aplikasi %s. Impor saldo awal memakai tanggal cutover resmi itu.',
   to_char(d,'YYYY-MM-DD'),to_char(v,'YYYY-MM-DD'));
end $$;

create trigger cp7_cutover_journal before insert on erp.journal_entries for each row execute function cp7_cutover.guard_journal();
create trigger cp7_cutover_material before insert on erp.material_stock_movements for each row execute function cp7_cutover.guard_movement();
create trigger cp7_cutover_fg before insert on erp.fg_stock_movements for each row execute function cp7_cutover.guard_movement();
create trigger cp7_cutover_batch before insert or update of cutover_at on erp.migration_batches for each row execute function cp7_cutover.guard_batch();

-- The earliest rows a new official date may not pass: the earliest operational row in the books (not opening, not an
-- inverse, not itself reversed) and the earliest import batch cutover.
create function cp7_cutover.limits()returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare op jsonb;batch jsonb;
begin
 select jsonb_build_object('date',x.d,'kind',x.k,'source_type',x.s)into op from(
  select j.economic_date d,'JOURNAL'k,j.source_type s from erp.journal_entries j
   where j.reversal_of_id is null and j.status<>'REVERSED' and not cp7_cutover.exempt(j.source_type)
  union all
  select(m.physical_at at time zone 'Asia/Jakarta')::date,'MATERIAL_MOVEMENT',m.source_type from erp.material_stock_movements m
   where m.reversal_of_id is null and not cp7_cutover.exempt(m.source_type)
    and not exists(select 1 from erp.material_stock_movements r where r.reversal_of_id=m.id)
  union all
  select(f.physical_at at time zone 'Asia/Jakarta')::date,'FG_MOVEMENT',f.source_type from erp.fg_stock_movements f
   where f.reversal_of_id is null and not cp7_cutover.exempt(f.source_type)
    and not exists(select 1 from erp.fg_stock_movements r where r.reversal_of_id=f.id)
 )x where x.d is not null order by x.d,x.k,x.s limit 1;
 select jsonb_build_object('date',(b.cutover_at at time zone 'Asia/Jakarta')::date,'batch_code',b.batch_code)into batch
  from erp.migration_batches b where b.cutover_at is not null order by b.cutover_at,b.batch_code limit 1;
 return jsonb_build_object('earliest_operational',op,'earliest_import',batch,
  'latest_allowed',least((op->>'date')::date,(batch->>'date')::date));
end $$;

create function cp7_cutover.access_now(p_set boolean)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;
begin
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_CUTOVER_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN')
  or(p_set and a->'profile'->>'role_code'<>'OWNER')then
  raise exception using errcode='42501',message='CP7_CUTOVER_DENIED';end if;
 return a;
end $$;

create function cp7_cutover.workspace()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;c cp7_cutover.control;lim jsonb;cur jsonb;hist jsonb;
begin
 a:=cp7_cutover.access_now(false);
 select*into c from cp7_cutover.control where singleton_id=1;
 lim:=cp7_cutover.limits();
 select jsonb_build_object('version',h.version,'cutover_date',h.cutover_date,'previous_date',h.previous_date,'reason',h.reason,
   'set_at',h.recorded_at,'set_by',coalesce(u.full_name,'Pengguna tidak dikenal'))into cur
  from cp7_cutover.history h left join erp.app_users u on u.id=h.app_user where h.version=c.version;
 select coalesce(jsonb_agg(jsonb_build_object('version',h.version,'cutover_date',h.cutover_date,'previous_date',h.previous_date,'reason',h.reason,
   'set_at',h.recorded_at,'set_by',coalesce(u.full_name,'Pengguna tidak dikenal'))order by h.version desc),'[]'::jsonb)into hist
  from(select*from cp7_cutover.history order by version desc limit 50)h left join erp.app_users u on u.id=h.app_user;
 if cp7_cutover.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_CUTOVER_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.cutover-workspace.v1','today',(clock_timestamp()at time zone'Asia/Jakarta')::date,
  'can_set',a->'profile'->>'role_code'='OWNER','version',c.version,'current',cur,'history',hist,
  'earliest_operational',lim->'earliest_operational','earliest_import',lim->'earliest_import','latest_allowed',lim->'latest_allowed',
  'business_DML',false);
end $$;

create function cp7_cutover.command(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_cutover.requests;c cp7_cutover.control;v_date date;v_reason text;v_user uuid;lim jsonb;answer jsonb;v_today date;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_cutover.access_now(true);
 if p_request is null or jsonb_typeof(p)is distinct from'object'or not(p?&array['action','expected_version','cutover_date','reason'])
  or(select count(*)from jsonb_object_keys(p))<>4 or p->>'action'is distinct from'SET'
  or jsonb_typeof(p->'expected_version')<>'number'or(p->>'expected_version')!~'^[0-9]{1,9}$'
  or jsonb_typeof(p->'cutover_date')<>'string'or(p->>'cutover_date')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
  or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 5 and 1000 then
  raise exception 'CP7_CUTOVER_FIELDS';end if;
 begin v_date:=(p->>'cutover_date')::date;exception when others then raise exception 'CP7_CUTOVER_FIELDS';end;
 if to_char(v_date,'YYYY-MM-DD')<>p->>'cutover_date'then raise exception 'CP7_CUTOVER_FIELDS';end if;
 v_reason:=btrim(p->>'reason');
 insert into cp7_cutover.requests values(auth.uid(),p_request,p,null)on conflict do nothing;
 select*into strict old from cp7_cutover.requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p then raise exception 'CP7_CUTOVER_REQUEST_CHANGED';end if;
 if cp7_cutover.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_CUTOVER_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 v_user:=erp.current_app_user_id();
 if v_user is null then raise exception using errcode='42501',message='CP7_CUTOVER_DENIED';end if;
 v_today:=(clock_timestamp()at time zone'Asia/Jakarta')::date;
 select*into strict c from cp7_cutover.control where singleton_id=1 for update;
 if c.version<>(p->>'expected_version')::integer then raise exception 'CP7_CUTOVER_STALE';end if;
 if c.cutover_date is not distinct from v_date then raise exception 'CP7_CUTOVER_NO_CHANGE';end if;
 if v_date<date'2000-01-01'or v_date>v_today+366 then raise exception 'CP7_CUTOVER_DATE';end if;
 -- Checked after the control row is held: every posting in flight has committed or waits for this change.
 lim:=cp7_cutover.limits();
 if(lim->'earliest_operational'->>'date')::date<v_date then
  raise exception 'CP7_CUTOVER_OPERATIONAL_BEFORE: sudah ada transaksi operasional tanggal % (%); tanggal mulai pakai aplikasi tidak boleh sesudahnya.',
   lim->'earliest_operational'->>'date',lim->'earliest_operational'->>'source_type';end if;
 if(lim->'earliest_import'->>'date')::date<v_date then
  raise exception 'CP7_CUTOVER_IMPORT_BEFORE: impor saldo awal % memakai tanggal cutover %; tanggal mulai pakai aplikasi tidak boleh sesudahnya.',
   lim->'earliest_import'->>'batch_code',lim->'earliest_import'->>'date';end if;
 update cp7_cutover.control set version=version+1,cutover_date=v_date where singleton_id=1;
 insert into cp7_cutover.history(version,cutover_date,previous_date,reason,actor,app_user,request_id,latest_allowed)
  values(c.version+1,v_date,c.cutover_date,v_reason,auth.uid(),v_user,p_request,(lim->>'latest_allowed')::date);
 if cp7_cutover.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_CUTOVER_ACCESS_CHANGED';end if;
 answer:=jsonb_build_object('contract_version','cp7.cutover-outcome.v1','kind','COMMITTED_OUTCOME','action','SET','request_id',p_request,
  'version',c.version+1,'cutover_date',v_date,'previous_date',c.cutover_date);
 update cp7_cutover.requests set response=answer where actor=auth.uid()and request_id=p_request;
 return answer;
end $$;

create function public.erp_cp7_get_cutover_v1()returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutover.workspace()$$;
create function public.erp_cp7_set_cutover_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutover.command(p_payload,p_request)$$;
alter function cp7_cutover.immutable()owner to postgres;
alter function cp7_cutover.exempt(text)owner to postgres;
alter function cp7_cutover.floor()owner to postgres;
alter function cp7_cutover.refuse(text,date,date,text)owner to postgres;
alter function cp7_cutover.guard_journal()owner to postgres;
alter function cp7_cutover.guard_movement()owner to postgres;
alter function cp7_cutover.guard_batch()owner to postgres;
alter function cp7_cutover.limits()owner to postgres;
alter function cp7_cutover.access_now(boolean)owner to postgres;
alter function cp7_cutover.workspace()owner to postgres;
alter function cp7_cutover.command(jsonb,uuid)owner to postgres;
grant create on schema public to cp7_cutover_read,cp7_cutover_write;
alter function public.erp_cp7_get_cutover_v1()owner to cp7_cutover_read;
alter function public.erp_cp7_set_cutover_v1(jsonb,uuid)owner to cp7_cutover_write;
revoke create on schema public from cp7_cutover_read,cp7_cutover_write;
revoke all on function cp7_cutover.immutable(),cp7_cutover.exempt(text),cp7_cutover.floor(),cp7_cutover.refuse(text,date,date,text),
 cp7_cutover.guard_journal(),cp7_cutover.guard_movement(),cp7_cutover.guard_batch(),cp7_cutover.limits(),cp7_cutover.access_now(boolean),
 cp7_cutover.workspace(),cp7_cutover.command(jsonb,uuid)
 from public,anon,authenticated,service_role,cp7_capture,cp7_cutover_read,cp7_cutover_write;
grant execute on function cp7_cutover.workspace()to cp7_cutover_read;
grant execute on function cp7_cutover.command(jsonb,uuid)to cp7_cutover_write;
revoke all on function public.erp_cp7_get_cutover_v1(),public.erp_cp7_set_cutover_v1(jsonb,uuid)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_cutover_v1(),public.erp_cp7_set_cutover_v1(jsonb,uuid)to authenticated;
