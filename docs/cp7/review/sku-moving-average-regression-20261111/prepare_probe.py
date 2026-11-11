"""Reuse the retained SKU model with the two selected PostgreSQL regressions."""
from hashlib import sha256
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys


CANDIDATE = '32590613a08e176536d9a19b3843f6a72f4479b4'
MONEY = 'f1674ae84739f577571d68415beabfca3f3b832b'
AUTOMATIC = '9b1b0fcc9fbf477634619f07d4628d5be3a1b634'
REFERENCE = 'scripts/current-sku-automatic-composite-preparation/SOURCE_REFERENCE.json'
NATIVE27 = 'CP7_SKU_MANAGED_RECOVERY_NATIVE27.json'
NATIVE27_SHA = '5e22077e71e34add6fd0627c89e9d21a2235f463818e45b233c7619bcfb0d48f'
CASE_KEY = 'SKU_NATIVE7_COST5_RACES3_PERMISSION_WAITS7_RECOVERY_BUSY1_AUTH_BROWSER4'
BOOK_SIGNATURE = 'erp.compute_non_po_product_hpp_book_v2620f(uuid)'


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def prepare(repo, auto_root, native27, out):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args])

    require(git('rev-parse', 'HEAD').decode().strip() == MONEY, 'Use the frozen money checkout')
    ref = json.loads(git('show', CANDIDATE + ':' + REFERENCE))
    require(ref['unchanged_money_product']['public_head'] == MONEY, 'Candidate money source')
    require(ref['automatic_source']['public_head'] == AUTOMATIC, 'Candidate automatic source')
    for path, blob in ref['unchanged_money_product']['files'].items():
        require(git('hash-object', str(repo / path)).decode().strip() == blob, path)
    auto_pins = ref['automatic_files']
    for path, expected in auto_pins.items():
        require(git('rev-parse', AUTOMATIC + ':' + path).decode().strip() == expected['blob'], path)
        require(pin((auto_root / path).read_bytes()) == {k: expected[k] for k in ('bytes', 'sha256')}, path)

    source = (native27 / NATIVE27).read_bytes()
    require(pin(source)['sha256'] == NATIVE27_SHA, 'Native27 original')
    raw_catalogue = json.loads(source)['committed'][CASE_KEY]['Native_to_copy_handoff']['raw_current_catalog']
    env = {**os.environ, 'CP7_SKU_PARENT_ORIGINALS': str(native27)}
    modes = ('REBALANCE', 'MONEY', 'INVERSE_REPAIR', 'BASE_MONEY', 'CHAIN_MODEL', 'MONEY_CREDIT_ONLY', 'BASE_CENT_ONLY')
    env.update({f'CP7_COST_{mode}': '1' for mode in modes})
    out.mkdir(parents=True, exist_ok=False)
    subprocess.run([sys.executable, '-B', str(repo / 'scripts/cp7_sku_cost_components/prepare_legacy_model.py'), str(out)],
                   cwd=repo, env=env, check=True)

    sys.path[:0] = [str(auto_root / 'scripts'), str(auto_root / 'scripts/cp7_sku_cost_components')]
    from cp7_sku_cost_components import prepared_product as money
    from cp7_sku_automatic_pending import installation_product as automatic
    originals = {sig: raw_catalogue['functions'][sig][0] for sig in money.parent_original_signatures()}
    money_product = money.derive(raw_catalogue, originals)
    profile = json.loads((repo / 'scripts/cp7_sku_cost_components/CATALOG_ADDITIONS.json').read_bytes())
    money_rows = raw_catalogue['functions'] | profile['groups']['functions'] | profile['replacement_functions']
    auto = automatic.derive({'functions': money_rows}, raw_catalogue, originals)

    input_path = out / 'COST_MODEL_INPUT.json'
    inputs = json.loads(input_path.read_bytes())
    require(inputs['cost_ddl'] == money_product['ddl'], 'Retained model differs from candidate money DDL')
    # The automatic scope reads BS provenance even when the test has no BS rows.
    bs_columns = [row for key, row in raw_catalogue['columns'].items() if key.startswith('erp.bs_cases:')]
    require(bool(bs_columns), 'Exact BS case types required by the automatic source')
    inputs['columns']['erp.bs_cases'] = sorted(bs_columns, key=lambda row: row[1])
    inputs['automatic_delta'] = {'ddl': auto['ddl'], 'definitions': auto['definitions']}
    inputs['candidate_money_definitions'] = money_product['definitions']
    native_book_signatures = ('erp.account_id(text)', BOOK_SIGNATURE)
    inputs['native_book_definitions'] = {sig: raw_catalogue['functions'][sig][0] for sig in native_book_signatures}
    inputs['source_pins'] = dict(
        candidate=CANDIDATE, candidate_tree=git('rev-parse', CANDIDATE + '^{tree}').decode().strip(),
        money=MONEY, money_tree=git('rev-parse', MONEY + '^{tree}').decode().strip(),
        automatic=AUTOMATIC, automatic_tree=git('rev-parse', AUTOMATIC + '^{tree}').decode().strip(),
        money_files_checked=len(ref['unchanged_money_product']['files']), automatic_files_checked=len(auto_pins),
        native27=pin(source), money_ddl=pin(money_product['ddl'].encode()),
        money_definitions=len(money_product['definitions']), automatic_definitions=len(auto['definitions']),
        automatic_ddl=pin(auto['ddl'].encode()), native_book={sig: pin(body.encode()) for sig, body in inputs['native_book_definitions'].items()},
    )
    input_path.write_text(json.dumps(inputs, sort_keys=True) + '\n')

    original = (out / 'test_cost_successor.mjs').read_text()
    import_marker = 'const {PGlite} = await import(process.env.CP7_PGLITE_MODULE);'
    first_case = " await control('Original unsold cost counterexample now accepts"
    require(original.count(import_marker) == original.count(first_case) == 1, 'Retained model boundary changed')
    prefix = original.split(first_case)[0]
    prefix = prefix.replace(import_marker, 'const {Pg17Lab, runFocusedCases} = await import(process.env.CP7_FOCUSED_PROBE);')
    require(prefix.count('const db = new PGlite()') == 1, 'Retained model connection changed')
    prefix = prefix.replace('const db = new PGlite()', 'const db = await Pg17Lab.open()')
    end = """
 for (const definition of Object.values(input.candidate_money_definitions)) await db.exec(definition);
 await db.exec(input.automatic_delta.ddl);
 for (const definition of Object.values(input.automatic_delta.definitions)) await db.exec(definition);
 for (const definition of Object.values(input.native_book_definitions)) await db.exec(definition);
 await runFocusedCases({db, input, engine, x, id, query, scalar, insert, saleSetup, costReconcile,
  costPool, costSnapshot, costBaseline, initializeBaseFixture, costDocument, costAccount});
} catch (error) {
 await db.firstFailure(error, 'SETUP_OR_CLEANUP');
 process.exitCode = 1;
} finally {
 await db.close();
}
"""
    (out / 'focused.mjs').write_text(prefix + end)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('money_checkout', type=Path)
    parser.add_argument('automatic_source', type=Path)
    parser.add_argument('native27_originals', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    prepare(*(p.resolve() for p in (args.money_checkout, args.automatic_source, args.native27_originals, args.output)))
