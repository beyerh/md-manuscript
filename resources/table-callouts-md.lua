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

-- Track table numbers
local table_counter = 0
local table_labels = {}

-- Configuration
local config = {
  number_tables = true,  -- whether to add "Table N." prefix
  table_prefix = "Table",  -- prefix for tables (e.g., "Table" for normal, "Table" for SI)
  is_si = false  -- whether this is SI mode (adds S prefix to numbers)
}

-- Read configuration from document metadata
function Meta(meta)
  if meta["number-tables"] ~= nil then
    config.number_tables = meta["number-tables"]
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

-- Parse options from the header line (we only need the label)
local function parse_options(header_text)
  local opts = {
    label = nil
  }
  
  -- Extract label (#tbl:something)
  opts.label = header_text:match("#(tbl:[%w%-_]+)")
  
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
      
      -- Output the caption as a bold paragraph
      if pending_caption_inlines and #pending_caption_inlines > 0 then
        local caption_content = {}
        
        -- Add "Table N. " prefix if configured
        if config.number_tables then
          local number_str = config.is_si and ("S" .. table_counter) or tostring(table_counter)
          table.insert(caption_content, pandoc.Strong({
            pandoc.Str(config.table_prefix .. " " .. number_str .. ". ")
          }))
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
      -- Just output the table as-is (markdown writer will handle it)
      table.insert(out, blk)
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
