"""Extend the catalogue while retaining the established evidence and action-graph protocol."""

from copy import deepcopy
import json
from pathlib import Path

from mech_v04 import classifier as baseline
from reliability_v04 import graph

pilot = baseline.pilot
HERE = Path(__file__).resolve().parent
CATALOG = HERE / "catalog.json"
NAMESPACE = "MECH-v0.5"
CORE = {"applicable_contract", "implementation_action"}
BOUNDARIES = {"compliant", "contract_inapplicable"}

# Explicitly reviewed descriptions of the same operation; never a general similarity rule.
COMPATIBLE_DESCRIPTIONS = {
    ("C2", "PLAN-SPLIT-01"): "PLAN-SPLIT-01",
    ("P1", "VALID-DOMAIN-01"): "P1",
}


def shared_operation_witness(facts, old_key, new_key):
    def witnesses(key):
        return {(f["claim_state"], a["source_id"], a["start_line"], a["end_line"], a["use"])
                for f in facts if f["key"] == key and f["value"] is True
                and f["claim_state"] not in {"observation", "hypothesis"}
                for a in f["anchors"] if a["use"] in {"confirmation", "behavior", "runtime"}}
    return bool(witnesses("implementation_action") & witnesses(old_key) & witnesses(new_key))


def load_catalog(path=CATALOG):
    value = json.loads(Path(path).read_bytes())
    validate_catalog(value)
    return value


def validate_catalog(value):
    previous = baseline.read_json(baseline.CATALOG)
    if value.get("version") != "0.5" or value.get("status") != "development_knowledge":
        raise ValueError("A versioned development knowledge catalogue is required")
    for mode, card in previous["modes"].items():
        if value["modes"].get(mode) != card:
            raise ValueError(f"Inherited mode definition changed: {mode}")
    hierarchy = value["parent_hierarchy"]
    for parent in value["parents"]:
        visited, current = set(), parent
        while current in hierarchy:
            if current in visited:
                raise ValueError("Cyclic parent hierarchy")
            visited.add(current)
            current = hierarchy[current]
        if current not in value["parents"]:
            raise ValueError("Unknown root parent")
    for mode, card in value["modes"].items():
        if card["parent"] not in value["parents"] or not card.get("definition"):
            raise ValueError(f"Incomplete mode: {mode}")
        if mode in previous["modes"]:
            continue
        if not CORE <= set(card["necessary"]) or card["operation_fact"] not in card["necessary"]:
            raise ValueError(f"New mode lacks an action/contract requirement: {mode}")
        if not card.get("exclusions") or not card.get("source_ids") or not card.get("test_design"):
            raise ValueError(f"New mode lacks provenance/boundary/test design: {mode}")
        if any(key not in value["fact_definitions"] for key in card["necessary"]):
            raise ValueError(f"Undocumented fact: {mode}")
        if card["classification_enabled"] and card["knowledge_status"] != "reviewed_definition":
            raise ValueError(f"Unreviewed definition cannot classify: {mode}")


