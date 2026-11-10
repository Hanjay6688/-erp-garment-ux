// Local transport/process controls only: no ERP, GitHub upload or acceptance.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {EventEmitter} from 'node:events';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {randomBytes,createHash} from 'node:crypto';
import {childEnvironment, command, digest, ownRuntime, originalLabel, outputs, snapshot, snapshotLargeState} from './durable_action.mjs';

const receipt = {artifact_id: '123', artifact_sha256: 'd'.repeat(64)};
const identity = {qualification_commit: 'c'.repeat(40), github_run_id: '1234', github_run_attempt: '1'};
test('large full state parts reassemble both compressed and complete original bytes without new case credit', async () => fixture(async f => {
  const name = 'MANDOR_BROWSER_STATE.json', source = path.join(f.cases, name);
  const raw = Buffer.from(JSON.stringify({all_fields: randomBytes(18000).toString('hex'),rows:[1,2,3]}) + '\n');
  await fs.writeFile(source, raw);
  const parts = await snapshotLargeState(source, path.join(f.staging, 'large'), identity, {partBytes: 4096});
  assert.ok(parts.length > 1);const buffers = [];
  for (const [i,part] of parts.entries()) {
    const manifest = JSON.parse(await fs.readFile(path.join(part.directory,'MANIFEST.json'),'utf8'));
    const bytes = await fs.readFile(path.join(part.directory,part.payload));buffers.push(bytes);
    assert.equal(manifest.part.number,i+1);assert.equal(manifest.part.offset,i*4096);assert.ok(bytes.length<=4096);
    assert.equal(manifest.part.sha256,createHash('sha256').update(bytes).digest('hex'));
    assert.deepEqual(manifest.original,await digest(source));assert.equal(manifest.actual_case_credit,0);
    assert.equal(manifest.full_restore_verified,false);assert.equal(manifest.production_go,false);
    assert.equal(manifest.classification,'INCOMPLETE_RUN_ORIGINAL_GZIP_PART_ONLY_NOT_ACCEPTANCE');
  }
  const compressed=Buffer.concat(buffers);assert.deepEqual(gunzipSync(compressed),raw);
  assert.deepEqual(parts[0].manifest.compressed_original,{name:name+'.gz',bytes:compressed.length,
    sha256:createHash('sha256').update(compressed).digest('hex')});
  assert.deepEqual(await fs.readFile(source),raw);
}));

test('large state path and connector byte bounds refuse before staging', async () => fixture(async f => {
  const other=path.join(f.cases,'other.json');await fs.writeFile(other,'{}');
  await assert.rejects(snapshotLargeState(other,path.join(f.staging,'other'),identity),/EXACT_LARGE_STATE/);
  const source=path.join(f.cases,'MANDOR_BROWSER_STATE.json');await fs.writeFile(source,'{}');
  for(const partBytes of [0,400*1024*1024+1])
    await assert.rejects(snapshotLargeState(source,path.join(f.staging,'invalid'),identity,{partBytes}),/BOUNDED_PART_BYTES/);
  assert.deepEqual(await fs.readdir(f.staging),[]);
}));

test('large state uses already compressed uploads and a mutated uploaded part still fails closed', async () => fixture(async f => {
  const source=path.join(f.cases,'MANDOR_BROWSER_STATE.json');const file=await fs.open(source,'wx');
  await file.truncate(64*1024*1024+1);await file.close();let calls=0;
  const result=await ownRuntime({worker:{program:process.execPath,args:['-e','setTimeout(()=>{},25)'],cwd:f.root,env:process.env},
    caseDirectory:f.cases,staging:f.staging,identity,pollMs:5,signalSource:new EventEmitter(),
    upload:async(directory,label,signal,level)=>{calls++;assert.equal(level,0);
      const manifest=JSON.parse(await fs.readFile(path.join(directory,'MANIFEST.json'),'utf8'));
      await fs.appendFile(path.join(directory,manifest.part.name),'changed after snapshot');return receipt;}});
  assert.equal(calls,1);assert.equal(result.status,'INCOMPLETE');assert.equal(result.errors.length,1);
  assert.match(result.errors[0].error,/STAGED_ORIGINAL_CHANGED_DURING_UPLOAD/);
  assert.equal(result.actual_case_credit,0);
}));
async function fixture(fn) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'afui-durable-control-'));
  try {
    const cases = path.join(root, 'originals'), staging = path.join(root, 'staging');
    await fs.mkdir(cases); await fs.mkdir(staging); await fn({root, cases, staging});
  } finally { await fs.rm(root, {recursive: true, force: true}); }
}

