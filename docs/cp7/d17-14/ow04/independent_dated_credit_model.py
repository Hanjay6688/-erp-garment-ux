"""Independent OW04 arithmetic countermodel, never an ERP runtime claim.

EXPECTED.json was written before this executable. Source events and component
amounts use integer cents; dates are synthetic ordered business-day coordinates.
No Supabase connection, journal writer, cash permission or posting is invoked.
"""
from dataclasses import asdict, dataclass
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = json.loads((HERE / "INDEPENDENT_COMPONENT_EXPECTED.json").read_text())


def cents(value):
    amount = Decimal(value)
    assert amount.is_finite() and amount * 100 == (amount * 100).to_integral_value()
    return int(amount * 100)


def money(value):
    return format(Decimal(value) / 100, ".2f")


@dataclass(frozen=True)
class Event:
    source_id: str
    kind: str
    economic: int
    book: int
    amount: int
    reverses: str | None = None

    def __post_init__(self):
        assert self.kind in ("SALE", "FUNDING", "RETURN")
        assert self.book >= self.economic
        assert isinstance(self.amount, int) and self.amount != 0


@dataclass(frozen=True)
class Component:
    economic: int
    book: int
    amount: int


@dataclass(frozen=True)
class Plan:
    components: tuple[Component, ...]
    source_hash: str
    dependencies: frozenset[str]


def ev(source_id, kind, economic, book, amount, reverses=None):
    return Event(source_id, kind, economic, book, cents(amount), reverses)


def source_ar(events, economic, book):
    return sum((1 if x.kind == "SALE" else -1) * x.amount for x in events
               if x.economic <= economic and x.book <= book)


def surplus(events, economic, book):
    return max(0, -source_ar(events, economic, book))


def rectangle(components, economic, book):
    return sum(x.amount for x in components if x.economic <= economic and x.book <= book)


def planner(before, new_return):
    assert new_return.kind == "RETURN" and new_return.amount > 0
    after = before + (new_return,)
    assert len({x.source_id for x in after}) == len(after)
    es = sorted({x.economic for x in after})
    bs = sorted({x.book for x in after})
    delta = {(e, b): surplus(after, e, b) - surplus(before, e, b) for e in es for b in bs}
    components = []
    for ei, e in enumerate(es):
        for bi, b in enumerate(bs):
            def at(i, j):
                return 0 if i < 0 or j < 0 else delta[es[i], bs[j]]
            amount = at(ei, bi) - at(ei - 1, bi) - at(ei, bi - 1) + at(ei - 1, bi - 1)
            if amount:
                assert b >= e, "source book>=economic must imply upper-triangular component support"
                components.append(Component(e, b, amount))
    plan = Plan(tuple(components), sha256(json.dumps([asdict(x) for x in after], sort_keys=True).encode()).hexdigest(),
                frozenset(x.source_id for x in after))
    for e in es:
        for b in bs:
            assert rectangle(plan.components, e, b) == delta[e, b]
            assert delta[e, b] >= 0, "adding a positive return may not reduce pointwise recognition"
    gross = sum(x.amount for x in before if x.kind == "SALE")
    prior_returns = sum(x.amount for x in before if x.kind == "RETURN")
    raw_funding = sum(x.amount for x in before if x.kind == "FUNDING")
    prior_issued = surplus(before, max(es), max(bs))
    effective = raw_funding - prior_issued
    net_before = gross - prior_returns
    assert 0 <= effective <= net_before
    scalar_k = max(0, new_return.amount - (net_before - effective))
    assert sum(x.amount for x in plan.components) == scalar_k
    return plan


def component_rows(plan):
    return [[x.economic, x.book, money(x.amount)] for x in plan.components]


def profile(events, components, basis, cutoff):
    end = max([x.economic for x in events] + [x.book for x in events] + [cutoff])
    e, b = (cutoff, end) if basis == "economic" else (end, cutoff)
    credit = rectangle(components, e, b)
    return [money(source_ar(events, e, b) + credit), money(credit)]


def can_spend(plan, economic, book, amount, already=()):
    assert book >= economic and amount > 0
    all_components = plan.components + tuple(Component(e, b, -a) for e, b, a in already)
    candidate = all_components + (Component(economic, book, -amount),)
    es = {economic, *(x.economic for x in candidate)}
    bs = {book, *(x.book for x in candidate)}
    # Every change breakpoint, including future-dated extinction relative to a
    # backdated spend, must stay nonnegative. The maximum pair is current capacity.
    return all(rectangle(candidate, e, b) >= 0 for e in es for b in bs)


