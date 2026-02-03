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
  local inlines = {}
  if block.t ~= "BlockQuote" then
    return nil
  end

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
    family = nil
  }
  
  -- Extract label (#tbl:something)
  opts.label = header_text:match("#(tbl:[%w%-_]+)")
  
  -- Extract width (width=100% or width=\textwidth)
  local width = header_text:match("width=([%d%%%.\\%a]+)")
  if width then
    -- Keep percentages in Pandoc-friendly form; convert later when computing fractions.
    opts.width = width
  end
  
  -- Extract fontsize
  local fontsize = header_text:match("fontsize=(%w+)")
  if fontsize then
    -- Validate it's a known LaTeX size
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
  -- Example: columns=0.2,0.4,0.3,0.1  (will be normalized to sum=1)
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
  -- Example: colsep=4pt or colsep=2pt
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

  -- Extract spanning behavior (two-column helpers)
  local span = header_text:match("span=(%w+)")
  if span == "full" then
    opts.span = span
  end
  
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
    if width_str == "\\linewidth" then
      return 1.0
    end
    if width_str == "\\textwidth" then
      return 1.0
    end
    local num = width_str:match("^([%d%.]+)\\linewidth$")
    if num then
      return tonumber(num)
    end
    local num_tw = width_str:match("^([%d%.]+)\\textwidth$")
    if num_tw then
      return tonumber(num_tw)
    end
    return nil
  end

  -- Preserve existing attrs, set ID for pandoc-crossref, and attach our alignment
  -- so downstream filters (e.g. no-longtable.lua) can honor it.
  do
    local id = (opts.label) or (tbl.attr and tbl.attr.identifier) or ""
    local classes = (tbl.attr and tbl.attr.classes) or {}
    local attrs = {}
    if tbl.attr and tbl.attr.attributes then
      for k, v in pairs(tbl.attr.attributes) do
        attrs[k] = v
      end
    end
    if opts.align ~= nil and opts.align ~= "" then
      attrs["md-align"] = opts.align
    end
    if opts.span ~= nil and opts.span ~= "" then
      attrs["md-span"] = opts.span
    end
    if id ~= "" or #classes > 0 or next(attrs) ~= nil then
      tbl.attr = pandoc.Attr(id, classes, attrs)
    end
  end

  local is_latex = (FORMAT and (FORMAT:match("latex") or FORMAT:match("pdf"))) ~= nil

  -- Width control via colspec widths (safe with longtable).
  -- If columns=... is provided, use it as relative weights.
  -- If width=... is a numeric fraction of \linewidth, scale total width.
  if is_latex and tbl.colspecs and #tbl.colspecs > 0 then
    local ncols = #tbl.colspecs
    local weights = nil

    if opts.columns and #opts.columns == ncols then
      weights = opts.columns
    else
      weights = {}
      for _ = 1, ncols do
        table.insert(weights, 1 / ncols)
      end
    end

    local width_frac = parse_width_fraction(opts.width)
    if width_frac == nil then
      width_frac = 1.0
    end

    local new_colspecs = {}
    for i, cs in ipairs(tbl.colspecs) do
      local align = cs[1]
      local w = weights[i] * width_frac
      new_colspecs[i] = { align, w }
    end
    tbl.colspecs = new_colspecs
  end

  local needs_styling = is_latex and (opts.align or opts.fontsize or opts.spacing or opts.colsep or opts.family)
  if not needs_styling then
    return tbl
  end

  local result = {}

  local preamble_parts = {}
  table.insert(preamble_parts, "\\begingroup")

  -- Table placement (PDF/LaTeX only).
  -- This does NOT affect per-column alignment from the Markdown alignment row (:-: etc.).
  -- It only controls how the whole table block is positioned.
  -- Guard against profiles/filters that remove the Table AST (e.g. no-longtable.lua),
  -- which can cause pandoc not to include the longtable package.
  table.insert(preamble_parts, "\\ifcsname LTleft\\endcsname\\else\\newlength{\\LTleft}\\fi")
  table.insert(preamble_parts, "\\ifcsname LTright\\endcsname\\else\\newlength{\\LTright}\\fi")
  if opts.align == "left" then
    table.insert(preamble_parts, "\\setlength{\\LTleft}{0pt}")
    table.insert(preamble_parts, "\\setlength{\\LTright}{\\fill}")
    table.insert(preamble_parts, "\\ifcsname captionsetup\\endcsname\\captionsetup{justification=raggedright,singlelinecheck=false}\\fi")
  elseif opts.align == "right" then
    table.insert(preamble_parts, "\\setlength{\\LTleft}{\\fill}")
    table.insert(preamble_parts, "\\setlength{\\LTright}{0pt}")
    table.insert(preamble_parts, "\\ifcsname captionsetup\\endcsname\\captionsetup{justification=raggedleft,singlelinecheck=false}\\fi")
  else
    -- default: center
    table.insert(preamble_parts, "\\setlength{\\LTleft}{\\fill}")
    table.insert(preamble_parts, "\\setlength{\\LTright}{\\fill}")
    table.insert(preamble_parts, "\\ifcsname captionsetup\\endcsname\\captionsetup{justification=centering,singlelinecheck=false}\\fi")
  end

  if opts.fontsize then
    table.insert(preamble_parts, "\\" .. opts.fontsize)
  end

  if opts.family then
    table.insert(preamble_parts, "\\" .. opts.family)
  end

  if opts.spacing then
    table.insert(preamble_parts, string.format("\\renewcommand{\\arraystretch}{%.2f}", opts.spacing))
  end

  if opts.colsep then
    table.insert(preamble_parts, "\\setlength{\\tabcolsep}{" .. opts.colsep .. "}")
  end

  table.insert(result, pandoc.RawBlock("latex", table.concat(preamble_parts, "\n")))
  table.insert(result, tbl)

  local postamble_parts = {}
  table.insert(postamble_parts, "\\endgroup")
  table.insert(result, pandoc.RawBlock("latex", table.concat(postamble_parts, "\n")))

  return result
end

function Blocks(blocks)
  local out = {}
  local pending_opts = nil
  local pending_caption_inlines = nil

  for _, blk in ipairs(blocks) do
    if blk.t == "BlockQuote" and is_table_callout(blk) and not blockquote_contains_table(blk) then
      -- Figure-like table header callout:
      -- > [!table] #tbl:label width=... columns=...
      -- > Caption text...
      -- (next block is the actual Markdown table, outside the blockquote)
      pending_opts = parse_options(stringify(blk.content[1]))
      pending_caption_inlines = extract_caption_inlines_from_table_header_callout(blk)
    elseif pending_opts ~= nil and blk.t == "RawBlock" and (blk.format == "latex" or blk.format == "tex") then
      -- Allow LaTeX raw blocks (e.g. \begin{landscape}) between the [!table] header callout
      -- and the actual Markdown table.
      table.insert(out, blk)
    elseif blk.t == "Table" and pending_opts ~= nil then
      if pending_caption_inlines ~= nil then
        set_table_caption_from_inlines(blk, pending_caption_inlines)
      end

      local styled = style_table(blk, pending_opts)
      if styled ~= nil and styled.t ~= nil then
        table.insert(out, styled)
      elseif type(styled) == "table" then
        for _, b in ipairs(styled) do
          table.insert(out, b)
        end
      end

      pending_opts = nil
      pending_caption_inlines = nil
    else
      table.insert(out, blk)
    end
  end

  return out
end

return {
  {Blocks = Blocks}
}
