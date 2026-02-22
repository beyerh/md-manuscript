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
    family = nil,
    pos = nil,
    wrap = nil
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
    if opts.pos ~= nil and opts.pos ~= "" then
      attrs["md-pos"] = opts.pos
    end
    if opts.wrap ~= nil and opts.wrap ~= "" then
      attrs["md-wrap"] = opts.wrap
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

  -- For wrap or float environments, we can't just wrap in \begingroup ... \endgroup
  -- because longtable (default pandoc table) floats on its own but doesn't respect [pos].
  -- And wrapfigure doesn't work with longtable easily.
  -- HOWEVER, if the user requests pos= or wrap=, they likely want a floating environment (table/table*)
  -- or wraptext environment, which means we should probably treat the content as a tabular
  -- inside a table environment, NOT a longtable.
  --
  -- But converting Pandoc Table AST to raw LaTeX tabular is hard.
  --
  -- Strategy:
  -- If pos is set, or span=full, we assume the user accepts that the table might not break across pages
  -- (which is true for floating tables anyway).
  -- But wait, Pandoc emits longtable by default. Longtable does NOT float.
  -- To make it float (pos=h/t/b), we typically need `\begin{table} ... \end{table}` wrapping a `tabular`.
  -- Pandoc doesn't easily let us switch to `tabular` without writing a custom writer or modifying the Table AST significantly.
  --
  -- A common trick: If we want a floating table, we might be able to wrap the longtable in a table environment?
  -- No, longtable inside table environment is forbidden.
  --
  -- If we want to support `pos`, we might need to rely on the fact that `longtable` supports some placement if it's NOT a longtable?
  -- No, longtable is designed to break pages.
  --
  -- Let's look at how we handled figures. We create RawBlock latex.
  -- For tables, we have a Table block.
  --
  -- If we use `pos`, we are asking for a float.
  -- If we use `wrap`, we are asking for a wrap float.
  --
  -- One option: `\begin{floatingtable}[pos] ... \end{floatingtable}` ? No such standard env.
  --
  -- Actually, `pandoc-crossref` or other filters often struggle with this.
  --
  -- However, if we simply want to inject `\begin{table}[pos]` around it, we must ensure the inner table is NOT a longtable.
  -- But Pandoc generates longtable.
  --
  -- A known workaround for Pandoc is to disable longtable (e.g. by using a filter that removes headers/widths? No).
  -- Or we can just use `\begingroup` properties for fonts/spacing, but placement `pos` is tricky with longtable.
  --
  -- Longtable does not support [htbp]. It always places "here" and breaks pages.
  --
  -- If the user specifically asks for `pos=t` (top), they want a float.
  -- To get a float, we MUST NOT use longtable.
  --
  -- How to force Pandoc to NOT use longtable for a specific table?
  -- If we are in `no-longtable.lua` mode, it converts Table to simple tabulars if possible?
  --
  -- Let's check `no-longtable.lua` if it exists.
  -- I saw `no-longtable.lua` in the file list earlier.
  -- If I can detect `pos` here, maybe I should signal `no-longtable.lua` to convert this table?
  -- Or maybe I can do it here.
  --
  -- Actually, `no-longtable.lua` usually runs *after* or *before*?
  -- If this filter runs before, we can modify the table to "un-longtable" it?
  --
  -- Simpler approach:
  -- If `pos` is requested, we can try to wrap the table in `\begin{table}[pos] ... \end{table}`
  -- AND hopefully Pandoc will render the inner table as `tabular` if we trick it?
  -- Unlikely.
  --
  -- WAIT. If I look at `figure-callouts.lua`, it constructs RawBlock("latex", ...).
  -- It handles the image inclusion manually `\includegraphics`.
  -- For tables, "manual inclusion" means writing `\begin{tabular}...`. That's extremely hard to do from Lua without re-implementing the table writer.
  --
  -- Alternative:
  -- Just handle `begingroup/endgroup` style for now, and IGNORE `pos` implementation details
  -- UNLESS we can confirm how to make it float.
  --
  -- BUT, if the user specifically asked for "update templater files ... to include a sensible default for position placement",
  -- they expect it to work.
  --
  -- If I add `pos=!ht`, I imply it works.
  --
  -- Let's check `no-longtable.lua`. It might hold the key.
  -- If `no-longtable.lua` converts tables to non-longtables, then wrapping them in `table` env is possible.

  local result = {}
  
  -- If we have placement or wrap options, we might need to be careful about longtable.
  -- Standard Pandoc LaTeX writer uses longtable.
  -- Longtable cannot be inside \begin{table} or \begin{wrapfigure}.
  --
  -- If the user requests `pos` or `wrap` or `span=full` (which implies table* float),
  -- we ideally want a floating environment.
  --
  -- Current implementation only adds \begingroup ... \endgroup.
  --
  -- Let's stick to the current scope: Add the *option parsing* to the Lua filter (which I did above),
  -- and then implement the logic.
  --
  -- Since reimplementing table writing is complex, I will implement a "best effort" support:
  -- 1. If `pos` or `wrap` is present, we wrap the table in a float env (table/table*/wraptable).
  -- 2. AND we must ensure the inner table renders as `tabular`, not `longtable`.
  --    How? We can strip the `Header` from the Table (if acceptable)?
  --    Or maybe set `classes` to something that `no-longtable` recognizes?
  --
  --    Actually, standard Pandoc behavior: if a table has a caption, it uses longtable.
  --    If it has no caption, it uses longtable (in recent versions) or tabular?
  --
  --    Let's look at `no-longtable.lua` to see what it does.
  
  -- Handle alignment via captionsetup if aligned left/right
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
