-- strip-latex.lua
-- Removes or converts LaTeX-specific code for clean markdown output
-- suitable for web/digital garden publishing.
--
-- Handles:
-- - Raw LaTeX blocks (```{=latex} ... ```)
-- - Raw LaTeX inline (`\command`{=latex})
-- - Div elements with {=latex} or custom-style attributes
-- - Landscape environment wrappers
-- - Font color tags (converts to HTML spans)
-- - Various LaTeX commands embedded in markdown
--
-- This filter should run AFTER figure-callouts-md.lua and table-callouts-md.lua

local stringify = pandoc.utils.stringify

-- Configuration
local config = {
  keep_color_as_html = true,  -- Convert <font color> to <span style="color:">
  keep_highlighting = true     -- Keep ==highlighted== text
}

-- Read configuration from document metadata
function Meta(meta)
  if meta["keep-color-as-html"] ~= nil then
    config.keep_color_as_html = meta["keep-color-as-html"]
  end
  if meta["keep-highlighting"] ~= nil then
    config.keep_highlighting = meta["keep-highlighting"]
  end
  return nil
end

-- Remove raw LaTeX blocks entirely
function RawBlock(block)
  if block.format == "latex" or block.format == "tex" then
    -- Check if it's a landscape wrapper - we want to remove these
    local text = block.text
    if text:match("\\begin{landscape}") or text:match("\\end{landscape}") then
      return {}  -- Remove landscape wrappers
    end
    -- Remove all other LaTeX blocks
    return {}
  end
  return nil
end

-- Remove or convert raw LaTeX inlines
function RawInline(inline)
  if inline.format == "latex" or inline.format == "tex" then
    local text = inline.text
    
    -- Remove common LaTeX commands that don't translate to markdown
    -- \setlength, \parindent, \parskip, etc.
    if text:match("\\setlength") or 
       text:match("\\parindent") or 
       text:match("\\parskip") or
       text:match("\\newpage") or
       text:match("\\clearpage") or
       text:match("\\pagebreak") or
       text:match("\\linebreak") or
       text:match("\\noindent") or
       text:match("\\indent") or
       text:match("\\hspace") or
       text:match("\\vspace") or
       text:match("\\centering") or
       text:match("\\raggedright") or
       text:match("\\raggedleft") then
      return {}  -- Remove entirely
    end
    
    -- Remove landscape environment markers
    if text:match("\\begin{landscape}") or text:match("\\end{landscape}") then
      return {}
    end
    
    -- Remove figure/table environment markers
    if text:match("\\begin{figure") or text:match("\\end{figure") or
       text:match("\\begin{table") or text:match("\\end{table") then
      return {}
    end
    
    -- Remove other common LaTeX-only commands
    if text:match("\\label{") or
       text:match("\\ref{") or
       text:match("\\caption{") or
       text:match("\\includegraphics") then
      return {}
    end
    
    -- For any other LaTeX, remove it
    return {}
  end
  return nil
end

-- Handle Div elements
function Div(div)
  -- Check for {=latex} class - remove the div but keep content
  for _, class in ipairs(div.classes) do
    if class == "latex" then
      return {}  -- Remove LaTeX-only divs entirely
    end
  end
  
  -- Check for custom-style attribute - remove wrapper but keep content
  if div.attributes["custom-style"] then
    -- Return just the content, unwrapping the div
    return div.content
  end
  
  return nil
end

-- Handle CodeBlock elements with {=latex} class
function CodeBlock(block)
  for _, class in ipairs(block.classes) do
    if class == "latex" then
      return {}  -- Remove LaTeX code blocks
    end
  end
  return nil
end

-- Handle Span elements (for color conversion)
function Span(span)
  -- Check for color attribute (from color-text.lua processing)
  if span.attributes.color then
    if config.keep_color_as_html then
      local color = span.attributes.color
      local content = stringify(span.content)
      -- Return as HTML span with inline style
      return pandoc.RawInline("html", 
        string.format('<span style="color:#%s">%s</span>', color, content))
    else
      -- Just return the content without color
      return span.content
    end
  end
  return nil
end

-- Process inline elements to handle font color tags
-- This catches <font color="...">text</font> that wasn't processed by color-text.lua
function process_inlines(inlines)
  local result = {}
  local i = 1

  while i <= #inlines do
    local el = inlines[i]

    if el.t == 'RawInline' and el.format == 'html' then
      -- Check for opening font tag
      local color = el.text:match('<font%s+color%s*=%s*"([^"]+)">')
      if color then
        local content = {}
        i = i + 1

        -- Collect content until closing tag
        while i <= #inlines do
          local current = inlines[i]
          if current.t == 'RawInline' and current.format == 'html' and current.text:match('</font>') then
            break
          end
          table.insert(content, current)
          i = i + 1
        end

        if config.keep_color_as_html then
          -- Convert to HTML span
          local text = stringify(content)
          table.insert(result, pandoc.RawInline('html', 
            string.format('<span style="color:%s">%s</span>', color, text)))
        else
          -- Just keep the content without color
          for _, c in ipairs(content) do
            table.insert(result, c)
          end
        end
      else
        table.insert(result, el)
      end
    else
      table.insert(result, el)
    end
    i = i + 1
  end

  return result
end

-- Apply inline processing to Para and Plain blocks
function Para(para)
  local new_content = process_inlines(para.content)
  if #new_content ~= #para.content then
    return pandoc.Para(new_content)
  end
  return nil
end

function Plain(plain)
  local new_content = process_inlines(plain.content)
  if #new_content ~= #plain.content then
    return pandoc.Plain(new_content)
  end
  return nil
end

-- Remove empty paragraphs that might result from stripping LaTeX
function remove_empty_blocks(blocks)
  local result = {}
  for _, block in ipairs(blocks) do
    if block.t == "Para" or block.t == "Plain" then
      if #block.content > 0 then
        -- Check if all content is just whitespace
        local has_content = false
        for _, inline in ipairs(block.content) do
          if inline.t ~= "Space" and inline.t ~= "SoftBreak" then
            has_content = true
            break
          end
        end
        if has_content then
          table.insert(result, block)
        end
      end
    else
      table.insert(result, block)
    end
  end
  return result
end

function Pandoc(doc)
  -- Clean up empty blocks at the document level
  doc.blocks = remove_empty_blocks(doc.blocks)
  return doc
end

return {
  {Meta = Meta},
  {RawBlock = RawBlock, RawInline = RawInline, CodeBlock = CodeBlock},
  {Div = Div, Span = Span},
  {Para = Para, Plain = Plain},
  {Pandoc = Pandoc}
}
