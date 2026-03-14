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

Write-Output "=== npm/pip/node_modules CACHES ==="
$npmCache = 'C:\Users\PC\AppData\Local\npm-cache'
if (Test-Path $npmCache) {
    $s = (Get-ChildItem $npmCache -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    Write-Output ("npm cache: {0:N1} MB" -f ($s/1MB))
}
$pipCache = 'C:\Users\PC\AppData\Local\pip\cache'
if (Test-Path $pipCache) {
    $s = (Get-ChildItem $pipCache -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    Write-Output ("pip cache: {0:N1} MB" -f ($s/1MB))
}

Write-Output ""
Write-Output "=== node_modules FOLDERS ==="
Get-ChildItem 'C:\Users\PC' -Recurse -Directory -Force -ErrorAction SilentlyContinue -Filter 'node_modules' | ForEach-Object {
    $s = (Get-ChildItem $_.FullName -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    if ($s -gt 50MB) {
        [PSCustomObject]@{SizeMB=[math]::Round($s/1MB,0); Path=$_.FullName}
    }
} | Sort-Object SizeMB -Descending | Format-Table -AutoSize

Write-Output "=== DOCKER ==="
$dockerPath = 'C:\Users\PC\AppData\Local\Docker'
if (Test-Path $dockerPath) {
    $s = (Get-ChildItem $dockerPath -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    Write-Output ("Docker data: {0:N1} GB" -f ($s/1GB))
}

Write-Output "=== .claude CACHE ==="
$claudePath = 'C:\Users\PC\.claude'
if (Test-Path $claudePath) {
    $s = (Get-ChildItem $claudePath -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    Write-Output (".claude: {0:N1} MB" -f ($s/1MB))
}
