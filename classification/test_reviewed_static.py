"""Exercise reviewed cross-file anchoring through the real classification graph."""

from copy import deepcopy
import unittest

from reliability_v04 import graph, reviewed_static


class ReviewedStaticTest(unittest.TestCase):
    def setUp(self):
        descriptions = {
            "contract": "Copy every logical value of a permitted strided source.",
            "entry": "copy_view(array);",
            "forwarding": "copy_buffer(array.ptr());",
            "implementation": "write(dst, get_storage_start(src), elements * item_size);",
            "consumer": "device_copy(dst, src, nbytes);",
        }
        sources = {
            key: {"id": key, "kind": "contract" if key == "contract" else "code",
                  "version": "revision-1", "path": f"{key}.cc", "text": value}
            for key, value in descriptions.items()
        }
        self.case = {"case_id": "view", "sources": list(sources.values())}
        self.extraction = {
            "case_id": "view", "operator": "copy view", "roles": [], "relations": [],
            "nodes": [{"id": "copy", "node_type": "unknown_action", "description": "copy",
                       "scope": {"source_id": "entry", "claim": "static"}, "source_location": None,
                       "expected_behavior": "", "observed_behavior": "", "violated_relation": "", "facts": []}],
        }
        self.review = {
            "case_id": "view", "version": "revision-1",
            "chain": {key: [{"source_id": key, "start_line": 1, "end_line": 1}] for key in descriptions},
            "source_digests": {key: graph.pilot.digest(src) for key, src in sources.items()},
            "facts": {key: "The reviewed old call forwards the actual view to the byte copy." for key in (
                "applicable_contract", "implementation_action", "causal_role", "supported_view",
                "no_correct_contiguous_conversion", "contiguous_formula",
            )},
            "statement": {"description": "dense copy from strided source",
                          "expected_behavior": "logical order", "observed_behavior": "storage order",
                          "violated_relation": "copy uses storage order for a legal strided view"},
        }

    def classify(self, extraction):
        result, = graph.classify_package({"cases": [self.case]}, {"cases": [extraction]})["cases"]
        node, = result["nodes"]
        return node["verdict"], result

    def test_reviewed_chain_binds_the_copy_without_editing_the_capture(self):
        previous = deepcopy(self.extraction)
        original, result = self.classify(previous)
        self.assertEqual((original["status"], result["independent_count"]), ("insufficient", 0))
        bound = reviewed_static.apply_review(self.case, self.extraction, "copy", self.review)
        self.assertEqual(self.extraction, previous)
        verdict, result = self.classify(bound)
        self.assertEqual((verdict["pattern_id"], result["independent_count"]), ("L1", 1))
        self.assertEqual(result["nodes"][0]["source_location"]["source_id"], "implementation")

    def test_missing_forwarding_span_cannot_be_promoted(self):
        self.review["chain"]["forwarding"] = []
        with self.assertRaisesRegex(ValueError, "every implementation step"):
            reviewed_static.apply_review(self.case, self.extraction, "copy", self.review)

    def test_matching_text_from_another_version_is_not_the_old_consumer(self):
        self.case["sources"][-1]["version"] = "revision-2"
        with self.assertRaisesRegex(ValueError, "consumer view is outside"):
            reviewed_static.apply_review(self.case, self.extraction, "copy", self.review)

    def test_a_new_contiguous_conversion_invalidates_the_review(self):
        self.case["sources"][2]["text"] = "copy_buffer(array.to_contiguous().ptr());"
        with self.assertRaisesRegex(ValueError, "forwarding view is outside"):
            reviewed_static.apply_review(self.case, self.extraction, "copy", self.review)


if __name__ == "__main__":
    unittest.main()
