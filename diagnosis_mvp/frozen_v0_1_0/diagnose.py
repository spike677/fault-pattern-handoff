"""Run bounded operator diagnosis from scoped, structured observations."""

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Callable

VERSION = "0.1.0"
FAMILIES = ("interface", "plan", "layout", "numeric", "contribution", "timing")
DTYPE_BYTES = {
    "bool": 1, "int8": 1, "int16": 2, "int32": 4, "int64": 8,
    "float16": 2, "bfloat16": 2, "float32": 4, "float64": 8,
}
METHODS = ("adaptive", "fixed_route")


class BadEvidence(ValueError):
    """The supplied observations cannot establish this predicate."""


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def read_json(path):
    def reject_constant(value):
        raise BadEvidence(f"Nonfinite JSON number: {value}")

    return json.loads(Path(path).read_text(encoding="utf-8-sig"), parse_constant=reject_constant)


def validate_int(value, label):
    if type(value) is not int:
        raise BadEvidence(f"{label} must be an integer")
    return value


def validate_int_list(values, label):
    if not isinstance(values, list):
        raise BadEvidence(f"{label} must be a list")
    return [validate_int(x, label) for x in values]


def tokens(values):
    if not isinstance(values, list) or any(not isinstance(x, str) or not x for x in values):
        raise BadEvidence("Participant and contribution identities must be nonempty strings")
    return Counter(values)


def different(expected, observed):
    return canonical(expected) != canonical(observed), {"expected": expected, "observed": observed}


def plan_range(expected, observed):
    if not isinstance(expected, dict) or not isinstance(observed, dict):
        raise BadEvidence("A plan slice requires a unit and a half-open range")
    if expected.get("unit") not in ("element", "byte", "tile") or expected["unit"] != observed.get("unit"):
        raise BadEvidence("Plan slices have incompatible units")
    first = validate_int_list(expected.get("range"), "Plan range")
    second = validate_int_list(observed.get("range"), "Plan range")
    if any(len(span) != 2 or not 0 <= span[0] <= span[1] for span in (first, second)):
        raise BadEvidence("Invalid half-open plan range")
    return first != second, {"unit": expected["unit"], "expected": first, "observed": second}


def address_mapping(geometry, actual):
    if not isinstance(geometry, dict):
        raise BadEvidence("Expected shape, strides, index, and base element offset")
    if geometry.get("unit") != "element":
        raise BadEvidence("Layout offsets require element units")
    shape = validate_int_list(geometry.get("shape"), "Shape")
    strides = validate_int_list(geometry.get("strides"), "Stride")
    index = validate_int_list(geometry.get("index"), "Index")
    base = validate_int(geometry.get("base"), "Base")
    if not len(shape) == len(strides) == len(index):
        raise BadEvidence("Shape, strides and logical coordinates have different ranks")
    if any(not 0 <= coordinate < size for coordinate, size in zip(index, shape)):
        raise BadEvidence("Logical coordinate is out of the contracted domain")
    expected = base + sum(x * stride for x, stride in zip(index, strides))
    if not isinstance(actual, dict) or actual.get("unit") != "element":
        raise BadEvidence("Actual layout offset requires element units")
    observed = validate_int(actual.get("offset"), "Physical offset")
    return expected != observed, {"logical_index": index, "expected": expected, "observed": observed}


def finite_number(x):
    if type(x) not in (float, int) or not math.isfinite(x):
        raise BadEvidence("Numeric comparison requires finite numeric values")
    return x


def numeric_distance(actual, reference, tolerance):
    if not all(isinstance(x, dict) for x in (actual, reference, tolerance)):
        raise BadEvidence("Expected two typed value vectors and a tolerance")
    if not nonempty_text(actual.get("dtype")) or actual["dtype"] not in DTYPE_BYTES or actual["dtype"] != reference.get("dtype"):
        raise BadEvidence("Numeric vectors have incompatible dtypes")
    left, right = actual.get("values"), reference.get("values")
    if not isinstance(left, list) or not isinstance(right, list) or len(left) != len(right):
        raise BadEvidence("Numeric vectors must have the same length")
    atol, rtol = finite_number(tolerance.get("atol")), finite_number(tolerance.get("rtol"))
    if atol < 0 or rtol < 0:
        raise BadEvidence("Tolerance must be nonnegative")
    differences = []
    for i, (a, b) in enumerate(zip(left, right)):
        a, b = finite_number(a), finite_number(b)
        if abs(a - b) > atol + rtol * abs(b):
            differences.append(i)
    return bool(differences), {"differing_indices": differences, "checked_elements": len(left)}


