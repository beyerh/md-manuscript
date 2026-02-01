-- table-callouts-md.lua
-- Converts Obsidian-style table callouts to standard markdown tables
-- for web/digital garden output.
--
-- Input syntax:
-- > [!table] #tbl:my-label width=80% fontsize=small spacing=1.1
-- >
-- > **Table Title.** Caption text with *formatting*.
--
-- | Col 1 | Col 2 | Col 3 |
-- |-------|-------|-------|
-- | A     | B     | C     |
--
-- Output:
-- **Table 1. Table Title.** Caption text with *formatting*.
--
-- | Col 1 | Col 2 | Col 3 |
-- |-------|-------|-------|
-- | A     | B     | C     |
--
-- This filter removes all LaTeX-specific options and outputs clean markdown.

local stringify = pandoc.utils.stringify

-- Parse width from header text (e.g. width=80% or width=0.8\linewidth)
local function parse_width_value(header_text)
  local width = header_text:match("width=([%d%%%.\\%a]+)")
  if not width then
    return nil
  end

  -- Return percentage if present
  if width:match("%%$") then
    return width
  end

  -- Handle \linewidth etc by defaulting to 100% for web/md
  if width:match("\\linewidth") or width:match("linewidth") or width:match("\\textwidth") or width:match("textwidth") then
    return "100%"
  end

  -- Handle bare numbers (fractions)
  local bare = tonumber(width)
  if bare then
    if bare <= 1 then
      return string.format("%.0f%%", bare * 100)
    end
    -- Keep pixels/units if > 1
    return tostring(bare) .. "px"
  end

  return width
end

-- Render table as HTML with styles
local function render_html_table(table_block, caption_inlines, label, width, align, columns, number_str, table_prefix)
  local styles = {}
  local classes = {}
  
  if width then
    table.insert(styles, "width: " .. width)
  end
  
  if align then
    if align == "center" then
      table.insert(styles, "display: block")
      table.insert(styles, "margin-left: auto")
      table.insert(styles, "margin-right: auto")
      table.insert(classes, "align-center")
    elseif align == "left" then
      table.insert(styles, "float: left")
      table.insert(styles, "margin-right: 1em")
      table.insert(classes, "align-left")
    elseif align == "right" then
      table.insert(styles, "float: right")
      table.insert(styles, "margin-left: 1em")
      table.insert(classes, "align-right")
    end
  end
  
  local style_attr = ""
  if #styles > 0 then
    style_attr = ' style="' .. table.concat(styles, "; ") .. '"'
  end
  
  local class_attr = ""
  if #classes > 0 then
    class_attr = ' class="' .. table.concat(classes, " ") .. '"'
  end
  
  local id_attr = ""
  if label then
    id_attr = ' id="' .. label .. '"'
  end
  
  local html_parts = {}
  table.insert(html_parts, '<figure' .. id_attr .. class_attr .. style_attr .. '>')
  
  -- Caption (top for tables usually)
  table.insert(html_parts, '  <figcaption>')
  table.insert(html_parts, '    <strong>' .. table_prefix .. ' ' .. number_str .. '.</strong> ')
  
  -- Caption text
  local caption_doc = pandoc.Pandoc({pandoc.Plain(caption_inlines)})
  local caption_html = pandoc.write(caption_doc, "html")
  caption_html = caption_html:gsub("^<p>", ""):gsub("</p>$", ""):gsub("^\n", ""):gsub("\n$", "")
  table.insert(html_parts, caption_html)
  
  table.insert(html_parts, '  </figcaption>')
  
  -- Apply column widths if specified
  if columns then
    local widths = {}
    for w in columns:gmatch("[^,]+") do
      table.insert(widths, tonumber(w))
    end
    
    -- Update table colspecs
    if table_block.t == "Table" then
      local colspecs = table_block.colspecs
      for i, spec in ipairs(colspecs) do
        if widths[i] then
          -- spec is {alignment, width}
          -- We create a new spec with updated width
          colspecs[i] = {spec[1], widths[i]}
        end
      end
      table_block.colspecs = colspecs
    end
  end

  -- Table content (rendered to HTML)
  local table_doc = pandoc.Pandoc({table_block})
  local table_html = pandoc.write(table_doc, "html")
  table.insert(html_parts, table_html)
  
  table.insert(html_parts, '</figure>')
  
  return pandoc.RawBlock("html", table.concat(html_parts, "\n"))
end

-- Remove existing "Table X." prefix from caption text to avoid duplication
local function clean_caption_text(text)
  -- Patterns to match: "Table 1.", "Tbl 1.", "Table S1.", etc.
  -- We match start of string, case insensitive "tab(le)|tbl", optional dot, space, digits/chars, dot/colon
  
  -- Remove "Table X." or "Table X:"
  local cleaned = text:gsub("^%s*[Tt]ab%a*%.?%s+[%w%d%-]+[.:]%s*", "")
  cleaned = cleaned:gsub("^%s*[Tt]bl%a*%.?%s+[%w%d%-]+[.:]%s*", "")
  
  -- Also remove just "Table." or "Tbl." if it appears alone
  cleaned = cleaned:gsub("^%s*[Tt]ab%a*%.?%s*", "")
  cleaned = cleaned:gsub("^%s*[Tt]bl%a*%.?%s*", "")
  
  return cleaned
