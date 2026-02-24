-- table-callouts.lua
-- Converts Obsidian-style table header callouts to styled tables
--
-- Syntax in Markdown (visible/editable in Obsidian):
--
-- > [!table] #tbl:my-label width=100% fontsize=small spacing=1.2
-- >
-- > This is my **caption** with *formatting*.
--
-- | Col 1 | Col 2 | Col 3 |
-- |-------|-------|-------|
-- | A     | B     | C     |
--
-- Options:
--   #tbl:label    - pandoc-crossref table label
--   width=X       - table width: 100%, 80%, \textwidth, \linewidth (default: full width)
--   fontsize=X    - LaTeX size: tiny, scriptsize, footnotesize, small, normalsize, large
--   spacing=X     - row spacing multiplier (arraystretch, default: 1.0)
--   align=X       - table alignment: left, center, right (default: center)
--
-- Converts to a properly styled LaTeX table for PDF output.

local stringify = pandoc.utils.stringify

local function set_table_caption_from_inlines(tbl, caption_inlines)
  if caption_inlines == nil then
    return
  end

  local long_blocks = { pandoc.Plain(caption_inlines) }

  -- Pandoc 3.x uses Caption userdata; older versions used a plain table.
  if tbl.caption ~= nil and type(tbl.caption) == "userdata" then
    tbl.caption.long = long_blocks
    tbl.caption.short = nil
    return
  end

  if pandoc.Caption ~= nil then
    tbl.caption = pandoc.Caption(long_blocks, nil)
  else
    tbl.caption = { long = long_blocks, short = nil }
  end
end

local function normalize_columns(cols)
  if not cols or #cols == 0 then
    return nil
  end
  local sum = 0
  for _, w in ipairs(cols) do
    sum = sum + w
  end
  if sum == 0 then
    return nil
  end
  local normalized = {}
  for _, w in ipairs(cols) do
    table.insert(normalized, w / sum)
  end
  return normalized
end

-- Check if a block is a table callout
local function is_table_callout(block)
  if block.t ~= "BlockQuote" then
    return false
  end
  
  local content = block.content
  if #content == 0 then
    return false
  end
  
  -- First element should be a Para/Plain starting with [!table]
  local first = content[1]
  if (first.t ~= "Para" and first.t ~= "Plain") or #first.content == 0 then
    return false
  end
  
  local text = stringify(first)
  return text:match("%[!table%]")
end

local function blockquote_contains_table(block)
  if block.t ~= "BlockQuote" then
    return false
  end
  for _, b in ipairs(block.content) do
    if b.t == "Table" then
      return true
    end
  end
  return false
end

local function extract_caption_inlines_from_table_header_callout(block)
  -- For a header-only [!table] callout, treat all Para/Plain blocks after the
  -- first header line as caption content.
  -- Also handles the case where caption is on the next line without an empty
  -- separator (merged into the same Para via SoftBreak).
  local inlines = {}
  if block.t ~= "BlockQuote" then
    return nil
  end

  -- Check if the first block contains caption inlines after a SoftBreak
  local first = block.content[1]
  if first and (first.t == "Para" or first.t == "Plain") then
    local after_break = false
    for _, inline in ipairs(first.content) do
      if not after_break then
        if inline.t == "SoftBreak" or inline.t == "LineBreak" then
          after_break = true
        end
      else
        -- Skip leading whitespace after the break
        if #inlines == 0 and (inline.t == "Space" or inline.t == "SoftBreak" or inline.t == "LineBreak") then
          -- skip
        else
          table.insert(inlines, inline)
        end
      end
    end
  end

  -- Also collect from subsequent blocks (with empty line separator)
  for i = 2, #block.content do
    local b = block.content[i]
    if b.t == "Para" or b.t == "Plain" then
      if #inlines > 0 then
        table.insert(inlines, pandoc.Space())
      end
      for _, inline in ipairs(b.content) do
        table.insert(inlines, inline)
      end
    end
  end

  if #inlines == 0 then
    return nil
  end
  return inlines
