"""Public arithmetic controls from the v0.4.4 local review.

These controls do not call the classifier or execute GPU operators. Expected
dispositions are review annotations, not measured model classifications.
Only Python's standard library is required. Signed wrap is a mathematical model,
not a claim that C++ signed overflow is defined to wrap.
"""

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import struct
import sys

def signed(value, width):
    return (value + 2 ** (width - 1)) % (2 ** width) - 2 ** (width - 1)


def operation(name, left, right, width, op="mul"):
    exact = left * right if op == "mul" else left + right
    actual = signed(exact, width)
    return {"name": name, "operator": op, "operands": [left, right], "signed_bits": width,
            "exact_integer": exact, "represented_integer": actual, "representation_loss": actual != exact}


def integer_controls():
    rows = []
    def add(case_id, scenario, operations, expected, consumer, assertion, detail):
        assert assertion, case_id
        rows.append({"id": case_id, "scenario": scenario, "operations": operations,
                     "expected_disposition": expected, "consumer": consumer,
                     "assertion_passed": True, "interpretation": detail})
    safe = operation("offset", 32766, 1, 16, "add")
    add("I01", "合法位宽和最大正偏移", [safe], "COMPLIANT", "read offset 32767 within extent 32768",
        safe["represented_integer"] == 32767 and not safe["representation_loss"], "窄类型本身不构成缺陷。")
    product = operation("row_times_stride", 128, 257, 16)
    add("I02", "中间乘法超有符号范围", [product], "INTEGER_ADDRESS_CANDIDATE", "gather consumes represented offset",
        product["exact_integer"] == 32896 and product["represented_integer"] == -32640, "首个丢失在乘法结果，后加正确基址不能恢复。")
    y = operation("y_stride", 7, 8 * 521, 16)
    x = operation("x_stride", 7, 521, 16)
    total = operation("spatial_add", y["represented_integer"], x["represented_integer"], 16, "add")
    add("I03", "GridSampler 合法分量相加超范围", [y, x, total], "INTEGER_ADDRESS_CANDIDATE", "forward gather",
        not y["representation_loss"] and not x["representation_loss"] and total["represented_integer"] == -32713,
        "C=521 的两个乘积均可表示，首错是加法。不能统一称为乘法溢出。")
    safe_grid = operation("spatial_add", 7 * 8 * 520, 7 * 520, 16, "add")
    add("I04", "GridSampler 报告正确对照 C=520", [safe_grid], "COMPLIANT", "forward gather",
        safe_grid["represented_integer"] == 32760, "对应报告中的正确输出边界，模型只复算地址整数。")
    wide = operation("wide_spatial_add", 7 * 8 * 521, 7 * 521, 32, "add")
    add("I05", "执行前使用足够位宽", [wide], "COMPLIANT", "consumer receives offset 32823",
        wide["represented_integer"] == 32823, "宽化发生在导致首错的运算之前。")
    after = signed(product["represented_integer"], 32)
    add("I06", "溢出之后再宽化", [product, {"cast_to_signed_bits": 32, "value": after}], "INTEGER_ADDRESS_CANDIDATE",
        "gather consumes the already damaged value", after == -32640 and after != 32896,
        "更宽结果变量不证明中间表达式按宽类型执行。")
    outside = operation("logical_index", 99, 1, 32, "add")
    add("I07", "最终目标超过对象范围但整数未回绕", [outside], "LOGICAL_OR_ALLOCATION_BOUNDS",
        "read offset 100 from an extent-100 object", outside["represented_integer"] == 100 and not outside["representation_loss"],
        "需另审合法索引/分配约定；不得因最终越界推断表示不足。")
    final = operation("final_integer_address_add", 2**31 - 48, 100, 32, "add")
    add("I08", "中间偏移可表示但最终整数加法超范围", [final], "INTEGER_ADDRESS_CANDIDATE_IF_CONSUMED",
        "hypothetical signed integer address later converted to a pointer", final["represented_integer"] == -2147483596,
        "若实际实现真在窄整数中完成基址加法，首错位于最终加法。不能用这个模型断言任意机器指针相加会如此执行。")
    add("I09", "元素与字节单位混用", [{"element_offset": 3, "item_bytes": 4, "required_byte_offset": 12, "actual_byte_offset": 3}],
        "L2", "byte-addressed consumer", 3 * 4 == 12 and signed(3, 16) == 3,
        "整数表示完全保留，失配由单位关系造成。")
    add("I10", "漏掉基址项", [{"required_base": 4096, "byte_offset": 12, "required_address": 4108, "actual_address": 12}],
        "OTHER_ADDRESS_MAPPING", "address consumer", signed(4108, 32) == 4108,
        "遗漏基址且无连续布局假设，不满足 L1，也不满足整数表示范围候选。")
    add("I11", "整数错误量没有到达消费者", [product, {"replacement_offset": 32896}], "NO_CONFIRMED_ADDRESS_FAULT",
        "consumer uses a separately recomputed wide value", product["representation_loss"] and signed(32896, 32) == 32896,
        "不确认实际寻址故障。对 C++ signed overflow 还须另审语言级未定义行为，不能由未消费断言整个程序安全。")
    for index, sample, expected in ((12, 65535, "COMPLIANT"), (13, 65536, "INTEGER_ADDRESS_CANDIDATE")):
        target = operation("sample_times_map", sample, 1, 32)
        offset = operation("sample_map_times_classes", target["represented_integer"], 32768, 32)
        exact = sample * 32768
        add(f"I{index}", "NLLLoss2d backward 边界", [target, offset], expected, "grad_input + ioffset then gradient write",
            offset["representation_loss"] == (sample == 65536) and 0 <= exact < 65537 * 32768,
            "target=0 且所有逻辑索引合法，首错为 ioffset 中的第二次乘法。")
    for index, block, expected in ((14, 65535, "COMPLIANT"), (15, 65536, "INTEGER_ADDRESS_CANDIDATE")):
        token = operation("block_times_block_size", block, 16, 32)
        offset = operation("token_times_stride", token["represented_integer"], 2 * 8 * 128, 32)
        add(f"I{index}", "FlexAttention 页块偏移边界", [token, offset], expected, "K/V tile load consumes the element offset",
            offset["representation_loss"] == (block == 65536),
            "此为报告独立复现脚本的逐 token 交错 K/V stride。最大安全块数 65536 与首个不安全块号 65536 相差一个计数位置。")
    fwd = signed(63 * 521, 16)
    bwd = signed(63, 16)
    add("I16", "前向错误而反向偏移正确", [{"forward_offset": fwd, "backward_offset": bwd}], "TWO_ACTIONS_MUST_NOT_BE_MERGED",
        "forward gather and backward grad_input scatter are distinct", fwd != 63 * 521 and bwd == 63,
        "8x8 大 stride 触发前向，grad_input 的 H*W 索引仍安全，支持两处代码职责独立。")
    add("I17", "反向错误而前向地址项正确的静态对照", [{"shape": [257, 257], "input_spatial_strides": [0, 0],
        "forward_offset": 0, "backward_exact": 66048, "backward_int16": signed(66048, 16)}], "TWO_ACTIONS_MUST_NOT_BE_MERGED",
        "forward reads an expanded scalar; backward addresses contiguous grad_input", signed(66048, 16) == 512,
        "只证明两条地址公式的独立性，未执行此展开输入的算子。实际合法调用仍受原接口条件约束。")
    half = lambda value: struct.unpack("e", struct.pack("e", value))[0]
    state = half(half(2048 + 1) + 1)
    wide_state = half(2048 + 1 + 1)
    add("I18", "NUM-01 浮点运行状态近邻", [{"repeated_half_state": state, "wide_state_then_half": wide_state}], "NUM01_NEIGHBOR",
        "floating accumulation consumes the previous rounded state", state == 2048 and wide_state == 2050,
        "状态语义为数值累加，未生成地址，不能归整数地址候选。此对照不代替实际合同举证。")
    return {"schema": "integer-address-v044/controls@1", "scope": "executable_arithmetic_and_semantic_controls",
            "original_device_operator_runs": 0, "total": len(rows), "passed": len(rows),
            "language_note": "Modulo arithmetic is a model of reported representation loss. Signed C++ overflow is not defined to wrap; device-runtime claims retain their original reported scope.",
            "cases": rows}


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def rounded_sum(xs, schedule):
    if schedule == "pairwise":
        if len(xs) == 1:
            return xs[0]
        k = len(xs) // 2
        return f32(rounded_sum(xs[:k], schedule) + rounded_sum(xs[k:], schedule))
    r = f32(0)
    for x in xs:
        r = f32(r + x)
    return r


