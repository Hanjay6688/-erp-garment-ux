"""Materialize the S06 successor of the accepted G04 product."""

from base64 import b64decode
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from .g04_source import git, require

PARENT = '672ad1464524d4f9c87ba98a18e9f84f6a73af95'
PARENT_TREE = 'c2f4754f106010152e3b8896f9db380c426ce0cb'
PRODUCT = '7a17d348ea5831454c770586eff4270627003be0'
TREE = '85b9e0b0dd6cde60ff33a231c3605f23677a2321'
BUNDLE = 'qualification/p21/s06-reminder.bundle.b64'
BUNDLE_SHA256 = 'dc8ea113c06a8310cd4272efa9d917968ce71be2ad0d8dc931776d59985640ee'
REF = 'refs/heads/writer-a/cp7-close05-s06'
FILES = {'scripts/cp7_s06_reminder_forward.py', 'scripts/cp7_s06_reminder_forward_cases.py'}


def confirm_source(product):
    require((git(product, 'rev-parse', 'HEAD'), git(product, 'rev-parse', 'HEAD^{tree}'),
             git(product, 'rev-parse', 'HEAD^')) == (PRODUCT, TREE, PARENT), 'CP7_S06_UNEXPECTED_PRODUCT_PIN')
    require(not git(product, 'status', '--porcelain', '--untracked-files=no'), 'CP7_S06_PRODUCT_TRACKED_DRIFT')
    changed = set(git(product, 'diff', '--no-renames', '--name-only', 'HEAD^', 'HEAD').splitlines())
    require(changed == FILES, 'CP7_S06_PRODUCT_CHANGE_SCOPE')


def prepare(product, raw):
    require((git(product, 'rev-parse', 'HEAD'), git(product, 'rev-parse', 'HEAD^{tree}')) == (PARENT, PARENT_TREE)
            and not git(product, 'status', '--porcelain', '--untracked-files=no'), 'CP7_S06_UNEXPECTED_PARENT_PIN')
    bundle = b64decode(b''.join(raw.splitlines()), validate=True)
    require(sha256(bundle).hexdigest() == BUNDLE_SHA256, 'CP7_S06_PRODUCT_BUNDLE_CHANGED')
    with TemporaryDirectory(prefix='s06-product-') as work:
        path = Path(work) / 'successor.bundle'
        path.write_bytes(bundle)
        git(product, 'bundle', 'verify', str(path))
        git(product, 'fetch', '--no-tags', str(path), REF)
        require(git(product, 'rev-parse', 'FETCH_HEAD') == PRODUCT, 'CP7_S06_PRODUCT_BUNDLE_HEAD_CHANGED')
        git(product, 'checkout', '--quiet', '--detach', PRODUCT)
    confirm_source(product)
