"""Materialize a version-scoped contract view from fixed GitHub dependency evidence."""

import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "validation_0_3_1" / "reader_v04"))
from readback import load, save


SHA1 = r"[a-f0-9]{40}"
ARCHIVE = re.compile(
    rf"[\w.-]+;https://github\.com/([\w.-]+/[\w.-]+)/archive/refs/tags/"
    rf"([\w./-]+)\.(?:zip|tar\.gz);{SHA1}"
)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def git_blob(source):
    url = urlsplit(source.get("origin", ""))
    if url.scheme != "https" or url.netloc != "github.com" or url.query:
        raise ValueError(f"{source['id']} needs a pin to the original GitHub blob")
    owner, repo, marker, revision, path = unquote(url.path).lstrip("/").split("/", 4)
    require(marker == "blob" and re.fullmatch(SHA1, revision)
            and revision == source["version"] and path == source["path"],
            f"{source['id']} blob, revision or path differs from the source")
    return f"{owner}/{repo}", revision


def confirmed_dependency(sources, entry):
    scope_id = entry["scope_source"]
    declaration = entry["declaration"]
    old = sources[scope_id]
    repo, revision = git_blob(old)
    lock = sources[declaration["source_id"]]
    require(old["kind"] == "code" and lock["kind"] in {"code", "contract"}
            and git_blob(lock) == (repo, revision),
            "The dependency declaration must come from the scoped implementation commit")
    lines = lock["text"].splitlines()
    line = declaration["line"]
    require(type(line) is int and 1 <= line <= len(lines), "Declaration line is outside its excerpt")
    match = ARCHIVE.fullmatch(lines[line - 1].strip())
    require(match is not None, "Selected declaration lacks a tagged GitHub archive and checksum")
    dependency_repo, tag = match.groups()
    ref = sources[entry["tag_ref_source"]]
    api = f"https://api.github.com/repos/{dependency_repo}/git"
    observed = json.loads(ref["text"])
    git_object = observed["object"]
    resolved = git_object["sha"]
    require(ref["kind"] == "report" and ref["version"] == f"refs/tags/{tag}"
            and ref["path"] == f"git/ref/tags/{tag}" and ref["origin"] == f"{api}/ref/tags/{tag}"
            and observed["ref"] == f"refs/tags/{tag}"
            and git_object["type"] == "commit" and re.fullmatch(SHA1, resolved)
            and git_object["url"] == f"{api}/commits/{resolved}",
            "Git ref evidence does not resolve this exact dependency tag to a commit")
    scope = {"claim": "static", "version": revision, "path": old["path"]}
    return (dependency_repo, resolved), scope


def materialize(material, manifest):
    """Return a derived scored view and the exact applicability of each projected source."""
    require(manifest["protocol"] == "pinned_dependency_contracts/0.4.1",
            "Unknown dependency contract protocol")
    cases = {case["case_id"]: case for case in material["cases"]}
    projected = {}
    for entry in manifest["bindings"]:
        case_id = entry["case_id"]
        sources = {source["id"]: source for source in cases[case_id]["sources"]}
        dependency, scope = confirmed_dependency(sources, entry)
        for source_id in entry["contracts"]:
            source = sources[source_id]
            key = (case_id, source_id)
            require(key not in projected and source["kind"] == "contract"
                    and git_blob(source) == dependency and source["version"] != scope["version"],
                    f"{case_id}/{source_id} is not a unique contract from the resolved dependency commit")
            projected[key] = scope
    require(bool(projected), "No applicable dependency contract found")
    view = {"cases": [
        {**case, "sources": [
            {**source, "version": projected[case["case_id"], source["id"]]["version"]}
            if (case["case_id"], source["id"]) in projected else source
            for source in case["sources"]
        ]}
        for case in material["cases"]
    ]}
    return view, projected


def check_requirements(packets, projected):
    for packet in packets:
        case_id = packet["case_id"]
        for action in packet["actions"]:
            for fact in action["facts"]:
                for anchor in fact["anchors"]:
                    scope = projected.get((case_id, anchor["source_id"]))
                    if scope is not None:
                        require(anchor["use"] == "requirement" and action["scope"] == scope,
                                "A dependency contract is usable only as a requirement in its bound static path")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("bindings", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    view, _ = materialize(load(args.original), load(args.bindings))
    if args.output.exists():
        parser.error("Write the projected view to a new path")
    save(args.output, view)


if __name__ == "__main__":
    main()
