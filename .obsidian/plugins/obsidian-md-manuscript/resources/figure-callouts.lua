-- figure-callouts.lua
-- Converts Obsidian-style figure callouts to proper Pandoc figures with captions
--
-- Syntax in Markdown (visible/editable in Obsidian):
--
-- > [!figure] #fig:my-label
-- > ![](path/to/image.pdf)
-- >
-- > This is my **caption** with *formatting*.
--
-- Converts to a proper figure with caption for LaTeX/PDF output.

local stringify = pandoc.utils.stringify

local is_twocolumn = false
local fig_prefix = "Figure"
local tbl_prefix = "Table"

-- Storage to pass wrapfig parameters from BlockQuote (pass 2) to Blocks (pass 5)
local wrapfig_store = {}
local wrapfig_store_idx = 0

local function meta_list_contains(meta_value, needle)
  if meta_value == nil then return false end
  if type(meta_value) == "table" and meta_value.t == "MetaList" then
    for _, item in ipairs(meta_value) do
      if stringify(item) == needle then return true end
    end
    return false
  end
  return stringify(meta_value) == needle
end

function Meta(meta)
  is_twocolumn = meta_list_contains(meta["classoption"], "twocolumn")
  if meta["figPrefix"] then
    if type(meta["figPrefix"]) == "table" and meta["figPrefix"][1] then
      fig_prefix = stringify(meta["figPrefix"][1])
    else
      fig_prefix = stringify(meta["figPrefix"])
    end
  end
  if meta["tblPrefix"] then
    if type(meta["tblPrefix"]) == "table" and meta["tblPrefix"][1] then
      tbl_prefix = stringify(meta["tblPrefix"][1])
    else
      tbl_prefix = stringify(meta["tblPrefix"])
    end
  end
  return nil
end

local function parse_width_value(header_text)
  local width = header_text:match("width=([%d%%%.\\%a]+)")
  if not width then return nil end

  if width:match("%%$") then return width end
  if width == "\\linewidth" or width == "linewidth" or width == "\\textwidth" or width == "textwidth" then
    return "100%"
  end

  local factor = width:match("^([%d%.]+)\\linewidth$") or width:match("^([%d%.]+)linewidth$")
  if not factor then factor = width:match("^([%d%.]+)\\textwidth$") or width:match("^([%d%.]+)textwidth$") end
  if factor then
    local f = tonumber(factor)
    if f then return string.format("%.0f%%", f * 100) end
  end

  local bare = tonumber(width)
  if bare then
    if bare <= 1 then return string.format("%.0f%%", bare * 100) end
    return tostring(bare)
  end

  return width
end

local function render_inlines_as_latex(inlines)
  local doc = pandoc.Pandoc({ pandoc.Plain(inlines) })
  local result = pandoc.write(doc, "latex")
  result = result:gsub("^%s*", ""):gsub("%s*$", "")
  return result
end

local function width_to_latex_dimension(width_str)
  if not width_str or width_str == "" then return "\\textwidth" end

  if width_str:match("%%$") then
    local pct = tonumber(width_str:match("^([%d%.]+)%%$"))
    if pct then
      if pct >= 100 then return "\\textwidth" end
      return string.format("%.4f\\textwidth", pct / 100)
    end
  end

  if width_str == "\\linewidth" or width_str == "linewidth" or width_str == "\\textwidth" or width_str == "textwidth" then
    return "\\textwidth"
  end

  local factor = width_str:match("^([%d%.]+)\\linewidth$") or width_str:match("^([%d%.]+)linewidth$") or width_str:match("^([%d%.]+)\\textwidth$") or width_str:match("^([%d%.]+)textwidth$")
  if factor then
    local f = tonumber(factor)
    if f then
      if f >= 1 then return "\\textwidth" end
      return string.format("%.4f\\textwidth", f)
    end
  end

  local bare = tonumber(width_str)
  if bare then
    if bare <= 1 then return string.format("%.4f\\textwidth", bare) end
    return tostring(bare)
  end

  return width_str
