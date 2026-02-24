-- underline.lua
-- Converts <u>...</u> tags and native Underline elements to proper underlining

local function make_underline(inlines)
  if FORMAT:match('latex') or FORMAT:match('pdf') then
    -- Wrap inlines in \uline{...}, preserving all inner formatting
    -- by returning open/close RawInline delimiters around the original inlines
    local result = {}
    table.insert(result, pandoc.RawInline('latex', '\\uline{'))
    for _, el in ipairs(inlines) do
      table.insert(result, el)
    end
    table.insert(result, pandoc.RawInline('latex', '}'))
    return result
  elseif FORMAT:match('docx') then
    local span = pandoc.Span(inlines)
    span.attributes['custom-style'] = 'Underline'
    return span
  else
    -- For other formats (like HTML/Markdown), return the original content wrapped in <u>
    return pandoc.Span(inlines, {['style'] = 'text-decoration: underline;'})
  end
end

-- Insert underline result into target list (handles both single element and list)
local function insert_underline(target, underlined)
  if type(underlined) == 'table' and underlined.t == nil then
    -- It's a plain list of inlines (LaTeX path)
    for _, item in ipairs(underlined) do
      table.insert(target, item)
    end
  else
    table.insert(target, underlined)
  end
end

local function process_inlines(inlines)
  local result = {}
  local i = 1

  while i <= #inlines do
    local el = inlines[i]

    -- Handle HTML <u> tags
    if el.t == 'RawInline' and el.format == 'html' and el.text:match('<u>') then
      local content = {}
      i = i + 1

      while i <= #inlines do
        local current = inlines[i]
        if current.t == 'RawInline' and current.format == 'html' and current.text:match('</u>') then
          break
        end
        table.insert(content, current)
        i = i + 1
      end

      insert_underline(result, make_underline(content))
    -- Handle native Pandoc Underline elements
    elseif el.t == 'Underline' then
      insert_underline(result, make_underline(el.content))
    else
      -- Recurse into other inline elements (Strong, Emph, etc.)
      if el.content then
        el.content = process_inlines(el.content)
      end
      table.insert(result, el)
    end
    i = i + 1
  end

  return result
end

-- Function to handle block elements by processing their inline content
local function process_block(block)
  if block.content then
    block.content = process_inlines(block.content)
  end
  return block
end

return {
  {
    -- Process all block types that contain inlines
    Para = process_block,
    Plain = process_block,
    Header = process_block,
    -- Handle native Underline if it exists at top level
    Underline = function(el)
      local underlined = make_underline(el.content)
      if type(underlined) == 'table' and underlined.t == nil then
        return underlined
      end
      return underlined
    end
  }
}
