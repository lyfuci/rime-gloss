#!/usr/bin/env python3
"""tools/build_dicts.py on small synthetic inputs in each format. No network."""

from __future__ import annotations

import gzip
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "build_dicts.py"

CEDICT = """# CC-CEDICT sample
學習 学习 [xue2 xi2] /to learn/to study/CL:個|个[ge4]/
張 张 [Zhang1] /surname Zhang/
張 张 [zhang1] /to open up/to spread/CL:個|个[ge4]/
个 个 [ge4] /variant of 個|个[ge4]/
電腦 电脑 [dian4 nao3] /computer/CL:臺|台[tai2]/
"""

JMDICT = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE JMdict [
<!ELEMENT JMdict (entry*)>
<!ENTITY n "noun (common) (futsuumeishi)">
<!ENTITY v5m "Godan verb with 'mu' ending">
<!ENTITY int "interjection (kandoushi)">
<!ENTITY uk "word usually written using kana alone">
]>
<JMdict>
<entry><k_ele><keb>学ぶ</keb><ke_pri>ichi1</ke_pri></k_ele><r_ele><reb>まなぶ</reb><re_pri>ichi1</re_pri></r_ele>
<sense><pos>&v5m;</pos><gloss>to study</gloss><gloss>to learn</gloss></sense></entry>
<entry><k_ele><keb>橋</keb><ke_pri>news1</ke_pri></k_ele><r_ele><reb>はし</reb><re_pri>news1</re_pri></r_ele>
<sense><pos>&n;</pos><gloss>bridge</gloss></sense></entry>
<entry><k_ele><keb>嘴</keb></k_ele><r_ele><reb>はし</reb></r_ele>
<sense><pos>&n;</pos><misc>&uk;</misc><gloss>beak</gloss></sense></entry>
<entry><k_ele><keb>端</keb></k_ele><r_ele><reb>はし</reb></r_ele>
<sense><pos>&n;</pos><gloss>end (e.g. of street)</gloss></sense></entry>
<entry><k_ele><keb>有難う</keb></k_ele><r_ele><reb>ありがとう</reb><re_pri>spec1</re_pri></r_ele>
<sense><pos>&int;</pos><misc>&uk;</misc><gloss>thank you</gloss></sense></entry>
</JMdict>
"""

ECDICT = """word,phonetic,definition,translation,pos,collins,oxford,tag,bnc,frq,exchange,detail,audio
apple,'æpl,n. fruit,n. 苹果\\n[医] 苹果,,5,1,zk gk,1000,900,,,
study,'stʌdi,,vt. 学习；研究\\nn. 学习,,5,1,zk,500,400,,,
obscureword,,,n. 罕见词,,0,0,,90000,90000,,,
taken,,,a. 被占用的,,0,0,,0,30000,,,
"""

TSV = "# my words\nzebra\tmy zebra\tn.\napple\tmy apple\tn.\n"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def read(path: Path) -> dict[str, tuple[str, ...]]:
    lines = path.read_bytes().split(b"\n")
    assert lines[-1] == b"", "ends with a newline"
    keys = [line.split(b"\t", 1)[0] for line in lines[:-1]]
    assert keys == sorted(keys) and len(keys) == len(set(keys)), f"{path.name} is byte-sorted and unique"
    return {line.split("\t")[0]: tuple(line.split("\t")[1:]) for line in path.read_text(encoding="utf-8").splitlines()}


with tempfile.TemporaryDirectory() as tmp:
    t = Path(tmp)
    (t / "cedict.txt.gz").write_bytes(gzip.compress(CEDICT.encode()))
    (t / "JMdict_e.gz").write_bytes(gzip.compress(JMDICT.encode()))
    with zipfile.ZipFile(t / "ecdict.zip", "w") as z:
        z.writestr("ecdict.csv", ECDICT)
    (t / "mine.tsv").write_text(TSV, encoding="utf-8")
    config = t / "dicts.toml"
    config.write_text(f"""
[[source]]
name = "cc-cedict"
pair = "zh-en"
format = "cedict"
url = "{t / 'cedict.txt.gz'}"
license = "CC BY-SA 4.0"
attribution = "CC-CEDICT"

