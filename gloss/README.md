# Gloss data

Tab-separated files loaded by `lua/rime_gloss_filter.lua`, one set per language
pair `<source>-<target>` (see `docs/format.md`):

```text
text<TAB>gloss
text<TAB>gloss<TAB>pos
```

- `zh-en.tsv`, `zh-ja.tsv`: hand-written seed lists (MIT).
- `user_<pair>.tsv`: the user's own entries; not shipped, never overwritten.
- `dict/<pair>.tsv`: large imported dictionaries, byte-sorted for on-disk
  binary search; each keeps its upstream license.
