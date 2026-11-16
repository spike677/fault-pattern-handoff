"""Reproduce captured scores and check that IDs drive grading."""

import argparse
import json
from pathlib import Path
import sys
import tempfile


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from evaluate import b_cases, compare_runs, grade_case, paired, score, summarize


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def reversed_actions(case):
    return {**case, "actions": list(reversed(case["actions"]))}


def verify_grading_order(stage, audit=None):
    first = stage / "round-1" / "run.json"
    second = stage / "round-2" / "run.json"
    standard, cases, package, _, predictions = paired(
        stage.parent / "freeze.json", stage / "A.json", stage / "seal.json", first, second,
    )
    grading = audit if audit is not None else stage
    archived = load(grading / "score.json")
    answer = load(audit / "revision.json")["answer"] if audit is not None else load(stage / "B.json")
    shuffled = dict(reversed(list(answer.items())))
    shuffled["cases"] = [reversed_actions(case) for case in reversed(answer["cases"])]
    answers = b_cases(shuffled, cases, standard, package["kind"])
    judgement = load(grading / "review.json")
    reviews = {run["run_sha256"]: run["cases"] for run in reversed(judgement["runs"])}
    lock = load(stage / "lock.json")
    rescored = []
    for digest, predicted, recorded in zip(lock["run_sha256"], predictions, archived["runs"]):
        review = {case["case_id"]: reversed_actions(case) for case in reversed(reviews[digest])}
        graded = [
            grade_case(reversed_actions(predicted[case_id]), answers[case_id], review[case_id], standard)
            for case_id in reversed(sorted(cases))
        ]
        metrics = summarize(graded, standard)
        if metrics != recorded["metrics"]:
            raise ValueError(f"Permuting unordered case, action or review entries changed {stage.name} metrics")
        rescored.append({"run_sha256": digest, "cases": graded, "metrics": metrics})
    shuffled_stability = {**judgement, "stability": list(reversed(judgement["stability"]))}
    if compare_runs(rescored, shuffled_stability) != archived["stability"]:
        raise ValueError(f"Permuting unordered records changed the stability score of {stage.name}")


def verify_audit(stage, output):
    audit = stage / "answer-scope-audit"
    if not (audit / "score.json").is_file():
        return
    score(
        stage.parent / "freeze.json", stage / "A.json", stage / "seal.json",
        stage / "round-1" / "run.json", stage / "round-2" / "run.json",
        stage / "lock.json", stage / "B.json", audit / "review.json", output,
        revision_path=audit / "revision.json",
    )
    if load(output) != load(audit / "score.json"):
        raise ValueError(f"Recomputed audit score differs from {audit}")
    verify_grading_order(stage, audit)
    print(f"{stage.name}: answer audit replayed and unordered JSON entries permuted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path, nargs="?", default=HERE)
    args = parser.parse_args()
    batch = args.batch.resolve()
    reader = (HERE.parent / load(batch / "execution.json").get("reader_directory", "readback")).resolve()
    if reader.parent != HERE.parent:
        raise ValueError("Reader must be from the frozen validation tree")
    sys.path.insert(0, str(reader))
    from readback import CANDIDATE, check_frozen
    from replay import replay_stage

    check_frozen(CANDIDATE, batch)
    stages = sorted(stage for stage in batch.iterdir() if (stage / "score.json").is_file())
    if not stages:
        raise ValueError(f"No scored stages in {batch}")
    with tempfile.TemporaryDirectory(prefix="method-replay-") as scratch:
        directory = Path(scratch)
        for stage in stages:
            replay_stage(stage, CANDIDATE, directory / (stage.name + ".json"))
            verify_grading_order(stage)
            print(f"{stage.name}: scores replayed and unordered JSON entries permuted")
            verify_audit(stage, directory / (stage.name + "-audit.json"))


if __name__ == "__main__":
    main()
