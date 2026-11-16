"""Recompute the published static examples for the v0.4.1 candidate review."""

import json
import math
import struct


def require(condition, message):
    if not condition:
        raise ValueError(message)


def binary_float(format_code, value):
    try:
        return struct.unpack(format_code, struct.pack(format_code, float(value)))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def recompute_boundaries():
    values = (2048, 1, 1)
    state = 0
    for contribution in values:
        state = binary_float("<e", state + contribution)
    require(state == 2048 and sum(values) == 2050, "NUM-01 state rounding witness")
    require(binary_float("<e", 512) == 512 and math.isinf(binary_float("<e", 512**2)),
            "V406 overflow must occur after the representable local norm")

    row = (4095.5, 4096.5)
    mean = binary_float("<f", sum(row) / len(row))
    moment = binary_float("<f", sum(x * x for x in row) / len(row))
    raw = moment - mean * mean
    centered = binary_float("<f", sum((x - mean) ** 2 for x in row) / len(row))
    require(raw == 0 and centered == 0.25, "NUM-02 moment cancellation witness")

    produced = (0.2, 0.8)
    old_destination = (0.9, 0.1)
    intended_expert = max(range(2), key=produced.__getitem__)
    old_expert = max(range(2), key=old_destination.__getitem__)
    require((intended_expert, old_expert) == (1, 0), "CTRL-01 source identity witness")

    capacity, row_bytes = 6, 4
    initial_factor = capacity // row_bytes
    old_first_candidate = initial_factor - 1
    require(old_first_candidate == 0 and initial_factor == 1 and capacity - row_bytes > 0,
            "CTRL-02 first tested factor witness")

    group, first_s1, boundary, active_s1, span = 5, 1011, 1023, 1024, 64
    first_row = first_s1 * group
    expected_rows = max(0, min(first_row + span, active_s1 * group) - max(first_row, boundary * group))
    old_enters_tail = first_s1 + span // group > boundary
    require(expected_rows == 4 and not old_enters_tail, "ADDR-01 fused interval witness")

    stored = struct.pack("<f", 1.0)
    low_bf16 = int.from_bytes(stored[:2], "little")
    require(low_bf16 == 0 and struct.unpack("<f", stored)[0] == 1,
            "REP-01 same address read-width witness")

    completed_flag = 1
    old_publish, old_wait = completed_flag, completed_flag
    published_with_generation, wait_generation = completed_flag + 10, completed_flag + 11
    require(old_publish == old_wait and published_with_generation != wait_generation,
            "SYNC-01 stale flag witness")

    return {
        "half_running_sum": {"half_state": state, "wide_state": sum(values), "v406_square": "262144 -> +inf in FP16"},
        "raw_moment_cancellation": {"raw": raw, "centered": centered},
        "buffer_source_identity": {"intended_expert": intended_expert, "old_expert": old_expert},
        "plan_candidate_order": {"first_legal_factor": initial_factor, "first_old_factor": old_first_candidate},
        "fused_row_intersection": {"required_count": expected_rows, "old_count": 0},
        "scalar_representation": {"stored_float": 1.0, "decoded_bf16": low_bf16},
        "notification_generation": {"old_protocol_accepts_stale": True, "tagged_protocol_accepts_stale": False},
    }


if __name__ == "__main__":
    print(json.dumps(recompute_boundaries(), ensure_ascii=False, indent=2))
