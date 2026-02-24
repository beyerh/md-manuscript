function Pandoc(doc)
  local blocks = {}
  
  -- Profile picture
  if doc.meta.picturepath then
    local path = pandoc.utils.stringify(doc.meta.picturepath)
    table.insert(blocks, pandoc.RawBlock('latex', '\\providecommand{\\profilepic}{' .. path .. '}'))
  else
    table.insert(blocks, pandoc.RawBlock('latex', '\\providecommand{\\profilepic}{}'))
  end

  -- Header Left
  if doc.meta.headerleft then
    local hl = pandoc.utils.stringify(doc.meta.headerleft)
    table.insert(blocks, pandoc.RawBlock('latex', '\\providecommand{\\headerleft}{' .. hl .. '}'))
  else
    table.insert(blocks, pandoc.RawBlock('latex', '\\providecommand{\\headerleft}{}'))
  end

  -- Header Right
  if doc.meta.headerright then
    local hr = pandoc.utils.stringify(doc.meta.headerright)
    table.insert(blocks, pandoc.RawBlock('latex', '\\providecommand{\\headerright}{' .. hr .. '}'))
  else
    table.insert(blocks, pandoc.RawBlock('latex', '\\providecommand{\\headerright}{}'))
  end

  -- Date
  if doc.meta.date then
    local d = pandoc.utils.stringify(doc.meta.date)
    table.insert(blocks, pandoc.RawBlock('latex', '\\providecommand{\\documentdate}{' .. d .. '}'))
  else
    table.insert(blocks, pandoc.RawBlock('latex', '\\providecommand{\\documentdate}{\\today}'))
  end

  -- Provide fallback color definitions (overridden by profile-specific definitions)
  table.insert(blocks, pandoc.RawBlock('latex', '\\providecolor{primary}{RGB}{0,0,0}'))
  table.insert(blocks, pandoc.RawBlock('latex', '\\providecolor{linkblue}{RGB}{0,0,0}'))
  table.insert(blocks, pandoc.RawBlock('latex', '\\providecolor{secondary}{RGB}{128,128,128}'))

  -- Insert all blocks at the beginning of the document
  for i = #blocks, 1, -1 do
    table.insert(doc.blocks, 1, blocks[i])
  end

  return doc
end
