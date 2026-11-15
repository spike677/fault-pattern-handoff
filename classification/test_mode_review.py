"""Bidirectional regressions for the suggest-only mechanism review gate."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from classify import digest
from mode_review import review_catalog
import test_boundary_rules as frozen_boundaries


CATALOG = json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8-sig"))


class ModeReviewTest(unittest.TestCase):
    def subject(self, identifier="proposal", text="Code reads the wrong parameter slot.", *, action_id="a"):
        return {
            "id": identifier,
            "definition": text,
            "scope": {"case_id": "fixture", "action_id": action_id,
                      "version": "v-pinned", "path": "op.py"},
            "sources": [{"id": "code", "version": "v-pinned", "path": "op.py",
                         "kind": "code", "text": text}],
        }

    def model(self, subject, recommendation="retain_candidate", *, level="implementation_error",
              role="primary", neighbor="P1", relationship="distinct"):
        evidence = {
            "text": subject["definition"],
            "anchors": [{"source_id": "code", "start_line": 1, "end_line": 1,
                         "quote": subject["sources"][0]["text"]}],
        }
        return {
            "subject_id": subject["id"],
            "state": "SUGGESTION_ONLY",
            "definition_level": level,
            "case_role": role,
            "recommendation": recommendation,
            "questions": {key: deepcopy(evidence) for key in
                          ("object_and_contract", "actual_action", "case_role", "near_neighbor", "disposition")},
            "support": [deepcopy(evidence)],
            "counterevidence": [],
            "missing": [],
            "comparison": {"pattern_id": neighbor, "relationship": relationship},
            "reference_relationship": "no_match",
            "reference_basis": "Synthetic control has no external reference.",
            "validation_basis": "Synthetic regression exercises a decision boundary.",
        }

    def review(self, subjects, rows, *, decision="supported", previous=None, catalog_sha256=None,
               references=None):
        inputs = {"catalog_version": CATALOG["version"], "subjects": subjects}
        if references is not None:
            inputs["references"] = references
        reviews = {"reviews": rows}
        provisional = review_catalog(inputs, reviews, CATALOG, catalog_sha256=catalog_sha256)
        cache_keys = {record["subject_id"]: record["cache_key"] for record in provisional["records"]}
        attestations = None if decision is None else {
            "reviews": [
                {"subject_id": row["subject_id"], "review_sha256": digest(row),
                 "cache_key": cache_keys[row["subject_id"]], "decision": decision,
                 "reviewer": "fixture-reviewer", "reason": "Synthetic semantic support control."}
                for row in rows
            ]
        }
        report = review_catalog(inputs, reviews, CATALOG, attestations, previous,
                                catalog_sha256=catalog_sha256)
        self.assertEqual([row["subject_id"] for row in report["records"]], [s["id"] for s in subjects])
        for row in report["records"]:
            self.assertTrue(row["retained"])
            self.assertEqual(row["state"], "SUGGESTION_ONLY")
        return report

    def single(self, subject, row, **options):
        result, = self.review([subject], [row], **options)["records"]
        return result

    def reuse(self, subject, pattern, **options):
        return {
            **self.model(subject, "reuse", neighbor=pattern, relationship="equivalent", **options),
            "target_pattern_id": pattern,
        }

    def test_symptom_only_proposal_remains_available(self):
        case = self.subject(text="The unaligned last block produces NaN.")
        row = self.model(case, "propose_addition", level="condition_or_symptom", role="unknown")
        row["missing"] = ["Which implementation action caused the deviation?"]
        result = self.single(case, row)
        self.assertEqual(result["recommendation"], "retain_candidate")
        self.assertEqual(result["proposed_recommendation"], "propose_addition")

    def test_symptom_cannot_be_reused_as_a_specific_mode(self):
        case = self.subject(text="An unaligned final tile gave a different output.")
        row = self.reuse(case, "L2", level="condition_or_symptom", role="unknown")
        result = self.single(case, row)
        self.assertEqual(result["recommendation"], "retain_candidate")
        self.assertEqual(result["proposed_recommendation"], "reuse")

    def test_concrete_early_return_can_support_omission(self):
        case = self.subject(text="Before counting required boundary members the routine returns zero.")
        result = self.single(case, self.reuse(case, "C2", level="mechanism_relation"))
        self.assertEqual(result["recommendation"], "reuse")
        self.assertTrue(result["counted_independent"])

    def test_new_operator_can_reuse_a_known_units_error(self):
        case = self.subject(text="A new gather kernel sends a byte offset directly to an element index.")
        result = self.single(case, self.reuse(case, "L2"))
        self.assertEqual(result["recommendation"], "reuse")
        self.assertEqual(result["model_review"]["target_pattern_id"], "L2")

    def test_one_static_confirmed_action_outside_catalog_supports_a_proposal(self):
        case = self.subject(text="Truncating a signed stride before validation changes its direction.")
        row = self.model(case, "propose_addition", neighbor="L2")
        row["confidence"] = 0.12
        old_catalog = deepcopy(CATALOG)
        result = self.single(case, row)
        self.assertEqual(result["recommendation"], "propose_addition")
        self.assertEqual(CATALOG, old_catalog)

    def test_downstream_relation_does_not_swallow_independent_local_error(self):
        root = self.subject("parameter", "The wrong attribute is read to generate the mask.", action_id="main")
        effect = self.subject("effect", "The incorrect mask allows an invalid contribution.", action_id="effect")
        local = self.subject("local", "Even with a correct mask, the kernel never applies it.", action_id="local")
        report = self.review(
            [root, effect, local],
            [self.reuse(root, "P1"),
             self.model(effect, "retain_relation", level="mechanism_relation", role="downstream"),
             self.reuse(local, "C1", level="mechanism_relation", role="independent")],
        )
        a, b, c = report["records"]
        self.assertTrue(a["counted_independent"])
        self.assertEqual(b["recommendation"], "retain_relation")
        self.assertFalse(b["counted_independent"])
        self.assertTrue(c["counted_independent"])
        self.assertEqual(report["independent_action_count"], 2)

    def test_c1_and_c2_same_replacement_remain_one_independent_action(self):
        first = self.subject("inclusion", "The replacement adds a forbidden element.")
        second = self.subject("omission", "The same replacement drops a required element.")
        report = self.review(
            [first, second], [self.reuse(first, "C1", level="mechanism_relation"),
                              self.reuse(second, "C2", level="mechanism_relation")],
        )
        self.assertEqual([r["recommendation"] for r in report["records"]], ["reuse", "reuse"])
        self.assertEqual(report["independent_action_count"], 1)

    def test_verbatim_but_semantically_unsupported_quote_cannot_exclude(self):
        case = self.subject(text="The release archive contains this source file.")
        row = self.model(case, "exclude_scoped")
        row.update(exclusion_target="C3 match", exclusion_scope=deepcopy(case["scope"]))
        result = self.single(case, row, decision="unsupported")
        self.assertEqual(result["recommendation"], "retain_candidate")
        self.assertEqual(result["semantic_status"], "unsupported")
        self.assertEqual(result["proposed_recommendation"], "exclude_scoped")

    def test_legal_repeated_indices_exclude_only_the_scoped_match(self):
        case = self.subject(text="This version of scatter-add counts duplicate indices by contract.")
        row = self.model(case, "exclude_scoped", neighbor="C3", role="unknown")
        row.update(exclusion_target="C3 match in the pinned scatter-add path",
                   exclusion_scope=deepcopy(case["scope"]))
        result = self.single(case, row)
        self.assertEqual(result["recommendation"], "exclude_scoped")
        self.assertFalse(result["counted_independent"])
        row["exclusion_scope"]["path"] = "other.py"
        self.assertEqual(self.single(case, row)["recommendation"], "retain_candidate")

    def test_exclusion_needs_positive_evidence_and_semantic_review(self):
        case = self.subject(text="The caller contract allows two independent partial sums.")
        row = self.model(case, "exclude_scoped", neighbor="C3")
        row.update(exclusion_target="C3 match", exclusion_scope=deepcopy(case["scope"]))
        self.assertEqual(self.single(case, row, decision=None)["recommendation"], "retain_candidate")
        row["support"] = []
        self.assertEqual(self.single(case, row)["recommendation"], "retain_candidate")

    def test_single_case_and_custom_term_with_no_runtime_are_not_exclusions(self):
        case = self.subject(text="One static example suggests a crate-specific quantization defect.")
        row = self.model(case, "retain_candidate", role="unknown")
        row["confidence"] = 0.03
        row["missing"] = ["Source and execution proof for the proposed error."]
        result = self.single(case, row, decision=None)
        self.assertEqual(result["recommendation"], "retain_candidate")

    def test_frozen_leaf_conflict_still_preserves_parent(self):
        existing = frozen_boundaries.BoundaryRules()
        output = existing.decide(existing.confirmed("L2") + [
            ("wrong_conversion", False), ("address_violation", True),
        ])
        self.assertEqual((output["status"], output["parent_id"]), ("parent", "address"))
        case = self.subject(text="An address relationship failed; the exact conversion error is unresolved.")
        row = self.model(case, "retain_relation", level="mechanism_relation", role="unknown",
                         neighbor="L2", relationship="uncertain")
        self.assertEqual(self.single(case, row)["recommendation"], "retain_relation")

    def test_malformed_or_missing_model_output_keeps_every_subject(self):
        cases = [self.subject("a"), self.subject("b")]
        for bad in (None, ["wrong envelope"], {"reviews": ["wrong row"]}, {"reviews": []}):
            with self.subTest(model_output=bad):
                inputs = {"catalog_version": CATALOG["version"], "subjects": cases}
                result = review_catalog(inputs, bad, CATALOG)
                self.assertEqual([r["subject_id"] for r in result["records"]], ["a", "b"])
                self.assertTrue(all(r["retained"] and r["recommendation"] == "retain_candidate"
                                    for r in result["records"]))

    def test_unknown_pattern_is_not_reused(self):
        case = self.subject()
        row = self.reuse(case, "unknown-mode")
        result = self.single(case, row)
        self.assertEqual(result["recommendation"], "retain_candidate")
        self.assertTrue(result["validation_issues"])

    def test_duplicate_model_reviews_do_not_choose_a_strong_suggestion(self):
        case = self.subject()
        add = self.model(case, "propose_addition")
        exclude = self.model(case, "exclude_scoped")
        exclude.update(exclusion_target="current match", exclusion_scope=deepcopy(case["scope"]))
        standalone = self.single(case, add)
        self.assertEqual(standalone["recommendation"], "propose_addition")
        attestations = {"reviews": [{
            "subject_id": case["id"], "review_sha256": digest(add),
            "cache_key": standalone["cache_key"], "decision": "supported",
            "reviewer": "fixture-reviewer", "reason": "Only the first review was checked.",
        }]}
        inputs = {"catalog_version": CATALOG["version"], "subjects": [case]}
        result, = review_catalog(inputs, {"reviews": [add, exclude]}, CATALOG, attestations)["records"]
        self.assertTrue(result["retained"])
        self.assertEqual(result["recommendation"], "retain_candidate")
        self.assertTrue(result["validation_issues"])

    def test_review_of_different_output_does_not_authorize_strong_suggestion(self):
        case = self.subject(text="The byte offset is sent straight to an element index.")
        row = self.reuse(case, "L2")
        inputs = {"catalog_version": CATALOG["version"], "subjects": [case]}
        reviews = {"reviews": [row]}
        pending, = review_catalog(inputs, reviews, CATALOG)["records"]
        for wrong_digest, wrong_key in ((True, False), (False, True)):
            with self.subTest(wrong_digest=wrong_digest, wrong_key=wrong_key):
                attestations = {"reviews": [{
                    "subject_id": case["id"],
                    "review_sha256": "0" * 64 if wrong_digest else digest(row),
                    "cache_key": "0" * 64 if wrong_key else pending["cache_key"],
                    "decision": "supported", "reviewer": "reviewer",
                    "reason": "Attestation for a different record or source context.",
                }]}
                output, = review_catalog(inputs, reviews, CATALOG, attestations)["records"]
                self.assertEqual(output["recommendation"], "retain_candidate")

    def test_version_mismatched_anchor_cannot_authorize_reuse(self):
        case = self.subject()
        case["sources"][0]["version"] = "other-release"
        result = self.single(case, self.reuse(case, "P1"))
        self.assertEqual(result["recommendation"], "retain_candidate")
        self.assertTrue(result["validation_issues"])

    def test_reference_supports_near_neighbor_only_and_changes_cache_scope(self):
        case = self.subject(text="The byte offset is sent to an element index.")
        ref = {"id": "other-system", "version": "r-pinned", "path": "guide.md",
               "text": "Check that the offset uses the same units as the pointer stride."}
        reference_claim = {"text": "External guide informs the comparison.",
                           "anchors": [{"source_id": ref["id"], "start_line": 1, "end_line": 1,
                                        "quote": ref["text"]}]}
        row = self.reuse(case, "L2")
        row["questions"]["near_neighbor"] = reference_claim
        first = self.review([case], [row], references=[ref])
        self.assertEqual(first["records"][0]["recommendation"], "reuse")

        altered_ref = {**ref, "text": ref["text"] + "\nAn additional condition applies."}
        stale, = self.review([case], [], references=[altered_ref], previous=first)["records"]
        self.assertFalse(stale["reused"])
        self.assertNotEqual(stale["cache_key"], first["records"][0]["cache_key"])

        row["questions"]["actual_action"] = reference_claim
        unsupported = self.single(case, row, references=[ref])
        self.assertEqual(unsupported["recommendation"], "retain_candidate")
        self.assertIn("actual_action:reference_cannot_bind_case_fact", unsupported["validation_issues"])

    def test_cache_reuses_exact_context_and_invalidates_on_source_or_catalog_change(self):
        case = self.subject()
        hash_a, hash_b = "a" * 64, "b" * 64
        first = self.review([case], [self.reuse(case, "P1")], catalog_sha256=hash_a)
        unchanged = self.review([case], [], previous=first, catalog_sha256=hash_a)["records"][0]
        self.assertTrue(unchanged["reused"])
        self.assertEqual(unchanged["cache_key"], first["records"][0]["cache_key"])

        changed = deepcopy(case)
        changed["sources"][0]["text"] += "\nThe source changed."
        for subject, catalog_hash in ((changed, hash_a), (case, hash_b)):
            with self.subTest(changed_source=subject != case, catalog_hash=catalog_hash):
                row = self.review([subject], [], previous=first, catalog_sha256=catalog_hash)["records"][0]
                self.assertFalse(row["reused"])
                self.assertNotEqual(row["cache_key"], unchanged["cache_key"])
                self.assertEqual(row["recommendation"], "retain_candidate")


if __name__ == "__main__":
    unittest.main()
