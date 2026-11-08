"""Build the pre-DDL guard for a future combined Mandor adapter inverse."""

import re


def original_unused_guard(original_tables):
    """Use table names from the verified original Mandor installation plan."""
    tables = sorted(original_tables)
    if (not tables or len(tables) != len(set(tables))
            or any(not re.fullmatch(r"cp7_mandor_shop\.[a-z_][a-z0-9_]*", table) for table in tables)):
        raise ValueError("MANDOR_ORIGINAL_PREUSE_TABLE_PLAN_CHANGED")
    checks = "\n".join(
        f" if exists (select 1 from {table} limit 1) then"
        f" raise exception 'MANDOR_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE:{table}'; end if;"
        for table in tables
    )
    return (f"lock table {', '.join(tables)} in access exclusive mode;\n"
            f"do $mandor_original_unused$ begin\n{checks}\nend $mandor_original_unused$;\n")
