// Actual package resolution, candidate compilation and isolated browser launch.
// No Auth request, database connection or financial case is performed.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import {readFileSync, existsSync, mkdirSync, writeFileSync, realpathSync} from 'node:fs';
import {resolve, dirname} from 'node:path';
import {pathToFileURL, fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {reviewContrastPreflight} from './browser_contrast.mjs';

const single = process.argv[2] === '--single-checkout';
const workspace = realpathSync(process.argv[single ? 3 : 2]);
const digest = raw => ({bytes: raw.length, sha256: createHash('sha256').update(raw).digest('hex')});

async function checkCheckout(name) {
  assert.ok(['auditor','writer'].includes(name));
  const root = realpathSync(resolve(workspace, name));
  assert.equal(root, resolve(workspace, name), 'AFUI_PREFLIGHT_EXACT_CHECKOUT_ROOT');
  const manifestRaw = readFileSync(resolve(root, 'package.json'));
  const lockRaw = readFileSync(resolve(root, 'package-lock.json'));
  const manifest = JSON.parse(manifestRaw), lock = JSON.parse(lockRaw);
  const host = resolve(root, 'scripts/current-s03-sku-s05-composite-qualification/host.mjs');
  const require = createRequire(host), entry = require.resolve('@playwright/test');
  const actual = JSON.parse(readFileSync(resolve(dirname(entry), 'package.json'))).version;
  assert.equal(actual, manifest.devDependencies['@playwright/test']);
  assert.equal(actual, lock.packages['node_modules/@playwright/test'].version);
  for (const dependency of ['typescript','vite']) require.resolve(dependency);
  const {chromium} = require('@playwright/test');
  execFileSync(process.execPath, ['--input-type=module','-e',
    "import {chromium,expect} from '@playwright/test'; if(typeof chromium.launch!=='function'||typeof expect!=='function')process.exit(1)"],
    {cwd: root, timeout: 20000, stdio: ['ignore','pipe','pipe']});
  assert.ok(existsSync(chromium.executablePath()), 'AFUI_ACTUAL_PINNED_BROWSER_BINARY_REQUIRED');
  const observations = [], browser = await chromium.launch({timeout: 20000});
  try {
    for (const [width, timezoneId] of [[1440,'Asia/Jakarta'],[390,'America/Los_Angeles']]) {
      const context = await browser.newContext({viewport: {width,height: 900},timezoneId,
        isMobile: width === 390,hasTouch: width === 390});
      try {
        const requests = [];
        await context.route('**/*', route => {requests.push(route.request().url());return route.abort('blockedbyclient');});
        const page = await context.newPage();
        const contrast = await reviewContrastPreflight(page);
        await page.getByRole('button',{name:'Browser prerequisite',exact:true}).click();
        const observed = await page.evaluate(() => ({width:innerWidth,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone}));
        assert.deepEqual(observed,{width,timezone:timezoneId});assert.deepEqual(requests,[]);
        observations.push({checkout:name,...observed,contrast,external_requests:0,status:'PASS'});
      } finally {await context.close();}
    }
  } finally {await browser.close();}
  return {pin:{checkout:name,package_manifest:digest(manifestRaw),lockfile:digest(lockRaw),playwright_version:actual},observations};
}

async function main() {
  if (single) {console.log(JSON.stringify(await checkCheckout(process.argv[4])));return;}
  const auditor = resolve(workspace,'auditor'), out = resolve(auditor,'cp6-proof/t3');
  const result = {status:'INCOMPLETE',pins:[],observations:[],actual_SQL_executed:0,
    actual_Auth_requests:0,actual_browser_case_credit:0,production_go:false};
  mkdirSync(out,{recursive:true});
  try {
    for (const name of ['auditor','writer']) {
      result.phase = name + '_ACTUAL_PACKAGE_AND_BROWSER';
      // Playwright rejects two physical installations in a single process.
      // Both checkout roots receive independent real browser processes.
      const text = execFileSync(process.execPath,[fileURLToPath(import.meta.url),'--single-checkout',workspace,name],
        {cwd:workspace,timeout:90000,maxBuffer:4*1024*1024,stdio:['ignore','pipe','pipe']});
      const checked = JSON.parse(text.toString('utf8'));result.pins.push(checked.pin);result.observations.push(...checked.observations);
    }
    result.phase = 'ACTUAL_CANDIDATE_DISPOSABLE_BUILD';
    // Fixed compile-only local placeholder; never sent to Auth or an API.
    const localCompileKey = 'eyJhbGciOiJub25lIn0.eyJyb2xlIjoiYW5vbiIsInJlZiI6ImxvY2FsIn0.cHJlZmxpZ2h0';
    const safeEnv = Object.fromEntries(['PATH','HOME','CI','TMPDIR','RUNNER_TEMP','PLAYWRIGHT_BROWSERS_PATH']
      .filter(k => process.env[k]).map(k => [k,process.env[k]]));
    execFileSync('npm',['run','build:cp6-disposable'],{cwd:auditor,timeout:180000,stdio:'inherit',
      env:{...safeEnv,VITE_ERP_RUNTIME_MODE:'DISPOSABLE_TEST',VITE_SUPABASE_URL:'http://127.0.0.1:54099',
        VITE_DISPOSABLE_API_PORT:'54099',VITE_SUPABASE_ANON_KEY:localCompileKey}});
    result.candidate_disposable_build = 'PASS';result.phase = 'ACTUAL_BROWSER_MODULE_IMPORT';
    const module = await import(pathToFileURL(resolve(auditor,'scripts/cp7_accessory_nonpayable/browser.mjs')).href);
    assert.equal(typeof module.cases,'function');assert.equal(module.IDS.length,2);
    result.candidate_browser_module_import = 'PASS';result.phase = 'COMPLETE';
    result.status = 'EXACT_BOTH_CHECKOUT_PACKAGES_AND_REAL_DESKTOP_MOBILE_BROWSER_READY';
  } catch (error) {
    result.error = String(error.stack || error);
    result.child_stdout = error.stdout?.toString('utf8').slice(-16000);
    result.child_stderr = error.stderr?.toString('utf8').slice(-16000);
    process.exitCode = 1;
  } finally {
    writeFileSync(resolve(out,'AFUI_BROWSER_PREREQUISITES.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
    console.log(JSON.stringify(result));
  }
}
await main();
