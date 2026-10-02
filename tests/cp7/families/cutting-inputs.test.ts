// @vitest-environment node
import { readFileSync } from 'node:fs'
import { beforeAll, beforeEach, afterAll, expect, test } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'

// Synthetic Native-table/Auth stubs validate this uninstalled adapter only.
// They prove no hosted, Native business, real Auth or factory qualification.
let db: Awaited<ReturnType<typeof openRuntime>>
const actor = '00000000-0000-4000-8000-000000000001'
const group = '00000000-0000-4000-8000-000000000002'
const pattern = '00000000-0000-4000-8000-000000000003'
const roll = '00000000-0000-4000-8000-000000000004'
const size = '00000000-0000-4000-8000-000000000005'
const family = { brand: 'B', mill: 'M', variant: 'V', spec_revision: '1' }
const payload = () => ({ group_id: group, expected_group_version: '1', expected_input_version: null as string | null, marker_key: 'marker-1', planned_mix: [{ size_id: size, drawings: '3' }], roll_inputs: [{ roll_id: roll, family, width_cm: null as string | null }], explicit_review: true })
beforeAll(async () => {
  db = await openRuntime()
  await db.execute(`create schema erp;create schema cp7_private;create schema cp7_planning;create schema cp7_cutting_yield;
    create function cp7_private.immutable_run()returns trigger language plpgsql as $$begin raise exception 'CONTROL_IMMUTABLE';end$$;
    create function cp7_planning.utc(t timestamptz)returns text language sql immutable as $$select to_char(t at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')$$;
    create table public.control_cutting_access(actor uuid not null,allowed boolean not null,write_allowed boolean not null);
    insert into public.control_cutting_access values('${actor}',true,true);
    grant select on public.control_cutting_access to cp7_capture;
    grant usage on schema erp,cp7_private,cp7_planning,cp7_cutting_yield to cp7_capture;
    create function cp7_cutting_yield.access_now()returns jsonb language plpgsql as $$
      declare r public.control_cutting_access%rowtype;
      begin select *into r from public.control_cutting_access;if not r.allowed then raise exception 'CONTROL_CURRENT_ACCESS_DENIED';end if;
       return jsonb_build_object('actor',r.actor,'allowed',r.allowed);end$$;
    create function erp.has_permission(p text)returns boolean language sql as $$select write_allowed from public.control_cutting_access$$;
    create table erp.cutting_groups(id uuid,po_id uuid,row_version bigint,cut_at timestamptz,material_issue_posted boolean,pattern_id uuid,pattern_revision_snapshot text);
    insert into erp.cutting_groups values('${group}','${group}',1,clock_timestamp()-interval '1 year',false,'${pattern}','r1');
    grant select on erp.cutting_groups to cp7_capture;
    create table public.control_cutting_slices(group_id uuid,slices jsonb);
    insert into public.control_cutting_slices values('${group}',${jsonArg([{ slice_id: roll, group_id: group, roll_id: roll, material_id: roll, unit_code: 'YARD', outputs: [{ yield_id: size, size_id: size, qty_pcs: '60' }], consumed_native: '60' }])});
    grant select on public.control_cutting_slices to cp7_capture;
    create function cp7_cutting_yield.source(q jsonb)returns jsonb language sql stable as $$
      select jsonb_build_object('requested_group_count',1,'found_group_count',1,'slices',slices)
      from public.control_cutting_slices where group_id=(q->'group_ids'->>0)::uuid$$;
    ${readFileSync('scripts/cp7-src/cutting-yield/learning-kernel.sql', 'utf8')}
    ${readFileSync('scripts/cp7-src/cutting-yield/inputs.sql', 'utf8')}`)
}, 120000)
afterAll(async () => { if (db) await db.close() })
beforeEach(async () => {
  await db.execute(`truncate cp7_cutting_inputs.plans,cp7_cutting_inputs.requests;
    update public.control_cutting_access set actor='${actor}',allowed=true,write_allowed=true;`)
})
const workspace = () => db.query(`select public.erp_cp7_get_cutting_input_workspace_v1('${group}') result`)
const command = async (p: ReturnType<typeof payload>, id: string, lookup = false) => (await db.query(`select public.${lookup ? 'erp_cp7_get_cutting_input_request_v1' : 'erp_cp7_record_cutting_inputs_v1'}(${jsonArg(p)},'${id}') result`))[0].result
const newRequest = () => crypto.randomUUID()

