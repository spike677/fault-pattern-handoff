import json
from pathlib import Path
import unittest

from classify import classify


ROOT = Path(__file__).resolve().parent
REGRESSION = ROOT / "validation_0_3_1" / "readback" / "regression"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ReadbackContributionTests(unittest.TestCase):
    def assert_readbacks(self, stage, expected):
        directory = REGRESSION / stage
        cases = {case["case_id"]: case for case in load(directory / "A.json")["cases"]}
        catalog = load(ROOT / "catalog.json")
        self.assertEqual(set(cases), set(expected))
        for round_name in ("round-1", "round-2"):
            facts = load(directory / round_name / "facts.json")
            self.assertCountEqual([packet["case_id"] for packet in facts], cases)
            for packet in facts:
                case_id = packet["case_id"]
                with self.subTest(round=round_name, case=case_id):
                    action, = classify(cases[case_id], packet, catalog)["actions"]
                    actual = (action["status"], action.get("pattern_id"), action["role"],
                              action["count_as_independent"])
                    self.assertEqual(expected[case_id], actual)

    def test_same_source_count_and_incomplete_evidence(self):
        unresolved = ("insufficient", None, "unknown", False)
        self.assert_readbacks("first", {
            "G02": unresolved,
            "G06": ("leaf", "C3", "primary", True),
            "G10": unresolved,
        })

    def test_required_addend_with_consumer(self):
        self.assert_readbacks("supplement", {"G10": ("leaf", "C2", "primary", True)})


if __name__ == "__main__":
    unittest.main()
