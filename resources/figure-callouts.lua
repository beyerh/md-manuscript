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

local function parse_width_value(header_text)
  local width = header_text:match("width=([%d%%%.\\%a]+)")
  if not width then
    return nil
  end

  -- Prefer Pandoc-native width values (percentages or absolute lengths).
  -- Pandoc understands percentages like "50%" and converts them appropriately
  -- for LaTeX/PDF (typically relative to \linewidth).
  if width:match("%%$") then
    return width
  end

  -- Map common LaTeX width macros to percentages.
  if width == "\\linewidth" or width == "linewidth" or width == "\\textwidth" or width == "textwidth" then
    return "100%"
  end

  -- Map numeric factors like 0.5\linewidth or 0.9\textwidth to percentages.
  local factor = width:match("^([%d%.]+)\\linewidth$") or width:match("^([%d%.]+)linewidth$")
  if not factor then
    factor = width:match("^([%d%.]+)\\textwidth$") or width:match("^([%d%.]+)textwidth$")
  end
  if factor then
    local f = tonumber(factor)
    if f then
      return string.format("%.0f%%", f * 100)
    end
  end

  -- If a bare number is provided, interpret <= 1 as a fraction of full width.
  local bare = tonumber(width)
  if bare then
    if bare <= 1 then
      return string.format("%.0f%%", bare * 100)
    end
    return tostring(bare)
  end

  -- Otherwise, keep as-is (e.g. "8cm", "120mm").
  return width
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
      if replace_first_image_in_blocks(b.content, new_image) then
        return true
      end
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
      if prepend_rawinline_to_first_para(b.content, raw_latex) then
        return true
      end
    end
  end
  return false
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
  
  -- First element should be a Para starting with [!figure]
  local first = content[1]
  if (first.t ~= "Para" and first.t ~= "Plain") or #first.content == 0 then
    return false
  end
  
  local text = stringify(first)
  return text:match("%[!figure%]")
end

-- Main filter function
function BlockQuote(block)
  if not is_figure_callout(block) then
    return nil
  end
  
  local content = block.content
  local label = nil
  local width_value = nil
  local align_value = nil
  local image = nil
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

      if text:match("%[!figure%]") then
        label = text:match("#([%w%-_:]+)")
        if width_value == nil then
          width_value = parse_width_value(text)
        end

        if align_value == nil then
          local a = text:match("align=(%w+)")
          if a == "left" or a == "center" or a == "right" then
            align_value = a
          end
        end
      end

      local image_pos = nil
      if not found_image then
        for idx, inline in ipairs(inlines) do
          if inline.t == "Image" then
            image = inline
            found_image = true
            image_pos = idx
            break
          end
        end
      end

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
  
  -- Remove trailing space from caption
  if #caption_inlines > 0 and caption_inlines[#caption_inlines].t == "Space" then
    table.remove(caption_inlines)
  end
  
  -- If no image found, return unchanged
  if not image then
    return nil
  end

  local fig_id = label or (image.attr and image.attr.identifier) or ""

  local is_latex = (FORMAT and (FORMAT:match("latex") or FORMAT:match("pdf"))) ~= nil

  -- Create image with caption as alt text
  -- Preserve existing classes/attributes, but ensure a sane default width in LaTeX/PDF.
  local img_classes = image.attr and image.attr.classes or {}
  local img_attrs = {}
  if image.attr and image.attr.attributes then
    for k, v in pairs(image.attr.attributes) do
      img_attrs[k] = v
    end
  end

  if is_latex then
    if width_value ~= nil then
      img_attrs["width"] = width_value
    elseif img_attrs["width"] == nil then
      img_attrs["width"] = "100%"
    end
  end

  local img_attr = pandoc.Attr("", img_classes, img_attrs)

  -- Create new image with caption inlines and label
  local new_image = pandoc.Image(caption_inlines, image.src, image.title, img_attr)
  

  -- Build a real Figure node using pandoc.read so the result is a proper
  -- Pandoc 2.x userdata object (important: LaTeX writer otherwise may drop captions).
  local placeholder_md = "![x](" .. image.src .. ")"
  if fig_id ~= "" then
    placeholder_md = placeholder_md .. "{#" .. fig_id .. "}"
  end

  -- Ensure width survives even if Figure internals differ across pandoc versions.
  if is_latex then
    local w = img_attrs["width"]
    if w ~= nil and w ~= "" then
      if fig_id ~= "" then
        placeholder_md = "![x](" .. image.src .. "){#" .. fig_id .. " width=" .. w .. "}"
      else
        placeholder_md = "![x](" .. image.src .. "){width=" .. w .. "}"
      end
    end
  end

  local doc = pandoc.read(placeholder_md, "markdown+implicit_figures")
  local fig = doc.blocks[1]

  if fig and fig.t == "Figure" then
    fig.caption.long = { pandoc.Plain(caption_inlines) }
    if fig_id ~= "" then
      fig.attr = pandoc.Attr(fig_id, {}, {})
    end

    -- Replace the placeholder image with our real image (attrs/title/alt)
    if fig.content then
      replace_first_image_in_blocks(fig.content, new_image)
    end

    if is_latex and align_value ~= nil and fig.content ~= nil then
      local align_cmd = nil
      local cap_just = nil
      if align_value == "left" then
        align_cmd = "\\raggedright"
        cap_just = "raggedright"
      elseif align_value == "right" then
        align_cmd = "\\raggedleft"
        cap_just = "raggedleft"
      else
        align_cmd = "\\centering"
        cap_just = "centering"
      end

      -- Keep the Figure content as a single block (avoid triggering pandoc's
      -- multi-block figure minipage layout) by injecting alignment as RawInline.
      local cap_setup = "\\ifcsname captionsetup\\endcsname\\captionsetup{justification=" .. cap_just .. ",singlelinecheck=false}\\fi"
      prepend_rawinline_to_first_para(fig.content, align_cmd .. cap_setup)
    end

    return fig
  end

  -- Fallback
  return pandoc.Para{new_image}
end

return {
  {BlockQuote = BlockQuote}
}
