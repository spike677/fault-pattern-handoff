"""Freeze, seal, read and grade MECH-v0.4 using the classification-only evaluation protocol."""

import argparse
import hashlib
import json
from pathlib import Path

if __package__:
    from . import classifier, reader
else:
    import classifier
    import reader

import evaluate as common
from validation_0_3_1.reader_v04.readback import call_reader


HERE = classifier.HERE
EXECUTION = HERE / "execution.json"
EXPOSURES = HERE / "development-exposures.json"
ARTIFACTS = (
    *common.ARTIFACTS,
    "mech_v04/catalog.json", "mech_v04/classifier.py", "mech_v04/evaluation.py",
    "mech_v04/reader.py", "mech_v04/response-schema.json", "mech_v04/PROMPT.md",
    "mech_v04/execution.json", "mech_v04/development-exposures.json",
    "proposals/numeric_validation/classify_candidates.py",
    "proposals/numeric_validation_v042/reader.py",
    "proposals/numeric_validation_v042/PROMPT.md", "proposals/numeric_validation_v042/SCOPE_BINDING.md",
    "validation_0_3_1/reader_v04/readback.py", "validation_0_3_1/reader_v04/RESPONSE.json",
)


def implementation():
    catalog = common.read_json(classifier.CATALOG)
    classifier.validate_catalog(catalog, common.read_json(classifier.PILOT_CATALOG))
    config = common.read_json(EXECUTION)
    lineage = common.read_json(EXPOSURES)
    common.require(isinstance(lineage, list) and all(common.valid_lineage(key) for key in lineage),
                   "Expected namespaced development exposure keys")
    prompt_hashes = {path.relative_to(common.ROOT).as_posix(): common.digest(path)
                     for path in reader.PROMPT_PARTS}
    common.require(config["prompt_artifacts"] == prompt_hashes
                   and config["response_schema_sha256"] == common.digest(reader.SCHEMA),
                   "Execution prompt or schema hashes disagree with their inputs")
    common.require(common.read_json(reader.SCHEMA) == reader.schema(),
                   "The frozen response schema differs from the reader schema")
    return {
        "protocol": common.PROTOCOL, "decision_version": classifier.DECISION_VERSION,
        **common.catalog_standard(catalog),
        "execution": config, "development_lineage": sorted(set(lineage)),
        "artifacts": {name: common.artifact_digest(name) for name in ARTIFACTS},
    }


def freeze(out):
    common.write_record(out, {**implementation(), "created_at": common.utc_now()})


def frozen(path):
    record = common.read_json(path)
    common.require(all(record.get(key) == value for key, value in implementation().items()),
                   "MECH-v0.4 freeze or implementation differs")
    return record


def answer_cases(answer, cases, standard, kind):
    records = common.b_cases(answer, cases, standard, kind)
    exposures = {key.casefold() for key in standard["development_lineage"]}
    owners = {}
    for case in records.values():
        for key in case["lineage"]:
            key = key.casefold()
            common.require(key not in exposures, "An evaluation case overlaps development")
            common.require(owners.setdefault(key, case["family_id"]) == case["family_id"],
                           "An event crosses adjudicated families")
    return records


def seal(freeze_path, a, b, out, kind):
    standard = frozen(freeze_path)
    cases = common.a_cases(a)
    if kind == "real":
        common.require(not b.resolve().is_relative_to(a.resolve().parent)
                       and not b.resolve().is_relative_to(HERE.parents[1]),
                       "Keep the real reference outside the A directory and reader checkout")
    answer = common.read_json(b)
    answer_cases(answer, cases, standard, kind)
    common.write_record(out, {
        "protocol": common.PROTOCOL, "kind": kind, "freeze_sha256": common.digest(freeze_path),
        "a_sha256": common.digest(a), "b_sha256": common.digest(b), "case_count": len(cases),
        "curator_id": answer["curator_id"], "answer_reviewer_id": answer["answer_reviewer_id"],
        "sealed_at": common.utc_now(),
    })


