"""Read action facts and supporting operations from the v0.4.2 response."""

from copy import deepcopy

from proposals.numeric_validation.classify_candidates import (
    CLASSIFICATION, DECISIVE_FACTS, classify_candidates, load,
)
from classify import ROOT_ROLES, by_id, check_anchor, collect_facts, nonempty
from validation_0_3_1.reader_v04.readback import packets_from_response


BASE_SCHEMA = CLASSIFICATION / "validation_0_3_1" / "reader_v04" / "RESPONSE.json"


def response_schema():
    schema = load(BASE_SCHEMA)
    definitions = schema["$defs"]
    keys = definitions["fact"]["properties"]["key"]["enum"]
    keys.extend(sorted(DECISIVE_FACTS - set(keys)))
    definitions["supporting_operation"] = {
        "type": "object",
        "properties": {
            "action_id": {"type": "string"},
            "description": {"type": "string"},
            "anchors": {"type": "array", "items": {"$ref": "#/$defs/anchor"}},
        },
        "required": ["action_id", "description", "anchors"],
        "additionalProperties": False,
    }
    packet = schema["properties"]["cases"]["items"]
    packet["properties"]["supporting_operations"] = {
        "type": "array", "items": {"$ref": "#/$defs/supporting_operation"},
    }
    packet["required"].append("supporting_operations")
    return schema


def validate_support(operation, actions, sources):
    linked = actions.get(operation["action_id"])
    if linked is None:
        return ["unknown_support_action"]
    issues = []
    if not nonempty(operation["description"]):
        issues.append("missing_support_description")
    if not operation["anchors"]:
        issues.append("missing_support_anchors")
    for anchor in operation["anchors"]:
        source = sources.get(anchor["source_id"])
        lines = source["text"].splitlines() if source else []
        start, end = anchor["start_line"], anchor["end_line"]
        valid_range = type(start) is int and type(end) is int and 1 <= start <= end <= len(lines)
        anchor["quote"] = "\n".join(lines[start - 1:end]) if valid_range else ""
        error = check_anchor(anchor, sources, linked["scope"])
        if error:
            issues.append(error)
    return issues


def validate_readback(package, packets, support, decisions):
    cases = by_id(package["cases"], "material cases", "case_id")
    by_case = by_id(decisions["cases"], "case decisions", "case_id")
    issues = []
    for packet in packets:
        case_id = packet["case_id"]
        sources = by_id(cases[case_id]["sources"], "sources")
        actions = by_id(packet["actions"], "actions")
        results = by_id(by_case[case_id]["actions"], "decisions", "action_id")
        for action in actions.values():
            action_id = action["id"]
            decision = results[action_id]
            role = action["role"]
            codes = []
            if role in ROOT_ROLES:
                _, positive, _, scoped, _, _ = collect_facts(action, sources, action["scope"], DECISIVE_FACTS)
                if "implementation_action" not in positive & scoped:
                    codes.append("unproven_implementation_action")
                if decision["role"] != role:
                    codes.append("unproven_root_role")
            if role == "downstream" and decision["role"] != "downstream":
                codes.append("unsupported_downstream_effect")
            issues.extend({"case_id": case_id, "action_id": action_id, "code": code} for code in codes)
        for operation in support[case_id]:
            codes = validate_support(operation, actions, sources)
            issues.extend({"case_id": case_id, "action_id": operation["action_id"], "code": code}
                          for code in codes)
    return issues


def decode_response(package, response, catalog):
    response = deepcopy(response)
    support = {packet["case_id"]: packet.pop("supporting_operations") for packet in response["cases"]}
    facts, notes = packets_from_response(package, response)
    decisions = classify_candidates(package, facts, catalog)
    issues = validate_readback(package, facts, support, decisions)
    return {"facts": facts, "supporting_operations": support, "decisions": decisions,
            "reader_issues": issues}, notes
