-- OW-12a (owner D17-16): the official finance and HPP figures for factory-scale work, in bounded steps.
-- The figures are the accepted owner report read ONCE, in one statement, through cp7_finance.workspace (the reader of the
-- finance screen and of the direct analysis). Only the provenance scan of the direct analysis (every journal, journal
-- line, daily balance and cash account up to the report date) is split into chunks; the capture is sealed only when the
-- chunks hold exactly the rows counted in the report's own statement, and, when the report statement ran before its
-- transaction wrote anything, no scanned row changed after that statement's snapshot. Nothing here posts, closes or
-- changes a business row. Contract: docs/cp7/d17-14/ow12/KONTRAK_OW12A.md (cp7.finance-capture.v1).
create schema cp7_finance_capture authorization cp7_capture;
revoke all on schema cp7_finance_capture from public,anon,authenticated,service_role;

create table cp7_finance_capture.captures(id uuid primary key,actor uuid not null,
 owner_kind text not null check(owner_kind in('STAGED_ANALYSIS','STAGED_REPORT')),owner_id uuid not null,query jsonb not null,dates jsonb not null,
 access_at_start jsonb not null,state text not null check(state in('RUNNING','READY','FAILED')),
 units_done integer not null default 0 check(units_done>=0),units_total integer check(units_total>=2),unit_attempts integer not null default 0,
 report jsonb,report_snapshot pg_snapshot,report_read_at timestamptz,report_ms numeric,plan jsonb,book_signature text,source_hash text,
 failure_code text,failure_unit integer,created_at timestamptz not null,updated_at timestamptz not null,finished_at timestamptz,
 unique(owner_kind,owner_id),check((state='FAILED')=(failure_code is not null)),check((report is null)=(units_total is null)),
 check(units_total is null or units_done<=units_total),
 check(state<>'READY'or(units_done=units_total and book_signature is not null and source_hash is not null and finished_at is not null)));
-- One stored chunk of the provenance scan (unit 1..n): its family, key range, row count and digest.
create table cp7_finance_capture.chunks(capture_id uuid not null references cp7_finance_capture.captures(id),unit integer not null check(unit>=1),
 family text not null check(family in('journal','line','book','cash')),first_key text,last_key text,rows bigint not null check(rows>=0),
 digest text not null,server_ms numeric not null,primary key(capture_id,unit));
do $$declare t text;begin
 foreach t in array array['captures','chunks']loop
  execute format('alter table cp7_finance_capture.%I owner to cp7_capture',t);
  execute format('alter table cp7_finance_capture.%I enable row level security',t);
  execute format('create policy cp7_finance_capture_no_access on cp7_finance_capture.%I for all to public using(false)with check(false)',t);
  execute format('revoke all on cp7_finance_capture.%I from public,anon,authenticated,service_role',t);
 end loop;
end $$;