test('complete large Original bytes stay exact; incomplete file ignored; upload precedes worker exit', async () => fixture(async f => {
  const name = 'a'.repeat(64) + '.jsonl', original = Buffer.from('{"amount":9007199254740993,"rows":["é","é"],"padding":"' + 'x'.repeat(2 ** 20) + '"}\n');
  await fs.writeFile(path.join(f.cases, name), original);
  await fs.writeFile(path.join(f.cases, 'b'.repeat(64) + '.partial'), 'incomplete');
  const done = path.join(f.root, 'worker-done'), released = path.join(f.root, 'upload-done'); let calls = 0;
  const result = await ownRuntime({worker: {program: process.execPath, args: ['-e',
    `const fs=require('fs');const t=setInterval(()=>{if(fs.existsSync(${JSON.stringify(released)})){fs.writeFileSync(${JSON.stringify(done)},'done');clearInterval(t)}},5);setTimeout(()=>process.exit(8),5000).unref()`], env: process.env},
    caseDirectory: f.cases, staging: f.staging, identity, pollMs: 5,
    upload: async (directory, label) => {
      calls++; assert.equal(label, 'a'.repeat(64));
      await assert.rejects(fs.stat(done), {code: 'ENOENT'});
      assert.deepEqual(await fs.readFile(path.join(directory, name)), original);
      const manifest = JSON.parse(await fs.readFile(path.join(directory, 'MANIFEST.json')));
      assert.deepEqual(manifest.original, await digest(path.join(f.cases, name)));
      assert.equal(manifest.actual_case_credit, 0); assert.equal(manifest.full_restore_verified, false);
      await fs.writeFile(released,'uploaded'); return receipt;
    }});
  assert.equal(calls, 1); assert.equal(result.complete_originals_uploaded.length, 1);
  assert.equal(result.status, 'OWNING_PROCESS_COMPLETED_ORIGINAL_TRANSPORT_PASS_NOT_ERP');
  assert.equal(result.actual_case_credit, 0);
}));

test('upload failure is retained once while the owning worker reaches its own cleanup', async () => fixture(async f => {
  await fs.writeFile(path.join(f.cases, 'c'.repeat(64) + '.jsonl'), '{}\n');
  const done = path.join(f.root, 'cleanup'); let calls = 0;
  const result = await ownRuntime({worker: {program: process.execPath, args: ['-e',
    `setTimeout(()=>require('fs').writeFileSync(${JSON.stringify(done)},'restored-by-fixture'),50)`], env: process.env},
    caseDirectory: f.cases, staging: f.staging, identity, pollMs: 5,
    upload: async () => { calls++; throw new Error('model artifact service unavailable'); }});
  assert.equal(await fs.readFile(done, 'utf8'), 'restored-by-fixture'); assert.equal(calls, 1);
  assert.equal(result.status, 'INCOMPLETE'); assert.equal(result.errors.length, 1);
  assert.equal(result.supervisor_process.code, 0); assert.equal(result.actual_case_credit, 0);
}));

test('nonzero owning exit never becomes success after a successful Original upload', async () => fixture(async f => {
  await fs.writeFile(path.join(f.cases, 'd'.repeat(64) + '.jsonl'), '{"status":"FAIL"}\n');
  const result = await ownRuntime({worker: {program: process.execPath, args: ['-e', 'process.exitCode=7'], env: process.env},
    caseDirectory: f.cases, staging: f.staging, identity, pollMs: 5, upload: async () => receipt});
  assert.equal(result.status, 'INCOMPLETE'); assert.equal(result.supervisor_process.code, 7);
  assert.equal(result.complete_originals_uploaded.length, 1);
}));

