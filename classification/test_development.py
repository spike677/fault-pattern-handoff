"""Development replays for the classification pilot, kept apart from blind scoring."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from classify import classify, classify_package


ROOT = Path(__file__).resolve().parent


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8-sig"))


def label(action):
    return action.get("pattern_id") or action.get("parent_id") or action.get("outside_reason")


class DevelopmentClassification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load("catalog.json")
        cls.cases = {row["case_id"]: row for row in load("development_cases.json")["cases"]}
        cls.packets = {row["case_id"]: row for row in load("development_facts.json")}

    def trial(self, case_id, packet=None):
        return classify(self.cases[case_id], self.packets[case_id] if packet is None else packet, self.catalog)

    def test_real_archived_material(self):
        expected = ["P2", "P1", "outside_catalog", "L1", "L2", "outside_catalog", "C2", "C1", "C3", "L1", "compliant"]
        self.assertEqual(len(expected), len(self.cases))
        for i, verdict in enumerate(expected, 1):
            case_id = f"dev-{i:02}"
            with self.subTest(case_id=case_id):
                output, = self.trial(case_id)["actions"]
                self.assertEqual(label(output), verdict)
                self.assertEqual(output["status"], "outside" if verdict in {"outside_catalog", "compliant"} else "leaf")
                self.assertEqual(output["scope"]["claim"], "reported" if i >= 8 else "static")
                self.assertFalse(output["issues"])
                self.assertTrue(all(f["anchors"] and f["explanation"] for f in output["facts"]))

    def test_batch_matches_cases_by_id(self):
        batch = load("development_cases.json")
        packets = list(reversed(load("development_facts.json")))
        output = classify_package(batch, packets, self.catalog)
        self.assertEqual(output, [self.trial(case["case_id"]) for case in batch["cases"]])
        with self.assertRaisesRegex(ValueError, "IDs must match"):
            classify_package(batch, packets[1:], self.catalog)

    def test_unfamiliar_operator_and_static_without_call(self):
        packet = deepcopy(self.packets["dev-04"])
        packet["operator"] = "unknown operator"
        result, = self.trial("dev-04", packet)["actions"]
        self.assertNotIn("call_id", result["scope"])
        self.assertEqual(label(result), "L1")

    def test_author_report_does_not_prove_code_or_runtime(self):
        packet = deepcopy(self.packets["dev-08"])
        packet["actions"][0]["scope"]["claim"] = "static"
        result, = self.trial("dev-08", packet)["actions"]
        self.assertEqual(result["status"], "insufficient")
        packet["actions"][0]["scope"].update(claim="runtime", build="different", call_id="other")
        result, = self.trial("dev-08", packet)["actions"]
        self.assertEqual(result["status"], "insufficient")

    def test_wrong_quoted_lines_or_wrong_version(self):
        packet = deepcopy(self.packets["dev-02"])
        action, = packet["actions"]
        action["facts"][2]["anchors"][0]["quote"] = "unsupported quote"
        result, = self.trial("dev-02", packet)["actions"]
        self.assertEqual(result["status"], "insufficient")
        self.assertIn("quote_not_in_source_span", {issue["code"] for issue in result["issues"]})
        action["scope"]["version"] = self.packets["dev-01"]["actions"][0]["scope"]["version"]
        result, = self.trial("dev-02", packet)["actions"]
        self.assertEqual(result["status"], "insufficient")
        self.assertIn("source_version_mismatch", {issue["code"] for issue in result["issues"]})

    def test_verified_parent_and_established_other_defect(self):
        packet = deepcopy(self.packets["dev-02"])
        action, = packet["actions"]
        contract, _, actual, _ = action["facts"]
        violation = {**actual, "key": "parameter_violation"}
        action["facts"] = [contract, violation]
        result, = self.trial("dev-02", packet)["actions"]
        self.assertEqual((result["status"], label(result)), ("parent", "parameter"))
        result, = self.trial("dev-03")["actions"]
        self.assertEqual((result["status"], label(result)), ("outside", "outside_catalog"))

    def test_missing_fact_and_contradictory_fact(self):
        packet = deepcopy(self.packets["dev-01"])
        action, = packet["actions"]
        treatment = action["facts"].pop()
        result, = self.trial("dev-01", packet)["actions"]
        self.assertEqual(result["status"], "insufficient")
        action["facts"].extend([treatment, {**treatment, "value": False}])
        result, = self.trial("dev-01", packet)["actions"]
        self.assertEqual(result["status"], "insufficient")
        self.assertIn("wrong_state_treatment", result["conflicts"])

    def test_wrong_recomputation_cannot_support_leaf(self):
        packet = deepcopy(self.packets["dev-05"])
        packet["actions"][0]["facts"][-1]["calculation"] = {"expected": 8, "actual": 8}
        result, = self.trial("dev-05", packet)["actions"]
        self.assertEqual(result["status"], "insufficient")
        self.assertIn("calculation_disagrees", {issue["code"] for issue in result["issues"]})

    def test_dependency_and_independent_defects_have_distinct_counts(self):
        case = deepcopy(self.cases["dev-02"])
        packet = deepcopy(self.packets["dev-02"])
        case["case_id"] = packet["case_id"] = "synthetic-causal-count"
        scope = packet["actions"][0]["scope"]
        # Synthetic assertions exercise causal grouping and do not supply a real-world verdict.
        source = {"id": "control", "path": scope["path"], "version": scope["version"], "kind": "code",
                  "text": "Synthetic control: wrong attribute mask admits a padded member."}
        case["sources"].append(source)
        src = {"source_id": "control", "start_line": 1, "end_line": 1, "quote": source["text"]}
        keys = self.catalog["modes"]["C1"]["necessary"]
        c1 = {"id": "a2", "scope": scope, "role": "downstream", "upstream_id": "a1",
              "facts": [{"key": key, "value": True, "anchors": [src]} for key in keys]}
        packet["actions"].append(c1)
        actions = classify(case, packet, self.catalog)["actions"]
        self.assertEqual([label(a) for a in actions], ["P1", "C1"])
        self.assertEqual([a["count_as_independent"] for a in actions], [True, False])
        c1.pop("upstream_id")
        c1["role"] = "independent"
        actions = classify(case, packet, self.catalog)["actions"]
        self.assertEqual([a["count_as_independent"] for a in actions], [True, True])


if __name__ == "__main__":
    unittest.main()

