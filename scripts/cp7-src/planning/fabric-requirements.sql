-- Explicit effective-dated planning inputs, never Native BOM/stock/consumption.
-- An exact physical product/size and full current Native material identity are
-- reviewed together. No rate, pattern, width, allocation or installation default.
create schema cp7_fabric_native authorization cp7_capture;
revoke all on schema cp7_fabric_native from public,anon,authenticated,service_role;
grant select on erp.materials,erp.production_patterns to cp7_capture;
create table cp7_fabric_native.recipes(
 id uuid primary key default gen_random_uuid(),target_key text not null,
 revision bigint not null check(revision>0),source_run uuid not null,source_hash text not null,
 config jsonb not null,reason text not null,actor uuid not null,request_id uuid not null,
 recorded_at timestamptz not null default clock_timestamp(),unique(target_key,revision),unique(actor,request_id)
);
create table cp7_fabric_native.commands(
 actor uuid not null,request_id uuid not null,payload jsonb not null,result jsonb not null,
 primary key(actor,request_id)
);
alter table cp7_fabric_native.recipes owner to cp7_capture;
alter table cp7_fabric_native.commands owner to cp7_capture;
alter table cp7_fabric_native.recipes enable row level security;
alter table cp7_fabric_native.commands enable row level security;
create policy fabric_recipes_private on cp7_fabric_native.recipes for all to public using(false)with check(false);
create policy fabric_commands_private on cp7_fabric_native.commands for all to public using(false)with check(false);
revoke all on all tables in schema cp7_fabric_native from public,anon,authenticated,service_role;
create trigger fabric_recipe_immutable before update or delete on cp7_fabric_native.recipes
 for each row execute function cp7_private.immutable_run();
create trigger fabric_command_immutable before update or delete on cp7_fabric_native.commands
 for each row execute function cp7_private.immutable_run();

