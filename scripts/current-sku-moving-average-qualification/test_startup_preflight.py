from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import socket
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import startup_preflight as guard


class StartupBoundaries(unittest.TestCase):
    def test_all_enabled_ports_come_from_config_and_disabled_ports_are_omitted(self):
        self.assertEqual(guard.ports({"db": {"port": 54322, "shadow_port": 54320},
            "api": {"enabled": True, "port": 54321},
            "inbucket": {"enabled": True, "port": 54324, "smtp_port": 54325, "pop3_port": 54326},
            "studio": {"enabled": True, "port": 54323}}),
            {"db.port": 54322, "api.port": 54321, "inbucket.port": 54324,
             "inbucket.smtp_port": 54325, "inbucket.pop3_port": 54326})
        self.assertEqual(guard.ports({"db": {"port": 54322}, "api": {"enabled": False, "port": 54321},
            "inbucket": {"enabled": False, "port": 54324}}), {"db.port": 54322})

    def test_invalid_or_duplicate_ports_refuse(self):
        for config in [{"db": {"port": True}}, {"db": {"port": 0}},
                       {"db": {"port": 54322}, "api": {"port": 54322}}]:
            with self.assertRaises(ValueError):
                guard.ports(config)

    def test_actual_busy_socket_is_retained_and_not_stopped(self):
        with socket.socket() as owned, TemporaryDirectory() as folder:
            owned.bind(("127.0.0.1", 0)); owned.listen()
            port = owned.getsockname()[1]
            config, report = Path(folder)/"config.toml", Path(folder)/"report.json"
            config.write_text(f"[db]\nport={port}\n[api]\nenabled=false\n[inbucket]\nenabled=false\n")
            with patch.object(guard.subprocess, "run") as process:
                with self.assertRaisesRegex(RuntimeError, "NO_OTHER_LISTENER_STOPPED"):
                    guard.preflight(config, report, collect=False)
                process.assert_not_called()
            data = json.loads(report.read_text())
            self.assertEqual(data["status"], "REFUSED_PORT_CONFLICT")
            self.assertEqual(data["listeners"][0]["port"], port)
            self.assertFalse(data["listeners"][0]["available"])
            self.assertEqual(owned.getsockname()[1], port)

    def test_free_port_is_released_after_preflight(self):
        with TemporaryDirectory() as folder:
            with socket.socket() as reservation:
                reservation.bind(("0.0.0.0", 0)); port = reservation.getsockname()[1]
            config, report = Path(folder)/"config.toml", Path(folder)/"report.json"
            config.write_text(f"[db]\nport={port}\n[api]\nenabled=false\n[inbucket]\nenabled=false\n")
            self.assertEqual(guard.preflight(config, report, collect=False)["status"], "PASS")
            with socket.socket() as next_owner:
                next_owner.bind(("0.0.0.0", port))

    def test_post_check_docker_bind_race_keeps_first_failure_without_retry(self):
        path=Path(__file__).resolve().parents[1]/"current-finance-combined-composition/disposable_start.py"
        spec=importlib.util.spec_from_file_location("startup_race_test",path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        calls=[];delays=[]
        failure=b'failed to bind host port for 0.0.0.0:54322: address already in use\n'
        def run(command, **kwargs):
            calls.append(command)
            kwargs["stdout"].write(failure if command==module.START else b'own attempted project stopped\n')
            return SimpleNamespace(returncode=1 if command==module.START else 0)
        with TemporaryDirectory() as folder, redirect_stdout(io.StringIO()):
            proof=Path(folder)/"attempts"
            with self.assertRaisesRegex(RuntimeError, "NO_REGISTRY_RETRY"):
                module.start(proof,run=run,pause=delays.append,environment={})
            self.assertEqual(calls,[module.START,module.STOP]);self.assertEqual(delays,[])
            self.assertEqual((proof/"attempt-1-start.log").read_bytes(),failure)
            self.assertEqual(json.loads((proof/"STARTUP_ATTEMPTS.json").read_text())["status"],"REFUSED_PORT_CONFLICT")


if __name__ == "__main__":
    unittest.main()
