-- figure-callouts-md.lua
-- Converts Obsidian-style figure callouts to standard markdown images
-- for web/digital garden output.
--
-- Input syntax:
-- > [!figure] #fig:my-label width=80% align=center
-- > ![](figures/image.pdf)
-- >
-- > **Figure Title.** Caption text with *formatting*.
--
-- Output:
-- ![Figure 1. Figure Title. Caption text with formatting.](figures/image.png)
--
-- This filter is designed for markdown-to-markdown conversion where
-- pandoc-crossref has already resolved the figure numbers.

local stringify = pandoc.utils.stringify

-- Track figure numbers for manual numbering when pandoc-crossref isn't used
local figure_counter = 0
local figure_labels = {}

-- Configuration: can be set via metadata
local config = {
  figure_format = "png",  -- png, webp, jpg, or original
  number_figures = true,  -- whether to add "Figure N." prefix
  figure_prefix = "Figure",  -- prefix for figures (e.g., "Figure" or "Fig.")
  is_si = false  -- whether this is SI mode (adds S prefix to numbers)
}

-- Read configuration from document metadata
function Meta(meta)
  if meta["figure-format"] then
    config.figure_format = stringify(meta["figure-format"])
  end
  if meta["number-figures"] ~= nil then
    config.number_figures = meta["number-figures"]
  end
  -- Read figPrefix from metadata
  if meta["figPrefix"] then
    -- figPrefix is typically a list like ["Figure","Figures"]
    -- We want the singular form (first element)
    if type(meta["figPrefix"]) == "table" and meta["figPrefix"][1] then
      config.figure_prefix = stringify(meta["figPrefix"][1])
    else
      -- Single value
      config.figure_prefix = stringify(meta["figPrefix"])
    end
  end
  
  -- Check for SI mode flag
  if meta["is_si"] and meta["is_si"] == true then
    config.is_si = true
  end
  
  return nil
end

-- Check if a block is a figure callout
local function is_figure_callout(block)
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
  return text:match("%[!figure%]")
end

-- Convert image path extension based on config
local function convert_image_path(src)
  if config.figure_format == "original" then
    return src
  end
  
  -- Replace any image extension (.pdf, .png, .jpg, .jpeg, .webp) with the configured format
  local new_src = src:gsub("%.[pP][dD][fF]$", "." .. config.figure_format)
  new_src = new_src:gsub("%.[pP][nN][gG]$", "." .. config.figure_format)
  new_src = new_src:gsub("%.[jJ][pP][eE]?[gG]$", "." .. config.figure_format)
  new_src = new_src:gsub("%.[wW][eE][bB][pP]$", "." .. config.figure_format)
  return new_src
end

-- Extract plain text from inlines, preserving basic formatting
local function inlines_to_plain_text(inlines)
  local result = {}
  
  for _, inline in ipairs(inlines) do
    if inline.t == "Str" then
      table.insert(result, inline.text)
    elseif inline.t == "Space" then
      table.insert(result, " ")
    elseif inline.t == "SoftBreak" then
      table.insert(result, " ")
    elseif inline.t == "LineBreak" then
      table.insert(result, " ")
    elseif inline.t == "Strong" then
      table.insert(result, stringify(inline.content))
    elseif inline.t == "Emph" then
      table.insert(result, stringify(inline.content))
    elseif inline.t == "Strikeout" then
      table.insert(result, stringify(inline.content))
    elseif inline.t == "Subscript" then
      table.insert(result, stringify(inline.content))
    elseif inline.t == "Superscript" then
      table.insert(result, stringify(inline.content))
    elseif inline.t == "Quoted" then
      table.insert(result, stringify(inline.content))
    elseif inline.t == "Code" then
      table.insert(result, inline.text)
    elseif inline.t == "Math" then
      table.insert(result, "$" .. inline.text .. "$")
    elseif inline.t == "RawInline" then
      -- Skip raw LaTeX/HTML in alt text
    elseif inline.t == "Link" then
      table.insert(result, stringify(inline.content))
    elseif inline.t == "Image" then
      -- Skip nested images
    elseif inline.t == "Note" then
      -- Skip footnotes in alt text
    elseif inline.t == "Span" then
      table.insert(result, stringify(inline.content))
    elseif inline.t == "Cite" then
      -- For citations, just use the text representation
      table.insert(result, stringify(inline.content))
    end
  end
  
  return table.concat(result)
end