test('operator input binds Native pattern, roll, unit and size; old physical time cannot become preknown knowledge', async () => {
  const before = await db.query('select row_to_json(t) t from erp.cutting_groups t')
  const p = payload(), id = newRequest()
  const first = await command(p, id)
  expect(first.result.status).toBe('COMMITTED')
  expect(first.result.record.version).toBe('1')
  expect(first.result.record.values.rolls[0].context).toEqual({ family, pattern_id: pattern, pattern_revision: 'r1', marker_key: 'marker-1', unit: 'YARD', planned_mix: [{ size_id: size, drawings: '1' }] })
  expect(first.result.record.values.rolls[0].width_cm).toBeNull()
  expect(first.current.preknown_before_physical).toBe(false)
  expect(first.current.record_matches_native_identity).toBe(true)
  expect(first.current.model_qualified).toBe(false)
  expect(await command(p, id)).toEqual(first)
  expect(await command(p, id, true)).toEqual(first)
  expect(await db.query('select row_to_json(t) t from erp.cutting_groups t')).toEqual(before)
  await expect(command({ ...p, marker_key: 'other' }, id)).rejects.toThrow('CP7_CUTTING_INPUT_REQUEST_CHANGED')
})

test('CAS keeps prior input immutable and an absent UUID is sealed; unknown physical width is not defaulted', async () => {
  const prior = (await command(payload(), newRequest())).result.record
  const p = { ...payload(), expected_input_version: prior.version, roll_inputs: [{ roll_id: roll, family, width_cm: '175.250' }] }
  const second = await command(p, newRequest())
  expect(second.result.record.previous_id).toBe(prior.id)
  expect(second.result.record.values.rolls[0].width_cm).toBe('175.250')
  await expect(command(p, newRequest())).rejects.toThrow('CP7_CUTTING_INPUT_VERSION_CHANGED')
  const key = newRequest(), absent = await command(p, key, true)
  expect(absent.result).toEqual({ status: 'NOT_COMMITTED', request_id: key, record: null })
  expect((await command(p, key)).result).toEqual(absent.result)
  await expect(db.execute(`update cp7_cutting_inputs.plans set features='{}'::jsonb`)).rejects.toThrow('CONTROL_IMMUTABLE')
  await expect(db.execute(`delete from cp7_cutting_inputs.plans`)).rejects.toThrow('CONTROL_IMMUTABLE')
  expect((await workspace())[0].result.record.id).toBe(second.result.record.id)
})

test('closed input refuses Native identity/size/version mismatch and current access or write revocation before cached replies', async () => {
  const prior = (await command(payload(), newRequest())).result.record
  const p = { ...payload(), expected_input_version: prior.version }, key = newRequest()
  const saved = await command(p, key)
  await expect(command({ ...p, expected_group_version: '2', expected_input_version: saved.result.record.version }, newRequest())).rejects.toThrow('CP7_CUTTING_INPUT_NATIVE_VERSION_CHANGED')
  await expect(command({ ...p, expected_input_version: saved.result.record.version, planned_mix: [{ size_id: pattern, drawings: '1' }] }, newRequest())).rejects.toThrow('CP7_CUTTING_INPUT_NATIVE_SIZE_MISMATCH')
  await expect(command({ ...p, expected_input_version: saved.result.record.version, roll_inputs: [{ roll_id: pattern, family, width_cm: null }] }, newRequest())).rejects.toThrow('CP7_CUTTING_INPUT_NATIVE_ROLL_MISMATCH')
  await expect(command({ ...p, source_complete: true } as ReturnType<typeof payload>, newRequest())).rejects.toThrow()
  await db.execute('update public.control_cutting_access set write_allowed=false')
  await expect(command(p, key, true)).rejects.toThrow('CP7_CUTTING_INPUT_WRITE_DENIED')
  expect((await workspace())[0].result.can_record).toBe(false)
  await db.execute('update public.control_cutting_access set allowed=false')
  await expect(command(p, key, true)).rejects.toThrow('CONTROL_CURRENT_ACCESS_DENIED')
  await expect(workspace()).rejects.toThrow('CONTROL_CURRENT_ACCESS_DENIED')
  await db.execute('update public.control_cutting_access set allowed=true,write_allowed=true')
  await db.execute(`update public.control_cutting_access set actor='${pattern}'`)
  expect((await workspace())[0].result.record).toBeNull()
  expect((await command({ ...payload(), expected_input_version: null }, key, true)).result.status).toBe('NOT_COMMITTED')
  await db.execute(`update public.control_cutting_access set actor='${actor}'`)
  expect((await command(p, key, true)).result).toEqual(saved.result)
})