def sealed(freeze_path, a, seal_path):
    standard = frozen(freeze_path)
    cases = common.a_cases(a)
    seal_record = common.read_json(seal_path)
    common.require(seal_record["protocol"] == common.PROTOCOL and seal_record["kind"] in {"real", "exercise"}
                   and seal_record["freeze_sha256"] == common.digest(freeze_path)
                   and seal_record["a_sha256"] == common.digest(a)
                   and seal_record["case_count"] == len(cases), "A or freeze differs from its seal")
    return standard, cases, seal_record


def read(freeze_path, a, seal_path, log, probe_path=None):
    standard, cases, package = sealed(freeze_path, a, seal_path)
    if package["kind"] == "real":
        probe = common.read_json(probe_path) if probe_path else None
        common.require(probe is not None and probe["protocol"] == common.PROTOCOL
                       and probe["outcome"] in ("denied", "unmounted_or_missing")
                       and probe["probed_at"] >= package["sealed_at"],
                       "A real reader needs its post-seal isolation probe before reading")
    body = reader.render_a({"cases": list(cases.values())})
    context_id, _, _ = call_reader(standard["execution"], body, log, reader.SCHEMA)
    print(json.dumps({"context_id": context_id, "execution": standard["execution"]}, ensure_ascii=False))


def classified(cases, facts, standard):
    result = classifier.classify_package({"cases": list(cases.values())}, facts)
    keyed = common.index(result, "case_id", "predictions")
    for case in result:
        common.require(case["decision_version"] == standard["decision_version"]
                       and case["mechanism_namespace"] == standard["mechanism_namespace"],
                       "Predictions use the wrong catalog or decision version")
        actions = common.index(case["actions"], "id", "predicted actions")
        common.relationships(actions)
        for action in actions.values():
            common.verdict(action, standard)
            common.prediction_resolution(action)
    return keyed


def context_check(context, package, probe, standard):
    common.verify_context(context, package, probe, standard)
    if probe is not None:
        common.require(context.get("probe_sha256") == hashlib.sha256(common.record_bytes(probe)).hexdigest(),
                       "The execution context does not bind its recorded probe")


def capture(freeze_path, a, seal_path, log, context_path, out, probe_path=None):
    standard, cases, package = sealed(freeze_path, a, seal_path)
    context = common.read_json(context_path)
    probe = common.read_json(probe_path) if probe_path else None
    context_check(context, package, probe, standard)
    context_id, facts, support, issues, notes = reader.decode_log(log, {"cases": list(cases.values())})
    common.require(context_id == context["context_id"], "Reader context differs from the raw log")
    result = classified(cases, facts, standard)
    common.write_record(out, {
        "protocol": common.PROTOCOL, "seal_sha256": common.digest(seal_path), "context": context,
        "probe": probe, "facts": facts, "predictions": result, "supporting_operations": support,
        "reader_issues": issues, "readback": notes, "log_sha256": common.digest(log),
        "captured_at": common.utc_now(),
    })


def pair(freeze_path, a, seal_path, run1, run2):
    standard, cases, package = sealed(freeze_path, a, seal_path)
    runs = [common.read_json(path) for path in (run1, run2)]
    first, second = runs
    common.require(first["context"]["context_id"] != second["context"]["context_id"]
                   and package["sealed_at"] <= first["captured_at"] <= second["captured_at"],
                   "Two fresh contexts must be captured in order after the seal")
    for run in runs:
        common.require(run["protocol"] == common.PROTOCOL
                       and run["seal_sha256"] == common.digest(seal_path),
                       "A capture does not belong to this sealed A")
        context_check(run["context"], package, run["probe"], standard)
        common.require(run["predictions"] == classified(cases, run["facts"], standard),
                       "A capture differs from the frozen classifier replay")
    if package["kind"] == "real":
        common.require(first["context"]["probe_sha256"] != second["context"]["probe_sha256"]
                       and first["captured_at"] <= second["probe"]["probed_at"],
                       "The second context needs a fresh isolation probe after the first capture")
    return standard, cases, package, runs


