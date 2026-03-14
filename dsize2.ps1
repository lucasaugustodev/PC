$folders = @('.ollama','AppData','.chocolatey','.bun','node_modules','.docker','.playwright','.playwright-cli','.m2','Documents','Desktop','Downloads','scoop','.nuget','hiveclip','.cache','.cursor','.lmstudio','magentic-ui-env','.local','.claude','.claude-mem','Pictures','Videos')
foreach($f in $folders) {
    $p = "C:\Users\PC\$f"
    if(Test-Path $p) {
        $bytes = 0
        Get-ChildItem $p -Recurse -Force -File -ErrorAction SilentlyContinue | ForEach-Object { $bytes += $_.Length }
        $mb = [math]::Round($bytes/1MB,0)
        if($mb -gt 50) {
            Write-Output ("{0,8} MB  {1}" -f $mb, $f)
        }
    }
}