end

local function replace_first_image_in_blocks(blocks, new_image)
  for bi, b in ipairs(blocks) do
    if b.t == "Para" or b.t == "Plain" then
      for ii, inl in ipairs(b.content) do
        if inl.t == "Image" then
          b.content[ii] = new_image
          blocks[bi] = b
          return true
        end
      end
    elseif b.t == "Div" and b.content then
      if replace_first_image_in_blocks(b.content, new_image) then return true end
    end
  end
  return false
end

local function prepend_rawinline_to_first_para(blocks, raw_latex)
  for bi, b in ipairs(blocks) do
    if b.t == "Para" or b.t == "Plain" then
      table.insert(b.content, 1, pandoc.RawInline("latex", raw_latex))
      blocks[bi] = b
      return true
    elseif b.t == "Div" and b.content then
      if prepend_rawinline_to_first_para(b.content, raw_latex) then return true end
    end
  end
  return false
end

local function process_citation_spacing(inlines)
  local i = 1
  while i < #inlines do
    local current = inlines[i]
    if current.t == "Cite" and #current.citations == 1 then
      local id = current.citations[1].id
      if id:match("^[Tt]bl:") or id:match("^[Ff]ig:") then
        local citation = current.citations[1]
        if #citation.suffix > 0 and citation.suffix[1].t == "Space" then
          table.remove(citation.suffix, 1)
        end
        local next_inline = inlines[i+1]
        local third_inline = inlines[i+2]
        if next_inline and next_inline.t == "Space" and third_inline and third_inline.t == "Str" then
          -- Match 1-2 letter sub-figure labels (e.g. "a", "B", "c).") but not words like "to"
          if third_inline.text:match("^[A-Za-z][A-Z]?$") or third_inline.text:match("^[A-Za-z][A-Z]?[^A-Za-z0-9]") then
            table.remove(inlines, i+1)
          end
        end
      end
    end
    i = i + 1
  end
  return inlines
end

-- Resolve @Fig:/@Tbl: citations to raw LaTeX references inside captions that
-- are rendered as raw LaTeX (pandoc-crossref cannot reach them there).
local function resolve_caption_cites(inlines)
  for i, inline in ipairs(inlines) do
    if inline.t == "Cite" and #inline.citations == 1 then
      local citation = inline.citations[1]
      local id = citation.id
      local prefix = nil
      local norm_id = nil
      if id:match("^[Ff]ig:") then
        prefix = fig_prefix
        norm_id = id:gsub("^[Ff]ig:", "fig:")
      elseif id:match("^[Tt]bl:") then
        prefix = tbl_prefix
        norm_id = id:gsub("^[Tt]bl:", "tbl:")
      end
      if prefix then
        if #citation.suffix > 0 and citation.suffix[1].t == "Space" then
          table.remove(citation.suffix, 1)
        end
        local suffix = ""
        if #citation.suffix > 0 then
          suffix = render_inlines_as_latex(citation.suffix)
        end
        inlines[i] = pandoc.RawInline("latex", prefix .. "~\\ref{" .. norm_id .. "}" .. suffix)
      end
    end
  end
  return inlines
end

local function is_figure_callout(block)
  if block.t ~= "BlockQuote" or #block.content == 0 then return false end
  local first = block.content[1]
  if (first.t ~= "Para" and first.t ~= "Plain") or #first.content == 0 then return false end
  return stringify(first):match("%[!figure%]")
end

