// Transport only. Partial Originals never grant financial or restoration credit.
import {spawn, execFileSync} from 'node:child_process';
import {constants, createReadStream} from 'node:fs';
import * as fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {performance} from 'node:perf_hooks';

export const UPLOADER = 'ea165f8d65b6e75b540449e92b4886f43607fa02';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const requireValue = (value, code) => { if (!value) throw new Error(code); };
const emit = value => process.stdout.write(JSON.stringify({afui_durable_original: true, ...value}) + '\n');
const json = value => JSON.stringify(value, null, 2) + '\n';

export function childEnvironment(environment) {
  return Object.fromEntries(Object.entries(environment).filter(([key]) =>
    !key.startsWith('ACTIONS_') && !key.startsWith('INPUT_') &&
    !['GITHUB_OUTPUT', 'GITHUB_STATE', 'GITHUB_STEP_SUMMARY'].includes(key)));
}

export async function regular(target, directory = false) {
  target = path.resolve(target);
  for (let part = target; ; part = path.dirname(part)) {
    const stat = await fs.lstat(part);
    requireValue(!stat.isSymbolicLink(), 'AFUI_DURABLE_SYMLINK_REFUSED');
    if (part === target) requireValue(directory ? stat.isDirectory() : stat.isFile(), 'AFUI_DURABLE_REGULAR_PATH_REQUIRED');
    if (path.dirname(part) === part) break;
  }
  return target;
}

export async function digest(file) {
  await regular(file);
  const hash = createHash('sha256'); let bytes = 0;
  for await (const data of createReadStream(file)) { hash.update(data); bytes += data.length; }
  return {bytes, sha256: hash.digest('hex')};
}

export function outputs(text) {
  const rows = text.split(/\r?\n/), result = {};
  for (let i = 0; i < rows.length; i++) {
    if (!rows[i]) continue;
    const multi = /^([a-z-]+)<<([A-Za-z0-9_-]+)$/.exec(rows[i]);
    const single = /^([a-z-]+)=(.*)$/.exec(rows[i]);
    let key, value;
    if (multi) {
      key = multi[1]; const values = [];
      while (++i < rows.length && rows[i] !== multi[2]) values.push(rows[i]);
      requireValue(i < rows.length, 'AFUI_DURABLE_TRUNCATED_UPLOAD_OUTPUT'); value = values.join('\n');
    } else {
      requireValue(single, 'AFUI_DURABLE_MALFORMED_UPLOAD_OUTPUT'); [, key, value] = single;
    }
    requireValue(!Object.hasOwn(result, key), 'AFUI_DURABLE_DUPLICATE_UPLOAD_OUTPUT'); result[key] = value;
  }
  requireValue(/^[1-9][0-9]*$/.test(result['artifact-id']) && /^[a-f0-9]{64}$/.test(result['artifact-digest']),
    'AFUI_DURABLE_CONFIRMED_ARTIFACT_ID_AND_DIGEST_REQUIRED');
  return {artifact_id: result['artifact-id'], artifact_sha256: result['artifact-digest']};
}

export function command(program, args, options = {}) {
  const {signal, timeoutMs, ...spawnOptions} = options;
  return new Promise((resolve, reject) => {
    let error, timer, killTimer;
    const child = spawn(program, args, {stdio: 'inherit', ...spawnOptions});
    const stop = reason => {
      if (!error) error = new Error(reason);
      child.kill('SIGTERM'); killTimer ??= setTimeout(() => child.kill('SIGKILL'), 1000);
    };
    const abort = () => stop('AFUI_DURABLE_UPLOAD_CANCELLED');
    signal?.addEventListener('abort', abort, {once: true});
    if (signal?.aborted) abort();
    if (timeoutMs !== undefined) timer = setTimeout(() => stop('AFUI_DURABLE_UPLOAD_DEADLINE'), timeoutMs);
    child.once('error', e => { error = e; });
    child.once('close', (code, sig) => {
      clearTimeout(timer); clearTimeout(killTimer); signal?.removeEventListener('abort', abort);
      if (error || code !== 0 || sig) reject(error || new Error('AFUI_DURABLE_CHILD_FAILED:' + code + ':' + sig));
      else resolve({code, signal: sig});
    });
  });
}

export async function snapshot(source, staging, identity) {
  const name = path.basename(source);
  requireValue(/^[a-f0-9]{64}\.jsonl$/.test(name), 'AFUI_DURABLE_FIXED_CASE_FILENAME');
  await regular(source); const before = await digest(source);
  await fs.mkdir(staging); await regular(staging, true);
  const destination = path.join(staging, name);
  await fs.copyFile(source, destination, constants.COPYFILE_EXCL);
  const copied = await digest(destination), after = await digest(source);
  requireValue(JSON.stringify(before) === JSON.stringify(copied) && JSON.stringify(before) === JSON.stringify(after),
    'AFUI_DURABLE_ORIGINAL_CHANGED_DURING_COPY');
  const manifest = {classification: 'INCOMPLETE_RUN_ORIGINAL_ONLY_NOT_ACCEPTANCE', ...identity,
    original_name: name, original: copied, actual_case_credit: 0, full_restore_verified: false, production_go: false};
  await fs.writeFile(path.join(staging, 'MANIFEST.json'), json(manifest), {flag: 'wx'});
  return manifest;
}

