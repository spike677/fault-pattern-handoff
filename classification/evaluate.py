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
PROTOCOL = "classification_only/0.3.1"
DECISION_VERSION = "0.3.1"
ARTIFACTS = ("catalog.json", "classify.py", "evaluate.py", "WORKFLOW.md")
ROOT_ROLES = ("primary", "independent")
ROLES = (*ROOT_ROLES, "downstream", "unknown")
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


def parent_ancestors(parent, hierarchy):
    ancestors = set()
    while parent in hierarchy:
        parent = hierarchy[parent]
        require(parent not in ancestors, "The parent hierarchy contains a cycle")
        ancestors.add(parent)
    return ancestors


def catalog_standard(catalog):
    parents = {mode: card["parent"] for mode, card in catalog["modes"].items()}
    parent_ids = sorted(catalog["parents"])
    hierarchy = catalog["parent_hierarchy"]
    combinations = catalog["combinations"]
    require(set(parents.values()) | set(hierarchy) | set(hierarchy.values()) <= set(parent_ids),
            "Every parent in a mode or hierarchy must be declared")
    for parent in hierarchy:
        parent_ancestors(parent, hierarchy)
    return {
        "catalog_version": catalog["version"],
        "mechanism_namespace": f"MECH-v{catalog['version']}",
        "parents": parents,
        "parent_ids": parent_ids,
        "parent_hierarchy": hierarchy,
        "combinations": combinations,
    }


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
        **catalog_standard(catalog),
        "artifacts": {name: artifact_digest(name) for name in sorted(set(ARTIFACTS) | set(artifact))},
        "created_at": utc_now(),
    }
    write_record(out, record)


def frozen(path):
    record = read_json(path)
    require(record["protocol"] == PROTOCOL and set(ARTIFACTS) <= set(record["artifacts"])
            and record["mechanism_namespace"] == mechanism_namespace(record),
            "Wrong evaluation protocol or incomplete freeze")
    require(all(artifact_digest(name) == sha for name, sha in record["artifacts"].items()),
            "A frozen implementation artifact changed")
    catalog = catalog_standard(read_json(ROOT / "catalog.json"))
    require(all(record.get(key) == value for key, value in catalog.items()),
            "Frozen label metadata differs from its catalog")
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


def mechanism_namespace(standard):
    return f"MECH-v{standard['catalog_version']}"


def verdict(action, standard, exact_shape=False):
    require(isinstance(action, dict), "A verdict must be an object")
    status = action["status"]
    field = LABEL_FIELDS.get(status)
    elements = {"status", field} if field else {"status"}
    require(status == "insufficient" or field is not None, "Unknown classification status")
    components = ()
    if "supported_pattern_ids" in action:
        ids = action["supported_pattern_ids"]
        require(status == "parent" and isinstance(ids, list)
                and all(isinstance(mode, str) for mode in ids)
                and len(ids) == len(set(ids))
                and any(rule["parent"] == action.get("parent_id") and set(rule["modes"]) == set(ids)
                        for rule in standard["combinations"]),
                "Combination must match a compatible mode set and parent declared in the catalog")
        components = tuple(sorted(ids))
        elements.add("supported_pattern_ids")
    if exact_shape:
        require(set(action) == elements, "An allowed label contains inconsistent fields")
    else:
        # Outside-catalog defects may retain the closest parent as metadata.
        allow_parent = status == "outside" and action.get("outside_reason") == "outside_catalog"
        extras = (set(LABEL_FIELDS.values()) - elements).intersection(action)
        require(not extras or (allow_parent and extras == {"parent_id"}
                              and action["parent_id"] in standard["parent_ids"]),
                "A prediction contains incompatible label fields")
        require((action.get("combination") == "compatible" if components
                 else "combination" not in action and "supported_pattern_refs" not in action),
                "Combination metadata must belong to a compatible parent")
        if components:
            refs = [f"{mechanism_namespace(standard)}:{mode}" for mode in action["supported_pattern_ids"]]
            require(action.get("supported_pattern_refs") == refs, "Combination references must match its attributes")
    value = action[field] if field else ""
    valid = {"leaf": standard["parents"], "parent": standard["parent_ids"],
             "outside": OUTSIDE_REASONS, "insufficient": ("",)}
    require(isinstance(value, str) and value in valid[status], "Unknown classification label")
    if not exact_shape and status == "leaf":
        require(action.get("pattern_ref") == f"{mechanism_namespace(standard)}:{value}",
                "The leaf reference must match its catalog version")
    if not exact_shape and "parent_id" in action:
        require(action.get("parent_ref") == f"{mechanism_namespace(standard)}:{action['parent_id']}",
                "The parent reference must match its catalog version")
    return status, value, components