def new_verdict(original, action, sources, catalog):
    """Retrieval scores never enter this decision; only scoped, evidence-bound facts do."""
    prior_ids = set(baseline.read_json(baseline.CATALOG)["modes"])
    cards = {key: card for key, card in catalog["modes"].items()
             if key not in prior_ids and card["classification_enabled"]}
    new_parent_facts = {k: v for k, v in catalog["parent_facts"].items()
                        if k not in baseline.read_json(baseline.CATALOG)["parent_facts"]}
    decisive = set().union(CORE, BOUNDARIES, {"causal_role"}, set(new_parent_facts.values()),
                           *(set(c["necessary"]) | set(c["excluded_by"]) for c in cards.values()))
    projected, _ = baseline.project_packet({"actions": [action]}, sources)
    action = projected["actions"][0]
    facts, positive, negative, scoped, issues, disputed = pilot.collect_facts(action, sources, action["scope"], decisive)
    proof, disputed = positive & scoped, set(disputed)
    complete, contenders, comparisons = [], [], {}
    for mode, card in cards.items():
        needed = set(card["necessary"])
        contrary = (set(card["excluded_by"]) & proof) | (needed & negative)
        requested = card["operation_fact"] in positive | disputed
        if needed <= proof and not contrary:
            complete.append(mode)
        if needed <= proof | disputed:
            contenders.append(mode)
        if requested:
            comparisons[mode] = {"missing": sorted(needed - proof), "contrary": sorted(contrary),
                                 "disputed": sorted(needed & disputed)}
    parents = [parent for parent, fact in new_parent_facts.items() if CORE | {fact} <= proof]
    if not complete and not contenders and not parents:
        result = deepcopy(original)
        if comparisons:
            result["knowledge_neighbors"] = comparisons
        return result
    result = {k: deepcopy(v) for k, v in original.items() if k not in baseline.RESULT_FIELDS}
    result.update(facts=facts, knowledge_neighbors=comparisons)
    result["issues"] = result.get("issues", []) + [issue for issue in issues if issue not in result.get("issues", [])]
    relevant = set().union(CORE, *(set(cards[m]["necessary"]) | set(cards[m]["excluded_by"]) for m in contenders))
    conflict = set(result.get("conflicts", [])) | (disputed & relevant)
    if len(complete) > 1:
        conflict.add("competing_new_mechanisms_for_one_action")
    compatible = None
    if complete and original["status"] == "leaf":
        pair = (original["pattern_id"], complete[0]) if len(complete) == 1 else None
        prior_card = catalog["modes"][original["pattern_id"]]
        if (pair in COMPATIBLE_DESCRIPTIONS and shared_operation_witness(
                facts, prior_card["operation_fact"], cards[complete[0]]["operation_fact"])):
            compatible = pair
        else:
            conflict.add("competing_inherited_and_new_mechanisms")
    if complete and proof & BOUNDARIES:
        conflict.add("mechanism_conflicts_with_boundary")
    scope_errors = pilot.validate_scope(action["scope"])
    if len(complete) == 1 and not conflict and not scope_errors:
        if compatible and COMPATIBLE_DESCRIPTIONS[compatible] == compatible[0]:
            result = deepcopy(original)
            result.update(co_supported_mode_ids=[compatible[1]],
                          compatibility_basis="reviewed_pair_with_shared_operation_witness",
                          knowledge_neighbors=comparisons)
            return result
        mode = complete[0]
        card = cards[mode]
        # A specific evidenced mechanism refines an outside-catalog verdict or its ancestor.
        if original["status"] == "parent":
            lineage = pilot.parent_lineage(card["parent"], catalog["parent_hierarchy"])
            if original["parent_id"] not in lineage:
                conflict.add("competing_unrelated_parent")
        if not conflict:
            result.update(status="leaf", pattern_id=mode, pattern_ref=f"{NAMESPACE}:{mode}",
                          mode_name=card["title"], group_id=card["parent"], group_ref=f"{NAMESPACE}:{card['parent']}",
                          group_name=catalog["parents"][card["parent"]], definition_level=card["definition_level"],
                          knowledge_status=card["knowledge_status"], missing=[])
            baseline.record_role(result, action, supported=True, causal="causal_role" in proof)
            if compatible:
                result.update(co_supported_mode_ids=[compatible[0]],
                              compatibility_basis="reviewed_pair_with_shared_operation_witness")
            return result
    if not complete and len(parents) == 1 and not conflict and not scope_errors and original["status"] != "leaf":
        parent = parents[0]
        result.update(status="parent", parent_id=parent, parent_ref=f"{NAMESPACE}:{parent}",
                      parent_name=catalog["parents"][parent], missing=sorted(set().union(*(set(row["missing"]) for row in comparisons.values()))))
        baseline.record_role(result, action, supported=True, causal="causal_role" in proof)
        return result
    result.update(status="insufficient", conflicts=sorted(conflict), missing=sorted(set(scope_errors).union(
        *(set(row["missing"]) for row in comparisons.values()))))
    baseline.record_role(result, action, supported=False, causal=False)
    return result


def classify_case(case, extracted, catalog):
    if case["case_id"] != extracted.get("case_id"):
        raise ValueError("Material and readback case IDs differ")
    sources = pilot.by_id(case["sources"], "source views")
    proposed = pilot.by_id(extracted["nodes"], "graph nodes")
    if not proposed or any(node["node_type"] not in graph.KINDS for node in proposed.values()):
        raise ValueError("Each case requires valid action graph nodes")
    prepared = {key: graph.prepare_node(node, sources) for key, node in proposed.items()}
    actions = [action for key, (action, _) in prepared.items() if proposed[key]["node_type"] != "supporting_operation"]
    if not actions:
        raise ValueError("Include an unknown or boundary action when no defect is established")
    packet = {"case_id": case["case_id"], "operator": extracted["operator"], "roles": extracted["roles"],
              "actions": actions, "fact_protocol": pilot.FACT_PROTOCOL}
    verdict, = baseline.classify_package({"cases": [case]}, [packet])
    previous = pilot.by_id(verdict["actions"], "inherited judgments")
    matches = {action["id"]: new_verdict(previous[action["id"]], action, sources, catalog) for action in actions}
    nodes = {key: graph.classify_node(proposed[key], action, position, matches.get(key), sources, catalog["modes"])
             for key, (action, position) in prepared.items()}
    edges = graph.resolve_relations(extracted["relations"], nodes, sources)
    graph.attribute_supported_effects(nodes, edges, catalog["modes"])
    graph.count_roots(nodes, edges, sources)
    graph.assign_effects(nodes, edges)
    return {"case_id": case["case_id"], "operator": extracted["operator"], "source_sha256": pilot.digest(case),
            "facts_sha256": pilot.digest(extracted), "nodes": list(nodes.values()), "relations": edges,
            "independent_count": sum(node["independent_count"] for node in nodes.values())}


def classify_package(material, extracted, catalog=None):
    catalog = load_catalog() if catalog is None else catalog
    validate_catalog(catalog)
    cases = pilot.by_id(material["cases"], "material cases", "case_id")
    packets = pilot.by_id(extracted["cases"], "graph packets", "case_id")
    if not cases or cases.keys() != packets.keys():
        raise ValueError("Readbacks must cover exactly the material inventory")
    return {"protocol": graph.PROTOCOL, "catalog": NAMESPACE, "decision": "0.5.0-development",
            "catalog_sha256": pilot.digest(catalog), "evaluation_class": "development_exercise",
            "cases": [classify_case(case, packets[key], catalog) for key, case in cases.items()]}
