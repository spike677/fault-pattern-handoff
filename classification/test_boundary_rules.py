"""Regressions for layered disputes and one-action membership combinations."""

import json
from pathlib import Path
import unittest

from classify import classify


CATALOG = json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8-sig"))


class BoundaryRules(unittest.TestCase):
    def decide(self, pairs):
        lines = [f"{key} = {value!r}" for key, value in pairs]
        source = {"id": "control", "version": "v-pinned", "path": "op.py", "kind": "code",
                  "text": "\n".join(lines)}
        case = {"case_id": "synthetic-control", "sources": [source]}
        facts = [
            {"key": key, "value": value, "explanation": "Synthetic membership map: x3 is new, x2 was dropped.",
             "anchors": [{"source_id": "control", "start_line": i, "end_line": i, "quote": lines[i - 1]}]}
            for i, (key, value) in enumerate(pairs, 1)
        ]
        packet = {"case_id": case["case_id"], "actions": [{
            "id": "a", "role": "primary", "scope": {
                "version": "v-pinned", "path": "op.py", "claim": "static"},
            "facts": facts,
        }]}
        result = classify(case, packet, CATALOG)
        self.assertEqual(result["decision_version"], "0.2.1")
        output, = result["actions"]
        return output

    def confirmed(self, *modes):
        return sorted({(key, True) for mode in modes for key in CATALOG["modes"][mode]["necessary"]})

    def test_membership_replacement_has_one_root_and_two_compatible_attributes(self):
        output = self.decide(self.confirmed("C1", "C2") + [("distinct_members_for_replacement", True)])
        self.assertEqual((output["status"], output["parent_id"]), ("parent", "contribution"))
        self.assertEqual(output["combination"], "compatible")
        self.assertEqual(output["supported_pattern_ids"], ["C1", "C2"])
        self.assertEqual(output["supported_pattern_refs"], ["MECH-v0.2:C1", "MECH-v0.2:C2"])
        self.assertEqual(output["parent_ref"], "MECH-v0.2:contribution")
        self.assertTrue(output["count_as_independent"])
        self.assertFalse(output["conflicts"])

    def test_membership_overlap_without_distinction_keeps_ordinary_parent(self):
        output = self.decide(self.confirmed("C1", "C2"))
        self.assertEqual((output["status"], output["parent_id"]), ("parent", "contribution"))
        self.assertNotIn("combination", output)
        self.assertNotIn("supported_pattern_ids", output)
        self.assertIn("distinct_members_for_replacement", output["missing"])

    def test_leaf_dispute_preserves_independently_proven_address_parent(self):
        output = self.decide(self.confirmed("L2") + [
            ("wrong_conversion", False), ("address_violation", True),
        ])
        self.assertEqual((output["status"], output["parent_id"]), ("parent", "address"))
        self.assertEqual(output["conflict_details"]["leaf"], ["wrong_conversion"])
        self.assertFalse(output["conflict_details"]["core"])

    def test_unresolved_rival_blocks_final_leaf_in_same_family(self):
        output = self.decide(self.confirmed("L1", "L2") + [("wrong_conversion", False)])
        self.assertEqual((output["status"], output["parent_id"]), ("parent", "address"))
        self.assertNotIn("pattern_id", output)
        self.assertIn("wrong_conversion", output["conflict_details"]["leaf"])

    def test_conflicting_common_applicability_or_current_violation_blocks(self):
        for key in ("applicable_contract", "address_violation"):
            with self.subTest(key=key):
                output = self.decide(self.confirmed("L1") + [(key, True), (key, False)])
                self.assertEqual(output["status"], "insufficient")
                self.assertIn(key, output["conflict_details"]["core"])

    def test_unrelated_dispute_does_not_discard_a_settled_parameter_leaf(self):
        output = self.decide(self.confirmed("P1") + [
            ("wrong_conversion", True), ("wrong_conversion", False),
        ])
        self.assertEqual((output["status"], output["pattern_id"], output["pattern_ref"]),
                         ("leaf", "P1", "MECH-v0.2:P1"))
        self.assertEqual(output["conflict_details"]["unrelated"], ["wrong_conversion"])
        self.assertFalse(output["conflict_details"]["leaf"])

    def test_arbitrary_overlaps_never_gain_combination_status(self):
        output = self.decide(self.confirmed("L1", "L2"))
        self.assertEqual((output["status"], output["parent_id"]), ("parent", "address"))
        self.assertNotIn("combination", output)
        self.assertIn("multiple_leaf_modes_for_one_action", output["conflict_details"]["leaf"])
        cross = self.decide(self.confirmed("P1", "L1"))
        self.assertEqual(cross["status"], "insufficient")
        self.assertIn("multiple_violation_groups_for_one_action", cross["conflict_details"]["core"])


if __name__ == "__main__":
    unittest.main()