[[source]]
name = "jmdict"
pair = "ja-en"
format = "jmdict"
url = "{t / 'JMdict_e.gz'}"
license = "CC BY-SA 4.0"

[[source]]
name = "mine"
pair = "en-zh"
format = "tsv"
url = "{t / 'mine.tsv'}"
license = "mine"

[[source]]
name = "ecdict"
pair = "en-zh"
format = "ecdict"
url = "{t / 'ecdict.zip'}"
license = "MIT"
""", encoding="utf-8")
    out = t / "out"
    result = run("--config", str(config), "--out", str(out), "--cache", str(t / "cache"))
    assert result.returncode == 0, result.stderr

    zh = read(out / "zh-en.tsv")
    assert zh["学习"] == ("to learn; to study",), zh["学习"]
    assert zh["學習"] == zh["学习"], "traditional form is a key too"
    assert zh["张"] == ("to open up; to spread",), "a common word beats the surname entry"
    assert zh["个"] == ("variant of 個|个[ge4]",), "a sense list of only skipped senses keeps the first"
    assert zh["电脑"] == ("computer",), "classifier senses dropped"

    ja = read(out / "ja-en.tsv")
    assert ja["学ぶ"] == ("to study; to learn", "v."), ja["学ぶ"]
    assert ja["まなぶ"] == ja["学ぶ"]
    assert ja["はし"] == ("bridge", "n."), "the common word wins a shared reading over a rarer kana word"
    assert ja["端"] == ("end", "n."), "parentheticals dropped"
    assert ja["ありがとう"] == ("thank you", "int."), "kana word"

    en = read(out / "en-zh.tsv")
    assert en["apple"] == ("my apple", "n."), "first listed source wins"
    assert en["zebra"] == ("my zebra", "n.")
    assert en["study"] == ("学习; 研究", "v."), en["study"]
    assert "obscureword" not in en, "rare words outside the frequency limit are dropped"
    assert en["taken"] == ("被占用的", "adj."), "within the modern-corpus limit"

    sources = (out / "SOURCES.md").read_text(encoding="utf-8")
    for name in ("cc-cedict", "jmdict", "mine", "ecdict"):
        assert f"| {name} |" in sources, name
    assert "- **cc-cedict** (zh-en): CC-CEDICT" in sources

    # Rebuilding one pair keeps the manifest rows of the others.
    result = run("--config", str(config), "--out", str(out), "--cache", str(t / "cache"), "--only", "zh-en")
    assert result.returncode == 0, result.stderr
    sources = (out / "SOURCES.md").read_text(encoding="utf-8")
    assert sources.count("| cc-cedict |") == 1 and "| jmdict |" in sources and "| ecdict |" in sources, sources

    # --url replaces one source's location; unknown names and plain HTTP are refused.
    other = t / "other.tsv"
    other.write_text("你好\thi there\tint.\n", encoding="utf-8")
    config2 = t / "tsv.toml"
    config2.write_text(f'[[source]]\nname = "a"\npair = "zh-en"\nformat = "tsv"\nurl = "{t / "missing.tsv"}"\nlicense = "x"\n', encoding="utf-8")
    result = run("--config", str(config2), "--out", str(t / "out2"), "--url", f"a={other}")
    assert result.returncode == 0, result.stderr
    assert read(t / "out2" / "zh-en.tsv") == {"你好": ("hi there", "int.")}
    assert run("--config", str(config2), "--out", str(t / "out2"), "--url", f"nope={other}").returncode != 0
    assert run("--config", str(config2), "--out", str(t / "out2"), "--url", "a=http://example.invalid/x.tsv").returncode != 0

    # --rime-dir writes into <dir>/gloss/dict.
    result = run("--config", str(config2), "--rime-dir", str(t / "Rime"), "--url", f"a={other}")
    assert result.returncode == 0 and (t / "Rime" / "gloss" / "dict" / "zh-en.tsv").exists(), result.stderr

print("build_dicts_test: ok")
