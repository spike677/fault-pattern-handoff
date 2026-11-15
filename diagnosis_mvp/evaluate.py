"""Freeze diagnosis and run the two evaluation tracks with sealed answers."""

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

from diagnose import KNOWN_FIELDS, METHODS, RULES, VERSION, diagnose, read_json


ROOT = Path(__file__).resolve().parent
FREEZE_PATH = ROOT / f"freeze_v{VERSION.replace('.', '_')}.json"
FROZEN_FILES = ("diagnose.py", "evaluate.py", "test_diagnose.py", "test_evaluate.py", "development.json")
PROTOCOL = {
    "version": "1",
    "budgets": {"classification": 0, "diagnosis": 2},
    "cost_per_request": 1,
    "methods": {"classification": ["adaptive"], "diagnosis": list(METHODS)},
}
KNOWN_DEVELOPMENT_LINEAGE = {
    "answer:pypto-shared-tutorial", "event:tensorrt-llm-07-08", "event:shared-13-14",
}
OUTCOMES = {"SUPPORTED", "NO_SUPPORTED_MECHANISM", "UNKNOWN", "OUT_OF_SCOPE"}
FAILURE_TYPES = {"definition", "diagnostic_step", "observation", "reference", "evidence"}


def require(condition, explanation):
    if not condition:
        raise ValueError(explanation)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_record(path, record):
    content = (json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True,
                          allow_nan=False) + "\n").encode("utf-8")
    if path.exists():
        require(path.read_bytes() == content, f"Existing record differs: {path}")
        return
    with path.open("xb") as output:
        output.write(content)


def freeze():
    dev = read_json(ROOT / "development.json")["cases"]
    dev_lineage = KNOWN_DEVELOPMENT_LINEAGE | {f"family:{c['family_id']}" for c in dev}
    record = {
        "engine_version": VERSION,
        "protocol": PROTOCOL,
        "artifacts": {name: digest(ROOT / name) for name in FROZEN_FILES},
        "development_lineage": sorted(dev_lineage),
    }
    write_record(FREEZE_PATH, record)


def verify_freeze():
    freeze_record = read_json(FREEZE_PATH)
    require(freeze_record["engine_version"] == VERSION and freeze_record["protocol"] == PROTOCOL,
            "The evaluation settings differ from the freeze")
    current = {name: digest(ROOT / name) for name in FROZEN_FILES}
    require(current == freeze_record["artifacts"], "Frozen artifacts changed")
    return freeze_record, digest(FREEZE_PATH)


def check_lineage(inputs, disallowed):
    trials = {}
    groups, key_owners = {}, {}
    for row in inputs:
        require(set(row) == {"case", "track", "lineage"}, "Input row contains unexpected sections")
        case, track, lineage = (row[key] for key in ("case", "track", "lineage"))
        require(set(case) <= {"case_id", "family_id", "build", "call_id", "routes",
                              "contract", "observations", "intake"}, "Input case contains unexpected sections")
        require(isinstance(lineage, list) and all(isinstance(x, str) and x for x in lineage),
                "Each source identity must be an explicit string")
        case_id, group = (case[key] for key in ("case_id", "family_id"))
        require(track in PROTOCOL["budgets"], f"Unknown track: {track}")
        require(case_id not in trials, f"Repeated case: {case_id}")
        require(f"family:{group}" in lineage, f"Missing family identity: {case_id}")
        require(not disallowed.intersection(lineage), f"Development overlap: {case_id}")
        require(groups.setdefault(group, track) == track, f"Family crosses tracks: {group}")
        for identity in lineage:
            require(key_owners.setdefault(identity, group) == group,
                    f"Shared source is assigned to different families: {identity}")
        trials[case_id] = row
    require(trials and set(groups.values()) == set(PROTOCOL["budgets"]),
            "The evaluation needs both tracks")
    return trials


