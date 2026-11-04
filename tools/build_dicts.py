#!/usr/bin/env python3
"""Build gloss/dict/<pair>.tsv from open dictionaries listed in dicts.toml.

Each output file is byte-sorted with unique keys, so the Lua filter can
binary-search it on disk. gloss/dict/SOURCES.md records where every file came
from, its license and when it was built.

Examples:
  python3 tools/build_dicts.py                         # every source, into ./gloss/dict
  python3 tools/build_dicts.py --only zh-en            # one pair
  python3 tools/build_dicts.py --rime-dir "$APPDATA/Rime"  # straight into a Rime user dir
  python3 tools/build_dicts.py --url cc-cedict=/path/to/cedict.txt.gz
  python3 tools/build_dicts.py --config my-dicts.toml
"""

from __future__ import annotations

import argparse
import csv
import datetime
import gzip
import hashlib
import io
import os
import re
import sys
import tempfile
import tomllib
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Iterable, Iterator
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
PAIR = re.compile(r"^[a-z]{2,3}-[a-z]{2,3}$")
FORMATS = ("cedict", "jmdict", "ecdict", "tsv")
MAX_DOWNLOAD = 256 * 1024 * 1024
MAX_KEY_BYTES = 64
MAX_GLOSS_CHARS = 60
SENSE_BUDGET = 36

# (key, gloss, pos, rank): lower rank wins when a key appears twice in one source.
Entry = tuple[str, str, str, tuple]


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\t", " ")).strip()


def short(gloss: str) -> str:
    gloss = clean(gloss)
    return gloss if len(gloss) <= MAX_GLOSS_CHARS else gloss[: MAX_GLOSS_CHARS - 1].rstrip(" ;,") + "…"


def drop_parens(sense: str) -> str:
    """'cat (esp. the domestic cat)' -> 'cat', unless nothing would be left."""
    stripped = clean(re.sub(r"\s*\([^()]*\)", "", sense))
    return stripped or clean(sense)


def join_senses(senses: list[str], limit: int = SENSE_BUDGET) -> str:
    """Whole senses, in order, while they fit in the budget; always the first."""
    out: list[str] = []
    for sense in senses:
        if out and len("; ".join(out + [sense])) > limit:
            break
        out.append(sense)
    return short("; ".join(out))


def usable_key(key: str) -> bool:
    return bool(key) and len(key.encode("utf-8")) <= MAX_KEY_BYTES and not any(ch in key for ch in "\t\r\n")


# --- fetching -----------------------------------------------------------------


def fetch(url: str, cache: Path) -> bytes:
    """The raw bytes of a source: a local path, or an https:// URL (cached by URL)."""
    if not re.match(r"^[a-z]+://", url):
        return Path(url).expanduser().read_bytes()
    if not url.startswith("https://"):
        raise SystemExit(f"refusing non-HTTPS URL {url}; use https:// or a local path")
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / hashlib.sha256(url.encode()).hexdigest()[:16]
    if path.exists():
        return path.read_bytes()
    print(f"  downloading {url}", file=sys.stderr)
    request = urllib.request.Request(url, headers={"User-Agent": "rime-gloss build_dicts"})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read(MAX_DOWNLOAD + 1)
    if len(data) > MAX_DOWNLOAD:
        raise SystemExit(f"{url} is larger than {MAX_DOWNLOAD} bytes")
    path.write_bytes(data)
    return data


def unpack(data: bytes, url: str) -> bytes:
    if data[:2] == b"\x1f\x8b":
        return gzip.decompress(data)
    if data[:4] == b"PK\x03\x04":
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = [m for m in archive.infolist() if not m.is_dir()]
            if len(members) != 1:
                names = ", ".join(m.filename for m in members[:5])
                raise SystemExit(f"{url}: zip must hold exactly one file, found {names}")
            return archive.read(members[0])
    return data


# --- parsers ------------------------------------------------------------------

