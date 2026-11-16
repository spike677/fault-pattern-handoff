"""Render source-only A views and bind fresh reader logs to evidence packets."""

import json

if __package__:
    from .classifier import CATALOG, HERE, pilot
else:
    from classifier import CATALOG, HERE, pilot

from proposals.numeric_validation_v042.reader import response_schema, validate_support
from validation_0_3_1.reader_v04.readback import answer_from_log, packets_from_response


READER_PROMPT = HERE / "PROMPT.md"
SCHEMA = HERE / "response-schema.json"
COMMON_READER = HERE.parent / "proposals" / "numeric_validation_v042"
PROMPT_PARTS = (COMMON_READER / "PROMPT.md", COMMON_READER / "SCOPE_BINDING.md", READER_PROMPT)


def schema():
    value = response_schema()
    props = value["properties"]["cases"]["items"]["properties"]
    props["actions"]["minItems"] = 1
    return value


def render_a(material):
    sections = [path.read_text(encoding="utf-8") for path in (*PROMPT_PARTS, CATALOG)]
    for case in material["cases"]:
        sections.append(f"## {case['case_id']}")
        for source in case["sources"]:
            metadata = {key: value for key, value in source.items() if key != "text"}
            lines = [f"{number:03d}|{line}" for number, line in enumerate(source["text"].splitlines(), 1)]
            sections.append(json.dumps(metadata, ensure_ascii=False) + "\n" + "\n".join(lines))
    return "\n\n".join(sections) + "\n"


def decode_log(log, material):
    context, message, _ = answer_from_log(log)
    response = json.loads(message)
    support = {case["case_id"]: case.pop("supporting_operations") for case in response["cases"]}
    facts, notes = packets_from_response(material, response)
    cases = pilot.by_id(material["cases"], "material cases", "case_id")
    issues = []
    for packet in facts:
        case_id = packet["case_id"]
        sources = pilot.by_id(cases[case_id]["sources"], "sources")
        actions = pilot.by_id(packet["actions"], "actions")
        for operation in support[case_id]:
            issues.extend({"case_id": case_id, "action_id": operation["action_id"], "code": code}
                          for code in validate_support(operation, actions, sources))
    return context, facts, support, issues, notes
