"""Check every enabled host listener in this disposable SKU setup before start.

Never change ports, stop another listener, connect to an existing database, or
retry ERP cases. Docker startup can still race after the bind probes close;
the retained startup helper refuses a bind conflict without registry retries.
"""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import tomllib


def ports(config):
    result = {"db.port": config["db"]["port"]}
    for section in ("api", "inbucket"):
        block = config.get(section, {})
        if block.get("enabled", True):
            for key in ("port", "smtp_port", "pop3_port"):
                if key in block:
                    result[section + "." + key] = block[key]
    if any(type(p) is not int or not 1024 <= p <= 65535 for p in result.values()):
        raise ValueError("DISPOSABLE_INVALID_HOST_PORT")
    if len(set(result.values())) != len(result):
        raise ValueError("DISPOSABLE_DUPLICATE_HOST_PORT")
    return result


def preflight(config_path, report_path, *, collect=True):
    raw = Path(config_path).read_bytes()
    declared = ports(tomllib.loads(raw.decode()))
    report = dict(status="CHECKING", scope="HOST_LISTENERS_BEFORE_DISPOSABLE_START",
                  checked_at_utc=datetime.now(timezone.utc).isoformat(),
                  config=dict(bytes=len(raw), sha256=sha256(raw).hexdigest()),
                  listeners=[], diagnostics=[], other_processes_stopped=False,
                  ports_changed=False, actual_Native_cases=0)
    held = []
    try:
        for name, port in declared.items():
            probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            held.append(probe)
            item = dict(setting=name, address="0.0.0.0", port=port, available=False)
            try:
                probe.bind(("0.0.0.0", port))
                item["available"] = True
            except OSError as error:
                item["error"] = dict(errno=error.errno, message=str(error))
            report["listeners"].append(item)
        if collect:
            commands = [
                ["ss", "-H", "-ltnp", "( " + " or ".join(f"sport = :{p}" for p in declared.values()) + " )"],
                ["docker", "ps", "--format", "{{.ID}}\t{{.Names}}\t{{.Ports}}"],
            ]
            for command in commands:
                try:
                    result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
                    # No process command lines, environment, or container secrets.
                    output = result.stdout
                    if command[0] == "docker":
                        output = "\n".join(line for line in output.splitlines()
                                           if any(f":{p}->" in line for p in declared.values()))
                    report["diagnostics"].append(dict(command=command, exit_code=result.returncode,
                                                       stdout=output, stderr=result.stderr))
                except (OSError, subprocess.TimeoutExpired) as error:
                    report["diagnostics"].append(dict(command=command, error=type(error).__name__))
        report["status"] = "PASS" if all(x["available"] for x in report["listeners"]) else "REFUSED_PORT_CONFLICT"
        dest = Path(report_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(report, indent=2) + "\n")
        if report["status"] != "PASS":
            raise RuntimeError("DISPOSABLE_HOST_PORT_CONFLICT_NO_OTHER_LISTENER_STOPPED")
        return report
    finally:
        for probe in held:
            probe.close()


def main():
    preflight("cp5-local/supabase/config.toml", "../auditor/cp6-proof/t3/DISPOSABLE_PORT_PREFLIGHT.json")
    path = Path(__file__).resolve().parents[1] / "current-finance-combined-composition/disposable_start.py"
    spec = importlib.util.spec_from_file_location("sku_disposable_start", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.start(Path("../auditor/cp6-proof/t3/disposable-startup-attempts"))


if __name__ == "__main__":
    main()