CEDICT_LINE = re.compile(r"^(\S+) (\S+) \[([^\]]*)\] /(.*)/\s*$")
CEDICT_SKIP = ("CL:", "Taiwan pr.", "also pr.", "old variant of", "variant of", "see ", "used in", "also written")


def parse_cedict(text: str) -> Iterator[Entry]:
    """CC-CEDICT: 'TRAD SIMP [pin1 yin1] /sense/sense/'. Keys are both script forms."""
    for order, line in enumerate(text.splitlines()):
        if line.startswith("#"):
            continue
        m = CEDICT_LINE.match(line)
        if not m:
            continue
        trad, simp, pinyin, defs = m.groups()
        senses = [clean(s.replace("(bound form)", "")) for s in defs.split("/")]
        senses = [s for s in senses if s]
        good = [drop_parens(s) for s in senses if not s.startswith(CEDICT_SKIP)] or senses[:1]
        if not good:
            continue
        gloss = join_senses(good)
        # Prefer common words over proper nouns and surname-only entries; among
        # readings of one character, the one with more senses is usually the
        # everyday word (打 da3 "to hit" over da2 "dozen").
        rank = (pinyin[:1].isupper(), good[0].startswith("surname "), -min(len(senses), 12), order)
        for key in dict.fromkeys((simp, trad)):
            yield key, gloss, "", rank


JMDICT_POS = (
    ("noun", "n."), ("pronoun", "pron."), ("adverb", "adv."), ("adjectival noun", "adj."),
    ("adjective", "adj."), ("'taru' adjective", "adj."), ("pre-noun adjectival", "adj."),
    ("godan verb", "v."), ("ichidan verb", "v."), ("suru verb", "v."), ("kuru verb", "v."),
    ("nidan verb", "v."), ("yodan verb", "v."), ("verb", "v."), ("transitive verb", "v."),
    ("intransitive verb", "v."), ("conjunction", "conj."), ("interjection", "int."),
    ("particle", "part."), ("counter", "ctr."), ("expressions", "exp."), ("prefix", "pref."),
    ("suffix", "suf."), ("auxiliary", "aux."), ("numeric", "num."),
)
COMMON = re.compile(r"^(news1|ichi1|spec1|spec2|gai1|nf\d\d)$")


def jmdict_pos(text: str) -> str:
    lowered = text.lower()
    for prefix, short_pos in JMDICT_POS:
        if lowered.startswith(prefix):
            return short_pos
    return ""


def parse_jmdict(data: bytes) -> Iterator[Entry]:
    """JMdict XML. Keys are kanji forms and kana readings; common words win."""
    order = 0
    for _, elem in ElementTree.iterparse(io.BytesIO(data), events=("end",)):
        if elem.tag != "entry":
            continue
        order += 1
        kebs = [(k.findtext("keb") or "", any(COMMON.match(p.text or "") for p in k.findall("ke_pri"))) for k in elem.findall("k_ele")]
        rebs = [(r.findtext("reb") or "", any(COMMON.match(p.text or "") for p in r.findall("re_pri"))) for r in elem.findall("r_ele")]
        senses = elem.findall("sense")
        elem.clear()
        if not senses:
            continue
        glosses = [clean(g.text or "") for g in senses[0].findall("gloss") if clean(g.text or "")]
        if not glosses:
            continue
        pos = next((jmdict_pos(p.text or "") for s in senses for p in s.findall("pos") if jmdict_pos(p.text or "")), "")
        kana_word = not kebs or any("usually written using kana" in (m.text or "") for m in senses[0].findall("misc"))
        gloss = join_senses([drop_parens(g) for g in glosses])
        common = any(c for _, c in kebs + rebs)
        for keb, keb_common in kebs:
            yield keb, gloss, pos, (not (keb_common or common), order)
        for reb, reb_common in rebs:
            # A common reading first; among those, a word usually written in kana.
            yield reb, gloss, pos, (not reb_common, not kana_word, order)


