"""Seal and score classification-only evaluation without granting access to answers."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent
PROTOCOL = "classification_only/0.2"
ARTIFACTS = ("catalog.json", "classify.py", "evaluate.py", "WORKFLOW.md")
ROLES = ("primary", "independent", "downstream")
LABEL_FIELDS = {"leaf": "pattern_id", "parent": "parent_id", "outside": "outside_reason"}
OUTSIDE_REASONS = ("compliant", "inapplicable", "outside_catalog")
FAILURES = (
    "material_understanding", "class_definition", "rule_execution",
    "insufficient_evidence", "sample_or_answer", "isolation",
)


def require(yes, message):
    if not yes:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_digest(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def read_json(path):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result

    def invalid_number(value):
        raise ValueError(f"Invalid JSON number: {value}")

    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      object_pairs_hook=unique_pairs, parse_constant=invalid_number)


def record_bytes(record):
    return (json.dumps(record, ensure_ascii=False, sort_keys=True,
                       allow_nan=False, indent=2) + "\n").encode("utf-8")


def write_record(path, record):
    with Path(path).open("xb") as output:
        output.write(record_bytes(record))


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def index(rows, key, section):
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows),
            f"Expected an array of objects for {section}")
    result = {}
    for row in rows:
        val = row.get(key)
        require(nonempty(val) and val not in result, f"Missing or duplicate {key} in {section}")
        result[val] = row
    return result


def artifact_digest(name):
    candidate = (ROOT / name).resolve()
    require(not Path(name).is_absolute() and candidate.is_relative_to(ROOT),
            "A frozen artifact must be relative to the classification directory")
    return digest(candidate)


def freeze(config, exposures, out, artifact=()):
    execution = read_json(config)
    require(isinstance(execution, dict)
            and all(nonempty(execution.get(key)) for key in ("model", "prompt"))
            and isinstance(execution.get("tools"), (list, dict)), "Record model, prompt and tools")
    lineage = read_json(exposures)
    require(isinstance(lineage, list) and all(valid_lineage(x) for x in lineage),
            "Exposure manifest must list namespaced lineage keys")
    catalog = read_json(ROOT / "catalog.json")
    record = {
        "protocol": PROTOCOL,
        "execution": execution,
        "config_sha256": digest(config),
        "exposure_manifest_sha256": digest(exposures),
        "development_lineage": sorted(set(lineage)),
        "catalog_version": catalog["version"],
        "parents": {key: value["parent"] for key, value in catalog["modes"].items()},
        "artifacts": {name: artifact_digest(name) for name in sorted(set(ARTIFACTS) | set(artifact))},
        "created_at": utc_now(),
    }
    write_record(out, record)


def frozen(path):
    record = read_json(path)
    require(record["protocol"] == PROTOCOL and set(ARTIFACTS) <= set(record["artifacts"]),
            "Wrong evaluation protocol or incomplete freeze")
    require(all(artifact_digest(name) == sha for name, sha in record["artifacts"].items()),
            "A frozen implementation artifact changed")
    return record


def valid_lineage(value):
    return nonempty(value) and bool(re.fullmatch(
        r"(family|event|patch|backport|mirror|defect|answer):\S+", value))


def a_cases(path):
    package = read_json(path)
    require(isinstance(package, dict) and set(package) == {"cases"}, "A must contain only cases")
    cases = index(package["cases"], "case_id", "A cases")
    require(bool(cases), "A needs at least one case")
    for case in cases.values():
        require(set(case) == {"case_id", "sources"}, "A cases contain raw material, not extracted facts or answers")
        sources = index(case["sources"], "id", "sources")
        require(bool(sources), "Every case needs source material")
        for source in sources.values():
            required = {"id", "version", "path", "kind", "text"}
            optional = {"origin", "original_start_line"}
            if source.get("kind") == "runtime":
                optional.update(("build", "call_id"))
            require(required <= set(source) <= required | optional
                    and all(nonempty(source[field]) for field in required - {"id"}),
                    "Invalid A source or source contains answer fields")
            require(all(nonempty(source[name]) for name in ("origin", "build", "call_id")
                        if name in source), "Empty source tracing metadata")
            if "original_start_line" in source:
                require(type(source["original_start_line"]) is int
                        and source["original_start_line"] > 0, "Invalid original line offset")
    return cases


def verdict(action, standard, exact_shape=False):
    status = action["status"]
    field = LABEL_FIELDS.get(status)
    elements = {"status", field} if field else {"status"}
    require(status == "insufficient" or field is not None, "Unknown classification status")
    if exact_shape:
        require(set(action) == elements, "An allowed label contains inconsistent fields")
    else:
        # Outside-catalog defects may retain the closest parent as metadata.
        allow_parent = status == "outside" and action.get("outside_reason") == "outside_catalog"
        extras = (set(LABEL_FIELDS.values()) - elements).intersection(action)
        require(not extras or (allow_parent and extras == {"parent_id"}
                              and action["parent_id"] in standard["parents"].values()),
                "A prediction contains incompatible label fields")
    value = action[field] if field else ""
    valid = {"leaf": standard["parents"], "parent": set(standard["parents"].values()),
             "outside": OUTSIDE_REASONS, "insufficient": ("",)}
    require(isinstance(value, str) and value in valid[status], "Unknown classification label")
    return status, value


def relationships(actions):
    for action in actions.values():
        require(action.get("role") in ROLES, "Unknown action role")
        if action["role"] == "downstream":
            parent = action.get("upstream_id")
            seen = {action["id"]}
            while parent in actions and parent not in seen:
                seen.add(parent)
                ancestor = actions[parent]
                if ancestor["role"] != "downstream":
                    break
                parent = ancestor.get("upstream_id")
            else:
                raise ValueError("A downstream chain needs an upstream root without cycles")
        else:
            require(action.get("upstream_id") is None, "A root has a downstream relationship")


def b_cases(answer, cases, standard, kind):
    require(all(nonempty(answer.get(key)) for key in ("curator_id", "answer_reviewer_id", "curation_notes")),
            "B needs custody, independent answer review and curation notes")
    require(answer["curator_id"] != answer["answer_reviewer_id"], "The curator cannot attest their own answer review")
    records = index(answer["cases"], "case_id", "B cases")
    require(set(records) == set(cases), "A and B case inventories differ")
    excluded = set(standard["development_lineage"])
    require(kind != "real" or excluded, "Independent evaluation needs a development exposure manifest")
    owners = {}
    for case in records.values():
        require(all(nonempty(case.get(key)) for key in ("family_id", "operator",
                     "exposure_review", "source_view_review")), "Record B lineage, source view and exposure review")
        lineage = case["lineage"]
        family_key = f"family:{case['family_id']}"
        require(isinstance(lineage, list) and all(valid_lineage(key) for key in lineage)
                and family_key in lineage and any(key.startswith("event:") for key in lineage),
                "A case needs an event identity and its family identity")
        require(not excluded.intersection(lineage), "An evaluation case overlaps development")
        for key in lineage:
            require(owners.setdefault(key, case["family_id"]) == case["family_id"],
                    "Shared event, defect or answer material crosses family boundaries")
        actions = index(case["actions"], "id", "B actions")
        require(bool(actions), "An answer must declare an expected action or an explicit insufficient verdict")
        relationships(actions)
        for action in actions.values():
            allowed = action["allowed"]
            require(isinstance(allowed, list) and allowed, "An answer needs at least one acceptable verdict")
            for label in allowed:
                verdict(label, standard, exact_shape=True)
            require(nonempty(action.get("rationale")) and nonempty(action.get("near_neighbor"))
                    and isinstance(action.get("decisive_facts"), list), "Record answer facts and nearest boundary")
    return records


def seal(freeze_path, a_path, b_path, out, kind):
    require(kind in ("exercise", "real"), "Unknown evaluation scope")
    standard = frozen(freeze_path)
    cases = a_cases(a_path)
    answer = read_json(b_path)
    b_cases(answer, cases, standard, kind)
    write_record(out, {
        "protocol": PROTOCOL, "kind": kind, "freeze_sha256": digest(freeze_path),
        "a_sha256": digest(a_path), "b_sha256": digest(b_path), "case_count": len(cases),
        "curator_id": answer["curator_id"], "answer_reviewer_id": answer["answer_reviewer_id"],
        "sealed_at": utc_now(),
    })


def load_a(freeze_path, a_path, seal_path):
    standard = frozen(freeze_path)
    cases = a_cases(a_path)
    package = read_json(seal_path)
    require(package["protocol"] == PROTOCOL and package["kind"] in ("exercise", "real")
            and package["freeze_sha256"] == digest(freeze_path)
            and package["a_sha256"] == digest(a_path) and package["case_count"] == len(cases),
            "A or the evaluation freeze differs from its seal")
    return standard, cases, package


def probe(sentinel, out):
    try:
        with Path(sentinel).open("rb"):
            outcome = "readable"
    except PermissionError:
        outcome = "denied"
    except FileNotFoundError:
        outcome = "unmounted_or_missing"
    subject = hashlib.sha256(str(Path(sentinel).absolute()).encode("utf-8")).hexdigest()
    write_record(out, {"protocol": PROTOCOL, "outcome": outcome, "sentinel_path_sha256": subject,
                       "probed_at": utc_now()})


def verify_context(context, package, witness_probe, standard):
    require(all(nonempty(context.get(key)) for key in ("context_id", "executor_id")),
            "Each run needs an execution context and executor")
    if package["kind"] == "exercise":
        return
    require(context.get("execution") == standard["execution"],
            "The witnessed execution settings differ from the freeze")
    require(nonempty(context.get("witness_id"))
            and context["witness_id"] != context["executor_id"]
            and context["executor_id"] not in (package["curator_id"], package["answer_reviewer_id"])
            and nonempty(context.get("isolation_mechanism"))
            and all(context.get(key) is True for key in ("sentinel_in_custody",
                                                        "only_approved_inputs", "fresh_context",
                                                        "no_prior_predictions")),
            "Independent custody and access must be externally witnessed for each real run")
    require(witness_probe is not None and witness_probe["protocol"] == PROTOCOL
            and witness_probe["outcome"] in ("denied", "unmounted_or_missing")
            and witness_probe["probed_at"] >= package["sealed_at"],
            "A real run needs its own post-seal denied or unmounted sentinel probe")


def verify_results(predictions, fact_packets, cases, standard):
    if __package__:
        from .classify import classify
    else:
        from classify import classify

    catalog = read_json(ROOT / "catalog.json")
    results = index(predictions, "case_id", "predictions")
    packets = index(fact_packets, "case_id", "extracted facts")
    require(set(results) == set(packets) == set(cases), "A, facts and predictions inventories differ")
    for case_id, result in results.items():
        require(result["catalog_version"] == standard["catalog_version"]
                and result["case_sha256"] == canonical_digest(cases[case_id])
                and result["facts_sha256"] == canonical_digest(packets[case_id]),
                "A prediction differs from its frozen input or facts")
        require(classify(cases[case_id], packets[case_id], catalog) == result,
                "Prediction differs from the replay of the frozen classification rules")
        actions = index(result["actions"], "id", "predicted actions")
        relationships(actions)
        for action in actions.values():
            verdict(action, standard)
    return results


def capture(freeze_path, a_path, seal_path, results, context_path, facts, log, out, probe_path=None):
    standard, cases, package = load_a(freeze_path, a_path, seal_path)
    context = read_json(context_path)
    witness_probe = read_json(probe_path) if probe_path is not None else None
    if witness_probe is not None:
        require(context.get("probe_sha256") == digest(probe_path)
                == hashlib.sha256(record_bytes(witness_probe)).hexdigest(),
                "Isolation statement does not match a recorded probe")
    verify_context(context, package, witness_probe, standard)
    predictions, packets = read_json(results), read_json(facts)
    verify_results(predictions, packets, cases, standard)
    require(Path(log).stat().st_size > 0, "Keep the actual execution log")
    write_record(out, {
        "protocol": PROTOCOL, "seal_sha256": digest(seal_path), "context": context,
        "probe": witness_probe, "predictions": predictions, "facts": packets,
        "artifacts": {"results_sha256": digest(results), "context_sha256": digest(context_path),
                      "facts_sha256": digest(facts), "log_sha256": digest(log)},
        "captured_at": utc_now(),
    })


def paired(freeze_path, a_path, seal_path, run1, run2):
    standard, cases, package = load_a(freeze_path, a_path, seal_path)
    runs = [read_json(path) for path in (run1, run2)]
    require(runs[0]["context"]["context_id"] != runs[1]["context"]["context_id"],
            "Two runs cannot share one execution context")
    require(runs[0]["captured_at"] <= runs[1]["captured_at"], "Provide runs in capture order")
    if package["kind"] == "real":
        require(runs[0]["context"]["probe_sha256"] != runs[1]["context"]["probe_sha256"]
                and runs[0]["captured_at"] <= runs[1]["probe"]["probed_at"],
                "The second run needs a new probe in its fresh context after the first capture")
    predictions = []
    for run in runs:
        require(run["protocol"] == PROTOCOL and run["seal_sha256"] == digest(seal_path),
                "Predictions do not belong to this sealed A")
        verify_context(run["context"], package, run["probe"], standard)
        if run["probe"] is not None:
            require(run["context"].get("probe_sha256") ==
                    hashlib.sha256(record_bytes(run["probe"])).hexdigest(),
                    "The captured probe changed")
        predictions.append(verify_results(run["predictions"], run["facts"], cases, standard))
    return standard, cases, package, runs, predictions


def lock(freeze_path, a_path, seal_path, run1, run2, out):
    paired(freeze_path, a_path, seal_path, run1, run2)
    write_record(out, {"protocol": PROTOCOL, "seal_sha256": digest(seal_path),
                       "run_sha256": [digest(path) for path in (run1, run2)], "locked_at": utc_now()})


def label_text(label):
    return ":".join(label).rstrip(":")


def grade_case(result, answer, review, standard):
    predicted = index(result["actions"], "id", "predicted actions")
    expected = index(answer["actions"], "id", "expected actions")
    entries = index(review["actions"], "prediction_id", "fact-review actions")
    require(set(entries) == set(predicted), "Judge must review every predicted action")
    mapping = {key: entry["expected_id"] for key, entry in entries.items()}
    matched = [item for item in mapping.values() if item is not None]
    require(set(matched) <= set(expected) and len(set(matched)) == len(matched),
            "Each prediction matches one answer action; additional claims are marked unmatched")
    rows = []
    for key, action in predicted.items():
        entry = entries[key]
        require(type(entry.get("facts_supported")) is bool and nonempty(entry.get("rationale"))
                and isinstance(entry.get("failure_causes"), list)
                and all(cause in FAILURES for cause in entry["failure_causes"]),
                "Judge each action against A and record failure attribution or an empty list")
        actual = verdict(action, standard)
        expected_id = mapping[key]
        allowed = []
        relationship = False
        double_count = entry.get("double_count") is True
        if expected_id is not None:
            gold = expected[expected_id]
            allowed = [verdict(label, standard) for label in gold["allowed"]]
            relationship = (action["role"] == gold["role"]
                            and mapping.get(action.get("upstream_id")) == gold.get("upstream_id"))
            double_count = double_count or (gold["role"] == "downstream" and action["role"] != "downstream")
        label_correct = actual in allowed
        strict = label_correct and relationship and entry["facts_supported"] and not double_count
        require(strict or entry["failure_causes"], "Judge must attribute each failed prediction")
        rows.append({
            "prediction_id": key, "expected_id": expected_id, "actual": label_text(actual),
            "expected": [label_text(item) for item in allowed], "label_correct": label_correct,
            "facts_supported": entry["facts_supported"], "relationship_correct": relationship,
            "strict": strict, "rationale": entry["rationale"], "failure_causes": entry["failure_causes"],
            "double_count": double_count,
            "partial_parent": actual[0] == "parent" and not label_correct and any(
                want[0] == "leaf" and standard["parents"][want[1]] == actual[1] for want in allowed),
            "over_abstention": actual[0] == "insufficient" and bool(allowed) and not label_correct,
            "unsupported_attribution": (actual[0] in ("leaf", "parent") and not entry["facts_supported"]),
        })
    missing = set(expected) - set(matched)
    omissions = review.get("omissions", {})
    require(isinstance(omissions, dict) and set(omissions) == missing
            and all(nonempty(item.get("rationale")) and item.get("failure_cause") in FAILURES
                    for item in omissions.values()), "Judge must document each omitted expected action")
    family = answer["family_id"]
    signature = sorted(
        (mapping[key] or "", label_text(verdict(action, standard)), action["role"],
         mapping.get(action.get("upstream_id")) or "") for key, action in predicted.items()
    )
    return {
        "case_id": result["case_id"], "family_id": family, "operator": answer["operator"],
        "strict": not missing and all(item["strict"] for item in rows),
        "actions": rows, "omissions": omissions,
        "expected_verdicts": {
            action_id: [label_text(verdict(label, standard)) for label in action["allowed"]]
            for action_id, action in expected.items()
        },
        "missing_independent_actions": sum(expected[key]["role"] == "independent" for key in missing),
        "signature": signature,
    }


def summarize(cases, standard):
    families, cross_op = defaultdict(list), defaultdict(set)
    confusion, metric, outcomes, failures = Counter(), Counter(), Counter(), Counter()
    denominators, eligible_families = Counter(), defaultdict(set)
    for case in cases:
        families[case["family_id"]].append(case["strict"])
        metric["missing_actions"] += len(case["omissions"])
        metric["missing_independent_actions"] += case["missing_independent_actions"]
        failures.update(item["failure_cause"] for item in case["omissions"].values())
        for labels in case["expected_verdicts"].values():
            denominators[labels[0]] += 1
            for label in labels:
                if label.startswith("leaf:"):
                    eligible_families[label.split(":", 1)[1]].add(case["family_id"])
        for key in case["omissions"]:
            confusion[(case["expected_verdicts"][key][0], "missing_action")] += 1
        for row in case["actions"]:
            actual = row["actual"]
            expected = row["expected"][0] if row["expected"] else "unexpected_action"
            confusion[(expected, actual)] += 1
            outcomes[actual] += row["strict"]
            failures.update(row["failure_causes"])
            metric.update(key for key in ("strict", "label_correct", "facts_supported", "double_count",
                                           "partial_parent", "over_abstention", "unsupported_attribution") if row[key])
            metric["label_match_with_failed_evidence"] += row["label_correct"] and not row["facts_supported"]
            metric["predicted_actions"] += 1
            metric["unexpected_actions"] += row["expected_id"] is None
            metric["misclassified_actions"] += row["expected_id"] is not None and not row["label_correct"]
            if row["strict"] and actual.startswith("leaf:"):
                cross_op[actual.split(":", 1)[1]].add((case["family_id"], case["operator"]))
    coverage = {}
    for mode in standard["parents"]:
        pairs = cross_op[mode]
        families_for_mode = {family for family, _ in pairs}
        operators = {operator for _, operator in pairs}
        # Distinct families and multiple operators imply at least one pair differs on both.
        coverage[mode] = {
            "eligible_families": len(eligible_families[mode]),
            "supported_families": len(families_for_mode), "operators": sorted(operators),
            "cross_operator_observed": len(families_for_mode) > 1 and len(operators) > 1,
            "status": "observed_in_batch" if pairs else
            ("needs_review" if eligible_families[mode] else "unverified"),
        }
    return {
        "families": len(families),
        "families_strict": sum(all(values) for values in families.values()),
        "cases": len(cases), "case_strict": sum(case["strict"] for case in cases),
        "action_counts": dict(metric), "strict_verdicts": dict(outcomes), "coverage": coverage,
        "expected_verdict_counts": dict(denominators),
        "failure_counts": dict(failures),
        "confusion": [{"expected": wanted, "actual": actual, "count": count}
                      for (wanted, actual), count in sorted(confusion.items())],
    }


def score(freeze_path, a_path, seal_path, run1, run2, lock_path, b_path, review_path, out,
          revision_path=None):
    standard, cases, package, runs, predictions = paired(freeze_path, a_path, seal_path, run1, run2)
    locked = read_json(lock_path)
    run_hashes = [digest(path) for path in (run1, run2)]
    require(locked["protocol"] == PROTOCOL and locked["seal_sha256"] == digest(seal_path)
            and locked["run_sha256"] == run_hashes and locked["locked_at"] >= runs[1]["captured_at"],
            "Both predictions must match the frozen run lock before accessing B")
    require(digest(b_path) == package["b_sha256"], "B differs from the sealed answers")
    answer_document = read_json(b_path)
    answers = b_cases(answer_document, cases, standard, package["kind"])
    answer_hash = package["b_sha256"]
    revision_record = None
    if revision_path is not None:
        revision = read_json(revision_path)
        require(revision["original_sha256"] == answer_hash and nonempty(revision.get("reason"))
                and nonempty(revision.get("reviewer_id"))
                and revision["reviewer_id"] not in {
                    answer_document["curator_id"], *(run["context"]["executor_id"] for run in runs)},
                "An independent reviewer must link and explain an answer correction")
        corrected = b_cases(revision["answer"], cases, standard, package["kind"])
        require(all((corrected[key]["family_id"], set(corrected[key]["lineage"])) ==
                    (answers[key]["family_id"], set(answers[key]["lineage"])) for key in cases),
                "Answer corrections cannot change sample family or lineage")
        answers = corrected
        answer_hash = digest(revision_path)
        revision_record = {field: revision[field] for field in ("original_sha256", "reason", "reviewer_id")}
    review = read_json(review_path)
    require(review["lock_sha256"] == digest(lock_path) and review["answer_sha256"] == answer_hash
            and nonempty(review.get("judge_id"))
            and review["judge_id"] not in {run["context"]["executor_id"] for run in runs},
            "Use an external judge, reviewing the exact lock and B")
    reviews = index(review["runs"], "run_sha256", "judge runs")
    require(set(reviews) == set(run_hashes), "Judge needs both locked predictions")
    graded = []
    for run_hash, predicted in zip(run_hashes, predictions):
        judgement = index(reviews[run_hash]["cases"], "case_id", "judge cases")
        require(set(judgement) == set(cases), "Judge must review every case")
        items = [grade_case(predicted[case_id], answers[case_id], judgement[case_id], standard)
                 for case_id in sorted(cases)]
        graded.append({"run_sha256": run_hash, "metrics": summarize(items, standard), "cases": items})
    stability = []
    for left, right in zip(graded[0]["cases"], graded[1]["cases"]):
        same = left["signature"] == right["signature"]
        stability.append({"case_id": left["case_id"], "family_id": left["family_id"], "same": same,
                          "same_and_both_incorrect": same and not left["strict"] and not right["strict"]})
    write_record(out, {
        "protocol": PROTOCOL, "scope": "real_with_external_custody_attestation"
        if package["kind"] == "real" else "exercise_only",
        "note": "Hashes preserve bytes. Human attestation, not the evaluator, establishes isolation and exposure.",
        "lock_sha256": digest(lock_path), "answer_sha256": answer_hash, "review_sha256": digest(review_path),
        "answer_revision": revision_record,
        "runs": graded, "stability": {
            "cases": stability,
            "same_cases": sum(item["same"] for item in stability),
            "same_and_both_incorrect_cases": sum(item["same_and_both_incorrect"] for item in stability),
        },
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def command(function, *positional):
        child = sub.add_parser(function.__name__)
        for name in positional:
            child.add_argument(name, type=Path)
        child.set_defaults(function=function)
        return child

    command(freeze, "config", "exposures", "out").add_argument("--artifact", action="append", default=[])
    command(seal, "freeze_path", "a_path", "b_path", "out").add_argument(
        "--kind", required=True, choices=("exercise", "real"))
    command(probe, "sentinel", "out")
    command(capture, "freeze_path", "a_path", "seal_path", "results", "context_path", "facts", "log",
            "out").add_argument("--probe", dest="probe_path", type=Path)
    command(lock, "freeze_path", "a_path", "seal_path", "run1", "run2", "out")
    command(score, "freeze_path", "a_path", "seal_path", "run1", "run2", "lock_path", "b_path",
            "review_path", "out").add_argument("--revision", dest="revision_path", type=Path)
    arguments = vars(parser.parse_args())
    function = arguments.pop("function")
    arguments.pop("command")
    try:
        function(**arguments)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(2, f"Evaluation rejected: {error}\n")


if __name__ == "__main__":
    main()