def reference_basis(reference, input_kind):
    keys = ("reference_id", "state_id", "mapping_id")
    if (not isinstance(reference, dict) or reference.get("qualified") is not True
            or reference.get("input_kind") != input_kind
            or any(not nonempty_text(reference.get(key)) for key in keys)):
        raise BadEvidence("Reference needs a qualified implementation, state, mapping, and input scope")
    return tuple(reference[key] for key in keys)


def local_numeric(actual, reference, tolerance):
    reference_basis(reference, "OBSERVED")
    return numeric_distance(actual, reference, tolerance)


def unexpected_members(expected, actual):
    extras = tokens(actual).keys() - tokens(expected).keys()
    return bool(extras), {"unexpected_ids": sorted(extras)}


def contribution_counts(mode, expected, actual):
    e, o = tokens(expected), tokens(actual)
    if mode == "extra":
        changed = {x: o[x] - e[x] for x in e if o[x] > e[x]}
    else:
        changed = dict(e - o)
    return bool(changed), {"multiplicity_differences": changed}


def repeated_members(expected, actual):
    return contribution_counts("extra", expected, actual)


def missing_members(expected, actual):
    return contribution_counts("missing", expected, actual)


def participant_rounds(expected, actual):
    e, o = tokens(expected), tokens(actual)
    return e != o, {"missing": dict(e - o), "unexpected": dict(o - e)}


def shared_slot_lifetime(read, write):
    if not isinstance(read, dict) or not isinstance(write, dict):
        raise BadEvidence("Shared accesses require identities, ranges, and established ordering")
    for access in (read, write):
        if not isinstance(access.get("allocation"), str) or not access["allocation"]:
            raise BadEvidence("Allocation identity is missing")
        if access.get("unit") != "byte":
            raise BadEvidence("Shared access ranges require byte units")
    if read["allocation"] != write["allocation"]:
        return False, {"overlap": False, "reason": "different_allocations"}
    r = validate_int_list(read.get("range"), "Read range")
    w = validate_int_list(write.get("range"), "Write range")
    if any(len(span) != 2 or not 0 <= span[0] < span[1] for span in (r, w)):
        raise BadEvidence("Invalid shared byte interval")
    overlap = max(r[0], w[0]) < min(r[1], w[1])
    if not overlap:
        return False, {"overlap": False, "reason": "disjoint_ranges"}
    earlier = validate_int(read.get("generation"), "Read generation")
    later = validate_int(write.get("generation"), "Write generation")
    if later <= earlier:
        return False, {"overlap": True, "reason": "write_not_from_a_later_generation"}
    if not read.get("order_id") or read["order_id"] != write.get("order_id"):
        raise BadEvidence("Read and write have no established common order")
    read_done = validate_int(read.get("read_done"), "Read completion order")
    write_at = validate_int(write.get("write_at"), "Later write order")
    if read_done == write_at:
        raise BadEvidence("Read and write order is ambiguous")
    return write_at < read_done, {"overlap": True, "read_done": read_done, "write_at": write_at}


@dataclass(frozen=True)
class Rule:
    name: str
    family: str
    fields: tuple[str, ...]
    check: Callable


