-- Dismiss the voice panel on an outside click; moving the pointer does nothing.
local panel_class = "org.omarchy.omp-voice"

local function outside_click(position)
  local cursor = position or hl.get_cursor_pos()
  for _, window in ipairs(hl.get_windows()) do
    if window.class == panel_class and window.mapped and not window.hidden then
      local at, size = window.at, window.size
      -- Include the window's border so clicking its edge doesn't dismiss it.
      local inside = cursor.x >= at.x - 2 and cursor.x <= at.x + size.x + 2
        and cursor.y >= at.y - 2 and cursor.y <= at.y + size.y + 2
      if not inside then
        hl.dispatch(hl.dsp.window.close({ window = window }))
      end
    end
  end
end

for _, button in ipairs({ 272, 273, 274 }) do
  hl.bind("mouse:" .. button, function() outside_click() end, {
    click = true,
    non_consuming = true,
    submap_universal = true,
    description = "Cerrar OMP voz al clicar fuera",
  })
end

return { outside_click = outside_click }
