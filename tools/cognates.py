"""Chinese -> Japanese word pairs derived from CC-CEDICT and JMdict.

No open Chinese-Japanese dictionary exists, but both dictionaries explain
words in English, and the two languages share much of their vocabulary in
writing. A Chinese word gets a Japanese counterpart in one of two ways:

1. Same written form (cognate): the traditional form, converted to Japanese
   shinjitai with OpenCC's tables (學習 -> 学習), is a JMdict headword, and
   the English meanings overlap. False friends fail the overlap test:
   手纸 "toilet paper" vs 手紙 "letter", 汽车 "car" vs 汽車 "steam train".
2. English pivot: the Chinese word's first meaning equals the first gloss of
   a common JMdict entry ("to eat" -> 食べる, "airplane" -> 飛行機).

A same-form match must share the Japanese word's main sense and be at least
as basic (JMdict ichi1/news1) as the pivot match; otherwise the pivot wins
(吃 -> 食べる rather than the rare 喫する). Well-known false friends never pair
by form. The reverse direction is not built: CC-CEDICT has no frequency data,
so rare Chinese cognates (会社, 病院) cannot be told from everyday words.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from xml.etree import ElementTree

# Well-known Chinese/Japanese false friends: same characters, different
# everyday meaning. They never pair by written form (the English route may
# still find the right word, e.g. 爱人 -> 配偶者).
FALSE_FRIENDS = set("爱人 公司 新闻 手纸 汽车 告诉 工作 东西 便宜 勉强 大丈夫 丈夫 老婆 娘 走 看病 留守 "
                    "迷惑 结束 先生 床 汤 颜色 心中 得意 用意 人间 大家 小人 一味 一向 结构 质问".split())

COMMON = re.compile(r"^(news1|ichi1|spec1|spec2|gai1|nf\d\d)$")
CEDICT_LINE = re.compile(r"^(\S+) (\S+) \[([^\]]*)\] /(.*)/\s*$")
SKIP = ("CL:", "Taiwan pr.", "also pr.", "old variant of", "variant of", "see ", "used in", "also written",
        "surname ", "abbr.", "erhua variant", "(Tw)", "(old)")
STOP = set("a an the of to in on at for by with from as or and be is sb sth one one's oneself something somebody "
           "etc also used fig lit esp usu e g i".split())
JA_POS = (("noun", "名"), ("pronoun", "代"), ("adverb", "副"), ("adjectival noun", "形動"), ("adjective", "形"),
          ("'taru' adjective", "形動"), ("pre-noun adjectival", "連体"), ("godan verb", "動"), ("ichidan verb", "動"),
          ("suru verb", "名・する"), ("kuru verb", "動"), ("verb", "動"), ("transitive verb", "動"),
          ("intransitive verb", "動"), ("conjunction", "接"), ("interjection", "感"), ("particle", "助"),
          ("counter", "助数"), ("expressions", "表現"), ("prefix", "接頭"), ("suffix", "接尾"), ("auxiliary", "助動"),
          ("numeric", "数"))


def meaning_words(text: str) -> set[str]:
    """Content words of an English gloss, crudely stemmed (marry/marriage -> marri)."""
    text = re.sub(r"\([^()]*\)", " ", text.lower())
    out = set()
    for w in re.findall(r"[a-z]+", text):
        if w in STOP or len(w) < 3:
            continue
        w = w[:-1] + "i" if w.endswith("y") else w
        out.add(w[:5])
    return out


MARKED = ("honorific", "humble", "archaic", "obsolete", "rare term", "derogatory", "vulgar", "dated term",
          "formal or literary", "rarely used", "jocular", "slang")


def bare_gloss(text: str) -> str:
    """Without any parentheses: "to come (spatially or temporally)" -> "to come"."""
    return re.sub(r"\s+", " ", re.sub(r"\([^()]*\)", "", text.lower())).strip(" ;,.")


def norm_gloss(text: str) -> str:
    # A leading label goes ("(business) company" is "company"); trailing
    # parentheses stay, they separate senses ("study (room)" is not "study").
    text = re.sub(r"^\s*\([^()]*\)\s*", "", text.lower())
    return re.sub(r"\s+", " ", text).strip(" ;,.")



def shinjitai_table(chars_text: str, phrases_text: str) -> tuple[dict[str, str], dict[str, str]]:
    """OpenCC JPShinjitai*: 'shinjitai<TAB>traditional ...' -> traditional -> shinjitai."""
    def parse(text: str) -> dict[str, str]:
        table: dict[str, str] = {}
        for line in text.splitlines():
            if not line or line.startswith("#") or "\t" not in line:
                continue
            shin, trads = line.split("\t", 1)
            for trad in trads.split():
                if trad != shin:
                    table.setdefault(trad, shin)
        return table
    return parse(chars_text), parse(phrases_text)


@dataclass
class JaEntry:
    word: str          # how it is usually written (kana for kana words)
    kebs: list[str]
    reading: str
    pos: str
    rank: tuple        # lower is more common
    common: bool
    words: set[str] = field(default_factory=set)
    first_words: set[str] = field(default_factory=set)
    first_gloss: str = ""
    first_bare: str = ""
    senses: int = 0
    marked: bool = False   # honorific, humble, archaic, ...: not what a learner wants first

    def pivot_rank(self, overlap: int) -> tuple:
        # Everyday vocabulary (ichi1) first, then shared meaning, then
        # polysemy (basic words have many senses); newspaper frequency last.
        return (self.marked, self.rank[0], -overlap, -min(self.senses, 8), self.rank[1], self.rank[2])


def read_jmdict(data: bytes) -> list[JaEntry]:
    entries = []
    for order, (_, el) in enumerate(ElementTree.iterparse(io.BytesIO(data), events=("end",))):
        if el.tag != "entry":
            continue
        kebs = [k.findtext("keb") or "" for k in el.findall("k_ele")]
        rebs = [r.findtext("reb") or "" for r in el.findall("r_ele")]
        senses = el.findall("sense")
        pris = [p.text or "" for p in el.iter() if p.tag in ("ke_pri", "re_pri")]
        if not rebs or not senses:
            el.clear()
            continue
        common = any(COMMON.match(p) for p in pris)
        nf = min([int(p[2:]) for p in pris if re.match(r"^nf\d\d$", p)] or [99])
        basic = "ichi1" in pris
        pos = ""
        for sense in senses:
            for p in sense.findall("pos"):
                text = (p.text or "").lower()
                pos = next((label for prefix, label in JA_POS if text.startswith(prefix)), "")
                if pos:
                    break
            if pos:
                break
        kana_word = not kebs or any("usually written using kana" in (m.text or "") for m in senses[0].findall("misc"))
        first = senses[0].find("gloss")
        marked = any(any(word in (m.text or "") for word in MARKED) for m in senses[0].findall("misc"))
        all_glosses = " ; ".join(g.text or "" for s in senses for g in s.findall("gloss"))
        entries.append(JaEntry(word=rebs[0] if kana_word else kebs[0], kebs=kebs, reading=rebs[0], pos=pos,
                               rank=(not basic, nf, order), common=common, words=meaning_words(all_glosses),
                               first_words=meaning_words(" ; ".join(g.text or "" for g in senses[0].findall("gloss"))),
                               first_gloss=norm_gloss(first.text or "") if first is not None else "",
                               first_bare=bare_gloss(first.text or "") if first is not None else "",
                               senses=len(senses), marked=marked))
        el.clear()
    return entries


@dataclass
class ZhWord:
    simp: str
    trads: list[str]
    pinyin: str
    senses: list[str]       # of the most used reading, split into single meanings
    words: set[str]         # meaning words of that reading
    main_words: set[str] = field(default_factory=set)  # of its first two meanings


def read_cedict(text: str) -> list[ZhWord]:
    by_simp: dict[str, list[tuple[str, str, list[str]]]] = {}
    for line in text.splitlines():
        m = CEDICT_LINE.match(line)
        if not m or line.startswith("#"):
            continue
        trad, simp, pinyin, defs = m.groups()
        if pinyin[:1].isupper():  # proper nouns
            continue
        meanings = [part.strip() for sense in defs.split("/") for part in sense.split(";")]
        meanings = [mng for mng in meanings if mng and not mng.startswith(SKIP)]
        if meanings:
            by_simp.setdefault(simp, []).append((trad, pinyin, meanings))
    words = []
    for simp, readings in by_simp.items():
        trad, pinyin, meanings = max(readings, key=lambda r: len(r[2]))  # most senses: the everyday reading
        words.append(ZhWord(simp=simp, trads=list(dict.fromkeys([trad] + [r[0] for r in readings])),
                            pinyin=pinyin, senses=meanings, words=meaning_words(" ; ".join(meanings)),
                            main_words=meaning_words(" ; ".join(meanings[:2]))))
    return words


def pair_words(cedict_text: str, jmdict_data: bytes, shin_chars: str, shin_phrases: str):
    """[(ZhWord, JaEntry, method)] with method 'cognate' or 'pivot'."""
    chars, phrases = shinjitai_table(shin_chars, shin_phrases)

    def to_shin(trad: str) -> str:
        return phrases.get(trad) or "".join(chars.get(ch, ch) for ch in trad)

    ja = read_jmdict(jmdict_data)
    by_keb: dict[str, list[JaEntry]] = {}
    by_gloss: dict[str, list[JaEntry]] = {}
    by_bare: dict[str, list[JaEntry]] = {}
    for e in ja:
        for keb in e.kebs:
            by_keb.setdefault(keb, []).append(e)
        if e.common and not e.marked and e.first_gloss:
            by_gloss.setdefault(e.first_gloss, []).append(e)
            by_bare.setdefault(e.first_bare, []).append(e)

    def pivot_for(zh: ZhWord) -> JaEntry | None:
        """An exact first-gloss match counts as is; a match only after dropping
        parentheses needs a second shared meaning word (来 -> 来る "to come
        (spatially or temporally)", but not 书房 "study (room)" -> 勉強)."""
        found: dict[int, tuple[JaEntry, int]] = {}
        for meaning in zh.senses[:3]:
            for e in by_gloss.get(norm_gloss(meaning), []):
                found[id(e)] = (e, len(zh.words & e.words))
            for e in by_bare.get(bare_gloss(meaning), []):
                overlap = len(zh.words & e.words)
                if overlap >= 2:
                    found.setdefault(id(e), (e, overlap))
            if found:
                break
        if not found:
            return None
        return min(found.values(), key=lambda item: item[0].pivot_rank(item[1]))[0]

    pairs = []
    for zh in read_cedict(cedict_text):
        forms = [] if zh.simp in FALSE_FRIENDS else list(dict.fromkeys([to_shin(t) for t in zh.trads] + zh.trads + [zh.simp]))
        cognate, best = None, (0, False)
        for form in forms:
            for e in by_keb.get(form, []):
                overlap = len(zh.words & e.words)
                single = len(form) == 1
                # The shared meaning must include both words' main senses.
                if not overlap or not (zh.main_words & e.first_words) or not (e.common or overlap >= 2):
                    continue
                if single and (not e.common or e.pos in ("接尾", "接頭", "助数")):
                    continue
                if (overlap, e.common) > best:
                    best, cognate = (overlap, e.common), e
        pivot = pivot_for(zh)
        if pivot and any(f in pivot.kebs for f in forms):
            pairs.append((zh, pivot, "cognate"))  # the English route found the same written word
        elif cognate and (not pivot or cognate.rank[0] <= pivot.rank[0]):
            pairs.append((zh, cognate, "cognate"))  # equally basic: the same written word wins
        elif pivot:
            pairs.append((zh, pivot, "pivot"))
    return pairs


def zh_ja(pairs) -> dict[str, tuple[str, str]]:
    """Chinese word (simplified and traditional) -> 'Japanese word reading'."""
    out: dict[str, tuple[str, str]] = {}
    for zh, e, _ in pairs:
        gloss = e.word if e.word == e.reading else f"{e.word} {e.reading}"
        for key in [zh.simp] + zh.trads:
            out.setdefault(key, (gloss, e.pos))
    return out
