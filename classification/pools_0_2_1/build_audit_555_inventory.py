"""Build a provenance-only register from the 555-case collection snapshot."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[3]
SOURCE = (
    ROOT / "fault-evidence-audit-codex-initial-public-release" / "work" / "evidence_gap_recheck_16ce36a"
)
DEFAULT_OUT = Path(__file__).with_name("audit_555_inventory.json")
RESOURCE = re.compile(r"/([^/]+)/([^/]+)/(issues|merge_requests|pulls?)/([0-9]+)/?")
INPUT_FILES = ("cases.jsonl", "case_components.jsonl", "audit_summary.json")


def read_rows(path):
    with path.open(encoding="utf-8-sig") as stream:
        return {line_no: json.loads(line) for line_no, line in enumerate(stream, 1) if line.strip()}


def lineage_key(url, expected):
    locator = urlsplit(url)
    path = RESOURCE.fullmatch(locator.path)
    if locator.scheme != "https" or locator.netloc.lower() != "gitcode.com" or path is None:
        raise ValueError(f"Unrecognized {expected} locator format")
    owner, repo, resource, number = path.groups()
    actual = "event" if resource == "issues" else "patch"
    if actual != expected:
        raise ValueError(f"Unrecognized {expected} resource type")
    separator = "#" if actual == "event" else "!"
    return f"{actual}:{locator.netloc.lower()}/{owner.lower()}/{repo.lower()}{separator}{int(number)}"


def count_identity(rows, role):
    frequency = Counter(key for row in rows for key, value in row["lineage_roles"].items() if value == role)
    return {
        "distinct_keys": len(frequency),
        "rows_with_key": sum(frequency.values()),
        "keys_repeated": sum(count > 1 for count in frequency.values()),
        "records_beyond_first_occurrence": sum(count - 1 for count in frequency.values()),
    }


def build(source):
    files = {name: source / name for name in INPUT_FILES}
    cases = read_rows(files["cases.jsonl"])
    components = read_rows(files["case_components.jsonl"])
    audit = json.loads(files["audit_summary.json"].read_text(encoding="utf-8-sig"))
    joined = {(row["audit_id"], row["case_id"]): (line, row) for line, row in components.items()}
    case_keys = {(row["audit_id"], row["case_id"]) for row in cases.values()}
    if len(cases) != len(joined) or len(components) != len(joined) or case_keys != set(joined):
        raise ValueError("The case and component rows do not join one to one")

    records = []
    for line, case in cases.items():
        component_line, component = joined[(case["audit_id"], case["case_id"])]
        event = lineage_key(case["issue_url"], "event")
        roles = {event: "primary_event"}
        if case["source_pr_url"]:
            roles[lineage_key(case["source_pr_url"], "patch")] = "associated_source_patch"
        record = {
            "record_id": f"audit-555:{case['case_id']}",
            "source_path": files["cases.jsonl"].as_posix(),
            "locator": f"line:{line}",
            "lineage_keys": list(roles),
            "lineage_roles": roles,
            "pointer": False,
            "input_status": case["input_status"],
            "component_locator": f"line:{component_line}",
            "mechanism_completeness": component["necessary_mechanism_evidence_completeness"],
            "semantic_review_completed_at_snapshot": component["semantic_review_completed"],
            "device_validation_completed_at_snapshot": component["device_validation_completed"],
            "component_gaps_at_snapshot": component["has_component_gaps"],
            "registered_references": component["registered_reference_count"],
            "registered_refs_without_payload": component["registered_references_without_payload"],
            "active_refs_without_payload": component["active_source_references_without_payload"],
        }
        if record["registered_references"] != len(case["source_refs"]):
            raise ValueError(f"Inconsistent source-reference metadata at line {line}")
        records.append(record)
    summary = {
        "rows": len(records),
        "primary_event_keys": count_identity(records, "primary_event"),
        "associated_patch_keys": count_identity(records, "associated_source_patch"),
        "input_status_counts": dict(Counter(row["input_status"] for row in records)),
        "mechanism_completeness": dict(Counter(row["mechanism_completeness"] for row in records)),
        "cases_with_component_gaps": sum(row["component_gaps_at_snapshot"] for row in records),
        "cases_with_active_missing_refs": sum(row["active_refs_without_payload"] > 0 for row in records),
        "cases_with_only_optional_missing_refs": sum(
            row["registered_refs_without_payload"] > 0 and row["active_refs_without_payload"] == 0
            for row in records
        ),
        "cases_with_no_registered_payload_gap": sum(row["registered_refs_without_payload"] == 0 for row in records),
        "cases_semantically_reviewed": sum(row["semantic_review_completed_at_snapshot"] for row in records),
        "cases_device_validated": sum(row["device_validation_completed_at_snapshot"] for row in records),
        "source_ref_count": sum(row["registered_references"] for row in records),
        "missing_source_refs": sum(row["registered_refs_without_payload"] for row in records),
        "active_missing_source_refs": sum(row["active_refs_without_payload"] for row in records),
    }
    expected_fields = (
        "mechanism_completeness", "cases_with_component_gaps", "cases_with_active_missing_refs",
        "cases_with_only_optional_missing_refs", "cases_with_no_registered_payload_gap",
        "source_ref_count", "missing_source_refs", "active_missing_source_refs",
    )
    if len(records) != audit["case_count"] or any(summary[field] != audit[field] for field in expected_fields):
        raise ValueError("Case/component metadata disagrees with audit_summary.json")
    return {
        "collection": "audit_555_16ce36a",
        "summary": summary,
        "sources": [
            {"kind": name, "path": path.as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for name, path in files.items()
        ],
        "boundary": (
            "Only case-owned issue_url and directly associated source_pr_url supply lineage keys. "
            "They are exact-source grouping hints. Event-family independence, exposure and sample readiness "
            "remain subject to curator review. Collection or possession of payloads does not establish mechanism evidence."
        ),
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true", help="Compare the existing output against the source metadata.")
    args = parser.parse_args()
    register = build(args.source_dir.resolve(strict=True))
    digestible = (json.dumps(register, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.check:
        if args.out.read_bytes() != digestible:
            raise ValueError("Inventory bytes differ from the current source metadata")
    else:
        with args.out.open("xb") as stream:
            stream.write(digestible)
    print(json.dumps(register["summary"], ensure_ascii=False))
    print(f"sha256 {hashlib.sha256(digestible).hexdigest()}")


if __name__ == "__main__":
    main()
