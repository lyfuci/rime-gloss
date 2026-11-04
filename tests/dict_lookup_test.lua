-- The filter's on-disk binary search against the real gloss/dict/ files:
-- `lua5.4 tests/dict_lookup_test.lua` from the repository root.
local sep = package.config:sub(1, 1)
package.path = "lua" .. sep .. "?.lua;" .. package.path
local G = require("rime_gloss_filter")

local total, files = 0, 0
for _, pair in ipairs({ "zh-en", "ja-en", "en-zh" }) do
  local path = "gloss" .. sep .. "dict" .. sep .. pair .. ".tsv"
  local f = io.open(path, "rb")
  if f then
    files = files + 1
    local n, sampled = 0, {}
    for line in f:lines() do
      n = n + 1
      if n % 997 == 1 then sampled[#sampled + 1] = line end
    end
    f:close()
    local started = os.clock()
    for _, line in ipairs(sampled) do
      local key, gloss = line:match("^([^\t]+)\t([^\t]+)")
      local hit = G.search_sorted(path, key)
      assert(hit and hit.gloss == gloss, pair .. ": lookup failed for " .. key)
    end
    for _, absent in ipairs({ "", "\xef\xbf\xbf", "zzzzzzzz-not-a-word", "\x01" }) do
      assert(G.search_sorted(path, absent) == nil, pair .. ": absent key matched")
    end
    local per = (os.clock() - started) / (#sampled + 4) * 1000
    print(string.format("%s: %d lines, %d sampled lookups ok, %.3f ms per lookup", pair, n, #sampled, per))
    total = total + #sampled
  end
end
assert(files > 0, "no gloss/dict files; run tools/build_dicts.py first")
print(string.format("dict_lookup_test: %d lookups passed", total))
