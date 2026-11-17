"""Freeze, capture and lock two source-only development reads of an existing A."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from mech_v04 import evaluation as formal

from . import graph, reader


HERE = Path(__file__).resolve().parent
PROTOCOL = "mech_v04_reliability_exercise/0.2"
ROUNDS = (1, 2)
common = formal.common


def inputs(directory):
    return directory / "A.json", directory / "reader-schema.json", directory / "freeze.json"


def implementation():
    formal_freeze = formal.frozen(formal.HERE / "F_FREEZE.json")
    artifacts = (HERE / name for name in ("graph.py", "reader.py", "PROMPT.md", "workflow.py",
                                         "scoring.py", "JUDGE.md", "scoring_rubric_v2.md"))
    return {
        "protocol": PROTOCOL, "graph_protocol": graph.PROTOCOL, "scope": "exercise_only",
        "catalog_version": formal_freeze["catalog_version"], "decision_version": formal_freeze["decision_version"],
        "formal_freeze_sha256": common.digest(formal.HERE / "F_FREEZE.json"),
        "artifacts": {path.name: common.digest(path) for path in artifacts},
        "execution": {**formal_freeze["execution"],
                      "batch_kind": "13-family source-only reliability exercise",
                      "prompt": "MECH-v0.4 source-to-root action graph",
                      "prompt_artifacts": {"reliability_v04/PROMPT.md": common.digest(reader.PROMPT)}},
    }


def freeze(source, directory):
    common.a_cases(source)
    directory.mkdir(parents=True, exist_ok=False)
    a_path, schema_path, freeze_path = inputs(directory)
    a_path.write_bytes(source.read_bytes())
    common.write_record(schema_path, reader.schema())
    settings = implementation()
    settings["execution"]["response_schema_sha256"] = common.digest(schema_path)
    common.write_record(freeze_path, {
        **settings, "a_sha256": common.digest(a_path), "schema_sha256": common.digest(schema_path),
        "prompt_sha256": sha256(reader.render(common.read_json(a_path)).encode("utf-8")).hexdigest(),
        "created_at": common.utc_now(), "answer_in_reader_inputs": False,
    })


def frozen(directory):
    a_path, schema_path, freeze_path = inputs(directory)
    record = common.read_json(freeze_path)
    expected = implementation()
    expected["execution"]["response_schema_sha256"] = common.digest(schema_path)
    if (any(record.get(key) != value for key, value in expected.items())
            or record["a_sha256"] != common.digest(a_path)
            or record["schema_sha256"] != common.digest(schema_path)
            or common.read_json(schema_path) != reader.schema()
            or record["answer_in_reader_inputs"] is not False):
        raise ValueError("MECH-v0.4 source-only freeze differs")
    material = common.read_json(a_path)
    payload = reader.render(material)
    if record["prompt_sha256"] != sha256(payload.encode("utf-8")).hexdigest():
        raise ValueError("Rendered source-only prompt differs")
    return record, material, payload


def round_dir(directory, number, attempt):
    return directory / f"round{number}" / f"attempt{attempt}"


def capture(material, log):
    context, message, usage = formal.reader.answer_from_log(log)
    facts = json.loads(message)
    graphs = graph.classify_package(material, facts)
    return facts, graphs, {"context_id": context, "usage": usage, "log_sha256": common.digest(log)}


def read(directory, number, attempt):
    record, material, payload = frozen(directory)
    folder = round_dir(directory, number, attempt)
    if (directory / "lock.json").exists():
        raise ValueError("The accepted rounds are locked")
    earlier = [round_dir(directory, number, n) for n in range(1, attempt)]
    if any(not path.is_dir() or (path / "run.json").exists() for path in earlier):
        raise ValueError("A retry requires preserved unsuccessful attempts")
    folder.mkdir(parents=True, exist_ok=False)
    log = folder / "read.jsonl"
    try:
        actual_cli = subprocess.check_output(["codex", "--version"], encoding="utf-8").strip().split()[-1]
        if actual_cli != record["execution"]["cli"]:
            raise ValueError(f"The installed reader CLI differs from the freeze: {actual_cli}")
        formal.call_reader(record["execution"], payload, log, inputs(directory)[1])
        facts, graphs, captured = capture(material, log)
        common.write_record(folder / "facts.json", facts)
        common.write_record(folder / "root_action_graph.json", graphs)
        common.write_record(folder / "run.json", {
            **captured, "round": number, "attempt": attempt, "scope": "exercise_only",
            "captured_at": common.utc_now(), "freeze_sha256": common.digest(inputs(directory)[2]),
            "facts_sha256": common.digest(folder / "facts.json"),
            "graph_sha256": common.digest(folder / "root_action_graph.json"),
        })
    except (ValueError, subprocess.SubprocessError) as error:
        common.write_record(folder / "failure.json", {"round": number, "attempt": attempt, "error": str(error)})
        raise
    print(f"Round {number} attempt {attempt} captured {len(graphs['cases'])} cases in {captured['context_id']}.")


def accepted(directory, attempts):
    _, material, _ = frozen(directory)
    freeze_sha256 = common.digest(inputs(directory)[2])
    records = []
    for number, attempt in zip(ROUNDS, attempts, strict=True):
        folder = round_dir(directory, number, attempt)
        run = common.read_json(folder / "run.json")
        facts, graphs, captured = capture(material, folder / "read.jsonl")
        if (run["freeze_sha256"] != freeze_sha256 or run["round"] != number or run["attempt"] != attempt
                or any(run[key] != value for key, value in captured.items())):
            raise ValueError(f"Round {number} differs from its capture or freeze")
        files = (("facts", "facts.json", facts), ("graph", "root_action_graph.json", graphs))
        for key, name, value in files:
            if common.digest(folder / name) != run[f"{key}_sha256"] or common.read_json(folder / name) != value:
                raise ValueError(f"Round {number} {key} differs on replay")
        records.append({
            "round": number, "attempt": attempt, "context_id": run["context_id"],
            "run_sha256": common.digest(folder / "run.json"), "graph_sha256": run["graph_sha256"],
            "facts_sha256": run["facts_sha256"], "log_sha256": run["log_sha256"],
        })
    if records[0]["context_id"] == records[1]["context_id"]:
        raise ValueError("Both reads must use separate ephemeral contexts")
    return records


def lock(directory, attempts):
    records = accepted(directory, attempts)
    common.write_record(directory / "lock.json", {
        "protocol": PROTOCOL, "scope": "exercise_only", "locked_at": common.utc_now(),
        "freeze_sha256": common.digest(inputs(directory)[2]), "rounds": records,
    })
    return records


def verify(directory):
    record = common.read_json(directory / "lock.json")
    attempts = [row["attempt"] for row in record["rounds"]]
    if (record["protocol"] != PROTOCOL or record["scope"] != "exercise_only"
            or record["freeze_sha256"] != common.digest(inputs(directory)[2])
            or record["rounds"] != accepted(directory, attempts)):
        raise ValueError("The lock differs from the accepted rounds")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_subparsers(dest="command", required=True)
    for key in ("freeze", "read", "lock", "verify"):
        sub = command.add_parser(key)
        sub.add_argument("directory", type=Path)
        if key == "freeze":
            sub.add_argument("a", type=Path)
        if key == "read":
            sub.add_argument("round", type=int, choices=ROUNDS)
            sub.add_argument("--attempt", default=1, type=int)
        if key == "lock":
            sub.add_argument("--attempts", default=(1, 1), type=int, nargs=2)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if args.command == "freeze":
        freeze(args.a, directory)
    elif args.command == "read":
        read(directory, args.round, args.attempt)
    else:
        result = lock(directory, args.attempts) if args.command == "lock" else verify(directory)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
