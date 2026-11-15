"""Classify sourced actions supplied by the pilot's material-reading procedure."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys


SOURCE_KINDS = {"issue", "contract", "code", "diff", "report", "runtime"}
CLAIMS = {"reported", "static", "runtime"}
ROLES = {"primary", "independent", "downstream"}
UNPINNED = {"unknown", "unavailable", "unpinned", "unspecified", "unverified",
            "n/a", "?", "head", "latest", "main", "master", "develop"}
OPERATION_FACTS = {
    "P1": "actual_source",
    "P2": "wrong_state_treatment",
    "L1": "contiguous_formula",
    "L2": "wrong_conversion",
    "C1": "actual_contribution",
    "C2": "omitted_contribution",
    "C3": "excess_multiplicity",
}
VIOLATIONS = {
    "parameter": "parameter_violation",
    "address": "address_violation",
    "contribution": "contribution_violation",
}
OUTSIDE = {
    "compliant": "compliant",
    "contract_inapplicable": "inapplicable",
    "established_other_defect": "outside_catalog",
}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def digest(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def records(value, label):
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError(f"{label} must be an array of objects")
    return value


def strings(value):
    return isinstance(value, list) and all(nonempty(item) for item in value)


def by_id(rows, label, key="id"):
    indexed = {}
    for row in records(rows, label):
        identity = row.get(key)
        if not nonempty(identity) or identity in indexed:
            raise ValueError(f"{label} must have unique nonempty IDs")
        indexed[identity] = row
    return indexed


def validate_catalog(catalog):
    if not isinstance(catalog, dict) or not nonempty(catalog.get("version")):
        raise ValueError("The catalog requires a version")
    parents, modes = catalog.get("parents"), catalog.get("modes")
    if not isinstance(parents, dict) or set(parents) != set(VIOLATIONS):
        raise ValueError("The pilot catalog requires its three parent groups")
    if not isinstance(modes, dict) or set(modes) != set(OPERATION_FACTS):
        raise ValueError("The pilot catalog requires its seven mode cards")
    for mode_id, card in modes.items():
        if (not isinstance(card, dict) or not nonempty(card.get("parent"))
                or card["parent"] not in parents or not strings(card.get("necessary"))
                or not strings(card.get("excluded_by", []))
                or "applicable_contract" not in card["necessary"]
                or OPERATION_FACTS[mode_id] not in card["necessary"]):
            raise ValueError(f"Invalid scope or requirements in mode {mode_id}")


def validate_scope(scope):
    if not isinstance(scope, dict):
        raise ValueError("Action scope must be an object")
    missing = [f"scope.{key}" for key in ("version", "path", "claim") if not nonempty(scope.get(key))]
    claim = scope.get("claim")
    if claim is not None and (not isinstance(claim, str) or (claim.strip() and claim not in CLAIMS)):
        raise ValueError("Claim must be reported, static, or runtime")
    version = scope.get("version")
    if claim in {"static", "runtime"} and nonempty(version) and version.strip().lower() in UNPINNED:
        missing.append("scope.pinned_version")
    if claim == "runtime":
        missing.extend(f"scope.{key}" for key in ("build", "call_id") if not nonempty(scope.get(key)))
    return missing


def check_anchor(anchor, sources, scope):
    if not isinstance(anchor, dict) or not nonempty(anchor.get("source_id")):
        return "invalid_anchor"
    source = sources.get(anchor["source_id"])
    if source is None:
        return "unknown_source"
    if source["version"] != scope.get("version"):
        return "source_version_mismatch"
    if (source["version"].strip().lower() in UNPINNED
            and (scope.get("claim") != "reported" or source["path"] != scope.get("path"))):
        return "unpinned_source_cannot_support_this_scope"
    if source["kind"] == "runtime" and scope.get("claim") == "runtime":
        if any(scope.get(k) != source.get(k) for k in ("build", "call_id")):
            return "runtime_binding_mismatch"
    start, end, quote = (anchor.get(k) for k in ("start_line", "end_line", "quote"))
    lines = source["text"].splitlines()
    if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
        return "invalid_excerpt_line_range"
    if not nonempty(quote) or "\n".join(quote.splitlines()) not in "\n".join(lines[start - 1:end]):
        return "quote_not_in_source_span"
    return None


def scoped_source(source, scope):
    if source["path"] != scope.get("path"):
        return False
    claim = scope.get("claim")
    if claim == "static":
        return source["kind"] in {"code", "diff"}
    if claim == "runtime":
        return source["kind"] == "runtime"
    return claim == "reported" and source["kind"] in {"issue", "report", "code", "diff"}


def check_calculation(fact):
    """Check an optional computation over values the reader has sourced."""
    if "calculation" not in fact:
        return None
    calculation = fact["calculation"]
    if not isinstance(calculation, dict):
        return "invalid_calculation"
    expected, actual = calculation.get("expected"), calculation.get("actual")
    key = fact["key"]
    if type(expected) is not int or type(actual) is not int:
        return "invalid_calculation"
    if key in {"contiguous_formula", "wrong_conversion"}:
        observed = expected != actual
    elif key == "actual_contribution" and expected == 0 and actual >= 0:
        observed = actual > 0
    elif key == "omitted_contribution" and expected > 0 and actual >= 0:
        observed = actual < expected
    elif key == "excess_multiplicity" and expected > 0 and actual >= 0:
        observed = actual > expected
    else:
        return "calculation_not_applicable"
    return None if observed is fact["value"] else "calculation_disagrees"


def collect_facts(action, sources, scope):
    arguments = defaultdict(set)
    scoped_facts = set()
    facts, issues = [], []
    for fact in records(action.get("facts", []), "facts"):
        key = fact.get("key")
        if not nonempty(key) or type(fact.get("value")) is not bool:
            issues.append({"code": "invalid_fact"})
            continue
        anchors = fact.get("anchors")
        if not isinstance(anchors, list) or not anchors:
            issues.append({"fact": key, "code": "missing_anchors"})
            continue
        errors = {error for anchor in anchors if (error := check_anchor(anchor, sources, scope))}
        if not errors and (error := check_calculation(fact)):
            if error == "calculation_disagrees":
                arguments[key].update((True, False))
            errors.add(error)
        if errors:
            issues.extend({"fact": key, "code": error} for error in sorted(errors))
            continue
        arguments[key].add(fact["value"])
        if fact["value"] and any(scoped_source(sources[a["source_id"]], scope) for a in anchors):
            scoped_facts.add(key)
        preserved = {name: fact[name] for name in ("key", "value", "anchors")}
        for name in ("explanation", "calculation"):
            if name in fact:
                preserved[name] = fact[name]
        facts.append(preserved)
    positives = {key for key, values in arguments.items() if values == {True}}
    negatives = {key for key, values in arguments.items() if values == {False}}
    conflicts = sorted(key for key, values in arguments.items() if len(values) > 1)
    return facts, positives, negatives, scoped_facts, issues, conflicts


def mode_comparisons(modes, positives, negatives, scoped):
    results = {}
    for mode, card in sorted(modes.items()):
        needed = set(card["necessary"])
        missing = sorted(needed - positives - negatives)
        excluded = sorted((needed & negatives) | (set(card.get("excluded_by", [])) & positives))
        operation = OPERATION_FACTS[mode]
        if operation in positives and operation not in scoped:
            missing.append(f"{operation}:scope")
        results[mode] = {
            "pattern_id": mode,
            "missing": missing,
            "contrary": excluded,
            "support_count": len((needed & positives) - {"applicable_contract"}),
        }
    return results


def verdict(action, sources, catalog):
    scope = action.get("scope")
    scope_missing = validate_scope(scope)
    modes = catalog["modes"]
    facts, true, false, scoped, issues, conflicts = collect_facts(action, sources, scope)
    comparisons = mode_comparisons(modes, true, false, scoped)
    supported = [mode for mode, check in comparisons.items() if not check["missing"] and not check["contrary"]]
    parents = [parent for parent, key in VIOLATIONS.items()
               if "applicable_contract" in true and key in true and key in scoped]
    outside = [key for key in OUTSIDE if key in true]
    established = "established_other_defect"
    if established in outside and not any(
            fact["key"] == established and fact["value"] and nonempty(fact.get("explanation")) for fact in facts):
        issues.append({"fact": established, "code": "missing_specific_other_defect"})
        scope_missing.append(f"{established}:detail")

    if len(supported) > 1:
        conflicts.append("multiple_leaf_modes_for_one_action")
    if len(parents) > 1 or (supported and parents and modes[supported[0]]["parent"] not in parents):
        conflicts.append("multiple_violation_groups_for_one_action")
    if len(outside) > 1 or (outside and supported):
        conflicts.append("competing_verdicts")
    if ("contract_inapplicable" in true and "applicable_contract" in true
            or (true & {"compliant", "contract_inapplicable"} and true & set(VIOLATIONS.values()))):
        conflicts.append("scope_or_outcome_contradiction")
    for mode, card in modes.items():
        if set(card["necessary"]) <= true and set(card.get("excluded_by", [])) & true:
            conflicts.append(f"contraindicated:{mode}")

    result = {
        "id": action["id"],
        "scope": scope,
        "role": action["role"],
        "status": "insufficient",
        "facts": facts,
        "issues": issues,
        "conflicts": sorted(set(conflicts)),
    }
    for name in ("description", "upstream_id"):
        if name in action:
            result[name] = action[name]
    if outside and not any(key in scoped for key in outside):
        scope_missing.append("outside_fact:scope")

    nearest_parent = parents[0] if len(parents) == 1 else None
    if not scope_missing and not conflicts:
        if outside and outside[0] in scoped:
            result.update(status="outside", outside_reason=OUTSIDE[outside[0]])
            if nearest_parent and outside[0] == established:
                result["parent_id"] = nearest_parent
        elif supported:
            mode = supported[0]
            result.update(status="leaf", pattern_id=mode)
            nearest_parent = modes[mode]["parent"]
        elif nearest_parent:
            result.update(status="parent", parent_id=nearest_parent)

    neighbors = [check for mode, check in comparisons.items()
                 if mode != result.get("pattern_id") and (nearest_parent is None or modes[mode]["parent"] == nearest_parent)]
    strongest = max((check["support_count"] for check in neighbors), default=0)
    if nearest_parent is None and strongest:
        neighbors = [check for check in neighbors if check["support_count"] == strongest]
    result["neighbors"] = [
        {k: check[k] for k in ("pattern_id", "missing", "contrary")} for check in neighbors
    ]
    missing = set(scope_missing)
    if result["status"] in {"insufficient", "parent"}:
        if strongest or nearest_parent:
            viable = [check for check in neighbors if not check["contrary"]]
            fewest = min((len(check["missing"]) for check in viable), default=None)
            for check in viable:
                if len(check["missing"]) == fewest:
                    missing.update(check["missing"])
        if not missing and not conflicts:
            missing.add("observed_implementation_action")
            if "applicable_contract" not in true:
                missing.add("applicable_contract")
    result["missing"] = sorted(missing)
    result["count_as_independent"] = action["role"] != "downstream" and (
        result["status"] in {"leaf", "parent"} or result.get("outside_reason") == "outside_catalog"
    )
    return result


def validate_links(actions):
    for action in actions.values():
        if not nonempty(action.get("role")) or action["role"] not in ROLES:
            raise ValueError("Each action needs a primary, independent, or downstream role")
        if action["role"] != "downstream" and "upstream_id" in action:
            raise ValueError("Only downstream actions can name an upstream action")
        if action["role"] == "downstream" and (
                not nonempty(action.get("upstream_id")) or action["upstream_id"] not in actions):
            raise ValueError("Downstream actions must reference an action in the same case")
    for action in actions.values():
        visited = {action["id"]}
        while "upstream_id" in action:
            upstream_id = action["upstream_id"]
            if upstream_id in visited:
                raise ValueError("Downstream links cannot be cyclic")
            visited.add(upstream_id)
            action = actions[upstream_id]


def classify(case, packet, catalog):
    """Check evidence binding and apply the supplied catalog to reader-extracted facts."""
    validate_catalog(catalog)
    if not isinstance(case, dict) or not isinstance(packet, dict) or not nonempty(case.get("case_id")):
        raise ValueError("Case and fact packet must be objects with a case ID")
    if case["case_id"] != packet.get("case_id"):
        raise ValueError("Case and fact packet IDs must match")
    sources = by_id(case.get("sources"), "sources")
    for source in sources.values():
        if (not all(nonempty(source.get(k)) for k in ("version", "path", "kind", "text"))
                or source["kind"] not in SOURCE_KINDS):
            raise ValueError("Each source requires a version, path, known kind, and excerpt text")
    operator = packet.get("operator", "unknown")
    roles = packet.get("roles", [])
    if not nonempty(operator) or not strings(roles):
        raise ValueError("Operator and semantic roles must be text")
    actions = by_id(packet.get("actions"), "actions")
    if not actions:
        raise ValueError("Submit an explicit insufficient action if the materials do not establish an action")
    validate_links(actions)
    return {
        "case_id": case["case_id"],
        "case_sha256": digest(case),
        "facts_sha256": digest(packet),
        "catalog_version": catalog["version"],
        "operator": operator,
        "roles": roles,
        "actions": [verdict(action, sources, catalog) for action in actions.values()],
    }


def classify_package(view, packets, catalog):
    """Classify a raw-material package using the separately extracted fact packets."""
    if not isinstance(view, dict) or set(view) != {"cases"}:
        raise ValueError("A material package must contain only cases")
    cases = by_id(view["cases"], "material cases", "case_id")
    facts = by_id(packets, "case fact packets", "case_id")
    if not cases or set(cases) != set(facts):
        raise ValueError("Material cases and fact packet IDs must match")
    return [classify(case, facts[case_id], catalog) for case_id, case in cases.items()]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, help="Material view including verbatim excerpts")
    parser.add_argument("facts", type=Path, help="Evidence facts extracted from those materials")
    parser.add_argument("--batch", action="store_true", help="Read a material package and a list of fact packets")
    parser.add_argument("--catalog", type=Path, default=Path(__file__).with_name("catalog.json"))
    args = parser.parse_args(argv)
    try:
        case, facts, catalog = (json.loads(path.read_text(encoding="utf-8-sig"))
                                for path in (args.case, args.facts, args.catalog))
        method = classify_package if args.batch else classify
        result = method(case, facts, catalog)
    except (OSError, ValueError) as exc:
        print(f"Invalid classification input: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

