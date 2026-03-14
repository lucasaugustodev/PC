Get-ChildItem 'C:\Users\PC\AppData\Local' -Directory | ForEach-Object {
    $size = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    [PSCustomObject]@{ SizeGB = [math]::Round($size / 1GB, 2); Name = $_.Name }
} | Sort-Object SizeGB -Descending | Select-Object -First 15 | Format-Table -AutoSize