def load_public_bundle(run_path):
    public = run_path / "public"
    freeze_record, freeze_digest = verify_freeze()
    seal = read_json(public / "seal.json")
    require(seal["freeze_sha256"] == freeze_digest, "Input bundle uses a different freeze")
    require(seal["kind"] in ("SYNTHETIC_CONTROLLED", "HISTORICAL_HELDOUT_DECLARED"),
            "Unknown sample preparation scope")
    for file in ("inputs.json", "packets.json"):
        require(digest(public / file) == seal["hashes"][file], f"Sealed file differs: {file}")
    trials = check_lineage(read_json(public / "inputs.json"), set(freeze_record["development_lineage"]))
    packets = read_json(public / "packets.json")
    require(set(packets) == set(trials), "Input and observation packet IDs differ")
    for case_id, row in trials.items():
        offered = packets[case_id]
        case = row["case"]
        initial = {obs["field"] for obs in case["observations"]}
        require(row["track"] == "diagnosis" or not offered,
                f"Classification cannot have a requestable packet: {case_id}")
        for field, observation in offered.items():
            require(field in KNOWN_FIELDS and field not in initial
                    and observation["field"] == field
                    and observation["build"] == case["build"] and observation["call_id"] == case["call_id"],
                    f"Invalid observation packet for {case_id}: {field}")
    return seal, trials, packets


def run_trial(row, packets, method):
    case = deepcopy(row["case"])
    budget = PROTOCOL["budgets"][row["track"]]
    requested, timeline = [], []
    result = diagnose(case, method)
    for _ in range(budget):
        request = result["next_observation"]
        if request is None:
            break
        field = request["field"]
        observation = packets.get(field)
        requested.append(field)
        timeline.append({
            "request": request, "prior_input_sha256": result["input_sha256"],
            "prior_outcome": result["outcome"], "prior_supported": result["supported_mechanisms"],
            "returned_fact_id": observation["fact_id"] if observation else None,
        })
        if observation:
            case["observations"].append(observation)
        result = diagnose(case, method, requested)
    return {"case_id": case["case_id"], "track": row["track"], "method": method, "budget": budget,
            "timeline": timeline, "visible_fields": sorted({o["field"] for o in case["observations"]}),
            "result": result}


def predict(run_path):
    seal, trials, packets = load_public_bundle(run_path)
    predictions = [
        run_trial(row, packets[case_id], method)
        for case_id, row in trials.items()
        for method in PROTOCOL["methods"][row["track"]]
    ]
    write_record(run_path / "predictions.json", {
        "freeze_sha256": seal["freeze_sha256"],
        "seal_sha256": digest(run_path / "public" / "seal.json"),
        "predictions": predictions,
    })


def grade(prediction, answer, available):
    result = prediction["result"]
    want, gave = set(answer["mechanisms"]), set(result["supported_mechanisms"])
    expected = answer["outcome"]
    correct = expected == result["outcome"] and want == gave
    decisive = set(answer["decisive_fields"])
    timeline = prediction["timeline"]
    failure = None
    if not correct:
        missing = decisive - set(prediction["visible_fields"])
        if missing.intersection(available):
            failure = "diagnostic_step"
        elif missing:
            failure = "observation"
        elif expected == "UNKNOWN":
            failure = answer["unresolved"]
        else:
            failure = "definition"
    stage = result["numeric_stage"]
    numeric_stage_correct = (
        stage is not None and stage["status"] == answer["numeric_stage"]
        if "numeric_stage" in answer else None
    )
    output_check_correct = (
        result["output_check"]["status"] == answer["output_check"]
        if "output_check" in answer else None
    )
    return {
        "numeric_stage_correct": numeric_stage_correct, "output_check_correct": output_check_correct,
        "case_id": prediction["case_id"], "family_id": result["family_id"],
        "expected": expected, "actual": result["outcome"],
        "expected_mechanisms": sorted(want), "actual_mechanisms": sorted(gave),
        "exact": correct, "claim": bool(gave), "unsupported_claim": bool(gave - want),
        "missed_mechanisms": sorted(want - gave), "extra_mechanisms": sorted(gave - want),
        "abstained": result["outcome"] == "UNKNOWN", "unresolved": answer["unresolved"],
        "failure": failure,
        "requests": len(timeline), "returned": sum(t["returned_fact_id"] is not None for t in timeline),
        "first_request_decisive": timeline[0]["request"]["field"] in decisive if timeline else None,
    }


