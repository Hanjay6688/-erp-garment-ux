"""Materialize the exact, two-file AUD-G04 successor to the final UI candidate."""

from base64 import b64decode
from hashlib import sha256
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


PARENT = '9ee09e9562978e8a501da2a9d36defd9ea30bfcf'
PARENT_TREE = '747313f22979077f2b149b6e90bf24374e9bb869'
PRODUCT = '672ad1464524d4f9c87ba98a18e9f84f6a73af95'
TREE = 'c2f4754f106010152e3b8896f9db380c426ce0cb'
BUNDLE = 'qualification/p21/g04-sale-credit.bundle.b64'
BUNDLE_SHA256 = '9db025b0313094af2e6fb10d7aad92054752904701151bd9f313b3a0916e810f'
REF = 'refs/heads/writer-a/cp7-g04-sale-credit'
FILES = {'scripts/cp7-src/sales/reverse-neutral-credit.sql', 'scripts/cp7_sale_reverse_credit_install.py'}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def git(product, *args):
    return subprocess.check_output(('git', '-C', str(product), *args),
                                   text=True, stderr=subprocess.STDOUT).strip()


def confirm_source(product):
    require((git(product, 'rev-parse', 'HEAD'), git(product, 'rev-parse', 'HEAD^{tree}'),
             git(product, 'rev-parse', 'HEAD^')) == (PRODUCT, TREE, PARENT), 'CP7_AUD_G04_UNEXPECTED_PRODUCT_PIN')
    require(not git(product, 'status', '--porcelain', '--untracked-files=no'), 'CP7_AUD_G04_PRODUCT_TRACKED_DRIFT')
    changed = set(git(product, 'diff', '--no-renames', '--name-only', 'HEAD^', 'HEAD').splitlines())
    require(changed == FILES, 'CP7_AUD_G04_PRODUCT_CHANGE_SCOPE')


def prepare(product, raw):
    require((git(product, 'rev-parse', 'HEAD'), git(product, 'rev-parse', 'HEAD^{tree}')) == (PARENT, PARENT_TREE)
            and not git(product, 'status', '--porcelain', '--untracked-files=no'), 'CP7_AUD_G04_UNEXPECTED_PARENT_PIN')
    bundle = b64decode(b''.join(raw.splitlines()), validate=True)
    require(sha256(bundle).hexdigest() == BUNDLE_SHA256, 'CP7_AUD_G04_PRODUCT_BUNDLE_CHANGED')
    with TemporaryDirectory(prefix='g04-product-') as work:
        path = Path(work) / 'successor.bundle'
        path.write_bytes(bundle)
        git(product, 'bundle', 'verify', str(path))
        git(product, 'fetch', '--no-tags', str(path), REF)
        require(git(product, 'rev-parse', 'FETCH_HEAD') == PRODUCT, 'CP7_AUD_G04_PRODUCT_BUNDLE_HEAD_CHANGED')
        git(product, 'checkout', '--quiet', '--detach', PRODUCT)
    confirm_source(product)
