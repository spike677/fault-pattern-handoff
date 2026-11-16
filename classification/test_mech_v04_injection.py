"""Validate injection traces, state restoration and the nearest compliant cases."""

import unittest

from mech_v04 import injection


class InjectionPrototype(unittest.TestCase):
    def test_all_nine_targets_meet_the_three_checks_and_restore(self):
        self.assertEqual(len(injection.SCENARIOS), 9)
        for mode in injection.SCENARIOS:
            with self.subTest(mode=mode):
                result = injection.run(mode)
                self.assertTrue(result["passed"], result["checks"])
                self.assertEqual([call["fault_hit"] for call in result["calls"]], [False, True, False])
                self.assertEqual(len({call["call_id"] for call in result["calls"]}), 3)

    def test_equal_parameter_values_can_hide_the_wrong_source(self):
        observed = injection.proposal_sort([9, 7, 5], {"pre_nms_topn": 1, "post_nms_topn": 1}, True)
        self.assertEqual((observed.output, observed.mechanism), ([9], "post_nms_topn"))

    def test_padding_controls_keep_default_and_explicit_index_distinct(self):
        args = ([3, 5, 9], [0, 2])
        self.assertEqual(injection.embedding_bag(*args, None, False).output, 12)
        self.assertEqual(injection.embedding_bag(*args, 2, True).output, 3)
        self.assertFalse(injection.embedding_bag(*args, 2, True).hit)

    def test_contiguous_view_and_single_byte_types_are_address_controls(self):
        self.assertEqual(injection.write_view([1, 2, 3, 4], (2, 1), True).output, [1, 2, 3, 4])
        self.assertEqual(injection.load_packed(bytes.fromhex("ab cd"), 1, 1, True).output, 0xcd)
        with self.assertRaisesRegex(ValueError, "packed buffer"):
            injection.load_packed(b"\x00", 1, 2, False)

    def test_neutral_and_equal_payload_sources_are_separate_controls(self):
        neutral = injection.reduce_terms({"A": 3, "B": 5, "C": 0}, ("A", "B"), "C", "add", True)
        self.assertEqual(neutral.output, 8)
        distinct = injection.reduce_terms({"A": 3, "B": 4, "C": 4}, ("A", "B", "C"), "B", "add", False)
        self.assertEqual((distinct.output, distinct.trace["ledger"]), (11, {"A": 1, "B": 1, "C": 1}))

    def test_numeric_reference_controls_legal_rounding_and_well_conditioned_variance(self):
        reference = injection.accumulate([2048, 1, 1], False)
        faulty = injection.accumulate([2048, 1, 1], True)
        self.assertEqual(injection.f16(reference.output), 2050)
        self.assertEqual(faulty.trace["updates"][1], {"read": 2048, "term": 1, "sum": 2049, "stored": 2048})
        centered = injection.normalize([1, 2, 4], False).output
        raw = injection.normalize([1, 2, 4], True).output
        self.assertTrue(injection.same_output(raw, centered, 1e-4))


if __name__ == "__main__":
    unittest.main()
