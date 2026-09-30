-- F04/P07. Supplied-history kernel only; no ERP reads, writes, migration or RPC.
-- Exact cohorts deliberately abstain rather than extrapolate size/length/width.
create schema cp7_yield authorization cp7_capture;
revoke all on schema cp7_yield from public,anon,authenticated,service_role;

create function cp7_yield.key(v jsonb) returns text
language plpgsql immutable security invoker set search_path='' as $$
begin
 if jsonb_typeof(v) is distinct from 'string' or length(v#>>'{}') not between 1 and 200
    or btrim(v#>>'{}')<>(v#>>'{}') then raise exception 'YIELD_KEY'; end if;
 return v#>>'{}';
end $$;
create function cp7_yield.quantity(v jsonb, pcs boolean default false) returns numeric
language plpgsql immutable security invoker set search_path='' as $$
begin
 if jsonb_typeof(v) is distinct from 'string' or (v#>>'{}') !~ '^(0|[1-9][0-9]{0,29})(\.[0-9]{1,12})?$'
    or (pcs and (v#>>'{}') !~ '^(0|[1-9][0-9]{0,29})$') then raise exception 'YIELD_QUANTITY'; end if;
 return (v#>>'{}')::numeric;
end $$;
create function cp7_yield.day(v jsonb) returns date
language plpgsql immutable security invoker set search_path='' as $$
declare d date;
begin
 if jsonb_typeof(v) is distinct from 'string' or (v#>>'{}') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'YIELD_DAY'; end if;
 d := (v#>>'{}')::date;
 if to_char(d,'YYYY-MM-DD')<>v#>>'{}' then raise exception 'YIELD_DAY'; end if;
 return d;
end $$;
create function cp7_yield.mix(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare x jsonb;
begin
 if jsonb_typeof(v) is distinct from 'array' or jsonb_array_length(v) not between 1 and 100 then raise exception 'YIELD_MIX'; end if;
 for x in select value from jsonb_array_elements(v) loop perform cp7_yield.key(x); end loop;
 return (select jsonb_agg(value order by (value#>>'{}') collate "C") from jsonb_array_elements(v));
end $$;
create function cp7_yield.features(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare width jsonb; marker jsonb;
begin
 if jsonb_typeof(v) is distinct from 'object' then raise exception 'YIELD_INPUT'; end if;
 perform cp7_yield.key(v->'rollId'); perform cp7_yield.key(v->'rollRevision');
 if v#>>'{consumed,unit}' is distinct from 'M' or cp7_yield.quantity(v#>'{consumed,value}')<=0 then raise exception 'YIELD_LENGTH'; end if;
 if not v ? 'usableWidthCm' or not v ? 'markerRevision' or jsonb_typeof(v->'outputComplete') is distinct from 'boolean' then raise exception 'YIELD_INPUT'; end if;
 width := v->'usableWidthCm'; marker := v->'markerRevision';
 if width<>'null'::jsonb then
  if cp7_yield.quantity(width)<=0 then raise exception 'YIELD_WIDTH'; end if;
  width:=to_jsonb(trim_scale(cp7_yield.quantity(width))::text);
 end if;
 if marker<>'null'::jsonb then perform cp7_yield.key(marker); end if;
 if v->'observedCutPcs'<>'null'::jsonb then perform cp7_yield.quantity(v->'observedCutPcs',true);
 elsif v->'outputComplete'='true'::jsonb then raise exception 'YIELD_COMPLETE_WITHOUT_PCS'; end if;
 if not v ? 'observedCutPcs' then raise exception 'YIELD_PCS'; end if;
 return jsonb_build_object('material',cp7_yield.key(v->'materialId'),
  'brand',cp7_yield.key(v#>'{materialFamily,brandId}'),'mill',cp7_yield.key(v#>'{materialFamily,millId}'),
  'pattern',cp7_yield.key(v->'patternId'),'patternRevision',cp7_yield.key(v->'patternRevision'),
  'marker',marker,'mix',cp7_yield.mix(v->'sizeSlots'),'length',trim_scale(cp7_yield.quantity(v#>'{consumed,value}'))::text,'width',width);
end $$;

create function cp7_yield.review(request jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare
 i jsonb:=request->'input'; ctx jsonb:=request->'context'; p jsonb:=request->'policy'; h jsonb:=request->'history';
 f jsonb; history_row jsonb; base jsonb; cohort jsonb; identity_count integer; n integer; minimum integer;
 qlo numeric; qhi numeric; lo numeric; hi numeric; actual numeric; start_day date; asof_day date;
begin
 if request->>'contract' is distinct from 'f04.yield-history-request.v1' or jsonb_typeof(h) is distinct from 'array'
    or jsonb_array_length(h)>1000 or jsonb_typeof(p) is distinct from 'object' then raise exception 'YIELD_REQUEST'; end if;
 perform cp7_yield.key(ctx->'runId'); perform cp7_yield.key(ctx->'actorScope'); perform cp7_yield.key(ctx->'accessEpoch');
 if jsonb_typeof(request->'inputKey') is distinct from 'string' or length(request->>'inputKey') not between 1 and 20000 then raise exception 'YIELD_INPUT_KEY'; end if;
 f:=cp7_yield.features(i);
 minimum:=cp7_yield.quantity(p->'minimumPeers',true)::integer;
 qlo:=cp7_yield.quantity(p->'lowerQuantile'); qhi:=cp7_yield.quantity(p->'upperQuantile');
 start_day:=cp7_yield.day(p->'windowStart'); asof_day:=cp7_yield.day(p->'asOf');
 if minimum not between 2 and 1000 or qlo<0 or qhi>1 or qlo>=qhi or start_day>asof_day then raise exception 'YIELD_POLICY'; end if;
 base:=jsonb_build_object('contract','f04.cutting-yield-preview.v1','fixtureKind','SYNTHETIC_ONLY',
   'inputKey',request->'inputKey','context',ctx,'modelVersion','f04-exact-cohort-empirical-v1','policyVersion',cp7_yield.key(p->'version'));
 for history_row in select value from jsonb_array_elements(h) loop
  perform cp7_yield.key(history_row->'actorScope'); perform cp7_yield.key(history_row->'sourceRevision');
  if cp7_yield.quantity(history_row->'revisionSequence',true)<1 or coalesce(history_row->>'state','') not in ('ACTIVE','VOID') then raise exception 'YIELD_HISTORY_REVISION'; end if;
  perform cp7_yield.day(history_row->'occurredOn'); perform cp7_yield.day(history_row->'knownOn');
  if cp7_yield.day(history_row->'knownOn')<cp7_yield.day(history_row->'occurredOn') then raise exception 'YIELD_HISTORY_DATE'; end if;
  perform cp7_yield.features(history_row->'input');
 end loop;
 -- Exact duplicates collapse. Conflicting revisions fail closed, even out of cohort.
 if exists(select 1 from jsonb_array_elements(h) a join jsonb_array_elements(h) b
   on a.value#>>'{input,rollId}'=b.value#>>'{input,rollId}' and a.value->'actorScope'=b.value->'actorScope'
   and cp7_yield.quantity(a.value->'revisionSequence',true)=cp7_yield.quantity(b.value->'revisionSequence',true)
   where a.value<>b.value) then raise exception 'YIELD_CONFLICTING_REVISION'; end if;
 if i->'outputComplete'<>'true'::jsonb or i->'observedCutPcs'='null'::jsonb then
  return base||jsonb_build_object('status','INCOMPLETE','reason','Hasil potong final belum lengkap. Lebar tetap opsional; jumlah kosong bukan nol PCS.');
 end if;
 with known as (
  select distinct value as r from jsonb_array_elements(h)
  where value->>'actorScope'=ctx->>'actorScope' and cp7_yield.day(value->'knownOn')<=asof_day
 ), latest as (
  select distinct on (r#>>'{input,rollId}') r from known
  order by r#>>'{input,rollId}',cp7_yield.quantity(r->'revisionSequence',true) desc
 ), eligible as (
  select r,cp7_yield.features(r->'input') as rf from latest
  where r->>'state'='ACTIVE' and r#>>'{input,rollId}'<>i->>'rollId'
   and r#>'{input,outputComplete}'='true'::jsonb
   and cp7_yield.day(r->'occurredOn') between start_day and asof_day
 ), same_identity as (
  select * from eligible where rf-array['length','width']=f-array['length','width']
 ), exact_cohort as (
  select r from same_identity where rf->'length'=f->'length'
   and (f->'width'='null'::jsonb or rf->'width'=f->'width')
 ) select (select count(*) from same_identity),coalesce(jsonb_agg(r order by r#>>'{input,rollId}'),'[]'::jsonb)
 into identity_count,cohort from exact_cohort;
 n:=jsonb_array_length(cohort);
 if identity_count=0 then return base||jsonb_build_object('status','UNSEEN_COMBINATION','reason','Kombinasi bahan/pola/marker dan frekuensi ukuran ini belum dikenal. Campuran lain tidak dipinjam.'); end if;
 if n=0 then return base||jsonb_build_object('status','UNSEEN_COMBINATION','reason','Belum ada pembanding pada panjang terpakai dan lebar yang diisi. Tidak memakai perkalian meter atau lebar rekaan.'); end if;
 if n<minimum then return base||jsonb_build_object('status','INSUFFICIENT','reason',format('Pembanding sebanding %s roll; kebijakan uji meminta %s. Umur data satu tahun tidak otomatis cukup.',n,minimum)); end if;
 -- Numeric order statistics: ceil(q*n), clamped at 1. No float PCS/math in JSX.
 select pcs into lo from (select cp7_yield.quantity(value#>'{input,observedCutPcs}',true) pcs from jsonb_array_elements(cohort)) s
 order by pcs offset greatest(ceil(qlo*n)::integer-1,0) limit 1;
 select pcs into hi from (select cp7_yield.quantity(value#>'{input,observedCutPcs}',true) pcs from jsonb_array_elements(cohort)) s
 order by pcs offset greatest(ceil(qhi*n)::integer-1,0) limit 1;
 actual:=cp7_yield.quantity(i->'observedCutPcs',true);
 return base||jsonb_build_object('status','READY','assessment',case when actual<lo then 'LOW' when actual>hi then 'HIGH' else 'NORMAL' end,
  'interval',jsonb_build_object('lower',lo::text,'upper',hi::text,'unit','PCS','kind','EMPIRICAL_REFERENCE',
    'basis',case when f->'width'='null'::jsonb then 'WITHOUT_WIDTH' else 'WITH_RECORDED_WIDTH' end,'qualification','FIXTURE_ONLY_NOT_CALIBRATED'),
  'peers',(select jsonb_agg(jsonb_build_object('rollId',value#>>'{input,rollId}','sourceRevision',value->>'sourceRevision') order by value#>>'{input,rollId}') from jsonb_array_elements(cohort)),
  'periodStart',(select min(value->>'occurredOn') from jsonb_array_elements(cohort)),
  'periodEnd',(select max(value->>'occurredOn') from jsonb_array_elements(cohort)),
  'reasons',jsonb_build_array(format('%s roll sebanding: bahan/merek/pabrik, revisi pola, marker, frekuensi ukuran dan panjang terpakai sama.',n),
   format('Batas adalah urutan ceil(q × n): q bawah %s, q atas %s. Parameter kebijakan demonstrasi, belum patokan pabrik.',qlo,qhi),
   'Satu revisi terbaru per roll sebelum cutoff; roll saat ini, pembatalan, data masa depan dan scope lain dikeluarkan.'),
  'findings',jsonb_build_array(case when f->'width'='null'::jsonb then 'Lebar belum tercatat. Variasi batch tercampur; penyebab selisih belum diketahui.'
    else format('Lebar batch yang diisi %s cm; pembanding memakai lebar tersebut. Isian belum membuktikan lebar fisik.',i->>'usableWidthCm') end)
    ||case when i#>'{measurements,issuedMeasuredM}' is not null and i#>'{measurements,issuedMeasuredM}'<>'null'::jsonb
       and cp7_yield.quantity(i#>'{measurements,issuedMeasuredM}')<>cp7_yield.quantity(i#>'{measurements,issuedDeclaredM}')
      then jsonb_build_array(format('Pengukuran yang disuplai: catatan %s M versus terukur %s M. Penyebab selisih panjang belum diketahui. Pembanding memakai meter terpakai %s M; bukti kartu ini hanya contoh.',
       i#>>'{measurements,issuedDeclaredM}',i#>>'{measurements,issuedMeasuredM}',i#>>'{consumed,value}')) else '[]'::jsonb end,
  'checks',jsonb_build_array('Ukur meter terpakai dan sisa fisik; cocokkan pencatatan jumlah serta komponen potongan.',
    'Periksa cacat kain, scrap, recut, marker dan lebar efektif. Hasil potong bukan GOOD/FG.',
    'Selisih tidak membuktikan bahan diambil atau BS tertentu; penyebab memerlukan pemeriksaan lapangan.'));
end $$;

alter function cp7_yield.key(jsonb) owner to cp7_capture;
alter function cp7_yield.quantity(jsonb,boolean) owner to cp7_capture;
alter function cp7_yield.day(jsonb) owner to cp7_capture;
alter function cp7_yield.mix(jsonb) owner to cp7_capture;
alter function cp7_yield.features(jsonb) owner to cp7_capture;
alter function cp7_yield.review(jsonb) owner to cp7_capture;
revoke all on all functions in schema cp7_yield from public,anon,authenticated,service_role;
