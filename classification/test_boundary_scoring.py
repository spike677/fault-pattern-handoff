"""Regression cases for explicit gold primaries and combined parent verdicts."""

from copy import deepcopy
import unittest

import evaluate


LEAF = {"status": "leaf", "pattern_id": "P1"}
PARENT = {"status": "parent", "parent_id": "parameter"}
COMBO = {"status": "parent", "parent_id": "contribution", "supported_pattern_ids": ["C1", "C2"]}
LEAF_REF = "leaf:MECH-v0.2:P1"
PARENT_REF = "parent:MECH-v0.2:parameter"
COMBO_REF = "parent:MECH-v0.2:contribution[MECH-v0.2:C1,MECH-v0.2:C2]"


class BoundaryScoringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog = evaluate.read_json(evaluate.ROOT / "catalog.json")
        cls.standard = {
            "catalog_version": catalog["version"],
            "parents": {mode: card["parent"] for mode, card in catalog["modes"].items()},
        }

    def grade(self, actual, allowed, *, primary=None, facts_supported=True, error=None):
        expected = {"id": "gold", "role": "primary", "allowed": allowed}
        if primary is not None:
            expected["primary"] = primary
        answer = {"family_id": "example-family", "operator": "example-op", "actions": [expected]}
        pred = {"id": "prediction", "role": "primary", **actual}
        if actual["status"] == "leaf":
            pred["pattern_ref"] = f"MECH-v0.2:{actual['pattern_id']}"
        if "supported_pattern_ids" in actual:
            pred["combination"] = "compatible"
            pred["supported_pattern_refs"] = [f"MECH-v0.2:{mode}" for mode in actual["supported_pattern_ids"]]
        result = {"case_id": "example", "actions": [pred]}
        review = {
            "actions": [{"prediction_id": "prediction", "expected_id": "gold",
                         "facts_supported": facts_supported, "rationale": "Synthetic boundary",
                         "failure_causes": [error] if error else []}],
        }
        graded = evaluate.grade_case(result, answer, review, self.standard)
        return graded, evaluate.summarize([graded], self.standard)

    def test_reordering_allowed_does_not_change_alternative_metrics(self):
        forward = self.grade(PARENT, [LEAF, PARENT], primary=LEAF)
        backward = self.grade(PARENT, [PARENT, LEAF], primary=LEAF)
        self.assertEqual(forward, backward)
        _, metrics = forward
        self.assertEqual(metrics["expected_verdict_counts"], {LEAF_REF: 1})
        self.assertEqual(metrics["families_strict"], 1)
        self.assertEqual(metrics["confusion"], [])
        self.assertEqual(metrics["strict_primary_verdicts"], {})
        self.assertEqual(metrics["accepted_alternatives"],
                         [{"primary_expected": LEAF_REF, "actual": PARENT_REF, "count": 1, "strict": 1}])
        mode_coverage = metrics["coverage"]["MECH-v0.2:P1"]
        self.assertEqual((mode_coverage["eligible_families"], mode_coverage["supported_families"]), (1, 0))

    def test_alternative_leaf_does_not_pad_leaf_coverage(self):
        _, metrics = self.grade(LEAF, [LEAF, PARENT], primary=PARENT)
        actual = metrics["coverage"]["MECH-v0.2:P1"]
        self.assertEqual((actual["eligible_families"], actual["supported_families"]), (0, 0))
        self.assertEqual(metrics["expected_verdict_counts"], {PARENT_REF: 1})

    def test_unsupported_facts_are_reported_separately_from_label_error(self):
        _, metrics = self.grade(PARENT, [LEAF, PARENT], primary=LEAF, facts_supported=False,
                                error="material_understanding")
        self.assertEqual(metrics["families_strict"], 0)
        self.assertEqual(metrics["confusion"], [])
        self.assertEqual(metrics["accepted_alternatives"][0]["strict"], 0)
        self.assertEqual(metrics["action_counts"]["label_match_with_failed_evidence"], 1)

    def test_error_uses_primary_even_when_alternative_is_listed_first(self):
        wrong = {"status": "leaf", "pattern_id": "P2"}
        _, metrics = self.grade(wrong, [PARENT, LEAF], primary=LEAF, error="rule_execution")
        self.assertEqual(metrics["confusion"],
                         [{"expected": LEAF_REF, "actual": "leaf:MECH-v0.2:P2", "count": 1}])
        self.assertEqual(metrics["accepted_alternatives"], [])

    def test_gold_primary_required_for_distinct_alternatives(self):
        with self.assertRaisesRegex(ValueError, "explicit primary"):
            evaluate.answer_verdicts({"allowed": [LEAF, PARENT]}, self.standard)
        wrong = {"status": "leaf", "pattern_id": "P2"}
        with self.assertRaisesRegex(ValueError, "in the allowed set"):
            evaluate.answer_verdicts({"allowed": [LEAF, PARENT], "primary": wrong}, self.standard)
        _, metrics = self.grade(LEAF, [LEAF])
        self.assertEqual(metrics["strict_primary_verdicts"], {LEAF_REF: 1})

    def test_combo_is_one_scored_parent_even_when_members_are_reordered(self):
        reversed_combo = {**COMBO, "supported_pattern_ids": ["C2", "C1"]}
        _, metrics = self.grade(COMBO, [reversed_combo])
        self.assertEqual(metrics["families_strict"], 1)
        self.assertEqual(metrics["expected_verdict_counts"], {COMBO_REF: 1})
        self.assertEqual(metrics["action_counts"]["predicted_actions"], 1)
        self.assertEqual(metrics["strict_primary_verdicts"], {COMBO_REF: 1})
        self.assertEqual(metrics["coverage"]["MECH-v0.2:C1"]["eligible_families"], 0)
        self.assertEqual(metrics["coverage"]["MECH-v0.2:C2"]["eligible_families"], 0)
        with self.assertRaisesRegex(ValueError, "must be distinct"):
            evaluate.answer_verdicts({"allowed": [COMBO, reversed_combo]}, self.standard)

    def test_plain_parent_does_not_match_combo_without_an_explicit_alternative(self):
        ordinary = {"status": "parent", "parent_id": "contribution"}
        _, metrics = self.grade(ordinary, [COMBO], error="rule_execution")
        self.assertEqual(metrics["families_strict"], 0)
        self.assertEqual(metrics["action_counts"]["misclassified_actions"], 1)
        _, metrics = self.grade(ordinary, [ordinary, COMBO], primary=COMBO)
        self.assertEqual(metrics["families_strict"], 1)
        self.assertEqual(metrics["accepted_alternatives"][0]["primary_expected"], COMBO_REF)

    def test_gold_combo_rejects_unsupported_components_or_shape(self):
        wrong = deepcopy(COMBO)
        wrong["supported_pattern_ids"][1] = "C3"
        with self.assertRaisesRegex(ValueError, "compatible C1"):
            evaluate.answer_verdicts({"allowed": [wrong]}, self.standard)
        wrong = {**LEAF, "supported_pattern_ids": ["C1", "C2"]}
        with self.assertRaisesRegex(ValueError, "contribution parent"):
            evaluate.answer_verdicts({"allowed": [wrong]}, self.standard)


if __name__ == "__main__":
    unittest.main()
