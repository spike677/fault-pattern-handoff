"""Check Work-adjudicated mechanism boundaries through the production graph entry."""

import argparse
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
FIELDS = ("status", "pattern_id", "parent_id", "outside_reason")


def observe(graph, fixture):
    case_id = fixture["id"]
    text = "\n".join(fixture["proof_text"])
    sources = [source(case_id, "fixed", "fixture-v1", text)]
    evidence_id = "fixed"
    if fixture.get("other_source"):
        evidence_id = "other"
        sources.append(source(case_id, "other", "fixture-v2",
                              "This separate snapshot proves the new numeric contract, members, and actual consumption."))
    span = {"source_id": evidence_id, "start_line": 1, "end_line": len(sources[-1]["text"].splitlines())}
    facts = fixture["facts"]
    node_type = fixture.get("node_type", "root_action")
    node = {
        "id": "action", "node_type": node_type, "description": case_id,
        "scope": {"source_id": "fixed", "claim": "reported", "build": None, "call_id": None},
        "source_location": {"source_id": "fixed", "start_line": 2, "end_line": 2},
        "expected_behavior": fixture["proof_text"][0],
        "observed_behavior": fixture["proof_text"][1],
        "violated_relation": text,
        "facts": [{"key": key, "value": True, "claim_state": fixture.get("state", "confirmed_report"),
                   "anchors": [{**span, "use": "confirmation"}], "explanation": sources[-1]["text"]}
                  for key in facts],
    }
    material = {"case_id": case_id, "sources": sources}
    response = {"case_id": case_id, "operator": case_id, "roles": [], "readback": "",
                "nodes": [node], "relations": []}
    result, = graph.classify_package({"cases": [material]}, {"cases": [response]})["cases"]
    action, = result["nodes"]
    decision = action["verdict"]
    return {**{name: decision[name] for name in FIELDS if name in decision},
            "root_count": result["independent_count"]}


def source(case, source_id, version, text):
    return {"id": source_id, "kind": "report", "version": version,
            "path": f"fixtures/{case}/{source_id}", "text": text}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--baseline", action="store_true", help="require the measured baseline gaps")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.checkout.resolve() / "classification"))
    from reliability_v04 import graph, reader

    schema = reader.schema()
    keys = set(schema["$defs"]["fact"]["properties"]["key"]["enum"])
    fixtures = json.loads((HERE / "parent_leaf_regression.json").read_bytes())["fixtures"]
    results = []
    for fixture in fixtures:
        # Direct graph replay exposes a decision bug even when an older reader
        # schema would reject the same fact before ingestion.
        actual = observe(graph, fixture)
        expected = fixture["expected"]
        allowed = fixture.get("baseline_gap", expected) if args.baseline else expected
        schema_missing = set(fixture["facts"]) - keys
        older_schema = {"numeric_evaluation_violation"} if args.baseline else set()
        results.append({"id": fixture["id"], "expected": expected, "actual": actual,
                        "schema_missing": sorted(schema_missing), "target_met": actual == expected,
                        "check_passed": actual == allowed and schema_missing <= older_schema})
    record = {"scope": "synthetic_parent_leaf_regression",
              "mode": "baseline" if args.baseline else "candidate",
              "total": len(results), "targets_met": sum(item["target_met"] for item in results),
              "checks_passed": sum(item["check_passed"] for item in results), "results": results}
    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
    print(payload, end="")
    if not all(item["check_passed"] for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