def lock(freeze_path, a, seal_path, run1, run2, out):
    pair(freeze_path, a, seal_path, run1, run2)
    common.write_record(out, {"protocol": common.PROTOCOL, "locked_at": common.utc_now(),
                              "seal_sha256": common.digest(seal_path),
                              "run_sha256": [common.digest(path) for path in (run1, run2)]})


def score(freeze_path, a, seal_path, run1, run2, lock_path, b, review_path, out):
    standard, cases, package, runs = pair(freeze_path, a, seal_path, run1, run2)
    lock_record = common.read_json(lock_path)
    run_hashes = [common.digest(path) for path in (run1, run2)]
    common.require(lock_record["protocol"] == common.PROTOCOL
                   and lock_record["seal_sha256"] == common.digest(seal_path)
                   and lock_record["run_sha256"] == run_hashes
                   and lock_record["locked_at"] >= runs[-1]["captured_at"],
                   "Both predictions must match the lock before accessing B")
    common.require(common.digest(b) == package["b_sha256"], "B differs from its seal")
    answers = answer_cases(common.read_json(b), cases, standard, package["kind"])
    review = common.read_json(review_path)
    common.require(review["lock_sha256"] == common.digest(lock_path)
                   and review["answer_sha256"] == package["b_sha256"]
                   and common.nonempty(review.get("judge_id"))
                   and review["judge_id"] not in {run["context"]["executor_id"] for run in runs},
                   "The judge must bind the exact answers and both locked predictions")
    reviews = common.index(review["runs"], "run_sha256", "judge runs")
    common.require(reviews.keys() == set(run_hashes), "The judge must review both runs")
    graded = []
    for run_hash, run in zip(run_hashes, runs, strict=True):
        judged = common.index(reviews[run_hash]["cases"], "case_id", "judge cases")
        common.require(judged.keys() == cases.keys(), "The judge must review every case")
        items = [common.grade_case(run["predictions"][key], answers[key], judged[key], standard)
                 for key in sorted(cases)]
        graded.append({"run_sha256": run_hash, "metrics": common.summarize(items, standard), "cases": items})
    scope = "real_with_external_custody_attestation" if package["kind"] == "real" else "exercise_only"
    common.write_record(out, {
        "protocol": common.PROTOCOL, "scope": scope, "mechanism_namespace": classifier.NAMESPACE,
        "decision_version": classifier.DECISION_VERSION, "catalog_version": standard["catalog_version"],
        "lock_sha256": common.digest(lock_path), "answer_sha256": package["b_sha256"],
        "review_sha256": common.digest(review_path), "runs": graded,
        "stability": common.compare_runs(graded, review),
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add(function, fields, name=None):
        command = sub.add_parser(name or function.__name__)
        for field in fields.split():
            command.add_argument(field, type=Path)
        command.set_defaults(function=function)
        return command

    add(freeze, "out")
    add(frozen, "path", "check-freeze")
    add(seal, "freeze_path a b out").add_argument("--kind", required=True, choices=("real", "exercise"))
    add(common.probe, "sentinel out")
    add(read, "freeze_path a seal_path log").add_argument("--probe", dest="probe_path", type=Path)
    add(capture, "freeze_path a seal_path log context_path out").add_argument("--probe", dest="probe_path", type=Path)
    add(lock, "freeze_path a seal_path run1 run2 out")
    add(score, "freeze_path a seal_path run1 run2 lock_path b review_path out")
    args = vars(parser.parse_args())
    function = args.pop("function")
    args.pop("command")
    try:
        function(**args)
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.exit(2, f"MECH-v0.4 evaluation rejected: {error}\n")


if __name__ == "__main__":
    main()
