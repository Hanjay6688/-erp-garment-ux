"""Owning-transaction adapter, gated by one verified focused diagnostic."""

from hashlib import sha256
import json
from pathlib import Path

from . import bind_mandor_adapter as binding
from .guard_original_unused import original_unused_guard
from .verify_catalogue_transition import ROUTINES


ASSET_PINS = {
    "FOCUSED_INSTALLER.sql": "d85ed5728c2a5b5269d12988994a4c5388dc7d60d9e41fd6bc52cd980528ece4",
    "FOCUSED_INSTALLER_RECEIPT.json": "35f2f5fdd76b1de47be912eab08156af796f7616f76b086f81fb66fcd1764ebd",
    "FORMAL_ALL22_WIB_GUARD_FIXTURE.json": "2d392768907d3ab4bb232df14500ec43160347a46395ab1b2cd209530cb12349",
    "UNUSED_INVERSE.sql": "04f4b1527fc9f79907460399135fa78d27c442c42fa3f68a29e6b806bba3e681",
}
USED = "MANDOR_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def verify_terminal(raw, expected_sha256):
    require(sha256(raw).hexdigest() == expected_sha256, "MANDOR_ADAPTER_TERMINAL_PIN_CHANGED")
    proof = json.loads(raw)
    require(proof.get("status") == "VERIFIED_FOCUSED_DIAGNOSTIC_PASS"
            and proof.get("run") == 42479817344 and proof.get("job") == 128729109169
            and proof.get("qualification_credit") == 0
            and proof.get("cleanup_success") is True and proof.get("rollback_proven") is True
            and type(proof.get("artifact")) is int and proof["artifact"] > 0
            and type(proof.get("native_originals")) is int and proof["native_originals"] > 0,
            "MANDOR_ADAPTER_REQUIRES_VERIFIED_FOCUSED_PASS")
    return proof


def read_exact(directory, name, expected):
    path = directory / name
    require(path.is_file() and not path.is_symlink(), "MANDOR_ADAPTER_SOURCE_NOT_REGULAR:" + name)
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == expected, "MANDOR_ADAPTER_SOURCE_CHANGED:" + name)
    return raw


def installer_body(raw):
    lines = raw.decode().splitlines()
    require(lines[:2] == ["\\set ON_ERROR_STOP on", "begin;"] and lines[-1:] == ["commit;"]
            and lines.count("begin;") == 1 and lines.count("commit;") == 1,
            "MANDOR_ADAPTER_INSTALLER_TRANSACTION_WRAPPER_CHANGED")
    return "\n".join(lines[2:-1]) + "\n"


def execute_as_trusted_installer(cur, mandor, statement):
    # The owning workflow already uses a disposable maintenance session.
    # Use its verified identity for DDL spanning multiple schema owners.
    mandor.trusted_installer(cur)
    installer = cur.execute("select session_user").fetchone()[0]
    with mandor.as_role(cur, installer, {installer}):
        cur.execute(statement, prepare=False)


def normalize_used(error):
    if isinstance(error, ValueError):
        text = str(error)
    elif getattr(error, "sqlstate", None) == "P0001":
        text = getattr(getattr(error, "diag", None), "message_primary", None)
    else:
        return False
    return isinstance(text, str) and (text == USED or text.startswith(USED + ":"))


class Adapter:
    def __init__(self, terminal_sha256, directory=None):
        directory = Path(__file__).resolve().parent if directory is None else Path(directory)
        terminal = read_exact(directory, "VERIFIED_FOCUS_TERMINAL.json", terminal_sha256)
        proof = verify_terminal(terminal, terminal_sha256)
        assets = {name: read_exact(directory, name, pin) for name, pin in ASSET_PINS.items()}
        self._installer = installer_body(assets["FOCUSED_INSTALLER.sql"])
        self._inverse = assets["UNUSED_INVERSE.sql"].decode()
        self._footprint = json.loads(assets["FORMAL_ALL22_WIB_GUARD_FIXTURE.json"])["footprint"]
        self._receipt = json.loads(assets["FOCUSED_INSTALLER_RECEIPT.json"])
        self._source = dict(asset_sha256=ASSET_PINS.copy(), terminal_sha256=terminal_sha256,
                            focus_run=proof["run"], focus_job=proof["job"], focus_artifact=proof["artifact"])

    def sources(self):
        return dict(self._source, asset_sha256=self._source["asset_sha256"].copy())

    def install(self, cur, mandor, original):
        with mandor.atomic(cur), mandor.metadata_context(cur):
            mandor.trusted_installer(cur)
            mandor.verify(cur, original)
            raw_before = mandor.native_identity(cur, ROUTINES)
            execute_as_trusted_installer(cur, mandor, self._installer)
            adapted = binding.bind(mandor, cur, original, raw_before, self._footprint, self._receipt)
        return adapted, raw_before

    def verify(self, cur, mandor, original, adapted, raw_before):
        return binding.verify(mandor, cur, original, adapted, raw_before, self._footprint, self._receipt)

    def rollback(self, cur, mandor, original, adapted, raw_before):
        try:
            with mandor.atomic(cur), mandor.metadata_context(cur):
                mandor.trusted_installer(cur)
                self.verify(cur, mandor, original, adapted, raw_before)
                cur.execute(original_unused_guard(original["plan"]["tables"]), prepare=False)
                execute_as_trusted_installer(cur, mandor, self._inverse)
                require(mandor.native_identity(cur, ROUTINES) == raw_before,
                        "MANDOR_ADAPTER_INVERSE_RAW_AUTHORITY_CHANGED")
                # The original inverse re-verifies its complete exact catalogue
                # and original use guard, then performs its existing narrow DDL.
                return mandor.rollback_preuse(cur, original)
        except Exception as error:
            if normalize_used(error):
                raise ValueError(USED) from error
            raise
