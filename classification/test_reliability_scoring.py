"""Regression tests for action identity, causal structure and scoring denominators."""

from copy import deepcopy
import unittest

import evaluate


LEAF = {"status": "leaf", "pattern_id": "C2"}
PARENT = {"status": "parent", "parent_id": "item_multiplicity"}
UNKNOWN = {"status": "insufficient"}


def gold(key, role, action, label=LEAF, **extra):
    return {"id": key, "role": role, "specific_action": action, "allowed": [label], **extra}


def predicted(key, role, label=LEAF, **extra):
    result = {"id": key, "role": role, "action_resolution": "supported",
              "count_as_independent": role in evaluate.ROOT_ROLES and label != UNKNOWN,
              **label, **extra}
    for field in ("pattern", "parent"):
        if f"{field}_id" in label:
            result[f"{field}_ref"] = f"MECH-v0.3:{label[f'{field}_id']}"
    return result


def decision(prediction_id, expected_id, correct=True, cause=None):
    return {"prediction_id": prediction_id, "expected_id": expected_id,
            "facts_supported": True, "rationale": "Scoped action evidence",
            "action_correct": correct, "action_rationale": "Match source, operation and scope",
            "failure_causes": [cause] if cause else []}


class ReliabilityScoringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.standard = evaluate.catalog_standard(evaluate.read_json(evaluate.ROOT / "catalog.json"))

    def grade(self, actions, answer, decisions, *, unordered=False, omissions=None):
        answer = {"family_id": "example-family", "operator": "example-op",
                  "actions": answer}
        if unordered:
            answer.update(root_order_unspecified=True, root_order_rationale="Two disconnected failures")
        return evaluate.grade_case({"case_id": "example", "actions": actions}, answer,
                                   {"actions": decisions, "omissions": omissions or {}}, self.standard)

    def test_independent_roots_are_unordered_only_when_answer_allows_it(self):
        answer = [gold("left", "primary", "First kernel write"),
                  gold("right", "independent", "Second kernel write")]
        actions = [predicted("z", "primary"), predicted("a", "independent")]
        decisions = [decision("z", "right", cause="sample_or_answer"),
                     decision("a", "left", cause="sample_or_answer")]
        ordered = self.grade(actions, answer, decisions)
        unordered = self.grade(actions[::-1], answer, decisions, unordered=True)
        self.assertFalse(ordered["strict"])
        self.assertTrue(unordered["strict"])
        self.assertTrue(all(row["relationship_correct"] for row in unordered["actions"]))
        self.assertFalse(any(row["role_exact"] for row in unordered["actions"]))
        self.assertEqual(unordered["causal_signature"], self.grade(
            [predicted("second", "independent"), predicted("first", "primary")], answer,
            [decision("first", "left"), decision("second", "right")],
            unordered=True)["causal_signature"])

    def test_unordered_roots_do_not_accept_incorrect_upstream_edge(self):
        answer = [gold("left", "primary", "First kernel write"),
                  gold("right", "independent", "Second kernel write"),
                  gold("effect", "downstream", "Dependent reduction", upstream_id="left")]
        actions = [predicted("a", "independent"), predicted("b", "primary"),
                   predicted("c", "downstream", upstream_id="b")]
        review = [decision("a", "left", cause="sample_or_answer"),
                  decision("b", "right", cause="sample_or_answer"),
                  decision("c", "effect", cause="material_understanding")]
        graded = self.grade(actions, answer, review, unordered=True)
        self.assertEqual([row["relationship_correct"] for row in graded["actions"]], [True, True, False])
        self.assertFalse(graded["strict"])
        actions[2] = predicted("c", "independent")
        wrong_role = self.grade(actions, answer, review, unordered=True)
        self.assertFalse(wrong_role["actions"][2]["relationship_correct"])
        self.assertEqual(wrong_role["actions"][2]["independent_count_outcome"], "false_positive")

    def test_count_identity_retains_false_positive_and_missed_root_at_equal_totals(self):
        answer = [gold("known", "primary", "Missing write"),
                  gold("unknown", "unknown", None, UNKNOWN)]
        grade = self.grade(
            [predicted("asserted", "primary")], answer,
            [decision("asserted", "unknown", False, "material_understanding")],
            omissions={"known": {"failure_cause": "material_understanding", "rationale": "Missing write skipped"}},
        )
        metrics = evaluate.summarize([grade], self.standard)
        self.assertEqual(metrics["independent_reconciliation"],
                         {"claimed": 1, "expected": 1, "true_positive": 0,
                          "false_positive": 1, "false_negative": 1, "duplicates": 0})
        self.assertEqual(metrics["concrete_action_metrics"]["unknown_false_confirmation"], 1)
        self.assertEqual(grade["omissions"]["known"]["independent_count_outcome"], "false_negative")
        self.assertFalse(grade["strict"])

    def test_action_review_can_fail_full_case_with_correct_mechanism(self):
        answer = [gold("target", "primary", "Wrong local branch")]
        grade = self.grade([predicted("wrong", "primary")], answer,
                           [decision("wrong", "target", False, "material_understanding")])
        self.assertFalse(grade["strict"])
        self.assertTrue(grade["actions"][0]["mechanism_correct"])
        self.assertEqual(grade["actions"][0]["independent_count_outcome"], "false_positive")
        self.assertEqual(grade["missed_independent_action_ids"], ["target"])

    def test_accepted_alternative_stability_preserves_primary_denominator(self):
        answer = [{**gold("target", "primary", "Missing write"),
                   "primary": LEAF, "allowed": [PARENT, LEAF]}]
        left = self.grade([predicted("p", "primary")], answer, [decision("p", "target")])
        right = self.grade([predicted("q", "primary", PARENT)], answer, [decision("q", "target")])
        review = {"stability": [{"case_id": "example", "same_decisive_facts": True,
                                 "same_specific_action": True, "rationale": "Same code, coarser label"}]}
        stable = evaluate.compare_runs([{"cases": [left]}, {"cases": [right]}], review)
        self.assertFalse(stable["cases"][0]["same_labels"])
        self.assertTrue(stable["cases"][0]["same_allowed_labels"])
        self.assertTrue(stable["cases"][0]["same_causal_structure"])
        metrics = evaluate.summarize([right, deepcopy(right)], self.standard)
        leaf = metrics["coverage"]["MECH-v0.3:C2"]
        self.assertEqual((leaf["eligible_families"], leaf["supported_families"]), (1, 0))
        self.assertEqual(metrics["status_metrics"]["leaf"]["eligible"], 2)


if __name__ == "__main__":
    unittest.main()
