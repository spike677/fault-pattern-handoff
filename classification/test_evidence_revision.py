"""Evidence and role regressions for reader fact protocol 0.3.1."""

import json
from pathlib import Path
import unittest

from classify import classify, classify_package


CATALOG = json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8-sig"))
PROTOCOL = "classification_facts/0.3.1"


class EvidenceRevision(unittest.TestCase):
    def setUp(self):
        self.case = {"case_id": "control", "sources": [
            {"id": "contract", "version": "v1", "path": "spec", "kind": "contract",
             "text": "Only logical values contribute. Copy data must be ready before it is consumed."},
            {"id": "old", "version": "v1", "path": "kernel", "kind": "code",
             "text": "The fixed old path uses the affected buffer and operation."},
            {"id": "patch", "version": "v1", "path": "kernel", "kind": "diff",
             "text": " Old path enters compute.\n+ Insert barrier.\n Compute reads buffer."},
            {"id": "report", "version": "v1", "path": "issue", "kind": "report",
             "text": "Maybe queue reuse matters. The author confirmed that a missing wait let the "
                     "consumer read unready input on the named path."},
        ]}
        self.action = {"id": "action", "role": "primary",
                       "scope": {"version": "v1", "path": "kernel", "claim": "static"}, "facts": []}
        self.packet = {"case_id": self.case["case_id"], "fact_protocol": PROTOCOL, "actions": [self.action]}

    def anchor(self, source_id, use, line=1):
        source = next(row for row in self.case["sources"] if row["id"] == source_id)
        return {"source_id": source_id, "start_line": line, "end_line": line,
                "quote": source["text"].splitlines()[line - 1], "use": use}

    def fact(self, key, state="derived", anchors=None):
        return {"key": key, "value": True, "claim_state": state,
                "explanation": f"Evidence for {key}.",
                "anchors": anchors if anchors is not None else [
                    self.anchor("contract", "requirement"), self.anchor("old", "behavior")
                ]}

    def result(self, *facts):
        self.action["facts"] = list(facts)
        result = classify(self.case, self.packet, CATALOG)
        return result["actions"][0]

    def test_padding_special_case_without_actual_contribution_is_insufficient(self):
        missing_branch = self.fact("implementation_action", "observation")
        output = self.result(self.fact("applicable_contract"), self.fact("ineligible_member"),
                             self.fact("participation_violation"), missing_branch,
                             self.fact("causal_role", "hypothesis"))
        self.assertEqual((output["status"], output["role"]), ("insufficient", "unknown"))
        self.assertEqual(output["proposed_role"], "primary")
        self.assertFalse(output["count_as_independent"])
        self.assertIn("actual_contribution", output["missing"])
        self.assertIn(missing_branch, output["facts"])

    def test_proven_non_neutral_invalid_item_keeps_c1(self):
        evidence = [self.fact(key) for key in CATALOG["modes"]["C1"]["necessary"]]
        output = self.result(*evidence, self.fact("implementation_action"), self.fact("causal_role"))
        self.assertEqual((output["pattern_id"], output["role"]), ("C1", "primary"))
        self.assertTrue(output["count_as_independent"])
        without_cause = self.result(*evidence, self.fact("implementation_action"))
        self.assertEqual((without_cause["pattern_id"], without_cause["role"]), ("C1", "unknown"))
        self.assertEqual(without_cause["action_resolution"], "supported")
        self.assertFalse(without_cause["count_as_independent"])

    def test_scoped_neutralization_rules_out_participation_parent(self):
        facts = [self.fact(key) for key in (
            "applicable_contract", "actual_contribution", "participation_violation",
            "implementation_action", "causal_role",
        )]
        self.assertEqual(self.result(*facts)["parent_id"], "item_participation")

        possible = self.fact("contribution_neutralized", "hypothesis")
        self.assertEqual(self.result(*facts, possible)["parent_id"], "item_participation")

        confirmed = self.fact("contribution_neutralized")
        output = self.result(*facts, confirmed)
        self.assertEqual((output["status"], output["role"]), ("insufficient", "unknown"))
        self.assertFalse(output["count_as_independent"])
        self.assertIn(confirmed, output["facts"])

    def test_patch_effect_and_suspicion_are_preserved_without_defect(self):
        hypothesis = self.fact("established_other_defect", "hypothesis", [self.anchor("report", "context")])
        changed = self.fact("added_barrier", "observation", [self.anchor("patch", "context", 2)])
        output = self.result(self.fact("applicable_contract"), hypothesis, changed)
        self.assertEqual((output["status"], output["role"]), ("insufficient", "unknown"))
        self.assertEqual(output["proposed_role"], "primary")
        self.assertIn(hypothesis, output["facts"])
        self.assertIn(changed, output["facts"])

    def test_parameter_parent_preserves_unresolved_implementation_action(self):
        evidence = [self.fact("applicable_contract"), self.fact("parameter_violation"),
                    self.fact("causal_role")]
        output = self.result(*evidence)
        self.assertEqual((output["status"], output["parent_id"]), ("parent", "parameter"))
        self.assertEqual((output["action_resolution"], output["role"]), ("unresolved", "unknown"))
        self.assertFalse(output["count_as_independent"])
        self.assertIn("implementation_action", output["missing"])

        resolved = self.result(*evidence, self.fact("implementation_action"))
        self.assertEqual((resolved["action_resolution"], resolved["role"]), ("supported", "primary"))
        self.assertTrue(resolved["count_as_independent"])

    def test_parameter_parent_with_known_action_does_not_request_it_again(self):
        output = self.result(*(self.fact(key) for key in (
            "applicable_contract", "parameter_violation", "correct_source",
            "state_treatment_allowed", "implementation_action", "causal_role",
        )))
        self.assertEqual((output["status"], output["parent_id"]), ("parent", "parameter"))
        self.assertEqual(output["action_resolution"], "supported")
        self.assertNotIn("observed_implementation_action", output["missing"])

    def test_new_diff_line_and_unfounded_derivation_do_not_prove_old_behavior(self):
        for anchors in ([self.anchor("patch", "behavior", 1)],
                        [self.anchor("contract", "requirement"), self.anchor("patch", "behavior", 2)]):
            with self.subTest(anchors=anchors):
                output = self.result(self.fact("established_other_defect", anchors=anchors))
                self.assertEqual(output["status"], "insufficient")
                self.assertIn("missing_derivation_basis", [issue["code"] for issue in output["issues"]])

    def test_static_contract_and_old_action_can_prove_outside_defect(self):
        output = self.result(self.fact("established_other_defect"), self.fact("causal_role"))
        self.assertEqual((output["status"], output["outside_reason"]), ("outside", "outside_catalog"))
        self.assertTrue(output["count_as_independent"])

    def test_diff_hunk_header_is_not_a_contract_or_old_behavior(self):
        self.case["sources"][2]["text"] = "@@ -1,2 +1,3 @@\n Old path enters compute."
        for use, other in (("behavior", self.anchor("contract", "requirement")),
                           ("requirement", self.anchor("old", "behavior"))):
            with self.subTest(use=use):
                header = self.anchor("patch", use)
                header["end_line"] = 2
                output = self.result(self.fact("established_other_defect", anchors=[header, other]))
                self.assertEqual(output["status"], "insufficient")
                self.assertIn("missing_derivation_basis", [issue["code"] for issue in output["issues"]])

    def test_quoted_old_behavior_survives_a_span_with_new_context(self):
        contract = self.anchor("contract", "requirement")
        old_quote = self.anchor("patch", "behavior", 3)
        old_quote["start_line"] = 2
        output = self.result(self.fact("established_other_defect", anchors=[contract, old_quote]))
        self.assertEqual((output["status"], output.get("outside_reason")), ("outside", "outside_catalog"))

    def test_mixed_diff_span_does_not_admit_quote_from_new_side(self):
        contract = self.anchor("contract", "requirement")
        new_quote = self.anchor("patch", "behavior", 2)
        new_quote.update(start_line=1, end_line=3)
        output = self.result(self.fact("established_other_defect", anchors=[contract, new_quote]))
        self.assertEqual((output["status"], output["role"]), ("insufficient", "unknown"))
        self.assertFalse(output["count_as_independent"])
        self.assertIn("missing_derivation_basis", [issue["code"] for issue in output["issues"]])

    def test_explicit_report_has_reported_scope_without_keyword_heuristic(self):
        self.action["scope"] = {"version": "v1", "path": "issue", "claim": "reported"}
        anchors = [self.anchor("report", "confirmation")]
        evidence = [self.fact(key, "confirmed_report", anchors)
                    for key in ("established_other_defect", "causal_role")]
        output = self.result(*evidence)
        self.assertEqual(output["outside_reason"], "outside_catalog")
        self.assertTrue(output["count_as_independent"])

        self.action["scope"] = {"version": "v1", "path": "kernel", "claim": "static"}
        self.assertEqual(self.result(*evidence)["status"], "insufficient")

    def test_insufficient_root_claim_is_only_a_proposal(self):
        output = self.result(self.fact("implementation_action", "observation"))
        self.assertEqual((output["status"], output["role"]), ("insufficient", "unknown"))
        self.assertEqual(output["proposed_role"], "primary")
        self.assertFalse(output["count_as_independent"])

    def test_unknown_protocol_and_evidence_enum_are_invalid_input(self):
        for bad in ("?", {}, None):
            with self.subTest(protocol=bad):
                with self.assertRaisesRegex(ValueError, "fact_protocol"):
                    classify(self.case, {**self.packet, "fact_protocol": bad}, CATALOG)
        with self.assertRaisesRegex(ValueError, "claim_state"):
            self.result(self.fact("established_other_defect", "sure"))
        with self.assertRaisesRegex(ValueError, "anchor use"):
            self.result(self.fact("established_other_defect", anchors=[self.anchor("old", [])]))

    def test_untyped_fact_cannot_silently_supply_current_correction(self):
        untyped = self.fact("established_other_defect")
        del untyped["claim_state"]
        with self.assertRaisesRegex(ValueError, "claim_state"):
            self.result(untyped)

    def test_batch_reports_each_invalid_case(self):
        second_case = {**self.case, "case_id": "second"}
        packets = [
            {**self.packet, "actions": [{**self.action, "role": "invented"}]},
            {**self.packet, "case_id": "second", "actions": [{**self.action, "upstream_id": "action"}]},
        ]
        with self.assertRaises(ValueError) as context:
            classify_package({"cases": [self.case, second_case]}, packets, CATALOG)
        self.assertIn("control: Each action needs one of", str(context.exception))
        self.assertIn("second: Only downstream actions", str(context.exception))

    def test_batch_inventory_reports_missing_and_extra_cases(self):
        packet = {**self.packet, "case_id": "unexpected"}
        with self.assertRaisesRegex(ValueError, "missing facts: control; unexpected facts: unexpected"):
            classify_package({"cases": [self.case]}, [packet], CATALOG)

    def test_protocol_does_not_change_unmarked_historical_replay(self):
        del self.packet["fact_protocol"]
        original = self.fact("established_other_defect", "hypothesis")
        output = self.result(original)
        self.assertEqual((output["status"], output["role"]), ("outside", "primary"))
        self.assertNotIn("claim_state", output["facts"][0])


if __name__ == "__main__":
    unittest.main()
