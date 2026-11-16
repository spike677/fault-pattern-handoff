"""Regression tests for action evidence and normal consumers during readback."""

from copy import deepcopy
from pathlib import Path
import unittest

from proposals.numeric_validation.classify_candidates import load
from proposals.numeric_validation_v042.controls import approximate_normalization, terminal_conversion
from proposals.numeric_validation_v042.reader import decode_response, response_schema


HERE = Path(__file__).resolve().parent
NUMERIC = HERE / "proposals" / "numeric_validation"
METHOD = HERE / "validation_0_3_1" / "method_acceptance_v2" / "first"


def reader_input(package, case_id):
    return {"cases": [case for case in package["cases"] if case["case_id"] == case_id]}


def reader_response(material, packet, supporting_operations=()):
    packet = deepcopy(packet)
    sources = material["cases"][0]["sources"]
    packet.pop("fact_protocol")
    packet["readback"] = "Regression fixture."
    packet["supporting_operations"] = list(supporting_operations)
    for action in packet["actions"]:
        action.setdefault("upstream_id", None)
        scope = action["scope"]
        source = next(s for s in sources if (s["version"], s["path"]) == (scope["version"], scope["path"]))
        action["scope"] = {"source_id": source["id"], "claim": scope["claim"],
                           "build": scope.get("build"), "call_id": scope.get("call_id")}
        for fact in action["facts"]:
            for anchor in fact["anchors"]:
                anchor.pop("quote")
    return {"cases": [packet]}


