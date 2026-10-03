"""Actual disposable note-command timings; no Native40 qualification credit."""
import cp7_note_correction_probe as owning
import cp7_note_command_diagnostic_cases as diagnostic

if __name__ == '__main__':
    owning.package._writer_runtime = lambda browser_mode=False: owning.run(diagnostic.cases_provider)
    owning.package.run('install')
