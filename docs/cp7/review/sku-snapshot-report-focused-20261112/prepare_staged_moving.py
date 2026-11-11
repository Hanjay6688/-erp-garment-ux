"""Select the single new MA scenario in the existing B harness."""
import argparse
from hashlib import sha256
from pathlib import Path


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError(f'Expected one retained marker: {before}')
    return text.replace(before, after, 1)


def prepare(lab, prior, case):
    target = lab / 'ma-two-stage/focused.mjs'
    route = """ const { checkRoundingCatalogue } = await import(process.env.CP7_ROUNDING_CATALOGUE_PROBE);
 await checkRoundingCatalogue(db, input);
"""
    target.write_text(replace_once(target.read_text(), route, ''))
    raw = prior.read_bytes()
    source = raw.decode()
    start = "  await run('B_LATE_COST_AFTER_PARTIAL_SALE'"
    end = '  db.report.cost_document_id = costDocument;'
    assert source.count(start) == source.count(end) == 1
    source = source[:source.index(start)] + case.read_text() + '\n' + source[source.index(end):]
    source = replace_once(source, '  async function returnOne() {\n    const returned = id(88001);',
                          '  async function returnOne(sequence, allocation, lot) {\n    const returned = id(88000 + sequence);')
    source = replace_once(source, "{ id: id(89001), return_id: returned, sale_stock_allocation_id: x.saleA,",
                          "{ id: id(89000 + sequence), return_id: returned, sale_stock_allocation_id: allocation,")
    source = replace_once(source, "product_id: x.target, lot_id: x.root50, location_id: x.location, quality_grade: 'GRADE_A',",
                          "product_id: x.target, lot_id: lot, location_id: x.location, quality_grade: 'GRADE_A',")
    source = replace_once(source, '  db.report.engine = engine;',
                          "  db.report.active_candidate = 'd08032a28b9f00d0ee70a6f98c6b7d0f5b770c4a';\n  db.report.engine = engine;")
    output = lab / 'handoff/focused_probe.mjs'
    output.write_text(source)
    print(f'Original B harness {sha256(raw).hexdigest()}, new harness {sha256(output.read_bytes()).hexdigest()}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('lab', 'prior', 'case'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    prepare(*(p.resolve() for p in vars(args).values()))
