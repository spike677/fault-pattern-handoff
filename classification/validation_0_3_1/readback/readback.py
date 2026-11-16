"""Run and replay the pilot's isolated, tool-free reader requests."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent
COMMIT = "21a6af4224b7c62681c241236c6850cac3e72109"
CANDIDATE = ROOT.parents[2]
DISABLED = (
    "shell_tool", "unified_exec", "shell_snapshot", "skill_search",
    "multi_agent", "plugins", "remote_plugin", "enable_mcp_apps",
)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def codex_command(execution, schema=None):
    binary = shutil.which("codex")
    if binary is None:
        raise RuntimeError("Codex CLI is required for new reader runs")
    command = [
        binary, "exec", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check",
        "--sandbox", "read-only", "--model", execution["model"],
        "-c", f'model_reasoning_effort="{execution["reasoning_effort"]}"',
        "-c", 'web_search="disabled"', "--json",
    ]
    for feature in DISABLED:
        command.extend(("--disable", feature))
    if schema is not None:
        command.extend(("--output-schema", str(schema)))
    return command + ["-"]


def answer_from_log(log):
    events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    for event in events:
        item = event.get("item")
        if item and item["type"] not in {"reasoning", "agent_message"}:
            raise ValueError(f"Unexpected reader tool or item: {item['type']}")
        if event["type"] in {"turn.failed", "error"}:
            raise ValueError(f"Reader failed: {event}")
    started = [event["thread_id"] for event in events if event["type"] == "thread.started"]
    finished = [event for event in events if event["type"] == "turn.completed"]
    messages = [event["item"]["text"] for event in events
                if event["type"] == "item.completed" and event["item"]["type"] == "agent_message"]
    if len(started) != 1 or len(finished) != 1 or not messages:
        raise ValueError("Expected one completed turn in a fresh context")
    return started[0], messages[-1], finished[0]["usage"]


def call_reader(execution, prompt, log, schema=None):
    with tempfile.TemporaryDirectory(prefix="pilot-reader-") as directory:
        with log.open("xb") as stdout, log.with_suffix(".stderr").open("xb") as stderr:
            subprocess.run(codex_command(execution, schema), cwd=directory,
                           input=prompt.encode("utf-8"), stdout=stdout, stderr=stderr,
                           check=True, timeout=900)
    return answer_from_log(log)


def render(stage, candidate):
    package = load(stage / "A.json")
    scopes = load(stage / "scopes.json")
    parts = [
        (ROOT / "PROMPT.md").read_text(encoding="utf-8"),
        "## 目录\n" + (candidate / "classification" / "catalog.json").read_text(encoding="utf-8"),
    ]
    for case in package["cases"]:
        case_id = case["case_id"]
        parts.append(f"## {case_id}\n受评范围：{scopes[case_id]}")
        for source in case["sources"]:
            metadata = {key: value for key, value in source.items() if key != "text"}
            lines = [f"{index:03d}|{line}" for index, line in
                     enumerate(source["text"].splitlines(), 1)]
            parts.append(json.dumps(metadata, ensure_ascii=False) + "\n" + "\n".join(lines))
    return "\n\n".join(parts) + "\n"


def packets_from_response(package, response):
    sources = {case["case_id"]: {item["id"]: item
                                for item in case["sources"]} for case in package["cases"]}
    facts, notes = [], []
    for packet in response["cases"]:
        case_id = packet["case_id"]
        notes.append(f"## {case_id}\n\n" + packet.pop("readback"))
        packet["fact_protocol"] = "classification_facts/0.3.1"
        for action in packet["actions"]:
            if action["upstream_id"] is None:
                action.pop("upstream_id")
            scope = action["scope"]
            scope_source = sources[case_id][scope.pop("source_id")]
            scope["version"] = scope_source["version"]
            scope["path"] = scope_source["path"]
            for field in ("build", "call_id"):
                if scope[field] is None:
                    scope.pop(field)
            for fact in action["facts"]:
                for anchor in fact["anchors"]:
                    source = sources[case_id].get(anchor["source_id"])
                    lines = source["text"].splitlines() if source else []
                    start, end = anchor["start_line"], anchor["end_line"]
                    anchor["quote"] = "\n".join(lines[start - 1:end]) if (
                        1 <= start <= end <= len(lines)
                    ) else ""
        facts.append(packet)
    if len(facts) != len(sources) or {packet["case_id"] for packet in facts} != set(sources):
        raise ValueError("Reader response inventory differs from A")
    return facts, "\n\n".join(notes) + "\n"


def evaluate_command(candidate, *args):
    return [sys.executable, "-B", "-X", "utf8",
            str(candidate / "classification" / "evaluate.py"), *map(str, args)]


def classify(candidate, a_path, facts_path):
    return json.loads(subprocess.check_output([
        sys.executable, "-B", "-X", "utf8", str(candidate / "classification" / "classify.py"),
        "--batch", str(a_path), str(facts_path),
    ], encoding="utf-8"))


def check_frozen(candidate, batch):
    manifest = load(batch / "inputs-sha256.json")
    if manifest["commit"] != COMMIT:
        raise ValueError(f"Expected the decision baseline {COMMIT}")
    for name, expected in manifest["shared_files"].items():
        if sha(ROOT / name) != expected:
            raise ValueError(f"Frozen input changed: {name}")
    for name, expected in manifest["batch_files"].items():
        if sha(batch / name) != expected:
            raise ValueError(f"Frozen batch input changed: {name}")
    for name, expected in manifest["candidate_files"].items():
        if sha(candidate / name) != expected:
            raise ValueError(f"Frozen candidate file changed: {name}")


def request_round(execution, prompt, output):
    output.mkdir()
    log = output / "execution.jsonl"
    return call_reader(execution, prompt, log, ROOT / "RESPONSE.json")


def capture_round(stage, candidate, output, execution, prompt, reply):
    batch = stage.parent
    log = output / "execution.jsonl"
    context_id, content, usage = reply
    facts, notes = packets_from_response(load(stage / "A.json"), json.loads(content))
    facts_path, results_path = output / "facts.json", output / "results.json"
    save(facts_path, facts)
    save(results_path, classify(candidate, stage / "A.json", facts_path))
    (output / "readback.md").write_text(notes, encoding="utf-8", newline="\n")
    context_path = output / "context.json"
    save(context_path, {
        "context_id": context_id,
        "executor_id": f"local-codex-exec:{context_id}",
        "execution": execution,
        "isolation_mechanism": "Ephemeral Codex request with no reader file or web tools",
        "usage": usage,
        "payload_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    })
    subprocess.run(evaluate_command(candidate, "capture", batch / "freeze.json", stage / "A.json",
                                    stage / "seal.json", results_path, context_path,
                                    facts_path, log, output / "run.json"), check=True)
    print(f"{stage.name} {output.name} captured: {context_id}", flush=True)


def run_round(stage, candidate, output):
    check_frozen(candidate, stage.parent)
    execution = load(stage.parent / "execution.json")
    prompt = render(stage, candidate)
    capture_round(stage, candidate, output, execution, prompt,
                  request_round(execution, prompt, output))


def run_pair(stage, candidate):
    batch = stage.parent
    check_frozen(candidate, batch)
    execution = load(batch / "execution.json")
    prompt = render(stage, candidate)
    outputs = [stage / f"round-{index}" for index in (1, 2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = [pool.submit(request_round, execution, prompt, output) for output in outputs]
        for output, reply in zip(outputs, pending):
            capture_round(stage, candidate, output, execution, prompt, reply.result())
    subprocess.run(evaluate_command(
        candidate, "lock", batch / "freeze.json", stage / "A.json", stage / "seal.json",
        *(output / "run.json" for output in outputs), stage / "lock.json",
    ), check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--pair", action="store_true")
    parser.add_argument("--candidate", type=Path, default=CANDIDATE)
    args = parser.parse_args()
    stage, candidate = args.stage.resolve(), args.candidate.resolve()
    if args.pair and args.output is None:
        run_pair(stage, candidate)
    elif args.output is not None and not args.pair:
        run_round(stage, candidate, args.output.resolve())
    else:
        parser.error("Provide an output directory or --pair")


if __name__ == "__main__":
    main()
