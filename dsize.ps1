$folders = @('.ollama','.bun','.chocolatey','.cache','.docker','.playwright','.playwright-cli','node_modules','.m2','AppData','Documents','Desktop','Downloads','scoop','.nuget','hiveclip','.claude','.claude-mem','.cline','.cursor','.lmstudio','magentic-ui-env','.local','.pack','Pictures','Videos','Music','.magentic_ui','.basic-memory','paperclip','pixel-agents','new-project','landing-page-ai-hub','suprema-decoder','suprema_cards','suprema_decode')
foreach($f in $folders) {
    $p = "C:\Users\PC\$f"
    if(Test-Path $p) {
        $info = robocopy $p "C:\DOESNOTEXIST" /L /S /NJH /NJS /NDL /NFL /BYTES 2>$null | Select-String 'Bytes'
        if($info) {
            $line = $info.ToString()
            if($line -match 'Bytes\s*:\s*(\d+)') {
                $mb = [math]::Round([int64]$Matches[1]/1MB,0)
                if($mb -gt 10) { Write-Output "$mb MB`t$f" }
            }
        }
    }
}