function BlockQuote(block)
  if not is_figure_callout(block) then return nil end
  
  local label, width_value, align_value, span_value, pos_value, wrap_value, wrap_lines, wrap_nblocks, image
  local caption_inlines = {}
  local found_image = false

  for _, blk in ipairs(block.content) do
    if blk.t == "Para" or blk.t == "Plain" then
      local text = stringify(blk)
      if text:match("%[!figure%]") then
        label = text:match("#([%w%-_:]+)")
        width_value = parse_width_value(text)
        align_value = text:match("align=(%w+)")
        span_value = text:match("span=full") and "full" or nil
        pos_value = text:match("pos=([%a!]+)") or text:match("placement=([%a!]+)")
        wrap_value = text:match("wrap=([a-zA-Z]+)")
        local lines_str = text:match("lines=(%d+)")
        if lines_str then wrap_lines = tonumber(lines_str) end
        local wbstr = text:match("wrapblocks=(%d+)")
        if wbstr then wrap_nblocks = tonumber(wbstr) end
      end

      local image_pos = nil
      if not found_image then
        for idx, inline in ipairs(blk.content) do
          if inline.t == "Image" then
            image = inline
            found_image = true
            image_pos = idx
            break
          end
        end
      end

      if found_image then
        local start = (image_pos or 0) + 1
        for j = start, #blk.content do
          local el = blk.content[j]
          if #caption_inlines == 0 and (el.t == "Space" or el.t == "SoftBreak" or el.t == "LineBreak") then
            -- skip leading whitespace between image and caption
          else
            table.insert(caption_inlines, el)
          end
        end
      end
    end
  end
  
  if #caption_inlines > 0 and caption_inlines[#caption_inlines].t == "Space" then table.remove(caption_inlines) end
  if not image then return nil end

  local fig_id = label or (image.attr and image.attr.identifier) or ""
  local is_latex = (FORMAT and (FORMAT:match("latex") or FORMAT:match("pdf"))) ~= nil

  caption_inlines = process_citation_spacing(caption_inlines)
  if is_latex then
    caption_inlines = resolve_caption_cites(caption_inlines)
  end

  local img_attrs = {}
  if image.attr and image.attr.attributes then
    for k, v in pairs(image.attr.attributes) do img_attrs[k] = v end
  end
  if is_latex then img_attrs["width"] = width_value or img_attrs["width"] or "100%" end

  local new_image = pandoc.Image(caption_inlines, image.src, image.title, pandoc.Attr("", image.attr.classes, img_attrs))
  
  if is_latex then
    -- Handle wrapfigure
    if wrap_value then
      local pos_char = wrap_value:sub(1,1):lower()
      local wdim = width_to_latex_dimension(img_attrs["width"])
      if wdim == "\\textwidth" then wdim = "0.5\\textwidth" end
      
      local wrap_begin
      if wrap_lines then
        wrap_begin = "\\begin{wrapfigure}[" .. tostring(wrap_lines) .. "]{" .. pos_char .. "}{" .. wdim .. "}"
      else
        wrap_begin = "\\begin{wrapfigure}{" .. pos_char .. "}{" .. wdim .. "}"
      end
      local latex = {
        "\\leavevmode",
        wrap_begin,
        "\\centering",
        "\\includegraphics[width=\\linewidth]{" .. image.src .. "}"
      }
      if #caption_inlines > 0 then table.insert(latex, "\\caption{" .. render_inlines_as_latex(caption_inlines) .. "}") end
      if fig_id ~= "" then table.insert(latex, "\\label{" .. fig_id .. "}") end
      table.insert(latex, "\\end{wrapfigure}")
      -- Store data for Blocks pass which replaces wrapfig with minipage
      table.insert(wrapfig_store, {
        pos = pos_char,
        width = wdim,
        src = image.src,
        caption_latex = #caption_inlines > 0 and render_inlines_as_latex(caption_inlines) or nil,
        label = fig_id ~= "" and fig_id or nil,
        wrapblocks = wrap_nblocks
      })
      return pandoc.RawBlock("latex", table.concat(latex, "\n"))
    end

    -- Handle standard floats with pos or span
    if span_value == "full" or pos_value then
      local env = span_value == "full" and "figure*" or "figure"
      local placement = pos_value and ("[" .. pos_value .. "]") or (span_value == "full" and "[t]" or "")
      local cap_just = align_value == "left" and "raggedright" or (align_value == "right" and "raggedleft" or "centering")
      local align_cmd = align_value == "left" and "\\raggedright" or (align_value == "right" and "\\raggedleft" or "\\centering")
      
      local latex = {
        "\\begin{" .. env .. "}" .. placement,
        align_cmd,
        "\\ifcsname captionsetup\\endcsname\\captionsetup{justification=" .. cap_just .. ",singlelinecheck=off}\\fi",
        "\\includegraphics[width=" .. width_to_latex_dimension(img_attrs["width"]) .. "]{" .. image.src .. "}"
      }
      if #caption_inlines > 0 then table.insert(latex, "\\caption{" .. render_inlines_as_latex(caption_inlines) .. "}") end
      if fig_id ~= "" then table.insert(latex, "\\label{" .. fig_id .. "}") end
      table.insert(latex, "\\end{" .. env .. "}")
      return pandoc.RawBlock("latex", table.concat(latex, "\n"))
    end

    -- Standard figure alignment injection
    local placeholder_md = "![x](" .. image.src .. ")" .. (fig_id ~= "" and ("{#" .. fig_id .. "}") or "")
    local doc = pandoc.read(placeholder_md, "markdown+implicit_figures")
    local fig = doc.blocks[1]
    if fig and fig.t == "Figure" then
      fig.caption.long = { pandoc.Plain(caption_inlines) }
      if fig_id ~= "" then fig.attr = pandoc.Attr(fig_id, {}, span_value == "full" and {["md-span"]="full"} or {}) end
      replace_first_image_in_blocks(fig.content, new_image)
      
      local cap_just = align_value == "left" and "raggedright" or (align_value == "right" and "raggedleft" or "centering")
      local align_cmd = align_value == "left" and "\\raggedright" or (align_value == "right" and "\\raggedleft" or "\\centering")
      prepend_rawinline_to_first_para(fig.content, align_cmd .. "\\ifcsname captionsetup\\endcsname\\captionsetup{justification=" .. cap_just .. ",singlelinecheck=off}\\fi")
      return fig
    end
  end

  return pandoc.Para{new_image}
