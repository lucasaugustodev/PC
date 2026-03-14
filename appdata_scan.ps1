Get-ChildItem 'C:\Users\PC\AppData\Local' -Directory -Force -EA 0 | ForEach-Object {
    $s = (Get-ChildItem $_.FullName -Recurse -Force -File -EA 0 | Measure-Object Length -Sum).Sum
    if ($s -gt 500MB) {
        [PSCustomObject]@{GB=[math]::Round($s/1GB,1); Folder=$_.Name}
    }
} | Sort-Object GB -Descending | Format-Table -AutoSize
