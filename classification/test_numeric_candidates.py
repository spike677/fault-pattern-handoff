"""Guard the first wrong state that separates the two numeric candidates."""

from copy import deepcopy
from pathlib import Path
import unittest

from proposals.numeric_validation.classify_candidates import classify_candidates, load


HERE = Path(__file__).resolve().parent
REGRESSION = HERE / "proposals" / "numeric_validation" / "regression"


class NumericCandidateRegression(unittest.TestCase):
    def setUp(self):
        self.material = load(REGRESSION / "A.json")
        self.facts = load(REGRESSION / "facts.json")
        self.catalog = load(HERE / "catalog.json")

    def action(self, case_id):
        results = classify_candidates(self.material, self.facts, self.catalog)
        case, = (entry for entry in results["cases"] if entry["case_id"] == case_id)
        decision, = case["actions"]
        return decision

    def test_loop_state_formula_and_pre_reduction_square_are_separate(self):
        self.assertEqual(self.action("E06")["pattern_id"], "NUM-01")
        self.assertEqual(self.action("G05")["pattern_id"], "NUM-02")
        square = self.action("V406")
        self.assertEqual((square["status"], square["reason"]), ("outside", "pre_reduction_square_overflow"))
        self.assertTrue(square["count_as_independent"])

    def test_missing_or_unbound_precision_anchor_cannot_establish_candidate(self):
        e06 = self.facts[0]["actions"][0]
        e06["facts"] = [row for row in e06["facts"] if row["key"] != "wider_state_preserves_same_updates"]
        self.assertEqual(self.action("E06")["status"], "insufficient")

        g05 = self.facts[1]["actions"][0]
        fact, = (row for row in g05["facts"] if row["key"] == "centered_variance_survives_at_same_precision")
        fact["anchors"][0]["quote"] = "a different revision of the contract"
        decision = self.action("G05")
        self.assertEqual(decision["status"], "insufficient")
        self.assertEqual(decision["issues"][0]["code"], "quote_not_in_source_span")

    def test_two_competing_first_wrong_states_do_not_get_a_candidate(self):
        e06 = self.facts[0]["actions"][0]
        extra = deepcopy(next(row for row in e06["facts"] if row["key"] == "loop_carried_narrow_state"))
        extra["key"] = "pre_reduction_square_overflow"
        e06["facts"].append(extra)
        decision = self.action("E06")
        self.assertEqual((decision["status"], decision["reason"]), ("insufficient", "conflicting_first_wrong_state"))


if __name__ == "__main__":
    unittest.main()
