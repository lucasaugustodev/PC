Get-Process | Where-Object { $_.Name -match 'mstsc|AutoHotkey' } | Select-Object Name, Id, MainWindowTitle
