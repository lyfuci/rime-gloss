#!/usr/bin/env python3
"""Send your own glosses back to the shared word lists, as a pull request.

Your corrections live in the Rime user directory, in gloss/user_<pair>.tsv
(they take effect locally on redeploy). This script merges them into this
repository's gloss/<pair>.tsv, so every install gets them:

- new words are appended under "# contributed", changed ones are replaced in place;
- a gloss of "-" hides a word (for example a wrong entry in an imported
  dictionary), for everyone once merged.

Only the lines of your user_*.tsv files are uploaded, nothing else. The
script shows them and asks before it creates a branch, commits, pushes and
opens a pull request (needs git and an authenticated gh).

  python3 tools/contribute.py --rime-dir "$APPDATA/Rime"            # preview, confirm, open a PR
  python3 tools/contribute.py --rime-dir "$APPDATA/Rime" --dry-run  # preview only
  python3 tools/contribute.py --rime-dir "$APPDATA/Rime" --no-pr    # only edit gloss/*.tsv here
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from enable_schema import default_rime_dir  # noqa: E402
from validate_tsv import validate_seed  # noqa: E402

PAIR = re.compile(r"^user_([a-z]{2,3}-[a-z]{2,3})\.tsv$")
HEADER = "# contributed"


def read_entries(text: str) -> dict[str, tuple[str, str]]:
    """text<TAB>gloss[<TAB>pos] lines, later lines win; comments and blanks skipped."""
    entries: dict[str, tuple[str, str]] = {}
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 2 or not parts[0] or not parts[1] or len(parts) > 3:
            raise ValueError(f"not text<TAB>gloss[<TAB>pos]: {line!r}")
        entries[parts[0]] = (parts[1], parts[2] if len(parts) == 3 else "")
    return entries


def format_line(key: str, gloss: str, pos: str) -> str:
    return f"{key}\t{gloss}\t{pos}" if pos else f"{key}\t{gloss}"


def merge_into_seed(seed_text: str, mine: dict[str, tuple[str, str]]) -> tuple[str, list[str], list[str]]:
    """The seed list with `mine` merged in: changed lines replaced where they
    are, new ones appended under '# contributed'. Returns (text, added, changed)."""
    lines = seed_text.splitlines()
    present: dict[str, int] = {}
    for i, line in enumerate(lines):
        if line and not line.startswith("#") and "\t" in line:
            present[line.split("\t", 1)[0].strip()] = i
    added, changed = [], []
    for key, (gloss, pos) in mine.items():
        new = format_line(key, gloss, pos)
        if key in present:
            if lines[present[key]].strip() != new:
                lines[present[key]] = new
                changed.append(key)
        else:
            added.append(key)
    if added:
        if HEADER not in lines:
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(HEADER)
        lines += [format_line(k, *mine[k]) for k in added]
    return "\n".join(lines) + "\n", added, changed


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=check)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rime-dir", type=Path, default=None, help="Rime user directory (default: detected)")
    parser.add_argument("--pair", action="append", default=[], help="only these pairs, e.g. zh-ja; repeatable")
    parser.add_argument("--dry-run", action="store_true", help="show what would be contributed, change nothing")
    parser.add_argument("--no-pr", action="store_true", help="edit gloss/*.tsv in this checkout, no git or GitHub")
    parser.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    args = parser.parse_args()

    rime_dir = args.rime_dir or default_rime_dir()
    files = sorted((rime_dir / "gloss").glob("user_*.tsv"))
    plan: list[tuple[str, str, list[str], list[str], dict]] = []
    for path in files:
        m = PAIR.match(path.name)
        if not m or (args.pair and m.group(1) not in args.pair):
            continue
        pair = m.group(1)
        try:
            mine = read_entries(path.read_text(encoding="utf-8-sig"))
        except ValueError as error:
            raise SystemExit(f"{path}: {error}")
        seed_path = ROOT / "gloss" / f"{pair}.tsv"
        seed = seed_path.read_text(encoding="utf-8") if seed_path.exists() else \
            f"# rime-gloss data — UTF-8 TSV\n# columns: text<TAB>gloss<TAB>pos\n# license: MIT (this project).\n"
        text, added, changed = merge_into_seed(seed, mine)
        if added or changed:
            plan.append((pair, text, added, changed, mine))
    if not plan:
        print(f"nothing to contribute: no new or changed lines in {rime_dir / 'gloss'}/user_*.tsv")
        return 0

    print("These lines from your user lists would be shared (MIT, in this repository):")
    for pair, _, added, changed, mine in plan:
        for kind, keys in (("+", added), ("~", changed)):
            for key in keys:
                gloss, pos = mine[key]
                print(f"  {pair} {kind} {key}\t{'(hide)' if gloss == '-' else format_line('', gloss, pos).strip()}")
    if args.dry_run:
        return 0
    if not args.yes and input("Contribute these glosses you wrote yourself? [y/N] ").strip().lower() not in ("y", "yes"):
        print("cancelled")
        return 1

    def write_all() -> None:
        for pair, text, _, _, _ in plan:
            path = ROOT / "gloss" / f"{pair}.tsv"
            path.write_text(text, encoding="utf-8", newline="\n")
            errors, _ = validate_seed(path)
            if errors:
                raise SystemExit("validation failed:\n" + "\n".join(errors))

    if args.no_pr:
        write_all()
        print("updated " + ", ".join(f"gloss/{p}.tsv" for p, *_ in plan))
        return 0

    if git("status", "--porcelain").stdout.strip():
        raise SystemExit("this checkout has uncommitted changes; commit or stash them first")
    original = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    git("fetch", "-q", "origin", "main")
    pairs = "-".join(p for p, *_ in plan)
    branch = f"contrib/{pairs}-{datetime.datetime.now():%Y%m%d-%H%M%S}"
    git("switch", "-q", "-c", branch, "origin/main")
    try:
        # Re-merge against the latest main, not the checkout we started from.
        for i, (pair, _, _, _, mine) in enumerate(plan):
            seed_path = ROOT / "gloss" / f"{pair}.tsv"
            seed = seed_path.read_text(encoding="utf-8") if seed_path.exists() else plan[i][1]
            plan[i] = (pair, merge_into_seed(seed, mine)[0], *plan[i][2:])
        write_all()
        count = sum(len(a) + len(c) for _, _, a, c, _ in plan)
        git("add", *[f"gloss/{p}.tsv" for p, *_ in plan])
        git("commit", "-q", "-m", f"Contribute {count} glosses ({', '.join(p for p, *_ in plan)})")
        push = git("push", "-q", "-u", "origin", branch, check=False)
        if push.returncode:
            raise SystemExit(f"push failed (no write access? fork the repository first):\n{push.stderr}")
        body = ["Glosses contributed from a user's own `gloss/user_<pair>.tsv` with `tools/contribute.py`.", "",
                "| Pair | Change | Word | Gloss |", "| --- | --- | --- | --- |"]
        for pair, _, added, changed, mine in plan:
            for kind, keys in (("added", added), ("changed", changed)):
                for key in keys:
                    gloss, pos = mine[key]
                    body.append(f"| {pair} | {kind} | {key} | {'(hidden)' if gloss == '-' else format_line('', gloss, pos).strip()} |")
        pr = subprocess.run(["gh", "pr", "create", "--base", "main", "--head", branch,
                             "--title", f"Contribute {count} glosses ({', '.join(p for p, *_ in plan)})",
                             "--body", "\n".join(body)], cwd=ROOT, capture_output=True, text=True)
        print(pr.stdout.strip() or pr.stderr.strip())
    finally:
        git("switch", "-q", original, check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