test('runner signal reaches the retained Python supervisor; its worker is reaped and cancellation earns no credit', async () => fixture(async f => {
  const signals = new EventEmitter(), ready = path.join(f.root, 'ready'), resultPath = path.join(f.root, 'supervisor.json');
  const here = path.dirname(fileURLToPath(import.meta.url));
  const supervisor = path.resolve(here, '../current-de-free-date-preparation/runtime_supervisor.py');
  const worker = `import pathlib,time,signal,sys\nsignal.signal(signal.SIGINT,lambda *_:sys.exit(0))\npathlib.Path(${JSON.stringify(ready)}).write_text('ready')\nwhile True:time.sleep(.01)`;
  const script = `import importlib.util,sys,json,pathlib\ns=importlib.util.spec_from_file_location('exact_supervisor',${JSON.stringify(supervisor)});m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nr=m.supervise([sys.executable,'-u','-c',${JSON.stringify(worker)}],work_seconds=5,recovery_seconds=.5,poll_seconds=.01)\npathlib.Path(${JSON.stringify(resultPath)}).write_text(json.dumps(r))\nsys.exit(0 if r['status']=='WORKER_COMPLETED_AND_REAPED' else 124)`;
  const promise = ownRuntime({worker: {program: 'python3', args: ['-B', '-u', '-c', script], env: process.env},
    caseDirectory: f.cases, staging: f.staging, identity, pollMs: 5, signalSource: signals, upload: async () => receipt});
  let found = false;
  for (let i = 0; i < 200; i++) { try { await fs.stat(ready); found = true; break; } catch {} await new Promise(r => setTimeout(r, 5)); }
  assert.equal(found, true); signals.emit('SIGTERM');
  const result = await promise, original = JSON.parse(await fs.readFile(resultPath));
  assert.equal(result.status, 'INCOMPLETE'); assert.equal(result.external_signal, 'SIGTERM');
  assert.equal(original.external_signal, 'SIGTERM'); assert.equal(original.process_tree_empty, true);
  assert.equal(original.worker_exit, 0); assert.equal(original.actual_case_credit, 0);
  assert.equal(signals.listenerCount('SIGTERM'), 0); assert.equal(signals.listenerCount('SIGINT'), 0);
}));

test('bounded uploader kills and reaps a hung process', async () => fixture(async f => {
  const pidFile = path.join(f.root, 'pid');
  await assert.rejects(command(process.execPath, ['-e',
    `require('fs').writeFileSync(${JSON.stringify(pidFile)},String(process.pid));process.on('SIGTERM',()=>{});setInterval(()=>{},100)`],
    {timeoutMs: 200}), /UPLOAD_DEADLINE/);
  const pid = Number(await fs.readFile(pidFile)); assert.throws(() => process.kill(pid, 0), {code: 'ESRCH'});
}));

test('symlink originals and overwrites fail before upload', async () => fixture(async f => {
  const name = 'e'.repeat(64) + '.jsonl', source = path.join(f.cases, name), target = path.join(f.staging, 'one');
  await fs.writeFile(source, '{}\n'); await snapshot(source, target, identity);
  await assert.rejects(snapshot(source, target, identity), {code: 'EEXIST'});
  await fs.unlink(source); await fs.symlink(path.join(target, name), source);
  await assert.rejects(snapshot(source, path.join(f.staging, 'two'), identity), /SYMLINK_REFUSED/);
}));

test('runtime credentials and action outputs are stripped from the financial process', () => {
  assert.deepEqual(childEnvironment({PATH: '/bin', AFUI_CONFIRM: 'cp6_rollback', GITHUB_RUN_ID: '9',
    ACTIONS_RUNTIME_TOKEN: 'secret-fixture', ACTIONS_RESULTS_URL: 'private-fixture', INPUT_MODE: 'runtime',
    GITHUB_OUTPUT: '/action-output', GITHUB_STATE: '/action-state', GITHUB_STEP_SUMMARY: '/summary'}),
  {PATH: '/bin', AFUI_CONFIRM: 'cp6_rollback', GITHUB_RUN_ID: '9'});
});

test('only complete unique official ID and digest outputs count as uploaded', () => {
  assert.deepEqual(outputs('artifact-id<<ghadelimiter_1\n123\nghadelimiter_1\nartifact-digest=' + 'd'.repeat(64) + '\n'), receipt);
  for (const value of ['', 'artifact-id=123\n', 'artifact-id<<missing\n123',
    'artifact-id=1\nartifact-id=2\nartifact-digest=' + 'd'.repeat(64)]) assert.throws(() => outputs(value));
});

