from copy import deepcopy
from pathlib import Path
import unittest

from diagnose import BadEvidence, diagnose, read_json


ROOT = Path(__file__).resolve().parent


def scoped_case(*routes, **fields):
    case = {
        "case_id": "unit", "family_id": "dev-unit", "build": "build-1", "call_id": "call-1",
        "routes": list(routes),
        "contract": {"version": "v1", "build": "build-1", "source": "fixture line 1",
                     "status": "APPLICABLE"},
        "observations": [],
    }
    for i, (key, value) in enumerate(fields.items()):
        case["observations"].append({
            "field": key.replace("__", "."), "fact_id": f"f{i}", "build": case["build"],
            "call_id": case["call_id"], "source": "fixture line 2", "kind": "OBSERVED", "value": value,
        })
    return case


def check(result, mechanism):
    return next(row for row in result["checks"] if row["mechanism"] == mechanism)["judgment"]


def span(n):
    return {"unit": "element", "range": [0, n]}


def ref(value, input_kind="OBSERVED"):
    return {"dtype": "float32", "values": [value], "qualified": True, "input_kind": input_kind,
            "reference_id": "reference-1", "state_id": "state-1", "mapping_id": "map-1"}


class DevelopmentRegressions(unittest.TestCase):
    def test_archived_cases_stop_at_supported_or_unknown(self):
        expected = {
            "DEV-CONV3D": ("SUPPORTED", {"PLAN_CONSUMPTION"}),
            "DEV-RMSNORM": ("SUPPORTED", {"ADDRESS_MAPPING"}),
            "DEV-FLASHINFER": ("UNKNOWN", set()),
            "DEV-EMBEDDINGBAG-BASE": ("SUPPORTED", {"INTERFACE_CONTRACT"}),
            "DEV-EMBEDDINGBAG-HEAD": ("SUPPORTED", {"INTERFACE_CONTRACT"}),
        }
        for case in read_json(ROOT / "development.json")["cases"]:
            with self.subTest(case=case["case_id"]):
                result = diagnose(case)
                self.assertEqual((result["outcome"], set(result["supported_mechanisms"])),
                                 expected[case["case_id"]])
                if case["case_id"] == "DEV-CONV3D":
                    self.assertEqual(check(result, "PLAN_GENERATION"), "UNKNOWN")
                    self.assertEqual(check(result, "PLAN_TRANSFER"), "UNKNOWN")

    def test_host_generation_and_transport_have_distinct_boundaries(self):
        generation = diagnose(scoped_case("plan", plan__expected=span(3), plan__produced=span(4),
                                          plan__received=span(4), plan__consumed=span(4)))
        transport = diagnose(scoped_case("plan", plan__expected=span(3), plan__produced=span(3),
                                         plan__received=span(4), plan__consumed=span(4)))
        self.assertEqual(generation["supported_mechanisms"], ["PLAN_GENERATION"])
        self.assertEqual(transport["supported_mechanisms"], ["PLAN_TRANSFER"])

    def test_layout_exclusion_scope_and_missing_observation(self):
        case = scoped_case("layout", layout__geometry={
            "unit": "element", "base": 0, "shape": [4, 1], "strides": [4, 2], "index": [1, 0],
        }, layout__actual_offset={"unit": "element", "offset": 4})
        self.assertEqual(check(diagnose(case), "ADDRESS_MAPPING"), "EXCLUDED")
        case["observations"].pop()
        result = diagnose(case)
        self.assertEqual(result["outcome"], "UNKNOWN")
        self.assertEqual(result["next_observation"]["field"], "layout.actual_offset")
        case["contract"]["status"] = "OUT_OF_SCOPE"
        self.assertEqual(diagnose(case)["outcome"], "OUT_OF_SCOPE")
        case["contract"]["build"] = "later-release"
        self.assertEqual(diagnose(case)["outcome"], "UNKNOWN")

    def test_interface_explicit_zero_and_stale_build(self):
        case = scoped_case("interface", interface__expected={"padding_idx": 0},
                           interface__observed={"padding_idx": 0})
        self.assertEqual(diagnose(case)["outcome"], "NO_SUPPORTED_MECHANISM")
        case["observations"][1]["build"] = "unrelated-build"
        result = diagnose(case)
        self.assertEqual(result["outcome"], "UNKNOWN")
        self.assertEqual(result["evidence_issues"][0]["reason"], "missing_or_mismatched_provenance")


