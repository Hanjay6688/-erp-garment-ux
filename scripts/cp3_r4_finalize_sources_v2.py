#!/usr/bin/env python3
from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[1]
target = root / 'scripts/cp3_r4_finalize_sources.py'
text = target.read_text(encoding='utf-8')
old = '''if workflow.count(race_marker) != 1:
    raise SystemExit(f"R4 workflow: expected one R3 concurrency command, found {workflow.count(race_marker)}")
lines = workflow.splitlines()
new_lines: list[str] = []
for line in lines:
    new_lines.append(line)
    if race_marker in line:
        indent = line[: len(line) - len(line.lstrip())]
        new_lines.append(indent + line.strip().replace(race_marker, "scripts/cp3_r4_full_schema_concurrency.py"))
'''
new = '''race_command_count = sum(1 for line in workflow.splitlines() if race_marker in line and "python" in line)
if race_command_count != 1:
    raise SystemExit(f"R4 workflow: expected one executable R3 concurrency command, found {race_command_count}")
lines = workflow.splitlines()
new_lines: list[str] = []
for line in lines:
    new_lines.append(line)
    if race_marker in line and "python" in line:
        indent = line[: len(line) - len(line.lstrip())]
        new_lines.append(indent + line.strip().replace(race_marker, "scripts/cp3_r4_full_schema_concurrency.py"))
'''
if text.count(old) != 1:
    raise SystemExit('R4 finalizer v2 could not find the exact race-command patch anchor')
target.write_text(text.replace(old, new, 1), encoding='utf-8')
runpy.run_path(str(target), run_name='__main__')
