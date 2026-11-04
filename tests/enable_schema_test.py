#!/usr/bin/env python3
"""tools/enable_schema.py: new file, append to an existing patch, no double append, refusal cases."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "enable_schema.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


with tempfile.TemporaryDirectory() as tmp:
    rime = Path(tmp)
    assert run("--schema", "melt_eng", "--source", "en", "--targets", "zh", "--rime-dir", tmp).returncode == 0
    text = (rime / "melt_eng.custom.yaml").read_text(encoding="utf-8")
    assert text.startswith("# encoding: utf-8\npatch:\n"), text
    assert "options: [gloss_off, gloss_zh], states: [释义关, 中]" in text, text
    assert "gloss_all" not in text, "one target needs no all state"
    assert "rime_gloss/source: en" in text and "rime_gloss/targets: [zh]" in text

    existing = rime / "rime_ice.custom.yaml"
    existing.write_text("patch:\n  menu/page_size: 7", encoding="utf-8")
    assert run("--schema", "rime_ice", "--rime-dir", tmp).returncode == 0
    text = existing.read_text(encoding="utf-8")
    assert text.startswith("patch:\n  menu/page_size: 7\n"), "existing patch kept"
    assert "options: [gloss_off, gloss_en, gloss_ja, gloss_all], states: [释义关, 英, 日, 全部]" in text, text
    assert run("--schema", "rime_ice", "--rime-dir", tmp).returncode == 0
    assert existing.read_text(encoding="utf-8") == text, "second run does not append again"

    nopatch = rime / "luna_pinyin.custom.yaml"
    nopatch.write_text("foo: 1\n", encoding="utf-8")
    assert run("--schema", "luna_pinyin", "--rime-dir", tmp).returncode == 2
    assert nopatch.read_text(encoding="utf-8") == "foo: 1\n", "no top-level patch: left untouched"

    assert run("--source", "zh", "--targets", "zh", "--rime-dir", tmp).returncode != 0, "target equal to source refused"

print("enable_schema_test: ok")