end

-- Parse options from the header line
local function parse_options(header_text)
  local opts = {
    label = nil,
    width = nil,  -- nil means no width constraint (natural width)
    fontsize = nil,
    spacing = nil,
    align = "center",
    span = nil,
    columns = nil,
    colsep = nil,
    family = nil,
    pos = nil,
    wrap = nil
  }
  
  -- Extract label (#tbl:something)
  opts.label = header_text:match("#(tbl:[%w%-_]+)")
  
  -- Extract width (width=100% or width=\textwidth)
  local width = header_text:match("width=([%d%%%.\\%a]+)")
  if width then
    opts.width = width
  end
  
  -- Extract fontsize
  local fontsize = header_text:match("fontsize=(%w+)")
  if fontsize then
    local valid_sizes = {
      tiny = true, scriptsize = true, footnotesize = true,
      small = true, normalsize = true, large = true,
      Large = true, LARGE = true, huge = true, Huge = true
    }
    if valid_sizes[fontsize] then
      opts.fontsize = fontsize
    end
  end
  
  -- Extract spacing (arraystretch)
  local spacing = header_text:match("spacing=([%d%.]+)")
  if spacing then
    opts.spacing = tonumber(spacing)
  end

  -- Extract column widths (relative weights)
  local columns = header_text:match("columns=([%d%.]+[%d%.,]*)")
  if columns then
    local col_widths = {}
    for w in columns:gmatch("([%d%.]+)") do
      table.insert(col_widths, tonumber(w))
    end
    if #col_widths > 0 then
      opts.columns = normalize_columns(col_widths)
    end
  end

  -- Extract horizontal padding between columns
  local colsep = header_text:match("colsep=([%d%.]+%a+)")
  if colsep then
    opts.colsep = colsep
  end

  -- Extract LaTeX font family
  local family = header_text:match("family=(%w+)")
  if family then
    local valid_families = { rmfamily = true, sffamily = true, ttfamily = true }
    if valid_families[family] then
      opts.family = family
    end
  end
  
  -- Extract alignment
  local align = header_text:match("align=(%w+)")
  if align then
    if align == "left" or align == "center" or align == "right" then
      opts.align = align
    end
  end

  -- Extract spanning behavior
  local span = header_text:match("span=(%w+)")
  if span == "full" then
    opts.span = span
  end

  -- Extract position (pos=h, t, b, p, !, H)
  opts.pos = header_text:match("pos=([%a!]+)") or header_text:match("placement=([%a!]+)")

  -- Extract wrap (wrap=l, r, i, o, L, R, I, O)
  opts.wrap = header_text:match("wrap=([a-zA-Z]+)")
  
  return opts
end

local function style_table(tbl, opts)
  local function parse_width_fraction(width_str)
    if not width_str then
      return nil
    end
    if width_str:match("%%$") then
      local pct = tonumber(width_str:match("^([%d%.]+)%%$") or width_str:match("^([%d%.]+)\\%%$"))
      if pct then
        return pct / 100
      end
      return nil
    end
    if width_str == "\\linewidth" or width_str == "\\textwidth" then
      return 1.0
    end
    local num = width_str:match("^([%d%.]+)\\linewidth$") or width_str:match("^([%d%.]+)\\textwidth$")
    if num then
      return tonumber(num)
    end
    return nil
  end

  -- Preserve existing attrs and set metadata for other filters
  local id = (opts.label) or (tbl.attr and tbl.attr.identifier) or ""
  local classes = (tbl.attr and tbl.attr.classes) or {}
  local attrs = {}
  if tbl.attr and tbl.attr.attributes then
    for k, v in pairs(tbl.attr.attributes) do
      attrs[k] = v
    end
  end
  if opts.align ~= nil and opts.align ~= "" then attrs["md-align"] = opts.align end
  if opts.span ~= nil and opts.span ~= "" then attrs["md-span"] = opts.span end
  if opts.pos ~= nil and opts.pos ~= "" then attrs["md-pos"] = opts.pos end
  if opts.wrap ~= nil and opts.wrap ~= "" then attrs["md-wrap"] = opts.wrap end
  
  tbl.attr = pandoc.Attr(id, classes, attrs)

  local is_latex = (FORMAT and (FORMAT:match("latex") or FORMAT:match("pdf"))) ~= nil

  -- Apply column widths
  if is_latex and tbl.colspecs and #tbl.colspecs > 0 then
    local ncols = #tbl.colspecs
    local weights = opts.columns or {}
    if #weights ~= ncols then
      weights = {}
      for _ = 1, ncols do table.insert(weights, 1 / ncols) end
    end

    local width_frac = parse_width_fraction(opts.width) or 1.0
    local new_colspecs = {}
    for i, cs in ipairs(tbl.colspecs) do
      new_colspecs[i] = { cs[1], weights[i] * width_frac }
    end
    tbl.colspecs = new_colspecs
  end

  -- Apply alignment and caption styling
  if is_latex and opts.align then
    local setup = nil
    if opts.align == "left" then
      setup = "\\captionsetup{justification=raggedright,singlelinecheck=off}"
    elseif opts.align == "right" then
      setup = "\\captionsetup{justification=raggedleft,singlelinecheck=off}"
    end
    
    if setup then
      return {
        pandoc.RawBlock("latex", "\\begingroup" .. setup),
        tbl,
        pandoc.RawBlock("latex", "\\endgroup")
      }
    end
  end

  return tbl
end

function Blocks(blocks)
  local out = {}
  local pending_opts = nil
  local pending_caption_inlines = nil

  for _, blk in ipairs(blocks) do
    if blk.t == "BlockQuote" and is_table_callout(blk) and not blockquote_contains_table(blk) then
      pending_opts = parse_options(stringify(blk.content[1]))
      pending_caption_inlines = extract_caption_inlines_from_table_header_callout(blk)
    elseif pending_opts ~= nil and blk.t == "RawBlock" and (blk.format == "latex" or blk.format == "tex") then
      table.insert(out, blk)
    elseif blk.t == "Table" and pending_opts ~= nil then
      if pending_caption_inlines ~= nil then
        set_table_caption_from_inlines(blk, pending_caption_inlines)
      end

      local styled = style_table(blk, pending_opts)
      if styled ~= nil and styled.t ~= nil then
        table.insert(out, styled)
      elseif type(styled) == "table" then
        for _, b in ipairs(styled) do table.insert(out, b) end
      end

      pending_opts = nil
      pending_caption_inlines = nil
    else
      table.insert(out, blk)
    end
  end

  return out
end

local function process_citation_spacing(inlines)
  local i = 1
  while i < #inlines do
    local current = inlines[i]
    if current.t == "Cite" and #current.citations == 1 then
      local id = current.citations[1].id
      if id:match("^[Tt]bl:") or id:match("^[Ff]ig:") then
        -- Handle suffix inside Cite
        local citation = current.citations[1]
        if #citation.suffix > 0 and citation.suffix[1].t == "Space" then
          table.remove(citation.suffix, 1)
        end

        -- Handle suffix outside Cite (narrative style)
        local next_inline = inlines[i+1]
        local third_inline = inlines[i+2]
        if next_inline and next_inline.t == "Space" and third_inline and third_inline.t == "Str" then
           if #third_inline.text <= 2 then
             table.remove(inlines, i+1)
           end
        end
      end
    end
    i = i + 1
  end
  return inlines
end

function Para(para)
  para.content = process_citation_spacing(para.content)
  return para
end

function Plain(plain)
  plain.content = process_citation_spacing(plain.content)
  return plain
end

function Strong(strong)
  strong.content = process_citation_spacing(strong.content)
  return strong
end

function Emph(emph)
  emph.content = process_citation_spacing(emph.content)
  return emph
end

return {
  {Meta = function(meta) return nil end},
  {Blocks = Blocks},
  {Para = Para, Plain = Plain, Strong = Strong, Emph = Emph}
}
