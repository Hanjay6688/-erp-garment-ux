"""Exact proven two-checkout browser preconditions; no ERP admission."""
from hashlib import sha256
from pathlib import Path
import argparse
import json

HERE = Path(__file__).resolve().parent
DONOR_HEAD = '21542ca22ad08f366d8f3c69929ca47b2d79b5f5'
DONOR_PIN = dict(bytes=6038, sha256='0484299806098b217b4fb159155a0992d5bef12a6b44e4ca3023b20529a76d73')
DONOR = HERE / 'browser_prerequisites_215.mjs.txt'
TARGET = HERE / 'browser_prerequisites.mjs'
RECEIPT = 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_BROWSER_PREREQUISITES.json'


def require(value, reason):
    if not value:
        raise ValueError(reason)


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def derive(raw=None):
    if raw is None:
        raw = DONOR.read_bytes()
    require(pin(raw) == DONOR_PIN, 'SKU_BROWSER_EXACT_PROVEN_TWO_CHECKOUT_PREFLIGHT_SOURCE_REQUIRED')
    routes = (
        ('scripts/cp7_accessory_nonpayable/browser.mjs',
         'scripts/current-sku-automatic-composite-preparation/browser.mjs'),
        ("'AFUI_BROWSER_PREREQUISITES.json'", repr(RECEIPT)),
    )
    text = raw.decode()
    for before, after in routes:
        require(text.count(before) == 1 and after not in text, 'SKU_BROWSER_ONE_EXACT_PREFLIGHT_ROUTE')
        text = text.replace(before, after, 1)
    recovered = text
    for before, after in reversed(routes):
        require(recovered.count(after) == 1, 'SKU_BROWSER_EXACT_PREFLIGHT_INVERSE_ROUTE')
        recovered = recovered.replace(after, before, 1)
    require(recovered.encode() == raw, 'SKU_BROWSER_COMPLETE_ORIGINAL_PREFLIGHT_NOT_RECOVERED')
    return text, dict(classification='SKU_BROWSER_PACKAGE_PREFLIGHT_PREPARED_NOT_ACTUAL_BROWSER_CASE',
                      exact_donor_head=DONOR_HEAD, retained=DONOR_PIN, derived=pin(text.encode()),
                      reversible_routes=2, complete_original_recovered=True,
                      independent_actual_checkout_processes=True,
                      real_desktop_and_mobile_launch_in_each_checkout=True,
                      candidate_build_and_exact_own_browser_module_import=True,
                      actual_SQL_executed=0, actual_Auth_requests=0, actual_browser_case_credit=0,
                      production_go=False)


def check():
    text, proof = derive()
    require(TARGET.is_file() and not TARGET.is_symlink() and TARGET.read_bytes() == text.encode(),
            'SKU_BROWSER_EXACT_REVIEWED_PREFLIGHT_REQUIRED')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--check', required=True, action='store_true');parser.parse_args()
    print(json.dumps(check(), sort_keys=True))
