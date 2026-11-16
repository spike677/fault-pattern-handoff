"""Reproduce numerical controls with explicit output contracts and precision."""

from decimal import Decimal
import math

from proposals.v041_review.verify_candidate_review import binary_float


def terminal_conversion(contributions):
    wide_state = 0.0
    narrow_state = 0.0
    for value in contributions:
        wide_state = binary_float("<f", wide_state + value)
        narrow_state = binary_float("<e", narrow_state + value)
    return {"wide_state": wide_state, "terminal_fp16": binary_float("<e", wide_state),
            "iterative_fp16": narrow_state}


def approximate_normalization(values):
    """Model unfused FP32 raw moments against a centered reference."""
    def fp32(value):
        return binary_float("<f", value)

    values = tuple(fp32(value) for value in values)
    epsilon = fp32(1e-5)
    mean = fp32(math.fsum(values) / len(values))
    moment = fp32(math.fsum(fp32(value * value) for value in values) / len(values))
    variance = fp32(moment - fp32(mean * mean))
    rsigma = fp32(1 / math.sqrt(fp32(variance + epsilon)))
    predicted = tuple(fp32(fp32(value - mean) * rsigma) for value in values)
    exact_values = tuple(Decimal.from_float(value) for value in values)
    exact_mean = sum(exact_values) / len(exact_values)
    centered = sum((value - exact_mean) ** 2 for value in exact_values) / len(exact_values)
    exact_scale = (centered + Decimal.from_float(epsilon)).sqrt()
    reference = tuple(float((value - exact_mean) / exact_scale) for value in exact_values)
    return {"variance": variance, "reference_variance": float(centered), "output": predicted,
            "reference_output": reference,
            "max_absolute_error": max(abs(x - y) for x, y in zip(predicted, reference, strict=True))}
