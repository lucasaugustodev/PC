$cred = New-Object System.Management.Automation.PSCredential("Administrator", (ConvertTo-SecureString "g4RQgOY4Jnr8" -AsPlainText -Force))
try {
    New-PSDrive -Name "OLD" -PSProvider FileSystem -Root "\\43.157.180.16\C$" -Credential $cred -ErrorAction Stop
    Write-Host "SUCCESS: $(Test-Path OLD:\Users)"
} catch {
    Write-Host "Error: $_"
}
