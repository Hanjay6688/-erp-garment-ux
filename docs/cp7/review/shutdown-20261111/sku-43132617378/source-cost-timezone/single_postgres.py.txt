"""Run a disposable PostgreSQL fixture in the standalone backend."""
import base64
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from uuid import UUID
import json

from psycopg import errors, sql


PROMPT = 'backend> '
ROW = re.compile(r'^\s+(\d+): .*? = (.*?)\s+\(typeid = (\d+),')
HEADER = re.compile(r'^\s+\d+: .*?\s+\(typeid = \d+,', re.MULTILINE)
ERROR = re.compile(r'\b(?:ERROR|FATAL):\s+([0-9A-Z]{5}):\s+([^\n]+)')
DECODERS = {16: lambda x: x == 't', 20: int, 21: int, 23: int, 1082: date.fromisoformat,
            1184: datetime.fromisoformat, 2950: UUID, 114: json.loads, 3802: json.loads}


class Cursor:
    def __init__(self, backend):
        self.backend = backend
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, statement, parameters=()):
        query = statement.as_string(None) if isinstance(statement, sql.Composable) else statement
        if parameters:
            parts = query.split('%s')
            assert len(parts) == len(parameters) + 1
            query = parts[0] + ''.join(sql.Literal(value).as_string(None) + part
                                       for value, part in zip(parameters, parts[1:], strict=True))
        output = self.backend.command(query)
        header, *records = output.split('\t----\n')
        count = len(HEADER.findall(header))
        rows = []
        for record in records[:-1]:
            row = [None] * count
            for line in record.splitlines():
                match = ROW.match(line)
                if match:
                    col, value, type_id = match.groups()
                    row[int(col) - 1] = DECODERS.get(int(type_id), str)(value[1:-1])
            rows.append(tuple(row))
        self.rows = rows
        return self

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)

    @contextmanager
    def copy(self, statement):
        filename = self.backend.directory / 'copy-input.txt'
        with filename.open('wb') as body:
            yield body
        prefix, suffix = statement.split(' FROM stdin;', 1)
        assert not suffix
        self.execute(prefix + ' FROM ' + sql.Literal(str(filename)).as_string(None))


class SinglePostgres:
    def __init__(self, bin_dir):
        self.bin_dir = Path(bin_dir)
        self.depth = 0

    def __enter__(self):
        self.fixture = TemporaryDirectory(prefix='sku-auth-', dir='/tmp')
        self.directory = Path(self.fixture.name)
        db = self.directory / 'db'
        subprocess.run([str(self.bin_dir / 'initdb'), '-D', str(db), '--username=postgres',
                        '--auth=trust', '--locale=C', '--encoding=UTF8'],
                       check=True, stdout=subprocess.DEVNULL)
        self.process = subprocess.Popen(
            [str(self.bin_dir / 'postgres'), '--single', '-j', '-D', str(db), '-c', 'log_error_verbosity=verbose', 'postgres'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        self.read_prompt()
        return self

    def __exit__(self, *_):
        self.process.stdin.close()
        self.process.stdout.read()
        self.process.wait(timeout=10)
        self.fixture.cleanup()

    def read_prompt(self):
        output = []
        tail = ''
        while not tail.endswith(PROMPT):
            char = self.process.stdout.read(1)
            if not char:
                raise RuntimeError('PostgreSQL standalone backend exited: ' + ''.join(output))
            output.append(char)
            tail = (tail + char)[-len(PROMPT):]
        return ''.join(output)[:-len(PROMPT)]

    def command(self, query):
        query = query.strip().rstrip(';')
        if ';\n\n' in query:
            encoded = base64.b64encode(query.encode()).decode()
            query = "DO $$BEGIN EXECUTE convert_from(decode('" + encoded + "','base64'),'UTF8'); END$$"
        self.process.stdin.write(query + ';\n\n')
        self.process.stdin.flush()
        output = self.read_prompt()
        match = ERROR.search(output)
        if match:
            state, message = match.groups()
            raise errors.lookup(state)(message.strip())
        return output

    def cursor(self):
        return Cursor(self)

    def execute(self, statement, parameters=()):
        return self.cursor().execute(statement, parameters)

    @contextmanager
    def transaction(self, force_rollback=False):
        depth = self.depth
        savepoint = f'fixture_{depth}'
        self.command('begin' if depth == 0 else 'savepoint ' + savepoint)
        self.depth += 1
        success = False
        try:
            yield
            success = True
        finally:
            self.depth -= 1
            rollback = force_rollback or not success
            if depth == 0:
                self.command('rollback' if rollback else 'commit')
            else:
                if rollback:
                    self.command('rollback to savepoint ' + savepoint)
                self.command('release savepoint ' + savepoint)