def arithmetic_case(name, values, schedule="sequential"):
    xs = [f32(x) for x in values]
    d = f32(1 / len(xs))
    def mean(items):
        return rounded_sum([f32(x * d) for x in items], schedule)
    m = mean(xs)
    ex2 = mean([f32(x * x) for x in xs])
    raw = f32(ex2 - f32(m * m))
    centered = mean([f32(f32(x - m) * f32(x - m)) for x in xs])
    exact_mean = sum(map(Fraction, xs)) / len(xs)
    exact = sum((Fraction(x) - exact_mean) ** 2 for x in xs) / len(xs)
    double_mean = math.fsum(xs) / len(xs)
    double_centered = math.fsum((x - double_mean) ** 2 for x in xs) / len(xs)
    epsilon = f32(1e-12)
    rsqrt_arg = f32(raw + epsilon)
    return {
        "id": name, "n": len(xs), "input_values": xs if len(xs) <= 4 else {"constant": xs[0]},
        "schedule": schedule, "mean_float32": m, "mean_square_float32": ex2,
        "raw_moment_float32": raw, "centered_float32": centered, "clamped_raw_float32": max(0.0, raw),
        "exact_variance_of_stored_inputs": str(exact), "reference_variance": float(exact),
        "centered_binary64_reference": double_centered,
        "epsilon_float32": epsilon, "rsqrt_arg_float32": rsqrt_arg,
        "rsqrt_status": "NaN-domain" if rsqrt_arg < 0 else "finite",
        "evidence_scope": "CPU rounded arithmetic control; neither GPU trace nor performance result",
    }


