"""Check the actual compiled SQL emitted by the ERP source builders."""

from argparse import ArgumentParser
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import subprocess
import sys

from audit_sql_generation import check, summarize


def module(name, path):
    spec = spec_from_file_location(name, path)
    value = module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def candidate_sql(source, frozen_auto, frozen_money, fixtures, global_source):
    area = Path("scripts/current-sku-automatic-composite-preparation")
    sys.path[:0] = [str(source / "scripts"), str(frozen_money / "scripts"), str(frozen_auto / "scripts")]
    from cp7_sku_cost_components import catalog_additions, financial_delta, prepared_product
    from cp7_sku_pending_accounting import derivation
    from cp7_frozen_analysis_v2 import render

    adapters = {name: module(name, source / area / (name + ".py"))
                for name in ("context_timezone", "cost_source_timezone", "module_scope", "non_po_rounding")}
    rounding = adapters["non_po_rounding"]
    old_native = (fixtures / "CP7_SKU_MANAGED_RECOVERY_NATIVE27.json").read_bytes()
    assert (len(old_native), sha256(old_native).hexdigest()) == rounding.ORIGINAL_PIN
    catalog = json.loads(old_native)["committed"][rounding.ORIGINAL_CASE]["Native_to_copy_handoff"]["raw_current_catalog"]
    originals = {signature: catalog["functions"][signature][0]
                 for signature in prepared_product.parent_original_signatures()}

    def money_base(before, prior):
        product = prepared_product.derive(before, prior["originals"])
        profile, tables = catalog_additions.expected(product)
        product, profile = rounding.correct(product, profile)
        return product, profile, tables

    scoped_money = adapters["module_scope"].bind_money_preparation(money_base, financial_delta)
    money, _, _ = adapters["cost_source_timezone"].bind(scoped_money)(catalog, dict(originals=originals))
    current = money["ddl"].encode()
    assert len(current) == 86374 and sha256(current).hexdigest() == (
        "1d2894bd4e298e0af332119bface60b15b4b4412ab2c00675a9958fcdc64ee16")
    yield "SKU money final derived DDL", current

    accounting = derivation.derive()
    scope = accounting["definitions"]["cp7_sku_conversion.cost_scope_value_v3(uuid,uuid,text)"]
    assert accounting["ddl"].count(scope) == 1
    context = (frozen_auto / "scripts/cp7_sku_automatic_pending/context.sql").read_text()
    original = dict(ddl=accounting["ddl"].replace(scope, "", 1) + "\n" + context)
    profile = json.loads((fixtures / "AUTOMATIC_PROFILE.json").read_bytes())
    current, _ = adapters["context_timezone"].adapt(original, profile)
    yield "SKU automatic final derived DDL", current["ddl"].encode()

    previous = {}
    exec(compile(git(source, "show", "3f2a7748:" + str(area / "context_timezone.py")),
                 "3f2a original failure source", "exec"), previous)
    failed, _ = previous["adapt"](original, profile)
    observed = check(failed["ddl"].encode())
    assert 'syntax error at or near "$"' in observed["sql_error"] and len(observed["single_dollar_body_lines"]) == 2

    for family in ("aw", "ax"):
        builder = module("cp6_" + family, source / "scripts" / ("cp6_" + family + "_build.py"))
        sql = builder.build().encode()
        assert sql == builder.OUT.read_bytes(), family + " generated source drift"
        yield "CP6 " + family.upper() + " actual generated installer", sql

    capsule = render.render().encode()
    assert capsule == (source / "scripts/cp7_frozen_analysis_v2/capsule.sql").read_bytes()
    yield "CP7 frozen analysis rendered capsule", capsule

    wrapper = (source / "scripts/current-mandor-afui-preparation/review_adapter/FOCUSED_INSTALLER.sql").read_bytes()
    assert sha256(wrapper).hexdigest() == "d85ed5728c2a5b5269d12988994a4c5388dc7d60d9e41fd6bc52cd980528ece4"
    lines = wrapper.decode().splitlines()
    assert lines[:2] == ["\\set ON_ERROR_STOP on", "begin;"] and lines[-1] == "commit;"
    yield "Mandor admitted owning installer body", ("\n".join(lines[2:-1]) + "\n").encode()

    snapshot = (source / "scripts/cp7-src/snapshot/capture_probe.sql").read_bytes()
    assert snapshot.count(b"%s") == 1
    yield "P02 diagnostic bound snapshot query", snapshot.replace(b"%s", b"$1", 1)

    sys.path.insert(0, str(global_source / "scripts"))
    from cp7_global_nonpo_envelope import composition, native_hooks
    plan = json.loads((global_source / "scripts/cp7_global_nonpo_envelope/INSTALL_PLAN.json").read_bytes())
    statements = composition.sql_sources()
    assert plan["source_sql"] == {name: composition.pin(sql.encode()) for name, sql in statements.items()}
    for name, sql in statements.items():
        yield "Global " + name, sql.encode()
    definitions, _ = native_hooks.derive(native_hooks.originals())
    assert plan["native_adapter_sources"] == {name: composition.pin(sql.encode()) for name, sql in definitions.items()}
    for name, sql in definitions.items():
        yield "Global adapted " + name, sql.encode()


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    for argument in ("source", "frozen_auto", "frozen_money", "fixtures", "global_source", "output"):
        parser.add_argument(argument, type=Path)
    arguments = parser.parse_args()
    source, global_source = arguments.source.resolve(), arguments.global_source.resolve()
    files = {name: check(raw) for name, raw in candidate_sql(
        source, arguments.frozen_auto.resolve(), arguments.frozen_money.resolve(),
        arguments.fixtures.resolve(), global_source)}
    receipt = dict(source=git(source, "rev-parse", "HEAD").decode().strip(),
                   tree=git(source, "rev-parse", "HEAD^{tree}").decode().strip(),
                   global_base=git(global_source, "rev-parse", "HEAD").decode().strip(),
                   global_staged_delta_sha256=sha256(git(global_source, "diff", "--cached", "--raw", "-z")).hexdigest(),
                   **summarize(files), files=files, previous_sku_syntax_error_reproduced=True,
                   actual_SQL_executed=0, actual_ERP_cases=0)
    with arguments.output.open("x") as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps(dict(counts=receipt["counts"], diagnostics=receipt["diagnostics"]), sort_keys=True))
