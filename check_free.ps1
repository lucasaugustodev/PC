$d = Get-PSDrive C
Write-Output ("Free: {0:N1} GB" -f ($d.Free/1GB))
