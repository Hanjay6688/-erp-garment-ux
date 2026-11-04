// Actual package resolution, candidate compilation and isolated browser launch.
// No Auth request, database connection or financial case is performed.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import {readFileSync, existsSync, mkdirSync, writeFileSync, realpathSync} from 'node:fs';
import {resolve, dirname} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';

const workspace = realpathSync(process.argv[2]);
const pins = [], observations = [];
const digest = raw => ({bytes: raw.length, sha256: createHash('sha256').update(raw).digest('hex')});
for (const name of ['auditor', 'writer']) {
  const root = realpathSync(resolve(workspace, name));
  assert.equal(root, resolve(workspace, name), 'AFUI_PREFLIGHT_EXACT_CHECKOUT_ROOT');
  const manifestRaw = readFileSync(resolve(root, 'package.json'));
  const lockRaw = readFileSync(resolve(root, 'package-lock.json'));
  const manifest = JSON.parse(manifestRaw), lock = JSON.parse(lockRaw);
  const host = resolve(root, 'scripts/current-s03-sku-s05-composite-qualification/host.mjs');
  const require = createRequire(host);
  const entry = require.resolve('@playwright/test');
  const actual = JSON.parse(readFileSync(resolve(dirname(entry), 'package.json'))).version;
  assert.equal(actual, manifest.devDependencies['@playwright/test']);
  assert.equal(actual, lock.packages['node_modules/@playwright/test'].version);
  for (const dependency of ['typescript', 'vite']) require.resolve(dependency);
  const {chromium} = require('@playwright/test');
  execFileSync(process.execPath, ['--input-type=module', '-e',
    "import {chromium,expect} from '@playwright/test'; if(typeof chromium.launch!=='function'||typeof expect!=='function')process.exit(1)"],
    {cwd: root, timeout: 20000, stdio: ['ignore','pipe','pipe']});
  assert.ok(existsSync(chromium.executablePath()), 'AFUI_ACTUAL_PINNED_BROWSER_BINARY_REQUIRED');
  const browser = await chromium.launch({timeout: 20000});
  try {
    for (const [width, timezoneId] of [[1440, 'Asia/Jakarta'], [390, 'America/Los_Angeles']]) {
      const context = await browser.newContext({viewport: {width, height: 900}, timezoneId,
        isMobile: width === 390, hasTouch: width === 390});
      try {
        const requests = [];
        await context.route('**/*', route => {requests.push(route.request().url());return route.abort('blockedbyclient');});
        const page = await context.newPage();
        await page.setContent('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><button>Browser prerequisite</button>');
        await page.getByRole('button', {name: 'Browser prerequisite', exact: true}).click();
        const observed = await page.evaluate(() => ({width: innerWidth, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone}));
        assert.deepEqual(observed, {width, timezone: timezoneId});assert.deepEqual(requests, []);
        observations.push({checkout: name, ...observed, external_requests: 0, status: 'PASS'});
      } finally {await context.close();}
    }
  } finally {await browser.close();}
  pins.push({checkout: name, package_manifest: digest(manifestRaw), lockfile: digest(lockRaw), playwright_version: actual});
}
const auditor = resolve(workspace, 'auditor');
// A fixed compile-only local placeholder. It is never sent to Auth or an API.
const localCompileKey = 'eyJhbGciOiJub25lIn0.eyJyb2xlIjoiYW5vbiIsInJlZiI6ImxvY2FsIn0.cHJlZmxpZ2h0';
const safeEnv = Object.fromEntries(['PATH','HOME','CI','TMPDIR','RUNNER_TEMP','PLAYWRIGHT_BROWSERS_PATH']
  .filter(k => process.env[k]).map(k => [k, process.env[k]]));
execFileSync('npm', ['run', 'build:cp6-disposable'], {cwd: auditor, timeout: 180000, stdio: 'inherit',
  env: {...safeEnv, VITE_ERP_RUNTIME_MODE: 'DISPOSABLE_TEST', VITE_SUPABASE_URL: 'http://127.0.0.1:54099',
    VITE_DISPOSABLE_API_PORT: '54099', VITE_SUPABASE_ANON_KEY: localCompileKey}});
const module = await import(pathToFileURL(resolve(auditor, 'scripts/cp7_accessory_nonpayable/browser.mjs')).href);
assert.equal(typeof module.cases, 'function');assert.equal(module.IDS.length, 2);
const result = {status: 'EXACT_BOTH_CHECKOUT_PACKAGES_AND_REAL_DESKTOP_MOBILE_BROWSER_READY', pins, observations,
  candidate_disposable_build: 'PASS', candidate_browser_module_import: 'PASS',
  actual_SQL_executed: 0, actual_Auth_requests: 0, actual_browser_case_credit: 0, production_go: false};
const out = resolve(auditor, 'cp6-proof/t3');mkdirSync(out, {recursive: true});
writeFileSync(resolve(out, 'AFUI_BROWSER_PREREQUISITES.json'), JSON.stringify(result, null, 2) + '\n', {flag: 'wx'});
console.log(JSON.stringify(result));
