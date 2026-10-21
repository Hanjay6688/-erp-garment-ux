"""Offline client-query/drop-refusal regression; never Native execution."""
import json
from unittest.mock import patch
from psycopg._queries import PostgresQuery
from psycopg.adapt import Transformer
from psycopg.errors import ProgrammingError
import cp7_full_owning_install as full


class Cursor:
    def __init__(self):
        self.queries = []

    def execute(self, query, params=None):
        text = query if isinstance(query,str) else query.as_string()
        if params is not None:
            parsed = PostgresQuery(Transformer())
            parsed.convert(text,params)
        self.queries.append(text)
        return self

    def fetchall(self):
        return [('cp7_credit','return_requests')]

    def fetchone(self):
        return (1,'a'*64)


def run():
    results = {}
    try:
        PostgresQuery(Transformer()).convert(
            "select 1 where 'cp7_credit' like 'cp7\\_%' or ''=any(%s::text[])",([],))
    except ProgrammingError as error:
        results['original_literal_percent_failure_reproduced'] = "only '%s', '%b', '%t'" in str(error)
    else:
        results['original_literal_percent_failure_reproduced'] = False
    cursor = Cursor()
    actual = full.private_rows(cursor)
    results['actual_row_guard_queries_client_parsed'] = actual == {'cp7_credit.return_requests':(1,'a'*64)} \
        and len(cursor.queries)==2 and 'left(n.nspname,4)' in cursor.queries[0]
    seeded = {'cp7_credit.return_requests':(1,'a'*64)}
    for name,rows in (
        ('same_count_changed_content_refused',{'cp7_credit.return_requests':(1,'b'*64)}),
        ('new_table_refused',{**seeded,'ow04_source_proposal.extra':(0,'c'*64)}),
        ('missing_table_refused',{}),
    ):
        with patch.object(full,'verify'),patch.object(full,'private_rows',return_value=rows), \
                patch.object(full.credit,'uninstall') as removal:
            try:
                full.rollback_preuse(cursor,{'seeded_private_rows':seeded})
            except ValueError as error:
                results[name] = str(error)=='CP7_FULL_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE' \
                    and not removal.called and len(cursor.queries)==2
            else:
                results[name] = False
    assert all(results.values()),results
    return dict(classification='OFFLINE_CLIENT_AND_REFUSAL_CONTROLS_NOT_NATIVE',
        database_calls=0,controls=results,passed=len(results),native_executed=False)


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
