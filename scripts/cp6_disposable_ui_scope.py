#!/usr/bin/env python3
"""A bounded frontend writer successor; never an independent/global PASS."""
from pathlib import Path
import hashlib
import json
import subprocess

BASE = '9f884fbb27bdb92d6ee63f60333e007dc36f3f1c'
BASE_TREE = 'b4cf1e5d6c8aff531470af01dcdb4d146b4fca7f'
BACKEND = '25fa4736329e5148dfdb3572bc169952cba23251'
BACKEND_TREE = 'a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d'
PIN_FILE = 'docs/evidence/cp6-disposable-ui-source-pins.json'
DOC = 'docs/cp6-disposable-ui-audit.md'
PATHS = '''.github/workflows/cp6-ad-roll-opening-check.yml
.github/workflows/cp6-full-schema-validation.yml
.github/workflows/cp6-final-boundary-audit.yml
package.json
scripts/assert-cp6-disposable-env.mjs
scripts/build-preflight.mjs
scripts/cp6_disposable_ui_e2e.mjs
scripts/cp6_disposable_ui_scope.py
scripts/check-cp6-deep-business-repair.mjs
src/AccessControlPage.tsx
src/ConnectedBsResolutionPage.tsx
src/ConnectedQcFinalPage.tsx
src/ConnectedLaundryQcSelectors.dom.test.tsx
src/ConnectedCuttingPage.tsx
src/ConnectedPatternFilter.tsx
src/ConnectedPickupPage.tsx
src/ConnectedWipStatusPage.tsx
src/CuttingPatternPicker.tsx
src/PatternPage.tsx
src/auth/AuthGate.tsx
src/auth/AuthProvider.tsx
src/components/RuntimeIdentity.tsx
src/config/runtime.test.ts
src/config/runtime.ts
src/lib/supabase.ts
src/main.tsx
src/useLaundryQcWorkspace.ts
src/vite-env.d.ts'''.splitlines()


def verify():
    git = lambda *args: subprocess.check_output(['git', *args], text=True).strip()
    assert git('rev-parse', BASE+'^{tree}') == BASE_TREE
    assert git('rev-parse', BACKEND+'^{tree}') == BACKEND_TREE
    assert git('merge-base', BASE, 'HEAD') == BASE
    assert not git('rev-list', '--merges', BASE+'..HEAD')
    assert not git('diff', '--name-only', 'HEAD'), 'Uncommitted tracked changes'
    changed = set(git('diff', '--name-only', BASE, 'HEAD').splitlines())
    assert changed == set(PATHS) | {PIN_FILE, DOC}, sorted(changed)
    pins = json.loads(Path(PIN_FILE).read_text())
    assert pins['base'] == BASE and pins['backend'] == BACKEND
    assert set(pins['sha256']) == set(PATHS)
    for path, expected in pins['sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, path
    assert not git('diff', '--name-only', BACKEND, 'HEAD', '--', 'supabase'), 'Backend changed'
    # Preserve the validation bodies; only routing to the dedicated combined gate changes.
    full = '.github/workflows/cp6-full-schema-validation.yml'
    route = '''          if python scripts/cp6_disposable_ui_scope.py; then
            echo 'full=false' >> "$GITHUB_OUTPUT"
          else
            python scripts/cp6_ai_audit_router.py
          fi
'''
    text = Path(full).read_text()
    assert text.count(route) == 1
    assert text.replace(route, '          python scripts/cp6_ai_audit_router.py\n') == subprocess.check_output(['git','show',BASE+':'+full],text=True)
    ad = '.github/workflows/cp6-ad-roll-opening-check.yml'
    route = ' || python scripts/cp6_disposable_ui_scope.py; then\n'
    text = Path(ad).read_text()
    assert text.count(route) == 1
    assert text.replace(route, '; then\n') == subprocess.check_output(['git','show',BASE+':'+ad],text=True)
    return dict(status='ROUTED_TO_COMBINED_AI_AND_WRITER_UI_GATE',backend_head=BACKEND,
                backend_tree=BACKEND_TREE,frontend_head=git('rev-parse','HEAD'),
                frontend_tree=git('rev-parse','HEAD^{tree}'),
                historical_460_matrix_reexecuted=False,independent_acceptance=False,
                production_go=False)


if __name__ == '__main__':
    print(json.dumps(verify()))