export async function ownRuntime({worker, caseDirectory, staging, identity, upload, signalSource = process, pollMs = 5000}) {
  const controller = new AbortController(), seen = new Set(), uploaded = [], errors = [];
  let finished = false, externalSignal = null;
  const child = spawn(worker.program, worker.args, {cwd: worker.cwd, env: childEnvironment(worker.env), stdio: 'inherit'});
  const done = new Promise(resolve => {
    let spawnError = null;
    child.once('error', e => { spawnError = e.message; });
    child.once('close', (code, signal) => { finished = true; resolve({code, signal, spawn_error: spawnError}); });
  });
  const forward = signal => { externalSignal ??= signal; controller.abort(); child.kill(signal); };
  const interrupt = () => forward('SIGINT'), terminate = () => forward('SIGTERM');
  signalSource.on('SIGINT', interrupt); signalSource.on('SIGTERM', terminate);
  const scan = async () => {
    let entries;
    try { await regular(caseDirectory, true); entries = await fs.readdir(caseDirectory); }
    catch (e) { if (e.code === 'ENOENT') return; throw e; }
    for (const name of entries.sort()) {
      if (!/^[a-f0-9]{64}\.jsonl$/.test(name) || seen.has(name) || externalSignal) continue;
      seen.add(name);
      try {
        const directory = path.join(staging, name.slice(0, -6));
        const manifest = await snapshot(path.join(caseDirectory, name), directory, identity);
        const receipt = await upload(directory, name.slice(0, -6), controller.signal);
        requireValue(JSON.stringify(await digest(path.join(directory, name))) === JSON.stringify(manifest.original),
          'AFUI_DURABLE_STAGED_ORIGINAL_CHANGED_DURING_UPLOAD');
        const value = {...manifest, ...receipt}; uploaded.push(value); emit(value);
      } catch (e) { errors.push({original_name: name, error: e.message}); emit({status: 'UPLOAD_FAILED', original_name: name, error: e.message}); }
    }
  };
  const watcher = (async () => {
    try {
      while (!finished && !externalSignal) { await scan(); if (!finished && !externalSignal) await pause(pollMs); }
      if (!externalSignal) await scan();
    } catch (e) { errors.push({error: e.message}); }
  })();
  try {
    const result = await done; await watcher;
    return {status: result.code === 0 && !result.signal && !result.spawn_error && !externalSignal && !errors.length
      ? 'OWNING_PROCESS_COMPLETED_ORIGINAL_TRANSPORT_PASS_NOT_ERP' : 'INCOMPLETE',
      ...identity, supervisor_process: result, external_signal: externalSignal, complete_originals_uploaded: uploaded,
      errors, actual_case_credit: 0, full_restore_verified: false, production_go: false};
  } finally { signalSource.removeListener('SIGINT', interrupt); signalSource.removeListener('SIGTERM', terminate); }
}

