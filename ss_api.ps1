$h = @{
    'X-API-KEY' = 'lmGwbvllpIqIrKROOCLgE5Z941MKP5EYfbkgwtqJZGigfXUTpuYRpNQkCqShmm6r'
}
try {
    $r = Invoke-WebRequest -Uri 'https://api.serverspace.com.br/api/v1/project' -Headers $h -Method Get -UseBasicParsing
    Write-Host "STATUS: $($r.StatusCode)"
    Write-Host $r.Content
} catch {
    Write-Host "STATUS: $($_.Exception.Response.StatusCode.value__)"
    Write-Host "ERROR: $($_.Exception.Message)"
}