def partial_parent(actual, wanted, standard):
    if actual[0] != "parent" or actual[2]:
        return False
    hierarchy = standard["parent_hierarchy"]
    if wanted[0] == "leaf":
        parent = standard["parents"][wanted[1]]
        return actual[1] == parent or actual[1] in parent_ancestors(parent, hierarchy)
    return wanted[0] == "parent" and actual[1] in parent_ancestors(wanted[1], hierarchy)


def answer_verdicts(action, standard):
    choices = action.get("allowed")
    require(isinstance(choices, list) and choices, "An answer needs at least one acceptable verdict")
    allowed = {verdict(label, standard, exact_shape=True) for label in choices}
    require(len(allowed) == len(choices), "Allowed verdicts must be distinct")
    if "primary" in action:
        primary = verdict(action["primary"], standard, exact_shape=True)
        require(primary in allowed, "The primary verdict must be in the allowed set")
    else:
        require(len(allowed) == 1, "Multiple allowed verdicts need an explicit primary verdict")
        primary = next(iter(allowed))
    return primary, sorted(allowed)


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
                raise ValueError("A downstream chain needs an upstream action without cycles")
        else:
            require(action.get("upstream_id") is None, "Only a downstream action can reference an upstream action")


def positive_verdict(action):
    return action["status"] in ("leaf", "parent") or action.get("outside_reason") == "outside_catalog"


def prediction_resolution(action):
    resolution = action.get("action_resolution")
    independent = action.get("count_as_independent")
    require(resolution in ("supported", "unresolved") and type(independent) is bool,
            "A prediction must record the implementation action resolution and independent defect count")
    require(independent == (action["role"] in ROOT_ROLES and resolution == "supported"
                            and positive_verdict(action)),
            "Independent defect count disagrees with the resolution, role, or verdict")
    return resolution, independent


def unordered_root_order(case, actions):
    unordered = case.get("root_order_unspecified", False)
    require(type(unordered) is bool, "The unordered-root flag must be boolean")
    if unordered:
        require(nonempty(case.get("root_order_rationale"))
                and sum(action["role"] in ROOT_ROLES for action in actions.values()) >= 2,
                "Unordered roots need at least two expected roots and an evidence rationale")
    return unordered


def known_action(action):
    require("specific_action" in action
            and (action["specific_action"] is None or nonempty(action["specific_action"])),
            "An answer must describe the specific action or set it to null")
    return action["specific_action"] is not None


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
        unordered_root_order(case, actions)
        for action in actions.values():
            answer_verdicts(action, standard)
            known_action(action)
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
    require(context.get("execution") == standard["execution"],
            "The execution settings differ from the freeze")
    if package["kind"] == "exercise":
        return
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
                and result.get("decision_version") == DECISION_VERSION
                and result["case_sha256"] == canonical_digest(cases[case_id])
                and result["facts_sha256"] == canonical_digest(packets[case_id]),
                "A prediction differs from its frozen decision version, input or facts")
        require(classify(cases[case_id], packets[case_id], catalog) == result,
                "Prediction differs from the replay of the frozen classification rules")
        actions = index(result["actions"], "id", "predicted actions")
        relationships(actions)
        for action in actions.values():
            verdict(action, standard)
            prediction_resolution(action)
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


def label_text(label, standard):
    status, value, components = label
    namespace = mechanism_namespace(standard)
    if status in ("leaf", "parent"):
        text = f"{status}:{namespace}:{value}"
        if components:
            text += "[" + ",".join(f"{namespace}:{mode}" for mode in components) + "]"
        return text
    return f"{status}:{value}" if value else status


