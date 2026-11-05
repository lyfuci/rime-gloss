#!/usr/bin/env python3
"""tools/contribute.py: merging, preview, and the git path against a local bare
'origin' (no GitHub; gh pr create is expected to fail there)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from contribute import merge_into_seed, read_entries  # noqa: E402

SEED = "# header\n学习\tstudy/learn\tv.\n\n# school\n学校\tschool\tn.\n"

text, added, changed = merge_into_seed(SEED, {"学校": ("school", "n."), "学习": ("to study", "v."), "洗雪": ("-", ""), "西学": ("Western learning", "n.")})
assert changed == ["学习"] and added == ["洗雪", "西学"], (added, changed)
assert text == "# header\n学习\tto study\tv.\n\n# school\n学校\tschool\tn.\n\n# contributed\n洗雪\t-\n西学\tWestern learning\tn.\n", repr(text)
again, added2, changed2 = merge_into_seed(text, {"洗雪": ("-", ""), "猫": ("cat", "n.")})
assert added2 == ["猫"] and not changed2 and again.count("# contributed") == 1 and again.endswith("西学\tWestern learning\tn.\n猫\tcat\tn.\n")
assert read_entries("# c\n\na\tA\na\tB\tn.\n") == {"a": ("B", "n.")}, "later lines win"
try:
    read_entries("broken line\n")
    raise AssertionError("malformed line accepted")
except ValueError:
    pass


def run(cwd: Path, *args: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(cwd / "tools" / "contribute.py"), *args], input=stdin,
                          capture_output=True, text=True, cwd=cwd)


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True).stdout


with tempfile.TemporaryDirectory() as tmp:
    t = Path(tmp)
    # A copy of the repository's tools and seed lists, with a bare 'origin'.
    repo = t / "repo"
    (repo / "gloss").mkdir(parents=True)
    shutil.copytree(ROOT / "tools", repo / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    (repo / "gloss" / "zh-ja.tsv").write_text(SEED, encoding="utf-8")
    shutil.copy2(ROOT / ".gitignore", repo / ".gitignore")
    git(t, "init", "-q", "-b", "main", str(repo))
    git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "add", ".")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "init")
    git(t, "init", "-q", "--bare", str(t / "origin.git"))
    git(repo, "remote", "add", "origin", str(t / "origin.git"))
    git(repo, "push", "-q", "origin", "main")

    rime = t / "Rime"
    (rime / "gloss").mkdir(parents=True)
    (rime / "gloss" / "user_zh-ja.tsv").write_text("# mine\n洗雪\t-\n学习\t学ぶ\t動\n学校\tschool\tn.\n", encoding="utf-8")

    preview = run(repo, "--rime-dir", str(rime), "--dry-run")
    assert preview.returncode == 0 and "zh-ja + 洗雪\t(hide)" in preview.stdout and "zh-ja ~ 学习\t動 学ぶ" not in preview.stdout, preview.stdout
    assert "zh-ja ~ 学习\t学ぶ\t動" in preview.stdout and "学校" not in preview.stdout, preview.stdout
    assert (repo / "gloss" / "zh-ja.tsv").read_text(encoding="utf-8") == SEED, "dry run changes nothing"

    no = run(repo, "--rime-dir", str(rime), stdin="n\n")
    assert no.returncode == 1 and "cancelled" in no.stdout and not git(repo, "status", "--porcelain")

    # The full path: branch from origin/main, commit, push; gh fails without GitHub.
    git(repo, "config", "user.name", "t")
    git(repo, "config", "user.email", "t@example.invalid")
    done = run(repo, "--rime-dir", str(rime), "--yes")
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip() == "main", "back on the original branch"
    assert not git(repo, "status", "--porcelain"), "nothing left behind"
    branches = [b.strip() for b in git(t / "origin.git", "branch", "--list", "contrib/*").splitlines()]
    assert len(branches) == 1 and branches[0].startswith("contrib/zh-ja-"), (branches, done.stdout, done.stderr)
    pushed = git(t / "origin.git", "show", f"{branches[0]}:gloss/zh-ja.tsv")
    assert pushed.endswith("# contributed\n洗雪\t-\n") and "学习\t学ぶ\t動\n" in pushed, pushed

    nothing = run(repo, "--rime-dir", str(rime), "--no-pr", "--yes")
    assert nothing.returncode == 0 and "updated gloss/zh-ja.tsv" in nothing.stdout, "main still lacks the lines until the PR merges"

    (rime / "gloss" / "user_zh-ja.tsv").write_text("坏行\n", encoding="utf-8")
    assert run(repo, "--rime-dir", str(rime), "--dry-run").returncode != 0, "malformed user lines refused"

print("contribute_test: ok")
