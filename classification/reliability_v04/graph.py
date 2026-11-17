"""Bind evidence to a case graph and apply the unchanged MECH-v0.4 cards."""

from collections import defaultdict
from itertools import combinations

from mech_v04 import classifier


pilot = classifier.pilot
PROTOCOL = "mech_v04_action_graph/0.2"
ROOTS = {"root_action", "independent_action"}
KINDS = ROOTS | {"downstream_effect", "supporting_operation", "unknown_action"}
CAUSAL = {"causes", "propagates_to"}
RELATIONS = CAUSAL | {"violates", "independent_of", "consumes", "supports"}


def excerpt(ref, sources):
    """Resolve a one-based span against its own frozen source."""
    source = sources.get(ref["source_id"])
    if source is None:
        return None
    start, end = ref["start_line"], ref["end_line"]
    lines = source["text"].splitlines()
    if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
        return None
    quote = "\n".join(lines[start - 1:end])
    return {**ref, "quote": quote} if quote.strip() else None


def scope_from(value, sources):
    source = sources.get(value["source_id"], {})
    scope = {"claim": value["claim"], "version": source.get("version", ""), "path": source.get("path", "")}
    scope.update({key: value[key] for key in ("build", "call_id") if value.get(key) is not None})
    return scope


def anchored_basis(state, explanation, anchors, sources, scope, *, decisive=True):
    if not anchors or pilot.validate_scope(scope):
        return False
    fact = {"claim_state": state, "explanation": explanation, "anchors": anchors}
    fact, _ = classifier.separate_cross_version_context(fact, sources, scope)
    return (not any(pilot.check_anchor(anchor, sources, scope) for anchor in fact["anchors"])
            and pilot.evidence_basis(fact, sources, scope, decisive)[0])


def action_position(location, scope, sources):
    ref = excerpt(location, sources) if location else None
    if ref is None or pilot.validate_scope(scope):
        return None
    source = sources[ref["source_id"]]
    if pilot.check_anchor(ref, sources, scope) or not pilot.scoped_source(source, scope):
        return None
    if source["kind"] == "diff" and not all(
        line.startswith((" ", "-")) and not line.startswith("---") for line in ref["quote"].splitlines()
    ):
        return None
    return {**ref, "origin": source.get("origin", source["path"]), "version": source["version"],
            "path": source["path"], "original_start_line": source.get("original_start_line", 1) + ref["start_line"] - 1,
            "original_end_line": source.get("original_start_line", 1) + ref["end_line"] - 1}


def prepare_node(node, sources):
    scope = scope_from(node["scope"], sources)
    location = action_position(node["source_location"], scope, sources)
    facts = []
    for original in node["facts"]:
        fact = dict(original)
        fact["anchors"] = [excerpt(anchor, sources) or {**anchor, "quote": ""} for anchor in fact["anchors"]]
        if fact.get("calculation") is None:
            fact.pop("calculation", None)
        facts.append(fact)
    return {
        "id": node["id"], "description": node["description"], "role": "unknown", "scope": scope, "facts": facts,
    }, location


def proved_keys(action, sources):
    """Use the same scope and evidence basis for semantic and causal assertions."""
    keys = {"applicable_contract", "implementation_action", "causal_role",
            "compliant", "contract_inapplicable", "established_other_defect"}
    projected, _ = classifier.project_packet({"actions": [action]}, sources)
    _, positive, _, scoped, _, _ = pilot.collect_facts(projected["actions"][0], sources, action["scope"], keys)
    return positive & scoped


def proof_at(location, anchor, sources):
    source = sources[anchor["source_id"]]
    offset = source.get("original_start_line", 1) - 1
    return (location is not None and location["version"] == source["version"] and location["path"] == source["path"]
            and anchor["start_line"] + offset <= location["original_end_line"]
            and anchor["end_line"] + offset >= location["original_start_line"])


def site_key(location):
    return tuple(location[key] for key in ("version", "path", "original_start_line", "original_end_line"))


def overlapping_sites(first, second):
    return first[:2] == second[:2] and first[2] <= second[3] and second[2] <= first[3]


def implementation_sites(node, sources):
    """Identify the old positions that independently support this operation."""
    uses = {"confirmed_report": "confirmation", "verified_runtime": "runtime", "derived": "behavior"}
    return frozenset(
        site_key(position)
        for fact in node["verdict"]["facts"]
        if fact["key"] == "implementation_action" and fact["value"] and fact["claim_state"] in uses
        and anchored_basis(fact["claim_state"], fact.get("explanation"), fact["anchors"], sources, node["scope"])
        for anchor in fact["anchors"]
        if anchor["use"] == uses[fact["claim_state"]]
        and (position := action_position(anchor, node["scope"], sources)) is not None
    )