def grade_case(result, answer, review, standard):
    predicted = index(result["actions"], "id", "predicted actions")
    expected = index(answer["actions"], "id", "expected actions")
    unordered = unordered_root_order(answer, expected)
    gold_verdicts = {key: answer_verdicts(action, standard) for key, action in expected.items()}
    known = {key for key, action in expected.items() if known_action(action)}
    independent_expected = {key for key in known if expected[key]["role"] in ROOT_ROLES
                            and gold_verdicts[key][0][:2] not in {
                                ("insufficient", ""), ("outside", "compliant"), ("outside", "inapplicable")}}
    entries = index(review["actions"], "prediction_id", "fact-review actions")
    require(set(entries) == set(predicted), "Judge must review every predicted action")
    mapping = {key: entry["expected_id"] for key, entry in entries.items()}
    matched = [item for item in mapping.values() if item is not None]
    require(set(matched) <= set(expected) and len(set(matched)) == len(matched),
            "Each prediction matches one answer action; additional claims are marked unmatched")
    rows = []
    roots_confirmed = set()
    for key, action in predicted.items():
        entry = entries[key]
        require(type(entry.get("facts_supported")) is bool and nonempty(entry.get("rationale"))
                and isinstance(entry.get("failure_causes"), list)
                and all(cause in FAILURES for cause in entry["failure_causes"]),
                "Judge each action against A and record failure attribution or an empty list")
        actual = verdict(action, standard)
        resolution, independent = prediction_resolution(action)
        expected_id = mapping[key]
        action_correct = entry.get("action_correct")
        require(type(action_correct) is bool and nonempty(entry.get("action_rationale"))
                and (expected_id is not None or not action_correct),
                "Judge must review the specific action and explain each decision")
        primary, allowed = gold_verdicts.get(expected_id, (None, []))
        expected_role = None
        role_exact = False
        relationship = False
        double_count = entry.get("double_count") is True
        upstream = mapping.get(action.get("upstream_id"))
        if expected_id is not None:
            gold = expected[expected_id]
            expected_role = gold["role"]
            edge_matches = upstream == gold.get("upstream_id")
            role_exact = action["role"] == expected_role and edge_matches
            unordered_match = unordered and expected_role in ROOT_ROLES and action["role"] in ROOT_ROLES
            relationship = role_exact or (unordered_match and edge_matches)
        label_correct = actual in allowed
        primary_hit = actual == primary
        alternative_hit = label_correct and not primary_hit
        mechanism_correct = label_correct and entry["facts_supported"]
        strict = mechanism_correct and action_correct and relationship and not double_count
        require(strict or entry["failure_causes"], "Judge must attribute each failed prediction")
        counted = "not_claimed"
        if independent:
            if expected_id in independent_expected and action_correct and relationship and not double_count:
                counted = "true_positive"
                roots_confirmed.add(expected_id)
            else:
                counted = "false_positive"
        elif expected_id in independent_expected:
            counted = "false_negative"
        rows.append({
            "prediction_id": key, "expected_id": expected_id, "actual": label_text(actual, standard),
            "primary_expected": label_text(primary, standard) if primary is not None else None,
            "expected": [label_text(item, standard) for item in allowed], "label_correct": label_correct,
            "primary_label_hit": primary_hit, "accepted_alternative_label": alternative_hit,
            "facts_supported": entry["facts_supported"], "relationship_correct": relationship,
            "mechanism_correct": mechanism_correct, "role_exact": role_exact,
            "action_correct": action_correct, "action_rationale": entry["action_rationale"],
            "independent_count_outcome": counted, "upstream_expected_id": upstream,
            "strict": strict, "rationale": entry["rationale"], "failure_causes": entry["failure_causes"],
            "double_count": double_count,
            "predicted_role": action["role"], "expected_role": expected_role,
            "action_resolution": resolution, "count_as_independent": independent,
            "unresolved_implementation_action": resolution == "unresolved" and positive_verdict(action),
            "partial_parent": not label_correct and any(partial_parent(actual, want, standard) for want in allowed),
            "over_abstention": actual[0] == "insufficient" and bool(allowed) and not label_correct,
            "unsupported_attribution": (actual[0] in ("leaf", "parent") and not entry["facts_supported"]),
        })
    missing = set(expected) - set(matched)
    omissions = review.get("omissions", {})
    require(isinstance(omissions, dict) and set(omissions) == missing
            and all(nonempty(item.get("rationale")) and item.get("failure_cause") in FAILURES
                    for item in omissions.values()), "Judge must document each omitted expected action")
    omissions = {key: {**entry, "independent_count_outcome":
                       "false_negative" if key in independent_expected else "not_claimed"}
                 for key, entry in omissions.items()}
    signature = sorted(
        (mapping[key] or "", label_text(verdict(action, standard), standard), action["role"],
         mapping.get(action.get("upstream_id")) or "", *prediction_resolution(action))
        for key, action in predicted.items()
    )
    causal_signature = sorted(
        (row["expected_id"] or "",
         "root" if unordered and row["predicted_role"] in ROOT_ROLES else row["predicted_role"],
         row["upstream_expected_id"] or "")
        for row in rows
    )
    return {
        "case_id": result["case_id"], "family_id": answer["family_id"], "operator": answer["operator"],
        "strict": not missing and all(item["strict"] for item in rows),
        "strict_with_role_order": not missing and all(item["strict"] and item["role_exact"] for item in rows),
        "actions": rows, "omissions": omissions,
        "root_order_unspecified": unordered,
        "root_order_rationale": answer.get("root_order_rationale"),
        "expected_verdicts": {
            action_id: {"primary": label_text(primary, standard),
                        "allowed": [label_text(label, standard) for label in allowed],
                        "concrete_action_expected": action_id in known,
                        "role": expected[action_id]["role"]}
            for action_id, (primary, allowed) in gold_verdicts.items()
        },
        "missing_independent_actions": len(independent_expected & missing),
        "expected_independent_actions": len(independent_expected),
        "missed_independent_action_ids": sorted(independent_expected - roots_confirmed),
        "signature": signature, "causal_signature": causal_signature,
    }


