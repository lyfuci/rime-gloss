-- rime-gloss: show short target-language glosses beside candidates of any
-- input language. Loaded as lua_filter@*rime_gloss_filter.
--
-- Schema config (all optional):
--   rime_gloss/source:  input language of this schema's candidates (default zh)
--   rime_gloss/targets: target languages the switch offers (default [en])
--   rime_gloss/default: target shown when no gloss_* option is set
--                       (a target code, "all" or "off"; default: first target)
-- Switch options: gloss_off, gloss_<target> for each target, gloss_all.
--
-- For each <source>-<target> pair, later files win:
--   gloss/dict/<pair>.tsv   large imported dictionary, byte-sorted, binary-searched on disk
--   gloss/<pair>.tsv        hand-written seed list, loaded into memory
--   gloss/user_<pair>.tsv   the user's own entries, loaded into memory
-- Line format: text<TAB>gloss<TAB>part-of-speech (third column optional).

local MAX_ONE = 42
local MAX_ALL = 96
local MAX_KEY = 64

local M = {}

local function data_dirs()
  local dirs = {}
  if rime_api then
    if rime_api.get_user_data_dir then dirs[#dirs + 1] = rime_api.get_user_data_dir() end
    if rime_api.get_shared_data_dir then dirs[#dirs + 1] = rime_api.get_shared_data_dir() end
  end
  if #dirs == 0 then dirs[1] = "" end
  return dirs
end

local function join(dir, rel)
  local sep = package.config:sub(1, 1)
  rel = rel:gsub("/", sep)
  if dir == "" then return rel end
  local last = dir:sub(-1)
  if last == "/" or last == "\\" then return dir .. rel end
  return dir .. sep .. rel
end

local function trim(s)
  return (s:gsub("^%s+", ""):gsub("%s+$", ""))
end

-- text<TAB>gloss[<TAB>pos] -> text, gloss, pos (nil for comments and malformed lines)
local function parse_line(line)
  line = line:gsub("\r$", "")
  if line == "" or line:sub(1, 1) == "#" then return nil end
  local text, gloss, pos = line:match("^([^\t]+)\t([^\t]+)\t?([^\t]*)$")
  if not text then return nil end
  text, gloss, pos = trim(text), trim(gloss), trim(pos or "")
  if text == "" or gloss == "" then return nil end
  return text, gloss, pos
end
M.parse_line = parse_line

local function load_tsv(path, into)
  local f = io.open(path, "rb")
  if not f then return 0 end
  local n = 0
  for line in f:lines() do
    local text, gloss, pos = parse_line(line)
    if text then
      into[text] = { gloss = gloss, pos = pos }
      n = n + 1
    end
  end
  f:close()
  return n
end

-- Byte-wise string order, independent of the C locale (Lua's < uses strcoll).
local function byte_less(a, b)
  local n = math.min(#a, #b)
  for i = 1, n do
    local x, y = a:byte(i), b:byte(i)
    if x ~= y then return x < y end
  end
  return #a < #b
end
M.byte_less = byte_less

-- Binary search a byte-sorted TSV file for an exact key without loading it.
-- Invariant: the matching line, if any, starts at an offset in [lo, hi).
local function search_sorted(path, key)
  local f = io.open(path, "rb")
  if not f then return nil end
  local lo, hi = 0, f:seek("end")
  local found
  while lo < hi do
    local mid = (lo + hi) // 2
    local start = 0
    if mid > 0 then
      -- The first line starting at or after mid.
      f:seek("set", mid - 1)
      f:read("l")
      start = f:seek()
    else
      f:seek("set", 0)
    end
    if start >= hi then
      hi = mid
    else
      local line = f:read("l")
      if not line then
        hi = mid
      else
        local k = line:match("^[^\t]*")
        if k == key then
          found = line
          break
        elseif byte_less(k, key) then
          lo = f:seek()
        else
          hi = mid
        end
      end
    end
  end
  f:close()
  if not found then return nil end
  local _, gloss, pos = parse_line(found)
  if not gloss then return nil end
  return { gloss = gloss, pos = pos }
end
M.search_sorted = search_sorted

local function clip(s, limit)
  if s == "" or #s <= limit then return s end
  -- Cut on bytes, then back up to a UTF-8 lead byte.
  local cut = limit
  while cut > 1 do
    local b = s:byte(cut)
    if b < 128 or b >= 192 then break end
    cut = cut - 1
  end
  return s:sub(1, cut - 1) .. "…"
end
M.clip = clip

local function format_entry(entry)
  if not entry then return "" end
  if entry.pos ~= "" then return entry.pos .. " " .. entry.gloss end
  return entry.gloss
end

-- One language pair: in-memory seed + user maps, and an optional on-disk dictionary.
local function open_pair(source, target, dirs)
  local pair = source .. "-" .. target
  local mem, n = {}, 0
  for _, rel in ipairs({ "gloss/" .. pair .. ".tsv", "gloss/user_" .. pair .. ".tsv" }) do
    -- Shared directory first, so the user directory wins.
    for i = #dirs, 1, -1 do
      n = n + load_tsv(join(dirs[i], rel), mem)
    end
  end
  local dict
  for _, dir in ipairs(dirs) do
    local path = join(dir, "gloss/dict/" .. pair .. ".tsv")
    local f = io.open(path, "rb")
    if f then
      f:close()
      dict = path
      break
    end
  end
  return { target = target, mem = mem, dict = dict, size = n }
end
M.open_pair = open_pair

-- Katakana to hiragana (ア..ヶ -> あ..ゖ); dictionaries list kana readings in hiragana.
local function katakana_to_hiragana(text)
  if not text:find("\xE3[\x82\x83]") then return text end
  local ok, out = pcall(function()
    local cps = {}
    for _, cp in utf8.codes(text) do
      cps[#cps + 1] = (cp >= 0x30A1 and cp <= 0x30F6) and cp - 0x60 or cp
    end
    return utf8.char(table.unpack(cps))
  end)
  return ok and out or text
end
M.katakana_to_hiragana = katakana_to_hiragana

-- On a miss, a second lookup in a normalised form, per input language.
local FOLDS = {
  en = string.lower, -- candidates may be capitalised ("Hello")
  ja = katakana_to_hiragana, -- ネコ finds ねこ
}

local function lookup(pair, text, fold)
  local hit = pair.mem[text]
  if not hit and pair.dict then hit = search_sorted(pair.dict, text) end
  if not hit and fold then
    local folded = fold(text)
    if folded ~= text then return lookup(pair, folded, nil) end
  end
  return hit
end
M.lookup = lookup

local function config_string(config, path)
  local ok, value = pcall(function() return config:get_string(path) end)
  if ok and value and value ~= "" then return value end
  return nil
end

local function config_list(config, path)
  local ok, values = pcall(function()
    local list = config:get_list(path)
    if not list then return nil end
    local out = {}
    for i = 0, list.size - 1 do
      local item = list:get_value_at(i)
      if item and item.value and item.value ~= "" then out[#out + 1] = item.value end
    end
    return out
  end)
  if ok and values and #values > 0 then return values end
  return nil
end

-- The pairs to show now: none for off, every pair for all, otherwise one.
local function active_pairs(env)
  local ctx = env.engine.context
  if ctx:get_option("gloss_off") then return {} end
  if ctx:get_option("gloss_all") then return env.pairs end
  for _, pair in ipairs(env.pairs) do
    if ctx:get_option("gloss_" .. pair.target) then return { pair } end
  end
  if env.default == "off" then return {} end
  if env.default == "all" then return env.pairs end
  for _, pair in ipairs(env.pairs) do
    if pair.target == env.default then return { pair } end
  end
  return { env.pairs[1] }
end

local function apply_comment(cand, extra)
  if extra == "" then return end
  local old = cand.comment or ""
  local merged = old ~= "" and (old .. " | " .. extra) or extra
  cand.comment = merged
  if cand.get_genuine then
    local genuine = cand:get_genuine()
    if genuine then genuine.comment = merged end
  end
end

-- The gloss text for one candidate given the active pairs.
local function gloss_for(text, active, fold)
  if text == "" or #text > MAX_KEY or #active == 0 then return "" end
  if #active == 1 then
    return clip(format_entry(lookup(active[1], text, fold)), MAX_ONE)
  end
  local parts = {}
  for _, pair in ipairs(active) do
    local one = clip(format_entry(lookup(pair, text, fold)), MAX_ONE)
    if one ~= "" then parts[#parts + 1] = pair.target .. ": " .. one end
  end
  return clip(table.concat(parts, " · "), MAX_ALL)
end
M.gloss_for = gloss_for

local function filter(input, env)
  local active = active_pairs(env)
  for cand in input:iter() do
    if #active > 0 then
      apply_comment(cand, gloss_for(cand.text or "", active, env.fold))
    end
    yield(cand)
  end
end

local function init(env)
  local config = env.engine.schema.config
  local source = config_string(config, "rime_gloss/source") or "zh"
  local targets = config_list(config, "rime_gloss/targets") or { "en" }
  local dirs = data_dirs()
  env.pairs = {}
  local summary = {}
  for _, target in ipairs(targets) do
    local pair = open_pair(source, target, dirs)
    env.pairs[#env.pairs + 1] = pair
    summary[#summary + 1] = string.format("%s-%s mem=%d dict=%s", source, target, pair.size, pair.dict and "yes" or "no")
  end
  env.default = config_string(config, "rime_gloss/default") or targets[1]
  env.fold = FOLDS[source]
  if log then log.info("[rime-gloss] " .. table.concat(summary, "; ") .. " default=" .. env.default) end
end

M.init = init
M.func = filter
return M
