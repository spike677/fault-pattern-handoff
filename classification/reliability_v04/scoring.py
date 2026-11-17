"""Grade locked action graphs against a separately reviewed reference."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path

from . import graph, reader, workflow


common = workflow.common
SCORE_PROTOCOL = "mech_v04_reliability_score/0.2"
ASSESSMENTS = ("facts_and_version", "concrete_action", "violated_relation", "causal_relation", "anchors_valid")
FAILURES = ("material_understanding", "class_definition", "rule_execution", "insufficient_evidence",
            "sample_or_answer", "isolation")
ROOT_ROLES = {"primary", "independent"}
ANCHOR_ERRORS = {"invalid_anchor", "unknown_source", "invalid_excerpt_line_range", "quote_not_in_source_span",
                 "unpinned_source_cannot_support_this_scope", "runtime_binding_mismatch"}
VERDICTS = ("status", "pattern_id", "parent_id", "outside_reason", "supported_pattern_ids")


def by_id(rows, field):
    return graph.pilot.by_id(rows, field, field)


def review_schema():
    text, obj, array = reader.TEXT, reader.object_schema, reader.array_schema
    failure = {"type": ["string", "null"], "enum": [*FAILURES, None]}
    action = obj({"action_id": text, "expected_id": {"type": ["string", "null"]},
                  **{name: {"type": "boolean"} for name in ASSESSMENTS},
                  "failure_cause": failure, "rationale": text})
    omission = obj({"expected_id": text, "failure_cause": {"enum": list(FAILURES)}, "rationale": text})
    return obj({"cases": array(obj({"case_id": text, "actions": array(action), "omissions": array(omission)}))})


def predicted_actions(case):
    return by_id([node for node in case["nodes"]
                  if node["node_type"] != "supporting_operation" and not node.get("attributed_to")], "action_id")


def mechanism(verdict, allowed):
    return any(all(verdict.get(key) == value for key, value in option.items()) for option in allowed)


def defect_verdict(verdict):
    return verdict["status"] in {"leaf", "parent"} or verdict.get("outside_reason") == "outside_catalog"


def roles_match(expected, actual, mapping, case):
    role_ok = expected["role"] == actual["causal_role"]
    if case.get("root_order_unspecified") and expected["role"] in ROOT_ROLES:
        role_ok = actual["causal_role"] in ROOT_ROLES
    if expected["role"] != "downstream":
        return role_ok
    expected_upstream = expected.get("upstream_ids", [expected.get("upstream_id")])
    actual_upstream = [mapping.get(key) for key in actual.get("upstream_ids", [])]
    return role_ok and set(actual_upstream) == set(expected_upstream)


def grade_action(expected, actual, review, mapping, case):
    expected_root = expected["role"] in ROOT_ROLES
    wants_relation = any(defect_verdict(option) for option in expected["allowed"])
    verdict = actual["verdict"]
    evidence = review["facts_and_version"]
    label = mechanism(verdict, expected["allowed"])
    causal = review["causal_relation"] and roles_match(expected, actual, mapping, case)
    valid_anchors = review["anchors_valid"] and not (ANCHOR_ERRORS & {issue["code"] for issue in verdict["issues"]})
    concrete = review["concrete_action"]
    relation = review["violated_relation"]
    count = actual["independent_count"]
    return {
        "expected_id": expected["id"], "action_id": actual["action_id"],
        "predicted": {key: verdict[key] for key in VERDICTS if key in verdict},
        "allowed": expected["allowed"], "expected_role": expected["role"], "actual_role": actual["causal_role"],
        "facts_and_version": evidence, "concrete_action": concrete, "concrete_eligible": expected["specific_action"] is not None,
        "violated_relation": relation, "relation_eligible": wants_relation, "mode_matches": label,
        "supported_mode": label and evidence and valid_anchors,
        "causal_relation": causal, "anchors_valid": valid_anchors, "root_claimed": count,
        "root_expected": expected_root, "root_correct": expected_root and count == 1 and causal and evidence
        and valid_anchors and concrete and relation,
        "strict": evidence and concrete and (relation or not wants_relation) and label and causal and valid_anchors
        and count == int(expected_root),
        "failure_cause": review["failure_cause"], "rationale": review["rationale"],
    }


def grade_case(expected_case, actual_case, review):
    expected = by_id(expected_case["actions"], "id")
    actual = predicted_actions(actual_case)
    votes = by_id(review["actions"], "action_id")
    omitted = by_id(review["omissions"], "expected_id")
    if votes.keys() != actual.keys():
        raise ValueError(f"{actual_case['case_id']}: judge must cover each predicted action once")
    mapping = {key: vote["expected_id"] for key, vote in votes.items()}
    matched = [key for key in mapping.values() if key is not None]
    if len(set(matched)) != len(matched) or not set(matched) <= expected.keys() or omitted.keys() != expected.keys() - set(matched):
        raise ValueError(f"{actual_case['case_id']}: duplicate match or incomplete reference coverage")
    rows = [grade_action(expected[reference], actual[key], votes[key], mapping, expected_case)
            for key, reference in mapping.items() if reference is not None]
    extras = [{"action_id": key, "root_claimed": actual[key]["independent_count"],
               "verdict": {field: actual[key]["verdict"][field] for field in VERDICTS if field in actual[key]["verdict"]},
               "failure_cause": votes[key]["failure_cause"],
               "rationale": votes[key]["rationale"]} for key, reference in mapping.items() if reference is None]
    missing = [{"expected_id": key, "root_expected": expected[key]["role"] in ROOT_ROLES,
                "concrete_eligible": expected[key]["specific_action"] is not None,
                "relation_eligible": any(defect_verdict(row) for row in expected[key]["allowed"]),
                "allowed": expected[key]["allowed"], **omission} for key, omission in omitted.items()]
    return {"case_id": actual_case["case_id"], "strict": not extras and not missing and all(row["strict"] for row in rows),
            "actions": rows, "extra_actions": extras, "omissions": missing,
            "normal_operations": sum(node["causal_role"] == "support" for node in actual_case["nodes"])}


def summarize(cases):
    rows = [row for case in cases for row in case["actions"]]
    missing = [row for case in cases for row in case["omissions"]]
    extras = [row for case in cases for row in case["extra_actions"]]
    references = rows + missing

    def metric(field, eligible=lambda row: True):
        return {"correct": sum(bool(row.get(field)) for row in references if eligible(row)),
                "eligible": sum(eligible(row) for row in references)}

    def includes(row, **kind):
        return any(all(option.get(key) == value for key, value in kind.items()) for option in row["allowed"])

    anchors = {"valid": sum(row["anchors_valid"] for row in rows), "matched_predictions": len(rows)}
    roots = metric("root_correct", lambda row: row["root_expected"])
    claimed = sum(row["root_claimed"] for row in rows + extras)
    return {
        "strict_cases": {"correct": sum(case["strict"] for case in cases), "eligible": len(cases)},
        "facts_and_version": metric("facts_and_version"),
        "concrete_action": metric("concrete_action", lambda row: row["concrete_eligible"]),
        "violated_relation": metric("violated_relation", lambda row: row["relation_eligible"]),
        "mode_matches": metric("mode_matches"), "supported_mode": metric("supported_mode"),
        "causal_relation": metric("causal_relation"),
        "independent_roots": {**roots, "claimed": claimed, "false_positive": claimed - roots["correct"],
                              "false_negative": roots["eligible"] - roots["correct"]},
        "supported_leaf": metric("supported_mode", lambda row: includes(row, status="leaf")),
        "supported_outside_defect": metric("supported_mode", lambda row: includes(row, outside_reason="outside_catalog")),
        "reasonable_abstention": metric("supported_mode", lambda row: includes(row, status="insufficient")),
        "over_abstention": sum(row["predicted"]["status"] == "insufficient" and not includes(row, status="insufficient")
                               for row in rows),
        "wrong_positive": (sum(defect_verdict(row["predicted"]) and not row["supported_mode"] and not row["facts_and_version"]
                               for row in rows) + sum(defect_verdict(row["verdict"]) for row in extras)),
        "wrong_exclusion": sum(row["predicted"].get("outside_reason") in {"compliant", "inapplicable"}
                               and not row["mode_matches"] for row in rows),
        "anchors": anchors, "unmatched_predictions": len(extras), "omitted_reference_actions": len(missing),
        "failure_causes": dict(Counter(row["failure_cause"] for row in rows + extras + missing if row["failure_cause"])),
    }


def grade_round(answer, graphs, review):
    targets = by_id(answer["cases"], "case_id")
    predicted = by_id(graphs["cases"], "case_id")
    votes = by_id(review["cases"], "case_id")
    if targets.keys() != predicted.keys() or targets.keys() != votes.keys():
        raise ValueError("Reference, graph and independent review must cover the same cases")
    cases = [grade_case(case, predicted[key], votes[key]) for key, case in targets.items()]
    return {"metrics": summarize(cases), "cases": cases}


def grade_input(directory, answer_path, number):
    lock = workflow.verify(directory)
    entry = lock["rounds"][number - 1]
    folder = workflow.round_dir(directory, number, entry["attempt"])
    answer = common.read_json(answer_path)
    graphs = common.read_json(folder / "root_action_graph.json")
    binding = {"round": number, "answer_sha256": common.digest(answer_path), "lock_sha256": common.digest(directory / "lock.json"),
               "graph_sha256": entry["graph_sha256"]}
    return lock, answer, graphs, binding


def score(directory, answer_path, review_paths, out):
    scores = []
    for number, path in enumerate(review_paths, 1):
        lock, reference, graphs, binding = grade_input(directory, answer_path, number)
        review = common.read_json(path)
        reader_ids = {item["context_id"] for item in lock["rounds"]}
        judge = review["judge_id"]
        if any(review.get(key) != value for key, value in binding.items()) or judge in reader_ids or not graph.pilot.nonempty(judge):
            raise ValueError("The separate judge must bind its exact round, reference, graph and lock")
        scores.append({"round": number, "review_sha256": common.digest(path), "judge_id": judge,
                       **grade_round(reference, graphs, review)})
    value = {"protocol": SCORE_PROTOCOL, "scope": "exercise_only", "lock_sha256": common.digest(directory / "lock.json"),
             "answer_sha256": common.digest(answer_path), "rounds": scores}
    common.write_record(out, value)
    return value


def judge_review(directory, answer_path, number, output):
    lock, answer, graphs, binding = grade_input(directory, answer_path, number)
    output.mkdir(parents=True, exist_ok=False)
    schema_path = output / "schema.json"
    common.write_record(schema_path, review_schema())
    a = common.read_json(directory / "A.json")
    properties = ("action_id", "node_type", "description", "scope", "source_location", "context_source_location", "expected_behavior",
                  "observed_behavior", "violated_relation", "mode_ids", "effect_mode_ids", "causal_role",
                  "independent_count", "upstream_ids", "issues", "mechanism_via", "attributed_to")
    brief = []
    for case in graphs["cases"]:
        nodes = []
        for node in case["nodes"]:
            verdict = node["verdict"]
            if verdict is None:
                continue
            facts = [{**fact, "anchors": [{key: value for key, value in anchor.items() if key != "quote"}
                                          for anchor in fact["anchors"]]} for fact in verdict["facts"]]
            nodes.append({**{key: node[key] for key in properties if key in node},
                          "facts": facts, "verdict": {key: value for key, value in verdict.items()
                                                      if key in {*VERDICTS, "issues", "missing"}}})
        brief.append({"case_id": case["case_id"], "nodes": nodes, "relations": case["relations"]})
    prompt = (Path(__file__).with_name("JUDGE.md").read_text(encoding="utf-8") + "\n"
              + json.dumps({"a": a, "b": answer, "predicted": brief}, ensure_ascii=False, separators=(",", ":")))
    execution = common.read_json(directory / "freeze.json")["execution"]
    judge, message, _ = workflow.formal.call_reader(execution, prompt, output / "judge.jsonl", schema_path)
    if judge in {row["context_id"] for row in lock["rounds"]}:
        raise ValueError("Judge must be a separate context")
    review = json.loads(message)
    grade_round(answer, graphs, review)
    common.write_record(output / "review.json", {**binding, "judge_id": judge, **review})


def write_matrix(score_path, out):
    value = common.read_json(score_path)
    with out.open("x", encoding="utf-8", newline="") as stream:
        fields = ("round", "case_id", "expected_id", "action_id", "allowed", "prediction",
                  "mode_supported", "role", "strict", "failure_cause", "rationale")
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        for round_result in value["rounds"]:
            for case in round_result["cases"]:
                prefix = {"round": round_result["round"], "case_id": case["case_id"]}
                for row in case["actions"] + case["omissions"] + case["extra_actions"]:
                    writer.writerow({**prefix, "expected_id": row.get("expected_id"), "action_id": row.get("action_id"),
                                     "allowed": json.dumps(row.get("allowed"), ensure_ascii=False),
                                     "prediction": json.dumps(row.get("predicted", row.get("verdict")), ensure_ascii=False),
                                     "mode_supported": row.get("supported_mode", False), "role": row.get("actual_role"),
                                     "strict": row.get("strict", False), "failure_cause": row["failure_cause"],
                                     "rationale": row["rationale"]})


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    judge = commands.add_parser("judge")
    score_parser = commands.add_parser("score")
    for parser in (judge, score_parser):
        parser.add_argument("directory", type=Path)
        parser.add_argument("answer", type=Path)
    judge.add_argument("round", type=int, choices=workflow.ROUNDS)
    judge.add_argument("output", type=Path)
    score_parser.add_argument("output", type=Path)
    score_parser.add_argument("reviews", type=Path, nargs=2)
    matrix = commands.add_parser("matrix")
    matrix.add_argument("score", type=Path)
    matrix.add_argument("output", type=Path)
    args = cli.parse_args()
    if args.command == "judge":
        judge_review(args.directory.resolve(), args.answer.resolve(), args.round, args.output.resolve())
    elif args.command == "score":
        result = score(args.directory.resolve(), args.answer.resolve(), args.reviews, args.output)
        print(json.dumps([row["metrics"] for row in result["rounds"]], ensure_ascii=False, indent=2))
    else:
        write_matrix(args.score, args.output)


if __name__ == "__main__":
    main()