def summarize(cases, standard):
    families, cross_op = defaultdict(list), defaultdict(set)
    confusion, outcomes, failures = Counter(), Counter(), Counter()
    metric = Counter(independent_defects_claimed=0, strict_independent_defects=0,
                     unresolved_implementation_actions=0, strict_unresolved_implementation_actions=0)
    primary_outcomes, alternatives, strict_alternatives = Counter(), Counter(), Counter()
    denominators, eligible_families = Counter(), defaultdict(set)
    eligible_operators, alternative_families = defaultdict(set), defaultdict(set)
    leaf_refs = {label_text(("leaf", mode, ()), standard): mode for mode in standard["parents"]}
    for case in cases:
        families[case["family_id"]].append(case["strict"])
        metric["missing_actions"] += len(case["omissions"])
        metric["missing_independent_actions"] += case["missing_independent_actions"]
        failures.update(item["failure_cause"] for item in case["omissions"].values())
        for gold in case["expected_verdicts"].values():
            primary = gold["primary"]
            denominators[primary] += 1
            if primary in leaf_refs:
                eligible_families[leaf_refs[primary]].add(case["family_id"])
                eligible_operators[leaf_refs[primary]].add(case["operator"])
        for key in case["omissions"]:
            confusion[(case["expected_verdicts"][key]["primary"], "missing_action")] += 1
        for row in case["actions"]:
            actual = row["actual"]
            expected = row["primary_expected"] or "unexpected_action"
            if row["accepted_alternative_label"]:
                alternatives[(expected, actual)] += 1
                strict_alternatives[(expected, actual)] += row["strict"]
                if row["mechanism_correct"] and actual in leaf_refs:
                    alternative_families[leaf_refs[actual]].add(case["family_id"])
            else:
                confusion[(expected, actual)] += 1
            outcomes[actual] += row["strict"]
            if row["primary_label_hit"]:
                primary_outcomes[actual] += row["strict"]
                if row["mechanism_correct"] and actual in leaf_refs:
                    cross_op[leaf_refs[actual]].add((case["family_id"], case["operator"]))
            failures.update(row["failure_causes"])
            metric.update(key for key in ("strict", "label_correct", "facts_supported", "double_count",
                                           "partial_parent", "over_abstention", "unsupported_attribution",
                                           "primary_label_hit", "accepted_alternative_label") if row[key])
            metric["label_match_with_failed_evidence"] += row["label_correct"] and not row["facts_supported"]
            metric["independent_defects_claimed"] += row["count_as_independent"]
            metric["strict_independent_defects"] += row["strict"] and row["count_as_independent"]
            metric["unresolved_implementation_actions"] += row["unresolved_implementation_action"]
            metric["strict_unresolved_implementation_actions"] += row["strict"] and row["unresolved_implementation_action"]
            metric["predicted_actions"] += 1
            metric["unexpected_actions"] += row["expected_id"] is None
            metric["misclassified_actions"] += row["expected_id"] is not None and not row["label_correct"]
    coverage = {}
    for namespaced_label, mode in leaf_refs.items():
        pairs = cross_op[mode]
        families_for_mode = {family for family, _ in pairs}
        operators = {operator for _, operator in pairs}
        # Distinct families and multiple operators imply at least one pair differs on both.
        coverage[namespaced_label.removeprefix("leaf:")] = {
            "eligible_families": len(eligible_families[mode]),
            "eligible_operators": sorted(eligible_operators[mode]),
            "supported_families": len(families_for_mode), "operators": sorted(operators),
            "accepted_alternative_families": len(alternative_families[mode]),
            "cross_operator_observed": len(families_for_mode) > 1 and len(operators) > 1,
            "status": "observed_in_batch" if pairs else
            ("needs_review" if eligible_families[mode] else "unverified"),
        }
    return {
        "families": len(families),
        "families_strict": sum(all(values) for values in families.values()),
        "cases": len(cases), "case_strict": sum(case["strict"] for case in cases),
        "action_counts": dict(metric), "strict_verdicts": dict(outcomes),
        "strict_primary_verdicts": dict(primary_outcomes), "coverage": coverage,
        "expected_verdict_counts": dict(denominators),
        "failure_counts": dict(failures),
        "confusion": [{"expected": wanted, "actual": actual, "count": count}
                      for (wanted, actual), count in sorted(confusion.items())],
        "accepted_alternatives": [
            {"primary_expected": key[0], "actual": key[1], "count": count, "strict": strict_alternatives[key]}
            for key, count in sorted(alternatives.items())
        ],
        **split_metrics(cases),
    }


