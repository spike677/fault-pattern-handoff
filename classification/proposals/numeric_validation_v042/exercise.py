"""Freeze, run and replay v0.4.2 exercises on previously opened materials."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CLASSIFICATION = HERE.parents[1]
CHECKOUT = CLASSIFICATION.parent
NUMERIC = HERE.parent / "numeric_validation"
sys.path[:0] = [str(CLASSIFICATION), str(NUMERIC)]

from holdout import CODE_FILES, ROUNDS, now, payload, payload_hash
from proposals.numeric_validation_v042.reader import decode_response, response_schema
from validation_0_3_1.reader_v04.readback import answer_from_log, call_reader, load, save, sha
from verify_regression import compare


INPUTS = ("A.json", "scopes.json", "execution.json", "response-schema.json")
PROGRAM = (*CODE_FILES, HERE / "PROMPT.md", HERE / "reader.py", Path(__file__).resolve())
KINDS = {"original": "holdout", "fixed": "regression"}
FIXED_SCOPES = {
    "E06": "固定旧版本中单块 CPU Flash Attention 的 F16 V 路径。沿 V 的读取、循环、重缩放与输出分析。区分源码结论和修复报告。",
    "G05": "固定旧版本中普通 SkipLayerNormalization 小核的静态范围，给定 FP32 输入、无 bias、skip 为零。可用宽度 4 作为求值对照，明确哪些形状和实际派发缺少运行证据。",
}


def prompt(stage):
    return (HERE / "PROMPT.md").read_text(encoding="utf-8") + "\n\n" + payload(stage)


def program_hashes():
    return {p.relative_to(CHECKOUT).as_posix(): sha(p) for p in PROGRAM}


def reference(suite):
    if suite == "original":
        return load(NUMERIC / "holdout" / "B.json")["expected"]
    expected = load(NUMERIC / "regression" / "expected.json")
    return {key: expected[key] for key in FIXED_SCOPES}


def reference_hash(expected):
    return payload_hash(json.dumps(expected, sort_keys=True, ensure_ascii=False))


def prepare(stage, suite):
    if stage.is_relative_to(CHECKOUT):
        raise ValueError("Use a new exercise directory outside the checkout")
    stage.mkdir(parents=True)
    source = NUMERIC / KINDS[suite]
    if suite == "original":
        for name in ("A.json", "scopes.json"):
            (stage / name).write_bytes((source / name).read_bytes())
    else:
        cases = load(source / "A.json")["cases"]
        save(stage / "A.json", {"cases": [c for c in cases if c["case_id"] in FIXED_SCOPES]})
        save(stage / "scopes.json", FIXED_SCOPES)
    execution = load(NUMERIC / "holdout" / "execution.json")
    execution.update(batch_kind="exercise_revised_prompt", prompt_sha256=payload_hash(prompt(stage)),
                     candidate_baseline="25808757205288bfa19f4c7259c99accf4243154")
    save(stage / "execution.json", execution)
    save(stage / "response-schema.json", response_schema())
    save(stage / "freeze.json", {
        "frozen_at": now(), "suite": suite, "scope": "exercise_revised_prompt",
        "inputs": {name: sha(stage / name) for name in INPUTS},
        "program": program_hashes(), "payload_sha256": payload_hash(prompt(stage)),
    })
    expected = reference(suite)
    if expected.keys() != {case["case_id"] for case in load(stage / "A.json")["cases"]}:
        raise ValueError("Reference and source inventories differ")
    save(stage / "seal.json", {
        "sealed_at": now(), "freeze_sha256": sha(stage / "freeze.json"),
        "answer_sha256": reference_hash(expected), "previously_opened_material": True,
    })


def check_freeze(stage):
    freeze = load(stage / "freeze.json")
    seal = load(stage / "seal.json")
    if (freeze["inputs"] != {name: sha(stage / name) for name in INPUTS}
            or freeze["program"] != program_hashes()
            or freeze["payload_sha256"] != payload_hash(prompt(stage))
            or seal["freeze_sha256"] != sha(stage / "freeze.json")
            or freeze["frozen_at"] > seal["sealed_at"]):
        raise ValueError("Exercise inputs, program or seal changed")
    return freeze, seal


def decode(stage, directory):
    context, message, usage = answer_from_log(directory / "execution.jsonl")
    result, notes = decode_response(
        load(stage / "A.json"), json.loads(message), load(CLASSIFICATION / "catalog.json"),
    )
    return {"context": context, "usage": usage, **result}, notes


def capture_hashes(directory, context):
    return {
        "context": context, "tool_events": 0,
        "files": {name: sha(directory / name) for name in ("execution.jsonl", "result.json", "readback.md")},
    }


def read(stage):
    check_freeze(stage)
    if any((stage / name).exists() for name in (*ROUNDS, "lock.json", "score.json")):
        raise ValueError("A previous exercise attempt exists")
    directories = [stage / name for name in ROUNDS]
    for directory in directories:
        directory.mkdir()
    execution = load(stage / "execution.json")
    body = prompt(stage)
    print(f"Starting two fresh readers on {stage.name}", flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = [pool.submit(call_reader, execution, body, directory / "execution.jsonl",
                               stage / "response-schema.json") for directory in directories]
        for handoff in pending:
            handoff.result()
    captures = {}
    for directory in directories:
        result, notes = decode(stage, directory)
        save(directory / "result.json", result)
        (directory / "readback.md").write_text(notes, encoding="utf-8", newline="\n")
        captures[directory.name] = capture_hashes(directory, result["context"])
    if len({run["context"] for run in captures.values()}) != len(ROUNDS):
        raise ValueError("Expected two different fresh reader contexts")
    save(stage / "lock.json", {
        "locked_at": now(), "seal_sha256": sha(stage / "seal.json"), "rounds": captures,
    })
    print(f"Locked both readers on {stage.name}", flush=True)


def replay(stage):
    freeze, seal = check_freeze(stage)
    lock = load(stage / "lock.json")
    if (lock["seal_sha256"] != sha(stage / "seal.json") or lock["locked_at"] < seal["sealed_at"]
            or lock["rounds"].keys() != set(ROUNDS)
            or len({run["context"] for run in lock["rounds"].values()}) != len(ROUNDS)):
        raise ValueError("Exercise lock does not bind two fresh contexts to the seal")
    expected = reference(freeze["suite"])
    if reference_hash(expected) != seal["answer_sha256"]:
        raise ValueError("Reference has changed since sealing")
    scores = {}
    for name in ROUNDS:
        directory = stage / name
        result, notes = decode(stage, directory)
        if (result != load(directory / "result.json")
                or notes != (directory / "readback.md").read_text(encoding="utf-8")
                or capture_hashes(directory, result["context"]) != lock["rounds"][name]):
            raise ValueError(f"Locked output changed: {name}")
        scores[name] = {**compare(result["decisions"], expected),
                        "reader_issues": result["reader_issues"]}
    return {"scope": freeze["scope"], "suite": freeze["suite"], "external_witness": False,
            "lock_sha256": sha(stage / "lock.json"), "scores": scores}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "read", "score", "verify"))
    parser.add_argument("stage", type=Path)
    parser.add_argument("--suite", choices=sorted(KINDS), default="original")
    args = parser.parse_args()
    stage = args.stage.resolve()
    if args.command == "prepare":
        prepare(stage, args.suite)
    elif args.command == "read":
        read(stage)
    else:
        score = replay(stage)
        if args.command == "score":
            with (stage / "score.json").open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(score, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        elif load(stage / "score.json") != score:
            raise ValueError("Stored score does not match the replay")
        print(json.dumps(score, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
