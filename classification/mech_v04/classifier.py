"""Classify evidence-bound actions using the admitted MECH-v0.4 catalog."""

import argparse
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import classify as pilot
from evaluate import read_json


NAMESPACE = "MECH-v0.4"
DECISION_VERSION = "0.4.3"
CATALOG = HERE / "catalog.json"
PILOT_CATALOG = HERE.parent / "catalog.json"
NUMERIC_MODES = ("NUM-01", "NUM-02")
NUMERIC_PARENT = "numerical_evaluation"
NUMERIC_PARENT_BASIS = {
    "applicable_contract", "implementation_action", "contribution_set_preserved", "distorted_value_consumed",
}
NUMERIC_BOUNDARIES = {"pre_reduction_square_overflow", "compliant", "contract_inapplicable"}
RESULT_FIELDS = (
    "pattern_id", "pattern_ref", "parent_id", "parent_ref", "parent_name",
    "definition_level", "mode_name", "group_id", "group_ref", "group_name",
    "outside_reason", "combination", "supported_pattern_ids", "supported_pattern_refs",
)


def validate_catalog(catalog, previous):
    modes = catalog["modes"]
    if (catalog["version"] != "0.4" or catalog["admitted_modes"] != list(NUMERIC_MODES)
            or set(modes) != set(previous["modes"]) | set(NUMERIC_MODES)
            or any(modes[mode] != card for mode, card in previous["modes"].items())
            or any(catalog[key] != previous[key] for key in ("parent_hierarchy", "combinations"))
            or any(catalog[section].get(key) != value
                   for section in ("parents", "parent_facts", "parent_definitions")
                   for key, value in previous[section].items())):
        raise ValueError("MECH-v0.4 must preserve the seven pilot cards and declare its two admissions")
    for mode in NUMERIC_MODES:
        card = modes[mode]
        if (card["parent"] != NUMERIC_PARENT or not pilot.strings(card["necessary"])
                or not pilot.strings(card["excluded_by"])
                or not {"applicable_contract", "implementation_action", card["operation_fact"]}
                <= set(card["necessary"])):
            raise ValueError(f"Invalid admitted card: {mode}")


def current_refs(action):
    updated = dict(action)
    for key in ("pattern_ref", "group_ref", "parent_ref"):
        if key in updated:
            updated[key] = updated[key].replace("MECH-v0.3:", NAMESPACE + ":", 1)
    if "supported_pattern_refs" in updated:
        updated["supported_pattern_refs"] = [
            f"{NAMESPACE}:{mode}" for mode in updated["supported_pattern_ids"]
        ]
    updated["neighbors"] = [
        {**neighbor, "pattern_ref": f"{NAMESPACE}:{neighbor['pattern_id']}"}
        for neighbor in action["neighbors"]
    ]
    return updated


def record_role(result, action, supported, causal):
    for key in ("upstream_id", "proposed_upstream_id", "proposed_role"):
        result.pop(key, None)
    role = action["role"] if supported and causal else "unknown"
    result.update(role=role, action_resolution="supported" if supported else "unresolved",
                  count_as_independent=supported and role in pilot.ROOT_ROLES)
    if role == "downstream":
        result["upstream_id"] = action["upstream_id"]
    if role != action["role"]:
        result["proposed_role"] = action["role"]
        if "upstream_id" in action:
            result["proposed_upstream_id"] = action["upstream_id"]


def proof_signature(fact):
    anchors = frozenset(
        (anchor["source_id"], anchor["start_line"], anchor["end_line"], anchor["use"])
        for anchor in fact["anchors"] if anchor["use"] != "context"
    )
    return fact["claim_state"], anchors, pilot.digest(fact.get("calculation"))


def parameter_boundary(result, action, sources, previous):
    """Prefer the proven parameter parent for a generic restatement of one action."""
    if (result.get("outside_reason"), result.get("parent_id")) != ("outside_catalog", "parameter"):
        return result
    parameter = previous["parent_facts"]["parameter"]
    outside = "established_other_defect"
    required = {"applicable_contract", "implementation_action", parameter, outside}
    scope = action["scope"]
    facts, positive, _, scoped, _, _ = pilot.collect_facts(action, sources, scope, required)
    if not required <= positive & scoped:
        return result
    decisive = [fact for fact in facts if fact["value"] and fact["key"] in {parameter, outside}
                and all(not pilot.check_anchor(anchor, sources, scope) for anchor in fact["anchors"])
                and pilot.evidence_basis(fact, sources, scope, decisive=True)[0]]
    parameter_proofs = {proof_signature(fact) for fact in decisive if fact["key"] == parameter}
    other = [fact for fact in decisive if fact["key"] == outside]
    if other and all(proof_signature(fact) in parameter_proofs for fact in other):
        specific = {**action, "facts": [fact for fact in action["facts"] if fact["key"] != outside]}
        judgment = pilot.verdict(specific, sources, previous, revised=True)
        judgment["restated_other_defect"] = other
        return judgment

    conflict = "competing_parameter_claims"
    judgment = {key: value for key, value in result.items() if key not in RESULT_FIELDS}
    details = judgment.get("conflict_details", {"core": [], "leaf": [], "unrelated": []})
    judgment.update(status="insufficient", conflicts=sorted(set(result["conflicts"]) | {conflict}),
                    conflict_details={**details, "core": sorted(set(details["core"]) | {conflict})})
    record_role(judgment, action, supported=False, causal=False)
    return judgment


