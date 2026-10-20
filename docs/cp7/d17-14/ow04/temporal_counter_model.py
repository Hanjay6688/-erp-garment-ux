"""Standalone dated-ledger oracle; no ERP/Native/database execution or planner.

Literal expected cutoffs below were declared before execution from the source
assessment. The narrative's reopened900+100 case is distinct from this
model's fully-funded1000 reopened variant; neither is an ERP runtime test.
Components below are explicit fixture inputs, not a proposed planning algorithm.
Run with Python 3.10+: python docs/cp7/d17-14/ow04/temporal_counter_model.py
"""

from dataclasses import dataclass
from decimal import Decimal
import json


@dataclass(frozen=True)
class Journal:
    name: str
    economic_day: int
    book_day: int
    lines: tuple[tuple[str, Decimal], ...]


def entry(name, economic_day, book_day, debit, credit, amount):
    amount = Decimal(amount)
    assert amount > 0
    return Journal(name, economic_day, book_day, ((debit, amount), (credit, -amount)))


def balance(journals, basis, cutoff):
    assert basis in ("economic_day", "book_day")
    result = {"AR": Decimal(0), "CUSTOMER_CREDIT": Decimal(0)}
    for journal in journals:
        assert sum(value for _, value in journal.lines) == 0
        if getattr(journal, basis) <= cutoff:
            for account, value in journal.lines:
                if account in result:
                    result[account] += value
    return (str(result["AR"]), str(-result["CUSTOMER_CREDIT"]))


def fixture(case, closed=False):
    journals = [entry("sale", 18, 18, "AR", "REVENUE", "1000")]
    if case == "A":
        journals.append(entry("payment_late", 20, 20, "CASH", "AR", "1000"))
        components = [entry("credit_late", 20, 20, "AR", "CUSTOMER_CREDIT", "200")]
    else:
        assert case == "B"
        journals.extend((entry("payment_early", 18, 18, "CASH", "AR", "900"),
                         entry("payment_late", 20, 20, "CASH", "AR", "100")))
        components = [entry("credit_early", 19, 20 if closed else 19, "AR", "CUSTOMER_CREDIT", "100"),
                      entry("credit_late", 20, 20, "AR", "CUSTOMER_CREDIT", "100")]
    journals.append(entry("return", 19, 20 if closed else 19, "REVENUE", "AR", "200"))
    return tuple(journals), tuple(components)


def main():
    # Literal expected balances, declared before execution. No solver involved.
    goldens = {
        ("A", False): {"economic_day": (("800", "0"), ("0", "200")),
                       "book_day": (("800", "0"), ("0", "200"))},
        ("B", False): {"economic_day": (("0", "100"), ("0", "200")),
                       "book_day": (("0", "100"), ("0", "200"))},
        ("A", True): {"economic_day": (("800", "0"), ("0", "200")),
                      "book_day": (("1000", "0"), ("0", "200"))},
        ("B", True): {"economic_day": (("0", "100"), ("0", "200")),
                      "book_day": (("100", "0"), ("0", "200"))},
    }
    outcomes = []
    for (case, closed), expected in goldens.items():
        source, components = fixture(case, closed)
        assert sum(-journal.lines[1][1] for journal in components) == Decimal("200")
        observations = {}
        for basis, expected_cutoffs in expected.items():
            actual = tuple(balance(source + components, basis, day) for day in (19, 20))
            assert actual == expected_cutoffs, (case, closed, basis, actual, expected_cutoffs)
            observations[basis] = dict(zip(("19", "20"), actual))
        wrong = source + (entry("wrong_all_credit_at_return", 19, 20 if closed else 19,
                                "AR", "CUSTOMER_CREDIT", "200"),)
        wrong_19 = balance(wrong, "economic_day", 19)
        assert wrong_19 != expected["economic_day"][0]
        outcomes.append(dict(case=case + ("_CLOSED19" if closed else "_OPEN"),
                             status="MODEL_COUNTER_CONFIRMED_NOT_NATIVE",
                             derived_component_fixture=observations,
                             wrong_single_date_economic19_AR_credit=wrong_19))

    # A payment physically on18 was booked on20 while19 was closed; the
    # owner then explicitly reopened through17 before entering the return.
    source = (entry("sale", 18, 18, "AR", "REVENUE", "1000"),
              entry("payment_late_book", 18, 20, "CASH", "AR", "1000"),
              entry("return_after_explicit_reopen", 19, 19, "REVENUE", "AR", "200"))
    component = entry("source_derived_pair", 19, 20, "AR", "CUSTOMER_CREDIT", "200")
    expected = {"economic_day": (("0", "200"), ("0", "200")),
                "book_day": (("800", "0"), ("0", "200"))}
    for basis, expected_cutoffs in expected.items():
        assert tuple(balance(source + (component,), basis, d) for d in (19, 20)) == expected_cutoffs
    wrong19 = source + (entry("ordinary_poster19_after_reopen", 19, 19, "AR", "CUSTOMER_CREDIT", "200"),)
    wrong20 = source + (entry("ordinary_poster20_after_reopen", 20, 20, "AR", "CUSTOMER_CREDIT", "200"),)
    assert balance(wrong19, "book_day", 19) == ("1000", "200")
    assert balance(wrong20, "economic_day", 19) == ("-200", "0")
    outcomes.append(dict(case="REOPENED_PAIR_REQUIRED", status="MODEL_COUNTER_CONFIRMED_NOT_NATIVE",
                         derived_component_fixture=expected,
                         wrong_ordinary19_book19_AR_credit=balance(wrong19, "book_day", 19),
                         wrong_ordinary20_economic19_AR_credit=balance(wrong20, "economic_day", 19)))
    print(json.dumps(dict(kind="STANDALONE_DECIMAL_DATED_LEDGER_MODEL_NOT_ERP_RUNTIME",
                          source_candidate="4e3c98b3ce04427c65c7bc7c1b21ec3bdacfea71",
                          cases=outcomes, observed_model_case_count=len(outcomes),
                          planner_implemented=False, native_executed=False,
                          feature_complete=False, audit_complete=False, production_go=False), indent=2))


if __name__ == "__main__":
    main()
