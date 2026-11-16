"""Experimental numeric decisions layered over the frozen v0.3 classifier."""

import argparse
import json
from pathlib import Path
import sys

CLASSIFICATION = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CLASSIFICATION))
from classify import FACT_PROTOCOL, by_id, classify_package, collect_facts


NAMESPACE = "MECH-v0.4-candidate"
COMMON_FACTS = {
    "applicable_contract",
    "implementation_action",
    "contribution_set_preserved",
    "distorted_value_consumed",
}
PATTERNS = {
    "NUM-01": {
        "loop_carried_narrow_state",
        "wider_state_preserves_same_updates",
    },
    "NUM-02": {
        "variance_from_raw_moment_difference",
        "centered_variance_survives_at_same_precision",
        "variance_consumed_by_normalization",
    },
}
SQUARE_OVERFLOW = "pre_reduction_square_overflow"
DECISIVE_FACTS = COMMON_FACTS.union(*PATTERNS.values(), {SQUARE_OVERFLOW})


def candidate_action(action, sources, legacy):
    result = {
        "action_id": legacy["id"],
        "role": legacy["role"],
        "count_as_independent": legacy["count_as_independent"],
        "legacy_status": legacy["status"],
        "legacy_pattern_id": legacy.get("pattern_id"),
        "legacy_outside_reason": legacy.get("outside_reason"),
    }
    if legacy.get("outside_reason") != "outside_catalog":
        status = "insufficient" if legacy["status"] == "insufficient" else "legacy_verdict"
        return {**result, "status": status}

    _, positive, _, scoped, issues, conflicts = collect_facts(
        action, sources, action["scope"], DECISIVE_FACTS,
    )
    supported = positive & scoped
    missing = {pattern: sorted((COMMON_FACTS | required) - supported)
               for pattern, required in PATTERNS.items()}
    matches = [pattern for pattern, unanswered in missing.items() if not unanswered]
    square_overflow = (COMMON_FACTS | {SQUARE_OVERFLOW}) <= supported
    contested = sorted(DECISIVE_FACTS.intersection(conflicts))
    if contested or len(matches) > 1 or (matches and square_overflow):
        return {**result, "status": "insufficient", "reason": "conflicting_first_wrong_state",
                "conflicting_facts": contested}
    if matches:
        pattern, = matches
        return {**result, "status": "candidate", "pattern_id": pattern,
                "pattern_ref": f"{NAMESPACE}:{pattern}"}
    if square_overflow:
        return {**result, "status": "outside", "reason": SQUARE_OVERFLOW}
    return {**result, "status": "insufficient", "missing": missing,
            "issues": [issue for issue in issues if issue.get("fact") in DECISIVE_FACTS]}


def classify_candidates(material, facts, catalog):
    legacy_cases = classify_package(material, facts, catalog)
    cases = by_id(material["cases"], "material cases", "case_id")
    packets = by_id(facts, "case fact packets", "case_id")
    decisions = []
    for legacy in legacy_cases:
        case_id = legacy["case_id"]
        packet = packets[case_id]
        if packet.get("fact_protocol") != FACT_PROTOCOL:
            raise ValueError("Numeric candidates require evidence-bound facts")
        sources = by_id(cases[case_id]["sources"], "case sources")
        actions = by_id(packet["actions"], "packet actions")
        decisions.append({
            "case_id": case_id,
            "actions": [candidate_action(actions[row["id"]], sources, row)
                        for row in legacy["actions"]],
        })
    return {"namespace": NAMESPACE, "formal_admission": False, "cases": decisions}


def load(path):
    return json.loads(path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("material", type=Path)
    parser.add_argument("facts", type=Path)
    args = parser.parse_args()
    results = classify_candidates(load(args.material), load(args.facts), load(CLASSIFICATION / "catalog.json"))
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
