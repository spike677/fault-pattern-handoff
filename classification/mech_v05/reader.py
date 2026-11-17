"""Prepare source-bound development readbacks using the unchanged action graph shape."""

from copy import deepcopy
import json

from reliability_v04 import reader as inherited
from . import engine, retrieval


def schema(catalog=None):
    catalog = engine.load_catalog() if catalog is None else catalog
    value = deepcopy(inherited.schema())
    keys = set(value["$defs"]["fact"]["properties"]["key"]["enum"])
    keys.update(catalog["fact_definitions"])
    value["$defs"]["fact"]["properties"]["key"]["enum"] = sorted(keys)
    return value


def render(material, catalog=None):
    catalog = engine.load_catalog() if catalog is None else catalog
    text = inherited.render(material)
    instructions = """
## MECH-v0.5 development knowledge extension
Keep the existing action graph and evidence protocol. First identify the observed
operation, applicable contract and actual consumer in the target version. Consult
historical/external definitions to compare mechanisms; retrieval ranking is never a
fact, an answer, or proof. State necessary facts only when target evidence supports
them. A report's explicit root-cause account may support confirmed_report within
reported scope. Hypotheses and fix success remain hypotheses/observations unless the
relation is independently established. Derived claims require requirement and old
behavior anchors; do not relabel patch additions as old code.
Record one implementation action once; normal downstream arithmetic is supporting
operation or propagation, not another root. Multiple actual faults need separate
actions and evidence of independence. Separate mechanism, action, causal role and
whole-case results. When a definition is disabled, it is a research neighbor; use a
proved parent/outside/insufficient result as appropriate. Do not invent a leaf to
fill catalogue coverage. Use the supplied neutral assessment scope.
All start_line/end_line values are ONE-BASED EXCERPT line numbers printed before the
vertical bar in this request. original_start_line is metadata for mapping back to a
file, never the line index accepted in a readback anchor. Validate these coordinates
before submitting; do not change a fact or its claim state to repair a line number.
"""
    extra = [instructions, "## Additional fact meanings", json.dumps(catalog["fact_definitions"], ensure_ascii=False)]
    for case in material["cases"]:
        extra.append("## Assessment scope " + case["case_id"] + "\n" + case.get("review_scope", "All claims remain bound to their original version/path."))
        query = " ".join(source["text"][:1800] for source in case["sources"][:2])
        hits = retrieval.search(query, catalog, limit=6, kind="unified_mode")
        extra.append("Candidate definitions, not answers:\n" + json.dumps([catalog["modes"][h["id"]] | {"id": h["id"]} for h in hits], ensure_ascii=False))
    extra.append("Full catalogue is available locally; search again using the actual operation if these candidates do not fit.")
    return text + "\n\n" + "\n\n".join(extra)


def validate_readback(material, extracted):
    """Detect binding/coordinate defects without changing the submitted evidence."""
    cases = {c["case_id"]: c for c in material["cases"]}
    errors = []
    for case in extracted["cases"]:
        if case["case_id"] not in cases:
            errors.append({"case_id": case["case_id"], "issue": "unknown_case"})
            continue
        sources = {s["id"]: s for s in cases[case["case_id"]]["sources"]}
        refs = [(node["id"], node.get("source_location")) for node in case["nodes"]]
        refs += [(node["id"], anchor) for node in case["nodes"] for fact in node["facts"] for anchor in fact["anchors"]]
        refs += [(edge["from"] + "->" + edge["to"], anchor) for edge in case["relations"] for anchor in edge["evidence_refs"]]
        for owner, anchor in refs:
            if anchor is None:
                continue
            source = sources.get(anchor.get("source_id"))
            start, end = anchor.get("start_line"), anchor.get("end_line")
            issue = None
            if source is None:
                issue = "unknown_source"
            elif type(start) is not int or type(end) is not int or start < 1 or end < start:
                issue = "invalid_excerpt_coordinates"
            elif end > len(source["text"].splitlines()):
                offset = source.get("original_start_line", 1) - 1
                issue = ("original_file_coordinates_instead_of_excerpt" if
                         1 <= start - offset <= end - offset <= len(source["text"].splitlines())
                         else "invalid_excerpt_coordinates")
            if issue:
                errors.append({"case_id": case["case_id"], "action_id": owner, "source_id": anchor.get("source_id"),
                               "start_line": start, "end_line": end, "issue": issue})
    if set(cases) != {c["case_id"] for c in extracted["cases"]}:
        errors.append({"issue": "case_inventory_mismatch"})
    return errors
