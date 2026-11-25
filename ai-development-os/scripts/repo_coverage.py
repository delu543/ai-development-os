#!/usr/bin/env python3
"""Inventory a fixed Git tree and reconcile a reviewer's JSONL ledger. Python 3.8+."""
import argparse
import json
import os
from collections import Counter
from pathlib import Path
import subprocess
import sys

SCHEMA = "ai-development-os/coverage-v1"
STATES = ("pending", "read", "object", "partial", "blocked")
TEXT = {"text", "lfs-text"}
OBJECTS = {"binary", "lfs-binary", "symlink", "submodule"}
KINDS = TEXT | OBJECTS | {"unknown", "restricted"}


class InvalidLedger(ValueError):
    pass


def git(repo, *args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1",
               GIT_ALLOW_PROTOCOL="", GIT_TERMINAL_PROMPT="0")
    # The explicit --repo must win even when invoked by a parent Git hook or tool.
    for variable in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
                     "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                     "GIT_PREFIX", "GIT_NAMESPACE"):
        env.pop(variable, None)
    # No checkout, hooks, text conversion, filters, or remote transports.
    result = subprocess.run(["git", "--no-replace-objects", "-C", str(repo), *args],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if result.returncode:
        raise ValueError("Git command failed ({}). Check local objects, ref and read access."
                         .format(args[0]))
    return result.stdout


def object_tree(repo, ref):
    if ref.startswith("-"):
        raise ValueError("Use a commit, branch or tag as the ref.")
    commit = git(repo, "rev-parse", "--verify", ref + "^{commit}").decode("ascii").strip()
    tree = git(repo, "rev-parse", "--verify", commit + "^{tree}").decode("ascii").strip()
    paths = {}
    for item in git(repo, "ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0"):
        if not item:
            continue
        meta, raw_path = item.split(b"\t", 1)
        mode, _, oid = meta.decode("ascii").split()
        # On all hosts preserve Git path bytes, including invalid UTF-8, without following links.
        path = raw_path.decode("utf-8", "surrogateescape")
        paths[path] = (mode, oid)
    return {"schema": SCHEMA, "commit": commit, "tree": tree, "paths": len(paths)}, paths


def default_kind(mode):
    return {"120000": "symlink", "160000": "submodule"}.get(mode, "unknown")


def write_inventory(args, header, paths):
    if args.out.is_symlink():
        raise ValueError("Provide a new regular ledger path, not a symlink.")
    out = args.out.resolve()
    git_dir = Path(os.fsdecode(git(args.repo, "rev-parse", "--absolute-git-dir").rstrip(b"\n")))
    protected = [git_dir.resolve()]
    common_dir = os.fsdecode(git(args.repo, "rev-parse", "--git-common-dir").rstrip(b"\n"))
    protected.append((args.repo / common_dir).resolve())
    bare = git(args.repo, "rev-parse", "--is-bare-repository").strip() == b"true"
    if not bare:
        top = os.fsdecode(git(args.repo, "rev-parse", "--show-toplevel").rstrip(b"\n"))
        protected.append(Path(top).resolve())
    if any(folder == out or folder in out.parents for folder in protected):
        raise ValueError("Use an output path in a separate review workspace.")
    # Exclusive creation preserves existing annotations. An interrupted inventory fails reconciliation.
    with out.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(header) + "\n")
        for path, (mode, oid) in paths.items():
            row = dict(path=path, mode=mode, oid=oid, kind=default_kind(mode), review="pending",
                       area="", evidence="", note="")
            stream.write(json.dumps(row, ensure_ascii=True) + "\n")
    return dict(commit=header["commit"], registered=len(paths), review="pending")


def parse(line, number):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise InvalidLedger("duplicate JSON key on line {}".format(number))
            obj[key] = value
        return obj
    try:
        row = json.loads(line, object_pairs_hook=unique)
    except json.JSONDecodeError as exc:
        raise InvalidLedger("invalid JSON on line {}".format(number)) from exc
    if not isinstance(row, dict):
        raise InvalidLedger("expected JSON object on line {}".format(number))
    return row


def review_state(row, mode, line_no):
    def fail(message):
        raise InvalidLedger("line {}: {}".format(line_no, message))
    for field in ("kind", "review", "area", "evidence", "note"):
        if not isinstance(row.get(field), str):
            fail("missing or invalid field " + field)
    kind, state = row["kind"], row["review"]
    if kind not in KINDS or state not in STATES:
        fail("unknown kind or review state")
    mode_kind = default_kind(mode)
    if mode_kind in ("submodule", "symlink") and kind != mode_kind:
        fail("kind disagrees with Git object mode")
    if kind in ("submodule", "symlink") and mode_kind != kind:
        fail("file has incompatible object kind")
    if state == "read" and kind not in TEXT:
        fail("read requires text or lfs-text")
    if state == "object" and kind not in OBJECTS:
        fail("object requires an inspected non-text object")
    if state in ("read", "object") and not all(row[k].strip() for k in ("area", "evidence")):
        fail("reviewed entries need an area and evidence locator")
    if state in ("object", "partial", "blocked") and not row["note"].strip():
        fail("describe the inspection, missing ranges or blocker")
    return state


def reconcile(args, header, paths):
    seen, counts = set(), Counter()
    with args.ledger.open(encoding="utf-8") as stream:
        if parse(stream.readline(), 1) != header:
            raise InvalidLedger("ledger header does not match this commit, tree or path count")
        for line_no, line in enumerate(stream, 2):
            row = parse(line, line_no)
            path = row.get("path")
            if not isinstance(path, str) or path not in paths or path in seen:
                raise InvalidLedger("missing, foreign or duplicate path on line {}".format(line_no))
            seen.add(path)
            if (row.get("mode"), row.get("oid")) != paths[path]:
                raise InvalidLedger("object identity mismatch on line {}".format(line_no))
            counts[review_state(row, paths[path][0], line_no)] += 1
    if len(seen) != len(paths):
        missing = next(p for p in paths if p not in seen)
        raise InvalidLedger("missing {} entries; first missing path is {}"
                            .format(len(paths) - len(seen), ascii(missing)))
    open_count = sum(counts[k] for k in ("pending", "partial", "blocked"))
    closed = bool(seen) and open_count == 0
    return dict(commit=header["commit"], registered=len(seen),
                counts={k: counts[k] for k in STATES}, ledger_closed=closed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    inv = sub.add_parser("inventory", help="start a new ledger outside the source repository")
    chk = sub.add_parser("check", help="check identities and review dispositions")
    for part in (inv, chk):
        part.add_argument("--repo", required=True, type=Path, help="local Git repository")
        part.add_argument("--ref", required=True, help="commit, tag or branch; prefer a full commit ID")
    inv.add_argument("--out", required=True, type=Path, help="new JSONL file; parent directory must exist")
    chk.add_argument("--ledger", required=True, type=Path)
    args = parser.parse_args()
    try:
        header, paths = object_tree(args.repo, args.ref)
        if args.action == "inventory":
            result, code = write_inventory(args, header, paths), 0
        else:
            result = reconcile(args, header, paths)
            code = 0 if result["ledger_closed"] else 1
    except (OSError, ValueError) as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