class EvidenceRegressions(unittest.TestCase):
    def test_conflict_and_contract_used_as_observation_are_unknown(self):
        case = scoped_case("interface", interface__expected=1, interface__observed=2)
        other = deepcopy(case["observations"][1])
        other.update(fact_id="conflict", value=1)
        case["observations"].append(other)
        self.assertEqual(diagnose(case)["checks"][0]["reason"], "conflict")
        case["observations"].pop()
        case["observations"][1]["kind"] = "CONTRACT"
        self.assertEqual(diagnose(case)["outcome"], "UNKNOWN")

    def test_malformed_route_is_rejected(self):
        case = scoped_case("interface")
        case["routes"].append([])
        with self.assertRaises(BadEvidence):
            diagnose(case)

    def test_manifest_requires_both_outputs_and_matching_dtype(self):
        item = {"dtype": "float32", "shape": [1], "mode": "BITWISE"}
        value = {"dtype": "float32", "shape": [1], "hex": "00000000"}
        case = scoped_case("numeric", comparison__expected={"a": item, "b": item},
                           comparison__actual={"a": value}, comparison__reference={"a": value})
        self.assertEqual(diagnose(case)["output_check"]["missing_outputs"],
                         {"actual": ["b"], "reference": ["b"]})
        case["observations"][0]["value"].pop("b")
        case["observations"][1]["value"]["a"]["dtype"] = "int32"
        self.assertEqual(diagnose(case)["output_check"]["status"], "INCOMPATIBLE")

    def test_boolean_shape_is_not_an_integer_extent(self):
        item = {"dtype": "float32", "shape": [1], "mode": "BITWISE"}
        left = {"dtype": "float32", "shape": [True], "hex": "00000000"}
        right = {"dtype": "float32", "shape": [1], "hex": "00000000"}
        case = scoped_case("numeric", comparison__expected={"out": item}, comparison__actual={"out": left},
                           comparison__reference={"out": right})
        self.assertEqual(diagnose(case)["output_check"]["status"], "INCOMPATIBLE")

    def test_finite_extreme_values_do_not_pass_when_both_intermediates_overflow(self):
        expected = ref(-1e308)
        expected["dtype"] = "float64"
        case = scoped_case("numeric", numeric__actual={"dtype": "float64", "values": [1e308]},
                           numeric__ref_observed=expected, numeric__tolerance={"atol": 0, "rtol": 1.9})
        self.assertEqual(check(diagnose(case), "LOCAL_NUMERIC_DEVIATION"), "SUPPORTED")
        case["observations"][2]["value"]["rtol"] = 2
        self.assertEqual(check(diagnose(case), "LOCAL_NUMERIC_DEVIATION"), "EXCLUDED")

    def test_signed_zero_differs_by_bits_and_matches_numerically(self):
        case = scoped_case("numeric", comparison__expected={
            "out": {"dtype": "float32", "shape": [1], "mode": "BITWISE"}
        }, comparison__actual={"out": {"dtype": "float32", "shape": [1], "hex": "00000000"}},
            comparison__reference={"out": {"dtype": "float32", "shape": [1], "hex": "00000080"}})
        self.assertEqual(diagnose(case)["output_check"]["status"], "DIFFERENT")
        case["observations"][0]["value"]["out"].update(mode="NUMERIC", tolerance={"atol": 0, "rtol": 0})
        for obs, number in zip(case["observations"][1:], [0.0, -0.0]):
            obs["value"]["out"]["values"] = [number]
        self.assertEqual(diagnose(case)["output_check"]["status"], "PASS")

    def test_staged_numeric_reference_and_incompatible_basis(self):
        case = scoped_case("numeric", numeric__actual={"dtype": "float32", "values": [3]},
                           numeric__ref_observed=ref(3), numeric__ref_healthy=ref(0, "HEALTHY"),
                           numeric__tolerance={"atol": 0, "rtol": 0})
        self.assertEqual(diagnose(case)["numeric_stage"]["status"], "UPSTREAM_PROPAGATION")
        case["observations"][0]["value"]["values"] = [4]
        self.assertEqual(diagnose(case)["numeric_stage"]["status"], "LOCAL_AND_PROPAGATION")
        case["observations"][2]["value"]["mapping_id"] = "wrong-map"
        self.assertEqual(diagnose(case)["numeric_stage"]["status"], "UNKNOWN")
        case["observations"][1]["value"]["qualified"] = False
        self.assertEqual(check(diagnose(case), "LOCAL_NUMERIC_DEVIATION"), "UNKNOWN")

    def test_contribution_identity_supports_multiple_distinct_predicates(self):
        case = scoped_case("contribution", contribution__expected=["k0", "k1"],
                           contribution__observed=["k0", "k0", "pad"])
        self.assertEqual(set(diagnose(case)["supported_mechanisms"]), {
            "UNEXPECTED_CONTRIBUTION", "REPEATED_CONTRIBUTION", "MISSING_CONTRIBUTION",
        })

    def test_participant_round_is_distinct_from_order_and_slot(self):
        read = {"allocation": "a", "unit": "byte", "range": [0, 4], "generation": 0,
                "order_id": "global-trace", "read_done": 5}
        write = {"allocation": "a", "unit": "byte", "range": [2, 6], "generation": 1,
                 "order_id": "global-trace", "write_at": 3}
        case = scoped_case("timing", timing__expected_participants=["g0:p1:round0"],
                           timing__observed_participants=["g0:p1:round1"],
                           timing__read=read, timing__later_write=write)
        self.assertEqual(set(diagnose(case)["supported_mechanisms"]),
                         {"COLLECTIVE_PARTICIPATION", "SHARED_SLOT_EARLY_REUSE"})
        write["range"] = [4, 6]
        self.assertEqual(check(diagnose(case), "SHARED_SLOT_EARLY_REUSE"), "EXCLUDED")
        write.update(range=[2, 6], order_id="another-clock")
        self.assertEqual(check(diagnose(case), "SHARED_SLOT_EARLY_REUSE"), "UNKNOWN")

    def test_next_observation_can_distinguish_across_routes(self):
        case = scoped_case("timing", "interface", interface__expected={"padding_idx": None})
        self.assertEqual(diagnose(case, "adaptive")["next_observation"]["field"], "interface.observed")
        self.assertEqual(diagnose(case, "fixed_route")["next_observation"]["field"], "timing.expected_participants")


if __name__ == "__main__":
    unittest.main()