def report_position(action, verdict, sources, cards):
    """Locate a self-sufficient confirmation even when the model points to older code."""
    if action["scope"]["claim"] != "reported":
        return None
    keys = ["implementation_action", "established_other_defect"]
    if verdict["status"] == "leaf":
        keys.append(cards[verdict["pattern_id"]]["operation_fact"])
    for key in keys:
        for fact in verdict["facts"]:
            if fact["key"] != key or not fact["value"] or fact["claim_state"] != "confirmed_report":
                continue
            for anchor in fact["anchors"]:
                if anchor["use"] == "confirmation":
                    position = action_position(anchor, action["scope"], sources)
                    if position:
                        return position
    return None


def anchored_context(location, sources):
    source = sources.get(location["source_id"]) if location else None
    if source is None or source["kind"] not in {"code", "diff"}:
        return None
    scope = {"claim": "static", "version": source["version"], "path": source["path"]}
    return action_position(location, scope, sources)


def relation_supported(edge, nodes, sources):
    left = nodes[edge["from"]]
    kind, state, reason = edge["kind"], edge["evidence_level"], edge["explanation"]
    anchors = edge["evidence_refs"]
    if not pilot.nonempty(reason) or not anchors or any(anchor is None for anchor in anchors):
        return False
    if kind == "violates":
        return left["action_proven"] and anchored_basis(state, reason, anchors, sources, left["scope"])
    right = nodes[edge["to"]]
    if kind == "independent_of":
        locations = [node["source_location"] for node in (left, right)]
        if None in locations or state in {"observation", "hypothesis"} or not all(
                node["action_proven"] and node["causal_proof"] for node in (left, right)):
            return False
        expected_claim = {"verified_runtime": "runtime", "confirmed_report": "reported"}.get(state)
        if expected_claim and any(node["scope"]["claim"] != expected_claim for node in (left, right)):
            return False
        if overlapping_sites(*(site_key(location) for location in locations)):
            left_sites, right_sites = (implementation_sites(node, sources) for node in (left, right))
            left_distinct = {site for site in left_sites if not any(
                overlapping_sites(site, other) for other in right_sites)}
            right_distinct = {site for site in right_sites if not any(
                overlapping_sites(site, other) for other in left_sites)}
            return all(any(
                anchor["use"] != "context"
                and (position := action_position(anchor, node["scope"], sources)) is not None
                and site_key(position) in unique_sites
                for anchor in anchors
            ) for node, unique_sites in ((left, left_distinct), (right, right_distinct)))
        return all(any(
            anchor["use"] != "context" and proof_at(location, anchor, sources)
            and not proof_at(other_location, anchor, sources)
            and not pilot.check_anchor(anchor, sources, node["scope"]) for anchor in anchors)
                   for node, location, other_location in (
                       (left, locations[0], locations[1]), (right, locations[1], locations[0])))
    if kind in {"consumes", "supports"} and state == "observation":
        return left["source_location"] is not None and any(
            anchor["use"] != "context" and proof_at(left["source_location"], anchor, sources)
            and not pilot.check_anchor(anchor, sources, left["scope"]) for anchor in anchors
        )
    if kind in CAUSAL:
        if left["node_type"] == "downstream_effect":
            upstream = left["relation_proven"]
        else:
            upstream = left["action_proven"] or (left["implementation_proof"] and left["scope"] == right["scope"])
        if not upstream or not right["relation_proven"]:
            return False
    return any(anchored_basis(state, reason, anchors, sources, node["scope"]) for node in (left, right))


def can_reach(start, goal, adjacency):
    visited = set()
    remaining = [start]
    while remaining:
        node = remaining.pop()
        if node == goal:
            return True
        if node not in visited:
            visited.add(node)
            remaining.extend(successor for successor in adjacency.get(node, ()) if successor not in visited)
    return False