class NumericReaderRegression(unittest.TestCase):
    def setUp(self):
        self.catalog = load(HERE / "catalog.json")

    def decode(self, material, packet, supporting_operations=()):
        response = reader_response(material, packet, supporting_operations)
        result, _ = decode_response(material, response, self.catalog)
        return result

    def test_schema_keeps_support_outside_the_actions(self):
        packet = response_schema()["properties"]["cases"]["items"]
        self.assertIn("supporting_operations", packet["required"])
        self.assertEqual(packet["properties"]["supporting_operations"]["items"],
                         {"$ref": "#/$defs/supporting_operation"})

    def test_unchanged_fixed_positives_and_overflow_neighbor(self):
        stage = NUMERIC / "regression"
        for packet, expected in zip(load(stage / "facts.json"), ("NUM-01", "NUM-02", "pre_reduction_square_overflow")):
            with self.subTest(case=packet["case_id"]):
                result = self.decode(reader_input(load(stage / "A.json"), packet["case_id"]), packet)
                decision, = result["decisions"]["cases"][0]["actions"]
                self.assertEqual(decision.get("pattern_id") or decision.get("reason"), expected)
                self.assertEqual(result["reader_issues"], [])

    def test_observation_does_not_establish_an_action(self):
        stage = NUMERIC / "regression"
        packet = load(stage / "facts.json")[0]
        fact, = (f for f in packet["actions"][0]["facts"] if f["key"] == "implementation_action")
        fact["claim_state"] = "observation"
        result = self.decode(reader_input(load(stage / "A.json"), "E06"), packet)
        self.assertEqual(result["facts"][0]["actions"][0]["facts"][
            packet["actions"][0]["facts"].index(fact)]["claim_state"], "observation")
        self.assertEqual(result["decisions"]["cases"][0]["actions"][0]["status"], "insufficient")
        self.assertIn("unproven_implementation_action", {row["code"] for row in result["reader_issues"]})

    def test_contract_citation_must_include_behavior_in_the_action_file(self):
        stage = NUMERIC / "regression"
        material = reader_input(load(stage / "A.json"), "G05")
        packet = next(row for row in load(stage / "facts.json") if row["case_id"] == "G05")
        action, = packet["actions"]
        contract, = (fact for fact in action["facts"] if fact["key"] == "applicable_contract")
        self.assertEqual(self.decode(material, packet)["decisions"]["cases"][0]["actions"][0]["pattern_id"],
                         "NUM-02")
        contract["anchors"] = [anchor for anchor in contract["anchors"] if anchor["source_id"] != "s3"]
        decision, = self.decode(material, packet)["decisions"]["cases"][0]["actions"]
        self.assertEqual((decision["status"], decision["legacy_outside_reason"]),
                         ("insufficient", "outside_catalog"))
        self.assertIn({"fact": "applicable_contract", "code": "missing_derivation_basis"}, decision["issues"])

    def test_insufficient_action_keeps_its_explicit_unknown_role(self):
        stage = NUMERIC / "regression"
        packet = load(stage / "facts.json")[0]
        material = reader_input(load(stage / "A.json"), packet["case_id"])
        packet["actions"][0].update(role="unknown", facts=[])
        result = self.decode(material, packet)
        action, = result["decisions"]["cases"][0]["actions"]
        self.assertEqual((action["status"], action["role"], action["count_as_independent"]),
                         ("insufficient", "unknown", False))
        packet["actions"] = []
        with self.assertRaisesRegex(ValueError, "explicit insufficient action"):
            self.decode(material, packet)

    def test_contract_can_allow_fp16_at_the_end(self):
        rounded_at_exit = terminal_conversion((2048, 1))
        self.assertEqual((rounded_at_exit["wide_state"], rounded_at_exit["terminal_fp16"]),
                         (2049, 2048))
        with_another_update = terminal_conversion((2048, 1, 1))
        self.assertEqual((with_another_update["terminal_fp16"], with_another_update["iterative_fp16"]),
                         (2050, 2048))

    def test_approximation_within_tolerance_and_cancellation_differ(self):
        normal = approximate_normalization((1, 2, 4))
        self.assertGreater(normal["max_absolute_error"], 0)
        self.assertLess(normal["max_absolute_error"], 1e-4)
        lost = approximate_normalization((8191, 8193))
        self.assertEqual((lost["variance"], lost["reference_variance"]), (0, 1))
        self.assertGreater(lost["max_absolute_error"], 1e-4)

    def test_qdrant_normal_widening_and_flashinfer_square(self):
        stage = NUMERIC / "holdout"
        packets = load(stage / "round-1" / "result.json")["facts"]
        examples = (("N501", "loop_carried_narrow_state", "NUM-01"),
                    ("N503", "pre_reduction_square_overflow", "pre_reduction_square_overflow"))
        for case_id, first_loss, expected in examples:
            with self.subTest(case=case_id):
                material = reader_input(load(stage / "A.json"), case_id)
                packet = next(row for row in packets if row["case_id"] == case_id)
                root, = (row for row in packet["actions"] if row["role"] == "primary")
                implementation, = (f for f in root["facts"] if f["key"] == "implementation_action")
                proof, = (f for f in root["facts"] if f["key"] == first_loss)
                implementation.update({k: deepcopy(proof[k]) for k in ("claim_state", "explanation", "anchors")})
                consumer, = (f for f in root["facts"] if f["key"] == "distorted_value_consumed")
                anchors = [{k: v for k, v in a.items() if k != "quote"} for a in consumer["anchors"]]
                supports = [{"action_id": root["id"], "description": consumer["explanation"], "anchors": anchors}]
                # A normal consumer entered as an extra fault stays visible to scoring.
                erroneous = self.decode(material, packet)
                self.assertIn("unsupported_downstream_effect", {row["code"] for row in erroneous["reader_issues"]})
                self.assertEqual(len(erroneous["facts"][0]["actions"]), 2)
                packet["actions"] = [root]
                result = self.decode(material, packet, supports)
                decision, = result["decisions"]["cases"][0]["actions"]
                self.assertEqual(decision.get("pattern_id") or decision.get("reason"), expected)
                support, = result["supporting_operations"][case_id]
                self.assertTrue(support["anchors"][0]["quote"])
                self.assertEqual(result["reader_issues"], [])
                supports[0]["anchors"][0]["end_line"] = 10000
                invalid = self.decode(material, packet, supports)
                self.assertIn("invalid_excerpt_line_range", {row["code"] for row in invalid["reader_issues"]})

    def test_true_downstream_and_two_independent_roots_survive(self):
        for case_id, roles, counts in (
            ("H01", ["primary", "downstream"], [True, False]),
            ("ops-nn-2828", ["independent", "independent"], [True, True]),
        ):
            with self.subTest(case=case_id):
                material = reader_input(load(METHOD / "A.json"), case_id)
                packet = next(row for row in load(METHOD / "round-1" / "facts.json") if row["case_id"] == case_id)
                result = self.decode(material, packet)
                actions = result["decisions"]["cases"][0]["actions"]
                self.assertEqual([row["role"] for row in actions], roles)
                self.assertEqual([row["count_as_independent"] for row in actions], counts)
                self.assertEqual(result["reader_issues"], [])
