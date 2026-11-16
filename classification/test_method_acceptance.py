"""Deterministic method checks kept separate from real-material scores."""

import json
from pathlib import Path
import unittest

from classify import FACT_PROTOCOL, classify


CATALOG = json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8"))


def anchor(source, use):
    return {"source_id": source["id"], "start_line": 1, "end_line": 1,
            "quote": source["text"], "use": use}


def decide(keys, scope, sources, anchors, state="derived"):
    case = {"case_id": "synthetic-method-check", "sources": sources}
    action = {
        "id": "operation", "role": "primary", "scope": scope,
        "facts": [{"key": key, "value": True, "claim_state": state,
                   "explanation": f"Synthetic boundary check for {key}.",
                   "anchors": anchors} for key in keys],
    }
    packet = {"case_id": case["case_id"], "fact_protocol": FACT_PROTOCOL, "actions": [action]}
    decision, = classify(case, packet, CATALOG)["actions"]
    return decision


def static_decision(keys, contract, behavior):
    specification = {"id": "requirement", "kind": "contract", "version": "old", "path": "spec",
                     "text": contract}
    old_code = {"id": "body", "kind": "code", "version": "old", "path": "kernel",
                "text": behavior}
    scope = {"version": "old", "path": "kernel", "claim": "static"}
    return decide(keys, scope, [specification, old_code],
                  [anchor(specification, "requirement"), anchor(old_code, "behavior")])


class MethodAcceptance(unittest.TestCase):
    def test_optional_member_and_preserved_contribution_exclude_c2(self):
        for exclusion, contract, behavior in (
            ("omission_permitted", "Only unmasked terms participate.",
             "The masked operand is skipped as required."),
            ("contribution_preserved", "The contribution from x must appear once.",
             "The separate boundary path already adds x exactly once."),
        ):
            with self.subTest(exclusion=exclusion):
                result = static_decision(
                    ("applicable_contract", exclusion, "compliant"), contract, behavior,
                )
                self.assertEqual((result["status"], result["outside_reason"]), ("outside", "compliant"))
                self.assertFalse(result["count_as_independent"])
                self.assertNotEqual(result.get("pattern_id"), "C2")

    def test_disjoint_partials_are_a_legal_layered_reduction(self):
        result = static_decision(
            ("applicable_contract", "expected_multiplicity_met", "compliant"),
            "Original slots 0 and 1 each contribute once to the final sum.",
            "p0 contains slot 0 alone. p1 contains slot 1 alone. The merge adds p0 and p1 once.",
        )
        self.assertEqual((result["status"], result["outside_reason"]), ("outside", "compliant"))
        self.assertFalse(result["count_as_independent"])

    def test_one_replacement_retains_both_membership_attributes(self):
        keys = tuple(sorted(set(CATALOG["modes"]["C1"]["necessary"])
                            | set(CATALOG["modes"]["C2"]["necessary"]))) + (
            "distinct_members_for_replacement", "implementation_action", "causal_role",
        )
        result = static_decision(
            keys, "The window must consume the active source slot, and never the padding slot.",
            "The selector replaces the active slot with non-neutral padding and the reducer consumes it.",
        )
        self.assertEqual(result["supported_pattern_ids"], ["C1", "C2"])
        self.assertEqual(result["role"], "primary")
        self.assertTrue(result["count_as_independent"])

    def test_runtime_evidence_binds_both_build_and_call(self):
        runtime = {"id": "trace", "version": "old", "path": "kernel", "kind": "runtime",
                   "build": "build-1", "call_id": "call-1",
                   "text": "Bound trace: required slot x arrived twice instead of its required single contribution."}
        scope = {key: runtime[key] for key in ("version", "path", "build", "call_id")}
        scope["claim"] = "runtime"
        keys = (*CATALOG["modes"]["C3"]["necessary"], "implementation_action", "causal_role")
        matching = decide(keys, scope, [runtime], [anchor(runtime, "runtime")], "verified_runtime")
        self.assertEqual(matching["pattern_id"], "C3")
        for field in ("build", "call_id"):
            with self.subTest(field=field):
                mismatched = decide(keys, {**scope, field: "different"}, [runtime],
                                    [anchor(runtime, "runtime")], "verified_runtime")
                self.assertEqual(mismatched["status"], "insufficient")
                self.assertFalse(mismatched["count_as_independent"])
                self.assertTrue(any(issue["code"] == "runtime_binding_mismatch"
                                    for issue in mismatched["issues"]))


if __name__ == "__main__":
    unittest.main()
