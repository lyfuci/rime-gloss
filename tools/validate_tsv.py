#!/usr/bin/env python3
"""Validate rime-gloss TSV files. Exit 1 on error."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "gloss" / "en.tsv", ROOT / "gloss" / "ja.tsv"]
MAX_GLOSS = 48


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    seen: dict[str, int] = {}
    text = path.read_text(encoding="utf-8")
    if text.startswith("﻿"):
        errors.append(f"{path.name}: unexpected UTF-8 BOM")
    for lineno, raw in enumerate(text.splitlines(), 1):
        if raw == "" or raw.startswith("#"):
            continue
        if "	" not in raw:
            errors.append(f"{path.name}:{lineno}: missing tab")
            continue
        parts = raw.split("	")
        if len(parts) not in (2, 3):
            errors.append(f"{path.name}:{lineno}: expected 2 or 3 columns, got {len(parts)}")
            continue
        word, gloss = parts[0].strip(), parts[1].strip()
        pos = parts[2].strip() if len(parts) == 3 else ""
        if not word or not gloss:
            errors.append(f"{path.name}:{lineno}: empty word or gloss")
        if any(ch.isspace() and ch != " " for ch in gloss):
            errors.append(f"{path.name}:{lineno}: gloss has unusual whitespace")
        if len(gloss) > MAX_GLOSS:
            errors.append(f"{path.name}:{lineno}: gloss longer than {MAX_GLOSS}: {word}")
        if pos and any(ch.isspace() and ch != " " and ch != "／" for ch in pos):
            errors.append(f"{path.name}:{lineno}: pos looks broken: {pos!r}")
        if word in seen:
            errors.append(f"{path.name}:{lineno}: duplicate {word!r} (also line {seen[word]})")
        else:
            seen[word] = lineno
    if not seen:
        errors.append(f"{path.name}: no entries")
    return errors


def main() -> int:
    errors: list[str] = []
    for path in FILES:
        if not path.exists():
            errors.append(f"missing {path}")
            continue
        errors.extend(validate(path))
    en = (ROOT / "gloss" / "en.tsv").read_text(encoding="utf-8")
    ja = (ROOT / "gloss" / "ja.tsv").read_text(encoding="utf-8")
    en_words = {line.split("	", 1)[0] for line in en.splitlines() if line and not line.startswith("#")}
    ja_words = {line.split("	", 1)[0] for line in ja.splitlines() if line and not line.startswith("#")}
    if en_words != ja_words:
        errors.append(f"en/ja headword mismatch only_en={sorted(en_words - ja_words)[:8]} only_ja={sorted(ja_words - en_words)[:8]}")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"ok en={len(en_words)} ja={len(ja_words)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
