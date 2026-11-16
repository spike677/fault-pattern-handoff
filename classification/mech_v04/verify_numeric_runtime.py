"""Reproduce the public JAX 0.6.2 CPU case and two precision controls."""

import argparse
import hashlib
import inspect
import json
import math
import os
import platform
from pathlib import Path
import struct
import sys


HERE = Path(__file__).resolve().parent
packages = Path(os.environ.get("JAX_REVIEW_PACKAGES", HERE / "jax-runtime"))
if packages.is_dir():
    sys.path.insert(0, str(packages))
if os.name == "nt":
    if (packages / "jaxlib").is_dir():
        runtime = os.add_dll_directory(str(packages / "jaxlib"))
    if dll_path := os.environ.get("JAX_REVIEW_DLL_PATH"):
        msvc = os.add_dll_directory(dll_path)

import jax
import jax.numpy as jnp
import jaxlib
import numpy as np
import scipy


def diff(left, right):
    return float(np.max(np.abs(np.asarray(left) - np.asarray(right))))


def normalize_with_centered_variance(x):
    variance = jnp.var(x, axis=-1, keepdims=True)
    return jax.nn.standardize(x, axis=-1, variance=variance)


def issue_model(x, normalize):
    pooled = jax.lax.reduce_window(x, -jnp.inf, jax.lax.max,
                                   (1, 1, 2, 2), (1, 1, 2, 2), "VALID")
    return normalize(jax.nn.gelu(jax.nn.silu(pooled)))


def float16(value):
    try:
        return struct.unpack("<e", struct.pack("<e", value))[0]
    except OverflowError:
        return math.inf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir-dir", type=Path)
    args = parser.parse_args()
    assert jax.__version__ == jaxlib.__version__ == "0.6.2"
    assert jax.default_backend() == "cpu"
    assert not jax.config.x64_enabled
    source = Path(inspect.getsourcefile(inspect.unwrap(jax.nn.standardize))).read_bytes()
    git_blob = hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest()
    assert git_blob == "21ea7ac615a920f33fb243bd86eeb8fffc8b4897", git_blob

    witness = jnp.asarray([[8191.0, 8193.0, 8191.0, 8193.0]], dtype=jnp.float32)
    raw = jax.nn.standardize(witness)
    stable = jax.jit(normalize_with_centered_variance)(witness)
    float64_witness = np.asarray(witness, dtype=np.float64)
    centered = float64_witness - float64_witness.mean(axis=-1, keepdims=True)
    reference = centered / np.sqrt((centered**2).mean(axis=-1, keepdims=True) + 1e-5)
    assert diff(stable, reference) < 1e-4
    assert diff(raw, reference) > 300

    if args.ir_dir:
        args.ir_dir.mkdir(parents=True, exist_ok=True)
        lowered = jax.nn.standardize.lower(witness)
        hlo = lowered.compiler_ir(dialect="stablehlo")
        compiled_hlo = lowered.compile().as_text()
        (args.ir_dir / "jax-standardize-stablehlo.mlir").write_text(str(hlo), encoding="utf-8")
        (args.ir_dir / "jax-standardize-cpu-hlo.txt").write_text(compiled_hlo, encoding="utf-8")

    _, key = jax.random.split(jax.random.PRNGKey(121235))
    inputs = jax.random.normal(key, (15, 14, 13, 4), dtype=jnp.float32)
    issue = {}
    for label, normalizer in (("release", jax.nn.standardize), ("centered", normalize_with_centered_variance)):
        def model(x):
            return issue_model(x, normalizer)

        issue[label] = diff(model(inputs), jax.jit(model)(inputs))

    sound_input = jnp.asarray([[1.0, 2.0, 4.0]], dtype=jnp.float32)
    sound = np.asarray(sound_input, dtype=np.float64)
    sound -= sound.mean(axis=-1, keepdims=True)
    sound /= np.sqrt((sound**2).mean(axis=-1, keepdims=True) + 1e-5)
    normal_error = diff(jax.nn.standardize(sound_input), sound)
    assert normal_error < 1e-4

    terminal = np.asarray([2048.0, 1.0, 1.0], dtype=np.float16)
    wide_value = float(np.sum(terminal, dtype=np.float32))
    end_value = float(np.float16(wide_value))
    step_value = 0.0
    for term in terminal:
        step_value = float16(step_value + float(term))
    assert (wide_value, end_value, step_value) == (2050, 2050, 2048)

    lane = 0.0
    overflow = None
    for update in range(1, 49):
        lane = float16(lane + 1400)
        if math.isinf(lane):
            overflow = update
            break
    assert overflow is not None and float16(1400) == 1400

    print(json.dumps({
        "environment": {"jax": jax.__version__, "jaxlib": jaxlib.__version__, "numpy": np.__version__,
                        "scipy": scipy.__version__, "python": platform.python_version(),
                        "platform": platform.system(), "machine": platform.machine(),
                        "backend": jax.default_backend(), "jax_source_git_blob": git_blob,
                        "x64_enabled": jax.config.x64_enabled},
        "jax_37281_seed": {"seed": 121235, "shape": list(inputs.shape), "eager_vs_outer_jit": issue},
        "jax_compiled_witness": {"input": np.asarray(witness).tolist(), "raw": np.asarray(raw).tolist(),
                                 "centered": np.asarray(stable).tolist(), "reference": reference.tolist(),
                                 "raw_error": diff(raw, reference), "centered_error": diff(stable, reference)},
        "jax_compiled_control": {"input": np.asarray(sound_input).tolist(),
                                 "max_absolute_error": normal_error, "review_bound": 1e-4},
        "terminal_cast_control": {"wide": wide_value, "terminal_fp16": end_value, "step_fp16": step_value},
        "qdrant_report_1400_control": {"modeled_first_overflow_update": overflow,
                                       "updates_per_lane": 48, "float32_full_dot": 1536 * 1400,
                                       "scope": "model of the fixed loop; this host did not execute NEON"},
    }, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