def main():
    results = []
    expected = EXPECTED["cases"]["CROSSING_PAYMENT_BOOK_ORDER"]
    before = (ev("sale:1", "SALE", 17, 17, "1000"),
              ev("payment:A", "FUNDING", 18, 21, "900"),
              ev("payment:B", "FUNDING", 19, 19, "100"))
    returned = ev("return:new", "RETURN", 20, 20, "200")
    plan = planner(before, returned)
    assert component_rows(plan) == expected["components"]
    events = before + (returned,)
    assert profile(events, plan.components, "economic", 20) == expected["economic20_AR_credit"]
    assert profile(events, plan.components, "book", 20) == expected["book20_AR_credit"]
    assert profile(events, plan.components, "book", 21) == expected["current_AR_credit"]
    wrong_fifo = (Component(20, 21, cents("100")), Component(20, 20, cents("100")))
    assert profile(events, wrong_fifo, "book", 20) == expected["wrong_per_payment_fifo_book20_AR_credit"]
    assert profile(events, wrong_fifo, "book", 20) != expected["book20_AR_credit"]
    results.append(dict(case="CROSSING_PAYMENT_BOOK_ORDER", components=component_rows(plan),
                        source_hash=plan.source_hash, status="PURE_MODEL_PASS"))

    expected = EXPECTED["cases"]["SIGNED_WITHOUT_SOURCE_REVERSAL"]
    before = (ev("sale:2", "SALE", 0, 0, "1000"), ev("return:old", "RETURN", 0, 0, "600"),
              ev("funding:A", "FUNDING", 1, 3, "600"), ev("funding:B", "FUNDING", 2, 2, "400"))
    plan = planner(before, ev("return:new", "RETURN", 0, 0, "200"))
    assert component_rows(plan) == expected["components"]
    assert money(sum(x.amount for x in plan.components)) == expected["current_new_credit"]
    assert money(sum(x.amount for x in plan.components if x.amount > 0)) == expected["positive_component_sum_is_not_current_entitlement"]
    for pair, amount in expected["joint_new_credit"].items():
        assert money(rectangle(plan.components, *map(int, pair.split(",")))) == amount
    assert money(sum(x.amount for x in plan.components if x.economic <= 1)) == expected["new_credit_economic1"]
    assert money(sum(x.amount for x in plan.components if x.book <= 2)) == expected["new_credit_book2"]
    assert not can_spend(plan, 1, 2, cents("200"))
    assert can_spend(plan, 1, 3, cents("200"))
    assert not can_spend(plan, 2, 2, cents("200"), already=((1, 3, cents("200")),))
    results.append(dict(case="SIGNED_WITHOUT_SOURCE_REVERSAL", components=component_rows(plan),
                        joint_spend_rejected=True, valid_spend_allowed=True, crossing_double_spend_rejected=True,
                        source_hash=plan.source_hash, status="PURE_MODEL_PASS"))

    expected = EXPECTED["cases"]["ZERO_CURRENT_CREDIT_WITH_HISTORICAL_RECOGNITION"]
    before = (ev("sale:3", "SALE", 18, 18, "1000"), ev("payment:3", "FUNDING", 18, 18, "1000"),
              ev("payment:3:reverse", "FUNDING", 20, 20, "-1000", "payment:3"))
    returned = ev("return:3", "RETURN", 19, 19, "200")
    plan = planner(before, returned)
    assert component_rows(plan) == expected["components"]
    assert money(sum(x.amount for x in plan.components)) == expected["current_new_credit"]
    for basis in ("economic", "book"):
        for day in (19, 20):
            assert profile(before + (returned,), plan.components, basis, day) == expected[f"{basis}{day}_AR_credit"]
    assert not can_spend(plan, 19, 19, cents("200"))
    results.append(dict(case="ZERO_CURRENT_CREDIT_WITH_HISTORICAL_RECOGNITION", components=component_rows(plan),
                        nonempty_plan_with_current_zero=True, extinct_historical_spend_rejected=True,
                        source_hash=plan.source_hash, status="PURE_MODEL_PASS"))

    expected = EXPECTED["cases"]["RETURN_SUPPORT_DEPENDENCY"]
    base = (ev("sale:4", "SALE", 18, 18, "1000"), ev("payment:4", "FUNDING", 18, 18, "900"))
    ra = ev("return:A", "RETURN", 19, 19, "200")
    rb = ev("return:B", "RETURN", 20, 20, "100")
    pa, pb = planner(base, ra), planner(base + (ra,), rb)
    assert money(sum(x.amount for x in pa.components)) == expected["issueA"]
    assert money(sum(x.amount for x in pb.components)) == expected["issueB"]
    correct_without_a = surplus(base + (rb,), 20, 20)
    assert money(correct_without_a) == expected["after_undo_A_correct_total_issuance"]
    assert sum(x.amount for x in pb.components) - correct_without_a == cents("100")
    assert "return:A" in pb.dependencies
    results.append(dict(case="RETURN_SUPPORT_DEPENDENCY", correct_issuance_after_undo_A=money(correct_without_a),
                        retained_issueB_unsupported=money(sum(x.amount for x in pb.components)),
                        return_A_in_immutable_support=True, status="PURE_MODEL_COUNTER_CONFIRMED"))
    print(json.dumps(dict(kind="INDEPENDENT_PURE_INTEGER_CENT_DATED_CREDIT_MODEL_NOT_ERP",
                          expected_sha256=sha256((HERE / "INDEPENDENT_COMPONENT_EXPECTED.json").read_bytes()).hexdigest(),
                          source_pin=EXPECTED["source_pin"], cases=results,
                          native_executed=False, journals_posted=False, feature_complete=False), indent=2))


if __name__ == "__main__":
    main()