end

function Para(para) para.content = process_citation_spacing(para.content) return para end
function Plain(plain) plain.content = process_citation_spacing(plain.content) return plain end
function Strong(strong) strong.content = process_citation_spacing(strong.content) return strong end
function Emph(emph) emph.content = process_citation_spacing(emph.content) return emph end

local function Header_wfclear(header)
  local is_latex = (FORMAT and (FORMAT:match("latex") or FORMAT:match("pdf"))) ~= nil
  if not is_latex then return nil end

  return {
    pandoc.RawBlock("latex", "\\ifcsname WFclear\\endcsname\\WFclear\\fi"),
    header
  }
end

-- Replace wrapfig + following paragraph with side-by-side minipage layout.
-- This guarantees full-width content after the figure, since minipage does not
-- have wrapfig's line-counting zone that leaks into vspace/enumerate.
local function make_minipage_latex(fw, content_blocks)
  local content_latex = pandoc.write(pandoc.Pandoc(content_blocks), "latex")
  content_latex = content_latex:gsub("%s+$", "")

  local figw
  if fw.width == "\\textwidth" or fw.width == "\\linewidth" then
    figw = 1.0
  else
    local num = fw.width:match("^([%d%.]+)")
    figw = num and tonumber(num) or 0.4
  end
  local gap = 0.025
  local txtw = math.max(0.1, 1.0 - figw - gap)
  local txtw_str = string.format("%.4f\\textwidth", txtw)

  local L = {}
  table.insert(L, "\\noindent%")
  if fw.pos == "l" then
    table.insert(L, "\\begin{minipage}[t]{" .. fw.width .. "}")
    table.insert(L, "\\centering\\vspace{0pt}")
    table.insert(L, "\\includegraphics[width=\\linewidth]{" .. fw.src .. "}")
    if fw.caption_latex then table.insert(L, "\\captionof{figure}{" .. fw.caption_latex .. "}") end
    if fw.label then table.insert(L, "\\label{" .. fw.label .. "}") end
    table.insert(L, "\\end{minipage}%")
    table.insert(L, "\\hspace{" .. string.format("%.4f", gap) .. "\\textwidth}%")
    table.insert(L, "\\begin{minipage}[t]{" .. txtw_str .. "}")
    table.insert(L, "\\vspace{0pt}")
    table.insert(L, content_latex)
    table.insert(L, "\\end{minipage}")
  else
    table.insert(L, "\\begin{minipage}[t]{" .. txtw_str .. "}")
    table.insert(L, "\\vspace{0pt}")
    table.insert(L, content_latex)
    table.insert(L, "\\end{minipage}%")
    table.insert(L, "\\hspace{" .. string.format("%.4f", gap) .. "\\textwidth}%")
    table.insert(L, "\\begin{minipage}[t]{" .. fw.width .. "}")
    table.insert(L, "\\centering\\vspace{0pt}")
    table.insert(L, "\\includegraphics[width=\\linewidth]{" .. fw.src .. "}")
    if fw.caption_latex then table.insert(L, "\\captionof{figure}{" .. fw.caption_latex .. "}") end
    if fw.label then table.insert(L, "\\label{" .. fw.label .. "}") end
    table.insert(L, "\\end{minipage}")
  end
  return pandoc.RawBlock("latex", table.concat(L, "\n"))
