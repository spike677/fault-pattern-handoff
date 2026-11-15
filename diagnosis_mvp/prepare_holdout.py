"""Prepare and seal controlled synthetic fixtures in a process separate from diagnosis."""

import hashlib
import json
from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parent
RUN = ROOT / "controlled_regression_v0_1_1"


def record(path, data):
    data = (json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Existing fixture differs: {path}")
    else:
        with path.open("xb") as output:
            output.write(data)
    return hashlib.sha256(data).hexdigest()


def span(size):
    return {"range": [0, size], "unit": "element"}


def geometry(shape, strides, index, base=0):
    return {"shape": shape, "strides": strides, "index": index, "base": base, "unit": "element"}


def offset(position):
    return {"offset": position, "unit": "element"}


def rounded_healthy(inputs):
    return sum(inputs) / 2


def vector(value):
    return {"dtype": "float32", "values": [value]}


def reference(value, input_kind, qualified=True):
    return {**vector(value), "input_kind": input_kind, "qualified": qualified,
            "reference_id": "scalar-average-v2", "state_id": "read-only-state", "mapping_id": "position-0"}


def numeric(actual, dirty_inputs, healthy_inputs=None):
    fields = {
        "numeric.actual": vector(actual),
        "numeric.ref_observed": reference(rounded_healthy(dirty_inputs), "OBSERVED"),
        "numeric.tolerance": {"atol": 0, "rtol": 0},
    }
    if healthy_inputs is not None:
        fields["numeric.ref_healthy"] = reference(rounded_healthy(healthy_inputs), "HEALTHY")
    return fields


def shared_memory(read_at, write_at, write_clock="trace-A", write_start=4):
    return {
        "timing.read": {"allocation": "ring", "range": [0, 8], "unit": "byte",
                        "generation": 6, "order_id": "trace-A", "read_done": read_at},
        "timing.later_write": {"allocation": "ring", "range": [write_start, write_start + 8], "unit": "byte",
                               "generation": 7, "order_id": write_clock, "write_at": write_at},
    }


def plan(expected, produced, received, consumed):
    return {f"plan.{key}": span(value) for key, value in
            zip(("expected", "produced", "received", "consumed"), (expected, produced, received, consumed))}


def raw_float(value):
    return {"dtype": "float32", "shape": [1], "hex": struct.pack("<f", value).hex()}


class Fixtures:
    def __init__(self):
        self.inputs, self.packets, self.answers = [], {}, {}

    def add(self, case_id, routes, fields, *, later=None, expect=(), outcome=None, decisive=(),
            why=None, scope="APPLICABLE", group=None, numeric_stage=None, output_check=None,
            symptom="Output values differ under an alternate configuration."):
        track = "classification" if case_id.startswith("C") else "diagnosis"
        family = f"controlled-{group or case_id}"
        lineage = [f"family:{family}", f"event:simulator-{family}", f"answer:sealed-{family}"]
        if group:
            lineage.extend((f"patch:simulated-{group}", f"source:shared-{group}"))
        build, call = f"build-{case_id}", f"invocation-{case_id}"

        def observation(field, value, index):
            anchoring = field.endswith(".expected") or field in {
                "layout.geometry", "numeric.tolerance", "timing.expected_participants",
            }
            return {"fact_id": f"{case_id}-record-{index}", "field": field, "build": build,
                    "call_id": call, "source": f"synthetic://{case_id}/observation/{index}",
                    "kind": "CONTRACT" if anchoring else "OBSERVED", "value": value}

        self.inputs.append({
            "track": track, "lineage": lineage,
            "case": {"case_id": case_id, "family_id": family, "build": build, "call_id": call,
                     "intake": symptom, "routes": routes,
                     "contract": {"version": "simulation-v1", "build": build, "status": scope,
                                  "source": f"synthetic://{case_id}/applicable-contract"},
                     "observations": [observation(f, v, i) for i, (f, v) in enumerate(fields.items(), 1)]},
        })
        self.packets[case_id] = {
            field: observation(field, value, index)
            for index, (field, value) in enumerate((later or {}).items(), len(fields) + 1)
        }
        answer = {"outcome": outcome or ("SUPPORTED" if expect else "NO_SUPPORTED_MECHANISM"),
                  "mechanisms": list(expect), "decisive_fields": list(decisive), "unresolved": why}
        if numeric_stage:
            answer["numeric_stage"] = numeric_stage
        if output_check:
            answer["output_check"] = output_check
        self.answers[case_id] = answer


def classification(f):
    # Different toy operators use the same address law. Faulty offsets come from distinct transformations.
    row_major = 1 * 3 + 1
    f.add("C01", ["layout"], {"layout.geometry": geometry([2, 3], [1, 2], [1, 1]),
                              "layout.actual_offset": offset(row_major)}, expect=["ADDRESS_MAPPING"])
    stride_ignored = 7 + 2
    f.add("C02", ["layout"], {"layout.geometry": geometry([4], [3], [2], base=7),
                              "layout.actual_offset": offset(stride_ignored)}, expect=["ADDRESS_MAPPING"])
    requested, truncated = len(range(9)), 2 * (len(range(9)) // 2)
    f.add("C03", ["plan"], plan(requested, truncated, truncated, truncated), expect=["PLAN_GENERATION"])
    f.add("C04", ["plan"], plan(6, 6, 5, 5), expect=["PLAN_TRANSFER"])
    f.add("C05a", ["plan"], plan(7, 7, 7, 8), expect=["PLAN_CONSUMPTION"], group="plan-end-inclusive")
    f.add("C05b", ["plan"], plan(11, 11, 11, 12), expect=["PLAN_CONSUMPTION"], group="plan-end-inclusive")
    f.add("C06", ["interface"], {"interface.expected": {"rank": 4, "axes": [1, 3]},
                                "interface.observed": {"rank": 4, "axes": [1, 2]}},
          expect=["INTERFACE_CONTRACT"])
    f.add("C07", ["contribution"], {"contribution.expected": ["lane8", "lane9", "lane10"],
                                   "contribution.observed": ["lane8", "lane10", "pad"]},
          expect=["UNEXPECTED_CONTRIBUTION", "MISSING_CONTRIBUTION"])
    f.add("C08", ["numeric"], numeric(8, [4, 8], [2, 6]), expect=["LOCAL_NUMERIC_DEVIATION"],
          numeric_stage="LOCAL_AND_PROPAGATION")
    f.add("C09", ["numeric"], numeric(9, [5, 13], [5, 9]), numeric_stage="UPSTREAM_PROPAGATION")
    f.add("C10", ["timing"], {
        **shared_memory(30, 28), "timing.expected_participants": ["g1:round6:t3", "g1:round6:t4"],
        "timing.observed_participants": ["g1:round6:t3", "g1:round7:t4"],
    }, expect=["COLLECTIVE_PARTICIPATION", "SHARED_SLOT_EARLY_REUSE"])
    f.add("C11", ["layout"], {"layout.geometry": geometry([3], [2], [3]),
                              "layout.actual_offset": offset(6)}, outcome="UNKNOWN", why="definition")
    f.add("C12", ["layout"], {"layout.geometry": geometry([9], [2], [4]),
                              "layout.actual_offset": offset(4)}, outcome="OUT_OF_SCOPE", scope="OUT_OF_SCOPE")
    mode = {"dtype": "float32", "shape": [1], "mode": "BITWISE"}
    f.add("C13", ["numeric"], {
        "comparison.expected": {"primary": mode, "secondary": mode},
        "comparison.actual": {"primary": raw_float(1.25)},
        "comparison.reference": {"primary": raw_float(1.25)},
    }, outcome="UNKNOWN", why="evidence", numeric_stage="UNKNOWN", output_check="INCOMPLETE")


def diagnosis(f):
    f.add("D01", ["numeric", "layout"], {
        "layout.geometry": geometry([5, 2], [5, 2], [2, 1], base=3),
        "numeric.actual": vector(4.5),
    }, later={"layout.actual_offset": offset(8), "numeric.tolerance": {"atol": 0, "rtol": 0},
              "numeric.ref_observed": reference(4.5, "OBSERVED")},
          expect=["ADDRESS_MAPPING"], decisive=["layout.actual_offset"])
    f.add("D02", ["plan", "layout"], {
        "plan.expected": span(15), "plan.received": span(14), "plan.consumed": span(14),
    }, later={"plan.produced": span(15)}, expect=["PLAN_TRANSFER"], decisive=["plan.produced"])
    f.add("D03", ["layout", "interface"], {
        "interface.expected": {"axis": -1, "normalized": 2},
    }, later={"interface.observed": {"axis": -1, "normalized": 1}},
          expect=["INTERFACE_CONTRACT"], decisive=["interface.observed"])
    slot = shared_memory(23, 22)
    f.add("D04", ["timing", "layout"], {
        "timing.read": slot["timing.read"], "timing.expected_participants": ["g4:round6:t2"],
    }, later={"timing.later_write": slot["timing.later_write"],
              "timing.observed_participants": ["g4:round6:t2"]},
          expect=["SHARED_SLOT_EARLY_REUSE"], decisive=["timing.later_write"])
    f.add("D05", ["timing", "contribution"], {
        "contribution.expected": ["part0", "part1", "part2"],
        "timing.expected_participants": ["g2:round1:t0", "g2:round1:t1"],
    }, later={"contribution.observed": ["part0", "part1", "part1", "part2"],
              "timing.observed_participants": ["g2:round1:t0", "g2:round1:t1"]},
          expect=["REPEATED_CONTRIBUTION"], decisive=["contribution.observed"])
    f.add("D06", ["layout", "plan"], {
        "layout.geometry": geometry([3, 6], [16, 2], [2, 3]),
        "plan.expected": span(13), "plan.produced": span(13), "plan.received": span(13),
    }, later={"layout.actual_offset": offset(35), "plan.consumed": span(14)},
          expect=["ADDRESS_MAPPING", "PLAN_CONSUMPTION"], decisive=["layout.actual_offset", "plan.consumed"])
    previous = numeric(11, [7, 15], [7, 9])
    healthy = previous.pop("numeric.ref_healthy")
    f.add("D07", ["numeric"], previous, later={"numeric.ref_healthy": healthy},
          decisive=["numeric.ref_healthy"], numeric_stage="UPSTREAM_PROPAGATION")
    incomparable_order = shared_memory(8, 2, write_clock="trace-Z")
    f.add("D08", ["timing"], {
        "timing.read": incomparable_order["timing.read"],
        "timing.expected_participants": ["g2:round6:t5"],
    }, later={"timing.later_write": incomparable_order["timing.later_write"],
              "timing.observed_participants": ["g2:round6:t5"]},
          outcome="UNKNOWN", why="evidence")
    f.add("D09", ["numeric"], {
        "numeric.actual": vector(7), "numeric.tolerance": {"atol": 0, "rtol": 0},
    }, later={"numeric.ref_observed": reference(3, "OBSERVED", qualified=False)},
          outcome="UNKNOWN", why="reference", numeric_stage="UNKNOWN")
    f.add("D10", ["layout", "interface"], {
        "layout.geometry": geometry([10], [3], [6]),
    }, later={"layout.actual_offset": offset(6)}, scope="UNKNOWN", outcome="UNKNOWN", why="evidence")
    f.add("D11", ["plan"], {"plan.expected": span(20)}, outcome="UNKNOWN", why="observation")
    f.add("D12", ["layout"], {"layout.geometry": geometry([5], [3], [3], base=2)},
          later={"layout.actual_offset": offset(11)}, decisive=["layout.actual_offset"],
          symptom="Changing the output view reproduces the observed values.")
    f.add("D13", ["timing"], {
        **shared_memory(18, 15, write_start=8), "timing.expected_participants": ["g0:round6:t7"],
    }, later={"timing.observed_participants": ["g0:round6:t7"]},
          decisive=["timing.observed_participants"], symptom="A newer iteration uses the same allocation.")
    f.add("D14", ["interface", "contribution"], {"contribution.expected": ["row17", "row18"]},
          later={"contribution.observed": ["row17", "row18"],
                 "interface.expected": {"output_count": 2}, "interface.observed": {"output_count": 1}},
          expect=["INTERFACE_CONTRACT"], decisive=["interface.expected", "interface.observed"])


def main():
    freeze_bytes = (ROOT / "freeze_v0_1_1.json").read_bytes()
    fixtures = Fixtures()
    classification(fixtures)
    diagnosis(fixtures)
    public = RUN / "public"
    answers = RUN / "answers"
    public.mkdir(parents=True, exist_ok=True)
    answers.mkdir(parents=True, exist_ok=True)
    hashes = {
        "inputs.json": record(public / "inputs.json", fixtures.inputs),
        "packets.json": record(public / "packets.json", fixtures.packets),
        "answer_key.json": record(answers / "answer_key.json", fixtures.answers),
    }
    record(public / "seal.json", {
        "kind": "SYNTHETIC_CONTROLLED", "freeze_sha256": hashlib.sha256(freeze_bytes).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "preparation": "Regression on the same controlled v0.1.0 fixtures, after both comparison fixes. "
                       "The answer key was already revealed for the first run.",
        "hashes": hashes,
    })


if __name__ == "__main__":
    main()

