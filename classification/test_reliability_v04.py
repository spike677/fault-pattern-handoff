"""Check the independence, mechanism and source boundaries of action-graph evaluation."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from reliability_v04 import graph, reader, scoring, workflow


CASE = {"case_id": "fixture", "sources": [
    {"id": "fixed", "path": "author/issues/3", "version": "confirmed-v1", "kind": "report",
     "text": "The valid input term is mandatory. Explicit -1 excludes the padding row.\n"
             "The parser treats the explicit -1 as omitted, admitting the padding row.\n"
             "The reduction really sums the ineligible term after the parser changed its membership.\n"
             "Separately, a different branch corrupts a saved index independently of padding.\n"
             "The consumer reads the saved mask in the listed reduction.", "original_start_line": 20},
    {"id": "patch", "path": "repair.diff", "version": "fixed-v2", "kind": "diff",
     "text": "+ if required: sum(term)"},
    {"id": "old", "path": "parser.py", "version": "frozen-v0", "kind": "code",
     "text": "parse_padding_as_omitted(-1)"},
]}


def anchor(line, use="confirmation", source="fixed"):
    return {"source_id": source, "start_line": line, "end_line": line, "use": use}


def node(action_id, node_type, line, keys):
    location = anchor(line)
    location.pop("use")
    return {
        "id": action_id, "node_type": node_type, "description": action_id,
        "scope": {"source_id": "fixed", "claim": "reported", "build": None, "call_id": None},
        "source_location": location, "expected_behavior": "respect the specified membership",
        "observed_behavior": f"observed action on line {line}", "violated_relation": "membership was changed",
        "facts": [{"key": key, "value": True, "claim_state": "confirmed_report",
                   "explanation": "This author identifies the applicable behavior and cause.",
                   "anchors": [anchor(line)]} for key in keys],
    }


def edge(kind, left, right, *lines, state="confirmed_report"):
    return {"kind": kind, "from": left, "to": right, "evidence_level": state,
            "evidence_refs": [anchor(line) for line in lines],
            "explanation": "The source identifies both affected operations in their stated paths."}


PROOF = ("applicable_contract", "implementation_action", "causal_role")


def run(*nodes, edges=()):
    extracted = {"case_id": "fixture", "operator": "test", "roles": [], "readback": "",
                 "nodes": list(nodes), "relations": list(edges)}
    return graph.classify_package({"cases": [CASE]}, {"cases": [extracted]})["cases"][0]


class ReliabilityGraph(unittest.TestCase):
    def test_root_and_downstream_modes_do_not_double_count_a_consumer(self):
        root = node("sentinel", "root_action", 2, (*PROOF, "correct_source", "special_state", "wrong_state_treatment"))
        effect = node("term", "downstream_effect", 3, ("applicable_contract", "ineligible_member", "actual_contribution"))
        consumer = node("normal-read", "supporting_operation", 5, ())
        result = run(root, effect, consumer, edges=(
            edge("causes", "sentinel", "term", 2, 3), edge("consumes", "normal-read", "sentinel", 5, state="observation"),
        ))
        parent, child, normal = result["nodes"]
        self.assertEqual((parent["mode_ids"], parent["effect_mode_ids"], parent["independent_count"]),
                         (["P2"], ["C1"], 1))
        self.assertEqual((child["causal_role"], child["upstream_ids"], child["independent_count"]),
                         ("downstream", ["sentinel"], 0))
        self.assertEqual((normal["causal_role"], normal["verdict"], normal["independent_count"]), ("support", None, 0))
        self.assertTrue(all(item["supported"] for item in result["relations"]))

    def test_two_evidenced_actions_keep_both_roots_without_forced_primary(self):
        first = node("capacity", "root_action", 2, (*PROOF, "established_other_defect"))
        second = node("workspace-step", "independent_action", 4, (*PROOF, "established_other_defect"))
        result = run(first, second, edges=(edge("independent_of", "capacity", "workspace-step", 2, 4),))
        self.assertEqual(result["independent_count"], 2)
        self.assertEqual([item["causal_role"] for item in result["nodes"]], ["independent", "independent"])
        self.assertTrue(all(item["verdict"]["outside_reason"] == "outside_catalog" for item in result["nodes"]))

    def test_independence_hypothesis_cannot_remove_the_uncertainty(self):
        first = node("first", "root_action", 2, (*PROOF, "established_other_defect"))
        second = node("second", "independent_action", 4, (*PROOF, "established_other_defect"))
        result = run(first, second, edges=(edge("independent_of", "first", "second", 2, 4, state="hypothesis"),))
        self.assertEqual(result["independent_count"], 0)
        self.assertTrue(all(item["action_proven"] and item["causal_role"] == "unknown" for item in result["nodes"]))

    def test_repeated_action_id_labels_cannot_double_count_the_same_implementation(self):
        first = node("first", "root_action", 2, (*PROOF, "established_other_defect"))
        repeated = {**deepcopy(first), "id": "duplicate", "node_type": "independent_action"}
        result = run(first, repeated, edges=(edge("independent_of", "first", "duplicate", 2),))
        self.assertEqual(result["independent_count"], 1)
        self.assertEqual(result["nodes"][1]["duplicate_of"], "first")
        self.assertFalse(result["relations"][0]["supported"])

    def test_known_action_survives_an_unresolved_leaf(self):
        result = run(node("first", "root_action", 2, PROOF))
        detail, = result["nodes"]
        self.assertEqual((detail["verdict"]["status"], detail["causal_role"], result["independent_count"]),
                         ("insufficient", "primary", 1))

    def test_patch_additions_cannot_prove_old_action_or_fill_missing_c2_consumer(self):
        candidate = node("possible-omission", "unknown_action", 2, (*PROOF, "required_member", "omitted_contribution"))
        candidate["facts"][-1]["anchors"] = [anchor(1, "behavior", "patch")]
        result = run(candidate)
        item, = result["nodes"]
        self.assertEqual(item["verdict"]["status"], "insufficient")
        self.assertEqual(item["mode_ids"], [])
        self.assertEqual(result["independent_count"], 0)

    def test_schema_reuses_card_facts_and_replaces_model_roles_with_graph_nodes(self):
        shape = reader.schema()
        case = shape["properties"]["cases"]["items"]["properties"]
        self.assertEqual(set(case) & {"nodes", "relations", "actions", "supporting_operations"}, {"nodes", "relations"})
        self.assertIn("causal_role", shape["$defs"]["fact"]["properties"]["key"]["enum"])

    def test_correct_action_does_not_turn_a_label_error_into_a_strict_pass(self):
        first = node("match", "root_action", 2, PROOF)
        actual = run(first)
        reference = {"case_id": "fixture", "actions": [
            {"id": "ref", "specific_action": "observed on line 2", "role": "primary",
             "allowed": [{"status": "leaf", "pattern_id": "P2"}]},
        ]}
        vote = {"case_id": "fixture", "actions": [
            {"action_id": "match", "expected_id": "ref", "failure_cause": "rule_execution", "rationale": "missing mode",
             **{field: True for field in scoring.ASSESSMENTS}},
        ], "omissions": []}
        score = scoring.grade_round({"cases": [reference]}, {"cases": [actual]}, {"cases": [vote]})["metrics"]
        self.assertEqual(score["concrete_action"], {"correct": 1, "eligible": 1})
        self.assertEqual(score["supported_mode"], {"correct": 0, "eligible": 1})
        self.assertEqual(score["independent_roots"]["correct"], 1)
        self.assertEqual(score["strict_cases"]["correct"], 0)

    def test_judge_cannot_hide_an_unmatched_root_by_omitting_a_review_row(self):
        predicted = run(node("unexpected", "root_action", 4, (*PROOF, "established_other_defect")))
        reference = {"case_id": "fixture", "actions": [
            {"id": "ref", "specific_action": "observed on line 2", "role": "primary",
             "allowed": [{"status": "leaf", "pattern_id": "P2"}]},
        ]}
        missing = {"expected_id": "ref", "failure_cause": "material_understanding", "rationale": "different action"}
        with self.assertRaisesRegex(ValueError, "each predicted action once"):
            scoring.grade_case(reference, predicted, {"actions": [], "omissions": [missing]})
        row = {"action_id": "unexpected", "expected_id": None, "failure_cause": "material_understanding",
               "rationale": "different action"}
        score = scoring.summarize([scoring.grade_case(reference, predicted, {"actions": [row], "omissions": [missing]})])
        self.assertEqual(score["independent_roots"], {"correct": 0, "eligible": 1, "claimed": 1,
                                                       "false_positive": 1, "false_negative": 1})
        self.assertEqual(score["wrong_positive"], 1)

    def test_freeze_binds_original_a_prompt_and_schema(self):
        source = deepcopy(CASE)
        for entry in source["sources"]:
            entry["origin"] = "https://example.invalid/" + entry["id"]
            entry.setdefault("original_start_line", 1)
        with TemporaryDirectory() as directory:
            source_path = Path(directory) / "original.json"
            run_path = Path(directory) / "run"
            workflow.common.write_record(source_path, {"cases": [source]})
            workflow.freeze(source_path, run_path)
            freeze, _, payload = workflow.frozen(run_path)
            self.assertIn("confirmed-v1", payload)
            self.assertEqual(workflow.common.digest(source_path), freeze["a_sha256"])
            (run_path / "A.json").write_bytes(source_path.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "freeze differs"):
                workflow.frozen(run_path)

    def test_old_code_location_is_context_when_report_independently_proves_action(self):
        action = node("known", "root_action", 2, (*PROOF, "established_other_defect"))
        action["source_location"] = {"source_id": "old", "start_line": 1, "end_line": 1}
        result = run(action)
        detail, = result["nodes"]
        self.assertEqual((detail["source_location"]["source_id"], detail["context_source_location"]["source_id"]),
                         ("fixed", "old"))
        self.assertEqual(result["independent_count"], 1)
        action["facts"][1]["anchors"] = [anchor(1, "behavior", "old")]
        self.assertEqual(run(action)["independent_count"], 0)

    def test_a_unique_c3_effect_can_classify_its_same_scope_cause_once(self):
        retain = node("retain", "root_action", 2, ("implementation_action", "causal_role"))
        overlap = node("overlap", "downstream_effect", 3, (
            "applicable_contract", "original_contribution_identity", "expected_multiplicity", "excess_multiplicity",
        ))
        cause = edge("causes", "retain", "overlap", 2, 3)
        result = run(retain, overlap, edges=(cause,))
        root, effect = result["nodes"]
        self.assertEqual((root["direct_verdict"]["status"], root["verdict"]["pattern_id"], root["mechanism_via"]),
                         ("insufficient", "C3", "overlap"))
        self.assertEqual((result["independent_count"], effect["independent_count"], effect["attributed_to"]),
                         (1, 0, "retain"))
        self.assertEqual(list(scoring.predicted_actions(result)), ["retain"])
        waiting = run(retain, overlap, edges=({**cause, "evidence_level": "hypothesis"},))
        self.assertEqual((waiting["nodes"][0]["verdict"]["status"], waiting["independent_count"]), ("insufficient", 0))

    def test_contract_relation_conserves_the_root_count(self):
        action = node("known", "root_action", 2, (*PROOF, "established_other_defect"))
        result = run(action, edges=(edge("violates", "known", "contract", 2),))
        self.assertTrue(result["relations"][0]["supported"])
        self.assertEqual(result["independent_count"], 1)

    def test_a_downstream_mode_attaches_to_only_its_own_independent_root(self):
        first = node("first", "root_action", 2, (*PROOF, "established_other_defect"))
        second = node("second", "independent_action", 4, (*PROOF, "established_other_defect"))
        effect = node("effect", "downstream_effect", 3, ("applicable_contract", "ineligible_member", "actual_contribution"))
        result = run(first, second, effect, edges=(
            edge("independent_of", "first", "second", 2, 4), edge("causes", "second", "effect", 3, 4),
        ))
        self.assertEqual(result["independent_count"], 2)
        self.assertEqual([item["effect_mode_ids"] for item in result["nodes"][:2]], [[], ["C1"]])
