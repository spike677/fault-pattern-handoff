"""Verify the public MECH-v0.4 release offline from a clone or source archive."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
RELEASE = Path(__file__).resolve().parent
CLASSIFICATION = ROOT / "classification"


def verify_files():
    records = (RELEASE / "FILE_HASHES.sha256").read_text(encoding="utf-8").splitlines()
    paths = set()
    for record in records:
        expected, name = record.split("  ", 1)
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or name in paths:
            raise ValueError(f"Invalid release inventory path: {name}")
        actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Release hash differs: {name}")
        paths.add(name)
    if not paths:
        raise ValueError("The release hash inventory is empty")
    return len(paths)


def run(*args, cwd=ROOT, capture=False):
    return subprocess.run([sys.executable, "-B", "-X", "utf8", *args], cwd=cwd, check=True,
                          stdout=subprocess.PIPE if capture else None, encoding="utf-8").stdout


def main():
    count = verify_files()
    formal = CLASSIFICATION / "mech_v04"
    run(str(formal / "evaluation.py"), "check-freeze", str(formal / "F_FREEZE.json"))
    catalog = json.loads((formal / "catalog.json").read_bytes())
    migration = json.loads((formal / "migration_from_v03.json").read_bytes())
    modes = set(catalog["modes"])
    inherited = migration["inherited_modes"]
    if (len(modes) != 9 or any(old != new for old, new in inherited.items())
            or modes != set(inherited) | set(migration["admitted_modes"])
            or set(catalog["admitted_modes"]) != set(migration["admitted_modes"])):
        raise ValueError("The public mode migration differs from the nine formal cards")
    run("-m", "unittest", "test_mech_v04_cross_version", "test_mech_v04_injection",
        "test_mech_v04.FWorkflowTest", cwd=CLASSIFICATION)
    run("-m", "unittest", "discover", "-s", "diagnosis_mvp", "-p", "test_*.py")
    injection = json.loads(run(str(formal / "injection.py"), capture=True))
    if injection["passed"] != len(modes) or {row["mode"] for row in injection["results"]} != modes:
        raise ValueError("The injection prototype did not pass for all nine modes")
    print(f"Verified {count} release file hashes, nine formal cards and nine CPU injection scenarios.")


if __name__ == "__main__":
    main()
