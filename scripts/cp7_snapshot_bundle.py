"""Explicit isolated P02 family files; no source rewriting or runtime monkeypatch."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=('bootstrap.sql','sources.sql','facades.sql')

def bundle():
    return '\n'.join((ROOT/'scripts/cp7-src/snapshot'/name).read_text() for name in FILES)
