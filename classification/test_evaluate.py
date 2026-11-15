"""The classification-only track is exercised here with synthetic material."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from classify import classify
import evaluate as evaluation


def put(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


class EvaluationTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.catalog = evaluation.read_json(evaluation.ROOT / "catalog.json")
        self.execution = {"model": "exercise", "tools": [], "prompt": "source view only"}
        self.freeze = self.root / "freeze.json"
        evaluation.freeze(put(self.root / "config.json", self.execution),
                          put(self.root / "exposures.json", ["event:development-only"]), self.freeze)
        self.case = {"case_id": "opaque-case", "sources": [{
            "id": "source", "version": "v-fixture", "path": "kernel.py", "kind": "code",
            "text": "expected parameter is attr_a; kernel reads attr_b with another role",
        }]}
        self.packet = {
            "case_id": self.case["case_id"], "operator": "toy", "roles": ["argument"],
            "actions": [{"id": "pred-action", "role": "primary",
                         "scope": {"version": "v-fixture", "path": "kernel.py", "claim": "static"},
                         "facts": [{"key": key, "value": True, "anchors": [{
                             "source_id": "source", "start_line": 1, "end_line": 1,
                             "quote": self.case["sources"][0]["text"],
                         }]} for key in self.catalog["modes"]["P1"]["necessary"]]}],
        }
        self.prediction = classify(self.case, self.packet, self.catalog)
        self.assertEqual(self.prediction["actions"][0]["pattern_id"], "P1")
        self.answers = {
            "curator_id": "curator", "answer_reviewer_id": "reviewer", "curation_notes": "Synthetic",
            "cases": [{
                "case_id": self.case["case_id"], "family_id": "family-001", "operator": "toy",
                "lineage": ["family:family-001", "event:synthetic-a"],
                "exposure_review": "A controlled example",
                "source_view_review": "Unmodified synthetic bytes",
                "actions": [{"id": "expected-action", "role": "primary",
                             "allowed": [{"status": "leaf", "pattern_id": "P1"}],
                             "rationale": "Attribute source differs", "near_neighbor": "P2",
                             "decisive_facts": ["Expected and actual source differ"]}],
            }],
        }
        self.a = put(self.root / "a.json", {"cases": [self.case]})
        self.b = put(self.root / "b.json", self.answers)
        self.seal = self.root / "seal.json"
        evaluation.seal(self.freeze, self.a, self.b, self.seal, "exercise")

    def capture(self, name, context_id, prediction=None):
        context = put(self.root / f"context-{name}.json", {
            "context_id": context_id, "executor_id": "executor",
        })
        results = put(self.root / f"results-{name}.json", [prediction or self.prediction])
        facts = put(self.root / f"facts-{name}.json", [self.packet])
        log = self.root / f"log-{name}.txt"
        log.write_text("synthetic exercise\n", encoding="utf-8")
        output = self.root / f"run-{name}.json"
        evaluation.capture(self.freeze, self.a, self.seal, results, context, facts, log, output)
        return output

    def test_score_rejects_unlocked_predictions_before_opening_b(self):
        with patch.object(evaluation, "digest", wraps=evaluation.digest) as observed:
            first = self.capture("one", "context-1")
            second = self.capture("two", "context-2")
            lock = self.root / "lock.json"
            evaluation.lock(self.freeze, self.a, self.seal, first, second, lock)
            data = evaluation.read_json(lock)
            data["run_sha256"][1] = "0" * 64
            put(lock, data)
            with self.assertRaisesRegex(ValueError, "before accessing B"):
                evaluation.score(self.freeze, self.a, self.seal, first, second, lock, self.b,
                                 self.root / "unused-review.json", self.root / "score.json")
            self.assertTrue(all(call.args[0] != self.b for call in observed.call_args_list))

    def test_correct_labels_but_unsupported_facts_fail_strict_family_scoring(self):
        first = self.capture("one", "context-1")
        second = self.capture("two", "context-2")
        lock = self.root / "lock.json"
        evaluation.lock(self.freeze, self.a, self.seal, first, second, lock)
        reviewed = put(self.root / "review.json", {
            "judge_id": "external-judge", "lock_sha256": evaluation.digest(lock),
            "answer_sha256": evaluation.digest(self.b), "runs": [
                {"run_sha256": evaluation.digest(run), "cases": [{
                    "case_id": self.case["case_id"], "actions": [{
                        "prediction_id": "pred-action", "expected_id": "expected-action",
                        "facts_supported": False, "rationale": "Decisive assertion not supported",
                        "failure_causes": ["material_understanding"],
                    }],
                }]} for run in (first, second)
            ],
        })
        output = self.root / "score.json"
        evaluation.score(self.freeze, self.a, self.seal, first, second, lock, self.b, reviewed, output)
        result = evaluation.read_json(output)
        counts = result["runs"][0]["metrics"]
        self.assertEqual(result["scope"], "exercise_only")
        self.assertEqual(counts["families_strict"], 0)
        self.assertEqual(counts["action_counts"]["label_match_with_failed_evidence"], 1)
        self.assertEqual(result["stability"]["same_and_both_incorrect_cases"], 1)

    def test_exposure_and_duplicate_context_are_rejected(self):
        changed = deepcopy(self.answers)
        changed["cases"][0]["lineage"].append("event:development-only")
        exposed = put(self.root / "exposed.json", changed)
        with self.assertRaisesRegex(ValueError, "overlaps development"):
            evaluation.seal(self.freeze, self.a, exposed, self.root / "exposed-seal.json", "exercise")
        first = self.capture("one", "context-1")
        second = self.capture("two", "context-1")
        with self.assertRaisesRegex(ValueError, "cannot share"):
            evaluation.lock(self.freeze, self.a, self.seal, first, second, self.root / "lock.json")

    def test_real_run_cannot_claim_isolation_from_readable_sentinel(self):
        evaluation.seal(self.freeze, self.a, self.b, self.root / "real-seal.json", "real")
        sentinel = self.root / "benign.txt"
        sentinel.touch()
        probe = self.root / "probe.json"
        evaluation.probe(sentinel, probe)
        package = evaluation.read_json(self.root / "real-seal.json")
        context = {
            "context_id": "claimed", "executor_id": "executor", "witness_id": "external",
            "execution": self.execution, "isolation_mechanism": "acl", "sentinel_in_custody": True,
            "only_approved_inputs": True, "fresh_context": True, "no_prior_predictions": True,
        }
        with self.assertRaisesRegex(ValueError, "denied or unmounted"):
            evaluation.verify_context(context, package, evaluation.read_json(probe),
                                      {"execution": self.execution})

    def test_a_rejects_prefilled_routes_and_capture_rechecks_prediction(self):
        a_with_routes = deepcopy(self.case)
        a_with_routes["routes"] = ["interface"]
        leaked = put(self.root / "prefilled.json", {"cases": [a_with_routes]})
        with self.assertRaisesRegex(ValueError, "raw material"):
            evaluation.a_cases(leaked)
        mismatched = deepcopy(self.prediction)
        mismatched["actions"][0]["pattern_id"] = "P2"
        with self.assertRaisesRegex(ValueError, "replay of the frozen"):
            self.capture("one", "context-1", mismatched)


if __name__ == "__main__":
    unittest.main()

