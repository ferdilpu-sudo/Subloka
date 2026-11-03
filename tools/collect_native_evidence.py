"""Copy bounded native build metadata for review; never execute build commands.

This is evidence collection, not a license-completeness verdict. Only run on
the CI build worker, before signing. No environment dump or Gradle credentials.
"""
import argparse
import hashlib
import json
from pathlib import Path

BUILD_NAMES = {"CMakeCache.txt", "build.ninja", "rules.ninja",
               "compile_commands.json", "link.txt", "android_gradle_build.json"}
LIMIT = 32 * 1024 * 1024
BUDGET = 128 * 1024 * 1024


def collect(repo, ndk, output):
    repo, ndk, output = map(lambda p: Path(p).resolve(), (repo, ndk, output))
    output.mkdir(parents=True, exist_ok=True)
    entries, missing = [], []
    candidates = []
    for module in ("asr", "translation"):
        root = repo / "engine" / module / ".cxx"
        found = [p for p in root.rglob("*") if p.name in BUILD_NAMES]
        if not found:
            missing.append(f"engine/{module}/.cxx build metadata")
        candidates.extend((p, repo, "build") for p in found)
    for name in ("source.properties", "NOTICE", "NOTICE.toolchain"):
        p = ndk / name
        if p.is_file():
            candidates.append((p, ndk, "ndk"))
        else:
            missing.append(f"ndk/{name}")
    used = 0
    for path, root, kind in sorted(candidates, key=lambda item: str(item[0])):
        relative = path.relative_to(root).as_posix()
        entry = {"kind": kind, "path": relative}
        entries.append(entry)
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            entry["status"] = "rejected_symlink"
            continue
        if not path.is_file():
            entry["status"] = "not_regular_file"
            continue
        size = path.stat().st_size
        if size > LIMIT or used + size > BUDGET:
            entry["status"] = "size_limit"
            continue
        data = path.read_bytes()
        used += len(data)
        dest = output / kind / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        entry.update(status="copied", size=len(data), sha256=hashlib.sha256(data).hexdigest())
    report = {"schema": 1, "review_status": "UNREVIEWED",
              "scope": "CMake metadata and installed NDK notices; not proof of license completeness",
              "missing": missing, "files": entries}
    (output / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--ndk", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = collect(args.repo, args.ndk, args.output)
    print(f"Native evidence: {sum(f['status'] == 'copied' for f in report['files'])} files; "
          f"{len(report['missing'])} missing inputs; review required")
