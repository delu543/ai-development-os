"""Isolated regression cases for the shipped coverage helper."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

REPOSITORY = Path(__file__).resolve().parent.parent
TOOL = REPOSITORY / "ai-development-os/scripts/repo_coverage.py"
root = Path(tempfile.mkdtemp(prefix="ai-development-os-coverage-"))
repo = root / "source"
repo.mkdir()
env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
passed = []


def git(*args):
    return subprocess.run(["git", "-C", str(repo), "-c", "core.hooksPath=/dev/null",
                           "-c", "commit.gpgSign=false", "-c", "user.name=Fixture",
                           "-c", "user.email=fixture@example.invalid", *args],
                          env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, check=True).stdout.strip()


def command(name, args, expected, extra_env=None):
    run = subprocess.run([sys.executable, str(TOOL), *map(str, args)], env=dict(env, **(extra_env or {})),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert run.returncode == expected, (name, run.returncode, run.stdout, run.stderr)
    passed.append(name)
    return json.loads(run.stdout) if run.stdout else {}


def save(name, rows):
    p = root / (name + ".jsonl")
    with p.open("x", encoding="utf-8") as fh:
        for row in rows:
            print(json.dumps(row, ensure_ascii=True), file=fh)
    return p


git("init", "-q")
git("commit", "--allow-empty", "-qm", "Empty tree")
empty = git("rev-parse", "HEAD")
(repo / "A.txt").write_text("one\n")
(repo / "中 文\n\t档.txt").write_text("two\n")
(repo / ".hidden").write_text("hidden\n")
(repo / "bin.dat").write_bytes(b"\0\2\6")
(repo / "symbol").symlink_to("../unavailable")
(repo / "pointer").write_text("version https://git-lfs.github.com/spec/v1\noid sha256:" + "7"*64 + "\nsize 9000\n")
(repo / "nested").mkdir()
(repo / "nested" / "run").write_text("#!/bin/sh\nexit 0\n")
(repo / "nested" / "run").chmod(0o755)
(repo / "leading-hyphen-sample").write_bytes(b"x")
git("add", "--", ".")
git("update-index", "--add", "--cacheinfo", "160000," + empty + ",linked-module")
git("commit", "-qm", "Tree sample")
sha = git("rev-parse", "HEAD")
(repo / "untracked").write_text("untracked")
(repo / "A.txt").write_text("dirty\n")
original = root / "original.jsonl"


def inv(target, ref=sha, directory=repo):
    return ["inventory", "--repo", directory, "--ref", ref, "--out", target]


def check(ledger, ref=sha, directory=repo):
    return ["check", "--repo", directory, "--ref", ref, "--ledger", ledger]


result = command("inventory-fixed-tree", inv(original), 0)
assert result["registered"] == 9
rows = [json.loads(s) for s in original.read_text().splitlines()]
assert set(r["path"] for r in rows[1:]) == {
    "A.txt", "中 文\n\t档.txt", ".hidden", "bin.dat", "symbol", "pointer",
    "nested/run", "leading-hyphen-sample", "linked-module"}
assert next(r for r in rows[1:] if r["path"]=="nested/run")["mode"] == "100755"
assert next(r for r in rows[1:] if r["path"]=="A.txt")["oid"] == git("rev-parse", sha + ":A.txt")
r = command("pending-exit-and-count", check(original), 1)
assert r["counts"]["pending"] == 9
command("preserve-existing-ledger", inv(original), 2)
command("refuse-in-tree-write", inv(repo / "ledger.jsonl"), 2)
command("refuse-in-git-write", inv(repo / ".git/new-ledger.jsonl"), 2)
dangling = root / "dangling"
dangling.symlink_to(root / "should-not-be-created")
command("refuse-symlink-output", inv(dangling), 2)
assert not (root / "should-not-be-created").exists()
command("full-tree-from-subdir", check(original, directory=repo/"nested"), 1)
command("isolate-inherited-git-dir", check(original), 1, {"GIT_DIR":str(root/"missing-repo")})

new = [dict(r) for r in rows]
for r in new[1:]:
    r.update(area="fixture", review="read", kind="text", evidence="review-note L1 to EOF")
    if r["path"] in ("linked-module", "symbol", "bin.dat"):
        kind = {"symbol":"symlink", "bin.dat":"binary", "linked-module":"submodule"}[r["path"]]
        r.update(review="object", kind=kind, note="synthetic inspection record")
    if r["path"] == "pointer":
        r.update(review="blocked", kind="lfs-text", note="fixture LFS content absent")
blocked = save("blocked",new)
r = command("blocked-lfs-stays-open", check(blocked), 1)
assert r["counts"]["blocked"] == 1
ptr = next(r for r in new[1:] if r["path"]=="pointer")
ptr.update(review="partial", note="only the pointer is available")
r = command("partial-content-stays-open", check(save("partial",new)), 1)
assert r["counts"]["partial"] == 1
# Deliberately synthetic completion annotations exercise only the schema and identity rules.
ptr.update(review="read", note="synthetic ledger test", evidence="synthetic E-1")
closed = save("closed",new)
r = command("closed-ledger-shape", check(closed), 0)
assert r["ledger_closed"] and r["counts"]["read"] == 6 and r["counts"]["object"] == 3
command("missing-row", check(save("missing",new[:-1])), 2)
command("duplicate-row", check(save("duplicate",new+[dict(new[-1])])), 2)
for field, value in (("path","foreign"),("mode","000000"),("oid","0"*40),
                     ("review","passed"),("kind","submodule"),("evidence","")):
    bad=[dict(r) for r in new]
    row=next(r for r in bad[1:] if r["path"] == "A.txt")
    row[field]=value
    command("invalid-"+field,check(save("bad-"+field,bad)),2)
bad=[dict(r) for r in new]
row=next(r for r in bad[1:] if r["path"]=="A.txt")
row.update(review="object", note="metadata only")
command("metadata-only-text-cannot-close", check(save("fake-text",bad)), 2)
badpath=root/"broken.jsonl"
badpath.write_text('{"invalid":1,"invalid":2}\n')
command("duplicate-json-key", check(badpath), 2)
badpath=root/"truncated.jsonl"
badpath.write_text('{"schema":\n')
command("truncated-json", check(badpath), 2)
command("commit-mismatch", check(closed, ref=empty), 2)
command("unknown-ref", check(closed, ref="missing-ref"), 2)
emptyfile = root/"empty.jsonl"
command("empty-tree-inventory", inv(emptyfile,ref=empty),0)
r=command("empty-tree-is-not-reviewed", check(emptyfile,ref=empty),1)
assert r["registered"] == 0 and not r["ledger_closed"]
subprocess.run(["git","clone","--bare","-q",str(repo),str(root/"bare.git")],env=env,check=True)
command("bare-snapshot", check(closed,directory=root/"bare.git"),0)
command("bare-write-protection", inv(root/"bare.git"/"notes.jsonl",directory=root/"bare.git"),2)
git("worktree","add","-q","--detach",str(root/"linked"),sha)
command("linked-worktree", check(closed,directory=root/"linked"),0)
command("linked-common-dir-protection", inv(repo/".git"/"more.jsonl",directory=root/"linked"),2)
# Build this tree directly. Some filesystems forbid non-UTF-8 names in a checkout.
obj = git("rev-parse", sha + ":A.txt")
raw_tree = subprocess.run(["git","-C",str(repo),"mktree","-z"],
                          input=b"100644 blob "+obj.encode()+b"\titem_\xff\0",
                          stdout=subprocess.PIPE,check=True,env=env).stdout.strip().decode()
odd_sha = git("commit-tree",raw_tree,"-m","Non-UTF8 tree")
odd_ledger = root/"bytes.jsonl"
command("non-utf8-git-path", inv(odd_ledger,ref=odd_sha),0)
assert json.loads(odd_ledger.read_text().splitlines()[1])["path"] == "item_\udcff"
assert not (repo/"ledger.jsonl").exists()
print(json.dumps({"cases":len(passed),"passed":passed,"evidence_dir":str(root)},ensure_ascii=False))
