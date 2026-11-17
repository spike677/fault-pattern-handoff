"""Project the Work source audit into a separately scored original-A reference."""

import argparse
from pathlib import Path
import re

from . import graph, workflow


common = workflow.common
SPAN = re.compile(r"(s[0-9]+):([0-9]+)(?:-([0-9]+))?")


def verify_source_refs(refs, sources):
    for ref in refs:
        position = SPAN.fullmatch(ref)
        if not position:
            raise ValueError(f"Original-A audit has a non-original source ref: {ref}")
        source_id, start, end = position.groups()
        window = {"source_id": source_id, "start_line": int(start), "end_line": int(end or start)}
        if graph.excerpt(window, sources) is None:
            raise ValueError(f"Original-A audit has an invalid source ref: {ref}")


def allowed_verdict(assessment):
    status = assessment["status"]
    if status == "leaf":
        mode, = assessment["mode_ids"]
        return {"status": "leaf", "pattern_id": mode}
    if status == "parent":
        return {"status": "parent", "parent_id": assessment["parent_id"]}
    if status in {"outside_catalog", "compliant", "inapplicable"}:
        return {"status": "outside", "outside_reason": status}
    if status != "insufficient":
        raise ValueError(f"Unexpected Work assessment status: {status}")
    return {"status": status}


def reference_case(audit, packet, original):
    sources = graph.pilot.by_id(packet["sources"], "source views")
    assessed = [node for node in audit["nodes"] if node["availability"] == "original" and node.get("assessment")]
    root_count = sum(node["independent_count"] for node in assessed)
    rows = []
    for node in assessed:
        refs = node["evidence_refs"]
        verify_source_refs(refs, sources)
        verdict = allowed_verdict(node["assessment"])
        role = "unknown"
        if node["independent_count"]:
            role = "independent" if root_count > 1 else "primary"
        if node["type"] == "downstream_effect":
            role = "downstream"
        row = {
            "id": node["action_id"],
            "specific_action": f"{node['subject']}。{node['observed_behavior']}" if role != "unknown" else None,
            "role": role, "allowed": [verdict],
            "rationale": node["assessment"]["reason"], "decisive_facts": refs,
            "near_neighbor": node["assessment"]["nearby"],
            "expected_behavior": node["expected_behavior"], "observed_behavior": node["observed_behavior"],
            "violated_relation": node["violated_relation"], "consumer": node["consumer"],
        }
        if role == "downstream":
            row["upstream_ids"] = sorted({edge["from"] for edge in audit["edges"]
                                          if edge["to"] == node["action_id"] and edge["relation"] in graph.CAUSAL
                                          and edge["availability"] == "original"})
        rows.append(row)
    metadata = {key: original[key] for key in ("case_id", "family_id", "operator", "lineage")}
    return {**metadata, "root_order_unspecified": root_count > 1, "actions": rows,
            "source_scope": audit["scope"], "semantic_context": [
                {key: node[key] for key in ("action_id", "type", "subject", "consumer", "evidence_refs")}
                for node in audit["nodes"] if node["availability"] == "original" and node.get("assessment") is None
            ]}


def build(work, source, baseline, output):
    inventory = common.read_json(work / "baseline_manifest.json")
    if (inventory["files"]["a-public/A.json"] != common.digest(source)
            or inventory["files"]["custody/B.json"] != common.digest(baseline)):
        raise ValueError("The Work audit and source/reference generation do not match")
    material = common.a_cases(source)
    old = graph.pilot.by_id(common.read_json(baseline)["cases"], "baseline answers", "case_id")
    files = {path.stem: path for path in (work / "case_reconstruction").glob("*.json")}
    if files.keys() != old.keys() or files.keys() != material.keys():
        raise ValueError("Work audit inventory differs from the frozen 13 cases")
    cases = []
    for case_id, packet in material.items():
        audit = common.read_json(files[case_id])
        if audit["case_id"] != case_id:
            raise ValueError("Work audit ID differs from its file name")
        cases.append(reference_case(audit, packet, old[case_id]))
    common.write_record(output, {
        "reference": "work_audited_original_a", "scope": "exercise_only",
        "a_sha256": common.digest(source), "original_b_sha256": common.digest(baseline),
        "work_case_reconstructions": {name: common.digest(path) for name, path in sorted(files.items())},
        "cases": cases,
    })


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("work", "source", "baseline", "output"):
        cli.add_argument(name, type=Path)
    args = cli.parse_args()
    build(args.work, args.source, args.baseline, args.output)


if __name__ == "__main__":
    main()