RULES = (
    Rule("INTERFACE_CONTRACT", "interface", ("interface.expected", "interface.observed"), different),
    Rule("PLAN_GENERATION", "plan", ("plan.expected", "plan.produced"), plan_range),
    Rule("PLAN_TRANSFER", "plan", ("plan.produced", "plan.received"), plan_range),
    Rule("PLAN_CONSUMPTION", "plan", ("plan.received", "plan.consumed"), plan_range),
    Rule("ADDRESS_MAPPING", "layout", ("layout.geometry", "layout.actual_offset"), address_mapping),
    Rule("LOCAL_NUMERIC_DEVIATION", "numeric", (
        "numeric.actual", "numeric.ref_observed", "numeric.tolerance"
    ), local_numeric),
    Rule("UNEXPECTED_CONTRIBUTION", "contribution", (
        "contribution.expected", "contribution.observed"
    ), unexpected_members),
    Rule("REPEATED_CONTRIBUTION", "contribution", (
        "contribution.expected", "contribution.observed"
    ), repeated_members),
    Rule("MISSING_CONTRIBUTION", "contribution", (
        "contribution.expected", "contribution.observed"
    ), missing_members),
    Rule("COLLECTIVE_PARTICIPATION", "timing", (
        "timing.expected_participants", "timing.observed_participants"
    ), participant_rounds),
    Rule("SHARED_SLOT_EARLY_REUSE", "timing", (
        "timing.read", "timing.later_write"
    ), shared_slot_lifetime),
)
OUTPUT_FIELDS = ("comparison.expected", "comparison.actual", "comparison.reference")
KNOWN_FIELDS = {field for rule in RULES for field in rule.fields} | set(OUTPUT_FIELDS) | {"numeric.ref_healthy"}
CONTRACT_FIELDS = {
    "interface.expected", "plan.expected", "layout.geometry", "numeric.tolerance",
    "contribution.expected", "timing.expected_participants", "comparison.expected",
}


def nonempty_text(value):
    return isinstance(value, str) and bool(value.strip())


def available_facts(case):
    available, conflicts, issues = {}, set(), []
    seen_ids = set()
    for item in case.get("observations", []):
        if not isinstance(item, dict):
            raise BadEvidence("Each observation must be an object")
        field, fact_id = item.get("field"), item.get("fact_id")
        if not nonempty_text(field) or field not in KNOWN_FIELDS or not nonempty_text(fact_id) or fact_id in seen_ids:
            raise BadEvidence("Unknown observation field, missing fact ID, or repeated fact ID")
        seen_ids.add(fact_id)
        if (item.get("call_id") != case["call_id"] or item.get("build") != case["build"]
                or not nonempty_text(item.get("source")) or "value" not in item
                or item.get("kind") not in ("OBSERVED", "REPORTED", "DERIVED", "CONTRACT")):
            issues.append({"fact_id": fact_id, "field": field, "reason": "missing_or_mismatched_provenance"})
            continue
        if item["kind"] == "CONTRACT" and field not in CONTRACT_FIELDS:
            issues.append({"fact_id": fact_id, "field": field, "reason": "contract_is_not_an_observation"})
            continue
        old = available.get(field)
        if old is not None and canonical(old["value"]) != canonical(item["value"]):
            conflicts.add(field)
            issues.append({"field": field, "reason": "conflicting_values",
                           "fact_ids": [old["fact_id"], fact_id]})
        available[field] = item
    return {k: v for k, v in available.items() if k not in conflicts}, issues, conflicts


def establish_scope(case):
    contract = case.get("contract", {})
    if not isinstance(contract, dict):
        return "UNKNOWN"
    if (not nonempty_text(contract.get("version")) or not nonempty_text(contract.get("source"))
            or contract.get("build") != case["build"]):
        return "UNKNOWN"
    status = contract.get("status")
    return status if status in ("APPLICABLE", "OUT_OF_SCOPE") else "UNKNOWN"


def evidence_citations(facts, fields):
    return [
        {key: facts[field][key] for key in ("fact_id", "field", "source", "kind")}
        for field in fields if field in facts
    ]