def numeric_verdict(pilot_result, action, sources, catalog):
    result = current_refs(pilot_result)
    cards = {mode: catalog["modes"][mode] for mode in NUMERIC_MODES}
    operations = {mode: card["operation_fact"] for mode, card in cards.items()}
    parent_fact = catalog["parent_facts"][NUMERIC_PARENT]
    asserted = {fact.get("key") for fact in action.get("facts", []) if fact.get("value") is True}
    requested = {mode for mode, operation in operations.items() if operation in asserted}
    if not requested and parent_fact not in asserted:
        return result

    parent_basis = NUMERIC_PARENT_BASIS | {parent_fact}
    required = {mode: set(cards[mode]["necessary"]) for mode in requested}
    excluded = {mode: set(cards[mode]["excluded_by"]) for mode in requested}
    decisive = parent_basis.union(NUMERIC_BOUNDARIES, {"causal_role"}, *required.values(), *excluded.values())
    _, positive, negative, scoped, issues, disputed = pilot.collect_facts(action, sources, action["scope"], decisive)
    proof = positive & scoped
    conflicts = (set(disputed) & decisive) - {"causal_role"}
    complete = {mode for mode, keys in required.items() if keys <= proof}
    blocked = {mode for mode, keys in excluded.items() if keys & proof}
    parent_supported = parent_basis <= proof
    parent_contender = parent_basis <= proof | conflicts
    square_first = "pre_reduction_square_overflow" in proof
    first_errors = proof & (set(operations.values()) | {"pre_reduction_square_overflow"})
    scope_errors = pilot.validate_scope(action["scope"])
    prior_conflicts = pilot_result.get("conflict_details", {}).get("core", [])
    prior_alternative = (pilot_result["status"] in {"leaf", "parent"}
                         or pilot_result.get("outside_reason") in {"compliant", "inapplicable"})

    if (square_first and pilot_result.get("outside_reason") == "outside_catalog" and not complete
            and not (parent_contender and len(first_errors) > 1)):
        return result
    if not (complete or parent_contender) and (prior_alternative or
                (requested and blocked == requested and pilot_result["status"] == "outside")):
        return result

    for field in RESULT_FIELDS:
        result.pop(field, None)
    result["issues"] = result["issues"] + [
        issue for issue in issues if issue.get("fact") in decisive and issue not in result["issues"]
    ]
    if (complete or parent_contender) and (
            prior_alternative or complete & blocked or len(first_errors) > 1
            or proof & {"compliant", "contract_inapplicable"}):
        conflicts.add("competing_mechanisms_for_one_action")
    if complete and parent_fact in negative:
        conflicts.add(parent_fact)

    clear = not (conflicts or prior_conflicts or scope_errors)
    causal = "causal_role" in proof
    if len(complete) == 1 and clear:
        mode, = complete
        card = cards[mode]
        result.update(status="leaf", pattern_id=mode, pattern_ref=f"{NAMESPACE}:{mode}",
                      definition_level=card["definition_level"], mode_name=card["title"],
                      group_id=NUMERIC_PARENT, group_ref=f"{NAMESPACE}:{NUMERIC_PARENT}",
                      group_name=catalog["parents"][NUMERIC_PARENT])
        result["missing"] = [] if causal or action["role"] == "unknown" else ["causal_role"]
        record_role(result, action, supported=True, causal=causal)
        return result

    result["status"] = "insufficient"
    result["numeric_neighbors"] = {
        mode: {"missing": sorted(required[mode] - proof), "contrary": sorted(excluded[mode] & proof)}
        for mode in sorted(requested)
    }
    missing = set(scope_errors).union(*(keys - proof for keys in required.values()))
    if parent_fact in asserted:
        missing.update(parent_basis - proof)
    if parent_supported and clear and not square_first:
        result.update(status="parent", parent_id=NUMERIC_PARENT, parent_ref=f"{NAMESPACE}:{NUMERIC_PARENT}",
                      parent_name=catalog["parents"][NUMERIC_PARENT])
        if not causal and action["role"] != "unknown":
            missing.add("causal_role")
    result["missing"] = sorted(missing)
    if conflicts:
        result["conflicts"] = sorted(set(result["conflicts"]) | conflicts)
        details = result.get("conflict_details", {"core": [], "leaf": [], "unrelated": []})
        result["conflict_details"] = {
            "core": sorted(set(details["core"]) | conflicts),
            "leaf": sorted(set(details["leaf"]) - conflicts),
            "unrelated": sorted(set(details["unrelated"]) - conflicts),
        }
    record_role(result, action, supported=result["status"] == "parent", causal=causal)
    return result


