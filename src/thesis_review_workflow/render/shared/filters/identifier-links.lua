-- Make bare scholarly identifiers clickable: "DOI 10.xxxx/..." -> https://doi.org/...,
-- "arXiv NNNN.NNNNN" -> https://arxiv.org/abs/... . Structural parsing of identifier
-- syntax only; text already inside a Markdown link is left alone.
traverse = "topdown"

-- The forms match `check_feedback_output.py::BARE_IDENTIFIER_RE`, which warns about the
-- same identifiers in the Markdown: "DOI 10.x/y", "DOI: 10.x/y", "doi:10.x/y",
-- "arXiv 2401.12345", "arXiv:2401.12345v2".
-- Split trailing punctuation off an identifier, but give back each closing parenthesis
-- that balances an opening one inside it: "10.1000/x(2026))." keeps "(2026)".
local function split_trailing(s)
  local core, tail = s:match("^(.-)([%.,;:%)]*)$")
  local _, opens = core:gsub("%(", "")
  local _, closes = core:gsub("%)", "")
  while opens > closes and tail:sub(1, 1) == ")" do
    core, tail, closes = core .. ")", tail:sub(2), closes + 1
  end
  return core, tail
end

local function url_for(kind, ident)
  kind = kind:lower()
  if kind == "doi" and ident:match("^10%.%d+/%S+$") then
    return "https://doi.org/" .. ident
  elseif kind == "arxiv" and ident:match("^%d%d%d%d%.%d%d%d%d%d?v?%d*$") then
    return "https://arxiv.org/abs/" .. ident
  end
end

-- Link inlines for "(label ident" + trailing punctuation, or nil when it is no identifier.
local function linked(open, label, ident_text, url_label)
  local ident, tail = split_trailing(ident_text)
  local url = url_for(label:gsub(":$", ""), ident)
  if not url then return nil end
  local out = pandoc.Inlines({})
  if open ~= "" then out:insert(pandoc.Str(open)) end
  out:insert(pandoc.Link(url_label(ident), url))
  if tail ~= "" then out:insert(pandoc.Str(tail)) end
  return out
end

-- "doi:10.x/y" or "arXiv:2401.12345" as one token.
local function single(str)
  local open, label, rest = str.text:match("^(%(?)(%a+):(%S+)$")
  if not open then return nil end
  return linked(open, label, rest, function(ident) return { pandoc.Str(label .. ":" .. ident) } end)
end

-- "DOI 10.x/y", "DOI: 10.x/y", "arXiv 2401.12345" as label, space, identifier.
local function pair(a, b)
  local open, label = a.text:match("^(%(?)(%a+:?)$")
  if not open then return nil end
  return linked(open, label, b.text, function(ident)
    return { pandoc.Str(label), pandoc.Space(), pandoc.Str(ident) }
  end)
end

function Inlines(inl)
  local out, i = pandoc.Inlines({}), 1
  while i <= #inl do
    local a, sp, b = inl[i], inl[i + 1], inl[i + 2]
    local replaced = nil
    if a.t == "Str" and sp and sp.t == "Space" and b and b.t == "Str" then
      replaced = pair(a, b)
      if replaced then out:extend(replaced); i = i + 3 end
    end
    if not replaced and a.t == "Str" then
      replaced = single(a)
      if replaced then out:extend(replaced); i = i + 1 end
    end
    if not replaced then out:insert(a); i = i + 1 end
  end
  return out
end

-- Do not descend into existing links, so their text is never re-linked.
function Link(el) return el, false end
