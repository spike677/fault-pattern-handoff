"""Regression for preserving the exact provenance and scope of a dependency contract."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from classify import FACT_PROTOCOL, classify_package
from validation_0_4_1.dependency_contracts import check_requirements, materialize


ROOT = Path(__file__).with_name("validation_0_4_1") / "dependency_supplement"


def load(path):
    return json.loads(path.read_bytes())


class PinnedDependencyContracts(unittest.TestCase):
    def setUp(self):
        self.material = load(ROOT / "original-A.json")
        self.bindings = load(ROOT / "bindings.json")
        self.sources = {source["id"]: source for source in self.material["cases"][0]["sources"]}

    def test_bound_requirement_crosses_versions_with_exact_old_behavior(self):
        view, projected = materialize(self.material, self.bindings)
        scoped = next(source for source in view["cases"][0]["sources"] if source["id"] == "s2")
        origin = self.sources["s2"]
        self.assertEqual(scoped, {**origin, "version": self.sources["s11"]["version"]})
        self.assertNotEqual(origin["version"], scoped["version"])

        anchors = [
            {"source_id": "s2", "start_line": 7, "end_line": 7, "use": "requirement",
             "quote": origin["text"].splitlines()[6]},
            {"source_id": "s11", "start_line": 17, "end_line": 23, "use": "behavior",
             "quote": "\n".join(self.sources["s11"]["text"].splitlines()[16:23])},
        ]
        keys = ("applicable_contract", "established_other_defect", "implementation_action", "causal_role")
        packet = {"case_id": "V404", "fact_protocol": FACT_PROTOCOL, "actions": [{
            "id": "copy", "role": "primary", "scope": projected["V404", "s2"], "facts": [
                {"key": key, "value": True, "claim_state": "derived", "anchors": anchors,
                 "explanation": "The selected empty-axes path copies input before the required square."}
                for key in keys
            ],
        }]}
        catalog = load(Path(__file__).with_name("catalog.json"))
        original = classify_package(self.material, [packet], catalog)[0]["actions"][0]
        self.assertEqual(original["status"], "insufficient")
        self.assertIn("source_version_mismatch", {record["code"] for record in original["issues"]})
        check_requirements([packet], projected)
        accepted = classify_package(view, [packet], catalog)[0]["actions"][0]
        self.assertEqual((accepted["status"], accepted["outside_reason"]), ("outside", "outside_catalog"))
        self.assertTrue(accepted["count_as_independent"])

        for use, path in (("behavior", packet["actions"][0]["scope"]["path"]),
                          ("requirement", "unrelated/kernel.cc")):
            with self.subTest(use=use, path=path):
                misplaced = deepcopy(packet)
                action = misplaced["actions"][0]
                action["scope"]["path"] = path
                action["facts"][0]["anchors"][0]["use"] = use
                with self.assertRaisesRegex(ValueError, "bound static path"):
                    check_requirements([misplaced], projected)

    def test_wrong_dependency_tag_is_rejected(self):
        self.sources["s14"]["version"] = "refs/tags/v1.20.0"
        with self.assertRaisesRegex(ValueError, "exact dependency tag"):
            materialize(self.material, self.bindings)

    def test_contract_from_an_unrelated_repository_is_rejected(self):
        self.sources["s2"]["origin"] = self.sources["s2"]["origin"].replace("/onnx/onnx/", "/other/onnx/", 1)
        with self.assertRaisesRegex(ValueError, "unique contract"):
            materialize(self.material, self.bindings)


if __name__ == "__main__":
    unittest.main()
