"""Run the MECH-v0.4 fault-injection specification on isolated CPU inputs."""

import argparse
from collections import Counter
from dataclasses import dataclass
import json
import math
import struct
from typing import Callable


@dataclass(frozen=True)
class Observation:
    output: object
    mechanism: object
    trace: dict
    hit: bool


def proposal_sort(scores, limits, fault):
    key = "post_nms_topn" if fault else "pre_nms_topn"
    limit = limits[key]
    return Observation(sorted(scores, reverse=True)[:limit], key, {"limit": limit}, fault)


def embedding_bag(table, indices, padding_idx, fault):
    hit = fault and padding_idx == -1
    effective = None if padding_idx is None or hit else padding_idx % len(table)
    contributions = [index for index in indices if index != effective]
    return Observation(sum(table[index] for index in contributions), effective,
                       {"raw_padding_idx": padding_idx, "contributions": contributions}, hit)


def write_view(values, strides, fault):
    applied = (2, 1) if fault else strides
    coordinates = [(row, col) for row in range(2) for col in range(2)]
    # Guard cells permit a direct check of the prototype's write footprint.
    guard = -999
    buffer = [guard, 0, 0, 0, 0, guard]
    offsets = [row * applied[0] + col * applied[1] for row, col in coordinates]
    for offset, value in zip(offsets, values, strict=True):
        if not 0 <= offset < 4:
            raise ValueError("Write exceeds the four-element view")
        buffer[1 + offset] = value
    output = [buffer[1 + row * strides[0] + col * strides[1]] for row, col in coordinates]
    return Observation(output, offsets[1], {"element_offsets": offsets, "strides": list(strides),
                                            "guards_intact": buffer[0] == buffer[-1] == guard}, fault)


def load_packed(storage, element_index, width, fault):
    offset = element_index if fault else element_index * width
    if not 0 <= offset <= len(storage) - width:
        raise ValueError("Read exceeds the packed buffer")
    value = int.from_bytes(storage[offset:offset + width], "little")
    return Observation(value, offset, {"element_index": element_index, "bytes_per_element": width}, fault)


def reduce_terms(terms, eligible, focus, change, fault):
    execution = list(eligible)
    if fault:
        if change == "omit":
            execution.remove(focus)
        else:
            execution.append(focus)
    ledger = Counter(execution)
    return Observation(sum(terms[source] for source in execution), ledger[focus],
                       {"eligible": list(eligible), "ledger": dict(ledger), "operations": execution}, fault)


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def f16(value):
    return struct.unpack("<e", struct.pack("<e", value))[0]


def accumulate(terms, fault):
    store = f16 if fault else f32
    state, updates = 0.0, []
    for term in terms:
        rounded_sum = f32(state + term)
        stored = store(rounded_sum)
        updates.append({"read": state, "term": term, "sum": rounded_sum, "stored": stored})
        state = stored
    return Observation(state, [row["stored"] for row in updates],
                       {"updates": updates, "state_precision": "fp16" if fault else "fp32"}, fault)


def normalize(row, fault):
    mean = f32(sum(row) / len(row))
    centered = [f32(value - mean) for value in row]
    if fault:
        moment = f32(sum(f32(value * value) for value in row) / len(row))
        variance = f32(moment - f32(mean * mean))
    else:
        variance = f32(sum(f32(value * value) for value in centered) / len(row))
    scale = f32(1 / math.sqrt(f32(variance + f32(1e-5))))
    return Observation([f32(value * scale) for value in centered], variance,
                       {"mean": mean, "variance": variance, "scale": scale}, fault)


@dataclass(frozen=True)
class Scenario:
    target: str
    invoke: Callable[[bool], Observation]
    reference: object
    injected: object
    expected_mechanism: tuple
    tolerance: float = 0


def same_output(actual, expected, tolerance):
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            same_output(value, reference, tolerance)
            for value, reference in zip(actual, expected, strict=True)
        )
    return math.isclose(actual, expected, rel_tol=0, abs_tol=tolerance)


SCENARIOS = {
    "P1": Scenario("proposal_sort.parameter_read",
                   lambda fault: proposal_sort([9, 7, 5], {"pre_nms_topn": 1, "post_nms_topn": 2}, fault),
                   [9], [9, 7], ("pre_nms_topn", "post_nms_topn")),
    "P2": Scenario("embedding_bag.padding_resolution",
                   lambda fault: embedding_bag([3, 5, 9], [0, 2], -1, fault),
                   3, 12, (2, None)),
    "L1": Scenario("write_view.coordinate_mapping",
                   lambda fault: write_view([1, 3, 2, 4], (1, 2), fault),
                   [1, 3, 2, 4], [1, 2, 3, 4], (2, 1)),
    "L2": Scenario("load_packed.byte_offset",
                   lambda fault: load_packed(bytes.fromhex("22 11 44 33 66 55"), 1, 2, fault),
                   0x3344, 0x4411, (2, 1)),
    "C1": Scenario("reduce_terms.validity",
                   lambda fault: reduce_terms({"A": 3, "B": 5, "C": 99}, ("A", "B"), "C", "add", fault),
                   8, 107, (0, 1)),
    "C2": Scenario("reduce_terms.required_update",
                   lambda fault: reduce_terms({"A": 2, "B": 5, "C": 7}, ("A", "B", "C"), "B", "omit", fault),
                   14, 9, (1, 0)),
    "C3": Scenario("reduce_terms.source_multiplicity",
                   lambda fault: reduce_terms({"A": 3, "B": 4}, ("A", "B"), "B", "add", fault),
                   7, 11, (1, 2)),
    "NUM-01": Scenario("accumulate.loop_state_store", lambda fault: accumulate([2048, 1, 1], fault),
                       2050, 2048, ([2048, 2049, 2050], [2048, 2048, 2048])),
    "NUM-02": Scenario("normalize.variance_expression",
                       lambda fault: normalize([8191, 8193, 8191, 8193], fault),
                       [-0.999995, 0.999995] * 2, [-316.22777, 316.22777] * 2, (1.0, 0.0), 1e-4),
}


def run(mode):
    scenario = SCENARIOS[mode]
    baseline = scenario.invoke(False)
    injected = scenario.invoke(True)
    restored = scenario.invoke(False)
    tolerance = scenario.tolerance
    checks = {
        "fault_hit": injected.hit and not baseline.hit and not restored.hit,
        "mechanism_changed": (baseline.mechanism, injected.mechanism) == scenario.expected_mechanism,
        "output_changed": (same_output(baseline.output, scenario.reference, tolerance)
                           and same_output(injected.output, scenario.injected, tolerance)
                           and not same_output(injected.output, scenario.reference, tolerance)),
        "restored": restored == baseline,
        "access_within_target": all(step.trace.get("guards_intact", True)
                                    for step in (baseline, injected, restored)),
    }
    return {"mode": mode, "target": scenario.target, "checks": checks, "passed": all(checks.values()),
            "calls": [
                {"call_id": f"{mode}/{name}", "output": step.output, "mechanism": step.mechanism,
                 "fault_hit": step.hit, "trace": step.trace}
                for name, step in (("baseline", baseline), ("injected", injected), ("restored", restored))
            ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=tuple(SCENARIOS), help="Run just one mode")
    args = parser.parse_args()
    results = [run(mode) for mode in ((args.mode,) if args.mode else SCENARIOS)]
    report = {"scope": "offline_synthetic_cpu_prototype", "results": results,
              "passed": sum(result["passed"] for result in results)}
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return int(report["passed"] != len(results))


if __name__ == "__main__":
    raise SystemExit(main())