-- Main filter function for figure callouts
function BlockQuote(block)
  if not is_figure_callout(block) then
    return nil
  end
  
  local content = block.content
  local label = nil
  local image = nil
  local image_src = nil
  local caption_inlines = {}
  local found_image = false

  local function block_inlines(blk)
    if blk.t == "Para" or blk.t == "Plain" then
      return blk.content
    end
    return nil
  end

  -- Parse all blocks in the callout
  for i, blk in ipairs(content) do
    local inlines = block_inlines(blk)
    if inlines then
      local text = stringify(blk)

      -- Extract label from header line
      if text:match("%[!figure%]") then
        label = text:match("#(fig:[%w%-_]+)")
      end

      -- Find the image
      local image_pos = nil
      if not found_image then
        for idx, inline in ipairs(inlines) do
          if inline.t == "Image" then
            image = inline
            image_src = inline.src
            found_image = true
            image_pos = idx
            break
          end
        end
      end

      -- Collect caption (everything after the image)
      if found_image then
        local start_idx = 1
        if image_pos ~= nil then
          start_idx = image_pos + 1
        end

        if start_idx <= #inlines then
          if #caption_inlines > 0 then
            table.insert(caption_inlines, pandoc.Space())
          end
          for j = start_idx, #inlines do
            table.insert(caption_inlines, inlines[j])
          end
        end
      end
    end
  end
  
  -- Remove leading/trailing spaces from caption
  while #caption_inlines > 0 and caption_inlines[1].t == "Space" do
    table.remove(caption_inlines, 1)
  end
  while #caption_inlines > 0 and caption_inlines[#caption_inlines].t == "Space" do
    table.remove(caption_inlines)
  end
  
  -- If no image found, return unchanged
  if not image then
    return nil
  end

  -- Increment figure counter and store label mapping
  figure_counter = figure_counter + 1
  if label then
    figure_labels[label] = figure_counter
  end

  -- Convert image path
  local new_src = convert_image_path(image_src)
  
  -- Build alt text: "Figure N. Caption" or "Fig. SN. Caption" for SI
  local caption_text = inlines_to_plain_text(caption_inlines)
  local alt_text
  if config.number_figures then
    local number_str = config.is_si and ("S" .. figure_counter) or tostring(figure_counter)
    alt_text = string.format("%s %s. %s", config.figure_prefix, number_str, caption_text)
  else
    alt_text = caption_text
  end
  
  -- Clean up alt text (remove multiple spaces, trim)
  alt_text = alt_text:gsub("%s+", " "):gsub("^%s+", ""):gsub("%s+$", "")
  
  -- Create standard markdown image
  -- Using Para with Image to get: ![alt](src)
  local new_image = pandoc.Image({pandoc.Str(alt_text)}, new_src, "")
  
  return pandoc.Para({new_image})
end

-- Handle cross-references that weren't resolved by pandoc-crossref
-- This converts **@Fig:label** or @Fig:label to plain text "Figure N"
function Cite(cite)
  for _, citation in ipairs(cite.citations) do
    local id = citation.id
    -- Check for figure references (case-insensitive)
    local fig_label = id:match("^[Ff]ig:(.+)$")
    if fig_label then
      local full_label = "fig:" .. fig_label
      local num = figure_labels[full_label]
      if num then
        local number_str = config.is_si and ("S" .. num) or tostring(num)
        return pandoc.Str(config.figure_prefix .. " " .. number_str)
      else
        -- Label not found, return as-is but without @ symbol
        return pandoc.Str(config.figure_prefix .. " " .. fig_label)
      end
    end
  end
  return nil  -- Let other filters handle non-figure citations
end

-- Also handle Strong elements containing citations (for **@Fig:label** syntax)
function Strong(strong)
  if #strong.content == 1 and strong.content[1].t == "Cite" then
    local cite = strong.content[1]
    for _, citation in ipairs(cite.citations) do
      local id = citation.id
      local fig_label = id:match("^[Ff]ig:(.+)$")
      if fig_label then
        local full_label = "fig:" .. fig_label
        local num = figure_labels[full_label]
        if num then
          local number_str = config.is_si and ("S" .. num) or tostring(num)
          return pandoc.Str(config.figure_prefix .. " " .. number_str)
        else
          return pandoc.Str(config.figure_prefix .. " " .. fig_label)
        end
      end
    end
  end
  return nil
end

return {
  {Meta = Meta},
  {BlockQuote = BlockQuote},
  {Cite = Cite, Strong = Strong}
}
