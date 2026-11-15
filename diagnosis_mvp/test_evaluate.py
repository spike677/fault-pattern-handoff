import unittest

from evaluate import check_lineage, grade, run_trial, summarize


def row(case_id, track, family, *keys):
    return {
        "case": {"case_id": case_id, "family_id": family},
        "track": track, "lineage": [f"family:{family}", *keys],
    }


class EvaluationRegressions(unittest.TestCase):
    def test_shared_answer_or_patch_cannot_leak_between_families(self):
        for borrowed in ("answer:shared", "patch:shared", "backport:shared", "source:shared"):
            with self.subTest(borrowed=borrowed):
                with self.assertRaisesRegex(ValueError, "Shared source"):
                    check_lineage([row("c1", "classification", "one", borrowed),
                                   row("d1", "diagnosis", "two", borrowed)], set())

    def test_development_or_same_family_cannot_cross_disjoint_tracks(self):
        with self.assertRaisesRegex(ValueError, "Development overlap"):
            check_lineage([row("c1", "classification", "one", "patch:same")], {"patch:same"})
        with self.assertRaisesRegex(ValueError, "Family crosses tracks"):
            check_lineage([row("c1", "classification", "one"),
                           row("d1", "diagnosis", "one")], set())
        self.assertEqual(len(check_lineage([row("c1", "classification", "one"),
                                            row("d1", "diagnosis", "two")], set())), 2)

    def test_budget_and_overabstention_preserve_the_denominator(self):
        build, call = "b1", "c1"
        item = {
            "track": "diagnosis",
            "case": {"case_id": "case-1", "family_id": "event-1", "build": build, "call_id": call,
                     "routes": ["timing", "interface"],
                     "contract": {"build": build, "version": "v1", "source": "fixture", "status": "APPLICABLE"},
                     "observations": [{"field": "interface.expected", "fact_id": "f1", "build": build,
                                       "call_id": call, "source": "fixture", "kind": "CONTRACT", "value": 0}]},
        }
        packets = {
            "interface.observed": {"field": "interface.observed", "fact_id": "f2", "build": build,
                                   "call_id": call, "source": "fixture", "kind": "OBSERVED", "value": 1},
        }
        answer = {"outcome": "SUPPORTED", "mechanisms": ["INTERFACE_CONTRACT"],
                  "decisive_fields": ["interface.observed"], "unresolved": None}
        adaptive = grade(run_trial(item, packets, "adaptive"), answer, set(packets))
        fixed = grade(run_trial(item, packets, "fixed_route"), answer, set(packets))
        self.assertTrue(adaptive["exact"])
        self.assertEqual(fixed["failure"], "diagnostic_step")
        metrics = summarize([fixed])
        self.assertEqual((metrics["attributable"], metrics["attributable_correct"],
                          metrics["excess_abstention"], metrics["request_cost"]), (1, 0, 1, 2))
        self.assertEqual(len(item["case"]["observations"]), 1)


if __name__ == "__main__":
    unittest.main()

