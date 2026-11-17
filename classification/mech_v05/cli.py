"""Local materials -> retrieval -> source-bound readback -> classification -> archive."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

from . import engine, reader, retrieval


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate-catalog")
    query = commands.add_parser("search")
    query.add_argument("query")
    query.add_argument("--limit", type=int, default=8)
    query.add_argument("--kind", choices=["unified_mode", "historical_source", "external_knowledge"])
    prep = commands.add_parser("prepare")
    prep.add_argument("material", type=Path)
    prep.add_argument("output", type=Path)
    classify = commands.add_parser("classify")
    classify.add_argument("material", type=Path)
    classify.add_argument("readback", type=Path)
    classify.add_argument("output", type=Path)
    validation = commands.add_parser("validate-readback")
    validation.add_argument("material", type=Path)
    validation.add_argument("readback", type=Path)
    archive = commands.add_parser("archive")
    archive.add_argument("material", type=Path)
    archive.add_argument("readback", type=Path)
    archive.add_argument("result", type=Path)
    archive.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    catalog = engine.load_catalog()
    if args.command == "validate-catalog":
        print(json.dumps({"version": catalog["version"], "counts": catalog["definition_counts"]}))
    elif args.command == "search":
        print(json.dumps(retrieval.search(args.query, catalog, args.limit, args.kind), ensure_ascii=False, indent=2))
    elif args.command == "prepare":
        material = read(args.material)
        # Validate shape with the inherited reader schema generator, never infer facts here.
        if not material.get("cases"):
            raise ValueError("At least one material case is required")
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "request.md").write_bytes(reader.render(material, catalog).encode())
        save(args.output / "response-schema.json", reader.schema(catalog))
        save(args.output / "input-record.json", {"material_sha256": sha256(args.material.read_bytes()).hexdigest(),
                                                "catalog_sha256": engine.pilot.digest(catalog), "readback_required": True,
                                                "warning": "No model is invoked by prepare; provide a separately recorded source-grounded readback."})
        print(json.dumps({"prepared_cases": len(material["cases"]), "model_invoked": False}))
    elif args.command == "validate-readback":
        issues = reader.validate_readback(read(args.material), read(args.readback))
        print(json.dumps({"valid": not issues, "issues": issues}, ensure_ascii=False, indent=2))
        return 1 if issues else 0
    elif args.command == "classify":
        result = engine.classify_package(read(args.material), read(args.readback), catalog)
        save(args.output, result)
        print(json.dumps({"cases": len(result["cases"]), "output": str(args.output), "evaluation_class": result["evaluation_class"]}))
    else:
        material, extracted, supplied = read(args.material), read(args.readback), read(args.result)
        expected = engine.classify_package(material, extracted, catalog)
        if supplied != expected:
            raise ValueError("Classification result does not reproduce from these inputs")
        key = engine.pilot.digest({"material": material, "readback": extracted, "result": expected})
        directory = args.destination / key
        if directory.exists():
            existing = read(directory / "archive.json")
            if existing["identity"] != key:
                raise ValueError("Archive collision")
            for name, expected_hash in existing["files"].items():
                if name not in {"material.json", "readback.json", "result.json"} or sha256((directory / name).read_bytes()).hexdigest() != expected_hash:
                    raise ValueError("Existing archive integrity mismatch")
            print(json.dumps({"archive": str(directory), "already_present": True}))
            return
        directory.mkdir(parents=True)
        for name, value in (("material.json", material), ("readback.json", extracted), ("result.json", expected)):
            save(directory / name, value)
        save(directory / "archive.json", {"identity": key, "scope": "development_exposure",
                                          "case_ids": [c["case_id"] for c in material["cases"]],
                                          "files": {name: sha256((directory / name).read_bytes()).hexdigest()
                                                    for name in ("material.json", "readback.json", "result.json")},
                                          "publication": "local; no automatic upload", "updates_catalog": False})
        print(json.dumps({"archive": str(directory), "newly_exposed_cases": len(material["cases"])}))


if __name__ == "__main__":
    raise SystemExit(main())
