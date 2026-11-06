import hashlib
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv) == 2 else Path('smoke-work')
expected = {
    'mandor': ('415e951c66a9406a7498182f48f827b7f00d475a', '23564f59aa82d661f982f92b87ffd10173ee5f8d'),
    'sku': ('49a0f1c643595d81840c4d457f53f400242423cd', 'ee8fc43182b2b085c17ab701c4f20dec314205a6'),
}
paths = ('src', 'public', 'contracts', 'package.json', 'package-lock.json', 'index.html',
         'vite.config.ts', 'tsconfig.json', 'tsconfig.app.json', 'tsconfig.contracts.json',
         'scripts/assert-cp6-disposable-env.mjs', 'scripts/build-preflight.mjs', 'scripts/scan-client-artifacts.mjs',
         'scripts/cp7_accessory_nonpayable/LOCAL_SETTINGS_CONTROLS.json')

def git(name, *args):
    return subprocess.check_output(['git', '-C', str(root / name), *args], text=True).strip()

for name, (head, tree) in expected.items():
    assert git(name, 'rev-parse', 'HEAD') == head
    assert git(name, 'rev-parse', 'HEAD^{tree}') == tree
    assert not git(name, 'status', '--porcelain', '--untracked-files=no')

common = {}
for path in paths:
    entry = git('sku', 'ls-tree', 'HEAD', '--', path)
    assert entry == git('mandor', 'ls-tree', 'HEAD', '--', path), path
    assert entry or path == 'public', path
    common[path] = entry.split()[2] if entry else None

sources = {
    'mandor': 'scripts/current-mandor-shop-native-qualification/browser.mjs',
    'sku': 'scripts/current-sku-automatic-composite-preparation/browser.mjs',
}
for name, path in sources.items():
    raw = (root / name / path).read_bytes()
    actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    assert actual == git(name, 'rev-parse', 'HEAD:' + path)

print(json.dumps({'status': 'EXACT_CURRENT_CANDIDATES_AND_IDENTICAL_BUILD_INPUTS',
                  'candidates': expected, 'common_build_inputs': common, 'browser_sources': sources,
                  'actual_financial_cases': 0, 'actual_Auth_cases': 0}, indent=2))
