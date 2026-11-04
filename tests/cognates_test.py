#!/usr/bin/env python3
"""tools/cognates.py on a tiny synthetic CC-CEDICT + JMdict. No network."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import cognates  # noqa: E402

CEDICT = """# sample
學習 学习 [xue2 xi2] /to learn/to study/
手紙 手纸 [shou3 zhi3] /toilet paper/
吃 吃 [chi1] /to eat; to consume/to eat at (a cafeteria etc)/
來 来 [lai2] /to come/to arrive/to come round/
書房 书房 [shu1 fang2] /study (room)/studio/
愛人 爱人 [ai4 ren5] /spouse/husband/wife/sweetheart/lover/
天氣 天气 [tian1 qi4] /weather/
說 说 [shuo1] /to speak/to say/to explain/theory; teaching/
Beijing 北京 [Bei3 jing1] /Beijing/
工作 工作 [gong1 zuo4] /to work/(of a machine) to operate/job/work/
"""

JMDICT = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE JMdict [
<!ELEMENT JMdict (entry*)>
<!ENTITY n "noun (common) (futsuumeishi)">
<!ENTITY v1 "Ichidan verb">
<!ENTITY v5u "Godan verb with 'u' ending">
<!ENTITY vk "Kuru verb - special class">
<!ENTITY hon "honorific or respectful (sonkeigo) language">
]>
<JMdict>
<entry><k_ele><keb>学習</keb><ke_pri>ichi1</ke_pri></k_ele><r_ele><reb>がくしゅう</reb><re_pri>ichi1</re_pri></r_ele>
<sense><pos>&n;</pos><gloss>study</gloss><gloss>learning</gloss></sense></entry>
<entry><k_ele><keb>学ぶ</keb><ke_pri>ichi1</ke_pri></k_ele><r_ele><reb>まなぶ</reb></r_ele>
<sense><pos>&v5u;</pos><gloss>to learn</gloss></sense></entry>
<entry><k_ele><keb>手紙</keb><ke_pri>ichi1</ke_pri></k_ele><r_ele><reb>てがみ</reb></r_ele>
<sense><pos>&n;</pos><gloss>letter</gloss></sense></entry>
<entry><k_ele><keb>召し上がる</keb><ke_pri>ichi1</ke_pri></k_ele><r_ele><reb>めしあがる</reb></r_ele>
<sense><pos>&v5u;</pos><misc>&hon;</misc><gloss>to eat</gloss></sense></entry>
<entry><k_ele><keb>食べる</keb><ke_pri>ichi1</ke_pri></k_ele><r_ele><reb>たべる</reb></r_ele>
<sense><pos>&v1;</pos><gloss>to eat</gloss></sense><sense><gloss>to live on</gloss></sense></entry>
<entry><k_ele><keb>来る</keb><ke_pri>ichi1</ke_pri></k_ele><r_ele><reb>くる</reb></r_ele>
<sense><pos>&vk;</pos><gloss>to come (spatially or temporally)</gloss><gloss>to arrive</gloss></sense></entry>
<entry><k_ele><keb>勉強</keb><ke_pri>ichi1</ke_pri></k_ele><r_ele><reb>べんきょう</reb></r_ele>
<sense><pos>&n;</pos><gloss>study</gloss></sense></entry>
<entry><k_ele><keb>愛人</keb><ke_pri>ichi1</ke_pri></k_ele><r_ele><reb>あいじん</reb></r_ele>
<sense><pos>&n;</pos><gloss>lover</gloss><gloss>mistress</gloss></sense></entry>
<entry><k_ele><keb>配偶者</keb><ke_pri>ichi1</ke_pri></k_ele><r_ele><reb>はいぐうしゃ</reb></r_ele>
<sense><pos>&n;</pos><gloss>spouse</gloss></sense></entry>
<entry><k_ele><keb>天気</keb><ke_pri>ichi1</ke_pri></k_ele><r_ele><reb>てんき</reb></r_ele>
<sense><pos>&n;</pos><gloss>weather</gloss></sense></entry>
<entry><k_ele><keb>気象</keb><ke_pri>news1</ke_pri></k_ele><r_ele><reb>きしょう</reb></r_ele>
<sense><pos>&n;</pos><gloss>weather</gloss><gloss>climate</gloss></sense></entry>
<entry><k_ele><keb>説</keb><ke_pri>ichi1</ke_pri></k_ele><r_ele><reb>せつ</reb></r_ele>
<sense><pos>&n;</pos><gloss>theory</gloss><gloss>doctrine</gloss></sense></entry>
<entry><k_ele><keb>話す</keb><ke_pri>ichi1</ke_pri></k_ele><r_ele><reb>はなす</reb></r_ele>
<sense><pos>&v5u;</pos><gloss>to speak</gloss><gloss>to talk</gloss></sense></entry>
<entry><k_ele><keb>工作</keb><ke_pri>ichi1</ke_pri></k_ele><r_ele><reb>こうさく</reb></r_ele>
<sense><pos>&n;</pos><gloss>work (e.g. political)</gloss><gloss>handicraft</gloss></sense></entry>
<entry><k_ele><keb>働く</keb><ke_pri>ichi1</ke_pri></k_ele><r_ele><reb>はたらく</reb></r_ele>
<sense><pos>&v5u;</pos><gloss>to work</gloss></sense></entry>
</JMdict>
"""

# OpenCC format: shinjitai<TAB>traditional
SHIN = "# sample\n学\t學\n気\t氣\n説\t說\n"

table = cognates.zh_ja(cognates.pair_words(CEDICT, JMDICT.encode(), SHIN, "# none\n"))


def eq(key: str, expected: tuple[str, str] | None, why: str) -> None:
    assert table.get(key) == expected, f"{key}: expected {expected}, got {table.get(key)} ({why})"


eq("学习", ("学習 がくしゅう", "名"), "same form after 學習 -> 学習, meanings overlap, at least as basic as 学ぶ")
eq("學習", ("学習 がくしゅう", "名"), "traditional key too")
eq("手纸", None, "手紙 means letter: no overlap, and no pivot for 'toilet paper'")
eq("吃", ("食べる たべる", "動"), "exact English match; the honorific 召し上がる is excluded")
eq("来", ("来る くる", "動"), "match after dropping '(spatially or temporally)', with a second shared word (arrive)")
eq("书房", None, "'study (room)' must not match 勉強 'study'")
eq("爱人", ("配偶者 はいぐうしゃ", "名"), "listed false friend: never by form; the English route finds spouse")
eq("天气", ("天気 てんき", "名"), "the same written word wins against an equally basic pivot (気象 is not ichi1 anyway)")
eq("说", ("話す はなす", "動"), "説 'theory' does not share 说's main meanings")
eq("北京", None, "proper nouns skipped")
eq("工作", ("働く はたらく", "動"), "listed false friend whose senses do overlap: only the list stops 工作 こうさく")
print("cognates_test: ok")