def variance_controls():
    checks = []
    def check(name, passed):
        if not passed:
            raise AssertionError(name)
        checks.append({"id": name, "passed": True})
    controls = [
        arithmetic_case("ordinary_scale", [1, 2, 3, 4]),
        arithmetic_case("nonzero_variance_lost", [1e6 - 1/16, 1e6 + 1/16]),
        arithmetic_case("negative_raw_variance", [1e6, 1e6 + 3/16]),
        arithmetic_case("constant_448_sequential", [1e6] * 448),
        arithmetic_case("constant_448_pairwise", [1e6] * 448, "pairwise"),
    ]
    c = {x["id"]: x for x in controls}
    check("control_ordinary_scale", c["ordinary_scale"]["raw_moment_float32"] == c["ordinary_scale"]["centered_float32"] == 1.25)
    check("control_same_precision_positive_loss", c["nonzero_variance_lost"]["raw_moment_float32"] == 0 and c["nonzero_variance_lost"]["centered_float32"] == 1/256)
    check("control_clamp_does_not_recover", c["nonzero_variance_lost"]["clamped_raw_float32"] == 0 and c["nonzero_variance_lost"]["reference_variance"] == 1/256)
    check("control_negative_raw_consumed", c["negative_raw_variance"]["raw_moment_float32"] == -65536 and c["negative_raw_variance"]["rsqrt_status"] == "NaN-domain")
    check("control_same_precision_centered_finite", c["negative_raw_variance"]["centered_float32"] == 0.009765625 and c["negative_raw_variance"]["reference_variance"] == 9/1024)
    check("control_schedule_affects_result", c["constant_448_sequential"]["raw_moment_float32"] == 8912896 and c["constant_448_pairwise"]["raw_moment_float32"] == -262144)
    check("control_exact_and_binary64_reference", all(x["reference_variance"] == x["centered_binary64_reference"] for x in controls))
    return {"GPU_execution": "NOT_TESTED", "controls": controls, "checks": checks,
            "case_count": len(controls), "assertions_passed": len(checks)}


def run():
    if sys.flags.optimize:
        raise RuntimeError("Run without -O: integer controls contain assertions")
    integer = integer_controls()
    variance = variance_controls()
    assert integer["total"] == integer["passed"] == 18
    assert variance["case_count"] == 5 and variance["assertions_passed"] == 7
    return {"schema": "MECH-v0.4.4/public-arithmetic-controls@1",
            "scope": "arithmetic_and_semantic_boundary_controls_only",
            "integer": integer, "variance": variance,
            "classifier_invocations": 0, "model_reads": 0, "GPU_executions": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write a new expected result file only if absent")
    parser.add_argument("--verify", action="store_true", help="compare against the published expected results (default)")
    args = parser.parse_args()
    result = run()
    payload = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    expected = Path(__file__).with_name("PUBLIC_CONTROL_RESULTS.json")
    if args.write:
        with expected.open("xb") as stream:
            stream.write(payload)
    elif expected.read_bytes() != payload:
        raise AssertionError("Public arithmetic control results changed")
    print(json.dumps({"result": "PASS", "integer_cases": 18, "variance_cases": 5,
                      "variance_assertions": 7, "classifier_invocations": 0,
                      "model_reads": 0, "GPU_executions": 0}))


if __name__ == "__main__":
    main()
