-- Runs the filter against a mocked Rime environment: `lua5.4 tests/filter_test.lua`
-- (from the repository root). No Rime installation needed.

local sep = package.config:sub(1, 1)
package.path = "lua" .. sep .. "?.lua;" .. package.path

local failures, checks = 0, 0
local function check(cond, what)
  checks = checks + 1
  if not cond then
    failures = failures + 1
    io.stderr:write("FAIL: " .. what .. "\n")
  end
end
local function eq(actual, expected, what)
  check(actual == expected, string.format("%s: expected %q, got %q", what, tostring(expected), tostring(actual)))
end

-- Temporary user and shared data directories.
local function tmpdir()
  local path = os.tmpname()
  os.remove(path)
  assert(os.execute((sep == "\\" and "mkdir " or "mkdir -p ") .. path))
  return path
end
local user, shared = tmpdir(), tmpdir()
local function mkdirs(dir)
  os.execute((sep == "\\" and "mkdir " or "mkdir -p ") .. dir .. sep .. "gloss" .. sep .. "dict")
end
mkdirs(user)
mkdirs(shared)
local function write(dir, rel, text)
  local f = assert(io.open(dir .. sep .. rel:gsub("/", sep), "wb"))
  f:write(text)
  f:close()
end

rime_api = {
  get_user_data_dir = function() return user end,
  get_shared_data_dir = function() return shared end,
}
local G = require("rime_gloss_filter")

-- byte order, not locale order
check(G.byte_less("Z", "a"), "byte order puts upper case first")
check(G.byte_less("ab", "abc"), "prefix sorts first")
check(not G.byte_less("abc", "abc"), "equal is not less")
check(G.byte_less("学", "学习"), "UTF-8 prefix")