end

-- Recursively strip prefix from inlines (modifies list in-place)
local function strip_prefix_from_inlines(inlines, after_keyword)
  if #inlines == 0 then return after_keyword end
  
  local first = inlines[1]
  
  if first.t == "Str" then
    local text = first.text
    
    if after_keyword then
       -- Match number part
       if text:match("^[%w%d%-]+[.:]?$") and (text:match("%d") or #text <= 4) then
          table.remove(inlines, 1)
          if not text:match("[.:]$") then
             return strip_prefix_from_inlines(inlines, true)
          else
             return strip_prefix_from_inlines(inlines, false)
          end
       elseif text:match("^[.:]$") then
          table.remove(inlines, 1)
          return strip_prefix_from_inlines(inlines, false)
       end
       return false
    end
    
    local cleaned = clean_caption_text(text)
    if cleaned ~= text then
      first.text = cleaned
      if cleaned == "" then
        table.remove(inlines, 1)
        
        local is_keyword = text:match("^%s*[Ff]ig%a*%.?%s*$") or text:match("^%s*[Tt]ab%a*%.?%s*$") or text:match("^%s*[Tt]bl%a*%.?%s*$")
        
        return strip_prefix_from_inlines(inlines, is_keyword)
      end
      return false
    end
    return false
    
  elseif first.t == "Strong" or first.t == "Emph" then
    local still_looking = strip_prefix_from_inlines(first.content, after_keyword)
    
    local is_empty = true
    for _, child in ipairs(first.content) do
      if child.t == "Str" and child.text ~= "" then is_empty = false break end
      if child.t ~= "Str" then is_empty = false break end
    end
    
    if is_empty or #first.content == 0 then
      table.remove(inlines, 1)
      return strip_prefix_from_inlines(inlines, still_looking)
    end
    return still_looking
    
  elseif first.t == "Space" then
     table.remove(inlines, 1)
     return strip_prefix_from_inlines(inlines, after_keyword)
  end
  
  return after_keyword
end

-- Track table numbers
local table_counter = 0
local table_labels = {}

-- Configuration
local config = {
  number_tables = true,  -- whether to add "Table N." prefix
  table_prefix = "Table",  -- prefix for tables (e.g., "Table" for normal, "Table" for SI)
  is_si = false,  -- whether this is SI mode (adds S prefix to numbers)
  caption_style = "plain" -- "plain" or "html"
}

-- Read configuration from document metadata
function Meta(meta)
  if meta["number-tables"] ~= nil then
    config.number_tables = meta["number-tables"]
  end
  if meta["caption-style"] then
    config.caption_style = stringify(meta["caption-style"])
  end
  -- Read tblPrefix from metadata
  if meta["tblPrefix"] then
    -- tblPrefix is typically a list like ["Table","Tables"]
    -- We want the singular form (first element)
    if type(meta["tblPrefix"]) == "table" and meta["tblPrefix"][1] then
      config.table_prefix = stringify(meta["tblPrefix"][1])
    else
      config.table_prefix = stringify(meta["tblPrefix"])
    end
  end
  
  -- Check for SI mode flag
  if meta["is_si"] and meta["is_si"] == true then
    config.is_si = true
  end
  
  return nil
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
  
  local first = content[1]
  if (first.t ~= "Para" and first.t ~= "Plain") or #first.content == 0 then
    return false
  end
  
  local text = stringify(first)
  return text:match("%[!table%]")
end

-- Check if blockquote contains a table (inline table callout)
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

-- Parse options from the header line
local function parse_options(header_text)
  local opts = {
    label = nil,
    width = nil,
    align = nil
  }
  
  -- Extract label (#tbl:something)
  opts.label = header_text:match("#(tbl:[%w%-_]+)")
  
  -- Parse width
  opts.width = parse_width_value(header_text)
  
  -- Parse align
  opts.align = header_text:match("align=(%w+)")
  
  -- Parse columns (comma-separated numbers)
  opts.columns = header_text:match("columns=([%d%.,]+)")
  
  return opts
end

-- Extract caption inlines from table header callout
local function extract_caption_inlines(block)
  local inlines = {}
  if block.t ~= "BlockQuote" then
    return nil
  end

  -- Skip the first block (header line with [!table])
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

-- Process blocks to handle table callouts
function Blocks(blocks)
  local out = {}
  local pending_opts = nil
  local pending_caption_inlines = nil

  for _, blk in ipairs(blocks) do
    if blk.t == "BlockQuote" and is_table_callout(blk) and not blockquote_contains_table(blk) then
      -- This is a table header callout (caption block before the table)
      local header_text = stringify(blk.content[1])
      pending_opts = parse_options(header_text)
      pending_caption_inlines = extract_caption_inlines(blk)
      
      -- Increment table counter and store label
      table_counter = table_counter + 1
      if pending_opts.label then
        table_labels[pending_opts.label] = table_counter
      end
      
      -- Output the caption as a bold paragraph (ONLY if not HTML style)
      if config.caption_style ~= "html" and pending_caption_inlines and #pending_caption_inlines > 0 then
        local caption_content = {}
        
        -- Clean the existing caption text to avoid duplication (recursively handling Strong etc.)
        strip_prefix_from_inlines(pending_caption_inlines)
        
        -- Remove leading space if present (to avoid double spacing)
        if #pending_caption_inlines > 0 and pending_caption_inlines[1].t == "Space" then
          table.remove(pending_caption_inlines, 1)
        end
        
        -- Add "Table N. " prefix if configured
        if config.number_tables then
          local number_str = config.is_si and ("S" .. table_counter) or tostring(table_counter)
          table.insert(caption_content, pandoc.Strong({
            pandoc.Str(config.table_prefix .. " " .. number_str .. ".")
          }))
          table.insert(caption_content, pandoc.Space())
        end
        
        -- Add the caption content
        for _, inline in ipairs(pending_caption_inlines) do
          table.insert(caption_content, inline)
        end
        
        table.insert(out, pandoc.Para(caption_content))
        table.insert(out, pandoc.Para({}))  -- Empty line for spacing
      end
      
    elseif pending_opts ~= nil and blk.t == "RawBlock" and (blk.format == "latex" or blk.format == "tex") then
      -- Skip LaTeX raw blocks between callout and table (e.g., \begin{landscape})
      -- Don't output them in markdown mode
      
    elseif blk.t == "Table" and pending_opts ~= nil then
      -- This is the actual table following a callout
      
      -- If HTML caption style is enabled
      if config.caption_style == "html" then
         -- We should have captured caption inlines in the previous block pass
         -- (stored in pending_caption_inlines)
         local caption_inlines = pending_caption_inlines or {}
         
         -- Clean caption
         strip_prefix_from_inlines(caption_inlines)
         if #caption_inlines > 0 and caption_inlines[1].t == "Space" then
            table.remove(caption_inlines, 1)
         end
         
         local number_str = config.is_si and ("S" .. table_counter) or tostring(table_counter)
         
         local html_block = render_html_table(
            blk,
            caption_inlines,
            pending_opts.label,
            pending_opts.width,
            pending_opts.align,
            pending_opts.columns,
            number_str,
            config.table_prefix
         )
         
         -- Remove the previously added caption para if we added it?
         -- In the previous loop iteration (BlockQuote), we inserted the caption para.
         -- If we are in HTML mode, we should NOT have inserted it there, or we remove it now.
         -- But we can't remove from 'out' easily if we don't know the index.
         -- SOLUTION: In the BlockQuote branch, check config.caption_style.
         -- If 'html', DO NOT insert the caption para.
         
         table.insert(out, html_block)
         
      else
        -- Just output the table as-is (markdown writer will handle it)
        table.insert(out, blk)
      end
      
      pending_opts = nil
      pending_caption_inlines = nil
      
    elseif blk.t == "Table" then
      -- Standalone table without callout - just pass through
      table.insert(out, blk)
      
    else
      table.insert(out, blk)
    end
  end

  return out
end

-- Handle cross-references that weren't resolved by pandoc-crossref
-- This converts **@Tbl:label** or @Tbl:label to plain text "Table N"
function Cite(cite)
  for _, citation in ipairs(cite.citations) do
    local id = citation.id
    -- Check for table references (case-insensitive)
    local tbl_label = id:match("^[Tt]bl:(.+)$")
    if tbl_label then
      local full_label = "tbl:" .. tbl_label
      local num = table_labels[full_label]
      if num then
        local number_str = config.is_si and ("S" .. num) or tostring(num)
        return pandoc.Str(config.table_prefix .. " " .. number_str)
      else
        -- Label not found, return as-is but without @ symbol
        return pandoc.Str(config.table_prefix .. " " .. tbl_label)
      end
    end
  end
  return nil  -- Let other filters handle non-table citations
end

-- Also handle Strong elements containing citations (for **@Tbl:label** syntax)
function Strong(strong)
  if #strong.content == 1 and strong.content[1].t == "Cite" then
    local cite = strong.content[1]
    for _, citation in ipairs(cite.citations) do
      local id = citation.id
      local tbl_label = id:match("^[Tt]bl:(.+)$")
      if tbl_label then
        local full_label = "tbl:" .. tbl_label
        local num = table_labels[full_label]
        if num then
          local number_str = config.is_si and ("S" .. num) or tostring(num)
          return pandoc.Str(config.table_prefix .. " " .. number_str)
        else
          return pandoc.Str(config.table_prefix .. " " .. tbl_label)
        end
      end
    end
  end
  return nil
end

return {
  {Meta = Meta},
  {Blocks = Blocks},
  {Cite = Cite, Strong = Strong}
}