def inspect_rule(rule, facts, conflicts, scope):
    result = {
        "mechanism": rule.name, "family": rule.family,
        "judgment": "UNKNOWN", "evidence": evidence_citations(facts, rule.fields),
    }
    if scope != "APPLICABLE":
        result["reason"] = "contract_scope_" + scope.lower()
        return result
    missing = [f for f in rule.fields if f not in facts]
    if missing:
        result["missing_fields"] = missing
        result["reason"] = "conflict" if conflicts.intersection(missing) else "insufficient_observations"
        return result
    try:
        broken, details = rule.check(*(facts[f]["value"] for f in rule.fields))
    except (BadEvidence, OverflowError) as exc:
        result["reason"] = str(exc)
        return result
    result["judgment"] = "SUPPORTED" if broken else "EXCLUDED"
    result["details"] = details
    return result


def output_item(expected, left, right):
    if not all(isinstance(v, dict) for v in (expected, left, right)):
        raise BadEvidence("Output metadata must be objects")
    dtype = expected.get("dtype")
    shape = validate_int_list(expected.get("shape"), "Output shape")
    if not nonempty_text(dtype) or dtype not in DTYPE_BYTES or any(n < 0 for n in shape):
        raise BadEvidence("Unsupported expected dtype or shape")
    for output in (left, right):
        if output.get("dtype") != dtype or output.get("shape") != shape:
            raise BadEvidence("Output dtype or shape differs from the manifest")
    count = math.prod(shape)
    if expected.get("mode") == "BITWISE":
        try:
            bit_vectors = [bytes.fromhex(v.get("hex")) for v in (left, right)]
        except (TypeError, ValueError) as exc:
            raise BadEvidence("Bitwise output requires raw hexadecimal bytes") from exc
        if any(len(b) != count * DTYPE_BYTES[dtype] for b in bit_vectors):
            raise BadEvidence("Output bytes do not match the expected shape and dtype")
        return bit_vectors[0] != bit_vectors[1]
    if expected.get("mode") == "NUMERIC":
        if any(not isinstance(v.get("values"), list) or len(v["values"]) != count for v in (left, right)):
            raise BadEvidence("Output values do not match the expected shape")
        return numeric_distance(left, right, expected.get("tolerance"))[0]
    raise BadEvidence("Comparison mode must specify BITWISE or NUMERIC")


def compare_outputs(facts, scope):
    if not any(f in facts for f in OUTPUT_FIELDS):
        return {"status": "NOT_ASSESSED"}
    missing_fields = [f for f in OUTPUT_FIELDS if f not in facts]
    if scope != "APPLICABLE" or missing_fields:
        return {"status": "UNKNOWN", "missing_fields": missing_fields, "scope": scope}
    expected, actual, reference = (facts[f]["value"] for f in OUTPUT_FIELDS)
    citation = evidence_citations(facts, OUTPUT_FIELDS)
    if not all(isinstance(v, dict) for v in (expected, actual, reference)) or not expected:
        return {"status": "UNKNOWN", "reason": "invalid_output_manifest", "evidence": citation}
    missing = {"actual": sorted(expected.keys() - actual.keys()),
               "reference": sorted(expected.keys() - reference.keys())}
    if any(missing.values()):
        return {"status": "INCOMPLETE", "missing_outputs": missing, "evidence": citation}
    if set(actual) != set(expected) or set(reference) != set(expected):
        return {"status": "INCOMPATIBLE", "reason": "unexpected_output_identity", "evidence": citation}
    try:
        different_outputs = [key for key in sorted(expected) if output_item(expected[key], actual[key], reference[key])]
    except (BadEvidence, OverflowError) as exc:
        return {"status": "INCOMPATIBLE", "reason": str(exc), "evidence": citation}
    return {"status": "DIFFERENT" if different_outputs else "PASS",
            "different_outputs": different_outputs, "evidence": citation}


