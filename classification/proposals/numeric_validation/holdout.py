"""Seal, read, lock and replay candidate-only holdout cases."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from classify_candidates import CLASSIFICATION, DECISIVE_FACTS, classify_candidates, load
from verify_regression import compare, recompute

HERE = Path(__file__).resolve().parent
CANDIDATE = CLASSIFICATION.parent
READER = CLASSIFICATION / "validation_0_3_1" / "reader_v04"
EXPOSURES = CLASSIFICATION / "validation_0_4_1" / "operator_holdout" / "exposures-after.json"
sys.path.insert(0, str(READER))
from readback import answer_from_log, call_reader, packets_from_response, save, sha

STAGE_FILES = ("A.json", "scopes.json", "sources.json", "lineage.json", "execution.json", "response-schema.json")
CODE_FILES = (
    HERE / "PROMPT.md", HERE / "classify_candidates.py", HERE / "verify_regression.py",
    Path(__file__).resolve(), CLASSIFICATION / "classify.py", CLASSIFICATION / "catalog.json",
    READER / "readback.py", READER / "RESPONSE.json", EXPOSURES,
)
ROUNDS = ("round-1", "round-2")


def now():
    return datetime.now(timezone.utc).isoformat()


def payload(stage):
    cases = load(stage / "A.json")["cases"]
    scopes = load(stage / "scopes.json")
    sections = [
        (HERE / "PROMPT.md").read_text(encoding="utf-8"),
        "## 七条冻结机理定义\n" + (CLASSIFICATION / "catalog.json").read_text(encoding="utf-8"),
    ]
    for case in cases:
        case_id = case["case_id"]
        sections.append(f"## {case_id}\n受评范围：{scopes[case_id]}")
        for source in case["sources"]:
            metadata = {key: value for key, value in source.items() if key != "text"}
            lines = [f"{line:03d}|{text}" for line, text in enumerate(source["text"].splitlines(), 1)]
            sections.append(json.dumps(metadata, ensure_ascii=False) + "\n" + "\n".join(lines))
    return "\n\n".join(sections) + "\n"


def payload_hash(body):
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def check_freeze(stage):
    freeze = load(stage / "freeze.json")
    if (freeze["inputs"] != {name: sha(stage / name) for name in STAGE_FILES}
            or freeze["program"] != {p.relative_to(CANDIDATE).as_posix(): sha(p) for p in CODE_FILES}
            or freeze["payload_sha256"] != payload_hash(payload(stage))):
        raise ValueError("Frozen reader inputs or implementation changed")
    return freeze


def seal(stage, private_answer):
    recompute()
    if private_answer.is_relative_to(CANDIDATE):
        raise ValueError("The answer must be outside the reader checkout")
    if any((stage / name).exists() for name in ("freeze.json", "seal.json", *ROUNDS, "B.json")):
        raise ValueError("The holdout directory already contains an attempt")
    case_ids = [case["case_id"] for case in load(stage / "A.json")["cases"]]
    if len(case_ids) != len(set(case_ids)) or set(case_ids) != set(load(private_answer)["expected"]):
        raise ValueError("Material and sealed-reference inventories differ")
    lineage = load(stage / "lineage.json")
    if lineage.keys() != set(case_ids):
        raise ValueError("Every independent family needs a lineage record")
    prior = {key.casefold() for key in load(EXPOSURES)}
    for case_id in case_ids:
        keys = {key.casefold() for key in lineage[case_id]}
        if not keys or prior.intersection(keys):
            raise ValueError(f"Previously exposed family or duplicated lineage: {case_id}")
        prior.update(keys)
    schema = load(READER / "RESPONSE.json")
    keys = schema["$defs"]["fact"]["properties"]["key"]["enum"]
    keys.extend(sorted(DECISIVE_FACTS - set(keys)))
    save(stage / "response-schema.json", schema)
    save(stage / "freeze.json", {
        "frozen_at": now(),
        "inputs": {name: sha(stage / name) for name in STAGE_FILES},
        "program": {p.relative_to(CANDIDATE).as_posix(): sha(p) for p in CODE_FILES},
        "payload_sha256": payload_hash(payload(stage)),
    })
    save(stage / "seal.json", {
        "sealed_at": now(),
        "freeze_sha256": sha(stage / "freeze.json"),
        "answer_sha256": sha(private_answer),
        "custody": "outside_checkout",
    })


def decode(stage, log):
    context, message, usage = answer_from_log(log)
    facts, notes = packets_from_response(load(stage / "A.json"), json.loads(message))
    decisions = classify_candidates(load(stage / "A.json"), facts, load(CLASSIFICATION / "catalog.json"))
    return {"context": context, "usage": usage, "facts": facts, "decisions": decisions}, notes


def read(stage):
    freeze = check_freeze(stage)
    seal_record = load(stage / "seal.json")
    if seal_record["freeze_sha256"] != sha(stage / "freeze.json") or (stage / "B.json").exists():
        raise ValueError("Reader run requires the pre-read seal with the answer in custody")
    for name in ROUNDS:
        if (stage / name).exists():
            raise ValueError(f"Previous round exists: {name}")
    for name in ROUNDS:
        (stage / name).mkdir()
    execution = load(stage / "execution.json")
    body = payload(stage)
    logs = [stage / name / "execution.jsonl" for name in ROUNDS]
    with ThreadPoolExecutor(max_workers=len(ROUNDS)) as pool:
        pending = [pool.submit(call_reader, execution, body, log, stage / "response-schema.json") for log in logs]
        for response in pending:
            response.result()
    locked = {}
    for log in logs:
        result, notes = decode(stage, log)
        save(log.parent / "result.json", result)
        (log.parent / "readback.md").write_text(notes, encoding="utf-8", newline="\n")
        locked[log.parent.name] = {
            "log_sha256": sha(log), "result_sha256": sha(log.parent / "result.json"),
            "context": result["context"], "tool_events": 0,
        }
    if len({run["context"] for run in locked.values()}) != len(ROUNDS):
        raise ValueError("The two rounds must come from different fresh contexts")
    save(stage / "lock.json", {
        "locked_at": now(), "seal_sha256": sha(stage / "seal.json"),
        "payload_sha256": freeze["payload_sha256"], "rounds": locked,
    })
    print("Locked two independent tool-free reader rounds")


def replay(stage, answer):
    freeze = check_freeze(stage)
    seal_record = load(stage / "seal.json")
    lock = load(stage / "lock.json")
    if (seal_record["freeze_sha256"] != sha(stage / "freeze.json")
            or lock["seal_sha256"] != sha(stage / "seal.json")
            or lock["payload_sha256"] != freeze["payload_sha256"]
            or not freeze["frozen_at"] <= seal_record["sealed_at"] <= lock["locked_at"]
            or len({r["context"] for r in lock["rounds"].values()}) != len(ROUNDS)
            or sha(answer) != seal_record["answer_sha256"]):
        raise ValueError("Freeze, custody, reference or lock mismatch")
    expected = load(answer)["expected"]
    scores = {}
    for name in ROUNDS:
        directory = stage / name
        log = directory / "execution.jsonl"
        result, _ = decode(stage, log)
        if lock["rounds"][name] != {
            "log_sha256": sha(log), "result_sha256": sha(directory / "result.json"),
            "context": result["context"], "tool_events": 0,
        } or load(directory / "result.json") != result:
            raise ValueError(f"Locked predictions changed: {name}")
        scores[name] = compare(result["decisions"], expected)
    return {"scope": "exercise_only", "answer_sha256": sha(answer), "scores": scores}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("seal", "read", "reveal", "verify"))
    parser.add_argument("stage", type=Path)
    parser.add_argument("answer", type=Path, nargs="?")
    args = parser.parse_args()
    stage = args.stage.resolve()
    if args.command == "seal":
        seal(stage, args.answer.resolve())
    elif args.command == "read":
        read(stage)
    elif args.command == "reveal":
        answer = args.answer.resolve()
        score = replay(stage, answer)
        with (stage / "B.json").open("xb") as stream:
            stream.write(answer.read_bytes())
        save(stage / "score.json", score)
        save(stage / "reveal.json", {"revealed_at": now(), "lock_sha256": sha(stage / "lock.json"),
                                    "answer_sha256": sha(stage / "B.json"), "external_witness": False})
        print(json.dumps(score, ensure_ascii=False, indent=2))
    else:
        score = replay(stage, stage / "B.json")
        if score != load(stage / "score.json"):
            raise ValueError("Stored score disagrees with the replay")
        print(json.dumps(score, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
