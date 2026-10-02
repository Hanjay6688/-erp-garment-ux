// @vitest-environment node
import { readFileSync } from 'node:fs'
import { expect, test } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'

test('private Original admission preserves own actor, current capabilities and final-reader separation', async () => {
  // SQL control with explicit Auth stubs: no Native, HTTP or family acceptance.
  const db = await openRuntime()
  const actor = '00000000-0000-4000-8000-000000000001'
  const run = '00000000-0000-4000-8000-000000000003'
  const ops = ['master.product.view', 'production.wip.view', 'warehouse.stock.view', 'sales.invoice.view']
  const rights = [...ops, 'finance.reports.view', 'finance.period_close.manage']
  const source = readFileSync('scripts/cp7-src/reminders/attention.sql', 'utf8')
  const helper = source.slice(source.indexOf('grant usage,create on schema cp7_reminder_native'), source.indexOf('-- Revalidate the complete current capability set'))
  const functionSql = (name: string, next: string) => source.slice(source.indexOf(`create function cp7_reminder_native.${name}`), source.indexOf(next))
  // The native kernel runtime opens a fresh psql session for each query.
  // Establish the stub settings AND role in the same session as the actual
  // private function call; a previous SET cannot stand in for that context.
  const configuration: Record<string, unknown> = {}
  let principal = 'cp7_reminder'
  const setting = async (key: string, value: unknown) => { configuration[key] = value }
  const contextual = async (sql: string) => (await db.query(`select public.control_authority_query(
    ${jsonArg(sql)}#>>'{}',${jsonArg(configuration)},${jsonArg(principal)}#>>'{}') result`))[0].result
  const pocket = () => contextual(`select cp7_reminder_native.original_authority('${run}') result`)
  try {
    await db.execute(`create role cp7_reminder nologin;
      create schema cp7_reminder_native authorization cp7_reminder;
      create schema cp7_analysis_native authorization cp7_capture;
      create schema auth;create schema erp;
      create function auth.uid()returns uuid language sql as $$select current_setting('test.actor')::uuid$$;
      create function auth.jwt()returns jsonb language sql as $$select '{"role":"authenticated"}'::jsonb$$;
      create function erp.get_my_access_v1()returns jsonb language sql as $$select
        jsonb_build_object('allowed',current_setting('test.allowed')::boolean,'profile',jsonb_build_object('role_code',current_setting('test.role')),
          'permissions',current_setting('test.rights')::jsonb)$$;
      create function erp.has_permission(k text)returns boolean language sql as $$select current_setting('test.rights')::jsonb?k$$;
      create table cp7_analysis_native.runs(id uuid,actor uuid,result jsonb,facts jsonb);
      alter table cp7_analysis_native.runs owner to cp7_capture;
      alter table cp7_analysis_native.runs enable row level security;
      create policy denied on cp7_analysis_native.runs using(false)with check(false);
      revoke all on cp7_analysis_native.runs from public,anon,authenticated,service_role;
      grant usage on schema auth,erp to cp7_capture,cp7_reminder;
      create function public.erp_cp7_read_analysis_v1(p_run uuid)returns jsonb language plpgsql volatile security definer set search_path=''as $$
       begin raise exception 'CONTROL_FRESH_SOURCE_REQUIRED';end $$;
      revoke all on function public.erp_cp7_read_analysis_v1(uuid)from public,anon,authenticated,service_role;
      grant execute on function public.erp_cp7_read_analysis_v1(uuid)to cp7_reminder;
      ${helper}
      ${functionSql('access_now(', '-- Private admission only:')}
      ${functionSql('recheck(', 'create function cp7_reminder_native.workspace(')}
      alter function cp7_reminder_native.access_now(uuid)owner to cp7_reminder;
      alter function cp7_reminder_native.recheck(jsonb,text)owner to cp7_reminder;
      revoke all on all functions in schema cp7_reminder_native from public,anon,authenticated,service_role;
      grant execute on function cp7_reminder_native.original_authority(uuid)to cp7_reminder;
      grant usage on schema cp7_reminder_native to authenticated;
      create function public.control_authority_query(q text,settings jsonb,principal text)returns jsonb
      language plpgsql security invoker set search_path=''as $$
      declare setting record;result jsonb;
      begin
       for setting in select key,value from jsonb_each(settings)loop
        perform set_config('test.'||setting.key,setting.value#>>'{}',true);
       end loop;
       perform set_config('role',principal,true);
       execute 'select coalesce(jsonb_agg(t),''[]''::jsonb)from ('||q||')t'into result;
       return result;
      end $$;`)
    await setting('actor', actor);await setting('allowed', true);await setting('role', 'OWNER');await setting('rights', rights)
    const original = { snapshot: { source_hash: 's'.repeat(64) }, semantic_hash: 'h'.repeat(64), recommendations: [{ target: { key: 'PRODUCT:SIZE' }, q_conditional: { value: '9007199254740993.01' } }], never_admit: 'SECRET_AMOUNT'.repeat(200000) }
    await db.execute(`insert into cp7_analysis_native.runs values('${run}','${actor}',${jsonArg(original)},
      '{"financial_source":{"report":{"close_preflight":{},"secret_balance":"12345.67"}}}'::jsonb);`)
    const admitted = (await pocket())[0].result
    expect(admitted.analysis.analysis.recommendations).toEqual([{ target: { key: 'PRODUCT:SIZE' } }])
    expect(admitted.analysis.analysis.snapshot).toEqual(original.snapshot)
    expect(admitted.analysis.analysis.semantic_hash).toBe(original.semantic_hash)
    expect(admitted.analysis.financial_source).toEqual({ report: { close_preflight: {} } })
    expect(admitted.analysis).not.toHaveProperty('source_state')
    expect(JSON.stringify(admitted).length).toBeLessThan(2000)
    expect(JSON.stringify(admitted)).not.toMatch(/SECRET_AMOUNT|9007199254740993|secret_balance/)
    await expect(contextual(`select cp7_reminder_native.access_now('${run}')`)).rejects.toThrow('CONTROL_FRESH_SOURCE_REQUIRED')
    expect((await pocket())[0].result).toEqual(admitted)
    for (const right of rights) {
      await setting('rights', rights.filter(x => x !== right))
      await expect(pocket()).rejects.toThrow(right.startsWith('finance.') ? 'CP7_ANALYSIS_FINANCE_ACCESS_DENIED' : 'CP7_REMINDER_ACCESS_DENIED')
      await expect(contextual(`select cp7_reminder_native.recheck(${jsonArg(admitted)})`)).rejects.toThrow()
    }
    await setting('rights', rights);await setting('role', 'STAFF')
    await expect(pocket()).rejects.toThrow('CP7_ANALYSIS_FINANCE_ACCESS_DENIED')
    await setting('role', 'OWNER');await setting('actor', '00000000-0000-4000-8000-000000000002')
    await expect(pocket()).rejects.toThrow('CP7_ANALYSIS_RUN_UNAVAILABLE')
    await setting('actor', actor);await setting('allowed', false)
    await expect(pocket()).rejects.toThrow('CP7_REMINDER_ACCESS_DENIED')
    await setting('allowed', true);principal = 'authenticated'
    await expect(pocket()).rejects.toThrow(/permission denied/)
    const privileges = (await db.query(`select pg_get_userbyid(proowner) owner,prosecdef definer,
      has_function_privilege('authenticated',oid,'EXECUTE') exposed,
      has_schema_privilege('cp7_capture','cp7_reminder_native','CREATE') ddl
      from pg_proc where oid='cp7_reminder_native.original_authority(uuid)'::regprocedure`))[0]
    expect(privileges).toEqual({ owner: 'cp7_capture', definer: true, exposed: false, ddl: false })
  } finally { await db.close() }
}, 120000)
