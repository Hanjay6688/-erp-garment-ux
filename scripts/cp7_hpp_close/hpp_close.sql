-- OW-07 (owner D17-13 kelompok 3, D17-14): the close engine names HPP pools that are not divided yet.
--
-- erp.period_blockers_v1 (close, close preview and report confidence) gets one extra `return query` from
-- cp7_hpp_close.blockers_v1(p_through). Nothing here writes; the reader only reads the Native pocket and attendance tables.
--   POCKET_USAGE_UNALLOCATED (POLICY): posted pocket fabric usage dated on or before the date, with a value, that no
--     active pocket period has taken as a source (daily usage and opening usage imported as not yet allocated).
--   ATTENDANCE_POOL_NOT_ACTIVE (POLICY): approved/paid attendance of a normal Mandor (the exact Native manifest) in a
--     payroll period ending on or before the date that no ACTIVE attendance pool has taken as a source.
--   ATTENDANCE_POOL_POLICY_MISSING (POLICY): the Native preview refuses the period because a Mandor's attendance payroll
--     has no HPP policy covering it, so no pool can be made until the policy is set.
--   ATTENDANCE_POOL_SOURCE_UNCLEAR (POLICY): the Native preview refuses the period because an attendance total does not
--     match its items or its WIP accrual line is not exactly one.
--   ATTENDANCE_POOL_ZERO_OUTPUT (INFO): uncovered attendance in a period without any normal-Mandor sewing; the Native
--     rule keeps that cost in WIP without a PO and no pool can divide it, so it is reported, not blocking.
-- The preview conditions are the Native erp.preview_attendance_hpp_pool_v1 queries; the preview itself is not called
-- because it requires an internal caller and the report runs as the signed-in user.
-- Every reference value is text, a date, a boolean or null (the client reads numbers only as strings).
create schema cp7_hpp_close;
revoke all on schema cp7_hpp_close from public;

create function cp7_hpp_close.blockers_v1(p_through date)
returns table(family text,code text,severity text,scope text,impact_date date,reference jsonb,reason text)
language plpgsql stable security definer set search_path=''as $$
declare
 v_period record;
 v_manifest jsonb;
 v_missing bigint;
 v_unclear bigint;
 v_count bigint;
 v_amount numeric;
 v_payrolls jsonb;
 v_active jsonb;
