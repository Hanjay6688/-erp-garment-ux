# Source-import argv successor of public b874 / local2834

Public head `b874783f57be809a867ce4d0806553a17c03243e` and local parent
`2834c9ada13a1f70f79bf67c62f5c7d3554e2cb5` share exact tree
`7f78cf2488afeca9d90a0d281a873c556dee082e`. Actual run40928511140,
job123640384388 failed at source admission `check.py --runtime`, before
`Start disposable database`, with the exact terminal:
`Current used-state restore accepts no arguments`.

The unchanged inherited `ow04-payment-used-restore-qualification/probe.py`
rejects `sys.argv[1:]` during import. The old wrapper accidentally forwarded its
own accepted `--runtime` flag. Its alternate `probe.py --check` has the same
cause. This is a source-import CLI boundary failure, not a Native, installer,
report calculation, database, or restoration result.

Only own `probe.check` now enters `import_argv.source_import_arguments` around
both `runtime()` and `admitted()` so delayed imports receive argv[0] only. The
exact caller list object AND contents are restored with try/finally after
success or any BaseException, including SystemExit/KeyboardInterrupt. Nested
calls restore their intermediate list correctly. The outer parsers reject
unknown flags before this boundary. `probe.runtime`, `probe.execute`, its
confirmation, original engine, parent modules and all product functions remain
unchanged; no inherited/plugin/Native global or function is replaced.

The source-only transition verifier closes the frozen parent112 pins, permits
only the named own wrapper/source metadata changes, and requires all report
SQL, stage, ten Native callbacks, UI, engine, gates and old module bytes to
remain exact. `workflow_source.py` changes only its execution-leaf constant to
`astra-a/s05-native10-import-argv-20261029`; workflow path,64 steps, runtime setup,
preconditions, install/inverse/reinstall, source admission before database,
complete restore, artifacts and five package gates stay unchanged. The old
published branch is not modified or automatically selected by this successor.

`B874_FIRST_FAILURE_RECEIPT.json` retains root's exact hash-verified receipt and
bounded terminal excerpt. `FIRST_FAILURE.json` records independent ZIP
verification:52,724 bytes, SHA256
`390e35d82df83fcce83752f2b38305b24ec4c9adfd23afeb4a2905583e74c401`,
98 entries (97 artifact-fetch metadata JSON +1 frozen-source metadata). There
is no T3/Native report. No complete environment log is copied. Database start,
Native cases and package.run were all0; restoration is NOT_APPLICABLE.

Eight new controls execute the actual own CLI parsers with explicit no-DB
engine/admission import doubles. Both doubles run the exact old source argv
guard. They reproduce both old failures, prove successful accepted-flags
routing across immediate/lazy imports, exact caller restoration on success and
SystemExit, unknown-flag refusal, nested contexts and RuntimeError/interrupt
restoration. The actual S05 engine/product runtime is never imported by these
controls. Full inherited `--runtime` admission still requires the prepared
workflow's retained directories and remains for root's actual run.

```bash
# Source/offline only, no inherited product runtime or database:
PYTHONDONTWRITEBYTECODE=1 GIT_NO_LAZY_FETCH=1 python scripts/current-s05-native10-qualification/check.py
PYTHONDONTWRITEBYTECODE=1 GIT_NO_LAZY_FETCH=1 python -m unittest discover -s scripts/current-s05-native10-qualification -p 'test_*.py'
```

The final owner-role repair remains exact and retains its prior8 local PGlite
controls; those are not rerun or credited as Native. The ten actual cases,
separate committed used witness, full recovery and all five package gates
remain mandatory. `Native_executions=0`, `database_calls=0`,
`independent_acceptance=false`, `production_go=false`.
