import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {context, ownRuntime} from '../cp7_accessory_nonpayable/durable_action.mjs';

const env = {...process.env, INPUT_MODE: 'runtime'};
if (env.GITHUB_REF !== 'refs/heads/astra-a/afui-lifecycle-smoke-20261106') {
  throw new Error('AFUI_SMOKE_FIXED_BRANCH_REQUIRED');
}
const c = await context(env);
const preflight = JSON.parse(await fs.readFile(path.join(c.out, 'AFUI_DURABLE_PREFLIGHT.json'), 'utf8'));
if (preflight.status !== 'OFFICIAL_ARTIFACT_UPLOAD_CONFIRMED_BEFORE_DATABASE' ||
    !Object.entries(c.identity).every(([key, value]) => preflight[key] === value)) {
  throw new Error('AFUI_SMOKE_EXACT_TRANSPORT_PREFLIGHT_REQUIRED');
}
const staging = path.join(c.stage, 'smoke-cases');
await fs.mkdir(staging);
const result = await ownRuntime({
  worker: {program: 'python', args: ['-u', '-B',
    path.join(c.workspace, 'auditor/scripts/cp7_afui_lifecycle_smoke/worker.py')],
    cwd: c.workspace, env},
  caseDirectory: path.join(c.out, 'AFUI_CASE_STDOUT'),
  staging, identity: c.identity, upload: c.upload, pollMs: 1000,
});
await fs.writeFile(path.join(c.out, 'AFUI_LIFECYCLE_SMOKE_TRANSPORT.json'), JSON.stringify(result, null, 2) + '\n', {flag: 'wx'});
const first = createHash('sha256').update('CP7_AFUI_ISOLATED_LIFECYCLE\0FIRST_FIXTURE_FAILURE').digest('hex') + '.jsonl';
const expected = [
  'AFUI_COMPLETE_STATE_PREREQUISITE_START.json',
  'AFUI_COMPLETE_STATE_PREREQUISITE_RESULT.json',
  'AFUI_BROWSER_SETTINGS_STATE.json',
  'AFUI_BROWSER_SETTINGS_STATE_CACHE.json',
  first,
];
const seen = new Set(result.complete_originals_uploaded.map(item => item.original_name));
if (result.status !== 'OWNING_PROCESS_COMPLETED_ORIGINAL_TRANSPORT_PASS_NOT_ERP' ||
    result.complete_originals_uploaded.length !== expected.length || !expected.every(name => seen.has(name))) {
  throw new Error('AFUI_SMOKE_EXPECTED_FIVE_EXACT_ORIGINALS_REQUIRED');
}
