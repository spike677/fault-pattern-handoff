"""Validate advisory reviews for mode changes without editing their catalog."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

if __package__:
    from .classify import (SOURCE_KINDS, UNPINNED, by_id, check_anchor, digest,
                           nonempty, scoped_source, strings, validate_scope)
else:
    from classify import (SOURCE_KINDS, UNPINNED, by_id, check_anchor, digest,
                          nonempty, scoped_source, strings, validate_scope)


PROTOCOL = "mode_semantic_review/0.1"
STATE = "SUGGESTION_ONLY"
RETAIN = "retain_candidate"
STRONG = {"reuse", "propose_addition", "exclude_scoped"}
RECOMMENDATIONS = STRONG | {"revise_definition", RETAIN, "retain_relation"}
LEVELS = {"implementation_error", "mechanism_relation", "condition_or_symptom", "mixed_or_unclear"}
ROLES = {"primary", "independent", "downstream", "unknown"}
QUESTIONS = ("object_and_contract", "actual_action", "case_role", "near_neighbor", "disposition")
COMPARISONS = {"equivalent", "limited_reuse", "partial_overlap", "distinct", "uncertain", "none"}
REFERENCE_RELATIONSHIPS = {"equivalent_reuse", "limited_reuse", "partial_overlap", "method_borrowing", "no_match"}
EXTERNAL_KINDS = {"reference", "catalog"}
SCOPE_KEYS = ("case_id", "action_id", "version", "path")


def in_set(value, allowed):
    return isinstance(value, str) and value in allowed


def review_rows(document, label, subjects, errors, key="subject_id"):
    """Index proposals individually so a malformed sibling does not erase a valid proposal."""
    if not isinstance(document, dict) or not isinstance(document.get("reviews"), list):
        errors.append(f"{label}:invalid_document")
        return {}, set()
    indexed, duplicates = {}, set()
    for row in document["reviews"]:
        identity = row.get(key) if isinstance(row, dict) else None
        if not nonempty(identity):
            errors.append(f"{label}:invalid_record")
        elif identity not in subjects:
            errors.append(f"{label}:unknown_subject:{identity}")
        elif identity in indexed:
            duplicates.add(identity)
            errors.append(f"{label}:duplicate_subject:{identity}")
        else:
            indexed[identity] = row
    return indexed, duplicates


def prior_records(document, subjects, errors):
    if document is None:
        return {}
    if not isinstance(document, dict) or document.get("protocol") != PROTOCOL:
        errors.append("previous:invalid_protocol")
        return {}
    rows, duplicates = review_rows({"reviews": document.get("records")}, "previous", subjects, errors)
    return {key: row for key, row in rows.items() if key not in duplicates}


def check_claim(statement, sources, scope, issues, label, *, allow_external=False, allow_contract=False):
    if (not isinstance(statement, dict) or not nonempty(statement.get("text"))
            or not isinstance(statement.get("anchors"), list)):
        issues.append(f"{label}:invalid_claim")
        return False

    bound = False
    for anchor in statement["anchors"]:
        source_id = anchor.get("source_id") if isinstance(anchor, dict) else None
        source = sources.get(source_id) if nonempty(source_id) else None
        source_scope = scope
        external = source is not None and source["kind"] in EXTERNAL_KINDS
        if external:
            if not allow_external:
                issues.append(f"{label}:reference_cannot_bind_case_fact")
                continue
            source_scope = {"version": source["version"], "path": source["path"], "claim": "reported"}
        error = check_anchor(anchor, sources, source_scope)
        if error is not None:
            issues.append(f"{label}:{error}")
        elif not external and (scoped_source(source, scope) or
                (allow_contract and scope["claim"] != "runtime" and source["kind"] == "contract"
                 and source["path"] == scope.get("path"))):
            bound = True
    return bound


def check_claim_list(items, sources, scope, issues, label, *, allow_contract=False):
    if not isinstance(items, list):
        issues.append(f"{label}:invalid_claim_list")
        return False
    results = [check_claim(item, sources, scope, issues, label, allow_contract=allow_contract) for item in items]
    return any(results)


def scope_and_sources(subject, issues):
    if not nonempty(subject.get("definition")):
        issues.append("missing_subject_definition")
    scope = subject.get("scope")
    if not isinstance(scope, dict):
        scope = {}
        issues.append("invalid_case_scope")
    scope = {"claim": "reported", **scope}
    if any(not nonempty(scope.get(key)) for key in SCOPE_KEYS):
        issues.append("missing_case_scope")
    try:
        if validate_scope(scope):
            issues.append("insufficient_case_scope")
    except ValueError:
        issues.append("invalid_case_scope")
        # Continue checking source text without allowing an invalid claim to bind.
        scope = {**scope, "claim": "reported"}

    try:
        candidate_sources = by_id(subject.get("sources"), "sources")
    except ValueError:
        candidate_sources = {}
        issues.append("invalid_sources")
    sources = {}
    for key, source in candidate_sources.items():
        if (all(nonempty(source.get(field)) for field in ("path", "version", "text"))
                and in_set(source.get("kind"), SOURCE_KINDS | EXTERNAL_KINDS)):
            sources[key] = source
        else:
            issues.append(f"invalid_source:{key}")
    return scope, sources


def check_semantic_fit(attestation, review_sha, cache_key, issues):
    if attestation is None:
        return "unverified"
    if (attestation.get("review_sha256") != review_sha
            or attestation.get("cache_key") != cache_key):
        issues.append("semantic_review_scope_mismatch")
        return "unverified"
    decision = attestation.get("decision")
    if (not in_set(decision, {"supported", "unsupported", "uncertain"})
            or not all(nonempty(attestation.get(key)) for key in ("reviewer", "reason"))):
        issues.append("invalid_semantic_review")
        return "unverified"
    if decision != "supported":
        issues.append(f"semantic_review_{decision}")
    return decision


def check_model(row, subject, scope, sources, modes, issues):
    recommendation = row.get("recommendation")
    level = row.get("definition_level")
    role = row.get("case_role")
    if row.get("state") != STATE:
        issues.append("invalid_review_state")
    if not in_set(recommendation, RECOMMENDATIONS):
        issues.append("invalid_recommendation")
    if not in_set(level, LEVELS) or not in_set(role, ROLES):
        issues.append("invalid_level_or_case_role")
    if (not in_set(row.get("reference_relationship"), REFERENCE_RELATIONSHIPS)
            or not all(nonempty(row.get(key)) for key in ("reference_basis", "validation_basis"))):
        issues.append("missing_reference_or_validation_basis")
    if not strings(row.get("missing")):
        issues.append("invalid_missing_list")

    comparison = row.get("comparison")
    if not isinstance(comparison, dict):
        comparison = {}
    neighbor, relationship = comparison.get("pattern_id"), comparison.get("relationship")
    if (not in_set(relationship, COMPARISONS)
            or (neighbor is not None and not in_set(neighbor, modes))):
        issues.append("invalid_catalog_comparison")
    if (relationship in ("equivalent", "limited_reuse", "partial_overlap", "distinct")
            and neighbor is None):
        issues.append("missing_neighbor_id")

    answers = row.get("questions")
    if not isinstance(answers, dict):
        answers = {}
    bound = {key: check_claim(answers.get(key), sources, scope, issues, key,
                              allow_external=(key in {"near_neighbor", "disposition"}))
             for key in QUESTIONS}
    support = check_claim_list(row.get("support"), sources, scope, issues, "support",
                               allow_contract=recommendation == "exclude_scoped")
    check_claim_list(row.get("counterevidence"), sources, scope, issues, "counterevidence")

    if in_set(recommendation, STRONG) and not support:
        issues.append("affirmative_scoped_support_required")
    if recommendation == "reuse":
        if level not in ("implementation_error", "mechanism_relation") or not bound["actual_action"]:
            issues.append("reuse_requires_anchored_mechanism")
        target = row.get("target_pattern_id")
        if (not in_set(target, modes) or target != neighbor
                or relationship not in ("equivalent", "limited_reuse")):
            issues.append("reuse_requires_covered_catalog_target")
    if recommendation == "propose_addition":
        if (level not in ("implementation_error", "mechanism_relation") or not bound["actual_action"]
                or role not in ("primary", "independent") or not bound["case_role"]):
            issues.append("addition_requires_anchored_concrete_action")
        if relationship not in ("none", "distinct") or (relationship == "none" and neighbor is not None):
            issues.append("addition_requires_catalog_difference")
    if recommendation == "exclude_scoped":
        if (row.get("exclusion_scope") != subject.get("scope") or not nonempty(row.get("exclusion_target"))
                or not nonempty(scope.get("version")) or scope["version"].strip().lower() in UNPINNED):
            issues.append("exclusion_requires_explicit_pinned_scope_and_target")
    return bound


def review_catalog(inputs, model_output, catalog, evidence_review=None, previous=None, *, catalog_sha256=None):
    """Report a review disposition per input while keeping every candidate."""
    if (not isinstance(inputs, dict) or not isinstance(catalog, dict)
            or not nonempty(catalog.get("version")) or not isinstance(catalog.get("modes"), dict)):
        raise ValueError("Expected a subject bundle and a versioned catalog")
    subjects = by_id(inputs.get("subjects"), "subjects")
    catalog_sha256 = catalog_sha256 or digest(catalog)
    errors = []
    if inputs.get("catalog_version") != catalog["version"]:
        errors.append("catalog_version_mismatch")
    model, repeated_model = review_rows(model_output, "model", subjects, errors)
    evidence, repeated_evidence = ({}, set()) if evidence_review is None else review_rows(
        evidence_review, "evidence", subjects, errors)
    old_records = prior_records(previous, subjects, errors)
    references = {}
    try:
        for key, reference in by_id(inputs.get("references", []), "references").items():
            origin = reference.get("path", reference.get("origin"))
            if not all(nonempty(value) for value in (reference.get("version"), reference.get("text"), origin)):
                raise ValueError("Reference excerpt requires version, location and text")
            references[key] = {**reference, "path": origin, "kind": "reference"}
    except ValueError:
        errors.append("invalid_reference_bundle")
        references = {}
    entries, actions = [], defaultdict(list)
    for identity, subject in subjects.items():
        issues = []
        if "catalog_version_mismatch" in errors:
            issues.append("catalog_version_mismatch")
        scope, sources = scope_and_sources(subject, issues)
        if "invalid_reference_bundle" in errors:
            issues.append("invalid_reference_bundle")
        if sources.keys() & references.keys():
            issues.append("conflicting_reference_id")
        sources = {**references, **sources}
        cache_key = digest({"protocol": PROTOCOL, "subject": subject, "catalog_sha256": catalog_sha256,
                            "catalog_version": catalog["version"], "input_catalog_version": inputs.get("catalog_version"),
                            "references": inputs.get("references", [])})
        row, assessment = model.get(identity), evidence.get(identity)
        reused = False
        old = old_records.get(identity)
        if (row is None and old is not None and old.get("cache_key") == cache_key
                and "model:invalid_document" not in errors
                and isinstance(old.get("validation_issues"), list)
                and not {"duplicate_model_review", "duplicate_semantic_review"}.intersection(old["validation_issues"])
                and isinstance(old.get("model_review"), dict)
                and old["model_review"].get("subject_id") == identity
                and old.get("review_sha256") == digest(old["model_review"])):
            row = old["model_review"]
            if assessment is None and isinstance(old.get("evidence_review"), dict):
                assessment = old["evidence_review"]
            reused = True

        if identity in repeated_model:
            issues.append("duplicate_model_review")
        if identity in repeated_evidence:
            issues.append("duplicate_semantic_review")
        if assessment is not None and assessment.get("subject_id") != identity:
            issues.append("semantic_review_subject_mismatch")
        proposed = row.get("recommendation") if row is not None else None
        review_sha = digest(row) if row is not None else None
        semantic = check_semantic_fit(assessment, review_sha, cache_key, issues)
        if row is None:
            issues.append("missing_model_review")
            role, level = "unknown", None
            bound = {}
        else:
            level = row.get("definition_level")
            role = row.get("case_role")
            bound = check_model(row, subject, scope, sources, catalog["modes"], issues)
        if in_set(proposed, STRONG) and semantic != "supported" and semantic != "unsupported":
            issues.append("semantic_review_required_for_strong_suggestion")
        entry = {
            "subject_id": identity, "state": STATE, "retained": True,
            "scope": subject.get("scope"),
            "definition_level": level if in_set(level, LEVELS) else None,
            "case_role": role if in_set(role, ROLES) else "unknown",
            "recommendation": RETAIN if issues or proposed is None else proposed,
            "proposed_recommendation": proposed, "semantic_status": semantic,
            "validation_issues": sorted(set(issues)), "cache_key": cache_key,
            "review_sha256": review_sha, "reused": reused,
            "model_review": row, "evidence_review": assessment,
            "counted_independent": False,
        }
        entries.append(entry)
        if (not issues and semantic == "supported" and level in ("implementation_error", "mechanism_relation")
                and proposed != "exclude_scoped" and bound.get("case_role") and bound.get("actual_action")):
            action_identity = tuple(scope[key] for key in SCOPE_KEYS)
            actions[action_identity].append(entry)

    for same_action in actions.values():
        roles = {entry["case_role"] for entry in same_action}
        roots = [entry for entry in same_action if entry["case_role"] in ("primary", "independent")]
        if roots and "downstream" not in roles:
            roots[0]["counted_independent"] = True
        elif roots:
            errors.append("conflicting_roles_for_same_scoped_action")

    return {
        "protocol": PROTOCOL, "catalog_version": catalog["version"], "catalog_sha256": catalog_sha256,
        "records": entries, "errors": errors,
        "independent_action_count": sum(entry["counted_independent"] for entry in entries),
    }


def load_json(content):
    def reject_constant(value):
        raise ValueError(f"Invalid JSON constant: {value}")

    return json.loads(content, parse_constant=reject_constant)


def optional_json(path, label, problems):
    if path is None:
        return None
    try:
        return load_json(path.read_bytes())
    except (OSError, ValueError) as exc:
        problems.append(f"{label}:unreadable:{exc}")
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("model_output", type=Path)
    parser.add_argument("--catalog", type=Path, default=Path(__file__).with_name("catalog.json"))
    parser.add_argument("--evidence-review", type=Path)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    errors = []
    try:
        raw_catalog = args.catalog.read_bytes()
        catalog = load_json(raw_catalog)
        inputs = load_json(args.inputs.read_bytes())
        model = optional_json(args.model_output, "model", errors)
        evidence_review = optional_json(args.evidence_review, "evidence", errors)
        previous = optional_json(args.previous, "previous", errors)
        result = review_catalog(inputs, model, catalog, evidence_review, previous,
                                catalog_sha256=hashlib.sha256(raw_catalog).hexdigest())
    except (OSError, ValueError) as exc:
        parser.exit(2, f"mode_review: {exc}\n")
    result["errors"].extend(errors)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()