create function cp7_fabric_native.validate(v jsonb,catalog jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare m jsonb;p jsonb;lo timestamptz;hi timestamptz;
begin
 perform cp7_wip.fields(v,array['basis','effective_from','effective_to','material_id','material_hash','unit','qty_per_good_pcs','pattern_id','pattern_hash']);
 if v->>'basis'is distinct from'SELECTED_ASSUMPTIONS'then raise exception 'CP7_FABRIC_BASIS';end if;
 if jsonb_typeof(v->'material_id')is distinct from'string'or v->>'material_id'!~'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'
  or jsonb_typeof(v->'material_hash')is distinct from'string'or v->>'material_hash'!~'^[0-9a-f]{64}$'
  or jsonb_typeof(v->'unit')is distinct from'string'then raise exception 'CP7_FABRIC_NATIVE_MATERIAL_CHANGED';end if;
 lo:=cp7_demand.instant(v->'effective_from');
 if v->'effective_to'<>'null'::jsonb then hi:=cp7_demand.instant(v->'effective_to');
  if hi<=lo then raise exception 'CP7_FABRIC_EFFECTIVE_WINDOW';end if;
 end if;
 if jsonb_typeof(v->'qty_per_good_pcs')is distinct from'string'
  or v->>'qty_per_good_pcs'!~'^(0|[1-9][0-9]{0,11})([.][0-9]{1,6})?$'
  or (v->>'qty_per_good_pcs')::numeric<=0 then raise exception 'CP7_FABRIC_RATE';end if;
 select x into m from jsonb_array_elements(catalog->'materials')x where x->>'id'=v->>'material_id';
 if m is null or m->>'material_type'<>'FABRIC'or m->'is_active'is distinct from'true'::jsonb
  or v->>'material_hash'is distinct from encode(extensions.digest(convert_to(m::text,'UTF8'),'sha256'),'hex')
  or v->>'unit'is distinct from m->>'unit_code'then raise exception 'CP7_FABRIC_NATIVE_MATERIAL_CHANGED';end if;
 if v->'pattern_id'='null'::jsonb then
  if v->'pattern_hash'<>'null'::jsonb then raise exception 'CP7_FABRIC_PATTERN';end if;
 else
  if jsonb_typeof(v->'pattern_id')is distinct from'string'or v->>'pattern_id'!~'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'
   or jsonb_typeof(v->'pattern_hash')is distinct from'string'or v->>'pattern_hash'!~'^[0-9a-f]{64}$'then raise exception 'CP7_FABRIC_PATTERN';end if;
  select x into p from jsonb_array_elements(catalog->'patterns')x where x->>'id'=v->>'pattern_id';
  if p is null or p->'is_active'is distinct from'true'::jsonb
   or v->>'pattern_hash'is distinct from encode(extensions.digest(convert_to(p::text,'UTF8'),'sha256'),'hex')then
   raise exception 'CP7_FABRIC_NATIVE_PATTERN_CHANGED';end if;
 end if;
 return v;
end $$;

create function cp7_fabric_native.source(products jsonb,p_at timestamptz)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare v jsonb;selected jsonb;m jsonb;p jsonb;
begin
 with targets as(select (x->>'root_id')||':'||(x->>'size_id')key from jsonb_array_elements(products)x),
 versions as(select to_jsonb(r)body from cp7_fabric_native.recipes r join targets t on t.key=r.target_key
  where r.recorded_at<=p_at order by r.target_key,r.revision limit 10001)
 select coalesce(jsonb_agg(body order by body->>'target_key',(body->>'revision')::bigint),'[]')into v from versions;
 if jsonb_array_length(v)>10000 then raise exception 'CP7_FABRIC_SOURCE_LIMIT';end if;
 -- A successor starts at its chosen effective clock. Expiry yields UNKNOWN;
 -- it never silently resurrects an older rate. Future versions are still kept
 -- in the Original, but cannot become a current operational operand early.
 with candidates as(select distinct on(x->>'target_key')x from jsonb_array_elements(v)x
  where(x->'config'->>'effective_from')::timestamptz<=p_at order by x->>'target_key',(x->>'revision')::bigint desc)
 select coalesce(jsonb_agg(x order by x->>'target_key'),'[]')into selected from candidates
  where x->'config'->'effective_to'='null'::jsonb or(x->'config'->>'effective_to')::timestamptz>p_at;
 select coalesce(jsonb_agg(to_jsonb(x)order by x.id),'[]')into m from erp.materials x
  where (to_jsonb(x)->>'created_at')::timestamptz<=p_at
   and exists(select 1 from jsonb_array_elements(selected)s where s->'config'->>'material_id'=x.id::text);
 select coalesce(jsonb_agg(to_jsonb(x)order by x.id),'[]')into p from erp.production_patterns x
  where x.created_at<=p_at and exists(select 1 from jsonb_array_elements(selected)s where s->'config'->>'pattern_id'=x.id::text);
 return jsonb_build_object('contract_version','cp7.fabric-source.v1','captured_at',p_at,
  'versions',v,'selected',selected,'materials',m,'patterns',p,
  'basis','SELECTED_ASSUMPTIONS_NOT_NATIVE_RECIPE_INSTALLATION_OR_ALLOCATION');
end $$;

create function cp7_fabric_native.needs(c jsonb,r jsonb,assumptions jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare s jsonb:=c->'fabric_source';recipe jsonb;m jsonb;p jsonb;refs jsonb:=r->'refs';ids jsonb:=assumptions;
 gross text;unit text:='MATERIAL_BASE_UNIT';material text:='FABRIC_UNREVIEWED:'||(r->>'target_key');
 reason text:='Resep kain untuk produk dan ukuran ini belum direview atau sudah berakhir; kebutuhan belum diketahui.';cfg jsonb;
begin
 select x into recipe from jsonb_array_elements(s->'selected')x where x->>'target_key'=r->>'target_key';
 if recipe is not null then
  cfg:=recipe->'config';unit:=cfg->>'unit';material:='FABRIC_MATERIAL:'||(cfg->>'material_id');
  refs:=refs||jsonb_build_array(cp7_wip.ref('CP7_FABRIC_RECIPE',recipe->>'id',recipe->>'revision'));
  ids:=ids||jsonb_build_array(recipe->>'id');
  select x into m from jsonb_array_elements(s->'materials')x where x->>'id'=cfg->>'material_id';
  if m is not null then refs:=refs||jsonb_build_array(cp7_wip.ref('erp.materials',m->>'id',
   encode(extensions.digest(convert_to(m::text,'UTF8'),'sha256'),'hex')));end if;
  if cfg->'pattern_id'<>'null'::jsonb then
   select x into p from jsonb_array_elements(s->'patterns')x where x->>'id'=cfg->>'pattern_id';
   if p is not null then refs:=refs||jsonb_build_array(cp7_wip.ref('erp.production_patterns',p->>'id',
    encode(extensions.digest(convert_to(p::text,'UTF8'),'sha256'),'hex')));end if;
  end if;
  if m is not null and m->'is_active'='true'::jsonb and m->>'material_type'='FABRIC'
   and m->>'unit_code'=unit and cfg->>'material_hash'=encode(extensions.digest(convert_to(m::text,'UTF8'),'sha256'),'hex')
   and(cfg->'pattern_id'='null'::jsonb or(p is not null and p->'is_active'='true'::jsonb
    and cfg->>'pattern_hash'=encode(extensions.digest(convert_to(p::text,'UTF8'),'sha256'),'hex')))
   and r->>'conditional_gap_pcs'is not null then
   gross:=((r->>'conditional_gap_pcs')::numeric*(cfg->>'qty_per_good_pcs')::numeric)::text;
   reason:=(m->>'material_name')||': kebutuhan kain memakai pemakaian per PCS yang dipilih, bukan pemakaian aktual. '
    ||case when p is null then 'Pola belum dipilih. 'else 'Pola '||(p->>'pattern_code')||' versi '||(p->>'revision')||'. 'end
    ||'Pemasangan, alokasi sisa, dan kemampuan produksi belum terbukti.';
  else reason:='Sumber bahan/pola atau jumlah rencana berubah atau belum lengkap; review resep kain kembali.';end if;
 end if;
 return jsonb_build_array(jsonb_build_object('target_key',r->'target_key','material_key',material,
  'gross',cp7_analysis_native.fact(gross,unit,refs,ids),
  'installed_proven',cp7_analysis_native.fact(null,unit,refs),
  'unused_allocated_proven',cp7_analysis_native.fact(null,unit,refs),
  'additional_external',cp7_analysis_native.fact(null,unit,refs),'reason',reason));
end $$;
alter function cp7_fabric_native.validate(jsonb,jsonb)owner to cp7_capture;
alter function cp7_fabric_native.source(jsonb,timestamptz)owner to cp7_capture;
alter function cp7_fabric_native.needs(jsonb,jsonb,jsonb)owner to cp7_capture;
revoke all on all functions in schema cp7_fabric_native from public,anon,authenticated,service_role;
