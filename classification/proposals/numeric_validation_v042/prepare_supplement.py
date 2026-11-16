"""Seal a new exercise with fixed-source additions to the E06/G05 materials."""

import argparse
from pathlib import Path

from exercise import (
    CHECKOUT, INPUTS, check_freeze, load, now, payload_hash, prompt, save, sha,
)


def prepare(base, additions, stage, scope_guidance=None):
    if stage.is_relative_to(CHECKOUT):
        raise ValueError("Use a new exercise directory outside the checkout")
    freeze, seal = check_freeze(base)
    if freeze["suite"] != "fixed":
        raise ValueError("Expected the fixed E06/G05 exercise")
    material = load(base / "A.json")
    scopes = load(base / "scopes.json")
    overlay = load(additions)
    guidance = scope_guidance.read_text(encoding="utf-8").strip() if scope_guidance else ""
    if overlay.keys() != scopes.keys():
        raise ValueError("Source additions must cover the same cases")
    for case in material["cases"]:
        case_id = case["case_id"]
        extra = overlay[case_id]
        existing = {item["id"] for item in case["sources"]}
        added = {item["id"] for item in extra["sources"]}
        versions = {item["version"] for item in case["sources"]}
        if (existing & added or len(added) != len(extra["sources"])
                or any(item["version"] not in versions for item in extra["sources"])):
            raise ValueError(f"Source ID or fixed-version conflict: {case_id}")
        case["sources"].extend(extra["sources"])
        scopes[case_id] = "\n\n".join(filter(None, (extra["scope"], guidance)))

    stage.mkdir(parents=True)
    save(stage / "A.json", material)
    save(stage / "scopes.json", scopes)
    if scope_guidance:
        schema = load(base / "response-schema.json")
        properties = schema["properties"]["cases"]["items"]["properties"]
        properties["actions"]["minItems"] = 1
        save(stage / "response-schema.json", schema)
    else:
        (stage / "response-schema.json").write_bytes((base / "response-schema.json").read_bytes())
    execution = load(base / "execution.json")
    execution["prompt_sha256"] = payload_hash(prompt(stage))
    save(stage / "execution.json", execution)
    save(stage / "freeze.json", {
        **freeze, "frozen_at": now(), "inputs": {name: sha(stage / name) for name in INPUTS},
        "payload_sha256": execution["prompt_sha256"], "source_additions_sha256": sha(additions),
        "base_freeze_sha256": sha(base / "freeze.json"),
        "scope_guidance_sha256": sha(scope_guidance) if scope_guidance else None,
    })
    save(stage / "seal.json", {**seal, "sealed_at": now(), "freeze_sha256": sha(stage / "freeze.json")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("base", "additions", "stage"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--scope-guidance", type=Path)
    args = parser.parse_args()
    prepare(args.base.resolve(), args.additions.resolve(), args.stage.resolve(), args.scope_guidance)