test('complete Native group, settings and compressed snapshots retain their exact real filenames', async () => fixture(async f => {
  const names = ['CP7_AFUI_GOOD_NONPAYABLE_FULL15_NATIVE9.json',
    'CP7_AFUI_GOOD_NONPAYABLE_FULL15_NATIVE9_BUSINESS_DAY_FIRST_ATTEMPT.json',
    'AFUI_BROWSER_NATIVE_PREREQUISITE.json', 'AFUI_BROWSER_SETTINGS_STATE.json',
    'AFUI_ACCESS_HTTP_SAME_REPLAY_' + 'f'.repeat(32) + '_FULL_CENSUS.json.gz',
    'AFUI_DESKTOP_INITIAL_FULL_CURRENT_CENSUS.json.gz'];
  const seen = [];
  for (const name of names) await fs.writeFile(path.join(f.cases, name), Buffer.from([0, 255, 35, 10]));
  await fs.writeFile(path.join(f.cases, 'AFUI_BROWSER_SETTINGS_STATE.json.partial'), 'incomplete');
  await fs.writeFile(path.join(f.cases, 'unrelated.json'), 'ignored');
  const result = await ownRuntime({worker: {program: process.execPath, args: ['-e', 'setTimeout(()=>{},50)'], env: process.env},
    caseDirectory: f.cases, staging: f.staging, identity, pollMs: 5,
    upload: async (directory, label) => {
      const manifest = JSON.parse(await fs.readFile(path.join(directory, 'MANIFEST.json')));
      assert(names.includes(manifest.original_name));
      assert.equal(label, originalLabel(manifest.original_name));
      assert.match(label, /^[a-f0-9]{64}$/);
      assert.deepEqual(await fs.readFile(path.join(directory, manifest.original_name)), Buffer.from([0, 255, 35, 10]));
      seen.push(manifest.original_name); return receipt;
    }});
  assert.deepEqual(seen.sort(), names.sort());
  assert.equal(result.complete_originals_uploaded.length, names.length);
  assert.equal(result.actual_case_credit, 0); assert.equal(result.full_restore_verified, false);
  for (const name of ['../AFUI_BROWSER_SETTINGS_STATE.json', 'AFUI_BROWSER_SETTINGS_STATE.json.partial',
    'AFUI_ACCESS_bad-label_' + 'a'.repeat(32) + '_FULL_CENSUS.json.gz', 'unrelated.json']) assert.equal(originalLabel(name), null);
}));

test('Mandor immutable root Originals and retained group directory both upload; mutable root group waits', async () => fixture(async f => {
  const group = 'CP7_FG_MANDOR_NATIVE9_STRICT.json', access = 'MANDOR_HTTP2_ORIGINAL.json';
  const raw = Buffer.from('{"explicit_local_protocol_model":true,"status":"PASS"}\n');
  await fs.writeFile(path.join(f.root, group), 'mutable group must not be uploaded');
  await fs.writeFile(path.join(f.root, access), raw);
  const names = [];
  const result = await ownRuntime({worker: {program: process.execPath, args: ['-e', 'setTimeout(()=>{},60)'], env: process.env},
    caseDirectory: f.cases, staging: f.staging, identity, pollMs: 5,
    upload: async (directory, label) => {
      const manifest = JSON.parse(await fs.readFile(path.join(directory, 'MANIFEST.json')));
      names.push(manifest.original_name);assert.equal(manifest.original_name, access);
      assert.equal(label, originalLabel(access));assert.deepEqual(await fs.readFile(path.join(directory, access)), raw);
      return receipt;
    }});
  assert.deepEqual(names, [access]);assert.equal(result.status, 'OWNING_PROCESS_COMPLETED_ORIGINAL_TRANSPORT_PASS_NOT_ERP');
  const staged = path.join(f.root, 'final-staging');await fs.mkdir(staged);
  await fs.writeFile(path.join(f.cases, group), raw);const second = [];
  await ownRuntime({worker: {program: process.execPath, args: ['-e', 'setTimeout(()=>{},60)'], env: process.env},
    caseDirectory: f.cases, staging: staged, identity, pollMs: 5,
    upload: async (directory) => {const manifest=JSON.parse(await fs.readFile(path.join(directory,'MANIFEST.json')));second.push(manifest.original_name);return receipt;}});
  assert.deepEqual(second.sort(), [group, access].sort());
}));

test('only fixed Mandor Original and exact full access snapshot names are admitted', () => {
  for (const name of ['CP7_FG_MANDOR_NATIVE9_STRICT.json','MANDOR_SESSION4_ORIGINAL.json','MANDOR_BROWSER2_ORIGINAL.json',
    'MANDOR_ACCESS_BEFORE_'+'a'.repeat(32)+'.json.gz']) assert.match(originalLabel(name), /^[a-f0-9]{64}$/);
  for (const name of ['MANDOR_ACCESS_BEFORE_fake.json.gz','MANDOR_HTTP2_ORIGINAL.json.partial','unreviewed.json']) assert.equal(originalLabel(name), null);
});