def resolve_relations(raw, nodes, sources):
    results, adjacency = [], defaultdict(set)
    seen = set()
    for edge in raw:
        kind, left, right = edge["kind"], edge["from"], edge["to"]
        # Symmetric edges have one identity even when the reader reverses their endpoints.
        ends = tuple(sorted((left, right))) if kind == "independent_of" else (left, right)
        key = (kind, ends)
        relationship = {**edge, "evidence_refs": [excerpt(ref, sources) for ref in edge["evidence_refs"]],
                        "supported": False, "issues": []}
        results.append(relationship)
        contract = kind == "violates" and right == "contract"
        if (key in seen or left == right or left not in nodes or kind not in RELATIONS
                or (right not in nodes and not contract)):
            relationship["issues"].append("invalid_or_duplicate_relation")
            continue
        seen.add(key)
        left_kind = nodes[left]["node_type"]
        right_kind = nodes[right]["node_type"] if right in nodes else None
        plausible = (
            kind == "independent_of" and left_kind in ROOTS and right_kind in ROOTS
            or kind in CAUSAL and left_kind in ROOTS | {"downstream_effect"} and right_kind == "downstream_effect"
            or kind in {"consumes", "supports"} and left_kind in {"supporting_operation", "downstream_effect"}
            or contract and left_kind in ROOTS
        )
        if not plausible or not relation_supported(relationship, nodes, sources):
            relationship["issues"].append("relation_requires_scoped_evidence")
            continue
        relationship["supported"] = True
        if kind in CAUSAL:
            adjacency[left].add(right)
    for relationship in results:
        if (relationship["supported"] and relationship["kind"] in CAUSAL
                and can_reach(relationship["to"], relationship["from"], adjacency)):
            relationship["supported"] = False
            relationship["issues"].append("cyclic_causal_relation")
    return results


def classify_node(node, action, position, verdict, sources, cards):
    references = [anchor for fact in action["facts"] for anchor in fact["anchors"]
                  if excerpt(anchor, sources) is not None]
    evidence = {fact["claim_state"] for fact in action["facts"]}
    proofs = proved_keys(action, sources) if verdict else set()
    context = None
    if position is None and verdict is not None:
        position = report_position(action, verdict, sources, cards)
        context = anchored_context(node["source_location"], sources)
    complete = position is not None and all(pilot.nonempty(node[key]) for key in (
        "expected_behavior", "observed_behavior", "violated_relation",
    ))
    mechanism_defect = verdict is not None and (
        verdict["status"] in {"leaf", "parent"} or verdict.get("outside_reason") == "outside_catalog"
    )
    known_boundary = bool(proofs & {"compliant", "contract_inapplicable"})
    has_contract = "applicable_contract" in proofs or (
        verdict is not None and verdict.get("outside_reason") == "outside_catalog"
        and "established_other_defect" in proofs
    )
    semantic_proof = complete and has_contract and not known_boundary
    implementation_proof = complete and "implementation_action" in proofs and not known_boundary
    action_proven = semantic_proof and implementation_proof
    modes = [] if verdict is None else verdict.get("supported_pattern_ids", [])
    if verdict and verdict["status"] == "leaf":
        modes = [verdict["pattern_id"]]
    return {
        "action_id": node["id"], "node_type": node["node_type"], "description": node["description"],
        "scope": action["scope"], "source_location": position, "context_source_location": context,
        "expected_behavior": node["expected_behavior"], "observed_behavior": node["observed_behavior"],
        "violated_relation": node["violated_relation"], "evidence_refs": references,
        "evidence_level": sorted(evidence), "mode_ids": modes, "effect_mode_ids": [], "verdict": verdict,
        "action_proven": action_proven, "implementation_proof": implementation_proof,
        "relation_proven": semantic_proof and (mechanism_defect or action_proven),
        "causal_proof": "causal_role" in proofs, "causal_role": "unknown", "independent_count": 0, "issues": [],
    }


def count_roots(nodes, edges, sources):
    roots = {}
    locations = {}
    independent = {frozenset((edge["from"], edge["to"])) for edge in edges
                   if edge["supported"] and edge["kind"] == "independent_of"}
    for node in nodes.values():
        if not (node["node_type"] in ROOTS and node["action_proven"] and node["causal_proof"]):
            continue
        action_id = node["action_id"]
        location = site_key(node["source_location"])
        sites = implementation_sites(node, sources)
        duplicates = [
            prior for prior, (prior_location, prior_sites) in locations.items()
            if frozenset((action_id, prior)) not in independent
            and overlapping_sites(location, prior_location)
            and any(overlapping_sites(site, prior_site) for site in sites for prior_site in prior_sites)
        ]
        if len(duplicates) == 1:
            node["issues"].append("duplicate_implementation_action")
            node["duplicate_of"], = duplicates
        else:
            locations[action_id] = (location, sites)
            roots[action_id] = node
    independent = {frozenset(nodes[action_id].get("duplicate_of", action_id) for action_id in pair)
                   for pair in independent}
    unresolved = {action for pair in combinations(roots, 2) if frozenset(pair) not in independent for action in pair}
    for action_id, node in roots.items():
        if action_id in unresolved:
            node["issues"].append("independence_unresolved")
        else:
            node["causal_role"] = "primary" if len(roots) == 1 else "independent"
            node["independent_count"] = 1


