"""Reject unsafe bytes before uploading evidence from this disposable test."""
from pathlib import Path
import re
import sys


SECRET_PATTERNS = tuple(re.compile(value, re.I) for value in (
    r'\b(?:gh[pousr]_[a-z0-9]{24,}|github_pat_[a-z0-9_]{25,})\b',
    r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b',
    r'-----BEGIN [A-Z ]*PRIVATE KEY-----',
    r'"\b(?:access_token|refresh_token|password|service_role_key|anon_key)"\s*:\s*"[^"]+"',
    r'https?://[a-z0-9-]+\.supabase\.(?:co|in)\b',
    r'postgres(?:ql)?://[^/\s]+@(?!(?:127\.0\.0\.1|localhost)[:/])[^/\s]+',
    r'-- PostgreSQL database dump|^PGDMP',
))
STEMS = (
    'P21_FOLLOWUP_ORIGINALS/*',
    'GLOBAL_AUTH_*_BASELINE.json',
    'GLOBAL_AUTH_*_REST_BOUND.json',
    'GLOBAL_AUTH_*_MAPPING.json',
    'GLOBAL_AUTH_*_FINAL_CLEANUP.json',
)


def check(path):
    if path.suffix not in ('.json', '.txt', '.ts') or path.is_symlink() or not path.is_file():
        raise ValueError('P21_PUBLIC_EVIDENCE_FILE_TYPE')
    document = path.read_text(encoding='utf-8')
    if '\x00' in document or any(p.search(document) for p in SECRET_PATTERNS):
        raise ValueError('P21_PUBLIC_EVIDENCE_SENSITIVE_BYTES')


def main():
    groups = {'raw': STEMS, 'source': ('ordinary-preflight*.json',),
              'terminal': ('P21_INSTALLATION_FINAL.json',)}
    scope, directory = sys.argv[1:]
    try:
        root = Path(directory)
        if root.is_symlink():
            raise ValueError('P21_PUBLIC_EVIDENCE_UNSAFE_ROOT')
        files = [path for stem in groups[scope] for path in root.glob(stem)]
        if not files and scope in ('raw', 'terminal'):
            raise ValueError('P21_PUBLIC_EVIDENCE_EMPTY')
        for file in files:
            check(file)
    except (OSError, UnicodeError, ValueError) as error:
        if type(error) is ValueError and str(error).startswith('P21_PUBLIC_EVIDENCE_'):
            raise SystemExit(str(error))
        raise SystemExit('P21_PUBLIC_EVIDENCE_READ_FAILED')
    print(f'P21_PUBLIC_SYNTHETIC_EVIDENCE_CHECK_PASS group={scope} files={len(files)}')


if __name__ == '__main__':
    main()

