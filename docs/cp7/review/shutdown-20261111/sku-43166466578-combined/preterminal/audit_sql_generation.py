"""Offline PostgreSQL grammar check for the candidate and its SQL inputs."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

import pglast
from pglast import ast, parse_plpgsql, parse_sql, split


SINGLE_DOLLAR_BODY = re.compile(r"\bas\s+\$(?!\$|[A-Za-z_][A-Za-z_0-9]*\$)(?=\s|$)", re.IGNORECASE)


def check(raw):
    sql = raw.decode()
    result = dict(bytes=len(raw), sha256=sha256(raw).hexdigest(), statements=0,
                  plpgsql_bodies=0, sql_bodies=0, body_errors=[],
                  single_dollar_body_lines=[sql.count("\n", 0, m.start()) + 1
                                            for m in SINGLE_DOLLAR_BODY.finditer(sql)])
    try:
        statements = parse_sql(sql)
    except pglast.parser.ParseError as error:
        result["sql_error"] = str(error)
        result["psql_lines"] = [i for i, line in enumerate(sql.splitlines(), 1)
                                if line.lstrip().startswith("\\")]
        return result

    result["statements"] = len(statements)
    for entry, statement in zip(statements, split(sql), strict=True):
        node = entry.stmt
        if isinstance(node, ast.DoStmt):
            name = "DO block"
            definitions = node.args
            default_language = "plpgsql"
        elif isinstance(node, ast.CreateFunctionStmt):
            name = ".".join(part.sval for part in node.funcname)
            definitions = node.options
            default_language = ""
        else:
            continue
        options = {option.defname: option.arg for option in definitions}
        language = getattr(options.get("language"), "sval", default_language)
        try:
            if language == "plpgsql":
                result["plpgsql_bodies"] += 1
                parse_plpgsql(statement)
            elif language == "sql" and options.get("as"):
                result["sql_bodies"] += 1
                parse_sql(options["as"][0].sval)
        except pglast.parser.ParseError as error:
            result["body_errors"].append(dict(name=name, language=language, error=str(error)))
    return result


def audit(root):
    command = ["git", "-C", str(root), "ls-files", "-z", "--", "scripts", "supabase", ".github"]
    paths = [Path(item.decode()) for item in subprocess.check_output(command).split(b"\0") if item.endswith(b".sql")]
    return {str(path): check((root / path).read_bytes()) for path in paths}


def summarize(results):
    counts = Counter()
    diagnostics = {}
    for name, result in results.items():
        counts.update(files=1, statements=result["statements"],
                      plpgsql_bodies=result["plpgsql_bodies"], sql_bodies=result["sql_bodies"])
        for key in ("sql_error", "body_errors", "single_dollar_body_lines"):
            if result.get(key):
                counts[key] += 1
        if any(result.get(key) for key in ("sql_error", "body_errors", "single_dollar_body_lines")):
            diagnostics[name] = result
    return dict(counts=counts, diagnostics=diagnostics)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    source = arguments.source.resolve()
    files = audit(source)
    receipt = dict(source=subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip(),
                   source_tree=subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD^{tree}"],
                                                       text=True).strip(),
                   parser=pglast.__version__, **summarize(files), files=files,
                   actual_SQL_executed=0, actual_ERP_cases=0)
    with arguments.output.open("x") as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps(receipt["counts"], sort_keys=True))
