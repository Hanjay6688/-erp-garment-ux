"""Start and stop a PostgreSQL fixture bound only to IPv4 loopback."""

from contextlib import contextmanager
from pathlib import Path
import socket
import subprocess
from tempfile import TemporaryDirectory

import psycopg


@contextmanager
def cluster(bin_path):
    bin_path = Path(bin_path)
    with TemporaryDirectory(prefix='cp7-postgres-') as temporary:
        root = Path(temporary)
        data, log = root / 'data', root / 'postgres.log'
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        subprocess.run([str(bin_path / 'initdb'), '-D', str(data), '-U', 'postgres',
                        '--auth=trust', '--locale=C', '--encoding=UTF8', '--no-sync'],
                       check=True, capture_output=True, timeout=25)
        process = subprocess.Popen([str(bin_path / 'postgres'), '-D', str(data), '-h', '127.0.0.1',
                                    '-p', str(port), '-k', '', '-c', 'max_connections=10',
                                    '-c', 'fsync=off', '-c', 'synchronous_commit=off',
                                    '-c', 'full_page_writes=off'], stdout=subprocess.DEVNULL, stderr=log.open('wb'))
        settings = dict(host='127.0.0.1', port=port, user='postgres', dbname='postgres',
                        connect_timeout=1, options='-c statement_timeout=20000 -c lock_timeout=8000')
        try:
            from time import monotonic, sleep
            deadline = monotonic() + 10
            while True:
                try:
                    with psycopg.connect(**settings) as conn:
                        conn.execute('select 1')
                    break
                except psycopg.OperationalError:
                    if process.poll() is not None or monotonic() >= deadline:
                        raise RuntimeError(log.read_text()[-2500:])
                    sleep(0.05)
            yield settings
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    subprocess.run([str(bin_path / 'pg_ctl'), '-D', str(data), '-w', '-t', '10',
                                    '-m', 'immediate', 'stop'], check=True, capture_output=True, timeout=12)
