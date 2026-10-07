-- Render-time layout for a topic brief projection, outputs/student_brief_<variant>.md.
-- The Markdown keeps the projection contract of docs/assignment-authoring.md unchanged;
-- this filter only fits it to the shared masthead. The headings arrive from render-brief
-- in render-values.json (see `render_values`), so this file carries no language:
--   projection title (H1)       -> dropped; the masthead carries the title
--   brief content headings (H3) -> section headings (H2), level with the variant delta
--   variant delta heading (H2)  -> its text without the " - <variant>" suffix
-- Only those exact headings are touched; every other block renders as written.

-- Read here and assigned to the metadata, the values override any front matter in the
-- source, which must never drop the draft stamp. Plain strings become MetaString
-- values, so a topic is printed literally rather than parsed as Markdown.
local function render_values()
  local path = pandoc.path.join({ pandoc.path.directory(quarto.doc.input_file), "render-values.json" })
  local handle = io.open(path, "rb")
  if handle == nil then error("render-brief values missing: " .. path) end
  local data = handle:read("a")
  handle:close()
  return pandoc.json.decode(data, false)
end

local function as_set(list)
  local set = {}
  for _, item in ipairs(list or {}) do set[item] = true end
  return set
end

function Pandoc(doc)
  local values = render_values()
  local headings = values.headings
  doc.meta.lang = values.lang
  doc.meta.masthead = values.masthead
  doc.meta.title = values.title
  -- Inlines, not a string: Quarto would parse "7. 10. 2026" as a date and reorder it.
  doc.meta.date = pandoc.Inlines({ pandoc.Str(values.date) })

  local content = as_set(headings.content)
  local out, title_seen = pandoc.Blocks({}), false
  for _, b in ipairs(doc.blocks) do
    local name = (b.t == "Header") and pandoc.utils.stringify(b.content) or nil
    if name and b.level == 1 and name == headings.title and not title_seen then
      title_seen = true
    elseif name and b.level == 3 and content[name] then
      out:insert(pandoc.Header(2, b.content, b.attr))
    elseif name and b.level == 2 and name == headings.delta then
      out:insert(pandoc.Header(2, pandoc.Inlines(headings.delta_display), b.attr))
    else
      out:insert(b)
    end
  end
  doc.blocks = out
  return doc
end
