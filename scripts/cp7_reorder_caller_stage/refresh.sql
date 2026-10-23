create or replace function cp7_stock_formula.refresh()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;result jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_stock_formula.access_now(false);
 if not pg_try_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0))then raise exception using errcode='55P03',message='CP7_FORMULA_BUSY';end if;
 result:=cp7_stock_formula.compute(clock_timestamp(),interval'3 seconds');
 if cp7_stock_formula.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_FORMULA_ACCESS_CHANGED';end if;
 return result;
end $$;
