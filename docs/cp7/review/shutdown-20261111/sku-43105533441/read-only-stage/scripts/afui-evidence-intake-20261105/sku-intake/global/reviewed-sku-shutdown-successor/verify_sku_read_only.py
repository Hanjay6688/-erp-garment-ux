"""Verify one reviewed SKU Original with the retained read-only GitHub transport."""

import argparse
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory

from reviewed_sku_source import PARENT, add_cli, from_cli, git, verify_source
from verify_terminal_sku import BRANCH, CATALOGUE, OUTCOMES, WORKFLOW, fields, require, strict, terminal_archive_name, verify

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "read-only"))
from retain import api, copy_stream, metadata


REPOSITORY = "Hanjay6688/-erp-garment-ux"
JOB_NAME = "Actual Mandor parent, full money and automatic Native25; complete restoration"


def pins(binding):
    require(type(binding) is dict and set(binding) == {"artifact_id", "bytes", "sha256", "conclusion"}
            and type(binding["artifact_id"]) is int and binding["artifact_id"] > 0
            and type(binding["bytes"]) is int and binding["bytes"] > 0
            and type(binding["sha256"]) is str and re.fullmatch("[a-f0-9]{64}", binding["sha256"])
            and binding["conclusion"] in OUTCOMES, "SKU_EXACT_REVIEWED_ARCHIVE_PINS_REQUIRED")
    return {key: binding[key] for key in ("bytes", "sha256")}


def check_metadata(binding, reviewed, run, job, artifact):
    expected = pins(binding)
    head, run_id, job_id = (reviewed[k] for k in ("head", "run_id", "job_id"))
    fields(run, dict(id=run_id, head_sha=head, head_branch=BRANCH, path=WORKFLOW, event="push",
                     status="completed", run_attempt=1, conclusion=binding["conclusion"]),
           "SKU_READ_ONLY_EXACT_TERMINAL_RUN")
    fields(job, dict(id=job_id, run_id=run_id, head_sha=head, status="completed", run_attempt=1,
                     conclusion=binding["conclusion"], name=JOB_NAME), "SKU_READ_ONLY_EXACT_TERMINAL_JOB")
    fields(artifact, dict(id=binding["artifact_id"], name=terminal_archive_name(run), expired=False,
                          size_in_bytes=expected["bytes"], digest="sha256:" + expected["sha256"]),
           "SKU_READ_ONLY_EXACT_TERMINAL_ORIGINAL")
    fields(artifact["workflow_run"], dict(id=run_id, head_sha=head, head_branch=BRANCH),
           "SKU_READ_ONLY_SAME_RUN_ORIGINAL")
    return expected


def bind(run, job, artifacts, reviewed):
    name = terminal_archive_name(run)
    selected = [a for a in artifacts["artifacts"] if a["name"] == name]
    require(len(selected) == 1, "SKU_READ_ONLY_UNIQUE_TERMINAL_ORIGINAL_REQUIRED")
    artifact = selected[0]
    require(type(artifact["digest"]) is str and artifact["digest"].startswith("sha256:"),
            "SKU_READ_ONLY_GITHUB_DIGEST_REQUIRED")
    binding = dict(artifact_id=artifact["id"], bytes=artifact["size_in_bytes"],
                   sha256=artifact["digest"].removeprefix("sha256:"), conclusion=run["conclusion"])
    check_metadata(binding, reviewed, run, job, artifact)
    return binding


def stream(binding, reviewed, repo, mandor, out):
    pins(binding)
    head, tree = reviewed["head"], reviewed["tree"]
    require(git(repo, "rev-parse", "HEAD", "HEAD^{tree}").decode().splitlines() == [head, tree]
            and git(repo, "show", head + ":" + PARENT) == mandor, "SKU_READ_ONLY_REVIEWED_SOURCE_CHANGED")
    verify_source(repo, head, reviewed, mandor)
    aid = binding["artifact_id"]
    route = f"/repos/{REPOSITORY}/actions/"
    with TemporaryDirectory(prefix="sku-reviewed-original-") as temp:
        d = Path(temp)
        run = metadata(route + f"runs/{reviewed['run_id']}", d / "run.json")
        job = metadata(route + f"jobs/{reviewed['job_id']}", d / "job.json")
        artifact = metadata(route + f"artifacts/{aid}", d / "artifact.json")
        expected = check_metadata(binding, reviewed, run, job, artifact)
        original = d / "canonical.zip"
        with api(route + f"artifacts/{aid}/zip") as source, original.open("xb") as target:
            copied = copy_stream(source, target, expected["bytes"])
        require(copied == expected, "SKU_READ_ONLY_ORIGINAL_BYTES_OR_DIGEST_CHANGED")
        receipt, root, catalogue = verify(original, artifact, run, job, repo, mandor, reviewed)
        out.mkdir()
        (out / "TERMINAL_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        if root is not None:
            (out / "SKU25_PARENT_ROOT_ACTUAL_INTAKE.json").write_text(json.dumps(root, indent=2) + "\n")
            (out / CATALOGUE).write_bytes(catalogue)
        for name in ("run.json", "job.json", "artifact.json"):
            (out / name).write_bytes((d / name).read_bytes())
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, paths in (("bind", ("run", "job", "artifacts", "binding")),
                        ("verify", ("binding", "repo", "mandor-root", "output"))):
        command = sub.add_parser(name)
        add_cli(command)
        for path in paths:
            command.add_argument("--" + path, type=Path, required=True)
    args = parser.parse_args()
    reviewed = from_cli(args)
    if args.command == "bind":
        values = (strict(p.read_bytes()) for p in (args.run, args.job, args.artifacts))
        value = bind(*values, reviewed)
        with args.binding.open("x") as out:
            out.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
    else:
        result = stream(strict(args.binding.read_bytes()), reviewed, args.repo.resolve(),
                        args.mandor_root.read_bytes(), args.output)
        print(json.dumps({key: result[key] for key in ("conclusion", "actual_case_credit",
                         "actual_outer_restore", "actual_worker_reaped", "all_member_crc_verified")}))


if __name__ == "__main__":
    main()