-- ------------------------------------------------- reads as the finance reader --
-- The report, its snapshot (only when this transaction has not written: a snapshot taken after a write cannot place
-- the transaction's own rows) and the row count of every scanned family, all in ONE statement.
create function cp7_finance_capture.report_unit(p_dates jsonb)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'set jit=off as $$
declare r jsonb;snap pg_snapshot;n_journal bigint;n_line bigint;n_book bigint;n_cash bigint;t0 timestamptz:=clock_timestamp();
 as_of date:=(p_dates->>'as_of')::date;
begin
 select cp7_finance.workspace(jsonb_build_object('from',p_dates->>'from','to',p_dates->>'to','as_of',p_dates->>'as_of','offset',0,'limit',25,'filing_id',null)),
  case when pg_current_xact_id_if_assigned()is null then pg_current_snapshot()end,
  (select count(*)from erp.journal_entries j where j.transaction_date<=as_of),
  (select count(*)from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.transaction_date<=as_of),
  (select count(*)from erp.account_daily_balances b where b.balance_date<=as_of),
  (select count(*)from erp.cash_accounts a)
 into r,snap,n_journal,n_line,n_book,n_cash;
 return jsonb_build_object('report',r,'snapshot',snap::text,'read_at',r->>'captured_at',
  'rows',jsonb_build_object('journal',n_journal,'line',n_line,'book',n_book,'cash',n_cash),
  'server_ms',round(extract(epoch from clock_timestamp()-t0)*1000,1));
end $$;

-- One chunk of the direct analysis' provenance scan: the same keys and facts (key || ':' || sha256(row as JSON)),
-- ordered by the family's own key, after p_after; p_limit null takes the rest of the family. "changed" counts scanned
-- rows inserted or last changed by a transaction the report's snapshot did not see (null snapshot: not counted).
create function cp7_finance_capture.book_chunk(p_family text,p_as_of date,p_after text,p_limit integer,p_snap pg_snapshot)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'set jit=off as $$
declare ref bigint:=pg_snapshot_xmax(pg_current_snapshot())::text::bigint;low bigint;base bigint;wrap bigint;r record;t0 timestamptz:=clock_timestamp();
begin
 -- A row's 32-bit xmin as the full id in the 2^32 window ending at this statement (cp7_analysis_stage.changes_since).
 low:=ref%4294967296;base:=ref-low;wrap:=greatest(ref-low-4294967296,0);
 if p_family='journal'then
  select count(*)n,(array_agg(s.k order by s.o))[1]first_key,(array_agg(s.k order by s.o desc))[1]last_key,
   encode(pg_catalog.sha256(convert_to(coalesce(string_agg(s.line,E'\n'order by s.o),''),'UTF8')),'hex')digest,
   count(*)filter(where p_snap is not null and not pg_visible_in_snapshot(s.x,p_snap))changed into r
  from(select j.id::text k,j.id o,'journal:'||j.id::text||':'||encode(pg_catalog.sha256(convert_to(to_jsonb(j)::text,'UTF8')),'hex')line,
    ((case when j.xmin::text::bigint<=low then base else wrap end)+j.xmin::text::bigint)::text::xid8 x
   from erp.journal_entries j where j.transaction_date<=p_as_of and(p_after is null or j.id>p_after::uuid)order by j.id limit p_limit)s;
 elsif p_family='line'then
  select count(*)n,(array_agg(s.k order by s.o))[1]first_key,(array_agg(s.k order by s.o desc))[1]last_key,
   encode(pg_catalog.sha256(convert_to(coalesce(string_agg(s.line,E'\n'order by s.o),''),'UTF8')),'hex')digest,
   count(*)filter(where p_snap is not null and not pg_visible_in_snapshot(s.x,p_snap))changed into r
  from(select l.id::text k,l.id o,'line:'||l.id::text||':'||encode(pg_catalog.sha256(convert_to(to_jsonb(l)::text,'UTF8')),'hex')line,
    ((case when l.xmin::text::bigint<=low then base else wrap end)+l.xmin::text::bigint)::text::xid8 x
   from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
   where j.transaction_date<=p_as_of and(p_after is null or l.id>p_after::uuid)order by l.id limit p_limit)s;
 elsif p_family='book'then
  select count(*)n,(array_agg(s.k order by s.a,s.d))[1]first_key,(array_agg(s.k order by s.a desc,s.d desc))[1]last_key,
   encode(pg_catalog.sha256(convert_to(coalesce(string_agg(s.line,E'\n'order by s.a,s.d),''),'UTF8')),'hex')digest,
   count(*)filter(where p_snap is not null and not pg_visible_in_snapshot(s.x,p_snap))changed into r
  from(select b.account_id::text||'|'||b.balance_date::text k,b.account_id a,b.balance_date d,
    'book:'||b.account_id::text||':'||b.balance_date::text||':'||encode(pg_catalog.sha256(convert_to(to_jsonb(b)::text,'UTF8')),'hex')line,
    ((case when b.xmin::text::bigint<=low then base else wrap end)+b.xmin::text::bigint)::text::xid8 x
   from erp.account_daily_balances b where b.balance_date<=p_as_of
    and(p_after is null or(b.account_id,b.balance_date)>(split_part(p_after,'|',1)::uuid,split_part(p_after,'|',2)::date))
   order by b.account_id,b.balance_date limit p_limit)s;
 elsif p_family='cash'then
  select count(*)n,(array_agg(s.k order by s.o))[1]first_key,(array_agg(s.k order by s.o desc))[1]last_key,
   encode(pg_catalog.sha256(convert_to(coalesce(string_agg(s.line,E'\n'order by s.o),''),'UTF8')),'hex')digest,
   count(*)filter(where p_snap is not null and not pg_visible_in_snapshot(s.x,p_snap))changed into r
  from(select a.id::text k,a.id o,'cash:'||a.id::text||':'||encode(pg_catalog.sha256(convert_to(to_jsonb(a)::text,'UTF8')),'hex')line,
    ((case when a.xmin::text::bigint<=low then base else wrap end)+a.xmin::text::bigint)::text::xid8 x
   from erp.cash_accounts a where p_after is null or a.id>p_after::uuid order by a.id limit p_limit)s;
 else raise exception 'CP7_FINANCE_CAPTURE_FAMILY';
 end if;
 return jsonb_build_object('rows',r.n,'first_key',r.first_key,'last_key',r.last_key,'digest',r.digest,'changed',r.changed,
  'server_ms',round(extract(epoch from clock_timestamp()-t0)*1000,1));
end $$;

-- The direct analysis' source hash over the sealed report and the chunked book signature.
create function cp7_finance_capture.seal_hash(p_report jsonb,p_book text)returns text
language sql immutable security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_analysis_native.financial_fingerprint(p_report,p_book)
$$;

grant usage,create on schema cp7_finance_capture to cp7_finance_read;
alter function cp7_finance_capture.report_unit(jsonb)owner to cp7_finance_read;
alter function cp7_finance_capture.book_chunk(text,date,text,integer,pg_snapshot)owner to cp7_finance_read;
alter function cp7_finance_capture.seal_hash(jsonb,text)owner to cp7_finance_read;
revoke create on schema cp7_finance_capture from cp7_finance_read;
revoke usage on schema cp7_finance_capture from cp7_finance_read;
revoke all on function cp7_finance_capture.report_unit(jsonb),cp7_finance_capture.book_chunk(text,date,text,integer,pg_snapshot),
 cp7_finance_capture.seal_hash(jsonb,text)from public,anon,authenticated,service_role;
grant execute on function cp7_finance_capture.report_unit(jsonb),cp7_finance_capture.book_chunk(text,date,text,integer,pg_snapshot),
 cp7_finance_capture.seal_hash(jsonb,text)to cp7_capture;

-- ------------------------------------------------------------- the job --
create function cp7_finance_capture.chunk_rows()returns integer language sql immutable set search_path=''as $$select 10000$$;

-- The status of one capture (cp7.finance-capture-status.v1); the caller checks the actor.
create function cp7_finance_capture.status_row(c cp7_finance_capture.captures)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('contract_version','cp7.finance-capture-status.v1','capture_id',c.id,'owner_kind',c.owner_kind,'owner_id',c.owner_id,
  'state',c.state,'units_done',c.units_done,'units_total',c.units_total,'report_read_at',c.report_read_at,'dates',c.dates,
  'readiness',case when c.report is null then null when c.report#>>'{snapshot,data_confidence,status}'='READY'then 'READY'
   when c.report#>>'{snapshot,data_confidence,status}'='RECALC_PENDING'then 'LIMITED'else 'BLOCKED'end,
  'failure_code',c.failure_code,'production_go',false)
$$;

create function cp7_finance_capture.status(p_capture uuid)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;c cp7_finance_capture.captures%rowtype;
begin
 a:=cp7_schedule_native.access_now(false);
 select *into c from cp7_finance_capture.captures x where x.id=p_capture;
 if c.id is null or c.actor<>(a->>'actor')::uuid then raise exception using errcode='42501',message='CP7_FINANCE_CAPTURE_UNAVAILABLE';end if;
 return cp7_finance_capture.status_row(c);
end $$;

-- The status of the capture an owning job started, or null when it has not started one.
create function cp7_finance_capture.status_of(p_kind text,p_owner uuid)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select cp7_finance_capture.status_row(c)from cp7_finance_capture.captures c where c.owner_kind=p_kind and c.owner_id=p_owner
$$;

-- One capture per owning job. The dates follow the direct analysis: the query's from/through and the Jakarta date of
-- p_at; a repeated call for the same job returns the same capture (its first p_at holds) or refuses another query.
create function cp7_finance_capture.start(p_kind text,p_owner uuid,p_query jsonb,p_at timestamptz)returns uuid
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;c cp7_finance_capture.captures%rowtype;d jsonb;id uuid;
begin
 a:=cp7_schedule_native.access_now(false);
 if not cp7_analysis_stage.report_finance_access(a,false)then raise exception using errcode='42501',message='CP7_FINANCE_CAPTURE_ACCESS';end if;
 if p_kind not in('STAGED_ANALYSIS','STAGED_REPORT')or p_owner is null or p_at is null or jsonb_typeof(p_query)is distinct from 'object'
  or coalesce(p_query->>'from_date','')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'or coalesce(p_query->>'through_date','')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'then
  raise exception 'CP7_FINANCE_CAPTURE_QUERY';end if;
 d:=jsonb_build_object('from',p_query->>'from_date','to',p_query->>'through_date','as_of',(p_at at time zone 'Asia/Jakarta')::date::text);
 if (d->>'from')::date>(d->>'to')::date or(d->>'to')::date>(d->>'as_of')::date then raise exception 'CP7_FINANCE_CAPTURE_QUERY';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:FINANCE_CAPTURE:'||p_kind||':'||p_owner::text,0));
 select *into c from cp7_finance_capture.captures x where x.owner_kind=p_kind and x.owner_id=p_owner;
 if c.id is not null then
  if c.actor<>(a->>'actor')::uuid or c.query<>p_query then raise exception 'CP7_FINANCE_CAPTURE_CHANGED';end if;
  return c.id;
 end if;
 id:=gen_random_uuid();
 insert into cp7_finance_capture.captures(id,actor,owner_kind,owner_id,query,dates,access_at_start,state,created_at,updated_at)
 values(id,(a->>'actor')::uuid,p_kind,p_owner,p_query,d,a,'RUNNING',clock_timestamp(),clock_timestamp());
 return id;
end $$;

-- One unit: 0 REPORT, 1..n one chunk of the plan, n+1 SEAL. Raises the refusal code; step() records it.
create function cp7_finance_capture.run_unit(p_capture uuid)returns void
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare c cp7_finance_capture.captures%rowtype;r jsonb;fam text;idx integer;k integer;u integer;v_after text;is_last boolean;n bigint;
 v_plan jsonb:='{}';total integer:=0;fams text[]:=array['journal','line','book','cash'];sealed text;
begin
 select *into c from cp7_finance_capture.captures x where x.id=p_capture;
 if c.units_done=0 then
  r:=cp7_finance_capture.report_unit(c.dates);
  if r->'report'is null or jsonb_typeof(r->'report')<>'object'then raise exception 'CP7_FINANCE_REPORT_INCOMPLETE';end if;
  foreach fam in array fams loop
   n:=(r->'rows'->>fam)::bigint;k:=ceil(n::numeric/cp7_finance_capture.chunk_rows())::integer;
   v_plan:=v_plan||jsonb_build_object(fam,jsonb_build_object('rows',n,'chunks',k));total:=total+k;
  end loop;
  update cp7_finance_capture.captures set report=r->'report',report_snapshot=(r->>'snapshot')::pg_snapshot,
   report_read_at=(r->>'read_at')::timestamptz,report_ms=(r->>'server_ms')::numeric,plan=v_plan,units_total=total+2,units_done=1,
   updated_at=clock_timestamp()where id=c.id;
  return;
 end if;
 if c.units_done<c.units_total-1 then
  u:=c.units_done;
  foreach fam in array fams loop
   k:=(c.plan->fam->>'chunks')::integer;
   if u<=k then idx:=u;exit;end if;
   u:=u-k;
  end loop;
  if idx is null then raise exception 'CP7_FINANCE_CAPTURE_INVARIANT';end if;
  is_last:=idx=(c.plan->fam->>'chunks')::integer;
  if idx>1 then select x.last_key into v_after from cp7_finance_capture.chunks x where x.capture_id=c.id and x.unit=c.units_done-1;end if;
  r:=cp7_finance_capture.book_chunk(fam,(c.dates->>'as_of')::date,v_after,case when is_last then null else cp7_finance_capture.chunk_rows()end,c.report_snapshot);
  if (r->>'changed')::bigint>0 then raise exception 'CP7_FINANCE_CAPTURE_SOURCE_CHANGED';end if;
  insert into cp7_finance_capture.chunks values(c.id,c.units_done,fam,r->>'first_key',r->>'last_key',(r->>'rows')::bigint,r->>'digest',(r->>'server_ms')::numeric);
  update cp7_finance_capture.captures set units_done=units_done+1,updated_at=clock_timestamp()where id=c.id;
  return;
 end if;
 -- SEAL: every family holds exactly the rows counted with the report (an insert or delete during the scan differs).
 foreach fam in array fams loop
  select coalesce(sum(x.rows),0)into n from cp7_finance_capture.chunks x where x.capture_id=c.id and x.family=fam;
  if n<>(c.plan->fam->>'rows')::bigint then raise exception 'CP7_FINANCE_CAPTURE_SOURCE_CHANGED';end if;
 end loop;
 if (select count(*)from cp7_finance_capture.chunks x where x.capture_id=c.id)<>c.units_total-2 then raise exception 'CP7_FINANCE_CAPTURE_INVARIANT';end if;
 select encode(pg_catalog.sha256(convert_to(coalesce(string_agg(x.family||':'||x.unit||':'||x.rows||':'||x.digest,E'\n'order by x.unit),''),'UTF8')),'hex')
  into sealed from cp7_finance_capture.chunks x where x.capture_id=c.id;
 update cp7_finance_capture.captures set book_signature=sealed,source_hash=cp7_finance_capture.seal_hash(c.report,sealed),
  units_done=units_total,state='READY',finished_at=clock_timestamp(),updated_at=clock_timestamp()where id=c.id;
end $$;

-- step: the actor's own capture, one unit per call. A concurrent caller runs nothing; access different from the start
-- (or no longer allowed to read owner finance) fails the capture; the statement limit is retried three times; any other
-- refusal fails the capture with its code. A failed or ready capture is returned as it is. The step holds an advisory
-- lock, not a row lock, so an untouched transaction reaches the report statement without a transaction id of its own.
create function cp7_finance_capture.step(p_capture uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;c cp7_finance_capture.captures%rowtype;
begin
 a:=cp7_schedule_native.access_now(false);
 select *into c from cp7_finance_capture.captures x where x.id=p_capture;
 if c.id is null or c.actor<>(a->>'actor')::uuid then raise exception using errcode='42501',message='CP7_FINANCE_CAPTURE_UNAVAILABLE';end if;
 if not pg_try_advisory_xact_lock(hashtextextended('CP7:FINANCE_CAPTURE_STEP:'||p_capture::text,0))then
  return cp7_finance_capture.status_row(c)||jsonb_build_object('worker_active',true);
 end if;
 select *into c from cp7_finance_capture.captures x where x.id=p_capture;
 if c.actor<>(a->>'actor')::uuid then raise exception using errcode='42501',message='CP7_FINANCE_CAPTURE_UNAVAILABLE';end if;
 if c.state='RUNNING'then
  if a is distinct from c.access_at_start or not cp7_analysis_stage.report_finance_access(a,false)then
   update cp7_finance_capture.captures set state='FAILED',failure_code='CP7_FINANCE_CAPTURE_ACCESS_CHANGED',failure_unit=units_done,
    finished_at=clock_timestamp(),updated_at=clock_timestamp()where id=c.id;
  else
   begin
    perform cp7_finance_capture.run_unit(c.id);
    update cp7_finance_capture.captures set unit_attempts=0 where id=c.id;
   exception
    when query_canceled then
     update cp7_finance_capture.captures set unit_attempts=unit_attempts+1,updated_at=clock_timestamp(),
      state=case when unit_attempts+1>=3 then 'FAILED'else state end,failure_unit=case when unit_attempts+1>=3 then units_done end,
      finished_at=case when unit_attempts+1>=3 then clock_timestamp()end,
      failure_code=case when unit_attempts+1>=3 then case when units_done=0 then 'CP7_FINANCE_REPORT_TIME_LIMIT'else 'CP7_FINANCE_CAPTURE_STOPPED'end end
     where id=c.id;
    when others then
     update cp7_finance_capture.captures set state='FAILED',failure_unit=units_done,finished_at=clock_timestamp(),updated_at=clock_timestamp(),
      failure_code=case when SQLSTATE='42501'then 'CP7_FINANCE_CAPTURE_ACCESS_CHANGED'when SQLERRM~'^CP7_[A-Z0-9_]+$'then SQLERRM
       else 'CP7_FINANCE_CAPTURE_ERROR'end where id=c.id;
   end;
  end if;
 end if;
 select *into c from cp7_finance_capture.captures x where x.id=p_capture;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_FINANCE_CAPTURE_ACCESS_CHANGED';end if;
 return cp7_finance_capture.status_row(c);
end $$;

-- The sealed figures, in the shape of cp7_analysis_native.financial_source (finance_apply reads it unchanged).
create function cp7_finance_capture.result(p_capture uuid)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;c cp7_finance_capture.captures%rowtype;
begin
 a:=cp7_schedule_native.access_now(false);
 select *into c from cp7_finance_capture.captures x where x.id=p_capture;
 if c.id is null or c.actor<>(a->>'actor')::uuid or not cp7_analysis_stage.report_finance_access(a,false)then
  raise exception using errcode='42501',message='CP7_FINANCE_CAPTURE_UNAVAILABLE';end if;
 if c.state<>'READY'then raise exception 'CP7_FINANCE_CAPTURE_NOT_READY';end if;
 return jsonb_build_object('contract_version','cp7.native-analysis-finance.v2','dates',c.dates,'book_signature',c.book_signature,
  'source_hash',c.source_hash,'report',c.report,
  'capture',jsonb_build_object('id',c.id,'units',c.units_total,'report_read_at',c.report_read_at,'report_ms',c.report_ms,'plan',c.plan,
   'change_check',case when c.report_snapshot is null then 'ROW_COUNTS'else 'ROW_COUNTS_AND_SNAPSHOT'end));
end $$;

-- Business Report v2 ACTUALS: start (once) and advance this job's capture by one unit; the sealed figures when ready,
-- null while running, the capture's refusal when it failed.
create function cp7_finance_capture.for_report(p_job uuid,p_query jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare id uuid;s jsonb;
begin
 id:=cp7_finance_capture.start('STAGED_REPORT',p_job,p_query,clock_timestamp());
 s:=cp7_finance_capture.step(id);
 if s->>'state'='READY'then return cp7_finance_capture.result(id);end if;
 if s->>'state'='FAILED'then raise exception '%',s->>'failure_code';end if;
 return null;
end $$;

-- The server runner's FINANCE family: the oldest running capture, one unit, as its own actor (as report_next).
create function cp7_finance_capture.run_next()returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare c cp7_finance_capture.captures%rowtype;s cp7_finance_capture.captures%rowtype;prior jsonb;found_one boolean:=false;
begin
 for c in select *from cp7_finance_capture.captures x where x.state='RUNNING'order by x.updated_at,x.id limit 20 loop
  if pg_try_advisory_xact_lock(hashtextextended('CP7:FINANCE_CAPTURE_STEP:'||c.id::text,0))then found_one:=true;exit;end if;
 end loop;
 if not found_one then return jsonb_build_object('ran',false,'outcome','IDLE');end if;
 prior:=jsonb_build_object('claims',current_setting('request.jwt.claims',true),'sub',current_setting('request.jwt.claim.sub',true),
  'claim',current_setting('request.jwt.claim',true));
 perform set_config('request.jwt.claims',jsonb_build_object('sub',c.actor,'role','authenticated')::text,true),
  set_config('request.jwt.claim.sub','',true),set_config('request.jwt.claim','',true);
 begin
  perform cp7_finance_capture.step(c.id);
 exception when others then
  update cp7_finance_capture.captures set state='FAILED',failure_unit=units_done,finished_at=clock_timestamp(),updated_at=clock_timestamp(),
   failure_code=case when SQLSTATE='42501'then 'CP7_FINANCE_CAPTURE_ACCESS_CHANGED'when SQLERRM~'^CP7_[A-Z0-9_]+$'then SQLERRM
    else 'CP7_FINANCE_CAPTURE_ERROR'end where id=c.id and state='RUNNING';
 end;
 perform set_config('request.jwt.claims',coalesce(prior->>'claims',''),true),set_config('request.jwt.claim.sub',coalesce(prior->>'sub',''),true),
  set_config('request.jwt.claim',coalesce(prior->>'claim',''),true);
 select *into s from cp7_finance_capture.captures where id=c.id;
 return jsonb_build_object('ran',true,'family','FINANCE','outcome',case when s.state='READY'then 'JOB_DONE'when s.state='FAILED'then 'JOB_FAILED'
  when s.units_done>c.units_done then 'UNIT_STORED'else 'UNIT_RETRY'end,'job_id',c.id,'unit',c.units_done,
  'units_done',s.units_done,'unit_count',s.units_total,'state',s.state);
end $$;

do $$declare f text;begin
 foreach f in array array['chunk_rows()','status_row(cp7_finance_capture.captures)','status(uuid)','status_of(text,uuid)',
  'start(text,uuid,jsonb,timestamptz)','run_unit(uuid)','step(uuid)','result(uuid)','for_report(uuid,jsonb)','run_next()']loop
  execute 'alter function cp7_finance_capture.'||f||' owner to cp7_capture';
  execute 'revoke all on function cp7_finance_capture.'||f||' from public,anon,authenticated,service_role';
 end loop;
end $$;
