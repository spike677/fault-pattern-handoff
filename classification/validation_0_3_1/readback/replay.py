"""Verify the recorded reader outputs and recompute the sealed pilot scores."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from readback import (
    CANDIDATE, answer_from_log, check_frozen, classify, evaluate_command,
    load, packets_from_response, render, sha,
)


def leaf_counts(score, mode):
    label = f"leaf:MECH-v0.3:{mode}"
    for run in score["runs"]:
        wanted = sum(
            item["primary"] == label
            for case in run["cases"]
            for item in case["expected_verdicts"].values()
        )
        predictions = [row for case in run["cases"] for row in case["actions"]
                       if row["actual"] == label]
        hits = sum(row["primary_expected"] == label and row["facts_supported"]
                   for row in predictions)
        yield {"eligible": wanted, "supported_hits": hits,
               "unsupported_or_wrong_claims": len(predictions) - hits}


def replay_stage(stage, candidate, output):
    a = stage / "A.json"
    package = load(a)
    payload_hash = hashlib.sha256(render(stage, candidate).encode("utf-8")).hexdigest()
    runs = [stage / "round-1", stage / "round-2"]
    ids = []
    for run_dir in runs:
        log = run_dir / "execution.jsonl"
        context, text, _ = answer_from_log(log)
        ids.append(context)
        facts, notes = packets_from_response(package, json.loads(text))
        context_path = run_dir / "context.json"
        facts_path = run_dir / "facts.json"
        results_path = run_dir / "results.json"
        captured = load(run_dir / "run.json")
        if (load(context_path)["context_id"] != context
                or load(context_path)["payload_sha256"] != payload_hash
                or load(facts_path) != facts
                or (run_dir / "readback.md").read_text(encoding="utf-8") != notes
                or load(results_path) != classify(candidate, a, facts_path)
                or captured["artifacts"] != {
                    "context_sha256": sha(context_path),
                    "facts_sha256": sha(facts_path),
                    "results_sha256": sha(results_path),
                    "log_sha256": sha(log),
                }):
            raise ValueError(f"Recorded output differs from replay: {run_dir}")
    if len(set(ids)) != 2:
        raise ValueError("Reader contexts were not distinct")
    subprocess.run(evaluate_command(
        candidate, "score", stage.parent / "freeze.json", a, stage / "seal.json",
        runs[0] / "run.json", runs[1] / "run.json", stage / "lock.json",
        stage / "B.json", stage / "review.json", output,
    ), check=True)
    score = load(output)
    if score != load(stage / "score.json"):
        raise ValueError(f"Recomputed score differs from recorded score: {stage}")
    return {mode: list(leaf_counts(score, mode)) for mode in ("P2", "C2", "C3")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("--candidate", type=Path, default=CANDIDATE)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    batch = args.batch.resolve()
    check_frozen(candidate, batch)
    stages = sorted(path for path in batch.iterdir() if (path / "score.json").is_file())
    if not stages:
        raise ValueError("No scored batch stages found")
    with tempfile.TemporaryDirectory(prefix="pilot-replay-") as directory:
        results = {stage.name: replay_stage(stage, candidate, Path(directory) / f"{stage.name}.json")
                   for stage in stages}
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
