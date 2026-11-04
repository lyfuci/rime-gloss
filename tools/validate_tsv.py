#!/usr/bin/env python3
"""Validate rime-gloss data. Exit 1 on error.

- gloss/<src>-<tgt>.tsv: hand-written seed lists (short, unique headwords).
- gloss/dict/<src>-<tgt>.tsv: imported dictionaries. Besides the line format
  they must be byte-sorted with unique keys and no comments, because the
  filter binary-searches them on disk.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAIR = re.compile(r"^[a-z]{2,3}-[a-z]{2,3}$")
MAX_SEED_GLOSS = 48
MAX_DICT_LINE = 512


def check_line(name: str, lineno: int, raw: str, errors: list[str], max_gloss: int | None) -> str | None:
    parts = raw.split("\t")
    if len(parts) not in (2, 3):
        errors.append(f"{name}:{lineno}: expected 2 or 3 tab-separated columns, got {len(parts)}")
        return None
    word, gloss = parts[0].strip(), parts[1].strip()
    pos = parts[2].strip() if len(parts) == 3 else ""
    if not word or not gloss:
        errors.append(f"{name}:{lineno}: empty text or gloss")
        return None
    if word != parts[0]:
        errors.append(f"{name}:{lineno}: text has surrounding spaces")
    if any(ch.isspace() and ch != " " for ch in gloss + pos):
        errors.append(f"{name}:{lineno}: unusual whitespace in gloss or pos")
    if max_gloss and len(gloss) > max_gloss:
        errors.append(f"{name}:{lineno}: gloss longer than {max_gloss}: {word}")
    return word


def validate_seed(path: Path) -> tuple[list[str], int]:
    errors: list[str] = []
    seen: dict[str, int] = {}
    text = path.read_text(encoding="utf-8")
    if text.startswith("﻿"):
        errors.append(f"{path.name}: unexpected UTF-8 BOM")
    for lineno, raw in enumerate(text.splitlines(), 1):
        if raw == "" or raw.startswith("#"):
            continue
        word = check_line(path.name, lineno, raw, errors, MAX_SEED_GLOSS)
        if word is None:
            continue
        if word in seen:
            errors.append(f"{path.name}:{lineno}: duplicate {word!r} (also line {seen[word]})")
        else:
            seen[word] = lineno
    if not seen:
        errors.append(f"{path.name}: no entries")
    return errors, len(seen)


def validate_dict(path: Path) -> tuple[list[str], int]:
    errors: list[str] = []
    data = path.read_bytes()
    name = f"dict/{path.name}"
    if data.startswith(b"\xef\xbb\xbf"):
        errors.append(f"{name}: unexpected UTF-8 BOM")
    if b"\r" in data:
        errors.append(f"{name}: CR line endings (binary search expects LF)")
    previous: bytes | None = None
    count = 0
    for lineno, raw in enumerate(data.split(b"\n"), 1):
        if raw == b"":
            continue
        if len(raw) > MAX_DICT_LINE:
            errors.append(f"{name}:{lineno}: line longer than {MAX_DICT_LINE} bytes")
        try:
            line = raw.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"{name}:{lineno}: not UTF-8")
            continue
        if line.startswith("#"):
            errors.append(f"{name}:{lineno}: comments are not allowed in sorted dictionaries")
            continue
        if check_line(name, lineno, line, errors, None) is None:
            continue
        key = raw.split(b"\t", 1)[0]
        if previous is not None and key <= previous:
            kind = "duplicate key" if key == previous else "not byte-sorted"
            errors.append(f"{name}:{lineno}: {kind} at {line.split(chr(9), 1)[0]!r}")
            if len(errors) > 20:
                break
        previous = key
        count += 1
    if count == 0:
        errors.append(f"{name}: no entries")
    return errors, count


def main() -> int:
    errors: list[str] = []
    summary: list[str] = []
    seeds = sorted(p for p in (ROOT / "gloss").glob("*.tsv") if not p.name.startswith("user_"))
    if not seeds:
        errors.append("no seed lists in gloss/")
    for path in seeds:
        if not PAIR.match(path.stem):
            errors.append(f"{path.name}: name must be <source>-<target>.tsv, e.g. zh-en.tsv")
            continue
        found, n = validate_seed(path)
        errors.extend(found)
        summary.append(f"{path.stem}={n}")
    for path in sorted((ROOT / "gloss" / "dict").glob("*.tsv")):
        if not PAIR.match(path.stem):
            errors.append(f"dict/{path.name}: name must be <source>-<target>.tsv")
            continue
        found, n = validate_dict(path)
        errors.extend(found)
        summary.append(f"dict/{path.stem}={n}")
    if errors:
        print("\n".join(errors))
        return 1
    print("ok " + " ".join(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
