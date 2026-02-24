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
  is_si = false,  -- whether this is SI mode (adds S prefix to numbers)
  visualize_captions = false, -- whether to output visible captions in addition to alt text
  caption_style = "plain" -- "plain" or "html"
}

-- Read configuration from document metadata
function Meta(meta)
  if meta["figure-format"] then
    config.figure_format = stringify(meta["figure-format"])
  end
  if meta["number-figures"] ~= nil then
    config.number_figures = meta["number-figures"]
  end
  if meta["visualize-captions"] ~= nil then
    config.visualize_captions = meta["visualize-captions"]
  end
  if meta["caption-style"] then
    config.caption_style = stringify(meta["caption-style"])
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

  -- Read figure offset
  if meta["figure-offset"] then
    local offset = tonumber(stringify(meta["figure-offset"]))
    if offset then
      figure_counter = offset
    end
  end
  
  -- Read global labels map
  if meta["global-labels"] then
    local globals = meta["global-labels"]
    if type(globals) == "table" then
      for k, v in pairs(globals) do
        local key = tostring(k)
        if key:match("^fig:") then
          -- Value is a MetaMap with 'num' and 'file'
          if type(v) == "table" then
            local num = tonumber(stringify(v.num))
            local file = stringify(v.file)
            if num then
              figure_labels[key] = { num = num, file = file }
            end
          else
            -- Fallback for old simple number values
            local val = tonumber(stringify(v))
            if val then
              figure_labels[key] = { num = val }
            end
          end
        end
      end
    end
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

-- Render figure as HTML with styles
local function render_html_figure(image_src, caption_inlines, label, width, align, number_str, figure_prefix)
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
      -- Use block display with margin-right: auto to align left without text wrapping
      table.insert(styles, "display: block")
      table.insert(styles, "margin-right: auto")
      table.insert(classes, "align-left")
    elseif align == "right" then
      -- Use block display with margin-left: auto to align right without text wrapping
      table.insert(styles, "display: block")
      table.insert(styles, "margin-left: auto")
      table.insert(classes, "align-right")
    elseif align == "left-wrap" then
      -- Float left for wrapping
      table.insert(styles, "float: left")
      table.insert(styles, "margin-right: 1em")
      table.insert(classes, "float-left")
    elseif align == "right-wrap" then
      -- Float right for wrapping
      table.insert(styles, "float: right")
      table.insert(styles, "margin-left: 1em")
      table.insert(classes, "float-right")
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
  
  local blocks = {}
  
  -- Figure start
  table.insert(blocks, pandoc.RawBlock("html", '<figure' .. id_attr .. class_attr .. style_attr .. '>'))
  
  -- Image as Markdown (so Digital Garden detects the file)
  local img = pandoc.Image({pandoc.Str("Figure " .. number_str)}, image_src, "")
  -- Use Plain instead of Para to avoid extra paragraph spacing/newlines
  table.insert(blocks, pandoc.Plain({img}))
  
  -- Caption start with styling to distinguish from main text
  -- Note: using display: block and line-height for cleaner appearance
  table.insert(blocks, pandoc.RawBlock("html", '<figcaption style="font-size: 0.9em; color: #555; margin-top: 0.5em; line-height: 1.5; font-style: normal; display: block;">'))
  
  -- Bold prefix and caption text merged into one RawBlock to ensure they are on the same line
  local caption_doc = pandoc.Pandoc({pandoc.Plain(caption_inlines)})
  local caption_html = pandoc.write(caption_doc, "html")
  -- Strip ALL block-level tags and newlines
  caption_html = caption_html:gsub("<%/?p[^>]*>", ""):gsub("<%/?div[^>]*>", ""):gsub("\n", " "):gsub("^%s*", ""):gsub("%s*$", "")
  
  local full_caption_html = '<strong style="color: #333;">' .. figure_prefix .. ' ' .. number_str .. '.</strong> ' .. caption_html
  table.insert(blocks, pandoc.RawBlock("html", full_caption_html))
  
  -- End
  table.insert(blocks, pandoc.RawBlock("html", '</figcaption>'))
  table.insert(blocks, pandoc.RawBlock("html", '</figure>'))
  
  return blocks
end

-- Remove existing "Figure X." prefix from caption text to avoid duplication
local function clean_caption_text(text)
  -- Patterns to match: "Figure 1.", "Fig. 1.", "Figure S1.", "Fig S1", etc.
  -- We match start of string, case insensitive "fig(ure)", optional dot, space, digits/chars, dot/colon
  
  -- Remove "Figure X." or "Figure X:"
  local cleaned = text:gsub("^%s*[Ff]ig%a*%.?%s+[%w%d%-]+[.:]%s*", "")
  
  -- Also remove just "Figure." or "Fig." if it appears alone
  cleaned = cleaned:gsub("^%s*[Ff]ig%a*%.?%s*", "")
  
  return cleaned
