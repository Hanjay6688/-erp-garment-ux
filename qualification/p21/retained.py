"""Reuse the vetted P21 and E14 receipts without exporting their private originals."""
import sys

from . import preflight


def verify_retained():
    return preflight.checked(preflight.EVIDENCE.read_bytes())['p21']


if __name__ == '__main__':
    preflight.write(sys.argv[1], verify_retained())
