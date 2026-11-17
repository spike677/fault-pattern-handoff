"""Meaningful boundary regressions for catalogue extension and preserved evidence discipline."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from mech_v05 import engine, reader, retrieval
from mech_v05.cli import main as cli
from reliability_v04 import graph
from test_reliability_v04 import CASE, node, edge, PROOF

REPORT = {
    "id": "report", "kind": "report", "path": "public/reports/offset", "version": "report-snapshot-1",
    "text": "Legal coordinates must preserve an exact integer element offset.\n"
            "The old signed 32-bit product overflows before pointer formation, which reads the wrong element.\n"
            "Using a 64-bit product before that first loss preserves the same units and geometry.\n"
            "The old integer type is the sole defective operation; normal pointer use only propagates it.\n"
            "A separate independent output copies 32 bytes into a 4-byte object from the correct start.\n"
            "No numerical computation consumes the otherwise invalid integer on the disabled path.\n"
            "The buffer is completely overwritten before any read; the removed initial fill was redundant.\n"
            "Later source disagrees with the original integer overflow account."
}


def ref(line, use="confirmation", source="report"):
    return {"source_id": source, "start_line": line, "end_line": line, "use": use}


def fact(key, line=2, value=True, state="confirmed_report"):
    return {"key": key, "value": value, "claim_state": state,
            "explanation": "The selected original report explicitly establishes this scoped relationship.",
            "anchors": [ref(line)]}


def address_node():
    keys = engine.load_catalog()["modes"]["ADR-INT-01"]["necessary"]
    return {"id": "integer", "node_type": "root_action", "description": "32-bit product first loses exact offset",
            "scope": {"source_id": "report", "claim": "reported", "build": None, "call_id": None},
            "source_location": {"source_id": "report", "start_line": 2, "end_line": 2},
            "expected_behavior": "preserve legal exact integer position", "observed_behavior": "overflowed product reaches pointer",
            "violated_relation": "integer range fails before address consumer", "facts": [fact(k) for k in [*keys, "causal_role"]]}


def run_nodes(nodes, relations=None, sources=None):
    case = {"case_id": "integer-example", "sources": sources or [REPORT]}
    extracted = {"case_id": case["case_id"], "operator": "GridLike", "roles": [], "readback": "Bounded report review",
                 "nodes": nodes, "relations": relations or []}
    material, readback = {"cases": [case]}, {"cases": [extracted]}
    return engine.classify_package(material, readback)["cases"][0], material, readback


class V05KnowledgeBoundaries(unittest.TestCase):
    def test_proven_plan_omission_and_its_c2_relation_are_one_supported_action(self):
        n = address_node()
        keys = engine.load_catalog()["modes"]["PLAN-SPLIT-01"]["necessary"]
        n["facts"] = [fact(k) for k in [*keys, "required_member", "omitted_contribution", "causal_role"]]
        report = {**REPORT, "text": "All current-token KV chunks must be written once.\n"
                  "The writer lost its stride loop but launches at most 512 threads: required chunks beyond 512 are omitted.\n"
                  "The later attention path reads the stale cache, not the required current-token contributions."}
        result, _, _ = run_nodes([n], sources=[report])
        self.assertEqual(result["nodes"][0]["mode_ids"], ["PLAN-SPLIT-01"])
        self.assertEqual(result["nodes"][0]["verdict"]["co_supported_mode_ids"], ["C2"])
        self.assertEqual(result["independent_count"], 1)

    def test_same_wrong_width_field_keeps_specific_p1_and_domain_description(self):
        n = address_node()
        keys = engine.load_catalog()["modes"]["VALID-DOMAIN-01"]["necessary"]
        n["facts"] = [fact(k) for k in [*keys, "expected_source", "actual_source", "non_equivalent_source", "causal_role"]]
        report = {**REPORT, "text": "TMA requires physical byte-stride alignment.\n"
                  "The old validation reads the logical 4-bit dtype field instead of 8-bit storage width, rejecting a valid physical stride.\n"
                  "These are two descriptions of the same wrong validation operand."}
        result, _, _ = run_nodes([n], sources=[report])
        self.assertEqual(result["nodes"][0]["mode_ids"], ["P1"])
        self.assertEqual(result["nodes"][0]["verdict"]["co_supported_mode_ids"], ["VALID-DOMAIN-01"])
        self.assertEqual(result["independent_count"], 1)

    def test_allowed_mode_pair_does_not_merge_different_evidence(self):
        n = address_node()
        keys = engine.load_catalog()["modes"]["PLAN-SPLIT-01"]["necessary"]
        n["facts"] = [fact(k) for k in keys]
        n["facts"].extend([fact("required_member", 5), fact("omitted_contribution", 5)])
        result, _, _ = run_nodes([n])
        self.assertEqual(result["nodes"][0]["verdict"]["status"], "insufficient")

    def test_original_file_line_numbers_are_reported_not_silently_translated(self):
        n = address_node()
        result, material, readback = run_nodes([n])
        self.assertEqual(reader.validate_readback(material, readback), [])
        material["cases"][0]["sources"][0]["original_start_line"] = 499
        n = readback["cases"][0]["nodes"][0]
        n["facts"][0]["anchors"][0].update(start_line=500, end_line=500)
        errors = reader.validate_readback(material, readback)
        self.assertEqual(errors[0]["issue"], "original_file_coordinates_instead_of_excerpt")
        self.assertEqual(n["facts"][0]["anchors"][0]["start_line"], 500)

    def test_integer_consumer_positive_and_widen_after_loss_negative(self):
        n = address_node()
        result, _, _ = run_nodes([n])
        self.assertEqual((result["nodes"][0]["mode_ids"], result["independent_count"]), (["ADR-INT-01"], 1))
        n["facts"] = [f for f in n["facts"] if f["key"] != "same_mapping_preserved_by_widening"]
        result, _, _ = run_nodes([n])
        self.assertEqual(result["nodes"][0]["verdict"]["status"], "insufficient")
        self.assertIn("same_mapping_preserved_by_widening", result["nodes"][0]["verdict"]["knowledge_neighbors"]["ADR-INT-01"]["missing"])

    def test_unused_loss_cannot_establish_address_fault(self):
        n = address_node()
        n["facts"] = [f for f in n["facts"] if f["key"] != "distorted_address_consumed"]
        n["facts"].append(fact("damaged_address_not_consumed", 6))
        result, _, _ = run_nodes([n])
        self.assertEqual(result["nodes"][0]["mode_ids"], [])

    def test_hypothesis_and_observation_do_not_prove_new_leaves_or_roots(self):
        for state in ("observation", "hypothesis"):
            n = address_node()
            for f in n["facts"]:
                f["claim_state"] = state
            result, _, _ = run_nodes([n])
            self.assertEqual((result["nodes"][0]["verdict"]["status"], result["independent_count"]), ("insufficient", 0))

    def test_foreign_only_proof_is_rejected_but_valid_confirmation_survives_context(self):
        n = address_node()
        foreign = {**REPORT, "id": "later", "version": "report-snapshot-2"}
        for f in n["facts"]:
            f["anchors"].append(ref(8, "context", "later"))
        result, _, _ = run_nodes([n], sources=[REPORT, foreign])
        self.assertEqual(result["nodes"][0]["mode_ids"], ["ADR-INT-01"])
        for f in n["facts"]:
            f["anchors"] = [ref(8, "confirmation", "later")]
        result, _, _ = run_nodes([n], sources=[REPORT, foreign])
        self.assertEqual(result["nodes"][0]["verdict"]["status"], "insufficient")

    def test_disputed_integer_range_is_not_selected_by_candidate_rank(self):
        n = address_node()
        n["facts"].append(fact("integer_range_loss", 8, False))
        result, _, _ = run_nodes([n])
        self.assertEqual(result["nodes"][0]["verdict"]["status"], "insufficient")
        self.assertIn("integer_range_loss", result["nodes"][0]["verdict"]["conflicts"])

    def test_correct_full_write_refutes_missing_initialization(self):
        n = address_node()
        n["facts"] = [fact(k, 7) for k in engine.load_catalog()["modes"]["BUF-INIT-01"]["necessary"]]
        n["facts"].extend([fact("all_slots_written_before_read", 7), fact("compliant", 7)])
        result, _, _ = run_nodes([n])
        self.assertNotEqual(result["nodes"][0]["verdict"].get("pattern_id"), "BUF-INIT-01")

    def test_research_float_roundtrip_cannot_be_promoted_by_its_predicates(self):
        n = address_node()
        n["facts"] = [fact(k) for k in engine.load_catalog()["modes"]["ADR-FLOAT-01"]["necessary"]]
        result, _, _ = run_nodes([n])
        self.assertEqual(result["nodes"][0]["mode_ids"], [])

    def test_same_action_alias_still_counts_once_with_new_leaf(self):
        first = address_node()
        alias = {**deepcopy(first), "id": "alias", "node_type": "independent_action"}
        relationship = {"kind": "independent_of", "from": "integer", "to": "alias",
                        "evidence_level": "confirmed_report", "evidence_refs": [ref(2)], "explanation": "Claimed independence"}
        result, _, _ = run_nodes([first, alias], [relationship])
        self.assertEqual(result["independent_count"], 1)
        self.assertEqual(result["nodes"][1]["duplicate_of"], "integer")
        self.assertFalse(result["relations"][0]["supported"])

    def test_new_parent_requires_its_own_evidence(self):
        n = address_node()
        n["facts"] = [fact(k) for k in ("applicable_contract", "implementation_action", "buffer_contract_violation")]
        result, _, _ = run_nodes([n])
        self.assertEqual(result["nodes"][0]["verdict"].get("parent_id"), "buffer")
        n["facts"].pop()
        result, _, _ = run_nodes([n])
        self.assertEqual(result["nodes"][0]["verdict"]["status"], "insufficient")

    def test_inherited_graph_semantics_identical_without_extension_facts(self):
        n = node("sentinel", "root_action", 2, (*PROOF, "correct_source", "special_state", "wrong_state_treatment"))
        package = {"cases": [CASE]}
        extraction = {"cases": [{"case_id": CASE["case_id"], "operator": "test", "roles": [], "readback": "",
                                  "nodes": [n], "relations": []}]}
        self.assertEqual(engine.classify_package(package, extraction)["cases"], graph.classify_package(package, extraction)["cases"])

    def test_retrieval_historical_and_external_hits_are_candidates_only(self):
        catalog = engine.load_catalog()
        for kind, query in (("historical_source", "FM-16 整数地址位宽"), ("external_knowledge", "同步 屏障 pipe sync")):
            hits = retrieval.search(query, catalog, 4, kind)
            self.assertTrue(hits)
            self.assertTrue(all(h["use"] == "candidate_only_not_evidence_or_classification" for h in hits))
        before = engine.pilot.digest(catalog)
        retrieval.search("CLR arbitrary text", catalog)
        self.assertEqual(engine.pilot.digest(catalog), before)

    def test_request_includes_neutral_scope_and_keeps_graph_structure(self):
        _, material, _ = run_nodes([address_node()])
        material["cases"][0]["review_scope"] = "Only signed integer address formation before access."
        rendered = reader.render(material)
        self.assertIn(material["cases"][0]["review_scope"], rendered)
        self.assertIn("integer_range_loss", reader.schema()["$defs"]["fact"]["properties"]["key"]["enum"])

    def test_case_archive_reproduces_and_rejects_tampering(self):
        _, material, extraction = run_nodes([address_node()])
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, value in (("material.json", material), ("readback.json", extraction)):
                (root / name).write_text(json.dumps(value), encoding="utf-8")
            result = root / "result.json"
            cli(["classify", str(root / "material.json"), str(root / "readback.json"), str(result)])
            archive_args = ["archive", str(root / "material.json"), str(root / "readback.json"), str(result), str(root / "archive")]
            cli(archive_args)
            cli(archive_args)
            stored = next((root / "archive").glob("*/result.json"))
            old_payload = stored.read_bytes()
            stored.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "archive integrity"):
                cli(archive_args)
            stored.write_bytes(old_payload)
            tampered = json.loads(result.read_bytes())
            tampered["cases"][0]["independent_count"] = 5
            result.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not reproduce"):
                cli(archive_args)

    def test_inherited_definition_change_and_parent_cycle_fail_validation(self):
        catalog = engine.load_catalog()
        catalog["modes"]["L2"]["definition"] = "all address mistakes"
        with self.assertRaisesRegex(ValueError, "Inherited"):
            engine.validate_catalog(catalog)
        catalog = engine.load_catalog()
        catalog["parent_hierarchy"]["address"] = "address"
        with self.assertRaisesRegex(ValueError, "Cyclic"):
            engine.validate_catalog(catalog)


if __name__ == "__main__":
    unittest.main()
