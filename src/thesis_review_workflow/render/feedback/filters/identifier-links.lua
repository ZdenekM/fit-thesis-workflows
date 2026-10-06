-- Make bare scholarly identifiers clickable: "DOI 10.xxxx/..." -> https://doi.org/...,
-- "arXiv NNNN.NNNNN" -> https://arxiv.org/abs/... . Structural parsing of identifier
-- syntax only; text already inside a Markdown link is left alone.
traverse = "topdown"

local function split_trailing(s)
  return s:match("^(.-)([%.,;:%)]*)$")
end

local function link_for(label, ident)
  local l = label:lower():gsub("^%(", "")
  if l == "doi" and ident:match("^10%.%d+/%S+$") then
    return "https://doi.org/" .. ident
  elseif l == "arxiv" and ident:match("^%d%d%d%d%.%d%d%d%d%d?$") then
    return "https://arxiv.org/abs/" .. ident
  end
end

function Inlines(inl)
  local out, i = pandoc.Inlines({}), 1
  while i <= #inl do
    local a, sp, b = inl[i], inl[i + 1], inl[i + 2]
    local done = false
    if a.t == "Str" and sp and sp.t == "Space" and b and b.t == "Str" then
      local ident, tail = split_trailing(b.text)
      local url = link_for(a.text, ident)
      if url then
        if a.text:match("^%(") then out:insert(pandoc.Str("(")) end
        out:insert(pandoc.Link({ pandoc.Str((a.text:gsub("^%(", ""))), pandoc.Space(), pandoc.Str(ident) }, url))
        if tail ~= "" then out:insert(pandoc.Str(tail)) end
        i, done = i + 3, true
      end
    end
    if not done then out:insert(a); i = i + 1 end
  end
  return out
end

-- Do not descend into existing links, so their text is never re-linked.
function Link(el) return el, false end
