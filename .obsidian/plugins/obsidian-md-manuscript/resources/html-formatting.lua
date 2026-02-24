-- html-formatting.lua
-- Converts HTML formatting tags to Pandoc AST equivalents so that both
-- Markdown and HTML syntax produce identical output across all formats.
--
-- Supported conversions:
--   <sup>...</sup>        → Superscript   (Markdown: ^text^)
--   <sub>...</sub>        → Subscript     (Markdown: ~text~)
--   <mark>...</mark>      → Highlighted   (Markdown: ==text==)
--   <s>...</s>            → Strikeout     (Markdown: ~~text~~)
--   <del>...</del>        → Strikeout     (Markdown: ~~text~~)
--   <strong>...</strong>  → Strong        (Markdown: **text**)
--   <b>...</b>            → Strong        (Markdown: **text**)
--   <em>...</em>          → Emph          (Markdown: *text*)
--   <i>...</i>            → Emph          (Markdown: *text*)
--
-- Note: <u>...</u> is handled separately by underline.lua

local tag_handlers = {
  sup    = function(c) return pandoc.Superscript(c) end,
  sub    = function(c) return pandoc.Subscript(c) end,
  mark   = function(c) return pandoc.Span(c, {class = "mark"}) end,
  s      = function(c) return pandoc.Strikeout(c) end,
  del    = function(c) return pandoc.Strikeout(c) end,
  strong = function(c) return pandoc.Strong(c) end,
  b      = function(c) return pandoc.Strong(c) end,
  em     = function(c) return pandoc.Emph(c) end,
  i      = function(c) return pandoc.Emph(c) end,
}

local function process_inlines(inlines)
  local result = {}
  local i = 1

  while i <= #inlines do
    local el = inlines[i]

    if el.t == 'RawInline' and el.format == 'html' then
      -- Try to match an opening HTML tag (e.g., <sup>, <em>)
      local tag = el.text:match('^<(%a+)>$')
      if tag then
        local handler = tag_handlers[tag:lower()]
        if handler then
          -- Collect content until closing tag
          local content = {}
          local close_tag = '</' .. tag:lower() .. '>'
          i = i + 1

          while i <= #inlines do
            local current = inlines[i]
            if current.t == 'RawInline' and current.format == 'html'
                and current.text:lower() == close_tag then
              break
            end
            table.insert(content, current)
            i = i + 1
          end

          -- Recursively process nested HTML tags in content
          content = process_inlines(content)
          table.insert(result, handler(content))
        else
          table.insert(result, el)
        end
      else
        table.insert(result, el)
      end
    else
      -- Recurse into inline elements that have content (e.g., Strong, Emph)
      if el.content then
        el.content = process_inlines(el.content)
      end
      table.insert(result, el)
    end
    i = i + 1
  end

  return result
end

local function process_block(block)
  if block.content then
    block.content = process_inlines(block.content)
  end
  return block
end

return {
  {
    Para = process_block,
    Plain = process_block,
    Header = process_block,
  }
}
