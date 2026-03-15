Get-ChildItem 'C:\Users\PC\AppData\Local' -Directory | ForEach-Object {
    $size = (Get-ChildItem $_.FullName -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
    if($size -gt 500MB) {
        Write-Host ("{0:N2} GB - {1}" -f ($size/1GB), $_.Name)
    }
}