ECDICT_POS = {"a.": "adj.", "adj.": "adj.", "vt.": "v.", "vi.": "v.", "v.": "v.", "n.": "n.", "adv.": "adv.",
              "prep.": "prep.", "conj.": "conj.", "pron.": "pron.", "int.": "int.", "interj.": "int.",
              "num.": "num.", "art.": "art.", "abbr.": "abbr.", "aux.": "aux."}
ECDICT_LIMIT = 50000


def parse_ecdict(text: str) -> Iterator[Entry]:
    """ECDICT CSV. Kept: words in the 50k most frequent (BNC or modern corpus),
    or tagged for an exam word list, or in Oxford/Collins core vocabulary."""
    for order, row in enumerate(csv.DictReader(io.StringIO(text))):
        word = (row.get("word") or "").strip()
        if not word or word.count(" ") > 2:
            continue

        def rank_of(field: str) -> int:
            try:
                value = int(row.get(field) or 0)
            except ValueError:
                return 0
            return value if value > 0 else 0

        frq, bnc = rank_of("frq"), rank_of("bnc")
        core = (row.get("tag") or "").strip() or (row.get("oxford") or "").strip() == "1" or rank_of("collins") > 0
        if not (core or 0 < frq <= ECDICT_LIMIT or 0 < bnc <= ECDICT_LIMIT):
            continue
        lines = [clean(x) for x in (row.get("translation") or "").replace("\\n", "\n").splitlines()]
        lines = [x for x in lines if x and not x.startswith("[")] or [x for x in lines if x]
        if not lines:
            continue
        m = re.match(r"^([a-z]+\.)\s*(.*)$", lines[0])
        pos, gloss = (ECDICT_POS.get(m.group(1), ""), m.group(2)) if m else ("", lines[0])
        if not gloss:
            continue
        items = [clean(x) for x in re.split(r"[,，;；]", gloss) if clean(x)]
        yield word, join_senses(items[:3]), pos, (min(frq or 10**9, bnc or 10**9), order)


def parse_tsv(text: str) -> Iterator[Entry]:
    for order, line in enumerate(text.splitlines()):
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        yield parts[0].strip(), short(parts[1]), clean(parts[2]) if len(parts) > 2 else "", (order,)


PARSERS: dict[str, Callable[[bytes], Iterable[Entry]]] = {
    "cedict": lambda data: parse_cedict(data.decode("utf-8")),
    "jmdict": parse_jmdict,
    "ecdict": lambda data: parse_ecdict(data.decode("utf-8-sig")),
    "tsv": lambda data: parse_tsv(data.decode("utf-8-sig")),
}


# --- building -----------------------------------------------------------------


def best_entries(entries: Iterable[Entry]) -> dict[str, tuple[str, str]]:
    best: dict[str, tuple[tuple, str, str]] = {}
    for key, gloss, pos, rank in entries:
        key = clean(key)
        if not usable_key(key) or not gloss:
            continue
        old = best.get(key)
        if old is None or rank < old[0]:
            best[key] = (rank, gloss, pos)
    return {k: (g, p) for k, (_, g, p) in best.items()}


