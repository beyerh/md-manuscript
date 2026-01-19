-- pdf2png.lua
function Image(el)
  -- Only swap if target is Docx
  if FORMAT == "docx" then
    -- Change .pdf extension to .png
    el.src = el.src:gsub("%.pdf$", ".png")
  end
  return el
end
