-- Render-time layout for outputs/feedback_student.md. The Markdown keeps the
-- supervisor-feedback skill's section contract unchanged; this filter only maps
-- headings of that contract to blocks. The headings arrive from render-feedback in
-- render-values.json (see `render_values`), so this file carries no language:
--   H1 and the review-date line -> title block metadata
--   scope section               -> note block
--   progress / working-well     -> tip block
--   priority table              -> one card per row (P0 caution, P1 important, P2 tip)
-- Every other section renders as plain text by design.

local NBSP = "\u{00A0}"

local EN_MONTHS = {
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
}

-- render-feedback writes the language, masthead fields, section headings and the
-- draft stamp to render-values.json beside the Markdown. Read here and assigned to the
-- metadata, they override any front matter in the source, which must never drop the
-- draft stamp or the section mapping. Plain strings become MetaString values, so a topic
-- is printed literally rather than parsed as Markdown.
local function render_values()
  local path = pandoc.path.join({ pandoc.path.directory(quarto.doc.input_file), "render-values.json" })
  local handle = io.open(path, "rb")
  if handle == nil then error("render-feedback values missing: " .. path) end
  local data = handle:read("a")
  handle:close()
  return pandoc.json.decode(data, false)
end

local function as_set(list)
  local set = {}
  for _, item in ipairs(list or {}) do set[item] = true end
  return set
end

-- A date in Typst content must not look like "6. 10. 2026" with plain spaces: Typst
-- reads "6. " at the start of a line as an enumerated-list marker.
local function display_date(raw, lang)
  local y, m, d = raw:match("^(%d%d%d%d)%-(%d%d)%-(%d%d)$")
  local text = raw
  if y then
    if lang == "en" then
      text = tonumber(d) .. " " .. EN_MONTHS[tonumber(m)] .. " " .. y
    else
      text = tonumber(d) .. ". " .. tonumber(m) .. ". " .. y
    end
  end
  return (text:gsub(" ", NBSP))
end

-- A callout whose title is a heading, so links and emphasis in the title survive;
-- Quarto takes a callout's leading heading as its title.
local function callout(kind, title, blocks)
  local content = pandoc.Blocks({ pandoc.Header(3, title) }) .. blocks
  return pandoc.Div(content, pandoc.Attr("", { "callout-" .. kind }))
end

local PRIORITY_KIND = { P0 = "caution", P1 = "important" }

-- Labelled cell blocks: "**Label.** text" when the cell opens with text, else a lead line.
local function labelled(label, blocks)
  local lead = pandoc.Inlines({ pandoc.Strong(label .. "."), pandoc.Space() })
  local first = blocks[1]
  if first.t == "Para" or first.t == "Plain" then
    return pandoc.Blocks({ pandoc.Para(lead .. first.content) }) .. pandoc.Blocks({ table.unpack(blocks, 2) })
  end
  return pandoc.Blocks({ pandoc.Para({ pandoc.Strong(label .. ".") }) }) .. blocks
end

-- One card per priority row. Column 1 is the priority (the checker requires it first);
-- the area column, found by its header, joins the card title; every other non-empty cell
-- becomes a labelled paragraph. A table without a header row is left as a table.
local function priority_cards(tbl, area_header)
  if #tbl.head.rows == 0 then return pandoc.Blocks({ tbl }) end
  local labels, area_index = {}, nil
  for i, cell in ipairs(tbl.head.rows[1].cells) do
    labels[i] = pandoc.utils.stringify(cell.contents)
    if labels[i] == area_header then area_index = i end
  end
  local cards = pandoc.Blocks({})
  for _, body in ipairs(tbl.bodies) do
    for _, row in ipairs(body.body) do
      local prio = pandoc.utils.stringify(row.cells[1].contents):upper()
      local title = pandoc.Inlines({ pandoc.Str(prio) })
      local inner = pandoc.Blocks({})
      for i = 2, #row.cells do
        local blocks = row.cells[i].contents
        if i == area_index then
          if #blocks > 0 then
            title:extend({ pandoc.Space(), pandoc.Str("·"), pandoc.Space() })
            title:extend(pandoc.utils.blocks_to_inlines(blocks))
          end
        elseif #blocks > 0 then
          inner:extend(labelled(labels[i] or "", blocks))
        end
      end
      cards:insert(callout(PRIORITY_KIND[prio] or "tip", title, inner))
    end
  end
  return cards
end

function Pandoc(doc)
  local values = render_values()
  doc.meta.lang = values.lang
  doc.meta.masthead = values.masthead
  local sections = values.sections
  local lang = values.lang
  local date_label = sections.date_label
  local scope = sections.scope
  local priority = sections.priority
  local area_header = sections.area_header
  local tips = as_set(sections.tips)

  local out, blocks, i = pandoc.Blocks({}), doc.blocks, 1
  while i <= #blocks do
    local b = blocks[i]
    local text = (b.t == "Para") and pandoc.utils.stringify(b.content) or nil
    if b.t == "Header" and b.level == 1 and not doc.meta.title then
      doc.meta.title = b.content
      i = i + 1
    elseif text and date_label and text:sub(1, #date_label) == date_label then
      local raw = text:sub(#date_label + 1):match("^%s*(.-)%s*$")
      doc.meta.date = pandoc.Inlines({ pandoc.Str(display_date(raw, lang)) })
      i = i + 1
    elseif b.t == "Header" and b.level == 2 then
      local name = pandoc.utils.stringify(b.content)
      local j, section = i + 1, pandoc.Blocks({})
      while j <= #blocks and not (blocks[j].t == "Header" and blocks[j].level <= 2) do
        section:insert(blocks[j]); j = j + 1
      end
      if name == scope then
        out:insert(callout("note", b.content, section))
      elseif tips[name] then
        out:insert(callout("tip", b.content, section))
      elseif name == priority then
        out:insert(b)
        for _, s in ipairs(section) do
          if s.t == "Table" then out:extend(priority_cards(s, area_header)) else out:insert(s) end
        end
      else
        out:insert(b); out:extend(section)
      end
      i = j
    else
      out:insert(b); i = i + 1
    end
  end
  doc.blocks = out
  return doc
end
