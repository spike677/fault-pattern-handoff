"""Bind a separately reviewed old-code chain in a directed exercise."""

from . import graph


STEPS = ("contract", "entry", "forwarding", "implementation", "consumer")
ACTION_FIELDS = ("description", "expected_behavior", "observed_behavior", "violated_relation")
REQUIRED_FACTS = {"applicable_contract", "implementation_action", "causal_role"}


def apply_review(case, extraction, action_id, review):
    """Project a frozen review onto one unresolved action without editing its capture."""
    if case["case_id"] != extraction["case_id"] or case["case_id"] != review["case_id"]:
        raise ValueError("The review and the captured action must belong to the same case")
    sources = graph.pilot.by_id(case["sources"], "source views")
    nodes = graph.pilot.by_id(extraction["nodes"], "graph nodes")
    node = nodes.get(action_id)
    if node is None or node["node_type"] != "unknown_action":
        raise ValueError("The reviewed chain must target the captured unresolved action")

    chain = review["chain"]
    if set(chain) != set(STEPS) or any(not chain[step] for step in STEPS):
        raise ValueError("The reviewed chain must bind the contract and every implementation step")

    anchors = []
    for step in STEPS:
        use = "requirement" if step == "contract" else "behavior"
        for location in chain[step]:
            anchor = graph.excerpt(location, sources)
            if anchor is None:
                raise ValueError(f"The reviewed {step} span is missing")
            source = sources[anchor["source_id"]]
            expected_digest = review["source_digests"].get(source["id"])
            allowed = {"contract", "code"} if step == "contract" else {"code"}
            if (source["version"] != review["version"] or source["kind"] not in allowed
                    or graph.pilot.digest(source) != expected_digest):
                raise ValueError(f"The reviewed {step} view is outside the pinned old source")
            anchors.append({**location, "use": use})

    assertions = review["facts"]
    if not REQUIRED_FACTS <= assertions.keys() or not all(map(graph.pilot.nonempty, assertions.values())):
        raise ValueError("Review needs sourced contract, implementation and causal assertions")
    statement = {field: review["statement"].get(field) for field in ACTION_FIELDS}
    if not all(map(graph.pilot.nonempty, statement.values())):
        raise ValueError("Review needs the expected and actual behavior of the bound action")

    position = chain["implementation"][0]
    replacement = {
        **node, **statement, "node_type": "root_action", "source_location": position,
        "scope": {"source_id": position["source_id"], "claim": "static", "build": None, "call_id": None},
        "facts": [{"key": key, "value": True, "claim_state": "derived",
                   "explanation": explanation, "anchors": anchors}
                  for key, explanation in assertions.items()],
    }
    return {**extraction, "nodes": [replacement if row["id"] == action_id else row for row in extraction["nodes"]]}
