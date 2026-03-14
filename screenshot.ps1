Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Start-Sleep -Milliseconds 500
$bmp = New-Object System.Drawing.Bitmap(1920,1080)
$gfx = [System.Drawing.Graphics]::FromImage($bmp)
$gfx.CopyFromScreen(0,0,0,0,[System.Drawing.Size]::new(1920,1080))
$bmp.Save("C:\Users\PC\Downloads\suprema_now.png")
$gfx.Dispose()
$bmp.Dispose()
Write-Output "SAVED"
