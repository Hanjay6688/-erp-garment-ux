"""Actual disposable note-command timings; no Native40 qualification credit."""
import cp7_note_correction_probe as owning
import cp7_note_command_diagnostic_cases as diagnostic
import cp7_note_actual_http_diagnostic_cases as actual_http

if __name__ == '__main__':
    owning.package._writer_runtime = lambda browser_mode=False: owning.run(diagnostic.cases_provider,actual_http)
    owning.package.run('install')
