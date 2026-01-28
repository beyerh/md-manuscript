-- no-longtable.lua
-- Converts tables to raw LaTeX tabular to avoid longtable in multicol mode
-- Runs AFTER pandoc-crossref so references are already resolved

local function escape_latex(s)
  -- Escape special LaTeX characters
  s = s:gsub('%%', '\\%%')
  s = s:gsub('&', '\\&')
  s = s:gsub('#', '\\#')
  s = s:gsub('_', '\\_')
  return s
end

local is_twocolumn = false

local function meta_list_contains(meta_value, needle)
  if meta_value == nil then
    return false
  end
  if type(meta_value) == "table" and meta_value.t == "MetaList" then
    for _, item in ipairs(meta_value) do
      if pandoc.utils.stringify(item) == needle then
        return true
      end
    end
    return false
  end
  return pandoc.utils.stringify(meta_value) == needle
end

function Meta(meta)
  is_twocolumn = meta_list_contains(meta["classoption"], "twocolumn")
  return nil
end

local function render_inlines(inlines)
  -- Render inlines to LaTeX string
  local result = pandoc.write(pandoc.Pandoc({pandoc.Para(inlines)}), 'latex')
  -- Remove trailing newline and paragraph wrapper
  result = result:gsub('^%s*', ''):gsub('%s*$', '')
  return result
end

function Table(tbl)
  if not (FORMAT:match 'latex' or FORMAT:match 'pdf') then
    return tbl
  end

  local md_align = nil
  local md_span = nil
  if tbl.attr and tbl.attr.attributes then
    md_align = tbl.attr.attributes["md-align"]
    md_span = tbl.attr.attributes["md-span"]
  end
  
  -- Build column alignment string
  local aligns = {}
  for i, col in ipairs(tbl.colspecs) do
    local align = col[1]
    local width = col[2]

    if type(width) == "number" and width > 0 then
      table.insert(aligns, string.format('p{%.4f\\linewidth}', width))
    elseif align == pandoc.AlignLeft then
      table.insert(aligns, 'l')
    elseif align == pandoc.AlignRight then
      table.insert(aligns, 'r')
    elseif align == pandoc.AlignCenter then
      table.insert(aligns, 'c')
    else
      table.insert(aligns, 'l')
    end
  end
  
  local colspec = table.concat(aligns, '')
  local latex = {}
  
  -- Start table environment
  local env = 'table'
  if md_span == 'full' then
    env = 'table*'
  end
  table.insert(latex, '\\begin{' .. env .. '}[t]')

  if md_align == 'left' then
    table.insert(latex, '\\raggedright')
    table.insert(latex, '\\ifcsname captionsetup\\endcsname\\captionsetup{justification=raggedright,singlelinecheck=false}\\fi')
  elseif md_align == 'right' then
    table.insert(latex, '\\raggedleft')
    table.insert(latex, '\\ifcsname captionsetup\\endcsname\\captionsetup{justification=raggedleft,singlelinecheck=false}\\fi')
  else
    table.insert(latex, '\\centering')
    table.insert(latex, '\\ifcsname captionsetup\\endcsname\\captionsetup{justification=centering,singlelinecheck=false}\\fi')
  end
  
  -- Caption if present (render full content to preserve formatting)
  if tbl.caption and tbl.caption.long and #tbl.caption.long > 0 then
    local caption_content = pandoc.write(pandoc.Pandoc(tbl.caption.long), 'latex')
    caption_content = caption_content:gsub('^%s*', ''):gsub('%s*$', '')
    table.insert(latex, '\\caption{' .. caption_content .. '}')
  end
  
  -- Label if present
  if tbl.identifier and tbl.identifier ~= '' then
    table.insert(latex, '\\label{' .. tbl.identifier .. '}')
  end
  
  table.insert(latex, '\\begin{tabular}{' .. colspec .. '}')
  table.insert(latex, '\\hline')
  
  -- Header row
  if tbl.head and tbl.head.rows and #tbl.head.rows > 0 then
    for _, row in ipairs(tbl.head.rows) do
      local cells = {}
      for _, cell in ipairs(row.cells) do
        local cell_content = pandoc.write(pandoc.Pandoc(cell.contents), 'latex')
        cell_content = cell_content:gsub('^%s*', ''):gsub('%s*$', '')
        table.insert(cells, cell_content)
      end
      table.insert(latex, table.concat(cells, ' & ') .. ' \\\\')
    end
    table.insert(latex, '\\hline')
  end
  
  -- Body rows
  for _, body in ipairs(tbl.bodies) do
    for _, row in ipairs(body.body) do
      local cells = {}
      for _, cell in ipairs(row.cells) do
        local cell_content = pandoc.write(pandoc.Pandoc(cell.contents), 'latex')
        cell_content = cell_content:gsub('^%s*', ''):gsub('%s*$', '')
        table.insert(cells, cell_content)
      end
      table.insert(latex, table.concat(cells, ' & ') .. ' \\\\')
    end
  end
  
  table.insert(latex, '\\hline')
  table.insert(latex, '\\end{tabular}')
  table.insert(latex, '\\end{' .. env .. '}')
  
  return pandoc.RawBlock('latex', table.concat(latex, '\n'))
end