def summarize(grades):
    families = {}
    for item in grades:
        families.setdefault(item["family_id"], []).append(item["exact"])
    positive = [r for r in grades if r["expected"] == "SUPPORTED"]
    unknown = [r for r in grades if r["expected"] == "UNKNOWN"]
    stable_negatives = [r for r in grades if r["expected"] in ("NO_SUPPORTED_MECHANISM", "OUT_OF_SCOPE")]
    requests = sum(r["requests"] for r in grades)

    return {
        "cases": len(grades), "case_exact": sum(r["exact"] for r in grades),
        "families": len(families), "family_exact": sum(all(results) for results in families.values()),
        "attributable": len(positive), "attributable_correct": sum(r["exact"] for r in positive),
        "stable_negatives": len(stable_negatives),
        "stable_negatives_correct": sum(r["exact"] for r in stable_negatives),
        "affirmative": sum(r["claim"] for r in grades),
        "unsupported_affirmative": sum(r["unsupported_claim"] for r in grades),
        "gold_unknown": len(unknown), "correct_abstention": sum(r["exact"] for r in unknown),
        "excess_abstention": sum(r["abstained"] and r["expected"] != "UNKNOWN" for r in grades),
        "missed_mechanisms": sum(len(r["missed_mechanisms"]) for r in grades),
        "extra_mechanisms": sum(len(r["extra_mechanisms"]) for r in grades),
        "requests": requests, "returned": sum(r["returned"] for r in grades),
        "request_cost": requests * PROTOCOL["cost_per_request"],
        "first_requests": sum(r["first_request_decisive"] is not None for r in grades),
        "first_requests_decisive": sum(r["first_request_decisive"] is True for r in grades),
        "numeric_stage_cases": sum(r["numeric_stage_correct"] is not None for r in grades),
        "numeric_stage_correct": sum(r["numeric_stage_correct"] is True for r in grades),
        "output_check_cases": sum(r["output_check_correct"] is not None for r in grades),
        "output_check_correct": sum(r["output_check_correct"] is True for r in grades),
        "disagreement_causes": dict(Counter(r["failure"] for r in grades if r["failure"])),
        "gold_unknown_causes": dict(Counter(r["unresolved"] for r in unknown)),
    }


def score(run_path, answer_key):
    seal, trials, packets = load_public_bundle(run_path)
    predictions_path = run_path / "predictions.json"
    predictions = read_json(predictions_path)
    require(predictions["freeze_sha256"] == seal["freeze_sha256"]
            and predictions["seal_sha256"] == digest(run_path / "public" / "seal.json"),
            "Predictions do not belong to this freeze and sealed bundle")
    answer_digest = digest(answer_key)
    require(answer_digest == seal["hashes"]["answer_key.json"], "Answer key differs from the seal")
    answers = read_json(answer_key)
    require(set(answers) == set(trials), "Answer key case inventory differs")
    evaluations = {}
    expected_predictions = {(case_id, method) for case_id, row in trials.items()
                            for method in PROTOCOL["methods"][row["track"]]}
    seen = set()
    for prediction in predictions["predictions"]:
        case_id = prediction["case_id"]
        key = (case_id, prediction["method"])
        require(key in expected_predictions and key not in seen, "Duplicate or invalid prediction")
        seen.add(key)
        track, answer = trials[case_id]["track"], answers[case_id]
        require(prediction["track"] == track, "Prediction uses an incorrect track")
        require(answer["outcome"] in OUTCOMES and
                (answer["outcome"] == "SUPPORTED") == bool(answer["mechanisms"]),
                f"Inconsistent answer: {case_id}")
        require((answer["outcome"] == "UNKNOWN" and answer["unresolved"] in FAILURE_TYPES)
                or (answer["outcome"] != "UNKNOWN" and answer["unresolved"] is None),
                f"Missing or unexpected abstention reason: {case_id}")
        require(set(answer["decisive_fields"]) <= KNOWN_FIELDS
                and set(answer["mechanisms"]) <= {rule.name for rule in RULES},
                f"Unknown decisive field or mechanism: {case_id}")
        available = set(packets[case_id])
        evaluations.setdefault(f"{track}/{prediction['method']}", []).append(grade(prediction, answer, available))
    require(seen == expected_predictions, "Predictions are incomplete")
    write_record(run_path / "score.json", {
        "kind": seal["kind"], "preparation": seal["preparation"], "freeze_sha256": seal["freeze_sha256"],
        "seal_sha256": predictions["seal_sha256"], "predictions_sha256": digest(predictions_path),
        "answer_sha256": answer_digest,
        "evaluations": {key: {"metrics": summarize(grades), "cases": grades}
                        for key, grades in evaluations.items()},
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("freeze")
    sub.add_parser("predict").add_argument("run", type=Path)
    scorer = sub.add_parser("score")
    scorer.add_argument("run", type=Path)
    scorer.add_argument("--answer-key", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "freeze":
        freeze()
    elif args.command == "predict":
        predict(args.run)
    else:
        score(args.run, args.answer_key)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        sys.exit(f"Evaluation error: {error}")

