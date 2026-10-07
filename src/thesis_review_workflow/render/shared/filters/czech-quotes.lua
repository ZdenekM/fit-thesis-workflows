-- Pandoc's Typst writer turns a literal closing quote (U+201C) into Typst's smart `"` but
-- keeps the opening low quote (U+201E) as text, so Typst never sees the quote open and
-- renders the closing one as „ again. Emit the opening quote as a smart `"` too; with
-- `lang: cs` Typst then sets the pair as „…“.
local LOW = "\u{201E}"

function Str(el)
  if not el.text:find(LOW, 1, true) then return nil end
  local out, rest = pandoc.List(), el.text
  while true do
    local i = rest:find(LOW, 1, true)
    if not i then break end
    if i > 1 then out:insert(pandoc.Str(rest:sub(1, i - 1))) end
    out:insert(pandoc.RawInline("typst", '"'))
    rest = rest:sub(i + #LOW)
  end
  if #rest > 0 then out:insert(pandoc.Str(rest)) end
  return out
end