begin
 if p_through is null then raise exception 'CP7_HPP_CLOSE_DATE_REQUIRED';end if;

 return query
 with usage as(
  select 'DAILY'::text kind,u.adjustment_id id,erp._cp3_business_date(h.physical_at) d,
   round(-((erp._cp6_material_adjustment_revaluation_state(h.id)->>'current_value')::numeric),2) amount
  from erp.pocket_fabric_usage u join erp.material_adjustments h on h.id=u.adjustment_id
  where h.status='POSTED' and erp._cp3_business_date(h.physical_at)<=p_through
   and not exists(select 1 from erp.pocket_period_sources s where s.adjustment_id=u.adjustment_id and erp.pocket_period_active_v1(s.pool_id))
  union all
  select 'OPENING'::text,u.id,u.physical_date,round(erp.be_pocket_usage_amount_v1(u.id),2)
  from erp.be_pocket_usage_v1 u
  where u.allocation_status='UNALLOCATED' and u.physical_date<=p_through
   and not exists(select 1 from erp.pocket_period_sources s where s.historical_usage_id=u.id and erp.pocket_period_active_v1(s.pool_id))
 ),valued as(
  select x.*,row_number()over(order by x.d,x.id) n from usage x where x.amount<>0
 )
 select 'HPP_POOL'::text,'POCKET_USAGE_UNALLOCATED'::text,'POLICY'::text,'AS_OF'::text,min(v.d),
  jsonb_build_object('usage_count',count(*)::text,'amount',sum(v.amount)::numeric(20,2)::text,'first_date',min(v.d),'last_date',max(v.d),
   'usages',coalesce(jsonb_agg(jsonb_build_object('kind',v.kind,'id',v.id,'date',v.d,'amount',v.amount::numeric(20,2)::text)order by v.n)
    filter(where v.n<=50),'[]'::jsonb),'usages_truncated',count(*)>50),
  format('%s pemakaian kain kantong senilai Rp%s (tanggal %s sampai %s) belum dibagi ke HPP. Buka Gudang > Kain kantong, bagian "Bagi ke HPP per periode", lalu bagi periode yang mencakup tanggal itu.',
   count(*),sum(v.amount)::numeric(20,2),min(v.d),max(v.d))
 from valued v
 having count(*)>0;

 -- One row per payroll period ending on or before the date with an attendance payroll no ACTIVE pool has taken that a
 -- pool would take (the Native manifest's latest covering policy is a normal Mandor) or that stops the pool (a Mandor
 -- without a covering policy). Special Mandors and Mandors without required attendance never start a manifest read.
 for v_period in
  select ps.period_start,ps.period_end
  from erp.payroll_settlements ps join erp.contractors c on c.id=ps.contractor_id
  left join lateral(
   select p.contractor_role_snapshot,p.attendance_required_snapshot,p.is_special
   from erp.contractor_hpp_policy_versions p
   where p.contractor_id=ps.contractor_id and p.effective_from<=ps.period_start
    and(p.effective_to is null or p.effective_to>=ps.period_end)
   order by p.effective_from desc,p.id desc limit 1
  )pol on true
  where ps.status in('APPROVED','PAID')and ps.attendance_total>0 and ps.period_end<=p_through
   and((pol.contractor_role_snapshot is null and c.contractor_type='MANDOR')
    or(pol.contractor_role_snapshot='MANDOR' and pol.attendance_required_snapshot and not pol.is_special))
   and not exists(select 1 from erp.attendance_hpp_pool_sources s join erp.attendance_hpp_pools hp on hp.id=s.pool_id
    where s.payroll_id=ps.id and hp.status='ACTIVE')
  group by ps.period_start,ps.period_end
  order by ps.period_end,ps.period_start
 loop
  select coalesce(jsonb_agg(hp.pool_number order by hp.pool_number),'[]'::jsonb)into v_active
  from erp.attendance_hpp_pools hp
  where hp.period_start=v_period.period_start and hp.period_end=v_period.period_end and hp.status='ACTIVE';

  -- Native preview refusal 1: a Mandor attendance payroll without one HPP policy covering the full period.
  select count(*),coalesce(jsonb_agg(ps.id order by ps.id),'[]'::jsonb)into v_missing,v_payrolls
  from erp.payroll_settlements ps join erp.contractors c on c.id=ps.contractor_id
  where ps.status in('APPROVED','PAID')and ps.period_start=v_period.period_start and ps.period_end=v_period.period_end
   and ps.attendance_total>0 and c.contractor_type='MANDOR'
   and not exists(select 1 from erp.contractor_hpp_policy_versions p where p.contractor_id=ps.contractor_id
    and p.effective_from<=v_period.period_start and(p.effective_to is null or p.effective_to>=v_period.period_end));
  if v_missing>0 then
   return query select 'HPP_POOL'::text,'ATTENDANCE_POOL_POLICY_MISSING'::text,'POLICY'::text,'AS_OF'::text,v_period.period_end,
    jsonb_build_object('period_start',v_period.period_start,'period_end',v_period.period_end,'payroll_ids',v_payrolls,'active_pools',v_active),
    format('Upah absen periode %s sampai %s belum bisa dibagi ke HPP: %s payroll mandor belum punya kebijakan HPP untuk seluruh periode itu. Isi kebijakannya di Master Data > Mandor, lalu buat dan aktifkan pool di Keuangan > HPP & Rekalkulasi.',
     v_period.period_start,v_period.period_end,v_missing);
   continue;
  end if;

  -- Native preview refusals 2 and 3: totals that do not match their items, or no single WIP accrual line.
  select count(*)into v_unclear from erp.payroll_settlements ps
  where ps.status in('APPROVED','PAID')and ps.period_start=v_period.period_start and ps.period_end=v_period.period_end
   and(abs(ps.attendance_total-coalesce((select sum(pai.amount)from erp.payroll_attendance_items pai where pai.payroll_id=ps.id),0))>0.01
    or(ps.attendance_total>0 and not exists(
     select 1 from(select count(*)line_count,max(jl.debit)debit_amount from erp.journal_entries je
      join erp.journal_lines jl on jl.journal_entry_id=je.id
      where je.source_id=ps.id and je.source_type='PAYROLL_ATTENDANCE_ACCRUAL' and je.status='POSTED'
       and jl.account_id=erp.account_id('WIP')and jl.debit>0)x
     where x.line_count=1 and x.debit_amount+0.01>=ps.attendance_total)));
  if v_unclear>0 then
   return query select 'HPP_POOL'::text,'ATTENDANCE_POOL_SOURCE_UNCLEAR'::text,'POLICY'::text,'AS_OF'::text,v_period.period_end,
    jsonb_build_object('period_start',v_period.period_start,'period_end',v_period.period_end,'payroll_count',v_unclear::text,'active_pools',v_active),
    format('Upah absen periode %s sampai %s belum bisa dibagi ke HPP: %s payroll punya total absen yang tidak sama dengan rinciannya atau jurnal akrual absennya tidak tunggal. Periksa payroll periode itu di Keuangan > Payroll & Kasbon.',
     v_period.period_start,v_period.period_end,v_unclear);
   continue;
  end if;

  -- The exact Native sources of a pool for this period, less those an ACTIVE pool already took.
  v_manifest:=erp._build_attendance_hpp_manifest_v1(v_period.period_start,v_period.period_end);
  select count(*),coalesce(sum((src->>'attendance_amount_cents')::bigint),0)/100.0,
   coalesce(jsonb_agg(src->>'payroll_id' order by src->>'payroll_id'),'[]'::jsonb)
  into v_count,v_amount,v_payrolls
  from jsonb_array_elements(v_manifest->'sources')src
  where not exists(select 1 from erp.attendance_hpp_pool_sources s join erp.attendance_hpp_pools hp on hp.id=s.pool_id
   where s.payroll_id=(src->>'payroll_id')::uuid and hp.status='ACTIVE');
  continue when v_count=0;
  if coalesce((v_manifest->>'denominator_qty')::bigint,0)<=0 then
   return query select 'HPP_POOL'::text,'ATTENDANCE_POOL_ZERO_OUTPUT'::text,'INFO'::text,'AS_OF'::text,v_period.period_end,
    jsonb_build_object('period_start',v_period.period_start,'period_end',v_period.period_end,'payroll_ids',v_payrolls,
     'amount',v_amount::numeric(20,2)::text,'active_pools',v_active),
    format('Upah absen periode %s sampai %s senilai Rp%s tidak bisa dibagi ke HPP karena tidak ada jahitan selesai mandor biasa pada periode itu; biayanya tetap di WIP tanpa PO.',
     v_period.period_start,v_period.period_end,v_amount::numeric(20,2));
  else
   return query select 'HPP_POOL'::text,'ATTENDANCE_POOL_NOT_ACTIVE'::text,'POLICY'::text,'AS_OF'::text,v_period.period_end,
    jsonb_build_object('period_start',v_period.period_start,'period_end',v_period.period_end,'payroll_ids',v_payrolls,
     'amount',v_amount::numeric(20,2)::text,'active_pools',v_active),
    case when jsonb_array_length(v_active)=0 then
     format('Upah absen periode %s sampai %s senilai Rp%s (%s payroll) belum dibagi ke HPP. Buat lalu aktifkan pool absen periode itu di Keuangan > HPP & Rekalkulasi.',
      v_period.period_start,v_period.period_end,v_amount::numeric(20,2),v_count)
    else
     format('Pool absen aktif %s untuk periode %s sampai %s belum mencakup %s payroll senilai Rp%s yang disetujui sesudahnya. Batalkan pool itu lalu buat dan aktifkan pool pengganti di Keuangan > HPP & Rekalkulasi.',
      v_active->>0,v_period.period_start,v_period.period_end,v_count,v_amount::numeric(20,2))
    end;
  end if;
 end loop;
end $$;
alter function cp7_hpp_close.blockers_v1(date)owner to postgres;
revoke all on function cp7_hpp_close.blockers_v1(date)from public,anon,authenticated,service_role;
