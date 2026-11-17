"""Render a source-only MECH-v0.4 action-graph request."""

import json
from pathlib import Path

from mech_v04 import reader as formal, classifier

from . import graph


PROMPT = Path(__file__).with_name("PROMPT.md")


def object_schema(fields):
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def array_schema(items):
    return {"type": "array", "items": items}


TEXT = {"type": "string"}
SPAN = object_schema({"source_id": TEXT, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}})


def schema():
    standard = formal.schema()
    definitions = standard["$defs"]
    existing = definitions.pop("action")["properties"]
    definitions.pop("supporting_operation")
    definitions["node"] = object_schema({
        "id": TEXT, "node_type": {"enum": sorted(graph.KINDS)}, "description": TEXT,
        "scope": existing["scope"],
        "source_location": {"anyOf": [SPAN, {"type": "null"}]},
        "expected_behavior": TEXT, "observed_behavior": TEXT, "violated_relation": TEXT,
        "facts": existing["facts"],
    })
    definitions["relation"] = object_schema({
        "kind": {"enum": sorted(graph.RELATIONS)}, "from": TEXT, "to": TEXT,
        "evidence_level": {"enum": sorted(graph.pilot.CLAIM_STATES)},
        "evidence_refs": array_schema({"$ref": "#/$defs/anchor"}), "explanation": TEXT,
    })
    standard["properties"]["cases"]["items"] = object_schema({
        "case_id": TEXT, "operator": TEXT, "roles": array_schema(TEXT), "readback": TEXT,
        "nodes": array_schema({"$ref": "#/$defs/node"}),
        "relations": array_schema({"$ref": "#/$defs/relation"}),
    })
    return standard


def render(material):
    parts = [PROMPT.read_text(encoding="utf-8"), classifier.CATALOG.read_text(encoding="utf-8")]
    for case in material["cases"]:
        parts.append(f"## {case['case_id']}")
        for source in case["sources"]:
            metadata = {key: value for key, value in source.items() if key != "text"}
            lines = [f"{number:03d}|{line}" for number, line in enumerate(source["text"].splitlines(), 1)]
            parts.append(json.dumps(metadata, ensure_ascii=False) + "\n" + "\n".join(lines))
    return "\n\n".join(parts) + "\n"
