"""Verify that two overlapping descriptions cannot create a second independent root."""

import argparse
import json
from pathlib import Path
import sys


def interval(first, last):
    return {"source_id": "fixed", "start_line": first, "end_line": last, "use": "confirmation"}


def put_basis(item, span):
    fact = next(fact for fact in item["facts"] if fact["key"] == "implementation_action")
    fact["anchors"] = [span]


def results(run, node, edge, proof):
    def evaluate(left, right, left_proof, right_proof):
        put_basis(left, left_proof)
        put_basis(right, right_proof)
        relation = edge("independent_of", left["id"], right["id"], 2, 4)
        relation["evidence_refs"] = [left_proof, right_proof]
        outcome = run(left, right, edges=(relation,))
        return {"roots": outcome["independent_count"], "independent_edge": outcome["relations"][0]["supported"]}

    keys = (*proof, "established_other_defect")
    rows = {}
    for report_end in (2, 3):
        left = node("first", "root_action", 2, keys)
        right = node("restated", "independent_action", 2, keys)
        left["observed_behavior"] = right["observed_behavior"] = "the single actual old action on line 2"
        right["source_location"]["end_line"] = report_end
        rows[f"shared_operation_window_{report_end}"] = evaluate(left, right, interval(1, 2), interval(2, 3))

    left = node("first", "root_action", 2, keys)
    right = node("separate", "independent_action", 4, keys)
    # Both source_location fields point to the same report paragraph. The
    # decisive operation evidence binds different operations within it.
    for item in (left, right):
        item["source_location"] = {"source_id": "fixed", "start_line": 2, "end_line": 4}
    rows["two_distinct_operations"] = evaluate(left, right, interval(2, 2), interval(4, 4))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--baseline", action="store_true", help="require the observed cdf0488 overlap bug")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.checkout.resolve() / "classification"))
    from test_reliability_v04 import run, node, edge, PROOF

    actual = results(run, node, edge, PROOF)
    same = {"roots": 2 if args.baseline else 1, "independent_edge": args.baseline}
    expected = {"shared_operation_window_2": same, "shared_operation_window_3": same,
                "two_distinct_operations": {"roots": 2, "independent_edge": True}}
    record = {"scope": "synthetic_shared_location_regression", "actual": actual, "passed": actual == expected}
    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
    print(payload, end="")
    if actual != expected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