end

-- Recursively strip prefix from inlines (modifies list in-place)
local function strip_prefix_from_inlines(inlines, after_keyword)
  if #inlines == 0 then return after_keyword end
  
  local first = inlines[1]
  
  if first.t == "Str" then
    local text = first.text
    
    if after_keyword then
       -- We already saw "Figure" or "Table". Now look for the number/label.
       -- Match "1", "1.", "1:", "S1", "S1.", "A", "IV", etc.
       -- Heuristic: must be alphanumeric/dash, short-ish or contain digits
       if text:match("^[%w%d%-]+[.:]?$") and (text:match("%d") or #text <= 4) then
          table.remove(inlines, 1)
          -- Found number. If it didn't end with dot/colon, look for it in next inline
          if not text:match("[.:]$") then
             return strip_prefix_from_inlines(inlines, true)
          else
             return strip_prefix_from_inlines(inlines, false)
          end
       elseif text:match("^[.:]$") then
          -- Just a dot or colon
          table.remove(inlines, 1)
          return strip_prefix_from_inlines(inlines, false)
       end
       return false -- Stop looking
    end
    
    local cleaned = clean_caption_text(text)
    -- Only update if it actually matched a prefix pattern (meaning text changed)
    if cleaned ~= text then
      first.text = cleaned
      -- If result is empty, remove the inline
      if cleaned == "" then
        table.remove(inlines, 1)
        
        -- Check if we removed a keyword like "Figure"
        local is_keyword = text:match("^%s*[Ff]ig%a*%.?%s*$") or text:match("^%s*[Tt]ab%a*%.?%s*$") or text:match("^%s*[Tt]bl%a*%.?%s*$")
        
        -- Recursively check next inline (for spaces or partial matches)
        return strip_prefix_from_inlines(inlines, is_keyword)
      end
      return false
    end
    return false
    
  elseif first.t == "Strong" or first.t == "Emph" then
    local still_looking = strip_prefix_from_inlines(first.content, after_keyword)
    
    -- If content is empty (or only empty strings), remove the element
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
     -- Remove leading spaces
     table.remove(inlines, 1)
     return strip_prefix_from_inlines(inlines, after_keyword)
  end
  
  return after_keyword
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
  local width_value = nil
  local align_value = nil
  local wrap_value = nil
  local pos_value = nil
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
        width_value = parse_width_value(text)
        align_value = text:match("align=(%w+)")
        wrap_value = text:match("wrap=(%w+)")
        pos_value = text:match("pos=(%w+)")
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
    figure_labels[label] = { num = figure_counter }
  end

  -- Convert image path
  local new_src = convert_image_path(image_src)
  
  -- Build alt text: "Figure N. Caption" or "Fig. SN. Caption" for SI
  local caption_text = inlines_to_plain_text(caption_inlines)
  
  -- Strip existing prefixes from caption text
  caption_text = clean_caption_text(caption_text)
  
  local number_str = config.is_si and ("S" .. figure_counter) or tostring(figure_counter)
  local prefix_str = string.format("%s %s. ", config.figure_prefix, number_str)
  
  local alt_text
  if config.number_figures then
    alt_text = prefix_str .. caption_text
  else
    alt_text = caption_text
  end
  
  -- Clean up alt text (remove multiple spaces, trim)
  alt_text = alt_text:gsub("%s+", " "):gsub("^%s+", ""):gsub("%s+$", "")
  
  -- Handle wrap by modifying alignment if not explicitly set
  if wrap_value then
    if wrap_value == "l" or wrap_value == "i" then
      align_value = "left-wrap"
    elseif wrap_value == "r" or wrap_value == "o" then
      align_value = "right-wrap"
    end
  end

  -- Check for HTML caption style OR wrapping (which requires HTML)
  if config.caption_style == "html" or (align_value and align_value:match("wrap")) then
    -- Strip existing prefix from caption inlines
    strip_prefix_from_inlines(caption_inlines)
    
    -- Remove leading space
    if #caption_inlines > 0 and caption_inlines[1].t == "Space" then
      table.remove(caption_inlines, 1)
    end
    
    return render_html_figure(
      new_src,
      caption_inlines,
      label,
      width_value,
      align_value,
      number_str,
      config.figure_prefix
    )
  end

  -- Create standard markdown image
  -- Using Para with Image to get: ![alt](src)
  local new_image = pandoc.Image({pandoc.Str(alt_text)}, new_src, "")
  local image_para = pandoc.Para({new_image})
  
  -- If visualize_captions is enabled, return both image and caption text
  if config.visualize_captions then
    local caption_para_content = {}
    
    -- Add "Figure N." prefix (bold)
    if config.number_figures then
      table.insert(caption_para_content, pandoc.Strong({pandoc.Str(config.figure_prefix .. " " .. number_str .. ".")}))
    end
    
    -- Strip existing prefix from caption inlines to avoid duplication
    strip_prefix_from_inlines(caption_inlines)
    
    -- Remove leading space if present (to avoid double spacing)
    if #caption_inlines > 0 and caption_inlines[1].t == "Space" then
      table.remove(caption_inlines, 1)
    end
    
    -- Add a space after the prefix
    table.insert(caption_para_content, pandoc.Space())

    -- Add the rest of the caption inlines
    for _, inline in ipairs(caption_inlines) do
      table.insert(caption_para_content, inline)
    end
    
    local caption_para = pandoc.Para(caption_para_content)
    
    -- Return list of blocks: Image then Caption
    return {image_para, caption_para}
  else
    return image_para
  end
end

-- Handle cross-references that weren't resolved by pandoc-crossref
-- This converts **@Fig:label** or @Fig:label to plain text "Figure N"
function Cite(cite)
  for _, citation in ipairs(cite.citations) do
    local id = citation.id
    
    -- Check for figure references (case-insensitive)
    local fig_id = id:match("^[Ff]ig:(.+)$")
    if fig_id then
      -- Split ID in case the space is part of the ID (happens with some parsers)
      local base_id, id_suffix = fig_id:match("^([^%s]+)%s+(.+)$")
      if not base_id then
        base_id = fig_id
        id_suffix = ""
      end

      -- Also handle suffix in citation metadata (standard Pandoc)
      local suffix = pandoc.utils.stringify(citation.suffix)
      
      -- Combine suffixes and remove leading space
      local combined_suffix = (id_suffix .. suffix):gsub("^%s+", "")
      
      local full_label = "fig:" .. base_id
      local label_info = figure_labels[full_label]
      
      if label_info and label_info.num then
        local number_str = config.is_si and ("S" .. label_info.num) or tostring(label_info.num)
        -- Link text includes the prefix, number, and suffix (no space between number and suffix)
        local link_text = config.figure_prefix .. " " .. number_str .. combined_suffix
        
        local url = ""
        if label_info.file and label_info.file ~= "" then
          url = label_info.file .. ".md#" .. full_label
        else
          url = "#" .. full_label
        end
        
        return pandoc.Link({pandoc.Str(link_text)}, url)
      else
        -- Fallback if label not found
        return pandoc.Str(config.figure_prefix .. " " .. fig_id .. suffix)
      end
    end
  end
  return nil
end

-- Process inlines to catch spaces and suffixes following a figure/table link
-- that were parsed as separate inlines (narrative citations)
local function process_inlines(inlines)
  local i = 1
  while i < #inlines do
    local current = inlines[i]
    if current.t == "Link" and #current.content > 0 then
      local link_text = pandoc.utils.stringify(current.content)
      -- Check if this is a figure/table link we generated
      if link_text:match("^" .. config.figure_prefix) or link_text:match("^Table") then
        local next_inline = inlines[i+1]
        local third_inline = inlines[i+2]
        
        -- Look for [Link] [Space] [Str("A")]
        if next_inline and next_inline.t == "Space" and third_inline and third_inline.t == "Str" then
           -- Check if third_inline looks like a sub-label (single letter or number)
           if #third_inline.text <= 2 then
             -- Merge the string into the link
             table.insert(current.content, pandoc.Str(third_inline.text))
             -- Remove the space and string from the inlines list
             table.remove(inlines, i+2)
             table.remove(inlines, i+1)
           end
        end
      end
    end
    i = i + 1
  end
  return inlines
end

-- Process all inlines in the document
function Para(para)
  para.content = process_inlines(para.content)
  return para
end

function Plain(plain)
  plain.content = process_inlines(plain.content)
  return plain
end

function Strong(strong)
  strong.content = process_inlines(strong.content)
  return strong
end

function Emph(emph)
  emph.content = process_inlines(emph.content)
  return emph
end

return {
  {Meta = Meta},
  {BlockQuote = BlockQuote},
  {Cite = Cite},
  {Para = Para, Plain = Plain, Strong = Strong, Emph = Emph}
}