def proportion(correct, eligible):
    return {"correct": correct, "eligible": eligible}


def status_bucket(label):
    return label if label.startswith("outside:") else label.split(":")[0]


def split_metrics(cases):
    gold_actions = [gold for case in cases for gold in case["expected_verdicts"].values()]
    rows = [row for case in cases for row in case["actions"]]
    known = sum(gold["concrete_action_expected"] for gold in gold_actions)
    statuses = Counter(status_bucket(gold["primary"]) for gold in gold_actions)
    supported = Counter(status_bucket(row["primary_expected"]) for row in rows if row["mechanism_correct"])
    actual = Counter(status_bucket(row["actual"]) for row in rows if row["mechanism_correct"])
    concrete_hits = unknown_hits = unknown_false = 0
    for case in cases:
        for row in case["actions"]:
            gold = case["expected_verdicts"].get(row["expected_id"])
            if gold is None:
                continue
            if gold["concrete_action_expected"]:
                concrete_hits += row["action_correct"]
            elif row["action_correct"]:
                unknown_hits += 1
            else:
                unknown_false += 1
    mechanism_families = defaultdict(list)
    for case in cases:
        mechanism_families[case["family_id"]].append(
            not case["omissions"] and all(row["mechanism_correct"] for row in case["actions"]))
    counted = Counter(row["independent_count_outcome"] for row in rows)
    return {
        "mechanism_metrics": {
            "actions": proportion(sum(row["mechanism_correct"] for row in rows), len(gold_actions)),
            "families": proportion(sum(all(values) for values in mechanism_families.values()),
                                   len(mechanism_families)),
            "actual_supported_statuses": dict(actual),
        },
        "status_metrics": {status: proportion(supported[status], eligible)
                           for status, eligible in sorted(statuses.items())},
        "concrete_action_metrics": {
            "known": proportion(concrete_hits, known),
            "unknown_retained": proportion(unknown_hits, len(gold_actions) - known),
            "unknown_false_confirmation": unknown_false,
        },
        "causal_metrics": {
            "role_and_edges_exact": proportion(sum(row["role_exact"] for row in rows), len(gold_actions)),
            "structure": proportion(sum(row["relationship_correct"] for row in rows), len(gold_actions)),
            "unresolved_predicted_roles": sum(row["predicted_role"] == "unknown" for row in rows),
            "unresolved_predicted_actions": sum(row["action_resolution"] == "unresolved" for row in rows),
        },
        "complete_cases_with_role_order": sum(case["strict_with_role_order"] for case in cases),
        "independent_reconciliation": {
            "claimed": sum(row["count_as_independent"] for row in rows),
            "expected": sum(case["expected_independent_actions"] for case in cases),
            "true_positive": counted["true_positive"],
            "false_positive": counted["false_positive"],
            "false_negative": sum(len(case["missed_independent_action_ids"]) for case in cases),
            "duplicates": sum(row["double_count"] for row in rows),
        },
    }


