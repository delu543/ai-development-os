"""Check local documentation and optionally build the public package. Python 3.8+."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SKILL = "ai-development-os"
EXAMPLE = "examples/calendar-audit.md"


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def tracked_files():
    paths = git("ls-files", "-z").decode("utf-8").split("\0")
    return [p for p in paths if p]


def verify(files):
    for name in ("README.md", "README.en.md", "CONTRIBUTING.md", "SECURITY.md", "CHANGELOG.md",
                 "CODE_OF_CONDUCT.md", "LICENSE", SKILL + "/LICENSE", EXAMPLE):
        if name not in files:
            raise ValueError("Missing tracked distribution file: " + name)
    if (ROOT / "LICENSE").read_bytes() != (ROOT / SKILL / "LICENSE").read_bytes():
        raise ValueError("Licenses in the repository and portable directory differ")
    modules = sorted(p for p in files if p.startswith(SKILL + "/references/") and p.endswith(".md"))
    if [Path(p).name[:2] for p in modules] != ["%02d" % i for i in range(16)]:
        raise ValueError("Expected review modules 00 through 15")
    links = 0
    for name in files:
        if not name.endswith(".md"):
            continue
        source = ROOT / name
        prose = re.sub(r"^```[^\n]*\n.*?^```[ \t]*$", "", source.read_text(encoding="utf-8"), flags=re.M | re.S)
        for ref in re.findall(r"\]\(([^()\s]+)\)", prose):
            link = urlsplit(ref)
            if link.scheme or link.netloc or not link.path:
                continue
            target = (source.parent / unquote(link.path)).resolve()
            if ROOT not in (target, *target.parents) or not target.exists():
                raise ValueError("{}: broken local link {}".format(name, ref))
            links += 1
    print("Checked 16 modules, matching licenses and {} local documentation links.".format(links))


def skill_zip(files):
    stream = io.BytesIO()
    # Store the small text payload directly for identical ZIP bytes across zlib versions.
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(p for p in files if p.startswith(SKILL + "/")):
            path = ROOT / name
            if not path.is_file() or path.is_symlink():
                raise ValueError("Expected a regular skill file: " + name)
            entry = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, path.read_bytes())
    return stream.getvalue()


def render_example(output):
    command = [sys.executable, str(ROOT / SKILL / "scripts/check_audit.py"), str(ROOT / EXAMPLE)]
    if output is not None:
        command += ["--html", str(output)]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.returncode != 1:
        raise ValueError("Expected a valid partial review: " + (result.stderr or result.stdout))
    verdict = json.loads(result.stdout)
    if verdict["modules"] != 16 or verdict["additional"] != 2 or not verdict["open"]:
        raise ValueError("Example module totals or open evidence changed. Recheck the published report.")


def build(files, destination):
    with tempfile.TemporaryDirectory() as tmp:
        rendered = Path(tmp) / "calendar-audit.html"
        render_example(rendered)
        assets = {"ai-development-os.zip": skill_zip(files), rendered.name: rendered.read_bytes()}
    checksums = ["{}  {}\n".format(hashlib.sha256(data).hexdigest(), name) for name, data in sorted(assets.items())]
    assets["SHA256SUMS"] = "".join(checksums).encode("utf-8")
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in assets.items():
        target = destination / name
        if target.is_symlink() or (target.exists() and target.read_bytes() != data):
            raise ValueError("Refusing to overwrite different output: " + str(target))
    for name, data in assets.items():
        path = destination / name
        if not path.exists():
            with path.open("xb") as out:
                out.write(data)
    print("Wrote release files to " + str(destination))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output-dir", type=Path, help="write the install ZIP, offline example and SHA256SUMS")
    options = cli.parse_args()
    files = tracked_files()
    verify(files)
    if options.output_dir is None:
        render_example(None)
    else:
        build(files, options.output_dir)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
