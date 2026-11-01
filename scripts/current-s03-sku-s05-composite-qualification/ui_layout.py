"""Only the reviewed S05 CSS delta; original bytes must recover exactly."""
from hashlib import sha256

PATH='src/accessory-standard-report.css'
ORIGINAL_SHA256='a9d62618178521d25fa392e6497e24ebc1e8146277b9cda33a9d76e7ea76d16a'
DERIVED_SHA256='0ca870ad603a4654d44b4f9b8905f4e91c47d26ff45947d8017d17a1b8b3bcdf'
CHANGES=(('.asr-report .asr-filters { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; margin: 16px 0; }\n', '.panel.asr-report { min-width: 0; max-width: 100%; padding: 20px; background: #111522; color: #f4f6fb; overflow-wrap: anywhere; }\n.asr-report .asr-filters { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; margin: 16px 0; }\n'), ('.asr-report label { display: grid; gap: 5px; font-weight: 600; }\n.asr-report input, .asr-report select { max-width: 100%; padding: 8px; font: inherit; }\n.asr-report button { min-height: 40px; padding: 8px 12px; }\n', '.asr-report label { display: grid; min-width: 0; gap: 5px; font-weight: 600; }\n.asr-report input, .asr-report select { min-width: 0; max-width: 100%; padding: 8px; border: 1px solid #64748b; border-radius: 8px; background: #0a0c14; color: #f4f6fb; color-scheme: dark; font: inherit; }\n.asr-report select { width: 100%; }\n.asr-report button { min-height: 40px; max-width: 100%; padding: 8px 12px; border: 1px solid #64748b; border-radius: 8px; background: #202b42; color: #f4f6fb; white-space: normal; overflow-wrap: anywhere; }\n'), ('.asr-report button[aria-pressed="true"] { outline: 2px solid currentColor; outline-offset: 2px; font-weight: 700; }\n', '.asr-report .asr-contractors li { min-width: 0; max-width: 100%; }\n.asr-report button[aria-pressed="true"] { outline: 2px solid currentColor; outline-offset: 2px; background: #294258; font-weight: 700; }\n'), ('.asr-report .asr-scroll { max-width: 100%; overflow-x: auto; }\n', '.asr-report .asr-scroll { min-width: 0; max-width: 100%; overflow-x: auto; }\n'))

def derive(raw):
    if sha256(raw).hexdigest()!=ORIGINAL_SHA256:
        raise ValueError('S05_LAYOUT_EXACT_ORIGINAL_CSS_REQUIRED')
    value=raw.decode()
    for before,after in CHANGES:
        if value.count(before)!=1 or after in value:
            raise ValueError('S05_LAYOUT_EXACT_SINGLE_CSS_HUNK_REQUIRED')
        value=value.replace(before,after,1)
    reverse=value
    for before,after in reversed(CHANGES):
        if reverse.count(after)!=1:
            raise ValueError('S05_LAYOUT_EXACT_CSS_INVERSE_HUNK_REQUIRED')
        reverse=reverse.replace(after,before,1)
    if reverse.encode()!=raw or sha256(value.encode()).hexdigest()!=DERIVED_SHA256:
        raise ValueError('S05_LAYOUT_EXACT_CSS_BYTES_REQUIRED')
    return value.encode(),dict(path=PATH,original_sha256=ORIGINAL_SHA256,derived_sha256=DERIVED_SHA256,
        counted_changes=len(CHANGES),complete_original_recovered=True,backend_or_reader_oracle_changed=False,actual_case_credit=0)