def compare_runs(graded, review):
    semantic_keys = ("same_decisive_facts", "same_specific_action")
    decisions = index(review["stability"], "case_id", "cross-run semantic review")
    left_cases = index(graded[0]["cases"], "case_id", "first graded run")
    right_cases = index(graded[1]["cases"], "case_id", "second graded run")
    require(set(left_cases) == set(right_cases) == set(decisions),
            "Judge must compare both readings for every case")
    items = []
    for case_id in sorted(decisions):
        decision = decisions[case_id]
        require(all(type(decision.get(key)) is bool for key in semantic_keys)
                and nonempty(decision.get("rationale")),
                "Record cross-run semantic decisions and a rationale")
        left, right = left_cases[case_id], right_cases[case_id]
        left_labels, right_labels = (
            sorted((row["expected_id"] or "", row["actual"]) for row in case["actions"])
            for case in (left, right)
        )
        aligned = all(expected_id for expected_id, _ in left_labels + right_labels)
        allowed = aligned and [key for key, _ in left_labels] == [key for key, _ in right_labels]
        allowed = allowed and all(not case["omissions"] and all(row["label_correct"] for row in case["actions"])
                                  for case in (left, right))
        same = left["signature"] == right["signature"]
        same_labels = left_labels == right_labels
        items.append({
            "case_id": case_id, "family_id": left["family_id"], "same": same,
            "same_and_both_incorrect": same and not left["strict"] and not right["strict"],
            "same_labels": same_labels, "same_allowed_labels": allowed,
            "same_causal_structure": aligned and left["causal_signature"] == right["causal_signature"],
            "same_labels_facts_and_action": same_labels and all(decision[key] for key in semantic_keys),
            "rationale": decision["rationale"], **{key: decision[key] for key in semantic_keys},
        })
    return {
        "cases": items,
        "same_cases": sum(item["same"] for item in items),
        "same_and_both_incorrect_cases": sum(item["same_and_both_incorrect"] for item in items),
        **{key: proportion(sum(item[key] for item in items), len(items))
           for key in ("same_labels", "same_allowed_labels", *semantic_keys, "same_causal_structure",
                       "same_labels_facts_and_action")},
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
    write_record(out, {
        "protocol": PROTOCOL, "mechanism_namespace": mechanism_namespace(standard),
        "catalog_version": standard["catalog_version"], "scope": "real_with_external_custody_attestation"
        if package["kind"] == "real" else "exercise_only",
        "note": "Hashes preserve bytes. Human attestation, not the evaluator, establishes isolation and exposure.",
        "lock_sha256": digest(lock_path), "answer_sha256": answer_hash, "review_sha256": digest(review_path),
        "answer_revision": revision_record,
        "runs": graded, "stability": compare_runs(graded, review),
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

