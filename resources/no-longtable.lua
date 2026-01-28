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
  if tbl.attr and tbl.attr.attributes then
    md_align = tbl.attr.attributes["md-align"]
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
  table.insert(latex, '\\begin{table}[htbp]')

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
  table.insert(latex, '\\end{table}')
  
  return pandoc.RawBlock('latex', table.concat(latex, '\n'))
end
