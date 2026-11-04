#!/usr/bin/env python3
"""End-to-end test with the real librime and librime-lua.

Installs the package into a fresh Rime user directory exactly as the plum
recipes list it, deploys, types pinyin and checks the candidate comments.

usage: run_e2e.py --probe PATH --shared DIR --plugin PATH/librime-lua.so
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def section(text: str, name: str) -> list[str]:
    """plum's print_section: the lines after a top-level `name:` up to the next
    line that starts with neither whitespace nor '#'."""
    lines, inside = [], False
    for line in text.splitlines():
        if inside and line and not line[0].isspace() and line[0] != "#":
            break
        if inside:
            lines.append(line)
        elif line.startswith(name + ":"):
            inside = True
    return lines


def recipe_files(name: str) -> list[str]:
    """The files `rime-install lyfuci/rime-gloss[:name]` copies, by plum's rules
    (scripts/recipe.sh): Rx must equal the requested name, install_files must
    be top-level, patterns are globbed from the package root."""
    path = ROOT / (f"{name}.recipe.yaml" if name else "recipe.yaml")
    text = path.read_text(encoding="utf-8")
    rx = next((l.split("Rx:", 1)[1].strip().strip("'\"") for l in section(text, "recipe") if l.strip().startswith("Rx: ")), "")
    assert not name or rx == name, f"{path.name}: plum rejects it, Rx {rx!r} does not match {name!r}"
    patterns = [l.strip().removeprefix("- ") for l in section(text, "install_files") if l.strip() and not l.strip().startswith("#")]
    patterns = [w for p in patterns for w in p.split()]
    assert patterns, f"{path.name}: plum installs nothing (no top-level install_files)"
    files = []
    for pattern in patterns:
        matched = sorted(str(m.relative_to(ROOT)) for m in ROOT.glob(pattern) if m.is_file())
        assert matched, f"{path.name}: {pattern} matches no file"
        files += matched
    return files


def install(user: Path, *names: str) -> None:
    for name in names:
        for rel in recipe_files(name):
            (user / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, user / rel)


def probe(args: argparse.Namespace, user: Path, schema: str, keys: str, **options: bool) -> dict[str, str]:
    cmd = [args.probe, args.shared, str(user), schema, keys, *(f"{k}={int(v)}" for k, v in options.items())]
    env = {**os.environ, "RIME_PROBE_LUA_PLUGIN": args.plugin}
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)
    errors = [line for line in result.stderr.splitlines() if "lua" in line.lower() or "schema" in line.lower()]
    assert result.returncode == 0 and not errors, f"{schema} {keys}: rc={result.returncode}\n{result.stderr[-2000:]}"
    out = {}
    for line in result.stdout.splitlines():
        text, _, comment = line.partition("\t")
        out.setdefault(text, comment)
    assert out, f"{schema} {keys}: no candidates\n{result.stderr[-2000:]}"
    return out


def eq(actual: str | None, expected: str, what: str) -> None:
    assert actual == expected, f"{what}: expected {expected!r}, got {actual!r}"


def radio(selected: str) -> dict[str, bool]:
    # The switch is a radio group; the frontend's menu clears the others.
    return {o: o == selected for o in ("gloss_off", "gloss_en", "gloss_ja", "gloss_all")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", required=True)
    parser.add_argument("--shared", required=True)
    parser.add_argument("--plugin", required=True)
    parser.add_argument("--installed", type=Path, help="a user dir already filled by the real plum: "
                        "rime-install lyfuci/rime-gloss lyfuci/rime-gloss:dict-zh-en lyfuci/rime-gloss:dict-zh-ja")
    parser.add_argument("--jaroomaji", type=Path, help="a checkout of lazyfoxchan/rime-jaroomaji: also test Japanese input")
    args = parser.parse_args()

    # Every recipe is valid for plum.
    recipe_files("")
    for path in sorted(ROOT.glob("*.recipe.yaml")):
        recipe_files(path.name.removesuffix(".recipe.yaml"))

    with tempfile.TemporaryDirectory() as tmp:
        # 1. Default recipe + zh-en dictionary, demo schema.
        user = Path(tmp) / "demo"
        if args.installed:
            shutil.copytree(args.installed, user)
            for rel in recipe_files("") + recipe_files("dict-zh-en") + recipe_files("dict-zh-ja"):
                assert (user / rel).is_file(), f"plum did not install {rel}"
        else:
            user.mkdir()
            install(user, "", "dict-zh-en", "dict-zh-ja")
        (user / "default.custom.yaml").write_text("patch:\n  schema_list:\n    - schema: rime_gloss_luna\n", encoding="utf-8")

        out = probe(args, user, "rime_gloss_luna", "xuexi")
        eq(out.get("学习"), "v. study/learn", "demo schema starts simplified, English seed gloss")
        out = probe(args, user, "rime_gloss_luna", "xuexi", **radio("gloss_ja"))
        eq(out.get("学习"), "動 学ぶ／勉強する", "Japanese")
        out = probe(args, user, "rime_gloss_luna", "xuexi", **radio("gloss_all"))
        eq(out.get("学习"), "en: v. study/learn · ja: 動 学ぶ／勉強する", "all targets")
        out = probe(args, user, "rime_gloss_luna", "xuexi", **radio("gloss_off"))
        eq(out.get("学习"), "", "off")
        out = probe(args, user, "rime_gloss_luna", "diannao", **radio("gloss_en"))
        eq(out.get("电脑"), "n. computer", "seed")
        out = probe(args, user, "rime_gloss_luna", "xueqi", **radio("gloss_en"))
        assert out.get("血气", "") or out.get("学期", ""), f"a dictionary-only word has a gloss: {out}"
        # Not in the seed list: comes from the derived zh-ja dictionary.
        out = probe(args, user, "rime_gloss_luna", "jingji", **radio("gloss_ja"))
        eq(out.get("经济"), "名 経済 けいざい", "derived zh-ja dictionary")
        print("demo schema: ok")

        # 2. The recommended route: enable on an existing schema with the script.
        user = Path(tmp) / "existing"
        user.mkdir()
        install(user, "", "dict-zh-en")
        (user / "default.custom.yaml").write_text("patch:\n  schema_list:\n    - schema: luna_pinyin\n", encoding="utf-8")
        (user / "luna_pinyin.custom.yaml").write_text("patch:\n  switches/@2/reset: 1\n", encoding="utf-8")
        enable = subprocess.run([sys.executable, str(ROOT / "tools" / "enable_schema.py"), "--schema", "luna_pinyin",
                                 "--source", "zh", "--targets", "en", "--rime-dir", str(user)], capture_output=True, text=True)
        assert enable.returncode == 0, enable.stderr
        out = probe(args, user, "luna_pinyin", "xuexi")
        eq(out.get("学习"), "v. study/learn", "enabled on luna_pinyin, default target")
        out = probe(args, user, "luna_pinyin", "nihao", gloss_off=False, gloss_en=True)
        assert out.get("你好"), f"你好 has a gloss: {out}"
        print("enable_schema on luna_pinyin: ok")

        # 3. Japanese input: jaroomaji + the ja-en dictionary.
        if args.jaroomaji:
            user = Path(tmp) / "japanese"
            user.mkdir()
            for f in args.jaroomaji.glob("*.yaml"):
                shutil.copy2(f, user / f.name)
            install(user, "", "dict-ja-en")
            (user / "default.custom.yaml").write_text("patch:\n  schema_list:\n    - schema: jaroomaji\n", encoding="utf-8")
            enable = subprocess.run([sys.executable, str(ROOT / "tools" / "enable_schema.py"), "--schema", "jaroomaji",
                                     "--source", "ja", "--targets", "en", "--rime-dir", str(user)], capture_output=True, text=True)
            assert enable.returncode == 0, enable.stderr
            # jaroomaji starts in ASCII mode.
            out = probe(args, user, "jaroomaji", "taberu", ascii_mode=False)
            eq(out.get("食べる"), "v. to eat", "Japanese verb")
            out = probe(args, user, "jaroomaji", "neko", ascii_mode=False)
            eq(out.get("猫"), "n. cat; feline", "Japanese noun")
            eq(out.get("ネコ"), "n. cat; feline", "katakana falls back to the hiragana reading")
            out = probe(args, user, "jaroomaji", "arigatou", ascii_mode=False)
            eq(out.get("ありがとう"), "int. thank you; thanks", "kana word")
            print("jaroomaji: ok")

    print("e2e: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