end

-- Replace wrapfig + following block(s) with side-by-side minipage layout.
-- Use wrapblocks=N in the figure callout to include N consecutive blocks in
-- the right minipage (default: 1 paragraph/plain block).
local function Blocks_minipage_wrap(blocks)
  local is_latex = (FORMAT and (FORMAT:match("latex") or FORMAT:match("pdf"))) ~= nil
  if not is_latex or #wrapfig_store == 0 then return nil end

  local out = {}
  local pending_data = nil
  local pending_block = nil
  local collecting = {}   -- blocks accumulating for the right minipage

  for _, blk in ipairs(blocks) do
    if blk.t == "RawBlock" and blk.format == "latex"
        and blk.text:match("\\begin{wrapfigure}") then
      wrapfig_store_idx = wrapfig_store_idx + 1
      pending_data = wrapfig_store[wrapfig_store_idx]
      pending_block = blk
      collecting = {}

    elseif pending_data ~= nil then
      local nblocks = pending_data.wrapblocks
      if nblocks then
        -- wrapblocks=N: collect exactly N blocks of any type
        table.insert(collecting, blk)
        if #collecting >= nblocks then
          table.insert(out, make_minipage_latex(pending_data, collecting))
          pending_data = nil; pending_block = nil; collecting = {}
        end
      else
        -- Default: accept only a single Para/Plain
        if blk.t == "Para" or blk.t == "Plain" then
          table.insert(out, make_minipage_latex(pending_data, {blk}))
        else
          table.insert(out, pending_block)  -- fallback: emit original wrapfig
          table.insert(out, blk)
        end
        pending_data = nil; pending_block = nil; collecting = {}
      end

    else
      table.insert(out, blk)
    end
  end

  -- Flush any un-consumed pending wrapfig
  if pending_block ~= nil then
    table.insert(out, pending_block)
    for _, b in ipairs(collecting) do table.insert(out, b) end
  end

  return out
end

return {
  {Meta = Meta},
  {BlockQuote = BlockQuote},
  {Header = Header_wfclear},
  {Para = Para, Plain = Plain, Strong = Strong, Emph = Emph},
  {Blocks = Blocks_minipage_wrap}
}
