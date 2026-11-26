"""Load the approved private Box archives inside a single runner job."""

import argparse
import base64
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener
from zipfile import ZipFile

import restore


PACKAGES = {
    "base": ("e91206ecc0ad52234628c67ef215eb26e054d87cc61733f0e1c072769ad2e373", 456423),
    "early": ("bab2730d5ad651404e41a1c209ec2c9ffd50d9deacb07f5b9bc947f6c737341f", 377524),
}
MAX_ENVELOPE = 1_050_000
MAX_UNPACKED = 32 * 1024 * 1024


class PackageError(RuntimeError):
    pass


def check_url(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "public.boxcloud.com"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.fragment
        or not parsed.path.startswith("/")
    ):
        raise PackageError("Tautan unduh privat Box tidak sah")


class CheckedRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url):
    check_url(url)
    try:
        with build_opener(CheckedRedirect()).open(url, timeout=35) as remote:
            body = remote.read(MAX_ENVELOPE + 1)
    except Exception:
        raise PackageError("Unduhan Box gagal atau tautannya kedaluwarsa") from None
    if len(body) > MAX_ENVELOPE:
        raise PackageError("Ukuran unduhan Box berubah")
    return body


def open_package(family, body, destination):
    expected_digest, expected_size = PACKAGES[family]
    wrapper = json.loads(body)
    compressed = base64.b64decode(wrapper["data"], validate=True)
    if len(compressed) != expected_size or wrapper["bytes"] != expected_size:
        raise PackageError("Ukuran paket Box berbeda")
    if sha256(compressed).hexdigest() != expected_digest or wrapper["sha256"] != expected_digest:
        raise PackageError("Checksum paket Box berbeda")

    with (ZipFile(io.BytesIO(compressed)) if family == "base" else
          tarfile.open(fileobj=io.BytesIO(compressed), mode="r:xz")) as archive:
        if family == "base":
            files = [(e.filename, e.file_size, e) for e in archive.infolist() if not e.is_dir()]
            read_file = archive.read
        else:
            files = [(e.name, e.size, e) for e in archive.getmembers() if e.isfile()]

            def read_file(entry):
                with archive.extractfile(entry) as source:
                    return source.read()

        names = [name for name, _, _ in files]
        if (
            len(names) != len(set(names))
            or any(name != Path(name).name or name in ("", ".", "..") for name in names)
            or sum(size for _, size, _ in files) > MAX_UNPACKED
        ):
            raise PackageError("Isi paket Box tidak sesuai")
        target = destination / family
        target.mkdir(mode=0o700)
        for name, _, entry in files:
            (target / name).write_bytes(read_file(entry))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--apply", action="store_true")
    args = cli.parse_args()
    os.umask(0o077)
    try:
        restore.connect_environment(os.environ.get("ENTENG_UJI_DATABASE_URL"), restore.CERTIFICATES)
        links = json.loads(os.environ.get("ENTENG_UJI_BOX_DOWNLOADS", "{}"))
        if not isinstance(links, dict) or links.keys() != PACKAGES.keys():
            raise PackageError("Dua tautan unduh privat Box belum dipasang")
        for url in links.values():
            check_url(url)
        with TemporaryDirectory(prefix="enteng-uji-", dir=os.environ.get("RUNNER_TEMP")) as tmp:
            root = Path(tmp)
            for family in PACKAGES:
                open_package(family, download(links[family]), root)
            env = dict(os.environ)
            env.pop("ENTENG_UJI_BOX_DOWNLOADS", None)
            args_restore = [sys.executable, str(Path(__file__).with_name("restore.py")), str(root)]
            if args.apply:
                args_restore.append("--apply")
            return subprocess.run(args_restore, env=env, check=False).returncode
    except (PackageError, restore.RestoreError) as error:
        print(str(error), file=sys.stderr)
    except (KeyError, TypeError, ValueError, OSError, tarfile.TarError):
        print("Pemeriksaan paket privat berhenti", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