def numeric_stage(facts, scope, routes):
    fields = ("numeric.actual", "numeric.ref_observed", "numeric.ref_healthy", "numeric.tolerance")
    if "numeric" not in routes:
        return None
    missing = [f for f in fields if f not in facts]
    if missing or scope != "APPLICABLE":
        return {"status": "UNKNOWN", "missing_fields": missing}
    actual, observed, healthy, tolerance = (facts[f]["value"] for f in fields)
    try:
        if reference_basis(observed, "OBSERVED") != reference_basis(healthy, "HEALTHY"):
            raise BadEvidence("Both references must use the same implementation, state, and mapping")
        local = numeric_distance(actual, observed, tolerance)[0]
        propagated = numeric_distance(observed, healthy, tolerance)[0]
    except (BadEvidence, OverflowError) as exc:
        return {"status": "UNKNOWN", "reason": str(exc)}
    labels = {
        (False, False): "NO_DEVIATION", (False, True): "UPSTREAM_PROPAGATION",
        (True, False): "LOCAL_DEVIATION", (True, True): "LOCAL_AND_PROPAGATION",
    }
    return {"status": labels[(local, propagated)], "evidence": evidence_citations(facts, fields)}


def select_observation(results, routes, attempted, method):
    proposals = defaultdict(list)
    for item in results:
        if method == "fixed_route" and item["family"] != routes[0]:
            continue
        for field in item.get("missing_fields", []):
            if field not in attempted:
                proposals[field].append(item)
    if not proposals:
        return None

    def priority(field):
        items = proposals[field]
        ready = sum(len(item["missing_fields"]) == 1 for item in items)
        return (-ready, -len(items), routes.index(items[0]["family"]), field)

    field = min(proposals, key=priority)
    return {
        "field": field,
        "distinguishes": [item["mechanism"] for item in proposals[field]],
        "test": "Supply a same-build, same-call observation to support or contradict these local predicates",
    }


def diagnose(case, method="adaptive", attempted=()):
    if not isinstance(case, dict) or any(not nonempty_text(case.get(k)) for k in ("case_id", "family_id", "build", "call_id")):
        raise BadEvidence("A case requires case_id, family_id, build, and call_id")
    routes = case.get("routes")
    if (not isinstance(routes, list) or not routes or any(not nonempty_text(r) or r not in FAMILIES for r in routes)
            or len(routes) != len(set(routes))):
        raise BadEvidence("Declare a nonempty ordered list of distinct applicable route candidates")
    if method not in METHODS or not isinstance(case.get("observations", []), list):
        raise BadEvidence("Invalid method or observations list")
    facts, issues, conflicts = available_facts(case)
    scope = establish_scope(case)
    checks = [inspect_rule(rule, facts, conflicts, scope) for rule in RULES if rule.family in routes]
    supported = [c["mechanism"] for c in checks if c["judgment"] == "SUPPORTED"]
    if scope == "OUT_OF_SCOPE":
        outcome = "OUT_OF_SCOPE"
    elif supported:
        outcome = "SUPPORTED"
    elif all(c["judgment"] == "EXCLUDED" for c in checks):
        outcome = "NO_SUPPORTED_MECHANISM"
    else:
        outcome = "UNKNOWN"
    outputs = compare_outputs(facts, scope)
    stage = numeric_stage(facts, scope, routes)
    requests_made = set(attempted)
    next_observation = None
    if scope == "APPLICABLE":
        next_observation = select_observation(checks, routes, requests_made, method)
        eligible = routes if method == "adaptive" else routes[:1]
        field = "numeric.ref_healthy"
        if (next_observation is None and "numeric" in eligible and field not in requests_made
                and stage.get("missing_fields") == [field]):
            next_observation = {
                "field": field, "distinguishes": ["LOCAL_DEVIATION", "UPSTREAM_PROPAGATION"],
                "test": "Evaluate the same reference on healthy input with the same state and mapping",
            }
    return {
        "version": VERSION, "case_id": case["case_id"], "family_id": case["family_id"],
        "input_sha256": hashlib.sha256(canonical(case).encode()).hexdigest(),
        "scope": scope, "outcome": outcome, "supported_mechanisms": supported,
        "checks": checks, "output_check": outputs, "numeric_stage": stage,
        "next_observation": next_observation, "evidence_issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("--method", choices=METHODS, default="adaptive")
    options = parser.parse_args()
    try:
        result = diagnose(read_json(options.case), options.method)
    except (BadEvidence, OSError, ValueError) as exc:
        print(f"Invalid diagnosis input: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

