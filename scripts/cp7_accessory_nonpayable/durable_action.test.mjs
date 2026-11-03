// Local transport/process controls only: no ERP, GitHub upload or acceptance.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {EventEmitter} from 'node:events';
import {fileURLToPath} from 'node:url';
import {childEnvironment, command, digest, ownRuntime, outputs, snapshot} from './durable_action.mjs';

const receipt = {artifact_id: '123', artifact_sha256: 'd'.repeat(64)};
const identity = {qualification_commit: 'c'.repeat(40), github_run_id: '1234', github_run_attempt: '1'};
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
