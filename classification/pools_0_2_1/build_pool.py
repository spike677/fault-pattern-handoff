"""Link documentation indexes without opening case bodies or assigning blind eligibility."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys


NAMESPACES = {"event", "patch", "backport", "mirror", "defect", "answer", "family"}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def index_records(inventories):
    data = {}
    collection_names = {}
    record_collections = {}
    pointers = []
    for inventory in inventories:
        collection = inventory["collection"]
        if collection in collection_names:
            raise ValueError(f"Repeated collection: {collection}")
        collection_names[collection] = len(inventory["records"])
        for row in inventory["records"]:
            key = row["record_id"]
            if key in data:
                raise ValueError(f"Repeated record ID: {key}")
            keys = row["lineage_keys"]
            if not isinstance(keys, list) or not all(
                    isinstance(k, str) and k.partition(":")[0] in NAMESPACES
                    and k.partition(":")[2] and not any(char.isspace() for char in k)
                    for k in keys):
                raise ValueError(f"Invalid typed lineage keys: {key}")
            data[key] = row
            record_collections[key] = collection
            if row.get("pointer") is True:
                pointers.append(key)
    return data, collection_names, sorted(pointers), record_collections


def group_records(records, pointers):
    parent, key_owner, key_members = {}, {}, defaultdict(list)

    def find(current):
        while current != parent[current]:
            parent[current] = parent[parent[current]]
            current = parent[current]
        return current

    for key in sorted(set(records) - set(pointers)):
        parent[key] = key
        for anchor in sorted(set(records[key]["lineage_keys"])):
            first = key_owner.setdefault(anchor, key)
            parent[find(key)] = find(first)
            key_members[anchor].append(key)
    groups = defaultdict(list)
    for key in parent:
        groups[find(key)].append(key)
    return sorted(groups.values(), key=lambda group: group[0]), key_members


def build(inventories, development_lineage):
    if not isinstance(development_lineage, list) or not all(isinstance(k, str) for k in development_lineage):
        raise ValueError("The development lineage must be a list of strings")
    exposed = set(development_lineage)
    records, sizes, pointers, record_collections = index_records(inventories)
    groups, key_members = group_records(records, pointers)
    partitions, result = Counter(), []
    cross_collection_groups = 0
    groups_with_related_exposure = 0
    for members in groups:
        keys = {k for record_id in members for k in records[record_id]["lineage_keys"]}
        direct_exposure = sorted(r for r in members if records[r].get("known_development_exposure") is True)
        matching_keys = sorted(keys & exposed)
        cited = {k for r in members for k in records[r].get("source_reference_keys", [])}
        related_exposure = sorted((cited & exposed) - keys)
        collections = sorted({record_collections[r] for r in members})
        cross_collection_groups += len(collections) > 1
        groups_with_related_exposure += bool(related_exposure)
        usage = "development" if matching_keys or direct_exposure else "curation_pending"
        partitions[(usage, "groups")] += 1
        partitions[(usage, "records")] += len(members)
        item = {
            "group_id": "metadata-" + digest("\n".join(members).encode("utf-8"))[:20],
            "usage": usage,
            "record_ids": members,
            "identity_basis": "shared_exact_keys" if len(members) > 1 else
                "single_record_with_keys" if keys else "unresolved_identity",
        }
        if matching_keys:
            item["matched_development_keys"] = matching_keys
        if len(collections) > 1:
            item["collections"] = collections
        if related_exposure:
            item["related_exposure_review_keys"] = related_exposure
        if direct_exposure:
            item["already_reviewed_records"] = direct_exposure
        result.append(item)
    return {
        "scope": "metadata_linkage_and_exposure_check",
        "catalog_record_counts": sizes,
        "pointers": pointers,
        "linkage_totals": {
            "groups": len(groups),
            "groups_with_multiple_records": sum(len(g) > 1 for g in groups),
            "cross_collection_groups": cross_collection_groups,
            "groups_with_related_exposure_review_keys": groups_with_related_exposure,
            "repeated_exact_keys": sum(len(member_ids) > 1 for member_ids in key_members.values()),
            "records_without_lineage_keys": sum(
                not records[key]["lineage_keys"] for key in set(records) - set(pointers)),
        },
        "usage_counts": {name: {unit: partitions[(name, unit)] for unit in ("groups", "records")}
                         for name in ("development", "curation_pending")},
        "independently_assigned_holdout": {"current_seven": 0, "future_versions": 0},
        "groups": result,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exposures", type=Path, required=True)
    parser.add_argument("inventories", type=Path, nargs="+")
    args = parser.parse_args()
    try:
        raw = [file.read_bytes() for file in [args.exposures, *args.inventories]]
        sources = [json.loads(data) for data in raw]
        result = build(sources[1:], sources[0])
        result["input_sha256"] = {
            str(file): digest(data) for file, data in zip([args.exposures, *args.inventories], raw)
        }
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Pool metadata error: {exc}", file=sys.stderr)
        return 2
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    sys.stdout.buffer.write(serialized.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
