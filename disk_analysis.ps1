Write-Output "=== DISK OVERVIEW ==="
$drive = Get-PSDrive C
Write-Output ("Used: {0:N1} GB" -f ($drive.Used/1GB))
Write-Output ("Free: {0:N1} GB" -f ($drive.Free/1GB))
Write-Output ""

Write-Output "=== TOP FOLDERS IN C:\Users\PC ==="
Get-ChildItem 'C:\Users\PC' -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $s = (Get-ChildItem $_.FullName -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
    if ($s -gt 50MB) {
        [PSCustomObject]@{Folder=$_.Name; SizeMB=[math]::Round($s/1MB,0)}
    }
} | Sort-Object SizeMB -Descending | Format-Table -AutoSize

Write-Output "=== TOP FOLDERS IN C:\ ROOT ==="
Get-ChildItem 'C:\' -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $s = 0
    try {
        $s = (Get-ChildItem $_.FullName -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
    } catch {}
    if ($s -gt 500MB) {
        [PSCustomObject]@{Folder=$_.Name; SizeMB=[math]::Round($s/1MB,0)}
    }
} | Sort-Object SizeMB -Descending | Format-Table -AutoSize

Write-Output "=== TEMP FILES ==="
$tempPath = [System.IO.Path]::GetTempPath()
$tempSize = (Get-ChildItem $tempPath -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
Write-Output ("User Temp: {0:N1} MB" -f ($tempSize/1MB))

$winTemp = (Get-ChildItem 'C:\Windows\Temp' -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
Write-Output ("Windows Temp: {0:N1} MB" -f ($winTemp/1MB))

Write-Output ""
Write-Output "=== LARGE FILES (>500MB) in C:\Users\PC ==="
Get-ChildItem 'C:\Users\PC' -Recurse -Force -File -ErrorAction SilentlyContinue | Where-Object { $_.Length -gt 500MB } | Sort-Object Length -Descending | Select-Object @{N='SizeMB';E={[math]::Round($_.Length/1MB,0)}}, FullName -First 30 | Format-Table -AutoSize

Write-Output "=== CACHES ==="
$paths = @{
    'npm cache' = 'C:\Users\PC\AppData\Local\npm-cache'
    'pip cache' = 'C:\Users\PC\AppData\Local\pip\cache'
    'nuget cache' = 'C:\Users\PC\.nuget'
    '.claude' = 'C:\Users\PC\.claude'
    'Docker' = 'C:\Users\PC\AppData\Local\Docker'
}
foreach ($entry in $paths.GetEnumerator()) {
    if (Test-Path $entry.Value) {
        $s = (Get-ChildItem $entry.Value -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        Write-Output ("{0}: {1:N0} MB" -f $entry.Key, ($s/1MB))
    }
}

Write-Output ""
Write-Output "=== node_modules FOLDERS (>50MB) ==="
Get-ChildItem 'C:\Users\PC' -Recurse -Directory -Force -ErrorAction SilentlyContinue -Filter 'node_modules' | ForEach-Object {
    $s = (Get-ChildItem $_.FullName -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    if ($s -gt 50MB) {
        [PSCustomObject]@{SizeMB=[math]::Round($s/1MB,0); Path=$_.FullName}
    }
} | Sort-Object SizeMB -Descending | Format-Table -AutoSize