-- clip never cuts inside a UTF-8 sequence
local clipped = G.clip(string.rep("学", 20), 10)
check(utf8.len(clipped) ~= nil, "clip keeps valid UTF-8")
check(#clipped <= 10 + #"…", "clip limit")
eq(G.clip("short", 10), "short", "no clip when short")

-- parse_line
local t, g, p = G.parse_line("学习\tstudy\tv.\r")
eq(t .. "|" .. g .. "|" .. p, "学习|study|v.", "parse three columns with CR")
t, g, p = G.parse_line("学习\tstudy")
eq(p, "", "parse two columns")
eq(G.parse_line("# comment"), nil, "comments skipped")
eq(G.parse_line("broken"), nil, "malformed skipped")

-- search_sorted over a large byte-sorted file
local keys = {}
for i = 1, 5000 do keys[#keys + 1] = string.format("k%05d", i * 3) end
keys[#keys + 1] = "Apple"
keys[#keys + 1] = "apple"
keys[#keys + 1] = "学习"
keys[#keys + 1] = "学"
table.sort(keys, G.byte_less)
local lines = {}
for _, k in ipairs(keys) do lines[#lines + 1] = k .. "\tg-" .. k .. "\tn." end
local big = user .. sep .. "big.tsv"
write(user, "big.tsv", table.concat(lines, "\n") .. "\n")
local all_found = true
for _, k in ipairs(keys) do
  local hit = G.search_sorted(big, k)
  if not hit or hit.gloss ~= "g-" .. k then
    all_found = false
    io.stderr:write("missed " .. k .. "\n")
    break
  end
end
check(all_found, "every key of a 5004-line file is found")
eq(G.search_sorted(big, keys[1]).gloss, "g-" .. keys[1], "first key")
eq(G.search_sorted(big, keys[#keys]).gloss, "g-" .. keys[#keys], "last key")
for _, missing in ipairs({ "k00001", "k99999", "", "A", "zzz", "学习者", "k0" }) do
  eq(G.search_sorted(big, missing), nil, "absent key " .. missing)
end
eq(G.search_sorted(big, "学").gloss, "g-学", "UTF-8 key whose extension also exists")
write(user, "nolf.tsv", "a\tA\nb\tB")
eq(G.search_sorted(user .. sep .. "nolf.tsv", "b").gloss, "B", "last line without newline")
eq(G.search_sorted(user .. sep .. "missing.tsv", "a"), nil, "missing file")

-- Fixture data: zh-en dictionary, seed and user override; zh-ja seed; en-zh dictionary.
write(user, "gloss/dict/zh-en.tsv", "学习\tdict study\tv.\n电脑\tcomputer\tn.\n苹果\tapple (dict)\tn.\n键盘\tkeyboard\tn.\n")
write(shared, "gloss/zh-en.tsv", "# shared seed\n苹果\tapple (shared)\tn.\n")
write(user, "gloss/zh-en.tsv", "学习\tstudy/learn\tv.\n苹果\tapple (seed)\tn.\n")
write(user, "gloss/user_zh-en.tsv", "苹果\tapple (mine)\tn.\n电脑\t-\n")
write(user, "gloss/zh-ja.tsv", "学习\t学ぶ\t動\n")
write(shared, "gloss/dict/en-zh.tsv", "apple\t苹果\tn.\nstudy\t学习\tv.\n")

-- Mock engine with a config and a switch state.
local function engine(config, options)
  return {
    context = { get_option = function(_, name) return options[name] == true end },
    schema = { config = {
      get_string = function(_, path) return config[path] end,
      get_list = function(_, path)
        local values = config[path]
        if type(values) ~= "table" then return nil end
        return { size = #values, get_value_at = function(_, i) return { value = values[i + 1] } end }
      end,
    } },
  }
end
local function run(config, options, texts)
  local env = { engine = engine(config, options) }
  G.init(env)
  local cands = {}
  for _, text in ipairs(texts) do cands[#cands + 1] = { text = text, comment = "" } end
  local out = {}
  _G.yield = function(c) out[#out + 1] = c end
  G.func({ iter = function()
    local i = 0
    return function() i = i + 1; return cands[i] end
  end }, env)
  check(#out == #cands, "every candidate is yielded")
  local comments = {}
  for i, c in ipairs(out) do comments[c.text] = c.comment; check(c.text == texts[i], "text unchanged") end
  return comments
end

local zh = { ["rime_gloss/source"] = "zh", ["rime_gloss/targets"] = { "en", "ja" } }
local c = run(zh, { gloss_en = true }, { "学习", "苹果", "电脑", "没有", "键盘" })
eq(c["键盘"], "n. keyboard", "dictionary fills what the seed lacks")
eq(c["学习"], "v. study/learn", "seed beats dictionary")
eq(c["苹果"], "n. apple (mine)", "user beats seed beats shared seed")
eq(c["电脑"], "", "a user \"-\" hides the dictionary entry")
eq(c["没有"], "", "no entry, no comment")

c = run(zh, { gloss_ja = true }, { "学习", "电脑" })
eq(c["学习"], "動 学ぶ", "ja target")
eq(c["电脑"], "", "no ja entry")

c = run(zh, { gloss_all = true }, { "学习", "电脑" })
eq(c["学习"], "en: v. study/learn · ja: 動 学ぶ", "all targets labelled")
eq(c["电脑"], "", "hidden in all mode too")

c = run(zh, { gloss_off = true }, { "学习" })
eq(c["学习"], "", "off")

c = run(zh, {}, { "学习" })
eq(c["学习"], "v. study/learn", "no option set: first target")
c = run({ ["rime_gloss/source"] = "zh", ["rime_gloss/targets"] = { "en", "ja" }, ["rime_gloss/default"] = "ja" }, {}, { "学习" })
eq(c["学习"], "動 学ぶ", "configured default")
c = run({}, {}, { "学习" })
eq(c["学习"], "v. study/learn", "defaults: zh -> en")

local en = { ["rime_gloss/source"] = "en", ["rime_gloss/targets"] = { "zh" } }
c = run(en, { gloss_zh = true }, { "Apple", "study", "nothing" })
eq(c["Apple"], "n. 苹果", "English input folds case; shared dictionary")
eq(c["study"], "v. 学习", "English input")
eq(c["nothing"], "", "English miss")

-- Japanese input: katakana candidates fall back to the hiragana reading.
eq(G.katakana_to_hiragana("ネコ"), "ねこ", "katakana to hiragana")
eq(G.katakana_to_hiragana("コーヒー"), "こーひー", "long vowel mark kept")
eq(G.katakana_to_hiragana("猫ねこ"), "猫ねこ", "no katakana, unchanged")
write(user, "gloss/dict/ja-en.tsv", "ねこ\tcat\tn.\n猫\tcat\tn.\n")
local ja = { ["rime_gloss/source"] = "ja", ["rime_gloss/targets"] = { "en" } }
c = run(ja, { gloss_en = true }, { "猫", "ネコ", "イヌ" })
eq(c["猫"], "n. cat", "Japanese kanji")
eq(c["ネコ"], "n. cat", "katakana falls back to hiragana")
eq(c["イヌ"], "", "katakana miss")
c = run(zh, { gloss_en = true }, { "ネコ" })
eq(c["ネコ"], "", "no katakana folding for Chinese input")

-- Existing comments are kept.
local env = { engine = engine(zh, { gloss_en = true }) }
G.init(env)
local cand = { text = "学习", comment = "xuéxí" }
_G.yield = function() end
G.func({ iter = function() local done = false; return function() if done then return nil end; done = true; return cand end end }, env)
eq(cand.comment, "xuéxí | v. study/learn", "appends to an existing comment")

-- Long candidates (sentences) are skipped.
c = run(zh, { gloss_en = true }, { string.rep("学", 30) })
eq(c[string.rep("学", 30)], "", "long candidate skipped")

os.execute((sep == "\\" and "rmdir /s /q " or "rm -rf ") .. user .. " " .. shared)
if failures > 0 then
  io.stderr:write(string.format("%d of %d checks failed\n", failures, checks))
  os.exit(1)
end
print(string.format("filter_test: %d checks passed", checks))