def assign_effects(nodes, edges):
    incoming = defaultdict(set)
    for edge in edges:
        if edge["supported"] and edge["kind"] in CAUSAL:
            upstream = nodes[edge["from"]]
            incoming[edge["to"]].add(upstream.get("duplicate_of", edge["from"]))
    for action_id, producers in incoming.items():
        nodes[action_id]["causal_role"] = "downstream"
        nodes[action_id]["upstream_ids"] = sorted(producers)
    for action_id, node in nodes.items():
        if node["node_type"] == "supporting_operation" and node["source_location"] is not None:
            node["causal_role"] = "support"
        if not node["independent_count"]:
            continue
        effects = set()
        for child in incoming:
            if can_reach(child, action_id, incoming):
                effects.update(nodes[child]["mode_ids"])
        node["effect_mode_ids"] = sorted(effects)


def attribute_supported_effects(nodes, edges, cards):
    """Attribute a proved local mechanism to its same-scope, evidenced cause."""
    for node in nodes.values():
        if (node["node_type"] not in ROOTS or not node["implementation_proof"]
                or node["verdict"]["status"] != "insufficient" or node["verdict"]["conflicts"]):
            continue
        effects = {edge["to"] for edge in edges if edge["supported"]
                   and edge["kind"] in CAUSAL and edge["from"] == node["action_id"]}
        eligible = [nodes[key] for key in effects if nodes[key]["scope"] == node["scope"]
                    and nodes[key]["verdict"]["status"] == "leaf" and nodes[key]["relation_proven"]]
        if len(eligible) != 1:
            continue
        effect, = eligible
        mode = effect["verdict"]["pattern_id"]
        card = cards[mode]
        contradicts = any(fact["claim_state"] not in {"observation", "hypothesis"} and (
            (not fact["value"] and fact["key"] in card["necessary"])
            or (fact["value"] and fact["key"] in card["excluded_by"])
        ) for fact in node["verdict"]["facts"])
        if contradicts:
            continue
        if any(edge["supported"] and edge["kind"] in CAUSAL
               and edge["to"] == effect["action_id"] and edge["from"] != node["action_id"] for edge in edges):
            continue
        direct = node["verdict"]
        node["direct_verdict"] = direct
        projection = {k: v for k, v in direct.items() if k not in classifier.RESULT_FIELDS}
        mechanism = effect["verdict"]
        projection.update({k: mechanism[k] for k in ("status", *classifier.RESULT_FIELDS) if k in mechanism})
        projection.update(missing=[], neighbors=mechanism["neighbors"])
        node.update(verdict=projection, mode_ids=effect["mode_ids"], action_proven=True,
                    relation_proven=True, mechanism_via=effect["action_id"])
        effect["attributed_to"] = node["action_id"]


def classify_case(case, extracted, catalog):
    sources = pilot.by_id(case["sources"], "source views")
    proposed = pilot.by_id(extracted["nodes"], "graph nodes")
    if not proposed or any(node["node_type"] not in KINDS for node in proposed.values()):
        raise ValueError("Each case requires valid action graph nodes")
    prepared = {key: prepare_node(node, sources) for key, node in proposed.items()}
    actions = [action for key, (action, _) in prepared.items() if proposed[key]["node_type"] != "supporting_operation"]
    if not actions:
        raise ValueError("Include a boundary or an unknown action for this case")
    packet = {"case_id": case["case_id"], "operator": extracted["operator"], "roles": extracted["roles"],
              "actions": actions, "fact_protocol": pilot.FACT_PROTOCOL}
    verdict, = classifier.classify_package({"cases": [case]}, [packet], catalog)
    matches = pilot.by_id(verdict["actions"], "mode verdicts")
    nodes = {key: classify_node(proposed[key], action, position, matches.get(key), sources, catalog["modes"])
             for key, (action, position) in prepared.items()}
    edges = resolve_relations(extracted["relations"], nodes, sources)
    attribute_supported_effects(nodes, edges, catalog["modes"])
    count_roots(nodes, edges, sources)
    assign_effects(nodes, edges)
    return {"case_id": case["case_id"], "operator": extracted["operator"], "source_sha256": pilot.digest(case),
            "facts_sha256": pilot.digest(extracted), "nodes": list(nodes.values()), "relations": edges,
            "independent_count": sum(node["independent_count"] for node in nodes.values())}


def classify_package(material, extracted):
    cases = pilot.by_id(material["cases"], "material cases", "case_id")
    packets = pilot.by_id(extracted["cases"], "graph packets", "case_id")
    if not cases or cases.keys() != packets.keys():
        raise ValueError("The graph must cover the exact original case inventory")
    catalog = classifier.read_json(classifier.CATALOG)
    return {"protocol": PROTOCOL, "catalog": classifier.NAMESPACE, "decision": classifier.DECISION_VERSION,
            "cases": [classify_case(case, packets[key], catalog) for key, case in cases.items()]}
