"""Evidence and role regressions for reader fact protocol 0.3.1."""

import json
from pathlib import Path
import unittest

from classify import classify


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

    def test_patch_effect_and_suspicion_are_preserved_without_defect(self):
        hypothesis = self.fact("established_other_defect", "hypothesis", [self.anchor("report", "context")])
        changed = self.fact("added_barrier", "observation", [self.anchor("patch", "context", 2)])
        output = self.result(self.fact("applicable_contract"), hypothesis, changed)
        self.assertEqual((output["status"], output["role"]), ("insufficient", "unknown"))
        self.assertEqual(output["proposed_role"], "primary")
        self.assertIn(hypothesis, output["facts"])
        self.assertIn(changed, output["facts"])

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

    def test_protocol_does_not_change_unmarked_historical_replay(self):
        del self.packet["fact_protocol"]
        original = self.fact("established_other_defect", "hypothesis")
        output = self.result(original)
        self.assertEqual((output["status"], output["role"]), ("outside", "primary"))
        self.assertNotIn("claim_state", output["facts"][0])


if __name__ == "__main__":
    unittest.main()
