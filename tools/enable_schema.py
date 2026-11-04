#!/usr/bin/env python3
"""Append the rime-gloss filter to an existing schema custom yaml.

Does not overwrite an existing rime_gloss_filter line.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

LABELS = {"en": "英", "ja": "日", "zh": "中", "ko": "韩", "fr": "法", "de": "德", "es": "西", "ru": "俄"}


def snippet(source: str, targets: list[str]) -> str:
    """The patch lines for one schema: filter, switch and language config."""
    options = ["gloss_off", *(f"gloss_{t}" for t in targets)]
    states = ["释义关", *(LABELS.get(t, t) for t in targets)]
    if len(targets) > 1:
        options.append("gloss_all")
        states.append("全部")
    return (
        "  engine/filters/@next: lua_filter@rime_gloss_filter\n"
        f"  switches/@next: {{options: [{', '.join(options)}], states: [{', '.join(states)}], reset: 1}}\n"
        f"  rime_gloss/source: {source}\n"
        f"  rime_gloss/targets: [{', '.join(targets)}]\n"
    )


def default_rime_dir() -> Path:
    if os.name == "nt" or os.environ.get("APPDATA"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Rime"
    mac = Path.home() / "Library" / "Rime"
    if mac.exists():
        return mac
    xdg = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    for candidate in (xdg / "fcitx5" / "rime", xdg / "ibus-rime"):
        if candidate.exists():
            return candidate
    return xdg / "fcitx5" / "rime"


def enable(schema: str, rime_dir: Path, text_snippet: str) -> int:
    rime_dir.mkdir(parents=True, exist_ok=True)
    target = rime_dir / f"{schema}.custom.yaml"
    if target.exists():
        text = target.read_text(encoding="utf-8")
        if "rime_gloss_filter" in text:
            print(f"already enabled: {target}")
            return 0
        if not any(line.split("#", 1)[0].strip() == "patch:" for line in text.splitlines()):
            print(f"{target} has no top-level patch:; not modified", file=sys.stderr)
            return 2
        if not text.endswith("\n"):
            text += "\n"
        target.write_text(text + text_snippet, encoding="utf-8")
        print(f"appended gloss patch: {target}")
        return 0
    target.write_text("# encoding: utf-8\npatch:\n" + text_snippet, encoding="utf-8")
    print(f"created: {target}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Enable rime-gloss on one schema")
    parser.add_argument("--schema", default="rime_ice", help="schema id, e.g. rime_ice or luna_pinyin")
    parser.add_argument("--source", default="zh", help="input language of the schema's candidates: zh, ja, en, ...")
    parser.add_argument("--targets", default="en,ja", help="comma-separated target languages, e.g. en,ja")
    parser.add_argument("--rime-dir", type=Path, default=None)
    args = parser.parse_args()
    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    if not targets or args.source in targets:
        parser.error("--targets needs at least one language other than --source")
    rime_dir = args.rime_dir or default_rime_dir()
    print(f"rime dir: {rime_dir}")
    code = enable(args.schema, rime_dir, snippet(args.source, targets))
    if code == 0:
        print("重新部署 Rime 后，在方案菜单切换释义开关。")
    return code


if __name__ == "__main__":
    sys.exit(main())