export async function context(environment) {
  const workspace = await regular(environment.GITHUB_WORKSPACE, true);
  requireValue(HERE === path.join(workspace, 'auditor/scripts/cp7_accessory_nonpayable'), 'AFUI_DURABLE_FIXED_ACTION_LOCATION');
  requireValue(['preflight', 'runtime'].includes(environment.INPUT_MODE), 'AFUI_DURABLE_FIXED_MODE');
  const {GITHUB_SHA: head, GITHUB_RUN_ID: run, GITHUB_RUN_ATTEMPT: attempt} = environment;
  requireValue(/^[a-f0-9]{40}$/.test(head) && /^[1-9][0-9]*$/.test(run) && attempt === '1', 'AFUI_DURABLE_SINGLE_OWNING_IDENTITY');
  const git = (cwd, ...args) => execFileSync('/usr/bin/git', ['-C', cwd, ...args], {encoding: 'utf8'}).trim();
  const auditor = path.join(workspace, 'auditor');
  requireValue(git(auditor, 'rev-parse', 'HEAD') === head && !git(auditor, 'status', '--porcelain', '--untracked-files=no'),
    'AFUI_DURABLE_EXACT_CLEAN_CANDIDATE');
  const uploader = await regular(path.join(workspace, 'afui-artifact-uploader'), true);
  requireValue(git(uploader, 'rev-parse', 'HEAD') === UPLOADER && !git(uploader, 'status', '--porcelain', '--untracked-files=no'),
    'AFUI_DURABLE_EXACT_OFFICIAL_UPLOADER');
  const entry = await regular(path.join(uploader, 'dist/upload/index.js'));
  requireValue(git(uploader, 'hash-object', entry) === git(uploader, 'rev-parse', 'HEAD:dist/upload/index.js'),
    'AFUI_DURABLE_EXACT_OFFICIAL_UPLOAD_BYTES');
  requireValue(environment.ACTIONS_RUNTIME_TOKEN && environment.ACTIONS_RESULTS_URL && environment.ACTIONS_RUNTIME_URL,
    'AFUI_DURABLE_ACTION_RUNTIME_REQUIRED');
  const temporary = await regular(environment.RUNNER_TEMP, true);
  const stage = path.join(temporary, 'afui-durable-' + run + '-' + attempt);
  const identity = {qualification_commit: head, github_run_id: run, github_run_attempt: attempt};
  // Take Python's same OS monotonic clock once; Node only measures elapsed time.
  const remaining = Number(execFileSync('python', ['-c',
    'import os,time,math; s=float(os.environ["AFUI_JOB_START_MONOTONIC"]); n=time.monotonic(); assert math.isfinite(s) and 0<s<=n; print(s+350*60-n)'],
    {env: childEnvironment(environment), encoding: 'utf8'}));
  requireValue(Number.isFinite(remaining) && remaining > 0, 'AFUI_DURABLE_ORIGINAL_RECOVERY_BUDGET_REQUIRED');
  const deadline = performance.now() + remaining * 1000;
  const upload = async (directory, label, signal) => {
    const timeoutMs = Math.min(120000, deadline - performance.now());
    requireValue(timeoutMs > 0, 'AFUI_DURABLE_RETENTION_BUDGET_EXHAUSTED');
    const output = path.join(stage, label + '.outputs'); await fs.writeFile(output, '', {flag: 'wx'});
    await command(process.execPath, [entry], {cwd: workspace, timeoutMs, signal, env: {...environment,
      INPUT_NAME: 'afui-original-' + run + '-' + attempt + '-' + label, INPUT_PATH: directory,
      'INPUT_IF-NO-FILES-FOUND': 'error', 'INPUT_RETENTION-DAYS': '30', 'INPUT_COMPRESSION-LEVEL': '6',
      INPUT_OVERWRITE: 'false', 'INPUT_INCLUDE-HIDDEN-FILES': 'false', GITHUB_OUTPUT: output}});
    return outputs(await fs.readFile(output, 'utf8'));
  };
  return {workspace, stage, identity, upload, out: path.join(auditor, 'cp6-proof/t3')};
}

export async function main(environment = process.env) {
  const c = await context(environment); await fs.mkdir(c.out, {recursive: true}); await regular(c.out, true);
  const preflightPath = path.join(c.out, 'AFUI_DURABLE_PREFLIGHT.json');
  if (environment.INPUT_MODE === 'preflight') {
    await fs.mkdir(c.stage); await regular(c.stage, true);
    const directory = path.join(c.stage, 'preflight'); await fs.mkdir(directory);
    const original = {status: 'ARTIFACT_TRANSPORT_PREFLIGHT_ONLY', ...c.identity, actual_case_credit: 0, production_go: false};
    await fs.writeFile(path.join(directory, 'PREFLIGHT.json'), json(original), {flag: 'wx'});
    const uploaded = await c.upload(directory, 'preflight');
    const receipt = {...original, status: 'OFFICIAL_ARTIFACT_UPLOAD_CONFIRMED_BEFORE_DATABASE', ...uploaded};
    await fs.writeFile(preflightPath, json(receipt), {flag: 'wx'}); emit(receipt); return;
  }
  await regular(c.stage, true); await regular(preflightPath);
  const prerequisite = JSON.parse(await fs.readFile(preflightPath, 'utf8'));
  requireValue(prerequisite.status === 'OFFICIAL_ARTIFACT_UPLOAD_CONFIRMED_BEFORE_DATABASE' &&
    Object.entries(c.identity).every(([key, value]) => prerequisite[key] === value) &&
    /^[1-9][0-9]*$/.test(prerequisite.artifact_id) && /^[a-f0-9]{64}$/.test(prerequisite.artifact_sha256),
    'AFUI_DURABLE_SAME_RUN_TRANSPORT_PREFLIGHT_REQUIRED');
  const staging = path.join(c.stage, 'cases'); await fs.mkdir(staging);
  const result = await ownRuntime({worker: {program: 'python', args: ['-u', '-B', path.join(HERE, 'runtime_supervisor.py')],
    cwd: path.join(c.workspace, 'writer'), env: environment}, caseDirectory: path.join(c.out, 'AFUI_CASE_STDOUT'),
    staging, identity: c.identity, upload: c.upload});
  await fs.writeFile(path.join(c.out, 'AFUI_DURABLE_RUNTIME.json'), json(result), {flag: 'wx'});
  emit({status: result.status, uploaded: result.complete_originals_uploaded.length, errors: result.errors.length, actual_case_credit: 0});
  if (result.status !== 'OWNING_PROCESS_COMPLETED_ORIGINAL_TRANSPORT_PASS_NOT_ERP') process.exitCode = 1;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => { emit({status: 'INCOMPLETE', error: error.message, actual_case_credit: 0}); process.exitCode = 1; });
}
