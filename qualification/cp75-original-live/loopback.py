"""Keep the archived database isolated and expose its PostgreSQL TCP listener only on runner loopback."""
import json
import os
import selectors
import socket
import socketserver
import subprocess
import sys
from pathlib import Path


def relay(client, postgres):
    with selectors.DefaultSelector() as events:
        events.register(client, selectors.EVENT_READ, postgres)
        events.register(postgres, selectors.EVENT_READ, client)
        while events.get_map():
            for event, _ in events.select():
                source, destination = event.fileobj, event.data
                block = source.recv(65536)
                if block:
                    destination.sendall(block)
                else:
                    events.unregister(source)
                    destination.shutdown(socket.SHUT_WR)


class DatabaseConnection(socketserver.BaseRequestHandler):
    def handle(self):
        name = "supabase_db_cp5-local"
        state, = json.loads(subprocess.check_output(["docker", "inspect", name]))
        if state["Config"]["Labels"].get("cp75.run") != os.environ["GITHUB_RUN_ID"]:
            raise ValueError("The active database does not belong to this synthetic run")
        pid = state["State"]["Pid"]
        if type(pid) is not int or pid <= 1:
            raise ValueError("Synthetic PostgreSQL is not running")
        # Switch only the network namespace. The host listener and target are
        # loopback, and the client still authenticates to PostgreSQL over TCP.
        subprocess.run(["sudo", "-n", "nsenter", "--target", str(pid), "--net",
                        sys.executable, str(Path(__file__).resolve()), "--peer"],
                       stdin=self.request, stdout=self.request, check=True)


class RunnerListener(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    if sys.argv[1:] == ["--peer"]:
        with socket.socket(fileno=0) as client, socket.create_connection(("127.0.0.1", 5432), timeout=10) as postgres:
            postgres.settimeout(None)
            relay(client, postgres)
    elif sys.argv[1:] == ["--serve"]:
        ready = Path(os.environ["RUNNER_TEMP"]) / "cp75-originals" / "loopback-ready"
        with RunnerListener(("127.0.0.1", 54322), DatabaseConnection) as server:
            ready.write_text(str(os.getpid()))
            server.serve_forever()
    else:
        raise SystemExit("Select the runner listener or its isolated PostgreSQL peer")
