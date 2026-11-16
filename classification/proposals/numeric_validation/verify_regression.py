"""Recompute the numeric candidate decisions and their development score."""

from collections import Counter
import json
from pathlib import Path

from classify_candidates import CLASSIFICATION, classify_candidates, load
from proposals.v041_review.verify_candidate_review import recompute_boundaries


HERE = Path(__file__).resolve().parent
REGRESSION = HERE / "regression"
SCORE_FIELDS = (
    "status", "pattern_id", "reason", "role", "count_as_independent",
    "legacy_status", "legacy_pattern_id", "legacy_outside_reason",
)


def compare(results, expected):
    def signatures(actions):
        return Counter(tuple(action.get(key) for key in SCORE_FIELDS) for action in actions)

    actual = {case["case_id"]: case["actions"] for case in results["cases"]}
    if actual.keys() != expected.keys():
        raise ValueError("Candidate prediction IDs differ from the expected IDs")
    per_case = []
    for case_id, reference in expected.items():
        targets = signatures(reference)
        predictions = signatures(actual[case_id])
        per_case.append({
            "case_id": case_id,
            "strict": predictions == targets,
            "actions_matched": sum((predictions & targets).values()),
            "expected_actions": len(reference),
            "returned_actions": len(actual[case_id]),
        })
    return {
        "namespace": results["namespace"],
        "strict_cases": sum(entry["strict"] for entry in per_case),
        "families": len(per_case),
        "cases": per_case,
    }


def recompute():
    results = classify_candidates(
        load(REGRESSION / "A.json"),
        load(REGRESSION / "facts.json"),
        load(CLASSIFICATION / "catalog.json"),
    )
    score = compare(results, load(REGRESSION / "expected.json"))
    if score["strict_cases"] != score["families"]:
        raise ValueError("Numeric candidate development regression failed")
    boundaries = recompute_boundaries()
    return {
        "scope": "development_regression",
        "decisions": results,
        "score": score,
        "numerical_examples": {
            key: boundaries[key]
            for key in ("half_running_sum", "raw_moment_cancellation")
        },
    }


if __name__ == "__main__":
    print(json.dumps(recompute(), ensure_ascii=False, indent=2))
