local color_map = {
  red = "#FF0000",
  blue = "#0000FF",
  green = "#008000",
  yellow = "#FFFF00",
  orange = "#FFA500",
  purple = "#800080",
  pink = "#FFC0CB",
  black = "#000000",
  white = "#FFFFFF",
  gray = "#808080",
  grey = "#808080",
  brown = "#A52A2A",
  cyan = "#00FFFF",
  magenta = "#FF00FF"
}

local function normalize_color(color)
  if not color then return "#FF0000" end
  color = color:lower():gsub("%s+", "")
  return color_map[color] or color
end

local function hex_to_rgb(hex)
  hex = hex:gsub("#", "")
  if #hex == 6 then
    return tonumber(hex:sub(1,2), 16), tonumber(hex:sub(3,4), 16), tonumber(hex:sub(5,6), 16)
  elseif #hex == 3 then
    return tonumber(hex:sub(1,1), 16) * 17,
           tonumber(hex:sub(2,2), 16) * 17,
           tonumber(hex:sub(3,3), 16) * 17
  end
  return 255, 0, 0
end

local function make_colored_span(inlines, color)
  local norm = normalize_color(color)
  local r, g, b = hex_to_rgb(norm)

  if FORMAT:match('latex') or FORMAT:match('pdf') then
    local text = pandoc.utils.stringify(inlines)
    return pandoc.RawInline('latex', string.format('\\textcolor[RGB]{%d,%d,%d}{%s}', r, g, b, text))
  elseif FORMAT:match('docx') then
    local span = pandoc.Span(inlines)
    span.attributes['custom-style'] = nil
    span.attributes['color'] = string.format("%02X%02X%02X", r, g, b)
    return span
  else
    return nil
  end
end

local function process_inlines(inlines)
  local result = {}
  local i = 1

  while i <= #inlines do
    local el = inlines[i]

    if el.t == 'RawInline' and el.format == 'html' then
      local color = el.text:match('<font%s+color%s*=%s*"([^"]+)">')
      if color then
        local content = {}
        i = i + 1

        while i <= #inlines do
          local current = inlines[i]
          if current.t == 'RawInline' and current.format == 'html' and current.text:match('</font>') then
            break
          end
          table.insert(content, current)
          i = i + 1
        end

        if FORMAT:match('latex') or FORMAT:match('pdf') or FORMAT:match('docx') then
          local colored = make_colored_span(content, color)
          if colored then
            table.insert(result, colored)
          else
            for _, c in ipairs(content) do
              table.insert(result, c)
            end
          end
        else
          table.insert(result, el)
          for _, c in ipairs(content) do
            table.insert(result, c)
          end
          table.insert(result, pandoc.RawInline('html', '</font>'))
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

return {
  {
    Para = function(para)
      para.content = process_inlines(para.content)
      return para
    end,
    Plain = function(plain)
      plain.content = process_inlines(plain.content)
      return plain
    end
  }
}
