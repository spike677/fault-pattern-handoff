"""Inventory pinned fault_review catalog metadata without exporting case prose."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


REVISION = "b78b2a232ed28377a64ddbe0a7cde48fe99c3a47"
WORK = Path(
    "fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114"
)
AUDIT = WORK / "rule_review_510601f/research/fault-review-catalog-audit.md"
MASTERS = {
    "inference": (1184, 1, "b8116a737b22c5485faef4cbabbe22890c5db400"),
    "training": (221, 0, "e8b483c30ddb70e5d952f74bfb5dc8753efb2f70"),
}
ENTRY = re.compile(r"^### ([A-Z][A-Z0-9-]*\.\d+|\d+\.\d+) \x60[A-Za-z0-9_]+\x60")
FIELD = re.compile(r"^- \*\*(.+?)\*\*[：:]\s*(.*)$")
COVERAGE = re.compile(r"Cov\s*[：:]\s*\x60([^\x60]+)\x60")
REFERENCE = re.compile(
    r"https://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)/(issues|pull)/(\d+)(?![\w/.-])",
    re.ASCII | re.IGNORECASE,
)
STANDALONE = re.compile(
    r"(?P<link>\[[^\]]+\]\()?(?:<)?(?P<url>https://(?:www\.)?github\.com/"
    r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(?:issues|pull)/\d+(?:[?#][^>\s)]*)?)"
    r"(?:>)?(?(link)\))[。.!！]?"
)
# Explicit mappings from already-reviewed rows, not inferred from co-citations.
REVIEWED = {
    ("inference", "6.23"): (29, "event:github.com/sgl-project/sglang#33268"),
    ("inference", "8.19"): (29, "event:github.com/sgl-project/sglang#33268"),
    ("inference", "6.185"): (29, "event:github.com/vllm-project/vllm#55221"),
    ("inference", "8.62"): (29, "event:github.com/vllm-project/vllm#55221"),
    ("inference", "1.24"): (35, "patch:github.com/tenstorrent/tt-metal!51903"),
    ("inference", "5.26"): (36, "event:github.com/sgl-project/sglang#37187",
                            "patch:github.com/sgl-project/sglang!37199"),
    ("inference", "8.80"): (37, "event:github.com/flashinfer-ai/flashinfer#5107"),
    ("inference", "5.39"): (38, "event:github.com/vllm-project/vllm#57130"),
    ("inference", "8.88"): (38, "event:github.com/flashinfer-ai/flashinfer#5260"),
    ("inference", "7.75"): (38, "event:github.com/vllm-project/vllm#55534"),
    ("inference", "8.57"): (39, "event:github.com/tenstorrent/tt-metal#54833"),
    ("training", "PAR.01"): (40, "event:github.com/deepspeedai/deepspeed#8224"),
    ("training", "PAR.02"): (40,),
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def keys(text):
    result = set()
    for owner, repository, kind, number in REFERENCE.findall(text):
        repo = f"github.com/{owner.lower()}/{repository.lower()}"
        result.add(f"event:{repo}#{number}" if kind.lower() == "issues" else f"patch:{repo}!{number}")
    return result


def record(edition, row, file, audit, audit_lines):
    record_key, line_no = row["identity"]
    meta = row["meta"]
    coverage = COVERAGE.search(meta)
    cov = coverage[1].lower() if coverage else ""
    pointer = (
        row["pointer_marker"]
        and cov == "existing"
        and bool(re.search(r"触发\s*\x60n/a\x60", meta, re.IGNORECASE))
        and not any(f"\x60{label}\x60" in meta for label in ("verified", "documented", "speculative"))
    )
    source = "\n".join(row["source"])
    references = keys(source)
    direct = STANDALONE.fullmatch(source.strip())
    own_keys = keys(direct["url"]) if direct and not pointer else set()
    item = {
        "record_id": f"fault_review:{edition}:{record_key}",
        "source_path": file.as_posix(),
        "locator": f"L{line_no}",
        "lineage_keys": [],
        "source_reference_keys": sorted(references),
        "pointer": pointer,
    }
    if reviewed := REVIEWED.get((edition, record_key)):
        line, *documented = reviewed
        if not set(documented) <= keys(audit_lines[line - 1]):
            raise ValueError(f"Reviewed locator drift for fault_review:{edition}:{record_key}")
        own_keys.update(documented)
        item.update(
            known_development_exposure=True,
            exposure_reference=f"{audit.as_posix()}:{line}",
        )
    if cov.startswith("var:"):
        item["cross_reference_hint"] = "catalog_variant"
    if pointer:
        item["pointer_target_collection_hint"] = "fault_review:training"
    item["lineage_keys"] = sorted(own_keys)
    return item


def extract(data, edition, file, audit, audit_lines):
    items, row = [], None
    source_field = False
    for number, line in enumerate(data.decode("utf-8-sig").splitlines(), start=1):
        header = ENTRY.match(line)
        if header or line.startswith("## "):
            if row:
                items.append(record(edition, row, file, audit, audit_lines))
            row = {"identity": (header[1], number), "meta": "", "source": [],
                   "pointer_marker": False} if header else None
            source_field = False
            continue
        if not row:
            continue
        if not row["meta"] and ("stage:" in line or "置信度" in line or "· Cov" in line):
            row["meta"] = line
        if "不是新故障" in line or "cited for completeness; not a new entry" in line.lower():
            row["pointer_marker"] = True
        field = FIELD.match(line)
        if field:
            source_field = field[1].strip() == "来源"
            if source_field:
                row["source"] = [field[2].strip()]
        elif source_field and line.strip() and not line.startswith("###"):
            row["source"].append(line)
    if row:
        items.append(record(edition, row, file, audit, audit_lines))
    return items


def summarize(records):
    citations = Counter(key for item in records for key in item["source_reference_keys"])
    return {
        "records": len(records),
        "pointers": sum(item["pointer"] for item in records),
        "records_with_source_references": sum(bool(item["source_reference_keys"]) for item in records),
        "distinct_source_references": len(citations),
        "source_references_shared_by_multiple_records": sum(count > 1 for count in citations.values()),
        "records_with_lineage_keys": sum(bool(item["lineage_keys"]) for item in records),
        "known_development_exposure_records": sum(item.get("known_development_exposure", False) for item in records),
        "variant_hints": sum(item.get("cross_reference_hint") == "catalog_variant" for item in records),
    }


def build(project_root):
    audit = project_root / AUDIT
    audit_data = audit.read_bytes()
    audit_lines = audit_data.decode("utf-8-sig").splitlines()
    catalog_dir = project_root / WORK / "fault_review_b78b2a2"
    records, sources, per_edition = [], [], {}
    for edition, (record_count, pointer_count, expected_blob) in MASTERS.items():
        file = catalog_dir / f"{edition}.md"
        data = file.read_bytes()
        if git_blob(data) != expected_blob:
            raise ValueError(f"Unexpected fixed source version: {file}")
        rows = extract(data, edition, file, audit, audit_lines)
        counts = summarize(rows)
        if (counts["records"], counts["pointers"]) != (record_count, pointer_count):
            raise ValueError(f"Unexpected catalog structure: {file}")
        records.extend(rows)
        per_edition[edition] = counts
        sources.append({
            "edition": edition, "path": file.as_posix(), "revision": REVISION,
            "git_blob": expected_blob, "sha256": sha256(data), "bytes": len(data),
        })
    if len(records) != len({item["record_id"] for item in records}):
        raise ValueError("Catalog entry IDs are not unique")
    original_parser = catalog_dir / "parse_reference.txt"
    sources.extend([
        {"path": original_parser.as_posix(), "role": "entry_structure_reference",
         "sha256": sha256(original_parser.read_bytes())},
        {"path": audit.as_posix(), "role": "previously_reviewed_locators",
         "sha256": sha256(audit_data)},
    ])
    return {
        "collection": "fault_review",
        "summary": {
            **summarize(records), "by_edition": per_edition,
            "scope": "catalog_metadata_only",
            "event_family_count": None,
            "independent_holdout_count": None,
            "lineage_basis": "standalone source locator or explicitly mapped prior review",
            "non_union_hints": ["source_reference_keys", "cross_reference_hint",
                                "pointer_target_collection_hint"],
        },
        "sources": sources,
        "records": records,
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--project-root", required=True, type=Path)
    cli.add_argument("--check", action="store_true")
    args = cli.parse_args()
    inventory = build(args.project_root.resolve())
    data = (json.dumps(inventory, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    destination = Path(__file__).with_name("fault_review_inventory.json")
    if args.check:
        if destination.read_bytes() != data:
            raise ValueError("Inventory differs from verified pinned sources")
    else:
        with destination.open("xb") as output:
            output.write(data)
    print(json.dumps(inventory["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
