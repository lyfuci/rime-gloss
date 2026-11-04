-- rime-gloss: show EN/JA part-of-speech + short gloss beside Chinese candidates.
-- Loaded as lua_filter@rime_gloss_filter

local MAX_ONE = 42
local MAX_BOTH = 72

local function user_dir()
  if rime_api and rime_api.get_user_data_dir then
    return rime_api.get_user_data_dir()
  end
  return ""
end

local function join(dir, rel)
  local sep = package.config:sub(1, 1)
  if dir == "" then
    return rel
  end
  if dir:sub(-1) == "/" or dir:sub(-1) == "\\" then
    return dir .. rel:gsub("/", sep)
  end
  return dir .. sep .. rel:gsub("/", sep)
end

local function trim(s)
  return (s:gsub("^%s+", ""):gsub("%s+$", ""))
end

local function load_tsv(path, into)
  local f = io.open(path, "r")
  if not f then
    return 0, "missing"
  end
  local n = 0
  for line in f:lines() do
    line = line:gsub("\r$", "")
    if line ~= "" and line:sub(1, 1) ~= "#" then
      local text, gloss, pos = line:match("^([^\t]+)\t([^\t]+)\t?([^\t]*)$")
      if text and gloss then
        text = trim(text)
        gloss = trim(gloss)
        pos = trim(pos or "")
        if text ~= "" and gloss ~= "" then
          into[text] = { gloss = gloss, pos = pos }
          n = n + 1
        end
      end
    end
  end
  f:close()
  return n, "ok"
end

local function load_map(rel_paths)
  local map = {}
  local dir = user_dir()
  local total = 0
  for _, rel in ipairs(rel_paths) do
    local path = join(dir, rel)
    local n, status = load_tsv(path, map)
    total = total + n
    if log then
      log.info(string.format("[rime-gloss] %s %s entries=%d", status, rel, n))
    end
  end
  return map, total
end

local function clip(s, limit)
  if not s or s == "" then
    return ""
  end
  -- UTF-8 safe enough for short glosses: cut on byte length, then back up to a lead byte.
  if #s <= limit then
    return s
  end
  local cut = limit
  while cut > 1 do
    local b = s:byte(cut)
    if b < 128 or b >= 192 then
      break
    end
    cut = cut - 1
  end
  if cut < 1 then
    cut = 1
  end
  return s:sub(1, cut - 1) .. "…"
end

local function format_one(entry)
  if not entry then
    return ""
  end
  if entry.pos ~= "" then
    return entry.pos .. " " .. entry.gloss
  end
  return entry.gloss
end

local function mode_of(env)
  local ctx = env.engine.context
  if ctx:get_option("gloss_off") then
    return "off"
  end
  if ctx:get_option("gloss_both") then
    return "both"
  end
  if ctx:get_option("gloss_ja") and not ctx:get_option("gloss_en") then
    return "ja"
  end
  if ctx:get_option("gloss_en") and not ctx:get_option("gloss_ja") then
    return "en"
  end
  -- Both language switches on, or neither configured: honor default.
  if ctx:get_option("gloss_ja") and ctx:get_option("gloss_en") then
    return "both"
  end
  return env.default_mode or "en"
end

local function apply_comment(cand, extra)
  if extra == "" then
    return
  end
  local old = cand.comment or ""
  local merged = extra
  if old ~= "" then
    merged = old .. " | " .. extra
  end
  cand.comment = merged
  if cand.get_genuine then
    local genuine = cand:get_genuine()
    if genuine then
      genuine.comment = merged
    end
  end
end

local function filter(input, env)
  local mode = mode_of(env)
  for cand in input:iter() do
    if mode ~= "off" then
      local text = cand.text or ""
      local en = mode ~= "ja" and env.en[text] or nil
      local ja = mode ~= "en" and env.ja[text] or nil
      local extra = ""
      if mode == "both" then
        local a = format_one(en)
        local b = format_one(ja)
        if a ~= "" and b ~= "" then
          extra = clip(a .. " · " .. b, MAX_BOTH)
        else
          extra = clip(a ~= "" and a or b, MAX_ONE)
        end
      elseif mode == "ja" then
        extra = clip(format_one(ja), MAX_ONE)
      else
        extra = clip(format_one(en), MAX_ONE)
      end
      apply_comment(cand, extra)
    end
    yield(cand)
  end
end

local function init(env)
  env.en = {}
  env.ja = {}
  local en_n, ja_n
  env.en, en_n = load_map({ "gloss/en.tsv", "gloss/user_en.tsv" })
  env.ja, ja_n = load_map({ "gloss/ja.tsv", "gloss/user_ja.tsv" })
  env.default_mode = "en"
  local ok, value = pcall(function()
    return env.engine.schema.config:get_string("rime_gloss/default")
  end)
  if ok and value and value ~= "" then
    env.default_mode = value
  end
  if log then
    log.info(string.format("[rime-gloss] ready en=%d ja=%d default=%s", en_n, ja_n, env.default_mode))
  end
end

return { init = init, func = filter }
