"""Scoped proof survives foreign context without accepting a foreign-only proof."""

from copy import deepcopy
import unittest

from mech_v04 import classifier


def anchor(source, use):
    return {"source_id": source["id"], "start_line": 1, "end_line": 1,
            "quote": source["text"], "use": use}


def fixture(claim, sources, anchors):
    primary = sources[0]
    case = {"case_id": "overlap-add", "sources": sources}
    keys = ("applicable_contract", "original_contribution_identity", "expected_multiplicity",
            "excess_multiplicity", "implementation_action", "causal_role")
    state = "confirmed_report" if claim == "reported" else "derived"
    packet = {"case_id": case["case_id"], "fact_protocol": classifier.pilot.FACT_PROTOCOL,
              "actions": [{
                  "id": "tail-add", "role": "primary",
                  "scope": {"version": primary["version"], "path": primary["path"], "claim": claim},
                  "facts": [{"key": key, "value": True, "claim_state": state,
                             "anchors": deepcopy(anchors),
                             "explanation": "The same bias reaches this output once in each partial."}
                            for key in keys],
              }]}
    return {"cases": [case]}, packet


class CrossVersionEvidence(unittest.TestCase):
    report = {"id": "author", "version": "triage-2", "path": "issue/8", "kind": "report",
              "text": "The output requires one bias. We merged two already biased partials."}
    code = {"id": "old", "version": "build-19", "path": "overlap.py", "kind": "code",
            "text": "return prior_with_bias + current_with_bias"}
    contract = {"id": "contract", "version": "build-19", "path": "contract.md", "kind": "contract",
                "text": "Each output element receives its layer bias once."}

    def decide(self, material, packet):
        return classifier.classify_package(material, [packet])[0]

    def test_author_confirmation_survives_a_valid_foreign_code_anchor(self):
        matched = anchor(self.report, "confirmation")
        material, packet = fixture("reported", [self.report, self.code],
                                   [matched, anchor(self.code, "behavior")])
        before = deepcopy(packet)
        result = self.decide(material, packet)
        action, = result["actions"]
        self.assertEqual((action["pattern_id"], action["role"], action["count_as_independent"]),
                         ("C3", "primary", True))
        self.assertEqual(action["cross_version_context"][0]["version"], "build-19")
        self.assertEqual(action["facts"][0]["anchors"], [matched])
        self.assertNotIn("source_version_mismatch", {item["code"] for item in action["issues"]})
        self.assertEqual(result["facts_sha256"], classifier.pilot.digest(before))
        self.assertEqual(packet, before)

    def test_static_proof_keeps_both_scoped_requirements_and_behavior(self):
        material, packet = fixture("static", [self.code, self.contract, self.report],
                                   [anchor(self.contract, "requirement"),
                                    anchor(self.code, "behavior"), anchor(self.report, "requirement")])
        action, = self.decide(material, packet)["actions"]
        self.assertEqual(action["pattern_id"], "C3")
        self.assertEqual(action["cross_version_context"][0]["anchor"]["source_id"], "author")
        for fact in packet["actions"][0]["facts"]:
            fact["anchors"] = [item for item in fact["anchors"] if item["source_id"] != "contract"]
        action, = self.decide(material, packet)["actions"]
        self.assertEqual((action["status"], action["role"]), ("insufficient", "unknown"))
        self.assertNotIn("cross_version_context", action)

    def test_foreign_report_cannot_supply_the_author_confirmation(self):
        other = {**self.report, "id": "other", "version": "later-snapshot"}
        material, packet = fixture("reported", [self.report, self.code, other],
                                   [anchor(self.report, "context"), anchor(other, "confirmation")])
        action, = self.decide(material, packet)["actions"]
        self.assertEqual(action["status"], "insufficient")
        self.assertNotIn("cross_version_context", action)

    def test_invalid_foreign_quote_is_not_discarded_as_valid_context(self):
        bad = {**anchor(self.code, "behavior"), "quote": "fabricated line"}
        material, packet = fixture("reported", [self.report, self.code],
                                   [anchor(self.report, "confirmation"), bad])
        action, = self.decide(material, packet)["actions"]
        self.assertEqual(action["status"], "insufficient")
        self.assertNotIn("cross_version_context", action)

    def test_observations_and_hypotheses_never_supply_the_missing_proof(self):
        for claim in ("observation", "hypothesis"):
            with self.subTest(claim=claim):
                material, packet = fixture("reported", [self.report, self.code],
                                           [anchor(self.report, "confirmation"), anchor(self.code, "behavior")])
                for fact in packet["actions"][0]["facts"]:
                    fact["claim_state"] = claim
                action, = self.decide(material, packet)["actions"]
                self.assertEqual((action["status"], action["count_as_independent"]), ("insufficient", False))


if __name__ == "__main__":
    unittest.main()
