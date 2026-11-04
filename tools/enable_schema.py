#!/usr/bin/env python3
"""Append the rime-gloss filter to an existing schema custom yaml.

Does not overwrite an existing rime_gloss_filter line.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SNIPPET = """  engine/filters/@next: lua_filter@rime_gloss_filter
  switches/@next: {options: [gloss_off, gloss_en, gloss_ja, gloss_both], states: [释义关, 英, 日, 双语], reset: 1}
  rime_gloss/default: en
"""


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


def enable(schema: str, rime_dir: Path) -> int:
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
        target.write_text(text + SNIPPET, encoding="utf-8")
        print(f"appended gloss patch: {target}")
        return 0
    target.write_text("# encoding: utf-8\npatch:\n" + SNIPPET, encoding="utf-8")
    print(f"created: {target}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Enable rime-gloss on one schema")
    parser.add_argument("--schema", default="rime_ice", help="schema id, e.g. rime_ice or luna_pinyin")
    parser.add_argument("--rime-dir", type=Path, default=None)
    args = parser.parse_args()
    rime_dir = args.rime_dir or default_rime_dir()
    print(f"rime dir: {rime_dir}")
    code = enable(args.schema, rime_dir)
    if code == 0:
        print("重新部署 Rime 后，在方案菜单切换 释义关 / 英 / 日 / 双语。")
    return code


if __name__ == "__main__":
    sys.exit(main())
