"""Verify this public projection and its file manifest, without private test inputs."""

from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))

from mech_v05 import engine, retrieval


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    manifest = json.loads((HERE / "PUBLIC_VALIDATION.json").read_bytes())
    files = manifest["files"]
    for name, record in files.items():
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT), "Manifest path escapes repository")
        require(path.is_file(), "Missing public file: " + name)
        require(sha256(path.read_bytes()).hexdigest() == record["sha256"], "Public bytes differ: " + name)
    expected = set(files) | {"classification/mech_v05/PUBLIC_VALIDATION.json"}
    present = {p.relative_to(ROOT).as_posix() for p in HERE.rglob("*")
               if p.is_file() and "__pycache__" not in p.parts}
    present.add("classification/test_mech_v05.py")
    require(present == expected, "Public projection contains missing or additional files")

    catalog = engine.load_catalog()
    require(len(catalog["modes"]) == 45, "Unexpected definition count")
    require(catalog["definition_counts"] == {"inherited_v04": 9, "reviewed_definition": 31,
                                           "research_definition": 5}, "Unexpected statuses")
    enabled = sum(c.get("classification_enabled", True) for c in catalog["modes"].values())
    require(enabled == 40, "Research definitions must remain disabled")
    for key, card in catalog["modes"].items():
        if key in catalog["inherited_mode_ids"]:
            continue  # engine.validate_catalog compares all nine inherited dictionaries exactly.
        require(card["representative_cases"] == [], "Real-case answer binding in public definition")
        for relative in card["source_cards"]:
            path = (HERE / relative).resolve()
            require(path.is_relative_to(HERE) and path.is_file(), "Missing public definition source")
    history = [json.loads(p.read_bytes()) for p in (HERE / "history/normalized_mode_cards").glob("*.json")]
    require(len(history) == 53, "Unexpected history index count")
    require(Counter(c["status"] for c in history) == {
        "NORMALIZED": 47, "PARTIALLY_RECOVERED": 2, "UNRESOLVED": 4}, "Unexpected historical statuses")
    external = json.loads((HERE / "external/knowledge_items.json").read_bytes())
    require(len(external["items"]) == 87, "Unexpected external knowledge count")
    require(len(retrieval.documents(catalog)) == 185, "Unexpected retrieval corpus count")
    with (HERE / "mode_id_migration.csv").open(encoding="utf-8", newline="") as stream:
        require(len(list(csv.DictReader(stream))) == 73, "Unexpected migration count")
    with (HERE / "overlap_exclusion_matrix.csv").open(encoding="utf-8", newline="") as stream:
        require(len(list(csv.DictReader(stream))) == 91, "Unexpected comparison count")
    print(json.dumps({"result": "PASS", "public_files": len(expected), "definitions": 45,
                      "classification_enabled": 40, "research_only": 5, "inherited_cards_unchanged": 9,
                      "history_index": 53, "external_items": 87, "retrieval_documents": 185,
                      "private_inputs_read": 0, "model_calls": 0, "device_executions": 0}))


if __name__ == "__main__":
    main()
