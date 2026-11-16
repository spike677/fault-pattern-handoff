"""Verify candidate evidence references and recompute local mechanism contrasts."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct


HERE = Path(__file__).resolve().parent
CANDIDATE = HERE.parents[2]
REVIEW = HERE / "candidate_review.json"
STAGED_PREFIX = Path("work/classification-v041-20261116/candidate")
DECISIONS = {"REUSE", "REFINE", "SPLIT", "MERGE", "NEW_CANDIDATE", "UNRESOLVED"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def locate(data, pointer):
    for key in pointer.split("/")[1:]:
        data = data[int(key)] if isinstance(data, list) else data[key]
    return data


def load_sources(review, workspace):
    sources = {}
    for key, name in review["source_files"].items():
        relative = Path(name)
        path = (CANDIDATE / relative.relative_to(STAGED_PREFIX) if relative.is_relative_to(STAGED_PREFIX)
                else workspace / relative)
        payload = path.read_bytes()
        require(hashlib.sha256(payload).hexdigest() == review["source_sha256"][key],
                f"Source content changed: {path}")
        sources[key] = json.loads(payload)
    return sources


def verify_evidence(ref, sources):
    source = ref["source"]
    package = sources[source]
    if source == "v16_ex":
        record = locate(package, "/".join(ref["pointer"].split("/")[:3]))
        evidence = locate(package, ref["pointer"])
        require(ref["case"] == record["lead_id"], f"Wrong V16 case: {ref['case']}")
        digest = hashlib.sha256(evidence["full_diff"].encode("utf-8")).hexdigest()
        require(digest == evidence["diff_sha256"], f"V16 patch changed: {ref['case']}")
        lineage = sources["lineage_v04"]["ex_by_id"][ref["case"]]
        require(any(row["diff_sha256"] == digest and row["fixed_repair_commit"] == evidence["fixed_commit"]
                    for row in lineage["patch_anchors"]), f"V16 patch unbound: {ref['case']}")
    elif source == "v16_code":
        record = locate(package, "/".join(ref["pointer"].split("/")[:3]))
        lineage = sources["lineage_v04"]["ex_by_id"].get(ref["case"], {})
        identity = lineage.get("mechanism_id", ref["case"])
        require(identity == record["mechanism_id"], f"Wrong code evidence: {ref['case']}")
        locate(package, ref["pointer"])
    else:
        case, = (row for row in package["cases"] if row["case_id"] == ref["case"])
        items = {item["id"]: item for item in case["sources"]}
        require(all(items[source_id]["text"].strip() for source_id in ref["case_sources"]),
                f"Empty evidence excerpt: {ref['case']}")


def verify_frozen_near_cases(score):
    expected = {
        "V402": [("leaf:MECH-v0.3:C1", "downstream", False), ("leaf:MECH-v0.3:P1", "primary", True)],
        "V403": [("leaf:MECH-v0.3:L2", "independent", True)] * 2,
        "V406": [("outside:outside_catalog", "primary", True)],
    }
    require(len(score["runs"]) == 2, "Two frozen scores are required")
    for run in score["runs"]:
        cases = {case["case_id"]: case for case in run["cases"]}
        for case_id, expected_actions in expected.items():
            case = cases[case_id]
            actual = sorted((a["actual"], a["predicted_role"], a["count_as_independent"])
                            for a in case["actions"])
            require(case["strict"] and actual == expected_actions, f"Frozen result differs: {case_id}")


def binary_float(format_code, value):
    try:
        return struct.unpack(format_code, struct.pack(format_code, float(value)))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def recompute_boundaries():
    values = (2048, 1, 1)
    state = 0
    for contribution in values:
        state = binary_float("<e", state + contribution)
    require(state == 2048 and sum(values) == 2050, "NUM-01 state rounding witness")
    require(binary_float("<e", 512) == 512 and math.isinf(binary_float("<e", 512**2)),
            "V406 overflow must occur after the representable local norm")

    row = (4095.5, 4096.5)
    mean = binary_float("<f", sum(row) / len(row))
    moment = binary_float("<f", sum(x * x for x in row) / len(row))
    raw = moment - mean * mean
    centered = binary_float("<f", sum((x - mean) ** 2 for x in row) / len(row))
    require(raw == 0 and centered == 0.25, "NUM-02 moment cancellation witness")

    produced = (0.2, 0.8)
    old_destination = (0.9, 0.1)
    intended_expert = max(range(2), key=produced.__getitem__)
    old_expert = max(range(2), key=old_destination.__getitem__)
    require((intended_expert, old_expert) == (1, 0), "CTRL-01 source identity witness")

    capacity, row_bytes = 6, 4
    initial_factor = capacity // row_bytes
    old_first_candidate = initial_factor - 1
    require(old_first_candidate == 0 and initial_factor == 1 and capacity - row_bytes > 0,
            "CTRL-02 first tested factor witness")

    group, first_s1, boundary, active_s1, span = 5, 1011, 1023, 1024, 64
    first_row = first_s1 * group
    expected_rows = max(0, min(first_row + span, active_s1 * group) - max(first_row, boundary * group))
    old_enters_tail = first_s1 + span // group > boundary
    require(expected_rows == 4 and not old_enters_tail, "ADDR-01 fused interval witness")

    stored = struct.pack("<f", 1.0)
    low_bf16 = int.from_bytes(stored[:2], "little")
    require(low_bf16 == 0 and struct.unpack("<f", stored)[0] == 1,
            "REP-01 same address read-width witness")

    completed_flag = 1
    old_publish, old_wait = completed_flag, completed_flag
    published_with_generation, wait_generation = completed_flag + 10, completed_flag + 11
    require(old_publish == old_wait and published_with_generation != wait_generation,
            "SYNC-01 stale flag witness")

    return {
        "half_running_sum": {"half_state": state, "wide_state": sum(values), "v406_square": "262144 -> +inf in FP16"},
        "raw_moment_cancellation": {"raw": raw, "centered": centered},
        "buffer_source_identity": {"intended_expert": intended_expert, "old_expert": old_expert},
        "plan_candidate_order": {"first_legal_factor": initial_factor, "first_old_factor": old_first_candidate},
        "fused_row_intersection": {"required_count": expected_rows, "old_count": 0},
        "scalar_representation": {"stored_float": 1.0, "decoded_bf16": low_bf16},
        "notification_generation": {"old_protocol_accepts_stale": True, "tagged_protocol_accepts_stale": False},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=CANDIDATE.parents[2])
    args = parser.parse_args()
    review = json.loads(REVIEW.read_bytes())
    sources = load_sources(review, args.workspace)
    current = json.loads((HERE.parent / "candidate_registry.json").read_bytes())
    original_ids = sorted(row["id"] for row in current["proposals"])
    require(sorted(row["id"] for row in review["reviews"]) == original_ids,
            "Each original candidate must have one review")
    require(review["catalog_baseline"] == "MECH-v0.3" and review["status"] == "PROPOSED",
            "Only proposal review is in scope")
    results = recompute_boundaries()
    count = 0
    for row in review["reviews"]:
        require(row["decision"] in DECISIONS, f"Unknown review decision: {row['id']}")
        require(row["admission"]["classifier_regression"] == "PENDING", f"Unexpected release claim: {row['id']}")
        require(row["regression"]["check"] in results, f"Missing boundary fixture: {row['id']}")
        require({item["role"] for item in row["evidence"]} >= {"positive", "closest_negative"},
                f"Missing real comparison: {row['id']}")
        for ref in row["evidence"]:
            verify_evidence(ref, sources)
            count += 1
    verify_frozen_near_cases(sources["V_score"])
    print(json.dumps({
        "reviewed_candidates": len(original_ids),
        "verified_source_files": len(sources),
        "verified_source_references": count,
        "verified_frozen_near_cases": 3,
        "boundary_checks": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
