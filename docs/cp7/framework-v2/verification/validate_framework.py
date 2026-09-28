"""Revision2 entrypoint; original validator is retained in history/v1."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name("validate_revision_v2.py")), run_name="__main__")