def write_sorted(path: Path, entries: dict[str, tuple[str, str]]) -> None:
    lines = []
    for key in sorted(entries, key=lambda k: k.encode("utf-8")):
        gloss, pos = entries[key]
        lines.append(f"{key}\t{gloss}\t{pos}" if pos else f"{key}\t{gloss}")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write next to the target, then swap, so a running Rime never reads half a file.
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def load_config(path: Path, overrides: list[str]) -> list[dict]:
    with path.open("rb") as f:
        sources = tomllib.load(f).get("source", [])
    urls = {}
    for item in overrides:
        name, sep, url = item.partition("=")
        if not sep or not url:
            raise SystemExit(f"--url expects NAME=URL, got {item!r}")
        urls[name] = url
    names = set()
    for source in sources:
        missing = [k for k in ("name", "pair", "format", "url", "license") if not source.get(k)]
        if missing:
            raise SystemExit(f"{path}: source {source.get('name', '?')} lacks {', '.join(missing)}")
        if not PAIR.match(source["pair"]):
            raise SystemExit(f"{path}: {source['name']}: pair must look like zh-en")
        if source["format"] not in FORMATS:
            raise SystemExit(f"{path}: {source['name']}: format must be one of {', '.join(FORMATS)}")
        source["url"] = urls.pop(source["name"], source["url"])
        names.add(source["name"])
    if urls:
        raise SystemExit(f"--url names not in {path}: {', '.join(urls)} (known: {', '.join(sorted(names))})")
    return sources


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=ROOT / "dicts.toml")
    parser.add_argument("--only", action="append", default=[], help="pair or source name; repeatable")
    parser.add_argument("--url", action="append", default=[], metavar="NAME=URL", help="use another URL or local file for a source")
    out = parser.add_mutually_exclusive_group()
    out.add_argument("--out", type=Path, help="output directory (default: gloss/dict in this repo)")
    out.add_argument("--rime-dir", type=Path, help="a Rime user directory; writes <dir>/gloss/dict")
    parser.add_argument("--cache", type=Path, default=Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "rime-gloss")
    args = parser.parse_args()

    sources = load_config(args.config, args.url)
    if args.only:
        sources = [s for s in sources if s["pair"] in args.only or s["name"] in args.only]
        if not sources:
            raise SystemExit(f"nothing matches --only {', '.join(args.only)}")
    out_dir = args.out or (args.rime_dir / "gloss" / "dict" if args.rime_dir else ROOT / "gloss" / "dict")

    by_pair: dict[str, list[dict]] = {}
    for source in sources:
        by_pair.setdefault(source["pair"], []).append(source)
    today = datetime.date.today().isoformat()
    manifest = []
    for pair, pair_sources in by_pair.items():
        merged: dict[str, tuple[str, str]] = {}
        for source in pair_sources:
            print(f"{pair}: {source['name']}", file=sys.stderr)
            raw = fetch(source["url"], args.cache)
            entries = best_entries(PARSERS[source["format"]](unpack(raw, source["url"])))
            for key, value in entries.items():
                merged.setdefault(key, value)  # earlier sources win
            manifest.append((pair, source, len(entries), hashlib.sha256(raw).hexdigest()[:12]))
        if not merged:
            raise SystemExit(f"{pair}: no entries parsed; is the format right?")
        write_sorted(out_dir / f"{pair}.tsv", merged)
        print(f"{pair}: wrote {len(merged)} entries", file=sys.stderr)

    rows = ["# Imported dictionaries", "",
            "Generated by `tools/build_dicts.py` from the sources in `dicts.toml`. Each file keeps the license of its source; they are not covered by the MIT license of this repository.", "",
            "| File | Source | Entries | License | Built | Input sha256 |", "| --- | --- | --- | --- | --- | --- |"]
    # Keep the rows of pairs this run did not rebuild (e.g. with --only).
    kept_rows, kept_credits = [], []
    old_manifest = out_dir / "SOURCES.md"
    if old_manifest.exists():
        for line in old_manifest.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\| `([a-z-]+)\.tsv` \|", line) or re.match(r"^- \*\*[^*]+\*\* \(([a-z-]+)\):", line)
            if m and m.group(1) not in by_pair:
                (kept_rows if line.startswith("|") else kept_credits).append(line)
    for pair, source, count, digest in manifest:
        rows.append(f"| `{pair}.tsv` | {source['name']} | {count} | {source['license']} | {today} | `{digest}` |")
    rows += kept_rows
    rows += ["", "## Attribution", ""]
    rows += [f"- **{source['name']}** ({pair}): {source.get('attribution', source['url'])}" for pair, source, _, _ in manifest]
    rows += kept_credits
    rows += ["", "Glosses are shortened (first senses only) and re-sorted; see `tools/build_dicts.py` for the exact transformation."]
    (out_dir / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
