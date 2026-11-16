"""Cover admission, supported actions and the new-catalog F workflow."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mech_v04 import classifier, evaluation


HERE = Path(__file__).resolve().parent
FIXED = HERE / "proposals" / "numeric_validation" / "regression"
read_json = evaluation.common.read_json


def action(packet, fact):
    return next(row for row in packet["actions"][0]["facts"] if row["key"] == fact)


class AdmissionTest(unittest.TestCase):
    def setUp(self):
        self.material = read_json(FIXED / "A.json")
        self.packets = read_json(FIXED / "facts.json")

    def classify(self, case_index=0):
        return classifier.classify_package(self.material, self.packets)[case_index]["actions"][0]

    def test_admitted_cards_and_single_square_neighbor(self):
        results = classifier.classify_package(self.material, self.packets)
        self.assertEqual([row["decision_version"] for row in results], [classifier.DECISION_VERSION] * 3)
        self.assertEqual([row["actions"][0].get("pattern_ref") for row in results],
                         ["MECH-v0.4:NUM-01", "MECH-v0.4:NUM-02", None])
        self.assertEqual(results[2]["actions"][0]["outside_reason"], "outside_catalog")
        self.assertEqual([row["actions"][0]["count_as_independent"] for row in results], [True] * 3)

    def test_formal_reader_does_not_need_a_pilot_outside_assertion(self):
        row = self.packets[0]["actions"][0]
        row["facts"] = [fact for fact in row["facts"] if fact["key"] != "established_other_defect"]
        self.assertEqual((self.classify()["pattern_id"], self.classify()["role"]), ("NUM-01", "primary"))

    def test_missing_and_observed_numeric_evidence_remain_insufficient(self):
        action(self.packets[1], "centered_variance_survives_at_same_precision")["claim_state"] = "observation"
        verdict = self.classify(1)
        self.assertEqual((verdict["status"], verdict["role"], verdict["count_as_independent"]),
                         ("insufficient", "unknown", False))
        self.assertIn("centered_variance_survives_at_same_precision", verdict["missing"])

    def test_causal_dispute_keeps_an_established_mechanism(self):
        row = self.packets[0]["actions"][0]
        causal = deepcopy(action(self.packets[0], "causal_role"))
        causal["value"] = False
        row["facts"].append(causal)
        verdict = self.classify()
        self.assertEqual((verdict["pattern_id"], verdict["role"], verdict["count_as_independent"]),
                         ("NUM-01", "unknown", False))

    def test_two_proven_first_wrong_states_on_one_action_remain_unresolved(self):
        row = self.packets[0]["actions"][0]
        other = deepcopy(action(self.packets[0], "loop_carried_narrow_state"))
        other["key"] = "pre_reduction_square_overflow"
        row["facts"].append(other)
        verdict = self.classify()
        self.assertEqual((verdict["status"], verdict["role"]), ("insufficient", "unknown"))
        self.assertIn("competing_mechanisms_for_one_action", verdict["conflicts"])

    def test_inherited_catalog_cards_and_compatible_contributions(self):
        old = read_json(classifier.PILOT_CATALOG)
        catalog = read_json(classifier.CATALOG)
        self.assertEqual({key: catalog["modes"][key] for key in old["modes"]}, old["modes"])
        self.assertEqual(catalog["combinations"], old["combinations"])
        material = HERE / "validation_0_3_1" / "method_acceptance_v2" / "supplement"
        previous = read_json(material / "round-1" / "results.json")
        current = classifier.classify_package(read_json(material / "A.json"),
                                              read_json(material / "round-1" / "facts.json"))
        fields = ("status", "pattern_id", "parent_id", "outside_reason", "role", "count_as_independent")
        def signatures(results):
            return [[tuple(row.get(key) for key in fields) for row in case["actions"]] for case in results]

        self.assertEqual(signatures(current), signatures(previous))

    def test_an_allowed_approximation_stays_compliant(self):
        material = {"cases": [{"case_id": "approximation", "sources": [
            {"id": "limit", "version": "fixture-1", "path": "spec", "kind": "contract",
             "text": "This input accepts an output error up to 1e-4."},
            {"id": "impl", "version": "fixture-1", "path": "norm", "kind": "code",
             "text": "raw_variance = mean_of_squares - square_of_mean"},
        ]}]}
        anchors = [{"source_id": src["id"], "start_line": 1, "end_line": 1, "quote": src["text"],
                    "use": use} for src, use in zip(material["cases"][0]["sources"],
                                                  ("requirement", "behavior"), strict=True)]
        facts = [{"key": key, "value": True, "claim_state": "derived",
                  "explanation": "The raw formula agrees with the reference within the bound on this input.",
                  "anchors": anchors} for key in ("variance_from_raw_moment_difference", "compliant")]
        packets = [{"case_id": "approximation", "operator": "normalization",
                    "fact_protocol": "classification_facts/0.3.1",
                    "actions": [{"id": "acceptable", "role": "unknown", "facts": facts,
                                 "scope": {"version": "fixture-1", "path": "norm", "claim": "static"}}]}]
        verdict = classifier.classify_package(material, packets)[0]["actions"][0]
        self.assertEqual((verdict["status"], verdict["outside_reason"], verdict["count_as_independent"]),
                         ("outside", "compliant", False))


class FWorkflowTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.fixture = [{
            "id": "api", "path": "api.txt", "version": "fixture-1", "kind": "contract",
            "text": "The accumulator shall retain binary32 through all updates.",
        }, {
            "id": "impl", "path": "kernel.txt", "version": "fixture-1", "kind": "code",
            "text": ("state = half(0)\nfor term in terms: state = half(float(state) + term)\n"
                     "return float(state)"),
        }]
        self.view = {"cases": [{"case_id": "smoke-a", "sources": self.fixture}]}
        self.a = self.put("A.json", self.view)
        self.answer = {
            "curator_id": "fixture-curator", "answer_reviewer_id": "fixture-reviewer",
            "curation_notes": "Synthetic end-to-end integration fixture",
            "cases": [{"case_id": "smoke-a", "family_id": "mech-v04-fixture", "operator": "toy dot",
                       "lineage": ["family:mech-v04-fixture", "event:mech-v04-fixture"],
                       "exposure_review": "Synthetic test", "source_view_review": "Literal fixture",
                       "actions": [{"id": "expected", "role": "primary",
                                    "allowed": [{"status": "leaf", "pattern_id": "NUM-01"}],
                                    "rationale": "The loop writes binary16",
                                    "near_neighbor": "legal terminal cast",
                                    "specific_action": "repeated writes of the narrow state",
                                    "decisive_facts": ["same terms, narrow loop state"]}]}],
        }
        self.b = self.put("B.json", self.answer)
        self.freeze = self.root / "freeze.json"
        self.seal = self.root / "seal.json"
        evaluation.freeze(self.freeze)
        evaluation.seal(self.freeze, self.a, self.b, self.seal, "exercise")

    def put(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def logged(self, context, name):
        card = read_json(classifier.CATALOG)["modes"]["NUM-01"]
        anchors = [{"source_id": "api", "start_line": 1, "end_line": 1, "use": "requirement"},
                   {"source_id": "impl", "start_line": 1, "end_line": 3, "use": "behavior"}]
        response = {"cases": [{"case_id": "smoke-a", "operator": "toy dot", "roles": ["accumulator"],
                               "readback": "Synthetic report",
                               "actions": [{"id": "predicted", "description": "Narrow loop state", "role": "primary",
                                            "upstream_id": None, "scope": {"source_id": "impl", "claim": "static",
                                                                          "build": None, "call_id": None},
                                            "facts": [{"key": key, "value": True, "anchors": anchors,
                                                       "claim_state": "derived", "explanation": "Fixture proof"}
                                                      for key in (*card["necessary"], "causal_role")]}],
                               "supporting_operations": []}]}
        events = [
            {"type": "thread.started", "thread_id": context},
            {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(response)}},
            {"type": "turn.completed", "usage": {}},
        ]
        log = self.root / f"{name}.jsonl"
        log.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
        return log

    def run_once(self, number):
        name = f"round-{number}"
        context = self.put(f"context-{number}.json", {
            "context_id": name, "executor_id": "fixture-executor",
            "execution": read_json(evaluation.EXECUTION),
        })
        capture = self.root / f"capture-{number}.json"
        evaluation.capture(self.freeze, self.a, self.seal, self.logged(name, name), context, capture)
        return capture

    def test_full_f_workflow_is_scored_as_exercise_only(self):
        first, second = self.run_once(1), self.run_once(2)
        lock = self.root / "lock.json"
        evaluation.lock(self.freeze, self.a, self.seal, first, second, lock)
        digest = evaluation.common.digest
        review = self.put("review.json", {
            "judge_id": "fixture-judge", "lock_sha256": digest(lock), "answer_sha256": digest(self.b),
            "runs": [{"run_sha256": digest(run), "cases": [{
                "case_id": "smoke-a", "actions": [{"prediction_id": "predicted", "expected_id": "expected",
                                                  "facts_supported": True, "action_correct": True,
                                                  "rationale": "Fixture facts", "action_rationale": "Same store",
                                                  "failure_causes": []}],
            }]} for run in (first, second)],
            "stability": [{"case_id": "smoke-a", "same_decisive_facts": True,
                           "same_specific_action": True, "rationale": "Fixture is deterministic"}],
        })
        result = self.root / "score.json"
        evaluation.score(self.freeze, self.a, self.seal, first, second, lock, self.b, review, result)
        score = read_json(result)
        self.assertEqual((score["scope"], score["mechanism_namespace"]), ("exercise_only", "MECH-v0.4"))
        self.assertEqual([run["metrics"]["families_strict"] for run in score["runs"]], [1, 1])

        bad_lock = read_json(lock)
        bad_lock["run_sha256"].reverse()
        altered = self.put("wrong-lock.json", bad_lock)
        with patch.object(evaluation.common, "digest", wraps=digest) as observed:
            with self.assertRaisesRegex(ValueError, "before accessing B"):
                evaluation.score(self.freeze, self.a, self.seal, first, second, altered, self.b, review,
                                 self.root / "unexpected.json")
            self.assertFalse(any(call.args == (self.b,) for call in observed.call_args_list))

    def test_exposures_and_colocated_answers_are_rejected(self):
        self.answer["cases"][0]["lineage"].append("event:github.com/QDRANT/qdrant#10350")
        exposed = self.put("seen.json", self.answer)
        with self.assertRaisesRegex(ValueError, "overlaps development"):
            evaluation.seal(self.freeze, self.a, exposed, self.root / "seen-seal.json", "exercise")
        with self.assertRaisesRegex(ValueError, "outside the A directory"):
            evaluation.seal(self.freeze, self.a, self.b, self.root / "real-seal.json", "real")

    def test_real_reader_requires_post_seal_access_isolation(self):
        sub = self.root / "reader"
        sub.mkdir()
        a = self.put("reader/A.json", self.view)
        seal = self.root / "real-seal.json"
        evaluation.seal(self.freeze, a, self.b, seal, "real")
        probe = self.root / "probe.json"
        evaluation.common.probe(self.b, probe)
        with patch.object(evaluation, "call_reader") as remote:
            with self.assertRaisesRegex(ValueError, "isolation probe before reading"):
                evaluation.read(self.freeze, a, seal, self.root / "read.jsonl", probe)
            remote.assert_not_called()