def separate_cross_version_context(fact, sources, scope):
    """Keep a fact's self-sufficient scoped proof apart from other snapshots."""
    anchors = fact.get("anchors")
    if (fact.get("claim_state") not in ("confirmed_report", "derived")
            or scope.get("claim") not in ("reported", "static")
            or not isinstance(anchors, list)):
        return fact, []

    bound, context = [], []
    for anchor in anchors:
        if (not isinstance(anchor, dict) or not pilot.nonempty(anchor.get("use"))
                or anchor["use"] not in pilot.ANCHOR_USES):
            return fact, []
        error = pilot.check_anchor(anchor, sources, scope)
        if error is None:
            bound.append(anchor)
            continue
        if error != "source_version_mismatch":
            return fact, []
        source = sources[anchor["source_id"]]
        source_scope = {"version": source["version"], "path": source["path"], "claim": "reported"}
        if source["kind"] == "runtime" or pilot.check_anchor(anchor, sources, source_scope):
            return fact, []
        context.append({
            "fact": fact.get("key"),
            "version": source["version"],
            "anchor": anchor,
        })

    projected = {**fact, "anchors": bound}
    if not context or not pilot.evidence_basis(projected, sources, scope, decisive=True)[0]:
        return fact, []
    return projected, context


def project_packet(packet, sources):
    actions, context_by_action = [], {}
    for action_id, action in pilot.by_id(packet.get("actions"), "actions").items():
        facts, context = [], []
        scope = action.get("scope")
        if not isinstance(scope, dict):
            actions.append(action)
            continue
        for fact in pilot.records(action.get("facts", []), "facts"):
            projected, supplemental = separate_cross_version_context(fact, sources, scope)
            facts.append(projected)
            context.extend(supplemental)
        if context:
            context_by_action[action_id] = context
            actions.append({**action, "facts": facts})
        else:
            actions.append(action)
    return {**packet, "actions": actions}, context_by_action


def classify_package(material, packets, catalog=None):
    previous = read_json(PILOT_CATALOG)
    catalog = read_json(CATALOG) if catalog is None else catalog
    validate_catalog(catalog, previous)
    results = pilot.classify_package(material, packets, previous)
    cases = pilot.by_id(material["cases"], "material cases", "case_id")
    by_case = pilot.by_id(packets, "case fact packets", "case_id")
    reviewed = []
    for result in results:
        case_id = result["case_id"]
        packet = by_case[case_id]
        if packet.get("fact_protocol") != pilot.FACT_PROTOCOL:
            raise ValueError("MECH-v0.4 requires evidence-bound fact packets")
        sources = pilot.by_id(cases[case_id]["sources"], "sources")
        projected, context = project_packet(packet, sources)
        if context:
            result = pilot.classify(cases[case_id], projected, previous)
        actions = pilot.by_id(projected["actions"], "actions")
        judged = []
        for row in result["actions"]:
            action = actions[row["id"]]
            boundary = parameter_boundary(row, action, sources, previous)
            verdict = numeric_verdict(boundary, action, sources, catalog)
            if row["id"] in context:
                verdict["cross_version_context"] = context[row["id"]]
            judged.append(verdict)
        result.update(catalog_version=catalog["version"], mechanism_namespace=NAMESPACE,
                      decision_version=DECISION_VERSION, facts_sha256=pilot.digest(packet),
                      actions=judged)
        reviewed.append(result)
    return reviewed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("material", type=Path)
    parser.add_argument("facts", type=Path)
    parser.add_argument("--batch", action="store_true")
    args = parser.parse_args()
    material, packets = read_json(args.material), read_json(args.facts)
    if not args.batch:
        material, packets = {"cases": [material]}, [packets]
    result = classify_package(material, packets)
    print(json.dumps(result if args.batch else result[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
