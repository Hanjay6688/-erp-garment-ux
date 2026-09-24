create or replace function public.show() returns table(d date, fg numeric, cogs numeric, oth_exp numeric, oth_inc numeric, wip numeric, cum_fg numeric, cum_cogs numeric, cum_wip numeric) language sql as $$
with x as(
 select j.transaction_date d,
  sum(case when l.mapping_key='FG_INVENTORY' then l.debit-l.credit else 0 end) fg,
  sum(case when l.mapping_key='COGS' then l.debit-l.credit else 0 end) cogs,
  sum(case when l.mapping_key='OTHER_EXPENSE' then l.debit-l.credit else 0 end) oe,
  sum(case when l.mapping_key='OTHER_INCOME' then l.debit-l.credit else 0 end) oi,
  sum(case when l.mapping_key='WIP' then l.debit-l.credit else 0 end) wip
 from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id group by 1)
select d,round(fg,2),round(cogs,2),round(oe,2),round(oi,2),round(wip,2),
 round(sum(fg) over(order by d),2),round(sum(cogs) over(order by d),2),round(sum(wip) over(order by d),2) from x order by d $$;
